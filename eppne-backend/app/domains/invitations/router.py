# app/domains/invitations/router.py (الإصدار النهائي المتكامل)
"""
مسارات (Endpoints) قطاع الدعوات وخدمة العملاء – النسخة الذهبية
تدعم: الدعوات، العملاء المحتملين (Leads)، الحملات التسويقية، تذاكر الدعم، التفاعلات، والمحادثات الذكية
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_user_optional
from app.domains.identity.models import User
from app.domains.invitations.service import InvitationsService
from app.domains.invitations.repository import InvitationsRepository
from app.domains.invitations.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/invitations", tags=["Sovereign CRM & Invitations"])


# ============================================================================
# 1. الدعوات (Invitations)
# ============================================================================

@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def create_invitation(
    data: InvitationCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء دعوة جديدة مع تحليل الذكاء الاصطناعي للهدف.
    """
    service = InvitationsService(db)
    invitation = await service.create_invitation(
        sender_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key,
        analyze_target=True
    )
    # توليد رابط الدعوة
    invite_url = f"https://{tenant.domain}/invite/{invitation.id}"
    return {
        **invitation.__dict__,
        "invitation_url": invite_url
    }


@router.get("/", response_model=List[InvitationResponse])
@rate_limit(max_requests=30, window=60)
async def list_invitations(
    status: Optional[InvitationStatus] = None,
    campaign_type: Optional[CampaignType] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    قائمة الدعوات الخاصة بالمستأجر الحالي.
    """
    repo = InvitationsRepository(db)
    invitations = await repo.list_invitations(tenant.id, status, campaign_type, skip, min(limit, 200))
    return invitations


@router.get("/{invitation_id}", response_model=InvitationResponse)
@rate_limit(max_requests=50, window=60)
async def get_invitation(
    invitation_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تفاصيل دعوة محددة مع تتبع الزيارة.
    """
    service = InvitationsService(db)
    invitation = await service.repo.get_invitation(invitation_id, tenant.id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # تتبع الزيارة في الخلفية (للصفحة العامة)
    background_tasks.add_task(
        service.track_behavior,
        invitation_id,
        tenant.id,
        {
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "device_type": request.headers.get("sec-ch-ua-platform", "web"),
            "page_visited": "/invite",
            "actions": []
        }
    )
    return invitation


@router.put("/{invitation_id}", response_model=InvitationResponse)
@rate_limit(max_requests=20, window=60)
async def update_invitation(
    invitation_id: int,
    data: InvitationUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث دعوة موجودة (يتطلب أن يكون المستخدم هو منشئها).
    """
    service = InvitationsService(db)
    invitation = await service.repo.get_invitation(invitation_id, tenant.id)
    if not invitation or invitation.sender_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await service.repo.update_invitation(invitation_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/{invitation_id}")
@rate_limit(max_requests=10, window=60)
async def delete_invitation(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    حذف دعوة (يتطلب أن يكون المستخدم هو منشئها).
    """
    service = InvitationsService(db)
    invitation = await service.repo.get_invitation(invitation_id, tenant.id)
    if not invitation or invitation.sender_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await service.repo.delete_invitation(invitation_id, tenant.id)
    return {"message": "Invitation deleted"}


@router.post("/{invitation_id}/accept", response_model=InvitationAcceptResponse)
@rate_limit(max_requests=10, window=60)
async def accept_invitation(
    invitation_id: int,
    data: InvitationAccept,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    قبول الدعوة (تحويل العميل إلى Lead).
    """
    service = InvitationsService(db)
    user_id = current_user.id if current_user else None
    result = await service.accept_invitation(
        invitation_id=invitation_id,
        tenant_id=tenant.id,
        accept_data=data.model_dump(),
        user_id=user_id,
        idempotency_key=idempotency_key
    )
    return result


@router.post("/{invitation_id}/chat", response_model=ConversationResponse)
@rate_limit(max_requests=30, window=60)
async def chat_with_ai(
    invitation_id: int,
    data: ConversationMessage,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    محادثة مع وكيل الذكاء الاصطناعي (مدعوم بـ AI Governance).
    """
    service = InvitationsService(db)
    user_id = current_user.id if current_user else None
    visitor_session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    response = await service.chat_with_ai(
        invitation_id=invitation_id,
        tenant_id=tenant.id,
        visitor_session_id=visitor_session_id,
        user_message=data.message,
        user_id=user_id,
        idempotency_key=idempotency_key
    )
    return response


@router.get("/{invitation_id}/tracking", response_model=List[InvitationTrackingResponse])
@rate_limit(max_requests=30, window=60)
async def get_invitation_tracking(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب بيانات تتبع سلوك المدعو.
    """
    repo = InvitationsRepository(db)
    tracking = await repo.list_tracking(invitation_id, tenant.id)
    return tracking


@router.get("/{invitation_id}/conversations", response_model=List[ConversationResponse])
@rate_limit(max_requests=30, window=60)
async def get_invitation_conversations(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب محادثات العميل مع وكيل الذكاء الاصطناعي.
    """
    repo = InvitationsRepository(db)
    conversations = await repo.get_conversations(invitation_id, tenant.id)
    return conversations


@router.get("/{invitation_id}/insight", response_model=ClientInsightResponse)
@rate_limit(max_requests=20, window=60)
async def get_client_insight(
    invitation_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تحليلات الذكاء الاصطناعي للعميل المستهدف.
    """
    repo = InvitationsRepository(db)
    insight = await repo.get_client_insight(invitation_id, tenant.id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.get("/stats", response_model=InvitationStatsResponse)
@rate_limit(max_requests=20, window=60)
async def get_invitation_stats(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إحصائيات الدعوات والحملات والعملاء.
    """
    service = InvitationsService(db)
    stats = await service.get_stats(tenant.id, current_user.id)
    return stats


# ============================================================================
# 2. العملاء المحتملون (Leads) – CRM Core
# ============================================================================

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def create_lead(
    data: LeadCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إضافة عميل محتمل جديد (يدوياً أو من مصدر خارجي).
    """
    service = InvitationsService(db)
    lead = await service.create_lead(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return lead


@router.get("/leads", response_model=List[LeadResponse])
@rate_limit(max_requests=30, window=60)
async def list_leads(
    status: Optional[LeadStatus] = None,
    source: Optional[LeadSource] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    قائمة العملاء المحتملين مع التصفية حسب الحالة والمصدر.
    """
    repo = InvitationsRepository(db)
    leads = await repo.list_leads(tenant.id, status, source, skip, min(limit, 200))
    return leads


@router.get("/leads/{lead_id}", response_model=LeadResponse)
@rate_limit(max_requests=50, window=60)
async def get_lead(
    lead_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تفاصيل عميل محتمل مع جميع التفاعلات.
    """
    repo = InvitationsRepository(db)
    lead = await repo.get_lead(lead_id, tenant.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/leads/{lead_id}", response_model=LeadResponse)
@rate_limit(max_requests=20, window=60)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث بيانات العميل المحتمل أو حالته.
    """
    repo = InvitationsRepository(db)
    lead = await repo.get_lead(lead_id, tenant.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    updated = await repo.update_lead(lead_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/leads/{lead_id}")
@rate_limit(max_requests=10, window=60)
async def delete_lead(
    lead_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    حذف عميل محتمل (حذف منطقي).
    """
    repo = InvitationsRepository(db)
    lead = await repo.get_lead(lead_id, tenant.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await repo.delete_lead(lead_id, tenant.id)
    return {"message": "Lead deleted"}


# ============================================================================
# 3. تفاعلات العملاء (Interactions)
# ============================================================================

@router.post("/leads/{lead_id}/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window=60)
async def create_interaction(
    lead_id: int,
    data: InteractionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تسجيل تفاعل جديد مع العميل (مكالمة، بريد، اجتماع، إلخ).
    """
    service = InvitationsService(db)
    interaction = await service.create_interaction(
        lead_id=lead_id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return interaction


@router.get("/leads/{lead_id}/interactions", response_model=List[InteractionResponse])
@rate_limit(max_requests=30, window=60)
async def get_lead_interactions(
    lead_id: int,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب جميع تفاعلات العميل (مرتبة تنازلياً حسب التاريخ).
    """
    repo = InvitationsRepository(db)
    interactions = await repo.list_interactions(lead_id, tenant.id, min(limit, 200))
    return interactions


# ============================================================================
# 4. الحملات التسويقية (Campaigns)
# ============================================================================

@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_campaign(
    data: CampaignCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء حملة تسويقية جديدة (مع دفع الميزانية المطلوبة).
    """
    service = InvitationsService(db)
    campaign = await service.create_campaign(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return campaign


@router.get("/campaigns", response_model=List[CampaignResponse])
@rate_limit(max_requests=30, window=60)
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    campaign_type: Optional[CampaignType] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    قائمة الحملات التسويقية مع التصفية حسب الحالة والنوع.
    """
    repo = InvitationsRepository(db)
    campaigns = await repo.list_campaigns(tenant.id, status, campaign_type, skip, min(limit, 200))
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
@rate_limit(max_requests=50, window=60)
async def get_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تفاصيل حملة تسويقية محددة مع إحصائيات الأداء.
    """
    repo = InvitationsRepository(db)
    campaign = await repo.get_campaign(campaign_id, tenant.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
@rate_limit(max_requests=10, window=60)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث حملة تسويقية (يتطلب أن يكون المستخدم هو منشئها).
    """
    repo = InvitationsRepository(db)
    campaign = await repo.get_campaign(campaign_id, tenant.id)
    if not campaign or campaign.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await repo.update_campaign(campaign_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/campaigns/{campaign_id}")
@rate_limit(max_requests=10, window=60)
async def delete_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    حذف حملة تسويقية (يتطلب أن يكون المستخدم هو منشئها).
    """
    repo = InvitationsRepository(db)
    campaign = await repo.get_campaign(campaign_id, tenant.id)
    if not campaign or campaign.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await repo.delete_campaign(campaign_id, tenant.id)
    return {"message": "Campaign deleted"}


@router.post("/campaigns/{campaign_id}/launch", response_model=CampaignResponse)
@rate_limit(max_requests=5, window=60)
async def launch_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إطلاق حملة (تغيير الحالة إلى ACTIVE).
    """
    service = InvitationsService(db)
    campaign = await service.launch_campaign(campaign_id, tenant.id, current_user.id)
    return campaign


# ============================================================================
# 5. تذاكر الدعم (Support Tickets)
# ============================================================================

@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def create_ticket(
    data: TicketCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء تذكرة دعم جديدة.
    """
    service = InvitationsService(db)
    ticket = await service.create_ticket(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return ticket


@router.get("/tickets", response_model=List[TicketResponse])
@rate_limit(max_requests=30, window=60)
async def list_tickets(
    status: Optional[TicketStatus] = None,
    assigned_to: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    قائمة تذاكر الدعم مع التصفية حسب الحالة والمسؤول.
    """
    repo = InvitationsRepository(db)
    tickets = await repo.list_tickets(tenant.id, status, assigned_to, skip, min(limit, 200))
    return tickets


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
@rate_limit(max_requests=50, window=60)
async def get_ticket(
    ticket_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تفاصيل تذكرة دعم مع جميع التعليقات.
    """
    repo = InvitationsRepository(db)
    ticket = await repo.get_ticket(ticket_id, tenant.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
@rate_limit(max_requests=20, window=60)
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث تذكرة دعم (تغيير الحالة، الأولوية، المسؤول).
    """
    repo = InvitationsRepository(db)
    ticket = await repo.get_ticket(ticket_id, tenant.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updated = await repo.update_ticket(ticket_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.post("/tickets/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window=60)
async def add_ticket_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إضافة تعليق على تذكرة (داخلي أو خارجي).
    """
    service = InvitationsService(db)
    comment = await service.add_ticket_comment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return comment


@router.get("/tickets/{ticket_id}/comments", response_model=List[TicketCommentResponse])
@rate_limit(max_requests=30, window=60)
async def get_ticket_comments(
    ticket_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب جميع تعليقات التذكرة.
    """
    repo = InvitationsRepository(db)
    comments = await repo.list_ticket_comments(ticket_id, tenant.id)
    return comments


# ============================================================================
# 6. التتبع والتحليلات (Tracking & Analytics)
# ============================================================================

@router.post("/tracking", response_model=InvitationTrackingResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=50, window=60)
async def track_invitation(
    data: InvitationTrackingCreate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    تتبع سلوك الزائر على صفحة الدعوة (يُستدعى من frontend عبر AJAX).
    """
    service = InvitationsService(db)
    tracking = await service.track_behavior(
        invitation_id=data.invitation_id,
        tenant_id=tenant.id,
        request_data={
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "device_type": request.headers.get("sec-ch-ua-platform", "web"),
            "page_visited": data.page_visited or "/invite",
            "actions": data.actions or []
        }
    )
    return tracking