# جلسة `affiliate-service-missing-methods` — Backlog #10 — سجل الجلسة

> جلسة منفصلة تمامًا عن كل الجلسات السابقة. راجع
> `.claude/plans/affiliate-service-missing-methods-session-instructions.md`
> للتعليمات الكاملة. **القاعدة الصارمة: صفر تنفيذ فوري — تشخيص كامل ثم
> توقف للموافقة.**

---

## 1. حالة التشخيص: مكتمل. لم يُكتب أي كود بعد.

## 2. الميثودز المفقودة فعليًا على `AffiliateService`

قراءة كاملة لـ`app/domains/affiliate/service.py` (648 سطر) أثبتت: **لا
يوجد** أي ميثود اسمها `register_commission` أو `_register_affiliate_commission`
أو `get_user_by_code` على الكلاس. الميثودز الموجودة فعليًا ذات الصلة:
`distribute_commissions(order_id)` (توزيع متعدد المستويات مرتبط بطلب/Order)،
`_distribute_levels`، `_get_commission_rate`، و`get_or_create_profile`.

**اكتشاف إضافي عن الوصف الأصلي في ملف التعليمات:** الوصف افترض ميثود
واحدة مفقودة. **التشخيص الفعلي كشف ميثودين مفقودتين مختلفتين**:

| الميثود المفقودة | عدد مواضع الاستدعاء | الدومينات |
|---|---|---|
| `AffiliateService.register_commission(...)` | **12 موضع مباشر** (+ موضع خارجي واحد عبر wrapper موجود في `employment`) | insurance, invitations, manufacturing, tenders_auctions, tourism_sports, transport, zamakana, employment, arbitration_syndicates, realestate, service_marketplace, digital_twin |
| `AffiliateService.get_user_by_code(affiliate_code)` | 1 موضع | digital_twin فقط (مسار بديل عند غياب `referred_by` لكن وجود `affiliate_code`) |

## 3. قايمة كاملة لكل موضع استدعاء (12 دومين)

كل دومين من الـ12 عنده **نفس النمط المعماري بالحرف**: ميثود خاص باسم
`_register_affiliate_commission` (مُعرَّف داخل خدمة الدومين نفسه، **موجود
وليس مفقودًا**) يُستدعى من نقطة أو أكثر في تدفق العمل، وهو بدوره يستدعي
`AffiliateService.register_commission(...)` (هي المفقودة فعليًا) داخل
`try/except Exception` **صامت** (فقط `logger.error(...)`, بلا `raise`).

| # | الدومين | ملف/سطر التعريف | نقاط الاستدعاء الفعلية (الملف/السطر) | حماية try/except؟ |
|---|---|---|---|---|
| 1 | `zamakana` | `service.py:645` | `:90` (`NODE_CREATED`), `:234` (`CAMPAIGN_CREATED`), `:399` (`PLEDGE_FULFILLED`) | نعم، صامتة بالكامل |
| 2 | `transport` | `service.py:574` | `:362` (fare), `:537` (delivery_fee) | نعم، صامتة |
| 3 | `tourism_sports` | `service.py:507` | `:171` (`PROGRAM_BOOKED`), `:455` (`PLAYER_TRANSFER`) | نعم، صامتة |
| 4 | `tenders_auctions` | `service.py:479` | `:87` (`TENDER_CREATED`), `:430` (`AUCTION_WON`) | نعم، صامتة |
| 5 | `service_marketplace` | `service.py:482` | `:211` (شراء خدمة) | نعم، صامتة |
| 6 | `realestate` | `service.py:581` | `:245` (شراء وحدة), `:396` (إيجار، أول قسط) | نعم، صامتة |
| 7 | `arbitration_syndicates` | `service.py:559` | `:131` (`ARBITRATION_CASE_CREATED`), `:360` (`SYNDICATE_JOINED`) | نعم، صامتة |
| 8 | `manufacturing` | `service.py:63` | `:116` (`FACILITY_CREATED`) | نعم، صامتة |
| 9 | `invitations` | `service.py:65` | `:213` (`INVITATION_CREATED`), `:328` (`LEAD_CONVERTED`), `:681` (`CAMPAIGN_CREATED`) | نعم، صامتة |
| 10 | `insurance` | `service.py:84` | `:209` (`INSURANCE_SUBSCRIPTION`) | نعم، صامتة |
| 11 | `employment` | `service.py:94` | `:177` (`JOB_CREATED`), `:335` (`CONTRACT_CREATED`) + استدعاء خارجي من `app/tasks/employment.py:345` (`SALARY_PAID`، عبر Celery task) | نعم، صامتة |
| 12 | `digital_twin` | `service.py:60` | `:123` (`TWIN_CREATION`), `:191` (`TWIN_INTERACTION`، مع `affiliate_code` اختياري) | نعم، صامتة |

**كل الـ36 نقطة استدعاء (`grep` شامل، عدد مؤكَّد وليس تقديريًا) محمية
بـ`try/except Exception` صامت بلا استثناء واحد** — يعني الطلب الأساسي في
كل الحالات الـ12 ينجح ظاهريًا (200/201) والعمولة تضيع بصمت، **طالما وصل
التنفيذ فعليًا لسطر `register_commission` نفسه** (انظر البند 5 — في
الواقع لا يصل غالبًا).

