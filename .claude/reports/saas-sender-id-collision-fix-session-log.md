# جلسة `saas-pay-invoice-sender-id-user-id-collision` — سجل الجلسة

- **التاريخ:** 2026-09-24
- **النوع:** تشخيص (§0-§12) ثم تنفيذ إصلاح تحقق عضوية الأدمن + اختبار دائم + mutation + regression (§13-§17). **لم يُكتب أي شيء في `PROGRESS_LOG.md`، ولا staging ولا commit.**
- **البند المصدر:** `PROGRESS_LOG.md:264` — `saas-pay-invoice-sender-id-user-id-collision` [2026-08-24]، 🔴 مفتوح.
- **قاعدة البيانات المفحوصة:** الحاوية `eppne_db` (المنفذ 5435، القاعدة `eppne_v2`، alembic head = `068_invoice_number_counters`). **لم تُلمَس** الحاوية الشاردة `postgres-eppne` (5433).
- **كل الاستعلامات الحية:** `SELECT` / `\d` فقط، ولم يُستدعَ أي كود من التطبيق.

---

## 0. الخلاصة التنفيذية

**البند مُصلَح فعليًا منذ 2026-08-25 (بعد يوم واحد من فتحه)، لكنه لم يُغلَق في `PROGRESS_LOG.md` أبدًا.** والبند الحاجب (`saas-invoices-idempotency-key-schema-drift`) مُصلَح في اليوم نفسه، **ولا يوجد له صف خاص به في `PROGRESS_LOG.md` أصلًا**، فهو مذكور فقط داخل نص الصف 264.

| البند | الحالة الحقيقية اليوم | الدليل |
|---|---|---|
| تصادم `sender_id=self.tenant_id` | ✅ **مُصلَح** — commit `0ba7204` (2026-08-25 08:03) | الكود الحالي `service.py:288-293` و`:698-704` يستخدم `payer_id` |
| انحراف `saas_invoices.idempotency_key` | ✅ **مُصلَح** — commit `8fccfa1` (2026-08-25 08:35)، migration `036` | `\d saas_invoices` الحي يُظهر العمود + فهرس unique جزئي |
| التحقق الحي end-to-end | ✅ **تم** (حسب رسالة `8fccfa1`)، **ومؤكَّد اليوم ضمنيًا** بـ164 تحويلًا حقيقيًا في القاعدة | القسم 3 |

**لذلك لا حاجة لإصلاح كود في هذه الجلسة لنفس الباج.** ما تبقّى: (أ) قرار توثيقي لإغلاق البندين، (ب) ثلاث ملاحظات متبقية على **التصميم المختار** (القسم 4)، أهمها التينانت 15 التي أدمنها ينتمي لتينانت أخرى.

---

## 1. الخطوة 1.1 — الكود الحالي

### 1.1 `_get_tenant_admin_id` — `eppne-backend/app/domains/saas/service.py:64-73`

```python
async def _get_tenant_admin_id(self, tenant_id: int) -> int:
    # الدافع الرسمي لفواتير/تجديدات التينانت هو AcademyTenant.admin_id
    # الإجباري الموجود بالفعل — راجع §7 بند 4 من مستند تصميم حساب
    # النظام الموحَّد لكل تينانت.
    from app.domains.academy.repository import AcademyRepository
    academy_repo = AcademyRepository(self.db)
    tenant = await academy_repo.get_tenant_by_id(tenant_id)
    if not tenant:
        raise NotFoundError("التينانت غير موجود")
    return cast(int, tenant.admin_id)
```

### 1.2 `process_auto_renewals` — `service.py:266` (موقع النداء `:288-297`)

```python
payer_id = await self._get_tenant_admin_id(sub_tenant_id)
system_account = await get_or_create_system_account(self.db, sub_tenant_id)
finance = FinanceService(self.db, sub_tenant_id)
async with self.db.begin_nested():
    tx = await finance.transfer(
        sender_id=payer_id,
        receiver_email=cast(str, system_account.email),
        ...
        idempotency_key=f"AUTO-RENEW-{sub.id}-{datetime.now(timezone.utc).strftime('%Y-%m')}",
```

### 1.3 `pay_invoice` — `service.py:693` (موقع النداء `:698-708`)

```python
payer_id = await self._get_tenant_admin_id(self.tenant_id)
system_account = await get_or_create_system_account(self.db, self.tenant_id)
finance = FinanceService(self.db, self.tenant_id)
async with self.db.begin_nested():
    try:
        tx = await finance.transfer(
            sender_id=payer_id,
            receiver_email=cast(str, system_account.email),
            ...
            idempotency_key=f"PAY-INV-{invoice.id}",
```

**النتيجة:** لم يعد أي من الموقعين يمرّر `tenant_id` في `sender_id`. الباج كما وُصف **غير موجود**. أصل التغيير هو `0ba7204` (`feat(finance): convert 9 tenant-system-account call sites (7 domains)`)، وهو يستبدل بالضبط:

```diff
-                        sender_id=target_tenant,
-                        receiver_email="system@eppne.com",
+                        sender_id=payer_id,
+                        receiver_email=cast(str, system_account.email),
```

(وتغيير مماثل في `pay_invoice`.) التعديلات اللاحقة على الملف (`99fb8aa`، `28a0ca4`، `7bd82d1`، `829b183`، وتعديل 2026-09-08 لـ`tenant_id=None` / `sub_tenant_id`) لم تُرجِع الباج، بل جعلت `process_auto_renewals` يستخدم `FinanceService(self.db, sub_tenant_id)` لكل اشتراك، وهذا صحيح. `git diff` الحالي لا يحتوي على أي تغيير غير مُلتزَم في `app/domains/saas/`.

---

## 2. الخطوة 1.2 — مخطط `saas_invoices` الحي

```
\d saas_invoices   (eppne_db / eppne_v2)
 ...
 idempotency_key | character varying(255) |  |  |
Indexes:
    "ix_saas_invoices_idempotency_key" UNIQUE, btree (idempotency_key) WHERE idempotency_key IS NOT NULL
```

- العمود موجود، وأضافته migration `036_add_idempotency_key_to_saas_invoices.py` (commit `8fccfa1`، 2026-08-25 08:35).
- `alembic_version` = `068_invoice_number_counters`، أي أن 036 مطبَّقة.
- المُعرَّف في الموديل: `saas/models.py:161` (`idempotency_key = Column(String(255), unique=True, nullable=True, index=True)`).
- **الانحراف غير موجود اليوم. الخطوة 1.3 قابلة للوصول، والخطوة 1.4 غير مطلوبة.**
- ملاحظة: `saas_invoices` فارغة حاليًا (0 صفوف)، فكل فواتير الاختبارات السابقة نُظِّفت.

---

## 3. الخطوة 1.3 — قابلية الوصول end-to-end + نمط `get_or_create_system_account`

### 3.1 نقاط الدخول

| المسار | الصلاحية | المصدر |
|---|---|---|
| `POST /saas/invoices/{invoice_id}/pay` ← `pay_invoice` | `require_admin_or_above` | `saas/router.py:194-203` |
| Celery `saas.process_auto_renewals` ← `process_auto_renewals(tenant_id=None)` | beat يومي | `tasks/saas_tasks.py:47-74` |

### 3.2 الدليل الحي على أن المسارين يعملان فعليًا (SELECT على `transactions`)

| النوع | sender_id | receiver_id | العدد | المجموع (MR_USDT) | الفترة |
|---|---|---|---|---|---|
| `AUTO-RENEW-*` | 1 | 957 | 107 | 107.0 | 2026-09-08 ← 2026-09-23 |
| `PAY-INV-*` | 1 | 957 | 57 | 66.0 | 2026-08-25 ← 2026-09-23 |

- `957` = `__system_tenant_1__` (حساب النظام للتينانت 1، `is_system_account=true`).
- `1` = `AcademyTenant(1).admin_id`.
- **صفر** تحويلات `PAY-INV`/`AUTO-RENEW` قبل 2026-08-25، وهذا متسق مع أن المسار كان مكسورًا بالانحراف قبلها.
- الرصيد متوازن تمامًا: محفظة user 1 (`wallets.id=39`) = 702.0، ومحفظة النظام (`id=929`) = 173.0، والمجموع 875.0، وهو الرقم الموثَّق في `PROGRESS_LOG.md:268` بتاريخ 2026-08-24. **كل الـ173 ذهبت من الأدمن إلى حساب النظام، وليس لأي مستخدم عشوائي.**
- مصدر هذه التحويلات: اختبارات regression (أسماء الخطط `REGTEST-FINBIND-*` و`REGTEST-TRIGREN-*`)، وهذا هو البند المعروف `test-financeservice-tenant-binding-leaks-user1-funds` (`PROGRESS_LOG.md:1059`). **لا علاقة له بهذه الجلسة.**

### 3.3 `get_or_create_system_account` — `eppne-backend/app/core/system_account_service.py`

- **التوقيع:** `async def get_or_create_system_account(db: AsyncSession, tenant_id: int) -> User`
- **السلوك:** يبحث عن `User` حيث `tenant_id == tenant_id AND is_system_account IS TRUE`، وإن لم يجده ينشئ واحدًا (`username=__system_tenant_{id}__`، `email=system+tenant-{id}@internal.eppne.local`، `is_active=False`، `system_role=SYSTEM`) بـ`flush()` فقط، بلا commit، لأنه آمن داخل savepoint.
- **مواقع النداء اليوم (9):** academy (`:73`، `:363`)، affiliate (`:573`)، iot (`:217`)، projects (`:183`)، saas (`:289`، `:699`)، social (`:588`، `:677`).
- **ملاحظة جانبية:** موقع commerce (`release_commissions`) لم يعد يظهر في الـgrep. على الأرجح انتقل إلى affiliate مع التوحيد في `28a0ca4`. لم أتحقق من ذلك بالتفصيل لأنه خارج النطاق، وأذكره فقط لأن الـprompt أشار إلى "commerce" كأحد الدومينات الثلاثة.
- **النمط في الدومينات الأخرى مقابل saas:** في affiliate وiot وcommerce سابقًا، حساب النظام هو **المُرسِل** (النظام يدفع للمستخدم). في saas الوضع **معكوس**: حساب النظام هو **المستقبِل** والتينانت هي التي تدفع. لذلك لا يكفي نمط `get_or_create_system_account` وحده، بل يلزم أيضًا مصدر للدافع، وهو ما حُلَّ بـ`_get_tenant_admin_id`.

---

## 4. الخطوة 2 — التشخيص والمراجعة المعمارية

### 4.1 هل الباج ما زال حيًا؟ هل ما زال محجوبًا؟

- **التصادم كما وُصف: لا، مُصلَح.** لم يعد `sender_id` مشتقًا من `tenant_id` في أي موقع في saas.
- **الحجب: لا.** الانحراف مُصلَح بـmigration 036 ومطبَّق حيًا.
- **الفجوة الحقيقية الوحيدة: فجوة توثيق.** الصف 264 ما زال "🔴 مفتوح"، و`saas-invoices-idempotency-key-schema-drift` لم يُسجَّل كصف ولم يُغلَق. هذا نفس نمط `project_uncommitted_pre_existing_changes_audit` (عمل مكتمل غير مسجَّل).

### 4.2 المراجعة المعمارية المطلوبة في البند الأصلي: من يجب أن يدفع؟

**القرار اتُّخذ فعليًا في جلسة `tenant-system-account-phase3-conversion`** (التقرير: `.claude/reports/tenant-system-account-phase3-conversion-session-log.md`، الصف 6 في الجدول و§4.1): **الدافع هو `AcademyTenant.admin_id`، والمستقبِل هو حساب النظام الخاص بالتينانت.** لكن هذا القرار لم يُعرَض عليك كمراجعة معمارية بهذه الصيغة، فأعرض البدائل الآن لتؤكده أو تغيّره:

