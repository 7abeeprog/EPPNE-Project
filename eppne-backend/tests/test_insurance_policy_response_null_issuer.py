"""
regression test لبند backlog `insurance-policy-response-schema-non-optional-issuer-entity-id`
(2026-09-10). فحص read-only سابق:
.claude/reports/insurance-policy-response-schema-fix-investigation-session-log.md
هذه الجلسة (تنفيذ فعلي): .claude/reports/insurance-policy-response-schema-fix-session-log.md

السياق: migration 049 (جلسة insurance-entity-membership-gap-fix، نفس
التاريخ) غيّرت issuer_entity_id.ondelete من CASCADE إلى SET NULL — حذف
الكيان المُصدِر يسيب البوليصة موجودة بـissuer_entity_id=NULL بدل ما
يمسحها. لكن InsurancePolicyResponse (schemas.py) وارثة
InsurancePolicyCreate اللي فيها issuer_entity_id: int غير Optional —
أي GET على بوليصة زي دي كان هيفشل بـPydantic response-validation error
(500) وقت تجميع الـresponse، لأن int مايقبلش None.

الإصلاح: override وحيد في InsurancePolicyResponse
(issuer_entity_id: Optional[int] = None)، بدون لمس InsurancePolicyCreate
(لسه int إجباري — create_policy بتعتمد عليها في فحص عضوية حقيقي).

هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) عبر الـHTTP layer الفعلية
(httpx.AsyncClient + ASGITransport ضد fastapi_app نفسه) — مش استدعاء
مباشر لـservice — عشان يفعّل تجميع الـresponse_model اللي فيه كان بيحصل
الـ500 قبل الإصلاح. auth اتعدّى بـdependency_overrides على
get_current_active_user (بمستخدم حقيقي من DB) بدل تسجيل دخول كامل عبر
كوكيز identity — النطاق هنا هو تجميع الـresponse، مش تدفق auth نفسه.
"""
import uuid
from decimal import Decimal

import pytest
import httpx
from sqlalchemy import delete, select

from app.main import fastapi_app
from app.core.database import AsyncSessionLocal
from app.api.deps import get_current_active_user

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.models import InsurancePolicy, PolicyType, PremiumCycle

from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_get_policy_after_issuer_entity_deletion_returns_200_with_null_issuer(db):
    creator = await _create_user(db, "p_regtest_respnull_creator")

    throwaway_entity = SovereignEntity(
        tenant_id=TENANT_ID,
        name=f"REGTEST-RESPNULL-ENTITY-{_suffix()}",
        entity_type=SovereignEntityType.ENTERPRISE,
        country_of_origin="EG",
        official_email=f"regtest-respnull-entity-{_suffix()}@eppne.com",
        created_by=creator.id,
    )
    db.add(throwaway_entity)
    await db.commit()
    await db.refresh(throwaway_entity)
    entity_id = throwaway_entity.id

    repo = InsuranceRepository(db)
    policy = await repo.create_policy(
        tenant_id=TENANT_ID, created_by=creator.id, issuer_entity_id=entity_id,
        name=f"REGTEST-RESPNULL-POLICY-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("10"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("500"),
    )
    await db.commit()
    policy_id = policy.id

    try:
        # حذف الكيان المُصدِر — ON DELETE SET NULL بيتنفَّذ جوّه Postgres مباشرة
        await db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity_id))
        await db.commit()

        # تأكيد مسبق (خارج الـHTTP layer) إن issuer_entity_id بقى NULL فعليًا
        async with AsyncSessionLocal() as verify_db:
            refreshed = (await verify_db.execute(
                select(InsurancePolicy).where(InsurancePolicy.id == policy_id)
            )).scalar_one_or_none()
        assert refreshed is not None
        assert refreshed.issuer_entity_id is None

        # الاختبار الفعلي: GET /insurance/policies/{id} عبر HTTP layer حقيقية
        # (تفعّل تجميع InsurancePolicyResponse بالضبط زي الإنتاج)
        fastapi_app.dependency_overrides[get_current_active_user] = lambda: creator
        try:
            transport = httpx.ASGITransport(app=fastapi_app)
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                response = await client.get(f"/api/insurance/policies/{policy_id}")
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200, (
            f"متوقَّع 200، جه {response.status_code} — "
            f"body: {response.text[:500]}"
        )
        body = response.json()
        assert body["id"] == policy_id
        assert body["issuer_entity_id"] is None
    finally:
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await db.execute(delete(User).where(User.id == creator.id))
        await db.commit()
