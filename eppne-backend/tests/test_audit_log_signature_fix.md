# `test_audit_log_signature_fix.py`

## المرجع الأصلي
- `.claude/reports/audit-log-fix-session-log.md` (المرحلة 1.2، جلسة `audit-log-signature-fix`، Backlog #14).

## السبب الجذري (كان) — ملخص
`audit_log()` (`app/core/audit.py`) — دالة logger فقط (`logging.info(json.dumps(...))`، صفر كتابة DB) — توقيعها القديم كان يقبل `action, user_id, details, ip_address` فقط. **95 موضع استدعاء عبر 18 ملف** كانوا بيمرروا `tenant_id=`/`resource_id=` (kwargs غير معروفة) → `TypeError` فوري.

**اكتشاف حرج غيَّر تأطير الخطورة بالكامل:** صفر `try/except` حوالين أي من الـ95 استدعاء، وصفر exception handler عام في `main.py`. يعني الباج **مش "audit trail بيفشل بصمت"** — كان **العملية الأساسية بترجع 500 خام**، ولأغلب المواضع (اللي فيها `commit()` بعد `audit_log()`) البيانات **كمان ما بتتحفظش على القرص إطلاقًا**.

## الإصلاح المُطبَّق
توسيع توقيع `audit_log()` ليقبل `tenant_id: Optional[int] = None`/`resource_id: Optional[int] = None` فعليًا (يُسجَّلان في الـJSON log entry). **صفر migration** (الدالة logger فقط، مفيش جدول DB مرتبط). صفر لمس على أي من الـ95 موضع الاستدعاء.

## إيه اللي بيتحقق منه هذا الملف
**3 مواضع تمثيلية** (مش الـ95 كلهم — بتنوّع نوع العملية، حسب تعليمات الجلسة):

| # | الموضع | النوع | نمط الـtransaction |
|---|---|---|---|
| 1 | `insurance.create_policy` | 💰 مالي | `audit_log()` قبل `commit()`، جوّه `begin_nested()` |
| 2 | `sovereign_entities.create_entity` | 🏛️ إداري | `audit_log()` بعد commits سابقة فورية (صفر `begin_nested()`) |
| 3 | `zamakana` (`ZAMAKANA_NODE_CREATED`) | 👤 عادي | `audit_log()` بعد `commit()` فوري لـ`repo.create_node()` |

كل عيّنة بتغطي نمط transaction مختلف فعليًا موجود في الكود — مش نفس السيناريو 3 مرات بأسماء مختلفة.

**كل اختبار بيثبت اثنين معًا (مطابق لمنهجية التقرير الأصلي، قسم 10):**
1. **`audit_log()` نجحت بلا `TypeError`** — بالتقاط سجل `eppne.audit` logger فعليًا عبر `logging.Handler` مؤقت (مش مجرد "صفر استثناء ظاهري")، وفحص `tenant_id`/`resource_id` داخل الـJSON المُسجَّل فعليًا.
2. **العملية الأساسية اتحفظت فعليًا على القرص** — `SELECT` مستقل يثبت الحفظ، يعني الـ500/rollback الصامت اختفى فعليًا.

### تجاوز متعمَّد لبج غير مرتبط (Backlog #12، `saas-control-service-wrong-arity-call`)
اختبار `zamakana` بيستدعي `ZamakanaRepository.create_node()` + `audit_log()` **مباشرة، بنفس الشكل الحرفي المستخدَم في `zamakana/service.py:78-98`** — بمعزل عمدًا عن `ZamakanaService.create_node()` الكاملة، لأنها بتصطدم ببج مسبق منفصل تمامًا (`_check_saas_limits` بتنادي `SaaSControlService.can_access_service(tenant_id, feature)` بمعاملين، لكن التوقيع الحقيقي `can_access_service(service_code)` بمعامل واحد فقط) **قبل** ما توصل حتى لـ`audit_log()`. **مؤكَّد بالقراءة المباشرة [2026-08-19] إنه لسه موجود بالحرف.** صفر لمس — خارج نطاق #14 تمامًا.

## بيانات throwaway
- `tenant_id=1`. `sovereign_entities_v2 id=3` — صف موجود بالفعل، قراءة فقط (نفس نمط `EXISTING_LAND_ASSET_ID` في الملفات السابقة)، مُستخدَم كـ`issuer_entity_id` لبوليصة التأمين.
- كل اختبار يستخدم بيانات جديدة (`uuid4` suffix) — صفر تصادم بين تشغيلات.
- تنظيف كامل في `finally` بعد كل اختبار؛ تأكَّد بـ`SELECT` مباشر بعد التشغيل (مرتين متتاليتين): صفر صفوف throwaway متبقية.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_audit_log_signature_fix.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435).

**آخر تشغيل مُوثَّق [2026-08-19]:** 3 passed (تشغيلتان متتاليتان، صفر تذبذب).
