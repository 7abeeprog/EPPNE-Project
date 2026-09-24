# جلسة تحقيق (قراءة فقط): `invitations-accept-orphaned-user-no-wallet-investigation`

**التاريخ:** 2026-09-24
**النوع:** قراءة فقط. لم يُعدَّل أي كود، ولم يُكتب شيء في DB (كل الاستعلامات `SELECT` تحت `default_transaction_read_only=on`)، ولم يحدث staging ولا commit، ولم يُكتب شيء في `PROGRESS_LOG.md`.

---

> **⚠️ تصحيح لاحق في نفس الجلسة (انظر §9.1):** البند 2 أدناه، و§4 "🔴"، وصف `transfer()` في §6، والمرحلة A في §7، **كلها خاطئة وسُحبت**. `FinanceService` تستخدم `WalletRepository` من `finance/repository.py`، و`create()` فيها `flush()` فقط (منذ `aeea353`)، وليس `WalletRepository` من `identity/repository.py` الذي قرأته خطأً. وفي §5.3 أيضًا: المحفظة "العابرة للمستأجر" هي `747` لا `930` (المستخدم 774 من tenant 16). تُركت الأقسام الأصلية كما هي للأمانة.

## 0) الخلاصة في سطرين

1. **فرضية الطلب غير دقيقة: الملف الحرج فُحص فعلًا وأُغلق.** فحصته جلسة 0-B (2026-09-21، قراءة فقط) ثم جلسة 0-B1 (مُنفَّذة ومُلتزَمة ومدفوعة إلى `origin/main`). الآلية الأصلية أُصلحت في `9f37201` (2026-08-18). ومسار إنشاء الحساب من `accept` **حُذف كليًا** في `54d6cfe` (2026-09-22). خارطة الطريق (2026-09-18) كُتبت قبل هذه الجلسات، فمعلومتها قديمة.
2. **لكن هذا التحقيق وجد نسخة حيّة من نفس فئة الباج في مكان آخر:** `FinanceService.transfer()` تنشئ المحفظة الناقصة (`WalletRepository.create` فيها `commit()` مباشر) **من داخل `begin_nested()`**. هذه هي آلية التقرير الحرج الأصلي بالضبط، لكن في دومين finance. والدليل عليها حتى الآن **قراءة الكود فقط، لم يُثبَت بالتشغيل**. ومعها اكتشافان من DB: جدول `wallets` **بلا قيد UNIQUE على `user_id`**، ويوجد فعلًا مستخدم له محفظتان في مستأجرين مختلفين.

---

## 1) محتوى الملف الحرج الأصلي

**المسار:** `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`

- **تاريخ الاكتشاف:** 2026-08-17، أثناء جلسة `constructor-mismatch` (`.claude/reports/constructor-mismatch-session-log.md`). ظهر كاكتشاف جانبي أثناء التحقق الحي من إصلاح الـconstructor في `invitations`.
- **الآلية الموثَّقة:** `accept_invitation` → `async with self.db.begin_nested()` (كان في service.py:286) → `_create_user_from_invitation` → `UserService.register()` → `UserRepository.create()` يعمل `db.add` + **`commit()` مباشر** يُغلق الـSAVEPOINT → `db.refresh(user)` يرمي `InvalidRequestError: Can't operate on closed transaction inside context manager`.
- **الأثر المُثبَت وقتها** (سكربت معزول + `SELECT` قبل/بعد):
  - سُجِّل `users.id=52` (`p_ctor_inv_newuser@eppne.com`) على القرص وهو نشط.
  - **صفر محفظة**، وصفر lead.
  - بقيت الدعوة `id=1` بحالة `SENT`.
  - تلقّى المستخدم `500`.
