# سجل التقدم (Progress Log)

سجل تراكمي لكل مهمة مكتملة في المشروع. كل مهمة جديدة تُضاف كسطر جديد في
الأسفل. لا يُحذف أو يُعدَّل أي إدخال قديم هنا أبداً.

---

## [2026-08-08] — P0: إصلاح الثغرات الأمنية الحرجة

**الحالة:** ✅ مكتمل

**بنود PROJECT_AUDIT.md التي عولجت:**
- قسم 4.3: عزل tenant_id في iot (6 جداول) وprivacy (4 جداول) — تمت الإضافة
  عبر 10 migrations منفصلة، طُبِّقت بنجاح على قاعدة البيانات المحلية
- قسم 5.3: حماية PUT /api/ai/routing — تم تغيير الاعتماد إلى
  get_current_superuser
- قسم 5.1: توحيد حماية auth_router باستخدام core/security.py القوي
  (يفحص session_version) بدل api/deps.py الأضعف

**ملاحظة مهمة:** هذا إصلاح لـauth_router فقط، وليس حلاً لتعارض auth/identity
الأشمل (قسم 2.1 من PROJECT_AUDIT.md) — هذا التعارض لا يزال قائماً وسيُعالَج
في مهمة منفصلة (P1).

**الاختبارات:** 5 smoke tests جديدة أُضيفت، كلها ناجحة (5/5 PASSED)

**الملفات المتأثرة:** iot/models.py, privacy/models.py, iot/repository.py,
iot/service.py, iot/router.py, privacy/repository.py, privacy/service.py,
privacy/router.py, app/domains/auth/router.py, main.py, 10 ملفات migration
جديدة في migrations/versions/

---

## [2026-08-08] — ملاحظة أمنية مكتشفة أثناء تحليل P1 (دمج auth في identity)

**الحالة:** ⚠️ اكتشاف موثَّق — لم يُعالَج بعد (سيُعالَج ضمن مهمة P1 الجارية)

**الاكتشاف:** أثناء تحليل الفرونت إند تمهيدًا لدمج auth داخل identity (قسم
2.1 و7 من PROJECT_AUDIT.md)، تبيّن أن `providers/AuthProvider.tsx` — وهو
الـ AuthProvider **الفعلي المُركَّب** في `app/providers.tsx` (وليس أي من
النسختين تحت `components/auth/` أو `components/identity/`، وكلاهما غير
مُركَّب فعليًا) — يُهيّئ حالة المصادقة بالكامل من `localStorage`
(`access_token`, `user`) دون أي استدعاء فعلي للسيرفر (لا `/identity/me` ولا
أي endpoint مكافئ) للتحقق من أن الجلسة لا تزال صالحة. القرار بالسماح/رفض
عرض المحتوى المحمي والتوجيه لصفحة الدخول يعتمد فقط على وجود توكن في
`localStorage`، وهو أمر يمكن التلاعب به من طرف العميل ولا يعكس حالة الجلسة
الحقيقية في الباك إند (مثال: توكن مُبطَل عبر "تسجيل خروج من كل الأجهزة" يبقى
يُظهر المستخدم "مسجَّل دخول" في الواجهة حتى انتهاء صلاحيته الطبيعية).

**العلاقة بثغرات P0:** هذه ملاحظة منفصلة تمامًا عن ثغرات P0 الأصلية
(المذكورة أعلاه) — اكتُشفت أثناء تحليل P1، وليست جزءًا من نطاق P0 المكتمل.

**المعالجة المخطَّطة:** ضمن خطة دمج auth→identity الجارية (Phase 2)، سيُعاد
بناء `providers/AuthProvider.tsx` ليعتمد على استعلام حقيقي لـ
`GET /identity/me` (عبر الكوكي HttpOnly) بدل الوثوق بـ `localStorage`.

---

## [2026-08-08] — P1 (Backend، Phase 0+1 من خطة دمج auth→identity): إصلاح
انهيارات المصادقة الحرجة + بناء آلية جلسة حقيقية في identity

**الحالة:** ✅ Phase 0 وPhase 1 (Backend فقط) مكتملتان ومُتحقَّق منهما فعليًا
— Phase 2 (Frontend) لم تبدأ بعد، بانتظار موافقة صريحة في جلسة منفصلة.

