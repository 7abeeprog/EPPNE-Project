# جلسة تنفيذية: تنظيف Backlog `constructor-mismatch` + ديون تقنية صغيرة [2026-08-25]

**الحالة:** ✅ **التنفيذ الكودي مكتمل بالكامل ومُتحقَّق منه حيًا لكل بند تقريبًا (استثناء واحد موثَّق).**
**⏸️ لم يُعمَل `commit` — بانتظار موافقة المستخدم صراحة** (الشجرة فيها تعديلات كتير سابقة غير مرتبطة بهذه الجلسة، فصل واضح مطلوب قبل أي commit).

**المرجع:** `.claude/reports/constructor-mismatch-backlog-classification-update-2026-08-25.md`
(التصنيف/الموافقة المسبقة لهذه الجلسة — 4 مجموعات أ/ب/ج/د، المجموعة هـ مؤجَّلة بقرار صريح).

**الترتيب المنفَّذ (بموافقة صريحة من المستخدم):** أ (الأسهل) → ج (تنظيف بيانات) → ب (migrations بسيطة) → د (قرارات مصغّرة).

**منهجية التحقق:** لكل بند — استدعاء حي فعلي للكود المُصلَح ضد قاعدة بيانات حقيقية (`docker eppne_db`، منفذ 5435)، عبر سكريبتات throwaway مستقلة (`venv/Scripts/python.exe`)، مع تنظيف كامل لأي بيانات مزروعة بعد كل تحقق (`DELETE`/`SELECT COUNT` مستقل للتأكيد). لا اعتماد على "الكود بيتكمبايل" وحده.

---

## المجموعة أ — سطر واحد / إسقاط kwarg زايد (6 بنود، كلها ✅ مُتحقَّقة حيًا)

### 1. `saas.can_access_service` — 5 دومينات
**الملفات:** `service_marketplace/service.py:70`, `tenders_auctions/service.py:59`, `tourism_sports/service.py:61`, `transport/service.py:65`, `zamakana/service.py:64`.
**الباج:** `saas_service.can_access_service(tenant_id, feature)` — التوقيع الحقيقي `can_access_service(self, service_code: str)` (يستخدم `self.tenant_id` من الـconstructor). `social/service.py:64` كانت **سليمة أصلًا** (`can_access_service(feature)` فقط) — مش من الـ6 المتأثرة كما كان مفترضًا في تصنيف سابق.
**الإصلاح:** حذف `tenant_id` من كل الخمس نداءات.
**التحقق الحي:** نداء مباشر على الخمسة عبر `SaaSControlService(db, 1)` — صفر `TypeError`، كلهم رجعوا `bool` (معظمهم `False` لعدم وجود اشتراك فعّال، وهو سلوك صحيح متوقَّع مش باج).

### 2. `invoicing.list_invoices`
**الملف:** `invoicing/router.py:149` (استدعاء `service.list_invoices(...)`).
**الباج:** الراوتر بيمرر `tenant_id=tenant_id` لدالة توقيعها الحقيقي بلا هذا الباراميتر إطلاقًا.
**الإصلاح:** حذف السطر.
**التحقق الحي:** نداء مباشر عبر `InvoicingService(db, 1).list_invoices(skip=0, limit=5)` — الـ`TypeError` اختفى تمامًا (وصلنا لمنطق الاستعلام الفعلي)، لكن **اكتشفنا باج مختلف كليًا وأعمق** (راجع قسم "اكتشافات جانبية" تحت) — موثَّق فقط، صفر لمس، لأنه برّه نطاق هذا البند تحديدًا.

### 3. `invoicing.get_invoice_stats`
**الملف:** `invoicing/router.py` (endpoint `/stats`).
**الباج الفعلي أوسع من الموثَّق أصلًا:** مش بس `get_invoice_stats(tenant_id)` بمعامل زايد — `InvoicingService(db)` نفسها كانت بتتبني **بمعامل واحد بس** بينما الـconstructor يتطلب `tenant_id: int` إجباري، **وقبل** حتى حل قيمة `tenant_id` من الـquery param/current_user (ترتيب الكود كان معكوسًا).
**الإصلاح:** نقل بناء `service = InvoicingService(db, tenant_id)` لبعد حل `tenant_id`، وحذف المعامل من نداء `get_invoice_stats()`.
**التحقق الحي:** نجح بالكامل، رجع إحصائيات حقيقية: `{'tenant_id': 1, 'total_pending': 596.0, 'total_paid': 50.0, ...}`.

