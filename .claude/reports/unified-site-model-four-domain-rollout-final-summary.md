# تقرير ختامي — ربط الأربعة دومينات بـ`Site` الموحّد (iot/manufacturing/agritech/health)

**نوع الجلسة:** تلخيص ختامي بعد اكتمال الخطوة 3 من مستند التصميم
(`.claude/reports/unified-site-model-and-academy-camera-design-proposal.md`
§1.4) على كل الأربعة دومينات المستهدفة. الدومين الرابع (health) نُفِّذ في
هذه الجلسة، والتقرير هذا يجمع حالة الأربعة معًا.

**التاريخ:** 2026-09-17

---

## 1. ملخص الأربعة دومينات

| # | الدومين | الموديل | migration | النوع | `entity_id`/`location_gps` القديم |
|---|---|---|---|---|---|
| 1 | `iot` | `SmartAsset` | 058 | استبدال كامل | حُذفا الاثنان (صفر FK أصلًا على `entity_id`) |
| 2 | `manufacturing` | `ManufacturingFacility` | 059 | استبدال كامل | حُذفا الاثنان. `real_estate_unit_id` بلا لمس |
| 3 | `agritech` | `SmartFarm` | 060 | **إضافة صافية** | لا يوجد `location_gps` أصلًا. `entity_id` (ميت، بلا FK) **بلا لمس عمدًا** — قرار مستخدم صريح، وُثِّق كـbacklog منفصل (§3 أسفل). `land_asset_id` بلا لمس |
| 4 | `health` | `HealthFacility` | 061 | **إضافة صافية (الاستثناء الموثَّق في §1.4)** | لا يوجد `location_gps` أصلًا. `entity_id` **FK حقيقي** لـ`sovereign_entities_v2` (migration 052، مجهود hardening مُغلَق) — **بلا لمس إطلاقًا** |

**الفرق الجوهري بين الفئتين:**
- **iot/manufacturing:** `entity_id` كان عمود ميت بلا أي FK ولا استخدام حقيقي → استبدال كامل بـ`site_id` منطقي وآمن.
- **agritech:** نفس حالة `entity_id` الميت (زي iot/manufacturing)، لكن القرار كان تركه بلا لمس لتقليل نطاق التغيير عن الحد الأدنى المطلوب (site_id فقط) — بعكس iot/manufacturing، وليس لأن الحالة التقنية مختلفة.
- **health:** حالة تقنية مختلفة جوهريًا — `entity_id` FK حقيقي مُنجَز حديثًا (migration 052)، فالإضافة هنا صافية بلا أي جدل.

---

## 2. سلاسل الحذف قبل فرض `NOT NULL` — ملخص عبر الأربعة

كل الأربعة احتاجوا حذف صف/صفوف throwaway واحدة (بيانات constructor/regression
test، أنماط تسمية واضحة `P-CTOR-*`/`REGTEST-*`/`p_ctor_*`) قبل فرض
`site_id NOT NULL`، بالمنهجية الدفاعية نفسها (فحص كل جدول تابع بالـFK قبل
أي `DELETE`، subqueries مرتبطة بجدول الأصل لا IDs مباشرة):

| الدومين | صفوف مباشرة | جداول تابعة محذوفة | إجمالي الجداول |
|---|---|---|---|
| iot | 1 (`smart_assets`) | — | 1 |
| manufacturing | 2 (`manufacturing_facilities`) | `production_lines`, `product_blueprints`, `production_batches` | 4 |
| agritech | 1 (`smart_farms`) | `farm_zones`, `crop_cycles`, `bio_asset_cohorts`, `soil_sensor_readings`, `harvest_batches`, `bio_product_yields`, `supply_chain_stages`, `traceability_qrs`, `agricultural_certificates` | 10 |
| health | 1 (`health_facilities`) | `medical_appointments`, `health_consultations` (0), `facility_departments` (0), `emergency_dispatches` (0) | 5 |

