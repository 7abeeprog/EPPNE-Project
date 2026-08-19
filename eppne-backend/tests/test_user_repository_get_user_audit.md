# `test_user_repository_get_user_audit.py`

## المرجع الأصلي
- `.claude/plans/user-repository-get-user-audit-session-instructions.md` (تعليمات الجلسة).
- `.claude/reports/user-repository-get-user-audit-session-log.md` (التقرير الكامل، Backlog #8).

## السبب الجذري (كان)
`UserRepository` **ليست عندها method اسمها `get_user()` إطلاقًا** (بعكس Backlog #1/`get_by_id` اللي كانت موجودة بتوقيع ناقص). `grep` شامل جديد بالكامل عن `\.get_user\(` كشف **5 مواضع فعليًا** — 3 منها مواضع حية (8 نقاط استدعاء إجمالًا) و2 dead code — كل استدعاء حي كان `AttributeError: 'UserRepository' object has no attribute 'get_user'` فورية.

## الإصلاح المُطبَّق
- `employment`/`digital_twin`: نفس منهجية Backlog #1 بالحرف — تعديل توقيع كل private helper (`_get_user`/`_get_user_email`) ليقبل `tenant_id: int` (متاح أصلًا في نطاق كل نقطة استدعاء)، واستبدال `.get_user(user_id)` بـ`.get_by_id(user_id, tenant_id)`. **صفر إضافة `try/except` جديد** — الإصلاح يقتصر على تصحيح الاستدعاء المكسور فقط.
- `communications`: **استثناء معماري** — الغرض من `_get_user_tenant` هو اكتشاف `tenant_id` نفسه، فلا يوجد `tenant_id` متاح في أي نقطة استدعاء أصلًا (الحل المعتاد لا ينطبق). الحل المعتمَد: **method جديدة على `UserRepository`**، `get_tenant_id_by_user_id(user_id) -> Optional[int]`، تبحث بـ`user_id` وحده عبر كل الـtenants وترجع `tenant_id` فقط — قرار **least-privilege** (أقصى ضرر ممكن لو استُخدمت غلط هو تسريب `tenant_id` فقط، مش بيانات مستخدم كاملة).
- `communications:36` و`health:54`: **بلا لمس عمدًا** — dead code مؤكَّد (صفر مستدعٍ حي في المشروع كله).

## القايمة الكاملة الـ5 مواضع وحالة كل موضع

| # | الملف:السطر | الآلية | نقاط الاستدعاء | الحل |
|---|---|---|---|---|
| 1 | `employment/service.py:87` | `_get_user` | `_register_affiliate_commission:100` (صامت)، `_calculate_ai_match_score:132` (صامت — ميزة AI matching كانت معطَّلة 100%)، **`app/tasks/employment.py:308`** (خارجية، `pay_payroll_task` — كانت تفشل دفع الرواتب فعليًا وتُعاد المحاولة 3 مرات) | معامل `tenant_id` جديد بالتوقيع |
| 2 | `digital_twin/service.py:53` | `_get_user` | `_register_affiliate_commission:71` (صامت)، **`interact_with_twin:180`** (عبر `_get_user_email` — كانت كسر واضح 500 داخل `begin_nested()` بلا أي `try/except`) | معامل `tenant_id` جديد بالتوقيع |
| 3 | `communications/service.py:29` | `_get_user_tenant` — **استثناء معماري** | `send_notification:63`، `send_mail:144` (`sender_tenant`)، `send_mail:145` (`recipient_tenant`) — الثلاثة بلا أي حماية `try/except`، كانت كسر واضح 500 لكل استدعاء API | method جديدة `UserRepository.get_tenant_id_by_user_id` (least privilege) |
| 4 | `communications/service.py:36` | `_get_user_email` | صفر مستدعٍ حي | **بلا لمس — Dead code، توثيق فقط** |
| 5 | `health/service.py:54` | `_get_user_email` | صفر مستدعٍ حي | **بلا لمس — Dead code، توثيق فقط** |

خارج النطاق (تحقَّق منه وتم استبعاده عمدًا): `identity/service.py:238` — `UserService.get_user()` الحقيقية (method معرَّفة على `UserService` نفسها، مش على `UserRepository`)، صحيحة 100%.

## ⚠️ اكتشاف جانبي حي أثناء التحقق — سلسلة `affiliate`/Backlog #10 وصلت لحالة موحَّدة كاملة (توثيق فقط، خارج نطاق هذه الجلسة صراحة)

`_register_affiliate_commission` في كل من `employment` و`digital_twin` بتوصل الآن بنجاح لـ`get_by_id` وتجيب المستخدم الصحيح تمامًا (Backlog #8 مُصلَح ومؤكَّد حيًا)، لكنها فورًا بعدها بتصطدم **بنفس طبقة الفشل الموحَّدة الموثَّقة في جلسة #1**: `User.referred_by` غير موجود إطلاقًا كحقل على الموديل → `AttributeError` (مُبتلَعة بنفس `try/except` الموجود، صمت مُسجَّل).

**بهذا، كل الـ12 دومينًا** المرتبطة بسلسلة `affiliate`/Backlog #10 (الـ10 من جلسة #1 + `digital_twin` و`employment` هنا) **وصلت الآن لنفس طبقة الفشل الموحَّدة الوحيدة المتبقية** — `User.referred_by`. هذا هو **الحاجز الوحيد الباقي** لإغلاق Backlog #10 نهائيًا (صفر إصلاح له هنا — خارج النطاق صراحة، قرار تصميمي مستقل).

الاختبارات هنا **تتوقع وتتسامح مع** هذا الـ`AttributeError` تحديدًا (`assert any("referred_by" in r ...)` — يثبت إن `get_by_id` نجح فعلًا)، بينما **ترفض بشكل قاطع** أي إشارة لـ`AttributeError` خاص بـ`get_user` نفسها (كان سيثبت رجوع Backlog #8).

## إيه اللي بيتحقق منه هذا الملف

**11 اختبارًا** يغطون الـ8 نقاط استدعاء الحية + موضعي الـdead code + الـmethod الجديدة:

| # | الاختبار | ما بيثبته |
|---|---|---|
| 1 | `test_employment_get_user_correct_and_wrong_tenant` | tenant صحيح → `User` صحيح؛ tenant خاطئ → `None` (عزل tenant) |
| 2 | `test_employment_get_user_email_correct_and_wrong_tenant` | يغطي نقطة `app/tasks/employment.py:308` — تأكيد نصي إن المهمة بقت بتمرر `tenant_id` + تحقق حي على مستوى `_get_user_email` |
| 3 | `test_employment_calculate_ai_match_score_passes_tenant_id` | تأكيد نصي إن `_calculate_ai_match_score` بقت بتمرر `job.tenant_id` — بلا تشغيل AI agent حقيقي (تفاديًا لتكلفة/تعقيد غير ضروري) |
| 4 | `test_employment_register_affiliate_commission_reaches_referred_by_layer` | tenant صحيح → يصل لـ`referred_by`؛ tenant خاطئ → صمت تام |
| 5 | `test_digital_twin_get_user_correct_and_wrong_tenant` | tenant صحيح → `User` صحيح؛ tenant خاطئ → `None` |
| 6 | `test_digital_twin_get_user_email_correct_and_wrong_tenant` | يغطي نقطة `interact_with_twin:180` (كانت كسر 500 مباشر) |
| 7 | `test_digital_twin_register_affiliate_commission_reaches_referred_by_layer` | نفس نمط #4 |
| 8 | `test_user_repository_get_tenant_id_by_user_id` | الـmethod الجديدة مباشرة — مستخدم حقيقي → `tenant_id` صحيح؛ مستخدم غير موجود → `None` |
| 9 | `test_communications_get_user_tenant_correct_user` | تأكيد نصي إن الثلاث نقاط استدعاء (`send_notification:63`, `send_mail:144/145`) لسه بتنادي `_get_user_tenant` + تحقق حي إن الأخيرة بترجع `tenant_id` صحيح عبر الـmethod الجديدة |
| 10 | `test_communications_get_user_email_left_untouched_as_documented_dead_code` | **يوثِّق ويقفل** الحالة الحالية (لسه بتستخدم `.get_user(` المكسورة) عمدًا |
| 11 | `test_health_get_user_email_left_untouched_as_documented_dead_code` | نفس نمط #10 |

## بيانات throwaway
- مستخدم واحد جديد لكل اختبار (`UserService.register`، بادئة `p8audit_*` + `uuid4` فريد) — صفر إعادة استخدام بيانات من جلسات سابقة.
- تنظيف كامل في `finally`: `delete(User)` + `commit()`.
- تحقق مستقل بعد تشغيلتين متتاليتين: `SELECT count(*) FROM users WHERE email LIKE 'p8audit\_%'` = **0**.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_user_repository_get_user_audit.py -v
```
يحتاج قاعدة `eppne_v2` حقيقية شغّالة (Docker `eppne_db`، منفذ 5435).

**آخر تشغيل مُوثَّق [2026-08-19]:** 11 passed (تشغيلتان متتاليتان، صفر تذبذب). تحقق مستقل إضافي أكَّد **صفر بيانات throwaway متبقية**. تشغيل شامل لكل `tests/` بعد هذه الجلسة: **71 passed, 4 xfailed** (60 السابقة + 11 الجديدة) — صفر تأثير جانبي، صفر اختبار انكسر.
