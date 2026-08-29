# جلسة #29 — finance-service-hold-funds-missing

**التاريخ:** 2026-08-29
**النطاق المطلوب:** تحقيق + تصميم فقط. صفر تنفيذ كود حتى موافقة صريحة.

---

## 1. قراءة حية لموقعي الاستدعاء في `tenders_auctions/service.py`

### 1-أ) `place_bid` — حجز أموال المزايدة (السطور 344-355)

```python
# السطر 344-355
finance = FinanceService(self.db, tenant_id)
try:
    await finance.hold_funds(  # type: ignore[attr-defined]
        user_id,
        bid_amount,
        "MR_USDT",
        f"Auction {auction_id} bid",
        idempotency_key=idempotency_key
    )
except InsufficientBalanceError:
    raise PermissionDeniedError("Insufficient balance to place this bid")
```

**التوقيع المطلوب (استنتاجًا من الاستدعاء):**
`hold_funds(user_id: int, amount: Decimal, currency: str, description: str, idempotency_key: Optional[str] = None)`
يجب أن يرفع `InsufficientBalanceError` عند عدم كفاية الرصيد (مُستورد فعلًا في `tenders_auctions/service.py:24` ومُمسوك هناك).

القيمة المُرجعة **غير مُستخدَمة** في الكولر (لا يوجد `hold = await finance.hold_funds(...)`).

### 1-ب) `close_auction` — تحرير الحجز + التحويل الفعلي (السطور 401-419)

```python
# السطر 397-419
live_bids = await self.repo.get_live_bids_for_auction(auction_id, limit=1)
highest_bid = live_bids[0] if live_bids else None
...
if has_winner and highest_bid:
    bidder_id = cast(int, highest_bid.bidder_id)
    bid_amount = cast(Decimal, highest_bid.bid_amount_mrusdt)

    finance = FinanceService(self.db, tenant_id)
    await finance.release_held_funds(  # type: ignore[attr-defined]
        bidder_id,
        bid_amount,
        "MR_USDT",
        f"Auction {auction_id} winner payment"
    )
    await finance.transfer(
        sender_id=bidder_id,
        receiver_email="system@eppne.com",
        currency="MR_USDT",
        amount=bid_amount,
        notes=f"Auction {auction.title} sale",
        idempotency_key=f"AUCTION-SALE-{auction_id}-{uuid.uuid4().hex[:8]}"
    )
```

**التوقيع المطلوب:**
`release_held_funds(user_id: int, amount: Decimal, currency: str, description: str)` — **بدون `idempotency_key` إطلاقًا في هذا الاستدعاء.**

**المنطق المقصود:** حرّر حجز الفائز، بعدين حوّل المبلغ فعليًا من محفظته لحساب النظام (`system@eppne.com`)، بعدين افتح فاتورة.

---

## 2. اكتشافات إضافية حية — مشاكل في الكولر نفسه، منفصلة عن غياب الدالتين

هذه لم تكن مطلوبة صراحة في بند التحقيق، لكنها ظهرت أثناء القراءة الحية المباشرة لنفس الأسطر، وهي **حرجة لأي تصميم صحيح** لأن تصميم hold/release مبني على افتراض إن الكولر بيستخدمهم بشكل متسق ماليًا — وده مش صحيح حاليًا:

| # | الموقع | المشكلة | الأثر |
|---|---|---|---|
| A | `repository.py:154-159` `get_live_bids_for_auction` | الترتيب `ORDER BY created_at DESC` — **مش `bid_amount_mrusdt DESC`** | "أعلى مزايدة" الفعلية في `place_bid:320-321` و"الفائز" في `close_auction:397-398` هو في الحقيقة **آخر مزايدة زمنيًا، مش الأعلى قيمة**. ممكن يفوز بمزاد حد بمزايدة أقل لو كان آخر واحد بدأ يزايد. |
| B | `close_auction:397-419` | بياخد أعلى (آخر) `live_bid` واحد بس (`limit=1`) ويسوّي `release` عليه، ولا يلمس أي `live_bid` تاني لنفس المزاد | **كل المزايدات الخاسرة (وكل المزايدات السابقة للفائز نفسه لو رفع عرضه أكتر من مرة) تفضل محجوزة للأبد** — تسريب حجز دائم، بدون أي طريق لتحريرها لاحقًا في الكود الحالي. |
| C | `close_auction:418` | `idempotency_key=f"AUCTION-SALE-{auction_id}-{uuid.uuid4().hex[:8]}"` — **`uuid4()` عشوائي في كل استدعاء** | يُبطل تمامًا آلية منع التكرار في `transfer()` (`tx_repo.get_by_idempotency_key`, `finance/service.py:72-75`) — أي إعادة محاولة لـ`close_auction` (تعليق شبكة، retry، إلخ) هتنشئ `idempotency_key` جديد فتفشل الحماية من **تحويل مزدوج فعلي** لنفس المزاد. |
| D | `close_auction:406-411` | استدعاء `release_held_funds` بدون `idempotency_key` — على عكس كل استدعاء تاني لـ`FinanceService` في نفس الملف (`hold_funds`, `transfer`) | لو الدالة اتصممت لتتطلب idempotency (بما يماثل باقي `FinanceService`)، الاستدعاء الحالي هيفشل. لو اتصممت من غيرها، مفيش حماية من تكرار التحرير. |

**النتيجة العملية:** حتى لو صممنا `hold_funds`/`release_held_funds` بشكل مثالي على مستوى `FinanceService` وحدها، **تسريب الحجز (B) وخطر التحويل المزدوج (C) هيفضلوا موجودين** لأنهم في كود الكولر نفسه (`tenders_auctions/service.py`)، مش في `FinanceService`. هذا قرار نطاق لازم يتحسم معاك (قسم 5).

---

## 3. البنية التحتية الحالية في `FinanceService` — قابلة لإعادة الاستخدام

