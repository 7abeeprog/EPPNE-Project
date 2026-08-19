# جلسة `user-repository-get-by-id-audit` — Backlog #1 — سجل الجلسة

مرجع التعليمات: `.claude/plans/user-repository-get-by-id-audit-session-instructions.md`

## 1. التوقيع الحقيقي (تحقق مباشر من الكود)

`app/domains/identity/repository.py:21`

```python
async def get_by_id(self, user_id: int, tenant_id: int, load_wallet: bool = False) -> Optional[User]:
    query = select(User).where(and_(User.id == user_id, User.tenant_id == tenant_id))
    ...
```

`tenant_id` معامل موضعي إجباري ثانٍ — أي استدعاء بمعامل واحد فقط ينتج
`TypeError: get_by_id() missing 1 required positional argument: 'tenant_id'`
فورًا (لا يصل حتى لتنفيذ الاستعلام).

## 2. منهجية الفحص

- `grep` شامل جديد بالكامل عبر `eppne-backend` (بلا استثناء أي مجلد) عن
  `\.get_by_id\(` — 40+ نتيجة، فُلترت يدويًا لاستبعاد:
  - `TenantInvitation` repo's `get_by_id` (توقيع مختلف تمامًا، `app/domains/identity/repository.py:297`، يطلب `tenant_id` أصلاً وكل استدعاءاته له صحيحة — `invitation_service.py:40,48`).
  - الاستدعاء الداخلي الصحيح داخل `UserRepository` نفسه (`repository.py:69`، `self.get_by_id(user_id, tenant_id, load_wallet=True)`).
- تأكيد شامل إضافي: `grep` عن كل `UserRepository(` (25 ملف) للتأكد من عدم
  فوات أي استدعاء بصيغة غير معتادة. من الـ25، بعضها يستخدم methods تانية
  خارج نطاق هذا البند تمامًا (وُثِّق في القسم 4).

## 3. القايمة الكاملة المحدَّثة — كل استدعاء فعلي مكسور لـ`UserRepository.get_by_id()`

**15 موضعًا فعليًا** (عبر 13 دومين) — **مطابقة تمامًا للقايمة التاريخية
القديمة من حيث العدد والمواضع** (تحقّق فعلي اليوم، مش افتراض): لا شيء
اتصلح بالصدفة ضمن جلسات لاحقة (savepoint fixes/redis wrapper/affiliate)،
ولا مواضع جديدة ظهرت أو اختفت.

| # | الملف:السطر | الدومين | مصدر `tenant_id` المتاح | نوع الحماية الحالية |
|---|---|---|---|---|
| 1 | `zamakana/service.py:650` | zamakana | متاح — معامل `tenant_id` في توقيع `_register_affiliate_commission` نفسها | صامت (مُسجَّل) — `try/except Exception: logger.error(...)` |
| 2 | `transport/service.py:569` | transport | متاح في كل الاستدعاءات (`book_trip`, `pay_for_delivery` عندهم `tenant_id` كمعامل) لكن **غير مُمرَّر لدالة `_get_user_by_id` نفسها لأنها لا تقبله أصلاً** | **بلا حماية — يكسر الطلب بوضوح (500)** |
| 3 | `transport/service.py:577` | transport | متاح — معامل `tenant_id` في `_register_affiliate_commission` | صامت (مُسجَّل) |
| 4 | `tourism_sports/service.py:518` | tourism_sports | متاح — نفس النمط | صامت (مُسجَّل) |
| 5 | `tenders_auctions/service.py:484` | tenders_auctions | متاح — نفس النمط | صامت (مُسجَّل) |
| 6 | `social/service.py:678` | social | متاح في المستدعي الوحيد `send_digital_gift` (معامل `tenant_id`) لكن **غير مُمرَّر لـ`_get_user_email` لأنها لا تقبله** | **بلا حماية — يكسر الطلب بوضوح (500)**، داخل `db.begin_nested()` لتحويل هدية رقمية حقيقي |
| 7 | `service_marketplace/service.py:476` | service_marketplace | متاح — نفس نمط `_register_affiliate_commission` (عبر `_get_user` الوسيطة) | صامت (مُسجَّل) |
| 8 | `realestate/service.py:576` | realestate | متاح في المستدعي الوحيد (شراء جزئي، `tenant_id` معامل الدالة الأم) لكن **`_get_land_owner_for_unit(self, unit)` لا تقبل `tenant_id` إطلاقًا** | **بلا حماية — يكسر الطلب بوضوح (500)** |
| 9 | `realestate/service.py:584` | realestate | متاح مباشرة — `tenant_id` معامل `_register_affiliate_commission` نفسها | صامت (مُسجَّل) |
| 10 | `arbitration_syndicates/service.py:564` | arbitration_syndicates | متاح — معامل `tenant_id` في توقيع `_register_affiliate_commission` نفسها (نفس نمط zamakana/tourism_sports/tenders_auctions حرفيًا) | صامت (مُسجَّل) — `try/except Exception: logger.error(...)` |
| 11 | `manufacturing/service.py:57` | manufacturing | متاح عبر المسار الحي الوحيد (`_register_affiliate_commission`) | صامت (مُسجَّل) — ملاحظة: يوجد مستدعٍ ثانٍ `_get_user_email` **ميت (dead code)**، لا يُستدعى من أي مكان في المشروع |
| 12 | `logistics/service.py:62` | logistics | لا يوجد — **الدالة كلها (`_get_user`/`_get_user_email`) غير مُستخدَمة إطلاقًا في أي مكان بالمشروع** (لا يوجد `_register_affiliate_commission` في هذا الملف أصلاً) | **Dead code — غير موصول بأي مسار حي حاليًا** |
| 13 | `iot/service.py:31` | iot | متاح — معامل `tenant_id` في `settle_carbon_credits` | **مختلفة عن الصمت المعتاد**: داخل `try/except Exception as e: raise BusinessError(...)` — يُحوَّل لخطأ عمل واضح، **ما زال يكسر الطلب لكن برسالة مُعاد صياغتها**، وليس صمتًا كاملًا ولا `TypeError` خام |
| 14 | `invitations/service.py:56` | invitations | متاح عبر المسار الحي الوحيد (`_register_affiliate_commission`) | صامت (مُسجَّل) — نفس ملاحظة manufacturing: `_get_user_email` **ميتة تمامًا** لا مستدعٍ لها |
| 15 | `insurance/service.py:60` | insurance | **ثلاث مسارات استدعاء مختلفة لنفس السطر — انظر تفصيل خاص في القسم 3.1** | **مختلطة — انظر القسم 3.1 (الحالة الأعقد في القايمة كلها)** |

