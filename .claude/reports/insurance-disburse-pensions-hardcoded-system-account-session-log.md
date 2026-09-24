# سجل جلسة: insurance-disburse-pensions-hardcoded-system-account

- **التاريخ:** 2026-09-24
- **النوع:** قراءة فقط (Step 1 + Step 2). **صفر تعديل كود، صفر staging/commit، صفر كتابة في PROGRESS_LOG.md.**
- **HEAD وقت الفحص:** `9167603` (main، متزامن مع origin/main).

---

## 0. الخلاصة التنفيذية

1. **سياق الجلسة (من بند 2026-09-16) قديم جزئيًا.** `disburse_monthly_pensions` **لم تعد تلف على كل التينانتات**: Batch 0-A (`44f1d0e`، 2026-09-22، مدفوع على origin) حوّلها إلى `disburse_monthly_pensions(tenant_id)` لتينانت واحد (تينانت المستدعي). لكن **`sender_id=1` لا يزال هاردكودد حرفيًا** — الآن في `insurance/service.py:650` (كان :626 ثم :638).
2. **الدالة معطّلة فعليًا اليوم** (`count=0` دائمًا): `finance.transfer(...)` يُستدعى **بلا `idempotency_key`** وهو معامل إجباري → `TypeError` يُبلَع بـ`except Exception: pass`. هذا موثَّق في بند منفصل `insurance-disburse-pensions-payout-logic-broken` (🔴)، ومعه **شرط ترتيب صريح**: قرار الدافع (هذه الجلسة) يُحسَم **قبل** إصلاح `idempotency_key`.
3. **الخطر لا يزال كامنًا (latent):** نقطة استدعاء وحيدة (endpoint يدوي superuser-only)، صفر جدولة، صفر استدعاء من الفرونت إند، **صفر معاملة pension في كل جدول `transactions`**، و`pension_records` **فارغ تمامًا اليوم (0 صف)**.
4. **ادعاء الـroadmap عن 4 endpoints تأخذ التينانت من الهيدر: قديم بالكامل (stale).** الأربعة (`create_policy`, `review_claim`, `create_pension`, `create_employee_profile`) أُصلحت في `44f1d0e` (Batch 0-A، 2026-09-22) — أي **بعد** تاريخ الـroadmap (2026-09-18). ليس أثرًا جانبيًا لجلسة `get_by_id` (2026-08-19) ولا لجلسة الدفع المزدوج (`88097be`، 2026-09-23).
5. **اكتشاف مهم للتصميم:** الإصلاح المقترح يجعل الدافع في تينانت 1 هو **حساب النظام 957 (محفظة 929، رصيد 173.0 MR_USDT)** — وهي نفس المحفظة التي **تستقبل** إيرادات الاشتراكات/الفواتير من user 1. أي تينانت آخر: حساب النظام إما رصيده 0 (تينانت 16) أو غير موجود أصلًا (يُنشأ تلقائيًا برصيد 0). هذا سؤال تمويل/أعمال يجب أن يُحسَم قبل إصلاح `idempotency_key`، لكنه **لا يمنع** إصلاح الدافع الآن.

---

## 1. إعادة التحقق من `disburse_monthly_pensions` (Step 1.1)

### 1.1 الكود الحالي بالحرف — `eppne-backend/app/domains/insurance/service.py:631-663`

```python
    async def disburse_monthly_pensions(self, tenant_id: int) -> int:
        """دفع المعاشات الشهرية لتينانت واحد (يتم استدعاؤها تلقائياً عبر جدولة).

        الطبقة (أ) فقط (عزل التينانت). منطق الصرف نفسه (sender_id=1، غياب
        idempotency_key، نوع last_payout_tx، فحص "دُفع هذا الشهر") لم يُلمَس عمدًا —
        راجع بند backlog `insurance-disburse-pensions-payout-logic-broken`.
        """
        pensions = await self.repo.list_active_pensions(tenant_id)
        count = 0
        for pension in pensions:
            if cast(int, pension.tenant_id) != tenant_id:  # فحص دفاعي (belt-and-suspenders)
                continue
            if pension.last_payout_tx:  # type: ignore
                last_payout_date = await self._get_payout_date(pension.last_payout_tx)  # type: ignore
                if last_payout_date and last_payout_date.month == datetime.utcnow().month:
                    continue
            finance = FinanceService(self.db, tenant_id)
            try:
                tx = await finance.transfer(
                    sender_id=1,
                    receiver_email=await self._get_user_email(pension.beneficiary_id, cast(int, pension.tenant_id)),  # type: ignore
                    currency="MR_USDT",
                    amount=pension.monthly_amount_mrusdt,  # type: ignore
                    notes=f"Pension payment for {pension.pension_type}"
                )
                await self.repo.update_pension(pension.id, last_payout_tx=tx)  # type: ignore
                count += 1
            except Exception:
                pass
        return count
```

### 1.2 الانحراف (drift) عن وصف 2026-09-16

| الوصف في بند 2026-09-16 | الواقع اليوم | الدليل |
|---|---|---|
| السطر `:626` | السطر `:650` (الدالة تبدأ :631) | `grep -n "sender_id=1"` |
| "تلف على كل pensions عبر كل التينانتس، بلا معامل tenant_id — بالتصميم" | **خطأ الآن:** الدالة تأخذ `tenant_id` وتقرأ `list_active_pensions(tenant_id)` (`repository.py:174-180`) + فحص دفاعي + `FinanceService(self.db, tenant_id)` | `git blame` → `44f1d0e` (Batch 0-A) |
| (ضمنيًا) الدالة تدفع فعليًا لكن من الحساب الخطأ | **لا تدفع شيئًا أصلًا:** `transfer()` بلا `idempotency_key` (معامل إجباري، `finance/service.py:64`) → `TypeError` مبلوع → `count=0` | `finance/service.py:58-70`؛ بند `insurance-disburse-pensions-payout-logic-broken` (PROGRESS_LOG ~:1031) |
| `sender_id=1` هاردكودد | **لم يتغيّر** | السطر 650 أعلاه |

ملاحظة: تصحيح مؤرَّخ لهذا الانحراف **موجود أصلًا** في PROGRESS_LOG.md أسفل بند [2026-09-16] (سطر ~4347، مضاف في Batch 0-A) — أي أن الانحراف موثَّق، لكن نص البند الأصلي (المقتبس في طلب الجلسة) لم يُحدَّث.

### 1.3 السلوك الفعلي لـ`sender_id=1` لو أُصلح `idempotency_key` بدون إصلاح الدافع

`FinanceService.transfer` يجلب محفظة المرسل عبر `get_or_create_wallet_for_update(sender_id)` المفلترة بـ`self.tenant_id` (`finance/service.py:34-39`):

- **تينانت 1:** `user_id=1` ينتمي لتينانت 1 → يسحب فعليًا من `wallets.id=39` (رصيد حقيقي 702.0). **هذا هو الخطر الحقيقي الوحيد.**
- **أي تينانت آخر X:** لا توجد محفظة لـuser 1 في X → تُنشأ محفظة ghost (user 1، تينانت X) برصيد 0 داخل `begin_nested()` → `InsufficientBalanceError` → rollback للـsavepoint (المحفظة لا تبقى) → يُبلَع. فشل آمن لكن صامت.

أي أن الوصف القديم "كل تينانت يسحب من user 1" لم يعد دقيقًا: بعد Batch 0-A الخطر محصور في **تينانت 1** فقط، والتينانتات الأخرى تفشل بصمت.

---

## 2. نقاط الاستدعاء والجدولة (Step 1.2)

