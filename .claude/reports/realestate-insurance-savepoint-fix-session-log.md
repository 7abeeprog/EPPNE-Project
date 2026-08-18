# تقرير جلسة — `invoicing-savepoint-conflict` (Backlog #11b، نطاق موسَّع)

**بدأ التسجيل:** 2026-08-18
**نطاق الجلسة الأصلي المعلن في الطلب:** إصلاح `commit()`-جوه-`begin_nested()` في `InvoicingRepository.create_invoice()` كما تستدعيه 4 دوال في دومينين (`realestate`, `insurance`).

**✅ تحديث النطاق [2026-08-18] — قرار مستخدم صريح بعد اكتشاف حي (راجع قسم 1-3 تحت):** النطاق اتسع ليشمل **7 دوال عبر 4 دومينات**، بنفس السبب الجذري بالضبط (حل واحد شامل، سبب جذري واحد):

**ترتيب الأولوية المعتمد:**
1. 🔴🔴 **`tourism_sports` (3 دوال)** — **أولوية أولى، الوحيدة المكشوفة فعليًا بلا أي حماية حاليًا** (`book_program`, `purchase_event_ticket`, `place_transfer_bid`).
2. 🔴 **`realestate` + `insurance` (4 دوال)** — أولوية ثانية (محميان مؤقتًا بكراش #9، صفر أثر فعلي حتى الآن).
3. 🟡 **`zamakana` (دالة واحدة)** — أولوية ثالثة (`pledge_time`، بلا تحويل مالي، محمي بكراش #9 أيضًا).

**هذا التقرير مرجع مستقل بالكامل لهذه الجلسة — لا يُدمج مع أي تقرير سابق.**

---

## 0) قراءة المصادر المطلوبة قبل أي حركة — تم بالكامل

1. `PROGRESS_LOG.md` — بند #11b (سطر 36) وبانر الحالة (سطور 11-13) وبند #9 (سطر 33).
2. `.claude/reports/saas-control-service-missing-methods-session-log.md` بالكامل — قسم 4 تحديدًا (4 دوال، أدلة بالسطور: `realestate/service.py:183/212/239/244/252`, `:330/360/378`؛ `insurance/service.py:165/193/196/207/215`, `:407/451/458/467`).
3. `.claude/reports/invitations-savepoint-leak-session-log.md` بالكامل — الحل الناجح هناك (نقل الاستدعاء بره `begin_nested()` + idempotency key ثابت)، مع ملاحظة أن السبب الجذري هناك كان `UserRepository.create()`/`WalletRepository.create()`، بينما هنا هو `InvoicingRepository.create_invoice()` — ملف مختلف تمامًا.

## 0.1) تأكيد السبب الجذري في الكود الحالي

`eppne-backend/app/domains/invoicing/repository.py:22-31`:

```python
async def create_invoice(self, **kwargs) -> Invoice:
    # WARNING: هذا الـcommit() بيغطي كمان كتابات finance.transfer() جوه service methods
    # تانية (زي arbitration_syndicates.join_syndicate) بتنادي InvoicingService.create_invoice
    # بعد finance.transfer مباشرة (flush() بس، بلا commit مستقل خاص بيها) — لا تحوّل الـcommit()
    # ده لـflush() بدون فحص شامل لكل الـcallers أولًا.
    invoice = Invoice(**kwargs)
    self.db.add(invoice)
    await self.db.commit()
    await self.db.refresh(invoice)
    return invoice
```

تحذير مكتوب فعليًا في الكود يؤكد وجود callers أخرى تعتمد على هذا السلوك — بالضبط كما ورد في تعليمات بداية الجلسة.

---

## 1) 🔴🔴 جرد كامل لكل مستدعي `InvoicingService.create_invoice()` في المشروع كله — اكتشاف حرج

`grep` شامل على `eppne-backend/app` لـ`create_invoice` أعطى 18 ملفًا. بعد فحص كل موضع بالسياق الكامل (فحص الإندنتيشن وموضع `begin_nested()` بالنسبة له مباشرة من الملفات، مش تخمين):

| # | الموقع | داخل `begin_nested()`؟ | فلوس حقيقية (`finance.transfer`) قبلها؟ | التصنيف |
|---|---|---|---|---|
| 1 | `realestate/service.py:244` (`buy_fractional_ownership`) | ✅ نعم (`212`-`~260`) | ✅ نعم (`239`) | 🔴 **مؤكَّد #11b (النطاق الأصلي)** |
| 2 | `realestate/service.py:378` (`rent_unit`) | ✅ نعم (`360`-`~390`) | ❌ لا (مذكور في تقرير #9 كتحويل عبر مسار مختلف، يحتاج تأكيد إضافي لكن التصنيف الأصلي في #9 يكفي هنا) | 🔴 **مؤكَّد #11b (النطاق الأصلي)** |
| 3 | `insurance/service.py:207` (`subscribe`) | ✅ نعم (`193`-`~225`) | ✅ نعم (`196`) | 🔴 **مؤكَّد #11b (النطاق الأصلي)** |
| 4 | `insurance/service.py:467` (`review_claim`) | ✅ نعم (`451`-`~480`) | ✅ نعم (`458`) | 🔴 **مؤكَّد #11b (النطاق الأصلي)** |
| 5 | `zamakana/service.py:312` (دالة تعهد وقت/`pledge_time`، شرطي `if pledge.pledged_hours > 10`) | ✅ نعم (`300`-`327`، مباشرة قبل `audit_log` جوه نفس البلوك) | ❌ لا (كتابة `repo.create_pledge` بس قبلها، لا تحويل مالي مباشر) | 🆕 **غير مكتشف سابقًا — نفس النمط** |
| 6 | `tourism_sports/service.py:171` (`book_program`) | ✅ نعم (`158`-`197`) | ✅ نعم (`160`، `finance.transfer` حقيقي) | 🆕🔴 **غير مكتشف سابقًا — نفس النمط بالضبط، فلوس حقيقية** |
| 7 | `tourism_sports/service.py:293` (`purchase_event_ticket`) | ✅ نعم (`280`-`321`) | ✅ نعم (`282`، `finance.transfer` حقيقي) | 🆕🔴 **غير مكتشف سابقًا — نفس النمط بالضبط، فلوس حقيقية** |
| 8 | `tourism_sports/service.py:447` (مزايدة انتقال لاعب، قسم "الرياضة") | ✅ نعم (`435`-`465`) | ❌ لا (`repo.create_transfer` قبلها، لا تحويل مالي مباشر في هذه الدالة) | 🆕 **غير مكتشف سابقًا — نفس النمط** |
| 9 | `tenders_auctions/service.py:422` (`close_auction`) | ❌ لا (`finance.transfer` في `412` وحدها، بلا أي `begin_nested()` محيط) | يوجد `finance.transfer` لكن خارج أي nested block | ✅ آمن — خارج نطاق #11b |
| 10 | `service_marketplace/service.py:203` (`purchase_service`) | ❌ لا (`begin_nested()` يبدأ لاحقًا في `219`، بعد الفاتورة) | ✅ يوجد قبلها لكن كله خارج `begin_nested()` | ✅ آمن — خارج نطاق #11b (محجوبة أصلًا ببج #12 منفصل) |
| 11 | `invitations/service.py:655` (`create_campaign`) | ❌ لا (`begin_nested()` يبدأ لاحقًا في `663`، بعد الفاتورة) | ✅ يوجد قبلها لكن كله خارج `begin_nested()` | ✅ آمن — خارج نطاق #11b |
| 12 | `tasks/employment.py:336` (`pay_employee_salary`، Celery task) | ❌ لا (صفر `begin_nested()` في الدالة كلها، من أولها لآخرها) | ✅ يوجد (`313`) لكن العملية كلها غير متداخلة أصلًا | ✅ آمن هيكليًا من نمط #11b (قد يكون له باج ذري منفصل تمامًا — خارج نطاقنا) |
| 13 | `manufacturing/service.py:327, 712` | ❌ لا (مؤكَّد سابقًا في تقرير #9 قسم 4.5) | — | ✅ آمن — مؤكَّد مسبقًا |
| 14 | `arbitration_syndicates/service.py:133, 351, 435` | ❌ لا (مؤكَّد سابقًا في تقرير #9 قسم 4.5) | — | ✅ آمن — مؤكَّد مسبقًا |
| 15 | `ai_agents/service.py:391` (`generate_monthly_invoice`) | ❌ لا (فحص السياق الكامل — استدعاء مستقل، صفر `begin_nested()` محيط) | ❌ لا | ✅ آمن — خارج نطاق #11b |
| 16 | `saas/repository.py:336` | — | — | ❌ **ليست نفس الدالة إطلاقًا** — `SaaSRepository.create_invoice()` منفصلة تمامًا، بتستخدم `flush()` مش `commit()` (سطر 339). لا علاقة لها بـ`InvoicingRepository`. |
| 17 | `transport/service.py:354, 529` (`finance.create_invoice`) | — | — | ❌ **ليست نفس الدالة إطلاقًا** — `grep "def create_invoice"` في `finance/*.py` أعطى **صفر نتيجة**؛ هذه method غير موجودة أصلًا على `FinanceService` (باج منفصل تمامًا، موثَّق بالفعل كـBacklog #18 `finance-service-create-invoice-does-not-exist`). صفر علاقة بـ#11b. |
| 18 | `automation/service.py:337` (`_exec_create_invoice`) | — | — | ❌ **تطابق اسم سطحي فقط** — استدعاء لدالة داخلية باسم `_exec_create_invoice` (نود تنفيذ Automation)، وتعريفها **غير موجود في الملف إطلاقًا** (`grep "async def _exec_create_invoice"` صفر نتيجة — باج مستقل تمامًا: method مفقودة، خارج نطاقنا كليًا). لا تنادي `InvoicingService`/`InvoicingRepository` على الإطلاق. |
| 19 | `invoicing/router.py:53`, `invoicing/service.py:51,88` | — | — | التعريف الأساسي/مسار الـAPI المباشر لإنشاء فاتورة — ليس استدعاءً من دومين آخر جوه `begin_nested()`، هذا هو الاستخدام المقصود الطبيعي. |

---

## 2) 🔴🔴 نقطة إيقاف فوري — شرط الإيقاف #3 مُفعَّل صراحةً

**اكتُشف نطاق إضافي غير مفحوص سابقًا لنفس نمط #11b بالضبط (`commit()` جوه `InvoicingRepository.create_invoice()` بيقفل SAVEPOINT بينما هو جوه `begin_nested()`):**

- **`zamakana`** — دالة واحدة (موضع #5 في الجدول).
- **`tourism_sports`** — **ثلاث دوال منفصلة** (مواضع #6, #7, #8 في الجدول)، اتنين منهم (`book_program`, `purchase_event_ticket`) بينهم **تحويل مالي حقيقي عبر `finance.transfer()` قبل الفاتورة مباشرة** — **نفس درجة الخطورة بالضبط الموجودة في `realestate`/`insurance`** (فلوس حقيقية بتتحوَّل بنجاح، ثم SAVEPOINT بيتقفل بالنص، وباقي الكتابات في نفس البلوك — إنشاء التذكرة/تسجيل المشارك، عمولة الأفلييت، الـaudit log — بتفشل بـ`InvalidRequestError`).

**السبب في عدم ظهور هاتين الدومينين في تقرير #9 (قسم 4.5):** ذلك الفحص كان مقيَّدًا بالدومينات الثمانية اللي بتستدعي `SaaSControlService.get_active_subscription` بالتوقيع الخاطئ (باج #9 نفسه) — `zamakana` و`tourism_sports` **لا تعتمدان على هذا النمط الخاطئ من `_check_saas_limits` أصلًا** (لم تُفحصا لأنهما لم تكونا ضمن قائمة الثمانية دومينات المتأثرة بباج #9)، وبالتالي **لا يوجد كراش وقائي بالصدفة يحميهما حاليًا** — أي طلب حقيقي لـ`tourism_sports.book_program`/`purchase_event_ticket` **الآن، بدون أي تعديل إضافي، قد يصل فعليًا لنقطة تحويل الفلوس ثم الكراش الجزئي** (بعكس `realestate`/`insurance` المحميين مؤقتًا بكراش #9).

**هذا يعني أن `tourism_sports` قد يكون فعليًا **أكثر إلحاحًا** من `realestate`/`insurance`** — لأن الأخيرين محميان حاليًا بكراش #9 (صفر أثر فعلي حتى الآن)، بينما `tourism_sports` **غير محمي بأي شيء** وقد يكون قابلاً للاستغلال/التسبب في فقدان كتابة حقيقي بفلوس حقيقية **الآن، في هذه اللحظة**، في بيئة إنتاج حقيقية.

---

## 3) ✅ قرار المستخدم [2026-08-18] — توسيع نطاق #11b

**القرار الصريح:** توسيع #11b ليشمل **7 دوال عبر 4 دومينات** في نفس هذه الجلسة: `realestate.buy_fractional_ownership`, `realestate.rent_unit`, `insurance.subscribe`, `insurance.review_claim`, `zamakana` (دالة تعهد الوقت، سطر 312)، `tourism_sports.book_program`, `tourism_sports.purchase_event_ticket`, `tourism_sports` (مزايدة انتقال لاعب، سطر 447).

الجلسة تكمل الآن لقسم التشخيص الكامل (جدول أدلة الحل + تريدوف `finance.transfer`) لكل الدوال السبعة دفعة واحدة، بنفس المعيار المستخدم في `invitations`.

---

## 4) 🔑 التحليل الحاسم — هل `finance.transfer()` لازم تتنقل مع `create_invoice()` بره `begin_nested()`؟

### 4.1) الحقيقة التقنية الأساسية (تحقَّق منها بقراءة الكود مباشرة، مش افتراض)

`finance/service.py:58-147` (`FinanceService.transfer`):

```python
async def transfer(self, ...):
    ...
    async with self.db.begin_nested():          # ← savepoint داخلية خاصة بيها
        ...
        await self.wallet_repo.update_balances(...)   # flush فقط
        await self.wallet_repo.update_balances(...)   # flush فقط
        tx = await self.tx_repo.create(...)            # flush فقط
    # لا يوجد await self.db.commit() هنا إطلاقًا — الدالة كلها بره الـblock بتعمل _create_audit_log بس (منفصل تمامًا عن الالتزام DB)
    return tx
```

**`finance.transfer()` تفتح `begin_nested()` خاصة بيها (savepoint متداخلة جوه أي savepoint خارجية)، ولا تعمل `commit()` مباشر إطلاقًا في أي مسار من مسارتها.** هذا يعني: **`finance.transfer()` آمنة تمامًا للاستدعاء من جوه `begin_nested()` خارجية — بالضبط زي ما هي مستخدمة الآن في كل المواضع الخمسة.** المشكلة الوحيدة في كل الدوال السبعة هي `invoicing.create_invoice()` تحديدًا (`commit()` مباشر، `invoicing/repository.py:29`) — **مفيش أي حاجة تانية في أي من البلوكات دي بتعمل `commit()` مباشر**.

### 4.2) الخلاصة القاطعة: الفلوس تفضل جوه الـ`begin_nested()`، الفاتورة بس اللي تتنقل بره

**لكل المواضع الخمسة اللي فيها `finance.transfer()` حقيقي — الجواب واحد وثابت: لأ، مفيش داعي تنقل `finance.transfer()` معاها، ومفيش أي فقدان atomicity في [التحويل المالي + إنشاء المورد الأساسي].** السبب: بما إن `create_invoice()` هي الوحيدة اللي بتعمل `commit()` مباشر، والحل (زي `invitations`) هو نقلها هي بس بره أي `begin_nested()` محيط — مش لازم ننقل حاجة تانية معاها، لأن مفيش حاجة تانية بتكسر الـsavepoint.

| # | الموقع | `finance.transfer()` موجودة؟ | هل تتنقل مع `create_invoice()`؟ | الأثر على الـatomicity |
|---|---|---|---|---|
| 1 | `realestate/service.py:244` (`buy_fractional_ownership`، transfer في `239`) | ✅ نعم | ❌ لأ — تفضل جوه `begin_nested()` | ✅ **تحسين فعلي عن الوضع الحالي**: التحويل + إنشاء سجل الملكية (`create_ownership`) + عمولة الأفلييت + audit log كلهم هيبقوا وحدة ذرية واحدة (تنجح مع بعض أو تتراجع مع بعض) — بعكس اليوم اللي بيكراش بالنص. الفاتورة بس بتتحول لخطوة "إيصال" منفصلة بعد نجاح العملية الأساسية بالكامل. |
| 2 | `realestate/service.py:378` (`rent_unit`) | ❌ لا (الدالة دي **مفيهاش `finance.transfer()` إطلاقًا** — بس `repo.create_rental_contract` + فاتورة، تأكَّد بقراءة الدالة كاملة `359-415`) | — لا ينطبق | لا يوجد تحويل مالي في هذا المسار من الأساس؛ التريدوف غير مطروح هنا. |
| 3 | `insurance/service.py:207` (`subscribe`، transfer في `196`) | ✅ نعم (جوه `if premium > 0:`) | ❌ لأ — تفضل جوه `begin_nested()` | ✅ نفس المنطق: التحويل + `create_subscription` + عمولة الأفلييت وحدة ذرية واحدة. الفاتورة بعد كده. |
| 4 | `insurance/service.py:467` (`review_claim`، transfer في `458`) | ✅ نعم (جوه `if approve:`) | ❌ لأ — تفضل جوه `begin_nested()` | ✅ نفس المنطق: صرف التعويض + `update_claim` (`status=PAID`) وحدة ذرية واحدة. الفاتورة بعد كده. |
| 5 | `zamakana/service.py:312` (دالة تعهد الوقت) | ❌ لا (مفيش `finance.transfer()`؛ بس `repo.create_pledge` + فاتورة شرطية) | — لا ينطبق | لا يوجد تحويل مالي؛ التريدوف غير مطروح هنا. |
| 6 | `tourism_sports/service.py:171` (`book_program`، transfer في `160`) | ✅ نعم | ❌ لأ — تفضل جوه `begin_nested()` | ✅ نفس المنطق: التحويل + `create_program_participant` + audit log وحدة ذرية واحدة. الفاتورة بعد كده. |
| 7 | `tourism_sports/service.py:293` (`purchase_event_ticket`، transfer في `282`) | ✅ نعم | ❌ لأ — تفضل جوه `begin_nested()` | ✅ نفس المنطق: التحويل + `create_ticket` + audit log وحدة ذرية واحدة. الفاتورة بعد كده. |
| 8 | `tourism_sports/service.py:447` (مزايدة انتقال لاعب) | ❌ لا (مفيش `finance.transfer()`؛ بس `repo.create_transfer` (سجل مزايدة) + فاتورة رسوم وكالة) | — لا ينطبق | لا يوجد تحويل مالي في هذا المسار (رسوم الوكالة نفسها بتتسجل كفاتورة بس، مفيش `finance.transfer` فعلي هنا). |

### 4.3) لماذا هذا أفضل من نقل كل حاجة بره الـ`begin_nested()`؟

لو افترضنا (خطأً) إن الحل يتطلب نقل `finance.transfer()` كمان بره الـblock:
- كنا هنفقد الحماية الذرية بين [التحويل المالي] و[إنشاء المورد الأساسي] (`ownership`/`subscription`/`participant`/`ticket`) — يعني احتمال حقيقي لسيناريو "فلوس اتحولت لكن مفيش سجل ملكية/اشتراك/تذكرة" لو حصل أي فشل بين الاتنين — وده **بالضبط الفئة اللي كنا بنحاول نتجنبها من الأساس**.
- بما إن `finance.transfer()` **مثبَّت تقنيًا** (بالقراءة المباشرة) إنها آمنة تمامًا جوه `begin_nested()` (savepoint متداخلة خاصة بيها، صفر `commit()`)، **مفيش أي سبب تقني يجبرنا على نقلها** — البقاء مكانها هو الخيار الأدق والأقل تغييرًا والأكثر أمانًا في نفس الوقت.

### 4.4) نقطة إضافية تم فحصها: هل أي حاجة بعد `create_invoice()` في نفس البلوك بتعتمد على قيمة راجعة منها؟

فحصت كل المواضع السبعة — **صفر استخدام لقيمة راجعة من `invoicing.create_invoice(...)`** في أي مكان (كل الاستدعاءات `await invoicing.create_invoice(...)` بلا `=` تخزين نتيجة). هذا يعني نقلها لأي مكان تاني (بره الـblock) **لا يكسر أي منطق لاحق يعتمد على كائن الفاتورة نفسه** — نقل آمن من هذه الزاوية أيضًا.

### 4.5) فحص إضافي: `_register_affiliate_commission` — هل هي مصدر خطر مشابه؟

`realestate/service.py:573-587` (نفس النمط موجود في `insurance`/`tourism_sports`): الدالة ملفوفة بالكامل بـ`try/except Exception` عام بيسجل اللوج بس ولا يرفع الاستثناء. `grep` لـ`async def register_commission` في دومين `affiliate` **أعطى صفر نتيجة** — method غير موجودة أصلًا (باج مستقل مسبق التوثيق، **Backlog #10** `affiliate-service-missing-methods`). بما إنها بتكراش بـ`AttributeError` **قبل** أي عملية DB، وبما إن الاستثناء ده متلقَّط ومُتجاهَل بالكامل، **صفر خطر savepoint إضافي من هذه الدالة** — مجرد تأكيد إضافي لباج موثَّق مسبقًا، صفر علاقة بـ#11b.

---

## 5) جدول تحليل الـatomicity الكامل — الأسئلة الثلاثة لكل موقع (بترتيب الأولوية المعتمد)

**دليل إضافي قبل الجدول (يخص السؤال 3 لكل المواقع دفعة واحدة):** فحصت `arbitration_syndicates.join_syndicate` (`arbitration_syndicates/service.py:304-380`) كمثال ملموس على caller **بره** `begin_nested()` (مؤكَّد سابقًا في قسم 1، الصف 14) — التسلسل هناك: `finance.transfer()` (flush فقط، سطر ~336) → `invoice_service.create_invoice()` (سطر ~351) → `_register_affiliate_commission` (try/except مُتجاهَل) → `repo.create_membership()` (سطر 363). **صفر `await self.db.commit()` صريح في الدالة كلها غير اللي جوه `create_invoice()` نفسها.** يعني `commit()` بتاع `create_invoice()` هو **نقطة الالتزام الوحيدة** اللي بتخلي كتابات `finance.transfer()` (تحديث الأرصدة، سجل الـtx) تتحفظ فعليًا على القرص. هذا دليل حي مباشر (مش نظري) على خطورة لمس `InvoicingRepository.create_invoice()` نفسها — بالضبط زي ما ورد في التحذير المكتوب جوه الكود.

---

### 5.1) 🔴🔴 `tourism_sports.book_program` (`tourism_sports/service.py:171`, transfer في `160`) — أولوية أولى

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | ❌ لا. تفضل جوه `begin_nested()` مع `repo.create_program_participant` (السطر 182) و`audit_log` (191) — بيبقوا وحدة ذرية واحدة (تنجح مع بعض أو تتراجع مع بعض بالكامل عبر SAVEPOINT rollback). |
| **2. أسوأ سيناريو لو الفاتورة في معاملة منفصلة؟** | **الاتجاه الوحيد الممكن للانفصال:** التحويل المالي + تسجيل المشارك (`ProgramParticipant`) ينجحوا وينلتزموا (transaction 1)، ثم `create_invoice()` (transaction 2، منفصلة تمامًا بعدها) تفشل لأي سبب (انقطاع DB لحظي، إلخ). **النتيجة:** المستخدم دفع فعليًا، عنده مقعد محجوز فعليًا في البرنامج (`ProgramParticipant` موجود)، **لكن بلا سجل فاتورة**. **العكس (فاتورة موجودة بدون تحويل/حجز) مستحيل هيكليًا** — لأن `finance.transfer()` والحجز داخل نفس الـ`begin_nested()` قبل `create_invoice()`، فلو أي منهم فشل الـblock بالكامل بيتراجع (rollback) و`create_invoice()` مبتتنفذش أصلًا. |
| **مقارنة بالوضع الحالي؟** | ✅ **أفضل موضوعيًا بشكل قاطع.** الوضع الحالي (لو اتنفذ فعليًا، `tourism_sports` مش محمية بأي كراش وقائي): فلوس بتتحول + فاتورة بتتسجل، ثم **كراش فوري** (`InvalidRequestError`) قبل `repo.create_program_participant` — يعني **المستخدم يدفع ولا يحصل على أي حجز فعلي**، أسوأ سيناريو ممكن (فلوس ضاعت بلا مقابل). الحل المقترح يقلب هذا: أسوأ سيناريو بعده هو "دفع + حجز فعلي بلا إيصال" — فجوة تسجيل بسيطة قابلة للتصحيح لاحقًا (الفاتورة ممكن تُنشأ يدويًا/بإعادة محاولة، البيانات اللازمة كلها موجودة: `tx_hash`, `amount`, `user_id`), **مش فقدان حق فعلي للمستخدم**. |
| **3. بديل يحافظ على atomicity كاملة؟** | تعديل `InvoicingRepository.create_invoice()` لتستخدم `flush()` بدل `commit()` (أو معامل `commit: bool = True` اختياري) بحيث تنضم لنفس الـ`begin_nested()` الخارجية بدل ما تقفلها. **🔴 هذا يفعِّل شرط الإيقاف #5 صراحةً** — `create_invoice()` مُستخدَمة من 18 موضع إجمالًا (قسم 1)، منهم على الأقل `arbitration_syndicates.join_syndicate`/`manufacturing` (خارج أي `begin_nested()`) بيعتمدوا على الـ`commit()` بتاعها كنقطة الالتزام الوحيدة لكتابات سابقة (دليل حي أعلاه). **محظور فعليًا من نطاق هذه الجلسة إلا بموافقة استثنائية صريحة تعلن تجاوز الشرط عمدًا، مع تحقق شامل إضافي لكل الـ18 موضع.** |

### 5.2) 🔴🔴 `tourism_sports.purchase_event_ticket` (`tourism_sports/service.py:293`, transfer في `282`) — أولوية أولى

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | ❌ لا. تفضل جوه `begin_nested()` مع `repo.create_ticket` (303) و`audit_log` (315) — وحدة ذرية واحدة. |
| **2. أسوأ سيناريو؟** | نفس البنية: دفع + تذكرة (`NFTTicket`) موجودة فعليًا، لكن بلا فاتورة، لو `create_invoice()` فشلت في معاملتها المنفصلة بعد نجاح الأولى. العكس مستحيل هيكليًا لنفس السبب. |
| **مقارنة بالوضع الحالي؟** | ✅ نفس التحسين القاطع: الوضع الحالي (غير المحمي) = فلوس اتحولت + فاتورة اتسجلت + **كراش قبل إنشاء التذكرة الفعلية** (المستخدم يدفع ولا يحصل على تذكرة). الحل المقترح = دفع + تذكرة فعلية بلا إيصال (فجوة بسيطة قابلة للتصحيح). |
| **3. بديل atomicity كاملة؟** | نفس التحذير بالضبط كـ5.1 — يفعِّل شرط الإيقاف #5، محظور إلا بموافقة استثنائية + تحقق شامل لـ18 موضع. |

### 5.3) 🟡 `tourism_sports` مزايدة انتقال لاعب (`tourism_sports/service.py:447`) — أولوية أولى (جزء من نفس الدومين)، لا يوجد فيها تحويل مالي

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | لا ينطبق — **لا يوجد `finance.transfer()` في هذه الدالة إطلاقًا** (فقط `repo.create_transfer` = سجل مزايدة، ثم فاتورة رسوم الوكالة). |
| **2. أسوأ سيناريو؟** | سجل المزايدة (`PlayerTransfer`) يتسجل وينلتزم، ثم فاتورة رسوم الوكالة تفشل في معاملتها المنفصلة. النتيجة: مزايدة مسجَّلة فعليًا بلا فاتورة رسوم — فجوة تسجيل بسيطة، صفر أثر مالي حقيقي فُقد (لا يوجد `finance.transfer` هنا من الأساس). |
| **مقارنة بالوضع الحالي؟** | ✅ أفضل — الوضع الحالي (غير المحمي): سجل المزايدة يتسجل، الفاتورة تتسجل، ثم **كراش عند** `_register_affiliate_commission`/`audit_log` بعدها (لو موجودة جوه نفس البلوك) — نفس فئة الفشل الجزئي، لكن بدون فلوس حقيقية فُقدت هنا. |
| **3. بديل atomicity كاملة؟** | نفس التحذير — يفعِّل شرط الإيقاف #5. |

### 5.4) 🔴 `realestate.buy_fractional_ownership` (`realestate/service.py:244`, transfer في `239`) — أولوية ثانية (محمية حاليًا بكراش #9)

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | ❌ لا. تفضل جوه `begin_nested()` مع `repo.create_ownership` (255)، تحديث حالة الوحدة (267)، `event_bus.publish` (269)، `audit_log` (277) — وحدة ذرية واحدة. |
| **2. أسوأ سيناريو؟** | دفع + سجل ملكية (`PropertyOwnership`) موجود فعليًا (المشتري فعليًا مالك الجزء اللي اشتراه)، لكن بلا فاتورة، لو `create_invoice()` فشلت بعد نجاح المعاملة الأولى. العكس مستحيل هيكليًا. |
| **مقارنة بالوضع الحالي؟** | ✅ أفضل بشكل قاطع — موثَّق في تقرير #9 قسم 4 حرفيًا: الوضع الحالي (لو اتصلح #9 بمعزل) = فلوس اتحولت + فاتورة اتسجلت + **كراش قبل تسجيل الملكية الفعلية** (المشتري يدفع ولا يملك حاجة). الحل المقترح = دفع + ملكية فعلية بلا إيصال. |
| **3. بديل atomicity كاملة؟** | نفس التحذير — يفعِّل شرط الإيقاف #5. |

### 5.5) 🔴 `insurance.subscribe` (`insurance/service.py:207`, transfer في `196`) — أولوية ثانية

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | ❌ لا. تفضل جوه `begin_nested()` مع `repo.create_subscription` (219) — وحدة ذرية واحدة. |
| **2. أسوأ سيناريو؟** | دفع القسط + اشتراك تأميني فعلي (`InsuranceSubscription`) موجود، لكن بلا فاتورة. العكس مستحيل هيكليًا. |
| **مقارنة بالوضع الحالي؟** | ✅ أفضل — الوضع الحالي (لو اتصلح #9 بمعزل، موثَّق حرفيًا في تقرير #9): دفع + فاتورة، ثم **كراش قبل تسجيل الاشتراك نفسه فعليًا** (العميل يدفع قسط تأمين ولا يحصل على بوليصة فعلية سارية). |
| **3. بديل atomicity كاملة؟** | نفس التحذير — يفعِّل شرط الإيقاف #5. |

### 5.6) 🔴 `insurance.review_claim` (`insurance/service.py:467`, transfer في `458`) — أولوية ثانية

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | ❌ لا. تفضل جوه `begin_nested()` مع `repo.update_claim(status=PAID, ...)` (475) — وحدة ذرية واحدة. |
| **2. أسوأ سيناريو؟** | صرف التعويض + حالة المطالبة اتحدثت فعليًا لـ`PAID` مع `payout_tx_hash` مسجَّل، لكن بلا فاتورة. العكس مستحيل هيكليًا — **مهم هنا تحديدًا:** لأن `payout_tx_hash` بيتسجل جوه نفس الـ`update_claim`، حتى لو الفاتورة فشلت، **حالة المطالبة نفسها متسقة تمامًا مع كون الفلوس اتحولت فعليًا** (صفر تعارض بين حالة `claim.status=PAID` والواقع المالي). |
| **مقارنة بالوضع الحالي؟** | ✅ أفضل — الوضع الحالي (لو اتصلح #9 بمعزل): صرف تعويض حقيقي + فاتورة، ثم **كراش قبل تحديث حالة المطالبة لـ`PAID`** — يعني تعويض اتصرف فعليًا لكن سجل المطالبة لسه `PENDING` (تناقض خطير: فلوس خرجت فعليًا لكن النظام مايعرفش إن المطالبة اتصرفت، خطر دفع مزدوج لو حد حاول يراجعها تاني). الحل المقترح يقفل هذا التناقض تمامًا. |
| **3. بديل atomicity كاملة؟** | نفس التحذير — يفعِّل شرط الإيقاف #5. |

### 5.7) 🟡 `zamakana` تعهد الوقت (`zamakana/service.py:312`) — أولوية ثالثة، لا يوجد فيها تحويل مالي

| السؤال | الإجابة |
|---|---|
| **1. هل ينقل `finance.transfer()` معاها؟** | لا ينطبق — **لا يوجد `finance.transfer()` في هذه الدالة إطلاقًا** (فقط `repo.create_pledge`، ثم فاتورة شرطية لو `pledged_hours > 10`). |
| **2. أسوأ سيناريو؟** | تعهد الوقت (`TimePledge`) يتسجل وينلتزم، ثم الفاتورة الشرطية تفشل في معاملتها المنفصلة (فقط لو `pledged_hours > 10`). فجوة تسجيل بسيطة، صفر أثر مالي حقيقي (لا يوجد `finance.transfer` هنا). |
| **مقارنة بالوضع الحالي؟** | ✅ أفضل — الوضع الحالي: تعهد + فاتورة (لو منطبقة)، ثم **كراش عند `audit_log`** بعدها (نفس البلوك) — فشل جزئي بلا داعٍ. |
| **3. بديل atomicity كاملة؟** | نفس التحذير — يفعِّل شرط الإيقاف #5. |

---

## 6) الخلاصة العامة قبل أي كود

- **السؤال 1 (لكل المواقع الخمسة اللي فيها فلوس):** الإجابة ثابتة = **لا، `finance.transfer()` تفضل جوه `begin_nested()`**. صفر استثناء.
- **السؤال 2:** في كل المواقع بلا استثناء، أسوأ سيناريو بعد الحل المقترح هو **"العملية الأساسية نجحت فعليًا (بما فيها الفلوس لو موجودة) لكن الفاتورة/الإيصال ناقص"** — فجوة تسجيلية قابلة للتصحيح، **مش فقدان حق أو فلوس فعلي**. هذا **أفضل موضوعيًا وبشكل قاطع** من الوضع الحالي في كل موقع (فحص فردي أعلاه)، اللي بيؤدي دائمًا لأحد نمطين أسوأ: (أ) فلوس/عمل خرجت فعليًا بلا أي مقابل للمستخدم (`buy_fractional_ownership`, `subscribe`, `book_program`, `purchase_event_ticket`)، أو (ب) تناقض بين حالة السجل المخزنة والواقع المالي الفعلي (`review_claim`، الأخطر: خطر دفع مزدوج).
- **السؤال 3:** بديل واحد فقط يحافظ على atomicity كاملة (تحويل `InvoicingRepository.create_invoice()` لـflush-only) — **محظور فعليًا من نطاق هذه الجلسة بموجب شرط الإيقاف #5**، بدليل حي ملموس (`arbitration_syndicates.join_syndicate`) على الخطر الحقيقي لو اتلمس بلا تحقق شامل لكل الـ18 موضع. **لن يُقترَح كتنفيذ إلا بموافقة استثنائية صريحة إضافية منك.**

**التوصية:** نفس نمط "الخيار أ" في `invitations` — نقل `create_invoice()` فقط بره كل `begin_nested()` (بعد إغلاقها، مش قبل فتحها، للأسباب الموضحة في قسم 4.4) — لكل المواقع السبعة، بترتيب التطبيق: `tourism_sports` (3) → `realestate`+`insurance` (4) → `zamakana` (1).

## 7) 🔑 توضيح إضافي مطلوب — ليه "بعد الإغلاق" مش "قبل الفتح" (بديل عن نمط `invitations` الحرفي)

**الفرق الجوهري بين الحالتين:**

في `invitations.accept_invitation`، الاستدعاء الخطر (`_create_user_from_invitation`) كان **أول سطر** جوه `begin_nested()`، وكان **مستقلاً تمامًا** عن أي تحقق/رفض لاحق داخل نفس البلوك — يعني نقله لقبل فتح البلوك ما كانش بيغيّر أي شرط قبول/رفض للعملية ككل.

**هنا الوضع مختلف جوهريًا:** `create_invoice()` في كل المواضع السبعة **بتيجي بعد سلسلة تحققات/عمليات ممكن تفشل وترفض العملية بالكامل** — مثلاً:
- `realestate.buy_fractional_ownership`: فحص "هل تجاوزت نسبة الملكية 100%؟" (`total_owned_dec + percentage > 100`) بيحصل **جوه** البلوك، **قبل** حساب `cost` نفسها، و**قبل** `create_invoice()`. لو الفحص ده فشل (`PermissionDeniedError`)، العملية كلها لازم تترفض من الأساس.
- في كل الدوال: `finance.transfer()` نفسها ممكن ترفع `InsufficientBalanceError` (رصيد غير كافٍ) — وهي بتيجي **قبل** `create_invoice()` مباشرة في كل موضع.
- `insurance.review_claim`: `create_invoice()` بتيجي جوه `if approve:` — شرط منطقي بالكامل.

**لو نقلنا `create_invoice()` لقبل فتح `begin_nested()` (تقليد حرفي لنمط `invitations`):** هنكون بننفذها **قبل** ما نعرف أصلاً هل العملية هتنجح ولا لأ. النتيجة الخطيرة: **فاتورة مُلتزَمة على القرص (`commit()` فوري) لعملية شراء/اشتراك/حجز لسه ما اتأكدتش — ولو العملية اترفضت بعد كده (مثلاً `PermissionDeniedError` بسبب تجاوز نسبة الملكية، أو `InsufficientBalanceError`)، الفاتورة تفضل موجودة على القرص لعملية لم تحدث إطلاقًا.** هذا **أسوأ من الفجوة الحالية اللي بنحاول نصلحها** — مش مجرد "فاتورة ناقصة"، ده "فاتورة وهمية لعملية مرفوضة" (خطأ محاسبي مباشر، ممكن يظهر في تقارير الفواتير كإيراد لم يحدث).

**لذلك القاعدة الحاكمة هنا:** `create_invoice()` لازم تتنفذ **فقط بعد ما نتأكد 100% إن العملية الأساسية نجحت فعليًا والتزمت على القرص** — وهذا التأكيد الوحيد المتاح هو نجاح `async with self.db.begin_nested():` بالكامل بلا استثناء **و**نجاح الـ`await self.db.commit()` الصريح بعده. أي نقطة قبل هذين الحدين لا تضمن نجاح العملية.

**التنفيذ العملي:** الموقع الموحّد المقترح لكل الدوال السبعة هو **مباشرة بعد سطر `await self.db.commit()` الموجود بالفعل في كل دالة، وقبل أي كود آخر بعده** (تخزين idempotency، `event_bus.publish`، `audit_log` الخارجي لو موجود، إلخ) — بحيث "الإيصال" هو أول حاجة تتحاول فور تأكيد نجاح العملية الأساسية.

---

## 8.0) ✅ إصلاح إضافي على الديف [2026-08-18] — فجوة اكتشفها المستخدم قبل الموافقة

**الفجوة:** `create_invoice()` بعد `await self.db.commit()` وقبل `_store_idempotency()` بلا `try/except` — لو `create_invoice()` فشلت، الاستثناء بيرفع لأعلى الدالة كلها، فـ`_store_idempotency()` مبتتنفذش رغم إن العملية الأساسية (`finance.transfer` + إنشاء المورد) نجحت والتزمت فعليًا على القرص. العميل يشوف 500، يعيد المحاولة بنفس الـ`idempotency_key`، والفحص الكاش-محور في أول الدالة (`_validate_idempotency`، جدول السطور تحت) بيرجع فاضي لأنه ما اتخزنش، فالدالة تعيد التنفيذ من الأول.

| الدالة | سطر فحص الـidempotency (الكاش) |
|---|---|
| `book_program` | `136-144` |
| `purchase_event_ticket` | `246-254` |
| `place_transfer_bid` | `386-394` |

**تحليل إضافي (دفاع موجود بالفعل، لكن غير كافٍ لوحده):** `finance.transfer()` (`finance/service.py:72-75`) عندها فحص idempotency مستقل على مستوى الـDB (`tx_repo.get_by_idempotency_key`) بيمنع تكرار التحويل المالي الفعلي، وكل الموديلات الأساسية (`ProgramParticipant`, `NFTTicket`, `PlayerTransfer`) عندها `idempotency_key` بـunique constraint (قسم 4 السابق) بيمنع تكرار إنشاء المورد. **لكن من غير الإصلاح، إعادة المحاولة هتضرب `IntegrityError`/تعارض غير متوقَّع بدل ما ترجع النتيجة المخزنة بسلاسة** — الحمايات دي شبكة أمان أخيرة، مش بديل عن `_store_idempotency()` الناجحة.

**الإصلاح المعتمد:** لف استدعاء `create_invoice()` بـ`try/except Exception` عام (نفس نمط `_register_affiliate_commission` الموجود بالفعل في نفس الملف) — تسجيل اللوج لو فشلت، والاستمرار عادي لـ`_store_idempotency()`/`return`. متسق مع فلسفة "الفاتورة إيصال تابع، مش شرط نجاح العملية".

---

## 8) 🛑 الديف الحرفي (بعد الإصلاح) — `tourism_sports` فقط (3 دوال) — بانتظار موافقتك الصريحة

**بالاتفاق: التطبيق هيتم دومين واحد في كل مرة، بالترتيب: `tourism_sports` أولًا (هنا)، بعدين `realestate`+`insurance`، بعدين `zamakana` — موافقة فردية على كل خطوة، مش batch واحد.**

الملف الوحيد المتأثر في هذه الخطوة: `eppne-backend/app/domains/tourism_sports/service.py`. **صفر لمس على أي ملف تاني، بما فيهم `invoicing/repository.py` نفسها.**

```diff
--- a/eppne-backend/app/domains/tourism_sports/service.py
+++ b/eppne-backend/app/domains/tourism_sports/service.py
@@ -156,26 +156,26 @@ class TourismSportsService:
         finance = FinanceService(self.db, tenant_id)
         invoice_service = InvoicingService(self.db, tenant_id)
         async with self.db.begin_nested():
             try:
                 tx_hash = await finance.transfer(
                     sender_id=user_id,
                     receiver_email="tourism@eppne.com",
                     currency="MR_USDT",
                     amount=program.base_price_mrusdt,  # type: ignore
                     notes=f"Booking program {program_id}",
                     idempotency_key=idempotency_key or ""
                 )
             except InsufficientBalanceError:
                 raise PermissionDeniedError("Insufficient balance")
 
-            await invoice_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=program.base_price_mrusdt,  # type: ignore
-                description=f"Tourism program booking: {program.title}",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
-
             await self._register_affiliate_commission(user_id, tenant_id, "PROGRAM_BOOKED", program.base_price_mrusdt)  # type: ignore
 
             nft_id = f"TKT-PROG-{program_id}-{user_id}-{uuid.uuid4().hex[:8].upper()}"
             participant = await self.repo.create_program_participant(
                 tenant_id=tenant_id,
                 program_id=program_id,
                 user_id=user_id,
                 ticket_nft_id=nft_id,
                 payment_tx_hash=tx_hash,
                 idempotency_key=idempotency_key
             )
 
             await audit_log(  # type: ignore[call-arg]
                 user_id=user_id,
                 tenant_id=tenant_id,
                 action="PROGRAM_BOOKED",
                 resource_id=participant.id,
                 details={"program_id": program_id, "amount": float(program.base_price_mrusdt)}  # type: ignore
             )
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=program.base_price_mrusdt,  # type: ignore
+                description=f"Tourism program booking: {program.title}",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for program booking {program_id}: {e}")
+
         # تخزين معرف المشارك فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"participant_id": participant.id})
 
         return participant
@@ -280,26 +280,26 @@ class TourismSportsService:
         async with self.db.begin_nested():
             try:
                 tx_hash = await finance.transfer(
                     sender_id=user_id,
                     receiver_email="events@eppne.com",
                     currency="MR_USDT",
                     amount=price,
                     notes=f"Ticket for event {event_id}",
                     idempotency_key=idempotency_key or ""
                 )
             except InsufficientBalanceError:
                 raise PermissionDeniedError("Insufficient balance")
 
-            await invoice_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=price,
-                description=f"Event ticket: {event.title} ({tier})",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
-
             nft_id = f"TKT-{event_id}-{user_id}-{uuid.uuid4().hex[:12].upper()}"
             qr_data = hashlib.sha256(f"{nft_id}-{uuid.uuid4().hex}".encode()).hexdigest()[:16]
             ticket = await self.repo.create_ticket(
                 tenant_id=tenant_id,
                 event_id=event_id,
                 owner_id=user_id,
                 tier=tier,
                 assigned_vehicle_id=None,
                 nft_token_id=nft_id,
                 qr_code_data=qr_data,
                 purchase_price_mrusdt=price,
                 idempotency_key=idempotency_key
             )
 
             await audit_log(  # type: ignore[call-arg]
                 user_id=user_id,
                 tenant_id=tenant_id,
                 action="TICKET_PURCHASED",
                 resource_id=ticket.id,
                 details={"event_id": event_id, "tier": tier, "amount": float(price)}
             )
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=price,
+                description=f"Event ticket: {event.title} ({tier})",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for ticket purchase (event {event_id}): {e}")
+
         # تخزين معرف التذكرة فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"ticket_id": ticket.id})
 
         return ticket
@@ -434,26 +434,26 @@ class TourismSportsService:
         invoice_service = InvoicingService(self.db, tenant_id)
         async with self.db.begin_nested():
             transfer = await self.repo.create_transfer(
                 tenant_id=tenant_id,
                 from_club_id=from_club_id,
                 status=TransferStatus.BID_PLACED,
                 medical_ai_flag=medical_flag,
                 medical_report_summary=medical_report,
                 idempotency_key=idempotency_key,
                 **data
             )
 
             agency_fee = data["bid_amount_mrusdt"] * (data.get("agency_fee_percentage", 10) / 100)
-            await invoice_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=agency_fee,
-                description=f"Agency fee for transfer of player {player.user_id}",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
 
             if data.get("facilitating_agency_id"):
                 await self._register_affiliate_commission(user_id, tenant_id, "PLAYER_TRANSFER", agency_fee)
 
             await audit_log(  # type: ignore[call-arg]
                 user_id=user_id,
                 tenant_id=tenant_id,
                 action="PLAYER_TRANSFER_BID",
                 resource_id=transfer.id,
                 details={"player_id": data["player_id"], "bid_amount": float(data["bid_amount_mrusdt"])}
             )
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=agency_fee,
+                description=f"Agency fee for transfer of player {player.user_id}",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for player transfer bid {transfer.id}: {e}")
+
         # تخزين معرف التحويل فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"transfer_id": transfer.id})
 
         return transfer
```

**ملخص التغيير:** في كل دالة من الثلاثة، `create_invoice()` بتتحرك حرفيًا من مكانها جوه `begin_nested()` إلى **مباشرة بعد `await self.db.commit()`**، ملفوفة بـ`try/except Exception` عام (نفس نمط `_register_affiliate_commission`) — لو فشلت، تسجيل لوج والاستمرار عادي لـ`_store_idempotency()`/`return` بدل ما ترفع الاستثناء للدالة كلها. صفر تغيير في `finance.transfer()`, `repo.create_*`, `audit_log`, `_register_affiliate_commission`, أو ترتيبهم النسبي مع بعض.

**تحقَّقت إن `logger` مستورَدة بالفعل في `tourism_sports/service.py`** (مستخدمة في استدعاءات `logger.warning(...)` موجودة سابقًا بالملف، مثلاً `AI transport optimization failed`) — صفر حاجة لإضافة import جديد.

**صفر `Edit` فعلي حتى الآن — بانتظار موافقتك الصريحة على هذا الديف تحديدًا قبل التطبيق.**

---

## 9) ✅ التطبيق [2026-08-18] — `git diff`/`git status` خام بعد التطبيق (`tourism_sports` فقط)

**موافقة صريحة استُلمت على الديف في قسم 8. تم التطبيق عبر 3 عمليات `Edit` مطابقة تمامًا للديف المعروض — صفر انحراف.**

### 9.1) ملاحظة ضرورية قبل قراءة الديف: ضوضاء من جلسة سابقة غير مرتبطة

`eppne-backend/app/domains/tourism_sports/service.py` كان **معدَّلًا بالفعل قبل بداية هذه الجلسة** (مؤكَّد من `git status` الأصلي في أول المحادثة) — تعديلات من جلسة `constructor-mismatch` سابقة (تحويل `self.finance`/`self.ai_service`/`self.saas_service`/`self.affiliate_service`/`self.invoicing_service` من instance attributes في `__init__` إلى instantiation محلي بـ`tenant_id` جوه كل دالة). بما إن `git diff` بيقارن القرص الحالي بآخر commit (مش بلحظة بداية الجلسة)، الناتج تحت فيه الاتنين مع بعض.

**تعديلاتي الفعلية في هذه الجلسة = 3 هنكات إزالة + 3 هنكات إضافة بس (نقل `create_invoice()` لبعد `commit()` + لفها بـ`try/except`):**

| نوع | الموقع في الديف تحت |
|---|---|
| إزالة `create_invoice()` من جوه `begin_nested()` — `book_program` | `@@ -170,14 +168,6 @@` |
| إضافة `create_invoice()` بعد `commit()` مع `try/except` — `book_program` | `@@ -200,6 +190,17 @@` |
| إزالة `create_invoice()` من جوه `begin_nested()` — `purchase_event_ticket` | `@@ -289,14 +293,6 @@` |
| إضافة `create_invoice()` بعد `commit()` مع `try/except` — `purchase_event_ticket` | `@@ -321,6 +317,17 @@` |
| إزالة `create_invoice()` من جوه `begin_nested()` — `place_transfer_bid` | `@@ -441,13 +450,6 @@` |
| إضافة `create_invoice()` بعد `commit()` مع `try/except` — `place_transfer_bid` | `@@ -462,6 +464,17 @@` |

**باقي الهنكات (`__init__`, `_check_saas_limits`, `ai_service`, `governance`, `affiliate_service` local instantiation) — من جلسة سابقة، صفر علاقة بي في هذه الجلسة.**

### 9.2) `git diff -- eppne-backend/app/domains/tourism_sports/service.py` (خام كامل)

```diff
diff --git a/eppne-backend/app/domains/tourism_sports/service.py b/eppne-backend/app/domains/tourism_sports/service.py
index c7f0b0e..7a6e98e 100644
--- a/eppne-backend/app/domains/tourism_sports/service.py
+++ b/eppne-backend/app/domains/tourism_sports/service.py
@@ -35,11 +35,6 @@ class TourismSportsService:
     def __init__(self, db: AsyncSession):
         self.db = db
         self.repo = TourismSportsRepository(db)
-        self.finance = FinanceService(db)
-        self.ai_service = AIAgentsService(db)
-        self.saas_service = SaaSSubscriptionService(db)
-        self.affiliate_service = AffiliateService(db)
-        self.invoicing_service = InvoicingService(db)
         self.event_bus = EventBus(cast(Any, redis_client))
         self.redis = redis_client
 
@@ -62,7 +57,8 @@ class TourismSportsService:
 
     # ========== التحقق من صلاحيات SaaS ==========
     async def _check_saas_limits(self, tenant_id: int, feature: str = "tourism_sports"):
-        has_access = await self.saas_service.can_access_service(tenant_id, feature)
+        saas_service = SaaSSubscriptionService(self.db, tenant_id)
+        has_access = await saas_service.can_access_service(tenant_id, feature)
         if not has_access:
             raise PermissionDeniedError("Tourism & Sports feature is not included in your current plan.")
         return None, {}
@@ -157,9 +153,11 @@ class TourismSportsService:
         if participants_count >= program.max_capacity:  # type: ignore
             raise InsufficientBalanceError("البرنامج مكتمل العدد")
 
+        finance = FinanceService(self.db, tenant_id)
+        invoice_service = InvoicingService(self.db, tenant_id)
         async with self.db.begin_nested():
             try:
-                tx_hash = await self.finance.transfer(
+                tx_hash = await finance.transfer(
                     sender_id=user_id,
                     receiver_email="tourism@eppne.com",
                     currency="MR_USDT",
@@ -170,14 +168,6 @@ class TourismSportsService:
             except InsufficientBalanceError:
                 raise PermissionDeniedError("Insufficient balance")
 
-            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=program.base_price_mrusdt,  # type: ignore
-                description=f"Tourism program booking: {program.title}",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
-
             await self._register_affiliate_commission(user_id, tenant_id, "PROGRAM_BOOKED", program.base_price_mrusdt)  # type: ignore
 
             nft_id = f"TKT-PROG-{program_id}-{user_id}-{uuid.uuid4().hex[:8].upper()}"
@@ -200,6 +190,17 @@ class TourismSportsService:
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=program.base_price_mrusdt,  # type: ignore
+                description=f"Tourism program booking: {program.title}",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for program booking {program_id}: {e}")
+
         # تخزين معرف المشارك فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"participant_id": participant.id})
@@ -265,8 +266,9 @@ class TourismSportsService:
             price += Decimal(50)
 
         if require_vip_transport:
+            ai_service = AIAgentsService(self.db, tenant_id)
             try:
-                await self.ai_service.execute_agent_action(  # type: ignore[call-arg]
+                await ai_service.execute_agent_action(  # type: ignore[call-arg]
                     agent_id=5,
                     tenant_id=tenant_id,
                     action_type="ANALYZE_SENSOR",
@@ -276,9 +278,11 @@ class TourismSportsService:
             except Exception as e:
                 logger.warning(f"AI transport optimization failed: {e}")
 
+        finance = FinanceService(self.db, tenant_id)
+        invoice_service = InvoicingService(self.db, tenant_id)
         async with self.db.begin_nested():
             try:
-                tx_hash = await self.finance.transfer(
+                tx_hash = await finance.transfer(
                     sender_id=user_id,
                     receiver_email="events@eppne.com",
                     currency="MR_USDT",
@@ -289,14 +293,6 @@ class TourismSportsService:
             except InsufficientBalanceError:
                 raise PermissionDeniedError("Insufficient balance")
 
-            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=price,
-                description=f"Event ticket: {event.title} ({tier})",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
-
             nft_id = f"TKT-{event_id}-{user_id}-{uuid.uuid4().hex[:12].upper()}"
             qr_data = hashlib.sha256(f"{nft_id}-{uuid.uuid4().hex}".encode()).hexdigest()[:16]
             ticket = await self.repo.create_ticket(
@@ -321,6 +317,17 @@ class TourismSportsService:
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=price,
+                description=f"Event ticket: {event.title} ({tier})",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for ticket purchase (event {event_id}): {e}")
+
         # تخزين معرف التذكرة فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"ticket_id": ticket.id})
@@ -402,8 +409,9 @@ class TourismSportsService:
 
         medical_flag = False
         medical_report = None
+        ai_service = AIAgentsService(self.db, tenant_id)
         try:
-            ai_result = await self.ai_service.execute_agent_action(  # type: ignore[call-arg]
+            ai_result = await ai_service.execute_agent_action(  # type: ignore[call-arg]
                 agent_id=6,
                 tenant_id=tenant_id,
                 action_type="ANALYZE_SENSOR",
@@ -420,7 +428,7 @@ class TourismSportsService:
             logger.warning(f"AI medical analysis failed: {e}")
 
         from app.domains.ai_governance.service import AIGovernanceService
-        governance = AIGovernanceService(self.db)
+        governance = AIGovernanceService(self.db, tenant_id)
         await governance.check_and_consume(
             tenant_id=tenant_id,
             agent_id=6,
@@ -429,6 +437,7 @@ class TourismSportsService:
             cost=Decimal("0.02")
         )
 
+        invoice_service = InvoicingService(self.db, tenant_id)
         async with self.db.begin_nested():
             transfer = await self.repo.create_transfer(
                 tenant_id=tenant_id,
@@ -441,13 +450,6 @@ class TourismSportsService:
             )
 
             agency_fee = data["bid_amount_mrusdt"] * (data.get("agency_fee_percentage", 10) / 100)
-            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
-                entity_id=tenant_id,
-                user_id=user_id,
-                amount=agency_fee,
-                description=f"Agency fee for transfer of player {player.user_id}",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
 
             if data.get("facilitating_agency_id"):
                 await self._register_affiliate_commission(user_id, tenant_id, "PLAYER_TRANSFER", agency_fee)
@@ -462,6 +464,17 @@ class TourismSportsService:
 
         await self.db.commit()
 
+        try:
+            await invoice_service.create_invoice(  # type: ignore[attr-defined]
+                entity_id=tenant_id,
+                user_id=user_id,
+                amount=agency_fee,
+                description=f"Agency fee for transfer of player {player.user_id}",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for player transfer bid {transfer.id}: {e}")
+
         # تخزين معرف التحويل فقط
         if idempotency_key:
             await self._store_idempotency(idempotency_key, {"transfer_id": transfer.id})
@@ -498,13 +511,14 @@ class TourismSportsService:
         action_type: str,
         amount: Decimal
     ):
+        affiliate_service = AffiliateService(self.db, tenant_id)
         try:
             from app.domains.identity.repository import UserRepository
             user_repo = UserRepository(self.db)
             user = await user_repo.get_by_id(user_id)
             if user and user.referred_by:
                 commission = amount * Decimal("0.05")
-                await self.affiliate_service.register_commission(  # type: ignore[attr-defined]
+                await affiliate_service.register_commission(  # type: ignore[attr-defined]
                     affiliate_id=user.referred_by,
                     user_id=user_id,
                     amount=commission,
```

### 9.3) `git status --porcelain` (خام كامل، لحظة كتابة هذا القسم)

```
 M .claude/reports/phase16-session-log.md
 M PROGRESS_LOG.md
 M eppne-backend/app/api/deps.py
 D eppne-backend/app/domains/agritech/router.py
 M eppne-backend/app/domains/arbitration_syndicates/service.py
 M eppne-backend/app/domains/automation/service.py
 M eppne-backend/app/domains/digital_twin/service.py
 M eppne-backend/app/domains/employment/service.py
 M eppne-backend/app/domains/health/service.py
 M eppne-backend/app/domains/insurance/service.py
 M eppne-backend/app/domains/invitations/service.py
 M eppne-backend/app/domains/invoicing/router.py
 M eppne-backend/app/domains/iot/service.py
 M eppne-backend/app/domains/logistics/service.py
 M eppne-backend/app/domains/manufacturing/service.py
 M eppne-backend/app/domains/projects/service.py
 M eppne-backend/app/domains/realestate/service.py
 M eppne-backend/app/domains/service_marketplace/service.py
 M eppne-backend/app/domains/social/service.py
 M eppne-backend/app/domains/tenders_auctions/service.py
 M eppne-backend/app/domains/tourism_sports/service.py
 M eppne-backend/app/domains/transport/service.py
 M eppne-backend/app/domains/zamakana/service.py
 M eppne-backend/app/main.py
 M eppne-backend/app/tasks/affiliate.py
 M eppne-backend/app/tasks/agritech.py
 M eppne-backend/app/tasks/billing.py
 M eppne-backend/app/tasks/employment.py
 M eppne-web/app/(dashboard)/academy/[id]/page.tsx
 M eppne-web/app/(dashboard)/academy/certificates/[courseId]/page.tsx
 M eppne-web/app/(dashboard)/academy/instructor/dashboard/page.tsx
 M eppne-web/app/(dashboard)/academy/my-learning/page.tsx
 M eppne-web/app/globals.css
 M eppne-web/components/academy/CourseActionButton.tsx
 M eppne-web/components/layout/theme-toggle.tsx
?? .claude/plans/phase10-audit-affiliate-report.md
?? .claude/plans/phase5-frontend-auth-identity-dedup.md
?? .claude/plans/phase6-ai-routing-authz-fix.md
?? .claude/plans/phase7-iot-privacy-tenant-isolation-execution.md
?? .claude/plans/phase7-iot-privacy-tenant-isolation-planning.md
?? .claude/plans/phase8-master-roadmap.md
?? .claude/plans/phase9-audit-identity-report.md
?? .claude/plans/phase9-audit-identity.md
?? .claude/plans/phase9b-fix-login-response-leak.md
?? .claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md
?? .claude/reports/constructor-mismatch-backlog-12-15-16-homogeneity-audit.md
?? .claude/reports/constructor-mismatch-backlog-classification.md
?? .claude/reports/constructor-mismatch-batch3-session-log.md
?? .claude/reports/constructor-mismatch-session-log.md
?? .claude/reports/invitations-savepoint-leak-session-log.md
?? .claude/reports/progress-log-reorg-2026-08-18-proposal.md
?? .claude/reports/realestate-insurance-savepoint-fix-session-log.md
?? .claude/skills/
?? eppne-web/academy-audit.txt
?? eppne-web/blocked-files-list.txt
?? eppne-web/full-frontend-audit.txt
?? eppne-web/globals-and-toggle-verification.txt
?? eppne-web/globals-css-diff.txt
?? eppne-web/globals-maat-proposed.css
?? eppne-web/learn-page-service-check.txt
?? eppne-web/link-fix-verification.txt
?? eppne-web/sample-cleanup-diff.txt
?? eppne-web/stash-verification.txt
?? eppne-web/theme-toggle-revision.txt
?? eppne-web/theme-toggle-visibility-check.txt
?? frontend-structure.txt
?? project_tree.txt
```

**كل الملفات المعدَّلة/غير المتابَعة هنا (غير `tourism_sports/service.py`, `PROGRESS_LOG.md`, وملف هذا التقرير نفسه) كانت موجودة بنفس الحالة من قبل بداية هذه الجلسة — صفر لمس مني عليها.**

**الحالة: بانتظار قرارك — هل الديف المطبَّق مطابق لتوقعك؟ لو موافق، الخطوة التالية هي التحقق الحي (سيناريو نظيف × 3 + سيناريو فشل مُفتعَل في `create_invoice()`).**

---

## 10) 🔴 تصحيح صريح [2026-08-18] — الادعاء السابق "`tourism_sports` مكشوفة بلا أي حماية" غلط

**الادعاء الأصلي (بانر `PROGRESS_LOG.md`، قسم 2/3 من هذا التقرير):** `tourism_sports` غير محمية بأي كراش وقائي، بعكس `realestate`/`insurance`/`zamakana` المحميين بكراش #9. **هذا الادعاء غير دقيق — تم اكتشاف حماية فعلية بالصدفة من بج مختلف (Backlog #12) قبل الانتقال لمرحلة التحقق الحي.**

### 10.1) الدليل

`tourism_sports/service.py` (النسخة الحالية على القرص، بعد pre-existing تعديلات `constructor-mismatch`):

```python
async def _check_saas_limits(self, tenant_id: int, feature: str = "tourism_sports"):
    saas_service = SaaSSubscriptionService(self.db, tenant_id)
    has_access = await saas_service.can_access_service(tenant_id, feature)   # ← معاملان
    if not has_access:
        raise PermissionDeniedError("Tourism & Sports feature is not included in your current plan.")
    return None, {}
```

`saas/service.py:209` — التوقيع الفعلي لـ`SaaSControlService.can_access_service`:

```python
async def can_access_service(self, service_code: str) -> bool:   # ← معامل واحد بس
```

**استدعاء بمعاملين (`tenant_id, feature`) على method توقيعها معامل واحد (`service_code`) → `TypeError: can_access_service() takes 2 positional arguments but 3 were given` فوري.** هذا **مطابق حرفيًا لباج موثَّق مسبقًا: Backlog #12 (`saas-control-service-wrong-arity-call`)** — وتحقَّقت إنه **نفس الاستدعاء بالحرف** الموجود في `service_marketplace/service.py:70` (`await saas_service.can_access_service(tenant_id, "service_marketplace")`)، اللي كان موثَّق مسبقًا في تقرير #9 قسم 4.5 كمثال على #12.

### 10.2) الأثر على التقييم

- **`_check_saas_limits` بتتنادى كأول سطر فعلي في الدوال الثلاثة كلها** (`book_program:133`, `purchase_event_ticket:243`, `place_transfer_bid:383` — أرقام السطور قبل تعديلات هذه الجلسة) — يعني الكراش بيحصل **قبل** أي وصول لـ`finance.transfer`/`create_invoice`/أي كتابة DB إطلاقًا.
- **النتيجة: `tourism_sports` كانت (ولسه، حتى بعد تطبيق ديف #11b) محمية فعليًا بكراش #12 وقائي — بالضبط نفس نمط "الحماية بالصدفة" اللي وثّقناه لـ`realestate`/`insurance` (بسبب #9) و`zamakana` (بسبب #9 كمان).** الفرق الوحيد: السبب هنا #12 مش #9.
- **تصحيح درجة الإلحاح:** `tourism_sports` **مش** "المخاطرة الحية الوحيدة غير المحمية دلوقتي" كما ورد في البانر — **كل السبع دوال (الأربعة الأصلية + الثلاثة في `tourism_sports` + `zamakana`) محمية حاليًا بأحد كراشين وقائيين (#9 أو #12)، صفر منها مكشوف فعليًا في الإنتاج الآن.** الأولوية الحرجة لإصلاح #11b تبقى قائمة (لأن #9 و#12 قيد الحل لاحقًا وهيكشفوا نفس الفخ)، لكن **بدون الاستعجال الزائف اللي أوحى بيه البانر الحالي**.

### 10.3) الأثر العملي على منهجية التحقق الحي

بما إن `_check_saas_limits` بتكراش بـ`TypeError` قبل الوصول لأي كود من كود #11b، **التحقق الحي المباشر (بدون تجاوز) مستحيل فعليًا** — لازم `monkeypatch`/تجاوز مؤقت لـ`_check_saas_limits` في سكريبت التحقق نفسه (بره `app/` بالكامل، Scratchpad فقط)، **تمامًا بنفس المنهجية اللي استخدمها سكريبت تحقق `invitations`** لتجاوز كراش #9 حينها. صفر تعديل على كود `app/` نفسه لأجل التحقق.

**القرار المطلوب:** موافقة صريحة على المتابعة بالـmonkeypatch ده لسكريبت التحقق الحي، قبل كتابة أي سكريبت فعلي.

---

## 11) ✅ موافقة المستخدم [2026-08-18] + تصحيحان إضافيان قبل سكريبت التحقق

**موافقة صريحة مستلَمة على `monkeypatch` لتجاوز #12 (نفس منهجية `invitations` لتجاوز #9)، بره `app/` بالكامل.**

### 11.1) تصحيح حسابي إضافي: العدد الصحيح 8 دوال، مش 7

راجعت القائمة الفعلية المذكورة في قسم 3 (قرار توسيع النطاق): `realestate.buy_fractional_ownership`, `realestate.rent_unit`, `insurance.subscribe`, `insurance.review_claim`, `zamakana.pledge_time`, `tourism_sports.book_program`, `tourism_sports.purchase_event_ticket`, `tourism_sports.place_transfer_bid` = **8 دوال بالعد الفعلي**، مش 7 كما ورد مرارًا في أقسام هذا التقرير (خطأ حسابي مني، 4+3+1=8 مش 7). **تصحيح `PROGRESS_LOG.md`** (بانر + جدول Backlog) تم لهذا الرقم. باقي إشارات "7 دوال"/"السبعة" في الأقسام السابقة من هذا التقرير **تُركت كما هي كسجل تاريخي لحظة كتابتها** (مش تُعدَّل بأثر رجعي) — هذا القسم هو المرجع الحسابي الصحيح من الآن فصاعدًا.

### 11.2) 🔑 الجدول النهائي — أي كراش وقائي بيحمي كل دالة من الثمانية دلوقتي

| # | الدالة | نمط `_check_saas_limits` المستخدَم | الاستثناء الناتج | الباج المسبب |
|---|---|---|---|---|
| 1 | `realestate.buy_fractional_ownership` | `saas.get_active_subscription(tenant_id)` — method غير موجودة على `SaaSControlService` | `AttributeError` | **#9** |
| 2 | `realestate.rent_unit` | نفس `_check_saas_limits` (method مشتركة في نفس الملف) | `AttributeError` | **#9** |
| 3 | `insurance.subscribe` | `saas_service.get_active_subscription(tenant_id)` | `AttributeError` | **#9** |
| 4 | `insurance.review_claim` | نفس `_check_saas_limits` المشتركة | `AttributeError` | **#9** |
| 5 | `zamakana.pledge_time` | `saas_service.can_access_service(tenant_id, feature)` — توقيعها الفعلي معامل واحد بس | `TypeError` (wrong arity) | **#12** |
| 6 | `tourism_sports.book_program` | `saas_service.can_access_service(tenant_id, feature)` | `TypeError` (wrong arity) | **#12** |
| 7 | `tourism_sports.purchase_event_ticket` | نفس `_check_saas_limits` المشتركة | `TypeError` (wrong arity) | **#12** |
| 8 | `tourism_sports.place_transfer_bid` | نفس `_check_saas_limits` المشتركة **+ طبقة حماية ثانية مستقلة: `AIGovernanceService.check_and_consume(tenant_id=..., ...)` (قبل `begin_nested()`, بلا `try/except`) بتبعت `tenant_id` كـkwarg غير موجود في التوقيع الفعلي + ناقصة `action_type` الإجبارية** | `TypeError` (wrong arity) من #12 أولًا، ثم `TypeError` تاني (kwarg غير موجود) من **#15** لو #12 اتجاوزت | **#12 ثم #15 (طبقتان، مش طبقة واحدة زي باقي دوال `tourism_sports`)** |

**ملاحظة إضافية [2026-08-18]:** `place_transfer_bid` هي الدالة الوحيدة من الثمانية المحمية بطبقتين مستقلتين وليس طبقة واحدة — لازم تجاوز #12 **و**#15 معًا (بالإضافة لـ#14 على `audit_log` جوه `begin_nested()`) للوصول الفعلي لكود #11b فيها أثناء التحقق الحي. باقي الدوال السبعة محمية بطبقة `_check_saas_limits` واحدة فقط (+ #14 على `audit_log` في الدوال الثلاثة بـ`tourism_sports`).

**تأكيد صريح مطلوب في الطلب:** فحصت `_check_saas_limits` الخاصة بكل دومين من الأربعة مباشرة بالقراءة (مش افتراض) — **صفر دالة من الثمانية تعتمد على أي نمط تالت غير الاتنين دول (#9 أو #12).** `realestate`/`insurance` (4 دوال) = `get_active_subscription` = #9 حصرًا. `zamakana`/`tourism_sports` (4 دوال) = `can_access_service` بمعاملين خطأ = #12 حصرًا. **مفيش دالة "آمنة" ببج تالت لسه ما اتكشفش — كل الثمانية مغطاة بالجدول ده بالكامل.**

---

## 12) 🟡 حالة التحقق الحي — قيد التنفيذ، متوقفة مؤقتًا (Checkpoint)

**الموافقات المستلَمة قبل هذا القسم:** `monkeypatch` موسَّع لـ#12 + #14 + #15 (بره `app/` بالكامل)، سكريبت تحقق واحد بيغطي `book_program`/`purchase_event_ticket`/`place_transfer_bid` — لكل واحدة سيناريو نظيف + سيناريو فشل مُفتعَل في `create_invoice()` تحديدًا (نفس منهجية `invitations`).

### 12.1) السكريبت

`C:\Users\Hp\AppData\Local\Temp\claude\E--cc\f8303d47-7dc3-4ea9-8dee-1704353b3c98\scratchpad\verify_tourism_savepoint_fix.py` — Scratchpad فقط، **صفر تعديل على `app/`**. بينادي `TourismSportsService` الحقيقية مباشرة (مش إعادة كتابة منطقها). بيانات throwaway جديدة تمامًا بادئة `p_tourism_verify_*` (7 يوزرات، برنامج سياحي، فعالية، 3 أندية رياضية، بروفايل لاعب — كلهم تحت `tenant_id=1`). آلية الفشل المُفتعَل: `monkeypatch` مؤقت (`try/finally`) على `InvoicingService.create_invoice` نفسها ليرفع `RuntimeError("SIMULATED-FAILURE-CREATE-INVOICE")` أثناء سيناريو الفشل بس، ثم استرجاع الدالة الأصلية فورًا بعده.

### 12.2) 🔴 عائق فني — السكريبت فشل في محاولة التشغيل الأولى، لسه ما اتصلحش

```
sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[User(users)],
expression 'app.domains.academy.models.AcademyTenant' failed to locate a name
("Module 'domains' has no mapped classes registered under the name 'academy'").
```

**السبب:** السكريبت بيستورد بس الموديلات اللي محتاجها مباشرة (`identity`, `finance`, `tourism_sports`)، لكن `User` (`identity/models.py`) عندها `relationship()` بيشير لموديل `academy.models.AcademyTenant` بالاسم النصي (string reference) — SQLAlchemy محتاج كل موديلات المشروع تكون متسجلة في الـmapper registry وقت إنشاء أول كائن `User()`، مش بس اللي استوردناها إحنا. **الحل المعروف (لسه ما اتطبقش):** إضافة `import app.main` (أو أي نقطة دخول تستورد كل الدومينات) في أول السكريبت قبل أي إنشاء كائن ORM — بيضمن تسجيل كل الموديلات. **صفر علاقة بكود #11b نفسه — عائق بيئة تشغيل السكريبت بس.**

### 12.3) الحالة الحالية

- **صفر تنفيذ ناجح حتى الآن** — لا سيناريو نظيف ولا سيناريو فشل اتنفذ فعليًا. السكريبت كراش في مرحلة الـseeding (إنشاء أول يوزر throwaway)، قبل ما يوصل لأي كود من `tourism_sports.service` أو `invoicing`.
- **صفر بيانات throwaway اتسجلت فعليًا على القرص** — الكراش حصل قبل أي `commit()` في السكريبت.
- **الخطوة التالية:** إضافة `import app.main` لأول السكريبت، إعادة التشغيل، ثم التحقق المستقل (`docker exec eppne_db psql` لكل من: `program_participants`/`nft_tickets`/`player_transfers`، `wallets`/`transactions`، `invoices`؛ + `docker exec redis redis-cli` لتأكيد مفاتيح idempotency).

**الجلسة متوقفة هنا مؤقتًا بسبب حد استخدام تقني (usage limit) — مش بسبب قرار أو اكتشاف جديد يستوجب سؤالك. هتُستكمل من هنا في الرد التالي.**

### 12.4) نتيجة التشغيلتين الفعليتين + 🔴 اكتشاف جديد يستوجب توقف (شرط الإيقاف #4)

**تشغيلة 1** (`import app.main` مُضاف): الـseeding نجح بالكامل (يوزرات 73-79، برنامج/فعالية/أندية/بروفايل لاعب). الـ6 سيناريوهات كلها فشلت. **تشغيلة 2** (بعد إصلاح خطأ مني في تمرير `player_id` كـ`PlayerProfile.id` بدل `user_id` — `get_player_profile(user_id)` بتفلتر بـ`user_id`، أكَّدت من `repository.py:104-108`) كشفت السبب الحقيقي لكل فشل بوضوح (بعد فرض `PYTHONIOENCODING=utf-8`):

1. **`book_program`/`purchase_event_ticket` (4 نتائج): `NotFoundError: المستلم غير موجود`** — من `finance.transfer()` نفسها: المستلمين المُشفَّرين في الكود (`tourism@eppne.com`, `events@eppne.com`) مش موجودين كيوزرات فعلية تحت `tenant_id=1`. **مش باج — ثغرة بيانات seed في سكريبت التحقق بس** (لازم ننشئ يوزرين throwaway بهذين الإيميلين تحديدًا). صفر علاقة بكود #11b.

2. **`place_transfer_bid` (نتيجتان): `IntegrityError: ForeignKeyViolationError` — `player_transfers.player_id` FK بيشاور على `player_profiles.id`، لكن `place_transfer_bid` بتمرر `data["player_id"]` كما هو (اللي هو `user_id` الخاص باللاعب، مُستخدَم كده في `get_player_profile(data["player_id"])` — دالة بتفلتر بـ`PlayerProfile.user_id`) مباشرة جوه `**data` للـINSERT، فبيحصل تعارض: نفس القيمة بتتعامل كـ`user_id` في السطر اللي فاتت وكـ`PlayerProfile.id` في الـINSERT.** 🔴 **هذا باج تطبيقي حقيقي في `place_transfer_bid` نفسها (تضارب دلالي بين `user_id` و`PlayerProfile.id` تحت نفس الاسم `player_id`) — خارج فئات #9/#12/#14/#15 الموثَّقة، ومنفصل تمامًا عن #11b.** يفعِّل شرط الإيقاف #4 صراحةً.

**الحالة: متوقفة بانتظار توجيهك بخصوص الاكتشاف الجديد في `place_transfer_bid` (بند Backlog منفصل؟ أولوية؟)، ثم إذن لإصلاح بيانات الـseed (مستلمين `tourism@eppne.com`/`events@eppne.com`) والمتابعة لـ`book_program`/`purchase_event_ticket` فقط في الوقت الحالي.**

### 12.5) ✅ قرار المستخدم [2026-08-18]

1. **مستلمين `tourism@`/`events@`:** مؤكَّد مشكلة seed بس — إصلاح وإعادة تشغيل.
2. **باج `place_transfer_bid`:** تم توثيقه كبند Backlog جديد منفصل في `PROGRESS_LOG.md` (`tourism-place-transfer-bid-player-id-user-id-conflict`، أولوية عادية-مرتفعة، برّه نطاق #11b تمامًا). **صفر إصلاح له في هذه الجلسة.**

**تأكيد صريح مطلوب — هل الباج مسبق بغض النظر عن ديف #11b؟** ✅ **نعم، مؤكَّد قطعيًا.** السطر المسبِّب للكراش هو `repo.create_transfer(**data)` (`tourism_sports/service.py`، جوه `begin_nested()`) — وهذا السطر **لم يُلمَس إطلاقًا** في ديف #11b المطبَّق على `place_transfer_bid` (قسم 8/9 أعلاه): تعديلنا الوحيد هناك كان نقل استدعاء `invoicing.create_invoice()` من مكانه (كان بعد `agency_fee = ...` مباشرة) إلى بعد `await self.db.commit()`، بلا أي لمس على `repo.create_transfer(**data)` أو على بناء `data` نفسها أو على `get_player_profile(data["player_id"])`. **بمعنى آخر: لو شغّلنا نفس سيناريو التحقق على النسخة الأصلية من `place_transfer_bid` (قبل ديف #11b تمامًا)، كان هيوصل لنفس `IntegrityError` بالحرف — الكراش بيحصل عند `repo.create_transfer` جوه `begin_nested()`، قبل ما الكود يوصل حتى لموضع `create_invoice()` الأصلي أو الجديد. هذا باج مسبق مكتشَف أثناء هذه الجلسة، مش regression ناتج عن ديف #11b.**

**أثر على معيار إغلاق #11b لـ`place_transfer_bid` تحديدًا:** بما إن الباج ده بيمنع أي تنفيذ فعلي للدالة (حتى بعد تجاوز #12/#15)، **`place_transfer_bid` لن يحصل على تحقق حي كامل (سيناريو نظيف + سيناريو فشل مُفتعَل) ضمن هذه الجلسة** — التحقق منها هيقتصر على: (أ) مراجعة الديف/الكود مباشرة (تأكيد إن `create_invoice()` انتقلت لمكانها الصحيح بعد `commit()`، ملفوفة بـ`try/except`، بنفس معيار باقي الدوال)، (ب) تأكيد منطقي إن نقل `create_invoice()` بمعزل تام عن السطر المسبِّب لباج `player_id`/`PlayerProfile.id` (مفيش تفاعل بين الاثنين). **هذا مستوى تحقق أضعف من `book_program`/`purchase_event_ticket` (اللي هياخدوا تحقق حي كامل بـSELECT مستقل)** — هيُذكر صراحة في ختم الإغلاق النهائي لـ#11b، مش هيتعامل كأنه بنفس القوة.

### 12.6) 🔴 اكتشاف جديد تاني — `book_program` أيضًا محجوبة، بباج مختلف عن `place_transfer_bid`

بعد إصلاح بيانات الـseed (يوزرين throwaway `tourism@eppne.com`/`events@eppne.com` تحت `tenant_id=1`)، **`purchase_event_ticket` نجحت في السيناريوهين، لكن `book_program` فشلت بباج جديد مختلف تمامًا:**

```
DataError: invalid input for query argument $8: <app.domains.finance.models.Transaction ...> (expected str, got Transaction)
[SQL: INSERT INTO program_participants (..., payment_tx_hash) VALUES (..., $8::VARCHAR) ...]
```

**السبب:** `FinanceService.transfer()` (`finance/service.py`) بترجع `tx` — كائن `Transaction` ORM **كامل** (`return tx` في نهاية الدالة)، مش نص `tx_hash`. `book_program` بتمرر الناتج مباشرة: `payment_tx_hash=tx_hash` لعمود `ProgramParticipant.payment_tx_hash` (`String(100)`) → `DataError`.

**مؤكَّد إنه مسبق تمامًا:** السطر `payment_tx_hash=tx_hash` جوه `begin_nested()`، **غير ملموس إطلاقًا** في ديف #11b (اللي اقتصر على نقل `create_invoice()` بعد `commit()`). `purchase_event_ticket` نجت من نفس الفخ فقط لأن `NFTTicket` مالهاش عمود `payment_tx_hash` من الأساس (فرق بنية بيانات، مش فرق في جودة الكود).

**قرار المستخدم [2026-08-18]:** توثيق كبند Backlog منفصل (`finance-transfer-returns-transaction-object-not-tx-hash-string`، `PROGRESS_LOG.md`)، **تخطي `book_program` من التحقق الحي الكامل زي `place_transfer_bid`** (نفس مستوى التحقق المخفَّض: مراجعة ديف/كود بس). **ملاحظة غير مؤكَّدة بعد، للمتابعة عند الوصول لـ`realestate`/`insurance`:** نمط مشابه بالعين المجردة موجود في `realestate.buy_fractional_ownership` (`purchase_tx_hash=tx_hash`) و`insurance.review_claim` (`payout_tx_hash=payout_tx`) — **يحتاج تأكيد مباشر وقتها، مش افتراض**.

### 12.7) ✅ التحقق الحي الناجح الوحيد المكتمل بالكامل — `purchase_event_ticket`

**سيناريو نظيف (`ticket_clean`, user_id=91):**

| الجدول | النتيجة |
|---|---|
| `nft_tickets` | `id=1, owner_id=91, tier=GENERAL, purchase_price_mrusdt=15.0, idempotency_key=P-TOURISM-VERIFY-TICKET-CLEAN-b02439` — **موجودة فعليًا** |
| `wallets.balances->>'MR_USDT'` (user 91) | `985.0` (كان 1000، خُصم 15) — **التحويل نجح فعليًا** |
| `transactions` | `sender=91→receiver=88 (events@eppne.com), amount=15, status=COMPLETED` |
| `invoices` | `id=11, user_id=91, amount=15, description='Event ticket: ...', status=PENDING` — **الفاتورة اتسجلت فعليًا بعد `commit()`** |
| Redis `idempotent:P-TOURISM-VERIFY-TICKET-CLEAN-b02439` | `{"ticket_id": 1}` — **`_store_idempotency()` نفَّذت بنجاح** |

**سيناريو الفشل المُفتعَل (`ticket_fail`, user_id=92, `create_invoice()` مُتعطَّلة عمدًا بـ`RuntimeError`):**

| الجدول | النتيجة |
|---|---|
| `nft_tickets` | `id=2, owner_id=92, tier=GENERAL, purchase_price_mrusdt=15.0` — **موجودة فعليًا رغم فشل الفاتورة** |
| `wallets.balances->>'MR_USDT'` (user 92) | `985.0` — **التحويل المالي نجح فعليًا والتزم، رغم فشل الفاتورة بعده** |
| `transactions` | `sender=92→receiver=88, amount=15, status=COMPLETED` |
| `invoices` | **صفر صف لـuser 92** — تأكيد قاطع إن `create_invoice()` فشلت فعلًا (`RuntimeError` مُفتعَل) وما اتسجلتش فاتورة، **بلا ما تؤثر على أي حاجة تانية** |
| Redis `idempotent:P-TOURISM-VERIFY-TICKET-FAIL-b02439` | `{"ticket_id": 2}` — **`_store_idempotency()` نفَّذت بنجاح رغم فشل الفاتورة** (بفضل `try/except` الجديد) |
| نتيجة السكريبت | `{"ok": True, "ticket_id": 2}` — **الدالة رجّعت بنجاح، صفر استثناء اتصعّد للمستدعي** |

**الخلاصة القاطعة:** إصلاح #11b شغّال بالضبط كما هو مخطَّط لـ`purchase_event_ticket` — التحويل المالي وإنشاء التذكرة يلتزموا معًا كوحدة ذرية واحدة بغض النظر عن نجاح/فشل الفاتورة، والفاتورة بقت خطوة "إيصال" منفصلة حقيقية بعدها، والـidempotency بتتخزن حتى لو الفاتورة فشلت (بفضل `try/except`).

### 12.8) ملخص تغطية `tourism_sports` (3 دوال)

| الدالة | مستوى التحقق | النتيجة |
|---|---|---|
| `purchase_event_ticket` | ✅ تحقق حي كامل (نظيف + فشل مُفتعَل + SELECT/Redis مستقل) | ✅ نجح بالكامل |
| `book_program` | 🟡 مراجعة ديف/كود بس — محجوبة ببج مسبق منفصل (`finance.transfer` ترجع `Transaction` مش `tx_hash`) | ديف صحيح بالقراءة، بلا تحقق حي |
| `place_transfer_bid` | 🟡 مراجعة ديف/كود بس — محجوبة ببج مسبق منفصل (`player_id`/`PlayerProfile.id`) | ديف صحيح بالقراءة، بلا تحقق حي |

**الحالة: بانتظار توجيهك للخطوة التالية — إغلاق `tourism_sports` بهذا المستوى المختلط من التحقق والانتقال لـ`realestate`/`insurance`؟**

---

## 13) ✅ تأكيد مسبق بالقراءة فقط [2026-08-18] — أثر باج `Transaction`/`tx_hash` على `realestate`/`insurance`

بطلب صريح، قبل بدء ديف `realestate`/`insurance`: فحصت مباشرة (`grep`/قراءة موديلات، بلا تشغيل) هل نفس باج `finance-transfer-returns-transaction-object-not-tx-hash-string` (قسم 12.6) بيؤثر على الأربع دوال.

| الدالة | العمود | القيمة الممرَّرة | العمود `String`؟ | متأثرة؟ |
|---|---|---|---|---|
| `realestate.buy_fractional_ownership` | `PropertyOwnership.purchase_tx_hash` (`models.py:160`) | `tx_hash` (راجع من `finance.transfer()` مباشرة) | ✅ `String(100)` | 🔴 **متأثرة — نفس الباج بالحرف** |
| `realestate.rent_unit` | `RentalContract.contract_tx_hash` | `f"RENT-{uuid.uuid4()...}"` (نص مولَّد يدويًا، **صفر `finance.transfer()` في الدالة أصلًا**) | ✅ `String(100)` | ✅ غير متأثرة |
| `insurance.subscribe` | `InsuranceSubscription.subscription_tx_hash` | `f"SUB-{uuid.uuid4()...}"` (نص مولَّد يدويًا، مش من `finance.transfer()`) | ✅ `String(100)` | ✅ غير متأثرة |
| `insurance.review_claim` | `InsuranceClaim.payout_tx_hash` (`models.py:144`) | `payout_tx` (راجع من `finance.transfer()` مباشرة) | ✅ `String(100)` | 🔴 **متأثرة — نفس الباج بالحرف** |

**النتيجة معروفة ومتوقَّعة قبل أي ديف — مش هتوقفنا في المنتصف زي `tourism_sports`:**
- `buy_fractional_ownership` و`review_claim`: هياخدوا **نفس مستوى تحقق `book_program`** — مراجعة ديف/كود فقط، بلا تحقق حي كامل (السبب مسبق تمامًا، غير متأثر بديف #11b — نفس منطق التأكيد في قسم 12.6).
- `rent_unit` و`subscribe`: **مرشَّحتان لتحقق حي كامل** (نفس مستوى `purchase_event_ticket`) — بلا عائق معروف حاليًا.

**`PROGRESS_LOG.md` اتحدَّث لتأكيد هذا الأثر على بند الـBacklog الموجود (بلا فتح بند جديد — نفس الباج).**

---

## 14) الديف الحرفي — `realestate` + `insurance` (4 دوال) — بانتظار الموافقة

**🔴 تنبيه حاسم قبل الديف — أثر باج `Transaction`/`tx_hash` على `insurance.review_claim` تحديدًا:**

مسار `approve=True` (الوحيد اللي بينادي `finance.transfer`+`create_invoice`) بيمر إجباريًا بـ`repo.update_claim(payout_tx_hash=payout_tx, ...)` **جوه نفس `begin_nested()`، قبل ما نوصل حتى لـ`await self.db.commit()`** — يعني الباج المسبق ده هيمنع الوصول لـ`commit()` أصلًا في مسار الموافقة، **بغض النظر عن ديف #11b تمامًا**. **معنى ده عمليًا: أهم نقطة تحقق طلبتها (claim.status→PAID مع payout_tx_hash) مش هينفع تتحقق حيًا في هذه الجلسة** — مسار الرفض (`approve=False`) وحده قابل للتنفيذ لكنه لا يستدعي `create_invoice()` أصلًا فمش بيختبر #11b. `review_claim` هتاخد نفس مستوى "مراجعة ديف/كود بس" زي `book_program`/`place_transfer_bid`.

**مرشَّحتان لتحقق حي كامل:** `realestate.rent_unit` و`insurance.subscribe` (غير متأثرين بباج `tx_hash`).

### 14.1) `realestate.buy_fractional_ownership` (🟡 مراجعة كود بس)

```diff
             except InsufficientBalanceError:
                 raise PermissionDeniedError("Insufficient balance")
 
-            # إنشاء فاتورة
-            await invoicing.create_invoice(  # type: ignore
-                entity_id=tenant_id,
-                user_id=buyer_id,
-                amount=cost,
-                description=f"Fractional ownership purchase: {percentage}% of unit {unit_id}",
-                due_date=datetime.utcnow() + timedelta(days=30)
-            )
-
             await self._register_affiliate_commission(buyer_id, tenant_id, cost)
 
             deed_nft = f"EPPNE-DEED-{unit_id}-{buyer_id}-{uuid.uuid4().hex[:8].upper()}"
@@ ... (باقي البلوك بلا تغيير: create_ownership, update_unit_availability, event_bus.publish, audit_log, _send_notification) ...
 
         await self.db.commit()
 
+        try:
+            await invoicing.create_invoice(  # type: ignore
+                entity_id=tenant_id,
+                user_id=buyer_id,
+                amount=cost,
+                description=f"Fractional ownership purchase: {percentage}% of unit {unit_id}",
+                due_date=datetime.utcnow() + timedelta(days=30)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for fractional ownership purchase (unit {unit_id}): {e}")
+
         # تخزين البيانات كاملة مع استخدام cast لتوضيح الأنواع
         if idempotency_key:
```

### 14.2) `realestate.rent_unit` (✅ مرشَّحة لتحقق حي كامل)

```diff
             first_payment = monthly_rent * Decimal(1)
-            await invoicing.create_invoice(  # type: ignore
-                entity_id=tenant_id,
-                user_id=tenant_user_id,
-                amount=first_payment,
-                description=f"First month rent for unit {unit_id}",
-                due_date=datetime.utcnow() + timedelta(days=3)
-            )
 
         await self.db.commit()
 
+        try:
+            await invoicing.create_invoice(  # type: ignore
+                entity_id=tenant_id,
+                user_id=tenant_user_id,
+                amount=first_payment,
+                description=f"First month rent for unit {unit_id}",
+                due_date=datetime.utcnow() + timedelta(days=3)
+            )
+        except Exception as e:
+            logger.error(f"Invoice creation failed for rental contract (unit {unit_id}): {e}")
+
         await self._register_affiliate_commission(tenant_user_id, tenant_id, first_payment)
```

### 14.3) `insurance.subscribe` (✅ مرشَّحة لتحقق حي كامل)

```diff
                 except InsufficientBalanceError:
                     raise PermissionDeniedError("Insufficient balance for premium payment")
 
-                await invoice_service.create_invoice(  # type: ignore
-                    entity_id=tenant_id,
-                    user_id=user_id,
-                    amount=premium,
-                    description=f"Insurance premium: {policy.name}",
-                    due_date=datetime.utcnow() + timedelta(days=30)
-                )
-
                 await self._register_affiliate_commission(user_id, tenant_id, "INSURANCE_SUBSCRIPTION", premium)
 
             sanitized_beneficiaries = self._sanitize_json(data.get("beneficiaries_json", {}))
@@ ... (create_subscription بلا تغيير) ...
 
         await self.db.commit()
 
+        if premium > 0:
+            try:
+                await invoice_service.create_invoice(  # type: ignore
+                    entity_id=tenant_id,
+                    user_id=user_id,
+                    amount=premium,
+                    description=f"Insurance premium: {policy.name}",
+                    due_date=datetime.utcnow() + timedelta(days=30)
+                )
+            except Exception as e:
+                logger.error(f"Invoice creation failed for insurance subscription {subscription.id}: {e}")
+
         await self.event_bus.publish({
```

### 14.4) `insurance.review_claim` (🟡 مراجعة كود بس — محجوبة ببج `tx_hash` قبل الوصول لـ`commit()`)

```diff
                     idempotency_key=payment_idempotency
                 )
 
-                await invoice_service.create_invoice(  # type: ignore
-                    entity_id=tenant_id,
-                    user_id=claim.claimant_user_id,  # type: ignore
-                    amount=final_amount,
-                    description=f"Insurance claim payout: {cast(Any, policy).name}",
-                    due_date=datetime.utcnow()
-                )
-
                 claim = await self.repo.update_claim(
                     claim_id,
                     status=ClaimStatus.PAID,
                     approved_amount_mrusdt=final_amount,
                     payout_tx_hash=payout_tx,
                     investigation_notes=notes
                 )
             else:
                 claim = await self.repo.update_claim(
                     claim_id, status=ClaimStatus.REJECTED, investigation_notes=notes
                 )
 
         await self.db.commit()
 
+        if approve:
+            try:
+                await invoice_service.create_invoice(  # type: ignore
+                    entity_id=tenant_id,
+                    user_id=claim.claimant_user_id,  # type: ignore
+                    amount=final_amount,
+                    description=f"Insurance claim payout: {cast(Any, policy).name}",
+                    due_date=datetime.utcnow()
+                )
+            except Exception as e:
+                logger.error(f"Invoice creation failed for insurance claim payout {claim_id}: {e}")
+
         await self.event_bus.publish({
```

**نفس القاعدة الثابتة زي `tourism_sports`:** `finance.transfer()` تفضل جوه `begin_nested()` (آمنة، صفر `commit()` مباشر فيها)، `create_invoice()` بس بتتنقل بعد `commit()`، ملفوفة بـ`try/except` (نفس نمط `_register_affiliate_commission`). `logger` مستوردة بالفعل في الملفين (مستخدمة في `_register_affiliate_commission`/رسائل AI موجودة سلفًا).

**صفر `Edit` فعلي حتى الآن — بانتظار موافقتك الصريحة.**

---

## 15) ✅ التطبيق [2026-08-18] + التحقق الحي — `realestate`/`insurance`

**موافقة صريحة مستلَمة على الديف الأربعة. تم التطبيق بالحرف على `realestate/service.py` و`insurance/service.py`.** `git diff`/`git status` خام عُرضا وأُكِّد تطابقهما مع الديف المعتمَد (نفس ضوضاء `constructor-mismatch` المسبقة الموجودة في الملفين من قبل هذه الجلسة، مؤكَّدة في `git status` الأصلي).

### 15.1) 🔴 اكتشاف إضافي أثناء التحقق — `EventBus.publish()` مفقودة (باج تالت مسبق)

`insurance.subscribe` بعد الإصلاح: `commit()` نجح، `create_invoice()` اتحاول (نجحت/فشلت حسب السيناريو)، ثم `self.event_bus.publish(...)` كراشت بـ`AttributeError: 'RedisClientWrapper' object has no attribute 'publish'`. **مؤكَّد مسبق، غير متأثر بديف #11b** (السطر بعد كل تعديلاتنا). وُثِّق كبند Backlog جديد (`eventbus-redis-wrapper-missing-publish`). **الأثر الجانبي المهم:** بيمنع `audit_log`/`_store_idempotency()` من التنفيذ في `insurance.subscribe` تحديدًا (بيحصل بعدهم في نفس التسلسل) — **لا يؤثر على صحة التزام `commit()` ولا على `create_invoice()` نفسها**، لأن الكراش يحصل بعدهم في التسلسل.

### 15.2) ✅ `realestate.rent_unit` — تحقق حي كامل ناجح (نظيف + فشل مُفتعَل × 2 تشغيلتين)

| | نظيف (contract 3, user 104) | فشل مُفتعَل (contract 4, user 105) |
|---|---|---|
| `rental_contracts` | ✅ موجود، `contract_tx_hash=RENT-0772CE8728FF` | ✅ موجود رغم فشل الفاتورة، `contract_tx_hash=RENT-3B69DF486B1A` |
| `invoices` | ✅ `id=13`, `First month rent for unit 3` | ✅ **صفر صف** — الفشل المُفتعَل منع الفاتورة بس |
| Redis idempotency | ✅ `{"contract_id": 3, ...}` | ✅ `{"contract_id": 4, ...}` — اتخزنت رغم فشل الفاتورة |
| نتيجة الدالة | `ok: True` | `ok: True` — صفر استثناء اتصعّد |

(تشغيلة أولى منفصلة أيضًا نجحت بنفس النمط: `contract_id=1,2`، `invoice id=12` للنظيف، صفر فاتورة للفشل المُفتعَل — نتيجتان متطابقتان عبر تشغيلتين مستقلتين.)

**لا يوجد `finance.transfer()` في `rent_unit` أصلًا** (مؤكَّد من قسم 5.4 السابق) — فمفيش تعارض مع باج `Transaction`/`tx_hash`، ومفيش `event_bus.publish` في الدالة (فمفيش تعارض مع باج 15.1 كمان). **تحقق حي كامل ونظيف 100%.**

### 15.3) ✅ `insurance.subscribe` — تحقق حي جزئي ناجح (الجزء المتعلق بـ#11b مؤكَّد بالكامل)

| | نظيف (subscription 4, user 106) | فشل مُفتعَل (subscription 5, user 107) |
|---|---|---|
| `insurance_subscriptions` | ✅ `id=4, status=ACTIVE` | ✅ `id=5, status=ACTIVE` رغم فشل الفاتورة |
| `wallets` (MR_USDT) | `980.0` (خُصم 20) | `980.0` — التحويل التزم |
| `transactions` | `COMPLETED` (106→109) | `COMPLETED` (107→109) |
| `invoices` | ✅ `id=14`, `Insurance premium: ...` | ✅ **صفر صف** — الفشل المُفتعَل منع الفاتورة بس |
| Redis idempotency | ❌ فاضي — `event_bus.publish` (15.1) كراشت قبل `_store_idempotency()` | ❌ فاضي، نفس السبب |
| نتيجة الدالة | `ok: False` (بسبب باج 15.1، بعد كل شيء متعلق بـ#11b) | `ok: False`، نفس السبب |

**الخلاصة:** الجزء اللي بيخص #11b تحديدًا (التزام `commit()` + سلوك `create_invoice()` الصحيح: ينجح في السيناريو النظيف، يفشل بأمان بلا كسر أي حاجة في السيناريو المُفتعَل) **مؤكَّد بالكامل بـSELECT مستقل، تمامًا زي `rent_unit`**. الفشل الكلي للدالة (`ok: False`) وغياب تخزين الـidempotency **سببهما باج 15.1 المنفصل تمامًا، مش #11b** — نفس منطق "باج لاحق في التسلسل بيمنع خطوات بعد نقطة نجاح #11b" المطبَّق على `book_program`/`place_transfer_bid`/`review_claim`، لكن هنا بمستوى أعمق (وصلنا فعليًا للتحقق من `commit()`+`create_invoice()` بنجاح، الباج التالي بس منع الباقي).

### 15.4) ملخص تغطية `realestate`/`insurance` (4 دوال)

| الدالة | مستوى التحقق | النتيجة |
|---|---|---|
| `realestate.rent_unit` | ✅ تحقق حي كامل (نظيف + فشل مُفتعَل + SELECT/Redis مستقل، تشغيلتان) | ✅ نجح بالكامل |
| `insurance.subscribe` | ✅ تحقق حي للجزء المتعلق بـ#11b (`commit`+`create_invoice`) عبر SELECT مستقل — 🟡 `_store_idempotency`/الاستجابة النهائية محجوبة ببج منفصل (15.1) | ✅ #11b مؤكَّد، 🟡 باقي الدالة محجوب ببج تالت |
| `realestate.buy_fractional_ownership` | 🟡 مراجعة ديف/كود بس — محجوبة ببج `tx_hash`/`Transaction` مسبق | ديف صحيح بالقراءة، بلا تحقق حي |
| `insurance.review_claim` | 🟡 مراجعة ديف/كود بس — محجوبة ببج `tx_hash`/`Transaction` مسبق (مسار `approve=True` تحديدًا، بما فيه claim.status→PAID/payout_tx_hash المطلوب تحقيقه) | ديف صحيح بالقراءة، بلا تحقق حي |

**الحالة: بانتظار توجيهك — ننتقل لـ`zamakana` (الدالة الأخيرة)، ولا نقفل الجلسة بهذا المستوى المختلط من التحقق عبر الدومينات الأربعة؟**

---

## 16) ✅ التطبيق [2026-08-18] + التحقق الحي — `zamakana.pledge_time` (الدالة الأخيرة)

**موافقة صريحة مستلَمة. الديف طُبِّق بالحرف** (`git diff` خام أُكِّد: نقل استدعاء `create_invoice()` من جوه `begin_nested()` — بعد `repo.create_pledge`، قبل `audit_log` — إلى بعد `await self.db.commit()`، محافظًا على شرط `if pledge.pledged_hours > 10:`، ملفوف بـ`try/except`. باقي الديف ضوضاء `constructor-mismatch` مسبقة غير مرتبطة، مؤكَّدة من `git status` الأصلي).

**تحقق حي كامل، بلا أي عائق — صفر باج جديد اتكشف:**

| | نظيف (`pledge_id=1`, user 111) | فشل مُفتعَل (`pledge_id=2`, user 112) |
|---|---|---|
| `time_pledges` | ✅ موجود، `pledged_hours=15.00` | ✅ موجود رغم فشل الفاتورة |
| `invoices` | ✅ `id=15`, `Time pledge registration for campaign ...` | ✅ **صفر صف** |
| Redis idempotency | ✅ `{"pledge_id": 1}` | ✅ `{"pledge_id": 2}` |
| نتيجة الدالة | `ok: True` | `ok: True` |

**`zamakana` لا يوجد فيها `finance.transfer()` ولا `event_bus.publish()`** — أنظف تحقق حي في الجلسة كلها، مطابق تمامًا لـ`purchase_event_ticket`/`rent_unit`.

---

## 17) ✅ ختم الإغلاق الرسمي النهائي [2026-08-18] — Backlog #11b

### 17.1) جدول مستوى التحقق الكامل — الثمانية دوال (بلا عبارات عامة)

| # | الدالة | الديف مطبَّق؟ | مستوى التحقق | النتيجة |
|---|---|---|---|---|
| 1 | `tourism_sports.purchase_event_ticket` | ✅ | ✅ **تحقق حي كامل** (نظيف + فشل مُفتعَل + SELECT/Redis مستقل) | ✅ نجح بالكامل |
| 2 | `tourism_sports.book_program` | ✅ | 🟡 **مراجعة ديف/كود فقط** — محجوبة ببج مسبق (`finance-transfer-returns-transaction-object`) | ديف صحيح بالقراءة، بلا تحقق حي |
| 3 | `tourism_sports.place_transfer_bid` | ✅ | 🟡 **مراجعة ديف/كود فقط** — محجوبة ببج مسبق (`tourism-place-transfer-bid-player-id-user-id-conflict`) | ديف صحيح بالقراءة، بلا تحقق حي |
| 4 | `realestate.rent_unit` | ✅ | ✅ **تحقق حي كامل** (نظيف + فشل مُفتعَل، تشغيلتان مستقلتان + SELECT/Redis مستقل) | ✅ نجح بالكامل |
| 5 | `realestate.buy_fractional_ownership` | ✅ | 🟡 **مراجعة ديف/كود فقط** — محجوبة ببج مسبق (`finance-transfer-returns-transaction-object`) | ديف صحيح بالقراءة، بلا تحقق حي |
| 6 | `insurance.subscribe` | ✅ | ✅🟡 **تحقق حي للجزء الخاص بـ#11b فقط** (`commit`+`create_invoice` مؤكَّدان بـSELECT مستقل) — باقي الدالة (`_store_idempotency`) محجوب ببج مسبق (`eventbus-redis-wrapper-missing-publish`) | #11b مؤكَّد، الباقي محجوب ببج تالت |
| 7 | `insurance.review_claim` | ✅ | 🟡 **مراجعة ديف/كود فقط** — محجوبة ببج مسبق (`finance-transfer-returns-transaction-object`)، تحديدًا مسار `approve=True` (`claim.status→PAID`/`payout_tx_hash`) | ديف صحيح بالقراءة، بلا تحقق حي |
| 8 | `zamakana.pledge_time` | ✅ | ✅ **تحقق حي كامل** (نظيف + فشل مُفتعَل + SELECT/Redis مستقل) | ✅ نجح بالكامل |

**الخلاصة الرقمية:** 4 دوال (1, 4, 8، وجزء من 6) حصلت على تحقق حي مباشر مؤكَّد بـSELECT/Redis مستقل. 4 دوال (2, 3, 5, 7) حصلت على مراجعة ديف/كود فقط — **السبب في كل الأربعة واحد: بجات مسبقة موثَّقة منفصلة تمامًا عن #11b، لا علاقة لها بديف #11b نفسه**، والديف المطبَّق عليها تم التأكد من صحته بالقراءة المباشرة (نفس نمط النقل، نفس البنية، نفس `try/except`) وبتأكيد منطقي إن نقطة النقل بمعزل تام عن نقطة الكراش في كل حالة.

### 17.2) الاكتشافات الجانبية الثلاثة — موثَّقة بالكامل كبنود Backlog منفصلة في `PROGRESS_LOG.md`

| # | البند | الملخص |
|---|---|---|
| 1 | `tourism-place-transfer-bid-player-id-user-id-conflict` | `place_transfer_bid` بتستخدم نفس القيمة كـ`user_id` (`get_player_profile`) وكـ`PlayerProfile.id` (`create_transfer` FK) — `IntegrityError` مؤكَّد حيًا، مسبق تمامًا. |
| 2 | `finance-transfer-returns-transaction-object-not-tx-hash-string` | `FinanceService.transfer()` بترجع كائن `Transaction` كامل مش نص `tx_hash` — بيكسر `book_program`/`buy_fractional_ownership`/`review_claim` (أعمدة `String` بتستقبل الكائن مباشرة) — مؤكَّد حيًا لـ`book_program`، مؤكَّد بالقراءة للباقي. |
| 3 | `eventbus-redis-wrapper-missing-publish` | `EventBus.publish()` بتنادي method غير موجودة على `RedisClientWrapper` — مؤكَّد حيًا في `insurance.subscribe` بعد `commit()`+`create_invoice()` الناجحين. |

**كل الثلاثة مؤكَّدين إنهم مسبقين بالكامل، غير متأثرين بديف #11b، وموثَّقين بأولوية عادية-مرتفعة برّه نطاق هذا البند.**

### 17.3) الملخص التنفيذي النهائي

**السبب الجذري (كان):** `InvoicingRepository.create_invoice()` (`invoicing/repository.py:22-31`) بتعمل `commit()` مباشر — بيقفل الـSAVEPOINT بتاع `begin_nested()` في أي دالة بتستدعيها من جواه. اكتُشف حيًا في `realestate`/`insurance` (4 دوال، محميين بكراش #9)، ثم اتسع النطاق أثناء الجرد الشامل ليشمل `tourism_sports` (3 دوال) و`zamakana` (دالة واحدة، الأربعة محميين بكراش #12) — **8 دوال إجمالًا عبر 4 دومينات**.

**الحل المُطبَّق (نفس النمط في كل الثمانية دوال، صفر لمس على `InvoicingRepository.create_invoice()` نفسها):** نقل استدعاء `create_invoice()` من جوه `begin_nested()` إلى **مباشرة بعد `await self.db.commit()`**، ملفوف بـ`try/except Exception` (يسجل اللوج، يكمل عادي لـ`_store_idempotency()`/`return`). `finance.transfer()` (حيث موجودة) تفضل جوه `begin_nested()` — مثبَّت أنها آمنة (savepoint داخلية خاصة بيها، صفر `commit()` مباشر).

**لماذا "بعد الإغلاق" مش "قبل الفتح" (بعكس نمط `invitations`/#11a):** `create_invoice()` هنا بتيجي بعد فحوصات/عمليات ممكن ترفض العملية بالكامل (تجاوز نسبة ملكية، رصيد غير كافٍ، إلخ) — نقلها لقبل فتح الـblock كان هيُنتج فواتير وهمية لعمليات مرفوضة. النقل لبعد الإغلاق يضمن: الفاتورة تتحاول فقط بعد تأكيد نجاح العملية الأساسية 100%.

**التحقق الحي:** 4 دوال (`purchase_event_ticket`, `rent_unit`, `zamakana.pledge_time`, وجزء من `insurance.subscribe`) — تحقق كامل/جزئي بـSELECT وRedis مستقلين، سيناريو نظيف + سيناريو فشل مُفتعَل لكل واحدة، بيانات throwaway جديدة تمامًا في كل الحالات. 4 دوال أخرى — مراجعة ديف/كود فقط بسبب 3 بجات مسبقة منفصلة تمامًا اتكشفت أثناء الجلسة ووُثِّقت كبنود Backlog مستقلة (لا تُعامَل كـ"محلولة" أو "مؤجَّلة ضمن #11b" — خارج نطاقه تمامًا).

**✅ تصحيح صياغة [2026-08-18]:** الجملة كانت مكتوبة سابقًا هنا "القيد على Backlog #9 اتشال جزئيًا" — **صياغة غير دقيقة، مصححة الآن.** لا يوجد سبب تقني للتشيل الجزئي: ديف #11b (نقل `create_invoice()` لبعد `commit()`) اتطبَّق بالتساوي على الثمانية دوال كلهم، بغض النظر عن عمق التحقق الحي لكل واحدة (تحقق كامل لـ4، مراجعة كود لـ4 بسبب بجات مسبقة منفصلة). سبب القيد الأصلي (حماية بالصدفة من باج #11b غير المُصلَح) **زال بالكامل من الثمانية دوال**. **القيد على Backlog #9 اتشال بالكامل** — #9 نفسها (كباج مستقل) لسه بتحتاج جلسة إصلاح منفصلة، لكن هذا وضعها الطبيعي كبند Backlog مفتوح عادي، مش قيد متبقٍ من #11b.

**تنظيف throwaway:** كل بيانات التحقق (يوزرات `p_tourism_verify_*`, `p_reins_verify_*`, `p_zamakana_verify_*` وما يتبعها من برامج/فعاليات/أندية/سياسات/حملات/فواتير) تُترك كما هي — تنظيف روتيني غير عاجل، مش جزء من هذا الإغلاق.

**الحالة: 🟢 مُغلَق — Backlog #11b (8 دوال، 4 دومينات).**
