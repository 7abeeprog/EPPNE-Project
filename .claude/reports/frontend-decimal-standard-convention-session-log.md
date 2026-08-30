# جلسة: تأسيس معيار موحَّد للتعامل مع حقول Decimal القادمة من الباك إند

- **الاسم:** frontend-decimal-fields-standard-convention
- **التاريخ:** 2026-08-30
- **الحالة:** 🟡 **مُنفَّذ جزئيًا ومتحقَّق منه بـtsc + snapshot Node — 9 من 16 موضع مؤكَّد.** فجوة تحقق حقيقية معلَّقة: render حي في متصفح فعلي (راجع §4.4). الـ7 الباقية مؤجَّلة عمدًا لبند backlog منفصل (`frontend-services-hooks-missing-exports-multi-domain`، PROGRESS_LOG.md).

## السياق

اكتُشفت المشكلة أثناء جلسة `realestate-hooks-layer-nonexistent-function-imports`
(2026-08-29) — حقول Decimal (مثل `area_sqm`, `current_value_mrusdt`,
`sale_price_mrusdt`) بترجع من الباك إند كـ`string` في الـOpenAPI schema
(قرار Pydantic متعمَّد للحفاظ على الدقة العشرية، مش باج)، لكن الفرونت إند
في بعض المواضع (`MasterPlanExplorer.tsx`, `TokenizationExchange.tsx`) كان
بيعاملها كـ`number` مباشرة (`.toFixed()`, عمليات حسابية) — TypeError وقت
التشغيل + احتمال فقدان دقة.

المبدأ الحاكم (مؤكَّد سابقًا، جلسة تصنيف الأولويات 2026-08-29، وتحقق فعليًا
في فحص buyFraction/tokenizeAsset): **"Never trust client-computed amounts"**
— الفرونت إند يعرض، ما يحسبش. هذه الجلسة تغطي الجزء المتبقي: توحيد *عرض*
حقول Decimal في الفرونت إند بأمان، بدون فقدان دقة حتى في العرض (لا حسابات
جديدة تُرسل للباك إند).

## نطاق هذه الجلسة

1. بحث: المعيار العالمي للتعامل مع Decimal-as-string في TS/React.
2. تحديد نطاق المشكلة: grep شامل في `eppne-web` عبر كل الدومينز.
3. تصميم utility مركزي + قاعدة CODING_STANDARDS.md.
4. خطة تطبيق (دفعة واحدة مقابل utility + حالتين معروفتين + backlog).

**لا تنفيذ في هذه الجلسة قبل عرض التصميم والموافقة الصريحة.**

---

## سجل الخطوات

### 1. محاولة فورك فشلت
أول محاولة لتفويض جرد النطاق الكامل (27 ملف schemas.py × 40 ملف frontend)
لـfork باءت بالفشل — الـfork رجع رد غير منطقي ("سأنتظر نتيجة الفورك الآن")
ولم يكتب أي شيء في هذا الملف رغم تعليمات صريحة، ولم يستخدم إلا 4 tool calls
في 121 ثانية (غير كافٍ إطلاقًا للمهمة). **السبب المرجّح:** الـfork ورث كل
سياق المحادثة، بما فيه تعليمات "اطلق فورك"، فارتبك حول هويته الخاصة.
**الدرس:** لمهام جرد شاملة كهذه، التحقق اليدوي المباشر (بدل تفويض فورك)
أعطى نتائج أدق وأكثر موثوقية — خصوصًا إنه كشف عدة false positives
(تفاصيل تحت) كانت ستُصنَّف كأخطاء لو اعتمدنا فقط على مطابقة أسماء الحقول
بدون التحقق الفعلي من الـschema والـendpoint.

### 2. بحث معياري
Intl.NumberFormat (v3 proposal, ECMA-402) بيقبل **string** مباشرة كمدخل
للعرض بدقة عشرية كاملة (arbitrary-precision) — من غير أي مكتبة خارجية.
لو الطرفية بتستخدم محرك أقدم بيدعم بس Number، الـstring بيتحول تلقائيًا
(نفس السلوك الحالي، صفر مخاطرة رجوع للخلف). decimal.js/big.js مطلوبة بس
لو فيه **حسابات** فعلية بتتنفذ في الفرونت إند — وده غير مطلوب هنا لأن
المبدأ الحاكم "الفرونت إند يعرض، ما يحسبش" (راجع buyFraction/tokenizeAsset
session). خلاصة: **لا حاجة لمكتبة جديدة** — Intl.NumberFormat وحده كافٍ.

