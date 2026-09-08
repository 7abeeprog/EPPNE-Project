# Phase 10 — التقرير الكامل لدومين affiliate (مراجعة أمنية + جرد وظيفي + تناغم Backend/Frontend)

> **المنهجية:** قراءة كاملة فعلية لكل ملفات الدومين
> (`router.py`, `service.py`, `repository.py`, `schemas.py`, `models.py`)،
> زائد الملفات المرتبطة فعليًا (`api/deps.py`, `core/rate_limiter.py`,
> `core/celery_config.py`, `tasks/affiliate.py`, `tasks/commerce.py`,
> `domains/commerce/service.py`, `domains/commerce/repository.py`,
> `domains/commerce/models.py`, `domains/saas/service.py`, `main.py`)
> + كل ملفات الفرونت إند المستهلِكة (`services/affiliate.service.ts`,
> `hooks/affiliate/useAffiliate.ts`, `app/(dashboard)/affiliate/page.tsx`,
> `components/affiliate/ShareButton.tsx`, `components/layout/sidebar.tsx`).
> **read-only بالكامل من ناحية كود التطبيق — صفر تعديل على أي ملف من
> ملفات المشروع.** أول محاولة تحقق ديناميكي (قراءة `openapi()['paths']`
> عبر استيراد `app.main` بدون سيرفر حي) عُلِّقت بطلب المستخدم بعد أن
> تسبَّبت في hang، والاعتماد كان بالكامل على قراءة الكود الثابت في أول
> الجلسة. **لاحقًا، بموافقة صريحة منفصلة من المستخدم لبند واحد محدَّد
> (فحص authz على endpoint إداري في affiliate)، تم فعليًا: تشغيل سيرفر
> `uvicorn` محلي حقيقي متصل بـPostgres/Redis حقيقيين (نفس containers
> Phase 9، `eppne_db` بورت 5435، `redis` بورت 6380)، إنشاء بيانات اختبار
> throwaway (tenant تجريبي id=5، مستخدم `SUPER_ADMIN` تجريبي id=15 تحت
> tenant الحقيقي id=1، صف `CommissionTier` تجريبي)، وتنفيذ طلبات HTTP
> حقيقية ضدها.** هذا التحقق الحي كشف اكتشافًا جوهريًا غير متوقَّع (باج
> `SimpleTenant` — انظر تحت) لم يكن ظاهرًا من القراءة الثابتة وحدها.
> كل استنتاج أدناه مُعلَّم صراحة بنوعه: "مؤكَّد من الكود" (semantics
> بايثون/FastAPI ثابتة)، أو "مؤكَّد بالتنفيذ الفعلي" (طلب HTTP حقيقي +
> traceback حقيقي من السيرفر + تحقق DB مباشر)، أو "يحتاج تحقق حي لاحق".
> **بيانات الاختبار لسه موجودة في القاعدة وقت كتابة هذا السطر — التنظيف
> لم يتم بعد، انظر قسم "حالة بيانات الاختبار" في آخر التقرير.**

---

## ملخص تنفيذي

| # | المشكلة | الخطورة | الحالة |
|---|---------|---------|--------|
| **0** | **باج `SimpleTenant` (كائن بدل `int`) — كل الـ15 endpoint في affiliate بترجع 500 لأي طلب، بغض النظر عن صحة الهيدر أو المستخدم أو الاشتراك** | 🔴 **الأخطر في التقرير كله** | 🟢 **مؤكَّد بالتنفيذ الفعلي** (طلبين حقيقيين، traceback حقيقي، تحقق DB) — لسه قائم، لم يُصلَح |
| 1 | `require_subscription("affiliate")` مكسور بالكامل (خطأ في عدد المعاملات) — يُسقط 5 من 15 endpoint بـ 500 دائمًا (سبب إضافي مستقل، بيموت الطلب حتى قبل ما يوصل لبند 0) | 🔴 حرجة (كسر وظيفي كامل) | مؤكَّد من الكود، لسه قائمة |
| 2 | `@rate_limit(...)` غير فعّال فعليًا على 14 من 15 endpoint (كل واحد إلا المسار العام) بسبب غياب `Request` من توقيع الدالة | 🔴 حرجة (أمنية صامتة) | مؤكَّد من الكود، لسه قائمة |
| 3 | `X-Tenant-ID` بلا تفويض على الـ4 endpoints الإدارية (tiers/bulk-release) — سوبر يوزر من tenant تاني يقدر (نظريًا) يعدّل/يفرج عمولات tenant مش بتاعه | 🟠 عالية | 🚫 **غير قابلة للفحص/الاستغلال الحي حاليًا — محجوبة تمامًا ببند 0 (انظر التوضيح تحت)**، لسه قائمة كعيب في الكود |
| 4 | `withdraw_commissions`: `sender_id=1` مُثبَّت (hardcoded) بلا فحص ملكية/tenant للمرسل — كل عمليات السحب لكل الـtenants بتسحب من نفس محفظة المستخدم رقم 1 | 🟠 عالية | مؤكَّد من الكود، لسه قائمة (غير قابل للفحص الحي حاليًا لنفس سبب بند 0) |
| 5 | `distribute_commissions` (محرك توزيع العمولات في دومين affiliate نفسه) **كود ميت بالكامل** — لا يُستدعى من أي مسار حي؛ الآلية الفعلية في الإنتاج منفصلة تمامًا في دومين `commerce` | 🔴 حرجة (فجوة وظيفية جوهرية) | مؤكَّد من الكود، لسه قائمة |
| 6 | `app/tasks/affiliate.py` (3 مهام Celery) مكسورة بالكامل (توقيعات لا تطابق `AffiliateService`/`AffiliateRepository` الحاليين) + غير مُستدعاة من أي مكان أصلاً | 🔴 حرجة (كود ميت مكسور) | مؤكَّد من الكود، لسه قائمة |
| 7 | **كل** استدعاءات `services/affiliate.service.ts` بمسارات مزدوجة (`/affiliate/affiliate/...`) لا تطابق أي مسار حقيقي في الباك إند | 🔴 حرجة (تناغم Backend/Frontend) | مؤكَّد من الكود، لسه قائمة |
| 8 | `hooks/affiliate/useAffiliate.ts` يستدعي دوال غير موجودة أصلاً (`getDashboardStats`, `getTree`) + توقيعات معاملات خاطئة (`getLinks`, `getCommissions`) | 🔴 حرجة | مؤكَّد من الكود، لسه قائمة |
| 9 | كل روابط التنقل الفرعية لصفحة affiliate (وللسايدبار) تشير لمسارات فرونت إند غير موجودة (`/affiliate/links`, `/tree`, `/commissions`, `/withdraw`, `/guidelines`) | 🟠 عالية | مؤكَّد من الكود، لسه قائمة |
| 10 | `get_or_create_profile` قد يرمي `IntegrityError` غير معالَج (500) لو هيدر `X-Tenant-ID` يخالف الـtenant الحقيقي لمستخدم عنده ملف بالفعل | 🟡 متوسطة | مؤكَّد من الكود، لسه قائمة (غير قابل للفحص الحي حاليًا لنفس سبب بند 0 — الطلب هيتعطل بباج SimpleTenant قبل ما يوصل لمسار IntegrityError) |

**ملاحظة نطاق مُحدَّثة:** أغلب البنود مؤكَّدة من قراءة الكود الثابت.
**بند 0 مؤكَّد بالتنفيذ الفعلي الحي** (سيرفر uvicorn حقيقي + Postgres/Redis
حقيقيين + طلبات HTTP حقيقية + بيانات اختبار throwaway، بموافقة صريحة
من المستخدم لهذا البند تحديدًا). هذا التحقق الحي **صحَّح خطأ في وصفي
الأصلي** لسلوك `get_current_tenant` (كنت افترضت إنها بترجع int مباشر —
غلط، بترجع كائن `SimpleTenant`)، وكشف إن البند 0 **يحجب** إمكانية فحص
بند 3 (وأي بند تاني بيحتاج طلب ناجح يوصل لطبقة الـDB) حيًا حتى يتصلح.

---

## المخرج 1: التقرير الأمني

### مصفوفة authz لكل الـ15 endpoint

