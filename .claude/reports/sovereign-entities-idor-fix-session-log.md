# جلسة إصلاح IDOR في `sovereign_entities` — 4 endpoints معلّقة منذ 2026-08-13

**بدأ التسجيل:** 2026-08-24
**نطاق الجلسة:** حصريًا `list_entities`, `get_entity`, `list_templates`, `list_components` في `eppne-backend/app/domains/sovereign_entities/router.py`. هذه هي الأربعة endpoints اللي استُثنيت عمدًا من إصلاح `SimpleTenant` الشامل (راجع `simpletenant-fix-session-log.md` + التحذير في `.claude/plans/critical-finding-xtenant-systemic.md`)، بانتظار قرار منتجي/أمني صريح — القرار وصل الآن: **تتحول لمحمية بـ`current_user` إجباري**، نفس نمط باقي الدومين.

**الملفات المرجعية اللي اتقرت كاملة قبل البدء:**
- `eppne-backend/app/domains/sovereign_entities/{router,service,repository,schemas}.py`
- `.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md`
- `.claude/reports/simpletenant-fix-session-log.md` (القسم الخاص بـ`academy`/`commerce`/`saas`/`sovereign_entities` — هو النمط الميكانيكي المرجعي، مش تقرير affiliate كما ورد افتراضًا في تعليمات الجلسة — راجع ملاحظة تصحيح تحت)
- `.claude/plans/critical-finding-xtenant-systemic.md` (التحذير البارز أعلى الملف)
- `.claude/reports/require-sector-removal-subscription-fix-session-log.md` (اكتشاف جديد أثناء هذه الجلسة — تفصيل في القسم 3)

**تصحيح على تعليمات الجلسة الأصلية:** طُلب اتباع "نمط affiliate (Phase 10c) وautomation (Phase 12)" — لا يوجد تقرير بهذا الاسم/الرقم فعليًا. الموجود فعليًا: `affiliate-service-missing-methods-session-log.md` (موضوعه ميثودز مفقودة على `AffiliateService`، **لا علاقة له بـIDOR/tenant_id إطلاقًا**)، ولا يوجد تقرير `automation` مطابق. **النمط الميكانيكي الصحيح والمُختبَر فعليًا لنفس هذا النوع من الإصلاح** (استبدال `Depends(get_current_tenant)` بـ`cast(int, current_user.tenant_id)`) موثَّق في `simpletenant-fix-session-log.md` — طُبِّق بنجاح ومؤكَّد حيًا على `academy` (36 موضع)، `commerce` (11)، `saas` (17)، و**17 من أصل 22 موضع في `sovereign_entities` نفسها بالفعل**. هذا هو المرجع المُستخدَم في هذه الجلسة.

---

## 1) تحليل دقيق — كل endpoint، وضعه الحالي بالضبط، ومكان نقص الفلتر

قراءة حية لـ`router.py` (369 سطر) اليوم (2026-08-24) تؤكد: **صفر تغيير على الأربعة endpoints منذ تقرير 2026-08-13** — لسه بالضبط نفس الشكل الموثَّق في `CRITICAL-sovereign-entities-unauthenticated-endpoints.md`.

| # | Endpoint | السطور | التوقيع الحالي | مصدر `tenant_id` |
|---|---|---|---|---|
| 1 | `GET /api/sovereign-entities/` (`list_entities`) | 39-57 | **بلا `current_user` إطلاقًا** | `tenant_id: int = Depends(get_current_tenant)` (سطر 46) — من هيدر `X-Tenant-ID` |
| 2 | `GET /api/sovereign-entities/{entity_id}` (`get_entity`) | 72-80 | **بلا `current_user` إطلاقًا** | `tenant_id: int = Depends(get_current_tenant)` (سطر 75) |
| 3 | `GET /api/sovereign-entities/templates` (`list_templates`) | 339-346 | **بلا `current_user` إطلاقًا** | `tenant_id: int = Depends(get_current_tenant)` (سطر 341) |
| 4 | `GET /api/sovereign-entities/components` (`list_components`) | 349-356 | **بلا `current_user` إطلاقًا** | `tenant_id: int = Depends(get_current_tenant)` (سطر 351) |

