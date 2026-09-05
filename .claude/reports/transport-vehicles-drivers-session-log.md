# جلسة: transport-vehicles-drivers-feature-build

**السياق:** بند "قرار كبير" مؤجَّل من جلستَي `transport-domain-full-build`
(2026-09-01) و`category-b-decision-needed-triage` (2026-09-04). ميزة
المركبات والسائقين غائبة بالكامل من الفرونت إند رغم إن الباك إند جاهز
جزئيًا. **صفر تنفيذ حتى الآن — تحقيق + تصميم فقط.**

---

## 1. تأكيد حالة الباك إند (models.py + service.py + repository.py + router.py + schemas.py — اتقروا كاملين)

### Vehicle model (`transport/models.py:83-109`)
موجود وكامل: `id, tenant_id, fleet_id, smart_asset_id, license_plate (unique),
vehicle_type, capacity_kg, capacity_passengers, fuel_type, carbon_per_km,
status (VehicleStatus enum), current_location (JSONB), created_at, updated_at`.

### العمليات الموجودة فعليًا (service.py + repository.py)
| دالة service | دالة repository | Endpoint (router.py) |
|---|---|---|
| `create_vehicle` | `create_vehicle` | `POST /transport/vehicles` (superuser) |
| `update_vehicle_location` | `update_vehicle_location` | `PATCH /transport/vehicles/{id}/location` (superuser) |
| `get_available_vehicles` | `list_available_vehicles` (مفلترة `status==AVAILABLE`) | `GET /transport/vehicles/available` (active_user) |
| `get_vehicle` | `get_vehicle` | `GET /transport/vehicles/{id}` (active_user) |
| `create_fleet` | `create_fleet` | `POST /transport/fleets` (superuser) |

### فجوات مؤكَّدة في الباك إند (غير موجودة إطلاقًا — لا service ولا repository ولا router)
- **لا يوجد `list_vehicles` عام** — الوحيد المتاح `list_available_vehicles`
  (مفلترة `AVAILABLE` فقط)، فمفيش endpoint يجيب كل المركبات (بما فيها
  `IN_TRIP`/`MAINTENANCE`/`OUT_OF_SERVICE`) لصفحة إدارة.
- **لا `update_vehicle`** (تعديل بيانات غير الموقع — لوحة، سعة، نوع وقود..).
- **لا `delete_vehicle`**.
- **لا `list_fleets`**, **لا `update_fleet`**, **لا `delete_fleet`** — الأسطول
  نفسه فيه `create` بس بلا أي عملية قراءة/تعديل/حذف.

---

## 2. تأكيد حالة الفرونت إند (اتقرت الملفات فعليًا)

### `hooks/transport/useVehicles.ts` — نسخة طبق الأصل من `useTrips.ts`
الملف بعنوانه الداخلي `// hooks/transport/useTrips.ts` (تعليق الهيدر باقي من
النسخ)، ومحتواه بالكامل `useMyTrips/useTrip/useCreateTrip/useStartTrip/
useCompleteTrip` — صفر علاقة بالمركبات. **مؤكَّد حيًا الآن، مش مجرد نقل من
ذاكرة جلسة سابقة.**

### الملفات اللي بتستدعي hooks غير موجودة فعليًا (broken imports حية الآن، مش افتراضية)
- `app/(dashboard)/transport/vehicles/page.tsx` — يستورد
  `useVehicles, useCreateVehicle, useDeleteVehicle` من
  `hooks/transport/useVehicles` (اللي محتواه غلط زي فوق) + `Edit` بلا
  `useUpdateVehicle` مطلقًا (زرار تعديل بلا أي handler).
- `app/(dashboard)/transport/fleets/page.tsx` — نفس النمط: يستورد
  `useVehicles` من نفس الملف الغلط، ويستورد
  `useFleets, useCreateFleet, useDeleteFleet` من `hooks/transport/useFleets`.
- `app/(dashboard)/transport/trips/page.tsx` — يستورد
  `useAvailableVehicles` من `hooks/transport/useVehicles` (غير موجودة في
  الملف أصلًا) **و`useDrivers` من `hooks/transport/useDrivers` — الملف ده
  مش موجود إطلاقًا في الكودبيز** (`Glob hooks/transport/*.ts` أكَّد: 9 ملفات
  موجودة، `useDrivers.ts` مش من بينهم).

