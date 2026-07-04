# app/domains/zamakana/router.py (الإصدار النهائي المتكامل)
"""
مسارات (Endpoints) قطاع الزمكان – واجهة برمجة التطبيقات للتعامل مع المعرفة، الحملات، والسيناريوهات.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.zamakana.service import ZamakanaService
from app.domains.zamakana.repository import ZamakanaRepository
from app.domains.zamakana.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.database import get_db, AsyncSessionLocal
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/zamakana", tags=["Zamakana - Time & Knowledge Engine"])


# ========== 1. عقد المعرفة (Nodes & Edges) ==========

@router.post("/nodes", response_model=ZamakanaNodeResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_node(
    data: ZamakanaNodeCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة عقدة معرفية جديدة (حقبة، ابتكار، شخص، حدث)."""
    service = ZamakanaService(db)
    node = await service.create_node(current_user.id, tenant.id, data.model_dump())
    return node


@router.get("/nodes", response_model=List[ZamakanaNodeResponse])
async def list_nodes(
    node_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة العقد المعرفية حسب النوع."""
    repo = ZamakanaRepository(db)
    nodes = await repo.list_nodes(tenant.id, node_type, skip, limit)
    return nodes


@router.get("/nodes/{node_id}", response_model=ZamakanaNodeResponse)
async def get_node(
    node_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب عقدة معرفية محددة."""
    repo = ZamakanaRepository(db)
    node = await repo.get_node(node_id, tenant.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.put("/nodes/{node_id}", response_model=ZamakanaNodeResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_node(
    node_id: int,
    data: ZamakanaNodeCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث عقدة معرفية (يتطلب أن يكون المستخدم هو منشئها)."""
    service = ZamakanaService(db)
    node = await service.repo.get_node(node_id, tenant.id)
    if not node or node.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await service.repo.update_node(node_id, tenant.id, **data.model_dump())
    return updated


@router.delete("/nodes/{node_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def delete_node(
    node_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف عقدة معرفية (يتطلب أن يكون المستخدم هو منشئها)."""
    service = ZamakanaService(db)
    node = await service.repo.get_node(node_id, tenant.id)
    if not node or node.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await service.repo.delete_node(node_id, tenant.id)
    return {"message": "Node deleted"}


@router.post("/edges", response_model=ZamakanaEdgeResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def create_edge(
    data: ZamakanaEdgeCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """ربط عقدتين (تأثير سببي أو تأثير الفراشة)."""
    service = ZamakanaService(db)
    edge = await service.create_edge(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return edge


@router.get("/graph", response_model=dict)
async def get_knowledge_graph(
    node_type: Optional[str] = None,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """استرجاع شبكة المعرفة (جميع العقد والحواف) للتصور."""
    service = ZamakanaService(db)
    graph = await service.get_knowledge_graph(tenant.id, node_type, limit)
    return graph


# ========== 2. الحملات الكوكبية والتعهدات الزمنية ==========

@router.post("/campaigns", response_model=PlanetaryCampaignResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_campaign(
    data: PlanetaryCampaignCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء حملة كوكبية لجمع ساعات تطوعية."""
    service = ZamakanaService(db)
    campaign = await service.create_campaign(current_user.id, tenant.id, data.model_dump())
    return campaign


@router.get("/campaigns", response_model=List[PlanetaryCampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة الحملات الكوكبية."""
    repo = ZamakanaRepository(db)
    campaigns = await repo.list_campaigns(tenant.id, status, skip, limit)
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=PlanetaryCampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب حملة كوكبية محددة."""
    repo = ZamakanaRepository(db)
    campaign = await repo.get_campaign(campaign_id, tenant.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/pledges", response_model=TimePledgeResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def pledge_time(
    data: TimePledgeCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """التعهد بساعات تطوعية لحملة معينة."""
    service = ZamakanaService(db)
    pledge = await service.pledge_time(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return pledge


@router.post("/pledges/{pledge_id}/fulfill", response_model=TimePledgeResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def fulfill_pledge(
    pledge_id: int,
    data: TimePledgeFulfill,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إثبات إنجاز الساعات المتعهد بها (رفع إثبات)."""
    service = ZamakanaService(db)
    fulfilled = await service.fulfill_pledge(
        user_id=current_user.id,
        tenant_id=tenant.id,
        pledge_id=pledge_id,
        proof_hash=data.proof_hash,
        idempotency_key=idempotency_key
    )
    return fulfilled


@router.get("/campaigns/{campaign_id}/pledges", response_model=List[TimePledgeResponse])
async def get_campaign_pledges(
    campaign_id: int,
    status: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة التعهدات الخاصة بحملة معينة."""
    repo = ZamakanaRepository(db)
    pledges = await repo.list_pledges(campaign_id, tenant.id, status)
    return pledges


# ========== 3. المحاكاة المستقبلية ==========

@router.post("/scenarios", response_model=FutureScenarioResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_scenario(
    data: FutureScenarioCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء سيناريو مستقبلي جديد."""
    service = ZamakanaService(db)
    scenario = await service.create_scenario(current_user.id, tenant.id, data.model_dump())
    return scenario


@router.get("/scenarios", response_model=List[FutureScenarioResponse])
async def list_scenarios(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة السيناريوهات المستقبلية."""
    repo = ZamakanaRepository(db)
    scenarios = await repo.list_scenarios(tenant.id, status, skip, limit)
    return scenarios


@router.get("/scenarios/{scenario_id}", response_model=FutureScenarioResponse)
async def get_scenario(
    scenario_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب سيناريو مستقبلي محدد."""
    repo = ZamakanaRepository(db)
    scenario = await repo.get_scenario(scenario_id, tenant.id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/scenarios/{scenario_id}/analyze", response_model=FutureScenarioResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def analyze_scenario(
    scenario_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    طلب تحليل الذكاء الاصطناعي للسيناريو.
    """
    service = ZamakanaService(db)
    scenario = await service.generate_ai_analysis(
        scenario_id=scenario_id,
        tenant_id=tenant.id,
        user_id=current_user.id,
        idempotency_key=idempotency_key
    )
    return scenario


@router.post("/scenarios/{scenario_id}/feedback", response_model=HumanFeedbackResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def add_feedback(
    scenario_id: int,
    data: HumanFeedbackCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة مراجعة بشرية على تقرير AI للسيناريو."""
    service = ZamakanaService(db)
    feedback = await service.add_human_feedback(
        user_id=current_user.id,
        data={"scenario_id": scenario_id, **data.model_dump()}
    )
    return feedback


@router.post("/scenarios/{scenario_id}/confirm", response_model=FutureScenarioResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def confirm_scenario(
    scenario_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """اعتماد السيناريو بعد المراجعة البشرية."""
    service = ZamakanaService(db)
    scenario = await service.confirm_scenario(scenario_id, current_user.id)
    return scenario