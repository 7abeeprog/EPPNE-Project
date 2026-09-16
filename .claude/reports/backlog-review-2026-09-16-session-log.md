# Backlog Review Session — 2026-09-16

Read-only review of old open PROGRESS_LOG.md backlog items, one at a time. No code edits made in this session unless explicitly noted.

## 0. البيئة والـ baseline

- Docker: `eppne_db` (Postgres, port 5435→5432, healthy), `postgres-eppne` (5433→5432), `redis` (6380→6379) — كلهم Up.
- DATABASE_URL الفعلي المستخدم: `postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2` (container `eppne_db`).
- `pytest` عادي (بدون `--ignore`) فشل بالكامل في مرحلة الـ collection:
  - `ImportError: cannot import name 'ActionCommission' from 'app.domains.affiliate.models'` في `tests/test_affiliate_service_missing_methods.py:87`.
  - ده نفس الـ side-finding المسجل سابقًا من جلسة tourism_sports entity-membership (لم يُصلح بعد).
- بعد استبعاد الملف ده فقط (`--ignore=tests/test_affiliate_service_missing_methods.py`, بدون أي تعديل كود):
  - **النتيجة: 223 passed, 15 failed, 2 xfailed, 284 warnings in 804.71s**
  - الفشل موزّع على:
    - `test_realestate_insurance_savepoint.py` (1)
    - `test_saas_active_subscription.py` (2 — realestate rent/buy saas-check)
    - `test_user_repository_get_by_id_audit.py` (10)
    - `test_user_repository_get_user_audit.py` (2)
  - هذا هو الـ baseline الحالي قبل أي عمل في هذه الجلسة.

## 1. finance-transfer-hardcoded-system-account-real-fund-risk

**كل الأوامر التالية read-only فقط، بدون أي write:**

- `SELECT id, balances FROM wallets WHERE id=39;`
  → `{"MR_USDT": 771.0}`
  ⚠️ الرصيد **تغيّر** من 875.0 المذكور في البند الأصلي إلى **771.0** — أي إن فيه تحويلات فعلية حصلت على الحساب ده بعد كتابة البند. لسه فلوس حقيقية موجودة وعرضة للتحويل الخاطئ.

- `SELECT id, email, created_at FROM users WHERE id=1;`
  → `id=1, email=p_system_treasury@example.com, created_at=2026-08-14 00:12:00`
  ✅ نفس الحساب المذكور في البند الأصلي، لسه موجود.

- `grep -n "sender_id=1" commerce/service.py affiliate/service.py iot/service.py`
  → **لا نتائج**. البحث الموسّع أظهر إن الثلاث ملفات دول **اتصلحوا فعلاً**:
  - `commerce/service.py:175,528` → `sender_id=customer_id` / `sender_id=order.customer_id` (مش hardcoded خالص)
  - `affiliate/service.py:577` → `sender_id=cast(int, system_account.id)` عبر `get_or_create_system_account(self.db, self.tenant_id)` (tenant-scoped)
  - `iot/service.py:215` → نفس النمط، `system_account` من `get_or_create_system_account(self.db, tenant_id)`

  **لكن** grep موسّع على `app/domains/` وجد نفس النمط لسه حي في مكان **جديد** لم يكن مذكورًا في البند الأصلي:
  - **`app/domains/insurance/service.py:626`** — داخل `disburse_monthly_pensions()`:
    ```python
    tx = await finance.transfer(
        sender_id=1,
        receiver_email=await self._get_user_email(...),
        currency="MR_USDT",
        amount=pension.monthly_amount_mrusdt,
        notes=f"Pension payment for {pension.pension_type}"
    )
    ```
    الدالة دي بتتصل تلقائيًا (scheduled) لكل الـ tenants، ومفيش `get_or_create_system_account` مستخدم هنا — يعني كل معاش شهري بيتسحب فعليًا من محفظة `user_id=1` (نفس `wallets.id=39` أعلاه) بدون فحص tenant، بنفس خطورة البند الأصلي بالظبط لكن في دومين تاني.

**الخلاصة:** البند الأصلي (commerce/affiliate/iot) **تم إصلاحه بالفعل** في وقت سابق (غير مسجل باسم واضح في PROGRESS_LOG وقت كتابة هذا التقرير — يحتاج تأكيد لاحقًا من السجل الكامل). لكن **نفس فئة الخطر لسه حية** في `insurance/service.py:626` مع فلوس حقيقية (771.0 MR_USDT) في نفس حساب `user_id=1`. هذا اكتشاف جديد يستحق بند backlog منفصل.

**لم يتم أي تعديل كود.** في انتظار توجيهك لفتح بند جديد لـ insurance pension بخصوص هذا الاكتشاف.