### 3. جرد النطاق (يدوي، متحقَّق منه سطر بسطر ضد الـschema الفعلي)

**دروس مهمة من التحقق الفعلي (كشفت 3 أنماط false-positive خطيرة):**
- بعض الـresponse schemas بتُعرِّف نفس اسم الحقل بنوع مختلف عن حقل الطلب
  (مثال: `BuyFractionalOwnership.ownership_percentage: Decimal` لكن
  `OwnershipResponse.ownership_percentage: float` — نفس الاسم، endpoint
  مختلف تمامًا).
- endpoints الإحصائيات/الملخصات (`stats`, `summary`) غالبًا بتحوّل
  Decimal → `float()` صراحة في الـservice/router قبل الإرجاع (affiliate,
  ai_governance, saas, commerce) — **لكن مش دايمًا** (logistics stats
  فضلت Decimal — تضارب داخلي في الباك إند نفسه، يستاهل ملاحظة منفصلة
  لفريق الباك إند، خارج نطاق هذه الجلسة).
- بعض الـendpoints بترجع `dict` خام (مش Pydantic response_model) وبتحوّل
  لـ`float()` يدويًا (`sovereign_entities/router.py:275`
  `get_entity_balance` → `{"balance_mrusdt": float(balance)}`) — بينما
  نفس الحقل (`treasury_balance_mrusdt`) في schema تاني بيفضل Decimal.

#### مواضع مؤكَّدة (Decimal-as-string حقيقي، خطورة عالية — TypeError عند التشغيل)

| الملف:السطر | الحقل | الدومين | ملاحظة |
|---|---|---|---|
| `app/(dashboard)/realestate/property/[id]/page.tsx:302` | `sale_price_mrusdt` | realestate | `?.toFixed()` مباشر على Decimal |
| `app/(dashboard)/realestate/property/[id]/page.tsx:308` | `rent_per_month_mrusdt` | realestate | نفس النمط |
| `app/(dashboard)/payroll/page.tsx:93,97,107` | `base_salary`, `overtime_pay`, `net_salary` | employment | `.toFixed()` مباشر، مؤكَّد Decimal في schema |
| `components/projects/ProjectDetails.tsx:138,142,145` | `current_funding_mrusdt`, `funding_goal_mrusdt` | projects | مؤكَّد Decimal |
| `components/projects/ProjectCard.tsx:97` | `currentFunding`/`fundingGoal` (props مشتقة من نفس الحقول) | projects | يحتاج تتبع props لكن نفس المصدر |
| `components/projects/ProjectAnalytics.tsx:30,42` | `total_funding_mrusdt`, `remaining_to_goal` | projects | مؤكَّد Decimal |
| `components/projects/ProjectAnalysisDashboard.tsx:82,100,106` | `total_funding_mrusdt`, `remaining_to_goal`, `total_in_kind_value` | projects | مؤكَّد Decimal |
| `components/projects/MilestoneTimeline.tsx:88` | `funds_to_release` | projects | مؤكَّد Decimal |
| `components/projects/AdvancedMilestones.tsx:118,168` | `funds_to_release` | projects | مؤكَّد Decimal |
| `components/invitations/CampaignPerformanceChart.tsx:43` | `spent_mrusdt`, `budget_mrusdt` | invitations | مؤكَّد Decimal، `.toFixed()` مباشر |
| `components/ai-governance/QuotaManager.tsx:104,107` | `limit_value`, `current_usage` | ai_governance | مؤكَّد Decimal |
| `app/(dashboard)/logistics/page.tsx:35` | `total_value_mrusdt` (من `LogisticsStatsResponse`) | logistics | استثناء: stats endpoint هنا فضل Decimal (عكس باقي الدومينز) |
| `components/realestate/MasterPlanExplorer.tsx:68,73` | `area_sqm`, `current_value_mrusdt` | realestate | (معروف من الجلسة السابقة) |
| `components/realestate/TokenizationExchange.tsx:67` | `sale_price_mrusdt` | realestate | (معروف من الجلسة السابقة) |
| `components/realestate/PropertyUnitCard.tsx:61,66` | `sale_price_mrusdt`, `rent_per_month_mrusdt` | realestate | نفس نمط property/[id] |
| `components/sovereign-entities/EntityCard.tsx:81` | `treasury_balance_mrusdt` | sovereign_entities | من قائمة الكيانات (schema Decimal)، **مختلف** عن endpoint الرصيد المنفرد (float) |

