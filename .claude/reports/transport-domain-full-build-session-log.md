# جلسة: transport-domain-full-build

**بدأ:** 2026-09-01
**الحالة:** 🔵 مرحلة تحقيق + تصميم فقط — **صفر تنفيذ**. بانتظار قرارات المستخدم (§6).

---

## 0) تصحيح افتراض افتتاح الجلسة — مهم

السياق الافتتاحي افترض أن transport "معطَّل بنيويًا بالكامل — 16 endpoint موصوفين
لكن صفر جداول DB خلفهم"، بالاستناد لـ `batch3-audit-security-...md` (2026-08-25).
بعد قراءة الكود الفعلي الحالي (2026-09-01) تبيّن:

- **الكود الخلفي (`models.py`, `schemas.py`, `service.py`, `repository.py`,
  `router.py`) مكتمل فعليًا وجيد التصميم** — ليس مجرد "وصف بلا منطق".
- **ثغرات X-Tenant-ID IDOR الموصوفة في تدقيق batch3 (16 endpoint) تم إصلاحها
  بالفعل** — `git log` يؤكد commit `6b38d82`
  (`fix(logistics,manufacturing,tourism-sports,transport): close X-Tenant-ID
  header IDOR across 68 endpoints`). كل الراوتر الحالي يستخدم
  `cast(int, current_user.tenant_id)` بدل الهيدر.
- **الفجوة الحقيقية المتبقية من التدقيق القديم = فقط غياب الـmigration**
  (صفر `CREATE TABLE` لـ 7 جداول: `fleets`, `vehicles`, `transport_hubs`,
  `transport_routes`, `transport_trips`, `trip_bookings`, `delivery_tasks`).
  تأكيد إضافي هذه الجلسة: `find migrations/versions -iname "*transport*"
  -o -iname "*vehicle*" -o -iname "*fleet*"` = **صفر نتيجة**.

**لكن اكتُشفت فجوة أكبر وغير موثقة سابقًا بنفس الحدة:** الفرونت إند
(`hooks/transport/*.ts`) مبني على افتراض وجود سطح API أوسع بكثير من الـ16
endpoint الفعليين في `router.py`. راجع §2.

---

## 1) جرد الـ16 endpoint الموجودين فعليًا (router.py) — الغرض + منطق العمل

| # | Endpoint | current_user | الغرض + منطق ضمني |
|---|---|---|---|
| 1 | `POST /hubs` | superuser | إنشاء محطة، sanitize بـbleach |
| 2 | `GET /hubs` | active_user | قائمة محطات التينانت (فلتر `hub_type` اختياري) |
| 3 | `POST /fleets` | superuser | إنشاء أسطول |
| 4 | `POST /vehicles` | superuser | إضافة مركبة لأسطول |
| 5 | `PATCH /vehicles/{id}/location` | superuser | تحديث GPS حي (`current_location` JSONB) |
| 6 | `GET /vehicles/available` | active_user | مركبات `status=AVAILABLE`، فلتر `fleet_id` اختياري |
| 7 | `POST /routes` | superuser | إنشاء مسار + تحسين AI اختياري (`AIAgentsService`، فشل صامت بـ`try/except` عريض) |
| 8 | `POST /trips` | superuser | جدولة رحلة (route+vehicle+driver) |
| 9 | `PATCH /trips/{id}/start` | active_user | يتحقق `driver_id==current_user.id` + `vehicle.status==AVAILABLE`، يحوّل الحالة لـ`ONGOING` + المركبة لـ`IN_TRIP` |
| 10 | `PATCH /trips/{id}/complete` | active_user | نفس فحص `driver_id`، يحسب الكربون (`carbon_per_km × distance`)، يحوّل الحالة لـ`COMPLETED` + المركبة لـ`AVAILABLE` |
| 11 | `GET /trips/my` | active_user | رحلات السائق الحالي فقط |
| 12 | `POST /bookings` | active_user | حجز مقعد/شحن — **دفع فوري مباشر** عبر `finance.transfer` (راجع §4)، فاتورة، عمولة affiliate، إشعار |
| 13 | `GET /bookings/my` | active_user | حجوزات الراكب الحالي |
| 14 | `POST /deliveries` | active_user | إنشاء مهمة توصيل (بلا دفع في هذه الخطوة) |
| 15 | `POST /deliveries/{id}/pay` | active_user | دفع فوري مباشر لرسوم التوصيل (يتحقق `task.sender_id==payer_id`) |
| 16 | `POST /deliveries/{id}/complete` | active_user | إثبات تسليم (proof hash)، **صفر فحص ملكية إضافي بعد إصلاح X-Tenant-ID** (نقطة تحتاج مراجعة — أي `active_user` بنفس التينانت يقدر يُنهي أي توصيل، لأن الفحص الوحيد الآن هو تطابق التينانت، مش `sender_id`/`receiver_id`/`driver_id`) |

