"""
regression test لجلسة `entity-membership-foundation` (الجلسة 1 من 2،
مسار الصلاحيات الجديد — بناء الأساس العام لنظام EntityMembership).

المرجع:
- `.claude/plans/entity-membership-foundation-session-instructions.md` (تعليمات الجلسة)
- `.claude/plans/entity-membership-technical-design.md` (الـschema الكامل)
- `.claude/reports/entity-membership-foundation-session-log.md` (سجل الجلسة والتحقق الحي)

النطاق: ثلاثة جداول جديدة بالكامل (`entity_memberships`,
`entity_permission_overrides`, `permission_audit_log`) + Repository/Service
جديدان في `app/core/`. **صفر لمس على `sovereign_entities`** — كل بيانات
هذا الملف بـ`entity_type="_TEST_ENTITY"` وهمي، معزول تمامًا عن أي كيان
سيادي حقيقي.

منهجية "تحقق مستقل" (بنفس معيار `test_affiliate_service_missing_methods.py`
و`test_redis_client_wrapper_missing_methods.py`): كل سيناريو حاسم (القيد
الفريد، upsert الـoverride، تسجيل الـaudit التلقائي) يُتحقَّق منه بـ`SELECT`
مباشر — وحيث ينطبق، عبر جلسة `AsyncSessionLocal` مستقلة تمامًا عن الجلسة
التي نفَّذت الاستدعاء — لا مجرد ثقة بالقيمة المُرجَعة من نفس الاستدعاء.
"""
import uuid

import pytest
from sqlalchemy import select, delete, and_
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels عبر Base.metadata

from app.core.database import AsyncSessionLocal
from app.core.models import (
    EntityMembership, EntityMembershipRole,
    EntityPermissionOverride, PermissionAuditLog, AuditAction,
)
from app.core.entity_membership_service import EntityMembershipService

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

TENANT_ID = 1
ENTITY_TYPE = "_TEST_ENTITY"


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


def _entity_id() -> int:
    """entity_id وهمي فريد لكل اختبار — بلا FK حقيقي (Polymorphic)، فقط
    لازم يكون فريدًا لعزل كل اختبار عن الباقي."""
    return 900_000_000 + (uuid.uuid4().int % 90_000_000)


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-EM-{prefix}-{suffix}",
    )


async def _cleanup(db, *, entity_ids, user_ids):
    """تنظيف بالترتيب الصحيح لتفادي FK RESTRICT: audit → overrides →
    memberships → users."""
    if entity_ids:
        await db.execute(
            delete(PermissionAuditLog).where(
                and_(
                    PermissionAuditLog.entity_type == ENTITY_TYPE,
                    PermissionAuditLog.entity_id.in_(entity_ids),
                )
            )
        )
        await db.execute(
            delete(EntityPermissionOverride).where(
                and_(
                    EntityPermissionOverride.entity_type == ENTITY_TYPE,
                    EntityPermissionOverride.entity_id.in_(entity_ids),
                )
            )
        )
        await db.execute(
            delete(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == ENTITY_TYPE,
                    EntityMembership.entity_id.in_(entity_ids),
                )
            )
        )
    if user_ids:
        await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


# ============================================================
# 1) add_member + list_members — إنشاء عضوية، استعلام "أعضاء كيان بعينه"
# ============================================================

@pytest.mark.asyncio
async def test_add_member_and_list_members_by_entity(db):
    user = await _create_user(db, "em_add")
    entity_id = _entity_id()
    user_ids, entity_ids = [user.id], [entity_id]

    try:
        svc = EntityMembershipService(db)
        member = await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
        )
        assert member.id is not None

        # تحقق مستقل: SELECT مباشر بدل الثقة بكائن الإرجاع
        row = (await db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == ENTITY_TYPE,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user.id,
                )
            )
        )).scalar_one_or_none()
        assert row is not None
        assert row.role == EntityMembershipRole.OWNER
        assert row.tenant_id == TENANT_ID

        members = await svc.get_members(entity_type=ENTITY_TYPE, entity_id=entity_id)
        assert len(members) == 1
        assert members[0].user_id == user.id
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 2) القيد الفريد: دور ثانٍ لنفس (entity_type, entity_id, user_id) يجب
#    أن يفشل بـIntegrityError
# ============================================================

