# إصلاح: باج تفسير القيمة الراجعة من check_idempotency() في 4 مواضع

**النوع:** إصلاح كود + اختبار حي + regression.
**الملفات المعدَّلة:** `eppne-backend/app/domains/health/service.py`,
`eppne-backend/app/domains/communications/router.py`.
**ملف اختبار جديد:** `eppne-backend/tests/test_idempotency_truthy_bug_fix.py`.
**بند backlog المصدر:** `PROGRESS_LOG.md` —
`backlog-idempotency-check-truthy-misinterpretation-health` [2026-09-10].
**التاريخ:** 2026-09-10

---

## 1. السبب الجذري (تذكير)

`check_idempotency()` (`app/core/idempotency.py:17-24`):
```python
async def check_idempotency(key: str, ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS) -> bool:
    is_new = await client.set(redis_key, "LOCKED", ex=ttl_seconds, nx=True)
    return is_new is True
```
بترجع `True` لما المفتاح **جديد** (SETNX نجح، يعني "كمّل تنفيذ العملية")
— مش لما فيه نتيجة سابقة مخزَّنة. أربع مواضع كانت بتعامل أي قيمة truthy
منها على إنها "نتيجة مخزَّنة، رجّعها فورًا" — فأول استخدام حقيقي لأي
`Idempotency-Key` جديد كان بيرجّع `True` (bool) بدل تنفيذ العملية
بالكامل.

---

## 2. فحص `safe_execute_with_idempotency()` (الخيار المفضَّل) — لماذا استُبعِد

**التوقيع الكامل (`app/core/idempotency.py:50-74`):**
```python
async def safe_execute_with_idempotency(
    key: str,
    func: Callable[[], Awaitable[Any]],
    ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS
) -> Any:
    is_allowed = await check_idempotency(key, ttl_seconds)
    if not is_allowed:
        cached_result = await get_idempotency_result(key)
        if cached_result is not None:
            return cached_result
        raise IdempotencyError("Duplicate request is still processing, please wait.")
    try:
        result = await func()
        await store_idempotency_result(key, result)
        return result
    except Exception as e:
        redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{key}"
        client = await redis_client.get_client()
        await client.delete(redis_key)
        raise
```

**التحقق من التوافق مع شكل الاستدعاء الحالي (تخزين نتيجة + استرجاعها):**
هذا الـhelper بيتعامل مع `check_idempotency()` **صح** (`is_allowed`
بمعناها الحقيقي)، وبيغلّف دورة كاملة: تنفيذ → تخزين → إرجاع، أو
استرجاع الكاش لو مش مسموح. من ناحية المنطق، مناسب 100%.

**لكن من ناحية شكل البيانات، مش مناسب مباشرة للأربع مواضع دي بلا
تعديل:**
- `store_idempotency_result(key, result)` بتعمل
  `json.dumps(result, default=str, ensure_ascii=False)`.
- الثلاثة مواضع الأولى (`book_appointment`, `trigger_emergency`) بترجع
  كائنات SQLAlchemy ORM (`MedicalAppointment`/`EmergencyDispatch`) —
  مش JSON-serializable مباشرة. `default=str` بيقع كـfallback وينتج
  سترينج زي `"<app.domains.health.models.MedicalAppointment object at
  0x...>"` (تمثيل الذاكرة، مش بيانات حقيقية).
- عند استرجاعها لاحقًا (`get_idempotency_result`)، `json.loads()` هترجع
  **نفس السترينج ده** كنتيجة — يعني التكرار هيرجّع سترينج غريب بدل
  الكائن الحقيقي، بدل ما FastAPI يقدر يسلسله عبر `response_model`
  (`MedicalAppointmentResponse(from_attributes=True)`) → `ResponseValidationError`
  فعليًا. **باج جديد مختلف تمامًا، بنفس الخطورة تقريبًا.**
- استخدام `safe_execute_with_idempotency` بأمان كان هيحتاج على أي حال
  تعديل الاستدعاء ليخزن تمثيل آمن (`{"id": obj.id}`) بدل الكائن الكامل
  — يعني "تعديل بسيط" فعلي، لكن بمجرد عمل هذا التعديل، أصبح استخدام
  الـhelper نفسه غير ضروري: نفس منطق "خزّن id، اجلب الكائن الحقيقي عند
  التكرار" ممكن يتطبق مباشرة بلا التفاف حول helper مصمم لنتائج JSON-safe
  عامة.

**القرار:** الإصلاح المحلي المباشر (الخيار البديل المصرَّح به) بدل
`safe_execute_with_idempotency` للمواضع الثلاثة الأولى في `health`.
للموضعين في `communications`، اكتُشف حل أنظف تمامًا (راجع §4).

---

## 3. الإصلاح في `health/service.py` (موضعان 1+2)

### `_validate_idempotency` (الهيلبر المشترك، تستخدمها `book_appointment`)

