# جلسة فحص IDOR/أمان عميق في `academy` — تأكيد/متابعة بعد جلسات سابقة

**بدأ التسجيل:** 2026-08-24
**الحالة:** ⏳ **الجرد + التحقق الحي مكتملان بالكامل. صفر تنفيذ كود. بانتظار موافقتك على التصنيف والحل المقترَح (§5/§6) قبل أي تطبيق.**

**نطاق الجلسة:** `eppne-backend/app/domains/academy/{router,service,repository,schemas}.py` بالكامل (35 endpoint).

---

## 0) المرجع الميكانيكي — ماذا كان موثَّقًا عن `academy` قبل هذه الجلسة

قُرئت الملفات المرجعية المطلوبة كاملة قبل البدء:

- **`.claude/reports/simpletenant-fix-session-log.md`** (قسم `academy` كامل): `academy` كانت من أول 4 دومينات أُصلحت (36 موضع) — لكن هذا الإصلاح كان **حصريًا لباج SimpleTenant/type-mismatch** (استبدال مصدر `tenant_id` من هيدر `X-Tenant-ID` إلى `current_user.tenant_id`)، **مش IDOR بالمعنى الأشمل**. تحقُّق حي في تلك الجلسة (`GET /academy/reports/financial`, `GET /academy/courses`, `PUT /academy/courses/1`) أكَّد إن الهيدر المزوَّر بلا أي تأثير بعد الإصلاح — **لكن هذا غطّى فقط الـendpoints اللي أصلًا بتستخدم `tenant.id`**، مش كل الـendpoints (بعضها بيقرأ من مصادر تانية تمامًا، راجع §2).
- **`.claude/reports/academy-live-testing-session-log.md`** (362 سطر) + **`academy-priority-fix-session-log.md`** (101 سطر): ركّزا على **كسور وظيفية/بنيوية** (schema↔model mismatches، `require_sector`/`require_subscription` TypeErrors، FK بين `Instructor`/`User`). فحصا **ثغرتي عزل مستأجرين حقيقيتين ومحدَّدتين فقط** (`get_node()`/`get_node_materials()` بلا فلتر تينانت) — **اتصلحوا فعليًا** في `academy-priority-fix` (بند 2.1/2.2: إضافة تحقق ملكية عبر `get_course(node.course_id, self.tenant_id)`). **لم يُفحص أي endpoint من endpoints القوائم (`list_org_entities`/`list_bootcamps`/`list_tracks`/`list_cohorts`) إطلاقًا في أي من الجلستين من زاوية IDOR.**
- **`.claude/reports/academy-structural-completeness-audit-session-log.md`**: جرد بنيوي/وظيفي (هل الميزة موجودة ومربوطة)، **صفر تركيز على IDOR**.
- **`.claude/reports/projects-idor-fix-session-log.md`**: قُرئ كاملًا لاستخلاص المنهجية الحالية — الفحص لازم يغطي **(أ) مصدر `tenant_id`** (هيدر/موثوق) **و(ب) وجود `current_user` من عدمه لكل endpoint** **و(ج) فلتر ملكية/تينانت فعلي على مستوى الـrepository نفسه** (مش بس الراوتر) — لأن endpoint ممكن يكون عنده `current_user` صحيح لكن الـrepository تحته لا يستخدمه إطلاقًا. هذا بالضبط الفجوة اللي طلعت في `academy` (راجع §2).

**الخلاصة قبل القراءة:** `academy` **مش دومين "مؤكَّد ومُصلَح بالكامل" من منظور IDOR** — الإصلاحات السابقة غطت (أ) مصدر `tenant_id` الجذري لمعظم الـendpoints و(ب) ثغرتين محدَّدتين في `nodes/materials`. **لم يُفحص نمط "endpoint بلا `current_user`" ولا نمط "endpoint عنده `current_user` لكن الـrepository تحته بلا فلتر تينانت" إطلاقًا من قبل** — وهذا بالضبط ما كشفته القراءة الكاملة في هذه الجلسة.

---

## 1) القراءة الكاملة — الحالة الحالية (بعد كل الإصلاحات السابقة)

قُرئت الملفات الأربعة كاملة (`router.py` 653 سطر، `service.py` 615 سطر، `repository.py` 847 سطر، `schemas.py` 441 سطر).

### ✅ نقطة إيجابية مؤكَّدة: الجذر (مصدر `tenant_id`) نظيف بالكامل
`grep "get_current_tenant"` على `router.py` = **0 نتيجة**. كل الـ35 endpoint (ما عدا استثناءين موثَّقين تحت) تستخدم `tenant_id = cast(int, current_user.tenant_id)` بشكل موحّد — **مطابق لما وثَّقته `simpletenant-fix-session-log.md`، لسه صحيح اليوم.**

### ✅ نقطة إيجابية ثانية مؤكَّدة: `nodes/materials/quiz/live-session` محمية فعليًا
`create_node_material`, `get_node_materials`, `create_quiz`, `get_node_quiz`, `submit_quiz`, `create_live_session` — **كلها** تمرّ بـ`get_node(node_id)` (بلا فلتر تينانت في الـrepository نفسه) **ثم** `get_course(node.course_id, self.tenant_id)` كتحقق ملكية صريح قبل أي استخدام — **مطابق تمامًا لإصلاح `academy-priority-fix` بند 2.1/2.2، لسه فعّال اليوم.**