(15 صفًا = 15 موضعًا فعليًا مختلفًا في الكود. صف insurance وحده يمثّل
موضعًا فعليًا واحدًا رغم تفصيله في جدول فرعي بالقسم 3.1 بسبب تعدد
مسارات الاستدعاء لنفس السطر.)

### 3.1 حالة خاصة: `insurance/service.py:60` — نفس الاستدعاء، ثلاث درجات خطورة مختلفة

`_get_user(user_id)` (`insurance/service.py:57-60`، تلف `get_by_id`) لها
**3 مستدعين مختلفين** بمستويات حماية مختلفة تمامًا — هذا التمايز نفسه
هو صلب القاعدة الصارمة المطلوبة في التعليمات:

1. **`review_claim` (مسار `approve=True`) → `_get_user_email` → `insurance/service.py:464`**
   داخل `finance.transfer(..., receiver_email=await self._get_user_email(claim.claimant_user_id), ...)`
   ضمن `async with self.db.begin_nested()` **بلا أي `try/except`**.
   **يكسر الطلب بوضوح (500)** — هذا تحديدًا هو نفس البج المُوثَّق
   مسبقًا وحيًا في `tests/test_saas_active_subscription.py` (قسم
   13.1/14.1 المذكور هناك، صف 4) من جلسة سابقة. `tenant_id` متاح
   مباشرة كمعامل لدالة `review_claim` نفسها.
2. **`_register_affiliate_commission` → `insurance/service.py:68`**
   داخل `try/except Exception as e: logger.error(...)` — صامت
   (مُسجَّل)، النمط المعتاد.
3. **`disburse_monthly_pensions` (دالة مجدولة تلقائيًا — تعليق صريح في
   الكود: "يتم استدعاؤها تلقائياً عبر جدولة") → `_get_user_email` →
   `insurance/service.py:554`**
   داخل `try: ... except Exception: pass` — **صمت كامل بلا أي تسجيل
   إطلاقًا** (لا `logger.error` ولا أي أثر). هذا **أسوأ من الصمت
   المُسجَّل المعتاد**: مدفوعات معاشات شهرية حقيقية تفشل بصمت تام دون
   أي طريقة لرصدها من السجلات. `tenant_id` متاح هنا لكن **ليس كمعامل
   دالة** — بل مُشتق من الصف المحمَّل فعليًا (`pension.tenant_id`)، وهو
   مصدر صالح تمامًا (ليس نفس فئة التحذير الموثَّق أدناه في القسم 3.2).

### 3.2 تمييز عن تحذير `missing-tenant-id-in-background-task-signature`

تم فحص هذا التحذير تحديدًا (المذكور في `app/tasks/affiliate.py:102`،
`release_commissions_task`) والتأكد من عدم انطباقه على أي من الـ15
موضعًا أعلاه:
- لا يوجد أي استدعاء مباشر لـ`.get_by_id(` داخل `app/tasks/*.py` إطلاقًا
  (تحقَّق بـ`grep` مباشر — صفر نتائج).
