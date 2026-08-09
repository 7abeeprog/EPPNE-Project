# Phase 4 — حذف دومين auth بالكامل من الباك إند

> ملف جديد مستقل، مبني على فحص فعلي للكود بتاريخ 2026-08-09 (grep شامل
> على `eppne-backend` و`eppne-web`، قراءة كل ملفات `domains/auth/*` و
> `domains/identity/*` المعنية، ومراجعة `main.py`). **هذا الملف نطاق
> فقط — صفر تنفيذ حتى الآن.**

## 🚦 بوابة حاكمة قبل أي تنفيذ لـ Phase 4 — لازم تُحسم أولًا

فحص `git status` الحالي و`PROGRESS_LOG.md` كشف حاجتين لازم الانتباه
لهم قبل أي تنفيذ فعلي (مش بس تخطيط) لـPhase 4:

1. **Phase 3 لسه مش committed.** كل ملفات الرينيم (`components/auth→identity`,
   `hooks/auth→identity`) وملفات الـimport الـ15 لسه في working tree كـ
   uncommitted changes (`git status` بيوريها `M`/`RM` دلوقتي، آخر commit
   هو `5b1d241` بتاريخ Phase 2 بس).
2. **قرار موثّق صراحة في `PROGRESS_LOG.md` (نهاية إدخال Phase 3):**
   > "التوقف الكامل عن أي تقدم إضافي في Phase 3 أو **أي Phase جديدة** لحد
   > ما يترجع للمستخدم ويتاخد قرار صريح بخصوص باغ الـWeb3 ده"

   السبب: باغ `lit`/`@reown/appkit-ui` (موجود من Initial commit، غير
   متعلق بـauth/identity إطلاقًا) بيكسر كل صفحات الموقع بـ500 في بيئة
   الديف، وده بيمنع اختبار logout يدويًا في متصفح حقيقي — شرط Phase 3
   الإجباري غير المكتمل.

**الخلاصة:** كتابة ملف الخطة ده (نطاق فقط) متوافقة مع طلبك الصريح
("بدون أي تنفيذ"). لكن أي تنفيذ فعلي لـPhase 4 — حتى لو backend-only
ومحصور، وحتى بعد حل §3 بأسلوب frontend-only اللي مايلمسش أي كود
متأثر بباغ الـWeb3 — هيكون تعطيل لقرار موثّق سابق بالتوقف عن "أي Phase
جديدة". **محتاج قرار صريح منك تحديدًا في جلسة منفصلة** قبل أي تنفيذ:
إما (أ) حسم باغ الـWeb3 وcommit لـPhase 3 أولًا، أو (ب) تأكيد صريح إنك
عايز تكمل Phase 4 رغم البلوكر ده.

---

## 1) قائمة كاملة بملفات `app/domains/auth/*` المرشحة للحذف (7 ملفات)

| # | الملف | السطور | الوصف |
|---|---|---|---|
| 1 | `__init__.py` | 0 | فارغ |
| 2 | `models.py` | 7 | **مش نموذج فعلي أصلًا** — re-export shim لـ `RefreshToken` من `identity.models`، وتعليقه بالحرف الواحد بيقول "حتى يُحذف دومين auth (Phase 4)" |
| 3 | `schemas.py` | 117 | `LoginRequest/Response`, `RefreshTokenRequest/Response`, `LogoutRequest`, `RevokeAllSessionsRequest/Response`, `SessionInfoResponse`, `TokenResponse` |
| 4 | `repository.py` | 137 | `AuthRepository` — CRUD على `RefreshToken` (المستورد من identity) |
| 5 | `service.py` | 214 | `AuthService` — منطق login/refresh/logout/revoke، يستخدم `jwt_service` |
| 6 | `router.py` | 121 | `router` + `protected_router`، prefix `/auth`: `POST /login`, `POST /refresh`, `POST /logout`, `POST /revoke-all`, `GET /sessions` |
| 7 | `jwt_service.py` | 143 | `JWTService` class + دوال توافقية (تفصيل في §4) |

**المجموع: 732 سطر، 7 ملفات، مجلد `app/domains/auth/` بالكامل.**

## 2) استيرادات خارجية من `domains.auth` — فحص شامل بالـgrep

بحث عن `domains\.auth|domains/auth` في كل `eppne-backend` (كود + tests +
alembic): **صفر استيراد خارجي غير main.py.**

- كل الاستيرادات الداخلية (`service.py`→`repository.py`/`jwt_service.py`/
  `models.py`, `router.py`→`service.py`/`schemas.py`) محصورة **داخل
  المجلد نفسه**.