### 🔴🔴🔴 المصدر الجذري الجديد — 4 endpoints قراءة (قوائم) تتجاوز `AcademyService` بالكامل وتستدعي `AcademyRepository` مباشرة من الراوتر، بلا أي فلتر تينانت في الـrepository نفسه

هذا نمط مختلف تمامًا عن أي باج فحصته الجلسات السابقة: الـendpoint **عنده `current_user` صحيح فعلاً**، لكن الراوتر **لا يستخدمه** لتمرير `tenant_id` للاستعلام — إما بيمرر بارامتر من العميل مباشرة، أو مش بيمرر تينانت للـ`repository` أصلًا.

| # | الدالة | المسار | `current_user`؟ | مصدر الفلترة الفعلي | فلتر تينانت في الـrepository؟ |
|---|---|---|---|---|---|
| 1 | `list_org_entities` | `GET /academy/entities?tenant_id=X` | ✅ موجود، **لكن غير مُستخدَم** | `tenant_id` **بارامتر من العميل مباشرة** (`router.py:93`) | ✅ الدالة نفسها بتفلتر صح (`WHERE tenant_id == tenant_id`) — **لكن القيمة المُمرَّرة هي مدخل العميل نفسه، مش `current_user.tenant_id`** |
| 2 | `list_bootcamps` | `GET /academy/bootcamps?org_entity_id=X` | ✅ موجود، **غير مُستخدَم إطلاقًا** | `org_entity_id` اختياري فقط | ❌ **صفر فلتر تينانت في `get_bootcamps()` (`repository.py:161-170`) — لو `org_entity_id` غير مُمرَّر، الاستعلام يرجّع كل الـbootcamps في المنصة بلا استثناء** |
| 3 | `list_tracks` | `GET /academy/tracks?org_entity_id=X&bootcamp_id=Y` | ✅ موجود، **غير مُستخدَم إطلاقًا** | `org_entity_id`/`bootcamp_id` اختياريان | ❌ **صفر فلتر تينانت في `get_tracks()` (`repository.py:179-195`)** |
| 4 | `list_cohorts` | `GET /academy/cohorts?org_entity_id=X` (إلزامي) | ✅ موجود، **غير مُستخدَم إطلاقًا** | `org_entity_id` إلزامي | ❌ **صفر فلتر تينانت في `get_cohorts()` (`repository.py:207-213`)** |

**الأثر:** أي مستخدم مُصادَق (بأي دور، بأي تينانت) يقدر:
- يقرأ قائمة `organization_entities` **لأي تينانت تاني** بمجرد تغيير قيمة `tenant_id` في الـquery string — بلا أي علاقة بتينانته الحقيقي.
- يقرأ **كل** الـbootcamps في المنصة (لو ماحددش `org_entity_id`)، أو bootcamps/tracks/cohorts **أي تينانت تاني** لو حدد `org_entity_id`/`bootcamp_id` تبع تينانت مش بتاعه — بلا أي تخمين معقّد، الـIDs متسلسلة وصغيرة.

### 🔴 استثناء إضافي — `get_tenant_by_domain` بلا `current_user` إطلاقًا (قراءة مفتوحة بالكامل، صفر مصادقة)

`router.py:68-78` — `GET /academy/tenants/by-domain?domain=X` — **التوقيع بالكامل بلا `current_user`**، الحماية الوحيدة `rate_limit` (60 طلب/دقيقة لكل IP). يرجّع `TenantResponse` كاملة (`name`, `domain`, `branding`, `id`, `is_active`, `created_at`, `updated_at`). **مؤكَّد حيًا (§3.3): زائر مجهول بالكامل، بلا أي `Authorization`، يقدر يستعلم عن أي تينانت بمجرد معرفة الدومين الخاص بيه.** أثر أضعف من نمط `projects`/`ai_governance` (لا يكشف بيانات مستخدمين/مالية، فقط ميتاداتا التينانت + `branding`)، لكنه **نفس الفئة الميكانيكية بالضبط** (endpoint بلا `current_user` في دومين حساس).

### 🟢 استثناء مقبول: `create_tenant`
`router.py:59-66` — `AcademyService(db, 0)` (تينانت `0` ثابت) — **هذا سليم بالتصميم**، الدالة *تنشئ* تينانت جديد، لا "تقرأ ضمن" تينانت موجود، ومحمية بـ`get_current_superuser`. لا علاقة له بـIDOR.

### 🟡 مرجع فقط (غير مُصعَّد) — استدعاء مالي بمصدر ثقة سليم
`service.py:347-354` (`enroll_in_course`، الدفع `WALLET`) يستدعي `self.finance.transfer(..., receiver_email="academy@eppne.com", ...)` — بريد نظام هاردكودد، لكن **`self.tenant_id` هنا مصدره `current_user.tenant_id` الموثوق فعليًا** (الجذر نظيف، راجع أعلاه)، و`FinanceService.transfer` (`finance/service.py:78-83`) بتفلتر `get_by_email(receiver_email, self.tenant_id)` + تتأكد `receiver.tenant_id == self.tenant_id` — **نفس فئة `projects.add_contribution` §4.2 بالضبط (مرجع فقط، ليس تصعيدًا)**: يتطلب وجود مستخدم حقيقي بريده بالحرف `academy@eppne.com` مزروع مسبقًا في كل تينانت، وتينانت المُرسِل نفسه غير قابل للتزوير هنا. **لم يُستدعَ حيًا في هذه الجلسة** (بقرار متعمَّد، نفس معاملة `projects`/`commerce` سابقًا).

