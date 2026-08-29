# جلسة: realestate-hooks-layer-nonexistent-function-imports

**تاريخ البدء:** 2026-08-29
**الحالة:** ⏸️ التحقيق الكامل لكل الـ10 ملفات (4 hooks + 6 إضافية) مكتمل
ومؤكَّد حيًا، بما فيه اكتشاف نظامي جديد (مشكلة unwrap في خطوة 6). بانتظار
قرار المستخدم على الجدول الموحّد النهائي (خطوة 9) قبل أي تنفيذ. صفر
إصلاح حتى الآن.

## السياق
اكتُشف هذا البند أثناء جلسة `constructor-mismatch-backlog #43` (2026-08-29)
كاكتشاف جانبي، موثَّق في PROGRESS_LOG.md، ولم يُصلَح وقتها (خارج نطاق #43).

المشكلة الموصوفة: `eppne-web/hooks/realestate/*.ts` (4 ملفات) تستورد دوال
غير موجودة إطلاقًا من الـservice المقابل — ليس مجرد اختلاف تسمية
(camelCase مقابل PascalCase مثل #43)، بل أسماء دوال مختلفة تمامًا عن
الـmethods الحقيقية. هذا يعطّل build لـ4 مكوّنات + صفحة realestate كاملة.

**المطلوب أولًا:** تحقيق فقط (تحديد الملفات، الدوال الغلط، المقابل
الصحيح إن وُجد، تصنيف كل حالة) + تأكيد حي لنطاق العطل عبر build/tsc.
**صفر تنفيذ** حتى المراجعة والموافقة الصريحة.

---

## خطوة 1: تحديد الملفات المتأثرة

عبر Glob:

```
eppne-web/hooks/realestate/useProperties.ts
eppne-web/hooks/realestate/useTokenization.ts
eppne-web/hooks/realestate/useMyOwnerships.ts
eppne-web/hooks/realestate/usePropertyOwnerships.ts
```

Backend المقابل:
```
eppne-backend/app/domains/realestate/_init__.py   (ملاحظة: اسم خاطئ، معروف من PROJECT_AUDIT.md)
eppne-backend/app/domains/realestate/schemas.py
eppne-backend/app/domains/realestate/models.py
eppne-backend/app/domains/realestate/repository.py
eppne-backend/app/domains/realestate/router.py
eppne-backend/app/domains/realestate/service.py
```

(سيُستكمل بالتفصيل لكل ملف أدناه أثناء الفحص الحي)

---

## خطوة 2: قراءة الملفات الأربعة + طبقة service الوسيطة

اكتُشف أن الهوكس لا تستورد من الـbackend مباشرة، بل من طبقة وسيطة في
الفرونت إند: `eppne-web/services/realestate.ts`. هذا الملف يُصدِّر
**كائن واحد فقط** `export const RealEstateService = { ... }` بميثودز،
**وليس named exports منفصلة**. كل الميثودز الفعلية الموجودة فيه:

```
createLandAsset, getMyLands, revalueLand, createDevelopment, getDevelopment,
createPropertyUnit, listUnitsForSale, buyFraction, getMyOwnerships,
createRentalContract, createMasterPlan, tokenizeAsset, deploySmartContract
```

تأكيد حي من قراءة `eppne-backend/app/domains/realestate/service.py` +
`router.py`: **لا يوجد مفهوم "Property" عام (CRUD كامل) في الباك إند
إطلاقًا** — الكيانات الحقيقية هي `LandAsset`, `RealEstateDevelopment`,
`PropertyUnit`, `MasterPlan`, `AssetTokenization`, `SmartContractEngine`,
`RentalContract`, `PropertyOwnership`. كذلك تأكدنا من
`eppne-web/types/realestate.ts` (156 سطر) — لا يوجد فيه `Property` ولا
`PropertyFormData` ولا `TokenizationFormData` (بحث `grep` صفر نتائج).

---

## خطوة 3: تحقيق حي عبر tsc (صفر افتراض)

تشغيل: `npx tsc --noEmit -p tsconfig.json` من `eppne-web/` — exit code 1.
مخرجات مفلترة بـ `realestate` (مقتبَسة حرفيًا من الأداة، بدون تلخيص):

```
hooks/realestate/useMyOwnerships.ts(3,10): error TS2305: Module '"@/services/realestate"' has no exported member 'getMyOwnerships'.
hooks/realestate/useProperties.ts(4,3): error TS2305: Module '"@/services/realestate"' has no exported member 'getProperties'.
hooks/realestate/useProperties.ts(5,3): error TS2305: Module '"@/services/realestate"' has no exported member 'getProperty'.
hooks/realestate/useProperties.ts(6,3): error TS2305: Module '"@/services/realestate"' has no exported member 'createProperty'.
hooks/realestate/useProperties.ts(7,3): error TS2305: Module '"@/services/realestate"' has no exported member 'updateProperty'.
hooks/realestate/useProperties.ts(8,3): error TS2305: Module '"@/services/realestate"' has no exported member 'deleteProperty'.
hooks/realestate/useProperties.ts(10,15): error TS2305: Module '"@/types/realestate"' has no exported member 'Property'.
hooks/realestate/useProperties.ts(10,25): error TS2305: Module '"@/types/realestate"' has no exported member 'PropertyFormData'.
hooks/realestate/usePropertyOwnerships.ts(3,10): error TS2305: Module '"@/services/realestate"' has no exported member 'getPropertyOwnerships'.
hooks/realestate/useTokenization.ts(3,10): error TS2305: Module '"@/services/realestate"' has no exported member 'getAssetTokenization'.
hooks/realestate/useTokenization.ts(3,32): error TS2305: Module '"@/services/realestate"' has no exported member 'createTokenization'.
hooks/realestate/useTokenization.ts(3,52): error TS2305: Module '"@/services/realestate"' has no exported member 'buyFractionalShare'.
hooks/realestate/useTokenization.ts(4,15): error TS2305: Module '"@/types/realestate"' has no exported member 'TokenizationFormData'.
```

**اكتشاف جانبي مهم (خارج نطاق الـ4 ملفات المطلوبة، لكن لازم يُبلَّغ فورًا):**
نفس الـtsc أظهر إن العطل أوسع بكثير من الـ4 hooks. ملفات إضافية بتستورد
من نفس `services/realestate.ts` بأسماء غير موجودة أو غير متطابقة:

```
app/(dashboard)/realestate/page.tsx(7,10): 'getAvailableProperties' غير موجودة
app/(dashboard)/realestate/property/[id]/page.tsx(7,23): 'useUpdateProperty' غير موجودة في useProperties.ts نفسه
components/realestate/InvestorPortfolio.tsx(5,10-27): 'getMyOwnerships' + 'getSmartContractStatus' غير موجودة
components/realestate/MasterPlanExplorer.tsx(6,10): 'getMyLands' غير موجودة (بالاسم كـ named export)
components/realestate/SmartContractDashboard.tsx(6,10): 'deploySmartContract' غير موجودة (بالاسم كـ named export)
components/realestate/TokenizationExchange.tsx(6,10-27): 'getUnitsForSale' + 'buyFractionalOwnership' غير موجودة
```

بالإضافة لأخطاء غير مرتبطة بالموضوع إطلاقًا (packages مفقودة: `date-fns/ar`،
`uuid` — ديبندنسي مش موجودة في node_modules، ونطاق منفصل تمامًا).

**الخلاصة:** المشكلة مش محصورة في الـ4 hooks كما وُصفت في بداية الجلسة —
هي عطل بنيوي في `services/realestate.ts` نفسه: الملف بيصدّر **كائن واحد**
(`RealEstateService.methodName`) بينما **كل** المستهلكين (hooks + components
+ pages) بيتوقعوا named exports مفردة، وبعضهم بأسماء مختلفة تمامًا. هذا
اكتشاف جانبي جديد يستحق قرار نطاق منفصل من المستخدم — تم توثيقه هنا فورًا
ولم يُخفَ للنهاية.

---

## خطوة 4: تصنيف الحالات (لكل الـ4 ملفات المطلوبة تحديدًا)

| # | الملف | الدالة/النوع المستورَد (غلط) | الموجود فعليًا في service | التصنيف |
|---|---|---|---|---|
| 1 | `useProperties.ts` | `getProperties`, `getProperty`, `createProperty`, `updateProperty`, `deleteProperty` | **لا يوجد** — لا مفهوم "Property" CRUD عام في الباك إند إطلاقًا. الكيانات الحقيقية: `LandAsset`/`RealEstateDevelopment`/`PropertyUnit`. أقرب شيء: `createPropertyUnit` (create فقط، لا يوجد get/update/delete لوحدة عقارية إطلاقًا) | **(ب)** قرار نطاق أوسع |
| 1b | نفس الملف | types `Property`, `PropertyFormData` | **لا يوجد** في `types/realestate.ts` (156 سطر، تأكيد grep) | **(ب)** |
| 2 | `useTokenization.ts` | `getAssetTokenization` | **لا يوجد** — لا GET endpoint/method لجلب tokenization لوحدة، فقط create | **(ب)** |
| 2b | نفس الملف | `createTokenization` | قريب من `tokenizeAsset` — لكن اسم **و** توقيع مختلفَين (`tokenizeAsset(unitId, data, headers)` مقابل `createTokenization(data)` مع `unit_id` جوّه الـdata) | **مختلط (أ+توقيع)** |
| 2c | نفس الملف | `buyFractionalShare` | قريب من `buyFraction` — اسم مختلف + توقيع مختلف قليلًا (idempotencyKey كـ arg منفصل) | **مختلط (أ+توقيع)** |
| 2d | نفس الملف | type `TokenizationFormData` | **لا يوجد** إطلاقًا | **(ب)** |
| 3 | `useMyOwnerships.ts` | `getMyOwnerships` | **موجودة بالضبط** — `RealEstateService.getMyOwnerships` (نفس الاسم، نفس التوقيع، بدون باراميترات) | **(أ)** تصحيح نمط استيراد فقط |
| 4 | `usePropertyOwnerships.ts` | `getPropertyOwnerships` | **لا يوجد** — لا endpoint/method لجلب ownerships حسب property/unit id، فقط `get_my_ownerships` لملكيات المستخدم الحالي | **(ب)** |

كل الأخطاء أعلاه مؤكدة حرفيًا من `npx tsc --noEmit -p tsconfig.json`
(exit code 1) — الاقتباسات الحرفية في خطوة 3 أعلاه.

**صفر تنفيذ حتى الآن.**

---

## السؤال المعلَّق للمستخدم (بعد عرض الجدول) — تم الرد

المستخدم طلب إكمال التحقيق (توثيق فقط، صفر تنفيذ) للـ6 ملفات الإضافية.
**صفر تنفيذ لسه ساري.**

---

## خطوة 5: قراءة الملفات الـ6 الإضافية بالتفصيل

**ملاحظة تصحيح مسار:** الملف المقصود بـ"page.tsx" في السؤال هو
`app/(dashboard)/realestate/page.tsx` تحديدًا (وليس `tokenization/page.tsx`
ولا `ownerships/page.tsx` اللي ظهروا برضو في مخرجات tsc لكن ملهمش ذِكر
صريح في الـ6 المطلوبة — راجع "اكتشاف جانبي إضافي" في آخر هذه الخطوة).

**ملاحظة ثانوية مثيرة:** أول سطر تعليق داخل `app/(dashboard)/realestate/page.tsx`
مكتوب فيه غلط `// app/(dashboard)/realestate/tokenization/page.tsx` —
تعليق قديم/mislabeled من نسخ-لصق واضح، اتأكد إن محتوى الملف فعلاً بيطابق
أخطاء tsc المسجّلة على `page.tsx` (رقم السطر 7، 166، 168...الخ) وليس على
`tokenization/page.tsx` الحقيقي. تعليق تجميلي بس، بدون أثر وظيفي — موثَّق
هنا للأمانة فقط.

### 1) `app/(dashboard)/realestate/page.tsx`
- `import { getAvailableProperties } from '@/services/realestate'` (سطر 7)
- `import { useCreateTokenization } from '@/hooks/realestate/useTokenization'` (سطر 8) — مغطاة بالفعل في جدول الـ4 hooks (حالة 2b)
- `import { useAssetTokenization } from '@/hooks/realestate/useTokenization'` (سطر 9) — مغطاة بالفعل (حالة 2)

`getAvailableProperties`: **لا يوجد** أي method بهذا الاسم أو بمعنى مطابق.
أقرب مرشح منطقي هو `listUnitsForSale` (`GET /realestate/units/for-sale`)
لكن الشكل مختلف جوهريًا: `PropertyUnitResponse` (تأكيد من `schemas.py`
سطر 54) **لا يحتوي على حقل `title`** أصلاً، بينما الصفحة بتستخدم
`p.title` (سطر 99) — يعني حتى لو غيّرنا الاسم، البيانات الراجعة مش هتوفّي
بمتطلبات الواجهة. **(ب)**

ملاحظة إضافية: `tokenizations` (الأسطر 36-43) مربوطة بـ query وهمي
بيرجّع `[]` دايمًا (تعليق بالكود: "في الإنتاج، سيتم استخدام نقطة نهاية
مخصصة") — كود placeholder مش متصل بأي endpoint حقيقي، مش خطأ استيراد،
لكن يفسّر أخطاء `Property 'id' does not exist on type 'never'`
(الأسطر 166-195 في tsc) — نطاق منفصل تمامًا (dead code)، غير مذكور في
جدول التصنيف لأنه مش استيراد غلط، بل endpoint لسه مش موجود بتاتًا.

### 2) `app/(dashboard)/realestate/property/[id]/page.tsx`
- `useProperty, useUpdateProperty` من `useProperties.ts` (سطر 7)
- `useAssetTokenization` من `useTokenization.ts` (سطر 8)
- `useBuyFractionalShare` من `useTokenization.ts` (سطر 9)
- `usePropertyOwnerships` (سطر 10)

`useProperty`, `useAssetTokenization`, `useBuyFractionalShare`,
`usePropertyOwnerships` — **مغطاة بالكامل بالفعل** في جدول الـ4 hooks
(حالات 1، 2، 2c، 4 على الترتيب) — نفس الجذر بالظبط.

`useUpdateProperty` — **اكتشاف جديد**: الاسم ده مش موجود حتى **جوّه ملف
الهوك نفسه** `useProperties.ts` (اللي بيصدّر بس: `useProperties`,
`useProperty`, `useCreateProperty`) — مفيش `useUpdateProperty` إطلاقًا،
مش مجرد استيراد غلط من مصدر تاني. وبالتوازي مفيش أي endpoint تحديث
لوحدة عقارية (`PropertyUnit`) في `router.py` أصلًا (لا `PATCH` ولا `PUT`
لـ `/realestate/units/{id}`) — يعني الوظيفة نفسها (تعديل بيانات وحدة)
غير موجودة في الباك إند إطلاقًا. **(ب)** — أوسع درجات "(ب)" لأنها مفقودة
على مستويين (الهوك + الservice + الـrouter).

### 3) `components/realestate/InvestorPortfolio.tsx`
- `import { getMyOwnerships, getSmartContractStatus } from '@/services/realestate'` (سطر 5)

`getMyOwnerships`: موجودة بالضبط كـ `RealEstateService.getMyOwnerships`
(نفس حالة hook رقم 3) — **(أ)** من ناحية الاسم، **لكن انظر خطوة 6 أدناه**
— فيه مشكلة تانية أعمق في نفس الاستدعاء.

`getSmartContractStatus`: **لا يوجد إطلاقًا** — لا يوجد أي GET
endpoint/method لجلب حالة عقد ذكي بمعرفه (`router.py` فيه بس
`POST /realestate/smart-contracts` للإنشاء، مفيش
`GET /realestate/smart-contracts/{id}` ولا method مقابلة في service.py).
المكوّن `SmartContractStatusMonitor` (سطور 100-159) بيعمل polling كل
3 ثواني على endpoint مش موجود إطلاقًا — الميزة نفسها (متابعة حالة تنفيذ
العقد الذكي على البلوكشين) غير مبنية بالباك إند. **(ب)** قرار نطاق أوسع.

### 4) `components/realestate/MasterPlanExplorer.tsx`
- `import { getMyLands } from '@/services/realestate'` (سطر 6)

موجودة بالضبط كـ `RealEstateService.getMyLands` — نفس التوقيع تقريبًا
(`params?: {skip?, limit?}`، الاستدعاء `getMyLands({ limit: 20 })`
متوافق شكليًا). **(أ)** من ناحية الاسم — لكن انظر خطوة 6 (نفس مشكلة
unwrap).

### 5) `components/realestate/SmartContractDashboard.tsx`
- `import { deploySmartContract } from '@/services/realestate'` (سطر 6)

موجودة بالضبط كـ `RealEstateService.deploySmartContract`، والتوقيع
متطابق فعليًا (`data: {contract_type, reference_id, contract_metadata}`
يطابق `SmartContractCreate` بالظبط)، **وهذا الملف الوحيد اللي مش بيعمل
`.then(res => res.data)`** — بيرجّع الـpromise مباشرة من `mutationFn`.
**(أ) — أنظف حالة في كل المجموعة، تصحيح استيراد بس (namespace)، بدون أي
تعديل توقيع أو استهلاك.**

### 6) `components/realestate/TokenizationExchange.tsx`
- `import { getUnitsForSale, buyFractionalOwnership } from '@/services/realestate'` (سطر 6)

`getUnitsForSale`: قريبة من `listUnitsForSale` — اسم مختلف بس، الباراميتر
متوافق شكليًا (`{limit: 20}`). **مختلط (أ+توقيع)** — التفاصيل في خطوة 8.

`buyFractionalOwnership`: قريبة من `buyFraction` — اسم مختلف + الباراميتر
الثالث بشكل مختلف تمامًا (string خام مقابل object). **مختلط (أ+توقيع)**
— التفاصيل في خطوة 8.

---

## خطوة 6: اكتشاف نظامي جديد — عدم تطابق شكل الـresponse (`res.data`)

أثناء قراءة `services/realestate.ts` بالتفصيل (خطوة 2) لوحظ إن **كل**
ميثودز `RealEstateService` بترجع البيانات النهائية **مباشرة** (unwrapped)،
مش axios response object:

```ts
// services/realestate.ts — مثال حرفي (getMyOwnerships)
getMyOwnerships: async (): Promise<OwnershipResponse[]> => {
  try {
    const { data } = await apiClient.get<OwnershipResponse[]>("/realestate/my-ownerships", { withCredentials: true });
    return data;   // <-- بيرجع الـarray مباشرة، مش { data: [...] }
  } catch (error) { ... }
},
```

لكن **كل** المستهلكين (hooks + components) بيتعاملوا معاها وكأنها axios
response object، وبيعملوا `.then((res) => res.data)`:

```ts
// hooks/realestate/useMyOwnerships.ts
queryFn: () => getMyOwnerships().then((res) => res.data),
```

يعني حتى لو اتصلح اسم الاستيراد بس (بدون تعديل توقيع الاستهلاك)، الكود
هيتصرف غلط وقت التشغيل: `res` هتبقى فعليًا الـ array/object النهائي،
و`res.data` هترجع `undefined`. هذا **مش خطأ TS ظاهر دلوقتي** لأن الاستيراد
الفاشل بيخلي النوع `any` (فبيبلع `.data` بصمت) — يعني الخطأ ده **هيظهر
كـTS error جديد فور ما نصلّح الاستيراد**، مش قبلها. لازم يتوثّق كقرار
منفصل: هل نلف الservice بـ `{ data: ... }` عشان يفضل التوافق مع
`.then(res=>res.data)` في كل المستهلكين، ولا نمسح `.then(res=>res.data)`
من كل استدعاء ونستخدم النتيجة مباشرة؟

**الملفات المتأثرة بهذا الاكتشاف تحديدًا (بحث حي عبر Grep):**
`useMyOwnerships.ts`, `useProperties.ts` (كل الـ3 استدعاءات),
`useTokenization.ts` (استدعاء `getAssetTokenization` فقط —
`createTokenization`/`buyFractionalShare` بترجع مباشرة بدون `.then`),
`usePropertyOwnerships.ts`, `InvestorPortfolio.tsx` (استدعاءين:
`getMyOwnerships`, `getSmartContractStatus`), `MasterPlanExplorer.tsx`
(`getMyLands`), `page.tsx` (`getAvailableProperties`),
`TokenizationExchange.tsx` (`getUnitsForSale` + `response.data` في
`onSuccess`). **الوحيد الناجي من هذه المشكلة: `SmartContractDashboard.tsx`.**

---

## خطوة 7: جدول تصنيف الـ6 ملفات الإضافية

| # | الملف | الاستيراد الغلط | الموجود فعليًا | التصنيف |
|---|---|---|---|---|
| 5 | `page.tsx` | `getAvailableProperties` | لا يوجد — أقرب مرشح `listUnitsForSale` لكن شكل بيانات مختلف جوهريًا (لا `title`) | **(ب)** |
| 6 | `property/[id]/page.tsx` | `useProperty`, `useAssetTokenization`, `useBuyFractionalShare`, `usePropertyOwnerships` | مغطاة بالفعل في جدول الـ4 hooks (حالات 1/2/2c/4) | (مكرّر — راجع الجدول الأصلي) |
| 6b | نفس الملف | `useUpdateProperty` | **لا يوجد حتى جوّه ملف الهوك نفسه**، ولا endpoint تحديث وحدة عقارية في الباك إند إطلاقًا | **(ب)** أوسع حالات (ب) |
| 7 | `InvestorPortfolio.tsx` | `getMyOwnerships` | موجودة بالاسم، لكن استهلاكها بـ`.then(res=>res.data)` غلط (خطوة 6) | **(أ) + مشكلة unwrap** |
| 7b | نفس الملف | `getSmartContractStatus` | **لا يوجد** — لا GET endpoint لحالة عقد ذكي إطلاقًا | **(ب)** |
| 8 | `MasterPlanExplorer.tsx` | `getMyLands` | موجودة بالاسم والتوقيع، نفس مشكلة unwrap | **(أ) + مشكلة unwrap** |
| 9 | `SmartContractDashboard.tsx` | `deploySmartContract` | موجودة بالاسم **والتوقيع مطابق تمامًا**، بدون مشكلة unwrap (الوحيد) | **(أ) — أنظف حالة** |
| 10 | `TokenizationExchange.tsx` | `getUnitsForSale` | قريبة من `listUnitsForSale` (اسم فقط) + مشكلة unwrap | **مختلط (أ+توقيع)** |
| 10b | نفس الملف | `buyFractionalOwnership` | قريبة من `buyFraction` (اسم + شكل الباراميتر الثالث مختلف) + `response.data` unwrap في `onSuccess` | **مختلط (أ+توقيع)** |

---

## خطوة 8: توثيق التواقيع التفصيلي لكل حالة "مختلط (أ+توقيع)" (الدفعتين معًا)

### أ) `createTokenization` (هوك) مقابل `tokenizeAsset` (service)
```ts
// المتوقَّع في الاستدعاء (useTokenization.ts + page.tsx):
createTokenization(data: TokenizationFormData): Promise<...>
// طريقة النداء الفعلية:
createTokenization.mutate({ unit_id: selectedProperty, total_shares, share_price_mrusdt, minimum_investment_shares })

// الموجود فعليًا في service.ts:
tokenizeAsset: async (
  unitId: number,                                  // منفصل عن data
  data: TokenizationCreate,                         // بدون unit_id جواه
  headers?: { 'X-Tenant-ID'?: number }
) => Promise<TokenizationResponse>
```
**الفرق:** (1) الاسم. (2) عدد الباراميترات — الهوك بيبعت باراميتر واحد
(data فيه unit_id مدمج)، الservice بياخد `unitId` منفصل عن `data`.
لازم إعادة هيكلة الاستدعاء نفسه، مش مجرد rename.

### ب) `buyFractionalShare` (هوك) مقابل `buyFraction` (service)
```ts
// المتوقَّع:
buyFractionalShare(unitId: number, data: {ownership_percentage:number}, idempotencyKey: string)
// النداء الفعلي:
buyFractionalShare(unitId, { ownership_percentage: percentage }, idempotencyKey)

// الموجود فعليًا:
buyFraction: async (
  unitId: number,
  data: BuyFractionalOwnership,
  headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }   // object مش string خام
) => Promise<OwnershipResponse>
```
**الفرق:** (1) الاسم. (2) الباراميتر الثالث — الهوك بيبعت `string` خام،
الservice بيتوقع `object` بمفتاح `'Idempotency-Key'`.

### ج) `getUnitsForSale` (component) مقابل `listUnitsForSale` (service)
```ts
// المتوقَّع:
getUnitsForSale({ limit: 20 }).then(res => res.data)

// الموجود فعليًا:
listUnitsForSale: async (
  params?: { development_id?: number | null; skip?: number; limit?: number }
) => Promise<PropertyUnitResponse[]>   // يرجع array مباشرة، مش { data }
```
**الفرق:** (1) الاسم فقط — الباراميتر متوافق شكليًا تمامًا. (2) مشكلة
unwrap إضافية (خطوة 6): `.then(res => res.data)` هترجع `undefined` حتى
بعد تصحيح الاسم.

### د) `buyFractionalOwnership` (component) مقابل `buyFraction` (service)
```ts
// المتوقَّع:
buyFractionalOwnership(selectedUnitId, { ownership_percentage: percentage }, idempotencyKey)
// onSuccess: (response) => { addOwnership(response.data); ... }

// الموجود فعليًا: نفس buyFraction في الفقرة (ب) أعلاه
```
**الفرق:** نفس فرق (ب) بالظبط (اسم + شكل الباراميتر الثالث) + مشكلة
unwrap إضافية في `onSuccess` (`response.data` بينما `buyFraction` بيرجع
`OwnershipResponse` مباشرة).

**خلاصة القرار المطلوب لكل الحالات المختلطة:** مافيش حل "rename" بسيط
واحد يكفي — أي إصلاح لازم يقرر: (1) نغيّر توقيع الـservice (نضيف
`unitId` منفصل في tokenizeAsset زي ما الهوك متوقّع، أو نلف idempotency
key بـobject) — ده هيأثر على router.py المرتبط بيه، أو (2) نغيّر توقيع
الاستدعاء في كل هوك/مكوّن ليطابق الservice الحالي (الأقل خطورة لأنه
frontend-only ومايلمسش الـbackend المُختبَر). **قرار مطلوب من المستخدم،
صفر تنفيذ حتى الآن.**

---

## اكتشاف جانبي إضافي (خارج نطاق الـ10 ملفات المطلوبة — للأمانة فقط)

نفس مسح tsc الأصلي (خطوة 3) وجد كمان أخطاء في `tokenization/page.tsx`
(`TS2554: Expected 1 arguments, but got 2` + implicit-any) و
`ownerships/page.tsx` (implicit-any + `Cannot find module 'date-fns/ar'`)
— دول **مش من فئة "استيراد دالة غير موجودة"** (فئة الجلسة الحالية)، بل
فئات أخطاء مختلفة تمامًا (arg-count mismatch، implicit-any، missing
npm package). **لم يُحقَّق فيهم بالتفصيل — خارج نطاق هذه الجلسة عمدًا**،
موثَّقين هنا فقط عشان محدش يفترض إن الـ10 ملفات دي هي كل شيء مكسور في
دومين realestate بالفرونت إند.

---

## خطوة 9: الجدول الموحَّد النهائي (10 ملفات) — للموافقة، صفر تنفيذ

| # | الملف | الاستيراد الغلط | التصنيف |
|---|---|---|---|
| 1 | `hooks/realestate/useProperties.ts` | `getProperties`, `getProperty`, `createProperty`, `updateProperty`, `deleteProperty` + types `Property`, `PropertyFormData` | **(ب)** لا مفهوم Property CRUD في الباك إند |
| 2 | `hooks/realestate/useTokenization.ts` | `getAssetTokenization` | **(ب)** لا يوجد GET |
| 2b | نفس الملف | `createTokenization` | **مختلط (أ+توقيع)** — تفاصيل خطوة 8-أ |
| 2c | نفس الملف | `buyFractionalShare` | **مختلط (أ+توقيع)** — تفاصيل خطوة 8-ب |
| 2d | نفس الملف | type `TokenizationFormData` | **(ب)** لا يوجد |
| 3 | `hooks/realestate/useMyOwnerships.ts` | `getMyOwnerships` | **(أ) + مشكلة unwrap** (خطوة 6) |
| 4 | `hooks/realestate/usePropertyOwnerships.ts` | `getPropertyOwnerships` | **(ب)** لا يوجد endpoint حسب property/unit |
| 5 | `app/(dashboard)/realestate/page.tsx` | `getAvailableProperties` | **(ب)** لا يوجد، وحتى أقرب مرشح شكل بياناته مختلف |
| 6 | `app/(dashboard)/realestate/property/[id]/page.tsx` | `useUpdateProperty` | **(ب)** غير موجودة في الهوك نفسه ولا في الباك إند |
| 7 | `components/realestate/InvestorPortfolio.tsx` | `getMyOwnerships` | **(أ) + مشكلة unwrap** |
| 7b | نفس الملف | `getSmartContractStatus` | **(ب)** لا يوجد GET لحالة عقد ذكي |
| 8 | `components/realestate/MasterPlanExplorer.tsx` | `getMyLands` | **(أ) + مشكلة unwrap** |
| 9 | `components/realestate/SmartContractDashboard.tsx` | `deploySmartContract` | **(أ) — أنظف حالة، بدون مشكلة unwrap** |
| 10 | `components/realestate/TokenizationExchange.tsx` | `getUnitsForSale` | **مختلط (أ+توقيع)** — تفاصيل خطوة 8-ج + unwrap |
| 10b | نفس الملف | `buyFractionalOwnership` | **مختلط (أ+توقيع)** — تفاصيل خطوة 8-د + unwrap |

**إحصائية سريعة:** 8 حالات (ب) [لا يوجد إطلاقًا]، 4 حالات (أ) [تصحيح
استيراد فقط، منهم 1 نظيفة تمامًا و3 محتاجة كمان إصلاح unwrap]، 4 حالات
مختلطة (أ+توقيع، كلهم كمان محتاجين قرار unwrap ما عدا 2b/2c).

**قرارات معلَّقة على المستخدم قبل أي تنفيذ:**
1. نطاق حالات (ب) — هل نبني الميزات الناقصة في الباك إند (property CRUD
   عام، update property unit، get tokenization details، get smart
   contract status، ownerships-by-property)، ولا نصلّح الفرونت إند بس
   ليطابق اللي موجود فعلاً (يعني حذف/تعديل الميزات دي في الواجهة)؟
2. حالات "مختلط" — نعدّل توقيع الـservice (يمس router.py) ولا نعدّل
   توقيع الاستدعاء في كل هوك/مكوّن (frontend-only)؟
3. مشكلة unwrap (خطوة 6) — نلف كل ميثودز `RealEstateService` بـ
   `{ data: ... }`، ولا نمسح `.then(res=>res.data)` من كل الاستدعاءات
   الـ8 المتأثرة؟

**صفر تنفيذ حتى الآن.**

---

## خطوة 10: تنفيذ المرحلة الأولى (موافقة صريحة من المستخدم — بدأ التنفيذ)

المستخدم وافق على تنفيذ المرحلة الأولى فقط: كل حالات (أ) البسيطة
(#3, #7, #8, #9) + كل الحالات المختلطة (#2b, #2c, #10, #10b). حالات (ب)
(#1, #1b, #2, #2d, #4, #5, #6, #7b) **تفضل backlog موثّق، صفر تنفيذ لها.**

### التعديلات المُنفَّذة (frontend-only بالكامل):

1. **`hooks/realestate/useMyOwnerships.ts`** (#3) — الاستيراد بقى
   `import { RealEstateService } from '@/services/realestate'`، والاستدعاء
   `RealEstateService.getMyOwnerships()` بدون `.then(res=>res.data)`.

2. **`components/realestate/MasterPlanExplorer.tsx`** (#8) — نفس النمط:
   `RealEstateService.getMyLands({ limit: 20 })` بدون unwrap.

3. **`components/realestate/SmartContractDashboard.tsx`** (#9) — نفس
   النمط: `RealEstateService.deploySmartContract({...})` (كانت أصلاً
   بدون `.then(res=>res.data)`، فمفيش تغيير غير الـnamespace).

4. **`components/realestate/InvestorPortfolio.tsx`** (#7 فقط، #7b باقية
   backlog عمدًا) — الاستيراد بقى
   `import { RealEstateService, getSmartContractStatus } from '@/services/realestate'`
   — `getSmartContractStatus` **متعمَّد إنها تفضل مكسورة** (import غير
   موجود، #7b مؤجَّلة). استدعاء `getMyOwnerships` بقى
   `RealEstateService.getMyOwnerships()` بدون unwrap.

5. **`hooks/realestate/useTokenization.ts`** (#2b, #2c فقط — #2
   `getAssetTokenization` و#2d `TokenizationFormData` باقيين backlog
   عمدًا):
   - `createTokenization` → `RealEstateService.tokenizeAsset(unit_id, rest)`
     — بفصل `unit_id` عن باقي الـdata (destructuring) عشان يطابق توقيع
     الـservice الحقيقي (`tokenizeAsset(unitId, data, headers?)`)، مع
     الحفاظ على شكل نداء المستهلك في `page.tsx`
     (`createTokenization.mutate({ unit_id, ...formData })`) زي ما هو —
     مفيش تعديل على استهلاك الصفحة، الإصلاح كله جوّه الهوك.
   - `buyFractionalShare` → `RealEstateService.buyFraction(unitId, {ownership_percentage}, {'Idempotency-Key': idempotencyKey})`
     — لف الـidempotencyKey (string خام) جوّه object زي ما الـservice
     بيتوقع.

6. **`components/realestate/TokenizationExchange.tsx`** (#10, #10b):
   - `getUnitsForSale` → `RealEstateService.listUnitsForSale({ limit: 20 })`
     بدون unwrap.
   - `buyFractionalOwnership` → `RealEstateService.buyFraction(selectedUnitId, {ownership_percentage: percentage}, {'Idempotency-Key': idempotencyKey})`.

### اكتشاف جديد أثناء التنفيذ (غير موثَّق سابقًا) — type mismatch حقيقي

عند إزالة `.data` من `onSuccess: (response) => { addOwnership(response.data) }`
في `TokenizationExchange.tsx`، ظهرت مشكلة إضافية: `RealEstateService.buyFraction`
بيرجع النوع `OwnershipResponse` (من `components['schemas']['OwnershipResponse']`
المولَّد من الباك إند)، وده **مفيهوش حقل `created_at`** إطلاقًا (تأكيد
من `schemas.py` سطر 65-73: `id, unit_id, owner_user_id,
ownership_percentage, acquisition_date, deed_nft_token_id?,
purchase_tx_hash?` — بدون `created_at`). لكن `addOwnership` في
`store/realestateStore.ts` بيتوقع `PropertyOwnership` (من
`types/realestate.ts`) واللي فيها `created_at: string` **إجباري (مش
اختياري)**. يعني حتى بعد تصحيح كل شيء تاني، فيه type mismatch حقيقي
موجود من الأول (النوعين مش متطابقين بنيويًا) — كان مخفي بسبب فشل
الاستيراد الأصلي (كان بيخلي النوع `any` فبيبلع أي مشكلة type).

**القرار المؤقت المُتّخذ الآن (frontend-only، أقل تدخل):** استخدام type
assertion صريح `response as unknown as PropertyOwnership` بدل تعديل
`store/realestateStore.ts` أو `types/realestate.ts` (خارج نطاق الموافقة
الحالية). **هذا حل مؤقت موثَّق، مش حل جذري** — الجذر الحقيقي (هل
`created_at` لازم يتضاف لـ`OwnershipResponse` في الباك إند، ولا يتشال
كـrequired من `PropertyOwnership` في الفرونت إند) **بند backlog جديد،
يحتاج قرار منفصل، مش جزء من نطاق هذه الجلسة.**

---

## خطوة 11: تحقق حي عبر tsc بعد المرحلة الأولى — ⚠️ توقّف، اكتشافات جديدة تحتاج قرار

شغّلت `npx tsc --noEmit -p tsconfig.json` كاملة تاني بعد كل تعديلات
المرحلة الأولى. **مقارنة قبل/بعد:**

### ✅ مؤكَّد حيًا — الإصلاحات المعتمَدة نجحت بدون أي أثر جانبي:
- `hooks/realestate/useMyOwnerships.ts` (#3) — **صفر أخطاء إطلاقًا** الآن.
- `components/realestate/SmartContractDashboard.tsx` (#9) — **صفر أخطاء
  إطلاقًا**.
- `hooks/realestate/useTokenization.ts` (#2b, #2c) — أخطاء
  `createTokenization`/`buyFractionalShare` اختفت تمامًا، الباقي بس
  الأخطاء المؤجَّلة عمدًا (#2 `getAssetTokenization`, #2d
  `TokenizationFormData`) — **بدون أي أثر جانبي جديد**.
- `components/realestate/InvestorPortfolio.tsx` (#7) — خطأ
  `getMyOwnerships` اختفى، الباقي أخطاء `getSmartContractStatus` (#7b،
  مؤجَّلة عمدًا) + أخطاء متسلسلة منها (status/tx_hash على type `{}`) —
  **متوقَّعة، نفس الجذر المؤجَّل**.
- `components/realestate/TokenizationExchange.tsx` (#10, #10b) — أخطاء
  `getUnitsForSale`/`buyFractionalOwnership` (التسمية) اختفت، خطأ
  `created_at` اللي اكتُشف واتعالج بـ type assertion اختفى برضو.

### ⚠️ اكتشافات جديدة حقيقية — ظهرت فقط لأن الإصلاح المعتمَد كشفها (كانت
### مخفية ورا `any` بسبب فشل الاستيراد الأصلي) — **لم يُلمَس أي منها،
### بانتظار قرار المستخدم:**

**1) `components/realestate/MasterPlanExplorer.tsx` (#8) — 3 أخطاء جديدة:**
```
(50,30): Argument of type '{...LandAssetResponse shape...}' is not assignable to parameter of type 'LandAsset'.
(68,36): Property 'toFixed' does not exist on type 'string'. (land.area_sqm.toFixed(0))
(73,44): Property 'toFixed' does not exist on type 'string'. (land.current_value_mrusdt.toFixed(2))
```
**السبب الجذري (تحقّق حي من `src/lib/api-types.ts`):** حقول Decimal
القادمة من الباك إند (`area_sqm`, `current_value_mrusdt` في
`LandAssetResponse`) **مُصرَّح عنها كـ`string` في الـOpenAPI schema
المولَّدة فعليًا** (سطر 11643/11652 في `api-types.ts`)، مش `number`. يعني
`land.area_sqm.toFixed(0)` هيكسر وقت التشغيل فعليًا (`TypeError:
toFixed is not a function`) — **باج حقيقي كان موجود من الأول في الكود**،
كان مخفي بس لأن فشل استيراد `getMyLands` كان بيخلي `lands` كله `any`
(فـTS ماكانش بيتحقق من `.toFixed()` على `any`). إصلاح الاستيراد (المعتمَد،
#8) كشف الباج، **لكن إصلاح الباج نفسه (تحويل string→number أو تعديل
النوع) مش جزء من الموافقة الحالية.**

**2) `components/realestate/TokenizationExchange.tsx` — خطآن جديدان:**
```
(67,42): Property 'toFixed' does not exist on type 'string'. (unit.sale_price_mrusdt?.toFixed(2))
(96,33): The left-hand side of an arithmetic operation must be of type 'any', 'number', 'bigint' or an enum type. ((unit.sale_price_mrusdt * percentage) / 100)
```
نفس الجذر بالظبط: `PropertyUnitResponse.sale_price_mrusdt` مُصرَّح
`string | null` فعليًا (سطر 14296 في `api-types.ts`). العملية الحسابية
(`*`) هتشتغل وقت التشغيل فعليًا بسبب تحويل JS التلقائي للنوع
(`"10.5" * 5 === 52.5`)، لكن `.toFixed()` هتكسر فعليًا.

**3) `app/(dashboard)/realestate/ownerships/page.tsx` — 3 أخطاء جديدة
(ملف لم يُلمَس، ولم يكن ضمن الـ10 المحقَّق فيهم أصلًا — اكتشاف تسلسلي):**
```
(32,61), (84,30), (87,34): Property 'current_value' does not exist on type '{id, unit_id, owner_user_id, ownership_percentage, acquisition_date, deed_nft_token_id, purchase_tx_hash}'.
```
**السبب:** هذه الصفحة بتستخدم `useMyOwnerships()` (نفس الهوك اللي
اتصلح في #3)، وكانت بتفترض إن النتيجة من نوع `Ownership` (النوع المحلي
في `types/realestate.ts` اللي فيه `current_value` إضافي)، لكن النوع
الحقيقي الراجع من الباك إند (`OwnershipResponse`) **مفيهوش هذا الحقل
إطلاقًا**. إصلاح #3 (المعتمَد، وناجح 100% لنطاقه) كشف إن `ownerships/page.tsx`
نفسها فيها افتراض بيانات غلط من الأول — **ملف حادي عشر مكتشَف الآن لأول
مرة، خارج الـ10 الأصليين تمامًا**، بسبب تأثير تسلسلي (ripple effect) من
إصلاح معتمَد وليس تعديل مباشر عليه.

### القرار المطلوب الآن قبل أي خطوة تانية:
هل نوسّع نطاق المرحلة الأولى المعتمَدة لتشمل إصلاح الـ3 اكتشافات دي
كمان (تحويل Decimal-as-string لـnumber بالـ`Number()`/`parseFloat`، وتصحيح
افتراض `current_value` في `ownerships/page.tsx`)، ولا نوقف عندها ونوثّقها
كـbacklog منفصل (زي حالات (ب))، ونسيب المرحلة الأولى في حالتها الحالية
(الاستيراد + التوقيع + unwrap مصلَّحين 100%، لكن الملفين دول لسه مش
هيعدّوا build نظيف)؟ **صفر تنفيذ إضافي حتى الرد.**

---