**الفلترة على مستوى SQL موجودة فعليًا** (مش "بترجع الجدول كامل") — المشكلة حصرًا في **مصدر قيمة الفلتر**:

- `repository.py:63-76` (`list_entities`): `SovereignEntity.tenant_id == tenant_id` — حيث `tenant_id` الممرَّر هو كائن `SimpleTenant` خام (مش `int`)، لأن `get_current_tenant()` (`core/security.py:275-280`) بترجع `SimpleTenant`، وتوقيع الراوتر (`tenant_id: int = Depends(...)`) **لا يفرض تحويل نوع فعلي وقت التشغيل** — الـannotation مجرد hint، فيبقى المتغيّر فعليًا `SimpleTenant`.
- نفس النمط بالحرف في `get_entity` (`repository.py:26-36`), `list_templates` (`:223-225`), `list_components` (`:227-229`).
- `service.py`: `__init__` (سطر 41-47) بتخزن `self.tenant_id = tenant_id` كما هو (الكائن الخام)، وباقي الميثودز (`get_entity`, `list_entities`, `list_templates`, `list_components`) بتمرره مباشرة لـ`self.repo.*`.

**النتيجة الحالية الفعلية عند أي استدعاء:** `asyncpg.exceptions.DataError` (تمرير كائن `SimpleTenant` كـbind parameter لعمود `INTEGER`) — كراش 500، **مش تسريب ناجح حاليًا**. هذا الكراش نفسه هو اللي بيمنع الاستغلال الفعلي اليوم (تفصيل حرج في القسم 3).

---

## 2) 🔴🔴🔴 اكتشاف جديد أثناء هذه الجلسة — التصنيف الأمني للأربعة endpoints تدهور منذ 2026-08-13، ولازم يُصحَّح فورًا

تقرير `CRITICAL-sovereign-entities-unauthenticated-endpoints.md` الأصلي (2026-08-13) وثّق أن الاستغلال **محصور في حساب `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`** — لأن `main.py:300-305` كان وقتها بيلف كل راوتر بـ`Depends(require_sector(sector))`، واللي بتتطلب توكن JWT صالح كحد أدنى داخليًا (`get_current_active_user`).

**هذا لم يعد صحيحًا.** جلسة لاحقة بتاريخ 2026-08-20 (`.claude/reports/require-sector-removal-subscription-fix-session-log.md`) **أزالت `require_sector` بالكامل من تسجيل الراوترز في `main.py`** (قرار معماري صحيح ومبرَّر، غير متعلق بـ`sovereign_entities` — راجع التقرير لسياقه الكامل). تلك الجلسة أكَّدت صراحة في جدولها ("السيناريو #6") أن **مجلد `sovereign_entities` نفسه لم يُلمَس** — لكنها **لم تُعِد تقييم الأثر غير المباشر** لإزالة الغطاء الوحيد اللي كان بيوفر أي حد أدنى من المصادقة للأربعة endpoints دول تحديدًا (لأنهم أصلًا بلا أي `Depends` مصادقة في توقيعهم الخاص).

**تحقق حي فعلي الآن (2026-08-24، قبل أي إصلاح) يثبت الأثر:**

```
$ curl -i http://127.0.0.1:8000/api/sovereign-entities/          # بلا Authorization header إطلاقًا
HTTP/1.1 500 Internal Server Error

$ curl -i http://127.0.0.1:8000/api/sovereign-entities/2         # بلا Authorization header إطلاقًا
HTTP/1.1 500 Internal Server Error

# عنصر تباين (control) — endpoint فيه current_user إجباري فعليًا في نفس الملف:
$ curl -i http://127.0.0.1:8000/api/sovereign-entities/me        # بلا Authorization header
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer
```