كل الـ16 محميين الآن بـ`cast(int, current_user.tenant_id)` — عزل التينانت سليم.
لا يزال **`complete_delivery` بلا فحص ملكية على مستوى المستخدم** (فقط تينانت) —
بند يستحق قرارًا صريحًا: هل نضيف فحص `sender_id`/`receiver_id`/`driver_id`؟

---

## 2) 🔴 الفجوة الحقيقية الأكبر — الفرونت إند يفترض ~23 endpoint إضافي غير موجودين

فحص شامل لكل `hooks/transport/*.ts` (`grep` على `from '@/services/transport'`)
أظهر أن الـhooks تستورد أسماء دوال (named exports) **غير موجودة إطلاقًا**
في `services/transport.ts` (اللي بيصدّر بس object واحد `TransportService`
بـ16 method مطابقين للـ16 endpoint). قائمة الدوال المفقودة بالكامل (باك إند
+ فرونت إند):

| المورد | الدوال المفقودة (لا backend endpoint ولا service.ts export) | يستخدمها |
|---|---|---|
| **Fleets** | `getFleets` (list)، `updateFleet`، `deleteFleet` | `useFleets.ts`, `hooks/useFleets.ts`(القديم), `fleets/page.tsx` |
| **Hubs** | `updateHub`، `deleteHub` (الـGET list موجود فعليًا كـ`listHubs` بس مش مُصدَّر باسم `getHubs`) | `useHubs.ts` |
| **Vehicles** | `getVehicles` (قائمة كل المركبات، مش بس المتاحة)، `getVehicle` (تفاصيل)، `deleteVehicle`، `getVehicleLocation` (تتبع حي، polling كل 3 ثواني) | `vehicles/page.tsx` (`useVehicles`, `useCreateVehicle`, `useDeleteVehicle`)، `useLiveTracking.ts` |
| **Routes** | `getRoutes` (list)، `getRoute` (تفاصيل)، `updateRoute`، `deleteRoute`، `optimizeRoute` | `useRoutes.ts` |
| **Trips** | `getTrips` (كل الرحلات، مش بس "رحلاتي")، `getTrip` (تفاصيل)، `cancelTrip` | `useTrips.ts` |
| **Bookings** | `getBookings` (كل الحجوزات — عرض إداري)، `cancelBooking` | `useBookings.ts` |
| **Deliveries** | `getDeliveries` (list)، `getMyDeliveries`، `assignDeliveryToTrip` | `useDeliveries.ts` |
| **Stats** | `getTransportStats` (`GET /transport/stats` — أرقام لوحة القيادة: `total_vehicles`, `available_vehicles`, `active_trips`, `total_deliveries`, `total_carbon_saved`, `total_hubs`, `total_routes`) | `useTransportStats.ts`, `TransportStatsCards.tsx` |

**هذا يعني:** بناء transport فعليًا يحتاج **~20 endpoint إضافي جديد** في
`router.py`/`service.py`/`repository.py` (list/detail/update/delete/cancel/
assign/optimize/stats/tracking) — مش بس migration للـ16 الموجودين. هذا
تغيير جوهري في حجم المهمة عن التقدير الافتتاحي.

**اكتشاف جانبي مؤكَّد أثناء نفس الفحص:** `hooks/transport/useVehicles.ts`
لسه فيه المحتوى الغلط الموثَّق سابقًا في `PROGRESS_LOG.md`
(`transport-vehicles-hook-file-wrong-content`) — تعليقه الأول
`// hooks/transport/useTrips.ts`، ومحتواه نسخة كاملة من hooks الرحلات
(`useTrips`, `getTrips`)، **صفر كود مركبات فيه**. لسه بلا لمس.

