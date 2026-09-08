# date-fns/ar locale import fix — session log

جلسة: date-fns-ar-locale-import-fix
تاريخ البدء: 2026-08-31
مصدر الاكتشاف: جلسة frontend-mechanical-fix-all-domains-pass1 (نفس اليوم)

## الخطوة 1: تأكيد نسخة date-fns الفعلية

`eppne-web/package.json`:
```
"date-fns": "^4.4.0",
```

v4 → الـlocale الصحيح هو `date-fns/locale/ar` أو `date-fns/locale` (named export `ar`).
`date-fns/ar` (بدون `/locale/`) **غير موجود إطلاقًا** في v4 — هذا استيراد خاطئ سيفشل وقت التشغيل/البناء.

`formatDistanceToNow` هي دالة أساسية من `date-fns` نفسها (ليست جزء من ملف locale) — توقيعها:
`formatDistanceToNow(date: Date | number, options?: { addSuffix?, includeSeconds?, locale?, ... })`

## الخطوة 2: grep شامل — مكتمل

`grep -r "date-fns/ar"` على `eppne-web/` → **45 ملف كود فعلي** (+ ملف نصي
قديم `link-fix-verification.txt` غير ذي صلة، مُتجاهَل). لا وجود لأي دالة
غير `format` أو `formatDistanceToNow` مستوردة من `date-fns/ar` — لا
`formatRelative`, لا `parseISO`, ولا استيراد مزدوج (كل استيراد سطر واحد
لدالة واحدة فقط).

**تقسيم فعلي مكتشف — 3 فئات، ليس فئتين كما افتُرض في وصف المهمة:**

### فئة 1 — `formatDistanceToNow` (13 ملف) — باج سلوكي حقيقي مؤكَّد
كل الاستدعاءات بنفس النمط: `formatDistanceToNow(new Date(x), { addSuffix: true })`.
تحقّق Node مباشر (`require('date-fns')` + `require('date-fns/locale').ar`):
```
بدون locale: "about 3 hours ago"       ← الوضع الحالي الفعلي لو كان الاستيراد يشتغل أصلاً
مع locale ar: "منذ 3 ساعات تقريباً"     ← الناتج الصحيح المطلوب
```
هذا هو الباج الحقيقي الذي وصفه طلب المهمة — بدون `locale: ar` الناتج
إنجليزي، مش عربي.

### فئة 2 — `format` بأنماط رقمية بحتة (29 ملف) — الاستيراد معطوب، لكن الناتج لا يتغير بالـ locale
كل الاستدعاءات المكتشفة تستخدم format strings رقمية فقط:
`'dd/MM/yyyy'`, `'dd/MM/yyyy HH:mm'`, `'HH:mm'`, `'HH:mm:ss'`, `'dd/MM'`
— لا توجد أي رموز اسمية (`MMMM`, `EEEE`, `a`) تعتمد على locale.
تحقّق Node مباشر:
```
format(date, 'dd/MM/yyyy', { locale: ar })  → "31/08/2026"
format(date, 'dd/MM/yyyy')                  → "31/08/2026"   (نفس الناتج تمامًا)
```
يعني: الباج هنا هو فقط أن `date-fns/ar` مسار غير موجود (سيفشل الـ build/
runtime import) — تصحيح الاستيراد وحده يكفي وظيفيًا. مع ذلك، سأضيف
`{ locale: ar }` كخيار ثالث لكل استدعاء `format()` أيضًا حسب تعليمات
المهمة (تمرير locale صراحة) — كإجراء تحوّطي لأي تنسيق مستقبلي يُضاف بحرف
اسمي، بدون أي تأثير على الناتج الحالي.

### فئة 3 — استيراد ميت غير مستخدم إطلاقًا (3 ملفات) — استثناء حقيقي عن النمط المتوقَّع
هذه الملفات تستورد `format` من `date-fns/ar` لكن **لا تستدعيه في أي مكان
بالملف** (تحقَّق بـ grep شامل على كامل محتوى كل ملف):
- `components/insurance/PolicyCard.tsx` (سطر 5)
- `components/tourism-sports/TicketCard.tsx` (سطر 5)
- `app/(dashboard)/transport/deliveries/page.tsx` (سطر 9)

الإصلاح هنا مختلف عن الفئتين الأخريين: **حذف سطر الاستيراد بالكامل**، لا
إضافة `date-fns/locale` ولا استدعاء دالة غير مستخدمة.

## الخطوة 3: الإصلاحات — مكتملة (بعد موافقة المستخدم)

`grep -r "date-fns/ar"` بعد التعديل على `eppne-web/` (glob `*.tsx`) → **0 نتيجة**. كل الـ45 ملف تم تصحيحهم.

### فئة 1 — formatDistanceToNow (13 ملف) — import كامل + locale على كل استدعاء
1. components/health/AIPrognosisRadar.tsx (1 استدعاء)
2. app/(dashboard)/digital-twin/legacy/page.tsx (2 استدعاء)
3. components/projects/AdvancedMilestones.tsx (1)
4. components/manufacturing/MaintenanceRadar.tsx (1)
5. components/communications/NotificationList.tsx (1)
6. app/(dashboard)/automation/secrets/page.tsx (1)
7. app/(dashboard)/automation/workflows/[id]/executions/page.tsx (1)
8. app/(dashboard)/automation/workflows/[id]/executions/[executionId]/page.tsx (2)
9. components/social/PostCard.tsx (1)
10. components/command/AlertList.tsx (1)
11. components/ai-governance/AuditLogViewer.tsx (1)
12. components/projects/ProjectUpdates.tsx (1)
13. components/projects/MilestoneTimeline.tsx (1)