## 4. توقيع `register_commission` الفعلي المُستخرَج من الاستخدام الحي

**كل الـ12 دومين بلا استثناء واحد يستخدمون نفس التوقيع بالضبط**
(kwargs، صفر تباين):

```python
await affiliate_service.register_commission(
    affiliate_id=<int>,   # = user.referred_by (كل المواضع الـ12)
    user_id=<int>,        # المستخدم الذي نفّذ الفعل المُولِّد للعمولة
    amount=<Decimal>,     # مبلغ العمولة المحسوب مسبقًا في نفس الدومين
    description=<str>,
    status="PENDING",
)
```

**النِسَب/القيم الثابتة لحساب العمولة محسوبة بالفعل داخل كل دومين قبل
النداء** (مش مفقودة، لكنها مبعثرة ومكرَّرة بلا مصدر مركزي):
zamakana (2.00 ثابت أو 1.00)، transport (2%)، tourism_sports (5%)،
tenders_auctions (5.00/25.00 ثابت)، service_marketplace (10%)،
realestate (2%)، arbitration_syndicates (5.00/2.00 ثابت)، manufacturing
(10.00/5.00 ثابت)، invitations (2.00/5.00 ثابت)، insurance (2%)،
employment (2.00 ثابت أو 2%)، digital_twin (5.00 ثابت أو 10%).

**الخلاصة: منطق حساب "النسبة/المبلغ" موجود (لو مبعثر)، فمفيش سؤال
"إزاي تتحسب العمولة" — لكن فيه فجوة تصميمية أعمق وأخطر في كيفية *تخزينها*،
موضّحة في البند التالي.**

## 5. الاكتشاف الحرج: `register_commission` مستحيل يكون wrapper بسيط — تعارض بنيوي حقيقي مع الـschema

هذا هو "القرار الحساس" المذكور صراحة في تعليمات الجلسة. تفصيل الأدلة:

### 5.1 جدول `Commission` (`affiliate/models.py:68-103`) مصمَّم حصريًا لعمولات مرتبطة بطلب تجاري (Order)

```python
order_id       = Column(..., ForeignKey("orders.id"), nullable=False)
order_item_id  = Column(..., ForeignKey("order_items.id"), nullable=False)
product_id     = Column(..., ForeignKey("products.id"), nullable=False)
item_amount    = Column(..., nullable=False)
order_amount   = Column(..., nullable=False)
commission_rate= Column(..., nullable=False)
referral_level = Column(..., nullable=False)
```

كل هذه الأعمدة **NOT NULL بلا default**، وثلاثة منها **FK حقيقي** على
جداول تجارة (orders/order_items/products). `AffiliateRepository.create_commission`
(`repository.py:138`) تمرر `**kwargs` مباشرة لمُنشئ `Commission(...)` —
أي قيمة مفقودة تفشل عند commit بـ`IntegrityError`/`NOT NULL violation`،
وأي `order_id`/`product_id` وهمي (0 أو placeholder) يفشل بـ
`ForeignKeyViolationError` حقيقي (مفيش صف فعلي بهذا الـid).

**لا شيء من الـ12 دومين المستدعية لـ`register_commission` عنده order_id
أو order_item_id أو product_id حقيقي** — دي كلها أحداث دومين مختلفة
تمامًا (إنشاء عقدة zamakana، حجز برنامج سياحي، توظيف، اشتراك تأمين،
تفاعل توأم رقمي...) **بلا أي علاقة بجدول `orders` التجاري إطلاقًا.**

**النتيجة: `register_commission` لا يمكن أن يكون مجرد استدعاء لـ
`self.repo.create_commission(...)` بنفس الحقول — الجدول الحالي لا
يستوعب "عمولة بلا Order" أصلًا.** هذا يخالف نمط `get_active_subscription`
(الجلسة السابقة `saas-control-service`) اللي كان فيه wrapper بسيط لأن
البيانات المطلوبة كانت موجودة فعلاً بشكل مكافئ — هنا العكس: **البيانات
المطلوبة (order_id/product_id) غير موجودة من الأساس ولا يمكن اختراعها.**

### 5.2 التباس دلالي في معنى `affiliate_id` نفسه

في كل الـ12 موضع: `affiliate_id=user.referred_by` — وهذه **قيمة من نطاق
`users.id`** (نفس نطاق `user_id` الممرَّر بجانبها). لكن `Commission.affiliate_id`
في الـmodel هو **FK على `affiliate_profiles.id`** — نطاق مختلف تمامًا
(نفس فئة الباج الموثَّقة سابقًا في `PROGRESS_LOG.md` كـ
`tourism-place-transfer-bid-player-id-user-id-conflict` و
`insurance-review-claim-issuer-entity-id-reviewer-id-conflict`: خلط
نطاقي IDs مختلفين كأنهما نفس المعنى). أي تنفيذ حرفي بيمرر
`user.referred_by` كـ`affiliate_id` مباشرة لـ`repo.create_commission`
سيفشل غالبًا بـ`ForeignKeyViolationError` على `affiliate_profiles.id`
(إلا لو تصادف رقميًا user_id == profile_id، غير مضمون إطلاقًا).