| الفحص | النتيجة |
|---|---|
| `grep -rn "disburse_monthly_pensions"` على `eppne-backend` (Python) | استدعاء وحيد: `insurance/router.py:358` داخل `POST /insurance/admin/disburse-pensions` (`get_current_superuser`، `rate_limit(5/60s)`). الباقي: تعليقات في `tests/test_user_repository_get_by_id_audit.py`. |
| `beat_schedule` (`app/core/celery_config.py:41`) | 7 مهام مفعّلة/معلّقة: `saas.*` ×4، `agritech.*` ×3 (معلّقة)، `affiliate.clean_expired_links`، `academy.purge_old_camera_analyses`. **صفر pension/insurance.** |
| `grep -rln "pension"` على `app/tasks` و`app/core` | **صفر نتيجة** — لا توجد مهمة Celery مسجَّلة تستدعي الدالة. |
| APScheduler / `AsyncIOScheduler` / `aiocron` / `schedule.every` | **صفر نتيجة** في `app/`. (`crontab` يظهر فقط في `celery_config.py`.) |
| `k8s/` و`terraform/` (CronJob/schedule/disburse) | **صفر نتيجة.** |
| الفرونت إند `eppne-web` | `services/insurance.ts:592` يعرّف `disbursePensions()` (ويرسل `X-Tenant-ID` المُتجاهَل الآن)، لكن **صفر مكوّن يستدعيها** (`grep` على `.ts/.tsx`). |

**الخلاصة:** لا تغيير عن 2026-09-16 — نقطة استدعاء يدوية واحدة، غير مجدولة. ⚠️ الـdocstring الحالي يقول "يتم استدعاؤها تلقائياً عبر جدولة" — **هذا غير صحيح** (يُقترَح تصحيحه ضمن الـdiff).

---

## 3. محفظة `wallets.id=39` وتاريخ المعاملات (Step 1.3)

استعلامات حية على `eppne_db` (postgres:16، قاعدة `eppne_v2`):

| البند | القيمة |
|---|---|
| `wallets.id=39` | `user_id=1`، `tenant_id=1`، `balances={"MR_USDT": 702.0}`، `updated_at=2026-09-23 23:02:36` |
| `users.id=1` | `email=p_system_treasury@example.com`، `tenant_id=1`، **`is_system_account=false`** |
| محافظ user 1 | واحدة فقط (id=39) — صفر محافظ ghost في تينانتات أخرى |
| إجمالي معاملات المحفظة 39 | 165 (كلها تاريخيًا) |
| منذ 2026-09-16 | 72 معاملة، **كلها خارجة 39 → 929 (حساب النظام 957)، 1.0 MR_USDT لكل منها**، notes = `تجديد اشتراك REGTEST-FINBIND-*`/`REGTEST-TRIGREN-*` أو `دفع فاتورة INV-*` |
| آخر معاملة | `id=1037`، `2026-09-23 12:17:47` |
| معاملات `notes ILIKE '%pension%'` في **كل** جدول `transactions` | **0** |
| معاملات لـuser 1 خارج المحفظة 39 | 0 |
| **مطابقة الرصيد** | رصيد 2026-09-16 المسجَّل = 771.0 (قيس بعد أول 3 معاملات في ذلك اليوم). المعاملات بعد `14:15:09` = 69 × 1.0 = 69.0 → **771 − 69 = 702 ✓ مطابقة تامة.** وتطابق أيضًا قيمة Batch 0-A (710.0 في 2026-09-21) + 8 معاملات 2026-09-23 = 702 ✓ |
| `pension_records` | **0 صف إجمالًا** (Batch 0-A رأت 7 ACTIVE عبر تينانتين — يبدو أنها كانت في تينانتات throwaway 124–129 التي حُذفت في تنظيف تلك الجلسة) |

**الخلاصة:** لا نشاط pension إطلاقًا منذ 2026-09-16. الانخفاض كله من اختبارات REGTEST (المرتبطة بالبند المعروف "FINBIND test leaks user1 funds").
ملاحظة جانبية (غير مُحقَّقة، خارج النطاق): `wallets.updated_at` (23:02) أحدث من آخر معاملة (12:17) — تعديل رصيد/held بدون صف `transactions`. لا يمس المعاشات؛ مذكور للأمانة فقط.

---

## 4. `get_or_create_system_account` (Step 1.4)

`eppne-backend/app/core/system_account_service.py:10`:

```python
async def get_or_create_system_account(db: AsyncSession, tenant_id: int) -> User:
```

- يبحث عن `User` بـ`tenant_id` + `is_system_account=True`؛ إن لم يوجد ينشئه (`db.add` + `flush` + `refresh`) **بلا commit** — آمن داخل savepoint.
- يُرجع كائن `User` → نستخدم `cast(int, system_account.id)` كـ`sender_id` (نفس `affiliate/service.py:573-577` و`iot/service.py:217-219` حرفيًا).
- مستخدَم اليوم في 7 أماكن: academy، affiliate، iot، projects (كمستلم)، saas ×2، social ×2.

**هل هو drop-in نظيف هنا؟ نعم، بملاحظتين:**
1. **لا حاجة لاستدعائه داخل الحلقة بـ`pension.tenant_id`** (كما اقترح طلب الجلسة): بعد Batch 0-A الدالة لتينانت واحد، والفحص الدفاعي يضمن `pension.tenant_id == tenant_id` لكل صف يصل للتحويل. استدعاء واحد قبل الحلقة بـ`tenant_id` مكافئ منطقيًا وأنظف (نفس نمط iot: `FinanceService(self.db, tenant_id)` + `get_or_create_system_account(self.db, tenant_id)`).
2. **`get_db` لا يعمل commit تلقائي** (`core/database.py:45-51`)، والدالة لا تعمل commit إلا عبر `repo.update_pension` عند نجاح تحويل. لذلك لو أُنشئ حساب نظام جديد ولم ينجح أي تحويل → يُتراجع عنه عند إغلاق الجلسة. غير ضار (يُعاد إنشاؤه لاحقًا). ولتجنّب إنشائه بلا داعٍ حين لا توجد معاشات، الـdiff يستدعيه فقط إن وُجدت معاشات.

### 4.1 حالة حسابات النظام اليوم (مهم للتمويل)

| تينانت | حساب النظام | المحفظة | رصيد MR_USDT |
|---|---|---|---|
| 1 | 957 (`system+tenant-1@internal.eppne.local`) | 929 | **173.0** (تراكم إيرادات REGTEST المحوَّلة من user 1) |
| 16 | 956 | 931 | 0 |
| أي تينانت آخر | غير موجود (يُنشأ عند أول استدعاء) | — | 0 |

→ بعد الإصلاح + إصلاح `idempotency_key` لاحقًا: تينانت 1 سيدفع المعاشات من **نفس المحفظة التي تجمع إيرادات SaaS**؛ بقية التينانتات ستفشل بـ`InsufficientBalanceError` (مبلوع). **قرار تمويل صندوق المعاشات (من يغذّي حساب النظام؟ هل يُفصل صندوق معاشات مستقل؟) قرار أعمال للمستخدم** — مقترح توثيقه كشرط إضافي على بند `payout-logic-broken`، لا حسمه في هذه الجلسة.

---

## 5. ادعاء الـroadmap: 4 endpoints تأخذ `tenant.id` من الهيدر (Step 1.5)

**الحكم: قديم بالكامل (fully stale) — أُصلح في `44f1d0e` (Batch 0-A، commit بتاريخ 2026-09-22 09:08، مدفوع على origin/main).** تاريخ الـroadmap (2026-09-18) يسبق الإصلاح بـ4 أيام؛ نفس ظاهرة بند invitations.