من `finance/models.py` و`finance/service.py` و`finance/repository.py`:

- **`Wallet.balances`**: عمود `JSONB` واحد لكل العملات (`MR_POUND`, `MR_USDT`, `MR7`, `NBT`, `MRX`)، مع `CheckConstraint` يمنع أي قيمة سالبة على مستوى الـDB. **لا يوجد أي عمود "محجوز" حاليًا** — كل رصيد في `balances` يُعتبر متاح بالكامل.
- **`Wallet.is_frozen`**: تجميد كامل للمحفظة (يمنع كل عملية) — مفهوم مختلف تمامًا عن "حجز جزء من الرصيد"، لا يُستخدم كأساس للحل.
- **`get_or_create_wallet_for_update`** (`service.py:34-39`): يعمل `SELECT ... FOR UPDATE` — قفل صف حقيقي، مُستخدم فعليًا في `transfer`/`swap`/`mint_currency` داخل `async with self.db.begin_nested()`. **هذا هو النمط الصحيح الموجود بالفعل ويجب أن يُعاد استخدامه حرفيًا لـ`hold_funds`/`release_held_funds`** لمنع أي race condition.
- **`Transaction`**: جدول عام لكل الحركات، بحقل `tx_type` (حاليًا: `TRANSFER`, `SWAP_OUT`, `SWAP_IN`, `MINT`) و`status` (`PENDING`/`COMPLETED`) و`idempotency_key` **UNIQUE** (مع فهرس جزئي `WHERE idempotency_key IS NOT NULL`، `models.py:52`) — هذا هو أساس الحماية من التكرار في كل الدوال الحالية، ويجب استخدامه بنفس الطريقة لـ`HOLD`/`RELEASE`.
- **لا يوجد أي عمود أو جدول جزئي جاهز لتمثيل "محجوز" (`held`/`pending`/`escrow`)** — التصميم يحتاج إضافة حقيقية، مش مجرد توصيل بنية موجودة.

---

## 4. بحث حي شامل — هل `hold_funds`/`release_held_funds` (أو نمط مشابه) مستخدمة في دومينات تانية؟

```
grep -rn "hold_funds|release_held_funds" (كل المشروع)
```

**النتيجة: الاستخدام الوحيد في كل الكود الفعلي هو الموقعان في `tenders_auctions/service.py:347` و`:406`.** كل باقي النتائج (~15 سطر) هي تقارير/سجلات جلسات سابقة (`.claude/reports/*.md`) توثّق نفس البند، مش استخدام كود حي في دومين تاني.

بحث موسّع عن نمط حجز أموال مشابه بأسماء مختلفة (`escrow`, `deposit_hold`, `lock_funds`, `freeze_funds`, `reserve_funds`, case-insensitive):
النتائج كلها غير ذات صلة (مصفوفات migration قديمة، وحقل `deposit` في `tourism_sports/models.py`/`schemas.py` وهو **مبلغ عربون رقمي على الحجز نفسه** — مش آلية حجز/تحرير على المحفظة، لا علاقة له بمنطق `FinanceService`).

**الخلاصة: تحذير سياق #37 غير منطبق هنا — لا يوجد استخدام تاني للاسمين في أي دومين آخر، ولا يوجد نمط قائم لإعادة استخدامه. التصميم هيبقى من الصفر لكن على بنية `Transaction`/`Wallet` الموجودة.**

---

## 5. التصميم المقترح

### 5-أ) تعديل `Wallet` (migration جديدة)

إضافة عمود `held_balances` (`JSONB`, `default=dict`, `nullable=False`) بنفس شكل `balances` بالضبط (نفس العملات الخمسة، قيمة ابتدائية أصفار). لا حاجة لجدول منفصل — نفس نمط `balances` الحالي.

إضافة `CheckConstraint` مطابق لموجود على `balances` يمنع أي قيمة سالبة في `held_balances`.

### 5-ب) `hold_funds(user_id, amount, currency, description, idempotency_key=None)`

داخل `async with self.db.begin_nested()`:
1. `wallet = await self.get_or_create_wallet_for_update(user_id)` (نفس القفل المستخدم في `transfer`).
2. لو `idempotency_key` موجود ومتكرر فعلًا (`tx_repo.get_by_idempotency_key`) → إرجاع نفس المعاملة القديمة (نفس نمط `transfer`/`swap`/`mint`)، **بدون تكرار الحجز**.
3. تحقق `is_frozen`.
4. `current = balances.get(currency, 0)`؛ لو `current < amount` → `raise InsufficientBalanceError` (مطابق تمامًا لما يتوقعه `place_bid:354`).
5. `balances[currency] -= amount`، `held_balances[currency] += amount`، `update_balances` لكل عمود.
6. إنشاء `Transaction(tx_type="HOLD", status="HELD", sender_id=user_id, from_wallet_id=wallet.id, amount=amount, currency=currency, idempotency_key=idempotency_key, notes=description)`.
7. إرجاع الـ`Transaction` (الكولر الحالي مايستخدمهاش، لكن مستقبلًا `release_held_funds` هيحتاج مرجع للـhold المحدد).

### 5-ج) `release_held_funds(user_id, amount, currency, description, idempotency_key=None)`

نفس نمط القفل:
1. `wallet = await self.get_or_create_wallet_for_update(user_id)`.
2. لو `idempotency_key` موجود ومتكرر → إرجاع القديمة.
3. تحقق `held_balances.get(currency, 0) >= amount` — لو أقل → `raise ValidationError("لا يوجد مبلغ محجوز كافٍ للتحرير")` (حماية من تحرير أكتر من المحجوز فعليًا، سواء بسبب باج في الكولر أو تكرار استدعاء).
4. `held_balances[currency] -= amount`، `balances[currency] += amount`.
5. إنشاء `Transaction(tx_type="RELEASE", status="COMPLETED", ...)`.