**الخلاصة الحاسمة:** طلب **مجهول تمامًا، بلا أي توكن على الإطلاق**، بيوصل فعليًا لمنطق التطبيق (يكراش على باج `SimpleTenant`، بدل ما يترفض بـ`401`) — بينما endpoint تاني بنفس الملف (`get_my_entities`) بيرفض نفس الطلب المجهول بـ`401` صح. **هذا يثبت أن الأربعة endpoints أصبحوا بلا أي حاجز مصادقة إطلاقًا، مش بس مفتوحين لـSUPER_ADMIN كما وُثِّق سابقًا.** بمجرد إصلاح كراش `SimpleTenant` بأي طريقة سطحية (بدون فحص هوية)، **أي زائر مجهول تمامًا على الإنترنت** (مش بس حساب SUPER_ADMIN مخترَق) هيقدر يقرأ بيانات KYB/رصيد خزينة لأي تينانت. **هذا تصعيد حقيقي في شدة الثغرة يستاهل تحديث فوري لتحذير `critical-finding-xtenant-systemic.md` والتقرير المخصَّص** — سيُنفَّذ كجزء من هذه الجلسة عند التنفيذ (قسم 5).

---

## 3) اكتشاف جانبي (موثَّق فقط، لا علاقة بالإصلاح) — `list_templates`/`list_components` غير قابلين للوصول فعليًا اليوم بسبب ترتيب تسجيل الـroutes

أثناء التحقق الحي، طلب `GET /api/sovereign-entities/templates` رجّع **`422`** مش `500`:
```
{"detail":[{"type":"int_parsing","loc":["path","entity_id"],"msg":"...","input":"templates"}]}
```
**السبب:** `GET /{entity_id}` (`get_entity`, مُعرَّفة في السطر 72) مُسجَّلة **قبل** `GET /templates` (السطر 339) و`GET /components` (السطر 349) في نفس الراوتر. FastAPI/Starlette بتطابق الـroutes بترتيب التسجيل — فـ`/templates` بتقع تحت نمط `/{entity_id}` **أولًا** (int-typed)، فتفشل بـ`422` قبل ما توصل لهاندلر `list_templates` الحقيقي إطلاقًا. **نفس الشيء لـ`/components`.**

**الأثر على هذه الجلسة:** `list_templates`/`list_components` **معطَّلين فعليًا (dead code) عبر الـHTTP path الحقيقي بتاعهم** — بغض النظر عن `SimpleTenant`/IDOR. هذا **باج ترتيب pre-existing منفصل تمامًا**، خارج نطاق الأربعة endpoints المطلوب إصلاحهم (مش IDOR)، **صفر إصلاح عليه في هذه الجلسة** — لكن لازم يُذكر بوضوح لأنه يمنع أي تحقق حي حقيقي عبر الـpath الفعلي لهذين الاثنين تحديدًا (تفصيل في قسم التحقق تحت).

---

## 4) الحل المقترَح — نفس النمط الميكانيكي المُختبَر (17/22 من نفس الملف بالفعل)

**القاعدة (مطابقة لـ`academy`/`commerce`/`saas` و18 endpoint آخر في نفس هذا الملف):**
- إزالة `tenant_id: int = Depends(get_current_tenant)` من التوقيع.
- إضافة `current_user: User = Depends(get_current_active_user)` (موجودة بالفعل في نفس الملف وbaقي الملف — صفر import جديد).
- إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر في جسم الدالة (`cast` مستوردة بالفعل، سطر 4).
- **صفر تغيير على سطر الـimport** (`get_current_tenant` لازم يفضل مستورَد — لسه مستخدَم في `get_entity_page`, سطر 215، بتصميم عام مقصود، خارج نطاق هذه الجلسة تمامًا).

### الديف المقترَح بالضبط (لسه غير مُطبَّق)

**1) `list_entities` (سطور 39-57):**
```python
# قبل (46)
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = SovereignEntitiesService(db, tenant_id)

# بعد
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SovereignEntitiesService(db, tenant_id)
```