## 2. invoicing-missing-rollback-on-exception-11b

**البند الأصلي** (PROGRESS_LOG.md سطر 123، [2026-08-18]): 8 دوال عبر 4 دومينات فيها `try/except Exception` حوالين `invoicing.create_invoice()` بتمسك الاستثناء وتسجّل اللوج **بدون `await self.db.rollback()`** — لو `create_invoice()` فشلت بخطأ DB حقيقي، الـsession تفضل `PendingRollbackError` وأي كود DB لاحق في نفس الدالة بيكراش فورًا.

**فحص حي للـ8 دوال — كلها لسه بنفس الشكل تمامًا، صفر إصلاح:**

| # | الدومين | الدالة | السطر | rollback() موجودة؟ |
|---|---|---|---|---|
| 1 | tourism_sports | `book_program` | service.py:225 (except) | ❌ لا |
| 2 | tourism_sports | `purchase_event_ticket` | service.py:384 (except) | ❌ لا |
| 3 | tourism_sports | `place_transfer_bid` | service.py:563 (except) | ❌ لا |
| 4 | realestate | `buy_fractional_ownership` | service.py:380 (except) | ❌ لا |
| 5 | realestate | `rent_unit` | service.py:491 (except) | ❌ لا |
| 6 | insurance | `subscribe` | service.py:261 (except) | ❌ لا |
| 7 | insurance | `review_claim` | service.py:551 (except) | ❌ لا |
| 8 | zamakana | `pledge_time` | service.py:330 (except) | ❌ لا |

كل الـ8 بنفس النمط الحرفي: `await self.db.commit()` (للمورد الأساسي) ← `try: await invoice_service.create_invoice(...) except Exception as e: logger.error(...)` بدون rollback. البند لسه **مفتوح بالكامل**، مطابق تمامًا لما هو موثّق.

### تصميم الإصلاح المقترح (لم يُكتب — في انتظار الموافقة)

1. **التعديل الأساسي (8 مواضع):** إضافة `await self.db.rollback()` كأول سطر داخل كل `except Exception as e:` المحيط بـ`create_invoice()`، قبل `logger.error(...)`. تعديل ميكانيكي متطابق في الـ8 المواضع.

2. **التحقق الإضافي المطلوب (موثّق كشرط في البند الأصلي نفسه):** `rollback()` لوحدها غير كافية للتأكيد — تجربة سابقة موثقة في `transaction-savepoint-bug-session-log.md` أثبتت إن نداء ORM لاحق على نفس الـasync session بعد `rollback()` ممكن يفشل بـ`MissingGreenlet: greenlet_spawn has not been called` رغم نجاح الـrollback نفسه. لازم بعد التعديل:
   - اختبار حي واحد على الأقل (مقترح: `book_program` أو `pledge_time`، الأبسط) يفتعل فشل DB حقيقي داخل `create_invoice()` (مثلًا `UniqueViolationError` عبر تكرار `invoice_number`/`idempotency_key` متعمّد — مع الانتباه لبند `invoicing-generate-invoice-number-count-based-collision` المفتوح أصلًا، ممكن نستغله مباشرة كمُحفِّز طبيعي للفشل بدل تصنيع خطأ صناعي).
   - التأكد إن الكود اللي بعد الـexcept (تحديدًا `_store_idempotency()` والوصول لـ`.id` على الكائنات المُنشأة قبل الـcommit الأساسي) بينفّذ بنجاح فعليًا بعد الـrollback، مش بس إن `rollback()` نفسها ما رمتش استثناء.
   - لو `MissingGreenlet` أو أي خطأ تاني ظهر، الحل هيحتاج توسعة (مثلًا `await self.db.rollback()` + إعادة استخدام session جديد أو `expire_all()` بعد الـrollback) — قرار هيتاخد بعد نتيجة الاختبار الحي، مش قبله.

3. **النطاق:** التعديل مقصور على الـ8 مواضع دي فقط (نفس ملفات/دوال البند الأصلي بالحرف). صفر لمس لأي كود تاني، صفر تغيير في `invoicing/service.py` نفسها.

**لم يتم أي تعديل كود بعد.** في انتظار موافقتك على التصميم قبل التنفيذ، أو توجيه للبند التالي.

## 3. بنود مالية/بيانات من 19-25 أغسطس

- **`affiliate-get-referral-tree-multiple-results-on-multi-scope`** [2026-08-19] — موجود مرة واحدة بس في PROGRESS_LOG.md (سطر 141، مكان الاكتشاف الأصلي في جلسة `referral-system-multilevel-investigation`). **صفر ذكر لاحق** في أي مكان تاني بالملف، وصفر ملف في `.claude/reports/` بيذكر الاسم ده غير التقرير الأصلي نفسه (`referral-system-multilevel-investigation-session-log.md`). **لا يوجد أي تعديل لاحق موثّق — لسه مفتوح كما هو.**