---

## 3) باقي البنود المكتشفة (تراكمية من PROGRESS_LOG + تحقق مباشر هذه الجلسة)

### 3.1 `transport-formdata-vs-openapi-schema-mismatch` (موثَّق سابقًا، مؤكَّد بقراءة الكود)
- `DeliveryTaskCreate.pickup_address`/`dropoff_address`: `Dict[str, Any]` (بلا Pydantic sub-model) → OpenAPI يولّد `Record<string, never>` غير قابل للاستخدام.
- الفرونت إند (`types/transport.ts`) **متوقّع فعليًا** الشكل الدقيق:
  `pickup_address: { address: string; lat: number; lng: number }`.
- `RouteCreate.waypoints: List[Dict[str, Any]]` نفس المشكلة — الفرونت متوقّع
  `Array<{ lat: number; lng: number; name?: string }>`.
- **حل مقترح (§5):** تعريف Pydantic sub-models حقيقية (`GeoAddress`,
  `Waypoint`) بدل `Dict[str, Any]` — يطابق تصميم الفرونت إند **الموجود
  بالفعل** بلا أي تغيير على `types/transport.ts`.

### 3.2 🆕 اكتشاف جديد هذه الجلسة — `DeliveryTaskCreate.sender_id` حقل زائد/مضلِّل
`schemas.py:114` يُعرِّف `sender_id: int` كحقل **مطلوب** في جسم الطلب. لكن
`service.create_delivery` بياخد `sender_id` كـ **معامل صريح من السيرفر**
(`current_user.id`، `router.py:193`) — و`data["sender_id"]` (من جسم
الطلب) **لا يُقرأ في أي مكان بالـservice** (تأكيد قراءة كاملة). الفرونت
إند (`DeliveryFormData`) **صح** — مش بيبعت `sender_id` أصلًا. الحقل في
الـschema ميت وخطر أمني كامن (لو حد استخدمه بالغلط مستقبلًا، ممكن يفتح
انتحال هوية مرسل). **الحل: حذف `sender_id` من `DeliveryTaskCreate`
بالكامل.**

### 3.3 🆕 اكتشاف جديد هذه الجلسة (تأكيد باج قديم لسه موجود) — `book_trip` idempotency retry مكسور
`service.py:315`:
```python
booking = await self.repo.get_booking(booking_id)
```
لكن `repository.py:180` تُعرِّف `get_booking(self, booking_id: int, tenant_id:
int)` — **وسيط `tenant_id` إجباري ناقص**. أي محاولة إعادة إرسال طلب حجز
بنفس `Idempotency-Key` (سيناريو شبكة بطيئة/retry حقيقي من العميل)
هترمي `TypeError` بدل إرجاع الحجز المخزَّن. **إصلاح بسيط: إضافة
`tenant_id` للاستدعاء.**

### 3.4 `trip.driver_name` / أنماط `*_name` غائبة من كل الـResponses
الفرونت إند (`types/transport.ts`) يتوقع حقول عرض جاهزة (`driver_name`,
`passenger_name`, `company_name`, `sender_name`, `receiver_name`) في
`Trip`, `TripBooking`, `DeliveryTask` — **لا واحد منها موجود في
`schemas.py` الحالي** (بس `*_id`). محتاج قرار: نضيف enrichment
(`selectinload` + حقل في الـResponse schema) وللا الفرونت إند يعمل
lookup منفصل لكل اسم مستخدم بمعرفه؟

### 3.5 `complete_delivery` — فحص ملكية غائب على مستوى المستخدم (راجع §1، بند 16)

---

## 4) نطاق الحجز المالي — الوضع الحالي + خيارات

**الوضع الحالي (كود فعلي، بلا حجز مسبق):**
- `book_trip`: يستدعي `finance.transfer()` **مباشرة** وقت تأكيد الحجز (داخل
  `begin_nested`)، ثم فاتورة بعد الـcommit. لا يوجد `hold_funds`.
- `pay_delivery`: نفس النمط — `finance.transfer()` مباشر وقت الدفع.

**نمط `hold_funds`/`settle_held_funds` موجود فعليًا في `finance/service.py`**
(`hold_funds:149`, `release_held_funds:212`, `settle_held_funds:272`)
ومُستخدَم في `tenders_auctions` (حجز عربون مزايدة قبل تحديد الفائز).

