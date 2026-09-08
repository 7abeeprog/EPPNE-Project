# جلسة: frontend-category-b-classification-all-domains

**التاريخ:** 2026-09-01
**الهدف:** تصنيف وتنظيم فقط — صفر تنفيذ كود. لكل حالة "فئة (ب)" المتبقية من
جلسة [[frontend-mechanical-fix-all-domains-pass1]] (استيراد/دالة غير موجودة
إطلاقًا في أي `service.ts`، مش مجرد نمط استيراد غلط)، نحدد: هل يقابلها
endpoint في الباك إند غير مربوط بالفرونت إند (تصنيف أ: وصلة رخيصة)، أم
الميزة غير موجودة في أي طبقة (تصنيف ب: قرار بناء/تقليم حقيقي)؟ صفر قرار
"نبني ولا نقلّم" في هذه الجلسة — ده خطوة تالية.

## تحديث الأرقام قبل البدء

تشغيل `tsc --noEmit` حي الآن أعطى **223** خطأ TS2305/TS2307 فعلي (مش 290
زي ما كان مقدّر في بداية الجلسة — العدد اتغيّر بسبب شغل لاحق غير مُلتزَم
بعد (uncommitted) ظاهر في `git status`، منه على الأرجح جلسة
`realestate-hooks-layer-design-decision` وربما npm installs). الأرقام
الفعلية حسب الدومين (تنازليًا):

| الدومين | عدد الأخطاء الحالي | التقدير الأصلي بالبرومبت |
|---|---|---|
| social | 35 | ~34 |
| transport | 33 | ~26 |
| tourism-sports | 17 | ~16 |
| tenders-auctions | 17 | ~17 |
| agritech | 17 | ~11 |
| realestate | 12 | ~9 |
| insurance | 12 | ~12 |
| invitations | 10 | (غير مذكور صراحة) |
| manufacturing | 9 | (غير مذكور صراحة) |
| arbitration-syndicates | 7 | ~7 |
| zamakana | 6 | (غير مذكور) |
| projects | 6 | ~7 |
| logistics | 6 | (غير مذكور) |
| automation | 6 | (غير مذكور) |
| command | 4 | (غير مذكور) |
| ai-governance | 4 | (غير مذكور) |
| employment | 3 | (غير مذكور) |
| marketplace/iot/health/academy | 2 لكل | (غير مذكور) |
| باقي متفرقات (wallet/saas/finance/digital-twin/communications/commerce/public/store) | ~11 مجتمعة | (غير مذكور) |

**ملاحظة منهجية مهمة (فلترة قبل التصنيف):** مش كل خطأ TS2305/TS2307 متبقٍ
هو "فئة ب" بمعنى المهمة. استبعدنا من التصنيف التفصيلي (لأنها مش مرتبطة
بـ`service.ts`/باك إند إطلاقًا، وموثّقة أصلاً كاستثناءات منفصلة في تقرير
pass1):
- ملفات UI عرضية مفقودة بالكامل (مكوّنات زي `FarmCard`, `CampaignCard`,
  `TicketCard`, `TransferCard`, `ReadingsChart` إلخ) — مفيش داعي لفحص باك
  إند، القرار هنا "نكتب المكوّن" مش "نبني API".
- استيرادات infra عامة مش خاصة بدومين (`@/lib/auth-utils`,
  `@/hooks/use-debounce`, `@/components/ui/tooltip`).
- قضايا حزم npm (`uuid`, `qrcode.react`, `date-fns/ar`) — قرار تبعية/منطق
  مختلف كليًا، موثّق في pass1.

كل حالة فيها الملف المستهلك بيحاول يستدعي دالة/hook بيُتوقع منها تجيب/تعدّل
بيانات فعلية (مش مجرد UI) اتفحصت مقابل الباك إند (`router.py`,
`service.py`, **و`repository.py`** — سابقة realestate أثبتت إن أحيانًا
الطبقة الأعمق فيها الدالة جاهزة وغير مكشوفة).

## حالة التنفيذ

✅ اكتمل التحقيق — 5 agents متوازيين غطّوا كل الدومينات، كل واحد كتب تقرير
تفصيلي (جدول حالة-بحالة + فحص حي لـ`router.py`/`service.py`/`repository.py`
+`openapi.json`) في `.claude/reports/category-b/`. التفاصيل الكاملة لكل حالة
(اسم الدالة، الملف المستهلك، أين وُجدت في الباك إند إن وُجدت) موجودة في ملفات
المجموعات — هذا الملف ملخص مجمّع فقط.