| Endpoint | الموقع الحالي | مصدر التينانت اليوم | `git blame` لسطر التينانت | تحقق إضافي |
|---|---|---|---|---|
| `create_policy` | `router.py:24-38` | `tenant_id = cast(int, current_user.tenant_id)` (:31) | `44f1d0e` | لا `Header`/`get_current_tenant` في التوقيع |
| `review_claim` | `router.py:220-242` | `tenant_id = cast(int, current_user.tenant_id)` (:231) | `44f1d0e` | الـ`Header` الوحيد هو `Idempotency-Key`. الخدمة تفلتر `claim.tenant_id != tenant_id`. `88097be` (الدفع المزدوج) لم يلمس سطر التينانت. |
| `create_pension` | `router.py:278-293` | `tenant_id = cast(int, current_user.tenant_id)` (:285) → `pension_data["tenant_id"] = tenant_id` | `44f1d0e` | + فحص انتماء المستفيد (D2) في الخدمة |
| `create_employee_profile` | `router.py:366-381` | `tenant_id = cast(int, current_user.tenant_id)` (:373) → `profile_data["tenant_id"] = tenant_id` | `44f1d0e` | `service.py:673-674` يتحقق أن الموظف من نفس التينانت |

**علاقة بالجلسات السابقة المذكورة في الطلب:**
- `user-repository-get-by-id-audit` (2026-08-19، `dbc96a4`): أضاف `tenant_id` لاستدعاءات `get_by_id` داخل الخدمة فقط — **لم يغيّر مصدر التينانت في الـrouter**. ليس هو من أصلح هذا.
- `review_claim double-payment` (`88097be`، 2026-09-23): حارس حالة + قفل صف + مفتاح دفع حتمي — **لم يلمس مصدر التينانت** (blame يؤكد).
- **المُصلِح الفعلي:** Batch 0-A (`44f1d0e`) — 8 endpoints، مع regression دائم `tests/test_insurance_batch0a_tenant_isolation.py`.

**بقايا متعلقة (ليست ادعاء الـroadmap، ومعروفة مسبقًا):** 4 endpoints لا تزال تحقن `tenant: AcademyTenant = Depends(get_current_tenant)` لكن **لا تستخدمه** (`renew_subscription` :145، `get_my_claims` :208، `get_my_pensions` :299، `get_my_employee_profile` :387) + استيراد `Header` غير المستخدم للتينانت. موثَّقة كبند ⚪ `insurance-unused-tenant-header-dependencies`. ليست ثغرة عزل (القيمة لا تُقرأ).

---

## 6. الإصلاح المقترح — diff حرفي للمراجعة (لم يُطبَّق)

الملف: `eppne-backend/app/domains/insurance/service.py`

```diff
@@ imports (بعد سطر 24 تقريبًا)
 from app.core.entity_membership_service import EntityMembershipService
 from app.core.models import EntityMembershipRole
+from app.core.system_account_service import get_or_create_system_account
 from app.domains.insurance.models import (
@@ -631,23 +632,29 @@
     async def disburse_monthly_pensions(self, tenant_id: int) -> int:
-        """دفع المعاشات الشهرية لتينانت واحد (يتم استدعاؤها تلقائياً عبر جدولة).
+        """دفع المعاشات الشهرية لتينانت واحد (يدويًا عبر POST /insurance/admin/disburse-pensions؛ غير مجدولة).
 
-        الطبقة (أ) فقط (عزل التينانت). منطق الصرف نفسه (sender_id=1، غياب
-        idempotency_key، نوع last_payout_tx، فحص "دُفع هذا الشهر") لم يُلمَس عمدًا —
-        راجع بند backlog `insurance-disburse-pensions-payout-logic-broken`.
+        الدافع حساب النظام الخاص بالتينانت (get_or_create_system_account)، لا user_id=1.
+        باقي منطق الصرف (غياب idempotency_key، نوع last_payout_tx، فحص "دُفع هذا الشهر")
+        لم يُلمَس عمدًا — راجع بند backlog `insurance-disburse-pensions-payout-logic-broken`.
         """
         pensions = await self.repo.list_active_pensions(tenant_id)
+        if not pensions:
+            return 0
+        system_account = await get_or_create_system_account(self.db, tenant_id)
         count = 0
         for pension in pensions:
             if cast(int, pension.tenant_id) != tenant_id:  # فحص دفاعي (belt-and-suspenders)
                 continue
             if pension.last_payout_tx:  # type: ignore
                 last_payout_date = await self._get_payout_date(pension.last_payout_tx)  # type: ignore
                 if last_payout_date and last_payout_date.month == datetime.utcnow().month:
                     continue
             finance = FinanceService(self.db, tenant_id)
             try:
                 tx = await finance.transfer(
-                    sender_id=1,
+                    sender_id=cast(int, system_account.id),
                     receiver_email=await self._get_user_email(pension.beneficiary_id, cast(int, pension.tenant_id)),  # type: ignore
```

**قرارات تصميم ضمنية في الـdiff (تحتاج موافقتك):**
- **D1 — مكان الاستدعاء:** مرة واحدة قبل الحلقة بـ`tenant_id` (لا داخل الحلقة بـ`pension.tenant_id`) — مبرّر في §4. البديل الحرفي لطلبك (داخل الحلقة) مكافئ وظيفيًا لكن يكرر استعلامًا لكل معاش.
- **D2 — `if not pensions: return 0`:** إضافة صغيرة لتجنّب إنشاء حساب نظام لتينانت بلا معاشات. يمكن حذفها إن أردت أدنى تغيير ممكن.
- **D3 — الاستدعاء خارج `try/except Exception: pass`:** أي فشل في جلب/إنشاء حساب النظام يظهر كخطأ (500) بدل أن يُبلَع. متسق مع iot/affiliate.
- **D4 — النطاق:** الدافع فقط. **لا** `idempotency_key`، **لا** `last_payout_tx=tx.tx_hash`، **لا** `_get_payout_date`، **لا** إزالة `except: pass` — كلها في بند `payout-logic-broken`. **نتيجة مباشرة: بعد هذا الإصلاح وحده تبقى الدالة ترجع `count=0` ولا تحرّك أي فلوس** (TypeError لا يزال يُبلَع). هذا متوافق مع شرط الترتيب الموثَّق.
- **D5 — تصحيح الـdocstring** ("تلقائياً عبر جدولة" → "يدويًا، غير مجدولة") — تعديل نصي غير سلوكي.

---

## 7. خطة التحقق الحي المقترحة (لم تُنفَّذ)

**مشكلة جوهرية:** لأن `transfer()` يفشل بـ`TypeError` **قبل** قراءة `sender_id`، فالتحقق عبر HTTP وحده لا يستطيع إثبات من هو الدافع (قبل/بعد: `count=0`، صفر حركة فلوس في الحالتين). لذلك الخطة على مستويين:

### 7.1 مستوى الخدمة (الإثبات الأساسي) — spy على `FinanceService.transfer`
في اختبار pytest جديد (`tests/test_insurance_disburse_pensions_system_account.py`):
1. **إعداد throwaway:** تينانتان جديدان A وB (بنمط Batch 0-A)، مستخدم superuser في كل منهما، مستفيدان، ومعاشان ACTIVE في A + معاش ACTIVE في B.
2. `monkeypatch` لـ`FinanceService.transfer` بـspy يسجّل `kwargs` ويرفع استثناء (لمحاكاة الوضع الحالي دون تحريك فلوس).
3. **Assertions:**
   - `sender_id` لكل استدعاء == `id` حساب النظام لتينانت A، و**≠ 1**.
   - حساب النظام المستخدَم `tenant_id == A` و`is_system_account=True`.
   - استدعاء لتينانت B يستخدم حساب نظام B (عزل الدافع بين التينانتات).
   - تينانت بلا معاشات: `count=0` و**لا يُنشأ** حساب نظام (D2).
