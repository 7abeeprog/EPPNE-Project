# إصلاح فجوة الصلاحيات في insurance + تصحيح ondelete

**التاريخ:** 2026-09-10
**النطاق:** إصلاح فعلي (كود + migration + اختبارات حية)، بناءً على فحص
read-only سابق موثَّق في
`.claude/reports/insurance-entity-membership-pattern-extraction-session-log.md`.
الهدف: سدّ فجوة الصلاحيات المكتشفة هناك، وتصحيح `ondelete`، **قبل** أي
تعميم على `tourism_sports`, `transport`, `health`, `logistics`.

---

## 0) ملخص تنفيذي

| البند | قبل | بعد |
|---|---|---|
| `create_policy` | صفر فحص عضوية — أي superuser ينشئ بوليصة باسم أي كيان | فحص `EntityMembershipService.get_member` قبل الإنشاء |
| `update_policy` | صفر فحص عضوية | نفس الفحص، باستخدام `policy.issuer_entity_id` المخزَّنة |
| `subscribe` | صفر فحص عضوية | **لم تُلمَس** (بالتصميم) |
| `issuer_entity_id` FK | `nullable=False`, `ondelete=CASCADE` | `nullable=True`, `ondelete=SET NULL` |
| Regression | — | `15 failed, 156 passed, 2 xfailed` (أساس موثَّق) | `15 failed, 160 passed, 2 xfailed` (+4 اختبارات جديدة، نفس الـ15 فشل بالحرف) |

---

## 1) فحص الصلاحيات — الإصلاح

### أ) `create_policy` (`app/domains/insurance/service.py`)

```python
async def create_policy(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> InsurancePolicy:
    """إنشاء بوليصة تأمين جديدة (للمشرفين فقط، وأعضاء الكيان المُصدِر فقط)."""
    member = await self.membership.get_member(
        entity_type=ENTITY_TYPE, entity_id=data["issuer_entity_id"],
        user_id=user_id,
    )
    if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
        raise PermissionDeniedError("Not authorized to create policy for this entity")

    async with self.db.begin_nested():
        ...
```

مطابق حرفيًا للنمط المطلوب (نفس نمط `review_claim` الموجود مسبقًا).
الفحص قبل أي `begin_nested()`/كتابة على القرص — رفض مبكر بلا أي أثر جانبي.

### ب) `update_policy` — تحقُّق من الافتراض أولًا

الافتراض المطلوب التأكد منه: *"`issuer_entity_id` على الأرجح مش قابل
للتعديل"*. **تم التحقق مباشرة من `schemas.py`:**

```python
class InsurancePolicyUpdate(BaseModel):
    name: Optional[str] = ...
    description: Optional[str] = ...
    base_premium_mrusdt: Optional[Decimal] = ...
    premium_cycle: Optional[PremiumCycle] = ...
    max_coverage_limit_mrusdt: Optional[Decimal] = ...
    terms_and_conditions: Optional[Dict[str, Any]] = ...
    is_active: Optional[bool] = ...
    # لا يوجد issuer_entity_id إطلاقًا
```

**الافتراض صحيح.** `issuer_entity_id` غير قابل للتعديل عبر
`PATCH /insurance/policies/{id}` — لا يوجد أي مسار في الكود لتغييره بعد
الإنشاء. لذلك مصدر الفحص الصحيح هو `policy.issuer_entity_id` المخزَّنة
على الصف (اللي جاية من `self.repo.get_policy(policy_id)`)، مش من `data`:

```python
async def update_policy(self, policy_id: int, tenant_id: int, reviewer_id: int, data: Dict[str, Any]) -> InsurancePolicy:
    policy = await self.repo.get_policy(policy_id)
    if not policy or cast(int, policy.tenant_id) != tenant_id:
        raise NotFoundError("Policy not found")

    member = await self.membership.get_member(
        entity_type=ENTITY_TYPE, entity_id=cast(int, policy.issuer_entity_id),
        user_id=reviewer_id,
    )
    if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
        raise PermissionDeniedError("Not authorized to update policy for this entity")

    return await self.repo.update_policy(policy_id, **data)
```

**تغيير توقيع ضروري (غير مذكور صراحةً في التعليمات لكنه استنتاج مباشر
من الطلب):** الدالة القديمة `update_policy(policy_id, tenant_id, data)`
ماكانتش بتاخد أي هوية للمستخدم المستدعي — مستحيل تنفيذ فحص عضوية
بدونها. أُضيف باراميتر `reviewer_id: int` (بنفس اسم `review_claim`
لتوحيد المصطلح عبر الملف)، و`router.py` اتحدَّث ليمرره:

