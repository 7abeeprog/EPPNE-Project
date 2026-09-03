# تقرير جلسة agritech-full-domain-build — بناء router.py من الصفر لدومين agritech

**بدأ التسجيل:** 2026-09-04
**الحالة العامة وقت بدء التسجيل:** صفر تنفيذ. مرحلة تحقيق + تصميم فقط قبل أي كتابة كود، بناءً على طلب صريح.

---

## خلفية القرار (من ملف التسليم + جلسة التصنيف 2026-08-29 + جلسة frontend-category-b-phase1 2026-08-01/02)

- `agritech` مصنَّف "معطَّل عمدًا، صفر router" — `router.py` القديم كان نسخة مكررة بالغلط من `ai_governance/router.py`، اتشال عمدًا في commit `9e01ede`.
- الكود الحقيقي (`service.py` + `models.py` + `repository.py` + `schemas.py`) موجود وسليم بنيويًا، لكنه orphaned بالكامل: صفر نقطة استدعاء HTTP، و`tasks/agritech.py` عنده استدعاءات مكسورة لدوال repository غير متطابقة التوقيع.
- **القرار المعتمد الآن:** تصميم `router.py` جديد بالكامل (مش استرجاع القديم) + تسجيله في `main.py`.

---

## 1. جرد فعلي لدوال service.py (671 سطر) — بتاريخ اليوم

تم قراءة `service.py` + `repository.py` + `models.py` + `schemas.py` كاملة بالفعل (لم تتغيّر جوهريًا عن التحقيق القديم). كل الدوال العامة (غير `_prefixed`) قابلة لتكون endpoint:

| # | المورد | الدالة | الوصف |
|---|---|---|---|
| 1 | Farms | `create_farm(user_id, data)` | إنشاء مزرعة |
| 2 | Farms | `list_farms(farm_type?, skip, limit)` | قائمة مزارع (paginated dict) |
| 3 | Farms | `get_farm(farm_id)` | مزرعة واحدة |
| 4 | Zones | `add_farm_zone(farm_id, user_id, data)` | إضافة منطقة لمزرعة |
| 5 | Zones | `list_farm_zones(farm_id)` | قائمة مناطق مزرعة (paginated dict) |
| 6 | Crop Cycles | `start_crop_cycle(zone_id, user_id, data, idempotency_key)` | بدء دورة زراعية (idempotent) |
| 7 | Crop Cycles | `list_crop_cycles(zone_id)` | قائمة دورات منطقة (paginated dict) |
| 8 | Harvest | `register_harvest(user_id, data, idempotency_key)` | تسجيل حصاد (idempotent، commit صريح) |
| 9 | Bio Assets | `add_bio_cohort(zone_id, user_id, data, idempotency_key)` | إضافة مجموعة حيوانية (idempotent) |
| 10 | Bio Assets | `register_bio_yield(user_id, yield_data, idempotency_key)` | تسجيل إنتاج حيواني (idempotent) |
| 11 | Traceability | `add_traceability_stage(user_id, data)` | إضافة مرحلة تتبع |
| 12 | Traceability | `get_traceability_stages(traceable_type, traceable_id)` | قائمة مراحل تتبع (paginated dict) |
| 13 | Traceability | `generate_traceability_qr(traceable_type, traceable_id, user_id)` | توليد QR (يتطلب مكتبة `qrcode` مثبتة) |
| 14 | Certificates | `issue_certificate(user_id, data)` | إصدار شهادة |
| 15 | Certificates | `get_entity_certificates(entity_type, entity_id)` | شهادات كيان (paginated dict) |
| 16 | Sensors | `record_soil_data(user_id, data)` | تسجيل قراءة تربة |
| 17 | Sensors | `get_recent_soil_readings(zone_id, limit)` | آخر قراءات تربة (paginated dict) |
| 18 | Weather | `create_weather_alert(user_id, data)` | إنشاء تنبيه طقس |
| 19 | Weather | `get_weather_alerts()` | التنبيهات النشطة (List مباشرة، **مش** dict) |