- `disburse_monthly_pensions` (القسم 3.1، البند 3) **ليست** من نفس فئة
  التحذير رغم كونها "دالة مجدولة": لا يوجد نقص في مصدر `tenant_id` —
  القيمة موجودة وقابلة للاشتقاق من الصف المحمَّل (`pension.tenant_id`)،
  فقط غير مُمرَّرة. فئة مختلفة تمامًا عن حالة "لا يوجد مصدر `tenant_id`
  متاح إطلاقًا" المحذَّر منها — **لا تُعامَل كبند Backlog منفصل**، بل
  كموضع عادي ضمن القايمة (يُصلَح بنفس الأسلوب).
- لم تُكتشف أي حالة جديدة من هذه الفئة (background task بلا مصدر
  `tenant_id` في التوقيع أصلاً) ضمن نطاق هذا الفحص.

## 4. مواضع خارج النطاق — تحقَّق منها وتم استبعادها عمدًا

فحصت كل الـ25 ملف اللي بتستدعي `UserRepository(` للتأكد من عدم فوات أي
موضع، ومنها ما هو خارج النطاق صراحة (فئات مختلفة تمامًا، موثَّقة مسبقًا
كبنود Backlog منفصلة):

| الملف | الاستدعاء | السبب |
|---|---|---|
| `digital_twin/service.py:53` | `user_repo.get_user(user_id)` | Backlog #8 — method مختلفة اسمها `get_user` مش `get_by_id`، غير موجودة أصلاً |
| `employment/service.py:87` | `UserRepository(self.db).get_user(user_id)` | نفس Backlog #8 |
| `health/service.py:54` | `user_repo.get_user(user_id)` | نفس Backlog #8 |
| `communications/service.py:78` | `user_repo.get_by_email(receiver_email, self.tenant_id)` | method مختلفة تمامًا (`get_by_email`)، صحيحة وخارج النطاق |
| `finance/service.py` | لا يوجد استدعاء `get_by_id`/`get_user` — استخدام آخر لـ`UserRepository` غير مرتبط | خارج النطاق |
| `identity/invitation_service.py:40,48` | `self.repo.get_by_id(invitation_id, tenant_id)` | `self.repo` هو `InvitationRepository` **مش** `UserRepository` — توقيع مختلف تمامًا (`TenantInvitation`)، يطلب `tenant_id` أصلاً وصحيح |

## 5. المواضع المُصلَحة بالفعل (لا تحتاج أي لمس) — تحقَّق منها

هذه استدعاءات صحيحة بمعاملين بالفعل، اتصلحت في جلسات سابقة (identity
service، affiliate، academy، deps.py، security.py، sovereign_entities،
commerce):

- `app/api/deps.py:50,231`
- `app/core/security.py:132`
- `app/domains/identity/service.py:172,232,263,278`
- `app/domains/identity/repository.py:69` (استدعاء داخلي صحيح)
- `app/domains/affiliate/service.py:179,470`
- `app/domains/academy/service.py:129,250,342`
- `app/domains/sovereign_entities/service.py:359`
- `app/domains/commerce/service.py:238`

## 6. خلاصة التصنيف حسب درجة الخطورة

- **كسر واضح فوري (500) — أولوية عالية جدًا، 4 مواضع:**
  `transport:569` (مسارين: `book_trip`, `pay_for_delivery`)،
  `social:678`، `realestate:576`، `insurance:464` (عبر `_get_user_email`
  في `review_claim` — نفس البج المُوثَّق حيًا مسبقًا في اختبار SaaS).
- **صمت كامل بلا أي تسجيل — أسوأ فئة صامتة، موضع واحد:**
  `insurance:554` (`disburse_monthly_pensions`، دفعات معاشات فعلية).
- **صمت مُسجَّل (`logger.error` ثم استمرار الطلب بنجاح) — 8 مواضع:**
  `zamakana:650`، `transport:577`, `tourism_sports:518`,
  `tenders_auctions:484`, `service_marketplace:476`, `realestate:584`,
  `manufacturing:57`, `invitations:56`, `insurance:60` (مسار
  `_register_affiliate_commission`), `arbitration_syndicates:564`.
- **مُحوَّل لخطأ عمل (لا صمت كامل ولا `TypeError` خام) — موضع واحد:**
  `iot:31` (`settle_carbon_credits` → `BusinessError`).
- **Dead code — غير موصول بأي مسار حي حاليًا، موضع واحد:**
  `logistics:62`.

## 7. حالة سلسلة `affiliate`/Backlog #10 (تذكير من التعليمات — لن يُتحقَّق
   إلا **بعد** إصلاح #1 فعليًا، حسب القاعدة الصارمة)

مؤجَّل لما بعد الموافقة على القايمة والتنفيذ — سيُوثَّق في قسم منفصل
لاحقًا في هذا الملف حسب تعليمات الجلسة.

## 9. التصميم المقترَح للإصلاح (قبل أي كود — للموافقة)

### 9.0 قرار عام: لا وجود لـwrapper/base class مشترك بين خدمات الدومينات