**لماذا يستحق transport نفس السؤال:**
- `book_trip`: الراكب يدفع **قبل** حصول الرحلة فعليًا. لا يوجد حاليًا أي
  `cancel_booking`/`cancel_trip` endpoint (لأنه مش موجود أصلًا — §2) —
  يعني لو رحلة اتلغت، **فلوس الراكب ضاعت بلا مسار استرداد** في التصميم
  الحالي. لو ضفنا `cancel_booking` (وهو مطلوب فرونت إند أصلًا)، لازم يبقى
  عنده منطق استرداد — إما `finance.transfer` عكسي يدوي، أو (أنظف) `hold_funds`
  وقت الحجز + `settle_held_funds` وقت `complete_trip` + `release_held_funds`
  وقت `cancel`.
- `pay_delivery`: نفس المنطق — الدفع بيحصل قبل `complete_delivery` (إثبات
  تسليم فعلي). لو التوصيل فشل بعد الدفع، بلا `hold`، مفيش استرداد.

**الخيارات للقرار (§6):**
- **أ) حجز فعلي (`hold_funds` → `settle_held_funds`/`release_held_funds`)**
  — أنسب معماريًا، يتطابق مع نمط `tenders_auctions`، لكن يزيد نطاق العمل
  (لازم `cancel_booking`/`cancel_delivery` يبقوا جزء من هذه المرحلة مش
  مؤجَّلين).
- **ب) دفع مباشر زي دلوقتي + إضافة استرداد يدوي صريح فقط عند الإلغاء**
  (`finance.transfer` عكسي بمبلغ الإلغاء) — أبسط، أقل تغيير، لكن يفتح نافذة
  عدم اتساق لو الإلغاء فشل نص الطريق (بلا `begin_nested` كافي).
