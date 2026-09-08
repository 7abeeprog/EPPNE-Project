# قرارات مطلوبة منك — استكمال جلسة constructor-mismatch-backlog

**تاريخ:** 2026-08-27
**الحالة:** صفر تنفيذ فوري. كل بند تحت رقم منفصل — رد بالأرقام اللي موافق عليها (أو "كله" / "ولا
واحد" / تعديل على أي بند).

**المرجع:** نتاج جلستي أمس — `.claude/reports/constructor-mismatch-backlog-11-plus-6-mapping.md`،
`.claude/reports/constructor-mismatch-backlog-remaining-approval-table.md`، والتحديث المباشر على
`constructor-mismatch-backlog-classification.md` + `PROGRESS_LOG.md`.

---

## 1. توثيق فجوة الـ9 بنود القديمة (#1, #5, #6, #7, #8, #9, #11, #14, #15)

مُصلَحة ومؤكَّدة من 2026-08-18 لغاية 2026-08-25 حسب `PROGRESS_LOG.md`، لكن لسه غير معلَّمة ✅ في
`constructor-mismatch-backlog-classification.md` — نفس فجوة `55032eb` بالظبط، بس أقدم بشهر.

**السؤال:** أطبِّق عليهم نفس معاملة أمس (اقتباس دليل حي من التقارير الأصلية لكل بند + علامة ✅ في
صف كل بند بالملف الموحَّد)؟ لو أيوه — كلهم دفعة واحدة، ولا نبدأ بعيّنة (مثلًا #11 بس، أعلى أولوية
موثَّقة) للمراجعة قبل الباقي؟

---

## 2. بقية #27 (`arbitration-syndicates-repository-missing-methods`)

`list_user_cases` وحدها اتصلحت. 4 دوال (`get_cases_by_claimant`, `get_election_votes`,
`get_syndicate_memberships`, `list_user_licenses`) + `list_candidates` لسه مكسورة فعليًا — تعطّل
`GET /syndicates/{id}/elections`, `GET /elections/{id}/candidates`, `GET /licenses/me` (بيرجع `[]`
صامت).

**السؤال:** جلسة إصلاح منفصلة مخصَّصة للـ4+1 دوال دول، ولا يُتركوا في الـbacklog لحد جلسة تصنيف
تانية؟

---

## 3. #31 (`frontend-service-url-prefix-mismatch`)

يبدو مُصلَحًا فعليًا عبر commit `6b4703a` (2026-08-26) — لكن غير مُتحقَّق منه بمنهجية "اقتباس حي"
زي باقي البنود، وغير معلَّم في الملف الموحَّد.

**السؤال:** أراجع commit `6b4703a` + `frontend-url-prefix-comprehensive-audit-session-log.md`
لاستخراج دليل التحقق الحي وأعلِّمه في الملف الموحَّد (زي ما عملت مع الـ6 بنود أمس)؟

---

## 4. البنود "سطر واحد / ميكانيكي" (7 بنود جاهزة للتنفيذ المباشر)

`#22` (ترتيب routes)، `#32` (kwarg اسم خطأ)، `#33` (naive/aware datetime)، `#37` (`.tx_hash` بدل
كائن `Transaction` — 4 مواضع)، `#40` (توقيع `execute_agent_action` قديم)، `#43` (export/import
mismatch)، `#38` (فلترة عمود خطأ).

**السؤال:** أبدأ التنفيذ؟ لو أيوه — كلهم في جلسة واحدة، ولا أرتّبهم حسب الأثر (مثلًا #37 أولًا —
4 مواضع مالية عبر 3-4 دومينات)؟ ولا نأجّل التنفيذ ونكتفي بالتصنيف دلوقتي؟

---

## 5. Migration بسيطة (بندان: #28, #45)

`#28` — بيانات seed ناقصة (`saas_service_catalog`) لـ3 دومينات. `#45` — قيد unique عالمي يحتاج
partial unique index (غير مؤكَّد حيًا).

**السؤال:** ننفّذ #28 (بيانات فقط، صفر كود) الآن؟ #45 يحتاج تأكيد حي أولًا (تينانتين + نص مطابق) —
أعمل التحقق الحي الأول قبل أي migration؟

---

## 6. البنود اللي تحتاج قرار تصميمي (7 بنود — مش تنفيذ مباشر)

بقية `#10` (`identity-user-referred-by-field-missing`)، بقية `#16` (`commit`-جوه-`begin_nested`)،
`#21` (`Invoice.metadata` collision)، `#29` (`hold_funds`/`release_held_funds` غير موجودتين)،
`#30` (صفر router للقراءة)، `#39` (جداول `transport` غير موجودة)، `#41`
(`issuer_entity_id`/`reviewer_id` مقارنة خاطئة — تحذير أمني إضافي).

**السؤال:** أي واحد فيهم يستاهل جلسة نقاش/تصميم أولى؟ ولا نأجّل السبعة لحد ما نخلّص المجموعات
الأسهل فوق؟

---

## 7. بنود تحتاج جرد (`grep`) قبل أي تصنيف نهائي

بقية `#4` (`process_auto_renewals`/`can_access_service` — غير مؤكَّدين DB-level)، `#13` (اسم kwarg
`InvoicingService.create_invoice` عبر باقي الـ12 دومين).

**السؤال:** أشغّل جلسة جرد (توثيق فقط، صفر إصلاح) للاتنين دول؟

---

## 8. تحديث الأقسام المتبقية في الملف الموحَّد نفسه

"🔴 المجموعة أ"، "🟢 المجموعة ب"، و"الخلاصة العملية" في
`constructor-mismatch-backlog-classification.md` لسه بتعكس العدّ القديم (زي ما وضَّحت الملاحظة
اللي أضفتها أمس) — الأعداد/القوائم مش متسقة مع العلامات الجديدة.

**السؤال:** أعيد كتابة الأعداد/القوائم دي لتطابق الحالة الحالية (بعد كل التحديثات، بما فيها لو
اتنفذ أي من البنود فوق)، ولا نسيبها كمرجع تاريخي زي ما هي؟

---

## 9. Commit الشغل

تعديلات أمس (`constructor-mismatch-backlog-classification.md` + `PROGRESS_LOG.md`) لسه غير
مُلتزَم بها. **الشجرة فيها كمان تعديلات سابقة غير مرتبطة بهذه الجلسة إطلاقًا** (`security.py`،
`main.py`، `health/service.py`، `tasks/affiliate.py`، `tasks/billing.py`، `conftest.py`، وملفات
frontend/academy) — نفس الملاحظة اللي ظهرت في `constructor-mismatch-backlog-cleanup-session-log.md`
قبل كده (commit `55032eb` نفسه اتأخر لنفس السبب).

**السؤال:** أعمل commit منفصل بس للملفين اللي عدّلتهم أنا النهاردة (توثيق فقط)، بمعزل عن باقي
التعديلات غير المرتبطة؟

---

**رد بالأرقام اللي موافق عليها، أو وضّح أي تعديل على الترتيب/النطاق.**
