# app/core/system_account_service.py
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SystemRole
from app.domains.identity.models import User


async def get_or_create_system_account(db: AsyncSession, tenant_id: int) -> User:
    """
    يُرجع حساب النظام الخاص بهذا التينانت (طرف نظامي واحد مشترك لكل
    الدومينات)، وينشئه إذا لم يكن موجودًا. Idempotent.

    لا تستخدم UserRepository.create() هنا — تلك تعمل commit() كامل على
    الـsession، وهذه الدالة قد تُستدعى من داخل savepoint (begin_nested)
    لأحد الدومينات المستدعية (راجع القسم 1.5 من مستند التصميم).
    """
    result = await db.execute(
        select(User).where(and_(User.tenant_id == tenant_id, User.is_system_account.is_(True)))
    )
    account = result.scalar_one_or_none()
    if account:
        return account

    # استيراد مؤجَّل لتجنب دورة استيراد: core.security تستورد
    # saas.service.SaaSControlService، وبعض دومينات هذه الدالة (saas
    # ضمنها) تستورد system_account_service على مستوى الموديول.
    from app.core.security import get_password_hash

    account = User(
        tenant_id=tenant_id,
        username=f"__system_tenant_{tenant_id}__",
        email=f"system+tenant-{tenant_id}@internal.eppne.local",
        hashed_password=get_password_hash(uuid.uuid4().hex),
        name_ar="حساب النظام",
        name_en="System Account",
        public_id=str(uuid.uuid4()),
        is_active=False,
        is_system_account=True,
        system_role=SystemRole.SYSTEM,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account