### 🆕 اكتشاف حي جديد أثناء هذه الجلسة — `useFleets.ts` نفسه معطوب (خارج نطاق السؤال الأصلي لكن لازم يتسجل)
`hooks/transport/useFleets.ts` (الملف اللي *موجود فعلًا وبمحتوى صحيح شكليًا*)
بيستورد `{ getFleets, updateFleet, deleteFleet }` كـ **named imports** من
`@/services/transport` — لكن `services/transport.ts` (اتقرا كامل، 545 سطر)
**بيصدّر `TransportService` object واحد بس، بلا أي named export اسمه
`getFleets`/`updateFleet`/`deleteFleet`**. نفس نمط الباج الميكانيكي الموثَّق
في `[[project_frontend_mechanical_fix_all_domains_pass1]]` لكن هنا الدالتين
التانيتين (`updateFleet`, `deleteFleet`) بيستدعوا endpoints مش موجودة
بالباك إند أصلًا (§1) — مش مجرد خطأ استيراد، الطبقة كلها ناقصة من الأساس
لحد service.py.

**خلاصة النطاق الفعلي المطلوب — أكبر من "vehicles + drivers" بس:**
1. `useVehicles.ts` — إعادة كتابة كاملة (list/create/delete/available +
   محتمل update لو اتقرر).
2. `useFleets.ts` — إصلاح الاستيراد (نمط `TransportService.xxx`) **+ بناء
   الطبقة الناقصة بالباك إند** (`list_fleets` على الأقل، `update`/`delete`
   لو اتقرر أنها مطلوبة فعليًا للـUI الحالي في `fleets/page.tsx`).
3. `useDrivers.ts` — غير موجود إطلاقًا، محتاج قرار تصميم (§3) قبل أي كتابة.
4. الباك إند: `list_vehicles` (عام)، وربما `update_vehicle`/`delete_vehicle`
   لو الـUI في `vehicles/page.tsx` (زرار تعديل موجود شكليًا بلا handler)
   هيتفعّل فعليًا.

---

## 3. قرار التصميم الأساسي: مفهوم "السائق" — مؤجَّل لحد قرار المستخدم

**الوضع الحالي بالباك إند (مؤكَّد):**
- `Trip.driver_id` = `ForeignKey("users.id")` مباشرة — **صفر جدول/موديل
  `Driver` منفصل في الكودبيز كله**.
- `identity/models.py` — `User.system_role` (enum `SystemRole`) **بلا أي
  قيمة `DRIVER`** (اتفحص `app/core/enums.py` عبر grep — مفيش تعريف
  `SystemRole` بمرادفات سائق).
- `create_trip` (service.py:213) بياخد `driver_id` كـ int عادي بلا أي
  تحقق إن اليوزر ده أصلًا "سائق" — أي `user_id` صالح بنفس التينانت يُقبل.
- الفحص الوحيد المرتبط بالسائق هو *ملكية* (`trip.driver_id == current_user.id`)
  في `start_trip`/`complete_trip`/`complete_delivery` — مفيش فحص *دور*.

**الخياران المطروحان للمستخدم (سؤال AskUserQuestion منفصل هيتبعت الآن):**
- **(أ) دور فوق User موجود** — إضافة `SystemRole.DRIVER` (أو حقل `is_driver`
  منفصل)، و`useDrivers()` تجيب `GET /identity/users?role=DRIVER` (أو
  endpoint مشابه بالـidentity domain).
- **(ب) كيان `Driver` منفصل** — جدول جديد (`license_number`, `rating`,
  `vehicle_type_certified`, ربط `user_id` FK) — هجرة DB جديدة + service/
  repository/router جدد بالكامل.

**رد المستخدم (بعد عرض الخيارين):** موافق على (أ) دور فوق User موجود، مش
كيان منفصل — بس بشرط: تحقق أول من `SystemRole` — لو كل قيمه أدوار حوكمة
منصة عالمية (مش أدوار تشغيلية محلية)، فاستخدامه لدور "سائق" مش مناسب. في
الحالة دي استخدم حقل منفصل (`is_driver: bool`)، أو حتى أبسط: استنتاج
"سائق" من كونه `driver_id` في أي Trip قائم بدون أي علم/دور صريح على
الإطلاق — قيّم الخيار الأبسط ده كمان. وسّع النطاق ليشمل `useFleets.ts`
(اتكتشف معطوب في نفس الفحص، نفس فئة الباج).