**ملاحظة تصميم مهمة:** كل دوال `list_*`/`get_*_stages`/`get_entity_certificates`/`get_recent_soil_readings` بترجّع `{"items", "total", "skip", "limit"}` — ما عدا `get_weather_alerts()` اللي بترجّع `List[WeatherAlert]` مباشرة.

---

## 2. فحص أمني: tenant_id scoping في service.py + repository.py

**النتيجة العامة: التصفية سليمة على مسار القراءة** — كل دالة list/get في repository.py بتفلتر بـ`tenant_id` صراحةً (مباشرة أو عبر join مع `SmartFarm`/`FarmZone`)، وكل دالة create في service.py بتمرر `tenant_id=self.tenant_id` صراحةً.

**لكن اتلقطت 3 ملاحظات:**

1. **🐛 باج فعلي (dead code, مش مستغَل حاليًا):** `repository.py:144` — `update_bio_cohort_count()` بيستدعي `self.get_bio_cohort(cohort_id)` بدون `tenant_id` (الدالة تتطلب معامل تاني إجباري) → `TypeError` لو اتنادت. **مش متسبب مشكلة دلوقتي لأن ولا دالة في service.py بتستخدمها** — لكن لازم تتصلح لو هنضيف endpoint لتحديث عدد المجموعة الحيوانية.

2. **⚠️ فجوة تحقق (defense-in-depth، مش تسريب بيانات مباشر):** `add_traceability_stage`، `issue_certificate`، و`register_harvest`/`register_bio_yield` (لحقول `destination_facility_id`/`destination_farm_id`) بتقبل IDs خام (`traceable_id`, `certified_entity_id`, ...) **من غير التحقق إن الكيان المُشار إليه فعلاً ملك لنفس الـtenant**. القراءة نفسها بتفضل معزولة (كل query بيفلتر بـtenant_id)، لكن ده معناه ممكن تنشئ شهادة/مرحلة تتبع بمعرّف كيان مش موجود أصلاً عندك. **قرار مقترح:** نسيبها زي ما هي في هذا البناء (مطابقة لباقي الدومينات المشابهة اللي اتبنت النهاردة)، ونوثقها كـfollow-up منفصل — إلا لو حابب نضيف تحقق إضافي دلوقتي.

3. **✅ إيجابي:** `get_farm`, `add_farm_zone`, `start_crop_cycle`, `register_bio_yield`, `record_soil_data`, `get_recent_soil_readings` كلها بتعمل `_check_tenant_access` صريح بعد الجلب، بالإضافة للفلترة في الـquery نفسه — طبقة حماية مزدوجة سليمة.

---

## 3. فحص tasks/agritech.py (orphaned + مكسور — خارج نطاق هذه الجلسة)

`tasks/agritech.py` (262 سطر) عنده استدعاءات لدوال repository بتوقيعات غير متطابقة إطلاقًا مع `repository.py` الحالي:
- `repo.get_soil_reading(reading_id)` — التوقيع الفعلي `get_soil_reading(reading_id, tenant_id)`.
- `repo.get_zone(zone_id)` — التوقيع الفعلي `get_zone(zone_id, tenant_id)`.
- `repo.get_farm(farm_id)` — التوقيع الفعلي `get_farm(farm_id, tenant_id)`.
- `repo.update_zone_last_reading(...)` — **الدالة دي مش موجودة إطلاقًا في `repository.py`.**

هذا الملف غير مستدعى من أي مكان في `service.py` حاليًا (لا `record_soil_data` ولا غيرها بتطلق Celery task)، فهو orphaned تمامًا وأعطاله غير مؤثرة على أي endpoint هنبنيه. **خارج نطاق هذه الجلسة صراحةً** — موثّق هنا فقط عشان ميتنسيش.

---

## 4. مقارنة مع الفرونت إند (hooks + components + services/agritech.ts)

**اكتشاف رئيسي:** `services/agritech.ts` (359 سطر) بالفعل مكتوب بالكامل ومُصمَّم على افتراض **مسار مضاعف الفرع**: كل استدعاء فيه `/agritech/agritech/...` (مش `/agritech/...` البسيط زي transport/tourism-sports). تأكدنا إن `apiClient` الأساسي (`lib/api-client.ts:7`) بيحط `baseURL` = `.../api` بالفعل، فالمسار الفعلي المتوقع = `/api/agritech/agritech/farms` وهكذا.