**لازم `register_commission` تعمل internal lookup**: تاخد `user_id`
المُحيل (المُسمَّى خطأً `affiliate_id` في كل الاستدعاءات)، وتجيب/تنشئ
`AffiliateProfile` بتاعه (بنفس نمط `get_or_create_profile` الموجود
أصلاً)، وتستخدم `.id` بتاع البروفايل الفعلي كـ`Commission.affiliate_id`.
هذا قرار تصميمي بسيط ومباشر (مش حساس)، لكن لازم يُذكر صراحة لأنه غير
موجود في أي من الاستدعاءات الـ12 الحالية.

### 5.3 اكتشاف أعمق وأخطر: `User.referred_by` غير موجود إطلاقًا كحقل في الـmodel

`grep` شامل لـ`referred_by\s*=\s*Column` عبر المشروع كله: **صفر نتيجة**.
قراءة كاملة لـ`app/domains/identity/models.py` (كلاس `User` بالكامل، الأسطر
14-94): **لا يوجد أي عمود، علاقة (`relationship`)، أو `property` اسمها
`referred_by`.** أقرب مفهوم موجود فعليًا هو `ReferralTree` (`affiliate/models.py:39-65`)
— لكنه **مرتبط بنطاق (`entity_type`/`entity_id`) لكل إحالة**، مش حقل مسطَّح
عام على `User`، ومُستخدَم فقط داخل `AffiliateService.track_referral`/
`distribute_commissions` — **لا نقطة استدعاء واحدة من الـ12 دومين
تستخدم `ReferralTree` أو `track_referral` أو `get_referral_by_scope`.**

**الأثر العملي:** أي وصول فعلي لسطر `if user and user.referred_by:` في
أي من الـ12 دومين سيرمي **`AttributeError: 'User' object has no attribute
'referred_by'`** — يعني حتى لو أُضيفت `register_commission` اليوم
بالضبط بالتوقيع المطلوب، **الاستدعاء الفعلي لن يصلها أبدًا** — الكراش
يحصل سطر واحد قبلها، ويُبتلَع بنفس `except Exception` الصامت. **هذا
يعني فقدان العمولة صامت اليوم لسبب مختلف تمامًا عمّا وثّقته ملفات
التسليم القديمة ("register_commission مفقودة") — السبب الفعلي الأعمق
هو غياب آلية "مين حوّل المستخدم ده" بالكامل من نموذج `User`.**

### 5.4 طبقة إضافية: 10 من الـ12 موضع لا تصل حتى لسطر `referred_by` — تُحجَب أبكر بباجات مفتوحة موثَّقة مسبقًا (خارج نطاق #10)

قراءة كل تعريفات `_get_user`/استدعاءات `UserRepository` مباشرة داخل
الـ12 ميثود:

| النمط | الدومينات | الباج المسبِّب | حالة التتبع |
|---|---|---|---|
| `user_repo.get_by_id(user_id)` بمعامل واحد (الصحيح يحتاج `tenant_id` إجباري ثانٍ — `identity/repository.py:21`) | invitations, manufacturing, insurance, service_marketplace (عبر `_get_user`)، transport, realestate (مباشرة عبر `self.user_repo`)، zamakana, tourism_sports, tenders_auctions, arbitration_syndicates (inline) | `TypeError: missing 1 required positional argument: 'tenant_id'` | **Backlog #1 مفتوح مسبقًا** (`user-repository-get-by-id-audit`) — موثَّق أصلًا في `PROGRESS_LOG.md` بند #10 كـ"تأكيد إضافي" لنفس هذا البند |
| `user_repo.get_user(user_id)` (ميثود قد لا تكون موجودة على `UserRepository` إطلاقًا) | employment, digital_twin (عبر `_get_user`) | `AttributeError` محتمل | **Backlog #8 مفتوح مسبقًا** (`user-repository-get-user-audit`، 6 مواضع) |

**يعني: 12/12 موضع اليوم يفشلون بالفعل قبل الوصول حتى لفحص `referred_by`،
بسبب بند #1 أو #8 (مفتوحان مسبقًا، مش من نطاق هذه الجلسة) — ثم حتى لو
اتصلحوا، هيفشلوا فورًا بعدها بسبب غياب `referred_by` نفسه (بند 5.3
فوق) — ثم حتى لو اتصلح ده كمان، `register_commission` نفسها مش موجودة
(بند 2) وحتى لو اتبنت، الجدول الحالي مش مصمَّم يستوعب استدعاءاتها
(بند 5.1). أربع طبقات فشل متتالية، كل واحدة تُخفي التالية بصمت.**