**2) `get_entity` (سطور 72-80):** نفس التحويل بالضبط (سطر 75 → إزالة، سطر جديد بعد `):`).

**3) `list_templates` (سطور 339-346):** نفس التحويل (سطر 341 → إزالة).

**4) `list_components` (سطور 349-356):** نفس التحويل (سطر 351 → إزالة).

**مستوى الحماية المختار: `get_current_active_user` (أي مستخدم مسجّل دخول)** — مطابق تمامًا لأقرب endpoints مكافئة بنفس الملف (`get_representatives`, `get_kyb_documents`, `get_my_entities`) اللي بتعرض بيانات على مستوى الكيان/التينانت بلا فحص عضوية إضافي. **لم أفترض مستوى أعلى (زي `get_current_superuser`)** لأن ده تغيير في نموذج الصلاحيات نفسه (قرار منتجي إضافي) مش مجرد سد لـIDOR — لو مطلوب فحص عضوية أدق (مثلاً "بس الممثلين المسجَّلين على الكيان") فهذا خارج نطاق هذا الإصلاح الميكانيكي ويحتاج تصميم منفصل، **قرارك لو عايز ده بدل الأدنى المقترَح هنا**.

**سطور الحذف/الإضافة الدقيقة (ملخّص):**

| الدالة | حذف | إضافة (توقيع) | إضافة (أول سطر بالجسم) |
|---|---|---|---|
| `list_entities` | سطر 46 | `current_user: User = Depends(get_current_active_user),` | `tenant_id = cast(int, current_user.tenant_id)` |
| `get_entity` | سطر 75 | نفس السطر | نفس السطر |
| `list_templates` | سطر 341 | نفس السطر | نفس السطر |
| `list_components` | سطر 351 | نفس السطر | نفس السطر |

**صفر تغيير على `service.py`/`repository.py`** — التوقيعات فيهم بالفعل `tenant_id: int` (int حقيقي)، المشكلة كانت فقط في مصدر القيمة عند الاستدعاء من الراوتر.

---

## 5) خطة التحقق الحي (إلزامي، لسه لم يُنفَّذ إلا الجزء "قبل")

### قبل الإصلاح — ✅ مُنفَّذ فعليًا (قسم 2 فوق)
- `list_entities`/`get_entity`: مؤكَّد حيًا — طلب مجهول تمامًا (بلا توكن) يصل لمنطق التطبيق (500)، بعكس endpoint محمي صح في نفس الملف (401). **هذا يثبت تصعيد الخطورة (قسم 2)، لكنه لا يثبت تسريب بيانات ناجح بعد** — التسريب الفعلي (عبر توكن SUPER_ADMIN حقيقي + هيدر مزوَّر) لسه محجوب بكراش `SimpleTenant` نفسه.
- **مطلوب إضافي قبل التنفيذ (لسه لم يُنفَّذ):** تكرار اختبار الجلسة السابقة بالضبط — مستخدمان throwaway حقيقيان (تينانتين مختلفين، `SUPER_ADMIN`)، هيدر `X-Tenant-ID` مزوَّر، لإثبات أن التسريب "كامن" (500) مش ناجح (200 ببيانات تينانت تاني) — **بنفس منهجية `simpletenant-fix-session-log.md` (يوزر B تينانت14، هيدر مزوَّر=1)**. هل أنفّذه الآن كجزء من "قبل الإصلاح"، أم يكفي الدليل الحالي (طلب مجهول → 500) قبل الانتقال للتنفيذ؟ **بانتظار توجيهك.**