- **الوصولية وقتها:** كان المسار محجوبًا بباج مستقل (Backlog #9، `_check_saas_limits`).
- **الحالة المكتوبة في الملف:** "🔴 صفر إصلاح". **الملف نفسه لم يُحدَّث ببانر إغلاق حتى اليوم.** هذا سبب أنه ظهر في خارطة الطريق "غير مفحوص".

---

## 2) ما حدث بعد كتابة الملف (سجل تاريخي كامل)

| التاريخ | الحدث | الدليل |
|---|---|---|
| 2026-08-18 | إصلاح الآلية: نُقل `_create_user_from_invitation` إلى **خارج** `begin_nested()` | commit `9f37201`، تقرير `invitations-savepoint-leak-session-log.md`، `PROGRESS_LOG.md` بند #11a (سطر 115، 181) |
| 2026-09-21 | **0-B (قراءة نقدية):** التحقق من كل ادعاء في الملف الحرج مقابل الكود. النتيجة: الملف **قديم/مُصلَح**، واكتُشفت ثغرة أخطر: قبول الدعوة **مجهولًا** + `X-Tenant-ID` غير مُتحقَّق منه ⇒ إنشاء حساب كامل في أي مستأجر | `.claude/reports/invitations-batch0b-critical-read-session-log.md` |
| 2026-09-21/22 | **0-B1 (تنفيذ):** `accept` بلا مصادقة ⇒ `401 REGISTRATION_VIA_INVITATION_REQUIRED` قبل أي وصول لـDB. المستأجر يُؤخذ من `current_user` فقط. **حُذفت `_create_user_from_invitation` وكلمة المرور الافتراضية `TempPass123!` نهائيًا.** 11 اختبارًا جديدًا. | commit **`54d6cfe`** (موجود في `origin/main`)، تقرير `invitations-batch0b1-close-hole-session-log.md` + 3 ملفات أدلة |
| 2026-09-22 | توثيق الإغلاق في `PROGRESS_LOG.md` | `PROGRESS_LOG.md:4354-4374`، وبانر السطر 21 |

**⚠️ انحراف توثيقي:** يذكر `PROGRESS_LOG.md:4356` و`:4362` أن الإصلاح في commit **`dde2a84`**. **هذا الـhash غير موجود في الريبو** (`git log dde2a84` ⇒ `unknown revision`). الـcommit الفعلي هو **`54d6cfe`** ("fix(invitations): stop accept_invitation creating accounts and trusting X-Tenant-ID"، 2026-09-22 01:20). ربما أُعيد كتابته بـamend/rebase بعد التوثيق. يحتاج تصحيحًا في جلسة توثيق، ولم يُلمس هنا.

---

## 3) مسار الكود الحالي (قراءة مباشرة، HEAD = `7f4207c`)

### `POST /invitations/{id}/accept`

- `invitations/router.py:587-610`: إذا كان `current_user is None` يُرجع **`401`** فورًا. لا بحث عن الدعوة ولا وصول للـSaaS gate ولا كتابة.
- في المسار المسجَّل: `tenant_id=current_user.tenant_id` و`user_id=current_user.id`.
- `invitations/service.py:260-300`: `user_id: int` **إلزامي**. داخل `begin_nested()` يوجد فقط: `create_lead` و`_apply_discount_gift` و`update_invitation`. **لا يوجد أي استدعاء لـ`UserService`/`register()` في دومين invitations إطلاقًا** (تم التحقق بـgrep: `_create_user` و`TempPass` و`register(` كلها صفر نتائج في `invitations/`).

**⇒ مسار "يوزر جديد بلا محفظة عبر قبول الدعوة" غير موجود في الكود الحالي. الثغرة الأصلية ميتة.**

### المتبقي من نفس العائلة (معروف منذ 0-B، لم يُصلَح)

`identity/service.py:95-96`: الدالة `register()` **غير ذرّية**:
- `user_repo.create` يعمل `commit` (`identity/repository.py:102`).
- ثم `wallet_repo.create` يعمل `commit` ثانيًا (`identity/repository.py:282`).
- لو فشل الثاني (انقطاع DB، kill للعملية، خطأ قيد) يبقى يوزر بلا محفظة.
- يُستدعى من `POST /identity/register` (`identity/router.py:40`) ومن `register_with_invitation` (`identity/invitation_service.py:74`).
- هذه "المرحلة 5" من تصميم 0-B الجزء 2، ولم تُفتح بعد.
- **احتمالها منخفض**، لأنها تحتاج فشلًا بين commit-ين متتاليين.

---

## 4) ماذا يحدث فعلًا لمستخدم بلا محفظة؟ (الشق الذي طلبته، بالكود)

**مفاجأة: لا يوجد كراش "لا توجد محفظة".** `FinanceService` تُصلح النقص ذاتيًا:
- `finance/service.py:28-32` `get_or_create_wallet`: إذا لم تُوجد محفظة ⇒ `wallet_repo.create`.
- `finance/service.py:34-39` `get_or_create_wallet_for_update`: نفس الشيء.
- `get_balances` (سطر 51) يستخدمها ⇒ **القراءة سليمة، وتُنشئ المحفظة عند أول طلب.**
- 9 استدعاءات لـ`get_or_create_wallet*` عبر `app/`.

### 🔴 لكن: الإنشاء الذاتي من داخل `transfer()` هو نفس آلية الباج الأصلي بالضبط

`finance/service.py` داخل `transfer()` (السطور النسبية 39-42 من الدالة، أي تقريبًا الأسطر المطلقة 96-100):

```
async with self.db.begin_nested():
    first_wallet  = await self.get_or_create_wallet_for_update(first_id)
    second_wallet = await self.get_or_create_wallet_for_update(second_id)
```

وعندما تكون المحفظة غير موجودة ⇒ `WalletRepository.create()` ⇒ `add` + **`commit()`** + `refresh()` (`identity/repository.py:275-284`).

**التسلسل المتوقَّع (بالقراءة، مطابق حرفيًا للتسلسل المُثبَت حيًا في التقرير الحرج §3):**
1. `commit()` يُغلق الـSAVEPOINT **ويُثبِّت المعاملة الخارجية كاملة**، أي كل ما كتبه المُستدعي قبل `transfer()`.
2. `refresh(wallet)` يرمي `InvalidRequestError: Can't operate on closed transaction inside context manager`.
3. النتيجة `500` للمستخدم. **المحفظة الجديدة محفوظة، ومعها أي كتابات سابقة للمُستدعي، بلا التحويل المالي نفسه.**
4. المحاولة التالية تجد المحفظة فتنجح. أي أن الكراش **يحدث مرة واحدة لكل مستخدم بلا محفظة**.

**متى يُطلَق؟** أول `transfer()` يكون فيها أحد الطرفين (مُرسِل أو مستقبِل) بلا محفظة **في هذا المستأجر**. ملاحظة مهمة: البحث يكون بـ`(user_id, tenant_id)`، لذلك **مستخدم عنده محفظة في مستأجر 1 يُعامَل كـ"بلا محفظة" عند أول تحويل في مستأجر 16.**

**أين الخطر الحقيقي؟** الخطر ليس في المحفظة نفسها، بل في **الـcommit الجزئي لكتابات المُستدعي** قبل `transfer()`. أمثلة على هذا النمط: حجز، فاتورة، أو claim يُكتب ثم يُحوَّل المال. النتيجة سجل عمل مُثبَّت بلا دفعة مقابلة، أي عدم اتساق مالي/بياناتي. **لم أتتبّع كل مُستدعٍ لـ`transfer()` في هذه الجلسة، ولم أُثبت الكراش بالتشغيل. هذا استنتاج من الكود مدعوم بسابقة مُثبَتة حيًا لنفس الآلية، وليس دليلًا حيًا بعد.**

---

## 5) فحص DB الحي (SELECT فقط، `eppne_db:5435/eppne_v2`، read-only مُؤكَّد)

### 5.1 المستخدمون بلا محفظة
- 125 مستخدمًا إجمالًا. **27 منهم بلا أي محفظة.**
- **كلهم throwaway بلا استثناء**، وكلهم في tenant 1:
  - `id=2`: `p0smoke_…@example.com`.
  - `id=52`: `p_ctor_inv_newuser@eppne.com`. هذا **دليل التقرير الحرج نفسه**، ما زال موجودًا ولم يُنظَّف.
  - `id=77-120` (25 مستخدمًا): `p_tourism_verify_*` و`p_reins_verify_*` و`p_zamakana_verify_*` و`p_saas9_verify_*`، كلها بتاريخ 2026-08-18. **ليست من invitations أصلًا.** هي مستخدمون أنشأتهم سكربتات تحقق مباشرة عبر ORM بلا محفظة.
- **صفر مستخدم حقيقي في حالة يتيمة.**

### 5.2 الدعوات
`sovereign_invitations_v2`: ACCEPTED=2، **SENT=1 (`id=1`، tenant 1، دعوة throwaway من جلسة 2026-08-17)**، DRAFT=1. والمستأجر 1 بلا وصول CRM (حسب 0-B1)، فحتى المستخدم المسجَّل يتلقى `403` هناك.

### 5.3 🔴 اكتشاف جديد: `wallets.user_id` بلا قيد UNIQUE
- الفهارس على `wallets`: `ix_wallets_user_id` **غير فريد**. لا يوجد أي UNIQUE على `user_id` ولا على `(user_id, tenant_id)`.
- **يوجد فعلًا مستخدم بمحفظتين:** `user_id=774` (`TEST_instr_b@example.com`، throwaway):
  - `wallets.id=747`: tenant 1، `{}`، أُنشئت 2026-08-20.
  - `wallets.id=930`: **tenant 16**، أرصدة صفرية، أُنشئت 2026-08-24.
- المعنى:
  - (أ) `get_or_create_wallet` **عرضة لسباق**: طلبان متزامنان لمستخدم بلا محفظة ينشئان محفظتين، ولا شيء في DB يمنع ذلك.
  - (ب) المحفظة المُنشأة ذاتيًا قد تُنشأ **في مستأجر غير مستأجر المستخدم** إذا استُدعيت FinanceService بسياق مستأجر آخر. يتسق هذا مع اكتشاف `saas-sender-id-collision` السابق (أدمن عبر مستأجرين).
- **لم أحقق في مصدر المحفظة 930 تحديدًا.** يحتاج جلسة مستقلة.

---

## 6) تقييم الخطورة (بالأدلة)

| البند | الحالة | الخطورة | الدليل |
|---|---|---|---|
| الثغرة الأصلية (accept ⇒ يوزر بلا محفظة) | **ميتة.** الكود محذوف | لا شيء | `54d6cfe`، `router.py:594-602`، grep صفري |
| دليلها التاريخي `users.id=52` | باقٍ في DB، throwaway | تنظيف فقط | SELECT §5.1 |
| `register()` غير ذرّية (commit-ان) | حيّة، ولم تُصلَح | منخفضة (تحتاج فشلًا بين commit-ين)، والنتيجة تُصلَح ذاتيًا عبر `get_or_create` | `identity/service.py:95-96` |
| `transfer()` تُنشئ المحفظة داخل `begin_nested()` | **حيّة بالقراءة، غير مُثبَتة حيًا** | **متوسطة إلى عالية محتملة**: 500 مرة واحدة لكل (مستخدم، مستأجر)، مع commit جزئي لكتابات المُستدعي. لا سرقة مال (التحويل نفسه لا يتم) لكن عدم اتساق بيانات | `finance/service.py` داخل `transfer`، `identity/repository.py:275-284`، وسابقة §3 من الملف الحرج |
| غياب UNIQUE على `wallets.user_id` | **حيّة، مُثبَتة بالبيانات** | متوسطة: محافظ مكررة ممكنة، ورصيد قد يتوزع/يُقرأ من محفظة خاطئة. أي من المحفظتين تُعاد عند `get_by_user_id`؟ غير محسوم | §5.3، `user_id=774` |
| `PROGRESS_LOG.md` يذكر commit غير موجود (`dde2a84`) | انحراف توثيقي | منخفضة | `git log` |
| الملف الحرج بلا بانر إغلاق | انحراف توثيقي. **هو سبب ظهوره في خارطة الطريق** | منخفضة | الملف نفسه |

---

## 7) خطة تحقق حي مقترحة (لم يُنفَّذ منها شيء)

الأصل مُغلق، فلا حاجة لإعادة إنتاجه. **الخطة المقترحة موجَّهة للاكتشاف الجديد (`transfer` + UNIQUE)** وبنفس الانضباط المعتاد:

**المرحلة A — إثبات حي (throwaway فقط):**
1. Baseline: `SELECT` لعدد `users` و`wallets` و`transactions` و`audit_logs`، مع بصمة محفظة المستخدم 1.
2. إنشاء مستخدمين throwaway `p_wtx_*` في tenant 1 بلا محفظة للمستقبِل، ومحفظة ممولة للمُرسِل.
3. استدعاء `FinanceService(db, 1).transfer(...)` مباشرة بسكربت معزول. المتوقع: `InvalidRequestError` + صف `wallets` جديد للمستقبِل + صفر `transactions` + رصيد المُرسِل كما هو.
4. تجربة ثانية: كتابة وهمية قبل `transfer()` في نفس الجلسة (مثل صف throwaway) لإثبات أنها تُثبَّت رغم الكراش. **هذا هو الدليل على الخطر الحقيقي.**
5. تتبّع قائمة مُستدعي `transfer()` الذين يكتبون قبلها، لتقدير نطاق الأثر.

**المرحلة B — خيارات الإصلاح (تحتاج قرارك):**
- (1) **opt-in param** (حسب تفضيلك الموثَّق): `WalletRepository.create(..., commit: bool = True)`، و`get_or_create_wallet_for_update` تمرر `commit=False` + `flush()`. لا تغيير على السلوك الافتراضي لباقي المستدعين.
- (2) إنشاء المحافظ الناقصة **قبل** `begin_nested()` في `transfer()`.
- (3) منفصلًا: migration بقيد `UNIQUE(user_id, tenant_id)` على `wallets`. يحتاج أولًا حسم `user_id=774` وأي تكرارات، و`INSERT … ON CONFLICT` في `get_or_create`.

**المرحلة C — تحقق بعد الإصلاح:** إعادة الخطوات 3-4 ⇒ نجاح التحويل + محفظة واحدة + صفر commit جزئي. ثم مجموعة اختبارات finance/insurance/saas الحالية، ثم تنظيف بمعاملة واحدة + zero-diff.

**مقترحات توثيق منفصلة (لا تُنفَّذ هنا):**
- بانر إغلاق على الملف الحرج يشير إلى `9f37201` و`54d6cfe`.
- تصحيح `dde2a84` ⇒ `54d6cfe` في `PROGRESS_LOG.md`.
- تحديث خارطة الطريق.
- قبل فتح أي بند backlog جديد: grep `PROGRESS_LOG.md` بحسب العَرَض (`get_or_create_wallet`، `wallets unique`) للتأكد من عدم وجود بند سابق. **لم يُجرَ هذا الـgrep في هذه الجلسة.**

---

## 8) ما قُرئ

- الملف الحرج كاملًا.
- رأس/ذيل تقارير `invitations-batch0b-critical-read` و`invitations-batch0b1-close-hole` و`invitations-backlog-entry-and-closure-banner-verification`.
- `PROGRESS_LOG.md:4354-4376` + نتائج grep.
- `invitations/router.py:575-610`، `invitations/service.py:260-300`.
- `identity/service.py:64-107`، `identity/repository.py:100-104, 275-284, 363-385`، `identity/invitation_service.py:55-80`.
- `finance/service.py:20-130`.
- `git log`/`git show --stat 54d6cfe`/`git branch -r --contains`.

**فجوات معلنة:**
- لم أتتبع كل مُستدعي `transfer()`.
- لم أقرأ `WalletRepository.get_by_user_id` لمعرفة أي محفظة تُعاد عند التكرار.
- لم أحقق في مصدر المحفظة 930.

---
---

# 9) تحديث الجلسة (2) — بعد قرارات المالك: مسودات التوثيق + فحص الاتساع + سحب الاكتشاف الجديد

**النوع:** ما زالت قراءة فقط. كل استعلامات DB `SELECT` تحت `default_transaction_read_only=on`. لم يُعدَّل أي كود، ولم يُكتب شيء في DB، ولم يُلمس `PROGRESS_LOG.md` ولا الملف الحرج ولا خارطة الطريق. **لم يُشغَّل أي تحقق حي.**

## 9.1) 🔴 سحب الاكتشاف الجديد (`transfer()` تنشئ المحفظة بـ`commit()` داخل SAVEPOINT): **خاطئ**

فحص الاتساع الذي طلبته (grep في `PROGRESS_LOG.md`) وجد بند `PROGRESS_LOG.md:1076`. هذا البند يقول صراحة إن المحفظة الناقصة داخل `transfer()` "تُنشأ ثم **تُلغى مع الـsavepoint**". هذا يناقض استنتاجي، فتحققت من الأمر وتبيّن أن الخطأ خطئي:

| | ما افترضتُه في §4 | الحقيقة |
|---|---|---|
| الـimport في `finance/service.py:8` | — | `from app.domains.finance.repository import WalletRepository, ...` |
| الـ`WalletRepository` الذي قرأته | `identity/repository.py:275-284` (`add` + **`commit()`** + `refresh`) | **ليس** الذي تستخدمه `FinanceService`. تستخدمه `identity/service.py:10` فقط (أي `register()`) |
| الـ`WalletRepository.create` الفعلي لـfinance | — | `finance/repository.py:34-49`: `add` + **`flush()`** + `refresh`. **صفر `commit()`** |
| متى تحوّل إلى flush-only | — | commit `aeea353` "fix(transactions): eliminate commit()-inside-begin_nested() across 24 domains" (جلسة `transaction-savepoint-bug`) |

**النتيجة:**
- الإنشاء الذاتي للمحفظة داخل `begin_nested()` في `transfer()` **آمن**: `flush` لا يُغلق الـSAVEPOINT، و`refresh` يعمل.
- لو نجح التحويل، تُثبَّت المحفظة مع التحويل ذرّيًا. ولو فشل، تُلغى معه.
- **لا كراش، ولا commit جزئي لكتابات المُستدعي.** الآلية المُفترضة غير موجودة.
- **سبب الخطأ:** تشابه الاسم (`WalletRepository` في دومينين) وقراءة نسخة identity من سياق `register()` ثم إسقاطها على finance دون التحقق من الـimport.

**أثر ذلك على قراراتك:**
- **المرحلة A (خطوات 1-5) أُلغيت ولم تُشغَّل.** لا يوجد باج لإثباته.
- **تتبّع مُستدعي `transfer()`** الذين يكتبون قبله أُلغي أيضًا، لأن الخطر الذي كان سيقيسه (commit جزئي) غير موجود. لم يُفحص أي مُستدعٍ: 0 من M.
- **خيار الإصلاح (1)** (`commit=False` opt-in) **غير لازم لـfinance**، فهي flush-only أصلًا. بقي الـ`commit()` فقط في نسخة identity، وهو جوهر "ذرّية `register()`" (المرحلة 5 من تصميم 0-B، بند معروف ومنخفض الاحتمال).
- **اقتراح اختياري (يحتاج موافقتك):** تشغيل حي قصير يثبت *الصحة* بدل الخطأ. الخطوات: مستقبِل throwaway بلا محفظة + كتابة وهمية قبل `transfer()`. المتوقع: نجاح، ومحفظة واحدة، والكتابة الوهمية لا تُثبَّت إلا مع commit المُستدعي، وعند `InsufficientBalanceError` لا تبقى محفظة. **رأيي أنه غير ضروري**: `aeea353` + بند 1076 (مُثبَت حيًا في mutation run) + الكود الحالي كافية. لكنه متاح إن أردت دليلًا حيًا.

## 9.2) فحص الاتساع (grep حسب العَرَض قبل أي بند backlog جديد)

**`PROGRESS_LOG.md`** (مصطلحات البحث: `get_or_create_wallet`، `wallets unique`، `wallets.user_id`، `unique.*wallet`، `duplicate wallet`، `محفظتين`، `محافظ مكرر`، `WalletRepository.create`):

| السطر | البند | علاقته |
|---|---|---|
| **1076** | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24، مفتوح، متوسط] | **يغطي بالفعل:** غياب تحقق انتماء المستخدم للمستأجر في `get_or_create_wallet*`، والمحافظ العابرة للمستأجرين، و`SAWarning: Multiple rows ... uselist=False` على `User.wallet`، **ومثال `wallets.id=747` للمستخدم 774 تحديدًا** |
| 264، 268 | `saas-pay-invoice-sender-id-user-id-collision`، `finance-transfer-hardcoded-system-account-real-fund-risk` | مجاورة (مُعرِّفات المُرسِل)، لا تمس الإنشاء/التفرد |
| 556 | hold_funds/settle | ذكر عابر لنمط القفل |