**صفر إعادة إدراج في أي دومين، صفر بيانات إنتاجية حقيقية لُمست.**

---

## 3. Backlog منفصل مفتوح — `agritech-smartfarm-unused-entity-id-column`

عمود `SmartFarm.entity_id` (nullable, بلا FK) اتأكَّد إنه ميت تمامًا: غائب
من `SmartFarmCreate` schema، غير مُستخدَم في `service.create_farm()` ولا
أي مكان تاني في الكود. بموافقة المستخدم الصريحة، **تُرِك بلا لمس** ضمن
نطاق هذه الجلسة (الفرق المتفَق عليه لـagritech كان "إضافة site_id فقط").
يستاهل تنظيف مستقبلي منفصل تمامًا عن مجهود Site — قرار منفصل، خارج نطاق
هذا المجهود.

---

## 4. تحقق ما بعد التنفيذ — الأربعة دومينات

- ✅ `\d <table>` لكل دومين تأكَّد: `site_id NOT NULL` + FK حقيقي لـ`sites.id`،
  والأعمدة الأخرى (`real_estate_unit_id`, `land_asset_id`, `entity_id`
  الحقيقي في health) سليمة بلا أي تعديل غير مقصود.
- ✅ `app.domains.sites` تأكَّد شغّال بلا أي مشكلة بعد كل الأربعة migrations
  (import مباشر لـ`app.main` + `Site` model في كل مرة).
- ✅ pytest الكامل بعد health: **`13 failed, 225 passed, 2 xfailed`** —
  مطابقة حرفية 100% مع baseline المعروف (نفس قائمة الفشول الثلاثة عشر:
  `test_realestate_insurance_savepoint.py` ×1,
  `test_user_repository_get_by_id_audit.py` ×10,
  `test_user_repository_get_user_audit.py` ×2). صفر اسم جديد، صفر اسم غائب.
  محاولة واحدة فقط، بلا `killed` (~10 دقائق).

**فشل جديد وُجد وأُصلح أثناء دومين agritech:**
`test_agritech_router_wiring.py::test_agritech_full_domain_flow_live` —
الاختبار مكنش بيمرّر `site_id` الإلزامي الجديد. أُصلح بإضافة إنشاء `Site`
(نفس نمط `test_iot_carbon_settlement_response_schema.py`) + تمريره +
تنظيفه.

**5 ملفات اختبار عُدِّلت أثناء دومين health** لتمرير `site_id` الجديد
(كل التعديلات إضافة `Site` fixture + تمريرها + تنظيفها، بلا لمس منطق
الاختبار الأصلي):
`test_guardian_overview_endpoint_implementation.py`,
`test_health_appointments_tenant_isolation_fix.py`,
`test_health_entity_membership_full_implementation.py` (3 مواضع),
`test_health_nameerror_and_fee_ordering_fix.py` (2 مواضع),
`test_idempotency_truthy_bug_fix.py`. تشغيل الخمسة منفردين: **`15 passed`**
قبل تشغيل السلسلة الكاملة.

---

## 5. الحالة الختامية

✅ **الخطوة 3 من مستند التصميم مكتملة بالكامل على الأربعة دومينات
المستهدفة (iot/manufacturing/agritech/health).** `Site` موحّد الآن نقطة
مرجعية حقيقية لموقع كل من: أصول IoT، منشآت التصنيع، المزارع الذكية،
والمنشآت الصحية — بلا كسر أي مجهود hardening سابق (health entity-membership)
وبلا حذف أي بيانات إنتاجية حقيقية.

**مفتوح للمستقبل:**
- `agritech-smartfarm-unused-entity-id-column` (§3 أعلاه) — تنظيف منفصل.
- الخطوات التالية من مستند التصميم (academy camera device authentication،
  `ClassroomCameraAnalysis.site_id`) لم تبدأ بعد — خارج نطاق هذه الجلسة.
