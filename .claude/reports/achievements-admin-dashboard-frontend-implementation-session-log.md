# جلسة تنفيذ: صفحة /admin/achievements (Next.js، eppne-web)

**التاريخ:** 2026-09-15
**النطاق:** بناء لوحة تحكم الإنجازات الكاملة في الفرونت إند، بنفس نمط
`saas/plans` (Layout, حماية SUPER_ADMIN, تنسيق Tables).
مرجع التخطيط: `.claude/reports/achievements-admin-dashboard-planning-session-log.md`.
مرجع الـbackend: `.claude/reports/achievements-stats-endpoints-implementation-session-log.md`.

---

## 1. حاجتان مفقودتان اكتُشفتا أثناء البناء (خارج نطاق الفرونت إند الأصلي — تمت معالجتهما بموافقة المستخدم)

قبل الشروع في الفرونت إند، ظهر بلوكرين حقيقيين خلال التخطيط الفعلي
للجدول والفورم — تم عرضهما على المستخدم واتخاذ قرار صريح لكل واحد:

1. **عمود "عدد المستخدمين اللي حققوه" في جدول التعريفات:** لا يوجد أي
   endpoint يرجّع عدد مجمَّع حسب `achievement_definition_id`. **القرار:**
   إضافة `GET /achievements/stats/by-definition` (تفاصيلها في تقرير
   الـbackend §6).
2. **"بحث بالاسم/الإيميل" في فورم المنح:** لا يوجد أي endpoint بحث/قائمة
   مستخدمين شغّال في الباك إند إطلاقًا — الفرونت إند القديم
   (`entity-representatives.tsx`) بينادي `/users/search` غير الموجود
   (بج قديم منفصل، **لم يُصلَح**، خارج النطاق). **القرار:** إضافة
   `GET /identity/users/search?q=&limit=` (تفاصيلها في تقرير الـbackend §7).

كلا الإضافتين خفيفتان وإضافيتان بحتًا (صفر لمس لأي كود موجود)، اختُبرتا
حيًا بالكامل مع Regression نظيف — راجع التقرير المذكور.

---

## 2. النمط المتبَع — `saas/plans` كمرجع حرفي

| الطبقة | الملف المرجعي | الملف الجديد |
|---|---|---|
| الصفحة | `app/(dashboard)/saas/plans/page.tsx` | `app/(dashboard)/admin/achievements/page.tsx` |
| Modal الإنشاء | `components/saas/CreatePlanModal.tsx` | `components/achievements/CreateDefinitionModal.tsx` |
| الهوكس | `hooks/saas/usePlans.ts` | `hooks/achievements/useAchievements.ts` |
| الخدمة | `services/saas.service.ts` | `services/achievements.service.ts` |
| حماية الدور | `app/(dashboard)/finance/admin/page.tsx` | نفس اللوحة، لكن بدور مختلف (انظر §3) |

**استدعاء الـAPI:** `apiClient` (axios) نفسه المستخدم في كل مكان —
**صفر مكتبات جديدة**، `withCredentials: true` دايمًا (كوكيز HttpOnly).
**الأنواع:** أُضيفت يدويًا لقسم `components['schemas']` في
`src/lib/api-types.ts` (نفس القرار المتعمَّد الموثَّق في جلسة
`transport-vehicles-drivers`: إعادة توليد الملف بالكامل عبر
`openapi-typescript` كانت هتعيد كتابة آلاف الأسطر وتُظهر انحرافات
تراكمية غير مرتبطة عبر 34+ دومين — الإضافة اقتصرت على الـ10 أنواع
المُستهلَكة فعليًا: `AchievementCategory`, `AchievementTriggerType`,
`AchievementDefinitionCreate/Response`, `AchievementGrantRequest`,
`UserAchievementResponse`, `AchievementCategoryStatItem`,
`AchievementTopUserItem`, `AchievementDefinitionStatItem`,
`UserSearchResult`).

---

## 3. حماية اللوحة — تصحيح عن نمط `finance/admin` القديم

`finance/admin/page.tsx` (النمط الشائع في المشروع) بيفحص
`SUPER_ADMIN || ADMIN`. **هذا مش صحيح لهذه اللوحة تحديدًا** — راجع
تقرير التخطيط: `achievements/definitions` (POST)، `/grant`، وكل
endpoints الإحصائيات محمية backend بـ`get_current_superuser` اللي
بيقبل فقط `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` (**مش** `ADMIN`). فحص
الصفحة هنا:

