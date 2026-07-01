# app/domains/zamakana/repository.py (الإصدار النهائي المتكامل)
"""
مستودع قطاع الزمكان – عمليات CRUD للعقد، الحواف، الحملات، التعهدات، والسيناريوهات.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domains.zamakana.models import (
    ZamakanaNode, ZamakanaEdge, PlanetaryCampaign, TimePledge,
    FutureScenario, HumanFeedback, PledgeStatus
)
from app.core.errors import NotFoundError


class ZamakanaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Nodes (مع العزل) ==========
    async def create_node(self, **kwargs) -> ZamakanaNode:
        node = ZamakanaNode(**kwargs)
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def get_node(self, node_id: int, tenant_id: int) -> Optional[ZamakanaNode]:
        result = await self.db.execute(
            select(ZamakanaNode).where(
                ZamakanaNode.id == node_id,
                ZamakanaNode.tenant_id == tenant_id,
                ZamakanaNode.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_nodes(
        self,
        tenant_id: int,
        node_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ZamakanaNode]:
        query = select(ZamakanaNode).where(
            ZamakanaNode.tenant_id == tenant_id,
            ZamakanaNode.is_deleted == False
        )
        if node_type:
            query = query.where(ZamakanaNode.node_type == node_type)
        query = query.order_by(ZamakanaNode.timeline_year).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_node(self, node_id: int, tenant_id: int, **kwargs) -> ZamakanaNode:
        await self.db.execute(
            update(ZamakanaNode)
            .where(ZamakanaNode.id == node_id, ZamakanaNode.tenant_id == tenant_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_node(node_id, tenant_id)

    async def delete_node(self, node_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(ZamakanaNode)
            .where(ZamakanaNode.id == node_id, ZamakanaNode.tenant_id == tenant_id)
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ========== Edges (مع العزل + Idempotency) ==========
    async def create_edge(self, **kwargs) -> ZamakanaEdge:
        edge = ZamakanaEdge(**kwargs)
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def get_edge_by_idempotency(self, idempotency_key: str) -> Optional[ZamakanaEdge]:
        result = await self.db.execute(
            select(ZamakanaEdge).where(ZamakanaEdge.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_edges_from_node(self, node_id: int, tenant_id: int) -> List[ZamakanaEdge]:
        result = await self.db.execute(
            select(ZamakanaEdge)
            .where(ZamakanaEdge.source_node_id == node_id, ZamakanaEdge.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def get_edges_to_node(self, node_id: int, tenant_id: int) -> List[ZamakanaEdge]:
        result = await self.db.execute(
            select(ZamakanaEdge)
            .where(ZamakanaEdge.target_node_id == node_id, ZamakanaEdge.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def delete_edge(self, edge_id: int, tenant_id: int) -> None:
        await self.db.execute(
            delete(ZamakanaEdge)
            .where(ZamakanaEdge.id == edge_id, ZamakanaEdge.tenant_id == tenant_id)
        )
        await self.db.commit()

    # ========== Planetary Campaigns ==========
    async def create_campaign(self, **kwargs) -> PlanetaryCampaign:
        campaign = PlanetaryCampaign(**kwargs)
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def get_campaign(self, campaign_id: int, tenant_id: int) -> Optional[PlanetaryCampaign]:
        result = await self.db.execute(
            select(PlanetaryCampaign).where(
                PlanetaryCampaign.id == campaign_id,
                PlanetaryCampaign.tenant_id == tenant_id,
                PlanetaryCampaign.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_campaigns(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PlanetaryCampaign]:
        query = select(PlanetaryCampaign).where(
            PlanetaryCampaign.tenant_id == tenant_id,
            PlanetaryCampaign.is_deleted == False
        )
        if status:
            query = query.where(PlanetaryCampaign.status == status)
        query = query.order_by(PlanetaryCampaign.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_campaign(self, campaign_id: int, tenant_id: int, **kwargs) -> PlanetaryCampaign:
        await self.db.execute(
            update(PlanetaryCampaign)
            .where(PlanetaryCampaign.id == campaign_id, PlanetaryCampaign.tenant_id == tenant_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_campaign(campaign_id, tenant_id)

    async def add_collected_hours(self, campaign_id: int, tenant_id: int, hours: float) -> PlanetaryCampaign:
        campaign = await self.get_campaign(campaign_id, tenant_id)
        if campaign:
            campaign.collected_time_hours = (campaign.collected_time_hours or 0) + hours
            await self.db.commit()
            await self.db.refresh(campaign)
        return campaign

    # ========== Time Pledges (مع العزل + Idempotency) ==========
    async def create_pledge(self, **kwargs) -> TimePledge:
        pledge = TimePledge(**kwargs)
        self.db.add(pledge)
        await self.db.commit()
        await self.db.refresh(pledge)
        return pledge

    async def get_pledge(self, pledge_id: int, tenant_id: int) -> Optional[TimePledge]:
        result = await self.db.execute(
            select(TimePledge).where(TimePledge.id == pledge_id, TimePledge.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_pledge_by_idempotency(self, idempotency_key: str) -> Optional[TimePledge]:
        result = await self.db.execute(
            select(TimePledge).where(TimePledge.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def list_pledges(
        self,
        campaign_id: int,
        tenant_id: int,
        status: Optional[str] = None
    ) -> List[TimePledge]:
        query = select(TimePledge).where(
            TimePledge.campaign_id == campaign_id,
            TimePledge.tenant_id == tenant_id
        )
        if status:
            query = query.where(TimePledge.status == status)
        query = query.order_by(TimePledge.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def fulfill_pledge(
        self,
        pledge_id: int,
        tenant_id: int,
        proof_hash: str,
        verifier_id: int
    ) -> TimePledge:
        await self.db.execute(
            update(TimePledge)
            .where(TimePledge.id == pledge_id, TimePledge.tenant_id == tenant_id)
            .values(
                status=PledgeStatus.FULFILLED,
                proof_hash=proof_hash,
                verified_by=verifier_id,
                verified_at=func.now()
            )
        )
        await self.db.commit()
        return await self.get_pledge(pledge_id, tenant_id)

    # ========== Future Scenarios ==========
    async def create_scenario(self, **kwargs) -> FutureScenario:
        scenario = FutureScenario(**kwargs)
        self.db.add(scenario)
        await self.db.commit()
        await self.db.refresh(scenario)
        return scenario

    async def get_scenario(self, scenario_id: int, tenant_id: int) -> Optional[FutureScenario]:
        result = await self.db.execute(
            select(FutureScenario).where(
                FutureScenario.id == scenario_id,
                FutureScenario.tenant_id == tenant_id,
                FutureScenario.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_scenarios(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[FutureScenario]:
        query = select(FutureScenario).where(
            FutureScenario.tenant_id == tenant_id,
            FutureScenario.is_deleted == False
        )
        if status:
            query = query.where(FutureScenario.status == status)
        query = query.order_by(FutureScenario.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_scenario(self, scenario_id: int, tenant_id: int, **kwargs) -> FutureScenario:
        await self.db.execute(
            update(FutureScenario)
            .where(FutureScenario.id == scenario_id, FutureScenario.tenant_id == tenant_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_scenario(scenario_id, tenant_id)

    async def update_ai_report(
        self,
        scenario_id: int,
        tenant_id: int,
        report: dict,
        agent_id: int
    ) -> FutureScenario:
        await self.db.execute(
            update(FutureScenario)
            .where(FutureScenario.id == scenario_id, FutureScenario.tenant_id == tenant_id)
            .values(
                ai_analysis_report=report,
                ai_agent_id=agent_id,
                status="HUMAN_REVIEW"
            )
        )
        await self.db.commit()
        return await self.get_scenario(scenario_id, tenant_id)

    # ========== Human Feedback ==========
    async def create_feedback(self, **kwargs) -> HumanFeedback:
        feedback = HumanFeedback(**kwargs)
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def list_feedbacks(self, scenario_id: int, tenant_id: int) -> List[HumanFeedback]:
        result = await self.db.execute(
            select(HumanFeedback).where(
                HumanFeedback.scenario_id == scenario_id,
                HumanFeedback.tenant_id == tenant_id
            )
        )
        return result.scalars().all()

    # ========== Knowledge Graph (محسّن لمنع N+1) ==========
    async def get_knowledge_graph_optimized(
        self,
        tenant_id: int,
        node_type: Optional[str] = None,
        limit: int = 100
    ) -> dict:
        """استرجاع الرسم البياني المعرفي مع تحميل الحواف دفعة واحدة."""
        # جلب العقد
        query = select(ZamakanaNode).where(
            ZamakanaNode.tenant_id == tenant_id,
            ZamakanaNode.is_deleted == False
        )
        if node_type:
            query = query.where(ZamakanaNode.node_type == node_type)
        query = query.limit(limit)
        result = await self.db.execute(query)
        nodes = result.scalars().all()

        if not nodes:
            return {"nodes": [], "edges": []}

        # جلب الحواف دفعة واحدة (استعلام واحد بدلاً من N+1)
        node_ids = [n.id for n in nodes]
        edge_result = await self.db.execute(
            select(ZamakanaEdge).where(
                ZamakanaEdge.tenant_id == tenant_id,
                (ZamakanaEdge.source_node_id.in_(node_ids)) |
                (ZamakanaEdge.target_node_id.in_(node_ids))
            )
        )
        edges = edge_result.scalars().all()

        # بناء النتيجة
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.node_type.value,
                    "title": n.title,
                    "year": n.timeline_year,
                    "location": n.geo_location
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "weight": float(e.impact_weight),
                    "alternative": e.is_alternative_timeline,
                    "description": e.impact_description
                }
                for e in edges
            ]
        }