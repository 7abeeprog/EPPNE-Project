# app/domains/invitations/service.py (الإصدار النهائي المتكامل المصحح بالكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, cast
import uuid
import bleach
import json

from app.domains.invitations.repository import InvitationsRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.invitations.models import (
    SovereignInvitation, InvitationTracking, InvitationConversation, ClientInsight,
    Lead, CustomerInteraction, MarketingCampaign, SupportTicket, TicketComment,
    InvitationStatus, LeadStatus, CampaignStatus, LeadSource, InteractionType, TicketStatus, CampaignType
)
from app.domains.identity.models import User


class InvitationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvitationsRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "crm"):
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        subscription = await saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        if not subscription.plan:
            raise PermissionDeniedError("No valid subscription plan found.")
        features = subscription.plan.features or []
        if feature not in features:
            raise PermissionDeniedError("CRM feature is not included in your current plan.")
        return subscription, features

    async def _get_user(self, user_id: int) -> Optional[User]:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_id(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    async def _get_entity_email(self, entity_id: int) -> str:
        return f"entity_{entity_id}@eppne.com"

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id)
            if user and user.referred_by:  # type: ignore
                commission = Decimal("2.00") if action_type in ["INVITATION_CREATED", "CAMPAIGN_CREATED"] else Decimal("5.00")
                await affiliate_service.register_commission(  # type: ignore
                    affiliate_id=user.referred_by,  # type: ignore
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    async def _analyze_target_user(self, user_id: int, tenant_id: int) -> dict:
        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            ai_result = await ai_service.execute_agent_action(
                agent_id=12,
                tenant_id=tenant_id,  # type: ignore
                action_type="ANALYZE_SENSOR",
                payload={"user_id": user_id},
                executor_user_id=user_id,
            )
            return ai_result.get("result", {
                "analysis": {"interests": ["General"], "engagement_level": "medium"},
                "recommended_discount": 10,
                "recommended_message": "مرحباً، ندعوك لتجربة خدماتنا.",
                "readiness_score": 50
            })
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "analysis": {"interests": ["General"], "engagement_level": "medium"},
                "recommended_discount": 10,
                "recommended_message": "مرحباً، ندعوك لتجربة خدماتنا.",
                "readiness_score": 50
            }

    async def _assign_ai_agent(self, invitation: SovereignInvitation):
        from app.domains.ai_agents.repository import AIAgentsRepository
        agents_repo = AIAgentsRepository(self.db)
        agents = await agents_repo.list_agents(
            tenant_id=invitation.tenant_id,  # type: ignore
            role="SUPPORT"
        )
        return agents[0] if agents else None

    async def _create_user_from_invitation(self, data: dict, tenant_id: int, invitation_id: int):
        from app.domains.identity.service import UserService
        identity_service = UserService(self.db, tenant_id)
        from app.domains.identity.schemas import UserCreate
        user_create = UserCreate(
            username=data.get("email", "").split("@")[0],
            email=cast(str, data.get("email")),
            password=data.get("password", "TempPass123!")
        )
        return await identity_service.register(user_create, f"INV-ACCEPT-T{tenant_id}-{invitation_id}")

    async def _apply_discount_gift(self, user_id: int, invitation: SovereignInvitation):
        pass

    # ============================================================
    # دوال Idempotency الموحّدة
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. الدعوات (Invitations) – مع Idempotency محسّن
    # ============================================================

    async def create_invitation(
        self,
        sender_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        analyze_target: bool = True
    ) -> SovereignInvitation:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                invitation_id = cached.get("invitation_id")
                if invitation_id:
                    invitation = await self.repo.get_invitation(invitation_id, tenant_id)
                    if invitation:
                        return invitation
                raise ValidationError("Idempotency record exists but invitation not found.")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
        sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)

        client_insight = None
        if analyze_target and data.get("target_user_id"):
            analysis = await self._analyze_target_user(data["target_user_id"], tenant_id)
            client_insight = await self.repo.create_client_insight(
                tenant_id=tenant_id,  # type: ignore
                invitation_id=0,
                ai_analysis=analysis["analysis"],
                recommended_discount=analysis["recommended_discount"],
                recommended_message_template=analysis["recommended_message"],
                readiness_score=analysis["readiness_score"]
            )
            if analysis["recommended_message"] and not data.get("custom_message"):
                data["custom_message"] = analysis["recommended_message"]
            if analysis["recommended_discount"] and data.get("discount_percentage", 0) == 0:
                data["discount_percentage"] = analysis["recommended_discount"]

        async with self.db.begin_nested():
            invitation = await self.repo.create_invitation(
                tenant_id=tenant_id,  # type: ignore
                sender_user_id=sender_id,
                title=sanitized_title,
                custom_message=sanitized_message,
                target_entity_identifier=sanitized_identifier,
                idempotency_key=idempotency_key,
                **{k: v for k, v in data.items() if k not in ["title", "custom_message", "target_entity_identifier"]}
            )

            if client_insight:
                client_insight.invitation_id = invitation.id  # type: ignore
                await self.db.flush()

        ai_agent = await self._assign_ai_agent(invitation)
        if ai_agent:
            invitation = await self.repo.update_invitation(
                cast(int, invitation.id), tenant_id, assigned_ai_agent_id=ai_agent.id
            )

        await self.db.commit()

        await self._register_affiliate_commission(sender_id, tenant_id, "INVITATION_CREATED")

        await audit_log(
            user_id=sender_id,
            tenant_id=tenant_id,  # type: ignore
            action="INVITATION_CREATED",
            resource_id=invitation.id,  # type: ignore
            details={"title": invitation.title}
        )

        await self.event_bus.publish("invitation.created", {
            "invitation_id": invitation.id,
            "tenant_id": tenant_id,
            "sender_id": sender_id
        })

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"invitation_id": invitation.id})

        return invitation

    async def list_invitations(
        self,
        tenant_id: int,
        status: Optional[InvitationStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignInvitation]:
        return await self.repo.list_invitations(tenant_id, status, campaign_type, skip, limit)

    async def get_invitation(self, invitation_id: int, tenant_id: int) -> Optional[SovereignInvitation]:
        return await self.repo.get_invitation(invitation_id, tenant_id)

    async def update_invitation(
        self,
        invitation_id: int,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> SovereignInvitation:
        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation or invitation.sender_user_id != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        return await self.repo.update_invitation(invitation_id, tenant_id, **data)

    async def delete_invitation(self, invitation_id: int, tenant_id: int, user_id: int) -> None:
        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation or invitation.sender_user_id != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        await self.repo.delete_invitation(invitation_id, tenant_id)

    # ============================================================
    # 2. قبول الدعوة – مع Idempotency محسّن
    # ============================================================

    async def accept_invitation(
        self,
        invitation_id: int,
        tenant_id: int,
        accept_data: Dict[str, Any],
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation or invitation.status != InvitationStatus.SENT:  # type: ignore
            raise NotFoundError("Invitation not found or not sent")

        if not user_id:
            new_user = await self._create_user_from_invitation(accept_data, tenant_id, invitation_id)
            user_id = cast(int, new_user.id)

        async with self.db.begin_nested():
            lead = await self.repo.create_lead(
                tenant_id=tenant_id,  # type: ignore
                source=LeadSource.INVITATION,
                source_reference=f"INV-{invitation_id}",
                status=LeadStatus.CONVERTED,
                converted_user_id=user_id,
                converted_at=datetime.utcnow(),
                email=accept_data.get("email"),
                first_name=accept_data.get("name"),
                phone=accept_data.get("phone"),
                idempotency_key=idempotency_key
            )

            if cast(Any, invitation.discount_percentage) > 0 or cast(Any, invitation.gift_coins_amount) > 0:
                await self._apply_discount_gift(cast(int, user_id), invitation)

            await self.repo.update_invitation(
                invitation_id,
                tenant_id,
                status=InvitationStatus.ACCEPTED,
                current_uses=invitation.current_uses + 1  # type: ignore
            )

            await self.repo.create_interaction(
                tenant_id=tenant_id,  # type: ignore
                lead_id=lead.id,
                user_id=user_id,
                interaction_type=InteractionType.EMAIL,
                title="Invitation Accepted",
                content=f"Accepted invitation: {invitation.title}",
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await self._register_affiliate_commission(cast(int, user_id), tenant_id, "LEAD_CONVERTED")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INVITATION_ACCEPTED",
            resource_id=invitation.id,  # type: ignore
            details={"lead_id": lead.id}
        )

        await self.event_bus.publish("invitation.accepted", {
            "invitation_id": invitation.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "lead_id": lead.id
        })

        result = {
            "message": "Invitation accepted successfully",
            "user_id": user_id,
            "lead_id": lead.id,
            "redirect_url": f"/campaign/{invitation.campaign_id}"
        }

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    # ============================================================
    # 3. الدردشة مع الذكاء الاصطناعي – مع Idempotency محسّن
    # ============================================================

    async def chat_with_ai(
        self,
        invitation_id: int,
        tenant_id: int,
        visitor_session_id: str,
        user_message: str,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation:
            raise NotFoundError("Invitation not found")

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db, tenant_id)
        await governance.check_and_consume(
            agent_id=invitation.assigned_ai_agent_id or 1,  # type: ignore
            user_id=user_id or 0,
            action_type="CRM_CHAT",
            tokens=100,
            cost=Decimal("0.01")
        )

        sanitized_message = bleach.clean(user_message, tags=[], strip=True)

        ai_service = AIAgentsService(self.db, tenant_id)
        async with self.db.begin_nested():
            await self.repo.create_conversation(
                tenant_id=tenant_id,  # type: ignore
                invitation_id=invitation_id,
                visitor_session_id=visitor_session_id,
                visitor_user_id=user_id,
                message=sanitized_message,
                is_from_ai=False,
                idempotency_key=idempotency_key
            )

            ai_agent_id = invitation.assigned_ai_agent_id or 1  # type: ignore
            prompt = f"""
            أنت وكيل ذكاء اصطناعي متخصص في تحويل العملاء.
            الدعوة: {invitation.title}
            نوع الحملة: {invitation.campaign_type}
            رسالة العميل: "{user_message}"
            قم بالرد بأسلوب ودود ومقنع.
            """

            ai_response = await ai_service.execute_agent_action(
                agent_id=ai_agent_id,
                tenant_id=tenant_id,  # type: ignore
                action_type="CHAT",
                payload={"prompt": prompt},
                executor_user_id=user_id or 0
            )

            reply_text = ai_response.get("result", {}).get("reply", "شكراً لتواصلك. كيف يمكنني مساعدتك؟")

            ai_message = await self.repo.create_conversation(
                tenant_id=tenant_id,  # type: ignore
                invitation_id=invitation_id,
                visitor_session_id=visitor_session_id,
                visitor_user_id=user_id,
                message=reply_text,
                is_from_ai=True,
                ai_agent_id=ai_agent_id,
                idempotency_key=idempotency_key
            )

            if user_id:
                lead = await self.repo.get_lead_by_user(user_id, tenant_id)
                if lead:
                    await self.repo.create_interaction(
                        tenant_id=tenant_id,  # type: ignore
                        lead_id=lead.id,
                        user_id=user_id,
                        interaction_type=InteractionType.CHAT,
                        title="AI Chat",
                        content=user_message[:500],
                        metadata={"ai_reply": reply_text[:500]},
                        idempotency_key=idempotency_key
                    )

        await self.db.commit()

        result = {"reply": reply_text, "conversation_id": ai_message.id}

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    async def get_invitation_tracking(self, invitation_id: int, tenant_id: int) -> List[InvitationTracking]:
        return await self.repo.list_tracking(invitation_id, tenant_id)

    async def get_invitation_conversations(self, invitation_id: int, tenant_id: int) -> List[InvitationConversation]:
        return await self.repo.get_conversations(invitation_id, tenant_id)

    async def get_client_insight(self, invitation_id: int, tenant_id: int) -> Optional[ClientInsight]:
        return await self.repo.get_client_insight(invitation_id, tenant_id)

    # ============================================================
    # 4. العملاء المحتملون (Leads) – مع Idempotency محسّن
    # ============================================================

    async def create_lead(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> Lead:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                lead_id = cached.get("lead_id")
                if lead_id:
                    lead = await self.repo.get_lead(lead_id, tenant_id)
                    if lead:
                        return lead
                raise ValidationError("Idempotency record exists but lead not found.")

        async with self.db.begin_nested():
            lead = await self.repo.create_lead(
                tenant_id=tenant_id,  # type: ignore
                idempotency_key=idempotency_key,
                **data
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="LEAD_CREATED",
            resource_id=lead.id,  # type: ignore
            details={"source": data.get("source")}
        )

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"lead_id": lead.id})

        return lead

    async def list_leads(
        self,
        tenant_id: int,
        status: Optional[LeadStatus] = None,
        source: Optional[LeadSource] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Lead]:
        return await self.repo.list_leads(tenant_id, status, source, skip, limit)

    async def get_lead(self, lead_id: int, tenant_id: int) -> Optional[Lead]:
        return await self.repo.get_lead(lead_id, tenant_id)

    async def update_lead(
        self,
        lead_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> Lead:
        return await self.repo.update_lead(lead_id, tenant_id, **data)

    async def delete_lead(self, lead_id: int, tenant_id: int) -> None:
        await self.repo.delete_lead(lead_id, tenant_id)

    # ============================================================
    # 5. تفاعلات العملاء (Interactions) – مع Idempotency محسّن
    # ============================================================

    async def create_interaction(
        self,
        lead_id: int,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> CustomerInteraction:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                interaction_id = cached.get("interaction_id")
                if interaction_id:
                    try:
                        from app.domains.invitations.models import CustomerInteraction
                        # إعادة بناء الكائن من البيانات المخزنة
                        return CustomerInteraction(
                            id=interaction_id,
                            lead_id=lead_id,
                            user_id=user_id,
                            tenant_id=tenant_id,
                            interaction_type=InteractionType(cached.get("interaction_type", "EMAIL")),
                            title=cached.get("title", ""),
                            content=cached.get("content", ""),
                            metadata=cached.get("metadata", {}),
                            created_at=datetime.utcnow()
                        )
                    except Exception:
                        raise ValidationError("Idempotency record exists but cannot reconstruct interaction.")
                raise ValidationError("Idempotency record exists but interaction not found.")

        lead = await self.repo.get_lead(lead_id, tenant_id)
        if not lead:
            raise NotFoundError("Lead not found")

        async with self.db.begin_nested():
            interaction = await self.repo.create_interaction(
                tenant_id=tenant_id,  # type: ignore
                lead_id=lead_id,
                user_id=user_id,
                idempotency_key=idempotency_key,
                **data
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INTERACTION_CREATED",
            resource_id=interaction.id,  # type: ignore
            details={"lead_id": lead_id}
        )

        if idempotency_key:
            # 🔥 تخزين البيانات كاملة مع استخدام cast لـ created_at
            created_at = cast(datetime, interaction.created_at)
            result_data = {
                "interaction_id": interaction.id,
                "lead_id": interaction.lead_id,
                "user_id": interaction.user_id,
                "interaction_type": interaction.interaction_type.value if hasattr(interaction.interaction_type, 'value') else str(interaction.interaction_type),
                "title": interaction.title,
                "content": interaction.content,
                "metadata": interaction.metadata,
                "created_at": created_at.isoformat() if created_at else None
            }
            await self._store_idempotency(idempotency_key, result_data)

        return interaction

    async def get_lead_interactions(self, lead_id: int, tenant_id: int, limit: int = 50) -> List[CustomerInteraction]:
        return await self.repo.list_interactions(lead_id, tenant_id, limit)

    # ============================================================
    # 6. الحملات التسويقية (Campaigns) – مع Idempotency محسّن
    # ============================================================

    async def create_campaign(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> MarketingCampaign:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                campaign_id = cached.get("campaign_id")
                if campaign_id:
                    campaign = await self.repo.get_campaign(campaign_id, tenant_id)
                    if campaign:
                        return campaign
                raise ValidationError("Idempotency record exists but campaign not found.")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        budget = data.get("budget_mrusdt", Decimal("0.0"))
        if budget > 0:
            payment_idempotency = f"campaign_budget_{idempotency_key or uuid.uuid4().hex[:12]}"
            finance = FinanceService(self.db, tenant_id)
            invoice_service = InvoicingService(self.db, tenant_id)
            await finance.transfer(
                sender_id=user_id,
                receiver_email="marketing@eppne.com",
                currency="MR_USDT",
                amount=budget,
                notes=f"Campaign budget: {sanitized_name}",
                idempotency_key=payment_idempotency
            )

            await invoice_service.create_invoice(  # type: ignore
                entity_id=tenant_id,
                user_id=user_id,
                amount=budget,
                description=f"Marketing campaign: {sanitized_name}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

        async with self.db.begin_nested():
            campaign = await self.repo.create_campaign(
                tenant_id=tenant_id,  # type: ignore
                created_by=user_id,
                name=sanitized_name,
                description=sanitized_description,
                campaign_type=data["campaign_type"],
                target_audience=data.get("target_audience", {}),
                budget_mrusdt=budget,
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                channels=data.get("channels", []),
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await self._register_affiliate_commission(user_id, tenant_id, "CAMPAIGN_CREATED")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="CAMPAIGN_CREATED",
            resource_id=campaign.id,  # type: ignore
            details={"name": campaign.name}
        )

        await self.event_bus.publish("campaign.created", {
            "campaign_id": campaign.id,
            "tenant_id": tenant_id,
            "user_id": user_id
        })

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"campaign_id": campaign.id})

        return campaign

    async def list_campaigns(
        self,
        tenant_id: int,
        status: Optional[CampaignStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MarketingCampaign]:
        return await self.repo.list_campaigns(tenant_id, status, campaign_type, skip, limit)

    async def get_campaign(self, campaign_id: int, tenant_id: int) -> Optional[MarketingCampaign]:
        return await self.repo.get_campaign(campaign_id, tenant_id)

    async def update_campaign(
        self,
        campaign_id: int,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> MarketingCampaign:
        campaign = await self.repo.get_campaign(campaign_id, tenant_id)
        if not campaign or campaign.created_by != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        return await self.repo.update_campaign(campaign_id, tenant_id, **data)

    async def delete_campaign(self, campaign_id: int, tenant_id: int, user_id: int) -> None:
        campaign = await self.repo.get_campaign(campaign_id, tenant_id)
        if not campaign or campaign.created_by != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        await self.repo.delete_campaign(campaign_id, tenant_id)

    async def launch_campaign(self, campaign_id: int, tenant_id: int, user_id: int) -> MarketingCampaign:
        campaign = await self.repo.get_campaign(campaign_id, tenant_id)
        if not campaign or campaign.created_by != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        return await self.repo.update_campaign(campaign_id, tenant_id, status=CampaignStatus.ACTIVE)

    # ============================================================
    # 7. تذاكر الدعم (Support Tickets) – مع Idempotency محسّن
    # ============================================================

    async def create_ticket(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        lead_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> SupportTicket:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                ticket_id = cached.get("ticket_id")
                if ticket_id:
                    ticket = await self.repo.get_ticket(ticket_id, tenant_id)
                    if ticket:
                        return ticket
                raise ValidationError("Idempotency record exists but ticket not found.")

        sanitized_subject = bleach.clean(data.get("subject", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        if not lead_id:
            lead = await self.repo.get_lead_by_user(user_id, tenant_id)
            if lead:
                lead_id = cast(int, lead.id)

        async with self.db.begin_nested():
            ticket = await self.repo.create_ticket(
                tenant_id=tenant_id,  # type: ignore
                lead_id=lead_id,
                user_id=user_id,
                subject=sanitized_subject,
                description=sanitized_description,
                priority=data.get("priority", "MEDIUM"),
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="SUPPORT_TICKET_CREATED",
            resource_id=ticket.id,  # type: ignore
            details={"subject": ticket.subject}
        )

        await self.event_bus.publish("support.ticket.created", {
            "ticket_id": ticket.id,
            "tenant_id": tenant_id,
            "user_id": user_id
        })

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"ticket_id": ticket.id})

        return ticket

    async def list_tickets(
        self,
        tenant_id: int,
        status: Optional[TicketStatus] = None,
        assigned_to: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportTicket]:
        return await self.repo.list_tickets(tenant_id, status, assigned_to, skip, limit)

    async def get_ticket(self, ticket_id: int, tenant_id: int) -> Optional[SupportTicket]:
        return await self.repo.get_ticket(ticket_id, tenant_id)

    async def update_ticket(
        self,
        ticket_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SupportTicket:
        return await self.repo.update_ticket(ticket_id, tenant_id, **data)

    # ============================================================
    # 8. تعليقات التذاكر – مع Idempotency محسّن
    # ============================================================

    async def add_ticket_comment(
        self,
        ticket_id: int,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> TicketComment:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                comment_id = cached.get("comment_id")
                if comment_id:
                    try:
                        from app.domains.invitations.models import TicketComment
                        return TicketComment(
                            id=comment_id,
                            ticket_id=ticket_id,
                            user_id=user_id,
                            tenant_id=tenant_id,
                            comment=cached.get("comment", ""),
                            is_internal=cached.get("is_internal", False),
                            created_at=datetime.utcnow()
                        )
                    except Exception:
                        raise ValidationError("Idempotency record exists but cannot reconstruct comment.")
                raise ValidationError("Idempotency record exists but comment not found.")

        ticket = await self.repo.get_ticket(ticket_id, tenant_id)
        if not ticket:
            raise NotFoundError("Ticket not found")

        sanitized_comment = bleach.clean(data.get("comment", ""), tags=[], strip=True)
        is_internal = data.get("is_internal", False)

        async with self.db.begin_nested():
            ticket_comment = await self.repo.create_ticket_comment(
                tenant_id=tenant_id,  # type: ignore
                ticket_id=ticket_id,
                user_id=user_id,
                comment=sanitized_comment,
                is_internal=is_internal,
                idempotency_key=idempotency_key
            )

            if not is_internal and ticket.status == TicketStatus.OPEN:  # type: ignore
                await self.repo.update_ticket_status(ticket_id, tenant_id, TicketStatus.IN_PROGRESS)

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="TICKET_COMMENT_ADDED",
            resource_id=ticket_comment.id,  # type: ignore
            details={"ticket_id": ticket_id}
        )

        if idempotency_key:
            # 🔥 تخزين البيانات كاملة مع استخدام cast لـ created_at
            created_at = cast(datetime, ticket_comment.created_at)
            result_data = {
                "comment_id": ticket_comment.id,
                "ticket_id": ticket_comment.ticket_id,
                "user_id": ticket_comment.user_id,
                "comment": ticket_comment.comment,
                "is_internal": ticket_comment.is_internal,
                "created_at": created_at.isoformat() if created_at else None
            }
            await self._store_idempotency(idempotency_key, result_data)

        return ticket_comment

    async def get_ticket_comments(self, ticket_id: int, tenant_id: int) -> List[TicketComment]:
        return await self.repo.list_ticket_comments(ticket_id, tenant_id)

    # ============================================================
    # 9. التتبع والتحليلات (Tracking) – مع Idempotency محسّن
    # ============================================================

    async def track_behavior(
        self,
        invitation_id: int,
        tenant_id: int,
        request_data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> InvitationTracking:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                tracking_id = cached.get("tracking_id")
                if tracking_id:
                    try:
                        from app.domains.invitations.models import InvitationTracking
                        return InvitationTracking(
                            id=tracking_id,
                            invitation_id=invitation_id,
                            tenant_id=tenant_id,
                            ip_address=cached.get("ip_address", ""),
                            user_agent=cached.get("user_agent", ""),
                            device_type=cached.get("device_type"),
                            location_city=cached.get("location_city"),
                            location_country=cached.get("location_country"),
                            page_visited=cached.get("page_visited"),
                            time_spent_seconds=cached.get("time_spent_seconds", 0),
                            actions=cached.get("actions", []),
                            created_at=datetime.utcnow()
                        )
                    except Exception:
                        raise ValidationError("Idempotency record exists but cannot reconstruct tracking.")
                raise ValidationError("Idempotency record exists but tracking not found.")

        sanitized_ip = bleach.clean(request_data.get("ip_address", ""), tags=[], strip=True)
        sanitized_user_agent = bleach.clean(request_data.get("user_agent", ""), tags=[], strip=True)

        async with self.db.begin_nested():
            tracking = await self.repo.create_tracking(
                tenant_id=tenant_id,  # type: ignore
                invitation_id=invitation_id,
                ip_address=sanitized_ip,
                user_agent=sanitized_user_agent,
                device_type=request_data.get("device_type"),
                location_city=request_data.get("location_city"),
                location_country=request_data.get("location_country"),
                page_visited=request_data.get("page_visited"),
                time_spent_seconds=request_data.get("time_spent_seconds", 0),
                actions=request_data.get("actions", []),
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        if idempotency_key:
            # 🔥 تخزين البيانات كاملة مع استخدام cast لـ created_at
            created_at = cast(datetime, tracking.created_at)
            result_data = {
                "tracking_id": tracking.id,
                "invitation_id": tracking.invitation_id,
                "ip_address": tracking.ip_address,
                "user_agent": tracking.user_agent,
                "device_type": tracking.device_type,
                "location_city": tracking.location_city,
                "location_country": tracking.location_country,
                "page_visited": tracking.page_visited,
                "time_spent_seconds": tracking.time_spent_seconds,
                "actions": tracking.actions,
                "created_at": created_at.isoformat() if created_at else None
            }
            await self._store_idempotency(idempotency_key, result_data)

        return tracking

    # ============================================================
    # 10. الإحصائيات (Stats)
    # ============================================================

    async def get_stats(self, tenant_id: int, user_id: int) -> dict:
        invitations = await self.repo.list_invitations(tenant_id)
        leads = await self.repo.list_leads(tenant_id)
        campaigns = await self.repo.list_campaigns(tenant_id)
        tickets = await self.repo.list_tickets(tenant_id)

        total_invitations = len(invitations)
        sent_invitations = len([i for i in invitations if i.status == InvitationStatus.SENT])  # type: ignore
        accepted_invitations = len([i for i in invitations if i.status == InvitationStatus.ACCEPTED])  # type: ignore
        conversion_rate = (accepted_invitations / sent_invitations * 100) if sent_invitations > 0 else 0.0
        total_clicks = sum(i.click_count for i in invitations)  # type: ignore

        total_leads = len(leads)
        converted_leads = len([l for l in leads if l.status == LeadStatus.CONVERTED])  # type: ignore
        active_campaigns = len([c for c in campaigns if c.status == CampaignStatus.ACTIVE])  # type: ignore
        open_tickets = len([t for t in tickets if t.status in (TicketStatus.OPEN, TicketStatus.IN_PROGRESS)])  # type: ignore

        return {
            "total_invitations": total_invitations,
            "sent_invitations": sent_invitations,
            "accepted_invitations": accepted_invitations,
            "conversion_rate": round(conversion_rate, 2),
            "total_clicks": total_clicks,
            "total_leads": total_leads,
            "converted_leads": converted_leads,
            "active_campaigns": active_campaigns,
            "open_tickets": open_tickets
        }