### ⚪ اكتشاف جانبي جديد، خارج نطاق IDOR — `create_bootcamp` معطوبة schema↔model (500 دائمًا)
`repository.py:154-159` (`create_bootcamp`) بيمرر `instructor_id` لـ`Bootcamp(**kwargs)`، لكن جدول `academy_bootcamps` الفعلي (تأكيد `\d academy_bootcamps` حي) **لا يملك عمود `instructor_id` إطلاقًا** (الأعمدة الفعلية: `id, org_entity_id, title, description, duration_days, target_rank, is_active, created_at, updated_at`). **مؤكَّد حيًا (§3.2): `TypeError: 'instructor_id' is an invalid keyword argument for Bootcamp`، فوري، لأي طلب `POST /academy/bootcamps` بلا استثناء** (بعد تجاوز باج `require_subscription` الموثَّق مسبقًا في `academy-live-testing`، وهو لسه قائم كما هو — لم يُفحص هنا لأنه خارج النطاق). **نفس فئة الحالات الثلاث في `constructor-mismatch-backlog-classification.md` — حالة رابعة جديدة تمامًا، لم تُكتشَف في أي جلسة `academy` سابقة** (الجلسات السابقة أنشأت الـbootcamps المطلوبة للاختبار عبر SQL مباشرة، فلم تصطدم بهذا الباج). **صفر علاقة بـIDOR، موثَّق للاكتمال فقط، لم يُلمَس.**

---

## 2) جدول الـ35 endpoint — التصنيف الكامل

| # | الدالة | المسار | `current_user`؟ | مصدر `tenant_id` الفعلي | التصنيف |
|---|---|---|---|---|---|
| 1 | `create_tenant` | `POST /tenants` | superuser | N/A (إنشاء تينانت جديد) | 🟢 سليم |
| 2 | `get_tenant_by_domain` | `GET /tenants/by-domain` | **بلا current_user** | N/A | 🔴 قراءة مفتوحة بالكامل — مؤكَّد حيًا |
| 3 | `create_org_entity` | `POST /entities` | superuser | `current_user.tenant_id` ✅ | 🟢 سليم |
| 4 | `list_org_entities` | `GET /entities?tenant_id=` | active_user (غير مُستخدَم) | **بارامتر عميل مباشر** | 🔴🔴🔴🔴 IDOR — مؤكَّد حيًا |
| 5 | `create_bootcamp` | `POST /bootcamps` | active_user | `current_user.tenant_id` ✅ (تحقق ملكية `org_entity` في service) | 🟢 سليم (لكن معطوب schema↔model، ⚪ أعلاه) |
| 6 | `list_bootcamps` | `GET /bootcamps` | active_user (غير مُستخدَم) | **صفر فلتر تينانت في الـrepository** | 🔴🔴🔴🔴 IDOR — الأخطر (يرجّع كل بيانات المنصة بلا org_entity_id) — مؤكَّد حيًا |
| 7 | `create_track` | `POST /tracks` | superuser | `current_user.tenant_id` ✅ (تحقق ملكية `org_entity_id` إلزامي في schema، دايمًا يشتغل) | 🟢 سليم |
| 8 | `list_tracks` | `GET /tracks` | active_user (غير مُستخدَم) | **صفر فلتر تينانت في الـrepository** | 🔴🔴🔴🔴 IDOR — مؤكَّد حيًا |
| 9 | `create_cohort` | `POST /cohorts` | superuser | `current_user.tenant_id` ✅ (تحقق ملكية `org_entity`) | 🟢 سليم |
| 10 | `list_cohorts` | `GET /cohorts?org_entity_id=` (إلزامي) | active_user (غير مُستخدَم) | **صفر فلتر تينانت في الـrepository** | 🔴🔴🔴🔴 IDOR — مؤكَّد حيًا |
| 11 | `create_course` | `POST /courses` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 12 | `get_courses` | `GET /courses` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 13 | `get_course_by_id` | `GET /courses/{id}` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 14 | `update_course` | `PUT /courses/{id}` | instructor_or_admin | `current_user.tenant_id` ✅ | 🟢 سليم |
| 15 | `get_store_courses` | `GET /store/courses` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 16 | `get_my_enrollments` | `GET /student/my-enrollments` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 17 | `enroll_in_course` | `POST /store/courses/{id}/enroll` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 18 | `enroll_in_course_simple` | `POST /enroll` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 19 | `update_enrollment_progress` | `PUT /student/enrollments/{id}/progress` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 20 | `cancel_enrollment` | `POST /enrollments/{id}/cancel` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 21 | `create_course_unit` | `POST /courses/{id}/units` | instructor_or_admin | `current_user.tenant_id` ✅ (عبر `get_course`) | 🟢 سليم |
| 22 | `get_course_units` | `GET /courses/{id}/units` | active_user | `current_user.tenant_id` ✅ (عبر `get_course`) | 🟢 سليم |
| 23 | `update_unit` | `PUT /units/{id}` | instructor_or_admin | `current_user.tenant_id` ✅ (JOIN مع `Course.tenant_id`) | 🟢 سليم |
| 24 | `delete_unit` | `DELETE /units/{id}` | instructor_or_admin | `current_user.tenant_id` ✅ (نفس أعلاه) | 🟢 سليم |
| 25 | `create_node` | `POST /nodes` | instructor_or_admin | `current_user.tenant_id` ✅ (عبر `get_course` في service) | 🟢 سليم |
| 26 | `get_course_nodes` | `GET /courses/{id}/nodes` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 27 | `update_node` | `PUT /nodes/{id}` | instructor_or_admin | `current_user.tenant_id` ✅ (عبر `get_node`+`get_course`) | 🟢 سليم |
| 28 | `delete_node` | `DELETE /nodes/{id}` | instructor_or_admin | `current_user.tenant_id` ✅ (نفس أعلاه) | 🟢 سليم |
| 29 | `create_node_live_session` | `POST /nodes/{id}/live` | instructor_or_admin | `current_user.tenant_id` ✅ (عبر service) | 🟢 سليم |
| 30 | `create_material` | `POST /nodes/{id}/materials` | instructor_or_admin | `current_user.tenant_id` ✅ | 🟢 سليم (مُصلَح سابقًا، مؤكَّد لسه صحيح) |
| 31 | `get_materials` | `GET /nodes/{id}/materials` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم (مُصلَح سابقًا، مؤكَّد لسه صحيح) |
| 32 | `create_node_quiz` | `POST /nodes/{id}/quiz` | instructor_or_admin | `current_user.tenant_id` ✅ | 🟢 سليم |
| 33 | `get_node_quiz` | `GET /nodes/{id}/quiz` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 34 | `submit_quiz` | `POST /quizzes/{id}/submit` | active_user | `current_user.tenant_id` ✅ | 🟢 سليم |
| 35 | باقي endpoints (`upload`, `tasks/*`, `instructor/*`, `reports/financial`, `leaderboard`, `digital-twin/me`) | — | ✅ الكل عندها `current_user` | `current_user.tenant_id` ✅ في كل واحدة (تأكيد قراءة مباشرة لكل سطر) | 🟢 سليم بالكامل |

