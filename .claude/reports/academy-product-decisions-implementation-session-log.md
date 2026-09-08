# جلسة: تنفيذ القرارات المنتجية الأربعة — قطاع الأكاديمية

**النوع:** بناء ميزات فعلي (كود + 2 migrations). أربعة بنود مستقلة، 4 commits منفصلة،
موافقة صريحة على كل diff قبل التنفيذ (plan mode + عرض كل تعديل حرفيًا في الشات).
**المرجع:** `.claude/plans/academy-product-decisions.md` (القرارات المعتمَدة)،
`.claude/reports/academy-structural-completeness-audit-session-log.md`،
`.claude/reports/academy-live-testing-session-log.md`،
`.claude/reports/academy-priority-fix-session-log.md`.
**السيرفر:** `uvicorn app.main:app` على `127.0.0.1:8000` (DB `eppne_db` docker على 5435،
Redis على 6380) — شُغِّل/أُعيد تشغيله عدة مرات خلال الجلسة (كان متوقفًا قبلها).

---

## توقفان مطلوبان صراحة قبل البدء (بحسب تعليمات الجلسة نفسها)

قبل أي كود، فحص الحالة الفعلية كشف نقطتين تطابقان شروط "وثّق ووقف واسأل" المنصوص
عليها في التعليمات — عُرضتا على المستخدم عبر `AskUserQuestion` وتقرَّر:

1. **Quizzes (البند 1):** `QuizQuestion.type` يقبل فعليًا `SHORT_ANSWER` بجانب
   `MCQ`/`TRUE_FALSE` (`schemas.py`) — افتراض "تصحيح تلقائي فوري لكل الأسئلة" غير صالح
   عالميًا. **القرار:** تصحيح جزئي فوري — MCQ/TRUE_FALSE تُصحَّح تلقائيًا، SHORT_ANSWER
   تُعطى صفرًا تلقائيًا، الحالة النهائية `GRADED` فقط لو كل الأسئلة MCQ/TRUE_FALSE،
   وإلا `PARTIALLY_GRADED` (تصحيح لاحق أثناء التنفيذ نفسه — انظر أدناه).
2. **Enrollment Cancellation (البند 2):** لا يوجد أي تتبع حقيقي لفتح المحتوى على مستوى
   العُقدة — الموجود الوحيد `Enrollment.progress_percentage` رقم **يُرسله العميل بنفسه**
   عبر `PUT .../progress`، بلا حساب سيرفر من فتح فعلي. **القرار:** استخدامه كبديل مؤقت
   لحساب شرط "7%"، مع توثيق الضعف (قابل للتلاعب) وبند backlog لاستبداله لاحقًا.

---

## البند 1 — Quizzes: قراءة + تسليم + تصحيح جزئي فوري

**Commit:** `71a5c5a` — `feat(academy): build full quiz read/submit/auto-grade path`

### الملخص
- Migration جديدة `031_create_quiz_submissions` — جدول `quiz_submissions` (`quiz_id`,
  `user_id`, `tenant_id`, `answers` JSONB, `score`, `status`, `submitted_at`).
- `GET /academy/nodes/{node_id}/quiz` — schema جديد `QuizPublicResponse`/
  `QuizQuestionPublic` بلا `correct_answer` (كان `QuizResponse` الأصلي يسرّبها).
- `POST /academy/quizzes/{quiz_id}/submit` — يتطلب تسجيلًا فعليًا (`Enrollment.status
  == "ACTIVE"`)، ينفذ `max_attempts`، يصحح MCQ/TRUE_FALSE تلقائيًا، SHORT_ANSWER = صفر
  تلقائي، `status = "GRADED"` إن لم توجد أسئلة نصية، وإلا `"PARTIALLY_GRADED"`
  (تصحيح أُدخل أثناء المراجعة الحية بعد ملاحظة من المستخدم أن `"GRADED"` دائمًا كان
  مضلِّلًا لسؤال معطى صفرًا افتراضيًا بانتظار تصحيح بشري).
- `get_quiz_by_node`/جميع النقاط الجديدة محكومة بنفس نمط التحقق من ملكية الـtenant
  الموجود مسبقًا (`get_node` → `get_course(tenant_id)`).
- بلا لمس لأي دالة قراءة/كتابة موجودة (Tasks/Submissions/Grading/materials).