@pytest.mark.asyncio
async def test_unique_constraint_blocks_second_role_same_entity_user(db):
    user = await _create_user(db, "em_uniq")
    entity_id = _entity_id()
    user_ids, entity_ids = [user.id], [entity_id]

    try:
        svc = EntityMembershipService(db)
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
        )

        # جلسة مستقلة تمامًا للمحاولة الثانية المتوقَّع فشلها — IntegrityError
        # بيسمّم أي جلسة تحصل فيها، والاعتماد على db الأصلية بعدها غير موثوق
        # (نفس الاحتياط المُتّبع في test_ai_agents_execute_action.py وtest_saas_active_subscription.py).
        async with AsyncSessionLocal() as db2:
            svc2 = EntityMembershipService(db2)
            with pytest.raises(IntegrityError):
                await svc2.add_member(
                    entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
                    tenant_id=TENANT_ID, role=EntityMembershipRole.SIGNATORY,
                )

        # تحقق مستقل: صف واحد بالضبط، لسه بدوره الأصلي (جلسة db الأصلية سليمة تمامًا)
        count_result = await db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == ENTITY_TYPE,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user.id,
                )
            )
        )
        rows = count_result.scalars().all()
        assert len(rows) == 1
        assert rows[0].role == EntityMembershipRole.OWNER
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 3) list_entities_for_user — استعلام "كيانات مستخدم بعينه"، معزول عن
#    عضويات مستخدمين آخرين
# ============================================================

@pytest.mark.asyncio
async def test_list_entities_for_user_isolated_from_other_users(db):
    user_a = await _create_user(db, "em_entlist_a")
    user_b = await _create_user(db, "em_entlist_b")
    entity_a = _entity_id()
    entity_b = _entity_id()
    user_ids = [user_a.id, user_b.id]
    entity_ids = [entity_a, entity_b]

    try:
        svc = EntityMembershipService(db)
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_a, user_id=user_a.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
        )
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_b, user_id=user_b.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
        )

        entities_a = await svc.get_user_entities(user_id=user_a.id, tenant_id=TENANT_ID)
        our_entities_a = [e for e in entities_a if e.entity_id in entity_ids]
        assert len(our_entities_a) == 1
        assert our_entities_a[0].entity_id == entity_a

        # تحقق مستقل عبر جلسة منفصلة تمامًا
        async with AsyncSessionLocal() as independent_db:
            rows = (await independent_db.execute(
                select(EntityMembership).where(
                    and_(
                        EntityMembership.user_id == user_a.id,
                        EntityMembership.tenant_id == TENANT_ID,
                        EntityMembership.entity_id.in_(entity_ids),
                    )
                )
            )).scalars().all()
            assert len(rows) == 1
            assert rows[0].entity_id == entity_a
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 4) update_member_role / change_role — نفس الصف يتحدَّث في مكانه
# ============================================================

@pytest.mark.asyncio
async def test_change_role_updates_same_row(db):
    user = await _create_user(db, "em_role")
    entity_id = _entity_id()
    user_ids, entity_ids = [user.id], [entity_id]

    try:
        svc = EntityMembershipService(db)
        created = await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.REPRESENTATIVE,
        )
        await svc.change_role(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            new_role=EntityMembershipRole.EXECUTIVE_DIRECTOR,
        )

        row = (await db.execute(
            select(EntityMembership).where(EntityMembership.id == created.id)
        )).scalar_one()
        assert row.role == EntityMembershipRole.EXECUTIVE_DIRECTOR

        total = (await db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == ENTITY_TYPE,
                    EntityMembership.entity_id == entity_id,
                )
            )
        )).scalars().all()
        assert len(total) == 1, "تعديل الدور يجب أن يحدِّث نفس الصف، لا ينشئ صفًا جديدًا"
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 5) remove_member — إزالة عضوية
# ============================================================

@pytest.mark.asyncio
async def test_remove_member_deletes_row(db):
    user = await _create_user(db, "em_remove")
    entity_id = _entity_id()
    user_ids, entity_ids = [user.id], [entity_id]

    try:
        svc = EntityMembershipService(db)
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
        )
        await svc.remove_member(entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id)

        row = (await db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == ENTITY_TYPE,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user.id,
                )
            )
        )).scalar_one_or_none()
        assert row is None
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 6) grant_permission — ينشئ override + سطر audit تلقائي، بلا استدعاء
#    منفصل من طرف الاختبار نفسه
# ============================================================