هذا **يخالف نمط transport/tourism-sports** (اللي فيها `APIRouter(prefix="/domain")` + مسارات بسيطة زي `/hubs`، ينتج `/api/transport/hubs`). لكن بما إن كل ملفات الفرونت إند (services + hooks + components) مكتوبة ومُقفلة على المسار المضاعف، ومطابقتها بالحرف بتوفر جولة تصحيح فرونت إند كاملة — **التصميم المقترح تحت بيطابق المسار المضاعف كما هو مكتوب فعليًا في `services/agritech.ts`**، مع توثيق الانحراف عن نمط باقي الدومينات بوضوح (قرار مطلوب أدناه).

**اكتشافات إضافية (فجوات فرونت إند مستقلة عن الباك إند، موجودة بالفعل بغض النظر عن الـrouter):**

- `services/agritech.ts` **يُصدِّر فقط** `AgritechService` (object واحد). لكن الـhooks التالية بتستورد دوال مباشرة (named exports) **غير موجودة إطلاقًا** في الملف:
  - `useFarms.ts`: `getFarms`, `getFarm`, `updateFarm`, `deleteFarm`
  - `useZones.ts`: `getZones`, `createZone`
  - `useCropCycles.ts`: `getCropCycles`
  - `useHarvests.ts`: `getHarvests`
  - `useBioAssets.ts`: `getBioCohorts`, `createBioCohort`
  - `useSensors.ts`: `getWeatherAlerts`
  → استيراد مكسور بالكامل حاليًا (compile error)، **مستقل تمامًا عن وجود/غياب الـbackend router**.
- `app/(dashboard)/agritech/page.tsx` بيستورد `useAgritechStats` من `@/hooks/agritech/useStats` — **الملف ده مش موجود إطلاقًا** في `hooks/agritech/`.
- **فجوات في service.py نفسه** (مطلوبة من الـhooks بس مش موجودة):
  - `update_farm` — غير موجودة (الموديل عنده `is_deleted`/`deleted_at` بس لا يوجد service/repo method).
  - `delete_farm` (soft delete) — غير موجودة.
  - `list_harvests(cycle_id)` — غير موجودة (فيه `register_harvest` بس ولا يوجد أي get/list للحصاد).
  - `list_bio_cohorts(zone_id)` — غير موجودة (فيه `add_bio_cohort` بس ولا يوجد أي get/list).
  - أي aggregation لإحصائيات dashboard (`useAgritechStats`) — غير موجودة إطلاقًا في service.py.

**قرار مطلوب:** هل نبني الـ19 endpoint المطابقة 1:1 لدوال service.py الموجودة فعليًا **في هذه الجلسة**، ونوثق الفجوات فوق (update/delete farm، list harvests، list bio cohorts، stats، named exports المفقودة في services/agritech.ts، ملف useStats.ts المفقود) كـ**Phase 2 منفصلة** (نفس نمط `phase 2` اللي اتعمل في commit `1bb70b2` لدومينات تانية)؟ ولا نضيفهم دلوقتي كجزء من نفس البناء؟

---

## 5. تصميم router.py المقترح (صفر تنفيذ — بانتظار الموافقة)

**تأكيد صفر تعارض:** `grep` على `main.py` أثبت عدم وجود أي إشارة لـ`agritech` حاليًا — تسجيله آمن 100%. كل الأخطاء المخصصة (`NotFoundError`, `PermissionDeniedError`, `ValidationError`, ...) ترث من `SovereignError` وله `exception_handler` عام في `main.py:104` — الراوتر الجديد **لا يحتاج try/except يدوي**، مطابقةً لنمط `transport/router.py`.

### الجدول الكامل (19 endpoint، مطابقة 1:1 لدوال service.py الموجودة فعليًا)

`router = APIRouter(prefix="/agritech", tags=["Sovereign Agritech"])`