**السياق:** أثناء التخطيط لدمج auth داخل identity (قسم 2.1 و7 من
PROJECT_AUDIT.md)، تبيّن أن identity — رغم كونه الأصح هيكليًا — كان **غير
قادر على تنفيذ عملية دخول واحدة ناجحة** بسبب سلسلة من الأعطال الحرجة
المتشابكة. التفاصيل الكاملة والتحليل في الخطة المعتمدة
(`delightful-kindling-wigderson.md`). هذا الإدخال يوثّق ما أُصلِح فعليًا.

**Phase 0 — إصلاح 3 انهيارات كانت تكسر كل تسجيل دخول (auth وidentity معًا)
وكل طلب مُصادَق عبر الـ32 دومين الأخرى:**
- `auth/jwt_service.py::JWTService`: كان لا يفكّ `SecretStr` الخاص بـ
  `SECRET_KEY` (`getattr(settings, 'SECRET_KEY', 'default_secret')`)، ما
  كان يجعل `jose` يرفع `JWSError` عند أي إصدار توكن — تم تأكيد ذلك فعليًا
  بتشغيله ضد الـ venv الحقيقي قبل الإصلاح.
- `api/deps.py::get_current_user` (+ `get_current_user_optional`) و
  `core/security.py::get_current_user`: كانا يستدعيان
  `UserRepository.get_by_id(int(user_id))` بمعامل واحد، بينما التوقيع
  الفعلي يتطلب `tenant_id` إجباريًا → `TypeError` 500 على أي طلب مُصادَق في
  كامل التطبيق. تم استخراج `tenant_id` من الـ payload وتمريره.
- `identity_router` كان مسجَّلاً في `main.py` عبر حلقة `routers_config`
  العامة مع `Depends(require_sector("identity"))`، وهذا يتطلب Bearer token
  صالح مسبقًا — أي أن `/api/identity/login` و`/register` كانا غير قابلين
  للوصول أصلًا (تسلسل دائري). تم تقسيم `identity/router.py` إلى `router`
  عام (register/login/refresh/logout) و`protected_router` محمي (بنفس نمط
  `auth/router.py`)، وتحديث تسجيلهما في `main.py`.

**اكتشافان إضافيان حجبا حتى اختبار Phase 0 نفسه (عولجا بموافقة صريحة):**
- `identity/models.py`: علاقة `User.tenant` كانت تشير لكلاس غير موجود
  (`academy.models.Tenant` بدل `AcademyTenant`) — تُسبب
  `InvalidRequestError` عند أول استعلام يلمس `User`.
- `identity/router.py`: كل الـ endpoints (9 مواضع) كانت تُعلن
  `tenant_id: int = Depends(get_current_tenant)` بينما `get_current_tenant`
  يُرجع كائن `SimpleTenant` (له `.id`) وليس `int` — FastAPI لا يفرض تطابق
  النوع مع Depends، فكان `tenant_id` كائن `SimpleTenant` فعليًا يُمرَّر
  لاستعلامات SQL مباشرة → خطأ قاعدة بيانات. تم تصحيحها لاستخدام
  `tenant: SimpleTenant = Depends(...)` ثم `tenant.id`.

**Phase 1 — بناء آلية جلسة حقيقية في identity (بدل الاعتماد على auth):**
- اكتُشف أن `identity/service.py` كان يعتمد بالكامل على
  `auth/jwt_service.py` لإصدار/إبطال التوكنات، وأن دوال الإبطال هناك
  (`revoke_refresh_token`, `revoke_all_user_tokens`) **stubs لا تفعل شيئًا
  فعليًا** (تُرجع True/0 فقط) — أي أن logout/revoke-all/change-password/
  delete-account في identity لم تكن تُبطل أي شيء في القاعدة فعليًا.
- اكتُشف أيضًا أن `generate_tokens` لم يكن يُخزّن أي refresh token في
  القاعدة إطلاقًا، وأن `refresh_tokens` كان يستدعي `verify_refresh_token`
  ويتعامل مع نتيجته كـ dict بينما الدالة تُرجع string — أي أن **endpoint
  التجديد لم يكن يعمل إطلاقًا من قبل**.