**قرار نطاق:** بند #1/#8 **خارج نطاق هذه الجلسة صراحة** (تُعالَج في
جلسات منفصلة مخصَّصة لهما) — لكن **لازم تُذكر هنا لأنها تمنع أي تحقق
حي فعلي لإصلاح #10 بمفرده**: لو أصلحنا `register_commission` بس بدون
لمس #1/#8/5.3، **الاستدعاءات الـ12 هتفضل تفشل صامتة بالضبط زي دلوقتي**
(بس بسبب مختلف). أي تحقق حي حقيقي لهذه الجلسة لازم يتعامل مع هذا
بوضوح — إما (أ) نطلب استثناء نطاق لتصليح #1/#8/5.3 هنا كجزء من نفس
الـcommit (يخالف "خارج النطاق صراحة" في تعليمات الجلسة الأصلية)، أو
(ب) نكتفي بتحقق حي عبر استدعاء مباشر لـ`register_commission` (تجاوز
الـwrapper المكسور)، مع توثيق صريح إن الـwrapper نفسه (`_register_affiliate_commission`
في كل دومين) هيفضل معطَّل عمليًا لحد ما #1/#8/5.3 تتصلح في جلسات لاحقة.
**هذا قرار محتاج توجيهك صراحة — مذكور في التوصية تحت.**

## 6. `get_user_by_code` (digital_twin فقط)

`digital_twin/service.py:80`: `referrer = await affiliate_service.get_user_by_code(affiliate_code)`
ثم `referrer_id = referrer.id`. لا يوجد ميثود بهذا الاسم على
`AffiliateService`. أقرب مكافئ موجود: `AffiliateRepository.get_affiliate_by_code(code, tenant_id)`
(يرجع `AffiliateProfile`, ليس `User`) — لو استُخدم، `referrer.id` هيبقى
`AffiliateProfile.id` (صح لـ`Commission.affiliate_id`)، بعكس المسار
التاني في نفس الدالة (`user.referred_by`) اللي بيرجع `users.id` — **نفس
دالة `_register_affiliate_commission` الواحدة في digital_twin عندها
مساران بيحطّوا قيم من نطاقين مختلفين في نفس المتغير `referrer_id`** —
دليل إضافي على غياب تعريف واضح لمعنى `affiliate_id` (بند 5.2).

## 7. التوصية

**مش قرار "بناء منطق حساب عمولة من الصفر" (النسب موجودة ومحسوبة مسبقًا
في كل دومين) ولا "wrapper بسيط صرف" (زي #7/#9) — هي حالة وسطى تحتاج
قرار منتجي/تصميمي صريح قبل أي سطر كود:**

1. **`register_commission` تحتاج تصميم جديد فعلي** (مش مجرد rename)،
   لأن جدول `Commission` الحالي مصمَّم حصريًا لعمولات مرتبطة بـOrder
   حقيقي — والاستدعاءات الـ12 كلها أحداث بلا Order. الخيارات المتاحة
   (تحتاج قرارك):
   - **(أ)** توسيع جدول `Commission` بجعل `order_id`/`order_item_id`/
     `product_id`/`commission_rate`/`referral_level` قابلة للـNULL
     (migration)، و`register_commission` تُنشئ صف بـ`entity_type` جديد
     (مثلاً `"CROSS_DOMAIN"` أو `"MANUAL"`) وهذه الأعمدة `None`.
   - **(ب)** جدول/موديل منفصل تمامًا لعمولات الأحداث العابرة للدومينات
     (بلا الحقول التجارية الإجبارية)، مع توحيد الاستعلام لاحقًا
     (`get_commissions_by_user` ستحتاج تعديل لتشمل المصدرين).
   - **(ج)** أي تصميم آخر تراه مناسبًا.
2. **داخليًا، `register_commission` لازم تعمل `get_or_create_profile`
   (أو مكافئ) على الـ`affiliate_id` الممرَّر** (لأنه فعليًا `user_id`
   في كل الاستدعاءات الحالية) عشان تحل مشكلة نطاق الـFK (بند 5.2) —
   هذا الجزء تقني بحت، مش قرار حساس.
3. **`get_user_by_code`** يمكن أن تكون wrapper بسيط حول
   `repo.get_affiliate_by_code` — لكن لازم تُحسم أولاً قيمة الإرجاع
   المتوقَّعة (`AffiliateProfile` أم `User`) بما يتسق مع القرار في
   البند 1-2، لأن digital_twin يفترض إنها ترجع كائن بـ`.id` مكافئ
   لنفس معنى `affiliate_id` في المسار التاني من نفس الدالة.
4. **بند `User.referred_by` غير الموجود (5.3) وبنود #1/#8 المفتوحة
   مسبقًا (5.4) لازم قرار نطاق صريح منك**: هل تُعالَج ضمن commit هذه
   الجلسة (خروج محدود عن "خارج النطاق" الأصلي، لكنه ضروري لأي تحقق حي
   حقيقي)، أم تُوثَّق كحاجز معروف وتُترك لجلسات #1/#8 المخصَّصة (والتحقق
   الحي هنا يقتصر على استدعاء `register_commission` مباشرة، متجاوزًا
   الـwrapper المكسور، لإثبات أن الميثود الجديدة نفسها تعمل بمعزل عن
   الطبقات المعطوبة فوقها)؟ **بدون توجيهك هنا، مستحيل أُقدّم على تصميم
   `register_commission` أو تنفيذها.**

