"""
مسارات (Endpoints) قطاع الكيانات السيادية والهوية المؤسسية
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header  # ✅ إضافة Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser, get_current_user_optional
from app.domains.identity.models import User
from app.domains.sovereign_entities.service import SovereignEntitiesService
from app.domains.sovereign_entities.repository import SovereignEntitiesRepository
from app.domains.sovereign_entities.schemas import *
from app.domains.academy.models import AcademyTenant
from decimal import Decimal

router = APIRouter(prefix="/sovereign-entities", tags=["Sovereign Entities & Brand Builder"])


# ========== 1. إدارة الكيانات ==========
@router.post("/", response_model=SovereignEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    data: SovereignEntityCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    entity = await service.create_entity(current_user.id, tenant.id, data.model_dump())
    # إضافة المستخدم كممثل (مالك) للكيان
    await service.add_representative(entity.id, current_user.id, {
        "user_id": current_user.id,
        "role": EntityRole.OWNER,
        "can_sign_contracts": True
    })
    return entity


@router.get("/", response_model=List[SovereignEntityResponse])
async def list_entities(
    entity_type: Optional[SovereignEntityType] = None,
    kyb_status: Optional[KYBStatus] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    entities = await repo.list_entities(tenant.id, entity_type, kyb_status, skip, limit)
    return entities


@router.get("/me", response_model=List[SovereignEntityResponse])
async def get_my_entities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    entities = await service.get_my_entities(current_user.id)
    return entities


@router.get("/{entity_id}", response_model=SovereignEntityResponse)
async def get_entity(entity_id: int, db: AsyncSession = Depends(get_db)):
    service = SovereignEntitiesService(db)
    entity = await service.get_entity(entity_id)
    return entity


@router.put("/{entity_id}/page")
async def update_entity_page(
    entity_id: int,
    data: EntityPageUpdate, 
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    page = await service.update_entity_page(entity_id, current_user.id, data.model_dump(exclude_unset=True))
    return page


@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: int,
    soft: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    await service.delete_entity(entity_id, current_user.id, soft)
    return {"message": "Entity deleted"}


# ========== 2. إدارة الممثلين ==========
@router.post("/{entity_id}/representatives", response_model=EntityRepresentativeResponse, status_code=201)
async def add_representative(
    entity_id: int,
    data: EntityRepresentativeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    rep = await service.add_representative(entity_id, current_user.id, data.model_dump())
    return rep


@router.get("/{entity_id}/representatives", response_model=List[EntityRepresentativeResponse])
async def get_representatives(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    reps = await repo.get_representatives(entity_id)
    return reps


@router.delete("/{entity_id}/representatives/{user_id}")
async def remove_representative(
    entity_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    await service.remove_representative(entity_id, current_user.id, user_id)
    return {"message": "Representative removed"}


# ========== 3. KYB (Know Your Business) ==========
@router.post("/{entity_id}/kyb/documents", response_model=dict)
async def upload_kyb_document(
    entity_id: int,
    data: KYBDocumentUpload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    doc = await service.upload_kyb_document(entity_id, current_user.id, data.document_type, data.document_url)
    return {"message": "Document uploaded", "document_id": doc.id}


@router.get("/{entity_id}/kyb/documents")
async def get_kyb_documents(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    docs = await repo.get_documents(entity_id)
    return docs


@router.put("/{entity_id}/kyb/status", response_model=SovereignEntityResponse)
async def review_kyb(
    entity_id: int,
    data: KYBUpdateStatus,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    entity = await service.review_kyb(entity_id, current_user.id, data.status.value, data.rejection_reason)
    return entity


# ========== 4. بناء الهوية المؤسسية (Brand Builder) ==========
@router.get("/{entity_id}/page")
async def get_entity_page(
    entity_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    page_data = await service.get_entity_page(entity_id, include_private=bool(current_user))
    return page_data


@router.put("/{entity_id}/page")
async def update_entity_page(
    entity_id: int,
    data: EntityPageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    page = await service.update_entity_page(entity_id, current_user.id, data.model_dump(exclude_unset=True))
    return page


@router.post("/{entity_id}/page/publish")
async def publish_entity_page(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    page = await service.publish_entity_page(entity_id, current_user.id)
    return {"message": "Page published", "published_at": page.published_at}


# ========== 5. الصفحة العامة (بدون مصادقة) ==========
@router.get("/public/{slug}")
async def get_public_entity_page(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    page_data = await service.get_public_entity_page(slug)
    return page_data


# ========== 6. التكامل المالي ==========
@router.get("/{entity_id}/balance")
async def get_entity_balance(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    balance = await service.get_entity_balance(entity_id)
    return {"entity_id": entity_id, "balance_mrusdt": float(balance)}


# 🟢 تحديث نقطة التحويل لدعم Idempotency (باستخدام Request Body)
@router.post("/{entity_id}/transfer")
async def transfer_from_entity(
    entity_id: int,
    data: EntityTransferRequest,  # يجب تعريفه في schemas
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    tx_hash = await service.transfer_from_entity(
        entity_id=entity_id,
        from_representative_id=current_user.id,
        to_address=data.to_address,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        idempotency_key=idempotency_key
    )
    return {"transaction_hash": tx_hash, "amount": float(data.amount), "currency": data.currency}


# ========== 7. قوالب ومكونات الصفحات (للإدارة) ==========
@router.post("/templates", response_model=PageTemplateResponse, status_code=201)
async def create_page_template(
    data: PageTemplateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    template = await repo.create_template(tenant_id=tenant.id, **data.model_dump())
    return template


@router.get("/templates", response_model=List[PageTemplateResponse])
async def list_templates(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    templates = await repo.list_templates(tenant.id)
    return templates


@router.get("/components", response_model=List[PageComponentResponse])
async def list_components(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = SovereignEntitiesRepository(db)
    components = await repo.list_components(tenant.id)
    return components


# ============================================================
# 🆕 الإضافات الجديدة
# ============================================================

# 🟢 استرجاع شجرة الكيان (التسلسل الهرمي)
@router.get("/{entity_id}/tree")
async def get_entity_tree(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    tree = await service.get_entity_tree(entity_id)
    return tree


# 🟢 الإيداع في محفظة الكيان (مع Idempotency)
@router.post("/{entity_id}/deposit", response_model=dict)
async def deposit_to_entity(
    entity_id: int,
    data: EntityDepositRequest,  # يجب تعريفه في schemas
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db)
    result = await service.deposit_to_entity_wallet(
        entity_id=entity_id,
        admin_user_id=current_user.id,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        idempotency_key=idempotency_key
    )
    return result