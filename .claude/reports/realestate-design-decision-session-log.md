# جلسة: realestate-hooks-layer-design-decision

**تاريخ البدء:** 2026-08-31
**الحالة:** 🔵 تحقيق + تصميم فقط — **صفر تنفيذ**. جدول التصميم الكامل جاهز
للموافقة.

## السياق

استكمال لجلسة `realestate-hooks-layer-nonexistent-function-imports`
(2026-08-29): 8 حالات "(ب)" مؤكَّدة — استدعاءات هوكس فرونت إند لا تقابلها
أي دالة/endpoint في `RealEstateService` (باك إند). القرار المؤجَّل من جلسة
تصنيف الأولويات (2026-08-29): **نبني الميزات الناقصة في الباك إند** (مش
نقلّم الواجهة)، لأن `realestate` دومين أساسي متكرر الاستخدام.

هذه الجلسة: تحقيق + تصميم فقط. صفر تنفيذ حتى موافقة صريحة.

---

## خطوة 1: اكتشاف تصحيحي مهم — 3 من الـ8 حالة ليست "غير موجودة إطلاقًا"

جلسة 2026-08-29 حكمت على الحالات الثمانية بالاعتماد على `service.py` +
`services/realestate.ts` فقط، **بدون قراءة `repository.py`**. قراءة حية
لـ`repository.py` الآن (E:\cc\eppne-backend\app\domains\realestate\repository.py)
كشفت إن 3 methods موجودة بالفعل على مستوى الـrepository، لكن **لا يوجد
لها service method ولا router endpoint يكشفها**:

| Method في `repository.py` | السطر | مُستخدَمة حاليًا فين؟ |
|---|---|---|
| `get_ownerships_by_unit(unit_id)` | 100-102 | **غير مستخدَمة إطلاقًا** في أي مكان في `service.py` |
| `get_smart_contract(contract_id, tenant_id)` | 162-166 | **غير مستخدَمة إطلاقًا** — حتى `deploy_smart_contract` نفسها لا تستدعيها |
| `get_tokenization_by_unit(unit_id, tenant_id)` | 148-152 | مستخدَمة داخليًا فقط جوّه `tokenize_asset` (للتحقق من عدم التكرار)، **مش مكشوفة كـGET مستقل** |

هذا يغيّر تصنيف 3 حالات من "(ب) مفهوم جديد" إلى **"(أ) امتداد بسيط —
الطبقة الأعمق جاهزة، ناقص فقط service method + router endpoint"**. تفصيل
كامل في الجدول أدناه (خطوة 3).

---

## خطوة 2: الحالات الثمانية — ماذا يتوقع الفرونت إند مقابل الموجود فعليًا

تأكيد حي من قراءة الملفات التالية:
`eppne-web/hooks/realestate/useProperties.ts`,
`eppne-web/hooks/realestate/usePropertyOwnerships.ts`,
`eppne-web/hooks/realestate/useTokenization.ts`,
`eppne-web/app/(dashboard)/realestate/property/[id]/page.tsx`,
`eppne-web/components/realestate/InvestorPortfolio.tsx`,
`eppne-web/types/realestate.ts`
مقابل `eppne-backend/app/domains/realestate/{models,schemas,service,repository,router}.py`.

### 1-5) `getProperties` / `getProperty` / `createProperty` / `updateProperty` / `deleteProperty`

الصفحة `property/[id]/page.tsx` (المستهلك الفعلي) تفترض شكل بيانات
"Property" به: `title`, `cover_image_url`, `location`, `status`,
`description`, `area_sqm`, `sale_price_mrusdt`, `rent_per_month_mrusdt`,
`owner_id`, `created_at` (تأكيد حرفي من الأسطر 155-325 من الملف).

`PropertyUnit` الحقيقي في `models.py` (السطر 114-142) عنده:
`unit_number`, `floor_number`, `area_sqm`, `property_type`,
`sale_price_mrusdt`, `rent_per_month_mrusdt`, `smart_asset_id`,
`is_available_for_sale`, `is_available_for_rent`, `development_id`
(FK) — **بدون** `title`, `cover_image_url`, `location`, `status`,
`description`, `owner_id` مباشرة (الملكية عبر سلسلة
`unit.development_id → development.land_asset_id → land.owner_id`، لا
يوجد `owner_id` مباشر على الوحدة).

**الخلاصة:** `PropertyUnit` هو نفس الكيان الصحيح منطقيًا (نفس المعنى:
وحدة عقارية قابلة للبيع/الإيجار)، لكنه **بنيوي/هندسي بحت** (رقم وحدة،
طابق، مساحة) بينما الواجهة تتوقع **كيان تسويقي/عرضي** (عنوان، صورة
غلاف، موقع، وصف، حالة عرض). هذا **ليس مفهومًا جديدًا كليًا** (مفيش داعي
لجدول `properties` منفصل يكرر `property_units`) — **بل امتداد Schema
طبيعي**: نضيف 5 أعمدة تسويقية اختيارية لـ`PropertyUnit` نفسها.

### 6) `getPropertyOwnerships(propertyId)`

الاستخدام في `usePropertyOwnerships.ts` + `property/[id]/page.tsx`:
جلب كل الملكيات الجزئية لوحدة معيّنة (مش ملكيات المستخدم الحالي —
دي `getMyOwnerships` منفصلة وموجودة بالفعل).

**الموجود فعليًا:** `repository.get_ownerships_by_unit(unit_id)` — تطابق
تام في المعنى، جاهزة 100%، غير مكشوفة فقط.

### 7) `getSmartContractStatus(contractId)`

الاستخدام في `InvestorPortfolio.tsx` (`SmartContractStatusMonitor`,
سطر 100-159): polling كل 3 ثوانٍ لحالة عقد ذكي، يتوقع `{status, tx_hash}`.