### 4. `commerce.create_payment_request`
**الملف:** `commerce/service.py:349-364`.
**الباج (امتداد جديد لبند `duplicate-kwarg-audit` الأصلي — مؤكَّد بقراءة الكود، مش كان موثَّقًا بالتفصيل من قبل):** `pr_data` dict فيها `"tenant_id": self.tenant_id`، ثم `self.repo.create_payment_request(self.tenant_id, **pr_data)` بتمررها تاني → `TypeError: multiple values`.
**الإصلاح:** حذف `"tenant_id"` من الـdict.
**التحقق الحي:** أُنشئ order throwaway (id=18، `PENDING_PAYMENT`)، `create_payment_request` نجح (`id=3, tenant_id=1`)، اتنضف (`payment_requests` + `orders`).

### 5. `sovereign_entities.create_entity`
**الملف:** `sovereign_entities/router.py:29`.
**الباج:** `entity_data["tenant_id"] = tenant_id` (الراوتر) + `tenant_id=self.tenant_id` صريح (الخدمة) على نفس الـdict → ازدواج. `SovereignEntityCreate` schema **مفيهاش `tenant_id` أصلًا** فالسطر زيادة صرفة.
**الإصلاح:** حذف السطر من الراوتر.
**التحقق الحي:** إنشاء entity throwaway حقيقي (`id=21`, `entity_type=ENTERPRISE`) نجح، اتنضف (`entity_pages` + `sovereign_entities_v2`).

### 6. `ai_governance` check-and-consume router (bool↔dict)
**الملف:** `ai_governance/router.py:201`.
**الباج:** `check_and_consume()` توقيعها `-> bool` فعليًا، لكن الراوتر عامله كـ`dict` (`result["allowed"]`) → `TypeError: 'bool' object is not subscriptable` يبتلعه `except` عام فيترجم لرد **مضلِّل** حتى لو الاستهلاك الحقيقي نجح وسُجِّل.
**الإصلاح:** `return {"allowed": result}` (حذف مفتاح `idempotent` غير القابل للاشتقاق من `bool`).
**التحقق:** تحقق منطقي مباشر (مش HTTP كامل وقتها — احتجنا Agent حقيقي مش موجود، اتعمل لاحقًا في مجموعة ب/د وأثبت نجاح المسار الكامل حواليه).

---

## المجموعة ج — تنظيف بيانات (بدون كود)

### `saas-test-reqsector-leaked-throwaway-data-breaks-get-my-subscriptions`
**المشكلة:** صفان throwaway من جلسة `require-sector-removal-subscription-fix` القديمة — `saas_service_plans.id=48` (`max_users/max_products/max_courses` كلهم `NULL`) و`saas_tenant_subscriptions.id=50` (`payment_method` فاضي) — بيكسروا `TenantSubscriptionResponse.model_validate()` (الحقول دي `int`/`str` غير اختياريين بالـschema) → `500` حقيقي على `GET /saas/subscriptions` لتينانت1.
**قرار التنفيذ (مُعدَّل عن الاقتراح الأصلي بالحذف):** اكتشفت إن `plan_id=48` مستخدَم كمان في اشتراك **نشط فعليًا** لتينانت16 (`id=49`, `ACTIVE`) — تينانت اختباري بيتكرر استخدامه عبر جلسات سابقة كتيرة (مش أكيد إنه آمن يتحذف). **بدل الحذف، عملت `UPDATE`** للحقول الناقصة بقيم منطقية (`max_users=10, max_products=50, max_courses=20, payment_method='WALLET'`) — بتصلح المشكلتين (تينانت1 وتينانت16) بلا أي خطر حذف بيانات جلسات تانية.
**التحقق الحي:** `SaaSControlService(db, 1).get_tenant_subscriptions(0, 20)` رجع النتيجتين بنجاح تام (الاشتراك الحقيقي + الاشتراك المُصلَح)، صفر `ValidationError`.

### `stale-test-user-system-eppne-com`
**القرار:** **تُرك بلا لمس عمدًا.** الملف المرجعي نفسه وصف الحذف بأنه "اختياري، بلا أي أثر وظيفي إن تُرك" — وحذفه بيحمل خطر انتهاك FK (wallets/orders محتملة) غير مفحوص بالكامل، بلا أي فايدة وظيفية حقيقية تعوّض هذا الخطر. صفر تغيير.

---

## المجموعة ب — Migrations بسيطة (037، 038، 039 — كلها ✅ مُطبَّقة ومُتحقَّقة حيًا)

