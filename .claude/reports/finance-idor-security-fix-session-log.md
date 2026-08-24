# جلسة فحص IDOR/أمان عميق في `finance` — منبثقة من ثغرة `saas.pay_invoice`

**بدأ التسجيل:** 2026-08-24
**الحالة:** ✅ **مُغلَقة — توثيق فقط، صفر إصلاح كود.** القرار المعماري (`is_system` flag/حساب خزانة رسمي/مصدر بديل) مؤجَّل بالكامل لجلسة تصميم منفصلة، بنفس منطق قرارات الهرم التنظيمي السابقة — مش patch سريع في نص جلسة فحص.

**الملفات المرجعية المقروءة كاملة قبل البدء:**
- `.claude/reports/simpletenant-fix-session-log.md` (كامل، 610 سطر)
- `.claude/reports/saas-idor-fix-session-log.md` (كامل) — مصدر اكتشاف `sender_id`/`user_id` collision في `pay_invoice`
- `app/domains/finance/{router,service,repository,models,schemas}.py` (كاملة)
- استدعاءات `FinanceService`/`finance.transfer`/`get_or_create_wallet*` عبر **كل** `app/` (grep شامل، لا استثناء)

---

## 1) آلية `sender_id`/`receiver_id` في `finance` نفسها — دقيقة، صفر IDOR داخلي

`get_or_create_wallet_for_update(user_id)` (service.py:34) بتنادي `wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)` اللي بتفلتر بـ`WHERE Wallet.user_id == user_id AND Wallet.tenant_id == tenant_id` **حرفيًا** — و`create()` (repository.py:34) بتزرع صف جديد بنفس الزوج `(user_id, tenant_id)` **بلا أي تحقق إن `user_id` ده فعلاً بيخص `tenant_id` ده** (مفيش join أو فحص `User.tenant_id` وقت الإنشاء).

**النتيجة الحاسمة:** الدالة **مصممة تمامًا على افتراض إن الـcaller بيمرر `user_id` حقيقي** (مش `tenant_id`، ومش أي معرف تاني). `finance/router.py` نفسه ملتزم بالعقد ده 100% — **كل استدعاء لـ`sender_id=`/`user_id=` في الملف بيجي من `cast(int, current_user.id)` مباشرة** (صفر مصدر خارجي زي path/query/body param). `receiver_email` (مش `receiver_id`) هو مصدر تحديد المستلم، ومفلتر بـ`get_by_email(email, self.tenant_id)` + فحص `receiver.tenant_id != self.tenant_id` (مزدوج، لكن سليم) — **مفيش طريقة تحقن `receiver_id` مباشر عبر الراوتر أصلًا.**

**الخلاصة: `finance/router.py` نفسه — صفر IDOR كلاسيكي (لا في المرسل ولا في المستلم).** الخطر الحقيقي **مش في `finance` نفسها، لكن في أي كود خارجي بيسيء استخدام العقد ده** (بيمرر حاجة مش `user_id` حقيقي كـ`sender_id`).

---

## 2) جدول `finance/router.py` الكامل — 9 endpoints

| # | Endpoint | الدالة | current_user | مصدر tenant_id | مصدر sender/user_id | ملاحظة |
|---|---|---|---|---|---|---|
| 1 | `GET /finance/balances` | get_balances | active_user | `current_user.tenant_id` | `current_user.id` | 🟢 آمن |
| 2 | `POST /finance/transfer` | transfer_funds | active_user | `current_user.tenant_id` | `current_user.id` (sender) + `receiver_email` (مش ID) | 🟢 آمن — معاملة مالية حساسة لكن العقد سليم |
| 3 | `POST /finance/swap` | swap_currencies | active_user | `current_user.tenant_id` | `current_user.id` | 🟢 آمن |
| 4 | `GET /finance/history` | get_history | active_user | `current_user.tenant_id` | `current_user.id` | 🟢 آمن (فلتر `user_id`+`tenant_id` مزدوج في الـrepo) |
| 5 | `GET /finance/admin/crypto-mode` | get_crypto_mode | **بلا مصادقة إطلاقًا** | `1` هاردكودد (غير مستخدَم فعليًا) | N/A | 🟡 بالتصميم (تعليق صريح بالكود "endpoint عام قراءة فقط") — `SystemState` صف عام مفرد بلا `tenant_id` أصلًا، فالهاردكود بلا أثر فعلي. **يستاهل تأكيد صريح من المستخدم إنه مقصود** (بيانات حساسة: `max_supply`) |
| 6 | `POST /finance/admin/crypto-mode` | set_crypto_mode | **superuser** | `current_user.tenant_id` | `current_user.id` (audit فقط) | 🟢 آمن |
| 7 | `POST /finance/admin/exchange-rates` | set_exchange_rates | superuser | `current_user.tenant_id` | نفس الشيء | 🟢 آمن |
| 8 | `POST /finance/admin/mint` | mint_funds | **superuser** | `current_user.tenant_id` | `current_user.id` (admin_id = المُستلِم) | 🟢 آمن — لكن ⚠️ **`mint_currency` بيعمل `db.commit()` صريح جوه `service.py:309` رغم إنها مش جوه `begin_nested()` — نمط مختلف عن باقي الدوال، يستاهل مراجعة إضافية (خارج IDOR، أقرب لفئة `cancel_subscription` silent-write لكن معكوسة: هنا فيه commit صريح فعلاً، فمفيش خطر silent-write هنا تحديدًا. موثَّق فقط للانتباه) |
| 9 | `POST /finance/admin/max-supply` | set_max_supply | superuser | `current_user.tenant_id` | نفس الشيء | 🟢 آمن |

