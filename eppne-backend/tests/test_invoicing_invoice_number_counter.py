"""
regression test لجلسة `invoicing-invoice-number-sequence-fix` (2026-09-23).
تقرير الجلسة: .claude/reports/invoicing-invoice-number-sequence-fix-session-log.md

يثبّت (DB حقيقية، صفر mock) إن توليد invoice_number مش مبني على COUNT(*)+1:
A. فجوة في الترقيم (فاتورة محذوفة) لا تقفل التينانت — مرتين متتاليتين (مش عابر).
B. حذف آخر فاتورة لا يعيد استخدام رقمها.
C. 10 استدعاءات create_invoice بالتزامن (جلسات مستقلة، asyncio.gather) → صفر أخطاء،
   10 أرقام مختلفة ومتتالية.
D. توليد رقم داخل معاملة تعمل rollback لا يستهلك الرقم (بلا فجوات من الفشل).
E. تحقق read-only على tenant 1 و16 الحقيقيين: الرقم التالي غير موجود أصلًا — داخل
   معاملة تعمل rollback، صفر insert على بيانات حقيقية.

تينانت throwaway خاص بالاختبار يُحذف بالكامل في finally (كل جدول فيه tenant_id).
"""
import asyncio
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal, engine
from app.core.redis_client import redis_client
from app.domains.academy.models import AcademyTenant
from app.domains.invoicing.service import InvoicingService

INVOICE_USER_ID = 1  # نفس admin_id=1 المستخدم لإنشاء التينانتات throwaway في باقي الاختبارات


@pytest_asyncio.fixture(autouse=True)
async def _fresh_pool_per_test():
    """نفس سبب conftest.db: pool/Redis عالميين مربوطين بـloop الاختبار السابق (Windows Proactor)."""
    yield
    await engine.dispose()
    await redis_client.close()


async def _seed_tenant(seq_numbers: list[int]) -> int:
    """تينانت throwaway + صفوف فواتير مُدرجة مباشرة بالأرقام المحددة (لمحاكاة فجوة حذف)."""
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        tenant = AcademyTenant(name=f"REGTEST_INVNUM_{suffix}", domain=f"regtest-invnum-{suffix}.local", admin_id=1, is_active=True)
        db.add(tenant)
        await db.commit()
        tid = tenant.id
        for seq in seq_numbers:
            await db.execute(text("""insert into invoices(tenant_id,user_id,invoice_number,invoice_type,status,amount,currency,due_date)
                values (:t,:u,:n,'SERVICE','PENDING',1,'MR_USDT',now() + interval '30 days')"""),
                {"t": tid, "u": INVOICE_USER_ID, "n": f"INV-{tid}-{str(seq).zfill(6)}"})
        await db.commit()
    return tid


async def _cleanup(tid: int) -> None:
    async with AsyncSessionLocal() as db:
        tables = [r[0] for r in (await db.execute(text(
            """select c.table_name from information_schema.columns c
               join pg_tables t on t.tablename=c.table_name and t.schemaname='public'
               where c.table_schema='public' and c.column_name='tenant_id' and c.table_name <> 'academy_tenants'"""))).all()]
        for _ in range(8):
            failed = []
            for table in tables:
                try:
                    async with db.begin_nested():
                        await db.execute(text(f'delete from "{table}" where tenant_id = :t'), {"t": tid})
                except Exception:
                    failed.append(table)
            await db.commit()
            if not failed:
                break
            tables = failed
        await db.execute(text("delete from academy_tenants where id = :t"), {"t": tid})
        await db.commit()


async def _create(tid: int) -> str:
    """create_invoice في جلسة مستقلة (زي طلب HTTP حقيقي)."""
    async with AsyncSessionLocal() as db:
        invoice = await InvoicingService(db, tid).create_invoice(
            entity_id=tid, user_id=INVOICE_USER_ID, amount=Decimal("1"), description="REGTEST invoice number",
        )
        return invoice.invoice_number


def _num(tid: int, seq: int) -> str:
    return f"INV-{tid}-{str(seq).zfill(6)}"


@pytest.mark.asyncio
async def test_gap_from_deleted_invoice_does_not_lock_tenant():
    tid = await _seed_tenant([1, 3])  # رقم 2 "محذوف" → COUNT=2 → الكود القديم يولّد 3 الموجود
    try:
        first = await _create(tid)
        second = await _create(tid)  # المحاولة التانية: لو كان القفل دائمًا هتفشل بنفس الطريقة
        assert first == _num(tid, 4)
        assert second == _num(tid, 5)
    finally:
        await _cleanup(tid)


@pytest.mark.asyncio
async def test_deleting_latest_invoice_does_not_reuse_its_number():
    tid = await _seed_tenant([])
    try:
        first = await _create(tid)
        assert first == _num(tid, 1)
        async with AsyncSessionLocal() as db:
            await db.execute(text("delete from invoices where invoice_number = :n"), {"n": first})
            await db.commit()
        second = await _create(tid)
        assert second == _num(tid, 2)
    finally:
        await _cleanup(tid)


@pytest.mark.asyncio
async def test_concurrent_creates_get_distinct_contiguous_numbers():
    tid = await _seed_tenant([])
    try:
        results = await asyncio.gather(*[_create(tid) for _ in range(10)], return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        assert errors == [], f"{len(errors)} failed: {errors[:2]}"
        assert sorted(results) == [_num(tid, i) for i in range(1, 11)]
    finally:
        await _cleanup(tid)


@pytest.mark.asyncio
async def test_rolled_back_generation_does_not_consume_number():
    tid = await _seed_tenant([1])
    try:
        async with AsyncSessionLocal() as db:
            burned = await InvoicingService(db, tid)._generate_invoice_number(tid)
            await db.rollback()
        assert burned == _num(tid, 2)
        assert await _create(tid) == _num(tid, 2)
    finally:
        await _cleanup(tid)


@pytest.mark.asyncio
@pytest.mark.parametrize("real_tenant_id", [1, 16])
async def test_real_tenants_next_number_is_free_readonly(real_tenant_id):
    """read-only: التوليد داخل معاملة تعمل rollback — صفر insert، صفر استهلاك invoices_id_seq."""
    async with AsyncSessionLocal() as db:
        existing = {r[0] for r in (await db.execute(
            text("select invoice_number from invoices where tenant_id = :t"), {"t": real_tenant_id})).all()}
        if not existing:
            pytest.skip(f"tenant {real_tenant_id} has no invoices")
        nxt = await InvoicingService(db, real_tenant_id)._generate_invoice_number(real_tenant_id)
        await db.rollback()
    assert nxt not in existing, f"{nxt} already exists → tenant {real_tenant_id} permanently locked"
