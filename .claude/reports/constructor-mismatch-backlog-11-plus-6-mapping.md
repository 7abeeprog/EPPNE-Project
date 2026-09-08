# ربط الـ11 بند + الـ6 أعطال بأرقام constructor-mismatch-backlog-classification.md

**تاريخ:** 2026-08-26
**الحالة:** ✅ جرد/ربط فقط — صفر تنفيذ كود في هذا الملف نفسه.
**سياق:** استكمال مباشر لـ`.claude/reports/constructor-mismatch-backlog-review-clarification-needed.md`
(السؤال اللي كان مفتوح هناك اتحل — الاسمان "technical-debt-cleanup"/"backend-bugs-cleanup" مش
أسماء ملفات حرفية، طلع إنهم إشارة لـ commit-ين حقيقيين موثَّقين، مذكورين تحت).

---

## المصدران الفعليان

| الاسم اللي استُخدم في السؤال | المصدر الحقيقي | تاريخ/وقت | التوثيق |
|---|---|---|---|
| `technical-debt-cleanup` | commit `55032eb` — "fix(constructor-mismatch): resolve 11 backlog items — kwarg drops to schema migrations" | 2026-08-25 11:16 | `.claude/reports/constructor-mismatch-backlog-cleanup-session-log.md` + `.claude/reports/constructor-mismatch-backlog-classification-update-2026-08-25.md` (التصنيف المسبق) |
| `backend-bugs-cleanup` | commit `f17636c` — "fix(backend): close 6 backend defects surfaced by #31 URL-prefix verification, incl. new arbitration_syndicates IDOR" | 2026-08-26 20:18 | `PROGRESS_LOG.md` سطر 250 (باسم `backend-fixes-post-url-prefix-audit`) + `.claude/reports/frontend-url-prefix-comprehensive-audit-session-log.md` §16-21 |

**ملاحظة مهمة اكتُشفت أثناء الجرد:** جلسة `55032eb` **لا يوجد لها إدخال في قسم "📋 الجلسات
المُقفلة" بـ`PROGRESS_LOG.md` إطلاقًا** — فقط 3 اكتشافات جانبية منها موثَّقة هناك (أسطر 202-204:
`invoicing-invoice-model-metadata-attribute-collision`،
`ai-governance-audit-log-decimal-not-json-serializable`،
إعادة تأكيد `ai-governance-usage-log-idempotency-wrong-arity`) — الملخص التنفيذي للجلسة نفسها غايب
من الفهرس. جلسة `f17636c` بالمقابل موثَّقة بإدخال كامل (سطر 250).

---

## الجدول 1 — الـ11 بند (commit `55032eb`)