| # | Method | Path (نسبي لـ prefix الراوتر) | دالة service | صلاحية | ملاحظة |
|---|---|---|---|---|---|
| 1 | POST | `/farms` | `create_farm` | active_user | 201 |
| 2 | GET | `/farms` | `list_farms` | active_user | يرجّع `result["items"]` فقط (array مسطّح) |
| 3 | GET | `/farms/{farm_id}` | `get_farm` | active_user | 404 يدوي لو `None` |
| 4 | POST | `/farms/{farm_id}/zones` | `add_farm_zone` | active_user | 201 |
| 5 | GET | `/farms/{farm_id}/zones` | `list_farm_zones` | active_user | unwrap items |
| 6 | POST | `/zones/{zone_id}/crop-cycles` | `start_crop_cycle` | active_user | 201، `Idempotency-Key` header |
| 7 | GET | `/zones/{zone_id}/crop-cycles` | `list_crop_cycles` | active_user | unwrap items |
| 8 | POST | `/crop-cycles/{cycle_id}/harvest` | `register_harvest` | active_user | 201، `Idempotency-Key`، **يرجّع dict مخصَّص مش ORM (راجع الملاحظة تحت)** |
| 9 | POST | `/zones/{zone_id}/bio-cohorts` | `add_bio_cohort` | active_user | 201، `Idempotency-Key` |
| 10 | POST | `/bio-cohorts/{cohort_id}/yields` | `register_bio_yield` | active_user | `Idempotency-Key`، **نفس ملاحظة #8** |
| 11 | POST | `/traceability/stage` | `add_traceability_stage` | active_user | 201 |
| 12 | GET | `/traceability/{traceable_type}/{traceable_id}` | `get_traceability_stages` | active_user | unwrap items |
| 13 | POST | `/traceability/qr/{traceable_type}/{traceable_id}` | `generate_traceability_qr` | active_user | 201، يفشل بـ400 لو `qrcode` مش مثبتة |
| 14 | POST | `/certificates` | `issue_certificate` | **superuser** (مقترح) | 201 — شهادة = فعل توثيقي رسمي |
| 15 | GET | `/certificates/{entity_type}/{entity_id}` | `get_entity_certificates` | active_user | unwrap items |
| 16 | POST | `/soil-readings` | `record_soil_data` | active_user | 201 |
| 17 | GET | `/soil-readings/{zone_id}` | `get_recent_soil_readings` | active_user | `?limit=` query, unwrap items |
| 18 | POST | `/weather-alerts` | `create_weather_alert` | **superuser** (مقترح) | 201 — بث إداري يوثّر على كل مزارع الـtenant |
| 19 | GET | `/weather-alerts` | `get_weather_alerts` | active_user | يرجّع List مباشرة (الدالة أصلاً بترجّع List مش dict) |

### ملاحظات تصميم حرجة (تحتاج قرارك)

**أ) ازدواج المسار (`/agritech/agritech/...`):** `services/agritech.ts` مكتوب بالكامل على افتراض مسار **مضاعف** (`/api/agritech/agritech/farms`)، وهو نمط **غير مستخدم في أي دومين تاني في المشروع كله** (تأكدت بفحص الـ33 راوتر — كلهم prefix بسيط واحد). الجدول فوق مبني على **prefix بسيط** (`/api/agritech/farms`) اتساقًا مع كل الدومينات التانية، لكن هذا يعني تعديل 16 سطر literal string في `services/agritech.ts` (حذف تكرار `/agritech/`) — تعديل ميكانيكي بسيط، لكنه لسه تعديل على ملف فرونت إند موجود.
  - **البديل:** نخلي الراوتر نفسه بمسار مضاعف عمدًا (`APIRouter(prefix="/agritech")` + كل مسار route جواه يتكتب بادئ بـ`/agritech/...` تاني) عشان نطابق `services/agritech.ts` كما هو **بدون أي تعديل فيه** — لكن هذا يُكرِّس انحراف معماري دائم عن باقي الدومينات.