| المجموعة | الدومينات | ملف التقرير |
|---|---|---|
| 1 | social, transport | `category-b/group1-social-transport.md` |
| 2 | tourism-sports, tenders-auctions, agritech | `category-b/group2-tourism-tenders-agritech.md` |
| 3 | realestate, insurance, invitations | `category-b/group3-realestate-insurance-invitations.md` |
| 4 | manufacturing, arbitration-syndicates, zamakana, projects, logistics, automation | `category-b/group4-manufacturing-arbitration-zamakana-projects-logistics-automation.md` |
| 5 | health, iot, marketplace, employment, ai-governance/ai-agents, command, digital-twin, saas, finance/wallet, academy, commerce, communications, projects(سطر الصفحة العامة) | `category-b/group5-misc-small-domains.md` |

**ملاحظة منهجية:** الأعداد تحت "أ/ب" هي عدد **الحالات المنطقية** بعد دمج
الأسماء المتكررة (نفس الاسم المفقود يظهر أحيانًا في أكثر من سطر `tsc` لأنه
مُستدعى من أكثر من ملف) — مش عدد أسطر `tsc` الخام. `transport` فيه استثناء
إضافي غير مصنّف: 12 سطر `tsc` خام سببها ملف `hooks/transport/useVehicles.ts`
اللي محتواه غلط بالكامل (نسخة من كود trips) — موثّق من جلسة سابقة، صفر لمس،
مش محسوب ضمن أ/ب هنا (تفاصيله في تقرير المجموعة 1).

## جدول الملخص الكامل حسب الدومين

| الدومين | (أ) وصلة فقط | (ب) غير موجود | تقدير حجم بناء (ب) |
|---|---|---|---|
| social | 11 | 24 | معظمها CRUD/service+router بسيط فوق جداول جاهزة (Events, Pages)؛ `followPage`/`unfollowPage` يحتاجان جدول جديد (`PageFollower`)؛ البعض يحتاج تصميم query/list جديد |
| transport | 9 | 16 | متنوع: بعضه migration بسيطة (fleets/hubs update/delete)، `useDrivers` = **مفهوم كامل غير موجود إطلاقًا** (لا role، لا جدول، صفر تمثيل) |
| tourism-sports | 4 | 11 (يشمل `TransferCard`) | بعض الحالات (`getMatches`,`getMyTickets`,`getTransfers`) استدعاء repository معطوب أصلاً حتى داخليًا — يحتاج إصلاح منطق مش مجرد وصلة |
| tenders-auctions | 10 | 1 | `getMyBids` فقط — بسيط نسبيًا |
| agritech | 7 | 8 (يشمل 3 مكوّنات UI + `useStats`) | **⚠️ الدومين بالكامل غير قابل للوصول عبر HTTP حاليًا** — لا يوجد `router.py` ومش مسجّل في `main.py` (فقط في `main.py.bak` غير المستخدم)؛ هذا مستقل عن تصنيف كل حالة على حدة ويجب معالجته أولًا |
| realestate | 12 | 0 | **صفر** — كل الـ8 حالات الأصلية اتنفذت فعليًا في جلسة `realestate-hooks-layer-design-decision` (migration 043 + 10 اختبارات حية)؛ الـ4 الجديدة أسماء/أنواع بديلة فوق نفس العمل المكتمل |
| insurance | 10 | 2 | `getInsuranceStats` (تجميع جديد كليًا) و`deletePolicy` (لا حذف بأي طبقة رغم عمود `is_deleted` جاهز) |
| invitations | 5 | 5 | كل الـ5 (ب) مكوّنات React مفقودة بالكامل — البيانات اللي هتعرضها **جاهزة 100%** في الباك إند |
| manufacturing | 4 | 4 | migration بسيطة — كل الجداول/الأعمدة المطلوبة موجودة، ناقص فقط دوال CRUD/تجميع عبر الطبقات |
| arbitration-syndicates | 7 | 0 | صفر — كله وصلة/إعادة تسمية |
| zamakana | 6 | 0 | صفر — كله وصلة/إعادة تسمية، حتى `usePledges`+`PledgeForm`+`PledgeCard` فوق باك إند جاهز بالكامل |
| projects | 2 | 2 | `releaseMilestoneFunds` (migration بسيطة — الحقل موجود، ناقص endpoint+ربط بـ`FinanceService.transfer`)، `getEntityProjects` (migration بسيطة — نفس نمط ربط الكيان أدناه) |
| logistics | 6 | 0 | صفر — كله جاهز، `useStats` هوك مفقود فقط رغم دعم باك إند كامل |
| automation | 6 | 0 | صفر — أقرب حاجة مطلوبة توثيق قيم enum (`SLACK`,`DATABASE`,`HTTP_RESPONSE`) وليست فجوة وظيفية |
| health | 2 | 0 | صفر |
| iot | 1 | 1 | migration بسيطة — جدول `MaintenanceLog` موجود، ناقص طبقات repository/service/router فقط |
| marketplace | 2 | 0 | صفر |
| employment | 3 | 0 | صفر |
| ai-governance/ai-agents | 4 | 0 | صفر — الباك إند **مكتمل تمامًا**؛ الفجوة فرونت إند بحتة: `services/ai-governance.ts` غير موجود كملف إطلاقًا (يغلّف 6 endpoints جاهزة) |
| command | 2 | 2 | `dismissAlert` (سطر واحد على enum + endpoint بسيط)، `getDashboardMetrics` (migration بسيطة/schema بسيط للتجميع حسب period) |
| digital-twin | 2 | 0 | صفر لهذين السطرين تحديدًا (ملاحظة أوسع: كل `digital-twin.service.ts` معطّل الأنواع عمدًا بـ18+ `any`، خارج نطاق هذا التصنيف) |
| saas | 1 | 0 | صفر |
| finance/wallet | 1 | 1 | **تصميم schema جديد** — `web3-deposit-withdraw` يحتاج مفهوم كامل جديد (عناوين محافظ خارجية، تتبع معاملات on-chain) |
| academy (سطر الصفحة العامة) | 0 | 1 | migration بسيطة — عمود ربط `sovereign_entity_id` مفقود |
| commerce | 1 (جزئي) | 1 | migration بسيطة — نفس نمط الربط بالكيان السيادي |
| communications | 1 | 0 | صفر |
| **الإجمالي** | **~119** | **~79** | — |