#### مواضع مؤكَّدة كـ"مقبولة/مش باج" (تحقَّق منها وتم استبعادها)

| الملف:السطر | السبب |
|---|---|
| `realestate/ownerships/page.tsx:58` (`ownership_percentage`) | `OwnershipResponse.ownership_percentage` معرَّف كـ`float` في schema، مش Decimal |
| `realestate/property/[id]/page.tsx:390,398,455` (`totalOwned`, `remainingPercentage`) | مبنية على `ownership_percentage` (float) — حسابياً سليمة |
| `sovereign-entities/WalletBalance.tsx:44` (`balance`) | endpoint `/balance` بيرجع `float(balance)` صراحة (dict خام، مش schema) |
| `command/page.tsx`, `manufacturing/page.tsx` (`total_revenue`, `total_material_cost`) | stats endpoints بتحوّل لـ`float()` صراحة في الـservice |
| `affiliate/page.tsx` (`total_earned`, `pending_earned`, `conversion_rate`) | نفس النمط — `AffiliateStatsResponse` كل الحقول دي `float` |
| `invitations/page.tsx` (`conversion_rate`) | `float` في schema |
| `ai-governance/UsageDashboard.tsx` (`total_cost_mrusdt`) | `float` صراحة في schema + service |
| `marketplace/PurchaseModal.tsx:147` (`addon.price_mrusdt`) | عرض مباشر للـstring في template literal (`${addon.price_mrusdt}`) — مفيش `.toFixed()` عليها، آمن فعليًا (بالصدفة) |
| GPS إحداثيات (`transport/hubs`, `health/emergency*`, `manufacturing/facilities`, `employment/AttendanceWidget`) | `lat`/`lng` مش حقول Decimal في أي schema — إحداثيات float عادية، خارج النطاق |

#### مواضع "غير مؤكَّدة" (مرشَّحة، تحتاج تحقق سطر بسطر وقت التنفيذ — لم تُفحص بعمق هذه الجلسة)

`zamakana/campaigns/[id]/page.tsx` (`progress`), `iot/CarbonCreditPanel.tsx`
(`totalCredits`, `totalValue` — مشتقة من `carbon_credits_generated`/
`consumed_value` وهي Decimal مؤكَّدة في iot schemas)، `marketplace/PurchaseModal.tsx`
(`totalPrice` — حساب محلي بيجمع `Number(addon.price_mrusdt)`؛ لازم تأكيد
إن القيمة دي عرض فقط ومش بتتبعت للباك إند)، `finance/SwapForm.tsx`
(`exchangeRate`, `estimatedAmountOut` — يحتاج فحص منفصل، دومين finance
حساس)، `command/BrandCard.tsx`, `transport/RouteOptimizer.tsx`
(`carbon_saved`), `manufacturing/MaintenanceRadar.tsx` (`probability` —
على الأرجح احتمالية AI محسوبة، مش Decimal مالي).

**ملخص:** 16 موضع مؤكَّد (7 دومينز: realestate, employment, projects,
invitations, ai_governance, logistics, sovereign_entities) + 9 مواضع تم
استبعادها بالتحقق الفعلي + ~7 مواضع لسه محتاجة تحقق. النطاق فعلاً عابر
للدومينز كما كان متوقَّع، لكن أضيق مما يبدو من مجرد grep أسماء الحقول —
لازم التحقق ضد الـschema الفعلي دايمًا قبل التصنيف كباج.

### 4. التصميم المقترح (لسه صفر تنفيذ — بانتظار الموافقة)

**القرار:** لا مكتبة جديدة (لا decimal.js ولا big.js) — العرض بس، والمبدأ
الحاكم أصلًا بيمنع أي حساب فرونت إند يتحول لمبلغ مُرسَل. الحل: دالة واحدة
مركزية فوق `Intl.NumberFormat` الأصلية في المتصفح.