**ملاحظة أولوية مهمة:** بحث حي (`Grep`) عبر كل `*.tsx` أثبت إن
`SmartContractStatusMonitor` **مُصدَّرة لكن غير مُستورَدة/مُستخدَمة في أي
مكان تاني في المشروع** — كود يتيم (orphaned) حاليًا، مش معروض لأي
مستخدم فعلي.

**الموجود فعليًا:** `repository.get_smart_contract(contract_id, tenant_id)`
موجودة بالضبط، غير مستخدَمة إطلاقًا حتى داخليًا. `SmartContractResponse`
(schemas.py سطر 182) فيها `execution_status`+`blockchain_tx_hash` —
نفس المعنى المطلوب (`status`+`tx_hash`) لكن بأسماء حقول مختلفة.

### 8) `getAssetTokenization(unitId)`

الاستخدام في `useTokenization.ts` + `property/[id]/page.tsx`: جلب تفاصيل
تجزئة وحدة معيّنة (أو `null`/`undefined` لو مش مجزأة — الصفحة بتتعامل مع
الحالتين بوضوح: `{tokenization ? (...) : (<div>هذا العقار غير مجزأ حالياً</div>)}`).

**الموجود فعليًا:** `repository.get_tokenization_by_unit(unit_id, tenant_id)`
موجودة بالضبط بنفس التوقيع المطلوب، مستخدَمة داخليًا فقط في
`tokenize_asset` (سطر 481) للتحقق من عدم التكرار.

---

## خطوة 3: الجدول الموحَّد النهائي — تصنيف + تصميم + أولوية + حجم العمل

| # | الحالة | التصنيف | لماذا | التصميم المقترح | الأولوية | الحجم |
|---|---|---|---|---|---|---|
| 6 | `getPropertyOwnerships` | **(أ) وصلة فقط** | `repo.get_ownerships_by_unit` جاهزة 100% | service: `get_unit_ownerships(unit_id, tenant_id)` (يجلب الوحدة، يتحقق `unit.tenant_id==tenant_id`، ثم `repo.get_ownerships_by_unit`) + router: `GET /realestate/units/{unit_id}/ownerships` → `list[OwnershipResponse]` | 🔴 عالية (جزء من صفحة التفاصيل الرئيسية) | سطر واحد إضافة (service+router قصيرين، صفر migration) |
| 8 | `getAssetTokenization` | **(أ) وصلة فقط** | `repo.get_tokenization_by_unit` جاهزة 100%، بنفس التوقيع | service: `get_asset_tokenization(unit_id, tenant_id) -> Optional[AssetTokenization]` (بدون رفع `NotFoundError` — `None` حالة طبيعية "غير مجزأة") + router: `GET /realestate/units/{unit_id}/tokenization` → `Optional[TokenizationResponse]` | 🔴 عالية (جزء من صفحة التفاصيل الرئيسية) | سطر واحد إضافة، صفر migration |
| 7 | `getSmartContractStatus` | **(أ) وصلة فقط** | `repo.get_smart_contract` جاهزة 100% | service: `get_smart_contract_status(contract_id, tenant_id)` (يرفع `NotFoundError` لو مش موجود) + router: `GET /realestate/smart-contracts/{contract_id}` → `SmartContractResponse`. ملاحظة فرونت إند منفصلة (خارج هذا التصميم): `SmartContractStatusMonitor` بتقرأ `data.status`/`data.tx_hash` بينما الـschema فيها `execution_status`/`blockchain_tx_hash` — تعديل استهلاك بسيط لاحقًا | 🟢 منخفضة (كود يتيم غير مستخدَم في أي صفحة فعليًا الآن) | سطر واحد إضافة، صفر migration |
| 3 | `createProperty` | **(أ) mapping فقط** | موجودة بالفعل حرفيًا كـ`create_property_unit`/`POST /realestate/units` | frontend-only: تصحيح الاستيراد (نفس نمط حالات (أ) في الجلسة السابقة) — إذا اعتُمد امتداد الـschema (حالة 1/2 التالية)، تُضاف الحقول التسويقية كـ`Optional` في `PropertyUnitCreate` أيضًا فيتدفقوا تلقائيًا عبر `data.model_dump()` الموجود بالفعل | 🔴 عالية (بدون create، صفحة الإنشاء معطّلة بالكامل) | صفر تعديل باك إند لو الحقول التسويقية اختيارية |
| 1 | `getProperties` (قائمة) | **(ب) امتداد schema لكيان موجود** | `PropertyUnit` صحيح منطقيًا، ناقصه أعمدة تسويقية | **Migration**: إضافة 5 أعمدة `Nullable` لـ`property_units`: `title varchar(255)`, `description text`, `location varchar(255)`, `cover_image_url text`, `status varchar(50) default 'AVAILABLE'`. + `PropertyUnitCreate`/`PropertyUnitResponse` تتحدّث بنفس الحقول (Optional). + service: `list_units(tenant_id, property_type?, development_id?, skip, limit)` (عام، بدون فرض `for_sale=True` — `list_units_for_sale` الحالية تفضل كما هي بدون تغيير) + router: `GET /realestate/units` → `list[PropertyUnitResponse]` | 🔴 عالية (تكسر صفحة `realestate/page.tsx` الرئيسية بالكامل) | migration بسيطة + endpoint قصير |
| 2 | `getProperty` (فردي) | **(ب) نفس امتداد #1** | نفس الأعمدة المطلوبة | service: `get_property_unit(unit_id, tenant_id)` (يستخدم `repo.get_unit` الموجودة + تحقق `tenant_id`، يرفع `NotFoundError`) + router: `GET /realestate/units/{unit_id}` → `PropertyUnitResponse` | 🔴 عالية (بدون هذا، صفحة `property/[id]` كلها معطّلة) | سطر واحد إضافة (فوق migration #1 المشتركة) |
| 4 | `updateProperty` | **(ب) endpoint جديد + فحص ملكية** | لا يوجد تحديث عام لوحدة، فقط `update_unit_availability` (بوليان فقط) | **Schema جديد**: `PropertyUnitUpdate` (كل الحقول `Optional`، نفس حقول `PropertyUnitCreate` + التسويقية). **Repo**: `update_unit(unit_id, **kwargs)` (تحديث جزئي، نفس نمط `update_land_value`). **Service**: `update_property_unit(unit_id, tenant_id, updater_id, data)` — يجلب الوحدة، يتحقق `tenant_id`، **ثم يتحقق ملكية بنفس نمط `tokenize_asset`/`rent_unit` الموجود فعليًا**: `owner = await self._get_land_owner_for_unit(unit, tenant_id); if owner.id != updater_id: raise PermissionDeniedError(...)`. **Router**: `PATCH /realestate/units/{unit_id}` (`@rate_limit`, نفس نمط بقية الـPATCH/POST في الدومين) → `PropertyUnitResponse` | 🔴 عالية (زر "تعديل" في صفحة التفاصيل معطّل بالكامل) | تصميم schema جديد (Update schema + فحص ملكية) — أكبر من إضافة سطر، أصغر من migration |
| 5 | `deleteProperty` | **(ب) endpoint جديد + فحص ملكية** | لا يوجد أي حذف/soft-delete لوحدة رغم وجود `is_deleted`/`deleted_at` جاهزين في الموديل (نمط soft-delete متّبع أصلاً في `LandAsset`/`Development` لكن غير مُفعَّل هناك برضو) | **Repo**: `soft_delete_unit(unit_id)` (`is_deleted=True`, `deleted_at=func.now()`). **Service**: `delete_property_unit(unit_id, tenant_id, deleter_id)` — **نفس فحص الملكية المستخدَم في #4 بالضبط** (`_get_land_owner_for_unit`). **قرار عمل مفتوح يحتاج إجابة صريحة قبل التنفيذ:** هل نمنع الحذف لو فيه ملكيات جزئية/تجزئة فعّالة على الوحدة (`get_ownerships_by_unit`/`get_tokenization_by_unit` غير فارغة)؟ لو لا يوجد فحص، حذف وحدة ليها مالكين جزئيين هيسيب سجلات `PropertyOwnership` يتيمة منطقيًا. **Router**: `DELETE /realestate/units/{unit_id}` → `204 No Content` | 🟡 متوسطة (ميزة أقل استخدامًا من التعديل/العرض، لكن لسه جزء من نفس الصفحة) | تصميم schema/قرار عمل (سؤال الحذف مع ملكيات فعّالة) — مشابه لـ#4 في الحجم |

