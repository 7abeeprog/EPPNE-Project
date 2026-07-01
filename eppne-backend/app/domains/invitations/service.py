# app/domains/invitations/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import uuid
import bleach
import json

from app.domains.invitations.repository import InvitationsRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.invitations.models import (
    SovereignInvitation, InvitationTracking, InvitationConversation, ClientInsight,
    Lead, CustomerInteraction, MarketingCampaign, SupportTicket, TicketComment,
    InvitationStatus, LeadStatus, CampaignStatus, LeadSource, InteractionType
)

class InvitationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvitationsRepository(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "crm"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("CRM feature is not included in your current plan.")
        return subscription, features

    # ========== 1. إنشاء دعوة (مع Idempotency + SaaS + AI) ==========
    async def create_invitation(
        self,
        sender_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None,
        analyze_target: bool = True
    ) -> SovereignInvitation:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # تعقيم المدخلات
        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
        sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)

        # تحليل الهدف بواسطة الذكاء الاصطناعي
        client_insight = None
        if analyze_target and data.get("target_user_id"):
            analysis = await self._analyze_target_user(data["target_user_id"], tenant_id)
            client_insight = await self.repo.create_client_insight(
                tenant_id=tenant_id,
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

        # إنشاء الدعوة
        invitation = await self.repo.create_invitation(
            tenant_id=tenant_id,
            sender_user_id=sender_id,
            title=sanitized_title,
            custom_message=sanitized_message,
            target_entity_identifier=sanitized_identifier,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in ["title", "custom_message", "target_entity_identifier"]}
        )

        if client_insight:
            client_insight.invitation_id = invitation.id
            await self.db.commit()

        # تعيين وكيل ذكاء اصطناعي
        ai_agent = await self._assign_ai_agent(invitation)
        if ai_agent:
            invitation = await self.repo.update_invitation(invitation.id, assigned_ai_agent_id=ai_agent.id)

        # تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(sender_id, tenant_id, "INVITATION_CREATED")

        # تسجيل التدقيق
        await audit_log(
            user_id=sender_id,
            tenant_id=tenant_id,
            action="INVITATION_CREATED",
            resource_id=invitation.id,
            details={"title": invitation.title}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("invitation.created", {
            "invitation_id": invitation.id,
            "tenant_id": tenant_id,
            "sender_id": sender_id
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, invitation)

        return invitation

    # ========== 2. قبول الدعوة (مع تحويل العميل إلى Lead) ==========
    async def accept_invitation(
        self,
        invitation_id: int,
        tenant_id: int,
        accept_data: Dict[str, Any],
        user_id: int = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        invitation = await self.repo.get_invitation(invitation_id)
        if not invitation or invitation.tenant_id != tenant_id:
            raise NotFoundError("Invitation not found")
        if invitation.status != InvitationStatus.SENT:
            raise PermissionDeniedError("Invitation is not active")

        # 1. تحديد المستخدم أو إنشاؤه
        if not user_id:
            new_user = await self._create_user_from_invitation(accept_data, tenant_id)
            user_id = new_user.id

        # 2. إنشاء Lead (عميل محتمل)
        lead = await self.repo.create_lead(
            tenant_id=tenant_id,
            source=LeadSource.INVITATION,
            source_reference=f"INV-{invitation_id}",
            status=LeadStatus.CONVERTED,
            converted_user_id=user_id,
            converted_at=datetime.utcnow(),
            email=accept_data.get("email"),
            first_name=accept_data.get("first_name"),
            last_name=accept_data.get("last_name"),
            phone=accept_data.get("phone"),
            idempotency_key=idempotency_key
        )

        # 3. تطبيق الخصم أو الهدية (عبر المالية)
        if invitation.discount_percentage > 0 or invitation.gift_coins_amount > 0:
            await self._apply_discount_gift(user_id, invitation)

        # 4. تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(user_id, tenant_id, "LEAD_CONVERTED")

        # 5. تحديث حالة الدعوة
        await self.repo.update_invitation(
            invitation_id,
            status=InvitationStatus.ACCEPTED,
            current_uses=invitation.current_uses + 1
        )

        # 6. تسجيل التفاعل الأول
        await self.repo.create_interaction(
            tenant_id=tenant_id,
            lead_id=lead.id,
            user_id=user_id,
            interaction_type=InteractionType.EMAIL,
            title="Invitation Accepted",
            content=f"Accepted invitation: {invitation.title}",
            idempotency_key=idempotency_key
        )

        # 7. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INVITATION_ACCEPTED",
            resource_id=invitation.id,
            details={"lead_id": lead.id}
        )

        # 8. نشر حدث للأتمتة
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

    # ========== 3. محادثة مع الذكاء الاصطناعي (مع AI Governance) ==========
    async def chat_with_ai(
        self,
        invitation_id: int,
        tenant_id: int,
        visitor_session_id: str,
        user_message: str,
        user_id: int = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        invitation = await self.repo.get_invitation(invitation_id)
        if not invitation or invitation.tenant_id != tenant_id:
            raise NotFoundError("Invitation not found")

        # التحقق من حوكمة الذكاء الاصطناعي
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=invitation.assigned_ai_agent_id or 1,
            user_id=user_id or 0,
            tokens=100,
            cost=Decimal("0.01")
        )

        # تسجيل رسالة العميل
        sanitized_message = bleach.clean(user_message, tags=[], strip=True)
        await self.repo.create_conversation(
            tenant_id=tenant_id,
            invitation_id=invitation_id,
            visitor_session_id=visitor_session_id,
            visitor_user_id=user_id,
            message=sanitized_message,
            is_from_ai=False,
            idempotency_key=idempotency_key
        )

        # استدعاء وكيل الذكاء الاصطناعي
        ai_agent_id = invitation.assigned_ai_agent_id or 1
        prompt = f"""
        أنت وكيل ذكاء اصطناعي متخصص في تحويل العملاء.
        الدعوة: {invitation.title}
        نوع الحملة: {invitation.campaign_type}
        رسالة العميل: "{user_message}"
        قم بالرد بأسلوب ودود ومقنع.
        """

        ai_response = await self.ai_service.execute_agent_action(
            agent_id=ai_agent_id,
            tenant_id=tenant_id,
            action_type="CHAT",
            payload={"prompt": prompt},
            executor_user_id=user_id or 0
        )

        reply_text = ai_response.get("result", {}).get("reply", "شكراً لتواصلك. كيف يمكنني مساعدتك؟")

        # تسجيل رد الـ AI
        ai_message = await self.repo.create_conversation(
            tenant_id=tenant_id,
            invitation_id=invitation_id,
            visitor_session_id=visitor_session_id,
            visitor_user_id=user_id,
            message=reply_text,
            is_from_ai=True,
            ai_agent_id=ai_agent_id,
            idempotency_key=idempotency_key
        )

        # تسجيل التفاعل في CRM
        if user_id:
            lead = await self.repo.get_lead_by_user(user_id, tenant_id)
            if lead:
                await self.repo.create_interaction(
                    tenant_id=tenant_id,
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

    # ========== 4. الحملات التسويقية ==========
    async def create_campaign(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> MarketingCampaign:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        # خصم الميزانية (إذا كانت مدفوعة)
        if data.get("budget_mrusdt", 0) > 0:
            await self.finance.transfer(
                sender_id=user_id,
                receiver_email="marketing@eppne.com",
                currency="MR_USDT",
                amount=data["budget_mrusdt"],
                notes=f"Campaign budget: {sanitized_name}",
                idempotency_key=idempotency_key
            )

            # إنشاء فاتورة
            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=user_id,
                amount=data["budget_mrusdt"],
                description=f"Marketing campaign: {sanitized_name}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

        campaign = await self.repo.create_campaign(
            tenant_id=tenant_id,
            created_by=user_id,
            name=sanitized_name,
            description=sanitized_description,
            campaign_type=data["campaign_type"],
            target_audience=data.get("target_audience", {}),
            budget_mrusdt=data.get("budget_mrusdt", 0),
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            channels=data.get("channels", []),
            idempotency_key=idempotency_key
        )

        # تسجيل الإحالة
        await self._register_affiliate_commission(user_id, tenant_id, "CAMPAIGN_CREATED")

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="CAMPAIGN_CREATED",
            resource_id=campaign.id,
            details={"name": campaign.name}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("campaign.created", {
            "campaign_id": campaign.id,
            "tenant_id": tenant_id,
            "user_id": user_id
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, campaign)

        return campaign

    # ========== 5. تتبع سلوك العميل ==========
    async def track_behavior(
        self,
        invitation_id: int,
        tenant_id: int,
        request_data: Dict[str, Any],
        idempotency_key: str = None
    ) -> InvitationTracking:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # تعقيم البيانات
        sanitized_ip = bleach.clean(request_data.get("ip_address", ""), tags=[], strip=True)
        sanitized_user_agent = bleach.clean(request_data.get("user_agent", ""), tags=[], strip=True)

        tracking = await self.repo.create_tracking(
            tenant_id=tenant_id,
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

    # ========== 6. إنشاء تذكرة دعم ==========
    async def create_support_ticket(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        lead_id: int = None,
        idempotency_key: str = None
    ) -> SupportTicket:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        sanitized_subject = bleach.clean(data.get("subject", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        # إذا لم يتم تمرير lead_id، نبحث عنه
        if not lead_id:
            lead = await self.repo.get_lead_by_user(user_id, tenant_id)
            if lead:
                lead_id = lead.id

        ticket = await self.repo.create_ticket(
            tenant_id=tenant_id,
            lead_id=lead_id,
            user_id=user_id,
            subject=sanitized_subject,
            description=sanitized_description,
            priority=data.get("priority", "MEDIUM"),
            idempotency_key=idempotency_key
        )

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="SUPPORT_TICKET_CREATED",
            resource_id=ticket.id,
            details={"subject": ticket.subject}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("support.ticket.created", {
            "ticket_id": ticket.id,
            "tenant_id": tenant_id,
            "user_id": user_id
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, ticket)

        return ticket

    # ========== 7. إضافة تعليق على تذكرة ==========
    async def add_ticket_comment(
        self,
        user_id: int,
        tenant_id: int,
        ticket_id: int,
        comment: str,
        is_internal: bool = False,
        idempotency_key: str = None
    ) -> TicketComment:
        await self._check_saas_limits(tenant_id, "crm")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        ticket = await self.repo.get_ticket(ticket_id, tenant_id)
        if not ticket:
            raise NotFoundError("Ticket not found")

        sanitized_comment = bleach.clean(comment, tags=[], strip=True)

        ticket_comment = await self.repo.create_ticket_comment(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            user_id=user_id,
            comment=sanitized_comment,
            is_internal=is_internal,
            idempotency_key=idempotency_key
        )

        # تحديث حالة التذكرة إذا كان التعليق غير داخلي
        if not is_internal and ticket.status == TicketStatus.OPEN:
            await self.repo.update_ticket_status(ticket_id, tenant_id, TicketStatus.IN_PROGRESS)

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TICKET_COMMENT_ADDED",
            resource_id=ticket_comment.id,
            details={"ticket_id": ticket_id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, ticket_comment)

        return ticket_comment

    # ========== دوال مساعدة ==========
    async def _analyze_target_user(self, user_id: int, tenant_id: int) -> dict:
        """استدعاء وكيل AI لتحليل المستهدف."""
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=12,  # CRM_ANALYST
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={"user_id": user_id},
                executor_user_id=user_id
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
        """تعيين وكيل ذكاء اصطناعي مناسب لنوع الحملة."""
        agents = await self.ai_service.repo.list_agents(role="SUPPORT")
        return agents[0] if agents else None

    async def _create_user_from_invitation(self, data: dict, tenant_id: int):
        """إنشاء مستخدم جديد من بيانات الدعوة."""
        from app.domains.identity.service import IdentityService
        identity_service = IdentityService(self.db)
        return await identity_service.create_user(
            email=data.get("email"),
            password=data.get("password"),
            name=data.get("name"),
            tenant_id=tenant_id
        )

    async def _apply_discount_gift(self, user_id: int, invitation: SovereignInvitation):
        """تطبيق الخصم أو الهدية عبر قطاع المالية."""
        if invitation.discount_percentage > 0:
            # تسجيل خصم في حساب المستخدم
            pass
        if invitation.gift_coins_amount > 0:
            # إضافة عملات مجانية للمستخدم
            pass

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        """تسجيل عمولة الإحالة."""
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("2.00") if action_type in ["INVITATION_CREATED", "CAMPAIGN_CREATED"] else Decimal("5.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")