| الخيار | الوصف | المزايا | العيوب |
|---|---|---|---|
| **A (الحالي)** | الدافع = `AcademyTenant.admin_id`، والمستقبِل = حساب نظام التينانت | حتمي؛ يعمل مع Celery (لا يوجد "مستخدم حالي" في المهمة المجدولة)؛ `admin_id` إجباري (NOT NULL + FK)؛ مُتحقَّق منه حيًا | يدفع من محفظة **شخص** بعينه وليس من خزانة التينانت؛ أي أدمن آخر (`require_admin_or_above`) يستطيع أن يخصم من محفظة `admin_id` لا من محفظته هو؛ لا يوجد تحقق أن `admin_id` ينتمي للتينانت نفسها (انظر 4.3-أ) |
| **B** | الدافع = المستخدم الذي نادى الـendpoint (`current_user.id`) | مساءلة واضحة (من ضغط يدفع) | **لا يعمل في `process_auto_renewals`** لعدم وجود مستخدم؛ يتطلب مسارين مختلفين للدافع؛ يغيّر عقد `pay_invoice(invoice_id)` |
| **C** | محفظة خزانة للتينانت نفسها (حساب نظام ثانٍ بدور "treasury/payer") | فصل تام بين أموال التينانت وأموال الأفراد؛ الأصح محاسبيًا | لا يوجد هذا المفهوم حاليًا (حساب نظام واحد لكل تينانت فقط)؛ يتطلب آلية لتمويل الخزانة؛ حساب النظام الحالي هو المستقبِل، فلا يصح أن يدفع لنفسه؛ عمل تصميمي كبير |
| **D** | الدافع = حساب النظام، والمستقبِل = حساب نظام منصة عالمي (tenant 0؟) | يعكس "التينانت تدفع للمنصة" بدقة | لا يوجد تينانت منصة؛ يتعارض مع قاعدة "حساب نظام لكل تينانت، لا حساب عالمي" المعتمدة في الدومينات الثلاثة |

**توصيتي: الإبقاء على A الآن** (فهو يحل خطر التصادم بالكامل، ومُتحقَّق منه، ومتسق مع Celery)، **مع إصلاحين ضيقين اختياريين** للمخاطر المتبقية في 4.3-أ و4.3-ب، وتسجيل C كبند تصميمي مؤجَّل إن كنت تريد فصل أموال التينانت عن أموال الأدمن قبل الإطلاق. B مرفوض عمليًا بسبب Celery.

### 4.3 مخاطر متبقية على التصميم A (حقيقية، ومن بيانات حية)

```
 tenant | admin_id | admin_user_tenant | sys_accts | user_with_id_eq_tenant
--------+----------+-------------------+-----------+-----------------------
      1 |        1 |                 1 |         1 |                      1
     15 |       48 |                 1 |         0 |
     16 |      774 |                16 |         1 |
```

> ⚠️ **تصحيح لاحق [نفس اليوم] — راجع §8.1 و§8.2:** عبارة "سينشئ بصمت محفظة" أدناه **غير دقيقة**. إنشاء المحفظة `flush()` فقط داخل savepoint، فيُلغى مع `InsufficientBalanceError`. والأهم أن الأدمن العابر للتينانت هو **الحالة الافتراضية** لكل تينانت تُنشأ عبر مسار المنتج، وليس حالة شاذة.

**(أ) 🟠 التينانت 15 (`نبت`) أدمنها من تينانت أخرى.** `admin_id=48` (`p_ctor_manual_admin`, `SUPER_ADMIN`) لكن `users.tenant_id=1`. لو نُودي `pay_invoice` للتينانت 15، فإن `FinanceService(db, 15).get_or_create_wallet_for_update(48)` (`finance/service.py:34-39`) **سينشئ بصمت محفظة `(user_id=48, tenant_id=15)`** لمستخدم ليس عضوًا في التينانت. هذا لا يسرّب مالًا (المحفظة الجديدة رصيدها صفر، فيفشل الدفع بـ`InsufficientBalanceError`)، لكنه:
- ينشئ صف محفظة عابر للتينانتات. **ويوجد سابقة فعلية:** `wallets.id=747` = `(user 774, tenant 1)`، ومستخدم 774 ينتمي للتينانت 16.
- `get_or_create_wallet_for_update` لا يتحقق من أن `user.tenant_id == self.tenant_id`، وهذه فجوة عامة في finance وليست خاصة بـsaas.
- حاليًا لا توجد اشتراكات للتينانت 15، فالخطر **كامن**.
- **إصلاح ضيق مقترح:** في `_get_tenant_admin_id`، تحقق من أن `admin.tenant_id == tenant_id` وإلا ارفع خطأ واضحًا (مثل `ValidationError("أدمن التينانت لا ينتمي لها")`). إنه سطران، والنطاق saas فقط.

**(ب) 🟡 أدمن التينانت 1 هو `user 1` = `p_system_treasury`.** هذا بقايا throwaway موثَّقة (`PROGRESS_LOG.md:268`). هو الآن الدافع الرسمي لكل فواتير التينانت 1، **بالتصميم** لا بالتصادم. **ومن المفارقة أن المحفظة التي خاف منها البند الأصلي (user 1) هي نفسها التي تُخصَم الآن**، لكن لسبب صحيح (هو الأدمن). هذه مشكلة بيانات اختبار وليست مشكلة كود، ولا أقترح لمسها في هذه الجلسة.

**(ج) 🟡 الأدمن الآخر يخصم من محفظة `admin_id`.** `require_admin_or_above` يسمح لأي أدمن في التينانت بتنفيذ `pay_invoice`، والخصم يكون دائمًا من محفظة `admin_id` وليس من محفظة المنادي. هذا مقبول ضمن التصميم A (الأدمن الرسمي هو "محفظة التينانت" فعليًا)، لكنه قرار منتجي يجب أن يكون معروفًا. **لا أقترح تغييره الآن.**

**(د) ℹ️ اشتراك واحد مستحق التجديد الآن** (تينانت 16، `auto_renew` و`ACTIVE` و`next_billing_date <= now`). عند تشغيل beat سيحاول الخصم من محفظة 774 في التينانت 16 (رصيدها 0)، فيتحول الاشتراك إلى `PAST_DUE`. هذا سلوك صحيح وأذكره فقط للعلم.

---

## 5. خطة التحقق الحي المقترحة

**ملاحظة جوهرية:** "إعادة إنتاج التصادم قبل الإصلاح" **لم تعد ممكنة** بلا إرجاع الكود إلى ما قبل `0ba7204`، ولا أنصح بذلك. البديل: **اختبار regression يثبت استحالة التصادم** في الكود الحالي.

### 5.1 (الخيار الموصى به) تحقق regression للتصادم، على بيانات throwaway

1. **لقطة قبل:** أرصدة المحافظ 39 و929 و930 و931، وعدد صفوف `wallets` و`transactions` و`saas_invoices` و`users`.
2. **Fixture:** تينانت throwaway `T` + مستخدم throwaway `U_collide` في `T` **بـ`id` = `T.id` صراحةً** (إدراج بـid صريح في مساحة غير مستخدمة، مع فحص مسبق أن الـid حر)، ومحفظة لـ`U_collide` برصيد 100. ثم أدمن throwaway `A` في `T` (`id ≠ T.id`) برصيد 100، واشتراك وفاتورة `PENDING` بمبلغ 10.
3. **تنفيذ:** `SaaSControlService(db, T.id).pay_invoice(invoice.id)` عبر الدالة الحقيقية.
4. **المتوقع:** محفظة `A` = 90، ومحفظة حساب نظام `T` = 10، و**محفظة `U_collide` = 100 بلا تغيير** (هذا هو الإثبات الجوهري)، والفاتورة `PAID`.
5. **تكرار نفس الإثبات لـ`process_auto_renewals(tenant_id=T.id)`** باشتراك مستحق.
6. **تنظيف صريح** بـ`DELETE` بترتيب FK (لأن `pay_invoice` يعمل `commit()` داخليًا، فلا يكفي `ROLLBACK` خارجي)، مع إعادة ضبط sequence إن لزم.
7. **لقطة بعد:** zero-diff على كل الجداول والمحافظ الحقيقية (39 و929 و930 و931).

### 5.2 (فقط إذا وافقت على إصلاح 4.3-أ) تحقق إضافي

- **قبل الإصلاح:** تينانت throwaway `T2` بـ`admin_id` = مستخدم من تينانت أخرى، ثم `pay_invoice` → **دليل** إنشاء محفظة عابرة `(admin, T2)`.
- **بعد الإصلاح:** نفس السيناريو → `ValidationError` واضح، و**صفر** صفوف محافظ جديدة.
- ثم regression: `tests/test_financeservice_tenant_binding_fix.py` و`test_saas_cancel_subscription_silent_write.py` و`test_trigger_renewals_endpoint_missing_commit.py`، مع ملاحظة أن الأول معروف بتسريب أموال user 1 (`PROGRESS_LOG.md:1059`)، فيجب أخذ لقطة المحفظة 39 قبله وبعده ومقارنة الفرق بالتسريب المعروف فقط.

---

## 6. قرارات مطلوبة منك

1. **إغلاق توثيقي:** هل أُحضّر (في هذا التقرير أولًا، للمراجعة) نص إغلاق الصف 264 + صف إغلاق لـ`saas-invoices-idempotency-key-schema-drift` يشير إلى `0ba7204` و`8fccfa1`؟
2. **تأكيد التصميم A** (الأدمن يدفع إلى حساب نظام التينانت)، أم تريد فتح بند تصميمي للخيار C (خزانة تينانت منفصلة)؟
3. **إصلاح 4.3-أ** (تحقق انتماء `admin_id` للتينانت داخل `_get_tenant_admin_id`): داخل نطاق هذه الجلسة أم بند backlog منفصل؟ (الفجوة الأعم في `finance.get_or_create_wallet_for_update` أقترح أن تكون بندًا منفصلًا حسب قاعدة فصل الاكتشافات الجانبية.)
4. **التحقق 5.1:** هل تريد تنفيذه (بيانات throwaway + تنظيف كامل) كتوثيق نهائي للإغلاق، أم يكفي الدليل الحي في §3.2 + تحقق `8fccfa1` الأصلي؟

---

## 7. قرارات المستخدم (الجولة 2)

1. **نص الإغلاق:** يُحضَّر هنا أولًا للمراجعة (§11). إغلاق الصف 264 بمرجع `0ba7204`، وصف **جديد** لـ`saas-invoices-idempotency-key-schema-drift` بمرجع `8fccfa1`/migration 036، مع التصريح بأنها **فجوة توثيق، لا باج حي**.
2. **التصميم A مؤكَّد** كتصميم قائم (الأدمن يدفع إلى حساب نظام التينانت). **الخيار C** (خزانة تينانت منفصلة) يُسجَّل كبند تصميمي مؤجَّل، بلا جلسة تصميم الآن.
3. **إصلاح 4.3-أ داخل هذه الجلسة**، مع تحقق §5.2. الفجوة الأعم في `finance.get_or_create_wallet_for_update` تُسجَّل كبند backlog **منفصل** ولا تُصلَح هنا.
4. **§5.1 يصبح اختبار regression دائمًا**، مع سيناريو 4.3-أ في نفس الملف.

**⛔ لكن قبل التنفيذ: اكتشافان جديدان في §8 يغيّران أثر القرار 3، ويحتاجان تأكيدك (§12).**

---

## 8. اكتشافات جديدة أثناء تحضير التنفيذ (قراءة فقط)

### 8.1 تصحيح: المحفظة العابرة **لا تُحفَظ** في السيناريو الذي وصفته في §4.3-أ

