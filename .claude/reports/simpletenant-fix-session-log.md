# تقرير جلسة — إصلاح باج `SimpleTenant`/type mismatch (نمط `get_current_tenant` عبر المشروع)

**بدأ التسجيل:** 2026-08-13
**نطاق الجلسة:** جلسة منفصلة تمامًا عن باج الترانزاكشن (`transaction-savepoint-bug-session-log.md`) وعن `critical-finding-xtenant-systemic.md` — الجلسة دي مخصصة حصريًا لباج `SimpleTenant`/type mismatch اللي اتكشف كاكتشاف حرج ثانٍ أثناء جلسة الترانزاكشن (راجع `PROGRESS_LOG.md` قسم "🔴🔴 اكتشاف نطاق ثانٍ").

**الملفات المرجعية اللي اتقرت كاملة قبل البدء:** `transaction-savepoint-bug-session-log.md`، `critical-finding-xtenant-systemic.md`، `phase16-session-log.md`، `PROGRESS_LOG.md` (آخر الأقسام). صفر تناقض بين الأربعة.

---

## [2026-08-13] المرحلة 1 — الجرد الشامل (read-only بالكامل، صفر تعديل كود)

### المنهجية

1. `grep` شامل لـ`get_current_tenant` عبر `app/` بالكامل (مش بس `app/domains`) — تأكيد إن الاستخدام محصور في `app/domains/*/router.py` (27 ملف فعلي + نسخة `.bak` مستبعدة لأنها مش منفَّذة) + تعريفها في `app/api/deps.py`. **صفر استخدام خارج الـrouters.**
2. سكريبت Python مخصَّص (parsing بالإزاحة، مش regex أعمى) قرأ كل الـ33 ملف `router.py` الموجودين فعليًا تحت `app/domains/`، استخرج كل دالة endpoint فيها بارامتر `Depends(get_current_tenant)`، وحلّل جسم الدالة لتصنيف كل استخدام:
   - **(أ) `.id` مستخدَمة بشكل صحيح** — صفر كراش من هذا المصدر.
   - **(ب) الكائن (أو المتغيّر المُسمّى بالغلط `tenant_id: int`) بيتستخدم مباشرة كـ`int`** — كراش مؤكَّد (`DataError`/`TypeError`) عند أول استخدام فعلي (SQL bind أو تمرير لـconstructor).
3. **كل نتيجة تلقائية اتراجعت يدويًا بقراءة الكود مباشرة** (مش اعتماد أعمى على السكريبت) — اكتشفنا وصححنا false positive حقيقي أثناء المراجعة (تفصيل تحت، دومين `employment`).
4. فحص إضافي مستقل: `grep` لـ`tenant\.\w+` عبر كل الملفات لرصد أي وصول لخاصية غير `.id` على الكائن (`SimpleTenant` عندها `.id` بس، أي خاصية تانية = `AttributeError` مؤكَّد) — كشف حالة إضافية غير متوقَّعة (تفصيل تحت، `invitations`).
5. فحص أسماء البارامترات المستخدَمة (`grep` على نمط الإعلان نفسه) — 3 أنماط بس موجودة في كل المشروع: `tenant: AcademyTenant`, `tenant: SimpleTenant`, `tenant_id: int`. النمط التالت (`tenant_id: int`) هو نفسه علامة الباج — اتأكَّد إنه موجود في **4 ملفات بالحرف، صفر زيادة**.

### تصحيح أثناء الفحص (منهجي، يستاهل التوثيق)

**`employment/router.py`** ظهر أول مرة في السكريبت كـ"BUG" في 6 مواضع (بسبب `if not tenant:` — فحص truthiness بسيط بيخلي regex بسيط يفتكرها استخدام "مباشر" للكائن). **قراءة الكود يدويًا أثبتت إن ده false positive كامل** — كل الـ6 مواضع بتستخدم `tenant.id` صح بعد الفحص، `if not tenant:` نفسه بيفحص وجود الكائن بس (دايمًا True عمليًا، منطقيًا زايد لكن مش خطر). **`employment` بالكامل فئة (أ)، صفر كراش.**

---

## نتيجة الجرد الكامل — 33 ملف `router.py`، 372 استخدام فعلي لـ`get_current_tenant`

### ✅ دومينات مُصلَحة بالفعل من جلسات سابقة (صفر استخدام متبقٍّ لـ`get_current_tenant`)
`finance` (8 endpoints، Phase الترانزاكشن)، `command` (18 endpoint، Phase 16).

### 🟢 دومينات صفر استخدام لـ`get_current_tenant` من الأساس (مؤكَّدة سابقًا SAFE في `critical-finding-xtenant-systemic.md`)
`admin`, `invoicing`, `iot`, `privacy` — صفر تغيير مطلوب.

### ⚪ دومين بلا `router.py` أصلًا (موثَّق سابقًا)
`agritech` — كود موجود (`service.py`/`repository.py`) لكن غير معروض بأي endpoint.

### 🔴 (ب) 4 دومينات — 100% من استخداماتها كراش مؤكَّد (87 موضع، صفر استثناء داخل كل ملف)

النمط بالحرف في كل الأربعة: `tenant_id: int = Depends(get_current_tenant)` ثم `tenant_id` (الكائن كامل) بيتبعت مباشرة لـconstructor الـService (`XService(db, tenant_id)`) و/أو بيتحط في dict كـ`entity_data["tenant_id"] = tenant_id`. **صفر استخدام لـ`.id` في أي من الأربعة ملفات — تأكَّد بمطابقة عدد `Depends(get_current_tenant)` مع عدد نمط `tenant_id: int =` (تطابق تام، صفر فرق) وعدد `tenant.id` (صفر في الأربعة).**

| الدومين | عدد المواضع | أمثلة (file:line الإعلان → line الاستخدام الخطر) |
|---|---|---|
| **academy** | **36** | `router.py:83→86` (`create_org_entity`), `:107→110`, `:128→131`, `:158→161`, `:182→185`, `:192→197`, `:203→209`, `:219→222`, `:236→239`, `:247→250`, `:259→262`, `:276→279`, `:293→296`, `:310→313`, `:322→325`, `:334→337`, `:347→350`, `:360→363`, `:372→375`, `:384→387`, `:397→400`, `:411→414`, `:425→428`, `:435→438`, `:446→449`, `:461→464`, `:486→489`, `:498→501`, `:510→513`, `:525→528`, `:537→540`, `:556→559`, `:569→572`, `:581→584`, `:594→598`, `:607→610` — كل الدوال (`create_*`, `get_*`, `update_*`, `enroll_*`, ...) في الملف بالكامل |
| **commerce** | **12** | `:26→29` (`create_store`), `:42→45` (`create_product`), `:58→62` (`list_products`), `:79→82` (`checkout`), `:95→98` (`get_my_orders`), `:115→118`, `:131→134`, `:146→149`, `:163→166`, `:181→184`, `:198→201`, `:213→216` |
| **saas** | **17** | `:28→31` (`list_services`), `:40→43`, `:53→56`, `:68→71`, `:80→83`, `:98→101`, `:110→113`, `:122→125`, `:134→137`, `:148→151`, `:159→162`, `:176→179`, `:187→190`, `:199→202` (`pay_invoice` — معاملة مالية)، `:214→217`, `:229→232,241` (خط مزدوج)، `:257→260` |
| **sovereign_entities** | **22** | `:23→26,29` (`create_entity`، **خطين خطر: constructor + dict assignment**)، `:46→49`, `:63→66`, `:75→78`, `:89→92`, `:104→107`, `:120→123`, `:133→136`, `:147→150`, `:163→166`, `:181→184`, `:196→199`, `:215→218`, `:229→232`, `:243→246`, `:269→272`, `:284→287` (`deposit_to_entity`), `:307→310` (`transfer_from_entity`), `:330→333`, `:341→344`, `:351→354`, `:364→367` |

**ملاحظة خاصة على `sovereign_entities.create_entity`:** فيه **باج ثانٍ متراكب** موثَّق مسبقًا في `PROGRESS_LOG.md` (قسم 🟠 الباجات المتفرقة) — `repository.create_entity()` بترمي `TypeError: got multiple values for keyword argument 'tenant_id'` (باج تمرير معاملات مكرر، منفصل تمامًا عن `SimpleTenant`). **هذا الباج الثاني هيظهر عمليًا الأول** (كراش على مستوى استدعاء Python نفسه، قبل ما الكود يوصل لأي استعلام DB يكشف باج `SimpleTenant`) — يعني إصلاح `SimpleTenant` وحده مش هيكفي لتشغيل `create_entity` بالكامل؛ الباج التاني (مكرر الـkwarg) هيفضل حاجز بعده، **خارج نطاق هذه الجلسة** (فئة مختلفة تمامًا)، يستاهل تتوثق كملاحظة تانية مش تتصلح دلوقتي إلا لو طلبت.

### 🟠 (جديد، لم يكن موثَّقًا في أي تقرير سابق) — حالة `AttributeError` منفصلة تمامًا في `invitations`

`invitations/router.py:42` (داخل `create_invitation`):
```python
invite_url = f"https://{tenant.domain}/invite/{invitation.id}"
```
`tenant` هنا كائن `SimpleTenant` (فيه `.id` بس، من `api/deps.py:144-145`: `class SimpleTenant: id: int`). **`SimpleTenant` معندهاش خاصية `.domain` إطلاقًا** — هذا السطر هيرمي `AttributeError: 'SimpleTenant' object has no attribute 'domain'` **دايمًا، لكل طلب**، بغض النظر عن أي تينانت. باقي الدالة نفسها (`tenant_id=cast(int, tenant.id)` في سطر 37) صحيحة ومفيهاش باج الكراش الأساسي — لكن الدالة كلها هتفشل برضه بسبب السطر 42.
**فئة مختلفة تمامًا عن باج (ب) الأساسي** (مش type-mismatch على int، دي attribute مفقودة تمامًا من الكائن) — **صفر مكان تاني فيه نفس النمط** (تأكَّد بـ`grep` شامل لـ`tenant\.\w+` عبر كل الملفات — الحالة الوحيدة من نوعها في المشروع كله).