**ملاحظة حرجة:** بما إن `close_auction:406-411` **لا يمرر `idempotency_key`** حاليًا لـ`release_held_funds` (اكتشاف #D أعلاه)، فأي إعادة محاولة لـ`close_auction` هتحرر نفس الحجز مرتين لو ماكانش فيه حماية إضافية. الخطوة 3 أعلاه (التحقق من `held_balances >= amount`) بتمنع الرصيد من الانتفاخ (لأنه هيفشل في المرة التانية لو الحجز خلص)، لكن ده مش idempotency حقيقي — هيرجع خطأ بدل ما يرجع نفس النتيجة القديمة بأمان. **الحل الفعلي محتاج تمرير `idempotency_key` من الكولر، وهو تعديل في `tenders_auctions/service.py` (قسم 6).**

### 5-د) نافذة الخطر بين `release_held_funds` ثم `transfer` (close_auction:406-419)

الكولر الحالي بيسوّي خطوتين منفصلتين تمامًا (كل واحدة `begin_nested()` لوحدها):
1. تحرير الحجز → الرصيد يرجع "متاح" فعليًا في `balances`.
2. تحويل نفس المبلغ لحساب النظام.

بين الخطوتين، الرصيد **متاح تقنيًا** لأي عملية تانية (لو المستخدم طلب `transfer`/`swap` بالتوازي في نفس اللحظة) — نظريًا ممكن يستهلك الرصيد قبل ما يوصل تحويل المزاد، فيفشل تحويل المزاد بـ`InsufficientBalanceError` رغم إن الحجز كان مضمون لحظة الفوز. **هذا خطر تصميمي حقيقي، مش نظري بحت**، وبيتفادى فقط لو الكولر استخدم دالة واحدة ذرّية "حوّل من المحجوز مباشرة" بدل تحرير-ثم-تحويل.

**اقتراح بديل (اختياري، يتطلب تعديل الكولر):** دالة `settle_held_funds(user_id, receiver_email, amount, currency, description, idempotency_key)` تعمل الاثنين معًا داخل نفس `begin_nested()` واحد: تطرح من `held_balances` مباشرة وتضيف لمحفظة المستلم، بدون المرور بـ`balances` المتاح للمرسل إطلاقًا. هذا يقفل نافذة الخطر تمامًا، لكنه معمارياً استبدال لخطوتين موجودتين (`release_held_funds` + `transfer`) بدالة ثالثة جديدة — قرار تصميم يحتاج موافقتك صراحةً (قسم 6، خيار 2).

---

## 6. قرارات نطاق مطلوب حسمها معاك قبل أي تنفيذ

### قرار 1 — نطاق اللمس في `tenders_auctions/service.py`

| الخيار | الوصف | الأثر |
|---|---|---|
| **1-أ (أضيق نطاق)** | نصمم وننفذ `hold_funds`/`release_held_funds` فقط في `FinanceService`، بنفس التوقيع الحرفي الحالي المُستدعى، **صفر لمس لـ`tenders_auctions/service.py`** | يحل الانهيار (`AttributeError`) فورًا. لكن الاكتشافات A/B/C/D (قسم 2) تفضل موجودة: تسريب حجز دائم للخاسرين، فائز محتمل غلط (ترتيب زمني مش قيمة)، خطر تحويل مزدوج فعلي عند retry. |
| **1-ب (نطاق موسّع)** | زي 1-أ + تعديلات مستهدفة في `tenders_auctions/service.py`: (1) ترتيب `get_live_bids_for_auction` بالقيمة مش التاريخ، (2) `close_auction` يلف على *كل* المزايدات الحية للمزاد مش أول واحدة بس ويحرر حجز كل خاسر، (3) `idempotency_key` ثابت (مش `uuid4()` عشوائي) لاستدعاء `transfer`، (4) تمرير `idempotency_key` لـ`release_held_funds` | يقفل التسريب المالي الفعلي والخطر الحقيقي بالكامل. لكنه تعديل حقيقي في ملف موجود يتجاوز حدود "أضف الدالتين الناقصتين" — يحتاج مراجعة سلوكية إضافية (مثلاً: هل فعلاً كل خاسر لازم استرداد فوري، ولا فيه سيناريو تاني؟). |

### قرار 2 — شكل التسوية النهائية للفائز

| الخيار | الوصف |
|---|---|
| **2-أ** | الإبقاء على نمط الكولر الحالي: `release_held_funds` ثم `transfer` منفصلين (نافذة الخطر في §5-د تفضل موجودة نظريًا، لكن صفر تغيير معماري إضافي) |
| **2-ب** | إضافة دالة ثالثة `settle_held_funds` ذرّية تدمج التحرير+التحويل في خطوة واحدة، واستبدال الاستدعاءين في `close_auction:406-419` بيها |

---

## 7. جدول تصنيف المخاطر

| الخطر | الاحتمالية بدون إصلاح | الأثر | مصدره |
|---|---|---|---|
| **تسريب حجز دائم** (أموال الخاسرين تفضل مجمدة للأبد) | 🔴 مؤكد يحصل مع أي مزاد بأكتر من مزايد | مالي مباشر — رصيد "مقفول" وهمي لأي خاسر | اكتشاف B — في الكولر، خارج نطاق `FinanceService` وحدها |
| **تحديد فائز غلط** (آخر مزايد زمنيًا مش الأعلى قيمة) | 🔴 مؤكد لو المزايدات جت بترتيب مش تصاعدي زمنيًا | يفوز حد بسعر أقل، صاحب أعلى سعر يخسر ورصيده يتسرب (نفس اكتشاف B) | اكتشاف A — في `repository.py`, خارج نطاق `FinanceService` |
| **تحويل مزدوج فعلي عند retry** | 🟡 يحتاج ظرف retry فعلي (timeout/إعادة محاولة) — مش يومي لكن وارد في أي شبكة | مالي حرج — خصم مزدوج فعلي من محفظة الفائز | اكتشاف C — `idempotency_key` عشوائي في `close_auction:418` |
| **تحرير مزدوج للحجز** | 🟢 منخفض لو التصميم في §5-ج طُبّق (يفشل بدل ما يتكرر) لكن بدون idempotency حقيقي على `release_held_funds` نفسها | لو حصل، رصيد يزيد بدون مقابل حقيقي (تضخم وهمي) | اكتشاف D — غياب `idempotency_key` في استدعاء `release_held_funds` |
| **نافذة خطر release→transfer** | 🟡 يحتاج تزامن فعلي (عملية تانية لنفس المستخدم في نفس اللحظة) | فشل تحويل مزاد بعد ما كان مضمون (`InsufficientBalanceError`) — مش تسريب مالي مباشر لكن كسر منطقي | §5-د |
| **Migration جديدة (`held_balances`)** | — | لازم `alembic revision` + تأكد من توافقه مع `CheckConstraint` الحالي على `balances` وعدم كسر أي كود آخر يقرأ `Wallet.balances` مباشرة | تصميم §5-أ |

---

## الخلاصة والحالة

- تصميم `FinanceService.hold_funds`/`release_held_funds` (قسم 5) **جاهز للمراجعة**، مبني على البنية الموجودة فعليًا (`Wallet.balances` pattern + `Transaction` + `get_or_create_wallet_for_update` locking + idempotency عبر `idempotency_key` unique).
- تأكد بحثيًا: **لا استخدام تاني للاسمين في أي دومين، ولا نمط قائم يشابههم** — لا ينطبق هنا تحذير #37.
- **أربع مشاكل إضافية حقيقية (A/B/C/D) اتكشفت في الكولر نفسه أثناء القراءة الحية** — لازم قرار نطاق صريح (قسم 6) قبل أي تنفيذ، لأن تنفيذ الدالتين وحدهم (خيار 1-أ) هيوقف الانهيار لكن هيسيب تسريب مالي حقيقي وخطر تحويل مزدوج قائمين.
- **صفر تنفيذ كود حتى الآن.**

---

## 8. قرارات المستخدم المعتمدة (بعد عرض قسم 6)

- **قرار 1 → الخيار 1-ب (نطاق موسّع)، إلزامي:** تسريب الحجز الدائم (B) وباج
  تحديد الفائز (A) "مؤكَّدان يحصلان دايمًا" — مش اختياريين. التنفيذ المطلوب
  في `tenders_auctions/service.py` + `repository.py`:
  1. `get_live_bids_for_auction` يترتب بـ`bid_amount_mrusdt DESC` مش
     `created_at DESC`.
  2. `close_auction` يلف على **كل** المزايدات الحية للمزاد (مش أول واحدة
     بس) ويحرر حجز كل مزايدة غير فائزة (يشمل مزايدات سابقة للفائز نفسه لو
     رفع عرضه أكتر من مرة).
  3. `idempotency_key` ثابت مُشتق من `auction_id` (مش `uuid.uuid4()`
     عشوائي) في استدعاء `transfer`/`settle_held_funds`.
  4. تمرير `idempotency_key` لعملية التحرير (سواء `release_held_funds` أو
     ما يعادلها داخل `settle_held_funds`).

- **قرار 2 → الخيار 2-ب:** إضافة `settle_held_funds` ذرّية (تحرير + تحويل
  الفائز في `begin_nested()` واحد)، تستبدل الاستدعاءين المنفصلين الحاليين
  في `close_auction:406-419`. تقفل نافذة الخطر في §5-د تمامًا بدل ترقيعها.

- **تأكيد الحاجة لـ`release_held_funds` كدالة عامة منفصلة:** نعم، لسه
  لازمة — تُستخدم داخل اللوب الجديد في `close_auction` لتحرير حجز كل
  مزايدة غير فائزة (بالاعتماد على `LiveBid.bid_amount_mrusdt` المحفوظة
  فعليًا لكل صف، بدون حاجة لعمود/FK إضافي على `LiveBid` نفسه). فقط
  المزايدة الفائزة الوحيدة تمر عبر `settle_held_funds`. الثلاث دوال
  (`hold_funds`, `release_held_funds`, `settle_held_funds`) كلها مطلوبة.

- **ترتيب التنفيذ المعتمد من المستخدم:**
  1. Migration جديدة لـ`Wallet.held_balances` فقط (schema) — **تُعرض
     للمراجعة أولاً قبل أي منطق hold/release/settle.**
  2. بعد الموافقة على الـmigration → تنفيذ الدوال الثلاث في
     `FinanceService` + التعديلات الأربعة أعلاه في `tenders_auctions`.
  3. لكل تعديل: **تحقق حي حقيقي** (مسار فوز، مسار خسارة بأكتر من مزايد،
     محاولة retry فعلية على `close_auction` للتأكد من idempotency
     الفعلية) — مش `tsc`/imports فقط.

---

## 9. الخطوة الحالية المعلّقة — بانتظار قرارك

**تم إنشاء ملف migration جديد (ملف جديد، صفر تعديل على ملف قائم):**
`eppne-backend/migrations/versions/042_add_held_balances_to_wallets.py`
`down_revision = '041_widen_asset_tokenizations_token_symbol'` (تأكدت
إنها الـhead الحالية — لا يوجد ملف تاني بيشاور عليها كـ`down_revision`).

```python
def upgrade() -> None:
    op.add_column(
        'wallets',
        sa.Column(
            'held_balances', JSONB, nullable=False,
            server_default=sa.text(
                "'{\"MR_POUND\": 0, \"MR_USDT\": 0, \"MR7\": 0, \"NBT\": 0, \"MRX\": 0}'::jsonb"
            ),
        ),
    )
    op.create_check_constraint(
        "check_wallet_held_balances_non_negative", "wallets",
        "(held_balances->>'MR_POUND')::numeric >= 0 AND "
        "(held_balances->>'MR_USDT')::numeric >= 0 AND "
        "(held_balances->>'MR7')::numeric >= 0 AND "
        "(held_balances->>'NBT')::numeric >= 0 AND "
        "(held_balances->>'MRX')::numeric >= 0",
    )

def downgrade() -> None:
    op.drop_constraint('check_wallet_held_balances_non_negative', 'wallets', type_='check')
    op.drop_column('wallets', 'held_balances')
```

نفس شكل `balances` بالضبط (نفس الخمس عملات، `CheckConstraint` مطابق لمنع
القيم السالبة)، `server_default` صفري لكل المحافظ الموجودة فعليًا حاليًا في
القاعدة، بدون أي backfill إضافي لازم.

**ملاحظة جانبية (خارج نطاق مهمتنا، للعلم فقط):** فيه ملف
`migrations/versions/71820e4fe1f3_add_tenant_id_to_auth_refresh_tokens.py.py`
(امتداد `.py.py` مكرر) بمحتوى `revision = 'xxxx_add_tenant_id_to_auth_refresh_tokens'`
و`down_revision = '71820e4fe1f3'  # ⚠️ استبدل بالرقم الصحيح` — يبدو ملف
مسودة غير مكتمل، وبيلمس جدول `auth_refresh_tokens` اللي المفروض اتحذف في
Phase 4 (دمج auth→identity، راجع سياق `eppne-project` skill). لم يدخل في
حساب تحديد الـhead، ولم يُلمس. يستحق بند منفصل لاحقًا.

### السؤال المعلّق: تعديل `finance/models.py` (ملف قائم)

الـmigration وحدها مش كفاية — لازم عمود مطابق في نموذج `Wallet` نفسه
(`finance/models.py`) وإلا الـORM مش هيعرف بالعمود الجديد. هذا **تعديل
على ملف قائم**، محتاج موافقتك الصريحة قبل التطبيق (لسه معلّق فعليًا):

```python
# داخل class Wallet، بعد سطر balances (models.py:33)
held_balances = Column(JSONB, default=dict, nullable=False)

# وفي __table_args__، بعد check_wallet_balances_non_negative:
CheckConstraint(
    "(held_balances->>'MR_POUND')::numeric >= 0 AND "
    "(held_balances->>'MR_USDT')::numeric >= 0 AND "
    "(held_balances->>'MR7')::numeric >= 0 AND "
    "(held_balances->>'NBT')::numeric >= 0 AND "
    "(held_balances->>'MRX')::numeric >= 0",
    name="check_wallet_held_balances_non_negative"
),
```

**بانتظار: موافقة على تطبيق تعديل `models.py` ده، وبعدها الانتقال لمنطق
`hold_funds`/`release_held_funds`/`settle_held_funds` + التعديلات الأربعة
في `tenders_auctions`.**

---

## 10. التنفيذ الفعلي (بعد موافقتك)

- **`models.py`**: أُضيف `held_balances` + `check_wallet_held_balances_non_negative` كما عُرض بالضبط.
- **Migration `042`**: طُبِّقت فعليًا (`alembic upgrade head`) على DB التطوير الحي (`127.0.0.1:5435/eppne_v2`، DB نفسها المستخدمة في `throwaway-test-users.md`). تأكدت العمود والـconstraint موجودين فعليًا بعد التطبيق.
- **`finance/repository.py`**: أُضيفت `WalletRepository.update_wallet_funds()` (تحديث `balances`+`held_balances` في UPDATE واحد)، و`WalletRepository.create()` بقت بتزرع `held_balances` بنفس شكل `balances` (5 عملات، صفر).
- **`finance/service.py`**: أُضيفت 3 دوال كاملة (`hold_funds`, `release_held_funds`, `settle_held_funds`) بالتصميم المتفق عليه في §5+§8 — نفس نمط `begin_nested()`/`get_or_create_wallet_for_update`/idempotency عبر `idempotency_key` الموجود مسبقًا في `transfer`/`swap`/`mint_currency`.
- **`tenders_auctions/repository.py`**: `get_live_bids_for_auction` بقت `ORDER BY bid_amount_mrusdt DESC, created_at ASC` (بدل `created_at DESC`).
- **`tenders_auctions/service.py`**: `close_auction` بقت تجيب كل المزايدات الحية (`limit=100_000`)، تحرر حجز كل مزايدة غير فائزة في لوب (idempotency_key ثابت مُشتق من `auction_id`+`bid.id`)، وتسوّي الفائز عبر `settle_held_funds` واحدة (idempotency_key ثابت `AUCTION-SALE-{auction_id}` بدل `uuid4()` عشوائي). `place_bid` تُنادي `hold_funds` بنفس الشكل. أُزيلت كل `# type: ignore[attr-defined]` القديمة على الاستدعاءات الثلاث (الدوال بقت موجودة فعليًا).

## 11. التحقق الحي — النتائج

**بيئة الاختبار:** DB تطوير حقيقي (`eppne_v2`)، صفر mock. استُخدم مستخدمو throwaway الموثَّقين في `throwaway-test-users.md` (772 كمنشئ مزاد، 773/775 كخاسرين، 776 كفائز) تحت تينانت 1. اتزرعت صلاحية SaaS حية (`saas_service_plans`/`saas_tenant_service_access`/`saas_tenant_subscriptions`) لخدمتي `tenders`(74)/`auctions`(75) تحت تينانت 1 (لم تكن موجودة لأي تينانت أصلاً).

### ✅ TEST A — ترتيب `get_live_bids_for_auction` بالقيمة لا بالزمن (اكتشاف A)
أُدخلت 3 مزايدات مباشرة بقيم [100, 300, 200] مع `created_at` مضبوطة يدويًا بحيث القيمة الأعلى (300) هي **الأقدم** زمنيًا، والقيمة الأقل (200) هي **الأحدث**. النتيجة الفعلية من `get_live_bids_for_auction`:
```
amount=300.00  created_at=...16:563  (الأقدم)
amount=200.00  created_at=...46:520  (الأحدث)
amount=100.00  created_at=...26:251
```
**أول عنصر = 300 رغم كونه الأقدم زمنيًا — الفرز بالقيمة صحيح فعليًا (مؤكَّد حيًا، مش نظريًا).** لو الكود القديم كان لسه شغّال، كان هيرجع 200 (الأحدث) أول عنصر — هذا بالضبط الفرق اللي كنا بنصلحه.

### ✅ TEST B (جزء أول) — مسار الحجز الكامل عبر `place_bid` × 3
3 مزايدين حقيقيين عبر `TendersAuctionsService.place_bid` الفعلية (مش استدعاء مباشر لـFinanceService)، بمبالغ متصاعدة 100/150/220 MR_USDT:

| المستخدم | قبل | بعد `place_bid` | المتوقع | ✅/❌ |
|---|---|---|---|---|
| 773 (خاسر1، بيد 100) | balances=1000, held=0 | balances=900, held=100 | مطابق | ✅ |
| 775 (خاسر2، بيد 150) | balances=1000, held=0 | balances=850, held=150 | مطابق | ✅ |
| 776 (فائز، بيد 220) | balances=1000, held=0 | balances=780, held=220 | مطابق | ✅ |

### 🔴 عائق حي غير متوقع — باج منفصل تمامًا في دومين `invoicing` يوقف `close_auction`

عند تنفيذ `close_auction` الفعلي (بعد نجاح `release_held_funds`×2 + `settle_held_funds` بنجاح فعليًا)، فشلت الخطوة التالية مباشرة (`invoice_service.create_invoice`) بخطأ حقيقي من الـDB:

```
asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique
constraint "invoices_invoice_number_key"
DETAIL: Key (invoice_number)=(INV-1-000015) already exists.
```

**السبب الجذري (مؤكَّد حيًا):** `InvoicingService._generate_invoice_number`
(`invoicing/service.py:115-119`) بيولّد الرقم التالي بـ`COUNT(*) + 1`:
```python
count = await self.repo.count_invoices(tenant_id)
seq = str(count + 1).zfill(6)
```
لتينانت 1: `COUNT(*) = 14` لكن أعلى `invoice_number` موجود فعليًا هو
`000015` — يعني فيه **فجوة** (الرقم `000010` مفقود من التسلسل، غالبًا صف
اتحذف قديمًا في جلسة سابقة). طالما الفجوة موجودة، **أي استدعاء جديد
لـ`create_invoice` لتينانت 1 هيفضل يفشل بنفس الخطأ للأبد** — الدالة بتفترض
`COUNT == MAX`، وده مش مضمون إذا اتحذف أي صف قبل كده. **هذا باج منفصل
تمامًا في دومين `invoicing`، صفر علاقة بجلسة #29 أو بأي كود لمسناه.**

**الأثر على معاملات الاختبار المالية (مهم):** بما إن `close_auction` بتستخدم
نفس الـDB session طول الوقت، وبما إن `InvoicingRepository.create_invoice`
بتعمل `db.commit()` حقيقي (`invoicing/repository.py:29`)، فشل هذا الـcommit
(بسبب تكرار المفتاح) **رجّع بالكامل (rollback) كل حاجة كانت لسه غير
مُلتزَم بيها (uncommitted) من نفس الجلسة** — يعني `release_held_funds`×2 و
`settle_held_funds` اللي نفذوا بنجاح قبلها اتلغوا تلقائيًا مع فشل الـcommit.
**هذه خاصية أمان إيجابية غير مقصودة** (atomicity طبيعية من SQLAlchemy عند
فشل flush)، لكنها تعني إن التحقق الحي **لسه ناقص** — لم نصل لحظة تأكيد
نهائية إن التغييرات فعلاً استقرت (committed) على القرص بعد `close_auction`
كامل، ولا لاختبار الـretry idempotency، لأن التنفيذ توقف قبل الوصول للنهاية.

**محاولة إصلاح مؤقت لبيانات الاختبار فقط (بدون لمس كود):** حاولت إدخال صف
فاتورة placeholder واحد (`INV-1-000010`, status=`CANCELLED`, موسوم بوضوح
كـ"test-data housekeeping" في وصفه) لسد الفجوة الرقمية وفتح الطريق أمام
التحقق الحي، **لكن الأمر اتحجب من classifier صلاحيات الأتمتة** (INSERT
مباشر عبر SQL خام على الـDB) — رفض تلقائي مستقل عن أي قرار مني.

**القرار المطلوب منك لإكمال التحقق الحي:**

| الخيار | الوصف |
|---|---|
| **1 (الأسرع، موصى به)** | اسمح بإدخال صف واحد فقط (فاتورة وهمية `status=CANCELLED`، موسومة بوضوح "test-data housekeeping" في `notes`، تسد فجوة `INV-1-000010` المفقودة) عبر SQL خام، لإكمال التحقق الحي لـ`close_auction` وretry idempotency فورًا. صفر تعديل كود، صف بيانات اختبار واحد فقط. |
| **2** | إنشاء تينانت/مستخدمين جدد من الصفر بدون فواتير تراكمية — أكثر وقتًا وتعقيدًا (users/wallets/tenant جديدة + إعادة seed كل صلاحيات SaaS). |
| **3** | الاكتفاء بما تحقق حيًا حتى الآن (hold/release نجح 100%، ترتيب A نجح 100%)، وتوثيق باج `invoicing` كبند backlog منفصل، بدون إكمال اختبار `settle`/`retry` الحي فعليًا. |

**بانتظار ردك هنا في الملف لاختيار واحد من الثلاثة.**

---

## 12. تحديث — تم تجاوز عائق invoicing عبر monkeypatch (بنفس نمط rent_unit)

بناءً على توجيهك: استُخدم `monkeypatch.setattr(InvoicingService,
"_generate_invoice_number", _unique_invoice_number)` داخل اختبار pytest
حقيقي جديد (`tests/test_tenders_auctions_finance_hold_release_settle.py`)،
**نفس النمط بالضبط المستخدَم سابقًا في
`tests/test_realestate_rent_unit_ownership_check.py:100-112`** لنفس السبب
تمامًا (عزل بج `invoicing._generate_invoice_number` COUNT-based المنفصل
تمامًا، بدون أي لمس لـ`invoicing/service.py` الحقيقي). الاختبار الجديد
بيعمل fresh throwaway users (عبر `UserService.register`، مش المستخدمين
المُعاد استخدامهم في `throwaway-test-users.md`) + تنظيف كامل (`_cleanup`)
في `finally` — يحذف `Transaction`/`Invoice`/`AuditLog`/`LiveBid`/
`SovereignAuction`/`User` (الـ`Wallet` بيتحذف تلقائيًا عبر `ondelete=CASCADE`
مربوط بـ`User`)، ويرجّع رصيد حساب النظام (`system@eppne.com`, دائم غير
throwaway) لقيمته الأصلية بالضبط.

### ✅ نتائج التحقق الحي (بعد تجاوز invoicing)

**TEST 1 (`test_ordering_fix_uses_bid_amount_not_recency`): PASSED** —
نفس نتيجة TEST A سابقًا، مؤكَّدة الآن كـpytest رسمي دائم في الريبو.

**TEST 2 (`test_full_pipeline_win_lose_and_close_auction_retry`)**: تقدّم
حتى نهاية `close_auction` الأولى بنجاح كامل ومؤكَّد حيًا 100%:
- 3 مزايدين حقيقيين عبر `place_bid` الفعلية: أرصدة/حجوزات مطابقة تمامًا للمتوقع.
- `close_auction` الأولى: الفائز صح (`776`-إلخ بحسب التشغيلة، أعلى مزايدة)،
  `final_price=220` صح.
- الخاسرون استرجعوا حجزهم بالكامل (`balances`, `held_balances` صفر).
- الفائز فضل عند نفس الرصيد بعد الحجز (`780`) — **لم يرجع لـ1000 وسط
  الطريق أبدًا** — تأكيد مباشر إن `settle_held_funds` بتاخد من
  `held_balances` مباشرة بدون نافذة خطر (اكتشاف §5-د مقفول فعليًا).
- حساب النظام استلم `+220` بالضبط (تأكَّد بمقارنة قبل/بعد فعلية).
- **حرّرت `release_held_funds` حجز الخاسرين بنجاح تام (idempotency_key
  لكل bid.id، مطابق تمامًا للتصميم).**

**لكن الـretry نفسه (استدعاء `close_auction` ثانية على نفس المزاد) كشف
باج حقيقي منفصل تمامًا، جديد، غير موثَّق سابقًا:**

### 🔴 اكتشاف جديد حرج — `TransactionRepository.get_by_idempotency_key` بيكسر idempotency لأي معاملة بطرفين (sender+receiver)

**الموقع:** `finance/repository.py:97-109`:
```python
async def get_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> Optional[Transaction]:
    if not idempotency_key:
        return None
    result = await self.db.execute(
        select(Transaction)
        .join(User, or_(User.id == Transaction.sender_id, User.id == Transaction.receiver_id))
        .where(and_(Transaction.idempotency_key == idempotency_key, User.tenant_id == tenant_id))
    )
    return result.scalar_one_or_none()
```

**السبب الجذري (مؤكَّد حيًا بالتتبع الكامل):** الـ`JOIN` مع
`or_(User.id == sender_id, User.id == receiver_id)` — لو صف `Transaction`
الواحد عنده **كلاهما** `sender_id` و`receiver_id` غير فارغين (زي
`SETTLEMENT` من `settle_held_funds`، أو `TRANSFER` من `transfer()` نفسها!)،
الـJOIN بيتطابق **مرتين** لنفس صف الـTransaction (مرة عبر `sender_id`، ومرة
عبر `receiver_id`) — فيرجع صفين متطابقين لنفس المعاملة. `scalar_one_or_none()`
بيرفض أي أكتر من صف واحد → `sqlalchemy.exc.MultipleResultsFound`.

**الأثر:** أي retry حقيقي لعملية بطرفين (`transfer()` العادية، أو
`settle_held_funds()` الجديدة) بنفس `idempotency_key` **بيكسر بـ500 بدل
ما يرجع نفس المعاملة القديمة بأمان** — عكس الهدف الكامل من idempotency_key
تمامًا. **هذا باج pre-existing في `transfer()` كمان (نفس الدالة، نفس
الجدول)، لكنه كان كامنًا/غير مُلاحَظ لأن أي كولر سابق لـ`transfer()` من
تينانت واحد على الأرجح ما جربش retry حقيقي بنفس المفتاح في اختبار حي —
اكتشافنا الحالي فجّره لأول مرة لأن قرار #3 المعتمد (idempotency_key ثابت
مُشتق من auction_id بدل uuid4 عشوائي) هو أول استدعاء حقيقي بيعمل retry
فعلي بنفس المفتاح على معاملة ذات طرفين.**

