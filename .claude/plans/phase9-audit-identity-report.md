# Phase 9 — التقرير الأمني لدومين identity (مخرج 1 من 3)

> **الحالة:** مخرج 1 فقط (التقرير الأمني) — شامل التحقق العملي الكامل.
> مخرجا 2 (الجرد الوظيفي) و3 (تناغم Backend/Frontend) **لم يبدآ بعد**.
>
> **المنهجية:** قراءة كاملة للكود (`router.py`, `service.py`,
> `repository.py`, `schemas.py`, `models.py`, `core/security.py`,
> `api/deps.py`, `core/rate_limiter.py`, تسجيل الراوترين في `main.py`)
> **+ تحقق عملي فعلي (empirical verification)** على بيئة محلية: تشغيل
> سيرفر حقيقي، طلبات `curl` فعلية، قاعدة بيانات Postgres وRedis محليين
> حقيقيين (عبر docker). كل النتائج أدناه إما "مؤكَّد من الكود" أو
> "مؤكَّد بالتنفيذ الفعلي" — تم التمييز صراحة بين الاثنين في كل بند.

---

## ملخص تنفيذي

| # | الثغرة | الحالة النهائية |
|---|--------|-------------------|
| 1 | تسريب `hashed_password` عبر `POST /identity/login` | 🟢 **كانت مؤكَّدة بالتنفيذ الفعلي، وتم إصلاحها فعليًا أثناء هذه الجلسة** — الإصلاح الآن **مُثبَّت في commit `0a488ba`** |
| 2 | `X-Tenant-ID` (هيدر العميل) هو مصدر tenant_id في `register`/`login` بلا أي تحقق تفويض | 🔴 **لسه قائمة، لم تُصلَح** — مؤكَّدة جزئيًا بالتنفيذ الفعلي (انظر نطاق التحقق أدناه بدقة) |

---

## 🔴 الثغرة 1: تسريب `hashed_password` عبر `POST /identity/login`

### وصف الثغرة (من قراءة الكود)

`identity/router.py`, endpoint الـ`login` (كان قبل الإصلاح بدون
`response_model`)، وكان بيرجّع كائن SQLAlchemy الخام مباشرة:
```python
return {..., "user": user}   # قبل الإصلاح
```

### التحقق العملي — قبل الإصلاح (مؤكَّد بالتنفيذ الفعلي)

**الإعداد:** سيرفر `uvicorn` محلي (`127.0.0.1:8000`) متصل بـPostgres حقيقي
(docker container `eppne_db`, بورت 5435) وRedis حقيقي (docker container
`redis`, بورت 6380). مستخدم تجريبي throwaway: `test_audit_phase9@example.com`.

**Request 1 — التسجيل (مرجعي، للتأكد من وجود المستخدم):**
```
POST /api/identity/register HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
X-Tenant-ID: 1

{"username":"test_audit_p9","email":"test_audit_phase9@example.com","password":"AuditPhase9Pass123"}
```
**Response 1:**
```
HTTP/1.1 201 Created
content-length: 541

{"username":"test_audit_p9","email":"test_audit_phase9@example.com","name_ar":null,"name_en":null,"birth_date":null,"marriage_status":"SINGLE","language_preference":"ar","profile_metadata":{},"preferences":{},"id":9,"public_id":"86b0d6a9-dc52-46c3-9dd9-4ed7364117eb","uid":null,"did":null,"tenant_id":1,"sovereign_rank":"CITIZEN_L1","system_role":"USER","kyc_status":"UNVERIFIED","reputation_score":100,"is_active":true,"balances":{},"last_login_at":null,"created_at":"2026-08-10T15:27:29.543393Z","updated_at":"2026-08-10T15:27:29.543393Z"}
```
نظيف تمامًا (كان دايمًا `response_model=UserResponse` على `register`).