### 🟡 (فئة ثالثة، غير خطرة) — بارامتر `tenant`/`tenant_id` مُعلَن لكن غير مُستخدَم إطلاقًا (7 مواضع، صفر كراش)

| الدومين | file:line | الدالة | ملاحظة |
|---|---|---|---|
| insurance | `router.py:129` | `renew_subscription` | البارامتر معلن، صفر استخدام في الجسم |
| insurance | `router.py:168` | `get_my_claims` | نفس الشيء |
| insurance | `router.py:230` | `get_my_pensions` | نفس الشيء |
| insurance | `router.py:243` | `disburse_pensions` | نفس الشيء — **ملاحظة أمنية منفصلة موثَّقة مسبقًا في `critical-finding-xtenant-systemic.md`: الدالة دي بتتجاهل الـtenant تمامًا وبتصرف لكل الـtenants، مش مرتبطة بباج `SimpleTenant`** |
| insurance | `router.py:277` | `get_my_employee_profile` | نفس الشيء |
| manufacturing | `router.py:343` | `schedule_maintenance` | البارامتر معلن، صفر استخدام؛ `log_id` نفسه مش مفلتر بالـtenant في هذه الدالة (IDOR محتمل، خارج نطاق هذه الجلسة) |
| projects | `router.py:41` | `list_products` | البارامتر معلن، صفر استخدام |

**صفر كراش من هذه الـ7** — البارامتر ميت (dead code)، لكنها نقطة عزل تينانت مفقودة أصلًا (مش بسبب `SimpleTenant`، الدالة كانت هتكون كده حتى لو `get_current_tenant` بترجع `int` خام). موثَّقة هنا للاكتمال، **خارج نطاق إصلاح `SimpleTenant`**.

### ✅ (أ) باقي الدومينات — `.id` مستخدَمة بشكل صحيح بالكامل، صفر كراش (23 دومين، ~277 موضع)

`affiliate` (11)، `ai_agents` (13)، `ai_governance` (9)، `arbitration_syndicates` (17)، `automation` (3)، `communications` (2)، `digital_twin` (14)، `employment` (6، بعد تصحيح الـfalse positive)، `health` (6)، `identity` (9 — فئة باج مختلفة تمامًا موثَّقة مسبقًا، pre-auth self-enrollment، لا علاقة بـ`SimpleTenant`)، `insurance` (9 من أصل 14، الباقي 5 unused فوق)، `invitations` (30 من أصل 31 — الموضع الـ31 هو `AttributeError` فوق)، `logistics` (22)، `manufacturing` (19 من أصل 20)، `projects` (18 من أصل 19)، `realestate` (9)، `service_marketplace` (7)، `social` (19)، `tenders_auctions` (6)، `tourism_sports` (10)، `transport` (16)، `translation` (3)، `zamakana` (19).

---

## الخلاصة النهائية للمرحلة 1

| الفئة | العدد | التفصيل |
|---|---|---|
| 🔴 (ب) كراش `DataError`/`TypeError` مؤكَّد (كائن كامل كـint) | **87 موضع، 4 دومين** | `academy`(36), `commerce`(12), `saas`(17), `sovereign_entities`(22) — **100% من استخدامات كل ملف من الأربعة** |
| 🟠 كراش `AttributeError` (فئة جديدة، خاصية مفقودة) | **1 موضع، 1 دومين** | `invitations.create_invitation` (`.domain`) |
| 🟡 بارامتر ميت، صفر كراش لكن صفر عزل تينانت فعلي | **7 مواضع، 3 دومين** | `insurance`(5), `manufacturing`(1), `projects`(1) |
| ✅ (أ) `.id` صحيحة، صفر كراش | **277 موضع، 23 دومين** | التفصيل فوق |
| ✅ مُصلَح مسبقًا | `finance`, `command` | صفر استخدام متبقٍّ |
| ✅ SAFE من الأساس | `admin`, `invoicing`, `iot`, `privacy` | صفر استخدام لـ`get_current_tenant` |
| ⚪ N/A | `agritech` | صفر `router.py` |

**إجمالي مُتحقَّق منه:** 372 استخدام حقيقي عبر 33 ملف `router.py` (كل الدومينات الموجودة فعليًا في المشروع). **صفر ملف اتفات من الفحص.**

**الأولوية المرشَّحة للإصلاح (بترتيب الأثر):**
1. `academy` (36)، `commerce` (12)، `saas` (17، فيها `pay_invoice` — معاملة مالية)، `sovereign_entities` (22، فيها `deposit_to_entity`/`transfer_from_entity` — معاملات مالية + باج `create_entity` المتراكب) — **المؤكَّدين مسبقًا، أولوية الإطلاق كما طلبت.**
2. `invitations.create_invitation` — إصلاح إضافي بسيط (خط واحد، `tenant.domain` محتاج مصدر بديل — على الأرجح `current_user`-scoped lookup بدل الكائن الوهمي، يحتاج قرار: مصدر الدومين الحقيقي منين؟).

**الحالة:** ✅ المرحلة 1 مكتملة بالكامل، مؤكَّدة بقراءة كود مباشرة لكل حالة (مش استنتاج سكريبت وحده). **في انتظار موافقتك للانتقال للمرحلة 2 (تطبيق القاعدة الموحّدة على academy/commerce/saas/sovereign_entities).**

---

## [2026-08-13] موافقة المستخدم على المرحلة 2 — الترتيب والشروط

**الترتيب المعتمَد:** `academy` → `commerce` → `saas` → `sovereign_entities`، دومين ورا التاني بالحرف — كل واحد: ديف مجمّع للمراجعة أولًا، تحقق حي كامل بعد التطبيق، بعدين الانتقال للتالي.

**3 شروط إلزامية اتفق عليها المستخدم قبل البدء:**

1. **`sovereign_entities.create_entity`:** متصلحش باج الـkwarg المكرر (`TypeError: got multiple values for keyword argument 'tenant_id'`، موثَّق مسبقًا في `PROGRESS_LOG.md`) في هذه الجلسة — فئة مختلفة تمامًا، خارج النطاق. **لازم يوثَّق بوضوح في التوثيق النهائي إن `create_entity` تحديدًا هتفضل غير قابلة للتحقق الحي حتى بعد إصلاح `SimpleTenant`** بسبب الباج التاني المتراكب. باقي الـ21 موضع في نفس الدومين يتصلحوا عادي.
2. **`saas.pay_invoice` و`sovereign_entities.deposit_to_entity`/`transfer_from_entity`** (معاملات مالية): التحقق الحي عليهم بعد الإصلاح لازم يكون بنفس صرامة `finance.transfer` بالظبط — `SELECT` مستقل على الأرصدة الفعلية قبل/بعد، مش status code.
3. **`invitations.create_invitation`** (باج `AttributeError` على `tenant.domain`): **متصلحش دلوقتي** — قرار تصميمي محتاج توضيح الأول (مصدر `tenant.domain` البديل إيه؟ `current_user`-scoped lookup؟). يُوثَّق كبند منفصل معلّق لقرار لاحق، خارج نطاق الأربعة دومينات الأساسيين.

**الحالة:** ✅ الشروط الثلاثة مسجَّلة. بدء التنفيذ بـ`academy`.

---

## [2026-08-13] `academy` — الديف المجمّع المعروض للمراجعة (لسه لم يُطبَّق)

**قراءة الملف كامل** (`academy/router.py`، 612 سطر) أكَّدت: الـ36 موضع كلهم بنفس النمط الميكانيكي بالحرف، صفر استثناء — كل دالة متأثرة عندها بالفعل `current_user: User = Depends(...)` بمستوى الحماية الأصلي (`get_current_superuser`/`get_current_active_user`/`get_current_instructor_or_admin`)، فالإصلاح مجرد استبدال مصدر `tenant_id`.

### النمط الموحَّد (يُطبَّق على الـ36 كلهم)

```python
# قبل
async def create_org_entity(
    data: OrganizationEntityCreate,
    current_user: User = Depends(get_current_superuser),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db, tenant_id)
    ...

# بعد
async def create_org_entity(
    data: OrganizationEntityCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AcademyService(db, tenant_id)
    ...
```

- إزالة سطر `tenant_id: int = Depends(get_current_tenant),` من التوقيع.
- إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر في جسم الدالة.
- `current_user` موجودة بالفعل في كل الـ36 دالة بنفس مستوى الحماية الأصلي — **صفر تغيير في الصلاحيات**.
- `cast` مستوردة بالفعل (`typing import ... cast`) — صفر import جديد.
- إزالة `get_current_tenant` من سطر الاستيراد (`app.api.deps`, سطر 11).

### جدول التأكيد الكامل — 36 موضع، صفر استثناء

| الدالة | سطر الحذف | مستوى current_user | سطر الاستخدام |
|---|---|---|---|
| create_org_entity | 83 | superuser | 86 |
| create_bootcamp | 107 | active_user | 110 |
| create_track | 128 | superuser | 131 |
| create_cohort | 158 | superuser | 161 |
| create_course | 182 | active_user | 185 |
| get_courses | 192 | active_user | 197 |
| get_course_by_id | 203 | active_user | 209 |
| update_course | 219 | instructor_or_admin | 222 |
| get_store_courses | 236 | active_user | 239 |
| get_my_enrollments | 247 | active_user | 250 |
| enroll_in_course | 259 | active_user | 262 |
| enroll_in_course_simple | 276 | active_user | 279 |
| update_enrollment_progress | 293 | active_user | 296 |
| create_course_unit | 310 | instructor_or_admin | 313 |
| get_course_units | 322 | active_user | 325 |
| update_unit | 334 | instructor_or_admin | 337 |
| delete_unit | 347 | instructor_or_admin | 350 |
| create_node | 360 | instructor_or_admin | 363 |
| get_course_nodes | 372 | active_user | 375 |
| update_node | 384 | instructor_or_admin | 387 |
| delete_node | 397 | instructor_or_admin | 400 |
| create_node_live_session | 411 | instructor_or_admin | 414 |
| create_material | 425 | instructor_or_admin | 428 |
| get_materials | 435 | active_user | 438 |
| create_node_quiz | 446 | instructor_or_admin | 449 |
| upload_file | 461 | active_user | 464 |
| create_task | 486 | active_user | 489 |
| get_course_tasks | 498 | active_user | 501 |
| submit_task | 510 | active_user | 513 |
| get_task_submissions | 525 | instructor_or_admin | 528 |
| grade_student_submission | 537 | instructor_or_admin | 540 |
| get_my_submissions | 556 | active_user | 559 |
| get_instructor_stats | 569 | instructor_or_admin | 572 |
| get_financial_summary | 581 | superuser | 584 |
| get_leaderboard | 594 | active_user | 598 |
| get_my_digital_twin | 607 | active_user | 610 |