- `WalletRepository.create` (`finance/repository.py:34-49`) يعمل `flush()` فقط، بلا commit.
- `FinanceService.transfer` ينادي `get_or_create_wallet_for_update` **داخل** `async with self.db.begin_nested()` (`finance/service.py:96-99`).
- المحفظة الجديدة رصيدها 0، فيُرفع `InsufficientBalanceError` داخل الـsavepoint، ويُلغى صف المحفظة معه.
- **الأثر الحقيقي إذن أضيق مما كتبت:** لا تنشأ محفظة عابرة بصمت. الضرر الفعلي يحدث **فقط إذا كانت محفظة `(admin, T)` موجودة مسبقًا وممولة**، وعندها يُخصم من محفظة شخص **ليس عضوًا** في التينانت. (وجود صفوف عابرة فعلًا ثابت: `wallets.id=747` = `(user 774, tenant 1)` بينما 774 في التينانت 16، ورصيدها `{}`.)
- في الحالة الشائعة (محفظة غير موجودة): الخطأ الحالي `"الرصيد غير كافٍ لدفع الفاتورة"` **مضلِّل**، لأن السبب الحقيقي أن الدافع ليس عضوًا في التينانت.

### 8.2 🔴 الأدمن العابر للتينانت هو **الحالة الافتراضية** لكل تينانت جديدة في المنتج

- المسار **الوحيد** لإنشاء تينانت: `POST /academy/tenants` (`academy/router.py:66-73`، `get_current_superuser`) ← `AcademyService.create_tenant(name, domain, admin_id, branding)` (`academy/service.py:61-75`). و`admin_id` **يأتي من جسم الطلب** (`academy/schemas.py:16`).
- `users.tenant_id` إلزامي (NOT NULL + FK)، والتينانت الجديدة **لا تحتوي أي مستخدم لحظة إنشائها**. إذن `admin_id` **يجب حتمًا** أن يشير لمستخدم من تينانت أخرى، غالبًا مشرف المنصة في التينانت 1. هذا بالضبط ما حدث للتينانت 15 (`admin_id=48`، مستخدم في التينانت 1، `SUPER_ADMIN`).
- **لا يوجد أي مسار كود يعيد تعيين `admin_id` لاحقًا.** الـgrep على `admin_id` في academy لا يعطي إلا الإنشاء. التينانت 16 أدمنها داخلي لأنها fixture يدوية (`TEST_TENANT_B`).
- **النتيجة:** مع التصميم A الحالي، **فوترة SaaS غير قابلة للدفع فعليًا لأي تينانت تُنشأ عبر المنتج**. الدافع هو مشرف المنصة، ومحفظته داخل التينانت الجديدة غير موجودة (رصيد 0)، فكل دفع يفشل بـ`InsufficientBalanceError`، ويتحول كل تجديد تلقائي إلى `PAST_DUE`. هذا قائم **اليوم، قبل أي تعديل مني**.
- **أثر إصلاح 4.3-أ على هذه الحقيقة:**
  - **لا يكسر شيئًا يعمل اليوم.** المسار فاشل أصلًا لهذه التينانتات، ما لم توجد محفظة `(admin, T)` ممولة، وهي بالضبط حالة الضرر التي نريد منعها.
  - **يغيّر نوع الفشل** من `InsufficientBalanceError` مضلِّل إلى `ValidationError` صريح يسمّي السبب الحقيقي.
  - في `process_auto_renewals`: الاشتراك يصبح `FAILED` (فرع `except Exception` العام، `service.py:330-332`) **بدل** `PAST_DUE`. **هذا فرق سلوكي حقيقي:** `PAST_DUE` يطلق مسار grace-period والإشعارات (`check_past_due_subscriptions`)، أما `FAILED` فيبقى الاشتراك `ACTIVE` ويعاد المحاولة يوميًا بلا نهاية وبلا إشعار. لا يوجد اليوم أي اشتراك لتينانت بأدمن عابر (التينانت 15 بلا اشتراكات)، فالفرق **كامن**.
- **هذه مشكلة تصميمية في مسار onboarding، وليست في saas.** لا أقترح حلّها هنا. أقترح بند backlog جديدًا (§11.4-ب).

---

## 9. الـdiff المقترح لإصلاح 4.3-أ (حرفي، للمراجعة، **لم يُطبَّق**)

الملف: `eppne-backend/app/domains/saas/service.py` (لا توجد به تعديلات غير مُلتزَمة حاليًا، و`git diff` نظيف). **لا لمس** لـ`academy/repository.py` (به تعديلات سابقة غير مُلتزَمة لا تخص هذه الجلسة).

```diff
@@ async def _get_tenant_admin_id(self, tenant_id: int) -> int:
         # الدافع الرسمي لفواتير/تجديدات التينانت هو AcademyTenant.admin_id
         # الإجباري الموجود بالفعل — راجع §7 بند 4 من مستند تصميم حساب
         # النظام الموحَّد لكل تينانت.
         from app.domains.academy.repository import AcademyRepository
+        from app.domains.identity.repository import UserRepository
         academy_repo = AcademyRepository(self.db)
         tenant = await academy_repo.get_tenant_by_id(tenant_id)
         if not tenant:
             raise NotFoundError("التينانت غير موجود")
+        # الأدمن لازم يكون عضوًا في نفس التينانت — وإلا transfer() هيخصم من
+        # محفظة (admin, tenant_id) لمستخدم مش عضو فيها. راجع
+        # saas-sender-id-collision-fix-session-log.md §4.3-أ و§8.
+        admin = await UserRepository(self.db).get_by_id(cast(int, tenant.admin_id), tenant_id)
+        if admin is None:
+            raise ValidationError("أدمن التينانت لا ينتمي لنفس التينانت — لا يمكن تحديد دافع الفاتورة")
         return cast(int, tenant.admin_id)
```

- `UserRepository.get_by_id(user_id, tenant_id)` (`identity/repository.py:21-22`) يفلتر بالفعل على `User.id == user_id AND User.tenant_id == tenant_id`، فلا حاجة لاستعلام يدوي أو `import select` جديد.
- استيراد مؤجَّل بنفس نمط `AcademyRepository` السطر السابق (تجنبًا لدورات الاستيراد).
- `ValidationError` مستورد أصلًا (`service.py:29`).
- **الترتيب مهم:** الفحص في `_get_tenant_admin_id` يسبق `get_or_create_system_account` في الموقعين (`:288` قبل `:289`، `:698` قبل `:699`)، فلن يُنشأ حساب نظام لتينانت دافعها غير صالح.
- الحجم الفعلي: 1 استيراد + 3 تعليق + 3 منطق، وليس "سطرين" كما قدّرت سابقًا.

---

## 10. خطة التحقق الموحَّدة (§5.1 + §5.2) — ملف الاختبار الدائم

**الملف:** `eppne-backend/tests/test_saas_pay_invoice_sender_id_collision_guard.py`، بنفس نمط `test_finance_non_positive_amount_guard.py` (fixture `db` الحقيقي، صفر mock، تنظيف صريح).

### 10.1 Setup واحد مشترك (fixture على مستوى الـmodule)

| العنصر | التفاصيل |
|---|---|
| **X** | يُختار وقت التشغيل: أصغر عدد في `[2, min(last_value(academy_tenants_id_seq), last_value(users_id_seq))]` غير مستخدم في `users.id` **ولا** `academy_tenants.id`. (اليوم: 9..14، 17..20.) **أقل من قيمتي الـsequence** فلا يمكن أن يتصادم مع أي `nextval` مستقبلي، بخلاف نمط بند `invoicing-invoice-number` الذي أغلقناه. |
| **التينانت T** | `AcademyTenant(id=X, name/domain=REGTEST_SIDCOL_{suffix}, admin_id=1)` مؤقتًا (قيد FK)، ثم `UPDATE admin_id = A` بعد إنشاء A. |
| **U_collide** | `User(id=X, tenant_id=X, ...)` **صراحةً بـid = tenant id**، أي السيناريو الأصلي حرفيًا. محفظة `(X, X)` برصيد 100 MR_USDT. |
| **A** | أدمن T (id من الـsequence، `≠ X`)، محفظة `(A, X)` برصيد 100. |
| **التينانت T2** | `AcademyTenant(admin_id=A)`، أي **A عضو في T وليس في T2** (نفس شكل التينانت 15 حرفيًا). محفظة `(A, T2)` **ممولة مسبقًا برصيد 100** بإدراج SQL مباشر، لمحاكاة حالة الضرر الحقيقية في §8.1. |
| **خطة/خدمة SaaS** | عبر `SaaSRepository.create_service/create_plan` (`REGTEST-SIDCOL-*`، سعر 10) + `PlanServiceAccess`، بنفس نمط `test_trigger_renewals_...`. |

### 10.2 الاختبارات (4)

| # | الاختبار | التوقع |
|---|---|---|
| 1 | `pay_invoice` على T (فاتورة PENDING بمبلغ 10) | A: 100→90؛ حساب نظام T: +10؛ **U_collide: 100 بلا تغيير** (الإثبات الجوهري)؛ `transactions.sender_id == A` و`!= X`؛ الفاتورة `PAID` |
| 2 | `process_auto_renewals(tenant_id=X)` باشتراك مستحق | نفس الإثبات: A −10، النظام +10، **U_collide بلا تغيير**، `sender_id == A`، النتيجة `SUCCESS` |
| 3 | `pay_invoice` على T2 | `ValidationError`؛ محفظة `(A, T2)` **100 بلا تغيير**؛ صفر `transactions` جديدة؛ الفاتورة لا تزال `PENDING`؛ **لا حساب نظام أُنشئ لـT2** |
| 4 | `process_auto_renewals(tenant_id=T2)` | النتيجة `FAILED` مع رسالة الـValidationError؛ محفظة `(A, T2)` 100؛ صفر transactions (يوثّق فرق `FAILED` مقابل `PAST_DUE` من §8.2 صراحةً) |

- كل تحقق من الأرصدة عبر **جلسة `AsyncSessionLocal()` مستقلة** بعد النداء.
- كل اختبار يستخدم فاتورة واشتراكًا مستقلين حتى لا تتداخل مفاتيح idempotency (`PAY-INV-{id}` و`AUTO-RENEW-{sub.id}-{YYYY-MM}`).

### 10.3 الـmutation check (على 4.3-أ فقط)

- إرجاع الأسطر الـ3 المنطقية مؤقتًا (بلا حذف الاستيراد) ← تشغيل الملف.
- **المتوقع:** الاختباران 3 و4 **يفشلان**. في الاختبار 3 سينجح الدفع ويُخصم 10 من `(A, T2)`، وهذا **يثبت حيًا ضرر §8.1**. أما الاختباران 1 و2 فينجحان (غير مرتبطين بالـmutation).
- ⚠️ **الـmutation run سيُحدث تحويلًا حقيقيًا** من `(A, T2)` إلى حساب نظام T2. كلاهما throwaway ويُنظَّف بنفس الـcleanup، لكن سأتحقق يدويًا من التنظيف بعد الـmutation run تحديدًا.
- استعادة الكود، ثم إعادة التشغيل ← 4/4 تنجح، ثم `git diff` للتأكد من التطابق الحرفي مع §9.

### 10.4 التنظيف (في `finally` + تحقق مستقل)

1. `delete from transactions where sender_id = any(:u) or receiver_id = any(:u)`، حيث `:u` = X و A و**حسابات النظام التي أُنشئت في T وT2** (تُجمع بـ`select id from users where tenant_id in (X, T2)` **قبل** الحذف).
2. حذف كل جداول `tenant_id` لـT2 ثم T بجولات (نمط `_cleanup` الحالي)، ثم `PlanServiceAccess`/`ServicePlan`/`ServiceCatalog` بالـid، ثم `academy_tenants` (T2 أولًا ثم T؛ مع `admin_id` لـT2 يشير لـA في T، فيُحذف T2 **قبل** مستخدمي T).
3. **تحقق مستقل بعد كل تشغيلة:** صفر صفوف لـ`users/wallets/transactions/saas_*` تخص X أو T2 أو `REGTEST-SIDCOL`، وقيم الـsequences لم تتأثر بالـids الصريحة.

### 10.5 الـregression suite

