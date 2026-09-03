# Category-B Decision-Needed Triage — Session Log

بدأ: 2026-09-04

## الهدف
تجميع كل بنود "تحتاج قرار" المتراكمة عبر جلسات frontend-category-b-phase1، phase2، وagritech، وPROGRESS_LOG.md، في جدول واحد مصنّف لثلاث فئات: فوري / قرار بسيط / قرار كبير. تنفيذ فئة "فوري" فقط.

## المصادر
- frontend-category-b-phase1-session-log.md
- frontend-category-b-phase2-session-log.md
- agritech-full-domain-build-session-log.md
- PROGRESS_LOG.md (بنود مشابهة غير مذكورة في الثلاثة أعلاه)

## فئة (فوري) — نُفِّذت في هذه الجلسة

| # | البند | الإصلاح | تحقق حي |
|---|---|---|---|
| 1 | `update_bio_cohort_count-tenant-id-bug` (agritech/repository.py:146) | كود ميت (صفر callers، تأكَّد بـgrep) كان بينادي `get_bio_cohort(cohort_id)` بمعامل واحد بينما التوقيع يتطلب `tenant_id` إجباريًا → `TypeError` مضمون لو اتنادت مستقبلًا. أُضيف `tenant_id: int` للتوقيع + فلترته في الـ`UPDATE` نفسه (`and_`) + تمريره لـ`get_bio_cohort` في النهاية. | `python -c "from app.domains.agritech import repository"` نجح بلا أخطاء. صفر caller حاليًا → صفر أثر على أي سلوك قائم. مُسجَّل في PROGRESS_LOG.md (إغلاق البند). |

لم يُعثر على بنود "فوري" حقيقية أخرى — الجلستان phase1/phase2 استنفدتا فعليًا كل الحالات الميكانيكية الآمنة (aliasing، rename، توصيل endpoint موجود) أثناء التنفيذ الأصلي؛ ما تبقّى في قوائم "تحتاج قرار" هو بالتعريف ما تعذّر حله ميكانيكيًا وقتها.

---

## فئة (قرار بسيط) — بانتظار ردك (سؤال واحد سطر لكل بند)

كل هذه البنود: "نبني endpoint واحد بنطاق صغير في الباك إند، ولا نحذف/نعطّل الجزء المعطوب في الفرونت إند؟" ما لم يُذكر خلاف ذلك.

### command
1. `dismissAlert` — لا مفهوم dismiss بالباك إند (فقط resolve). حاليًا `useDismissAlert` بينادي `dismissAlert(alertId)` **غير مستوردة أصلًا** (خطأ compile حي: `Cannot find name`).
2. `useSystemAlerts`: `is_resolved`/`skip` — الباك إند عنده فلتر `status` (enum) مش `is_resolved` (bool)، و`skip` مش مدعوم إطلاقًا. صفحة `command/page.tsx` بتمرر `is_resolved: false` فعليًا متوقّعة فلترة بتحصلش — التنبيهات المعروضة كـ"نشطة" فعليًا تشمل المحلولة.

### manufacturing
3. `updateFacility`/`deleteFacility` — صفر دعم باك إند.
4. `useProductionLines` — صفر list endpoint.
5. `useStats` — صفر endpoint إحصائيات.
6. `usePendingMaintenance` — الموجود per-line، الاستهلاك الفعلي بيحتاج tenant-wide.

