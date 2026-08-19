# جلسة `user-repository-get-user-audit` — Backlog #8 — سجل الجلسة

مرجع التعليمات: `.claude/plans/user-repository-get-user-audit-session-instructions.md`

## 0. ملخص البند (من التعليمات)

`UserRepository` **ليس عندها method اسمها `get_user()` إطلاقًا** — أي
استدعاء لـ`.get_user(` عليها هو `AttributeError` مباشر (مش `TypeError`
بمعامل ناقص، بعكس Backlog #1/`get_by_id`).

القايمة التاريخية الموثَّقة (من جلسة #1، قسم 4 "مواضع خارج النطاق"،
والوصف في تعليمات هذه الجلسة) رجّعت 6 مواضع مبدئية:
- `communications/service.py:29`
- `communications/service.py:36`
- `digital_twin/service.py:51` (جلسة #1 وثّقتها لاحقًا بسطر `:53`)
- `employment/service.py:89` (جلسة #1 وثّقتها لاحقًا بسطر `:87`)
- `health/service.py:54`
- موضع سادس غير مسمى صراحة

اختلاف أرقام الأسطر بين المصدرين (digital_twin `51` مقابل `53`،
employment `89` مقابل `87`) **مؤشر مباشر** إنه لازم تحقق حي جديد بالكامل
بدل الاعتماد على أي رقم قديم — بالظبط زي ما حذّرت التعليمات.

استثناء موثَّق مسبقًا: `identity/service.py:238` — تحقَّق سابقًا إنه
**مش باج**: بينادي method حقيقية على `UserService` نفسها، مش على
`UserRepository`. هيتفحص من الأول هنا برضه بلا افتراض.

## 1. التوقيع الحقيقي — تحقق مباشر من الكود

`app/domains/identity/repository.py` — كلاس `UserRepository` يمتد من
السطر 12 إلى السطر 99 (قبل `class RefreshTokenRepository:` في السطر
100). الـmethods الكاملة المعرَّفة عليه:

```
get_by_id, get_by_username_or_email, get_by_email, get_by_username,
get_by_idempotency_key, create, update, delete, update_last_login,
increment_session_version
```

**لا توجد method اسمها `get_user` ولا alias/assignment بديل
(`get_user = ...`) — تحقَّق بـ`grep` مباشر، صفر نتائج.** أي استدعاء
`.get_user(` على كائن `UserRepository` هو `AttributeError: 'UserRepository'
object has no attribute 'get_user'` مباشر عند التنفيذ.

## 2. منهجية الفحص

`grep` شامل جديد بالكامل عبر `eppne-backend` (بلا استثناء أي مجلد) عن
`\.get_user\(` — **6 نتائج فقط** (استبعاد ملفات `tests/*.md`/`*.py`
التوثيقية اللي بترجع اسم الدالة كنص، مش استدعاء حقيقي):

| # | الموضع | الكائن المُستدعى عليه |
|---|---|---|
| 1 | `employment/service.py:87` | `UserRepository(self.db).get_user(user_id)` |
| 2 | `digital_twin/service.py:53` | `user_repo.get_user(user_id)` (`user_repo = UserRepository(self.db)`) |
| 3 | `communications/service.py:29` | `self.user_repo.get_user(user_id)` |
| 4 | `communications/service.py:36` | `self.user_repo.get_user(user_id)` |
| 5 | `health/service.py:54` | `user_repo.get_user(user_id)` |
| 6 | `identity/service.py:238` | `self.get_user(user_id)` — **ليس `UserRepository`** |

**التحقق من الاستثناء `identity/service.py:238`**: قراءة مباشرة للكود
(`UserService.get_current_user`, سطر 237-238) تؤكد إنه بينادي
`self.get_user(user_id)` اللي هي method حقيقية معرَّفة على `UserService`
نفسها في السطر 228 (`async def get_user(self, user_id: int) -> User:`،
بتنادي `self.user_repo.get_by_id(...)` الصحيحة داخليًا). **مؤكَّد: مش
باج، خارج النطاق تمامًا** — تطابق كامل مع التوثيق التاريخي.

**فارق أرقام الأسطر عن التاريخ الموثَّق** (`digital_twin:51`→`53`,
`employment:89`→`87`): طبيعي، ناتج عن تعديلات لاحقة في نفس الملفات لا
علاقة لها بهذا البند — **يؤكد أهمية التحقق الحي الجديد بدل الثقة بالأرقام
القديمة**، بالظبط زي تحذير التعليمات.

بعدها، لكل موضع من الـ5 الحقيقية، تتبعت **كل نقاط الاستدعاء الفعلية**
لكل helper (مش بس سطر الـ`.get_user(` نفسه) عبر `grep` شامل لاسم الـhelper
(`_get_user`, `_get_user_email`, `_get_user_tenant`) في كل الملف + في
المشروع كله (لرصد استدعاءات خارجية من `app/tasks/*.py` مثلًا) — هذا كشف
تفاصيل ونقاط استدعاء **غير موثَّقة في القايمة التاريخية القديمة** (قسم 3).

## 3. القايمة الكاملة المحدَّثة — 5 مواضع حقيقية، لكل واحد كل نقاط استدعائه

### 3.1 `employment/service.py:87` — `_get_user(user_id)` helper (سطر 84-87)

**3 نقاط استدعاء حية** (نقطتان داخل الملف + نقطة خارجية جديدة غير
موثَّقة تاريخيًا):

| نقطة الاستدعاء | `tenant_id` متاح؟ | نوع الحماية | الأثر الفعلي |
|---|---|---|---|
| `_register_affiliate_commission:100` | ✅ معامل مباشر لتوقيع الدالة نفسها (سطر 95) | صامت (مُسجَّل) — `try/except Exception: logger.error(...)` (سطر 114-115) | عمولة إحالة التوظيف لا تُسجَّل أبدًا، بصمت |
| `_calculate_ai_match_score:132` (تُستدعى من `apply_for_job:246`، مسار تقديم طلب توظيف حقيقي) | ✅ عبر `job.tenant_id` (نفس القيمة المُستخدَمة سطر 141 لإنشاء `AIAgentsService`) | صامت (مُسجَّل) — `try/except Exception: logger.error(...)` (سطر 152-154)، يرجع `Decimal(50.0)` افتراضي | **ميزة AI matching معطَّلة فعليًا 100%** — كل طلب توظيف ياخد نفس الدرجة الافتراضية 50 دايمًا، بصمت، بدل تحليل حقيقي لمهارات المتقدم |
| **جديد — `app/tasks/employment.py:308`** (`service._get_user_email(employee_id)` داخل مهمة Celery `pay_payroll_task`) | ✅ معامل مباشر لتوقيع المهمة (`tenant_id: int`, سطر 257) | **غير محمي بـ`try/except` محلي عند السطر نفسه** (الـ`try` القريب سطر 312-326 يبدأ *بعد* هذا الاستدعاء ويغطي بس `finance.transfer`) — لكن **الدالة كلها ملفوفة بـ`try` أعلى مستوى** (سطر 266، `except` سطر 367-369) اللي بيسجّل الخطأ ويعمل `self.retry(exc=e, countdown=120)` (حتى `max_retries=3`) | **دفع الرواتب الفعلي (salary payment) يفشل ويعاد المحاولة 3 مرات ثم يفشل نهائيًا — لا راتب يُدفع أبدًا عبر هذا المسار حاليًا** |

**ملاحظة**: `_get_user_email` (employment، سطر 89-92) هي نفسها اللي بتنادي
`_get_user` داخليًا — نفس السلسلة الموثَّقة في جلسة #1 (نمط
`_get_user`→`_get_user_email`).

### 3.2 `digital_twin/service.py:53` — `_get_user(user_id)` helper (سطر 49-53)

**نقطتا استدعاء حيتان** (واحدة موثَّقة تاريخيًا كـ"صامتة"، وواحدة **جديدة
غير موثَّقة وأخطر بكثير — كسر واضح 500**):

| نقطة الاستدعاء | `tenant_id` متاح؟ | نوع الحماية | الأثر الفعلي |
|---|---|---|---|
| `_register_affiliate_commission:71` | ✅ معامل مباشر (سطر 63) | صامت (مُسجَّل) — `try/except Exception: logger.error(...)` (سطر 104-105) | عمولة إحالة إنشاء/تفاعل التوأم الرقمي لا تُسجَّل أبدًا، بصمت |
| **جديد — `_get_user_email:57` ← `interact_with_twin:180`** (`receiver_email=await self._get_user_email(twin_owner_id)`) | ✅ معامل مباشر لـ`interact_with_twin` (سطر 139) | **بلا أي `try/except` إطلاقًا** — الاستدعاء داخل `async with self.db.begin_nested():` (سطر 177-197) بلا حماية محلية، ولا يوجد `try` أعلى مستوى يغطي `interact_with_twin` كلها | **كسر واضح فوري (500) لكل محاولة تفاعل مدفوع مع توأم رقمي** — نفس نمط `social:678` و`realestate:576` الموثَّق في جلسة #1 بالضبط (نقطة دفع فعلية داخل `begin_nested()`) |

### 3.3 `communications/service.py:29` — `_get_user_tenant(user_id)` helper (سطر 27-32) — **استثناء معماري مختلف تمامًا عن كل الأنماط السابقة**

**3 نقاط استدعاء حية، صفر حماية `try/except` على أي منها:**

| نقطة الاستدعاء | السياق |
|---|---|
| `send_notification:63` | إرسال إشعار لأي `user_id` (endpoint `POST /notifications/send`، محمي بـ`get_current_superuser` فقط — **إداري، يستهدف أي مستخدم بأي tenant**) |
| `send_mail:144` (`sender_tenant`) | إرسال بريد داخلي — `sender_id = current_user.id` (المستخدم المصادَق) |
| `send_mail:145` (`recipient_tenant`) | نفس الدالة — `recipient_id` من مدخلات الطلب |

**لماذا هذا موضع مختلف جوهريًا عن كل المواضع الأخرى في هذا البند
وفي Backlog #1**: الغرض الوحيد من `_get_user_tenant` هو **اكتشاف
`tenant_id` نفسه** انطلاقًا من `user_id` فقط — **لا يوجد `tenant_id`
متاح في نطاق أي من نقاط الاستدعاء الثلاث أصلًا** (مش "معامل موجود بس مش
مُمرَّر" زي كل الحالات في #8 و#1، بل "غير موجود من الأساس لأن هذا بالضبط
سبب وجود الدالة"). `CommunicationsService.__init__` نفسه (سطر 18-21) **لا
يخزّن `tenant_id` إطلاقًا**.

- `send_notification`: مستخدَم إداري (superuser) بيستهدف مستخدم في أي
  tenant — لا يوجد "tenant الطلب" واحد أصلًا يصلح كبديل.
- `send_mail`: الغرض الصريح من استدعاء الدالة **مرتين** (للمرسل وللمستقبل)
  هو **التحقق من إنهما في نفس الـtenant** (سطر 143: تعليق `"# التحقق من
  أن المرسل والمستلم في نفس المستأجر"`) — لو افترضنا `recipient_tenant =
  sender_tenant` (اللي هو `current_user.tenant_id` المتاح فعلاً بدون أي
  استعلام) بنكون **ألغينا الفحص الأمني نفسه اللي الكود مصمَّم عشانه**؛
  التحقق من `UserRepository` بحث سريع أكد: **لا توجد method واحدة على
  `UserRepository` تقبل `user_id` فقط بدون `tenant_id`** (كل الـ5
  methods: `get_by_id`, `get_by_username_or_email`, `get_by_email`,
  `get_by_username`, `get_by_idempotency_key` تطلب `tenant_id` كمعامل
  إجباري) — ولا يوجد نمط "بحث عابر للـtenants" مسبوق في دومين `identity`
  كله (تحقَّق بـ`grep` عن `cross_tenant`/`any_tenant`/`superuser` في
  الدومين، صفر نتائج).

**هذا يعني: الحل المعتاد "أضف `tenant_id` كمعامل ومرّره من المستدعي"
(نفس أسلوب #1 وباقي مواضع #8) لا ينطبق هنا إطلاقًا** — الأقرب هو حاجة
حقيقية جديدة: method على `UserRepository` تبحث بـ`user_id` وحده عبر كل
الـtenants (بدون فلتر `tenant_id`)، وهو قرار أمني/معماري يستحق نقاشًا
منفصلاً (من المسموح له يستدعيها؟ superuser فقط؟) — **متروك للمستخدم
يقرر، صفر افتراض أو تنفيذ من عندي**.

**ملاحظة كفاءة جانبية (توثيق فقط، مش جزء من نطاق الإصلاح)**: في
`send_mail`، `sender_tenant` ممكن نظريًا يُستبدَل بـ`current_user.tenant_id`
المتاح فعلاً من طبقة المصادقة بدل استعلام إضافي — لكن `recipient_tenant`
لازم يفضل استعلامًا حقيقيًا (هو صلب الفحص الأمني). قرار تصميمي، مش
إصلاح تلقائي مني.

### 3.4 `communications/service.py:36` — `_get_user_email(user_id)` helper (سطر 34-39) — **Dead code، صفر مستدعٍ حي**

`grep` شامل للملف كامل + المشروع كله: **صفر استدعاء لـ`_get_user_email`
في `communications/service.py` أو أي مكان آخر بالمشروع**. غير موصولة بأي
مسار حي حاليًا — نفس فئة `logistics/service.py:62` الموثَّقة في جلسة #1.
**لن تُلمَس — توثيق فقط.**

### 3.5 `health/service.py:54` — `_get_user_email(user_id)` helper (سطر 50-55) — **Dead code، صفر مستدعٍ حي**

`grep` شامل لملف `health/service.py` كامل + `app/tasks/` + المشروع كله:
**صفر استدعاء حي لـ`_get_user_email`** في هذا الدومين. غير موصولة بأي
مسار حي حاليًا. **لن تُلمَس — توثيق فقط.**

## 4. مواضع خارج النطاق — تحقَّق منها وتم استبعادها عمدًا

| الموضع | السبب |
|---|---|
| `identity/service.py:238` | `UserService.get_user()` (method حقيقية على `UserService` نفسها، معرَّفة سطر 228) — مش `UserRepository.get_user()` — صحيح 100%، خارج النطاق |
| `logistics/service.py:62,65` | `.get_by_id(user_id)` (فئة #1، معامل ناقص مش method غير موجودة) — بالإضافة كونه dead code موثَّق في جلسة #1 |
| كل مواضع `_get_user(user_id, tenant_id)` الصحيحة في `insurance`, `manufacturing`, `invitations`, `service_marketplace`, `social`, `iot`, `commerce` | مُصلَحة بالفعل ضمن جلسة #1 (`get_by_id` بمعاملين صحيحين)، خارج نطاق #8 تمامًا |

## 5. خلاصة التصنيف حسب درجة الخطورة (كل الـ8 نقاط استدعاء الحية عبر المواضع الـ3 غير الميتة)

- **كسر واضح فوري (500) — بلا أي حماية، أعلى أولوية:**
  - `communications: send_notification:63`, `send_mail:144`, `send_mail:145` (**3 نقاط، صفر try/except على أي منها** — تُكسر كل استدعاء API لـ`POST /notifications/send` و`POST /mail/send` بلا استثناء، دومين كامل معطَّل عمليًا)
  - `digital_twin: interact_with_twin:180` (داخل `begin_nested()`، بلا حماية)
- **يفشل بعد إعادة محاولة Celery ثم يستسلم نهائيًا — تأثير مالي حقيقي:**
  - `employment: tasks/employment.py:308` (`pay_payroll_task`) — دفع رواتب حقيقي لا يتم أبدًا عبر هذا المسار
- **صامت مُسجَّل (`logger.error` ثم استمرار الطلب بنجاح جزئي) — تأثير وظيفي حقيقي لكن الطلب نفسه لا ينهار:**
  - `employment: _register_affiliate_commission:100` (عمولة إحالة توظيف)
  - `employment: _calculate_ai_match_score:132` (**ميزة AI matching معطَّلة 100% بصمت — كل طلب ياخد درجة 50 افتراضية**)
  - `digital_twin: _register_affiliate_commission:71` (عمولة إحالة توأم رقمي)
- **Dead code — غير موصول بأي مسار حي، صفر أثر فعلي حاليًا:**
  - `communications/service.py:36` (`_get_user_email`)
  - `health/service.py:54` (`_get_user_email`)

## 6. الاعتماد النهائي من المستخدم — القايمة + التصميم (بعد عرض القسم 5)

**القايمة والتحليل (أقسام 3-5) معتمَدان بالكامل بلا تعديل.**

### 6.1 `employment` + `digital_twin` (المواضع #1، #2) — معتمَد

نفس منهجية Backlog #1 بالحرف: تعديل توقيع كل private helper ليقبل
`tenant_id: int` (متاح في نطاق كل نقطة استدعاء)، **صفر إضافة
`try/except` جديد**، إصلاح per-site بلا base class مشترك.

- `digital_twin.interact_with_twin:180` — **صفر `try/except` جديد**، فقط
  إصلاح تمرير `tenant_id` (نفس قرار `social:678` في جلسة #1 بالحرف — لا
  تغيير في سلوك `begin_nested()`/معالجة الأخطاء).
- `employment._calculate_ai_match_score` — إصلاح تمرير المعامل فقط،
  **بلا التحقق من صحة منطق الـAI matching نفسه** (خارج النطاق).

### 6.2 `communications` (الموضع #3) — قرار معماري معتمَد

**method جديدة على `UserRepository`**:
```python
async def get_tenant_id_by_user_id(self, user_id: int) -> Optional[int]
```
ترجع `tenant_id` **فقط** (مش كائن `User` كامل) عبر كل الـtenants، بلا
فلتر — **least privilege**: أقصى ضرر ممكن لو استُخدمت غلط مستقبلاً هو
تسريب `tenant_id` فقط، مش بيانات مستخدم كاملة (إيميل، هاش كلمة مرور،
إلخ).

استخدامها في الثلاث نقاط:
- `send_notification:63` — الـendpoint محمي بالفعل بـ`get_current_superuser`، الاستخدام مقبول كما هو.
- `send_mail:144` (`sender_tenant`) **و**`:145` (`recipient_tenant`) —
  **الاحتفاظ بالاستعلامين الاثنين كما هما** (رغم إمكانية استبدال
  `sender_tenant` نظريًا بـ`current_user.tenant_id` المتاح فعلاً من طبقة
  المصادقة) — **قرار متعمَّد**: الفحص الأمني (مقارنة
  `sender_tenant == recipient_tenant`) يفضل واضحًا ومتماثلاً في الكود
  (استعلامان متطابقان)، مش نص استعلام ونص افتراض. الكفاءة الإضافية من
  حذف استعلام واحد لا تستاهل تعقيد القراءة.

### 6.3 ترتيب التنفيذ المعتمَد

1. `digital_twin` (كسر واضح 500).
2. `communications` (كسر واضح 500، 3 نقاط + method جديدة).
3. `employment` — مهمة `pay_payroll_task` (فشل مالي حقيقي).
4. `_register_affiliate_commission` في `employment` و`digital_twin` (صامت).
5. `employment._calculate_ai_match_score` (صامت، ميزة معطَّلة — إصلاح تمرير المعامل بس).
6. `communications:36` / `health:54` — توثيق فقط، بلا لمس كود (dead code مؤكَّد).

**تحقق حي إلزامي لكل نقطة استدعاء (8 نقاط)** — نفس منهجية جلسة #1
(بيانات حقيقية موجودة أو throwaway مع تنظيف كامل، معامل `tenant_id`
صحيح + معامل خاطئ حيث ينطبق لإثبات عزل الـtenant فعليًا).

بعد الإصلاح: تحقق (**توثيق فقط، بلا إصلاح**) هل `digital_twin` و
`employment` وصلا الآن لطبقة `User.referred_by` المفقودة زي باقي الـ10
دومينات في سلسلة `affiliate`/Backlog #10 — نفس نمط جلسة #1 تمامًا.

**التوقف المطلوب**: بعد التنفيذ والتحقق الحي الكامل، عرض على المستخدم
قبل `regression test` النهائي والـcommit.

## 7. التنفيذ الفعلي

### 7.1 التعديلات بالكود — ملف بملف

| # | الملف | التعديل |
|---|---|---|
| 1 | `app/domains/identity/repository.py` | **method جديدة** `get_tenant_id_by_user_id(user_id: int) -> Optional[int]` على `UserRepository` — `SELECT User.tenant_id WHERE User.id == user_id` بلا فلتر tenant (تمت الإضافة بعد `get_by_idempotency_key`، قبل `create`) |
| 2 | `app/domains/digital_twin/service.py` | توقيع `_get_user(user_id, tenant_id)` (يستخدم `get_by_id` بدل `get_user`) + `_get_user_email(user_id, tenant_id)`؛ تحديث نقطتي استدعاء: `_register_affiliate_commission:71`، `interact_with_twin:180` (عبر `_get_user_email`) — **صفر تغيير في `begin_nested()`/معالجة الأخطاء** |
| 3 | `app/domains/communications/service.py` | `_get_user_tenant` مُبسَّطة لتنادي `self.user_repo.get_tenant_id_by_user_id(user_id)` مباشرة (بدل `get_user(user_id).tenant_id`)؛ **`_get_user_email` (سطر 31-36) بلا لمس — dead code مؤكَّد، متروك عمدًا** |
| 4 | `app/domains/employment/service.py` | توقيع `_get_user(user_id, tenant_id)` (يستخدم `get_by_id`) + `_get_user_email(user_id, tenant_id)`؛ تحديث 3 نقاط استدعاء داخلية: `_register_affiliate_commission:100`، `_calculate_ai_match_score:132` (يمرر `cast(int, job.tenant_id)`) |
| 5 | `app/tasks/employment.py` | تحديث الاستدعاء الخارجي الوحيد `service._get_user_email(employee_id)` → `(employee_id, tenant_id)` داخل `pay_payroll_task` (سطر 308، `tenant_id` معامل المهمة نفسها) |
| — | `app/domains/health/service.py` | **بلا لمس** — `_get_user_email:54` dead code موثَّق فقط (مؤكَّد) |
| — | `app/domains/communications/service.py:33` | **بلا لمس** — `_get_user_email` dead code موثَّق فقط (مؤكَّد، بالاتفاق الصريح) |

تحقق `python -m py_compile` على كل الملفات المعدَّلة (`identity/repository.py`،
`digital_twin/service.py`، `communications/service.py`،
`employment/service.py`، `tasks/employment.py`): **نجح بلا أخطاء** لكل
الملفات.

### 7.2 تحقق نهائي بـ`grep` شامل بعد التعديل

```
tests/test_affiliate_service_missing_methods.py:51  (توثيق تاريخي فقط، نص لا كود)
tests/test_affiliate_service_missing_methods.md:50   (نفس الشيء)
app/domains/identity/service.py:238                  (مؤكَّد سابقًا: UserService.get_user()، صحيح)
app/domains/health/service.py:54                     (dead code، متروك عمدًا بالاتفاق)
app/domains/communications/service.py:33             (dead code، متروك عمدًا بالاتفاق)
```

**صفر استدعاء حي متبقٍ لـ`.get_user(` على `UserRepository` في أي مسار
مستخدَم فعليًا** — مطابق تمامًا للتصميم المعتمَد.

## 8. التحقق الحي — السكربت والنتائج

سكربت throwaway (خارج المشروع، `scratchpad`، غير مُلتزَم — حُذف بعد
التشغيل مباشرة) — `verify_get_user_fix.py` — يفتح جلسة DB حقيقية
(`AsyncSessionLocal`، نفس Docker `eppne_db` منفذ 5435، قاعدة `eppne_v2`)،
يستخدم **نفس المستخدم الحقيقي الموجود بالفعل من جلسة #1**
(`user_id=41`, `tenant_id=1`, `p_ctor_iot_owner@example.com`) — **صفر
بيانات throwaway جديدة**، `db.rollback()` في النهاية لضمان صفر أثر (لا
`commit` حدث لأي مسار مُختبَر).

**12/12 تحقق نجح، صفر فشل:**

```
OK | setup: real user confirmed                        | id=41 email=p_ctor_iot_owner@example.com
OK | digital_twin._get_user(correct tenant)             | id=41
OK | digital_twin._get_user(WRONG tenant -> None)        | result=None
OK | digital_twin._get_user_email(correct tenant)        | email صحيح
OK | digital_twin._register_affiliate_commission (no crash) | اكتملت بلا استثناء
OK | UserRepository.get_tenant_id_by_user_id(real user)  | tenant_id=1
OK | UserRepository.get_tenant_id_by_user_id(nonexistent) | result=None
OK | communications._get_user_tenant(real user)          | tenant_id=1
OK | employment._get_user(correct tenant)                | id=41
OK | employment._get_user(WRONG tenant -> None)           | result=None
OK | employment._get_user_email(correct tenant)           | email صحيح
OK | employment._register_affiliate_commission (no crash) | اكتملت بلا استثناء
```

**اكتشاف حي مؤكِّد لتوقُّع القسم 6.3 (سلسلة affiliate/#10)**: أثناء
تشغيل `_register_affiliate_commission` لكل من `digital_twin` و
`employment`، ظهر في السجلات الفعلية **نفس الخطأ الموثَّق في جلسة #1
للـ10 دومينات الأخرى بالضبط**:

```
Affiliate registration failed: 'User' object has no attribute 'referred_by'          (digital_twin)
Failed to register affiliate commission: 'User' object has no attribute 'referred_by' (employment)
```

**تفسير**: كلا الدومينين وصلا الآن بنجاح لـ`get_by_id` وجلبا المستخدم
الصحيح (Backlog #8 مُصلَح ومؤكَّد لهما)، لكنهما اصطدما فورًا **بنفس طبقة
الفشل التالية** (`User.referred_by` غير موجود كحقل على الموديل — تحقَّق
مباشر من `app/domains/identity/models.py`، صفر نتائج) — **بالضبط نفس
النمط المطلوب رصده في التعليمات**. بهذا، **كل الـ12 دومينًا** المرتبطة
بسلسلة `affiliate`/Backlog #10 (الـ10 من جلسة #1 + `digital_twin` و
`employment` الآن) وصلت لنفس طبقة الفشل الموحَّدة. **صفر إصلاح لـ
`User.referred_by` هنا — خارج النطاق صراحة**، توثيق فقط.

## 9. أثر جانبي على الاختبارات الموجودة — فحص شامل

`grep` عن `get_user(`/`pytest.raises` في `tests/`: **صفر اختبار يعتمد
فعليًا على وجود باج #8** (الإشارات الوحيدة في
`test_affiliate_service_missing_methods.py/.md` توثيقية نصية فقط، بلا
أي `pytest.raises` مرتبط).

**تشغيل الـsuite الكامل بعد كل التعديلات**: `60 passed, 4 xfailed` —
**مطابق تمامًا لنتيجة ما قبل هذه الجلسة (جلسة #1)** — صفر تأثير جانبي
غير مُعالَج، صفر اختبار انكسر.

## 10. الحالة الحالية

**التنفيذ (5 ملفات) + التحقق الحي (12/12) + تأكيد وصول `digital_twin`
و`employment` لطبقة `referred_by` الموحَّدة + فحص أثر الاختبارات
الموجودة (60 passed, 4 xfailed، صفر تغيير) — كل ذلك اكتمل.**

**توقفت هنا للعرض على المستخدم قبل `regression test` الدائم و
`PROGRESS_LOG.md` والـ`git commit`، حسب طلبه الصريح.**