4. **Mutation test:** إعادة `sender_id=1` مؤقتًا → الاختبار يجب أن **يفشل**؛ ثم الإرجاع. (وأيضًا mutation على D1: تمرير تينانت خاطئ لـ`get_or_create_system_account` → فشل.)

### 7.2 مستوى HTTP (إثبات عدم الانحدار وعدم حركة الفلوس)
عبر `POST /insurance/admin/disburse-pensions` الحقيقي، قبل/بعد الإصلاح:
- لقطة أرصدة: `wallets.id=39` (702.0)، محفظة 929 (173.0)، محافظ حسابات نظام A/B، محافظ المستفيدين.
- عدد صفوف `transactions` + `users WHERE is_system_account`.
- **المتوقع قبل وبعد:** `200 {"count": 0}`، صفر تغيير في كل الأرصدة وعدد المعاملات، صفر محافظ ghost لـuser 1، `last_payout_tx` لم يتغير.
- **Belt-and-suspenders اختياري (يحتاج موافقة منفصلة):** تشغيل واحد في اختبار الخدمة فقط يمرّر `idempotency_key` عبر spy wrapper يستدعي `transfer` الأصلي، مع تمويل حساب نظام A بمبلغ صغير، لإثبات أن الفلوس تخرج فعليًا من محفظة حساب نظام A لا من 39. هذا يحرّك فلوسًا حقيقية في تينانت throwaway فقط، ويُنظَّف بعده.

### 7.3 التنظيف ومعايير الإغلاق
- حذف التينانتات/المستخدمين/المعاشات/المحافظ/المعاملات throwaway؛ مقارنة لقطة الجداول قبل/بعد **zero-diff**؛ `wallets.id=39 = 702.0` و929 = 173.0 في النهاية.
- الاختبار الجديد ×2 بلا تذبذب + suite insurance كاملة (`test_insurance_*`) + `test_user_repository_get_by_id_audit.py` (يذكر `disburse_monthly_pensions`). الفشلان المسبقان المعروفان (`test_insurance_get_user_and_get_user_email_all_three_call_paths`، `test_realestate_buy_fractional_ownership_invoice_ordering`) يُعاد تأكيدهما على HEAD نظيف إن ظهرا.
- ⚠️ شجرة العمل فيها تعديلات غير مُلتزَمة كثيرة في دومينات أخرى (git status)؛ `insurance/` نظيف حاليًا → الـcommit لاحقًا يجب أن يكون بـpathspec لملف `insurance/service.py` + ملف الاختبار فقط، مع `git show --stat` للتأكد.

---

## 8. بنود PROGRESS_LOG المتأثرة (للاقتراح فقط — لا كتابة)

- `finance-transfer-hardcoded-system-account-real-fund-risk` (الصف ~:270، 🟡 مُغلَق جزئيًا 3/4): الموضع الرابع هو هذا — يُغلَق بالكامل عند الإصلاح.
- بند [2026-09-16] `insurance-disburse-pensions-hardcoded-system-account` (~:4302) + التصحيح المؤرَّخ تحته (~:4347): إضافة سطر إغلاق مؤرَّخ.
- `insurance-disburse-pensions-payout-logic-broken` (~:1031): تحديث مؤرَّخ بأن شرط "قرار الدافع أولًا" تحقّق، + (اقتراح) إضافة شرط التمويل من §4.1.
- ادعاء الـroadmap (Batch 0) عن الـ4 endpoints: سطر تصحيح مؤرَّخ "stale — أُصلح في `44f1d0e`".
- **لا بنود جديدة مقترحة** (تم `grep` بالعَرَض: sender_id=1، disburse، header tenant — كلها مغطّاة ببنود قائمة).

---
---

# الجزء الثاني — التنفيذ والتحقق (بعد موافقة المستخدم على D1–D5 و§7 كاملًا)

## 9. تطبيق الـdiff (الخطوة 1)

طُبِّق **حرفيًا كما في §6** على `eppne-backend/app/domains/insurance/service.py` (9+ / 5−). `git diff` الفعلي:

```diff
@@ -23,6 +23,7 @@ from app.core.redis_client import redis_client
 from app.core.logging_conf import logger
 from app.core.entity_membership_service import EntityMembershipService
 from app.core.models import EntityMembershipRole
+from app.core.system_account_service import get_or_create_system_account
 from app.domains.insurance.models import (
@@ -629,13 +630,16 @@ class InsuranceService:
     async def disburse_monthly_pensions(self, tenant_id: int) -> int:
-        """دفع المعاشات الشهرية لتينانت واحد (يتم استدعاؤها تلقائياً عبر جدولة).
+        """دفع المعاشات الشهرية لتينانت واحد (يدويًا عبر POST /insurance/admin/disburse-pensions؛ غير مجدولة).
 
-        الطبقة (أ) فقط (عزل التينانت). منطق الصرف نفسه (sender_id=1، غياب
-        idempotency_key، نوع last_payout_tx، فحص "دُفع هذا الشهر") لم يُلمَس عمدًا —
-        راجع بند backlog `insurance-disburse-pensions-payout-logic-broken`.
+        الدافع حساب النظام الخاص بالتينانت (get_or_create_system_account)، لا user_id=1.
+        باقي منطق الصرف (غياب idempotency_key، نوع last_payout_tx، فحص "دُفع هذا الشهر")
+        لم يُلمَس عمدًا — راجع بند backlog `insurance-disburse-pensions-payout-logic-broken`.
         """
         pensions = await self.repo.list_active_pensions(tenant_id)
+        if not pensions:
+            return 0
+        system_account = await get_or_create_system_account(self.db, tenant_id)
         count = 0
@@ -647,7 +651,7 @@ class InsuranceService:
             try:
                 tx = await finance.transfer(
-                    sender_id=1,
+                    sender_id=cast(int, system_account.id),
```

## 10. ملف الاختبار الجديد (الخطوة 2)

`eppne-backend/tests/test_insurance_disburse_pensions_system_account.py` — 3 اختبارات، تينانتات throwaway خاصة (`REGTEST_PENSYS_*`) تُحذف كاملة في `finally`:

| # | الاختبار | ما يثبته |
|---|---|---|
| 1 | `test_disburse_sender_is_own_tenant_system_account_not_user_1` | spy على `FinanceService.transfer` (يسجّل kwargs ويرفع استثناء → صفر حركة أموال). تينانت A (معاشان) وتينانت B (معاش): كل `sender_id` ≠ 1 و== حساب نظام **نفس** التينانت (`tenant_id` صحيح، `is_system_account=True`)، `FinanceService.tenant_id` صحيح، المستلمون هم مستفيدو التينانت فقط، **وحساب A ≠ حساب B** (عزل الدافع). |
| 2 | `test_disburse_tenant_without_pensions_creates_no_system_account` | D2: تينانت C بلا معاشات → `count=0`، صفر استدعاء `transfer`، **صفر حساب نظام** (يُفحَص في نفس الجلسة فيرى حتى الصفوف المُفلَّشة بلا commit). |
| 3 | `test_disburse_real_money_moves_from_tenant_system_wallet_not_wallet_39` | §7.3 حركة أموال حقيقية في تينانت throwaway واحد: حساب نظام A مُموَّل بـ100، `transfer` **الحقيقي** مغلَّف بـwrapper يمرّر `idempotency_key` ويرجّع `tx.tx_hash` (**محاكاة داخل الاختبار فقط** لإصلاحي (1) و(2) في `payout-logic-broken`، غير مُصلَحين في الكود). النتيجة: `count=2`، محفظة حساب نظام A 100→80، كل مستفيد 0→10، صفّا `transactions` بـ`sender_id`=حساب نظام A و`from_wallet_id`=محفظته (≠39)، `last_payout_tx` = `TX-…`، **محفظة 39 ومحفظة 929 بلا تغيير**. |