**الخلاصة العددية:** 35 endpoint إجمالي — **30 سليمة** (تينانت من `current_user` + فلتر فعلي)، **5 فيها فجوة IDOR/قراءة مفتوحة حقيقية** (`get_tenant_by_domain`, `list_org_entities`, `list_bootcamps`, `list_tracks`, `list_cohorts`).

---

## 3) التحقق الحي — مكتمل بالكامل

**السيرفر:** `uvicorn` شُغِّل محليًا (كان متوقفًا)، تأكيد `GET /docs` → `200`، **أُوقف في نهاية الجلسة** (`netstat` يؤكد صفر `LISTEN` على المنفذ 8000).

**البيانات:** استُخدمت بيانات throwaway **متبقية بالكامل من جلسات سابقة** (`academy-live-testing`/`academy-priority-fix`)، بلا حذف أو تعديل — Tenant A=`id=1`, Tenant B=`id=16` (`TEST_TENANT_B`)، `TEST_super_a`(772, تينانت1, SUPER_ADMIN)، `TEST_instr_b`(774, تينانت16, SUPER_ADMIN)، `organization_entities` id=2(تينانت1)/id=3(تينانت16). تسجيل دخول حقيقي للاثنين (`POST /identity/login`، حقل `username_or_email` كما يتطلبه الـschema الحالي).

### 3.1 🔴🔴🔴🔴 `list_org_entities` — IDOR مؤكَّد

```
A (توكن حقيقي تينانت1) → GET /academy/entities?tenant_id=1
→ 200، [TEST_ORG_A(id=2), TEST_ORG_FIX_1_2(id=4)] — بيانات A الصحيحة

A (نفس التوكن، بلا تغيير الهوية) → GET /academy/entities?tenant_id=16
→ 200، [TEST_ORG_B(id=3)] — بيانات تينانت B كاملة، بمجرد تغيير رقم في الـquery string
```

### 3.2 🔴🔴🔴🔴 `list_bootcamps`/`list_tracks`/`list_cohorts` — IDOR مؤكَّد

**زرعت بيانات throwaway جديدة عبر B (تينانت16) لاختبار القراءة عبر A:**
- `POST /academy/tracks {"org_entity_id":3,"title":"TEST_TRACK_B"}` (B) → `201` نجح فعليًا عبر الـAPI الحقيقي.
- `POST /academy/cohorts {"org_entity_id":3,"name":"TEST_COHORT_B"}` (B) → `201` نجح فعليًا عبر الـAPI الحقيقي.
- `POST /academy/bootcamps {"org_entity_id":3,...}` (B) → **`500`** (باج schema↔model منفصل تمامًا، موثَّق في §1 أعلاه كـ⚪) — زُرع بديل عبر SQL مباشر (`INSERT INTO academy_bootcamps`) لفتح اختبار القراءة فقط.