**Request 2 — تسجيل الدخول (نفس المستخدم):**
```
POST /api/identity/login HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
X-Tenant-ID: 1

{"username_or_email":"test_audit_phase9@example.com","password":"AuditPhase9Pass123"}
```
**Response 2 (كاملة، خام، بتاريخ `Mon, 10 Aug 2026 15:27:44 GMT`، قبل الإصلاح):**
```
HTTP/1.1 200 OK
content-length: 1627
set-cookie: access_token=eyJhbGciOiJIUzI1NiIs...; HttpOnly; Max-Age=900; Path=/; SameSite=strict
set-cookie: refresh_token=eyJhbGciOiJIUzI1NiIs...; HttpOnly; Max-Age=604800; Path=/; SameSite=strict

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer","message":"تم تسجيل الدخول بنجاح","user_id":9,"user":{"marriage_status":"SINGLE","created_at":"2026-08-10T15:27:29.543393+00:00","email":"test_audit_phase9@example.com","kyc_status":"UNVERIFIED","id":9,"hashed_password":"$2b$12$OiqB4iFx4Z3YfIwujMljeOyu8BjOGQ0awWso3bgRI95IjrYHiHB8e","father_id":null,"phone_verified":false,"name_ar":null,"mother_id":null,"reputation_score":100,"is_active":true,"public_id":"86b0d6a9-dc52-46c3-9dd9-4ed7364117eb","username":"test_audit_p9","name_en":null,"spouse_id":null,"language_preference":"ar","session_version":1,"idempotency_key":"REG-5E7CC89FD520","uid":null,"birth_date":null,"sovereign_rank":"CITIZEN_L1","profile_metadata":{},"did":null,"death_date":null,"system_role":"USER","preferences":{},"last_login_ip":"127.0.0.1","tenant_id":1,"email_verified":false,"last_login_user_agent":"curl/8.14.1","refresh_tokens":[],"wallet":{"user_id":9,"wallet_address":null,"balances":{},"created_at":"2026-08-10T15:27:32.016762+00:00","updated_at":"2026-08-10T15:27:32.016762+00:00","id":7,"tenant_id":1,"is_custodial":true,"is_frozen":false},"tenant":{"domain":"test.local","admin_id":1,"created_at":"2026-08-08T17:54:16.841940+00:00","branding":null,"id":1,"name":"Local Test Tenant","is_active":true,"updated_at":"2026-08-08T17:54:16.841940+00:00"},"updated_at":"2026-08-10T15:27:44.736137+00:00","last_login_at":"2026-08-10T15:27:44.736137+00:00"}}
```

**تأكيد قاطع: `"hashed_password":"$2b$12$OiqB4iFx4Z3YfIwujMljeOyu8BjOGQ0awWso3bgRI95IjrYHiHB8e"`
ظاهر فعليًا في جسم استجابة حقيقية من سيرفر حي.** بالإضافة لتسريب زائد:
كائن `wallet` كامل، كائن `tenant` كامل (شامل `admin_id` و`domain`)،
`idempotency_key`, `session_version`, `last_login_ip`, `last_login_user_agent`.

**التفسير الجذري (من الكود):** `login` كان بدون `response_model`. FastAPI
بيستخدم `jsonable_encoder` كـfallback على الكائن الخام، واللي بيستخدم
`vars(obj)` (`obj.__dict__`) لو `dict(obj)` فشل — وده بيرجّع كل الأعمدة
المحمَّلة فعليًا شاملة `hashed_password`. أُكِّد ده بتجربة مباشرة لـ
`jsonable_encoder` على كلاس `User` الحقيقي (بدون DB) قبل التحقق الحي،
ورجّعت نفس النتيجة.

### اكتشاف الإصلاح أثناء الجلسة (مؤكَّد بـ`git diff`)

أثناء تحقيق لاحق على مستخدم تجريبي تانٍ (id=12)، لاحظت إن نفس طلب الـ
`login` رجّع **response نظيف تمامًا** (بدون `hashed_password`/`wallet`/
`tenant`). فحص `git status`/`git diff` كشف إن **الملف كان فيه تعديل
uncommitted حصل أثناء الجلسة** (مش مني — لم أستخدم Edit/Write على الملف
ده إطلاقًا قبل هذه اللحظة):
```diff
- return {..., "user": user}
+ return {..., "user": UserResponse.model_validate(user)}
```
تطابق زمني كامل: التعديل حصل الساعة `16:17:33 UTC` (من `mtime` الملف) —
بعد Test 2 (`15:27:44 GMT`، متسخ) وقبل الاختبارات اللاحقة (`17:22+ GMT`،
نظيفة). **بناءً على طلب صريح من المستخدم، تم عمل commit للتعديل ده الآن:**
```
commit 0a488ba
fix(security): filter hashed_password from login response via UserResponse.model_validate (Phase 9b)
```
تأكَّد بـ`git log --oneline -1` و`git status` (نظيف، صفر تغييرات pending
على الملف).

### التحقق العملي — بعد الإصلاح (مؤكَّد بالتنفيذ الفعلي)

**Request/Response (مستخدم تجريبي id=12، بعد الإصلاح، مُكرَّر مرتين
للتأكد من الثبات):**
```
POST /api/identity/login HTTP/1.1
X-Tenant-ID: 1
{"username_or_email":"p9_tenantA@example.com","password":"AuditPhase9Pass123"}
```
```
HTTP/1.1 200 OK
content-length: 863   (ثابت في المحاولتين)

{"access_token":"...","token_type":"bearer","message":"تم تسجيل الدخول بنجاح","user_id":12,"user":{"username":"p9_tenantA_user","email":"p9_tenantA@example.com","name_ar":null,"name_en":null,"birth_date":null,"marriage_status":"SINGLE","language_preference":"ar","profile_metadata":{},"preferences":{},"id":12,"public_id":"19f50f9a-6e3b-451f-96e0-0279d51de47a","uid":null,"did":null,"tenant_id":1,"sovereign_rank":"CITIZEN_L1","system_role":"USER","kyc_status":"UNVERIFIED","reputation_score":100,"is_active":true,"balances":{},"last_login_at":"2026-08-10T17:22:35.112414Z","created_at":"2026-08-10T17:21:41.490462Z","updated_at":"2026-08-10T17:22:35.112414Z"}}
```
**صفر حقول حساسة.** الشكل مطابق تمامًا لـ`UserResponse`. مؤكَّد بمحاولتين
منفصلتين (نتيجة ثابتة، مش عشوائية).