@pytest.mark.asyncio
async def test_grant_permission_creates_override_and_autologs_audit(db):
    granter = await _create_user(db, "em_grant_by")
    target = await _create_user(db, "em_grant_target")
    entity_id = _entity_id()
    user_ids = [granter.id, target.id]
    entity_ids = [entity_id]

    try:
        svc = EntityMembershipService(db)
        override = await svc.grant_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts",
            granted_by=granter.id, reason="regression test grant",
        )
        assert override.granted is True

        # تحقق مستقل بجلسة منفصلة تمامًا — صفر ثقة بنفس الاستدعاء
        async with AsyncSessionLocal() as independent_db:
            override_rows = (await independent_db.execute(
                select(EntityPermissionOverride).where(
                    and_(
                        EntityPermissionOverride.entity_type == ENTITY_TYPE,
                        EntityPermissionOverride.entity_id == entity_id,
                        EntityPermissionOverride.user_id == target.id,
                        EntityPermissionOverride.permission == "can_sign_contracts",
                    )
                )
            )).scalars().all()
            assert len(override_rows) == 1
            assert override_rows[0].granted is True
            assert override_rows[0].granted_by == granter.id

            # الضمان الأساسي: سطر audit تلقائي — الاختبار لم يستدعِ أي
            # دالة audit بنفسه إطلاقًا
            audit_rows = (await independent_db.execute(
                select(PermissionAuditLog).where(
                    and_(
                        PermissionAuditLog.entity_type == ENTITY_TYPE,
                        PermissionAuditLog.entity_id == entity_id,
                        PermissionAuditLog.target_user_id == target.id,
                        PermissionAuditLog.permission == "can_sign_contracts",
                    )
                )
            )).scalars().all()
            assert len(audit_rows) == 1
            assert audit_rows[0].action == AuditAction.GRANT
            assert audit_rows[0].performed_by == granter.id
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 7) revoke_permission بعد grant — upsert على نفس الصف (لا صف جديد) +
#    سطر audit ثانٍ تلقائي (REVOKE) — بلا حذف السطر الأول
# ============================================================

@pytest.mark.asyncio
async def test_revoke_permission_upserts_same_row_and_appends_audit(db):
    granter = await _create_user(db, "em_revoke_by")
    target = await _create_user(db, "em_revoke_target")
    entity_id = _entity_id()
    user_ids = [granter.id, target.id]
    entity_ids = [entity_id]

    try:
        svc = EntityMembershipService(db)
        granted = await svc.grant_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts",
            granted_by=granter.id,
        )
        revoked = await svc.revoke_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts",
            revoked_by=granter.id, reason="regression test revoke",
        )
        assert revoked.id == granted.id, "revoke يجب أن يحدِّث نفس صف الـoverride، لا صفًا جديدًا"
        assert revoked.granted is False

        async with AsyncSessionLocal() as independent_db:
            override_rows = (await independent_db.execute(
                select(EntityPermissionOverride).where(
                    and_(
                        EntityPermissionOverride.entity_type == ENTITY_TYPE,
                        EntityPermissionOverride.entity_id == entity_id,
                        EntityPermissionOverride.user_id == target.id,
                        EntityPermissionOverride.permission == "can_sign_contracts",
                    )
                )
            )).scalars().all()
            assert len(override_rows) == 1, "لازم صف واحد بالضبط (upsert)، مش صفين"
            assert override_rows[0].id == granted.id
            assert override_rows[0].granted is False

            audit_rows = (await independent_db.execute(
                select(PermissionAuditLog).where(
                    and_(
                        PermissionAuditLog.entity_type == ENTITY_TYPE,
                        PermissionAuditLog.entity_id == entity_id,
                        PermissionAuditLog.target_user_id == target.id,
                        PermissionAuditLog.permission == "can_sign_contracts",
                    )
                ).order_by(PermissionAuditLog.performed_at)
            )).scalars().all()
            assert len(audit_rows) == 2, "لازم صفَّا audit: GRANT ثم REVOKE، بلا حذف الأول"
            assert audit_rows[0].action == AuditAction.GRANT
            assert audit_rows[1].action == AuditAction.REVOKE
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 8) check_permission — ثلاث حالات: None (لا override)، True (بعد
#    grant)، False (بعد revoke) — ومعزول عن مستخدم آخر بلا override
# ============================================================

@pytest.mark.asyncio
async def test_check_permission_none_true_false_states(db):
    granter = await _create_user(db, "em_check_by")
    target = await _create_user(db, "em_check_target")
    bystander = await _create_user(db, "em_check_bystander")
    entity_id = _entity_id()
    user_ids = [granter.id, target.id, bystander.id]
    entity_ids = [entity_id]

    try:
        svc = EntityMembershipService(db)

        before = await svc.check_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            permission="can_sign_contracts",
        )
        assert before is None

        await svc.grant_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts", granted_by=granter.id,
        )
        after_grant = await svc.check_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            permission="can_sign_contracts",
        )
        assert after_grant is True

        await svc.revoke_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts", revoked_by=granter.id,
        )
        after_revoke = await svc.check_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            permission="can_sign_contracts",
        )
        assert after_revoke is False

        bystander_check = await svc.check_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=bystander.id,
            permission="can_sign_contracts",
        )
        assert bystander_check is None, "مستخدم بلا override إطلاقًا يجب أن يرجع None دائمًا"
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 9) signature_pub_key — عمود nullable جديد (migration 030)، يُخزَّن
#    ويُقرأ فعليًا، بلا تأثير على أي عضوية بلا قيمة (تبقى NULL)
# ============================================================

