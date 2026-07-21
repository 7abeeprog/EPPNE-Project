# app/domains/zamakana/router.py (الإصدار النهائي المتكامل)
"""
مسارات (Endpoints) قطاع الزمكان – واجهة برمجة التطبيقات للتعامل مع المعرفة، الحملات، والسيناريوهات.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast

from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.zamakana.service import ZamakanaService
from app.domains.zamakana.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.database import get_db
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
    user_id = cast(int, current_user.id)
    node = await service.create_node(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return node


@router.get("/nodes", response_model=List[ZamakanaNodeResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_nodes(
    node_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة العقد المعرفية حسب النوع."""
    service = ZamakanaService(db)
    nodes = await service.list_nodes(cast(int, tenant.id), node_type, skip, limit)  # ✅ cast
    return nodes


@router.get("/nodes/{node_id}", response_model=ZamakanaNodeResponse)
async def get_node(
    node_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب عقدة معرفية محددة."""
    service = ZamakanaService(db)
    node = await service.get_node(node_id, cast(int, tenant.id))  # ✅ cast
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
    user_id = cast(int, current_user.id)
    updated = await service.update_node(node_id, cast(int, tenant.id), user_id, data.model_dump())  # ✅ cast
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
    user_id = cast(int, current_user.id)
    await service.delete_node(node_id, cast(int, tenant.id), user_id)  # ✅ cast
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
    user_id = cast(int, current_user.id)
    edge = await service.create_edge(user_id, cast(int, tenant.id), data.model_dump(), idempotency_key)  # ✅ cast
    return edge


@router.get("/graph", response_model=dict)
@rate_limit(max_requests=20, window_seconds=60)
async def get_knowledge_graph(
    node_type: Optional[str] = None,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """استرجاع شبكة المعرفة (جميع العقد والحواف) للتصور."""
    service = ZamakanaService(db)
    graph = await service.get_knowledge_graph(cast(int, tenant.id), node_type, limit)  # ✅ cast
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
    user_id = cast(int, current_user.id)
    campaign = await service.create_campaign(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return campaign


@router.get("/campaigns", response_model=List[PlanetaryCampaignResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_campaigns(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة الحملات الكوكبية."""
    service = ZamakanaService(db)
    campaigns = await service.list_campaigns(cast(int, tenant.id), status, skip, limit)  # ✅ cast
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=PlanetaryCampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب حملة كوكبية محددة."""
    service = ZamakanaService(db)
    campaign = await service.get_campaign(campaign_id, cast(int, tenant.id))  # ✅ cast
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
    user_id = cast(int, current_user.id)
    pledge = await service.pledge_time(user_id, cast(int, tenant.id), data.model_dump(), idempotency_key)  # ✅ cast
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
    user_id = cast(int, current_user.id)
    fulfilled = await service.fulfill_pledge(user_id, cast(int, tenant.id), pledge_id, data.proof_hash, idempotency_key)  # ✅ cast
    return fulfilled


@router.get("/campaigns/{campaign_id}/pledges", response_model=List[TimePledgeResponse])
async def get_campaign_pledges(
    campaign_id: int,
    status: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة التعهدات الخاصة بحملة معينة."""
    service = ZamakanaService(db)
    pledges = await service.list_pledges(campaign_id, cast(int, tenant.id), status)  # ✅ cast
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
    user_id = cast(int, current_user.id)
    scenario = await service.create_scenario(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return scenario


@router.get("/scenarios", response_model=List[FutureScenarioResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_scenarios(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """قائمة السيناريوهات المستقبلية."""
    service = ZamakanaService(db)
    scenarios = await service.list_scenarios(cast(int, tenant.id), status, skip, limit)  # ✅ cast
    return scenarios


@router.get("/scenarios/{scenario_id}", response_model=FutureScenarioResponse)
async def get_scenario(
    scenario_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب سيناريو مستقبلي محدد."""
    service = ZamakanaService(db)
    scenario = await service.get_scenario(scenario_id, cast(int, tenant.id))  # ✅ cast
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
    user_id = cast(int, current_user.id)
    scenario = await service.generate_ai_analysis(
        scenario_id=scenario_id,
        tenant_id=cast(int, tenant.id),  # ✅ cast
        user_id=user_id,
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
    user_id = cast(int, current_user.id)
    feedback = await service.add_human_feedback(
        user_id=user_id,
        data={"scenario_id": scenario_id, "tenant_id": cast(int, tenant.id), **data.model_dump()}  # ✅ cast
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
    user_id = cast(int, current_user.id)
    scenario = await service.confirm_scenario(scenario_id, user_id, cast(int, tenant.id))  # ✅ cast
    return scenario