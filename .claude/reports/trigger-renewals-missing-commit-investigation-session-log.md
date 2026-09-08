# تحقيق read-only: تأكيد `backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`

**النطاق:** فحص حي بحت — **صفر تعديل كود موجود**. الملف الوحيد المُضاف
هذه الجلسة: `eppne-backend/tests/test_trigger_renewals_endpoint_missing_commit.py`
(اختبار جديد، لا يلمس أي كود إنتاج). تم التأكد بـ `git status` إن كل
الملفات الأخرى الظاهرة كـ `M` (معدَّلة) كانت معدَّلة بالفعل *قبل* بداية
هذه المحادثة (نفس القائمة موجودة في snapshot أول رسالة) — لا علاقة لها
بهذه الجلسة.

**البند المستهدف:** `PROGRESS_LOG.md` سطر 2841،
`backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`
(🔴 أولوية عالية، مُكتشَف 2026-09-08 كملاحظة جانبية أثناء
`financeservice-tenant-binding-fix-session-log.md` §3، **غير مؤكَّد حيًا
بعد لهذا الـendpoint تحديدًا** وقت فتح البند).

---

## 1) الكود كاملاً — الـendpoint

`app/domains/saas/router.py:265-275`:

```python
@router.post("/admin/trigger-renewals")
@rate_limit(max_requests=5, window_seconds=300)
async def trigger_renewals(
    tenant_id: Optional[int] = Query(None, description="معرف المستأجر (اختياري)"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    # نمرر tenant_id=0 مؤقتاً، ثم نمرر target_tenant
    service = SaaSControlService(db, 0)
    results = await service.trigger_renewals(tenant_id)
    return {"message": "تم تشغيل مهمة تجديد الاشتراكات بنجاح", "results": results}
```

**صفر `await db.commit()` في جسم الدالة كله.** `db` جاي من
`Depends(get_db)` (`app/core/database.py:45-51`):

```python
async def get_db():
    """يُستخدم لحقن الجلسة في مسارات الـ API وإغلاقها بأمان بعد انتهاء الطلب"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

`get_db()` نفسها **بلا commit تلقائي** — `session.close()` فقط في
`finally`. أي ترانزاكشن معلَّقة (flush بلا commit) بترولباك ضمنيًا وقت
الإغلاق (سلوك SQLAlchemy الافتراضي).

---

## 2) الكود كاملاً — `trigger_renewals` (service) وما حولها

`app/domains/saas/service.py:610-621`:

```python
    # ==========================================
    # 8. دوال إدارية (Admin)
    # ==========================================
    async def get_tenant_subscriptions_admin(
        self, tenant_id: int, skip: int = 0, limit: int = 20
    ) -> PaginatedResponse[TenantSubscriptionResponse]:
        return await self.repo.get_tenant_subscriptions(tenant_id, skip, limit)

    async def trigger_renewals(self, tenant_id: Optional[int] = None):
        """تشغيل مهمة تجديد الاشتراكات يدوياً (للمشرفين)."""
        target = tenant_id if tenant_id is not None else self.tenant_id
        return await self.process_auto_renewals(target)
```

`trigger_renewals` سطرين فقط — تحديد `target` ثم استدعاء
`process_auto_renewals(target)` مباشرة، بلا أي `commit()`. **صفر منطق
DB خاص بها هي نفسها** — كل الكتابة الفعلية جوّه `process_auto_renewals`.

---

## 3) مقارنة دقيقة مع `process_auto_renewals_task`

`app/tasks/saas_tasks.py:62-75`:

```python
try:
    async def _run():
        async with SessionLocal() as db:  # ✅ استخدام SessionLocal
            service = SaaSControlService(db, 0)
            results = await service.process_auto_renewals(tenant_id=None)
            await db.commit()          # 👈 هنا بالضبط، سطر 75
            ...