**ب) `register_harvest` و`register_bio_yield` بيرجّعوا dicts مخصَّصة (مش ORM):**
  - `register_harvest` يرجّع `{harvest_id, grade, quantity_kg, tracking_number, ai_logistics_actions}` — لكن `HarvestBatchResponse` (المتوقَّع في `services/agritech.ts:120`) شكله `{id, cycle_id, grade, quantity_kg, harvest_date, shipment_tracking_number, ...}`. تسمية الحقول مختلفة (`harvest_id`≠`id`, `tracking_number`≠`shipment_tracking_number`) وناقص `cycle_id`/`harvest_date`.
  - نفس المشكلة في `register_bio_yield` مقابل `BioProductYieldResponse`.
  - **مقترح:** نضيف schema جديدة مخصَّصة (`HarvestRegistrationResult`, `BioYieldRegistrationResult`) تحافظ على حقل `ai_logistics_actions` المفيد، والراوتر يرجّعها زي ما هي من الـservice بدون تغيير — لكن ده معناه `services/agritech.ts` TS types لهذين الاستدعاءين بالذات غلط وتحتاج تصحيح لاحق (منفصل). **البديل:** إضافة صغيرة لـ`service.py` (سطرين) تحقن `id`/`cycle_id`/`harvest_date`/`shipment_tracking_number` كأسماء بديلة في الـdict المُرجَع، عشان يطابق التوقع الحالي بالكامل من غير أي تعديل فرونت إند.

**ج) فجوات فرونت إند/باك إند مكتشَفة (مستقلة عن بناء الراوتر — راجع قسم 4)، محتاجة قرار Scope:**
  - Named exports مفقودة في `services/agritech.ts` (تكسر كل الـhooks حاليًا، بغض النظر عن الباك إند).
  - `hooks/agritech/useStats.ts` غير موجود إطلاقًا (يكسر `app/(dashboard)/agritech/page.tsx`).
  - دوال service.py مفقودة: `update_farm`, `delete_farm`, `list_harvests(cycle_id)`, `list_bio_cohorts(zone_id)`, وأي stats aggregation.
  - **مقترح:** نبني الـ19 endpoint فوق فقط في هذه الجلسة (مطابقة تمامًا لطلبك الأصلي: "دوال service.py الجاهزة")، ونوثق باقي الفجوات كـ**Phase 2 منفصلة** — بنفس النمط اللي اتبع في commit `1bb70b2` (`phase 2` لدومينات تانية).

**د) `update_bio_cohort_count` (repository.py:141-144):** فيها باج (`self.get_bio_cohort(cohort_id)` ناقص `tenant_id`) — dead code حاليًا، هتفضل كده لأننا مش هنضيف endpoint بيستخدمها في هذا الـscope (ملاحظة أ).

---

## 6. الموافقة + التنفيذ [2026-09-04]

المستخدم وافق على التصميم بالكامل + الأربع قرارات (prefix بسيط، نطاق 19 endpoint فقط، schema جديدة لنتائج التسجيل، صلاحيات كما هي)، وطلب التنفيذ الفوري + تحقق حي + تسجيل PROGRESS_LOG + عرض `git diff --stat` قبل commit.

### التنفيذ الفعلي

1. `router.py` (19 endpoint، `APIRouter(prefix="/agritech")`) + تسجيل في `main.py` (import + سطر في `routers_config`، مكانه أبجديًا بعد `affiliate` قبل `ai_agents`).
2. `services/agritech.ts`: 16 سطر مسار مضاعف (`/agritech/agritech/...`) → بسيط (`/agritech/...`) عبر `sed`.
3. `schemas.py`: إضافة `HarvestRegistrationResult` و`BioYieldRegistrationResult`.
4. `service.py`: حقن أسماء بديلة في نتائج `register_harvest`/`register_bio_yield` (راجع قسم 5.ب).
5. `PROGRESS_LOG.md`: إغلاق البند المفتوح + 3 بنود Backlog جديدة (`agritech-phase2-frontend-gaps`, `update_bio_cohort_count-tenant-id-bug`, `agritech-traceability-certificate-idor-defense-gap`).

### 🐛 اكتشافان حرجان أثناء التحقق الحي (لم يكونا معروفين وقت التصميم — الكود لم يُستورَد فعليًا من قبل أبدًا)