### جدول الاختبار الحي
| # | سيناريو | النتيجة |
|---|---|---|
| 1 | `GET` اختبار لطالب مسجَّل | 200، بلا `correct_answer` |
| 2 | تسليم (MCQ✓+TRUE_FALSE✓+SHORT_ANSWER) لطالب مسجَّل | 200، `score=80.0`, `status=PARTIALLY_GRADED` |
| 3 | تسليم من مستخدم غير مسجَّل | 403 `PermissionDeniedError` |
| 4 | قراءة اختبار عبر تينانت آخر | 404 — عزل مؤكَّد |
| 5 | قراءة من غير مسجَّل بنفس التينانت (قبل بوابة البند 3) | 200 |
| 6 | تسليم ثانٍ (ضمن `max_attempts=2`) | 200 |
| 7 | تسليم ثالث (تجاوز `max_attempts`) | 403 صريح |
| 8 | كويز MCQ فقط (بلا SHORT_ANSWER) | 200، `score=100.0`, `status=GRADED` |

**صفر كسر:** لا تعديل على `create_quiz`/`create_node_material`/Tasks؛ إضافي بالكامل.

---

## البند 2 — Enrollment Cancellation

**Commit:** `d5f843a` — `feat(academy): add enrollment cancellation with two-tier refund policy`

### الملخص
- Migration جديدة `032_add_enrollment_cancellation` — 5 أعمدة على `academy_enrollments`
  (`cancelled_at`, `cancellation_reason`, `cancellation_note`, `refund_status`,
  `refund_amount`) + عمود `is_foundational` على `academy_courses` (لا يوجد أي flag سابق
  يميّز "الكورس الأساسي" — أُضيف جديدًا، قرار موثَّق ومعروض للموافقة قبل التنفيذ).
- `POST /academy/enrollments/{id}/cancel` — نافذة الاسترداد تُقفَل عند أول شرط: 7 أيام
  من `created_at` **أو** `progress_percentage >= 7` (OR، ثنائي: `FULL`/`NONE`).
- 11 سبب إلغاء (`CANCELLATION_REASONS` في `schemas.py`، مطابقة حرفيًا لـ
  `academy-product-decisions.md` §1-ب)، `OTHER` يتطلب نصًا حرًا (تحقق service-layer،
  بلا قيد DB صارم).
- إلغاء تسجيل بكورس `is_foundational=true` ضمن النافذة يُلغي أي اشتراك `TRIAL` لنفس
  الـtenant عبر `SaaSControlService.cancel_subscription` الموجودة فعليًا (method جديدة
  `SaaSRepository.get_trial_subscriptions`).
- `_revoke_affiliate_commission_hook` — placeholder صريح (`pass` + `# TODO`)، بلا منطق
  فعلي، بانتظار نظام العمولة الموحَّد (لا يزال 🔴 مفتوحًا).
- "7% من المحتوى": يستخدم `Enrollment.progress_percentage` الموجود (ذاتي التبليغ من
  العميل، غير موثوق بالكامل) — **بلا** بناء تتبع حقيقي جديد هذه الجلسة (قرار مستخدم
  صريح بعد توقف/سؤال).

### جدول الاختبار الحي
| # | سيناريو | النتيجة |
|---|---|---|
| 1 | إلغاء فوري (0 يوم، 0%) | `refund_status=FULL`, `refund_amount=50.00` |
| 2 | إلغاء بعد 8 أيام (0%) | `refund_status=NONE` |
| 3 | إلغاء بعد يوم واحد + تقدم 10% | `refund_status=NONE` (تأكيد OR) |
| 4 | `OTHER` بلا نص | 422 `ValidationError` |
| 5 | `OTHER` بنص | 200 |
| 6 | كورس `is_foundational=true` ضمن النافذة | `FULL` + اشتراك `TRIAL` تحوَّل `CANCELLED` تلقائيًا |
| 7 | إلغاء نفس التسجيل مرتين | الأولى 200، الثانية 403 |
| — | تحقق ارتداد: اشتراك `ACTIVE` آخر + تسجيل مستخدَم من البند 1 | لم يتأثرا |

**صفر كسر:** بيانات throwaway فقط (6 كورسات، 6 تسجيلات، اشتراك TRIAL واحد) — تحقَّق
مباشرة عبر SQL أن الاشتراك `ACTIVE` الحقيقي (id=2) وتسجيلات مستخدَمة في بنود أخرى
لم تُلمَس.

---

## البند 3 — `is_free_preview`: تفعيل فعلي

