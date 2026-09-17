"""
regression test لجلسة `iot-translation-service-method-mismatches-investigation`
(2026-09-04). تقرير الجلسة: .claude/reports/iot-translation-service-mismatches-session-log.md

السياق: POST /iot/carbon/settle كان بلا response_model (الراوتر كان بيرجع
dict ضمني بدون أي schema)، رغم أن service.settle_carbon_credits() فعليًا
بترجع بيانات مفيدة (total_credits_settled, monetary_value_added_mrusdt,
readings_processed لحالة SUCCESS، أو status/message لحالة NO_CREDITS).
أُضيف CarbonSettlementResponse (schemas.py) + response_model في الراوتر،
وiot.service.ts (الفرونت إند) بقت فعليًا بترجع نتيجة الـAPI بدل ما تتجاهلها
(كانت موقّعة Promise<void> رغم استخدام الكومبوننت لحقول الرد).

هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) من:
1. حالة SUCCESS: القراءة الحقيقية تتحول لمسواة، والرد يتحقق من صحته ضد
   CarbonSettlementResponse Pydantic model (صفر انحراف عن الـschema الجديد).
2. حالة NO_CREDITS: نفس الشيء لما مفيش أرصدة متاحة.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, update

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.system_account_service import get_or_create_system_account

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.iot.repository import IoTRepository
from app.domains.iot.service import IoTService
from app.domains.iot.models import SmartAsset, UtilityReading, AssetClass, UtilityType, IoTRequestLog
from app.domains.iot.schemas import CarbonSettlementResponse

from app.domains.sites.models import Site, SiteType

from app.domains.finance.models import Wallet, Transaction, AuditLog as FinanceAuditLog
from app.domains.finance.repository import WalletRepository

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


async def _ensure_system_wallet_funded(db, min_balance: float):
    """يلتقط رصيد حساب النظام الأصلي، ويزوده مؤقتًا لو أقل من المطلوب.
    نفس فلسفة test_tenders_auctions_finance_hold_release_settle.py —
    حساب النظام بنية تحتية دائمة، يُستعاد رصيده بالضبط في النهاية."""
    system_user = await get_or_create_system_account(db, TENANT_ID)
    await db.commit()
    wallet_repo = WalletRepository(db)
    wallet = await wallet_repo.get_by_user_id(system_user.id, TENANT_ID)
    original_balances = dict(wallet.balances)
    if float(original_balances.get("MR_USDT", 0)) < min_balance:
        topped_up = dict(original_balances)
        topped_up["MR_USDT"] = min_balance * 10
        await db.execute(update(Wallet).where(Wallet.id == wallet.id).values(balances=topped_up))
        await db.commit()
    return system_user.id, wallet.id, original_balances


async def _cleanup(user_ids, asset_ids, reading_ids, system_wallet_id, system_original_balances, site_ids=None):
    async with AsyncSessionLocal() as cdb:
        await cdb.execute(delete(FinanceAuditLog).where(FinanceAuditLog.user_id.in_(user_ids)))
        await cdb.execute(delete(Transaction).where(
            Transaction.sender_id.in_(user_ids) | Transaction.receiver_id.in_(user_ids)
        ))
        await cdb.execute(delete(IoTRequestLog).where(IoTRequestLog.user_id.in_(user_ids)))
        await cdb.execute(delete(UtilityReading).where(UtilityReading.id.in_(reading_ids)))
        await cdb.execute(delete(SmartAsset).where(SmartAsset.id.in_(asset_ids)))
        if site_ids:
            await cdb.execute(delete(Site).where(Site.id.in_(site_ids)))
        await cdb.execute(delete(User).where(User.id.in_(user_ids)))  # Wallet ondelete=CASCADE
        await cdb.execute(update(Wallet).where(Wallet.id == system_wallet_id).values(balances=system_original_balances))
        await cdb.commit()


@pytest.mark.asyncio
async def test_settle_carbon_credits_success_matches_response_schema(db):
    owner = await _create_user(db, "p_regtest_carbonsettle_owner")
    user_ids = [owner.id]
    asset_ids = []
    reading_ids = []
    site_ids = []
    system_wallet_id = None
    system_original_balances = None

    try:
        system_user_id, system_wallet_id, system_original_balances = await _ensure_system_wallet_funded(db, min_balance=1000)

        site = Site(
            tenant_id=TENANT_ID, site_type=SiteType.GENERIC,
            name=f"REGTEST-CARBONSETTLE-SITE-{_suffix()}",
        )
        db.add(site)
        await db.flush()
        site_ids.append(site.id)

        repo = IoTRepository(db)
        asset = await repo.create_asset(
            tenant_id=TENANT_ID, owner_id=owner.id, site_id=site.id,
            asset_code=f"REGTEST-CARBONSETTLE-{_suffix()}",
            asset_class=AssetClass.UTILITY_METER,
            specs={},
        )
        await db.flush()
        asset_ids.append(asset.id)

        reading = await repo.create_reading(
            tenant_id=TENANT_ID, asset_id=asset.id,
            reading_type=UtilityType.BIOGAS,
            reading_timestamp=datetime.now(timezone.utc),
            carbon_credits_generated=Decimal("5.0"),
            carbon_emissions_mt=Decimal("0"),
            is_settled_on_chain=False,
        )
        await db.commit()
        reading_ids.append(reading.id)

        service = IoTService(db)
        result = await service.settle_carbon_credits(
            owner_id=owner.id, tenant_id=TENANT_ID,
            idempotency_key=f"REGTEST-CARBONSETTLE-{_suffix()}",
        )

        # صفر انحراف عن الـschema الجديد — لو الحقول ماتطابقتش، Pydantic هيرفض
        validated = CarbonSettlementResponse(**result)
        assert validated.status == "SUCCESS"
        assert validated.total_credits_settled == 5.0
        assert validated.monetary_value_added_mrusdt == 250.0
        assert validated.readings_processed == 1

        refreshed = await db.execute(select(UtilityReading).where(UtilityReading.id == reading.id))
        assert refreshed.scalar_one().is_settled_on_chain is True, "FAIL: القراءة لسه مش متسواة بعد settle_carbon_credits"
    finally:
        await _cleanup(user_ids, asset_ids, reading_ids, system_wallet_id, system_original_balances, site_ids)


@pytest.mark.asyncio
async def test_settle_carbon_credits_no_credits_matches_response_schema(db):
    owner = await _create_user(db, "p_regtest_carbonsettle_nocredits")
    user_ids = [owner.id]

    try:
        service = IoTService(db)
        result = await service.settle_carbon_credits(
            owner_id=owner.id, tenant_id=TENANT_ID,
            idempotency_key=f"REGTEST-CARBONSETTLE-NC-{_suffix()}",
        )

        validated = CarbonSettlementResponse(**result)
        assert validated.status == "NO_CREDITS"
        assert validated.message
        assert validated.total_credits_settled is None
        assert validated.monetary_value_added_mrusdt is None
    finally:
        await _delete_users_only(user_ids)


async def _delete_users_only(user_ids):
    async with AsyncSessionLocal() as cdb:
        await cdb.execute(delete(User).where(User.id.in_(user_ids)))
        await cdb.commit()