**بق #1 — `repository.py` كان بيكسر الاستيراد بالكامل:** كل دوال `list_*`/`get_*_stages`/`get_entity_certificates`/`get_recent_soil_readings` كانت بترجّع `PaginatedResponse[<ORM Model>]` (زي `PaginatedResponse[SmartFarm]`) — بارامترة الـgeneric كانت كلاس SQLAlchemy خام مش Pydantic schema. مقارنةً بكل الدومينات التانية اللي بتستخدم نفس `PaginatedResponse` (academy, affiliate, ai_agents, commerce, ...) — كلهم بيمرّروا schema فعلية (`PaginatedResponse[CourseResponse]`). هذا كان بيفشل بـ`PydanticSchemaGenerationError` فور `import` — **هذا هو السبب الحقيقي** إن agritech كانت orphaned، مش بس غياب router. **الإصلاح:** استبدال الـ6 استخدامات بالـschemas الفعلية المقابلة.

**بق #2 — `record_soil_data` كانت بتكسر عند أول استدعاء حقيقي:** `audit_log(details={..., "moisture": data.get("moisture_percent")})` بتمرر `Decimal` خام لدالة `audit_log()` اللي بتعمل `json.dumps()` بدون `default=str` → `TypeError`. بما إن `SoilSensorReadingCreate.moisture_percent` نوعه `Decimal`، وPydantic v2 `model_dump()` بيحافظ عليه كـ`Decimal`، هذا كان هيحصل مع **أي طلب حقيقي حاوي moisture_percent** عبر الراوتر. **الإصلاح:** `float(...)` قبل التمرير، نفس نمط باقي الملف. باقي الـ10 استدعاءات audit_log في نفس الملف اتفحصت يدويًا — سليمة.

**إضافات تبعية:** `qrcode[pil]>=8.0` أُضيفت لـ`requirements.txt` (كانت مستخدمة فعليًا في `generate_traceability_qr` مع `try/except ImportError` صريح، لكن غير معلَنة كـdependency إطلاقًا) ومُثبَّتة في venv.

### ✅ التحقق الحي (pytest ضد PostgreSQL حقيقي، صفر mock)

اختبار شامل جديد `tests/test_agritech_router_wiring.py` يغطي كل الموارد التسعة بالترتيب (farm → zone → crop cycle → harvest → bio cohort → bio yield → traceability stage → QR → certificate → soil reading → weather alert)، + تحقق عزل tenant_id على عيّنتين مختلفتين (farms: عمود مباشر؛ soil-readings: عبر join مع FarmZone) — **PASSED** (بعد إصلاح البقين فوق).

تأكيد `app.main` يستورد بنجاح: **581 route إجمالي**، **19 مسار `/api/agritech/*`** مسجَّلة بالضبط بلا تكرار وبلا تعارض (`grep` على كل الدومينات التانية أثبت zero تداخل prefix).

**Full suite (`pytest -q`, كل ملفات tests/):** `4 failed, 141 passed, 2 xfailed` (741 ثانية). الأربعة failures اتفحصت فردًا فردًا — **كلها pre-existing وغير مرتبطة بـagritech إطلاقًا** (صفر تداخل ملفات مع تعديلات هذه الجلسة):
- `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` — assertion على ترتيب أسطر كود في `invoicing/service.py`، مرتبط ببند `invoicing-missing-rollback-on-exception-11b` المفتوح مسبقًا.
- `test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes` و`...saas_check_passes_then_hits_known_bug` — `PermissionDeniedError`/`InsufficientBalanceError` من `realestate/service.py`/`finance/service.py`، غير مرتبطين بأي كود لمسناه.
- `test_user_repository_get_by_id_audit.py::test_social_get_user_email_correct_and_wrong_tenant` — `NotFoundError` من `social/service.py:723`.

كلها في دومينات (`realestate`, `saas`, `finance`, `social`, `invoicing`) لم تُلمَس بأي شكل في هذه الجلسة. **صفر regression ناتج عن عمل agritech.**

**الحالة:** ✅ التنفيذ اكتمل بالكامل. باقي: عرض `git diff --stat` للمستخدم + قرار commit.
