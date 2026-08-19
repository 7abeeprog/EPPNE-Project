"""
regression test لجلسة `audit-log-signature-fix` (المرحلة 1.2).
تقرير الجلسة الأصلية: .claude/reports/audit-log-fix-session-log.md

السبب الجذري (كان): `audit_log()` (`app/core/audit.py`) — دالة logger فقط
(`logging.info(json.dumps(...))`، صفر كتابة DB) — كان توقيعها القديم يقبل
`action, user_id, details, ip_address` فقط. **95 موضع استدعاء عبر 18 ملف**
كانوا بيمرروا `tenant_id=`/`resource_id=` (top-level kwargs غير معروفة) →
`TypeError` فوري.

**اكتشاف حرج غيَّر تأطير الخطورة بالكامل (قسم 7 من التقرير):** صفر
`try/except` حوالين أي من الـ95 استدعاء، وصفر exception handler عام في
`app/main.py` (بس 3 مخصَّصة). يعني الباج مش "audit trail بيفشل بصمت" —
كان **العملية الأساسية (بوليصة تأمين، كيان سيادي، عقدة معرفية، عقد إيجار...)
بترجع 500 خام للعميل الحقيقي**، ولأغلب المواضع (اللي فيها `commit()` بعد
`audit_log()` في نفس الدالة) البيانات **كمان ما بتتحفظش على القرص إطلاقًا**
(rollback ضمني لغياب commit).

الإصلاح المُطبَّق (`app/core/audit.py`، صفر migration لأنها أصلًا logger
فقط):
```python
async def audit_log(
    action: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,   # ← جديد
    resource_id: Optional[int] = None, # ← جديد
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    log_entry = {..., "tenant_id": tenant_id, "resource_id": resource_id, ...}
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
```
صفر لمس على أي من الـ95 موضع الاستدعاء نفسها.

**هذا الملف يغطي 3 مواضع تمثيلية (مش الـ95 كلهم)، بتنوّع نوع العملية
(تعليمات الجلسة: مالي/إداري/عادي)** — نفس الأربعة أنماط النصية الموجودة
فعليًا في الكود (`kwargs` مباشرة، ترتيب `commit()`/`begin_nested()` مختلف
بين الدومينات):

| # | الملف/الدالة | النوع | نمط الـtransaction | مصدر التنوع |
|---|---|---|---|---|
| 1 | `insurance.create_policy` | 💰 مالي | `audit_log()` **قبل** `commit()`، جوّه `begin_nested()` | نفس العيّنة المُتحقَّق منها حيًا في التقرير الأصلي (قسم 10، صف 1) |
| 2 | `sovereign_entities.create_entity` | 🏛️ إداري | `audit_log()` **بعد** commits سابقة (كل `repo.create_*` بتعمل `commit()` فوري خاص بيها) — صفر `begin_nested()` | نمط transaction مختلف تمامًا عن insurance — المورد بيتحفظ فعليًا حتى لو `audit_log()` فشلت، فالفارق العملي (لو الباج لسه موجود) هو "500 كاذب رغم نجاح الحفظ" مش "rollback حقيقي" |
| 3 | `zamakana` (عقدة معرفية، `ZAMAKANA_NODE_CREATED`) | 👤 عادي (ميزة مجتمعية عادية) | `audit_log()` بعد `commit()` فوري لـ`repo.create_node()` | نفس العيّنة المُتحقَّق منها حيًا في التقرير الأصلي (قسم 10، صف 2) — **استدعاء مباشر لـ`ZamakanaRepository.create_node()` + `audit_log()` بمعزل عن `ZamakanaService.create_node()` الكاملة عمدًا**، لأنها بتصطدم ببج مسبق منفصل تمامًا وموثَّق (Backlog #12 `saas-control-service-wrong-arity-call`: `_check_saas_limits` بتنادي `can_access_service(tenant_id, feature)` بمعاملين، لكن التوقيع الحقيقي `can_access_service(service_code)` بمعامل واحد فقط) — **تأكَّدت أنه لسه موجود فعليًا بالقراءة المباشرة وقت كتابة هذا الملف**، خارج نطاق #14 تمامًا، صفر لمس |

**منهجية موحَّدة لكل عيّنة (مطابقة لقسم 10 من التقرير الأصلي حرفيًا)،
تثبت اثنين معًا:**
1. `audit_log()` نجحت بلا `TypeError` — بالتقاط سجل `eppne.audit` logger
   فعليًا (`logging.Handler` مؤقت، مش مجرد "صفر استثناء ظاهري")، وفحص
   `tenant_id`/`resource_id` داخل الـJSON المُسجَّل فعليًا.
2. العملية الأساسية اتحفظت فعليًا على القرص — `SELECT` مستقل يثبت الحفظ،
   يعني الـ500/rollback الصامت (قسم 7 من التقرير) اختفى فعليًا.

**بيانات throwaway:** `tenant_id=1`. `sovereign_entities_v2 id=3` — صف
موجود بالفعل، قراءة فقط (نفس نمط `EXISTING_LAND_ASSET_ID` في الملفات
السابقة)، مُستخدَم كـ`issuer_entity_id` لبوليصة التأمين. كل اختبار بيستخدم
بيانات فريدة (`uuid4` suffix)، تنظيف كامل في `finally`.
"""
import json
import logging
import uuid
from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator, List

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.finance.models import AuditLog

