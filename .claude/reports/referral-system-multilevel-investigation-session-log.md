# جلسة تشخيص: نظام الإحالة متعدد المستويات (10 مستويات)

**تاريخ:** 2026-08-19
**النوع:** تشخيص فقط — صفر كود، صفر migration، صفر تعديل.
**الهدف:** تمهيدًا لقرار حل `User.referred_by` المفقود (بند 5.3، مرتبط بإغلاق Backlog #10)، ولتقييم قابلية النظام الحالي لدعم "نسبة عمولة مختلفة حسب المنتج/القسم/الكيان".

---

## ملخص تنفيذي (اقرأ هذا أولًا)

**اكتشاف مركزي لم يكن موثّقًا في أي جلسة سابقة:** يوجد في المشروع **ثلاثة أنظمة إحالة/عمولة منفصلة تمامًا**، بثلاث مخططات بيانات مختلفة، لا تتقاطع مع بعضها إطلاقًا:

| # | النظام | الموديلات | من يكتب؟ | من يقرأ/يوزّع؟ | حي فعليًا؟ | يدعم نسبة لكل منتج؟ |
|---|---|---|---|---|---|---|
| A | **affiliate domain (10 مستويات، Product-Scoped)** | `ReferralTree` + `Commission` + `CommissionTier` | `AffiliateService.track_referral` (استدعاء حي وحيد: `academy/service.py`) | `AffiliateService.distribute_commissions` | ❌ **ميت** — لا يوجد أي استدعاء حي له (فقط Celery task غير مُفعَّل + توقيع خاطئ) | ✅ نعم، جزئيًا مبني بالفعل (لكن معطّل) |
| B | **commerce domain (10 مستويات، Sponsor Chain)** | `AffiliateTree` + `CommissionRecord` + `AffiliateConfig` | `CommerceService.register_affiliate` (مسار حي: `POST /affiliate/link`) | `CommerceService.distribute_commissions` (مُستدعاة مباشرة inline من `checkout`) | ✅ **هو الحي فعليًا** للطلبات التجارية | ❌ لا إطلاقًا — لا يوجد `product_id` في أي من الموديلات الثلاثة |
| C | **الـ12 دومين (Backlog #10, Direct)** | `ActionCommission` عبر `register_commission` | كل دومين من الـ12 عبر `_register_affiliate_commission` | لا يوجد توزيع — عمولة مباشرة لمستوى واحد فقط | ⚠️ الكود موصول، لكنه **يفشل بصمت دائمًا** لأن `User.referred_by` غير موجود كعمود | ❌ لا، مبلغ ثابت مكتوب Hardcoded في كل دومين |

**النتيجة الحاسمة لبند 7:** أي دعم لـ"نسبة عمولة مختلفة حسب المنتج" **غير متاح اليوم في أي مسار حي**. القطع اللازمة موجودة جزئيًا فقط في النظام (A) **الميت**. النظام (B) الوحيد الحي للطلبات التجارية **لا يملك أي بُعد منتج/قسم إطلاقًا** — نسبة واحدة عامة لكل مستأجر.

---

## 1) ReferralTree — القراءة الكاملة

`eppne-backend/app/domains/affiliate/models.py:39-65`

```python
class ReferralTree(Base):
    """شجرة الإحالة المخصصة (Product-Scoped Affiliate)"""
    __tablename__ = "referral_trees"
    __table_args__ = (
        Index("ix_referral_trees_tenant_id", "tenant_id"),
        Index("ix_referral_trees_referrer_id", "referrer_id"),
        Index("ix_referral_trees_referred_id", "referred_id"),
        Index("ix_referral_trees_unique_referred_scope",
              "referred_id", "entity_type", text("COALESCE(entity_id, 0)"), unique=True),
        Index("ix_referral_trees_depth", "depth"),
        Index("ix_referral_trees_entity_type", "entity_type"),
        Index("ix_referral_trees_entity_id", "entity_id"),
    )

    id, tenant_id, referrer_id, referred_id
    entity_type = Column(String(50), default="GLOBAL", nullable=False)
    entity_id   = Column(Integer, nullable=True)
    depth       = Column(Integer, nullable=False, default=1)
    path        = Column(String(500), nullable=True)   # موجود كعمود لكن لا يُملأ أبدًا في أي مكان (grep: لا استدعاء يمرر path=)
    created_at, updated_at
```

**دلالة `entity_type`/`entity_id` — مؤكَّدة من الاستخدام الفعلي، ليست تخمينًا:**
الاسم صريح في الـdocstring: **"Product-Scoped Affiliate"**. القيد الفريد `(referred_id, entity_type, COALESCE(entity_id,0))` يعني: **نفس المستخدَم المُحال يمكن أن يكون له أكثر من صف إحالة، واحد لكل (entity_type, entity_id)** — أي التصميم **يسمح صراحة** بأن يكون لنفس الشخص محيلين مختلفين حسب "أي منتج/كورس/كيان جاء منه". هذا **ليس** نوع صفحة أو مصدر تتبّع (زي UTM) — إنه فعلاً بُعد منتج/كيان تجاري.

**القيم الفعلية المستخدَمة لـ`entity_type` في الكود اليوم (grep شامل):**
- `"GLOBAL"` — القيمة الافتراضية، تُستخدم كـfallback في `distribute_commissions`.
- `"PRODUCT"` — مُستخدَمة حرفيًا (hardcoded) في `AffiliateService.distribute_commissions`/`_distribute_levels` (`service.py:288, 365`) عند التعامل مع طلبات الشراء (لكن هذا المسار كله ميت — راجع §4).
- `"COURSE"` — مُستخدَمة في `academy/service.py:298` عند تسجيل طالب بكورس عبر `affiliate_code` — **هذا هو الاستدعاء الحي الوحيد الذي يكتب فعليًا في `ReferralTree`**.
- `"HEADQUARTERS"` — في `scripts/seed_tenant.py:59` فقط (بيانات تجريبية/seed، ليست مسار تشغيل حقيقي).
- `"CROSS_DOMAIN"` — **تنويه مهم:** هذه القيمة تخص موديل مختلف تمامًا (`ActionCommission.entity_type`، الافتراضي في `register_commission`)، **وليست** قيمة فعلية لـ`ReferralTree.entity_type`. لا تخلط بينهما.

---

## 2) distribute_commissions / _distribute_levels / _get_commission_rate — القراءة الكاملة

`eppne-backend/app/domains/affiliate/service.py:261-390`

**كيف تُحسب المستويات العشرة فعليًا:**
- `distribute_commissions(order_id)`: تجلب الطلب وعناصره من `commerce_repo`. لكل عنصر (`product_id`)، تبحث عن `ReferralTree` بـ`entity_type="PRODUCT", entity_id=product_id` أولًا، وإن لم تجد تسقط إلى `entity_type="GLOBAL"` (بدون `entity_id`). إن لم تجد أي شيء، تتخطى العنصر بالكامل (لا عمولة).
- `_distribute_levels`: تمشي **صعودًا** في السلسلة عبر عمود `referrer_id` في `ReferralTree` — تبدأ من صف الإحالة الذي وجدته، وفي كل تكرار (حتى 10 مرات) تجلب `AffiliateProfile` الخاص بـ`referrer_id`، وتحسب العمولة، ثم تنتقل للمستوى الأعلى عبر `self.repo.get_referral_tree(referrer_id, tenant_id)` — **أي أنها تبحث عن "من أحال هذا المُحيل؟" عبر استعلام `ReferralTree.referred_id == referrer_id` (ليس عمود parent_id منفصل، بل نفس جدول `ReferralTree` يُستخدَم بشكل عودي/متسلسل بالاعتماد على referred_id/referrer_id).**
- ⚠️ **فجوة/باج مكتشَف مهم في المشي عبر السلسلة:** `AffiliateRepository.get_referral_tree(user_id, tenant_id)` (المُستخدَمة في حلقة `_distribute_levels` للانتقال للمستوى التالي) **لا تُمرِّر `entity_type`/`entity_id` إطلاقًا** — تستعلم فقط `ReferralTree.referred_id == user_id` وتتوقع نتيجة واحدة (`scalar_one_or_none`). لكن القيد الفريد في الموديل **يسمح صراحة** بوجود أكثر من صف لنفس `referred_id` (واحد لكل `entity_type`/`entity_id`، أي واحد لكل منتج). **إذا كان لمستخدم واحد أكثر من صف إحالة (لأكثر من منتج/كورس)، هذا الاستعلام سيرمي `MultipleResultsFound` عند محاولة صعود السلسلة.** هذا تعارض مباشر بين تصميم الـschema (يدعم تعدد النطاقات لكل مستخدم) ومنطق المشي في السلسلة (يفترض صفًا واحدًا فقط). هذا يمس مباشرة متطلب "الإحالة قابلة للربط بعدة منتجات" المذكور في طلبك — التصميم الحالي **غير آمن** لهذه الحالة حتى لو تم تفعيل هذا المسار الميت.

**من أين "مين حوّل مين" لكل مستوى؟** من `ReferralTree.referrer_id` فقط — لا يوجد أي استخدام لعمود `User.referred_by` في هذا المسار بالذات (النظام A لا يعرف عن `referred_by` إطلاقًا).

**`_get_commission_rate` — هل تأخذ معامل يخص المنتج؟**
```python
async def _get_commission_rate(self, tiers, level: int, product_id: int) -> Decimal:
    product_tier = await self.repo.get_commission_tier_by_product(tenant_id=self.tenant_id, product_id=product_id)
    if product_tier:
        return getattr(product_tier, f"level_{level}_pct", Decimal(0))
    if tiers:
        return getattr(tiers, f"level_{level}_pct", Decimal(0))
    return Decimal(0)
```
**نعم — تأخذ `product_id` فعليًا**، وتبحث أولًا عن `CommissionTier` مخصص للمنتج (`entity_type="PRODUCT", target_product_id=product_id`)، وتسقط إلى الإعدادات العامة (`entity_type="GLOBAL", target_product_id IS NULL`) إن لم تجد. **هذا يناقض الافتراض الوارد في طلب الجلسة بأن الدالة "بس بتاخد رقم المستوى" — الكود يثبت العكس، لكنه معطَّل بالكامل عمليًا (راجع §4).**

---

## 3) من يكتب فعليًا في ReferralTree؟

`grep` شامل لكل استدعاء لـ`create_referral_tree`/`track_referral` في الباك إند بالكامل:

- **التعريف:** `AffiliateService.track_referral` (`affiliate/service.py:167`) → `AffiliateRepository.create_referral_tree` (`repository.py:129`).
- **الاستدعاء الحي الوحيد:** `academy/service.py:295` — عند تسجيل مستخدم في كورس عبر `affiliate_code`، تُستدعى `track_referral(entity_type="COURSE", entity_id=course_id)`.
- **لا يوجد أي استدعاء آخر** لـ`track_referral` في أي مكان في المشروع (لا في الـ12 دومين، لا في commerce، لا في أي مكان آخر).

**الخلاصة:** `ReferralTree` **ليست** كود ميت بالكامل — هي حية فعليًا من مسار Academy (تسجيل الكورسات)، لكنها **معزولة تمامًا** عن الـ12 دومين وعن نظام التجارة (commerce)، وحتى لو كانت مكتوبة، **لا يوجد أي مسار حي يقرأها لتوزيع عمولات** (راجع §4) — فيما عدا عرضها فقط عبر `GET /affiliate/tree`.

---

## 4) من يستدعي distribute_commissions فعليًا؟

يوجد **تعريفان منفصلان تمامًا** بنفس الاسم في دومينين مختلفين — هذا مصدر التباس محتمل يجب الانتباه له:

### 4.أ — `AffiliateService.distribute_commissions` (نظام A، الـ10 مستويات Product-Scoped)
- المُستدعي الوحيد في الكود: `app/tasks/affiliate.py:67` داخل مهمة Celery باسم `affiliate.distribute_commissions`.
- **لا يوجد أي مكان في المشروع بأكمله يستدعي `distribute_commissions_task.delay(...)` أو `.apply_async(...)` أو `send_task("affiliate.distribute_commissions", ...)`** — `grep` شامل لم يجد أي نتيجة. **المهمة معرَّفة لكنها غير مُفعَّلة (dead task wiring) — لا تُستدعى أبدًا من أي مسار طلب حقيقي.**
- ⚠️ حتى لو فُعِّلت مستقبلًا، توقيعها اليوم **خاطئ**: `tasks/affiliate.py:67` يستدعيها بمعاملين `service.distribute_commissions(order_id, tenant_id)`، بينما التعريف الفعلي في `affiliate/service.py:261` يقبل معاملًا واحدًا فقط (`self, order_id`) — سيرمي `TypeError` فورًا لو تم تفعيله بدون إصلاح.

### 4.ب — `CommerceService.distribute_commissions` (نظام B، الـ10 مستويات Sponsor Chain — **هذا هو الحي فعليًا**)
`eppne-backend/app/domains/commerce/service.py:251-292`
```python
async def distribute_commissions(self, order_id: int, affiliate_code: str, order_total: Decimal):
    sponsor_id = int(affiliate_code) if affiliate_code.isdigit() else None
    ...
    chain = await self.repo.get_sponsor_chain(sponsor_id, self.tenant_id, max_depth=10)
    config = await self.repo.get_affiliate_config(self.tenant_id)
    ...
    for level, beneficiary_id in enumerate(chain, start=1):
        pct = getattr(config, f"level_{level}_pct", Decimal(0))
        amount = order_total_decimal * Decimal(str(pct)) / Decimal(100)
        await self.repo.create_commission(beneficiary_id=..., order_id=..., level_earned=level, amount=..., ...)
```
- **مُستدعاة مباشرة (inline، بلا Celery) من `checkout()` نفسها**: `commerce/service.py:215-220` — `if checkout_data.affiliate_code and store.is_affiliate_enabled: await self.distribute_commissions(order.id, checkout_data.affiliate_code, total)`. **هذا هو المسار التجاري الحي الوحيد فعليًا لتوزيع عمولات 10 مستويات على طلبات حقيقية.**
- تعتمد على `sponsor_id = int(affiliate_code)` — أي أن "كود الإحالة" هنا هو **رقم `user_id` الخام**، وليس `AffiliateProfile.referral_code` الأبجدي (نظام A). **نظاما الأكواد غير متوافقين إطلاقًا مع بعضهما.**
- السلسلة تُبنى عبر `get_sponsor_chain` → موديل **مختلف تمامًا**: `AffiliateTree` (`commerce/models.py:191`، أعمدة `user_id`/`sponsor_id`/`network_depth`، بلا أي `entity_type`/`entity_id`/`product_id`).
- النسبة تُقرأ من `AffiliateConfig` (`commerce/models.py:229`) — **صف واحد لكل tenant فقط** (`unique index على tenant_id`)، لا يوجد فيه أي عمود `product_id`/`category`/`target_entity`. **نسبة واحدة ثابتة لكل مستوى لكل المستأجر، بغض النظر عن المنتج المُشترى.**
- العمولات تُخزَّن في `CommissionRecord` (`commerce/models.py:207`) — أيضًا بلا `product_id`.
- **هل تختلف النسبة فعليًا حسب المنتج المُشترى في هذا المسار؟ لا إطلاقًا** — `order_total` بالكامل (وليس `item_amount` لكل منتج على حدة كما في نظام A) هو ما يُضرب بالنسبة، والنسبة نفسها عامة لكل المستأجر.

---

## 5) جدول Commission — القراءة الكاملة

يوجد **جدولا "عمولة" منفصلان تمامًا** — يجب عدم الخلط بينهما:

### `affiliate.Commission` (نظام A، غير مُستخدَم فعليًا — راجع §4.أ)
`affiliate/models.py:68-103` — يحتوي `product_id` (FK)، `order_id`, `order_item_id`, `item_amount`, `order_amount`, **`commission_rate`** (تُخزَّن كقيمة snapshot وقت الإنشاء، وليست مرجعًا لجدول آخر)، `commission_amount`, `referral_level`, `entity_type` (افتراضي `"PRODUCT"`).
`commission_rate` **تُحسب وقت التوزيع** من `_get_commission_rate` (التي تراجع `CommissionTier` — تدعم `product_id`، راجع §2) ثم **تُخزَّن كقيمة ثابتة (snapshot)** في الصف — أي أنها ليست FK لجدول أسعار، بل نتيجة حساب لحظي محفوظة. لكن هذا كله بلا فائدة عملية حاليًا لأن `distribute_commissions` (النظام A) ميت.

### `commerce.CommissionRecord` (نظام B، **هو الحي فعليًا**)
`commerce/models.py:207-226` — `beneficiary_id`, `order_id`, `level_earned`, `amount`, `currency`, `status`. **لا يوجد `product_id` ولا `commission_rate` مخزَّن في هذا الجدول إطلاقًا** — فقط `amount` النهائي المحسوب، بلا أي أثر لأي بُعد منتج.

---

## 6) الإجابة الحاسمة المطلوبة (بند 6) — عمولات الـ12 دومين: مستوى واحد مباشر أم تصاعد عبر 10 مستويات؟

**الدليل من الكود (قاطع، وليس تخمينًا):** كل موضع استدعاء من الـ12 دومين (`zamakana`, `transport`, `employment`, `tourism_sports`, `tenders_auctions`, `digital_twin`, `service_marketplace`, `realestate`, `arbitration_syndicates`, `manufacturing`, `invitations`, `insurance`) يتبع **حرفيًا** نفس النمط:

```python
# مثال زمكانة (zamakana/service.py:645-661) — نفس النمط في كل الـ12 دومين
async def _register_affiliate_commission(self, user_id, tenant_id, action_type):
    user = await user_repo.get_by_id(user_id, tenant_id)
    if user and user.referred_by:                      # ← عمود واحد، محيل واحد مباشر
        await affiliate_service.register_commission(
            affiliate_id=user.referred_by,              # ← لا يوجد أي walk-up للسلسلة
            user_id=user_id, amount=..., ...
        )
```

- **لا يوجد أي استدعاء لـ`ReferralTree`/`get_referral_tree`/أي منطق تصاعدي في أي من الـ12 دومين.**
- `AffiliateService.register_commission` نفسها (`service.py:660-687`) لا تحتوي أي حلقة أو تكرار — فقط تحل ملف `AffiliateProfile` للمُحيل المُمرَّر وتُنشئ صف `ActionCommission` واحد.
- **النتيجة: عمولة الـ12 دومين هي عمولة مباشرة لمستوى واحد فقط (direct referrer)، مستقلة تمامًا عن أي من نظامي الـ10 مستويات (A أو B).**

**لكن — هل هذا "قرار تصميم صريح" أم مجرد أثر تطبيق فعلي بلا قرار موثَّق؟**
لا يوجد أي تعليق، اسم، أو توثيق في الكود يقول صراحة "هذه عمولة مقصودة كمستوى واحد فقط بعكس نظام X". الدليل الوحيد الموجود هو نمط الاستدعاء الفعلي نفسه + docstring `ActionCommission` (`models.py:106-113`) التي تقول إن الموديل "منفصل عمدًا عن `Commission`" لأسباب تتعلق بغياب `order_id`/`product_id` حقيقي في هذه الأحداث — **وليس** لأسباب تتعلق بعدد المستويات. **هذا سؤال مفتوح صراحة لك:** هل الأثر الحالي (مستوى واحد) هو المطلوب فعلاً منتجيًا، أم أنه ناتج جانبي لكون `register_commission` أُضيفت لاحقًا لسد فجوة "missing methods" (راجع `.claude/reports/affiliate-service-missing-methods-session-log.md`) بدون تصميم متعمد لسلوك متعدد المستويات؟ الكود لا يحسم هذا.

---

## 7) هل التصميم الحالي يدعم "نسبة عمولة مختلفة حسب المنتج/القسم/الكيان"؟

**الإجابة مجزّأة حسب النظام الثلاثة (لا إجابة واحدة صحيحة للمشروع ككل):**

- **نظام A (affiliate/ReferralTree+CommissionTier):** ✅ **مبني جزئيًا بالفعل** لدعم هذا البعد تمامًا كما تطلب — `ReferralTree` تدعم نطاقًا لكل (مستخدَم × entity_type × entity_id)، و`CommissionTier` تدعم صفًا مخصصًا لكل `target_product_id` بنسب مستقلة لكل مستوى، و`_get_commission_rate` تراجع فعليًا حسب `product_id`. **لكنه غير قابل للاستخدام اليوم لسببين:** (1) ميت بالكامل تشغيليًا (§4.أ)، (2) به باج بنيوي في المشي عبر السلسلة عند تعدد النطاقات لنفس المستخدم (§2) — يحتاج إصلاحًا قبل أي اعتماد عليه، وحتى تصميمه محدود بـ`entity_type="PRODUCT"`/`"GLOBAL"` فقط داخل `distribute_commissions` (لا "قسم" ولا أنواع كيانات أخرى مدعومة في منطق التوزيع الفعلي، رغم أن الموديل نفسه عام).
- **نظام B (commerce/AffiliateTree+CommissionRecord+AffiliateConfig — الحي فعليًا للطلبات التجارية):** ❌ **لا يدعم هذا البعد إطلاقًا.** لا يوجد أي عمود `product_id`/`category_id` في أي من الموديلات الثلاثة. `AffiliateConfig` صف واحد فقط لكل tenant. يحتاج **تصميم schema إضافي جديد بالكامل** (جدول قواعد عمولة منفصل بـ`product_id`/`category_id` + نسبة لكل مستوى) إذا أردت تفعيل هذا البعد على المسار التجاري الحي فعليًا.
- **نظام C (الـ12 دومين/ActionCommission):** ❌ **لا يدعم أي نسب أصلاً** — المبلغ رقم `Decimal` ثابت مكتوب مباشرة في كود كل دومين (مثال: `Decimal("2.00")` أو `Decimal("1.00")` في `zamakana/service.py:652`)، وليس نسبة مئوية محسوبة من أي شيء، ولا مستوى، ولا جدول إعدادات.

**الخلاصة العامة لبند 7:** بافتراض أن "المسار الحي" هو المعيار (وهو المنطقي)، **لا يوجد اليوم أي دعم فعلي وعملي** لنسبة عمولة مختلفة حسب المنتج/القسم في أي مسار يعمل فعلاً. أقرب تصميم موجود لما تطلبه (نظام A) موجود لكنه معطَّل وبه باج بنيوي غير مُصلَح.

---

## 8) تعارضات/غموض مع الجلسات السابقة

- **جلسة `affiliate-service-missing-methods`** قالت إن `ReferralTree` "غير مستخدمة حاليًا من أي مسار حي في الـ12 دومين" — **هذا صحيح وما زال صحيحًا** (الـ12 دومين لا تلمس `ReferralTree` إطلاقًا). لكن **يجب عدم تعميم هذا** إلى "`ReferralTree` ميتة بالكامل" — هي **حية فعليًا** من مسار Academy (`track_referral` عبر تسجيل الكورسات، §3) وتُقرأ حيًا عبر `GET /affiliate/tree` للعرض فقط (وليس للتوزيع). الجلسات السابقة لم تفحص مسار Academy أو نظام commerce المنفصل (B) إطلاقًا — لأنها كانت مركّزة على الـ12 دومين فقط.
- **لم يرد ذكر نظام (B) — `commerce.AffiliateTree`/`CommissionRecord`/`AffiliateConfig` — في أي تقرير سابق اطلعتُ عليه.** هذا اكتشاف جديد لهذه الجلسة، وهو **الأهم عمليًا** لأنه المسار الحي الوحيد فعليًا لتوزيع عمولات متعددة المستويات على طلبات شراء حقيقية اليوم — أي قرار مستقبلي بشأن "نسبة لكل منتج" يجب أن يأخذه في الاعتبار، وليس فقط نظام `affiliate` domain.
- **`User.referred_by` غير موجود كعمود** على `User` model (`identity/models.py`) — مؤكَّد بالقراءة الكاملة للموديل (§ أعلاه) وبتطابقه مع ما وثّقته الجلسات السابقة (`test_affiliate_service_missing_methods.*`, `test_user_repository_get_*_audit.*`) بند 5.3. لا تعارض هنا — توثيق متسق.

---

## ملاحظة صريحة خارج نطاق الطلب المباشر (للسجل فقط، بلا اقتراح حل)

توقيع الاستدعاء الخاطئ لمهمة Celery (§4.أ) والباج البنيوي في `get_referral_tree` عند تعدد النطاقات (§2) هما اكتشافان جانبيان أثناء القراءة — مذكوران هنا للتوثيق فقط تمشيًا مع قاعدة "توثيق أولًا بأول"، وليسا اقتراح حل ولا جزءًا من أي قرار مطلوب في هذه الجلسة.