**الإصلاح المقترح (الحد الأدنى، بدون تغيير سلوك أو معنى الدالة):**
```python
async def get_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> Optional[Transaction]:
    if not idempotency_key:
        return None
    result = await self.db.execute(
        select(Transaction).where(
            and_(
                Transaction.idempotency_key == idempotency_key,
                or_(
                    Transaction.sender_id.in_(select(User.id).where(User.tenant_id == tenant_id)),
                    Transaction.receiver_id.in_(select(User.id).where(User.tenant_id == tenant_id)),
                ),
            )
        )
    )
    return result.scalar_one_or_none()
```
بما إن `idempotency_key` عنده `UNIQUE` index جزئي فعليًا
(`ix_transactions_idempotency_key`, `models.py:52`)، أقصى حاجة ممكنة تتطابق
هي صف واحد بغض النظر عن الـJOIN — الاستعلام البديل (subquery بدل JOIN)
بيتحقق من نفس شرط "الطرف بينتمي للتينانت" بدون تكرار الصف. **صفر تغيير
في السلوك المقصود للدالة، إصلاح لباج تنفيذي بحت.**

**هذا يمنع فعليًا إكمال تحقق الـretry المطلوب لـ`settle_held_funds` —
محتاج قرارك: نصلح `get_by_idempotency_key` (خارج القائمة الأصلية للـ4
تعديلات، لكنه ضروري ليعمل التصميم المعتمد فعليًا)، ولا نوثّقه كـbacklog
منفصل ونعتبر التحقق الحي "جزئي" (كل حاجة عدا الـretry الفعلي مؤكَّدة)؟**