- **ج) إبقاء الدفع المباشر كما هو تمامًا، وتأجيل أي منطق استرداد/إلغاء
  لجلسة لاحقة منفصلة** (لو الأولوية دلوقتي هي بس "خلي الـ16 endpoint
  الموجودين يشتغلوا فعليًا على DB حقيقية").

---

## 5) تصميم الجداول (models.py الحالي — يُعتمَد كما هو، بلا تغيير بنيوي)

الجداول السبعة موجودة بالفعل في `models.py` بتصميم سليم (`tenant_id` FK
+ index على كل جدول، enums نظيفة `TransportType`/`TripCategory`/
`TripStatus`/`VehicleStatus`، `idempotency_key` unique partial index على
`trip_bookings`/`delivery_tasks`، `CheckConstraint` على `TripBooking`
لضمان `passenger_id XOR company_id`). **لا حاجة لإعادة تصميمه من الصفر
كما افترضت مذكرة الافتتاح — فقط:**

1. **Migration واحد جديد** (`alembic revision`) يُنشئ الـ7 جداول بالضبط
   كما هي مُعرَّفة في `models.py` حاليًا (`transport_hubs`, `fleets`,
   `vehicles`, `transport_routes`, `transport_trips`, `trip_bookings`,
   `delivery_tasks`) — ترتيب FK: `transport_hubs` → `fleets` → `vehicles`
   → `transport_routes` (يعتمد على hubs) → `transport_trips` (يعتمد على
   routes+vehicles+users) → `trip_bookings`/`delivery_tasks` (تعتمد على
   trips+users).
2. **تعديلان صغيران على `schemas.py` فقط** (بلا تغيير DB): `GeoAddress`/
   `Waypoint` sub-models (§3.1) + حذف `sender_id` الميت (§3.2).
3. **صفر تغيير على `models.py`** إلا لو القرار في §4 كان "أ" (حجز مالي) —
   عندها `TripBooking`/`DeliveryTask` محتاجين حقل إضافي (`held_transaction_id`
   أو مشابه) لتتبع الحجز، بنفس نمط `tenders_auctions`.

---

## 6) القرارات المطلوبة منك قبل أي تنفيذ

1. **نطاق هذه الجلسة:** نبني بس الـ16 endpoint الموجودين (migration +
   إصلاح البنود 3.1-3.3 + الفرونت إند المطابق لهم فقط)، وللا نلتزم بالبناء
   الكامل (~20 endpoint إضافي + إعادة كتابة `services/transport.ts` بالكامل
   + `useVehicles.ts` من الصفر) في نفس الملحمة (على مراحل)؟
2. **نموذج الحجز المالي (§4):** أ (حجز فعلي `hold_funds`) / ب (دفع مباشر +
   استرداد يدوي) / ج (تأجيل الإلغاء/الاسترداد بالكامل لجلسة لاحقة)؟
3. **`complete_delivery` (§1 بند 16):** نضيف فحص ملكية مستخدم (`sender_id`/
   `receiver_id`/`driver_id`) الآن، وللا نتركه كما هو (تينانت فقط) ونوثّقه
   backlog؟
4. **`*_name` enrichment (§3.4):** نضيف الحقول دلوقتي (يحتاج `selectinload`
   + تعديل schemas)، وللا نتركها للفرونت إند يعمل lookup منفصل؟

**صفر تنفيذ حتى تُجاب هذه الأربعة.**

---

## 7) ✅ التنفيذ الكامل — [2026-09-01، نفس الجلسة، بعد موافقة صريحة]

**القرارات المعتمَدة:** (1) نطاق هذه الجلسة = الـ16 endpoint الموجودين فقط
+ الـ~23 المؤجَّلة → backlog (راجع §8). (2) الحجز المالي: الخيار أ
(`hold_funds`/`settle_held_funds`/`release_held_funds`، نفس نمط
`tenders_auctions`) — يشمل بناء `cancel_booking`/`cancel_delivery` كجزء
من هذه المرحلة (استثناء مبرَّر عن التأجيل، ضروري لإكمال دورة الحجز
بأمان). (3) فحص ملكية `complete_delivery` يُضاف الآن. (4) `*_name`
enrichment → backlog، بلا تنفيذ.

### 7.1 Migration — `044_create_transport_tables.py`
7 جداول (`transport_hubs`, `fleets`, `vehicles`, `transport_routes`,
`transport_trips`, `trip_bookings`, `delivery_tasks`) مطابقة تمامًا
لـ`models.py` الحالي (بلا أي تغيير بنيوي). **تحقق حي:** `alembic upgrade
head` نجح، `pg_tables`/`information_schema.columns`/`pg_indexes` أكَّدوا
الجداول والأعمدة والفهارس (بما فيها الفهرس الفريد الجزئي المزدوج على
`idempotency_key`) مطابقة 1:1 لتعريف SQLAlchemy — تصحيح ذاتي أثناء
الكتابة: أول مسودة أضافت `UniqueConstraint` منفصل زيادة عن index
`unique=True` (كان هيولّد قيد DB إضافي غير موجود في تعريف الموديل) —
اتصحّح قبل التطبيق.

### 7.2 إصلاحات `schemas.py` (§3.1, §3.2)
- `GeoAddress` (`address`, `lat`, `lng`) sub-model حقيقي بدل
  `Dict[str, Any]` لـ`DeliveryTaskCreate.pickup_address`/`dropoff_address`.
- `Waypoint` (`lat`, `lng`, `name?`) sub-model حقيقي بدل
  `List[Dict[str, Any]]` لـ`RouteCreate.waypoints`.
- حذف `DeliveryTaskCreate.sender_id` الميت (كان مطلوبًا في الـschema بلا
  أي استخدام فعلي في `service.create_delivery`).

### 7.3 إصلاح باج idempotency retry (§3.3)
`service.py` — `book_trip`: `self.repo.get_booking(booking_id)` →
`self.repo.get_booking(booking_id, tenant_id)`.

### 7.4 🆕 اكتشاف حي جديد أثناء التحقق — باج "طمس نجاح الحجز" في
`book_trip`/`pay_delivery`
عند فشل `invoicing.create_invoice()` (باج معروف مسبقًا
`invoicing-generate-invoice-number-count-based-collision`، خارج النطاق)،
كود `except Exception as e: logger.error(f"...{booking.id}...")` كان
بيحاول يقرأ صفة ORM بعد ما الجلسة احتاجت `rollback()` — بيفشل بخطأ ثانٍ
(`PendingRollbackError` ثم `MissingGreenlet` بعد أول محاولة إصلاح) يطمس
نجاح الحجز/الدفع الفعلي ويرجّع 500 للعميل رغم أن العملية المالية اتمت
فعلًا. **الإصلاح:** `await self.db.rollback()` + `await
self.db.refresh(booking/task)` قبل أي وصول لاحق للكائن. مؤكَّد حيًا
(محاكاة الباج المعروف فعليًا، رأينا الرسالة تُسجَّل بنظافة بمعرف صحيح
بدل الكراش المزدوج).

### 7.5 🆕 اكتشاف حي جديد — علاقات ORM مفقودة (`Trip.vehicle/driver/route`,
`TripBooking.trip`)
`repository.py` كانت تستخدم `selectinload(Trip.vehicle)` إلخ في
`list_trips`/`list_bookings` (المستخدَمة فعليًا بواسطة `GET /trips/my` و
`GET /bookings/my` — من ضمن الـ16 endpoint الأصليين) — لكن `models.py`
ما كانش فيه أي `relationship()` معرَّف إطلاقًا، فقط أعمدة FK خام. كود
ميت من الأساس (الدومين كان معطَّل بنيويًا) — **أول تنفيذ حقيقي في تاريخ
المشروع** لهذا المسار (عبر منطق التسوية الجديد `complete_trip`) كشفه
بـ`AttributeError: type object 'TripBooking' has no attribute 'trip'`.
**الإصلاح:** إضافة 4 `relationship()` (`Trip.vehicle`, `Trip.driver`,
`Trip.route`, `TripBooking.trip`) — تغيير ORM بحت، صفر عمود/migration
جديد. مؤكَّد حيًا (استيراد نظيف + `list_bookings` تشتغل فعليًا في تسوية
الرحلة).

