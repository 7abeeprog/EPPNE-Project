# جلسة: تصميم التنفيذ الموحَّد لنظامي Referral/Affiliate

**تاريخ:** 2026-09-05
**النوع:** تصميم تفصيلي نهائي — **صفر تنفيذ** حتى موافقة قاطعة صريحة.
**مرجعان أساسيان (اقرأهما أولاً لأي سياق تاريخي):**
- `.claude/reports/referral-affiliate-system-design-session-log.md`
  (2026-09-05، جلسة "design") — كشف الأنظمة الثلاثة A/B/C وحالتها الحية.
- `.claude/reports/referral-system-multilevel-investigation-session-log.md`
  (2026-08-19) — القراءة الكاملة الأصلية لكود نظام A.

**القرارات المعتمدة نهائيًا (من رسالة المستخدم، لا نقاش إضافي عليها):**
1. التوحيد على نظام A (`affiliate` domain)، حذف نظام B (`commerce`
   Affiliate*) بالكامل، ربط نظام C (12 دومين) بنفس آلية A.
2. كود الإحالة الموحَّد = الشكل الأبجدي (`AffiliateProfile.referral_code`).
3. العمولة تشمل كل الدومينات البائعة (commerce + academy + 12 دومين)
   بنفس منطق تصاعد 10 مستويات.
4. الشجرة/العمولة مربوطة بـ"نطاق" (scope) لا بالمنصة كلها — نفس
   المستخدم يمكن أن يكون له شجر منفصلة تمامًا لكل نطاق.
5. مفهوم `AffiliateScope`/`AffiliateScopeMember` جديد بدل ربط
   `ReferralTree`/`CommissionTier` مباشرة بـ`product_id`.
6. الأفيليت نفسه خدمة SaaS قابلة للتفعيل لكل tenant عبر
   `saas_service_catalog`/`saas_service_plans` الموجودة بالفعل.

هذه الجلسة تحقَّقت حيًا من كل الأكواد ذات الصلة (لا اعتماد على افتراضات
من الجلسات السابقة فقط) قبل وضع التصميم — كل قسم يذكر الملف/السطر
المصدر.

---

## اكتشاف تصميمي إضافي مهم (نتيجة مباشرة لقرارك #3 — يوسّع نطاق العمل)

قرار #3 يعني أن الـ12 دومين (Backlog #10) لازم تدخل في **نفس** خط أنابيب
العمولة متعددة المستويات (`Commission` + `distribute_commissions`)،
**مش** تبقى على منطق `ActionCommission` الحالي (مستوى واحد مباشر، مبلغ
Hardcoded). لكن `Commission.distribute_commissions(order_id)` اليوم
(`affiliate/service.py:262-316`) **مبني حصريًا حول `commerce.Order`**
(`self.commerce_repo.get_order(order_id, ...)` + `OrderItem`) — الـ12
دومين ليس عندها `Order`/`OrderItem` تجاري إطلاقًا (زمكانة تنشئ Node/
Campaign/Pledge، مش طلب شراء).

**الأثر:** لازم تعميم `distribute_commissions` ليقبل "حدث بيع" عام
(مبلغ + نطاق + مصدر) وليس `order_id` فقط. هذا يستلزم تعديل جدول
`Commission` نفسه (تفاصيل §1) — **وليس فقط `CommissionTier`/`ReferralTree`
كما ورد في طلبك الأصلي.** هذا اكتشاف أثناء التصميم، أعرضه صراحة لأنه
يوسّع حجم Phase 0/1 عن المتوقع في طلبك (بند 7 تحت يعكس هذا في التقدير).

**نتيجة مترتبة:** `ActionCommission` (نظام C الحالي، `models.py:106-144`)
يصبح **زائدًا تمامًا** بعد هذا التعميم — عمولات الـ12 دومين ستُخزَّن في
نفس جدول `Commission` الموحَّد، بمستويات متعددة، بدل جدول منفصل بمستوى
واحد. أقترح **حذفه بالكامل** (نفس منطق "لا عملاء، لا حاجة توافق خلفي" —
راجع §5 للتبرير الكامل). **يحتاج تأكيدك الصريح** لأنه يلغي جدولًا بالكامل
لم يُطلَب حذفه صراحة في رسالتك.

---

## 1) `AffiliateScope` + `AffiliateScopeMember` — التصميم الكامل

### 1.أ الموديلات الجديدة