```ts
// eppne-web/lib/format.ts

/**
 * لعرض حقل Decimal راجع من الباك إند كـstring (أو null/undefined).
 * بيستخدم Intl.NumberFormat اللي بيقبل string مباشرة فيحافظ على الدقة
 * الكاملة بدون تحويل وسيط لـJS number.
 */
export function formatDecimalString(
  value: string | null | undefined,
  options: Intl.NumberFormatOptions = { minimumFractionDigits: 2, maximumFractionDigits: 2 }
): string {
  if (value === null || value === undefined || value === '') return '—';
  if (!/^-?\d+(\.\d+)?$/.test(value)) return '—'; // حماية من قيم غير رقمية غير متوقعة
  return new Intl.NumberFormat('en-US', options).format(value as unknown as number);
  //                                                      ^ TS types NumberFormat.format كـ(number|bigint)
  //                                                        لكن runtime فعليًا بيقبل string (ECMA-402 v3).
  //                                                        الـcast هنا موثّق ومقصود، مش هروب من type error عشوائي.
}
```

**قبل/بعد:**
```ts
// قبل (باج — TypeError وقت التشغيل لأن sale_price_mrusdt string)
{property.sale_price_mrusdt?.toFixed(2) || 'غير محدد'} MR_USDT

// بعد
{formatDecimalString(property.sale_price_mrusdt)} MR_USDT
```

**قاعدة CODING_STANDARDS.md المقترحة (تُضاف تحت قسم Frontend):**
> أي حقل من نوع `Decimal`/`condecimal` في schema الباك إند (بيوصل كـ`string`
> في الـJSON) **ممنوع** يتعامل معه الفرونت إند كـ`number` مباشرة
> (`.toFixed()`, عمليات حسابية، `Number()`/`parseFloat()` بدون داعي).
> للعرض: استخدم `formatDecimalString()` من `lib/format.ts` حصرًا.
> استثناء: endpoints الإحصائيات/الملخصات (`*StatsResponse`,
> `*SummaryResponse`) لو الباك إند بيحوّلها لـ`float` صراحة — راجع
> الـschema الفعلي قبل الافتراض.

### 4.1 تحقق حي فعلي (بطلب المستخدم — قبل اعتماد التصميم)

نُفِّذ سكريبت Node مباشر على بيئة المشروع الفعلية (Node **v24.14.1** —
نفس ما رجعه `node --version` في هذا المشروع، `eppne-web/package.json`
بيحدد `@types/node: ^20` لكن التشغيل الفعلي على الجهاز v24). الملف:
`scratchpad/decimal-format-probe.mjs` (خارج الريبو، للفحص فقط).

**النتيجة: الدعم حقيقي وموثوق فعليًا في هذه البيئة — مش افتراض نظري.**

| الحالة | `format(STRING)` | `format(Number(str))` | الفرق |
|---|---|---|---|
| `"123456789012345.6789"` @ 2dp | `123,456,789,012,345.68` (صحيح رياضيًا) | `...67` (خطأ — فقدان دقة float64) | ✅ فرق حقيقي |
| `"9007199254740993.5"` @ 2dp (تخطّى `MAX_SAFE_INTEGER`) | `9,007,199,254,740,993.50` (دقيق) | `9,007,199,254,740,994.00` (خطأ) | ✅ فرق حقيقي وواضح |
| `"10.124999999999999999"` @ 2dp (٥ فراغ التقريب) | `10.12` (صحيح — القيمة الحقيقية أقل من 10.125) | `10.13` (خطأ — التحويل لـfloat64 قرّبها لأعلى قبل التنسيق) | ✅ فرق حقيقي، تحديدًا يوضح خطر التقريب المزدوج |
| `"2.675"` @ 2dp | `2.68` | `2.68` | لا فرق هنا (محرك Intl نفسه بيتفادى فخ float الكلاسيكي حتى لمسار Number) |
| `"10.123456789"` @ 2dp | `10.12` (تقريب لأسفل صحيح) | `10.12` | مطابق |

**خلاصة نقطة (2) — سلوك التقريب:** التقريب فعليًا "نصف لأعلى" (round-half-up)
صحيح رياضيًا في كل الحالات المُختبرة، ومسار الـstring **أدق** فقط في
الحالات اللي فيها أرقام بعد الفاصلة تتجاوز دقة float64 (~15-17 رقم
معنوي) — وهو بالظبط سيناريو المبالغ المالية عالية الدقة (`condecimal`
بعدد كبير من الخانات العشرية).

**حالات حافة (edge cases):**
- `format("")` → `"0.00"` (مش خطأ، لكن **غير مناسب دلاليًا** لعرض "غير محدد" —
  الـutility المقترح بيتحقق من `value === ''` **قبل** الوصول لـ`Intl.NumberFormat`
  ويرجّع `'—'` بدل ما يسيب المحرك يرجّع "0.00" مضلِّلة).