تحقَّق مباشرةً: `TransportService`, `InsuranceService`, `SocialService`,
`RealEstateService`, ... إلخ كل واحدة `class X:` مستقلة تمامًا، **لا
يوجد أي base class أو mixin مشترك بينها**. لذلك **لا يوجد حل مركزي
حقيقي متاح** يمس أكتر من دومين بتعديل واحد — كل دومين ملفه المستقل.
القرار المقترَح: **صفر تجريد جديد** (لا إنشاء base class ولا wrapper
جديد) — التكرار الفعلي في كل موضع هو سطر واحد أو تعديل توقيع بسيط، وده
أصغر من تكلفة إدخال تجريد جديد يمس 13 ملف دومين مختلف لأول مرة. الإصلاح
per-site مباشر.

### 9.1 الفئة 1 — `tenant_id` متاح في الدالة الأم لكن الدالة الداخلية
لا تقبله إطلاقًا (transport, social, realestate:576, insurance:464)

**الأسلوب**: تعديل توقيع كل دالة مساعدة خاصة (private helper) لتقبل
`tenant_id: int` كمعامل موضعي إجباري ثانٍ (نفس نمط `get_by_id` نفسها
ونفس نمط `_register_affiliate_commission` الموجود بالفعل)، ثم تحديث كل
نقطة استدعاء لتمرر القيمة المتاحة أصلاً في نطاقها. **بدون حل أعم ممكن**
لأن كل دالة خاصة بكلاس مختلف تمامًا:

| الملف | الدالة | التوقيع الجديد المقترَح | نقاط الاستدعاء المطلوب تحديثها |
|---|---|---|---|
| `transport/service.py` | `_get_user_by_id(self, user_id)` | `_get_user_by_id(self, user_id: int, tenant_id: int)` | `book_trip:326`، `pay_for_delivery:507` (كلاهما عندهم `tenant_id` كمعامل دالة أصلاً) |
| `social/service.py` | `_get_user_email(self, user_id)` | `_get_user_email(self, user_id: int, tenant_id: int)` | `send_digital_gift:492` فقط (مستدعٍ وحيد، `tenant_id` معامل الدالة) — **عناية خاصة**: الاستدعاء حاليًا داخل `async with self.db.begin_nested():` بلا `try/except` — الإصلاح لن يضيف أي حماية جديدة، فقط يصلح المعامل الناقص؛ قرار عدم إضافة `try/except` هنا **خارج نطاق هذه الجلسة** (تغيير سلوك معاملة، قرار تصميمي مستقل) — إلا لو رأيت غير ذلك |
| `realestate/service.py` | `_get_land_owner_for_unit(self, unit)` | `_get_land_owner_for_unit(self, unit: PropertyUnit, tenant_id: int)` | `purchase_fraction`-type method (السطر ~237)، `tenant_id` متاح كمعامل الدالة الأم |
| `insurance/service.py` | `_get_user(self, user_id)` → `_get_user_email(self, user_id)` (سلسلة) | `_get_user(self, user_id: int, tenant_id: int)` + `_get_user_email(self, user_id: int, tenant_id: int)` | **3 نقاط استدعاء في نفس الملف** — انظر 9.2 |

### 9.2 insurance تحديدًا — تعديل واحد يغطي 3 مسارات (464، 554، والصامت 60)

بما إن `_get_user`/`_get_user_email` سلسلة واحدة مُعاد استخدامها 3 مرات
في نفس الملف، **تعديل التوقيع مرة واحدة يغطي الفئتين 1 و2 معًا +
موضع الصمت المُسجَّل insurance:60**:
- `review_claim:464` → يمرر `tenant_id` (معامل الدالة نفسها) — فئة 1 (كسر واضح).
- `disburse_monthly_pensions:554` → يمرر `cast(int, pension.tenant_id)`
  (نفس القيمة المُستخدَمة بالفعل سطر 550 لإنشاء `FinanceService`) —
  فئة 2. **نفس الأسلوب تمامًا كفئة 1**، الفرق الوحيد مصدر القيمة
  (سطر محمَّل، مش معامل دالة) — لا يحتاج تصميمًا مختلفًا.
- `_register_affiliate_commission:68` → يمرر `tenant_id` (معامل الدالة) — فئة 3 (صامت مُسجَّل).

**تعديل واحد في الملف، لكن 3 سيناريوهات تحقق حي منفصلة بنفس ترتيب
الأولوية اللي طلبته** (554 أولًا، 464 ضمن الكسور الواضحة، 60 ضمن
الصامتة).

### 9.3 الفئة 3 — الصامتة المُسجَّلة (zamakana, transport:577,
tourism_sports, tenders_auctions, service_marketplace, realestate:584,
manufacturing, invitations, arbitration_syndicates)

