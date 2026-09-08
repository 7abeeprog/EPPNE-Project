# فئة (ب) — social + transport

مفاتيح `SocialService` الحالية (services/social.ts): `createPost, getFeed, likePost, sharePost, createGroup, joinGroup, createContract, signContract, setupMatchProfile, getMatchSuggestions, requestConnection, getMyConnections, createOccasion, getUpcomingOccasions, sendDigitalGift, requestPhysicalGift, createSubscriptionPlan, subscribeGroup, getGroupFeatures`.

مفاتيح `TransportService` الحالية (services/transport.ts): `createHub, listHubs, createFleet, createVehicle, updateVehicleLocation, getAvailableVehicles, createRoute, createTrip, startTrip, completeTrip, getMyTrips, bookTrip, getMyBookings, createDelivery, payDelivery, completeDelivery`.

## social

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `CreatePostModal` (مكوّن) | `app/(dashboard)/social/page.tsx` | TS2307 وحدة غير موجودة | المكوّن مفقود فعليًا من `components/social/` (فقط `PostCard.tsx`, `CreateOccasionModal.tsx` موجودان). لكن العملية التي سيستدعيها (`createPost`) **موجودة بالكامل**: `SocialService.createPost` + `POST /social/posts` مُوجّه ومُوثّق في openapi.json | (أ) الباك إند جاهز بالكامل؛ الناقص هو ملف الواجهة (مكوّن UI) نفسه فقط |
| 2 | `getConnections` | `hooks/social/useConnections.ts` | TS2305 | `SocialService.getMyConnections` يقوم بنفس العملية تمامًا (`GET /social/connections`) | (أ) عبر إعادة تسمية/alias — نفس `getMyConnections` |
| 3 | `acceptConnection` | `hooks/social/useConnections.ts` | TS2305 | لا يوجد أي منطق لتغيير حالة `UserConnection.status` (PENDING→ACCEPTED) في repository.py/service.py/router.py؛ الحقل موجود في الموديل فقط | (ب) غير موجود إطلاقًا |
| 4 | `rejectConnection` | `hooks/social/useConnections.ts` | TS2305 | نفس أعلاه — لا يوجد state-transition method | (ب) غير موجود إطلاقًا |
| 5 | `getContracts` | `hooks/social/useContracts.ts` | TS2305 | لا توجد أي دالة listing للعقود في أي طبقة (repo فيه `get_contract` مفرد فقط) | (ب) غير موجود إطلاقًا |
| 6 | `getContract` | `hooks/social/useContracts.ts` | TS2305 | `SocialRepository.get_contract(contract_id)` موجودة لكنها تُستخدم داخليًا فقط (في `sign_contract`)؛ لا service method عام ولا router endpoint (`GET /social/contracts/{id}`) | (أ) موجود في repository.py فقط |
| 7 | `getEvents` | `hooks/social/useEvents.ts` | TS2305 | نموذج `SocialEvent` وschemas (`SocialEventCreate/Response`) موجودان في models.py/schemas.py، لكن **صفر** دوال في repository.py/service.py/router.py | (ب) غير موجود إطلاقًا (البيانات جاهزة، منطق CRUD كله غائب) |
| 8 | `getEvent` | `hooks/social/useEvents.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 9 | `createEvent` | `hooks/social/useEvents.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 10 | `attendEvent` | `hooks/social/useEvents.ts` | TS2305 | نموذج `EventAttendee` موجود (models.py) لكن بدون أي دالة إضافة/حذف حضور في أي طبقة | (ب) غير موجود إطلاقًا |
| 11 | `unattendEvent` | `hooks/social/useEvents.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 12 | `getDigitalGifts` | `hooks/social/useGifts.ts` | TS2305 | repo فيه `get_digital_gift(id)` مفرد فقط، ولا list method في أي طبقة، ولا GET endpoint | (ب) غير موجود إطلاقًا |
| 13 | `getPhysicalGifts` | `hooks/social/useGifts.ts` | TS2305 | نفس أعلاه (`get_physical_gift_request(id)` مفرد فقط) | (ب) غير موجود إطلاقًا |
| 14 | `getGroups` | `hooks/social/useGroups.ts` | TS2305 | لا list method لأي طبقة (فقط `create_group`, `get_group` مفرد) | (ب) غير موجود إطلاقًا |
| 15 | `getGroup` | `hooks/social/useGroups.ts` | TS2305 | `SocialRepository.get_group(group_id, tenant_id)` موجودة لكن غير مُعروضة عبر service.py/router.py | (أ) موجود في repository.py فقط |
| 16 | `leaveGroup` | `hooks/social/useGroups.ts` | TS2305 | `add_group_member` موجودة لكن لا يوجد remove/leave في أي طبقة | (ب) غير موجود إطلاقًا |
| 17 | `getGroupMembers` | `hooks/social/useGroups.ts` | TS2305 | لا توجد دالة لجلب قائمة أعضاء مجموعة في أي طبقة | (ب) غير موجود إطلاقًا |
| 18 | `getMatchProfile` | `hooks/social/useMatchmaking.ts` | TS2305 | `SocialRepository.get_match_profile(user_id)` موجودة، تُستخدم داخليًا فقط في `get_match_suggestions`؛ لا service method عام ولا `GET /social/match/profile` | (أ) موجود في repository.py فقط |
| 19 | `updateMatchProfile` | `hooks/social/useMatchmaking.ts` | TS2305 | `SocialService.setup_match_profile` يعمل upsert فعليًا (`create_or_update_match_profile`) وهو مُوجّه بالفعل عبر `POST /social/match/profile` | (أ) عبر إعادة تسمية/alias — نفس `setupMatchProfile` |
| 20 | `getConnections` | `hooks/social/useMatchmaking.ts` | TS2305 | مطابق للبند 2 | (أ) alias لـ `getMyConnections` |
| 21 | `acceptConnection` | `hooks/social/useMatchmaking.ts` | TS2305 | مطابق للبند 3 | (ب) غير موجود إطلاقًا |
| 22 | `rejectConnection` | `hooks/social/useMatchmaking.ts` | TS2305 | مطابق للبند 4 | (ب) غير موجود إطلاقًا |
| 23 | `getMatchProfile` | `hooks/social/useMatchSuggestions.ts` | TS2305 | مطابق للبند 18 | (أ) موجود في repository.py فقط |
| 24 | `updateMatchProfile` | `hooks/social/useMatchSuggestions.ts` | TS2305 | مطابق للبند 19 | (أ) alias لـ `setupMatchProfile` |
| 25 | `getOccasions` | `hooks/social/useOccasions.ts` | TS2305 | يوجد فقط `getUpcomingOccasions(days_ahead)` (نافذة زمنية محدودة)؛ لا list عام غير مُقيّد (يشمل المناسبات الماضية) في أي طبقة | (ب) غير موجود إطلاقًا (queries مختلفة دلاليًا عن upcoming) |
| 26 | `deleteOccasion` | `hooks/social/useOccasions.ts` | TS2305 | لا يوجد حذف مناسبات في أي طبقة | (ب) غير موجود إطلاقًا |
| 27 | `getPages` | `hooks/social/usePages.ts` | TS2305 | نموذج `SocialPage` وschemas (`SocialPageCreate/Response`) موجودان في models.py/schemas.py، لكن صفر دوال repo/service/router | (ب) غير موجود إطلاقًا |
| 28 | `getPage` | `hooks/social/usePages.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 29 | `createPage` | `hooks/social/usePages.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 30 | `followPage` | `hooks/social/usePages.ts` | TS2305 | لا يوجد حتى جدول/علاقة متابعة صفحات (لا في models.py) | (ب) غير موجود إطلاقًا — يحتاج جدول جديد أيضًا |
| 31 | `unfollowPage` | `hooks/social/usePages.ts` | TS2305 | نفس أعلاه | (ب) غير موجود إطلاقًا |
| 32 | `getPost` | `hooks/social/usePosts.ts` | TS2305 | `SocialRepository.get_post(post_id)` موجودة (تُستخدم داخليًا في `like_post`/`share_post`)، لا service method عام ولا `GET /social/posts/{id}` | (أ) موجود في repository.py فقط |
| 33 | `getSubscriptionPlans` | `hooks/social/useSubscriptions.ts` | TS2305 | فقط `get_subscription_plan(id)` مفرد في repo؛ لا list في أي طبقة ولا GET endpoint | (ب) غير موجود إطلاقًا |
| 34 | `getGroupSubscription` | `hooks/social/useSubscriptions.ts` | TS2305 | `SocialRepository.get_active_subscription_for_group(group_id, tenant_id)` موجودة، غير مُعروضة عبر service.py/router.py | (أ) موجود في repository.py فقط |
| 35 | `cancelSubscription` | `hooks/social/useSubscriptions.ts` | TS2305 | لا يوجد إلغاء اشتراك في أي طبقة | (ب) غير موجود إطلاقًا |

**ملخص social:** 11 حالة (أ)، 24 حالة (ب). تقدير حجم بناء كل حالات (ب):
- **سطر واحد / وصلة بسيطة:** لا يوجد — كل حالات (ب) هنا تحتاج منطق state-transition أو list-query جديد على الأقل.
- **CRUD/service+router بسيط فوق جداول موجودة بالفعل:** Events (7,8,9,10,11) و Pages (27,28,29 — `followPage`/`unfollowPage` يحتاجان جدول جديد) — البيانات (models.py + schemas.py) جاهزة بالكامل لـ Events وPages، الناقص فقط طبقتا repository/service/router؛ هذا أخف الحالات لأن التصميم (schema) منتهي فعلاً.
- **migration بسيطة (عمود/جدول صغير):** `acceptConnection`/`rejectConnection` (تعديل status فقط، لا migration)، `deleteOccasion`، `cancelSubscription`، `leaveGroup`، `getGroupMembers` — منطق CRUD/state-transition فوق جداول موجودة، بلا حاجة migration.
- **تصميم schema جديد:** `getDigitalGifts`/`getPhysicalGifts` (list queries جديدة)، `getSubscriptionPlans` (list)، `getOccasions` (list عام)، `getGroups` (list) — تحتاج تصميم query/pagination جديد لكن فوق جداول موجودة.
- **جدول جديد كليًا:** `followPage`/`unfollowPage` فقط — لا يوجد أي تمثيل لعلاقة "متابعة صفحة" في models.py، يحتاج جدول جديد (مثل `PageFollower`) قبل أي منطق.
- **دومين كامل جديد:** لا يوجد — Events وPages أقرب لـ"دومين شبه جاهز البيانات، ناقص المنطق" وليس دومين جديد من الصفر.

## transport

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `useVehicles`, `useCreateVehicle`, `useDeleteVehicle`, `useAvailableVehicles` (hooks)، وداخليًا `getTrips`, `getTrip`, `createTrip`, `startTrip`, `completeTrip`, `cancelTrip`, `getMyTrips` (استيرادات) | `app/.../fleets/page.tsx`, `app/.../vehicles/page.tsx`, `app/.../trips/page.tsx`, و`hooks/transport/useVehicles.ts` نفسه (12 سطر خطأ) | TS2305 (متعددة) | **استثناء موثّق مسبقًا** — `hooks/transport/useVehicles.ts` محتواه الفعلي نسخة من كود hooks الرحلات (trips)، وليس كود مركبات؛ لا تحقيق إضافي هنا حسب الجلسة السابقة | استثناء موثّق — غير مصنّف (أ)/(ب) |
| 2 | `getVehicles` (تحقيق إضافي مطلوب — الحاجة الحقيقية وراء البند 1) | `fleets/page.tsx`, `vehicles/page.tsx` (عبر hook مركبات حقيقي غير موجود) | — | لا list عام لكل المركبات في أي طبقة؛ الموجود فقط `list_available_vehicles` (مُفلترة بـ`status=AVAILABLE`) — دلاليًا مختلفة | (ب) غير موجود إطلاقًا |
| 3 | `createVehicle` (الحاجة الحقيقية) | `vehicles/page.tsx` | — | **موجودة بالكامل**: `TransportService.createVehicle` + `POST /transport/vehicles` (مُوجّه في openapi.json) | (أ) الباك إند جاهز بالكامل؛ فقط ينقص hook فرونت إند صحيح يستدعيها |
| 4 | `deleteVehicle` (الحاجة الحقيقية) | `vehicles/page.tsx` | — | لا حذف مركبات في أي طبقة (repo/service/router) | (ب) غير موجود إطلاقًا |
| 5 | `getAvailableVehicles` (الحاجة الحقيقية) | `trips/page.tsx` | — | **موجودة بالكامل**: `TransportService.getAvailableVehicles` + `GET /transport/vehicles/available` | (أ) الباك إند جاهز بالكامل؛ فقط ينقص hook فرونت إند صحيح يستدعيها |
| 6 | `useCancelTrip` | `hooks/transport/useTrips.ts` (الملف الصحيح، غير ملف useVehicles.ts) | TS2305 | لا يوجد `cancel_trip` في repository.py/service.py/router.py إطلاقًا (فقط `cancel_booking`/`cancel_delivery` موجودتان كنمط مشابه) | (ب) غير موجود إطلاقًا |
| 7 | `useDrivers` (module) | `app/.../trips/page.tsx` | TS2307 وحدة غير موجودة | لا يوجد أي مفهوم "سائق" مستقل في الباك إند: `driver_id` في `Trip` هو مجرد FK لـ`users.id` بلا role/flag مخصص؛ لا في identity ولا في transport أي repo/service/router method لسرد السائقين؛ ولا حتى نوع `Driver` في `types/transport.ts` الفرونت إند | (ب) غير موجود إطلاقًا — أكبر فجوة في هذه المجموعة |
| 8 | `getBookings` | `hooks/transport/useBookings.ts` | TS2305 | `TransportRepository.list_bookings(tenant_id, passenger_id?, trip_id?)` موجودة وتدعم بالضبط نفس الفلاتر المطلوبة (trip_id/passenger_id)، لكن غير مُعروضة عبر service.py (الموجود `get_my_bookings` بفلتر passenger_id فقط) ولا عبر router | (أ) موجود في repository.py فقط |
| 9 | `cancelBooking` | `hooks/transport/useBookings.ts` | TS2305 | **موجودة بالكامل**: `repo.cancel_booking` + `service.cancel_booking` + `PATCH /transport/bookings/{booking_id}/cancel` (مُوجّه في router.py، لكن غائب عن services/transport.ts الفرونت إند) | (أ) الباك إند جاهز بالكامل؛ فقط ينقص استدعاء في services/transport.ts |
| 10 | `getDeliveries` | `hooks/transport/useDeliveries.ts` | TS2305 | لا list عام لمهام التوصيل في أي طبقة (فقط `get_delivery_task(id)` مفرد) | (ب) غير موجود إطلاقًا |
| 11 | `getMyDeliveries` | `hooks/transport/useDeliveries.ts` | TS2305 | لا يوجد "my deliveries" (مُفلتر بـ sender_id) في أي طبقة، رغم وجود نمط مطابق جاهز في `get_my_bookings`/`list_bookings` يمكن تقليده | (ب) غير موجود إطلاقًا |
| 12 | `assignDeliveryToTrip` | `hooks/transport/useDeliveries.ts` | TS2305 | `TransportRepository.assign_delivery_to_trip(task_id, tenant_id, trip_id)` موجودة، لا service method ولا router endpoint | (أ) موجود في repository.py فقط |
| 13 | `getFleets` | `hooks/transport/useFleets.ts` | TS2305 | فقط `get_fleet(id)` مفرد في repo؛ لا list method، ولا `GET /transport/fleets` (الموجود فقط POST) | (ب) غير موجود إطلاقًا |
| 14 | `updateFleet` | `hooks/transport/useFleets.ts` | TS2305 | لا تحديث أسطول في أي طبقة | (ب) غير موجود إطلاقًا |
| 15 | `deleteFleet` | `hooks/transport/useFleets.ts` | TS2305 | لا حذف أسطول في أي طبقة | (ب) غير موجود إطلاقًا |
| 16 | `getHubs` | `hooks/transport/useHubs.ts` | TS2305 | `TransportService.listHubs` تقوم بنفس العملية بالضبط (`GET /transport/hubs`، مدعومة بـ hub_type/skip/limit) | (أ) عبر إعادة تسمية/alias — نفس `listHubs` الموجودة في services/transport.ts |
| 17 | `updateHub` | `hooks/transport/useHubs.ts` | TS2305 | لا تحديث مركز نقل في أي طبقة | (ب) غير موجود إطلاقًا |
| 18 | `deleteHub` | `hooks/transport/useHubs.ts` | TS2305 | لا حذف مركز نقل في أي طبقة | (ب) غير موجود إطلاقًا |
| 19 | `getVehicleLocation` | `hooks/transport/useLiveTracking.ts` | TS2305 | لا `GET` مخصص لموقع مركبة في أي طبقة، لكن `repo.get_vehicle(vehicle_id, tenant_id)` يرجع الكائن كاملاً ويشمل عمود `current_location` (نفس العمود الذي يُحدَّثه `update_vehicle_location`) — البيانات موجودة، القراءة المخصصة غير مُعروضة | (أ) موجود جزئيًا في repository.py (`get_vehicle` يحمل `current_location`)، لا service method ولا router endpoint مخصص |
| 20 | `getRoutes` | `hooks/transport/useRoutes.ts` | TS2305 | فقط `get_route(id)` مفرد في repo؛ لا list method، ولا `GET /transport/routes` (الموجود فقط POST) | (ب) غير موجود إطلاقًا |
| 21 | `getRoute` | `hooks/transport/useRoutes.ts` | TS2305 | `TransportRepository.get_route(route_id, tenant_id)` موجودة، غير مُعروضة عبر service.py/router.py | (أ) موجود في repository.py فقط |
| 22 | `updateRoute` | `hooks/transport/useRoutes.ts` | TS2305 | لا تحديث مسار في أي طبقة | (ب) غير موجود إطلاقًا |
| 23 | `deleteRoute` | `hooks/transport/useRoutes.ts` | TS2305 | لا حذف مسار في أي طبقة | (ب) غير موجود إطلاقًا |
| 24 | `optimizeRoute` | `hooks/transport/useRoutes.ts` | TS2305 | يوجد استدعاء AI للتحسين مبني داخل `create_route` فقط (أثناء الإنشاء عبر `AIAgentsService`)، لا endpoint/method مستقل لتحسين مسار قائم أو معاينة بين hub بداية/نهاية بدون إنشاء فعلي | (ب) غير موجود إطلاقًا كعملية مستقلة (منطق AI الأساسي موجود لكنه مدمج داخل create_route فقط) |
| 25 | `getTransportStats` | `hooks/transport/useTransportStats.ts` | TS2305 | لا يوجد أي endpoint/service/repo لإحصائيات النقل في الدومين إطلاقًا | (ب) غير موجود إطلاقًا |
| 26 | `getTrip` | `hooks/transport/useTrips.ts` (الملف الصحيح) | TS2305 | `TransportService.get_trip(trip_id, tenant_id)` موجودة في service.py، لكن لا `GET /transport/trips/{trip_id}` في router.py | (أ) موجود في service.py فقط، ينقص router endpoint |

**ملخص transport:** 9 حالة (أ) (تشمل 2 من "الحاجة الحقيقية" خلف البند 1: createVehicle وgetAvailableVehicles)، 16 حالة (ب) (تشمل 2 من "الحاجة الحقيقية": getVehicles وdeleteVehicle)، + سطر استثناء واحد موثّق مسبقًا (يغطي 12 سطر خطأ tsc الأصلية) غير مصنّف. تقدير حجم بناء كل حالات (ب):
- **سطر واحد / وصلة فقط (frontend فقط، صفر تغيير باك إند):** لا يوجد ضمن (ب) — بحكم التعريف كل (ب) هنا غائبة عن الباك إند بالكامل.
- **service+router بسيطة فوق دوال repository/pattern موجود فعلاً (أخف حالات ب):** `getMyDeliveries` (يمكن تقليد `get_my_bookings` حرفيًا)، `deleteVehicle`/`updateFleet`/`deleteFleet`/`updateHub`/`deleteHub`/`updateRoute`/`deleteRoute` (نمط CRUD متكرر بسيط فوق نماذج SQLAlchemy موجودة، بلا migration).
- **query/pagination جديد فوق جداول موجودة:** `getDeliveries`، `getFleets`، `getRoutes`، `getVehicles` — list queries عامة جديدة.
- **منطق أعمق (state machine / تسوية مالية جزئية):** `useCancelTrip` (يحتاج مطابقة نمط `cancel_booking`/`cancel_delivery` بما يشمل إفراج hold_funds ومزامنة حالة المركبة)، `optimizeRoute` كعملية مستقلة عن `create_route`، `getTransportStats` (تجميع/aggregation عبر عدة جداول).
- **دومين كامل جديد (أكبر فجوة في المجموعتين):** `useDrivers` — لا يوجد أي تمثيل لمفهوم "سائق" في الباك إند إطلاقًا (لا role في identity، لا جدول مخصص في transport، لا نوع `Driver` حتى في types الفرونت إند) — يحتاج قرار تصميم (هل السائق دور User، أم كيان منفصل مرتبط بـ Fleet؟) قبل أي بناء.