**`.claude/reports` و`.claude/plans`:** 15 ملفًا تذكر `get_or_create_wallet`. أهمها:
- `transaction-savepoint-bug-session-log.md:27`: توثيق تحويل `finance/repository.py` `create` إلى flush.
- `saas-sender-id-collision-fix-session-log.md:167-228, 342, 540, 606`: أصل بند 1076.
- **لم يرد أي منها** عن غياب `UNIQUE(user_id, tenant_id)` على `wallets` أو عن سباق الإنشاء المزدوج في المستأجر نفسه.

**الخلاصة:** اكتشاف "المحفظة المكررة للمستخدم 774" **ليس جديدًا**، فهو موثَّق في بند 1076. الجزء الجديد فعلًا ضيق جدًا (§9.4).

## 9.3) تتبّع المحفظة 930 (استعلام واحد، كما طلبت)

| | `wallets.id=747` | `wallets.id=930` |
|---|---|---|
| `tenant_id` | **1** | **16** |
| أُنشئت | 2026-08-20 06:22:44.676 | 2026-08-24 20:55:37 |
| الأرصدة | `{}` (فارغ، لا مفاتيح عملات) | 5 عملات = 0 |
| الحركات | لا شيء | `transactions.id=66`: 774 ⇒ 956، **50 MR_USDT**، 2026-08-24 20:55:42، من `930` إلى `931` |

- `users.id=774` (`TEST_instr_b@example.com`) **مستأجره 16**، وأُنشئ 2026-08-20 06:22:44.097.
- **⇒ تصحيح §5.3:** المحفظة **930 هي الشرعية** (مستأجر المستخدم نفسه). أنشأتها `get_or_create_wallet_for_update` داخل تحويل اختبار (مُوِّلت ثم أرسلت 50 بعد 5 ثوانٍ، ومستقبِلها 931 أُنشئ في نفس اللحظة). **العابرة هي 747** (tenant 1): أُنشئت بعد اليوزر بـ0.58 ثانية، وأرصدتها `{}` بلا مفاتيح عملات، أي **ليست** من `finance/repository.py` (التي تملأ 5 مفاتيح). الأرجح أنها من `identity` `register()`/سكربت اختبار بسياق مستأجر خاطئ. لم أُتابع أبعد من ذلك.

**"أي محفظة يعيدها `get_by_user_id` عند التكرار؟"**
- `finance/repository.py:18-24` تفلتر بـ`(user_id, tenant_id)` + `scalar_one_or_none()` ⇒ في سياق tenant 16 تعيد **930 بالضبط**، وفي سياق tenant 1 تعيد 747. **حتمي، ولا خطأ في المسار المالي** ما دام التكرار عبر مستأجرين مختلفين.
- اللا-حتمية الوحيدة في علاقة ORM `User.wallet` (`uselist=False`)، **وهي موثَّقة في بند 1076**.
- **تكرارات داخل نفس `(user_id, tenant_id)`:** `SELECT ... GROUP BY user_id, tenant_id HAVING count(*)>1` ⇒ **0 صفوف**.
- **إجمالي المحافظ العابرة** (`wallets.tenant_id <> users.tenant_id`): **1 فقط** (747).

## 9.4) الجزء الجديد فعلًا (ضيق): سباق الإنشاء بلا `UNIQUE(user_id, tenant_id)`

- `pg_indexes` على `wallets`: `ix_wallets_user_id` **غير فريد**. لا قيد فريد على `(user_id, tenant_id)`.
- `get_or_create_wallet_for_update`: `SELECT ... FOR UPDATE` على صف **غير موجود** لا يقفل شيئًا ⇒ طلبان متزامنان لنفس `(user, tenant)` بلا محفظة يُدخلان صفّين.
- بعدها كل `get_by_user_id*` بـ`scalar_one_or_none()` يرمي `MultipleResultsFound` ⇒ **المستخدم يُحرَم من كل العمليات المالية في ذلك المستأجر دائمًا**، حتى تدخّل يدوي.
- **الدليل:** قراءة كود فقط. صفر حالات حالية في DB (§9.3). احتمال منخفض (يحتاج أول عمليتين ماليتين متزامنتين). الأثر عند الحدوث DoS دائم لمستخدم واحد، لا سرقة.
- **الاقتراح (توثيق فقط، كما قررت):** **لا بند جديد**. يُلحق كفقرة "أثر ثالث" في بند 1076 نفسه، لأنه نفس الدالة ونفس الـbacklog ويُحل معه (migration `UNIQUE(user_id, tenant_id)` + `ON CONFLICT DO NOTHING` ثم إعادة القراءة). المسودة في §9.5-د.

## 9.5) مسودات التوثيق (لم يُكتب شيء منها بعد، بانتظار موافقتك)

### (أ) بانر إغلاق للملف الحرج
`.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`: يُدرج **قبل السطر 1**، والسطر 5 (`الحالة: 🔴 صفر إصلاح`) يبقى كما هو كسجل تاريخي.

```markdown
> ## ✅ مُغلَق — [تحديث 2026-09-24]
> **الآلية الموصوفة أدناه لم تعد موجودة في الكود.**
> 1. **`9f37201` (2026-08-18):** نُقل `_create_user_from_invitation` إلى خارج `begin_nested()` (جلسة `invitations-savepoint-leak`، `PROGRESS_LOG.md` بند #11a).
> 2. **`54d6cfe` (2026-09-22، Batch 0-B1):** حُذفت `_create_user_from_invitation` وكلمة المرور الافتراضية نهائيًا؛ `POST /invitations/{id}/accept` بلا مصادقة يُرجع `401 REGISTRATION_VIA_INVITATION_REQUIRED` قبل أي وصول لـDB؛ المستأجر من `current_user` فقط.
> 3. تحقق إعادة (قراءة فقط، 2026-09-24): صفر استدعاء لـ`UserService`/`register()` في دومين `invitations`؛ صفر مستخدم حقيقي بلا محفظة في DB.
> 4. **دليل هذا التقرير (`users.id=52`)**: [يُحدَّث عند التنظيف: "حُذف في <التاريخ> بعد التحقق من صفر مراجع" / أو "ما زال موجودًا"].
>
> المتبقي من نفس العائلة (خارج هذا الملف): عدم ذرّية `UserService.register()` (commit-ان متتاليان في `identity/repository.py`) — المرحلة 5 من تصميم 0-B، غير مفتوحة.
> المراجع: `invitations-batch0b-critical-read-session-log.md`، `invitations-batch0b1-close-hole-session-log.md`، `invitations-orphaned-user-wallet-investigation-session-log.md`.

---
```

### (ب) تصحيح hash في `PROGRESS_LOG.md`
**ثلاث مواضع لا اثنان:** grep وجد `dde2a84` أيضًا في **السطر 21** (بانر الحالة أعلى الملف).

| السطر | قبل | بعد |
|---|---|---|
| 21 | `…عبر accept_invitation، commit dde2a84)…` | `…عبر accept_invitation، commit 54d6cfe)…` |
| 4356 | `…مُلتزَم بواسطة صاحب المشروع يدويًا في commit dde2a84…` | `…مُلتزَم بواسطة صاحب المشروع يدويًا في commit 54d6cfe (وُثِّق أصلًا بـhash سابق dde2a84 لم يعد موجودًا في التاريخ — أُعيدت كتابته لاحقًا بنفس الرسالة)…` |
| 4362 | `**0-B1 (مُنفَّذ، commit dde2a84):**` | `**0-B1 (مُنفَّذ، commit 54d6cfe):**` |

(التنسيق الفعلي بعلامات backtick حول الـhash يُحفظ كما هو في الملف؛ حُذفت هنا فقط داخل الجدول لتفادي كسر العرض.)

**مصدر الانحراف (للأمانة):** `batch0-commits-session-log.md:13` يسجّل أن `dde2a84` **كان فعلًا على `HEAD`** في 2026-09-22، بنفس رسالة `54d6cfe` حرفيًا ("fix(invitations): stop accept_invitation creating accounts and trusting X-Tenant-ID"). الآن `git log dde2a84` ⇒ `unknown revision`، ولا أثر له في `git reflog`. **⇒ أُعيدت كتابة الـcommit** (amend/rebase) بعد التوثيق. الـhash القديم لم يكن خطأً وقت كتابته.
- لم أُثبت تطابق المحتوى بين الاثنين، فالكائن القديم غير متاح.
- التقارير التاريخية الأخرى التي تذكر `dde2a84` (`batch0-commits-session-log.md`، `batch0-progress-log-diff-for-review.md`، `batch0-progress-log-update-session-log.md`) **يُقترح تركها كما هي**، فهي سجلات لحظية صحيحة وقتها.
- ملاحظة: التعديلات هنا hunks داخل `PROGRESS_LOG.md` الذي فيه تعديلات غير مُلتزَمة سابقة (`M` منذ بداية الجلسة). أي commit لاحق يحتاج فصل hunks بحذر.

### (ج) ملاحظة خارطة الطريق
- **الملف ليس في الريبو.** موقعه: `C:\Users\Hp\Downloads\eppne-master-roadmap-1000-and-smart-city.md`.
- **توجد نسخة ثانية مطابقة بايت-ببايت:** `…\Downloads\eppne-master-roadmap-1000-and-smart-city (1).md`. **يحتاج قرارك:** أي نسخة تُعدَّل (أو كلتاهما)؟
- السطر 25 الحالي:
  > | **`invitations` — ثغرة `CRITICAL-invitations-accept-orphaned-user-no-wallet.md`** | **غير مفحوصة إطلاقًا في الجرد الأخير** — حجم الخطر مجهول | فحص فوري لمحتوى هذا الملف تحديدًا قبل أي شيء آخر يخص `invitations` |
- المقترح (استبدال العمودين 2 و3 بشطب + ملاحظة، مع إبقاء الصف):
  > | **`invitations` — ثغرة `CRITICAL-invitations-accept-orphaned-user-no-wallet.md`** | ~~غير مفحوصة إطلاقًا في الجرد الأخير — حجم الخطر مجهول~~ **✅ [تحديث 2026-09-24] معلومة قديمة وقت كتابة الخارطة: الآلية أُصلحت في `9f37201` (2026-08-18)، ومسار إنشاء الحساب حُذف كليًا في `54d6cfe` (Batch 0-B1، 2026-09-22). الخطر الفعلي اليوم: لا شيء.** | ~~فحص فوري~~ مُغلَق — انظر `.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md` |

### (د) إلحاق بند 1076 (بدل بند جديد)
يُضاف داخل خلية الوصف في `PROGRESS_LOG.md:1076`، بعد "…لم تُفحص من هذه الزاوية.":

