# سجل التقدم (Progress Log)

للسياق التاريخي الكامل قبل 2026-08-18، راجع `PROGRESS_LOG_ARCHIVE_2026-08-18.md`.

سجل تراكمي لكل مهمة مكتملة في المشروع. **بدءًا من 2026-08-18، جدول الـBacklog تحت هو مصدر الحقيقة الوحيد لحالة كل بند — يُحدَّث بالتعديل في مكانه، مش بالإضافة في الآخر.** قائمة الجلسات المُقفلة بس هي append-only (سطرين لكل جلسة جديدة تُقفَل).

---

## 📌 بانر الحالة [آخر تحديث: 2026-08-18]

آخر إغلاق رسمي: **Backlog #11a (فرع `invitations` فقط)** — راجع الجدول تحت. **⚠️ تصحيح صريح على القرار السابق:** بند #11 **مُغلَق جزئيًا بس** — الفرع الأصلي (#11b، نفس السبب الجذري `commit()`-جوه-`begin_nested()` لكن عبر `InvoicingService.create_invoice` مش `identity`) **لسه مفتوح تمامًا، صفر إصلاح عليه، يحتاج جلسة منفصلة.** **نطاقه المؤكَّد حيًا [2026-08-18]: `realestate`/`insurance` فقط (4 دوال) — `service_marketplace`/`arbitration_syndicates` كانا مذكورين سابقًا كافتراض من الأرشيف، اتضح بالقراءة المباشرة إنهما غير مشمولين (راجع بند #11b في الجدول تحت للتفاصيل الكاملة).**

**⚠️ قيد نشط جديد [2026-08-18]:** Backlog #9 **معلَّقة رسميًا — ممنوع إصلاحها قبل إغلاق #11b.** جلسة تشخيص #9 اكتشفت إن `realestate`/`insurance` (4 دوال) بتعتمد حاليًا على كراش #9 كحماية بالصدفة من #11b، بنفس نمط `invitations`/#11a قبل إغلاقها — لكن هنا بفلوس حقيقية (`finance.transfer`) مش مجرد يوزر بلا محفظة. **#11b بقت أولوية حرجة نتيجة هذا الاكتشاف.** التفاصيل: `.claude/reports/saas-control-service-missing-methods-session-log.md`.

**استثناء throwaway-cleanup نشط (تنظيف روتيني غير عاجل، مش عاجل):** `users id=52` (دليل جلسة `invitations`) و`users id=71/72`/دعوات `sovereign_invitations_v2 id=2,3` (بيانات تحقق حي لنفس الجلسة).

---

## 🗂️ جدول الـBacklog النشط

**ملاحظة منهجية:** هذا الجدول أُعيد بناؤه [2026-08-18] من مسح كامل لـ`PROGRESS_LOG_ARCHIVE_2026-08-18.md` (27 بند: 25 مرقّم من قائمة الانتظار الرسمية + بندان بالاسم أُضيفا لاحقًا)، **زائد بندين إضافيين من `sovereign_entities` أُضيفا يدويًا بناءً على توجيه صريح**. **لم يُجرَ تدقيق شامل يضمن أن كل اكتشاف تاريخي في الأرشيف انعكس هنا** — أي بند تاريخي يظهر لاحقًا وغير موجود في هذا الجدول، ارجع للأرشيف كمرجع نهائي وأضِفه هنا وقتها.