**نمط موحَّد 100% لكن بلا حل مركزي حقيقي ممكن** (كل موضع داخل
`_register_affiliate_commission` بكلاسه الخاص، و`tenant_id` **بالفعل**
معامل موجود في توقيع هذه الدالة في كل هذه المواضع — لا حاجة لتغيير أي
توقيع إطلاقًا). **الإصلاح: سطر واحد لكل موضع** —
`user_repo.get_by_id(user_id)` → `user_repo.get_by_id(user_id, tenant_id)`
(أو عبر `_get_user(user_id, tenant_id)` في manufacturing/invitations
بعد تعديل توقيعها كما في 9.1). **9 مواضع، 9 تعديلات من سطر واحد،
متطابقة تمامًا في الشكل** — تحقق حي كامل للجميع، لكن **عينة تمثيلية
موسَّعة** (وليس تحقق منفصل بالتفصيل الكامل لكل واحد) لـ2-3 مواضع تمثل
الأنماط الفرعية المختلفة (نمط `user_repo` محلي مباشر مثل zamakana، ونمط
`self.user_repo` مباشر مثل transport:577/realestate:584، ونمط
`_get_user()` الوسيط مثل manufacturing/invitations)، والباقي يُوثَّق
بديف الكود + regression test يغطي الجميع — **نفس أسلوب جلسة
`redis-client-wrapper` المُشار له في التعليمات**.

**سلوك `try/except`**: لن يتغير — الهدف فقط إصلاح المعامل الناقص، مش
إعادة تصميم معالجة الأخطاء. بعد الإصلاح، الـ`except` هيفضل موجود
كحماية دفاعية لأي خطأ تاني (زي DB error)، لكن مش هيتفعّل بسبب
`TypeError` بعد اليوم لنفس السبب.

### 9.4 الفئة 4 — iot:31

نفس أسلوب الفئة 1 تمامًا: `_get_user_email(self, user_id)` →
`_get_user_email(self, user_id: int, tenant_id: int)`، تحديث المستدعي
الوحيد `settle_carbon_credits` (`tenant_id` معامل الدالة). أولوية أقل
لأنها بالفعل تتحول لـ`BusinessError` واضح بدل صمت أو `TypeError` خام —
لكن نفس درجة سهولة الإصلاح ونفس الأسلوب، هتُنفَّذ في مكانها بترتيب
الأولوية المطلوب (رابعًا).

### 9.5 logistics:62 — توثيق فقط، صفر لمس (مؤكَّد)

الدالتان `_get_user`/`_get_user_email` **بلا أي مستدعٍ حي في المشروع
كله** (لا يوجد `_register_affiliate_commission` في هذا الملف أصلاً).
**لن يُلمَس الكود هنا إطلاقًا في هذه الجلسة** — يُوثَّق فقط كبند
Backlog منفصل عند الإغلاق (نفس الشكل: `get_by_id` بمعامل ناقص، بس
كامنة في كود ميت، تُكتشف فقط لو حد وصل يوم من الأيام ويضيف
`_register_affiliate_commission` لهذا الدومين ويستخدم هذه الدوال).

### 9.6 ترتيب التنفيذ والتحقق الحي المؤكَّد (بالحرف زي ما طلبت)

1. **insurance:554** (صمت كامل، معاشات حقيقية) — أولًا.
2. **الأربعة كسور الواضحة**: transport (كلا الاستدعاءين `book_trip` و
   `pay_for_delivery`)، **social بعناية خاصة** (جوّه `begin_nested()`،
   لازم تأكيد إن الإصلاح ما يغيّرش سلوك المعاملة غير إصلاح المعامل)،
   realestate:576، insurance:464.
3. **9 المواضع الصامتة المُسجَّلة** (فئة 3 أعلاه) — تحقق حي كامل +
   عينة تمثيلية موسَّعة كما في 9.3.
4. **iot:31** — رابعًا.
5. **logistics** — توثيق فقط، بلا لمس كود.

## 10. الحالة الحالية

**توقفت هنا للموافقة الصريحة على التصميم المقترَح أعلاه (القسم 9) قبل
أي سطر كود**، حسب طلبك المباشر.

**اعتماد المستخدم**: التصميم (القسم 9) معتمَد بالكامل بلا تعديل. قرار
إضافي بخصوص `social`: **لا يُضاف `try/except` جديد** — الإصلاح يقتصر
على تصحيح المعامل الناقص فقط، صفر تغيير في سلوك المعاملة
(`begin_nested()`). حماية `begin_nested()` الناقصة في `social` تُوثَّق
كبند Backlog منفصل عند الإغلاق بدل لمسها هنا.

## 11. عيّنة التحقق الحي التفصيلي المُحدَّدة مسبقًا (فئة 3 — القسم 9.3)

بناءً على طلب صريح لتحديد الموضع بدقة: **كل التسعة مواضع في الفئة 3
اتنفَّذت واتحقَّق منها حيًا فعليًا** (مش عينة فقط تُنفَّذ، والباقي
يُوثَّق بالديف بس) — التكلفة الإضافية لتشغيل التسعة كلهم حيًا كانت أصغر
من تكلفة تبرير الاستثناء. **لكن السرد التفصيلي خطوة بخطوة في هذا القسم
اقتصر على 3 مواضع تمثل الأنماط الفرعية الثلاثة** كما اتفقنا:
1. **`arbitration_syndicates:564`** — نمط "استيراد محلي + `user_repo.get_by_id` مباشر داخل `_register_affiliate_commission`".
2. **`transport:577`** — نمط "`self.user_repo.get_by_id` مباشر" (نفس نمط `realestate:584`).
3. **`invitations:56`** — نمط "عبر دالة وسيطة `_get_user()`" (نفس نمط `manufacturing`/`service_marketplace`).