- **`affiliate-commission-tiers-duplicate-global-null-gap`** [2026-08-25] — موجود مرة واحدة بس (سطر 147، جلسة `tenant-system-account-phase3-conversion`). نفس الحالة: **صفر ذكر لاحق** في الملف، وصفر ملف تقرير تاني بيشير له غير تقرير الاكتشاف الأصلي. **لا يوجد أي تعديل لاحق موثّق — لسه مفتوح كما هو.**

كلا البندين لسه بحالتهما الأصلية بدون أي إصلاح موثّق، حسب البحث في PROGRESS_LOG.md و`.claude/reports/` بالكامل.

## 4. البنود متوسطة الأولوية — فحص سريع (سطر واحد لكل بند)

1. **`ai-governance-check-and-consume-commit-inside-begin-nested`** — ✅ **مُغلَق رسميًا** [2026-09-01]، تقرير: `.claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md`.
2. **`invitations-chat-with-ai-reply-key-mismatch`** — 🔴 لسه موجود حرفيًا في الكود: `invitations/service.py:422` لسه بتقرأ `.get("reply", ...)` مش `.get("text", ...)`.
3. **`realestate-ai-governance-quota-not-enforced`** — 🔴 لسه موجود: `realestate/service.py:363` لسه `await self._check_ai_governance(...)` كـstatement مجرد بلا فحص القيمة المرجعة.
4. **`insurance-update-claim-permission-asymmetry`** — ✅ **مُغلَق بقرار مستخدم** [2026-09-04]: البقاء superuser-only، صفر تعديل كود (قرار مقصود، مش باج).
5. **`tourism-sports-transfer-repository-method-missing`** — ✅ **مُغلَق بتنفيذ حي** [2026-09-04] ضمن جلسة `category-b-decision-needed-triage`.
6. **`frontend-types-null-vs-undefined-mismatch-pattern`** — 🔴 لسه مفتوح: قرار نطاق صريح وقتها بإصلاح حقول محددة بس، والنمط العام (مثلاً `Lead`/`LeadCard`) متروك عمدًا بدون حل شامل.
7. **`agritech-phase2-frontend-gaps`** — 🔴 لسه مفتوح: مُصنَّف صراحة كـ"قرار كبير" وتُرك كـbacklog بقرار مستخدم [2026-09-04]، صفر تنفيذ.
8. **`update_bio_cohort_count-tenant-id-bug`** — ✅ **مُغلَق بتنفيذ فوري** [2026-09-04] ضمن نفس جلسة `category-b-decision-needed-triage`.
9. **`agritech-traceability-certificate-idor-defense-gap`** — 🟡 لسه مفتوح عمدًا: قرار مستخدم بالإبقاء كما هو (defense-in-depth غير عاجل)، يحتاج جلسة أمنية مخصصة لو حُسم لاحقًا.