- لقطة **قبل** (المحفظة 39، المحفظة 929، `count(*)` لـ`transactions/wallets/users/saas_invoices/saas_tenant_subscriptions`، و`max(id)` للـtransactions).
- تشغيل: `test_financeservice_tenant_binding_fix.py` + `test_saas_cancel_subscription_silent_write.py` + `test_trigger_renewals_endpoint_missing_commit.py` + الملف الجديد.
- لقطة **بعد**: أي فرق في المحفظة 39 يجب أن يساوي **بالضبط** مجموع التحويلات الجديدة `sender_id=1 AND receiver_id=957 AND idempotency_key LIKE 'AUTO-RENEW-%'` المنشأة أثناء التشغيل (التسريب المعروف `test-financeservice-tenant-binding-leaks-user1-funds`). وأي فرق آخر غير مفسَّر يُعتبر فشلًا.
- **ملاحظة:** الإصلاح لا يؤثر على التينانت 1 (أدمنها 1 عضو فيها)، فلا يُتوقع أي تغيير في سلوك الاختبارات الثلاثة.

---

## 11. مسودات نصوص `PROGRESS_LOG.md` (للمراجعة فقط، **لم تُكتب**)

**الموقع:** حسب السابقة (إغلاق `474d3af`، السطر 1078)، **لا يُعدَّل** نص/عمود الحالة للصف 264 الأصلي. تُضاف فقرة إغلاق مؤرَّخة بعد آخر إغلاق (بعد السطر 1078)، وتُضاف الصفوف الجديدة في نهاية الجدول (بعد السطر 1076). *إن أردت تعديل عمود الحالة في الصف 264 إلى ✅ أيضًا فأخبرني.*

### 11.1 فقرة الإغلاق

> **✅ إغلاق مؤرَّخ [2026-09-24] — `saas-pay-invoice-sender-id-user-id-collision` (الصف `[2026-08-24]` أعلاه): مُغلَق (commit `0ba7204`، 2026-08-25) — فجوة توثيق، لا باج حي.** جلسة `saas-sender-id-collision-fix` (`.claude/reports/saas-sender-id-collision-fix-session-log.md`). التصادم كان مُصلَحًا **قبل بدء هذه الجلسة بشهر**: `0ba7204` (`feat(finance): convert 9 tenant-system-account call sites`) استبدل `sender_id=self.tenant_id` بـ`sender_id=AcademyTenant.admin_id` (`SaaSControlService._get_tenant_admin_id`) و`receiver_email="system@eppne.com"` بحساب نظام التينانت (`get_or_create_system_account`) في `pay_invoice` و`process_auto_renewals`، لكن هذا الصف لم يُغلَق أبدًا. **دليل حي (SELECT فقط):** 164 تحويلًا `PAY-INV-*`/`AUTO-RENEW-*` كلها `sender_id=1` (أدمن تينانت 1) إلى `receiver_id=957` (`__system_tenant_1__`)، والمجموع 173 MR_USDT = 875 − 702 بالضبط، وصفر تحويلات مشتقة من `tenant_id`. **التصميم A مؤكَّد صراحةً كتصميم قائم** (الأدمن يدفع إلى حساب نظام التينانت؛ البديل B "المستخدم المنادي" مرفوض لعدم وجود مستخدم في Celery؛ C مؤجَّل، انظر `saas-tenant-treasury-account-separation-design`). **مُضاف في نفس الجلسة:** [يُملأ بعد التنفيذ: commit إصلاح تحقق عضوية الأدمن + اختبار `tests/test_saas_pay_invoice_sender_id_collision_guard.py` (4 اختبارات، سيناريو `user.id == tenant.id` حرفيًا) + نتيجة الـmutation + الـregression]. **وفي نفس الإغلاق:** `saas-invoices-idempotency-key-schema-drift` (الصف الجديد أدناه).

### 11.2 صف جديد: الانحراف (يُنشأ مُغلَقًا)

> | — | **`saas-invoices-idempotency-key-schema-drift`** [2026-08-24، صف مُنشأ بأثر رجعي 2026-09-24] — ذُكر فقط داخل نص `saas-pay-invoice-sender-id-user-id-collision` ولم يُمنح صفًا خاصًا به قط: `Invoice.idempotency_key` (`saas/models.py:161`) مُعرَّف في الموديل ومفقود من جدول `saas_invoices` الحي منذ أول migration أنشأته، فكان أي SELECT/INSERT على `Invoice` يفشل بـ`UndefinedColumnError`، ما حجب `pay_invoice` و`process_auto_renewals` (عبر `_generate_invoice`) بالكامل. **أُصلح في commit `8fccfa1` (2026-08-25)**، migration `036_add_idempotency_key_to_saas_invoices` (عمود + فهرس unique جزئي `WHERE idempotency_key IS NOT NULL`)، ومُتحقَّق منه حيًا في 2026-09-24 (`\d saas_invoices` + alembic head `068`). **فجوة توثيق، لا باج حي.** | ✅ **مُغلَق** (`8fccfa1`) | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §2 |

### 11.3 صف جديد: فجوة finance العامة

> | — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، فأي مسار يمرّر `sender_id` لمستخدم من تينانت أخرى يحصل على محفظة `(user, tenant)` عابرة (تُنشأ، أو يُخصم منها إن كانت موجودة وممولة). `transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. دليل وجود صفوف عابرة فعلًا: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`، لكن بقية الدومينات التي تمرّر `sender_id` لـ`transfer()` لم تُفحص من هذه الزاوية. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | نفس التقرير §8.1 |

### 11.4 صفان جديدان إضافيان

**(أ) الخيار C المؤجَّل (قرارك رقم 2):**

> | — | **`saas-tenant-treasury-account-separation-design`** [2026-09-24] — بند تصميم مؤجَّل (لا جلسة تصميم بعد، بقرار صريح): التصميم A القائم يجعل فواتير/تجديدات SaaS تُخصم من **المحفظة الشخصية** لـ`AcademyTenant.admin_id`. الخيار C (محفظة خزانة للتينانت مستقلة عن أي شخص) يفصل أموال التينانت عن أموال الأدمن، لكنه يتطلب مفهوم حساب ثانٍ لكل تينانت (الحالي حساب نظام واحد هو **المستقبِل**) وآلية تمويل. يُفتح فقط إن قرر المنتج هذا الفصل قبل الإطلاق الأوسع. | ⏸️ **مؤجَّل — قرار منتجي** | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §4.2 |

**(ب) اكتشاف §8.2 (يحتاج موافقتك على تسجيله):**

> | — | **`tenant-onboarding-admin-always-cross-tenant-saas-unpayable`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§8.2): المسار الوحيد لإنشاء تينانت (`POST /academy/tenants` ← `AcademyService.create_tenant`) يأخذ `admin_id` من جسم الطلب، والتينانت الجديدة لا تحتوي مستخدمين لحظة إنشائها (`users.tenant_id` إلزامي)، فـ`admin_id` **يشير حتمًا** لمستخدم من تينانت أخرى (مثال حي: تينانت 15، `admin_id=48` في تينانت 1)، ولا يوجد أي مسار يعيد تعيينه. ومع تصميم دافع SaaS القائم (`admin_id`)، **فوترة SaaS غير قابلة للدفع لأي تينانت مُنشأة عبر المنتج**: كان الفشل قبل هذه الجلسة `InsufficientBalanceError`/`PAST_DUE` مضلِّلًا، وبعد تحقق العضوية أصبح `ValidationError`/`FAILED` صريحًا. يحتاج تصميم onboarding (إنشاء أول أدمن داخل التينانت ذريًا، أو endpoint لإعادة تعيين `admin_id` لعضو داخلي). **ملاحظة:** `FAILED` في `process_auto_renewals` لا يطلق مسار grace/إشعارات `PAST_DUE`، بل يعيد المحاولة يوميًا بصمت. | 🟠 **مفتوح، أولوية عالية قبل الإطلاق** — يمنع أي فوترة SaaS حقيقية لتينانت جديدة | نفس التقرير §8.2 |

---

## 12. ⛔ نقطة توقف — سؤال واحد قبل أي تعديل كود

اكتشاف §8.2 يعني أن إصلاح 4.3-أ سيُطبَّق على **الحالة الافتراضية** لكل تينانت جديدة، وليس على حالة شاذة. البدائل:

- **(1) تطبيق §9 كما هو (توصيتي).** fail-closed وصريح، ولا يكسر شيئًا يعمل اليوم (المسار فاشل أصلًا لهذه التينانتات)، ويمنع الخصم من محفظة غير عضو. الثمن: `PAST_DUE` يصبح `FAILED` في التجديد التلقائي لتينانتات الأدمن العابر (كامن اليوم، ويُوثَّق في 11.4-ب).
- **(2) تطبيق §9 مع تمييز الحالة في `process_auto_renewals`،** بحيث يعامل `ValidationError` الدافع كـ`PAST_DUE` لا `FAILED`، ليبقى مسار grace والإشعارات. يعني أسطرًا إضافية في `process_auto_renewals`، أي توسيع نطاق.
- **(3) عدم تطبيق الكود الآن.** تسجيل 11.3 و11.4-ب فقط، وإصلاح المسألة من جذرها في جلسة onboarding.

**مطلوب منك:** اختيار (1) أو (2) أو (3)، والموافقة على تسجيل 11.4-ب كبند جديد. لم يُعدَّل أي كود ولا `PROGRESS_LOG.md`، ولا staging.

---

## 13. قرارات المستخدم (الجولة 3)

- **§12: الخيار (1)**، أي تطبيق §9 كما هو. السبب: المسار يفشل أصلًا اليوم لتينانتات الأدمن العابر، فالتغيير يمس **نوع الفشل** فقط ولا يحوّل شيئًا يعمل إلى معطّل. فرق `FAILED`/`PAST_DUE` حقيقي لكنه كامن، ومكانه إصلاح onboarding الجذري.
- **11.4-ب مُعتمَد**، **مع إضافة إلزامية**: النص يجب أن ينص صراحةً على أن إصلاح onboarding مستقبلًا **يجب أن يستعيد دلالة `PAST_DUE`** (grace period + إشعارات) لفشل `process_auto_renewals` بسبب عدم عضوية الأدمن، ولا يتركه يعيد المحاولة كـ`FAILED` بصمت للأبد (§15.4).
- **11.1 و11.2 و11.3 و11.4-أ معتمدة.** الـhash في 11.1 يُملأ بعد commit هذه الجلسة.

---

## 14. التنفيذ والتحقق

### 14.1 الإصلاح: مُطبَّق حرفيًا كما في §9

`git diff eppne-backend/app/domains/saas/service.py` بعد استعادة الـmutation:

```diff
@@ -66,10 +66,17 @@ class SaaSControlService:
         # الإجباري الموجود بالفعل — راجع §7 بند 4 من مستند تصميم حساب
         # النظام الموحَّد لكل تينانت.
         from app.domains.academy.repository import AcademyRepository
+        from app.domains.identity.repository import UserRepository
         academy_repo = AcademyRepository(self.db)
         tenant = await academy_repo.get_tenant_by_id(tenant_id)
         if not tenant:
             raise NotFoundError("التينانت غير موجود")
+        # الأدمن لازم يكون عضوًا في نفس التينانت — وإلا transfer() هيخصم من
+        # محفظة (admin, tenant_id) لمستخدم مش عضو فيها. راجع
+        # saas-sender-id-collision-fix-session-log.md §4.3-أ و§8.
+        admin = await UserRepository(self.db).get_by_id(cast(int, tenant.admin_id), tenant_id)
+        if admin is None:
+            raise ValidationError("أدمن التينانت لا ينتمي لنفس التينانت — لا يمكن تحديد دافع الفاتورة")
         return cast(int, tenant.admin_id)
```

**مطابق لـ§9 سطرًا بسطر.** لا توجد تعديلات أخرى في `app/domains/saas/`.

### 14.2 ملف الاختبار الدائم