**Commit:** `7f22911` — `feat(academy): enforce is_free_preview on node content reads`

### الملخص
- بعد فحص كل مسارات قراءة المحتوى في الدومين، تبيَّن وجود **3** لا 1: `get_node_materials`
  (المذكورة صراحة بالتعليمات)، `get_node_quiz` (الجديدة من البند 1)، و**اكتشاف إضافي**:
  `GET /courses/{course_id}/nodes` كانت تُعيد `content_url` لكل عُقدة بلا أي فحص تسجيل.
- القرار المطبَّق (مقترَح مني، عُرض للموافقة قبل التنفيذ): قائمة العُقَد تبقى كاملة
  الظهور (لتصفح المنهج)، لكن `content_url` يُصفَّر (`null`) للعُقَد غير المجانية عند
  مستخدم غير مسجَّل — بدل حذف العقدة من القائمة بالكامل.
- `_is_enrolled(user_id, course_id)` helper مشترك جديد يُستخدم في الثلاثة مسارات.
- الاستثناء الوحيد: `node.is_free_preview=true`.

### جدول الاختبار الحي
| # | سيناريو | النتيجة |
|---|---|---|
| 1 | غير مسجَّل + مواد على node عادي | 403 |
| 2 | غير مسجَّل + مواد على node معاينة مجانية | 200 |
| 3 | مسجَّل فعليًا + مواد على node عادي | 200 |
| 4 | غير مسجَّل + قائمة عُقَد الكورس | 200، `content_url=null` لغير المجانية |
| 5 | مسجَّل فعليًا + قائمة عُقَد الكورس | 200، كل `content_url` ظاهر |
| 6 | غير مسجَّل + قراءة اختبار (البند 1) على node عادي | 403 (كانت 200 قبل هذا البند) |

**صفر كسر:** المستخدمون المسجَّلون فعليًا يحصلون على نفس السلوك السابق تمامًا (200،
محتوى كامل) في كل المسارات الثلاثة.

---

## البند 4 — Payment Installments: توثيق فقط

**Commit:** `a129d9e` — `docs(academy): document PaymentInstallment freeze as intentional`

### الملخص
- تعليق فوق `PaymentInstallment` (`models.py`) وفوق سطر `total_overdue` في
  `get_financial_summary` (`repository.py`) يوضّحان أن القيمة `0` دائمًا **قرار مقصود**
  (انتظار خدمة أقساط مشتركة عبر القطاعات)، لا نسيان.
- **صفر تعديل آخر** — لا حذف موديل، لا منطق جديد، لا مسار كتابة.

### تحقق
`GET /academy/reports/financial` (سوبر أدمن) → `200`, `{"total_paid": 400.0,
"total_overdue": 0.0}` — نفس السلوك تمامًا قبل وبعد التعديل (تعليقات فقط).

---

## ملخص الجلسة الكامل

| البند | Commit | migration | صفر كسر مؤكَّد |
|---|---|---|---|
| 1. Quizzes | `71a5c5a` | `031_create_quiz_submissions` | ✅ |
| 2. Enrollment Cancellation | `d5f843a` | `032_add_enrollment_cancellation` | ✅ |
| 3. `is_free_preview` | `7f22911` | لا يوجد (سلوك فقط) | ✅ |
| 4. Payment Installments (توثيق) | `a129d9e` | لا يوجد | ✅ |

**بيانات throwaway مُبقاة** (موسومة `TEST_`): 3 نقاط throwaway جديدة — node رابع
(`TEST_NODE_FREE_PREVIEW`, id=4) بمادة عليه، 6 كورسات (`TEST_COURSE_C2_*`, id=7-12) و6
تسجيلات مقابلة لاختبار الإلغاء، اشتراك `TRIAL` واحد (id=50، تحوَّل `CANCELLED` أثناء
الاختبار كنتيجة متوقَّعة). **صفر بيانات مشتركة/حقيقية لُمست.**

**ملاحظة بيئية (غير متعلقة بالكود):** واجهت الجلسة أخطاء بيانات throwaway ذاتية
المصدر مرتين (`is_completed`/`reward_amount` NULL من إدراجات SQL مباشرة بدون قيم
افتراضية على مستوى DB) — صُحِّحت فورًا، صفر علاقة بمنطق الكود المُنفَّذ، موثَّقة هنا
للشفافية فقط.

**القرارات الأربعة المعتمَدة في `academy-product-decisions.md` — منفَّذة بالكامل الآن.**