| Method | Path | الـdependency | فحص tenant_id فعلي وقت الاستعلام؟ | rate limit فعّال؟ |
|---|---|---|---|---|
| GET | `/affiliate/profile` | `get_current_active_user` | ✅ (`user_id AND tenant_id` في `AffiliateRepository`) | ❌ (لا `Request` بالتوقيع) |
| PUT | `/affiliate/profile` | `get_current_active_user` | ✅ | ❌ |
| POST | `/affiliate/links` | `require_subscription("affiliate")` **[مكسور — انظر ثغرة 1]** | ✅ (لو وصل الكود، ما بيوصلش) | ❌ |
| GET | `/affiliate/links` | `get_current_active_user` | ✅ (join مع `AffiliateProfile.tenant_id`) | ❌ |
| PATCH | `/affiliate/links/{id}` | `require_subscription("affiliate")` **[مكسور]** | ✅ (لو وصل) | ❌ |
| GET | `/affiliate/commissions` | `require_subscription("affiliate")` **[مكسور]** | ✅ (لو وصل) | ❌ |
| POST | `/affiliate/commissions/release` | `require_subscription("affiliate")` **[مكسور]** | ✅ (لو وصل) | ❌ |
| POST | `/affiliate/withdraw` | `require_subscription("affiliate")` **[مكسور]** | ⚠️ (المستلم مفحوص، المرسل `id=1` غير مفحوص tenant — انظر ثغرة 4) | ❌ |
| GET | `/affiliate/stats` | `get_current_active_user` | ✅ | ❌ |
| GET | `/affiliate/tree` | `get_current_active_user` | ✅ | ❌ |
| GET | `/affiliate/track/{code}` | **بدون مصادقة** (`get_current_tenant` فقط، هيدر افتراضي=1) | ✅ داخل نطاق الـtenant المُحدَّد بالهيدر (لكن الهيدر نفسه غير موثوق — بالتصميم، endpoint عام) | ✅ (الوحيد اللي بيصرّح `request: Request`) |
| GET | `/affiliate/admin/tiers` | `get_current_superuser` | ✅ لكن الـtenant من الهيدر بلا تحقق تطابق مع tenant السوبريوزر — انظر ثغرة 3 | ❌ |
| PUT | `/affiliate/admin/tiers` | `get_current_superuser` | ⚠️ نفس ثغرة 3 | ❌ |
| POST | `/affiliate/admin/tiers/product` | `get_current_superuser` | ⚠️ نفس ثغرة 3 | ❌ |
| POST | `/affiliate/admin/commissions/bulk-release` | `get_current_superuser` | ⚠️ نفس ثغرة 3 (+ تأثير مالي مباشر) | ❌ |

**كل الـrouter مسجَّل في `main.py` عبر `routers_config` بـ
`dependencies=[Depends(require_sector("affiliate"))]` (سطر 269، 302-308)
— طبقة حماية إضافية عامة تتطلب أن يكون للمستخدم `sector` أو دور مسموح،
مؤكَّدة من الكود، لم تُختبَر حيًا في هذه الجلسة.**

---

### 🔴 البند 0 (الأخطر في التقرير كله، مؤكَّد بالتنفيذ الفعلي): باج `SimpleTenant` — كل الـ15 endpoint بترجع 500 لأي طلب، مهما كان الهيدر صحيح

**هذا البند اكتُشف أثناء محاولة فحص ثغرة 3 (X-Tenant-ID) حيًا بموافقة
صريحة من المستخدم، وقلب نتيجة الفحص بالكامل.**

#### الوصف من الكود (`api/deps.py:144-153`)

```python
class SimpleTenant:
    id: int

async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant                    # ⬅️ بيرجع الكائن نفسه، مش .id
```

`get_current_tenant` بترجع **كائن** `SimpleTenant` بيحمل القيمة جوه
خاصية `.id`، **مش القيمة كـ`int` مباشر.** كل الـ15 endpoint في
`affiliate/router.py` (فحص شامل بـ`grep`، 15 موضع بلا استثناء) بيعلنوا:
```python
tenant_id: int = Depends(get_current_tenant),   # ⬅️ type hint تزييني فقط
...
service = AffiliateService(db, tenant_id)        # ⬅️ الكائن الخام بيتمرر هنا
```
FastAPI **لا يفرض** تطابق النوع المُعلَن (`int`) مع القيمة الفعلية
الراجعة من الـDepends — بيمرر اللي الدالة رجعته زي ما هو. يعني
`tenant_id` اللي بيوصل لـ`AffiliateService.__init__` هو كائن
`SimpleTenant` خام، مش رقم. من هناك بيتخزن في `self.tenant_id` وينتشر
لكل استدعاءات `AffiliateRepository` كـbind parameter في استعلامات
SQLAlchemy (`Model.tenant_id == tenant_id`).

**تصحيح صريح لخطأ سابق مني:** في وصفي الأول لثغرة 3 كتبت إن
`get_current_tenant` "بيرجع الرقم من الهيدر كما هو" — ده غلط. الدالة
بترجع الكائن الحاوي للرقم، مش الرقم نفسه.

#### التحقق العملي الأول (مؤكَّد بالتنفيذ الفعلي): `PUT /admin/tiers` بهيدر مخالف

**الإعداد:** سيرفر `uvicorn` محلي حقيقي (`127.0.0.1:8000`) متصل
بـPostgres حقيقي (`eppne_db`, بورت 5435) وRedis حقيقي (`redis`, بورت
6380). بيانات اختبار throwaway: tenant تجريبي `id=5`، مستخدم
`SUPER_ADMIN` تجريبي `id=15` (تحت tenant حقيقي `id=1`)، صف
`CommissionTier` تجريبي تحت tenant `id=5` (`level_1_pct=13.37`).

```
POST /api/identity/login HTTP/1.1
X-Tenant-ID: 1
{"username_or_email":"phase10_audit_superadmin@example.com","password":"Phase10AuditPass123!"}
```
```
HTTP/1.1 200 OK
{"access_token":"...","user_id":15,"user":{"system_role":"SUPER_ADMIN","tenant_id":1,...}}
```

```
PUT /api/affiliate/admin/tiers HTTP/1.1
Cookie: access_token=<JWT صالح، tenant_id=1 داخل التوكن>
X-Tenant-ID: 5   ⬅️ مخالف عمدًا لـtenant المستخدم الحقيقي (1)
{"level_1_pct": 42.5}
```
```
HTTP/1.1 500 Internal Server Error
```

**الـtraceback الحقيقي من لوج السيرفر:**
```
File "app/domains/affiliate/repository.py", line 237, in get_commission_tiers
  result = await self.db.execute(...)
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error)
<class 'asyncpg.exceptions.DataError'>: invalid input for query argument $1:
<app.api.deps.SimpleTenant object at 0x...>
('SimpleTenant' object cannot be interpreted as an integer)
[SQL: ... WHERE affiliate_commission_tiers.tenant_id = $1::INTEGER ...]
[parameters: (<app.api.deps.SimpleTenant object at 0x...>, 'GLOBAL')]
```

#### التحقق العملي الثاني (مؤكَّد بالتنفيذ الفعلي): نفس النتيجة بهيدر **صحيح 100%**

عشان أعزل هل المشكلة في *مخالفة* الهيدر أو في *أي* هيدر، اتعمل طلب
تاني بـ`X-Tenant-ID: 1` (مطابق تمامًا للـtenant الحقيقي للمستخدم) على
`GET /affiliate/profile` (endpoint بسيط، بلا `require_subscription`):

```
GET /api/affiliate/profile HTTP/1.1
Cookie: access_token=<نفس الجلسة>
X-Tenant-ID: 1   ⬅️ مطابق تمامًا هذه المرة
```
```
HTTP/1.1 500 Internal Server Error
```

**نفس النتيجة بالضبط.** هذا يثبت قطعيًا إن الباج **مالوش أي علاقة
بتطابق أو عدم تطابق الهيدر** — كل طلب لأي affiliate endpoint هيفشل
بـ500، من أي مستخدم، بأي هيدر، صح أو غلط.

#### تحقق DB (read-only): تأكيد عدم حدوث أي كتابة جزئية

```sql
SELECT id, tenant_id, entity_type, target_product_id, level_1_pct
FROM affiliate_commission_tiers WHERE tenant_id = 5;
-- (1, 5, 'GLOBAL', None, Decimal('13.37'))   ⬅️ نفس القيمة الأصلية، لم تتغيّر
```
الطلب انهار وقت الـ`SELECT` الأول (`get_commission_tiers`)، قبل ما
يوصل لأي `UPDATE` — صفر تأثير جزئي على البيانات.

#### فحص إضافي مطلوب صراحة من المستخدم: هل فيه bypass صامت بديل (مقارنة `==` مباشرة بدل `.id`) بدل الـcrash؟

فحص شامل بـ`grep` لكل استخدام لـ`tenant_id`/`tenant` القادم من
`get_current_tenant` في **كل** ملفات دومين affiliate (`router.py`،
`service.py`، `repository.py` — 39 موضع إجمالي: 15 في router.py + 24
مقارنة `== tenant_id` في service.py/repository.py):

**النتيجة: صفر حالة bypass صامت.** كل موضع بلا استثناء من النوعين
التاليين فقط:
1. `router.py` (15 موضع): `tenant_id` بيتمرر مباشرة كـargument لـ
   `AffiliateService(db, tenant_id)` — صفر أي مقارنة Python مباشرة
   (`==`/`!=`/`in`/`is`) في `router.py` نفسه.