### ملاحظة منهجية (كيف اكتُشف الإصلاح)

جزء من وقت هذه الجلسة اتصرف في محاولة تفسير "سلوك غير متسق" في نتائج
الاختبار (response متسخ مرة، نظيف مرتين) بافتراضات عن سلوك SQLAlchemy
الداخلي (`expire_on_commit`, lazy loading, إلخ) — كلها كانت مسارات خاطئة.
السبب الحقيقي كان بسيطًا: **الملف اتغيّر فعليًا على القرص بين الاختبارين**،
مش سلوك عشوائي في الـORM. تم التأكد من كده بشكل قاطع عبر `git diff` بدل
الاستمرار في تخمين سلوك المكتبة. **مفيش وقت إضافي اتصرف على ده بعد
اكتشاف السبب الحقيقي.**

### الحالة النهائية

✅ **مُصلَحة ومُثبَّتة في commit `0a488ba`.** التحقق العملي قبل وبعد
الإصلاح كلاهما موثَّق بأدلة خام أعلاه.

---

## 🔴 الثغرة 2: `X-Tenant-ID` (هيدر العميل) كمصدر tenant_id في `register`/`login` بلا تحقق

### وصف الثغرة (من قراءة الكود)

`api/deps.py:148-153`:
```python
async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```
لا يوجد استعلام DB أو أي تحقق — القيمة بتيجي من هيدر HTTP مباشرة.
`identity/router.py:11` بيستورد الدالة دي (مش نسخة أقوى)، ومُستخدَمة في
**كل الـ10 endpoints** في identity (عام ومحمي).

### التحقق العملي 1: `register` تحت tenant حقيقي مختلف بلا أي تفويض (مؤكَّد بالتنفيذ الفعلي)

**الإعداد:** أُنشئ tenant حقيقي ثانٍ (`Tenant B`, id=2) مباشرة في
`academy_tenants` عبر سكربت مستقل (`test_create_tenant_b.py`، خارج
`app/`، بدون لمس أي كود إنتاجي) لأن `register` نفسه لا يُنشئ tenants،
فقط يُلحق مستخدمين بـtenant_id موجود.

```
POST /api/identity/register HTTP/1.1
X-Tenant-ID: 2
{"username":"p9_tenantB_user","email":"p9_tenantB@example.com","password":"AuditPhase9Pass123"}
```
```
HTTP/1.1 201 Created
content-length: 537

{"username":"p9_tenantB_user","email":"p9_tenantB@example.com",...,"id":13,...,"tenant_id":2,...}
```

**تأكيد قاطع:** أي زائر مجهول (بدون أي دعوة أو تفويض) سجّل مستخدم جديد
تحت `tenant_id=2` (Tenant B، مش بتاعه) **بمجرد تغيير قيمة هيدر HTTP**.
النظام تحقق فقط من **وجود** الـtenant (بسبب FK constraint على
`users.tenant_id → academy_tenants.id`؛ لو الهيدر كان لرقم غير موجود
أصلًا كـtenant، الـINSERT كان هيفشل بخطأ FK) — **مش من ملكية/تفويض
الزائر على هذا الـtenant**. هذا الجزء من الثغرة **لسه قائم فعليًا،
مؤكَّد بالتنفيذ الحي**.

### التحقق العملي 2: هل ينجح هذا في تسريب بيانات مستخدم تابع لـtenant تانٍ عبر `protected_router`؟ (مؤكَّد بالتنفيذ الفعلي — نتيجة سلبية)

**الإعداد:** تسجيل دخول كـ`User A` (id=12, tenant الحقيقي=1)، والحصول
على كوكيز جلسة صالحة (JWT موقَّع بـ`tenant_id=1`).

**Request A — ضبط مرجعي (هيدر صحيح):**
```
GET /api/identity/me HTTP/1.1
Cookie: access_token=<JWT صالح لـUser A>
X-Tenant-ID: 1
```
```
HTTP/1.1 200 OK
{"username":"p9_tenantA_user",...,"id":12,"tenant_id":1,...}
```

**Request B — هيدر لـTenant B الحقيقي (id=2، مش بتاع User A):**
```
GET /api/identity/me HTTP/1.1
Cookie: access_token=<نفس JWT، بدون تغيير>
X-Tenant-ID: 2
```
```
HTTP/1.1 404 Not Found
{"detail":"المستخدم غير موجود","code":"NotFoundError"}
```

**Request C — نفس الاختبار على `GET /identity/sessions`:**
```
GET /api/identity/sessions HTTP/1.1
Cookie: access_token=<نفس JWT>
X-Tenant-ID: 2
```
```
HTTP/1.1 200 OK
[]
```