### ملاحظة جانبية اكتُشفت أثناء المراجعة (خارج نطاق الإصلاح، موثَّقة فقط)

`list_org_entities` (سطر 89-98) بتاخد `tenant_id: int` كـquery param **مباشر بلا أي `Depends`** — العميل بيحدد الـtenant صراحة في الـquery string، بلا حتى هيدر. فئة ثغرة مختلفة تمامًا (زي `invoicing.create_invoice`/`commerce.create_store` الموثَّقين سابقًا في `critical-finding-xtenant-systemic.md`) — **صفر لمس، موثَّقة بس**.

**الحالة:** ⏳ **الديف معروض، لسه لم يُطبَّق على القرص.** في انتظار موافقة المستخدم النهائية على التنفيذ.

---

## [2026-08-13] `academy` — التطبيق الفعلي + التحقق الكامل (خطوات 1-3)

### التطبيق

طُبِّق الديف المعروض بالضبط على الـ36 موضع (عبر سكريبت Python مخصَّص، بعد اختبار جاف على نسخة مؤقتة من الملف أولًا للتأكد من صحة التحويل قبل لمس الملف الحقيقي). **قراءة الملف كامل بعد التعديل (612 سطر) أكَّدت مطابقة تامة للديف المعروض** — كل الـ36 دالة بقت `tenant_id = cast(int, current_user.tenant_id)` كأول سطر في الجسم، `current_user` بنفس مستوى الحماية الأصلي بلا تغيير، `list_org_entities` متلمستش زي المتفق.

### 1) تأكيد `grep` مستقل

```
grep "get_current_tenant" academy/router.py → 0 نتيجة
```
`python -m py_compile` على الملف → `exit code: 0` (صفر أخطاء syntax).

### 2) إعادة تشغيل uvicorn — لوج نظيف

تشغيل جديد (`PYTHONIOENCODING=utf-8`، Redis متأكَّد شغال مسبقًا عبر `docker ps`). فحص كامل للوج: `Application startup complete`، **صفر `Traceback` عند الإقلاع**، نفس تحذيرات dev المعتادة (`SECRET_KEY`/`GEMINI_API_KEY` افتراضية).

### 3) التحقق الحي — 3 endpoints عبر 3 مستويات حماية مختلفة

**بيانات الاختبار:** تسجيل يوزرين حقيقيين عبر `POST /api/identity/register` (`p_academy_a` id=31 → تينانت1 الافتراضي، `p_academy_b` id=32 → تينانت1 مبدئيًا)، ترقية الاتنين لـ`SUPER_ADMIN` (تجاوز بوابة `require_sector` العامة غير المتعلقة، نفس سابقة الجلسات قبل كده)، إنشاء تينانت اختباري تاني (`academy_tenants id=14`) ونقل يوزر B ليه. تسجيل دخول الاتنين (يوزر B عبر هيدر `X-Tenant-ID: 14` وقت الـlogin تحديدًا، لأن `identity/login` بتفلتر بالتينانت من الهيدر بتصميم — سلوك SAFE موثَّق مسبقًا). بيانات إضافية throwaway: كورس واحد + منظمة تعليمية واحدة + قيد التحاق واحد (بقيم مبلغ 777.50 مميِّزة) تحت تينانت 1 — **زُرعت عبر SQL خام مباشر** (مسار الـAPI لإنشائها كان محجوبًا ببجّين منفصلين تمامًا، تفصيل تحت)، مع الحرص الصريح على استكمال كل الأعمدة اللي عندها default على مستوى الـORM بس (نفس درس Phase 16 عن NULL defaults).

**النتائج (5 اختبارات لكل endpoint: تينانت شرعي، هيدر مزوَّر لتينانت موجود، هيدر مزوَّر لقيمة عشوائية، تينانت تاني شرعي بلا هيدر، تينانت تاني + هيدر مزوَّر يدّعي التينانت الأول):**

| Endpoint | المستوى | تينانت1 (شرعي/مزوَّر14/مزوَّر999) | تينانت14 (شرعي/مزوَّر1) | الحكم |
|---|---|---|---|---|
| `GET /academy/courses` (`get_courses`) | active_user | نفس الكورس (id=1) في الثلاثة، بالحرف | `[]` في الحالتين | ✅ **الهيدر بلا أي تأثير، عزل حقيقي مؤكَّد في الاتجاهين** |
| `PUT /academy/courses/1` (`update_course`) | instructor_or_admin | 🔴 500 (باج منفصل، تفصيل تحت) | `404 "الكورس غير موجود"` في الحالتين | ✅ **جزئي — عزل الكتابة cross-tenant مؤكَّد (الاتجاه الحرج)، المسار الشرعي محجوب ببج غير متعلق** |
| `GET /academy/reports/financial` (`get_financial_summary`) | superuser | `{"total_paid": 777.5, "total_overdue": 0.0}` في الثلاثة، بالحرف | `{"total_paid": 0.0, "total_overdue": 0.0}` في الحالتين | ✅ **الهيدر بلا أي تأثير، عزل حقيقي مؤكَّد في الاتجاهين — هذا بالضبط الـendpoint اللي كان مذكور كدليل أصلي على ثغرة academy في `critical-finding-xtenant-systemic.md`** |

**تفصيل حاسم لكل حالة:** طلب بدون توكن إطلاقًا → `401` (يفرّق عن الـ`404`/النتائج الفارغة، يثبت إنها وصلت فعليًا لمنطق التطبيق بعد مصادقة ناجحة، مش رفض مصادقة).

### باجات جانبية مكتشفة أثناء التحقق (موثَّقة فقط، صفر إصلاح، خارج نطاق هذه الجلسة تمامًا)

1. **`create_org_entity`/`create_course` — باج duplicate/unexpected kwarg (فئة مشابهة لباج `sovereign_entities.create_entity` الموثَّق مسبقًا):**
   - `create_org_entity`: `OrganizationEntityCreate` سكيما بتاخد `tenant_id` في الـbody، والراوتر بيعمل `**data.model_dump()` كامل لـ`service.create_org_entity()` اللي توقيعها الحقيقي **معندهوش** بارامتر `tenant_id` أصلًا → `TypeError: got an unexpected keyword argument 'tenant_id'`، فوري، لكل طلب.
   - `create_course`: نفس الفئة لكن أخطر (duplicate بدل unexpected) — `CourseCreate` سكيما فيها `instructor_id` اختياري، و`service.create_course` بتعمل `self.repo.create_course(**data, instructor_id=instructor_id)` — لو `data` (من `model_dump()` بلا `exclude_unset`) فيها مفتاح `instructor_id` بالفعل (دايمًا موجود، حتى لو `None`)، بيبقى `TypeError: got multiple values for keyword argument 'instructor_id'` فوري، قبل أي وصول لـDB.
   - **الأثر:** منعاني من زرع بيانات الاختبار عبر الـAPI الحقيقي (خلاف التفضيل المعتاد)، فاضطريت لـSQL خام موثَّق ومحسوب بدقة بدلًا منه.
2. **`update_course` — باج caching/session detachment (فئة جديدة تمامًا، غير مرتبطة بـSimpleTenant ولا بباج الترانزاكشن):** `repository.get_course()` بترجع كائن `Course(**cached)` **معاد بناؤه من الكاش، غير مرتبط بالـsession** لو حصل cache hit. `service.update_course()` بينادي `get_course()` مرة (فحص وجود)، وبعدها `repository.update_course()` **بينادي `get_course()` تاني جواها** — النداء التاني بيلاقي الكاش اللي اتظبط تو من النداء الأول (خلال نفس الطلب) فبيرجّع الكائن المفصول عن الـsession، وأي `db.refresh(course)` بعدها بيكراش بـ`InvalidRequestError: Instance is not persistent within this Session`. **يمنع نجاح المسار الشرعي لـ`update_course` تحديدًا** (لكن مسار الرفض cross-tenant سليم 100%، لأنه بيرجع `NotFoundError` قبل ما يوصل للكود المكسور أصلًا).
3. **`academy_instructors` — انحراف schema حقيقي بين الكود والـDB:** الموديل (`models.py:75`) بيعرّف عمود `tenant_id`، لكن الجدول الفعلي في الـDB **معندوش العمود ده إطلاقًا** (تأكَّد بـ`\d academy_instructors`) — أي استعلام بيفلتر بـ`Instructor.tenant_id` (زي `get_instructor_stats`) هيكراش بـ`UndefinedColumnError`. **استُبدِل اختبار `get_instructor_stats` بـ`update_course`** لتمثيل مستوى `instructor_or_admin` بسبب الباج ده.

**كل الثلاثة باجات موجودة مسبقًا في الكود، صفر علاقة بتعديلات هذه الجلسة، صفر إصلاح — موثَّقة فقط.**

### الخلاصة

**✅ `academy` مؤكَّد حيًا بالكامل** — 3 endpoints عبر 3 مستويات حماية، الهيدر المزوَّر بلا أي تأثير في كل الحالات القابلة للاختبار، عزل حقيقي مؤكَّد في الاتجاهين (تينانت1 ما يشوفش بيانات تينانت14 والعكس) بما فيها أخطر endpoint (`get_financial_summary`، نفس الدليل الأصلي من `critical-finding-xtenant-systemic.md`). بيانات الاختبار (تينانت 14، يوزرين 31/32، كورس/منظمة/قيد التحاق تينانت1) **هتتسيب شغالة مؤقتًا لإعادة استخدامها في تحقق `commerce`/`saas`/`sovereign_entities`** بدل تكرار الإعداد من الصفر — التنظيف النهائي الشامل هيحصل في آخر الجلسة كلها (كل الأربعة دومينات)، مش دلوقتي.

