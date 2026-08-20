# جلسة: إصلاح مركَّز — قطاع الأكاديمية (6 بنود)

**النوع:** إصلاح كود مباشر، نطاق محدد بستة بنود فقط (4 إصلاح مستقل + ثغرتا عزل مستأجرين).
**السيرفر:** `uvicorn app.main:app` على `http://127.0.0.1:8000` (DB: `eppne_db` docker على 5435، Redis على 6380) — شُغِّل في هذه الجلسة (كان متوقفًا).
**المرجع:** تعليمات الجلسة (root causes موثَّقة سلفًا)، `.claude/reports/academy-structural-completeness-audit-session-log.md`، `.claude/reports/academy-live-testing-session-log.md`.
**الموافقة:** خطة كاملة (diff حرفي لكل بند) عُرضت في `plan mode` ووُوفق عليها صراحة قبل أي تعديل — بموجب قاعدة المشروع "zero touch على كود موجود قبل موافقة صريحة" ([[feedback-stop-before-consequential-edits]]).

---

## ملاحظة سياق مهمة قبل البدء

فحصت الحالة الحالية للمنصة قبل التنفيذ ووجدت: باج `require_subscription()`
(`TypeError` بمعامل زائد) **مُصلَح بالفعل** في جلسة سابقة اليوم
(`require-sector-removal-subscription-fix`)، و`require_sector()` **أُلغي
بالكامل** من `main.py`. لكن `_issue_tokens` (`identity/service.py`) لسه ما
بتحطش `sector` claim في التوكن (متبقٍّ من قبل، غير مرتبط بأي من البنود
الستة) — لا يؤثر عمليًا لأن `require_sector` نفسه أُلغي من `main.py`، لكن
استخدمت حسابات `SUPER_ADMIN` throwaway موجودة من جلسات سابقة (772-777)
تجنبًا لأي عامل إرباك جانبي أثناء الاختبار.

---

## جدول قبل/بعد — الستة بنود