```
A (تينانت1) → GET /academy/bootcamps   (بلا org_entity_id إطلاقًا)
→ 200، [TEST_BOOTCAMP_B] — bootcamp تبع تينانت16 بالكامل، بلا أي تخمين ID أو هيدر

A (تينانت1) → GET /academy/bootcamps?org_entity_id=3   (org_entity تبع تينانت16)
→ 200، [TEST_BOOTCAMP_B] — نفس النتيجة

A (تينانت1) → GET /academy/tracks?org_entity_id=3
→ 200، [TEST_TRACK_B] — track تبع تينانت16

A (تينانت1) → GET /academy/cohorts?org_entity_id=3
→ 200، [TEST_COHORT_B] — cohort تبع تينانت16
```

### 3.3 🔴 `get_tenant_by_domain` — قراءة مفتوحة بلا أي مصادقة، مؤكَّدة حيًا

```
مجهول بالكامل (صفر Authorization) → GET /academy/tenants/by-domain?domain=test-tenant-b.local
→ 200 {"name":"TEST_TENANT_B","domain":"test-tenant-b.local","branding":{},"id":16,"is_active":true,...}
```

### 3.4 ⚪ `create_bootcamp` — تأكيد حي للباج الجانبي (خارج النطاق)

```
B (تينانت16، SUPER_ADMIN) → POST /academy/bootcamps {"org_entity_id":3,"title":"TEST_BOOTCAMP_B",...}
→ 500، traceback: TypeError: 'instructor_id' is an invalid keyword argument for Bootcamp
```

---

## 4) بيانات throwaway — تنظيف كامل ومؤكَّد مستقل

- `academy_tracks.id=1` (`TEST_TRACK_B`) — **محذوف** (زُرع عبر API هذه الجلسة).
- `academy_cohorts.id=1` (`TEST_COHORT_B`) — **محذوف** (زُرع عبر API هذه الجلسة).
- `academy_bootcamps.id=1` (`TEST_BOOTCAMP_B`) — **محذوف** (زُرع عبر SQL هذه الجلسة، بسبب الباج ⚪).
- `SELECT count(*)` مستقل بعد الحذف على الثلاثة جداول = **0 لكل واحد**.
- **لم يُلمَس أي شيء من بيانات الجلسات السابقة** (Tenant B id=16، المستخدمون 772-777، `organization_entities` id=2/3/4، الكورسات) — تُركت كما هي بلا تعديل، بادئة `TEST_`/`TEST_TENANT_B` واضحة كما كانت.
- السيرفر التجريبي **أُوقف**، `netstat` يؤكد صفر اتصال `LISTEN` على المنفذ 8000.
- **صفر تعديل كود، صفر migration** طوال الجلسة.

---

## 5) الخلاصة والتصنيف النهائي — بانتظار قرارك

| # | الاكتشاف | الخطورة | مؤكَّد حيًا؟ | يحتاج قرار |
|---|---|---|---|---|
| 1 | `list_org_entities` — `tenant_id` مصدره بارامتر عميل مباشر، `current_user` موجود لكن غير مُستخدَم | 🔴🔴🔴🔴 IDOR كلاسيكي، أوضح صورة (بارامتر صريح لا حتى هيدر) | ✅ | نعم |
| 2 | `list_bootcamps` — صفر فلتر تينانت في الـrepository، بلا `org_entity_id` يرجّع كل بيانات المنصة | 🔴🔴🔴🔴 **الأخطر في هذه الجلسة** — لا يحتاج حتى معرفة ID | ✅ | نعم |
| 3 | `list_tracks` — صفر فلتر تينانت في الـrepository | 🔴🔴🔴🔴 | ✅ | نعم |
| 4 | `list_cohorts` — صفر فلتر تينانت في الـrepository | 🔴🔴🔴🔴 | ✅ | نعم |
| 5 | `get_tenant_by_domain` — قراءة مفتوحة بالكامل، بلا `current_user` | 🔴 (أثر أضعف من 1-4: ميتاداتا تينانت فقط، لا بيانات مستخدمين/مالية) | ✅ | نعم |
| ⚪ | `create_bootcamp` — schema↔model `TypeError` (`instructor_id`) | — | ✅ | Backlog منفصل — **خارج نطاق IDOR**، يستحق إضافة لـ`constructor-mismatch-backlog-classification.md` (حالة رابعة) |
| 🟡 | `enroll_in_course` → `receiver_email="academy@eppne.com"` هاردكودد | — | لم يُستدعَ حيًا (قرار متعمَّد، مصدر التينانت موثوق أصلًا) | مرجع فقط، نفس معاملة `projects`/`commerce` |

### الحل المقترَح (معروض فقط — **صفر تنفيذ حتى الآن**)

**نفس النمط الميكانيكي المطبَّق على `projects`/`ai_governance`/الدومينات الخمسة الأخرى:**