2. `service.py`/`repository.py` (24 موضع): كل الـ`== tenant_id` من
   الشكل `Model.tenant_id == tenant_id` — يعني الطرف الشمال دايمًا
   عمود SQLAlchemy مُعرَّف (`AffiliateProfile.tenant_id`،
   `Commission.tenant_id`، إلخ)، مش متغيّر Python عادي. مقارنة عمود
   SQLAlchemy مع أي قيمة (حتى كائن غريب زي `SimpleTenant`) **بترجع
   تعبير SQL (`BinaryExpression`) في وقت البايثون، مش `True`/`False`
   Python عادي** — يعني مفيش أي مسار منطقي ممكن يتجاوز بصمت (يرجع
   `True` غلط أو يتخطى شرط) بسبب النوع الغلط. **الفشل دايمًا صريح
   ولاحق (وقت تنفيذ الاستعلام الفعلي على DB)، مش صامت ولا مبكر.**

**الخلاصة على السؤال المحدَّد:** لا يوجد أي bypass صامت أخطر من الـ500
داخل `affiliate/router.py` (أو باقي ملفات الدومين) لنفس الباج — سلوك
الباج **موحَّد ومتوقَّع**: كل طلب لكل endpoint هيتعطل بنفس الشكل
بالظبط (500، DataError، وقت أول استعلام DB بيستخدم tenant_id).

#### العلاقة مع ثغرة 3 (X-Tenant-ID بلا تفويض) — توضيح صريح للـblocker

**ثغرة 3 (الموصوفة تحت) لسه موجودة فعليًا كعيب في الكود** — غياب أي
مقارنة بين `current_user.tenant_id` والـ`tenant_id` القادم من الهيدر
في الـ4 endpoints الإدارية — **لكنها حاليًا غير قابلة للفحص أو
الاستغلال الحي إطلاقًا**، لأن أي طلب (بهيدر صح أو غلط) بيتعطل ببند 0
**قبل** ما يوصل للنقطة اللي فيها مقارنة الـtenant كانت هتبقى مهمة.
بمعنى تاني: **بند 0 حاليًا بيمنع استغلال ثغرة 3 عمليًا، لكن بالصدفة
مش بالتصميم** — لو حد أصلح بند 0 مستقبلاً (بنفس نمط إصلاح identity
Phase 0: `tenant: SimpleTenant = Depends(get_current_tenant)` ثم
`tenant.id`) **من غير** ما يضيف فحص مطابقة tenant، ثغرة 3 هتبقى
قابلة للاستغلال فورًا من أول طلب ناجح. **هذا مش باج middleware** —
فُحصت كل الـ6 middleware المسجَّلة في `main.py` (trace-id, idempotency,
security headers, CORS, trusted hosts, performance) وولا واحد فيهم
له علاقة بـtenant_id. الإصلاح المطلوب على مستوى توقيع كل endpoint في
`affiliate/router.py` تحديدًا (أو الدالة الأعم `get_current_tenant`
نفسها، قرار معماري خارج نطاق هذا التقرير).

**نطاق أوسع محتمل (خارج affiliate، للسياق فقط):** نفس نمط
`tenant_id: int = Depends(get_current_tenant)` (بدل `tenant: SimpleTenant`
ثم `.id`) موجود على الأرجح في أي دومين تاني لسه مش اتصلح زي identity —
**لم يُفحص أي دومين تاني في هذه الجلسة، خارج نطاق Phase 10 صراحة.**

**الحالة:** 🔴 **لسه قائم، لم يُصلَح.** مؤكَّد بالتنفيذ الفعلي (طلبين
منفصلين، هيدر صحيح وهيدر مخالف، نفس النتيجة)، وبتحقق DB مباشر (صفر
كتابة جزئية).

---

### 🔴 ثغرة 1 (الأخطر وظيفيًا): `require_subscription("affiliate")` مكسور بالكامل — 5 endpoints ترجع 500 دائمًا

**من الكود (`app/api/deps.py:202-210`):**
```python
def require_subscription(service_code: str):
    async def subscription_checker(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        service = SaaSControlService(db)
        await service.check_and_enforce_access(current_user.tenant_id, service_code)
        return current_user
    return subscription_checker
```

**مقابل التوقيع الفعلي الحالي لـ`SaaSControlService` (`app/domains/saas/service.py:33-38`):**
```python
class SaaSControlService:
    def __init__(self, db: AsyncSession, tenant_id: int):   # ⬅️ tenant_id إجباري، بلا default
```
و`check_and_enforce_access` (`saas/service.py:229`):
```python
async def check_and_enforce_access(self, service_code: str):   # ⬅️ معامل واحد فقط
```

**النتيجة الحتمية (semantics بايثون ثابتة، مؤكَّدة 100% من قراءة الكود
بلا حاجة لتشغيل):**
- `SaaSControlService(db)` وحدها كافية لرفع
  `TypeError: __init__() missing 1 required positional argument: 'tenant_id'`
  **قبل** حتى الوصول لسطر `check_and_enforce_access`.
- حتى لو أُصلِح ده، `check_and_enforce_access(current_user.tenant_id, service_code)`
  هيرمي `TypeError` تاني (معاملين ممرَّرين مقابل معامل واحد متوقَّع).
- لا يوجد أي `exception_handler` عام لـ`TypeError`/`Exception` في
  `main.py` (فُحص — فقط `SovereignError`, `IdempotencyError`,
  `RateLimitError` مُسجَّلين، سطر 105/113/121) → الـTypeError هتتسرب
  كـ HTTP 500 قياسي من Starlette، بلا رسالة عربية مفهومة.

**الأثر:** أي طلب لأي من الـ5 endpoints دي —
`POST /links`, `PATCH /links/{id}`, `GET /commissions`,
`POST /commissions/release`, `POST /withdraw` — **هيفشل بـ 500 لأي
مستخدم، بغض النظر عن حالة اشتراكه فعليًا.** يعني عمليًا: إنشاء/تعديل
روابط الدعوة، عرض سجل العمولات، الإفراج عنها، وسحبها — **كل ده معطَّل
بالكامل حاليًا في الباك إند نفسه**، مش بس في الفرونت إند.

**نطاق أوسع (خارج affiliate، للسياق فقط):** نفس `require_subscription`
مُستخدَم أيضًا في دومين `academy` و`commerce` (مؤكَّد بـ`grep`) — يعني
هذا العطل، لو صحيح، مش خاص بـaffiliate وحده. **لم يُفحص أثر هذا على
الدومينين الآخرين في هذه الجلسة — خارج نطاق Phase 10.**

**الحالة:** 🔴 لسه قائمة، لم تُصلَح (خارج نطاق read-only لهذه الجلسة).

---

### 🔴 ثغرة 2: `@rate_limit(...)` غير فعّال فعليًا على 14 من 15 endpoint

**من الكود (`app/core/rate_limiter.py:14-23`):**
```python
async def wrapper(*args, **kwargs):
    request: Optional[Request] = kwargs.get("request")
    if not request:
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
    if not request:
        return await func(*args, **kwargs)   # ⬅️ تجاوز صامت، بلا أي تسجيل/تحذير
```

الديكوريتور بيحاول ياخد كائن `Request` من الـkwargs/args اللي FastAPI
بيمررها لدالة الـendpoint وقت التنفيذ. FastAPI بيحقن بس الـparameters
المُعلَنة صراحة في توقيع الدالة (وبيتعرَّف عليها عبر `inspect.signature`
اللي بيتبع `__wrapped__` من `functools.wraps` — يعني بيشوف التوقيع
الأصلي الصحيح، مش توقيع الـwrapper العام `*args, **kwargs`). **فحص
شامل لتوقيعات الـ15 endpoint في `affiliate/router.py`: endpoint واحد
بس (`track_referral_click`) بيُعلن `request: Request` صراحة في
توقيعه.** كل الباقي (14 endpoint) بيوقع `if not request` بـ`True`
دايمًا → **الديكوريتور بيرجع مباشرة لتنفيذ الدالة الأصلية بلا أي فحص
Redis أو حد أقصى للطلبات، بصمت تام وبلا أي أثر في اللوج.**

**الأثر الحقيقي:** كل الحدود المُعلَنة في الكود —
`@rate_limit(max_requests=5, window_seconds=300)` على `/withdraw`
و`/commissions/release` و`/admin/commissions/bulk-release` (أخطر
العمليات في الدومين، مالية بالكامل) — **زخرفية بحتة، بلا أي تطبيق
فعلي.** لا يوجد حد أقصى فعلي لعدد محاولات السحب أو الإفراج أو
bulk-release لأي مستخدم/سوبريوزر حاليًا.