```python
class AffiliateScope(Base):
    """نطاق عمولة: منتج فردي، مجموعة منتجات، أو "كل مبيعات الكيان"."""
    __tablename__ = "affiliate_scopes"
    __table_args__ = (
        Index("ix_affiliate_scopes_tenant_id", "tenant_id"),
        Index("ix_affiliate_scopes_scope_type", "scope_type"),
        # نطاق افتراضي واحد فقط لكل tenant (ENTITY_WIDE) — يُنشأ تلقائيًا
        # عند تفعيل خدمة affiliate (راجع §4)
        Index("ix_affiliate_scopes_tenant_entity_wide_unique",
              "tenant_id",
              postgresql_where=text("scope_type = 'ENTITY_WIDE'"),
              unique=True),
    )
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    scope_type = Column(String(20), nullable=False)   # SINGLE_PRODUCT | PRODUCT_GROUP | ENTITY_WIDE
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateScopeMember(Base):
    """عضوية "شيء قابل للبيع" داخل نطاق — منتج commerce، كورس academy،
    أو نوع حدث من أحد الـ12 دومين."""
    __tablename__ = "affiliate_scope_members"
    __table_args__ = (
        Index("ix_affiliate_scope_members_scope_id", "scope_id"),
        # عضو واحد (نوع+معرف) لا يمكن أن يكون في أكثر من نطاق واحد فعّال
        # — يمنع غموض "أي نسبة عمولة تُطبَّق؟" لو نفس المنتج في نطاقين
        Index("ix_affiliate_scope_members_unique_member",
              "member_type", "member_id", unique=True),
    )
    id = Column(Integer, primary_key=True, index=True)
    scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="CASCADE"), nullable=False, index=True)
    member_type = Column(String(30), nullable=False)   # PRODUCT | COURSE | ZAMAKANA_ACTION | ...
    member_id = Column(Integer, nullable=True)          # NULL لو member_type يمثّل "كل حدث من هذا النوع بلا تمييز فردي" (مثال: كل أحداث زمكانة)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**قرار تصميمي يحتاج تأكيدك:** `member_id` نُلِّت (nullable) عمدًا —
لأن الـ12 دومين ليس عندها "منتج" بمعرّف فردي بالضرورة (زمكانة NODE_CREATED
مثلًا حدث نوعي، مش سجل منتج). المقترح: كل دومين من الـ12 يحصل على صف
`AffiliateScopeMember` واحد بـ`member_type="ZAMAKANA"` (أو اسم الدومين)
و`member_id=NULL`، يشير لنطاق `ENTITY_WIDE` افتراضي (أو نطاق مخصص لو
أراد الـtenant تمييز عمولة الزمكانة عن باقي مبيعاته). **لو تريد تمايزًا
أدق داخل الدومين نفسه (نسبة مختلفة لكل `action_type`) — هذا يحتاج تصميمًا
إضافيًا غير مطلوب في رسالتك الحالية، أُجّله كسؤال مفتوح صراحة.**

### 1.ب أثر التغيير على `ReferralTree`

**لا تغيير في العمود نفسه** (`entity_type`/`entity_id` يبقيان كما هما
بنيويًا) — فقط تغيير **دلالة القيمة**:
- `entity_type` يصبح دائمًا الحرف الثابت `"SCOPE"` لكل الصفوف الجديدة
  (بدل `"PRODUCT"`/`"COURSE"`/`"GLOBAL"` المتفرقة اليوم).
- `entity_id` يصبح `affiliate_scopes.id` دائمًا (بدل `product_id`/
  `course_id` الخام).
- **لا حاجة لتعديل schema/migration على `ReferralTree` نفسه** — القيد
  الفريد الموجود بالفعل (`ix_referral_trees_unique_referred_scope`,
  `referred_id + entity_type + COALESCE(entity_id,0)`) يبقى صحيحًا
  ويعمل تمامًا كما هو مصمَّم أصلًا، لأنه أصلًا عام (لا يفترض قيمة معيّنة
  لـ`entity_type`). **هذا يعني نظام A لم يكن يحتاج تعديل schema لدعم
  scopes من الأساس — كان يحتاج فقط "شيء" يشغل `entity_id` بمعنى مستقر
  بدل `product_id` الخام، وهذا بالضبط ما توفره `AffiliateScope`.**
- **توصية إضافية (تحسين اختياري):** إضافة FK حقيقي `entity_id →
  affiliate_scopes.id` بدل `Integer` غير مقيَّد كما هو اليوم
  (`models.py:59`) — يمنع بيانات يتيمة مستقبلًا. يتطلب `ALTER TABLE
  referral_trees ADD CONSTRAINT ... FOREIGN KEY (entity_id) REFERENCES
  affiliate_scopes(id)` — ممكن فقط لأن `entity_type` غير مقيَّد بقيمة
  واحدة على مستوى DB (لسه `String`)، فلا تعارض. **موصى به، ليس إجباريًا.**

### 1.ج أثر التغيير على `CommissionTier` و`_get_commission_rate`

`CommissionTier` (`models.py:146-176`) يحتاج تعديل schema فعلي (رينيم +
تغيير FK):

```python
# قبل: target_product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
# بعد:
target_scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="CASCADE"), nullable=True)
```
`entity_type` على `CommissionTier` (كان `"GLOBAL"`/`"PRODUCT"`) **يبقى
كما هو بدلالة مبسَّطة**: `"GLOBAL"` = تعريفة افتراضية للـtenant كله
(`target_scope_id IS NULL`)، `"SCOPE"` = تعريفة مخصَّصة لنطاق بعينه
(`target_scope_id NOT NULL`). القيد الفريد الحالي
(`tenant_id, entity_type, target_scope_id`) يبقى صحيحًا بلا تغيير بنيوي
إضافي.

`_get_commission_rate` (`service.py:375-391`) — تغيير التوقيع فقط:
```python
async def _get_commission_rate(self, tiers, level: int, scope_id: Optional[int]) -> Decimal:
    scope_tier = await self.repo.get_commission_tier_by_scope(
        tenant_id=self.tenant_id, scope_id=scope_id,
    ) if scope_id else None
    if scope_tier:
        return getattr(scope_tier, f"level_{level}_pct", Decimal(0))
    if tiers:
        return getattr(tiers, f"level_{level}_pct", Decimal(0))
    return Decimal(0)
```
`repository.get_commission_tier_by_product(tenant_id, product_id)` →
يُعاد تسميتها `get_commission_tier_by_scope(tenant_id, scope_id)`، نفس
منطق الاستعلام تمامًا لكن بعمود `target_scope_id`.

### 1.د أثر التعميم (§ الاكتشاف أعلاه) على `Commission`

لدعم مصادر غير `commerce.Order` (academy enrollments، أحداث الـ12
دومين)، `Commission` (`models.py:68-103`) يحتاج تعديلات:

```python
# order_id, order_item_id, product_id: من NOT NULL إلى nullable=True
order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=True, index=True)
product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)

# أعمدة جديدة — المصدر العام لأي حدث بيع بغض النظر عن الدومين
source_type = Column(String(30), nullable=False)   # COMMERCE_ORDER | ACADEMY_ENROLLMENT | ZAMAKANA | TRANSPORT | ...
source_id = Column(Integer, nullable=True)          # order_item_id لو COMMERCE_ORDER، enrollment_id لو ACADEMY، إلخ

# عمود جديد إجباري — نفس النطاق المستخدَم وقت الحساب (للتدقيق/العرض)
scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="RESTRICT"), nullable=False, index=True)
```
`distribute_commissions` يتحول من دالة واحدة مقفولة على `order_id` إلى
دالتين: دالة عامة `_distribute_for_sale_event(referred_user_id, scope_id,
sale_amount, source_type, source_id)` (المنطق المشترك: البحث عن
`ReferralTree` بالنطاق، تصعيد 10 مستويات، إنشاء `Commission` صفوف)، ودالة
غلاف رقيقة `distribute_commissions_for_order(order_id)` (لـcommerce/
academy، تجلب `order_items`/`enrollment` ثم تستدعي الدالة العامة لكل
عنصر). الـ12 دومين يستدعون الدالة العامة مباشرة بمبلغ العملية نفسها
(مثال: `Decimal("2.00")` الثابت الحالي في زمكانة، أو مبلغ حقيقي لو
كان الحدث مرتبطًا بدفعة فعلية).

---

## 2) إصلاح باج `get_referral_tree` (MultipleResultsFound)

**الباج الحالي** (`repository.py:80-86`):
```python
async def get_referral_tree(self, user_id: int, tenant_id: int) -> Optional[ReferralTree]:
    result = await self.db.execute(
        select(ReferralTree)
        .join(User, User.id == ReferralTree.referred_id)
        .where(and_(ReferralTree.referred_id == user_id, User.tenant_id == tenant_id))
    )
    return result.scalar_one_or_none()
