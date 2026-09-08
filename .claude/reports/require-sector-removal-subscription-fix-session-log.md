# إلغاء `require_sector` + إصلاح `require_subscription` + Whitelist مبدئي — تقرير الجلسة [2026-08-20]

**الخطة المعتمَدة:** `.claude/plans/glistening-toasting-bentley.md` (الملف الفعلي
الذي وافق عليه المستخدم أثناء هذه الجلسة — الملف الوارد أصلًا باسم
`require-sector-removal-subscription-fix-session-instructions.md` في الطلب
كان "خطة عاجلة محدَّثة"، ونُفِّذ بالحرف).

المرجع الأصلي للاكتشاف: `.claude/reports/academy-live-testing-session-log.md`
(قسم "اكتشافات جديدة"، بندان 1 و2).

---

## 1. القرار المعماري (خلفية)

`require_sector()` كانت مسجَّلة على مستوى `include_router` لكل الـ30 دومين في
`main.py:300-306`، وترفض أي مستخدم غير `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` من
كل endpoint في المنصة — لأن لا يوجد ولم يوجد أي مصدر حقيقة لـ"sector واحد لكل
مستخدم" في الكود (`_issue_tokens` لا تصدر claim `sector` إطلاقًا). بعد نقاش
مباشر مع المستخدم، تأكد أن نموذج المنصة الفعلي **لا يدعم** أصلًا فكرة sector
ثابت — تينانت واحد يمكن أن يكون مشتركًا في عدة دومينات/خدمات معًا في نفس
الوقت، وهذا بالضبط ما يمثّله نظام `saas_tenant_subscriptions` الموجود فعلاً.

**القرار: إلغاء `require_sector` من مسار التنفيذ بالكامل** (الدالة نفسها
باقية للمرجعية، معلَّمة `DEPRECATED`)، والاعتماد حصريًا على
`require_subscription` بعد إصلاحها + whitelist مبدئي لدومينات معفاة.

---

## 2. السبب الجذري لـ`require_subscription` (تحديد الطرف الخاطئ)

- الاستدعاء الخاطئ (قبل الإصلاح)، `core/security.py:317`:
  `await service.check_and_enforce_access(current_user.tenant_id, service_code)`
- التوقيع الفعلي، `domains/saas/service.py:237`:
  `async def check_and_enforce_access(self, service_code: str)` — تستخدم
  `self.tenant_id` داخليًا (مضبوط في `__init__(self, db, tenant_id)`،
  والـcaller في `security.py:316` أصلًا يمرره صح عند إنشاء الكائن:
  `SaaSControlService(db, current_user.tenant_id)`).
- **الخلاصة: الطرف الخاطئ هو الاستدعاء (معامل زائد)، وليس التوقيع.** تم حذف
  `current_user.tenant_id` الزائد من الاستدعاء فقط — صفر تعديل على
  `saas/service.py`.

---

## 3. التغييرات المُطبَّقة

### `app/main.py`
- حذف `require_sector` من import (كان يُستورد ولا يُستخدم بعد الحذف).
- حذف `dependencies=[Depends(require_sector(sector))]` من حلقة
  `include_router` (كانت أسطر 300-306). `sector` باقٍ في `routers_config`
  tuples بلا استخدام فعلي — لم تُعَد هيكلة الـtuples نفسها لتقليل مساحة
  التغيير.

### `app/core/security.py`
- `require_sector()`: **لم تُحذف.** أُضيف تعليق `# DEPRECATED — no longer
  wired into any router (main.py); no sector claim exists on tokens. Kept
  for reference/tests only.` فوقها مباشرة.
- `require_subscription()`: أُصلح الاستدعاء لمعامل واحد فقط
  (`check_and_enforce_access(service_code)`).
- أُضيف ثابت جديد **`SUBSCRIPTION_CHECK_EXEMPT_SERVICES: set[str] = {"identity",
  "saas"}`** فوق `require_subscription` مباشرة، بتعليق صريح:
  > ⚠️ قرار مبدئي قابل للتغيير لاحقًا — دومينات معفاة بالكامل من فحص الاشتراك.

  `subscription_checker` الداخلية تتحقق من `service_code in
  SUBSCRIPTION_CHECK_EXEMPT_SERVICES` **قبل** إنشاء `SaaSControlService` أصلًا
  — تخطٍّ حقيقي (صفر استعلام DB)، وليس مجرد نجاح دائم بعد الفحص.

  **⚠️ تأكيد صريح: هذا القرار مبدئي وقابل للتغيير — قائمة `identity`/`saas`
  ليست تصميمًا نهائيًا، فقط حد أدنى مبدئي متفق عليه في هذه الجلسة.**

