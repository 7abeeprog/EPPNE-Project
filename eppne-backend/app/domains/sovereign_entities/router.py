# app/domains/sovereign_entities/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser, get_current_user_optional
from app.domains.identity.models import User
from app.domains.sovereign_entities.service import SovereignEntitiesService
from app.domains.sovereign_entities.schemas import *
from app.core.rate_limiter import rate_limit
from app.core.pagination import PaginatedResponse

router = APIRouter(prefix="/sovereign-entities", tags=["Sovereign Entities & Brand Builder"])


# ========== 1. إدارة الكيانات ==========
@router.post("/", response_model=SovereignEntityResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_entity(
    data: SovereignEntityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    entity_data = data.model_dump()
    entity_data["tenant_id"] = tenant_id
    entity = await service.create_entity(user_id, entity_data)
    await service.add_representative(cast(int, entity.id), user_id, {
        "user_id": user_id,
        "role": EntityRole.OWNER,
        "can_sign_contracts": True
    })
    return entity


@router.get("/", response_model=PaginatedResponse[SovereignEntityResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_entities(
    entity_type: Optional[SovereignEntityType] = None,
    kyb_status: Optional[KYBStatus] = None,
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)
    result = await service.list_entities(entity_type, kyb_status, skip, limit)
    items = [SovereignEntityResponse.model_validate(item) for item in result["items"]]
    return PaginatedResponse[SovereignEntityResponse](
        data=items,
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"]
    )


@router.get("/me", response_model=List[SovereignEntityResponse])
async def get_my_entities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    entities = await service.get_my_entities(user_id)
    return entities


@router.get("/{entity_id}", response_model=SovereignEntityResponse)
async def get_entity(
    entity_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)
    entity = await service.get_entity(entity_id)
    return entity


@router.put("/{entity_id}", response_model=SovereignEntityResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_entity(
    entity_id: int,
    data: SovereignEntityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    entity = await service.update_entity(entity_id, user_id, data.model_dump(exclude_unset=True))
    return entity


@router.delete("/{entity_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def delete_entity(
    entity_id: int,
    soft: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    await service.delete_entity(entity_id, user_id, soft)
    return {"message": "Entity deleted"}


# ========== 2. إدارة الممثلين ==========
@router.post("/{entity_id}/representatives", response_model=EntityRepresentativeResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def add_representative(
    entity_id: int,
    data: EntityRepresentativeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    rep = await service.add_representative(entity_id, user_id, data.model_dump())
    return rep


@router.get("/{entity_id}/representatives", response_model=List[EntityRepresentativeResponse])
async def get_representatives(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    reps = await service.get_representatives(entity_id)
    return reps


@router.delete("/{entity_id}/representatives/{user_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def remove_representative(
    entity_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    admin_user_id = cast(int, current_user.id)
    await service.remove_representative(entity_id, admin_user_id, user_id)
    return {"message": "Representative removed"}


# ========== 3. KYB ==========
@router.post("/{entity_id}/kyb/documents", response_model=dict)
@rate_limit(max_requests=5, window_seconds=60)
async def upload_kyb_document(
    entity_id: int,
    data: KYBDocumentUpload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    doc = await service.upload_kyb_document(
        entity_id=entity_id,
        user_id=user_id,
        document_type=data.document_type,
        document_url=data.document_url
    )
    return {"message": "Document uploaded", "document_id": doc.id}


@router.get("/{entity_id}/kyb/documents")
async def get_kyb_documents(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    docs = await service.get_kyb_documents(entity_id, user_id)
    return docs


@router.put("/{entity_id}/kyb/status", response_model=SovereignEntityResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def review_kyb(
    entity_id: int,
    data: KYBUpdateStatus,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    admin_id = cast(int, current_user.id)
    entity = await service.review_kyb(
        entity_id=entity_id,
        admin_id=admin_id,
        status=data.status.value,
        rejection_reason=data.rejection_reason
    )
    return entity


# ========== 4. بناء الهوية المؤسسية ==========
@router.get("/{entity_id}/page")
async def get_entity_page(
    entity_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)
    page_data = await service.get_entity_page(entity_id, include_private=bool(current_user))
    return page_data


@router.put("/{entity_id}/page", response_model=EntityPageResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_entity_page(
    entity_id: int,
    data: EntityPageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    page = await service.update_entity_page(entity_id, user_id, data.model_dump(exclude_unset=True))
    return page


@router.post("/{entity_id}/page/publish", response_model=EntityPageResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def publish_entity_page(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    page = await service.publish_entity_page(entity_id, user_id)
    return page


# ========== 5. الصفحة العامة ==========
@router.get("/public/{slug}")
async def get_public_entity_page(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    # نمرر tenant_id=0 مؤقتاً، سيتم استخراجه من الكيان
    service = SovereignEntitiesService(db, 0)
    page_data = await service.get_public_entity_page(slug)
    return page_data


# ========== 6. التكامل المالي ==========
@router.get("/{entity_id}/balance")
async def get_entity_balance(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    balance = await service.get_entity_balance(entity_id)
    return {"entity_id": entity_id, "balance_mrusdt": float(balance)}


@router.post("/{entity_id}/deposit")
@rate_limit(max_requests=10, window_seconds=60)
async def deposit_to_entity(
    entity_id: int,
    data: EntityDepositRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    result = await service.deposit_to_entity_wallet(
        entity_id=entity_id,
        admin_user_id=user_id,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        idempotency_key=idempotency_key
    )
    return result


@router.post("/{entity_id}/transfer")
@rate_limit(max_requests=5, window_seconds=60)
async def transfer_from_entity(
    entity_id: int,
    data: EntityTransferRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    tx_hash = await service.transfer_from_entity(
        entity_id=entity_id,
        from_representative_id=user_id,
        to_address=data.to_address,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        idempotency_key=idempotency_key
    )
    return {"transaction_hash": tx_hash, "amount": float(data.amount), "currency": data.currency}


# ========== 7. قوالب ومكونات الصفحات ==========
@router.post("/templates", response_model=PageTemplateResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_page_template(
    data: PageTemplateCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    user_id = cast(int, current_user.id)
    template = await service.create_page_template(user_id, data.model_dump())
    return template


@router.get("/templates", response_model=List[PageTemplateResponse])
async def list_templates(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)
    templates = await service.list_templates()
    return templates


@router.get("/components", response_model=List[PageComponentResponse])
async def list_components(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)
    components = await service.list_components()
    return components


# ========== 8. الهيكل التنظيمي ==========
@router.get("/{entity_id}/tree")
async def get_entity_tree(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
    tree = await service.get_entity_tree(entity_id)
    return tree