### tourism-sports
7. `getDestination` (مفرد) — صفر دعم.
8. `getPlayers`/`getPrograms`/`getSportsOrganizations` (قوائم) — صفر list endpoint لكل منها.
9. `useMatches`/`useMyTickets` — صفر دعم، وحتى `get_ticket` الداخلية في service.py الأصلي معطوبة.
10. `useTournaments` (قائمة+مفرد) — صفر دعم.
11. **[أولوية أعلى — باج حي محتمل]** `getTransfers`/`TransferCard` — `TourismSportsRepository` **لا تملك `get_transfer`/`list_transfers` إطلاقًا**، لكن `service.py: place_transfer_bid` (كود أصلي قديم، لم يُلمَس بأي جلسة) بينادي `self.repo.get_transfer(transfer_id)` في مسار idempotency-cache — أي طلب مكرر بنفس `idempotency_key` هيرمي `AttributeError` **في الإنتاج الآن**، بمعزل تام عن قرار بناء `TransferCard`. القرار هنا فعليًا مركّب: (أ) نصلح `place_transfer_bid` بإضافة `get_transfer`/`list_transfers` لـ`repository.py` (سطور قليلة، الجدول `PlayerTransfer` موجود بالفعل)، و(ب) هل نبني `GET` endpoint فوقها لـ`TransferCard` كمان؟

### transport
12. `getVehicles`/`deleteVehicle` — مفهوم "مركبات عامة" غير موجود، فقط `list_available_vehicles` مفلترة.
13. `useCancelTrip` — صفر `cancel_trip`.
14. `getDeliveries`/`getMyDeliveries` — صفر list.
15. `getFleets`/`updateFleet`/`deleteFleet` — صفر دعم.
16. `updateHub`/`deleteHub` — صفر دعم.
17. `getRoutes` (قائمة)/`updateRoute`/`deleteRoute` — صفر دعم.
18. `optimizeRoute` كعملية مستقلة — المنطق مدمج داخل `create_route` فقط، يحتاج فصل.
19. `getTransportStats` — صفر endpoint.
20. `transport-formdata-vs-openapi-schema-mismatch`: `DeliveryFormData`/`RouteFormData` اليدوية لا تطابق الـschema المولَّد (`pickup_address`/`dropoff_address`/`waypoints` طلعت `Record<string, never>` لغياب Pydantic sub-model)، و`DeliveryTaskCreate.sender_id` مطلوب مش موجود في `DeliveryFormData`. سؤال: نصلح schema الباك إند (نضيف sub-models صريحة) ولا نرقّع types الفرونت إند؟ (نفس الفئة: `trip.driver_name` مستخدَم في الفرونت لكن غير موجود في `TripResponse`، فقط `driver_id`.)

### insurance
21. `getInsuranceStats` — صفر تجميع إحصائيات.
22. `deletePolicy` — صفر حذف رغم استعداد `is_deleted` على الموديل.
23. `insurance-update-claim-permission-asymmetry` — `update_claim` مقيَّدة `superuser`-only بينما `review_claim` المجاورة بتستخدم فحص دور membership أوسع. صفر ثغرة أمنية (الحالي أضيق لا أوسع). سؤال مختلف الصيغة: **نوسّع `update_claim` لنفس دور `review_claim`، ولا تبقى superuser-only كما هي (قرار متعمَّد سابقًا)؟**

### tenders-auctions
24. `getMyBids` — صفر استعلام مجمَّع لعطاءات المستخدم عبر المناقصات+المزادات.

### social
25. `acceptConnection`/`rejectConnection` — صفر دعم.
26. `getDigitalGifts`/`getPhysicalGifts` — صفر دعم.
27. `getGroups`/`leaveGroup`/`getGroupMembers` — صفر دعم.
28. `getOccasions`/`deleteOccasion` — صفر دعم.
29. `getSubscriptionPlans`/`cancelSubscription` — صفر دعم.
30. `social-createpostmodal-missing-component-decision` — **الباك إند جاهز بالكامل** (`createPost`/`POST /social/posts` موصولان فعلًا)، فقط مكوّن UI مفقود. سؤال مختلف: **نضيف `CreatePostModal` كسادس مكوّن ضمن البند 3 (5 invitations + 1 tourism-sports)، ولا نتركه لجلسة لاحقة منفصلة؟**

---

## فئة (قرار كبير) — تستاهل جلسة مستقلة لاحقًا (صفر سؤال الآن)

