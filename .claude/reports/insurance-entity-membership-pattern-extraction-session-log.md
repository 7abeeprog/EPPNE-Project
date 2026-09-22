# استخراج وصفة نمط EntityMembership من insurance (فحص read-only)

**التاريخ:** 2026-09-10
**النطاق:** فحص read-only بحت — بدون أي تعديل كود. الهدف: توثيق الوصفة الكاملة
المستخدَمة في `insurance` لتعميمها لاحقًا على `tourism_sports`, `transport`,
`health`, `logistics`.

---

## 1) `InsurancePolicy.issuer_entity_id` — تعريف العمود الكامل

**الملف:** `eppne-backend/app/domains/insurance/models.py:52`
**الجدول:** `insurance_policies`

```python
issuer_entity_id = Column(
    Integer,
    ForeignKey("sovereign_entities_v2.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```

- **nullable:** `False` — إجباري على مستوى قاعدة البيانات.
- **الجدول المُشار إليه:** `sovereign_entities_v2` (عمود `id`).
- **ondelete:** `CASCADE` — لو اتمسح الكيان السيادي، تتمسح كل بوالص التأمين
  المرتبطة به تلقائيًا (ملاحظة: هذا خيار قوي جدًا، عكس `PensionRecord
  .source_entity_id` بنفس الملف اللي بيستخدم `ondelete="SET NULL"` +
  `nullable=True` — تناقض تصميمي داخل نفس الدومين يستحق الانتباه لو
  التعميم هيتم بنفس القوة).
- **index:** `True` — عمود مفهرس منفصل (`ix_insurance_policies_issuer_entity_id`
  حسب الـmigration، راجع القسم 4).

---

## 2) إزاي `EntityMembershipService` بتتحط وتُستخدم

### أ) الحقن في `__init__`

**الملف:** `eppne-backend/app/domains/insurance/service.py:36-41`

```python
class InsuranceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InsuranceRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client
        self.membership = EntityMembershipService(db)
```

- الاستيراد: `from app.core.entity_membership_service import EntityMembershipService`
  (`service.py:24`) و `from app.core.models import EntityMembershipRole`
  (`service.py:25`).
- ثابت على مستوى الموديول: `ENTITY_TYPE = "SOVEREIGN_ENTITY"` (`service.py:32`)
  — نفس القيمة الحرفية المستخدَمة في
  `eppne-backend/app/domains/sovereign_entities/service.py:37` (تم التحقق
  بالمقارنة المباشرة بين الملفين — القيمة متطابقة حرفيًا).

### ب) فحص الصلاحية في `review_claim`

**الملف:** `eppne-backend/app/domains/insurance/service.py:436-472` (الدالة كاملة)
**السطر الحاسم لفحص الصلاحية:** `service.py:467-472`

```python
member = await self.membership.get_member(
    entity_type=ENTITY_TYPE, entity_id=cast(int, policy.issuer_entity_id),
    user_id=reviewer_id,
)
if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
    raise PermissionDeniedError("Not authorized to review this claim")
```

**السياق الكامل قبل الفحص** (`service.py:460-466`) — إزاي بيوصل لـ
`policy.issuer_entity_id` أصلًا:

```python
claim = await self.repo.get_claim(claim_id)
if not claim or cast(int, claim.tenant_id) != tenant_id:
    raise NotFoundError("Claim not found")

subscription = await self.repo.get_subscription(claim.subscription_id)
policy = await self.repo.get_policy(subscription.policy_id)
```

أي أن السلسلة هي: `claim → subscription → policy → policy.issuer_entity_id`،
ثم `EntityMembershipService.get_member(entity_type, entity_id, user_id)`
بيرجّع العضوية (أو `None`)، والقرار النهائي (مين الأدوار المسموح لها) محصور
بالكامل في الدومين المستدعي (`insurance`) — مطابق تمامًا للتوثيق الصريح في
`app/core/entity_membership_service.py:20-26` اللي بيقول إن فحص التفويض
"مش مسؤولية" الطبقة دي، ومسؤولية الدومين المستدعي حصرًا.

**ملاحظة سلبية مهمة (غير مطلوبة صراحةً بس ذات صلة بالتعميم):** الفحص ده
موجود فقط في `review_claim`. الدوال الأخرى اللي بتلمس `issuer_entity_id`
(`create_policy`, `update_policy`, `subscribe`, `renew_subscription`) **لا
تفحص عضوية الكيان مطلقًا** — `update_policy` مثلًا (`service.py:160-164`)
بيتحقق بس إن `policy.tenant_id == tenant_id`، وبيسمح لأي `superuser` بالتعديل
بدون فحص إنه عضو/مالك للكيان المُصدِر. لو التعميم للقطاعات الأربعة هيتضمن
"نفس نمط insurance بالظبط"، فالنمط الحالي فيه فحص عضوية جزئي (على
`review_claim` بس) مش شامل.

---

## 3) مين اللي بيملأ `issuer_entity_id` وقت الإنشاء — إجباري وقت الإنشاء

**إجباري بالكامل، على 3 مستويات:**

1. **مستوى الـSchema (Pydantic):**
   `eppne-backend/app/domains/insurance/schemas.py:16`
   ```python
   class InsurancePolicyCreate(BaseModel):
       issuer_entity_id: int = Field(description="معرف الكيان المصدر")
   ```
   بدون `Optional` وبدون قيمة افتراضية → حقل مطلوب في جسم الطلب. لو الطلب
   جاله من غير الحقل ده، FastAPI/Pydantic بيرفضه بـ `422` قبل ما يوصل
   للـservice أصلًا.