```
يفلتر فقط بـ`referred_id` — لو نفس المستخدم له صفوف متعددة (نطاقات
مختلفة، بالضبط سيناريو قرارك #4)، `scalar_one_or_none()` يرمي
`MultipleResultsFound`.

**التصميم المُصلَح — يضيف `scope_id` كمعامل إجباري:**
```python
async def get_referral_tree(
    self, user_id: int, tenant_id: int, scope_id: int,
) -> Optional[ReferralTree]:
    result = await self.db.execute(
        select(ReferralTree)
        .join(User, User.id == ReferralTree.referred_id)
        .where(and_(
            ReferralTree.referred_id == user_id,
            ReferralTree.entity_type == "SCOPE",
            ReferralTree.entity_id == scope_id,
            User.tenant_id == tenant_id,
        ))
    )
    return result.scalar_one_or_none()
```
بما إن القيد الفريد على `(referred_id, entity_type, COALESCE(entity_id,0))`
موجود بالفعل، الاستعلام دلوقتي **مضمون** يرجع صف واحد كحد أقصى —
`MultipleResultsFound` يصبح مستحيلًا بنيويًا، مش مجرد أقل احتمالًا.

**أثر التصعيد عبر المستويات (`_distribute_levels`, `service.py:318-373`):**
يجب تمرير **نفس `scope_id`** في كل استدعاء متكرر للصعود، بدل
`get_referral_tree(referrer_id, self.tenant_id)` الحالية بلا نطاق:
```python
current_referral = await self.repo.get_referral_tree(
    referrer_id, self.tenant_id, scope_id=cast(int, referral.entity_id)
)
```
هذا يضمن إن السلسلة كلها (كل الـ10 مستويات) تمشي **داخل نفس النطاق**
فقط — لو الراعي في المستوى 3 له راعٍ خاص به في نطاق مختلف، السلسلة
تتوقف هناك بدل القفز لنطاق آخر (بالضبط قرارك #4: "لا تتداخل").

---

## 3) إصلاح توقيع `tasks/affiliate.py` (Celery)

**الحالة الحية اليوم (3 أعطال مستقلة، تأكيد حي 2026-09-05):**

| المهمة | العطل | الإصلاح المصمَّم |
|---|---|---|
| `distribute_commissions_task(order_id, tenant_id)` | سطر 67: `service.distribute_commissions(order_id, tenant_id)` — دالتها الحقيقية تاخد `order_id` فقط (`self.tenant_id` بيجي من الـconstructor، مُصلَح بالفعل جزئيًا وغير مُلتزَم — راجع تقرير الجلسة السابقة §4) | `commissions = await service.distribute_commissions_for_order(order_id)` (الاسم الجديد بعد التعميم §1.د) — إسقاط `tenant_id` من الاستدعاء الداخلي فقط |
| `release_commissions_task(user_id, idempotency_key)` | سطر 102: `AffiliateService(db)` — ناقص `tenant_id` الإجباري | المهمة نفسها ناقصة `tenant_id` في **توقيعها هي** (مش بس في الاستدعاء الداخلي) — لازم تضاف `tenant_id: int` كمعامل جديد للـtask، وتُمرَّر من أي مكان بينادي `.delay()`/`.apply_async()` مستقبلًا (لا يوجد استدعاء حي حاليًا — نفس ملاحظة "كود ميت" من التقرير السابق) |
| `clean_expired_links_task()` | سطر 141: `repo.delete_expired_invitations(cutoff_date)` — ناقصة `tenant_id` الإجباري في `AffiliateRepository` | **لا يوجد نمط عبور-كل-الـtenants جاهز بالمشروع** (فحصت `saas_tasks.py`/`agritech.py`/`celery_config.py` — صفر سابقة). التصميم المقترح: `AcademyTenant` عندها جدول tenants كامل — التعديل يجلب كل `tenant_id` نشط (`SELECT id FROM academy_tenants WHERE is_active`) ويلف عليهم: `for tid in tenant_ids: await repo.delete_expired_invitations(cutoff_date, tid)`. **هذا نمط جديد يُقدَّم هنا لأول مرة بالمشروع — إن كان هناك تفضيل مختلف (مثال: تشغيل مهمة Celery منفصلة لكل tenant عبر `beat_schedule` ديناميكي)، وضّح قبل التنفيذ.** |

**كمان لازم تُسجَّل المهمة فعليًا في `celery_config.py::beat_schedule`**
(اليوم غير مسجَّلة إطلاقًا — نفس ملاحظة الجلسة السابقة، `clean_expired_links`
موجودة كودًا لكن لا Celery Beat ينادي عليها دوريًا). **خارج نطاق طلبك
المباشر لكن ذِكره هنا لتفادي "إصلاح نص المشكلة".**

---

## 4) آلية تفعيل الأفيليت كخدمة SaaS

**تأكيد حي مهم قبل التصميم:** `saas_service_catalog` **فارغ فعليًا
اليوم** — لا يوجد أي seed/migration يملأ صفوفًا فيه لأي دومين (تأكيد
`grep` شامل: صفر نتيجة إنشاء بيانات، فقط تعريف الجدول في migration
أولية). هذا يعني `require_subscription("affiliate")` (مُستخدَمة بالفعل
في `affiliate/router.py` على 5 endpoints) **ترجع `False` دائمًا اليوم
لأي tenant** — لا يوجد tenant واحد بمقدوره فعليًا إنشاء رابط دعوة أو سحب
عمولة **حتى قبل أي تعديل من هذه الجلسة**، لأن الصف الأساسي في الكاتالوج
غير موجود. هذا ليس باج تقني — هو غياب بيانات تأسيسية.

**service_code المقترح:** `"affiliate"` — **مطابق تمامًا** للاسم
المستخدَم بالفعل في كود اليوم (`require_subscription("affiliate")`،
`require_sector("affiliate")` في `main.py:269`) — صفر تغيير على أي كود
تحقق موجود، فقط **إضافة الصفوف المفقودة**.

**تصميم آلية التفعيل (يحتاج تأكيدك على الخيار):**

**الخيار المقترح (موصى به): `ENTITY_WIDE` تلقائي عند التفعيل + Scopes يدوية اختيارية بعدها.**
عند إنشاء/تفعيل `TenantServiceAccess` + `TenantSubscription` لـ
`service_code="affiliate"` لأي tenant (عبر `POST /saas/admin/...`
الموجودة بالفعل — لا endpoint جديد مطلوب لهذا الجزء)، **hook** جديد في
`SaaSControlService` (أو `AffiliateService`، التفاصيل في §7) يُنشئ
تلقائيًا:
```python
AffiliateScope(tenant_id=tenant_id, name="كل مبيعات المستأجر", scope_type="ENTITY_WIDE", is_active=True)
```
هذا يضمن أن الـtenant **قابل للاستخدام فورًا** بلا خطوة يدوية إضافية
(نسبة عمولة افتراضية تُطبَّق على كل شيء عبر `CommissionTier` الافتراضي
GLOBAL). لاحقًا، الـtenant (أو superuser) يقدر ينشئ `AffiliateScope`
إضافية بـ`scope_type=SINGLE_PRODUCT`/`PRODUCT_GROUP` ويضيف لها أعضاء
(`AffiliateScopeMember`) لمنتجات محددة تستحق نسبة مختلفة — عند وجود
عضوية أدق، هي تُفضَّل تلقائيًا على `ENTITY_WIDE` (لأن `resolve_scope_for_member`
يبحث أولًا في `AffiliateScopeMember` قبل السقوط لـ`ENTITY_WIDE`
الافتراضي، راجع §1.د).

**البديل المرفوض بالتفضيل (يُذكر للمقارنة فقط):** ترك الـtenant يُنشئ
كل شيء يدويًا من الصفر بعد التفعيل — أبسط تصميميًا لكنه يترك الـtenant
"بلا نطاق افتراضي" فيفشل أي بيع بصمت (`if not referral: continue`) حتى
يُنشئ يدويًا نطاقًا واحدًا على الأقل. **مرفوض لأنه يكرر نفس فئة "الفشل
الصامت" الموثَّقة كأخطر فئة أعطال في المشروع.**

---

## 5) خطة الهجرة من نظام B — الحذف الفوري (رأيي + التبرير)

**التوصية: حذف فوري كامل**، وليس إبقاء كجداول deprecated فارغة. السبب:

1. **لا عملاء في الإنتاج** — القيد الوحيد الذي كان يبرر الإبقاء المؤقت
   (خوف من كسر بيانات حية) غير قائم هنا، مؤكَّد صراحة في قرار المستخدم.
2. **الجداول الثلاثة معزولة تمامًا داخل دومين `commerce`** (تأكيد
   `grep` شامل: `AffiliateTree`/`CommissionRecord`/`AffiliateConfig`
   تظهر فقط في `commerce/{models,service,repository,schemas,router}.py`
   + `openapi.json` المولَّد) — **صفر أثر جانبي على أي دومين آخر** عند
   الحذف.
3. إبقاء جداول فارغة "احتياطيًا" يخالف صراحة قاعدة المشروع ("لا تستخدم
   feature flags أو backwards-compatibility shims لما تقدر تغيّر الكود
   مباشرة") ويترك كودًا ميتًا يربك أي قراءة مستقبلية لدومين commerce.
4. **ما يُحذَف تحديدًا:**
   - `commerce/models.py`: `AffiliateTree`, `CommissionRecord`,
     `AffiliateConfig` (+ DROP TABLE في الـmigration).
   - `commerce/service.py`: `register_affiliate`, `distribute_commissions`
     (النسخة الخاصة بـcommerce)، واستبدال استدعاء `checkout()` لها
     (`service.py:219-224`) بالنداء الموحَّد الجديد (`affiliate_service
     .distribute_commissions_for_order(order.id)` بعد التأكد من وجود
     `ReferralTree` مطابق — راجع الفجوة في §6).
   - `commerce/repository.py`: `get_affiliate_tree`, `create_affiliate_tree`,
     `create_commission` (نسخة commerce)، `get_affiliate_config`.
   - `commerce/router.py`/`schemas.py`: أي endpoint/schema خاص بـ
     `register_affiliate`/tree/config (يحتاج قراءة `router.py` كاملة
     وقت التنفيذ لتحديد القائمة الدقيقة — لم تُقرأ بالكامل في هذه
     الجلسة، فقط `checkout`/`register_affiliate`/`distribute_commissions`).
   - عمود `Store.is_affiliate_enabled` (`models.py:28`): **أقترح
     الإبقاء عليه** (وليس حذفه) كـ"مفتاح تفعيل على مستوى المتجر" إضافي
     فوق تفعيل SaaS على مستوى الـtenant — قرار منتجي بسيط: متجر معيّن
     داخل tenant مفعَّل له affiliate يقدر يوقف الميزة لنفسه فقط. **يحتاج
     تأكيدك — البديل هو حذفه بالكامل والاعتماد فقط على تفعيل SaaS
     الشامل للـtenant.**
   - عمود `Order.affiliate_code_used`: **يبقى كما هو** — لا علاقة له
     بجداول B المحذوفة، فقط سجل تدقيقي لأي كود استُخدم وقت الطلب.

**فجوة تصميمية يجب سدّها عند الحذف (مهمة):** نظام B كان يقبل
`affiliate_code` **مباشرة وقت الـcheckout** (بلا تسجيل مسبق — نداء
`register_affiliate` منفصل اختياري). نظام A's `distribute_commissions`
**يفترض وجود `ReferralTree` مسجَّل مسبقًا** (لا يقبل كود مباشرة). لذلك
`checkout()` بعد الهجرة يجب أن **يستدعي `track_referral` أولًا** (upsert
idempotent — الكود الحالي في `track_referral` أصلًا يتجاهل الاستدعاء لو
صف موجود بالفعل، `service.py:190-191`) **قبل** `distribute_commissions_for_order`،
باستخدام `scope_id` المُحلَّل من أول منتج في السلة (أو `ENTITY_WIDE` لو
منتجات متعددة النطاقات في نفس الطلب — **حالة حافة تحتاج قرارك**: هل
يُسمح بعمولات من نطاقين مختلفين في نفس الطلب، أم يُرفَض الطلب لو السلة
تخلط منتجات من نطاقين مختلفين؟).

---

## 6) ربط الـ12 دومين — `User.referred_by_user_id` + توقيت إنشاء `ReferralTree`

### 6.أ العمود الجديد
```python
# identity/models.py — إضافة لـUser
referred_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
```
**Immutable بعد التسجيل** — يُفرَض على مستوى التطبيق (السماح بالكتابة
فقط داخل مسار `POST /identity/register`، وعدم عرضه إطلاقًا في أي
`UserUpdate` schema) — **ليس** بقيد DB (لا يوجد trigger/constraint يمنع
UPDATE، بما يطابق نمط المشروع في أعمدة مشابهة مثل `created_at`).

### 6.ب خياران لتوقيت إنشاء `ReferralTree` — التوصية: (ب)

**الخيار (أ) — عند التسجيل مباشرة:**
عند نجاح `POST /identity/register` بكود إحالة صالح، يُنشأ فورًا صف
`ReferralTree` واحد بـ`entity_type="SCOPE"`, `entity_id=<default ENTITY_WIDE
scope للـtenant>`. بسيط، لكن: **المستخدم قد لا يشتري أبدًا من أي دومين** —
يظل صف "إحالة" بلا أي عمولة مرتبطة به إطلاقًا (غير ضار لكنه بيانات
بلا فائدة عملية إلا للعرض الإحصائي "كم شخص جبت").

**الخيار (ب) — عند أول عملية بيع فعلية لكل دومين (موصى به):**
لا يُنشأ أي `ReferralTree` وقت التسجيل. بدلًا من ذلك، كل دومين من الـ12
(في `_register_affiliate_commission` أو معادلها بعد إعادة التصميم)
يستدعي دالة مساعدة جديدة على مستوى `AffiliateService`:
```python
async def ensure_referral_link(
    self, referrer_user_id: int, referred_user_id: int, scope_id: int,
) -> ReferralTree:
    """يُنشئ صف ReferralTree لو غير موجود لهذا (referred × scope)، أو
    يرجّع الموجود. لا يعتمد على referral_code — الربط مباشر بـuser_id
    (مصدره User.referred_by_user_id، مش كود مُدخَل يدويًا)."""
