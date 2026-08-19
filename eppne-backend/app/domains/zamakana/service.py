# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

# app/domains/zamakana/service.py (الإصدار النهائي المتكامل المصحح)
"""
خدمات قطاع الزمكان – محرك المعرفة والتأثير عبر الزمن
يدعم: إنشاء عقد المعرفة، ربطها، الحملات الكوكبية، التعهدات الزمنية،
المحاكاة المستقبلية بالذكاء الاصطناعي، والمراجعة البشرية.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, cast
import uuid
import json
import bleach

from app.domains.zamakana.repository import ZamakanaRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.zamakana.models import (
    ZamakanaNode, ZamakanaEdge, PlanetaryCampaign, TimePledge,
    FutureScenario, HumanFeedback, PledgeStatus, ZamakanaNodeType
)


class ZamakanaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ZamakanaRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # 0. دوال Idempotency الموحّدة
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

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "zamakana"):
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        has_access = await saas_service.can_access_service(tenant_id, feature)
        if not has_access:
            raise PermissionDeniedError("Zamakana feature is not included in your current plan.")
        return None, {}

    # ============================================================
    # 1. العقد المعرفية (Nodes)
    # ============================================================
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

        await self._register_affiliate_commission(user_id, tenant_id, "NODE_CREATED")

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="ZAMAKANA_NODE_CREATED",
            resource_id=node.id,
            details={"title": node.title, "type": node.node_type.value}
        )

        await self.event_bus.publish("zamakana.node.created", {
            "node_id": node.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": node.title
        })

        return node

    async def list_nodes(
        self,
        tenant_id: int,
        node_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ZamakanaNode]:
        await self._check_saas_limits(tenant_id, "zamakana")
        result = await self.repo.list_nodes(tenant_id, node_type, skip, limit)
        return list(result)

    async def get_node(self, node_id: int, tenant_id: int) -> ZamakanaNode:
        node = await self.repo.get_node(node_id, tenant_id)
        if not node:
            raise NotFoundError("Node not found")
        return node

    async def update_node(
        self,
        node_id: int,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> ZamakanaNode:
        node = await self.repo.get_node(node_id, tenant_id)
        if not node or node.created_by != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to update this node")
        return await self.repo.update_node(node_id, tenant_id, **data)

    async def delete_node(self, node_id: int, tenant_id: int, user_id: int) -> None:
        node = await self.repo.get_node(node_id, tenant_id)
        if not node or node.created_by != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to delete this node")
        await self.repo.delete_node(node_id, tenant_id)

    # ============================================================
    # 2. الحواف المعرفية (Edges) – مع Idempotency محسّن
    # ============================================================
    async def create_edge(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ZamakanaEdge:
        await self._check_saas_limits(tenant_id, "zamakana")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                edge_id = cached.get("edge_id")
                if edge_id:
                    edge = await self.repo.get_edge(edge_id, tenant_id)
                    if edge:
                        return edge
                raise ValidationError("Idempotency record exists but edge not found.")

        source = await self.repo.get_node(data["source_node_id"], tenant_id)
        target = await self.repo.get_node(data["target_node_id"], tenant_id)
        if not source or not target:
            raise NotFoundError("One or both nodes not found")

        sanitized_description = bleach.clean(data.get("impact_description", ""), tags=[], strip=True)

        edge = await self.repo.create_edge(
            tenant_id=tenant_id,
            created_by=user_id,
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            impact_description=sanitized_description,
            impact_weight=data.get("impact_weight", Decimal(1.0)),
            is_alternative_timeline=data.get("is_alternative_timeline", False),
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="ZAMAKANA_EDGE_CREATED",
            resource_id=edge.id,
            details={"source": source.title, "target": target.title}
        )

        # تخزين معرف الحافة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"edge_id": edge.id})

        return edge

    # ============================================================
    # 3. الرسم البياني المعرفي
    # ============================================================
    async def get_knowledge_graph(
        self,
        tenant_id: int,
        node_type: Optional[str] = None,
        limit: int = 100
    ) -> dict:
        await self._check_saas_limits(tenant_id, "zamakana")
        return await self.repo.get_knowledge_graph_optimized(tenant_id, node_type, min(limit, 200))

    # ============================================================
    # 4. الحملات الكوكبية (Campaigns)
    # ============================================================
    async def create_campaign(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> PlanetaryCampaign:
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

        await self._register_affiliate_commission(user_id, tenant_id, "CAMPAIGN_CREATED")

        await audit_log(  # type: ignore[call-arg]
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

    async def list_campaigns(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PlanetaryCampaign]:
        await self._check_saas_limits(tenant_id, "zamakana")
        result = await self.repo.list_campaigns(tenant_id, status, skip, limit)
        return list(result)

    async def get_campaign(self, campaign_id: int, tenant_id: int) -> PlanetaryCampaign:
        campaign = await self.repo.get_campaign(campaign_id, tenant_id)
        if not campaign:
            raise NotFoundError("Campaign not found")
        return campaign

    # ============================================================
    # 5. التعهدات الزمنية (Pledges) – مع Idempotency محسّن
    # ============================================================
    async def pledge_time(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> TimePledge:
        await self._check_saas_limits(tenant_id, "zamakana")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                pledge_id = cached.get("pledge_id")
                if pledge_id:
                    pledge = await self.repo.get_pledge(pledge_id, tenant_id)
                    if pledge:
                        return pledge
                raise ValidationError("Idempotency record exists but pledge not found.")

        campaign = await self.repo.get_campaign(data["campaign_id"], tenant_id)
        if not campaign or campaign.status != "ACTIVE":  # type: ignore
            raise NotFoundError("Campaign not active or not found")

        if campaign.collected_time_hours >= campaign.target_time_hours:  # type: ignore
            raise PermissionDeniedError("Campaign already reached its target")

        invoicing_service = InvoicingService(self.db, tenant_id)
        async with self.db.begin_nested():
            pledge = await self.repo.create_pledge(
                tenant_id=tenant_id,
                campaign_id=data["campaign_id"],
                user_id=user_id,
                pledged_hours=data["pledged_hours"],
                skill_category=bleach.clean(data.get("skill_category", ""), tags=[], strip=True) if data.get("skill_category") else None,
                idempotency_key=idempotency_key
            )

            await audit_log(  # type: ignore[call-arg]
                user_id=user_id,
                tenant_id=tenant_id,
                action="TIME_PLEDGE_CREATED",
                resource_id=pledge.id,
                details={"campaign_id": campaign.id, "hours": float(pledge.pledged_hours)}
            )

        await self.db.commit()

        # إنشاء فاتورة (للخدمات المدفوعة) – إذا تجاوزت الساعات 10
        if pledge.pledged_hours > 10:  # type: ignore
            try:
                await invoicing_service.create_invoice(  # type: ignore[attr-defined]
                    entity_id=tenant_id,
                    user_id=user_id,
                    amount=Decimal("5.00"),
                    description=f"Time pledge registration for campaign {campaign.title}",
                    due_date=datetime.utcnow() + timedelta(days=30)
                )
            except Exception as e:
                logger.error(f"Invoice creation failed for time pledge {pledge.id}: {e}")

        # تخزين معرف التعهد فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"pledge_id": pledge.id})

        return pledge

    async def list_pledges(
        self,
        campaign_id: int,
        tenant_id: int,
        status: Optional[str] = None
    ) -> List[TimePledge]:
        await self._check_saas_limits(tenant_id, "zamakana")
        result = await self.repo.list_pledges(campaign_id, tenant_id, status)
        return list(result)

    # ============================================================
    # 6. تنفيذ التعهد – مع Idempotency محسّن
    # ============================================================
    async def fulfill_pledge(
        self,
        user_id: int,
        tenant_id: int,
        pledge_id: int,
        proof_hash: str,
        idempotency_key: Optional[str] = None
    ) -> TimePledge:
        await self._check_saas_limits(tenant_id, "zamakana")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                pledge_id_cached = cached.get("pledge_id")
                if pledge_id_cached:
                    pledge = await self.repo.get_pledge(pledge_id_cached, tenant_id)
                    if pledge:
                        return pledge
                raise ValidationError("Idempotency record exists but pledge not found.")

        pledge = await self.repo.get_pledge(pledge_id, tenant_id)
        if not pledge or pledge.user_id != user_id:  # type: ignore
            raise NotFoundError("Pledge not found or not yours")
        if pledge.status != "PENDING":  # type: ignore
            raise PermissionDeniedError("Pledge already fulfilled or cancelled")

        sanitized_proof = bleach.clean(proof_hash, tags=[], strip=True)

        async with self.db.begin_nested():
            fulfilled = await self.repo.fulfill_pledge(pledge_id, tenant_id, sanitized_proof, user_id)

            # إضافة الساعات إلى الحملة
            campaign = await self.repo.get_campaign(pledge.campaign_id, tenant_id)  # type: ignore
            if campaign:
                await self.repo.add_collected_hours(campaign.id, tenant_id, float(pledge.pledged_hours))

                # إذا اكتملت الحملة
                if campaign.collected_time_hours >= campaign.target_time_hours:  # type: ignore
                    await self.repo.update_campaign(campaign.id, tenant_id, status="COMPLETED")
                    await self.event_bus.publish("zamakana.campaign.completed", {
                        "campaign_id": campaign.id,
                        "tenant_id": tenant_id,
                        "title": campaign.title,
                        "total_hours": float(campaign.collected_time_hours)
                    })

            await self._register_affiliate_commission(user_id, tenant_id, "PLEDGE_FULFILLED")

            await audit_log(  # type: ignore[call-arg]
                user_id=user_id,
                tenant_id=tenant_id,
                action="TIME_PLEDGE_FULFILLED",
                resource_id=pledge.id,
                details={"hours": float(pledge.pledged_hours)}
            )

        await self.db.commit()

        # تخزين معرف التعهد فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"pledge_id": pledge.id})

        return fulfilled

    # ============================================================
    # 7. السيناريوهات المستقبلية (Scenarios)
    # ============================================================
    async def create_scenario(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> FutureScenario:
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

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="FUTURE_SCENARIO_CREATED",
            resource_id=scenario.id,
            details={"title": scenario.scenario_title, "year": scenario.target_year}
        )

        return scenario

    async def list_scenarios(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[FutureScenario]:
        await self._check_saas_limits(tenant_id, "zamakana")
        result = await self.repo.list_scenarios(tenant_id, status, skip, limit)
        return list(result)

    async def get_scenario(self, scenario_id: int, tenant_id: int) -> FutureScenario:
        scenario = await self.repo.get_scenario(scenario_id, tenant_id)
        if not scenario:
            raise NotFoundError("Scenario not found")
        return scenario

    # ============================================================
    # 8. تحليل الذكاء الاصطناعي – مع Idempotency محسّن
    # ============================================================
    async def generate_ai_analysis(
        self,
        scenario_id: int,
        tenant_id: int,
        user_id: int,
        ai_agent_id: int = 11,
        idempotency_key: Optional[str] = None
    ) -> FutureScenario:
        await self._check_saas_limits(tenant_id, "zamakana")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                scenario_id_cached = cached.get("scenario_id")
                if scenario_id_cached:
                    scenario = await self.repo.get_scenario(scenario_id_cached, tenant_id)
                    if scenario:
                        return scenario
                raise ValidationError("Idempotency record exists but scenario not found.")

        scenario = await self.repo.get_scenario(scenario_id, tenant_id)
        if not scenario or scenario.created_by != user_id:  # type: ignore
            raise NotFoundError("Scenario not found or not yours")

        # التحقق من حوكمة الذكاء الاصطناعي
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db, tenant_id)
        await governance.check_and_consume(
            agent_id=ai_agent_id,
            user_id=user_id,
            action_type="SCENARIO_ANALYSIS",
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

            ai_service = AIAgentsService(self.db, tenant_id)
            ai_result = await ai_service.execute_agent_action(
                agent_id=ai_agent_id,
                action_type="ANALYZE_SENSOR",
                payload={"prompt": prompt, "scenario_id": scenario_id},
                executor_user_id=user_id,
                idempotency_key=f"AI-SCENARIO-T{tenant_id}-{scenario_id}"
            )

            report = ai_result.get("result", {}).get("report", {
                "economic_impact": "تحليل اقتصادي متوقع",
                "environmental_impact": "تحليل بيئي متوقع",
                "social_impact": "تحليل اجتماعي متوقع",
                "recommendations": ["توصيات قائمة على التحليل"]
            })

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            report = {
                "economic_impact": "تعذر إجراء التحليل الاقتصادي",
                "environmental_impact": "تعذر إجراء التحليل البيئي",
                "social_impact": "تعذر إجراء التحليل الاجتماعي",
                "recommendations": ["يرجى إعادة المحاولة"],
                "error": str(e)
            }

        # إنشاء فاتورة لخدمة التحليل
        invoicing_service = InvoicingService(self.db, tenant_id)
        await invoicing_service.create_invoice(  # type: ignore[attr-defined]
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("10.00"),
            description=f"AI analysis for scenario: {scenario.scenario_title}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        updated = await self.repo.update_ai_report(
            scenario_id,
            tenant_id,
            report,
            ai_agent_id
        )

        await self.event_bus.publish("zamakana.scenario.analyzed", {
            "scenario_id": scenario.id,
            "tenant_id": tenant_id,
            "status": "HUMAN_REVIEW"
        })

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="SCENARIO_AI_ANALYZED",
            resource_id=scenario.id,
            details={"ai_agent_id": ai_agent_id}
        )

        # تخزين معرف السيناريو فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"scenario_id": updated.id})

        return updated

    async def add_human_feedback(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> HumanFeedback:
        # التحقق من وجود السيناريو
        scenario = await self.repo.get_scenario(data["scenario_id"], data.get("tenant_id", 0))
        if not scenario:
            raise NotFoundError("Scenario not found")

        sanitized_text = bleach.clean(data.get("feedback_text", ""), tags=[], strip=True)

        feedback = await self.repo.create_feedback(
            tenant_id=data.get("tenant_id", 0),
            scenario_id=data["scenario_id"],
            reviewer_id=user_id,
            feedback_text=sanitized_text,
            agreement_score=data.get("agreement_score"),
            idempotency_key=data.get("idempotency_key")
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=data.get("tenant_id", 0),
            action="HUMAN_FEEDBACK_ADDED",
            resource_id=feedback.id,
            details={"scenario_id": data["scenario_id"]}
        )

        return feedback

    async def confirm_scenario(
        self,
        scenario_id: int,
        user_id: int,
        tenant_id: int
    ) -> FutureScenario:
        scenario = await self.repo.get_scenario(scenario_id, tenant_id)
        if not scenario or scenario.created_by != user_id:  # type: ignore
            raise NotFoundError("Scenario not found or not yours")
        if scenario.status == "DRAFTING":  # type: ignore
            raise PermissionDeniedError("Scenario not yet analyzed by AI")

        updated = await self.repo.update_scenario(
            scenario_id,
            tenant_id,
            status="CONFIRMED"
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="SCENARIO_CONFIRMED",
            resource_id=scenario_id,
            details={"title": scenario.scenario_title}
        )

        return updated

    # ============================================================
    # 9. دوال مساعدة
    # ============================================================
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by:
                commission = Decimal("2.00") if action_type in ["NODE_CREATED", "CAMPAIGN_CREATED"] else Decimal("1.00")
                await affiliate_service.register_commission(  # type: ignore[attr-defined]
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")