```python
policy = await service.update_policy(
    policy_id=policy_id,
    tenant_id=cast(int, current_user.tenant_id),
    reviewer_id=cast(int, current_user.id),   # جديد
    data=data.model_dump(exclude_unset=True)
)
```

فُحص الكودبيس بالكامل بحثًا عن أي استدعاء آخر لـ`update_policy`/
`create_policy` (`grep` على مستوى المشروع) — لا يوجد أي مستدعٍ آخر غير
`router.py` ونفس ملفي الاختبار المذكورين في القسم 4.

### ج) `subscribe` — لم تُلمَس

بالتصميم الصريح المطلوب. اتأكَّد بالاختبار الحي (قسم 3) إن مستخدم بصفر
عضويات لسه يقدر يشترك بنجاح.

---

## 2) تصحيح `ondelete`

### فحص البيانات الحالية قبل الكتابة (كما طُلب)

```sql
SELECT COUNT(*) FROM insurance_policies;                              -- 9
SELECT COUNT(*) FROM insurance_policies WHERE issuer_entity_id IS NULL; -- 0
SELECT id, tenant_id, issuer_entity_id FROM insurance_policies;
-- 9 صفوف حقيقية، tenant_id=1 (8 صفوف) و tenant_id=16 (صف واحد)
-- issuer_entity_id ∈ {3, 4, 5, 6, 30} — كلها غير NULL
```

**النتيجة:** التغيير آمن. صفر صف هيتأثر فورًا — الأثر فقط على أي حذف
مستقبلي لكيان سيادي عليه بوليصة.

### الـmigration (Expand فقط، نفس نمط 046-048)

اسم القيد الفعلي اتأكَّد بالاستعلام المباشر على `pg_constraint` قبل
الكتابة: `insurance_policies_issuer_entity_id_fkey`. Postgres لا يسمح
بتعديل `ondelete` عبر `ALTER` مباشر → `drop_constraint` +
`create_foreign_key` بديل، بنفس نمط `047_saas_plan_service_access_fk_restrict.py`
بالحرف:

```python
# migrations/versions/049_insurance_issuer_entity_id_set_null.py
revision = '049_insurance_issuer_entity_id_set_null'
down_revision = '048_add_cancelled_at_to_saas_tenant_subscriptions'

def upgrade() -> None:
    op.alter_column('insurance_policies', 'issuer_entity_id',
                     existing_type=sa.Integer(), nullable=True)
    op.drop_constraint('insurance_policies_issuer_entity_id_fkey',
                        'insurance_policies', type_='foreignkey')
    op.create_foreign_key('insurance_policies_issuer_entity_id_fkey',
                           'insurance_policies', 'sovereign_entities_v2',
                           ['issuer_entity_id'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    # عكسي: يرجّع CASCADE + nullable=False
    ...
```

**طُبِّقت فعليًا** (`alembic upgrade head`، نجحت بلا أخطاء) والنتيجة
اتفحصت مباشرة على DB بعد التطبيق:

```
fk: ('insurance_policies_issuer_entity_id_fkey', 'n')   # n = SET NULL
nullable: YES
total policies still: 9   # صفر فقدان بيانات
```

`app/domains/insurance/models.py::InsurancePolicy.issuer_entity_id`
اتحدَّث ليطابق DB (`ForeignKey(..., ondelete="SET NULL"), nullable=True`)
— صفر drift بين الـmodel والـmigration.

---

## 3) اختبار حي (4/4 ناجحة، DB حقيقية، صفر mock)

الملف: `tests/test_insurance_entity_membership_gap_fix.py`

| # | الاختبار | يثبت |
|---|---|---|
| 1 | `test_create_policy_owner_succeeds_non_member_rejected` | `OWNER` ينجح؛ غير عضو يترفض `PermissionDeniedError` (→403 عبر `core/errors.py:39-41`) |
| 2 | `test_update_policy_member_succeeds_non_member_rejected` | نفس المنطق بـ`EXECUTIVE_DIRECTOR`، باستخدام `policy.issuer_entity_id` المخزَّنة |
| 3 | `test_subscribe_still_works_for_non_member_user` | مستخدم بصفر عضويات (اتأكَّد بالاستعلام المباشر `SELECT ... WHERE user_id=subscriber.id` → قائمة فارغة) لسه يقدر يشترك بنجاح |
| 4 | `test_issuer_entity_deletion_sets_null_not_cascade` | حذف كيان throwaway مرتبط ببوليصة throwaway → البوليصة تفضل موجودة (`refreshed is not None`) بـ`issuer_entity_id IS NULL` |

