# `test_entity_membership_foundation.py`

## المرجع الأصلي
- `.claude/plans/entity-membership-foundation-session-instructions.md` (تعليمات الجلسة).
- `.claude/plans/entity-membership-technical-design.md` (الـschema الكامل — جداول، أعمدة، قيود، فهارس).
- `.claude/plans/entity-permissions-and-lifecycle-vision.md` و`.claude/plans/entity-membership-system-vision.md` (رؤية نظام الصلاحيات ثلاثي المكوّنات).
- `.claude/reports/entity-membership-foundation-session-log.md` (سجل الجلسة كاملًا — القراءة، التصميم، الموافقات، التحقق الحي).

## السياق
الجلسة 1 من 2 في مسار توحيد صلاحيات/عضوية الكيانات. تبني **الأساس العام**
فقط: ثلاثة جداول جديدة كليًا (`entity_memberships`,
`entity_permission_overrides`, `permission_audit_log`) في `app/core/`،
تعميمًا لنظام `EntityRole`/`EntityRepresentative`/`can_sign_contracts`
الحالي في `sovereign_entities` — **بمعزل تام** عنه. الربط الفعلي (تحديث
`sovereign_entities/service.py` وحذف الموديلات القديمة) جلسة 2 منفصلة
تمامًا، لم تبدأ.

## الإصلاح/البناء المُطبَّق

1. **`app/core/models.py`** (جديد) — `EntityMembershipRole` (Enum منفصل
   عمدًا عن `sovereign_entities.EntityRole`)، `AuditScope`, `AuditAction`،
   وثلاثة موديلات SQLAlchemy.
2. **Migration `029_create_entity_membership_foundation`** —
   `down_revision='028_create_affiliate_action_commissions'`. صفر لمس على
   أي جدول موجود.
3. **`app/core/entity_membership_repository.py`** — `EntityMembershipRepository`:
   عمليات DB خام (`add_member`, `update_member_role`, `remove_member`,
   `get_member`, `list_members`, `list_entities_for_user`)، زائد دالتين
   داخليتين `_upsert_override`/`_insert_audit_row` (بادئة `_` — لا تُستدعيان
   إلا من الـService).
4. **`app/core/entity_membership_service.py`** — `EntityMembershipService`:
   تمرير مباشر لعمليات العضوية، زائد `grant_permission`/`revoke_permission`
   (المسار الوحيد المتاح لتعديل `entity_permission_overrides` — يضمنان
   تسجيل `permission_audit_log` تلقائيًا في نفس الـtransaction)، و
   `check_permission`. **صفر استيراد من `sovereign_entities` أو أي دومين
   وظيفي آخر** — docstring صريح يوضح أن فحص التفويض (هل current_user مسموح
   له يستدعي هذه الدوال) مسؤولية الدومين المستدعي وقت الدمج في الجلسة 2.
5. **اكتشاف جانبي مُصحَّح بموافقة صريحة:** `entity-membership-technical-design.md`
   يكتب حرفيًا `tenant_id ... FK → tenants.id` — لا يوجد جدول `tenants` في
   المشروع فعليًا، الجدول الحقيقي `academy_tenants`. استُخدم
   `academy_tenants.id` فعليًا (تطبيق لنية المستند لا لنصه الحرفي)، موثَّق
   بالتفصيل في سجل الجلسة §3.

## إيه اللي بيتحقق منه هذا الملف

8 اختبارات — بمنهجية "تحقق مستقل" (SELECT مباشر بعد كل استدعاء، وحيث ينطبق
عبر **جلسة `AsyncSessionLocal` منفصلة تمامًا** — لا مجرد ثقة بالقيمة
المُرجَعة من نفس الاستدعاء):