| البند | لماذا كبير |
|---|---|
| **transport: `useDrivers`** | صفر مفهوم "سائق" مستقل بالباك إند بالكامل — يحتاج قرار تصميم: دور `User` أم كيان `Driver` منفصل (جدول/schema جديد محتمل). |
| **transport: ميزة المركبات معدومة بالكامل من الفرونت إند** (`useVehicles`, `useCreateVehicle`, `useDeleteVehicle`, `useAvailableVehicles` — غير موجودة في أي ملف بالكودبيز كله، رغم `TransportService.createVehicle`/`updateVehicleLocation`/`getAvailableVehicles` جاهزة بالباك إند) | ميزة UI كاملة تحتاج كتابة من الصفر (مش إصلاح استيراد)، مرتبطة منطقيًا بـ`useDrivers` أعلاه — الأنسب جلسة "transport vehicles & drivers" واحدة. |
| **social: دومين Pages كامل** (5 حالات — follow/unfollow) | صراحة يحتاج **جدول جديد** بالباك إند. |
| **social: دومين Events كامل** (5 حالات) | حجم غير موثَّق بالتفصيل هنا (يحتاج جرد أول قبل حتى تأطيره كقرار بسيط أو كبير) — تحفّظ: تُصنَّف كبير لحد ما تُجرَد. |
| **realestate: `realestate-hooks-layer-nonexistent-function-imports`** (12 حالة) | الباك إند جاهز، لكن أسماء الدوال في الـ4 hooks (`getMyOwnerships`, `getProperties`, `createProperty`, `deleteProperty`, `getPropertyOwnerships`, `getAssetTokenization`, `createTokenization`, `buyFractionalShare`...) **مختلفة دلاليًا** عن methods الـservice الفعلية (`createPropertyUnit`, `listUnitsForSale`, `tokenizeAsset`, `buyFraction`...) — رينيم أعمى ممكن يربط دالة بمعنى غلط. يعطّل build لصفحة كاملة + 4 مكونات، يحتاج مراجعة دقيقة اسم-باسم قبل أي ربط. |
| **`api-types-schema-name-collision-auction-tender-create`** | تصادم اسم class Python بين دومينين (`tenders_auctions` وربما `realestate`/`invoicing`) بيولّد types غلط تمامًا في `api-types.ts`. يحتاج تحقيق (`grep` لتتبع مصدر التصادم) + إعادة تسمية + إعادة توليد `api-types.ts` — خارج نطاق "وصلة ميكانيكية". |
| **agritech: `agritech-phase2-frontend-gaps`** | مجموعة: named exports مفقودة في `services/agritech.ts` (تكسر 6 hooks حاليًا)، `hooks/agritech/useStats.ts` غير موجود (تكسر الصفحة الرئيسية)، + 4 دوال service.py مفقودة (`update_farm`, `delete_farm`, `list_harvests`, `list_bio_cohorts`, stats aggregation). حجم يعادل جلسة phase2 كاملة (نفس نمط باقي الدومينات) — مؤجَّلة بقرار مستخدم صريح سابق. |
| **agritech: `agritech-traceability-certificate-idor-defense-gap`** | `add_traceability_stage`/`issue_certificate`/`register_harvest`/`register_bio_yield` تقبل IDs خام بدون تحقق ملكية الـtenant للكيان المُشار إليه (defense-in-depth، صفر تسريب مباشر). قرار منتجي عابر لعدة دومينات مشابهة، أنسب مراجعة موحَّدة بدل قرار agritech منفرد. |
| **`frontend-types-null-vs-undefined-mismatch-pattern`** | `types/invitations.ts`/`types/social.ts` اليدوية بتعرّف الحقول الاختيارية `X\|undefined` بينما الـPydantic الفعلي `X\|null` — تصادم منهجي عابر لكل حقل تقريبًا في الملفين (وربما ملفات types يدوية تانية). الحل الجذري (توليد أنواع تلقائي بدل ملفات يدوية موازية) يمس المشروع كله. |
| **`iot-translation-service-method-mismatches-post-backlog43-fix`** | بعد إصلاح Backlog #43 (rename `iotService`→`IoTService`)، ظهرت أعطال حقيقية: `IoTService.getAssets` (جمع، مستخدَمة في `AssetsManager.tsx`/`IoTDashboardStats.tsx`) مقابل `getAsset` (مفرد فعلي، يتطلب `assetId` مش `{limit}`) — **مش رينيم بسيط**، الموجود method مفردة بمعامل مختلف تمامًا عن المتوقَّع (list). محتاج تحقق: هل `list_assets`/`getAssets` موجودة أصلًا بالباك إند بأي اسم؟ + type mismatches منفصلة في `CarbonCreditPanel`/`BatchTranslator`/`ChatTranslator`/`TextTranslator` (توقيع `headers?` مقابل `MutationFunction`). 7 ملفات متأثرة، خارج نطاق الفحص العميق في هذه الجلسة (لم يُذكر أصلًا في phase1/phase2/agritech) — يستاهل جلسة تحقيق مستقلة قبل التصنيف الدقيق.

