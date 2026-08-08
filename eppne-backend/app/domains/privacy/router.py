# app/domains/privacy/router.py
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast
import logging

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.domains.identity.models import User
from app.domains.privacy.service import PrivacyService
from app.domains.privacy.schemas import *
from app.domains.privacy.models import ErasureStatus

logger = logging.getLogger("eppne.privacy.router")

router = APIRouter(prefix="/privacy", tags=["Sovereign Privacy & Data Erasure"])

# ==========================================
# 1. إعدادات الخصوصية (Privacy Settings)
# ==========================================

@router.get(
    "/settings",
    response_model=PrivacySettingResponse,
    summary="جلب إعدادات الخصوصية"
)
# @rate_limit(max_requests=60, window_seconds=60)
async def get_privacy_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب إعدادات الخصوصية للمستخدم الحالي."""
    service = PrivacyService(db)
    user_id = cast(int, current_user.id)
    settings = await service.get_privacy_settings(user_id, cast(int, current_user.tenant_id))
    return settings


@router.put(
    "/settings",
    response_model=PrivacySettingResponse,
    summary="تحديث إعدادات الخصوصية"
)
# @rate_limit(max_requests=30, window_seconds=60)
async def update_privacy_settings(
    data: PrivacySettingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث إعدادات الخصوصية للمستخدم الحالي."""
    service = PrivacyService(db)
    user_id = cast(int, current_user.id)
    try:
        settings = await service.update_privacy_settings(
            user_id,
            cast(int, current_user.tenant_id),
            data.model_dump(exclude_unset=True)
        )
        return settings
    except Exception as e:
        logger.error(f"Failed to update privacy settings for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذر تحديث إعدادات الخصوصية. يرجى التحقق من القيم المدخلة."
        )


# ==========================================
# 2. سجلات الموافقات (Consent Logs)
# ==========================================

@router.post(
    "/consent/log",
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل موافقة المستخدم"
)
# @rate_limit(max_requests=20, window_seconds=60)
async def log_consent(
    request: Request,
    consent_type: str = Query(..., alias="type", description="نوع الموافقة"),
    granted: bool = Query(..., alias="granted", description="هل تمت الموافقة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تسجيل موافقة المستخدم على معالجة البيانات."""
    user_id = cast(int, current_user.id)
    try:
        service = PrivacyService(db)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        await service.record_consent(
            user_id,
            cast(int, current_user.tenant_id),
            consent_type,
            granted,
            ip,
            ua
        )
        return {"message": "تم تسجيل الموافقة بنجاح"}
    except Exception as e:
        logger.error(f"Failed to log consent for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذر تسجيل الموافقة. يرجى التحقق من النوع والمحاولة مرة أخرى."
        )


# ==========================================
# 3. طلبات محو البيانات (Erasure Requests)
# ==========================================

@router.post(
    "/erasure/request",
    response_model=DataErasureRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء طلب محو بيانات"
)
# @rate_limit(max_requests=5, window_seconds=3600)
async def request_data_erasure(
    data: DataErasureRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء طلب محو بيانات جديد."""
    service = PrivacyService(db)
    user_id = cast(int, current_user.id)
    try:
        request_obj = await service.request_data_erasure(
            user_id,
            cast(int, current_user.tenant_id),
            data.target_module,
            data.reason
        )
        return request_obj
    except Exception as e:
        logger.warning(f"Failed to create erasure request for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذر إنشاء طلب محو البيانات. قد يكون هناك طلب معلق بالفعل."
        )


@router.get(
    "/erasure/requests",
    response_model=PaginatedErasureRequestResponse,
    summary="جلب طلبات محو البيانات الخاصة بي"
)
# @rate_limit(max_requests=30, window_seconds=60)
async def list_my_erasure_requests(
    skip: int = Query(0, ge=0, alias="offset"),
    limit: int = Query(20, ge=1, le=1000, alias="size"),
    request_status: Optional[str] = Query(None, alias="state", description="تصفية حسب الحالة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب طلبات محو البيانات الخاصة بالمستخدم الحالي مع Pagination."""
    service = PrivacyService(db)
    user_id = cast(int, current_user.id)

    status_enum = None
    if request_status:
        try:
            status_enum = ErasureStatus(request_status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حالة غير صالحة. القيم المسموحة: PENDING, COMPLETED, REJECTED"
            )

    result = await service.list_erasure_requests(
        user_id,
        cast(int, current_user.tenant_id),
        skip=skip,
        limit=limit,
        status=status_enum
    )
    return result


# ==========================================
# 4. إدارة المشرفين (Admin Only)
# ==========================================

@router.post(
    "/admin/erasure/{request_id}/process",
    status_code=status.HTTP_200_OK,
    summary="معالجة طلب محو البيانات (للمشرفين)"
)
# @rate_limit(max_requests=50, window_seconds=60)
async def process_erasure_request(
    request_id: int,
    approve: bool = Query(..., alias="approved"),
    notes: Optional[str] = Query(None, alias="comment"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """معالجة طلب محو البيانات (للمشرفين فقط)."""
    service = PrivacyService(db)
    admin_id = cast(int, current_user.id)
    try:
        processed = await service.process_erasure_request(
            request_id,
            cast(int, current_user.tenant_id),
            admin_id,
            approve,
            notes
        )
        return {
            "status": processed.status,
            "receipt_tx": processed.erasure_receipt_tx,
            "message": "تمت معالجة الطلب بنجاح" if approve else "تم رفض الطلب"
        }
    except Exception as e:
        logger.error(f"Failed to process erasure request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذر معالجة الطلب. يرجى التأكد من الصلاحيات والبيانات."
        )


@router.get(
    "/admin/erasure/pending",
    response_model=PaginatedErasureRequestResponse,
    summary="جلب طلبات المحو المعلقة (للمشرفين)"
)
# @rate_limit(max_requests=30, window_seconds=60)
async def get_pending_erasure_requests(
    skip: int = Query(0, ge=0, alias="offset"),
    limit: int = Query(50, ge=1, le=500, alias="size"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب طلبات محو البيانات المعلقة (للمشرفين فقط)."""
    admin_id = cast(int, current_user.id)
    from app.core.security import is_privacy_officer
    if not await is_privacy_officer(admin_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح لك بالوصول")

    service = PrivacyService(db)
    result = await service.get_pending_erasure_requests_for_admin(
        tenant_id=cast(int, current_user.tenant_id),
        skip=skip,
        limit=limit
    )
    return result