**الحالة:** ✅ **`academy` مكتمل بالكامل (جرد + ديف + تطبيق + تحقق حي).** الانتقال لـ`commerce` بنفس المنهجية بالضبط.

---

## [2026-08-13] موافقة المستخدم على `academy` + تأكيد على عزل بيانات الاختبار

**موافقة صريحة على `academy` بالكامل** (الجرد، الديف، التطبيق، التحقق الحي) وعلى ترك بيانات الاختبار (تينانت14، يوزرين 31/32) شغالة لإعادة الاستخدام مع باقي الدومينات.

**شرط إضافي:** أي بيانات throwaway جديدة خاصة بـ`commerce`/`saas`/`sovereign_entities` لازم تتزرع بادئة/تسمية واضحة ومنفصلة تمامًا عن بيانات `academy` الحالية (كورس/منظمة/قيد التحاق) — بدون تداخل IDs أو أرصدة، عشان التنظيف النهائي الشامل (آخر الجلسة) يفضل واضح وآمن دومين ورا التاني.

**الحالة:** ✅ مسجَّل. سيُطبَّق حرفيًا على أي بيانات throwaway جديدة (بادئة `p_commerce_`، `p_saas_`، `p_sovereign_` حسب الدومين).

---

## [2026-08-13] `commerce` — الديف المجمّع المعروض للمراجعة (لسه لم يُطبَّق)

**قراءة الملف كامل** (`commerce/router.py`، 221 سطر) كشفت: من أصل 12 موضع، **11 بنفس النمط الميكانيكي المضبوط بتاع `academy`**، لكن **موضع واحد استثناء حقيقي** يحتاج قرار تصميمي منفصل قبل أي تطبيق.

### الاستثناء — `visa_webhook` (سطر 193-206)، بلا `current_user` إطلاقًا

هذا webhook بيتنادى من بوابة الدفع (Visa) مباشرة، مش من مستخدم مسجّل دخول — التوقيع بياخد `signature: str = Header(...)` بدل أي `Depends(get_current_active_user)`. **القاعدة الموحّدة (`cast(int, current_user.tenant_id)`) مش قابلة للتطبيق هنا حرفيًا — مفيش `current_user` أصلًا.**

```python
async def handle_visa_webhook(self, payload, signature=None, idempotency_key=None):
    order_id = cast(int, payload.get("order_id"))
    order = await self.repo.get_order(order_id, self.tenant_id)   # self.tenant_id من الهيدر حاليًا
    ...
```

`tenant_id` هنا مش بيحدد "مين الطالب" (زي باقي الـ11)، بيحدد "الطلب (`order`) ده بتاع أنهي تينانت" — والمصدر الوحيد المتاح فعليًا هو `order_id` نفسه (موجود في الـpayload). **المقترح (لسه معروض للمراجعة، مش مطبَّق):** إزالة الاعتماد على أي `tenant_id` خارجي (هيدر) بالكامل، واستبداله بجلب التينانت الحقيقي من الطلب نفسه — إضافة `get_order_by_id(order_id)` (بلا فلتر تينانت) في `repository.py`، تُستخدَم هنا فقط لاستخراج `order.tenant_id` الحقيقي قبل الاستكمال. ده أعمق من استبدال سطر — بيلمس `repository.py` كمان، مش بس `router.py`. **قرار مؤجَّل: هل يُعرض ديف كامل له الآن قبل الاستكمال، أم يُوثَّق ونُكمل الـ11 التانيين أولًا؟**

### النمط الموحّد — 11 موضع (نفس نمط `academy` بالحرف)

| الدالة | سطر الحذف | مستوى current_user | سطر الاستخدام |
|---|---|---|---|
| create_store | 26 | active_user | 29 |
| create_product | 42 | active_user | 45 |
| list_products | 58 | active_user | 62 |
| checkout | 79 | active_user | 82 |
| get_my_orders | 95 | active_user | 98 |
| set_affiliate_sponsor | 115 | active_user | 118 |
| get_my_commissions | 131 | active_user | 134 |
| release_my_commissions | 146 | active_user | 149 |
| create_payment_request | 163 | active_user | 166 |
| confirm_agent_payment | 181 | active_user | 184 |
| get_payment_status | 213 | active_user | 216 |

نفس التحويل بالضبط (إزالة `tenant_id: int = Depends(get_current_tenant),`، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم)، إزالة `get_current_tenant` من سطر الاستيراد. صفر تغيير صلاحيات (كلهم `active_user` بالفعل، أعلى مستوى موجود في الملف كله — `commerce` معندهاش أي endpoint بمستوى `superuser`/`instructor_or_admin`).

**الحالة:** ⏳ **الديف معروض، لسه لم يُطبَّق على القرص.** في انتظار قرار المستخدم بخصوص `visa_webhook` (ديف كامل الآن أم توثيق وتأجيل) وموافقة نهائية على الـ11.

---

## [2026-08-13] قرار المستخدم — موافقة على الـ11 + تأجيل `visa_webhook` رسميًا كبند أمني منفصل

**موافقة على تطبيق الـ11 موضع فورًا.**

**`visa_webhook`: تأجيل صريح، مش مجرد "SimpleTenant fix مؤجل".** توجيه المستخدم: الحل المقترح (`get_order_by_id` بلا فلتر تينانت) منطقي من ناحية `SimpleTenant` بس، **لكنه قرار أمني أعمق محتاج مراجعة مخصَّصة قبل أي تنفيذ**، لسببين صريحين:
1. هل فيه تحقق `signature` فعلي (HMAC بمفتاح Visa السري) بيحصل فعلًا قبل الوصول لمنطق الخصم؟ لو الـsignature validation نفسها مفقودة/معطوبة، ده أخطر بكتير من مصدر `tenant_id`.
2. `order_id` نفسه — هل هو قابل للتخمين (تسلسلي)؟ لو أيوه، اعتباره "مصدر ثقة وحيد" لتحديد التينانت في مسار مالي (حتى بعد إصلاح `SimpleTenant`) يفتح باب تاني للتلاعب.

**التصنيف الرسمي:** 🔴 **معلَّق — يحتاج جلسة أمنية مخصَّصة لمراجعة بوابة دفع Visa webhook بالكامل** (توقيع، تكرار، مصدر tenant_id سوا)، مش مجرد "type mismatch مؤجل". لن يُلمس في هذه الجلسة أو أي جلسة SimpleTenant تانية بدون مراجعة منفصلة.

**الحالة:** ✅ مسجَّل. بدء تطبيق الـ11.

---

## [2026-08-13] `commerce` — التطبيق الفعلي + التحقق الحي (خطوات 1-3، مكتملة)

### التطبيق

طُبِّق نفس السكريبت المستخدَم في `academy`، بعد تعديله ليتخطى تلقائيًا أي دالة بلا `current_user` في توقيعها (حماية آلية إضافية لـ`visa_webhook` فوق المراجعة اليدوية). **11 دالة اتعدَّلت بالضبط** (نفس القائمة المعروضة)، `visa_webhook` **اتخطّى تلقائيًا** (رسالة `SKIPPED` من السكريبت نفسه). سطر الاستيراد **متلمسش** (السكريبت اتأكد أولًا إن فيه استخدام واحد متبقٍّ لـ`Depends(get_current_tenant)` بسبب `visa_webhook`، فسيب `get_current_tenant` في الاستيراد بالحرف).

### 1) تأكيد `grep` مستقل
```
grep "Depends(get_current_tenant)" commerce/router.py → نتيجة واحدة بس، سطر 198 (visa_webhook، المؤجَّل رسميًا)
```
`py_compile` → `exit code: 0`.

### 2) إعادة تشغيل uvicorn — لوج نظيف
Restart كامل (`PYTHONIOENCODING=utf-8`). فحص اللوج: `Application startup complete`، صفر `Traceback` عند الإقلاع. (ملاحظة تشغيلية: السيرفر توقف بصمت مرة واحدة أثناء سلسلة الاختبارات الحية بلا أي أثر خطأ في اللوج — أُعيد تشغيله فورًا، لوج نظيف تاني، اعتُبرت عارضة تشغيلية غير متعلقة بالكود.)

### 3) التحقق الحي — 3 endpoints، تغطية "قراءة + كتابة + معاملتين ماليتين"

**بيانات الاختبار:** نفس يوزري `academy` (A=تينانت1، B=تينانت14) بالضبط بلا تعديل. بيانات throwaway جديدة خاصة بـ`commerce` (بادئة `p_commerce_` واضحة، جداول مختلفة تمامًا عن `academy` — `store_profiles`/`products`/`orders`/`payment_requests`، صفر تداخل IDs):
- `store_profiles id=1` + `products id=1` + `product_variants id=1` — **اتعملوا عبر الـAPI الحقيقي الفعلي** (`POST /commerce/stores`, `POST /commerce/products`)، تأكيد إضافي إن الإصلاح شغال من أول استدعاء.
- **إصلاح فجوة بيانات بدل زرع جديد (بتوجيه المستخدم):** `store_profiles.owner_email` كان قيمة تلقائية وهمية (`tenant_1@eppne.com`) بتمنع `finance.transfer` من إيجاد مستلم حقيقي. اتحدَّث لبريد يوزر A الحقيقي المسجَّل (`p_academy_a@example.com`) + شحن محفظة يوزر A بـ200 MR_USDT throwaway (سيناريو شراء ذاتي — نفس اليوزر بائع ومشتري، مقبول لغرض اختبار مصدر `tenant_id`/التكامل مع `finance`، مش لواقعية العمل). **النتيجة: كفت لإكمال `checkout` بالكامل، مفيش داعي لزرع بيانات إضافية لأول اختبارين.**
- `payment_requests id=1` (نوع `AGENT`) **اتزرعت عبر SQL خام** (مسار الإنشاء عبر الـAPI محجوب ببج منفصل، تفصيل تحت) — بادئة `p_commerce_`/`AG-P-COMMERCE-1` واضحة.