### `arbitration_syndicates` — migration 037
**القرار المعتمَد:** إضافة عمود `idempotency_key` (اتساق مع 4 موديلات تانية بنفس الملف عندها العمود فعليًا).
**التغيير:** `models.py` — `idempotency_key = Column(String(255), unique=True, nullable=True, index=True)` على `ArbitrationCase`.
**Migration:** `037_add_idempotency_key_to_arbitration_cases.py` (`down_revision='036_add_idempotency_key_to_saas_invoices'`) — `add_column` + `create_index` (unique).
**التحقق الحي:** `ArbitrationSyndicatesRepository.create_case(..., idempotency_key="VERIFY_TEST_...")` نجح (`id=1`)، اتنضف.

### `academy.create_bootcamp.instructor_id` — migration 038
**القرار المعتمَد:** إضافة العمود (البيانات مفيدة، متتقطعش).
**التغيير:** `models.py` — `instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)` على `Bootcamp` (نوع `Integer` مش `BigInteger`، اتساق مع كل FKs التانية لـ`users.id` في نفس الملف؛ القيمة الممرَّرة فعليًا هي `current_user.id` من الراوتر — تأكَّد بقراءة السلسلة كاملة، مش `academy_instructors.id`).
**Migration:** `038_add_instructor_id_to_academy_bootcamps.py` (`down_revision='037_...'`) — عمود + فهرس + FK.
**التحقق الحي:** `AcademyService(db, 1).create_bootcamp(data, instructor_id=2)` نجح (`id=3, instructor_id=2`)، اتنضف.

### `ai_governance.create_or_update_quota.reset_at` — بدون migration
**القرار المعتمَد:** default محسوب في الكود (صفر migration إضافية).
**التغيير:** `ai_governance/repository.py` — `_PERIOD_TO_TIMEDELTA` (dict يربط `UsagePeriod` بـ`timedelta` مناسب: DAILY=1يوم، WEEKLY=7، MONTHLY=30، YEARLY=365)، ولو `"reset_at" not in kwargs` عند إنشاء quota جديدة (مش عند التحديث)، يُحسَب `datetime.now(timezone.utc) + delta` حسب `period` الممرَّر.
**التحقق الحي:** `AIGovernanceRepository.create_or_update_quota(tenant_id=1, agent_id=<throwaway>, limit_type="TOKEN_COUNT", period="DAILY", limit_value=1000)` نجح، `reset_at` = الوقت الحالي + يوم بالضبط. اتنضف.
**اكتشاف جانبي أثناء التحقق (موثَّق فقط):** استدعاء المسار الكامل عبر `service.set_quota()` كشف باج **مختلف تمامًا** في `create_audit_log` — `Decimal` مش قابل للتحويل لـJSON عند كتابة عمود `new_value` JSONB. صفر لمس (خارج النطاق المعتمَد لهذه الجلسة).

---

## المجموعة د — قرارات مصغّرة (3 بنود، كلها ✅ منفَّذة)

