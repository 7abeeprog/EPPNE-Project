# health — EntityMembership Implementation (`create_facility` فقط)

**النطاق:** تنفيذ فعلي (لا read-only) لنمط `EntityMembership` على
`health`، مقصور صراحة على `create_facility`. **ممنوع صراحة:**
`get_or_create_profile` (`tenant_id or 1` fallback)، `list_facilities`
(فلترة tenant بعد الجلب في بايثون) — لم يُلمَسا.

بُني على الفحص read-only السابق:
`.claude/reports/health-entity-membership-planning-session-log.md`.

---

## 1. Migration 052

`migrations/versions/052_health_facility_entity_id_fk_set_null.py`:

```python
revision = '052_health_facility_entity_id_fk_set_null'
down_revision = '051_sports_organizations_entity_id_fk_set_null'

def upgrade() -> None:
    op.create_foreign_key(
        'fk_health_facilities_entity_id_sovereign_entities',
        'health_facilities', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )

def downgrade() -> None:
    op.drop_constraint(
        'fk_health_facilities_entity_id_sovereign_entities',
        'health_facilities',
        type_='foreignkey',
    )
```

**Expand فقط** — `health_facilities.entity_id` كان عمود Integer عادي
بفهرس بس (`ix_health_facilities_entity_id`)، بدون أي `ForeignKeyConstraint`
إطلاقًا (اتأكَّد مباشرة على `\d health_facilities` قبل الكتابة — القيد
الوحيد الموجود كان `health_facilities_tenant_id_fkey`). `entity_id` أصلًا
`nullable=True` — صفر `alter_column` مطلوب.

**البيانات قبل التطبيق (فُحصت حيًا، `docker exec eppne_db psql`):** صف
واحد فقط في `health_facilities` (`id=1`, `name=p_ctor_health_facility`,
`entity_id IS NULL`) — بقية اختبار throwaway من 2026-08-14، صفر بيانات
إنتاج. التغيير آمن 100%.

**طُبِّقت فعليًا:**

```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 051_sports_organizations_entity_id_fk_set_null -> 052_health_facility_entity_id_fk_set_null
```

**تحقُّق حي بعد التطبيق (`\d health_facilities`):**

```
Foreign-key constraints:
    "fk_health_facilities_entity_id_sovereign_entities" FOREIGN KEY (entity_id) REFERENCES sovereign_entities_v2(id) ON DELETE SET NULL
    "health_facilities_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES academy_tenants(id)
```

---

## 2. Schema

`app/domains/health/schemas.py` — `HealthFacilityCreate`:

```python
class HealthFacilityCreate(BaseModel):
    entity_id: int = Field(description="الكيان السيادي المالك للمنشأة")
    name: str = Field(description="اسم المنشأة")
    facility_category: FacilityCategory = Field(description="تصنيف المنشأة")
    specialties: List[str] = Field(default_factory=list, description="التخصصات")
    facility_wallet_address: Optional[str] = Field(
        default=None,
        pattern="^0x[a-fA-F0-9]{40}$",
        description="عنوان المحفظة"
    )
```

`entity_id: int` **إجباري** (بدون `Optional`/`default`) — كانت موجودة
فقط في `HealthFacilityResponse` (قراءة)، دلوقتي مكشوفة للكتابة كمان.
`HealthFacilityResponse` بترث من `HealthFacilityCreate` وتُعيد تعريف
`entity_id: Optional[int]` بالفعل (كانت موجودة قبل هذه الجلسة) — بلا
تغيير مطلوب هناك.

---

## 3. Service

`app/domains/health/service.py` — الإضافات:

```python
from app.core.entity_membership_service import EntityMembershipService
from app.core.models import EntityMembershipRole

ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = HealthRepository(db)
        self.iot = IoTService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.membership = EntityMembershipService(db)
```

`create_facility` (النتيجة النهائية، `service.py:396-416`):

```python
async def create_facility(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> HealthFacility:
    """إنشاء منشأة صحية جديدة (للمشرفين فقط، وأعضاء الكيان المالك فقط)."""
    member = await self.membership.get_member(
        entity_type=ENTITY_TYPE, entity_id=data["entity_id"],
        user_id=user_id,
    )
    if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
        raise PermissionDeniedError("Not authorized to create facility for this entity")

    async with self.db.begin_nested():
        facility_data = {**data, "tenant_id": tenant_id}
        facility = await self.repo.create_facility(**facility_data)
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="FACILITY_CREATED",
            resource_id=facility.id,
            details={"name": facility.name}
        )
    await self.db.commit()
    return facility
```

فحص العضوية **أول سطر في الدالة، قبل `begin_nested()`** — نفس نمط
`insurance/service.py::create_policy:126-133` بالحرف. `PermissionDeniedError`
موجودة أصلًا في imports (كانت مستخدَمة في دوال تانية بالملف) — صفر import
جديد مطلوب لها.

---

## 4. الاختبار الموجود المُحدَّث

`tests/test_health_nameerror_and_fee_ordering_fix.py::test_create_facility_endpoint_persists_with_correct_audit_data`
كان بينادي `router.create_facility` مباشرة (يمر عبر الـService بالكامل)
— **اتأثر فعليًا** بفحص العضوية الجديد وكان سيفشل بـ `KeyError` (عدم
وجود `entity_id` في الـpayload) ثم `PermissionDeniedError` لو
اتصلح الـKeyError بدون عضوية حقيقية. الإصلاح: إنشاء `SovereignEntity`
throwaway + `EntityMembership` بدور `OWNER` للمستخدم `admin` قبل
الاستدعاء، وتمرير `entity_id=entity.id` في `HealthFacilityCreate`،
مع تنظيف العضوية والكيان في الـ`finally` (بالإضافة للتنظيف الموجود
أصلًا للمنشأة والمستخدم).