- الاستيراد الوحيد من خارج المجلد: `app/main.py:39`
  ```python
  from app.domains.auth.router import router as auth_router, protected_router as auth_protected_router
  ```
  ومسجَّل في `main.py:311-315` بـ `prefix="/api"` تحت tag `"Authentication"`.
- `app/main.py.bak` (ملف قديم committed في git، لاحظ الامتداد `.bak` —
  Python مش بيحمّله، مش نشط) فيه نفس الاستيراد. **خارج نطاق Phase 4
  فعليًا** (مش كود حي) لكن يستاهل تنضيف لاحقًا — نفس الحال لـ
  `app/domains/identity/router.py.bak` و`app/domains/invitations/router.py.bak`
  الموجودين في git كملفات ميتة.
- **لا يوجد أي test يستورد من `domains.auth`.**
- **لا يوجد أي alembic migration بيرجع لـ`auth`.**

**النتيجة: الحذف الآمن للباك إند = حذف المجلد + إزالة 3 أسطر من `main.py`
(الاستيراد سطر 39 + التسجيل سطرين 311-315) — لا حاجة لأي تعديل تاني في
أي دومين آخر بالباك إند.**

## 3) عميل الفرونت إند — هل فيه استخدام فعلي لـ `/api/auth/*`؟

**لا. صفر استدعاء HTTP فعلي.** فحص دقيق (grep مخصص لأنماط
`apiClient/axios/fetch(...'/auth...)`، بالإضافة لأي `/auth/` حرفي في
كل `.ts`/`.tsx`):

- `services/auth.service.ts` (الاسم بس فيه "auth" — **كل الـ8 دوال جواه
  بتنادي `/identity/*` فعليًا**: `/identity/login`, `/identity/register`,
  `/identity/refresh`, `/identity/logout`, `/identity/revoke-all`,
  `/identity/sessions`, `/identity/me`, `/identity/me/password`).
- الظهورات الوحيدة الباقية لسلسلة `/auth/`: (أ) `app/(auth)/login` و
  `app/(auth)/register` — **مسارات صفحات Next.js للتنقل** (`<Link
  href="/auth/login">`)، مش API calls، وخارج النطاق زي ما اتفقنا في
  Phase 3، و(ب) `src/lib/api-types.ts` — أنواع TypeScript مولّدة آليًا
  من OpenAPI schema الحالي (فيها `/auth/auth/login` إلخ لأن كلا
  الـrouter-ين شغالين دلوقتي)، **ملف أنواع فقط، مفيش كود بينفّذه**.

**الخلاصة المؤكدة: التحويل الكامل لـ`/identity/*` حصل فعليًا في Phase 2
(`5b1d241`) — مفيش أي عميل فرونت إند لازم يتحول قبل الحذف.**

### تبعية type-level واحدة لازم تتنضف قبل إعادة توليد الأنواع: `RevokeAllSessionsResponse`

`auth.service.ts:6` بيستورد `RevokeAllSessionsResponse` من
`components['schemas']` (مولّد من OpenAPI). النوع ده **معرَّف حاليًا في
`auth/schemas.py` بس** (`response_model=RevokeAllSessionsResponse` على
`POST /auth/revoke-all`). المقابل الفعلي المُستخدَم — `POST
/identity/revoke-all` (`identity/router.py:123-128`) — **مالوش
response_model أصلًا**، بيرجع `dict` خام صحيح وظيفيًا لكن بدون اسم
schema موثَّق.

**مش خلل وظيفي — المشكلة type-level بحتة:** لو اتحذف auth وأُعيد توليد
`api-types.ts` من غير معالجة، اسم `RevokeAllSessionsResponse` هيختفي من
الملف المولَّد، و`tsc --noEmit` هيفشل على `auth.service.ts:6` (رغم إن
الـendpoint نفسه شغال 100%).

**القرار المعتمد (frontend-only، صفر لمس لـidentity backend، أقل عدد
ملفات ممكن):** تحويل `type RevokeAllSessionsResponse =
components['schemas']['RevokeAllSessionsResponse']` (سطر 6 حاليًا) إلى
`interface` محلي معرَّف يدويًا جوه `auth.service.ts` نفسه — بنفس النمط
المسبوق تمامًا بالملف لـ`IdentityLoginResponse` (سطور 15-21، ومعاه
تعليق مشابه يشرح السبب). **ملف واحد بس يتأثر (`auth.service.ts`)، صفر
تعديل على `identity/router.py` أو `identity/schemas.py`.**