| # | العنوان المختصر | الحالة | مرجع |
|---|---|---|---|
| 1 | `user-repository-get-by-id-audit` — 15 موضع `tenant_id` ناقص في `UserRepository.get_by_id` | 🔴 مفتوح — أولوية مرفوعة (فقدان عمولات affiliate صامت مؤكَّد حيًا) | أرشيف ~3068 |
| 2 | `duplicate-kwarg-audit` — 4+ حالات `multiple values for keyword` | 🔴 مفتوح | أرشيف ~3069 |
| 3 | استكمال Phase 16 الأصلي | 🟡 غير واضح — علاقته بـ`.claude/reports/phase16-session-log.md` (commits `2d4ef59`/`ab73c8c`) غير مؤكَّدة 100% | أرشيف ~3070 |
| 4 | `silent-write-regression` — حالتان غير مؤكَّدتين DB-level (`saas.process_auto_renewals` فرع except، `saas.can_access_service`) | 🔴 مفتوح | أرشيف ~3071 |
| 5 | `sovereign_entities` — قرار منتجي معلَّق (4 endpoints) | 🔴 مفتوح — تطوّر لاحقًا لاكتشاف أخطر (راجع بند `sovereign_entities-auth` تحت) | أرشيف ~3072 |
| 6 | `commerce.visa_webhook` مراجعة أمنية | 🔴 مفتوح، لم يبدأ | أرشيف ~3073 |
| 7 | `redis-client-wrapper-missing-methods` (`hincrbyfloat`, `setnx`) | 🔴 مفتوح | أرشيف ~3074 |
| 8 | `user-repository-get-user-audit` (method غير موجودة، 6 مواضع) | 🔴 مفتوح | أرشيف ~3075 |
| 9 | `saas-control-service-missing-methods` (`get_active_subscription`) | 🟡 **معلَّقة — محظورة بسبب #11b [2026-08-18]** — تشخيص كامل تم؛ اكتشاف حي إن `realestate`/`insurance` (4 دوال) بتعتمد حاليًا على كراش #9 كحماية بالصدفة من #11b المفتوح (نفس نمط #11a قبل إغلاقها). صفر كود على #9 لحد ما يُغلق #11b رسميًا. | `.claude/reports/saas-control-service-missing-methods-session-log.md` |
| 10 | `affiliate-service-missing-methods` | 🔴 مفتوح | أرشيف ~3077 |
| 11a | `invitations-user-registration-savepoint-leak` (امتداد #11، فرع `invitations`) | ✅ **مُغلَق رسميًا [2026-08-18]** | `.claude/reports/invitations-savepoint-leak-session-log.md` |
| 11b | `realestate-invoicing-savepoint-conflict` (النطاق المؤكَّد حيًا [2026-08-18]: `realestate`/`insurance` فقط — راجع ملاحظة النطاق تحت) | 🔴🔴 **أولوية حرجة [2026-08-18] — يحجب #9 أيضًا، إصلاح فوري مطلوب.** مؤكَّد حيًا بالقراءة المباشرة: `realestate.buy_fractional_ownership`/`rent_unit` و`insurance.subscribe`/`review_claim` (4 دوال فقط، تحويلات مالية حقيقية جوه `begin_nested()` مقفولة بـ`commit()` مباشر في `invoicing.create_invoice`) — تفاصيل كاملة + جدول أدلة في `.claude/reports/saas-control-service-missing-methods-session-log.md` قسم 4. **تصحيح نطاق صريح على العنوان القديم (كان بيذكر `service_marketplace`/`arbitration_syndicates` كجزء من "الفرع الأصلي" بناءً على افتراض من الأرشيف فقط، غير مؤكَّد بقراءة كود مباشرة وقتها):** (أ) `arbitration_syndicates` — 3 مواضع `invoicing.create_invoice` فُحصت مباشرة (`create_dispute`, `join_syndicate`, `issue_license`) ووُجدت **الثلاثة خارج أي `begin_nested()` فعليًا** — **آمنة، مش جزء من #11b**، لا تحتاج إصلاح ضمن هذا البند. (ب) `service_marketplace` — `_check_saas_limits` بتاعتها بتنادي `can_access_service` مش `get_active_subscription` إطلاقًا، فمحجوبة حاليًا ببج مختلف تمامًا (**Backlog #12**، `wrong-arity call`) — **صفر علاقة بـ#11b أو بكراش #9**. | أرشيف ~3078، 3104، 3132؛ دليل حي إضافي/تصحيح النطاق: `.claude/reports/saas-control-service-missing-methods-session-log.md` قسم 4.5 |
| 12 | `saas-control-service-wrong-arity-call` | 🔴 مفتوح | أرشيف ~3111 |
| 13 | `invoicing-create-invoice-wrong-kwarg` | 🔴 مفتوح | أرشيف ~3114 |
| 14 | `audit-log-wrong-kwargs` | 🔴 مفتوح، أولوية عالية (grep شامل غير منفَّذ) — تأكيد إضافي [2026-08-18] داخل `invitations.accept_invitation` نفسها | أرشيف ~3137، 3407 |
| 15 | `ai-governance-check-and-consume-wrong-kwarg` | 🔴 مفتوح | أرشيف ~3138 |
| 16 | `ai-agents-execute-agent-action-wrong-kwarg` | 🔴 مفتوح (محمي جزئيًا بـ`try/except` في بعض المواضع) | أرشيف ~3158 |
| 17 | `arbitration-case-model-idempotency-key-mismatch` | 🔴 مفتوح — عائق بنيوي | أرشيف ~3159 |
| 18 | `finance-service-create-invoice-does-not-exist` (`transport`) | 🔴 مفتوح | أرشيف ~3160 |
| 19 | `cross-tenant-scheduled-task-vs-constructor-mismatch` (8+1 مواضع) | 🔴 مفتوح، توثيق فقط بقرار صريح | أرشيف ~3161-3162 |
| 20 | `missing-tenant-id-in-background-task-signature` | 🔴 مفتوح | أرشيف ~3163 |
| 21 | `billing-tasks-saas-subscription-import-error` (حاجب موديول) | 🔴 مفتوح — يحجب كل tasks الملف | أرشيف ~3164 |
| 22 | `finance-transfer-tx-hash-type-mismatch` (نمط في 8 ملفات، 2 مؤكَّدة) | 🔴 مفتوح، 6 ملفات غير مؤكَّدة بعد | أرشيف ~3165 |
| 23 | `invoicing-list-invoices-wrong-kwarg` | 🔴 مفتوح | أرشيف ~3168 |
| 24 | `invoicing-get-invoice-stats-wrong-arity` | 🔴 مفتوح | أرشيف ~3169 |
| 25 | `invoicing-get-invoice-null-tenant-admin-bypass-broken` | 🔴 مفتوح | أرشيف ~3171 |
| — | `invitations-missing-expiry-max_uses-validation` | 🔴 مفتوح، أولوية أعلى من العادي | أرشيف ~3344 |
| — | `sovereign_invitations_v2` أعمدة nullable بلا `NOT NULL`/server-default | 🟡 مفتوح، أولوية منخفضة | أرشيف ~3380 |
| — | **`sovereign_entities-unauthenticated-endpoints`** — 4 endpoints (`list_entities`, `get_entity`, `list_templates`, `list_components`) بلا `current_user` في توقيعها؛ **مصححة لاحقًا لكامنة (latent) مش حية حاليًا** — محمية بالصدفة بباج `SimpleTenant` مستقل (نفس نمط "حماية بالصدفة" زي Backlog #9/#11a)؛ إصلاح ذاك الباج بمعزل عن هذا سيفتح تسريب `treasury_balance_mrusdt`/`kyb_status` عبر تينانتات لحسابات `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` | 🔴 **صفر إصلاح — بانتظار توجيه/قرار منتجي صريح** | أرشيف ~2778-2842 (بلا ملف تقرير مستقل، جوه سياق `.claude/reports/simpletenant-fix-session-log.md`) |
| — | `sovereign_entities.review_kyb`/`update_entity` — فقدان كتابة صامت (الـresponse بيرجع القيمة الجديدة، الـDB فاضلة بالقديمة؛ `repo.update_entity` flush-only بلا `begin_nested()`/`commit()` محيط) + 3 حالات مشابهة في `saas` | 🟡 **غير مصنَّف — يحتاج تأكيد لاحقًا** (نُقل كمرجع فقط، بلا فحص كود إضافي؛ قد يتداخل مع بند #4) | أرشيف ~2846-2863 (بلا ملف تقرير مستقل، جوه سياق `.claude/reports/simpletenant-fix-session-log.md`) |

---

## 📋 الجلسات المُقفلة

- **P0 إصلاح الثغرات الأمنية الحرجة [2026-08-08]** — ✅ مكتمل. عزل `tenant_id` في `iot`/`privacy` (10 migrations)، حماية `PUT /api/ai/routing`، توحيد حماية `auth_router`. 5/5 smoke tests ناجحة. بلا ملف تقرير مستقل — موثَّق كاملًا في الأرشيف.
- **P1 Backend — آلية جلسة `identity` حقيقية (Phase 0+1) [2026-08-08]** — ✅ مكتمل ومُتحقَّق E2E (تخزين/إبطال refresh tokens فعلي). بلا ملف تقرير مستقل.
- **Phase 2 Frontend — توحيد auth→identity على كوكيز [2026-08-09]** — ✅ مكتمل (commit `5b1d241`)، `AuthProvider.tsx` يستعلم `GET /identity/me`. بلا ملف تقرير مستقل.
- **Phase 3 Frontend — Rename `components/auth`→`identity` [~2026-08-09/10]** — ✅ الكود مكتمل ومتحقَّق (`tsc` نظيف + مقارنة `git worktree` baseline). ⏸️ اختبار logout اليدوي بالمتصفح **لسه معلَّق** — باج منفصل تمامًا (`lit`/`@reown/appkit-ui`) غير مرتبط بـPhase 3 نفسها.
- **Phase 4 Backend — حذف دومين `auth` بالكامل [2026-08-10]** — ✅ مكتمل، مع بند واحد مؤجَّل صراحة (تأكيد `pytest`/`GET /docs` خالي من `/auth/*`). خطة: `.claude/plans/phase4-remove-auth-backend.md`.
- **transaction-savepoint-bug — إصلاح منهجي `commit()`-جوه-`begin_nested()` عبر 24 دومين [2026-08-13]** — 🟡 **مكتمل كودًا، لكن غير مُغلَقة بالكامل** — التحقق الحي (DB-level، مش status code) أُنجز لـ3 دومين فقط من الـ24. تقرير: `.claude/reports/transaction-savepoint-bug-session-log.md`.
- **simpletenant-fix — إصلاح `SimpleTenant` type-mismatch [~2026-08-13]** — 🟡 مختلط: أصلحت `finance`/`command` بنجاح مؤكَّد، لكن كشفت 4 دومينات إضافية متأثرة + اكتشافين حرجين منفصلين تمامًا (`sovereign_entities`-auth أعلاه، و`review_kyb`/`update_entity` فقدان كتابة صامت) لم يُغلَقا. تقرير: `.claude/reports/simpletenant-fix-session-log.md`.
- **constructor-mismatch (+ batch3) — service constructors بمعاملات ناقصة، 111 موضع [2026-08-14 → 2026-08-17]** — ✅ نطاقها الضيق (توقيعات الـconstructor نفسها) يبدو مكتملًا عبر الدفعات الثلاث، **لكنها فتحت 25 بند Backlog جانبي غير مُغلَقين** (راجع الجدول فوق). تقارير: `.claude/reports/constructor-mismatch-session-log.md`, `.claude/reports/constructor-mismatch-batch3-session-log.md`, `.claude/reports/constructor-mismatch-backlog-classification.md`.
- **invitations-savepoint-leak — يوزر بلا محفظة عبر `accept_invitation` [2026-08-18]** — ✅ **مُغلَق رسميًا** (Backlog #11a). نقل استدعاء إنشاء اليوزر بره `begin_nested()` + تثبيت `idempotency_key`، تحقق حي كامل (سيناريو نظيف + retry). تقرير: `.claude/reports/invitations-savepoint-leak-session-log.md`.

**⚠️ لم تُراجَع بثقة كافية في هذا الفهرس (موجودة كملفات في `.claude/reports/` لكن حالتها النهائية غير مُدمَجة هنا):** `silent-write-regression-session-log.md`، `phase16-session-log.md`، ملفات `.claude/reports/CRITICAL-*.md` الأخرى غير المذكورة أعلاه. راجع الأرشيف أو الملفات نفسها عند الحاجة.