**النتائج:**

| Endpoint | الطبيعة | تينانت1 (شرعي/مزوَّر14) | تينانت14 (شرعي/مزوَّر1) | الحكم |
|---|---|---|---|---|
| `GET /commerce/products` (`list_products`) | قراءة | نفس المنتج (id=1) في الحالتين + هيدر عشوائي=999 | `[]` في الحالتين | ✅ **حاسم — هيدر بلا تأثير، عزل مؤكَّد بالاتجاهين** |
| `POST /commerce/checkout` | كتابة + مالية | نجاح (`order id=1` ثم `id=2` بهيدر مزوَّر14، نفس النتيجة PAID) | `404 "المتجر غير موجود أو غير نشط"` في الحالتين (شرعي/مزوَّر1) | ✅ **حاسم بالكامل — المسار السعيد اكتمل بعد إصلاح `owner_email`، والعزل cross-tenant مؤكَّد** |
| `POST /commerce/payment/agent/confirm` (`confirm_agent_payment`) | كتابة + مالية | نجاح (هيدر مزوَّر14، `order id=3` → `PAID`، مؤكَّد DB مستقل) | `404 "طلب الدفع غير موجود..."` في الحالتين (شرعي/مزوَّر1) | ✅ **حاسم بالكامل — نفس معيار `finance.transfer` الصارم (SELECT مستقل قبل/بعد)** |

**تحقق DB مستقل (مش status code) لـ`checkout`:**
```sql
orders: id=1 (بلا هيدر) → tenant_id=1, status=PAID
        id=2 (هيدر مزوَّر=14) → tenant_id=1, status=PAID   -- مطابق لـid=1 بالحرف، الهيدر اتجاهل تمامًا
transactions: id=7, sender=31, receiver=31, amount=100, COMPLETED
```

**تحقق DB مستقل لـ`confirm_agent_payment`:**
```sql
قبل: payment_requests id=1 → status=PENDING, agent_id=NULL
بعد (هيدر مزوَّر=14): payment_requests id=1 → status=PAID, agent_id=31
                       orders id=3 → tenant_id=1 (ثابت، مش 14), status=PAID
```

### باجات جانبية إضافية اتكشفت (موثَّقة فقط، صفر إصلاح)

1. **`create_payment_request` — نفس فئة باج duplicate-kwarg (الرابعة من نوعها في الجلسة، بعد `academy.create_course`، `sovereign_entities.create_entity`، `academy.create_org_entity`):** `service.py:355` — `self.repo.create_payment_request(self.tenant_id, **pr_data)`، و`pr_data` (المبني في نفس الدالة) **فيه مفتاح `tenant_id` بالفعل** (`pr_data["tenant_id"] = self.tenant_id`, سطر 342) → `TypeError: got multiple values for argument 'tenant_id'`، فوري، **لأي `payment_method`** (مش بس AGENT). **يمنع `create_payment_request` بالكامل** — هو سبب زرع `payment_requests` عبر SQL خام بدل الـAPI.
2. **شذوذ رصيد ملحوظ أثناء اختبار `checkout` الذاتي (سيناريو مصطنع، مش تمثيلي):** محفظة يوزر A كانت 200 MR_USDT، بعد تحويل ذاتي (نفس اليوزر بائع ومشتري) بقيمة 100 اتوقع تفضل 200 (خصم ثم إضافة لنفس المحفظة) لكن طلعت 300. **مش اتفحص بعمق** — على الأرجح `finance.transfer` بتاخد نسخة واحدة من رصيد المحفظة في الذاكرة قبل أي تعديل، وتستخدمها في عمليتي الخصم والإضافة منفصلين بدل قراءة القيمة المُحدَّثة بينهم، فبيحصل تراكم غير صحيح في حالة "المرسل = المستلم" تحديدًا. **حالة حافة نادرة جدًا (تحويل ذاتي حقيقي نادر في الإنتاج)، صفر علاقة بـ`SimpleTenant`، خارج النطاق تمامًا — موثَّقة فقط لأنها ظهرت أثناء الاختبار.**
3. **`list_products`/`create_product` response لا يُرجع `variants`** رغم إنها اتسجَّلت صح في الـDB (مؤكَّد بـSELECT مباشر) — ملاحظة serialization بسيطة، pre-existing، خارج النطاق.

### الخلاصة

**✅ `commerce` مؤكَّد حيًا بالكامل — 11/11 endpoint، 3 endpoints عبر 3 طبائع مختلفة (قراءة، كتابة+مالية مباشرة، كتابة+مالية عبر وكيل)، الهيدر المزوَّر بلا أي تأثير في كل الحالات، عزل حقيقي مؤكَّد بالاتجاهين، معياري التحقق الصارم (SELECT مستقل) مُطبَّق على الاثنين الماليين.** `visa_webhook` مؤجَّل رسميًا كبند أمني منفصل (راجع فوق). بيانات throwaway (`store_profiles`, `products`, `product_variants`, `orders` ×3, `transactions`, `payment_requests`) هتفضل شغالة للتنظيف النهائي الشامل آخر الجلسة.

**الحالة:** ✅ **`commerce` مكتمل بالكامل (جرد + ديف + تطبيق + تحقق حي).** الانتقال لـ`saas` بنفس المنهجية — تذكير: `pay_invoice` معاملة مالية، نفس معيار `finance.transfer` الصارم مطلوب.

---

## [2026-08-13] موافقة نهائية على `commerce` + رفع مستوى توثيق ملاحظتين

**موافقة كاملة على `commerce`.** توجيه إضافي: رفع مستوى توثيق ملاحظتين من القسم السابق —

### 🔴 شذوذ رصيد `finance.transfer` عند تحويل ذاتي (sender == receiver) — أعلى أولوية توثيق

اتصادف أثناء اختبار `checkout` (محفظة يوزر A: 200 → متوقَّع 200 بعد تحويل ذاتي 100 → طلعت **300 فعليًا**). **السبب الأرجح (غير مؤكَّد بالكامل، محتاج تحقيق منفصل لو حصل قرار بمتابعته):** `finance.transfer` غالبًا بتقرا رصيد المحفظة **نسخة واحدة في الذاكرة** قبل أي تعديل، وتستخدم نفس النسخة القديمة في عمليتي الخصم والإضافة بدل قراءة القيمة المُحدَّثة بينهم — فبيحصل تراكم غلط لما `sender_id == receiver_id`. **حالة حافة نادرة (تحويل ذاتي حقيقي شبه مستحيل في الإنتاج العادي)، لكنها ثغرة محاسبية محتملة تستاهل تسجيل صريح كـ"دين تقني مكتشف" منفصل — خارج نطاق `SimpleTenant` بالكامل، صفر علاقة بأي تعديل في هذه الجلسة، لم تُحقَّق بعمق ولم تُصلَح.**

### 🟠 فئة باج duplicate-kwarg (`got multiple values for keyword argument`) — نمط منهجي متكرر، مش نقطة معزولة

اتكشفت **4 مرات منفصلة** خلال هذه الجلسة وحدها، في دومينات وmethods مختلفة تمامًا:
1. `academy.create_org_entity` (`service.create_org_entity(**data.model_dump())` — `tenant_id` زيادة غير متوقَّعة في التوقيع)
2. `academy.create_course` (`self.repo.create_course(**data, instructor_id=instructor_id)` — `instructor_id` مكرر)
3. `sovereign_entities.create_entity` (موثَّق مسبقًا في `PROGRESS_LOG.md` قبل هذه الجلسة — `tenant_id` مكرر)
4. `commerce.create_payment_request` (`self.repo.create_payment_request(self.tenant_id, **pr_data)` — `tenant_id` مكرر)

**النمط المشترك في الأربعة:** دالة service بتبني `dict` كامل البيانات (يشمل `tenant_id`/معرف آخر) ثم بتنادي الـrepository بتمرير **نفس المفتاح مرتين** — مرة جوه الـdict (`**data`) ومرة تانية صريحة كـkwarg منفصل. بايثون بترفض ده فورًا وقت الاستدعاء (`TypeError`)، بغض النظر عن توقيع الـcallee. **مش صدفة متفرقة — نمط برمجي متكرر عبر أكتر من دومين ومطوّر، يستاهل جرد منهجي مخصَّص شبيه بجرد `get_current_tenant` نفسه في جلسة منفصلة مستقبلية** (مش الآن، خارج نطاق هذه الجلسة، لكن موثَّق هنا بوضوح كفئة، مش كأربع ملاحظات معزولة).

**الحالة:** ✅ الرفع اتنفَّذ. الانتقال لـ`saas`.

---

## [2026-08-13] `saas` — الديف المجمّع المعروض للمراجعة (لسه لم يُطبَّق)

**قراءة الملف كامل** (`saas/router.py`، 275 سطر) — **17 موضع بنفس النمط الميكانيكي المضبوط بلا استثناء واحد** (كل الـ17 عندها `current_user` بالفعل بمستوى الحماية الأصلي). **2 endpoints تانيين في نفس الملف لا علاقة لهم بـ`get_current_tenant` إطلاقًا** — موثَّقين هنا للوضوح بس، صفر تعديل عليهم.

### النمط الموحّد — 17 موضع