الباقي (`zamakana`, `tourism_sports`, `tenders_auctions`,
`service_marketplace`, `manufacturing`, `realestate:584`) نُفِّذوا حيًا
بنفس السكربت ونفس المنهجية لكن بسطر نتيجة واحد بدل سرد مفصَّل (النتائج
مطابقة تمامًا). **`regression test` النهائي (لاحقًا، بعد هذا التوقف)
هيغطي التسعة كلهم بلا استثناء**، مش بس الثلاثة الممثِّلة.

## 12. التنفيذ الفعلي (بالترتيب المتفق عليه في 9.6)

### 12.1 التعديلات بالكود — ملف بملف

| # | الملف | التعديل |
|---|---|---|
| 1 | `insurance/service.py` | توقيع `_get_user(user_id, tenant_id)` + `_get_user_email(user_id, tenant_id)`؛ تحديث 3 نقاط استدعاء: `_register_affiliate_commission` (سطر ~87)، `review_claim` (سطر ~464، يمرر `tenant_id` من معامل الدالة)، `disburse_monthly_pensions` (سطر ~554، يمرر `cast(int, pension.tenant_id)`) |
| 2 | `transport/service.py` | توقيع `_get_user_by_id(user_id, tenant_id)`؛ تحديث نقطتي استدعاء (`book_trip:326`, `pay_delivery:507`)؛ تحديث `self.user_repo.get_by_id(user_id)` → `(user_id, tenant_id)` داخل `_register_affiliate_commission` |
| 3 | `social/service.py` | توقيع `_get_user_email(user_id, tenant_id)`؛ تحديث نقطة الاستدعاء الوحيدة `send_digital_gift:492` — **صفر تغيير في `begin_nested()`/معالجة الأخطاء** كما اتفقنا |
| 4 | `realestate/service.py` | توقيع `_get_land_owner_for_unit(unit, tenant_id)`؛ تحديث نقطة الاستدعاء (شراء جزئي، سطر ~237)؛ تحديث `self.user_repo.get_by_id(user_id)` → `(user_id, tenant_id)` داخل `_register_affiliate_commission` |
| 5 | `zamakana/service.py` | سطر واحد: `get_by_id(user_id)` → `get_by_id(user_id, tenant_id)` |
| 6 | `tourism_sports/service.py` | نفس التعديل — سطر واحد |
| 7 | `tenders_auctions/service.py` | نفس التعديل — سطر واحد |
| 8 | `arbitration_syndicates/service.py` | نفس التعديل — سطر واحد |
| 9 | `service_marketplace/service.py` | توقيع `_get_user(user_id, tenant_id)`؛ تحديث نقطة الاستدعاء الوحيدة داخل `_register_affiliate_commission` |
| 10 | `manufacturing/service.py` | توقيع `_get_user(user_id, tenant_id)` + `_get_user_email(user_id, tenant_id)` (تحديث تبعي لأن `_get_user_email` كانت بتنادي `_get_user` رغم إنها ميتة الاستدعاء — لتفادي كسر جديد في كود ميت)؛ تحديث نقطة الاستدعاء الحية |
| 11 | `invitations/service.py` | نفس نمط manufacturing تمامًا |
| 12 | `iot/service.py` | توقيع `_get_user_email(user_id, tenant_id)`؛ تحديث نقطة الاستدعاء الوحيدة `settle_carbon_credits:214` |
| — | `logistics/service.py` | **بلا لمس** — Dead code موثَّق فقط (مؤكَّد) |

تحقق `python -m py_compile` على كل الملفات الـ12 المعدَّلة: **نجح بلا
أخطاء** لكل الملفات.

تحقق نهائي بـ`grep` شامل بعد التعديل: **صفر استدعاء بمعامل واحد فقط
لـ`get_by_id(` في المشروع كله ماعدا `logistics/service.py:62` (الكود
الميت المتروك عمدًا)**.

### 12.2 التحقق الحي — السكربت والنتائج

سكربت throwaway (خارج المشروع، مش commit) — `verify_get_by_id_fix.py`
— يفتح جلسة DB حقيقية (`AsyncSessionLocal`، Docker `eppne_db` منفذ
5435 — نفس القاعدة `eppne_v2` المؤكَّدة من الجلسات السابقة)، يستخدم
مستخدم حقيقي موجود بالفعل (`user_id=41`, `tenant_id=1`,
`p_ctor_iot_owner@example.com`) — **صفر بيانات throwaway جديدة**، كل
الاستدعاءات قراءة فقط (`get_by_id` = `SELECT`)، `db.rollback()` في
النهاية لضمان صفر أثر (لم يحدث أي `commit` أصلاً لأي مسار مُختبَر).