```
tests/test_insurance_entity_membership_gap_fix.py::test_create_policy_owner_succeeds_non_member_rejected PASSED
tests/test_insurance_entity_membership_gap_fix.py::test_update_policy_member_succeeds_non_member_rejected PASSED
tests/test_insurance_entity_membership_gap_fix.py::test_subscribe_still_works_for_non_member_user PASSED
tests/test_insurance_entity_membership_gap_fix.py::test_issuer_entity_deletion_sets_null_not_cascade PASSED
4 passed in 84.76s
```

**عثرة تقنية أثناء كتابة اختبار #4 (تستحق التوثيق لأي تعميم لاحق):**
`ON DELETE SET NULL` بيتنفَّذ داخل Postgres مباشرة عند تنفيذ الـ`DELETE`
— **مش عبر الـORM**. الـsession الأصلية (`db`) لسه شايلة الكائن `policy`
القديم في الـidentity map بقيمة `issuer_entity_id` القديمة، وأي `SELECT`
تاني على نفس الـsession بيرجّع نفس الكائن الكاش من الذاكرة بدل ما يعمل
round-trip حقيقي. المحاولة الأولى استخدمت `db.expire_all()` لحل المشكلة
— نجحت جزئيًا، لكنها كسرت الوصول لاحقًا لـ`creator.id` في `finally`
(كل كائنات الـsession اتـexpire، وأي attribute access بعد كده بيحاول
lazy-load متزامن، وده **ممنوع في `AsyncSession`** →
`MissingGreenlet` error). **الحل النهائي:** التحقق بجلسة
`AsyncSessionLocal()` منفصلة تمامًا (نفس نمط الـcleanup sessions
الموجود بالفعل في `test_insurance_getter_endpoints_wiring.py`)، بدل أي
`expire`/`refresh` على الـsession الأصلية.

---

## 4) Regression

### اختباران موجودان سابقًا اتأثروا واتصلحوا (نفس الجلسة)

كلاهما كان بينشئ بوليصة/يعدّلها عبر `InsuranceService` بمستخدم **بدون
أي عضوية كيان** — كانوا هيفشلوا بـ`PermissionDeniedError` جديدة بعد
الإصلاح لولا التحديث:

1. `tests/test_insurance_getter_endpoints_wiring.py::test_update_policy_real_record_and_tenant_isolation`
   — كانت بتنادي `service.update_policy(policy_id, OTHER_TENANT_ID, {"name": "hacked"})`
   بتوقيع موضعي قديم (3 معاملات). اتحدَّثت: عضوية `OWNER` throwaway
   تتحط لـ`user` على `EXISTING_ISSUER_ENTITY_ID=4` قبل الاستدعاء
   الناجح، والاستدعاءات بقت بـkeyword args (`reviewer_id=user.id`،
   `data={...}`) لمطابقة التوقيع الجديد. تنظيف العضوية مضاف في `finally`.

2. `tests/test_audit_log_signature_fix.py::test_insurance_create_policy_audit_log_no_500_and_policy_persisted`
   — نفس السبب لـ`create_policy` (`admin` بدون عضوية على
   `EXISTING_ISSUER_ENTITY_ID=3`). اتحدَّثت بنفس الأسلوب (عضوية
   throwaway + تنظيف).

كلا التعديلين تم التحقق منهما حيًا (`pytest`، PASSED) بعد التحديث.

### تشغيلة كاملة (`pytest tests/ --continue-on-collection-errors`، 609 ثانية)

```
FAILED tests/test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering
FAILED tests/test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes
FAILED tests/test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug
FAILED tests/test_user_repository_get_by_id_audit.py::test_zamakana_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_transport_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_tourism_sports_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_tenders_auctions_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_service_marketplace_get_user_correct_and_wrong_tenant
FAILED tests/test_user_repository_get_by_id_audit.py::test_realestate_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_arbitration_syndicates_register_affiliate_commission_get_by_id_fixed
FAILED tests/test_user_repository_get_by_id_audit.py::test_manufacturing_get_user_correct_and_wrong_tenant
FAILED tests/test_user_repository_get_by_id_audit.py::test_invitations_get_user_correct_and_wrong_tenant
FAILED tests/test_user_repository_get_by_id_audit.py::test_insurance_get_user_and_get_user_email_all_three_call_paths
FAILED tests/test_user_repository_get_user_audit.py::test_employment_register_affiliate_commission_reaches_referred_by_layer
FAILED tests/test_user_repository_get_user_audit.py::test_digital_twin_register_affiliate_commission_reaches_referred_by_layer
ERROR tests/test_affiliate_service_missing_methods.py   # ImportError: ActionCommission — استيراد قديم غير مرتبط
15 failed, 160 passed, 2 xfailed, 221 warnings, 1 error in 609.04s
```