- نُقل موديل `RefreshToken` من `auth/models.py` إلى `identity/models.py`
  (نفس الجدول `auth_refresh_tokens`، بدون migration جديدة). `auth/models.py`
  أصبح re-export shim مؤقت (auth ما زال حيًا حتى Phase 4 من خطة الدمج).
  أُضيف `RefreshTokenRepository` إلى `identity/repository.py` (منطق حقيقي
  منقول من `AuthRepository`).
- أُعيدت كتابة `UserService` بالكامل لتستخدم `core.security.create_access_
  token/create_refresh_token/decode_token` (الصحيحة أصلًا) بدل
  `auth/jwt_service`، مع تخزين واسترجاع وإبطال حقيقي لكل refresh token عبر
  `RefreshTokenRepository`. أُضيف `get_active_sessions` و
  `GET /identity/sessions` (endpoint كان موجودًا في auth فقط،
  `GET /api/auth/sessions`، وغائبًا تمامًا عن identity).

**3 أعطال إضافية اكتُشفت أثناء اختبار Phase 1 فعليًا وعولجت (كلها داخل
نطاق الملفات المُعاد كتابتها):**
- `begin_nested()` في `register`/`revoke_all_sessions`/`change_password`/
  `soft_delete_account` كانت تُغلّف استدعاءات repository تُنفّذ
  `db.commit()` داخليًا — الـ commit داخل معاملة متداخلة (SAVEPOINT) يكسرها
  فيرمي `Can't operate on closed transaction`. أُزيل الغلاف غير الفعّال.
- `core/security.py::get_current_user` لم يكن يدعم الكوكيز إطلاقًا (Bearer
  header فقط) — بعد تحويل `identity` (القائم على الكوكيز) للاعتماد على
  core.security في Phase 0/1، كان هذا يكسر كل طلب `/identity/me` وما شابه.
  أُضيف دعم `Cookie(alias="access_token")` كمصدر بديل للـ Bearer.
- `UserService.get_user`: مسار الكاش في Redis كان يُعيد بناء كائن `User()`
  جزئي (7 حقول فقط) لا يكفي لتلبية `UserResponse` الكامل، فيفشل
  `GET /me` بخطأ تحقق (`ResponseValidationError`) في أي طلب ثانٍ خلال مدة
  صلاحية الكاش. أُزيل مسار القراءة من الكاش (يُقرأ من القاعدة دائمًا الآن).

**الاختبارات:** لا توجد smoke tests دائمة جديدة بعد (ستُضاف في Phase 5 من
خطة الدمج). تم التحقق الفعلي عبر سكربت اختبار E2E غير دائم
(`httpx.AsyncClient` + `ASGITransport`، حلقة أحداث واحدة مطابقة لبيئة
الإنتاج) ضد قاعدة بيانات وRedis محليين فعليين: register(201) → login(200،
كوكيز HttpOnly حقيقية) → GET /me(200) → GET /sessions(200، يُظهر جلسة حقيقية
من القاعدة) → refresh(200، دوران الكوكيز) → GET /me بعد refresh(200) →
revoke-all(200، revoked_count=1) → GET /me بعد revoke(401 "Session has been
revoked" — يثبت أن الإبطال حقيقي وليس شكليًا) → logout(200، مسح الكوكيز).

**الملفات المتأثرة (Backend فقط، Frontend لم يُلمس بعد):**
`app/domains/auth/jwt_service.py`, `app/domains/auth/models.py`,
`app/domains/auth/router.py` (بدون تغيير من هذه المهمة، كان معدَّلاً مسبقًا
ضمن P0)، `app/api/deps.py`, `app/core/security.py`,
`app/domains/identity/models.py`, `app/domains/identity/repository.py`,
`app/domains/identity/schemas.py`, `app/domains/identity/service.py`,
`app/domains/identity/router.py`, `app/main.py`, `scripts/seed_tenant.py`,
`scripts/create_superuser.py`, `migrations/env.py`, `alembic/env.py`.

**التالي:** Phase 2 (إعادة بناء الفرونت إند على أساس الكود الشغّال،
cookie-only بالكامل) — **لن يبدأ إلا بموافقة صريحة في جلسة منفصلة**، حسب
طلب المستخدم. auth (Backend) ما زال حيًا ومسجَّلاً في `main.py` ولم يُحذف
بعد (سيُحذف في Phase 4 من خطة الدمج).

---

## [2026-08-09] — ملاحظة مكتشفة أثناء تنفيذ Phase 2 (دمج auth→identity،
الفرونت إند): `birth_date` غير قابل للتحديث فعليًا عبر `PUT /identity/me`