**لا يوجد أي endpoint في `finance/router.py` بمستوى `active_user` بلا ownership check حقيقي، ولا أي مصدر `tenant_id`/`user_id` من مصدر خارجي غير `current_user`.** هذا الدومين **نفسه** لا يكرر باج `SimpleTenant`/IDOR الكلاسيكي المكتشف في `academy`/`commerce`/`saas`/`sovereign_entities`.

---

## 3) 🔴🔴 الاكتشاف الحقيقي — فئة "sender_id مش user_id حقيقي" منتشرة في **9 مواضع خارج finance**، عبر 7 دومينات

جرد شامل (`grep` لكل استدعاءات `finance.transfer(`/`FinanceService(` عبر `app/` بالكامل، **قراءة سياق كل موضع يدويًا** — مش استنتاج آلي) كشف النمط ده بيتكرر في **3 أنماط فرعية مختلفة**، كل واحد بمستوى خطورة مختلف:

### النمط أ — `tenant_id` بدل `user_id` (نفس باج `saas.pay_invoice` بالحرف)
| الموقع | السطر | القيمة الممرَّرة كـ`sender_id` | ملاحظة |
|---|---|---|---|
| `saas.pay_invoice` | `service.py:309` | `self.tenant_id` | **موثَّق مسبقًا** في `saas-idor-fix-session-log.md` (محجوب بانحراف schema `idempotency_key`) |
| `saas.process_auto_renewals` | `service.py:169` | `target_tenant` | **نفس الباج بالحرف، نفس الدالة الأصل تقريبًا** — موثَّق مسبقًا كجزء من نفس البند، **لكن لم يُختبَر حيًا لوحده** |

### النمط ب — معرف "نظام" هاردكودد حرفي (`0` أو `1`) بدل `user_id` حقيقي — **جديد كليًا، غير موثَّق في أي تقرير سابق**
| الدومين.الدالة | السطر | القيمة | التأثير |
|---|---|---|---|
| `social.subscribe_group_to_plan` | `service.py:633` | `sender_id=0` | `user_id=0` على الأرجح غير موجود في `users` (PK يبدأ من 1) → `wallet_repo.create(user_id=0, ...)` هيفشل بـ`IntegrityError` (FK `users.id`) لكل محاولة اشتراك جماعي — **يبدو feature معطوبة بالكامل، مش IDOR، لكن أثر وظيفي حرج** |
| `commerce.release_commissions` | `service.py:303` | `sender_id=1` | ⚠️ **الأخطر — تأكَّد حيًا (§4) إن `user_id=1` مستخدم حقيقي موجود بمحفظة فعلية برصيد حقيقي** |
| `affiliate.withdraw_commissions` (تقريبي، بحاجة تأكيد اسم الدالة الدقيق) | `service.py:477` | `sender_id=1` | نفس الخطر بالضبط |
| `iot.settle_carbon_credits` (تقريبي) | `service.py:213` | `sender_id=1` | نفس الخطر بالضبط |

**التحليل:** الثلاثة (`commerce`/`affiliate`/`iot`) بيستخدموا `sender_id=1` كتمثيل لـ"حساب النظام/الخزانة" — **لكن `finance` معندهاش مفهوم "حساب نظام" مخصَّص أصلًا** (لا عمود `is_system` في `Wallet`، ولا استثناء في `get_or_create_wallet_for_update`). النتيجة: أي دالة من التلاتة دي، لو اتنفذت في أي تينانت فيه مستخدم حقيقي بمعرف `1`، هتخصم فلوس حقيقية من محفظة ذلك المستخدم **بلا علمه أو موافقته** — تحويل الأموال بيتحدد بمعرف عددي هاردكودد في الكود، مش بحساب نظام مخصَّص فعليًا.

