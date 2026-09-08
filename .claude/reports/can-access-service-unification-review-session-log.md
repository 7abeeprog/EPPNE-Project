# تقرير جلسة — مراجعة قبل أي تنفيذ: `can_access_service` + خريطة backfill المقترح لـ`saas_plan_service_access`

**تاريخ الجلسة:** 2026-09-07
**النطاق:** فحص read-only بحت. **صفر تنفيذ في هذه الجلسة** — لا تعديل كود،
لا migration، لا backfill فعلي، لا أي INSERT/UPDATE على أي جدول. الهدف
عرض الصورة الكاملة (كود `can_access_service` الحالي + الفرق الفعلي بين
حالة `saas_service_plans`/`saas_plan_service_access` الآن) قبل اتخاذ أي
قرار تنفيذ.

---

## 1. كود `can_access_service` الحالي كامل (بدون تلخيص)

**المسار الكامل:** `E:\cc\eppne-backend\app\domains\saas\service.py`
(السطور 328–350، داخل `class SaaSControlService`)

```python
    async def can_access_service(self, service_code: str) -> bool:
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        service_id = cast(int, service.id)
        access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
        if access is None or not cast(bool, access.is_active):
            return False

        subscription = await self.repo.get_active_subscription(self.tenant_id, service_id)
        if subscription is None:
            return False

        if subscription.status == "PAST_DUE":
            grace_end = subscription.grace_period_end_date
            if grace_end is not None and datetime.now(timezone.utc) < grace_end:
                return True
            else:
                await self.repo.update_subscription_status(cast(int, subscription.id), self.tenant_id, "EXPIRED")
                return False

        return subscription.status in ["ACTIVE", "TRIAL"]
```

**ملاحظات على القراءة الحرفية (للسياق فقط، بدون أي تعديل):**
- بتتحقق من **إشارتين مستقلتين**: (1) `TenantServiceAccess` (علم تفعيل
  يدوي للخدمة عند التينانت، عبر `get_tenant_service_access`)، **و**(2)
  اشتراك نشط مرتبط بالخدمة عبر `get_active_subscription(tenant_id,
  service_id)` — واللي بدورها بتربط عن طريق `ServicePlan.service_id`
  (الـFK الوحيد القديم)، **مش** عبر `saas_plan_service_access` الجديد.
- فرع `PAST_DUE` (سطور 342-348) غير قابل للوصول فعليًا حاليًا: الاستعلام
  جوه `get_active_subscription` (`repository.py:133-151`) بيفلتر
  `status.in_(["ACTIVE", "TRIAL"])` بالفعل، فمستحيل يرجع صف بحالة
  `PAST_DUE` أصلًا ليدخل الشرط في سطر 342. ملاحظة قراءة فقط — مش جزء من
  طلب هذه الجلسة، ومذكورة هنا للأمانة لأنها ظهرت أثناء القراءة الحرفية.

---

## 2. حالة `saas_service_plans` (service_id NOT NULL) مقابل `saas_plan_service_access`

الاستعلام المنفَّذ (read-only، `SELECT`/`EXISTS` فقط، لا كتابة):

```sql
SELECT sp.id AS plan_id, sp.service_id, sp.name AS plan_name, sp.code AS plan_code,
       sc.name AS service_name, sc.code AS service_code,
       EXISTS (
           SELECT 1 FROM saas_plan_service_access psa
           WHERE psa.plan_id = sp.id AND psa.service_id = sp.service_id
       ) AS already_linked
FROM saas_service_plans sp
LEFT JOIN saas_service_catalog sc ON sc.id = sp.service_id
WHERE sp.service_id IS NOT NULL
ORDER BY sp.id;
```

**نتيجة العدّ العام (dev DB، لحظة الجلسة):**
- إجمالي صفوف `saas_service_plans`: **7**
- منها بـ`service_id IS NULL`: **0** (كل الصفوف الحالية لسه `service_id` معبّى — لا يوجد أي صف استفاد فعليًا من `nullable=True` بعد)
- صفوف موجودة حاليًا في `saas_plan_service_access`: **1** (الصف الوحيد اللي اتضاف يدويًا في جلسة pilot دومين insurance السابقة، مش backfill)