**نمط عام محتمل:** بما إن الديكوريتور نفسه (مش كود affiliate) هو مصدر
المشكلة، هذا على الأرجح ينطبق على أي endpoint في أي دومين تاني بالمشروع
كله بيستخدم `@rate_limit` بدون `request: Request` بالتوقيع — **لم
يُفحص باقي الدومينات، خارج نطاق Phase 10.**

**الحالة:** 🔴 لسه قائمة، لم تُصلَح.

---

### 🟠 ثغرة 3: `X-Tenant-ID` بلا تحقق تفويض على الـ4 endpoints الإدارية

نفس الجذر التقني الموثَّق في Phase 9 لـidentity (`api/deps.py:148-153`،
`get_current_tenant` بياخد `X-Tenant-ID` مباشرة من الهيدر بلا استعلام
DB أو تحقق ملكية)، لكن بأثر مختلف هنا لأن affiliate عنده endpoints
إدارية بتعتمد **حصريًا** على هذا الهيدر لتحديد نطاق التعديل، بلا أي فحص
مقارنة مع tenant السوبريوزر الفعلي:

```python
@router.put("/admin/tiers", ...)
async def update_commission_tiers(
    data: CommissionTierUpdate,
    tenant_id: int = Depends(get_current_tenant),   # ⬅️ من الهيدر
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),  # ⬅️ يفحص الدور فقط، مش الـtenant
):
```

`get_current_superuser` (`api/deps.py:67-80`) بيفحص `system_role`
(`EXECUTIVE_DIRECTOR`/`SUPER_ADMIN`) بس — **بلا أي مقارنة بين
`current_user.tenant_id` والـ`tenant_id` القادم من الهيدر.** نفس الأمر
لـ`get_commission_tiers` (GET)، `create_product_tier`، و**الأخطر:**
`bulk_release_commissions` — سوبريوزر حقيقي من tenant A، لو عنده أو
خمَّن `commission_ids` تخص tenant B، وغيَّر الهيدر لـ`X-Tenant-ID: B`،
هيقدر (من الكود، بلا تحقق حي في هذه الجلسة):
- يعدّل نسب العمولات (`level_1_pct`...`level_10_pct`) الخاصة بـtenant B.
- يُنشئ إعدادات عمولة لمنتج تابع لـtenant B.
- **يُفرج (`CONFIRMED`) دفعة عمولات مالية حقيقية تخص tenant B** — أثر
  مباشر على تدفق أموال حقيقي، مش مجرد قراءة بيانات.

هذا مختلف عن نتيجة Phase 9 لـidentity (حيث كانت الـendpoints المحمية
الست تعتمد على `current_user.id` من JWT فمُحصَّنة عمليًا) — هنا
الـendpoints الإدارية بتعتمد **فقط** على الهيدر + معرّفات موارد، بلا أي
ربط بهوية الطالب على الإطلاق.

**الحالة:** 🟠 لسه قائمة كعيب في الكود (مؤكَّد من القراءة)، **لكن غير
قابلة للفحص أو الاستغلال الحي حاليًا — محجوبة بالكامل ببند 0 أعلاه**
(باج `SimpleTenant` بيوقف أي طلب قبل الوصول لنقطة القرار دي، بهيدر
صح أو غلط سواء). محاولة الفحص الحي الفعلية لهذه الثغرة تحديدًا (`PUT
/admin/tiers` بهيدر مخالف) هي اللي اكتشفت بند 0 أصلاً — التفاصيل
الكاملة والـtraceback الحقيقي موثَّقين هناك.

---

### 🟠 ثغرة 4: `withdraw_commissions` — `sender_id=1` مُثبَّت بلا فحص tenant للمُرسِل

**من الكود (`affiliate/service.py:474-482`):**
```python
async with self.db.begin_nested():
    tx = await self.finance.transfer(
        sender_id=1,   # ⬅️ مُثبَّت حرفيًا لكل الـtenants
        receiver_email=receiver_email,
        amount=amount,
        currency="MR_USDT",
        ...
    )
```

`FinanceService.transfer` (`finance/service.py:58-147`) بيفحص
`receiver.tenant_id != self.tenant_id` (سطر 82) — **لكن بلا أي فحص
مماثل على المُرسِل**، لأن `sender_id` بيتمرر كرقم خام بلا استعلام `User`
على الإطلاق؛ بيتم فقط جلب/إنشاء محفظة (`get_or_create_wallet_for_update`)
بمعرّف `1` مباشرة والتأكد إن رصيدها يكفي (سطر 106-109). بما إن `id`
مفتاح عمومي عبر جدول `users` كله (مش لكل tenant)، المستخدم رقم `1`
كيان **واحد فعليًا** يخص tenant معيّن بعينه (غالبًا أول tenant اتعمل).

**الأثر (من قراءة الكود):** كل عمليات سحب العمولات لكل الـtenants في
المنصة — بغض النظر عن الـtenant الحقيقي للداعي الساحب — بتسحب من نفس
محفظة المستخدم رقم `1` بالضبط. لو المستخدم ده تابع لـtenant مختلف عن
tenant الساحب، ده اقتران مالي غير مقصود بين tenants (تنضب محفظة
tenant واحد بسبب مسحوبات عمولات تخص tenant تاني تمامًا)، وخرق مباشر
لمبدأ العزل المالي بين الـtenants. **لم يُتحقق حيًا** (يحتاج بيانات
اختبار متعددة الـtenants، مؤجَّل بطلب المستخدم).

**الحالة:** 🟠 لسه قائمة، لم تُصلَح.

---

### 🟡 ثغرة 5: `get_or_create_profile` قد يرمي `IntegrityError` غير معالَج (500)

`AffiliateProfile.user_id` عمود **فريد (`unique=True`)** على مستوى
الجدول كله (`models.py:21`، `ix_affiliate_profiles_user_id`). لو مستخدم
عنده ملف داعي بالفعل تحت tenant الحقيقي بتاعه، وبعت هيدر
`X-Tenant-ID` بقيمة *tenant تانٍ موجود فعليًا*، فـ`get_affiliate_profile(user_id, tenant_id_من_الهيدر)`
هيرجع `None` (الفلترة بـ`AND tenant_id == الهيدر` مش هتلاقي السطر
الموجود أصلاً تحت الـtenant الصح)، فالكود هيحاول
`create_affiliate_profile(tenant_id=الهيدر, user_id=X, ...)` — ده هيفشل
بـ`IntegrityError` (انتهاك القيد الفريد على `user_id`) لأن صف بنفس
`user_id` موجود بالفعل. لا يوجد `try/except` حول هذا المسار في
`service.py`/`router.py` → **500 غير معالَج، بلا رسالة عربية واضحة،
قابل للتحفيز بمجرد تغيير هيدر HTTP من طرف أي مستخدم مسجَّل دخول.**

**الحالة:** 🟡 لسه قائمة، لم تُصلَح، لم تُختبَر حيًا.

---

### ملاحظات إضافية (input validation / rate limiting العام)

- Pydantic schemas مطبَّقة على كل الـendpoints. `WithdrawRequest.amount`
  محمي بـ`gt=0`. `AffiliateProfileBase.referral_code`/`custom_slug`
  عندهم `max_length`. **لا يوجد `max_length` على `AffiliateLinkBase.target`
  أو حقول `utm_*`** — نص حر بلا حد أقصى (خطر تخزين منخفض، مش استغلال
  حرج).
- `AffiliateProfileUpdate`/`AffiliateLinkUpdate`/`CommissionTierUpdate`:
  الحقول المتاحة في الـSchema نفسها **ضيقة ومقصودة** (لا تحتوي
  `tenant_id`/`id`/`affiliate_id`) — **صفر خطر mass-assignment**، فحص
  إيجابي، الكود سليم هنا.
- `update_affiliate_link`: منطق التحقق من الملكية بيمر بحلقة Python
  (جلب لغاية 100 رابط ثم مطابقة `id` يدويًا) بدل استعلام مباشر
  `WHERE id=... AND affiliate_id=...` — غير فعّال أداءً (ملاحظة كفاءة،
  مش ثغرة، لأن الـUPDATE الفعلي بعدها بيتفّذ فقط لو الرابط اتلاقى في
  النطاق الصحيح أصلاً).
- `GET /affiliate/tree`: `response_model=List[dict]` — الـservice
  بيحط كائن `AffiliateProfile` ORM خام جوّه كل عنصر (`"profile": profile`)
  بدل `AffiliateProfileResponse` مُنظَّم. الجدول ده مالوش أعمدة حساسة
  (لا باسورد ولا سر)، فمش تسريب بيانات حرج زي حالة identity/login، لكنه
  نمط تسلسل غير منضبط (نفس فئة الخطأ البنيوي اللي سبَّب ثغرة
  `hashed_password` في identity) يستحق `response_model` صريح لاحقًا.
- Rate limiting fail-open عند فشل Redis (سطر 64-67 في `rate_limiter.py`)
  — نفس النمط الموثَّق في identity Phase 9، لكنه بلا قيمة عملية هنا أصلاً
  بسبب ثغرة 2 أعلاه.