### النمط ج — `user_id`/معرف حقيقي مُمرَّر بشكل صحيح (23 موضع باقي) — 🟢 لا خطر من هذه الفئة
كل باقي المواضع (`transport`, `tourism_sports`, `health`, `digital_twin`, `tenders_auctions`, `sovereign_entities` [2], `service_marketplace` [3], `realestate`, `projects`, `commerce.checkout`, `academy.enroll`, `invoicing.update_invoice_status`, `invitations.create_campaign`, `employment` [tasks], `billing` [tasks]) بتمرر `sender_id` من متغير مُشتَق فعليًا من `current_user.id`/كائن مستخدم حقيقي مُحمَّل من الـDB (زي `bidder_id`, `admin_user_id`, `from_representative_id`, `contributor_id`...) — **صفر دليل تصادم من هذه الفئة، بمراجعة يدوية لكل موضع.**

---

## 4) 🔴🔴 تحقق حي (SELECT فقط، صفر تعديل) — الخطر مؤكَّد حقيقي، مش نظري

```sql
SELECT id, email, tenant_id FROM users WHERE id IN (0,1,2);
--  1 | p_system_treasury@example.com | 1
--  2 | p0smoke_b68d8b18@example.com   | 1
-- (id=0 غير موجود، كما متوقَّع)

SELECT id, user_id, tenant_id, balances, is_frozen FROM wallets WHERE user_id IN (0,1,2);
-- id=39 | user_id=1 | tenant_id=1 | balances={"MR_USDT": 875.0} | is_frozen=NULL
```

**دلالة حرجة:** `user_id=1` (تينانت1) **موجود فعليًا وله محفظة حقيقية برصيد 875.0 MR_USDT حاليًا في قاعدة البيانات المستخدَمة عبر كل الجلسات (`eppne_v2`).** بريده `p_system_treasury@example.com` — تسمية توحي بإنه **اتعمل عمدًا كـ"حساب خزانة نظام" في جلسة سابقة** (نمط بادئة `p_` المستخدَم لبيانات throwaway في كل التقارير المرجعية)، **لكنه لم يُوثَّق كقرار تصميمي رسمي في أي تقرير مقروء حتى الآن**، ولسه موجود وبرصيد غير صفري.

**⚠️ هذا يعني:** أي تنفيذ حي لـ`commerce.release_commissions`/`affiliate.withdraw_commissions`/`iot` (النمط ب فوق) داخل تينانت1 **هيخصم فعليًا من رصيد حقيقي موجود دلوقتي (875.0 MR_USDT)** — مش بيانات throwaway معزولة زي باقي التحققات الحية السابقة. **لم أنفّذ أي استدعاء حي لأي من الدوال التلاتة دي — التحقق اتوقف عند `SELECT` فقط بالضبط زي ما طلبت ("صفر تنفيذ فوري").**

**سؤال مفتوح يستاهل توجيهك قبل أي حركة:** هل `p_system_treasury@example.com` (id=1) **قرار تصميمي مقصود** (حساب خزانة رسمي، ولو كده يستاهل توثيق رسمي + حماية خاصة زي `is_system` flag)، ولا **بقايا بيانات throwaway من جلسة سابقة كان المفروض تتنضف** ولسه عالقة برصيد حقيقي بيُستخدَم الآن كـsystem account بالصدفة/العرف بدل التصميم؟ الفرق ده بيغيّر تصنيف الخطر بالكامل (باج تصميمي خطير لو الحساب حقيقي وعليه اعتماد ضمني، أو تلوث بيانات لو مخلّف من اختبار).

---

## 5) ما لم يُنفَّذ بعد (بانتظار توجيهك)

- **لا تحقق HTTP حي على أي من المواضع التسعة** (النمط أ+ب) — بما فيها `saas.process_auto_renewals` اللي ممكن تتحقق منفصلة عن `pay_invoice` (نفس انحراف schema `idempotency_key` هيحجبها للأسف، غالبًا بنفس الطريقة).
- **لا تأكيد لأسماء الدوال الدقيقة** في `affiliate.py`/`iot.py` (استنتجتها من السياق المقروء، مش من توقيع الدالة الكامل — يحتاج قراءة كاملة للدالتين لو قررنا نكمل عليهم).
- **لا اقتراح إصلاح** لأي من الأنماط التلاتة — القرار التصميمي الصحيح (مين المصدر الحقيقي لـ"حساب النظام"؟ عمود `is_system` جديد؟ حساب خزانة مُدار رسميًا؟) يحتاج نقاش منفصل قبل أي ديف.

