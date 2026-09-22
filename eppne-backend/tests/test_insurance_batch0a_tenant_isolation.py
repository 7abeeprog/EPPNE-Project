"""
regression test لجلسة `insurance-batch0a-tenant-isolation` (2026-09-21).
تقرير الجلسة: .claude/reports/insurance-batch0a-tenant-isolation-session-log.md

يثبّت (DB حقيقية، صفر mock):
1. list_active_pensions(tenant_id) بترجع معاشات ACTIVE لهذا التينانت فقط، ولا تسرّب تينانت آخر، وترجع [] لتينانت غير موجود.
2. create_pension: مستفيد من تينانت آخر يترفض NotFoundError (D2) — مستفيد من نفس التينانت ينجح.
3. create_employee_insurance_profile: نفس منطق D2 على user_id.

التحقق الحي عبر HTTP (هجوم X-Tenant-ID قبل/بعد) موثَّق في تقرير الجلسة وملفات evidence.
يستخدم التينانتين throwaway الموجودين أصلًا (1 و16).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.models import PensionRecord, EmployeeInsuranceProfile

TENANT_A = 1
TENANT_B = 16


async def _user(db, tenant_id: int, prefix: str) -> User:
    suffix = uuid.uuid4().hex[:10]
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, tenant_id).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


def _pension_data(tenant_id: int, beneficiary_id: int) -> dict:
    return {
        "tenant_id": tenant_id, "beneficiary_id": beneficiary_id, "pension_type": "REGTEST_BATCH0A",
        "monthly_amount_mrusdt": Decimal("10"), "start_date": datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_list_active_pensions_is_tenant_scoped_and_create_pension_checks_beneficiary(db):
    ben_a = await _user(db, TENANT_A, "p_b0a_ben_a")
    ben_b = await _user(db, TENANT_B, "p_b0a_ben_b")
    admin_a = await _user(db, TENANT_A, "p_b0a_admin_a")
    service = InsuranceService(db)
    pension_ids = []
    try:
        pa = await service.create_pension(admin_a.id, _pension_data(TENANT_A, ben_a.id))
        pension_ids.append(pa.id)
        # مستفيد تينانت B مع tenant_id تينانت A → مرفوض (D2)
        with pytest.raises(NotFoundError):
            await service.create_pension(admin_a.id, _pension_data(TENANT_A, ben_b.id))
        pb = await service.create_pension(ben_b.id, _pension_data(TENANT_B, ben_b.id))
        pension_ids.append(pb.id)

        repo = InsuranceRepository(db)
        got_a = await repo.list_active_pensions(TENANT_A)
        got_b = await repo.list_active_pensions(TENANT_B)
        assert pa.id in [p.id for p in got_a] and pb.id not in [p.id for p in got_a]
        assert pb.id in [p.id for p in got_b] and pa.id not in [p.id for p in got_b]
        assert all(p.tenant_id == TENANT_A for p in got_a)
        assert all(p.tenant_id == TENANT_B for p in got_b)
        assert await repo.list_active_pensions(999999) == []
    finally:
        if pension_ids:
            await db.execute(delete(PensionRecord).where(PensionRecord.id.in_(pension_ids)))
        await db.execute(delete(User).where(User.id.in_([ben_a.id, ben_b.id, admin_a.id])))
        await db.commit()


@pytest.mark.asyncio
async def test_create_employee_profile_rejects_user_from_other_tenant(db):
    emp_a = await _user(db, TENANT_A, "p_b0a_emp_a")
    emp_b = await _user(db, TENANT_B, "p_b0a_emp_b")
    admin_a = await _user(db, TENANT_A, "p_b0a_admin2_a")
    service = InsuranceService(db)
    profile_id = None
    payload = lambda uid: {  # noqa: E731
        "tenant_id": TENANT_A, "user_id": uid, "government_insurance_number": f"REGB0A-{uuid.uuid4().hex[:10]}",
        "employee_share_percentage": Decimal("5"), "employer_share_percentage": Decimal("10"),
    }
    try:
        with pytest.raises(NotFoundError):
            await service.create_employee_insurance_profile(admin_a.id, payload(emp_b.id))
        profile = await service.create_employee_insurance_profile(admin_a.id, payload(emp_a.id))
        profile_id = profile.id
        assert profile.tenant_id == TENANT_A and profile.user_id == emp_a.id
    finally:
        if profile_id is not None:
            await db.execute(delete(EmployeeInsuranceProfile).where(EmployeeInsuranceProfile.id == profile_id))
        await db.execute(delete(User).where(User.id.in_([emp_a.id, emp_b.id, admin_a.id])))
        await db.commit()