**مطابقة تامة للأساس الموثَّق مسبقًا** (`15 failed, 156 passed, 2
xfailed`، آخر ذكر في `PROGRESS_LOG.md` — جلسة
`backlog-idempotency-check-truthy-misinterpretation-health`):
`160 = 156 + 4` (الاختبارات الأربعة الجديدة)، ونفس عدد/توزيع الـ15 فشل
+ نفس الـerror المعروف.

**تحقُّق فردي إضافي (احتياط):**
`test_insurance_get_user_and_get_user_email_all_three_call_paths` ظهر
في قائمة الفشل واسمه يوحي بعلاقة مباشرة بـ`insurance` — تم عزله وتشغيله
منفردًا للتأكد إنه مش regression جديد من هذه الجلسة:

```
E    assert False
E     +  where False = any(<genexpr> ...)
tests\test_user_repository_get_by_id_audit.py:569: AssertionError
# الفشل في: assert any("referred_by" in r for r in cap.records)
```

الفشل في سطر بيفحص محتوى `logging` بعد استدعاء
`svc._register_affiliate_commission(...)` — دالة لم تُلمَس إطلاقًا في
هذه الجلسة (مشكلة منفصلة تمامًا بالـaffiliate logging، جزء من نفس
مجموعة الـ15 فشل المرتبطة بملف `test_user_repository_get_by_id_audit.py`
بالكامل — Backlog #1 `UserRepository.get_by_id` tenant_id، commit
`33f5b71`، خارج نطاق هذه الجلسة تمامًا). **صفر علاقة بتغييرات
`create_policy`/`update_policy`/migration 049.**

---

## 5) ⚠️ اكتشاف جانبي غير مُصلَح عمدًا (يحتاج قرارًا منفصلًا)

`InsurancePolicyResponse` (`schemas.py:41`) وارثة
`InsurancePolicyCreate`، واللي فيها:

```python
issuer_entity_id: int = Field(description="معرف الكيان المصدر")  # غير Optional
```

بعد migration 049، أي بوليصة اتمسح كيانها المُصدِر (سيناريو **جديد
ومسموح دلوقتي** بعد التصحيح) هتبقى `issuer_entity_id IS NULL` فعليًا في
DB. أي طلب `GET /insurance/policies/{id}` أو `GET /insurance/policies`
عليها هيفشل بـPydantic response-validation error (500 داخلي) وقت
تجميع الـresponse، لأن `int` مايقبلش `None`.

**لم يُصلَح في هذه الجلسة** — لم يكن ضمن البنود الأربعة المطلوبة صراحةً،
وتعديل الـschema يستأهل قرارًا مستقلًا (هل `Optional[int]` في
`InsurancePolicyResponse` وحدها كافية، ولا فيه حاجة أوسع زي إظهار حالة
"الكيان المُصدِر محذوف" للعميل؟). **مخاطرة عملية منخفضة حاليًا** (تتطلب
حذف فعلي لكيان سيادي عليه بوليصة نشطة — إجراء نادر)، لكنها **موجودة
الآن ولم تكن موجودة قبل هذه الجلسة** (قبلها كان `CASCADE` يمنع وصول
`issuer_entity_id` لـNULL أصلًا عبر مسح البوليصة نفسها). يُنصح بفتح
backlog منفصل قبل أي اعتماد إنتاجي على migration 049.

---

## 6) الملفات

**معدَّلة:**
- `app/domains/insurance/service.py` (فحص عضوية في `create_policy`/`update_policy` + توقيع `update_policy` الجديد)
- `app/domains/insurance/router.py` (تمرير `reviewer_id`)
- `app/domains/insurance/models.py` (`issuer_entity_id`: `nullable=True`, `ondelete="SET NULL"`)
- `tests/test_insurance_getter_endpoints_wiring.py` (عضوية throwaway + توقيع جديد)
- `tests/test_audit_log_signature_fix.py` (عضوية throwaway)
- `PROGRESS_LOG.md` (سجل هذه الجلسة)

**جديدة:**
- `migrations/versions/049_insurance_issuer_entity_id_set_null.py`
- `tests/test_insurance_entity_membership_gap_fix.py`

**الحالة النهائية:** ✅ الفجوة اتسدَّت، الـmigration مُطبَّقة فعليًا على
DB التطوير ومتحقَّق منها حيًا، صفر regression (نفس الـ15 فشل المعروف
بالحرف + 4 نجاحات جديدة). تعميم النمط على `tourism_sports`/`transport`/
`health`/`logistics` **لسه ما بدأش** — خارج نطاق هذه الجلسة، وقرار
البند #5 (schema `Optional`) لسه مفتوح.
