# Agritech — فحص تصنيف سريع (2026-08-26)

**نوع الجلسة:** قراءة فقط، تصنيف حالة فقط — لا جرد endpoints كامل.

## الأسئلة الأربعة

**1. مسجَّل في main.py؟**
لا (working tree الحالي). في HEAD الملتزم فعليًا مسجَّل (`from app.domains.agritech.router import router as agritech_router` + mount على `/agritech`)، لكن التسجيل ده معلَّق كـ**تعديل غير ملتزم (uncommitted)** من Phase 13 — موثَّق ومتروك عمدًا في 3 جلسات سابقة على الأقل (`phase16-session-log.md:686-690`, `rbac-ownership-review-session-log.md:313`, `security-deps-unification-session-log.md:600`) تحت تصنيف "خارج النطاق، ملفات معلَّقة من قبل، ملهاش علاقة بالجلسة الحالية".

**2. فيه router.py/service.py حقيقي؟**
- `router.py`: **محذوف من working tree**. النسخة اللي كانت موجودة في HEAD (204 سطر) لم تكن راوتر agritech حقيقي أصلًا — كانت **نسخة مكررة بالخطأ من `ai_governance/router.py`** (header الملف نفسه بيقول `# app/domains/ai_governance/router.py`، والـ endpoints بتستخدم `AIGovernanceService`). يعني حتى وقت ما كان "مسجَّل"، مكنش فيه API حقيقي لـagritech أصلًا — كان agritech mount بيقدّم endpoints ai_governance بالغلط.
- `service.py` / `models.py` / `repository.py` / `schemas.py`: **موجودة وحقيقية فعلًا** (671 + 312 + 283 + 188 = 1454 سطر) — منطق أعمال كامل (farms, crop cycles, harvest, bio assets, traceability QR, certificates, soil sensors, weather alerts)، مش stubs. هذا تغيير حقيقي عن حالة "معطَّل بالكامل بدون أي كود" في الجرد القديم.
- **لكن**: `AgriTechService` **صفر استدعاء فعلي في المشروع كله** — مستوردة فقط في `tasks/agritech.py` (Celery tasks) وغير مستخدَمة فيه إطلاقًا (dead import)، موثَّق في `constructor-mismatch-session-log.md:55,138`. يعني الكود موجود لكن orphaned — مفيش أي مسار (HTTP ولا حتى task) بيشغّله فعليًا.

**3. Endpoints قابلة للوصول؟ جداول DB/migration موجودة؟**
- Endpoints: **لا يوجد أي endpoint قابل للوصول** — لا راوتر مسجَّل حاليًا، ولو كان مسجَّل كان هيقدّم ai_governance مش agritech.
- DB tables: **موجودة فعلًا** في migration واحدة شاملة (`migrations/versions/71820e4fe1f3_initial_migration_all_34_sectors_final.py`) — 12 جدول (`smart_farms`, `farm_zones`, `crop_cycles`, `harvest_batches`, `bio_asset_cohorts`, `bio_product_yields`, `supply_chain_stages`, `traceability_qrs`, `agricultural_certificates`, `soil_sensor_readings`, `weather_alerts`, + enums). الـschema متوفرة في DB لكن مفيش أي كود بيوصلها فعليًا (لا API ولا task).

**4. الخلاصة**
**لسه معطَّل وظيفيًا بالكامل من ناحية الوصول (zero reachable API)** — نفس نتيجة الجرد القديم (Phase 11/13)، لكن السبب اتغيّر شكليًا: مكنش "مفقود بالكامل"، كان فيه راوتر مكرَّر بالغلط من ai_governance اتشال (uncommitted)، والكود الحقيقي (service/models/repo) اتبنى فعلًا لكنه **orphaned بدون أي نقطة استدعاء** (لا HTTP ولا Celery). صفر تعرّض أمني حاليًا لأنه صفر وصول — لا داعي لدفعة أمنية منفصلة الآن.

## توصية
- ملهوش أولوية أمنية (مفيش سطح هجوم — الكود مش reachable).
- التعديل غير الملتزم (حذف router.py + main.py) يستاهل commit مستقل منفصل يوثّق إزالة الراوتر المكرَّر بالخطأ (تنظيف)، بدل ما يفضل معلَّق في working tree إلى ما لا نهاية — قرار للمستخدم، مش منفَّذ هنا (جلسة قراءة فقط).
- لو حصل قرار مستقبلي لتفعيل agritech كـ feature حقيقي، هيحتاج: (أ) كتابة router.py حقيقي من الصفر (مش استرجاع القديم — كان تالف)، (ب) توصيل `AgriTechService`/`AgriTechRepository` الموجودين فعلًا، (ج) عندها يستاهل دفعة أمنية كاملة زي باقي الدومينات.