```ts
const isSuperuser = user?.system_role === "SUPER_ADMIN" || user?.system_role === "EXECUTIVE_DIRECTOR";
```

+ نفس نمط `useEffect` + `router.push("/dashboard")` + `toast.error` من
`finance/admin/page.tsx`، لكن بالقيمة الصحيحة (مطابقة لمرجع
`sidebar.tsx:356` الموجود بالفعل لعنصر "العمليات السيادية").

---

## 4. الملفات الجديدة

| الملف | المحتوى |
|---|---|
| `src/lib/api-types.ts` | 10 أنواع جديدة (إضافة يدوية، انظر §2) |
| `services/achievements.service.ts` | `AchievementsService` — 7 دوال (`listDefinitions`, `createDefinition`, `grantAchievement`, `getUserAchievements`, `getStatsByCategory`, `getTopUsers`, `getStatsByDefinition`, `searchUsers`) |
| `hooks/achievements/useAchievements.ts` | `useAchievementDefinitions`, `useCreateAchievementDefinition`, `useGrantAchievement`, `useAchievementStatsByCategory`, `useAchievementTopUsers`, `useAchievementStatsByDefinition`, `useUserSearch` |
| `components/achievements/CreateDefinitionModal.tsx` | فورم تعريف جديد (name, description, category, points_value, icon_url اختياري) — `trigger_type` مثبَّت `MANUAL` دايمًا، بلا حقل في الفورم |
| `app/(dashboard)/admin/achievements/page.tsx` | الصفحة الكاملة (3 أقسام) |

**صفر تعديل** على أي ملف موجود في `eppne-web` (باستثناء `src/lib/api-types.ts`
بإضافات فقط).

---

## 5. الأقسام الثلاثة (مطابقة للمواصفة بالحرف)

1. **الإحصائيات أعلى الصفحة:** 3 بطاقات (عدد الإنجازات لكل فئة من
   الفئات الثلاث، حتى لو صفر — القيم الافتراضية `?? 0` تغطي حالة فئة
   غايبة تمامًا من رد `by-category` لأنها INNER JOIN) + جدول "أكتر 10
   مستخدمين إنجازًا" (`useAchievementTopUsers(10)`).
2. **قائمة التعريفات:** جدول (اسم، فئة كـ`Badge`، نوع التريجر
   كـ`Badge` ملوَّن حسب `MANUAL`/`AUTO_EVENT`، عدد المستخدمين من
   `by-definition` مطابَق بـ`Map<id, count>`) + زر "تعريف جديد" يفتح
   `CreateDefinitionModal`. `trigger_event_name`/`trigger_threshold`
   **غير معروضين إطلاقًا في هذه المرحلة** (لا في الجدول ولا في
   الفورم) — الفورم بيُنشئ MANUAL بس، بالظبط زي المطلوب.
3. **فورم المنح اليدوي:** بحث نصي (`useUserSearch`، `enabled` بس لو
   الاستعلام ≥ حرفين) بيعرض نتائج `GET /identity/users/search` كقائمة
   قابلة للاختيار (اسم + إيميل)، + `Select` لاختيار تعريف الإنجاز من
   `useAchievementDefinitions`، + زر "امنح" (`useGrantAchievement`) —
   بعد النجاح: `invalidateQueries(['achievements','stats'])` (يغطي
   الثلاث endpoints الإحصائية بـpartial match) فيحدّث كل الجداول فورًا
   بلا reload.

---

## 6. الاختبار الحي — المحاولة الأولى (HTTP فقط، جلسة سابقة نفس اليوم)

**أداة claude-in-chrome غير متصلة في هذه البيئة (تأكَّد مرتين، في
جلستين منفصلتين).** بدلًا منها، تحقق حي عبر HTTP الفعلي ضد سيرفرين
حقيقيين شُغِّلا محليًا (uvicorn على 8000 + `next dev` على 3000):

1. تسجيل مستخدم throwaway حقيقي (`livetest_superadmin`) عبر
   `POST /api/identity/register`، ترقيته لـ`SUPER_ADMIN` مباشرة في DB.
2. تسجيل دخول حقيقي (`POST /api/identity/login`) — كوكيز HttpOnly
   فعلية.