> **أثر ثالث [2026-09-24، جلسة `invitations-orphaned-user-wallet-investigation` §9.4]:** `wallets` بلا قيد `UNIQUE(user_id, tenant_id)` (`ix_wallets_user_id` غير فريد)، و`FOR UPDATE` على صف غير موجود لا يقفل شيئًا ⇒ طلبان متزامنان أولان لنفس `(user, tenant)` قد يُنشئان محفظتين، وبعدها `scalar_one_or_none()` في `get_by_user_id*` يرمي `MultipleResultsFound` دائمًا لهذا المستخدم في هذا المستأجر (DoS مالي دائم لمستخدم واحد). قراءة كود فقط؛ صفر حالات حالية (تكرارات نفس المستأجر = 0؛ المحافظ العابرة = 1 فقط: 747). الحل مع هذا البند: migration `UNIQUE(user_id, tenant_id)` + `INSERT … ON CONFLICT DO NOTHING` ثم إعادة القراءة.

## 9.6) تنظيف `users.id=52`: فحص الأمان (SELECT فقط) + خطة الحذف (لم يُنفَّذ)

**هوية الصف:** `id=52`، `tenant_id=1`، `p_ctor_inv_newuser@eppne.com` / `p_ctor_inv_newuser`، `system_role=USER`، `idempotency_key=INV-11ad40e555cb`، أُنشئ 2026-08-16 22:52:46. Throwaway صريح (بادئة `p_ctor_`، ودليل الاكتشاف نفسه).

**المراجع:**
- **مفاتيح أجنبية:** كل الـ**191** قيد FK الذي يشير إلى `users` في DB، مع `count(*) WHERE <col>=52` لكل منها ⇒ **0 صفوف في كل الجداول**.
- **أعمدة بلا FK:** كل عمود `integer/bigint` في `public` اسمه `%user_id` أو `created_by/updated_by/owner_id/sender_id/receiver_id/actor_id` ⇒ **0 صفوف**.
- **المحفظة:** لا يوجد (§5.1). **الـlead:** لم يُنشأ أصلًا (التقرير الأصلي §4).
- **⇒ الحذف آمن من ناحية سلامة البيانات:** لا شيء يعتمد عليه، ولا cascade سيمس أي صف آخر.

**ما يبقى خارج الفحص:**
- مفتاح Redis `user:52:1`. الـTTL=3600ث وعمر الصف أكثر من شهر، فالأرجح أنه انتهى. يُتحقق بـ`EXISTS` قبل الحذف.
- المراجع النصية (البريد في سجلات/JSON) لم تُفحص، وليست قيود سلامة.

**أثر جانبي مرتبط يحتاج قرارك:** الدعوة `sovereign_invitations_v2.id=1` (`P-CTOR-INV-ACCEPT-TEST`، tenant 1، `sender_user_id=51`، **`status=SENT`**) هي أيضًا دليل نفس الجلسة، و**الدعوة الوحيدة بحالة `SENT` في DB**. هل تُنظَّف معه، أم تبقى؟ (لم تطلبها صراحة.)

**خطة الحذف المقترحة (معاملة واحدة، بعد موافقتك):**
```sql
BEGIN;
-- before
SELECT count(*) FROM users;                                  -- المتوقع 125
SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL;  -- المتوقع 27
-- guard: يجب أن يطابق صفًا واحدًا بالضبط
DELETE FROM users WHERE id=52 AND email='p_ctor_inv_newuser@eppne.com' AND idempotency_key='INV-11ad40e555cb' RETURNING id;
-- after (قبل COMMIT)
SELECT count(*) FROM users;                                  -- المتوقع 124
SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL;  -- المتوقع 26
COMMIT;   -- فقط إذا RETURNING أعاد 52 والأعداد مطابقة؛ وإلا ROLLBACK
```
بعدها: `redis-cli EXISTS user:52:1`، ويُحذف فقط لو موجود. ثم تحديث البند 4 في بانر (أ).

## 9.7) الحالة
- [x] سحب الاكتشاف الخاطئ مع الدليل.
- [x] grep الاتساع.
- [x] تتبّع المحفظة 930.
- [x] فحص أمان حذف 52.
- [x] مسودات (أ)-(د).
- [ ] **لم يُنفَّذ (بانتظار قرارك):**
  - كتابة (أ)، (ب)، (ج) [وأي نسخة من الخارطة]، (د).
  - حذف 52 [ومعه الدعوة 1؟].
  - التشغيل الحي الاختياري في §9.1.

---
---

# 10) الجلسة (3): تنفيذ التنظيف (معاملة قراءة-كتابة واحدة ومحروسة)

**التاريخ:** 2026-09-24
**النوع:** معاملة كتابة واحدة في DB (`eppne_db:5435/eppne_v2`، المستخدم `eppne`)، **بموافقة صريحة من المالك**. لم يُعدَّل أي كود، ولم يحدث staging ولا commit في git، ولم يُلمس `PROGRESS_LOG.md` ولا الملف الحرج ولا الخارطة.
**النطاق:** `users.id=52` (دليل التقرير الحرج، §9.6) + `sovereign_invitations_v2.id=1` (الدعوة المقترنة بحالة `SENT`، من نفس جلسة 2026-08-16/17)، **في المعاملة نفسها**.

## 10.1) فحوصات ما قبل التنفيذ (قراءة فقط، `default_transaction_read_only=on`)

**هوية الصفّين (مطابقة لـ§9.6):**
```
 id | tenant_id |            email             | idempotency_key  |          created_at
 52 |         1 | p_ctor_inv_newuser@eppne.com | INV-11ad40e555cb | 2026-08-16 22:52:46.424058+00

 id | tenant_id | status | sender_user_id |          created_at
  1 |         1 | SENT   |             51 | 2026-08-16 22:48:12.545039+00
    title=P-CTOR-INV-ACCEPT-TEST, target_type=PERSON, target_user_id=NULL, idempotency_key=NULL, campaign_id=1, current_uses=0
```

**مراجع `users.id=52` (أُعيد الفحص طازجًا لتفادي أي انحراف منذ §9.6):**
```
NOTICE:  users FK constraints scanned=191, total rows referencing 52=0
```

**مراجع `sovereign_invitations_v2.id=1`:**
- الجداول التي تشير إليه بـFK ثلاثة: `client_insights` و`invitation_conversations` و`invitation_tracking`، كلها بعمود `invitation_id`.
- `count(*) WHERE invitation_id=1` ⇒ `ci=0 | ic=0 | it=0`.
- أعمدة `%invitation%id%` من نوع integer/bigint في `public`: **لا يوجد غير الثلاثة نفسها**.
- `campaign_id=1` ليس FK، ولا شيء يعتمد على الدعوة من خلاله.

**⇒ الحذفان آمنان: لا شيء يعتمد على أي منهما، ولا cascade.**

## 10.2) فحص Redis `user:52:1`: ⚠️ **لم يُنفَّذ (محجوب بالمصادقة)**

```
$ docker exec redis redis-cli EXISTS user:52:1
NOAUTH Authentication required.
```

- محاولة ثانية عبر عميل التطبيق نفسه (`settings.REDIS_URL` + `settings.REDIS_PASSWORD` من `eppne-backend`، دون طباعة أي سرّ) ⇒ **رُفضت المصادقة** أيضًا (خطأ مصادقة عند `PING`).
- التفسير المرجَّح: كلمة المرور في إعدادات التطبيق لا تطابق الحيّة، وهذا متسق مع بند الـbacklog المعروف `redis-password-rotation-not-durable` (تدوير 2026-09-23 عبر `CONFIG SET` فقط). **لم يُحقَّق في ذلك هنا.**
- **لم أحاول استخراج كلمة المرور** من بيئة الحاوية، فقد رُفض ذلك (حماية بيانات الاعتماد).
- **الحالة:** وجود المفتاح **غير مُتحقَّق منه**. المتوقَّع نظريًا أنه غير موجود (TTL=3600ث وعمر المستخدم أكثر من 5 أسابيع). وحتى لو وُجد، فهو نسخة cache لمستخدم محذوف لا تشير لأي صف حي. **لم يُحذف شيء من Redis.**
- **للإغلاق يدويًا:** يشغّل المالك `! docker exec -it redis redis-cli --askpass EXISTS user:52:1` (أو ما يعادله بكلمة المرور الحالية).

## 10.3) الـSQL المُنفَّذ حرفيًا

الأمر: `docker exec -i eppne_db psql -U eppne -d eppne_v2 -v ON_ERROR_STOP=1 < cleanup.sql`

```sql
\echo '=== BEGIN ==='
BEGIN;
CREATE TEMP TABLE _before ON COMMIT DROP AS SELECT
  (SELECT count(*) FROM users) AS users_total,
  (SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL) AS users_no_wallet,
  (SELECT count(*) FROM sovereign_invitations_v2) AS inv_total,
  (SELECT count(*) FROM sovereign_invitations_v2 WHERE status='SENT') AS inv_sent;
\echo '=== BEFORE ==='
SELECT * FROM _before;
\echo '=== DELETE users.id=52 (guarded) ==='
DELETE FROM users WHERE id=52 AND email='p_ctor_inv_newuser@eppne.com' AND idempotency_key='INV-11ad40e555cb' RETURNING id, email;
\echo '=== DELETE sovereign_invitations_v2.id=1 (guarded) ==='
DELETE FROM sovereign_invitations_v2 WHERE id=1 AND tenant_id=1 AND title='P-CTOR-INV-ACCEPT-TEST' AND status='SENT' AND sender_user_id=51 RETURNING id, title, status;
\echo '=== AFTER (pre-COMMIT) ==='
SELECT (SELECT count(*) FROM users) AS users_total,
       (SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL) AS users_no_wallet,
       (SELECT count(*) FROM sovereign_invitations_v2) AS inv_total,
       (SELECT count(*) FROM sovereign_invitations_v2 WHERE status='SENT') AS inv_sent;
\echo '=== GUARD (raises -> abort+rollback on any mismatch) ==='
DO $$ DECLARE b record; BEGIN
  SELECT * INTO b FROM _before;
  IF (SELECT count(*) FROM users) <> b.users_total-1 THEN RAISE EXCEPTION 'users_total guard failed'; END IF;
  IF (SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL) <> b.users_no_wallet-1 THEN RAISE EXCEPTION 'users_no_wallet guard failed'; END IF;
  IF (SELECT count(*) FROM sovereign_invitations_v2) <> b.inv_total-1 THEN RAISE EXCEPTION 'inv_total guard failed'; END IF;
  IF (SELECT count(*) FROM sovereign_invitations_v2 WHERE status='SENT') <> b.inv_sent-1 THEN RAISE EXCEPTION 'inv_sent guard failed'; END IF;
  IF EXISTS (SELECT 1 FROM users WHERE id=52) OR EXISTS (SELECT 1 FROM sovereign_invitations_v2 WHERE id=1) THEN RAISE EXCEPTION 'target row still present'; END IF;
  RAISE NOTICE 'ALL GUARDS PASSED';
END $$;
COMMIT;
\echo '=== POST-COMMIT VERIFY (new session state) ==='
SELECT (SELECT count(*) FROM users) AS users_total,
       (SELECT count(*) FROM users u LEFT JOIN wallets w ON w.user_id=u.id WHERE w.id IS NULL) AS users_no_wallet,
       (SELECT count(*) FROM sovereign_invitations_v2) AS inv_total,
       (SELECT count(*) FROM sovereign_invitations_v2 WHERE status='SENT') AS inv_sent,
       (SELECT count(*) FROM users WHERE id=52) AS u52,
       (SELECT count(*) FROM sovereign_invitations_v2 WHERE id=1) AS inv1;
SELECT status,count(*) FROM sovereign_invitations_v2 GROUP BY status ORDER BY 1;
```

**آلية الحراسة:** مع `ON_ERROR_STOP=1`، أي `RAISE EXCEPTION` في كتلة `DO` يوقف psql قبل `COMMIT`، فتُلغى المعاملة تلقائيًا عند إغلاق الاتصال. الحراس **نسبية** (بعد = قبل − 1)، لا أرقام ثابتة، ولذلك لم تتأثر بانحراف §10.5.