---

## 5.5) فحص إمكانية التحقق الحي الآمن (begin/rollback) لنمط ب — النتيجة: **مستحيل بلا لمس الكود، توقفت زي ما وجّهت**

بطلبك الصريح: قبل أي استدعاء حي لأي من الثلاثة (`commerce.release_commissions`, `affiliate.withdraw_commissions`, `iot.settle_carbon_credits`) — فحصت (قراءة فقط) هل الدالة تسمح بلف الاستدعاء كله بـ`transaction` خارجية أقدر أعمل عليها `ROLLBACK` بدل `commit`، ولا فيها `commit()` داخلي غير قابل للف حوله. **النتيجة: الثلاثة كلهم عندهم `commit()` داخلي غير مشروط، مباشرة جوه جسم الدالة نفسها (أو جوه repository method بتتنادى من جواها)، بلا أي طريقة للتحكم في نقطة الـcommit من برّه بدون تعديل كود:**

| الدالة | مكان الـ`commit()` الداخلي | التفصيل |
|---|---|---|
| `commerce.release_commissions` | `commerce/repository.py:264` — **جوه `WalletRepository`-مماثل، method `release_commission()` المنادى من جوه اللوب في `service.py:310`** | تعليق صريح موجود بالفعل في الكود (`repository.py:256-258`): *"WARNING: هذا الـcommit() بيغطي كمان كتابة finance.transfer() جوه service.release_commissions"* — يعني الـcommit ده بيغطي `finance.transfer()` (اللي جوه `begin_nested()` بتاعها الخاص) **كمان**. أول commission بس هيكفي عشان يلتزم الخصم من `user_id=1` نهائيًا **قبل ما الدالة كلها ترجع أصلًا**. |
| `affiliate.withdraw_commissions` | `affiliate/service.py:509` — **آخر سطر في الدالة نفسها، بعد الخروج من `begin_nested()`** | `commit()` صريح ومباشر جوه جسم `withdraw_commissions()` نفسها، بلا أي شرط. |
| `iot.settle_carbon_credits` | `iot/service.py:244` — **آخر سطر في الدالة نفسها، بعد الخروج من `begin_nested()`** | نفس النمط بالحرف — `commit()` صريح جوه جسم الدالة، قبل ما ترجع. |

**الخلاصة الحاسمة:** الثلاثة كلهم **مش مجرد `begin_nested()` (savepoint) قابل للتراجع من برّه** — كل واحد فيه `self.db.commit()` **صريح وغير مشروط** بيتنفذ **جوه** الدالة المشبوهة نفسها (أو جوه استدعاء داخلي منها) قبل ما الـcontrol يرجع لأي كود مستدعي. بمجرد ما أنادي أي واحدة من الثلاثة دي، مفيش أي `ROLLBACK` بعد كده من أي مكان تاني هيقدر يلغي الأثر — الالتزام (commit) بيحصل **من جوه الدالة نفسها**، مش من مستدعيها.

**تطبيقًا لتوجيهك الصريح:** *"لو الدالة بتعمل commit داخلي مش قابل للف حوله بـROLLBACK من برّه — وقف واكتفِ بالتوثيق النظري + دليل SELECT الحالي، بلا أي استدعاء حي إطلاقًا."*

✅ **توقفت بالكامل. صفر استدعاء حي لأي من الثلاثة. الإثبات مقصور على:**
1. القراءة الثابتة للكود (§3، نمط ب) — تأكيد إن `sender_id=1`/`sender_id=0` هاردكودد حرفيًا في الكود.
2. دليل `SELECT` المباشر (§4) — تأكيد إن `user_id=1` حقيقي وله محفظة برصيد فعلي 875.0 MR_USDT.

**هذا كافٍ لإثبات الخطر بثقة عالية جدًا (مش استنتاج نظري بحت) بلا أي مخاطرة على الرصيد الحقيقي** — الكود بيقرأ حرفيًا، والبيانات الحية بتأكد وجود ضحية محتملة حقيقية، لكن **صفر تنفيذ فعلي حصل أو هيحصل** على أي من الدوال التلاتة في هذه الجلسة.

---

## 6) أسئلة القرار — بانتظار توجيهك قبل أي خطوة تالية

**س1:** هل نكمل تحقق حي (HTTP + throwaway data معزولة تمامًا عن `user_id=1`) على **نمط أ** بس (`saas.process_auto_renewals`) بافتراض إنه هيتحجب بنفس انحراف الـschema، كخطوة توثيق فقط؟

