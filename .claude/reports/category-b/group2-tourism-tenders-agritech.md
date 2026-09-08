# فئة (ب) — tourism-sports + tenders-auctions + agritech

ملاحظة منهجية: `eppne-backend/openapi.json` تاريخه 8 يوليو، وهو **قديم جدًا** مقارنة بحالة الكود الحالية (تعديلات حتى أواخر أغسطس) — بعض المسارات فيه (`/tenders/social/...`) لا تطابق حتى prefix الراوتر الحالي (`/tenders-auctions/...`). تم تجاهله كمرجع واعتماد قراءة `router.py`/`service.py`/`repository.py` مباشرة كمصدر الحقيقة.

اكتشاف جوهري لـ agritech: **لا يوجد ملف `router.py` إطلاقًا** في `app/domains/agritech/` (فقط `models.py`, `schemas.py`, `repository.py`, `service.py`)، و`app/main.py` الحالي **لا يستورد ولا يُسجّل** أي راوتر agritech (الاستيراد موجود فقط في `main.py.bak`، نسخة احتياطية غير مُفعّلة). يعني الدومين كامل غير موصول بأي HTTP endpoint حاليًا، بصرف النظر عن اكتمال `service.py`/`repository.py` الداخلي. هذا يجعل كل حالات (أ) في agritech أكبر من "أضف wrapper" العادية — تتطلب كتابة `router.py` من الصفر لكل نقاط الوصول + تسجيله في `main.py`.

---