**الحالة:** ⚠️ اكتشاف موثَّق — لم يُعالَج، مؤجَّل كمهمة مستقلة لاحقة (خارج
نطاق Phase 2)

**الاكتشاف:** أثناء نقل `ProfileForm.tsx` من `components/identity/` (كان
معطَّلاً بالكامل، يستورد `useUpdateProfile` من `hooks/identity/useUserProfile`
غير الموجود إطلاقًا) إلى `components/auth/` وربطه بـ hook حقيقي مكتوب حديثًا
(`hooks/auth/useUserProfile.ts`) مُطابِق لمخطط `UserUpdate` الفعلي في الباك
إند (`app/domains/identity/schemas.py`)، تبيّن أن حقل `birth_date` **غير
موجود إطلاقًا** في `UserUpdate` (الحقول المتاحة: `email`, `name_ar`,
`name_en`, `marriage_status`, `language_preference`, `profile_metadata`,
`preferences`, `primary_wallet`, `is_active`). الفورم الأصلي كان يرسل
`birth_date` ضمن جسم التحديث رغم ذلك — لكن بما أن الـ hook الذي يستدعيه كان
مفقودًا أصلًا، **هذا المسار لم يُنفَّذ أو يُختبَر فعليًا من قبل** (كود ميت)،
فلم يُكتشَف الخلل حتى الآن.

**القرار المؤقت (بموافقة صريحة):** إبقاء حقل تاريخ الميلاد ظاهرًا في
`components/auth/ProfileForm.tsx` كحقل للقراءة فقط (`disabled`/`readOnly`)
مع ملاحظة نصية للمستخدم أنه غير قابل للتعديل من هنا حاليًا، بدل حذفه
بالكامل أو تركه يبدو قابلاً للتعديل بينما التغيير لا يُحفَظ فعليًا (كان
سيُنتج تجربة مستخدم مضلِّلة: toast نجاح دون أي تحديث فعلي في القاعدة).

**العمل المستقل المطلوب لاحقًا (خارج نطاق auth/identity الحالي):** إضافة
`birth_date: date | None` إلى `UserUpdate` في
`app/domains/identity/schemas.py`، وتحديث `UserService.update_user` في
`app/domains/identity/service.py` للتعامل معه فعليًا، ثم إعادة تفعيل حقل
الإدخال (بدل القراءة فقط) في `ProfileForm.tsx`.

**الملفات المتأثرة:** `eppne-web/components/auth/ProfileForm.tsx`,
`eppne-web/hooks/auth/useUserProfile.ts`.

---

## [2026-08-09] — إصلاح: زرّا تسجيل الخروج في السايدبار والـ navbar غير
مربوطين بآلية logout الصحيحة

**الحالة:** ✅ مكتمل، تم التأكد يدويًا في المتصفح (بدليل قاطع من المستخدم)

**الاكتشاف:** بعد اكتمال إعادة بناء الفرونت إند (Phase 2 من خطة دمج
auth→identity) وأصبح `hooks/auth/useAuth.ts::useLogout` هو المصدر الوحيد
الصحيح لتسجيل الخروج (يستدعي `POST /identity/logout` فعليًا عبر الكوكي
HttpOnly)، تبيّن أن زرّي تسجيل الخروج الفعليين في الواجهة لم يُحدَّثا
للاستخدام الجديد:
- `components/layout/sidebar.tsx`: زر "إنهاء الجلسة" كان يستدعي
  `useAuthStore().logout()` — وهي فقط تمسح حالة Zustand محليًا، **لا تستدعي
  أي endpoint بالباك إند إطلاقًا**. النتيجة: الكوكيز HttpOnly تبقى موجودة
  والـ refresh token يبقى غير مُبطَل في القاعدة رغم أن الواجهة تُظهر
  المستخدم "خارج الجلسة".