| # | الإصلاح المُنفَّذ | الدومين | البند المقابل في `constructor-mismatch-backlog-classification.md` | معلَّم ✅ في الملف؟ |
|---|---|---|---|---|
| 1 | `saas.can_access_service` — حذف `tenant_id=` الزايدة | 5 دومينات (`service_marketplace`, `tenders_auctions`, `tourism_sports`, `transport`, `zamakana`) | **#12** `saas-control-service-wrong-arity-call` | ❌ **لا** — لسه 🔴 مركزي بلا أي ملاحظة إغلاق في الجدول الموحَّد |
| 2 | `invoicing.list_invoices` — حذف `tenant_id=` غير المقبولة | `invoicing` | **لا يوجد رقم بالملف** — بج منفصل عن #13 (اللي بيخص `create_invoice`، مش `list_invoices`)، غير مُدرَج فيه أصلًا | — N/A |
| 3 | `invoicing.get_invoice_stats` — إصلاح ترتيب بناء الـservice + حذف معامل زايد | `invoicing` | **لا يوجد رقم بالملف** | — N/A |
| 4 | `commerce.create_payment_request` — حذف `tenant_id` من الـdict | `commerce` | امتداد لـ**#2** `duplicate-kwarg-audit` | ❌ **لا** |
| 5 | `sovereign_entities.create_entity` — حذف السطر المكرِّر لـ`tenant_id` | `sovereign_entities` | امتداد لـ**#2** كمان | ❌ **لا** |
| 6 | `ai_governance` check-and-consume — إصلاح تعامل الراوتر مع `bool` كأنه `dict` | `ai_governance` | **لا يوجد رقم بالملف** (مختلف عن #15 — #15 عن kwarg غلط في نداء `check_and_consume`، هنا عن تفسير الناتج الراوتر بعد النجاح) | — N/A |
| 7 | `saas-test-reqsector` — إصلاح صفَّي throwaway (`UPDATE`) | `saas` | **لا يوجد رقم بالملف** — تنظيف بيانات، مش نمط `constructor-mismatch` | — N/A |
| 8 | `arbitration_syndicates` — إضافة عمود `idempotency_key` (migration `037`) | `arbitration_syndicates` | **#17** `arbitration-case-model-idempotency-key-mismatch` | ❌ **لا** |
| 9 | `academy.create_bootcamp` — إضافة عمود `instructor_id` (migration `038`) | `academy` | **#20** `academy-create-bootcamp-instructor-id-mismatch` | ❌ **لا** |
| 10 | `projects` — توسيع 3 موديلات (`Project`/`Contribution`/`ProjectUpdate`، migration `039`) | `projects` | **#19** `projects-schema-model-field-mismatch` | ❌ **لا** |
| 11 | `transport` — رُبِط بـ`InvoicingService` (بدل بناء method جديدة على `FinanceService`) | `transport` | **#18** `finance-service-create-invoice-does-not-exist` | ❌ **لا** |
| — | `ai_governance._check_agent_ownership` — تصميم/تنفيذ فعلي عبر `agent.owner_id` | `ai_governance` | **لا يوجد رقم بالملف** | — N/A |

**خلاصة الجدول 1:** من أصل 11 إصلاحًا، **7 لها رقم فعلي بالملف** (#12، #2 ×2 مواضع، #17، #18، #19،
#20) — **صفر واحد منهم معلَّم ✅**. لسه كلهم بالملف الرئيسي بحالة "🔴 مفتوح"/"🔴 مركزي" بلا أي
تحديث، رغم إصلاحهم كودًا وتحققًا حيًا كاملًا موثَّق في `constructor-mismatch-backlog-cleanup-session-log.md`.
حتى جدول PROGRESS_LOG.md **الداخلي** (سطور 159-168، فهرس مختلف برقمنة موازية) لسه بيقول
"🔴 مفتوح" لـ#12/#17/#18 بلا تصحيح.

---

## الجدول 2 — الـ6 أعطال (commit `f17636c`)

| # | الإصلاح المُنفَّذ | الدومين | البند المقابل في `constructor-mismatch-backlog-classification.md` | معلَّم ✅ في الملف؟ |
|---|---|---|---|---|
| 1 | alias مضلِّل لـ`redis_client` (يُستدعى كـfactory) | `translation` | **#47** `translation-redis-client-singleton-called-as-factory` | ✅ **نعم** |
| 2 | `get_dashboard` بترجع ORM object بدل dict | `command` | **لا يوجد رقم بالملف** — اكتشاف جديد كليًا، لم يُدرَج فيه من الأساس | — N/A |
| 3 | `required_skills`/`required_certificate_ids` — `None` بدل `[]` | `employment` | **لا يوجد رقم بالملف** | — N/A |
| 4 | `terms_and_conditions` — عمود Nullable مقابل schema غير Optional | `insurance` | **#46** `insurance-policies-response-validation-terms-and-conditions-null` | ✅ **نعم** |
| 5 | صفوف قديمة (list + detail) — `click_count`/`discount_percentage`/`gift_coins_amount`/`gift_currency` | `invitations` | **#25** `invitations-legacy-invitation-rows-response-validation-error` | ✅ **نعم** |
| 6 | `list_user_cases` — بلا `tenant_id` أصلًا (arity + IDOR حقيقي) | `arbitration_syndicates` | **#27** `arbitration-syndicates-repository-missing-methods` | 🟡 **جزئيًا فقط** — `list_user_cases` وحدها اتصلحت، 4 دوال أخرى + `list_candidates` لسه مفتوحين ومُوثَّقين كـ"باقي بانتظار إصلاح منفصل" |

**خلاصة الجدول 2:** هنا العكس — الملف **مُحدَّث بدقة**: 4 من 6 معلَّمة ✅ (أو ✅ جزئي)، والاثنان
الباقيان (`command.get_dashboard`، `employment`) أصلًا مش من بنود الملف من الأساس (اكتشافات جديدة
لم تُدرَج فيه). commit `f17636c` نفسه بيقول صراحة في رسالته: *"Backlog #25, #27, #46, #47 ...
marked fixed; PROGRESS_LOG.md updated"* — وده مطابق تمامًا للواقع المُتحقَّق منه هنا.

---

## الفرق الجوهري بين الجلستين

جلسة `f17636c` (الأحدث، 2026-08-26) **حدَّثت `constructor-mismatch-backlog-classification.md`
فعليًا بعد كل إصلاح** (✅ + تاريخ + تفاصيل التحقق الحي مباشرة في نفس صف البند). جلسة `55032eb`
(الأقدم بيوم، 2026-08-25) **لم تُحدِّث الملف إطلاقًا** رغم إصلاح 7 بنود مرقّمة منه (#2 ×2، #12،
#17، #18، #19، #20) كودًا وتحققًا حيًا كاملًا — فجوة توثيقية حقيقية بين الكود الفعلي وحالة الملف
المرجعي، مش مجرد اختلاف تسمية جلسة.

---

## بانتظار توجيهك

هذا الملف جرد/ربط فقط — لم يُعدَّل `constructor-mismatch-backlog-classification.md` نفسه. القرارات
المحتملة التالية (لم تُنفَّذ، بانتظار توجيهك):
1. تحديث الجدول الموحَّد في `constructor-mismatch-backlog-classification.md` لتعليم #2، #12، #17،
   #18، #19، #20 بـ✅ (استكمال توثيقي بحت، صفر لمس كود).
2. المتابعة على السؤال الأصلي (عرض كل البنود المتبقية غير المُصلَحة مصنَّفة حسب سهولة الإصلاح) —
   الآن ممكن تُبنى بدقة على أساس هذا الربط (استبعاد #2، #12، #17، #18، #19، #20 كمان من أي جدول
   "متبقي"، مش بس #23-#26 كما طُلب أصلًا).