---

## المخرج 2: الجرد الوظيفي الكامل (15 endpoints)

**المنهجية:** تتبّع فعلي `router.py → service.py → repository.py`
لكل endpoint، بلا افتراض من اسم الدالة.

> ⚠️ **تحديث بعد التحقق الحي (بند 0):** الجدول تحت اتكتب أول مرة بناءً
> على قراءة كود ثابتة، وكان بيفترض إن أي endpoint من غير `require_subscription`
> "شغال". **التحقق الحي أثبت العكس تمامًا:** باج `SimpleTenant` بيكسر
> **كل الـ15 endpoint بلا استثناء** عند أول استعلام DB بيستخدم `tenant_id`،
> بغض النظر عن `require_subscription`. عمود "الحالة" تحت مُحدَّث ليعكس
> ده — كل صف بقى 🔴 **مكسور فعليًا (مؤكَّد أو شبه مؤكَّد)**، مع توضيح
> إن الاستدلال على الـ13 اللي مبتاخدش `require_subscription` مبني على
> **التعميم المنطقي** من نفس نمط الكود المؤكَّد حيًا في endpoint واحد
> بسيط (`GET /profile`) وendpoint إداري واحد (`PUT /admin/tiers`) —
> مش كل الـ13 اتُختبر فرديًا حيًا.

| Method | Path | الغرض | Input | Output | الحالة |
|---|---|---|---|---|---|
| GET | `/affiliate/profile` | جلب ملف الداعي (أو إنشاؤه تلقائيًا لو أول مرة) | لا شيء (هوية من JWT) | `200` + `AffiliateProfileResponse` | 🔴 **مكسور فعليًا — مؤكَّد بالتنفيذ الفعلي** (بند 0، طلب حي فعلي، 500) |
| PUT | `/affiliate/profile` | تحديث `custom_slug`/`default_commission_rate`/`is_active` | `AffiliateProfileUpdate` | `200` + `AffiliateProfileResponse` | 🔴 **مكسور فعليًا — نفس نمط الكود المؤكَّد حيًا في `GET /profile`** (لم يُختبَر هو نفسه حيًا، تعميم منطقي عالي الثقة) |
| POST | `/affiliate/links` | إنشاء رابط دعوة مخصص | `AffiliateLinkCreate` (`target`, `product_id`, utm_*) | `201` + `AffiliateLinkResponse` | 🔴 **مكسور فعليًا** — سببان مستقلان: `require_subscription` يرمي 500 قبل الوصول لأي منطق (ثغرة 1)، وحتى لو اتصلح هيتعطل ببند 0 |
| GET | `/affiliate/links` | عرض روابط المستخدم (paginated) | `skip`, `limit` | `200` + `PaginatedResponse[AffiliateLinkResponse]` | 🔴 **مكسور فعليًا** (بند 0، تعميم منطقي) |
| PATCH | `/affiliate/links/{id}` | تعديل رابط (target/utm/status/expiry) | `AffiliateLinkUpdate` | `200` + `AffiliateLinkResponse` | 🔴 **مكسور فعليًا** (ثغرة 1 + بند 0) |
| GET | `/affiliate/commissions` | عرض سجل العمولات (فلترة بالحالة، paginated) | `status?`, `skip`, `limit` | `200` + `PaginatedResponse[CommissionResponse]` | 🔴 **مكسور فعليًا** (ثغرة 1 + بند 0) — وحتى لو اتصلحوا الاثنين، الجدول فاضي عمليًا (انظر تحت) |
| POST | `/affiliate/commissions/release` | ترقية عمولات `PENDING`→`CONFIRMED` | لا شيء | `202` + `{message, released, count}` | 🔴 **مكسور فعليًا** (ثغرة 1 + بند 0) |
| POST | `/affiliate/withdraw` | سحب رصيد عمولات مؤكَّدة إلى محفظة المستخدم | `WithdrawRequest` (`amount`) | `202` + `WithdrawResponse` | 🔴 **مكسور فعليًا** (ثغرة 1 + بند 0) — **+ ثغرة 4 (`sender_id=1`) لو اتصلحوا الاثنين قبلها** |
| GET | `/affiliate/stats` | إحصائيات أداء الداعي | لا شيء | `200` + `AffiliateStatsResponse`، أو `404` لو مفيش ملف | 🔴 **مكسور فعليًا** (بند 0، تعميم منطقي) — لو اتصلح، القيم هترجع صفرية عمليًا برضو (انظر تحت) |
| GET | `/affiliate/tree` | شجرة الرعاة الصاعدة (sponsors chain) | `max_depth` | `200` + `List[dict]` | 🔴 **مكسور فعليًا** (بند 0) — لو اتصلح، الشجرة هترجع فاضية عمليًا برضو (`ReferralTree` لا تُنشأ من أي مسار حي) |
| GET | `/affiliate/track/{code}` | تسجيل نقرة + بيانات UTM (عام، بلا مصادقة) | path `referral_code` + query params | `200` + `{message, click_id}`، أو `404` لو الكود غير صالح | 🔴 **مكسور فعليًا** (بند 0 — بيستخدم نفس `tenant_id: int = Depends(get_current_tenant)`، حتى بلا مصادقة) — **وحتى لو اتصلح، غير مُستدعى من أي واجهة فرونت إند (انظر مخرج 3)** |
| GET | `/affiliate/admin/tiers` | عرض إعدادات العمولات العامة (GLOBAL) للـtenant | لا شيء | `200` + `CommissionTierResponse`، أو `404` | 🔴 **مكسور فعليًا — مؤكَّد بالتنفيذ الفعلي** (بند 0، نفس مسار `get_commission_tiers` اللي فحصناه حيًا عبر `PUT`) |
| PUT | `/affiliate/admin/tiers` | تعديل نسب المستويات 1-10 + رسوم النظام + حد السحب الأدنى | `CommissionTierUpdate` | `200` + `CommissionTierResponse` | 🔴 **مكسور فعليًا — مؤكَّد بالتنفيذ الفعلي** (بند 0، طلب حي مباشر، traceback حقيقي موثَّق) |
| POST | `/affiliate/admin/tiers/product` | إنشاء إعدادات عمولة خاصة بمنتج محدد | `CommissionTierCreate` | `200`/`201` + `CommissionTierResponse` | 🔴 **مكسور فعليًا** (بند 0، تعميم منطقي) |
| POST | `/affiliate/admin/commissions/bulk-release` | إفراج جماعي عن عمولات محدَّدة بالـID | `CommissionBulkReleaseRequest` (`commission_ids`, `notes`) | `202` + `CommissionBulkReleaseResponse` | 🔴 **مكسور فعليًا** (بند 0، تعميم منطقي) — وحتى لو اتصلح، هيرجع دايمًا "لم يتم العثور على العمولات" لأن `affiliate_commissions` فاضي |

**النتيجة النهائية بعد التحقق الحي: 15 من 15 endpoint مكسورة فعليًا
(500 دائمًا) بسبب باج `SimpleTenant` (بند 0) — 2 منهم (`GET /profile`،
`PUT /admin/tiers`) مؤكَّدين حرفيًا بطلب HTTP حقيقي وtraceback حقيقي،
والباقي بتعميم منطقي عالي الثقة لنفس نمط الكود المُكرَّر حرفيًا في
كل الـ15 موضع. زائد 5 منهم عندهم سبب فشل إضافي مستقل تمامًا
(`require_subscription`، ثغرة 1) بيموتوا بيه حتى قبل ما يوصلوا لبند 0
أصلاً. لا يوجد أي endpoint حاليًا شغّال end-to-end ضد قاعدة بيانات
حقيقية.**

---

### 🔴 اكتشاف جوهري: محرك توزيع العمولات في دومين affiliate نفسه **كود ميت بالكامل** — لا يُستدعى من أي مسار حي في الإنتاج

> ⚠️ **ملاحظة بعد اكتشاف بند 0:** هذا الاكتشاف بقى **من الناحية العملية
> الفورية غير قابل للملاحظة أصلاً** — كل الـendpoints المعنية (commissions,
> stats, tree, bulk-release) بترجع 500 بسبب بند 0 قبل ما توصل حتى لمرحلة
> "بيانات فاضية". لكنه **يفضل صحيح ومهم كوصف لما هيحصل لو بند 0 اتصلح**
> (هترجع 200 ببيانات فاضية/صفرية، مش 200 ببيانات حقيقية) — موثَّق هنا
> كتحليل جاهز لأي إصلاح مستقبلي، مش كوصف للسلوك الحالي الفوري.

هذا الاكتشاف يفسّر ليه أي endpoint بيقرأ من جدول `affiliate_commissions`
(commissions, stats, tree, bulk-release) **كان هيرجع** بيانات فاضية/صفرية
دايمًا حتى لو الـauth وبند 0 كانوا سليمين 100%.