| # | الملف/الموضع | قبل (traceback/سلوك) | بعد (تعديل) | نتيجة الاختبار الحي |
|---|---|---|---|---|
| 1.1 | `academy/service.py:112` `create_course` | `TypeError: got multiple values for keyword argument 'instructor_id'` (مؤكَّد سابقًا، `PROGRESS_LOG.md` backlog مفتوح) | استبعاد `instructor_id` من `data` قبل `**kwargs`، استخدام معامل `instructor_id` (من `current_user.id`) حصريًا | `POST /academy/courses` (تينانت16، TEST_instr_b=774) بجسم يحتوي `"instructor_id":999` (محاولة انتحال) → **201**، `instructor_id` المخزَّن = **774** (المستخدم الحقيقي)، `999` تجوهلت تمامًا |
| 1.2 | `academy/router.py:79-87` `create_org_entity` | `TypeError: create_org_entity() got an unexpected keyword argument 'tenant_id'` (مؤكَّد حيًا في `academy-live-testing`) | استبعاد `tenant_id` من `data.model_dump()` في الراوتر قبل تمريرها للخدمة (الخدمة نفسها صحيحة، تستخدم `self.tenant_id`) | `POST /academy/entities` (TEST_super_a، superuser، تينانت1) → **201**، `tenant_id` الناتج = 1 (من `current_user`) |
| 1.3 | `employment/service.py:164` `create_job` | `TypeError: argument cannot be of 'NoneType' type` من `bleach.clean(data.get("description",""))` عند حذف الحقل (مؤكَّد حيًا) | تطبيق نفس نمط `location` المجاور: `bleach.clean(...) if data.get("description") else None` | `POST /employment/jobs` بلا `description` (TEST_instr_b، تينانت16) → **201**، `description: null`، لا كراش. نفس الطلب مع `description="<b>Some</b> job description"` → **201**، `description: "Some job description"` (تنظيف HTML سليم) |
| 1.4 | `academy/router.py:272-286` `/enroll` | يفرض `payment_method="FREE"` دائمًا → تسجيل `PENDING` عالق لكورس مدفوع (مؤكَّد حيًا) | فحص `is_free`/`price_mrusdt` قبل الاستدعاء؛ رفض `400` صريح لكورس مدفوع بدل تسجيل عالق | `POST /academy/enroll?course_id=2` (TEST_COURSE_A_PAID، سعر 100) → **400** "هذا الكورس مدفوع... استخدم .../store/courses/{id}/enroll..."، **لا صف جديد أُنشئ** (تأكيد SQL: الصف الوحيد لـcourse_id=2 هو الصف القديم من الجلسة السابقة). نفس الطلب لكورس مجاني (id=3، مستخدم جديد لم يسجَّل من قبل) → **200**، `ACTIVE`/`COMPLETED` كالمعتاد |
| 2.1 | `academy/service.py` (`create_live_session`/`create_node_material`/`create_quiz`) | `get_node()` بلا فلتر tenant → كتابة ناجحة (201) عبر حدود المستأجر (مؤكَّد حيًا سابقًا) | إضافة تحقق ملكية عبر `get_course(node.course_id, self.tenant_id)` بعد `get_node()`، بنفس نمط `update_node`/`delete_node` الموجود مسبقًا | `POST /academy/nodes/1/materials` (node1 يخص تينانت16؛ TEST_instr_a تينانت1) → **404** "الدرس غير موجود". نفس الطلب على `node2` (يخص تينانت1، نفس المستخدم) → **201** (الاستخدام الشرعي سليم) |
| 2.2 | `academy/service.py:215-222` `get_node_materials` | بلا فلتر tenant → قراءة `file_url` كاملة عبر حدود المستأجر (مؤكَّد حيًا سابقًا) | نفس نمط 2.1: تحقق ملكية قبل `repo.get_node_materials` | `GET /academy/nodes/1/materials` (تينانت16؛ TEST_student_a تينانت1) → **404**. نفس الطلب على `node2` (تينانت1) → **200** مع المادة المتوقَّعة |

---

## تفاصيل تنفيذية إضافية (بيانات throwaway فقط، صفر كود إضافي)

- **1.1 كشف اعتماديًا:** `academy_courses.instructor_id` مربوط بـ`FOREIGN KEY` على
  `academy_instructors.id` — **وليس** `users.id` مباشرة. جدول
  `academy_instructors` كان فارغًا بالكامل، فمحاولة إنشاء كورس بـ
  `instructor_id=current_user.id` سقطت بـ`IntegrityError` (FK violation) —
  **هذا اكتشاف جديد، خارج نطاق الستة بنود، مرتبط ببند مُوثَّق سابقًا في
  الجرد الأصلي (Instructor منفصل بنيويًا عن User/الأدوار)**. للتحقق حيًا من
  إصلاح 1.1 فقط (لا علاقة له بالـFK)، أدرجت صف throwaway واحد في
  `academy_instructors` (`id=774, user_id=774`) عبر SQL مباشر — بيانات فقط،
  صفر كود. **لم أُصلح الـFK/العلاقة نفسها — خارج النطاق صراحة.**
- **1.3:** احتجت تفعيل ميزة `hr_management` مؤقتًا على خطة اشتراك throwaway
  (`saas_service_plans.id=48`, اسمها `TEST_REQSECTOR_AFFILIATE_PLAN`، ليست
  خطة مشتركة حقيقية) لتجاوز فحص SaaS منفصل تمامًا عن هذا البند
  (`_check_saas_limits`). **أُرجعت لحالتها الأصلية (`features=[]`) فور
  انتهاء الاختبار** — تأكيد SQL أعلاه.
