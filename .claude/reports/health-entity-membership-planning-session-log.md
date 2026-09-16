# health — EntityMembership Planning (read-only)

**النطاق:** فحص read-only بحت لتجهيز خطة تنفيذ نمط EntityMembership على
domain `health`، بنفس منهجية [[insurance]]/[[transport]]/[[tourism_sports]].
**ممنوع أي تعديل كود في هذه الجلسة — التزمنا بده.**

---

## 1. موديل `HealthFacility` كامل

`eppne-backend/app/domains/health/models.py:71-94`

```python
class HealthFacility(Base):
    __tablename__ = "health_facilities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    facility_category = Column(SQLEnum(FacilityCategory), nullable=False)
    supported_targets = Column(JSONB, default=list)
    specialties = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)

    facility_wallet_address = Column(String(42), nullable=True)
    on_chain_identity = Column(String(255), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_health_facility_tenant", "tenant_id", "is_active"),
        Index("ix_health_facility_category", "tenant_id", "facility_category"),
    )
```

**تأكيد الجرد القديم:** `entity_id` (سطر 76) موجود فعلًا، `nullable=True`،
**بلا `ForeignKey`** (مقارنةً بـ `tenant_id` اللي جنبه مباشرة وعنده FK صريح
لـ `academy_tenants.id`) — نفس النمط اللي شُفناه في insurance/transport
قبل الإصلاح (migrations 049/050/051 كلها أضافت FK `ON DELETE SET NULL`
لعمود كان بلا أي قيد).

**تصحيح جزئي عن الجرد القديم:** الجرد القديم قال "بلا أي استخدام حتى في
الـresponse schema" — ده لم يعد دقيقًا. `HealthFacilityResponse` (انظر
قسم 3) **بيحتوي فعلًا على `entity_id: Optional[int]`** الآن. يعني القراءة
مكشوفة، لكن الكتابة (`HealthFacilityCreate`) لسه **مش** مكشوفة — تفصيل
مهم لتصميم الخطوة القادمة (قسم 3).

---

## 2. فحص مباشر على DB — هل فيه بيانات حقيقية؟

```
docker exec eppne_db psql -U eppne -d eppne_v2 -c
"SELECT count(*), count(entity_id), count(DISTINCT tenant_id) FROM health_facilities;"

 total | with_entity_id | distinct_tenants
-------+----------------+------------------
     1 |              0 |                1
```

الصف الوحيد:

```
 id | tenant_id | entity_id |          name          | facility_category | is_active | is_deleted |          created_at
----+-----------+-----------+------------------------+--------------------+-----------+------------+-------------------------------
  1 |         1 |  (NULL)   | p_ctor_health_facility | CLINIC             | t         | f          | 2026-08-14 17:12:23.713931+00
```

- **صف واحد فقط**، `entity_id` فارغ تمامًا (NULL) — صفر استخدام فعلي حتى
  اللحظة.
- الاسم `p_ctor_health_facility` بادئته `p_` هي نفس نمط بيانات الاختبار
  المستخدَم في helper الاختبارات (`_create_user(db, "p_...")` في
  `test_health_nameerror_and_fee_ordering_fix.py` وغيرها) — **هذا صف
  throwaway من تشغيل اختبار سابق بتاريخ 2026-08-14، مش بيانات إنتاج
  حقيقية.**
- الاعتماديات المباشرة على `facility_id=1`:
  - `facility_departments`: 0 صفوف
  - `emergency_dispatches`: 0 صفوف
  - `medical_appointments`: **صف واحد** (id=1, patient_user_id=38,
    doctor_id=39, status=SCHEDULED, نفس تاريخ 2026-08-14) — أيضًا واضح
    إنه بيانات اختبار (نفس التوقيت بالظبط، أرقام مستخدمين اختبارية).

**الخلاصة:** زي insurance/transport/tourism_sports بالظبط — لا توجد
بيانات إنتاج حقيقية تعتمد على `entity_id` أو حتى على الصف الوحيد
الموجود. الطريق مفتوح لإضافة FK `ON DELETE SET NULL` بلا أي backfill أو
مخاطرة على بيانات حية.

---

## 3. العملية الإدارية الحساسة — `create_facility`

### الحالة بعد إصلاح NameError (جلسة `health-nameerror-and-fee-ordering-fix`، 2026-09-10)

**`service.py:391-404`:**