```

الـ`commit()` هنا موجود **مباشرة بعد** استدعاء `service.process_auto_renewals(...)`
(سطر 74)، **خارج** أي حلقة أو معالجة نتائج — قبل أي كود تحليل/تسجيل
لاحق (`total = len(results)` إلخ في السطور اللي بعده).

**هل نفس الموضع منطقي في الراوتر؟** نعم بالضبط — نفس البنية حرفيًا:
`router.py` بيستدعي `service.trigger_renewals(tenant_id)` (سطر 274) ثم
مباشرة بيبني الـresponse dict (سطر 275). الموضع المكافئ المنطقي لـ
`db.commit()` لو كان موجودًا كان هيبقى **بين السطرين 274 و275** —
تمامًا نفس العلاقة البنيوية بين سطر 74 وسطر 75 في `saas_tasks.py`. هذا
الموضع غائب كليًا في `router.py` — **صفر أي شكل من `commit()` في الملف
كله لهذا المسار.**

| | `saas_tasks.py` (Celery) | `router.py` (`POST /admin/trigger-renewals`) |
|---|---|---|
| استدعاء العملية | `service.process_auto_renewals(tenant_id=None)` (سطر 74) | `service.trigger_renewals(tenant_id)` → `process_auto_renewals(target)` داخليًا (سطر 274) |
| `commit()` خارجي بعده | ✅ `await db.commit()` (سطر 75) | ❌ غير موجود إطلاقًا |
| نوع الجلسة | `SessionLocal()` (= `AsyncSessionLocal`) عبر `async with` صريح، مُتحكَّم بها يدويًا في الـtask | `AsyncSessionLocal()` عبر `Depends(get_db)` — نفس الكائن، لكن دورة حياتها محكومة بـ`get_db()` (فتح → yield → `close()` بلا commit) |

---

## 4) هل فيه فرع تاني (غير PAST_DUE) بيعاني من نفس القصور؟

`process_auto_renewals` (`service.py:265-333`) فيها 3 فروع داخل اللوب
على كل اشتراك مستحق:

### فرع SUCCESS (سطر 282-317) — **آمن، بيعمل commit خاص بيه**

```python
payer_id = await self._get_tenant_admin_id(sub_tenant_id)
system_account = await get_or_create_system_account(self.db, sub_tenant_id)
finance = FinanceService(self.db, sub_tenant_id)
async with self.db.begin_nested():
    tx = await finance.transfer(...)                    # سطر 291
    await self.repo.update_subscription(..., status="ACTIVE", ...)   # سطر 300
    await self._generate_invoice(...)                    # سطر 308

await self.db.commit()                                   # 👈 سطر 314 — هنا بالضبط
results.append({"subscription_id": ..., "status": "SUCCESS", "tx_hash": tx.tx_hash})
```

`async with self.db.begin_nested()` بيفتح **SAVEPOINT** متداخلة جوّه
الترانزاكشن الخارجي (مش commit مستقل بحد ذاته — `begin_nested` بترفع
الـsavepoint لما تخرج بنجاح، لكن الترانزاكشن الخارجي يفضل معلَّقة). لكن
**السطر اللي بعدها مباشرة (314) بيعمل `self.db.commit()` صريح على
الترانزاكشن الخارجي نفسها** — يعني فرع SUCCESS **مش معلَّق على أي
commit خارجي إطلاقًا**؛ بيحفظ نفسه بنفسه فور نجاحه، بغض النظر عن مين
استدعى `process_auto_renewals` (task ولا router). **لا يعاني من نفس
مشكلة PAST_DUE.**

بخصوص سؤال "`pay_invoice` جوّه `transfer()` عندها `begin_nested()`/
commit خاصة بيها؟" — `pay_invoice` (دالة منفصلة تمامًا، غير مستخدَمة في
مسار `process_auto_renewals` إطلاقًا؛ التوليد هنا عبر `_generate_invoice`
مش `pay_invoice`) لها نفس نمط `begin_nested()` + `commit()` صريح خاص
بيها (موثَّق ومختبَر في `financeservice-tenant-binding-fix-session-log.md`
§3، `test_pay_invoice_same_tenant_still_works_after_removing_self_finance`)
— **غير ذات صلة مباشرة بمسار `trigger_renewals` أصلاً**، لكن نفس النمط:
كل عملية مالية في `SaaSControlService` بتعمل `commit()` خاص بيها **إلا**
فرع `except InsufficientBalanceError`.

### فرع `except InsufficientBalanceError` → PAST_DUE (سطر 319-327) — **الوحيد المعطوب**

```python
except InsufficientBalanceError:
    await self.repo.update_subscription(
        cast(int, sub.id),
        sub_tenant_id,
        status="PAST_DUE",
        grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
    )
    results.append({"subscription_id": cast(int, sub.id), "status": "PAST_DUE"})
    logger.warning(...)