### 7.6 تكامل `hold_funds`/`settle_held_funds`/`release_held_funds`
- `book_trip`: `finance.transfer()` → `finance.hold_funds()` (الأجرة
  تتجمّد وقت الحجز، مش تتحول فورًا).
- `complete_trip`: بعد تحديث حالة الرحلة، تسوية (`settle_held_funds`)
  لكل حجز `CONFIRMED` على الرحلة (حجوزات `company_id` تتخطى — خارج
  النطاق). **🆕 اكتشاف حي أثناء التحقق:** `settle_held_funds()` بتعمل
  `begin_nested()` (savepoint) بس من جوّه، بلا `commit()` صريح — تسوية
  ناجحة منطقيًا كانت بترجع (rollback) صامتة تمامًا لما جلسة الطلب تتقفل
  بلا أي استثناء (مؤكَّد حيًا: `held_balances` فضلت زي ما هي رغم نجاح
  الاستدعاء). **الإصلاح:** `await self.db.commit()` صريح بعد حلقة
  التسوية.
- `pay_delivery`: `finance.transfer()` → `finance.hold_funds()`.
- `complete_delivery`: فحص ملكية (`trip.driver_id == driver_id`، §7.7)
  + تسوية (`settle_held_funds`) لو الرسوم كانت محجوزة أصلًا. (commit
  آمن هنا — `repo.complete_delivery()` التالية بتعمل commit شامل).
- `cancel_booking` (جديد، `PATCH /bookings/{id}/cancel`): فحص ملكية
  (`passenger_id`) + فحص حالة (`CONFIRMED` فقط) + فحص `trip.status ==
  SCHEDULED` + `release_held_funds` + تحديث الحالة لـ`CANCELLED`. (commit
  آمن — `repo.cancel_booking()` بتعمل commit شامل).
- `cancel_delivery` (جديد، `POST /deliveries/{id}/cancel`): فحص ملكية
  (`sender_id`) + فحص حالة (مش `DELIVERED`/`CANCELLED`) + `release_held_funds`
  لو مدفوعة + تحديث الحالة.

### 7.7 فحص ملكية `complete_delivery`
أضيف معامل `driver_id` (من `current_user.id` في الراوتر) — لازم يطابق
`trip.driver_id` للرحلة المرتبطة بالتوصيل، وإلا `PermissionDeniedError`.
كان قبل كده بلا أي فحص مستخدم (تينانت بس).