| الدالة | سطر الحذف | مستوى current_user | سطر الاستخدام |
|---|---|---|---|
| list_services | 28 | superuser | 31 |
| create_service | 40 | superuser | 43 |
| get_service | 53 | active_user | 56 |
| list_service_plans | 68 | active_user | 71 |
| create_plan | 80 | superuser | 83 |
| get_my_subscriptions | 98 | active_user | 101 |
| subscribe_to_plan | 110 | active_user | 113 |
| cancel_subscription | 122 | active_user | 125 |
| get_subscription_status | 134 | active_user | 137 |
| get_services_access | 148 | active_user | 151 |
| check_service_access | 159 | active_user | 162 |
| get_my_invoices | 176 | active_user | 179 |
| get_invoice | 187 | active_user | 190 |
| **pay_invoice** | 199 | active_user | 202 | ⚠️ **معاملة مالية — تحقق حي بمعيار `finance.transfer` الصارم بعد التطبيق** |
| list_feature_flags | 214 | superuser | 217 |
| toggle_feature_flag | 229 | superuser | 232 |
| get_saas_dashboard | 257 | superuser | 260 |

نفس التحويل الميكانيكي بالحرف (إزالة سطر `Depends(get_current_tenant)`، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم)، إزالة `get_current_tenant` من سطر الاستيراد.

### endpoints خارج النطاق تمامًا (لا يستخدمان `get_current_tenant`، موثَّقين للوضوح فقط)

- **`get_tenant_subscriptions_admin`** (`/admin/tenant/{tenant_id}/subscriptions`, سطر 241-250): `tenant_id: int = Path(...)` — بارامتر مسار صريح (مش هيدر، مش `Depends`)، يسمح لسوبريوزر بالاستعلام عن **أي تينانت بالـID** مباشرة في الرابط. تصميم إداري صريح (Cross-tenant admin view)، مش ثغرة header-spoofing من نفس فئة `SimpleTenant` — **خارج نطاق هذه الجلسة بالكامل، صفر لمس**. (ملاحظة: يستاهل سؤال منتجي مشابه للي اتسجَّل في `critical-finding-xtenant-systemic.md` عن `finance` — "هل أي سوبريوزر من أي tenant يُفترض يشوف بيانات تينانت تاني عبر ID صريح؟" — مش قرار هذه الجلسة.)
- **`trigger_renewals`** (`/admin/trigger-renewals`, سطر 265-274): `SaaSControlService(db, 0)` بمعامل `0` هاردكودد صراحة (بتعليق فسّرها: "نمرر tenant_id=0 مؤقتاً")، و`tenant_id` الحقيقي (اختياري) بيتبعت منفصل كـargument لـ`service.trigger_renewals(tenant_id)` — مهمة نظامية عبر كل التينانتس (batch job)، مش مربوطة بـ`current_user` أصلًا بتصميمها. **خارج نطاق هذه الجلسة، صفر لمس.**

**الحالة:** ⏳ **الديف معروض، لسه لم يُطبَّق على القرص.** في انتظار موافقتك للتطبيق.

---

## [2026-08-13] `saas` — التطبيق الفعلي + التحقق الحي (مكتمل)

### التطبيق
طُبِّق نفس السكريبت (17 دالة، اختبار جاف أولًا ثم الملف الحقيقي). **17/17 مطابقين للجدول المعروض بالحرف**، الاستثناءان (`get_tenant_subscriptions_admin`, `trigger_renewals`) **متلمسوش** (تأكَّد بقراءة الملف بعد التعديل).

### 1) `grep` مستقل + `py_compile`
```
grep "get_current_tenant" saas/router.py → 0 نتيجة
```
`py_compile` → `exit code: 0`.

### 2) إعادة تشغيل uvicorn
**عائق تشغيلي (غير متعلق بالكود):** أول محاولة `restart` بعد إيقاف العملية القديمة اكتشفت إن **عملية uvicorn قديمة من اختبار `commerce` كانت لسه شغالة وماسكة بورت 8000** (توقفها الصامت المُلاحَظ سابقًا لم يكن توقفًا فعليًا) — أي طلب كان بيوصل لنسخة قديمة من الكود (قبل إصلاح `saas`) بدون أي ظهور خطأ. اتحل بإيقاف العمليتين القديمتين يدويًا والتأكد من فراغ البورت قبل التشغيل الجديد. **لوج الإقلاع النهائي نظيف تمامًا** (`Application startup complete`، صفر `Traceback`).

**درس مُسجَّل:** من الآن، أي `restart` لازم يتأكد أولًا (`Get-NetTCPConnection`) إن البورت فاضي فعليًا قبل التشغيل، مش الاعتماد على افتراض إن العملية القديمة ماتت.

### 3) التحقق الحي — 2 endpoints حاسمين (active_user + superuser) + محاولة `pay_invoice` (موثَّقة، محجوبة)

**بيانات throwaway جديدة** (بادئة `p_saas_` واضحة، منفصلة عن `academy`/`commerce`): `saas_service_catalog id=1` ("p_saas_service_A") + `saas_service_plans id=1` ("p_saas_plan_A") — **اتعملوا عبر الـAPI الحقيقي** (`POST /saas/services`, `POST /saas/plans`، الاثنان من الـ17 المُصلَحين).

**`toggle_feature_flag` (superuser، كتابة) + `list_feature_flags` (superuser، قراءة) — اختبار كامل حاسم:**
- تفعيل `beta_access` لخدمة `P_SAAS_SVC_A` عبر الـAPI الحقيقي (User A، بلا هيدر) → نجاح، `tenant_id=1` في الـresponse (مصدره `current_user.tenant_id` الآن، لا الهيدر).
- `list_feature_flags`: User A (بلا هيدر / هيدر مزوَّر=14 / هيدر مزوَّر=999) → **نفس النتيجة بالحرف (فلاج واحد، تينانت1) في الثلاثة**. User B (تينانت14، بلا هيدر / هيدر مزوَّر=1) → **`[]` في الحالتين، بلا تسريب**. ✅ **حاسم، 5/5.**

**`get_my_subscriptions` (active_user، قراءة) — اختبار كامل حاسم بعد عائق:**
- محاولة أولى فارغة (`total=0`، صحيح، مفيش اشتراك بعد) — ثم اكتشاف إن `subscribe_to_plan` (مسار الإنشاء الطبيعي) **محجوب ببج منطقي منفصل تمامًا** (تفصيل تحت)، فاتزرع اشتراك throwaway واحد عبر SQL خام مباشر (تينانت1، بادئة واضحة، بعد تصحيح أعمدة NULL-default غلط زرعتها بنفسي أول مرة — نفس درس Phase 16، اتصلح فورًا).
- بعد الزرع: User A (بلا هيدر / مزوَّر14 / مزوَّر999) → **نفس النتيجة بالحرف (اشتراك واحد) في الثلاثة**. User B (بلا هيدر / مزوَّر1) → **`total=0` في الحالتين، بلا تسريب**. ✅ **حاسم، 5/5.**

