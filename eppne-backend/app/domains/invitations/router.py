# app/domains/invitations/router.py (الإصدار النهائي المتكامل)
"""
مسارات (Endpoints) قطاع الدعوات وخدمة العملاء – النسخة الذهبية
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_user_optional
from app.domains.identity.models import User
from app.domains.invitations.service import InvitationsService
from app.domains.invitations.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/invitations", tags=["Sovereign CRM & Invitations"])


# ============================================================
# 1. الدعوات (Invitations)
# ============================================================

@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_invitation(
    data: InvitationCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    invitation = await service.create_invitation(
        sender_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key,
        analyze_target=True
    )
    invite_url = f"https://{tenant.domain}/invite/{invitation.id}"
    return {
        **invitation.__dict__,
        "invitation_url": invite_url
    }


@router.get("/", response_model=List[InvitationResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_invitations(
    status: Optional[InvitationStatus] = Query(None, description="حالة الدعوة"),
    campaign_type: Optional[CampaignType] = Query(None, description="نوع الحملة"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    invitations = await service.list_invitations(
        tenant_id=cast(int, tenant.id),
        status=status,
        campaign_type=campaign_type,
        skip=skip,
        limit=limit
    )
    return invitations


@router.get("/{invitation_id}", response_model=InvitationResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_invitation(
    request: Request,
    invitation_id: int,
    background_tasks: BackgroundTasks,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    invitation = await service.get_invitation(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id)
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    background_tasks.add_task(
        service.track_behavior,
        invitation_id,
        cast(int, tenant.id),
        {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "device_type": request.headers.get("sec-ch-ua-platform", "web"),
            "page_visited": "/invite",
            "actions": []
        }
    )
    return invitation


@router.put("/{invitation_id}", response_model=InvitationResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def update_invitation(
    invitation_id: int,
    data: InvitationUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    updated = await service.update_invitation(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump(exclude_unset=True)
    )
    return updated


@router.delete("/{invitation_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_invitation(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    await service.delete_invitation(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return {"message": "Invitation deleted"}


@router.post("/{invitation_id}/accept", response_model=InvitationAcceptResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def accept_invitation(
    invitation_id: int,
    data: InvitationAccept,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    user_id = cast(int, current_user.id) if current_user else None
    result = await service.accept_invitation(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id),
        accept_data=data.model_dump(),
        user_id=user_id,
        idempotency_key=idempotency_key
    )
    return result


@router.post("/{invitation_id}/chat", response_model=ConversationResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def chat_with_ai(
    request: Request,
    invitation_id: int,
    data: ConversationMessage,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    user_id = cast(int, current_user.id) if current_user else None
    visitor_session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    response = await service.chat_with_ai(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id),
        visitor_session_id=visitor_session_id,
        user_message=data.message,
        user_id=user_id,
        idempotency_key=idempotency_key
    )
    return response


@router.get("/{invitation_id}/tracking", response_model=List[InvitationTrackingResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_invitation_tracking(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    tracking = await service.get_invitation_tracking(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id)
    )
    return tracking


@router.get("/{invitation_id}/conversations", response_model=List[ConversationResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_invitation_conversations(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    conversations = await service.get_invitation_conversations(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id)
    )
    return conversations


@router.get("/{invitation_id}/insight", response_model=ClientInsightResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_client_insight(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    insight = await service.get_client_insight(
        invitation_id=invitation_id,
        tenant_id=cast(int, tenant.id)
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.get("/stats", response_model=InvitationStatsResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_invitation_stats(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    stats = await service.get_stats(
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return stats


# ============================================================
# 2. العملاء المحتملون (Leads)
# ============================================================

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_lead(
    data: LeadCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    lead = await service.create_lead(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return lead


@router.get("/leads", response_model=List[LeadResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_leads(
    status: Optional[LeadStatus] = Query(None, description="حالة العميل المحتمل"),
    source: Optional[LeadSource] = Query(None, description="مصدر العميل المحتمل"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    leads = await service.list_leads(
        tenant_id=cast(int, tenant.id),
        status=status,
        source=source,
        skip=skip,
        limit=limit
    )
    return leads


@router.get("/leads/{lead_id}", response_model=LeadResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_lead(
    lead_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    lead = await service.get_lead(
        lead_id=lead_id,
        tenant_id=cast(int, tenant.id)
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/leads/{lead_id}", response_model=LeadResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    updated = await service.update_lead(
        lead_id=lead_id,
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(exclude_unset=True)
    )
    return updated


@router.delete("/leads/{lead_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_lead(
    lead_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    await service.delete_lead(
        lead_id=lead_id,
        tenant_id=cast(int, tenant.id)
    )
    return {"message": "Lead deleted"}


@router.post("/leads/{lead_id}/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def create_interaction(
    lead_id: int,
    data: InteractionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    interaction = await service.create_interaction(
        lead_id=lead_id,
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return interaction


@router.get("/leads/{lead_id}/interactions", response_model=List[InteractionResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_lead_interactions(
    lead_id: int,
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    interactions = await service.get_lead_interactions(
        lead_id=lead_id,
        tenant_id=cast(int, tenant.id),
        limit=limit
    )
    return interactions


# ============================================================
# 3. الحملات التسويقية (Campaigns)
# ============================================================

@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_campaign(
    data: CampaignCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    campaign = await service.create_campaign(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return campaign


@router.get("/campaigns", response_model=List[CampaignResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_campaigns(
    status: Optional[CampaignStatus] = Query(None, description="حالة الحملة"),
    campaign_type: Optional[CampaignType] = Query(None, description="نوع الحملة"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    campaigns = await service.list_campaigns(
        tenant_id=cast(int, tenant.id),
        status=status,
        campaign_type=campaign_type,
        skip=skip,
        limit=limit
    )
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    campaign = await service.get_campaign(
        campaign_id=campaign_id,
        tenant_id=cast(int, tenant.id)
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    campaign = await service.update_campaign(
        campaign_id=campaign_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump(exclude_unset=True)
    )
    return campaign


@router.delete("/campaigns/{campaign_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    await service.delete_campaign(
        campaign_id=campaign_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return {"message": "Campaign deleted"}


@router.post("/campaigns/{campaign_id}/launch", response_model=CampaignResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def launch_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    campaign = await service.launch_campaign(
        campaign_id=campaign_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return campaign


# ============================================================
# 4. تذاكر الدعم (Support Tickets)
# ============================================================

@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_ticket(
    data: TicketCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    ticket = await service.create_ticket(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        lead_id=data.lead_id,
        idempotency_key=idempotency_key
    )
    return ticket


@router.get("/tickets", response_model=List[TicketResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_tickets(
    status: Optional[TicketStatus] = Query(None, description="حالة التذكرة"),
    assigned_to: Optional[int] = Query(None, description="معرف المسؤول المعين"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    tickets = await service.list_tickets(
        tenant_id=cast(int, tenant.id),
        status=status,
        assigned_to=assigned_to,
        skip=skip,
        limit=limit
    )
    return tickets


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_ticket(
    ticket_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    ticket = await service.get_ticket(
        ticket_id=ticket_id,
        tenant_id=cast(int, tenant.id)
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    updated = await service.update_ticket(
        ticket_id=ticket_id,
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(exclude_unset=True)
    )
    return updated


@router.post("/tickets/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def add_ticket_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    comment = await service.add_ticket_comment(
        ticket_id=ticket_id,
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return comment


@router.get("/tickets/{ticket_id}/comments", response_model=List[TicketCommentResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_ticket_comments(
    ticket_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    comments = await service.get_ticket_comments(
        ticket_id=ticket_id,
        tenant_id=cast(int, tenant.id)
    )
    return comments


# ============================================================
# 5. التتبع والتحليلات (Tracking & Analytics)
# ============================================================

@router.post("/tracking", response_model=InvitationTrackingResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=50, window_seconds=60)
async def track_invitation(
    request: Request,
    data: InvitationTrackingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    service = InvitationsService(db)
    tracking = await service.track_behavior(
        invitation_id=data.invitation_id,
        tenant_id=cast(int, tenant.id),
        request_data={
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "device_type": request.headers.get("sec-ch-ua-platform", "web"),
            "page_visited": data.page_visited or "/invite",
            "actions": data.actions or []
        },
        idempotency_key=idempotency_key
    )
    return tracking