```
هذه دالة **أعم** من `track_referral` الحالية (التي تتطلب `referrer_code`
نصيًا) — تُستخدَم من الـ12 دومين مباشرة بـ`referrer_user_id=user.referred_by_user_id`.
`track_referral` (commerce/academy) تبقى كما هي لكن تُعاد كتابتها
داخليًا لتنادي `ensure_referral_link` بعد حل الكود لـ`user_id` (توحيد
منطق، صفر تكرار).

**سبب التوصية بـ(ب):** يطابق تمامًا النمط المطبَّق بالفعل في `academy`
اليوم (`track_referral` تُستدعى وقت التسجيل بالكورس، **وليس** وقت
تسجيل حساب المستخدم لأول مرة) — الاتساق مع نمط قائم فعليًا في الكود،
وليس تصميمًا مستوردًا من الصفر. كمان يتجنب مشكلة "أي `scope_id` نستخدم
وقت التسجيل؟" (المستخدم وقتها لسه ما اشترى حاجة، فمفيش نطاق محدد
منطقيًا بعد).

### 6.ج تعديل الاستدعاء في الـ12 دومين
```python
# قبل (zamakana/service.py:645-661):
async def _register_affiliate_commission(self, user_id, tenant_id, action_type):
    ...
    if user and user.referred_by:
        await affiliate_service.register_commission(affiliate_id=user.referred_by, ...)