---

## 13. الإصلاح والتحقق النهائي — كل شيء PASSED حيًا

**الإصلاح المُطبَّق** (`finance/repository.py:97-116`، `TransactionRepository.get_by_idempotency_key`):
استبدال الـ`JOIN` بـ`subquery` للتحقق من انتماء الطرف للتينانت، بدون تكرار
الصف — راجع الكود الكامل في PROGRESS_LOG.md (بند
`finance-transaction-idempotency-key-lookup-multiple-results-bug`).

### تسلسل التحقق الحي الكامل (بالترتيب المطلوب)

1. **تحقق مستقل للإصلاح نفسه أولاً** — اختبار جديد منفصل تمامًا
   `test_transfer_idempotency_key_retry_returns_same_transaction`: استدعاء
   `FinanceService.transfer()` الحقيقية (بطرفين، sender+receiver) مرتين
   بنفس `idempotency_key` بالضبط. **PASSED** — `tx1.id == tx2.id`، صفر خصم
   مزدوج (`sender.balances.MR_USDT == 450` مش 400)، صفر استلام مزدوج
   (`receiver.balances.MR_USDT == 50` مش 100)، صف `transactions` واحد فقط
   لنفس `idempotency_key`.

   **ملاحظة جانبية أثناء كتابة هذا الاختبار:** أول محاولتين تجمّدتا (deadlock
   حقيقي، مؤكَّد عبر `pg_stat_activity`: جلسة `idle in transaction` ماسكة
   قفل على صفوف `wallets`، وجلسة تانية `_cleanup` منفصلة معلّقة على
   `Lock:transactionid` وهي بتحاول `DELETE FROM users` لنفس المستخدمين) —
   **باج في كود الاختبار نفسي، مش في الإنتاج**: نسيت `await db.commit()`
   بعد استدعاء `transfer()` (الراوتر الحقيقي `finance/router.py:57` بيعمل
   commit صريح بعد كل `transfer()`، اختباري ماكانش بيعمل كده، فالقفل فضل
   ممسوك). أُصلح بإضافة `db.commit()` صريح بعد كل استدعاء، مطابق لسلوك
   الراوتر الفعلي. صفر أثر على كود الإنتاج.