- **2.1/2.2:** استُخدمت بيانات throwaway متبقية من جلسة `academy-live-testing`
  (تينانت B `id=16`، `node_id=1` يخصه) بدون أي تعديل عليها، بالإضافة لـ
  `node_id=2` (تينانت1، موجود مسبقًا) للاختبار الشرعي المقابل.
- **حسابات throwaway مستخدمة:** `TEST_super_a`(772)، `TEST_instr_a`(773)،
  `TEST_instr_b`(774، رُقِّي من `ADMIN`→`SUPER_ADMIN` هذه الجلسة لتفادي أي
  التباس رغم إلغاء `require_sector`)، `TEST_student_a`(775)،
  `TEST_applicant`(776) — كلهم متبقون من جلسات سابقة، لم يُحذف أي منهم.

---

## تأكيد صريح: صفر كسر على الاستخدام الشرعي

| السيناريو الشرعي | النتيجة |
|---|---|
| إنشاء كورس بـ`instructor_id` الحقيقي (بلا محاولة انتحال) | ✅ يعمل (نفس اختبار 1.1، القيمة الصحيحة 774 هي فعليًا ما استُخدم) |
| إنشاء `org_entity` بجسم `tenant_id` مطابق لتينانت المستخدم | ✅ 201 |
| إنشاء وظيفة **بـ**`description` فعلي | ✅ 201، تنظيف HTML سليم |
| تسجيل مجاني عبر `/enroll` | ✅ 200، `ACTIVE`/`COMPLETED` |
| كتابة مادة/جلسة حية/اختبار لـ`node_id` **يخص نفس المستأجر** | ✅ 201 |
| قراءة مواد لـ`node_id` يخص نفس المستأجر | ✅ 200 مع البيانات الصحيحة |

---

## تنظيف بيانات الجلسة

- **السيرفر:** `uvicorn` تُرك شغالًا على `127.0.0.1:8000` (كان متوقفًا قبل
  الجلسة).
- **الوحيد الذي أُرجِع لحالته الأصلية:** `saas_service_plans.id=48.features`
  (أُضيفت `hr_management` مؤقتًا لاختبار 1.3، أُزيلت فور الانتهاء).
- **بيانات throwaway جديدة أُبقيت (موسومة بوضوح):**
  - `academy_instructors.id=774` (صف throwaway لسد فجوة FK غير مرتبطة بالستة بنود، موثَّق أعلاه)
  - `academy_courses.id=6` (`TEST_COURSE_FIX_1_1`, تينانت16)
  - `organization_entities.id=4` (`TEST_ORG_FIX_1_2`, تينانت1)
  - `employment_job_listings.id=4,5` (`TEST_JOB_NO_DESC`, `TEST_JOB_WITH_DESC`)
  - `academy_enrollments` صف جديد لـ`TEST_applicant`(776) في course_id=3
  - `node_materials.id=2` (`TEST_LEGIT_MATERIAL_TENANT_A`, node2/تينانت1)
- **صفر migration، صفر تعديل على بيانات مشتركة/حقيقية** طوال الجلسة.

---

## اكتشافات جديدة خارج النطاق (توثيق فقط، صفر لمس)

- `academy_courses.instructor_id` FK على `academy_instructors.id` وليس
  `users.id` — أي إنشاء كورس حقيقي (بمستخدم بلا صف `Instructor` مقابل)
  سيفشل بـ`IntegrityError` حتى بعد إصلاح 1.1. **نفس المشكلة الجذرية
  الموثَّقة سابقًا في الجرد الأصلي** (`academy-structural-completeness-audit-session-log.md`
  §2.أ: انفصال مفهوم Instructor بنيويًا عن `User`/الأدوار)، بزاوية جديدة
  فقط — أُضيفت كملاحظة تحديث على ذلك القسم مباشرة (بقرار مستخدم صريح: لا
  بند backlog منفصل لنفس المشكلة الجذرية). بانتظار قرار مستند رؤية
  `EntityMembership` (استبدال `academy_instructors`) لا إصلاح موضعي.
