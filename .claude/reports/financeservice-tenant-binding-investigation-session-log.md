# فحص read-only: FinanceService tenant binding

**النطاق:** فحص فقط، صفر تعديل كود. الهدف: تحديد حجم التأثير الحقيقي قبل أي تصميم لإصلاح ربط `tenant_id` في `FinanceService`.

---

## 1) `FinanceService.__init__` كامل

```python
# app/domains/finance/service.py:18-26
class FinanceService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = TransactionRepository(db)
        self.state_repo = SystemStateRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.event_bus = EventBus()
```

`tenant_id` بيتقفل جوّه الـinstance وقت الإنشاء، وكل الدوال بعد كده بتعتمد على `self.tenant_id` — مفيش أي دالة في الكلاس بتاخد `tenant_id` كباراميتر خاص بيها (ما عدا `SystemStateRepository.get_state()` اللي مش tenant-scoped أصلاً — حالة نظام عامة).

## 2) `transfer()` كاملة

```python
# app/domains/finance/service.py:58-147
async def transfer(
    self,
    sender_id: int,
    receiver_email: str,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    notes: Optional[str] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None
):
    if not idempotency_key:
        raise ValidationError("Idempotency key is required")

    existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
    if existing_tx:
        logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
        return existing_tx

    user_repo = UserRepository(self.db)
    receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
    if not receiver:
        raise NotFoundError("المستلم غير موجود")

    if receiver.tenant_id != self.tenant_id:
        raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

    state = await self.state_repo.get_state()
    crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))
    if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
        raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

    amount_decimal = Decimal(str(amount))

    async with self.db.begin_nested():
        first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
        first_wallet = await self.get_or_create_wallet_for_update(first_id)
        second_wallet = await self.get_or_create_wallet_for_update(second_id)

        sender_wallet = first_wallet if first_id == sender_id else second_wallet
        receiver_wallet = second_wallet if second_id == receiver.id else first_wallet

        if cast(bool, sender_wallet.is_frozen):
            raise PermissionDeniedError("محفظتك مجمدة. يرجى التواصل مع الدعم.")
        if cast(bool, receiver_wallet.is_frozen):
            raise PermissionDeniedError("محفظة المستلم مجمدة.")

        sender_balances = getattr(sender_wallet, "balances", {}).copy()
        sender_current = Decimal(str(sender_balances.get(currency, 0)))
        if sender_current < amount_decimal:
            raise InsufficientBalanceError(f"رصيد غير كافٍ من {currency}")

        sender_balances[currency] = float(sender_current - amount_decimal)
        receiver_balances = getattr(receiver_wallet, "balances", {}).copy()
        receiver_balances[currency] = float(Decimal(str(receiver_balances.get(currency, 0))) + amount_decimal)

        await self.wallet_repo.update_balances(cast(int, sender_wallet.id), sender_balances)
        await self.wallet_repo.update_balances(cast(int, receiver_wallet.id), receiver_balances)

        tx_hash = f"TX-{uuid.uuid4().hex[:12].upper()}"
        tx = await self.tx_repo.create(
            tx_hash=tx_hash, idempotency_key=idempotency_key,
            sender_id=sender_id, receiver_id=receiver.id,
            from_wallet_id=sender_wallet.id, to_wallet_id=receiver_wallet.id,
            amount=float(amount_decimal), currency=currency,
            tx_type="TRANSFER", status="COMPLETED", notes=notes,
        )

    await self._create_audit_log(
        user_id=sender_id, action="TRANSFER",
        details={"receiver_id": receiver.id, "receiver_email": receiver_email,
                  "currency": currency, "amount": float(amount_decimal), "tx_hash": tx_hash},
        ip=ip, ua=ua,
    )

    return tx
```

### كل نقاط استخدام `self.tenant_id` جوّه الكلاس (بالسطر)