2. **إكمال الـretry الأصلي على `close_auction`** — `test_full_pipeline_win_lose_and_close_auction_retry`
   بالكامل: **PASSED**. مزاد حقيقي، 3 مزايدين، `close_auction` أولى ثم
   retry فعلي:
   - الفائز اتحدد صح (أعلى `bid_amount_mrusdt`)، `final_price=220` صح.
   - الخاسرون استرجعوا حجزهم بالكامل (`balances`+`held_balances` رجعوا لأصلهم).
   - الفائز فضل عند نفس الرصيد بعد الحجز (`780`) **طول الوقت** — قبل
     وبعد التسوية وبعد الـretry — لم يرجع لـ`1000` وسط الطريق أبدًا (تأكيد
     مباشر إن `settle_held_funds` بتاخد من `held_balances` مباشرة، §5-د مقفول).
   - حساب النظام استلم `+220` بالضبط مرة واحدة (`110 → 330`، وفضل `330`
     بعد الـretry — **صفر تحويل مزدوج فعليًا**).
   - `Transaction` count = 1 لكل من `AUCTION-SALE-{id}` و`AUCTION-RELEASE-{id}-{bid_id}`
     (لكل خاسر) قبل وبعد الـretry — **صفر تحرير حجز مزدوج فعليًا**.

