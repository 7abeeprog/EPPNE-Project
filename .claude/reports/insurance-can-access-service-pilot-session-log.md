# تقرير جلسة — Pilot: تحويل `insurance` من `check_feature_access` إلى `can_access_service_via_plan` (جدول many-to-many)

**تاريخ الجلسة:** 2026-09-07
**النطاق المطلوب (حرفيًا):** دومين `insurance` فقط. **ممنوع** لمس أي دومين
تاني من الـ7 الباقيين (`employment`, `digital_twin`, `arbitration_syndicates`,
`realestate`, `manufacturing`, `logistics`, `invitations`)، ممنوع لمس
`check_feature_access` نفسها (تفضل موجودة لحد ما الباقي يتحول)، وممنوع أي
حذف عمود. هذا أول تطبيق فعلي (pilot) لقرار
`PROGRESS_LOG.md` ([2026-09-07] — قرار تصميم: توحيد
check_feature_access/can_access_service عبر جدول many-to-many جديد)
والـmigrations 046/047 اللي أنشأت `saas_plan_service_access`.

---

## 1. الملفات المتأثرة (كل التغييرات الفعلية)

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/saas/models.py` | إضافة `class PlanServiceAccess` (ORM جديد لجدول `saas_plan_service_access`) |
| `eppne-backend/app/domains/saas/repository.py` | إضافة `get_active_subscription_via_plan_access()` |
| `eppne-backend/app/domains/saas/service.py` | إضافة `has_any_active_subscription()` و`can_access_service_via_plan()` — بدون لمس `check_feature_access`/`can_access_service` الموجودين |
| `eppne-backend/app/domains/insurance/service.py` | `_check_saas_limits()` (سطر 47-56) بقى بيستخدم الاثنين الجداد بدل `check_feature_access` |

**لم يُلمَس أي ملف تاني** (تأكَّد بـ`git status`/`git diff` — الملفات المتأثرة الوحيدة في `app/` من هذه الجلسة هي الأربعة فوق. ملفات تانية ظاهرة كـ`modified` في `git status` عامة للريبو — `app/core/security.py`، `app/domains/health/service.py`، `app/tasks/billing.py` — كانت أصلًا معدَّلة **قبل بدء هذه الجلسة** من جلسات سابقة غير متعلقة، لم تُلمَس هنا).

`saas` نفسها (`models.py`/`repository.py`/`service.py`) **مش** من الدومينات الـ8 الممنوعة — هي طبقة الخدمة المشتركة اللي كل الدومينات الـ8 (بما فيها insurance) بتستدعيها، وإضافة method جديدة ليها (بدون تعديل `check_feature_access`/`can_access_service` الموجودين) لا تُعتبر "لمس دومين تاني".

---

## 2. محتوى التغييرات كامل (diff فعلي، منسوخ حرفيًا)

### 2.1 `app/domains/saas/models.py` — موديل ORM جديد

```diff
     id = Column(Integer, primary_key=True, index=True)
-    service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=False, index=True)
+    service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=True, index=True)
     name = Column(String(100), nullable=False)
     code = Column(String(50), nullable=False)
 ...
     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


+class PlanServiceAccess(Base):
+    """جدول ربط many-to-many بين ServicePlan وServiceCatalog — بديل
+    تدريجي (Expand-Contract) عن الاعتماد على ServicePlan.features (نص حر
+    بلا schema enforcement) لتحديد الخدمات المتاحة لخطة معيّنة. راجع قرار
+    PROGRESS_LOG.md ([2026-09-07] — قرار تصميم: توحيد
+    check_feature_access/can_access_service عبر جدول many-to-many جديد)
+    وmigrations 046/047 (إنشاء الجدول + ondelete='RESTRICT' على الطرفين)."""
+    __tablename__ = "saas_plan_service_access"
+    __table_args__ = (
+        Index("ix_saas_plan_service_access_service_id", "service_id"),
+    )
+
+    plan_id = Column(Integer, ForeignKey("saas_service_plans.id", ondelete="RESTRICT"), primary_key=True)
+    service_id = Column(Integer, ForeignKey("saas_service_catalog.id", ondelete="RESTRICT"), primary_key=True)
+
+
 class TenantSubscription(Base):