**قبل:**
```python
async def _validate_idempotency(self, idempotency_key: str, model_class) -> Optional[Any]:
    if not idempotency_key:
        return None
    cached = await check_idempotency(idempotency_key)
    if cached:
        if isinstance(cached, dict) and "id" in cached:
            return await self.repo.get_appointment(cached["id"]) if model_class == MedicalAppointment else None
        return cached
    return None
```
عيب إضافي مستقل هنا: `cached` مصدرها `check_idempotency()` (دايمًا
`bool`)، فشرط `isinstance(cached, dict)` **كود ميت مستحيل التنفيذ** —
النية الأصلية كانت غالبًا استدعاء `get_idempotency_result()` هنا، لكن
الكود بيستدعي `check_idempotency()` بالغلط.

**بعد:**
```python
async def _validate_idempotency(self, idempotency_key: str, model_class) -> Optional[Any]:
    if not idempotency_key:
        return None
    is_new = await check_idempotency(idempotency_key)
    if is_new:
        return None
    cached = await get_idempotency_result(idempotency_key)
    if isinstance(cached, dict) and "id" in cached:
        fetched = None
        if model_class == MedicalAppointment:
            fetched = await self.repo.get_appointment(cached["id"])
        elif model_class == EmergencyDispatch:
            fetched = await self.repo.get_dispatch(cached["id"])
        if fetched:
            return fetched
    raise IdempotencyError("طلب مكرر لا يزال قيد المعالجة، يرجى المحاولة لاحقًا.")
```
- `is_new=True` → إرجاع `None` (تابع التنفيذ العادي).
- `is_new=False` (المفتاح مُستخدَم من قبل) → جلب النتيجة الحقيقية عبر
  `get_idempotency_result()` (مضافة الآن للاستيراد)، وإعادة جلب الكائن
  الفعلي من DB بالـid (بدل إرجاع الـdict الخام أو سترينج معطوب).
- لو المفتاح محجوز لكن لسه مفيش نتيجة مخزَّنة (العملية الأصلية لسه قيد
  التنفيذ — سباق حقيقي بين طلبين متزامنين بنفس المفتاح) → `IdempotencyError`
  (مسجَّلة مسبقًا كـexception handler في `main.py:113-118` → **409
  Conflict**)، بدل التجاهل الصامت السابق.
- عُمِّمت لتدعم `EmergencyDispatch` كمان (كانت مقصورة على
  `MedicalAppointment` فقط)، تمهيدًا لتوحيد `trigger_emergency` عليها.

### `_store_idempotency`

**قبل:** `await store_idempotency_result(idempotency_key, result)` —
تخزين الكائن الكامل (نفس عيب `safe_execute_with_idempotency` الموضَّح
في §2، غير قابل لإعادة البناء لاحقًا).

**بعد:** `await store_idempotency_result(idempotency_key, {"id": result.id})`
— تخزين الـid فقط (JSON-safe 100%)، وإعادة الجلب الكامل من DB تحصل في
`_validate_idempotency` عند التكرار.

### `trigger_emergency` — إزالة التكرار

كانت الدالة فيها نسخة مطابقة تمامًا لنفس المنطق الغلط، مكتوبة inline
بدل استخدام `_validate_idempotency`:
```python
# قبل
if idempotency_key:
    cached = await check_idempotency(idempotency_key)
    if cached:
        if isinstance(cached, dict) and "id" in cached:
            dispatch = await self.repo.get_dispatch(cached["id"])
            if dispatch:
                return dispatch
        return cast(EmergencyDispatch, cached)
```
```python
# بعد
if idempotency_key:
    cached = await self._validate_idempotency(idempotency_key, EmergencyDispatch)
    if cached:
        return cached
```
نفس السبب الجذري، نفس الإصلاح، مكان واحد بس دلوقتي (الهيلبر الموحَّد).
تخزين النتيجة في نهاية `trigger_emergency` كانت أصلاً بتستخدم
`self._store_idempotency(idempotency_key, dispatch)` (الهيلبر المشترك)
— لم تحتَج أي تغيير في نقطة الاستدعاء، فقط الهيلبر نفسه اتصلح.

---

## 4. الإصلاح في `communications/router.py` (موضعان 3+4) — نهج مختلف

بمراجعة `CommunicationsService.send_notification`/`send_mail`
(`communications/service.py:54-57`, `135-138`)، تبيَّن إنهم **أصلاً
بيعملوا تحقق Idempotency صحيح ومستقل تمامًا**، عبر عمود `idempotency_key`
**الفريد (`unique=True`)** على جدولي `notifications`/`mail_messages`
نفسهم (`models.py:47`, `108`)، باستخدام
`repo.get_notification_by_idempotency`/`get_message_by_idempotency`
(موجودتان مسبقًا في `repository.py:36-40`, `139-142`):
```python
if idempotency_key:
    existing = await self.repo.get_notification_by_idempotency(idempotency_key)
    if existing:
        return existing
```
هذا التحقق **صحيح 100%** ولا يعاني من باج `check_idempotency` إطلاقًا
(بيستخدم DB query مباشر، مش Redis). طبقة `check_idempotency`/
`store_idempotency_result` في الراوتر كانت **طبقة Redis زيادة تمامًا
وغير ضرورية** فوق هذا التحقق الصحيح أصلاً، وهي اللي كانت حاملة الباج.