**تعديل واحد على الخطة أثناء التنفيذ (بيئي):** التشغيل الأول فشل في اختبارَي 1 و3 داخل **fixture** إنشاء المستخدمين — `UserService.register` يكتب كاش المستخدم في Redis، وRedis الحي يرفض بيانات اعتماد التطبيق (`AuthenticationError: invalid username-password pair` — نفس انحراف كلمة سر Redis المعروف منذ 2026-09-24). مسار `disburse` نفسه لم يُنفَّذ أصلًا. الحل: إنشاء المستخدمين مباشرة بـORM (نفس حقول `get_or_create_system_account`، بلا `is_system_account`). تحقّقت أن مسار `disburse`/`transfer` لا يلمس Redis (`finance/service.py` يستخدم `EventBus` فقط في `invoice.paid` خارج `transfer`).

## 11. النتائج (الخطوة 3)

- التشغيل 1 (بعد تعديل الـfixture): **3 passed** (178s).
- بعد الـmutations والاستعادة: **3 passed** (242s).
- ضمن الـsuite الكامل: الثلاثة passed مرة ثالثة.

## 12. Mutation checks (الخطوة 4)

نسخة الإصلاح محفوظة في scratchpad (`service.fixed.py`) واستُعيدت بـ`cp` بعد كل mutation، مع `cmp` → **مطابقة بايت ببايت**.

**M1 — إعادة `sender_id=1`** (`grep` أكّد السطر 654 = `sender_id=1,`):
```
E                   assert 1 != 1                 ← اختبار 1: sender_id لسه user_id=1 الهاردكودد
E           assert 0 == 2                         ← اختبار 3: count=0 (user 1 بلا محفظة في تينانت A → رصيد غير كافٍ مبلوع)
FAILED ...::test_disburse_sender_is_own_tenant_system_account_not_user_1
FAILED ...::test_disburse_real_money_moves_from_tenant_system_wallet_not_wallet_39
2 failed, 1 passed
```
(اختبار 2 نجح كما هو متوقَّع — لا يتعلق بالدافع.) الاستعادة → `no sender_id=1 (restored)`.

**M2 (إضافي) — حذف `if not pensions: return 0`** (D2):
```
E           AssertionError: تينانت بلا معاشات لازم ما يتنشألوش حساب نظام (D2)
E           assert [14042] == []
1 failed
```
→ فحص D2 له معنى حقيقي. ملاحظة شفافية: المحاولة الأولى لـM2 لم تُطبَّق فعليًا (أمر `python` في Windows وجّه لـstub غير المفسِّر) فاختبرت كودًا غير مُعدَّل ونجحت — **لا تُحتسَب**؛ أُعيدت بمفسّر الـvenv وطُبِّقت فعليًا (`early return removed`) وفشلت كما يجب. الحساب 14042 كان مُفلَّشًا بلا commit فتُرُوجع عنه عند إغلاق الجلسة (مؤكَّد في لقطة zero-diff).

## 13. التحقق على مستوى HTTP قبل/بعد (الخطوة 5، §7.2)

**تعديل على الخطة (بيئي):** تشغيل `uvicorn` فشل عند الإقلاع (`Application startup failed`) لأن hook الإقلاع يتصل بـRedis المرفوض. إصلاح بيانات Redis خارج النطاق (بند مفتوح يحتاج قرارك)، فلم يُلمَس. البديل: نفس طلبات HTTP **داخل العملية** عبر `httpx.ASGITransport(app=fastapi_app)` — مسار كامل حقيقي (routing + `get_current_superuser` + `rate_limit` [يفشل مفتوحًا بلا Redis] + serialization)، بلا hook الإقلاع فقط. التوكن مُنشأ بـ`create_access_token` نفسها (`sub`/`sv`/`tenant_id`) بدل مسار login. المسار الصحيح `/api/insurance/admin/disburse-pensions` (أول محاولة على `/insurance/...` رجعت 404 — خطأ prefix في السكربت، ملفها معزول `http_evidence_invalid_404_wrong_prefix.txt` ولا يُحتسَب).

إعداد: تينانتان throwaway 222 (admin 14051 SUPER_ADMIN + معاشان 102/103) و223 (admin 14054 + معاش 104).

| | BEFORE (كود HEAD، `sender_id=1`) | AFTER (الإصلاح) |
|---|---|---|
| تينانت A | `HTTP 200 {"message":"Disbursed 0 pensions","count":0}` | `HTTP 200 {"message":"Disbursed 0 pensions","count":0}` |
| تينانت B | `HTTP 200 … "count":0` | `HTTP 200 … "count":0` |
| w39 / w929 | 702.0 / 173.0 → 702.0 / 173.0 | 702.0 / 173.0 → 702.0 / 173.0 |
| `transactions` (count / max id) | 200 / 1037 → 200 / 1037 | 200 / 1037 → 200 / 1037 |
| `wallets` الكلي / محافظ user 1 | 98 / 1 → 98 / 1 | 98 / 1 → 98 / 1 |
| حسابات النظام | `956:16,957:1` → نفسه | `956:16,957:1` → نفسه (الحساب المؤقت تُرُوجع عنه — لا commit لأن لا تحويل نجح، كما في §4) |
| `last_payout_tx` (102/103/104) | null → null | null → null |
| **UNCHANGED** | **True** | **True** |

→ متطابق تمامًا كما هو متوقَّع: `count=0` لحين إصلاح `payout-logic-broken` منفصلًا. تنظيف: `cleaned [222, 223]`.

## 14. §7.3 — حركة الأموال الحقيقية (الخطوة 6)

منفَّذ كاختبار 3 أعلاه (§10) في تينانت throwaway واحد، وهو **جزء دائم من ملف الـregression** (يُعاد في كل تشغيل، ويُنظَّف ذاتيًا). الأرقام: حساب نظام A 100→80، المستفيدان 0→10 لكل منهما، w39 وw929 بلا تغيير، `from_wallet_id` = محفظة حساب نظام A. ثلاث مرات passed.

## 15. الـregression suites (الخطوة 7)

الملفات: كل `tests/test_insurance_*.py` (6) + `test_realestate_insurance_savepoint.py` + `test_user_repository_get_by_id_audit.py`.

| التشغيل | النتيجة |
|---|---|
| على الإصلاح (مع الملف الجديد) | **31 failed, 10 passed, 1 xfailed** |
| على كود HEAD (`git show HEAD:…` مؤقتًا، بدون الملف الجديد) | **31 failed, 7 passed, 1 xfailed** |
| مقارنة مجموعتي `FAILED` (`diff`) | **IDENTICAL-FAILURE-SETS** — الفرق الوحيد +3 passed = الاختبارات الجديدة |

**تصنيف الـ31 (سبب جذري):**
- **26 مؤكَّدة آليًا: Redis `AuthenticationError`** داخل fixtures تستدعي `UserService.register` (`set_cached_user`) — بيئي. يشمل الفشل المسبق المعروف `test_insurance_get_user_and_get_user_email_all_three_call_paths`.
- **2: حراس بنيويون (`inspect.getsource`) قديمون** — `test_realestate_buy_fractional_ownership_invoice_ordering` (فشل مسبق معروف، `assert 1277 < 928`) و`test_tourism_sports_place_transfer_bid_invoice_ordering` (`assert 1964 < 1629`، نفس الفئة؛ لا يلمس insurance).
- **3 لم يلتقطها المحلّل الآلي** (أقسام pytest مدمجة: `test_list_active_pensions_…`، `test_get_policy_after_issuer_entity_deletion_…`، `test_arbitration_syndicates_register_affiliate_commission_…`) — كلها تستخدم `register` في fixtures، والأهم أنها **ضمن المجموعة المتطابقة مع HEAD**.