### الجدول الكامل (كل الـ7 صفوف):

| plan_id | service_id | plan_name | plan_code | service_name | service_code | موجود بالفعل في `saas_plan_service_access`؟ |
|---|---|---|---|---|---|---|
| 2 | 2 | P-SAAS9-VERIFY-PLAN-8fa402 | `p_saas9_plan_8fa402` | P-SAAS9-VERIFY-CATALOG-8fa402 | `p_saas9_verify_8fa402` | ❌ لا |
| 47 | 47 | TEST_REQSECTOR_ACADEMY_PLAN | `test_reqsector_academy_plan` | TEST_REQSECTOR_SESSION_ACADEMY_SERVICE | `academy` | ❌ لا |
| 48 | 48 | TEST_REQSECTOR_AFFILIATE_PLAN | `test_reqsector_affiliate_plan` | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE | `affiliate` | ❌ لا |
| 77 | 74 | TEST plan tenders | `test-tenders` | المزادات والمناقصات - مناقصات | `tenders` | ❌ لا |
| 78 | 75 | TEST plan auctions | `test-auctions` | المزادات والمناقصات - مزادات | `auctions` | ❌ لا |
| 99 | 48 | الخطة الافتراضية (مجانية) | `default` | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE | `affiliate` | ❌ لا |
| 101 | 101 | خطة التأمين التجريبية (Pilot) | `insurance-pilot-plan` | التأمين السيادي (Pilot) | `insurance` | ✅ نعم (صف موجود فعلًا) |

---

## 3. بالظبط أي صفوف هيتضافوا لو نُفِّذ backfill بمنطق "لكل `(plan_id, service_id)` من `saas_service_plans` حيث `service_id IS NOT NULL` وغير موجود بالفعل، ضيفه في `saas_plan_service_access`"

**6 صفوف بالضبط** (كل الجدول فوق ماعدا `plan_id=101` اللي موجود بالفعل):

```sql
INSERT INTO saas_plan_service_access (plan_id, service_id) VALUES
  (2, 2),
  (47, 47),
  (48, 48),
  (77, 74),
  (78, 75),
  (99, 48);
```

**ملاحظة مهمة على الصف `(99, 48)` و`(48, 48)` معًا:** الخدمة `service_id=48`
(`affiliate`) هيبقى ليها **صفّان** في `saas_plan_service_access` بعد
البackfill (واحد لكل خطة: `plan_id=48` و`plan_id=99`) — ده متوقَّق مع
تصميم many-to-many نفسه (خدمة واحدة ممكن يكون ليها أكتر من خطة)، مش خطأ
في الاستعلام، لكن يستاهل تأكيد بشري قبل التنفيذ لأنه أول حالة فعلية بـ
"أكتر من صف لنفس الخدمة" في الجدول الجديد.

**لم يُنفَّذ أي INSERT من الستة دول في هذه الجلسة** — الجدول فوق تمامًا
هو ناتج الاستعلام الفعلي، معروض للمراجعة فقط.

---

## 4. الحالة النهائية وقت انتهاء الجلسة

- `saas_plan_service_access`: لسه فيه صف واحد بس (نفس اللي كان موجود من
  جلسة pilot insurance السابقة) — **لم يتغيّر أبدًا في هذه الجلسة**.
- `saas_service_plans`/`saas_service_catalog`: لم يُلمَسوا إطلاقًا (لا
  INSERT ولا UPDATE ولا DELETE).
- لا تعديل على أي ملف كود (`.py`) ولا أي migration في هذه الجلسة.

**القرار (تنفيذ الـbackfill من عدمه، ومعالجة حالة `service_id=48`
المزدوجة) متروك بالكامل لجلسة تالية بعد مراجعة هذا التقرير.**