3. `GET http://127.0.0.1:3000/admin/achievements` بالكوكيز → **200**
   (فحص صفر أخطاء 500 في الـpayload الخام — بلا تنفيذ JS فعلي).
4. تأكيد كل الـendpoints الأربعة عبر HTTP فعلي (مش `ASGITransport` كما
   في pytest) — كلها أرجعت بيانات صحيحة.
5. `POST /achievements/definitions` + `POST /achievements/grant` ثم
   إعادة استعلام الثلاث endpoints الإحصائية فورًا — الأرقام اتحدَّثت
   بشكل صحيح.
6. تنظيف كامل + تأكيد DB رجعت لحالتها.

**القصور الحقيقي في هذه المحاولة (اتضح لاحقًا في §6ب):** كل ده تحقق من
طبقة الـHTTP/API فقط — **بلا أي تنفيذ JavaScript فعلي**. `curl`/HTTP
مباشر ميعرفش يكتشف لو React نفسها بتعلق قبل ما توصل لعرض الصفحة —
وده بالظبط اللي اكتشفناه بعد كده.

---

## 6ب. الاختبار الحي في متصفح حقيقي (هذه الجلسة — Playwright headless Chromium)

claude-in-chrome لسه غير متصلة (اتأكَّد تالت مرة في بداية هذه الجلسة).
بدل تكرار نفس قصور المحاولة الأولى، تم تثبيت **Playwright مؤقتًا في
مجلد scratchpad معزول تمامًا** (`npm init` + `npm install playwright`
في مجلد مستقل تحت `%TEMP%`، **صفر لمس لـ`package.json` أو
`node_modules` الخاصين بـ`eppne-web`** — أول محاولة `npm install
--no-save playwright` جوّه `eppne-web` نفسها اتلغت فورًا لما ظهر
تعارض peer dependency موجود أصلًا في المشروع بين `wagmi`/`@rainbow-me/rainbowkit`،
تفاديًا لأي مخاطرة على شجرة اعتماديات المشروع الحقيقية) — يديني متصفح
Chromium حقيقي (headless) بدل الاعتماد على HTTP خام.

### الإعداد
- تشغيل uvicorn (8000) + `next dev` (3000) فعليًا محليًا.
- إنشاء مستخدمين throwaway حقيقيين عبر السكريبت مباشرة (نفس نمط
  pytest): `browsertest_superadmin` (تُرقّي لـ`SUPER_ADMIN` في DB
  مباشرة) و`browsertest_grantee` (للبحث عنه في فورم المنح).

### خطوة 1 — فتح `/login` في المتصفح الحقيقي

**النتيجة: الصفحة عالقة إلى ما لا نهاية على شاشة تحميل عامة** —
"جاري تهيئة المنصة السيادية..." (سبينر بيدور فعليًا، يعني JS شغّال،
لكن المحتوى الحقيقي مايظهرش أبدًا). اتأكَّد بعد 15 ثانية، 40 ثانية،
وحتى بعد تحميل كل الـJS bundles بنجاح (200 لكل الـchunks — Next.js
Turbopack، wagmi، RainbowKit، axios، إلخ) — نفس الشاشة العالقة بلا أي
تغيير.

### خطوة 2 — إثبات إن ده مش خاص بصفحة achievements أو بأي كود من هذه الجلسة

نفس الاختبار بالحرف على `/login` (صفحة موجودة قبل أي شغل اليوم، صفر
علاقة بـ`achievements`/`identity` اللي عدّلته الجلسة) أظهر **نفس
السلوك بالظبط**. `/login` بتتحمّل عبر `AuthProvider` (`providers/AuthProvider.tsx`)
اللي بيغلّف **كل** صفحة في التطبيق من `app/providers.tsx` — يعني
المشكلة أوسع من achievements بمراحل، وموجودة أصلًا **قبل** أي تعديل
من اليوم (اتأكَّد بـ`git status` إن لا `providers.tsx` ولا
`web3-provider.tsx` ولا `AuthProvider.tsx` ولا `app/layout.tsx` اتلمسوا
في أي جلسة اليوم إطلاقًا).

### خطوة 3 — تشخيص السبب (بلا أي تعديل كود، تشخيص بحت)