**متوقف هنا تمامًا في انتظار قرارك على البنود 1 و4 تحديدًا (2 و3 نتيجة
مباشرة لأي قرار تختاره في 1) — صفر كود مكتوب حتى الآن.**

---

## 8. قرارات المستخدم المعتمَدة [بعد عرض التشخيص]

1. **تصميم `Commission`: الخيار (ب) معتمَد** — جدول منفصل تمامًا
   للعمولات العابرة للدومينات، بدل توسيع `affiliate_commissions`
   التجاري الحالي بأعمدة nullable. السبب المذكور: الحفاظ على صرامة
   NOT NULL/FK على جدول العمولات التجارية الأصلي.
2. **النطاق: نهائي وصريح** — بند #1 (`user-repository-get-by-id-audit`)،
   بند #8 (`user-repository-get-user-audit`)، وبند 5.3 (`User.referred_by`
   المفقود بالكامل) **خارج نطاق هذه الجلسة بالكامل، بلا استثناء.**
   السبب: #1/#8 أوسع من نطاق الأفيليت (يؤثران على دومينات كتير تانية)،
   و5.3 قرار تصميمي مستقل (نظام الإحالة العام) يستاهل جلسة منفصلة.
   **التحقق الحي هنا سيكون فقط عبر استدعاء `register_commission` مباشرة**
   (تجاوز الـwrapper `_register_affiliate_commission` المكسور في كل
   دومين) — إثبات أن الميثود الجديدة نفسها تعمل بمعزل عن الطبقات
   المعطوبة فوقها. **يجب توثيق بوضوح شديد في `PROGRESS_LOG.md` عند
   الإغلاق:** الـwrapper في كل الـ12 دومين سيفضل معطَّلاً عمليًا
   ويبتلع العمولة صامتة حتى تُحل #1/#8/5.3 في جلسات لاحقة — **هذا
   الإصلاح ضروري لكن غير كافٍ لوحده لحل فقدان العمولة الفعلي في
   الإنتاج.**
3. **`get_or_create_profile` داخل `register_commission`** (حل مشكلة
   نطاق `affiliate_id` من البند 5.2) — معتمَد.
4. **`get_user_by_code`** wrapper حول `repo.get_affiliate_by_code`،
   ترجع `AffiliateProfile` (بما يتسق مع القرار 1-3) — معتمَد.

## 9. تصميم الجدول الجديد المقترَح (لم يُنفَّذ بعد — بانتظار موافقة نهائية)

اسم مقترَح: `affiliate_action_commissions` (تمييزًا واضحًا عن
`affiliate_commissions` التجاري، ونفس نمط تسمية `affiliate_*` المتّبع
في باقي جداول الدومين). موديل مقترَح: `ActionCommission` في
`app/domains/affiliate/models.py`.