**تحقق إضافي نُفِّذ فورًا (مؤكَّد من الكود، مش افتراض):**
- `app/core/enums.py:16-21` — `SystemRole` = `USER, ADMIN, SUPER_ADMIN,
  EXECUTIVE_DIRECTOR, SYSTEM` فقط. **كله أدوار حوكمة منصة عالمية بالكامل،
  صفر دور تشغيلي محلي** — تأكيد: إضافة `DRIVER` هنا غلط، بيلوّث enum عالمي
  بمفهوم دومين واحد.
- `identity/router.py` (اتقرا كامل) — **صفر endpoint لسرد المستخدمين
  إطلاقًا** (بس `register/login/logout/refresh/register-with-invitation`).
  يعني أي مسار Driver (فلاج أو زيرو-فلاج) محتاج endpoint جديد بيسرد
  يوزرز — الفرق بينهم حجم النطاق بس، مش وجود الحاجة من عدمها.
- `identity/repository.py` (`UserRepository`, اتقرا كامل) — **صفر دالة
  `list` بالكامل** (بس `get_by_id` وتوابعها المفردة). يعني حتى مسار
  الزيرو-فلاج محتاج دالة repository جديدة واحدة كحد أدنى.

---

## 4. التصميم الكامل (اتعرض على المستخدم، بانتظار الموافقة النهائية)

### 4.1 Vehicles — إضافات باك إند
| الطبقة | الإضافة |
|---|---|
| `repository.py` | `list_vehicles(tenant_id, fleet_id=None, status=None, skip, limit)` |
| `repository.py` | `update_vehicle(vehicle_id, tenant_id, **fields)` |
| `repository.py` | `delete_vehicle(vehicle_id, tenant_id)` — hard delete، الحماية من حذف مركبة لها رحلات مجانًا من `Trip.vehicle_id` FK (`NOT NULL`) → `IntegrityError` تتلقّط وتترجم لـ`ValidationError`. صفر migration (مفيش `is_active` على `Vehicle`). |
| `service.py` | نظائر الثلاثة |
| `router.py` | `GET /transport/vehicles` (active_user)، `PATCH /transport/vehicles/{id}` (superuser)، `DELETE /transport/vehicles/{id}` (superuser) |
| `schemas.py` | `VehicleUpdate` (Optional كلها) |

### 4.2 Fleets — إضافات باك إند
| الطبقة | الإضافة |
|---|---|
| `repository.py` | `list_fleets(tenant_id, skip, limit)` — فلتر `is_active=True` افتراضيًا |
| `repository.py` | `update_fleet(fleet_id, tenant_id, name)` |
| `repository.py` | `delete_fleet(fleet_id, tenant_id)` — **soft delete** (`is_active=False`، العمود موجود بالفعل)، عكس Vehicle — لأن hard delete هيتصادم مع `Vehicle.fleet_id` FK (`NOT NULL`) لأي أسطول فيه مركبات. |
| `service.py` + `router.py` + `schemas.py` | نظائر مطابقة لنمط Vehicle |

### 4.3 Drivers — القرار المُوصى به: صفر flag، صفر migration
بما إن `create_trip` الحالية أصلًا بتقبل أي `user_id` بلا أي فحص دور،
أصدق تصميم هو عكس الواقع ده حرفيًا:
- **`GET /transport/drivers`** (endpoint جديد في transport domain، مش
  identity) — بيرجع كل المستخدمين النشطين (`is_active=True`) بنفس
  التينانت. يحتاج دالة واحدة جديدة: `UserRepository.list_active_by_tenant(
  tenant_id, skip, limit)`.
- صفر migration، صفر تعديل على `identity/models.py` أو `SystemRole`.
- **العيب الصادق:** لو التينانت كبير، الـdropdown هيسرد كل مستخدم نشط مش
  بس "السايقين الفعليين" — بس ده نفس حدود الباك إند الحالي بالظبط (مفيش
  تمييز أصلًا)، مش قيد جديد.