- `format("abc")` → `"NaN"` (بدون throw) — نفس السبب، الـregex validation
  في `formatDecimalString` بيمنع وصول قيمة زي دي للمحرك أصلًا.
- `format(null)` → `"0.00"`, `format(undefined)` → `"NaN"` — نفس المعالجة،
  الدالة المقترحة بترجع `'—'` صراحة قبل استدعاء `Intl.NumberFormat`.
- `format("1e21")` (Scientific notation) اتقبلت وتنسّقت صح — لكن الـregex
  الحالي في التصميم (`^-?\d+(\.\d+)?$`) **بيرفضها** (يرجع `'—'`). ما
  شفناش أي حقل Decimal من الباك إند بيرجّع بصيغة scientific notation
  (Pydantic `Decimal.__str__` ما بيعملش كده عادةً)، فده فشل آمن (safe
  fail) مش باج — لكن يستاهل ملاحظة موثّقة هنا.

**القرار النهائي بعد التحقق الحي:** التصميم في القسم 4 **مؤكَّد بالتجربة
الفعلية**، لا حاجة لبديل (زي تنسيق نصي يدوي بدون float). Node v24 في هذه
البيئة بيدعم الـfeature بالكامل ومطابق لما وثّقه TC39/MDN.

### 4.2 اكتشاف حرج قبل أي تعديل: أغلب الـ16 موضع داخل ملفات مكسورة أصلًا (باج منفصل تمامًا)

بعد موافقة المستخدم على خطة "صحّح types/*.ts أولًا ثم شغّل tsc"، وقبل أي
تعديل فعلي، اتفحصت ثلاثة طبقات أنواع منفصلة في الفرونت إند:
1. `eppne-web/src/lib/api-types.ts` — مولَّد فعليًا (openapi-typescript)،
   **صحيح**: بيوصف حقول Decimal كـ`string` بدقة.
2. `eppne-web/types/*.ts` — يدوي، **خاطئ**: كل حقل Decimal اتفحص فيه
   معرَّف `number`.
3. `services/*.ts` — بعضها بيستورد النوع الصحيح من `api-types.ts` مباشرة
   (`ProjectResponse = components['schemas']['ProjectResponse']` في
   `services/projects.ts`، ونفس النمط في `services/employment.ts`)،
   وبعضها التاني بيستخدم أنواع `types/*.ts` اليدوية الخاطئة.

**تشغيل `npx tsc --noEmit -p tsconfig.json` (baseline حي، 1811 سطر خطأ،
متسق مع الرقم الموثَّق سابقًا ~1253-1268) كشف إن 7 من الـ16 موضع المؤكَّد
واقعين داخل ملفات عندها أخطاء استيراد سابقة **غير متعلقة بالـDecimal
إطلاقًا** — بتخلي المتغير كله `any` ضمنيًا، فمفيش أي فرصة يمسك التحويل
الخاطئ (لأن `any` بيبلع أي استخدام):**

| الملف | الاستيراد المكسور |
|---|---|
| `realestate/property/[id]/page.tsx` | `useUpdateProperty` غير موجود في `useProperties` hook + `date-fns/ar` + `uuid` module مفقودين |
| `payroll/page.tsx` | `getMyPayrolls`, `generatePayroll`, `approvePayroll`, `payPayroll` **مش موجودين إطلاقًا** في `services/employment.ts` + `uuid` مفقود |
| `components/projects/ProjectAnalysisDashboard.tsx` | `getProjectAnalytics` غير موجودة في `services/projects.ts` |
| `components/projects/MilestoneTimeline.tsx` | `getProject` غير موجودة في `services/projects.ts` + `date-fns/ar` مفقود |
| `components/projects/AdvancedMilestones.tsx` | `getProject`, `completeMilestone`, `releaseMilestoneFunds` غير موجودين في `services/projects.ts` + `date-fns/ar` مفقود |
| `components/ai-governance/QuotaManager.tsx` | موديول `@/services/ai-governance` **غير موجود إطلاقًا** |
| `app/(dashboard)/logistics/page.tsx` | موديول `@/hooks/logistics/useStats` **غير موجود إطلاقًا** |

**هذا نفس نمط الباج المعروف من الجلسة السابقة
(`realestate-hooks-layer-nonexistent-function-imports`) — لكن اتضح إنه
أوسع بكتير مما كان معروف: منتشر في 4 دومينز على الأقل (employment,
projects, ai_governance, logistics)، مش realestate بس.** ده باج منفصل
تمامًا، أكبر بكتير من نطاق هذه الجلسة (Decimal convention)، ولازم جلسة
تحقيق واعتماد منفصلة له — **لم يُلمس أي كود له في هذه الجلسة.**

