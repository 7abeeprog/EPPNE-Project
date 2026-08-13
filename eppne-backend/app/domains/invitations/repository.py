# app/domains/invitations/repository.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domains.invitations.models import (
    SovereignInvitation, InvitationTracking, InvitationConversation, ClientInsight,
    InvitationStatus,
    Lead, CustomerInteraction, MarketingCampaign, SupportTicket, TicketComment,
    LeadStatus, LeadSource, CampaignStatus, CampaignType, TicketStatus
)
from app.core.errors import NotFoundError


class InvitationsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. الدعوات (Invitations)
    # ============================================================

    async def create_invitation(self, **kwargs) -> SovereignInvitation:
        inv = SovereignInvitation(**kwargs)
        self.db.add(inv)
        await self.db.flush()
        await self.db.refresh(inv)
        return inv

    async def get_invitation(self, inv_id: int, tenant_id: int) -> Optional[SovereignInvitation]:
        result = await self.db.execute(
            select(SovereignInvitation).where(
                SovereignInvitation.id == inv_id,  # type: ignore
                SovereignInvitation.tenant_id == tenant_id,  # type: ignore
                SovereignInvitation.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_invitations(
        self,
        tenant_id: int,
        status: Optional[InvitationStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignInvitation]:
        query = select(SovereignInvitation).where(
            SovereignInvitation.tenant_id == tenant_id,  # type: ignore
            SovereignInvitation.is_deleted == False  # type: ignore
        )
        if status:
            query = query.where(SovereignInvitation.status == status)  # type: ignore
        if campaign_type:
            query = query.where(SovereignInvitation.campaign_type == campaign_type)  # type: ignore
        query = query.order_by(SovereignInvitation.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_invitation(self, inv_id: int, tenant_id: int, **kwargs) -> SovereignInvitation:
        await self.db.execute(
            update(SovereignInvitation).where(
                SovereignInvitation.id == inv_id,  # type: ignore
                SovereignInvitation.tenant_id == tenant_id  # type: ignore
            ).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_invitation(inv_id, tenant_id)

    async def delete_invitation(self, inv_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(SovereignInvitation).where(
                SovereignInvitation.id == inv_id,  # type: ignore
                SovereignInvitation.tenant_id == tenant_id  # type: ignore
            ).values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    async def increment_clicks(self, inv_id: int) -> None:
        inv = await self.db.execute(select(SovereignInvitation).where(SovereignInvitation.id == inv_id))  # type: ignore
        inv = inv.scalar_one_or_none()
        if inv:
            inv.click_count += 1  # type: ignore
            if inv.first_clicked_at is None:  # type: ignore
                inv.first_clicked_at = func.now()  # type: ignore
            inv.last_clicked_at = func.now()  # type: ignore
            await self.db.commit()

    # ============================================================
    # 2. التتبع والمحادثات (Tracking & Conversations)
    # ============================================================

    async def create_tracking(self, **kwargs) -> InvitationTracking:
        track = InvitationTracking(**kwargs)
        self.db.add(track)
        await self.db.flush()
        await self.db.refresh(track)
        return track

    async def list_tracking(self, invitation_id: int, tenant_id: int) -> List[InvitationTracking]:
        result = await self.db.execute(
            select(InvitationTracking).where(
                InvitationTracking.invitation_id == invitation_id,  # type: ignore
                InvitationTracking.tenant_id == tenant_id  # type: ignore
            ).order_by(InvitationTracking.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_conversation(self, **kwargs) -> InvitationConversation:
        conv = InvitationConversation(**kwargs)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def get_conversations(self, invitation_id: int, tenant_id: int, limit: int = 50) -> List[InvitationConversation]:
        result = await self.db.execute(
            select(InvitationConversation).where(
                InvitationConversation.invitation_id == invitation_id,  # type: ignore
                InvitationConversation.tenant_id == tenant_id  # type: ignore
            ).order_by(InvitationConversation.created_at).limit(limit)
        )
        return list(result.scalars().all())

    async def create_client_insight(self, **kwargs) -> ClientInsight:
        insight = ClientInsight(**kwargs)
        self.db.add(insight)
        await self.db.commit()
        await self.db.refresh(insight)
        return insight

    async def get_client_insight(self, invitation_id: int, tenant_id: int) -> Optional[ClientInsight]:
        result = await self.db.execute(
            select(ClientInsight).where(
                ClientInsight.invitation_id == invitation_id,  # type: ignore
                ClientInsight.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 3. العملاء المحتملون (Leads)
    # ============================================================

    async def create_lead(self, **kwargs) -> Lead:
        lead = Lead(**kwargs)
        self.db.add(lead)
        await self.db.flush()
        await self.db.refresh(lead)
        return lead

    async def get_lead(self, lead_id: int, tenant_id: int) -> Optional[Lead]:
        result = await self.db.execute(
            select(Lead).where(
                Lead.id == lead_id,  # type: ignore
                Lead.tenant_id == tenant_id,  # type: ignore
                Lead.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def get_lead_by_user(self, user_id: int, tenant_id: int) -> Optional[Lead]:
        result = await self.db.execute(
            select(Lead).where(
                Lead.converted_user_id == user_id,  # type: ignore
                Lead.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        tenant_id: int,
        status: Optional[LeadStatus] = None,
        source: Optional[LeadSource] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Lead]:
        query = select(Lead).where(Lead.tenant_id == tenant_id, Lead.is_deleted == False)  # type: ignore
        if status:
            query = query.where(Lead.status == status)  # type: ignore
        if source:
            query = query.where(Lead.source == source)  # type: ignore
        query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_lead(self, lead_id: int, tenant_id: int, **kwargs) -> Lead:
        await self.db.execute(
            update(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id).values(**kwargs)  # type: ignore
        )
        await self.db.commit()
        return await self.get_lead(lead_id, tenant_id)

    async def delete_lead(self, lead_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id).values(  # type: ignore
                is_deleted=True, deleted_at=func.now()
            )
        )
        await self.db.commit()

    # ============================================================
    # 4. تفاعلات العملاء (Interactions)
    # ============================================================

    async def create_interaction(self, **kwargs) -> CustomerInteraction:
        interaction = CustomerInteraction(**kwargs)
        self.db.add(interaction)
        await self.db.flush()
        await self.db.refresh(interaction)
        return interaction

    async def list_interactions(self, lead_id: int, tenant_id: int, limit: int = 50) -> List[CustomerInteraction]:
        result = await self.db.execute(
            select(CustomerInteraction).where(
                CustomerInteraction.lead_id == lead_id,  # type: ignore
                CustomerInteraction.tenant_id == tenant_id  # type: ignore
            ).order_by(CustomerInteraction.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    # ============================================================
    # 5. الحملات التسويقية (Campaigns)
    # ============================================================

    async def create_campaign(self, **kwargs) -> MarketingCampaign:
        campaign = MarketingCampaign(**kwargs)
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def get_campaign(self, campaign_id: int, tenant_id: int) -> Optional[MarketingCampaign]:
        result = await self.db.execute(
            select(MarketingCampaign).where(
                MarketingCampaign.id == campaign_id,  # type: ignore
                MarketingCampaign.tenant_id == tenant_id,  # type: ignore
                MarketingCampaign.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_campaigns(
        self,
        tenant_id: int,
        status: Optional[CampaignStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MarketingCampaign]:
        query = select(MarketingCampaign).where(
            MarketingCampaign.tenant_id == tenant_id,  # type: ignore
            MarketingCampaign.is_deleted == False  # type: ignore
        )
        if status:
            query = query.where(MarketingCampaign.status == status)  # type: ignore
        if campaign_type:
            query = query.where(MarketingCampaign.campaign_type == campaign_type)  # type: ignore
        query = query.order_by(MarketingCampaign.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_campaign(self, campaign_id: int, tenant_id: int, **kwargs) -> MarketingCampaign:
        await self.db.execute(
            update(MarketingCampaign).where(
                MarketingCampaign.id == campaign_id,  # type: ignore
                MarketingCampaign.tenant_id == tenant_id  # type: ignore
            ).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_campaign(campaign_id, tenant_id)

    async def delete_campaign(self, campaign_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(MarketingCampaign).where(
                MarketingCampaign.id == campaign_id,  # type: ignore
                MarketingCampaign.tenant_id == tenant_id  # type: ignore
            ).values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ============================================================
    # 6. تذاكر الدعم (Support Tickets)
    # ============================================================

    async def create_ticket(self, **kwargs) -> SupportTicket:
        ticket = SupportTicket(**kwargs)
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def get_ticket(self, ticket_id: int, tenant_id: int) -> Optional[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket).where(
                SupportTicket.id == ticket_id,  # type: ignore
                SupportTicket.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_tickets(
        self,
        tenant_id: int,
        status: Optional[TicketStatus] = None,
        assigned_to: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportTicket]:
        query = select(SupportTicket).where(SupportTicket.tenant_id == tenant_id)  # type: ignore
        if status:
            query = query.where(SupportTicket.status == status)  # type: ignore
        if assigned_to:
            query = query.where(SupportTicket.assigned_to == assigned_to)  # type: ignore
        query = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_ticket(self, ticket_id: int, tenant_id: int, **kwargs) -> SupportTicket:
        await self.db.execute(
            update(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.tenant_id == tenant_id).values(**kwargs)  # type: ignore
        )
        await self.db.commit()
        return await self.get_ticket(ticket_id, tenant_id)

    async def update_ticket_status(self, ticket_id: int, tenant_id: int, status: TicketStatus) -> SupportTicket:
        values: Dict[str, Any] = {"status": status}
        if status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            values["resolved_at"] = datetime.utcnow()
        await self.db.execute(
            update(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.tenant_id == tenant_id).values(**values)  # type: ignore
        )
        await self.db.flush()
        return await self.get_ticket(ticket_id, tenant_id)

    async def create_ticket_comment(self, **kwargs) -> TicketComment:
        comment = TicketComment(**kwargs)
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def list_ticket_comments(self, ticket_id: int, tenant_id: int, limit: int = 50) -> List[TicketComment]:
        result = await self.db.execute(
            select(TicketComment).where(
                TicketComment.ticket_id == ticket_id,  # type: ignore
                TicketComment.tenant_id == tenant_id  # type: ignore
            ).order_by(TicketComment.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())