**الخلاصة: 3 من 9 مُغلَقة (#1, #4, #5, #8 = فعليًا 4 مُغلَقة)، 5 لسه مفتوحة (#2, #3, #6, #7, #9).**

## 5. متابعة عاجلة على البند 1 — هل خطر `insurance/service.py:626` حي دلوقتي؟

**سؤال 1 — الجدولة:**
- `grep -rn "disburse_monthly_pensions"` على كل المشروع: استدعاء واحد بس، `insurance/router.py:358` (`POST /insurance/admin/disburse-pensions`، `get_current_superuser` + rate limit 5/60s).
- فحص `celery_config.py` (`beat_schedule` بالكامل، 6 مهام): صفر ذكر لـ pension/insurance disburse.
- صفر استخدام APScheduler/`BackgroundScheduler`/`add_job` في المشروع كله.
- **الجواب: مش مجدولة خالص.** endpoint يدوي admin-only بس، صفر تفعيل تلقائي.

**سؤال 2 — تاريخ التحويلات من wallet 39:**
- الفرق الكامل (875→771 = **104.0 MR_USDT** بالظبط) متفسّر 100%: **95 معاملة** في آخر 30 يوم، `62 REGTEST + 33 دفع فاتورة اختبار = 104.0`.
- **صفر معاملة بأي ذكر لـ"pension"/"معاش" في تاريخ الجدول بالكامل** (مش بس آخر 30 يوم).

**الخلاصة: الخطر كامن (latent) مش حي فعليًا.** الباج موجود بالكود لكن غير مستغَل، لأن مفيش محفّز تلقائي. فُتح بند backlog منفصل (`insurance-disburse-pensions-hardcoded-system-account`) وحُدِّث البند الأصلي (`finance-transfer-hardcoded-system-account-real-fund-risk`) إلى "✅ جزئيًا" في PROGRESS_LOG.md.

## 6. تنفيذ إصلاح invoicing rollback (البند 2 — بعد الموافقة)

**التعديل:** أُضيف `await self.db.rollback()` كأول سطر داخل كل `except Exception` المحيط بـ`create_invoice()` في الـ8 مواضع المتفَق عليها بالظبط:
- `tourism_sports/service.py:226,386,566` (book_program, purchase_event_ticket, place_transfer_bid)
- `realestate/service.py:381,493` (buy_fractional_ownership, rent_unit)
- `insurance/service.py:262,553` (subscribe, review_claim)
- `zamakana/service.py:331` (pledge_time)

**الاختبار الحي على `zamakana.pledge_time` (تينانت 16، مستخدم 774، بيانات throwaway):**
1. أُنشئت حملة throwaway نشطة (`campaign.id=6`).
2. اتحسب رقم الفاتورة المتوقَّع التالي (`INV-16-000003`) عبر استغلال بند `invoicing-generate-invoice-number-count-based-collision` المفتوح أصلًا، واتحقن فاتورة throwaway بنفس الرقم مسبقًا (`invoice.id=159`) لضمان تصادم `UniqueViolationError` حقيقي عند `create_invoice()`.
3. نودي `pledge_time(pledged_hours=15)` (فوق 10 ساعات، بيحفّز مسار الفاتورة) مع `idempotency_key` — **نجحت الدالة بالكامل ورجّعت `pledge.id=5`** رغم فشل `create_invoice()` بـ`IntegrityError` حقيقي جوه الـ`try`.
4. **تأكيد إن الجلسة صالحة فعليًا بعد الـrollback (مش بس إنها ما رمتش استثناء):** استعلام ORM جديد على نفس الـsession (`SELECT` على `TimePledge`) نجح بدون أي `MissingGreenlet`/`PendingRollbackError`.
5. **تأكيد إن `_store_idempotency()` نفذت بنجاح بعد الفشل:** الكاش احتوى `{'pledge_id': 5}` فعليًا.
6. **صفر `MissingGreenlet` أو أي خطأ تاني ظهر.** الإصلاح شغّال 100% في هذا السيناريو.
7. تنضيف throwaway كامل: `DELETE` مباشر لـ`time_pledges.id=5`، `planetary_campaigns.id=6`، `invoices.id=159` — تأكَّد بـ`SELECT count(*)=0` على الثلاثة.

**النتيجة: الإصلاح يعمل كما هو متوقَّع، بلا أي أثر جانبي مكتشَف.** الاختبار الحي اقتصر على `pledge_time` فقط (السيناريو المتفق عليه) — الـ7 المواضع الباقية بنفس النمط الميكانيكي المتطابق تمامًا، لم تُختبر حيًا فرديًا بقرار نطاق (تعديل ميكانيكي متطابق 100%، صفر فرق منطقي بين المواضع الثمانية).

## 7. تحديثات PROGRESS_LOG.md

- 4 بنود اتأكدت كمُغلَقة فعليًا وأُضيفت لها سطر "✅ اتحل [تأكيد 2026-09-16]" في مكانها الأصلي: `ai-governance-check-and-consume-commit-inside-begin-nested`، `insurance-update-claim-permission-asymmetry`، `tourism-sports-transfer-repository-method-missing`، `update_bio_cohort_count-tenant-id-bug`.
- البند الأصلي `finance-transfer-hardcoded-system-account-real-fund-risk` [2026-08-24] اتحدّث لـ**"✅ جزئيًا"** — موثَّق فيه إن `commerce`/`affiliate`/`iot` اتصلحوا فعليًا (غير موثَّق وقت الإصلاح)، والجزء المفتوح (`insurance/service.py:626`) موثَّق بالاسم الصريح جواه.
- بند backlog جديد منفصل اتفتح: `insurance-disburse-pensions-hardcoded-system-account` [2026-09-16] — تفاصيل الاكتشاف + نتيجة الفحص الحي (latent، مش مجدولة، صفر استغلال حتى الآن).

## 8. تصنيف الـ15 فشل من baseline البند 0 (read-only بالكامل، صفر تعديل كود)

### مجموعة 1: `test_user_repository_get_by_id_audit.py` (10 فشل)

**نمط واحد متكرر بالحرف في كل الـ10** — نفس الـtraceback بالضبط:
`assert any("referred_by" in r for r in cap.records)` بيفشل بـ`AssertionError` بسيط (مش `TypeError`/`AttributeError`).

**السبب الجذري:** الاختبارات كُتبت [2026-08-19] لما `User.referred_by` كان عمود *غير موجود إطلاقًا* — فصُممت عمدًا تتوقع `AttributeError` (يحتوي كلمة "referred_by") كدليل نجاح `get_by_id`. جه commit `2960d9d` [2026-09-07] وأضاف عمود حقيقي `User.referred_by_user_id` + أعاد بناء `_register_affiliate_commission` عبر الـ10 دومينات لتستخدمه ضمن نظام إحالة/عمولة موحَّد جديد كامل (`resolve_scope_id_for_member`, `ensure_referral_link`, `distribute_commissions_for_sale_event`) — تحقق حي مباشر أكّد نفس النمط في `zamakana`/`transport`/`insurance`/`manufacturing`. لمستخدم اختباري جديد (`referred_by_user_id IS NULL`)، الدالة بترجع بصمت **بلا أي log** (سلوك صحيح منطقيًا — مفيش محيل يستحق عمولة) → `cap.records` فاضية → فشل الـ`assert`.

**هل اتلمس قبل كده؟** ✅ نعم — **مُحقَّق ومُغلَق رسميًا بالفعل** [2026-09-07]، تفصيل كامل في `.claude/reports/affiliate-commission-registration-investigation-session-log.md` (11 صفحة، تحقق حي كامل بنفس النتيجة بالحرف)، ومسجَّل في PROGRESS_LOG.md سطر 2215: **"✅ اتحقَّق منه، لا حاجة لإصلاح كود"**. الـbacklog المتبقي (منخفض الأولوية، موثَّق هناك): تحديث الـ10 اختبارات لتعكس السلوك الجديد الصحيح.

**التصنيف: تغيير متعمد في سلوك من غير تحديث الاختبار.** ليس باج، الكود يعمل بشكل صحيح.

### مجموعة 2: `test_user_repository_get_user_audit.py` (2 فشل)

**نفس النمط بالحرف** (`employment`, `digital_twin`) — نفس `assert any("referred_by"...)` فاشل بنفس الشكل. تأكيد حي مباشر: كلا الملفين يستخدموا نفس `user.referred_by_user_id` + `resolve_scope_id_for_member`. **مرتبط 100% بنفس سبب المجموعة 1** — نفس commit `2960d9d`، نفس نمط الاختبار القديم، صفر سبب مختلف.

**التصنيف: تغيير متعمد في سلوك من غير تحديث الاختبار.** نفس تصنيف المجموعة 1 بالحرف.

### مجموعة 3: `test_realestate_insurance_savepoint.py` (1 فشل — `buy_fractional_ownership`)

**الـtraceback:** دالة مساعدة في الاختبار (`_assert_invoice_after_commit_and_wrapped`) بتفحص *ترتيب النص المصدري* (source string position) للتأكد إن `create_invoice()` جوه `try/except` بعد `commit()` (تحقق بند #11b). بتفترض **try/except واحد بس** بين `commit()` و`create_invoice()`. لكن جلسات لاحقة (`ai-agents-execute-action-fix`/`ai-governance-check-and-consume-begin-nested`) ضافت `try: await ai.execute_agent_action(...) except...` **قبل** try/except الفاتورة (نفس المكان، بعد commit() برضه، لسبب شرعي تمامًا: تفادي تعارض begin_nested). دالة الفحص الساذجة بتاخد أول `try:`/أول `except` بس (بتاعة الـAI)، فبتقارن موضع `create_invoice()` (اللي جوه try/except التاني) ضد `except` الأول → `assert 1277 < 928` يفشل.

**تأكيد حي بالقراءة المباشرة:** `create_invoice()` **لسه فعليًا** جوه `try/except` خاص بيها بعد `commit()` — الكود سليم 100%، نفس البنية اللي فحصناها وأصلحناها بـ`rollback()` في البند 2 فوق. المشكلة **في منهجية فحص الاختبار نفسها** (بحث ساذج عن أول try/except بدل الزوج الصحيح)، مش في الكود.

**هل مرتبط ببند مفتوح؟** غير مذكور بالاسم في أي بند backlog حاليًا، لكن مرتبط بنيويًا بـ`ai-agents-execute-action-fix`/`ai-governance-check-and-consume-begin-nested` (المُغلَقين رسميًا) — إضافتهم try/except جديد هي اللي كسرت افتراض الاختبار.

**التصنيف: تغيير متعمد (بنيوي، شرعي) من غير تحديث الاختبار** — تحديدًا: منهجية فحص الاختبار (source-position parsing) هشة أمام أي try/except إضافي يُضاف لاحقًا لأي سبب.

### مجموعة 4: `test_saas_active_subscription.py` (2 فشل — realestate rent/buy)

**السببان مختلفان جزئيًا:**

- **`test_realestate_rent_unit_saas_check_passes`:** `_create_funded_user(db, "p_regtest_saas9_re_tenant")` **بدون** تمرير `mr_usdt=` (القيمة الافتراضية `Decimal("0")`) — `tenant_user` (الدافع) بمحفظة فارغة، بينما `rent_unit` بتحاول تحوّل `monthly_rent=Decimal("50")` منه → `InsufficientBalanceError` حقيقية قبل أي وصول لمنطق `#9` المُختبَر أصلًا. **باج تافه وواضح 100% في fixture الاختبار نفسه** — نسيان تمرير `mr_usdt=` للمستخدم الدافع. **الإصلاح المقترح (لم يُنفَّذ):** إضافة `mr_usdt=Decimal("100")` (أو أي قيمة ≥50) لاستدعاء `_create_funded_user` الخاص بـ`tenant_user` في هذا الاختبار بس.

- **`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`:** نفس فئة المشكلة (`buyer` بدون `mr_usdt=`، `cost=50` من سعر الوحدة 500×10%) → `InsufficientBalanceError` قبل الوصول للسيناريو المقصود. **لكن هنا المشكلة مركّبة:** حتى لو اتحل التمويل، الاختبار بيتوقع `pytest.raises(TypeError, match="tenant_id")` عند `ai.execute_agent_action(...)` — تأكيد حي بالقراءة المباشرة: `execute_agent_action()` (`ai_agents/service.py:147-154`) **توقيعها الحالي بلا `tenant_id` إطلاقًا**، والاستدعاء في `buy_fractional_ownership` (`realestate/service.py`) بيمرر بالظبط نفس الكوارج الصحيحة (`agent_id`, `action_type`, `payload`, `executor_user_id`, `idempotency_key`) — **الـTypeError المتوقَّع في الاختبار لم يعد يحدث إطلاقًا**، لأن البج الأصلي (`ai-agents-execute-action-fix`) اتصلح فعليًا في جلسة لاحقة منفصلة. يعني الاختبار ده **مش مجرد fixture ناقصة** — premise الاختبار بالكامل (توقّع فشل معروف) بقى stale. **لو موّلنا الـbuyer بس، الاختبار هيفشل بشكل مختلف** (`pytest.raises` هيفشل لأن الاستثناء المتوقَّع مبيحصلش، والدالة على الأرجح هتنجح بالكامل).

**التصنيف:**
- `rent_unit`: **اختبار قديم بيانه/fixtures غير محدّثة** — تافه وواضح 100%، إصلاح مقترح جاهز، **لم يُنفَّذ، في انتظار موافقتك**.
- `buy_fractional_ownership`: **تغيير متعمد في سلوك من غير تحديث الاختبار** (مركّب مع نفس نوع باج الـfixture) — يحتاج قرار: هل نحدّث الاختبار ليتوقع نجاح كامل بدل `TypeError`؟ ده أكبر من تعديل سطر واحد، محتاج توجيهك.

## ملخص التصنيف النهائي (4 مجموعات، 15 فشل)

| المجموعة | العدد | التصنيف |
|---|---|---|
| `test_user_repository_get_by_id_audit.py` | 10 | تغيير متعمد في سلوك، مُحقَّق ومُغلَق رسميًا [2026-09-07] |
| `test_user_repository_get_user_audit.py` | 2 | نفس سبب المجموعة أعلاه بالحرف |
| `test_realestate_insurance_savepoint.py` | 1 | منهجية فحص الاختبار هشة أمام تغيير بنيوي شرعي لاحق |
| `test_saas_active_subscription.py` (rent_unit) | 1 | **فيكستشر تافهة وواضحة 100%** — إصلاح جاهز، ينتظر موافقة |
| `test_saas_active_subscription.py` (buy_fractional) | 1 | فيكستشر + premise الاختبار stale معًا — يحتاج قرار أكبر |

**صفر تعديل كود في هذه الجلسة الفرعية — فحص وتصنيف بس، حسب الطلب.**

## 9. تنفيذ إصلاحات المجموعة 4 (test_saas_active_subscription.py) — [2026-09-17]

### 9.1 `test_realestate_rent_unit_saas_check_passes` — ✅ مُصلَح بالكامل

**الإصلاح المتفق عليه:** إضافة `mr_usdt=Decimal("100")` لاستدعاء `_create_funded_user` الخاص بـ`tenant_user` (الدافع) في `tests/test_saas_active_subscription.py:188`.

**اكتشاف جانبي أثناء التنفيذ (مش جزء من الإصلاح الأصلي):** بعد حل مشكلة التمويل، ظهر فشل تاني مختلف تمامًا: `PermissionDeniedError("انت مش مالك الوحدة دي أو تابع لها")` من `_get_land_owner_for_unit`. السبب: الاختبار كان بينشئ `landlord` جديد عشوائي، لكن `EXISTING_LAND_ASSET_ID=1` (أصل مشترك حقيقي من جلسة سابقة، مش throwaway) له `owner_id=47` (`p_ctor_re_owner@example.com`) ثابت — و`rent_unit` بترفض أي `landlord_id` غير مالك الأرض فعليًا. **ده باج fixture إضافي، منفصل تمامًا عن نقص `mr_usdt=` الأصلي، لم يكن موثَّقًا قبل كده** (كان مُقنَّع بالكامل بسبب فشل التمويل الأسبق اللي كان بيكراش الاختبار قبل ما يوصل للنقطة دي أصلًا).

**القرار المُنفَّذ (بتوجيه المستخدم):** استخدام `landlord_id=47` (المالك الحقيقي الموجود) مباشرة بدل إنشاء `landlord` عشوائي — صفر لمس على `land_assets.id=1.owner_id` نفسه (أصل مشترك، قراءة فقط)، وصفر إضافة لـ`user_ids` الخاصة بالتنظيف (نفس نمط `_cleanup_users_and_finance` الموثَّق بالفعل في الملف لـ"مستقبِلين مشتركين... قراءة فقط من جلسات سابقة").

**النتيجة:** `1 passed` — الاختبار عدّى بالكامل، صفر مشاكل تالتة.

### 9.2 `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` — 🔴 متوقف، محتاج قرارك

**الإصلاحات المُنفَّذة:**
- إضافة `mr_usdt=Decimal("100")` لتمويل الـ`buyer`.
- استبدال `pytest.raises(TypeError, match="tenant_id")` بتوقّع نجاح كامل — بعد تأكيد بالقراءة المباشرة إن `execute_agent_action()` (`ai_agents/service.py:147-154`) توقيعها الحالي بلا `tenant_id` إطلاقًا (اتصلحت فعليًا في جلسة `ai-agents-execute-action-fix` منفصلة).
- إضافة تحقق حي: (1) الرصيد اتخصم بالظبط بـ`cost=50`، (2) سجل `PropertyOwnership` صح، (3) الفاتورة اتعملت بنجاح.

**نتيجة التشغيل — العملية التجارية نجحت فعليًا بالكامل** (دليل مباشر إضافي إن إصلاح rollback من البند 2 شغّال صح في سيناريو حقيقي غير مصطنع): الرصيد اتخصم، سجل الملكية اتعمل (`resource_id=127`). **لكن ظهرت مشكلتان منعوا عدي الاختبار:**

1. **بند backlog مفتوح أصلاً اشتغل حيًا:** `invoicing-generate-invoice-number-count-based-collision` — `create_invoice()` فشلت بـ`UniqueViolationError: invoice_number=INV-1-000015 already exists` (تينانت 1 له تاريخ حذف فواتير throwaway). اتمسكت بنجاح بـ`try/except`+`rollback()` (إصلاح البند 2 شغّال صح)، لكن **مفيش فاتورة اتعملت فعليًا** — الـassertion الجديدة "الفاتورة اتعملت بنجاح" **مستحيل تعدي لتينانت_id=1** طالما هذا البند مفتوح. مش عيب في إصلاح الـrollback نفسه.

2. **باج تنظيف منفصل، كامن، في `_cleanup_users_and_finance` (helper مشترك بالملف):** بتحاول `DELETE FROM users` قبل حذف `Notification` المرتبطة — `buy_fractional_ownership` بتستدعي `_send_notification()` دايمًا فبيتعمل صف notification حقيقي → `ForeignKeyViolationError`. الاختبار القديم عمره ما وصل للنقطة دي (كان بيكراش بدري بالـTypeError القديم)، فالباج ده كان كامن دايمًا وغير مكتشَف.

**تنظيف طارئ:** البيانات الـthrowaway المتخلّفة من التشغيل الفاشل (`users.id=7781`, `wallets.id=7418`, `transactions.id=594`, `audit_logs.id=592`, `notifications.id=306`) اتنضّفت يدويًا بالكامل بعد الفشل — تأكَّد بـ`SELECT count(*)=0` على الخمسة. `land_assets.id=1`/`users.id=47` لم يُلمَسا إطلاقًا.

**الخيارات المطروحة على المستخدم (في انتظار القرار):**
- بند (1) — الفاتورة: (أ) حذف assertion الفاتورة من الاختبار، (ب) `monkeypatch` لـ`create_invoice` زي `rent_unit` بدل الاصطدام بالبند المفتوح، أو (ج) إصلاح `invoicing-generate-invoice-number-count-based-collision` نفسه أولًا (خارج نطاق هذه الجلسة).
- بند (2) — التنظيف: إضافة `delete(Notification)` لـ`_cleanup_users_and_finance` (يفيد كل اختبارات الملف)، أو تنظيف محلي داخل هذا الاختبار بس.

**الحالة: الاختبار لسه فاشل، الكود المُختبَر (rollback fix) اتأكد إنه سليم 100% من نفس هذا التشغيل — المشكلة بالكامل في fixture/تنظيف الاختبار وبند backlog تاني مفتوح، مش في الكود الإنتاجي موضوع البند 2.**

## 11. حسم البند 9.2 — [2026-09-17]

**اكتشاف مهم:** كلا المشكلتين اللي وقفنا عندهم (fixture الـlandlord، وTypeError الstale في buy_fractional) **كانوا موثَّقين بالفعل مسبقًا** في PROGRESS_LOG.md كبنود backlog مفتوحة من [2026-09-08] (`backlog-realestate-test-fixture-landlord-not-registered-land-owner`، `backlog-realestate-ai-agent-exception-silently-swallowed`) — اكتشافنا الحي المستقل [2026-09-16] طابق التحليل الأصلي بالحرف 100%، وأكَّد صحته.

**0. تأكيد تسرب البيانات:** `SELECT count(*) FROM property_ownerships WHERE id=127` → `0`. صفر تسرب.

**1. حل مشكلة الفاتورة:** أُضيف `monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)` لـ`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` (نفس نمط `rent_unit`) — اتشال assertion وجود الفاتورة بالكامل (كان بيعتمد على نجاح `create_invoice()` الحقيقي، اللي بيصطدم ببند `invoicing-generate-invoice-number-count-based-collision` المفتوح لتينانت 1).

**2. إصلاح باج التنظيف المشترك:** `_cleanup_users_and_finance` (`tests/test_saas_active_subscription.py`) — أُضيف `delete(Notification)` قبل `delete(Wallet)`/`delete(User)`. باج كامن هيفيد أي اختبار حالي/مستقبلي بالملف.

**3. تحقق حي:**
- الاختبار المفرد: `1 passed` — الرصيد اتخصم بالظبط بـ`cost=50`، سجل الملكية اتسجل صح، صفر `ForeignKeyViolationError` في التنظيف.
- الملف كامل: `pytest tests/test_saas_active_subscription.py` → **`4 passed`** (كان `2 failed, 2 passed`).

**4. توثيق PROGRESS_LOG.md:**
- `backlog-realestate-test-fixture-landlord-not-registered-land-owner` → ✅ اتحل [تنفيذ 2026-09-17].
- `backlog-realestate-ai-agent-exception-silently-swallowed` → إضافة تأكيد "✅ تأكيد إضافي [2026-09-17]" (كان مُغلَق بالفعل من 2026-09-08، أضفنا ربط توقّع الاختبار الجديد).
- بند جديد: `test-cleanup-notification-fk-violation-in-shared-helper` — ✅ اتحل.
- بند جديد: `test-savepoint-fragile-source-position-parsing` (من القسم 8) — 🟡 مفتوح، توثيق فقط، أولوية منخفضة.
- بند ختامي: `test_saas_active_subscription.py` → ✅ اتصلح بالكامل [2026-09-17].

## 12. تشغيل الـsuite الكامل النهائي

**النتيجة:** `13 failed, 225 passed, 2 xfailed, 287 warnings in 703.25s` — تحسّن من `15 failed, 223 passed` (baseline البند 0) إلى `13 failed, 225 passed`. **بالظبط زي المتوقَّع — صفر مفاجآت، صفر فشل جديد.**

**الـ13 فشل المتبقي (كلهم موثَّقون ومصنَّفون بالفعل، مفيش أي جديد):**
- 10× `test_user_repository_get_by_id_audit.py` — مُحقَّق ومُغلَق رسميًا [2026-09-07]، الكود سليم.
- 2× `test_user_repository_get_user_audit.py` — نفس السبب بالحرف.
- 1× `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` — بند `test-savepoint-fragile-source-position-parsing` (مفتوح، توثيقي، الكود الإنتاجي سليم).

**اختفى تمامًا من قائمة الفشل:** كلا فشلي `test_saas_active_subscription.py` (rent_unit, buy_fractional_ownership) — الاثنان بقوا `passed`.

**خلاصة الجلسة الكاملة (من البند 0 لحد هنا):** باج حقيقي واحد أُصلح في الكود الإنتاجي (rollback fix، 8 مواضع)، بالإضافة لإصلاح fixtures/helpers الاختبارات (funding + landlord_id + notification cleanup)، بند backlog جديد فُتح لخطر latent (insurance pension)، وبند backlog جديد وُثِّق لمشكلة منهجية اختبار (savepoint parsing). صفر انحدار (regression) في أي مكان.