```

**ملاحظة:** `service_id nullable=True` هنا هو نفس التعديل اللي كان مطلوبًا
ومُنفَّذًا فعليًا في جلسة migration 046 السابقة (`saas-plan-service-access-migration-session-log.md`)
— ظاهر في الـdiff هنا لأنه لسه مش committed، مش تعديل جديد في هذه الجلسة.

### 2.2 `app/domains/saas/repository.py` — دالة repo جديدة

```python
    async def get_active_subscription_via_plan_access(
        self,
        tenant_id: int,
        service_id: int,
    ) -> Optional[TenantSubscription]:
        """نفس شكل get_active_subscription بالضبط، لكن الربط بين
        الاشتراك والخدمة عبر saas_plan_service_access (many-to-many)
        بدل ServicePlan.service_id (FK وحيد). جزء من pilot دومين
        insurance فقط — راجع PROGRESS_LOG.md [2026-09-07]."""
        result = await self.db.execute(
            select(TenantSubscription)
            .join(PlanServiceAccess, PlanServiceAccess.plan_id == TenantSubscription.plan_id)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    PlanServiceAccess.service_id == service_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                )
            )
            .order_by(TenantSubscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
```

(+ إضافة `PlanServiceAccess` لقائمة الـimports من `app.domains.saas.models` أعلى الملف.)

### 2.3 `app/domains/saas/service.py` — دالتين جداد في `SaaSControlService`

```python
    async def has_any_active_subscription(self) -> bool:
        """هل عند الـtenant أي اشتراك ACTIVE/TRIAL (بغض النظر عن الخدمة)؟
        استُخرجت كدالة عامة صغيرة عشان دومينات زي insurance تقدر تفرّق بين
        'مفيش اشتراك خالص' و'عندك اشتراك بس مش لهذه الخدمة' من غير ما
        تعتمد على check_feature_access (اللي لسه بتفحص plan.features نص
        حر) ومن غير ما توصل مباشرة لـ.repo من خارج الكلاس."""
        subscriptions = await self.repo.get_all_active_subscriptions(self.tenant_id)
        return bool(subscriptions)

    async def can_access_service_via_plan(self, service_code: str) -> bool:
        """مثل can_access_service تمامًا في الشكل (بحث عن اشتراك
        ACTIVE/TRIAL مرتبط بخدمة معيّنة، إرجاع bool)، لكن الربط
        plan↔service هنا عبر saas_plan_service_access (many-to-many) بدل
        plan.features (نص حر بلا schema enforcement). مرحلة تجريبية
        (pilot) على دومين insurance فقط، بديل تدريجي لـcheck_feature_access
        — راجع PROGRESS_LOG.md ([2026-09-07] — قرار تصميم: توحيد
        check_feature_access/can_access_service عبر جدول many-to-many
        جديد).

        ⚠️ فرق متعمَّد عن can_access_service: هذه الدالة **لا** تتحقق من
        TenantServiceAccess (علم تفعيل الخدمة اليدوي للـtenant) — نطاقها
        مقصور على استبدال فحص plan.features الأصلي في check_feature_access
        فقط (اشتراك نشط ← خطة ← خدمة)، مش توسيع لمنطق can_access_service
        الكامل. لو احتجنا لاحقًا دمج الاثنين، ده قرار منفصل بعد ما باقي
        الدومينات الـ7 تتحول لنفس النمط."""
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False
        service_id = cast(int, service.id)
        subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
        return subscription is not None
```

### 2.4 `app/domains/insurance/service.py` — نقطة الاستدعاء الوحيدة اللي اتغيّرت (سطر 49 الأصلي)

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "insurance"):
+        # Pilot [2026-09-07]: بديل can_access_service_via_plan (جدول
+        # saas_plan_service_access many-to-many) بدل check_feature_access
+        # (plan.features نص حر) — راجع PROGRESS_LOG.md لتفاصيل القرار.
+        # check_feature_access نفسها لم تُلمَس، وباقي الدومينات الـ7 لسه
+        # عليها لحد ما تتحول كل واحدة بجلسة منفصلة.
         saas_service = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
+        if not await saas_service.has_any_active_subscription():
             raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        if not await saas_service.can_access_service_via_plan(feature):
             raise PermissionDeniedError("Insurance feature is not included in your current plan.")
```

رسائل الخطأ نفسها **لم تتغيّر حرفيًا** (`"No active subscription found."` /
`"Insurance feature is not included in your current plan."`) — الفرق فقط
في مصدر القرار (الجدول الجديد بدل `plan.features`)، مش في سلوك الـAPI
الظاهر للمستخدم.

---

## 3. بيانات الاختبار الحقيقية (Seed مباشر في dev DB — بدون migration)

نُفِّذ عبر `asyncpg` مباشرة على `eppne_v2` (نفس أسلوب الجلسات السابقة)،
داخل transaction واحدة:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة insurance حقيقية | `id=101`, `code='insurance'`, `name='التأمين السيادي (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=101`, `service_id=101`, `code='insurance-pilot-plan'`, **`features='[]'::jsonb`** (فاضية عمدًا — لإثبات إن القرار الجديد مش معتمد على أي نص فيها) |
| `saas_plan_service_access` | **الربط الفعلي عبر الجدول الجديد** | `(plan_id=101, service_id=101)` |
| `saas_tenant_subscriptions` | اشتراك ACTIVE حقيقي لتينانت 16 | `id=114`, `tenant_id=16`, `plan_id=101`, `status='ACTIVE'` |
| `sovereign_entities_v2` | كيان لازم لإنشاء بوليصة تحت تينانت 16 (لم يكن موجود أصلًا — الكيانات الأربعة الحالية كلها تحت tenant_id=1) | `id=30`, `name='PILOT-INSURANCE-ENTITY-TENANT16'`, `entity_type='ENTERPRISE'` |
| `insurance_policies` | بوليصة حقيقية تحت تينانت 16، `base_premium_mrusdt=0` (لتفادي الحاجة لرصيد محفظة فعلي في اختبار E2E) | `id=103`, `tenant_id=16`, `issuer_entity_id=30`, `policy_type='ACCIDENT'` |

**لماذا تينانت 16 لـ"معه صلاحية" وتينانت 1 لـ"من غيرها":** تينانت 1
(`Local Test Tenant`) كان أصلًا عنده اشتراك `ACTIVE` (id=2) على خطة
`P-SAAS9-VERIFY-PLAN-8fa402` (id=2) اللي حقل `features` بتاعها **يحتوي
النص `"insurance"` حرفيًا** (`["real_estate", "insurance"]`) رغم إنها خطة
اختبار لخدمة `p_saas9_verify_8fa402` مالهاش أي علاقة فعلية بالتأمين — هذا
بالظبط المثال المُستخدَم في التوثيق (`plan-service-mapping-data-audit-session-log.md`
§4.1) على عيب الاعتماد على نص حر. تينانت 1 كان تحت المنطق **القديم**
(`check_feature_access`) هيحصل على وصول insurance **خطأً** بسبب تطابق
نصي محض. اختياره لسيناريو "من غير صلاحية" يثبت عمليًا إن المنطق الجديد
(`can_access_service_via_plan`) بيرفض هذا الوصول الوهمي بشكل صحيح — وده
دليل حي على إصلاح العيب، مش بس اختبار محايد.

---

## 4. اختبار E2E حي — الطريقة

تشغيل السيرفر فعليًا (`uvicorn app.main:fastapi_app`, منفذ `8123` محلي
مؤقت لهذه الجلسة فقط، أُغلق في نهايتها) + طلبات HTTP فعلية بـ`curl` ضد
endpoint حقيقي (`POST /api/insurance/subscriptions`)، بمستخدمين حقيقيين
مسجَّلين دخول فعليًا (JWT حقيقي من `/api/identity/login`)، لا mocks ولا
استدعاء دوال مباشر بمعزل عن الـHTTP layer.

**المستخدمون المُستخدَمون** (من `.claude/reports/throwaway-test-users.md`
— ملف throwaway users المُعاد استخدامه، لم يُحدَّث لأن كلمة السر
اشتغلت من أول محاولة):

| المستخدم | tenant_id | كلمة السر | الدور في الاختبار |
|---|---|---|---|
| `TEST_super_a` (id=772) | 1 | `TEST_pass_batch3_2026` | تينانت **من غير** صلاحية insurance |
| `TEST_instr_b` (id=774) | 16 | `TEST_pass_batch3_2026` | تينانت **معه** صلاحية insurance |

**ملاحظة سياقية (غير مُستغَلة، للتوضيح فقط):** `POST /api/insurance/subscriptions`
بيحدد `tenant_id` من `get_current_tenant` (هيدر `X-Tenant-ID`، افتراضي=1،
غير مرتبط بالـJWT — نفس الثغرة الموثَّقة في `PROJECT_AUDIT.md` §5.1، غير
مُصلَحة، **خارج نطاق هذه الجلسة تمامًا**)، مش من `tenant_id` بتاع
المستخدم نفسه في التوكن. في اختبارنا كل مستخدم استخدم هيدر `X-Tenant-ID`
**المطابق لتينانته الحقيقي** (16 لـ`TEST_instr_b`، 1 لـ`TEST_super_a`) —
لم نستغل هذه الثغرة لتزييف هوية، لكن يستاهل التوضيح إن قيمة `tenant_id`
في هذا الـendpoint مصدرها الهيدر تقنيًا.

---

## 5. نتيجة الاختبار 1 — تينانت **معه** صلاحية insurance → متوقَّع نجاح

```
POST /api/insurance/subscriptions
Authorization: Bearer <JWT لـTEST_instr_b>
X-Tenant-ID: 16
Content-Type: application/json

{"policy_id":103,"subscriber_user_id":774,"start_date":"2026-09-07T00:00:00Z"}
```

**أول محاولة فعلية فشلت** (تفصيلها في §6 — سطر واحد مُصلَح)، **بعد
الإصلاح، النتيجة الفعلية:**

```
HTTP_STATUS: 201
{
  "policy_id": 103,
  "subscriber_user_id": 774,
  "fleet_id": null,
  "land_asset_id": null,
  "project_id": null,
  "bio_asset_id": null,
  "shipment_id": null,
  "employment_contract_id": null,
  "beneficiaries_json": {},
  "start_date": "2026-09-07T00:00:00Z",
  "end_date": null,
  "id": 88,
  "status": "ACTIVE",
  "policy_nft_id": "INS-103-774-4A1D8351",
  "subscription_tx_hash": "SUB-C5820500743A",
  "created_at": "2026-09-06T23:13:33.136031Z",
  "updated_at": "2026-09-06T23:13:33.136031Z"
}
```

**✅ نجح فعليًا (201 Created، اشتراك حقيقي اتسجَّل بـid=88)** — يعني
`can_access_service_via_plan("insurance")` رجعت `True` لتينانت 16، بناءً
فقط على صف `saas_plan_service_access` الجديد، مش أي نص في `features`.

---

## 6. اكتشاف ومفاجأة أثناء الاختبار 1 (قبل النجاح)

**أول محاولة** لنفس الطلب فوق رجعت:

```
HTTP_STATUS: 404
{"detail":"Policy not found or inactive","code":"NotFoundError"}
```

**السبب (تأكَّد بالتحقيق الفعلي):** `InsuranceRepository.get_policy()`
(`app/domains/insurance/repository.py:35`) بيفلتر
`InsurancePolicy.is_deleted == False` صراحة. عمود `is_deleted` في
الموديل معرَّف `Column(Boolean, default=False)` — لكن `default=` في
SQLAlchemy هو **قيمة افتراضية على مستوى الـORM فقط** (تُطبَّق وقت إنشاء
كائن Python عبر `session.add()`)، **مش** `server_default` على مستوى
الـDB. الـINSERT المباشر بتاعي عبر `asyncpg` (خارج ORM تمامًا) ماكانش
بيحدد `is_deleted` صراحة، فرجعت `NULL` فعليًا في العمود — والفلتر
`is_deleted == False` في SQL **بيستبعد `NULL`** (مقارنة `NULL = false`
ترجع `NULL`/unknown، مش `true`)، فالسياسة رجعت "مش موجودة" رغم وجودها
فعليًا بـ`is_active=true`.

**الإصلاح (بيانات فقط، مش كود):**
```sql
UPDATE insurance_policies SET is_deleted = false WHERE id = 103;
```
بعدها الطلب نجح فورًا (201، تفصيله في §5). **هذا مش باج في الكود** —
سلوك متوقَّع ومعروف لـSQLAlchemy `default=` مقابل `server_default=`؛
بس يستاهل توثيق لأي جلسة seed مستقبلية عبر SQL خام تلمس جداول فيها أعمدة
بـORM-side default بس (زي `is_deleted`, `is_active` في موديلات كتير في
المشروع) — لازم تحديدها صراحة في أي INSERT خام، مش الاعتماد على
الـmodel default.

---

## 7. نتيجة الاختبار 2 — تينانت **من غير** صلاحية insurance → متوقَّع رفض

```
POST /api/insurance/subscriptions
Authorization: Bearer <JWT لـTEST_super_a>
X-Tenant-ID: 1
Content-Type: application/json

{"policy_id":103,"subscriber_user_id":772,"start_date":"2026-09-07T00:00:00Z"}
```

**النتيجة الفعلية (نفس النتيجة بالضبط في محاولتين منفصلتين، قبل وبعد
إصلاح §6 — غير متأثرة بيه لأن الفشل بيحصل في `_check_saas_limits` قبل
ما الكود يوصل لسطر `get_policy` أصلًا):**

```
HTTP_STATUS: 403
{"detail":"Insurance feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة واضحة ومطابقة للرسالة الأصلية في الكود)** —
تينانت 1 عنده اشتراك `ACTIVE` فعلي (id=2)، فـ`has_any_active_subscription()`
رجعت `True` (مافيش رفض بسبب "no active subscription")، لكن
`can_access_service_via_plan("insurance")` رجعت `False` بشكل صحيح لأن
خطته (id=2) **مش** موجودة في `saas_plan_service_access` لخدمة insurance
الحقيقية (id=101) — **رغم إن `features` بتاع نفس الخطة يحتوي النص
`"insurance"` حرفيًا** (راجع §3). هذا يثبت حيًا إن المنطق الجديد ما عادش
عرضة لتطابق نصي زائف كان المنطق القديم (`check_feature_access`) هيقع
فيه.

---

## 8. فحص ارتداد (regression) — مجموعة الاختبارات الموجودة

```
pytest tests/test_realestate_insurance_savepoint.py -q
```

**النتيجة:** `1 failed, 7 passed, 1 xfailed`.

الفشل الوحيد: `test_realestate_buy_fractional_ownership_invoice_ordering`
— حارس بنيوي (source-order assertion) على
`RealEstateService.buy_fractional_ownership` (ترتيب `try/except` حول
`create_invoice()`). **تأكَّد إنه غير متعلق بهذه الجلسة إطلاقًا:**
- الدالة دي في `app/domains/realestate/service.py` — ملف لم يُلمَس ولا
  حرف فيه في هذه الجلسة (تأكَّد بـ`git diff`/`git status`، الملفات
  المتأثرة الوحيدة مذكورة في §1).
- الاختبارات الستة التانية الخاصة بـ`insurance` تحديدًا في نفس الملف
  (`test_insurance_subscribe_invoice_ordering`,
  `test_insurance_review_claim_invoice_ordering`, وغيرهم) **نجحوا كلهم**
  — يعني التعديل في `insurance/service.py` (استبدال `_check_saas_limits`)
  ماكسرش أي حارس بنيوي موجود لنفس الدومين.

هذا فشل realestate موجود مسبقًا (drift غير مرتبط)، مش نتيجة لأي تعديل في
هذه الجلسة — مذكور هنا للشفافية فقط، بدون أي إصلاح له (خارج النطاق
الصريح: "ممنوع لمس أي دومين تاني من الـ7 الباقيين").

---

## 9. ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين insurance فقط | ✅ الملفات المتأثرة: `insurance/service.py` + `saas/{models,repository,service}.py` (طبقة مشتركة، مش أحد الـ8) |
| ممنوع لمس أي دومين من الـ7 الباقيين | ✅ تأكَّد صفريًا عبر `git diff`/`git status` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل سطر واحد فيها — لسه موجودة بالضبط زي ما كانت، مُستخدَمة من الـ7 دومينات الباقيين |
| ممنوع أي حذف عمود | ✅ صفر `DROP COLUMN` — كل التعديلات إضافة (موديل/method/بيانات) |
| بيانات اختبار حقيقية عبر seed/insert مباشر، مش migration | ✅ كل الـ6 صفوف في §3 عبر `asyncpg` مباشر، بلا أي ملف migration جديد في هذه الجلسة |
| اختبار حي E2E حقيقي (مش tsc/import) | ✅ سيرفر uvicorn فعلي + طلبات HTTP فعلية + مستخدمين مسجَّلين دخول فعليًا + status codes وresponses فعلية موثَّقة كاملة (§5, §7) |

**الحالة النهائية:** pilot ناجح على دومين `insurance` وحده. الـ7 دومينات
الباقيين (`employment`, `digital_twin`, `arbitration_syndicates`,
`realestate`, `manufacturing`, `logistics`, `invitations`) لسه بتستخدم
`check_feature_access` القديمة زي ما هي — تحويلها يحتاج 7 جلسات منفصلة
بنفس النمط، كل واحدة بموافقة صريحة على حدة.