**السلسلة الكاملة اللي تم تتبّعها فعليًا بالكود:**

1. `AffiliateService.distribute_commissions(order_id)` (`affiliate/service.py:260`)
   هو المكان الوحيد اللي بيكتب فعليًا في `affiliate_commissions` (عبر
   `_distribute_levels` → `repo.create_commission`). **مفيش أي مكان
   تاني في الكود بيكتب في الجدول ده.**
2. الاستدعاء الوحيد لـ`distribute_commissions` هو من
   `app/tasks/affiliate.py::distribute_commissions_task` (مهمة Celery
   باسم `affiliate.distribute_commissions`).
3. `grep` شامل على المشروع كله لـ`distribute_commissions_task` /
   `affiliate.distribute_commissions` (كـstring اسم مهمة، لاحتمال
   استدعاء عبر `send_task`): **صفر نتيجة استدعاء من أي مكان تاني** —
   لا webhook، لا service، لا router. المهمة دي **معزولة تمامًا، غير
   مُطلَقة من أي حدث فعلي في التطبيق.**
4. حتى لو اتنادت، هي **مكسورة بنيويًا** (`app/tasks/affiliate.py:58-67`):
   ```python
   def distribute_commissions_task(self, order_id: int, tenant_id: int):
       ...
       service = AffiliateService(db)            # ⬅️ ناقص tenant_id الإجباري
       commissions = await service.distribute_commissions(order_id, tenant_id)  # ⬅️ الدالة الحقيقية بتاخد order_id بس (tenant_id بييجي من self)
   ```
   `AffiliateService.__init__(self, db, tenant_id)` (سطر 50) بياخد
   `tenant_id` إجباري — استدعاء `AffiliateService(db)` هيرمي
   `TypeError` فورًا. وحتى لو اتصلح، `distribute_commissions` توقيعها
   الحقيقي `(self, order_id: int)` — مش `(order_id, tenant_id)` — يعني
   استدعاء تمرير معاملين هيفشل تاني.
5. **الآلية الفعلية المُستخدَمة في الإنتاج مختلفة تمامًا ومنفصلة
   بالكامل**، موجودة في دومين `commerce`:
   - `CommerceService.checkout()` (`commerce/service.py:213-218`) —
     بتُستدعى **synchronously** (مش عبر Celery) وقت إتمام الطلب، لو
     `checkout_data.affiliate_code` موجود و`store.is_affiliate_enabled`.
   - بتنادي `CommerceService.distribute_commissions(order_id, affiliate_code, order_total)`
     (`commerce/service.py:249-289`) — دالة **مختلفة تمامًا**، بتكتب في
     جداول commerce الخاصة بيها: `CommissionRecord`
     (`commerce/models.py:207`) و`AffiliateConfig`
     (`commerce/models.py:229`)، عبر `get_sponsor_chain`/`create_commission`/
     `get_affiliate_config` في `commerce/repository.py` — **مش
     `affiliate.Commission`/`CommissionTier`/`ReferralTree` على الإطلاق.**
   - حتى نظام "كود الإحالة" مختلف: `commerce` بيتعامل مع `affiliate_code`
     كـرقم `user_id` خام (`int(affiliate_code)`)، بينما `affiliate`
     domain بيولّد `referral_code` كنص ألفانيوميري (`EPPNE-{id}-{hex}`
     مقطوع لـ8 حروف) — **صيغتان غير متوافقتين تمامًا لنفس المفهوم.**

**الخلاصة:** الدومين اللي بنراجعه (`affiliate/*`) — بكل جداوله
(`Commission`, `CommissionTier`, `ReferralTree`, `AffiliateLink`,
`AffiliateClickLog`) ومنطقه (10 مستويات عمولة، شجرة إحالة متعددة
المستويات) — **مبني بالكامل ومتّسق داخليًا (tenant isolation صحيح،
schemas سليمة)، لكنه غير متصل إطلاقًا بمسار الشراء الحقيقي في
commerce.** أي مستخدم يسجّل، يُنشئ رابط دعوة (لو اتصلحت ثغرة 1)، ويشارك
الرابط — نقراته هتتسجّل فعليًا في `affiliate_click_logs` (عبر
`GET /track/{code}` الشغّال)، لكن **مفيش أي عمولة هتتولّد أبدًا** من أي
عملية شراء حقيقية، لأن الشراء بيمر من مسار commerce المنفصل تمامًا
الذي لا يتفاعل مع بيانات affiliate إطلاقًا. `GET /commissions`,
`GET /stats` (pending/paid/earned)، `GET /tree`، و`admin/*` — كلهم
هيرجعوا فاضي/صفر بشكل دائم في أي بيئة إنتاج حقيقية.

**هذا اكتشاف جوهري يستحق قرار منتج/معماري منفصل** (هل الهدف توحيد
الدومينين، أم حذف أحدهما، أم ربطهما؟) — **لا قرار أو تعديل تم هنا،
توثيق فقط.**

---

### ملاحظة إضافية: `app/tasks/affiliate.py` بالكامل كود ميت مكسور (3 مهام)

بالإضافة لـ`distribute_commissions_task` أعلاه:
- `release_commissions_task` (سطر 93): بتنادي `AffiliateService(db)`
  بنفس الخطأ (ناقص `tenant_id`) — TypeError فوري لو اتنادت. **غير
  مُستدعاة من أي مكان** (نفس فحص الـgrep الشامل).
- `clean_expired_links_task` (سطر 129): بتنادي
  `repo.delete_expired_invitations(cutoff_date)` — التوقيع الحقيقي في
  `AffiliateRepository` (سطر 375) بياخد `tenant_id` **إجباري** كمان —
  استدعاء ناقص معامل، TypeError. **وحتى لو اتصلحت، مفيش أي جدولة (Celery
  Beat) مسجَّلة لها في `core/celery_config.py::beat_schedule`** (فُحص
  الملف كامل — يحتوي جدولة لـ`saas.*` و`agritech.*` بس، صفر ذِكر
  لـ`affiliate.*`) — يعني حتى لو اشتغلت، **محدش بينادي عليها دوريًا
  أصلًا.**

الدالة المكافئة الصحيحة فعليًا موجودة ومكتوبة صح في
`AffiliateService.clean_expired_invitations(days=30)` (سطر 642-646،
بتمرر `self.tenant_id` صح) — لكنها **مش متصلة بأي celery task شغّال أو
مجدول.** كود صحيح لكنه يتيم بلا أي مُستدعٍ.

---

## المخرج 3: تناغم Backend/Frontend

### 🔴 اكتشاف جوهري: كل مسارات `services/affiliate.service.ts` مزدوجة البادئة (`/affiliate/affiliate/...`) — لا تطابق أي مسار حقيقي بالباك إند

**من الكود:**
- الباك إند: `affiliate/router.py:15` → `router = APIRouter(prefix="/affiliate", ...)`.
  `main.py:302-308` بيسجّل كل روترات `routers_config` بـ
  `include_router(router_obj, prefix="/api", ...)` **فقط** — حقل
  `prefix_path` التاني في الـtuple (`"/affiliate"`) **غير مُستخدَم فعليًا**
  في `include_router` (نفس الاكتشاف الموثَّق سابقًا لـidentity في Phase 5،
  `PROGRESS_LOG.md [2026-08-10]`). **المسار الحقيقي النهائي:
  `/api/affiliate/profile`، `/api/affiliate/links`، إلخ — بادئة واحدة
  بس.**
- الفرونت إند: `lib/api-client.ts:7` → `BASE_URL = ".../api"`. كل دالة
  في `affiliate.service.ts` بتستهدف مسارات بصيغة
  `"/affiliate/affiliate/profile"`, `"/affiliate/affiliate/links"`,
  `"/affiliate/affiliate/commissions"`, `"/affiliate/affiliate/withdraw"`,
  `"/affiliate/affiliate/stats"`, `"/affiliate/affiliate/tree"`,
  `"/affiliate/affiliate/track/{code}"` — **بادئة مزدوجة حرفيًا داخل
  الـstring نفسه**، مش مجرد نوع بيانات قديم زي ما كان الحال في `api-types.ts`
  لـidentity. الـURL النهائي الفعلي اللي هيتبعت =
  `.../api/affiliate/affiliate/profile` — **لا يطابق أي route مُسجَّل في
  الباك إند إطلاقًا.**

فُحص `next.config.ts` فعليًا — الملف فارغ تمامًا (بلا أي `rewrites()`)،
فلا يوجد أي تصحيح مسار وسيط يلغي أثر البادئة المزدوجة.