```

`repo.update_subscription` (`repository.py:270-285`):

```python
async def update_subscription(self, subscription_id: int, tenant_id: int, **kwargs) -> TenantSubscription:
    await self.db.execute(update(TenantSubscription)...)
    await self.db.flush()      # 👈 flush فقط، صفر commit
    subscription = await self.get_subscription(subscription_id, tenant_id)
    ...
    return subscription
```

**`flush()` بس** — لا `begin_nested()` ولا `commit()` خاص بها إطلاقًا.
هذا الفرع بيقع بالكامل خارج أي savepoint (`begin_nested` بتاعة السطر
290 كانت خرجت بالفعل — بالإلغاء التلقائي — وقت رمي `InsufficientBalanceError`
جوّها). التحويل لـPAST_DUE بيتم فقط على مستوى الـsession/الترانزاكشن
الخارجية المعلَّقة، ومعتمد **كليًا** على `commit()` خارجي بعد رجوع
`process_auto_renewals()` بالكامل.

### فرع `Exception` العام → FAILED (سطر 329-331) — **آمن، صفر كتابة DB**

```python
except Exception as e:
    logger.error(...)
    results.append({"subscription_id": cast(int, sub.id), "status": "FAILED", "error": str(e)})
```

صفر أي استدعاء `repo.*` أو DB — مجرد تسجيل في `results` (ذاكرة فقط).
لا يحتاج `commit()` أصلاً.

**الخلاصة لهذا البند:** فرع `except InsufficientBalanceError`
(PAST_DUE) هو **الوحيد** من بين الثلاثة اللي بيعتمد على commit خارجي
غائب في مسار الراوتر. SUCCESS آمن بذاته، FAILED لا يكتب شيء.

**ملاحظة جانبية مهمة اكتُشفت أثناء التحليل (توثيقية، غير مطلوبة
للتحقق لكن تُغيّر موثوقية إعادة الإنتاج):** لو حصل SUCCESS **لاشتراك
تاني بعد** PAST_DUE في نفس تشغيلة اللوب (نفس الاستدعاء)، الـ`self.db.commit()`
بتاعة السطر 314 هتُثبّت الترانزاكشن الخارجي **كلها**، بما فيها أي
`flush()` معلَّق من PAST_DUE سابق في نفس اللوب — يعني الباج **مش
حتمي 100%** لو فيه SUCCESS لاحق في نفس الاستدعاء، لكنه حتمي لو كان
PAST_DUE هو آخر حدث كتابة (أو الوحيد) في الاستدعاء. الاختبار الحي تحت
استخدم اشتراك باهظ واحد فقط (بلا أي اشتراك SUCCESS مصاحب) لضمان نتيجة
حاسمة وغير مشروطة بترتيب اللوب.

---

## 5) الاختبار الحي — إثبات فعلي، DB حقيقية `eppne_db`، صفر mock

**الملف الجديد:** `eppne-backend/tests/test_trigger_renewals_endpoint_missing_commit.py`

**منهجية الاستدعاء:** استدعاء دالة الراوتر الفعلية `trigger_renewals`
(نفس الكائن المسجَّل تحت `POST /admin/trigger-renewals`) مباشرة، بجلسة
DB مستقلة (`AsyncSessionLocal()`) تُفتح وتُغلق بنفس **بالضبط** نمط
`get_db()` الحقيقي (فتح → استدعاء → `close()` في `finally`، بلا أي
commit إضافي من الاختبار). تم تجاوز طبقة ASGI/HTTP الكاملة (`httpx`)
عمدًا لتفادي سحب `lifespan` (تهيئة Redis، فهارس Mongo) غير ذات الصلة
بالتحقيق — لكن هذا **نفس منطق الـendpoint الفعلي حرفيًا** بلا أي فرق
في دورة حياة الجلسة أو ترتيب الاستدعاءات.

**السيناريو:** اشتراك حقيقي واحد تحت تينانت 1، `next_billing_date` في
الماضي، خطة باهظة عمدًا (999999.00 MR_USDT) لضمان `InsufficientBalanceError`
→ PAST_DUE (نفس السيناريو المستخدَم ومؤكَّد سابقًا في
`financeservice-tenant-binding-fix-session-log.md` §3، لكن **بلا** أي
`db.commit()` إضافي بعد الاستدعاء هذه المرة).

**نتيجة التشغيل الفعلي:**

```
tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_loses_past_due_write_silently PASSED
```

**التفاصيل المؤكَّدة داخل الاختبار (assertions حقيقية ضد DB حي):**

| | القيمة |
|---|---|
| رد الـAPI الفعلي (نتيجة استدعاء `trigger_renewals(...)`) | `{"subscription_id": <id>, "status": "PAST_DUE"}` ✅ (كما هو متوقَّع من منطق الكود) |
| حالة الاشتراك في الـDB (جلسة مستقلة جديدة بعد إغلاق جلسة "الطلب") | `status == "ACTIVE"` (**لم يتغيّر لـ PAST_DUE**) |
| `grace_period_end_date` في الـDB | `None` (لم يُضرب رغم إن الكود ضربه في الذاكرة قبل الرولباك) |

**الإثبات حاسم:** الـAPI يرجّع نجاحًا ظاهريًا (`PAST_DUE` في الـresponse)
بينما التغيير الفعلي في قاعدة البيانات **ضاع بالكامل** — بالضبط السيناريو
المتوقَّع في `PROGRESS_LOG.md` سطر 2867-2876 وقت فتح البند، **الآن مؤكَّد
حيًا لأول مرة** (لم يكن مؤكَّدًا حيًا سابقًا — كان توقعًا كوديًا فقط،
موثَّق صراحة كـ"غير مؤكَّد حيًا بعد لهذا الـendpoint تحديدًا").

---

## 6) خلاصة الإجابات على الأسئلة الأربعة

1. **الكود الكامل معروض بالكامل في §1 و§2** — `router.py:265-275` و
   `service.py:610-621` (+ السياق المحيط بـ`process_auto_renewals`
   كاملة في §4).
2. **موضع الـcommit في `saas_tasks.py:74-75` محدَّد بدقة** (مباشرة بعد
   استدعاء `process_auto_renewals`، قبل معالجة النتائج) — **نفس الموضع
   المنطقي غائب تمامًا** في `router.py` (كان لازم يكون بين السطرين
   274-275، §3).
3. **لا يوجد فرع تاني معطوب.** SUCCESS آمن (commit خاص بيه، سطر 314،
   مستقل تمامًا عن أي commit خارجي — بما فيها `pay_invoice`/`transfer()`
   المنفصلة، عندها نفس النمط الآمن). FAILED لا يكتب شيء بالـDB. فرع
   `except InsufficientBalanceError` (PAST_DUE) هو **الوحيد** المعتمِد
   على commit خارجي غائب (§4).
4. **الاختبار الحي أثبت المشكلة فعليًا** (§5) — استدعاء `trigger_renewals`
   الفعلي بسيناريو PAST_DUE يرجّع `PAST_DUE` في الرد بينما الـDB تفضل
   `ACTIVE` بعد إغلاق الجلسة، **بلا أي تعديل كود**.

---

## 7) الحالة النهائية

**البند مؤكَّد بالكامل: `backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`
تحوَّل من "توقع كودي غير مؤكَّد حيًا" إلى "باج مؤكَّد حيًا 100%".**
الإصلاح المقترح (لم يُنفَّذ اليوم — القرار متروك لجلسة منفصلة صراحةً):
إضافة `await db.commit()` في `router.py` مباشرة بعد سطر 274
(`results = await service.trigger_renewals(tenant_id)`)، بنفس نمط
`saas_tasks.py:75` تمامًا — أو نقل الـcommit لداخل `trigger_renewals`
(service.py) نفسها لتغطية أي مستدعٍ مستقبلي آخر لنفس الدالة، قرار
تصميمي يحتاج نقاش منفصل (commit في الراوتر مقابل الخدمة) قبل التنفيذ.

**صفر تعديل على أي كود إنتاج هذه الجلسة.** الملف الوحيد المُضاف:
`eppne-backend/tests/test_trigger_renewals_endpoint_missing_commit.py`
(اختبار تحقق جديد، قابل للحذف أو الإبقاء كـregression test دائم بعد
الإصلاح — قرار المستخدم).