| # | الاختبار | ما بيثبته |
|---|---|---|
| 1 | `test_add_member_and_list_members_by_entity` | إنشاء عضوية + استعلام "أعضاء كيان بعينه" (فهرس `(entity_type, entity_id)`) |
| 2 | `test_unique_constraint_blocks_second_role_same_entity_user` | القيد الفريد `UNIQUE(entity_type, entity_id, user_id)` يفشل فعليًا بـ`IntegrityError` عند محاولة دور ثانٍ لنفس الزوج |
| 3 | `test_list_entities_for_user_isolated_from_other_users` | استعلام "كيانات مستخدم بعينه" (فهرس `(user_id, tenant_id)`)، معزول عن عضويات مستخدم آخر |
| 4 | `test_change_role_updates_same_row` | تعديل الدور يحدِّث نفس الصف (لا صف جديد) |
| 5 | `test_remove_member_deletes_row` | إزالة عضوية فعليًا |
| 6 | `test_grant_permission_creates_override_and_autologs_audit` | **الضمان الأساسي**: `grant_permission` ينشئ صف override + سطر `permission_audit_log` (`GRANT`) تلقائيًا، بلا أي استدعاء منفصل لدالة audit من الاختبار نفسه |
| 7 | `test_revoke_permission_upserts_same_row_and_appends_audit` | `revoke_permission` يُحدِّث **نفس صف** الـoverride (upsert، لا صف ثانٍ — `COUNT`=1 دائمًا)، ويضيف سطر `audit` ثانٍ (`REVOKE`) بلا حذف الأول |
| 8 | `test_check_permission_none_true_false_states` | ثلاث حالات: `None` (لا override)، `True` (بعد منح)، `False` (بعد سحب)، ومعزول عن مستخدم آخر بلا override إطلاقًا |

## بيانات throwaway
- `entity_type="_TEST_ENTITY"` ثابت في كل الاختبارات — لا تقاطع مع
  `SOVEREIGN_ENTITY` أو أي نوع كيان حقيقي.
- `entity_id` رقم عشوائي فريد لكل اختبار (بادئة `900_000_000+`) — Polymorphic
  بلا FK حقيقي، فقط لازم يكون فريدًا للعزل.
- مستخدمون جدد لكل اختبار (`UserService.register`، بادئة `em_*` + `uuid4`
  فريد) — صفر إعادة استخدام بيانات من جلسات سابقة.
- تنظيف كامل في `finally` بالترتيب الصحيح (FK `RESTRICT` على `granted_by`/
  `performed_by`): `permission_audit_log` → `entity_permission_overrides` →
  `entity_memberships` → `users`.
- **احتياط IntegrityError موثَّق سابقًا في المشروع** (نفس نمط
  `test_ai_agents_execute_action.py`/`test_saas_active_subscription.py`):
  الاستدعاء المتوقَّع فشله بـ`IntegrityError` (اختبار #2) يُنفَّذ في **جلسة
  `AsyncSessionLocal` مستقلة تمامًا** — إعادة استخدام جلسة `db` الأصلية بعد
  `IntegrityError` مباشرة (حتى بعد `rollback()`) تسبَّبت فعليًا في
  `sqlalchemy.exc.MissingGreenlet` عند أول محاولة (تفاعل `pool_pre_ping=True`
  مع asyncpg بعد فشل commit) — مُصحَّح بعزل الجلسة، لا بإزالة السيناريو.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_entity_membership_foundation.py -v
```
يحتاج قاعدة `eppne_v2` حقيقية شغّالة (Docker `eppne_db`، منفذ 5435) بعد
تطبيق migration `029_create_entity_membership_foundation`
(`PYTHONIOENCODING=utf-8 ./venv/Scripts/alembic.exe upgrade head`).

**آخر تشغيل مُوثَّق [2026-08-20]:** 8 passed (تشغيلتان متتاليتان، صفر
تذبذب). تحقق مستقل عبر `psql` بعد التشغيلتين أكَّد **صفر بيانات throwaway
متبقية** في الجداول الثلاثة وجدول `users`.