**س2:** بخصوص **نمط ب** (`commerce.release_commissions`, `affiliate`, `iot` — `sender_id=1` هاردكودد على حساب حقيقي برصيد فعلي): هل تحب نحقق أصل `user_id=1`/`p_system_treasury@example.com` الأول (مين عمله وإمتى — عبر `created_at`/audit logs لو موجودة) قبل أي قرار، ولا نعتبره فورًا "باج خطير يستاهل بند عاجل في التوثيق" بغض النظر عن الأصل؟

**س3:** أي تحقق حي فعلي (استدعاء API حقيقي) على دوال النمط ب هيمس رصيد `user_id=1` الحقيقي (875.0 MR_USDT) — **مش بيانات throwaway معزولة**. موافق نكمل بيه أصلًا (مع نية استرجاع الرصيد بالضبط بعد الاختبار)، ولا نعتبره برضه "غير قابل للتحقق الحي بأمان" ونكتفي بالتوثيق النظري + خطة إصلاح؟

**أي توجيه إضافي:**

---

## 7) الإغلاق [2026-08-24] — توجيه المستخدم النهائي ونتائجه

### 7.1 فحص سريع لأصل `p_system_treasury@example.com` (`user_id=1`)

```sql
SELECT id, email, tenant_id, created_at FROM users WHERE id IN (1,2);
--  1 | p_system_treasury@example.com | 1 | 2026-08-14 00:12:00.327809+00
--  2 | p0smoke_b68d8b18@example.com   | 1 | 2026-08-08 17:55:17.714038+00
```

`grep` عبر `.claude/reports/` لـ`system_treasury` لقى مصدره بالضبط: **`.claude/reports/silent-write-regression-session-log.md`** (سطر 305) — بيانات throwaway من دفعة اختبار بتاريخ 2026-08-14، موثَّقة هناك حرفيًا ضمن قائمة **"بيانات throwaway إضافية من هذه الدفعة (هتتنضف آخر الجلسة)"** (مع `id=37`/`p_stub_email_receiver_36`، `wallets 33/34/38`، وبنود تانية). **التنظيف الموعود لم يشمل `users id=1` تحديدًا** (بقية القائمة اتنضّفت غالبًا، الحساب ده بالذات عالق).

**الخلاصة:** أصله مؤكَّد الآن بثقة عالية — **بقايا بيانات throwaway منسية، مش قرار تصميمي مقصود لحساب خزانة رسمي.** الصدفة الخطيرة: معرفه الرقمي (`1`) طابق حرفيًا القيمة الهاردكودد في 3 دومينات (`commerce`/`affiliate`/`iot`)، فتحوّل بالصدفة من "بيانات اختبار منسية" لـ"هدف مالي حقيقي محتمل" لأي استخدام عادي لتلك الميزات. **فحص سريع بس كما طُلب — لم يُحقَّق أعمق (مين بالضبط شغّل جلسة `silent-write-regression`، ليه التنظيف فاته الحساب ده تحديدًا).**

### 7.2 التوثيق المُحدَّث

- ✅ `.claude/plans/critical-finding-xtenant-systemic.md` — بند 🔴🔴🔴 جديد مضاف (فوق `ai_agents` في الترتيب والخطورة)، بعنوان فئة منفصلة صراحة عن نمط X-Tenant-ID، + تحديث سطر `finance` في جدول SAFE بإشارة للبند الجديد.
- ✅ `PROGRESS_LOG.md` — بند عاجل `finance-transfer-hardcoded-system-account-real-fund-risk` مضاف (🔴🔴🔴)، شامل توصية الحراسة المؤقتة (guard clause يرفض `sender_id in (0,1)`) **كخيار مطروح لو التطبيق قريب من استخدام حقيقي — قرار التفعيل نفسه لسه مؤجَّل، لم يُنفَّذ أي كود.**
- ✅ هذا التقرير (`finance-idor-security-fix-session-log.md`) — الحالة محدَّثة لـ"مُغلقة، توثيق فقط" أعلى الملف.

### 7.3 صفر تنفيذ كود

**مؤكَّد صراحة:** لا `guard clause`، لا `is_system` flag، لا أي تعديل على `commerce`/`affiliate`/`iot`/`social`/`saas`/`finance` تم في هذه الجلسة. القرار المعماري الرسمي (مين المصدر الصحيح لـ"حساب النظام"؟) مؤجَّل لجلسة تصميم منفصلة بالكامل.

**الحالة النهائية:** ✅ **الجلسة مُغلَقة.** commit واحد للتوثيق فقط (3 ملفات: هذا التقرير + `critical-finding-xtenant-systemic.md` + `PROGRESS_LOG.md`) — صفر كود.