**ملاحظة تسمية:** #1b و#2d من الجلسة السابقة (types `Property`,
`PropertyFormData`, `TokenizationFormData` في الفرونت إند) مش بنود
باك إند منفصلة — هتُحل تلقائيًا كجزء من تحديث `types/realestate.ts`
عند التنفيذ الفعلي (خارج نطاق هذا القرار المعماري).

---

## خطوة 4: الأولوية المجمَّعة (الأكثر إلحاحًا أولًا)

1. **`getProperty` + `updateProperty` + `getPropertyOwnerships` +
   `getAssetTokenization`** — الأربعة دول مع بعض يشكّلوا صفحة
   `property/[id]/page.tsx` بالكامل (التفاصيل + التعديل + الملكية +
   التجزئة). بدونهم الصفحة **معطّلة 100%** لأي مستخدم يفتح تفاصيل عقار.
2. **`getProperties` + `createProperty`** — صفحة `realestate/page.tsx`
   الرئيسية (تصفح العقارات + إنشاء عقار جديد) معطّلة بالكامل بدونهم.
3. **`deleteProperty`** — جزء من نفس صفحة التفاصيل، لكن حذف عقار أقل
   إلحاحًا من عرضه/تعديله (يحتاج كمان قرار عمل معلَّق عن الحذف مع
   ملكيات فعّالة).
4. **`getSmartContractStatus`** — الأقل إلحاحًا فعليًا: كود يتيم غير
   مربوط بأي صفحة حاليًا (مؤكَّد عبر Grep حي)، رغم إنه أرخص حالة تُبنى
   (وصلة فقط، صفر migration).

---

## خطوة 5: ملخص حجم العمل (نفس تصنيف الجلسات السابقة)

| الفئة | الحالات | الوصف |
|---|---|---|
| **سطر واحد/إضافة بسيطة (وصلة service+router فقط، صفر migration)** | #6, #7, #8 | الطبقة العميقة (`repository.py`) جاهزة بالفعل — service method قصيرة (فحص tenant/ownership) + router endpoint واحد لكل حالة |
| **Migration بسيطة (أعمدة Nullable + تحديث Schema)** | #1, #2 (تشترك في نفس الـmigration)، #3 (صفر تغيير باك إند إذا الحقول اختيارية) | 5 أعمدة تسويقية اختيارية على `property_units` + endpoint list + endpoint get-by-id |
| **تصميم Schema جديد (Update schema + منطق فحص ملكية)** | #4, #5 | أول تحديث/حذف عام لوحدة عقارية في الدومين كله — يحتاج `PropertyUnitUpdate` schema جديد + تكرار نمط فحص الملكية الموجود (`_get_land_owner_for_unit`) + قرار عمل معلَّق لـ#5 (منع الحذف مع ملكيات فعّالة؟) |