(+ 3 أسطر "غير قابل للتطبيق" مش مرتبطة بأي service.ts إطلاقًا:
`@/lib/auth-utils`, `@/hooks/use-debounce`, `@/components/ui/tooltip` — تفاصيلها
في تقرير المجموعة 5.)

## أهم الاكتشافات العابرة للدومينات

1. **agritech معطّل بالكامل على مستوى الراوتينج** — لا `router.py`، غير مسجّل
   في `main.py` (فقط `main.py.bak`). هذا أخطر من أي حالة (ب) فردية فيه لأنه
   يمنع أي استخدام حي للدومين كله بغض النظر عن حالة كل دالة.
2. **نمط "aliasing مجاني" متكرر جدًا عبر كل الدومينات تقريبًا** (`getPolicies`↔`listPolicies`،
   `getCampaigns`↔`listCampaigns`، `createCase`↔`createDispute`، `getDestinations`↔`listDestinations`...)
   — عدد كبير من حالات (أ) هي مجرد إعادة تسمية، صفر عمل باك إند، أرخص حتى من
   "وصلة" عادية.
3. **نمط "البيانات جاهزة، المكوّن نفسه (JSX) مش مكتوب"** يتكرر في invitations
   (5 مكوّنات)، agritech (3 مكوّنات)، zamakana (2)، tourism-sports (1) — هذه
   كلها فرص رخيصة جدًا: صفر عمل باك إند، مجرد كتابة مكوّن React فوق endpoint موجود.
4. **نمط "ربط بكيان سيادي" متكرر** (academy/commerce/projects عبر
   `public/[slug]/page.tsx`) — الثلاثة يحتاجون نفس العمود/الربط
   (`sovereign_entity_id`)، فرصة لـmigration واحدة موحّدة بدل ثلاث منفصلة (قرار
   تصميم لاحق).
5. **سابقة realestate (فحص `repository.py`) أثبتت قيمتها بشكل متكرر** — حالات
   كتير في insurance, tourism-sports, tenders-auctions, social, employment
   كانت ستُصنَّف (ب) لو الفحص وقف عند `service.py`/`router.py` فقط، لكنها
   فعليًا (أ) لأن المنطق جاهز في `repository.py` وغير مكشوف.
6. **realestate تحديدًا: صفر حالات (ب) متبقية** — الجلسة السابقة
   (`realestate-hooks-layer-design-decision`) نفّذت الحل فعليًا (migration 043)،
   الحالات الأربع الجديدة في هذا التحقيق أسماء/أنواع بديلة فوق نفس العمل.

## الخطوة التالية (خارج نطاق هذه الجلسة)

قرار "نبني ولا نقلّم" لكل حالة (ب) — يحتاج جلسة منفصلة بعد مراجعة هذا الملخص.
الأولوية الواضحة قبل أي قرار: **agritech routing gap** (رقم 1 أعلاه) لأنه
يمنع الدومين كله بغض النظر عن أي قرار لاحق بخصوص حالاته الفردية.