**`pay_invoice` — محاولة صريحة، محجوبة بالكامل ببج pre-existing، موثَّقة بالتفصيل (مش تم تجاوزها بصمت):**
1. أول محاولة زرع فاتورة استخدمت جدول غلط (`invoices` — بتاع دومين `invoicing` مختلف تمامًا، غلطة زرع مني) — اتصححت (`DELETE`) فور اكتشافها عبر رسالة خطأ SQL واضحة (`saas_invoices.idempotency_key does not exist`، أثناء محاولة قراءة الفاتورة من الجدول الصح).
2. **الاكتشاف الحقيقي:** الجدول الصحيح (`saas_invoices`) **معندوش عمود `idempotency_key` أصلًا في الـDB**، رغم إن الموديل/الاستعلام (`repository.py`) بيتوقعه دايمًا — **انحراف schema حقيقي بين الكود والـDB** (نفس فئة `academy_instructors.tenant_id` المكتشفة في `academy`) — أي استعلام `SELECT` على `saas_invoices` (`get_invoice`, وبالتبعية `pay_invoice`) **هيكراش دايمًا، لأي تينانت، بغض النظر عن أي بيانات اختبار أو أي تعديل بتاعنا**.
3. **ملاحظة تصميمية إضافية مكتشفة بالقراءة (لم تُختبَر حيًا لأن #2 بيمنع الوصول أصلًا):** `service.py:302-303` — `pay_invoice` بتنادي `finance.transfer(sender_id=self.tenant_id, ...)` — **`sender_id` هنا هو الـ`tenant_id` نفسه، مش أي `user_id` حقيقي**. `finance.transfer` بتتوقع `sender_id` يكون معرف مستخدم (لتحديد محفظته)، فتمرير `tenant_id` (مثلًا `1`) بيعني البحث عن محفظة "يوزر رقم 1" — لو معندوش يوزر بالـid ده أصلًا (مؤكَّد، `SELECT` مباشر رجع صفر صفوف)، هيفشل بـ`NotFoundError` حتى لو انحراف الـschema اتصلح. **باج تصميمي محتمل ثانٍ منفصل تمامًا، غير مؤكَّد بالكامل (محجوب خلف #2)، موثَّق كملاحظة فقط.**

**النتيجة الرسمية لـ`pay_invoice`:** 🔴 **غير قابلة للتحقق الحي إطلاقًا حاليًا** — محجوبة ببجّين pre-existing منفصلين تمامًا (انحراف schema مؤكَّد + تصميم `sender_id` مشكوك فيه)، **صفر علاقة بـ`SimpleTenant`**. الكود الخاص بمصدر `tenant_id` نفسه (`cast(int, current_user.tenant_id)`) **مُطبَّق وصحيح شكليًا** (مطابق لباقي الـ16)، لكن التحقق الحي الحاسم (المعيار الصارم المطلوب) **غير ممكن فعليًا في الوضع الحالي للكود** — موثَّق بصراحة كفجوة تحقق، مش كنجاح مُفترَض.

### باج جانبي إضافي — `subscribe_to_plan` (فئة جديدة: انعكاس منطقي، مش duplicate-kwarg ولا schema drift)
`repository.py:55-70` (`get_plan_by_id`) — التعليق بيقول "جلب الخطة والتحقق من اشتراك نشط"، لكن الاستعلام الفعلي بيدوّر بس على **اشتراك (`TenantSubscription`) موجود بالفعل** بنفس `plan_id`+`tenant_id`+حالة (`ACTIVE`/`TRIAL`) — **مفيش أي استعلام يجيب الخطة (`ServicePlan`) نفسها من الأساس**. يعني أول محاولة اشتراك لأي تينانت في أي خطة (لسه معندوش اشتراك) **هترجع "الخطة غير موجودة" دايمًا** — تناقض منطقي: بيتطلب اشتراك موجود مسبقًا عشان يسمح بإنشاء اشتراك جديد. **يمنع `subscribe_to_plan` بالكامل، لأي تينانت، بغض النظر عن `SimpleTenant`.** موثَّق فقط، صفر إصلاح.

### الخلاصة
**✅ `saas`: 17/17 موضع مُصلَح ومؤكَّد `grep`+`py_compile`. 2 endpoints حاسمين مؤكَّدين حيًا بالكامل (`list_feature_flags` سوبريوزر كتابة+قراءة، `get_my_subscriptions` active_user) — الهيدر بلا أي تأثير، عزل حقيقي بالاتجاهين في الحالتين.** `pay_invoice` (الأهم أمنيًا/ماليًا) **محجوبة بالكامل عن التحقق الحي** ببجّين pre-existing منفصلين (schema drift مؤكَّد + تصميم sender_id مشكوك فيه) — الكود مُصلَح شكليًا، لكن **لا يوجد دليل تشغيلي فعلي**، موثَّق كفجوة صريحة. `subscribe_to_plan` كمان محجوب ببج منطقي pre-existing منفصل. 3 دومينات مؤكَّدين حيًا بالكامل + رابع (`saas`) مُصلَح ومؤكَّد جزئيًا بصدق.

**الحالة:** ✅ **`saas` مكتمل (جرد + ديف + تطبيق + تحقق حي جزئي صادق).** الانتقال لآخر دومين: `sovereign_entities` — **تذكير مُسجَّل: `create_entity` هيفضل غير قابلة للتحقق الحي حتى بعد إصلاح `SimpleTenant`، بسبب باج duplicate-kwarg المتراكب فيها (موثَّق مسبقًا في `PROGRESS_LOG.md` قبل هذه الجلسة) — باقي الـ21 موضع في نفس الدومين هيتصلحوا ويتحقق منهم عادي.**

---

## [2026-08-13] `sovereign_entities` — الجرد كشف تعقيد أكبر من المتوقَّع (5 استثناءات، مش استثناء واحد زي `commerce`)

**قراءة الملف كامل** (`sovereign_entities/router.py`، 369 سطر) كشفت: من أصل 22 موضع، **17 بالنمط الميكانيكي المضبوط** (شامل `create_entity`، مؤجَّلة عن التحقق الحي بس مش عن الإصلاح)، لكن **5 استثناءات حقيقية**:

- `list_entities` (41-48), `get_entity` (72-77), `list_templates` (339-343), `list_components` (349-353) — **بلا أي `Depends` مصادقة إطلاقًا في توقيعها**.
- `get_entity_page` (211-220) — `current_user: Optional[User] = Depends(get_current_user_optional)` (تصميم عام مقصود صراحة).

### استيضاح المستخدم بخصوص الأربعة الأولى — تحقيق فوري، مش افتراض

بتوجيه المستخدم: اتقرا الكود الفعلي (فلترة SQL موجودة فعلًا)، اتفحص `critical-finding-xtenant-systemic.md` (الأربعة غير مذكورين إطلاقًا)، واتكتب تقرير Escalation منفصل بارز جدًا. **تفاصيل كاملة، مصححة بعد اختبار حي فعلي (نقطتان مهمتان اتصححوا بعد ما كنت افترضتهم غلط في التوثيق الأول):**

1. **مش "بلا أي مصادقة" فعليًا** — `main.py:300-305` بيلف كل الراوترز بـ`Depends(require_sector(sector))`، واللي بتتطلب `current_user` صالح داخليًا (`security.py:211`). تأكَّد حيًا: طلب بلا توكن → `401`.
2. **مش "أي حد"** — أي مستخدم عادي (`sector=None` دايمًا، موثَّق مسبقًا) هيترفض، **الاستثناء الوحيد `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`**.
3. **🔴 الأهم: الثغرة "كامنة" حاليًا مش "حية"** — اختبار حي فعلي (User B، `SUPER_ADMIN` حقيقي تينانت14، هيدر مزوَّر تينانت1) رجّع **`500` (نفس كراش `SimpleTenant` الأصلي)، مش تسريب ناجح** — لأن الأربعة دول **لسه فيهم باج `SimpleTenant` نفسه غير مُصلَح عمدًا**. **بمجرد إصلاح الكراش ده بأي طريقة سطحية (بديهية، سهلة الوقوع فيها)، الاستغلال هيشتغل فورًا** — لأن مفيش أي ربط بين تينانت الطالب الحقيقي والتينانت المطلوب.

**تقرير Escalation مخصَّص كامل (endpoints، مثال curl حقيقي، الحقول الحساسة من `schemas.py`):** `.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md`.

**قرار المستخدم النهائي:** صفر إصلاح على الأربعة دول في أي جلسة قادمة إلا بقرار منتجي صريح (عام بتصميم مع مراجعة الحقول المُرجَعة، أم محمي بـ`current_user` إجباري) — **تحذير إلزامي بارز جدًا أُضيف في أعلى `.claude/plans/critical-finding-xtenant-systemic.md` نفسه** لمنع أي جلسة `SimpleTenant` مستقبلية من "تصليح" الأربعة دول بالنمط المعتاد بدون قراءة التحذير أولًا.

**`get_entity_page`:** اتسيبت زي ما هي (السكريبت اتعدَّل عشان يتخطاها تلقائيًا — current_user فيها Optional، فلو اتطبَّق النمط الأعمى كان هيكراش `AttributeError` لأي زائر مجهول).

---

## [2026-08-13] `sovereign_entities` — التطبيق (17 موضع) + التحقق الحي

### التطبيق
السكريبت اتعدَّل عشان يتخطى تلقائيًا أي دالة `current_user` فيها مفقودة **أو `Optional`**. اختبار جاف أولًا (17 معدَّلة، 5 متخطاة بالحرف زي المتوقَّع) ثم التطبيق الحقيقي — مطابق تمامًا.

**1) `grep` مستقل:** `Depends(get_current_tenant)` → **5 نتائج بالضبط** (أسطر 46, 75, 215, 341, 351 — الخمسة المؤجَّلة، صفر زيادة). `py_compile` → `exit code: 0`.

**2) إعادة تشغيل uvicorn — القاعدة الجديدة الإلزامية (تأكيد فعلي إن البورت فاضي قبل أي `restart`) مُطبَّقة لأول مرة:** اكتشفت فعليًا عملية قديمة (من اختبار `saas`) لسه ماسكة البورت رغم "توقفها الصامت" المُلاحَظ سابقًا — اتوقفت يدويًا، تأكيد صريح "PORT 8000 CONFIRMED FREE"، وتأكيد إضافي بعد الإقلاع إن الـPID الماسك للبورت يطابق PID الإقلاع في اللوج. لوج نظيف تمامًا.

### 3) التحقق الحي

**بيانات throwaway** (بادئة `p_sovereign_`): `sovereign_entities_v2 id=2` + `entity_representatives id=2` (User A، `OWNER`) — عبر SQL خام (مسار الـAPI محجوب ببج `create_entity` المعروف).

| Endpoint | الطبيعة | النتيجة |
|---|---|---|
| `GET /sovereign-entities/me` (`get_my_entities`) | active_user، قراءة | ✅ **حاسم 5/5** |
| `PUT /sovereign-entities/{id}/kyb/status` (`review_kyb`) | superuser، كتابة | ✅ عزل cross-tenant حاسم. ⚠️ **اكتُشف بج منفصل — تفصيل تحت** |
| `POST /sovereign-entities/{id}/deposit` (`deposit_to_entity`) | مالية، كتابة | 🟡 عزل جزئي (فحص صلاحية بيسبق فحص التينانت) + محجوب ببج `audit_log()` |
| `POST /sovereign-entities/{id}/transfer` (`transfer_from_entity`) | مالية، كتابة | ✅ عزل cross-tenant حاسم (فحص تينانت-scoped أولًا) + محجوب بنفس بج `audit_log()`، **رولباك الأرصدة مؤكَّد سليم 100%** |

### باج جانبي — `audit_log()` توقيع غير متطابق
`service.py:377,444` بينادوا `audit_log(..., tenant_id=..., resource_id=...)`، لكن `core/audit.py:12-17` الحقيقي `(action, user_id=None, details=None, ip_address=None)` — **مفيهوش `tenant_id`/`resource_id`** → `TypeError` فوري. يمنع `deposit_to_entity`/`transfer_from_entity` عن النجاح الظاهري، **لكن أثبت السلامة المالية للسـavepoint** (رولباك كامل ونظيف).

### 🔴🔴 اكتشاف حرج ثانٍ — `review_kyb`/`update_entity` بيفقدوا الكتابة صامتًا (regression من جلسة الترانزاكشن السابقة)

`SELECT` مستقل بعد `review_kyb`/`update_entity` أظهر: الـAPI بيرجّع نجاح بالقيمة الجديدة، الـDB بيفضل بالقديمة. **السبب:** `repo.update_entity` بقت `flush()`-only (تعديل صحيح من الجلسة السابقة)، لكن الـservice methods دي **معندهاش `begin_nested()` أصلًا** فمحصلش لها `commit()` صريح. **تفاصيل كاملة + فحص موسَّع (وسّعناه لباقي الـ3 دومينات بتوجيه المستخدم) في `PROGRESS_LOG.md`.**

**الفحص الموسَّع (10 دقايق، بتوجيه المستخدم، عبر `flush()`-only grep في الأربعة `repository.py` + تتبّع كل caller):**
- `academy`: ✅ نظيف (موضع واحد، `enroll`، ملفوف صح).
- `commerce`: ✅ نظيف (مؤكَّد تجريبيًا من اختبارات هذه الجلسة).
- `sovereign_entities`: 🔴 حالتان (`review_kyb`, `update_entity`).
- `saas`: 🔴🔴 **3 حالات إضافية** (`cancel_subscription` — بلا `begin_nested`/`commit` إطلاقًا؛ `process_auto_renewals`'s فرع `except InsufficientBalanceError`؛ `can_access_service`'s تحديث `EXPIRED`) — تأكيد بالقراءة بس، مش DB-level بعد.