**لم تُعدَّل** بقية اختبارات نفس الملف (`test_trigger_emergency_...`,
`test_book_appointment_...`) — لا تلمس `create_facility` ولا فحص
العضوية.

**لم يُعدَّل** `tests/test_idempotency_truthy_bug_fix.py` — بينادي
`HealthRepository.create_facility` **مباشرة** (يتخطى الـService بالكامل
حيث يعيش فحص العضوية)، فغير متأثر إطلاقًا.

---

## 5. اختبار حي جديد

`tests/test_health_entity_membership_full_implementation.py` — نفس شكل
`test_tourism_sports_entity_membership_full_implementation.py` بالضبط،
3 سيناريوهات:

1. `test_create_facility_owner_succeeds_non_member_rejected` — عضو
   `OWNER` ينجح وبيتسجل `entity_id` صح، وغير عضو نفس الكيان يترفض بـ
   `PermissionDeniedError`.
2. `test_create_facility_executive_director_succeeds` — دور
   `EXECUTIVE_DIRECTOR` مسموح كمان (نفس insurance/transport/tourism_sports
   بالحرف).
3. `test_facility_entity_deletion_sets_null_not_cascade` — حذف الكيان
   السيادي المالك (مباشرة عبر SQL DELETE، خارج الـORM — نفس ملاحظة
   insurance/transport/tourism_sports إن `ON DELETE SET NULL` بينفَّذ جوّه
   Postgres مباشرة) → المنشأة **تفضل موجودة** (مش CASCADE)، و`entity_id`
   بيتحول لـ`NULL`.

**نتيجة التشغيل الحي (3 اختبارات جديدة + 4 اختبارات الملف المُحدَّث):**

```
tests/test_health_entity_membership_full_implementation.py::test_create_facility_owner_succeeds_non_member_rejected PASSED
tests/test_health_entity_membership_full_implementation.py::test_create_facility_executive_director_succeeds PASSED
tests/test_health_entity_membership_full_implementation.py::test_facility_entity_deletion_sets_null_not_cascade PASSED
tests/test_health_nameerror_and_fee_ordering_fix.py::test_create_facility_endpoint_persists_with_correct_audit_data PASSED
tests/test_health_nameerror_and_fee_ordering_fix.py::test_trigger_emergency_endpoint_persists_with_correct_audit_data PASSED
tests/test_health_nameerror_and_fee_ordering_fix.py::test_book_appointment_endpoint_success_charges_fee_exactly_once PASSED
tests/test_health_nameerror_and_fee_ordering_fix.py::test_book_appointment_fee_not_charged_when_appointment_creation_fails PASSED
7 passed, 8 warnings in 356.91s (0:05:56)
```

**7/7 PASSED.**

---

## 6. Regression الكاملة

تشغيلة كاملة (2038.00 ثانية / 33:57 دقيقة)، باستثناء
`test_affiliate_service_missing_methods.py` (collection error مسبق غير
مرتبط، موثَّق في جلسة `tourism-sports-entity-membership-implementation`
—`ActionCommission` اتشالت من `app/domains/affiliate/models.py` في
commit `2960d9d`، خارج نطاق هذه الجلسة تمامًا):

```
15 failed, 174 passed, 2 xfailed, 240 warnings in 2038.00s (0:33:57)
```

**مقارنة بالأساس الموثَّق (جلسة `tourism-sports-entity-membership-implementation`):**
`15 failed, 171 passed, 2 xfailed, 237 warnings`

`174 = 171 + 3` (الاختبارات الحية الجديدة فقط — الاختبار المُحدَّث في
`test_health_nameerror_and_fee_ordering_fix.py` كان موجودًا أصلًا، فعدد
الاختبارات الكلي زاد بمقدار الجديد فقط لا غير). نفس الـ15 فشل بالحرف
(نفس أسماء الملفات: `test_realestate_insurance_savepoint.py`،
`test_saas_active_subscription.py`، `test_user_repository_get_by_id_audit.py`،
`test_user_repository_get_user_audit.py` — كل واحد موثَّق في تقرير
investigation منفصل خاص بيه من جلسات سابقة، غير مرتبط بـhealth).

**صفر regression جديد.**

---

## 7. الملفات

**مُعدَّلة:**
- `app/domains/health/schemas.py`
- `app/domains/health/service.py`
- `tests/test_health_nameerror_and_fee_ordering_fix.py`

**جديدة:**
- `migrations/versions/052_health_facility_entity_id_fk_set_null.py`
- `tests/test_health_entity_membership_full_implementation.py`

---

## 8. نطاق متبقٍّ خارج هذه الجلسة (عمدًا وصراحةً، ممنوع لمسهما بالتعليمات)

- `get_or_create_profile` (`app/domains/health/service.py:100`):
  `tenant_id=tenant_id or 1` — fallback خطير لكيان دالة الملف الطبي
  الشخصي، **دالة مختلفة تمامًا** عن `create_facility`، لم تُلمس.
- `list_facilities` (`app/domains/health/service.py:406-418` +
  `repository.py:25-31`): الـRepository بيجيب كل المنشآت عبر كل الـ
  tenants بلا `WHERE tenant_id`، والفلترة بتحصل بعد الجلب في بايثون على
  مستوى الـService — **دالة مختلفة تمامًا** عن `create_facility`، لم
  تُلمس.
- `logistics`: لسه محتاج فحص read-only أول قبل أي تنفيذ (نفس تسلسل
  insurance → transport → tourism_sports → health).