---

## ملاحظة منهجية
البنود المُغلَقة بالفعل ضمن الجلسات المصدر (aliasing، توصيل endpoints جاهزة، إلخ) لم تُدرَج هنا — هذا التقرير حصريًا لما تبقّى تحت "تحتاج قرار" وقت بدء هذه الجلسة (2026-09-04).

---

## رد المستخدم (2026-09-04) + التنفيذ الفعلي

القرارات: (أ) تنفيذ فوري لباج `get_transfer`/`list_transfers` + GET endpoint لـ`TransferCard`، (ب) تنفيذ 4 list/get endpoints في tourism-sports (`getDestination`, `getPlayers`, `getPrograms`, `getSportsOrganizations`)، (ج) التحقق من `transport formdata sub-models` (GeoAddress/Waypoint) قبل أي تنفيذ، (د) البقية (command, manufacturing, insurance stats/delete, tenders-auctions, social) → **لا تنفيذ، تبقى backlog**، (هـ) `insurance-update-claim-permission-asymmetry` → **مغلق، يبقى superuser-only** (وثّق في PROGRESS_LOG).

### 1+2. tourism-sports — باج `get_transfer` + 6 endpoints جديدة

**`repository.py`:** أُضيفت `get_destination(dest_id, tenant_id)`، `list_programs(tenant_id)`، `list_sports_orgs(tenant_id, org_type=None)`، `list_player_profiles(tenant_id, club_id=None, sport_category=None)`، `get_transfer(transfer_id, tenant_id)`، `list_transfers(tenant_id, status=None)` — كلها بنفس نمط الفلترة المزدوجة (`tenant_id` في الـquery) المستخدَم في `get_sports_org` الموجودة مسبقًا.

**`service.py`:** أُضيفت الأغلفة المقابلة (`get_destination`, `list_programs`, `list_sports_orgs`, `list_players`, `get_transfer`, `list_transfers`) — كل getter مفرد بيتحقق من `tenant_id` بعد الجلب ويرفع `NotFoundError`. **إصلاح الباج الحي:** استدعاء `self.repo.get_transfer(transfer_id)` (سطر واحد، مسار idempotency-cache في `place_transfer_bid`) — كانت بتنادي دالة غير موجودة إطلاقًا، أُصلحت لـ`self.repo.get_transfer(transfer_id, tenant_id)` بعد ما الدالة بقت موجودة.

**`router.py`:** 6 endpoints جديدة (`GET /destinations/{dest_id}`, `GET /programs`, `GET /sports/organizations`, `GET /sports/players`, `GET /sports/transfers`, `GET /sports/transfers/{transfer_id}`) — تأكَّد بـgrep صفر تعارض مسارات مع الموجود (`/sports/players/profile` POST، `/sports/transfers/bid` POST).

**تحقق حي (`tests/test_tourism_sports_decision_triage_wiring.py`، DB حقيقية، صفر mock):** 5 اختبارات — `get_destination` (+ عزل tenant_id + 404 لمعرف غير موجود)، `list_programs`، `list_sports_orgs` (+ فلترة `org_type`)، `list_players` (+ فلترة `club_id`)، `get_transfer`/`list_transfers` (+ عزل tenant_id، يغطي مباشرة مسار الباج الأصلي في `place_transfer_bid`). **PASSED 5/5، exit code صريح خارج أي pipe: `PYTEST_EXIT_CODE=0`.**