**الخلاصة:** صفر انحدار من هذا الإصلاح. لكن **لا يمكن اعتبار الـsuite "أخضر"** اليوم — معظم الاختبارات لا تصل أصلًا لكودها بسبب Redis؛ تغطيتها الحقيقية معلّقة حتى يُصلَح Redis.

## 16. التنظيف وzero-diff (الخطوة 8)

لقطة baseline قبل أي اختبار: عدد صفوف **كل** جداول `public` + w39/w929 + أقصى id لـ`transactions`/`users`/`wallets` + قائمة حسابات النظام.

**أول مقارنة بعد كل التشغيلات: ليست zero-diff** — +6 `academy_tenants`، +60 `users`، +60 `wallets`، +2 `property_units`، +2 `real_estate_developments`. التحقيق:
- **صفر** منها من اختبارات هذه الجلسة (`p_pensys*` = 0، `REGTEST_PENSYS*` = 0).
- كلها من **الاختبارات القديمة** في تشغيلَي الـsuite: الـfixture يعمل `register` (commit للمستخدم والمحفظة) ثم ينهار على Redis **قبل** دخول `try/finally` → التنظيف لا يعمل. (تينانتات `REGTEST_RCGUARD_*` 228–233، مستخدمو `p1audit_*`/`p_regtest_*`/`p_b0a_*` في تينانت 1، ووحدتان عقاريتان/مشروعان.) كل الصفوف `created_at` بين 06:56 و07:05 اليوم و`id` أكبر من أقصى baseline.
- حُذفت بمعاملة واحدة محمية (`ON_ERROR_STOP` + `DO` block يرفع استثناء ويتراجع لو أي عدد ≠ baseline): `DELETE 2 / 2 / 60 / 60 / 6` → `COMMIT`.

**المقارنة النهائية: `ZERO-DIFF`** — كل الجداول، w39 = **702.0**، w929 = **173.0**، `max(transactions.id)=1037`، `max(users.id)=13185`، `max(wallets.id)=12642`، حسابات النظام `956:16,957:1`. Redis: لا مفاتيح كُتبت (كل الكتابات رُفضت). سيرفر uvicorn خرج عند الإقلاع — لا عملية عالقة.

**ملاحظة منهجية (لا بند جديد):** نفس فئة `admin-kill-switch-regression-suite-side-effects` (مجموعات الانحدار الحية تترك آثارًا) — هنا بمُحفِّز محدد: fixtures تعمل commit قبل `try`. أي تشغيل للـsuite قبل إصلاح Redis سيسرّب نفس الصفوف.

## 17. حالة شجرة العمل

- مُعدَّل: `eppne-backend/app/domains/insurance/service.py` (الإصلاح فقط).
- جديد (untracked): `eppne-backend/tests/test_insurance_disburse_pensions_system_account.py`، وهذا التقرير.
- **صفر staging، صفر commit، صفر كتابة في PROGRESS_LOG.md.**
- ملفات evidence في scratchpad: `http_evidence.txt`، `suite_after.txt`، `suite_head.txt`، `snap_before.txt`/`snap_after.txt`، `mutation1.txt`/`mutation2.txt`.

---

# الجزء الثالث — الـstaging والـcommit (بانتظار الموافقة)

## 18. الـstaging (pathspec)

- قبل الـstaging: `git diff --cached --name-only` = **0 ملف** (لا شيء مُجهَّز مسبقًا).
- الأمر: `git add -- eppne-backend/app/domains/insurance/service.py eppne-backend/tests/test_insurance_disburse_pensions_system_account.py`
- `git diff --cached --stat`:
```
 eppne-backend/app/domains/insurance/service.py     |  14 +-
 ...t_insurance_disburse_pensions_system_account.py | 251 +++++++++++++++++++++
 2 files changed, 260 insertions(+), 5 deletions(-)
```
- `--numstat`: `9 5 service.py` / `251 0 test_…py` — **ملفّان بالضبط**، لا شيء آخر من الشجرة المتسخة.
- **diff الـservice.py المُجهَّز مطابق حرفيًا لـ§9** (14 سطر +/−). وتأكيد إضافي: محتوى blob الـindex == نسخة الإصلاح المُختبَرة (`service.fixed.py`) بعد توحيد نهايات الأسطر. الفرق البايتي الوحيد CRLF (شجرة العمل، `core.autocrlf=true`) مقابل LF (الـindex وHEAD كلاهما LF، صفر CR) — الـcommit سيكون LF مثل HEAD، بلا تغيير نهايات أسطر على مستوى الملف (numstat 9/5 يؤكد).
- ملف الاختبار: المحتوى الكامل في شجرة العمل (`eppne-backend/tests/test_insurance_disburse_pensions_system_account.py`، 251 سطر) — موصوف في §10.

## 19. رسالة الـcommit المقترحة (نصها بالإنجليزية كبقية رسائل المشروع)

```
fix(insurance): pay pensions from the tenant's system account, not hardcoded user_id=1

disburse_monthly_pensions() called finance.transfer(sender_id=1, ...) —
every pension would have been drawn from user 1's personal wallet
(wallets.id=39, tenant 1). This was the 4th and last position of
finance-transfer-hardcoded-system-account-real-fund-risk (commerce,
affiliate and iot were already fixed); that item is now fully closed (4/4).

The sender is now get_or_create_system_account(self.db, tenant_id),
fetched once before the loop (the function is single-tenant since
Batch 0-A, 44f1d0e), the same pattern as affiliate/iot. A tenant with no
active pensions returns 0 early, so no system account is created for
nothing. Docstring corrected: the function is manual-only, not scheduled.

Still count=0 by design: transfer() is called without its required
idempotency_key, and the TypeError is swallowed. That, last_payout_tx
storing the Transaction object, and the stuck "paid this month" check
stay in insurance-disburse-pensions-payout-logic-broken. The documented
ordering condition (decide the payer before fixing idempotency_key) is
now honored. Open precondition for that item: who funds each tenant's
system account (tenant 1's is also the SaaS revenue collector; others
hold 0).

Verification (live DB, throwaway tenants):
- New tests/test_insurance_disburse_pensions_system_account.py, 3/3 pass:
  spy asserts sender == own tenant's system account, never 1, and A != B;
  no-pensions tenant creates no system account; real transfer (test-only
  wrapper supplying idempotency_key) moves funds out of tenant A's system
  wallet, with wallets 39 and 929 unchanged.
- Mutations: restoring sender_id=1 fails (assert 1 != 1, count 0 == 2);
  removing the early return fails (system account created).
- HTTP before/after (in-process ASGI; uvicorn can't boot on current
  Redis auth drift): identical 200 count=0, zero balance/tx changes.
- Insurance + get_by_id audit suites: 31 failures, identical set on HEAD
  and on the fix (Redis auth in fixtures + 2 stale source guards); the
  only delta is the +3 new passes. Zero regression.
- DB zero-diff restored (wallet 39 = 702.0, wallet 929 = 173.0).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## 20-أ. الـcommit

✅ **`7d1ff0f5e21e716c14ca2bbe804972ddf229e08b`** — `fix(insurance): pay pensions from the tenant's system account, not hardcoded user_id=1` — بالرسالة الحرفية في §19. `git show --stat HEAD`: ملفّان بالضبط (`service.py` 14 +/−، ملف الاختبار 251+). الفهرس فارغ بعده. **لم يُدفع (no push).**