**لا توجد ولا حالة واحدة من الثمانية تحتاج "تصميم schema جديد من الصفر"
بالمعنى الأقصى (كيان جديد كليًا بجدول DB منفصل)** — الاكتشاف الأهم في
هذه الجلسة إن `PropertyUnit` كافٍ كأساس لكل الحالات الثمانية، فقط محتاج
امتداد (أعمدة تسويقية) + وصلات مفقودة (repo→service→router) + عملية
تحديث/حذف واحدة جديدة مبنية على نفس نمط الملكية المُتَّبع بالفعل في
`tokenize_asset`/`rent_unit`.

---

## التوصية للموافقة

1. **تنفيذ الحالات الثلاث "وصلة فقط" (#6, #7, #8) أولًا** — أرخص تكلفة،
   صفر migration، صفر قرار عمل معلَّق، وتغطي معظم صفحة التفاصيل.
2. **بعدها migration الأعمدة التسويقية + #1/#2/#3** — تكسر صفحة كاملة
   حاليًا، وتعتمد على قرار واحد بسيط: هل الأسماء المقترحة للأعمدة
   (`title`, `description`, `location`, `cover_image_url`, `status`)
   مناسبة أم يفضّل المستخدم أسماء/نطاقًا مختلفًا (مثلاً `status` كـ
   `Enum` بدل `String` حر)؟
3. **أخيرًا #4 (`updateProperty`) و#5 (`deleteProperty`)** — يحتاجوا
   قرار عمل صريح واحد قبل التنفيذ: **هل نمنع حذف وحدة عندها ملكيات
   جزئية/تجزئة فعّالة؟** (موصى به: نعم، بنفس منطق `existing` check في
   `tokenize_asset`).

**صفر تنفيذ حتى الآن — في انتظار الموافقة على الجدول أعلاه، وتحديدًا:**
(أ) ترتيب التنفيذ المقترح في خطوة 5 أعلاه، (ب) أسماء/نوع الأعمدة
التسويقية الخمسة، (ج) قرار منع الحذف مع ملكيات فعّالة.

---

## القرارات المعتمَدة من المستخدم (2026-08-31)

1. **ترتيب التنفيذ:** كما هو مقترح — #6/#7/#8 (وصلة فقط) → migration
   الأعمدة التسويقية + #1/#2/#3 → #4/#5 (تعديل/حذف).
2. **`status`:** `Enum` مش `String` حر. القيم المعتمَدة (بعد تعديل مبرَّر
   — راجع خطوة 6 أدناه): **`AVAILABLE`, `SOLD`, `RENTED`,
   `UNDER_CONSTRUCTION`** (مش `UNDER_OFFER` كما اقترح المستخدم أول
   مرة — تصحيح بناءً على اكتشاف حي، موثَّق أدناه).
3. **منع حذف وحدة عندها ملكيات/تجزئة فعّالة:** معتمَد.
4. **منهجية التحقق:** استدعاء مباشر لكل service method بقيم حقيقية ضد DB
   حقيقية (pytest + `AsyncSessionLocal`، نفس نمط
   `test_realestate_tokenize_asset_ownership_check.py`) — مش `tsc` (باك
   إند Python). تحديث هذا الملف بعد كل خطوة قبل الانتقال للتالية.

---

## خطوة 6: تنفيذ #6/#7/#8 (وصلة فقط) — ✅ مكتمل ومتحقَّق حيًا

### التعديلات

**`service.py`** — 3 methods جديدة أُضيفت (بجانب الميثودز ذات الصلة
مباشرة، بدون أي تعديل على الكود الموجود):

```python
async def get_unit_ownerships(self, unit_id: int, tenant_id: int) -> list[PropertyOwnership]:
    """جلب كل الملكيات الجزئية لوحدة معيّنة."""
    unit = await self.repo.get_unit(unit_id)
    if not unit or unit.tenant_id != tenant_id:
        raise NotFoundError("Property unit not found")
    result = await self.repo.get_ownerships_by_unit(unit_id)
    return list(result)

async def get_asset_tokenization(self, unit_id: int, tenant_id: int) -> Optional[AssetTokenization]:
    """جلب تفاصيل تجزئة وحدة (None لو غير مجزأة — حالة طبيعية وليست خطأ)."""
    return await self.repo.get_tokenization_by_unit(unit_id, tenant_id)

async def get_smart_contract_status(self, contract_id: int, tenant_id: int) -> SmartContractEngine:
    """جلب حالة عقد ذكي بمعرفه."""
    contract = await self.repo.get_smart_contract(contract_id, tenant_id)
    if not contract:
        raise NotFoundError("Smart contract not found")
    return contract
```

**`router.py`** — 3 GET endpoints جديدة:
- `GET /realestate/units/{unit_id}/ownerships` → `list[OwnershipResponse]`
- `GET /realestate/units/{unit_id}/tokenization` → `Optional[TokenizationResponse]`
- `GET /realestate/smart-contracts/{contract_id}` → `SmartContractResponse`

كل الثلاثة بنفس نمط `get_development` الموجود (`current_user.tenant_id`
مباشرة، بدون `get_current_tenant` dependency — GET-by-id endpoints في
نفس الملف بتستخدم نفس النمط).

### التحقق الحي (pytest + DB حقيقية، صفر mock)

ملف جديد: `eppne-backend/tests/test_realestate_getter_endpoints_wiring.py`
(3 اختبارات، نفس نمط `test_realestate_tokenize_asset_ownership_check.py`
— مستخدمين/أراضي/تطويرات/وحدات throwaway بـ`uuid` suffix، تنظيف كامل
في `finally`).

**تشغيل حي:** `venv/Scripts/python.exe -m pytest tests/test_realestate_getter_endpoints_wiring.py -v`
→ **3 passed** (80 ثانية):

1. `test_get_unit_ownerships_returns_real_records` — أُنشئت وحدة +
   سجل ملكية حقيقي (25%) عبر `repo.create_ownership` مباشرة، ثم
   `service.get_unit_ownerships(unit_id, tenant_id=1)` رجعت السجل
   بالضبط (نفس `id`, `owner_user_id`, `ownership_percentage`). تحقق
   إضافي: نفس `unit_id` بـ`tenant_id=2` (مستأجر خطأ) → `NotFoundError`
   فعليًا (تأكيد الـtenant scoping، مش مجرد افتراض).
2. `test_get_asset_tokenization_none_then_real_record` — قبل أي تجزئة:
   `service.get_asset_tokenization` رجعت `None` فعليًا (مش استثناء —
   يطابق افتراض الفرونت إند "هذا العقار غير مجزأ حاليًا"). بعد إنشاء
   `AssetTokenization` حقيقي عبر الـrepo: نفس الاستدعاء رجع الكائن
   الصحيح (`total_shares=500` مؤكَّد).
3. `test_get_smart_contract_status_real_record_and_not_found` — عقد
   ذكي حقيقي أُنشئ (`execution_status="PENDING"`)، الاستدعاء رجعه
   بالضبط. معرف غير موجود (`999999999`) → `NotFoundError` فعليًا.
   نفس المعرف الصحيح بـ`tenant_id=2` (مستأجر خطأ) → `NotFoundError`
   فعليًا أيضًا (تأكيد إضافي إن `repo.get_smart_contract` بتفلتر
   بـ`tenant_id` في نفس الاستعلام، مش بعد الجلب).

**صفر بيانات throwaway متبقية** — كل الاختبارات نظّفت في `finally`
(تأكيد ضمني: تشغيل الاختبارات الثلاثة تتابعيًا بدون تعارض unique
constraints يعني التنظيف اشتغل من أول مرة).

### ملاحظة جانبية غير حرجة (موثَّقة للأمانة، صفر أثر على النطاق)

تحذيرات `DeprecationWarning` (`datetime.utcnow()`, Redis `close()`
القديمة) ظهرت أثناء التشغيل — **موجودة من قبل في نفس نمط الكود
المستخدَم في الاختبارات المرجعية القديمة** (`test_realestate_tokenize_asset_ownership_check.py`
نفسها بتستخدم `datetime.utcnow()`)، مش ناتجة عن هذا التعديل، وخارج
نطاق هذه الجلسة تمامًا.

**صفر مسار هجوم مطلوب هنا** — الثلاثة دول GET بسيطة بدون منطق صلاحية
معقّد (فقط tenant scoping، مؤكَّد حيًا أعلاه)، خلافًا لـ#4/#5 القادمة
اللي هتحتاج فحص ownership كامل + مسار هجوم صريح (نفس منهجية
`rent_unit`/`tokenize_asset`).

**الخطوة التالية:** Migration الأعمدة التسويقية الخمسة على
`property_units` + #1 (`getProperties`)/#2 (`getProperty`)/#3
(`createProperty`).

---

## خطوة 7: تعديل مبرَّر على قيم `status` Enum — قبل التنفيذ

المستخدم اقترح `AVAILABLE, SOLD, RENTED, UNDER_OFFER` مع إذن صريح
بالتعديل لو فيه قيم عمل مختلفة فعليًا. قراءة حية لـ
`eppne-web/app/(dashboard)/realestate/property/[id]/page.tsx` (سطر
54-59) أظهرت إن الفرونت إند **بالفعل** عنده `statusColors` مُعرَّفة
لأربع قيم: `AVAILABLE, SOLD, RENTED, UNDER_CONSTRUCTION` — مش
`UNDER_OFFER` (قيمة غير مستخدَمة في أي مكان في الكود الحالي). استُخدمت
`UNDER_CONSTRUCTION` بدل `UNDER_OFFER` لتطابق الكود الفرونت إند الموجود
فعليًا بالحرف، بدل افتراض قيمة جديدة غير مُستخدَمة.

---

## خطوة 8: تنفيذ Migration + #1/#2/#3 — ✅ مكتمل ومتحقَّق حيًا

### 8.1 الـModel (`models.py`)

- `PropertyStatus(str, enum.Enum)` جديد: `AVAILABLE, SOLD, RENTED, UNDER_CONSTRUCTION`.
- 5 أعمدة جديدة على `PropertyUnit`: `title` (`String(255)`, nullable)،
  `description` (`Text`, nullable)، `location` (`String(255)`, nullable)،
  `cover_image_url` (`Text`, nullable)، `status`
  (`SQLEnum(PropertyStatus)`, `nullable=False`, `default=PropertyStatus.AVAILABLE`).

### 8.2 الـMigration (`migrations/versions/043_add_marketing_fields_to_property_units.py`)

**اكتشاف حي أثناء التنفيذ (وليس افتراضًا مسبقًا):** أول محاولة
(`sa.Enum(..., name='propertystatus')` مباشرة جوّه `op.add_column`)
فشلت فعليًا:
```
sqlalchemy.exc.ProgrammingError: UndefinedObjectError: type "propertystatus" does not exist
[SQL: ALTER TABLE property_units ADD COLUMN status propertystatus DEFAULT 'AVAILABLE' NOT NULL]
```
السبب: عكس `create_table` (بينشئ نوع الـEnum تلقائيًا)، `op.add_column`
**لا** ينشئ نوع الـPostgres Enum الأصلي تلقائيًا. بفضل الـtransactional
DDL (نفس نمط `env.py` الموثَّق في migration 035)، الفشل رجّع الترانزاكشن
بالكامل — تأكيد حي عبر `alembic current` بعد الفشل: لسه واقف على
`042_add_held_balances_to_wallets`، **صفر أعمدة معلَّقة جزئيًا**.

**الإصلاح:** `postgresql.ENUM(..., name='propertystatus', create_type=False)`
+ استدعاء صريح `property_status_enum.create(op.get_bind(), checkfirst=True)`
قبل `op.add_column` للعمود نفسه. نفس النمط بالمقلوب في `downgrade`
(`drop_column` أولاً، بعدين `property_status_enum.drop(...)`).

**تشغيل حي:** `alembic upgrade head` نجح فعليًا
(`042_add_held_balances_to_wallets → 043_add_marketing_fields_to_property_units`).
**تحقق حي إضافي عبر استعلام مباشر لـ`information_schema.columns`**
(صفر اعتماد على نجاح الأمر فقط): كل الأعمدة الخمسة موجودة فعليًا بالأنواع
الصحيحة، والعمود `status` من نوع `USER-DEFINED` (`propertystatus`) بقيمة
افتراضية `'AVAILABLE'::propertystatus` مطبَّقة فعليًا على مستوى DB.

### 8.3 `schemas.py`

- `PropertyUnitCreate` + `PropertyUnitResponse` (بالوراثة): 5 حقول
  جديدة (`title`, `description`, `location`, `cover_image_url` —
  Optional، `status` — افتراضي `PropertyStatus.AVAILABLE`).
- **لم يُضَف `PropertyUnitUpdate` في هذه الخطوة عمدًا** (جزء من نطاق
  #4/#5 القادمة، مش هذه الخطوة — التزامًا بالفصل الصريح بين المراحل
  اللي طلبه المستخدم).

### 8.4 `repository.py`

`list_units` اتوسّعت بباراميتر اختياري `property_type` (فلترة إضافية،
صفر تغيير على السلوك الافتراضي لأي استدعاء موجود — `list_units_for_sale`
اللي بتستخدمها مش هتتأثر لأنها مش بتمرر القيمة الجديدة).

### 8.5 `service.py`

- `list_property_units(tenant_id, property_type?, development_id?, skip, limit)`
  — عامة، `for_sale=False` دايمًا (بعكس `list_units_for_sale` الموجودة
  اللي فضلت زي ما هي بدون أي تعديل).
- `get_property_unit(unit_id, tenant_id)` — نفس نمط `get_unit_ownerships`
  (خطوة 6): `repo.get_unit` + تحقق `tenant_id` + `NotFoundError`.
- `create_property_unit` **لم تتغيّر إطلاقًا** — الحقول التسويقية بتتدفّق
  تلقائيًا عبر `data.model_dump()` الموجود بالفعل، مؤكَّد حيًا (خطوة
  8.6 أدناه).

### 8.6 `router.py`

- `GET /realestate/units` (قائمة عامة) → `list[PropertyUnitResponse]`
  — أُضيفت **قبل** `GET /units/for-sale` (لا تعارض مسارات، صفر تأثير
  على ترتيب مطابقة FastAPI لمسارات `/units/for-sale` أو
  `/units/{unit_id}/...` الأخرى).
- `GET /realestate/units/{unit_id}` → `PropertyUnitResponse` — أُضيفت
  **بعد** `GET /units/for-sale` صراحةً (لازم يفضل الترتيب ده — لو
  اتحطت قبلها، أي طلب لـ`/units/for-sale` كان هيتحاول يتفسَّر كـ
  `unit_id="for-sale"` ويفشل بـ422 بدل ما يوصل للراوت الصحيح؛ الترتيب
  الحالي مؤكَّد آمن).

### التحقق الحي (pytest + DB حقيقية)

ملف جديد: `eppne-backend/tests/test_realestate_property_crud_endpoints.py`
(اختباران، نفس منهجية throwaway + تنظيف `finally`).

**تشغيل حي:** `venv/Scripts/python.exe -m pytest tests/test_realestate_property_crud_endpoints.py -v`
→ **2 passed** (86 ثانية):

1. `test_create_property_unit_with_marketing_fields_and_default_status`
   — إنشاء وحدة بالحقول التسويقية الخمسة عبر `service.create_property_unit`
   الموجودة بالفعل (بدون أي تعديل عليها)، تأكيد مستقل من الـDB إن
   `title`/`location` اتخزّنوا بالضبط، وإن `status` طلع
   `PropertyStatus.AVAILABLE` تلقائيًا بدون تمرير صريح (الافتراضي
   اشتغل فعليًا).
2. `test_list_and_get_property_unit_live` — وحدة **غير متاحة للبيع
   ولا للإيجار عمدًا** (`is_available_for_sale=False`,
   `is_available_for_rent=False`) — `list_units_for_sale` القديمة ماكانتش
   هتجيبها إطلاقًا، لكن `list_property_units` الجديدة (العامة) جابتها
   فعليًا (تأكيد الفرق الجوهري بين الدالتين حيًا، مش افتراضًا). فلترة
   `property_type=OFFICE` جابت الوحدة، `property_type=APARTMENT` ماجابتهاش
   (تأكيد الفلترة الجديدة في `repo.list_units` شغّالة فعليًا). `get_property_unit`
   رجّعت الوحدة الصحيحة بـ`tenant_id` صح، ورفعت `NotFoundError` فعليًا
   بـ`tenant_id` غلط.

### تحقق إضافي: صفر رجعية على باقي اختبارات realestate

`pytest tests/ -k realestate` (يشمل الاختبارات المرجعية القديمة:
`test_realestate_insurance_savepoint.py`,
`test_realestate_rent_unit_ownership_check.py`,
`test_realestate_tokenize_asset_ownership_check.py` + الملفين الجديدين
من خطوة 6/8) — **قيد التشغيل، النتيجة ستُوثَّق فور اكتمالها قبل
الانتقال لخطوة #4/#5.**

**الخطوة التالية:** `updateProperty` (#4) و`deleteProperty` (#5) —
`PropertyUnitUpdate` schema + فحص ملكية بنمط `_get_land_owner_for_unit`
+ قرار منع الحذف مع ملكيات/تجزئة فعّالة (معتمَد) + تحقق حي لمسار شرعي
ومسار هجوم.

---

## خطوة 9: تحقق إضافي — الـ3 فشلات في الـsuite الكامل غير مرتبطة بهذه الجلسة

بعد خطوة 8، تشغيل `pytest tests/ -k realestate` (كل اختبارات الدومين،
القديمة والجديدة مع بعض) رجّع **3 فشلات** لم تكن متوقَّعة:
```
FAILED tests/test_realestate_rent_unit_ownership_check.py::test_rent_unit_succeeds_for_real_owner
FAILED tests/test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes
FAILED tests/test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug
```

**تحقيق حي فوري (مش افتراض):** إعادة تشغيل أول فشل منفردًا
(`test_rent_unit_succeeds_for_real_owner`) رجّعت نفس الفشل، والـtraceback
الكامل أظهر السبب الحقيقي:
```
app\domains\realestate\service.py:69: PermissionDeniedError:
Real Estate feature is not included in your current plan.
```
هذا نفس التحذير الموثَّق **بالفعل** كتعليق داخل
`test_realestate_tokenize_asset_ownership_check.py` (خطة اشتراك
`tenant_id=1` الحالية في قاعدة بيانات الديف ما فيهاش feature
`real_estate`/`real_estate_tokenization` مفعّلة) — والملفين الفاشلين
التانيين (`test_saas_active_subscription.py`) **مصمَّمين عمدًا** (تأكيد من
docstring الملف نفسه) ليتحققوا من إن `_check_saas_limits` الحقيقية
(**بدون** `monkeypatch` عليها) بتعدي بنجاح — يعني فشلهم دليل مباشر إضافي
إن حالة بيانات الاشتراك في الـDB الحالية تغيّرت (drift بيئي)، **مش أي
كود لمسته هذه الجلسة**. صفر تعديل من هذه الجلسة على `saas/service.py`،
`service.py:_check_saas_limits` نفسها، أو أي بيانات اشتراك — **الفشول
الثلاثة موجودة قبل أي تعديل من هذه الجلسة وغير مرتبطة بالـmigration أو
الـendpoints الجديدة إطلاقًا**. خارج نطاق هذه الجلسة (مشكلة بيانات
بيئة ديف، مش عيب تصميم أو كود) — موثَّق هنا للأمانة، صفر إصلاح.

---

## خطوة 10: تنفيذ #4/#5 (`updateProperty`/`deleteProperty`) — ✅ مكتمل ومتحقَّق حيًا

### 10.1 `repository.py`

- `update_unit(unit_id, **kwargs)` — تحديث جزئي (يستبعد أي مفتاح `None`
  تلقائيًا)، نفس نمط `update_land_value`/`update_development_progress`
  الموجودَين بالفعل.
- `soft_delete_unit(unit_id)` — `is_deleted=True`, `deleted_at=func.now()`.

### 10.2 `schemas.py`

`PropertyUnitUpdate` جديد (كل الحقول `Optional`، نفس حقول
`PropertyUnitCreate` + التسويقية) — أُضيف الآن (مش في خطوة 8) التزامًا
بالفصل الصريح بين المراحل.

### 10.3 `service.py`

```python
async def update_property_unit(self, unit_id, tenant_id, updater_id, data):
    unit = await self.repo.get_unit(unit_id)
    if not unit or unit.tenant_id != tenant_id:
        raise NotFoundError("Property unit not found")
    owner = await self._get_land_owner_for_unit(unit, tenant_id)
    if cast(int, owner.id) != updater_id:
        raise PermissionDeniedError("ليس لديك صلاحية تعديل هذه الوحدة")
    return await self.repo.update_unit(unit_id, **data)

async def delete_property_unit(self, unit_id, tenant_id, deleter_id):
    unit = await self.repo.get_unit(unit_id)
    if not unit or unit.tenant_id != tenant_id:
        raise NotFoundError("Property unit not found")
    owner = await self._get_land_owner_for_unit(unit, tenant_id)
    if cast(int, owner.id) != deleter_id:
        raise PermissionDeniedError("ليس لديك صلاحية حذف هذه الوحدة")
    if await self.repo.get_ownerships_by_unit(unit_id):
        raise ValidationError("لا يمكن حذف وحدة عندها ملكيات جزئية فعّالة")
    if await self.repo.get_tokenization_by_unit(unit_id, tenant_id):
        raise ValidationError("لا يمكن حذف وحدة مجزأة (tokenized) بالفعل")
    await self.repo.soft_delete_unit(unit_id)
```

فحص الملكية **حرفيًا نفس نمط** `tokenize_asset`/`rent_unit`
(`_get_land_owner_for_unit` + مقارنة `owner.id`) — صفر منطق جديد مخترَع،
نفس القاعدة المُتَّبعة في الدومين بالفعل.

### 10.4 `router.py`

- `PATCH /realestate/units/{unit_id}` → `PropertyUnitResponse`
  (`@rate_limit`، `PropertyUnitUpdate.model_dump(exclude_unset=True)`
  — يمرّر فقط الحقول اللي المستخدم بعتها فعليًا، مش كل الحقول بقيم
  `None` افتراضية).
- `DELETE /realestate/units/{unit_id}` → `204 No Content`.

### التحقق الحي (pytest + DB حقيقية، مسار شرعي + مسار هجوم لكل عملية)

ملف جديد: `eppne-backend/tests/test_realestate_update_delete_property_unit_ownership_check.py`
(5 اختبارات).

**تشغيل حي:** `venv/Scripts/python.exe -m pytest tests/test_realestate_update_delete_property_unit_ownership_check.py -v`
→ **5 passed** (168 ثانية):

1. `test_update_property_unit_succeeds_for_real_owner` — المالك الحقيقي
   عدّل `title`+`sale_price_mrusdt` → نجح فعليًا، تأكيد مستقل من الـDB.
2. `test_update_property_unit_rejects_non_owner_with_403` — مهاجم (مستخدم
   حقيقي، مش مالك) حاول يعدّل نفس الوحدة → `PermissionDeniedError` فعليًا
   بنص الرسالة الصحيح، **وتأكيد إضافي إن العنوان لم يتغيّر فعليًا في الـDB**
   (صفر تعديل جزئي متسرّب رغم الرفض).
3. `test_delete_property_unit_succeeds_for_real_owner_with_no_ownerships`
   — المالك الحقيقي حذف وحدة بلا ملكيات → `is_deleted=True` و`deleted_at`
   مُسجَّلين فعليًا في الـDB.
4. `test_delete_property_unit_rejects_non_owner_with_403` — نفس نمط
   الهجوم، تأكيد `is_deleted=False` فضلت زي ما هي.
5. `test_delete_property_unit_blocked_when_active_ownership_exists` —
   **المالك الحقيقي نفسه** (صفر مشكلة صلاحية) حاول يحذف وحدة عندها
   ملكية جزئية فعّالة (30% لمشتري تاني) → `ValidationError` فعليًا
   بنفس الرسالة المتوقَّعة، وتأكيد `is_deleted=False` (الحذف اتمنع
   فعليًا وليس بالصدفة).

### تحقق نهائي: `pytest tests/ -k realestate` (كل ملفات الدومين مع بعض)

**تشغيل حي كامل بعد كل تعديلات الجلسة (خطوات 6+8+10 مجتمعة):**
`23 passed, 3 failed, 89 deselected, 2 xfailed` (292 ثانية).

الفشول الثلاثة **بالضبط نفس الثلاثة** الموثَّقة في خطوة 9 (drift بيئي
في بيانات اشتراك `tenant_id=1` — `real_estate` feature غير مفعّلة —
غير مرتبط بأي كود لمسته هذه الجلسة)، **صفر فشل جديد**. الـ23 اختبار
الناجح يشمل: كل الاختبارات المرجعية القديمة (`insurance_savepoint`,
`rent_unit_ownership_check` [عدا الفشل المعزول أعلاه],
`tokenize_asset_ownership_check`) + الملفات الثلاثة الجديدة من هذه
الجلسة (`getter_endpoints_wiring` [3]، `property_crud_endpoints` [2]،
`update_delete_property_unit_ownership_check` [5]) = 10 اختبارات جديدة،
كلها ناجحة، صفر أثر جانبي على أي اختبار قديم.

---

## ملخص حالة الجلسة النهائي

| الخطوة | الحالات المُنفَّذة | الحالة |
|---|---|---|
| 6 | `getPropertyOwnerships`, `getSmartContractStatus`, `getAssetTokenization` (وصلة service+router فقط) | ✅ مكتمل، 3 اختبارات حية ناجحة |
| 8 | Migration الأعمدة التسويقية الخمسة + `getProperties`, `getProperty`, `createProperty` | ✅ مكتمل، migration مُطبَّقة حيًا على DB الديف، 2 اختبار حي ناجح |
| 10 | `updateProperty`, `deleteProperty` (فحص ملكية + منع حذف مع ملكيات فعّالة) | ✅ مكتمل، 5 اختبارات حية ناجحة (مسار شرعي + هجوم لكل عملية) |

**الحالات الثمانية الأصلية من جلسة 2026-08-29 — كل الثمانية أُنجزت
بالكامل في الباك إند** (`getProperties`, `getProperty`, `createProperty`,
`updateProperty`, `deleteProperty`, `getPropertyOwnerships`,
`getSmartContractStatus`, `getAssetTokenization`). **إجمالي 10 ملفات
اختبار جديدة (بينهم 3 ملفات جديدة كليًا هذه الجلسة)، صفر رجعية على أي
اختبار موجود مسبقًا** (الفشول الثلاثة المتبقية سابقة الوجود وموثَّقة
كخارج النطاق).

**متبقٍ خارج نطاق الباك إند (توثيق فقط، صفر تنفيذ مطلوب هنا):**
- ربط الفرونت إند فعليًا بالـendpoints الجديدة (`hooks/realestate/*.ts`،
  `services/realestate.ts`) — نفس نمط الإصلاحات المرحلة الأولى من جلسة
  2026-08-29 (استيراد صحيح + إزالة `.then(res=>res.data)` لو موجودة).
- `property.owner_id` في `property/[id]/page.tsx`: `PropertyUnitResponse`
  الحالي **لا** يحتوي `owner_id` مباشرة (الملكية عبر سلسلة
  `unit → development → land_asset → owner_id`، لا عمود مباشر على
  الوحدة) — لم يكن من ضمن الأعمدة الخمسة المعتمَدة، يحتاج قرار منفصل
  لاحقًا (إضافة عمود/computed field، أم تعديل الفرونت إند ليستخدم
  السلسلة الصحيحة).
- `SmartContractStatusMonitor` (كود يتيم غير مستخدَم حاليًا في أي صفحة)
  + عدم تطابق أسماء الحقول (`status`/`tx_hash` بالفرونت إند مقابل
  `execution_status`/`blockchain_tx_hash` في `SmartContractResponse`) —
  يحتاج تعديل استهلاك فرونت إند بسيط عند تفعيل المكوّن فعليًا.
- الفشول الثلاثة غير المرتبطة (خطوة 9) — مشكلة بيانات بيئة ديف
  (`real_estate` feature غير مفعّلة في خطة اشتراك `tenant_id=1`)، تستحق
  بند backlog منفصل خارج نطاق هذه الجلسة.

**صفر تنفيذ إضافي متبقٍ في نطاق هذه الجلسة — كل الحالات الثمانية
المعتمَدة من جدول التصميم مُنفَّذة ومتحقَّق منها حيًا بالكامل.**