(`SessionInfoResponse` مالهاش نفس المشكلة — معرَّفة فعليًا في
`identity/schemas.py` ومربوطة بـ`response_model` على `GET
/identity/sessions`، فهتفضل موجودة في الأنواع المولَّدة بعد الحذف
بدون أي تدخل.)

## 4) `auth/jwt_service.py` تحديدًا — فحص خطر tenant_id=1 المُثبَّت

الملف فيه طبقتين:

1. **`class JWTService`** (سطور 12-88) — منطق سليم، بيستقبل `tenant_id`
   كـ parameter حقيقي من الكولر. الـ instance الوحيد `jwt_service`
   (سطر 91) **يُستخدم فقط داخل `auth/service.py`** (7 نداءات، كلها
   بتمرّر `tenant_id` حقيقي من الطلب — مش مُثبَّت).
2. **دوال توافقية (Adapter Functions, سطور 98-144)** — دي المُوثَّقة في
   `PROJECT_AUDIT.md` §5.2 كخطر أمني: `create_access_token()` و
   `create_refresh_token()` (module-level، مش method) بيثبّتوا
   `tenant_id=1` **hardcoded** (سطور 109 و116) عند مناداة الـclass method
   الحقيقي. وكمان `revoke_refresh_token()`/`revoke_all_user_tokens()`
   (سطور 130-144) — stub functions فعليًا، بترجع `True`/`0` من غير أي
   منطق حقيقي، مجرد `logger.warning`.

**فحص الاستيراد:** بحث عن `jwt_service` في كل `eppne-backend` — **كل
النتائج داخل `domains/auth/` نفسه فقط** (`service.py` بيستورد الـ
instance، `jwt_service.py` بيعرّف نفسه). **صفر استيراد لأي حاجة من
الملف ده — لا الـclass، ولا الـinstance، ولا أي دالة توافقية — من أي
مكان تاني في الباك إند (لا identity، لا core، لا أي دومين تاني، لا
tests).**

**الخلاصة: خطر `tenant_id=1` المُثبَّت في `PROJECT_AUDIT.md` §5.2 غير
مُستغَل فعليًا حاليًا (dead code من ناحية الاستدعاء الخارجي) — لكنه
سلاح محشو في درج مفتوح: أي استيراد مستقبلي بالغلط (`from
app.domains.auth.jwt_service import create_access_token`) هيولّد توكن
بـtenant_id=1 لأي مستخدم. حذف الملف بالكامل في Phase 4 بيقفل الثغرة دي
نهائيًا، مش بس يتجاهلها.**

## 5) خطة التنفيذ المقترحة (لسه بدون تنفيذ — للمراجعة فقط)

بالترتيب، لو اتأخذ قرار المُضي قُدمًا (راجع البوابة الحاكمة في الأول):

1. **Frontend (ملف واحد):** في `auth.service.ts:6`، استبدال
   `type RevokeAllSessionsResponse = components['schemas'][...]` بـ
   `interface` محلي (§3 أعلاه). صفر لمس لأي ملف باك إند في الخطوة دي.
2. **Backend:** حذف `app/domains/auth/` بالكامل (7 ملفات).
3. **Backend:** إزالة سطر الاستيراد (39) وسطرين التسجيل (311-315) من
   `app/main.py`.
4. **Backend:** `pytest` كامل + تشغيل السيرفر محليًا + تأكيد
   `GET /docs` (OpenAPI) ما فيهاش أي `/auth/*` path تاني، وإن كل مسارات
   `/identity/*` لسه شغالة.
5. **Frontend:** إعادة توليد `src/lib/api-types.ts` من الـOpenAPI schema
   الجديد (بعد خطوة 4)، ثم `npx tsc --noEmit -p tsconfig.json` والتأكد
   من `exit code 0`.
6. **توثيق:** إدخال جديد في `PROGRESS_LOG.md` (بدون لمس القديم) يوثّق
   اكتمال Phase 4 وإغلاق خطر `PROJECT_AUDIT.md` §5.2.

**خارج النطاق صراحة:** إعادة تسمية `services/auth.service.ts` أو
`hooks/identity/useAuth.ts` نفسها (الاسم الداخلي `AuthService`/`useAuth`
— دي تسمية frontend-side مش جزء من دمج auth/identity الـbackend، ومفيش
داعي تقني للمسها). تنضيف ملفات `.bak` الثلاثة (§2) — مهمة منفصلة صغيرة،
مش جزء عضوي من Phase 4.