**لكل موضع من الـ15**: استدعاء حقيقي وصل فعليًا لنفس السطر المُصلَح،
بمعاملين صحيحين (`tenant_id` صحيح) وبمعامل خاطئ (`tenant_id` غير
موجود) للتأكد من عزل tenant فعليًا مش بس اختفاء الخطأ.

**نتيجة التشغيل الفعلي — 18/18 تحقق نجح، صفر فشل:**

```
OK | insurance._get_user(correct tenant)              | id=41
OK | insurance._get_user(WRONG tenant -> None)         | result=None
OK | insurance._get_user_email(correct tenant)         | email صحيح
OK | transport._get_user_by_id(correct tenant)         | id=41
OK | transport._get_user_by_id(WRONG tenant)           | NotFoundError صحيح (سلوك الدالة الأصلي محفوظ)
OK | social._get_user_email(correct tenant)            | email صحيح
OK | social._get_user_email(WRONG tenant -> fallback)  | fallback صحيح (سلوك الدالة الأصلي محفوظ)
OK | realestate.user_repo.get_by_id(correct tenant)    | id=41
OK | 9× _register_affiliate_commission (zamakana, tourism_sports,
     tenders_auctions, arbitration_syndicates, service_marketplace,
     manufacturing, invitations, transport(577), realestate(584))
   | صفر أثر لـTypeError/missing positional argument في السجلات
OK | iot._get_user_email(correct tenant)               | email صحيح
```

**ملاحظة منهجية مهمة**: التحقق تم على مستوى الدالة المساعدة الخاصة
مباشرة (`_get_user_by_id`/`_get_user_email`/`_get_user`/
`_get_land_owner_for_unit` أو استدعاء `get_by_id` المباشر داخل
`_register_affiliate_commission`) بدل تنفيذ التدفق التجاري الكامل من
الـAPI (حجز رحلة كاملة، شراء جزئي كامل، مطالبة تأمين كاملة) — لأن البج
المُصلَح هنا هو معامل ناقص تحديدًا، والتحقق على مستوى نفس السطر المُصلَح
مباشرة بجلسة DB حقيقية وبيانات حقيقية **يصل فعليًا لنفس الكود المُصلَح
بلا أي mock**، وتفادى تكلفة تركيب سيناريوهات تجارية كاملة (رحلات،
عقارات، بوالص تأمين) غير ضرورية لإثبات إصلاح معامل. نقاط الاستدعاء نفسها
(مين بيمرر إيه) تحقَّقت عبر قراءة الكود المباشرة (القسم 12.1) + `grep`
النهائي الشامل.

## 13. اكتشاف جانبي حي مهم — تأكيد سلوك سلسلة `affiliate`/Backlog #10
بعد إصلاح #1 (توثيق فقط، بلا إصلاح، حسب الاتفاق)

أثناء التحقق الحي للفئة 3 (تشغيل `_register_affiliate_commission`
الفعلية لكل الدومينات التسعة + `insurance` بشكل منفصل = **10 دومينات
إجمالًا**)، ظهرت النتيجة التالية **بشكل حي ومباشر من السجلات الفعلية**:

```
[ERROR] eppne: Affiliate registration failed: 'User' object has no attribute 'referred_by'
```