from app.domains.insurance.service import InsuranceService
from app.domains.insurance.models import InsurancePolicy, PolicyType, PremiumCycle

from app.domains.sovereign_entities.service import SovereignEntitiesService
from app.domains.sovereign_entities.models import SovereignEntity, EntityPage, EntityRepresentative, SovereignEntityType

from app.domains.zamakana.repository import ZamakanaRepository
from app.domains.zamakana.models import ZamakanaNode, ZamakanaNodeType
from app.core.audit import audit_log

TENANT_ID = 1
EXISTING_ISSUER_ENTITY_ID = 3  # sovereign_entities_v2 id=3 — صف throwaway موجود بالفعل، قراءة فقط


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())


@contextmanager
def _capture_audit_logger() -> Iterator[_CapturingHandler]:
    """يلتقط سجلات logger `eppne.audit` الفعلية أثناء تنفيذ الكتلة — إثبات
    مباشر إن audit_log() نجحت بلا TypeError، بدل الاعتماد على "صفر استثناء"
    وحدها (اللي ممكن تخفي فشل صامت لو حد لف استدعاء audit_log() بـtry/except
    مستقبلاً)."""
    handler = _CapturingHandler()
    logger = logging.getLogger("eppne.audit")
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _cleanup_user(db, user_id: int):
    await db.execute(delete(AuditLog).where(AuditLog.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


# ============================================================
# 1) insurance.create_policy — 💰 مالي — audit_log() قبل commit()، جوّه begin_nested()
# ============================================================

@pytest.mark.asyncio
async def test_insurance_create_policy_audit_log_no_500_and_policy_persisted(db):
    """قبل الإصلاح: audit_log(tenant_id=, resource_id=...) كانت ترمي TypeError
    غير ملتقَط (صفر try/except حوالينها) جوّه begin_nested() — الاستثناء
    يتصعّد كـ500 خام، والـcommit() اللي بعد begin_nested() ما بينفَّذش أبدًا
    (rollback ضمني للـsavepoint) → البوليصة ما بتتحفظش على الإطلاق."""
    admin = await _create_user(db, "p_regtest_audit_ins_admin")
    service = InsuranceService(db)
    policy_id = None

    try:
        with _capture_audit_logger() as handler:
            policy = await service.create_policy(
                user_id=admin.id, tenant_id=TENANT_ID,
                data={
                    "issuer_entity_id": EXISTING_ISSUER_ENTITY_ID,
                    "name": f"REGTEST-AUDIT14-POLICY-{_suffix()}",
                    "policy_type": PolicyType.ACCIDENT,
                    "base_premium_mrusdt": Decimal("10"),
                    "premium_cycle": PremiumCycle.MONTHLY,
                    "max_coverage_limit_mrusdt": Decimal("500"),
                },
            )
        policy_id = policy.id

        # 1) audit_log() نجحت فعليًا بلا TypeError — سجل حقيقي مُلتقَط
        assert len(handler.records) >= 1, "audit_log() لم تُنفَّذ إطلاقًا — رجوع محتمل لباج TypeError غير ملتقَط"
        entry = json.loads(handler.records[-1])
        assert entry["action"] == "POLICY_CREATED"
        assert entry["tenant_id"] == TENANT_ID
        assert entry["resource_id"] == policy.id

        # 2) العملية الأساسية اتحفظت فعليًا — SELECT مستقل (500/rollback صامت اختفى)
        refreshed = (await db.execute(
            select(InsurancePolicy).where(InsurancePolicy.id == policy.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "البوليصة لم تُحفظ — رجوع محتمل لـ500/rollback صامت (قسم 7 من التقرير)"
        assert refreshed.issuer_entity_id == EXISTING_ISSUER_ENTITY_ID
    finally:
        if policy_id is not None:
            await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
            await db.commit()
        await _cleanup_user(db, admin.id)


# ============================================================
# 2) sovereign_entities.create_entity — 🏛️ إداري — audit_log() بعد commits سابقة، صفر begin_nested
# ============================================================

@pytest.mark.asyncio
async def test_sovereign_entities_create_entity_audit_log_no_500_and_entity_persisted(db):
    """قبل الإصلاح: audit_log(tenant_id=, resource_id=...) كانت ترمي TypeError
    غير ملتقَط بعد ما الكيان + الصفحة + الممثل اتحفظوا فعليًا (كل repo.create_*
    بتعمل commit() فوري خاص بيها، صفر begin_nested() يلف الدالة كلها) — يعني
    العميل كان بياخد 500 رغم إن الكيان اتسجل فعلًا (نمط مختلف عن insurance:
    "500 كاذب" مش "rollback حقيقي" — لسه أثر حقيقي لأن event.publish اللي
    بعد audit_log() ما كانش بيتنفَّذ، والـresponse نفسه كان بيفشل)."""
    founder = await _create_user(db, "p_regtest_audit_entity_founder")
    service = SovereignEntitiesService(db, TENANT_ID)
    entity_id = None

    try:
        with _capture_audit_logger() as handler:
            entity = await service.create_entity(
                user_id=founder.id,
                data={
                    "name": f"REGTEST-AUDIT14-ENTITY-{_suffix()}",
                    "entity_type": SovereignEntityType.ENTERPRISE,
                    "country_of_origin": "EG",
                    "official_email": f"regtest-entity-{_suffix()}@eppne.com",
                },
            )
        entity_id = entity.id

        assert len(handler.records) >= 1, "audit_log() لم تُنفَّذ إطلاقًا — رجوع محتمل لباج TypeError غير ملتقَط"
        entry = json.loads(handler.records[-1])
        assert entry["action"] == "ENTITY_CREATED"
        assert entry["tenant_id"] == TENANT_ID
        assert entry["resource_id"] == entity.id

        refreshed = (await db.execute(
            select(SovereignEntity).where(SovereignEntity.id == entity.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "الكيان لم يُحفظ — رجوع محتمل لـ500/rollback صامت (قسم 7 من التقرير)"
        assert refreshed.entity_type == SovereignEntityType.ENTERPRISE
    finally:
        if entity_id is not None:
            await db.execute(delete(EntityRepresentative).where(EntityRepresentative.entity_id == entity_id))
            await db.execute(delete(EntityPage).where(EntityPage.entity_id == entity_id))
            await db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity_id))
            await db.commit()
        await _cleanup_user(db, founder.id)


# ============================================================
# 3) zamakana (ZAMAKANA_NODE_CREATED) — 👤 عادي — audit_log() بعد commit() فوري
# ============================================================

@pytest.mark.asyncio
async def test_zamakana_node_audit_log_no_500_and_node_persisted(db):
    """استدعاء مباشر لـ`ZamakanaRepository.create_node()` + `audit_log()`
    بنفس الشكل الحرفي المستخدَم فعليًا في `zamakana/service.py:78-98` —
    بمعزل عمدًا عن `ZamakanaService.create_node()` الكاملة، لأنها بتصطدم
    ببج مسبق منفصل تمامًا وموثَّق (Backlog #12، `_check_saas_limits` بتنادي
    `can_access_service()` بمعاملين بدل واحد) قبل ما توصل حتى لـaudit_log()
    — خارج نطاق #14 تمامًا، صفر لمس."""
    creator = await _create_user(db, "p_regtest_audit_zamakana_creator")
    repo = ZamakanaRepository(db)
    node_id = None

    try:
        with _capture_audit_logger() as handler:
            node = await repo.create_node(
                tenant_id=TENANT_ID,
                created_by=creator.id,
                title=f"REGTEST-AUDIT14-NODE-{_suffix()}",
                description="regression test throwaway node",
                node_type=ZamakanaNodeType.ERA,
            )
            await audit_log(  # type: ignore[call-arg] — نفس شكل الاستدعاء الحقيقي بالحرف
                user_id=creator.id,
                tenant_id=TENANT_ID,
                action="ZAMAKANA_NODE_CREATED",
                resource_id=node.id,
                details={"title": node.title, "type": node.node_type.value},
            )
        node_id = node.id

        assert len(handler.records) >= 1, "audit_log() لم تُنفَّذ إطلاقًا — رجوع محتمل لباج TypeError غير ملتقَط"
        entry = json.loads(handler.records[-1])
        assert entry["action"] == "ZAMAKANA_NODE_CREATED"
        assert entry["tenant_id"] == TENANT_ID
        assert entry["resource_id"] == node.id

        refreshed = (await db.execute(
            select(ZamakanaNode).where(ZamakanaNode.id == node.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "العقدة لم تُحفظ — رجوع محتمل لـ500/rollback صامت (قسم 7 من التقرير)"
        assert refreshed.node_type == ZamakanaNodeType.ERA
    finally:
        if node_id is not None:
            await db.execute(delete(ZamakanaNode).where(ZamakanaNode.id == node_id))
            await db.commit()
        await _cleanup_user(db, creator.id)