### بعد الإصلاح — مخطَّط، لم يُنفَّذ (بانتظار موافقتك على التنفيذ)
- `list_entities`/`get_entity`: نفس سيناريو "5 اختبارات" المُستخدَم في `academy`/`commerce`/`saas` (شرعي / هيدر مزوَّر لتينانت موجود / هيدر مزوَّر عشوائي / تينانت تاني شرعي / تينانت تاني+هيدر مزوَّر) — تينانت A يشوف كياناته فقط، تينانت B يشوف كياناته فقط، الهيدر بلا أي تأثير في الاتجاهين. **يتطلب بيانات throwaway جديدة** (`sovereign_entities_v2` تحت تينانتين مختلفين — عبر SQL خام، لأن `create_entity` لسه فيها الباج المعروف duplicate-kwarg، **خارج نطاق هذه الجلسة**، نفس قرار الجلسة السابقة بالحرف).
- `list_templates`/`list_components`: **محجوبين فعليًا عن أي تحقق حي عبر الـpath الحقيقي بتاعهم** بسبب باج ترتيب الـroutes (قسم 3) — **قرار مطلوب منك:** (أ) أكتفي بتحقق عبر استدعاء الـservice method مباشرة (`SovereignEntitiesService.list_templates()`) بمعزل عن الراوتر، موثَّق بوضوح كتحقق جزئي (مش end-to-end)، أم (ب) نطلب استثناء نطاق صريح لإصلاح ترتيب الـroutes (نقل `/templates`/`/components` قبل `/{entity_id}`) كجزء ملازم من هذه الجلسة عشان التحقق يبقى كامل؟ **هذا قرار نطاق يحتاج توجيهك، مش افتراض مني.**
- طلب بلا توكن إطلاقًا يجب يرجع `401` بعد الإصلاح (بدل الـ500 الحالي) — تأكيد إضافي إن التصعيد الموثَّق في قسم 2 اتقفل فعليًا.

---

## 6) النطاق — ما لن يُلمَس

- `create_entity` (باج `TypeError: got multiple values for keyword argument 'tenant_id'`) — **خارج النطاق بالكامل**، موثَّق مسبقًا في `PROGRESS_LOG.md` وفي `simpletenant-fix-session-log.md`. صفر لمس.
- `get_entity_page` (استخدام مقصود لـ`get_current_user_optional` + `get_current_tenant` — صفحة عامة بتصميم) — **خارج النطاق**، صفر لمس، `get_current_tenant` يفضل مستورَد بسببه.
- باج `audit_log()` توقيع غير متطابق (يمنع `deposit_to_entity`/`transfer_from_entity` من النجاح الظاهري) — موثَّق مسبقًا، **خارج النطاق**، صفر لمس.
- باج ترتيب الـroutes (قسم 3 فوق) — **موثَّق فقط**، صفر إصلاح إلا بقرار صريح منك (راجع قسم 5).

---

## 7) الحالة الآن

**صفر تنفيذ. صفر تعديل كود.** الخادم الحي (`uvicorn`, PID محلي، `127.0.0.1:8000`، لوج: `eppne-backend/idor_verify_uvicorn.log`) **لسه شغال حاليًا** لغرض التحقق فقط (قراءة فقط تمت عليه حتى الآن — 5 طلبات `curl` بلا أي كتابة/تعديل بيانات) — هوقفه فور توجيهك، أو أسيبه شغال لو هنكمل بالتنفيذ فورًا.

**بانتظار قرارك على 3 نقاط قبل أي سطر كود:**
1. مستوى الحماية المقترَح (`get_current_active_user`، أدنى مطابق للملف) — موافق، أم تفضل مستوى أعلى/فحص عضوية إضافي؟
2. تحديث تحذير `critical-finding-xtenant-systemic.md`/`CRITICAL-...md` ليعكس التصعيد الجديد (زيرو-مصادقة بدل SUPER_ADMIN فقط) — جزء من هذه الجلسة؟
3. `list_templates`/`list_components`: تحقق جزئي (service-level) أم استثناء نطاق لإصلاح ترتيب الـroutes أيضًا؟

---

## 8) قرار المستخدم النهائي [2026-08-24] — موافقة كاملة على الخطة