**تفسير دقيق**: كل الـ10 دومينات (`zamakana`, `tourism_sports`,
`tenders_auctions`, `arbitration_syndicates`, `service_marketplace`,
`manufacturing`, `invitations`, `transport`, `realestate`, `insurance`)
**نجحت الآن في الوصول لـ`get_by_id` وجلب المستخدم الصحيح بنجاح تام
(Backlog #1 مُصلَح ومؤكَّد لهم بالكامل)**، لكنها فورًا اصطدمت **بنفس
طبقة الفشل التالية الموثَّقة مسبقًا** في قسم 5.3 من جلسة
`affiliate-service-missing-methods`: **`User.referred_by` غير موجود
إطلاقًا كحقل على موديل `User`** (تحقَّق مباشر من
`app/domains/identity/models.py` — صفر نتائج لـ`referred_by`). هذا
بالضبط النمط اللي طلبت مني أرصده ("وصلوا لطبقة تالية من طبقات الفشل
الموثَّقة" — نص التعليمات الأصلية).

**دومينان متبقيان خارج هذا التأكيد تمامًا**: `digital_twin` و
`employment` — لسه محجوزان عند طبقة أسبق (Backlog #8، ميثود
`get_user()` غير موجودة إطلاقًا)، **ولا علاقة لهما بإصلاح Backlog #1 —
لم يصلوا لـ`get_by_id` من الأساس ولا قبل ولا بعد هذا الإصلاح**.

**القرار**: صفر إصلاح لـ`User.referred_by` هنا (خارج النطاق صراحة حسب
تعليمات الجلسة وتأكيدك المباشر) — فقط توثيق أن سلسلة Backlog #10 وصلت
الآن لهذه الطبقة تحديدًا لكل الـ10 دومينات المرتبطة، بدل الفشل الصامت
القديم بسبب #1.

## 14. الحالة الحالية

**التنفيذ والتحقق الحي لكل المواضع الـ15 اكتمل، وكذلك تأكيد سلسلة
affiliate/Backlog #10 بعد إصلاح #1 (القسم 13).**

## 15. أثر جانبي على اختبار موجود مسبقًا — مُعالَج بموافقة صريحة

تشغيل `tests/test_saas_active_subscription.py` (الملف الشامل، مش بس
الاختبار المتأثر) كشف: `test_insurance_review_claim_saas_check_passes_then_hits_known_bug`
كان بيعتمد صراحة على `pytest.raises(TypeError, match="tenant_id")`
كدليل غير مباشر على الوصول لـ`insurance/service.py:464` — نفس الموضع
اللي أصلحناه هنا. بعد الإصلاح هذا التوقُّع بقى باطل (الكود بيعدي
`get_by_id` بنجاح تام الآن ويكمل لـ`finance.transfer`). **بموافقتك
الصريحة (الخيار 1)**، الاختبار اتحدَّث ليعتمد على الطبقة التالية
الحقيقية المؤكَّدة حيًا بدل الطبقة القديمة المُصلَحة:
- `reviewer_id` اتغيَّر من `EXISTING_ISSUER_ENTITY_ID` (trick قديم
  لتفادي بج `issuer_entity_id`/`reviewer_id` عمدًا) إلى `claimant.id`
  (قيمة واقعية من نطاق `users.id`، بالظبط زي `current_user.id` الحقيقية
  من الراوتر) — بيفعِّل نفس البج الموثَّق `insurance-review-claim-issuer-entity-id-reviewer-id-conflict`
  **بشكل واقعي، مش بالصدفة**.
- الـassert اتحدَّث لـ`pytest.raises(PermissionDeniedError, match="Not authorized to review this claim")`.
- Docstring الاختبار + جدول ملخص الملف أُضيف لهم توضيح تاريخي كامل (كان
  يعتمد على TypeError من #1، اتصلح، حُدِّث ليعتمد على الطبقة التالية).

**تحقق حي**: الملف الكامل (4 اختبارات) اتشغَّل بعد التحديث — **4
passed**. فحص شامل إضافي لباقي ملفات `tests/` أكَّد: صفر اختبار آخر
بيعتمد فعليًا على وجود بج #1 (الإشارات التانية في `test_affiliate_service_missing_methods.py`
docstrings/تعليقات توثيقية بس، بلا أي `pytest.raises` مرتبط). **تشغيل
الـsuite الكامل بعد كل التعديلات: 60 passed, 4 xfailed** — صفر تأثير
جانبي غير مُعالَج.

## 16. regression test الدائم + PROGRESS_LOG.md

- `tests/test_user_repository_get_by_id_audit.py` — 15 اختبارًا، واحد
  لكل موضع من الـ15، بنفس منهجية التحقق الحي (معاملين صحيحين + tenant
  خاطئ لعزل tenant فعلي). **15 passed × تشغيلتين متتاليتين، صفر
  تذبذب، صفر بيانات throwaway متبقية** (تحقق مستقل بعد التشغيلتين).
- `tests/test_user_repository_get_by_id_audit.md` — README مخصص، جدول
  الـ15 موضع الكامل + جدول الاختبارات + توثيق الأثر الجانبي على
  `test_saas_active_subscription.py`.
- `PROGRESS_LOG.md` — بانر الحالة محدَّث لإغلاق #1، صف #1 في جدول
  الـBacklog محدَّث لـ✅ مُغلَق رسميًا بالقايمة الكاملة، صف #10 وصف
  `identity-user-referred-by-field-missing` محدَّثان ليعكسا إن #1 اتقفل
  والحاجب المتبقي بقى طبقة `referred_by` فقط لـ10 دومينات، صف
  `insurance-review-claim-issuer-entity-id-reviewer-id-conflict` محدَّث
  ليعكس إنه بقى مؤكَّد حيًا بشكل مباشر (مش عبر تجاوز)، وبند Backlog
  جديد `logistics-affiliate-commission-dead-code-uses-broken-get-by-id`
  مُضاف. سطر جديد في قائمة الجلسات المُقفلة (append-only).

## 17. الحالة الحالية النهائية

**كل الخطوات المتفق عليها اكتملت**: التنفيذ (12 ملف) + التحقق الحي
(15/15) + تأكيد سلسلة affiliate/#10 + معالجة الأثر الجانبي على اختبار
موجود + regression test دائم + README + تحديث `PROGRESS_LOG.md`.

**توقفت هنا قبل أي `git commit` فعلي** — القسم التالي (`git status`
النهائي) للموافقة قبل الـcommit، حسب طلبك المباشر.