**النتيجة: كل استدعاء HTTP واحد في `affiliate.service.ts` (8 دوال) هيفشل
بـ 404 مضمون عند التنفيذ الفعلي في المتصفح.** لم يُختبَر ده حيًا (بطلب
المستخدم)، لكن الاستنتاج مبني على مطابقة نصية مباشرة بين رقمين ثابتين
(prefix الروتر الحقيقي، ومسار الـaxios call الحرفي) — ثقة عالية جدًا.

---

### 🔴 اكتشاف إضافي منفصل: `hooks/affiliate/useAffiliate.ts` يستدعي دوال غير موجودة أصلاً في `affiliate.service.ts`، وبتوقيعات معاملات مختلفة

فحص كل الدوال التسع في `hooks/affiliate/useAffiliate.ts` مقارنةً
بالدوال الفعلية المُصدَّرة من `services/affiliate.service.ts`
(المصدر الوحيد، بلا نسخة تانية):

| Hook | استدعاء الـHook | الدالة الفعلية في service.ts | التطابق؟ |
|---|---|---|---|
| `useAffiliateProfile` | `getProfile()` | `getProfile(): Promise<...>` | ✅ متطابق |
| `useUpdateAffiliateProfile` | `updateProfile(payload)` | `updateProfile(data)` | ✅ متطابق |
| `useAffiliateLinks` | `getLinks(skip, limit)` **(معاملين منفصلين)** | `getLinks(params?: {skip?, limit?})` **(كائن واحد)** | 🔴 **مش متطابق** — شكل المعاملات مختلف |
| `useCreateAffiliateLink` | `createLink(payload)` | `createLink(data)` | ✅ متطابق |
| `useCommissions` | `getCommissions(skip, limit, status)` **(3 معاملات منفصلة)** | `getCommissions(params?: {status?, skip?, limit?})` **(كائن واحد)** | 🔴 **مش متطابق** |
| `useReleaseCommissions` | `releaseCommissions()` | `releaseCommissions(): Promise<void>` | ✅ متطابق |
| `useWithdraw` | `withdraw(payload)` | `withdraw(data: WithdrawRequest)` | ✅ متطابق شكليًا |
| `useAffiliateStats` | `getStats()` | `getStats(): Promise<...>` | ✅ متطابق |
| `useAffiliateDashboard` | `getDashboardStats()` | **غير موجودة إطلاقًا** | 🔴 **دالة غير معرَّفة — `TypeError` وقت التنفيذ** |
| `useAffiliateTree` | `getTree(maxDepth)` | **غير موجودة إطلاقًا (الموجود `getReferralTree`)** | 🔴 **دالة غير معرَّفة — `TypeError` وقت التنفيذ** |

**الأثر:** بصرف النظر تمامًا عن ثغرة الـURL المزدوج أعلاه، **حتى لو
اتصلحت المسارات**، استدعاء `useAffiliateDashboard()` أو
`useAffiliateTree()` هيرمي `TypeError: AffiliateService.getDashboardStats
is not a function` وقت التنفيذ الفعلي في المتصفح (مش فقط 404 شبكة —
خطأ JS قبل حتى إرسال أي طلب). و`useAffiliateLinks`/`useCommissions`
هيرسلوا `params` بشكل غير صحيح (تمرير رقم مكان كائن) للدالة اللي
بتتوقع `{skip, limit}`.

**ملاحظة سياق:** هذا النوع من الانحراف (hooks غير متزامنة مع service
حقيقي) قد يكون له علاقة بانحراف الـ`+15` خطأ tsc غير المفحوص، الموثَّق
مسبقًا في `PROGRESS_LOG.md [2026-08-10]` (قبل Phase 4) — **لم يُشغَّل
`tsc --noEmit` في هذه الجلسة للتأكيد (خارج نطاق read-only بدون طلب
صريح)، هذا افتراض معقول غير مؤكَّد.**

---

### 🟠 الصفحة الوحيدة الفعلية للدومين (`app/(dashboard)/affiliate/page.tsx`) تستخدم مباشرة الـhook المكسور، وكل روابطها الفرعية تشير لصفحات غير موجودة

`AffiliateDashboard` (الصفحة الوحيدة الموجودة فعليًا تحت
`app/(dashboard)/affiliate/`، مؤكَّد بـ`Glob` شامل — لا يوجد
`links/`, `commissions/`, `tree/`, `withdraw/`, `guidelines/` كملفات
صفحات فعلية) بتستخدم `useAffiliateProfile`, `useAffiliateStats`,
`useAffiliateDashboard` (سطر 6، 43-45) — الثلاثة الأخيرة كلها متأثرة
بثغرتي الـURL المزدوج والدالة المفقودة أعلاه. النتيجة العملية (react-query
بيمتص الأخطاء بصمت، الصفحة مش هتنهار بالكامل لكن هتفضل فاضية): كل
البطاقات هتعرض "0 MR_USDT"/"0%" دايمًا، `profile?.referral_code` هيفضل
`undefined` فيختفي كود الدعوة بالكامل من الواجهة، وقسمي "آخر العمولات"/
"الروابط الأكثر استخدامًا" هيفضلوا في حالة "لا توجد بيانات" الدائمة.

**كل الروابط الأربعة الظاهرة في الصفحة نفسها بتشاور على مسارات غير
موجودة إطلاقًا:**
- `/affiliate/links` (زر "روابطي" + "إنشاء رابط دعوة" + بطاقة سريعة)
- `/affiliate/commissions` (زر "سحب الأرباح" + رابط "عرض الكل" مرتين)
- `/affiliate/tree` (بطاقة "شجرة الإحالة")
- `/affiliate/guidelines` (بطاقة "دليل الداعي السيادي")
- `/affiliate/links/create` (رابط "إنشاء رابط" في حالة القائمة الفاضية)

**وبشكل مستقل تمامًا، السايدبار (`components/layout/sidebar.tsx`
سطر 505-529) بيربط لنفس المجموعة من المسارات غير الموجودة**
(`/affiliate/links`, `/affiliate/commissions`, `/affiliate/tree`,
`/affiliate/withdraw`) — **تأكيد مزدوج ومستقل (صفحة + قائمة تنقل
رئيسية) إن الدومين كله من ناحية الواجهة = صفحة dashboard واحدة معطوبة
البيانات، بلا أي تنقل فعلي لأي عمق تاني.** Next.js App Router هيرجّع
404 قياسي لكل هذه الروابط عند الضغط عليها.

---

### مصفوفة الاستهلاك الكاملة (كل الـ15 endpoint)

| Endpoint | مُستهلَك من الفرونت؟ | ملاحظة |
|---|---|---|
| `GET /profile` | ⚠️ محاولة استهلاك موجودة (`useAffiliateProfile`) | لكن مكسورة بثغرة الـURL المزدوج |
| `PUT /profile` | ⚠️ محاولة استهلاك موجودة (`useUpdateAffiliateProfile`) | نفس المشكلة، + لا يوجد أي فورم/UI فعلي بيستدعيها (الـhook معرَّف، غير مُستخدَم من أي صفحة) |
| `POST /links` | ⚠️ محاولة استهلاك (`useCreateAffiliateLink`) | لا صفحة `create` فعلية تستخدمه؛ الـhook يتيم بلا مُستهلِك UI |
| `GET /links` | ⚠️ محاولة استهلاك (`useAffiliateLinks`) | يتيم بلا مُستهلِك UI + توقيع معاملات خاطئ |
| `PATCH /links/{id}` | 🔴 **غير مُستهلَك إطلاقًا** | لا يوجد `updateLink`/ما يعادلها في `useAffiliate.ts` أو `affiliate.service.ts` أصلاً |
| `GET /commissions` | ⚠️ محاولة استهلاك (`useCommissions`) | يتيم بلا صفحة، توقيع معاملات خاطئ |
| `POST /commissions/release` | ⚠️ محاولة استهلاك (`useReleaseCommissions`) | يتيم بلا صفحة |
| `POST /withdraw` | ⚠️ محاولة استهلاك (`useWithdraw`) | يتيم بلا صفحة/فورم سحب فعلي |
| `GET /stats` | ✅ مُستهلَك فعليًا من الصفحة الوحيدة | لكن مكسور بثغرة الـURL |
| `GET /tree` | ⚠️ محاولة استهلاك (`useAffiliateTree`) | دالة `getTree` غير موجودة أصلاً في service.ts |
| `GET /track/{code}` | 🔴 **غير مُستهلَك إطلاقًا** | `trackReferralClick` معرَّفة في service.ts لكن صفر استدعاء من أي hook/component/page (`grep` شامل) |
| `GET/PUT /admin/tiers` | 🔴 **غير مُستهلَك إطلاقًا** | لا توجد أي واجهة إدارية لـaffiliate في الفرونت إند |
| `POST /admin/tiers/product` | 🔴 **غير مُستهلَك إطلاقًا** | نفس الشيء |
| `POST /admin/commissions/bulk-release` | 🔴 **غير مُستهلَك إطلاقًا** | نفس الشيء |