- `components/layout/navbar.tsx`: عنصر القائمة "إنهاء الجلسة الآمنة" في
  الـ dropdown **لم يكن له `onClick` إطلاقًا** — زر ميت بالكامل، بلا أي
  تأثير عند الضغط عليه.

**الإصلاح:** ربط كلا الزرّين بـ `useLogout()` من `hooks/auth/useAuth.ts`
(`logoutMutation.mutate()`)، مع تعطيل الزر أثناء انتظار الاستجابة
(`disabled={logoutMutation.isPending}`).

**اكتشاف إضافي غير مرتبط، عولج بنفس الإصلاح:** `navbar.tsx` كان يستورد
`useNotificationStore` من مسار خاطئ (`@/store/notification-store`، بينما
الملف الفعلي `store/notificationStore.ts`) — خطأ `tsc` مانع للبناء بالكامل،
سابق لهذه المهمة وغير متعلق بـ auth/identity، اكتُشف أثناء التحقق من
النوع (`tsc --noEmit`) بعد إصلاح الـ logout. تم تصحيح مسار الاستيراد فقط.

**الاختبارات:** `tsc --noEmit` نظيف على كلا الملفين بعد الإصلاح (لا أخطاء
type). التحقق الوظيفي الفعلي (الضغط على الزرّين والتأكد من تسجيل الخروج
الحقيقي) تم يدويًا في المتصفح من قِبل المستخدم وأُكِّد ناجحًا.

**الملفات المتأثرة:** `eppne-web/components/layout/sidebar.tsx`,
`eppne-web/components/layout/navbar.tsx`.

---

## [2026-08-09] — Phase 2 (Frontend) من خطة دمج auth→identity: مكتملة
ومُتحقَّق من تناسقها بالكامل

**الحالة:** ✅ مكتمل ومُتحقَّق منه (فحص تناسق شامل لكل ملف + `tsc --noEmit`
نظيف على كامل المشروع + تأكيد وظيفي يدوي في المتصفح للزرّين — انظر الإدخال
السابق)

**ما تم:** إعادة بناء الفرونت إند بالكامل ليصبح cookie-only، وحذف الكود
الميت المكرر (`components/identity/*`):
- `store/auth-store.ts`: أُعيد تصميمه — حذف `accessToken`/`refreshToken`
  كتخزين دائم؛ الحقل الوحيد المتبقي (`accessToken`) يبقى في الذاكرة فقط
  ولا يُستخدم كـ Authorization header لأي طلب REST، بل حصريًا لاستثناء
  مصافحة WebSocket في `hooks/communications/useWebSocket.ts`.
- `hooks/auth/useAuth.ts`: أُعيد كتابته بالكامل — `useLogin`, `useRegister`,
  `useLogout`, `useRevokeAllSessions`, `useActiveSessions`,
  `useChangePassword` (جديد)، `useMe` (استعلام حقيقي `GET /identity/me`
  بدل قراءة store محلي)، `useCurrentUser`، وتصدير مركّب `useAuth()` ليحل
  محل كل الاستيرادات المكسورة القديمة.
- `services/auth.service.ts`: كل الدوال تستهدف مسارات `/identity/*`
  الصحيحة (بما فيها `GET /identity/sessions` الحقيقي من Phase 1).
- `lib/api-client.ts`: cookie-based بالكامل، حذف إلحاق `Authorization:
  Bearer` من الـ Zustand store، تدفق تجديد 401 يعتمد على الكوكي فقط.
- `providers/AuthProvider.tsx`: يعتمد الآن على `useMe()` الحقيقي بدل الوثوق
  بـ `localStorage` — هذا الإصلاح الفعلي للثغرة الأمنية المُسجَّلة في
  الإدخال الثاني أعلاه (2026-08-08).
- **حذف:** `components/identity/*` بالكامل (7 ملفات كانت معطَّلة أصلًا)،
  `services/identity.service.ts` (مسارات مضاعفة خاطئة `/identity/identity/*`)،
  `hooks/use-auth.ts` (تطبيق رابع معطوب لـ`useAuth`).
