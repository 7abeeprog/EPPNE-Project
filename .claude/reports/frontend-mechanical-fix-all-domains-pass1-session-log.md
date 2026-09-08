# جلسة: frontend-mechanical-fix-all-domains-pass1

**التاريخ:** 2026-08-31
**الهدف:** تطبيق فئة (أ) وضع استيراد غلط + فئة (ج) مسار/اسم ملف مختلف — فقط — على
كل دومينات الفرونت إند اللي فيها TS2305/TS2307، صفر تحقق إضافي غير `tsc`،
صفر لمس على أي `service.ts`.

**ملاحظة منهجية مهمة:** 5 agents مستقلين اتبعثوا بالتوازي لتغطية 25 دومين، لكن
الحساب ضرب rate limit في نص الشغل (كل الـ5 وقفوا فجأة بأخطاء "session limit").
الجلسة كملت الباقي **مباشرة بدون subagents** (نفس المحادثة)، بما في ذلك مراجعة
والتحقق من كل حاجة كان الـagents خلّصوها جزئيًا قبل ما يقفوا.

## النمط المكتشف (موحّد عبر كل الدومينات تقريبًا)

كل `services/<domain>.ts` (أو `.service.ts`) بيصدّر **كائن واحد**:
```ts
export const AgritechService = { createFarm: async (...) => {...}, listFarms: ..., ... };
```
لكن معظم `hooks/<domain>/*.ts` و`components/<domain>/*.tsx` كانت بتستورد
دوال منفردة بالاسم مباشرة (`import { createFarm } from '@/services/agritech'`)
بدل استيراد الكائن. **فئة أ** = الاسم موجود فعليًا كمفتاح في الكائن، بس بنمط
استيراد غلط → الإصلاح: استيراد `XService` واستخدام `XService.name(...)` في كل
موضع استدعاء. **فئة ب الحقيقية** = الاسم مش موجود بأي شكل في الكائن (توثيق فقط،
صفر لمس).

## نتيجة `tsc` الإجمالية

TS2305+TS2307 قبل الجلسة: **442** → بعدها: **290** (تراجع 152 خطأ، كلها فئة أ/ج
مُصلَحة). الباقي (290) فئة ب حقيقية موثّقة تحت، أو استثناءات (حزم npm، ملفات
مفقودة كليًا)، أو `hooks/transport/useVehicles.ts` (استثناء موثّق من جلسة سابقة).

## الدومينات اللي اتصلّحت (فئة أ مُطبَّقة، صفر لمس على service.ts)