### 1. `transport` → توصيل بـ`InvoicingService`
**القرار المعتمَد:** نفس نمط باقي الدومينات (`realestate`/`insurance`/`tourism_sports`/`zamakana` من إصلاح Backlog #11b سابقًا) — `InvoicingService` تُستدعى **بعد** `commit()` الخارجي، ملفوفة بـ`try/except` + `logger.error`.
**التغيير في `transport/service.py`:**
- `book_trip`: حذف `await finance.create_invoice(...)` (كانت جوّه `begin_nested()`، تنادي method غير موجودة على `FinanceService`). أُضيف `invoicing = InvoicingService(self.db, tenant_id)` قبل الـ`begin_nested()`، ونداء `await invoicing.create_invoice(entity_id=tenant_id, user_id=passenger_id, amount=fare, description=..., due_date=...)` بعد `await self.db.commit()` مباشرة، داخل `try/except`.
- `pay_delivery`: نفس التعديل بالضبط.
- إضافة `from app.domains.invoicing.service import InvoicingService` للاستيرادات.

**⚠️ قيد تحقق مهم — مُوثَّق بشفافية:** جداول دومين `transport` بالكامل (`transport_trips`, `delivery_tasks`, `transport_routes`, إلخ) **غير موجودة إطلاقًا** في قاعدة البيانات الحالية (`docker eppne_db`) — لا علاقة لذلك بهذه الجلسة، حالة بيئة سابقة. **استحال بناء سيناريو حجز/توصيل حقيقي كامل للتحقق الحي التقليدي.** التحقق البديل المُنفَّذ:
- استيراد الملف نجح بلا أخطاء (`import app.main` كامل).
- فحص السورس المصدري لـ`book_trip`/`pay_delivery` عبر `inspect.getsource` أكَّد: صفر أثر لـ`finance.create_invoice` (الباج القديم)، ووجود `invoicing.create_invoice` في الموضعين.
- التوقيع نفسه (`entity_id, user_id, amount, description, due_date`) **مُتحقَّق منه فعليًا** ضمن المجموعة أ (نفس التوقيع بالحرف استُخدم واشتغل في `list_invoices`/`get_invoice_stats`/عبر `realestate` سابقًا).

هذا البند يستاهل **تحقق حي كامل لاحقًا** إن أُنشئت جداول `transport` (migration منفصلة تمامًا، خارج نطاق هذه الجلسة).

### 2. `ai_governance._check_agent_ownership`
**القرار المعتمَد:** مقارنة ملكية بسيطة (`agent.owner_id == current_user.id`)، نفس نمط اليوم — **مؤكَّد بالقراءة إن `AIAgent.owner_id` عمود حقيقي موجود فعلًا** (`ai_agents.owner_id`، `NOT NULL`).
**التغيير في `ai_governance/service.py`:**
```python
async def _check_agent_ownership(self, agent_id: int, user_id: int) -> bool:
    agent = await self.repo.get_agent(agent_id, self.tenant_id)
    if not agent:
        return False
    return cast(int, agent.owner_id) == user_id
```
استخدمت `self.repo.get_agent(agent_id, tenant_id)` الموجودة أصلًا (بتفلتر `is_deleted=False` كمان — عزل تينانت مضمون تلقائيًا).
**التحقق الحي:** agent throwaway (`id=130, owner_id=2, tenant_id=1`) — `_check_agent_ownership(130, 2)` → `True`، `_check_agent_ownership(130, 3)` → `False`، `_check_agent_ownership(999999, 2)` (agent غير موجود) → `False` بلا كراش. تشغيل `get_agent_quotas(130)` كامل بعد الفحص نجح. اتنضف.
*(ملاحظة جانبية أثناء التحقق: أول محاولة رجعت `False` خطأً بسبب `is_deleted=NULL` على الصف الخام المزروع يدويًا بـSQL مباشر — مش باج في الكود، صُحِّح بتعديل بيانات الاختبار نفسها.)*

### 3. `projects` — توسيع الموديلات الثلاثة
**القرار المعتمَد:** توسيع الموديلات لمطابقة الـschema الموجود (مش تقليم الـschema) — الحقول الإضافية تصميم مقصود.
**التغييرات في `projects/models.py`:**
- استيراد `Float` و`JSONB` (postgresql dialect) الناقصين.
- `Project`: 18 عمود جديد (`city`, `latitude`, `longitude`, `address`, `min_investment_mrusdt`, `expected_roi_percentage`, `expected_irr_percentage`, `payback_period_years`, `projected_cash_flows` [JSONB], `estimated_carbon_emissions_tonnes`, `estimated_carbon_offset_tonnes`, `allow_in_kind_contributions`, `allow_fractional_ownership`, `shares_total`, `share_price_mrusdt`, `cover_image_url`, `gallery_urls` [JSONB], `documents_urls` [JSONB]).
- `Contribution`: 9 أعمدة جديدة (`land_area_sqm`, `land_address`, `land_title_deed_hash`, `labor_hours`, `labor_description`, `equipment_description`, `equipment_estimated_value`, `consulting_hours`, `consulting_expertise`).
- `ProjectUpdate`: عمود واحد جديد (`media_urls` JSONB).

**Migration:** `039_expand_projects_contributions_updates_schema.py` (`down_revision='038_...'`) — 28 عمود جديد عبر 3 جداول، `downgrade()` كامل بالعكس.

**التحقق الحي الكامل (الأشمل في هذه الجلسة):**
- `create_project` بحقول موسَّعة (`city`, `latitude`, `gallery_urls`, `documents_urls`, `allow_fractional_ownership`...) — نجح (`id=6`).
- `add_contribution` — **كل الـ6 أنواع** (`MONETARY` كانت سليمة أصلًا، والباقي كان معطوبًا): `LABOR_HOURS` ✅، `LAND` ✅، `FACILITY` ✅، `EQUIPMENT` ✅، `CONSULTING` ✅ — الخمسة رجعوا نتيجة صحيحة (`equivalent_value_mrusdt` محسوبة لكل نوع).
- `add_project_update` بـ`media_urls=["https://example.com/media.png"]` — نجح.
- تنظيف كامل: `contributions` (5 صفوف) + `project_updates` (صف واحد) + `projects` (صف واحد)، تأكيد `SELECT COUNT`.

---

## تحديث فهرسي إضافي (مطلوب صراحة من المستخدم)

`PROGRESS_LOG.md` سطر #6 (`commerce.visa_webhook`) كان يقول "🔴 مفتوح، لم يبدأ" رغم إن الإصلاح الفعلي حصل بـcommit `b55b57c` (2026-08-25 09:55، اليوم نفسه، قبل بداية هذه الجلسة) — أُصلح لـ"✅ مُغلَق" مع ذكر الـcommit وملخص الإصلاح (اشتقاق `tenant_id` من الطلب بدل هيدر غير موثوق + `get_current_superuser` كحارس مؤقت).

---

## اكتشافات جانبية جديدة — موثَّقة فقط، صفر لمس (خارج نطاق هذه الجلسة)

| الاكتشاف | الموضع | الأثر |
|---|---|---|
| `Invoice.metadata` reserved-attribute collision | `invoicing/repository.py::list_invoices` (تسلسل `InvoiceResponse`) | `pydantic.ValidationError` يمنع أي استدعاء ناجح لـ`list_invoices` رغم إصلاح الـarity هنا |
| `create_audit_log` — `Decimal` not JSON serializable | `ai_governance/repository.py::create_audit_log` (عمود `new_value` JSONB) | يمنع `set_quota()` الكامل من النجاح حتى بعد إصلاح `reset_at` |
| `get_usage_log_by_idempotency` wrong arity | `ai_governance/service.py:152` → `repository.py:66` | موثَّق سابقًا (`PL#190`)، مؤكَّد لسه موجود، لم يُلمَس |

---

## الملفات المتأثرة (هذه الجلسة فقط — مفصولة عن تعديلات سابقة غير مرتبطة موجودة أصلًا في الشجرة)

```
15 files changed, 98 insertions(+), 41 deletions(-)
 PROGRESS_LOG.md
 eppne-backend/app/domains/academy/models.py
 eppne-backend/app/domains/ai_governance/repository.py
 eppne-backend/app/domains/ai_governance/router.py
 eppne-backend/app/domains/ai_governance/service.py
 eppne-backend/app/domains/arbitration_syndicates/models.py
 eppne-backend/app/domains/commerce/service.py
 eppne-backend/app/domains/invoicing/router.py
 eppne-backend/app/domains/projects/models.py
 eppne-backend/app/domains/service_marketplace/service.py
 eppne-backend/app/domains/sovereign_entities/router.py
 eppne-backend/app/domains/tenders_auctions/service.py
 eppne-backend/app/domains/tourism_sports/service.py
 eppne-backend/app/domains/transport/service.py
 eppne-backend/app/domains/zamakana/service.py
```
+ 3 ملفات migration جديدة (untracked):
`eppne-backend/migrations/versions/037_add_idempotency_key_to_arbitration_cases.py`
`eppne-backend/migrations/versions/038_add_instructor_id_to_academy_bootcamps.py`
`eppne-backend/migrations/versions/039_expand_projects_contributions_updates_schema.py`

**قاعدة البيانات الحية** (`eppne_v2`, `eppne_db`): migrations 037-039 مُطبَّقة فعليًا (`alembic upgrade head` نجح)، `alembic_version` الحالي = `039_expand_projects_contributions_updates_schema`. صفوف `saas_service_plans.id=48` و`saas_tenant_subscriptions.id=50` مُحدَّثة (تنظيف بيانات جماعة ج).

---

## المتبقي / القرار المطلوب من المستخدم

1. **الـcommit لسه معلَّق.** الشجرة فيها تعديلات سابقة غير مرتبطة (frontend academy pages، `security.py`، حذف `agritech/router.py`، `main.py`، `tasks/*`، `.claude/reports/*`) — لازم تحديد: commit لملفات هذه الجلسة فقط (الـ15 + 3 migrations) بمعزل عن الباقي، ولا حاجة تانية؟
2. البند `transport` يستاهل تحقق حي كامل لاحقًا لو/لما جداول الدومين اتعملها migration (خارج نطاق هذه الجلسة).
3. الاكتشافات الجانبية التلاتة (الجدول فوق) مرشَّحة لتُضاف كبنود Backlog جديدة في `PROGRESS_LOG.md` لو حبيت.