نمط التصحيح:
```ts
// قبل
import { formatDistanceToNow } from 'date-fns/ar';
formatDistanceToNow(new Date(x), { addSuffix: true })

// بعد
import { formatDistanceToNow } from 'date-fns';
import { ar } from 'date-fns/locale';
formatDistanceToNow(new Date(x), { addSuffix: true, locale: ar })
```

### فئة 2 — format() بأنماط رقمية بحتة (29 ملف) — import + locale احترازي
1. components/command/BrandCard.tsx (1)
2. components/logistics/EquipmentCard.tsx (1)
3. components/logistics/InventoryCard.tsx (1)
4. components/invitations/LeadCard.tsx (1)
5. app/(dashboard)/zamakana/campaigns/[id]/page.tsx (2)
6. components/zamakana/CampaignCard.tsx (2)
7. app/(dashboard)/arbitration-syndicates/licenses/page.tsx (2)
8. components/arbitration-syndicates/ElectionCard.tsx (4)
9. components/arbitration-syndicates/CaseCard.tsx (1)
10. components/insurance/PensionCard.tsx (2)
11. components/insurance/ClaimCard.tsx (1)
12. components/insurance/SubscriptionCard.tsx (2)
13. components/tenders-auctions/AuctionDetail.tsx (2)
14. components/tenders-auctions/TenderDetail.tsx (2)
15. components/tenders-auctions/LiveBidCard.tsx (1)
16. app/(dashboard)/tenders-auctions/auctions/[id]/page.tsx (2)
17. app/(dashboard)/tenders-auctions/tenders/[id]/page.tsx (2)
18. components/tenders-auctions/AuctionCard.tsx (2)
19. components/tenders-auctions/TenderCard.tsx (2)
20. components/social/EventCard.tsx (2)
21. components/social/OccasionCard.tsx (1)
22. app/(dashboard)/social/occasions/page.tsx (1)
23. components/tourism-sports/EventCard.tsx (1)
24. components/tourism-sports/ProgramCard.tsx (2)
25. app/(dashboard)/transport/bookings/page.tsx (1)
26. app/(dashboard)/transport/trips/page.tsx (3)
27. app/(dashboard)/transport/page.tsx (1)
28. app/(dashboard)/realestate/ownerships/page.tsx (1)
29. app/(dashboard)/realestate/property/[id]/page.tsx (1)

نمط التصحيح:
```ts
// قبل
import { format } from 'date-fns/ar';
format(new Date(x), 'dd/MM/yyyy')

// بعد
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';
format(new Date(x), 'dd/MM/yyyy', { locale: ar })
```
**ملاحظة مهمة:** تأكَّد Node أن `{ locale: ar }` هنا **لا يغيّر أي ناتج حالي**
(كل أنماط التنسيق المستخدمة رقمية بحتة). الإضافة احترازية بحتة تماشيًا مع
تعليمات المهمة، وليست إصلاح باج سلوكي كما في فئة 1.

### فئة 3 — استيراد ميت محذوف (3 ملفات) — استثناء عن النمط المتوقَّع
1. components/insurance/PolicyCard.tsx — حذف سطر `import { format } from 'date-fns/ar';` بالكامل (غير مستخدم إطلاقًا)
2. components/tourism-sports/TicketCard.tsx — نفس الإجراء
3. app/(dashboard)/transport/deliveries/page.tsx — نفس الإجراء

## الخطوة 4: التحقق

### اختبار Node مباشر (نفس منهجية جلسة Decimal/Intl.NumberFormat)
```
formatDistanceToNow(45min ago, { addSuffix: true, locale: ar })
→ "منذ ساعة واحدة تقريباً"   ✅ عربي صحيح، مش fallback إنجليزي

format('2026-08-31T14:22:09', 'dd/MM/yyyy HH:mm:ss', { locale: ar })
→ "31/08/2026 14:22:09"      ✅ رقمي، متطابق مع/بدون locale كما هو متوقَّع
```

### tsc --noEmit
`grep "date-fns/ar"` بعد التعديل = 0 نتيجة في كل `eppne-web/` (مؤكَّد أعلاه).
`npx tsc --noEmit -p tsconfig.json` اكتمل: **1023 خطأ إجمالي، صفر منهم
يذكر "date-fns"** (`grep -ic "date-fns" tsc_out.txt` = 0). كل أخطاء
date-fns/ar اختفت. باقي الـ1023 خطأ drift معروف وغير مرتبط بهذه الجلسة
(موثّق في جلسات سابقة كباقي أخطاء ما بعد baseline).

## الملخص النهائي
- **45/45 ملف** تم تصحيحهم فعليًا (13 فئة 1 + 29 فئة 2 + 3 فئة 3).
- **الاستثناء المكتشف** غير المتوقَّع في وصف المهمة الأصلي: 3 ملفات باستيراد
  ميت غير مستخدم إطلاقًا — تطلّب حذف بدل تصحيح.
- **اكتشاف إضافي غير متوقَّع:** فئة 2 (29 من 45 ملف، أغلبية الملفات) لم
  يكن الباج فيها سلوكيًا فعليًا (الناتج يتطابق مع/بدون locale) — الباج
  الحقيقي فيها كان فقط مسار استيراد معطوب (سيفشل الـ build). الوصف
  الأصلي للمهمة افترض أن كل الـ~30 ملف كانت بنفس باج `formatDistanceToNow`
  السلوكي، لكن الفحص الفعلي بالـ Node أظهر إن هذا صحيح فقط لـ13 ملف من
  أصل 45.