1. مستوى الحماية: `get_current_active_user` — موافَق كما اقتُرح.
2. تحديث التحذيرات: نعم، ضمن هذه الجلسة، مع دليل الـcurl (401 مقابل 500).
3. `list_templates`/`list_components`: نفس الإصلاح الميكانيكي على التوقيع (نفس التكلفة)، تحقق حي جزئي (service-level) فقط — باج ترتيب الـroutes يُوثَّق كبند Backlog منفصل بأولوية عالية.

**الأمر بالتنفيذ الكامل:** تطبيق الديف على الأربعة، تحقق "بعد" الخماسي على `list_entities`/`get_entity`، تحقق service-level لـ`list_templates`/`list_components`، عرض النتائج + `git status` قبل أي commit.

---

## 9) التنفيذ — مكتمل

### 9.1 الديف

طُبِّق **بالحرف** على الأربعة دوال كما عُرض في القسم 4 (`list_entities`, `get_entity`, `list_templates`, `list_components`) — إزالة `tenant_id: int = Depends(get_current_tenant)`، إضافة `current_user: User = Depends(get_current_active_user)` + `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم. صفر تغيير على `service.py`/`repository.py`/سطر الـimport.

**تأكيد `grep` مستقل:**
```
grep "Depends(get_current_tenant)" router.py → نتيجة واحدة بس (سطر 217، get_entity_page، خارج النطاق بتصميم)
```
`python -m py_compile app/domains/sovereign_entities/router.py` → `exit code 0`.

### 9.2 إعادة تشغيل السيرفر

أُوقفت النسخة القديمة (PID 11120، كانت شغالة منذ التحقق "قبل")، تأكيد صريح "PORT 8000 CONFIRMED FREE"، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، لوج نظيف تمامًا (`Application startup complete`، صفر `Traceback` عند الإقلاع، PID جديد 11124).

### 9.3 التحقق الحي "بعد" — إغلاق تصعيد الخطورة (زيرو-مصادقة)

طلب مجهول تمامًا (بلا أي `Authorization` header) على الأربعة كلهم:
```
GET /api/sovereign-entities/           → 401
GET /api/sovereign-entities/2          → 401
GET /api/sovereign-entities/templates  → 401
GET /api/sovereign-entities/components → 401
```
✅ **التصعيد الحرج من القسم 2/8 مُقفَل بالكامل.**

### 9.4 التحقق الحي "بعد" — عزل التينانت (`list_entities`/`get_entity`)

**بيانات throwaway:** أُعيد استخدام مستخدمين حقيقيين موجودين مسبقًا (بادئة `TEST_` من جلسات سابقة، كلمة مرور معروفة موثَّقة `TestPass123!`): `TEST_super_a` (`id=772`, `SUPER_ADMIN`, تينانت1) و`TEST_instr_b` (`id=774`, `SUPER_ADMIN`, تينانت16) — تسجيل دخول حقيقي عبر `POST /api/identity/login` لكل منهما، توكنات `Bearer` حقيقية. Entity throwaway واحد جديد أُضيف عبر SQL خام تحت تينانت16 (`id=19`, `P_SOVEREIGN_IDOR_VERIFY_TENANT_B`, بادئة `p_sovereign_idor_` واضحة) — مسار الإنشاء عبر الـAPI محجوب ببج `create_entity` المعروف (خارج النطاق). استُخدمت أيضًا entities موجودة مسبقًا تحت تينانت1 (`id=3,4,5,6`، من جلسات سابقة).

**`get_entity` — 9 سيناريوهات، حاسمة بالكامل:**

| الاتجاه | السيناريو | النتيجة |
|---|---|---|
| entity4 (تينانت1) | User A، بلا هيدر | `200` |
| entity4 | User A، هيدر مزوَّر=16 | `200` (مطابق) |
| entity4 | User A، هيدر مزوَّر=999 | `200` (مطابق) |
| entity4 | User B (تينانت16)، بلا هيدر | `404` |
| entity4 | User B، هيدر مزوَّر=1 | `404` (مطابق) |
| entity19 (تينانت16) | User B، بلا هيدر | `200` |
| entity19 | User B، هيدر مزوَّر=1 | `200` (مطابق) |
| entity19 | User B، هيدر مزوَّر=999 | `200` (مطابق) |
| entity19 | User A، بلا هيدر | `404` |
| entity19 | User A، هيدر مزوَّر=16 | `404` (مطابق) |

**✅ حاسم — الهيدر بلا أي تأثير في الاتجاهين، عزل حقيقي مؤكَّد بالكامل (10/10، أكثر من الـ9 المخطَّطة).**

**اكتشاف جانبي أثناء التحقق (data hygiene، صفر علاقة بكود الإصلاح):** entity `id=19` الجديد فشل أول محاولة (`500`، `ResponseValidationError` على `primary_color`/`secondary_color` — أعمدة عندها `default=` على مستوى الموديل [`models.py:70-71`] بس الإدراج عبر SQL خام مباشر لم يملأها). صُحِّح بتحديث الصف نفسه للـdefaults الصحيحة (`#8CC63F`/`#06b6d4`) — نفس درس "NULL defaults" من Phase 16.