- **صفر أخطاء console حقيقية** (غير تحذيرات WebSocket لـwebpack-hmr
  متكررة — `net::ERR_INVALID_HTTP_RESPONSE` — غير مرتبطة، بيئة Playwright/dev
  server).
- **صفر استدعاء لـ`GET /identity/me` إطلاقًا** خلال 40 ثانية كاملة
  (راقبت شبكة الصفحة بالكامل) — يعني `useMe()` (اللي بوابة التحميل في
  `AuthProvider` بتعتمد على `isFetched` بتاعتها) **مبتتنفّذش أصلًا**،
  مش إنها بتاخد وقت طويل.
- **فحص مباشر (`page.evaluate`) لتأكيد الشبكة سليمة**: نداء `fetch()`
  خام من جوّه نفس صفحة المتصفح لـ`http://localhost:8000/api/identity/me`
  رجع **فورًا** `401 {"detail":"Not authenticated"}` — يعني **الشبكة
  والـbackend سليمين 100%**، والمشكلة داخل كود React نفسه (مش CORS،
  مش سيرفر واقع، مش timeout شبكة).
- **الاحتمال الأقوى المكتشف بقراءة الكود:** `app/providers.tsx` بيلف
  التطبيق بـ`<QueryClientProvider client={queryClient}>` (الرئيسي)، **لكن**
  `app/web3-provider.tsx` (المُستخدَم جوّه نفس الشجرة، ملفوف حوالين
  `AuthProvider` وكل الصفحات) بينشئ **`QueryClientProvider` تاني منفصل
  بالكامل** (`const queryClient = new QueryClient(); ... <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>`)
  **جوّه** الأول. أي `useQuery`/`useMutation` في أي مكون تحت
  `Web3Provider` (يعني كل التطبيق فعليًا، بما فيها `AuthProvider`
  ولوحة achievements الجديدة) بيقرأ الـcontext الأقرب — يعني
  `QueryClientProvider` الداخلي بتاع `web3-provider.tsx`، مش المُعدّ
  في `providers.tsx`. **ده لسه فرضية قوية مبنية على قراءة كود دقيقة،
  مش تأكيد نهائي 100%** (محتاج تتبّع فعلي جوّه React DevTools Profiler
  لتأكيدها بيقين كامل) — لكنها أقوى دليل ملموس ظهر لحد دلوقتي على سبب
  حقيقي واضح لباج موثَّق مسبقًا بس بلا سبب جذري معروف.

### القرار بخصوص الإصلاح

هذا الباج **موثَّق مسبقًا في ملف المشروع الدائم** (قبل أي جلسة
achievements اليوم) كـ"باج `lit`/`@reown/appkit-ui` قديم، يمنع اختبار
تدفقات auth/identity يدويًا في المتصفح، منفصل تمامًا، محتاج مهمة
مخصَّصة". اكتشاف هذه الجلسة (نظرية الـQueryClientProvider المزدوج)
**سبب تقني محتمل جديد** لنفس الباج المعروف — لكن `web3-provider.tsx`
ملف مشترك تستخدمه **كل صفحة في المنصة بالكامل**، وأي تعديل فيه — حتى
لو سطر واحد ظاهريًا — نطاق تأثيره يمتد لكل شيء، مش نطاق ضيق حقيقي.

**عُرِض الأمر على المستخدم صراحة أثناء الجلسة، وقرَّر:** توثيق الاكتشاف
فقط بلا أي تعديل على `web3-provider.tsx` الآن — يبقى ملف مفتوح بتاريخ
لاحق، خارج نطاق جلسة achievements.

### الخلاصة الصادقة النهائية

- ✅ **طبقة الـAPI بالكامل تعمل بشكل صحيح ومتحقَّق منها حيًا مرتين**
  (عبر pytest وعبر HTTP خام مباشر في المحاولة الأولى §6).
- ✅ **الكود الجديد (frontend files) نفسه سليم بنيويًا** — `tsc`
  نظيف تمامًا، الاستدعاءات لـAPI صحيحة المسار/البارامترات (مؤكَّد يدويًا
  ضد نفس الـendpoints اللي اشتغلت في §6).