## 21. مسودة PROGRESS_LOG.md — diff معزول بالـhunks (بانتظار الموافقة، لم يُجهَّز)

**التقنية:** نسخة احتياطية من شجرة العمل (`PROGRESS_LOG.pre-edit.md` في scratchpad) → 4 تعديلات بالـEdit → `git diff -U3` كامل (5 hunks) → سكربت يُسقط الـhunk المسبق غير المُلتزَم (`@@ -4626,4 +4632,673 @@` — إلحاق 670 سطرًا من جلسات أخرى في آخر الملف) ويُبقي 4 → `git apply --cached --check` = **OK**، والفهرس بقي فارغًا (0 ملف).
- ملف الـpatch المعزول: **`.claude/reports/insurance-disburse-pensions-progress-log-isolated.patch`** (numstat: `8 2 PROGRESS_LOG.md`؛ السياق كبير لأن أسطر الجدول طويلة).
- 4 hunks = 4 تعديلات بالضبط:

| # | hunk | الموضع | النوع | بند §8 |
|---|---|---|---|---|
| 1 | `@@ -267,7 +267,7 @@` | السطر 270 — صف `finance-transfer-hardcoded-system-account-real-fund-risk` | تعديل في مكانه (1−/1+) | إغلاق 4/4 |
| 2 | `@@ -1028,7 +1028,7 @@` | السطر 1031 — صف `insurance-disburse-pensions-payout-logic-broken` | تعديل في مكانه (1−/1+) | تحديث مؤرَّخ + شرط التمويل |
| 3 | `@@ -1087,6 +1087,10 @@` | بعد السطر 1088 — كتلة "إغلاق مؤرَّخ" أسفل جدول الـBacklog (نمط invitations/invoicing/saas) | إضافة سطرين (+ فراغان) | إغلاق 4/4 (سطر) + تصحيح الخارطة |
| 4 | `@@ -4346,6 +4350,8 @@` | بعد السطر 4347 — بند `[2026-09-16]` بعد تصحيح 09-21 | إضافة سطر (+ فراغ) | تحديث مؤرَّخ لبند 2026-09-16 |

### 21.1 — hunk 1 (السطر 270): التغيير فقط

**أُضيف في نهاية خلية الوصف** (بعد "الباج الجديد لم يُستغل بعد."):
> **✅ الموضع الرابع [2026-09-24، commit `7d1ff0f`]:** `disburse_monthly_pensions` (`insurance/service.py:654` حاليًا) بقت تدفع من `get_or_create_system_account(self.db, tenant_id)` — راجع سطر الإغلاق المؤرَّخ أسفل الجدول.

**خلية الحالة:**
- قبل: `🟡 **مُغلَق جزئيًا (3 من 4 مواضع)، الجزء المتبقي (`insurance/service.py:626`) موثَّق كبند منفصل تحت**`
- بعد: `✅ **مُغلَق بالكامل (4 من 4 مواضع) [2026-09-24، commit `7d1ff0f`]** (كان: 🟡 مُغلَق جزئيًا 3 من 4)`

**خلية المراجع:** أُضيف `.claude/reports/insurance-disburse-pensions-hardcoded-system-account-session-log.md` في آخرها.

### 21.2 — hunk 2 (السطر 1031): التغيير فقط

**أُضيف في نهاية خلية الوصف** (بعد "...فقط بسبب العطل (1)."، قبل خلية الحالة — **خلية الحالة 🔴 لم تتغيّر**):
> **تحديث مؤرَّخ [2026-09-24] — شرط الترتيب تحقّق:** قرار الدافع حُسم ونُفِّذ في commit `7d1ff0f` (حساب نظام التينانت عبر `get_or_create_system_account`، السطر 654 حاليًا؛ صفر `sender_id=1`)، فإصلاح `idempotency_key` لم يعد يسحب من محفظة `user_id=1`. الأعطال (1)–(3) أعلاه **لم تُلمَس** — الدالة لا تزال ترجع `count=0` (مؤكَّد حيًا عبر HTTP قبل/بعد). **⚠️ شرط مسبق جديد قبل إغلاق هذا البند — قرار أعمال (مصدر التمويل):** من يغذّي حساب نظام كل تينانت؟ حساب نظام تينانت 1 (user 957، محفظة 929، 173.0 MR_USDT) هو **نفسه جامع إيرادات SaaS** (يستقبل اشتراكات/فواتير user 1)، فبعد إصلاح (1) ستُدفع معاشات تينانت 1 من الإيرادات؛ حساب تينانت 16 رصيده 0، وبقية التينانتات بلا حساب نظام (يُنشأ برصيد 0 عند أول صرف → `InsufficientBalanceError` مبلوع). هل يُفصل صندوق معاشات مستقل؟ يُحسَم قبل إصلاح (1). تفاصيل: `.claude/reports/insurance-disburse-pensions-hardcoded-system-account-session-log.md` §4.1.

### 21.3 — hunk 3 (بعد السطر 1088): سطران جديدان

> **✅ إغلاق مؤرَّخ [2026-09-24] — `finance-transfer-hardcoded-system-account-real-fund-risk` (الصف `[2026-08-24]` أعلاه): مُغلَق بالكامل 4/4 (commit `7d1ff0f`)، ويُغلِق معه `insurance-disburse-pensions-hardcoded-system-account` (بند `[2026-09-16]` أدناه — نفس الموضع تحت اسم تتبُّع أقدم).** جلسة `insurance-disburse-pensions-hardcoded-system-account` (`.claude/reports/insurance-disburse-pensions-hardcoded-system-account-session-log.md`). الموضع الرابع والأخير: `InsuranceService.disburse_monthly_pensions` كانت تنادي `finance.transfer(sender_id=1, ...)` → الآن `get_or_create_system_account(self.db, tenant_id)` مرة واحدة قبل الحلقة (الدالة لتينانت واحد منذ Batch 0-A `44f1d0e`) + `return 0` مبكر لتينانت بلا معاشات (لا يُنشأ حساب نظام بلا داعٍ) + تصحيح الـdocstring (يدوية، غير مجدولة). **التحقق:** اختبار دائم جديد `tests/test_insurance_disburse_pensions_system_account.py` (3 passed: spy يثبت الدافع = حساب نظام نفس التينانت لا 1، وA≠B؛ تينانت بلا معاشات لا يُنشئ حسابًا؛ تحويل حقيقي في تينانت throwaway يُخرج الفلوس من محفظة حساب نظامه ومحفظتا 39/929 بلا تغيير)؛ mutations: إعادة `sender_id=1` تُفشِل (`assert 1 != 1`)، وحذف الـ`return` المبكر يُفشِل؛ HTTP قبل/بعد متطابق (`200 count=0`، صفر حركة — ASGI داخل العملية لأن `uvicorn` لا يقلع بسبب انحراف كلمة سر Redis)؛ suites insurance + `get_by_id_audit`: 31 فشلًا **بمجموعة متطابقة على HEAD وعلى الإصلاح** (Redis في fixtures + حارسان بنيويان قديمان)، الفرق الوحيد +3 passed؛ zero-diff (محفظة 39 = 702.0، 929 = 173.0). **لا يزال `count=0`** حتى يُصلَح `insurance-disburse-pensions-payout-logic-broken` (تحديث مؤرَّخ على صفه أعلاه: شرط الترتيب تحقّق + شرط تمويل جديد).