- **لو قلق فعليًا لاحقًا:** أضيف `is_driver: bool` على `User` كـfollow-up
  منفصل — قرار مؤجَّل بوعي.

**البديل المرفوض حاليًا (استنتاج من `driver_id` في Trip قائم بدون أي علم
صريح):** اتقيّم واتُرفض — مشكلة chicken-and-egg: مينفعش تختار سائق جديد
لرحلة جديدة لو "سائق" معرَّف بس بكونه ظهر في رحلة سابقة أصلًا. غير عملي
لأول رحلة لأي سائق.

**⏸️ قرار معلّق: انتظار رد المستخدم على مسار Drivers (زيرو-فلاج المقترح
فوق، ولا `is_driver` flag مع migration + endpoint toggle في identity).**

### 4.4 جدول الـEndpoints المفقودة (كلها جديدة)
`GET /transport/vehicles`, `PATCH /transport/vehicles/{id}`,
`DELETE /transport/vehicles/{id}`, `GET /transport/fleets`,
`PATCH /transport/fleets/{id}`, `DELETE /transport/fleets/{id}`,
`GET /transport/drivers`.

### 4.5 الفرونت إند
- `services/transport.ts`: 7 دوال جديدة على `TransportService` object —
  `listVehicles, updateVehicle, deleteVehicle, listFleets, updateFleet,
  deleteFleet, listDrivers`.
- `hooks/transport/useVehicles.ts`: إعادة كتابة كاملة (المحتوى الحالي نسخة
  من `useTrips.ts`، غلط بالكامل) — `useVehicles, useVehicle,
  useAvailableVehicles, useCreateVehicle, useUpdateVehicle,
  useDeleteVehicle, useUpdateVehicleLocation`.
- `hooks/transport/useFleets.ts`: إصلاح الاستيراد المعطوب
  (`getFleets/updateFleet/deleteFleet` كـnamed imports غير موجودة → نمط
  `TransportService.xxx` الصحيح، زي `useTrips.ts`).
- `hooks/transport/useDrivers.ts`: ملف جديد — `useDrivers()`.
- `types/transport.ts`: إضافة `VehicleUpdateFormData`, `Driver` (نوع بسيط
  `{id, name, email}`).
- زرار "تعديل" في `vehicles/page.tsx` — شكلي حاليًا بلا handler، هيتفعّل
  بـ`useUpdateVehicle`.

## 5. ترتيب التنفيذ المرحلي (اتعرض، بانتظار الموافقة)
| # | المرحلة | الحجم | يعتمد على |
|---|---|---|---|
| 1 | باك إند Vehicle (list/update/delete + schema + router) | صغيرة (4 ملفات) | — |
| 2 | باك إند Fleet (list/update/delete + schema + router) | صغيرة (4 ملفات) | — |
| 3 | باك إند Driver (`UserRepository.list_active_by_tenant` + service + router) | صغيرة-متوسطة (3 ملفات، يلمس identity repo) | قرار §4.3 |
| 4 | `services/transport.ts` — 7 دوال جديدة | صغيرة | 1-3 |
| 5 | `hooks/transport/useVehicles.ts` إعادة كتابة | صغيرة | 4 |
| 6 | `hooks/transport/useFleets.ts` إصلاح استيراد | صغيرة جدًا | 4 |
| 7 | `hooks/transport/useDrivers.ts` جديد | صغيرة جدًا | 4 |
| 8 | وصل زرار التعديل في `vehicles/page.tsx` | صغيرة جدًا | 5 |
| 9 | اختبار يدوي حقيقي بالمتصفح (`/transport/vehicles`, `/transport/fleets`, `/transport/trips`) | — | 1-8 |

**رد المستخدم:** موافقة كاملة على التصميم — زيرو-flag للـDrivers، hard
delete للـVehicle مع حماية FK، soft delete للـFleet، والترتيب المرحلي
كما هو. بدء التنفيذ بالترتيب 1→9.

---

## 6) التنفيذ — مراحل 1-3 (باك إند: Vehicle + Fleet + Driver) ✅ مكتملة ومُتحقَّقة حيًا