- **`list_org_entities`:** حذف بارامتر `tenant_id` من التوقيع، استبداله بـ`tenant_id = cast(int, current_user.tenant_id)` (الاستدعاء `repo.get_org_entities(tenant_id, ...)` نفسه لا يتغيّر — الدالة أصلًا بتفلتر صح، المشكلة في مصدر القيمة فقط).
- **`list_bootcamps`/`list_tracks`/`list_cohorts`:** يحتاج تغيير أعمق شوية — الـrepository نفسه (`get_bootcamps`/`get_tracks`/`get_cohorts`) لازم ياخد `tenant_id` كبارامتر إلزامي، ويفلتر عبر `JOIN` مع `OrganizationEntity.tenant_id` (نفس نمط `update_course_unit`/`get_task` الموجود بالفعل في نفس الملف — `JOIN` + `WHERE tenant.tenant_id == tenant_id`). الراوتر يمرر `current_user.tenant_id` دايمًا.
- **`get_tenant_by_domain`:** **سؤال تصميمي مفتوح** (بانتظار توجيهك، بالضبط زي أسئلة `ai_governance`/`projects` المماثلة) — هل الغرض من هذا الـendpoint هو "دليل عام" مقصود (مثلاً شاشة تسجيل دخول تسأل "اكتب دومين مؤسستك")، وفي هذه الحالة الحل هو تضييق الحقول المُرجَعة فقط (حذف `branding`)، مش إضافة `current_user`؟ أم إنه لازم يتطلب مصادقة زي باقي الدومين؟ **لا أفترض نية التصميم من القراءة وحدها.**

**سؤال تصميمي إضافي (`list_bootcamps` تحديدًا):** حاليًا الـendpoint بيسمح بقائمة بلا `org_entity_id` (كل الـbootcamps). بعد الإصلاح، هل تحب سلوك "كل bootcamps تينانتي" (نفس نمط `list_org_entities`) أم يفضل الإبقاء على `org_entity_id` اختياري لكن **دايمًا** مقيّد بتينانت `current_user` (يعني لو مُرِّر `org_entity_id` تبع تينانت تاني، يرجّع قائمة فاضية بدل خطأ)؟ الأقرب لنمط باقي الدومينات هو الثاني (فلترة صامتة، لا رفض صريح) — **معروض لتأكيدك فقط.**

---

## 6) بانتظار توجيهك

**صفر تنفيذ كود. صفر كتابة في `PROGRESS_LOG.md` بعد.** الجرد (35/35 endpoint) + التحقق الحي (6 سيناريوهات هجوم عبر-تينانت مؤكَّدة، تغطي القراءة المفتوحة والقوائم غير المفلترة والباج الجانبي المحجوب) **مكتمل بالكامل**، البيانات المزروعة هذه الجلسة مُنظَّفة ومؤكَّدة، بيانات الجلسات السابقة سليمة بلا لمس، السيرفر متوقف.

**القرار المطلوب:**
1. الموافقة على التصنيف أعلاه (§5).
2. الحل المقترَح لكل من الأربعة IDOR الأساسية (`list_org_entities`/`list_bootcamps`/`list_tracks`/`list_cohorts`) — نفس النمط الميكانيكي المعتاد.
3. توجيه تصميمي بخصوص `get_tenant_by_domain` (فتح مقصود يحتاج تضييق الحقول، أم يحتاج مصادقة كاملة؟).
4. توجيه بخصوص سلوك `list_bootcamps` بعد الإصلاح (فلترة صامتة تعيد `[]` للـIDs الأجنبية، أم رفض صريح؟).
5. تأكيد إضافة حالة `create_bootcamp`/`instructor_id` لملف `constructor-mismatch-backlog-classification.md` (بند خامس، مرجع فقط، خارج نطاق هذا الإصلاح).

---

## 7) قرار المستخدم [2026-08-24] — موافقة كاملة على الخمسة، مع توجيهين تصميميين

1. ✅ التصنيف (§5) — موافقة كاملة.
2. ✅ **الحل الميكانيكي للأربعة IDOR الأساسية** — كما هو مقترَح.
3. ✅ **`get_tenant_by_domain` يحتاج `current_user` كامل** — بخلاف `sovereign_entities.get_entity_page` (اللي كان موثَّق صراحة كقرار تصميمي متعمَّد)، لا يوجد أي إشارة إن الفتح هنا مقصود — يُعامَل بنفس نمط الأربعة الأخرى: `current_user` + `tenant_id = cast(int, current_user.tenant_id)`، وفلترة النتيجة بالتينانت.
4. ✅ **`list_bootcamps` (وأي قائمة مشابهة): فلترة صامتة** — `org_entity_id` تبع تينانت تاني يرجّع `[]` بدل رفض صريح، اتساقًا مع نمط باقي القوائم في الدومين.
5. ✅ إضافة `academy-create-bootcamp-instructor-id-mismatch` كحالة خامسة في `constructor-mismatch-backlog-classification.md`.

**توجيه إضافي:** تنفيذ الخمسة، تحقق حي بعد كل واحد بنفس سيناريوهات §3، عرض النتائج + `git status`/`git diff --stat` قبل أي commit.

---

## 8) التنفيذ — مكتمل، مؤكَّد حيًا بالكامل

### 8.1 الديف المُطبَّق