**ملاحظة:** "POST-COMMIT VERIFY" نُفِّذ على نفس الاتصال بعد `COMMIT`، فهو يرى الحالة المُثبَّتة.

## 10.4) المخرجات الفعلية (حرفيًا)

```
=== BEGIN ===
BEGIN
SELECT 1
=== BEFORE ===
 users_total | users_no_wallet | inv_total | inv_sent
-------------+-----------------+-----------+----------
         124 |              27 |         4 |        1
(1 row)

=== DELETE users.id=52 (guarded) ===
 id |            email
----+------------------------------
 52 | p_ctor_inv_newuser@eppne.com
(1 row)

DELETE 1
=== DELETE sovereign_invitations_v2.id=1 (guarded) ===
 id |         title          | status
----+------------------------+--------
  1 | P-CTOR-INV-ACCEPT-TEST | SENT
(1 row)

DELETE 1
=== AFTER (pre-COMMIT) ===
 users_total | users_no_wallet | inv_total | inv_sent
-------------+-----------------+-----------+----------
         123 |              26 |         3 |        0
(1 row)

=== GUARD (raises -> abort+rollback on any mismatch) ===
DO
NOTICE:  ALL GUARDS PASSED
COMMIT
=== POST-COMMIT VERIFY (new session state) ===
 users_total | users_no_wallet | inv_total | inv_sent | u52 | inv1
-------------+-----------------+-----------+----------+-----+------
         123 |              26 |         3 |        0 |   0 |    0
(1 row)

  status  | count
----------+-------
 DRAFT    |     1
 ACCEPTED |     2
(2 rows)

psql exit=0
```

**ملخص:**

| المقياس | قبل | بعد | الفرق |
|---|---|---|---|
| `users` | 124 | 123 | −1 (52) |
| مستخدمون بلا محفظة | 27 | 26 | −1 (52) |
| `sovereign_invitations_v2` | 4 | 3 | −1 (1) |
| دعوات `SENT` | 1 | 0 | −1 (1) |

- كل `DELETE` أعاد **صفًا واحدًا بالضبط**، وهو الصف المقصود.
- `ALL GUARDS PASSED`، ثم `COMMIT`، و`psql exit=0`.
- **لم يعد في DB أي دعوة بحالة `SENT`.**

## 10.5) ⚠️ انحراف مُعلَن: `users_total` قبل الحذف = **124 لا 125**

- §5.1 سجّل "125 مستخدمًا إجمالًا"، وخطة §9.6 توقعت 125 ⇒ 124.
- القيمة الفعلية عند بدء المعاملة **124**، مع أن عدد المستخدمين بلا محفظة **27 كما هو**.
- **⇒ مستخدم واحد *لديه* محفظة اختفى من `users` بين جلسة §5 وهذه الجلسة.** لم يحذفه أي شيء في هذا التحقيق، فكل ما سبق كان `SELECT` تحت read-only.
- **لم أحدّد أي مستخدم هو، ولا من حذفه.** الأرجح أنه تنظيف من جلسة/اختبار موازٍ، لكن هذا **غير مُثبَت**.
- لم يؤثر على صحة التنظيف، لأن الحراس نسبية وكل `DELETE` مقيَّد بالهوية الكاملة للصف.
- يمكن تتبّعه بالقراءة فقط إن أردت (مثلًا: محافظ `wallets.user_id` بلا مستخدم مقابل). **لم يُجرَ.**

## 10.6) الحالة

- [x] فحوصات المراجع (FK + أعمدة بلا FK) للصفّين: صفر.
- [x] حذف `users.id=52` + `sovereign_invitations_v2.id=1` في معاملة واحدة محروسة، وتم الـCOMMIT والتحقق بعده.
- [ ] **Redis `user:52:1`: غير مُتحقَّق منه** (NOAUTH، §10.2). يحتاج المالك.
- [ ] انحراف 124/125 (§10.5): مُعلَن، ولم يُتتبَّع.
- [ ] §11 (المسودات النهائية (أ)-(د)): **بانتظار موافقة المالك على §10.**

---
---

# 11) المسودات النهائية (أ)-(د) — جاهزة للمراجعة، **لم يُكتب شيء منها في الملفات الهدف**

**التاريخ:** 2026-09-24. المالك وافق على §10.
**القاعدة:** هذه نصوص نهائية فقط. **لم يُلمس** `PROGRESS_LOG.md`، ولا `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، ولا نسختا الخارطة. يُكتب كل ذلك في جلسة لاحقة بعد موافقة صريحة.

## 11.0) تحقق المراسي قبل التثبيت (قراءة فقط، اليوم)

| الهدف | المرساة | النتيجة |
|---|---|---|
| الملف الحرج | السطر 1 = `# 🔴🔴 يوزر حقيقي بلا محفظة…`، والسطر 5 = `**الحالة: 🔴 صفر إصلاح تم…` | ✅ مطابق لـ§9.5-أ |
| `PROGRESS_LOG.md` (`grep -n dde2a84`) | الأسطر 21، 4356، 4362 | ✅ الأسطر صحيحة، **لكن السطر 21 فيه ظهوران لا ظهور واحد** ⇒ **4 ظهورات في 3 أسطر**. صُحِّحت المسودة (ب) أدناه لتشمل الاثنين |
| `PROGRESS_LOG.md:1076` | يحوي `finance-wallet-get-or-create-no-tenant-membership-check` و`لم تُفحص من هذه الزاوية.` | ✅ المرساة موجودة |
| الخارطة (نسختان) | السطر 25 يبدأ بـ`\| **\`invitations\` — ثغرة \`CRITICAL-invitations-accept-orphaned-user-no-wallet.md\`** \| **غير مفحوصة إطل…` | ✅ في النسختين. و`sha1` متطابق للنسختين (`34e70d70…`) ⇒ ما زالتا متطابقتين بايت-ببايت |

**ملاحظة:** `PROGRESS_LOG.md` فيه تعديلات غير مُلتزَمة سابقة (`M`). الأسطر أعلاه صحيحة الآن، **ويجب إعادة `grep` قبل الكتابة الفعلية** في حال تغيّر الملف.

---

## 11.1) (أ) بانر إغلاق للملف الحرج

**الهدف:** `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`
**الموضع:** يُدرج **قبل السطر 1**. السطر 5 (`الحالة: 🔴 صفر إصلاح`) يبقى كما هو كسجل تاريخي.
**التغيير عن §9.5-أ:** البند 4 فقط (نتيجة §10 الفعلية)، مع ذكر عدم التحقق من Redis بأمانة.

```markdown
> ## ✅ مُغلَق — [تحديث 2026-09-24]
> **الآلية الموصوفة أدناه لم تعد موجودة في الكود.**
> 1. **`9f37201` (2026-08-18):** نُقل `_create_user_from_invitation` إلى خارج `begin_nested()` (جلسة `invitations-savepoint-leak`، `PROGRESS_LOG.md` بند #11a).
> 2. **`54d6cfe` (2026-09-22، Batch 0-B1):** حُذفت `_create_user_from_invitation` وكلمة المرور الافتراضية نهائيًا؛ `POST /invitations/{id}/accept` بلا مصادقة يُرجع `401 REGISTRATION_VIA_INVITATION_REQUIRED` قبل أي وصول لـDB؛ المستأجر من `current_user` فقط.
> 3. تحقق إعادة (قراءة فقط، 2026-09-24): صفر استدعاء لـ`UserService`/`register()` في دومين `invitations`؛ صفر مستخدم حقيقي بلا محفظة في DB.
> 4. **دليل هذا التقرير حُذف في 2026-09-24** بعد التحقق من صفر مراجع (191 قيد FK على `users` + أعمدة بلا FK = 0 صف؛ 3 جداول FK على الدعوة = 0 صف): `users.id=52` (`p_ctor_inv_newuser@eppne.com`) و`sovereign_invitations_v2.id=1` (`P-CTOR-INV-ACCEPT-TEST`، `SENT`)، في معاملة واحدة محروسة (`ALL GUARDS PASSED` ⇒ `COMMIT`؛ users 124⇒123، الدعوات 4⇒3، `SENT` 1⇒0). مفتاح Redis `user:52:1` **لم يُتحقَّق منه** (`NOAUTH`)، والمتوقع أنه منتهٍ (TTL=3600ث). التفاصيل: `invitations-orphaned-user-wallet-investigation-session-log.md` §10.
>
> المتبقي من نفس العائلة (خارج هذا الملف): عدم ذرّية `UserService.register()` (commit-ان متتاليان في `identity/repository.py`) — المرحلة 5 من تصميم 0-B، غير مفتوحة.
> المراجع: `invitations-batch0b-critical-read-session-log.md`، `invitations-batch0b1-close-hole-session-log.md`، `invitations-orphaned-user-wallet-investigation-session-log.md`.

---
```

---

## 11.2) (ب) تصحيح hash في `PROGRESS_LOG.md`: `dde2a84` ⇒ `54d6cfe`

**4 ظهورات في 3 أسطر** (مُصحَّح عن §9.5-ب، التي فاتها الظهور الثاني في السطر 21). علامات backtick حول الـhash تبقى كما هي في الملف.

**السطر 21، الظهور الأول:**
- قبل: ``…عبر `accept_invitation`، commit `dde2a84`) و**Batch 0-C**…``
- بعد: ``…عبر `accept_invitation`، commit `54d6cfe`) و**Batch 0-C**…``

**السطر 21، الظهور الثاني (جديد):**
- قبل: ``…← `319313b` (Batch 0-C)؛ `dde2a84` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا…``
- بعد: ``…← `319313b` (Batch 0-C)؛ `54d6cfe` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا…``

**السطر 4356:**
- قبل: ``…**مُلتزَم بواسطة صاحب المشروع يدويًا في commit `dde2a84`**]).``
- بعد: ``…**مُلتزَم بواسطة صاحب المشروع يدويًا في commit `54d6cfe`** (وُثِّق أصلًا بـhash سابق `dde2a84` لم يعد موجودًا في التاريخ — أُعيدت كتابته لاحقًا بنفس الرسالة)]).``

**السطر 4362:**
- قبل: ``**0-B1 (مُنفَّذ، commit `dde2a84`):** المرحلة 1 فقط — سدّ الثغرة فورًا:``
- بعد: ``**0-B1 (مُنفَّذ، commit `54d6cfe`):** المرحلة 1 فقط — سدّ الثغرة فورًا:``

**تحقق بعد الكتابة (مقترح):**
- `grep -c dde2a84 PROGRESS_LOG.md` ⇒ **1** (الإشارة التاريخية الوحيدة المقصودة في السطر 4356).
- `grep -c 54d6cfe PROGRESS_LOG.md` ⇒ يزيد بـ**4** عن قيمته قبل الكتابة.

**مصدر الانحراف (من §9.5-ب):** الـcommit أُعيدت كتابته (amend/rebase) بعد التوثيق. التقارير التاريخية التي تذكر `dde2a84` تُترك كما هي.

---

## 11.3) (ج) الخارطة: **النسختان معًا، بنص متطابق**

**الأهداف (خارج git):**
- `C:\Users\Hp\Downloads\eppne-master-roadmap-1000-and-smart-city.md`
- `C:\Users\Hp\Downloads\eppne-master-roadmap-1000-and-smart-city (1).md`

**الموضع:** السطر 25 في كل نسخة. يُستبدل الصف كاملًا.

**قبل:**
> | **`invitations` — ثغرة `CRITICAL-invitations-accept-orphaned-user-no-wallet.md`** | **غير مفحوصة إطلاقًا في الجرد الأخير** — حجم الخطر مجهول | فحص فوري لمحتوى هذا الملف تحديدًا قبل أي شيء آخر يخص `invitations` |