**Request D — ضبط إضافي (هيدر tenant وهمي غير موجود، 999، للمقارنة):**
```
GET /api/identity/me HTTP/1.1
Cookie: access_token=<نفس JWT>
X-Tenant-ID: 999
```
```
HTTP/1.1 404 Not Found
{"detail":"المستخدم غير موجود","code":"NotFoundError"}
```
(تأكَّد بفحص DB مباشر: `tenant_id=999` **غير موجود فعليًا** في
`academy_tenants` — بعكس Tenant B في Request B/C، اللي هو **tenant
حقيقي موجود فعليًا**. النتيجة كانت نفسها (404) في الحالتين — يعني
النتيجة **مش لأن النظام بيتحقق من وجود الـtenant**.)

**التفسير الدقيق (من الكود + التنفيذ الحي معًا):** `GET /me` بيستخدم
`user_id=current_user.id` (من الـJWT الموقَّع، مش من الهيدر) في استعلام
`WHERE users.id = X AND users.tenant_id = <هيدر>`. بما إن `id` قيمة
ثابتة وموثوقة، وبما إن `users.id` **مفتاح فريد على مستوى الجدول كله**،
تغيير الهيدر لأي قيمة (حقيقية أو وهمية) غير `1` **مستحيل يرجّع بيانات
مستخدم تانٍ** — النتيجة الوحيدتان الممكنتان هما بيانات المستخدم الحقيقي
(هيدر صح) أو صفر نتائج (هيدر غلط). **ده مش نتيجة فحص أمني مقصود** (زي
الفحص الصريح `if token_tenant_id != user.tenant_id: raise "Tenant
mismatch"` الموجود في `core/security.py`) — **ده أثر جانبي لكون
`user_id` مصدره الـJWT دايمًا، مش الهيدر، في هذه الـendpoints تحديدًا.**

### نطاق النتيجة السلبية (مهم — بناءً على طلب توضيح صريح)

**النتيجة "غير قابلة للاستغلال عبر تسريب بيانات" أعلاه تنطبق حصريًا على
الـendpoints اللي بتعتمد على `current_user.id` (من الـJWT) كمصدر وحيد
لتحديد "مين اليوزر" — يعني `GET /me`, `PUT /me`, `GET /sessions`,
`POST /revoke-all`, `PUT /me/password`, `DELETE /me`.**

**جرد شامل ومكتمل (100%) لكل الـ10 endpoints في `identity/router.py` +
`protected_router` — هل فيه أي endpoint بياخد `user_id` أو `tenant_id`
مستهدَف كـpath أو query parameter مباشر بدل الاعتماد على `current_user.id`؟**

| Endpoint | Path param؟ | Query param متعلق بهوية؟ |
|---|---|---|
| `POST /register` | لا | لا (body فقط) |
| `POST /login` | لا | لا (body فقط) |
| `POST /logout` | لا | لا (كوكي فقط) |
| `POST /refresh` | لا | لا (كوكي فقط) |
| `GET /me` | لا | لا |
| `PUT /me` | لا | لا (body فقط) |
| `GET /sessions` | لا | `skip`, `limit` (pagination بس، مش هوية) |
| `POST /revoke-all` | لا | لا |
| `PUT /me/password` | لا | لا (body فقط) |
| `DELETE /me` | لا | لا (body فقط) |

**نتيجة الجرد: صفر من أصل 10 endpoints في identity بياخد `user_id` أو
`tenant_id` مستهدَف كـpath/query parameter.** كل الـendpoints المحمية
الستة تعتمد حصريًا على `current_user.id` من الـJWT. **الجرد ده مكتمل
ونهائي بالنسبة لدومين identity نفسه تحديدًا — مفيش endpoint متبقي فيه
لسه محتاج اختبار من هذا النوع داخل identity.** (تنويه نطاق: الجرد ده
خاص بـidentity وبس — دومينات تانية في المشروع ممكن يكون فيها endpoints
بنمط "GET by ID" مختلف، وده خارج نطاق Phase 9، هيتغطى لو/لما تتراجع
الدومينات التانية.)

### الحالة النهائية

🔴 **لسه قائمة، لم تُصلَح.** الجزء المؤكَّد بالتنفيذ الفعلي:
- ✅ `register`/`login` بيسمحوا بأي tenant_id **موجود فعليًا** من غير
  أي تفويض (مؤكَّد بالتنفيذ الحي، خطر حقيقي).
- ✅ لا يوجد تسريب بيانات عبر الـendpoints المحمية الست (`me`, `sessions`,
  إلخ) — مؤكَّد بالتنفيذ الحي بـtenant حقيقي وبـtenant وهمي كلاهما.
- الخطر المتبقي الحقيقي محصور في: (أ) تسجيل/دخول مستخدمين تحت tenant
  مش بتاعهم (بدون تفويض)، و(ب) الاعتماد المعماري العام على هيدر غير
  موثوق كنمط متكرر عبر 30+ راوتر في المشروع كله (خارج نطاق identity
  وحده).

---

## ملاحظة جانبية: عزل tenant_id الفعلي وقت الاستعلام (مطلوب من الخطة، مرتبط بـPhase 7)