```python
class ActionCommission(Base):
    """عمولات الأحداث العابرة للدومينات (بلا Order تجاري) — Backlog #10"""
    __tablename__ = "affiliate_action_commissions"
    __table_args__ = (
        Index("ix_affiliate_action_commissions_tenant_id", "tenant_id"),
        Index("ix_affiliate_action_commissions_affiliate_profile_id", "affiliate_profile_id"),
        Index("ix_affiliate_action_commissions_user_id", "user_id"),
        Index("ix_affiliate_action_commissions_status", "status"),
        Index("ix_affiliate_action_commissions_entity_type", "entity_type"),
        Index("ix_affiliate_action_commissions_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    affiliate_profile_id = Column(Integer, ForeignKey("affiliate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT", nullable=False)
    description = Column(String(255), nullable=False)

    entity_type = Column(String(50), nullable=False)   # اسم الدومين المصدر: "ZAMAKANA"/"TRANSPORT"/"INSURANCE"/...
    action_type = Column(String(50), nullable=True)     # الحدث الدقيق (اختياري): "NODE_CREATED"/"SALARY_PAID"/...

    status = Column(String(20), default="PENDING", nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**ملاحظات على الاختيارات فوق (لأسبابها):**
- **`tenant_id`**: مش من الحقول الأربعة/الستة اللي ذكرتها صراحة، لكن
  **إضافة إجبارية** — كل جدول تاني في المشروع (بما فيها `affiliate_commissions`
  نفسها) عنده `tenant_id NOT NULL` كقاعدة عزل صارمة بلا استثناء واحد
  في الـschema بالكامل؛ تركه هيكون ثغرة عزل تينانتات جديدة.
- **`affiliate_profile_id`** (مش `affiliate_id`): سمّيته بالاسم الصريح
  الكامل تفاديًا لتكرار نفس الالتباس الموثَّق في بند 5.2 (`affiliate_id`
  كان بيتلخبط بين `users.id`/`affiliate_profiles.id`) — هنا واضح من
  الاسم نفسه إنه FK على `affiliate_profiles.id` فقط، بعد resolve عبر
  `get_or_create_profile`.
- **`entity_type`**: استخدمته لاسم **الدومين المصدر** (zamakana/transport/...)
  مش لنوع العملية، لأن هذا يطابق استخدام `entity_type` في الجداول التانية
  بالدومين (`ReferralTree.entity_type`, `Commission.entity_type`) كـ"مصدر/سياق
  السجل" — وأضفت `action_type` منفصل اختياري للحدث الدقيق (`NODE_CREATED`
  إلخ) بدل خلط الاثنين في عمود واحد.
- **`currency`**: أضفتها (غير مطلوبة صراحة) لأن كل قيمة مالية تانية في
  الدومين (`Commission.currency`, `AffiliateProfile` أرصدة) عندها هذا
  العمود دايمًا بنفس الـdefault `"MR_USDT"` — حفاظًا على الاتساق.
- **`paid_at`/`paid_tx_hash`**: أضفتهم رغم إنهم مش في قائمتك الصريحة —
  **سؤال حقيقي محتاج قرارك، مش افتراض مني**، موضّح في القسم التالي.

## 10. سؤال تصميمي إضافي محتاج قرارك قبل أي migration: هل السجلات دي هتتكامل مع دورة حياة العمولة العادية؟

اكتشاف أثناء تصميم الجدول: كل الدوال اللي بتتعامل مع **رصيد/سحب/إحصائيات**
العمولات حاليًا بتقرأ **فقط** من جدول `affiliate_commissions` (التجاري):
`get_affiliate_stats` (`total_pending`)، `withdraw_commissions`
(`get_pending_commissions` لحساب المتاح للسحب وخصمه)، `release_commissions`،
`get_commissions_by_user`. **لو السجلات الجديدة عاشت في جدول منفصل
تمامًا بلا أي لمسة على هذه الدوال، فالعمولة هتتسجَّل فعليًا (تختفي
مشكلة الفقدان الصامت) لكنها هتفضل غير مرئية تمامًا لصاحبها** — مش هتظهر
في رصيده المعلَّق، ومش هيقدر يسحبها. يعني نوع تاني من "الفقدان الفعّال"
(مش صامت في الكود، لكن صامت في تجربة المستخدم).

**الخيارات (محتاجة قرارك، مش هفترض):**
- **(أ) أقلّ تدخل الآن**: الجدول الجديد تخزين فقط في هذه الجلسة (سجل
  تدقيق/تتبع حي يثبت إن العمولة اتسجَّلت، بدل الضياع الكامل الحالي)،
  وربطه بدورة الرصيد/السحب يُفتح كبند Backlog منفصل صراحة (يحتاج تصميم
  استعلام موحَّد UNION عبر الجدولين أو دمج، خارج نطاق هذه الجلسة).
- **(ب) تكامل كامل الآن**: تعديل `get_affiliate_stats`/`withdraw_commissions`/
  `release_commissions`/`get_commissions_by_user` ليشملوا الجدول الجديد
  أيضًا (تعديل أوسع من مجرد إضافة `register_commission`، لكنه يحل
  المشكلة فعليًا من منظور المستخدم النهائي مش بس من منظور "الكود بيتسجل").
- **(ج) حل وسط**: `paid_at`/`paid_tx_hash`/`status` تُبقى في الجدول
  الجديد (استعدادًا لتكامل لاحق) لكن بلا لمس فعلي على دوال الرصيد/السحب
  الآن — فقط توثيق صريح في `PROGRESS_LOG.md` إن هذا بند Backlog تالٍ
  مطلوب لإكمال الصورة.

**بانتظار قرارك على هذا السؤال + تأكيد نهائي على تصميم الجدول (البند 9)
قبل أي migration أو كود.**

---

## 11. قرار المستخدم النهائي [بعد عرض تصميم الجدول]

- **تصميم الجدول (قسم 9) معتمَد بالكامل بدون تعديل.**
- **سؤال التكامل (قسم 10): الخيار (ج) معتمَد** — الأعمدة
  `paid_at`/`paid_tx_hash`/`status` تُبقى في الجدول استعدادًا لتكامل
  لاحق، لكن **صفر لمس** على `get_affiliate_stats`/`withdraw_commissions`/
  `release_commissions`/`get_commissions_by_user` في هذه الجلسة. سبب
  صريح من المستخدم: تعديل `withdraw_commissions`/`release_commissions`
  يلمس منطق سحب فلوس حقيقي، ويستاهل جلسة مخصَّصة بتصميم واختبار
  مستقل. **يجب توثيق بند Backlog جديد صريح عند الإغلاق**
  (`affiliate-action-commissions-not-integrated-with-balance`): العمولات
  الجديدة تُسجَّل فعليًا الآن لكنها غير مرئية في رصيد المستخدم المعلَّق
  ولا قابلة للسحب — أولوية عالية (فجوة تجربة مستخدم حقيقية حتى لو
  الفقدان الصامت في الكود اتحل).
- **الأمر بالتنفيذ الكامل الآن**: migration → `register_commission` +
  `get_user_by_code` → تحقق حي مباشر (تجاوز الـwrapper المكسور) → توقف
  وعرض النتائج قبل regression test/commit.

## 12. التنفيذ

### 12.1 Migration

`migrations/versions/028_create_affiliate_action_commissions.py` —
`down_revision = '027_create_identity_tenant_invitations'` (الرأس
الحالي المؤكَّد من `alembic_version` في قاعدة `eppne_v2` الحيّة قبل
التنفيذ). يطابق تصميم القسم 9 حرفيًا (تأكيد: مشروع `eppne-backend`
يستخدم Alembic حقيقي — `migrations/versions/` فيه 27 ملف سابق، `alembic.ini`
يشاور على `script_location = migrations` وليس المجلد الافتراضي
`alembic/`، اكتُشف بعد بحث أولي فاشل في المسار الافتراضي).

**تم تطبيقه فعليًا** على قاعدة `eppne_v2` (Docker `eppne_db`، منفذ
5435) عبر `venv/Scripts/alembic.exe upgrade head`
(`PYTHONIOENCODING=utf-8` مطلوب لتفادي `UnicodeEncodeError` من رسائل
emoji في `migrations/env.py` على Windows console — مشكلة بيئة محلية
بحتة، بلا علاقة بالمنطق). **تحقق حي بـ`\d affiliate_action_commissions`
مباشر على الـDB** أثبت تطابق كل عمود/index/FK مع التصميم المعتمَد
بالضبط.

### 12.2 الموديل والـRepository

- `ActionCommission` أُضيف لـ`app/domains/affiliate/models.py` (بعد
  `Commission`, قبل `CommissionTier`) — نفس تصميم القسم 9 حرفيًا، مع
  تعليق مرجعي لهذا التقرير.
- `AffiliateRepository.create_action_commission(tenant_id, **kwargs)`
  أُضيفت لـ`repository.py` — نفس نمط `create_commission` الموجود
  بالضبط (إضافة صرفة، صفر تعديل على أي ميثود موجودة).

### 12.3 `AffiliateService.register_commission` + `get_user_by_code`

أُضيفا في قسم جديد "11. عمولات الأحداث العابرة للدومينات" في نهاية
الكلاس (`service.py`):

```python
async def register_commission(
    self, affiliate_id: int, user_id: int, amount: Decimal,
    description: str, status: str = "PENDING",
    entity_type: str = "CROSS_DOMAIN", action_type: Optional[str] = None,
) -> ActionCommission:
    profile = await self.get_or_create_profile(affiliate_id)
    return await self.repo.create_action_commission(
        tenant_id=self.tenant_id,
        affiliate_profile_id=cast(int, profile.id),
        user_id=user_id, amount=amount, description=description,
        status=status, entity_type=entity_type, action_type=action_type,
    )