### ما اتنفَّذ
- `transport/repository.py`: `list_vehicles`, `update_vehicle`,
  `delete_vehicle` (hard delete)، `list_fleets`, `update_fleet`,
  `delete_fleet` (soft delete `is_active=False`).
- `transport/service.py`: نظائر الست دوال + `list_drivers` (يستخدم
  `self.user_repo` الموجود بالفعل بالـ`__init__`).
- `identity/repository.py`: `UserRepository.list_active_by_tenant` —
  دالة list وحيدة جديدة (كان `UserRepository` صفر دالة list قبل كده).
- `transport/schemas.py`: `VehicleUpdate`, `FleetUpdate`, `DriverResponse`.
- `transport/router.py`: 7 endpoints جديدة (`GET/PATCH/DELETE /vehicles`
  فرعياتها، `GET/PATCH/DELETE /fleets` فرعياتها، `GET /drivers`).

### تحقق حي (pytest ضد DB حقيقية) — `tests/test_transport_vehicles_fleets_drivers.py`
**النتيجة النهائية: 7/7 passed** (بعد 3 دورات تصحيح موثَّقة تحت):

| # | اختبار | يتحقق من |
|---|---|---|
| 1 | `test_list_vehicles_tenant_isolation_and_fleet_filter` | عزل tenant_id + فلتر fleet_id |
| 2 | `test_update_vehicle_sanitizes_and_isolates_tenant` | تعقيم bleach + NotFoundError عبر تينانت غلط |
| 3 | `test_delete_vehicle_success_when_no_trip_history` | حذف ناجح + NotFoundError على حذف مزدوج |
| 4 | `test_delete_vehicle_blocked_by_trip_history_fk` | **حماية FK فعلية** — `ValidationError` بدل حذف صامت |
| 5 | `test_list_fleets_tenant_isolation` | عزل tenant_id |
| 6 | `test_update_and_soft_delete_fleet` | soft delete فعلي (`is_active=False`، الصف باقٍ) + NotFoundError عبر تينانت غلط |
| 7 | `test_list_drivers_active_only_and_tenant_isolation` | فلتر `is_active=True` + عزل tenant_id |

### 🆕 اكتشافان حيّان أثناء التصحيح — مهمّان لأي عمل مستقبلي على هذا الدومين

**(أ) `saas_service_catalog` عندها صفر صف بـ`code='transport'` في بيئة
الديف الحالية بالكامل.** يعني `_check_saas_limits(tenant_id, "transport")`
— المستخدَمة في `list_hubs`, `create_vehicle`, `book_trip`, ودوالي
الجديدة (`list_vehicles`, `update_vehicle`, `list_fleets`, `update_fleet`,
`list_drivers`) — **بترجع `PermissionDeniedError` لأي تينانت، دايمًا،
حاليًا** — الدومين بالكامل معطَّل SaaS-wise في هذه البيئة، مش مشكلة في
منطق أي دالة. السبب: جلسة `transport-domain-full-build` زرعت صف مؤقت
لتحققها الحي، ونظَّفته بالكامل في نهايتها (§7.9 من تقرير تلك الجلسة) —
تنظيف متعمَّد، مش سهو، لكنه سايب البيئة في حالة "الدومين مقفول SaaS" لحد
دلوقتي. اختباراتي بتزرع نفس المنحة مؤقتًا (`_grant_transport_saas_access`
idempotent get-or-create) وتنضّفها بالكامل بعد كل test
(`_revoke_transport_saas_access`) — مؤكَّد صفر أثر باقٍ (`saas_service_
catalog/plans/subscriptions` = 0 بعد التشغيلة النهائية). **ده مش في نطاق
هذه الجلسة يتصلح دائمًا (قرار بيانات seed بيئة، مش كود) — موثَّق هنا
كتنبيه لأي جلسة قادمة تحاول تستخدم transport API فعليًا (حتى من المتصفح)
هتصطدم بنفس PermissionDeniedError لحد ما حد يزرع صف transport حقيقي غير
throwaway في `saas_service_catalog`.**