مؤكَّد من قراءة الكود: `UserRepository` و`RefreshTokenRepository` كلاهما
يطبّقان فلترة `tenant_id` حقيقية في كل استعلام (`and_(... , tenant_id
== ...)`)، مش مجرد وجود عمود. **الاستثناء الوحيد المكتشف:**
`WalletRepository.update_balances`/`freeze` (`repository.py:241-258`) —
لا يستقبلان `tenant_id` كمعامل ولا يفلتران بيه. **لكن لا يوجد أي
endpoint في identity بيستدعي الدالتين دول** (الاستخدام الوحيد لـ
`WalletRepository` من identity هو `get_by_user_id`/`create`، الاتنين
مفلترين صح). موثَّق كملاحظة نظافة كود خاصة بدومين `finance` الحقيقي
(المالك المنطقي لمنطق المحفظة)، مش استغلال فعلي متاح من identity.

---

## ملخص إضافي (من التحليل الأول، لسه صحيح)

- Rate limiting: مُطبَّق على 8/10 endpoints (غايب على `GET/PUT /me`)،
  مع fail-open لو Redis واقع.
- Input validation: Pydantic schemas على كل الـendpoints، `SecretStr`
  للباسورد، `forbidden` fields ضد mass-assignment في `update_user`.
  نقص بسيط: لا يوجد `max_length` على الباسورد.
- `identity_router`/`identity_protected_router` بدون `require_sector`
  — قرار معماري متعمَّد (identity مش قطاعي)، مش خطأ.
- `identity/router.py.bak`: نسخة قديمة على القرص، **غير محمَّلة أبدًا**
  (بايثون ما بيستوردش `.bak`)، كود ميت يستحق حذفًا لاحقًا.

---

## بيانات الاختبار المستخدمة (للـcleanup) — الحالة النهائية

| الكيان | المعرّف | الحالة النهائية |
|---|---|---|
| مستخدم تجريبي 1 | `test_audit_phase9@example.com` (id=9) | ✅ محذوف (wallets+auth_refresh_tokens+users) |
| مستخدم تجريبي 2 | `test_audit_phase9b@example.com` (id=10) | ✅ محذوف |
| مستخدم تجريبي A | `p9_tenantA@example.com` (id=12, tenant=1) | ✅ محذوف |
| مستخدم تجريبي B | `p9_tenantB@example.com` (id=13, tenant=2) | ✅ محذوف |
| Tenant تجريبي | `Phase9 Audit Tenant B` (id=2) | ✅ محذوف |

كل الكيانات الخمسة اتحذفت وتأكدت — **صفر بيانات اختبار متبقية في القاعدة
من جلسة Phase 9.**

### تصحيح افتراض أثناء التحقق النهائي

قبل إغلاق الجلسة، طلب المستخدم دليل `SELECT` فعلي (مش ملخص نصي) على
افتراض إن `id=9,10` **لسه المفروض موجودين** (بافتراض إنهم اتحفظوا عمدًا)
مقابل `id=12,13`/tenant `id=2` (المفروض محذوفين). تنفيذ الاستعلام
الفعلي أثبت إن الافتراض ده **غير دقيق**: الأربعة IDs (9, 10, 12, 13)
وtenant `id=2` **كلهم محذوفين بالفعل** — `id=9` و`id=10` اتحذفوا
سابقًا في نفس الجلسة (بموافقة صريحة وقتها، بعد كل اختبار على حدة)، مش
في الخطوة الأخيرة بس. **مفيش حذف غير مقصود حصل** — الحذف الرباعي كله
كان بموافقة صريحة، بس التسلسل الزمني لمين اتحذف إمتى كان مختلف عن
الافتراض الأولي. تم التحقق بـ`SELECT` مباشر على `users`/`academy_tenants`:

```
SELECT id, email, username, tenant_id, is_active FROM users WHERE id IN (9,10,12,13);
 -- (0 rows)

SELECT id, name, domain FROM academy_tenants WHERE id = 2;
 -- (0 rows)

SELECT id, email, username, tenant_id FROM users ORDER BY id;
 -- ids 2-8 فقط (مستخدمون قدامى من اختبارات P0/P1/Phase2 سابقة لهذه
 -- الجلسة تمامًا — لم تُلمَس إطلاقًا في Phase 9)
```

**الخلاصة:** قاعدة البيانات نظيفة تمامًا من أي أثر لجلسة Phase 9، وصفر
تأثير على أي بيانات سابقة أو غير متعلقة بالمهمة.

---

**التالي:** الـcleanup اكتمل والسيرفر التجريبي متوقف. الانتقال لمخرج 2
(الجرد الوظيفي) عند إعطاء الضوء الأخضر.

---

## [2026-08-10] — مخرج 2: الجرد الوظيفي الكامل لـ10 endpoints في identity