### لا تعديل (تم التحقق والتأكيد فقط)
- `get_sector()`/`set_sector()` (`core/logging_conf.py`): باقيتان بلا تعديل.
  `set_sector()` تُستدعى من `get_current_user` (`security.py:146`) كأثر
  جانبي غير ضار على كل طلب. `get_sector()` كانت مستخدَمة فقط داخل
  `require_sector()` (سطر 213) — أصبحت غير مستدعاة من أي مسار تنفيذ حي، لكن
  الدالتان تبقيان كما هما. `grep` شامل أكّد عدم وجود استخدام آخر لهما في
  المشروع (`command/service.py::_get_sector_stats` اسم مشابه فقط، منطق مختلف
  تمامًا وغير مرتبط بـContextVar القطاع).
- `app/domains/invoicing/router.py:13` يستورد `require_sector` من
  `app/api/deps.py` **لكن لا يستخدمه فعليًا كـDepends في أي مكان بالملف**
  (import ميت). لم يُلمَس — خارج نطاق الجلسة.
- `app/domains/commerce/router.py:7` يستورد `require_subscription` بنفس
  النمط (import ميت، بدون أي `Depends(require_subscription(...))` فعلي في
  الملف). لم يُلمَس.
- `app/api/deps.py` (shim) يعيد تصدير الدالتين كما هما — لا حاجة لتعديل
  لأنهما لم تُحذفا.
- ثغرة `sovereign_entities` الأمنية المعروفة — صفر لمس (مؤكَّد بـ`git status`
  على مجلد الدومين: لا تغيير).
- `app/main.py.bak` — ملف نسخة احتياطية غريب لوحظ أثناء الاستكشاف، ليس جزءًا
  من الشجرة المستوردة، لم يُلمَس.

---

## 4. التحقق الساكن (قبل الاختبار الحي)

- `python -c "import app.main"` → exit code 0 (استيراد نظيف).
- `pytest tests/test_security_deps_unification.py tests/test_saas_active_subscription.py`
  → **8 passed**، صفر فشل. مهم: اختبارات `require_sector` الأربعة
  (`test_security_deps_unification.py`) تستدعي الدالة **مباشرة بمعزل عن
  `main.py`** — نجاحها المستمر متوقَّع ومقصود (الدالة لم تُحذف، فقط أُلغي
  تسجيلها في الراوتر).

---

## 5. الاختبار الحي — إعداد البيانات (throwaway فقط)

أُعيد استخدام تينانت/مستخدمي throwaway موسومين `TEST_` من جلسة
`academy-live-testing` (`academy_tenants.id=16` = `TEST_TENANT_B`، مستخدم
`id=774` = `TEST_instr_b`). التعديلات الجديدة كلها على بيانات throwaway حصرًا
— **صفر لمس على أي تينانت/اشتراك حقيقي**:

| التغيير | التفاصيل |
|---|---|
| ترقية دور | `users.id=774` (`TEST_instr_b`, tenant 16) رُجِّع من `SUPER_ADMIN` (كان تُرقّى مؤقتًا في الجلسة السابقة للالتفاف حول باج `require_sector`) إلى `ADMIN` عادي — ضروري لإثبات أن دورًا غير-superadmin يصل الآن فعليًا لمنطق `require_subscription` بدل الانحجاب المبكر بـ`require_sector`. |
| Catalog جديد | `saas_service_catalog`: `id=47` code=`academy` (`TEST_REQSECTOR_SESSION_ACADEMY_SERVICE`)، `id=48` code=`affiliate` (`TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE`) — لم يكن أي كود منهما موجودًا في الـcatalog أصلًا. |
| Plans جديدة | `saas_service_plans`: `id=47`/`id=48` تحت الخدمتين أعلاه (سعر 0، throwaway بحتة). |
| Access جديد | `saas_tenant_service_access`: صفان لـ`tenant_id=16` (الخدمتان أعلاه، `is_active=true`) — الطبقة الأولى من فحص الوصول. |
| Subscriptions | `saas_tenant_subscriptions`: صفان جديدان `ACTIVE` لـ`tenant_id=16` (خطة `academy` ثم لاحقًا خطة `affiliate` أيضًا) — أُضيفا تباعًا أثناء الاختبار (راجع الجدول أدناه)، لم يُلمَس الصف الموجود مسبقًا (`id=47`, من جلسة `saas9` سابقة). |