**`router.py` (5 تعديلات):**
- `get_tenant_by_domain`: أُضيف `current_user: User = Depends(get_current_active_user)`؛ بعد جلب `tenant = await repo.get_tenant_by_domain(domain)`، الشرط أصبح `if not tenant or cast(int, tenant.id) != tenant_id: raise 404` (بدل `if not tenant`).
- `list_org_entities`: حُذف بارامتر `tenant_id: int` من التوقيع بالكامل، أُضيف `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم — الاستدعاء `repo.get_org_entities(tenant_id, ...)` نفسه لم يتغيّر.
- `list_bootcamps`: أُضيف `tenant_id = cast(int, current_user.tenant_id)`، الاستدعاء أصبح `repo.get_bootcamps(tenant_id, org_entity_id=org_entity_id, skip=skip, limit=limit)`.
- `list_tracks`: نفس النمط — `repo.get_tracks(tenant_id, org_entity_id=..., bootcamp_id=..., skip=..., limit=...)`.
- `list_cohorts`: نفس النمط — `repo.get_cohorts(tenant_id, org_entity_id, skip=skip, limit=limit)`.

**`repository.py` (3 تعديلات — إضافة `tenant_id` كبارامتر إلزامي + `JOIN` مع `OrganizationEntity`):**
```diff
- async def get_bootcamps(self, org_entity_id=None, skip=0, limit=100):
-     query = select(Bootcamp)
+ async def get_bootcamps(self, tenant_id: int, org_entity_id=None, skip=0, limit=100):
+     query = (
+         select(Bootcamp)
+         .join(OrganizationEntity, OrganizationEntity.id == Bootcamp.org_entity_id)
+         .where(OrganizationEntity.tenant_id == tenant_id)
+     )
      if org_entity_id is not None:
          query = query.where(Bootcamp.org_entity_id == org_entity_id)