`eppne-backend/tests/test_saas_pay_invoice_sender_id_collision_guard.py` (جديد، غير متتبَّع)، 4 اختبارات بنفس جدول §10.2.

**انحراف واحد مقصود عن §10.1:** الـsetup **helper مشترك** (`_seed()`) يُستدعى داخل كل اختبار، وليس fixture بنطاق module. السبب: fixture `db` في `conftest.py` يعمل `engine.dispose()` بعد كل اختبار (مشكلة event loop على Windows)، فالـfixture المشترك على مستوى الـmodule غير آمن. ولأن كل اختبار يأخذ نسخة مستقلة من T/T2، يستطيع الـmutation check أن يُفشل الاختبارين 3 و4 وحدهما بلا تلوث متبادل. **صفر تكرار في كود الـfixtures.**

تفاصيل أخرى:
- **X:** يُختار وقت التشغيل بـ`generate_series` تحت `least(last_value(tenant_seq), last_value(users_seq))`، والاختبار يتحقق صراحةً من `U_collide.id == T.id != A.id`.
- **T2:** `admin_id = A` (عضو في T فقط)، مع محفظة `(A, T2)` ممولة بـ100 بـSQL مباشر.
- **الاختباران 3 و4:** لا يستخدمان `pytest.raises` مباشرة. يلتقطان النتيجة، ثم يقرآن الرصيد والـtransactions، ثم يعملان assert مجمَّعًا **رسالته تتضمن الرصيد الفعلي** لـ`(A, T2)`. هذا ما سمح بإثبات الضرر حيًا في الـmutation run (§14.4).

### 14.3 التشغيل الأول: الإصلاح مُطبَّق

```
4 passed, 3 warnings in 471.82s (0:07:51)
```

**تحذير يستحق التسجيل** (في الاختبارين 1 و2):

```
SAWarning: Multiple rows returned with uselist=False for eagerly-loaded attribute 'User.wallet'
```

المستخدم A لديه صفّا محفظة (`(A, T)` و`(A, T2)`)، والعلاقة `User.wallet` معرَّفة `uselist=False`. هذا **أثر مباشر آخر للمحافظ العابرة للتينانت**: أي كود يقرأ `user.wallet` لمستخدم له محفظة عابرة سيحصل على محفظة عشوائية من الاثنتين. أضفته إلى نص 11.3 (§15.3).

**تحقق بقايا بعد التشغيل:** 0 تينانتات `REGTEST_SIDCOL%`، و0 مستخدمين `p_sidcol%` (ولا أي مستخدم بـid في 9..20)، و0 خطط/خدمات، و0 `saas_invoices`، و0 محافظ يتيمة. التينانتات الموجودة `1,15,16` فقط. الـsequences تقدمت بالتخصيص الطبيعي فقط (`188→192` = 4 تينانتات T2؛ `14000→14006` = 4 أدمن + 2 حساب نظام لـT في الاختبارين 1 و2). المحفظة 39 بلا تغيير (702.0).

### 14.4 الـmutation check (حذف الأسطر المنطقية الثلاثة فقط)

**التشغيلة الكاملة:**

```
FAILED ...::test_pay_invoice_rejects_admin_from_another_tenant
FAILED ...::test_auto_renewal_fails_for_admin_from_another_tenant
2 failed, 2 passed, 1 warning in 359.27s (0:05:59)
```

الاختبار 4 تحت الـmutation:

```
assert ({'status': 'SUCCESS', 'subscription_id': 924, 'tx_hash': 'TX-54C4B6FEE006'} ... 'SUCCESS' == 'FAILED'
```

أي أن التجديد **نجح وخصم فعليًا** من `(A, T2)`.

رسالة الاختبار 3 حُجبت في الـgrep الأول بسبب ترميز الإخراج، فأُعيد تشغيله **وحده تحت نفس الـmutation** وحُفظ الإخراج كاملًا في `.claude/reports/saas-sender-id-collision-mutation-evidence.txt`:

```
AssertionError: أدمن من تينانت تانية اتقبل كدافع: raised=False، رصيد (A, T2)=90.0، transactions=[(14015, 14016, Decimal('10.00000000'))]
1 failed, 1 warning in 140.27s (0:02:20)
```

**هذا إثبات حي لضرر §8.1:** بلا الفحص، محفظة ممولة لمستخدم **ليس عضوًا** في T2 خُصم منها `100 → 90`، بتحويل حقيقي من A (14015) إلى حساب نظام T2 (14016) أُنشئ ضمنيًا.

**الاستعادة:** أُعيدت الأسطر الثلاثة، و`git diff` مطابق لـ§9 حرفيًا (§14.1). **بقايا بعد تشغيلتي الـmutation:** 0 في كل الفئات، بما فيها حساب نظام T2 والتحويل الخاص به، فالـcleanup داخل الاختبارات التقطهما.

### 14.5 الـregression suite (مع الإصلاح)

```
test_financeservice_tenant_binding_fix.py::test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due PASSED
test_financeservice_tenant_binding_fix.py::test_pay_invoice_same_tenant_still_works_after_removing_self_finance PASSED
test_saas_cancel_subscription_silent_write.py::test_cancel_subscription_persists_cancelled_status_independent_session PASSED
test_saas_cancel_subscription_silent_write.py::test_cancel_already_cancelled_subscription_raises_validation_error PASSED
test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_persists_past_due_after_fix PASSED
test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_success_path_no_double_commit_error PASSED
test_saas_pay_invoice_sender_id_collision_guard.py (×4) PASSED
10 passed, 4 warnings in 194.87s (0:03:14)
```

الإخراج الكامل في `.claude/reports/saas-sender-id-collision-regression-run.txt`.

**اللقطات** (`...-regression-snapshot-before.txt` و`...-after.txt`):

| | w39 | w929 | max_tx | tx | wallets | users | inv | subs | tenants |
|---|---|---|---|---|---|---|---|---|---|
| قبل | 702.0 | 173.0 | 1037 | 200 | 98 | 124 | 0 | 24 | 3 |
| بعد | 699.0 | 176.0 | 1047 | 203 | 98 | 124 | 0 | 24 | 3 |

**نسبة الفرق (−3 على w39، +3 على w929، +3 tx):**

| tx | المفتاح | من ← إلى | المصدر | معروف؟ |
|---|---|---|---|---|
| 1045 | `AUTO-RENEW-926-2026-09` | 1 ← 957، 1.0 | `test_financeservice_tenant_binding_fix` (FINBIND) | ✅ `test-financeservice-tenant-binding-leaks-user1-funds` |
| 1046 | `PAY-INV-179` | 1 ← 957، 1.0 | `test_financeservice_tenant_binding_fix` (FINBIND) | ✅ نفس البند |
| 1047 | `AUTO-RENEW-932-2026-09` | 1 ← 957، 1.0 | `test_trigger_renewals_endpoint_missing_commit` (`..._success_path_...`، `REGTEST-TRIGREN-PLAN-*`) | ❌ **غير مسجَّل** |

- **تصحيح لقاعدتي في §10.5:** كتبت أن التسريب المعروف هو `AUTO-RENEW-%` فقط، لكن نص البند المعروف نفسه يشمل **`PAY-INV-*` أيضًا** (−2 لكل تشغيل). الـ−2 من FINBIND مفسَّرة بالكامل بالبند المعروف.
- **الـ−1 الثالثة تسريب سابق غير مسجَّل** في `test_trigger_renewals_endpoint_missing_commit.py` (اختبار مسار SUCCESS). نفس الآلية بالضبط: `_cleanup` هناك يحذف الاشتراك/الخطة/الخدمة/الفاتورة لكنه لا يعكس التحويل ولا يحذف صف `transactions`/`audit_logs`. **ليس ناتجًا عن تعديلي**، لأن أدمن التينانت 1 (user 1) عضو فيها فلا يتأثر بالفحص الجديد، والدليل موجود من قبل: 107 تحويلات `AUTO-RENEW` في §3.2 تشمل خطط `REGTEST-TRIGREN-*` منذ 2026-09-08.
- **ملف الاختبار الجديد لم يترك أي أثر:** ids التحويلات 1038-1044 (من تشغيلته داخل الـsuite) حُذفت كلها، فلم يزد `count(tx)` إلا بـ3.
- **صفوف `audit_logs` المرتبطة بالتسريبات الثلاثة:** 1027 (← tx 1045)، 1028 (← 1046)، 1029 (← 1047)، كلها `user_id=1, tenant_id=1, action=TRANSFER`.

---

## 15. التنظيف

### 15.1 تنظيف fixtures هذه الجلسة: ✅ تلقائي، ومُتحقَّق منه (صفر بقايا)

تم داخل `finally` في كل اختبار، وتحقق مستقل بعد كل تشغيلة (§14.3 و§14.4 ونهاية §14.5):

```
residue | tenants REGTEST_SIDCOL: 0 | users p_sidcol: 0 | plans regtest_sidcol: 0 | tx 1038..1044: 0 | orphan wallets: 0
```

**لا حاجة لأي أمر تنظيف يدوي لبيانات هذه الجلسة.**

### 15.2 عكس تسريب الـregression (−3 على user 1): **مقترح فقط، لم يُنفَّذ، وينتظر موافقتك**

بنفس نمط `.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql` (مُحرَس بقيم متوقعة):

```sql
BEGIN;
-- كل UPDATE مشروط بالقيمة الحالية بالضبط؛ المتوقع rowcount=1 لكلٍّ
UPDATE wallets SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(702.0))
 WHERE id = 39  AND user_id = 1   AND (balances->>'MR_USDT')::numeric = 699.0;
UPDATE wallets SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(173.0))
 WHERE id = 929 AND user_id = 957 AND (balances->>'MR_USDT')::numeric = 176.0;
-- المتوقع rowcount=3 لكلٍّ
DELETE FROM audit_logs   WHERE id IN (1027, 1028, 1029) AND user_id = 1 AND action = 'TRANSFER';
DELETE FROM transactions WHERE id IN (1045, 1046, 1047) AND sender_id = 1 AND receiver_id = 957 AND amount = 1;
-- تحقق قبل COMMIT: w39=702.0، w929=173.0، max(transactions.id)=1037
COMMIT;  -- أو ROLLBACK إن لم تطابق أي rowcount
```

**ملاحظة:** هذا العكس يعيد القاعدة إلى لقطة "قبل" (702/173)، **وليس** إلى ما قبل كل التسريبات التاريخية (تسريب 09-18 وتسريبات TRIGREN السابقة لم تُعكَس أبدًا، حسب البند المعروف).

---

## 16. مسودات `PROGRESS_LOG.md` النهائية (بعد تعديلات الجولة 3، **لم تُكتب**)

### 16.1 فقرة الإغلاق (11.1، مُحدَّثة بالنتائج؛ الـhash يُملأ بعد الـcommit)