async def get_user_by_code(self, referral_code: str) -> Optional[AffiliateProfile]:
    return await self.repo.get_affiliate_by_code(referral_code, self.tenant_id)
```

**قرارات تصميم منفَّذة كما اعتُمدت:**
- `get_or_create_profile(affiliate_id)` داخل `register_commission` يحل
  التباس نطاق `users.id`/`affiliate_profiles.id` (قسم 5.2) — الـ12
  موضع كلهم يمررون `affiliate_id=user.referred_by` (قيمة `users.id`)،
  فيتحوَّل تلقائيًا لملف Affiliate الصحيح (يُنشأ لو مش موجود).
- `entity_type: str = "CROSS_DOMAIN"` **قيمة افتراضية**، لأن الـ12
  موضع الحاليين في الدومينات **لا يمررون `entity_type` إطلاقًا** (خارج
  نطاق هذه الجلسة تعديل الـ12 ملف لإضافته — قرار نطاق "صفر لمس على
  الاستدعاءات" من قسم 8). **التمييز بين الدومينات لسه متاح نصيًا فقط
  عبر عمود `description`** (كل الاستدعاءات بتبني النص كـ
  `f"Affiliate commission for {action_type}"`) — قيد معروف، موثَّق هنا
  صراحة بدل إخفائه.

### 12.4 إصلاح ضروري ملازم (مش "اكتشاف جانبي منفصل"، جزء لا يتجزأ من تنفيذ `get_user_by_code` المعتمَد)

`digital_twin/service.py:82`: كان `referrer_id = referrer.id`. بما إن
`get_user_by_code` المعتمَدة ترجع `AffiliateProfile` (قرار المستخدم
صراحة في قسم 8 بند 4)، و`register_commission.affiliate_id` مصمَّم
ليستقبل **user_id** (قرار قسم 8 بند 3، نفس نمط الـ11 دومين الباقيين)
— لو تُرك `referrer.id` (وهو `AffiliateProfile.id`) هيتمرَّر غلط
كـ`user_id` لـ`get_or_create_profile` جوه `register_commission`،
معناها بالضبط نفس باج خلط النطاقين (5.2) اللي الجلسة دي بالذات
مصمَّمة تحله. **هذا مش باج مستقل جديد — هو نتيجة مباشرة وحتمية لتنفيذ
التصميم المعتمَد لـ`get_user_by_code` نفسها**، فتم تصحيحه كجزء من
نفس التغيير (`referrer.id` → `referrer.user_id`)، مش كاكتشاف جانبي
منفصل يحتاج توقف/موافقة إضافية.

## 13. التحقق الحي

**تنفيذ فعلي مباشر لـ`register_commission`/`get_user_by_code`**
(بتجاوز الـwrapper `_register_affiliate_commission` المكسور في كل
دومين، بقرار نطاق صريح من قسم 8) — عبر سكربت مؤقَّت
(`eppne-backend/scratch_verify_p10.py`، حُذف بعد الانتهاء) يستخدم
`AsyncSessionLocal`/`AffiliateService` الحقيقيين على قاعدة `eppne_v2`
الحيّة (نفس الـDB اللي الـAPI بيشتغل عليها، Docker `eppne_db`).

**بيانات throwaway**: مستخدمان جدد (`id=315` مُحيل، `id=316` منفِّذ
الفعل)، `tenant_id=1`.

**3 سيناريوهات، تمثيلية للـ12 موضع الفعليين** (نفس التوقيع بالضبط في
كل الـ12، يختلف بس القيم — راجع قسم 4 — فعينة تمثيلية كافية بدل تكرار
حرفي 12 مرة):
1. **نمط نسبة مئوية** (زي `transport` 2%): `amount=2.00`,
   `entity_type="TRANSPORT"`.
2. **نمط مبلغ ثابت** (زي `tenders_auctions` 25.00 ثابت):
   `amount=25.00`, `entity_type="TENDERS_AUCTIONS"`.
3. **مسار `get_user_by_code`/`affiliate_code`** (النمط الوحيد الخاص
   بـ`digital_twin`، غير موجود في الـ11 دومين الباقيين): `get_or_create_profile`
   → استخراج `referral_code` → `get_user_by_code(code)` → التأكد
   `looked_up.user_id == REFERRER_USER_ID` و`looked_up.id == profile.id`
   → تمرير `looked_up.user_id` (مطابقة تمامًا لتصحيح `digital_twin.py`
   في 12.4) → `register_commission`.

**نتائج التنفيذ داخل العملية (in-process):** الثلاثة نجحوا، `assert`
صريح إن الثلاثة يشيرون لنفس `affiliate_profile_id` (يثبت
`get_or_create_profile` بيعيد استخدام نفس البروفايل، مش بينشئ تكرار
مع كل نداء).

**تحقق مستقل حقيقي (مش بس صفر استثناء)** — `SELECT` من جلسة `psql`
منفصلة تمامًا عن جلسة الكود:

```
 id | tenant_id | affiliate_profile_id | user_id |   amount    | currency |   entity_type    |   action_type    | status