| # | الدومين | ملفات اتصلحت |
|---|---|---|
| 1 | agritech | useBioAssets, useCertificates, useCropCycles, useFarms, useHarvests, useSensors, useTraceability (7) |
| 2 | arbitration-syndicates | useCases, useElections, useJuryVote, useLicenses, useSyndicates (5) |
| 3 | command | useAlerts (1) |
| 4 | employment | jobs/[jobId]/page, jobs/page, employment/page, payroll/page, AttendanceWidget (5) |
| 5 | insurance | useClaims, useEmployeeProfile, usePensions, usePolicies, useSubscriptions (5) |
| 6 | invitations | useCampaigns, useChatWithAI, useInteractions, useInvitations, useLeads, useStats, useTickets (7) |
| 7 | logistics | useWarehouses*, useEquipment, useForecast, useInventory (4) |
| 8 | manufacturing | useFacilities, useRawMaterials, MaintenanceRadar (3) |
| 9 | marketplace | PurchaseModal, ServiceDetails (2) |
| 10 | projects | AdvancedMilestones, ContributionModal (2) |
| 11 | realestate | **صفر ملفات — كل الأسماء فئة ب حقيقية** (راجع القسم تحت) |
| 12 | social | useConnections*, useContracts*, useGifts*, useGroups*, useMatchSuggestions*, useMatchmaking*, useOccasions*, usePosts*, useSubscriptions* (9، useEvents/usePages صفر تطابق) |
| 13 | sovereign-entities | BrandEditor*, EntityForm*, EntityTreeView*, KYBDocumentUploader*, RepresentativeList*, WalletActions*, WalletBalance* (7) |
| 14 | tenders-auctions | useAuctions, useBids, useCloseAuction, useEvaluateBid, useLiveBids, usePlaceBid, useSubmitBid, useTenders (8) |
| 15 | tourism-sports | useDestinations, usePlayers, usePrograms, useSportsOrganizations, useTournaments, useTransfers (6) |
| 16 | transport | useBookings*, useDeliveries*, useFleets*, useHubs*, useRoutes*, useTrips* (6، useVehicles استثناء موثّق سابقًا — صفر لمس) |
| 17 | zamakana | useCampaigns*, useEdges*, useKnowledgeGraph*, useNodes*, useScenarios* (5) |
| 18 | digital-twin | TwinConfigForm, legacy/page (+ حذف import ميت لـ`createTimeCapsule`/`createDigitalWill` غير مستخدمين) (2) |
| 19 | health | health/page, AIPrognosisRadar, EmergencySOSButton (3) |
| 20 | communications | NotificationList* (1) |
| 21 | ai-agents | AgentForm (1) |
| 22 | automation | secrets/page*, workflows/[id]/executions/[executionId]/page*, workflows/[id]/executions/page*, workflows/[id]/page* (+ إصلاح import مكرر لـ`ExecutionsPage`)، SecretForm*, WorkflowBuilder*, AIAgentConfig* (7) |
| 23 | finance (wallet) | wallet/page — تصحيح مسار `balance-card`→`BalanceCard` (1، فئة ج) |
| 24 | sovereign-entities/academy/commerce/projects (مشترك) | `public/[slug]/page.tsx` — تصحيح `getPublicEntityPage` فقط (1) |

`*` = كان الملف بدأه أحد الـagents الخمسة قبل ما يقف بـrate limit، وتم التحقق
من اكتماله وصحته مباشرة (مقارنة كل اسم مستدعى بقائمة مفاتيح الـService
الفعلية) — بعضها كان كامل فعلاً، بعضها كان ناقص وكُمِّل.

**ملاحظة أمانة تقنية:** بعض الإصلاحات في `transport` احتاجت تعديل شكل الوسيط
الثاني (`idempotencyKey: string` → `{ 'Idempotency-Key': idempotencyKey }`)
عشان توقيع `bookTrip`/`payDelivery` الحقيقي في الـservice بيستقبل كائن headers
مش string خام — اتحقّق منه بقراءة الكود الفعلي، مش تخمين، وده الحد الأدنى
اللازم عشان الاستيراد الصحيح يترجم أصلاً (مش تجاوز لنطاق "فئة أ").

**دومين `academy`, `saas`, `commerce`:** كانوا مصنّفين ضمن "الـ7 دومينات
المصحَّحة مسارها بس" — بعد الفحص، الصفحات فيهم بتستورد من طبقة hooks وسيطة
(`@/hooks/academy-queries`, `@/hooks/saas/*`) مش من `services/*.service.ts`
مباشرة، فمفيش أي `TS2305`/`TS2307` فعلي متبقي يخص هذه الجلسة (فجوة `saas`
المذكورة في الجلسة السابقة هي أخطاء `TS2339`/`TS2551` — خارج نطاق هذه المرحلة
تمامًا زي ما حدد المستخدم). **صفر لمس، صفر حاجة تتصلح.**

## استثناءات (وثّقت فقط — صفر لمس، تحتاج جلسة مخصصة)