> **✅ إغلاق مؤرَّخ [2026-09-24] — `saas-pay-invoice-sender-id-user-id-collision` (الصف `[2026-08-24]` أعلاه): مُغلَق (commit `0ba7204`، 2026-08-25) — فجوة توثيق، لا باج حي.** جلسة `saas-sender-id-collision-fix` (`.claude/reports/saas-sender-id-collision-fix-session-log.md`). التصادم كان مُصلَحًا **قبل بدء هذه الجلسة بشهر**: `0ba7204` استبدل `sender_id=self.tenant_id` بـ`sender_id=AcademyTenant.admin_id` (`SaaSControlService._get_tenant_admin_id`) و`receiver_email="system@eppne.com"` بحساب نظام التينانت (`get_or_create_system_account`) في `pay_invoice` و`process_auto_renewals`، لكن هذا الصف لم يُغلَق أبدًا. **دليل حي:** 164 تحويلًا `PAY-INV-*`/`AUTO-RENEW-*` كلها `sender_id=1` (أدمن تينانت 1) إلى `957` (`__system_tenant_1__`)، وصفر تحويلات مشتقة من `tenant_id`. **التصميم A مؤكَّد صراحةً كتصميم قائم** (البديل B "المستخدم المنادي" مرفوض لعدم وجود مستخدم في Celery؛ C مؤجَّل: `saas-tenant-treasury-account-separation-design`). **مُضاف في نفس الجلسة (commit `<HASH>`):** تحقق عضوية الأدمن في `_get_tenant_admin_id` (`ValidationError` إن لم يكن `admin_id` عضوًا في التينانت، ويسبق `get_or_create_system_account`)، واختبار دائم `tests/test_saas_pay_invoice_sender_id_collision_guard.py` (4/4) يثبت سيناريو `user.id == tenant.id` حرفيًا لـ`pay_invoice` و`process_auto_renewals`. **Mutation:** حذف الفحص يُفشل الاختبارين 3 و4، وأثبت حيًا الخصم من محفظة ممولة لغير عضو (`(A, T2)` 100→90). Regression: 10/10؛ فرق w39 (−3) مفسَّر بالكامل: −2 بالبند المعروف `test-financeservice-tenant-binding-leaks-user1-funds`، و−1 تسريب غير مسجَّل سابقًا في `test_trigger_renewals_endpoint_missing_commit.py` (أُضيف لنص ذلك البند). **وفي نفس الإغلاق:** `saas-invoices-idempotency-key-schema-drift` (الصف الجديد أدناه).

### 16.2 الصف الجديد للانحراف (11.2): بلا تغيير عن §11.2

### 16.3 صف فجوة finance (11.3)، مع إضافة SAWarning

> | — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |

### 16.4 صف onboarding (11.4-ب)، مع الإضافة الإلزامية

> | — | **`tenant-onboarding-admin-always-cross-tenant-saas-unpayable`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§8.2): المسار الوحيد لإنشاء تينانت (`POST /academy/tenants` ← `AcademyService.create_tenant`) يأخذ `admin_id` من جسم الطلب، والتينانت الجديدة لا تحتوي مستخدمين لحظة إنشائها (`users.tenant_id` إلزامي)، فـ`admin_id` **يشير حتمًا** لمستخدم من تينانت أخرى (مثال حي: تينانت 15، `admin_id=48` في تينانت 1)، ولا يوجد أي مسار يعيد تعيينه. ومع تصميم دافع SaaS القائم (`admin_id`)، **فوترة SaaS غير قابلة للدفع لأي تينانت مُنشأة عبر المنتج**: قبل commit `<HASH>` كان الفشل `InsufficientBalanceError`/`PAST_DUE` مضلِّلًا، وبعده أصبح `ValidationError`/`FAILED` صريحًا. يحتاج تصميم onboarding (إنشاء أول أدمن داخل التينانت ذريًا، أو endpoint لإعادة تعيين `admin_id` لعضو داخلي). **⚠️ شرط إلزامي لإغلاق هذا البند مستقبلًا (لا تُسقطه أي جلسة تقرأ الملخص فقط):** بعد تحقق عضوية الأدمن، فشل `process_auto_renewals` بسبب عدم عضوية الأدمن يقع في فرع `except Exception` العام (`saas/service.py`) ← `status="FAILED"`، **والاشتراك يبقى `ACTIVE` ويُعاد المحاولة يوميًا بصمت للأبد، بلا grace period وبلا إشعارات `PAST_DUE`** (`check_past_due_subscriptions` لا تراه). **إصلاح onboarding يجب أن يستعيد دلالة `PAST_DUE` (grace period + إشعارات) لهذه الحالة صراحةً**، ولا يكفي منع حدوثها للتينانتات الجديدة، لأن التينانتات القائمة ذات الأدمن العابر (مثل 15) ستبقى. الاختبار `test_auto_renewal_fails_for_admin_from_another_tenant` يثبّت سلوك `FAILED` الحالي عمدًا، **ويجب تحديثه** مع ذلك الإصلاح. | 🟠 **مفتوح، أولوية عالية قبل الإطلاق** — يمنع أي فوترة SaaS حقيقية لتينانت جديدة | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.2، §13 |

### 16.5 الصف 11.4-أ (الخيار C): بلا تغيير عن §11.4-أ

### 16.6 تعديل مقترح على بند قائم (قاعدة "ابحث في PROGRESS_LOG قبل بند جديد")

**لا صف جديد لتسريب TRIGREN.** بدلًا من ذلك تُضاف جملة إلى نص البند القائم `test-financeservice-tenant-binding-leaks-user1-funds` (`PROGRESS_LOG.md:1059`)، قبل "**الحل المتوقَّع**":

> **[تحديث 2026-09-24، جلسة `saas-sender-id-collision-fix` §14.5]:** نفس التسريب قائم أيضًا في `tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_success_path_no_double_commit_error` (خطة `REGTEST-TRIGREN-PLAN-*`، مفتاح `AUTO-RENEW-{sub_id}-{YYYY-MM}`): −1 على user 1 و+1 على 957 لكل تشغيل، لأن `_cleanup` هناك لا يعكس التحويل. **مؤكَّد:** tx #1047 / audit_log #1029. إجمالي تشغيل الملفين معًا: −3 على user 1. أي حل (أ)/(ب) أدناه يجب أن يغطي الملفين.

---

## 17. الحالة الحالية: ⛔ توقف قبل staging/commit

**الملفات المُعدَّلة في هذه الجلسة:**
- `eppne-backend/app/domains/saas/service.py` (+7 أسطر، §14.1)
- `eppne-backend/tests/test_saas_pay_invoice_sender_id_collision_guard.py` (جديد)
- `.claude/reports/saas-sender-id-collision-fix-session-log.md` (هذا الملف)
- ملفات أدلة جديدة: `saas-sender-id-collision-mutation-evidence.txt`، `saas-sender-id-collision-regression-run.txt`، `saas-sender-id-collision-regression-snapshot-before.txt`، `saas-sender-id-collision-regression-snapshot-after.txt`

**لم يُلمَس:** `PROGRESS_LOG.md`، `insurance/service.py`، `academy/repository.py`، `finance/*`. لا staging ولا commit ولا push.

**مطلوب منك:**
1. الموافقة على الـcommit (الكود + الاختبار + التقارير)، ثم commit docs منفصل لـ`PROGRESS_LOG.md` بنصوص §16 (مع ملء `<HASH>`)، بنفس نمط الجلسات السابقة (`474d3af` + `3ed72c2` + `77c216c`).
2. الموافقة على §16.6 (تعديل البند القائم بدل صف جديد).
3. تنفيذ عكس التسريب في §15.2 أم تركه؟

---

## 18. عكس التسريب (§15.2): ✅ مُنفَّذ بموافقة صريحة

الملف: `.claude/reports/saas-sender-id-collision-leak-reversal.sql`. كل خطوة داخل `DO` تفحص `ROW_COUNT` وتعمل `RAISE EXCEPTION` عند أي عدد غير متوقع، وتحقق ما قبل `COMMIT` مُحرَس بنفس الطريقة.

| المرحلة | w39 | w929 | max_tx | count(tx) | audit_logs 1027-1029 |
|---|---|---|---|---|---|
| قبل | 699.0 | 176.0 | 1047 | 203 | 3 |
| قبل COMMIT (داخل الترانزاكشن) | 702.0 | 173.0 | 1037 | — | — |
| بعد COMMIT | **702.0** | **173.0** | **1037** | **200** | **0** |

rowcounts: 1 / 1 / 3 / 3، كما هو متوقع. **النتيجة: تطابق تام مع لقطة "قبل" الـregression (§14.5).**

---

## 19. الـdiff المعزول لـ`PROGRESS_LOG.md` (docs commit، hunk-only)

مبني على نسخة `HEAD` (بعد `8979eb9`) + إدراجات §16.1-§16.6 فقط، بالـanchors لا بأرقام الأسطر. التعديلات السابقة غير المُلتزَمة في الملف (+670/−1) **خارج** هذا الـcommit. التنظيم: سطر واحد مُعدَّل (§16.6، داخل صف `test-financeservice-tenant-binding-leaks-user1-funds`)، و4 صفوف جديدة بعد `alembic-ini-points-to-stray-container`، وفقرة إغلاق بعد إغلاق `invoicing-invoice-number-...`.