> **✅ تصحيح مؤرَّخ [2026-09-24] — خارطة الطريق الرئيسية (`eppne-master-roadmap-1000-and-smart-city.md`، 2026-09-18، خارج الريبو في Downloads)، الدفعة 0 — بندا `insurance`: معلومة قديمة وقت كتابة الخارطة.** (أ) "`insurance` — باقي الـ4 endpoints (`create_policy`, `review_claim`, `create_pension`, `create_employee_profile`) تستخدم `tenant.id` من الهيدر": **أُصلحت الأربعة في `44f1d0e`** (Batch 0-A، commit 2026-09-22) — كلها الآن `tenant_id = cast(int, current_user.tenant_id)` (`insurance/router.py` :31، :231، :285، :373؛ `git blame` لكل سطر = `44f1d0e`). **ليس** أثرًا جانبيًا لـ`user-repository-get-by-id-audit` (2026-08-19، خدمة فقط) ولا لـ`88097be` (الدفع المزدوج، لم يلمس سطر التينانت). البقايا الوحيدة: 4 endpoints تحقن `get_current_tenant` ولا تستخدمه — بند ⚪ `insurance-unused-tenant-header-dependencies` القائم، ليست ثغرة عزل. (ب) "`insurance.disburse_pensions` يتجاهل التينانت ويصرف لكل المستأجرين عالميًا": **أيضًا قديم** — أُصلح في نفس `44f1d0e` (`disburse_monthly_pensions(tenant_id)`)، والدافع أُصلح الآن في `7d1ff0f`. ملف الخارطة نفسه (نسختان متطابقتان) **لم يُعدَّل**.

### 21.4 — hunk 4 (بعد السطر 4347): سطر جديد

> **✅ إغلاق مؤرَّخ [2026-09-24] — سطر جديد؛ النص أعلاه لم يُعدَّل:** مُغلَق (commit `7d1ff0f`). `sender_id=1` استُبدل بـ`get_or_create_system_account(self.db, tenant_id)` (السطر 654 حاليًا). **انحراف مقصود عن "الحل المتوقَّع" أعلاه:** الاستدعاء **مرة واحدة قبل الحلقة** بـ`tenant_id` لا "داخل الحلقة لكل `pension.tenant_id`" — لأن الدالة لم تعد تلف على كل التينانتات منذ Batch 0-A (`44f1d0e`)، والفحص الدفاعي يضمن `pension.tenant_id == tenant_id` لكل صف يصل للتحويل (مكافئ وظيفيًا). + `return 0` مبكر لتينانت بلا معاشات. تحقق حي لـ2026-09-24: صفر جدولة (beat/APScheduler/k8s/فرونت إند)، صفر معاملة pension في كل `transactions`، `pension_records` فارغ، محفظة 39 = 702.0 (مطابقة تامة: 771 − 69 معاملة `REGTEST` بـ1.0). التفاصيل والتحقق: سطر الإغلاق المؤرَّخ لـ`finance-transfer-hardcoded-system-account-real-fund-risk` (أسفل جدول الـBacklog) و`.claude/reports/insurance-disburse-pensions-hardcoded-system-account-session-log.md`.

### 21.4-ب — hunk 5 (بانر الحالة، بعد السطر 15) — أُضيف بموافقة المستخدم لاحقًا

> **✅ تحديث [2026-09-24] — شرط الترتيب أعلاه تحقّق:** قرار الدافع حُسم في commit `7d1ff0f` — `sender_id=1` استُبدل بحساب نظام التينانت (`get_or_create_system_account`، `insurance/service.py:654`)، فإصلاح `idempotency_key` لم يعد يسحب من محفظة `user_id=1`. الصرف لا يزال `count=0` حتى يُصلَح `insurance-disburse-pensions-payout-logic-broken`، الذي أُضيف له شرط مسبق جديد: قرار مصدر تمويل حسابات النظام (راجع صفه في جدول الـBacklog).

**الـstaging:** أُعيد بناء الـpatch المعزول (6 hunks في `git diff` → أُسقط `@@ -4626,4 +4634,673 @@` المسبق → **5 hunks**: `-14,6` + `-267,7` + `-1028,7` + `-1087,6` + `-4346,6`)، وحُدِّث الملف `.claude/reports/insurance-disburse-pensions-progress-log-isolated.patch`، ثم `git apply --cached` → `git diff --cached --numstat` = `10 2 PROGRESS_LOG.md`. **الباقي غير المُجهَّز** = `@@ -4634,4 +4634,673 @@` (670+/1−)، ومحتوى أسطره +/− **مطابق حرفيًا** لـdiff الـPROGRESS_LOG المسبق المحفوظ قبل أي تعديل (`progress_preexisting.diff`).

**ملف الخارطة (Downloads):** طُبِّق نمط invitations على السطرين 23 و24 (شطب `~~…~~` للنص القديم في خليتي الوضع والإجراء + تصحيح مؤرَّخ بالخط العريض). النسخة `(1)` مُزامَنة بالنسخ. sha1 قبل: `34db37e7…` للنسختين؛ بعد: **`a144b8d3…` للنسختين (متطابقتان)**، 160 سطرًا دون تغيير في العدد.

### 21.4-ج — commits الجلسة (ملخص نهائي)

| # | commit | المحتوى | `--stat` |
|---|---|---|---|
| 1 | `7d1ff0f5e21e716c14ca2bbe804972ddf229e08b` | `fix(insurance): pay pensions from the tenant's system account, not hardcoded user_id=1` | `service.py` 14 +/− (9+/5−)، `tests/test_insurance_disburse_pensions_system_account.py` +251 |
| 2 | `7bfc9f1e1a832bb4f8ba03316f5aaf1d828afa3f` | `docs: close finance-transfer hardcoded system account (4/4, 7d1ff0f) — …` | `PROGRESS_LOG.md` 10+/2− (5 hunks معزولة؛ الذيل المسبق 670+/1− بقي غير مُجهَّز وغير مُلتزَم) |
| 3 | commit هذا التقرير + `insurance-disburse-pensions-progress-log-isolated.patch` (دليل) | `docs: add session report for insurance disburse-pensions hardcoded system account` | — (الـhash يُذكر في رد الجلسة؛ لا يمكن تضمين hash commit داخل نفسه) |

**لم يُنفَّذ أي push.** خارج الريبو: نسختا الخارطة في Downloads (sha1 `a144b8d3…` للاثنتين).

### 21.5 — ما لم يُلمَس عمدًا (قرارك) — [حُسم لاحقًا: البانر أُضيف (hunk 5)، والخارطة عُدِّلت]

- **بانر الحالة أعلى الملف** (سطر 15، "⚠️ تحذير ترتيب الإصلاح" يذكر `sender_id=1` في `:638` كمفتوح) — لم يُعدَّل لأنه خارج §8 المعتمد. أصبح قديمًا جزئيًا؛ هل يُضاف له سطر "تحقّق [2026-09-24]"؟
- **ملف الخارطة في Downloads** (نسختان متطابقتان، سطرا 23 و24) — لم يُعدَّل (خارج الريبو). سابقة invitations: شُطب النص وأُضيف تحديث بعد سؤال المستخدم عن أي نسخة.

## 22. ملاحظة لجلسة قادمة (لا بند الآن — بطلب المستخدم)

انحراف بيانات اعتماد Redis **ثبت أنه يسبّب تلوّثًا حقيقيًا في قاعدة البيانات أثناء الاختبارات** (6 تينانتات + 60 مستخدم + 60 محفظة + 4 صفوف عقارية تسرّبت في تشغيلين ونُظِّفت يدويًا، §16) — لا مجرد إزعاج NOAUTH شكلي، ويمنع أيضًا إقلاع `uvicorn`. هذا يرفع الأولوية العملية لـ`redis-password-rotation-not-durable` — مقترح رفع أولويته في أول جلسة تلمس هذه المنطقة (مؤجَّل مرة أخرى الليلة بقرار المستخدم).