**القرار:** حذف الطبقة الزيادة بالكامل من الراوتر (بدل تصحيحها) —
الاعتماد الآن فقط على تحقق الـservice الصحيح، وصفر تعديل على
`service.py` (لم يكن معطوبًا أصلاً).

**قبل (`send_notification`, وبالمثل `send_mail`):**
```python
idempotency_key = data.idempotency_key or request.headers.get("Idempotency-Key")
if idempotency_key:
    cached_result = await check_idempotency(idempotency_key)
    if cached_result:
        return cached_result
...
if idempotency_key:
    await store_idempotency_result(idempotency_key, notification)
```

**بعد:**
```python
idempotency_key = data.idempotency_key or request.headers.get("Idempotency-Key")
...
# (صفر كتلة Redis إضافية — service.send_notification كافية وحدها)
```
`from app.core.idempotency import check_idempotency, store_idempotency_result`
اتشالت من imports الراوتر (بقت غير مُستخدَمة تمامًا بعد الحذف).

---

## 5. اختبار حي (`tests/test_idempotency_truthy_bug_fix.py`) — 4/4 ناجحة

المنهجية: استدعاء دوال الراوتر الفعلية مباشرة (نفس أسلوب الجلسات
السابقة)، DB حقيقية، مرتين متتاليتين بنفس `idempotency_key`:

1. **`book_appointment`:** أول استدعاء يُنشئ الموعد فعليًا ويخصم 10
   MR_USDT (تأكيد `not isinstance(first, bool)`). التكرار بنفس المفتاح
   يرجّع **نفس** `appointment.id`، صف واحد بس في `medical_appointments`،
   والرصيد يفضل 90.00 (صفر خصم إضافي عند التكرار).
2. **`trigger_emergency`:** نفس المنهجية — التكرار يرجّع نفس
   `dispatch.id`، صف واحد بس في `emergency_dispatches`.
3. **`send_notification`:** أول استدعاء ينشئ إشعارًا فعليًا. التكرار
   يرجّع نفس `notification.id`، صف واحد بس في `notifications`.
4. **`send_mail`:** نفس المنهجية لـ`mail_messages`.

كل الأربعة بتتأكد صراحة من `not isinstance(result, bool)` — الفحص
المباشر لأعراض الباج القديم (كان بيرجع `True` حرفيًا).

**نتيجة التشغيلة:** `4 passed` (84.95s، DB حقيقية `eppne_v2`، صفر
mock/stub). أُعيد تشغيل ملف الاختبار السابق
(`test_health_nameerror_and_fee_ordering_fix.py`) للتأكد من عدم تعارض
مع إصلاحات الجلسة السابقة — **4/4 ناجحة كمان (74.84s)**.

---

## 6. Regression

تشغيلة كاملة نظيفة لكل `tests/` (باستثناء
`test_affiliate_service_missing_methods.py` — عطل استيراد قديم غير
مرتبط، موثَّق مسبقًا): `15 failed, 156 passed, 2 xfailed`. نفس الـ15 اسم
فشل بالحرف الموثَّقة كأساس (baseline) في `PROGRESS_LOG.md` (جلسة
`invoicing-process-overdue-invoices` بتاريخ 2026-09-09:
`15 failed, 148 passed, 2 xfailed`) + 4 اختبارات
`test_health_nameerror_and_fee_ordering_fix.py` (جلسة سابقة) + 4
اختبارات `test_idempotency_truthy_bug_fix.py` (هذه الجلسة) = `156
passed`. صفر علاقة لأي من الـ15 فشل بـ`health`/`communications`/
`finance`. **صفر regression.**

**الملفات المعدَّلة في هذه الجلسة فقط:** `health/service.py`,
`communications/router.py` (+ ملف اختبار جديد). `communications/service.py`
لم يُلمَس (لم يكن معطوبًا). لا يوجد أي كود تاني بيستدعي
`_validate_idempotency`/`_store_idempotency` (خاصتان بـ`HealthService`)
غير `book_appointment`/`trigger_emergency` نفسهم — تم التأكد بقراءة
الملف كاملًا. `check_idempotency`/`store_idempotency_result` مستخدَمة
في مواضع تانية غير هذه الأربعة (`core/idempotency.py` نفسها فقط، عبر
`safe_execute_with_idempotency` — غير متأثرة، صفر تعديل عليها) — تم
التأكد بـgrep شامل قبل التعديل (راجع بند الـbacklog المصدر).

---

## 7. الحالة النهائية

✅ **الأربع نقاط عطب (`book_appointment`, `trigger_emergency` في
`health`، و`send_notification`, `send_mail` في `communications`)
اتصلحت بالكامل ومتحقَّق منها حيًا** — أول استخدام لمفتاح جديد بينفذ
العملية فعليًا، والتكرار بيرجّع النتيجة الحقيقية المخزَّنة (مش `True`).
بند backlog `backlog-idempotency-check-truthy-misinterpretation-health`
في `PROGRESS_LOG.md` بقى **✅ اتحل** (تم توضيح إن النطاق الفعلي كان 4
مواضع في ملفين، مش 2 كما بدا أول الأمر).
