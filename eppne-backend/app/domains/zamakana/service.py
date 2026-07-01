# app/domains/zamakana/service.py (الإصدار النهائي المتكامل)
"""
خدمات قطاع الزمكان – محرك المعرفة والتأثير عبر الزمن
يدعم: إنشاء عقد المعرفة، ربطها، الحملات الكوكبية، التعهدات الزمنية،
المحاكاة المستقبلية بالذكاء الاصطناعي، والمراجعة البشرية.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import uuid
import json
import bleach

from app.domains.zamakana.repository import ZamakanaRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.zamakana.models import (
    ZamakanaNode, ZamakanaEdge, PlanetaryCampaign, TimePledge,
    FutureScenario, HumanFeedback, PledgeStatus
)

class ZamakanaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ZamakanaRepository(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "zamakana"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Zamakana feature is not included in your current plan.")
        return subscription, features

    # ========== إنشاء عقدة معرفية ==========
    async def create_node(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> ZamakanaNode:
        await self._check_saas_limits(tenant_id, "zamakana")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        node = await self.repo.create_node(
            tenant_id=tenant_id,
            created_by=user_id,
            title=sanitized_title,
            description=sanitized_description,
            node_type=data["node_type"],
            timeline_year=data.get("timeline_year"),
            geo_location=bleach.clean(data.get("geo_location", ""), tags=[], strip=True) if data.get("geo_location") else None,
            verified_sources=data.get("verified_sources", []),
            extra_data=data.get("extra_data", {})
        )

        # تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(user_id, tenant_id, "NODE_CREATED")

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="ZAMAKANA_NODE_CREATED",
            resource_id=node.id,
            details={"title": node.title, "type": node.node_type.value}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("zamakana.node.created", {
            "node_id": node.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": node.title
        })

        return node

    # ========== إنشاء حافة معرفية (مع Idempotency) ==========
    async def create_edge(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> ZamakanaEdge:
        await self._check_saas_limits(tenant_id, "zamakana")

        # التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # التحقق من وجود العقدتين
        source = await self.repo.get_node(data["source_node_id"], tenant_id)
        target = await self.repo.get_node(data["target_node_id"], tenant_id)
        if not source or not target:
            raise NotFoundError("One or both nodes not found")

        # تعقيم المدخلات
        sanitized_description = bleach.clean(data.get("impact_description", ""), tags=[], strip=True)

        edge = await self.repo.create_edge(
            tenant_id=tenant_id,
            created_by=user_id,
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            impact_description=sanitized_description,
            impact_weight=data.get("impact_weight", 1.0),
            is_alternative_timeline=data.get("is_alternative_timeline", False),
            idempotency_key=idempotency_key
        )

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="ZAMAKANA_EDGE_CREATED",
            resource_id=edge.id,
            details={"source": source.title, "target": target.title}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, edge)

        return edge

    # ========== الرسم البياني المعرفي (محسّن) ==========
    async def get_knowledge_graph(self, tenant_id: int, node_type: Optional[str] = None, limit: int = 100) -> dict:
        return await self.repo.get_knowledge_graph_optimized(tenant_id, node_type, min(limit, 200))

    # ========== الحملات الكوكبية ==========
    async def create_campaign(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> PlanetaryCampaign:
        await self._check_saas_limits(tenant_id, "zamakana")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        campaign = await self.repo.create_campaign(
            tenant_id=tenant_id,
            created_by=user_id,
            title=sanitized_title,
            description=sanitized_description,
            target_time_hours=data["target_time_hours"],
            end_date=data["end_date"]
        )

        # تسجيل الإحالة
        await self._register_affiliate_commission(user_id, tenant_id, "CAMPAIGN_CREATED")

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="PLANETARY_CAMPAIGN_CREATED",
            resource_id=campaign.id,
            details={"title": campaign.title}
        )

        await self.event_bus.publish("zamakana.campaign.created", {
            "campaign_id": campaign.id,
            "tenant_id": tenant_id,
            "title": campaign.title
        })

        return campaign

    # ========== التعهد بالساعات (مع Idempotency) ==========
    async def pledge_time(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> TimePledge:
        await self._check_saas_limits(tenant_id, "zamakana")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        campaign = await self.repo.get_campaign(data["campaign_id"], tenant_id)
        if not campaign or campaign.status != "ACTIVE":
            raise NotFoundError("Campaign not active or not found")

        if campaign.collected_time_hours >= campaign.target_time_hours:
            raise PermissionDeniedError("Campaign already reached its target")

        pledge = await self.repo.create_pledge(
            tenant_id=tenant_id,
            campaign_id=data["campaign_id"],
            user_id=user_id,
            pledged_hours=data["pledged_hours"],
            skill_category=bleach.clean(data.get("skill_category", ""), tags=[], strip=True) if data.get("skill_category") else None,
            idempotency_key=idempotency_key
        )

        # إنشاء فاتورة (للخدمات المدفوعة)
        if pledge.pledged_hours > 10:
            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=user_id,
                amount=Decimal("5.00"),
                description=f"Time pledge registration for campaign {campaign.title}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TIME_PLEDGE_CREATED",
            resource_id=pledge.id,
            details={"campaign_id": campaign.id, "hours": float(pledge.pledged_hours)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, pledge)

        return pledge

    # ========== إثبات التعهد (مع Idempotency) ==========
    async def fulfill_pledge(
        self,
        user_id: int,
        tenant_id: int,
        pledge_id: int,
        proof_hash: str,
        idempotency_key: str = None
    ) -> TimePledge:
        await self._check_saas_limits(tenant_id, "zamakana")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        pledge = await self.repo.get_pledge(pledge_id, tenant_id)
        if not pledge or pledge.user_id != user_id:
            raise NotFoundError("Pledge not found or not yours")
        if pledge.status != "PENDING":
            raise PermissionDeniedError("Pledge already fulfilled or cancelled")

        sanitized_proof = bleach.clean(proof_hash, tags=[], strip=True)

        fulfilled = await self.repo.fulfill_pledge(pledge_id, tenant_id, sanitized_proof, user_id)

        # إضافة الساعات إلى الحملة
        campaign = await self.repo.get_campaign(pledge.campaign_id, tenant_id)
        if campaign:
            await self.repo.add_collected_hours(campaign.id, tenant_id, float(pledge.pledged_hours))

            # إذا اكتملت الحملة
            if campaign.collected_time_hours >= campaign.target_time_hours:
                await self.repo.update_campaign(campaign.id, tenant_id, status="COMPLETED")
                await self.event_bus.publish("zamakana.campaign.completed", {
                    "campaign_id": campaign.id,
                    "tenant_id": tenant_id,
                    "title": campaign.title,
                    "total_hours": float(campaign.collected_time_hours)
                })

        # تسجيل الإحالة
        await self._register_affiliate_commission(user_id, tenant_id, "PLEDGE_FULFILLED")

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TIME_PLEDGE_FULFILLED",
            resource_id=pledge.id,
            details={"hours": float(pledge.pledged_hours)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, fulfilled)

        return fulfilled

    # ========== إنشاء سيناريو مستقبلي ==========
    async def create_scenario(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> FutureScenario:
        await self._check_saas_limits(tenant_id, "zamakana")

        sanitized_title = bleach.clean(data.get("scenario_title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        scenario = await self.repo.create_scenario(
            tenant_id=tenant_id,
            created_by=user_id,
            scenario_title=sanitized_title,
            description=sanitized_description,
            target_year=data["target_year"],
            assumptions=data.get("assumptions", {})
        )

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="FUTURE_SCENARIO_CREATED",
            resource_id=scenario.id,
            details={"title": scenario.scenario_title, "year": scenario.target_year}
        )

        return scenario

    # ========== تحليل الذكاء الاصطناعي (الحقيقي) ==========
    async def generate_ai_analysis(
        self,
        scenario_id: int,
        tenant_id: int,
        user_id: int,
        ai_agent_id: int = 11,  # وكيل ZAMAKANA_ANALYST
        idempotency_key: str = None
    ) -> FutureScenario:
        await self._check_saas_limits(tenant_id, "zamakana")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        scenario = await self.repo.get_scenario(scenario_id, tenant_id)
        if not scenario or scenario.created_by != user_id:
            raise NotFoundError("Scenario not found or not yours")

        # التحقق من حوكمة الذكاء الاصطناعي
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=ai_agent_id,
            user_id=user_id,
            tokens=500,
            cost=Decimal("0.05")
        )

        # استدعاء وكيل الذكاء الاصطناعي الحقيقي
        try:
            prompt = f"""
            تحليل سيناريو مستقبلي: {scenario.scenario_title}
            الوصف: {scenario.description}
            السنة المستهدفة: {scenario.target_year}
            الافتراضات: {json.dumps(scenario.assumptions, indent=2)}
            قم بتقديم تحليل يتضمن:
            1. التأثيرات الاقتصادية المتوقعة
            2. التأثيرات البيئية
            3. التأثيرات الاجتماعية
            4. التوصيات للاستعداد لهذا السيناريو
            """

            ai_result = await self.ai_service.execute_agent_action(
                agent_id=ai_agent_id,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={"prompt": prompt, "scenario_id": scenario_id},
                executor_user_id=user_id
            )

            # استخراج التقرير من نتيجة الوكيل
            report = ai_result.get("result", {}).get("report", {
                "economic_impact": "تحليل اقتصادي متوقع",
                "environmental_impact": "تحليل بيئي متوقع",
                "social_impact": "تحليل اجتماعي متوقع",
                "recommendations": ["توصيات قائمة على التحليل"]
            })

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # خيار احتياطي
            report = {
                "economic_impact": "تعذر إجراء التحليل الاقتصادي",
                "environmental_impact": "تعذر إجراء التحليل البيئي",
                "social_impact": "تعذر إجراء التحليل الاجتماعي",
                "recommendations": ["يرجى إعادة المحاولة"],
                "error": str(e)
            }

        # إنشاء فاتورة لخدمة التحليل
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("10.00"),
            description=f"AI analysis for scenario: {scenario.scenario_title}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # تحديث السيناريو بالتقرير
        updated = await self.repo.update_ai_report(
            scenario_id,
            tenant_id,
            report,
            ai_agent_id
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("zamakana.scenario.analyzed", {
            "scenario_id": scenario.id,
            "tenant_id": tenant_id,
            "status": "HUMAN_REVIEW"
        })

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="SCENARIO_AI_ANALYZED",
            resource_id=scenario.id,
            details={"ai_agent_id": ai_agent_id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, updated)

        return updated

    # ========== دوال مساعدة ==========
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("2.00") if action_type in ["NODE_CREATED", "CAMPAIGN_CREATED"] else Decimal("1.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")