```python
async def create_facility(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> HealthFacility:
    """إنشاء منشأة صحية جديدة (للمشرفين فقط)."""
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

هذا هو الكود **بعد** إصلاح NameError — `tenant_id` بقى باراميتر رسمي
للدالة (كان قبل الإصلاح غير موجود أصلًا وكان بيتسبب في NameError مضمون
عند أول استدعاء، موثَّق في `PROGRESS_LOG.md` سطر 3950+ و
`.claude/reports/health-nameerror-and-fee-ordering-fix-session-log.md`).

**`router.py:211-225`:**

```python
@router.post("/facilities", response_model=HealthFacilityResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_facility(
    data: HealthFacilityCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    facility = await service.create_facility(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return facility
```

**`repository.py:14-19`:**

```python
async def create_facility(self, **kwargs) -> HealthFacility:
    facility = HealthFacility(**kwargs)
    self.db.add(facility)
    await self.db.flush()
    await self.db.refresh(facility)
    return facility
```

**حماية الوصول الحالية:** `get_current_superuser` فقط (لا يوجد فحص
عضوية على مستوى الكيان المُصدِر — ده بالظبط نفس الفجوة اللي كانت موجودة
في `create_policy` قبل إصلاح insurance).

---

## 4. هل `create_facility` بتاخد `entity_id` في الـschema أصلًا؟

**لأ — محتاجة كشف صريح، بالظبط زي حالة tourism_sports.**

`schemas.py:16-32`:

```python
class HealthFacilityCreate(BaseModel):
    name: str = Field(description="اسم المنشأة")
    facility_category: FacilityCategory = Field(description="تصنيف المنشأة")
    specialties: List[str] = Field(default_factory=list, description="التخصصات")
    facility_wallet_address: Optional[str] = Field(
        default=None,
        pattern="^0x[a-fA-F0-9]{40}$",
        description="عنوان المحفظة"
    )


class HealthFacilityResponse(HealthFacilityCreate):
    id: int
    entity_id: Optional[int]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

- `HealthFacilityCreate` **لا يحتوي `entity_id`** → `data.model_dump()`
  في الراوتر لا يمكن أن يحمل `entity_id` أبدًا → أي فحص عضوية مستقبلي
  (`membership.get_member(entity_type=ENTITY_TYPE, entity_id=data["entity_id"], ...)`)
  **سيفشل بـ `KeyError` فورًا** ما لم يُضَف الحقل للـschema أولًا — تمامًا
  نفس الحاجز اللي وُثِّق في خطة tourism_sports.
- `HealthFacilityResponse` **بيحتوي `entity_id`** بالفعل (القراءة مكشوفة
  من قبل) — فقط الكتابة (`Create`) ناقصة.
- **الخطوة اللازمة (لخطة التنفيذ، ليست جزءًا من هذه الجلسة):** إضافة
  `entity_id: int` (أو `Optional[int]` بحسب القرار على الإلزامية) لـ
  `HealthFacilityCreate`، ثم في `service.create_facility` استدعاء
  `EntityMembershipService.get_member(entity_type=ENTITY_TYPE, entity_id=data["entity_id"], user_id=user_id)`
  والتحقق من الدور (`OWNER`/`EXECUTIVE_DIRECTOR`) قبل الإنشاء — نفس نمط
  `insurance/service.py:126-133`.
- **قيمة `ENTITY_TYPE` المتوقعة:** `"SOVEREIGN_ENTITY"` — القيمة الموحَّدة
  المستخدَمة بالفعل في `sovereign_entities`, `insurance`, `transport`,
  `tourism_sports` (كلها `ENTITY_TYPE = "SOVEREIGN_ENTITY"` مع نفس
  التعليق التوضيحي "نفس القيمة المستخدَمة في sovereign_entities/service.py").
- **رقم migration التالي المتاح:** `052` (آخر واحدة مستخدَمة هي
  `051_sports_organizations_entity_id_fk_set_null.py` من جلسة
  [[tourism_sports EntityMembership implementation]]).

---

## 5. المستدعون المباشرون للدالة في الاختبارات

بحث `create_facility` / `health_facilities` في `eppne-backend/tests/`:

1. **`tests/test_health_nameerror_and_fee_ordering_fix.py`**
   - سطر 61: `from app.domains.health.router import book_appointment, call_emergency, create_facility`
   - سطر 108-138: `test_create_facility_endpoint_persists_with_correct_audit_data` —
     بيستدعي **الراوتر مباشرة** (`create_facility(data=data, tenant=tenant, current_user=admin, db=db)`)،
     نفس أسلوب باقي الدومينز (استدعاء دالة الراوتر مباشرة بدل TestClient).
     `HealthFacilityCreate` المُستخدَمة هنا **لا تمرر `entity_id`** — لو
     اتضاف فحص عضوية إلزامي مستقبلًا، هذا الاختبار (وأي اختبار مشابه)
     هيحتاج تحديث ليمرر `entity_id` + عضوية صالحة، وإلا هيفشل.

2. **`tests/test_idempotency_truthy_bug_fix.py`**
   - سطر 141-145: استدعاء **مباشر على الـRepository** (`health_repo.create_facility(tenant_id=..., name=..., facility_category=...)`)
     — بيتخطى الـService بالكامل، فمش هيتأثر بفحص عضوية مستقبلي يُضاف على
     مستوى الـService (لأنه لا يمر عبره أصلًا). يستخدمها فقط كـfixture
     لاختبار idempotency على `book_appointment`.

لا يوجد أي استدعاء آخر لـ`create_facility` في الاختبارات.

---

## 6. تقاطع الباجات المعروفة الأخرى مع `create_facility`؟

المطلوب التحقق منه (بدون معالجته هنا — النطاق عضوية فقط):

### أ) `tenant_id or 1` fallback

**موجود، لكن في مكان مختلف تمامًا — لا يتقاطع مع `create_facility`.**

`service.py:93-108`، دالة `get_or_create_profile` (الملف الطبي الشخصي،
مش المنشآت):

```python
async def get_or_create_profile(self, user_id: int, tenant_id: Optional[int] = None) -> MedicalProfile:
    profile = await self.repo.get_medical_profile(user_id)
    if not profile:
        async with self.db.begin_nested():
            profile = await self.repo.create_medical_profile(
                user_id=user_id,
                tenant_id=tenant_id or 1,   # ← الباج هنا
                ...
            )
```

`create_facility` (قسم 3) بياخد `tenant_id` كـباراميتر إلزامي رسمي من
الراوتر (`tenant: AcademyTenant = Depends(get_current_tenant)`) — **لا
يوجد أي `or 1` fallback في مساره**. الباجان منفصلان تمامًا: واحد في
`MedicalProfile` (بيانات المريض)، والتاني (المطلوب فحصه هنا) في
`HealthFacility` (المنشأة الإدارية).

### ب) فلترة tenant بعد الجلب في بايثون

**موجودة، وأيضًا في مكان مختلف — `list_facilities` مش `create_facility`.**

`service.py:406-418`:

```python
async def list_facilities(
    self, tenant_id: int, category: Optional[str] = None, skip: int = 0, limit: int = 50
) -> List[HealthFacility]:
    """جلب قائمة المنشآت الصحية للمستأجر."""
    # نحتاج إلى تعديل دالة list_facilities في الـ Repository لتقبل tenant_id
    # لكن حالياً نمررها بدون tenant_id، سنقوم بتحسينها
    facilities = await self.repo.list_facilities(category, skip, limit)
    # تصفية حسب tenant_id (مؤقت حتى يتم تحديث الـ Repository)
    return [f for f in facilities if f.tenant_id == tenant_id]  # type: ignore
```

والـRepository (`repository.py:25-31`) فعلًا بيجيب **كل** المنشآت النشطة
عبر كل الـtenants (بلا `WHERE tenant_id`)، والفلترة بتحصل بعد الجلب في
بايثون على مستوى الـService — نفس نمط الباج الموصوف في الجرد الأصلي.
هذا **منفصل عن** `create_facility` (الإنشاء بيسجل `tenant_id` صح دايمًا،
المشكلة في القراءة/القائمة فقط).

**الخلاصة:** ولا واحد من الباجين المعروفين يتقاطع مع `create_facility`
أو مع فحص العضوية المخطَّط له. الاثنان في دوال مختلفة تمامًا
(`get_or_create_profile` و`list_facilities`) ويبقيان خارج نطاق هذه
الخطة تمامًا — يُتركا كما هما لجلسة منفصلة لو قُرِّر معالجتهما، زي ما
اتفقنا [[Split urgent side-findings from investigations]].

---

## 7. ملخص الخطوات المطلوبة لخطة التنفيذ (غير منفذة هنا)

1. Migration `052`: إضافة `ForeignKey("sovereign_entities.id", ondelete="SET NULL")`
   على `health_facilities.entity_id` (نفس نمط 049/050/051).
2. إضافة `entity_id` لـ `HealthFacilityCreate` في `schemas.py`.
3. في `HealthService.create_facility`: استدعاء
   `EntityMembershipService.get_member(entity_type=ENTITY_TYPE, entity_id=data["entity_id"], user_id=user_id)`
   وفحص `role in [OWNER, EXECUTIVE_DIRECTOR]` قبل الإنشاء (نفس
   `insurance/service.py:126-133`).
4. تعريف `ENTITY_TYPE = "SOVEREIGN_ENTITY"` أعلى `health/service.py`
   (نفس القيمة الموحدة في باقي الدومينز).
5. تحديث `test_create_facility_endpoint_persists_with_correct_audit_data`
   (وأي اختبار جديد) ليمرر `entity_id` + عضوية صالحة.
6. **خارج النطاق عمدًا** (تُترك مفتوحة، توثَّق فقط): `tenant_id or 1` في
   `get_or_create_profile`، والفلترة بعد الجلب في `list_facilities`.