جميع القيم موسومة بوضوح (`TEST_`/`test_reqsector_`) ومُبقاة كما هي، لم تُحذف —
بنفس القرار المتبع في جلسة `academy-live-testing`.

---

## 6. الاختبار الحي — جدول قبل/بعد (السيناريوهات الستة المطلوبة)

خادم `uvicorn` حقيقي (تم إيقاف نسختين قديمتين بواقيتين من جلسة سابقة أولًا،
بموافقة صريحة، ثم تشغيل نسخة جديدة بالكود المُصلَح) + `curl` عبر الشبكة —
صفر محاكاة/mock.

| # | السيناريو | قبل الإصلاح (متوقَّع من التقرير المرجعي) | بعد الإصلاح (مُلاحَظ حيًا الآن) |
|---|---|---|---|
| 1 | `ADMIN` عادي (`TEST_instr_b`, tenant 16) بلا اشتراك `academy`/`affiliate` → `POST /api/academy/courses` و`GET /api/affiliate/commissions` | `403 "sector not defined"` (require_sector) أو `500 TypeError` (require_subscription) | **مطابق للمتوقَّع تمامًا:** كلاهما `403` — `{"detail":"الخدمة 'academy' غير متاحة. يرجى الاشتراك في الخطة المناسبة.","code":"PermissionDeniedError"}` و`{"detail":"الخدمة 'affiliate' غير متاحة...","code":"PermissionDeniedError"}` — رسالة `require_subscription` الصحيحة، **صفر ذكر لـsector**. |
| 2 | نفس المستخدم، بعد تفعيل اشتراك throwaway لـ`academy` لتينانته | يفشل حتمًا (باج `require_sector` أو TypeError) | **الفحص عدَّى بنجاح** — `POST /api/academy/courses` توقف عن إرجاع 403/سكتور، ووصل فعليًا لمنطق `academy/service.py.create_course()` حيث اصطدم بباج **جديد كليًا غير مرتبط** (تفصيل في §7 تحت). هذا يثبت مباشرة أن بوابة الاشتراك اجتازت المستخدم بنجاح. |
| 3 | نفس المستخدم يستدعي دومين مختلف (`affiliate`) وتينانته مشترك فيه أيضًا | يفشل حتمًا | **نجاح كامل ونظيف:** بعد تفعيل اشتراك throwaway ثانٍ لـ`affiliate` لنفس التينانت (16)، `GET /api/affiliate/commissions` → `200 {"data":[],"total":0,...}`. **قبل** تفعيل هذا الاشتراك الثاني، نفس المستخدم كان لا يزال يُرفَض من `affiliate` (`403`) رغم اشتراكه الفعّال في `academy` — إثبات مباشر لعزل الفحص لكل دومين على حدة (تينانت واحد، اشتراكات متعددة ومستقلة). |
| 4 | مستخدم (`TEST_applicant`, id=776, tenant 1) بلا أي اشتراك على الإطلاق → `identity`/`saas` | يُفترض ينجح دائمًا (لا تغيير) | **مؤكَّد على مستويين:** (أ) HTTP: `GET /api/identity/me` → `200`، `GET /api/saas/services` → `200` — بلا أي فحص اشتراك أصلًا (لا `identity` ولا `saas` يستخدمان `require_subscription` في أي راوتر اليوم). (ب) **تحقق مباشر على آلية الـwhitelist نفسها** (بمعزل عن أي راوتر، بنفس منهجية اختبارات المشروع): استدعاء `require_subscription("identity")`/`("saas")` بمعامل `db=None` عمدًا نجح بلا أي استثناء (يثبت أن `SaaSControlService` لم يُنشأ أصلًا ولا DB لُمست) — بينما نفس الاستدعاء بكود غير مُدرَج بالـwhitelist مع `db=None` رمى `AttributeError: 'NoneType' object has no attribute 'execute'` فورًا (يثبت أنه **حاول فعليًا** الوصول لقاعدة البيانات). هذا يثبت أن التخطي حقيقي ومتعمَّد، وليس نجاحًا صدفويًا. |
| 5 | `POST /academy/courses` بحساب `SUPER_ADMIN` مع اشتراك `academy` فعّال | باج `require_subscription` (500) يمنعه دائمًا | بوابة الاشتراك اجتازت بنجاح (نفس نتيجة #2)، ثم اصطدم بباج إنتاجي **جديد كليًا** في `academy/service.py:112` — موثَّق بالتفصيل في §7، **خارج نطاق هذه الجلسة تمامًا، لم يُصلَح**. |
| 6 | ثغرة `sovereign_entities` الأمنية المعروفة | لا تُمس | **مؤكَّد:** `git status`/`git diff --stat` على نطاق الجلسة يظهران فقط `app/main.py` و`app/core/security.py` — صفر تغيير في `app/domains/sovereign_entities/`. |

**تأكيد إضافي (غير مطلوب صراحة في الستة، لكن يثبت النطاق الكامل للإصلاح):**
`GET /api/commerce/products` (دومين لا يستخدم `require_subscription` إطلاقًا،
كان محجوبًا **فقط** بـ`require_sector` سابقًا) بحساب المستخدم رقم 776 (بلا أي
اشتراك) → `200 []` — يثبت أن الإلغاء طبّق فعليًا على الـ30 دومين، لا فقط
`academy`/`affiliate` اللتين تستخدمان `require_subscription`.

---

## 7. اكتشاف جانبي جديد (خارج النطاق، توثيق فقط — لم يُصلَح)

**`academy/service.py:112` — `create_course()` تمرر `instructor_id` مرتين:**

```
TypeError: app.domains.academy.repository.AcademyRepository.create_course()
got multiple values for keyword argument 'instructor_id'
```

`academy/service.py:112`: `course = await self.repo.create_course(**data,
instructor_id=instructor_id)` — لكن `data` (من `CourseCreate.model_dump()`)
يحتوي أصلًا مفتاح `instructor_id` (حقل اختياري على الـschema،
`schemas.py:118`)، فيتكرر التمرير. **هذا باج مختلف كليًا عن باج
`create_org_entity`/`TypeError` الموثَّق سابقًا في `academy-live-testing-session-log.md`**
(ذاك في إنشاء الكيان التنظيمي، هذا في إنشاء الكورس نفسه بعد نجاح كل الفحوصات
السابقة). **الأثر:** أي محاولة `POST /academy/courses` ناجحة من ناحية
الصلاحيات/الاشتراك (تمامًا كحالتنا هنا، بعد إصلاح هذه الجلسة) ستفشل 500 دائمًا
طالما `org_entity_id` صحيح وموجود. لم يُلمَس — يُضاف كبند Backlog جديد في
`PROGRESS_LOG.md`.

---

## 8. الخلاصة

| البند | الحالة |
|---|---|
| `require_sector` مُلغاة من كل مسار تنفيذ فعلي (main.py) | ✅ مؤكَّد — `grep` شامل: `Depends(require_sector` غير موجودة في أي ملف حي (فقط `main.py.bak` غير المستخدَم) |
| الدالة `require_sector()` نفسها | ✅ باقية، معلَّمة `DEPRECATED`، لا تزال تُستدعى مباشرة من `tests/test_security_deps_unification.py` (8/8 اختبارات ناجحة) |
| `require_subscription` مُصلَحة | ✅ مؤكَّد حيًا (السيناريوهات 1-3-5) |
| Whitelist (`identity`, `saas`) | ✅ مُطبَّق، **مبدئي وقابل للتغيير صراحة** — مُختبَر HTTP + مباشر (تخطٍّ حقيقي، صفر DB) |
| ثغرة `sovereign_entities` | ✅ صفر لمس |
| اكتشاف جانبي جديد (`academy.create_course` `instructor_id` مكرر) | 🔴 موثَّق، غير مُصلَح، خارج النطاق |
| بيانات throwaway | مُبقاة موسومة `TEST_`/`test_reqsector_`، لم تُحذف |