- ❌ **لم يتم تأكيد بصري/تفاعلي داخل متصفح فعلي لصفحة `/admin/achievements`
  نفسها إطلاقًا** — لا الجداول، لا فورم المنح، لا أي تفاعل — لأن
  التطبيق **بالكامل** (كل صفحة، مش بس achievements) عالق على شاشة
  تحميل عامة بسبب باج مستقل موثَّق مسبقًا في `web3-provider.tsx`،
  اتأكَّد وجوده وأُثبت إنه سابق لأي عمل في هذه الجلسة وغير ناتج عنها.
  **هذا قصور حقيقي في التحقق، مش نجاح جزئي — يجب عدم اعتبار اللوحة
  "مُختبَرة حيًا في متصفح" حتى يُصلَح هذا الباج ويُعاد الاختبار.**

---

## 7. Regression

### Backend
راجع `.claude/reports/achievements-stats-endpoints-implementation-session-log.md`
§6-§7: `15 failed, 203 passed, 2 xfailed, 264 warnings` — مطابقة تامة
للأساس، صفر regression جديد (4 اختبارات حية جديدة عبر إضافتي
by-definition وusers/search).

### Frontend — `tsc --noEmit -p tsconfig.json`
| | إجمالي أخطاء المشروع |
|---|---|
| قبل بناء اللوحة (لقطة فعلية وقت الجلسة، مش الأساس القديم 1253) | 737 |
| بعد (بعد تصحيح typing واحد — انظر تحت) | **733** (-4) |

**كل ملف جديد لمسته الجلسة — صفر أخطاء `tsc` فيه** (`page.tsx`,
`CreateDefinitionModal.tsx`, `achievements.service.ts`,
`useAchievements.ts`, `api-types.ts`). الانخفاض الصافي (-4) سببه: أول
نسخة من `page.tsx` نسخت `containerVariants`/`itemVariants` حرفيًا من
`saas/plans/page.tsx` (نفس مشكلة typing موجودة أصلًا في الملف المرجعي
نفسه — `Variants` غير مُعلَنة صراحة، فـ`framer-motion` بيوسّع
`type: "spring"` لـ`string` عام مش literal) — 4 تكرارات هنا (مقابل 2 في
saas/plans) بسبب استخدام `itemVariants` في 4 أقسام. **تم تفاديها هنا**
بإضافة `import type { Variants } from "framer-motion"` وتعليم الثابتين
بالنوع صراحة — تحسين بسيط عن النمط المرجعي، صفر تكلفة إضافية.

---

## 8. المرحلة الجاية (لو حابب المستخدم)

**0) أولوية أعلى من أي حاجة تانية — إصلاح باج `web3-provider.tsx`
(القيد الحقيقي أمام إثبات أي تفاعل UI في أي صفحة بالمنصة، مش
achievements بس):** راجع §6ب فوق للتشخيص الكامل والفرضية التقنية
(`QueryClientProvider` مزدوج). بدون إصلاح هذا الباج، مفيش أي صفحة في
الداشبورد ممكن تتأكد بصريًا في متصفح فعلي (dev mode) — بما فيها كل
لوحات الأدمن الموجودة أصلًا (`saas/plans`, `finance/admin`, إلخ)، مش
بس اللوحة الجديدة دي.

**1)** دعم `trigger_type = AUTO_EVENT` في نفس فورم "تعريف جديد" — يسمح
للأدمن بإنشاء عتبات تلقائية جديدة (فئة + اسم حدث + عتبة) من اللوحة
مباشرة، بدل ما يكون التفعيل التلقائي مقصورًا على الأحداث الثلاثة
المُهيَّأة بالفعل من الكود (`academy.bootcamp_enrollment.created`,
`academy.course.completed`, `project.contribution.received`). يحتاج:
حقل `trigger_event_name` (قائمة منسدلة بالأحداث المسجَّلة فعليًا في
`CRITICAL_EVENT_HANDLERS`، مش نص حر) + `trigger_threshold` (رقمي،
اختياري حسب الفئة) في `CreateDefinitionModal`، بلا أي تعديل backend
إضافي (schema/endpoint الحاليين بيدعموا الحقلين بالفعل).

---

## 9. لم يُلمَس إطلاقًا

- `entity-representatives.tsx` (البج القديم `/users/search` — موثَّق
  كملاحظة بس، مش مُصلَح، خارج النطاق).
- أي صفحة/دومين فرونت إند تاني غير `achievements`.
- أي جزء من `src/lib/api-types.ts` غير قسم `Achievement*`/`UserSearchResult`
  المُضاف.