**(ب) قيد بيئة SQLAlchemy async + asyncpg + `pool_pre_ping=True` (موثَّق
مسبقًا في هذا الكودبيز — `tests/test_entity_membership_foundation.md`,
`tests/test_realestate_insurance_savepoint.py:263-268`، أعدت اكتشافه هنا
باستقلالية):** بعد `IntegrityError` حقيقي من `commit()` فاشل، أي كائن ORM
اتحمَّل قبل كده (`vehicle`, `trip`, ...) بيبقى expired، وأي وصول لاحق
لـ`.id` عليه — **حتى من جوّه session تانية تمامًا** — بيحاول lazy-reload
عبر الـsession الأصلية المكسورة فيفشل بـ`MissingGreenlet` (مش
`PendingRollbackError` المتوقعة). **الحل مش "استخدم session جديدة" —
الحل: انسخ `.id` لمتغير `int` عادي *قبل* أي محاولة متوقَّع فشلها.** كلفني
3 دورات تصحيح (مباشرة أدت لبقايا بيانات throwaway من التشغيلات الفاشلة —
اتنضَّفت بالكامل يدويًا بعدين، تفاصيل تحت).

### تنظيف بيانات throwaway (بعد كل التشغيلات، تحقق مستقل)
3 تشغيلات فاشلة من دورات التصحيح (قبل اكتشاف (ب) فوق) سابت بقايا: كل
فشل حصل *قبل* دخول `try/finally` (فشل إنشاء صف بتينانت=2 غير موجود قبل
إصلاح `OTHER_TENANT_ID`) أو *داخل* `finally` نفسها (نفس باج
`MissingGreenlet` كسر التنظيف كمان). تم اكتشاف البقايا بفحص مستقل بعد
التشغيلة النهائية الناجحة (7/7)، تحديد كل صف بدقة بالـid (مش بـLIKE
عريض — أول محاولة بـ`LIKE 'p_regtest%'` كادت تلمس مستخدم من دومين تاني
تمامًا `test_realestate_insurance_savepoint.py`، اتوقفت فورًا بفضل حماية
FK حقيقية `insurance_policies_created_by_fkey`، صفر بيانات لمسها فعليًا
لأن الـScript فشل قبل أي `commit()`)، وحُذفت بالضبط: 6 fleets، 5 vehicles،
6 hubs، 3 routes، 3 trips، 5 users. **تحقق مستقل نهائي: كل العدادات = 0.**

**الحالة: مراحل 1-3 مكتملة، مُتحقَّقة حيًا بالكامل. التالي: مرحلة 4
(`services/transport.ts`).**

---

## 7) التنفيذ — مراحل 4-8 (فرونت إند) ✅ مكتملة، `tsc` نظيف على كل الملفات المُعدَّلة

### مرحلة 4 — `services/transport.ts` + `src/lib/api-types.ts`
- 7 دوال جديدة على `TransportService`: `listVehicles, updateVehicle,
  deleteVehicle, listFleets, updateFleet, deleteFleet, listDrivers`
  (نفس نمط الدوال الموجودة بالضبط — axios + `handleError` + دعم
  `X-Tenant-ID`).
- `api-types.ts`: أُضيف يدويًا 3 أنواع (`VehicleUpdate`, `FleetUpdate`,
  `DriverResponse`) في قسم `components['schemas']` فقط — **قرار نطاق
  متعمَّد**: الملف مولَّد أصلًا بـ`openapi-typescript` (تأكَّد الشبكة
  متاحة فعليًا، `npx openapi-typescript@latest --version` نجح)، لكن إعادة
  توليده كاملًا كانت هتعيد كتابة 17000+ سطر وتُظهر كل انحراف تراكمي عبر
  34+ دومين (مؤكَّد وجود انحراف فعلي بالفعل: `VehicleCreate` المولَّدة
  الحالية ناقصة `fleet_id`/`smart_asset_id` الموجودين فعليًا في
  `schemas.py`) — خارج نطاق هذه الجلسة تمامًا. الإضافة اليدوية اقتصرت على
  الـ3 أنواع المُستهلَكة فعليًا من كود مكتوب يدويًا (لا حاجة لقسم
  `paths`/`operations` — مؤكَّد بالبحث إنه غير مُستخدَم من أي كود استهلاك
  في المشروع كله، فقط داخل `api-types.ts` نفسها).