```diff
@@ -1056,7 +1056,7 @@
 | — | **`invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`** [2026-09-23] — اكتُشف حيًا مرتين مستقلتين أثناء التحقق الحي (BEFORE/AFTER) لجلسة `tourism-sports-transfer-bid-hardcoded-agent-id-6`: `InvoicingService._generate_invoice_number` (`invoicing/service.py:115-119`) يولِّد الرقم التالي بصيغة `count_invoices(tenant_id) + 1` — غير آمن عند حذف أي صف فاتورة سابق. لتينانت 1: `count(*)=14` لكن أعلى رقم مُستخدَم فعليًا `INV-1-000015` (صف id=17 لا يزال موجودًا) — أي استدعاء `create_invoice(entity_id=1, ...)` **يفشل دائمًا** بـ`IntegrityError`/`duplicate key` على نفس الرقم بالضبط، **قفل دائم لا عرضي** (مؤكَّد بتكراره حرفيًا مرتين اليوم بمستخدمين/تحويلات مختلفين تمامًا). **مستقل تمامًا عن حجب المراجعة الطبية B-E3** (مؤكَّد: حالة `PlayerTransfer` تُلتزَم بنجاح قبل أي محاولة لإنشاء الفاتورة، وفشل الفاتورة يُعالَج بأمان الآن). صفر لمس كود — توثيق فقط. | 🟡 **مفتوح، أولوية متوسطة — يُفشِل فوترة رسوم الوكالة/أي فاتورة أخرى لتينانت 1 دائمًا، لا يحجب أي مسار حرج آخر** | `.claude/reports/invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key-backlog.md` |
 | — | **`admin-kill-switch-llm-activation-gate-open-items`** [2026-09-22] — *تجميع 11 بندًا من قائمة "LLM activation gate" في تقرير 0-C §6-7، لم تُصلَح:* (B-1) قائمة تحقق قبل أي تفعيل حقيقي لاستدعاء LLM: الـkill switch ✅ (هذه الجلسة)، `POST /api/ai/chat` بلا مصادقة إلزامية (`get_current_user_optional`)، `PUT /api/ai/routing` قابل للتعديل من superuser أي تينانت (نفس نمط ثغرة الصلاحية العالمية التي أُصلحت هنا لمفتاح الإيقاف، لم تُصلَح هناك)، المحرك محاكاة بالكامل بمفاتيح API وهمية، حالة المفتاح غير دائمة (Redis فقط)؛ (B-2) لا تخزين دائم (DB) لحالة المفتاح — `FLUSHALL` على Redis يعيدها "يعمل" بصمت؛ (B-3) 25 حساب `SUPER_ADMIN` في تينانت المنصة قادرون جميعًا على تفعيل/إلغاء المفتاح (الشرط تينانت لا حساب بعينه) — يستحق مراجعة صلاحيات لاحقًا؛ (B-4) حساب `EXECUTIVE_DIRECTOR` الذي يُفترض أن ينشئه `scripts/create_superuser.py` **غير موجود فعليًا في DB** (0 صف)؛ (B-5) استهلاك حصة `AIGovernanceService.check_and_consume` يسبق رفض بوابة الـkill switch في ~14 دومينًا يستدعيها قبل `execute_agent_action` — استدعاء مرفوض يُحتسَب عليه استهلاك حصة فعليًا؛ (B-6) فولباكات AI مُختلَقة أخرى غير مغطاة بالحارس الجديد (نتيجة تصميم متعمَّد للنطاق): `employment` يُخزِّن `50` كدرجة افتراضية، `insurance`/`tenders`/`transport` استشارية بحتة؛ (B-7) بطء ذيلي محتمل للبوابة أثناء انقطاع Redis (إعادة محاولة أسية 3 مرات قبل fail-open)؛ (B-8) `core/ai_engine.py::analyze_and_recommend_courses` كود ميت فعليًا (مستورد في `academy/service.py` ولا يُستدعى من أي مكان)؛ (B-9) `POST /api/ai/chat` **بجسمه الافتراضي يرجع `500` دائمًا** (`task_type` الافتراضي `"arabic_chat"` بحروف صغيرة ≠ enum `ARABIC_CHAT`) — باج مستقل موجود قبل هذه الجلسة، غير مُصلَح؛ (B-10) نافذة سباق نظرية: لو انقلب المفتاح بين بوابتَي `execute_agent_action` والمحرك خلال نفس الطلب يُنشأ صف `ai_task_logs` بنوع `ERROR` صادق قبل رمي الاستثناء (لا رصد فعلي، قرار متعمَّد بعدم إضافة `rollback` تفاديًا لكسر identity-map لدى المستدعين)؛ (B-11) `changed_at` بتوقيت UTC بينما سجلات السيرفر بالتوقيت المحلي — قد يربك مقارنة أحداث التدقيق يدويًا. صفر لمس كود لأي بند. | ⚪ **مرجع فقط — قائمة تحقق مطلوبة قبل أي تفعيل إنتاجي لاستدعاء LLM حقيقي، لا عاجلة اليوم (المحرك محاكاة)** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §6-7 (B-1…B-11) |
 | — | **`admin-kill-switch-regression-suite-side-effects`** [2026-09-22] — *لم تُصلَح، غير خاصة بمنطق الـkill switch نفسه:* أثناء تشغيل مجموعة الانحدار (147 اختبارًا) للتحقق من عدم كسر شيء بعد 0-C، ظهرت 3 آثار جانبية **من الاختبارات القديمة نفسها، ليست من تعديلات هذه الجلسة**: (1) **`admin-kill-switch-realestate-invoice-ordering-guard-stale`** — الفشل الوحيد في المجموعة (`test_realestate_buy_fractional_ownership_invoice_ordering`) حارس بنيوي (`inspect.getsource`) قديم مقابل بنية `buy_fractional_ownership` الحالية (كتلة `try/except` جديدة لاستدعاء AI أُضيفت قبل كتلة الفاتورة في جلسة أخرى غير متعلقة) — لم يُشغَّل الكود الفعلي، `realestate/service.py` لم يُلمَس في 0-C؛ (2) مجموعات الانحدار **تغيّر رصيد محفظتي حسابَي اختبار دائمَين** (`wallets.id=41`/`45`) وتترك **رسائل Celery يتيمة** في طابور `celery` (931 رسالة متراكمة من جلسات سابقة، منها اثنتان من هذه الجلسة أُزيلتا) وكاش Redis لمستخدمين محذوفين — لا baseline على مستوى الصفوف لهذين الحسابين لتمكين استعادة دقيقة مستقبلًا؛ (3) توصية منهجية: أي لقطة zero-diff مستقبلية يجب أن تحفظ صفوف `wallets`/`users` الحساسة كاملة، لا فقط md5/عدد الصفوف. **قرار المالك [2026-09-22]:** أرصدة `wallets` 41/45 تُترَك كما هي — لا استعادة (جدول `transactions` لم يتغيّر، فلا فقد محاسبي حقيقي؛ أي استعادة الآن تخمين غير مسجَّل). | 🟡 **مفتوح، أولوية متوسطة — منهجي، يخص كل مجموعات الانحدار الحية لا 0-C تحديدًا** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §الجزء الرابع (B-12، B-13، B-14) |
-| — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا. **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |
+| — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا. **[تحديث 2026-09-24، جلسة `saas-sender-id-collision-fix` §14.5]:** نفس التسريب قائم أيضًا في `tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_success_path_no_double_commit_error` (خطة `REGTEST-TRIGREN-PLAN-*`، مفتاح `AUTO-RENEW-{sub_id}-{YYYY-MM}`): −1 على user 1 و+1 على 957 لكل تشغيل، لأن `_cleanup` هناك لا يعكس التحويل. **مؤكَّد:** tx #1047 / audit_log #1029. إجمالي تشغيل الملفين معًا: −3 على user 1. أي حل (أ)/(ب) أدناه يجب أن يغطي الملفين. **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |
 | — | **`insurance-review-claim-negative-approved-amount-reverses-transfer`** [2026-09-23] — *ملاحظة بالقراءة الثابتة أثناء جلسة `insurance-review-claim-double-payment-verification`، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* `PUT /insurance/claims/{id}/review` يقبل `approved_amount` **سالبًا**: (1) `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`؛ (2) `insurance/service.py` (`final_amount = approved_amount or claimed`، سطر 524 بعد الإصلاح) — الـcap على الحد الأعلى فقط (`> max_coverage_limit`)؛ (3) **`FinanceService.transfer` (`finance/service.py:90-113`) لا يفحص `amount > 0`**: مع `amount=-50` فحص الرصيد `sender_current < -50` خطأ دائمًا → يمر، ثم رصيد المُرسِل (المراجِع) **يزيد** 50 ورصيد المستلم (المطالِب) **ينقص** 50 — وقد يصبح سالبًا (لا فحص على المستلم) — ثم `status=PAID` و`approved_amount_mrusdt=-50` وفاتورة بمبلغ سالب. **شرط الهجوم:** OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة — أي مُصدِر تأمين خبيث يسحب من مشتركيه بـ"مراجعة" مطالباتهم. **إصلاح `review_claim` [2026-09-23] لا يغلقه** (مطالبة `SUBMITTED` تقبل مراجعة أولى بمبلغ سالب). **نطاق أوسع:** `FinanceService.transfer` مشترك بين كل الدومينات — أي مستدعٍ يمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّض لنفس الانعكاس؛ و`hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا. **نقطة البداية للجلسة المخصصة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`)؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس مركزي في `transfer` (`amount <= 0 → ValidationError`) + `gt=0` في الـrouter. **ملاحظة جانبية:** `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`or`) فيُدفع المبلغ المطالَب به كاملًا. | 🔴 **غير مُتحقَّق منه — أولوية عالية (احتمال سرقة أموال)**؛ جلسة مخصصة ضيقة (قرار المستخدم 2026-09-23) | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §6، §11 |
 | — | **`social-physical-gift-product-price-no-positive-constraint`** [2026-09-23] — اكتُشف في جلسة `insurance-negative-approved-amount-verification` (§3/§ب، الصف 24): `social/schemas.py:169` `product_price_mrusdt` بلا `gt=0` ولا حارس في `request_physical_gift` (`social/service.py:590`). منذ `58b30af` المبلغ غير الموجب يُرفض مركزيًا في `FinanceService` (422) — المتبقي دفاع إضافي على مستوى الـschema فقط. أولوية منخفضة. |
 | — | **`projects-contribution-amount-no-positive-constraint`** [2026-09-23] — نفس الجلسة (الصف 16): `projects/schemas.py:69` `amount_mrusdt` (Optional) بلا `gt=0`؛ المساهمة النقدية تمرره مباشرة لـ`finance.transfer` (`projects/service.py:185`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
@@ -1072,11 +1072,17 @@
 | — | **`ai-agents-test-noop-create-invoice-workaround-removable`** [2026-09-24] — نفس الجلسة (§2.4): `tests/test_ai_agents_execute_action.py:344` (`_noop_create_invoice_for_isolation`) يتجاوز `create_invoice` بـmonkeypatch **بسبب** تصادم ترقيم الفواتير تحديدًا (commit `b4bf356`). بعد إغلاق الترقيم (commit `474d3af`) لم يعد التجاوز ضروريًا لهذا السبب — إزالته تجعل الاختبار يمرّن مسار الفاتورة الحقيقي. **تحفّظ:** قد يظل مطلوبًا جزئيًا بسبب `invoicing-missing-rollback-on-exception-11b` (`:135`) إن فشلت الفاتورة لسبب آخر — يُتحقق عند الإزالة. جلسة منفصلة بموافقة (قرار مستخدم: لا تُزال في جلسة الإصلاح). | 🟢 منخفض | `tests/test_ai_agents_execute_action.py` |
 | — | **`invoicing-count-invoices-now-unused`** [2026-09-24] — نفس الجلسة: `InvoicingRepository.count_invoices` (`invoicing/repository.py:117`) بلا أي مستدعٍ بعد استبدال `_generate_invoice_number` بـ`next_invoice_seq` (المستدعي الوحيد كان هو). أُبقي عمدًا (صفر حذف خارج النطاق). | 🟢 منخفض جدًا | `eppne-backend/app/domains/invoicing/repository.py` |
 | — | **`alembic-ini-points-to-stray-container`** [2026-09-24] — نفس الجلسة (§3.1): `alembic.ini:70` `sqlalchemy.url` يشير لـ`127.0.0.1:5433` (حاوية `postgres-eppne` اليتيمة، كلمة سر قديمة) لا للقاعدة الحقيقية `eppne_db:5435`. غير مؤثر حاليًا لأن `migrations/env.py:74` يتجاوزه بـ`DATABASE_URL` من `.env` (مؤكَّد من سطر الاتصال: `...@127.0.0.1:5435/eppne_v2`)، لكنه فخ: لو `.env`/`DATABASE_URL` لم يُحمَّل، الـmigrations تُطبَّق بصمت على الحاوية الخطأ. الحل: تصحيح/حذف القيمة في `alembic.ini`، ويُحسم مع قرار الحاوية اليتيمة نفسها. | 🟡 منخفض-متوسط | `eppne-backend/alembic.ini` |
+| — | **`saas-invoices-idempotency-key-schema-drift`** [2026-08-24، صف مُنشأ بأثر رجعي 2026-09-24] — ذُكر فقط داخل نص `saas-pay-invoice-sender-id-user-id-collision` ولم يُمنح صفًا خاصًا به قط: `Invoice.idempotency_key` (`saas/models.py:161`) مُعرَّف في الموديل ومفقود من جدول `saas_invoices` الحي منذ أول migration أنشأته، فكان أي SELECT/INSERT على `Invoice` يفشل بـ`UndefinedColumnError`، ما حجب `pay_invoice` و`process_auto_renewals` (عبر `_generate_invoice`) بالكامل. **أُصلح في commit `8fccfa1` (2026-08-25)**، migration `036_add_idempotency_key_to_saas_invoices` (عمود + فهرس unique جزئي `WHERE idempotency_key IS NOT NULL`)، ومُتحقَّق منه حيًا في 2026-09-24 (`\d saas_invoices` + alembic head `068`). **فجوة توثيق، لا باج حي.** | ✅ **مُغلَق** (`8fccfa1`) | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §2 |
+| — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |
+| — | **`tenant-onboarding-admin-always-cross-tenant-saas-unpayable`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§8.2): المسار الوحيد لإنشاء تينانت (`POST /academy/tenants` ← `AcademyService.create_tenant`) يأخذ `admin_id` من جسم الطلب، والتينانت الجديدة لا تحتوي مستخدمين لحظة إنشائها (`users.tenant_id` إلزامي)، فـ`admin_id` **يشير حتمًا** لمستخدم من تينانت أخرى (مثال حي: تينانت 15، `admin_id=48` في تينانت 1)، ولا يوجد أي مسار يعيد تعيينه. ومع تصميم دافع SaaS القائم (`admin_id`)، **فوترة SaaS غير قابلة للدفع لأي تينانت مُنشأة عبر المنتج**: قبل commit `8979eb9` كان الفشل `InsufficientBalanceError`/`PAST_DUE` مضلِّلًا، وبعده أصبح `ValidationError`/`FAILED` صريحًا. يحتاج تصميم onboarding (إنشاء أول أدمن داخل التينانت ذريًا، أو endpoint لإعادة تعيين `admin_id` لعضو داخلي). **⚠️ شرط إلزامي لإغلاق هذا البند مستقبلًا (لا تُسقطه أي جلسة تقرأ الملخص فقط):** بعد تحقق عضوية الأدمن، فشل `process_auto_renewals` بسبب عدم عضوية الأدمن يقع في فرع `except Exception` العام (`saas/service.py`) ← `status="FAILED"`، **والاشتراك يبقى `ACTIVE` ويُعاد المحاولة يوميًا بصمت للأبد، بلا grace period وبلا إشعارات `PAST_DUE`** (`check_past_due_subscriptions` لا تراه). **إصلاح onboarding يجب أن يستعيد دلالة `PAST_DUE` (grace period + إشعارات) لهذه الحالة صراحةً**، ولا يكفي منع حدوثها للتينانتات الجديدة، لأن التينانتات القائمة ذات الأدمن العابر (مثل 15) ستبقى. الاختبار `test_auto_renewal_fails_for_admin_from_another_tenant` يثبّت سلوك `FAILED` الحالي عمدًا، **ويجب تحديثه** مع ذلك الإصلاح. | 🟠 **مفتوح، أولوية عالية قبل الإطلاق** — يمنع أي فوترة SaaS حقيقية لتينانت جديدة | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.2، §13 |
+| — | **`saas-tenant-treasury-account-separation-design`** [2026-09-24] — بند تصميم مؤجَّل (لا جلسة تصميم بعد، بقرار صريح): التصميم A القائم يجعل فواتير/تجديدات SaaS تُخصم من **المحفظة الشخصية** لـ`AcademyTenant.admin_id`. الخيار C (محفظة خزانة للتينانت مستقلة عن أي شخص) يفصل أموال التينانت عن أموال الأدمن، لكنه يتطلب مفهوم حساب ثانٍ لكل تينانت (الحالي حساب نظام واحد هو **المستقبِل**) وآلية تمويل. يُفتح فقط إن قرر المنتج هذا الفصل قبل الإطلاق الأوسع. | ⏸️ **مؤجَّل — قرار منتجي** | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §4.2 |
 
 **✅ إغلاق مؤرَّخ [2026-09-23] — `insurance-review-claim-negative-approved-amount-reverses-transfer`: مُغلَق (commit `58b30af`)، مع تصحيح تصنيف الخطورة.** جلسة `insurance-negative-approved-amount-verification` (تقرير: `.claude/reports/insurance-negative-approved-amount-verification-session-log.md`). **التصحيح:** الملاحظة الأصلية ("مُصدِر خبيث يسرق أموال المُطالِبين بمبلغ سالب") **بُنيت على قراءة ناقصة** — فاتها قيود DB: `transactions.check_transaction_amount_positive` (`CHECK (amount > 0)`، migration `71820e4fe1f3...:2034`) و`wallets.check_wallet_balances_non_negative` / `check_wallet_held_balances_non_negative`. كل دوال `FinanceService` الأربع تُحدِّث المحافظ وتُدرج صف `Transaction` داخل نفس `begin_nested()` بلا commit داخلي → أي مبلغ `<= 0` يُلغى بالكامل. **BEFORE (حي، تينانت throwaway 144، كود غير مُصلَح):** B1–B7 — `review_claim(-50)` (بمُطالِب رصيده 0 ثم 100)، HTTP (`-50`)، و`transfer`/`hold_funds`/`release_held_funds`/`settle_held_funds(-10)` مباشرة — **كلها `IntegrityError` بصافي تغيير صفر** (لا حركة أموال)، لكن العميل يتلقى **HTTP 500**؛ B6/B7 أثبتا أن قيد `transactions` هو **الحاجز الوحيد** لـrelease/settle (قيود المحفظة مرّت)؛ B8 — `approved_amount=0` **دفع كامل المطالبة (20)**. **الخطورة الفعلية:** hardening + تصحيح كود خطأ (منخفضة–متوسطة)، **ليست سرقة**. **الإصلاح (2 ملف، +15/−5):** حارس `amount <= 0 → ValidationError (422)` في أول الدوال الأربع قبل أي SQL (`finance/service.py`)؛ `approved_amount: Query(None, gt=0)` (`insurance/router.py:225`). **AFTER (تينانت 145):** 15/15 — الدوال الأربع ترفض `-10` و`0` بـ**صفر عبارات SQL** (مستمع `before_cursor_execute`)؛ HTTP `-50`/`0` → 422؛ التدفقات الموجبة (موافقة 50 عبر HTTP، hold→release→hold→settle) سليمة؛ الموافقة بـ0 عبر الخدمة مباشرة لا تزال تدفع كاملًا (backlog `review-claim-zero-amount-falls-back-to-claimed`). **اختبار دائم:** `tests/test_finance_non_positive_amount_guard.py` — 10/10 على الإصلاح، 10/10 FAIL على HEAD (mutation check). **Regression:** 26/26 (insurance status guard، FINBIND، tenders hold/release/settle، 4 مجموعات transport). **تنظيف:** التينانتان 144 (17 صفًا) و145 (29 صفًا) حُذفا بالكامل، صفر متبقٍ. **مواقع الاستدعاء:** 40 موقعًا لـ`transfer`/`hold`/`release`/`settle` صُنِّفت (7 A، 10 B، 23 S) — الحارس المركزي يغطيها كلها؛ قيود الـschema لمواقع A/B → 10 بنود backlog أعلاه (توثيق فقط، بقرار المستخدم).
 
 **✅ إغلاق مؤرَّخ [2026-09-24] — `invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`: مُغلَق (commit `474d3af`)، ويُغلِق معه نفس الخطأ المُتتبَّع تحت أسماء أقدم: `invoicing-generate-invoice-number-count-based-collision` (`[2026-08-18]` و`[2026-08-29]` أعلاه) والشق (أ) من `invoicing-create-invoice-numbering-collision` (`[2026-09-01]` أدناه — الشق (ب) الخاص بـrollback بعد استثناء DB يبقى مفتوحًا، وكذلك `invoicing-missing-rollback-on-exception-11b`).** جلسة `invoicing-invoice-number-sequence-fix` (`.claude/reports/invoicing-invoice-number-sequence-fix-session-log.md`). **الحالة الحية قبل الإصلاح:** ليس tenant 1 وحده — **tenant 16 مقفول أيضًا** (count=3، `INV-16-000004` موجود؛ فجوة عند 3)، أي 100% من التينانتات التي لها فواتير (2/2؛ tenant 15 بلا فواتير). مصدر الحذف: تنظيف الاختبارات (`delete(Invoice)` في 5 ملفات)، لا كود التطبيق. **الإصلاح (الخيار C بقرار المستخدم، من بين MAX+1 / MAX+advisory lock / SEQUENCE عالمي / جدول عداد):** migration `068_invoice_number_counters` — جدول `invoice_number_counters(tenant_id PK → academy_tenants ON DELETE CASCADE, last_seq)` مع seed من أعلى seq فعلي لكل تينانت → `(1,15), (16,4)`؛ `InvoicingRepository.next_invoice_seq` بـ`INSERT ... ON CONFLICT DO UPDATE SET last_seq = GREATEST(last_seq + 1, MAX(seq) + 1) RETURNING` — قفل صف يسلسل التزامن، لا يعيد رقمًا محذوفًا أبدًا، transactional (rollback يسترجع الرقم)، و`GREATEST` يغطي تينانت له فواتير بلا صف عداد؛ `models.InvoiceNumberCounter` لتطابق الـmetadata. **downgrade 068 يجب أن يقترن دائمًا بـrevert للكود** (موثَّق داخل ملف الـmigration). **التحقق:** `alembic current` = 067 (رأس واحد) قبل كتابة 068؛ جولة upgrade → downgrade → upgrade نظيفة والـseed متطابق مرتين؛ اختبار جديد `tests/test_invoicing_invoice_number_counter.py` — قبل الإصلاح 5 فشل/1 نجاح (التزامن: 9/10 استدعاءات فشلت بـduplicate key)، بعده **6/6**، وmutation check (إرجاع `count+1` مؤقتًا) أعاد نفس الـ5 فشل بالضبط؛ التحقق على tenant 1 و16 read-only داخل rollback (صفر insert حقيقي، العداد لم يتحرك). **Regression** (7 ملفات، مقارنة بخط أساس على الكود غير المُعدَّل): **25 passed, 2 failed, 1 xfailed — مطابق حرفيًا لخط الأساس**؛ الفشلان (`test_tourism_sports_place_transfer_bid_invoice_ordering`، `test_realestate_buy_fractional_ownership_invoice_ordering`) هما بالضبط حالتا `test-savepoint-fragile-source-position-parsing` (`[2026-09-17]` + "حالة ثانية" `[2026-09-23]`) — **تأكيد مستقل إضافي** أنهما مسبقان وغير مرتبطين بهذا الإصلاح، لا بند جديد. **بعد الإصلاح:** الرقم التالي `INV-1-000016` و`INV-16-000005` (غير موجودين) — التينانتان لم يعودا مقفولين. **الـstaging:** `service.py` كان يحمل hunk قديمًا غير مرتبط (`process_overdue_invoices`، ~295) — hunk-split بـ`git apply --cached`، الـcommit يضم 5 ملفات بالضبط، `router.py` مستبعد. `count_invoices` أُبقي بلا مستدعين (backlog). 4 بنود backlog جديدة أعلاه (`invoices-invoice-number-duplicate-unique-index`، `ai-agents-test-noop-create-invoice-workaround-removable`، `invoicing-count-invoices-now-unused`، `alembic-ini-points-to-stray-container`).
 