2. **مستوى الـRouter:** `eppne-backend/app/domains/insurance/router.py:24-38`
   — `create_policy` بياخد `data: InsurancePolicyCreate` ويعمل
   `data.model_dump()` ويمرره كامل لـ`service.create_policy(...)` بدون أي
   تعديل أو تعبئة تلقائية لـ`issuer_entity_id`.

3. **مستوى الـService/Repository:**
   `service.py:126-142` (`create_policy`) بيمرر `**data` مباشرة لـ
   `self.repo.create_policy(tenant_id=..., created_by=..., **data)`، و
   `repository.py:26-31`:
   ```python
   async def create_policy(self, **kwargs) -> InsurancePolicy:
       policy = InsurancePolicy(**kwargs)
       ...
   ```
   الـrepository تمرير خام (`**kwargs`) بدون أي قيمة افتراضية لـ
   `issuer_entity_id` — فلو الحقل مش موجود في `kwargs`، الفشل هيكون على
   مستوى SQLAlchemy/DB (`NOT NULL constraint`)، لكن عمليًا هذا لا يحدث لأن
   الـschema بيمنعه قبل كده.

**الخلاصة:** `issuer_entity_id` **إجباري 100% وقت الإنشاء** — لا يوجد أي
مسار في الكود الحالي لإنشاء `InsurancePolicy` بدونه. القيمة بتيجي بالكامل
من جسم طلب الـclient (مفيش استنتاج تلقائي من `current_user` أو من عضوية
موجودة مسبقًا — الـ`current_user` اللي بينشئ البوليصة لازم يكون `superuser`
[`router.py:29`، `get_current_superuser`]، لكن مفيش أي ربط أو تحقق وقت
الإنشاء إن هذا الـ`superuser` عضو فعلي في الكيان اللي بيمرر ID بتاعه).

---

## 4) الـMigration — هل كان لازم يتعمل واحد جديد، ولا كان موجود من الأول؟

**لم يُعمل أي migration منفصل لهذا العمود.** العمود موجود منذ البداية ضمن
migration واحد شامل:

**الملف:** `eppne-backend/migrations/versions/71820e4fe1f3_initial_migration_all_34_sectors_final.py`
(migration وحيد في الريبو بالكامل يذكر `issuer_entity_id` — تم التأكد بالبحث
الشامل في مجلد `migrations/versions/`، ولا يوجد أي migration آخر لاحق
بـALTER TABLE على هذا العمود).

**التعريف داخل الـmigration** (سطور 2786-2809):

```python
sa.Column('issuer_entity_id', sa.Integer(), nullable=False),
...
sa.ForeignKeyConstraint(['issuer_entity_id'], ['sovereign_entities_v2.id'], ondelete='CASCADE'),
...
op.create_index(op.f('ix_insurance_policies_issuer_entity_id'), 'insurance_policies', ['issuer_entity_id'], unique=False)
```

مطابق تمامًا لتعريف الـmodel الحالي (لا يوجد drift بين الـmodel والـmigration).

**التبعية على `EntityMembership` نفسها:** جدول `entity_memberships` (اللي
بيستخدمه `EntityMembershipService`) بنية بيانات عامة في `app/core/models.py`
منفصلة تمامًا عن جدول `insurance_policies` — العلاقة بينهم منطقية فقط
(`entity_type="SOVEREIGN_ENTITY"` + `entity_id=policy.issuer_entity_id`)،
مفيش FK فعلي بين الجدولين. يعني تعميم النمط على القطاعات الأربعة **مايحتاجش
migration خاص بجدول العضويات نفسه** (موجود بالفعل ومشترك)، لكن **كل قطاع
هيحتاج عموده الخاص** (زي `issuer_entity_id`) لو مش موجود عنده أصلًا — ده
لازم يتفحص لكل قطاع من الأربعة على حدة (خارج نطاق هذا الفحص).

---

## ملخص الوصفة القابلة للتعميم

| الخطوة | التفاصيل |
|---|---|
| 1. عمود FK | `Integer, ForeignKey("sovereign_entities_v2.id", ondelete=...), nullable=False, index=True` على الجدول المالك للمورد (هنا `insurance_policies`) |
| 2. حقن الخدمة | `self.membership = EntityMembershipService(db)` في `__init__` + ثابت `ENTITY_TYPE = "SOVEREIGN_ENTITY"` على مستوى الموديول |
| 3. فحص الصلاحية | `member = await self.membership.get_member(entity_type=ENTITY_TYPE, entity_id=<issuer_entity_id من السجل>, user_id=<current/reviewer id>)` ثم `if member is None or member.role not in [...]: raise PermissionDeniedError` |
| 4. تعبئة العمود | إجباري (`Field(...)` بدون default) في الـPydantic Create schema، يُمرَّر خام من الـclient حتى الـrepository، بدون أي auto-fill من السياق |
| 5. Migration | لا حاجة لجدول عضويات جديد (مشترك عبر `app/core/models.py`)؛ فقط إضافة عمود FK جديد لكل قطاع إن لم يكن موجودًا |

**تحذير للتعميم:** فحص العضوية في `insurance` **جزئي** — مطبّق فقط في
`review_claim`، وليس في `create_policy`/`update_policy`/`subscribe`. أي
تعميم "كامل" للقطاعات الأربعة يحتاج قرارًا صريحًا: هل نعمّم النمط الجزئي
كما هو، أم نسدّ الفجوة في insurance نفسها أولًا؟ هذا القرار خارج نطاق هذا
الفحص (read-only فقط) ويحتاج جلسة منفصلة بموافقة صريحة حسب قواعد المشروع.