### مرحلة 5 — `hooks/transport/useVehicles.ts`
إعادة كتابة كاملة (المحتوى القديم كان نسخة حرفية من `useTrips.ts`) —
`useVehicles, useVehicle, useAvailableVehicles, useCreateVehicle,
useUpdateVehicle, useDeleteVehicle, useUpdateVehicleLocation`، بنمط
`useFleets.ts`/`useTrips.ts` الصحيح (`TransportService.xxx` + React Query
invalidation).

### مرحلة 6 — `hooks/transport/useFleets.ts`
إصلاح استيراد معطوب فعليًا (`getFleets/updateFleet/deleteFleet` كـnamed
imports غير موجودة من `services/transport` — مؤكَّد بـ`tsc` قبل الإصلاح:
3 أخطاء `TS2305`) → نمط `TransportService.listFleets/updateFleet/
deleteFleet` الصحيح.

### مرحلة 7 — `hooks/transport/useDrivers.ts`
ملف جديد — `useDrivers(params)` يستدعي `TransportService.listDrivers`.

### مرحلة 8 — وصل زرار "تعديل" في `vehicles/page.tsx`
كان زرار شكلي بلا `onClick` إطلاقًا. أُضيف: `editingId` state،
`handleEdit(vehicle)` بيملأ `formData` من المركبة المختارة، `handleSubmit`
بيميّز إنشاء/تعديل حسب `editingId`، `closeForm` موحَّدة للإلغاء وبعد
النجاح، وعنوان/نص الزرار الديناميكي ("إضافة" ↔ "حفظ").

### تحقق `tsc --noEmit -p tsconfig.json` — قبل/بعد (المشروع كامل، 34+ دومين)
| | إجمالي الأخطاء بالمشروع |
|---|---|
| قبل مرحلة 4 (لقطة مرجعية فعلية، مش الأساس الموثَّق قديمًا 1253/1268 — الكودبيز اتغيَّر substantially منذ ذلك التاريخ) | 740 |
| بعد مراحل 4-8 كاملة | **733** (-7) |

**كل ملف لمسته هذه الجلسة (`services/transport.ts`, `api-types.ts`,
`useVehicles.ts`, `useFleets.ts`, `useDrivers.ts`,
`transport/vehicles/page.tsx`) — صفر أخطاء `tsc` فيه، مؤكَّد بالاسم
(`grep` على السجل الكامل، صفر تطابق).** بالإضافة لذلك، إصلاح `useFleets.ts`
صحَّح تلقائيًا خطأين implicit-`any` كانا موجودين في
`transport/vehicles/page.tsx` و`transport/fleets/page.tsx` (كانا بيستخدموا
`fleets?.map((f) => ...)` بلا نوع، لأن `useFleets` القديم كان معطوب).

**أثر جانبي على `transport/trips/page.tsx` (خارج نطاق هذه الجلسة، لم
يُلمَس):** كان عنده خطأ "Cannot find module '@/hooks/transport/useDrivers'"
— اختفى الآن (الملف بقى موجودًا)، لكن ده كشف باج حقيقي تاني تحته كان
مستخبي وراء "module not found": الصفحة بتحاول تقرأ `driver.name` بينما
`DriverResponse` (نوعي الجديد) بيعرض `username/email/name_ar/name_en` بس
(صفر حقل `name`). **مش في نطاق هذه الجلسة يتصلح** — الصفحة أصلًا معطوبة
بأخطاء تانية غير مرتبطة (`useCancelTrip` مفقودة من `useTrips.ts`،
`driver_name` غير موجود في `TripResponse`) موثَّقة كـbacklog منفصل. صافي
عدد الأخطاء بالملف نفسه فضل تقريبًا زي ما هو (خطأ implicit-any واحد اتبدل
بخطأ property-mismatch واحد أوضح) — صفر تراجع حقيقي بسبب شغلي.

---

## 8) مرحلة 9 — اختبار متصفح حي: **غير مُمكن فعليًا اليوم، تحقق منطقي مكافئ بديل**