**المنهجية:** قراءة كاملة فعلية لـ`router.py` (146 سطر)، `service.py` (289
سطر)، `repository.py` (258 سطر)، `schemas.py` (70 سطر) — بدون تشغيل سيرفر
جديد في هذا المخرج (الأدلة الحية من مخرج 1 أعلاه، وأدلة Phase 1/9b
E2E الموثَّقة سابقًا في PROGRESS_LOG.md، اعتُمدت كتأكيد تشغيلي حيث تنطبق،
وذُكر ذلك صراحة تحت عمود "الحالة"). **لا افتراض من اسم الدالة في أي بند —
كل "شغال" هنا مبني على تتبّع فعلي لمسار الكود router → service → repository.**

| Method | Path | الغرض | Input | Output | الحالة |
|---|---|---|---|---|---|
| POST | `/identity/register` | تسجيل مستخدم جديد + إنشاء محفظة تلقائيًا + حماية idempotency (مفتاح `X-Idempotency-Key` أو مولَّد تلقائيًا) | `UserCreate` body (`username`, `email`, `password`, + حقول `UserBase` الاختيارية شاملة `birth_date`) + هيدر `X-Tenant-ID` (اختياري، افتراضي 1) | `201` + `UserResponse` | ✅ **شغال، مؤكَّد بالتنفيذ الحي** (مخرج 1، Request 1) |
| POST | `/identity/login` | مصادقة + إصدار كوكيز جلسة (access/refresh HttpOnly) | `UserLogin` body (`username_or_email`, `password`) + هيدر `X-Tenant-ID` | `200` + `{access_token, token_type, message, user_id, user: UserResponse}` + `Set-Cookie` × 2 | ✅ **شغال، مؤكَّد بالتنفيذ الحي بعد إصلاح Phase 9b** (مخرج 1) |
| POST | `/identity/logout` | إبطال الـrefresh token الحالي (لو موجود بالكوكي) + مسح الكوكيز | كوكي `refresh_token` (اختياري — الدالة لا تفشل لو غايب) | `200` + `{message}` | ✅ **شغال، مؤكَّد بـE2E حي سابق** (Phase 1، موثَّق في PROGRESS_LOG `[2026-08-08]`: "logout(200، مسح الكوكيز)") |
| POST | `/identity/refresh` | تدوير التوكنات (رفض التوكن القديم، إصدار زوج جديد) + فحص `session_version` و`tenant_id` من التوكن | كوكي `refresh_token` (إجباري) | `200` + `{message}` + كوكيز جديدة، أو `401` لو التوكن مفقود/منتهي/مُبطَل | ✅ **شغال، مؤكَّد بـE2E حي سابق** (Phase 1: "refresh(200، دوران الكوكيز)") |
| GET | `/identity/me` (protected) | جلب بيانات المستخدم الحالي | لا شيء (الهوية من الكوكي/JWT) | `200` + `UserResponse` | ✅ **شغال، مؤكَّد بالتنفيذ الحي** (مخرج 1، Request A) |
| PUT | `/identity/me` (protected) | تحديث الملف الشخصي (mass-assignment محمي عبر قائمة `forbidden`) | `UserUpdate` body (`email`, `name_ar`, `name_en`, `marriage_status`, `language_preference`, `profile_metadata`, `preferences`, `primary_wallet`, `is_active`) | `200` + `UserResponse` | ⚠️ **شغال جزئيًا** — كل الحقول المدعومة تعمل (مؤكَّد من الكود: `repository.update` بيطبّق `**kwargs` مباشرة بعد استبعاد `forbidden`). **لكن `birth_date` غير موجود إطلاقًا في `UserUpdate`** رغم وجوده في `UserBase`/`UserCreate` — قصور معروف وموثَّق سابقًا (`PROGRESS_LOG.md [2026-08-09]`)، الفرونت إند متوافق معه (حقل معطَّل بوضوح في `ProfileForm.tsx`، ليس bug جديد) |
| GET | `/identity/sessions` (protected) | عرض الجلسات النشطة (refresh tokens غير المُبطَلة) مع pagination | Query: `skip` (افتراضي 0)، `limit` (افتراضي 20، حد أقصى 100) | `200` + `List[SessionInfoResponse]` | ✅ **شغال، مؤكَّد بالتنفيذ الحي** (مخرج 1، Request C: `[]` — رد صحيح فارغ لعدم وجود جلسات مطابقة) |
| POST | `/identity/revoke-all` (protected) | إبطال كل الجلسات (رفع `session_version` + إبطال كل الـrefresh tokens غير المُبطَلة) | لا شيء | `200` + `{message, revoked_count}` | ✅ **شغال، مؤكَّد بـE2E حي سابق** (Phase 1: "revoke-all(200، revoked_count=1)") |
| PUT | `/identity/me/password` (protected) | تغيير كلمة المرور (يتطلب كلمة المرور القديمة صحيحة) + إبطال كل الجلسات تلقائيًا | `ChangePasswordRequest` body (`old_password`, `new_password`) | `200` + `{message}` | ✅ **شغال، مؤكَّد من الكود فقط** (مسار `router→service.change_password→repository.update` مباشر ومنطقي، نفس نمط `soft_delete_account` المؤكَّد جزئيًا أدناه؛ **لم يُختبَر حيًا في هذا المخرج تحديدًا** — لا يوجد تعارض أو شك يستدعي تشغيل سيرفر إضافي) |
| DELETE | `/identity/me` (protected) | تعطيل الحساب (soft delete: `is_active=False`) + إبطال كل الجلسات، يتطلب كلمة المرور | `DeleteAccountRequest` body (`password`) | `200` + `{message, account_status: "disabled"}` | ✅ **شغال من ناحية الباك إند (مؤكَّد من الكود)، لكن يتيم تمامًا من الفرونت إند — انظر مخرج 3** |