```
نفس النمط بالحرف لـ`get_tracks` (`JOIN` عبر `Track.org_entity_id` — العمود موجود دايمًا على الصف لأنه إلزامي في `TrackCreate` schema، بغض النظر عن مسار `bootcamp_id`/`org_entity_id` المُستخدَم للفلترة) و`get_cohorts` (`JOIN` + `and_(org_entity_id==org_entity_id, tenant_id==tenant_id)`). `OrganizationEntity` كانت مستوردة بالفعل في `repository.py` — صفر import جديد.

`python -m py_compile app/domains/academy/router.py app/domains/academy/repository.py` → `exit code 0`.

### 8.2 إعادة تشغيل uvicorn

تأكيد فعلي إن المنفذ 8000 فاضي، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، انتظار حتى `GET /docs` → `200`. تسجيل دخول حقيقي جديد لنفس مستخدمي §3 (`TEST_super_a`/تينانت1، `TEST_instr_b`/تينانت16) — تأكيد `access_token` صالح لكل واحد.

### 8.3 التحقق الحي بعد الإصلاح — نفس سيناريوهات الهجوم بالحرف (§3) + مسارات شرعية

**بيانات throwaway جديدة** (`TEST_TRACK_B2`/`TEST_COHORT_B2` عبر الـAPI الحقيقي لـB، `TEST_BOOTCAMP_B2` عبر SQL بسبب باج `instructor_id` الجانبي غير المتعلق — نفس القيد الموثَّق في §1/§3.4، لم يتغيّر):

| # | الاختبار | قبل الإصلاح (§3) | بعد الإصلاح | الحكم |
|---|---|---|---|---|
| 1 | A → `GET /academy/entities` (بلا بارامتر، الحقل حُذف من الـAPI) | `200` مع بيانات A فقط (بس كان بارامتر `tenant_id` متاح للتلاعب) | `200`، [`TEST_ORG_A`, `TEST_ORG_FIX_1_2`] فقط — بيانات A الصحيحة | ✅ **المسار الشرعي سليم** |
| 2 | A → `GET /academy/entities?tenant_id=16` (محاولة الهجوم القديم، البارامتر لم يعد له تأثير) | `200` مع بيانات B الكاملة | **نفس نتيجة #1 بالحرف** (بيانات A فقط) — البارامتر الزائد يُتجاهَل تمامًا الآن | ✅ **حاسم — الهجوم القديم عديم الأثر** |
| 3 | A → `GET /academy/bootcamps` (بلا `org_entity_id`) | `200` مع `TEST_BOOTCAMP_B` (تبع B) | **`200`، `[]`** | ✅ **حاسم — أخطر ثغرة في الجلسة مقفولة بالكامل** |
| 4 | A → `GET /academy/bootcamps?org_entity_id=3` (تبع B) | `200` مع `TEST_BOOTCAMP_B` | **`200`، `[]`** (فلترة صامتة، لا `404`/`403` — كما طُلب) | ✅ **حاسم** |
| 5 | A → `GET /academy/tracks?org_entity_id=3` (تبع B) | `200` مع `TEST_TRACK_B` | **`200`، `[]`** | ✅ **حاسم** |
| 6 | A → `GET /academy/cohorts?org_entity_id=3` (تبع B) | `200` مع `TEST_COHORT_B` | **`200`، `[]`** | ✅ **حاسم** |
| 7 | A → `GET /academy/tenants/by-domain?domain=test-tenant-b.local` | `200` (حتى بلا `Authorization` أصلًا) | **`404 {"detail":"Tenant not found"}`** | ✅ **حاسم** |
| 7b | مجهول بالكامل (صفر `Authorization`) → نفس الطلب | `200` | **`401 {"detail":"Not authenticated"}`** | ✅ **حاسم** |
| 7s | A → `GET /academy/tenants/by-domain?domain=test.local` (دومين تينانته الحقيقي) | — | `200` مع بيانات تينانت A الصحيحة | ✅ **المسار الشرعي سليم** |
| 8s | B → `GET /academy/entities` (بلا بارامتر) | — | `200`، `[TEST_ORG_B]` فقط | ✅ **المسار الشرعي سليم** |
| 9s | B → `GET /academy/bootcamps` (بلا `org_entity_id`) | — | `200`، `[TEST_BOOTCAMP_B2]` (بتاعه فقط) | ✅ **المسار الشرعي سليم — القائمة بقت مفلترة بتينانته، مش فاضية ولا عالمية** |
| 10s | B → `GET /academy/bootcamps?org_entity_id=3` (بتاعه) | — | `200`، `[TEST_BOOTCAMP_B2]` | ✅ **المسار الشرعي سليم** |
| 11s | B → `GET /academy/tracks?org_entity_id=3` (بتاعه) | — | `200`، `[TEST_TRACK_B2]` | ✅ **المسار الشرعي سليم** |
| 12s | B → `GET /academy/tracks?bootcamp_id=999` (غير موجود) | — | `200`، `[]` | ✅ سلوك صحيح متوقَّع |
| 13s | B → `GET /academy/cohorts?org_entity_id=3` (بتاعه) | — | `200`، `[TEST_COHORT_B2]` | ✅ **المسار الشرعي سليم** |
| 14s | B → `GET /academy/tenants/by-domain?domain=test-tenant-b.local` (دومين تينانته الحقيقي) | — | `200` مع بيانات تينانت B الصحيحة | ✅ **المسار الشرعي سليم** |

**تأكيد حاسم إضافي:** كل الأربعة IDOR الأساسية أصبحت ترجع `[]` (فلترة صامتة، كما طُلب صراحة) بدل بيانات التينانت الآخر — **صفر خطأ `500`/`403` يكشف عن وجود المورد بشكل غير مباشر**، و`get_tenant_by_domain` أصبح يتطلب مصادقة + تطابق تينانت صريح (`404` موحّد لكل من "غير موجود" و"موجود لكن تينانت تاني" — لا يفرّق الرد بين الحالتين، فلا يوجد تسريب معلومات عبر فرق الرسائل).

### 8.4 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

```sql
DELETE FROM academy_tracks WHERE id=2 AND title='TEST_TRACK_B2';
DELETE FROM academy_cohorts WHERE id=2 AND name='TEST_COHORT_B2';
DELETE FROM academy_bootcamps WHERE id=2 AND title='TEST_BOOTCAMP_B2';
```
`SELECT count(*)` مستقل بعد الحذف على الثلاثة جداول = **0 لكل واحد**. بيانات الاكتشاف الأولى (§4) كانت اتنضَّفت بالفعل قبل هذا القسم. **لم يُلمَس أي شيء من بيانات الجلسات السابقة** (Tenant B id=16، المستخدمون 772-777، `organization_entities` id=2/3/4، الكورسات). السيرفر التجريبي **أُوقف**، `netstat` يؤكد صفر اتصال `LISTEN` على المنفذ 8000. **صفر migration** طوال الجلسة.

### 8.5 توثيق البنود الجانبية — مكتمل

- **`create_bootcamp`/`instructor_id`** أُضيف كبند #20 (🟢 محلي) في `constructor-mismatch-backlog-classification.md`، وكبند جديد في جدول الـBacklog النشط بـ`PROGRESS_LOG.md`.
- **`enroll_in_course` → `receiver_email="academy@eppne.com"`** أُضيف كبند مرجعي (🟢، أضعف حتى من نظيره في `projects` لأن مصدر التينانت كان موثوقًا من الأساس) في نفس الجدول.

---

## 9) `git status` / `git diff --stat` — للمراجعة قبل أي commit

**الملفات التي عدَّلتها هذه الجلسة:**
```
M eppne-backend/app/domains/academy/router.py       (+11, -8 تقريبًا — 5 endpoints)
M eppne-backend/app/domains/academy/repository.py   (+18, -6 تقريبًا — 3 دوال list)
M PROGRESS_LOG.md                                    (3 بنود جديدة في جدول الـBacklog النشط)
M .claude/reports/constructor-mismatch-backlog-classification.md  (بند #20 + تحديثات الملخص)
?? .claude/reports/academy-idor-fix-session-log.md   (جديد، هذا الملف)
```

**باقي الملفات الظاهرة في `git status` الأصلي (متعدّلة/untracked من جلسات سابقة غير متعلقة بهذه الجلسة إطلاقًا)** — `security.py`, `main.py`, `agritech/router.py` (محذوف)، `health/service.py`, `invoicing/router.py`, `tasks/affiliate.py`, `tasks/billing.py`, `tests/conftest.py`, ملفات `eppne-web/*`، وباقي خطط/تقارير `.claude/` الأخرى (`.claude/plans/*`, `.claude/reports/phase16-session-log.md`) — **لم تُلمس، لن تُضاف لأي commit من هذه الجلسة.**

**الحالة النهائية:** ✅ **الإصلاح الميكانيكي للخمسة (4 IDOR + endpoint مفتوح) مُطبَّق بالكامل على `academy`، مؤكَّد حيًا بالكامل (7 سيناريوهات هجوم مرفوضة/محايَدة + 7 مسارات شرعية سليمة، بما فيها تحقق أن قوائم B لم تتأثر بالفلترة الجديدة)، بيانات throwaway منظَّفة بالكامل.** البندان الجانبيان موثَّقان في `PROGRESS_LOG.md` وملف التصنيف. ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.