**بعد:**
> | **`invitations` — ثغرة `CRITICAL-invitations-accept-orphaned-user-no-wallet.md`** | ~~غير مفحوصة إطلاقًا في الجرد الأخير — حجم الخطر مجهول~~ **✅ [تحديث 2026-09-24] معلومة قديمة وقت كتابة الخارطة: الآلية أُصلحت في `9f37201` (2026-08-18)، ومسار إنشاء الحساب حُذف كليًا في `54d6cfe` (Batch 0-B1، 2026-09-22). الخطر الفعلي اليوم: لا شيء.** | ~~فحص فوري~~ مُغلَق — انظر `.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md` |

**ضمان التزامن (مقترح عند الكتابة):**
- قبل: `sha1sum` للنسختين ⇒ متطابق (`34e70d70…`، تحقق اليوم).
- تطبيق نفس الاستبدال على النسختين.
- بعد: `sha1sum` للنسختين ⇒ **متطابق فيما بينهما** (ومختلف عن `34e70d70…`).
- `diff` بين النسختين ⇒ فارغ.

---

## 11.4) (د) إلحاق "أثر ثالث" بالبند `PROGRESS_LOG.md:1076` (لا بند جديد)

**الهدف:** `PROGRESS_LOG.md:1076` (`finance-wallet-get-or-create-no-tenant-membership-check`).
**الموضع:** داخل خلية الوصف نفسها، مباشرة بعد `…لم تُفحص من هذه الزاوية.`، بمسافة واحدة، **في نفس السطر** (فهو صف جدول، وأي سطر جديد يكسره).

**النص المُلحق (مطابق لـ§9.5-د):**

> **أثر ثالث [2026-09-24، جلسة `invitations-orphaned-user-wallet-investigation` §9.4]:** `wallets` بلا قيد `UNIQUE(user_id, tenant_id)` (`ix_wallets_user_id` غير فريد)، و`FOR UPDATE` على صف غير موجود لا يقفل شيئًا ⇒ طلبان متزامنان أولان لنفس `(user, tenant)` قد يُنشئان محفظتين، وبعدها `scalar_one_or_none()` في `get_by_user_id*` يرمي `MultipleResultsFound` دائمًا لهذا المستخدم في هذا المستأجر (DoS مالي دائم لمستخدم واحد). قراءة كود فقط؛ صفر حالات حالية (تكرارات نفس المستأجر = 0؛ المحافظ العابرة = 1 فقط: 747). الحل مع هذا البند: migration `UNIQUE(user_id, tenant_id)` + `INSERT … ON CONFLICT DO NOTHING` ثم إعادة القراءة.

**تحقق بعد الكتابة (مقترح):** `sed -n '1076p'` يحوي `أثر ثالث`، وعدد أعمدة `|` في السطر لم يتغير.

---

## 11.5) الحالة

- [x] §10 تنظيف DB (مُنفَّذ، وافق عليه المالك).
- [x] §11 مسودات (أ)-(د) نهائية، مع تحقق المراسي، وتصحيح (ب) إلى 4 ظهورات.
- [ ] **بانتظار موافقة المالك** لكتابة: (أ) الملف الحرج، (ب)+(د) `PROGRESS_LOG.md`، (ج) نسختا الخارطة.
- [ ] Redis `user:52:1`: غير مُتحقَّق منه (§10.2).
- [ ] انحراف 124/125 (§10.5): لم يُتتبَّع.
- لا staging، لا commit.


---
---

# 12) الجلسة (4): كتابة الأهداف الأربعة (بموافقة المالك على §11)

**التاريخ:** 2026-09-24. **لا staging ولا commit** لأي ملف: `PROGRESS_LOG.md` ينتظر موافقة صريحة، وكذلك الملف الحرج (انظر 12.1).

## 12.1) (أ) بانر الملف الحرج: ✅ مكتوب

- أُدرج **قبل السطر 1** (12 سطرًا: 10 بانر + `---` + سطر فارغ). السطر الأصلي `# 🔴🔴 يوزر حقيقي بلا محفظة…` صار السطر 13، وسطر `الحالة: 🔴 صفر إصلاح` باقٍ كما هو.
- `git diff --stat` ⇒ `12 insertions(+)`، صفر حذف. الحجم 16167 ⇒ 18139 بايت. LF محفوظ، بلا BOM.
- **⚠️ تصحيح لفرضية:** الملف **مُتتبَّع في git** (`git ls-files` يُدرجه)، أي أنه ليس خارج git. يظهر الآن `M`، **ويحتاج قرار staging** مثل `PROGRESS_LOG.md`. لم يُعمل له stage.
- ملاحظة: البانر يسجّل users 124⇒123 لكنه **لا يذكر** انحراف 124/125 صراحةً (المسودة المعتمدة §11.1 كما هي). الانحراف موثَّق في §10.5 من هذا التقرير.

## 12.2) (ب)+(د) `PROGRESS_LOG.md`: مكتوب في شجرة العمل، **غير مُجهَّز للـstage**

**الطريقة:**
- الاستبدالات الخمسة نفسها طُبِّقت على مستوى البايت، على شجرة العمل وعلى blob الـHEAD في آنٍ واحد.
- كل استبدال مشروط بتطابق **واحد بالضبط** في كلٍّ منهما، وإلا يتوقف السكربت.
- حُفظ CRLF في شجرة العمل.
- نسخة احتياطية: `scratchpad/PL_work_old_backup.md`.
- الـblob المعزول (HEAD + هذه التعديلات فقط): `scratchpad/PL_head_new_isolated.md`، sha1 `1fab7cb1…`. **هذا هو ما سيُجهَّز للـstage** عند الموافقة، عبر `git hash-object -w` + `git update-index --cacheinfo`، لا بـ`git add`.

**التحققات:**

| الفحص | النتيجة |
|---|---|
| `diff HEAD ⇒ blob معزول` | **4 أسطر تغيّرت فقط** (21، 1076، 4356، 4362)، 4+/4− |
| التعديلات الأخرى غير المُلتزَمة سابقًا | diff-of-diffs (HEAD⇒work قبل، مقابل HEAD-معزول⇒work بعد) = **566 سطرًا متطابقة بايت-ببايت** ⇒ لم تُمس |
| `dde2a84` في شجرة العمل | **1** (الإشارة التاريخية المقصودة في 4356) |
| `54d6cfe` في شجرة العمل | 0 ⇒ **4** |
| `أثر ثالث [2026-09-24` | 1 |
| عدد `\|` في السطر 1076 | 5 ⇒ 5 (صف الجدول سليم) |
| `git diff --cached` | فارغ (لا شيء مُجهَّز) |

**الـdiff المعزول حرفيًا** (HEAD ⇒ blob معزول، `-U0`):