**ملاحظة جانبية (كود ميت):** `identity/router.py.bak` موجود على القرص
بجانب `router.py` — غير محمَّل أبدًا (بايثون لا يستورد `.bak`)، موثَّق
سابقًا في مخرج 1 كملاحظة إضافية، مُعاد ذكره هنا لاكتمال الجرد.

**النتيجة: صفر endpoint "مكسور" فعليًا من أصل 10.** كل الـ10 قابلة للوصول
ومسجَّلة صح في `main.py` (مؤكَّد سابقًا في Phase 6/Phase 4:
`IDENTITY_PATHS_COUNT=8` عبر OpenAPI schema — وده بيغطي `register`+`login`
من `router` العام زائد الـ6 المحمية من `protected_router`؛ الفرق بين
"8" و"10" في هذا الجرد هو `logout`/`refresh`، وهما مسجَّلان في `router`
العام بردهم لكنهم من نوع `POST` بلا `response_model` صريح فيغيّرش من
كونهم مسجَّلين وقابلين للوصول). القصور الوحيد المكتشف (`birth_date` في
`PUT /me`) قصور نطاق موثَّق ومقصود، مش عطل.

---

## [2026-08-10] — مخرج 3: تناغم Backend/Frontend لدومين identity

**المنهجية:** قراءة كاملة لـ`services/auth.service.ts` (150 سطر — الملف
الوحيد اللي بيستهدف مسارات `/identity/*` في الفرونت إند بالكامل، مؤكَّد
بـ`grep` شامل لـ`/identity/` عبر 27 ملف)، `hooks/identity/useAuth.ts`،
`hooks/identity/useUserProfile.ts`، `providers/AuthProvider.tsx`،
`lib/api-client.ts` (منطق الـ401/refresh)، وكل مكوّنات
`components/identity/*` (6 ملفات) والصفحات المستهلِكة لها.

### مصفوفة الاستهلاك (كل الـ10 endpoints)

| Endpoint | مُستهلَك؟ | المسار الكامل (service → hook → component/page) |
|---|---|---|
| `POST /register` | ✅ نعم | `AuthService.register` → `useRegister` → `RegisterForm.tsx` → `app/(auth)/register/page.tsx` |
| `POST /login` | ✅ نعم | `AuthService.login` → `useLogin` → `LoginForm.tsx` → `app/(auth)/login/page.tsx` |
| `POST /logout` | ✅ نعم | `AuthService.logout` → `useLogout` → `sidebar.tsx` + `navbar.tsx` (موثَّق سابقًا `[2026-08-09]`) |
| `POST /refresh` | ✅ نعم | `AuthService.refreshToken` → مُستدعاة مباشرة (بدون hook) من interceptor الـ401 في `lib/api-client.ts` (تجديد تلقائي شفاف عند أي 401 غير bootstrap) |
| `GET /me` | ✅ نعم | `AuthService.getMe` → `useMe`/`useCurrentUser`/`useAuth` → `AuthProvider.tsx` (كل تحميل صفحة) + `profile/page.tsx` (تمرير `user` لـ`ProfileForm`) |
| `PUT /me` | ✅ نعم | `AuthService.updateProfile` → `useUpdateProfile` → `ProfileForm.tsx` → `profile/page.tsx` |
| `GET /sessions` | ✅ نعم | `AuthService.getActiveSessions` → `useActiveSessions` → **مستهلَك من مسارين مستقلين تمامًا** (انظر ملاحظة التكرار تحت) |
| `POST /revoke-all` | ✅ نعم | `AuthService.revokeAllSessions` → `useRevokeAllSessions` → نفس المسارين المستقلين تحت |
| `PUT /me/password` | ✅ نعم | `AuthService.changePassword` → `useChangePassword` → `ChangePasswordForm.tsx` → `profile/page.tsx` |
| `DELETE /me` | 🔴 **لا — يتيم بالكامل** | لا يوجد `AuthService.deleteAccount`/أي دالة مكافئة في `auth.service.ts`، ولا أي استدعاء لـ`DELETE /identity/me` في كامل `eppne-web` (تأكَّد بـ`grep` عن `حذف الحساب`/`deleteAccount`/`soft_delete`/`DeleteAccountRequest` — صفر نتائج). **لا توجد أي واجهة لحذف/تعطيل الحساب في الفرونت إند إطلاقًا** |

### 🟡 endpoint يتيم: `DELETE /identity/me`