### 7.8 راوتر — endpoint جديدين
`POST /transport/deliveries/{task_id}/cancel`،
`PATCH /transport/bookings/{booking_id}/cancel`. إجمالي endpoints الدومين
دلوقتي: **18** (16 أصليين + 2 جديدين، الباقي ~21 من الـ23 المؤجَّلة —
راجع §8 لملاحظة العدد الدقيق).

### 7.9 التحقق الحي الكامل — ملخص النتائج
سكريبتات مباشرة (Python + `AsyncSessionLocal` حقيقية، جلسة منفصلة لكل
خطوة تحاكي دورة حياة طلب HTTP حقيقي، بيانات throwaway + تنظيف كامل مؤكَّد
بـSELECT مستقل بعد كل تشغيلة، بنفس منهجية جلسات التدقيق السابقة):

| # | الاختبار | النتيجة |
|---|---|---|
| A | `book_trip` يحجز (بدل تحويل مباشر) | ✅ `balances -20`, `held_balances +20` بدقة |
| B | `complete_trip` يسوّي كل الحجوزات المؤكَّدة | ✅ السائق استلم الأجرة فعليًا، `held_balances` رجعت صفر |
| C1 | `cancel_booking` فحص ملكية | ✅ سائق (مش الراكب) اتمنع من الإلغاء |
| C2 | `cancel_booking` يحرر الحجز | ✅ الأجرة رجعت لـ`balances`، `held_balances` صفر |
| C3 | إلغاء مزدوج | ✅ اتمنع (`ValueError`) |
| D1 | `complete_delivery` فحص ملكية | ✅ المُرسِل (مش السائق) اتمنع من الإنهاء |
| D2 | `complete_delivery` يسوّي الرسوم | ✅ السائق استلم 3 MR_USDT، `held_balances` صفر |
| — | عزل تينانت (`get_trip` عبر تينانت16) | ✅ `None` |
| — | إعادة إرسال idempotency (بعد إصلاح §7.3) | ✅ يرجّع الحجز المخزَّن بنظافة، صفر `TypeError` |

**تنظيف نهائي مؤكَّد مستقل:** صفر صفوف throwaway متبقية (كل الجداول
السبعة + `saas_service_catalog`)، محفظتا الراكب/السائق (772/773، تينانت1)
اتأكَّد رجوعهم بالضبط للقيم الأصلية (`{}`/`{}` وMR_USDT=905 على التوالي).

### 7.10 بنود جانبية مكتشَفة، **بلا لمس** (خارج نطاق موافَق عليه)
- `invoicing-generate-invoice-number-count-based-collision` — لسه موجود
  وبيتفعّل بانتظام مع تينانت1 (`INV-1-000015`)، موثَّق مسبقًا خارج النطاق.
- `AI Governance check failed` — `agent_id=3` غير موجود في `ai_agents`
  (بيانات seed ناقصة في هذه البيئة). مُعالَج بأمان بواسطة `try/except`
  الموجود أصلًا في `_check_ai_governance`.
- `Affiliate registration failed: 'User' object has no attribute
  'referred_by'` — باج موثَّق مسبقًا (`identity-user-referred-by-field-missing`)،
  مُعالَج بأمان بواسطة `try/except` الموجود أصلًا.
- Celery/Redis backend في بيئة الديف المحلية مُعدَّل على منفذ `6379`
  بينما الـredis الفعلي شغّال على `6380` — كل استدعاء `_send_notification`
  بياخد ~65 ثانية retry قبل ما يفشل بأمان (مُعالَج بـ`try/except` أصلًا،
  بلا أي أثر على العملية الأساسية). أبطأ التحقق الحي بشكل ملحوظ، بلا أي
  تأثير وظيفي. مش في نطاق هذه الجلسة (إعداد بيئة محلية بحت).

**صفر تعديل على أي frontend file هذه الجلسة** — النطاق كان backend بالكامل
حسب الموافقة الصريحة.

---

## 8) Backlog — الـ~23 endpoint المؤجَّلة (مفصَّلة في `PROGRESS_LOG.md`)

راجع `PROGRESS_LOG.md` (بند `transport-frontend-assumed-api-surface-backlog`)
للتفاصيل الكاملة — جدول موزَّع حسب المورد (Fleets/Hubs/Vehicles/Routes/
Trips/Bookings/Deliveries/Stats) بأسماء الدوال المفقودة بالضبط والملفات
المستهلِكة.