----+-----------+----------------------+---------+-------------+----------+------------------+------------------+---------
  1 |         1 |                    3 |     316 |  2.00000000 | MR_USDT  | TRANSPORT        | RIDE_COMPLETED   | PENDING
  2 |         1 |                    3 |     316 | 25.00000000 | MR_USDT  | TENDERS_AUCTIONS | AUCTION_WON      | PENDING
  3 |         1 |                    3 |     316 |  5.00000000 | MR_USDT  | DIGITAL_TWIN     | TWIN_INTERACTION | PENDING
```

+ `SELECT` مستقل على `affiliate_profiles WHERE user_id = 315` أثبت
**صف واحد بالضبط** (`id=3`, `referral_code='EPPNE-31'`) — يؤكد عدم
تكرار البروفايل حيًا (مش بس افتراض من الكود).

**تنظيف كامل بعد التحقق**: حذف الثلاثة سجلات + البروفايل + المستخدمين
الاثنين، وتأكيد `SELECT` نهائي `count = 0` على الثلاثة. صفر أثر متبقٍ.
حذف السكربت المؤقت.

**تنبيه صريح يُكرَّر عمدًا (نفس تنبيه قسم 8):** هذا التحقق أثبت أن
`register_commission`/`get_user_by_code` **أنفسهم** يعملون بشكل صحيح
ومعزول. **لم يُختبَر ولم يُصلَح** استدعاء الـwrapper الفعلي
(`_register_affiliate_commission`) من داخل أي من الـ12 دومين نفسها —
دول لسه هيفشلوا صامتين بسبب #1/#8/5.3 (خارج النطاق، قسم 5.4/8) قبل
ما يوصلوا حتى لـ`register_commission`. **الإصلاح ده ضروري لكنه غير
كافٍ لوحده لحل فقدان العمولة الفعلي في الإنتاج — سيُوثَّق بوضوح في
`PROGRESS_LOG.md` عند الإغلاق.**

## 14. الحالة الآن

✅ Migration مُطبَّقة وحيّة على `eppne_v2`.
✅ `register_commission`/`get_user_by_code` مبنيّتين ومتحقَّق منهما حيًا
(معزولتين عن الـwrapper المكسور، بقرار نطاق صريح).
✅ إصلاح ضروري واحد ملازم (`digital_twin.py:82`).
⏸️ **متوقف الآن** بانتظار مراجعتك لنتائج هذا القسم — قبل كتابة
`tests/test_affiliate_service_missing_methods.py` + README + تحديث
`PROGRESS_LOG.md` + الـcommit النهائي (بالضبط زي ما طلبت).