| سطر | الدالة | الاستخدام |
|---|---|---|
| 21 | `__init__` | `self.tenant_id = tenant_id` (التقفيل الأولي) |
| 29 | `get_or_create_wallet` | `wallet_repo.get_by_user_id(user_id, self.tenant_id)` |
| 31 | `get_or_create_wallet` | `wallet_repo.create(user_id, self.tenant_id)` |
| 35 | `get_or_create_wallet_for_update` | `wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)` |
| 37 | `get_or_create_wallet_for_update` | `wallet_repo.create(user_id, self.tenant_id)` |
| 38 | `get_or_create_wallet_for_update` | `wallet_repo.get_by_user_id_for_update(...)` بعد الإنشاء |
| 44 | `_create_audit_log` | `tenant_id=self.tenant_id` في `audit_repo.create` |
| 72 | `transfer` | `tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| **78** | `transfer` | **`user_repo.get_by_email(receiver_email, self.tenant_id)`** ← نقطة الفشل الأولى |
| **82-83** | `transfer` | **`if receiver.tenant_id != self.tenant_id: raise PermissionDeniedError`** ← الحارس الصريح |
| 162 | `hold_funds` | `get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| 225 | `release_held_funds` | `get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| 289 | `settle_held_funds` | `get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| **295** | `settle_held_funds` | **`user_repo.get_by_email(receiver_email, self.tenant_id)`** ← نفس نقطة الفشل |
| **299-300** | `settle_held_funds` | **`if receiver.tenant_id != self.tenant_id: raise PermissionDeniedError`** |
| 377 | `swap` | `get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| 471 | `mint_currency` | `get_by_idempotency_key(idempotency_key, self.tenant_id)` |
| 540-541 | `get_transaction_history` | `tx_repo.get_by_user_paginated(tenant_id=self.tenant_id, ...)` |
| 551 | `get_transaction_history` | `tx_repo.count_by_user(tenant_id=self.tenant_id, ...)` |

`process_invoice_payment` (سطر 565) هي الدالة الوحيدة اللي **مبتلمسش** `self.tenant_id` إطلاقًا — بتنشر event بس.

**نقطة الفشل الحرجة الفعلية**: `transfer()` و`settle_held_funds()` بيبحثوا عن المستلم بـ`user_repo.get_by_email(receiver_email, self.tenant_id)`. `UserRepository.get_by_email` (`app/domains/identity/repository.py:52-55`) فيها فلتر صريح `User.tenant_id == tenant_id`. لو الـ`FinanceService` اتبنى بـ`tenant_id` غلط (زي سنتينل `0`)، أي بحث عن مستلم حقيقي بتينانت تاني بيرجع `None` → `NotFoundError("المستلم غير موجود")` — قبل ما توصل حتى لمرحلة التحقق من المحافظ أو المعاملة.

---

## 2) جرد شامل: كل نقاط إنشاء `FinanceService(...)` عبر المشروع

عدد نقاط الإنشاء داخل `app/` (بعيدًا عن الاختبارات والتقارير التوثيقية): **48 نقطة استدعاء**، موزّعة على **21 دومين + دومين `finance` نفسه (الراوتر) + مهمتين مباشرتين في `app/tasks/`**.

### النمط أ — تُبنى **مرة واحدة** في `__init__` وتُخزّن كـ `self.finance` (زي `SaaSControlService`)

هذا هو النمط الخطر: الـ`tenant_id` بيتقفل وقت إنشاء الـservice الخارجي نفسه، وبعدين أي دالة داخل نفس الـinstance بتستخدم `self.finance` المقفول ده — حتى لو الدالة استُدعيت لتينانت تاني.

| الدومين | الملف:السطر |
|---|---|
| `saas` | `saas/service.py:63` |
| `commerce` | `commerce/service.py:28` |
| `sovereign_entities` | `sovereign_entities/service.py:45` |
| `ai_agents` | `ai_agents/service.py:36` |
| `agritech` | `agritech/service.py:32` |
| `affiliate` | `affiliate/service.py:55` |
| `academy` | `academy/service.py:30` |
| `invoicing` | `invoicing/service.py:27` |

**8 دومينات** بنفس نمط `SaaSControlService`.

### النمط ب — تُبنى **من جديد داخل كل دالة على حدة** (per-operation)

`finance = FinanceService(self.db, tenant_id)` محلي داخل الدالة، بيتبني بـ`tenant_id` الفعلي بتاع العملية، مش بتينانت الـservice الخارجي المُخزَّن وقت الإنشاء.

| الدومين | عدد نقاط الإنشاء | ملاحظة |
|---|---|---|
| `transport` | 6 (354, 441, 542, 580, 727, 778) | |
| `insurance` | 4 (203, 290, 492, 608) | سطرين منها بـ`cast(int, policy.tenant_id)` / `pension.tenant_id` — تينانت الكيان نفسه، مش تينانت الطالب |
| `social` | 3 (513, 580, 666) | |
| `service_marketplace` | 3 (188, 361, 398) | مصمَّمة **عمدًا** لتينانت مختلف عن تينانت الخدمة الخارجية (`buyer_tenant_id`, `license_obj.tenant_id`) — سوق بين-تينانت بطبيعته |
| `tourism_sports` | 2 (175, 307) | |
| `tenders_auctions` | 2 (413, 476) | |
| `health` | 1 (224) | |
| `digital_twin` | 1 (175) | |
| `arbitration_syndicates` | 1 (335) | |
| `realestate` | 1 (289) | |
| `projects` | 1 (182) | |
| `iot` | 1 (211) | |
| `invitations` | 1 (656) | |
| `app/tasks/employment.py` | 1 (271) | مهمة مباشرة، مش عبر دومين service |
| `app/tasks/billing.py` | 1 (329) | مهمة مباشرة |

**13 دومين + مهمتين مباشرتين** بنمط per-operation آمن من هذه المشكلة تحديدًا.

### `finance/router.py` نفسه (8 نقاط)

كل endpoint بيبني `FinanceService(db, ...)` جديد لكل طلب HTTP — آمن بطبيعة دورة حياة FastAPI request-scoped، **إلا** سطر واحد شاذ:

```python
# finance/router.py:121
service = FinanceService(db, 1)   # ⚠️ tenant_id=1 مكتوب صريح، مش من current_user
```

باقي الـ7 نقاط (29, 45, 75, 102, 135, 146, 158, 182) بتستخدم `cast(int, current_user.tenant_id)` بشكل صحيح. السطر 121 ده خارج نطاق مشكلة "instance بتينانت ثابت عبر عدة عمليات" (كل request instance جديد وبيموت بعد الطلب) لكنه شبهة منفصلة (hardcoded tenant=1) تستاهل بند backlog مستقل — لم أفحص الـendpoint المحيط بعمق لأنه خارج نطاق هذا الفحص.

---

## 3) هل فيه دومين تاني (غير `saas`) بيعاني فعليًا من نفس المشكلة؟

**الإجابة: لأ. `saas` هي الحالة العملية الوحيدة المؤكدة حاليًا.**

فحصت الـ8 دومينات من النمط أ (اللي بتبني `self.finance` مرة واحدة في `__init__`) بحثًا عن أي مكان تاني بيُنشئ الـservice الخارجي بـtenant sentinel ثابت (زي `0`) ثم يلوب على تينانتات حقيقية مختلفة ويستخدم `self.finance`:

```
grep "Service(db,\s*0\)|Service(self\.db,\s*0\)"
```

النتيجة: **3 نقاط استخدام فقط لسنتينل `tenant_id=0`** في كل المشروع:

1. **`app/tasks/saas_tasks.py:69`** — `SaaSControlService(db, 0)` قبل `process_auto_renewals(tenant_id=None)`.
2. **`app/tasks/saas_tasks.py:297`** — `SaaSControlService(db, 0)` قبل `check_past_due_subscriptions(tenant_id=None)`.
3. **`app/domains/saas/router.py:273`** — `SaaSControlService(db, 0)` قبل `trigger_renewals(tenant_id)` (endpoint الأدمن اليدوي).
4. **`app/domains/academy/router.py:65`** — `AcademyService(db, 0)` قبل `create_tenant(...)`.
5. **`app/domains/sovereign_entities/router.py:260`** — `SovereignEntitiesService(db, 0)` قبل `get_public_entity_page(slug)`.

### لماذا `academy` و`sovereign_entities` **مش** حالات فعلية رغم استخدامهم نفس نمط `0`:

- **`academy/router.py:65`** → `create_tenant()` (`academy/service.py:56-70`) — بتنشئ التينانت نفسه وتستدعي `get_or_create_system_account(self.db, tenant.id)` **مباشرة كدالة مستقلة**، مش عبر `self.finance`. الدالة دي **لا تلمس `self.finance` إطلاقًا**. آمنة.
- **`sovereign_entities/router.py:260`** → `get_public_entity_page()` (`sovereign_entities/service.py:332-352`) — قراءة عامة لصفحة كيان، بتستخدم `self.repo` بس، **لا تلمس `self.finance` إطلاقًا**. آمنة من زاوية FinanceService (وإن كان فيها ملاحظة جانبية منفصلة: `self.repo.get_entity_page_by_slug_with_entity(slug, self.tenant_id=0)` قد يكون فيه فلتر تينانت خاطئ في حد ذاته — خارج نطاق هذا الفحص المخصص لـFinanceService).

### الحالة الوحيدة الفعلية: `saas` + `process_auto_renewals`

**التسلسل الفعلي للفشل (مؤكَّد بقراءة الكود، بدون تنفيذ):**

1. `saas_tasks.py:69` (أو `router.py:273` للتشغيل اليدوي) يبني `SaaSControlService(db, 0)` → `self.finance = FinanceService(db, 0)` مقفول على تينانت `0` (اللي مش تينانت حقيقي).
2. `process_auto_renewals(tenant_id=None)` (`saas/service.py:266`) بيستدعي `self.repo.get_subscriptions_for_renewal(None)` — ده بيرجع **اشتراكات كل التينانتات الحقيقية** بشكل صحيح (تم إصلاح هذا الجزء تحديدًا في جلسة سابقة اليوم — راجع التعليق في `saas/service.py:269-277`).
3. لكل اشتراك، بيتحدد `sub_tenant_id = sub.tenant_id` (التينانت الحقيقي)، وبيتجاب `system_account = get_or_create_system_account(self.db, sub_tenant_id)` — ده **بيرجع الحساب الصح** للتينانت الصح (دالة مستقلة مش متأثرة).
4. لكن الاستدعاء بعد كده `self.finance.transfer(sender_id=payer_id, receiver_email=system_account.email, ...)` بيدخل جوّه `transfer()` اللي بتعمل `user_repo.get_by_email(receiver_email, self.tenant_id)` — و**`self.tenant_id` هنا لسه `0`**، مش `sub_tenant_id`.
5. `User.tenant_id == 0` مبيرجعش أي صف حقيقي → `NotFoundError("المستلم غير موجود")` تتقفز.
6. الاستثناء ده **مش** `InsufficientBalanceError` (المُعالَج خصيصًا في `except InsufficientBalanceError` بسطر 319)، فبيقع في `except Exception` العام (سطر 329) → الاشتراك بيتسجل `{"status": "FAILED", "error": "المستلم غير موجود"}` بدون أي تغيير في حالته (يفضل زي ما هو، مش PAST_DUE ومش ACTIVE محدَّثة).

**النتيجة العملية:** التجديد التلقائي (`process_auto_renewals`) معطَّل فعليًا لـ**كل** الاشتراكات في **كل** التينانتات — مش حالة نادرة، دي 100% فشل لكل استدعاء عبر المسار ده (الـcelery task اليومي والـendpoint اليدوي `trigger-renewals` سواء). حتى لو الأدمن مرّر `tenant_id` محدد صريح في `trigger_renewals(tenant_id)` (`saas/service.py:617-620`)، الفلترة على مستوى الاشتراكات بتبقى صح (`target` بيتفلتر صح)، لكن `self.finance` يفضل مقفول على `0` بنفس الطريقة → نفس الفشل بالظبط، مفيش استثناء لأي تينانت حتى لو محدد بالاسم.

**خارج النطاق لكن مُلاحَظ أثناء الفحص (بدون تنفيذ، بدون تعميق):** فيه نمط باج مختلف تمامًا وغير متعلق بربط التينانت — استدعاءات constructor ناقصة الآرجيومنت `tenant_id` (بتطلع `TypeError` فورًا وقت الإنشاء، قبل أي منطق تينانت أصلاً):
- `app/tasks/commerce.py` (5 مواضع: 71, 122, 165, 214, 254) — `CommerceService(db)` بمعامل واحد بدل اتنين.
- `app/domains/invoicing/router.py:330` — `InvoicingService(db)` بمعامل واحد بدل اتنين.

دي نفس عائلة الباج الموثقة سابقًا في `constructor-mismatch-session-log.md` (`PROGRESS_LOG_ARCHIVE_2026-08-18.md:2768` وما حولها) — مش نفس مشكلة "instance بتينانت ثابت وصحيح لكن غلط" اللي إحنا بنحقق فيها هنا. مذكورة هنا فقط للأمانة لأنها ظهرت أثناء الـgrep الشامل.

---

## 4) تقييم الخيارين تقنيًا (بدون تنفيذ)

### الخيار أ) `FinanceService` تتبنى per-operation (تاخد `tenant_id` كباراميتر في كل دالة بدل الـconstructor)

**الشكل:** إزالة `tenant_id` من `__init__`، وإضافته كباراميتر أول (أو keyword) في كل دالة عامة: `transfer(self, tenant_id, sender_id, ...)`, `hold_funds(self, tenant_id, ...)`, إلخ — وتمرير `tenant_id` صراحة لكل استخدام داخلي بدل `self.tenant_id`.

**الأثر:**
- **يمس الـ48 نقطة استدعاء كلها** عبر الـ21 دومين + الراوتر + المهمتين — كل نقطة `FinanceService(db, tenant_id)` لازم تتغيّر لـ`FinanceService(db)` + تمرير `tenant_id` لكل استدعاء دالة بعد كده.
- الدومينات الـ8 من النمط أ (اللي عندها `self.finance` مُخزَّن) محتاجة تعديل إضافي: كل استدعاء لـ`self.finance.transfer(...)` داخلهم لازم يضيف `tenant_id=...` — ده بيحل مشكلة `saas` **جذريًا** (مفيش تينانت مقفول أصلاً، كل استدعاء بيمرر التينانت الصح بتاعه).
- **مخاطرة الحجم:** تغيير في توقيع دالة عامة (public API) لكلاس بيُستخدم في 21 دومين + الراوتر — أي دومين ينسى تمرير `tenant_id` صح (أو يمرر تينانت غلط بالخطأ) بيبقى باج صامت جديد، مش TypeError واضح (لأن لو الباراميتر وله default مش هيبين وقت الكتابة). الـ13 دومين من النمط ب أصلاً بيبنوا instance جديد بالتينانت الصح في كل مرة — نقلهم لـper-operation signature هو "no-op منطقيًا" بس تغيير ميكانيكي في كل نقطة استدعاء (نفس عدد التعديلات تقريبًا، بدون فايدة حقيقية عندهم لأنهم مش عندهم المشكلة أصلًا).
- **الفايدة:** يقفل الفئة كلها من الباجات المستقبلية — أي دومين جديد يستخدم `FinanceService` مستحيل يقع في نفس فخ "instance بتينانت ثابت"، لأن الـAPI نفسه بيجبرك تمرر التينانت في كل نداء.

### الخيار ب) `SaaSControlService` بس تبني `FinanceService` جديدة جوّه كل عملية (بدل `self.finance` الثابتة)

**الشكل:** حذف `self.finance = FinanceService(db, tenant_id)` من `__init__`، وبناء `finance = FinanceService(self.db, sub_tenant_id)` محليًا جوّه `process_auto_renewals` (وأي دالة تانية في `SaaSControlService` بتستخدم `self.finance` لتينانت مختلف عن `self.tenant_id`) — بالظبط نفس النمط المُستخدَم بالفعل في الـ13 دومين من النمط ب.

**الأثر:**
- **محصور في ملف واحد**: `saas/service.py` — حذف سطر `self.finance = ...` من `__init__` (63)، وإضافة `finance = FinanceService(self.db, sub_tenant_id)` محلي في `process_auto_renewals` (قبل استخدامها في سطر 291)، وفحص باقي دوال `SaaSControlService` (زي `cancel_subscription`, `create_subscription`, إلخ) اللي ممكن تستخدم `self.finance` بتينانت `self.tenant_id` الصحيح فعلاً (مش سيناريو cross-tenant) وترجعلها `self.finance` أو تبنيها محليًا بنفس القيمة.
- **مفيش أي مساس بالـ20 دومين التاني ولا بتوقيع `FinanceService` العام.**
- **الفايدة:** يحل الحالة العملية الوحيدة المؤكدة (`saas`) بأقل مساحة تغيير وأقل مخاطرة — لا TypeError محتمل، لا تعديل في استدعاءات خارجية.
- **العيب:** الفئة (class) نفسها ("instance بتينانت ثابت + احتمال استخدامها لعملية تينانت تاني") تفضل موجودة في تصميم `FinanceService` — لو دومين تاني مستقبلًا احتاج نفس نمط "أدمن بيلوب على تينانتات" (زي `SaaSControlService` بالظبط)، هيقع في نفس الفخ من غير أي حماية على مستوى الكلاس نفسه. الإصلاح هنا "محلي" مش "بنيوي".

### مقارنة سريعة

| | الخيار أ (per-operation API) | الخيار ب (fix محلي في `saas`) |
|---|---|---|
| مساحة التغيير | 48 نقطة استدعاء، 21+ دومين | ملف واحد (`saas/service.py`) |
| يحل `saas` فعليًا | ✅ | ✅ |
| يمنع تكرار نفس الباج في دومين جديد مستقبلًا | ✅ (بنيويًا) | ❌ (يعتمد على انتباه المطوّر) |
| مخاطرة regressions في الدومينات التانية | متوسطة-عالية (كل نقطة استدعاء لازم تتعدّل صح) | شبه معدومة (صفر مساس بدومينات تانية) |
| يتماشى مع النمط الموجود فعلاً في 13 دومين | لأ (بيغيّر النمط اللي شغال أصلاً بالنمط ب) | ✅ (نفس النمط بالظبط) |

---

**خلاصة الفحص:** `saas` (عبر `process_auto_renewals` وتحديدًا سيناريو `tenant_id=0` سنتينل الإداري) هي الحالة العملية الوحيدة المؤكدة حاليًا لمشكلة "instance بتينانت ثابت + عملية مالية لتينانت مختلف" في المشروع كله. لا يوجد تعديل كود تم في هذه الجلسة — فحص read-only بحت.