| النوع | التفاصيل |
|---|---|
| **دومين تصميم كامل** | `realestate` — **كل** استدعاءات الـhooks (`getProperties`, `getProperty`, `createProperty`, `updateProperty`, `deleteProperty`, `getPropertyOwnerships`, `getSmartContractStatus`, `getAssetTokenization`) مفيش ولا واحدة منها موجودة في `RealEstateService` — الـservice مبني حول أصول أرض/تطوير جزئية (`createLandAsset`, `createPropertyUnit`, `tokenizeAsset`...) مش CRUD عام للعقارات. هذا نفس نمط `realestate-hooks-layer-nonexistent-function-imports` الموثّق قبل كده كسابقة — **يحتاج قرار تصميم**، مش تصحيح ميكانيكي. |
| **حزمة npm بمسار غلط + استدعاء غلط** | `date-fns/ar` مستخدَم في ~30 ملف كـ`import { formatDistanceToNow } from 'date-fns/ar'` — ده غلط مزدوج: (1) الـlocale الصحيح في date-fns v4 هو `date-fns/locale/ar` مش `date-fns/ar`، (2) `formatDistanceToNow` أصلاً دالة من `date-fns` نفسها مش من الـlocale — الاستخدام الصحيح `formatDistanceToNow(date, { locale: ar })`. هذا يحتاج تعديل منطق في كل موضع استدعاء (مش مجرد سطر استيراد) — **خارج نطاق فئة أ/ج بالتعريف**، صفر لمس. |
| **حزمة npm غير مثبتة** | `uuid` (~15 ملف) و`qrcode.react` (ملف واحد) مش موجودين في `package.json` ولا `node_modules` إطلاقًا — يحتاج `npm install`، قرار منتجي/تبعية مش تصحيح استيراد. |
| **ملفات/hooks معدومة تمامًا** (اتأكد بـ`Glob` قبل التصنيف) | `components/agritech/{FarmCard,WeatherAlertCard,FarmZoneCard}.tsx`, `hooks/agritech/useStats.ts`, `hooks/logistics/useStats.ts`, `hooks/manufacturing/{useProductionLines,usePendingMaintenance,useStats}.ts`, `components/iot/{ReadingsChart,MaintenanceLogs}.tsx`, `components/zamakana/{PledgeForm,PledgeCard}.tsx` + `hooks/zamakana/usePledges.ts`, `components/tourism-sports/TransferCard.tsx`, `components/invitations/{CampaignCard,InvitationCard,InvitationStatusBadge,TicketCard,TicketStatusBadge}.tsx`, `components/finance/{web3-deposit-withdraw,admin-mint-card}` (كـ`Web3DepositWithdraw`/`AdminMintCard`)، `components/automation/node-configs/{DatabaseConfig,HttpResponseConfig,SlackConfig}.tsx`. |
| **موثّق من جلسة سابقة، احترمناه** | `hooks/transport/useVehicles.ts` (محتوى غلط كليًا، نسخة من trips) — صفر لمس. `types/realestate.ts` (`Property`/`PropertyFormData`/`TokenizationFormData` مش متوافقة مع الـschema) — صفر لمس. |

## جدول فئة (ب) — أسماء غير موجودة إطلاقًا (تجميع مختصر حسب الدومين)

القائمة الكاملة موجودة في `tsc` نفسه (290 خطأ متبقي بعد الجلسة)؛ أبرزها حسب
عدد الأخطاء: `social` (34), `transport` (26، أغلبها `useVehicles` الاستثناء),
`tenders-auctions` (17), `tourism-sports` (16), `insurance` (12),
`agritech` (11), `realestate` (9), `projects` (7), `arbitration-syndicates` (7).
كل الأسماء دي اتفحصت واحدة واحدة مقابل مفاتيح الـService الفعلية قبل
تصنيفها ب — صفر تخمين.

## الخطوة التالية المقترحة (خارج نطاق هذه الجلسة)

جلسة مخصصة لـ`realestate` (قرار تصميم: توحيد الـhooks مع الـservice الفعلي
أو العكس)، وجلسة منفصلة لباج `date-fns/ar` (يمس ~30 ملف عبر كل الدومينات
تقريبًا)، وقرار تبعية لـ`uuid`/`qrcode.react`.
