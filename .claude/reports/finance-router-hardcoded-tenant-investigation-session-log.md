# تحقيق: `FinanceService(db, 1)` الهاردكودد في finance/router.py:121

**النطاق:** فحص read-only بحت — صفر تعديل كود.

## الـendpoint المحيط بالسطر

```python
# eppne-backend/app/domains/finance/router.py:116-126
@router.get("/admin/crypto-mode")
async def get_crypto_mode(
    db: AsyncSession = Depends(get_db)
):
    # هذا endpoint عام (قراءة فقط) - لا يحتاج tenant_id
    service = FinanceService(db, 1)
    state = await service.state_repo.get_state()
    return {
        "crypto_mode": str(getattr(state, "crypto_mode", "FULL_CRYPTO")),
        "max_supply": dict(getattr(state, "max_supply", {}))
    }
```

- **اسم الـendpoint:** `get_crypto_mode` — `GET /finance/admin/crypto-mode`.
- **بدون أي auth dependency** — لا `current_user`، لا `get_current_active_user` ولا `get_current_superuser`. الاعتماد الوحيد هو `db: AsyncSession = Depends(get_db)`.

## هل `current_user.tenant_id` متاح فعليًا في نفس الدالة؟

**لا.** بخلاف الـ7 نقاط الصحيحة الأخرى في نفس الملف (السطور 29, 45, 75, 102, 135, 146, 158, 182 — كلها فيها `current_user: User = Depends(get_current_active_user)` أو `get_current_superuser`)، دالة `get_crypto_mode` **لا تحتوي على أي parameter اسمه `current_user` من الأساس**. فمفيش `tenant_id` متاح للاستخدام حتى لو حبينا — لازم نضيف dependency جديد للـ auth الأول قبل ما نقدر نستبدل الـ`1`.

## هل فيه سبب خاص وراء الـ`1` الثابتة؟

فيه تعليق موجود بالفعل فوق السطر (line 120):
> `# هذا endpoint عام (قراءة فقط) - لا يحتاج tenant_id`
> ("هذا endpoint عام (قراءة فقط) - لا يحتاج tenant_id")

يعني نية المطور كانت: الـendpoint ده عام/بدون تينانت لأنه read-only، فمفيش داعي لـ tenant_id حقيقي.

**لكن الفحص الأعمق يكشف حاجتين مهمين:**

1. **الـ `tenant_id` مش بيتستخدم فعليًا في المسار ده أصلًا.** `FinanceService.__init__` (service.py:19) بيخزن `self.tenant_id = tenant_id`، لكن الكود بعد كده بيستخدم بس `self.state_repo.get_state()` — و`SystemStateRepository` (repository.py:217-229) **class كامل بدون tenant_id في الـ constructor ولا في أي query جواه**:
   ```python
   class SystemStateRepository:
       def __init__(self, db: AsyncSession):
           self.db = db

       async def get_state(self) -> SystemState:
           result = await self.db.execute(select(SystemState).order_by(SystemState.id.desc()).limit(1))
           ...
   ```
   يعني `get_state()` بترجع أحدث صف في جدول `SystemState` بدون أي فلترة بـ tenant — النظام أصلًا مصمم كـ **global singleton state** (نمط exchange-rates/crypto-mode نظام واحد لكل الـ deployment مش لكل تينانت). فالقيمة `1` اللي بتتمرر لـ `FinanceService` **dead/unused** بالنسبة لهذا المسار تحديدًا — مش بس هاردكودد، هي أصلًا مش بتأثر على النتيجة.

2. **التناقض مع الـPOST المقابل (نفس الملف، سطر 129-137):**
   ```python
   @router.post("/admin/crypto-mode")
   async def set_crypto_mode(
       req: CryptoModeToggle,
       current_user: User = Depends(get_current_superuser),
       db: AsyncSession = Depends(get_db)
   ):
       service = FinanceService(db, cast(int, current_user.tenant_id))
       await service.state_repo.update_crypto_mode(req.mode, cast(int, current_user.id))
   ```
   الـ POST بتاع نفس الـ resource (تعديل crypto_mode) **بيطلب superuser auth فعليًا** ويمرر `current_user.tenant_id` الحقيقي — رغم إن `update_crypto_mode` كمان مش بيستخدم tenant_id (بيعمل نفس `get_state()` العام). ده تناقض معماري: لو الـ state فعلًا "عام" ومفيهوش تينانت، مفروض الـ POST كمان يبقى بلا auth بمنطق "مفيش tenant_id"، لكن هو محمي بـ `get_current_superuser`. العكس (GET) مكشوف بالكامل بدون أي auth — أي حد بيعرف الـ URL يقدر يقرا crypto_mode و max_supply من غير تسجيل دخول أصلًا.

## الخلاصة

- الـ `1` الهاردكودد **مش بگ من نوع "استعمل تينانت غلط" فعليًا** — لأن `SystemStateRepository` بالكامل تينانت-أجنوستيك (global)، فالرقم مش بيأثر على أي نتيجة فعلية في هذا المسار.
- التعليق الموجود (سطر 120) بيوثّق نية "قراءة عامة" — لكنه بيغطي بس جزء المشكلة: الفجوة الحقيقية مش الـ`1` نفسه، لكن **غياب أي auth على الإطلاق** على endpoint بيرجع `max_supply` وإعدادات النظام، بينما الـ POST المقابل (تعديل نفس البيانات) بيتطلب superuser. لو ده مقصود (endpoint عام فعلاً بالتصميم) يبقى مفيش حاجة تتصلح؛ لو مش مقصود، المشكلة الحقيقية هي "GET بدون auth" مش "hardcoded tenant_id".
- **صفر تعديل كود اتنفذ في الجلسة دي** — الفحص كان read-only بالكامل زي المطلوب.
