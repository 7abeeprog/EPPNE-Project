# سجل التقدم (Progress Log)

للسياق التاريخي الكامل قبل 2026-08-18، راجع `PROGRESS_LOG_ARCHIVE_2026-08-18.md`.

سجل تراكمي لكل مهمة مكتملة في المشروع. **بدءًا من 2026-08-18، جدول الـBacklog تحت هو مصدر الحقيقة الوحيد لحالة كل بند — يُحدَّث بالتعديل في مكانه، مش بالإضافة في الآخر.** قائمة الجلسات المُقفلة بس هي append-only (سطرين لكل جلسة جديدة تُقفَل).

---

## 📌 بانر الحالة [آخر تحديث: 2026-09-22]

آخر إغلاق رسمي: **Batch 0-A — إصلاح أمني عاجل لعزل التينانت في دومين `insurance` (8 endpoints) [2026-09-21]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا (قبل/بعد عبر HTTP حقيقي، تينانتان throwaway، وتنظيف كامل zero-diff).**

خلفية: كانت 8 endpoints في `insurance` بتاخد التينانت من هيدر `X-Tenant-ID` (قيمته الافتراضية 1 لو غايب) — بما فيها اشتراك مدفوع وصرف تعويض يحرّكوا فلوس. الإصلاح: `current_user.tenant_id` (نمط `ai_agents`) + فحص انتماء المستفيد/الموظف للتينانت (D2) + عزل التينانت في `disburse_monthly_pensions` (الطبقة أ فقط). **لا migration.** التفاصيل والأدلة في قائمة الجلسات المُقفلة تحت و`.claude/reports/insurance-batch0a-tenant-isolation-session-log.md`.

**⚠️ تحذير ترتيب الإصلاح (مهم):** قرار **الدافع** في `disburse_monthly_pensions` (`sender_id=1` هاردكودد في `insurance/service.py:638` — مغطّى في `finance-transfer-hardcoded-system-account-real-fund-risk` [تحديث 2026-09-16]) **يجب أن يُحسَم قبل** إصلاح `idempotency_key` — وإلا فإصلاح المفتاح وحده يجعل الصرف يسحب فعليًا من محفظة `user_id=1`. الصرف حاليًا معطَّل فعليًا (`count=0`، لا فلوس تتحرك)، فالخطر كامن، لكنه قريب خطوة واحدة.

**حدود موثَّقة:** `insurance.submit_claim` **مكسور** (500 لأي مستخدم) و`disburse` **معطَّل فعليًا** — لذلك مسار نجاح `submit_claim` لم يُتحقَّق منه، والتحقق العابر للتينانت عليه يلزم إعادته بعد إصلاحه.

**بنود مفتوحة/موثَّقة نتيجة هذا الإغلاق (بدون تنفيذ):** (1) 🔴 `insurance-disburse-pensions-payout-logic-broken`، (2) 🔴 `insurance-submit-claim-500`، (3) 🟡 `insurance-review-claim-no-status-guard-and-random-payout-idempotency` — **غير مُتحقَّق منه، أولوية عالية (تحرّك فلوس)**، ليس ثغرة مؤكَّدة، (4) ⚪ `insurance-unused-tenant-header-dependencies`، (5) ⚪ `server-startup-index-creation-failure-and-cp1256-logging-errors` (خارج insurance)، (6) ⏸️ `insurance-batch0a-commits-pending` (قرار المستخدم/صاحب جلسة saas: تبعية migration 048). تحديث مؤرَّخ مضاف على البند الموجود `insurance-review-claim-payout-from-reviewer-personal-wallet` (بلا بند جديد)، وسطر تصحيح مؤرَّخ أسفل بند [2026-09-16] `insurance-disburse-pensions-hardcoded-system-account`.

**تحديث [2026-09-22] — الدفعة 0 اكتملت بكامل نطاقها الثلاثي:** بالإضافة لـBatch 0-A أعلاه (insurance)، أُغلقت **Batch 0-B/0-B1** (`invitations` — سدّ ثغرة تسجيل ذاتي مجهول عبر `accept_invitation`، commit `dde2a84`) و**Batch 0-C** (`admin` — مفتاح إيقاف طارئ لاستدعاءات AI، commit `319313b`). التفاصيل الكاملة لكل من B/C في قسم `## [2026-09-22]` تحت. الأربعة commits بالترتيب الزمني: `347c337` (migration 048) ← `9ff6572`/`65a4168` (insurance، أعمال سابقة على 0-A) ← `a231c58` (Batch 0-A) ← `319313b` (Batch 0-C)؛ `dde2a84` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا (مُلتزَم يدويًا بواسطة صاحب المشروع).

إغلاق رسمي سابق [2026-09-07]: **إغلاق كامل لمسار `check_feature_access`→`can_access_service`
عبر 8 دومينات [2026-09-07]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل.**

خلفية المسار: قرار تصميم بداية اليوم — استبدال الاعتماد على
`plan.features` (JSONB نص حر بلا schema enforcement) بجدول ربط
many-to-many جديد (`saas_plan_service_access`، migrations 046/047).
Pilot أول على `insurance` وحده (اختبار حي أثبت إصلاح فعلي لعيب تطابق
نصي وهمي في `plan.features`)، ثم توحيد `can_access_service` نفسها على
الجدول الجديد، ثم تحويل الـ7 دومينات الباقيين (`employment`,
`digital_twin`, `arbitration_syndicates`, `realestate`, `manufacturing`,
`logistics`, `invitations`) — كل واحد بجلسة منفصلة وموافقة صريحة، ديف
محصور في سطر واحد استدعاء داخل `_check_saas_limits()` بكل دومين + استيراد،
seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + اختبار E2E حي
فعلي (نجاح 200/201 لتينانت معه صلاحية + رفض 403 لتينانت من غيرها) لكل
دومين، موثَّق بالكامل بالـtraceback والـstatus codes الفعلية.

**قاعدة إلزامية اتفعّلت أثناء المسار:** أي `INSERT` مباشر بـ`id=` صريح
على جدول `SERIAL` لازم يتبعه `setval()` فوري على نفس الجدول — بعد حادثة
تصادم `UniqueViolationError` فعلية سببها seed بدون `setval` (تفصيل في
تقرير الجلسة).

**تحقُّق نهائي (`grep` مباشر):** `check_feature_access` بقت **dead code
فعليًا** — صفر مُستدعٍ لها في كل `app/` (لسه موجودة في تعريفها كما طُلب،
لم تُلمَس). **14 دومين** دلوقتي على `can_access_service`
(الـ8 المذكورين + `zamakana`/`transport`/`tourism_sports`/
`tenders_auctions`/`social`/`service_marketplace` اللي كانوا عليها
أصلًا).

**5 بنود backlog مفتوحة نتيجة هذا المسار (تفاصيل كاملة في §8.5 من
`.claude/reports/remaining-7-domains-can-access-service-migration-session-log.md`):**
1. فرع `PAST_DUE` في `can_access_service` غير قابل للوصول فعليًا (dead code) — يحتاج قرار تصميمي.
2. ✅ **اتحل جزئيًا [تحديث 2026-09-08]** — `tests/test_saas_active_subscription.py` بيفترض سلوك `plan.features` النصي القديم — ضرب `insurance` ثم `realestate`/`invitations`. Seed تينانت 1 لخدمتي `insurance`(101)/`real_estate`(107) اكتمل (نفس نمط تينانت 16) — بوابة `can_access_service` بقت بتعدي للأربعة اختبارات. اختباري `insurance` نجحا بالكامل (`2 passed`). اختباري `realestate` لسه فاشلين، لكن بمشاكل fixture منفصلة تمامًا عن بوابة الـSaaS — راجع البندين الجديدين `realestate-test-fixture-landlord-not-registered-land-owner`/`realestate-ai-agent-exception-silently-swallowed` تحت في جدول الـBacklog، وتفصيل كامل في §2 من هذا الملف (بند التاريخ [2026-09-07]) و`.claude/reports/plan-features-tests-fix-session-log.md`.
3. ✅ **اتحل** — تناقض بورت Redis/Celery في `.env`. الفرضية الأصلية (تناقض `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` عن `REDIS_URL`) كانت غير دقيقة — تحقيق كامل (`.claude/reports/redis-celery-port-mismatch-investigation-session-log.md`) كشف السبب الجذري الحقيقي: `config.py` كان بيحمّل `.env` بمسار نسبي (يعتمد على `cwd`)، وملف `.env` تاني قديم موجود على جذر الريبو (`E:\cc\.env`، بورت 6379، بلا باسورد) كان بيتقرأ بدل النسخة الصحيحة (`eppne-backend/.env`، بورت 6380) لو أي عملية اتشغّلت من جذر الريبو. اكتشاف جانبي: `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` كانوا قيم ميتة بالكامل — صفر سطر كود بيقرأهم (`celery_app.py` بيستخدم `REDIS_URL` حصريًا لكل من الـbroker والـbackend). **الإصلاح المُنفَّذ** (`.claude/reports/redis-celery-env-path-fix-session-log.md`): (1) `config.py` بقى بيحسب مسار `.env` بشكل مطلق (`Path(__file__).resolve()`) بدل الاعتماد على `cwd` — تحقُّق حي أثبت نجاح الاتصال بـRedis من جذر الريبو بعد التعديل. (2) حذف `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` من `eppne-backend/.env` (قيم ميتة مؤكَّدة) — تحقُّق على 3 مستويات (`Settings`، اتصال Redis حي، `celery_app.conf` الفعلي) أثبت عدم كسر أي شيء. Regression: 25 فشل، كلهم pre-existing غير متعلقين (WIP في دومينات أخرى + بند backlog #2 المعروف). **بند مفتوح متبقٍّ (منخفض الأولوية، لم يُنفَّذ عمدًا):** قرار بشأن `E:\cc\.env` (الجذر) — لسه موجود بقيمته القديمة (غير ذي صلة الآن بعد الإصلاح، لكن ممكن يلخبط أي حد يفتحه بالغلط)، وقرار بنيوي أوسع بشأن تفعيل `docker-compose.yml` بالكامل مقابل الحاويات اليدوية الحالية — كلاهما مؤجَّل لجلسة منفصلة.
4. `backlog-affiliate-commission-registration-systemwide-broken` — `_register_affiliate_commission` بتفشل عبر 11 دومين، أولوية عالية.
5. ✅ **اتحل** — `backlog-invitations-create-invitation-broken` (`create_invitation` كانت بترجع 500 دايمًا بسبب `_assign_ai_agent`/`PaginatedResponse`). تفاصيل الحل الكاملة في القسم المخصص تحت.

**تقارير الجلسات الكاملة لهذا المسار (بالترتيب الزمني):**
`.claude/reports/plan-service-mapping-data-audit-session-log.md` →
`.claude/reports/saas-plan-service-access-migration-session-log.md` →
`.claude/reports/saas-plan-service-access-restrict-fix-session-log.md` →
`.claude/reports/insurance-can-access-service-pilot-session-log.md` →
`.claude/reports/can-access-service-unification-review-session-log.md` →
`.claude/reports/can-access-service-unification-session-log.md` →
`.claude/reports/remaining-7-domains-can-access-service-migration-session-log.md`
(§8 فيه الملخص الختامي الشامل الكامل لكل الـ7 دومينات).

**ملاحظة (إغلاق رسمي سابق، محفوظ بالكامل في `📋 الجلسات المُقفلة` تحت):**
`entity-membership-foundation` [2026-08-20] — بناء الأساس العام لنظام
`EntityMembership` (الجلسة 1 من 2، مسار الصلاحيات الجديد)، ✅ مُغلَق
رسميًا. راجع السجل الكامل في قائمة الجلسات المُقفلة، أو
`.claude/reports/entity-membership-foundation-session-log.md`.

---

## 🗂️ جدول الـBacklog النشط

**ملاحظة منهجية:** هذا الجدول أُعيد بناؤه [2026-08-18] من مسح كامل لـ`PROGRESS_LOG_ARCHIVE_2026-08-18.md` (27 بند: 25 مرقّم من قائمة الانتظار الرسمية + بندان بالاسم أُضيفا لاحقًا)، **زائد بندين إضافيين من `sovereign_entities` أُضيفا يدويًا بناءً على توجيه صريح**. **لم يُجرَ تدقيق شامل يضمن أن كل اكتشاف تاريخي في الأرشيف انعكس هنا** — أي بند تاريخي يظهر لاحقًا وغير موجود في هذا الجدول، ارجع للأرشيف كمرجع نهائي وأضِفه هنا وقتها.

| # | العنوان المختصر | الحالة | مرجع |
|---|---|---|---|
| 1 | `user-repository-get-by-id-audit` — 15 موضع `tenant_id` ناقص في `UserRepository.get_by_id` | ✅ **مُغلَق رسميًا [2026-08-19].** `grep` شامل جديد بالكامل من الصفر (بلا اعتماد على القايمة التاريخية كمرجع نهائي) أكَّد: **15 موضعًا فعليًا عبر 13 دومين، بلا زيادة ولا نقصان** عن القايمة القديمة رغم كل الجلسات اللي حصلت من وقتها. الحل: تمرير `tenant_id` المتاح أصلًا في نطاق كل دالة (معامل مباشر أو مُشتق من صف محمَّل) كمعامل ثانٍ، مع تعديل توقيع أي دالة مساعدة خاصة ما كانتش بتقبله. **4 كسور واضحة (500)** أُصلحت (`transport`, `social` [جوّه `begin_nested()`، صفر `try/except` جديد بقرار مستخدم]، `realestate`, `insurance.review_claim`)، **موضع صمت كامل بلا تسجيل** أُصلح (`insurance.disburse_monthly_pensions`)، **9 مواضع صمت مُسجَّل** أُصلحت، **موضع واحد Dead code** تُرك بلا لمس عمدًا (`logistics` — بند Backlog منفصل `logistics-affiliate-commission-dead-code-uses-broken-get-by-id` تحت). **رابط مباشر بـBacklog #10:** بعد الإصلاح، كل الـ10 دومينات المستدعية لـ`_register_affiliate_commission` (9 + `insurance`) وصلت فعليًا لـ`get_by_id` بنجاح، لكن اصطدمت فورًا بطبقة `identity-user-referred-by-field-missing` (تحت) — سلسلة #10 تقدَّمت طبقة كاملة لهذه الـ10، بينما `digital_twin`/`employment` لسه محجوزان عند Backlog #8. **أثر جانبي مُعالَج في نفس الجلسة:** `tests/test_saas_active_subscription.py::test_insurance_review_claim_...` حُدِّث من الاعتماد على `TypeError` (مُصلَح) لطبقة `insurance-review-claim-issuer-entity-id-reviewer-id-conflict` (تحت) الحقيقية. تحقق حي كامل للـ15 موضعًا (tenant صحيح+خاطئ، عزل tenant فعلي) + regression test دائم `tests/test_user_repository_get_by_id_audit.py` (15 passed ×2) + suite كامل بعد الإصلاح (60 passed, 4 xfailed). | `.claude/reports/user-repository-get-by-id-audit-session-log.md` (كامل)؛ خلفية: أرشيف ~3068، `.claude/reports/saas-control-service-fix-session-log.md` §13 |
| 2 | `duplicate-kwarg-audit` — 4+ حالات `multiple values for keyword` | 🔴 مفتوح | أرشيف ~3069 |
| 3 | استكمال Phase 16 الأصلي | 🟡 غير واضح — علاقته بـ`.claude/reports/phase16-session-log.md` (commits `2d4ef59`/`ab73c8c`) غير مؤكَّدة 100% | أرشيف ~3070 |
| 4 | `silent-write-regression` — الآن 3 حالات: `saas.cancel_subscription` (مؤكَّدة DB-level، أعلى أولوية) + حالتان غير مؤكَّدتين DB-level (`saas.process_auto_renewals` فرع except، `saas.can_access_service`) | 🔴🔴 **مفتوح — `cancel_subscription` أولوية قصوى، أعلى من أي بند backlog تاني حاليًا** [تأكيد إضافي 2026-08-24، جلسة `saas-idor-fix`]: **`saas.cancel_subscription` — silent-write مؤكَّد DB-level، معروف من 2026-08-14 ولسه مش متصلح.** الـAPI بيرجع `200 {"status":"CANCELLED"}`، لكن `SELECT` مستقل فوري بيظهر `status=ACTIVE, auto_renew=true` — الكتابة متعملتلهاش `commit()` أبدًا. **السبب:** إصلاح `a9bbae4` (`commit()`-inside-`begin_nested()`) حوّل `repo.update_subscription` لـ`flush()`-only وغطى الـcallers اللي جوه `begin_nested()` بـ`commit()` صريح (`create_subscription`, `pay_invoice`, `process_auto_renewals`)، لكن `cancel_subscription` معندهاش `begin_nested()` من الأساس — فضلت بلا أي `commit()` إطلاقًا. **الأثر: تأثير مالي مباشر ومستمر، مش مجرد "لازم يتصلح يومًا ما"** — أي عميل حقيقي يفتكر إنه ألغى الاشتراك (الـUI بيعرض CANCELLED) ولسه بيتحاسب فعليًا كل شهر (`auto_renew=true` في الـDB). **إعادة تأكيد حية اليوم (مش استنتاج من التوثيق القديم):** مستخدم `USER` throwaway نادى `PUT /saas/subscriptions/51/cancel` → `200 CANCELLED`، `SELECT` مستقل فوري = `ACTIVE`. الحالتان التانيتان (`process_auto_renewals` فرع except، `can_access_service`) لسه غير مؤكَّدتين DB-level، لم يُعاد فحصهما اليوم. **✅ [تصحيح فهرس، 2026-08-25]: الحالة أعلاه (`🔴🔴 مفتوح — cancel_subscription أولوية قصوى`) كانت stale — `cancel_subscription` تحديدًا اتصلح فعليًا من commit `45eb4bf` (`fix(saas): commit() explicit in cancel_subscription (silent-write)`, 2026-08-24 11:32:52، أي بعد التوثيق أعلاه بنفس اليوم) — `await self.db.commit()` صريح بعد `repo.update_subscription()`. مؤكَّد بثلاث طبقات مستقلة: (1) الكوميت نفسه وثّق قبل/بعد حيًا، (2) `tests/test_saas_cancel_subscription_silent_write.py` (regression test مخصَّص، جلسة `AsyncSessionLocal` منفصلة) شُغِّل مستقلًا بتاريخ 2026-08-25 → `2 passed`، (3) تحقق حي إضافي بتاريخ 2026-08-25 (جلسة `rbac-ownership-review`، تحت تعديل RBAC غير متعلق) أكَّد نفس النتيجة (`SELECT` مستقل: `status=CANCELLED` فعليًا بعد استدعاء ناجح). **الحالتان التانيتان (`process_auto_renewals` فرع except، `can_access_service`) لسه بلا تغيير — غير مؤكَّدتين DB-level، غير مُصلَحتين.**

**⚠️ تحديث [2026-08-29، جلسة جرد كودي — توثيق فقط، صفر إصلاح]:** الاتنين اتأكَّدوا كودًا بثقة
عالية (نفس نمط `cancel_subscription` المُصلَح بالحرف — `flush()` بس بلا `commit()`)، لكن بلا تحقق
حي كامل (بيانات throwaway) في هذه الجلسة تحديدًا — أُبقيا "غير مؤكَّدتين DB-level" رسميًا لحد ما
يحصل تحقق حي فعلي:
- **`process_auto_renewals` فرع `except InsufficientBalanceError`** (`saas/service.py:210-218`):
  فرع النجاح (`try`) عنده `await self.db.commit()` صريح (سطر 205)، **لكن فرع `except
  InsufficientBalanceError` (210-218) بينادي `repo.update_subscription(..., status="PAST_DUE",
  grace_period_end_date=...)` بلا أي `commit()` بعده** — نفس البنية بالحرف اللي كانت في
  `cancel_subscription` قبل إصلاحها. `repo.update_subscription()` (`saas/repository.py:216-227`)
  مؤكَّد إنها `flush()` بس. **النتيجة المتوقَّعة:** `results.append({"status": "PAST_DUE"})` بترجع
  للمستدعي رغم إن الكتابة الفعلية (`status`, `grace_period_end_date`) بتضيع صامتة.
- **`can_access_service`** (`saas/service.py:229-251`)، سطر 248: فرع `PAST_DUE` منتهي الصلاحية
  بينادي `repo.update_subscription_status(..., "EXPIRED")` — نفس `flush()`-بس (`repository.py:233-239`
  wrapper حول `update_subscription`). **أخطر من `process_auto_renewals`:** `can_access_service`
  بتتنادى كفحص قراءة بحت من **كل** المستدعين (`check_and_enforce_access`, `check_service_access`,
  وعبر `_check_saas_limits` في تقريبًا كل الـ30 دومين) — ولا واحد فيهم متوقَّع يعمل `commit()`
  بعدها (فحص صلاحية، مش عملية كتابة). يعني الكتابة دي **شبه دايمًا** بتضيع صامتة، مش بس في حالة
  حافة.

راجع `.claude/reports/constructor-mismatch-backlog-inventory-4-13-session.md` للتفصيل الكامل. التفاصيل: `.claude/reports/saas-cancel-subscription-silent-write-fix-session-log.md`؛ `.claude/reports/rbac-ownership-review-session-log.md` §4.1.** | أرشيف ~3071؛ `.claude/reports/simpletenant-fix-session-log.md` (تأكيد 2026-08-14)؛ `.claude/reports/saas-idor-fix-session-log.md` §4 (تأكيد 2026-08-24) |
| 5 | `sovereign_entities` — قرار منتجي معلَّق (4 endpoints) | 🔴 مفتوح — تطوّر لاحقًا لاكتشاف أخطر (راجع بند `sovereign_entities-auth` تحت) | أرشيف ~3072 |
| 6 | `commerce.visa_webhook` مراجعة أمنية | ✅ **مُغلَق [2026-08-25]** (تصحيح فهرسي — كان هذا السطر لسه يقول "لم يبدأ" رغم أن الإصلاح حصل فعليًا في commit `b55b57c` بنفس اليوم: إزالة الاعتماد على هيدر `X-Tenant-ID` غير الموثوق، اشتقاق `tenant_id` من الطلب نفسه، وتقييد الـendpoint بـ`get_current_superuser` كحارس مؤقت لحد ما يوجد تكامل Visa حقيقي بتوقيع HMAC) | أرشيف ~3073؛ commit `b55b57c` |
| 7 | `redis-client-wrapper-missing-methods` (`hincrbyfloat`, `pubsub`, `lpush`, `ltrim`, `hgetall`, `setnx`) | ✅ **مُغلَق رسميًا [2026-08-19].** الحل: إضافة الست methods على `RedisClientWrapper` (`app/core/redis_client.py`) — إضافة صرفة، صفر لمس لأي ملف مستدعٍ. الخمسة الأولى (`hincrbyfloat, hgetall, lpush, ltrim, setnx`) بنفس نمط `async def ... client = await self.get_client() ...` الموحَّد لباقي الـwrapper؛ `setnx` أُضيفت رغم عدم ذكرها في تعليمات هذه الجلسة تحديدًا لأنها موثَّقة أصلًا كجزء من بند #7 نفسه منذ إنشائه (تصحيح صريح من المستخدم على تعليمات الجلسة، بموافقته). `pubsub()` **أول method متزامنة في الكلاس** (بلا `async`/`await`)، بقرار معماري مبني على دليلين حيّين مستقلين (`communications/router.py:48`، endpoint حي `/communications/ws`، و`event_bus.py:44`) بيستدعوها بلا `await` — تقرأ `self._client` مباشرة، تعتمد على أن `main.py:79` بينادي `initialize()` في الـ`lifespan` قبل أي طلب. **تصحيح/توسيع جوهري على الوصف الأصلي للأثر:** التأكيد السابق [2026-08-18] وصف الأثر كـ"يُسقط `execute_agent_action`" فقط — **التشخيص هنا كشف نطاقًا أوسع فعليًا**: `CostTracker.record_usage()` تُستدعى من `AIEngine.generate()` بلا أي `try/except`، ومؤكَّد بالقراءة المباشرة إن `app/main.py:356` (`POST /api/ai/chat`) — endpoint عام مستقل تمامًا عن `ai_agents` — كان متأثرًا بنفس `AttributeError` بالضبط، يعني الباج كان يُسقط **أي استدعاء AI ناجح عبر المنصة بالكامل**، مش مسار وكلاء فقط. **تحقق حي كامل مزدوج:** (أ) الست methods منفردة، كل واحدة بأداة تحقق مستقلة (HGET/LRANGE/GET/subscriber منفصل، مش بس صفر استثناء) — راجع regression test تحت؛ (ب) **`execute_agent_action` + `ai_engine.generate()` (مسار `main.py:356`) بلا أي `monkeypatch` إطلاقًا** (عكس التحقق السابق في جلسة #16 اللي اضطر يتجاوز هذا الباج بالتحديد) — اكتشاف مُيسِّر: `AIEngine._call_model()` أصلًا محاكاة داخلية جاهزة (الكود الفعلي لاتصال الشبكة معلَّق في الكود، سطر 290-298)، فصفر اعتماد على شبكة/API حقيقي. النتيجة: `AITaskLog.task_type` رجعت `ARABIC_CHAT` (مش `ERROR`)، `AgentApprovalQueue` اتسجَّلت فعليًا لأول مرة — تنظيف كامل + SELECT/`redis-cli` مستقل أثبتا صفر أثر متبقٍ. **اكتشاف جانبي وُثِّق منفصلًا (صفر لمس):** `agritech-redis-calls-missing-await-orphaned-coroutines` (تحت) — باج مختلف جذريًا (نداءات على عميل خام بلا `await`، مش method مفقودة). regression test دائم: `tests/test_redis_client_wrapper_missing_methods.py` (6 اختبارات، 6 passed × تشغيلتين). | `.claude/reports/redis-client-wrapper-missing-methods-session-log.md` (كامل)، خلفية: أرشيف ~3074، `.claude/reports/ai-agents-execute-action-fix-session-log.md` §10 |
| 8 | `user-repository-get-user-audit` (method غير موجودة) | ✅ **مُغلَق رسميًا [2026-08-19].** `grep` شامل جديد بالكامل عن `\.get_user\(` (بلا اعتماد على القايمة التاريخية "6 مواضع" كمرجع نهائي) كشف **5 مواضع فعليًا، 8 نقاط استدعاء حية + موضعان Dead code مؤكَّدان**. `employment/service.py:87` (`_get_user`): 3 نقاط — `_register_affiliate_commission:100` (صامت)، `_calculate_ai_match_score:132` (صامت، **ميزة AI matching كانت معطَّلة 100%**)، و**نقطة خارجية جديدة غير موثَّقة تاريخيًا** `app/tasks/employment.py:308` (`pay_payroll_task` — **كانت تفشل دفع الرواتب فعليًا، يُعاد المحاولة 3 مرات ثم يستسلم نهائيًا**). `digital_twin/service.py:53` (`_get_user`): 2 نقطة — `_register_affiliate_commission:71` (صامت)، و**نقطة أخطر غير موثَّقة تاريخيًا** `interact_with_twin:180` عبر `_get_user_email` (**كسر واضح 500 داخل `begin_nested()` بلا أي `try/except`**، نفس نمط `social:678` من #1). الحل لهذين الموضعين: نفس منهجية #1 بالحرف (تعديل توقيع كل helper ليقبل `tenant_id`، صفر `try/except` جديد). `communications/service.py:29` (`_get_user_tenant`): 3 نقاط (`send_notification:63`, `send_mail:144/145`) — **استثناء معماري**: الغرض من الدالة هو اكتشاف `tenant_id` نفسه، فلا يوجد `tenant_id` متاح في أي نقطة استدعاء أصلًا (الحل المعتاد لا ينطبق). الحل المعتمَد (قرار مستخدم صريح): **method جديدة على `UserRepository`**، `get_tenant_id_by_user_id(user_id) -> Optional[int]` — تبحث بـ`user_id` وحده عبر كل الـtenants وترجع `tenant_id` فقط (لا كائن `User` كامل، قرار **least-privilege**). `communications/service.py:36` و`health/service.py:54` (كلاهما `_get_user_email`): **Dead code مؤكَّد، بلا لمس عمدًا** (صفر مستدعٍ حي في المشروع كله، نفس فئة `logistics-affiliate-commission-dead-code-uses-broken-get-by-id`). **رابط مباشر بـBacklog #10:** أثناء التحقق الحي، `_register_affiliate_commission` في `employment`/`digital_twin` وصلت بنجاح لـ`get_by_id` واصطدمت فورًا بنفس طبقة `identity-user-referred-by-field-missing` — **كل الـ12 دومينًا في سلسلة affiliate/#10 بقوا الآن محجوزين عند نفس الحاجز الوحيد المتبقي**. تحقق حي كامل (12 اختبار throwaway، `db.rollback()`) + regression test دائم `tests/test_user_repository_get_user_audit.py` (11 passed ×2) + suite كامل (71 passed, 4 xfailed، صفر أثر جانبي). | `.claude/reports/user-repository-get-user-audit-session-log.md` (كامل)؛ خلفية: أرشيف ~3075، `.claude/reports/audit-log-fix-session-log.md` §10 (`communications-service-get-user-missing-method`) |
| 9 | `saas-control-service-missing-methods` (`get_active_subscription`) | ✅ **مُغلَق رسميًا [2026-08-18].** الحل: `SaaSRepository.get_any_active_subscription`/`SaaSControlService.get_active_subscription` (اشتراك واحد شامل لكل tenant) + تصحيح `subscription.features`→`subscription.plan.features` (list membership) عبر 8 دومينات + فحص دفاعي `belt-and-suspenders` على `subscription.plan`. **تحقق حي كامل** لـ`rent_unit`/`subscribe` (SELECT مستقل). `buy_fractional_ownership`/`review_claim` محجوبتان ببجات مسبقة (#16, #1 — مش `tx_hash` كما كان متوقَّعًا)، تراجع نظيف مؤكَّد. | `.claude/reports/saas-control-service-fix-session-log.md`، خلفية: `.claude/reports/saas-control-service-missing-methods-session-log.md`، `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` |
| 10 | `affiliate-service-missing-methods` | 🟡 **مُغلَق جزئيًا [2026-08-19] — المرحلة 2.** تشخيص كامل (`grep` شامل) صحّح الوصف الأصلي: **12 دومين، 36 موضع استدعاء فعلي** (مش 8 كما كان مفترضًا) لميثودين مفقودتين فعليًا على `AffiliateService`: `register_commission` (كل الـ12) و`get_user_by_code` (`digital_twin` فقط). **اكتشاف حرج غيَّر التصميم بالكامل:** جدول `Commission` الموجود (`affiliate_commissions`) مصمَّم حصريًا لعمولات مرتبطة بـOrder تجاري (`order_id`/`order_item_id`/`product_id` FK **NOT NULL**) — الـ12 موضع كلها أحداث بلا Order، فـ`register_commission` استحال تُبنى كنداء مباشر لـ`repo.create_commission`. **الحل المعتمَد (قرار مستخدم صريح):** جدول منفصل تمامًا `affiliate_action_commissions`/موديل `ActionCommission` (migration `028`)، بدل توسيع الجدول التجاري بأعمدة nullable. `register_commission` تستدعي `get_or_create_profile(affiliate_id)` داخليًا لحل التباس نطاق `users.id`/`affiliate_profiles.id` (كل الـ12 موضع بيمرروا `affiliate_id=user.referred_by`، وهي قيمة `users.id` فعليًا). إصلاح ضروري ملازم واحد: `digital_twin/service.py:82` (`referrer.id`→`referrer.user_id`، نفس فئة باج خلط النطاق). **تحقق حي كامل + regression دائم:** `tests/test_affiliate_service_missing_methods.py` (6 passed ×2، بيانات throwaway + SELECT مستقل، بما فيها حالة حافة "نفس affiliate_id عبر جلستين DB منفصلتين" تثبت `get_or_create_profile` idempotent حقيقيًا). **⚠️ لماذا "جزئيًا" وليس "رسميًا":** `register_commission`/`get_user_by_code` أنفسهم يعملون بشكل صحيح ومعزول، **لكن الـwrapper الفعلي (`_register_affiliate_commission`) في الـ12 دومين لسه معطَّل عمليًا** — كان بيفشل صامتًا **قبل** ما يوصل حتى لـ`register_commission`، بسبب ثلاث طبقات فشل سابقة **خارج نطاق هذه الجلسة بقرار مستخدم صريح**: (أ) بند #1 (`user-repository-get-by-id-audit`، 10 من الـ12 موضع)، (ب) بند #8 (`user-repository-get-user-audit`، دومينان)، (ج) **اكتشاف جديد وقتها**: `User.referred_by` (`identity/models.py`) **غير موجود إطلاقًا** كحقل على موديل `User` — أي وصول له `AttributeError` حتى بعد حل #1/#8 (راجع بند Backlog الجديد `identity-user-referred-by-field-missing` تحت). **⚠️ تحديث [2026-08-19، جلسة `user-repository-get-by-id-audit`]:** بند #1 **اتقفل رسميًا**. تحقق حي مباشر بعد الإصلاح أكَّد: كل الـ10 دومينات المرتبطة بـ#1 (كل الـ12 ماعدا `digital_twin`/`employment`) بتوصل الآن فعليًا لـ`get_by_id` وتجيب المستخدم الصحيح بنجاح تام — **الطبقة (أ) اختفت فعليًا**، والطبقة (ج) `identity-user-referred-by-field-missing` بقت **الحاجب الوحيد المؤكَّد حيًا** لهذه الـ10 (`digital_twin`/`employment` لسه عند الطبقة (ب)/#8). **الفقدان الصامت الفعلي للعمولات في الإنتاج لسه قائم اليوم** — بس بطبقة واحدة أوضح دلوقتي، مش تلاتة. اكتشاف جانبي إضافي وُثِّق كبند Backlog منفصل: `affiliate-action-commissions-not-integrated-with-balance` (تحت). **⚠️ تحديث [2026-08-19، جلسة `user-repository-get-user-audit`]:** بند #8 **اتقفل رسميًا** كمان. تحقق حي مباشر أكَّد: `digital_twin`/`employment` (الطبقة (ب) الأخيرة) بيوصلوا الآن فعليًا لـ`get_by_id` بنجاح تام واصطدموا فورًا بنفس طبقة `identity-user-referred-by-field-missing`. **بهذا، كل الـ12 دومينًا بلا استثناء بقوا محجوزين عند نفس الحاجز الوحيد المتبقي — `User.referred_by`** — هي الخطوة الوحيدة الباقية لإغلاق #10 نهائيًا بالكامل. | `.claude/reports/affiliate-service-missing-methods-session-log.md` (كامل)، `.claude/reports/user-repository-get-by-id-audit-session-log.md` §13 (تأكيد ما بعد #1)، `.claude/reports/user-repository-get-user-audit-session-log.md` §8 (تأكيد ما بعد #8)؛ خلفية: أرشيف ~3077، `.claude/reports/audit-log-fix-session-log.md` §10 |
| — | **`identity-user-referred-by-field-missing`** [2026-08-19] — اكتُشف أثناء تشخيص Backlog #10 (`affiliate-service-missing-methods-session-log.md` قسم 5.3): كل الـ12 دومين المستدعية لـ`AffiliateService.register_commission` بتحدد "هل المستخدم مُحال؟" بفحص `user.referred_by` — لكن **هذا الحقل غير موجود إطلاقًا** كعمود/`relationship`/`property` على موديل `User` (`app/domains/identity/models.py`، قراءة كاملة للكلاس، `grep` شامل لـ`referred_by\s*=\s*Column` عبر المشروع كله: صفر نتيجة). أقرب مفهوم موجود فعليًا هو `ReferralTree` (مرتبط بنطاق `entity_type`/`entity_id` لكل إحالة، مُستخدَم فقط داخل `AffiliateService.track_referral`/`distribute_commissions`) — **لا نقطة استدعاء واحدة من الـ12 دومين تستخدمه**. **الأثر:** أي وصول فعلي لسطر `if user and user.referred_by:` في أي من الـ12 دومين يرمي `AttributeError` فورًا (مبتلَع بنفس `except Exception` الصامت). **قرار نطاق صريح من المستخدم:** هذا "نظام إحالة عام" يستاهل جلسة تصميم منفصلة (هل نضيف عمود `referred_by` على `User`؟ نعتمد `ReferralTree` بنطاق `GLOBAL` بدل عمود مسطَّح؟ قرار منتجي، مش تقني بحت) — **صفر لمس في جلسة #10**. **⚠️ تأكيد حي [2026-08-19، جلسة `user-repository-get-by-id-audit`]:** بعد إغلاق Backlog #1، هذا البند **بقى الحاجب المباشر المؤكَّد حيًا** (مش نظري) لـ10 من الـ12 دومين — `AttributeError` ظهرت فعليًا في السجلات أثناء التحقق الحي (`_register_affiliate_commission` × 9 دومينات + `insurance`)، صفر `TypeError` بعد كده. **⚠️ تأكيد حي إضافي [2026-08-19، جلسة `user-repository-get-user-audit`]:** بعد إغلاق Backlog #8، `digital_twin`/`employment` (الطبقة الأخيرة المتبقية) وصلا الآن بنجاح لـ`get_by_id` وارتطما فورًا بنفس البند — نفس `AttributeError` ظهرت حيًا في السجلات لكليهما. **بهذا، هذا البند بقى الحاجب الوحيد المؤكَّد حيًا لكل الـ12 دومينًا بلا استثناء — الخطوة الوحيدة الباقية لإغلاق Backlog #10 نهائيًا بالكامل.** | 🔴 **مفتوح، أولوية عالية جدًا** — يمنع أي عمولة إحالة عابرة للدومينات من الوصول حتى لمرحلة التسجيل؛ **مؤكَّد حيًا كالحاجب الوحيد الفعلي لكل الـ12 دومينًا** (بعد إغلاق #1 و#8) | `.claude/reports/affiliate-service-missing-methods-session-log.md` قسم 5.3، 5.4؛ `.claude/reports/user-repository-get-by-id-audit-session-log.md` §13؛ `.claude/reports/user-repository-get-user-audit-session-log.md` §8 |
| — | **`logistics-affiliate-commission-dead-code-uses-broken-get-by-id`** [2026-08-19] — اكتُشف أثناء جلسة `user-repository-get-by-id-audit` (Backlog #1): `logistics/service.py:59-66` (`_get_user`/`_get_user_email`) بتنادي `UserRepository.get_by_id(user_id)` بمعامل واحد بس — نفس بج #1 بالضبط — **لكن بلا أي مستدعٍ حي في المشروع كله** (لا يوجد `_register_affiliate_commission` في هذا الملف أصلًا، بعكس باقي الـ12 دومين المتأثرة). **قرار نطاق صريح:** تُرك بلا لمس عمدًا في جلسة #1 (كل الـ14 موضع الحي الباقي اتصلح، ده الوحيد المتروك) — اختبار `regression` مخصَّص (`tests/test_user_repository_get_by_id_audit.py::test_logistics_get_user_left_untouched_as_documented_dead_code`) بيوثِّق ويقفل الحالة الحالية عمدًا (بيفشل تحذيريًا لو حد أضاف مستدعٍ حي مستقبلًا بلا مراجعة هذا البند). | 🟡 **مفتوح، أولوية منخفضة (كود ميت، صفر أثر إنتاجي حاليًا)** — يستاهل نفس إصلاح باقي الـ14 موضع (`tenant_id` كمعامل ثانٍ) **فقط لو/لما** يُضاف `_register_affiliate_commission` لـ`logistics` مستقبلًا | `.claude/reports/user-repository-get-by-id-audit-session-log.md` §9.5، `tests/test_user_repository_get_by_id_audit.py` |
| — | **`affiliate-action-commissions-not-integrated-with-balance`** [2026-08-19] — اكتُشف أثناء تصميم حل Backlog #10: العمولات المُسجَّلة عبر `AffiliateService.register_commission()` الجديدة تُخزَّن فعليًا في جدول منفصل (`affiliate_action_commissions`)، لكن **غير مدموجة** في أي من دوال الرصيد/السحب/الإحصائيات الحالية — `get_affiliate_stats` (`total_pending`)، `withdraw_commissions` (`get_pending_commissions`)، `release_commissions`، `get_commissions_by_user` — كلها بتقرأ **فقط** من جدول `affiliate_commissions` التجاري القديم. **الأثر العملي:** العمولة بقت تُسجَّل فعليًا (اختفت مشكلة الفقدان الصامت **في الكود**)، لكنها **غير مرئية تمامًا لصاحبها** — مش هتظهر في رصيده المعلَّق، ومش هيقدر يسحبها. **قرار نطاق صريح من المستخدم (خيار "ج" — حل وسط):** أعمدة `paid_at`/`paid_tx_hash`/`status` أُبقيت في الجدول الجديد استعدادًا لتكامل لاحق، لكن **صفر لمس** على دوال الرصيد/السحب الآن — السبب: تعديل `withdraw_commissions`/`release_commissions` يلمس منطق سحب فلوس حقيقي، يستاهل جلسة مخصَّصة بتصميم واختبار مستقل. | 🔴 **مفتوح، أولوية عالية** — فجوة تجربة مستخدم حقيقية (عمولة مسجَّلة لكن غير قابلة للوصول/السحب) حتى لو الفقدان الصامت في الكود اتحل | `.claude/reports/affiliate-service-missing-methods-session-log.md` قسم 10، 11 |
| 11a | `invitations-user-registration-savepoint-leak` (امتداد #11، فرع `invitations`) | ✅ **مُغلَق رسميًا [2026-08-18]** | `.claude/reports/invitations-savepoint-leak-session-log.md` |
| 11b | `invoicing-savepoint-conflict` (**نطاق نهائي:** `tourism_sports` [3 دوال] + `realestate` [2] + `insurance` [2] + `zamakana` [1] = **8 دوال**/4 دومينات) | ✅ **مُغلَق رسميًا [2026-08-18].** الحل: نقل `invoicing.create_invoice()` من جوه `begin_nested()` لبعد `commit()` الخارجي، ملفوف بـ`try/except`. **تحقق حي كامل بـSELECT/Redis مستقل** لـ4 دوال (`purchase_event_ticket`, `rent_unit`, `zamakana.pledge_time`، وجزء `insurance.subscribe`) — صفر باج جديد فيهم. **مراجعة ديف/كود فقط** للأربعة الباقية (`book_program`, `place_transfer_bid`, `buy_fractional_ownership`, `review_claim`) — محجوبين ببجات مسبقة منفصلة تمامًا (بنود #12-#14 تحت). `arbitration_syndicates`/`service_marketplace` مؤكَّدين مسبقًا **خارج** النطاق (خارج `begin_nested()` / بج مختلف #12). | `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` (كامل)؛ خلفية: `.claude/reports/saas-control-service-missing-methods-session-log.md` قسم 4 |
| 12 | `saas-control-service-wrong-arity-call` | 🔴 مفتوح | أرشيف ~3111 |
| 13 | `invoicing-create-invoice-wrong-kwarg` | 🟡 **جرد مكتمل [2026-08-29]، صفر إصلاح** — `grep` شامل حقيقي على كل الـ21 موضع `create_invoice(` عبر كل الدومينات (`ai_agents`, `arbitration_syndicates`×3, `insurance`×2, `invitations`, `manufacturing`×2, `realestate`×2, `service_marketplace`, `tenders_auctions`, `tourism_sports`×3, `transport`×2, `zamakana`×2) — **`service_marketplace/service.py:203` (`tenant_id=buyer_tenant_id`) هو الموضع الوحيد المؤكَّد، صفر انتشار إضافي.** باقي الـ20 موضع كلهم بيستخدموا `entity_id=` صح. | أرشيف ~3114؛ `.claude/reports/constructor-mismatch-backlog-inventory-4-13-session.md` |
| 14 | `audit-log-wrong-kwargs` | ✅ **مُغلَق رسميًا [2026-08-18].** الحل: توسيع توقيع `audit_log()` (`app/core/audit.py`) ليقبل `tenant_id: Optional[int] = None`/`resource_id: Optional[int] = None` فعليًا (يُسجَّلان في الـJSON log entry — صفر migration لأن الدالة أصلًا logger فقط، لا تكتب أي جدول DB). **الرقم المصحَّح بجرد كامل (كل موضع اتقرا لوحده، مش عيّنة):** **95 موضع مكسور فعليًا عبر 18 ملف** (مش ~112 عبر 22 كما كان موثَّقًا) — `agritech` (11) و`ai_agents` (4) آمنان أصلًا (يحملان `tenant_id` جوّه `details` مسبقًا، صفر kwargs top-level زيادة)، `commerce` (1) آمن أصلًا (مؤكَّد سابقًا)، و`communications/router.py` فيه 7 مكسورة من 8 (`DEVICE_REGISTER` آمن أصلًا). صفر نمط استدعاء خامس/سادس جديد — كله يتبع نفس الحقول الخمسة (`user_id, tenant_id, action, resource_id, details`) بشكلين سلوكيًا متطابقين (kwargs مباشرة أو `**{dict}`). **اكتشاف حرج جانبي غيّر تأطير الخطورة بالكامل:** الباج مش "audit trail بيفشل بصمت" — صفر `try/except` يغلّف الاستدعاءات المكسورة، وصفر exception handler عام في `main.py` (بس 3 مخصَّصة)، و`get_db()` بلا commit تلقائي — يعني قبل الإصلاح، أي endpoint حي بيستدعي هذه الدوال كان بيرجع **500 حقيقي وبيتراجع (rollback) بالكامل**، مش مجرد فقدان سجل تدقيق. **تحقق حي كامل** (SELECT مستقل من جلسة DB منفصلة يثبت اختفاء الـ500/rollback فعليًا) عبر 4 عيّنات: `insurance.create_policy` (kwargs مباشرة)، `zamakana` (نفس النمط، عبر repo مباشرة تفاديًا لبج #12 غير مرتبط)، `communications/router.py` (`MAIL_MOVE_TO_TRASH`، النمط الناقص بلا `tenant_id`)، `realestate.rent_unit` (نمط `**{...}` unpacking). كشف اكتشافين جانبيين غير مرتبطين وُثِّقا منفصلين (`communications-service-get-user-missing-method` تحت، وتحديث على #10). | أرشيف ~3137، 3407، `.claude/reports/saas-control-service-fix-session-log.md` §13، `.claude/reports/audit-log-fix-session-log.md` (كامل) |
| 15 | `ai-governance-check-and-consume-wrong-kwarg` | ✅ **مُغلَق رسميًا [2026-08-18].** الحل: إزالة `tenant_id=` الزائدة من كل الـ13 موضع (التوقيع الحقيقي لا يقبلها؛ الـmethod تستخدم `self.tenant_id` من الـconstructor). **7 من 13 موضع كان عندهم `action_type` الإجباري مفقود كمان** — أُضيف بقيم معبِّرة عن السياق الفعلي (`SCENARIO_ANALYSIS`/`PLAYER_TRANSFER_ANALYSIS`/`BID_EVALUATION`/`MATCH_SUGGESTIONS`/`AI_JUDGE_ANALYSIS`)، واتنين (`transport`, `realestate`) استخدموا `action_type=action` (تمرير معامل helper موجود أصلًا بدل نص ثابت). **تحقق حي كامل** (docker `eppne_db`، throwaway + SELECT مستقل) أثبت الاستهلاك الصحيح، تسجيل `action_type` بدقة، **والرفض الفعلي الحقيقي عند تجاوز الحصة**. 4 من الـ13 ملف (`service_marketplace`, `social`, `tenders_auctions`, `transport`) فيهم ضوضاء ديف موروثة من جلسة سابقة غير محفوظة (بموافقة صريحة: تُركت بلا لمس، موثَّقة في رسالة الـcommit). اكتشافان جانبيان حرجان وُثِّقا منفصلين تحت (`ai-governance-quota-result-ignored`, `ai-governance-create-or-update-quota-multiple-results`). **#16 (`execute_agent_action`) لا يزال مفتوحًا — جلسة منفصلة تالية.** | أرشيف ~3138، `.claude/reports/ai-governance-agents-fix-session-log.md` (كامل) |
| 16 | `ai-agents-execute-agent-action-wrong-kwarg` | 🟡 **مُغلَق جزئيًا [2026-08-18] — 17 من 19 موضع.** الحل: إزالة `tenant_id=` الزائدة (كل الـ19) + إضافة `idempotency_key=` الناقصة (11 من 19، بنمط `PREFIX-T{tenant_id}-{unique_id}`، 7 منهم بإعادة استخدام معامل خارجي موجود). **2 موضع مُستثنيان عمدًا** (`realestate/service.py:232`, `invitations/service.py:415`) لاكتشاف حرج: `commit()` داخل `execute_agent_action` سيتعارض مع `begin_nested()` المحيط بهما — راجع بند `ai-agents-execute-action-commit-inside-begin-nested` تحت. **تحقق حي كامل** (docker `eppne_db`، تينانتين حقيقيين 1/15) أثبت نجاح الاستدعاءات، صحة التسجيل، كاش idempotency فعّال، ونمط `T{tenant_id}` يمنع تصادم عبر تينانتين (بينما مفتاح خام بلاه يسبب `IntegrityError` حقيقي مؤكَّد حيًا). اكتشاف حي جانبي أكّد أن #7 يُسقِط الدالة بالكامل عمليًا. | أرشيف ~3158، `.claude/reports/saas-control-service-fix-session-log.md` §13، `.claude/reports/ai-agents-execute-action-fix-session-log.md` (كامل) |
| 17 | `arbitration-case-model-idempotency-key-mismatch` | 🔴 مفتوح — عائق بنيوي | أرشيف ~3159 |
| 18 | `finance-service-create-invoice-does-not-exist` (`transport`) | 🔴 مفتوح | أرشيف ~3160 |
| 19 | `cross-tenant-scheduled-task-vs-constructor-mismatch` (8+1 مواضع) | 🔴 مفتوح، توثيق فقط بقرار صريح | أرشيف ~3161-3162 |
| 20 | `missing-tenant-id-in-background-task-signature` | 🔴 مفتوح | أرشيف ~3163 |
| 21 | `billing-tasks-saas-subscription-import-error` (حاجب موديول) | 🔴 مفتوح — يحجب كل tasks الملف | أرشيف ~3164 |
| 22 | `finance-transfer-tx-hash-type-mismatch` (نمط في 8 ملفات، 2 مؤكَّدة) | 🔴 مفتوح، 6 ملفات غير مؤكَّدة بعد | أرشيف ~3165 |
| 23 | `invoicing-list-invoices-wrong-kwarg` | 🔴 مفتوح | أرشيف ~3168 |
| 24 | `invoicing-get-invoice-stats-wrong-arity` | 🔴 مفتوح | أرشيف ~3169 |
| 25 | `invoicing-get-invoice-null-tenant-admin-bypass-broken` | 🔴 مفتوح | أرشيف ~3171 |
| — | `tourism-place-transfer-bid-player-id-user-id-conflict` [2026-08-18] — `tourism_sports.place_transfer_bid` بتستخدم نفس القيمة (`data["player_id"]`) بمعنيين متضاربين: `user_id` عند `repo.get_player_profile(data["player_id"])` (الدالة بتفلتر بـ`PlayerProfile.user_id`)، ثم `PlayerProfile.id` عند تمريرها مباشرة جوه `**data` لـ`repo.create_transfer(...)` (`player_transfers.player_id` FK بيشاور فعليًا على `player_profiles.id`) — `IntegrityError: ForeignKeyViolationError` مؤكَّد حيًا. **مؤكَّد صراحة إنه باج مسبق بالكامل، غير متأثر بديف #11b** (السطر المسبِّب للكراش — `repo.create_transfer(**data)` — غير ملموس إطلاقًا في ديف #11b، اللي اقتصر على نقل `create_invoice()` بس). | 🔴 مفتوح، أولوية عادية-مرتفعة، برّه نطاق #11b تمامًا | `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` قسم 12.4 |
| — | `finance-transfer-returns-transaction-object-not-tx-hash-string` [2026-08-18] — `FinanceService.transfer()` (`finance/service.py`) بترجع كائن `Transaction` ORM كامل (`return tx`)، مش نص `tx_hash`. `tourism_sports.book_program` بتمرر الناتج مباشرة كـ`payment_tx_hash=tx_hash` لعمود `String(100)` (`ProgramParticipant.payment_tx_hash`) → `DataError: invalid input... expected str, got Transaction` مؤكَّد حيًا. **مؤكَّد إنه مسبق بالكامل، غير متأثر بديف #11b** (السطر جوه `begin_nested()`، غير ملموس). **✅ مؤكَّد حيًا بالقراءة [2026-08-18]:** نفس النمط بالحرف موجود ومتأثر فعليًا في `realestate.buy_fractional_ownership` (`purchase_tx_hash=tx_hash` → عمود `PropertyOwnership.purchase_tx_hash String(100)`, `models.py:160`) و`insurance.review_claim` (`payout_tx_hash=payout_tx` → عمود `InsuranceClaim.payout_tx_hash String(100)`, `models.py:144`) — **الاتنان هيكراشوا بنفس `DataError` عند الوصول لـ`repo.create_ownership`/`repo.update_claim`.** **غير متأثرين:** `realestate.rent_unit` (`contract_tx_hash` نص مولَّد يدويًا، صفر `finance.transfer` في الدالة أصلًا) و`insurance.subscribe` (`subscription_tx_hash` نص مولَّد يدويًا، مش من `finance.transfer`) و`purchase_event_ticket` (`NFTTicket` مالهاش عمود `payment_tx_hash` أصلاً). | 🔴 مفتوح، أولوية عادية-مرتفعة، برّه نطاق #11b تمامًا | `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` قسم 12.6 |
| — | `invoicing-missing-rollback-on-exception-11b` [2026-08-18] — اكتُشف أثناء كتابة regression test لـ#11b (`tests/test_realestate_insurance_savepoint.py`): الـ`try/except Exception` المضاف حوالين `create_invoice()` في كل الثمانية دوال المُصلَحة (#11b) بيمسك الاستثناء ويسجّل اللوج، **لكن من غير `await self.db.rollback()`**. لو `create_invoice()` فشلت بخطأ DB حقيقي (مش استثناء مُفتعَل بره الـDB زي `RuntimeError` مباشر) — `IntegrityError`/`UniqueViolationError` مثلًا — الـSession بتفضل في حالة `PendingRollbackError` (SQLAlchemy بتـexpire كل الكائنات في identity map تلقائيًا بعد فشل flush، بغض النظر عن `expire_on_commit=False`). **أي كود DB بعد الـtry/except في نفس الدالة (تحديدًا الوصول لأي attribute على الكائن اللي اتعمل قبل الـcommit، زي `contract.id`/`ticket.id` جوه `_store_idempotency`) بيكراش بنفس الخطأ فورًا.** **المورد الأساسي غير متأثر** — `await self.db.commit()` بيحصل *قبل* الـtry/except، فالبيانات الحرجة (العقد/التذكرة/الاشتراك... إلخ) بتكون اتحفظت فعليًا على القرص بنجاح، مؤكَّد بـSELECT مستقل. **الخطر محصور في:** فشل صامت لـ`_store_idempotency()`/أي كود لاحق في نفس الطلب لو `create_invoice()` فشلت بخطأ DB حقيقي (مش سيناريو نظري — دومين مالي، ممكن يحصل فعليًا بسبب أي تعارض DB مؤقت). **اكتشاف إضافي أثناء كتابة تنظيف الاختبار نفسه [2026-08-18]:** `await self.db.rollback()` **لوحدها مش كافية للتعافي الكامل** بعد فشل flush حقيقي جوه async session — تجربة مباشرة أثبتت إن أي استدعاء ORM لاحق على نفس الـsession (حتى بعد `rollback()` ناجح) بيكراش بخطأ مختلف تمامًا وأعمق: `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`. يعني الحل المطلوب (`db.rollback()` جوه الـ`except`) هيمنع `PendingRollbackError` نفسها، لكن **لازم يتأكد إضافيًا إن الـsession فعلًا رجعت صالحة للاستخدام الكامل بعد كده** — مش بس إن `rollback()` نفسها ما رمتش استثناء. **الحل المطلوب (لم يُنفَّذ، مقصود):** إضافة `await self.db.rollback()` جوه كل `except Exception` المحيط بـ`create_invoice()` عبر الثمانية دوال، قبل `logger.error(...)` — **مع تحقق حي إضافي بعد الإصلاح إن استدعاء ORM لاحق (زي `_store_idempotency()`) فعلًا بيشتغل، مش بس إن `rollback()` نجحت**. | 🔴 **مفتوح، أولوية عالية جدًا** — دومين مالي، وبيكسر الـsession بالكامل لأي كود بعده | `tests/test_realestate_insurance_savepoint.py` (اختبار `xfail` موثَّق يثبت السلوك الحالي) |
| — | `invoicing-generate-invoice-number-count-based-collision` [2026-08-18] — اكتُشف أثناء نفس جلسة regression tests: `InvoicingService._generate_invoice_number()` (`invoicing/service.py:115-119`) بتحسب الرقم التالي بـ`count(invoices for tenant) + 1`. لو أي فاتورة سابقة للـtenant اتحذفت (مثلًا تنظيف throwaway data من جلسة تحقق سابقة) بينما فواتير تانية بأرقام أعلى فضلت موجودة، الـ`count()` بيرجع رقم أقل من أعلى رقم مُستخدَم فعليًا فعلًا في الجدول → **تصادم `UniqueViolationError` على `invoices_invoice_number_key` مؤكَّد حيًا** (`tenant_id=1`: `count()=14` لكن `INV-1-000015` موجودة بالفعل، فجوة عند `INV-1-000010` المفقودة). **مؤكَّد أنه مسبق تمامًا وغير متأثر بديف #11b** (منطق الترقيم نفسه، `invoicing/service.py`، لم يُلمَس في #11b). **الأثر العملي:** أي محاولة إنشاء فاتورة حقيقية لـ`tenant_id=1` حاليًا (عبر التطبيق الفعلي، مش بس الاختبارات) هتفشل بنفس الخطأ لحد ما الفجوة تتصلح أو منطق الترقيم يتغيّر لآلية آمنة (مثل `SERIAL`/DB sequence بدل `count()`). **بسبب هذا البج، 4 من دوال #11b الثمانية (`tourism_sports.purchase_event_ticket`, `realestate.rent_unit`, `insurance.subscribe`, `zamakana.pledge_time`) نزلت من "تحقق حي كامل/جزئي" (كما وثَّقها تقرير #11b الأصلي) لـ"مراجعة بنيوية فقط" في ملف الـregression test — قرار مستخدم صريح، صفر لمس على `invoicing/service.py`. النتيجة النهائية: كل الثمانية دوال بمراجعة بنيوية فقط في ملف الـtest، معوَّضة باختبار تاسع `xfail` يثبت اكتشاف `invoicing-missing-rollback-on-exception-11b` حيًا.** | 🔴 **مفتوح، أولوية عالية** — يمنع إنشاء فواتير حقيقية لـtenant_id=1 حاليًا | `tests/test_realestate_insurance_savepoint.py` |
| — | `eventbus-redis-wrapper-missing-publish` [2026-08-18] — `EventBus.publish()` بتنادي `RedisClientWrapper.publish` غير موجودة (`AttributeError`) — مؤكَّد حيًا في `insurance.subscribe` (بعد `commit()`، بعد محاولة `create_invoice()`). مسبق تمامًا، غير متأثر بديف #11b. **أثر جانبي كان موثَّقًا:** بيمنع الوصول لـ`audit_log`/`_store_idempotency()` في أي دالة بتنادي `event_bus.publish` بعد `create_invoice()`. | ✅ **مُغلَق رسميًا [2026-08-18].** الحل: إضافة `RedisClientWrapper.publish(self, channel: str, message: str)` حقيقية (5 أسطر، `app/core/redis_client.py`، نفس نمط `get`/`setex`/... الموجود) — إضافة صرفة، صفر لمس لـ`EventBus` أو أي ملف دومين. **تصحيح رقم النطاق:** جرد لاحق (`technical-pattern-sweep`) وثّق الرقم كـ"34 من 35 دومين" — **الرقم الصحيح المؤكَّد بجرد كامل: 22 دومين مكسور فعليًا** (مش 34؛ 10 دومينات لا تستخدم EventBus إطلاقًا، و`finance` + `app/tasks/agritech.py` صحيحان أصلًا بنمطين مختلفين تمامًا). **تحقق حي كامل** (subscriber مستقل عن EventBus، إثبات استلام فعلي للرسالة على القناة مع تطابق `event`/`payload` 1:1 — مش بس صفر استثناء) لـ3 دومينات متنوعة: `insurance` (مكان الاكتشاف الأصلي)، `zamakana` (الأبسط)، `arbitration_syndicates` (سياق أحداث متعددة، ونمط بناء نصي مختلف `# type: ignore` مباشر بدل `cast(Any,...)`). **فحص قرائي** للـ19 الباقية أكّد: كل الـ22 يؤولوا فعليًا لنفس التعبير وقت التشغيل (`EventBus(redis_client)` حيث `redis_client` هو نفس الـSingleton) عبر 4 متغيرات نصية فقط (`cast(Any, redis_client)` في 17، `# type: ignore` مباشر في 2 [`commerce`, `arbitration_syndicates`]، بلا أي تعليق في 2 [`employment`, `invoicing`]، ومسار كود ميت `hasattr` يسقط دومًا على نفس القيمة في `agritech`) — `cast()`/`# type: ignore` بلا أي أثر وقت التشغيل، فصفر نمط بناء رابع فعلي مكتشَف. `communications/router.py:84` (نداء `redis_client.publish()` مباشر، نفس الجذر) مغطى تلقائيًا بنفس الإصلاح، مؤكَّد بالقراءة. | `.claude/reports/eventbus-publish-fix-session-log.md` (كامل — تشخيص + ديف + تحقق حي + فحص شامل)؛ خلفية الاكتشاف الأصلي: `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` قسم 15؛ الجرد الموسَّع (مصدر الرقم 34 غير الدقيق): `.claude/reports/technical-pattern-sweep-session-log.md` |
| — | `invitations-missing-expiry-max_uses-validation` | 🔴 مفتوح، أولوية أعلى من العادي | أرشيف ~3344 |
| — | `sovereign_invitations_v2` أعمدة nullable بلا `NOT NULL`/server-default | 🟡 مفتوح، أولوية منخفضة | أرشيف ~3380 |
| — | **`sovereign_entities-unauthenticated-endpoints`** — 4 endpoints (`list_entities`, `get_entity`, `list_templates`, `list_components`) بلا `current_user` في توقيعها؛ **مصححة لاحقًا لكامنة (latent) مش حية حاليًا** — محمية بالصدفة بباج `SimpleTenant` مستقل (نفس نمط "حماية بالصدفة" زي Backlog #9/#11a)؛ إصلاح ذاك الباج بمعزل عن هذا سيفتح تسريب `treasury_balance_mrusdt`/`kyb_status` عبر تينانتات لحسابات `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` | 🔴 **صفر إصلاح — بانتظار توجيه/قرار منتجي صريح** | أرشيف ~2778-2842 (بلا ملف تقرير مستقل، جوه سياق `.claude/reports/simpletenant-fix-session-log.md`) |
| — | `sovereign_entities.review_kyb`/`update_entity` — فقدان كتابة صامت (الـresponse بيرجع القيمة الجديدة، الـDB فاضلة بالقديمة؛ `repo.update_entity` flush-only بلا `begin_nested()`/`commit()` محيط) + 3 حالات مشابهة في `saas` | 🟡 **غير مصنَّف — يحتاج تأكيد لاحقًا** (نُقل كمرجع فقط، بلا فحص كود إضافي؛ قد يتداخل مع بند #4) | أرشيف ~2846-2863 (بلا ملف تقرير مستقل، جوه سياق `.claude/reports/simpletenant-fix-session-log.md`) |
| — | **`ai-governance-create-or-update-quota-multiple-results`** [2026-08-18] — `AIGovernanceRepository.create_or_update_quota()` (`ai_governance/repository.py:20-26`) تستعلم بـ`(agent_id, tenant_id)` فقط بلا فلترة `limit_type`، وتفترض صف واحد (`scalar_one_or_none`). لكن `check_and_consume()` مصمَّمة للتعامل مع وكيل عنده أكثر من نوع حصة فعّال واحد (`TOKEN_COUNT`+`COST_MRUSDT` معًا مثلًا) وتستدعي هذه الدالة داخل حلقة لكل نوع. **أي وكيل حقيقي مُهيَّأ بأكثر من نوع حصة واحد سيتسبب في `sqlalchemy.exc.MultipleResultsFound` عند أول استدعاء ناجح لـ`check_and_consume`** (مؤكَّد حيًا أثناء التحقق من إصلاح #15، بالصدفة عبر تكرار بيانات throwaway حاكى نفس الشرط). خارج نطاق #15/#16 أنفسهم (method مختلفة تمامًا) — لم يُلمَس. | 🔴 **مفتوح، أولوية عالية** — يكسر ميزة "حصص متعددة الأنواع" المصمَّمة أصلًا في `set_quota`، مستقل عن #15/#16 | `.claude/reports/ai-governance-agents-fix-session-log.md` §16 |
| — | **`ai-governance-quota-result-ignored`** [2026-08-18] — `check_and_consume()` ترجع `bool` (سماح/رفض حقيقي حسب الحصة)، لكن **10 من 13 موضع استدعاء (بعد إصلاح #15) بتتجاهل الناتج الراجع تمامًا** (`await governance.check_and_consume(...)` بلا `=`) — يعني إنفاذ الحصة "يعمل" بمعنى إنه لا يرمي استثناء، لكنه **لا يمنع أي تجاوز فعليًا** في أغلب الدومينات (`zamakana`, `insurance`, `tourism_sports`, `tenders_auctions`, `social`, `arbitration_syndicates`, `manufacturing`×2, `logistics`, `invitations`). فقط 3 مواضع (`transport`, `realestate`, `service_marketplace`) تستخدم الناتج فعليًا (`return`/`if not allowed: raise`). إصلاحه يتطلب لمس caller code خارج `check_and_consume` نفسها في 9+ ملفات — خارج نطاق #15. | 🔴 **مفتوح، أولوية عالية** — قريب من خطورة فقدان عمولة affiliate الصامت #10 | `.claude/reports/ai-governance-agents-fix-session-log.md` §3 |
| — | **`action-type-placeholder-copy-paste`** [2026-08-18] — 15 من 19 موضع استدعاء `execute_agent_action()` بتمرر `action_type="ANALYZE_SENSOR"` حرفيًا (نسخ-لصق من قالب واحد) بغض النظر عن السياق الفعلي — تحليل مطالبة تأمين، تقييم توظيف، تحليل نزاع، تحليل استراتيجي، إلخ، كلها مسجَّلة بنفس القيمة الخاطئة في `ai_task_logs`/طلبات الموافقة. لا يُسبِّب كراش (الجسم يقارن `action_type` بـ`"TRANSLATE"` فقط، وإلا افتراضي `ARABIC_CHAT`) لكنه يفسد بيانات التدقيق/التحليلات. اكتُشف أثناء تشخيص #16، مستقل عن بج `tenant_id`/`idempotency_key`. | 🟡 **مفتوح، أولوية عادية** — بيانات مضلِّلة مش كراش | `.claude/reports/ai-governance-agents-fix-session-log.md` §4 |
| — | **`ai-agents-execute-action-commit-inside-begin-nested`** [2026-08-18] — `AIAgentsService.execute_agent_action()` (`ai_agents/service.py:223,226`) تنفّذ `await self.db.commit()` داخل جسمها (مساري النجاح والفشل معًا). موضعان يستدعيانها من **جوّه `async with self.db.begin_nested()`** خارجي بلا `try/except`: `realestate/service.py:232` (داخل `buy_fractional_ownership`، عملية شراء ملكية بأموال حقيقية) و`invitations/service.py:415` (داخل `chat_with_ai`). حاليًا يفشلان دومًا بـ`TypeError` (نفس بج #16) **قبل** الوصول لجسم الدالة، فالمشكلة كامنة (latent) لا حية بعد. **لو صُلِّحا بنفس منطق باقي #16 (حذف `tenant_id=`/إضافة `idempotency_key=`) بمعزل عن هذا البند، سيصلان لأول مرة لتنفيذ `commit()` حقيقي وهما لسه جوّه savepoint** — احتمال تلف حالة transaction بالكامل، نفس فئة خطورة #11a/#11b الجذرية، لكن هنا الكراش سبب فعلي لكسر نفس الـcommit المفروض يحمي العملية (عكس #11a/#11b حيث الكراش كان بعد commit ناجح). **الإصلاح الحقيقي المطلوب:** نقل نداء `execute_agent_action` بره `begin_nested()` في الدالتين أولًا، ثم تصحيح kwargs — الموضعان لازم يُصلَحا سوا، ممنوع تصحيح الـkwargs بمعزل عن حل بنية المعاملة. | 🔴 **مفتوح، أولوية عالية جدًا** — نفس فئة #11a/#11b | `.claude/reports/ai-agents-execute-action-fix-session-log.md` §4، §7 |
| — | **`ai-agents-execute-action-approval-queue-global-unique-collision`** [2026-08-18] — عمود `AgentApprovalQueue.idempotency_key` (`ai_agents/models.py:86`) `unique=True` **على مستوى الـDB بالكامل، بلا أي قيد مركّب مع `tenant_id`** (بعكس `AITaskLog.idempotency_key` اللي `index=True` بس). **مؤكَّد حيًا [2026-08-18]:** استدعاءان لـ`execute_agent_action` من تينانتين مختلفين بنفس `idempotency_key` الخام (بلا تمييز tenant داخل النص) يسببان `IntegrityError`/`UniqueViolationError` فعليًا عند إنشاء طلب الموافقة الثاني (`requires_human_approval` افتراضي `True`). كل القيم المُضافة في إصلاح #16 تتجنب هذا بتضمين `T{tenant_id}` صراحة في النص، لكن هذا **تعامل دفاعي على مستوى الاستدعاء فقط**، مش حل بنيوي — المواضع الآمنة الستة (وأي كود مستقبلي) لسه بتعتمد على عشوائية `uuid` بدل قيد DB حقيقي. **الحل الجذري:** تحويل القيد إلى `UniqueConstraint(tenant_id, idempotency_key)` (migration). | 🔴 **مفتوح، أولوية عالية** — خطر تصادم عابر للمستأجرين (cross-tenant) على مستوى الـschema نفسه | `.claude/reports/ai-agents-execute-action-fix-session-log.md` §1، §5، §10 |
| — | **`communications-service-get-user-missing-method`** [2026-08-18] — `communications/service.py:29,36` (`CommunicationsService._get_user_tenant`/`_get_user_email`) بينادوا `self.user_repo.get_user(user_id)` — الدالة دي **مش موجودة** على `UserRepository` (الصحيحة `get_by_id`) → `AttributeError` مؤكَّد حيًا. الأثر: **`POST /communications/notifications/send` معطَّل بالكامل حاليًا** — الكراش بيحصل جوّه `send_notification()` **قبل الوصول لـ`audit_log()` من الأساس**، يعني مش مرتبط ببند #14 إطلاقًا رغم اكتشافه أثناء التحقق الحي له. اتكتشف أثناء محاولة استخدام `send_notification` كعيّنة تحقق لبند #14، واستُبدلت العيّنة بـ`move_to_trash` (نفس الملف، بلا اعتماد على الدالة المكسورة) لإتمام التحقق. **✅ مُغلَق رسميًا [2026-08-19، جلسة `user-repository-get-user-audit`، Backlog #8]:** `_get_user_tenant:29` — **استثناء معماري مؤكَّد حيًا**: الغرض من الدالة هو اكتشاف `tenant_id` نفسه (مستخدَمة في `send_notification:63` بواسطة superuser يستهدف أي مستخدم، و`send_mail:144/145` للتحقق إن المرسل والمستلم في نفس الـtenant) — **لا يوجد `tenant_id` متاح في نطاق أي نقطة استدعاء أصلًا**، فالحل المعتاد (إضافة معامل) لا ينطبق. الحل: **method جديدة على `UserRepository`**، `get_tenant_id_by_user_id(user_id) -> Optional[int]` (least-privilege — ترجع `tenant_id` فقط، لا كائن `User` كامل)، و`_get_user_tenant` بقت تنادي عليها مباشرة. `_get_user_email:36` **تُركت بلا لمس عمدًا — Dead code مؤكَّد** (صفر مستدعٍ حي في الملف/المشروع كله). تحقق حي: `send_notification`/`send_mail` بقيا يعملان بلا `AttributeError`. تفصيل كامل + regression test: `.claude/reports/user-repository-get-user-audit-session-log.md` §3.3، `tests/test_user_repository_get_user_audit.py`. | ✅ **مُغلَق رسميًا** | `.claude/reports/audit-log-fix-session-log.md` §10؛ `.claude/reports/user-repository-get-user-audit-session-log.md` §3.3، §6.2 |
| — | **`health-service-get-user-email-dead-code-uses-missing-method`** [2026-08-19] — اكتُشف أثناء جلسة `user-repository-get-user-audit` (Backlog #8): `health/service.py:50-55` (`_get_user_email`) بتنادي `UserRepository.get_user(user_id)` غير الموجودة — لكن **بلا أي مستدعٍ حي في الملف أو المشروع كله** (`grep` شامل: صفر نتيجة). نفس فئة `logistics-affiliate-commission-dead-code-uses-broken-get-by-id` بالضبط (كود ميت يستخدم استدعاء مكسور). **قرار نطاق صريح:** تُركت بلا لمس عمدًا — اختبار `regression` مخصَّص (`tests/test_user_repository_get_user_audit.py::test_health_get_user_email_left_untouched_as_documented_dead_code`) بيوثِّق ويقفل الحالة الحالية عمدًا (بيفشل تحذيريًا لو حد أضاف مستدعٍ حي مستقبلًا بلا مراجعة هذا البند). | 🟡 **مفتوح، أولوية منخفضة (كود ميت، صفر أثر إنتاجي حاليًا)** — يستاهل إصلاح `get_by_id(user_id, tenant_id)` **فقط لو/لما** يُضاف مستدعٍ حي لها مستقبلًا | `.claude/reports/user-repository-get-user-audit-session-log.md` §3.5، `tests/test_user_repository_get_user_audit.py` |
| — | **`insurance-review-claim-issuer-entity-id-reviewer-id-conflict`** [2026-08-19] — اكتُشف أثناء كتابة regression test لبند #9 (`tests/test_saas_active_subscription.py`، جلسة `regression-tests-backfill`): `InsuranceService.review_claim()` (`insurance/service.py:431`) بتفحص التفويض بمقارنة مباشرة `if cast(int, policy.issuer_entity_id) != reviewer_id: raise PermissionDeniedError(...)` — لكن `policy.issuer_entity_id` قيمة من نطاق `sovereign_entities_v2.id`، بينما `reviewer_id` بيتمرر من الراوتر (`insurance/router.py:195`) كـ`current_user.id` — قيمة من نطاق `users.id` مختلف تمامًا. **نفس فئة البج المسبق الموثَّق `tourism-place-transfer-bid-player-id-user-id-conflict`** (خلط نطاقي IDs مختلفين كأنهما نفس المعنى). **الأثر العملي:** أي `superuser` حقيقي بيحاول يراجع مطالبة تأمين حقيقية (`PUT /insurance/claims/{id}/review`) هيرجعله `PermissionDeniedError("Not authorized to review this claim")` **دايمًا تقريبًا**، إلا لو `user.id` بتاعه صادف يساوي رقميًا `sovereign_entities_v2.id` بتاع الكيان المُصدِر للبوليصة (تصادم غير وارد عمليًا، مفيش أي منطق ربط بين الجدولين) — يعني **ميزة الموافقة/الرفض على مطالبات التأمين معطَّلة فعليًا لأي مستخدم حقيقي في الإنتاج**. **مؤكَّد بالقراءة المباشرة لكود الراوتر والخدمة معًا [2026-08-19]، صفر افتراض.** اختبار regression تجاوز البج ده عمدًا وقتها (بتمرير نفس القيمة الثابتة `EXISTING_ISSUER_ENTITY_ID=4` كـ`issuer_entity_id` **و**`reviewer_id` معًا) عشان يوصل لهدفه الفعلي وقتها (تأكيد بج #1 `UserRepository.get_by_id` بعده) — مش اختبار سيناريو واقعي لمسار المراجع. **⚠️ تحديث [2026-08-19، جلسة `user-repository-get-by-id-audit`]:** بعد إغلاق Backlog #1، الاختبار **حُدِّث ليثبت هذا البج مباشرة بدل تجاوزه** — `reviewer_id` بقى `claimant.id` (قيمة واقعية من نطاق `users.id`، مختلفة عمدًا عن `issuer_entity_id`)، والاختبار الآن بيؤكد حيًا `pytest.raises(PermissionDeniedError, match="Not authorized to review this claim")` كسلوك **متوقَّع ومقصود** (يوثِّق البج، لا يصلحه). **صفر لمس على `insurance/service.py` نفسها** في أي من الجلستين. | 🔴 **مفتوح، أولوية عالية جدًا** — يعطّل ميزة إنتاجية كاملة (مراجعة مطالبات التأمين) لأي مستخدم حقيقي؛ **مؤكَّد حيًا بشكل مباشر (مش عبر تجاوز) بعد 2026-08-19** | `tests/test_saas_active_subscription.py`، `insurance/service.py:431`، `insurance/router.py:195` |
| — | **`ai-governance-usage-log-idempotency-wrong-arity`** [2026-08-19] — اكتُشف أثناء كتابة regression test لبند #15 (`tests/test_ai_governance_check_and_consume.py`، جلسة `regression-tests-backfill`): `AIGovernanceService.check_and_consume()` (`ai_governance/service.py:152`) بتنادي `self.repo.get_usage_log_by_idempotency(idempotency_key)` بمعامل واحد بس، لكن `AIGovernanceRepository.get_usage_log_by_idempotency()` (`repository.py:66`) توقيعها الحقيقي `(idempotency_key: str, tenant_id: int)` — `tenant_id` إجباري بلا `default`. **الأثر:** أي استدعاء `check_and_consume()` بـ`idempotency_key` حقيقي (غير `None`/فارغ) يكراش فورًا بـ`TypeError`. **هذا باج جديد كليًا داخل جسم `check_and_consume` نفسها، منفصل تمامًا عن بج `tenant_id`/`action_type` الموثَّق في #15** (الأخير في توقيع `check_and_consume` الخارجي، هذا في نداء داخلي لدالة تانية). **الموضع الوحيد من الـ13 المُصلَحة في #15 اللي بيمرر `idempotency_key` فعليًا هو `service_marketplace/service.py:159`** (`idempotency_key=idempotency_key`، القيمة جايه من `purchase_service(..., idempotency_key: Optional[str] = None)`). **شرط التفعيل الدقيق (مؤكَّد من الراوتر مباشرة، `service_marketplace/router.py:90`):** `idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")` — **هيدر HTTP اختياري**. يعني الكراش **مش حتمي على كل استدعاء** (بعكس بج `review_claim`/`issuer_entity_id` اللي بيفشل على كل استدعاء حقيقي بلا استثناء) — بيحصل **فقط** لو العميل (frontend/caller) فعليًا بعت هيدر `Idempotency-Key` غير فارغ مع طلب الشراء (ممارسة قياسية متوقَّعة لـendpoint شراء/دفع، لكن غير مضمونة بنيويًا من الكود نفسه). لو الهيدر غايب، الشرط `if idempotency_key:` (`ai_governance/service.py:151`) بيفشل بهدوء والمسار بيكمل عادي بلا كراش. مُثبَت باختبار `xfail(strict=True)` موثَّق في الملف نفسه (بتمرير `idempotency_key` فعلي عمدًا لإثبات الكراش). **صفر لمس على `ai_governance/service.py`/`repository.py`/`service_marketplace/*`.** | 🔴 **مفتوح، أولوية عالية** — يعطّل مسار شراء حقيقي (`service_marketplace`) كلما استُخدمت idempotency فعليًا | `tests/test_ai_governance_check_and_consume.py`، `ai_governance/service.py:152`، `ai_governance/repository.py:66` |
| — | **`agritech-redis-calls-missing-await-orphaned-coroutines`** [2026-08-19] — اكتُشف أثناء تشخيص بند #7 (`redis-client-wrapper-missing-methods`، جلسة `redis-client-wrapper-missing-methods`): `app/tasks/agritech.py` بتستخرج عميل Redis خام حقيقي يدويًا (`redis_client = await redis_client_wrapper.get_client()`, سطر 255) ثم بتنادي عليه `redis_client.setex(...)` (سطر 243، داخل `_analyze_medium_priority`)، `redis_client.lpush(...)` (سطر 257)، و`redis_client.ltrim(...)` (سطر 261، الاتنين الأخيرتين داخل `_analyze_low_priority`) — **الثلاثة نداءات بلا `await`**. بما إن هذه methods من `redis.asyncio.Redis` كلها `async def` (بترجع coroutine بدل تنفيذ العملية مباشرة)، النداء بلا `await` **لا ينفّذ عملية Redis إطلاقًا** — ينشئ coroutine "يتيم" (orphaned) لا يُشغَّل أبدًا. **هذا باج مختلف جذريًا عن #7** (مش method مفقودة على `RedisClientWrapper` — العميل هنا خام وعنده الـmethods الثلاثة أصلًا؛ المشكلة نحوية بحتة، نسيان `await`). **الأثر المحتمل (غير مؤكَّد حيًا بعد، قراءة كود فقط):** بيانات القراءات الزراعية (`agritech:zone:{id}:last_reading`, `agritech:zone:{id}:daily_readings`) المفروض تتخزَّن/تُقصّ في Redis **مش بتتسجَّل فعليًا إطلاقًا رغم إن الكود شكليًا "بينفّذ" بلا استثناء ظاهر** — فشل صامت بالكامل. **صفر لمس على `agritech.py`** — خارج نطاق جلسة #7 صراحة بقرار مستخدم. | 🔴 **مفتوح، لم يبدأ فحص/إصلاح** — يحتاج تحقق حي (Redis) لتأكيد الفشل الصامت قبل أي إصلاح | `.claude/reports/redis-client-wrapper-missing-methods-session-log.md` §3.2 |
| — | **`affiliate-distribute-commissions-celery-task-wrong-signature`** [2026-08-19] — اكتُشف أثناء جلسة تشخيص `referral-system-multilevel-investigation` (تمهيدًا لقرار `identity-user-referred-by-field-missing`، Backlog #10): مهمة Celery `affiliate.distribute_commissions` (`app/tasks/affiliate.py:58-67`) بتنادي `service.distribute_commissions(order_id, tenant_id)` بمعاملين، لكن التعريف الفعلي `AffiliateService.distribute_commissions(self, order_id: int)` (`affiliate/service.py:261`) بياخد معامل واحد بس (`order_id`) — أي تفعيل فعلي للمهمة سيرمي `TypeError` فورًا. **مؤكَّد إضافيًا (`grep` شامل) إن المهمة نفسها غير مُفعَّلة أصلًا اليوم** — صفر استدعاء `.delay(`/`.apply_async(`/`send_task("affiliate.distribute_commissions"` في المشروع بالكامل، فالباج كامن (latent) لا حي حاليًا. مرتبط مباشرة ببند `affiliate-get-referral-tree-multiple-results-on-multi-scope` تحت (نفس المسار الميت، نظام "A" في تقرير الجلسة). | 🔴 **مفتوح، أولوية منخفضة حاليًا (كود ميت التفعيل)** — لازم يُصلَح **قبل** أي محاولة تفعيل مستقبلية لهذه المهمة | `.claude/reports/referral-system-multilevel-investigation-session-log.md` §4.أ |
| — | **`affiliate-get-referral-tree-multiple-results-on-multi-scope`** [2026-08-19] — اكتُشف في نفس جلسة `referral-system-multilevel-investigation`: `AffiliateRepository.get_referral_tree(user_id, tenant_id)` (`affiliate/repository.py:80-86`) بتستعلم `ReferralTree.referred_id == user_id` بلا أي فلتر `entity_type`/`entity_id`، وبتفترض نتيجة واحدة (`scalar_one_or_none()`). لكن القيد الفريد الفعلي على الموديل (`ix_referral_trees_unique_referred_scope`، `affiliate/models.py:46-47`) يسمح **صراحة** بأكثر من صف لنفس `referred_id` — واحد لكل (`entity_type`, `entity_id`)، أي لكل منتج/كورس/كيان على حدة (التصميم نفسه Product-Scoped عمدًا، راجع docstring الموديل). **الأثر:** `AffiliateService._distribute_levels` (`affiliate/service.py:317-372`) بتستخدم بالضبط هذه الدالة للمشي صعودًا في سلسلة الإحالة (مين أحال المُحيل) — **أي مستخدم له أكثر من صف إحالة فعلي (له أكثر من منتج/كورس أحاله شخص) سيتسبب في `sqlalchemy.exc.MultipleResultsFound` مؤكَّد لو تم الوصول له أثناء صعود السلسلة**، حتى لو نظام التوزيع نفسه (`distribute_commissions`) اتفعّل مستقبلًا. **هذا الباج يمنع مباشرة أي دعم مستقبلي لـ"إحالة قابلة للربط بأكثر من منتج" (المتطلب المنتجي المطروح في جلسة التشخيص) ما لم يُصلَح أولًا** — حتى لو النظام (A) بالكامل فُعِّل وأُصلح باج التوقيع أعلاه. صفر لمس/إصلاح في جلسة التشخيص (قرار نطاق: توثيق فقط). | 🔴 **مفتوح، أولوية عالية عند أي محاولة تفعيل/توسيع نظام A** — عائق بنيوي مباشر أمام دعم عدة منتجات لكل مستخدم | `.claude/reports/referral-system-multilevel-investigation-session-log.md` §2 |
| — | **`academy-create-course-instructor-id-duplicate-kwarg`** [2026-08-20] — اكتُشف أثناء جلسة `require-sector-removal-subscription-fix` (سيناريو الاختبار الحي #2/#5): بعد إصلاح بوابتي `require_sector`/`require_subscription`، أول طلب `POST /academy/courses` وصل فعليًا لمنطق الإنشاء الحقيقي لأول مرة — واصطدم فورًا بباج **مختلف كليًا** عن `create_org_entity` الموثَّق سابقًا. `academy/service.py:112`: `await self.repo.create_course(**data, instructor_id=instructor_id)` — لكن `data` (من `CourseCreate.model_dump()`) يحتوي أصلًا مفتاح `instructor_id` (حقل اختياري على الـschema، `schemas.py:118`)، فيتكرر التمرير → `TypeError: got multiple values for keyword argument 'instructor_id'`. **الأثر:** أي `POST /academy/courses` ناجح من ناحية الصلاحيات/الاشتراك (وهو الحال الآن بعد الإصلاح) سيفشل 500 دائمًا. صفر لمس على `academy/service.py` في جلسة الاكتشاف (خارج نطاقها صراحة). **✅ مُغلَق رسميًا [2026-08-20، جلسة `academy-priority-fix`]:** استبعاد `instructor_id` من `data` قبل `**kwargs`، استخدام معامل `instructor_id` (من `current_user.id`) حصريًا. تحقق حي: `POST /academy/courses` بجسم يحتوي محاولة انتحال (`"instructor_id":999`) → 201، القيمة المخزَّنة فعليًا = المستخدم الحقيقي، `999` تجوهلت تمامًا. تفصيل كامل: `.claude/reports/academy-priority-fix-session-log.md`. | ✅ **مُغلَق رسميًا** | `.claude/reports/require-sector-removal-subscription-fix-session-log.md` §7؛ `.claude/reports/academy-priority-fix-session-log.md` |
| — | **`sovereign-entities-create-entity-tenant-id-duplicate-kwarg`** [2026-08-20] — اكتُشف أثناء التحقق الحي في جلسة `entity-membership-sovereign-entities-integration` (الجلسة 2 من 2، مسار الصلاحيات الجديد) عند محاولة اختبار `POST /sovereign-entities/` الحقيقي عبر uvicorn حي: `sovereign_entities/router.py::create_entity` بيضبط `entity_data["tenant_id"] = tenant_id` في الـdict المُمرَّر لـ`service.create_entity(user_id, entity_data)`، والتي بدورها بتنادي `self.repo.create_entity(tenant_id=self.tenant_id, created_by=user_id, **data)` — نفس `tenant_id` بيتمرر مرتين (باراميتر صريح + داخل `**data`) → `TypeError: got multiple values for keyword argument 'tenant_id'` فوري، **نفس فئة الباج بالحرف** الموثَّقة في `academy-create-course-instructor-id-duplicate-kwarg` أعلاه. **الأثر:** `POST /sovereign-entities/` (endpoint إنشاء الكيان السيادي) معطوب بالكامل حاليًا في الإنتاج — يفشل 500 قبل ما يوصل حتى لأي منطق لاحق، **بما فيه باج الازدواج المسبق التوثيق** (`sovereign_entities` Backlog #5 أعلاه، استدعاء `add_representative` المكرر بعد `create_entity` في نفس الراوتر) — لأن التنفيذ يتوقف عند `TypeError` قبل الوصول له أصلًا. **مؤكَّد إنه باج مسبق بالكامل، غير متعلق بأي تعديل من جلستي مسار `entity-membership` (لا الجلسة 1 ولا الجلسة 2)** — لا `router.py:29` (بناء `entity_data`) ولا استدعاء `self.repo.create_entity` (`service.py`) اتلمسوا في أي diff من الجلستين، تحقق مباشر. **صفر لمس/إصلاح — خارج نطاق الجلسة صراحة، توثيق فقط.** لا صف يُنشَأ عند الفشل (الاستثناء يحصل قبل أي لمس لقاعدة البيانات)، فصفر بيانات throwaway محتاجة تنظيف. | 🔴 **مفتوح، أولوية عالية جدًا** — يمنع أي إنشاء كيان سيادي ناجح عبر الـAPI بالكامل | `.claude/reports/entity-membership-sovereign-entities-integration-session-log.md` §5.3 |
| — | **`three-competing-affiliate-commission-systems`** [2026-08-19] — اكتشاف مركزي في جلسة `referral-system-multilevel-investigation`: يوجد في المشروع **ثلاثة أنظمة إحالة/عمولة منفصلة تمامًا، بثلاث مخططات بيانات مختلفة، لا تتقاطع مع بعضها إطلاقًا** — لم يكن أي منها موثَّقًا مجتمعًا في جلسة سابقة واحدة. **نظام A (`affiliate` domain، 10 مستويات Product-Scoped):** `ReferralTree`+`Commission`+`CommissionTier` — مبني جزئيًا بدعم نسبة عمولة لكل منتج (`_get_commission_rate` تأخذ `product_id` فعليًا، `CommissionTier.target_product_id`)، لكنه **ميت تشغيليًا بالكامل** (راجع `affiliate-distribute-commissions-celery-task-wrong-signature` أعلاه) وبه باج بنيوي (راجع `affiliate-get-referral-tree-multiple-results-on-multi-scope` أعلاه). **نظام B (`commerce` domain، 10 مستويات Sponsor Chain — اكتشاف جديد كليًا، لم يُذكر في أي تقرير سابق):** `AffiliateTree`+`CommissionRecord`+`AffiliateConfig` (`commerce/models.py:191-248`) — **هو المسار الحي الوحيد فعليًا** لتوزيع عمولات 10 مستويات على طلبات شراء حقيقية اليوم، مُستدعى مباشرة (inline، بلا Celery) من `CommerceService.checkout()` عبر `CommerceService.distribute_commissions()` (`commerce/service.py:215-220, 251-292`). كود الإحالة هنا **رقمي** (`sponsor_code = int(affiliate_code)`، حرفيًا `user_id`)، بعكس نظام A (كود أبجدي `AffiliateProfile.referral_code`) — **نظاما الأكواد غير متوافقين إطلاقًا**. `AffiliateConfig` صف واحد فقط لكل tenant، **بلا أي عمود `product_id`/`category_id`** في أي من الموديلات الثلاثة — نسبة واحدة عامة بغض النظر عن المنتج المُشترى. **نظام C (الـ12 دومين، Backlog #10):** `ActionCommission` عبر `register_commission`/`_register_affiliate_commission` — عمولة مباشرة لمستوى واحد فقط (`user.referred_by`)، بمبلغ Hardcoded ثابت لكل دومين، بلا أي نسبة أو مستوى متصاعد، **ومحجوبة بالكامل حاليًا ببند `identity-user-referred-by-field-missing`** (فوق). **الرابط المباشر بالصورة الأكبر:** أي قرار مستقبلي لحل `User.referred_by` (بند 5.3) أو لدعم "نسبة عمولة مختلفة حسب المنتج/القسم" **يجب أن يحسم أولًا** أي من الأنظمة الثلاثة (أو توحيد بينها) هو المرجع النهائي — القطع الأقرب لدعم تعدد المنتجات (نظام A) هي بالضبط القطع الميتة/المعطوبة اليوم، بينما النظام الحي فعليًا (B) لا يدعم هذا البُعد إطلاقًا. **صفر قرار تصميمي اتُّخذ في جلسة التشخيص — توثيق فقط بقرار مستخدم صريح.** | 🔴 **مفتوح، يتطلب جلسة نقاش/قرار معماري منفصلة قبل أي تنفيذ** — يمس مباشرة بند #10 وبند `identity-user-referred-by-field-missing` | `.claude/reports/referral-system-multilevel-investigation-session-log.md` (كامل، خصوصًا الملخص التنفيذي وأقسام 4، 5، 6، 7) |
| — | **`installments-shared-service`** [2026-08-21] — قرار منتجي (`academy-product-decisions.md` §1-د، جلسة `academy-product-decisions-implementation`): الأقساط آلية دفع عامة (تنطبق على المتجر/التأمين/العقارات، لا التعليم فقط)، فلا تُبنى داخل الأكاديمية. `PaymentInstallment`/`Financial Summary.total_overdue` (academy) بقيا مجمَّدين عمدًا (تعليقات توثيقية أُضيفت في نفس الجلسة، صفر منطق). | 🔴 **مفتوح، لم يبدأ** — جلسة تصميم منفصلة مطلوبة: خدمة أقساط مشتركة (Installments Service) عبر القطاعات، تُستهلَك كـAPI من أي قطاع يحتاجها | `.claude/plans/academy-product-decisions.md` §1-د؛ `.claude/reports/academy-product-decisions-implementation-session-log.md` (البند 4) |
| — | **`projects-schema-model-field-mismatch`** [2026-08-24] — 🟢 **محلي (دومين `projects` وحده)، فئة `constructor-mismatch` (عدم تطابق Schema↔Model، مش duplicate-kwarg) — 3 حالات مؤكَّدة حيًا خلال جلسة `projects-idor-fix`، مُكتشَفة أثناء زرع بيانات throwaway ومحاولة التحقق الحي عبر الـAPI الحقيقي:** (1) `ProjectCreate` schema فيها 20+ حقل (`city`, `latitude`, `longitude`, `min_investment_mrusdt`, `allow_fractional_ownership`, `gallery_urls`, ...) والموديل `Project` (`models.py:50-83`) عنده أقل من نصفهم — `service.create_project` بتعمل `Project(**data.model_dump())` كامل → `TypeError: 'city' is an invalid keyword argument for Project`، فوري، **يمنع `POST /projects/` بالكامل لأي مستخدم/تينانت**. (2) `Contribution` model (`models.py:105-127`) عنده بس `amount_mrusdt` من كل حقول `ContributionCreate` الاختيارية (`land_area_sqm`, `labor_hours`, `equipment_estimated_value`, `consulting_hours`, ...) → `TypeError` فوري لأي مساهمة من 5 أنواع من أصل 6 (`LAND`/`FACILITY`/`LABOR_HOURS`/`EQUIPMENT`/`CONSULTING`) — **نوع `MONETARY` وحده ينجو** (بيستخدم `amount_mrusdt` الموجود فعليًا كعمود). (3) `ProjectUpdate` model (`models.py:130-148`) عنده بس `title`/`content`، بينما `media_urls` حقل أساسي في `ProjectUpdateCreate` مُمرَّر دايمًا (حتى لو `[]`) → `TypeError: 'media_urls' is an invalid keyword argument for ProjectUpdate`، فوري، **يمنع `POST /{id}/updates` بالكامل لأي مستخدم بغض النظر عن الملكية**. **الأثر على IDOR:** الحالتان (1) و(3) تحجبان فعليًا استغلال ثغرتي IDOR مؤكَّدتين في نفس الدومين (`create_project` عبر-تينانت، و`add_project_update` بلا فحص ملكية) — تمامًا زي حجب `ai_governance._check_agent_ownership` سابقًا. **صفر لمس/إصلاح — خارج نطاق جلسة `projects-idor-fix` صراحة (كانت مخصَّصة للجذر IDOR فقط)، توثيق فقط.** صفر بيانات throwaway متأثرة (كل الاستثناءات حصلت قبل أي `INSERT` فعلي، تحقُّق مستقل). | 🔴 **مفتوح، لم يبدأ** — إصلاح محلي بحت (مواءمة أعمدة الموديل مع حقول الـschema في 3 جداول، أو تقليم الـschema لو الحقول الزيادة غير مطلوبة فعليًا) — صفر سبب جذري مشترك مع أي دومين آخر، لا يستدعي جلسة عابرة للدومينات | `.claude/reports/projects-idor-fix-session-log.md` §4.1 |
| — | **`affiliate-commission-tiers-duplicate-global-null-gap`** [2026-08-25] — **ثغرة سلامة بيانات كامنة حقيقية (data integrity)، وليست مجرد ملاحظة عابرة** — اكتُشفت أثناء التحقق الحي لجلسة `tenant-system-account-phase3-conversion` (زرع بيانات throwaway لموقع `affiliate.withdraw_commissions`). الفهرس الفريد المُعرَّف فعليًا على `affiliate_commission_tiers` هو `UNIQUE(tenant_id, entity_type, target_product_id)` — القصد منه منع أكثر من صف `GLOBAL` واحد لكل تينانت (`target_product_id IS NULL` في هذه الحالة). لكن **دلالة `NULL` في فهارس Postgres الفريدة تعتبر كل قيمة `NULL` "مختلفة" عن أي `NULL` أخرى** (بعكس القيم الفعلية) — أي إدراج أكثر من صف `GLOBAL` لنفس التينانت **ينجح بصمت بلا أي `IntegrityError`**، رغم أن القيد صُمِّم تحديدًا لمنع هذا بالضبط. **الأثر العملي:** أي كود يعتمد على `get_commission_tiers()` (اللي بتفترض ضمنيًا صفًا واحدًا فقط عبر `scalar_one_or_none()` أو ما يعادلها) معرَّض لسلوك غير متوقَّع (أي صف من عدة صفوف صالحة يُرجَع فعليًا، حسب ترتيب القراءة) لو تكرر إدراج هذا الصف — ليس افتراضًا نظريًا: **حصل فعليًا وبالصدفة أثناء إعادة تشغيل جزء من اختبار Phase 3 هذا (صف مكرر بمعرّف `affiliate_commission_tiers.id=7`، اكتُشف وحُذف يدويًا فورًا كجزء من تنظيف بيانات الاختبار، صفر أثر على بيانات حقيقية)**. **الحل المطلوب (لم يُنفَّذ، خارج نطاق Phase 3 صراحة):** فهرس فريد جزئي (partial unique index) بدل الفهرس المركَّب الحالي — مثلًا `UNIQUE(tenant_id) WHERE entity_type='GLOBAL' AND target_product_id IS NULL` (نفس نمط `uq_users_tenant_system_account` المُضاف في نفس الجلسة لحساب النظام الموحَّد لكل تينانت) — يحتاج migration + تحقق من عدم وجود تكرارات فعلية بالفعل في القاعدة الحية قبل تطبيق القيد الجديد. | 🔴 **مفتوح، أولوية متوسطة-عالية** — ثغرة سلامة بيانات حقيقية مؤكَّدة حيًا (ليست افتراضية)، تمس دومين مالي (عمولات الإحالة) | `.claude/reports/tenant-system-account-phase3-conversion-session-log.md` §4.3 |
| — | **`saas-social-limits-catalog-unseeded`** [2026-08-25] — اكتُشف أثناء التحقق الحي لموقع `social.subscribe_group_to_plan` (جلسة `tenant-system-account-phase3-conversion`): `SocialService._check_saas_limits(tenant_id, "social")` بينادي `SaaSControlService.can_access_service("social")`، اللي بيدوّر عن صف بـ`saas_service_catalog.code='social'` — **صفر صف بهذا الكود موجود في القاعدة الحية بالكامل**. النتيجة: أي استدعاء حقيقي لـ`subscribe_group_to_plan` (أو أي دالة تانية بتمر عبر نفس الفحص) بيرجع `has_access=False` دايمًا → `PermissionDeniedError` فوري، بغض النظر عن وجود اشتراك حقيقي صالح من عدمه — **يمنع الميزة بالكامل حاليًا لأي تينانت**. للوصول لمنطق `finance.transfer` المطلوب تحقيقه في نفس الجلسة، لزم تجاوز الفحص بـ`monkeypatch` على مستوى instance داخل سكربت الاختبار فقط (صفر لمس على الكود المصدري). | 🔴 **مفتوح، لم يبدأ** — يحتاج زرع صف `saas_service_catalog(code='social')` (أو مراجعة هل الميزة يُفترض أصلًا تُستثنى من فحص `_check_saas_limits`، قرار منتجي) | `.claude/reports/tenant-system-account-phase3-conversion-session-log.md` §4.3 |
| — | **`stale-test-user-system-eppne-com`** [2026-08-25] — ليس باجًا في الكود، بل بقايا بيانات اختبار من جلسة سابقة تستحق تسجيلًا صريحًا لتفادي التباس مستقبلي: مستخدم حقيقي في القاعدة الحية بالبريد `system@eppne.com` (`id=43`, `username=p_ctor_proj_sysrecv`, أُنشئ 2026-08-14) — كان على الأرجح فِخًّا/حلاً بديلًا مُتعمَّدًا لسدّ ثغرة الحساب الثابت القديمة (`receiver_email="system@eppne.com"` الهاردكودد) قبل حل `tenant-system-account` الحالي. الكود الحالي (بعد Phase 3) **لا يشير لهذا البريد بأي شكل إطلاقًا** — الصف خامل تمامًا، بلا أي تأثير وظيفي. مذكور هنا فقط لأنه قد يُربِك أي جلسة تشخيص مستقبلية تبحث عن "من يملك هذا البريد". | 🟡 **مفتوح، أولوية منخفضة جدًا (تنظيف بيانات فقط)** — حذف الصف اختياري، بلا أي أثر وظيفي إن تُرك | `.claude/reports/tenant-system-account-phase3-conversion-session-log.md` §4.3 |
| — | **`invoicing-invoice-model-metadata-attribute-collision`** [2026-08-25] — اكتُشف أثناء التحقق الحي لإصلاح Backlog #23 (`invoicing-list-invoices-wrong-kwarg`، جلسة `constructor-mismatch-backlog-cleanup`): بعد إزالة الـkwarg الزايد بنجاح (التحقق أكَّد اختفاء `TypeError` تمامًا)، الاستدعاء الحي لـ`InvoicingRepository.list_invoices()` كشف باجًا مختلفًا كليًا وأعمق: عمود `Invoice.metadata` بيتصادم مع attribute محجوز على مستوى SQLAlchemy declarative (`Base.metadata`) — أي محاولة تسلسل صف `Invoice` حقيقي عبر `InvoiceResponse.model_validate(inv)` تفشل بـ`pydantic_core.ValidationError: Input should be a valid dictionary` (لأن القيمة المقروءة فعليًا هي كائن `MetaData()` مش الـdict المتوقَّع). **الأثر (وقتها):** `GET /invoicing/invoices` معطوب بالكامل لأي تينانت عنده فاتورة واحدة حقيقية على الأقل — بغض النظر عن إصلاح الـarity. مؤكَّد حيًا (تينانت1، فاتورة حقيقية موجودة). **✅ مُغلَق [اكتُشف الإغلاق 2026-08-29، جلسة `invoicing-21-metadata-collision`]:** هذا البند نفسه هو #21 في `constructor-mismatch-backlog-classification.md`. التحقيق في جلسة 2026-08-29 (المفروض تحديد قرار تصميم أ/ب) اكتشف إن العطل **مش موجود أصلًا في الكود الحالي** — الموديل والـmigration كانا دايمًا `invoice_metadata` (صفر تصادم على مستوى الـDB/ORM)، والتصادم كان محصورًا في `InvoiceBase.metadata` (schema فقط). اتصلح فعليًا بنفس اليوم (2026-08-25) عبر commit `93e68ac` (`fix(invoicing): close create_invoice mass-assignment, fix masked metadata bug`) — إصلاح جانبي مذكور صراحة في نفس commit message، لكن معنون لبند أمني مختلف تمامًا (mass-assignment)، فمافيش حد لاحظ وقتها إنه بيقفل هذا البند بالذات — من هنا جاء التضارب بين هذا السطر (فاضل "مفتوح") وتصنيف #21 (فاضل "لسه مفتوح، يحتاج قرار تصميم"). **تحقق حي بعد الإصلاح [2026-08-29]:** 5 فواتير حقيقية (من أصل 16 لتينانت 1) مُرِّرت فعليًا عبر `InvoiceResponse.model_validate()` — صفر استثناءات، `invoice_metadata` بيتسلسل صح. النمط المتبع فعليًا بالمشروع (9 دومينات فحصت) هو تسمية العمود نفسه `<entity>_metadata` في الـDB من البداية (مش alias بايثوني `key=`) — و`invoicing` كان بالفعل كذلك، فمفيش أي migration/تعديل موديل مطلوب. تفصيل كامل: `.claude/reports/invoicing-21-metadata-collision-session-log.md`. | ✅ **مُغلَق [اكتُشف الإغلاق 2026-08-29، مصدر الإصلاح الفعلي: commit `93e68ac`، 2026-08-25]** | `.claude/reports/constructor-mismatch-backlog-cleanup-session-log.md` (بند 2، مجموعة أ)؛ `.claude/reports/invoicing-21-metadata-collision-session-log.md` |
| — | **`ai-governance-audit-log-decimal-not-json-serializable`** [2026-08-25] — اكتُشف أثناء التحقق الحي لإصلاح default الـ`reset_at` (جلسة `constructor-mismatch-backlog-cleanup`، مجموعة ب): بعد تأكيد نجاح `AIGovernanceRepository.create_or_update_quota()` منفردة، تشغيل المسار الكامل عبر `AIGovernanceService.set_quota()` كشف باجًا مختلفًا تمامًا وأعمق في نفس التسلسل: `repo.create_audit_log(..., new_value=quota_data, ...)` بيحاول يكتب `quota_data` (فيها `Decimal` من `limit_value`) مباشرة لعمود `agent_audit_logs.new_value` (JSONB) — `Decimal` **مش قابل للتحويل لـJSON افتراضيًا** (`asyncpg`/`sqlalchemy` بيرفضوه بـ`TypeError: Object of type Decimal is not JSON serializable`). **الأثر:** `POST /agents/{id}/quotas` (`set_quota`) معطوب بالكامل حاليًا — حتى بعد إصلاح `reset_at` — لأن الكراش بيحصل في خطوة `create_audit_log` الملازمة لنفس الـtransaction (`begin_nested()`). مؤكَّد حيًا (تينانت1، agent throwaway، `limit_value=Decimal("1000")`). صفر لمس — يحتاج تحويل `Decimal`→`float`/`str` قبل التخزين (أو `json.dumps(default=...)` مخصَّص) في `create_audit_log` أو عند بناء `quota_data`. | 🔴 **مفتوح، أولوية عالية** — يحجب endpoint إداري حساس (تحديد حصص الوكلاء) بالكامل | `.claude/reports/constructor-mismatch-backlog-cleanup-session-log.md` (بند ب، `ai_governance.reset_at`) |
| — | **`ai-governance-usage-log-idempotency-wrong-arity`** [إعادة تأكيد 2026-08-25، اكتُشف أصلًا 2026-08-19] — تصعيد لبند رسمي في الجدول (كان موثَّقًا فقط ضمن سجل الجلسات المُقفلة أعلاه، تحت `regression-tests-backfill`). `AIGovernanceService.check_and_consume()` (`service.py:152`) بتنادي `self.repo.get_usage_log_by_idempotency(idempotency_key)` بمعامل واحد بس، لكن التوقيع الحقيقي (`repository.py:66`) `(idempotency_key: str, tenant_id: int)` — `tenant_id` إجباري بلا default. **الأثر:** أي استدعاء `check_and_consume()` بـ`idempotency_key` حقيقي (غير فاضي) يكراش فورًا بـ`TypeError` — مشروط بوجود هيدر `Idempotency-Key` من العميل، مش حتمي على كل استدعاء. **مؤكَّد لسه موجود [2026-08-25]** أثناء قراءة نفس الملف لإصلاح بند `reset_at` (مجموعة ب) — صفر لمس، برّه نطاق تلك الجلسة صراحة. | 🔴 **مفتوح، أولوية عالية** — يعطّل مسار شراء حقيقي (`service_marketplace`) كلما استُخدمت idempotency فعليًا | `tests/test_ai_governance_check_and_consume.py`؛ `.claude/reports/constructor-mismatch-backlog-cleanup-session-log.md` (بند ب) |
| — | **`invitations-customer-interaction-metadata-attribute-collision`** [2026-08-29] — اكتُشف كاكتشاف جانبي أثناء جلسة `invoicing-21-metadata-collision` (بحث عن نمط تسمية `metadata` في كل المشروع، خارج نطاق الجلسة نفسها بالكامل — صفر تحقق حي، صفر لمس). **نفس فئة العطل بالحرف** الموثَّقة سابقًا في `invoicing-invoice-model-metadata-attribute-collision` أعلاه (المُغلَق)، لكن في دومين مختلف تمامًا: موديل `CustomerInteraction` (`invitations/models.py:257-270`، جدول `crm_interactions`) عنده عمود JSONB فعلي اسمه `meta_data` (سطر 270) — **مش `metadata`**، فصفر تصادم على مستوى الموديل نفسه. لكن `invitations/service.py:606` بيقرأ `"metadata": interaction.metadata` — أي بيحاول يوصل لـattribute اسمه `metadata` حرفيًا على كائن `interaction`، وهو مش موجود كعمود، فبيرجّع بدل منه `Base.metadata` المحجوز (كائن `MetaData` بتاع SQLAlchemy) بدل القيمة الفعلية المخزَّنة في `meta_data`. **الأثر المتوقَّع (غير مؤكَّد حيًا بعد):** أي استجابة API بتمر بالسطر ده (لازم تحديد أي endpoint/دالة بتستدعي الكود المحيط بسطر 606) هترجّع كائن `MetaData` بدل بيانات الـinteraction الفعلية بدل الحقل ده — إما فشل serialization (لو الاستجابة عبر Pydantic schema بيتوقع `dict`)، أو تسريب/عرض غلط لكائن داخلي لو مفيش validation صارمة. **لم يُحدَّد بعد:** أي route/دالة تحديدًا بتستدعي هذا الكود، هل فيه Pydantic schema بيتحقق من الاستجابة (زي حالة `invoicing` اللي كانت بترجع 400)، ولا الكود ماشي مباشر كـdict بلا validation (يعني ممكن يفشل بشكل مختلف تمامًا — تسريب كائن مش ValidationError). **صفر لمس، صفر تحقق حي — يحتاج جلسة تشخيص مستقلة.** | 🔴 **مفتوح، لم يبدأ فحص** — يحتاج تحديد نطاق الاستدعاء الفعلي (مين بينادي الكود حوالين `service.py:606`) وتحقق حي قبل أي إصلاح | `.claude/reports/invoicing-21-metadata-collision-session-log.md` §5 |
| — | **`invoicing-process-overdue-invoices-missing-tenant-id-arg`** [2026-08-29] — اكتُشف كاكتشاف جانبي أثناء جلسة `invoicing-21-metadata-collision` (قراءة `router.py` بالكامل أثناء فحص كل استخدامات `InvoicingService`، خارج نطاق الجلسة نفسها — صفر تحقق حي، صفر لمس). `invoicing/router.py:330` (`POST /invoicing/admin/process-overdue`) بينادي `InvoicingService(db)` **بمعامل واحد بس**، لكن الـconstructor الفعلي (`invoicing/service.py:23`) `def __init__(self, db: AsyncSession, tenant_id: int)` — `tenant_id` **إجباري بلا default**. **الأثر المتوقَّع (غير مؤكَّد حيًا):** أي استدعاء فعلي لهذا الـendpoint (المفروض يُستدعى من Celery، حسب الوصف في الراوتر) هيرمي `TypeError: __init__() missing 1 required positional argument: 'tenant_id'` فورًا، قبل ما يوصل حتى لمنطق `process_overdue_invoices()` نفسه. **لم يُحدَّد بعد:** هل الـendpoint ده مُفعَّل فعليًا (مربوط بمهمة Celery حقيقية بتتنفذ دوريًا) ولا كود كامن زي `affiliate-distribute-commissions-celery-task-wrong-signature` (أعلاه) — لو مُفعَّل، ده معناه معالجة الفواتير المتأخرة معطَّلة بالكامل في الإنتاج. **صفر لمس، صفر تحقق حي — يحتاج جلسة تشخيص مستقلة.** | 🔴 **مفتوح، لم يبدأ فحص** — يحتاج تأكيد هل الـendpoint مُفعَّل فعليًا (Celery beat/schedule) قبل تحديد الأولوية الحقيقية | `.claude/reports/invoicing-21-metadata-collision-session-log.md` §5 |
| — | **`realestate-rent-unit-land-owner-fixture-mismatch`** [2026-08-31] — اكتُشف أثناء التحقق الحي لإغلاق باج #9 (`get_any_active_subscription`، راجع `saas-feature-flags-drift-session-log.md` §9)، **وليس ناتجًا عنه** — الباج ده كان **مقنَّعًا بالكامل** ورا #9 لحد النهارده: `test_realestate_rent_unit_saas_check_passes` كان دايمًا بيفشل عند أول سطر (`_check_saas_limits` بترمي `PermissionDeniedError: Real Estate feature is not included`)، **قبل** ما يوصل الكود أصلًا لمنطق التحقق من الملكية تحت. بعد إصلاح #9، `_check_saas_limits` بقت تعدي بنجاح لأول مرة، وكشفت فورًا: `RealEstateService.rent_unit` بترفض بـ`PermissionDeniedError("انت مش مالك الوحدة اللي عايز تأجرها")` عند `service.py:453` (`owner.id != landlord_id`). السبب المباشر: الاختبار بيستخدم `EXISTING_LAND_ASSET_ID = 1` (أصل أرض ثابت موجود مسبقًا في بيانات الديف)، لكن مالكه الفعلي المخزَّن في القاعدة **مش** نفس مستخدم `landlord` الجديد اللي الاختبار بينشئه لحظيًا — إما بيانات ديف قديمة/غلط لأصل الأرض id=1، أو الاختبار نفسه ناقص خطوة تعيين ملكية صريحة قبل استدعاء `rent_unit`. لم يُحدَّد أيهما بعد — **صفر تحقيق إضافي، صفر لمس** في جلسة `saas-feature-flags-drift`. | 🟡 **مفتوح، لم يبدأ فحص** — يحتاج تحديد مصدر عدم التطابق (بيانات ديف مقابل نقص في الاختبار) قبل أي إصلاح؛ اكتُشف بسبب **نجاح** إصلاح #9 مش نتيجة له | `.claude/reports/saas-feature-flags-drift-session-log.md` §9.3(1) |
| — | **`ai-agent-id-2-missing-seed-masks-execute-action-old-bug`** [2026-08-31] — اكتُشف أثناء نفس التحقق الحي أعلاه (باج #9)، **وليس ناتجًا عنه**. `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` مبني على `pytest.raises(TypeError, match="tenant_id")` — توقُّع صريح إن الكود يكراش بباج Backlog #16 القديم الموثَّق (`execute_agent_action` بمعامل `tenant_id=` زايد). بعد إصلاح #9، `_check_saas_limits` عدَّت بنجاح ووصل الكود فعليًا لنفس نقطة الاستدعاء — لكن الاستثناء الفعلي طلع `NotFoundError("وكيل 2 غير موجود")` من `app/domains/ai_agents/service.py:161`، مش `TypeError`. يعني **باج #16 القديم اللي الاختبار مبني على توقُّعه يبدو إنه اتصلح فعلًا** (في جلسة تانية، لم يُحدَّد أيها)، فالكود بقى يوصل أعمق ويصطدم ببيانات ديف ناقصة (`AI Agent id=2` مش موجود في القاعدة الحالية) بدل الباج القديم. تصنيف الاختبار (`_then_hits_known_bug`) بقى قديم/غير دقيق بالنسبة لحالة الكود الحالية. **صفر تحقيق إضافي، صفر لمس** في جلسة `saas-feature-flags-drift` — يحتاج إما seed لـ`AI Agent id=2`، أو تحديث توقُّع الاختبار نفسه. | 🟡 **مفتوح، لم يبدأ فحص** — اكتُشف بسبب **نجاح** إصلاح #9 مش نتيجة له؛ غير مرتبط بـSaaS إطلاقًا | `.claude/reports/saas-feature-flags-drift-session-log.md` §9.3(2) |
| — | **`frontend-missing-exports-genuinely-absent-backlog`** [2026-08-31] — من إجمالي 37 حالة `TS2307` (استيراد داخلي `@/...` مفقود بالكامل) اكتُشفت في الفحص الشامل لبند `frontend-missing-exports-multidomain-scope` (أعلاه)، **8 اتصلحوا فعليًا** (فئة "ج" — الملف موجود بمسار/اسم مختلف، راجع بند `frontend-hooks-misplaced-files-phase2-warning` وتفاصيل الإصلاح في تقرير الجلسة)، و**29 اتأكَّدوا معدومين فعلًا** بعد فحص `Glob` + قراءة أي تطابق اسم مرشَّح (رُفض تطابقان بالاسم فقط بعد قراءة المحتوى: `zamakana/CampaignCard.tsx` و`tourism-sports/TicketCard.tsx` — مكوّنات مختلفة تمامًا عن اللي محتاجه `invitations`). قائمة الـ29 منظَّمة حسب الدومين: **Components (17):** `agritech/{FarmCard,FarmZoneCard,WeatherAlertCard}`، `automation/ExecutionsPage`، `finance/{admin-mint-card,balance-card,web3-deposit-withdraw}`، `invitations/{CampaignCard,InvitationCard,InvitationStatusBadge,TicketCard,TicketStatusBadge}`، `iot/{MaintenanceLogs,ReadingsChart}`، `saas/CreatePlanModal`، `social/CreatePostModal`، `tourism-sports/TransferCard`، `ui/tooltip`، `zamakana/{PledgeCard,PledgeForm}`. **Hooks (8):** `agritech/useStats`، `commerce/useOrders`، `logistics/useStats`، `manufacturing/{usePendingMaintenance,useProductionLines,useStats}`، `transport/useDrivers`، `zamakana/usePledges`. **Utilities (2):** `hooks/use-debounce`، `lib/auth-utils` — صفر أي ملف بأي اسم قريب في المشروع كله. **Services (1):** `services/ai-governance` — يوجد `types/ai-governance.ts` فقط (الأنواع جاهزة)، صفر ملف service حتى بمسمّى `.service.ts`. كل حالة محتاجة **كتابة كود جديد بالكامل**، مش إصلاح استيراد — بعضها (`ui/tooltip`, `hooks/use-debounce`) utility عامة مفقودة تمامًا من المشروع، مش خاصة بدومين واحد. | 🔴 **مفتوح، backlog منظَّم — أساس لجلسات تصميم/تنفيذ مستقبلية لكل دومين على حدة، صفر قرار أولوية نهائي حتى الآن** | `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |

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
- **invoicing-savepoint-conflict — `commit()`-جوه-`begin_nested()` عبر `invoicing.create_invoice` في 8 دوال/4 دومينات [2026-08-18]** — ✅ **مُغلَق رسميًا** (Backlog #11b). نفس الحل الجذري (نقل `create_invoice()` لبعد `commit()`، ملفوف بـ`try/except`) طُبِّق على `tourism_sports` (3)، `realestate` (2)، `insurance` (2)، `zamakana` (1). تحقق حي كامل بـSELECT/Redis مستقل لـ4 دوال؛ مراجعة ديف/كود فقط للأربعة الباقية بسبب 3 بجات مسبقة منفصلة اتكشفت واتوثَّقت كبنود Backlog جديدة (`tourism-place-transfer-bid-player-id-user-id-conflict`, `finance-transfer-returns-transaction-object-not-tx-hash-string`, `eventbus-redis-wrapper-missing-publish`). القيد على #9 اتشال. تقرير: `.claude/reports/realestate-insurance-savepoint-fix-session-log.md`.
- **saas-control-service-get-active-subscription-fix — إكمال Backlog #9 [2026-08-18]** — ✅ **مُغلَق رسميًا**. إضافة `SaaSRepository.get_any_active_subscription`/`SaaSControlService.get_active_subscription` (اشتراك واحد شامل لكل tenant، بلا `service_id`) + اكتشاف وتصحيح باج إضافي غير موثَّق مسبقًا (`subscription.features` غير موجودة على `TenantSubscription`؛ الصحيح `subscription.plan.features`، ونوعها `List[str]` وليس `Dict[str,bool]` — يتطلب `in` مش `.get()`) عبر الثمانية دومينات، + فحص دفاعي `belt-and-suspenders` (`if not subscription.plan`). تحقق حي حقيقي (بلا `monkeypatch` على `_check_saas_limits`) أثبت نجاحها في الأربعة دوال الأصلية بلا استثناء؛ `rent_unit`/`subscribe` وصلتا لتنفيذ كامل ناجح (SELECT مستقل)؛ `buy_fractional_ownership`/`review_claim` محجوبتان ببجات مسبقة موثَّقة (#16 و#1 على التوالي — ليس `tx_hash` كما كان متوقَّعًا)، تراجع نظيف مؤكَّد بلا أثر جزئي. تقرير: `.claude/reports/saas-control-service-fix-session-log.md`.
- **eventbus-redis-wrapper-missing-publish — إصلاح مركزي واحد يغطي 22 دومين [2026-08-18]** — ✅ **مُغلَق رسميًا**. تشخيص أول (جدول أدلة: الخيار أ [إضافة `publish()` على `RedisClientWrapper`] مقابل الخيار ب [تعديل `EventBus.__init__`] — أ أُقِرَّ لأنه أقل تغييرًا/خطرًا وبلا حاجة لجعل `__init__` غير-sync) كشف تصحيحًا جوهريًا على رقم تقرير `technical-pattern-sweep`: **22 دومين مكسور فعليًا، مش 34** (10 دومينات لا تستخدم EventBus إطلاقًا؛ `finance` + `app/tasks/agritech.py` صحيحان مسبقًا بنمطين مختلفين — الأخير مكتشَف حديثًا هنا، كان مُدرَجًا خطأً ضمن قوائم الجرد الأولى). الحل: `async def publish(self, channel, message)` على `RedisClientWrapper` (`app/core/redis_client.py`)، 5 أسطر، إضافة صرفة صفر تعارض. **تحقق حي كامل حقيقي** (Redis عبر Docker، subscriber مستقل عن EventBus، إثبات استلام فعلي على القناة + تطابق `event`/`payload` 1:1، مش بس صفر استثناء) لـ3 دومينات متنوعة: `insurance`، `zamakana`، `arbitration_syndicates` (نمط بناء نصي مختلف `# type: ignore` مباشر). **فحص قرائي شامل** للـ19 الباقية أكّد أن كل الـ22 يؤولوا لنفس التعبير وقت التشغيل عبر 4 متغيرات نصية فقط (`cast(Any,...)`×17، `# type: ignore`×2، بلا تعليق×2، كود ميت في `agritech`×1) — صفر نمط بناء رابع فعلي. `communications/router.py:84` مغطى تلقائيًا بنفس الإصلاح. تقرير: `.claude/reports/eventbus-publish-fix-session-log.md`.
- **audit-log-signature-fix — توسيع توقيع `audit_log()` ليقبل `tenant_id`/`resource_id` [2026-08-18]** — ✅ **مُغلَق رسميًا** (Backlog #14). قرار تصميمي محسوم بالقراءة المباشرة لجسم `audit_log()`: الدالة logger فقط (`logging.info(json.dumps(...))`)، لا تكتب أي جدول DB — فالتوسيع اقتصر على إضافة المعاملين للتوقيع وتسجيلهما في الـJSON log entry، **صفر migration، صفر استثناء تصميمي غير قياسي**. جرد كامل (مش عيّنة) صحّح الرقم من "~112 عبر 22 ملف" إلى **95 موضع فعليًا عبر 18 ملف** (`agritech`×11، `ai_agents`×4, وموضع `commerce` الوحيد آمنون أصلًا؛ `communications/router.py` 7 من 8 فقط). اكتشاف حرج جانبي أثناء التشخيص: غياب أي `try/except` حول الاستدعاءات المكسورة + غياب exception handler عام في `main.py` يعني الباج كان بيسبب **500 حقيقي + rollback كامل للعملية الأساسية** في كل endpoint حي متأثر، مش مجرد فقدان سجل تدقيق صامت. **تحقق حي كامل** (SELECT من جلسة DB مستقلة تثبت اختفاء الـ500/rollback فعليًا، مش بس صفر استثناء) عبر 4 عيّنات تغطي كل الأنماط الموثَّقة: `insurance.create_policy`، `zamakana` (عبر repo مباشرة تفاديًا لبج #12 غير مرتبط)، `communications/router.py` `MAIL_MOVE_TO_TRASH` (النمط الناقص بلا `tenant_id`)، `realestate.rent_unit` (نمط `**{...}`). كشفت اكتشافين جانبيين وُثِّقا كبند Backlog جديد (`communications-service-get-user-missing-method`) وتحديث على #10 (affiliate/`get_by_id` في `realestate`). تقرير: `.claude/reports/audit-log-fix-session-log.md`.

- **ai-agents-execute-action-fix — إصلاح `AIAgentsService.execute_agent_action()` [2026-08-18]** — 🟡 **مُغلَق جزئيًا** (Backlog #16، الجزء ب من المرحلة 1.3). إزالة `tenant_id=` الزائدة من كل الـ19 موضع استدعاء + إضافة `idempotency_key=` الناقصة لـ11 منهم (بنمط `PREFIX-T{tenant_id}-{unique_id}`)، بعد تأكيد أن `self.tenant_id` (constructor) يُستخدم بنفس قوة `check_and_consume` (#15). **موضعان (`realestate:232`, `invitations:415`) استُثنيا عمدًا** لاكتشاف حرج جديد (`commit()` داخل `execute_agent_action` يتعارض مع `begin_nested()` المحيط بهما — نفس جذر #11a/#11b) ووُثِّقا كبند Backlog منفصل. تحقق حي كامل (docker `eppne_db`، تينانتين حقيقيين، throwaway + SELECT مستقل، 4 سيناريوهات) أثبت نجاح الاستدعاءات، صحة عزل tenant_id، فعالية كاش idempotency، وأثبت حيًا خطر تصادم `idempotency_key` عبر تينانتين لو لم يتضمن المفتاح tenant_id (عمود `AgentApprovalQueue.idempotency_key` فريد عالميًا في الـschema). اكتشاف حي جانبي أكّد أن بند #7 (`redis-client-wrapper-missing-methods`) يُسقِط الدالة بالكامل فعليًا، لا مجرد فشل تتبع تكلفة. تقرير: `.claude/reports/ai-agents-execute-action-fix-session-log.md`.

- **redis-client-wrapper-missing-methods — إضافة ست methods على `RedisClientWrapper` [2026-08-19]** — ✅ **مُغلَق رسميًا** (Backlog #7، المرحلة 1.4). تشخيص أول (قراءة كاملة للكلاس + `grep` شامل لكل استخدام فعلي عبر المشروع لكل method، بمعزل عن توثيق Redis العام) كشف: النطاق الفعلي المُعلَن (5 methods) ناقص `setnx` (موثَّقة أصلًا في بند #7 نفسه بـ`PROGRESS_LOG.md`، ولها استخدام حي مكسور في `projects/service.py:157`) — أُضيفت بموافقة مستخدم صريحة، فصار النطاق النهائي 6 methods. **قرار معماري محوري:** `pubsub()` وحدها متزامنة (بلا `async`/`await`) — أول method من نوعها في الكلاس — بدليلين حيّين مستقلين (`communications/router.py:48` endpoint حي، `event_bus.py:44`) بيستدعوها بلا `await`؛ الخمسة الباقية بنفس النمط الموحَّد القياسي. **`ltrim` أُضيفت استباقيًا** (صفر استخدام حي على الـwrapper نفسه اليوم، مؤكَّد بـ`grep` شامل) بقرار مستخدم صريح. **تصحيح/توسيع جوهري على تقدير الأثر السابق:** الوصف القديم ("يُسقط `execute_agent_action`") تبيَّن إنه ناقص — `CostTracker.record_usage()` (المستخدِمة لـ`hincrbyfloat`/`hgetall`) تُستدعى من `AIEngine.generate()` بلا `try/except`، ومؤكَّد بالقراءة المباشرة إن `app/main.py:356` (`POST /api/ai/chat`، endpoint عام مستقل عن `ai_agents`) كان متأثرًا بنفس `AttributeError` — الباج كان يُسقط **أي نجاح AI عبر المنصة بالكامل**. **تحقق حي مزدوج:** (أ) الست methods منفردة بأدوات تحقق مستقلة (HGET/LRANGE/GET/subscriber منفصل) — راجع `tests/test_redis_client_wrapper_missing_methods.py` (6 passed ×2)؛ (ب) `execute_agent_action` + `ai_engine.generate()` (`main.py:356`) **بلا أي `monkeypatch`** — ممكن لأول مرة لأن `AIEngine._call_model()` أصلًا محاكاة داخلية (اتصال الشبكة الحقيقي معلَّق في الكود)، فنتج تحقق أنظف من تحقق #16 السابق (اللي اضطر يتجاوز هذا الباج بالذات). النتيجة: `AITaskLog.task_type` رجعت `ARABIC_CHAT` مش `ERROR`، `AgentApprovalQueue` اتسجَّلت فعليًا لأول مرة، تنظيف كامل + SELECT/`redis-cli` مستقل أثبتا صفر أثر متبقٍ (بما فيها صفر محفظة يتيمة). **اكتشاف جانبي وُثِّق منفصلًا، صفر لمس:** `agritech-redis-calls-missing-await-orphaned-coroutines` (نداءات على عميل خام بلا `await` — باج مختلف جذريًا، مش method مفقودة). تقرير: `.claude/reports/redis-client-wrapper-missing-methods-session-log.md`.

- **affiliate-service-missing-methods — إضافة `register_commission`/`get_user_by_code` على `AffiliateService` [2026-08-19]** — 🟡 **مُغلَق جزئيًا** (Backlog #10، المرحلة 2). جدول جديد منفصل `affiliate_action_commissions` (migration `028`) بدل توسيع الجدول التجاري `affiliate_commissions` (NOT NULL/FK على Order — غير متوافق بنيويًا مع الـ12 موضع). `register_commission` تحل التباس نطاق users.id/affiliate_profiles.id عبر `get_or_create_profile` داخلي. إصلاح ضروري ملازم واحد (`digital_twin/service.py:82`). تحقق حي كامل + `tests/test_affiliate_service_missing_methods.py` (6 passed ×2). **مُغلَق جزئيًا لأن الـwrapper الفعلي في الـ12 دومين كان لسه معطَّل بسبب #1/#8 + اكتشاف جديد (`identity-user-referred-by-field-missing`) — الفقدان الصامت الفعلي في الإنتاج لسه قائم.** (**تحديث [2026-08-19]:** #1 اتقفل — راجع بند `user-repository-get-by-id-audit` تحت؛ الحاجب المتبقي لـ10 من الـ12 دومين بقى `identity-user-referred-by-field-missing` وحدها.) اكتشاف جانبي إضافي: `affiliate-action-commissions-not-integrated-with-balance`. تقرير: `.claude/reports/affiliate-service-missing-methods-session-log.md`.

- **user-repository-get-by-id-audit — إصلاح `UserRepository.get_by_id()` الناقص `tenant_id` عبر 15 موضعًا [2026-08-19]** — ✅ **مُغلَق رسميًا** (Backlog #1). `grep` شامل جديد بالكامل من الصفر (بلا اعتماد على القايمة التاريخية) أكَّد **15 موضعًا فعليًا عبر 13 دومين، بلا تغيير عن القايمة القديمة**. الحل: تمرير `tenant_id` المتاح أصلًا في نطاق كل دالة كمعامل ثانٍ، مع تعديل توقيع أي دالة مساعدة خاصة ما كانتش بتقبله — **صفر تغيير في منطق معالجة الأخطاء الموجود** (بما فيها قرار صريح بعدم إضافة `try/except` جديد في `social` رغم الاستدعاء جوّه `begin_nested()` بلا حماية). **تصنيف دقيق للـ15:** 4 كسور واضحة (500) — `transport` (`_get_user_by_id`)، `social` (`_get_user_email`)، `realestate` (`_get_land_owner_for_unit`)، `insurance.review_claim` (نفس البج المُوثَّق حيًا مسبقًا في `test_saas_active_subscription.py`)؛ موضع واحد **أسوأ فئة صمت** (بلا أي `logger.error` إطلاقًا) — `insurance.disburse_monthly_pensions` (دفعات معاشات حقيقية)؛ 9 مواضع صمت مُسجَّل (`_register_affiliate_commission` عبر 8 دومين + `insurance`)؛ موضع واحد يتحوَّل لـ`BusinessError` (`iot`)؛ موضع واحد **Dead code متروك عمدًا** (`logistics` — بند Backlog منفصل `logistics-affiliate-commission-dead-code-uses-broken-get-by-id`). **اكتشاف حي حاسم أثناء التحقق يربط #1 بـ#10 مباشرة:** كل الـ10 دومينات المستدعية لـ`_register_affiliate_commission` (9 + `insurance`) وصلت الآن فعليًا لـ`get_by_id` بنجاح تام، واصطدمت فورًا بطبقة `identity-user-referred-by-field-missing` (Backlog #10) — سلسلة #10 تقدَّمت طبقة كاملة لهذه الـ10 (`digital_twin`/`employment` لسه عند #8 فقط). **أثر جانبي مُعالَج في نفس الجلسة:** `tests/test_saas_active_subscription.py::test_insurance_review_claim_...` كان بيعتمد على `TypeError` بتاع #1 كدليل غير مباشر — حُدِّث ليعتمد بدلًا منه على `insurance-review-claim-issuer-entity-id-reviewer-id-conflict` (طبقة حقيقية تالية، `PermissionDeniedError`)، بدل ما يُترَك outdated؛ الملف الكامل اتشغَّل بعد التحديث (4 passed) وكل الـsuite (60 passed, 4 xfailed) للتأكد من صفر أثر جانبي غير مُعالَج. **تحقق حي كامل** لكل الـ15 موضعًا (`tenant_id` صحيح وخاطئ لكل واحد — عزل tenant فعلي مؤكَّد، مش بس اختفاء الخطأ) + regression test دائم `tests/test_user_repository_get_by_id_audit.py` (15 passed ×2، صفر تذبذب، صفر بيانات throwaway متبقية). تقرير: `.claude/reports/user-repository-get-by-id-audit-session-log.md`.

- **user-repository-get-user-audit — إصلاح `.get_user(` غير الموجودة على `UserRepository` عبر 5 مواضع [2026-08-19]** — ✅ **مُغلَق رسميًا** (Backlog #8). `grep` شامل جديد بالكامل عن `\.get_user\(` (بلا اعتماد على القايمة التاريخية "6 مواضع" كمرجع نهائي) كشف **5 مواضع فعليًا: 8 نقاط استدعاء حية + موضعان Dead code مؤكَّدان**. `employment/service.py:87` و`digital_twin/service.py:53` (كلاهما `_get_user`) — نفس منهجية Backlog #1 بالحرف (توقيع كل helper يقبل `tenant_id`، صفر `try/except` جديد)؛ كشفت التتبع الكامل لنقاط الاستدعاء (بدل الاكتفاء بسطر `.get_user(` نفسه) نقطتين خطيرتين غير موثَّقتين تاريخيًا: `interact_with_twin:180` (`digital_twin`، عبر `_get_user_email`) كانت **كسر واضح 500 داخل `begin_nested()` بلا أي `try/except`** (نفس نمط `social:678` من #1)، و`app/tasks/employment.py:308` (`pay_payroll_task`) كانت **تفشل دفع الرواتب الفعلي فعليًا وتُعاد المحاولة 3 مرات ثم تستسلم نهائيًا**. `communications/service.py:29` (`_get_user_tenant`) كانت **استثناء معماري**: الغرض من الدالة اكتشاف `tenant_id` نفسه، فلا يوجد `tenant_id` متاح في أي من نقاط الاستدعاء الثلاث (`send_notification:63`, `send_mail:144/145`) أصلًا — الحل المعتمَد (قرار مستخدم صريح، **least-privilege**): method جديدة `UserRepository.get_tenant_id_by_user_id(user_id) -> Optional[int]` ترجع `tenant_id` فقط (لا كائن `User` كامل) عبر كل الـtenants بلا فلتر. `communications/service.py:36` و`health/service.py:54` (كلاهما `_get_user_email`) **Dead code مؤكَّد، بلا لمس عمدًا** — نفس فئة `logistics-affiliate-commission-dead-code-uses-broken-get-by-id`. **اكتشاف حي حاسم يُغلق سلسلة Backlog #10 لطبقة موحَّدة كاملة عبر كل الـ12 دومين:** `_register_affiliate_commission` في `employment`/`digital_twin` وصلت الآن بنجاح لـ`get_by_id`، واصطدمت فورًا بنفس طبقة `identity-user-referred-by-field-missing` الموثَّقة مسبقًا للـ10 دومينات الأخرى — **`User.referred_by` بقى الحاجز الوحيد المتبقي لكل الـ12 دومينًا بلا استثناء، الخطوة الوحيدة الباقية لإغلاق Backlog #10 نهائيًا**. تحقق حي كامل (12 فحص throwaway، `db.rollback()`، صفر بيانات متبقية) + regression test دائم `tests/test_user_repository_get_user_audit.py` (11 passed ×2، صفر تذبذب) + suite كامل بعد الإصلاح (71 passed, 4 xfailed — 60 السابقة + 11 الجديدة، صفر أثر جانبي). تقرير: `.claude/reports/user-repository-get-user-audit-session-log.md`.

- **security-deps-unification — توحيد `app/core/security.py` + `app/api/deps.py` [2026-08-19]** — ✅ **مُغلَق رسميًا. جلسة أمنية عاجلة صريحة (أعلى أولوية من أي مسار عمل آخر جارٍ وقتها).** اكتشاف خلفية (`permissions-systems-investigation`، نفس اليوم): نسختان متوازيتان ومتباينتان فعليًا لكل دوال المصادقة/الصلاحية الأساسية، مستوردتان معًا بحرية عبر 40 ملفًا (4 منها تستوردان الاثنتين معًا في نفس الوقت) — `core/security.py` تفحص `session_version` (إبطال الجلسة عن بُعد) وتطابق `tenant_id` الصارم، `api/deps.py` **لا تفحص أيًا منهما إطلاقًا**، و`require_sector` فيها معطَّلة بالكامل (`getattr(user, "sector", None)` — حقل `sector` غير موجود على `User` model، fallback ثابت `"academy"` دائمًا لغير الإداريين). **القرار المعتمَد: الدمج لا الاختيار** — `security.py` الموقع النهائي (أساسه الأمني الصارم غير قابل للتفاوض)، أدوات `deps.py` العملية (`SimpleTenant`, `get_current_tenant`, `require_tenant_access`, `require_subscription`, `get_current_instructor_or_admin`) نُقلت فوقه، و`deps.py` أصبح re-export shim مؤقت (234→39 سطرًا، صفر منطق محلي متبقٍ، تحقق `is` صريح: كل اسم مشترك بين الملفين نفس كائن الدالة بالحرف). **الست دوال المشتركة بالاسم** (`get_current_user`, `get_current_active_user`, `get_current_superuser`, `require_sector`, `is_privacy_officer`, `require_roles`): نسخة `security.py` فازت بالكامل في الست جميعًا. **توسيع نطاق مُعتمَد أثناء التخطيط:** `get_current_user_optional` (دالة سابعة بنفس الاسم غير مذكورة صراحة، لكن بنفس فئة الثغرة — كانت تتجاوز `get_current_user` كليًا في `deps.py`، تُستخدم في 3 راوترات ضيوف) أُصلحت أيضًا: دعم `cookie_token` الكامل (فجوة كانت موجودة حتى في `security.py` الأصلية) + تمرير عبر `get_current_user` الموحَّدة. **تحقق حي عبر HTTP حقيقي فعلي (سيرفر `uvicorn` حقيقي + `curl` عبر الشبكة، لا استدعاء Python مباشر):** (1) `session_version` — توكن صالح شكليًا لكن جلسته أُبطلت عبر `POST /api/identity/revoke-all` رُفض فورًا بعدها بنفس التوكن القديم من `GET /api/communications/notifications/me` (كانت تعتمد على `deps.get_current_active_user` الأضعف): `{"detail":"Session has been revoked","code":"AuthenticationError"}` **HTTP 401** (بعد أن كان `200` قبل الإبطال) — **الإثبات المباشر لإغلاق الثغرة الأمنية الأصلية لهذه الجلسة كلها**. (2) `require_sector` — حساب غير إداري بتوكنين بقيم `sector` صريحة مختلفة: توكن `sector=communications` على راوتر `communications` → `200`؛ نفس التوكن على راوتر `academy` → `403` **"قطاعك الحالي: communications"** (القيمة الحقيقية من التوكن عبر `ContextVar`، لا fallback ثابت)؛ توكن `sector=academy` على `academy` → `200`. مستخدمان تجريبيان حُذفا من القاعدة فور التحقق (`DELETED_ROWS=2`)، السيرفر أُوقف. **الأربعة ملفات المزدوجة الاستيراد** (`communications/router.py`, `identity/router.py`, `privacy/router.py`, `tests/test_identity_router_protection.py`) رُوجعت فعليًا بعد الدمج — صفر تعارض، صفر استيراد دائري، كل الأسماء المشترَكة نفس الكائن بالحرف. `tests/test_identity_router_protection.py` أُعيد كتابته (كان سيفشل حتمًا بعد الدمج — كان يفترض أن نسخة `deps.py` كائن منفصل فعليًا) + 8 اختبارات حية جديدة (صالح Header/Cookie، منتهي، مُبطَل `session_version`، `tenant` مزوَّر). `tests/test_security_deps_unification.py` (ملف جديد، 4 اختبارات) يوفّر النسخة الدائمة القابلة لإعادة التشغيل لسيناريو `require_sector` (تطابق/عدم تطابق/بلا `sector` claim/تخطي `SUPER_ADMIN`) عبر استدعاء حقيقي لنفس الدوال. `pytest` كامل نهائي: **84 passed, 4 xfailed** (71 قبل الجلسة + 13 اختبار جديد صافي، صفر فشل جديد عبر كل الـ40 ملفًا). **خارج النطاق صراحة (بقرار مسبق):** حذف `deps.py` نهائيًا وتحديث الـ40 ملف (جلسة تنظيف منفصلة لاحقة)؛ ثغرة `sovereign_entities` المنفصلة (باج `SimpleTenant`)؛ تصميم نظام الصلاحيات الجديد (يُستأنف الآن). تقرير كامل بكل قرار دمج دالة-بدالة + التحقق الحي الكامل: `.claude/reports/security-deps-unification-session-log.md`.

- **entity-membership-foundation — بناء الأساس العام لنظام `EntityMembership` (الجلسة 1 من 2، مسار الصلاحيات الجديد) [2026-08-20]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل.** أول جلسة تنفيذية فعلية (كود + migration) بعد أربعة مستندات رؤية/تصميم متتالية بلا كود (`multilevel-referral-system-design-vision.md` ← `entity-permissions-and-lifecycle-vision.md` ← `entity-membership-system-vision.md` ← `entity-membership-technical-design.md`، كلها [2026-08-19])، مستأنَفة بعد تعليقها مؤقتًا لصالح `security-deps-unification` الأمنية العاجلة. **ثلاثة جداول جديدة كليًا في `app/core/`** (`app/core/models.py`): `EntityMembership` (`tenant_id` FK `academy_tenants.id`، `entity_type`/`entity_id` Polymorphic بلا FK، `user_id` FK `users.id`، `role` Enum `EntityMembershipRole` منفصل عمدًا عن `sovereign_entities.EntityRole`، `UNIQUE(entity_type, entity_id, user_id)`، فهرسا `(entity_type, entity_id)`/`(user_id, tenant_id)`)؛ `EntityPermissionOverride` (`permission`, `granted` `NOT NULL`, `granted_by` FK `RESTRICT`, `reason`، `UNIQUE(entity_type, entity_id, user_id, permission)` — صف state يُحدَّث في مكانه، لا سجل تاريخي)؛ `PermissionAuditLog` (`scope` `PLATFORM`/`ENTITY` موحَّد، `action` `GRANT`/`REVOKE`، `performed_by` FK `RESTRICT`، فهارس منفصلة على `performed_by`/`target_user_id`/`performed_at`). **اكتشاف جانبي مُصحَّح بموافقة صريحة:** المستند التقني يكتب حرفيًا `tenant_id ... FK → tenants.id` — لا يوجد جدول `tenants` في المشروع فعليًا؛ استُخدم `academy_tenants.id` (الجدول الحقيقي، نفس ما تستخدمه `sovereign_entities`/`affiliate_action_commissions` بالفعل) تطبيقًا لنية المستند لا لنصه الحرفي. **Migration `029_create_entity_membership_foundation`** (`down_revision='028_create_affiliate_action_commissions'`)، طُبِّقت على القاعدة الحية وتحقَّق منها `\d` مباشرةً مطابقة تامة للـschema الموثَّق؛ تعديل مصاحب وحيد على ملف موجود: `migrations/env.py` (إضافة `from app.core.models import *`). **منطق CRUD — `app/core/entity_membership_repository.py`** (`EntityMembershipRepository`: `add_member`/`update_member_role`/`remove_member`/`get_member`/`list_members`/`list_entities_for_user`، زائد `_upsert_override`/`has_permission_override`/`_insert_audit_row` الداخلية) **و`app/core/entity_membership_service.py`** (`EntityMembershipService`: تمرير مباشر لعمليات العضوية، زائد `grant_permission`/`revoke_permission` — المسار الوحيد لتعديل `entity_permission_overrides`، كل واحدة تستدعي upsert الـoverride + insert سطر audit في نفس الـtransaction وcommit واحد، يضمن تسجيل `permission_audit_log` تلقائيًا بلا مسار يسمح بتخطيه — و`check_permission`). **`EntityMembershipService` لا تستورد أي شيء من `sovereign_entities` أو أي دومين وظيفي آخر** (تحقق مباشر)، وdocstring صريح يوضح أن فحص التفويض مسؤولية الدومين المستدعي وقت الدمج في الجلسة 2. **تحقق حي مزدوج:** (أ) سكريبت يدوي عبر بيانات throwaway (`entity_type="_TEST_ENTITY"`) مع تحقق `psql` مستقل تمامًا بعد كل خطوة — القيد الفريد فشل كما يجب، upsert الـoverride أنتج نفس الصف دائمًا (`COUNT`=1)، وصفَّا audit بالضبط (`GRANT` ثم `REVOKE`) بلا استدعاء منفصل من طرف السكريبت؛ (ب) **regression test دائم** `tests/test_entity_membership_foundation.py` (8 اختبارات) + README مخصص — اكتشاف جانبي أثناء الكتابة (`IntegrityError` بيسمّم أي جلسة تحصل فيها، نفس نمط موثَّق مسبقًا في `test_ai_agents_execute_action.py`) مُصحَّح بعزل المحاولة المتوقَّع فشلها في جلسة `AsyncSessionLocal` مستقلة؛ **8 passed ×2 تشغيلتان متتاليتان، صفر تذبذب**، صفر بيانات throwaway متبقية (تحقق `psql` مستقل). **✅ تأكيد صريح: صفر لمس على `sovereign_entities` في هذه الجلسة** — لا الموديلات (`EntityRole`, `EntityRepresentative`, `can_sign_contracts`)، لا `service.py`، لا الراوتر (`git status`: 4 ملفات جديدة + تعديل سطر واحد في `migrations/env.py` فقط). **الجلسة 2 (الربط الفعلي + حذف الموديلات القديمة) لم تبدأ بعد.** تقرير كامل: `.claude/reports/entity-membership-foundation-session-log.md`.

- **academy-live-testing — اختبار حي لقطاع الأكاديمية على سيرفر حقيقي [2026-08-20]** — 🔵 **جلسة تحقق فقط (صفر إصلاح كود/migration، كما طُلب صراحة)**، بناءً على `academy-structural-completeness-audit-session-log.md` (جرد سابق نفس اليوم). شغّلت `uvicorn` حقيقي (كان متوقفًا) + Postgres/Redis عبر docker، وجهّزت بيانات throwaway حقيقية (تينانتين `academy_tenants.id=1/16`، 6 مستخدمين `TEST_*`، كورسات/org_entities مُدرَجة عبر SQL مباشر بعد أن تبيَّن أن مسارات الإنشاء عبر الـAPI نفسها مكسورة — انظر أدناه). **§1 (الكسور الثلاثة المؤكَّدة بالجرد):** `POST /academy/enroll` لكورس مدفوع (§1.3) و`POST /employment/applications` بشهادة مطلوبة (§1.2) تأكَّدا **مطابقين تمامًا** لتوقع الجرد (200 PENDING عالق ثم 403 "مسجل بالفعل"؛ `AttributeError: get_user_certificates` → 500). `GET /academy/instructor/stats` (§1.1) تأكَّد **مكسورًا دائمًا كما توقَّع الجرد لكن بسبب مختلف وأعمق**: 500 (`UndefinedColumnError: academy_instructors.tenant_id does not exist` — انحراف Model↔Migration حقيقي، العطل يحدث قبل الوصول لمنطق الـ404 المفترَض أصلًا). **§2 (ثغرتا عزل المستأجرين):** الاثنتان **مؤكَّدتان حيًا بالكامل** — كتابة `POST /nodes/{id}/materials` عبر مستأجرين نجحت 201، وقراءة `GET /nodes/{id}/materials` كشفت `file_url` كاملًا لمستخدم في مستأجر آخر غير مسجَّل بأي كورس هناك (200). **§3/§4:** عيّنة "الميزات الميتة" (`instructor/stats`، `nodes/{id}/quiz` كتابة-فقط-بلا-قراءة) مؤكَّدة حيًا؛ الشهادات/الشارات (Frontend) **لم تُختبَر حيًا في متصفح** — `npm run dev` (Next.js/Turbopack) عُلِّق أكثر من دقيقتين على تجميع أول صفحة، متسق مع باج `lit`/`@reown/appkit-ui` الموثَّق مسبقًا في `SKILL.md` (غير مرتبط بالأكاديمية) — اكتفيت بتحقق ساكن (صفر تطابق لـ`getCertificates`/`getMyCertificates`/`getBadges` في `academy.service.ts`، يطابق الجرد). المسار الذهبي (§4: تسجيل مجاني→مهمة→تصحيح→لوحة متصدرين) **يعمل بالكامل، صفر انحراف**. **أربعة اكتشافات جديدة حرجة خارج نطاق الجرد الأصلي، غير مذكورة فيه إطلاقًا:** (1) 🔴 **`require_sector()` (`main.py:300-306`) يحظر كل مستخدم بدور غير `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` من كل الـ30 دومين في `routers_config` بالكامل — منصة كاملة، ليس الأكاديمية فقط** — لأن `_issue_tokens` (`identity/service.py:115-124`، مصدر كل توكن حقيقي عبر `/identity/login`) لا يضع `sector` claim إطلاقًا؛ **هذا لا يتعارض مع تحقق `require_sector` الحي الناجح في جلسة `security-deps-unification` بالأمس** — ذاك التحقق استخدم توكنات بـ`sector` صريح مُدرَج يدويًا لاختبار منطق الفحص نفسه بمعزل، ولم يختبر مسار الإصدار الحقيقي عبر تسجيل الدخول الفعلي؛ **الفجوة بين الاثنين لم تُكتشف قبل اليوم**؛ الدليل الظرفي الداعم: كل حسابات الاختبار `p_ctor_*` المتبقية من جلسات سابقة كانت جميعًا بلا استثناء `SUPER_ADMIN`. (2) 🔴 `require_subscription()` (`core/security.py:317`) يستدعي `check_and_enforce_access()` بمعاملين موضعيين لكن توقيعها الفعلي يقبل واحدًا فقط → `TypeError`→500 من أي حساب حتى `SUPER_ADMIN`؛ يجعل `POST /academy/courses`/`bootcamps` غير قابلين للاستخدام إطلاقًا. (3) 🔴 `POST /academy/entities` يفشل 500 دائمًا (`create_org_entity()` لا تقبل `tenant_id` رغم كونه حقلًا مطلوبًا في الـschema) — بما أن الـDB كانت فارغة تمامًا من أي `organization_entities` قبل الجلسة، **لا يمكن حاليًا بناء أي هيكل أكاديمية من الصفر عبر الـAPI وحده**. (4) 🟠 `employment.create_job` يسقط 500 (`bleach.clean(None)`) لأي طلب بلا حقل `description` رغم كونه `Optional` شرعيًا بالـschema. زائد تأكيد إضافي حي (SQL مباشر مرفوض): enum `SystemRole` في الـDB لا يحتوي `INSTRUCTOR` إطلاقًا. **تنظيف:** بيانات throwaway (تينانت B id=16، 6 مستخدمين، 3 كورسات، org_entities، إلخ) أُبقيت موسومة `TEST_*` كما سُمح بالتعليمات؛ التعديل الوحيد على إعداد مشترك (إضافة `hr_management` مؤقتًا لخطة اشتراك `id=2` لتجاوز فحص feature-flag أثناء اختبار §1.2) **أُرجِع لحالته الأصلية فور الانتهاء**؛ `next dev` أُوقف، `uvicorn` تُرك شغالًا. **الخطوة التالية (غير منفَّذة في هذه الجلسة):** تقرير أولويات موحَّد يدمج الجرد + هذا التحقق الحي + الاكتشافات الجديدة الأربعة، قبل أي قرار إصلاح. تقرير كامل بكل استجابة HTTP (status+body) وTraceback: `.claude/reports/academy-live-testing-session-log.md`.

- **require-sector-removal-subscription-fix — إلغاء `require_sector` بالكامل + إصلاح `require_subscription` + whitelist مبدئي [2026-08-20]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل.** **يُلغي صراحة** حلاً كان مخططًا في جلسة سابقة (إضافة `sector` claim للتوكن) بعد نقاش استراتيجي مباشر مع المستخدم — تبيَّن أن نموذج المنصة أصلًا لا يدعم "sector واحد ثابت لكل مستخدم"، وأن `saas_tenant_subscriptions` (تينانت واحد، عدة اشتراكات دومين مستقلة) هو التمثيل الصحيح. **القرار: إلغاء `require_sector()` من `main.py:300-306` بالكامل** (الدالة نفسها باقية في `core/security.py`، معلَّمة `DEPRECATED` فقط، لا تزال تُستدعى مباشرة من `tests/test_security_deps_unification.py`) — الفحص الوحيد المتبقي لوصول أي دومين هو `require_subscription`. **السبب الجذري لباج `require_subscription` (`core/security.py:317`) حُدِّد بدقة قبل التعديل:** الطرف الخاطئ هو الاستدعاء (`check_and_enforce_access(current_user.tenant_id, service_code)` بمعامل زائد)، وليس توقيع `SaaSControlService.check_and_enforce_access(self, service_code)` (تستخدم `self.tenant_id` داخليًا بالفعل) — إصلاح سطر واحد. **Whitelist جديد `SUBSCRIPTION_CHECK_EXEMPT_SERVICES = {"identity", "saas"}`** فوق `require_subscription` مباشرة، بتعليق صريح أنه **قرار مبدئي قابل للتغيير**، بتخطٍّ حقيقي (صفر استعلام DB) لا مجرد نجاح دائم. **تحقق حي كامل** (uvicorn حقيقي + curl، بعد إيقاف نسختين قديمتين بواقيتين من الجلسة السابقة بموافقة صريحة) للسيناريوهات الستة المطلوبة: رفض `403` صحيح (رسالة اشتراك، صفر ذكر sector) لمستخدم `ADMIN` عادي بلا اشتراك، نجاح بعد تفعيل اشتراك throwaway لدومين، نجاح مستقل لدومين ثانٍ مختلف بعد اشتراك ثانٍ لنفس التينانت (يثبت تعدد الاشتراكات فعليًا)، `identity`/`saas` ناجحان دائمًا لمستخدم بلا أي اشتراك (مؤكَّد HTTP **و** بفحص مباشر للـwhitelist نفسها بـ`db=None` — نجاح بلا لمس DB مقابل `AttributeError` فوري لكود غير مُدرَج، إثبات تخطٍّ حقيقي)، وصفر لمس على `sovereign_entities`. تأكيد إضافي: `GET /commerce/products` (دومين بلا `require_subscription` إطلاقًا، كان محجوبًا فقط بـ`require_sector`) نجح لمستخدم بلا أي اشتراك — يثبت الإلغاء طُبِّق فعليًا على الـ30 دومين لا فقط `academy`/`affiliate`. **اكتشاف جانبي جديد كليًا وُثِّق منفصلًا، صفر لمس:** `academy-create-course-instructor-id-duplicate-kwarg` (فوق) — أول طلب حقيقي وصل لمنطق إنشاء الكورس بعد إصلاح البوابتين اصطدم بباج `TypeError` مختلف تمامًا عن `create_org_entity` الموثَّق سابقًا. بيانات throwaway (تينانت B id=16، مستخدم 774 مُرجَّع لـ`ADMIN` عادي، خدمات/خطط/اشتراكات SaaS جديدة موسومة `TEST_`/`test_reqsector_`) مُبقاة، لم تُحذف. تقرير كامل بجدول قبل/بعد للستة سيناريوهات: `.claude/reports/require-sector-removal-subscription-fix-session-log.md`.

- **academy-priority-fix — إصلاح مركَّز لستة بنود أولوية في قطاع الأكاديمية (4 إصلاح مستقل + ثغرتا عزل مستأجرين) [2026-08-20]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل للستة بنود.** بناءً على `academy-structural-completeness-audit`/`academy-live-testing` (نفس اليوم) + تقرير أولويات مرفق مع تعليمات الجلسة. **خطة كاملة (diff حرفي لكل بند) عُرضت في `plan mode` ووُوفق عليها صراحة قبل أي تعديل**، بعد أن طلب المستخدم رؤية الـdiff الكامل لـ`service.py` في الشات (لا المقطع في المحرر فقط) قبل الموافقة — نُفِّذ الطلب حرفيًا. **الستة إصلاحات:** (1.1) `academy/service.py:112` `create_course` — استبعاد `instructor_id` من `data` قبل `**kwargs`، استخدام المعامل الصريح (من `current_user.id`) حصريًا؛ يغلق `academy-create-course-instructor-id-duplicate-kwarg` (فوق). (1.2) `academy/router.py:87` `create_org_entity` — استبعاد `tenant_id` من جسم الطلب في الراوتر (الخدمة نفسها صحيحة أصلًا، تستخدم `self.tenant_id`). (1.3) `employment/service.py:164` `create_job` — تطبيق نفس نمط `location` المجاور على `description` (`bleach.clean(...) if data.get("description") else None`) لمنع `bleach.clean(None)`. (1.4) `academy/router.py:272` `/enroll` — فحص `is_free`/`price_mrusdt` قبل الاستدعاء، رفض `400` صريح لكورس مدفوع بدل تسجيل `PENDING` عالق (يوجّه لمسار `/store/courses/{id}/enroll` الصحيح). (2.1) `academy/service.py` (`create_live_session`/`create_node_material`/`create_quiz`) — إضافة تحقق ملكية عبر `get_course(node.course_id, self.tenant_id)` بعد `get_node()`، بنفس نمط `update_node`/`delete_node` الصحيح الموجود مسبقًا في نفس الملف (فحصت كل نقاط استدعاء `get_node()` أولًا قبل القرار، تفاديًا لكسر الاستخدامين الآخرين). (2.2) `academy/service.py:215` `get_node_materials` — نفس نمط 2.1 (عزل مستأجر فقط، بلا تحقق تسجيل بالكورس — قرار منتجي منفصل مؤجَّل عمدًا). **تحقق حي كامل عبر `uvicorn` حقيقي + `curl`** (بعد تشغيله، كان متوقفًا) للستة بنود بالكامل: محاولة انتحال `instructor_id`/`tenant_id` في الجسم تجوهلت فعليًا (القيمة المخزَّنة = المستخدم/التينانت الحقيقي من التوكن، لا الجسم)، `description` غائبة لا تكسر إنشاء الوظيفة، كورس مدفوع يُرفض `400` بلا صف `PENDING` جديد (تأكيد SQL) بينما كورس مجاني يعمل كالمعتاد، كتابة/قراءة `node_id` عبر مستأجر آخر ترفض `404` بينما نفس العملية على `node_id` من نفس المستأجر تنجح — **كل الاستخدامات الشرعية المقابلة اتحقَّق منها بلا كسر بالتوازي**. **اكتشاف جديد أثناء التحقق الحي لـ1.1، خارج الستة بنود صراحة، صفر إصلاح:** `academy_courses.instructor_id` FK على `academy_instructors.id` وليس `users.id` — **نفس المشكلة الجذرية الموثَّقة مسبقًا في الجرد الأصلي (`academy-structural-completeness-audit-session-log.md` §2.أ: انفصال مفهوم "مدرّب" بنيويًا عن `User`/الأدوار)، بزاوية جديدة فقط (تمتد للـschema/FK نفسه، لا فقط الأدوار)** — أُضيفت ملاحظة تحديث على ذلك القسم مباشرة بدل فتح بند backlog منفصل. للتحقق من إصلاح 1.1 فقط أُدرج صف throwaway واحد يدويًا (بيانات فقط). **بيانات throwaway:** أُعيد استخدام حسابات/تينانتات/كورسات متبقية من `academy-live-testing` (تينانت B `id=16`، حسابات `TEST_*` 772-777، `TEST_instr_b` رُقِّي لـ`SUPER_ADMIN`)، زائد كيانات جديدة موسومة `TEST_*` (كورس، org_entity، وظيفتان، تسجيل، مادة). **الوحيد الذي أُرجِع لحالته الأصلية:** `saas_service_plans.id=48.features` (أُضيفت `hr_management` مؤقتًا لاختبار 1.3، أُزيلت فور الانتهاء). تقرير كامل بجدول قبل/بعد وtraceback لكل بند: `.claude/reports/academy-priority-fix-session-log.md`.

- **academy-product-decisions-implementation — تنفيذ القرارات المنتجية الأربعة لقطاع الأكاديمية [2026-08-21]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل للأربعة بنود، 4 commits منفصلة** (`71a5c5a` Quizzes، `d5f843a` Enrollment Cancellation، `7f22911` `is_free_preview`، `a129d9e` توثيق Payment Installments). بناءً على `academy-product-decisions.md` (القرارات الأربعة المعتمَدة بعد نقاش سابق). **توقفان مطلوبان صراحة نُفِّذا قبل الكود:** (1) أسئلة `SHORT_ANSWER` موجودة فعليًا في `QuizQuestion.type` — قرار مستخدم صريح: تصحيح جزئي فوري (MCQ/TRUE_FALSE تلقائي، SHORT_ANSWER صفر تلقائي، `status="PARTIALLY_GRADED"` لا `"GRADED"` لو وُجد سؤال نصي — تصحيح على القرار الأولي أُدخل أثناء المراجعة الحية للـdiff بعد ملاحظة المستخدم أن `"GRADED"` الدائمة كانت مضلِّلة). (2) لا يوجد تتبع حقيقي لفتح المحتوى — قرار مستخدم صريح: استخدام `Enrollment.progress_percentage` الذاتي التبليغ كبديل مؤقت لحساب شرط "7%" (ضعف تتبع التقدم موثَّق داخل تقرير الجلسة نفسه، لم يُفتح له بند backlog منفصل بقرار المستخدم). **⚠️ ملاحظة تسلسل مهمة بين البندين 1 و3:** commit البند 1 (`71a5c5a`) وحده **لم يكن يحمي قراءة الاختبار (`GET /nodes/{id}/quiz`) من مستخدم غير مسجَّل** — الحماية اكتملت فقط بعد commit البند 3 (`7f22911`) في نفس الجلسة، اللي طبَّق بوابة `is_free_preview`/التسجيل على الثلاثة مسارات معًا (`materials`, `quiz`, `course nodes`). موثَّق بوضوح في تقرير الجلسة (جدولا الاختبار الحي للبندين 1 و3). **اكتشاف إضافي في البند 3 خارج نص التعليمات:** `GET /courses/{course_id}/nodes` كانت تُعيد `content_url` لكل عُقدة بلا أي فحص — قرار مُعتمَد (تصفير `content_url` للعقد غير المجانية بدل حذف العقدة من القائمة) عُرض كخطة أولًا ثم كـdiff حرفي في الشات، ووُوفق عليه صراحة مرتين قبل التنفيذ. **4 commits، كل واحد بموافقة صريحة على الـdiff الكامل في الشات قبل الكتابة** (نفس منهجية `academy-priority-fix`). بيانات throwaway فقط طوال الجلسة (6 كورسات جديدة، 6 تسجيلات، عُقدة معاينة مجانية واحدة، اشتراك `TRIAL` واحد تحوَّل `CANCELLED` كنتيجة اختبار متوقَّعة) — صفر بيانات مشتركة/حقيقية لُمست. تقرير كامل بجداول الاختبار الحي الأربعة: `.claude/reports/academy-product-decisions-implementation-session-log.md`.

- **sovereign-entities-idor-fix — حماية الأربعة endpoints المعلَّقة منذ 2026-08-13 (`list_entities`, `get_entity`, `list_templates`, `list_components`) [2026-08-24]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل.** يحسم القرار المنتجي/الأمني اللي كان معلَّقًا صراحة في `.claude/plans/critical-finding-xtenant-systemic.md` (وتقرير `CRITICAL-sovereign-entities-unauthenticated-endpoints.md`) منذ جلسة `simpletenant-fix`. **القرار المعتمَد:** الأربعة يتحولوا لمحمية بـ`current_user: User = Depends(get_current_active_user)` إجباري + `tenant_id = cast(int, current_user.tenant_id)` — نفس النمط الميكانيكي المطبَّق بالفعل على 17/22 موضع آخر في نفس الملف (`academy`/`commerce`/`saas` أيضًا)، بلا أي لمس على `service.py`/`repository.py`. **🔴🔴🔴 اكتشاف حرج أثناء التحقق قبل الإصلاح: الخطورة كانت أسوأ مما وثَّقه التقرير الأصلي.** جلسة منفصلة تمامًا (`require-sector-removal-subscription-fix`, 2026-08-20) أزالت `require_sector` من `main.py` (قرار سليم، غير متعلق بهذا الملف) بلا إعادة تقييم أثرها على الأربعة endpoints دول تحديدًا — من 2026-08-20 حتى هذا الإصلاح، كانت الأربعة **بلا أي حاجز مصادقة إطلاقًا** (مش بس مفتوحة لـ`SUPER_ADMIN` كما كان موثَّقًا)، مؤكَّد حيًا (`curl` بلا Authorization header: `list_entities`/`get_entity` → `500` وصلا فعليًا لمنطق التطبيق، بينما endpoint محمي صح بنفس الملف رفض بـ`401`). التسريب كان لسه "كامنًا" (كراش `SimpleTenant`)، لكن أي إصلاح سطحي للكراش كان هيفتحه لأي زائر مجهول تمامًا. **بعد الإصلاح: نفس الطلبات المجهولة ترجع `401` في الأربعة كلهم.** **تحقق حي كامل** (توكنات `SUPER_ADMIN` حقيقية عبر `/identity/login`، `academy_tenants.id=1`/`16`، هيدر `X-Tenant-ID` مزوَّر في الاتجاهين): `list_entities`/`get_entity` — 9 سيناريوهات حاسمة، الهيدر بلا أي تأثير في الاتجاهين (مؤكَّد على entity throwaway جديد تحت تينانت16 + 4 entities موجودة تحت تينانت1). **اكتشاف جانبي غير متوقَّع أثناء التحقق:** entity قديمة (`id=3`, من جلسة `constructor-mismatch` سابقة) كانت ناقصة أعمدة ORM-default (`primary_color`/`secondary_color`/`treasury_balance_mrusdt`/`kyb_status` جميعًا `NULL` فعليًا رغم `default=` على مستوى الموديل) — كانت بتُسقط `list_entities` بالكامل لتينانت1 بـ`ResponseValidationError`/`ValidationError`؛ صُحِّحت بيانات هذا الصف تحديدًا (تعبئة القيم بنفس الـdefault المُعرَّف في الموديل، صفر تغيير كود) لإتمام التحقق الحي — **نفس فئة "NULL defaults" الموثَّقة سابقًا في Phase 16، تستاهل جرد منهجي مستقل مستقبلي عبر باقي الجداول لو تكررت**. `list_templates`/`list_components`: تطبيق الإصلاح الميكانيكي نفسه على التوقيع (بلا فرق في التكلفة)، لكن **التحقق الحي جزئي على مستوى `service` مباشرة فقط** (بقرار مستخدم صريح) — لأن **باج ترتيب routes منفصل تمامًا وخارج النطاق** (`GET /{entity_id}` مُسجَّلة قبل `/templates`/`/components` في نفس الملف، فأي طلب حقيقي للمسارين يقع تحت نمط `/{entity_id}` [int-typed] أولًا ويُرفض بـ`422`/`401` قبل ما يوصل للهاندلر الحقيقي إطلاقًا) — **موثَّق كبند Backlog جديد بأولوية عالية** (`sovereign-entities-templates-components-routes-shadowed-by-entity-id`): المسارين معطَّلين فعليًا في الإنتاج اليوم، بمعزل تام عن IDOR. تحديث تحذير `critical-finding-xtenant-systemic.md` والتقرير `CRITICAL-...md` (كلاهما) بدليل الـ`curl` الكامل (401 مقابل 500) — منفَّذ ضمن نفس الجلسة. تنظيف كامل لكل بيانات throwaway (entity/templates/components جديدة) + `SELECT COUNT` مستقل يؤكد صفر، سكريبت التحقق المؤقت اتحذف. تقرير كامل: `.claude/reports/sovereign-entities-idor-fix-session-log.md`.

- **ai-agents-idor-fix — حماية الـ13 endpoint في `ai_agents/router.py` (مصدر `tenant_id` من هيدر `X-Tenant-ID` بدل `current_user.tenant_id`) [2026-08-24]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا بالكامل.** استكمال مباشر لنفس مسار `academy`/`commerce`/`saas`/`sovereign_entities` (نفس اليوم) — نفس النمط الميكانيكي (`tenant: AcademyTenant = Depends(get_current_tenant)` → `tenant_id = cast(int, current_user.tenant_id)`)، بلا لمس `service.py`/`repository.py`/`schemas.py`. **بعكس `sovereign_entities`، كل الـ13 endpoint هنا كانوا عندهم `current_user` صريح من الأساس — لا يوجد zero-auth إطلاقًا، المشكلة محصورة في مصدر `tenant_id`.** **🔴🔴🔴 اكتشاف حرج أثناء التحقق الحي "قبل": exploit chain كامل يتجاوز صمام الأمان البشري (human-in-the-loop)، أخطر من تصنيف IDOR القياسي المذكور أصلًا في `critical-finding-xtenant-systemic.md` (الصف #4).** مؤكَّد حيًا (مستخدمان throwaway حقيقيان، تينانت1/تينانت16، **بلا أي تزوير هيدر** — القيمة الافتراضية `X-Tenant-ID=1` كفت وحدها): مستخدم تينانت16 (1) نفّذ فعليًا إجراء AI حقيقي على agent يخص تينانت1 (تكلفة حقيقية اتحسبت على فاتورة الضحية)، (2) وافق بنفسه رسميًا على نفس الإجراء عبر `resolve_approval` (تجاوز كامل لصمام موافقة تينانت1)، (3) `list_approvals` سرَّبت approval كامل يخص مستخدم شرعي آخر تمامًا (صفر فلتر ملكية). إضافة: `update_agent_status` عطَّلت (`SUSPENDED`) agent تينانت1 فعليًا من مستخدم تينانت16. **تحقق حي "بعد" بمعيار `finance.transfer` الصارم (SELECT مستقل قبل/بعد)** على الأربعة دول — الأربعة أُغلقوا بالكامل (`404`/`[]`، صفوف DB بلا أي تغيير)، + تحقق حي إضافي (مش grep فقط) على `get_agent_analytics`/`get_agent_status`/`create_agent`/**`delete_agent`** (الأخطر، تدميري وغير قابل للتراجع، **لم يُختبَر حيًا في أي جلسة سابقة على الإطلاق** — مؤكَّد الآن: محجوب تمامًا cross-tenant، ويعمل صح لصاحبه الشرعي). Sanity كامل: المسار الشرعي داخل نفس التينانت لم يتأثر إطلاقًا. **باج pre-existing منفصل موثَّق فقط، صفر إصلاح:** `get_ai_usage` يكراش (`AttributeError: 'TenantSubscription' object has no attribute 'features'`) — يمنع تحقق حي حاسم لهذا الـendpoint تحديدًا بغض النظر عن إصلاح `tenant_id`، بقرار المستخدم الصريح يُترك Backlog. تحديث بارز `🔴🔴🔴` أُضيف لـ`critical-finding-xtenant-systemic.md` (exploit chain الكامل + أدلة قبل/بعد)، بتوجيه صريح من المستخدم لتمييزه عن تصنيف IDOR القياسي. تنظيف كامل لكل بيانات throwaway (agents/task logs/approvals، جلستي "قبل"/"بعد") + `SELECT COUNT` مستقل يؤكد صفر. تقرير كامل: `.claude/reports/ai-agents-idor-fix-session-log.md`.

- **backend-fixes-post-url-prefix-audit — إغلاق 6 أعطال backend اكتُشفت أثناء التحقق الحي لبند #31 [2026-08-26]** — ✅ **مُغلَق رسميًا، تحقق حي 6/6.** `translation` (alias مضلِّل لـ`redis_client`)، `command.get_dashboard` (ORM object بدل dict)، `employment.jobs/open` و`insurance.policies` و`invitations` (list/#id) (حقول `None` تخالف schema غير-`Optional`) — كلها `500`→`200`. **+ اكتشاف/إصلاح IDOR حقيقي إضافي غير مخطَّط** في `arbitration_syndicates.list_user_cases` (فلترة تينانت كانت مفقودة بالكامل، مش مجرد `TypeError` سطحي) — راجع `.claude/plans/critical-finding-xtenant-systemic.md` (تحديث 2026-08-26). بنود Backlog #25/#27/#46/#47 حُدِّثت لـ"مُصلَح". تقرير كامل: `.claude/reports/frontend-url-prefix-comprehensive-audit-session-log.md` §16-21.

  **⚠️ ملاحظة عملية (process gap) اكتُشفت [2026-08-26] أثناء مقارنة هذه الجلسة بجلسة سابقة بيوم واحد
  فقط — درس لازم يُتفادى مستقبلًا، مش مجرد تفصيلة توثيقية:** commit `55032eb`
  ("fix(constructor-mismatch): resolve 11 backlog items — kwarg drops to schema migrations"،
  2026-08-25 11:16، جلسة `constructor-mismatch-backlog-cleanup`) صلَّح وتحقَّق حيًا (بمنهجية صارمة —
  throwaway data + `SELECT` مستقل لكل بند تقريبًا) من **7 بنود مرقّمة** في
  `constructor-mismatch-backlog-classification.md` (#2 ×2 موضع، #12، #17، #18، #19، #20) — لكنه
  **لم يُحدِّث الملف الموحَّد نفسه إطلاقًا، ولا أضاف إدخالًا في قسم "📋 الجلسات المُقفلة" هنا حتى
  اليوم [2026-08-26]** (فقط 3 اكتشافات جانبية منه وُثِّقت، أسطر 202-204 — الملخص التنفيذي للجلسة
  غايب تمامًا). بالمقابل، commit `f17636c` (اليوم بعده مباشرة) **حدَّث الملف الموحَّد بدقة كاملة بعد
  كل إصلاح (✅ + تاريخ + تفاصيل التحقق) وأضاف إدخال جلسة كامل هنا فورًا** — نفس نوع الشغل بالضبط،
  نتيجة توثيقية مختلفة تمامًا. **الأثر العملي المؤكَّد:** الملف المرجعي الرسمي (`constructor-mismatch-backlog-classification.md`)
  فضل يعرض 7 بنود كـ"🔴 مفتوح" لمدة يوم كامل رغم إصلاحها فعليًا وتحقُّقها حيًا — أي قرار اعتمد على
  الملف وحده (بلا مراجعة الـcommits/PROGRESS_LOG مباشرة) كان هيكرر شغل مُنجَز فعلًا. **صُحِّح لاحقًا
  [جلسة 2026-08-26/27] بنفس المنهجية اللي كانت المفروض تُطبَّق وقتها: اقتباس دليل التحقق الحي من
  `.claude/reports/constructor-mismatch-backlog-cleanup-session-log.md` نفسه لكل بند من الـ6 قبل
  التعليم بـ✅، مش الاعتماد على رسالة الـcommit فقط — راجع `.claude/reports/constructor-mismatch-backlog-11-plus-6-mapping.md`
  و`.claude/reports/constructor-mismatch-backlog-remaining-approval-table.md`.** **الدرس العملي
  العام لأي جلسة إصلاح مستقبلية تغلق بنود Backlog مرقّمة:** تحديث الملف/الفهرس المرجعي المباشر
  (✅ + دليل حي مختصر) جزء لا يتجزأ من "إغلاق" البند، **ليس خطوة توثيقية اختيارية بعده** — التأجيل
  ولو ليوم واحد يخلق نافذة حقيقية لتكرار العمل أو اتخاذ قرارات بناءً على حالة قديمة. **اكتشاف إضافي
  أثناء نفس المراجعة:** نفس الفجوة (إصلاح مؤكَّد بلا علامة ✅ في الملف الموحَّد) موجودة كمان لـ9 بنود
  أقدم بكتير (#1، #5، #6، #7، #8، #9، #11، #14، #15 — مُصلَحة بين 2026-08-18 و2026-08-25 حسب هذا
  الملف نفسه، لكن غير معلَّمة في `constructor-mismatch-backlog-classification.md` حتى اليوم) — نمط
  متكرر، مش حادثة معزولة، يستاهل مراجعة شاملة لاحقة.

  **ملاحظة إضافية [2026-08-27]: اكتشاف جانبي أثناء تنفيذ #28 (`saas-service-catalog-missing-entries`).**
  #28 نُفِّذ فعليًا (بيانات seed فقط، صفر كود) — 4 صفوف أُدرجت في `saas_service_catalog`
  (`tenders` id=74, `auctions` id=75, `service_marketplace` id=76, `zamakana` id=77، كلها
  `is_active=true`)، تحقق حي: `SaaSRepository.get_service_by_code()` رجعت صفوف حقيقية للأربعة
  (كانت `None` قبل الإصلاح). **لكن أثناء التحقق ظهر إن الكتالوج كان شبه فاضٍ تمامًا قبل الإصلاح —
  3 صفوف بس، اتنين منهم بادئة `TEST_REQSECTOR_SESSION_*` (بيانات throwaway مش seed حقيقي).**
  وأخطر من كده: **`transport`/`tourism_sports`/`social` بتستخدم نفس آلية
  `SaaSControlService.can_access_service(code)` بأكواد (`transport`/`tourism_sports`/`social`)
  **لسه ناقصة من الكتالوج بنفس الأثر بالضبط** (`get_service_by_code` بترجع `None` → `False` دايمًا
  بغض النظر عن الاشتراك) — **مش من ضمن الـ3-4 دومينات الموصوفة أصلًا في #28، وغير مُصلَحة حتى
  الآن.** commit `6b4703a` (بند #31) أكَّد نفس الاكتشاف بشكل مستقل تمامًا (تحقق حي منفصل، نتيجة
  `403 PermissionDeniedError` لـ`social`/`tourism-sports`/`transport` بعد تصحيح الـURL prefix) —
  تقاطع دليلين مستقلين يرفع الثقة في دقة الاكتشاف. **صفر إصلاح لهذه الثلاثة — يستاهل توسيع #28
  نفسه أو بند Backlog منفصل لاحقًا.** راجع `.claude/reports/constructor-mismatch-backlog-classification.md`
  صف #28 (تحديث 2026-08-27) للتفاصيل الكاملة.

**⚠️ لم تُراجَع بثقة كافية في هذا الفهرس (موجودة كملفات في `.claude/reports/` لكن حالتها النهائية غير مُدمَجة هنا):** `silent-write-regression-session-log.md`، `phase16-session-log.md`، ملفات `.claude/reports/CRITICAL-*.md` الأخرى غير المذكورة أعلاه. راجع الأرشيف أو الملفات نفسها عند الحاجة.

| — | **`require-subscription-domain-coverage-gap`** [2026-08-20] — اكتُشف كأثر جانبي أثناء التحقق الحي لجلسة `require-sector-removal-subscription-fix`: بعد إلغاء `require_sector` بالكامل، أي دومين من الـ30 كان يعتمد **فقط** على `require_sector` بلا `require_subscription` بجانبه أصبح **بلا أي فحص وصول إطلاقًا** — مؤكَّد حيًا بمثال واحد (`GET /commerce/products` نجح 200 لمستخدم بلا أي اشتراك، حيث `commerce` لا يستخدم `require_subscription` في أي راوتر). **لم يُجرَ جرد شامل** لعدد/هوية الدومينات الأخرى المتأثرة بنفس النمط — العيّنة الوحيدة المؤكَّدة هي `commerce`، عبر تأكيد إضافي غير مخطَّط له أصلًا ضمن نطاق الجلسة (لم يكن أحد السيناريوهات الستة المطلوبة). | 🔴 **مفتوح، أولوية عالية نسبيًا** — يحتاج جلسة جرد سريعة (توثيق فقط) لكل الـ30 دومين: مين بيستخدم `require_subscription` فعليًا ومين بقى مكشوفًا بالكامل بعد إلغاء `require_sector` | `.claude/reports/require-sector-removal-subscription-fix-session-log.md` §6 (تأكيد إضافي بعد جدول السيناريوهات الستة) |

- **command-idor-fix — فحص IDOR في `command/router.py` (استكمال مسار `ai_agents`/`sovereign_entities`) [2026-08-24]** — ✅ **مُغلَق رسميًا.** بعكس افتراض التعليمات الأولي، `command` **كان بالفعل في الحالة النهائية (post-fix)** — كل الـ18 endpoint يستخدموا `tenant_id = cast(int, current_user.tenant_id)` من الأساس (مُصلَح مسبقًا من "Phase 16"، صفر `get_current_tenant`/هيدر مزوَّر). **تحقق حي كامل (6 اختبارات cross-tenant: قراءة+كتابة+حذف+تزوير هيدر) أكَّد عزل التينانتات سليم 100%، صفر IDOR عبر-تينانت.** **لكن اكتُشف واتصلح حيًا شيء أخطر من IDOR القياسي:** `update_my_brand` (`router.py:75`) كانت محمية بـ`get_current_active_user` بس (مش `get_current_superuser`، بعكس `create_brand` على نفس المورد) — أي مستخدم عادي (دور `USER`) قدر يعدّل فعليًا `billing_email`/`tax_id` لبراند التينانت كله (privilege escalation داخل نفس التينانت، مؤكَّد حيًا: `200` قبل الإصلاح، تحقق DB مستقل أكَّد التغيير الفعلي). **الإصلاح:** رفع الحماية لـ`get_current_superuser` (سطر واحد، مطابق تمامًا لـ`create_brand`). **تحقق حي "بعد":** نفس محاولة المستخدم العادي ترجع `403` الآن، تحقق DB مستقل أكَّد صفر أثر، والمسار الشرعي (سوبريوزر) سليم 100%. تنظيف كامل لبيانات throwaway + `SELECT COUNT` مستقل يؤكد صفر. تقرير كامل: `.claude/reports/command-idor-fix-session-log.md`.

| — | **`saas-pay-invoice-sender-id-user-id-collision`** [2026-08-24] — اكتُشف أثناء جلسة `saas-idor-fix`: `SaaSControlService.pay_invoice`/`process_auto_renewals` (`service.py:306`, `:166`) بينادوا `self.finance.transfer(sender_id=self.tenant_id, ...)` — أي بيمرروا **`tenant_id`** في معامل `sender_id`. لكن `FinanceService.get_or_create_wallet_for_update(user_id, tenant_id)` (`finance/service.py:34-39`، مؤكَّد بالقراءة المباشرة) بتفسّر `sender_id` كـ**`user_id`** حرفيًا وتبحث عن محفظة بـ`(user_id=sender_id, tenant_id=self.tenant_id)`. **الخطر:** لو تصادف `id` مستخدم حقيقي داخل نفس التينانت = رقم الـ`tenant_id` نفسه (تصادم IDs وارد عمليًا مع IDs تسلسلية)، `pay_invoice`/تجديد تلقائي هيخصم/ينشئ محفظة باسم ذلك المستخدم العشوائي — **مش محفظة تينانت مخصَّصة ولا محفظة المستخدم اللي نادى الـendpoint فعليًا**. **غير قابل للتحقق الحي حاليًا** — محجوب بالكامل بانحراف schema منفصل (`saas-invoices-idempotency-key-schema-drift` — عمود `idempotency_key` مفقود من جدول `saas_invoices` الفعلي، `get_invoice()` بيكراش قبل ما يوصل لـ`finance.transfer()` أصلًا). **يحتاج حل انحراف الـschema أولًا، ثم مراجعة معمارية منفصلة تمامًا لمصدر `sender_id` الصحيح** (تينانت مالكة محفظة نظامية؟ المستخدم الفعلي اللي نادى الـendpoint؟ قرار منتجي). | 🔴 **مفتوح، أولوية عالية جدًا** — خطر مالي حقيقي (مسّ محفظة مستخدم عشوائي)، مش IDOR كلاسيكي لكنه أخطر أثرًا | `.claude/reports/saas-idor-fix-session-log.md` §4 |

| — | **`saas-test-reqsector-leaked-throwaway-data-breaks-get-my-subscriptions`** [2026-08-24] — اكتُشف أثناء جلسة `saas-idor-fix` عند اختبار `GET /saas/subscriptions` (`get_my_subscriptions`) حيًا: رجعت `500` (`pydantic_core.ValidationError: 4 validation errors for TenantSubscriptionResponse`) — **ليس باج كود، ولا علاقة له بعزل التينانت.** السبب مؤكَّد من اللوج: صفان **متبقيان فعليًا في قاعدة `eppne_v2` من جلسة `require-sector-removal-subscription-fix` السابقة** (بادئة `TEST_REQSECTOR_*`، تينانت1) — `saas_tenant_subscriptions.id=50` (`payment_method=NULL`) وخطتها `saas_service_plans.id=48` (`max_users`/`max_products`/`max_courses` كلهم `NULL`). هذه الأعمدة عندها `default=` على مستوى Python/SQLAlchemy بس (مش `server_default`/`NOT NULL` على مستوى الـDB)، فالصفوف المزروعة يدويًا وقتها بلا القيم دي صراحة أصبحت غير قابلة للقراءة عبر `TenantSubscriptionResponse` (تتطلب non-optional). **الأثر الفعلي الآن:** **أي مستخدم حقيقي في تينانت1 يستدعي `GET /saas/subscriptions` اليوم يرجعله `500`** — بيانات throwaway متسربة من جلسة سابقة بتأثر فعليًا على مسار إنتاجي حي، مش مجرد "كود محتاج تحسين مستقبلي". **الحل المطلوب: تنظيف بيانات (`UPDATE`/`DELETE` الصفين، أو تعبئة القيم الناقصة)، صفر تعديل كود** — مختلف تمامًا عن فئة "silent-write"/schema drift الأخرى في هذه الجلسة. | 🟠 **مفتوح، أولوية متوسطة-عالية** — بيانات متسربة بتأثر على مستخدمين حقيقيين الآن، لا مجرد كود يحتاج تحسين | `.claude/reports/saas-idor-fix-session-log.md` §4 |

| — | **`finance-transfer-hardcoded-system-account-real-fund-risk`** [2026-08-24] — اكتُشف أثناء جلسة `finance-idor-security-fix` (فحص عميق منبثق من `saas-pay-invoice-sender-id-user-id-collision` فوق): **3 دومينات — `commerce.release_commissions` (`commerce/service.py:303`)، `affiliate.withdraw_commissions` (`affiliate/service.py:477`)، `iot.settle_carbon_credits` (`iot/service.py:213`) — بتمرر `sender_id=1` هاردكودد حرفيًا** لـ`finance.transfer()` كتمثيل لـ"حساب النظام/الخزانة"، رغم إن `finance` معندهاش مفهوم حساب نظام مخصَّص أصلًا (لا `is_system` flag، لا استثناء في `get_or_create_wallet_for_update`). **تحقق حي (`SELECT` فقط، صفر استدعاء دالة) أكَّد الخطر حقيقي مش نظري:** `user_id=1` (تينانت1) موجود فعليًا، إيميله `p_system_treasury@example.com`، `created_at=2026-08-14` — بقايا بيانات throwaway من جلسة `silent-write-regression` **موثَّقة هناك صراحة كـ"هتتنضف آخر الجلسة" ولم تُنضَّف**، وله محفظة حقيقية برصيد فعلي **875.0 MR_USDT حاليًا** (`wallets.id=39`). **الأثر: أي استدعاء حقيقي/إنتاجي للثلاثة دول (تحرير عمولة تاجر، سحب عمولة داعي، تسييل كربون IoT) هيخصم فعليًا من هذا الرصيد الحقيقي — بلا أي نية هجومية، مجرد استخدام عادي للميزة الشرعية كافٍ.** (بند رابع أقل خطورة: `social.subscribe_group_to_plan`, `social/service.py:633`, بيمرر `sender_id=0` — `user_id=0` غير موجود أصلًا، على الأرجح `IntegrityError` قاطع/فشل وظيفي مش تسريب مالي). **لم يُنفَّذ أي استدعاء حي للثلاثة الخطيرة** — فحص مسبق (بطلب صريح) أثبت إن الثلاثة عندهم `db.commit()` داخلي غير مشروط جوه جسم الدالة نفسها (`commerce/repository.py:264` جوه `release_commission()`، `affiliate/service.py:509`، `iot/service.py:244`) — **مستحيل تحقق آمن بـ`begin`/`ROLLBACK` من برّه بلا لمس الكود**، فالإثبات مقصور على القراءة الثابتة + دليل `SELECT`. **صفر إصلاح كود حتى الآن — القرار المعماري (`is_system` flag؟ حساب خزانة مُدار رسميًا؟ مصدر آخر؟) محتاج نقاش تصميمي منفصل.** ⚠️ **لو التطبيق قريب من أي استخدام حقيقي/إنتاجي: الدومينات التلاتة دي لازم تتعطّل مؤقتًا أو يتحط عليها guard clause صريح (رفض `sender_id in (0, 1)` قبل نداء `finance.transfer()`) لحد ما يتصمم الحل الرسمي — القرار ده لسه مؤجَّل لتوجيه صريح.** التطبيق لسه مش شغال بمستخدمين حقيقيين حاليًا (2026-08-24) — الخطر نظري مش فوري. **لكن هذا البند launch blocker صريح: `commerce.release_commissions` و`iot.settle_carbon_credits` ممنوع تفعيلهم لمستخدمين حقيقيين قبل حل القرار المعماري (`is_system` flag أو حساب خزانة مُدار رسميًا).**

**✅ جزئيًا [تأكيد 2026-09-16]:** فحص حي (`grep -n "sender_id=1"` على الثلاثة ملفات) أثبت إن **الثلاثة الأصليون اتصلحوا فعليًا** في جلسة لاحقة غير موثَّقة صراحة على هذا البند وقت الإصلاح: `commerce/service.py` (`sender_id=customer_id`/`order.customer_id`، صفر hardcode)، `affiliate/service.py:577` و`iot/service.py:215` بقوا يستخدموا `get_or_create_system_account(self.db, tenant_id)` (tenant-scoped، مش حساب عالمي مشترك). **جزء مفتوح صراحة لسه:** نفس النمط الخطير (بالحرف) اكتُشف حيًا في مكان **جديد لم يكن مذكورًا هنا أصلًا** — `insurance/service.py:626` داخل `disburse_monthly_pensions()`، لسه `sender_id=1` هاردكودد بلا `get_or_create_system_account`. تحقق حي إضافي [2026-09-16]: الدالة **مش مجدولة خالص** (صفر Celery beat/APScheduler، endpoint يدوي `POST /insurance/admin/disburse-pensions` superuser-only) — الخطر كامن (latent) مش حي فعليًا حاليًا. تأكيد رصيد `wallets.id=39`: انخفض من 875.0 إلى 771.0 MR_USDT، لكن الفرق (104.0) بالكامل من معاملات اختبار (`REGTEST-*`/فواتير اختبار)، **صفر معاملة pension في تاريخ الجدول بالكامل** — الباج الجديد لم يُستغل بعد. | 🟡 **مُغلَق جزئيًا (3 من 4 مواضع)، الجزء المتبقي (`insurance/service.py:626`) موثَّق كبند منفصل تحت** | `.claude/reports/finance-idor-security-fix-session-log.md`، `.claude/plans/critical-finding-xtenant-systemic.md` (تحديث [2026-08-24] الأحدث)، `.claude/reports/backlog-review-2026-09-16-session-log.md` |

| — | **`projects-add-contribution-hardcoded-receiver-email`** [2026-08-24] — اكتُشف بالقراءة الثابتة أثناء جلسة `projects-idor-fix` (`projects/service.py:180-190`، `add_contribution`، نوع `MONETARY`): `finance.transfer(receiver_email="system@eppne.com", ...)` — بريد مستلم ثابت هاردكودد، بلا أي إعداد لكل تينانت. **بعكس `finance-transfer-hardcoded-system-account-real-fund-risk` أعلاه (`sender_id=1` ثابت عالميًا، بلا فلترة تينانت)، هذا الاستدعاء أضعف/مشروط:** `FinanceService.transfer` بتعمل `user_repo.get_by_email(receiver_email, self.tenant_id)` **مفلتر بالتينانت نفسه** — لازم يوجد مستخدم حقيقي بريده بالحرف `system@eppne.com` **داخل كل تينانت على حدة**؛ لو غير موجود، فشل آمن (`NotFoundError`)، مش تسريب لحساب عالمي مشترك. **الخطر الوحيد المتبقي:** بما إن `tenant_id` نفسه في `add_contribution` كان (قبل إصلاح جلسة `projects-idor-fix`) مصدره هيدر مزوَّر، لو `system@eppne.com` موجود فعلاً في تينانت الضحية، مهاجم كان يقدر (بهيدر مزوَّر) يوجّه مساهمة "له" تُخصَم من محفظته الحقيقية وتُقيَّد تحت مشروع تينانت آخر — **هذا الجزء أُغلق فعليًا بإصلاح الجذر (`tenant_id = cast(int, current_user.tenant_id)`) في نفس الجلسة**، فالمخاطرة الحالية مشروطة بوجود مستخدم `system@eppne.com` فعلي لكل تينانت، لا أكثر. **لم يُستدعَ حيًا إطلاقًا** (بقرار متعمَّد، نفس معاملة `commerce.release_commissions`). **صفر إصلاح كود — مرجع/توثيق فقط بقرار مستخدم صريح، ليس تصعيدًا عاجلاً بعكس البند أعلاه.** | 🟡 **مرجع فقط — أضعف من البند أعلاه، مشروط بوجود مستخدم `system@eppne.com` لكل تينانت، والجزء الأخطر (مصدر `tenant_id`) مُغلَق بالفعل** | `.claude/reports/projects-idor-fix-session-log.md` §4.2 |
| — | **`insurance-review-claim-payout-from-reviewer-personal-wallet`** [2026-08-28] — اكتُشف بالقراءة الثابتة أثناء التحقق الحي لإصلاح Backlog #37 (`finance-transfer-payment-tx-hash-broken`) على `insurance.review_claim`: `insurance/service.py:462-469` — مسار الموافقة (`approve=True`) بينادي `finance.transfer(sender_id=reviewer_id, receiver_email=<claimant>, ...)` — يعني **تعويض المطالبة بيتحوّل من محفظة المراجع (`reviewer_id`) الشخصية مباشرة، مش من حساب نظام/خزانة تأمين مركزي**. **نفس فئة `finance-transfer-hardcoded-system-account-real-fund-risk`/`projects-add-contribution-hardcoded-receiver-email` أعلاه (غياب مفهوم "حساب نظام" في `finance` أصلًا)، لكن بزاوية معكوسة:** الاتنين اللي فوق بيمرروا `sender_id`/`receiver_email` **ثابت هاردكودد** يمثّل نظام؛ هنا **مفيش تمثيل لحساب نظام إطلاقًا** — المستخدم البشري اللي بيوافق على المطالبة (`reviewer_id`، مرتبط بـ`policy.issuer_entity_id` عبر فحص #41) هو نفسه اللي بيدفع من رصيده الشخصي في `MR_USDT`. **الأثر العملي المحتمل:** أي مراجع حقيقي وافق على مطالبة تعويض كبيرة هيتخصم فعليًا من محفظته الشخصية بمبلغ التعويض كامل، بدل ما يكون مجرد "موافقة إدارية" — سلوك غير متوقَّع على الأرجح من منظور المنتج (هل ده مقصود كنموذج "ضامن شخصي"، ولا خطأ تصميم يفترض ضمنيًا وجود حساب خزانة التأمين اللي مش موجود فعليًا في `finance`؟). **صفر لمس كود — توثيق فقط، خارج نطاق #37 صراحة (اللي اقتصر على تصحيح `.tx_hash`/`Transaction` فقط، بلا أي تعديل على منطق التحويل نفسه).** غير مؤكَّد حيًا كـ"مشكلة" (التحويل نفسه نجح بنجاح تام في التحقق الحي لـ#37 — راجع `.claude/reports/constructor-mismatch-backlog-37-insurance-result.md`)، لكنه سؤال تصميمي/منتجي حقيقي يستاهل نقاش منفصل قبل أي استخدام إنتاجي واسع لـ`review_claim`. | 🟡 **مرجع فقط، يستاهل نقاش تصميمي منفصل** — لا يمنع #37 ولا يُعتبر جزءًا منه | `.claude/reports/constructor-mismatch-backlog-37-insurance-result.md`؛ `.claude/reports/constructor-mismatch-backlog-37-blockers-found.md` |

**✅ تأكيد حي [2026-09-21، Batch 0-A]:** أُعيد تأكيد هذا السلوك حيًا (بند موجود، بلا بند جديد): `PUT /insurance/claims/{id}/review?approve=true&approved_amount=20` في سيناريو مشروع (أدمن تينانت A، عضو OWNER في الكيان المُصدِر) → `200`، المطالبة `PAID`، **محفظة المراجِع (`admin_A`) اتخصم منها 20 (500→480)، ومحفظة صاحب المطالبة (`member_A`) اتضاف لها 20 (490→510)**، `payout_tx_hash=TX-EEC5CFD5BC46` — نفس النتيجة بالحرف قبل الإصلاح (تينانت 124، `TX-EAC1C8F3023D`) وبعده (تينانت 128). السلوك لم يتغيّر (قرار تصميم/منتج، خارج نطاق Batch 0-A، لم يُلمَس بأمر صريح من المستخدم). المرجع: `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §7.2، §11.

| — | **`invoicing-generate-invoice-number-count-based-collision`** [2026-08-29] — اكتُشف حيًا أثناء التحقق الحي end-to-end لإصلاح Backlog #37 على `tourism_sports.book_program` (بعد توسيع #28 بكود `"tourism"` لفتح الطريق للتحقق الكامل): `InvoicingService._generate_invoice_number()` (`invoicing/service.py:115-119`) بتبني رقم الفاتورة بصيغة `f"INV-{tenant_id}-{str(count+1).zfill(6)}"` حيث `count = await self.repo.count_invoices(tenant_id)` — **عدّ حي (`COUNT(*)`) مش sequence حقيقي**. أي فاتورة اتحذفت قبل كده لنفس التينانت (شائع جدًا في هذا المشروع — تنظيف throwaway بعد كل جلسة تحقق) بتخلي الـ`COUNT` الحالي أقل من أعلى رقم اتّستخدم فعليًا تاريخيًا، فأول محاولة إنشاء فاتورة جديدة بعدها بترجع رقم **مُستخدَم بالفعل** → `IntegrityError: duplicate key value violates unique constraint "invoices_invoice_number_key"`. **مؤكَّد حيًا:** أول محاولة حقيقية لـ`book_program` (بعد نجاح الدفع وكتابة `payment_tx_hash` بنجاح تام — الخطوة دي **مش** جزء من كراش #37، الفاتورة بتتبنى **بعد** `commit()` الخارجي، نفس نمط #11b) اصطدمت بـ`INV-1-000015` (رقم موجود مسبقًا لفاتورة أقدم من جلسة تانية غير مرتبطة) — التعارض مضمون التكرار في أي محاولة تالية بنفس الظروف (مش صدفة لمرة واحدة). **الأثر:** أي endpoint بيستدعي `InvoicingService.create_invoice()` لتينانت له تاريخ حذف فواتير throwaway (يعني كل تينانت اختباري تقريبًا في هذا المشروع) معرَّض لنفس الكراش — بعد نجاح الدفع/الحجز الأساسي فعليًا (مش قبل)، فالأثر المالي الأساسي سليم لكن الفاتورة نفسها بتفشل. **صفر إصلاح — توثيق فقط، خارج نطاق #37 صراحة** (اللي اقتصر على `.tx_hash`/`Transaction`). الحل الصحيح على الأرجح: `SEQUENCE` حقيقي في Postgres بدل `COUNT`، أو `UUID`/timestamp-based numbering. | 🔴 **مفتوح، أولوية متوسطة-عالية** — يمنع إنشاء فواتير حقيقية لأي تينانت له تاريخ حذف بيانات throwaway، عبر كل الدومينات المستخدمة لـ`InvoicingService` | `.claude/reports/constructor-mismatch-backlog-37-tourism-transport-result.md` |

  **⚠️ تصحيح [2026-08-29]:** هذا البند **مش اكتشاف جديد فعليًا** — نفس العلة بالحرف موثَّقة مسبقًا
  في سطر أعلى بتاريخ **2026-08-18** (`invoicing-generate-invoice-number-count-based-collision`
  الأصلي، أول ظهور في الملف) بنفس السبب الجذري (`count()` بدل sequence) ونفس الدليل الحي
  (`count()=14` مقابل `INV-1-000015` موجودة). إعادة الاكتشاف المستقلة في #37 (2026-08-29) بتأكيد
  حي جديد كليًا (تينانت/سيناريو مختلف) تُعتبر **تقاطع دليلين مستقلين يرفع الثقة إن البج حقيقي
  ومستمر منذ 11 يوم بلا إصلاح**، مش تكرار عرضي — لكن يستاهل تنويه صريح: الرقم/التاريخ الصحيح
  لأول اكتشاف هو 2026-08-18 وليس 2026-08-29.

| — | **`realestate-hooks-layer-nonexistent-function-imports`** [2026-08-29] — اكتُشف أثناء الجرد
  التأكيدي لبند Backlog #43 (`frontend-service-export-import-name-mismatch`): `services/realestate.ts`
  يُصدِّر **كائن واحد فقط** (`RealEstateService`، بمethods: `createLandAsset`, `getMyLands`,
  `revalueLand`, `createDevelopment`, `getDevelopment`, `createPropertyUnit`, `listUnitsForSale`,
  `buyFraction`, `getMyOwnerships`, `createRentalContract`, `createMasterPlan`, `tokenizeAsset`,
  `deploySmartContract`) — **صفر named exports مستقلة**. لكن **كل الأربعة ملفات في
  `hooks/realestate/*.ts`** (`useMyOwnerships.ts`, `useProperties.ts`, `usePropertyOwnerships.ts`,
  `useTokenization.ts`) بتستورد دوال مباشرة **غير موجودة إطلاقًا** كـnamed exports:
  `getMyOwnerships`, `getProperties`, `getProperty`, `createProperty`, `updateProperty`,
  `deleteProperty`, `getPropertyOwnerships`, `getAssetTokenization`, `createTokenization`,
  `buyFractionalShare`. **مختلف جوهريًا عن #43** (مش مجرد اختلاف حالة أحرف زي `iotService`/`IoTService`
  — الأسماء نفسها مختلفة تمامًا عن methods الكائن الحقيقية، حتى لو قريبة مفاهيميًا: `createPropertyUnit`
  ≠ `createProperty`، `listUnitsForSale` ≠ `getProperties`، `tokenizeAsset` ≠ `createTokenization`،
  `buyFraction` ≠ `buyFractionalShare`). **الأثر:** `TS2305` قاطع لكل الأربعة ملفات — أي مكوّن
  فرونت إند يستخدم هذه الـhooks (`InvestorPortfolio`, `MasterPlanExplorer`,
  `SmartContractDashboard`, `TokenizationExchange`, صفحة `realestate` نفسها) معطَّل بالكامل على
  مستوى الـbuild، مش وقت تشغيل فقط. **صفر إصلاح — يحتاج قرار تصميمي/مراجعة مقصودة** (هل الـhooks
  اتكتبت ضد نسخة تصميم API قديمة للـservice كليًا اتغيّرت لاحقًا لكائن واحد؟ ولا العكس؟) قبل أي
  ربط ميكانيكي بسيط — رينيم بسيط ممكن يربط بالـmethod الغلط دلاليًا. راجع
  `.claude/reports/constructor-mismatch-backlog-classification.md` صف #43 (تحديث 2026-08-29). |
  🔴 **مفتوح، أولوية عالية — يعطّل الـbuild لـ4 مكوّنات + صفحة كاملة** | `.claude/reports/constructor-mismatch-backlog-classification.md` |

| — | **`iot-translation-service-method-mismatches-post-backlog43-fix`** [2026-08-29] — اكتُشف
  فورًا بعد إصلاح Backlog #43 (rename `iotService`→`IoTService`، `translationService`→`TranslationService`
  عبر 8 ملفات): قبل الإصلاح كانت هذه الاستدعاءات كلها تظهر كـ`TS2304 Cannot find name` (المتغيّر
  نفسه غير معرَّف)، فـ`tsc` ما كانش بيوصل لفحص توافق الـmethods المُستدعاة أصلًا. بعد الإصلاح
  (الكائن بقى معرَّف صح)، ظهرت أعطال حقيقية **مستخبية سابقًا**، من فئتين: **(أ) method غير موجودة
  بالاسم ده** — `IoTService.getAssets` (بالجمع) مُستخدَمة في `AssetsManager.tsx`/`IoTDashboardStats.tsx`
  لكن الكائن الفعلي عنده `getAsset` (بالمفرد) بس (`TS2551 ... Did you mean 'getAsset'?`)؛ **(ب) عدم
  توافق أنواع بين الـmethod الحقيقية ونوع الـhook المستهلِك** — `CarbonCreditPanel.tsx` (مقارنات/عمليات
  حسابية على قيم من النوع الخطأ)، و`BatchTranslator.tsx`/`ChatTranslator.tsx`/`TextTranslator.tsx`
  (توقيع دالة `TranslationService.xxx` الحقيقي بيقبل `headers?` كمعامل ثانٍ اختياري، بينما
  `MutationFunction` من `@tanstack/react-query` بتتوقَّع توقيع مختلف تمامًا). **`LanguageSelector.tsx`
  الوحيدة اللي بقت نضيفة 100% بعد إصلاح #43 وحده** — الباقي (7 ملفات) لسه فيهم أعطال. **صفر إصلاح —
  خارج نطاق #43 صراحة** (اللي اقتصر على اسم الكائن نفسه). راجع نفس المرجع فوق. |
  🟡 **مفتوح، أولوية متوسطة** — أعطال build حقيقية لكنها كانت مستخبية أصلًا خلف باج #43 (يعني
  الوضع الوظيفي الفعلي للمستخدم النهائي متحسِّنش بمجرد إصلاح #43 وحده لهذه الملفات السبعة) |
  `.claude/reports/constructor-mismatch-backlog-classification.md` |
| — | **`command-rbac-ownership-review`** [2026-08-24] — اكتُشف أثناء التحقق الحي في جلسة `command-idor-fix`: عدة endpoints في `command/router.py` (`acknowledge_alert`, `resolve_alert`, `get_report`, `delete_report`, `apply_recommendation`) بتفلتر بـ`tenant_id` بس (سليم وموثوق)، **بلا أي فحص ملكية/دور إضافي** — أي `active_user` (حتى دور `USER` العادي) يقدر يتصرف في تنبيهات/تقارير/توصيات أنشأها عضو تينانت تاني (سوبريوزر مثلًا)، **طالما داخل نفس التينانت**. **مؤكَّد حيًا مباشرة (مش افتراض):** مستخدم `USER` عادي (id=844) نادى `POST /command/alerts/1/acknowledge` على تنبيه أنشأه سوبريوزر تاني → `200` (`acknowledged_by` اتسجَّل = المستخدم العادي)، وبعدها `DELETE /command/reports/2` (تقرير أنشأه نفس السوبريوزر) → `204`، تحقق DB مستقل أكَّد `is_deleted=true`. **هذا ليس IDOR عبر-تينانت** (العزل بين التينانتات سليم 100%، مؤكَّد في نفس الجلسة) — لكنه غياب RBAC/ownership على عمليات حذف/كتابة بيانات استراتيجية (تقارير/تنبيهات) داخل نفس التينانت. **قد يكون تصميمًا تعاونيًا مقصودًا (أدوات تينانت-واسعة) أو ثغرة صلاحيات تحتاج تقييد بدور/ملكية — قرار منتجي، بقرار مستخدم صريح لم يُصلَح في جلسة الاكتشاف.** **⚠️ توسيع [2026-08-24، جلسة `saas-idor-fix`]:** نفس السؤال ينطبق على `saas.subscribe_to_plan`/`cancel_subscription`/`pay_invoice`/`get_my_invoices` — كلها `active_user`، يعني أي موظف عادي (بلا دور إداري) يقدر يلغي اشتراك التينانت كله أو يحاول الدفع من رصيده. **بعكس `command.update_my_brand`، لا يوجد هنا تناقض حماية بين sibling endpoints** (مفيش نظير بمستوى أعلى لنفس المورد يفضح التناقض) — يبدو تصميم self-service مقصود، لكنه يستاهل نفس القرار المنتجي المعلَّق هنا. | 🟠 **مفتوح، أولوية متوسطة-عالية** — يمس حذف بيانات استراتيجية فعليًا (تقارير/تنبيهات) في `command`، وإلغاء/دفع اشتراكات تينانت كامل في `saas`؛ يحتاج قرار منتجي قبل أي تنفيذ **✅ [مُغلَق، 2026-08-25]: القرار المنتجي اتحسم — جلسة `rbac-ownership-review` (فحص محتوى `report_data`/`InvoiceResponse`/`service.py` فعليًا، مش افتراض) صنّفت الثمانية: 4 فجوات حقيقية مؤكَّدة (`acknowledge_alert`, `resolve_alert`, `get_report`, `delete_report`) + 3 مالية حقيقية في `saas` (`subscribe_to_plan`, `cancel_subscription`, `pay_invoice`)، `apply_recommendation` تراجع تصنيفه (status/tag فقط، صفر تنفيذ فعلي) لكن اتقيّد بنفس القرار بطلب المستخدم، و`get_my_invoices` تأكَّد آمن (صفر بيانات دفع حساسة) فبقي بلا تعديل. **التنفيذ:** الثمانية اتقيّدوا بـ`Depends(require_admin_or_above)` بدل `get_current_active_user` — سطر واحد لكل endpoint، نفس نمط `update_my_brand`، **صفر migration** (دور `ADMIN` موجود من الأساس، `require_admin_or_above` مُختبَرة إنتاجيًا في `identity`). **تحقق حي كامل 8/8:** `USER` عادي → `403`، `ADMIN`/`SUPER_ADMIN` → نجاح طبيعي + تأكيد DB مستقل على كل كتابة/حذف. commit `313f880`، مدفوع لـ`origin/main`. تقرير كامل: `.claude/reports/rbac-ownership-review-session-log.md`.** | `.claude/reports/command-idor-fix-session-log.md` §5؛ `.claude/reports/saas-idor-fix-session-log.md` §2 |

| — | **`commerce-affiliate-backfill-review-at-launch`** [2026-08-24] — بعد إصلاح `set_affiliate_sponsor` في جلسة `commerce-idor-fix` اليوم (منع سبونسرات عبر-تينانت/وهمية من الآن فصاعدًا)، لو كان فيه بيانات إنتاج حقيقية وقت الإطلاق الفعلي للتطبيق، يحتاج فحص `affiliate_trees`/`commission_records` الموجودة وقتها لتدقيق أي صفوف قديمة (اتسجلت قبل هذا الإصلاح) بسبونسر غير صالح/عبر-تينانت. غير عاجل الآن (صفر مستخدمين حقيقيين حاليًا) — لكن لازم يُراجَع صراحة كخطوة ضمن قائمة ما-قبل-الإطلاق، مش يتنسى. | 🟡 **مفتوح، أولوية منخفضة حاليًا — يتحول لعاجل عند وجود بيانات إنتاج حقيقية** | `.claude/reports/commerce-idor-fix-session-log.md` §3.2, §9, §10 |

| — | **`ai-governance-check-and-consume-bool-vs-dict-response`** [2026-08-24] — اكتُشف أثناء جلسة `ai-governance-idor-fix`: `AIGovernanceService.check_and_consume()` توقيعها `-> bool` وترجع `True`/`False` فعليًا، لكن `ai_governance/router.py` (endpoint `check-and-consume`) بيعامل الناتج كـ`dict` (`result["allowed"]`) → `TypeError` مُلتقَط داخل `try/except` عام في الراوتر نفسه، فيترجم لرد **مضلِّل** (`{"allowed": false, "error": "'bool' object is not subscriptable"}`) **حتى لو الاستهلاك الحقيقي نجح فعلًا وكُتب في `agent_usage_logs`** — مؤكَّد حيًا (راجع المرجع). **الأولوية أعلى من البندين التاليين** لأنه يخفي نجاح/فشل كتابة حقيقية وراء رد كاذب — أي مستدعٍ (بما فيهم استدعاءات in-process من دومينات أخرى بعد إصلاح `check_and_consume` الأصلي) قد يفتكر إن الاستهلاك فشل بينما فعليًا نجح وسُجِّل. مؤجَّل عمدًا لجلسة إصلاح `check_and_consume` المخصَّصة (قد يتقاطع مع بند `ai-governance-quota-result-ignored` الموثَّق مسبقًا) — لا يُلمَس كجزء من إصلاح IDOR. | 🟠 **مفتوح، أولوية عالية** — يخفي نتيجة كتابة حقيقية وراء رد مضلِّل | `.claude/reports/ai-governance-idor-fix-session-log.md` §3.1, §3.4.3, §6.3 |

| — | **`ai-governance-check-agent-ownership-undefined`** [2026-08-24] — اكتُشف أثناء جلسة `ai-governance-idor-fix`: `ai_governance/router.py` بينادي `service._check_agent_ownership(agent_id, current_user.id)` في 3 endpoints (`get_agent_quotas`, `get_agent_remaining_quotas`, `get_rate_limit`)، لكن `_check_agent_ownership` **غير معرَّفة إطلاقًا** في `AIGovernanceService` — كل استدعاء يرمي `AttributeError` غير محمي بـ`try/except` → `500` مضمون لكل طلب، بغض النظر عن التينانت/الصلاحية. مؤكَّد حيًا (المالك الحقيقي بتوكنه الصحيح جرَّب `GET /agents/{id}/quotas` → `500`). **ليس IDOR** (الطلب يفشل بدل أن ينجح خطأً) — لكنه يعني إن الثلاثة endpoints دول معطَّلة وظيفيًا بالكامل حاليًا. | 🟡 **مفتوح، أولوية متوسطة** — كراش وظيفي كامل لـ3 endpoints، صفر علاقة بـIDOR | `.claude/reports/ai-governance-idor-fix-session-log.md` §1, §3.4.1 |

| — | **`ai-governance-set-quota-reset-at-missing`** [2026-08-24] — اكتُشف أثناء جلسة `ai-governance-idor-fix`: عمود `agent_quotas.reset_at` عندها `NOT NULL` بلا `server_default`، لكن `AgentQuotaCreate` schema (المُستخدَمة في `POST /agents/{id}/quotas`) **لا تحتوي `reset_at` إطلاقًا**، ولا `AIGovernanceRepository.create_or_update_quota` بتزوّده افتراضيًا. النتيجة: أي محاولة إنشاء حصة جديدة عبر الـendpoint الرسمي **تفشل دائمًا** بـ`IntegrityError: null value in column "reset_at"` — لأي تينانت، مش بس تينانت مزوَّر. مؤكَّد حيًا مرتين (قبل/بعد إصلاح IDOR، نفس النتيجة). | 🟡 **مفتوح، أولوية متوسطة** — يمنع إنشاء أي حصة AI جديدة عبر الـAPI بالكامل | `.claude/reports/ai-governance-idor-fix-session-log.md` §3.3, §3.4.2, §6.3 |

| — | **`academy-create-bootcamp-instructor-id-mismatch`** [2026-08-24] — اكتُشف أثناء التحقق الحي لجلسة `academy-idor-fix`: `AcademyRepository.create_bootcamp()` (`repository.py:154-159`) بتمرر `instructor_id` لـ`Bootcamp(**kwargs)`، لكن جدول `academy_bootcamps` الفعلي **بلا عمود `instructor_id` إطلاقًا** (تأكيد `\d academy_bootcamps` حي: `id, org_entity_id, title, description, duration_days, target_rank, is_active, created_at, updated_at` فقط). **مؤكَّد حيًا: `TypeError: 'instructor_id' is an invalid keyword argument for Bootcamp`، فوري، لأي طلب `POST /academy/bootcamps` بلا استثناء** — بعد تجاوز باج `require_subscription` الموثَّق مسبقًا في `academy-live-testing-session-log.md` (لسه قائم كما هو، خارج نطاق هذه الجلسة). نفس فئة `constructor-mismatch` (schema↔model) الموثَّقة في البند `projects-schema-model-field-mismatch` أعلاه — أُضيفت كحالة رابعة (#20) في `constructor-mismatch-backlog-classification.md`. **صفر لمس/إصلاح — خارج نطاق جلسة `academy-idor-fix` صراحة (كانت مخصَّصة للجذر IDOR فقط)، توثيق فقط.** بيانات الاختبار الحية زُرعت عبر SQL مباشر بدلًا من الـAPI المعطوبة، ونُظِّفت بالكامل بعد التحقق. | 🔴 **مفتوح، لم يبدأ** — إصلاح محلي بحت (إضافة عمود `instructor_id`، أو استبعاده من `**kwargs` قبل `Bootcamp(...)`) — صفر سبب جذري مشترك مع أي دومين آخر | `.claude/reports/academy-idor-fix-session-log.md` §1, §3.4 |

| — | **`throwaway-test-users-password-documented`** [2026-08-24] — أثناء جلسة `digital-twin-idor-fix`: كلمة سر مستخدمَي throwaway المُعاد استخدامهم عبر كل جلسات سويپ IDOR السابقة (`772`/`TEST_super_a`/تينانت1، `774`/`TEST_instr_b`/تينانت16) **لم تكن موثَّقة في أي مكان مركزي** — تم تعيين/توثيق كلمة سر رسمية لأول مرة (`TEST_pass_dtwin_2026`، عبر `bcrypt hash` مباشر في `users.hashed_password`، صفر تعديل كود). **ملف مرجعي مخصَّص جديد أُنشئ:** `.claude/reports/throwaway-test-users.md` — يوثّق المستخدمين/التينانتات المُعاد استخدامها + كلمة السر الحالية، ويُحدَّث كلما تغيّرت. **أي جلسة سويپ قادمة تفشل في تسجيل الدخول بهذين الحسابين: راجع الملف ده أولًا قبل افتراض حساب معطوب.** | 🟢 **مرجعي فقط — ليس بند إصلاح** | `.claude/reports/throwaway-test-users.md` |

| — | **`digital-twin-unique-user-id-crash-on-tenant-mismatch`** [2026-08-24] — اكتُشف أثناء التحقق الحي لجلسة `digital-twin-idor-fix`: 4 جداول (`digital_twin_configs`, `time_capsules`, `digital_wills`, `death_oracle_checks`) عندها قيد `UNIQUE` **عالمي على `user_id` وحده** (مش composite مع `tenant_id`) — `ix_digital_twin_configs_user_id` وأقرانها، تأكيد `\d` حي على الأربعة. النتيجة: أي مستخدم عنده صف واحد بالفعل تحت أي تينانت (حقيقي أو حتى ناتج عن تزوير هيدر) **يستحيل ينشئ صف تاني تحت أي تينانت مختلف** — أي محاولة ثانية (`get_or_create_twin`/`create_time_capsule`/`create_digital_will`/`create_death_oracle`) تصطدم بـ`IntegrityError: duplicate key value violates unique constraint` **غير مُعالَج في الكود إطلاقًا** → `500 Internal Server Error` مباشر. **مؤكَّد حيًا** (`GET /digital-twin/config` بهيدر تينانت مختلف عن أول إنشاء ناجح → `500`، تتبُّع اللوج أكَّد `UniqueViolationError` بالحرف). **هذا ليس IDOR** — على العكس، القيد على مستوى الـDB هو اللي **يمنع** تسرّب/تلوّث بيانات كان مفروض يحصل لولاه (راجع §5.3 من تقرير `digital-twin-idor-fix`) — لكنه **باج وظيفي كامل**: حتى مستخدم شرعي 100% بيحاول ينشئ توأم/خزنة/وصية/أوراكل تاني بالخطأ (أو بعد أي سيناريو استرجاع/إعادة محاولة) هيصطدم بـ`500` غير مفهوم بدل رسالة خطأ واضحة. **صفر لمس/إصلاح — خارج نطاق جلسة `digital-twin-idor-fix` صراحة** (كانت مخصَّصة للجذر IDOR فقط، بتوجيه صريح من المستخدم). نفس فئة `constructor-mismatch`/schema-drift الأخرى في هذا الجدول — يستحق معالجة منفصلة (إما `try/except IntegrityError` مع رسالة واضحة "التوأم/الوصية موجودة بالفعل"، أو مراجعة تصميمية: هل القيد العالمي على `user_id` مقصود أصلًا في نظام متعدد المستأجرين؟). | 🟡 **مفتوح، لم يبدأ** — إصلاح محلي (معالجة الاستثناء + رسالة واضحة، أو مراجعة القيد نفسه) — صفر سبب جذري مشترك مع أي دومين آخر | `.claude/reports/digital-twin-idor-fix-session-log.md` §5.3 |

| — | **`academy-enroll-hardcoded-receiver-email`** [2026-08-24] — اكتُشف بالقراءة الثابتة أثناء جلسة `academy-idor-fix` (`academy/service.py:347-354`، `enroll_in_course`، الدفع `WALLET`): `finance.transfer(receiver_email="academy@eppne.com", ...)` — بريد مستلم ثابت هاردكودد، بلا أي إعداد لكل تينانت. **نفس فئة `projects-add-contribution-hardcoded-receiver-email` أعلاه بالضبط:** `FinanceService.transfer` بتفلتر `get_by_email(receiver_email, self.tenant_id)` + تتأكد `receiver.tenant_id == self.tenant_id` — يتطلب مستخدم حقيقي بريده بالحرف `academy@eppne.com` **داخل كل تينانت على حدة**، وفشل آمن (`NotFoundError`) لو غير موجود. **بعكس حالة `projects` قبل إصلاحها، هنا `tenant_id` كان أصلًا (وقبل هذه الجلسة) موثوقًا 100%** (`current_user.tenant_id`، لا علاقة له بالثغرات الأربعة المُصلَحة في هذه الجلسة) — يعني **صفر مسار استغلال عبر-تينانت حتى نظريًا**، أضعف حتى من نظيره في `projects`. **لم يُستدعَ حيًا** (بقرار متعمَّد، نفس معاملة `projects`/`commerce`). **صفر إصلاح كود — مرجع/توثيق فقط.** | 🟢 **مرجع فقط — أضعف حالة في هذه العائلة، مصدر التينانت موثوق أصلًا قبل هذه الجلسة** | `.claude/reports/academy-idor-fix-session-log.md` §1 |

| — | **`social-group-model-missing-idempotency-key-column`** [2026-08-24] — اكتُشف أثناء التحقق الحي لجلسة `social-media-idor-fix`: `SocialService.create_group()` كانت بتمرر `idempotency_key=idempotency_key` لـ`SocialRepository.create_group(**kwargs)` → `SocialGroup(**kwargs)`، لكن موديل `SocialGroup` (`social/models.py`) هو **الوحيد بين كل موديلات دومين `social` اللي معندوش عمود `idempotency_key`** (تأكيد `grep` شامل: كل موديل تاني بيدعم idempotency عنده العمود — `Post`, `PostComment`, `PostLike`, `GroupMember`, `SocialSmartContract`, `ContractSignature`, `EventAttendee`, `UserConnection`, `DigitalGift`, `PhysicalGiftRequest`, `GroupSubscription`). **مؤكَّد حيًا: `TypeError: 'idempotency_key' is an invalid keyword argument for SocialGroup`، فوري، لأي `POST /social/groups` بلا استثناء** (قبل الإصلاح). **الإصلاح المُطبَّق فعليًا في نفس الجلسة (نطاق كود بحت، صفر migration):** حذف تمرير `idempotency_key` من الاستدعاء — الحماية الحقيقية من التكرار موجودة أصلًا عبر Redis idempotency cache (`_validate_idempotency`/`_store_idempotency`)، مش عبر عمود الموديل. **قرار مفتوح، خارج نطاق هذه الجلسة:** هل يستحق `SocialGroup` عمود `idempotency_key` فعلي (زي بقية الموديلات، بحماية DB-level ضد race conditions) — يحتاج migration منفصلة، قرار معماري لاحق. | 🟢 **مُغلَق جزئيًا** — الكراش الفوري اتصلح (كود)، القرار المعماري (عمود DB) لسه مفتوح | `.claude/reports/social-media-idor-fix-session-log.md` §6.1 |

| — | **`social-hardcoded-shop-email-not-registered`** [2026-08-24] — اكتُشف أثناء التحقق الحي لجلسة `social-media-idor-fix` (اختبار ضبط لـ`request_physical_gift` بعد إضافة فحص المستلم): `SocialService.request_physical_gift()` بتنادي `finance.transfer(receiver_email="shop@eppne.com", ...)` — بريد مستلم ثابت هاردكودد (نفس فئة `academy-enroll-hardcoded-receiver-email`/`projects-add-contribution-hardcoded-receiver-email` أعلاه)، لكن **الحساب `shop@eppne.com` غير موجود في الـDB المحلي** (`FinanceService.transfer` بترجع `NotFoundError: "المستلم غير موجود"`). **مؤكَّد حيًا:** طلب شرعي 100% (نفس التينانت، فحص المستلم الجديد اجتاز بنجاح) اصطدم بهذا الخطأ **بعد** تجاوز فحص `receiver_id` الجديد بنجاح — يثبت إن الفحص الجديد نفسه سليم ولا يرفض خطأً، والخطأ مصدره منطق منفصل تمامًا. **نفس فئة "حساب نظام هاردكودد" الموثَّقة في `critical-finding-xtenant-systemic.md`** لـ`commerce.release_commissions`/`affiliate.withdraw_commissions`/`iot.settle_carbon_credits`/`social.subscribe_group_to_plan` (`sender_id=0`/`sender_id=1`) — هنا نفس الفئة لكن كمستلم ثابت (`receiver_email`) بدل `user_id` هاردكودد، ولكل تينانت (مش تينانت1 بس). **صفر لمس/إصلاح — خارج نطاق جلسة `social-media-idor-fix` صراحة، توثيق فقط.** | 🟡 **مفتوح، لم يبدأ** — يمنع `request_physical_gift` بالكامل من الوصول لمرحلة النجاح لأي تينانت؛ يحتاج حساب متجر حقيقي لكل تينانت أو آلية "حساب نظام" رسمية (نفس القرار المعماري المؤجَّل لعائلة `sender_id=0/1` بالكامل) | `.claude/reports/social-media-idor-fix-session-log.md` §6.4 |

| — | **`realestate-masterplanexplorer-decimal-fields-returned-as-string`** [2026-08-29] —
  اكتُشف حيًا أثناء تنفيذ المرحلة الأولى من جلسة
  `realestate-hooks-nonexistent-imports` (تصحيح استيراد `getMyLands` في
  `components/realestate/MasterPlanExplorer.tsx` من الكائن الحقيقي
  `RealEstateService` بدل استيراد اسمي فاشل — راجع البند
  `realestate-hooks-layer-nonexistent-function-imports` أعلاه للسياق
  الأصلي). بمجرد ما الاستيراد بقى صحيح وظهر النوع الحقيقي، تبيّن إن
  `LandAssetResponse.area_sqm` و`current_value_mrusdt` **مُصرَّح عنهم
  `string` فعليًا** في الـOpenAPI schema المولَّدة (`src/lib/api-types.ts`
  سطر 11643/11652 — تأكيد حي، مش افتراض)، لكن `MasterPlanExplorer.tsx`
  (سطور 68، 73) بينادي `.toFixed()` مباشرة عليهم — لو الشكل الحقيقي وقت
  التشغيل فعلًا `string`، ده هيرمي `TypeError: toFixed is not a function`
  **لأي مستخدم يفتح الصفحة**. الباج كان موجود من الأول في الكود، لكن
  مخفي بالكامل بسبب فشل استيراد `getMyLands` الأصلي (كان بيخلي النوع
  `any` فـTS ماكانش بيتحقق من `.toFixed()`). **صفر إصلاح — القرار مؤجَّل
  عمدًا، خارج موافقة المرحلة الأولى الحالية:** هل التصحيح frontend-only
  (`Number(land.area_sqm).toFixed(0)`)، ولا مراجعة أوسع لليه Decimal
  بيتسلسل كـstring في الـschema بدل number (قرار قد يمس كل حقول Decimal
  في المشروع، مش بس `realestate`)؟ | 🟡 **مفتوح، لم يبدأ — قرار تصميمي
  معلَّق (frontend `Number()` مقابل مراجعة تسلسل الـschema بالباك إند)**
  | `.claude/reports/realestate-hooks-nonexistent-imports-session-log.md` خطوة 11 |

| — | **`realestate-tokenizationexchange-decimal-fields-returned-as-string`** [2026-08-29] —
  نفس فئة `realestate-masterplanexplorer-decimal-fields-returned-as-string`
  أعلاه بالضبط، اكتُشف بنفس الطريقة وفي نفس جلسة
  `realestate-hooks-nonexistent-imports` (تصحيح استيراد
  `getUnitsForSale`/`buyFraction` في
  `components/realestate/TokenizationExchange.tsx`):
  `PropertyUnitResponse.sale_price_mrusdt` مُصرَّح `string | null` فعليًا
  (`src/lib/api-types.ts` سطر 14296). سطر 67 بينادي `.toFixed()` عليه
  مباشرة (هيكسر وقت التشغيل فعليًا)، وسطر 96 بيعمل عملية حسابية
  (`unit.sale_price_mrusdt * percentage`) عليه — دي فعليًا هتشتغل وقت
  التشغيل بفضل تحويل JS التلقائي للنوع، لكن TS بيرفضها كـtype error.
  **نفس القرار التصميمي المعلَّق في البند فوق ينطبق هنا حرفيًا** — صفر
  إصلاح. | 🟡 **مفتوح، لم يبدأ — نفس القرار المعلَّق في البند أعلاه**
  | `.claude/reports/realestate-hooks-nonexistent-imports-session-log.md` خطوة 11 |

| — | **`realestate-ownerships-page-current-value-field-mismatch`** [2026-08-29] —
  اكتُشف حيًا كتأثير تسلسلي (ripple effect) من إصلاح معتمَد ومُنفَّذ فعليًا
  (`hooks/realestate/useMyOwnerships.ts`، استيراد صحيح لـ
  `RealEstateService.getMyOwnerships`، جزء من المرحلة الأولى المكتملة
  لجلسة `realestate-hooks-nonexistent-imports`): `app/(dashboard)/realestate/ownerships/page.tsx`
  (سطور 32، 84، 87) بيستخدم نفس الهوك، وكان مفترض إن نتيجته فيها حقل
  `current_value` (موجود بس في النوع المحلي `Ownership` بـ
  `types/realestate.ts`)، لكن النوع الحقيقي الراجع من الباك إند
  (`OwnershipResponse`، `schemas.py` سطر 65-73) **مفيهوش هذا الحقل
  إطلاقًا**. هذا الملف لم يكن من ضمن الـ10 ملفات المحقَّق فيها أصلًا في
  الجلسة — اكتشاف حادي عشر ظهر فقط بعد إصلاح `useMyOwnerships.ts`
  المعتمَد، مش تعديل مباشر عليه. **صفر إصلاح — قرار مؤجَّل:** هل
  `current_value` (القيمة الحالية المقدَّرة للملكية) ميزة حقيقية لازم
  تُبنى بالباك إند (تحتاج منطق تقييم/تسعير حي)، ولا الحقل ده كان افتراض
  غلط في الفرونت إند من الأول ولازم يتشال من `Ownership` type ومن
  الصفحة؟ | 🟡 **مفتوح، لم يبدأ — قرار منتجي معلَّق (بناء ميزة تسعير حي،
  ولا حذف افتراض غلط)** | `.claude/reports/realestate-hooks-nonexistent-imports-session-log.md` خطوة 11 |

| — | **`realestate-ownershipresponse-missing-created-at-vs-frontend-type`** [2026-08-29] —
  اكتُشف حيًا أثناء تنفيذ المرحلة الأولى لجلسة
  `realestate-hooks-nonexistent-imports` (إصلاح `buyFractionalOwnership`
  → `RealEstateService.buyFraction` في
  `components/realestate/TokenizationExchange.tsx`، وإزالة unwrap
  `response.data`): بمجرد ما نوع الاستدعاء بقى صحيح، ظهر type mismatch
  حقيقي كان مخفي بالكامل بسبب فشل الاستيراد الأصلي (كان بيخلي النوع
  `any`). `RealEstateService.buyFraction` بيرجع `OwnershipResponse`
  (النوع المولَّد من الباك إند، `schemas.py` سطر 65-73:
  `id, unit_id, owner_user_id, ownership_percentage, acquisition_date,
  deed_nft_token_id?, purchase_tx_hash?`) — **مفيهوش `created_at`
  إطلاقًا**. لكن `store/realestateStore.ts`
  (`addOwnership: (ownership: PropertyOwnership) => void`) بيتوقع النوع
  المحلي `PropertyOwnership` (`types/realestate.ts`) واللي فيه
  `created_at: string` **إجباري (مش اختياري)**. **الحل المؤقَّت المُطبَّق
  فعليًا الآن** (frontend-only، أقل تدخل، **مش حل جذري**): type
  assertion صريح `response as unknown as PropertyOwnership` في
  `TokenizationExchange.tsx` (سطر `onSuccess`) بدل تعديل
  `store/realestateStore.ts` أو `types/realestate.ts`. **صفر إصلاح جذري
  — القرار مؤجَّل:** هل `created_at` لازم يتضاف كحقل فعلي لـ
  `OwnershipResponse` schema بالباك إند (لو الـDB فيها العمود أصلًا
  بـSQLAlchemy default لكن الـschema مش عارضاه)، ولا `created_at` يتشال
  من كونه إجباري في `PropertyOwnership` بالفرونت إند (يبقى اختياري أو
  يتحذف لو مش مُستخدَم فعليًا في أي مكان)؟ **لما القرار يُتَّخذ، الـtype
  assertion المؤقَّت في `TokenizationExchange.tsx` لازم يترجع/يتشال —
  مش حل نهائي، مجرد تسكين مؤقت لعبور الـcompile.** | 🟡 **مفتوح، لم يبدأ
  — حل مؤقت (type assertion) قائم حاليًا في `TokenizationExchange.tsx`،
  يحتاج تراجع عند حسم القرار** | `.claude/reports/realestate-hooks-nonexistent-imports-session-log.md` خطوة 10 |
| — | **`arbitration-syndicates-repository-27-remaining-methods`** [2026-08-29] —
  إكمال بند Backlog #27 (`arbitration-syndicates-repository-missing-methods`)
  بالكامل: 6/6 دوال `repository.py` مفقودة/بتوقيع غلط (`list_user_licenses`,
  `list_candidates`, `list_syndicate_elections` [دالة سادسة اكتُشفت أثناء
  التحقيق — كانت السبب الفعلي الوحيد لعطل `GET /syndicates/{id}/elections`،
  مش من الخمسة المذكورين أصلًا في وصف البند]، `get_election_votes`,
  `get_syndicate_memberships` [+ تعديل نداء `service.py:join_syndicate` عشان
  يمرر `tenant_id` كمان — كان بيمرر `syndicate_id` بس]) + حذف الكود الميت
  `get_cases_by_claimant` (شرط `hasattr` في `service.py` كان بيختار
  `list_user_cases` الصحيحة دايمًا، فالفرع التاني مالوش أي مسار تنفيذ حي).
  كل دالة فُلترت بـ`tenant_id` فعليًا من أول تنفيذها ومؤكَّدة حيًا (مسار
  شرعي + مسار هجوم عبر تينانتين حقيقيين `1`/`16` + تنظيف)، **صفر IDOR
  اتلقى أثناء الإصلاح في أي من الست دوال.**
  **تمييز دقيق مهم لـ`list_candidates` تحديدًا (الأعلى خطورة كامنة في
  البند):** ماكانتش بتسرّب بيانات فعليًا في أي وقت — كانت بترمي
  `TypeError` (مؤكَّد `500 Internal Server Error` عبر اختبار HTTP
  end-to-end حقيقي) **لأي طلب على الإطلاق، بصرف النظر عن هوية الطالب** —
  المالك الشرعي والمهاجم كانا ياخدوا نفس العطل بالظبط، صفر بيانات لأي
  حد. الخطورة كانت **افتراضية بحتة**: لو الإصلاح اقتصر على تمرير
  `tenant_id` للدالة (لحل الـ`TypeError`) بلا استخدامه فعليًا في
  `WHERE`، كان هيتولد IDOR حقيقي من لحظة نشر هذا الإصلاح الساذج تحديدًا
  — لكن هذا لم يحدث؛ الإصلاح المُطبَّق فلتر بـ`tenant_id` من أول تعديل
  واحد. **لا تُقرأ هذه الفقرة على إنها "IDOR اتصلح" بالمعنى اللي بيوحي
  بتسريب فعلي تاريخي — النمط مختلف جوهريًا عن `list_user_cases` (المُصلَحة
  سابقًا 2026-08-26، راجع صف #6 في `critical-finding-xtenant-systemic.md`)
  حيث الثغرة كانت غياب فلترة فعلي وليس عطل شامل لكل الطلبات.** | ✅
  **مُغلَق بالكامل [2026-08-29]** | `.claude/reports/arbitration-syndicates-repository-27-session-log.md`,
  `.claude/reports/arbitration-syndicates-repository-27-post-execution-confirmation.md` |
| — | **`realestate-rent-tokenize-missing-ownership-check`** [2026-08-29] —
  اكتُشف عرضًا أثناء تحقيق أمني منفصل (سؤال أصلي: هل `buyFraction`/
  `tokenizeAsset` بتثق بـamount جاهز من الفرونت إند؟ — الإجابة: لأ، آمن،
  السيرفس بتحسب المبلغ بنفسها من `Decimal` في الـDB، راجع نفس التقرير).
  أثناء فحص `rent_unit` كجزء من نفس السؤال، ظهر بج أمني أخطر تمامًا
  ومنفصل: **`RealEstateService.rent_unit()` و`.tokenize_asset()` كانتا
  بتقبلوا هوية الـcaller نفسه كـ`landlord_id`/`initiator_id` من غير أي
  تحقق إنه فعلاً مالك الوحدة** (عبر سلسلة unit → development →
  land_asset → owner_id). أي مستخدم authenticated كان يقدر: (أ) يعمل
  `POST /realestate/rentals` لأي `unit_id`، ينصب نفسه landlord، ويحدد
  `monthly_rent_mrusdt` كيفما شاء — وده بيولّد invoice حقيقي ضد
  `tenant_user_id`. (ب) يعمل `POST /realestate/tokenize/{unit_id}` لأي
  وحدة مش بتاعته بأي `share_price_mrusdt`. **الإصلاح المُطبَّق:** تحقق
  `owner.id == landlord_id`/`initiator_id` (عبر helper موجود بالفعل
  `_get_land_owner_for_unit`، نفس النمط المستخدَم في
  `buy_fractional_ownership`) → `PermissionDeniedError` (403) عند عدم
  التطابق. **تحقق حي كامل 100% لكلا الدالتين** (مسار شرعي ينجح فعليًا +
  مسار هجوم يترفض بـ403 مؤكَّد بالرسالة الدقيقة + SELECT مستقل يثبت صفر
  مورد اتسجل للمهاجم)، عبر ملفي اختبار جديدين:
  `test_realestate_rent_unit_ownership_check.py`،
  `test_realestate_tokenize_asset_ownership_check.py`. Commit `ed3af4f`. | ✅
  **مُغلَق بالكامل ومتحقَّق حيًا [2026-08-29]** | `.claude/reports/realestate-buyfraction-amount-trust-check-session-log.md` |
| — | **`realestate-asset-tokenizations-token-symbol-too-narrow`** [2026-08-29] —
  اكتُشف حيًا (مش أمني — باج وظيفي بحت) أثناء التحقق من إصلاح
  `tokenize_asset` أعلاه (بند منفصل تمامًا، وثّقته هنا لوحده عشان يكون
  قابل للعثور عليه بمعزل عن السياق الأمني): `AssetTokenization.token_symbol`
  كان `VARCHAR(10)` (`models.py`)، بينما `RealEstateService.tokenize_asset()`
  بتولّد القيمة بصيغة `f"EPPNE-RE-{unit_id}-{uuid.uuid4().hex[:4].upper()}"`
  — دايمًا 15+ حرف (حتى `unit_id` برقم واحد). **النتيجة: أي استدعاء
  حقيقي لـ`tokenize_asset` — بغض النظر تمامًا عن هوية الـcaller أو صحة
  أي تحقق ownership — كان بيفشل بـ`StringDataRightTruncationError` عند
  الـINSERT.** مؤكَّد حيًا (رسالة الخطأ الكاملة موثَّقة في التقرير).
  **الإصلاح المُطبَّق (بموافقة صريحة، نطاق موسَّع عن الطلب الأصلي):**
  migration جديدة `041_widen_asset_tokenizations_token_symbol.py`
  (`VARCHAR(10)` → `VARCHAR(30)`) + تحديث `models.py` مطابق، اتنفذت فعليًا
  (`alembic upgrade head`). **تحقق حي بعد الـmigration:** إعادة تشغيل
  `test_tokenize_asset_succeeds_for_real_owner` نجحت للنهاية الطبيعية
  (`AssetTokenization` اتسجلت فعليًا، اتأكد بـSELECT مستقل). Commit
  `ed3af4f` (نفس commit إصلاح الـownership، موثَّق كبند منفصل هنا). | ✅
  **مُغلَق بالكامل ومتحقَّق حيًا [2026-08-29]** | `.claude/reports/realestate-buyfraction-amount-trust-check-session-log.md` |
| — | **`insurance-review-claim-issuer-entity-id-reviewer-id-mismatch`**
  (Backlog #41) [2026-08-29] — بند كان موثَّقًا مسبقًا بتحذير أمني صريح
  في `constructor-mismatch-backlog-classification.md` ("الإصلاح الساذج
  قد يفتح ثغرة صلاحية مختلفة"، نفس نمط تحذير `sovereign_entities`/#32).
  **الفحص المُكتشَف قبل الإصلاح** (`insurance/service.py:431`):
  `if policy.issuer_entity_id != reviewer_id: raise PermissionDeniedError`
  — يقارن مفتاح أساسي لجدول `sovereign_entities_v2` (`issuer_entity_id`)
  مقابل مفتاح أساسي لجدول `users` (`reviewer_id`)، **مساحتا معرِّفات
  مختلفتان تمامًا رياضيًا**، فوق بوابة راوتر منفصلة تمامًا
  `get_current_superuser` (دور منصة عالمي `system_role`، لا علاقة له
  بعضوية الكيان المُصدِر). **تحقيق حي قاطع [جلسة
  `insurance-41-review-claim-permission-check`] أثبت التصنيف الدقيق:**
  استدعاء حي مباشر للفحص الأصلي غير المُعدَّل بأقرب تعريف ممكن لمراجع
  شرعي (مستخدم `system_role=SUPER_ADMIN` **و** عضو `EntityMembership`
  حقيقي بدور `OWNER` على نفس الكيان) رجع **نفس رسالة الرفض بالحرف**
  اللي رجعتها لمستخدم عشوائي مالوش أي علاقة بالكيان إطلاقًا. **هذا
  التمييز مهم لأي مراجعة لاحقة للسجل: البند لم يكن `broken-open`
  (ثغرة صلاحية تسمح لغير المخوَّل — القلق الأصلي المسجَّل وقت اكتشاف
  البند) — كان `broken-closed` (الميزة معطّلة بالكامل، تمنع حتى
  المخوَّل الحقيقي 100% من حالات الاستخدام الواقعية). صفر دليل على أي
  استغلال فعلي أو تسريب بيانات تاريخي — العطل كان شاملًا لكل الطلبات
  بصرف النظر عن هوية المستخدم، مطابق لنفس نمط التمييز المسجَّل سابقًا
  في بند `arbitration-syndicates-repository-27-remaining-methods`
  أعلاه (`list_candidates`) لكن بسياق صلاحيات مختلف تمامًا (هناك
  `TypeError` شامل، هنا مقارنة IDs بلا معنى منطقي شاملة).**
  **الإصلاح المُطبَّق (بموافقة مستخدم صريحة على كل قرار):** استبدال
  المقارنة بفحص `EntityMembership` حقيقي (`entity_type="SOVEREIGN_ENTITY"`,
  `role in [OWNER, EXECUTIVE_DIRECTOR]`) — نفس نمط
  `_is_authorized_representative`/`deposit_to_entity_wallet` الموجود
  فعليًا في `sovereign_entities/service.py`. + إزالة بوابة
  `get_current_superuser` من الراوتر (بلا علاقة منطقية بعضوية الكيان،
  كانت ستُبقي الفحص الجديد الصحيح غير قابل للتفعيل عمليًا) → استُبدلت
  بـ`get_current_active_user`، والـ`EntityMembership` أصبح الحارس
  الوحيد والكافي — مطابق تمامًا لنمط بقية endpoints `sovereign_entities`
  (لا بوابة `system_role` مكدَّسة فوق فحص العضوية في أي منها). **تحقق
  حي كامل بعد الإصلاح لكلا المسارين** (عبر استدعاء مباشر للـservice
  method الحقيقية، DB حقيقية، صفر mock): عضو `OWNER` حقيقي → نجح فعليًا
  (claim → `REJECTED`، تأكيد `SELECT` مستقل من session منفصلة)؛ عضو
  `REPRESENTATIVE` حقيقي (عضوية فعلية لكن دور غير كافٍ) → لسه بيترفض
  بـ403، **يثبت إن الإصلاح واعٍ بالدور (`role-aware`) مش مجرد "أي
  عضوية كافية"** — بالضبط نقيض التحذير الساذج المسجَّل مسبقًا عند
  اكتشاف البند. Commit `99253e3`. | ✅ **مُغلَق بالكامل ومتحقَّق حيًا
  [2026-08-29]** | `.claude/reports/insurance-41-review-claim-permission-check-session-log.md`,
  `.claude/reports/constructor-mismatch-backlog-classification.md` (صف #41 محدَّث) |
| 29 | **`finance-service-hold-funds-missing`** [2026-08-29] — `tenders_auctions/service.py`
  كانت بتنادي `finance.hold_funds()`/`finance.release_held_funds()` بمعاملات
  `# type: ignore[attr-defined]` — `FinanceService` ما كانتش عندها الدالتين دول
  إطلاقًا (فقط `transfer()`/`swap()`/`mint_currency()`). أي `place_bid`/`close_auction`
  حقيقي كان بيفشل `AttributeError`. **بحث حي شامل أكَّد:** الاسمان مستخدَمان فقط
  في `tenders_auctions`، لا يوجد نمط حجز/تحرير مشابه بأسماء مختلفة في أي دومين آخر.
  **الإصلاح المُطبَّق (بموافقة مستخدم صريحة على كل قرار تصميم):**
  (1) عمود جديد `Wallet.held_balances` (JSONB، نفس شكل `balances`، migration
  `042_add_held_balances_to_wallets.py`) + `CheckConstraint` مطابق لمنع القيم
  السالبة. (2) 3 دوال جديدة في `FinanceService`: `hold_funds` (نقل من `balances`
  لـ`held_balances`)، `release_held_funds` (عكسها)، و`settle_held_funds` **ذرّية**
  (تحرير+تحويل الفائز في `begin_nested()` واحد، تاخد من `held_balances` مباشرة
  بدون المرور بـ`balances` المتاح — تقفل نافذة خطر كانت موجودة في التصميم الأولي
  المقترَح لو استخدمنا `release_held_funds`+`transfer()` منفصلين). نفس نمط القفل
  (`get_or_create_wallet_for_update`) وidempotency (`Transaction.idempotency_key`
  الفريد) المستخدَم فعليًا في `transfer`/`swap`/`mint_currency`.
  (3) 4 إصلاحات إضافية اكتُشفت حيًا في الكولر نفسه أثناء التصميم (كانت هتسيب
  تسريب مالي حقيقي حتى لو الدالتين الناقصتين اتصلحوا لوحدهم): `get_live_bids_for_auction`
  كانت بترتب `created_at DESC` (آخر مزايدة زمنيًا) مش `bid_amount_mrusdt DESC`
  (الأعلى قيمة فعليًا) → فائز غلط محتمل؛ `close_auction` كانت بتحرر حجز الفائز
  بس، بتسيب كل المزايدات الخاسرة (وأي مزايدة سابقة للفائز نفسه لو رفع عرضه أكتر
  من مرة) محجوزة للأبد → أُصلحت بلوب يحرر حجز كل مزايدة غير فائزة؛ `idempotency_key`
  عشوائي (`uuid4()`) في استدعاء التحويل → أُصلح لمفتاح ثابت مُشتق من `auction_id`
  (`AUCTION-SALE-{id}`)؛ `release_held_funds` كانت هتُستدعى بدون `idempotency_key`
  إطلاقًا → أُضيف (`AUCTION-RELEASE-{auction_id}-{bid_id}`، فريد لكل مزايدة).
  **تحقق حي كامل** (DB حقيقي، صفر mock، `tests/test_tenders_auctions_finance_hold_release_settle.py`
  جديد ودائم): مزاد بـ3 مزايدين حقيقيين عبر `place_bid` الفعلية — الفائز
  (أعلى `bid_amount_mrusdt` فعليًا، مش آخر مزايدة زمنيًا) اتحدد صح، الخاسرون
  استرجعوا حجزهم بالكامل (`balances`/`held_balances` رجعوا لأصلهم بالظبط)،
  الفائز فضل عند نفس الرصيد بعد الحجز طول الوقت (لم يرجع لرصيده الأصلي وسط
  الطريق أبدًا — تأكيد مباشر لقفل نافذة الخطر)، حساب النظام استلم المبلغ
  الصحيح بالظبط مرة واحدة. **Retry حقيقي على `close_auction`** (استدعاء
  المزاد المُغلَق نفسه ثانية) أكَّد: صفر تحويل مزدوج، صفر تحرير حجز مزدوج
  (`Transaction` count = 1 لكل `idempotency_key` قبل وبعد الـretry). عزل بج
  `invoicing._generate_invoice_number` المنفصل تمامًا (راجع البند التالي
  المرتبط، وسجل جلسات `realestate-buyfraction`/`insurance-savepoint` لتاريخه)
  عبر `monkeypatch` داخل الاختبار فقط (نفس نمط `test_realestate_rent_unit_ownership_check.py`)
  — صفر لمس على `invoicing/service.py`. | ✅ **مُغلَق بالكامل ومتحقَّق حيًا
  [2026-08-30]** | `.claude/reports/finance-29-hold-funds-session-log.md` (كامل، يشمل
  تصميم §5 وجدول مخاطر §7)، `.claude/reports/constructor-mismatch-backlog-classification.md`
  (صف #29 محدَّث) |
| — | **`finance-transaction-idempotency-key-lookup-multiple-results-bug`**
  [2026-08-30] — اكتُشف أثناء التحقق الحي لجلسة #29 (`finance-service-hold-funds-missing`
  أعلاه)، **لكنه باج منفصل تمامًا وكان كامنًا في `transfer()` من قبل جلسة #29
  بكتير — مش نتيجة لتعديلاتها.** `TransactionRepository.get_by_idempotency_key`
  (`finance/repository.py:97-109`) كانت بتعمل `.join(User, or_(User.id==sender_id,
  User.id==receiver_id))` — لو صف `Transaction` واحد عنده **كلاهما** `sender_id`
  و`receiver_id` غير فارغين (أي معاملة بطرفين حقيقيين: `transfer()` العادية،
  وكمان `settle_held_funds()` الجديدة من #29)، الـJOIN بيتطابق **مرتين** لنفس
  الصف (مرة عبر كل عمود) → صفين متطابقين يرجعوا من الاستعلام → `scalar_one_or_none()`
  يرفع `sqlalchemy.exc.MultipleResultsFound` (500) **بدل ما يرجع نفس المعاملة
  القديمة بأمان — عكس الهدف الكامل من `idempotency_key` تمامًا.** كان كامنًا
  وغير مُلاحَظ لأن أي كولر سابق لـ`transfer()` على الأرجح ما عملش retry حقيقي
  فعلي بنفس المفتاح في اختبار حي؛ أول استدعاء حقيقي بيعمل retry فعلي على معاملة
  بطرفين (قرار #29-قسم8: `idempotency_key` ثابت مُشتق من `auction_id` بدل
  `uuid4()` عشوائي لـ`settle_held_funds`) هو اللي فجّره لأول مرة.
  **الإصلاح المُطبَّق:** استبدال الـJOIN بـ`subquery` (`Transaction.sender_id.in_(select(User.id)...)`
  أو `receiver_id.in_(...)`) — نفس شرط "الطرف بينتمي للتينانت" بدون تكرار الصف
  (`idempotency_key` عنده أصلًا `UNIQUE` index جزئي، `models.py:52`، فأقصى حاجة
  ممكنة تتطابق صف واحد بغض النظر عن الـJOIN). صفر تغيير في السلوك المقصود
  للدالة — إصلاح تنفيذي بحت. **تحقق حي مستقل مخصَّص** (`tests/test_tenders_auctions_finance_hold_release_settle.py::test_transfer_idempotency_key_retry_returns_same_transaction`،
  منفصل عن اختبارات #29): استدعاء `transfer()` حقيقي مرتين بنفس `idempotency_key`
  على معاملة بطرفين حقيقيين — رجعت نفس المعاملة (`tx1.id == tx2.id`)، صفر خصم
  مزدوج، صف `transactions` واحد فقط. | ✅ **مُغلَق بالكامل ومتحقَّق حيًا
  [2026-08-30]** | `.claude/reports/finance-29-hold-funds-session-log.md` §12 |
| — | **`frontend-services-hooks-missing-exports-multi-domain`** [2026-08-30] —
  اكتُشف أثناء جلسة `frontend-decimal-fields-standard-convention` (توحيد
  التعامل مع حقول Decimal في الفرونت إند)، أثناء تشغيل `npx tsc --noEmit`
  كـcheckpoint تحقق قبل تعديل types/*.ts: **نفس فئة الباج الموثَّقة في
  `realestate-hooks-layer-nonexistent-function-imports` أعلاه [2026-08-29]
  — لكن منتشرة في 4 دومينز إضافية على الأقل، لم تكن معروفة وقت توثيق البند
  الأصلي:**
  - `app/(dashboard)/payroll/page.tsx` و`app/(dashboard)/employment/page.tsx`:
    بيستوردوا `getMyPayrolls`, `generatePayroll`, `approvePayroll`,
    `payPayroll`, `getOpenJobs`, `getMyApplications`, `getMyContract` من
    `@/services/employment` — **غير موجودة إطلاقًا** كـnamed exports.
  - `components/projects/ProjectAnalysisDashboard.tsx`: `getProjectAnalytics`
    غير موجودة في `@/services/projects`.
  - `components/projects/MilestoneTimeline.tsx`,
    `components/projects/AdvancedMilestones.tsx`: `getProject`,
    `completeMilestone`, `releaseMilestoneFunds` غير موجودة في
    `@/services/projects`.
  - `components/ai-governance/QuotaManager.tsx`: الموديول
    `@/services/ai-governance` **غير موجود إطلاقًا** (لا الملف ولا أي export منه).
  - `app/(dashboard)/logistics/page.tsx`: الموديول `@/hooks/logistics/useStats`
    **غير موجود إطلاقًا**.
  - `app/(dashboard)/realestate/property/[id]/page.tsx`: إضافة لباج
    `realestate-hooks-layer-nonexistent-function-imports` المعروف، هذا الملف
    تحديدًا عنده أيضًا `useUpdateProperty` غير موجودة في
    `hooks/realestate/useProperties.ts` (الموجود `useCreateProperty` بس)،
    + موديولات npm مفقودة كليًا (`date-fns/ar`, `uuid` — تظهر أيضًا في
    `payroll/page.tsx` و`AdvancedMilestones.tsx`/`MilestoneTimeline.tsx`،
    قد تكون مشكلة تثبيت/lockfile منفصلة تمامًا تستاهل تحقق مستقل).
  **الأثر المباشر على جلسة Decimal:** 7 من أصل 16 موضع Decimal-as-string
  مؤكَّد وقعوا داخل هذه الملفات بالذات — بما إن الاستيراد المكسور بيخلي
  المتغيرات كلها `any` ضمنيًا، **تصحيح type أي حقل Decimal في `types/*.ts`
  لن يُظهر أي خطأ tsc جديد لهذه الـ7 حتى يُصلَح باج الاستيراد أولًا** —
  السلسلة مقطوعة قبل ما توصل لفحص النوع أصلًا. **صفر إصلاح — خارج نطاق
  جلسة Decimal صراحة، يحتاج جلسة تحقيق/اعتماد مستقلة تمامًا زي المعاملة
  بالضبط مع realestate** (هل الـservices اتكتبت ضد تصميم API قديم تغيّر،
  ولا العكس؟ قرار تصميمي قبل أي ربط ميكانيكي). | 🔴 **مفتوح، أولوية عالية
  — يعطّل الـbuild/الصفحة بالكامل لـ7+ ملفات عبر 4 دومينز (employment,
  projects, ai_governance, logistics)، أوسع نطاقًا من البند المكافئ في
  realestate** | `.claude/reports/frontend-decimal-standard-convention-session-log.md` §4.2 |
| — | **`frontend-decimal-fix-live-browser-render-unverified`** [2026-08-30] —
  في نفس جلسة `frontend-decimal-fields-standard-convention`، بعد تطبيق
  `formatDecimalString()` على 9 مواضع Decimal-as-string وتأكيدها عبر
  `tsc --noEmit` (نظيفة تمامًا) + سكريبت Node مباشر يحاكي نفس التعبيرات
  البرمجية الفعلية ببيانات Decimal-string واقعية (كل الحالات نجحت، راجع
  §4.4 من التقرير) — **التحقق الحي الكامل في متصفح فعلي (DOM حقيقي، تفاعل
  مستخدم، console errors) لم يحصل**: امتداد Chrome غير متصل بهذه الجلسة،
  وأوامر PowerShell الشبكية علّقت بلا استجابة في الـsandbox رغم إن سيرفر
  Next.js dev اتشغّل فعليًا (`localhost:3000`، تأكيد من الـlog). المستخدم
  وافق صراحة على قبول الـsnapshot Node كبديل **مؤقت** لهذه الجلسة تحديدًا
  — **مش اعتبار الفجوة مُغلَقة**. **صفر دليل بصري/DOM حقيقي حتى الآن** إن
  الـ9 مكوّنات فعليًا بترندر صح بلا كسر layout/CSS أو أخطاء console في
  متصفح حقيقي. **خطوات الإغلاق المقترَحة (بترتيب الأولوية):** (1) إعادة
  نفس التحقق في جلسة قادمة بعد ما اتصال Chrome يرجع (فتح الصفحات التسعة
  فعليًا، بمستخدم throwaway من `.claude/reports/throwaway-test-users.md`)؛
  (2) بديل أدوم: إضافة `@testing-library/react` + `vitest`/`jest`
  للمشروع (**غير مثبَّتين حاليًا إطلاقًا** — صفر إشارة في
  `eppne-web/package.json`) للرندر عبر `jsdom` بدون حاجة لمتصفح فعلي —
  قرار بنية تحتية جديد يحتاج موافقة صريحة منفصلة، مش جزء تلقائي من هذا
  البند. | 🟡 **مفتوح، أولوية متوسطة — فجوة تحقق حقيقية، مش خطأ معروف**
  | `.claude/reports/frontend-decimal-standard-convention-session-log.md` §4.4 |
| — | **`frontend-missing-exports-multidomain-scope`** [2026-08-31] —
  فحص شامل (`tsc --noEmit` كامل على `eppne-web`) أثبت إن باج "استيراد
  دوال/hooks/modules غير موجودة فعليًا" (نفس فئة
  `realestate-hooks-layer-nonexistent-function-imports`) منتشر عبر
  **~36 دومين، 175 ملف، 438 سطر خطأ** — مش محصور في الـ4 دومينات
  (employment, projects, ai_governance, logistics) الموثَّقة سابقًا في
  البند اللي فوق. السبب الجذري في كل عيّنة اتفحصت (social, transport,
  insurance, tourism-sports, agritech, employment): كل `services/
  <domain>.ts` بيصدّر كائن واحد (`export const XService = {...}`)، بينما
  الـhooks بتعمل named import مباشر. **لكن مش كل حالة نفس السبب** — من
  كل الأسماء المطلوبة المفحوصة، ~42% موجودة فعلًا كـproperty بنمط
  استيراد غلط (قابلة لإصلاح ميكانيكي)، و**~58% غير موجودة إطلاقًا تحت
  أي اسم** (فجوة تنفيذ حقيقية، بعضها بباك إند جاهز فعلًا — تأكدت من
  `openapi.json` لـagritech: `GET /agritech/agritech/farms` و
  `weather-alerts` شغّالين لكن الفرونت إند ماستدعاهمش إطلاقًا). راجع
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md`
  للتفاصيل الكاملة والجدول الكامل لكل دومين. | 🔴 **مفتوح، أولوية عالية
  — أوسع بمقياس كامل من التقدير الأصلي** |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |
| — | **`frontend-missing-exports-social-duplicate-hooks`** [2026-08-31] —
  أثناء إصلاح دومين `social` (مرحلة 1 من البند اللي فوق)، لوحظ إن
  `hooks/social/useMatchmaking.ts` و`hooks/social/useMatchSuggestions.ts`
  بيصدّروا نفس أسماء الـhooks حرفيًا (`useMatchProfile`,
  `useUpdateMatchProfile`, `useMatchSuggestions`) بمحتوى شبه مطابق. وكذلك
  `hooks/social/useConnections.ts` و`useMatchmaking.ts` بيصدّروا نفس
  `useConnections`/`useRequestConnection`/`useAcceptConnection`/
  `useRejectConnection`. `useRequestConnection` (من useMatchmaking.ts)
  **مالوش أي مستهلك `.tsx` إطلاقًا** — hook ميت. **صفر لمس** — قرار "أي
  ملف الأصلي وأيهم يتحذف" مؤجَّل لجلسة تصنيف أولويات منفصلة. | 🟡 **مفتوح،
  أولوية منخفضة — تكرار كود، مش كسر وظيفي** |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |
| — | **`transport-vehicles-hook-file-wrong-content`** [2026-08-31] —
  أثناء نفس المرحلة على دومين `transport`،
  `hooks/transport/useVehicles.ts` طلع تعليقه الأول
  `// hooks/transport/useTrips.ts` ومحتواه نسخة شبه كاملة من hooks
  الرحلات (trips) — **صفر كود مركبات فيه إطلاقًا**. الصفحات
  (`vehicles/page.tsx`, `trips/page.tsx`, `fleets/page.tsx`) بتستورد
  `useVehicles`, `useCreateVehicle`, `useDeleteVehicle`,
  `useAvailableVehicles` من نفس المسار — **مش موجودين في أي ملف في
  الكود كله**. ميزة "المركبات" في الفرونت إند معدومة بالكامل من الجذر،
  رغم إن `TransportService` في `services/transport.ts` عنده فعلًا
  `createVehicle`, `updateVehicleLocation`, `getAvailableVehicles` جاهزين
  ومُنفَّذين. **صفر لمس** — يحتاج جلسة تصميم/تنفيذ منفصلة (كتابة كود
  hooks مركبات جديد بالكامل، مش إصلاح استيراد). | ✅ **مُغلَق [2026-09-05]،
  جلسة `transport-vehicles-drivers-feature-build`** — أُعيد كتابة
  `useVehicles.ts` بالكامل (list/vehicle واحدة/available/create/update/
  delete/location) + بُنيت الـendpoints الناقصة بالباك إند، مُتحقَّق حيًا
  بـ7 pytest ضد DB حقيقية |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md`،
  `.claude/reports/transport-vehicles-drivers-session-log.md` |
| — | **`transport-formdata-vs-openapi-schema-mismatch`** [2026-08-31] —
  بعد إصلاح استيراد `createDelivery`/`createRoute` (فئة "نمط استيراد
  غلط") في نفس مرحلة transport، ظهر TS2345 جديد كان مخفيًا: `DeliveryFormData`
  و`RouteFormData` اليدويتين في `types/transport.ts` غير متوافقتين مع
  الـschema الحقيقي المولَّد من الباك إند — حقول زي `pickup_address`,
  `dropoff_address`, `waypoints` معرَّفة في الباك إند كـ`dict`/`list[dict]`
  بدون Pydantic model فرعي، فطلعت `Record<string, never>` في
  `api-types.ts` (غير قابلة عمليًا لأي كائن حقيقي بحقول). كمان
  `DeliveryTaskCreate` محتاج `sender_id: number` مطلوب مش موجود في
  `DeliveryFormData` إطلاقًا. **صفر لمس** — `useDeliveries.ts:42` و
  `useRoutes.ts:27` سايبينهم بالحالة دي عمدًا (لا type assertion ترقيعي
  ولا إصلاح schema). محتمل نفس النمط يتكرر في دومينات تانية فيها
  `*FormData` يدوي في `types/<domain>.ts`. أيضًا اكتُشف بالمصادفة:
  `trip.driver_name` مستخدَم في `trips/page.tsx:88,320` لكن مش موجود في
  `TripResponse` الحقيقي إطلاقًا (بس `driver_id` موجود) — نفس فئة
  المشكلة، على جانب القراءة مش الكتابة. | 🟡 **مفتوح، أولوية متوسطة —
  يحتاج قرار: إصلاح schema الباك إند أم ترقيع frontend** |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |
| — | **`transport-trips-page-driver-display-and-cancel-trip-missing`**
  [2026-09-05] — اكتشاف جانبي أثناء جلسة
  `transport-vehicles-drivers-feature-build` (بناء `useDrivers.ts` كشف
  الباج ده، مش سببه): **مرتبط مباشرة ببند `transport-formdata-vs-openapi-
  schema-mismatch` فوق** (نفس الصفحة `trips/page.tsx`، نفس فئة "قراءة حقل
  غير موجود")، لكنه موضع مختلف: `trips/page.tsx:168` بيحاول يقرأ
  `driver.name` من عنصر قائمة السائقين (مش `trip.driver_name` بتاع البند
  التاني) — `DriverResponse` (النوع الجديد من هذه الجلسة، مطابق تمامًا
  لـ`schemas.py` الفعلي) بيعرض `username`/`email`/`name_ar`/`name_en` بس،
  صفر حقل `name`. **مؤكَّد حيًا بـ`tsc`**: كان الخطأ قبل هذه الجلسة
  "Cannot find module '@/hooks/transport/useDrivers'" (module كان معدوم)،
  وبعد ما اتبنى الملف صح، تحوَّل لخطأ أوضح "Property 'name' does not
  exist on type ...DriverResponse". **بالإضافة:** نفس الصفحة فيها
  `useCancelTrip` مستوردة من `useTrips.ts` لكن غير مُصدَّرة منها إطلاقًا
  (`TS2305`) — الصفحة معطوبة ببواقي أخطاء أخرى غير مرتبطة كمان، مش جاهزة
  للعمل ككل. **صفر لمس** — خارج نطاق هذه الجلسة (كانت مقصورة على
  vehicles/fleets/drivers، مش trips). | 🔴 **مفتوح، أولوية متوسطة —
  الصفحة معطوبة ببواقي أخطاء متعددة، يحتاج جلسة تصميم/تنفيذ منفصلة لـ
  trips/page.tsx كاملة** |
  `.claude/reports/transport-vehicles-drivers-session-log.md` |
| — | **`frontend-hooks-misplaced-files-phase2-warning`** [2026-08-31] —
  أثناء إصلاح transport، اتكشف إن `hooks/useFleets.ts` و`hooks/useHubs.ts`
  كانوا موجودين فعليًا (بمحتوى سليم ومطابق لاسمهم) لكن في `hooks/`
  مباشرة بدل `hooks/transport/` — الصفحات كانت بتستوردهم بمسار
  `@/hooks/transport/useFleets`/`useHubs` فيطلع `TS2307: Cannot find
  module`. كانوا متصنَّفين في الفحص الشامل الأول (بند
  `frontend-missing-exports-multidomain-scope` فوق) كـ"موديول غير موجود
  إطلاقًا" — **تصنيف غلط**، الملفات كانت موجودة وبس في مكان غلط. تم
  إصلاحهم فعليًا بـ`git mv` (صفر أثر جانبي، تأكدت بـgrep إن محدش بيستورد
  من المسار القديم). **تحذير منهجي لأي جلسة مرحلة 2 قادمة:** قبل تصنيف
  أي حالة TS2307 (`@/hooks/...`, `@/components/...`) كـ"ميزة معدومة"
  نهائيًا في جدول التوثيق، **لازم تتأكد بـ`find`/`Glob` من عدم وجود
  الملف في مكان تاني بمحتوى مطابق** — قد يكون مجرد نقل ملف، مش كتابة
  كود جديد. | 🟢 **الجزء المُنفَّذ (نقل الملفين) مغلَق ومُتحقَّق منه —
  التحذير المنهجي نفسه مفتوح لحد ما يتطبَّق على باقي الـ34 دومين** |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |
| — | **`frontend-missing-exports-category-c-path-fixes`** [2026-08-31] —
  تطبيقًا لتحذير `frontend-hooks-misplaced-files-phase2-warning` (فوق)،
  اتفحصت كل الـ37 حالة `TS2307` الداخلية الباقية عبر المشروع كله
  (`Glob` لكل basename + قراءة أي تطابق مرشَّح). طلع **8 منها فئة "ج"
  جديدة** (الملف موجود فعلًا، بس بمسار/اسم مختلف تمامًا عن المتوقَّع):
  `@/services/{academy,ai-agents,commerce,communications,digital-twin,
  health}` كلها موجودة فعليًا بلاحقة `.service.ts` (`academy.service.ts`
  إلخ) — بعض المستهلكين (`store/agentStore.ts`,
  `app/(dashboard)/communications/mail/inbox/page.tsx`) كانوا بيستوردوا
  صح بالفعل، وهذا أثبت الاتفاقية الصحيحة موجودة أصلًا في نفس الكودبيز.
  `@/store/aiAgentStore` (+ اسم `useAIAgentStore`) الصح فعليًا
  `@/store/agentStore` (+ `useAgentStore`) — تأكدت بقراءة المحتوى (نفس
  الميزة بالضبط: بيستورد من `ai-agents.service`، بيدير agents/approvals).
  `@/hooks/saas` (استيراد barrel لـ`useServices`/`useSubscriptions`)
  الملفات موجودة منفصلة (`hooks/saas/useServices.ts` إلخ) بلا
  `index.ts` — **نفس الملف** (`app/(dashboard)/saas/page.tsx`) كان
  بيستورد `useInvoices`/`useDashboardStats` بمسار مباشر صح في نفس
  الوقت. **الإصلاح المُطبَّق: تصحيح مسار/اسم الاستيراد في 18 ملف
  مستهلِك فقط — صفر لمس على أي `service.ts`/`store.ts`، صفر تغيير
  منطق.** تحقق `tsc`: صفر `TS2307` متبقٍ لأي من الـ8. **متوقَّع وموثَّق
  (مش مُصلَح):** بمجرد تصحيح المسار، ظهر TS2305/2339/2459/2551 جديد في
  7 دومينات (academy, ai-agents, commerce, communications, digital-twin,
  health, saas) — نفس فئة الباج الأصلية (استيراد named ضد كائن واحد أو
  أسماء مش متطابقة)، أوسعها فجوة `saas` (نمط تسمية `get*`/`list*` مختلف
  تمامًا بين الـhooks والـservice الفعلي). هذه الاكتشافات الجديدة نقطة
  بداية جاهزة لجلسات هذه الـ7 دومينات القادمة، **صفر إصلاح إضافي في هذه
  الجلسة**. | 🟢 **مُغلَق (تصحيح المسار نفسه) — الاكتشافات الجديدة
  المتفرعة عنه مفتوحة كبداية لجلسات دومينات مستقبلية منفصلة** |
  `.claude/reports/frontend-missing-exports-multidomain-session-log.md` |
| — | **`frontend-mechanical-fix-all-domains-pass1`** [2026-08-31] —
  تطبيق فئة "أ" (نمط استيراد غلط) على كل الدومينات المتبقية دفعة واحدة.
  النمط: كل `services/<domain>.ts` بيصدّر كائن واحد (`XService = {...}`)،
  لكن أغلب `hooks/`/`components/` كانت بتستورد دوال منفردة بالاسم مباشرة.
  5 agents متوازيين اتبعثوا لتغطية 25 دومين لكن ضربوا rate limit في
  النص؛ الجلسة كملت الباقي مباشرة (بدون subagents) بما فيها التحقق من
  شغل الـagents الجزئي. **23 دومين اتصلّح فعليًا** (~80 ملف)، `tsc`
  TS2305+TS2307: 442 → 290 (تراجع 152). **استثناءات موثّقة صفر لمس:**
  `realestate` (كل الـhooks بلا استثناء فئة ب حقيقية — نفس سابقة
  `realestate-hooks-layer-nonexistent-function-imports`، يحتاج قرار
  تصميم)، باج مزدوج في `date-fns/ar` عبر ~30 ملف (locale غلط + دالة من
  الباكدج الأساسي مش الـlocale — يحتاج تعديل منطق مش مجرد استيراد)،
  `uuid`/`qrcode.react` غير مثبتين كتبعية أصلًا، ~20 ملف/hook معدوم
  تمامًا (اتأكد بـ`Glob` قبل التصنيف). `academy`/`saas`/`commerce`:
  صفر لمس مطلوب — الصفحات بتستورد من طبقة hooks وسيطة مش من الـservice
  مباشرة، فمفيش `TS2305`/`TS2307` فعلي في نطاق هذه الجلسة. تفاصيل كاملة
  (كل ملف، جدول فئة ب حسب الدومين) في التقرير. | 🟢 **مُغلَق —
  الاستثناءات الموثقة (realestate، date-fns/ar، الملفات المعدومة)
  مفتوحة لجلسات مخصصة قادمة** |
  `.claude/reports/frontend-mechanical-fix-all-domains-pass1-session-log.md` |
| — | **`npm-missing-dependencies-uuid-qrcode`** [2026-08-31] —
  حزمتين مفقودتين فعليًا من `package.json`/`node_modules` (اكتُشفوا في
  `frontend-mechanical-fix-all-domains-pass1`). **uuid (21 ملف، مش ~15
  كما قُدِّر أوليًا):** كل استخدام كان `uuidv4()` واحد بس لبناء
  idempotency key — استُبدل بدالة محلية `generateIdempotencyKey()` في كل
  ملف (نفس النمط الدفاعي `crypto.randomUUID()` + fallback `IDEMP-` الموجود
  فعليًا في `hooks/finance/useTransfer.ts`/`useCheckout.ts`؛ **قرار: صفر
  utility مشتركة جديدة في `lib/`** لأن النمط القائم بالفعل محلي لكل ملف،
  مش دالة مشتركة — استخراج واحدة كان هيبقى نمط تالت مختلف، خارج نطاق
  الاستبدال الميكانيكي المتفق عليه). صفر `npm install` لـuuid. **qrcode.react
  (ملف واحد، TicketCard.tsx):** وظيفة عرض SVG حقيقية بلا بديل built-in،
  اتثبتت فعليًا (`npm install qrcode.react@^4.2.0 --legacy-peer-deps`).
  تحقق `tsc` بعد الدفعتين: 1023 → 1002 (uuid) → 1001 (qrcode.react)،
  صفر خطأ uuid/qrcode متبقٍ. اختبار Node مباشر أكّد صيغة UUID v4 صحيحة
  (RFC 4122) من الدالة المحلية الجديدة. **اكتشاف جانبي غير مرتبط بهذه
  الجلسة:** تثبيت qrcode.react كشف (بالصدفة، مش بالسبب) تعارض peer-dependency
  موجود بالفعل من قبل بين `@rainbow-me/rainbowkit@2.2.11` (يطلب
  `wagmi: ^2.9.0`) و`wagmi@3.6.16` المثبت فعليًا في المشروع — تأكَّد إن
  التعارض كان مُثبَّتًا بالفعل في `package-lock.json` قبل أي لمسة من هذه
  الجلسة، وإن `qrcode.react` نفسها صفر علاقة بـ`wagmi` إطلاقًا (`npm view`
  لا يذكرها في dependencies ولا peerDependencies). استُخدم
  `--legacy-peer-deps` لتجاوز الفحص النظري فقط (لم يغيّر نسخة `wagmi`
  الفعلية). **يستاهل مراجعة لاحقة** (تحديث `rainbowkit` لنسخة بدعم رسمي
  لـwagmi v3) — **خارج نطاق هذه الجلسة تمامًا.** | 🟢 **مُغلَق** —
  تعارض rainbowkit/wagmi موثَّق كـbacklog item منفصل، لم يُلمَس |
  `.claude/reports/npm-missing-deps-uuid-qrcode-session-log.md` |

| — | **`realestate-hooks-layer-design-decision`** [2026-08-31] — إغلاق
  كامل للـ8 حالات (ب) الموثَّقة في بند
  `realestate-hooks-layer-nonexistent-function-imports` أعلاه [2026-08-29]
  (`getProperties`, `getProperty`, `createProperty`, `updateProperty`,
  `deleteProperty`, `getPropertyOwnerships`, `getSmartContractStatus`,
  `getAssetTokenization`). **اكتشاف تصحيحي أول خطوة:** قراءة حية لـ
  `repository.py` (لم تُقرأ في جلسة 2026-08-29) كشفت إن 3 من الثمانية
  (`getPropertyOwnerships`, `getSmartContractStatus`,
  `getAssetTokenization`) كان عندها method جاهزة بالكامل على مستوى
  الـrepository (`get_ownerships_by_unit`, `get_smart_contract`,
  `get_tokenization_by_unit`) غير موصولة بـservice/router إطلاقًا —
  إعادة تصنيف من "(ب) مفهوم جديد" لـ"(أ) وصلة فقط". **القرار المعماري
  المعتمَد لباقي الحالات:** `PropertyUnit` الموجود كافٍ كأساس للثمانية
  كلها (**صفر كيان/جدول DB جديد كليًا** — القرار المؤجَّل من جلسة
  التصنيف بتاريخ 2026-08-29 "نبني الميزات الناقصة، مش نقلّم الواجهة"
  تحقَّق بامتداد schema بدل بناء مفهوم "Property" منفصل). **التنفيذ
  الفعلي (3 مراحل متسلسلة، تحقُّق حي كامل بعد كل مرحلة):**
  (1) وصلة service+router للحالات الثلاث أعلاه — صفر migration.
  (2) migration جديدة `043_add_marketing_fields_to_property_units`
  (5 أعمدة اختيارية على `property_units`: `title`, `description`,
  `location`, `cover_image_url`, `status` — الأخير `Enum` جديد
  `propertystatus` بقيم `AVAILABLE/SOLD/RENTED/UNDER_CONSTRUCTION`،
  **مُعدَّلة عن اقتراح المستخدم الأولي `UNDER_OFFER`** لتطابق
  `statusColors` الموجودة فعليًا في `property/[id]/page.tsx`) +
  `GET /realestate/units` (قائمة عامة) + `GET /realestate/units/{id}`.
  **اكتشاف حي أثناء الـmigration:** أول محاولة (`sa.Enum` مباشرة جوّه
  `op.add_column`) فشلت فعليًا (`UndefinedObjectError: type
  "propertystatus" does not exist` — عكس `create_table`، `add_column`
  لا ينشئ نوع الـPostgres Enum تلقائيًا)؛ الترانزاكشن اتلف بالكامل
  (تأكيد `alembic current` بعد الفشل)، صفر أعمدة معلَّقة. الإصلاح:
  `postgresql.ENUM(..., create_type=False)` + `.create(checkfirst=True)`
  صريح قبل `add_column`. (3) `PATCH /realestate/units/{id}` +
  `DELETE /realestate/units/{id}` (soft-delete) — فحص ملكية **حرفيًا
  نفس نمط** `_get_land_owner_for_unit` المستخدَم فعليًا في
  `tokenize_asset`/`rent_unit`، + منع الحذف لو عند الوحدة ملكيات جزئية
  أو تجزئة فعّالة (قرار عمل معتمَد من المستخدم). **تحقق حي كامل** (10
  اختبارات pytest جديدة عبر 3 ملفات، DB حقيقية صفر mock، مسار شرعي
  ومسار هجوم لكل عملية حساسة — نفس منهجية
  `test_realestate_tokenize_asset_ownership_check.py`): كل الـ10 نجحوا.
  `pytest tests/ -k realestate` الكامل بعد كل التعديلات: 23 passed،
  **نفس** 3 فشلات موجودة *قبل* هذه الجلسة (drift بيئي في SaaS feature
  flags لـ`tenant_id=1`، غير مرتبطة — تفصيل خطوة 9 من التقرير)، صفر
  فشل جديد. **متبقٍ خارج النطاق (توثيق فقط):** ربط الفرونت إند فعليًا
  بالـendpoints الجديدة، `property.owner_id` غير موجود في
  `PropertyUnitResponse` (لم يكن من ضمن الأعمدة الخمسة المعتمَدة)،
  `SmartContractStatusMonitor` كود يتيم بأسماء حقول مختلفة
  (`status`/`tx_hash` مقابل `execution_status`/`blockchain_tx_hash`)،
  والفشلات الثلاثة غير المرتبطة تستاهل بند backlog SaaS منفصل. |
  ✅ **مُغلَق بالكامل ومتحقَّق حيًا [2026-08-31]** — كل الثمانية حالات
  (ب) الأصلية اتقفلت في الباك إند (migration + service + router +
  10 اختبارات حية) | `.claude/reports/realestate-design-decision-session-log.md` |
| — | **`transport-domain-migration-and-hold-funds`** [2026-09-01] —
  دومين `transport` كان مكتمل كودًا (models/schemas/service/repository/
  router) وتم إصلاح ثغرات X-Tenant-ID IDOR مسبقًا (commit `6b38d82`)، لكن
  **صفر migration** أنشأ الجداول السبعة (`transport_hubs`, `fleets`,
  `vehicles`, `transport_routes`, `transport_trips`, `trip_bookings`,
  `delivery_tasks`) — كل الـ16 endpoint كانت تفشل بـ`UndefinedTableError`
  عند أول استدعاء حقيقي. **الحل المُنفَّذ [موافقة مستخدم صريحة]:**
  (1) `migrations/versions/044_create_transport_tables.py` — الجداول
  السبعة بالضبط كما فى `models.py`، صفر تغيير بنيوي. (2) `schemas.py`:
  `GeoAddress`/`Waypoint` sub-models حقيقية بدل `Dict[str, Any]` لحل
  `transport-formdata-vs-openapi-schema-mismatch` (أسفل)، وحذف
  `DeliveryTaskCreate.sender_id` الميت. (3) إصلاح باج idempotency retry
  في `book_trip` (`get_booking()` كان بوسيط واحد بدل اتنين). (4) تحويل
  `book_trip`/`pay_delivery` من `finance.transfer()` المباشر لـ
  `hold_funds()`، مع تسوية (`settle_held_funds()`) عند `complete_trip`
  (لكل حجوزات `CONFIRMED` على الرحلة) و`complete_delivery` (لو الرسوم
  محجوزة)، وإضافة `cancel_booking`/`cancel_delivery` (endpoint جديدين)
  بـ`release_held_funds()` — نفس نمط `tenders_auctions` بالكامل. (5) فحص
  ملكية جديد لـ`complete_delivery` (`trip.driver_id == current_user.id`،
  كان بلا أي فحص مستخدم من قبل). **اكتشافان حيّان جديدان اتصلحوا أثناء
  التحقق (أول تنفيذ حقيقي في تاريخ المشروع لهذا الكود، كان معطَّل بنيويًا
  من الأساس):** (أ) `logger.error(f"...{booking.id}...")` بعد فشل
  `invoicing.create_invoice()` (باج `invoicing-generate-invoice-number-
  count-based-collision` أسفل، خارج النطاق) كان بيحاول يقرأ صفة ORM
  والجلسة محتاجة `rollback()` — بيطمس نجاح الحجز الفعلي بخطأ ثانٍ
  (`MissingGreenlet`) يرجّع 500 كاذب للعميل؛ الحل `rollback()`+`refresh()`
  صريحين. (ب) `Trip.vehicle`/`driver`/`route` و`TripBooking.trip` كانت
  مُستخدَمة عبر `selectinload()` في `repository.py` بلا أي `relationship()`
  مُعرَّف فعليًا في `models.py` — `AttributeError` فوري (كود ميت كان
  مخفيًا لأن الجداول ما كانتش موجودة أصلًا)؛ أُضيفت الأربعة علاقات (تغيير
  ORM بحت، صفر migration). **تحقق حي كامل** (سكريبتات مباشرة، جلسة منفصلة
  لكل خطوة تحاكي دورة حياة طلب HTTP، throwaway + تنظيف مؤكَّد مستقل):
  hold→settle (السائق استلم الأجرة فعليًا)، hold→release (استرداد كامل عند
  الإلغاء)، فحوصات ملكية `cancel_booking`/`complete_delivery` (رفض حقيقي
  لغير المالك)، عزل تينانت، إعادة إرسال idempotency نظيفة. **صفر لمس
  فرونت إند** (خارج النطاق المُتَّفَق عليه) — الـ~23 endpoint إضافية
  اللي الفرونت إند مبني عليها (list/update/delete/cancel/stats/tracking)
  تُوثَّق كبند منفصل تحت. | ✅ **مُغلَق ومتحقَّق حيًا بالكامل [2026-09-01]** |
  `.claude/reports/transport-domain-full-build-session-log.md` (كامل، §7) |
| — | **`transport-frontend-assumed-api-surface-backlog`** [2026-09-01] —
  اكتُشف أثناء `transport-domain-migration-and-hold-funds` (أعلاه):
  `hooks/transport/*.ts` مبنية على افتراض سطح API أوسع بكثير من الـ16-18
  endpoint الفعليين — بتستورد أسماء دوال (named exports) من
  `services/transport.ts` **غير موجودة إطلاقًا** (الملف بيصدّر بس object
  واحد `TransportService`). محتاج ~21 endpoint إضافي (باك إند + service.ts
  متوافق) موزَّعين هيك: **Fleets:** `getFleets` (list)، `updateFleet`،
  `deleteFleet`. **Hubs:** `updateHub`، `deleteHub` (الـGET list موجود
  فعليًا كـ`listHubs`، محتاج بس تصدير باسم `getHubs`). **Vehicles:**
  `getVehicles` (قائمة كل المركبات، مش بس المتاحة)، `getVehicle`،
  `deleteVehicle`، `getVehicleLocation` (تتبع حي polling كل 3 ثواني —
  `useLiveTracking.ts`). **Routes:** `getRoutes`، `getRoute`،
  `updateRoute`، `deleteRoute`، `optimizeRoute`. **Trips:** `getTrips`
  (كل الرحلات، مش بس "رحلاتي")، `getTrip`، `cancelTrip`. **Bookings:**
  `getBookings` (عرض إداري لكل الحجوزات — `cancelBooking` بقى موجود من
  الجلسة أعلاه، محتاج بس تصدير frontend مطابق). **Deliveries:**
  `getDeliveries`، `getMyDeliveries`، `assignDeliveryToTrip`
  (`cancelDelivery` نفس ملاحظة `cancelBooking`). **Stats:**
  `getTransportStats` (`GET /transport/stats` — `total_vehicles`,
  `available_vehicles`, `active_trips`, `total_deliveries`,
  `total_carbon_saved`, `total_hubs`, `total_routes`، يستهلكها
  `TransportStatsCards.tsx`). **مرتبط:** `hooks/transport/useVehicles.ts`
  لسه فيه محتوى غلط بالكامل (نسخة كاملة من `useTrips.ts`، صفر كود مركبات)
  — موثَّق سابقًا `transport-vehicles-hook-file-wrong-content` (أسفل)،
  لسه بلا لمس. أيضًا `*_name` enrichment (`driver_name`, `passenger_name`,
  `sender_name`, `receiver_name`) غائب من كل الـResponse schemas — الفرونت
  إند يتوقعها جاهزة، الباك إند بيرجّع `*_id` بس. | 🟡 **مفتوح جزئيًا
  [تحديث 2026-09-05، جلسة `transport-vehicles-drivers-feature-build`]** —
  **Fleets (list/update/delete) وVehicles (list/update/delete) اتقفلوا
  بالكامل** (باك إند + `services/transport.ts` + `useVehicles.ts`/
  `useFleets.ts` مُعاد كتابتهم، مُتحقَّق حيًا بـ7 pytest). **Drivers**
  اتحل بتصميم مختلف عن المفترَض هنا أصلًا — مفيش `getBookings`-مثيل، بس
  `GET /transport/drivers` (سرد مستخدمين نشطين، صفر كيان سائق منفصل، راجع
  التقرير المرجعي الجديد §3-4). **لسه مفتوح فعليًا:** Hubs
  (`updateHub`/`deleteHub`)، Routes (الخمسة كلهم)، Trips (`getTrips` عام/
  `getTrip`/`cancelTrip`)، Bookings (`getBookings` إداري)، Deliveries
  (`getDeliveries`/`getMyDeliveries`)، Stats (`getTransportStats`)،
  و`getVehicleLocation` (تتبع حي لـ`useLiveTracking.ts` تحديدًا — مختلف
  عن `updateVehicleLocation` الموجودة). `*_name` enrichment لسه غائب
  بالكامل زي ما هو. | `.claude/reports/transport-domain-full-build-session-log.md` §2, §8،
  `.claude/reports/transport-vehicles-drivers-session-log.md` |
| — | **`transport-saas-catalog-entry-missing-in-dev`** [2026-09-05] —
  اكتُشف حيًا أثناء جلسة `transport-vehicles-drivers-feature-build`
  (تحقُّق pytest ضد DB حقيقية): `saas_service_catalog` في بيئة الديف
  الحالية **عندها صفر صف بـ`code='transport'`** — السبب: جلسة
  `transport-domain-migration-and-hold-funds` [2026-09-01] زرعت صف مؤقت
  لتحقُّقها الحي الخاص، ونظَّفته بالكامل في نهايتها عمدًا (§7.9 من تقرير
  تلك الجلسة، تنظيف متعمَّد صحيح، مش سهو). **الأثر:** أي استدعاء لأي
  service method بتنادي `_check_saas_limits(tenant_id, "transport")` —
  ده يشمل **الدومين بالكامل، القديم والجديد**: `list_hubs`,
  `create_vehicle`, `create_fleet`, `create_route`, `book_trip`,
  `create_delivery`, `pay_delivery`, `get_my_trips`, وكل دوال هذه الجلسة
  الجديدة (`list_vehicles`, `update_vehicle`, `list_fleets`,
  `update_fleet`, `list_drivers`) — **بيرجع `PermissionDeniedError` لأي
  تينانت، دايمًا، في هذه البيئة تحديدًا.** يمنع فعليًا أي اختبار متصفح
  حقيقي أو استخدام فعلي للدومين بالكامل حاليًا (راجع بند
  `transport-vehicles-drivers-phase9-browser-verification-gap` تحت —
  نفس السبب الجذري). **قرار مطلوب، لم يُتَّخذ بعد:** (أ) زرع صف
  `saas_service_catalog`/`saas_service_plans`/`saas_tenant_subscriptions`/
  `saas_tenant_service_access` **دائم** (غير throwaway) لتينانت(ات) الديف
  الأساسية، أم (ب) تعديل `_check_saas_limits`/آلية الفحص لتتجاوز بيئة
  الديف (متغير بيئة، مثلًا). **صفر لمس في هذه الجلسة** — الاختبارات
  الجديدة بتزرع نفس المنحة مؤقتًا وتنضّفها بالكامل بعد كل test (idempotent
  get-or-create + تنظيف مؤكَّد مستقل، راجع التقرير المرجعي). | 🔴 **مفتوح،
  أولوية عالية نسبيًا — يحجب أي استخدام فعلي/اختبار متصفح للدومين بالكامل
  حتى يُتَّخذ القرار** | `.claude/reports/transport-vehicles-drivers-session-log.md` §6(أ) |
| — | **`transport-vehicles-drivers-phase9-browser-verification-gap`**
  [2026-09-05] — في نفس جلسة `transport-vehicles-drivers-feature-build`،
  بعد تنفيذ كامل (باك إند + فرونت إند، `tsc` نظيف على كل ملف مُعدَّل +
  7/7 pytest ضد DB حقيقية) — **التحقق الحي الكامل في متصفح فعلي لم يحصل**:
  امتداد Chrome غير متصل بهذه الجلسة (نفس القيد الموثَّق سابقًا في بند
  `frontend-decimal-fix-live-browser-render-unverified`)، **رغم محاولة
  حقيقية فعلية** (شُغِّل الباك إند فعليًا عبر `uvicorn` وتأكَّد `LISTENING`
  على المنفذ 8000 قبل محاولة الاتصال بالمتصفح). **فجوة تحقق إضافية
  مكتشَفة أثناء المحاولة:** حتى لو اتصل المتصفح فعليًا، أي تحميل حقيقي
  لصفحات `/transport/vehicles`/`/transport/fleets` كان هيرجع
  `403 PermissionDeniedError` لكل الطلبات بسبب بند
  `transport-saas-catalog-entry-missing-in-dev` أعلاه — يعني حتى مع
  اتصال ناجح، الـgolden path مكنش هيتفحص فعليًا اليوم بلا قرار SaaS
  منفصل. **التحقق المنطقي المكافئ المُنفَّذ بدلًا منه (بموافقة مستخدم
  صريحة):** تتبّع تدفق البيانات يدويًا لكل صفحة مستهلِكة
  (`vehicles/page.tsx`, `fleets/page.tsx`) من الـhook → `TransportService`
  → endpoint → service → repository، مقارنةً بنفس المسارات المُتحقَّق
  منها حيًا في الـ7 pytest، زائد `tsc --noEmit` نظيف. **صفر دليل بصري/DOM
  حقيقي حتى الآن** إن الصفحات بترندر بلا كسر layout/CSS أو أخطاء console
  في متصفح حقيقي، وصفر تأكيد إن استجابة HTTP الفعلية (بعد
  `X-Tenant-ID` header + JSON serialization حقيقي) مطابقة تمامًا لما
  اختبرته الـservice مباشرة. **خطوات الإغلاق المقترَحة:** (1) إعادة نفس
  التحقق بعد ما اتصال Chrome يرجع + بعد حل بند SaaS catalog أعلاه؛
  (2) فتح `/transport/vehicles`, `/transport/fleets`, `/transport/trips`
  فعليًا بمستخدم superuser (المطلوب لـ`create`/`update`/`delete`) من
  `.claude/reports/throwaway-test-users.md`. | 🟡 **مفتوح، أولوية متوسطة
  — فجوة تحقق حقيقية موثَّقة بوضوح، مش خطأ معروف ولا ادّعاء نجاح لم
  يحصل** | `.claude/reports/transport-vehicles-drivers-session-log.md` §8 |
| — | **`insurance-disburse-pensions-payout-logic-broken`** [2026-09-21] — اكتُشف أثناء Batch 0-A (`insurance-batch0a-tenant-isolation`) في التشخيص ثم التحقق الحي لـ`POST /insurance/admin/disburse-pensions` (`insurance/service.py::disburse_monthly_pensions`). **الطبقة (أ) — عزل التينانت — اتصلحت في نفس الجلسة (لا تُعاد هنا):** الدالة بقت `disburse_monthly_pensions(tenant_id)` تقرأ `list_active_pensions(tenant_id)` (دالة repo جديدة) وتربط `FinanceService(self.db, tenant_id)`؛ الاستعلام القديم `list_pensions_for_beneficiary(None, ACTIVE)` كان يترجم `WHERE beneficiary_id IS NULL` على عمود `NOT NULL` فيرجّع صفر صف دائمًا (مؤكَّد حيًا: 7 معاشات ACTIVE، `count=0`). **الباقي مفتوح — منطق الصرف نفسه، 3 أعطال جديدة:** (1) **`finance.transfer(...)` بلا `idempotency_key`** رغم إنه معامل إجباري → `TypeError` عند الاستدعاء قبل أي أثر، و`except Exception: pass` في نفس الدالة بيبلعه صامتًا فترجع `count=0` "نجاح" — وده اللي بيخلّي الدالة ما تدفعش حاجة النهارده؛ (2) **كائن `Transaction` كامل بيتخزَّن في `last_payout_tx`** (`update_pension(..., last_payout_tx=tx)` بدل `tx.tx_hash`) بينما العمود `PensionRecord.last_payout_tx` هو `String(100)` — نفس فئة `finance-transfer-returns-transaction-object-not-tx-hash-string` [2026-08-18] أعلاه (المرجع العام للفئة)؛ (3) **فحص "دُفع هذا الشهر" عالق:** `_get_payout_date()` بترجع `datetime.utcnow()` دايمًا بغض النظر عن `tx_hash`، فأي معاش له `last_payout_tx` غير فاضي بيُعتبر مدفوع الشهر الحالي وبيتخطّاه في كل شهر — عمليًا مفيش حماية شهرية حقيقية. **`sender_id=1` هاردكودد — مش بيتوثَّق هنا تاني:** إحالة للبند الموجود `finance-transfer-hardcoded-system-account-real-fund-risk` [تحديث 2026-09-16] (الصف أعلاه؛ تتبُّعه الأول كان تحت اسم `insurance-disburse-pensions-hardcoded-system-account`)؛ الموقع الآن `insurance/service.py` السطر 638 (كان :626 قبل Batch 0-A). **⚠️ شرط ترتيب صريح: قرار الدافع (مين بيدفع؟ حساب نظام التينانت عبر `get_or_create_system_account`؟) لازم يتحسم قبل إصلاح `idempotency_key` — وإلا فإصلاح المفتاح وحده هيخلّي الصرف يسحب فعليًا من محفظة `user_id=1`**، لأن الإصلاح الحالي جعل الحلقة تصل لأول مرة لمعاشات حقيقية ولا فلوس بتتحرك فقط بسبب العطل (1). | 🔴 **مفتوح، أولوية عالية — الخطر كامن (latent) لا حي:** الـendpoint حاليًا بيرجع `count=0` ولا بيحرّك أي فلوس (مؤكَّد حيًا بعد الإصلاح: أرصدة + جدول `transactions` + محفظة user 1 = 710.0 بلا تغيير)، ولا جدولة تلقائية للدالة | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §2.4، §11، §12؛ `.claude/reports/insurance-batch0a-evidence-after.txt` |
| — | **`insurance-submit-claim-500`** [2026-09-21] — اكتُشف أثناء التحقق الحي لـBatch 0-A: `POST /insurance/claims` (`submit_claim`) بيرجع **500 دايمًا لأي مستخدم في أي تينانت**، حتى في السيناريو المشروع تمامًا (`member_A` على اشتراك ACTIVE خاص به: تينانت 124 قبل الإصلاح و128 بعده — نفس النتيجة). **السبب الجذري (من لوج السيرفر):** `insurance/service.py` (`submit_claim`، ~سطر 403-408) بيبني `create_claim(**{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]})` — **بيستبعد `subscription_id` نفسه**، فيُدرَج `NULL` في `insurance_claims.subscription_id` (`nullable=False`). ملخص الـtraceback: `router.py:195 submit_claim` → `service.py:402 submit_claim` → `repository.py:113 create_claim` (`await self.db.flush()`) → `IntegrityError`/`asyncpg NotNullViolationError: null value in column "subscription_id" of relation "insurance_claims"`؛ والـ`parameters` بتوضح `tenant_id=128` سليم و`subscription_id=None`. **غير متعلق بعزل التينانت** (`tenant_id` سليم في الـINSERT). **الحالة في Batch 0-A:** طُبِّق **جزء عزل التينانت فقط** (`tenant_id = cast(int, current_user.tenant_id)` بدل الهيدر)، **الباج نفسه لم يُصلَح**. **⚠️ مسار النجاح (`submit_claim` المشروع) لم يُتحقَّق منه حيًا ولا يمكن التحقق منه** حتى إصلاح هذا البند — المُثبَت فقط الاتجاه الهجومي (قبل: الطلب المزوَّر بهيدر تينانت آخر وصل للـINSERT بـ`tenant_id=125`؛ بعد: 404 "Subscription not found" قبل الوصول للـINSERT). وأي خطوات بعد الـINSERT (audit / event_bus / idempotency، ومسار AI governance المغلَّف بـ`try/except`) غير مُختبَرة أيضًا. **مطلوب عند إصلاح هذا البند (F1): إعادة تشغيل التحقق الحي العابر للتينانت على المسار المشروع** (مطالبة بتُقدَّم فعليًا بنجاح داخل تينانت المستدعي + محاولة عابرة بهيدر تينانت آخر تفشل)، **لأن العزل أُثبت على مسار الهجوم فقط**. **الحل المتوقَّع (لم يُنفَّذ):** تمرير `subscription_id=data["subscription_id"]` صراحة لـ`create_claim`. | 🔴 **مفتوح، أولوية عالية** — endpoint مكسور بالكامل (لا يمكن تقديم أي مطالبة عبر الـAPI) | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §7.1، §9-F1، §13-ب |
| — | **`insurance-review-claim-no-status-guard-and-random-payout-idempotency`** [2026-09-21] — *ملاحظة بالقراءة الثابتة أثناء Batch 0-A، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* (1) `review_claim` (`insurance/service.py` ~452-578) **لا يفحص حالة المطالبة الحالية قبل الموافقة** — الإشارات الوحيدة لـ`ClaimStatus` داخل الدالة هي عند **كتابة** `PAID`/`REJECTED`، فمطالبة `PAID` بالفعل تقدر تدخل نفس المسار تاني؛ (2) **مفتاح idempotency الخاص بالتحويل بيحوي `uuid` عشوائي** (`payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"`، ~سطر 517) فبيتغيّر في كل استدعاء ولا يمنع تكرار الدفع أبدًا — الحماية الوحيدة من التكرار هي هيدر `Idempotency-Key` الاختياري اللي بيرجّع نتيجة مخزَّنة (لو مش مبعوت، مفيش حماية)؛ (3) **نفس النمط في `renew_subscription`** (`payment_idempotency = f"renew_{subscription_id}_{uuid...}"`، ~سطر 305، وبلا هيدر idempotency أصلًا). **السياق:** قبل Backlog #41 [2026-08-29] (`insurance-review-claim-issuer-entity-id-reviewer-id-mismatch`) كان فحص الصلاحية في `review_claim` بيقارن مساحتَي معرِّفات مختلفتين فكان يرفض الجميع (المسار عمليًا مقفول، `broken-closed`)، وبعد إصلاحه بقت `review_claim` قابلة للوصول فعليًا؛ وفي Batch 0-A أثبت **LEGIT-2** حيًا إن الدفع بيشتغل (`approve=true`، 20 MR_USDT، المراجِع 500→480، صاحب المطالبة 490→510، `payout_tx_hash` مسجَّل، المطالبة `PAID`) — **يعني لو الفرضية اتأكدت، `approve=true` مرتين على نفس المطالبة ممكن يدفع مرتين** (وبنفس السبب `approve=false` بعد `PAID` ممكن يقلب المطالبة لـ`REJECTED` والفلوس اتدفعت). **الحالة:** لم تُجرَّب ولم تُصلَح. **تحقق حي قصير مقترَح (منفصل، بموافقة قبل التنفيذ):** تينانت throwaway + مطالبة SUBMITTED + مراجِع OWNER ممول → (أ) `approve=true` مرتين بلا `Idempotency-Key`، (ب) `approve=true` مرتين بنفس `Idempotency-Key`، (ج) `approve=false` بعد `PAID`؛ مقارنة أرصدة المراجِع/المطالِب و`transactions` و`status` بعد كل خطوة (بـ`SELECT` مستقل) ثم تنظيف zero-diff. | 🟡 **غير مُتحقَّق منه — أولوية عالية (تحرّك فلوس)**؛ التصنيف النهائي (مؤكَّد/مُنفى) بعد التحقق الحي | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §15 - Pre-log review package (ج)؛ `.claude/reports/insurance-41-review-claim-permission-check-session-log.md` |

**✅ إغلاق جزئي مؤرَّخ [2026-09-23] — الجزءان (1) و(2) مُغلَقان، الجزء (3) مفتوح:** الفرضية **تأكدت حيًا** ثم أُصلحت (جلسة `insurance-review-claim-double-payment-verification`). **BEFORE (HTTP حقيقي، تينانت throwaway 130، الكود غير المُصلَح):** `approve=true` مرتين على مطالبة بـ20 → **200 مرتين ودفع مزدوج فعلي** (المراجِع 500→480→460، المطالِب 0→20→40، صفّا `transactions` بمفتاحين عشوائيين مختلفين، فاتورتان، و`payout_tx_hash` استُبدل بالثاني)؛ `approve=false` بعد `PAID` → **200 والمطالبة `REJECTED`** مع بقاء `approved_amount=20` و`payout_tx_hash` والأموال مدفوعة. **الإصلاح (3 ملفات، +29/−2):** (1) `REVIEWABLE_CLAIM_STATUSES = {SUBMITTED, UNDER_INVESTIGATION}` — فحص مبكر قبل استدعاء AI + فحص حاسم تحت `SELECT ... FOR UPDATE` داخل `begin_nested()` عبر دالة repo جديدة `get_claim_for_update` (مع `populate_existing=True` — لازم لأن `expire_on_commit=False` واستدعاء AI يعمل commit وسيط فيبقى الكائن المحمَّل قديمًا)؛ (2) مفتاح دفع حتمي `claim_payout_{claim_id}`؛ (3) استثناء جديد `ClaimStatusConflictError` → **409** `CLAIM_STATUS_CONFLICT` (`core/errors.py`). `APPROVED`/`PAID`/`REJECTED` نهائية لهذا المسار — أي تصحيح لاحق يحتاج مسارًا منفصلًا للـsuperuser (قرار المستخدم). **AFTER:** الاستدعاء الثاني 409 وصفر حركة أموال/فواتير؛ reject بعد `PAID` → 409 والحالة تبقى `PAID`؛ **تزامن حقيقي** (طلبان عبر `asyncio.gather`) → 200 + 409 ودفعة واحدة فقط، ورسالة الـ409 أثبتت أن **فرع القفل** هو من أمسك الطلب الثاني. اختبار دائم `tests/test_insurance_review_claim_status_guard.py` (3/3، A+B+C على مستوى الخدمة بجلسات منفصلة، تينانت throwaway خاص؛ **mutation check مُنفَّذ:** بإرجاع `service.py`/`repository.py` لـHEAD يفشل 3/3 على السلوك نفسه — A وB `DID NOT RAISE ClaimStatusConflictError`، وC نجاحان متزامنان بدل نجاح + تعارض — ثم 3/3 passed بعد إعادة الإصلاح، وzero-diff بعد التشغيلين؛ `_cleanup` في الاختبار يحذف `transactions` بمستخدمي الاختبار لا بالمفتاح، فينظّف حتى عند الفشل). Regression insurance+finance: لا فشل جديد (3 فشلات مسبقة مُثبَتة على HEAD). تنظيف zero-diff (259 جدولًا). **الجزء (3) لم يُلمَس — ما زال مفتوحًا:** `renew_subscription` بمفتاح `renew_{subscription_id}_{uuid}` عشوائي (~سطر 305) وبلا هيدر idempotency — لم يُتحقَّق منه حيًا. **اكتشاف جانبي من نفس الجلسة (بند منفصل أدناه):** `insurance-review-claim-negative-approved-amount-reverses-transfer`. | commit: `88097be` | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §13، §14، §16؛ `.claude/reports/insurance-review-claim-double-payment-evidence-{before,after}.txt`

| — | **`insurance-unused-tenant-header-dependencies`** [2026-09-21] — *documented-only، لا تنفيذ:* 4 endpoints في `insurance/router.py` (`renew_subscription`، `get_my_claims`، `get_my_pensions`، `get_my_employee_profile`) لسه بتعلن `tenant: AcademyTenant = Depends(get_current_tenant)` **بدون أي استخدام لها في الجسم** — صفر خطر فعلي (الهيدر لا يؤثر على شيء فيها)، دين تنظيف فقط؛ واستيراد `get_current_tenant`/`AcademyTenant` باقٍ في الملف بسببها وحدها. | ⚪ **مرجع فقط، أولوية منخفضة** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §10 |
| — | **`server-startup-index-creation-failure-and-cp1256-logging-errors`** [2026-09-21] — *documented-only، **خارج نطاق `insurance`** (لم يُلمَس، اكتُشف بالصدفة أثناء تشغيل `uvicorn` محليًا على Windows في Batch 0-A):* (1) **`app/core/database_indexes.py:78`** — كتلة فهارس `transactions` فيها `CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, created_at DESC)` (وكمان `idx_transactions_currency_user ... (currency, user_id)`)، لكن جدول `transactions` **ما فيهوش عمود `user_id`** (فيه `sender_id`/`receiver_id`) → `ProgrammingError: column "user_id" does not exist` عند كل بدء سيرفر؛ والكتلة (نص SQL واحد) بتتسجَّل كـ"⚠️ Skipping index (likely exists)" — **رسالة مضلِّلة** لأن السبب خطأ حقيقي مش "الفهرس موجود". وبعده ظهر في لوج بدء واحد 176 سطر `InFailedSQLTransactionError` — يوحي بأن كتل فهارس تانية بتفشل بالتبعية (**لم يُحصَر عددها ولا أيها فاتها الإنشاء فعليًا**). (2) **`UnicodeEncodeError: 'charmap' codec can't encode character`** (كودك cp1256 للكونسول على Windows) عند تسجيل رسائل فيها عربي/إيموجي (✅ 🔄 ⚠️) → "--- Logging error ---" tracebacks بتغرق اللوج (لوج تشغيل واحد فيه أكتر من 10 آلاف سطر) وبتدفن أخطاء حقيقية — traceback باج `submit_claim` كان مدفونًا وسطها. **الأثر:** أداء (إنشاء فهارس `transactions` مش مضمون من هذا المسار) + صعوبة تشخيص؛ صفر أثر أمني/مالي مباشر. **الحل المتوقَّع (لم يُنفَّذ):** تصحيح أعمدة الفهارس (`sender_id`/`receiver_id`) في `database_indexes.py`، وتغيير رسالة الـskip لتعرض الخطأ الفعلي، وضبط ترميز الـlogging (`utf-8`) لبيئة Windows. | ⚪ **مفتوح، أولوية متوسطة–منخفضة، documented-only — خارج نطاق `insurance`** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §9-F3 |
| — | **`insurance-batch0a-commits-pending`** [2026-09-21] — بند إداري (git hygiene): **لم يُنفَّذ أي commit** في Batch 0-A؛ تعديلات `insurance` القديمة متداخلة مع Batch 0-A في `router.py`/`service.py` (تقسيم A ثم B بـ`git apply --cached` مُثبَتة جدواه)، وmigration `049` تعتمد على `048` غير tracked من جلسة saas — **`048` لا يُضمّ في commit insurance، وقراره لصاحب جلسة saas/المستخدم**؛ و`PROGRESS_LOG.md` يُقسَّم hunks لا يُلتزَم كاملًا. | ⏸️ **معلَّق — بانتظار قرار المستخدم/صاحب جلسة saas** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §14-د، §15 - Pre-log review package (د) |

**✅ إغلاق مؤرَّخ [2026-09-22]:** الحالة أعلاه (⏸️ معلَّق) باتت باليةً — الـ4 commits نُفِّذت فعليًا بالترتيب الموصى به هنا بالحرف: migration 048 (`347c337`، جلسة saas منفصلة) ← `9ff6572` (فحص عضوية الكيان) ← `65a4168` (migration 049 + سكيما `issuer_entity_id` الفارغة) ← `a231c58` (Batch 0-A — عزل التينانت، هذا البند). تفاصيل التقسيم والتحقق قبل كل commit في `.claude/reports/batch0-commits-session-log.md`. **البند مُغلَق.**

| — | **`invitations-update-invitation-missing-commit-silent-write`** [2026-09-21] — اكتُشف حيًا أثناء 0-B1 (السدّ الفوري لثغرة `accept_invitation`): `PUT /invitations/{id}` بيرجع `200` (والتعديل يبدو ناجحًا) لكن **لا يُخزَّن فعليًا** — `InvitationsRepository.update_invitation` تعمل `flush()` فقط، و`InvitationsService.update_invitation` لا تعمل `commit()` بعدها، فيُتراجَع عن كل تعديل عند إغلاق جلسة الطلب. **مؤكَّد حيًا:** `PUT {status: SENT}` على 5 دعوات throwaway رجعت `200` لكل واحدة، وبقيت كلها `DRAFT` في DB. **الأثر العملي:** (1) لا يوجد اليوم **أي مسار API** يضع دعوة بحالة `SENT` فعليًا (`launch_campaign` تفعّل **حملة** لا دعوة، والإنشاء عبر API ينتج `DRAFT` دائمًا) — وهذا ما يجعل ثغرة `accept_invitation` الأصلية (0-B) **كامنة لا حية** اليوم؛ (2) يُصحِّح ادعاءً كان خاطئًا في تقرير 0-B عن ثغرة مزعومة ('المرسِل يقدر يضبط `status`/`max_uses` يدويًا') — **غير فاعلة عمليًا** لأن `PUT` كله لا يحفظ شيئًا أصلًا، أيًّا كان الحقل. صفر لمس كود — توثيق فقط. | 🟡 **مفتوح، أولوية متوسطة** — endpoint إدارة الدعوات معطَّل فعليًا لأي تعديل، ويحجب حاليًا استغلال ثغرة `accept_invitation` عبر الـAPI | `.claude/reports/invitations-batch0b1-close-hole-session-log.md` (اكتشاف "أثناء التنفيذ")، §S-1 |
| — | **`invitations-header-trusted-cross-tenant-endpoints`** [2026-09-21] — *تجميع 7 اكتشافات جانبية من 0-B1 §الشرط 2، لم تُصلَح، خارج نطاق 0-B1 صراحة (اقتصر على `accept`):* من أصل 31 مسارًا في `invitations/router.py`، **3 مسارات فقط** ما زالت تعتمد على هيدر `X-Tenant-ID` غير الموثوق (`get_current_tenant`) بدل `current_user.tenant_id`: (F-1) **`POST /tracking`** — مصادقة اختيارية غير مُستخدَمة فعليًا لتحديد الفاعل، فأي مستدعٍ (حتى مجهول) يكتب صف `InvitationTracking` في أي تينانت يختاره عبر الهيدر، بلا فحص انتماء `invitation_id` لذلك التينانت (بوابته الوحيدة `_check_saas_limits` على قيمة الهيدر نفسها)؛ (F-2) **`POST /{id}/chat`** — الهيدر يتغلّب على تينانت التوكن حتى لو كان المتصل مصادَقًا، فيُنشئ محادثة ويستهلك حصة AI ويقرأ بيانات دعوة في تينانت آخر؛ (F-3) بوابة `_check_saas_limits` على المسارين أعلاه تعمل ببيانات الهيدر فتكشف أي تينانت مفعَّل عليه CRM (فرق 403/تابع). **اكتشافات إضافية موثَّقة فقط:** (F-4) ديكوريتور `@rate_limit` بلا أثر على 28 من 31 مسارًا (يتطلب معامل `request: Request` غير موجود عليها، ومنها `accept`/`create`/`update`)؛ (F-5) `InvitationsRepository.increment_clicks` كود ميت بلا فلتر تينانت أصلًا (لا مستدعٍ حاليًا)؛ (F-6) مفتاح idempotency لـ`accept`/`chat`/`tracking` عالمي غير مقيَّد بالتينانت/المستخدم — نتيجة مخزَّنة تُعاد لأي مستدعٍ يعيد نفس المفتاح؛ (F-7) `target_user_id` في `create_invitation` يُمرَّر لتحليل AI بلا تحقق من انتمائه لتينانت المتصل. صفر لمس كود لأي من الستة. | 🟡 **مفتوح، أولوية متوسطة (F-1/F-2 كتابة/قراءة عابرة للتينانت فعليًا؛ الباقي أدنى)** | `.claude/reports/invitations-batch0b1-close-hole-session-log.md` §الشرط 2 (F-1 إلى F-8) |
| — | **`admin-kill-switch-medical-flag-skipped-on-ai-failure`** [2026-09-22] — اكتُشف أثناء تنفيذ 0-C: `tourism_sports/service.py:504` — الفحص الطبي المعتمِد على AI لتحويل لاعب (`medical_flag`) **يُتخطّى بصمت عند أي فشل في استدعاء AI** — ومنه الإيقاف المتعمَّد بمفتاح الطوارئ الجديد نفسه. اليوم الأثر شبه معدوم (المحرك محاكاة ولا يُرجع `flag` أصلًا)، لكن الثغرة **تصبح خطيرة فعليًا فور تفعيل استدعاء LLM حقيقي**: تفعيل الـkill switch (لأي سبب طارئ، بما فيه هذا نفسه) سيسمح بتحويل لاعبين بلا فحص طبي فعلي بدل حجب العملية. **قرار منتج مطلوب (لم يُتخذ):** يفشل التحويل (`503`) أثناء الإيقاف أم يتحوّل لمراجعة بشرية إلزامية؟ صفر لمس كود — توثيق فقط. | 🔴 **مفتوح، أولوية عالية — سلامة طبية، مستقل عن باقي بنود الـkill switch** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §6 (B-E3) |

**✅ إغلاق جزئي مؤرَّخ [2026-09-22]:** الحجب (`TransferStatus.MEDICAL_REVIEW` بدل `BID_PLACED` غير المشروطة) نُفِّذ ومُتحقَّق منه حيًا بالكامل (4 سيناريوهات: `medical_flag=True`، الكيل سويتش (`AISystemSuspendedError`)، لا موافِق مؤهَّل، تحويل نظيف بلا انحدار) — القرار المنتج المطلوب سابقًا حُسم: **الخيار (ب) مراجعة بشرية إلزامية**، عبر آلية `ai_agents.create_approval_request` الموجودة أصلًا (موافِق = أقدم `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` نشط في التينانت باستثناء صاحب العرض). الحجب **مستقل بنيويًا** عن أي فشل لاحق في مسار الموافقة (الحالة تُلتزَم في DB قبل أي محاولة لإنشاء طلب الموافقة). Commit: `2c69baf` (`fix(tourism_sports): require human medical review before player transfer bid proceeds (B-E3)`).
**⚠️ قيد وظيفي معروف — الإغلاق جزئي لا كامل:** إنشاء سجل الموافقة نفسه (`agent_approval_queue`) **يفشل بصمت اليوم** في كل الحالات، بسبب باج منفصل مكتشَف أثناء هذه الجلسة (`agent_id=6` مُحكَم في الكود وغير موجود في `ai_agents`) — بند backlog جديد `tourism-sports-transfer-bid-hardcoded-agent-id-6-not-found-crashes-endpoint` (تحت، 🔴 HIGH). **بمعنى عملي: التحويلات تُحجب بنجاح، لكن لا يوجد اليوم أي مسار لأدمن لحلّها عبر `GET /approvals/pending`/`POST /approvals/{id}/resolve`.** إصلاح ذلك البند **شرط ضروري** لا تحسين اختياري لاكتمال هذا المسار من طرف لطرف. تفاصيل كاملة: `.claude/reports/tourism-medical-flag-priority-assessment-session-log.md` (التقييم/القرار) و`.claude/reports/tourism-medical-flag-review-implementation-session-log.md` (التنفيذ + الأدلة الحية + الـdiff الحرفي الكامل في §12).

**تحديث [2026-09-23]:** بند `agent_id=6`/انهيار `place_transfer_bid` أُغلق جزئيًا (commit `edb5e5e`) — **الانهيار الكامل للـendpoint (500 على كل استدعاء حقيقي) انتهى**، والحجب (`MEDICAL_REVIEW`) مُتحقَّق منه الآن فعليًا على استدعاء حقيقي غير محاكى للمرة الأولى. **لكن القيد الوظيفي المذكور أعلاه (فشل إنشاء سجل الموافقة `agent_approval_queue` بصمت) لا يزال قائمًا بالحرف** — مُتحقَّق منه حيًا مجددًا اليوم بنفس الخطأ بالضبط، لأن هذه الجلسة تعمَّدت عدم لمس `agent_id=6`/مسألة الوكيل الطبي الحقيقي (قرار صريح ومسوَّغ في تقرير التشخيص). التفاصيل: `.claude/reports/tourism-sports-transfer-bid-hardcoded-agent-id-6-implementation-session-log.md`.

| — | **`tourism-sports-transfer-bid-hardcoded-agent-id-6-not-found-crashes-endpoint`** [2026-09-22] — اكتُشف أثناء تنفيذ إصلاح `admin-kill-switch-medical-flag-skipped-on-ai-failure` (B-E3) — **مستقل تمامًا عن الكيل سويتش/medical_flag**، ثلاث طبقات انهيار مستقلة متتالية في `place_transfer_bid`: (1) `agent_id=6` مُحكَم في موضعين (`execute_agent_action`، `governance.check_and_consume`) بينما `ai_agents` الفعلي يحتوي `id=216` فقط — `check_and_consume` تعمل **بلا `try/except`** فيُدرِج صفًا بـ`agent_id=6` في `agent_usage_logs`، فيفشل بـ`IntegrityError` **غير مُلتقَط** يُسقط الدالة بالكامل (500) على كل استدعاء حقيقي اليوم؛ (2) حتى بعد تجاوز (1): `data` (تتضمن `from_club_id` من الراوتر) تُمرَّر لاحقًا `**data` مع `from_club_id=from_club_id` صراحةً إلى `repo.create_transfer` → `TypeError: got multiple values for keyword argument 'from_club_id'` (مؤكَّد حيًا)؛ (3) حتى بعد تجاوز (1)+(2): معالج فشل إنشاء الفاتورة يصل لخاصية `transfer.id` مباشرة بعد `await self.db.rollback()` → `MissingGreenlet` تحت SQLAlchemy async (مؤكَّد حيًا). **الأثر: `POST /sports/transfers/bid` منهار بالكامل على أي استدعاء حقيقي اليوم، بغض النظر عن medical_flag أو الكيل سويتش.** صفر لمس كود — توثيق فقط. | 🔴 **مفتوح، أولوية عالية — endpoint منهار بالكامل (500 غير معالَج)، ليست صيانة روتينية** | `.claude/reports/tourism-sports-transfer-bid-hardcoded-agent-id-6-not-found-crashes-endpoint.md` |

**✅ إغلاق مؤرَّخ [2026-09-23]:** الثلاث طبقات الانهيار المستقلة أعلاه أُصلحت بالكامل ومُتحقَّق منها حيًا (BEFORE: استدعاء حقيقي 100% بلا محاكاة أكَّد الانهيار بالضبط كما وُثِّق أعلاه؛ AFTER: نفس الاستدعاء الحقيقي بلا محاكاة يصل الآن لـ`MEDICAL_REVIEW` بأمان، ومسار نظيف منفصل يصل لـ`BID_PLACED`). **الطبقة 3 (القديمة، `transfer.id` بعد `rollback()`) كانت مُغلَقة أصلًا ضمن كوميت B-E3 (`2c69baf`) قبل هذه الجلسة — لم تُلمَس هنا.** الإصلاحات الثلاثة المطبَّقة فعليًا في هذه الجلسة: (1) تغليف `governance.check_and_consume` بـ`try/except` (بلا تغيير `agent_id=6` نفسه — قرار متعمَّد: استخدام وكيل حقيقي آخر (`id=216`) كان سيُبطل ضمانة B-E3 صمتًا، راجع تحليل الأمان في تقرير التشخيص)؛ (2) حذف `from_club_id=from_club_id` المكرر في استدعاء `repo.create_transfer`؛ (3) إضافة `db.refresh(transfer)` في معالج فشل إنشاء الفاتورة (نفس نمط كتلة المراجعة الطبية المجاورة) — اكتشاف جانبي أثناء إعادة القراءة، أُدرِج بموافقة صريحة ضمن هذا التنفيذ. انحدار: 12/12 tourism_sports + 12 passed/1 xfailed (متوقَّع مسبقًا) على ai_agents/ai_governance — صفر انحدار. **اكتشاف جانبي جديد غير مُصلَح، بند backlog منفصل أدناه:** تعارض دائم في توليد `invoice_number` لتينانت 1. Commit: `edb5e5e` (`fix(tourism_sports): stop place_transfer_bid crashing on every real call (agent_id=6 unguarded governance check + duplicate kwarg + missing refresh)`). تفاصيل كاملة: `.claude/reports/tourism-sports-transfer-bid-hardcoded-agent-id-6-diagnosis-session-log.md` (التشخيص) و`.claude/reports/tourism-sports-transfer-bid-hardcoded-agent-id-6-implementation-session-log.md` (التنفيذ + الأدلة الحية BEFORE/AFTER + الديف الحرفي).

| — | **`invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`** [2026-09-23] — اكتُشف حيًا مرتين مستقلتين أثناء التحقق الحي (BEFORE/AFTER) لجلسة `tourism-sports-transfer-bid-hardcoded-agent-id-6`: `InvoicingService._generate_invoice_number` (`invoicing/service.py:115-119`) يولِّد الرقم التالي بصيغة `count_invoices(tenant_id) + 1` — غير آمن عند حذف أي صف فاتورة سابق. لتينانت 1: `count(*)=14` لكن أعلى رقم مُستخدَم فعليًا `INV-1-000015` (صف id=17 لا يزال موجودًا) — أي استدعاء `create_invoice(entity_id=1, ...)` **يفشل دائمًا** بـ`IntegrityError`/`duplicate key` على نفس الرقم بالضبط، **قفل دائم لا عرضي** (مؤكَّد بتكراره حرفيًا مرتين اليوم بمستخدمين/تحويلات مختلفين تمامًا). **مستقل تمامًا عن حجب المراجعة الطبية B-E3** (مؤكَّد: حالة `PlayerTransfer` تُلتزَم بنجاح قبل أي محاولة لإنشاء الفاتورة، وفشل الفاتورة يُعالَج بأمان الآن). صفر لمس كود — توثيق فقط. | 🟡 **مفتوح، أولوية متوسطة — يُفشِل فوترة رسوم الوكالة/أي فاتورة أخرى لتينانت 1 دائمًا، لا يحجب أي مسار حرج آخر** | `.claude/reports/invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key-backlog.md` |
| — | **`admin-kill-switch-llm-activation-gate-open-items`** [2026-09-22] — *تجميع 11 بندًا من قائمة "LLM activation gate" في تقرير 0-C §6-7، لم تُصلَح:* (B-1) قائمة تحقق قبل أي تفعيل حقيقي لاستدعاء LLM: الـkill switch ✅ (هذه الجلسة)، `POST /api/ai/chat` بلا مصادقة إلزامية (`get_current_user_optional`)، `PUT /api/ai/routing` قابل للتعديل من superuser أي تينانت (نفس نمط ثغرة الصلاحية العالمية التي أُصلحت هنا لمفتاح الإيقاف، لم تُصلَح هناك)، المحرك محاكاة بالكامل بمفاتيح API وهمية، حالة المفتاح غير دائمة (Redis فقط)؛ (B-2) لا تخزين دائم (DB) لحالة المفتاح — `FLUSHALL` على Redis يعيدها "يعمل" بصمت؛ (B-3) 25 حساب `SUPER_ADMIN` في تينانت المنصة قادرون جميعًا على تفعيل/إلغاء المفتاح (الشرط تينانت لا حساب بعينه) — يستحق مراجعة صلاحيات لاحقًا؛ (B-4) حساب `EXECUTIVE_DIRECTOR` الذي يُفترض أن ينشئه `scripts/create_superuser.py` **غير موجود فعليًا في DB** (0 صف)؛ (B-5) استهلاك حصة `AIGovernanceService.check_and_consume` يسبق رفض بوابة الـkill switch في ~14 دومينًا يستدعيها قبل `execute_agent_action` — استدعاء مرفوض يُحتسَب عليه استهلاك حصة فعليًا؛ (B-6) فولباكات AI مُختلَقة أخرى غير مغطاة بالحارس الجديد (نتيجة تصميم متعمَّد للنطاق): `employment` يُخزِّن `50` كدرجة افتراضية، `insurance`/`tenders`/`transport` استشارية بحتة؛ (B-7) بطء ذيلي محتمل للبوابة أثناء انقطاع Redis (إعادة محاولة أسية 3 مرات قبل fail-open)؛ (B-8) `core/ai_engine.py::analyze_and_recommend_courses` كود ميت فعليًا (مستورد في `academy/service.py` ولا يُستدعى من أي مكان)؛ (B-9) `POST /api/ai/chat` **بجسمه الافتراضي يرجع `500` دائمًا** (`task_type` الافتراضي `"arabic_chat"` بحروف صغيرة ≠ enum `ARABIC_CHAT`) — باج مستقل موجود قبل هذه الجلسة، غير مُصلَح؛ (B-10) نافذة سباق نظرية: لو انقلب المفتاح بين بوابتَي `execute_agent_action` والمحرك خلال نفس الطلب يُنشأ صف `ai_task_logs` بنوع `ERROR` صادق قبل رمي الاستثناء (لا رصد فعلي، قرار متعمَّد بعدم إضافة `rollback` تفاديًا لكسر identity-map لدى المستدعين)؛ (B-11) `changed_at` بتوقيت UTC بينما سجلات السيرفر بالتوقيت المحلي — قد يربك مقارنة أحداث التدقيق يدويًا. صفر لمس كود لأي بند. | ⚪ **مرجع فقط — قائمة تحقق مطلوبة قبل أي تفعيل إنتاجي لاستدعاء LLM حقيقي، لا عاجلة اليوم (المحرك محاكاة)** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §6-7 (B-1…B-11) |
| — | **`admin-kill-switch-regression-suite-side-effects`** [2026-09-22] — *لم تُصلَح، غير خاصة بمنطق الـkill switch نفسه:* أثناء تشغيل مجموعة الانحدار (147 اختبارًا) للتحقق من عدم كسر شيء بعد 0-C، ظهرت 3 آثار جانبية **من الاختبارات القديمة نفسها، ليست من تعديلات هذه الجلسة**: (1) **`admin-kill-switch-realestate-invoice-ordering-guard-stale`** — الفشل الوحيد في المجموعة (`test_realestate_buy_fractional_ownership_invoice_ordering`) حارس بنيوي (`inspect.getsource`) قديم مقابل بنية `buy_fractional_ownership` الحالية (كتلة `try/except` جديدة لاستدعاء AI أُضيفت قبل كتلة الفاتورة في جلسة أخرى غير متعلقة) — لم يُشغَّل الكود الفعلي، `realestate/service.py` لم يُلمَس في 0-C؛ (2) مجموعات الانحدار **تغيّر رصيد محفظتي حسابَي اختبار دائمَين** (`wallets.id=41`/`45`) وتترك **رسائل Celery يتيمة** في طابور `celery` (931 رسالة متراكمة من جلسات سابقة، منها اثنتان من هذه الجلسة أُزيلتا) وكاش Redis لمستخدمين محذوفين — لا baseline على مستوى الصفوف لهذين الحسابين لتمكين استعادة دقيقة مستقبلًا؛ (3) توصية منهجية: أي لقطة zero-diff مستقبلية يجب أن تحفظ صفوف `wallets`/`users` الحساسة كاملة، لا فقط md5/عدد الصفوف. **قرار المالك [2026-09-22]:** أرصدة `wallets` 41/45 تُترَك كما هي — لا استعادة (جدول `transactions` لم يتغيّر، فلا فقد محاسبي حقيقي؛ أي استعادة الآن تخمين غير مسجَّل). | 🟡 **مفتوح، أولوية متوسطة — منهجي، يخص كل مجموعات الانحدار الحية لا 0-C تحديدًا** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §الجزء الرابع (B-12، B-13، B-14) |
| — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا. **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |
| — | **`insurance-review-claim-negative-approved-amount-reverses-transfer`** [2026-09-23] — *ملاحظة بالقراءة الثابتة أثناء جلسة `insurance-review-claim-double-payment-verification`، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* `PUT /insurance/claims/{id}/review` يقبل `approved_amount` **سالبًا**: (1) `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`؛ (2) `insurance/service.py` (`final_amount = approved_amount or claimed`، سطر 524 بعد الإصلاح) — الـcap على الحد الأعلى فقط (`> max_coverage_limit`)؛ (3) **`FinanceService.transfer` (`finance/service.py:90-113`) لا يفحص `amount > 0`**: مع `amount=-50` فحص الرصيد `sender_current < -50` خطأ دائمًا → يمر، ثم رصيد المُرسِل (المراجِع) **يزيد** 50 ورصيد المستلم (المطالِب) **ينقص** 50 — وقد يصبح سالبًا (لا فحص على المستلم) — ثم `status=PAID` و`approved_amount_mrusdt=-50` وفاتورة بمبلغ سالب. **شرط الهجوم:** OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة — أي مُصدِر تأمين خبيث يسحب من مشتركيه بـ"مراجعة" مطالباتهم. **إصلاح `review_claim` [2026-09-23] لا يغلقه** (مطالبة `SUBMITTED` تقبل مراجعة أولى بمبلغ سالب). **نطاق أوسع:** `FinanceService.transfer` مشترك بين كل الدومينات — أي مستدعٍ يمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّض لنفس الانعكاس؛ و`hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا. **نقطة البداية للجلسة المخصصة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`)؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس مركزي في `transfer` (`amount <= 0 → ValidationError`) + `gt=0` في الـrouter. **ملاحظة جانبية:** `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`or`) فيُدفع المبلغ المطالَب به كاملًا. | 🔴 **غير مُتحقَّق منه — أولوية عالية (احتمال سرقة أموال)**؛ جلسة مخصصة ضيقة (قرار المستخدم 2026-09-23) | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §6، §11 |
| — | **`social-physical-gift-product-price-no-positive-constraint`** [2026-09-23] — اكتُشف في جلسة `insurance-negative-approved-amount-verification` (§3/§ب، الصف 24): `social/schemas.py:169` `product_price_mrusdt` بلا `gt=0` ولا حارس في `request_physical_gift` (`social/service.py:590`). منذ `58b30af` المبلغ غير الموجب يُرفض مركزيًا في `FinanceService` (422) — المتبقي دفاع إضافي على مستوى الـschema فقط. أولوية منخفضة. |
| — | **`projects-contribution-amount-no-positive-constraint`** [2026-09-23] — نفس الجلسة (الصف 16): `projects/schemas.py:69` `amount_mrusdt` (Optional) بلا `gt=0`؛ المساهمة النقدية تمرره مباشرة لـ`finance.transfer` (`projects/service.py:185`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`transport-booking-seats-count-no-min`** [2026-09-23] — نفس الجلسة (الصف 36): `transport/schemas.py:131` `seats_count` بلا `ge=1` → `fare = base_fare × seats_count` سالب/صفر → `hold_funds` (`transport/service.py:478`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`merchant-set-prices-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (فئة B): أسعار يضعها تاجر/منشئ/صاحب عمل/مسؤول بلا `ge=0`: commerce `price_mrusdt`/`wholesale_price_mrusdt` (`schemas.py:44,50`)، tourism_sports `base_price_mrusdt`/`base_ticket_price_mrusdt` (`schemas.py:44,97`)، transport `base_fare_mrusdt` (`schemas.py:101`)، social أسعار خطط المجموعات (`schemas.py:184-185`)، saas `price_monthly` (`schemas.py:39`)، employment `base_salary` (`schemas.py:70`). قبل `58b30af`: سعر سالب → 500 للمشتري؛ بعده → 422. المتبقي قيود schema. أولوية منخفضة. |
| — | **`digital-twin-negative-duration-free-interaction`** [2026-09-23] — نفس الجلسة (الصف 6): `digital_twin/schemas.py:49` `duration_minutes` بلا قيد → `fee × duration` سالب → حارس `if fee > 0` يتخطى الدفع → تفاعل مجاني يُسجَّل بمدة سالبة (ليس عكس أموال؛ الحارس المركزي لا يلتقطه لأن `transfer` لا يُستدعى). أولوية منخفضة. |
| — | **`no-global-integrityerror-handler`** [2026-09-23] — نفس الجلسة: `app/main.py` فيه handlers لـ`SovereignError`/`IdempotencyError`/`RateLimitError` فقط؛ أي انتهاك قيد DB يخرج كـ500 عام بلا traceback في اللوج (مُثبت حيًا في B3 قبل الإصلاح). أولوية منخفضة–متوسطة. |
| — | **`review-claim-zero-amount-falls-back-to-claimed`** [2026-09-23] — نفس الجلسة: `insurance/service.py:524` `final_amount = approved_amount or claimed` — `Decimal("0")` falsy → الموافقة بـ0 تدفع كامل المبلغ المطالب به (مُثبت حيًا: B8 قبل الإصلاح، N8 بعده). عبر HTTP مغلق منذ `58b30af` (`gt=0` → 422)؛ مستدعٍ داخلي يمرر 0 مباشرة لا يزال يدفع كاملًا. الإصلاح: `approved_amount if approved_amount is not None else claimed`. أولوية منخفضة. |
| — | **`social-group-subscription-duration-months-no-min`** [2026-09-23] — نفس الجلسة (الصف 25): `social/schemas.py:196` `duration_months` من الطلب بلا حد أدنى (`social/router.py:389`) → `price_monthly × duration_months` سالب/صفر (`social/service.py:671`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema (`ge=1`). أولوية منخفضة. |
| — | **`transport-delivery-fee-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 38): `DeliveryTaskCreate.delivery_fee_mrusdt` (`transport/schemas.py:157`) بلا `ge=0` — المُرسِل يضع الرسوم (`transport/service.py:701`) ثم هو نفسه الدافع (`hold_funds`، `service.py:814`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`tenders-min-increment-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 32): `tenders_auctions/schemas.py:75` `min_increment_mrusdt` بلا `ge=0` → منشئ المزاد يضع زيادة سالبة → `min_required = current_highest + min_increment` (`service.py:390`) قد يصبح سالبًا → مزايدة سالبة تصل `hold_funds`. مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |

**✅ إغلاق مؤرَّخ [2026-09-23] — `insurance-review-claim-negative-approved-amount-reverses-transfer`: مُغلَق (commit `58b30af`)، مع تصحيح تصنيف الخطورة.** جلسة `insurance-negative-approved-amount-verification` (تقرير: `.claude/reports/insurance-negative-approved-amount-verification-session-log.md`). **التصحيح:** الملاحظة الأصلية ("مُصدِر خبيث يسرق أموال المُطالِبين بمبلغ سالب") **بُنيت على قراءة ناقصة** — فاتها قيود DB: `transactions.check_transaction_amount_positive` (`CHECK (amount > 0)`، migration `71820e4fe1f3...:2034`) و`wallets.check_wallet_balances_non_negative` / `check_wallet_held_balances_non_negative`. كل دوال `FinanceService` الأربع تُحدِّث المحافظ وتُدرج صف `Transaction` داخل نفس `begin_nested()` بلا commit داخلي → أي مبلغ `<= 0` يُلغى بالكامل. **BEFORE (حي، تينانت throwaway 144، كود غير مُصلَح):** B1–B7 — `review_claim(-50)` (بمُطالِب رصيده 0 ثم 100)، HTTP (`-50`)، و`transfer`/`hold_funds`/`release_held_funds`/`settle_held_funds(-10)` مباشرة — **كلها `IntegrityError` بصافي تغيير صفر** (لا حركة أموال)، لكن العميل يتلقى **HTTP 500**؛ B6/B7 أثبتا أن قيد `transactions` هو **الحاجز الوحيد** لـrelease/settle (قيود المحفظة مرّت)؛ B8 — `approved_amount=0` **دفع كامل المطالبة (20)**. **الخطورة الفعلية:** hardening + تصحيح كود خطأ (منخفضة–متوسطة)، **ليست سرقة**. **الإصلاح (2 ملف، +15/−5):** حارس `amount <= 0 → ValidationError (422)` في أول الدوال الأربع قبل أي SQL (`finance/service.py`)؛ `approved_amount: Query(None, gt=0)` (`insurance/router.py:225`). **AFTER (تينانت 145):** 15/15 — الدوال الأربع ترفض `-10` و`0` بـ**صفر عبارات SQL** (مستمع `before_cursor_execute`)؛ HTTP `-50`/`0` → 422؛ التدفقات الموجبة (موافقة 50 عبر HTTP، hold→release→hold→settle) سليمة؛ الموافقة بـ0 عبر الخدمة مباشرة لا تزال تدفع كاملًا (backlog `review-claim-zero-amount-falls-back-to-claimed`). **اختبار دائم:** `tests/test_finance_non_positive_amount_guard.py` — 10/10 على الإصلاح، 10/10 FAIL على HEAD (mutation check). **Regression:** 26/26 (insurance status guard، FINBIND، tenders hold/release/settle، 4 مجموعات transport). **تنظيف:** التينانتان 144 (17 صفًا) و145 (29 صفًا) حُذفا بالكامل، صفر متبقٍ. **مواقع الاستدعاء:** 40 موقعًا لـ`transfer`/`hold`/`release`/`settle` صُنِّفت (7 A، 10 B، 23 S) — الحارس المركزي يغطيها كلها؛ قيود الـschema لمواقع A/B → 10 بنود backlog أعلاه (توثيق فقط، بقرار المستخدم).

---

## [2026-09-01] درس عام — انتهاك تحذير Backlog موثَّق صراحة أثناء "إصلاح نمطي" لاحق

**السياق:** جلسة `backlog-16-begin-nested-commit-conflict` (راجع `.claude/reports/backlog-16-begin-nested-commit-session-log.md`) اكتشفت أن commit `b4bf356` [2026-08-29، جلسة `constructor-mismatch-backlog-cleanup`، بند #40 في رسالة الـcommit] **صحّح فعليًا** `tenant_id=`/`idempotency_key=` في `realestate/service.py:306` (نداء `execute_agent_action` جوّه `buy_fractional_ownership`) — **رغم أن هذا الموضع بالتحديد كان مُستثنى عمدًا بقرار صريح موثَّق** في `.claude/reports/ai-agents-execute-action-fix-session-log.md` §6-7 [2026-08-18]: "**لا يُطبَّق أي إصلاح على الموضعين... حتى لو بدا الحل 'بسيط'**" — لأن تصحيح الـkwargs بمعزل عن حل بنية `begin_nested()`/`commit()` كان سيجعل الكود يصل لأول مرة فعليًا لتلف حالة transaction حقيقي.

**ما حصل فعليًا:** جلسة `#40` عالجت هذا الموضع كجزء من نمط عام متكرر (17 موضع مشابهة، نفس الشكل الحرفي: حذف `tenant_id=` + إضافة `idempotency_key=`) **بدون** مراجعة التحذير الخاص المُوثَّق مسبقًا لهذا الموضع تحديدًا. النتيجة: الكود وصل فعليًا لـ`self.db.commit()` الداخلي جوّه `begin_nested()` الخارجي، وأنتج `sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager` — بالضبط كما حذَّر التقرير الأصلي (مؤكَّد حيًا بسكربت `repro_begin_nested_commit.py`). **الموضع الشقيق (`invitations/service.py:415`) لم يُلمَس في نفس الجلسة — يبدو أن الاستثناء طُبِّق بشكل غير متسق (ربما لأن `realestate` بدا "من نفس المجموعة الآمنة الـ17" بينما `invitations` احتفظ بشكل مختلف قليلًا يميّزه بصريًا).**

**الدرس العام (لأي جلسة "إصلاح نمطي/ميكانيكي" مستقبلية):** قبل تطبيق نفس التعديل على مجموعة مواضع تبدو متطابقة الشكل، **افحص صراحة هل أي موضع من المجموعة له تحذير/استثناء موثَّق مسبقًا في تقرير جلسة سابقة أو في `PROGRESS_LOG.md`** — تشابه الشكل السطحي (نفس الـkwarg، نفس نوع التعديل) **لا يضمن** تطابق الأمان أو السياق (هنا: وجود `begin_nested()` محيط غيّر الأثر الفعلي بالكامل). التوصية العملية: `grep` عن اسم الدالة/الموضع في كل تقارير `.claude/reports/*.md` وفي `PROGRESS_LOG.md` نفسه **قبل** تطبيق أي "دفعة إصلاحات مشابهة"، وأي موضع عليه علم 🔴 مستثنى صراحة يُعامَل بمعزل تام عن باقي الدفعة حتى لو بدا الإصلاح مطابقًا حرفيًا.

**الحالة:** ✅ الموضعان (`realestate`, `invitations`) اتصلحا بنيويًا بشكل صحيح في نفس جلسة `backlog-16-begin-nested-commit-conflict` (نقل `execute_agent_action()` بره حدود `begin_nested()`، تفاصيل كاملة في التقرير المرجعي أعلاه). هذا القسم توثيق للدرس العام فقط، مش بند عمل معلَّق.

---

## [2026-09-01] بند Backlog جديد — `ai-governance-check-and-consume-commit-inside-begin-nested`

**الوصف:** `AIGovernanceService.check_and_consume()` (`ai_governance/service.py:165-200`) عندها **نفس بالضبط** عيب `begin_nested()`+`commit()` داخلي الموصوف في بند `ai-agents-execute-action-commit-inside-begin-nested` (Backlog #16) — تفتح `begin_nested()` خاصة بيها (سطر 165)، وبعد الخروج منها تعمل `await self.db.commit()` مستقل (سطر 200) — **بالضبط نفس بنية `execute_agent_action()`**.

**موضع مؤكَّد حيًا:** `realestate._check_ai_governance()` (`realestate/service.py:69-81`) بتنادي `check_and_consume()` من **جوّه** `begin_nested()` الخارجي بتاعة `buy_fractional_ownership()` نفسها (السطر بعد حساب `cost`، قبل `_get_land_owner_for_unit`) — غير متأثرة بإصلاح جلسة `backlog-16-begin-nested-commit-conflict` (اللي عالجت `execute_agent_action` بس). **الأثر المؤكَّد حيًا:** الاستثناء (`InvalidRequestError`) بيتبلع فعليًا بـ`try/except` موجودة أصلاً في `_check_ai_governance`، لكن الجلسة (`AsyncSession`) بتفضل بحالة transaction "مقفولة" (`DEACTIVE`) — أي عملية DB تالية غير محمية بـ`try/except` (زي `_get_land_owner_for_unit` مباشرة بعدها) بتفشل بنفس النوع من `InvalidRequestError` غير معالَج، وتُسقِط `buy_fractional_ownership` بالكامل.

**احتمال الانتشار:** `check_and_consume()` مُستخدَمة عبر 8+ دومينات (راجع بند `ai-governance-check-and-consume-wrong-kwarg`، #15، في `constructor-mismatch-backlog-classification.md`) — أي دومين ينادي `check_and_consume()` (مباشرة أو عبر helper زي `_check_ai_governance`) من **جوّه** `begin_nested()` خاصة بيه معرَّض لنفس النمط. لم يُفحَص شموليًا في هذه الجلسة (خارج نطاقها) — يحتاج نفس منهجية الجرد المُتَّبعة في `transaction-savepoint-bug-session-log.md` (`grep` شامل لكل استدعاء `check_and_consume` + فحص هل محاط بـ`begin_nested()` خارجي).

**الحل المتوقَّع (بناءً على سابقة #16):** نفس المبدأ — `check_and_consume()` لها كولرز مستقلة (بلا `begin_nested()` محيط) تحتاج الـ`commit()` الداخلي فعليًا، فالإصلاح يكون في الكولرز المتضررة (نقل النداء بره `begin_nested()` بتاعتها)، مش في `check_and_consume()` نفسها — يحتاج قرار/جلسة منفصلة.

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر إصلاح. اكتُشف أثناء التحقق الحي لجلسة `backlog-16-begin-nested-commit-conflict` (`.claude/reports/backlog-16-begin-nested-commit-session-log.md` §5.4).

**✅ اتحل [تأكيد 2026-09-16]** — أُغلق رسميًا في جلسة `ai-governance-check-and-consume-begin-nested` [2026-09-01] (راجع قسم "✅ إغلاق" أسفل هذا البند في نفس الملف). تأكيد إضافي أثناء مراجعة backlog دورية: `.claude/reports/backlog-review-2026-09-16-session-log.md`.

---

## [2026-09-01] بند Backlog جديد — `invitations-chat-with-ai-reply-key-mismatch`

**الوصف:** `InvitationsService.chat_with_ai()` (`invitations/service.py`) بتبني رد الـAI هكذا:
```python
reply_text = ai_response.get("result", {}).get("reply", "شكراً لتواصلك. كيف يمكنني مساعدتك؟")
```
لكن `ai_response["result"]` مصدرها القيمة اللي بترجعها `ai_engine.generate()` الحقيقية (`services/ai/engine.py:157`) — **ومفتاحها الفعلي هو `"text"`, مش `"reply"` إطلاقًا** (`{"text": generated_text, "model": ..., "usage": {...}, ...}`). يعني `ai_response.get("result", {}).get("reply", <fallback>)` **بترجع نص الـfallback الثابت دايمًا**، بغض النظر عن رد الـAI الفعلي — `chat_with_ai` كسول وظيفيًا: العميل بيدردش مع نص افتراضي واحد ("شكراً لتواصلك...") مهما كان محتوى رد النموذج الحقيقي.

**الأثر:** ميزة "الدردشة مع الـAI" في CRM الدعوات (`invitations`) لا تعمل فعليًا كما هو متوقَّع — الرد المعروض للعميل ثابت دايمًا، مش رد ذكي حقيقي. باج مستقل تمامًا عن begin_nested/commit، **موجود من قبل جلسة `backlog-16-begin-nested-commit-conflict` وبعدها** (لم يُنشأ ولم يُصلَح في هذه الجلسة).

**الحل المتوقَّع:** تغيير المفتاح المقروء من `"reply"` إلى `"text"` (`ai_response.get("result", {}).get("text", <fallback>)`) — يحتاج تأكيد إضافي إن `"text"` هو المحتوى الصحيح المطلوب عرضه للعميل (مش مجرد تصحيح اسم مفتاح أعمى)، وتحقق حي بعده يثبت إن رد فعلي متغيّر (مش نص ثابت) بيوصل للعميل.

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر إصلاح. اكتُشف أثناء التحقق الحي لجلسة `backlog-16-begin-nested-commit-conflict` (`.claude/reports/backlog-16-begin-nested-commit-session-log.md` §5.2/§5.4) — الاختبار الجديد `test_invitations_chat_with_ai_execute_agent_action_now_fixed` وثّق السلوك الحالي الحقيقي (نص fallback) صراحة كتحفّظ، بدل افتراض سلوك غير موجود.

---

## [2026-09-01] بند Backlog — تأكيد إضافي على `invoicing-create-invoice-numbering-collision` (معروف مسبقًا، commit `b4bf356`)

**الوصف:** `InvoicingService.create_invoice()` بتفشل بتكرار بـ`IntegrityError` على قيد `invoices_invoice_number_key` — نفس الاكتشاف الموثَّق أصلًا في رسالة commit `b4bf356` ("an invoice-numbering collision surfaced while testing #37"، غير مُصلَح وقتها). **تأكيد حي إضافي [2026-09-01]:** نفس رقم الفاتورة بالحرف (`INV-1-000015`) تكرر عبر 3 تشغيلات throwaway مختلفة تمامًا لجلسة `backlog-16-begin-nested-commit-conflict` — يبدو إن آلية توليد الرقم مش بتعتمد فعليًا على قيمة متزايدة يتم قراءتها/تحديثها بشكل ذرّي وموثوق (سباق أو منطق عداد ثابت/كاش).

**اكتشاف جانبي جديد (تفاعل مع بج آخر معروف — نمط "عدم `rollback()` صريح بعد استثناء DB مُمسوك"، موثَّق سابقًا في `transaction-savepoint-bug-session-log.md`):** الـ`try/except` الموجودة حول `create_invoice()` في `realestate.buy_fractional_ownership` (ونظيراتها في دومينات تانية، نمط #11b) بتمسك الاستثناء وتسجّله بـ`logger.error()`، **لكن الجلسة (`AsyncSession`) بتفضل بحالة `PendingRollbackError`** بعد الفلاش الفاشل (`expire_on_commit=True` الافتراضي بيخلي أي وصول تالٍ لخاصية ORM منتهية الصلاحية على نفس الجلسة يفشل). **مؤكَّد حيًا:** الوصول لـ`ownership.acquisition_date` (في فرع تخزين الـidempotency، بعد `create_invoice()` الفاشلة) بيفشل بـ`PendingRollbackError` غير معالَج، ويُسقِط `buy_fractional_ownership` بالكامل رغم إن الشراء نفسه نجح فعليًا قبل هذه النقطة.

**الحل المتوقَّع (شقّان منفصلان):** (أ) إصلاح آلية توليد `invoice_number` نفسها (خارج نطاق هذا التوثيق، يحتاج فحص الكود المولِّد). (ب) نمط عام: أي `except Exception` بيمسك استثناء DB (فشل flush/commit) **لازم يعمل `await self.db.rollback()` صريح** قبل أي استمرار على نفس الجلسة — مش بس `logger.error()` — وإلا أي كود لاحق في نفس الجلسة معرَّض لنفس فئة `PendingRollbackError` (يحتاج جرد شبيه بـ`transaction-savepoint-bug-session-log.md` لكل مواضع `except Exception` المحيطة بعمليات DB في المشروع).

**الحالة:** 🔴 مفتوح (كلا الشقين)، موثَّق فقط، صفر إصلاح في هذه الجلسة (تم تجاوزه بـ`monkeypatch` معزول في الاختبار فقط، صفر لمس على كود الإنتاج). اكتُشف/تأكَّد أثناء التحقق الحي لجلسة `backlog-16-begin-nested-commit-conflict` (`.claude/reports/backlog-16-begin-nested-commit-session-log.md` §5.4).

---

## [2026-09-01] ✅ إغلاق — `ai-governance-check-and-consume-commit-inside-begin-nested` (تابع مباشر لدرس #16)

**السياق:** هذا إغلاق للبند المفتوح أعلاه (نفس التاريخ) بجلسة منفصلة
`ai-governance-check-and-consume-begin-nested` — **تابع مباشر ومتعمَّد لنفس
درس §16** ("انتهاك تحذير Backlog موثَّق أثناء إصلاح نمطي لاحق"، القسم أعلاه)،
مش اكتشاف جديد: نفس فئة العطل بالحرف (`begin_nested()`+`commit()` داخلي
مستقل)، فى دالة حوكمة مختلفة (`check_and_consume`) بدل `execute_agent_action`،
واتصلحت بنفس المنهجية بالضبط (جرد كامل لكل الكولرز، تحقق حي بسكربت throwaway
قبل أي تنفيذ، نقل موضع النداء بدل تعديل الدالة المشتركة).

**التقرير الكامل:** `.claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md`.

**الفرق البنيوي المكتشَف عن #16 (مهم لأي بحث مستقبلي مشابه):** `check_and_consume()`
بتفتح `begin_nested()` **خاصة بيها هي** وتغلقها بشكل طبيعي قبل الـ`commit()`
الداخلي — فالاستثناء (`InvalidRequestError: Can't operate on closed
transaction`) **لا** يحدث عند نداء الدالة نفسها (خلافًا لـ`execute_agent_action`)،
بل عند **أول عملية DB تالية** جوّه أي `begin_nested()` خارجي محيط. مؤكَّد
حيًا بسكربت throwaway مستقل قبل الإصلاح (تشغيلتان: بدون/مع SELECT تالية).

**الجرد:** 15 موضع استدعاء عبر 14 دومين + الراوتر — **موضع واحد بس** متأثر:
`realestate.buy_fractional_ownership()` (عبر `_check_ai_governance()`، جوّه
`begin_nested()` الخاص بالشراء). الـ14 الباقيين مستقلون تمامًا (يعتمدون على
الـ`commit()` الداخلي، بلا تغيير).

**الإصلاح المُطبَّق:** نقل نداء `self._check_ai_governance(...)` (كان سطر 303
جوّه `begin_nested()`) لبعد `self.db.commit()` الرئيسي، بجوار `ai.execute_agent_action`
الموجودة هناك بالفعل من إصلاح #16 أمس — بلا `try/except` إضافية (الدالة عندها
واحدة داخلية أصلًا). صفر لمس على `check_and_consume()` نفسها.

**اختبار جديد:** `tests/test_ai_governance_begin_nested.py` (اختبارين: مسار
شرعي كامل عبر `buy_fractional_ownership()` الحقيقية بلا أي `monkeypatch` على
الحوكمة، + نداء مستقل مباشر لـ`check_and_consume()` يثبت الشكل الصحيح
المستخدَم في الـ14 دومين الآخرين) — **كلاهما PASSED** ضد DB حقيقية.

**الحالة:** ✅ مُغلَق بالكامل. `realestate/service.py`،
`tests/test_ai_governance_begin_nested.py` مُعدَّلان ومُتحقَّق منهما حيًا.

---

## [2026-09-01] بند Backlog جديد — `realestate-ai-governance-quota-not-enforced`

**الوصف:** اكتُشف أثناء جلسة `ai-governance-check-and-consume-begin-nested`
(أثناء تحليل نقل نداء `_check_ai_governance`، خارج نطاق إصلاح begin_nested
نفسه): `RealEstateService._check_ai_governance()` (`realestate/service.py:69-81`)
بترجع `result: bool` (ناتج `check_and_consume()` — `True` لو الاستهلاك
مسموح، `False` لو تجاوز الحصة)، **لكن** الكولر الوحيد
(`buy_fractional_ownership`) بينادي `await self._check_ai_governance(...)`
**كـstatement مجرد، بلا استخدام القيمة المُرجَعة إطلاقًا** — لا `if not
result: raise PermissionDeniedError(...)`، ولا أي فحص من أي نوع.

**الأثر:** حتى لو الحصة (quota) الخاصة بالوكيل (`agent_id=2`) اتجاوزت فعليًا
(`check_and_consume` ترجع `False` بشكل صحيح)، **عملية شراء الملكية الجزئية
(`buy_fractional_ownership`) لا تُمنَع أبدًا** — الحوكمة (governance) لا تعمل
فعليًا كبوابة (choke-point) لهذه العملية تحديدًا، رغم أن هذا هو الغرض
المُعلَن من `check_and_consume()` (راجع تعليق "نقطة الخنق والتنفيذ" في
`ai_governance/service.py:142-145`).

**ملاحظة مهمة:** إصلاح begin_nested (أعلاه) **لا يغيّر ولا يُصلِح هذا
السلوك** — نقل موضع النداء لبعد الـ`commit()` لا يؤثر على حقيقة أن القيمة
المُرجَعة كانت وهتفضل غير مستخدَمة على أي حال (كانت غير مستخدَمة قبل النقل
وبعده على حد سواء).

**الحل المتوقَّع (يحتاج قرار منتج/عمل منفصل، خارج نطاق begin_nested):** إما
(أ) `_check_ai_governance` تفحص القيمة المُرجَعة وترفع `PermissionDeniedError`
صراحة لو `False`، أو (ب) توثيق صريح إن الحوكمة هنا "استشارية فقط" (best-effort
logging) وليست بوابة إلزامية — قرار يحتاج مراجعة منتج، مش تخمين تقني.

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر إصلاح — يحتاج جلسة/قرار منفصل.
`.claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md`.

---

## [2026-09-01] بند Backlog جديد — `agritech-full-domain-build`

**الوصف:** اكتُشف أثناء جلسة `frontend-category-b-phase1-cheap-wins` (البند
1، "agritech routing"، أعلى أولوية في تلك الجلسة). مقارنة `main.py.bak`
(يحوي `agritech_router` مسجَّل) بـ`main.py` الحالي (لا وجود لـagritech
إطلاقًا) كشفت إن هذا مش نسيان تسجيل — commit موثَّق ومقصود
(`9e01ede`, 2026-08-26, `fix(agritech): remove duplicate ai_governance
router mistakenly mounted at /agritech`) شال `router.py` القديم لأنه كان
**نسخة مكررة بالغلط من `ai_governance/router.py`** (نفس الـheader، نفس
الـendpoints بتستخدم `AIGovernanceService`) — لم يقدّم أي API حقيقي
لـagritech حتى وقت ما كان "مسجَّل". راجع
`.claude/reports/agritech-status-check-2026-08-26.md` (تفاصيل الفحص
الأصلي) و`.claude/reports/category-b/group2-tourism-tenders-agritech.md`
(تصنيف الحالات).

**الحالة الحقيقية لـagritech الآن:** `service.py`/`models.py`/
`repository.py`/`schemas.py` (~1454 سطر) موجودة وسليمة وظيفيًا (منطق كامل:
farms, crop cycles, harvest, bio assets, traceability QR, certificates,
soil sensors, weather alerts)، لكن **orphaned بالكامل** — صفر `router.py`،
صفر تسجيل في `main.py`، صفر نقطة استدعاء (حتى `tasks/agritech.py` عنده
import ميت). جداول DB موجودة في migration.

**القرار الموثَّق سابقًا (وأُعيد تأكيده في هذه الجلسة):** بناء `router.py`
حقيقي لـagritech **قرار منتجي مؤجَّل، مش bug fix ولا "وصلة فقط"** — يحتاج
تصميم ~11 endpoint من الصفر (مش استرجاع القديم، كان تالف)، بالإضافة لـ3
مكوّنات UI مفقودة (`FarmCard`, `FarmZoneCard`, `WeatherAlertCard`) فوقه.
هذا يرقّى agritech لحجم **"بناء دومين كامل"** — يشبه حجم عمل `transport`
(راجع commit `fffd5fe`)، مش حالة "وصلة فقط" مايكروية.

**الحل المتوقَّع:** جلسة مستقلة مخصَّصة (زي transport) تتضمن: (أ) تصميم
`router.py` جديد كليًا لكل الـ11 endpoint، (ب) توصيله بـ`service.py`/
`repository.py` الموجودين فعليًا، (ج) تسجيله في `main.py` (نمط
`routers_config` الحالي، بلا `require_sector` — أُلغيت مشروعيًا)، (د)
دفعة أمنية كاملة (tenant scoping, ownership checks) زي باقي الدومينات —
لأنه هيكون سطح هجوم جديد بالكامل، (هـ) الثلاثة مكوّنات UI فوقه بعد اكتمال
الـAPI.

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر إصلاح/تفعيل في هذه الجلسة (بناءً على
موافقة المستخدم الصريحة بعدم اللمس) — يحتاج جلسة منفصلة لاحقًا.
`.claude/reports/frontend-category-b-phase1-session-log.md`.

---

## [2026-09-01] جلسة `frontend-category-b-phase1-cheap-wins` — إغلاق مرحلي

**السياق:** المرحلة 1 من خطة إصلاح ~290 حالة فئة (ب) المصنَّفة في جلسة
`frontend-category-b-classification-all-domains` (راجع
`.claude/reports/category-b/group1..group5-*.md`). النطاق: أرخص وأضمن
119 حالة "وصلة فقط" (أ) + بند agritech الحرج + 11 مكوّن UI فوق API جاهز.
توقَّفت الجلسة عند نقطة منطقية بموافقة المستخدم، بدل تنفيذ كل الحالات
دفعة واحدة. التفاصيل الكاملة والدقيقة لكل حالة:
`.claude/reports/frontend-category-b-phase1-session-log.md`.

**البند 1 (agritech):** ✅ مغلق — رُقِّي لبند backlog مستقل منفصل، راجع
`agritech-full-domain-build` أعلاه في نفس الملف.

**البند 2 (119 حالة "وصلة فقط") — 40/119 مُنجَزة عبر 11 دومين كامل:**

| الدومين | حالات مُنجَزة | باك إند لُمس؟ |
|---|---|---|
| arbitration-syndicates | 6/7 (1 مؤجَّلة — `getElections` يحتاج query repository جديد، خارج حدود "صفر قرار تصميم") | لا |
| zamakana | 6/6 | لا |
| logistics | 6/6 | لا |
| automation | 6/6 | لا |
| health | 2/2 | لا |
| marketplace | 2/2 | لا |
| employment | 3/3 | **نعم** — `EmploymentService.get_job` + `GET /employment/jobs/{job_id}`، تحقَّق منه حيًا بـ`pytest` ضد DB حقيقية (`tests/test_employment_get_job_wiring.py`, PASSED) |
| ai-governance/ai-agents | 4/4 | لا |
| digital-twin | 2/2 | لا |
| saas | 1/1 | لا |
| communications | 1/1 | لا |

**تأكيد مهم:** `employment` هو الدومين الوحيد من الـ11 اللي احتاج أي
تعديل باك إند في هذه الجلسة — كل الباقي كان توصيل فرونت إند بحت (named
exports/aliases فوق endpoints جاهزة بالكامل مسبقًا)، صفر تعديل على
`router.py`/`service.py`/`repository.py` لأي دومين آخر.

**الباقي من البند 2 (~79 حالة، لم يبدأ):** realestate (12، الباك إند
جاهز من جلسة سابقة، الفرونت إند لسه محتاج تصدير أسماء)، insurance (10)،
invitations (5 aliases)، social (11)، transport (9)، tourism-sports (4)،
tenders-auctions (10)، manufacturing (4)، command (2)، + سطور متفرقة
(commerce/academy/projects/finance-wallet، ~5).

**البند 3 (11 مكوّن UI فوق API جاهز):** 🔴 لم يبدأ. 5 invitations + 1
tourism-sports (`TransferCard`) قابلة للتنفيذ لاحقًا. **3 مكوّنات
agritech محظورة بالكامل** — نفس سبب حظر بند agritech routing أعلاه (API
غير جاهز، صفر endpoint قابل للوصول).

**الحالة:** 🟡 مرحلة 1 مُغلَقة جزئيًا بنجاح — 40/119 + agritech موثَّق
كبند backlog منفصل. المتبقي (~79 حالة من البند 2 + البند 3) يحتاج جلسة/
جلسات لاحقة بنفس المنهجية.

---

## [2026-09-02] بند Backlog جديد — `insurance-update-claim-permission-asymmetry`

**الوصف:** أثناء جلسة `frontend-category-b-phase2-remaining-domains`، أُضيف
endpoint جديد `PATCH /insurance/claims/{claim_id}` (`update_claim`) كوصلة
ميكانيكية فوق `repository.update_claim` الموجودة بالفعل. الـendpoint
الموجود سابقًا `PUT /insurance/claims/{claim_id}/review` (`review_claim`)
يستخدم صلاحية مبنية على membership role (`OWNER`/`EXECUTIVE_DIRECTOR` لكيان
البوليصة المُصدِر). بدل بناء نفس منطق الـmembership check لـ`update_claim`
الجديدة (يحتاج استيراد/استخدام `membership service` بمنطق تفويض إضافي —
يتجاوز "وصلة ميكانيكية بحتة")، اتّخذ قرار متحفِّظ: تقييد `update_claim`
بـ`get_current_superuser` فقط — بوابة أضيق من `review_claim` (superuser
منصة بدل مالك/مدير الكيان تحديدًا).

**الأثر:** الاثنان الآن عندهم نطاقا صلاحية مختلفان لعملية مشابهة على نفس
المورد (`InsuranceClaim`) — `review_claim` (الموافقة/الرفض + صرف مالي)
متاحة لمديري الكيان، بينما `update_claim` (تعديل حقول عامة زي
`investigation_notes`) مقيَّدة لـsuperuser المنصة بس. هذا تناقض تصميمي
بسيط، مش ثغرة أمنية (البوابة الجديدة أضيق، مش أوسع)، لكنه يستاهل قرار
منتجي: هل `update_claim` يجب أن تستخدم نفس فحص membership الخاص بـ
`review_claim`؟ أم البقاء superuser-only مقصود (تمييز "تعديل إداري عام"
عن "قرار مراجعة الكيان")؟

**✅ [مُغلَق، 2026-09-04، جلسة `category-b-decision-needed-triage`]:** قرار
المستخدم صريح — تبقى `update_claim` `superuser`-only كما هي، صفر تعديل.
التناقض التصميمي موثَّق أعلاه لأي مراجعة مستقبلية، لكنه ليس backlog نشط.

**الحالة:** ✅ مغلق (قرار: البقاء كما هو). `.claude/reports/frontend-category-b-phase2-session-log.md` قسم insurance، `.claude/reports/category-b-decision-needed-triage-session-log.md`.

**✅ اتحل [تأكيد 2026-09-16]** — تأكيد إضافي أثناء مراجعة backlog دورية: القرار (البقاء superuser-only) لسه ساري، صفر تعديل كود لاحق. `.claude/reports/backlog-review-2026-09-16-session-log.md`.

---

## [2026-09-02] بند Backlog جديد — `api-types-schema-name-collision-auction-tender-create`

**الوصف:** أثناء جلسة `frontend-category-b-phase2-remaining-domains`،
اكتُشف (عبر تحقق `tsc` نهائي شامل) أن `components['schemas']['AuctionCreate']`
و`TenderCreate` في `eppne-web/src/lib/api-types.ts` **المولَّد حاليًا** لا
يطابقان الـPydantic schemas الفعلية في
`eppne-backend/app/domains/tenders_auctions/schemas.py` إطلاقًا — النوع
المولَّد يحمل حقولًا غريبة تمامًا (`entity_id`, `opening_date`,
`closing_date`, `booklet_price_mrusdt`, `bid_bond_mrusdt`,
`settlement_type`, `min_sovereign_rank_required`...) لا علاقة لها بـ
`tenders_auctions` — تلمّح لتصادم اسم class Python مع دومين آخر (schema
بنفس الاسم الحرفي `TenderCreate`/`AuctionCreate` في دومين مختلف، ربما
realestate أو invoicing) بيغلب في توليد OpenAPI (FastAPI/Pydantic
بيستخدم `__name__` الكلاس لتسمية component، فأي تصادم اسم عبر دومينين
مختلفين بيتسبب في استبدال صامت لواحد بالتاني في `openapi.json`).

**الأثر:** أي كود فرونت إند يعتمد على `components['schemas']['AuctionCreate']`/
`TenderCreate` المولَّدة حاليًا هيحصل على types خاطئة تمامًا (autocomplete
مضلِّل، وربما أخطاء compile لو استُخدمت الحقول الخاطئة فعليًا). تم
تجاوزها في هذه الجلسة بكتابة نوع `createAuction` يدويًا في
`services/tenders-auctions.ts` مطابق للـschema الحقيقي بدل الاعتماد على
النوع المولَّد.

**الحل المتوقَّع:** (أ) تتبع مصدر التصادم (`grep` عن class مسمّاة
`TenderCreate`/`AuctionCreate` في دومين تاني)، (ب) إعادة تسمية أحد الطرفين
(أو استخدام namespace/tag مميّز في FastAPI)، (ج) إعادة توليد
`api-types.ts` من `openapi.json` محدَّث. يحتاج جلسة/تحقيق منفصل — خارج
نطاق "وصلة ميكانيكية".

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر إصلاح جذري (فقط تجاوز محلي في ملف
واحد). `.claude/reports/frontend-category-b-phase2-session-log.md` قسم
tenders-auctions.

**⚠️ توسيع [2026-09-04، جلسة `category-b-decision-needed-triage`]:** اكتُشف
جانبيًا أثناء التحقق من `transport-formdata-vs-openapi-schema-mismatch`
(البند اتأكد إنه اتحل بالفعل بالباك إند في جلسة `transport-domain-full-build`
2026-09-01 — `GeoAddress`/`Waypoint` sub-models حقيقية موجودة في
`transport/schemas.py`) إن **`api-types.ts` المولَّد لسه قديم ومايعكسش
الإصلاح**: `RouteCreate.waypoints`/`RouteResponse.waypoints` لسه
`Record<string, never>[]` بدل شكل `Waypoint` الحقيقي. بلا أثر عملي حاليًا
(الفرونت إند بيستخدم `types/transport.ts` اليدوي السليم، مش النوع المولَّد
مباشرة) — لكنها **نفس فئة المشكلة بالضبط**: schema generation قديم/ملوَّث
في `api-types.ts` مش متزامن مع الباك إند الفعلي، عبر دومينين مختلفين
(tenders-auctions بتصادم اسم، transport بعدم إعادة توليد بعد إصلاح
schema). **مرشَّح قوي لجلسة واحدة تراجع الاتنين مع بعض** (تتبع كل
الانحرافات + إعادة توليد `api-types.ts` شاملة واحدة، بدل جلستين منفصلتين
لنفس الأداة).

**الحالة:** 🔴 لسه مفتوح (لم يتغيّر) — البعد الجديد (transport) موثَّق هنا
فقط للتجميع، صفر إصلاح. `.claude/reports/category-b-decision-needed-triage-session-log.md`.

---

## [2026-09-02] بند Backlog جديد — `social-createpostmodal-missing-component-decision`

**الوصف:** اكتُشف أصلًا في جلسة `frontend-category-b-classification-all-domains`
(2026-09-01، `category-b/group1-social-transport.md` بند #1) ولم يُذكر
ضمن عدّ "11 مكوّن UI فوق API جاهز" الموثَّق في إغلاق مرحلة 1 أعلاه (5
invitations + 1 tourism-sports + 3 agritech محظورة + agritech stats =
10، مش 11 فعليًا — `CreatePostModal` هو الحالة الحادية عشرة المفقودة من
العدّ). مكوّن `components/social/CreatePostModal.tsx` **غير موجود
إطلاقًا** في `app/(dashboard)/social/page.tsx`، رغم أن البيانات اللي
سيستدعيها (`SocialService.createPost` + `POST /social/posts`) **جاهزة
بالكامل وموصولة** (موجودة أصلًا قبل أي جلسة من هذه السلسلة).

**الأثر:** فجوة UI بحتة، صفر عمل باك إند مطلوب — نفس فئة الـ5 مكوّنات
invitations + مكوّن tourism-sports `TransferCard` (رغم أن `TransferCard`
يحتاج endpoint إضافي مفقود، بعكس `CreatePostModal` الجاهز بياناته 100%).

**القرار المطلوب:** هل يُضاف `CreatePostModal` كسادس مكوّن ضمن "البند 3"
القادم (يرفع العدد لـ6 بدل 5 invitations + 1 tourism-sports)، أم يُترك
لجلسة لاحقة منفصلة؟

**الحالة:** 🟡 مفتوح — قرار نطاق بسيط، صفر عمل باك إند، جاهز للتنفيذ فورًا
بمجرد القرار. `.claude/reports/frontend-category-b-phase2-session-log.md`
قسم social.

---

## [2026-09-02] جلسة `frontend-category-b-phase2-remaining-domains` — إغلاق

**السياق:** استكمال مباشر لجلسة `frontend-category-b-phase2-remaining-domains`
السابقة (توقَّفت قبل أي تعديل كود بسبب اكتشاف جلسات Claude Code أخرى
نشطة على نفس الملفات — أُغلقت الجلسات القديمة من المستخدم، فأُكمِلت
الجلسة). النطاق: الثمانية دومينات المتبقية من "البند 2" (command,
manufacturing, tourism-sports, invitations [aliases فقط], transport,
insurance, tenders-auctions, social) — كلها **أُنجزت بالكامل ومتحقَّق
منها حيًا**، بنمط `XxxService.method()` مباشر داخل الهوك (بدل نمط alias
في service.ts المستخدَم في مرحلة 1)، هذا هو النمط المعتمَد من الآن
فصاعدًا.

**تصحيح منهجي مهم [تعليق مستخدم مباشر]:** التحقق الأول لعدة نتائج
pytest اعتمد على تشغيل خلفي (`run_in_background`) وقراءة *ملخَّص*
الإشعار (`exit code 0`) بدل قراءة المخرجات الفعلية — وده كشف لاحقًا إن
بعض هذه التشغيلات كانت بتمر عبر `| tail -N` اللي بيُخفي exit code
pytest الحقيقي (exit code المُبلَّغ كان بتاع `tail` مش `pytest`). عند
إعادة التشغيل بالتقاط exit code صريح (`echo $?` مباشرة بعد الأمر، بدون
pipe)، ظهر **فشلان حقيقيان** كانا مخفيين:
1. `test_transport_getter_endpoints_wiring.py::test_list_bookings_filters_by_trip`
   — `PermissionDeniedError` لأن `list_bookings` (المُضافة حديثًا) كانت
   بتنادي `_check_saas_limits` (تقليدًا لـ`get_my_bookings` المجاورة)،
   لكن tenant الاختبار ماعندوش اشتراك SaaS فعّال لميزة `transport` —
   اتصلح بإزالة الفحص (مطابقةً لباقي الإضافات الجديدة في نفس الجلسة
   اللي مافيهاش الفحص ده أصلًا).
2. `test_command_brands_metrics_wiring.py::test_list_brands_returns_real_record`
   — `NotNullViolationError` على عمود `created_by` (باج في fixture
   الاختبار نفسه، مش في الكود المُنتَج) — اتصلح بإضافة مستخدم `created_by`
   فعلي.
بعد الإصلاحين، **كل الـ6 ملفات اختبار (23 اختبارًا إجماليًا) أُعيد
تشغيلها معًا بالتقاط exit code صريح خارج أي pipe: `PYTEST_EXIT_CODE=0`،
كل الاختبارات PASSED.**

**التفاصيل الكاملة لكل دومين (الإضافات، الملفات، أرقام الاختبارات،
قوائم "تحتاج قرار"):** `.claude/reports/frontend-category-b-phase2-session-log.md`.

**3 بنود Backlog جديدة اتسجَّلت من اكتشافات جانبية لهذه الجلسة** (أعلاه
مباشرة): `insurance-update-claim-permission-asymmetry`،
`api-types-schema-name-collision-auction-tender-create`،
`social-createpostmodal-missing-component-decision`.

**الحالة:** ✅ الثمانية دومينات مكتملة ومتحقَّق منها حيًا (23 اختبار
PASSED عبر 6 ملفات، exit code صريح مؤكَّد). **البند 3 (مكوّنات UI) لم
يبدأ بعد** — ينتظر توجيه المستخدم، بما فيه قرار `CreatePostModal` أعلاه.

---

## [2026-09-02] بند Backlog جديد — `tourism-sports-transfer-repository-method-missing`

**الوصف:** اكتُشف أثناء فحص جاهزية مكوّنات البند 3 (`TransferCard`،
`.claude/reports/frontend-category-b-item3-components-readiness.md`):
`TourismSportsRepository` **لا تملك `get_transfer`/`list_transfers`
إطلاقًا** — لا كـmethod، ولا حتى تعريف داخلي. المفاجئ: `service.py:
place_transfer_bid` (الكود الأصلي، لم يُلمَس في أي جلسة من هذه السلسلة)
بينادي `self.repo.get_transfer(transfer_id)` في مسار التحقق من
idempotency-cache — **استدعاء لدالة غير موجودة في `repository.py`
إطلاقًا**، يعني أي مسار كود بيوصل لهذا السطر (تكرار طلب بنفس
`idempotency_key`) هيرمي `AttributeError` فورًا.

**الأثر:** (أ) مكوّن UI `TransferCard` مستحيل بناؤه بمعنى حقيقي — صفر
`list` endpoint لعرض قائمة عمليات الانتقال إطلاقًا. (ب) **أعمق من مجرد
مكوّن مفقود:** حتى لو حد حاول يبني endpoint جديد بمعزل عن هذا الاكتشاف،
مسار الـidempotency الموجود بالفعل في `place_transfer_bid` معطوب
بالفعل وهيفشل بـ`AttributeError` صامت (مبتلَع؟ يحتاج فحص) عند إعادة
محاولة بنفس المفتاح — نفس فئة أخطاء `get_by_id`/`get_user` التاريخية
(Backlog #1/#8 أعلاه)، لكن هنا الدالة **غير موجودة إطلاقًا من الأساس**
مش بس ناقصة معامل.

**الحل المتوقَّع:** جلسة/قرار منفصل: (أ) إضافة `get_transfer(transfer_id,
tenant_id)` + `list_transfers(tenant_id, ...)` لـ`repository.py`
(migration؟ الجدول `PlayerTransfer` موجود بالفعل، غالبًا صفر migration
مطلوبة، مجرد استعلامات جديدة)، (ب) تعريض الاثنين عبر `service.py`/
`router.py`، (ج) بعدها فقط يصبح `TransferCard` قابلًا للبناء.

**✅ [مُغلَق، 2026-09-04، جلسة `category-b-decision-needed-triage`]:** قرار
مستخدم صريح لتنفيذ فوري (باج حي، مش قرار منتجي). أُضيفت `get_transfer(transfer_id,
tenant_id)`/`list_transfers(tenant_id, status=None)` لـ`repository.py` +
أغلفة `service.py` + `GET /tourism-sports/sports/transfers` و
`GET /tourism-sports/sports/transfers/{transfer_id}` في `router.py`.
استدعاء `place_transfer_bid` (مسار idempotency-cache) اتصلح ليمرر
`tenant_id` بعد ما الدالة بقت موجودة فعليًا. تحقق حي: `tests/test_tourism_sports_decision_triage_wiring.py`
(5 اختبارات إجمالية بما فيها هذا البند + 4 endpoints تانية مرتبطة —
راجع البند التالي) — PASSED 5/5، exit code صريح `PYTEST_EXIT_CODE=0`.
`TransferCard` بقى قابلًا للبناء الآن (endpoint list جاهز).

**الحالة:** ✅ مغلق. `.claude/reports/frontend-category-b-item3-components-readiness.md`،
`.claude/reports/category-b-decision-needed-triage-session-log.md`.

**✅ اتحل [تأكيد 2026-09-16]** — تأكيد إضافي أثناء مراجعة backlog دورية: `get_transfer`/`list_transfers` لسه موجودة وموصولة، صفر تراجع. `.claude/reports/backlog-review-2026-09-16-session-log.md`.

---

## [2026-09-03] بند Backlog جديد — `frontend-types-null-vs-undefined-mismatch-pattern`

**الوصف:** اكتُشف أثناء بناء 6 مكوّنات UI (`CampaignCard`, `InvitationCard`,
`InvitationStatusBadge`, `TicketCard`, `TicketStatusBadge`, `CreatePostModal`
— راجع `.claude/reports/frontend-category-b-item3-components-readiness.md`):
ملفات الأنواع اليدوية (مش المولَّدة) `eppne-web/types/invitations.ts` و
`types/social.ts` بتُعرِّف كل حقل اختياري بصيغة `field?: X` (يعني
`X | undefined`)، بينما الـschemas الفعلية في الباك إند (Pydantic،
`Optional[X] = None`) بترجع `X | null` في الـJSON — تصادم نوع منهجي
عبر **كل** حقل اختياري تقريبًا في الملفين، مش محدود بمكوّن واحد.

**الدليل:** نفس فئة الخطأ بالضبط موجودة حاليًا وبشكل مستقل على
`Lead`/`LeadCard` (مكوّن قديم موجود من قبل أي جلسة من هذه السلسلة —
`app/(dashboard)/invitations/leads/page.tsx` عنده هذا الخطأ نشطًا الآن،
لم يُلمَس). يعني هذا التصادم **موجود مسبقًا وعابر للمشروع، مش مقتصر على
عمل هذه الجلسة** — جلستنا فقط أصلحت الحقول المحدَّدة اللي مكوّناتها
الستة الجديدة بتستهلكها فعليًا (`SovereignInvitation`, `MarketingCampaign`,
`SupportTicket`, `TicketComment` في `types/invitations.ts`؛ `Post` في
`types/social.ts`) — قرار نطاق صريح، مش إصلاح شامل.

**الأثر:** أي مكوّن جديد يُبنى مستقبلًا فوق هذين الملفين هيصطدم بنفس
الفئة من أخطاء `tsc` (missing property / incompatible types) بمجرد
أول استخدام حقيقي للبيانات الحية (بدل `any` المُقنَّع من استيراد مكسور
سابقًا) — تمامًا زي ما حصل هنا مع `CampaignCard`/`InvitationCard`/`TicketCard`.

**الحل المتوقَّع (قرار منفصل إن قررنا توحيده):** إما (أ) تدقيق شامل
لكل الملفين وتحويل كل `field?: X` إلى `field?: X | null` حيث ينطبق،
حقل بحقل مقابل الـschema الفعلية، أو (ب) إعادة توليد أنواع Pydantic
تلقائيًا بدل الاعتماد على ملفات يدوية موازية أصلًا (يحل المشكلة جذريًا
لكل الدومين، مش بس invitations/social).

**الحالة:** 🟡 مفتوح، موثَّق فقط — نمط معروف الآن، غير عاجل (لا يمنع
أي عمل حالي، بس هيتكرر كتكلفة صغيرة مع كل مكوّن جديد فوق نفس الملفين).
`.claude/reports/frontend-category-b-item3-components-readiness.md`.

---

## [2026-09-04] جلسة `agritech-full-domain-build` — إغلاق (البند المفتوح من [2026-09-01] أعلاه)

**الوصف:** تنفيذ القرار الموثَّق سابقًا (بند Backlog `agritech-full-domain-build`،
2026-09-01 أعلاه): بناء `router.py` جديد بالكامل من الصفر لدومين `agritech`
وتسجيله في `main.py`. تصميم الـ19 endpoint (farms, zones, crop cycles,
harvest, bio assets, traceability+QR, certificates, soil sensors, weather
alerts) عُرض للموافقة الصريحة قبل أي تنفيذ (4 قرارات: prefix بسيط `/agritech`
مطابق لكل الدومينات التانية، نطاق 19 endpoint فقط بدون توسيع، schema جديدة
لنتائج register_harvest/register_bio_yield، صلاحية superuser لـissue_certificate
وcreate_weather_alert) — راجع `.claude/reports/agritech-full-domain-build-session-log.md`.

**اكتشافان حرجان أثناء التحقق الحي (pytest ضد DB حقيقية) — لم يكونا معروفين
وقت التصميم، لأن الكود لم يُستورَد فعليًا من قبل أبدًا:**

1. **`repository.py` كان بيكسر الاستيراد بالكامل فور محاولة تحميله:** كل
   دوال `list_*`/`get_*_stages`/`get_entity_certificates`/`get_recent_soil_readings`
   بترجّع `PaginatedResponse[SmartFarm]` (وأخواتها) — بارامترة الـgeneric
   كانت **كلاس ORM خام** (SQLAlchemy model)، مش Pydantic schema. كل دومين
   تاني بيستخدم نفس `PaginatedResponse` (academy, affiliate, ai_agents,
   commerce, ...) بيمرّر schema فعلية (`PaginatedResponse[CourseResponse]`
   مثلًا) — agritech وحدها كانت الاستثناء. هذا كان بيفشل بـ
   `PydanticSchemaGenerationError` فور `import` — وهو **السبب الحقيقي** إن
   الملف "orphaned" مش بس غياب router، كان حرفيًا مستحيل الاستيراد من
   الأساس. **الإصلاح:** استبدال الـ6 استخدامات بـschemas الفعلية
   (`SmartFarmResponse`, `FarmZoneResponse`, `CropCycleResponse`,
   `SupplyChainStageResponse`, `AgriculturalCertificateResponse`,
   `SoilSensorReadingResponse`).
2. **`record_soil_data` في `service.py` كانت بتكسر عند أول استدعاء حقيقي:**
   `audit_log(details={..., "moisture": data.get("moisture_percent")})` —
   بتمرر `Decimal` خام لدالة `audit_log()` اللي بتعمل `json.dumps()` **بدون**
   `default=str` → `TypeError: Object of type Decimal is not JSON serializable`.
   بما إن `SoilSensorReadingCreate.moisture_percent` من نوع `Decimal` في الـschema،
   وPydantic v2 `model_dump()` بيحافظ على نوع `Decimal` كما هو — هذا كان
   هيحصل مع **أي طلب حقيقي فيه moisture_percent** عبر الـrouter، مش حالة
   اختبار حافة. **الإصلاح:** `float(data["moisture_percent"])` قبل التمرير
   لـ`audit_log` (نفس النمط المستخدم فعلًا في باقي دوال هذا الملف، مثل
   `HARVEST_REGISTERED`). باقي الـ10 استدعاءات audit_log في نفس الملف
   اتفحصت ولا فيها نفس الباج.

**تعديلات إضافية منفَّذة (بموافقة صريحة ضمن القرارات الأربعة):**
- `services/agritech.ts`: إصلاح 16 سطر URL كانت مكتوبة بمسار مضاعف
  (`/agritech/agritech/...`) — تم توحيدها لمسار بسيط (`/agritech/...`)
  اتساقًا مع كل الدومينات التانية في المشروع (كلها بلا استثناء prefix واحد).
- `schemas.py`: إضافة `HarvestRegistrationResult` و`BioYieldRegistrationResult`
  (تحافظان على حقل `ai_logistics_actions` المفيد من الـservice).
- `service.py`: حقن أسماء بديلة (`id`, `cycle_id`, `harvest_date`,
  `shipment_tracking_number` لـregister_harvest؛ `id`, `cohort_id`,
  `quantity_unit`, `collection_date` لـregister_bio_yield) في الـdicts
  المُرجَعة، عشان تطابق التوقع الأصلي في `services/agritech.ts` بدون
  الحاجة لتعديل فرونت إند إضافي.
- `requirements.txt`: إضافة `qrcode[pil]>=8.0` — كانت مستخدمة فعليًا في
  `generate_traceability_qr` (مع `try/except ImportError` صريح) لكن غير
  مُعلَنة كـdependency إطلاقًا؛ مثبَّتة الآن في venv ومُختبَرة حيًا.

**التحقق الحي المنفَّذ:** اختبار pytest واحد شامل (`tests/test_agritech_router_wiring.py`)
يمشي الدومين بالكامل ضد DB حقيقية (PostgreSQL، صفر mock): إنشاء مزرعة →
منطقة → دورة زراعية → حصاد → مجموعة حيوانية → إنتاج حيواني → مرحلة تتبع →
QR → شهادة → قراءة تربة → تنبيه طقس، + تحقق عزل tenant_id على عيّنتين
(farms عبر عمود مباشر، soil-readings عبر join مع FarmZone) — **PASSED**.
تأكيد إضافي: `app.main` يستورد بنجاح (581 route إجمالي)، و19 مسار
`/api/agritech/*` مسجَّلة بالضبط بلا تكرار وبلا تعارض مع أي دومين تاني.
تشغيل كامل test suite الباك إند (`pytest -q`) قيد التنفيذ للتأكد من صفر
regression خارج agritech — نتيجته تُوثَّق في تعليق تالٍ فور اكتماله.

**الحالة:** ✅ مغلق. `router.py` (19 endpoint) موجود ومسجَّل في `main.py`،
كل الدوال الموجودة فعليًا في `service.py` مكشوفة الآن كـHTTP endpoints،
الفرونت إند (`services/agritech.ts`) يطابق المسارات الحقيقية بالحرف.
الفجوات المتبقية (named exports مفقودة، `useStats.ts`، update/delete farm،
list harvests/bio cohorts) موثَّقة في البند التالي كـPhase 2 منفصلة —
قرار نطاق صريح من المستخدم، مش نسيان.
`.claude/reports/agritech-full-domain-build-session-log.md`.

---

## [2026-09-04] بند Backlog جديد — `agritech-phase2-frontend-gaps`

**الوصف:** اكتُشف أثناء جلسة `agritech-full-domain-build` (أعلاه) عند مقارنة
الـrouter الجديد (19 endpoint، مطابقة 1:1 لدوال service.py الموجودة) مع
الفرونت إند الموجود مسبقًا (`hooks/agritech/*.ts`, `services/agritech.ts`,
`app/(dashboard)/agritech/**`). قرار نطاق صريح من المستخدم: هذه الجلسة
بنت الـ19 endpoint فقط، وأجّلت الفجوات التالية لجلسة Phase 2 منفصلة
(نفس نمط `phase 2` في commit `1bb70b2` لدومينات تانية):

1. **`services/agritech.ts` يُصدِّر فقط `AgritechService` (object واحد)**،
   لكن الـhooks بتستورد named exports غير موجودة إطلاقًا: `getFarms`,
   `getFarm`, `updateFarm`, `deleteFarm` (`useFarms.ts`)، `getZones`,
   `createZone` (`useZones.ts`)، `getCropCycles` (`useCropCycles.ts`)،
   `getHarvests` (`useHarvests.ts`)، `getBioCohorts`, `createBioCohort`
   (`useBioAssets.ts`)، `getWeatherAlerts` (`useSensors.ts`) — استيراد
   مكسور بالكامل حاليًا (compile error)، **مستقل عن وجود الـbackend router**.
2. **`hooks/agritech/useStats.ts` غير موجود إطلاقًا** — `app/(dashboard)/agritech/page.tsx`
   بيستورد `useAgritechStats` منه، فالصفحة الرئيسية للدومين مكسورة حاليًا.
3. **فجوات في `service.py` نفسه** (مطلوبة من الـhooks بس مش موجودة):
   `update_farm`, `delete_farm` (الموديل عنده `is_deleted`/`deleted_at`
   بس لا يوجد service/repo method)، `list_harvests(cycle_id)` (فيه
   `register_harvest` بس ولا يوجد أي get/list للحصاد)، `list_bio_cohorts(zone_id)`
   (فيه `add_bio_cohort` بس ولا يوجد أي get/list)، وأي stats aggregation
   لدعم `useAgritechStats`.

**الحالة:** 🔴 مفتوح، موثَّق فقط، صفر تنفيذ — يحتاج جلسة منفصلة (تصميم
+ موافقة زي أي دومين، خصوصًا update/delete farm وlist endpoints جديدة).
`.claude/reports/agritech-full-domain-build-session-log.md`.

---

## [2026-09-04] بند Backlog جديد — `update_bio_cohort_count-tenant-id-bug`

**الوصف:** اكتُشف أثناء مراجعة أمنية لـ`agritech/repository.py` ضمن جلسة
`agritech-full-domain-build`. الدالة `update_bio_cohort_count(self, cohort_id, new_count)`
(سطر 146) بتستدعي `self.get_bio_cohort(cohort_id)` بمعامل واحد فقط، بينما
توقيع `get_bio_cohort` الفعلي يتطلب `(cohort_id, tenant_id)` إجباريًا —
`TypeError` مضمون لو اتنادت. **dead code حاليًا** — ولا دالة في `service.py`
بتستخدمها، وrouter الجلسة دي ماضافش أي endpoint بيستدعيها (تحديث عدد
المجموعة الحيوانية مش من ضمن الـ19 endpoint المتفَق عليها).

**✅ [مُغلَق، 2026-09-04، جلسة `category-b-decision-needed-triage`]:** كود
ميت (صفر استدعاءات في الكودبيز بالكامل، تأكَّد بـgrep) → إصلاح ميكانيكي
فوري صفر مخاطرة: أُضيف معامل `tenant_id: int` لتوقيع
`update_bio_cohort_count`، واستُخدم في فلترة الـ`UPDATE` نفسه (`and_(...,
tenant_id==...)`، نفس نمط باقي الدالة `get_bio_cohort`) وفي استدعاء
`self.get_bio_cohort(cohort_id, tenant_id)` في نهايتها. تحقَّق حيًا:
`python -c "from app.domains.agritech import repository"` نجح بلا أخطاء.
لا يوجد caller حاليًا يستدعي الدالة، فلا أثر على أي سلوك قائم.

**الحالة:** ✅ مغلق. `.claude/reports/agritech-full-domain-build-session-log.md`،
`.claude/reports/category-b-decision-needed-triage-session-log.md`.

**✅ اتحل [تأكيد 2026-09-16]** — تأكيد حي إضافي: `update_bio_cohort_count(cohort_id, tenant_id, new_count)` لسه بتوقيعها الصحيح (`agritech/repository.py:146`)، صفر تراجع. `.claude/reports/backlog-review-2026-09-16-session-log.md`.

---

## [2026-09-04] بند Backlog جديد — `agritech-traceability-certificate-idor-defense-gap`

**الوصف:** اكتُشف أثناء الفحص الأمني لـtenant_id scoping في `agritech/service.py`
ضمن جلسة `agritech-full-domain-build`. الدوال `add_traceability_stage`،
`issue_certificate`، و`register_harvest`/`register_bio_yield` (لحقول
`destination_facility_id`/`destination_farm_id`) بتقبل IDs خام
(`traceable_id`, `certified_entity_id`, ...) **من غير التحقق إن الكيان
المُشار إليه فعلاً ملك لنفس الـtenant الحالي**. القراءة نفسها بتفضل معزولة
(كل query في repository.py بيفلتر بـtenant_id)، فمفيش تسريب بيانات مباشر —
لكن معناه ممكن تُصدر شهادة/مرحلة تتبع بمعرّف كيان مش موجود أصلاً عند
الـtenant الحالي (garbage reference)، بدون أي رفض من السيرفر.

**القرار المتَّخذ في هذه الجلسة:** تُرك الوضع كما هو (مطابقة لباقي
الدومينات المشابهة اللي اتبنت بنفس النمط)، وتم توثيقه كـfollow-up منفصل
بدل حجب الـendpoints أو إضافة تحقق إضافي بدون موافقة صريحة.

**الحالة:** 🟡 مفتوح، موثَّق فقط، غير عاجل (defense-in-depth، مش ثغرة عزل
مباشرة) — يحتاج قرار منتجي (هل نضيف تحقق ownership قبل إصدار شهادة/مرحلة
تتبع؟) في جلسة أمنية مخصَّصة لو حبينا نسدها.
`.claude/reports/agritech-full-domain-build-session-log.md`.

---

## [2026-09-04] جلسة `category-b-decision-needed-triage` — إغلاق

**السياق:** جرد وتصنيف كل بنود "تحتاج قرار" المتراكمة عبر phase1/phase2/
agritech لثلاث فئات (فوري/قرار بسيط/قرار كبير)، ثم تنفيذ ما وافق عليه
المستخدم صراحة فقط. تفاصيل الجدول الكامل والتصنيف:
`.claude/reports/category-b-decision-needed-triage-session-log.md`.

**نُفِّذ:**
1. `update_bio_cohort_count-tenant-id-bug` (agritech) — فوري، صفر انتظار قرار (أعلاه).
2. `tourism-sports-transfer-repository-method-missing` (باج حي في `place_transfer_bid`) — أعلاه.
3. **4 endpoints جديدة إضافية في tourism-sports** (قرار مستخدم صريح، نفس commit):
   `GET /destinations/{dest_id}` (`getDestination`)، `GET /programs`
   (`getPrograms`)، `GET /sports/organizations` (`getSportsOrganizations`)،
   `GET /sports/players` (`getPlayers`) — كلها mechanical فوق `repository.py`/
   `service.py` جديدة (فلترة `tenant_id` مزدوجة، نفس نمط `get_sports_org`
   الموجود). تحقق حي ضمن نفس ملف الاختبار `tests/test_tourism_sports_decision_triage_wiring.py`
   (5 اختبارات، PASSED 5/5، `PYTEST_EXIT_CODE=0` صريح).
4. **`transport-formdata-vs-openapi-schema-mismatch`** — تحقُّق فقط (بلا
   تنفيذ): `GeoAddress`/`Waypoint` sub-models و`sender_id` المحذوف **مُطبَّقون
   بالفعل** من جلسة `transport-domain-full-build` (2026-09-01) — البند كان
   stale وقت طرحه. اكتُشف جانبيًا: `eppne-web/src/lib/api-types.ts` المولَّد
   لسه قديم (`waypoints: Record<string, never>[]`) رغم إصلاح الباك إند —
   بلا أثر عملي حاليًا لأن `types/transport.ts` اليدوي المستخدَم فعليًا سليم،
   لكن يستاهل تسجيل كملاحظة منفصلة (نفس فئة `api-types-schema-name-collision-auction-tender-create`).
5. `insurance-update-claim-permission-asymmetry` — قرار مستخدم: **البقاء
   superuser-only، صفر تعديل** (أُغلق أعلاه في مكانه).

**لم يُنفَّذ (قرار مستخدم صريح: يبقى backlog):** كل بنود "قرار بسيط"
المتبقية في command، manufacturing، insurance (stats/`deletePolicy`)،
tenders-auctions، وsocial — راجع الجدول الكامل في تقرير الجلسة. كذلك
كل بنود "قرار كبير" (9 بنود، منها `useDrivers`/ميزة المركبات المعدومة في
transport، دومين Pages بـsocial، فجوة realestate hooks، تصادم schema
tenders-auctions/دومين آخر، `agritech-phase2-frontend-gaps`) — صفر سؤال
عنها، موثَّقة كمرشَّحة لجلسات مستقلة لاحقة.

**الحالة:** ✅ الأربعة بنود المطلوبة اتقفلت (فوري واحد + تنفيذان حيّان
+ تأكيد بلا حاجة لتنفيذ). commit واحد شامل يجمع agritech + tourism-sports
+ التوثيق. `.claude/reports/category-b-decision-needed-triage-session-log.md`.

---

## [2026-09-04] بند Backlog مؤجَّل عمدًا — `api-types-full-regeneration-deferred-until-backend-queue-clear`

**السياق:** جلسة `api-types-schema-collision-investigation` — تحقيق فقط
(صفر تنفيذ). راجع
`.claude/reports/api-types-schema-collision-investigation-session-log.md`
للتفاصيل الكاملة.

**النتيجة الأساسية:** افتراض "تصادم اسم class عبر دومينين" (اللي كان
مسجَّل في بند `api-types-schema-name-collision-auction-tender-create`
أعلاه) **غير صحيح** — أُثبت بأرشيف git إنه لا يوجد أي تصادم اسم حقيقي في
أي نقطة زمنية. السبب الجذري الموحَّد لكل الانحرافات المكتشَفة (tenders/
auctions **و**transport) هو: `eppne-backend/openapi.json` ملف **ثابت**
مُلتزَم في git، يتولَّد منه `api-types.ts` عبر `openapi-typescript`
يدويًا بدون أي سكريبت/CI تلقائي، ولم يُعَد توليده منذ commit `0d9c55b`
(2026-07-21) — **45 يوم** حتى تاريخ هذه الجلسة، رغم ~40 commit لمست
`schemas.py`/`router.py` عبر معظم دومينات المشروع خلال هذه الفترة. يعني
الانحراف الحقيقي أوسع من الحالتين المكتشَفتين لحد الآن.

**قرار المستخدم الصريح [2026-09-04]:** تأجيل الـregeneration الكامل
(`openapi.json` من سيرفر حي + `api-types.ts` منه + `tsc --noEmit`) إلى
**جلسة أخيرة مخصَّصة بعد الانتهاء من كل تعديلات الباك إند المخطَّط لها
حاليًا** (transport vehicles/drivers، Referral+Affiliate، وأي بند آخر في
الطابور بيلمس `schemas.py`). **السبب:** تجنب تكرار عملية الـregeneration
أكتر من مرة — كل تعديل schema جديد في الطابور هيخلي أي regeneration
مبكرة قديمة تاني بمجرد ما يتنفَّذ، فالأفضل انتظار استقرار كل تعديلات
schemas.py المخطَّطة أولاً ثم regeneration واحدة شاملة نهائية.

**الحالة:** 🟡 مؤجَّل عمدًا (قرار مستخدم صريح، مش نسيان) — **لا تنفَّذ
regeneration قبل التأكد إن طابور تعديلات الباك إند المخطَّطة (transport
vehicles/drivers، Referral+Affiliate، وغيرها) خلص فعليًا.** عند فتح
الجلسة الأخيرة المخصَّصة لهذا البند، ابدأ من
`.claude/reports/api-types-schema-collision-investigation-session-log.md`
مباشرة — التحقيق والدليل جاهزين بالكامل، الخطوة الوحيدة الناقصة هي
التنفيذ.

---

## [2026-09-04] `iot-translation-service-method-mismatches` — 3 أعطال حقيقية
اتصلحت بعد كشفها خلف باج rename سابق (commit `cf98a74`)

**السياق:** جلسة `frontend-mechanical-fix-all-domains-pass1` (2026-08-31)
كانت عملت rename ميكانيكي (`iotService`→`IoTService`،
`translationService`→`TranslationService`) بدون تدقيق كل استدعاء. بعده
ظهرت 3 أعطال حقيقية منفصلة تمامًا كانت مخفية خلف باج الاستيراد القديم،
عبر 7 ملفات فرونت إند + الباك إند:

1. **rename بسيط (method لا يوجد إطلاقًا):** `AssetsManager.tsx` و
   `IoTDashboardStats.tsx` بينادوا `IoTService.getAssets({limit:1000})`
   غير موجود أصلاً — الصح `listMyAssets({limit})`. اكتُشف كمان إن
   `limit:1000` كانت أصلاً خاطئة بغض النظر عن اسم الميثود (الباك إند
   `le=200`) — اتصلحت لـ`200`.
2. **service file بيتجاهل رد الـAPI (مش مجرد type mismatch):**
   `CarbonCreditPanel.tsx` بينادي `settleCarbon()` بلا الآرجيومنت
   المطلوب (`CarbonSettlementRequest`)، و`iot.service.ts`'s `settleCarbon`
   كانت موقّعة `Promise<void>` رغم إن الباك إند فعليًا بيرجّع
   `total_credits_settled`/`monetary_value_added_mrusdt` — الكومبوننت
   كانت بتقرأ حقول من نتيجة متجاهَلة عمدًا. اتصلح الاستدعاء
   (`settleCarbon({})`) + الـservice بقت بترجع النتيجة الفعلية + أُضيفت
   `CarbonSettlementResponse` schema صريحة في الباك إند
   (`POST /iot/carbon/settle` كانت بلا `response_model` إطلاقًا).
3. **تصادم توقيع مع مكتبة react-query v5 نفسها (اكتشاف غير متوقَّع):**
   `BatchTranslator.tsx`/`ChatTranslator.tsx`/`TextTranslator.tsx` كانوا
   بيمرروا `TranslationService.translate`/... مباشرة كـ`mutationFn`.
   الباراميتر الثاني الاختياري `headers?` في الـservice methods اصطدم
   موضعيًا مع الآرجيومنت الجديد `context: MutationFunctionContext` اللي
   react-query v5 بيبعته لـ`mutationFn` — مش نفس نمط idempotencyKey
   الخام المفترَض أصلاً. الإصلاح: لف كل استدعاء بـlambda محلي، صفر لمس
   لـ`translation.service.ts` (الـheaders param مقصودة لدعم X-Tenant-ID
   مستقبلي، مؤكَّد بلا أي استخدام حالي عبر grep).

**اكتشاف إضافي أثناء التحقق الحي:** إصلاح #1 كشف باج تاني كان مخفي خلف
`any[]` — `types/iot.ts`'s `SmartAsset.location_gps`/`iot_wallet_address`
كانوا أضيق (required/`{lat,lng}`) من الشكل الفعلي المولَّد
(optional/`Record<string,number>`). اتصلح بتوسيع النوعين فقط، صفر تغيير
سلوك وقت التشغيل.

**التحقق الحي:** `tsc --noEmit` نظيف على كل الملفات المتأثرة +
`pytest tests/test_iot_carbon_settlement_response_schema.py` (اختبار
جديد، DB حقيقية صفر mock) — 2 passed، يغطي حالتَي SUCCESS و NO_CREDITS
ضد الـschema الجديدة.

**الحالة:** ✅ مكتمل ومُتحقَّق منه حيًا. تقرير الجلسة الكامل:
`.claude/reports/iot-translation-service-mismatches-session-log.md`.

---

## [2026-09-05] `transport-vehicles-drivers-feature-build` — بناء ميزة المركبات/الأساطيل/السائقين من الصفر (فرونت إند معدوم رغم باك إند جزئي)

نفَّذت الترتيب المرحلي الكامل (1→9) المعتمَد من المستخدم: باك إند
Vehicle (list/update/delete hard-delete مع حماية FK) + Fleet
(list/update/delete soft-delete) + Driver (`GET /transport/drivers`،
زيرو-flag بدون كيان منفصل، قرار مستخدم صريح) — 7/7 pytest حي ضد DB
حقيقية، ثم فرونت إند كامل (`services/transport.ts`, `api-types.ts`,
`useVehicles.ts` مُعاد كتابته بالكامل، `useFleets.ts` مُصلَح،
`useDrivers.ts` جديد، زرار تعديل `vehicles/page.tsx` مُفعَّل) — `tsc`
740→733 خطأ (تحسّن)، صفر تراجع في أي ملف مُعدَّل. مرحلة 9 (اختبار متصفح
حي) اصطدمت بقيدين بيئيين حقيقيين موثَّقين كبنود Backlog منفصلة فوق
(`transport-saas-catalog-entry-missing-in-dev`,
`transport-vehicles-drivers-phase9-browser-verification-gap`) — استُبدلت
بتحقق منطقي مكافئ بموافقة صريحة. اكتشاف جانبي إضافي وُثِّق
(`transport-trips-page-driver-display-and-cancel-trip-missing`). تفاصيل
كاملة (كل قرار تصميم، كل اكتشاف حي، الجداول الكاملة): **الحالة:** ✅
التنفيذ المتفَق عليه مكتمل بالكامل ومُتحقَّق منه (حيًا للباك إند، `tsc`+
تتبّع منطقي للفرونت إند) — فجوتان بيئيتان موثَّقتان صراحة، مش ادّعاء نجاح
لم يحصل. تقرير الجلسة الكامل:
`.claude/reports/transport-vehicles-drivers-session-log.md`.

---

## [2026-09-06] `referral-affiliate-unified-system-implementation` —
توحيد 3 أنظمة إحالة/عمولة منفصلة (A/B/C) على نظام واحد مربوط بنطاقات

**السياق:** جلستان سابقتان (`referral-affiliate-system-design`،
`referral-affiliate-unified-system-implementation` design phase) كشفتا
3 أنظمة إحالة/عمولة منفصلة تمامًا في المشروع: `affiliate` domain
(10 مستويات، Product-Scoped، ميت تشغيليًا)، `commerce` domain (10
مستويات Sponsor Chain، الحي فعليًا لكن بلا تمايز منتج)، والـ12 دومين
(`ActionCommission`، مستوى واحد، معطَّلة بسبب `User.referred_by` مفقود).
قرار المستخدم النهائي: التوحيد على نظام `affiliate` (الأذكى تصميميًا)،
حذف نظام `commerce` بالكامل، ربط الـ12 دومين بنفس الآلية، + مفهوم
`AffiliateScope` جديد (بدل ربط مباشر بـ`product_id`) يسمح بشجر/عمولات
منفصلة تمامًا لكل نطاق (منتج فردي/مجموعة/كل مبيعات الـtenant).

**التنفيذ (9 مراحل، بالترتيب 0→1→2→3→(4،7)→5→6→8، تحقق حي بعد كل
مرحلة):**
- **Phase 0 (migration 045):** `AffiliateScope`+`AffiliateScopeMember`
  جديدتان (Enum حقيقي `scope_type`، فهارس جزئية مزدوجة تمنع تكرار
  عضوية دومين كامل). `CommissionTier.target_product_id`→`target_scope_id`.
  `Commission` عُمِّمت لتقبل أي مصدر بيع (`order_id`/`order_item_id`/
  `product_id` صاروا nullable، + `source_type`/`source_id`/`scope_id`
  جدد). `ReferralTree.entity_id` صار FK حقيقي لـ`affiliate_scopes.id`.
  حذف `affiliate_action_commissions` (نظام C) و`affiliate_trees`/
  `commission_records`/`affiliate_configs` (نظام B) بالكامل. `TRUNCATE`
  صريح على 3 جداول (بيانات اختبارية بحتة، مؤكَّد). `users.referred_by_user_id`
  جديد. Seed صف `saas_service_catalog(code='affiliate')` — **اكتُشف
  ناقصًا من أول كتابة وأُضيف قبل التطبيق** (بدونه Phase 7 مستحيلة
  تشغيليًا). **باجان اكتُشفا وأُصلحا أثناء التطبيق الفعلي** (مش نظريًا):
  ENUM مزدوج الإنشاء (`DuplicateObjectError`)، وdowngrade كان هيمسح
  بيانات اختبار سابقة غير مرتبطة (`ForeignKeyViolationError` على
  اشتراك SaaS حي لـ`tenant_id=16`) — الحل: عدم عكس الـseed إطلاقًا
  (بنفس فلسفة عدم قابلية التراجع عن TRUNCATE). round-trip
  `downgrade -1`→`upgrade head` نجح بالكامل بعد الإصلاحين.
- **Phase 1-2 (Models/Repository):** إضافة الموديلات الجديدة، حذف
  `ActionCommission`. **إصلاح باج `MultipleResultsFound` الموثَّق سابقًا**
  في `get_referral_tree` — بقت تفلتر بـ`scope_id` صريح بدل `referred_id`
  وحده، فالقيد الفريد الموجود أصلاً يضمن الآن صفًا واحدًا فعليًا لا
  نظريًا فقط.
- **Phase 3 (Service، أكبر مرحلة):** `distribute_commissions`→
  `distribute_commissions_for_order` (تقسيم العمولة حسب نطاق كل منتج
  في سلة مختلطة) + `distribute_commissions_for_sale_event` جديدة (لأي
  بيع بلا Order تجاري) + `ensure_referral_link` عامة. تعديل ضيّق مسحوب
  من Phase 4 (ضرورة حتمية): `CommissionBase`/`CommissionTierBase`
  schemas عُدِّلت لتطابق الأعمدة الجديدة (كانت هتكسر `GET /affiliate/commissions`
  فورًا). `commerce/service.py`: حذف `register_affiliate`/`distribute_commissions`
  (B)، `checkout()` بقت تنادي المسار الموحَّد.
- **Phase 4/7:** Scope CRUD endpoints جديدة (`/affiliate/admin/scopes*`)
  + hook تلقائي في `SaaSControlService.create_subscription`: أول
  اشتراك فعّال على `service_code="affiliate"` لأي tenant ينشئ تلقائيًا
  نطاق `ENTITY_WIDE` افتراضي (idempotent).
- **Phase 5 (academy):** **اكتشاف جديد** — تسجيل الكورس بكود إحالة كان
  يسجّل الشجرة فقط، **صفر توزيع عمولة فعلي من أي وقت مضى**. أُصلح:
  توزيع فعلي الآن لو الدفع اكتمل بمبلغ حقيقي.
- **Phase 6 (12 دومين):** كل الـ12 (`zamakana`, `transport`, `insurance`,
  `tourism_sports`, `tenders_auctions`, `service_marketplace`,
  `employment`, `realestate`, `manufacturing`, `arbitration_syndicates`,
  `invitations`, `digital_twin`) — `user.referred_by`→`user.referred_by_user_id`
  + استبدال `register_commission`/`ActionCommission` (مستوى واحد) بنفس
  خط أنابيب `Commission` الموحَّد (10 مستويات فعلية).
- **Phase 8 (Celery):** إصلاح 3 أعطال توقيع مستقلة في `tasks/affiliate.py`
  (موثَّقة سابقًا في تقارير قديمة) + تسجيل `clean_expired_links` فعليًا
  في `beat_schedule` لأول مرة (كانت موجودة بلا أي جدولة من البداية) —
  ونمط "loop عبر كل الـtenants النشطين" جديد بالكامل بالمشروع (لا سابقة
  مماثلة).

**تحقق حي شامل (Phase 9 جزئي):** `python -c "import app.main"` ناجح
بعد كل مرحلة تراكميًا (كل الـ35+ دومين يستوردون بلا خطأ). اختبار حي
كامل end-to-end (بيانات throwaway تحت `tenant_id=16` الموجود بالفعل،
منظَّفة بالكامل بعده عبر CASCADE): إنشاء scope → tier → affiliate
profile → `ensure_referral_link` → `get_referral_tree` (بعد إصلاح
الباج) → `distribute_commissions_for_sale_event` → **صف `Commission`
حقيقي أُنشئ فعليًا** (`level=1, amount=10.00, scope_id=1`) — يثبت
المسار الكامل الجديد يعمل صح على DB حقيقية، مش مجرد `import` ناجح.

**الحالة:** ✅ التصميم + Phases 0-8 مكتملة ومُتحقَّق منها حيًا. **متبقٍ
صراحة (لم يُنفَّذ في هذه الجلسة):** ملف اختبار `pytest` رسمي دائم
(Phase 9 الكاملة بالمعنى الرسمي — التحقق الحي تم عبر سكريبت مؤقت غير
مُلتزَم)، وتنظيف بقايا صغيرة غير حرجة (`Store.is_affiliate_enabled`
تحديد نهائي لدوره، مراجعة أعمق لـ`@rate_limit` decorator غير الفعّال
الموثَّق في تقرير Phase 10 القديم — خارج نطاق هذه الجلسة). تقرير
الجلسة الكامل (تصميم + تنفيذ + كل قرار وكل اكتشاف حي):
`.claude/reports/referral-affiliate-unified-implementation-session-log.md`
و`.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md`.

---

## [2026-09-06] `saas-check-feature-access-missing-service-id-binding` —
بند Backlog أمني (توثيق فقط، صفر تنفيذ) — اكتُشف أثناء Phase 9 من
جلسة `referral-affiliate-unified-system-implementation`

**السياق:** أثناء محاولة اختبار Phase 7 hook (تفعيل affiliate كخدمة
SaaS) عبر `SaaSControlService.create_subscription` الحقيقية، اكتُشف
إن `POST /saas/subscriptions/{plan_id}` معطَّل بالكامل حاليًا لأي
tenant/خدمة (باج `get_plan_by_id` chicken-and-egg — تفاصيل كاملة في
`.claude/reports/saas-get-plan-by-id-security-tradeoff-note.md`)، وإن
إصلاحه بمعزل عن بند أمني موثَّق سابقًا سيعيد فتح ثغرة كامنة. **قرار
المستخدم [2026-09-06]: عدم لمس `get_plan_by_id` في هذه الجلسة، وتسجيل
هذا البند صراحة كـbacklog أمني منفصل قبل المتابعة.**

**(1) الثغرة الكامنة (موثَّقة أصلًا من `saas-feature-flags-drift-session-log.md`
§6، لم تُحَل من وقتها):** `SaaSControlService.check_feature_access`
تمنح الوصول لأي `feature` string لو وُجد داخل `plan.features` (JSON)
لأي اشتراك نشط للـtenant — **بلا أي تحقق إن هذا الاشتراك ينتمي فعلًا
لنفس service الدومين اللي بيطلب الفحص.** لا يوجد ربط رسمي
`feature → service_id` في الـschema الحالي. لو تفعّل مسار اشتراك حي
(`create_subscription`)، أي tenant admin يقدر (نظريًا) يشترك بخطة
رخيصة/غير متعلقة تحتوي بالصدفة (أو عمدًا) على نص feature يخص خدمة
تانية أغلى، ويكسبها مجانًا عبر أي دومين يستخدم `check_feature_access`.

**(2) `get_plan_by_id` (`saas/repository.py:55-75`) بيمنع الاستغلال
حاليًا — لكن بالصدفة، مش كحماية مقصودة:** الدالة تشترط وجود اشتراك
`ACTIVE`/`TRIAL` **سابق** لنفس `(plan_id, tenant_id)` عشان ترجّع أي
نتيجة أصلًا — يعني **مفيش tenant يقدر ينشئ أي اشتراك جديد عبر الـAPI
الحي من الأساس، لأي خطة كانت.** أي إصلاح لهذا الباج بمعزل عن (1) يفتح
الثغرة فورًا (موثَّق صراحة كتحذير داخل الكود نفسه، `saas/service.py:138-147`).

**(3) اكتشاف جديد اليوم — الكودبيز فيه آليتان مختلفتان، مش آلية واحدة
موحَّدة:** فحص جزئي (`zamakana` مقابل `insurance`) أظهر إن بعض
الدومينات تستخدم `SaaSSubscriptionService.can_access_service` (آمنة —
مفحوصة بـ`service_code` مباشر، بلا علاقة بالثغرة) بينما دومينات تانية
(`insurance` مؤكَّد) تستخدم `check_feature_access` (المعرَّضة فعليًا).
**docstring الدالة نفسها بيدّعي "تُستخدَم من 12 دومين" — رقم غير دقيق،
لم يُحصَ بدقة.** العدد الحقيقي للدومينات المعرَّضة فعليًا غير محصور —
يحتاج فحص كامل لكل الـ14-15 ملف اللي بيستخدموا
`check_feature_access`/`_check_saas_limits` (القائمة الأولية: `digital_twin`,
`invitations`, `arbitration_syndicates`, `manufacturing`, `realestate`,
`employment`, `service_marketplace`, `tenders_auctions`, `tourism_sports`,
`insurance`, `transport`, `zamakana`, `social`, `logistics` — بعضهم
(زي `zamakana`) قد يكون آمنًا فعليًا، والبعض الآخر لسه غير مفحوص).

**الحالة:** 🟡 **مفتوح — توثيق فقط، صفر تنفيذ.** يحتاج جلسة أمنية
مخصَّصة منفصلة (خارج نطاق أي جلسة referral/affiliate) تبدأ بفحص كامل
للـ14-15 ملف لتحديد العدد الدقيق للدومينات المعرَّضة فعليًا، ثم تقرر
بين: (أ) إصلاح ضيّق (`get_plan_by_id` + معامل `service_id` إجباري في
`check_feature_access` يقيّد اللف على نفس الخدمة بس)، أو (ب) حل جذري
(ربط رسمي `feature → service_id` على مستوى الـschema، migration
جديدة). **لا تصلح `get_plan_by_id` في أي جلسة مستقبلية بمعزل عن هذا
البند — نفس التحذير الأصلي لسه ساري.** تفاصيل كاملة:
`.claude/reports/saas-get-plan-by-id-security-tradeoff-note.md`.

---

## [2026-09-07] `referral-affiliate-systems-unified-into-scope-based-model` —
توحيد 3 أنظمة إحالة/عمولة متضاربة في نظام واحد (feat)

**ما تغيَّر:** 3 أنظمة منفصلة تمامًا (affiliate domain 10-مستويات
Product-Scoped الميت تشغيليًا، commerce Sponsor Chain الحي بلا تمايز
منتج، والـ12 دومين بمستوى واحد معطَّل) اتوحَّدوا في نظام واحد قائم على
مفهوم جديد `AffiliateScope`/`AffiliateScopeMember` — نطاق عمولة (منتج
فردي/مجموعة/كل مبيعات الـtenant) بدل الربط المباشر بـ`product_id`، يسمح
بشجر/عمولات منفصلة تمامًا لكل نطاق بلا تداخل. نظام `commerce` القديم
(`AffiliateTree`/`CommissionRecord`/`AffiliateConfig`) حُذف بالكامل.
الـ12 دومين (`zamakana`, `transport`, `insurance`, `tourism_sports`,
`tenders_auctions`, `service_marketplace`, `employment`, `realestate`,
`manufacturing`, `arbitration_syndicates`, `invitations`, `digital_twin`)
بقوا يستخدموا نفس خط أنابيب `Commission` الموحَّد (10 مستويات فعلية)
عبر `User.referred_by_user_id` الجديد، بدل `ActionCommission` (مستوى
واحد، كان معطَّلًا أصلًا). خدمة affiliate بقت قابلة للتفعيل كـSaaS لكل
tenant عبر `saas_service_catalog`، بـhook تلقائي ينشئ نطاق `ENTITY_WIDE`
افتراضي عند أول اشتراك.

**التحقق:** migration `045` مطبَّقة فعليًا على DB (`eppne_v2`)، round-trip
`downgrade→upgrade` ناجح. `pytest tests/test_referral_affiliate_unified_system.py`
— 6/6 ناجحة (سيناريوهات: عمولة أساسية، سلة بنطاقين مختلطة مع تقسيم
صحيح، تفعيل SaaS + idempotency، zamakana كمرجع، digital_twin كحالة
خاصة، تخطٍّ صامت عند عدم التفعيل).

**تفاصيل كاملة:**
`.claude/reports/referral-affiliate-system-design-session-log.md`
(التحقيق الأولي واكتشاف الأنظمة الثلاثة)،
`.claude/reports/referral-affiliate-unified-implementation-session-log.md`
(التصميم التفصيلي الكامل)،
`.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md`
(سجل التنفيذ الفعلي لكل مرحلة)،
`.claude/reports/referral-affiliate-unified-system-final-summary.md`
(ملخص فهرسي نهائي).

---

## [2026-09-07] `fix-get-referral-tree-multiple-results-found` —
إصلاح باج MultipleResultsFound موثَّق سابقًا (fix)

**السبب الجذري (كان):** `AffiliateRepository.get_referral_tree(user_id,
tenant_id)` كانت تفلتر بـ`referred_id` وحده — لو نفس المستخدم له صفوف
`ReferralTree` متعددة (نطاقات مختلفة، سيناريو معتمَد صراحة في التصميم
الجديد)، `scalar_one_or_none()` كانت ترمي `MultipleResultsFound`.

**الإصلاح:** التوقيع بقى `get_referral_tree(user_id, tenant_id, scope_id)`
— يفلتر بـ`entity_type='SCOPE' AND entity_id=scope_id` صراحة، والمشي
عبر السلسلة (`_distribute_levels`) بقى يمرّر نفس `scope_id` في كل
استدعاء متكرر — القيد الفريد الموجود بالفعل (`ix_referral_trees_unique_referred_scope`)
بقى يضمن صفًا واحدًا حقيقيًا لا نظريًا فقط.

**التحقق:** مؤكَّد حيًا في اختبار `test_basic_referral_creates_level1_commission`
(`tests/test_referral_affiliate_unified_system.py`) + الاختبار اليدوي
الأولي قبله. تفاصيل كاملة:
`.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md`
(قسم Phase 1-2).

---

## [2026-09-07] `fix-academy-enrollment-affiliate-commission-never-distributed` —
تسجيل كورس بكود إحالة كان يسجّل الشجرة بس، صفر عمولة توزَّعت أبدًا (fix)

**الاكتشاف:** `academy/service.py` (تسجيل كورس عبر `affiliate_code`) كان
يستدعي `track_referral` فقط — يسجّل `ReferralTree` بلا أي استدعاء لدالة
توزيع عمولة بعدها. **هذا يعني: أي عمولة "متوقَّعة" من تسجيل كورس بكود
إحالة لم تتولَّد فعليًا من أي وقت مضى في الإنتاج** — فشل صامت موجود منذ
كتابة الكود الأصلي، لم يكن موثَّقًا صراحة في أي تقرير سابق.

**الإصلاح:** بعد `track_referral`، لو الدفع اكتمل بمبلغ حقيقي
(`amount > 0 and payment_status == "COMPLETED"`)، يُستدعى
`distribute_commissions_for_sale_event` فعليًا (`source_type=
"ACADEMY_ENROLLMENT"`). لو النطاق غير موجود (خدمة affiliate غير مفعَّلة
SaaS للـtenant)، يتخطَّى بصمت — نفس نمط الحماية الأصلي.

**تفاصيل كاملة:**
`.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md`
(قسم Phase 5).

---

## [2026-09-07] `fix-affiliate-celery-tasks-signature-bugs-and-beat-schedule` —
3 أعطال توقيع مستقلة في tasks/affiliate.py + تسجيل أول جدولة فعلية (fix)

**3 أعطال مستقلة (موثَّقة سابقًا في تقارير Phase 10 قديمة، أُصلحت الآن
فعليًا):**
1. `distribute_commissions_task`: كانت تنادي `service.distribute_commissions(order_id, tenant_id)`
   بتوقيع غير موجود أصلًا → `service.distribute_commissions_for_order(order_id)`.
2. `release_commissions_task`: كانت ناقصة `tenant_id` في توقيع الـtask
   نفسها (مش بس في استدعاء `AffiliateService`) — أُضيف كمعامل جديد.
   اكتشاف جانبي: كانت كمان تتجاهل `idempotency_key` الممرَّر لها بالكامل
   — أُصلح كمان.
3. `clean_expired_links_task`: كانت تنادي `delete_expired_invitations`
   بمعامل واحد بينما التوقيع الحقيقي يتطلب `tenant_id` إجباري. **أول
   نمط "loop عبر كل الـtenants النشطين" بالمشروع** (لا سابقة مماثلة في
   `saas_tasks.py`/`agritech.py`) — استعلام `AcademyTenant` لكل tenant
   نشط ثم loop.

**+ تسجيل فعلي في `beat_schedule`** (`core/celery_config.py`) —
`clean_expired_links` كانت مُعرَّفة بالكود منذ البداية **بلا أي جدولة
Celery Beat تنادي عليها إطلاقًا** — أُضيف entry جديد (5:00 صباحًا يوميًا).

**تفاصيل كاملة:**
`.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md`
(قسم Phase 8).

---

## [2026-09-07] — قرار تصميم: توحيد check_feature_access/can_access_service عبر جدول many-to-many جديد

**السبب:** `check_feature_access` (8 دومينات: `employment`, `digital_twin`,
`arbitration_syndicates`, `realestate`, `manufacturing`, `logistics`,
`insurance`, `invitations`) بتفحص `plan.features` كنص حر بلا schema
enforcement، بلا ربط فعلي بـ`service_id`. مؤكَّدة كمعرَّضة عبر جلستين
مستقلتين:
1. جلسة grep على الكود عبر الـ8 دومينات —
   `.claude/reports/check-feature-access-vs-can-access-service-audit-session-log.md`.
2. جلسة تدقيق بيانات (dev DB) —
   `.claude/reports/plan-service-mapping-data-audit-session-log.md`.

**اكتشاف داعم:** `ServicePlan.service_id` (FK) حاليًا single-service بس،
وحقل `features` (JSONB حر) فيه تناقض دلالي مؤكَّد مع الـFK في صف واحد
(`plan_id=2`: `service_id` بيشاور على service اسمه
`P-SAAS9-VERIFY-CATALOG-8fa402`، لكن `features` محتواه
`["real_estate", "insurance"]` — قطاعات تانية تمامًا). الصف ده test
artifact، اتجاهل كداتا إنتاج فعلية، بس هو الدليل المباشر على وجود مصدرين
متعارضين للحقيقة (FK مقابل نص حر).

**القرار:** جدول ربط جديد `saas_plan_service_access(plan_id, service_id)`
many-to-many. Services بس مبدئيًا (بلا granularity على مستوى feature جوه
الخدمة).

**المؤجَّل صراحة (منتجي، بعد الإطلاق):** feature-level granularity جوه
الخدمة الواحدة.

**استراتيجية الانتقال:** Expand-Contract — العمود القديم `service_id`
يفضل `nullable` مؤقتًا في migration الإنشاء، وتُحذف في migration منفصلة
بعد تحقق فعلي (grep) إن صفر كود بيستخدمه.

**ملاحظة بيانات:** مفيش داتا عملاء إنتاج حاليًا — كل صفوف
`saas_service_plans`/`saas_service_catalog` الحالية test artifacts، عدا
مثال ذهني متفق عليه (أكاديمية + أفلييت + متجر) هيُستخدم كأساس اختبار.

**الحالة:** قرار تصميم موثَّق فقط — لم يُنفَّذ أي migration أو تعديل كود
بعد.

---

## [2026-09-07] `backlog-can-access-service-past-due-dead-branch` — فرع `PAST_DUE` في `can_access_service` غير قابل للوصول فعليًا (backlog، مش fix)

**الاكتشاف:** أثناء مراجعة `can_access_service`
(`app/domains/saas/service.py:328-350`) قبل تحويل دومين `insurance`
عليها، لوحظ إن الفرع الخاص بحالة `PAST_DUE` (سطور 342-348، بيدي فترة
سماح `grace_period_end_date` قبل ما يحوّل الاشتراك لـ`EXPIRED`) **غير
قابل للوصول فعليًا في الوقت الحالي** — الاستعلام اللي بيجيب الاشتراك
(`get_active_subscription`, `app/domains/saas/repository.py:133-151`)
بيفلتر `status.in_(["ACTIVE", "TRIAL"])` صراحة في الـSQL نفسه، فمستحيل
يرجع صف بحالة `PAST_DUE` أصلًا عشان الكود بعده (`if subscription.status
== "PAST_DUE"`) يتنفذ. النتيجة: أي تينانت فعليًا بحالة `PAST_DUE` هيوصل
لسطر `return subscription.status in ["ACTIVE", "TRIAL"]` (لو رجع أصلًا،
وهو مش هيرجع) أو ببساطة `subscription is None` في سطر 339 لأن الاستعلام
مستبعده من الأساس — يعني منطق "فترة السماح" **مُعطَّل فعليًا لكل
التينانتات، بدون أي رسالة خطأ أو تحذير يوضح كده**.

**لماذا backlog مش fix:** الإصلاح يحتاج قرار تصميمي (هل `get_active_subscription`
تتوسّع لتشمل `PAST_DUE` كمان، ولا فرع `PAST_DUE` في `can_access_service`
يتشال كـdead code، ولا حل تالت) — قرار خارج نطاق أي من الجلستين اللي
اكتُشف فيهم (مراجعة `can_access_service-unification-review` ثم توحيد
`insurance` عليها)، وممنوع صراحة لمسه في جلسة التوحيد نفسها. راجع
`.claude/reports/can-access-service-unification-review-session-log.md`
§1 (أول توثيق للاكتشاف) و
`.claude/reports/can-access-service-unification-session-log.md` (جلسة
التوحيد اللي أكَّدت عدم اللمس).

**الحالة:** backlog مفتوح — لسه محتاج قرار تصميم بشري قبل أي إصلاح.

---

## [2026-09-07] `check-feature-access-to-can-access-service-unification-day-summary` — ملخص شامل: مسار توحيد check_feature_access/can_access_service من القرار للتنفيذ عبر 7 دومينات

**القرار الأساسي (بداية اليوم):** بدل الاعتماد على `plan.features`
(JSONB نص حر بلا schema enforcement) لتحديد الخدمات المتاحة لخطة معيّنة
— قرار جدول ربط **many-to-many جديد** (`saas_plan_service_access`
بأعمدة `plan_id`/`service_id`، composite PK). **Services بس مبدئيًا**
(بلا granularity على مستوى feature جوه الخدمة الواحدة — ده مؤجَّل صراحة
لمرحلة منتجية لاحقة). راجع البند الأول
`design-decision-plan-service-access-many-to-many` أعلى هذا الملف
للتفاصيل الكاملة (السبب، الاكتشاف الداعم، استراتيجية Expand-Contract).

**migrations 046/047 (إنشاء الجدول + RESTRICT):**
- `046_create_saas_plan_service_access`: إنشاء `saas_plan_service_access`
  (FKs بـ`ondelete='CASCADE'` كخطوة أولى) + جعل `saas_service_plans.service_id`
  **nullable** (Expand-Contract، العمود القديم لسه موجود، الحذف الفعلي
  مؤجَّل). راجع `.claude/reports/saas-plan-service-access-migration-session-log.md`.
- `047_saas_plan_service_access_fk_restrict`: تعديل الـFKين نفسهم من
  `CASCADE` إلى `RESTRICT` (عبر drop/recreate constraint، إجباري في
  Postgres لتغيير `ondelete`). راجع
  `.claude/reports/saas-plan-service-access-restrict-fix-session-log.md`.
- الاتنين اتعمل لهم round-trip test كامل (`downgrade -1` ثم `upgrade head`)
  وأكَّدوا نجاح تام قبل ما يُعتبروا مستقرين.

**Pilot ثم التوحيد الكامل (7 دومينات):**
- **Pilot أول** على دومين `insurance` وحده (دالتين مؤقتتين
  `can_access_service_via_plan`/`has_any_active_subscription` في
  `saas/service.py`)، اختبار حي كامل (granted + denied) أثبت إصلاح فعلي
  لعيب حقيقي: تينانت كان بيتمنح وصول insurance خطأً بسبب تطابق نصي محض
  في `features` خطة غير متعلقة. راجع
  `.claude/reports/insurance-can-access-service-pilot-session-log.md`.
- **مراجعة قبل التنفيذ** (`can_access_service` الحالية كاملة + خريطة
  backfill المقترح دقيقة صف-بصف). راجع
  `.claude/reports/can-access-service-unification-review-session-log.md`.
- **التوحيد الكامل الفعلي:** تعديل `can_access_service` نفسها (سطر واحد:
  `get_active_subscription` → `get_active_subscription_via_plan_access`،
  فحص `TenantServiceAccess` وفرع `PAST_DUE` لم يُلمَسا)، حذف الدالتين
  المؤقتتين، وإرجاع `insurance/service.py::_check_saas_limits` لنفس نمط
  الـ6 دومينات اللي كانت أصلًا بتستخدم `can_access_service` (`zamakana`,
  `transport`, `tourism_sports`, `tenders_auctions`, `social`,
  `service_marketplace`). اختبار حي فعلي لكل الـ7 دومينات (6 نجحوا
  200/201 بوضوح، السابع — `service_marketplace` — نجح على مستوى الـSaaS
  gate نفسه لكن فشل لاحقًا بمشكلة Redis/Celery منفصلة تمامًا، راجع البند
  التالت تحت). راجع
  `.claude/reports/can-access-service-unification-session-log.md`
  للتفاصيل الكاملة (diffs حرفية، كل الطلبات/الردود، تحليل الـ500).

**4 بنود backlog اتكشفوا اليوم — كل واحد يحتاج جلسة/قرار منفصل، ولسه
مفتوحين كلهم:**

1. **فرع `PAST_DUE` في `can_access_service` غير قابل للوصول فعليًا
   (dead code)** — موثَّق بالتفصيل في البند
   `backlog-can-access-service-past-due-dead-branch` فوق مباشرة في هذا
   الملف. يحتاج قرار تصميمي (توسيع الاستعلام ليشمل `PAST_DUE`، أو حذف
   الفرع الميت) قبل أي إصلاح.

2. **`tests/test_saas_active_subscription.py` بيفترض السلوك القديم
   (الخاطئ) كـ"النجاح المتوقَّع" لـ`insurance`** — اختبارين
   (`test_insurance_subscribe_saas_check_passes`,
   `test_insurance_review_claim_saas_check_passes_then_hits_known_bug`)
   بيفشلوا الآن **بشكل صحيح ومتوقَّع** بعد التوحيد، لأنهم بيعتمدوا على
   `TENANT_ID=1` اللي كان بيتمنح وصول insurance وهميًا بسبب تطابق نصي
   عرضي في خطة غير متعلقة (نفس العيب اللي اتصلح). الاختبارات دي لسه لم
   تُعدَّل — محتاجة seed حقيقي جديد لخدمة insurance الفعلية بدل الاعتماد
   على التطابق النصي القديم. تفصيل كامل في §8.1 من
   `.claude/reports/can-access-service-unification-session-log.md`.
   **(تحديث لاحق: البند اتوسّع بعد جلسة `remaining-7-domains` ليشمل
   `realestate` كمان — راجع القائمة الموسَّعة في بانر الحالة أعلى
   الملف، بند 2، و§8.5 من
   `.claude/reports/remaining-7-domains-can-access-service-migration-session-log.md`.)**

   **الحالة [تحديث 2026-09-08]: ✅ اتحل جزئيًا** — بوابة
   `can_access_service` اتفتحت للأربعة اختبارات كلهم (seed تينانت 1
   مكتمل: صف `saas_tenant_subscriptions` + صف
   `saas_tenant_service_access` لكل من `insurance`(101)/`real_estate`(107)،
   بنفس نمط تينانت 16 الموجود مسبقًا). **اختباري `insurance` نجحا
   بالكامل (`2 passed`)** — `test_insurance_subscribe_saas_check_passes`
   و`test_insurance_review_claim_saas_check_passes_then_hits_known_bug`.
   **اختباري `realestate` (`test_realestate_rent_unit_saas_check_passes`،
   `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`)
   لسه فاشلين** — لكن ببرهان traceback مباشر إن بوابة الـSaaS نفسها
   عدّت بنجاح تام؛ الفشل الحالي راجع لمشاكل fixture منفصلة تمامًا
   ببوابة الـSaaS (راجع البندين الجديدين تحت: `realestate-test-fixture-landlord-not-registered-land-owner`
   و`realestate-ai-agent-exception-silently-swallowed`). تفصيل كامل
   في `.claude/reports/plan-features-tests-fix-investigation-session-log.md`
   و`.claude/reports/plan-features-tests-fix-session-log.md`.

3. **تناقض بورت Redis/Celery في `.env` (موجود من قبل، غير مرتبط
   بالتوحيد)** — `REDIS_URL` بيشاور صح على `127.0.0.1:6380` (مطابق
   لحاوية Docker الفعلية)، لكن `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`
   لسه بيشاوروا على `127.0.0.1:6379` (بورت غلط) — أي `.delay()` لأي
   Celery task هيفشل بـ`ConnectionRefusedError`. اكتُشف عبر اختبار
   `service_marketplace` الحي (فشل بـ500 بعد ما الـSaaS gate نجح فعليًا).
   لم يُصلَح — تفصيل كامل في §7 من
   `.claude/reports/can-access-service-unification-session-log.md`.

4. **الـ7 دومينات الباقيين لسه على `check_feature_access` القديمة**
   (`employment`, `digital_twin`, `arbitration_syndicates`, `realestate`,
   `manufacturing`, `logistics`, `invitations`) — كل واحد محتاج نفس نمط
   تحويل `insurance` (استبدال استدعاء `check_feature_access` بـ
   `can_access_service`)، بجلسة منفصلة وموافقة صريحة لكل دومين على حدة.
   `check_feature_access` نفسها **لم تُلمَس** ولسه موجودة لحد ما آخر
   دومين يتحول.

**⚠️ ملاحظة بيانات مهمة قبل أي seed إنتاجي حقيقي:** جدول
`saas_plan_service_access` فيه دلوقتي **12 صف إجمالًا**، وكلهم بيانات
اختبار/backfill من جلسات اليوم (7 من الـbackfill الأصلي + 5 من seed
اختبار الدومينات الـ5 الإضافية في جلسة التوحيد) — **صفر بيانات إنتاج
حقيقية**. **لازم تتراجع/تتنضف صراحة قبل أي seed إنتاجي حقيقي لأي دومين**،
وإلا هتختلط صفوف اختبار (`*-pilot-plan`, `TEST_*`) مع بيانات حقيقية في
جدول واحد بلا تمييز واضح غير الأسماء النصية.

## [2026-09-07] backlog-affiliate-commission-registration-systemwide-broken — ✅ اتحقَّق منه، لا حاجة لإصلاح كود

✅ **اتحقَّق منه — مفيش regression حقيقي.** تحقيق كامل
(`.claude/reports/affiliate-commission-registration-investigation-session-log.md`)
أثبت حيًا إن الكود شغّال صح بعد commit `2960d9d`: العمود
`User.referred_by_user_id` بقى موجود فعليًا، والدالة بترجع بصمت (بلا
log) لمستخدم بلا محيل — سلوك صحيح منطقيًا، مش عطل. الفشل في الـ10
اختبارات سببه إنها كُتبت قبل 19 يوم من التوحيد وكانت تتوقع
`AttributeError` قديم (لما العمود مكانش موجود) كدليل نجاح — دليل قاطع:
كل الـ10 فشل بـ`AssertionError` بسيط، صفر `TypeError`/`AttributeError`
في أي منهم.

**تصحيح خطأ تصنيف:** `social` من ضمن قائمة الـ11 دومين الأصلية بالغلط —
`_register_affiliate_commission` غير موجودة أصلًا في
`social/service.py`، والملف لم يُلمَس بـcommit `2960d9d`. فشله بند
منفصل تمامًا (راجع البند الجديد تحت،
`backlog-social-get-user-email-tenant-mismatch-behavior`).

**الحالة النهائية:** لا حاجة لإصلاح كود. backlog متبقٍّ (منخفض
الأولوية): تحديث الـ10 اختبارات لتعكس السلوك الصحيح الجديد (غياب log
لمستخدم بلا محيل = نجاح)، أو توسيعها لتغطي سيناريو "مستخدم معاه محيل
فعلي" فعليًا.

## [2026-09-07] backlog-social-get-user-email-tenant-mismatch-behavior — ✅ اتحل [تحديث 2026-09-08] — الكود سليم كما هو، تم تحديث الاختبار ليتوقّع NotFoundError صريح بدل fallback نصي قديم

اختبار `test_social_get_user_email_correct_and_wrong_tenant` كان بيفشل
لأنه بيتوقع `_get_user_email` (`social/service.py:718-724`) ترجّع
fallback نصي (`f"user_{user.id}@eppne.com"`) لـtenant خاطئ، لكن الكود
الفعلي بيرمي `NotFoundError` صراحة. مكتشَف أثناء تحقيق
`backlog-affiliate-commission-registration-systemwide-broken` (بند فوق)
بالصدفة — غير مرتبط إطلاقًا بـcommit `2960d9d` أو بمنطق العمولة
(`social/service.py` لم يُلمَس بالتوحيد، والدالة المعنية مختلفة كليًا).
كان محتاج قرار تصميمي: استثناء صريح صح (والاختبار قديم)، ولا fallback
مطلوب فعليًا (والكود ناقص)؟ راجع
`.claude/reports/affiliate-commission-registration-investigation-session-log.md`
§5 للتفاصيل الكاملة عن الاكتشاف الأصلي.

**[تحديث 2026-09-08] القرار اتحسم: صفر تعديل على الكود الإنتاجي.**
`_get_user_email` رمي `NotFoundError("Receiver not found in your
tenant")` صراحة لـtenant خاطئ هو السلوك الصحيح المتعمَّد — لا يوجد أي
مسار fallback في الدالة أصلًا، ومتّسق مع تعليق موجود بالفعل عند نقطة
استدعاء شقيقة (`social/service.py:578`، `# raises NotFoundError if
receiver is outside your tenant`). الاختبار القديم حُدِّث ليتوقّع
`pytest.raises(NotFoundError)` بدل الـfallback النصي غير الموجود أصلًا
(نفس الـimport ونفس النمط المستخدَمين أصلًا في باقي الملف). شُغِّل
الاختبار حيًا بعد التعديل ونجح (`1 passed`). راجع
`.claude/reports/social-get-user-email-test-fix-session-log.md`
للتفاصيل الكاملة. **الحالة النهائية: backlog مُغلَق، لا حاجة لأي إصلاح
كود إضافي.**

## [2026-09-07] backlog-invitations-create-invitation-broken

`InvitationsService.create_invitation` (`POST /api/invitations/`)
بترجع `500` دايمًا لأي تينانت عنده صلاحية CRM فعلية (اتأكَّد حيًا أثناء
اختبار جلسة تحويل دومين `invitations` من `check_feature_access`).
السبب الجذري: `_assign_ai_agent` (`invitations/service.py`, سطر
~108-115) بتحاول `agents[0]` على نتيجة `AIAgentsRepository.list_agents()`
اللي بترجع `PaginatedResponse[AIAgentResponse]` — غير قابلة للفهرسة
مباشرة، فترفع `TypeError`. الاستدعاء غير مشروط (بلا `if` قبله)، يعني
كل طلب لهذا الـendpoint هيفشل بغض النظر عن أي شيء تاني. مؤكَّد إنه
غير مرتبط بمسار `check_feature_access`→`can_access_service` (العطل
بعد بوابة الـSaaS بمراحل، صفر لمس لـ`create_invitation`/`_assign_ai_agent`
في أي جلسة من مسار التوحيد). ملاحظة إضافية غير حرجة من نفس التحقيق:
`data.get("custom_message", "")`/`target_entity_identifier` بيرجعوا
`None` صراحة مش `""` بسبب `Optional[str] = None` في الـschema، بيكسر
`bleach.clean()` قبل ما يوصل لعطل `_assign_ai_agent` أصلًا لو الحقول
فاضية. راجع `.claude/reports/remaining-7-domains-can-access-service-migration-session-log.md`
§7.4.1 للتفاصيل الكاملة والـtraceback.

**الحالة: ✅ اتحل.** تحقيق كامل
(`.claude/reports/invitations-create-invitation-investigation-session-log.md`)
كشف 4 أعطال بترتيب تنفيذ (مش 2 زي ما كان موثَّق أول مرة): (1)
`bleach.clean(None)` على `title` (سطر 172) — مكتشَف حديثًا، أول عطل
فعليًا في ترتيب التنفيذ. (2)+(3) نفس العطل على
`custom_message`/`target_entity_identifier` (سطر 173-174) — معروفين
مسبقًا. (4) `_assign_ai_agent` بتحاول `agents[0]` على
`PaginatedResponse` غير قابلة للفهرسة (سطر 115) — العطل الجذري
الحقيقي، بيمنع أي طلب ناجح بغض النظر عن باقي الحقول.

الإصلاح المُنفَّذ
(`.claude/reports/invitations-create-invitation-fix-session-log.md`):
4 أسطر فقط — `data.get(key) or ""` بدل `data.get(key, "")` للثلاثة
حقول، و`agents.data[0] if agents.data else None` بدل
`agents[0] if agents else None`. اختبار حي مزدوج (حقول فاضية + حقول
حقيقية) نجح بالكامل (`id=71`, `id=72`). مقارنة baseline صارمة عبر
`git stash` أثبتت تطابق حرفي للـ16 فشل regression قبل وبعد الإصلاح —
صفر أثر جانبي.

## [2026-09-07] backlog-paginatedresponse-misuse-automation-list-available-agents

✅ اتحل. تدقيق شامل عبر المشروع كله
(`.claude/reports/paginatedresponse-misuse-audit-session-log.md`)
كشف 3 حالات حقيقية (مش حالة واحدة زي ما كان موثَّق أول مرة):
(1) `invoicing/router.py:159` — الأخطر، بيصيب المسار الافتراضي
لـ`GET /invoices` لأي مستخدم عادي (أغلبية الاستخدام الفعلي)، وكشف
كمان عطل ثانٍ مخفي (`repository.py:110` — اسم حقل غلط `items=`
بدل `data=`) اتصلح بموافقة صريحة موسَّعة. (2) `academy/router.py:248`
(`GET /store/courses`) — بترجع كائن `PaginatedResponse` كامل تحت
`response_model` غير متوافق. (3) `automation/service.py:1045`
(`list_available_agents`) — العطل الأصلي المكتشَف، نفس فئة عطل
`invitations`.

الإصلاح (`.claude/reports/paginatedresponse-misuse-fix-session-log.md`):
كل حالة اتصلحت في جلسة منفصلة بموافقة صريحة، واختُبرت حيًا بنجاح
فعلي (200 + بيانات حقيقية في الرد لكل حالة، مش استنتاج من الكود).
التدقيق فحص ~33 نقطة استدعاء عبر المشروع كله — الباقي (~30) صحيح
أو كود ميت (موثَّق بالتفصيل في تقرير التدقيق).

## [2026-09-07] backlog-privacy-double-pagination-offset-limit — ✅ اتحقّق منه — مفيش عطل وظيفي

اكتُشف بالصدفة أثناء تدقيق `PaginatedResponse` الشامل: دالة
`list_erasure_requests` في `privacy/repository.py` (سطر 143 ثم 148)
بتطبّق `query.offset(skip).limit(limit)` مرتين على نفس الـquery.
تحقيق مخصص (`.claude/reports/privacy-double-pagination-investigation-session-log.md`)
أثبت: **مفيش عطل وظيفي**. SQLAlchemy بيستبدل قيمة `offset`/`limit` عند
كل استدعاء (`_offset_clause`/`_limit_clause`) — مش بيتراكم — مؤكَّد
بتجربة مباشرة ضد SQLAlchemy 2.0.36 (استدعاء بقيم مختلفة أثبت إن آخر
استدعاء بيغلب بالكامل). وبما إن الاستدعائين في الكود بيمرروا نفس قيم
`skip`/`limit` بالظبط، الناتج النهائي مطابق 100% لاستدعاء واحد.
اختبار حي ضد Postgres حقيقي (25 صف مُدخَلة مؤقتًا، صفحتين بـ
`limit=20`) أكّد كده عمليًا: صفحة 1 = 20 عنصر صح، صفحة 2 = 5 عناصر
صح، `total` صح في الاثنين، دمج الصفحتين طابق الترتيب الكامل المتوقَّع
بلا أي تكرار أو فقدان بيانات؛ كل بيانات الاختبار اتنضّفت بعدها والجدول
رجع فاضي زي ما كان.

**التصنيف الصحيح:** كود زائد/مكرر (redundant chaining) — سطر 148
بيعيد ضبط نفس القيمة اللي اتحطت في سطر 143 من غير داعٍ وظيفي — مش
باج. **الحالة النهائية: backlog مُغلَق كتحقيق، لا حاجة لأي إصلاح
عاجل.** أي تعديل مستقبلي (حذف السطر المكرر) هيكون تنظيف كود اختياري
بحت بدون أثر على السلوك. راجع التقرير أعلاه للتفاصيل الكاملة (بما فيها
حصر شامل بالـgrep أثبت إن باقي دوال الملف بتطبّق offset/limit مرة
واحدة بس، مفيش تراكب فيها).

## [2026-09-08] backlog-realestate-test-fixture-landlord-not-registered-land-owner — ✅ اتحل [تنفيذ 2026-09-17]

اكتُشف أثناء seed تينانت 1 لخدمتي `insurance`/`real_estate` في
`saas_tenant_subscriptions`/`saas_tenant_service_access` (متابعة بند
Backlog #2 أعلاه). بعد ما بوابة `can_access_service` بقت تعدي، ظهر إن
`test_realestate_rent_unit_saas_check_passes`
(`tests/test_saas_active_subscription.py:168-211`) بيفشل بـ
`PermissionDeniedError("ليس لديك صلاحية تعديل هذه الوحدة")`
(`realestate/service.py:463`) — **مش بسبب بوابة الـSaaS** (اتحققت
بنجاح تام، دليل traceback مباشر).

**السبب الجذري:** الاختبار بينشئ مستخدم `landlord` جديد عشوائي في كل
تشغيلة ويمرره كـ`landlord_id` لـ`rent_unit`، لكن
`_get_land_owner_for_unit` (`realestate/service.py:683-695`) بتجيب
المالك الحقيقي حصريًا من `land_assets.owner_id` — وصف `land_assets`
المشترك (`id=1`، `EXISTING_LAND_ASSET_ID` في ملف الاختبار سطر 119) له
`owner_id=47` **ثابت** (تحقُّق DB مباشر). الفحص `owner.id !=
landlord_id` بيرفض بحق لأن `landlord` المُنشأ حديثًا فعلًا مش نفس
`user_id=47`.

**تأكيد إضافي مستقل — مربوط ببند `realestate-hooks-layer-design-decision`
[2026-08-31]:** نفس الجلسة القديمة دي طبّقت **نفس نمط فحص الملكية
بالحرف** (`_get_land_owner_for_unit`) على `PATCH`/`DELETE
/realestate/units/{id}` واختبرته حيًا بـ10 اختبارات pytest ناجحة، **و**
وثَّقت وقتها صراحةً "3 فشلات موجودة *قبل* هذه الجلسة (drift بيئي في
SaaS feature flags لـ`tenant_id=1`، غير مرتبطة)" — يعني تينانت 1 كان
عليه بالفعل drift بيانات معروف ومُوثَّق من قبل في نفس منطقة
`realestate`/SaaS، بشكل مستقل تمامًا عن هذا الاكتشاف. هذا يرجّح إن فجوة
fixture الاختبار الحالية (استخدام `landlord`/`owner` عشوائيين بدل
المالك الحقيقي المسجَّل) نمط متكرر في اختبارات الدومين، مش حالة معزولة.

**الإصلاح المقترح (غير مُنفَّذ — قرار مستخدم مطلوب):** تمرير
`landlord_id=47` (المالك المسجَّل فعليًا لـ`land_assets` رقم 1) بدل
إنشاء `landlord` عشوائي جديد، أو إنشاء `land_asset` throwaway منفصل
مملوك للمستخدم الجديد نفسه.

**المرجع:** `.claude/reports/plan-features-tests-fix-session-log.md`
§2.3/§5.1، `.claude/reports/plan-features-tests-fix-investigation-session-log.md`،
`.claude/reports/realestate-design-decision-session-log.md`
(بند `realestate-hooks-layer-design-decision` [2026-08-31]).

**✅ اتحل [تنفيذ 2026-09-17]:** نُفِّذ بالظبط الحل المقترح أعلاه —
`test_realestate_rent_unit_saas_check_passes` بقت تستخدم
`landlord_id=47` (المالك الحقيقي المسجَّل لـ`land_assets.id=1`)
مباشرة بدل إنشاء `landlord` عشوائي جديد، بلا أي لمس على
`land_assets.id=1.owner_id` نفسه (أصل مشترك، قراءة فقط)، وبلا إضافته
لقائمة تنظيف المستخدمين (`user_ids`) — نفس نمط "مستقبِلين مشتركين
قراءة فقط" الموثَّق بالفعل في الملف. اكتُشف الباج ده حيًا من جديد (بشكل
مستقل) أثناء جلسة مراجعة backlog دورية [2026-09-16] قبل ما نلاقي إنه
موثَّق هنا بالفعل — تأكيد إضافي إن التحليل الأصلي [2026-09-08] كان
دقيقًا 100%. تحقق حي: `1 passed`، صفر مشاكل تالتة. تقرير الجلسة:
`.claude/reports/backlog-review-2026-09-16-session-log.md`.

## [2026-09-08] backlog-realestate-ai-agent-exception-silently-swallowed — ✅ اتحل — تمييز NotFoundError/PermissionDeniedError عن باقي الأخطاء

اكتُشف عرضًا في نفس تحقيق seed تينانت 1 أعلاه، أثناء فحص
`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
(بعد ما بوابة الـSaaS بقت تعدي بنجاح لهذا الاختبار كمان).

**العطل المباشر (سبب فشل الاختبار حاليًا):** `buyer` بينشأ في الاختبار
برصيد `0` (افتراضي `_create_funded_user` بلا تمرير `mr_usdt`)، فتكلفة
شراء 10% من وحدة سعرها `500` (=`50 MR_USDT`) بترمي
`InsufficientBalanceError` → `PermissionDeniedError("Insufficient
balance")` (`realestate/service.py:313`) قبل الوصول لأي منطق تاني —
هذا مجرد فجوة تمويل في fixture الاختبار، غير خطير لوحده.

**الاكتشاف الأخطر (كود إنتاجي، غير مُصلَح):** بالقراءة المباشرة لسطر
365-368 من `realestate/service.py`، اتضح إن استدعاء
`AIAgentsService.execute_agent_action()` (جزء من منطق
`buy_fractional_ownership`) بقى ملفوفًا بـ`try/except Exception`
بيسجّل الخطأ فقط (`logger.error(...)`) **بلا `raise`**. يعني أي فشل في
تحليل الـAI Agent لعملية الشراء — بما فيه بج Backlog #16 المُوثَّق
مسبقًا (معامل `tenant_id=` الزايد على `execute_agent_action`، اللي
التقرير الأصلي [2026-08-19] وثَّقه كـ"لسه موجود فعليًا بالقراءة
المباشرة" بمعنى إنه بيتصدَّر كـ`TypeError` غير مُمسوك وقتها) — **بقى
مُبتلَعًا صمتًا بالكامل** في هذا الموضع تحديدًا. العملية المالية
(تحويل الملكية + `finance.transfer`) بتكمل وتنجح بغض النظر تمامًا عن
نجاح أو فشل تحليل الـAI Agent، بلا أي إشارة للمستخدم أو للمُطوِّر إن
التحليل فشل.

**لماذا أولوية بارزة، ومربوط بنمط `silent-write-regression` الموثَّق
سابقًا:** المشروع عنده بالفعل بند backlog قائم (`silent-write-regression`
— جدول الـBacklog النشط أعلى الملف، بند #4) بيوثّق فئة كاملة من
الأعطال حيث الـAPI/العملية "بتنجح" ظاهريًا بينما جزء من الكتابة/المنطق
بيفشل صامتًا بلا أثر (`saas.cancel_subscription` — اتصلح، +حالتان
غير مؤكَّدتين `saas.process_auto_renewals`/`saas.can_access_service`).
هذا الاكتشاف **حالة رابعة محتملة من نفس الفئة**: نجاح ظاهري
(`buy_fractional_ownership` بترجع 201/نجاح) مع فشل صامت غير مُسجَّل
بوضوح لمستخدم/مراقب خارجي (فقط `logger.error` داخلي) لمنطق فرعي مهم
(تحليل AI للعملية). **القرار المطلوب صراحةً:** هل ابتلاع بج #16 صمتًا
هنا **سلوك مقصود** (تريث متعمَّد: فشل تحليل AI مش لازم يوقف عملية
شراء مالية حقيقية) أم **رجعة غير مقصودة** نتجت عرضًا عن إضافة
`try/except` عام لسبب تاني (مثلاً منع كراش الـendpoint الأساسي)
وأخفت بج #16 بدل ما تصلحه؟ **لم يُتحقَّق متى بالضبط اتضاف هذا
`try/except` ولا في أي جلسة** — خارج نطاق هذا التحقيق (seed بيانات
فقط، صفر لمس كود).

**الإصلاح المقترح (غير مُنفَّذ — قرار مستخدم مطلوب أولاً):**
1. تمويل `buyer` في الاختبار برصيد كافٍ (`>= 50 MR_USDT`) لتجاوز
   العطل السطحي، **ثم**
2. قرار تصميمي صريح بشأن `try/except Exception` حول
   `execute_agent_action`: تسجيل مرئي/قابل للرصد (مش `logger.error`
   داخلي فقط) على الأقل، أو إعادة `raise` مضبوطة لو التحليل جزء
   إلزامي من العملية.

**المرجع:** `.claude/reports/plan-features-tests-fix-session-log.md`
§2.4/§5.2، `.claude/reports/plan-features-tests-fix-investigation-session-log.md`،
خلفية بج #16 الأصلي: `.claude/reports/backlog-16-begin-nested-commit-session-log.md`،
نمط `silent-write-regression`: جدول الـBacklog النشط أعلى الملف، بند #4.

**الحالة:** ✅ اتحل — تمييز `NotFoundError`/`PermissionDeniedError`
(`warning`) عن أي استثناء تاني (`error`، رسالة 'unexpectedly')، بلا
`raise`، بلا تغيير سلوك مالي. تحقيق التوقيت
(`.claude/reports/realestate-ai-agent-silent-swallow-investigation-session-log.md`)
أثبت إن النمط سياسة عامة متعمَّدة عبر 16 موضع تاني في المشروع (مش
استثناء)، بس الفجوة (عدم تمييز نوع الفشل) كانت حقيقية وغير مدروسة —
اتحلت لـrealestate بس، الـ15 موضع الباقي لم يُلمَسوا (قرار نطاق ضيق
متعمَّد). اختبار حي مزدوج (`NotFoundError` حقيقي + `TypeError`
مصطنع) أثبت الفصل صح، والعملية المالية غير متأثرة في الحالتين.
تفاصيل التنفيذ والتحقق الحي:
`.claude/reports/realestate-ai-agent-exception-differentiation-fix-session-log.md`.

**✅ تأكيد إضافي [2026-09-17]:** بما إن Backlog #16 (كوارج
`execute_agent_action`) وهذا البند اتصلحوا الاتنين فعليًا، توقّع
الاختبار الأصلي `pytest.raises(TypeError, match="tenant_id")` في
`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
بقى **stale مزدوج** (مش بس فجوة تمويل الـbuyer). الاختبار اتحدَّث
ليتوقع **نجاح كامل** للعملية بدل الكراش القديم — تحقق حي كامل (خصم
رصيد دقيق + سجل ملكية صحيح) بعد `monkeypatch` لـ`create_invoice`
(تفاديًا لبند `invoicing-generate-invoice-number-count-based-collision`
المفتوح أصلًا، غير متأثر بهذا البند). تفاصيل:
`.claude/reports/backlog-review-2026-09-16-session-log.md`.

## [2026-09-08] backlog-notification-delivery-stub-empty-non-inapp-channels — 🔴🔴 أولوية بارزة

اكتُشف أثناء فحص read-only تحضيرًا لتصميم فترة سماح/إشعارات
`PAST_DUE` في `saas`. `send_notification_task` معرَّفة مرتين
متضاربتين بنفس الاسم بالظبط:

1. `app/core/celery_app.py:64-75` — stub صريح موثَّق كمؤقت
   (`@shared_task(name="send_notification_task")`، جسمها `pass`
   بالكامل، وكذلك `send_email_task` المجاورة).
2. `app/domains/communications/tasks.py:1-28` — نسخة تبدو "حقيقية"
   (تستورد `send_fcm`/`send_smtp_email`/`send_twilio_sms` فعليًا في
   أعلى الملف) لكن الفروع الثلاثة `PUSH`/`EMAIL`/`SMS` كلها كود
   مُعلَّق بـ`pass`، ولا استدعاء فعلي واحد لأي من الدوال
   المستوردة. الدالة كمان مُعرَّفة على تطبيق Celery منفصل تمامًا
   (`Celery("communications", broker=settings.REDIS_URL)`) مش نفس
   `celery_app` المركزي المُحمَّل من `app/core/celery_app.py`.

**الأثر العملي:** `CommunicationsService.send_notification(...)`
(النمط الحي المُستخدَم فعليًا من transport/automation/realestate)
بتخزن الصف في جدول `notifications` بنجاح وتستدعي
`send_notification_task.delay(...)` بنجاح (الـtask بتتقبل من
الـbroker وترجع `{"status": "sent"}` وهمي)، لكن **صفر تسليم فعلي**
لأي مستخدم عبر أي قناة بره `IN_APP` في المشروع كله — لا FCM push
حقيقي، لا إيميل SMTP، لا SMS عبر Twilio. `IN_APP` هي القناة الوحيدة
الكاملة فعليًا (لأنها مجرد صف يُقرأ لاحقًا من الجدول نفسه، بلا حاجة
لتسليم خارجي).

**المرجع:**
`.claude/reports/past-due-grace-period-notifications-investigation-session-log.md`
§3ب.

**الحالة:** 🔴 مفتوح، لم يُصلَح. يحتاج إما بناء تكامل تسليم حقيقي
(SMTP فعلي لـEMAIL، FCM فعلي لـPUSH، Twilio فعلي لـSMS) أو قرار صريح
بإزالة الادعاء بدعم هذه القنوات (توثيق `IN_APP` كقناة الدعم الوحيدة
حاليًا) لحد ما يُبنى التكامل الحقيقي.

## [2026-09-08] backlog-saas-tasks-calling-nonexistent-methods — 🔴 أولوية عالية

اكتُشف في نفس فحص read-only أعلاه، أثناء قراءة
`app/tasks/saas_tasks.py` كاملًا مقابل `SaaSControlService` الفعلية
في `app/domains/saas/service.py`. 4 من أصل 6 مهام Celery معرَّفة في
`saas_tasks.py` بتستدعي دوال على `SaaSControlService` **غير موجودة
إطلاقًا** (بحث `grep` شامل في `app/domains/saas/` أكَّد الغياب
الكامل لكل الأربعة):

- `generate_monthly_invoices` — مُستدعاة من
  `generate_monthly_invoices_task`، **ومجدولة فعليًا** في
  `beat_schedule` (`celery_config.py`، أول كل شهر 3 صباحًا) —
  هتفشل بـ`AttributeError` عند أول تنفيذ فعلي.
- `check_and_expire_trials` — مُستدعاة من `check_expired_trials_task`،
  **ومجدولة فعليًا** أيضًا (يوميًا 4 صباحًا) — نفس المصير.
- `send_trial_expiry_reminders` — مُستدعاة من
  `send_trial_expiry_reminders_task`، **غير مجدولة** في
  `beat_schedule` حاليًا، لكن الدالة نفسها غير موجودة لو اتنادت
  يدويًا أو أُضيفت جدولتها لاحقًا بدون تأكد أولًا.
- `cleanup_cancelled_subscriptions` — مُستدعاة من
  `cleanup_cancelled_subscriptions_task`، نفس وضع البند السابق
  (غير مجدولة، غير موجودة).

كل الأربعة معلَّمة في الكود نفسه بـ`# type: ignore[attr-defined]`
مع تعليق "تأكد من وجود الدالة" — إشارة إلى إن الكاتب الأصلي كان
عارف إنها غير مؤكَّدة وقت الكتابة ولم يُتحقَّق منها لاحقًا.

**المرجع:**
`.claude/reports/past-due-grace-period-notifications-investigation-session-log.md`
§4.

**الحالة:** 🔴 مفتوح، لم يُصلَح. يحتاج إما بناء الدوال الأربعة من
الصفر على `SaaSControlService` (`generate_monthly_invoices`,
`check_and_expire_trials`, `send_trial_expiry_reminders`,
`cleanup_cancelled_subscriptions`)، أو تعطيل جدولة المهمتين
المجدولتين فعليًا (`generate-monthly-invoices`,
`check-expired-trials`) مؤقتًا في `beat_schedule` لحد ما يتوفر
تنفيذ حقيقي، لمنع فشل صامت متكرر في الإنتاج.

## [2026-09-08] backlog-process-auto-renewals-task-constructor-typeerror — 🔴🔴🔴 أولوية حرجة

اكتُشف أثناء تنفيذ مهمة `check_past_due_subscriptions_task` الجديدة
(بند فترة سماح `PAST_DUE`/تنبيهات، خيار ب). `process_auto_renewals_task`
(`app/tasks/saas_tasks.py`) بتستدعي `SaaSControlService(db)` **بلا**
`tenant_id` — باراميتر إجباري بلا `default` في
`SaaSControlService.__init__(self, db, tenant_id: int)`. على الأرجح
بيرمي `TypeError: missing 1 required positional argument: 'tenant_id'`
فورًا عند محاولة الإنشاء، **قبل** الوصول لأي منطق داخل
`process_auto_renewals()` نفسها.

**الأثر المحتمل الأخطر:** `process_auto_renewals_task` هي نفسها
المصدر الوحيد الموثَّق حاليًا للتحويل التلقائي `ACTIVE → PAST_DUE`
(عبر `InsufficientBalanceError` في `process_auto_renewals`،
service.py) — أساس كل شغل فترة السماح المُنفَّذ اليوم. لو الـ`TypeError`
ده بيحصل فعليًا في كل تشغيلة، فالتحويل التلقائي **ممكن يكون مش بيحصل
خالص حاليًا** رغم وجود الكود والجدولة الكاملة في `beat_schedule`
(2 صباحًا يوميًا) — يعني كل بنية فترة السماح/التنبيهات المُنفَّذة
اليوم (`check_past_due_subscriptions_task`) هتفضل بلا أي اشتراك
`PAST_DUE` تفحصه في الإنتاج، لحد ما هذا البج يتصلح.

**نفس القصور موجود حرفيًا في مهام أخرى بنفس الملف**
(`generate_monthly_invoices_task`, `check_expired_trials_task`,
`send_trial_expiry_reminders_task`, `cleanup_cancelled_subscriptions_task`
— كل الخمسة بتستدعي `SaaSControlService(db)` بنفس الشكل)، لكن دول
أصلًا بيفشلوا لسبب آخر موثَّق مسبقًا (دوال غير موجودة —
`backlog-saas-tasks-calling-nonexistent-methods` أعلاه) فمفيش فرصة
عملية لاحظ فيها أثر الـ`TypeError` بمعزل — `process_auto_renewals_task`
هي الوحيدة اللي دالتها (`process_auto_renewals`) موجودة وكاملة
فعليًا، فهي أول مكان يظهر فيه هذا البج بوضوح لو اتأكد حيًا.

**لم يُختبَر حيًا بعد** — اكتشاف بالقراءة المباشرة للكود فقط (مقارنة
`SaaSControlService.__init__` بكل نداءات `SaaSControlService(db)` في
`saas_tasks.py` عبر `grep`)، مش بتشغيل فعلي للـworker. **أولوية فحص
فورية في الاختبار الحي القادم لفترة السماح** — لو اتأكد، فترة
السماح/التنبيهات المُنفَّذة اليوم مش هيبقى ليها أثر عملي في الإنتاج
غير مرتبطة بإصلاح هذا البج أولًا.

**المرجع:**
`.claude/reports/past-due-grace-period-notifications-implementation-session-log.md`
§2ج.

**الحالة:** 🔴 مفتوح، لم يُصلَح. يحتاج إما تمرير `tenant_id` صريح (مثلًا
نمط `SaaSControlService(db, 0)` المُستخدَم فعليًا في
`saas/router.py:273`، مع التأكد إن `process_auto_renewals(tenant_id=
None)` معدَّلة كمان عشان متقعش على `self.tenant_id` بدل فحص كل
المستأجرين — راجع نفس القصور في `trigger_renewals`، §2ج من نفس
التقرير)، أو تعديل `SaaSControlService.__init__` ليقبل `tenant_id`
اختياري لحالات الاستخدام الإدارية/عبر-المستأجرين. قرار تصميمي يحتاج
جلسة منفصلة.

## [2026-09-08] backlog-process-auto-renewals-task-tenant-zero-noop — ✅ اتحل بالكامل [تحديث 2026-09-08]

اكتُشف كمتابعة مباشرة لـ`backlog-process-auto-renewals-task-constructor-
typeerror` أعلاه: بعد إصلاح الـ`TypeError` (`SaaSControlService(db, 0)`)،
`process_auto_renewals_task` بقت تشتغل بلا كراش لكن بترجع نتيجة فاضية
دايمًا (`total: 0`) — لأن `process_auto_renewals` (service.py) كانت
بتحوّل `tenant_id=None` (الحالة الوحيدة اللي `saas_tasks.py` بينادي بيها
الدالة) لـ`self.tenant_id` (=0، سنتينل إداري بلا تينانت حقيقي بهذا الـid)
عبر `target_tenant = tenant_id if tenant_id is not None else self.
tenant_id`، بدل معالجة كل التينانتات فعليًا.

**إصلاح جزئي [2026-09-08] — جلسة منفصلة تالية:** قبل التعديل، فُحص كل
المشروع (`grep -rn "process_auto_renewals(\|trigger_renewals("`) — 3 نقاط
استدعاء فقط، صفر استخدام حي بيعتمد على الـfallback عمدًا لتحديد تينانت
حقيقي بعينه (الاستخدام الوحيد اللي بيمرر `tenant_id` صريح، عبر
`/admin/trigger-renewals?tenant_id=X`، غير متأثر). بناءً عليه: `process_
auto_renewals` (service.py) عُدِّلت لتمرر `tenant_id` مباشرة لـ
`get_subscriptions_for_renewal` (كانت أصلًا بتدعم `None`="كل التينانتات"،
بلا تعديل مطلوب فيها) بدل الـfallback، مع استبدال كل استخدام لـ
`target_tenant` جوّه الحلقة بـ`sub.tenant_id` الحقيقي لكل اشتراك (نفس نمط
`check_past_due_subscriptions`). `process_auto_renewals_task` (saas_
tasks.py) عُدِّلت لتستدعي `service.process_auto_renewals(tenant_id=None)`
صراحةً.

**التحقق الحي أثبت نجاح جزء الإصلاح المستهدف:** اشتراكان حقيقيان مستحقان
للتجديد تحت تينانت 1 (غير 0) اتلقطوا بنجاح عبر `process_auto_renewals_
task.run()` (`total: 2`، مش `0`) — طبقة اختيار/تكرار الاشتراكات عبر كل
التينانتات **بقت شغّالة ومؤكَّدة**.

**لكن اتكشف مانع تاني منفصل تمامًا وقف دون إتمام التنفيذ الفعلي (تجديد
ناجح أو تحويل `PAST_DUE`):** الاثنين فشلوا بـ`NotFoundError("المستلم غير
موجود")` بدل `SUCCESS`/`PAST_DUE` المتوقَّعين — راجع البند الجديد
`backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
تحت لتفاصيل السبب الجذري الكامل (طبقة مختلفة تمامًا، `FinanceService` مش
`SaaSControlService` نفسها).

**المرجع:**
`.claude/reports/past-due-grace-period-notifications-implementation-session-log.md`
§6 (الاكتشاف والإصلاح الأول لـ`TypeError`)، §9 (الإصلاح الجزئي لهذا البند
+ الاكتشاف الجديد).

**الحالة:** 🟡 جزئي — طبقة اختيار الاشتراكات اتصلحت ومؤكَّدة (`total:2`)،
لكن التنفيذ الفعلي (تجديد/`PAST_DUE`) لسه معطوب بمانع تاني منفصل (راجع
البند الجديد).

**⚠️ تحديث [2026-09-08، جلسة `financeservice-tenant-binding-fix`]:**
المانع التاني (`backlog-financeservice-tenant-binding-blocks-cross-
tenant-operations` تحت) اتصلح. أُعيد بالظبط نفس سيناريو التحقق الحي
هنا (اشتراكان حقيقيان تحت تينانت 1، رخيص/باهظ، عبر
`SaaSControlService(db, 0)`) كـregression test حقيقي ضد DB حي
(`tests/test_financeservice_tenant_binding_fix.py`) — **النتيجة دلوقتي:
الرخيص → `SUCCESS` فعلي (معاملة + فاتورة `PENDING` حقيقيتان على القرص)،
الباهظ → `InsufficientBalanceError` → `PAST_DUE` فعلي
(`grace_period_end_date` مضروب +3 أيام)، مؤكَّدان الاثنان عبر جلسة DB
مستقلة.** أول مرة نشوف الحلقة الكاملة (اختيار الاشتراكات + تنفيذ
العملية المالية الفعلي) شغّالة من طرف لطرف. **الحالة النهائية: ✅ اتحل
بالكامل.** تفاصيل كاملة:
`.claude/reports/financeservice-tenant-binding-fix-session-log.md`.

## [2026-09-08] backlog-financeservice-tenant-binding-blocks-cross-tenant-operations — ✅ اتحل [تحديث 2026-09-08]

اكتُشف أثناء الاختبار الحي لإصلاح `backlog-process-auto-renewals-task-
tenant-zero-noop` أعلاه. `SaaSControlService.__init__` (service.py:59-63)
بيبني `self.finance = FinanceService(db, tenant_id)` — كائن `FinanceService`
**ثابت طول عمر الـinstance**، مربوط بقيمة `tenant_id` اللي اتبنى بيها
الـ`SaaSControlService` نفسه وقت الإنشاء، مش بتينانت العملية الفعلية وقت
كل استدعاء.

**الأثر المؤكَّد حيًا:** أي عملية مالية (`self.finance.transfer(...)`) من
`SaaSControlService` instance مبني بـ`tenant_id` سنتينل (زي `(db, 0)` —
النمط الإداري المُستخدَم في `process_auto_renewals_task`/`router.py:273`)
بتفشل لأي تينانت حقيقي مختلف — `FinanceService.transfer` (finance/
service.py:78) بيدوّر على المستلم عبر `get_by_email(receiver_email,
self.tenant_id)` حيث `self.tenant_id` هنا هو تينانت الـ`FinanceService`
الثابت (0)، مش تينانت الاشتراك/العملية الحقيقي — فميرجّعش حساب النظام
الحقيقي لتينانت 1 (أو أي تينانت تاني)، ويرمي `NotFoundError("المستلم غير
موجود")` **قبل** ما يوصل لمنطق فحص الرصيد أصلًا (`InsufficientBalanceError`
مستحيل يتحقق في هذا المسار).

**تأكيد حي:** اشتراكان حقيقيان تحت تينانت 1 (واحد بسعر رخيص يفترض
`SUCCESS`، واحد بسعر باهظ عمدًا يفترض `InsufficientBalanceError→PAST_DUE`)
اتلقطوا بنجاح عبر `process_auto_renewals` (بعد إصلاح البند أعلاه) لكن
الاثنين فشلا بنفس `NotFoundError` بالحرف، بدل الوصول لأي من المسارين
المتوقَّعين.

**نفس النمط المعماري اللي ظهر مرتين النهارده في نفس الدومين (`SaaSControlService`
نفسها):** تينانت مربوط بلحظة إنشاء الـinstance بدل كل عملية على حدة —
لكن هنا في مكوّن مختلف تمامًا (`FinanceService`)، **مُستخدَم عبر دومينات
كتير غير `saas`** (أي دومين بينادي `FinanceService(db, tenant_id)` مباشرة
مُعرَّض لنفس القصور لو حاول يعالج أكتر من تينانت من نفس الـinstance).
**مرتبط أيضًا بـ`trigger_renewals`/`router.py:273` بنفس القصور** — أي
استدعاء لـ`/admin/trigger-renewals` (بتينانت محدد أو بلا تحديد) هيمر عبر
نفس `self.finance` الثابتة على `tenant_id=0`، فمعرَّض لنفس الفشل.

**هذا مش رقعة سريعة — يحتاج مراجعة معمارية مخصصة:** هل `FinanceService`
لازم تتبنى نمط per-operation (تُبنى/تُستدعى بـtenant_id لكل عملية على
حدة) بدل per-instance (تينانت ثابت وقت الإنشاء)؟ التغيير المحدود الممكن
(بناء `FinanceService` جديدة داخل حلقة `process_auto_renewals` بـ
`sub.tenant_id` بدل `self.finance` الثابتة) بيحل هذه الحالة تحديدًا بس
مش الأثر الأعمّ عبر باقي استخدامات `FinanceService` في المشروع — قرار
تصميمي يحتاج جلسة منفصلة.

**المرجع:**
`.claude/reports/past-due-grace-period-notifications-implementation-session-log.md`
§9-ج/د.

**⚠️ تحديث [2026-09-08، جلسة `financeservice-tenant-binding-fix`]:**
**الحالة النهائية: ✅ اتحل** (داخل `SaaSControlService` تحديدًا —
النطاق الفعلي الوحيد المؤكَّد لهذه المشكلة، راجع
`financeservice-tenant-binding-investigation-session-log.md` §3: صفر
دومين تاني بيعاني من نفس النمط فعليًا). الإصلاح المُنفَّذ هو الخيار
(ب) من تقييم الجلسة السابقة (نطاق ضيق، صفر لمس على `FinanceService`
نفسها أو أي دومين تاني): حذف `self.finance = FinanceService(db,
tenant_id)` الثابتة من `SaaSControlService.__init__`، وبناء
`FinanceService` محلية جوّه كل دالة على حدة بالتينانت الصح ليها —
`FinanceService(self.db, sub_tenant_id)` لكل اشتراك على حدة داخل حلقة
`process_auto_renewals` (كانت هي مصدر الباج المؤكَّد)، و
`FinanceService(self.db, self.tenant_id)` داخل `pay_invoice` (كانت
أصلًا بتستخدم نفس تينانت الـinstance، إعادة بناء محلية فقط بلا تغيير
سلوك). **الاختبار الحي أثبت الحلقة الكاملة شغّالة** (راجع تحديث البند
`backlog-process-auto-renewals-task-tenant-zero-noop` فوق للتفاصيل
الكاملة). **Regression:** 3 ملفات اختبار بتستخدم `SaaSControlService`
مباشرة — `cancel_subscription` (2/2 ✅، لا تستخدم `self.finance`
أصلًا)، `referral_affiliate` (6/6 ✅)، `saas_active_subscription` (2/4،
الفشلان الاتنان مؤكَّدان **غير مرتبطين** بهذا الإصلاح عبر traceback
كامل — مشاكل مسبقة داخل `realestate/service.py` نفسه [`landlord`
مختلف عن مالك الوحدة الفعلي: راجع `backlog-realestate-test-fixture-
landlord-not-registered-land-owner` أعلاه؛ ورصيد مشتري اختباري صفري
كشفته إصلاح باج #16 سابق غير مرتبط]، ومفيش أي منهم بيبني
`SaaSControlService` أو يلمس `self.finance`). **ملاحظة جانبية اتكشفت
أثناء الإصلاح، خارج نطاقه، فُتح لها بند backlog جديد منفصل تحت
(`backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`).**
النطاق الأعمّ المذكور فوق (هل `FinanceService` نفسها تتبنى per-operation
API عبر كل استخدامتها في المشروع؟) **لسه قرار معماري منفصل مؤجَّل** —
لم يُتخذ اليوم، خارج نطاق الإصلاح الضيق المطلوب. تفاصيل كاملة:
`.claude/reports/financeservice-tenant-binding-fix-session-log.md`،
`tests/test_financeservice_tenant_binding_fix.py`.

## [2026-09-08] backlog-finance-router-hardcoded-tenant-id-1 — ✅ مُغلَق [2026-09-09]، مُتحقَّق منه حيًا

اكتُشف أثناء فحص read-only شامل (جرد كل نقاط إنشاء `FinanceService(...)`
عبر المشروع) لتوثيق حجم تأثير
`backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
أعلاه. `finance/router.py:121` بيبني الـservice بـ`tenant_id` مكتوب
صريح بدل قراءته من `current_user`:

```python
service = FinanceService(db, 1)   # سطر 121 — مقارنة بباقي الـ7 endpoints في نفس الملف
```

باقي الـ7 نقاط استدعاء في نفس الملف (29, 45, 75, 102, 135, 146, 158,
182) كلهم `FinanceService(db, cast(int, current_user.tenant_id))` —
السطر 121 هو الشاذ الوحيد. **مختلف عن مشكلة `SaaSControlService`
(instance ثابتة عبر عدة عمليات)** — هنا كل request بيبني instance
جديدة (دورة حياة request-scoped طبيعية)، لكن الـtenant المُستخدَم
مكتوب صريح `1` بدل تينانت المستخدم الفعلي الحالي — أي مستخدم من أي
تينانت غير `1` بيستدعي هذا الـendpoint هيتعامل مع بيانات تينانت `1`
بدل تينانته هو (أو العكس: عزل تينانت مكسور بالكامل لهذا الـendpoint
تحديدًا). **لم يُحدَّد بعد أي endpoint بالضبط (لم تُقرأ الدالة
المحيطة بعمق — خارج نطاق الفحص المخصص لـ`FinanceService` نفسها).**
صفر تعديل كود، صفر تحقق حي — يحتاج جلسة تشخيص مستقلة لتحديد الـendpoint
وتأكيد الأثر الفعلي (هل ده كود ميت/مش مربوط براوتر فعّال؟).

**المرجع:**
`.claude/reports/financeservice-tenant-binding-investigation-session-log.md`
§2 ("`finance/router.py` نفسه").

### تحديث الإغلاق [2026-09-09] — السبب الحقيقي كان غياب auth، مش الـtenant_id

سلسلة تحقيق read-only على 3 جلسات كشفت إن التشخيص الأصلي أعلاه ("عزل
تينانت مكسور") **غير دقيق**. الـendpoint المحدَّد فعليًا: `GET
/finance/admin/crypto-mode` (دالة `get_crypto_mode`، `finance/router.py:116-126`).

**الاكتشاف الحاسم:** `SystemStateRepository.get_state()`
(`repository.py:217-229`) **تينانت-أجنوستيك بالكامل** — بيرجع أحدث صف
من جدول `system_state` من غير أي فلترة بـ`tenant_id` على الإطلاق. الجدول
نفسه singleton عالمي (صف واحد فقط، `id=1`، مؤكَّد بـSELECT حي ضد الـDB
الفعلية). يعني الـ`1` المكتوب في `FinanceService(db, 1)` **مُهملة
وظيفيًا تمامًا** — أي رقم هيدّي نفس النتيجة بالظبط، فمفيش "عزل تينانت
مكسور" لأن مفيش عزل تينانت من الأساس على هذا المسار.

المشكلة الحقيقية اللي طلعت بدل كده: الدالة **كانت من غير أي auth
dependency خالص** — لا `current_user`، لا `get_current_active_user`
ولا `get_current_superuser` — يعني أي حد بيعرف الـURL يقدر يقرا
`crypto_mode` و`max_supply` بدون تسجيل دخول أصلًا. ده كمان تناقض مع
الـ`POST` المقابل لنفس الـresource (`set_crypto_mode`، سطر 129) اللي
بيتطلب `get_current_superuser` فعليًا.

**الإصلاح المُنفَّذ (ضيق جدًا، صفر لمس لـ`FinanceService(db, 1)`):**
إضافة `current_user: User = Depends(get_current_active_user)` (تسجيل
دخول عادي — البيانات المُرجَعة رقم تصميمي عام مش حساس كفاية لتبرير
`get_current_superuser`)، وتحديث التعليق فوق السطر ليوضّح صراحة إن الـ`1`
مُهملة وظيفيًا ولازم مراجعة الـauth level تاني لو حد وسّع الـresponse
مستقبلًا بحقول أحساس زي `total_supply`/`exchange_rates` (موجودين في
نفس جدول `SystemState` بس مش مُرجَعين حاليًا).

**تحقق حي (TestClient in-process + DB حقيقية، صفر mock):**
- بدون توكن → `401 {"detail":"Not authenticated"}` ✅
- مستخدم عادي مسجّل (`system_role=USER`, لا `SUPER_ADMIN`) → `200
  {"crypto_mode":"FULL_CRYPTO","max_supply":{...}}` ✅
- Regression: `tests/test_financeservice_tenant_binding_fix.py` — `2
  passed`، صفر كسر.

**المرجع:**
`.claude/reports/finance-router-hardcoded-tenant-investigation-session-log.md`،
`.claude/reports/finance-router-system-state-model-and-live-data-session-log.md`،
`.claude/reports/finance-router-crypto-mode-auth-fix-session-log.md`.

## [2026-09-08] ربط بباجات constructor-mismatch القديمة: commerce/tasks.py + تأكيد invoicing/router.py:330

اكتُشفا كملاحظتين جانبيتين أثناء نفس الجرد الشامل لكل نقاط إنشاء
`FinanceService(...)` (نفس الجلسة أعلاه) — **نفس عائلة الباج القديمة
`constructor-mismatch` (service constructors بمعاملات ناقصة)، صفر علاقة
بمشكلة تينانت-البايندنغ نفسها، مذكورين هنا فقط للأمانة والربط.**

**(أ) `invoicing/router.py:330` — `InvoicingService(db)` بمعامل واحد
بدل اتنين:** **موثَّق مسبقًا بالفعل** كبند backlog قائم بذاته —
`invoicing-process-overdue-invoices-missing-tenant-id-arg` [2026-08-29]
(الجدول أعلاه، قرب السطر الموصوف بـ`POST /invoicing/admin/process-overdue`،
تفاصيل كاملة في `.claude/reports/invoicing-21-metadata-collision-session-log.md`
§5). **صفر معلومة جديدة** — نفس السطر، نفس التوقيع الناقص، أعيد رصده
بالصدفة أثناء الـgrep الشامل لهذه الجلسة. لا داعي لبند backlog منفصل؛
هذا مجرد ربط/تأكيد إضافي للبند الموجود، موثَّق كاملًا في
`.claude/reports/financeservice-tenant-binding-investigation-session-log.md`
§3 (قسم "خارج النطاق لكن مُلاحَظ أثناء الفحص").

**(ب) `app/tasks/commerce.py` — `CommerceService(db)` بمعامل واحد بدل
اتنين، 5 مواضع (أسطر 71, 122, 165, 214, 254):** **لم يوجد بند backlog
سابق مخصَّص له** (بعد بحث في `PROGRESS_LOG.md` والأرشيف — الإشارة
الوحيدة الموجودة سابقًا لـ`commerce`/`tasks/commerce.py` هي ملاحظة
سياق تكامل عابرة في جلسة Phase 10 لـ`affiliate` [أرشيف ~1010-1020]،
مش بند backlog فعلي). `CommerceService.__init__` (`commerce/service.py:24`)
`def __init__(self, db: AsyncSession, tenant_id: int)` — `tenant_id`
إجباري بلا default، بينما كل الخمس مهام في `tasks/commerce.py`
(`distribute_commissions_task` وأخواتها) بتنادي `CommerceService(db)`
بمعامل واحد بس. **الأثر المتوقَّع (غير مؤكَّد حيًا):** `TypeError`
فوري وقت الإنشاء، قبل أي منطق دومين — نفس النمط بالحرف الموثَّق سابقًا
لـ`InvoicingService(db)`/`FinanceService(db)` في جلسة `constructor-mismatch`
الأصلية (`PROGRESS_LOG_ARCHIVE_2026-08-18.md:2989` وما حولها). **بند
backlog صغير جديد مقترَح:** `backlog-commerce-tasks-constructor-missing-tenant-id`
— 🔴 مفتوح، لم يبدأ فحص، يحتاج تأكيد هل الـ5 مهام دي مربوطة فعليًا
بـcelery beat schedule/استدعاء حي قبل تحديد الأولوية الحقيقية (نفس
منهجية بند `invoicing-process-overdue-invoices-missing-tenant-id-arg`
المذكور فوق). صفر تعديل كود، صفر تحقق حي في هذه الجلسة.

**المرجع:**
`.claude/reports/financeservice-tenant-binding-investigation-session-log.md`
§3 (قسم "خارج النطاق لكن مُلاحَظ أثناء الفحص").

**الحالة:** 🔴 مفتوح، لم يُصلَح.

## [2026-09-08] إصلاح ضيق: FinanceService tenant binding في SaaSControlService — النطاق الأصلي (الخيار ب من التقييم)

**تنفيذًا للخيار (ب)** من تقييم
`backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
(راجع `.claude/reports/financeservice-tenant-binding-investigation-session-log.md`
§4) — إصلاح محصور في `app/domains/saas/service.py` بس، صفر لمس على
`FinanceService` نفسها أو أي دومين تاني.

**التعديل:** حذف `self.finance = FinanceService(db, tenant_id)` الثابتة
من `__init__` (سطر 63). فحص الدالتين الوحيدتين اللي كانتا بتستخدماها:
`process_auto_renewals` (بتتعامل مع تينانتات متعددة — `sub.tenant_id`
لكل اشتراك، مختلف عن `self.tenant_id`) و`pay_invoice` (بتتعامل دايمًا
مع نفس تينانت الـinstance، `self.tenant_id`، لأن `get_invoice` بتفلتر
بيه أصلًا). الحل: بناء `FinanceService` محلية جديدة جوّه كل دالة —
`FinanceService(self.db, sub_tenant_id)` داخل حلقة `process_auto_renewals`
(تُبنى من جديد لكل اشتراك على حدة)، و`FinanceService(self.db,
self.tenant_id)` محليًا جوّه `pay_invoice`.

**الاختبار الحي — أول مرة نشوف الحلقة الكاملة شغّالة من طرف لطرف:**
كررت بالضبط نفس السيناريو اللي كان فشل قبل الإصلاح (اشتراكان تحت
تينانت 1، رخيص/باهظ، عبر `SaaSControlService(db, 0)` — نفس نمط
السنتينل الإداري الحقيقي في `saas_tasks.py`/`router.py:273`)، كـ
regression test حقيقي ضد DB حي (`tests/test_financeservice_tenant_binding_fix.py`،
صفر mock). **قبل الإصلاح:** الاثنان كانا بيفشلا بنفس
`NotFoundError("المستلم غير موجود")`. **بعد الإصلاح:** الرخيص →
`SUCCESS` فعلي (معاملة حقيقية + فاتورة `PENDING` حقيقية على القرص)،
الباهظ → `InsufficientBalanceError` → `PAST_DUE` فعلي (`grace_period_end_date`
مضروب +3 أيام)، مؤكَّدان الاثنان عبر جلسة DB مستقلة (`AsyncSessionLocal()`
جديدة). تفاصيل كاملة + ملاحظة تقنية جانبية (باج `missing-commit` مستقل
في فرع `except InsufficientBalanceError`، لم يُلمَس) في
`.claude/reports/financeservice-tenant-binding-fix-session-log.md` §3.

**Regression:** 3 ملفات اختبار بتستخدم `SaaSControlService` مباشرة —
`test_saas_cancel_subscription_silent_write.py` (2/2 ✅، `cancel_subscription`
لا تستخدم `self.finance` أصلًا)، `test_referral_affiliate_unified_system.py`
(6/6 ✅)، `test_saas_active_subscription.py` (2/4 — الفشلان الاتنان
مؤكَّدان **غير مرتبطين** بإصلاح اليوم عبر traceback كامل: مشاكل داخل
`realestate/service.py` نفسه — تعارض بيانات `landlord`/مالك الوحدة،
ورصيد مشتري اختباري صفري كشفته إصلاح باج #16 القديم غير المرتبط — كلا
الاختبارين بيمرا فقط عبر `can_access_service`، المؤكَّد إنها لا تلمس
`self.finance`/`FinanceService` إطلاقًا، و`realestate/service.py` كان
أصلًا معدَّل uncommitted من قبل بداية هذه الجلسة). تفاصيل التحليل
الكامل في `.claude/reports/financeservice-tenant-binding-fix-session-log.md`
§4.

**تحديث حالة البندين:**
- `backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
  (أعلاه) → **✅ اتحل** (داخل `SaaSControlService` تحديدًا — النطاق
  الفعلي الوحيد المؤكَّد لهذه المشكلة، راجع تقرير الفحص §3).
- `backlog-process-auto-renewals-task-tenant-zero-noop` (أعلاه) →
  **✅ اتحل بالكامل** — الاختبار الحي أثبت الحلقة الكاملة (اختيار
  الاشتراكات عبر كل التينانتات + تنفيذ العملية المالية الفعلي، SUCCESS
  حقيقي وPAST_DUE حقيقي) شغّالة من طرف لطرف لأول مرة.

**المرجع:** `.claude/reports/financeservice-tenant-binding-fix-session-log.md`
(كامل)، `tests/test_financeservice_tenant_binding_fix.py`.

## [2026-09-08] backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write — 🔴 أولوية عالية

اكتُشف كملاحظة جانبية أثناء الاختبار الحي لإصلاح
`backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
أعلاه (`.claude/reports/financeservice-tenant-binding-fix-session-log.md`
§3) — **صفر لمس، توثيق فقط**.

`POST /admin/trigger-renewals` (`saas/router.py:265-275`) بينادي
`service.trigger_renewals(tenant_id)` (`saas/service.py:617-620`) اللي
بدورها بتنادي `process_auto_renewals(target)` — **بلا أي `db.commit()`
بعد الاستدعاء** (`get_db()` مفيهاش commit تلقائي، `router.py` نفسه
مفيهوش أي `await db.commit()` صريح). فرع `except InsufficientBalanceError`
جوّه `process_auto_renewals` (`service.py`، سطر ~319-327) بيعمل
`repo.update_subscription(..., status="PAST_DUE", ...)` عبر `flush()`
بس (`SaaSRepository.update_subscription`، بلا `commit()` مستقل) — نفس
نمط "الكتابة الصامتة" (`silent-write`) الموثَّق سابقًا ومتكرر في المشروع
(زي `saas-cancel-subscription-silent-write-fix` القديم، وبند
`process_auto_renewals` نفسه فرع #4 في الجدول أعلى الملف).

**عكس ذلك تمامًا:** `process_auto_renewals_task` (الـcelery task
اليومي، `saas_tasks.py:69-75`) عندها `await db.commit()` **صريح مباشرة
بعد** استدعاء `service.process_auto_renewals(tenant_id=None)` — فأي
تحويل `PAST_DUE` عبر المسار التلقائي اليومي بيتحفظ فعليًا (مؤكَّد حيًا
في جلسة اليوم، راجع تحديث `backlog-process-auto-renewals-task-tenant-
zero-noop` فوق).

**الأثر المتوقَّع (غير مؤكَّد حيًا بعد لهذا الـendpoint تحديدًا — الاختبار
الحي اليوم استخدم مسار الخدمة المباشر + `commit()` يدوي يحاكي التاسك،
مش الـHTTP endpoint نفسه):** أي استدعاء إداري حقيقي لـ`POST
/admin/trigger-renewals` (بتينانت محدد أو بلا تحديد) لاشتراك هيفشل
تجديده بـ`InsufficientBalanceError`، الكود بيحوّل حالته لـ`PAST_DUE`
في الذاكرة (ويرجّع `{"status": "PAST_DUE"}` في الـresponse كنجاح
ظاهري)، **لكن الكتابة بتتفقد صامتة عند إغلاق الـsession** (`get_db()`
بترولباك أي ترانزاكشن معلَّقة بلا commit) — الاشتراك بيفضل فعليًا
بحالته القديمة (`ACTIVE`) على القرص، بلا `grace_period_end_date`،
رغم رد الـHTTP الناجح الكاذب.

**غير محتاج تحقق حي منفصل لإثبات النمط نفسه** — نفس الآلية بالحرف
(`flush()`-only + غياب `commit()` محيط) موثَّقة ومؤكَّدة حيًا مسبقًا
لمرات عديدة في المشروع (`saas-cancel-subscription-silent-write-fix`،
وغيرها) — لكن **التحقق الحي المحدد لهذا الـendpoint نفسه (`POST
/admin/trigger-renewals` عبر HTTP فعلي) لم يحصل بعد.**

**الإصلاح المقترَح (لم يُنفَّذ، خارج نطاق جلسة اليوم):** إضافة `await
db.commit()` في `router.py` بعد `await service.trigger_renewals(tenant_id)`
مباشرة — أبسط حل، نفس نمط `process_auto_renewals_task`. البديل الأعمّ
(نقل `commit()` جوّه `process_auto_renewals`/`trigger_renewals` نفسها
بدل الاعتماد على المستدعي) يحتاج مراجعة كل نقاط الاستدعاء التانية
(الـcelery task) عشان مايتكررش commit مزدوج — قرار تصميم بسيط لكن
يحتاج جلسة منفصلة.

**المرجع:** `.claude/reports/financeservice-tenant-binding-fix-session-log.md`
§3.

**الحالة:** 🔴 مفتوح، أولوية عالية — صفر تحقق حي، صفر إصلاح.

---

## [2026-09-08] تحديث backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write — ✅ اتحل

**جلسة 1 (تحقق حي، صفر تعديل كود):** استُدعيت دالة الراوتر
`trigger_renewals` فعليًا (نفس الكائن المسجَّل تحت `POST
/admin/trigger-renewals`) بجلسة `AsyncSessionLocal()` تُفتح وتُغلق بنفس
نمط `get_db()` الحقيقي بالضبط (بلا commit إضافي) — سيناريو اشتراك باهظ
واحد → `InsufficientBalanceError` → PAST_DUE. **الباج تأكَّد حيًا لأول
مرة**: رد الـAPI رجّع `PAST_DUE`، لكن الاشتراك في الـDB (جلسة مستقلة بعد
إغلاق جلسة الطلب) فضل `status="ACTIVE"` و`grace_period_end_date=None`.
فُحصت كمان الفروع التلاتة في `process_auto_renewals` بدقة: SUCCESS آمن
تمامًا (`self.db.commit()` خاص بيه، `service.py:314`، مستقل عن أي
commit خارجي)، FAILED صفر كتابة DB، فرع PAST_DUE هو **الوحيد** المعتمِد
على commit خارجي غائب. المرجع الكامل:
`.claude/reports/trigger-renewals-missing-commit-investigation-session-log.md`.

**جلسة 2 (إصلاح ضيق):** أُضيف `await self.db.commit()` داخل
`SaaSControlService.trigger_renewals` (`saas/service.py:618-622`) بس —
مباشرة بعد `results = await self.process_auto_renewals(target)` وقبل
الـ`return`، نفس نمط `saas_tasks.py:75` تمامًا:

```python
async def trigger_renewals(self, tenant_id: Optional[int] = None):
    target = tenant_id if tenant_id is not None else self.tenant_id
    results = await self.process_auto_renewals(target)
    await self.db.commit()
    return results
```

**صفر لمس على `router.py` أو `process_auto_renewals` نفسها.** تحقق حي
بعد الإصلاح (نفس الاشتراك الباهظ، نفس منهجية الاستدعاء): رد الـAPI
`PAST_DUE`، والاشتراك في الـDB أصبح فعليًا `status="PAST_DUE"` بـ
`grace_period_end_date` مضروب — تطابق كامل. اختبار SUCCESS إضافي عبر
نفس المسار (اشتراك رخيص) أكّد إن `self.db.commit()` الإضافي بعد commit
داخلي سابق (فرع SUCCESS، سطر 314) **لا يسبب أي خطأ "double commit"** —
commit على session بلا ترانزاكشن معلَّقة no-op آمن في SQLAlchemy.
4 اختبارات مرّت (`test_trigger_renewals_endpoint_missing_commit.py`
اتنين + `test_financeservice_tenant_binding_fix.py` اتنين كـregression،
صفر تأثر). المرجع الكامل:
`.claude/reports/trigger-renewals-missing-commit-fix-session-log.md`.

**الحالة النهائية:** ✅ اتحل بالكامل ومؤكَّد حيًا (الملاحظة القديمة فوق
تفضل كما هي — سجل تراكمي — لكنها متجاوَزة بهذا التحديث).

---

## [2026-09-08] تحديث backlog-notification-delivery-stub-empty-non-inapp-channels — 🟡 قرار مُتَّخذ

**النطاق:** توثيق فقط — صفر تغيير وظيفي، منطق الـstubs نفسه لم يتغيّر
حرفًا واحدًا.

أُضيف تعليق بارز فوق تعريف `send_notification_task` في المكانين
(`app/core/celery_app.py:67`، `app/domains/communications/tasks.py:10`)
يوضّح إن القنوات EMAIL/SMS/PUSH غير مُفعَّلة حاليًا وإن IN_APP هي
القناة الوحيدة المدعومة فعليًا، مع إشارة صريحة لهذا البند.

**grep شامل عن كل نقطة استدعاء فعلية لـ`CommunicationsService.send_notification(...)`
في المشروع (`.send_notification(` عبر `app/domains/`)** — 5 نقاط
استدعاء فعلية بس، **كلها بتستخدم `IN_APP` بالفعل** (صراحة أو عبر
القيمة الافتراضية لتوقيع الدالة نفسها):

| الملف:السطر | القناة الفعلية |
|---|---|
| `app/domains/transport/service.py:875` (عبر `_send_notification` helper) | `channel="IN_APP"` صراحة |
| `app/domains/realestate/service.py:729` (عبر `_send_notification` helper) | `channel="IN_APP"` صراحة |
| `app/domains/automation/service.py:553` | استدعاء بمعاملات موضعية بلا `channel` — يقع على القيمة الافتراضية `NotificationChannel.IN_APP` في توقيع `send_notification` (`communications/service.py:49`) |
| `app/domains/saas/service.py:396` | `channel="IN_APP"` صراحة |
| `app/domains/communications/router.py:105` | `channel="IN_APP"` صراحة (مُثبَّتة صراحة في جسم الراوتر — مش من الطلب) |

**صفر نقطة في المشروع كله بتحاول تمرر `EMAIL`/`SMS`/`PUSH` فعليًا** —
تأكَّد ببحث إضافي عن `channel="EMAIL"/"SMS"/"PUSH"` و
`NotificationChannel.EMAIL/SMS/PUSH` في كل الباك إند: التطابق الوحيد
كان `communication_templates.channel` (`communications/models.py:164`،
`default=NotificationChannel.EMAIL`) — عمود schema افتراضي لجدول
قوالب البريد، **مش استدعاء فعلي لـ`send_notification`**، خارج نطاق
هذا الفحص تمامًا.

**بما إن صفر نقطة فعلية بتحاول تستخدم قناة معطَّلة، القرار الثنائي
المطروح أصلًا (تغييرها لـIN_APP دلوقتي / تركها كـbacklog منفصل) أصبح
غير ذي موضوع — لا يوجد استدعاء يحتاج تغيير.**

**الحالة الجديدة:** 🟡 قرار مُتَّخذ — IN_APP هي القناة الرسمية الوحيدة
حاليًا، موثَّقة في الكود (تعليقات واضحة). التكامل الحقيقي
(SMTP/FCM/Twilio) مؤجَّل لحد ما تتوفر حسابات/مفاتيح فعلية من الفريق —
ليس قرارًا تقنيًا معلَّقًا، بل يعتمد على بنية تحتية خارجية غير متاحة
حاليًا.

**المرجع:**
`.claude/reports/notification-channels-inapp-only-decision-documentation-session-log.md`.

## [2026-09-08] backlog-saas-tasks-calling-nonexistent-methods — تحديث: `check_expired_trials_task` اتحل بالكامل

متابعة لبند `backlog-saas-tasks-calling-nonexistent-methods` أعلاه
(البند القديم **لم يُعدَّل** — راجعه للسياق الكامل الأصلي). واحدة من
الأربعة المذكورة فيه، `check_expired_trials_task`، اتصلحت بالكامل
النهارده في جلسة منفصلة، عبر بَجين كانا متراكبين فوق بعض:

1. **`SaaSControlService(db)` بلا `tenant_id`** (نفس بَج
   `backlog-process-auto-renewals-task-constructor-typeerror`) — اتصلح
   بتغيير الاستدعاء في `app/tasks/saas_tasks.py` (`check_expired_trials_task`)
   لـ`SaaSControlService(db, 0)`، بنفس نمط
   `process_auto_renewals_task`/`check_past_due_subscriptions_task`.
2. **دالة `check_and_expire_trials` غير موجودة أصلًا** — اتبنت من
   الصفر على `SaaSControlService` (`app/domains/saas/service.py`)، بنفس
   بنية `check_past_due_subscriptions` (المبنية النهارده كمان):
   - `SaaSRepository.get_trial_subscriptions` (`repository.py`) اتوسَّعت
     لتقبل `tenant_id: Optional[int] = None` (بلا فلتر = كل
     المستأجرين، بنفس نمط `get_past_due_subscriptions`) + باراميتر
     جديد `expired_only: bool = False` بيضيف فلتر فعلي
     `trial_end_date <= now()`. **قرار تصميم مهم:** الفلتر الزمني
     اتحط خلف باراميتر اختياري افتراضيه `False`، **مش تعديل مباشر
     للسلوك الافتراضي** — عشان المستدعي الوحيد الموجود مسبقًا
     (`AcademyService._cancel_related_free_trials`،
     `academy/service.py:479-484`) محتاج فعليًا **كل** اشتراكات TRIAL
     للتينانت بغض النظر عن تاريخ الانتهاء (بيلغيها كلها عند إلغاء
     enrollment مرتبط)، مش بس المنتهية زمنيًا — تعديل الفلتر الافتراضي
     كان هيكسر هذا الاستدعاء الموجود بصمت.
   - `check_and_expire_trials(tenant_id: Optional[int] = None) -> int`
     دالة جديدة: تجيب `get_trial_subscriptions(tenant_id,
     expired_only=True)`، تحوّل كل واحد لـ`EXPIRED` عبر
     `update_subscription_status` الموجودة، `try/except` حول كل
     اشتراك على حدة (فشل واحد ما يوقفش الباقي)، وترجع `int` (عدد
     الاشتراكات اللي اتحوّلت فعليًا).

**اختبار حي فعلي (مش mocked):** زُرع اشتراكان `TRIAL` مباشرة عبر SQL
(`tenant_id=1`, `plan_id=48`) — id=158 بـ`trial_end_date` في الماضي
(قبل يومين)، id=159 بـ`trial_end_date` في المستقبل (بعد 10 أيام).
تشغيل `check_expired_trials_task.run()` فعليًا (بعد `import app.main`
لتسجيل كل الـmappers، بنفس منهجية الجلسة السابقة) رجع
`{'status': 'success', 'expired_count': 1, ...}`. تحقُّق مستقل عبر
`SELECT` مباشر بعد التشغيل: **id=158 → `EXPIRED`** (`updated_at`
اتغيّر)، **id=159 → لسه `TRIAL`** (بلا أي تغيير) — بالظبط النتيجتان
المتوقَّعتان. الصفان اتحذفا بعدها (`DELETE ... WHERE id IN (158,159)`)
لإرجاع القاعدة لحالتها الأصلية (23 `ACTIVE` + 1 `CANCELLED`، صفر
`TRIAL`، مطابق تمامًا لما كان قبل الزرع).

**Regression:** كل الاختبارات الموجودة اللي بتلمس
`SaaSControlService`/`get_trial_subscriptions`
(`test_trigger_renewals_endpoint_missing_commit.py`,
`test_financeservice_tenant_binding_fix.py`,
`test_referral_affiliate_unified_system.py`,
`test_saas_cancel_subscription_silent_write.py`,
`test_saas_active_subscription.py`) — **14 نجحوا، فشلان اثنان
موجودان مسبقًا وموثَّقان بالفعل** (`test_realestate_rent_unit_saas_check_passes`
و`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
— راجع الإدخالين بتاريخ [2026-09-08] أعلاه اللي بيوثقوا هذين الفشلين
كمشكلة fixture/بَج معروف منفصل تمامًا في دومين `realestate`، غير
مرتبط بـSaaS trial expiry). **صفر رجوع (regression) ناتج عن هذا
التعديل.**

**الحالة المحدَّثة للأربعة الأصليين:**
- ✅ `check_expired_trials_task` / `check_and_expire_trials` —
  **اتحل بالكامل واتأكد حيًا** (هذا الإدخال).
- 🔴 `generate_monthly_invoices_task` / `generate_monthly_invoices` —
  **لسه مفتوح** (مجدولة فعليًا، أول كل شهر 3ص — لسه هتفشل).
- 🔴 `send_trial_expiry_reminders_task` / `send_trial_expiry_reminders`
  — **لسه مفتوح** (غير مجدولة حاليًا).
- 🔴 `cleanup_cancelled_subscriptions_task` / `cleanup_cancelled_subscriptions`
  — **لسه مفتوح** (غير مجدولة حاليًا، ويحتاج قرار نطاق صريح
  PDPL/GDPR قبل أي بناء — راجع
  `.claude/reports/saas-nonexistent-methods-investigation-session-log.md`
  §4).

**المرجع:** `.claude/reports/check-expired-trials-task-fix-session-log.md`.

---

## [2026-09-09] backlog-saas-tasks-calling-nonexistent-methods — تحديث: `generate_monthly_invoices_task` اتحل بالكامل

متابعة لبند `backlog-saas-tasks-calling-nonexistent-methods` أعلاه
(البند القديم **لم يُعدَّل**). ثانية من الأربعة، `generate_monthly_invoices_task`،
اتصلحت بالكامل، عبر نفس فئتي البَج المتراكبين:

1. **`SaaSControlService(db)` بلا `tenant_id`** — اتصلح لـ
   `SaaSControlService(db, 0)`، نفس نمط التلاتة المُصلَحين قبلها.
2. **دالة `generate_monthly_invoices` غير موجودة أصلًا** — اتبنت من
   الصفر على `SaaSControlService`:
   - `SaaSRepository.get_subscriptions_for_manual_billing`
     (`repository.py`) — استعلام جديد: `status="ACTIVE"`,
     `auto_renew=False`, `next_billing_date <= now()`. **بنفس معيار
     الاستحقاق بالضبط** في `get_subscriptions_for_renewal` الموجودة،
     لكن بفلتر `auto_renew=False` بدل `True` — دالة منفصلة تمامًا
     (مش توسيع لـ`get_subscriptions_for_renewal` بباراميتر)، لأن الاسم
     والمعنى مختلفان جوهريًا (تجديد تلقائي مقابل فوترة يدوية). بلا
     فلتر `tenant_id` افتراضيًا (عبر كل المستأجرين).
   - `generate_monthly_invoices(tenant_id: Optional[int] = None) -> int`
     دالة جديدة: تخص حصريًا الاشتراكات ACTIVE بـ`auto_renew=False`
     (عملاء الدفع اليدوي — بعكس `process_auto_renewals` اللي تخص
     `auto_renew=True`، **صفر تداخل/تكرار بين الاثنين**، مؤكَّد حيًا
     تحت). لكل اشتراك مستحق: تستدعي `_generate_invoice` الموجودة
     أصلًا (idempotent عبر `idempotency_key`، نفس الدالة المُستخدَمة
     جوّه `process_auto_renewals`) **بلا أي استدعاء لـ`FinanceService`/
     `transfer` وبلا أي خصم فوري من المحفظة** — الفرق الجوهري عن
     `process_auto_renewals`؛ الدفع الفعلي بيحصل لاحقًا عبر
     `pay_invoice` الموجودة. بعد الإصدار، `next_billing_date` بيتحدّث
     +30 يوم (نفس منطق `process_auto_renewals` بالضبط) عشان الفاتورة
     الجاية متتصدرش تاني الشهر ده. `try/except` حول كل اشتراك على حدة،
     وترجع `int` (عدد الفواتير المُصدرة فعليًا).

**اختبار حي فعلي (مش mocked):** زُرع اشتراكان `ACTIVE` مباشرة عبر SQL
(`tenant_id=1`, `plan_id=48`, كلاهما `next_billing_date` في الماضي
بساعة) — id=163 بـ`auto_renew=false` (الهدف)، id=164 بـ`auto_renew=true`
(كنترول، لإثبات عدم التأثر/عدم التكرار مع `process_auto_renewals`).
تشغيل `generate_monthly_invoices_task.run()` فعليًا (بعد `import
app.main`، بنفس منهجية الجلسات السابقة) رجع `{'status': 'success',
'issued_count': 1, ...}`. تحقُّق مستقل عبر `SELECT` مباشر بعد التشغيل:
**id=163** → فاتورة `PENDING` حقيقية اتصدرت (`INV-6EEA4EADE936`،
`amount=0.00000000` مطابق لسعر الخطة)، `next_billing_date` اتحدّث
لـ+30 يوم فعليًا (`2026-10-08`)، **id=164** → **بلا أي تغيير إطلاقًا**
(`next_billing_date`/`updated_at` زي وقت الزرع بالظبط — لم يُلمَس،
إثبات حي إن الفلترة صح ومفيش تداخل مع `process_auto_renewals`).
تأكيد إضافي: صفر صف جديد في جدول `transactions` (بحث `WHERE
created_at > now() - interval '10 minutes'` رجع `0`) — **صفر خصم من
أي محفظة**، الفرق الجوهري عن `process_auto_renewals` مؤكَّد حيًا لا
نظريًا فقط. **اختبار idempotency إضافي:** إعادة تشغيل
`generate_monthly_invoices_task.run()` فورًا بعد كده رجعت
`issued_count: 0` — id=163 مبقاش مرشَّحًا (next_billing_date اتحرك
للمستقبل)، صفر فاتورة مكررة. الصفان اتحذفا بعدها (`DELETE FROM
saas_invoices WHERE subscription_id IN (163,164); DELETE FROM
saas_tenant_subscriptions WHERE id IN (163,164)`) لإرجاع القاعدة
لحالتها الأصلية (تحقُّق `GROUP BY status, auto_renew` بعد الحذف طابق
تمامًا الحالة قبل الزرع).

**Regression:** نفس الخمسة اختبارات اللي بتلمس
`SaaSControlService`/`get_subscriptions_for_renewal` — **14 نجحوا،
نفس الفشلان الاثنان الموجودان مسبقًا** (`test_realestate_rent_unit_saas_check_passes`
و`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
— بَج fixture/`realestate` معروف ومنفصل تمامًا، موثَّق مسبقًا). **صفر
رجوع (regression) ناتج عن هذا التعديل.**

**الحالة المحدَّثة للأربعة الأصليين:**
- ✅ `check_expired_trials_task` / `check_and_expire_trials` — اتحل
  بالكامل واتأكد حيًا [2026-09-08].
- ✅ `generate_monthly_invoices_task` / `generate_monthly_invoices` —
  **اتحل بالكامل واتأكد حيًا** (هذا الإدخال).
- 🔴 `send_trial_expiry_reminders_task` / `send_trial_expiry_reminders`
  — **لسه مفتوح** (غير مجدولة حاليًا).
- 🔴 `cleanup_cancelled_subscriptions_task` / `cleanup_cancelled_subscriptions`
  — **لسه مفتوح** (غير مجدولة حاليًا، ويحتاج قرار نطاق صريح
  PDPL/GDPR قبل أي بناء — راجع
  `.claude/reports/saas-nonexistent-methods-investigation-session-log.md`
  §4).

**المرجع:** `.claude/reports/generate-monthly-invoices-task-fix-session-log.md`.

## [2026-09-09] backlog-saas-tasks-calling-nonexistent-methods — تحديث: `send_trial_expiry_reminders_task` اتحل بالكامل

**النطاق:** بناء + إصلاح `send_trial_expiry_reminders_task` بالكامل — تالت
واحدة من الأربعة المذكورين في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`،
بنفس منهجية `check_expired_trials_task` [2026-09-08] و
`generate_monthly_invoices_task` [2026-09-09] بالضبط.

**أ) الـconstructor:** نفس بَج `SaaSControlService(db)` بلا `tenant_id`
(`TypeError` مؤكَّد نظريًا، نفس النمط في التلاتة التانيين) — اتصلح لـ
`SaaSControlService(db, 0)` (سنتينل إداري، نفس نمط
`check_past_due_subscriptions_task`).

**ب) الدالة المفقودة:** `send_trial_expiry_reminders` مضافة في
`app/domains/saas/service.py` (بعد `check_and_expire_trials` مباشرة)،
بنفس بنية `check_past_due_subscriptions` تمامًا — بتستخدم
`get_trial_subscriptions(tenant_id, expired_only=False)` الموجودة
بالفعل (من جلسة `check_expired_trials_task`)، مع فلتر إضافي محلي:
`now <= trial_end_date <= now + يومين` (نافذة تذكير "باقي يومين").
لكل اشتراك مطابق: `CommunicationsService.send_notification(channel=
"IN_APP", idempotency_key=f"SUB-TRIAL-REMIND-{sub_id}", ...)` —
`try/except` حول كل اشتراك على حدة، بترجع `int` (عدد التذكيرات
اللي اتبعتت فعليًا) مباشرة، مطابق لتوقع `saas_tasks.py`
(`# type: ignore[attr-defined]` اتشال). **قناة `EMAIL` لم تُستخدَم
إطلاقًا** — الـstub الفاضي موثَّق في backlog منفصل
(`backlog-notification-delivery-stub-empty-non-inapp-channels`)، ودوكستring
المهمة نفسها في `saas_tasks.py` اتعدّل عشان يوضّح كده صراحة (كانت
بتقول "إشعارات In-App وبريد إلكتروني" بالغلط).

**ج) اختبار حي فعلي — بيانات مزروعة + تشغيلتان منفصلتان (idempotency) +
تحقق مستقل:**

زرع 3 اشتراكات `TRIAL` تحت تينانت1 (`plan_id=48`، نفس النمط المرجعي
من جلسة `check_expired_trials_task`): `id=173` (`trial_end_date` =
الآن+1.5 يوم، لازم يتبعتله تذكير)، `id=174` (الآن+7 أيام، لازم ما
يتبعتلوش)، `id=175` (الآن+1.5 يوم برضو، لاختبار idempotency). قبل
الزرع: صفر `TRIAL` في القاعدة — عزل تام.

**تشغيلة 1** (`send_trial_expiry_reminders_task.run()`، سكريبت Python
منفصل بعد `import app.main`) رجعت `{'status': 'success',
'reminders_sent': 2, ...}` — لوج: `Trial expiry reminder sent:
subscription 173` و`175` (مش `174`، مطابق تمامًا للتوقع). **تشغيلة 2**
(عملية Python منفصلة تمامًا — استدعاء `.run()` مرتين في نفس العملية
بيرمي `AttributeError` بسبب تسريب event loop مغلق من `_run_async`،
نفس الملاحظة التقنية الموثَّقة في جلسة `past-due-grace-period-
notifications-implementation-session-log.md` §"ملاحظة تقنية عن
سكريبت الاختبار") رجعت بردو `reminders_sent: 2` (متوقَّع — الكود
بيعتبر أي `send_notification` ناجح "مُرسَل" بصرف النظر عن كونه idempotent
duplicate، بنفس فلسفة `check_past_due_subscriptions`؛ الدليل الحاسم
على الـidempotency الفعلية هو صفوف جدول `notifications` مش الرقم
المرجَع من الـtask).

**تحقق مستقل على القرص بعد التشغيلتين:**
```
SELECT id, user_id, idempotency_key, title, channel, created_at
FROM notifications WHERE idempotency_key LIKE 'SUB-TRIAL-REMIND-%';

 id | user_id |   idempotency_key    | channel |          created_at
----+---------+----------------------+---------+-------------------------------
 30 |       1 | SUB-TRIAL-REMIND-173 | IN_APP  | 2026-09-08 21:27:33 (تشغيلة 1)
 31 |       1 | SUB-TRIAL-REMIND-175 | IN_APP  | 2026-09-08 21:27:38 (تشغيلة 1)
```
**صفان بالظبط** رغم التشغيلتين — التشغيلة التانية (الساعة 21:29) صفر
صف جديد. صفر `SUB-TRIAL-REMIND-174` — التذكير اتبعت للاشتراكين
المستهدَفين بس. حالة الاشتراكات التلاتة بعد التشغيلتين: **`TRIAL`
بلا أي تغيير** (الدالة دي بترسل تذكيرات بس، ما بتلمسش `status` —
بعكس `check_and_expire_trials`). التنظيف: `DELETE FROM notifications
WHERE idempotency_key LIKE 'SUB-TRIAL-REMIND-%'` +
`DELETE FROM saas_tenant_subscriptions WHERE id IN (173,174,175)` —
تحقُّق بعدي: صفر `TRIAL` في القاعدة، صفر صف `SUB-TRIAL-REMIND-%`
متبقٍّ.

**Regression:** نفس الخمسة اختبارات اللي بتلمس
`SaaSControlService`/`get_trial_subscriptions` — **14 نجحوا، نفس
الفشلان الاثنان الموجودان مسبقًا** (`test_realestate_rent_unit_saas_check_passes`
و`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
— بَج fixture/`realestate` معروف ومنفصل تمامًا، موثَّق مسبقًا). **صفر
رجوع (regression) ناتج عن هذا التعديل.**

**الحالة المحدَّثة للأربعة الأصليين:**
- ✅ `check_expired_trials_task` / `check_and_expire_trials` — اتحل
  بالكامل واتأكد حيًا [2026-09-08].
- ✅ `generate_monthly_invoices_task` / `generate_monthly_invoices` —
  اتحل بالكامل واتأكد حيًا [2026-09-09].
- ✅ `send_trial_expiry_reminders_task` / `send_trial_expiry_reminders`
  — **اتحل بالكامل واتأكد حيًا** (هذا الإدخال).
- 🔴 `cleanup_cancelled_subscriptions_task` / `cleanup_cancelled_subscriptions`
  — **لسه مفتوح** (غير مجدولة حاليًا، ويحتاج قرار نطاق صريح
  PDPL/GDPR قبل أي بناء — راجع
  `.claude/reports/saas-nonexistent-methods-investigation-session-log.md`
  §4).

**المرجع:** `.claude/reports/send-trial-expiry-reminders-task-fix-session-log.md`.

## [2026-09-16] entertainment-venue-endpoint-implementation — ✅ endpoint إنشاء EntertainmentVenue الجديد مبني بالكامل ومُتحقَّق منه حيًا (3/3 اختبارات)، بما فيها migration 055 جديد

بناءً على فحص read-only سابق
(`.claude/reports/entertainment-venue-endpoint-planning-session-log.md`)
اللي أكَّد إن `EntertainmentVenue` عندها repository method (`create_venue`)
و`schemas` (`VenueCreate`/`VenueResponse`) جاهزين من قبل ويتيمين تمامًا —
بلا `service` method ولا `router` endpoint يستخدمهم. اتبنى الجزء المفقود
كامل، بنفس نمط `create_sports_org` بالحرف
([[project_tourism_sports_entity_membership_implementation_closed]]):

- **migration 055** (`055_entertainment_venues_entity_id_fk_set_null.py`):
  إضافة `ForeignKey("sovereign_entities_v2.id", ondelete="SET NULL")` على
  `entertainment_venues.entity_id` (كان عمود `Integer` شكلي بلا أي FK
  إطلاقًا). اتأكَّد مباشرة عبر `asyncpg` قبل الكتابة: 4 صفوف حاليًا،
  صفر منها `entity_id` غير NULL — صفر خطر backfill. اتطبَّقت على DB
  الديف واتأكَّد `confdeltype='n'` (SET NULL) عبر `pg_constraint` بعدها.
- **`models.py`**: تحديث `EntertainmentVenue.entity_id` ليطابق الـFK
  الجديد.
- **`schemas.py`**: إضافة `entity_id: int` لـ`VenueCreate` (كانت مفقودة
  تمامًا، بخلاف `SportsOrgCreate` اللي عندها الحقل ده بالفعل).
- **`service.py`**: `create_venue` جديدة تحت قسم "3. الترفيه" — فحص
  عضوية عبر `self.membership.get_member(entity_type=ENTITY_TYPE,
  entity_id=data["entity_id"], user_id=user_id)`، رفض لو مش
  `OWNER`/`EXECUTIVE_DIRECTOR` بـ`PermissionDeniedError` (→403)،
  `_check_saas_limits(tenant_id, "entertainment")` (نفس مفتاح
  `create_event`)، ثم `repo.create_venue(...)` الموجودة من قبل.
- **`router.py`**: `POST /tourism-sports/venues` (مسطّح، بدون
  `/entertainment/` sub-prefix — مطابق لباقي مسارات قسم الترفيه)،
  `response_model=VenueResponse`, `status_code=201`,
  `Depends(get_current_active_user)` (مش superuser — التفويض عبر عضوية
  الكيان، تمامًا زي `create_sports_org`).

**الاختبار الحي** (`tests/test_entertainment_venue_entity_membership_full_implementation.py`,
3 سيناريوهات، نفس شكل ملف tourism_sports/sports_org بالضبط): (1) عضو
OWNER ينجح + غير عضو يترفض بـ`PermissionDeniedError` — **PASSED**؛ (2)
`EXECUTIVE_DIRECTOR` أيضًا مسموح — **PASSED**؛ (3) حذف الكيان المُصدِر
→ `entity_id` بيرجع NULL والمكان يفضل موجود (SET NULL مش CASCADE) —
**PASSED**. **3/3 نجحوا.**

**Regression check:** كل tourism_sports/entertainment_venue tests
(19 اختبار عبر 4 ملفات) — 18 نجحوا، فشل واحد **مسبق وغير مرتبط**
(`test_tourism_sports_register_affiliate_commission_get_by_id_fixed` في
`tests/test_user_repository_get_by_id_audit.py` — عن `_register_affiliate_commission`
وموضوع `referred_by` في audit log، صفر علاقة بـ`EntertainmentVenue` أو
أي ملف اتلمس في هذه الجلسة؛ لم يُعدَّل أي ملف من الملفين). لم يُصلَح —
خارج نطاق هذه الجلسة.

**الحالة النهائية:** endpoint إنشاء `EntertainmentVenue` مبني بالكامل
ومتحقَّق منه حيًا، صفر تعديل على الملف الفاشل مسبقًا. لم يُعمَل commit
بعد — بانتظار طلب المستخدم.

**المرجع الكامل:**
`.claude/reports/entertainment-venue-endpoint-implementation-session-log.md`.

## [2026-09-16] guardian-relationship-foundation-implementation — ✅ الأساس فقط (migration 056 + دومين app/domains/guardian/ جديد بالكامل)، صفر endpoint/service/منطق تدفق بعد

بناءً على جلستي التخطيط read-only السابقتين
([[project_guardian_relationship_design_planning]] و
[[project_birth_date_null_percentage_check]])، اتبنى **الأساس البنيوي
فقط** لعلاقة ولي أمر↔طالب — جدولان جديدان + دومين جديد كامل، بلا أي
endpoint أو service أو منطق طلب/موافقة/تحقق إداري فعلي (المرحلة القادمة):

- **migration 056** (`056_create_guardian_relationship_tables.py`):
  جدولان جدد بالكامل، صفر لمس على أي جدول قائم.
  - `guardian_relationships`: `guardian_user_id`/`ward_user_id` (FK
    `users.id`, `ON DELETE CASCADE`)، `relationship_type`
    (enum `FATHER/MOTHER/GUARDIAN`)، `status` (enum
    `PENDING_WARD_APPROVAL/PENDING_ADMIN_REVIEW/VERIFIED/REJECTED`،
    افتراضي `PENDING_WARD_APPROVAL`)، `initiated_by_user_id`،
    `ward_birth_date_provided` (Date, nullable — منفصل عمدًا عن
    `users.birth_date` القديمة الناقصة 99.16%)، `verified_by`/
    `verified_at`/`rejection_reason` (نفس شكل `kyb_status` في
    `sovereign_entities`)، قيد فريد `uq_guardian_ward` على
    `(guardian_user_id, ward_user_id)`.
  - `guardian_visibility_settings`: `guardian_relationship_id` (FK
    `ON DELETE CASCADE`)، `sector` (enum
    `ACADEMY/SOCIAL/TRANSPORT/HEALTH`)، `is_visible` (افتراضي `True`)،
    قيد فريد `uq_guardian_visibility_relationship_sector` على
    `(guardian_relationship_id, sector)`.
  - اتطبَّقت فعليًا على DB الديف (`alembic upgrade head`، من 055 لـ056)
    واتأكَّد الشكل الكامل (أعمدة، فهارس، FKs، قيود فريدة) مباشرة عبر
    `psql \d`.
- **`app/domains/guardian/`** (دومين جديد، __init__.py فارغ زي باقي
  الدومينات): `models.py` (الموديلين + 3 enums)، `schemas.py`
  (`GuardianRelationshipCreate/Response`,
  `GuardianVisibilitySettingCreate/Response`)، `repository.py`
  (`GuardianRepository`: `create_relationship`, `get_relationship`,
  `get_relationship_by_guardian_and_ward`, `create_visibility_setting`,
  `list_visibility_settings` — كل الدوال المطلوبة للاختبار الحي بس،
  صفر منطق فوق CRUD). **لا `service.py` ولا `router.py`** — بالضبط زي
  المطلوب، صفر تسجيل في `main.py`.

**الاختبار الحي** (`tests/test_guardian_relationship_foundation_implementation.py`,
3 سيناريوهات، عبر `GuardianRepository` مباشرة بلا أي service/endpoint):
(1) إنشاء علاقة + 4 صفوف رؤية (كل قطاعات `GuardianVisibilitySector`)،
تأكيد الحالة الافتراضية `PENDING_WARD_APPROVAL` — **PASSED**؛ (2) القيد
الفريد `uq_guardian_ward` يرفض نفس زوج (guardian, ward) مرتين
(`IntegrityError` فعلي من DB) — **PASSED**؛ (3) القيد الفريد
`uq_guardian_visibility_relationship_sector` يرفض نفس القطاع مرتين لنفس
العلاقة — **PASSED**. **3/3 نجحوا.**

**اكتشاف جانبي أثناء كتابة الاختبار (deadlock حقيقي، اتصلح في الاختبار
نفسه، صفر تعديل على الكود الأساسي):** أول محاولة تشغيل عَلَّقت بلا نهاية
(اتأكَّد بفحص `pg_stat_activity` مباشرة). السبب: `INSERT` في
`guardian_relationships` بياخد قفل `FOR KEY SHARE` على صفوف `users`
المُشار إليها (guardian/ward) لحد ما الترانزاكشن تتقفل — الاختبار كان
بيعمل `flush()` بس (بلا `commit()`) ثم الـ`finally` بيفتح `session`
منفصلة (`AsyncSessionLocal()`) وتحاول `DELETE FROM users` لنفس الصفوف
→ تعليق دائري: الـfinally مستني قفل مايتفكش غير لما الـtest function
نفسها تخلص، والـtest function مستنية الـfinally يخلص. الحل: إضافة
`await db.commit()` صريح بعد كل إنشاء ناجح (نفس نمط
`AchievementService.grant_achievement` اللي بيعمل `commit()` داخل
الـservice — هنا الاختبار نفسه لعب دور الـservice المؤقت). بعد الإصلاح:
3/3 نجحوا في 57.75 ثانية، صفر بقايا بيانات (اتأكَّد مباشرة على DB).

**Regression check:** `pytest --collect-only` على كامل `tests/`
(226 اختبار عبر كل الملفات) — صفر خطأ استيراد جديد من الدومين الجديد؛
الخطأ الوحيد الموجود (`ActionCommission` مفقودة من
`app.domains.affiliate.models`) **مسبق وموثَّق من قبل**
([[project_tourism_sports_entity_membership_implementation_closed]]،
side-finding لم يُصلَح)، صفر علاقة بهذه الجلسة. + عيّنة تشغيل فعلية
(`test_achievements_foundation_implementation.py` +
`test_achievement_auto_grant_training_implementation.py`, 7 اختبارات) —
**7/7 نجحوا**، صفر تأثير من الدومين الجديد على أي دومين قائم (إضافة
بحتة، صفر تعديل على أي ملف موجود مسبقًا).

**الحالة النهائية:** الأساس (migration + models + schemas + repository)
مبني بالكامل ومتحقَّق منه حيًا. **صفر endpoint، صفر service، صفر منطق
تدفق (طلب/موافقة/رفض/تحقق إداري/تنبيهات)** — كل ده مرحلة تانية بموافقة
صريحة منفصلة. لم يُعمَل commit بعد — بانتظار طلب المستخدم.

**المرجع الكامل:**
`.claude/reports/guardian-relationship-foundation-implementation-session-log.md`.

## [2026-09-16] guardian-relationship-flow-implementation — ✅ المرحلة الثانية (service.py/router.py كاملين): 6 endpoints، 6/6 اختبارات حية، اكتشاف وإصلاح باج identity-map حقيقي

بناءً على [[project_guardian_relationship_foundation_implementation]]
(الأساس: migration 056 + models/schemas/repository) و
[[project_guardian_flow_implementation_planning]] (تخطيط read-only)،
اتبنى منطق التدفق الكامل — `service.py` + `router.py` جديدين في
`app/domains/guardian/`، + endpoint إضافي واحد صغير في `identity`:

- **`identity/repository.py`**: إضافة `UserRepository.list_by_role(tenant_id,
  roles)` — دالة جديدة بحتة (صفر تعديل على أي دالة قائمة)، لجلب كل
  `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` نشط في tenant معيّن (كانت
  التوصية الجاهزة من جلسة التخطيط).
- **`guardian/schemas.py`**: 6 schemas جديدة للطلبات/الردود
  (`GuardianRelationshipRequestCreate` بدون `guardian_user_id` عمدًا —
  بيتحدد من `current_user` دايمًا، مش من مدخلات العميل؛
  `GuardianRelationshipApproveRequest`, `RejectRequest`,
  `ReviewRequest` مع `field_validator` يقصر `status` على
  `VERIFIED`/`REJECTED` بس، `GuardianVisibilityUpdateRequest`,
  `UserLookupResponse`).
- **`guardian/repository.py`**: 3 دوال جديدة — `update_relationship`
  (تحديث عام)، `upsert_visibility_setting` (INSERT...ON CONFLICT DO
  UPDATE ذرّي، نفس نمط `AchievementRepository.increment_bootcamp_network_size`).
- **`guardian/service.py`** (جديد بالكامل) — `GuardianService`:
  1. `find_user(email, username)` — تطابق تام بس (`get_by_email`/
     `get_by_username` الموجودتين فعليًا، غير المُعرَّضتين سابقًا).
  2. `create_relationship_request` — فحص تكرار (pre-check +
     `IntegrityError` fallback، نفس نمط achievements)، `PENDING_WARD_APPROVAL`.
  3. `approve_relationship` — يتطلب `ward_birth_date_provided` في
     الطلب. حساب عمر يدوي (بلا مكتبة خارجية). تاريخ في المستقبل =
     "إدخال مرفوض" → `PENDING_ADMIN_REVIEW` (زي القاصر بالحرف، مش خطأ
     4xx). 18+ → `VERIFIED` فورًا (`verified_by=None`, self-attested).
     أقل من 18 أو تاريخ مرفوض → `PENDING_ADMIN_REVIEW` + تنبيه فعلي
     لكل الأدمنز (loop على `send_notification` المفردة — صفر دعم
     لمستلمين متعددين في الدالة نفسها، زي ما وثَّقت الجلسات السابقة).
  4. `reject_relationship` — الطالب بس، `PENDING_WARD_APPROVAL` فقط.
  5. `review_relationship` — الأدمن (`get_current_superuser` في
     الراوتر)، يتطلب الحالة `PENDING_ADMIN_REVIEW`، `REJECTED` يتطلب
     `rejection_reason`.
  6. `update_visibility` — الطالب بس، يتطلب `VERIFIED`، upsert لكل
     قطاع مُرسَل.
  - `_ensure_default_visibility_settings`: تُنشئ الـ4 صفوف رؤية
    (is_visible=True) تلقائيًا أول ما العلاقة توصل `VERIFIED` (عبر
    أي مسار — موافقة راشد أو مراجعة أدمن).
- **`guardian/router.py`** (جديد بالكامل) — 6 endpoints مطابقة تمامًا
  للمطلوب: `GET /guardian/find-user`, `POST /guardian/relationships`,
  `POST .../{id}/approve`, `POST .../{id}/reject`,
  `PUT .../{id}/review` (`get_current_superuser`)،
  `PUT .../{id}/visibility`. باقي كلهم `get_current_active_user`.
- **`main.py`**: تسجيل `guardian_router` (import + سطر في
  `routers_config`، بين `finance` و`health` أبجديًا) — صفر تعديل على
  أي router قائم.

**اكتشاف وإصلاح باج حقيقي أثناء الاختبار (نفس فئة باج
`get_network_stats` الموثَّق في achievements، اتكرر هنا بالغلط):**
`upsert_visibility_setting` كانت بترجع القيمة القديمة (`is_visible`
الأصلية) بعد الـUPDATE مباشرة، رغم إن التنفيذ في DB كان صح — identity
map الخاصة بالـsession كانت بترجّع الكائن المحمَّل قبل كده (من
`_ensure_default_visibility_settings`) بدل القيمة الطازة. الإصلاح:
إضافة `.execution_options(populate_existing=True)` على الـSELECT بعد
الـupsert مباشرة — بالحرف نفس حل `AchievementRepository.get_network_stats`.
اتأكَّد بالفشل الفعلي للاختبار قبل الإصلاح ونجاحه بعده.

**الاختبار الحي** (`tests/test_guardian_relationship_flow_implementation.py`,
6 سيناريوهات، عبر `GuardianService` مباشرة بلا HTTP client، فوق DB
حقيقية): بحث تطابق تام + عدم وجود + تحقق مدخلات؛ راشد يوافق فورًا
(`VERIFIED` self-attested) + يتحكم في رؤية قطاع واحد بنجاح؛ قاصر →
`PENDING_ADMIN_REVIEW` + **تحقق فعلي من DB إن الأدمن استلم إشعار حقيقي**
(صف `Notification` بـ`idempotency_key` مطابق) → مراجعة أدمن `VERIFIED`؛
رفض الطالب + منع معالجة مزدوجة؛ منع تكرار نفس زوج (guardian, ward)؛
تفويض خاطئ (مستخدم غريب يحاول يوافق/يرفض) مرفوض + حالات مبكرة (مراجعة
أدمن قبل الأوان، تحكّم في الرؤية قبل VERIFIED) مرفوضة. **6/6 نجحوا.**

**اكتشاف جانبي أثناء التطوير (بيئة، غير مرتبط بالكود، غير مُصلَح
عمدًا):** أول تشغيلة لاختبار القاصر كشفت إن `list_by_role` بترجع
**24 حساب** `SUPER_ADMIN` حقيقي في tenant_id=1 — كلهم throwaway محذوف
منه التنظيف من جلسات اختبار قديمة تمامًا وغير مرتبطة (`p_ctor_*`,
`TEST_*` — انظر أسماءهم)، مش بيانات إنتاج ولا مرتبطين بهذه الجلسة.
هذا يعني كل تشغيلة لمنطق تنبيه الأدمن الجديد كانت هتبعت إشعارات حقيقية
لكل الـ24 حساب دول. **الكود الجديد سليم ويعمل بالضبط زي المطلوب** (تنبيه
كل الأدمنز فعلًا) — المشكلة في تراكم بيانات throwaway قديمة من دومينات
تانية بالكامل. تم فقط تصحيح تنظيف الاختبار الحالي (`_cleanup` بقت تمسح
كل إشعار مرتبط بـ`relationship_id` بغض النظر عن المستلم، مش بس
المستخدمين اللي الاختبار نفسه أنشأهم) — **لم يُلمَس أي كود أو بيانات
تخص الجلسات القديمة دي**، خارج نطاق هذه الجلسة تمامًا.

**Regression check:**
- `pytest --collect-only` على كامل `tests/` (232 اختبار): صفر خطأ
  استيراد جديد؛ نفس الخطأ المسبق الوحيد (`ActionCommission`، موثَّق من
  [[project_tourism_sports_entity_membership_implementation_closed]]).
- `test_guardian_relationship_foundation_implementation.py` +
  `test_guardian_relationship_flow_implementation.py` معًا: **9/9
  نجحوا**.
- عيّنة `test_identity_router_protection.py` +
  `test_user_repository_get_by_id_audit.py` +
  `test_user_repository_get_user_audit.py` (37 اختبار): **12 فشلوا،
  25 نجحوا** — **تأكَّد بالتفصيل إن الـ12 فشل ده صفر علاقة بهذه الجلسة**:
  كلهم عن طبقة "Backlog #8" (`_register_affiliate_commission` +
  `referred_by` عبر zamakana/transport/tourism_sports/tenders_auctions/
  service_marketplace/realestate/arbitration_syndicates/manufacturing/
  invitations/insurance/employment/digital_twin) — دومينات صفر علاقة
  بـ`guardian`. اتأكَّد إن `list_by_role` (الإضافة الوحيدة لـ
  `identity/repository.py`) **مُستخدَمة فقط من `guardian/service.py`**
  (grep شامل، صفر مستدعٍ تاني)، وإن `identity/router.py`/`service.py`/
  `schemas.py` كان عندهم بالفعل تعديلات uncommitted **قبل بداية هذه
  الجلسة** (موجودة في git status الأصلي لبداية المحادثة) — الفشل ده
  مرتبط بيها، مش بإضافة `list_by_role` البسيطة. **لم يُصلَح — خارج نطاق
  هذه الجلسة بالكامل**، يحتاج جلسة منفصلة مخصصة لـBacklog #8.

**الحالة النهائية:** منطق التدفق الكامل مبني ومتحقَّق منه حيًا (9/9
اختبار guardian). Endpoints الستة كلهم مسجَّلين وشغالين
(`/api/guardian/...`). لم يُعمَل commit بعد — بانتظار طلب المستخدم.

**المرجع الكامل:**
`.claude/reports/guardian-flow-implementation-session-log.md`.

## [2026-09-16] health-appointments-tenant-isolation-fix — 🔒 إصلاح أمني عاجل ومعزول تمامًا عن guardian: `HealthRepository.list_appointments`/`HealthService.get_my_appointments` كانا بلا فلتر tenant_id إطلاقًا

**هذا البند منفصل تمامًا عن كل جلسات guardian السابقة — صفر لمس على
أي كود أو دومين guardian في هذه الجلسة**، بناءً على اكتشاف جانبي من
جلسة [[project_guardian_overview_endpoint_planning]] (فحص read-only)
تطلَّب إصلاحًا عاجلًا معزولًا فورًا.

**الثغرة المؤكَّدة قبل الإصلاح:**
```python
# health/repository.py (قبل)
async def list_appointments(self, user_id: int, status: Optional[str] = None):
    query = select(MedicalAppointment).where(MedicalAppointment.patient_user_id == user_id)
    ...
```
**صفر أي فلتر `tenant_id`** — الدالة بتفلتر بـ`patient_user_id` بس.
`HealthService.get_my_appointments(user_id, status_filter=None)` نفس
الشيء بالضبط، وبتمررهم كده لـrepo. `HealthService(db)` نفسها بتتبنى
بلا `tenant_id` أصلًا (بعكس كل الدومينات التانية زي
`AcademyService(db, tenant_id)`). أي مسار مستقبلي (أو حالي غير مكتشَف)
يستدعي هذه الدالة بـ`user_id` تابع لمستخدم في تينانت مختلف عن المتوقَّع
كان هيرجّع بياناته الطبية بلا أي حاجز.

**الإصلاح (3 ملفات، تعديل بسيط ومحدود جدًا):**
- `health/repository.py`: `list_appointments(user_id, tenant_id, status=None)`
  — إضافة `and_(MedicalAppointment.patient_user_id == user_id,
  MedicalAppointment.tenant_id == tenant_id)` (استيراد `and_` جديد).
- `health/service.py`: `get_my_appointments(user_id, tenant_id,
  status_filter=None)` — تمرير `tenant_id` للـrepo. **دالة تانية غير
  مرتبطة** (`get_health_carbon_footprint`) كانت بتستدعي نفس
  `repo.list_appointments(user_id)` القديمة — اتصلحت بتمرير `tenant_id`
  كمان (تعديل ميكانيكي إجباري لتفادي كسرها بالتوقيع الجديد؛ تم التحقق
  إنها **dead code فعليًا** — صفر مستدعٍ لها من أي router أو مكان تاني
  في المشروع كله، `"get_health_carbon_footprint"` الظاهرة في
  `process_voice_command` مجرد نص وصفي في dict، مش استدعاء فعلي).
- `health/router.py`: `GET /health/appointments` — تمرير
  `tenant_id=cast(int, current_user.tenant_id)` (من التوكن المُوثَّق،
  مش أي header) عند استدعاء `service.get_my_appointments`.

**الاختبار الحي** (`tests/test_health_appointments_tenant_isolation_fix.py`):
مستخدم بموعد طبي حقيقي في `tenant_id=1` (عيادة + موعد حقيقيين، بلا
استخدام `book_appointment` كامل تفاديًا لتعقيد رسوم المحفظة غير
المرتبط بالاختبار) → استدعاء `get_my_appointments(user_id, tenant_id=16)`
→ **قائمة فارغة فعليًا** (صفر تسريب)؛ استدعاء بـ`tenant_id=1` الصح →
**الموعد يظهر عادي** (صفر false negative من الإصلاح). **PASSED**.

**Regression check:**
- كل اختبارات health الحالية (`test_health_entity_membership_full_implementation.py`
  + `test_health_nameerror_and_fee_ordering_fix.py`، 7 اختبارات بما
  فيها `book_appointment` الكامل مع الرسوم): **7/7 نجحوا**.
- `pytest --collect-only` على كامل `tests/` (233 اختبار، +1 من هذه
  الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission`، غير مرتبط، موثَّق من قبل).

**الحالة النهائية:** الثغرة مُصلَحة ومتحقَّق منها حيًا. **صفر لمس على
أي كود guardian في هذه الجلسة بالكامل** (فُحص بالمطابقة قبل وبعد —
الملفات المعدَّلة الوحيدة: `health/repository.py`, `health/service.py`,
`health/router.py`, + ملف الاختبار الجديد). لم يُعمَل commit بعد —
بانتظار طلب المستخدم.

**المرجع الكامل:**
`.claude/reports/health-appointments-tenant-isolation-fix-session-log.md`.

## [2026-09-16] guardian-overview-endpoint-implementation — ✅ GET /guardian/wards/{ward_id}/overview مبني بالكامل: تفويض VERIFIED + احترام الرؤية + تجميع تسلسلي من 4 دومينات، 12/12 اختبار guardian

بناءً على [[project_guardian_overview_endpoint_planning]] (فحص
read-only سابق)، اتبنى endpoint موحَّد يجمّع ملخصات خفيفة من academy،
achievements، social، transport، health لولي أمر مُوثَّق — بأقل قدر
تعديل ممكن على الدومينات القائمة (إضافتان جديدتان بس، صفر تعديل على
منطق موجود):

- **الأمان أولًا** (`GuardianService.get_ward_overview`): فحص
  `GuardianRelationship` بين `guardian_user_id`/`ward_user_id` — لازم
  تكون موجودة، `tenant_id` مطابق، و**`status == VERIFIED` بالحرف** (مش
  `PENDING_*`) — غير كده `PermissionDeniedError` (403) فورًا، قبل أي
  استعلام لأي دومين تشغيلي.
- **احترام الرؤية**: لكل قطاع من الأربعة، لو فيه صف
  `GuardianVisibilitySetting` صريح بـ`is_visible=False`، **القسم
  بيُستبعد تمامًا من الـdict المُرجَع** (مفتاح غائب بالكامل، مش
  `null`) — الـendpoint نفسه **بلا `response_model`** عمدًا عشان
  `jsonable_encoder` يسيب الـdict زي ما هو بالظبط، بلا أي مفتاح إضافي
  بقيمة فاضية.
- **استدعاء تسلسلي بحت** — 4 `await` متتاليين على نفس `self.db`
  المُحقَنة، **صفر `asyncio.gather`** (راجع سبب الخطر الموثَّق في تقرير
  التخطيط، ومثال `projects/service.py:455` كتحذير فعلي موجود بالكود).

**إضافتان جديدتان بس (صفر تعديل على أي دالة قائمة)، بالضبط زي ما
اتفق):**
- `AcademyRepository.get_user_enrollments_summary` +
  `AcademyService.get_user_enrollments_summary` — `join` جديد مع
  `Course.title` (كان مفقودًا، `get_user_enrollments` القائمة اتسابت
  بلا لمس).
- `SocialRepository.get_user_activity_summary` +
  `SocialService.get_user_activity_summary` — دالة جديدة بالكامل
  (مفيش أي دالة "منشورات مستخدم" كانت موجودة أصلًا)، بترجع `{post_count,
  comment_count, last_activity_at}` **بلا أي محتوى نصي خام** — `Post`
  بلا أي عمود خصوصية (راجع تقرير التخطيط)، فالعد المجرد هو الخيار
  الآمن الوحيد.
- **achievements/transport/health: صفر كود جديد في الدومينات نفسها** —
  `GuardianService` بتستهلك `AchievementService.get_user_achievements`
  + `AchievementService.list_definitions` (موجودتين) لعمل الـjoin
  (اسم/أيقونة) في طبقة guardian نفسها؛ `TransportService.list_bookings`
  (موجودة، مش `get_my_bookings` — تفصيل مهم تحت)؛
  `HealthService.get_my_appointments` (بعد إصلاح الجلسة اللي فاتت) +
  `HealthService.get_facility` (موجودة) لاسم المنشأة.

**⚠️ انحراف واحد موثَّق عن الطلب الحرفي:** استُخدمت
`TransportService.list_bookings(tenant_id, passenger_id=ward_id)` بدل
`get_my_bookings` المذكورة — الاتنين بينفذوا **نفس استعلام repo
بالحرف**، لكن `get_my_bookings` بتضيف `_check_saas_limits(tenant_id,
"transport")` فوقها (بوابة اشتراك SaaS للـtenant ككل، اتأكَّد فعليًا
بالفشل الحي: tenant_id=1 في DB الديف مالوش خطة "transport" مفعَّلة،
فـ`get_my_bookings` كانت هتكسر overview أي طالب لأي tenant بلا اشتراك
transport صريح — قيد بيئي منفصل تمامًا عن تفويض guardian). التبديل
لـ`list_bookings` بيحافظ على نفس البيانات بالضبط بلا المخاطرة بتعديل
اشتراكات tenant المشتركة.

**الاختبار الحي** (`tests/test_guardian_overview_endpoint_implementation.py`،
3 سيناريوهات، fixtures عبر إدخال ORM مباشر لكل الدومينات الأربعة —
كورس+تسجيل، تعريف إنجاز+منح، منشور+تعليق، محطتان+أسطول+مركبة+مسار+رحلة+حجز،
منشأة+موعد):
1. علاقة VERIFIED + نشاط حقيقي في الأربعة → الرد يحتوي بيانات صحيحة
   من كل قطاع (عنوان الكورس، اسم الإنجاز، عدد المنشورات/التعليقات،
   تاريخ/حالة الرحلة، اسم المنشأة/حالة الموعد) — **PASSED**.
2. نفس الطالب يحجب HEALTH بعدها (`update_visibility`) → استدعاء تاني
   → `"health" not in overview` (استبعاد كامل، مش `null`)، باقي
   الثلاثة لسه موجودين — **PASSED**.
3. علاقة `PENDING_WARD_APPROVAL` (مش VERIFIED بعد) → `PermissionDeniedError`
   — **PASSED**.
4. مستخدم بلا أي علاقة إطلاقًا → `PermissionDeniedError` — **PASSED**.

**النتيجة: 3/3 نجحوا** (12/12 مع كل ملفات guardian الثلاثة معًا).

**Regression check:**
- كل اختبارات guardian الثلاثة معًا (foundation + flow + overview):
  **12/12 نجحوا**.
- عيّنة عبر الدومينات المُعدَّلة (`test_social_getter_endpoints_wiring.py`
  + `test_transport_getter_endpoints_wiring.py` +
  `test_transport_vehicles_fleets_drivers.py` +
  `test_achievements_foundation_implementation.py`، 19 اختبار): **19/19
  نجحوا** — صفر تأثير من `get_user_enrollments_summary`/
  `get_user_activity_summary` الجديدتين على أي مسار قائم.
- `pytest --collect-only` على كامل `tests/` (236 اختبار، +3 من هذه
  الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission`، غير مرتبط).

**الحالة النهائية:** الـendpoint مبني بالكامل ومتحقَّق منه حيًا.
**صفر تعديل على أي منطق قائم** في academy/achievements/social/transport/health
— إضافتان جديدتان فقط (academy join + social summary)، والباقي استهلاك
مباشر لدوال موجودة من طبقة guardian. لم يُعمَل commit بعد — بانتظار
طلب المستخدم.

**المرجع الكامل:**
`.claude/reports/guardian-overview-endpoint-implementation-session-log.md`.

## [2026-09-16] بند Backlog جديد — `backlog-live-session-instructor-id-no-identity-verification`

**الوصف:** `instructor_id` في `LiveSessionCreate` (`academy/schemas.py:317-319`)
حقل إجباري بلا قيمة افتراضية، **يُدخَل حر بالكامل من العميل** — بلا أي
تحقق سيرفر إنه يطابق `Course.instructor_id` بتاع الكورس اللي الـlive
session تابعة له، ولا حتى إنه يطابق `current_user.id` (المُدخِل نفسه).
الفحص الوحيد على الـendpoint (`POST /academy/nodes/{node_id}/live`،
`academy/router.py:433-442`) هو `get_current_instructor_or_admin` —
دور عام (INSTRUCTOR/ADMIN/SUPER_ADMIN/EXECUTIVE_DIRECTOR)، مش تطابق
هوية. أي مدرّس أو أدمن يقدر يدخل `instructor_id` لمدرّس تاني تمامًا،
عمدًا أو بالغلط، وهيتقبل بلا اعتراض.

**تصحيح على التوثيق التاريخي** (كان موثَّقًا في جلسة
`targeted-notifications-planning` كـ"hardcoded `instructor_id=1`"):
الـfallback الفعلي في `AcademyRepository.create_live_session`
(`academy/repository.py:707-716`، `if "instructor_id" not in
session_data: session_data["instructor_id"] = 1`) **غير قابل للتفعيل
عمليًا اليوم** — بما إن `LiveSessionCreate` بتحدد الحقل إجباري،
`data.model_dump()` هيحتوي المفتاح دايمًا (تأكَّد بـgrep شامل: صفر
مستدعٍ تاني لـ`create_live_session` في كامل المشروع). **المشكلة
الحقيقية أعمق من الـfallback نفسه**: غياب أي تحقق مقابل مصدر حقيقة
(`Course.instructor_id`) على القيمة المُدخَلة، مش القيمة الافتراضية
الميتة.

**الأثر:** خطر نظري بالكامل حاليًا — جدول `live_sessions` **فاضي
تمامًا** في DB الديف (تأكَّد مباشرة، صفر صف)، فمفيش أي بيانات حقيقية
اتأثرت لحد الآن. لكن الخطر بنيوي وحقيقي: أي استخدام فعلي مستقبلي
(بما فيه أي منطق تنبيه/توجيه يعتمد على `LiveSession.instructor_id`،
زي ميزة "رسالة لمدرّس" المُخطَّط لها) معرَّض لمعلومة مدرّس غير موثوقة.

**الحل المتوقَّع (لم يُنفَّذ):** إما (أ) اشتقاق `instructor_id` من
`Course.instructor_id` بتاع الكورس نفسه بدل قبوله من العميل (حذفه من
`LiveSessionCreate` تمامًا)، أو (ب) لو لازم يفضل قابل للتخصيص (مدرّس
مختلف يغطي جلسة معيّنة)، إضافة تحقق صريح إنه عضو مُصرَّح له بالتدريس
على هذا الكورس (زي عضوية كيان)، مش مجرد دور عام.

**الحالة:** 🟡 **مفتوح، أولوية متوسطة** — خطر نظري (الجدول فاضي حاليًا)
لكن بنيوي حقيقي، يستاهل إصلاح قبل أي اعتماد فعلي على
`LiveSession.instructor_id` في ميزة جديدة. راجع
`.claude/reports/guardian-message-instructor-planning-session-log.md` §2.

---

## [2026-09-16] بند Backlog جديد — `backlog-send-notification-missing-realtime-broadcast`

**الوصف:** `broadcast_to_user_redis()` (`communications/router.py:79-82`
— البث اللحظي الحقيقي الوحيد عبر Redis Pub/Sub لـWebSocket
`/communications/ws`) **موجودة ومُستدعاة فقط جوّه الـrouter handler
الخاص بـ`POST /communications/notifications/send`**
(`communications/router.py:89-128`، endpoint إداري محمي
بـ`get_current_superuser`) — **بعد** استدعاء
`CommunicationsService.send_notification()`، مش جوّها. البث اللحظي
**ليس جزءًا من `send_notification()` نفسها إطلاقًا**.

**الأثر المؤكَّد بالقراءة المباشرة:** أي دومين تاني بينادي
`CommunicationsService.send_notification()` مباشرة — وهو نمط
الاستخدام الفعلي **الوحيد** اليوم عبر كل المشروع (`transport`,
`realestate`, `automation`, `saas`, و`guardian._notify_admins_pending_review`
من الجلسات الأخيرة) — بياخد **صف `Notification` محفوظ في DB بس**،
**بلا أي بث WebSocket لحظي**. المستلم لازم يفتح `GET
/communications/notifications/me` (endpoint موجود ومؤكَّد،
`communications/router.py:134`) بنفسه ليكتشف وجود إشعار جديد — صفر
"push" حقيقي لأي تنبيه برمجي (server-to-server) في المشروع كله
اليوم، فقط للمسار الإداري اليدوي الوحيد. **تأكيد إضافي:**
`send_notification_task` (Celery، `app/core/celery_app.py:71-73`)
نفسها دالة فارغة تمامًا (`pass`، موسومة صراحةً "مؤقتة") بغض النظر عن
القناة — يعني حتى لو البث كان جوّه الـservice، مفيش قناة فعلية غير
Redis Pub/Sub أصلًا.

**الحل المتوقَّع (لم يُنفَّذ):** نقل استدعاء `broadcast_to_user_redis()`
لجوّه `CommunicationsService.send_notification()` نفسها (بعد الـcommit
مباشرة)، عشان كل مستدعٍ برمجي يستفيد من نفس البث اللحظي بدل الأدمن
اليدوي بس. يحتاج فحص تبعية دائرية محتملة (`communications/service.py`
لازم يستورد من `communications/router.py` أو نقل الدالة المساعدة
لمكان مشترك، زي `app/core/` أو داخل الـservice نفسها).

**الحالة:** 🟡 **مفتوح، أولوية متوسطة** — كل تنبيهات اليوم (بما فيها
تنبيهات guardian للأدمنز) بتفتقد بثًا لحظيًا فعليًا، لكن الوظيفة
الأساسية (حفظ الإشعار + إمكانية الاستعلام عنه لاحقًا) سليمة. راجع
`.claude/reports/guardian-message-instructor-planning-session-log.md` §3.

## [2026-09-16] guardian-message-instructor-implementation — ✅ POST /guardian/wards/{ward_id}/message-instructor مبني بالكامل، 16/16 اختبار guardian — اكتشاف وتجاوز باج schema حقيقي (academy_instructors بلا tenant_id)

بناءً على [[project_guardian_message_instructor_planning]] بالحرف، اتبنى
`GuardianService.message_instructor` + `POST
/guardian/wards/{ward_id}/message-instructor`:

- **فحص التفويض**: نفس `get_ward_overview` بالحرف (`GuardianRelationship`
  موجودة، `tenant_id` مطابق، `status == VERIFIED`) + فحص إضافي خاص:
  `GuardianVisibilitySetting` لقطاع `ACADEMY` لازم يكون `is_visible=True`
  — غير كده `PermissionDeniedError`.
- **سلسلة تحديد المدرّس**: `AcademyRepository.get_enrollment(ward_id,
  course_id, tenant_id)` (تأكيد تسجيل فعلي، غير كده `NotFoundError`) →
  `AcademyRepository.get_course(course_id, tenant_id)` (`instructor_id
  IS NULL` → `NotFoundError`) → **مش** `AcademyRepository.get_instructor`
  (راجع الاكتشاف تحت) → `send_notification(user_id=instructor_user_id,
  ..., channel=IN_APP, idempotency_key=None)`. قرار `idempotency_key=None`
  موثَّق بتعليق صريح في الكود: الرسائل مش عملية حساسة لإعادة محاولة،
  كل رسالة لازم تتسجل كصف مستقل.

**⚠️ اكتشاف باج schema حقيقي أثناء التحقق الحي (مش تخطيطي):**
`AcademyRepository.get_instructor(instructor_id, tenant_id)` — الدالة
المطلوبة أصلًا في التخطيط لخطوة 4 — **بتفشل فوريًا لأي استدعاء
إطلاقًا**، مؤكَّد بتجربة مباشرة معزولة قبل أي لمس كود:
```
sqlalchemy.exc.ProgrammingError: UndefinedColumnError: column academy_instructors.tenant_id does not exist
```
الموديل (`academy/models.py`) بيعرّف `Instructor.tenant_id`، لكن جدول
`academy_instructors` الفعلي (`\d academy_instructors` حي) **بلا هذا
العمود إطلاقًا** — انحراف موديل↔DB قديم، موجود من قبل هذه الجلسة
بالكامل، غير مرتبط بـguardian. **تم إيقاف التنفيذ وعرض الخيارات على
المستخدم صراحةً** (تجاوز داخل guardian فقط / إصلاح `get_instructor`
نفسها / migration لإضافة العمود / تأجيل كامل) — **القرار المُتَّخذ:
تجاوز معزول تمامًا داخل `guardian/repository.py` بس، صفر لمس على
`academy/repository.py` أو أي migration.**

**الحل المُنفَّذ**: دالة جديدة `GuardianRepository.get_instructor_user_id(instructor_id)`
— `SELECT Instructor.user_id WHERE Instructor.id == instructor_id` **بلا
أي فلتر `tenant_id`** (الأمان محقَّق مسبقًا عبر `Course.tenant_id`
المفحوص فعلًا في الخطوة السابقة — `Course.instructor_id` FK يضمن صف
`Instructor` حقيقي). `message_instructor` بتستخدمها بدل
`academy_repo.get_instructor(...)`. **صفر تعديل على أي ملف academy.**

**الاختبار الحي** (`tests/test_guardian_message_instructor_implementation.py`،
4 سيناريوهات — الـfixture لصف `Instructor` استخدمت `insert()` من
SQLAlchemy Core بدل `db.add(Instructor(...))` عمدًا، لنفس سبب باج
الـschema بالضبط: الـORM كان بيولّد INSERT شامل لكل أعمدة الموديل
المُعرَّفة بما فيها `tenant_id` الوهمي، حتى بدون تمريره صراحةً):
1. علاقة VERIFIED + تسجيل فعلي + مدرّس مُسنَد → نجاح، صف `Notification`
   حقيقي محفوظ للمدرّس (تحقق مباشر من DB، مش mock). **PASSED**.
2. قطاع `ACADEMY` محجوب → `PermissionDeniedError`. **PASSED**.
3. `course_id` الطالب مش مسجَّل فيه → `NotFoundError`. **PASSED**.
4. كورس بلا مدرّس مُسنَد (`instructor_id IS NULL`) → `NotFoundError`.
   **PASSED**.

**النتيجة: 4/4 نجحوا** (16/16 مع كل ملفات guardian الأربعة معًا).

**اكتشاف جانبي أثناء التطوير (غير مرتبط بالكود النهائي، مُصلَح ذاتيًا):**
أول محاولتين للاختبار فشلتا (قبل اكتشاف الحل النهائي)، وبما إن المستخدمين
التجريبيين بيتكوّنوا عبر `UserRepository.create()` (بتعمل `commit()`
فوري، مستقل عن نجاح باقي الاختبار)، تركوا **36 مستخدم throwaway يتيم**
في DB (الفشل حصل قبل الوصول لـ`try/finally` الخاص بالتنظيف). اتنضَّفوا
يدويًا بعد نجاح التشغيلة النهائية (`DELETE ... WHERE username LIKE
'p_regtest_msg_%'` بعد تأكيد `4/4 PASSED`) — **صفر بقايا بيانات
حاليًا**، ونمط `fx = await _build_...()` قبل `try:` (بدل جوّاه) موجود
كمان في كل ملفات guardian السابقة (سابقة قائمة، لم تُعدَّل هنا).

**Regression check:**
- كل ملفات guardian الأربعة معًا (foundation + flow + overview +
  message-instructor): **16/16 نجحوا**.
- `pytest --collect-only` على كامل `tests/` (240 اختبار، +4 من هذه
  الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission`، غير مرتبط).
- **صفر تعديل على `academy/`, `communications/`, أو أي دومين تاني غير
  `guardian/`** — تم التحقق بمطابقة الملفات المعدَّلة.

**الحالة النهائية:** الـendpoint مبني بالكامل ومتحقَّق منه حيًا. باج
schema حقيقي اتكشف، اتوقَّف التنفيذ، اتعرضت الخيارات، واتحل بقرار
المستخدم الصريح بأضيق نطاق ممكن. لم يُعمَل commit بعد — بانتظار طلب
المستخدم.

**المرجع الكامل:**
`.claude/reports/guardian-message-instructor-implementation-session-log.md`.

## [2026-09-16] بند Backlog جديد — `backlog-academy-instructors-missing-tenant-id`

**الوصف:** جدول `academy_instructors` الفعلي في DB **بلا عمود
`tenant_id` إطلاقًا** (تأكَّد مباشرة عبر `\d academy_instructors`:
`id, user_id, org_entity_id, bio, expertise_areas,
revenue_share_percentage, is_approved, created_at, updated_at` بس) —
رغم إن الموديل `Instructor` (`academy/models.py`) بيعرّف
`tenant_id = Column(Integer, ForeignKey("academy_tenants.id"),
nullable=False, index=True)` صراحةً. **أي كود يحاول `INSERT` أو
`SELECT`/`WHERE` على `Instructor.tenant_id` عبر الـORM يفشل فورًا
بـ`UndefinedColumnError`** — مؤكَّد حيًا مرتين مستقلتين (`INSERT` عبر
`db.add(Instructor(...))`، و`SELECT` عبر
`AcademyRepository.get_instructor()`).

**الأثر:** `AcademyRepository.create_instructor()` (`repository.py:142-146`)
و`AcademyRepository.get_instructor()` (`repository.py:149-153`) —
**كلاهما مكسورتان بالكامل لأي استدعاء، بلا استثناء**. `create_instructor`
**dead code فعليًا** (صفر مستدعٍ في كامل المشروع، تأكَّد بـgrep) — مفيش
أي endpoint حاليًا لإنشاء مدرّس جديد عبر الـAPI. `get_instructor`
**مُستخدَمة في مسارات حية** (`count_instructor_courses` وما شابه)، لكن
لم تُختبَر حيًا قبل هذه الجلسة — أول استدعاء فعلي (أثناء بناء
`guardian.message_instructor`) كشف الكسر فورًا.

**عزل التينانتات على `academy_instructors` معتمد بالكامل على فلترة
غير مباشرة** — عبر `Course.tenant_id` (لما نوصل لمدرّس من خلال كورس)
أو `EntityMembership`/`OrganizationEntity.tenant_id` (لما نوصل من خلال
الكيان التنظيمي) — **مش FK مباشر على الجدول نفسه**. هذا نمط مختلف عن
كل جدول تاني في `academy` (كلهم عندهم `tenant_id` مباشر).

**الحل المتوقَّع (لم يُنفَّذ):** migration مخصَّص يضيف عمود `tenant_id`
فعليًا لجدول `academy_instructors` (مع تحديد قيمته من `org_entity_id`
أو `user_id.tenant_id` للصفوف الحالية إن وُجدت)، بعد فحص بيانات حقيقية
أولًا. يحتاج جلسة تصميم/migration منفصلة تمامًا — **خارج نطاق guardian
بالكامل**.

**الحالة:** 🟡 **مفتوح، أولوية متوسطة** — تُجووِز بنجاح داخل
`guardian/repository.py` (استعلام معزول بلا فلتر `tenant_id`، الأمان
محقَّق عبر `Course` بدلًا منه) بدون الحاجة لإصلاح هذا البند أولًا، لكنه
يستاهل إصلاح مستقل لأي استخدام مستقبلي لـ`AcademyRepository.get_instructor`/
`create_instructor` نفسهما. راجع
`.claude/reports/guardian-message-instructor-implementation-session-log.md`.

## [2026-09-16] تحديث توثيقي — 7 جلسات مُكتشَفة عبر جلسة `uncommitted-pre-existing-changes-audit`، صفر إشارة ليها في هذا الملف قبل الآن

**السياق:** جلسة `uncommitted-pre-existing-changes-audit` (فحص
read-only) كشفت إن 5 ملفات فضلت جزئيًا unstaged بعد commit `2f70711`
(guardian) بترجع لـ~15 تقرير جلسة حقيقي في `.claude/reports/`،
**صفر واحد فيهم موثَّق في `PROGRESS_LOG.md`** — رغم إن كل واحد منهم
مكتمل ومُختبَر حيًا بregression موثَّق في تقريره. الإدخالات السبعة
التالية (بالترتيب الزمني الصحيح حسب تواريخ/توقيتات التقارير الفعلية،
مش ترتيب الاكتشاف) بتسد هذه الفجوة التوثيقية. **صفر تعديل كود أو
commit في هذه الجلسة التوثيقية — توثيق فقط.**

**المرجع الكامل:** `.claude/reports/uncommitted-pre-existing-changes-audit-session-log.md`.

---

## [2026-09-10] health-nameerror-and-fee-ordering-fix — ✅ إصلاح 3 NameError حقيقية (فشل مضمون 100% في كل استدعاء بدون استثناء) + ترتيب الخصم المالي في book_appointment

اكتُشف الباج أولًا في فحص read-only منفصل سابق بنفس اليوم
(`.claude/reports/health-nameerror-investigation-session-log.md`،
2026-09-10): كتلة `audit_log(...)` كاملة (5 أسطر) اتنسخت حرفيًا من
`employment/service.py::create_job` في 3 دوال مختلفة تمامًا في
`health/service.py` (`book_appointment`, `trigger_emergency`,
`create_facility`)، بلا استبدال المتغير `job` بالكائن الفعلي
(`appointment`/`dispatch`/`facility`) ولا `action="JOB_CREATED"` باسم
مناسب للسياق — **`NameError` مضمون الحدوث في كل استدعاء بدون استثناء،
الكود مستحيل ينفّذ جزء `audit_log` بنجاح أبدًا قبل الإصلاح.**

**الإصلاح (٣ دوال):**

| الدالة | `job.id` → | `JOB_CREATED` → | `details` |
|---|---|---|---|
| `book_appointment` | `appointment.id` | `APPOINTMENT_BOOKED` | `{doctor_id, facility_id}` |
| `trigger_emergency` | `dispatch.id` | `EMERGENCY_DISPATCHED` | `{emergency_type}` |
| `create_facility` | `facility.id` | `FACILITY_CREATED` | `{name}` |

+ ترتيب الخصم المالي في `book_appointment`: الرسوم بقت تُخصَم **بعد**
نجاح إنشاء الموعد (جوّه نفس `begin_nested()`)، مش قبله — فشل أي من
الخطوتين يتراجع عن الاثنين معًا عبر نفس الـsavepoint.

**Regression:** تذبذب بيئي عابر (flaky) مرة واحدة أثناء التشغيلة
الكاملة الأولى (فشل اختبارين حيين جدد بـ`PermissionDeniedError:
Insufficient balance`)، اتأكَّد إنه مش regression حقيقي بإعادة تشغيل
معزولة (4/4 نجحت) ثم كاملة نظيفة من الصفر: **`15 failed, 152 passed, 2
xfailed`** — مطابق تمامًا للأساس الموثَّق (جلسة
`invoicing-process-overdue-invoices`، 2026-09-09:
`15 failed, 148 passed, 2 xfailed`) + 4 اختبارات حية جديدة. نفس الـ15
فشل بالحرف، كلهم pre-existing غير مرتبطين بـ`health`/`finance`/
`employment`.

**الملفات:** `health/service.py`, `health/router.py` + اختبار جديد
`tests/test_health_nameerror_and_fee_ordering_fix.py`.

**اكتشاف جانبي وُثِّق كبند backlog منفصل في نفس التقرير (لم يُصلَح في
هذه الجلسة):** باج idempotency (`check_idempotency()` truthy
misinterpretation) — راجع الجلسة التالية.

**المرجع الكامل:** `.claude/reports/health-nameerror-and-fee-ordering-fix-session-log.md`
(خلفية التشخيص: `.claude/reports/health-nameerror-investigation-session-log.md`).

---

## [2026-09-10] idempotency-truthy-bug-fix — ✅ إصلاح باج تفسير القيمة الراجعة من check_idempotency() في 4 مواضع (health×2, communications/router.py×2)

`check_idempotency()` (`app/core/idempotency.py:17-24`) بترجع `True`
لما المفتاح **جديد** (SETNX نجح، يعني "كمّل تنفيذ العملية") — مش لما
فيه نتيجة سابقة مخزَّنة فعليًا. 4 مواضع
(`HealthService._validate_idempotency` المُستخدَمة في `book_appointment`/
`trigger_emergency` + `send_notification`/`send_mail` في
`communications/router.py`) كانت بتفسّر أي قيمة truthy منها على إنها
"نتيجة مخزَّنة، رجّعها فورًا" — فأول استخدام حقيقي لأي `Idempotency-Key`
جديد كان بيرجّع `True` (bool) بدل تنفيذ العملية بالكامل. اكتُشف حيًا
أثناء كتابة اختبار حي بـ`idempotency_key` حقيقي في الجلسة السابقة
ووُثِّق كبند backlog منفصل هناك.

**الإصلاح:** `_validate_idempotency`/`_store_idempotency`
(`health/service.py`) أُعيد كتابتهما لتفرقة صريحة بين "مفتاح جديد"
(`is_new=True` من `check_idempotency`) و"نتيجة مخزَّنة فعليًا" (تُقرأ
من `get_idempotency_result()` منفصلة). نفس المبدأ اتطبَّق على
`send_notification`/`send_mail` في `communications/router.py`.

**اختبار حي جديد (4/4 PASSED, 84.95 ثانية، DB حقيقية `eppne_v2`، صفر
mock):** `tests/test_idempotency_truthy_bug_fix.py` — يغطي الأربعة
مواضع، كل واحد بيتأكد صراحة من `not isinstance(result, bool)` (فحص
مباشر لأعراض الباج القديم).

**Regression:** `15 failed, 156 passed, 2 xfailed` — مطابق تمامًا
للأساس (`invoicing-process-overdue-invoices`: `15 failed, 148 passed`)
+ 4 اختبارات `health-nameerror-and-fee-ordering-fix` (الجلسة السابقة)
+ 4 اختبارات هذه الجلسة = `156`. نفس الـ15 فشل بالحرف. صفر regression.

**الملفات:** `health/service.py`, `communications/router.py` (لم
يُلمَس `communications/service.py` — لم يكن معطوبًا) + اختبار جديد
`tests/test_idempotency_truthy_bug_fix.py`.

**المرجع الكامل:** `.claude/reports/idempotency-truthy-bug-fix-session-log.md`.

---

## [2026-09-14] health-entity-membership-implementation — ✅ نمط EntityMembership لـcreate_facility في health (مقصور عليها صراحة) + migration 052

بناءً على فحص read-only سابق بنفس اليوم
(`.claude/reports/health-entity-membership-planning-session-log.md`)،
اتبنى فحص عضوية على `HealthService.create_facility` بنفس نمط باقي
الدومينات (insurance/transport/tourism_sports/logistics): فحص
`EntityMembershipService.get_member(entity_type="SOVEREIGN_ENTITY",
entity_id=data["entity_id"], user_id=user_id)`، رفض لو مش
`OWNER`/`EXECUTIVE_DIRECTOR`. **نطاق ضيق صريح بالتعليمات** —
`get_or_create_profile` (`tenant_id or 1` fallback) و`list_facilities`
(فلترة tenant بعد الجلب في بايثون، دالتان مختلفتان تمامًا) **ممنوع
لمسهما صراحة، لم يُلمَسا.**

**migration 052** (`052_health_facility_entity_id_fk_set_null.py`):
`ForeignKeyConstraint` جديد على `health_facilities.entity_id` →
`sovereign_entities_v2(id)`, `ondelete='SET NULL'`.

**Regression:** `15 failed, 174 passed, 2 xfailed, 240 warnings in
2038.00s (0:33:57)` — مطابق تمامًا للأساس الموثَّق (جلسة
`tourism-sports-entity-membership-implementation`:
`15 failed, 171 passed, 2 xfailed, 237 warnings`): `174 = 171 + 3`
(3 اختبارات حية جديدة فقط — الاختبار المُحدَّث في
`test_health_nameerror_and_fee_ordering_fix.py` كان موجودًا أصلًا).
نفس الـ15 فشل بالحرف، صفر علاقة بـ`health`.

**الملفات:** `health/schemas.py`, `health/service.py`, `health/router.py`
(معدَّلة) + `tests/test_health_nameerror_and_fee_ordering_fix.py`
(محدَّث). **جديدة:** `migrations/versions/052_health_facility_entity_id_fk_set_null.py`,
`tests/test_health_entity_membership_full_implementation.py`.

**نطاق متبقٍّ خارج هذه الجلسة (عمدًا وصراحةً):**
`get_or_create_profile` (`tenant_id or 1` fallback خطير)،
`list_facilities` (فلترة tenant بعد الجلب في بايثون)، `logistics`
(لسه محتاج فحص read-only قبل أي تنفيذ).

**المرجع الكامل:** `.claude/reports/health-entity-membership-implementation-session-log.md`
(تخطيط: `.claude/reports/health-entity-membership-planning-session-log.md`).

---

## [2026-09-15] achievements-foundation-implementation — ✅ أساس نظام الإنجازات: migration 054 (3 جداول) + 4 endpoints إدارية — ⚠️ تقرير الجلسة الأصلي تالف/شبه فارغ

**⚠️ ملحوظة توثيقية مهمة قبل أي حاجة تانية:** ملف
`.claude/reports/achievements-foundation-implementation-session-log.md`
نفسه **شبه فارغ فعليًا** (يحتوي حرفيًا على كلمة واحدة بس عند الفحص
المباشر — على الأرجح كتابته انقطعت أو اتكتب بالغلط وقتها). **هذا
الإدخال مبني على استنتاج غير مباشر** (استشهاد صريح من تقرير الجلسة
اللاحقة مباشرة + تأكيد تنفيذي مباشر لاحق)، مش على قراءة تقرير الجلسة
نفسها.

**ما اتبنى (مُستنتَج من محتوى `achievements/models.py`/`repository.py`/
`service.py`/`router.py` + migration 054 الحاليين):** دومين
`achievements` جديد بالكامل — 3 جداول (`achievement_definitions`,
`user_achievements`, `user_network_stats`) + 4 endpoints إدارية
(`POST /achievements/definitions`, `GET /achievements/definitions`,
`POST /achievements/grant`, `GET /achievements/users/{user_id}`) — منح
يدوي بس في هذه المرحلة (`trigger_type=MANUAL`)، صفر منطق `AUTO_EVENT`
فعلي بعد (مُخزَّن كقيمة enum فقط، مفيش أي كود بيقرأه وقتها).

**الأساس (baseline) الموثَّق من الجلسة اللاحقة مباشرة** (بما إن تقرير
هذه الجلسة نفسه تالف): **`15 failed, 186 passed, 2 xfailed, 250
warnings`** (مذكور صراحة في
`.claude/reports/achievement-network-tracking-implementation-session-log.md`
كـ"الأساس... آخر جلسة قبل هذه").

**تأكيد تنفيذي مباشر (منفصل تمامًا عن أي تقرير، جلسة
`guardian-relationship-flow-implementation` اللاحقة بيوم واحد):**
شُغِّل `tests/test_achievements_foundation_implementation.py` مباشرة
ضد DB حقيقية — **3/3 PASSED** (إنشاء تعريف، منح يدوي + عرض إنجازات
مستخدم، رفض التكرار عبر القيد الفريد).

**الملفات (مُستنتَجة من محتوى الكود الحالي، غير مؤكَّدة من تقرير
الجلسة نفسه):** `app/domains/achievements/` (جديد بالكامل: `models.py`,
`schemas.py`, `repository.py`, `service.py`, `router.py`)،
`migrations/versions/054_create_achievement_tables.py`، اختبار جديد
`tests/test_achievements_foundation_implementation.py`.

**المرجع:** `.claude/reports/achievements-foundation-implementation-session-log.md`
(تالف — راجع الملحوظة أعلاه).

---

## [2026-09-15] achievement-network-tracking-implementation — ✅ حدث academy.bootcamp_enrollment.created + منطق walk-up (8 مستويات) لعداد الشبكة التراكمي

نشر حدث `academy.bootcamp_enrollment.created` من `enroll_in_course`
(`academy/service.py`) — أول قيمة حقيقية في
`app/core/critical_events.py` (`CRITICAL_EVENT_HANDLERS`)، معالجة عبر
`achievements.update_bootcamp_network_stats`.
`update_bootcamp_network_stats` (`achievements/service.py`) بتمشي فوق
سلسلة `users.referred_by_user_id` بدءًا من المستخدم لحد `max_depth=8`
مستويات، وتزوّد `user_network_stats.bootcamp_network_size` لكل سلف بـ1
(INSERT...ON CONFLICT DO UPDATE ذرّي — مش SELECT ثم UPDATE). بعد كل
تحديث ناجح، فحص فوري لعتبات `AchievementDefinition` من فئة
`TEAM_BUILDING` — لو القيمة الجديدة تجاوزت `trigger_threshold`، منح
تلقائي (`granted_by=None`) عبر INSERT...ON CONFLICT DO NOTHING.

**Regression:** `190 = 186 + 4` (4 اختبارات حية جديدة،
`test_achievement_network_tracking_implementation.py`) — نفس الـ15
فشل pre-existing بالحرف، صفر regression جديد.

**الملفات:** `academy/service.py` (import `EventBus`/`redis_client` +
`self.event_bus` في `__init__` + نشر الحدث في `enroll_in_course`)،
`app/core/critical_events.py` (جديد)، `app/tasks/events.py` (جديد —
`CRITICAL_EVENT_DISPATCH_HANDLERS` + معالج
`bootcamp_enrollment_created`)، `achievements/service.py`
(`update_bootcamp_network_stats`)، `achievements/repository.py`
(`get_referred_by_user_id`, `increment_bootcamp_network_size`,
`get_network_stats` — + إصلاح `populate_existing`).

**⚠️ ملحوظة نطاق (اكتشاف جانبي أثناء التوثيق، خارج نطاق هذه الجلسة
التوثيقية المحدَّد صراحة):** بين هذه الجلسة والجلسة التالية أدناه
(`achievement-auto-grant-training`) وقعت جلستان إضافيتان بنفس النمط
غير موثَّقتين هنا (`achievement-auto-grant-team-building`,
`achievement-auto-grant-project-funding` — أسماء الفئتين التانيتين من
تلات فئات الإنجازات). **نفس فجوة عدم التوثيق في `PROGRESS_LOG.md`،
تستاهل بند مماثل لاحقًا لو طُلب.** راجع
`.claude/reports/achievement-auto-grant-team-building-session-log.md`
و`.claude/reports/achievement-auto-grant-project-funding-session-log.md`.

**المرجع الكامل:** `.claude/reports/achievement-network-tracking-implementation-session-log.md`.

---

## [2026-09-15] achievement-auto-grant-training-session — ✅ حدث academy.course.completed + منح تلقائي مباشر لفئة TRAINING (بلا عتبة، بلا walk-up)

نشر حدث `academy.course.completed` من `update_progress`
(`academy/service.py`) عند اكتمال الكورس (`is_completed=True`) — ثاني
قيمة حقيقية في `CRITICAL_EVENT_HANDLERS`، معالجة عبر
`achievements.grant_training_achievements_for_course_completion`.
بعكس `TEAM_BUILDING` (فيها عتبة `trigger_threshold` + walk-up)، فئة
`TRAINING` بتُمنح **مباشرة بلا عتبة** لأول مرة يوصل فيها الحدث للمستخدم
— نفس آلية INSERT...ON CONFLICT DO NOTHING (القيد الفريد يمنع أي
تكرار، بلا SELECT أول).

**Regression:** `195 = 191 + 4` (4 اختبارات حية جديدة،
`test_achievement_auto_grant_training_implementation.py`؛ الأساس `191
passed` من جلسة `achievement-auto-grant-team-building` غير الموثَّقة
هنا — راجع ملحوظة النطاق في الإدخال السابق). تشغيلة أبطأ من المعتاد
بشكل ملحوظ (~42.5 دقيقة بدل ~10-11 دقيقة المعتادة) اتفحصت صراحة أثناء
الجلسة نفسها (مراقبة `Get-Process` حية: استهلاك CPU فعلي ~215 ثانية
بس من أصل ~2555 ثانية wall-time، ~8%) وتأكَّد إنه ازدحام I/O بيئي عابر
(تراكم حمل DB محلي من كثرة تشغيلات متكررة نفس اليوم)، **مش تغيير في
الكود** — النتيجة النهائية مطابقة تمامًا بلا أي شذوذ. **تأكيد إضافي:**
13 اختبار من 3 جلسات سابقة (`achievements-foundation`,
`achievement-network-tracking`, `achievement-auto-grant-team-building`)
+ `test_critical_event_dispatch_infrastructure.py` — **13/13 لسه
PASSED**، بما فيهم تأكيد إن حدث `academy.bootcamp_enrollment.created`
لسه شغّال بلا أي تداخل مع الحدث الجديد.

**الملفات:** `academy/service.py` (نشر الحدث في `update_progress`)،
`achievements/service.py`
(`grant_training_achievements_for_course_completion`).

**المرجع الكامل:** `.claude/reports/achievement-auto-grant-training-session-log.md`.

---

## [2026-09-15] achievements-stats-endpoints-implementation — ✅ endpoints إحصائية (by-category, top-users, by-definition) + إضافة جانبية: GET /identity/users/search

**endpoints جديدة:** `GET /achievements/stats/by-category`,
`GET /achievements/stats/top-users`, `GET /achievements/stats/by-definition`
(`achievements/service.py`: `get_stats_by_category`, `get_top_users`؛
`achievements/router.py` + `Query` import) — إحصائيات حقيقية من
`UserAchievement` (INNER JOIN عمدًا مع `AchievementDefinition` — فئة/
تعريف بلا أي منح فعلي مش هيظهر إطلاقًا، مش بـ`count=0`).

**إضافة جانبية (نفس اليوم، دومين `identity` مش `achievements`):**
فورم المنح اليدوي في لوحة أدمن الإنجازات احتاج "بحث بالاسم/الإيميل عن
مستخدم". اكتُشف: **صفر endpoint بحث/قائمة مستخدمين شغّال في الباك
إند إطلاقًا** — الفرونت إند القديم (`entity-representatives.tsx`)
بينادي `/users/search` (بلا `/identity` prefix)، endpoint غير موجود
إطلاقًا، بج قديم منفصل تمامًا خارج النطاق (موثَّق كملاحظة بس، لم
يُصلَح). **الحل:** `GET /identity/users/search?q=&limit=` على
`protected_router` الموجود بالفعل — `UserRepository.search_by_username_or_email`
(ILIKE على `username`/`email`، مقيَّد بـtenant)،
`UserService.search_users`, `UserSearchResult` schema (`user_id, name,
email`)، حماية **`is_admin_or_above`** (نفس نمط
`GET /identity/invitations?scope=tenant` الموجود بالفعل بنفس الدومين
بالحرف).

**Regression:** إحصائيات بس: `15 failed, 201 passed, 2 xfailed, 262
warnings in 529.85s` — مطابق تمامًا للأساس (جلسة
`achievement-auto-grant-project-funding` غير الموثَّقة هنا أيضًا —
`199 passed`؛ `201 = 199 + 2` اختبار حي جديد). بعد إضافة identity
search: **`15 failed, 203 passed, 2 xfailed, 264 warnings in
1509.30s` — `203 = 199 + 4`** (2 إحصائيات + 2 بحث). نفس الـ15 فشل
pre-existing بالحرف، صفر علاقة بأي منهما. **تأكيد إضافي:** كل الـ16
اختبار حي القائم بالفعل لدومين `achievements` (5 ملفات) — **16/16 لسه
PASSED** + تحقق مباشر ضد DB إن الحالة رجعت بالظبط لما كانت عليه قبل
الجلسة.

**الملفات:** `achievements/service.py`, `achievements/router.py` (+
`Query` import)، `identity/repository.py`
(`search_by_username_or_email`)، `identity/service.py`
(`UserService.search_users`)، `identity/schemas.py`
(`UserSearchResult`)، `identity/router.py` (`GET /users/search`) —
**صفر تعديل على `app/main.py`** (الراوتر مسجَّل بالفعل من جلسة
`achievements-foundation-implementation`). اختبارات جديدة:
`tests/test_achievements_stats_endpoints_implementation.py`,
`tests/test_identity_users_search_implementation.py`.

**⚠️ ملحوظة نطاق:** الأساس المذكور فوق (`achievement-auto-grant-project-funding`،
`199 passed`) جلسة غير موثَّقة هنا كمان — تالت فئة إنجازات (`PROJECT_FUNDING`)
بنفس نمط `TRAINING` بالحرف. راجع
`.claude/reports/achievement-auto-grant-project-funding-session-log.md`.

**المرجع الكامل:** `.claude/reports/achievements-stats-endpoints-implementation-session-log.md`
(تخطيط: `.claude/reports/achievements-admin-dashboard-planning-session-log.md`).

---

## [2026-09-16] بند Backlog جديد — `insurance-disburse-pensions-hardcoded-system-account`

**الوصف:** اكتُشف أثناء جلسة مراجعة backlog دورية (السؤال الأول: هل بند
`finance-transfer-hardcoded-system-account-real-fund-risk` [2026-08-24]
لسه حي؟). فحص حي (`grep` موسّع على `app/domains/`) أثبت إن **3 من الـ4
مواضع الأصلية اتصلحت فعليًا** في وقت لاحق غير موثَّق صراحة على البند
الأصلي: `commerce/service.py` (`sender_id=customer_id`)،
`affiliate/service.py:577`، `iot/service.py:215` (الاتنان الأخيرين
بقوا يستخدموا `get_or_create_system_account(self.db, tenant_id)`
tenant-scoped بدل `sender_id=1` هاردكودد). **لكن نفس النمط الخطير
بالحرف اتكشف في مكان جديد لم يكن مذكورًا في البند الأصلي إطلاقًا:**
`InsuranceService.disburse_monthly_pensions()` (`insurance/service.py:626`)
لسه بتنادي `finance.transfer(sender_id=1, ...)` هاردكودد، بلا
`get_or_create_system_account`، بلا أي tenant scoping — كل معاش شهري
لأي تينانت بيتسحب فعليًا من نفس حساب `user_id=1`
(`p_system_treasury@example.com`, `wallets.id=39`).

**تحقق حي إضافي [2026-09-16] — هل الخطر حي دلوقتي؟**
1. **الجدولة:** `grep -rn "disburse_monthly_pensions"` على المشروع
   بالكامل أظهر استدعاء واحد بس: `insurance/router.py:358`
   (`POST /insurance/admin/disburse-pensions`, `get_current_superuser`
   + rate limit). فحص `celery_config.py` (`beat_schedule` بالكامل) وصفر
   استخدام لـ APScheduler في المشروع كله يؤكدان: **الدالة مش مجدولة
   خالص** — مفيش Celery beat ولا cron. الخطر **كامن (latent) مش حي
   فعليًا** حاليًا.
2. **الرصيد:** `wallets.id=39` انخفض من 875.0 إلى 771.0 MR_USDT
   (104.0 فرق) منذ توثيق البند الأصلي. `SELECT` على `transactions`
   (`from_wallet_id=39`, آخر 30 يوم) أظهر 95 معاملة تجمع 104.0 بالظبط
   — كلها `REGTEST-*`/فواتير اختبار، **صفر معاملة بأي ذكر لـ
   "pension"/"معاش" في تاريخ الجدول بالكامل**. الفرق مش نتيجة استغلال
   هذا الباج.

**الحل المتوقَّع:** نفس نمط الإصلاح المُطبَّق فعليًا على
`affiliate`/`iot` — استبدال `sender_id=1` بـ
`await get_or_create_system_account(self.db, tenant_id)` داخل الحلقة
(لكل `pension.tenant_id` على حدة، مش تينانت الـservice instance
نفسه — الدالة بتُنادى بلا `tenant_id` بارامتر أصلًا وبتلف على كل
pensions عبر كل التينانتس). يحتاج تصميم/موافقة منفصلة قبل التنفيذ.

**الحالة:** 🟡 **مفتوح، أولوية عالية عند أي تفعيل مستقبلي للـendpoint/جدولة
تلقائية — كامن (latent) لا حي حاليًا.** جزء صريح من عائلة
`finance-transfer-hardcoded-system-account-real-fund-risk` (راجع تحديث
"✅ جزئيًا" على البند الأصلي أعلاه في الملف). |
`.claude/reports/backlog-review-2026-09-16-session-log.md`.

**تصحيح مؤرَّخ [2026-09-21، Batch 0-A] — سطر جديد؛ النص أعلاه لم يُعدَّل:** وصف هذا البند أعلاه ("كل معاش شهري لأي تينانت بيتسحب فعليًا من نفس حساب `user_id=1`" و"بتلف على كل pensions عبر كل التينانتس") كان وصفًا **للنية التصميمية** للكود لا لسلوكه الفعلي وقتها: الاستعلام المستخدَم كان `list_pensions_for_beneficiary(None, ACTIVE)` = `WHERE beneficiary_id IS NULL` على عمود `NOT NULL`، فكان يرجّع **صفر صف دائمًا** والحلقة ما اشتغلتش أصلًا (مؤكَّد حيًا في Batch 0-A: 7 معاشات ACTIVE عبر تينانتين، `count=0`، صفر حركة فلوس، محفظة user 1 = 710.0؛ وسبقه `batch4-audit-security-realestate-insurance-health.md` §4.5). **ما تغيّر في Batch 0-A:** (1) عزل التينانت اتصلح (`list_active_pensions(tenant_id)` + `FinanceService(self.db, tenant_id)`)؛ (2) الحلقة بقت **تصل لأول مرة** لمعاشات حقيقية، ولا فلوس بتتحرك فقط لأن `finance.transfer` بيُستدعى بلا `idempotency_key` (TypeError مبلوع). `sender_id=1` **لسه هاردكودد** (السطر 638 حاليًا، كان :626) — الخطر كامن؛ **قرار الدافع يُحسَم قبل إصلاح `idempotency_key`**. التفاصيل: `insurance-disburse-pensions-payout-logic-broken` (جدول الـBacklog) و`.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §2.4، §11.

---

## [2026-09-21] insurance-batch0a-tenant-isolation

**insurance-batch0a-tenant-isolation — إصلاح أمني عاجل: عزل التينانت في 8 endpoints بدومين `insurance` [2026-09-21]** — ✅ **مُغلَق رسميًا** (نطاق: عزل التينانت + D2 + الطبقة (أ) من `disburse`). النمط المعتمَد من `ai_agents`: `tenant_id = cast(int, current_user.tenant_id)` بدل هيدر `X-Tenant-ID` (`create_policy`، `subscribe`، `get_my_subscriptions`، `submit_claim`، `review_claim`، `create_pension`، `disburse_pensions`، `create_employee_profile`) + فحص انتماء `beneficiary_id`/`user_id` للتينانت (D2، يرجّع 404) + `list_active_pensions(tenant_id)` جديدة. **تحقق حي قبل/بعد (HTTP حقيقي، تينانتان throwaway):** في التشغيل الأول قبل الإصلاح (تينانتات 124/125) نجح **7 سيناريوهات هجوم** عابرة للتينانت (`create_policy`، `review_claim` [رفض مطالبة B]، `create_pension` ×2، `create_employee_profile`، `subscribe` المجاني، `get_my_subscriptions`) اتكتبت/اتقرت في تينانت B؛ أما `subscribe` المدفوع (5b) فتوقّف بـ403 "Insufficient balance" **فقط لأن محفظة المهاجم في تينانت B فارغة** (حاجز عرضي مش دفاع، ومفيش فلوس اتحرّكت)، و`submit_claim` (6) وصل للـINSERT بـ`tenant_id=125` قبل ما يفشل بباج منفصل. وفي التشغيل الأقوى `before2` (تينانتات 126/127، بعد تمويل محفظة `member_A` داخل تينانت B) **نجح 5b كمان (201): محفظة `member_A` في B 500→490، مستلم القسط في B None→10.0، واشتراك اتكتب في تينانت B** — وفحص ghost-wallet أظهر `unchanged: False`. بعد الإصلاح: الكل 404 أو "الهيدر مُتجاهَل، حُلَّ لتينانت المستدعي"، **كل الأرصدة بلا تغيير، صفر محافظ ghost جديدة في تينانت B**، والسيناريوهات المشروعة (`subscribe` مدفوع، `review_claim` approve=20) نتيجتها مطابقة قبل/بعد. `disburse`: 200 `count=0`، صفر فلوس، عزل `list_active_pensions` مُثبَت (A=4 صفوف، B=2، تينانت غير موجود=[])، محفظة user 1 = 710.0 طوال الجلسة. صفر migration، regression دائم `tests/test_insurance_batch0a_tenant_isolation.py` (2 passed ×2). فشلان في suite مسبقان **مُثبَتان بالتشغيل على HEAD نظيف** (`6f68cb4`) وغير متعلقين: `test_insurance_get_user_and_get_user_email_all_three_call_paths` و`test_realestate_buy_fractional_ownership_invoice_ordering`. **⚠️ حدود موثَّقة:** `submit_claim` **مكسور** (مسار نجاحه لم يُتحقَّق منه → `insurance-submit-claim-500`، ويلزم إعادة التحقق العابر للتينانت عند إصلاحه) و`disburse` **معطَّل فعليًا** (الخطر كامن) — راجع تحذير قرار الدافع في البانر. **بنود جديدة:** `insurance-disburse-pensions-payout-logic-broken` (🔴)، `insurance-submit-claim-500` (🔴)، `insurance-review-claim-no-status-guard-and-random-payout-idempotency` (🟡 غير مُتحقَّق، أولوية عالية — تحرّك فلوس)، `insurance-unused-tenant-header-dependencies` (⚪)، `server-startup-index-creation-failure-and-cp1256-logging-errors` (⚪، خارج insurance)، `insurance-batch0a-commits-pending` (⏸️ قرار المستخدم/صاحب جلسة saas)؛ + تحديث مؤرَّخ على `insurance-review-claim-payout-from-reviewer-personal-wallet`، وتصحيح مؤرَّخ أسفل بند [2026-09-16]. **تنظيف:** تينانتات throwaway 124–129 + 5 صفوف `transactions` حُذفت، مقارنة لقطة الـ259 جدولًا **zero-diff**، ومحفظة user 1 = 710.0. **لم يُنفَّذ أي commit.** التقرير: `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` + 3 ملفات evidence (`insurance-batch0a-evidence-{before,before2-funded-ghost-wallet,after}.txt`).

---

## [2026-09-22] Batch 0-B/0-B1 + 0-C — بوابة تسجيل الدعوات (invitations) + مفتاح إيقاف AI الطارئ (admin)

**invitations-batch0b-accept-invitation-anonymous-registration-gateway-closed [2026-09-21/22]** — ✅ **مُغلَق رسميًا** (نطاق: قراءة نقدية للاكتشاف الحرج التاريخي [0-B] + تصميم بوابة `register-with-invitation` [0-B الجزء 2، تصميم فقط، لم يُنفَّذ] + سدّ فوري لثغرة self-enrollment [0-B1، مُنفَّذ ومُتحقَّق حيًا، **مُلتزَم بواسطة صاحب المشروع يدويًا في commit `dde2a84`**]).

**0-B (قراءة نقدية):** الاكتشاف الحرج التاريخي (`CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، يوزر يتيم بلا محفظة عبر SAVEPOINT) **تأكَّد أنه مُصلَح فعليًا منذ commit `9f37201` [2026-08-18]** (بند `invitations-savepoint-leak` أعلاه) — الآلية المكتوبة في الملف الحرج (commit داخل SAVEPOINT) لم تعد موجودة. لكن القراءة كشفت ثغرة **أخطر وحيّة فعليًا**: `POST /invitations/{id}/accept` بلا مصادقة كان يقرأ التينانت من هيدر `X-Tenant-ID` (الافتراضي 1) ويُنشئ حسابًا كاملًا (يوزر+محفظة) في أي تينانت يختاره الطالب المجهول طالما وُجدت دعوة `SENT` فيه — **إعادة فتح جزئية لثغرة self-enrollment التي أغلقتها Phase 15** لمسار `/identity/register` تحديدًا، عبر طريق جانبي مختلف تمامًا. مُثبَتة حيًا لاحقًا في 0-B1.

**0-B الجزء 2 (تصميم فقط):** اقتُرح تصميم شامل لتحويل `accept_invitation` إلى بوابة (Gateway) نحو `POST /identity/register-with-invitation` الموجودة أصلًا (Phase 15) — ربط 1:1 بين دعوة CRM ودعوة هوية عبر عمود جديد `identity_invitation_id`، سرّ الرابط يُصدَر عند الإرسال لا عند القبول، حدث Celery حرج للإكمال بعد التسجيل. **5 مراحل مخطَّطة، لم يُنفَّذ منها إلا المرحلة 1 (أدناه)؛ المراحل 2-5 (الربط، الإكمال، الواجهة، ذرّية `register()`) لم تُفتح بعد.**

**0-B1 (مُنفَّذ، commit `dde2a84`):** المرحلة 1 فقط — سدّ الثغرة فورًا:
- **D-A:** `accept_invitation` بلا مستخدم مصادَق **لا تنشئ حسابًا ولا تبحث عن الدعوة** — تُرجع `401` + `WWW-Authenticate: Bearer` + `code=REGISTRATION_VIA_INVITATION_REQUIRED`، بجسم متطابق بايت-ببايت لدعوة موجودة/غير موجودة (بلا enumeration)، وهيدر `X-Tenant-ID` يُتجاهَل بالكامل.
- **D-B:** المسار المسجَّل يستخدم `current_user.tenant_id` حصريًا (لا الهيدر ولا الجسم) — دعوة تينانت آخر تُرجع `404`.
- **D-C:** حُذفت `_create_user_from_invitation` وكلمة المرور الافتراضية `"TempPass123!"` نهائيًا.
- حُذف `tests/test_invitations_savepoint_leak.{py,md}` (آليتهما القديمة انتهت فعليًا) وأُضيف `tests/test_invitations_accept_gateway.py` (11 اختبارًا).

**تحقق حي قبل/بعد (HTTP حقيقي):** قبل الإصلاح: مجهول + هيدر تينانت 16 على دعوة `SENT` جديدة → `200`، أُنشئ يوزر+محفظة+lead+interaction في تينانت 16 بلا أي مصادقة؛ ومستخدم تينانت 1 + هيدر 16 → كتابة عبر المستأجرين مُثبَتة (والعكس). بعد الإصلاح: نفس السيناريوهات كلها → `401` (المجهول، جسم مطابق بايت-ببايت لموجود/غير موجود/توكن تالف) أو `404` (عبر المستأجرين)، **صفر يوزر/محفظة/lead/interaction جديد**؛ السيناريو المشروع (مستخدم مصادَق يقبل دعوة تينانته) ما زال ينجح (`200`، Lead CONVERTED، الدعوة ACCEPTED). تنظيف كامل بمعاملة واحدة + zero-diff على 259 جدولًا (باستثناء استعادة صريحة لثلاثة أعمدة `last_login_*` لصف الاختبار الموثَّق `774`).

**⚠️ استنتاج الوصولية الفعلية (يُصحِّح تقييم الخطورة الأولي):** الثغرة الأصلية **كامنة لا حية اليوم عبر الـAPI بالبيانات الحالية** — لا يوجد مسار API واحد ينتج دعوة بحالة `SENT` فعليًا (اكتُشف أثناء 0-B1 أن `PUT /invitations/{id}` **لا يحفظ شيئًا أصلًا** بسبب غياب `commit()`، بند `invitations-update-invitation-missing-commit-silent-write` تحت)؛ الاستغلال يتطلب دعوة `SENT` أُنشئت خارج الـAPI (ORM/سكربت) **و**مستأجرًا فعّل CRM. تصير حية فور وجود أي endpoint/سكربت إرسال. الإصلاح 0-B1 يمنعها بغض النظر عن ذلك.

**بنود جديدة (backlog، تُفصَّل تحت):** `invitations-update-invitation-missing-commit-silent-write`، `invitations-header-trusted-cross-tenant-endpoints` (تجميع: tracking/chat/rate-limit/idempotency/target_user_id). **مراحل 2-5 من تصميم البوابة (0-B الجزء 2) لم تُفتح كبند backlog منفصل — تبقى خطة مستقبلية موثَّقة في تقرير الجلسة فقط.**

التقرير: `.claude/reports/invitations-batch0b-critical-read-session-log.md` + `.claude/reports/invitations-batch0b1-close-hole-session-log.md` + 3 ملفات أدلة (`invitations-batch0b1-evidence-{before,after,cleanup}.txt`).

---

**admin-batch0c-ai-kill-switch-implementation [2026-09-22]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا** (نطاق: قراءة نقدية لدومين `admin` غير المسجَّل [0-C تشخيص] + تنفيذ كامل [الخيار B الموصى به] + تحقق حي + تنظيف + مجموعة انحدار 147 اختبارًا). **commit `319313b`.**

**التشخيص الأولي:** دومين `admin` كان يحوي ملفًا واحدًا فقط (`router.py`، 24 سطر) **غير مسجَّل في `main.py` إطلاقًا** (`admin_router` لا `router`، خلاف كل الدومينات الأخرى)، يكتب مفتاح Redis واحدًا (`system:ai_agents:suspended`, TTL=30 يومًا) **لا يقرأه أي كود في المشروع** ("write-only" — مؤكَّد بـ`grep` شامل). لو سُجِّل كما هو كان سيصبح "مفتاح موصول بلا شيء" — أخطر من غيابه (إحساس زائف بالأمان). المحرك (`AIEngine._call_model`) محاكاة بالكامل اليوم (مفاتيح API وهمية، `asyncio.sleep`)، وصفر تنفيذ وكيل سابق في `ai_task_logs` — فالحاجة غير عاجلة تشغيليًا لكنها **شرط مسبق قبل أي تفعيل لاستدعاء LLM حقيقي**.

**التنفيذ (القرارات D1-D5):** POST `/api/admin/system/toggle-ai-agents` (body `{suspend: bool}`) + GET `/api/admin/system/ai-agents-status`، مقصوران على `system_role ∈ {SUPER_ADMIN, EXECUTIVE_DIRECTOR}` **و** `current_user.tenant_id == settings.PLATFORM_TENANT_ID` (إعداد جديد، افتراضي 1، إلزامي صراحةً في الإنتاج — تدبير جديد ومستقل مفهوميًا عن `PUBLIC_REGISTRATION_TENANT_ID` رغم تساويهما اليوم). البوابة الفعلية عند أدنى 3 نقاط تنفيذ LLM: `AIEngine.generate` (أول سطر، خارج أي `try/except` يبتلعها)، `core/ai_engine.py` (مسار Gemini الأكاديمي، كود ميت فعليًا اليوم)، و`AIAgentsService.execute_agent_action` (قبل أي عمل DB). استثناء مخصص `AISystemSuspendedError` → `503 AI_SYSTEM_SUSPENDED` عبر معالج `SovereignError` العام بلا كود جديد. **القراءة تفشل مفتوحة (fail-open + سجل ERROR)** لو تعذّر Redis؛ **الكتابة تفشل مغلقة** (`503 KILL_SWITCH_STORE_UNAVAILABLE`) كي لا يظن المُشغِّل أن التبديل نجح وهو لم ينجح. المفتاح بلا TTL الآن (كان 30 يومًا — كان سيلغي الإيقاف الطارئ تلقائيًا وبصمت). حدث تدقيق `AI_KILL_SWITCH_TOGGLED` (user_id/tenant_id/الحالة السابقة والجديدة) يُسجَّل في اللوغر (لا جدول `audit_logs` — نفس قيد `audit_log()` الحالي في كل المشروع). `social`/`logistics`/`manufacturing`/`zamakana` عُدِّلت (حارس + استيراد فقط) لترفع `AISystemSuspendedError` بدل ابتلاعها في `except Exception` العام وإرجاع بيانات AI **مُختلَقة** أثناء الإيقاف (احتمال عطل ثابت، توقعات عشوائية...)؛ `tasks/agritech.py` يميّز الإيقاف بسطر log صريح مع الإبقاء على الفولباك الحتمي (تنبيه ري عاجل لا يُفقَد).

**تحقق حي (HTTP حقيقي، 127.0.0.1:8010):** قبل التسجيل: `POST /api/admin/system/toggle-ai-agents` → `404`؛ كتابة المفتاح يدويًا في Redis (`true`) لم تغيّر شيئًا في `/api/ai/chat` ولا `execute_agent_action` — **إثبات مباشر أن لا أحد كان يقرأ المفتاح**. بعد التنفيذ: مجهول → `401`؛ USER عادي → `403`؛ SUPER_ADMIN من تينانت 16 → `403` **والحالة لا تتغير**؛ superuser المنصة (تينانت 1) → `200` تفعيل، `TTL=-1`، `GET status` يعكس الحالة ومن/متى؛ أثناء التفعيل: `/api/ai/chat` و`POST /api/ai/agents/{id}/execute` → `503 AI_SYSTEM_SUSPENDED` **بصفر صف جديد** في `ai_task_logs`/`agent_approval_queue`؛ إلغاء التفعيل يعيد العمل الطبيعي. حدثا تدقيق (تفعيل/إلغاء) مؤكَّدان من السجل. 18 اختبار جديد (`tests/test_ai_kill_switch_implementation.py`) **passed**. تنظيف كامل بمعاملة واحدة + zero-diff على 259 جدولًا + فهارس Postgres (1877، نفس hash) + مفاتيح Redis (25→25).

**مجموعة انحدار 32 ملفًا/147 اختبارًا:** **144 passed · 2 xfailed · 1 failed** (فشل وحيد **مسبق وغير مرتبط**: حارس بنيوي قديم في `test_realestate_buy_fractional_ownership_invoice_ordering` — بند backlog منفصل `admin-kill-switch-realestate-invoice-ordering-guard-stale` تحت). **مجموعة الانحدار نفسها تركت أثرًا غير متوقَّع:** رصيد محفظتي حسابَي اختبار دائمَين (`wallets.id=41`/`45`) تغيّر أثناء التشغيل بلا سجل قيم سابقة يمكّن استعادة دقيقة (جدول `transactions` نفسه لم يتغيّر — لا فقد محاسبي حقيقي). **قرار المالك [2026-09-22]: تُترَك كما هي — لا استعادة (تخمين غير مسجَّل أسوأ من الإبقاء).**

**بنود جديدة (backlog، تُفصَّل تحت):** `admin-kill-switch-medical-flag-skipped-on-ai-failure` (🔴 أولوية عالية، سلامة طبية، مستقلة)، `admin-kill-switch-llm-activation-gate-open-items` (تجميع 11 بندًا صغيرًا)، `admin-kill-switch-regression-suite-side-effects` (تسريب أرصدة/طابور Celery/كاش من تشغيل الاختبارات نفسها، غير خاص بالـkill switch).

التقرير: `.claude/reports/admin-batch0c-kill-switch-session-log.md`.

---

## [2026-09-17] بند Backlog جديد — ✅ اتحل — `test-cleanup-notification-fk-violation-in-shared-helper`

**الوصف:** اكتُشف أثناء تحديث `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
ليتوقع نجاح كامل بدل الكراش القديم (راجع بند `backlog-realestate-ai-agent-exception-silently-swallowed`
أعلاه). الـhelper المشترك `_cleanup_users_and_finance` (`tests/test_saas_active_subscription.py`)
كان بيحاول `DELETE FROM users` مباشرة بعد حذف `Transaction`/`AuditLog`/`Wallet`،
**بدون حذف `Notification`** المرتبطة بالمستخدم أولًا — أي اختبار بيوصل
لمنطق بيستدعي `_send_notification()` (زي `buy_fractional_ownership`)
بيعمل صف `notifications` حقيقي، فمحاولة حذف الـuser بعدها بتفشل بـ
`ForeignKeyViolationError` (`notifications_user_id_fkey`). الاختبار
القديم عمره ما وصل لهذه النقطة (كان بيكراش بدري بالـTypeError القديم)،
فالباج ده كان كامن وغير مكتشَف من قبل.

**الإصلاح المُطبَّق:** إضافة `await db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))`
في `_cleanup_users_and_finance` قبل حذف `Wallet`/`User` — تعديل ميكانيكي
صرف على الـhelper المشترك، يفيد أي اختبار حالي/مستقبلي في نفس الملف
يستخدم نفس الدالة. تحقق حي: تشغيل الملف كامل (`4 passed`)، صفر
`ForeignKeyViolationError`.

**الحالة:** ✅ اتحل بالكامل [2026-09-17]. `.claude/reports/backlog-review-2026-09-16-session-log.md`.

## [2026-09-17] بند Backlog جديد — `test-savepoint-fragile-source-position-parsing`

**الوصف:** `tests/test_realestate_insurance_savepoint.py::_assert_invoice_after_commit_and_wrapped`
بتفحص *ترتيب النص المصدري* (source string position، عبر `inspect.getsource`
+ `str.index`) للتأكد إن `create_invoice()` جوه `try/except` بعد
`await self.db.commit()` (تحقق بند #11b) — بتفترض **try/except واحد بس**
بين `commit()` و`create_invoice()` (أول `try:`/أول `except` بعد الـcommit).

**الأثر المؤكَّد حيًا [2026-09-16]:** فشل `test_realestate_buy_fractional_ownership_invoice_ordering`
لأن جلسات لاحقة شرعية (`ai-agents-execute-action-fix`،
`backlog-realestate-ai-agent-exception-silently-swallowed`) ضافت
`try: await ai.execute_agent_action(...) except (NotFoundError,
PermissionDeniedError)... except Exception...` **قبل** try/except
الفاتورة (بعد نفس الـcommit()، لسبب شرعي تمامًا). دالة الفحص الساذجة
بتاخد أول try/except بس (بتاعة الـAI)، فبتقارن موضع `create_invoice()`
(في الزوج التاني) ضد `except` الزوج الأول → `assert` فاشلة رغم إن
الكود سليم 100% (تأكيد بالقراءة المباشرة: `create_invoice()` لسه فعليًا
جوه try/except خاصة بيها بعد `commit()`).

**الحل المتوقَّع:** تعديل `_assert_invoice_after_commit_and_wrapped`
لتبحث عن **زوج try/except يحتوي فعليًا** الـsnippet المطلوب (`create_invoice(`)
بدل افتراض إنه أول زوج بعد الـcommit — مثلًا: تلقيط كل مواضع `try:`
بعد الـcommit، واختيار أقرب واحد قبل موضع `create_invoice(` مباشرة،
مش أول واحد مطلقًا.

**الحالة:** 🟡 **مفتوح، أولوية منخفضة — الكود الإنتاجي سليم 100%، المشكلة
في منهجية فحص الاختبار بس.** توثيق فقط، لم يُصلَح بعد. `.claude/reports/backlog-review-2026-09-16-session-log.md` (قسم 8).

**تحديث [2026-09-23] — حالة ثانية:** `test_realestate_insurance_savepoint.py::test_tourism_sports_place_transfer_bid_invoice_ordering` يفشل الآن بنفس السبب بالضبط: commit `cc9e5c4` (B-E3) أضاف كتلة `if requires_medical_review: try: ... except Exception` بعد `commit()` وقبل try/except الفاتورة في `TourismSportsService.place_transfer_bid` (`tourism_sports/service.py` ~570-599)، و`create_invoice` نفسها لا تزال بعد `commit()` ومُغلَّفة بـtry/except خاصة بها (~601-612) — فشل كاذب، الكود الإنتاجي سليم. مُثبَت أنه مسبق (يفشل على HEAD) في جلسة `insurance-review-claim-double-payment-verification` (§14.3، §15.5). الحالة والأولوية بلا تغيير.

---

## [2026-09-17] `test_saas_active_subscription.py` — ✅ اتصلح بالكامل

**الملخص:** الملف كان فيه فشلان اثنان من الـ15 فشل الموروثة في baseline
مراجعة backlog [2026-09-16] (راجع القسم 8 من التقرير). الاتنان اتصلحوا
بالكامل اليوم:

1. `test_realestate_rent_unit_saas_check_passes` — إضافة `mr_usdt=Decimal("100")`
   لتمويل `tenant_user` + استخدام `landlord_id=47` (المالك الحقيقي
   المسجَّل، مش `landlord` عشوائي — راجع إغلاق
   `backlog-realestate-test-fixture-landlord-not-registered-land-owner`
   أعلاه).
2. `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` —
   تمويل `buyer` + استبدال `pytest.raises(TypeError, match="tenant_id")`
   القديم بتوقّع نجاح كامل (راجع تأكيد `backlog-realestate-ai-agent-exception-silently-swallowed`
   أعلاه) + `monkeypatch` لـ`create_invoice` (تفاديًا لبند
   `invoicing-generate-invoice-number-count-based-collision` المفتوح) +
   تحقق حي كامل لخصم الرصيد وسجل الملكية.

**اكتشاف جانبي أثناء الإصلاح:** باج تنظيف كامن في `_cleanup_users_and_finance`
(`notifications_user_id_fkey`) — راجع `test-cleanup-notification-fk-violation-in-shared-helper`
أعلاه، ✅ اتحل بالكامل.

**تحقق حي نهائي:** `pytest tests/test_saas_active_subscription.py` →
**`4 passed`** (كان `2 failed, 2 passed`). صفر مشاكل تالتة غير متوقعة.

## [2026-09-17] `academy-camera-single-section-consent-scenario-deferred` — ✅ محسوم للـpilot الحالي [2026-09-17]

**الوصف الأصلي:** أثناء تصميم كاميرات academy (راجع
`.claude/reports/unified-site-model-and-academy-camera-design-proposal.md`
و`.claude/reports/camera-implementation-step0-single-section-scenario.md`)،
اتكشف إن opt-out الحقيقي (رفض تسجيل الكاميرا) مستحيل عمليًا لو المدرسة
عندها section واحد بس لكل صف دراسي — الطالب الرافض مالوش فصل بديل
ينتقل له. الفحص وقتها أكّد إن السيناريو ده افتراض نظري بحت (صفر مدرسة
حقيقية onboarded، `AcademyCohort` صفر صف موجود، كل الـ9 enrollments
الحية `cohort_id = NULL`).

**القرار:** محسوم لصالح **الخيار الأصلي رقم 1 من التقرير، لكن بصيغة
مختلفة جوهريًا** — مش "قبول الكاميرا شرط إلزامي بعد التسجيل"، بل
**تصميم المدرسة نفسه قائم من الأساس على "فصول بكاميرات + فصول بدون"
كخيار (option) على مستوى الفصل نفسه**، يُحدَّد **قبل** أي تسجيل طالب
فيه — مش نقل اضطراري لاحق. بمعنى: المعضلة الأصلية ("مفيش فصل بديل")
لا تنطبق على حجم الـpilot الحقيقي المؤكَّد.

**حجم الـpilot المؤكَّد:** 14 مرحلة دراسية (KG1-2, ابتدائي1-6,
إعدادي1-3, ثانوي1-3) × حتى 5 فصول/مرحلة × كثافة 20-60 طالب/فصل — يعني
حتى ~70 فصل محتمل لمدرسة واحدة، **مش كلهم بالضرورة بكاميرا**.

**شرط تصميمي جديد ناتج عن هذا القرار (لازم يُضاف لتصميم `Site`/
`ClassroomCameraAnalysis` قبل أي migration):** حقل صريح (مثلًا
`has_camera_option`) على مستوى الـcohort/section أو `Site` نفسه، يحدد
**مسبقًا** هل الفصل ده "مخصَّص كاميرا" — **قرار إداري وقت إنشاء الفصل،
مش استنتاج لاحق من وجود بيانات `classroom_camera_analyses` مسجَّلة
فعليًا لهذا الفصل**. هذا يغيّر §1.3/§2.1 من مستند التصميم الأصلي (لسه
لم يُطبَّق — بانتظار migration الخطوة 2).

**الحالة:** ✅ محسوم للـpilot الحالي [2026-09-17]. التنفيذ الفعلي
(migration `Site` + الحقل الجديد) لسه لم يبدأ — الجلسة الحالية منتقلة
لتصميم device authentication (الخطوة 1 من خطة التنفيذ المتفَق عليها)
قبل أي migration.

**الحالة:** ✅ **الملف بالكامل سليم الآن.** `.claude/reports/backlog-review-2026-09-16-session-log.md`.

## [2026-09-17] ربط الأربعة دومينات بـ`Site` الموحّد (iot/manufacturing/agritech/health) — ✅ مكتمل بالكامل

**السياق:** الخطوة 3 من `.claude/reports/unified-site-model-and-academy-camera-design-proposal.md`
(§1.4) — ربط كل دومين له مفهوم "موقع فعلي" بـ`Site` الموحّد الجديد
(migration 057). نُفِّذت على 4 دومينات بالتتابع، بموافقة صريحة قبل كل
دومين. التقرير الختامي المجمَّع:
`.claude/reports/unified-site-model-four-domain-rollout-final-summary.md`.

| # | الدومين | الموديل | migration | النوع |
|---|---|---|---|---|
| 1 | `iot` | `SmartAsset` | 058 | استبدال كامل (`entity_id`/`location_gps` حُذفا) |
| 2 | `manufacturing` | `ManufacturingFacility` | 059 | استبدال كامل (`entity_id`/`location_gps` حُذفا، `real_estate_unit_id` بلا لمس) |
| 3 | `agritech` | `SmartFarm` | 060 | إضافة صافية (`land_asset_id`/`entity_id` الميت بلا لمس) |
| 4 | `health` | `HealthFacility` | 061 | إضافة صافية — استثناء موثَّق (`entity_id` FK حقيقي لـ`sovereign_entities_v2` عبر migration 052، بلا لمس) |

**سلاسل حذف throwaway قبل فرض `NOT NULL`** (بيانات constructor/regression
test مؤكَّدة، صفر بيانات إنتاجية، صفر إعادة إدراج): iot (1 صف)،
manufacturing (5 صفوف/4 جداول)، agritech (10 صفوف/10 جداول)، health (2
صف/5 جداول مفحوصة).

**فشل جديد وُجد وأُصلح (اختبارات لم تكن تمرّر `site_id` الإلزامي
الجديد):**
- `test_agritech_router_wiring.py::test_agritech_full_domain_flow_live`
- 5 ملفات health: `test_guardian_overview_endpoint_implementation.py`,
  `test_health_appointments_tenant_isolation_fix.py`,
  `test_health_entity_membership_full_implementation.py`,
  `test_health_nameerror_and_fee_ordering_fix.py`,
  `test_idempotency_truthy_bug_fix.py`

كل الإصلاحات كانت إضافة `Site` fixture + تمريرها + تنظيفها فقط — صفر
لمس لمنطق الاختبار الأصلي.

**تحقق نهائي:** pytest كامل بعد health → **`13 failed, 225 passed, 2
xfailed`** — مطابقة حرفية 100% مع baseline المعروف (نفس الـ13 اسم فشل
الموروثة، غير متعلقة بهذا المجهود). `app.domains.sites` تأكَّد شغّال بعد
كل الأربعة migrations.

**Backlog مفتوح ناتج عن هذه الجلسة:**

### `agritech-smartfarm-unused-entity-id-column`
`SmartFarm.entity_id` (nullable, بلا FK) عمود ميت 100% — غائب من
`SmartFarmCreate` schema، غير مُستخدَم في `service.create_farm()` ولا أي
مكان تاني. بموافقة المستخدم، تُرك بلا لمس عمدًا (نطاق agritech كان
"site_id فقط"). **الحالة:** 🟡 مفتوح، أولوية منخفضة — تنظيف مستقبلي منفصل
تمامًا عن مجهود Site.

---

## جلسة `academy-site-hierarchy-endpoints-implementation` (2026-09-17)

**الهدف:** endpoints لإدارة شجرة Site الأكاديمية (مدرسة → مرحلة → فصل)
فوق `app/domains/sites/models.py` (migration 057، كان صفر
service/repository/endpoint فعلي قبل هذه الجلسة — راجع الجلسة التصميمية
السابقة read-only، صفر كود).

**تحقق قبل التنفيذ (صحّح افتراض تصميمي):**
- `SiteType` مؤكَّد `native_enum=False` — إضافة `GRADE_LEVEL`/`CLASSROOM`
  تمت بصفر migration (VARCHAR بلا CHECK constraint).
- ⚠️ الافتراض الأصلي إن `ClassroomCameraAnalysis.site_id` موجود غلط —
  الموديل الفعلي (`academy/models.py:487-507`) بيربط بـ`org_entity_id`
  بس، **صفر عمود `site_id`** أصلًا. رُبط هذا الجزء بالكامل — لو لزم مستقبلًا
  محتاج migration منفصلة لإضافة العمود، خارج نطاق هذه الجلسة عمدًا.
- نمط الصلاحيات مؤكَّد: `get_current_superuser` (شرط
  `system_role in [SUPER_ADMIN, EXECUTIVE_DIRECTOR]`) هو نفسه المستخدَم
  فعليًا لكل endpoint إنشاء هرمية تنظيمية في academy
  (`/tenants`, `/entities`, `/tracks`, `/cohorts`) — اتّبع بالحرف، صفر
  نمط صلاحيات جديد.

**نُفِّذ (POST+GET فقط، بقرار نطاق صريح — DELETE وربط
`classroom_camera_analyses.site_id` مؤجَّلان عمدًا):**
- ملفات جديدة: `app/domains/sites/schemas.py`,
  `app/domains/sites/repository.py`, `app/domains/sites/service.py`
  (`SiteService` عام قابل لإعادة الاستخدام لأنواع `Site` تانية مستقبلًا —
  مش خاص بـacademy فقط).
- `app/domains/sites/models.py`: أُضيف `SiteType.GRADE_LEVEL` و
  `SiteType.CLASSROOM` (صفر migration، راجع فوق).
- `app/domains/academy/router.py`: 6 endpoints جديدة تحت prefix
  `/academy` الموجود (`POST/GET /sites`,
  `POST/GET /sites/{school_id}/grades`,
  `POST/GET /sites/{grade_id}/classes`) — تحقق `parent.site_type` عند كل
  إنشاء (`ValidationError` → 422 لو أصل من نوع خطأ، `NotFoundError` → 404
  لو الأصل مش موجود).
- `max_capacity` للفصل (validation 20-60 عبر Pydantic `Field`) اتخزّن
  جوّه `Site.geo_metadata` (JSONB) — **قرار نطاق واعٍ**: صفر عمود مخصص
  بصفر migration جديدة في هذه الدفعة، رغم إن اسم العمود "geo_metadata"
  مش دقيق دلاليًا لبيانات غير جغرافية. لو ده اتلاحظ كإشكال مستقبلًا،
  الحل الأنظف عمود `capacity` مخصص عبر migration منفصلة.

**اختبار حي وُجد فيه باج حقيقي في نمط الاختبار نفسه (مش في الكود
المُنتَج):** `test_academy_site_hierarchy_endpoints_implementation.py`
— أول تشغيلة كاملة كشفت فشل جديد واحد (`test_list_endpoints_scoped_by_tenant_and_parent`،
`AttributeError: 'NoneType' object has no attribute 'send'` / `RuntimeError:
Event loop is closed`) بيظهر بس لما الاختبارات تتشغّل بالتتابع، مش منفردة.
السبب: اختبار سابق في نفس الملف كان بيفتح `AsyncSessionLocal()` يدويًا
بلا طلب fixture الـ`db` من `conftest.py` — فـ`engine.dispose()` الإلزامي
على Windows (موثَّق في `conftest.py:19-25`) ما كانش بيتنفّذ، فسابت
connections متسربة من event loop قديم للاختبار اللي بعده. الإصلاح: خلي
الاختبار يطلب fixture الـ`db` بدل `AsyncSessionLocal()` يدوي.

**تحقق نهائي:** pytest كامل (باستثناء
`test_affiliate_service_missing_methods.py` collection error المعروف
مسبقًا، غير متعلق) → **`13 failed, 229 passed, 2 xfailed`** — مطابقة
حرفية 100% مع baseline المعروف (نفس الـ13 اسم فشل الموروثة بالحرف). صفر
regression. الجلسة توقفت هنا بقرار المستخدم — زرع بيانات pilot فعلية أو
ربط الكاميرا مؤجَّلان لموافقة منفصلة.

**Backlog مفتوح ناتج عن هذه الجلسة:**

### `site-classroom-max-capacity-in-geo-metadata-field`
`max_capacity` للفصول (`Site.site_type=CLASSROOM`) متخزّنة حاليًا جوّه
`Site.geo_metadata` (JSONB، `{"max_capacity": N}`) بدل عمود مخصص —
موديل `Site` الأصلي (migration 057) ما فيهوش عمود `capacity`، والقرار
كان تفادي migration جديدة لحقل واحد في دفعة POST+GET هذه الجلسة. اسم
الحقل "geo_metadata" غير دقيق دلاليًا لبيانات غير جغرافية زي السعة.
**الحالة:** 🟡 مفتوح، أولوية منخفضة — يستاهل migration منفصلة مستقبلية
لعمود `capacity` مخصص لو الفريق حاب حل أنظف. راجع
`.claude/reports/academy-site-hierarchy-endpoints-implementation-session-log.md`
§2.