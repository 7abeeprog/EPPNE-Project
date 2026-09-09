# إصلاح: إضافة auth لـ `GET /finance/admin/crypto-mode`

**النطاق:** إصلاح ضيق جدًا — `finance/router.py:116-126` بس (دالة `get_crypto_mode`).
**استكمال لـ:**
[finance-router-hardcoded-tenant-investigation-session-log.md](finance-router-hardcoded-tenant-investigation-session-log.md)،
[finance-router-system-state-model-and-live-data-session-log.md](finance-router-system-state-model-and-live-data-session-log.md)

## التشخيص (ملخّص من الجلستين السابقتين)

- `FinanceService(db, 1)` (السطر 121 الأصلي) **مُهملة وظيفيًا** —
  `SystemStateRepository.get_state()` تينانت-أجنوستيك بالكامل (صف واحد
  عالمي فقط، `id=1`، مؤكَّد بـSELECT حي).
- المشكلة الحقيقية: الدالة كانت **من غير أي auth dependency خالص** —
  لا `current_user` من الأساس، بخلاف باقي الـ8 نقاط الصحيحة في نفس
  الملف. أي حد بيعرف الـURL يقدر يوصل بدون تسجيل دخول.

## الإصلاح المُنفَّذ

```diff
 @router.get("/admin/crypto-mode")
 async def get_crypto_mode(
+    current_user: User = Depends(get_current_active_user),
     db: AsyncSession = Depends(get_db)
 ):
-    # هذا endpoint عام (قراءة فقط) - لا يحتاج tenant_id
+    # الـ 1 هنا مُهملة وظيفيًا: SystemStateRepository تينانت-أجنوستيك بالكامل
+    # (get_state() بيرجع أحدث صف من غير أي فلترة بـ tenant_id) - أي رقم هنا
+    # هيدّي نفس النتيجة. لو حد وسّع الـresponse مستقبلًا يضيف total_supply
+    # أو exchange_rates (بيانات تشغيلية أحساس)، لازم يراجع الـauth level
+    # تاني وقتها - ما ينفعش يفترض إن "GET بدون قيود إضافية" يفضل آمن دايمًا.
     service = FinanceService(db, 1)
     state = await service.state_repo.get_state()
     return {
         "crypto_mode": str(getattr(state, "crypto_mode", "FULL_CRYPTO")),
         "max_supply": dict(getattr(state, "max_supply", {}))
     }
```

- **`get_current_active_user` (تسجيل دخول عادي)، مش `get_current_superuser`** —
  البيانات المُرجَعة (`crypto_mode`, `max_supply`) رقم تصميمي عام (سقف
  نظري للعرض الكلي)، مش حساسة كفاية لتبرير قيد إداري، لكنها محتاجة
  مستخدم مسجّل على الأقل (بدل مفتوحة بالكامل).
- **`FinanceService(db, 1)` لم يُلمس** — القيمة باقية زي ما هي بالظبط،
  الاستيرادات (`User`, `get_current_active_user`) كانت موجودة بالفعل في
  الملف فمفيش import جديد.

## تحقق حي (TestClient في نفس العملية + DB حقيقية، صفر mock/stub)

سكريبت مؤقت (خارج الريبو، في scratchpad) استخدم `fastapi.testclient.TestClient`
على تطبيق FastAPI الفعلي (`app.main.fastapi_app`) مع الـDB الحقيقية
(نفس `.env`)، وتوكنات JWT حقيقية مُولَّدة عبر `create_access_token`
الفعلية (نفس آلية الإصدار المستخدمة في `identity/service.py`).

**Test 1 — بدون توكن:**
```
status: 401
body: {"detail":"Not authenticated"}
```
✅ مطابق للمتوقع.

**Test 2 — مستخدم عادي مسجّل (id=2, tenant_id=1, `system_role=USER` — مش SUPER_ADMIN):**
```
status: 200
body: {"crypto_mode":"FULL_CRYPTO","max_supply":{"MR7":10000000,"MRX":100000,"NBT":1000000,"MR_USDT":100000000,"MR_POUND":1000000000}}
```
✅ مطابق للمتوقع — مستخدم عادي (مش إداري) قادر يوصل بنجاح، والقيم
المُرجَعة مطابقة للبيانات الحية في الـDB (موثَّقة في التقرير السابق).

**ملاحظة تقنية:** أول محاولة رجّعت `400` بسبب `TrustedHostMiddleware`
(الـ`host` الافتراضي لـ`TestClient` هو `testserver`، مش ضمن
`ALLOWED_HOSTS` في `.env`) — اتصلح بتمرير `base_url="http://localhost"`
(موجود في `ALLOWED_HOSTS`). مفيش علاقة بالتغيير نفسه، مجرد تفصيلة إعداد
الاختبار.

## Regression

بحث شامل في `tests/` أكّد: **مفيش أي test موجود بيستورد أو بيمرّن
`finance/router.py` مباشرة** (كل تيستات finance الموجودة بتشتغل على
مستوى `FinanceService`/repository مباشرة، صفر HTTP client في الريبو
كله). أقرب test ذو صلة:

```
tests/test_financeservice_tenant_binding_fix.py -q
2 passed, 1 warning in 36.95s
```
✅ صفر كسر.

## الملفات المُعدَّلة

- `eppne-backend/app/domains/finance/router.py` (سطور 116-126 بس — إضافة
  `current_user` param + تحديث تعليق واحد. `FinanceService(db, 1)` لم يتغيّر).
- `PROGRESS_LOG.md` — إغلاق بند `backlog-finance-router-hardcoded-tenant-id-1`
  بتوضيح إن التشخيص الأصلي ("عزل تينانت مكسور") كان غير دقيق؛ السبب
  الحقيقي غياب auth، والإصلاح إضافة auth بسيط، صفر لمس للـ`tenant_id`
  الهاردكودد المُهمَل وظيفيًا.

**لا تعديلات تانية أُجريت — النطاق التزم بالضبط بالسطور 116-126 المطلوبة.**