**لا يوجد استدعاء فرونت إند لمسار غير موجود من ناحية *اسم الدالة* على
الباك إند** (المسارات المُستهدَفة، لو صُحِّح الـprefix المزدوج، تُطابق
أسماء حقيقية) — لكن **الصيغة الفعلية المُرسَلة (المزدوجة) نفسها غير
موجودة**، وهو ما تم توثيقه أعلاه كثغرة منفصلة أخطر من مجرد "مسار غير
موجود".

---

## الحصيلة الإجمالية لدومين affiliate (بعد Phase 10)

| البند | العدد |
|---|---|
| Endpoints فُحصت | 15/15 |
| **Endpoints مكسورة فعليًا (500 دائمًا) بعد التحقق الحي** | **15/15 (100%)** — بسبب باج `SimpleTenant` (بند 0)، 2 منهم مؤكَّدين حرفيًا بطلب HTTP حي |
| منهم بسبب فشل إضافي مستقل (`require_subscription`) | 5 |
| ثغرات/اكتشافات أمنية-وظيفية حرجة (من الكود + التنفيذ الحي) | 7 (**باج SimpleTenant [مؤكَّد حيًا]**، require_subscription، rate_limit صامت، X-Tenant-ID إداري [محجوبة حاليًا بباج SimpleTenant]، sender_id=1، محرك التوزيع كود ميت، مهام Celery مكسورة) |
| ثغرات متوسطة | 1 (IntegrityError غير معالَج، غير قابل للفحص الحي حاليًا لنفس سبب باج SimpleTenant) |
| استدعاءات فرونت إند تستهدف مسار مزدوج غير موجود | 8/8 دوال في `affiliate.service.ts` (100%) |
| Hooks تستدعي دوال غير معرَّفة أصلاً | 2 (`getDashboardStats`, `getTree`) |
| Hooks بتوقيع معاملات غير متطابق | 2 (`getLinks`, `getCommissions`) |
| Endpoints بلا أي محاولة استهلاك فرونت إند إطلاقًا | 6 (`PATCH /links/{id}`, `GET /track`, و4 admin) |
| صفحات فرونت إند فعلية للدومين | 1 فقط (`page.tsx`) — كل الروابط الفرعية (5) تشير لصفحات غير موجودة |

---

## ملاحظة هامشية غير مرتبطة — نمط double-prefix محتمل في `commerce.service.ts`، يحتاج تحقق منفصل ضمن phase commerce لاحقًا

أثناء تتبّع مسار توزيع العمولات الحقيقي (لإثبات إن
`AffiliateService.distribute_commissions` كود ميت — انظر مخرج 2)، تم
فتح `domains/commerce/service.py` و`tasks/commerce.py` **حصريًا لغرض
سياق التكامل** (هل affiliate متصل بمسار الشراء الفعلي في commerce؟).
أثناء هذا الفحص، لوحظ بالصدفة (بلا أي تحقق مقصود أو مراجعة لدومين
commerce نفسه) إن `services/commerce.service.ts` يحتوي أسطرًا شبيهة
بصيغة `/commerce/commerce/...` (لاحظتها فقط لأنها ظهرت أثناء `grep`
غير مباشر). **هذه ملاحظة سطحية غير مؤكَّدة وغير مُتحقَّق منها بنفس
الصرامة المُطبَّقة على affiliate في هذا التقرير** — لم يُفحص
`commerce/router.py` لتأكيد الـprefix الحقيقي، ولم يُراجَع أي شيء آخر
في commerce (authz، جرد وظيفي، تناغم frontend). **مذكورة هنا للتوثيق
فقط، بلا أي استنتاج قاطع** — أي تحقق أو تقييم فعلي لدومين commerce
(بما فيه هذه النقطة تحديدًا) يحتاج phase مستقل خاص بـcommerce، خارج
نطاق Phase 10 تمامًا.

---

## القرارات/الإصلاحات المؤجَّلة صراحة (تحتاج موافقة/جلسة منفصلة — خارج نطاق Phase 10 القرائي)

**مرتَّبة بالأولوية الفعلية بعد التحقق الحي — بند 1 هنا هو أعلى
أولوية على الإطلاق لأنه blocker يمنع تشغيل أو حتى فحص أي حاجة تانية
في الدومين:**

1. **إصلاح باج `SimpleTenant` (بند 0)** — تغيير `tenant_id: int =
   Depends(get_current_tenant)` إلى `tenant: SimpleTenant =
   Depends(get_current_tenant)` ثم استخدام `tenant.id` في كل الـ15
   endpoint، بنفس نمط إصلاح identity Phase 0. **يجب أن يترافق حتمًا مع
   إضافة فحص `current_user.tenant_id == tenant.id` على الـ4 endpoints
   الإدارية على الأقل** (وإلا الإصلاح الجزئي هيفتح ثغرة 3 فورًا —
   موضَّح بالتفصيل في بند 0 أعلاه). **بدون هذا الإصلاح، الدومين بالكامل
   (15/15 endpoint) غير قابل للاستخدام إطلاقًا ضد قاعدة بيانات حقيقية.**
2. إصلاح `require_subscription` (`api/deps.py`) ليطابق التوقيع الحقيقي
   لـ`SaaSControlService` — يؤثر أيضًا على `academy` و`commerce`، يحتاج
   فحص أثر أوسع قبل التعديل.
3. إصلاح `rate_limiter.py` أو إضافة `request: Request` لتوقيعات
   الـendpoints المحمية — قرار معماري (تعديل الديكوريتور نفسه أفضل من
   تعديل 15+ endpoint في كل دومين).
4. قرار معماري حاسم بخصوص ازدواجية نظام العمولات (`affiliate` مقابل
   `commerce`) — توحيد، ربط، أو حذف أحدهما.
5. حذف أو إصلاح `app/tasks/affiliate.py` (3 مهام ميتة مكسورة).
6. إصلاح مسارات `affiliate.service.ts` (إزالة البادئة المزدوجة) —
   خارج commerce بالكامل (انظر "ملاحظة هامشية" أعلاه: أي فحص لـ
   `commerce.service.ts` يحتاج phase مستقل خاص بـcommerce).
7. مزامنة `hooks/affiliate/useAffiliate.ts` مع التوقيعات الفعلية
   لـ`affiliate.service.ts` (أو العكس).
8. إنشاء الصفحات الناقصة (`links`, `commissions`, `tree`, `withdraw`،
   `guidelines`) أو إزالة الروابط اليتيمة من الصفحة والسايدبار.
9. معالجة `sender_id=1` المُثبَّت في `withdraw_commissions` — يحتاج
   تصميم واضح لمفهوم "محفظة النظام/الخزينة" متعددة الـtenants.
10. معالجة `IntegrityError` غير المعالَج في `get_or_create_profile`
    (يحتاج فحص حي بعد إصلاح بند 0 أولاً).
11. تشغيل `tsc --noEmit` للتأكد من وجود/عدم وجود type errors فعلية
    ناتجة عن ثغرة hooks/service المذكورة (مؤجَّل، لم يُشغَّل في هذه
    الجلسة).
12. فحص باقي الدومينات التي تستخدم `require_subscription` أو نفس نمط
    `tenant_id: int = Depends(get_current_tenant)` (academy, commerce،
    وأي دومين تاني) — احتمال وارد إن باج `SimpleTenant` أوسع بكتير من
    affiliate لوحده.

**لا تعديل كود تم في أي جزء من هذا التقرير — Phase 10 بالكامل
read-only من ناحية كود التطبيق، باستثناء تشغيل سيرفر محلي وإنشاء بيانات
اختبار throwaway بموافقة صريحة لبند 0 فقط (تفاصيل التنظيف تحت).**

---

## حالة بيانات الاختبار (وقت كتابة هذا التقرير — لسه لم يتم التنظيف)

| الكيان | المعرّف | الحالة |
|---|---|---|
| Tenant تجريبي (`Phase10 Audit Tenant B`) | `id=5` | ⏳ **لسه موجود، لم يُحذف بعد** |
| مستخدم `SUPER_ADMIN` تجريبي (`phase10_audit_superadmin@example.com`) | `id=15` | ⏳ **لسه موجود، لم يُحذف بعد** |
| صف `CommissionTier` تجريبي (تحت tenant `id=5`) | `id=1` (في `affiliate_commission_tiers`) | ⏳ **لسه موجود، `level_1_pct=13.37` (غير مُعدَّل)** |
| سيرفر `uvicorn` تجريبي محلي | `127.0.0.1:8000` | ⏳ **لسه شغّال وقت كتابة هذا السطر** |

**التنظيف الكامل (حذف الكيانات الثلاثة + إيقاف السيرفر + تحقق `SELECT`
مباشر بعد الحذف) لم يتم بعد — يحتاج موافقة صريحة منفصلة قبل التنفيذ،
بنفس نمط Phase 9.**