**توصية المستخدم المسجَّلة:** هذا الاكتشاف (regression يمس جلسة سابقة كانت مُعتبَرة مقفولة) **يستاهل أولوية جلسة عاجلة، أعلى من جلسة duplicate-kwarg المقترَحة سابقًا.**

### الخلاصة

**✅ `sovereign_entities`: 17/22 موضع مُصلَح (شامل `create_entity`، غير مُختبَر حيًا) ومؤكَّد `grep`+`py_compile`. `get_my_entities` حاسم بالكامل. `transfer_from_entity` حاسم في عزل cross-tenant. `review_kyb` حاسم في العزل لكن كشف regression خطير. `deposit_to_entity` عزل جزئي.** 5 مواضع مؤجَّلة عمدًا (4 endpoints بلا مصادقة + `get_entity_page` العامة بتصميم) — **تحذير بارز مُضاف لمنع أي إصلاح مستقبلي ساذج**. اكتشافان حرجان إضافيان (regression الكتابة الصامتة + الأربعة endpoints) موثَّقان بشكل بارز جدًا، خارج نطاق `SimpleTenant` بالكامل، صفر إصلاح على أي منهما.

**الحالة:** ✅ **الدومينات الأربعة (`academy`, `commerce`, `saas`, `sovereign_entities`) مكتملة من ناحية جرد + ديف + تطبيق + تحقق حي.** التالي: إغلاق الجلسة الكامل.

---

## [2026-08-13] تصعيد فوري — تقرير Escalation منفصل + تصحيح ذاتي بعد اختبار حي + تحذير في الملف المرجعي

بتوجيه صريح من المستخدم، اتكتب تقرير قائم بذاته (`CRITICAL-sovereign-entities-unauthenticated-endpoints.md`) لقضية الأربعة endpoints، منفصل عن هذا التقرير — يشمل file:line الدقيقة، الحقول الحساسة من `schemas.py`، ومثال curl حقيقي.

**أثناء إعداد المثال الحي، اتكشف تصحيحان مهمان (بعد اختبار فعلي، مش قراءة كود بس):**
1. الأربعة endpoints **مش بلا مصادقة إطلاقًا** — `require_sector` (مربوطة على مستوى تسجيل الراوتر في `main.py:300-305`) بتتطلب توكن JWT صالح كحد أدنى (مؤكَّد: طلب بلا توكن → `401`). الاستغلال الفعلي محصور في `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` (المستخدمين العاديين بيترفضوا دايمًا لأن `sector` مش بيتبعت في التوكن أصلًا).
2. **الأهم:** الثغرة **"كامنة" حاليًا مش "حية"** — محاولة استغلال حقيقية (SUPER_ADMIN تينانت14، هيدر مزوَّر تينانت1) رجّعت `500` (نفس كراش `SimpleTenant` الأصلي، لسه غير مُصلَح فيهم عمدًا) **مش تسريب ناجح**. بمجرد إصلاح الكراش ده بأي طريقة سطحية، الاستغلال هيشتغل فورًا.

**التصحيحان اتطبّقا فورًا على `PROGRESS_LOG.md` (تصحيح الادّعاء الأصلي "أي زائر مجهول") قبل ما يتقروا كنهائيين.**

**بتوجيه المستخدم النهائي:** تحذير إلزامي بارز جدًا (🔴🔴🔴) أُضيف في **أعلى `.claude/plans/critical-finding-xtenant-systemic.md` نفسه** (مش بس تقرير الجلسة) — يمنع أي جلسة `SimpleTenant`/X-Tenant-ID مستقبلية (حتى بسياق/شخص مختلف) من "تصليح" الأربعة دول بالنمط الميكانيكي المعتاد بدون قراءة التحذير والتقرير المخصَّص أولًا. **صفر إصلاح على الأربعة endpoints — قرار منتجي معلَّق لجلسة مخصَّصة.**

---

## [2026-08-14] الفحص الموسَّع لـregression الكتابة الصامتة — تحقق DB-level إضافي على `saas.cancel_subscription`

بطلب المستخدم (أعلى أثر مباشر على العميل من بين الحالات الخمس المكتشفة)، اتعمل تحقق DB-level كامل على `cancel_subscription` تحديدًا قبل إغلاق الجلسة:

```
قبل: saas_tenant_subscriptions id=1 → status=ACTIVE
طلب: PUT /api/saas/subscriptions/1/cancel → 200 {"status": "CANCELLED"}
بعد (SELECT مستقل فوري): saas_tenant_subscriptions id=1 → status=ACTIVE  -- ❌ لم يتغيّر إطلاقًا
```

**مؤكَّد DB-level بشكل قاطع** — نفس فئة `review_kyb`/`update_entity` بالحرف. **الحالتان الباقيتان من الخمس** (`process_auto_renewals`'s فرع `except`, `can_access_service`) **لسه مؤكَّدتين بقراءة الكود بس، مش DB-level** — التمييز موثَّق بدقة في `PROGRESS_LOG.md` (جدول مخصَّص، عمود "مستوى التأكيد" لكل حالة) تفاديًا لخلط درجات اليقين المختلفة. القسم الموحَّد الكامل لنمط "regression الكتابة الصامتة" (5 حالات، توصية بجلسة عاجلة منفصلة أعلى أولوية من duplicate-kwarg) موجود في `PROGRESS_LOG.md`.

---

## [2026-08-14] إغلاق الجلسة — Sweep نهائي + إعادة تشغيل + تنظيف شامل + Commit

### 1. Sweep نهائي (`grep` + `py_compile` على الأربعة ملفات)

```
academy/router.py:            0 نتيجة لـ Depends(get_current_tenant)
commerce/router.py:           1 نتيجة (سطر 198، visa_webhook، مؤجَّل رسميًا)
saas/router.py:                0 نتيجة
sovereign_entities/router.py: 5 نتيجة (list_entities, get_entity, get_entity_page, list_templates, list_components — مؤجَّلة رسميًا)
```
مطابق تمامًا للمتوقَّع، صفر انحراف. `python -m py_compile` على الأربعة ملفات معًا → `exit code: 0`.

### 2. إعادة تشغيل نهائية للتحقق

تأكيد فعلي إن البورت 8000 فاضي قبل التشغيل (القاعدة الإلزامية)، تشغيل نظيف، تأكيد PID الاستماع مطابق للوج، **صفر `Traceback`/`[ERROR]`/`[CRITICAL]`**. السيرفر التجريبي أُوقف بعد التحقق النهائي.

### 3. تنظيف بيانات throwaway — الأربعة دومينات دفعة واحدة + تحقق مستقل شامل

**عائق تقني اتعلّم منه أثناء التنفيذ:** أول محاولتي حذف متعددة الأوامر عبر `psql -c "DELETE...; DELETE...;"` فشلت جزئيًا (FK constraint غير متوقَّعة — `commerce_audit_logs`, `store_profiles` تحت تينانت14, `audit_logs`)، واكتشفت إن **كل استدعاء `-c` بعبارات متعددة بيتنفذ كترانزاكشن واحدة ضمنية — فشل عبارة واحدة بيرجّع كل العبارات التانية في نفس الاستدعاء**، حتى اللي ظهرت "DELETE N" ناجحة. اتأكَّد بإعادة فحص الحالة الفعلية بعد كل محاولة فاشلة (مش الاعتماد على مخرجات `DELETE N` وحدها)، واتصلح بترتيب الحذف الصحيح حسب الـFK (`entity_representatives` → `sovereign_entities_v2` → `payment_requests` → `commerce_audit_logs` → `order_items` → `orders` → `transactions` → `product_variants` → `products` → `store_profiles` → `saas_*` (4 جداول) → `academy_enrollments` → `academy_courses` → `organization_entities` → `audit_logs` → `wallets` → `users(32)` → `academy_tenants(14)` → `users(31)`).

**تحقق مستقل نهائي — 20 استعلام `SELECT COUNT`، كلهم صفر:** users(31,32), wallets, academy_tenants(14), academy_courses(1), organization_entities(1), store_profiles(1,2), products(1), product_variants(1), orders(1,2,3), order_items, commerce_audit_logs, payment_requests(1), transactions(7,8), saas_service_catalog(1), saas_service_plans(1), saas_tenant_subscriptions(1), saas_tenant_feature_flags(1), sovereign_entities_v2(2), entity_representatives(2), audit_logs(31,32).

**تحقق إضافي — حالة `academy_tenants` النهائية:** صف واحد بس (`id=1, "Local Test Tenant"`) — **مطابق تمامًا لحالة البداية قبل أي نشاط في هذه الجلسة**، صفر أثر متبقٍّ.

### 4. الملفات المُضافة للـcommit (بعد `git status`، طبقًا لمبدأ "الملفات المتعلقة بس" المتّبع في كل الجلسات السابقة)

**مُعدَّلة:**
- `eppne-backend/app/domains/academy/router.py`
- `eppne-backend/app/domains/commerce/router.py`
- `eppne-backend/app/domains/saas/router.py`
- `eppne-backend/app/domains/sovereign_entities/router.py`
- `.claude/plans/critical-finding-xtenant-systemic.md` (التحذير المُضاف)
- `PROGRESS_LOG.md`

**جديدة:**
- `.claude/reports/simpletenant-fix-session-log.md` (هذا الملف)
- `.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md`

**لم تُلمس (ملفات معلَّقة من جلسات تانية، تأكَّدت بـ`git status`/`git diff` إنها مش من تعديلاتي):** `.claude/reports/phase16-session-log.md`, `.claude/reports/transaction-savepoint-bug-session-log.md`, `eppne-backend/app/main.py`, حذف `eppne-backend/app/domains/agritech/router.py`, كل ملفات `eppne-web/*`, `.claude/plans/phase5-10*`, `.claude/skills/`.

**الحالة:** ✅ الخطوات 1-4 مكتملة. جاري تنفيذ الـcommit.