**بقان اتصلحا أثناء التحقق:**
- `SportsEntityType.AGENCY` غير موجودة (القيم الفعلية: `CLUB`/`ACADEMY`/`MARKETING_AGENCY`) — باج في الاختبار نفسه، اتصلح لـ`MARKETING_AGENCY`.
- `create_transfer` (repository.py) بتعمل `flush()` بس بلا `commit()` — نفس نمط باج insurance.update_claim المكتشَف في phase2 (deadlock بين transaction الاختبار وجلسة التنظيف المنفصلة). أُضيف `await db.commit()` صريح في الاختبار بعد `create_transfer` (الدالة نفسها لم تُعدَّل — نفس نمط باقي دوال الملف اللي بتستخدم `flush()` فقط، خارج نطاق هذه الجلسة).
- محاولة أولى لاختبار `list_programs` حاولت INSERT بـ`tenant_id=2` (`OTHER_TENANT_ID`) غير موجود في `academy_tenants` على DB الاختبار → `ForeignKeyViolationError`. اتصلح بإزالة فرع عزل الـtenant من هذا الاختبار تحديدًا (العزل متحقَّق منه فعليًا عبر الـgetters المفردة الأربعة في نفس الملف).

**تحقق `app.main`:** `python -c "from app.main import app"` نجح بعد كل التعديلات.

### 3. transport formdata sub-models — **تأكيد: مُطبَّقة بالفعل، صفر تنفيذ لازم**

فحصت `eppne-backend/app/domains/transport/schemas.py`: `GeoAddress` (سطر 120) و`Waypoint` (سطر 52) **موجودتان بالفعل** كـPydantic sub-models حقيقية (مش `dict`/`list[dict]` خام)، و`DeliveryTaskCreate.sender_id` **محذوف بالفعل** (تعليق صريح في الكود: "كان موجود سابقًا كحقل مطلوب هنا بلا أي استخدام فعلي... حُذف [جلسة transport-domain-full-build، 2026-09-01]"). يعني القرار المذكور في `transport-formdata-vs-openapi-schema-mismatch` (2026-08-31) **اتحل فعلًا في جلسة لاحقة** (transport-domain-full-build، 2026-09-01) قبل ما نبدأ الجلسة دي — البند كان stale.

**اكتشاف جانبي (خارج نطاق طلبك، صفر تنفيذ):** `eppne-web/src/lib/api-types.ts` **المولَّد** لسه قديم ومايعكسش هذا الإصلاح — `RouteCreate.waypoints`/`RouteResponse.waypoints` لسه `Record<string, never>[]` بدل شكل `Waypoint` الحقيقي. ده يعني الفرونت إند (لو بيعتمد على الأنواع المولَّدة مباشرة بدل `types/transport.ts` اليدوي) لسه ممكن يواجه نفس المشكلة على مستوى TypeScript، حتى لو الباك إند سليم 100%. `types/transport.ts` اليدوي (المستخدَم فعليًا في `useDeliveries.ts`/`useRoutes.ts`) بالفعل بيعرّف الشكل الصح، فمفيش أثر عملي حاليًا. **لم يُلمَس** — يحتاج قرار منفصل هل نعيد توليد `api-types.ts` (نفس فئة `api-types-schema-name-collision-auction-tender-create` المفتوحة أصلًا في tenders-auctions).

### الحالة النهائية
✅ الثلاثة بنود اتقفلت (اتنين تنفيذ حي + واحد تأكيد بلا حاجة لتنفيذ). البقية (command, manufacturing, insurance stats/delete, tenders-auctions, social) تبقى backlog بدون لمس بقرار المستخدم. `insurance-update-claim-permission-asymmetry` اتقفل بقرار "البقاء كما هو" في PROGRESS_LOG.