**`list_entities` — عزل كامل، الهيدر بلا أي تأثير:**

| المستخدم | بلا هيدر | هيدر مزوَّر=16/1 | هيدر مزوَّر=999 |
|---|---|---|---|
| User A (تينانت1) | `total=4، ids=[3,4,5,6]` | نفس النتيجة بالحرف | نفس النتيجة بالحرف |
| User B (تينانت16) | `total=1، ids=[19]` | نفس النتيجة بالحرف | — |

**اكتشاف جانبي إضافي (data hygiene، pre-existing، غير مرتبط بهذه الجلسة):** entity `id=3` (`P-CTOR-INS-ENTITY`، من جلسة `constructor-mismatch` سابقة تمامًا) كانت `primary_color`/`secondary_color`/`treasury_balance_mrusdt`/`kyb_status` **جميعًا `NULL` فعليًا** رغم `default=` على مستوى الموديل — كانت **بتُسقط `list_entities` بالكامل لأي مستخدم تينانت1** (بغض النظر عن أي هيدر) بـ`ValidationError`/`ResponseValidationError`. صُحِّحت بيانات هذا الصف تحديدًا (تعبئة نفس الـdefaults المُعرَّفة في الموديل: `#8CC63F`/`#06b6d4`/`0`/`PENDING`) — **صفر تغيير كود**، فقط بيانات صف throwaway واحد من جلسة سابقة، لإتمام التحقق الحي. موثَّق كبند Backlog محتمل (فحص منهجي لأعمدة NULL-رغم-default عبر باقي الجداول) في `PROGRESS_LOG.md`.

**✅ `list_entities`/`get_entity` مؤكَّدان حيًا بالكامل، 19/19 نقطة تحقق، صفر تسريب في أي اتجاه.**

### 9.5 التحقق الحي "بعد" — `list_templates`/`list_components` (service-level، بموافقة صريحة)

سكريبت مؤقت (`scratch_verify_sovereign_idor.py`، حُذف بعد الانتهاء) يستخدم `AsyncSessionLocal`/`SovereignEntitiesService` الحقيقيين مباشرة (بمعزل عن الراوتر، بسبب باج ترتيب الـroutes). بيانات throwaway: صف `entity_page_templates` + صف `page_components` لكل تينانت (1، 16)، بادئة `P_SOVEREIGN_IDOR_TPL_`/`P_SOVEREIGN_IDOR_CMP_` واضحة.

```
templates tenant=1  -> [(1, 1, 'P_SOVEREIGN_IDOR_TPL_TENANT_A')]
templates tenant=16 -> [(2, 16, 'P_SOVEREIGN_IDOR_TPL_TENANT_B')]
components tenant=1  -> [(1, 1, 'P_SOVEREIGN_IDOR_CMP_TENANT_A')]
components tenant=16 -> [(2, 16, 'P_SOVEREIGN_IDOR_CMP_TENANT_B')]
ASSERTIONS PASSED: tenant isolation confirmed at service level
```