## tourism-sports

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getDestinations` | `hooks/tourism-sports/useDestinations.ts` | TS2305 | **ليست فئة (ب) — alias**: نفس الوظيفة موجودة بالكامل تحت اسم `TourismSportsService.listDestinations` (router+service+repo كاملين، `GET /tourism-sports/destinations`) | أ (إعادة تسمية فقط) |
| 2 | `getDestination` (مفرد) | نفس الملف | TS2305 | لا يوجد أي getter لوجهة واحدة لا في `repository.py` ولا `service.py` ولا `router.py` (فقط `list_destinations` الجماعي) | ب |
| 3 | `getEvents` | `hooks/tourism-sports/useEvents.ts` | TS2305 | لا توجد دالة `list_events` في أي طبقة — فقط `create_event` | ب |
| 4 | `getEvent` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_event(event_id)` (مستخدمة داخليًا في `purchase_event_ticket`) — غير مكشوفة في `service.py` ولا `router.py` | أ (repository) |
| 5 | `purchaseTicket` | نفس الملف | TS2305 | **ليست فئة (ب) — alias**: نفس الوظيفة موجودة بالكامل تحت اسم `TourismSportsService.buyTicket` (`POST /tourism-sports/tickets/purchase`)، لكن التوقيع مختلف شكليًا (hook يتوقع `(data, idempotencyKey)` كوسيطين منفصلين وليس `headers` object) | أ (إعادة تسمية + تعديل توقيع بسيط) |
| 6 | `getMatches` | `hooks/tourism-sports/useMatches.ts` | TS2305 | لا توجد أي دالة قراءة لـ`SportsMatch` — فقط `create_match` في `repository.py`، ولا يوجد حتى `service.py` أو `router.py` لها | ب |
| 7 | `getMyTickets` | `hooks/tourism-sports/useMyTickets.ts` | TS2305 | لا يوجد أي getter/lister للتذاكر بحسب `owner_id`. حتى `get_ticket(id)` المُستدعاة من `service.py` (`self.repo.get_ticket(ticket_id)`) **غير مُعرَّفة فعليًا في `repository.py`** — استدعاء معطوب موجود بالفعل في الباك إند | ب |
| 8 | `getPlayers` | `hooks/tourism-sports/usePlayers.ts` | TS2305 | لا توجد دالة قائمة لاعبين بفلترة `club_id`/`sport_category` — فقط `get_player_profile(user_id)` و`get_player_profile_by_id(id)` | ب |
| 9 | `getPlayer` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_player_profile_by_id(profile_id)` جاهزة — غير مكشوفة في `service.py`/`router.py` | أ (repository) |
| 10 | `getPrograms` | `hooks/tourism-sports/usePrograms.ts` | TS2305 | لا توجد دالة قائمة برامج سياحية — فقط `create_program` و`get_program(id)` (مفرد داخلي) | ب |
| 11 | `getProgram` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_program(program_id)` جاهزة (مستخدمة داخليًا في `book_program`) — غير مكشوفة في `service.py`/`router.py` | أ (repository) |
| 12 | `getSportsOrganizations` | `hooks/tourism-sports/useSportsOrganizations.ts` | TS2305 | لا توجد دالة قائمة منظمات رياضية — فقط `create_sports_org` و`get_sports_org(id, tenant_id)` (مفرد) | ب |
| 13 | `getSportsOrg` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_sports_org(org_id, tenant_id)` جاهزة — غير مكشوفة في `service.py`/`router.py` | أ (repository) |
| 14 | `getTournaments` | `hooks/tourism-sports/useTournaments.ts` | TS2305 | لا توجد دالة قائمة بطولات — فقط `create_tournament` | ب |
| 15 | `getTournament` (مفرد) | نفس الملف | TS2305 | لا يوجد حتى getter مفرد لبطولة واحدة في أي طبقة — فقط `create_tournament` | ب |
| 16 | `getTransfers` | `hooks/tourism-sports/useTransfers.ts` | TS2305 | لا توجد دالة قائمة/مفردة لعمليات انتقال اللاعبين. حتى `get_transfer(id)` المُستدعاة من `service.py` (`self.repo.get_transfer(transfer_id)`) **غير مُعرَّفة فعليًا في `repository.py`** — استدعاء معطوب موجود بالفعل | ب |
| 17 | مكوّن `TransferCard` | `app/(dashboard)/tourism-sports/sports/transfers/page.tsx` | TS2307 (ملف مفقود) | لا يوجد ملف `components/tourism-sports/TransferCard.tsx` إطلاقًا. **والبيانات التي يحتاجها (`getTransfers`) هي نفسها حالة (ب) رقم 16 أعلاه** — إذن بناء هذا المكوّن ليس مجرد "غلاف UI"، بل يحتاج أولاً بناء endpoint القائمة كاملة في الباك إند | ب (مكوّن مفقود + بياناته غير موجودة بالكامل) |

**ملخص tourism-sports:** 4 حالة (أ) [`getEvent`, `getPlayer`, `getProgram`, `getSportsOrg` — كلها موجودة في `repository.py` فقط وتحتاج كشف عبر service+router]، 10 حالة (ب) حقيقية، + مكوّن UI واحد مفقود (`TransferCard`) بياناته أيضًا (ب). بالإضافة لحالتين "alias" لا تُحتسبان ضمن (ب) لأنهما إعادة تسمية بحتة لدوال موجودة فعليًا وموصولة بالكامل (`getDestinations`→`listDestinations`, `purchaseTicket`→`buyTicket`).
تقدير حجم بناء حالات (ب): معظمها **migration بسيطة على مستوى الكود فقط، بدون migration فعلية لقاعدة البيانات** (الجداول والأعمدة موجودة بالفعل في `models.py` — العمل هو كتابة استعلام `list_*`/`get_*` جديد في `repository.py` + كشفه في `service.py` + مسار `GET` جديد في `router.py`، على نفس نمط الدوال الموجودة). لا يوجد أي حالة تحتاج تصميم schema جديد أو دومين جديد بالكامل.

---

## tenders-auctions

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getAuctionBids` | `hooks/tenders-auctions/useAuctionBids.ts`, `useLiveBids.ts` | TS2305 | `repository.py` يحوي `get_live_bids_for_auction(auction_id, limit)` جاهزة (مستخدمة داخليًا في `place_bid`/`close_auction`) — غير مكشوفة في `service.py`/`router.py` | أ (repository) |
| 2 | `getAuctions` | `hooks/tenders-auctions/useAuctions.ts` | TS2305 | `repository.py` يحوي `list_auctions(tenant_id, status, asset_type, skip, limit)` جاهزة بالكامل — غير مكشوفة في `service.py`/`router.py` | أ (repository) |
| 3 | `getAuction` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_auction(auction_id)` جاهزة — غير مكشوفة | أ (repository) |
| 4 | `createAuction` | نفس الملف | TS2305 | **الـendpoint كامل وموصول فعليًا**: `router.py` يحوي `POST /tenders-auctions/auctions` → `service.create_auction` → `repo.create_auction`. الناقص فقط wrapper في `services/tenders-auctions.ts` | أ (router — endpoint كامل، ناقص واجهة أمامية فقط) |
| 5 | `startAuction` | نفس الملف، و`hooks/tenders-auctions/useStartAuction.ts` | TS2305 | لا توجد دالة نقل حالة مخصّصة (`DRAFT/SCHEDULED → OPEN`). الدعم الوحيد الموجود هو `repository.py: update_auction(auction_id, **kwargs)` العام (تحديث أي عمود بما فيه `status`) — بدون أي منطق تحقق خاص بالانتقال | أ (repository عام فقط — يحتاج service method جديدة تستخدم `update_auction`) |
| 6 | `getTenderBids` | `hooks/tenders-auctions/useBids.ts`, `useTenderBids.ts` | TS2305 | `repository.py` يحوي `list_bids_for_tender(tender_id, status)` جاهزة — غير مكشوفة | أ (repository) |
| 7 | `getMyBids` | `hooks/tenders-auctions/useBids.ts`, `useMyBids.ts` | TS2305 | لا يوجد أي استعلام "عطاءات المستخدم الحالي عبر كل المناقصات" — فقط `get_bid_by_tender_and_bidder(tender_id, bidder_id)` (يتطلب `tender_id` معروف مسبقًا) و`list_bids_for_tender(tender_id)` (بدون فلترة bidder). لا يوجد استعلام مكافئ لمزايدات المستخدم في المزادات (`LiveBid`) أيضًا | ب |
| 8 | `openTender` | `hooks/tenders-auctions/useOpenTender.ts`, `useTenders.ts` | TS2305 | لا توجد دالة نقل حالة مخصّصة (`DRAFT → PUBLISHED`). الدعم الوحيد هو `repository.py: update_tender(tender_id, **kwargs)` العام | أ (repository عام فقط — يحتاج service method جديدة) |
| 9 | `getTenders` | `hooks/tenders-auctions/useTenders.ts` | TS2305 | `repository.py` يحوي `list_tenders(tenant_id, status, project_id, skip, limit)` جاهزة بالكامل — غير مكشوفة | أ (repository) |
| 10 | `getTender` (مفرد) | نفس الملف | TS2305 | `repository.py` يحوي `get_tender(tender_id)` جاهزة — غير مكشوفة | أ (repository) |
| 11 | `updateTender` | `hooks/tenders-auctions/useTenders.ts`, `useUpdateTender.ts` | TS2305 | `repository.py` يحوي `update_tender(tender_id, **kwargs)` جاهزة بنفس الاسم تمامًا — غير مكشوفة في `service.py`/`router.py` | أ (repository) |

**ملخص tenders-auctions:** 10 حالة (أ) (معظمها موجود جاهزًا في `repository.py` بنفس التوقيع أو قريب منه، والراوتر نفسه موجود وله نمط واضح لإضافة مسارات `GET`)، حالة (ب) واحدة فقط (`getMyBids`).
تقدير حجم بناء `getMyBids`: **صغير** — استعلام جديد بسيط في `repository.py` (`SELECT ... WHERE bidder_id = :user_id`، ربما union بين `TenderBid` و`LiveBid`)، لا حاجة لعمود/جدول جديد ولا migration فعلية لقاعدة البيانات.

---

## agritech

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getBioCohorts` | `hooks/agritech/useBioAssets.ts` | TS2305 | لا توجد دالة قائمة (`list_bio_cohorts(zone_id)`) في أي طبقة — `repository.py` يحوي فقط `get_bio_cohort(id, tenant_id)` (مفرد) و`create_bio_cohort` و`update_bio_cohort_count` | ب |
| 2 | `createBioCohort` | نفس الملف | TS2305 | `service.py: add_bio_cohort(zone_id, user_id, data, idempotency_key)` منفّذة بالكامل (تحقق tenant + idempotency) — **لكن لا يوجد `router.py` إطلاقًا لهذا الدومين** | أ (service — لكن الدومين كله غير مُوصَّل بأي HTTP route، انظر الملاحظة أعلى الملف) |
| 3 | `getCropCycles` | `hooks/agritech/useCropCycles.ts` | TS2305 | `service.py: list_crop_cycles(zone_id)` منفّذة بالكامل | أ (service — بلا router) |
| 4 | `getFarms` | `hooks/agritech/useFarms.ts` | TS2305 | `service.py: list_farms(farm_type, skip, limit)` منفّذة بالكامل | أ (service — بلا router) |
| 5 | `getFarm` (مفرد) | نفس الملف | TS2305 | `service.py: get_farm(farm_id)` منفّذة بالكامل | أ (service — بلا router) |
| 6 | `updateFarm` | نفس الملف | TS2305 | لا توجد `update_farm` في `repository.py` ولا `service.py` إطلاقًا (رغم وجود عمود `is_deleted`/حقول قابلة للتحديث على `SmartFarm` في `models.py` تلمّح لنيّة دعمها لاحقًا) | ب |
| 7 | `deleteFarm` | نفس الملف | TS2305 | لا توجد `delete_farm`/soft-delete في `repository.py` ولا `service.py` إطلاقًا (نفس ملاحظة `is_deleted` أعلاه — العمود موجود، لكن لا توجد دالة تستخدمه للحذف) | ب |
| 8 | `getHarvests` | `hooks/agritech/useHarvests.ts` | TS2305 | لا توجد `list_harvests`/`get_harvests` في أي طبقة — `repository.py` يحوي فقط `create_harvest` (بدون حتى getter مفرد) | ب |
| 9 | `getWeatherAlerts` | `hooks/agritech/useSensors.ts` | TS2305 | **ليست فئة (ب) — alias**: نفس الوظيفة موجودة بالكامل تحت اسم `AgritechService.getActiveWeatherAlerts` في `services/agritech.ts`، ومطابقة لـ`service.py: get_weather_alerts()` → `repo.get_active_weather_alerts(tenant_id)` | أ (إعادة تسمية فقط — بلا router) |
| 10 | `getZones` | `hooks/agritech/useZones.ts` | TS2305 | `service.py: list_farm_zones(farm_id)` منفّذة بالكامل | أ (service — بلا router) |
| 11 | `createZone` | نفس الملف | TS2305 | `service.py: add_farm_zone(farm_id, user_id, data)` منفّذة بالكامل | أ (service — بلا router) |
| 12 | مكوّن `FarmCard` | `app/(dashboard)/agritech/farms/[id]/page.tsx`, `farms/page.tsx`, `page.tsx` | TS2307 (ملف مفقود) | لا يوجد `components/agritech/FarmCard.tsx`. بياناته (`SmartFarmResponse` عبر `getFarms`/`getFarm`) **موجودة بالكامل في الباك إند** (حالة أ رقم 3-4 أعلاه) — فقط تحتاج المكوّن نفسه + وصل الدومين بالراوتر | ب (مكوّن مفقود فقط، البيانات جاهزة) |
| 13 | مكوّن `FarmZoneCard` | `app/(dashboard)/agritech/farms/[id]/page.tsx` | TS2307 (ملف مفقود) | لا يوجد `components/agritech/FarmZoneCard.tsx`. بياناته (`FarmZoneResponse` عبر `getZones`) موجودة بالكامل (حالة أ رقم 10) | ب (مكوّن مفقود فقط، البيانات جاهزة) |
| 14 | مكوّن `WeatherAlertCard` | `app/(dashboard)/agritech/farms/[id]/page.tsx`, `page.tsx` | TS2307 (ملف مفقود) | لا يوجد `components/agritech/WeatherAlertCard.tsx`. بياناته (`WeatherAlertResponse` عبر `getActiveWeatherAlerts`) موجودة بالكامل (حالة أ رقم 9) | ب (مكوّن مفقود فقط، البيانات جاهزة) |
| 15 | هوك `useStats` (`useAgritechStats`) | `app/(dashboard)/agritech/page.tsx` | TS2307 (ملف مفقود) | لا يوجد ملف `hooks/agritech/useStats.ts`، ولا يوجد أي دالة تجميع/إحصائيات (`stats`/`aggregate`) في `service.py` أو `repository.py` إطلاقًا | ب (هوك مفقود، والقدرة الإحصائية نفسها غير موجودة في الباك إند) |