### محاولة حقيقية أولاً (مش افتراض)
- شغَّلت الباك إند فعليًا (`uvicorn app.main:fastapi_app --port 8000`) —
  نجح، تأكَّد `LISTENING` عبر `netstat`.
- حاولت الاتصال بمتصفح Chrome فعليًا عبر أداة `claude-in-chrome`.
  **النتيجة: "Browser extension is not connected"** — قيد بيئة اليوم
  الفعلي (مش افتراضي)، تمامًا زي ما توقَّعت في طلبك.

### فجوة تحقق إضافية مكتشَفة (حتى لو المتصفح كان متاحًا)
حتى لو اتصل المتصفح فعليًا، أي تحميل حقيقي لـ`/transport/vehicles` أو
`/transport/fleets` في هذه البيئة **كان هيرجع 403 PermissionDeniedError
لكل الطلبات** — بسبب فجوة `saas_service_catalog` الموثَّقة في §6(أ) فوق
(صفر صف `code='transport'` في بيئة الديف الحالية، بعد ما جلسة
`transport-domain-full-build` نظَّفت صفها المؤقت). يعني حتى مع اتصال
متصفح ناجح، الـgolden path مكنش هيتفحص فعليًا اليوم بلا قرار زرع بيانات
SaaS دائم — قيد بيئي حقيقي ثانٍ، مش مرتبط بكود هذه الجلسة.

### التحقق المنطقي المكافئ المُنفَّذ بدلًا منه
1. **`tsc --noEmit` نظيف على كل الملفات المُعدَّلة** (§7) — يغطي: صحة
   الأنواع بين الـhooks والـservice layer والمكوّنات المستهلِكة، وتوافق
   البيانات المُرجَعة من `VehicleResponse/FleetResponse/DriverResponse`
   مع كل استخدام فعلي في `vehicles/page.tsx` و`fleets/page.tsx`.
2. **تتبّع تدفق البيانات يدويًا لكل صفحة مستهلِكة:**
   - `vehicles/page.tsx`: `useVehicles()` → `TransportService.listVehicles()`
     → `GET /transport/vehicles` → `service.list_vehicles` →
     `repo.list_vehicles` — **نفس المسار المُتحقَّق حيًا بـpytest test #1
     (§6)**، الفرق الوحيد غير المُتحقَّق هو طبقة HTTP نفسها (serialization/
     `X-Tenant-ID` header/`cast()` بالراوتر) — راوتر رقيق جدًا (سطر واحد
     تفويض)، خطر منخفض. نفس المنطق لـ`useCreateVehicle/useUpdateVehicle/
     useDeleteVehicle` مقابل pytest tests #2-4، و`useFleets` (تستهلكها
     نفس الصفحة لعرض الأسطول) مقابل pytest test #5.
   - `fleets/page.tsx`: `useFleets()` + `useVehicles()` (لعدّ مركبات كل
     أسطول) — نفس المسارات المُتحقَّقة، زائد pytest test #6
     (soft delete).
   - `trips/page.tsx`: `useAvailableVehicles` و`useDrivers` (الجزء
     المطلوب من هذه الجلسة تحديدًا) بيرجّعوا بيانات مطابقة الشكل
     لـ`VehicleResponse[]`/`DriverResponse[]` المُتحقَّقين — لكن الصفحة
     ككل *لسه معطوبة* ببواقي بترجع لباجات تانية خارج النطاق (فوق).
3. **فجوة التحقق المتبقية الموثَّقة بوضوح (زي نمط "فجوة render الحي"
   السابق):** **صفر تأكيد بصري فعلي إن الصفحات بترندر بلا كراش في
   متصفح حقيقي، وصفر تأكيد إن استجابة HTTP الفعلية (بعد `X-Tenant-ID`
   header + JSON serialization الحقيقي) مطابقة تمامًا لما اختبرته
   `service` مباشرة في pytest.** لازم يتفحص يدويًا في جلسة لاحقة لما
   يتوفر اتصال Chrome extension + قرار SaaS seed دائم للـtransport.

**الحالة: التنفيذ الكامل (مراحل 1-8) منتهٍ ومُتحقَّق منطقيًا/حيًا حسب
المتاح. مرحلة 9 موثَّقة كفجوة تحقق صريحة، مش ادّعاء نجاح لم يحصل.**