# بعد:
async def _register_affiliate_commission(self, user_id, tenant_id, action_type):
    user = await user_repo.get_by_id(user_id, tenant_id)
    if not user or not user.referred_by_user_id:
        return
    scope_id = await affiliate_service.get_default_scope_id(tenant_id)  # ENTITY_WIDE، أو نطاق خاص بـzamakana لو أُنشئ لاحقًا
    await affiliate_service.ensure_referral_link(
        referrer_user_id=user.referred_by_user_id,
        referred_user_id=user_id,
        scope_id=scope_id,
    )
    amount = Decimal("2.00") if action_type in [...] else Decimal("1.00")
    await affiliate_service.distribute_commissions_for_sale_event(
        referred_user_id=user_id, scope_id=scope_id, sale_amount=amount,
        source_type="ZAMAKANA", source_id=None,
    )
```
**ملاحظة حرجة على `try/except` الحالي:** الكود اليوم يلف الاستدعاء
بالكامل بـ`except Exception as e: logger.error(...)` بلا rethrow —
تأكيد حي: هذا **يبتلع فعليًا** `AttributeError` الناتج عن `user.referred_by`
غير الموجود أصلًا كعمود (وليس مجرد قيمة `None`) — **الفشل صامت فعلًا
اليوم، ومؤكَّد الآن (لم يكن مؤكَّدًا بدقة في تقرير 2026-09-05 السابق،
§2 هناك). بعد الإصلاح، يجب الإبقاء على نفس نمط try/except** (فشل
تسجيل عمولة لا يجب أبدًا أن يفشل العملية الأساسية للمستخدم — نفس مبدأ
معماري قائم بالفعل، لا نغيّره) **لكن** يُستحسَن تسجيل الخطأ بتفصيل كافٍ
(نوع الخطأ + `user_id`/`action_type`) لأن هذا "فشل صامت مالي" — نفس
الفئة المذكورة صراحة في تعليمات الجلسة السابقة كأخطر فئة أعطال.

---

## 7) ترتيب التنفيذ المرحلي الكامل

| # | المرحلة | المحتوى | الحجم التقريبي |
|---|---|---|---|
| 0 | **Migration واحدة شاملة** | `CREATE affiliate_scopes, affiliate_scope_members` · `ALTER affiliate_commission_tiers` (rename `target_product_id`→`target_scope_id` + FK) · `ALTER affiliate_commissions` (nullable order/item/product + إضافة `source_type`, `source_id`, `scope_id`) · `DROP TABLE affiliate_action_commissions` · `DROP TABLE affiliate_trees, commission_records, affiliate_configs` · `ALTER users ADD referred_by_user_id` · seed صف `saas_service_catalog`(code='affiliate') + `saas_service_plans` افتراضية | **L** — أكبر مرحلة، تلمس 6+ جداول، تحتاج مراجعة دقيقة لكل `DROP`/`ALTER` قبل التطبيق على DB حقيقي |
| 1 | **Models** | `affiliate/models.py` (إضافة Scope/ScopeMember، تعديل CommissionTier/Commission، حذف ActionCommission) · `identity/models.py` (+`referred_by_user_id`) · `commerce/models.py` (حذف 3 كلاسات) | M |
| 2 | **Repository** | `affiliate/repository.py`: دوال scope جديدة (`create_scope`, `add_scope_member`, `resolve_scope_for_member`, `get_default_scope`) · إصلاح `get_referral_tree` (§2) · رينيم `get_commission_tier_by_product`→`_by_scope` · `commerce/repository.py`: حذف دوال Affiliate* | M |
| 3 | **Service** | `affiliate/service.py`: تعميم `distribute_commissions`→`distribute_commissions_for_order`+`_for_sale_event` (§1.د) · `ensure_referral_link` جديدة (§6.ب) · `track_referral` تُعاد كتابتها فوق `ensure_referral_link` · حذف `register_commission`/`ActionCommission` · `commerce/service.py`: حذف `register_affiliate`/`distribute_commissions`، تعديل `checkout()` (§5) | L — أكبر مرحلة منطقية، فيها كل قرارات التعميم |
| 4 | **Router/Schemas** | `affiliate/router.py`: endpoints جديدة لإدارة Scopes (CRUD أساسي) · `commerce/router.py`: حذف endpoints المرتبطة بـB · تحديث `CommissionResponse`/`CommissionTierResponse`/إلخ schemas لتعكس الأعمدة الجديدة | M |
| 5 | **ربط academy** | `academy/service.py:390-401`: بعد enrollment ناجح، استدعاء `distribute_commissions_for_sale_event` (اليوم يسجّل `track_referral` فقط، **صفر توزيع عمولة فعلي** — تأكيد حي جديد من هذه الجلسة، فجوة لم تُذكر صراحة في التقارير السابقة) | S |
| 6 | **ربط الـ12 دومين** | تعديل `_register_affiliate_commission` (أو معادلها) في كل الـ12 موضع (§6.ج) — نفس النمط حرفيًا في كل مكان، تعديل ميكانيكي بعد اعتماد النمط في `zamakana` كمرجع أول | M — 12 موضع لكن نمط متطابق |
| 7 | **تفعيل SaaS** | Hook تلقائي لإنشاء `ENTITY_WIDE` scope عند تفعيل `TenantServiceAccess`+`TenantSubscription` لـ`affiliate` (§4) — الأنسب في `SaaSControlService` أو Event/Signal بعد إنشاء الاشتراك | S-M |
| 8 | **إصلاح Celery** | `tasks/affiliate.py` الثلاث مهام (§3) + تسجيل `clean_expired_links` في `beat_schedule` | S |
| 9 | **Tests + تحقق حي** | نفس معيار الجلسات المالية السابقة (finance hold/settle/release): بيانات throwaway، تحقق DB مباشر لكل مرحلة (تسجيل مستخدم بكود إحالة → شراء من نطاقين مختلفين → تأكيد عدم تداخل الشجرتين → تفعيل affiliate كخدمة SaaS لـtenant → تأكيد إنشاء ENTITY_WIDE تلقائيًا) | L |

**الترتيب الموصى به للتنفيذ الفعلي (لو اعتُمد):** 0 → 1 → 2 → 3 → (4
و7 بالتوازي، مستقلان) → 5 → 6 → 8 → 9. لا تبدأ 3 قبل اكتمال 0+1+2 —
كل الدوال الجديدة في الـservice تعتمد على أعمدة/جداول لسه مش موجودة.

---

## أسئلة تحتاج تأكيدك القاطع قبل أي تنفيذ (بالإضافة لموافقة التصميم ككل)

1. حذف `ActionCommission` بالكامل (نتيجة مباشرة لقرارك #3 — راجع
   "اكتشاف تصميمي إضافي" أعلاه) — موافق؟
2. `Store.is_affiliate_enabled`: يبقى كمفتاح إضافي على مستوى المتجر
   فوق تفعيل SaaS، أم يُحذَف بالكامل؟ (§5)
3. سلة تحتوي منتجات من نطاقين (`AffiliateScope`) مختلفين في نفس طلب
   commerce واحد: تُقسَّم العمولة لكل نطاق حسب منتجاته، أم يُرفَض
   الطلب كخلط غير مسموح؟ (§5، الفجوة التصميمية)
4. توقيت إنشاء `ReferralTree` للـ12 دومين: أُوصي بالخيار (ب) — عند أول
   عملية بيع فعلية لكل دومين، وليس وقت التسجيل (§6.ب) — موافق على
   التوصية؟
5. تمايز عمولة داخل نفس الدومين من الـ12 حسب نوع الحدث (`action_type`)
   عبر `AffiliateScopeMember` مخصص لكل نوع بدل `ENTITY_WIDE` واحد لكل
   دومين — مطلوب في هذه المرحلة، أم يُؤجَّل (نسبة واحدة لكل دومين
   كافية الآن)؟ (§1.أ)
6. نمط "التكرار عبر كل الـtenants" الجديد المقترح لـ`clean_expired_links_task`
   (§3) — أول سابقة من نوعها بالمشروع، هل تعتمده أم تفضّل بديلًا؟

**لا تنفيذ لأي مرحلة قبل إجابة صريحة على الأسئلة الستة + موافقة عامة
على التصميم ككل.**

---

## ✅ موافقة المستخدم (2026-09-06) — بدء التنفيذ

المستخدم وافق على التصميم بالكامل + الأسئلة الستة:
1. حذف `ActionCommission` بالكامل ✅
2. `Store.is_affiliate_enabled` يبقى ✅
3. سلة بنطاقات مختلطة: تُقسَّم العمولة حسب نطاق كل منتج ✅
4. توقيت `ReferralTree` للـ12 دومين: الخيار (ب) — أول عملية بيع فعلية ✅
5. تمايز `action_type` داخل نفس الدومين: مؤجَّل ✅
6. نمط loop عبر كل الـtenants لـ`clean_expired_links_task`: معتمد ✅

**ترتيب التنفيذ:** 0 → 1 → 2 → 3 → (4, 7) → 5 → 6 → 8 → 9، بتحقق حي
بعد كل مرحلة، تحديث هذا الملف أول بأول.

---

## Phase 0 — Migration (كُتبت، **لم تُطبَّق بعد على DB**)

**الملف:** `eppne-backend/migrations/versions/045_create_affiliate_scopes_and_unify_commission.py`
(`revision`, `down_revision = '044_create_transport_tables'` — تأكَّدت
حيًا إن `044` هو الـhead الحالي، صفر migration تاني بيشاور عليه كـ
`down_revision`).

**قرار إضافي اتخذه المستخدم أثناء المراجعة (يبسّط عن التصميم الأصلي):**
بدل الـbackfill المنطقي المقترح في §1 (تحويل صفوف `GLOBAL`/`PRODUCT`/
`COURSE` القديمة إلى `AffiliateScope` مقابلة) — **TRUNCATE بسيط** لـ
`affiliate_commissions`, `affiliate_commission_tiers`, `referral_trees`
قبل أي تعديل بنيوي. السبب المعتمد: البيانات الحالية اختبارية بحتة
(مؤكَّد من `phase10-audit-affiliate-report.md` — صف `CommissionTier`
تجريبي تحت `tenant_id=5` لسه موجود وغير منظَّف)، ولا عملاء إنتاج. هذا
يسمح بإضافة `NOT NULL`/`FK` صارمة مباشرة (`Commission.scope_id NOT NULL`،
`ReferralTree.entity_id → affiliate_scopes.id`) بلا أي مخاطرة توافق
بيانات.

**اكتشاف جانبي أثناء كتابة الـmigration (باج تصميمي في `AffiliateScopeMember`،
لم يُذكَر في تصميم §1 الأصلي):** unique index بسيط على
`(member_type, member_id)` **لا يمنع فعليًا** تكرار عضوية "دومين كامل
بلا معرّف فردي" (`member_id IS NULL`، حالة الـ12 دومين) — لأن Postgres
يعامل `NULL != NULL` داخل unique index عادي، فيسمح بصفين
`(ZAMAKANA, NULL)` في نفس الوقت بلا أي تعارض. **الإصلاح:** index جزئي
مزدوج (`UNIQUE(member_type, member_id) WHERE member_id IS NOT NULL` +
`UNIQUE(member_type) WHERE member_id IS NULL`) — مُطبَّق في الملف.

**محتوى الـmigration الكامل (8 خطوات في `upgrade()`):**
0. `TRUNCATE affiliate_commissions, affiliate_commission_tiers, referral_trees RESTART IDENTITY CASCADE`
1. `CREATE TABLE affiliate_scopes` (+ index جزئي فريد: نطاق `ENTITY_WIDE`
   واحد فقط لكل `tenant_id`)
2. `CREATE TABLE affiliate_scope_members` (+ الـindex الجزئي المزدوج أعلاه)
3. `affiliate_commission_tiers`: drop FK/index القديمين على
   `target_product_id` → rename لـ`target_scope_id` → FK جديد على
   `affiliate_scopes.id` → إعادة إنشاء index الفرادة المركَّب
4. `affiliate_commissions`: `order_id`/`order_item_id`/`product_id`
   تصبح `nullable=True` + أعمدة جديدة `source_type` (NOT NULL)،
   `source_id` (nullable)، `scope_id` (NOT NULL + FK RESTRICT)
5. `referral_trees`: إضافة FK حقيقي على `entity_id → affiliate_scopes.id`
   (آمن الآن بعد التفريغ في الخطوة 0)
6. `DROP TABLE affiliate_action_commissions`
7. `DROP TABLE affiliate_trees, commission_records, affiliate_configs`
   (نظام B بالكامل)
8. `users`: إضافة `referred_by_user_id` (BigInteger، FK ذاتي
   `ON DELETE SET NULL`، nullable، immutable على مستوى التطبيق فقط)

**`downgrade()` كاملة أيضًا** (تعيد الشكل البنيوي بجداول فارغة — التفريغ
في الخطوة 0 **غير قابل للتراجع**، موثَّق صراحة كتحذير في أعلى الدالة).

**⚠️ نقطة تحتاج تحقق فعلي وقت التطبيق (مش نظري):** اسم الـFK constraint
القديم على `affiliate_commission_tiers.target_product_id`
(`affiliate_commission_tiers_target_product_id_fkey`) **مبني على تسمية
Postgres التلقائية القياسية** لقيد بلا اسم صريح — القراءة الثابتة لكود
الإنشاء الأصلي (migration `71820e4fe1f3`) أكَّدت عدم وجود اسم صريح، لكن
**لم يُتحقَّق من الاسم الفعلي في DB حية بعد** (`\d affiliate_commission_tiers`
في psql). لو الاسم مختلف فعليًا، الخطوة هتفشل بخطأ صريح واضح (constraint
غير موجود) — ليس فشلًا صامتًا، لكن يحتاج تصحيح الاسم في الملف قبل
إعادة المحاولة.

**الحالة: الملف مكتوب بالكامل، معروض للمراجعة النهائية أدناه في نفس
رسالة الجلسة — لم يُطبَّق `alembic upgrade` بعد. ينتظر موافقة صريحة.**

---

## تأكيد صريح على 6 نقاط طلبها المستخدم (2026-09-06) — قبل أي تطبيق

### 1. `alembic heads` يؤكد إن `down_revision` هو الـhead الفعلي

**تحقُّق حي فعلي (مش استنتاج من grep)** — شغّلت الأمر مباشرة:
```
$ .\venv\Scripts\python.exe -m alembic heads
045_create_affiliate_scopes_and_unify_commission (head)
```
نتيجة واحدة فقط (لا تفرّع/multiple heads) — يعني Alembic قرأ السلسلة
كاملة من `<base>` لحد `045` بنجاح، و`044_create_transport_tables`
كان فعلاً الـhead الوحيد قبل إضافة `045`. ✅ **مؤكَّد بالتنفيذ الفعلي.**

### 2. `AffiliateScope.scope_type` أصبح Enum حقيقي، مش String حر

كان في المسودة الأولى `sa.String(length=20)` — **تم تصحيحه فعليًا** في
الملف الحالي (نفس نمط `vehicle_type`/`vehiclestatus` في migration 044):
```python
affiliate_scope_type_enum = postgresql.ENUM(
    'SINGLE_PRODUCT', 'PRODUCT_GROUP', 'ENTITY_WIDE',
    name='affiliatescopetype',
)
affiliate_scope_type_enum.create(op.get_bind(), checkfirst=True)
...
sa.Column('scope_type', affiliate_scope_type_enum, nullable=False),
```
`downgrade()` يُسقِط النوع بعد إسقاط الجدول (`postgresql.ENUM(name=
'affiliatescopetype').drop(...)`) — ترتيب صحيح (لا يمكن إسقاط Enum
مُستخدَم في عمود حي). ✅ **مُصحَّح ومؤكَّد بقراءة الملف الحالي.**

### 3. `AffiliateScopeMember` عندها unique index يمنع تكرار العضو

الفهرسان الجزئيان:
```python
op.create_index('ix_affiliate_scope_members_unique_typed',
    'affiliate_scope_members', ['member_type', 'member_id'], unique=True,
    postgresql_where=sa.text('member_id IS NOT NULL'))