- **جديد:** `components/auth/ChangePasswordForm.tsx`,
  `hooks/auth/useUserProfile.ts`، `components/auth/ProfileForm.tsx` (منقول
  من identity وأُصلِح — انظر ملاحظة `birth_date` أعلاه)،
  `components/finance/WalletCard.tsx` (منقول من identity، مُعطَّل عمدًا
  بوضوح لحين ربطه بدومين finance الحقيقي — خارج نطاق auth/identity).
- إصلاح استيرادات مكسورة في 8 ملفات كانت تستورد `useAuth`/`useAuth`-shaped
  hooks من مسارات خاطئة أو غير موجودة (`health/emergency`, `finance/admin`,
  `digital-twin`, `ai/approvals`, `dashboard/page.tsx`, `web3-provider.tsx`,
  `useWebSocket.ts`, `profile/page.tsx`).

**التحقق (بناءً على طلب صريح قبل الـcommit):** قراءة كاملة لكل ملف في
السلسلة (store → hooks → services → provider → api-client → الصفحات
المستهلِكة)، `grep` شامل للتأكد من صفر استيرادات معلّقة لأي من الملفات
المحذوفة، وتشغيل `tsc --noEmit` على كامل المشروع — صفر أخطاء type في كل
سطح auth/identity.

**3 ملاحظات هامشية مكتشفة أثناء التحقق (موثَّقة بوضوح، لا تمنع الإنجاز):**
1. تكرار بسيط غير ضار: كل من `api-client.ts` (عند فشل تجديد الجلسة)
   و`error-handler.ts` يُعيدان التوجيه لـ`/login` بشكل مستقل عن بعضهما —
   ازدواجية كود غير ضارة وظيفيًا، تستحق تبسيطًا لاحقًا.
2. `src/lib/api-types.ts` (مولَّد آليًا من OpenAPI) قديم — أُنشئ قبل
   تعديلات Phase 1 بالباك إند، فلا يعرف `GET /identity/sessions` كمسار
   مستقل (لا يزال يحمل فقط عملية `/api/auth/sessions` القديمة). لا يكسر
   شيئًا حاليًا لأن الكود يستخدم generics صريحة على `apiClient.get<T>()`
   وليس بحثًا بالمسار، لكن يستحق إعادة توليد لاحقًا لدقة التوثيق.
3. **`hooks/communications/useWebSocket.ts`** يستدعي `setWsConnected`
   و`incrementUnread` من `useNotificationStore()`، لكن هذا الـstore لا
   يعرّف أيًا منهما إطلاقًا (يعرّف `addNotification` بدلاً منهما، بشكل
   مختلف) — **bug سابق تمامًا لهذه المهمة** (موجود من قبل أي لمسة لـ
   Phase 2، مؤكَّد من ملاحظات التحليل الأصلية)، وخارج نطاق auth/identity
   (دومين `communications`). لم يُلمَس منه عمدًا سوى تصحيح مسار استيراد
   `useAuth` فيه (ضمن نطاق Phase 2 المتفق عليه). إشعارات WebSocket غير
   فعّالة حاليًا نتيجة لهذا الـbug، لكنه **ليس ناتجًا عن هذه المهمة** —
   موثَّق هنا كمرشَّح لمهمة منفصلة لاحقة في دومين communications.

**الملفات المتأثرة:** `eppne-web/store/auth-store.ts`,
`eppne-web/hooks/auth/useAuth.ts`, `eppne-web/services/auth.service.ts`,
`eppne-web/lib/api-client.ts`, `eppne-web/lib/error-handler.ts`,
`eppne-web/providers/AuthProvider.tsx`,
`eppne-web/components/auth/LoginForm.tsx`,
`eppne-web/components/auth/ChangePasswordForm.tsx`,
`eppne-web/components/auth/ProfileForm.tsx`,
`eppne-web/hooks/auth/useUserProfile.ts`,
`eppne-web/components/finance/WalletCard.tsx`,
`eppne-web/app/(dashboard)/profile/page.tsx`,
`eppne-web/app/(dashboard)/dashboard/page.tsx`, `eppne-web/app/web3-provider.tsx`,
`eppne-web/hooks/communications/useWebSocket.ts` (سطر الاستيراد فقط)،
حذف `eppne-web/components/identity/*` (7 ملفات)،
`eppne-web/services/identity.service.ts`, `eppne-web/hooks/use-auth.ts`.

---