الباك إند يوفّر مسارًا كاملاً وشغّالاً (مؤكَّد من الكود في مخرج 2) لتعطيل
الحساب ذاتيًا (soft delete بكلمة مرور)، لكن **لا يوجد أي زر أو صفحة أو
حتى دالة service في الفرونت إند تستدعيه**. هذا مش خطأ برمجي (مفيش استدعاء
مكسور)، لكن فجوة وظيفية: المستخدم لا يملك أي طريقة من الواجهة لحذف/تعطيل
حسابه، رغم أن الباك إند يدعم ذلك بالكامل ومُختبَر منطقيًا. **قرار
معالجتها (إضافة UI أو ترك الوضع كما هو) خارج نطاق هذا المخرج القرائي —
يحتاج قرار منتج/مهمة منفصلة بموافقة صريحة.**

### صفر استدعاء فرونت إند لـendpoint غير موجود أو معطوب

فحص شامل لكل الدوال التسع في `auth.service.ts`: **كل مسار مُستهدَف
(`/identity/register`, `/identity/login`, `/identity/refresh`,
`/identity/logout`, `/identity/revoke-all`, `/identity/sessions`,
`/identity/me` [GET/PUT], `/identity/me/password`) مطابق حرفيًا لمسار
حقيقي مُعرَّف فعليًا في `router.py`/`protected_router` (مخرج 2 أعلاه).**
صفر مسار وهمي أو قديم (بعكس `api-types.ts` المولَّد آليًا، الذي لا يزال
يحمل مسارات `/auth/auth/*` المحذوفة — لكن هذا الملف **غير مُستخدَم
كمصدر مسارات فعليًا** في `auth.service.ts`، فقط كمصدر *أنواع* TypeScript
عبر `components['schemas'][...]`، والمسارات نفسها Hardcoded كنصوص في
كل استدعاء `apiClient`، موثَّق ومؤكَّد سابقًا في `Phase 5`).

**فحص إضافي: هل الأنواع المستوردة من `api-types.ts` (الملف القديم) لسه
متوافقة شكليًا مع استجابات الباك إند الفعلية رغم قِدَم الملف؟** فُحص
تحديدًا `UserUpdate` و`RevokeAllSessionsResponse` (الأكثر عرضة للتغيير):
كلاهما **متطابقان حرفيًا** مع `schemas.py` الحالي (نفس الحقول بالضبط) —
مصادفة إن هذين الـschemas تحديدًا لم يتغيّرا منذ توليد الملف، رغم قِدَمه
العام (موثَّق في Phase 5). لا يوجد خطر type-mismatch فعلي حاليًا على
هذين الجزئين تحديدًا.

### ملاحظة تكرار وظيفي (ليست bug — كفاءة/صيانة فقط)

ميزة "الجلسات النشطة + إبطال الكل" مُنفَّذة **مرتين بشكل مستقل تمامًا**:
1. `components/identity/SessionsList.tsx` + `SessionCard.tsx` (تُستهلَك
   من صفحتين: `app/(dashboard)/profile/page.tsx` و
   `app/(dashboard)/privacy/settings/page.tsx`).
2. `app/(dashboard)/settings/sessions/page.tsx` — تطبيق منفصل بالكامل
   (JSX مكرر مختلف الشكل، نفس الـhooks `useActiveSessions`/
   `useRevokeAllSessions` بالضبط).

كلا المسارين يستهلكان نفس الـendpoints بشكل صحيح ومتوافق — **مفيش خطر
وظيفي أو تعارض بيانات**، لكنها ازدواجية كود (3 مسارات UI مختلفة لنفس
الميزة عبر صفحتين + مكوّن منفصل) تستحق توحيدًا لاحقًا كتنظيف كود منفصل.

### `POST /identity/refresh` — حالة خاصة في الاستهلاك

بعكس باقي الـendpoints، `refreshToken` **مالهاش hook مخصَّص في
`useAuth.ts`** — بيتم استدعاؤه مباشرة من داخل axios interceptor في
`lib/api-client.ts` عند أي `401` مش من نوع bootstrap call (مؤكَّد من
الكود، سطر 78-89 هناك). هذا نمط سليم ومقصود (تجديد شفاف بدون تدخل UI)،
مش فجوة استهلاك.

### الخلاصة

| البند | النتيجة |
|---|---|
| Endpoints مُستهلَكة فعليًا | 9 من 10 |
| Endpoints يتيمة | 1 (`DELETE /identity/me`) |
| استدعاءات فرونت إند لـendpoint غير موجود/معطوب | 0 |
| Type mismatch فعلي مكتشف | 0 (رغم قِدَم `api-types.ts` عمومًا) |
| ملاحظات تنظيف كود غير عاجلة | تكرار SessionsList (3 مسارات UI) |

---

**الحالة النهائية لـPhase 9 بالكامل:** المخرجات الثلاثة (1: التقرير
الأمني، 2: الجرد الوظيفي، 3: تناغم Backend/Frontend) **مكتملة**. صفر
تعديل كود تم في هذين المخرجين (2 و3) — قراءة وتوثيق فقط، حسب الالتزام
الصارم بـread-only.