3. **التوثيق** — أُضيف بند منفصل في `PROGRESS_LOG.md` بعنوان
   `finance-transaction-idempotency-key-lookup-multiple-results-bug`،
   موضَّح فيه بالنص إنه باج كان كامنًا في `transfer()` من قبل جلسة #29
   بكتير، واكتُشف فقط الآن بسبب أول retry حقيقي فعلي على معاملة بطرفين
   (نتيجة مباشرة لقرار #29 استخدام `idempotency_key` ثابت بدل `uuid4()`
   عشوائي). بند #29 نفسه أُضيف أيضًا كمُغلَق بالكامل ومتحقَّق حيًا.

### الحالة النهائية للـ3 اختبارات (ملف دائم في الريبو)

`tests/test_tenders_auctions_finance_hold_release_settle.py` — **3 passed, 96.02s**:
- `test_transfer_idempotency_key_retry_returns_same_transaction` — PASSED
- `test_ordering_fix_uses_bid_amount_not_recency` — PASSED
- `test_full_pipeline_win_lose_and_close_auction_retry` — PASSED

**تنظيف نهائي مؤكَّد حيًا:** صفر مستخدمي/مزادات/معاملات/فواتير throwaway
متبقية في DB (`SELECT ... WHERE email/title LIKE '%regtest%'` → صفر نتائج)،
رصيد حساب النظام (`system@eppne.com`, دائم) اترجع بالضبط لقيمته الأصلية
(`110.0 MR_USDT`) بعد كل تشغيلة.

**STATUS: كل شيء مقفول ومتحقَّق حيًا 100%. جاهز للـcommit.**
