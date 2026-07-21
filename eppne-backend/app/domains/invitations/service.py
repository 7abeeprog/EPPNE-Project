# app/domains/invitations/service.py (الإصدار النهائي المتكامل)
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
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
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
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "crm"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
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
        try:
            user = await self._get_user(user_id)
            if user and user.referred_by:  # type: ignore
                commission = Decimal("2.00") if action_type in ["INVITATION_CREATED", "CAMPAIGN_CREATED"] else Decimal("5.00")
                await self.affiliate_service.register_commission(  # type: ignore
                    affiliate_id=user.referred_by,  # type: ignore
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    async def _analyze_target_user(self, user_id: int, tenant_id: int) -> dict:
        try:
            ai_result = await self.ai_service.execute_agent_action(
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

    async def _create_user_from_invitation(self, data: dict, tenant_id: int):
        from app.domains.identity.service import UserService
        identity_service = UserService(self.db)
        # إنشاء مستخدم جديد (تبسيط)
        from app.domains.identity.schemas import UserCreate
        user_create = UserCreate(
            username=data.get("email", "").split("@")[0],
            email=cast(str, data.get("email")),
            password=data.get("password", "TempPass123!")
        )
        return await identity_service.register(user_create, f"INV-{uuid.uuid4().hex[:12]}")

    async def _apply_discount_gift(self, user_id: int, invitation: SovereignInvitation):
        pass

    # ============================================================
    # 1. الدعوات (Invitations)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

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

        # 🔥 معاملة ذرية
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
                await self.db.commit()

        ai_agent = await self._assign_ai_agent(invitation)
        if ai_agent:
            invitation = await self.repo.update_invitation(
                cast(int, invitation.id), tenant_id, assigned_ai_agent_id=ai_agent.id
            )

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
            await store_idempotency_result(idempotency_key, invitation)

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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation or invitation.status != InvitationStatus.SENT:  # type: ignore
            raise NotFoundError("Invitation not found or not sent")

        # 🔥 معاملة ذرية
        async with self.db.begin_nested():
            if not user_id:
                new_user = await self._create_user_from_invitation(accept_data, tenant_id)
                user_id = cast(int, new_user.id)

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
            await store_idempotency_result(idempotency_key, result)

        return result

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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        invitation = await self.repo.get_invitation(invitation_id, tenant_id)
        if not invitation:
            raise NotFoundError("Invitation not found")

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,  # type: ignore
            agent_id=invitation.assigned_ai_agent_id or 1,  # type: ignore
            user_id=user_id or 0,
            action_type="CRM_CHAT",
            tokens=100,
            cost=Decimal("0.01")
        )

        sanitized_message = bleach.clean(user_message, tags=[], strip=True)

        # 🔥 معاملة ذرية لتسجيل المحادثة
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

            ai_response = await self.ai_service.execute_agent_action(
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

        result = {"reply": reply_text, "conversation_id": ai_message.id}

        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

        return result

    async def get_invitation_tracking(self, invitation_id: int, tenant_id: int) -> List[InvitationTracking]:
        return await self.repo.list_tracking(invitation_id, tenant_id)

    async def get_invitation_conversations(self, invitation_id: int, tenant_id: int) -> List[InvitationConversation]:
        return await self.repo.get_conversations(invitation_id, tenant_id)

    async def get_client_insight(self, invitation_id: int, tenant_id: int) -> Optional[ClientInsight]:
        return await self.repo.get_client_insight(invitation_id, tenant_id)

    # ============================================================
    # 2. العملاء المحتملون (Leads)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        async with self.db.begin_nested():
            lead = await self.repo.create_lead(
                tenant_id=tenant_id,  # type: ignore
                idempotency_key=idempotency_key,
                **data
            )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="LEAD_CREATED",
            resource_id=lead.id,  # type: ignore
            details={"source": data.get("source")}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, lead)

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
    # 3. تفاعلات العملاء (Interactions)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

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

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INTERACTION_CREATED",
            resource_id=interaction.id,  # type: ignore
            details={"lead_id": lead_id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, interaction)

        return interaction

    async def get_lead_interactions(self, lead_id: int, tenant_id: int, limit: int = 50) -> List[CustomerInteraction]:
        return await self.repo.list_interactions(lead_id, tenant_id, limit)

    # ============================================================
    # 4. الحملات التسويقية (Campaigns)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        # خصم الميزانية
        budget = data.get("budget_mrusdt", Decimal("0.0"))
        if budget > 0:
            payment_idempotency = f"campaign_budget_{idempotency_key or uuid.uuid4().hex[:12]}"
            await self.finance.transfer(
                sender_id=user_id,
                receiver_email="marketing@eppne.com",
                currency="MR_USDT",
                amount=budget,
                notes=f"Campaign budget: {sanitized_name}",
                idempotency_key=payment_idempotency
            )

            await self.invoicing_service.create_invoice(  # type: ignore
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
            await store_idempotency_result(idempotency_key, campaign)

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
    # 5. تذاكر الدعم (Support Tickets)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

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
            await store_idempotency_result(idempotency_key, ticket)

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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

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

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="TICKET_COMMENT_ADDED",
            resource_id=ticket_comment.id,  # type: ignore
            details={"ticket_id": ticket_id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, ticket_comment)

        return ticket_comment

    async def get_ticket_comments(self, ticket_id: int, tenant_id: int) -> List[TicketComment]:
        return await self.repo.list_ticket_comments(ticket_id, tenant_id)

    # ============================================================
    # 6. التتبع والتحليلات (Tracking)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

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

        if idempotency_key:
            await store_idempotency_result(idempotency_key, tracking)

        return tracking

    # ============================================================
    # 7. الإحصائيات (Stats)
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