op.create_index('ix_affiliate_scope_members_unique_untyped',
    'affiliate_scope_members', ['member_type'], unique=True,
    postgresql_where=sa.text('member_id IS NULL'))
```
**ملاحظة دقة مهمة:** الفريدة هنا على `(member_type, member_id)` **بلا**
`scope_id` — يعني الضمان **أقوى** مما طُلِب حرفيًا ("منع تكرار نفس
المنتج في نفس المجموعة"): هذا التصميم يمنع نفس المنتج من الانضمام
لأي مجموعتين مختلفتين على الإطلاق (قرار §1.أ الأصلي: "عضو واحد لا يمكن
أن يكون في أكثر من نطاق واحد فعّال") — وبالتبعية يمنع تكراره داخل نفس
المجموعة أيضًا (نفس `(member_type, member_id)` مرتين في أي مكان يخالف
الفهرس بغض النظر عن `scope_id`). ✅ **مؤكَّد — الضمان المطلوب موجود
ومُوسَّع.**

### 4. `ReferralTree` unique constraint يشاور على scope الآن

**لا تعديل schema على `referral_trees` نفسه في هذه الـmigration** (قرار
تصميمي أصلي من §1.ب في التصميم — العمود `entity_id` يبقى `Integer` عام
بلا تغيير اسم/نوع، فقط تتغيّر **دلالته**). القيد الفريد الموجود بالفعل
في `models.py:46-47`:
```python
Index("ix_referral_trees_unique_referred_scope",
      "referred_id", "entity_type", text("COALESCE(entity_id, 0)"), unique=True)