**الـ9 مواضع اللي سليمة السلسلة (chain) دلوقتي وهتفيد فعلاً من تصحيح
types/*.ts** (0 أخطاء استيراد حاليًا، وأكَّدت غيابها بالـgrep على
baseline كامل):
`MasterPlanExplorer.tsx` (خطأ موجود بالفعل)، `TokenizationExchange.tsx`
(خطأ موجود بالفعل)، `CarbonCreditPanel.tsx` (**خطأ موجود بالفعل** — كان
مصنَّف "غير مؤكَّد" في القسم 3، دلوقتي **مؤكَّد حيًا عبر tsc نفسه**)،
`PropertyUnitCard.tsx`, `EntityCard.tsx`, `CampaignPerformanceChart.tsx`,
`ProjectDetails.tsx`, `ProjectAnalytics.tsx` (النوعين الأخيرين
presentational components بتاخد الـprop مباشرة من `types/projects.ts`،
مفيش استدعاء service بتاعهم)، و`ProjectCard.tsx` (فرضًا مختلف — بيستخدم
`ProjectResponse` من `api-types.ts` **الصحيح أصلًا** (`string`)، والمطوّر
حط `Number(project.funding_goal_mrusdt ?? 0)` كـworkaround يدوي بالفعل —
محتاج إزالة الـworkaround واستخدام `formatDecimalString` بدل تصحيح نوع).

**القرار المطلوب:** تنفيذ الخطة (تصحيح types + formatDecimalString +
تحقق حي) على الـ9 مواضع دي بس الآن، وتوثيق الـ7 المحجوبة كبند backlog
منفصل وعاجل (باج استيراد واسع النطاق، أولوية أعلى من مشكلة الـDecimal
نفسها لأنه بيكسر الصفحة كليًا مش بس عرض رقم).

### 4.3 التنفيذ الفعلي على الـ9 (+1) مواضع السليمة

**الملفات المعدَّلة:**
- **جديد:** `eppne-web/lib/format.ts` — `formatDecimalString()`.
- **تصحيح نوع (types/*.ts):** `types/realestate.ts` (`PropertyUnit.area_sqm/sale_price_mrusdt/rent_per_month_mrusdt`، و**إضافيًا** `LandAsset.area_sqm/current_value_mrusdt` — نفس الاسمين ضمن نفس الملف، اكتُشف لزومهما أثناء التحقق التالي)، `types/sovereign-entities.ts` (`SovereignEntity.treasury_balance_mrusdt`)، `types/invitations.ts` (`MarketingCampaign.budget_mrusdt/spent_mrusdt`)، `types/projects.ts` (`Project.funding_goal_mrusdt/current_funding_mrusdt`، `ProjectAnalytics.total_in_kind_value/total_funding_mrusdt/remaining_to_goal`).
- **تصحيح مكوّنات:** `MasterPlanExplorer.tsx`, `TokenizationExchange.tsx`, `CarbonCreditPanel.tsx`, `PropertyUnitCard.tsx`, `EntityCard.tsx`, `CampaignPerformanceChart.tsx`, `ProjectDetails.tsx`, `ProjectAnalytics.tsx`, `ProjectCard.tsx`.

**اكتشاف إضافي أثناء أول تشغيل tsc بعد تصحيح النوع:** `MasterPlanExplorer.tsx`
كان عنده خطأ **موجود مسبقًا وغير متعلق بالـtoFixed** — تمرير `land` (الشكل
الحقيقي، `area_sqm: string`) لـ`onSelectLand?: (land: LandAsset) => void`
كان بيفشل لأن `LandAsset.area_sqm` كانت `number`. صحّحنا `LandAsset` كمان
(كانت غايبة عن خطة الإصلاح الأصلية سهوًا رغم إنها من ضمن الحقلين
الأصليين في الـ16) — أغلقت الخطأ القديم كأثر جانبي مفيد، صفر خطأ جديد.

**اكتشاف منفصل غير مُلمَس (خارج النطاق، pre-existing):**
`CarbonCreditPanel.tsx` عنده خطآن تسمية/توقيع لا علاقة لهما بالـDecimal
(`IoTService.settleCarbon()` بتتوقَّع معامل واحد لكن بتتنادى بصفر
معاملات، ورد `onSuccess` بيتعامل معه كـ`{total_credits_settled,
monetary_value_added_mrusdt}` رغم إن التوقيع `void`) — **موجودان قبل هذه
الجلسة**، نفس فئة `iot-translation-service-method-mismatches` الموثَّقة
في PROGRESS_LOG.md. لم يُلمَسا. كذلك `TokenizationExchange.tsx` عندها
موديول `uuid` مفقود من `node_modules` (pre-existing، غير مرتبط).

**اكتشاف حقيقي إضافي أثناء الإصلاح (باج صامت جديد، ليس مجرد type error):**
`CarbonCreditPanel.tsx` سطر 15 (الأصلي) — `unsettled.reduce((acc, r) => acc
+ r.carbon_credits_generated, 0)` بدون `Number()`: بما إن
`carbon_credits_generated` string وبما إن `acc` يبدأ رقم (`0`)، أول عملية
`0 + "12.5"` بترجع **concatenation** ("012.5") مش جمع — أي تينانت عنده
أكتر من قراءة كربون غير مسوّاة كان هيشوف **"NaN طن"** بدل الرقم الحقيقي،
صامت بالكامل (لا استثناء، لا رسالة خطأ). أُصلح بـ`Number()` صريح على كل
عنصر قبل الجمع. **تحقق حي (Node مباشر، أسفل) أثبت الفرق بالضبط.**

### 4.4 التحقق النهائي (tsc + snapshot Node) — بديل عن render حي في متصفح

**تسلسل tsc (كل الأرقام قِيست فعليًا، مش تقديرية):**
1. Baseline قبل أي تعديل: **1811 سطر خطأ**.
2. بعد تصحيح types/*.ts فقط (بدون لمس المكوّنات): **1826 سطر** (+15 خطأ
   toFixed/arithmetic جديد، بالظبط عند الأماكن المتوقَّعة — تأكيد حي إن
   تصحيح النوع فعّال، prêt لـtsc يمسك أي استخدام خاطئ مستقبلي تلقائيًا).
3. بعد تصحيح المكوّنات التسعة: **1798 سطر** (كل الـ15 + الأخطاء
   القديمة الأصلية في MasterPlanExplorer/TokenizationExchange/
   CarbonCreditPanel اختفت بالكامل).
4. بعد تصحيح `LandAsset` الإضافي: **1795 سطر نهائي**. تأكيد بالـgrep:
   **صفر خطأ متعلق بالـDecimal/toFixed متبقٍ في أي من الـ9 ملفات.**
   المتبقي فقط: 3 أسطر `CarbonCreditPanel` (باج settleCarbon منفصل
   موثَّق فوق) + سطر `uuid` مفقود (موديول npm منفصل).

**Node snapshot مباشر (`scratchpad/decimal-fix-snapshot.mjs`) — تنفيذ
حي فعلي، مش مجرد قراءة كود:**

| الحالة | الناتج |
|---|---|
| `"123456789.987654321"` | `"123,456,789.99"` |
| `null` | `"—"` |
| `undefined` | `"—"` |
| `""` (فارغة) | `"—"` |
| `"500000"` (بدون كسور) | `"500,000.00"` |
| `"10.129999999999999999"` @ 2dp افتراضي | `"10.13"` |
| نفس القيمة @ 6dp | `"10.13"` |
| `"-42.5"` (سالب) | `"-42.50"` |
| `"abc"` (غير رقمية) | `"—"` (safe-fail) |

كل الـ9 مواضع اتحاكت بنفس التعبير البرمجي الفعلي المُطبَّق في الكود
(مش مجرد استدعاء `formatDecimalString` منعزل) — كلها نجحت بلا استثناء.
**حالة `CarbonCreditPanel` اتحقّق منها بالمقارنة المباشرة:** محاكاة
"قبل الإصلاح" (نفس بيانات: `["12.5","7.25","3.125"]`) رمت
`TypeError: totalCredits.toFixed is not a function` **فعليًا** (تأكيد
حي للباج القديم، مش افتراض)، بينما "بعد الإصلاح" أرجعت `22.8750 طن`
(مطابق تمامًا لـ`12.5+7.25+3.125=22.875` حسابيًا).

**⚠️ فجوة تحقق حقيقية معلَّقة — لم يُغلَق بالكامل:** الـsnapshot ده
تحقّق من **منطق التنسيق/الحساب** (نفس التعبيرات البرمجية، بيانات
واقعية) وليس من الـrender الفعلي في DOM حقيقي عبر متصفح — مطلوب أصلًا
من المستخدم (`render فعلي أو snapshot`)، اتقبل الـsnapshot كبديل مؤقت
بموافقة صريحة **لسبب تقني**: امتداد Chrome غير متصل بهذه الجلسة
(`tabs_context_mcp` رجع "Browser extension is not connected")، وأوامر
PowerShell الشبكية (`Invoke-WebRequest`, `Get-NetTCPConnection`) بتعلّق
بلا استجابة في هذا الـsandbox رغم إن سيرفر Next.js dev اتشغّل فعليًا
(بورت 3000، تأكيد من الـlog: `Local: http://localhost:3000`). **لسه
معلَّق:** لا تفاعل مستخدم حقيقي، لا فحص console errors في متصفح حقيقي،
لا تأكيد بصري إن الـCSS/layout ما اتأثرش. **ده لا يُعتبر "خلص" —
فجوة حقيقية.**

**اقتراح لإغلاق الفجوة لاحقًا (بترتيب الأولوية):**
1. **الأبسط:** إعادة تشغيل نفس التحقق (فتح الصفحات التسعة فعليًا) في
   جلسة قادمة بعد ما اتصال Chrome يرجع — سيرفر الـdev لسه شغّال في
   الخلفية من هذه الجلسة (`localhost:3000`، PID غير مؤكَّد — أوامر
   PowerShell لفحص/إيقاف العملية علّقت هي كمان، فمن المحتمل يحتاج إيقاف
   يدوي لو لسه شغّال).
2. **الأكثر ديمومة (يحتاج قرار/تكلفة إعداد):** المشروع **حاليًا بدون أي
   framework اختبار frontend مثبَّت** (`package.json` فيه صفر إشارة
   لـ`jest`/`vitest`/`@testing-library/react`) — إضافة
   `@testing-library/react` + `vitest` (أو `jest`) تسمح برندر حقيقي
   لهذه المكوّنات (DOM حقيقي عبر `jsdom`) بدون الحاجة لمتصفح فعلي أو
   سيرفر dev — لكنها قرار بنية تحتية جديدة للمشروع (تبعية جديدة +
   إعداد أولي)، يستاهل موافقة صريحة منفصلة، مش جزء تلقائي من إصلاح
   Decimal هذا.

### 5. الحالة النهائية للجلسة

**القرار المُنفَّذ فعليًا (بموافقة صريحة، بعد اكتشاف §4.2):** تطبيق
`formatDecimalString` على الـ9 مواضع السليمة السلسلة فقط (راجع §4.3/§4.4)،
+ توثيق الـ7 المحجوبة ببند `frontend-services-hooks-missing-exports-multi-domain`
في `PROGRESS_LOG.md` (صفر لمس كود له).

**غير مُنفَّذ عمدًا في هذه الجلسة (backlog صريح موثَّق):**
- الـ7 مواضع المحجوبة بباج الاستيراد المنفصل (§4.2).
- حقول Decimal تانية موثَّقة أثناء الجرد بس برّه نطاق الـ9/الـ16 (مثال:
  `total_monetary_contributions` في `types/projects.ts` — علّمتها
  بتعليق `TODO backlog` صريح في الكود نفسه؛ `ProjectFormData`/`QuotaFormData`/
  إلخ من أنواع الطلبات (request) — اتركت عمدًا `number` لأن Pydantic
  Decimal بيقبل رقم JSON عادي في الطلبات، الفرق يهم بس في الاستجابات).
- المواضع "غير مؤكَّدة" الأصلية من §3 اللي مش من ضمن الـ9 (`zamakana progress`،
  `marketplace/PurchaseModal totalPrice`، `finance/SwapForm`، إلخ) — لسه
  بلا تحقق.
- **render حي في متصفح حقيقي** — فجوة معلَّقة، راجع §4.4 للتفاصيل والاقتراح.

**✅ قاعدة CODING_STANDARDS.md مُضافة فعليًا** (`CODING_STANDARDS.md` §2،
مثال قبل/بعد + استثناءي Request-types وstats endpoints).

**✅ فجوة render الحي موثَّقة كبند backlog مستقل صريح** في `PROGRESS_LOG.md`
(`frontend-decimal-fix-live-browser-render-unverified`) — لن تُنسى، جلسة
قصيرة منفصلة كافية لإغلاقها لاحقًا.

**الجلسة جاهزة للـcommit.**