**✅ عزل التينانت مؤكَّد على مستوى `service` (الطبقة اللي لمسها الإصلاح فعليًا).** التحقق **ليس** end-to-end عبر الـHTTP path الحقيقي — محجوب ببج ترتيب الـroutes المنفصل (موثَّق كبند Backlog تحت).

### 9.6 بند Backlog جديد — `list_templates`/`list_components` معطَّلين فعليًا في الإنتاج (خارج نطاق هذه الجلسة)

`GET /{entity_id}` (`get_entity`, مُسجَّلة السطر ~72) مُسجَّلة **قبل** `GET /templates`/`GET /components` (مُسجَّلتين السطر ~217/~227 بعد الإصلاح) في نفس الملف. FastAPI/Starlette تطابق الـroutes بترتيب التسجيل — أي طلب فعلي لـ`/templates`/`/components` يقع تحت نمط `/{entity_id}` (int-typed) **أولًا**، ويُرفض (`422` int-parsing قبل الإصلاح، `401` بعده لأن فحص المصادقة بقى يسبق فحص الحقل) **قبل ما يوصل لهاندلر `list_templates`/`list_components` الحقيقي إطلاقًا**. **الحل (لم يُنفَّذ، خارج النطاق):** نقل تسجيل `/templates`/`/components` قبل `/{entity_id}` في نفس الملف — تغيير بسيط لكنه خارج نطاق جلسة IDOR هذه بقرار مستخدم صريح.

### 9.7 تحديث التوثيق

- `.claude/plans/critical-finding-xtenant-systemic.md` — تحديث `[2026-08-24]` مُضاف بعد التحذير الأصلي (مُبقَى للسياق التاريخي، مش مُعدَّل) يوثق الإصلاح + اكتشاف التصعيد + دليل الـcurl.
- `.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md` — نفس التحديث، بنفس الأدلة.
- `PROGRESS_LOG.md` — سطر جديد في "الجلسات المُقفلة" (لا تعديل على أي سطر قديم).

### 9.8 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

حُذفت: `sovereign_entities_v2 id=19`، `entity_page_templates id=1,2`، `page_components id=1,2`. **تحقق `SELECT COUNT` مستقل بعد الحذف: صفر في الثلاثة.** سكريبت التحقق المؤقت (`scratch_verify_sovereign_idor.py`) وملف لوج مؤقت (`idor_verify_uvicorn.log`) حُذفا. **entity `id=3`/`id=4-6` (تينانت1) وentity `id=19`... (محذوف) لم تُلمَس أي بيانات أخرى من جلسات سابقة غير الإصلاح الموصوف صراحة أعلاه.** المستخدمان `TEST_super_a`/`TEST_instr_b` (وتوكناتهما) — لم يُعدَّل أي منهما، استُخدما للقراءة فقط.

---

## 10) الحالة النهائية

✅ **الأربعة endpoints محمية بالكامل، مؤكَّدة حيًا (19/19 نقطة تحقق لـ`list_entities`/`get_entity`، عزل جزئي مؤكَّد service-level لـ`list_templates`/`list_components`).**
✅ **تصعيد الخطورة الحرج (زيرو-مصادقة) مُقفَل ومُوثَّق في التحذيرين المرجعيين.**
✅ **صفر لمس على `create_entity`، `get_entity_page`، أو أي جزء آخر من الدومين خارج الأربعة endpoints المطلوبين.**
🟠 **بند Backlog جديد موثَّق:** باج ترتيب routes يمنع الوصول الفعلي لـ`/templates`/`/components` — خارج النطاق، لم يُصلَح.
⏳ **لم يُنفَّذ بعد:** `git add`/commit — بانتظار مراجعتك لـ`git status`/`git diff` تحت قبل أي commit.