+**✅ إغلاق مؤرَّخ [2026-09-24] — `saas-pay-invoice-sender-id-user-id-collision` (الصف `[2026-08-24]` أعلاه): مُغلَق (commit `0ba7204`، 2026-08-25) — فجوة توثيق، لا باج حي.** جلسة `saas-sender-id-collision-fix` (`.claude/reports/saas-sender-id-collision-fix-session-log.md`). التصادم كان مُصلَحًا **قبل بدء هذه الجلسة بشهر**: `0ba7204` استبدل `sender_id=self.tenant_id` بـ`sender_id=AcademyTenant.admin_id` (`SaaSControlService._get_tenant_admin_id`) و`receiver_email="system@eppne.com"` بحساب نظام التينانت (`get_or_create_system_account`) في `pay_invoice` و`process_auto_renewals`، لكن هذا الصف لم يُغلَق أبدًا. **دليل حي:** 164 تحويلًا `PAY-INV-*`/`AUTO-RENEW-*` كلها `sender_id=1` (أدمن تينانت 1) إلى `957` (`__system_tenant_1__`)، وصفر تحويلات مشتقة من `tenant_id`. **التصميم A مؤكَّد صراحةً كتصميم قائم** (البديل B "المستخدم المنادي" مرفوض لعدم وجود مستخدم في Celery؛ C مؤجَّل: `saas-tenant-treasury-account-separation-design`). **مُضاف في نفس الجلسة (commit `8979eb9`):** تحقق عضوية الأدمن في `_get_tenant_admin_id` (`ValidationError` إن لم يكن `admin_id` عضوًا في التينانت، ويسبق `get_or_create_system_account`)، واختبار دائم `tests/test_saas_pay_invoice_sender_id_collision_guard.py` (4/4) يثبت سيناريو `user.id == tenant.id` حرفيًا لـ`pay_invoice` و`process_auto_renewals`. **Mutation:** حذف الفحص يُفشل الاختبارين 3 و4، وأثبت حيًا الخصم من محفظة ممولة لغير عضو (`(A, T2)` 100→90). Regression: 10/10؛ فرق w39 (−3) مفسَّر بالكامل: −2 بالبند المعروف `test-financeservice-tenant-binding-leaks-user1-funds`، و−1 تسريب غير مسجَّل سابقًا في `test_trigger_renewals_endpoint_missing_commit.py` (أُضيف لنص ذلك البند). **وفي نفس الإغلاق:** `saas-invoices-idempotency-key-schema-drift` (الصف الجديد أدناه).
+
 ---
 
 ## [2026-09-01] درس عام — انتهاك تحذير Backlog موثَّق صراحة أثناء "إصلاح نمطي" لاحق
```