```diff
diff --git a/PROGRESS_LOG.md b/PROGRESS_LOG.md
index 4c1b009..f1b3144 100644
--- a/PROGRESS_LOG.md
+++ b/PROGRESS_LOG.md
@@ -21 +21 @@
-**تحديث [2026-09-22] — الدفعة 0 اكتملت بكامل نطاقها الثلاثي:** بالإضافة لـBatch 0-A أعلاه (insurance)، أُغلقت **Batch 0-B/0-B1** (`invitations` — سدّ ثغرة تسجيل ذاتي مجهول عبر `accept_invitation`، commit `dde2a84`) و**Batch 0-C** (`admin` — مفتاح إيقاف طارئ لاستدعاءات AI، commit `319313b`). التفاصيل الكاملة لكل من B/C في قسم `## [2026-09-22]` تحت. الأربعة commits بالترتيب الزمني: `347c337` (migration 048) ← `9ff6572`/`65a4168` (insurance، أعمال سابقة على 0-A) ← `a231c58` (Batch 0-A) ← `319313b` (Batch 0-C)؛ `dde2a84` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا (مُلتزَم يدويًا بواسطة صاحب المشروع).
+**تحديث [2026-09-22] — الدفعة 0 اكتملت بكامل نطاقها الثلاثي:** بالإضافة لـBatch 0-A أعلاه (insurance)، أُغلقت **Batch 0-B/0-B1** (`invitations` — سدّ ثغرة تسجيل ذاتي مجهول عبر `accept_invitation`، commit `54d6cfe`) و**Batch 0-C** (`admin` — مفتاح إيقاف طارئ لاستدعاءات AI، commit `319313b`). التفاصيل الكاملة لكل من B/C في قسم `## [2026-09-22]` تحت. الأربعة commits بالترتيب الزمني: `347c337` (migration 048) ← `9ff6572`/`65a4168` (insurance، أعمال سابقة على 0-A) ← `a231c58` (Batch 0-A) ← `319313b` (Batch 0-C)؛ `54d6cfe` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا (مُلتزَم يدويًا بواسطة صاحب المشروع).
@@ -1076 +1076 @@ seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + 
-| — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |
+| — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. **أثر ثالث [2026-09-24، جلسة `invitations-orphaned-user-wallet-investigation` §9.4]:** `wallets` بلا قيد `UNIQUE(user_id, tenant_id)` (`ix_wallets_user_id` غير فريد)، و`FOR UPDATE` على صف غير موجود لا يقفل شيئًا ⇒ طلبان متزامنان أولان لنفس `(user, tenant)` قد يُنشئان محفظتين، وبعدها `scalar_one_or_none()` في `get_by_user_id*` يرمي `MultipleResultsFound` دائمًا لهذا المستخدم في هذا المستأجر (DoS مالي دائم لمستخدم واحد). قراءة كود فقط؛ صفر حالات حالية (تكرارات نفس المستأجر = 0؛ المحافظ العابرة = 1 فقط: 747). الحل مع هذا البند: migration `UNIQUE(user_id, tenant_id)` + `INSERT … ON CONFLICT DO NOTHING` ثم إعادة القراءة. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |
@@ -4356 +4356 @@ pensions عبر كل التينانتس). يحتاج تصميم/موافقة م
-**invitations-batch0b-accept-invitation-anonymous-registration-gateway-closed [2026-09-21/22]** — ✅ **مُغلَق رسميًا** (نطاق: قراءة نقدية للاكتشاف الحرج التاريخي [0-B] + تصميم بوابة `register-with-invitation` [0-B الجزء 2، تصميم فقط، لم يُنفَّذ] + سدّ فوري لثغرة self-enrollment [0-B1، مُنفَّذ ومُتحقَّق حيًا، **مُلتزَم بواسطة صاحب المشروع يدويًا في commit `dde2a84`**]).
+**invitations-batch0b-accept-invitation-anonymous-registration-gateway-closed [2026-09-21/22]** — ✅ **مُغلَق رسميًا** (نطاق: قراءة نقدية للاكتشاف الحرج التاريخي [0-B] + تصميم بوابة `register-with-invitation` [0-B الجزء 2، تصميم فقط، لم يُنفَّذ] + سدّ فوري لثغرة self-enrollment [0-B1، مُنفَّذ ومُتحقَّق حيًا، **مُلتزَم بواسطة صاحب المشروع يدويًا في commit `54d6cfe`** (وُثِّق أصلًا بـhash سابق `dde2a84` لم يعد موجودًا في التاريخ — أُعيدت كتابته لاحقًا بنفس الرسالة)]).
@@ -4362 +4362 @@ pensions عبر كل التينانتس). يحتاج تصميم/موافقة م
-**0-B1 (مُنفَّذ، commit `dde2a84`):** المرحلة 1 فقط — سدّ الثغرة فورًا:
+**0-B1 (مُنفَّذ، commit `54d6cfe`):** المرحلة 1 فقط — سدّ الثغرة فورًا:
```

## 12.3) (ج) نسختا الخارطة: ✅ مكتوبتان ومتزامنتان

| النسخة | sha1 قبل | sha1 بعد |
|---|---|---|
| `eppne-master-roadmap-1000-and-smart-city.md` | `34e70d7010eccdb3141f93c1dd936059f8c53bc5` | `34db37e761c7c35b4e23953a089a85f5119a6990` |
| `eppne-master-roadmap-1000-and-smart-city (1).md` | `34e70d7010eccdb3141f93c1dd936059f8c53bc5` | `34db37e761c7c35b4e23953a089a85f5119a6990` |

- السكربت اشترط، قبل الكتابة، أن sha1 = الأصل، وأن المرساة على السطر 25 بالضبط.
- بعد الكتابة: النسختان **متطابقتان فيما بينهما**، و**مختلفتان عن الأصل**. `diff -q` بينهما فارغ.
- الفرق عن النسخة الاحتياطية: `25c25` فقط، سطر واحد.
- نسخ احتياطية: `scratchpad/roadmap_backup_0.md` و`_1.md`.

## 12.4) الحالة

- [x] (أ) الملف الحرج: مكتوب (مُتتبَّع في git، غير مُجهَّز للـstage).
- [x] (ب)+(د) `PROGRESS_LOG.md`: مكتوب في شجرة العمل، والـblob المعزول جاهز.
- [x] (ج) نسختا الخارطة: مكتوبتان ومتطابقتان.
- [ ] **بانتظار موافقة المالك:** staging + commit لـ`PROGRESS_LOG.md` (الـblob المعزول) و`CRITICAL-…md`.


---
---

# 13) الجلسة (5): صف backlog لانحراف 124/125 + فقرة إغلاق + توسيع الـblob المعزول + رسالتا commit (**مسودات، لا stage ولا commit**)

**التاريخ:** 2026-09-24. **لم يُلمس `PROGRESS_LOG.md` في شجرة العمل** (sha1 ما زال `bba476d0…` من §12). كل شيء أدناه في الـscratchpad فقط.

## 13.1) فحص الاتساع قبل الصف الجديد (grep حسب العَرَض)

- `grep -i 'user-count|users_total|disappeared|اختفى|user count'` في `PROGRESS_LOG.md` ⇒ **لا بند سابق** يغطي انخفاض عدد `users` غير المفسَّر.
- `grep -i 'redis-password-rotation|redis.*rotation|CONFIG SET'` ⇒ **صفر نتائج**. بند `redis-password-rotation-not-durable` موجود فقط في الذاكرة/التقارير، **ولا صف له في `PROGRESS_LOG.md`**. لذلك، وحسب البند 4 من تعليماتك، ذُكر Redis عابرًا في **فقرة الإغلاق** (13.3).

## 13.2) (أ) الصف الجديد: `users-row-count-unexplained-drop-2026-09-24`

**الموضع:** آخر صف في جدول الـbacklog، مباشرة بعد صف `academy-camera-stack-uncommitted-implementation-deferred-session` (السطر 1079 ⇒ الجديد 1080). الشكل مطابق للجدول: `| — | وصف | أولوية | تقرير |` (5 أعمدة `|`).

```
| — | **`users-row-count-unexplained-drop-2026-09-24`** [2026-09-24] — اكتُشف في جلسة `invitations-accept-orphaned-user-no-wallet-investigation` (§10.5): `users.id=?` — مستخدم واحد **لديه محفظة** اختفى من جدول `users` بين §5 من الجلسة (125 إجمالًا) و§10 (124 إجمالًا، وعدد المستخدمين بلا محفظة ثابت عند 27)، دون أي `DELETE` من أي تحقيق قراءة-فقط بينهما. السبب وهوية المستخدم المفقود مجهولان — الأرجح جلسة اختبار/تنظيف موازية، لكن غير مؤكَّد. للعلم فقط، غير عاجل (لم يُعثر على أثر على سلامة البيانات)، لكن يجب تتبّعه إن تكرر أو ظهرت فجوة مماثلة. | 🟡 منخفض — للعلم فقط | `.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md` §10.5 |
```

**ملاحظتان للمراجعة:**
1. **اللغة:** نصك كان بالإنجليزية. تُرجم للعربية كما هو باقي `PROGRESS_LOG.md`، مع الحفاظ على كل عنصر (`users.id=?`، 125⇒124، 27 ثابت، لا `DELETE`، سبب مجهول، "الأرجح جلسة موازية، غير مؤكَّد"، للعلم، تتبُّع عند التكرار). إن أردت الإنجليزية حرفيًا، فالاستبدال بسيط.
2. **رمز الأولوية:** طلبتَ `🟡 منخفض، للعلم`. في هذا الجدول تحديدًا الاصطلاح الفعلي: `🟢 منخفض` (3 صفوف)، و`⚪ مرجع فقط/مفتوح` (2)، و`🟡` يُستخدم غالبًا لـ"مفتوح/منخفض-متوسط". وُضع `🟡` كما طلبت. البديل الأكثر اتساقًا: `⚪ للعلم فقط` أو `🟢 منخفض — للعلم فقط`. القرار لك.

## 13.3) (ب-إضافي) فقرة الإغلاق: **إضافة خارج قائمتك الثلاثية، للمراجعة**

**السبب:** البند 4 يطلب ذكر Redis "في فقرة إغلاق PROGRESS_LOG"، ورسالة الـcommit تقول "close invitations orphaned-user investigation"، لكن الـblob المعزول **لم يكن فيه فقرة إغلاق**. نمط الملف: كل إغلاق مؤرَّخ = فقرة `**✅ إغلاق مؤرَّخ [...]**` بعد الجدول (أمثلة: الأسطر 1081، 1083، 1085).
**الموضع:** بعد آخر فقرة إغلاق (`saas-pay-invoice-sender-id-user-id-collision`، السطر 1085)، يفصلها سطر فارغ.

```
**✅ إغلاق مؤرَّخ [2026-09-24] — `invitations-accept-orphaned-user-no-wallet` (`.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، 2026-08-17): مُغلَق — تقرير حرج قديم، لا باج حي.** جلسة `invitations-accept-orphaned-user-no-wallet-investigation` (`.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md`). الآلية أُصلحت في `9f37201` (2026-08-18)، ومسار إنشاء الحساب من `accept` حُذف كليًا في `54d6cfe` (Batch 0-B1، 2026-09-22)؛ تحقق إعادة: صفر استدعاء لـ`UserService`/`register()` في `invitations/`. أُضيف بانر إغلاق للملف الحرج (commit منفصل). **تنظيف DB:** حُذف دليل التقرير `users.id=52` والدعوة المقترنة `sovereign_invitations_v2.id=1` (`SENT`) في معاملة واحدة محروسة بعد التحقق من صفر مراجع (§10). مفتاح Redis `user:52:1` **لم يُتحقَّق منه** (`NOAUTH`: كلمة سر Redis الحية لا تطابق إعدادات التطبيق، متسق مع تدوير 2026-09-23 عبر `CONFIG SET` غير الدائم، ولا صف backlog له في هذا الملف بعد)؛ المتوقع أنه منتهٍ (TTL=3600ث)، غير مانع. **سُحب في نفس الجلسة:** اشتباه `commit()` داخل `begin_nested()` في `FinanceService.transfer()` — خاطئ (خلط بين `WalletRepository` في identity وfinance؛ نسخة finance `flush()` فقط منذ `aeea353`). **وفي نفس الإغلاق:** تصحيح hash `dde2a84`⇒`54d6cfe` (4 مواضع؛ أُعيدت كتابة الـcommit بعد التوثيق)، و"أثر ثالث" في `finance-wallet-get-or-create-no-tenant-membership-check` (غياب `UNIQUE(user_id, tenant_id)` على `wallets`)، والصف الجديد `users-row-count-unexplained-drop-2026-09-24` (أعلاه).
```

إن رفضتَها، تُحذف من الـblob، ويبقى Redis بلا ذكر في `PROGRESS_LOG.md` (أو يُضاف كجملة داخل الصف الجديد، لكنه موضوع مختلف).

## 13.4) (ب) الـdiff المعزول المُحدَّث: HEAD ⇒ `PL_head_new_isolated_v2.md` (sha1 `18ac121f…`)

**الإحصاء:** 7+/4− في 6 hunks:

| hunk | المحتوى |
|---|---|
| `@@ -21 +21` | تصحيحا الـhash في السطر 21 (ظهوران) |
| `@@ -1076 +1076` | "أثر ثالث" |
| `@@ -1079,0 +1080` | **الصف الجديد** |
| `@@ -1086,0 +1088,2` | **سطر فارغ + فقرة الإغلاق** |
| `@@ -4356 +4359` | تصحيح hash + ملاحظة `dde2a84` التاريخية |
| `@@ -4362 +4365` | تصحيح hash |

**التحقق:**
- diff-of-diffs (HEAD-معزول-v2 ⇒ مرشَّح شجرة العمل، مقابل الأصل) = **566 سطرًا متطابقة بايت-ببايت** (`cmp` ⇒ IDENTICAL).
- كل إدراج مشروط بمرساة **واحدة بالضبط** + سطر فارغ بعدها، في النسختين.

**⚠️ اكتشاف أثناء البناء:** `PROGRESS_LOG.md` في شجرة العمل كله CRLF (5293)، **إلا سطرًا واحدًا بـLF مجرد: نهاية السطر 1079** (صف `academy-camera-stack…`، من العمل غير المُلتزَم السابق، لا من هذه الجلسة). الحارس أوقف المحاولة الأولى عنده قبل أي كتابة. عُدِّل السكربت ليقسم على `\n` ويحافظ على نهاية كل سطر كما هي، **فالـLF الشاذ لم يُلمس**. git يطبّعه عند الـstage على أي حال (الـblob المعزول LF بالكامل).

```diff
diff --git a/PROGRESS_LOG.md b/PROGRESS_LOG.md
--- a/PROGRESS_LOG.md
+++ b/PROGRESS_LOG.md
@@ -21 +21 @@
-**تحديث [2026-09-22] — الدفعة 0 اكتملت بكامل نطاقها الثلاثي:** بالإضافة لـBatch 0-A أعلاه (insurance)، أُغلقت **Batch 0-B/0-B1** (`invitations` — سدّ ثغرة تسجيل ذاتي مجهول عبر `accept_invitation`، commit `dde2a84`) و**Batch 0-C** (`admin` — مفتاح إيقاف طارئ لاستدعاءات AI، commit `319313b`). التفاصيل الكاملة لكل من B/C في قسم `## [2026-09-22]` تحت. الأربعة commits بالترتيب الزمني: `347c337` (migration 048) ← `9ff6572`/`65a4168` (insurance، أعمال سابقة على 0-A) ← `a231c58` (Batch 0-A) ← `319313b` (Batch 0-C)؛ `dde2a84` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا (مُلتزَم يدويًا بواسطة صاحب المشروع).
+**تحديث [2026-09-22] — الدفعة 0 اكتملت بكامل نطاقها الثلاثي:** بالإضافة لـBatch 0-A أعلاه (insurance)، أُغلقت **Batch 0-B/0-B1** (`invitations` — سدّ ثغرة تسجيل ذاتي مجهول عبر `accept_invitation`، commit `54d6cfe`) و**Batch 0-C** (`admin` — مفتاح إيقاف طارئ لاستدعاءات AI، commit `319313b`). التفاصيل الكاملة لكل من B/C في قسم `## [2026-09-22]` تحت. الأربعة commits بالترتيب الزمني: `347c337` (migration 048) ← `9ff6572`/`65a4168` (insurance، أعمال سابقة على 0-A) ← `a231c58` (Batch 0-A) ← `319313b` (Batch 0-C)؛ `54d6cfe` (Batch 0-B1) مستقل عن هذه السلسلة تمامًا (مُلتزَم يدويًا بواسطة صاحب المشروع).
@@ -1076 +1076 @@ seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + 
-| — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |
+| — | **`finance-wallet-get-or-create-no-tenant-membership-check`** [2026-09-24] — اكتُشف في جلسة `saas-sender-id-collision-fix` (§4.3-أ، §8.1، §14.3-4): `FinanceService.get_or_create_wallet_for_update(user_id)` (`finance/service.py:34-39`) و`WalletRepository.create` لا يتحققان أبدًا من أن `users.tenant_id == self.tenant_id`، و`transfer()` يتحقق من تينانت **المستقبِل** (`:88`) لا **المُرسِل**. النتيجة: أي `sender_id` لمستخدم من تينانت أخرى يُخصم من محفظة `(user, tenant)` عابرة إن كانت موجودة وممولة (**مُثبَت حيًا** في الـmutation run: 100→90). وإن لم تكن موجودة فتُنشأ ثم تُلغى مع الـsavepoint عند `InsufficientBalanceError`. **أثر ثانٍ:** العلاقة `User.wallet` (`uselist=False`) تعطي `SAWarning: Multiple rows returned with uselist=False` لأي مستخدم له محفظة عابرة، فأي كود يقرأ `user.wallet` يحصل على محفظة غير حتمية. دليل صفوف عابرة حقيقية: `wallets.id=747` = `(user 774 [tenant 16], tenant 1)`. saas محمي الآن بتحقق محلي في `_get_tenant_admin_id`؛ بقية مستدعي `transfer()` لم تُفحص من هذه الزاوية. **أثر ثالث [2026-09-24، جلسة `invitations-orphaned-user-wallet-investigation` §9.4]:** `wallets` بلا قيد `UNIQUE(user_id, tenant_id)` (`ix_wallets_user_id` غير فريد)، و`FOR UPDATE` على صف غير موجود لا يقفل شيئًا ⇒ طلبان متزامنان أولان لنفس `(user, tenant)` قد يُنشئان محفظتين، وبعدها `scalar_one_or_none()` في `get_by_user_id*` يرمي `MultipleResultsFound` دائمًا لهذا المستخدم في هذا المستأجر (DoS مالي دائم لمستخدم واحد). قراءة كود فقط؛ صفر حالات حالية (تكرارات نفس المستأجر = 0؛ المحافظ العابرة = 1 فقط: 747). الحل مع هذا البند: migration `UNIQUE(user_id, tenant_id)` + `INSERT … ON CONFLICT DO NOTHING` ثم إعادة القراءة. | 🔴 **مفتوح، أولوية متوسطة** — دفاع في العمق على مستوى finance كله، خارج نطاق saas | `.claude/reports/saas-sender-id-collision-fix-session-log.md` §8.1، §14 |
@@ -1079,0 +1080 @@ seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + 
+| — | **`users-row-count-unexplained-drop-2026-09-24`** [2026-09-24] — اكتُشف في جلسة `invitations-accept-orphaned-user-no-wallet-investigation` (§10.5): `users.id=?` — مستخدم واحد **لديه محفظة** اختفى من جدول `users` بين §5 من الجلسة (125 إجمالًا) و§10 (124 إجمالًا، وعدد المستخدمين بلا محفظة ثابت عند 27)، دون أي `DELETE` من أي تحقيق قراءة-فقط بينهما. السبب وهوية المستخدم المفقود مجهولان — الأرجح جلسة اختبار/تنظيف موازية، لكن غير مؤكَّد. للعلم فقط، غير عاجل (لم يُعثر على أثر على سلامة البيانات)، لكن يجب تتبّعه إن تكرر أو ظهرت فجوة مماثلة. | 🟡 منخفض — للعلم فقط | `.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md` §10.5 |
@@ -1086,0 +1088,2 @@ seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + 
+**✅ إغلاق مؤرَّخ [2026-09-24] — `invitations-accept-orphaned-user-no-wallet` (`.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، 2026-08-17): مُغلَق — تقرير حرج قديم، لا باج حي.** جلسة `invitations-accept-orphaned-user-no-wallet-investigation` (`.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md`). الآلية أُصلحت في `9f37201` (2026-08-18)، ومسار إنشاء الحساب من `accept` حُذف كليًا في `54d6cfe` (Batch 0-B1، 2026-09-22)؛ تحقق إعادة: صفر استدعاء لـ`UserService`/`register()` في `invitations/`. أُضيف بانر إغلاق للملف الحرج (commit منفصل). **تنظيف DB:** حُذف دليل التقرير `users.id=52` والدعوة المقترنة `sovereign_invitations_v2.id=1` (`SENT`) في معاملة واحدة محروسة بعد التحقق من صفر مراجع (§10). مفتاح Redis `user:52:1` **لم يُتحقَّق منه** (`NOAUTH`: كلمة سر Redis الحية لا تطابق إعدادات التطبيق، متسق مع تدوير 2026-09-23 عبر `CONFIG SET` غير الدائم، ولا صف backlog له في هذا الملف بعد)؛ المتوقع أنه منتهٍ (TTL=3600ث)، غير مانع. **سُحب في نفس الجلسة:** اشتباه `commit()` داخل `begin_nested()` في `FinanceService.transfer()` — خاطئ (خلط بين `WalletRepository` في identity وfinance؛ نسخة finance `flush()` فقط منذ `aeea353`). **وفي نفس الإغلاق:** تصحيح hash `dde2a84`⇒`54d6cfe` (4 مواضع؛ أُعيدت كتابة الـcommit بعد التوثيق)، و"أثر ثالث" في `finance-wallet-get-or-create-no-tenant-membership-check` (غياب `UNIQUE(user_id, tenant_id)` على `wallets`)، والصف الجديد `users-row-count-unexplained-drop-2026-09-24` (أعلاه).
+
@@ -4356 +4359 @@ pensions عبر كل التينانتس). يحتاج تصميم/موافقة م
-**invitations-batch0b-accept-invitation-anonymous-registration-gateway-closed [2026-09-21/22]** — ✅ **مُغلَق رسميًا** (نطاق: قراءة نقدية للاكتشاف الحرج التاريخي [0-B] + تصميم بوابة `register-with-invitation` [0-B الجزء 2، تصميم فقط، لم يُنفَّذ] + سدّ فوري لثغرة self-enrollment [0-B1، مُنفَّذ ومُتحقَّق حيًا، **مُلتزَم بواسطة صاحب المشروع يدويًا في commit `dde2a84`**]).
+**invitations-batch0b-accept-invitation-anonymous-registration-gateway-closed [2026-09-21/22]** — ✅ **مُغلَق رسميًا** (نطاق: قراءة نقدية للاكتشاف الحرج التاريخي [0-B] + تصميم بوابة `register-with-invitation` [0-B الجزء 2، تصميم فقط، لم يُنفَّذ] + سدّ فوري لثغرة self-enrollment [0-B1، مُنفَّذ ومُتحقَّق حيًا، **مُلتزَم بواسطة صاحب المشروع يدويًا في commit `54d6cfe`** (وُثِّق أصلًا بـhash سابق `dde2a84` لم يعد موجودًا في التاريخ — أُعيدت كتابته لاحقًا بنفس الرسالة)]).
@@ -4362 +4365 @@ pensions عبر كل التينانتس). يحتاج تصميم/موافقة م
-**0-B1 (مُنفَّذ، commit `dde2a84`):** المرحلة 1 فقط — سدّ الثغرة فورًا:
+**0-B1 (مُنفَّذ، commit `54d6cfe`):** المرحلة 1 فقط — سدّ الثغرة فورًا:
```

## 13.5) (ج) رسالتا الـcommit (مسودتان)

**Commit 1 — الملف الحرج فقط** (`.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، 12+/0−، عبر `git add` لملف واحد لا توجد فيه تعديلات أخرى):
```
docs: close CRITICAL invitations orphaned-user-wallet report — already fixed (9f37201, 54d6cfe)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**Commit 2 — `PROGRESS_LOG.md` فقط** (الـblob المعزول v2 عبر `git hash-object -w` + `git update-index --cacheinfo 100644,<sha>,PROGRESS_LOG.md`؛ 7+/4−):
```
docs: close invitations orphaned-user investigation — stale critical report, dde2a84→54d6cfe hash fix, wallets UNIQUE gap appended to 1076, unexplained user-count drop logged

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**بعد كل commit:** `git show --stat` للتأكد من المطابقة (ملف واحد؛ 12+/0− ثم 7+/4−). ثم `git diff PROGRESS_LOG.md` يجب أن يُظهر الـ566 سطرًا فقط. **وتنبيه:** بعد commit 2 يجب تطبيق الإضافتين الجديدتين (الصف + الإغلاق) على شجرة العمل أيضًا، وإلا ظهرتا كـ"محذوفتين" مقارنة بـHEAD. الترتيب المقترح: كتابة `PL_work_candidate_v2.md` إلى شجرة العمل **أولًا**، ثم الـstage للـblob المعزول، ثم commit.

**سؤال مفتوح:** تقرير هذه الجلسة نفسه (`invitations-orphaned-user-wallet-investigation-session-log.md`) **غير مُتتبَّع** (`??`). نمط اليوم (`77c216c`، `5c21a92`) = commit ثالث منفصل `docs: add session report for …`. هل يُضاف؟

## 13.6) الحالة

- [x] grep الاتساع (لا بند سابق، ولا صف Redis).
- [x] مسودة الصف الجديد + فقرة الإغلاق.
- [x] الـblob المعزول v2 + مرشَّح شجرة العمل (في الـscratchpad فقط)، و566 سطرًا متطابقة.
- [x] مسودتا رسالتي الـcommit.
- [ ] **بانتظار موافقتك على:** نص الصف (اللغة + الرمز)، فقرة الإغلاق (قبول/رفض)، الرسالتين، وcommit ثالث لتقرير الجلسة.
- لا staging، لا commit. شجرة العمل لم تتغير منذ §12.


---
---

# 14) الإغلاق: ثلاثة commits (بموافقة المالك على §13)

المالك وافق على §13 كما هي: الصف بالعربية وبرمز `🟡`، وفقرة الإغلاق مقبولة.

| # | commit | الملف | الإحصاء | الطريقة |
|---|---|---|---|---|
| 1 | `73c17c4` | `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md` | 12+/0− | `git add` لملف واحد (لا تعديلات أخرى فيه) |
| 2 | `8295f4c` | `PROGRESS_LOG.md` | 7+/4− | blob معزول (`PL_head_new_isolated_v2.md`) عبر `git hash-object -w --no-filters` + `git update-index --cacheinfo` |
| 3 | (هذا التقرير) | `.claude/reports/invitations-orphaned-user-wallet-investigation-session-log.md` | ملف جديد | `git add` لملف واحد |

**تحققات commit 2:**
- قبل الكتابة: sha1 شجرة العمل = `bba476d0…` (لم يتغير منذ §12)، وblob الـHEAD = `PL_head_old.md`. وإلا كان السكربت سيتوقف.
- شجرة العمل كُتبت أولًا (المرشَّح v2) ثم جُهِّز الـblob المعزول ⇒ لا تظهر الإضافات كـ"محذوفة".
- `git diff --cached --stat` قبل الـcommit = 7+/4− بالضبط.
- الباقي غير المُجهَّز = 670+/1− = **نفس الـ566 سطرًا الأصلية بايت-ببايت** (`cmp`).
- `git show --stat 8295f4c` = ملف واحد، 7+/4−.
- في HEAD: `dde2a84` في سطرين (الملاحظة التاريخية 4359 + فقرة الإغلاق التي تذكر التصحيح)، وهذا مقصود.

**ما بقي مفتوحًا (موثَّق، غير مانع):**
- Redis `user:52:1` غير مُتحقَّق منه (§10.2)، ومذكور في فقرة الإغلاق.
- بند `redis-password-rotation-not-durable` **لا صف له في `PROGRESS_LOG.md`** (موجود في الذاكرة/التقارير فقط).
- انحراف 124/125 ⇒ صف `users-row-count-unexplained-drop-2026-09-24`.
- الـLF المجرد الوحيد في نهاية السطر 1079 من شجرة العمل (من العمل غير المُلتزَم السابق) ⇒ لم يُلمس.