**ملخص agritech:** 7 حالة (أ) (`createBioCohort`, `getCropCycles`, `getFarms`, `getFarm`, `getWeatherAlerts`-alias, `getZones`, `createZone` — كلها منفّذة بالكامل في `service.py`)، 4 حالة (ب) حقيقية على مستوى المنطق (`getBioCohorts`, `updateFarm`, `deleteFarm`, `getHarvests`)، + 3 مكوّنات UI مفقودة (بياناتها جاهزة، فهي أقرب لـ"سطر واحد/غلاف بسيط" بمجرد وصل الدومين)، + هوك `useStats` مفقود وقدرته غير موجودة بالباك إند إطلاقًا (يحتاج دالة تجميع جديدة).

**تنبيه حاسم يخص كل حالات (أ) في agritech تحديدًا:** خلافًا لـ tourism-sports وtenders-auctions (اللي فيهم راوتر شغّال بالفعل وناقصهم مسارات GET فردية)، agritech **لا يملك `router.py` من الأساس** ولا تسجيل في `main.py`. حتى أبسط حالة (أ) هنا تتطلب: (1) كتابة `router.py` جديد بالكامل لكل الـ11 endpoint (create + list + get)، (2) استيراده وتسجيله في `main.py` بنفس نمط بقية الدومينات (`fastapi_app.include_router(agritech_router, prefix="/api", tags=[...])`)، ثم (3) فقط بعدها تصبح إضافة كل دالة كشف/wrapper منفردة "migration بسيطة" فعلاً.