@pytest.mark.asyncio
async def test_signature_pub_key_column_nullable_and_persists(db):
    user = await _create_user(db, "em_sigkey")
    entity_id = _entity_id()
    user_ids, entity_ids = [user.id], [entity_id]

    try:
        svc = EntityMembershipService(db)
        member = await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.SIGNATORY,
        )

        # افتراضيًا NULL — الإضافة الحالية لا تمرر signature_pub_key
        row = (await db.execute(
            select(EntityMembership).where(EntityMembership.id == member.id)
        )).scalar_one()
        assert row.signature_pub_key is None

        # تحديث مباشر (لا توجد دالة service مخصَّصة له بعد — خارج نطاق
        # هذه الجلسة، فقط العمود نفسه) + تحقق مستقل بجلسة منفصلة
        row.signature_pub_key = "-----BEGIN PUBLIC KEY-----TESTKEY-----END PUBLIC KEY-----"
        await db.commit()

        async with AsyncSessionLocal() as independent_db:
            persisted = (await independent_db.execute(
                select(EntityMembership).where(EntityMembership.id == member.id)
            )).scalar_one()
            assert persisted.signature_pub_key == (
                "-----BEGIN PUBLIC KEY-----TESTKEY-----END PUBLIC KEY-----"
            )
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)


# ============================================================
# 10) remove_member — إصلاح الفجوة السلوكية: يجب أن يحذف أيضًا أي
#     entity_permission_overrides مرتبطة، بحيث إعادة إضافة نفس العضو
#     لاحقًا لا ترث override قديم بلا منح جديد صريح
# ============================================================

@pytest.mark.asyncio
async def test_remove_member_also_deletes_related_overrides(db):
    granter = await _create_user(db, "em_rm_ov_by")
    target = await _create_user(db, "em_rm_ov_target")
    entity_id = _entity_id()
    user_ids = [granter.id, target.id]
    entity_ids = [entity_id]

    try:
        svc = EntityMembershipService(db)
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.REPRESENTATIVE,
        )
        await svc.grant_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, permission="can_sign_contracts",
            granted_by=granter.id, reason="regression test — pre-removal grant",
        )

        await svc.remove_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
        )

        # تحقق مستقل بجلسة منفصلة تمامًا: صفر overrides متبقية لهذا العضو
        async with AsyncSessionLocal() as independent_db:
            override_rows = (await independent_db.execute(
                select(EntityPermissionOverride).where(
                    and_(
                        EntityPermissionOverride.entity_type == ENTITY_TYPE,
                        EntityPermissionOverride.entity_id == entity_id,
                        EntityPermissionOverride.user_id == target.id,
                    )
                )
            )).scalars().all()
            assert len(override_rows) == 0, (
                "remove_member يجب أن يحذف overrides المرتبطة — بدون هذا "
                "الإصلاح كان الصف القديم يبقى موجودًا"
            )

            # سجل الـaudit (GRANT السابق) يبقى كما هو — لا يُحذَف، فقط الـoverride
            audit_rows = (await independent_db.execute(
                select(PermissionAuditLog).where(
                    and_(
                        PermissionAuditLog.entity_type == ENTITY_TYPE,
                        PermissionAuditLog.entity_id == entity_id,
                        PermissionAuditLog.target_user_id == target.id,
                    )
                )
            )).scalars().all()
            assert len(audit_rows) == 1
            assert audit_rows[0].action == AuditAction.GRANT

        # إعادة إضافة نفس العضو لاحقًا — لا يجب أن يرث الـoverride القديم
        await svc.add_member(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            tenant_id=TENANT_ID, role=EntityMembershipRole.REPRESENTATIVE,
        )
        after_re_add = await svc.check_permission(
            entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=target.id,
            permission="can_sign_contracts",
        )
        assert after_re_add is None, (
            "بعد إعادة الإضافة، لازم None (لا override إطلاقًا) — لا True موروث "
            "من المنح القديم قبل الإزالة"
        )
    finally:
        await _cleanup(db, entity_ids=entity_ids, user_ids=user_ids)