```
**يبقى كما هو حرفيًا بلا أي تعديل** — لكنه الآن (بعد أن أصبح `entity_id`
يحمل `scope_id` بدل `product_id`/`course_id` الخام) يفرض تلقائيًا نفس
فلسفة "صف واحد لكل مستخدم × نطاق" **المطلوبة بالضبط** (لأن الفهرس أصلًا
مبني على `entity_id` كقيمة عامة، بغض النظر عن معناها). هذه الـmigration
تضيف فقط **FK حقيقي جديد** فوق نفس العمود:
```python
op.create_foreign_key('fk_referral_trees_entity_id_affiliate_scopes',
    'referral_trees', 'affiliate_scopes', ['entity_id'], ['id'], ondelete='CASCADE')
```
✅ **مؤكَّد — القيد الفريد يعمل بنفس الفلسفة تلقائيًا، والـFK الجديد
يقوّيه بربط حقيقي بدل `Integer` غير مقيَّد.**

### 5. `Commission.order_id`/`order_item_id`/`product_id` أصبحت nullable

```python
op.alter_column('affiliate_commissions', 'order_id', nullable=True)
op.alter_column('affiliate_commissions', 'order_item_id', nullable=True)
op.alter_column('affiliate_commissions', 'product_id', nullable=True)
```
✅ **مؤكَّد — الثلاثة موجودة حرفيًا في قسم "4. affiliate_commissions"
من `upgrade()`.**

### 6. ترتيب العمليات: TRUNCATE أولاً، ثم DROP لجداول B وActionCommission، بلا FK violation

**الترتيب الفعلي في الملف:** الخطوة 0 (TRUNCATE) → خطوات 1-5 (CREATE/ALTER
لـscopes/tiers/commissions/referral_trees) → **الخطوة 6** (`DROP TABLE
affiliate_action_commissions`) → **الخطوة 7** (`DROP TABLE affiliate_trees,
commission_records, affiliate_configs`) → الخطوة 8 (`users` عمود جديد).

**فحص FK violation صراحة:**
- الجداول الأربعة المحذوفة (`affiliate_action_commissions`،
  `affiliate_trees`، `commission_records`، `affiliate_configs`) **لا
  يشير إليها أي جدول آخر بأي FK** (تأكَّد مسبقًا بـ`grep` شامل على
  الـmigration الأولية — صفر نتيجة لأي `ForeignKeyConstraint` يستهدف
  أيًا من الأربعة). حذفها **لا يتطلب أي ترتيب خاص فيما بينها** ولا
  علاقة له بخطوة TRUNCATE (تستهدف 3 جداول مختلفة تمامًا: `affiliate_commissions`،
  `affiliate_commission_tiers`، `referral_trees` — لا تقاطع مع الأربعة
  المحذوفة).
- TRUNCATE نفسها استُخدمت بصيغة `RESTART IDENTITY CASCADE` على الجداول
  الثلاثة **معًا في نفس الأمر** — يتجنب أي مشكلة ترتيب FK بين الثلاثة
  (لا حاجة لتحديد أيها يُفرَّغ أولًا، Postgres يتعامل معها كوحدة واحدة).
✅ **مؤكَّد — لا يوجد أي احتمال FK violation في الترتيب الحالي.**

**الخلاصة: النقاط الستة مؤكَّدة، نقطة واحدة (`scope_type`) كانت تحتاج
تصحيحًا فعليًا وتم تطبيقه. الملف جاهز للمراجعة النهائية الكاملة —
معروض بالكامل في رسالة الرد لهذه الجلسة.**
