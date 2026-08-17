# سجل التقدم (Progress Log)

سجل تراكمي لكل مهمة مكتملة في المشروع. كل مهمة جديدة تُضاف كسطر جديد في
الأسفل. لا يُحذف أو يُعدَّل أي إدخال قديم هنا أبداً.

---

## 🔴🔴 بانر أولوية نشط [2026-08-17] — اقرأ قبل أي عمل، خصوصًا قبل أي إصلاح لـ Backlog #9

**يوجد قرار أولوية صريح نشط حاليًا** بخصوص ثغرة حرجة (يوزر حقيقي بلا محفظة بيتسجَّل على القرص فعليًا عبر `invitations.accept_invitation`) — **محجوبة بالصدفة حاليًا ببج مستقل (Backlog #9)، مش بتصميم آمن**. **قبل أي إصلاح لـ`SaaSControlService.get_active_subscription` (Backlog #9)، لازم تقرأ القسم الكامل "🔴 قرار أولوية صريح [2026-08-17]" في آخر هذا الملف مباشرة**، وكذلك `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`. **`users id=52` مُستثنى من أي تنظيف throwaway عام لحد ما هذه الجلسة تُغلق رسميًا.**

**✅ تحديث [2026-08-18] — هذا البانر أصبح تاريخيًا، الثغرة مُغلَقة رسميًا.** راجع بند Backlog #11 المُحدَّث في آخر هذا الملف ("✅ إغلاق رسمي [2026-08-18]") و`.claude/reports/invitations-savepoint-leak-session-log.md` للتفاصيل الكاملة. **`users id=52`/دعوة `id=1` لسه مستثنيان من التنظيف الروتيني العادي (غير عاجل)، لكن القيد الصارم على Backlog #9 اتشال.**

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

## [2026-08-09] — إعادة فحص فعلي لزرّي logout (navbar.tsx وsidebar.tsx)
بعد شك في تعارض مع إدخال سابق — لم يُعثر على أي تعارض

**السياق:** قبل بدء Phase 3 (إعادة تسمية `components/auth`/`hooks/auth`
إلى `identity`)، أُثير شك بأن زر "إنهاء الجلسة الآمنة" في dropdown الـ
navbar (الموثَّق إصلاحه في الإدخال الخاص بتاريخ [2026-08-09] أعلاه بعنوان
"إصلاح: زرّا تسجيل الخروج في السايدبار والـ navbar غير مربوطين بآلية
logout الصحيحة") قد يكون اختفى أو رجع بلا `onClick` في تعديل لاحق.

**الفحص الفعلي المباشر لملفي المصدر الحاليين (وليس اعتمادًا على التوثيق
القديم):**
- `eppne-web/components/layout/navbar.tsx` (السطر 91-99): عنصر
  `DropdownMenuItem` الخاص بـ"إنهاء الجلسة الآمنة" **موجود** وله
  `onClick={() => logoutMutation.mutate()}` و`disabled={logoutMutation.isPending}`،
  و`logoutMutation` مأخوذ من `useLogout()` المستورَدة من
  `@/hooks/auth/useAuth` (السطر 18، 26). مطابق تمامًا لما وثّقه الإدخال
  السابق.
- `eppne-web/components/layout/sidebar.tsx` (السطر 1277، 1431-1439): نفس
  النمط — `logoutMutation = useLogout()` من نفس المسار، وزر "إنهاء
  الجلسة" مربوط بـ `onClick={() => logoutMutation.mutate()}`.
- لا يوجد أكثر من ملف `navbar.tsx` واحد في المشروع (تم التأكد عبر بحث
  شامل بالاسم)، فلا مجال لالتباس "ملف تاني بنفس الاسم".

**الخلاصة:** لم يُعثر على أي discrepancy فعلي بين التوثيق والكود الحالي
وقت هذا الفحص. الإصلاح الموثَّق سابقًا لا يزال قائمًا سليمًا في كلا
الملفين. سبب الشك الذي أثير غير مؤكَّد (احتمال: نظرة على نسخة مبنية/
مخبَّأة قديمة في المتصفح، أو فرع/checkout مختلف، أو التباس في القراءة) —
لم يتم تحديد السبب الجذري لأن الكود الحالي على القرص مطابق للمتوقع، ولا
داعٍ لأي إصلاح إضافي بناءً على هذا الفحص وحده.

**الحالة:** ✅ فحص تم، بدون أي تعديل على الكود (توثيق فقط).

**الملفات المفحوصة (بدون تعديل):** `eppne-web/components/layout/navbar.tsx`,
`eppne-web/components/layout/sidebar.tsx`.

---

## [2026-08-09] — Phase 3 (Frontend) من خطة دمج auth→identity: الكود
مكتمل ومتحقَّق منه، لكن اكتُشف بلوكر منفصل تمامًا يمنع الاختبار اليدوي
في المتصفح

**الحالة:** 🔄 **Phase 3 نفسها مكتملة ومتحقَّق منها بالكود** (رينيم +
imports، صفر لمس منطق، مُثبَت بمقارنة `tsc` قبل/بعد). **لكن** الشرط
الإجباري لاختبار زرار logout يدويًا في متصفح حقيقي (المطلوب تحديدًا
لملفي `sidebar.tsx` و`navbar.tsx`) **لسه معلَّق** بسبب باغ منفصل تمامًا
اكتُشف أثناء محاولة التنفيذ — موثَّق بالتفصيل تحت. **لم يُلمس الباغ ده
ولا أي حل مؤقت له — بانتظار موافقة صريحة منفصلة.**

### ما تم تنفيذه فعليًا (Phase 3، خطة `.claude/plans/phase3-rename-auth-to-identity.md`)

- `git mv` لـ8 ملفات: `components/auth/*` (6 ملفات) → `components/identity/*`،
  `hooks/auth/*` (ملفين) → `hooks/identity/*`.
- تحديث تعليق المسار الذاتي في رأس 7 من الـ8 ملفات.
- تحديث 22 سطر `import` في 15 ملف خارجي مستهلِك (القائمة الكاملة موثَّقة
  في ملف الخطة).
- صفر تغيير في أي اسم export/hook (`useAuth`, `useLogin`, `useLogout`...
  إلخ)، وصفر لمس لـ`app/(auth)/` (route group) أو أي URL فعلي.

### التحقق المُنفَّذ فعليًا (بديل مؤقت لاختبار المتصفح، ليس بديلًا كاملًا عنه)

- `grep` شامل نهائي: **صفر بقايا** لـ`@/components/auth` أو `@/hooks/auth`
  (alias أو relative) في كامل المشروع، وصفر تعليقات مسار ذاتي قديمة.
- `npx tsc --noEmit -p tsconfig.json` على كامل المشروع: **`EXIT_CODE=2`،
  1253 خطأ** — **لكن** بالمقارنة الدقيقة (عبر `git worktree add` منفصل
  عند commit `5b1d241`، أي *قبل* أي لمسة من Phase 3، مع تشغيل نفس أمر
  `tsc` بالظبط): الـbaseline (قبل) طلّع **1253 خطأ** أيضًا، وبعد تطبيع
  فرق المسار (`auth`→`identity` على الملفات المنقولة) كانت نتيجة الـ`diff`
  بين قائمتي الأخطاء **فرق واحد فقط، وهو شكلي بحت** (مسار مطلق لمجلد
  الـworktree المؤقت نفسه في رسالة خطأ واحدة، مش خطأ إضافي حقيقي). يعني
  Phase 3 **لم يُدخل ولا خطأ واحد جديد، ولم يُصلح أي خطأ قديم** — الـ1253
  خطأ كلهم ديون تقنية سابقة في دومينات تانية تمامًا (academy, insurance,
  logistics, tenders-auctions, translation, digital-twin store...)
  مالهاش أي علاقة بـauth/identity، بدليل إنهم في ملفات لم تُلمس إطلاقًا
  في هذه المهمة. تم تنظيف الـworktree المؤقت والـjunction الخاص به بالكامل
  بعد المقارنة (`git worktree remove` + `git worktree prune`)، والتأكد إن
  `node_modules` الحقيقي في `eppne-web/` سليم 100% (نفس عدد الحزم قبل وبعد).

### البلوكر المكتشف: التطبيق كله (كل صفحة) يرجع 500 في بيئة التطوير — غير مرتبط بـPhase 3 إطلاقًا

**الاكتشاف:** عند محاولة تشغيل السيرفر لاختبار زرار logout يدويًا، لُقي
سيرفر `next dev` شغّال بالفعل مسبقًا على المشروع (من قبل هذه الجلسة)،
وطلب أي صفحة منه (`/login` وأي صفحة تانية عمليًا) بيرجّع **500 Internal
Server Error**. اللوج (`.next/dev/logs/next-development.log`) بيوضّح
السبب بدقة:

```
The export unsafeCSS was not found in module node_modules/lit/index.js
Import trace: app/web3-provider.tsx → app/providers.tsx → app/layout.tsx
```

**السلسلة الكاملة:** `lit@3.3.0` (النسخة المثبَّتة، تأكَّد إنها نسخة
وحيدة في `node_modules` بدون أي تعارض نسخ متداخلة) لم يعد يُصدِّر
`unsafeCSS` من نقطة الدخول الرئيسية بالشكل اللي `@reown/appkit-ui`
بيتوقعه ← `@reown/appkit` ← `@walletconnect/ethereum-provider` ←
`wagmi`/`@rainbow-me/rainbowkit` ← **`app/web3-provider.tsx`** ←
`app/providers.tsx` ← **`app/layout.tsx` (الـroot layout)**. بما إن
الـroot layout بيتحمّل لأي صفحة في التطبيق، **الأثر مش محصور في
auth/identity أو صفحات `/login`/`/dashboard` بس — كل صفحة في المنصة
كلها واقعة بـ500 في بيئة التطوير الحالية.**

**تأكيد صريح: الباغ ده مش ناتج عن Phase 3 ولا عن أي مهمة سابقة في خطة
دمج auth/identity:**
- `git log --follow` على `app/web3-provider.tsx`: آخر لمسة ليه كانت في
  Phase 2 (commit `5b1d241`) لتصحيح سطر استيراد `useAuth` فقط (موثَّق
  مسبقًا في إدخال Phase 2 أعلاه) — **صفر لمس لمنطق أو تبعيات Web3**.
  أول ظهور للملف كان في **"Initial commit" بتاريخ 2026-07-01** (commit
  `1d37167`)، ومنطق الـWeb3 provider نفسه لم يتغيّر منذ ذلك التاريخ.
- `app/providers.tsx`: آخر لمسة حقيقية للمنطق كانت في commit `83eaabb`
  (إضافة قطاعات رئيسية، قبل أي عمل على auth/identity)، ثم لمسة سطر
  استيراد فقط في Phase 2.
- `package.json` (تبعيات `lit`/`@reown/*`/`wagmi`/`@rainbow-me/rainbowkit`):
  لم تُلمس منذ "Initial commit" — أي إن التعارض بين النسخ كان موجودًا
  من أول يوم في المشروع، **قبل بدء خطة دمج auth/identity بالكامل**.
- Phase 3 نفسها لا تلمس `web3-provider.tsx` ولا `providers.tsx` ولا
  `layout.tsx` إطلاقًا (مش من ضمن الـ23 ملف المتأثرة).

**لم يُتخذ أي إجراء إصلاحي لهذا الباغ** (لا downgrade، لا patch، لا
تعطيل مؤقت) — خارج نطاق Phase 3 تمامًا، ومحتاج موافقة صريحة على مهمة
منفصلة بالكامل قبل أي لمسة له.

### الأثر على معيار نجاح Phase 3

- ✅ الرينيم نفسه: مكتمل، نظيف، مُثبَت بمقارنة `tsc` قبل/بعد (فرق = صفر
  خطأ فعلي).
- ⏸️ **الشرط الإجباري (غير القابل للتفاوض) لاختبار logout يدويًا في متصفح
  حقيقي لـ`sidebar.tsx`/`navbar.tsx`: لم يُنفَّذ بعد** — مش لأن فيه مشكلة
  في الرينيم، لكن لأن التطبيق كله (كل صفحاته) واقع حاليًا في بيئة التطوير
  بسبب الباغ المذكور فوق، فمفيش أي صفحة ممكن تتفتح لاختبارها أصلًا.
- **القرار المتخذ:** التوقف الكامل عن أي تقدم إضافي في Phase 3 أو أي
  Phase جديدة لحد ما يترجع للمستخدم ويتاخد قرار صريح بخصوص باغ الـWeb3
  ده (يشمل بدائل زي: توثيقه فقط والرجوع له لاحقًا كمهمة منفصلة، أو عمل
  patch/downgrade مؤقت لـ`lit` كمهمة مستقلة بموافقة صريحة).

**الملفات المتأثرة (Phase 3 فعليًا):** `eppne-web/components/identity/*`
(منقولة من `components/auth/*`)، `eppne-web/hooks/identity/*` (منقولة من
`hooks/auth/*`)، و15 ملف مستهلِك (`providers/AuthProvider.tsx`,
`hooks/communications/useWebSocket.ts`, `components/layout/sidebar.tsx`,
`components/layout/navbar.tsx`, `app/(dashboard)/health/emergency/page.tsx`,
`app/(dashboard)/finance/admin/page.tsx`,
`app/(dashboard)/settings/sessions/page.tsx`,
`app/(dashboard)/ai-agents/page.tsx`, `app/(dashboard)/ai/approvals/page.tsx`,
`app/(dashboard)/digital-twin/page.tsx`, `app/(dashboard)/dashboard/page.tsx`,
`app/(dashboard)/profile/page.tsx`, `app/(dashboard)/privacy/settings/page.tsx`,
`app/(auth)/register/page.tsx`, `app/(auth)/login/page.tsx`).

**الملفات المفحوصة فقط لتشخيص البلوكر (بدون أي تعديل):**
`eppne-web/app/web3-provider.tsx`, `eppne-web/app/providers.tsx`,
`eppne-web/app/layout.tsx`, `eppne-web/package.json`,
`eppne-web/node_modules/lit/*`.

---

## [2026-08-10] — ملاحظة صغيرة: انحراف طبيعي في baseline أخطاء tsc

أثناء التحقق من خطوة 1 في Phase 4 (`eppne-web/services/auth.service.ts`)،
`npx tsc --noEmit` طلّع **1268** خطأ، مقابل الـbaseline الموثَّق سابقًا
(**1253**) في إدخال Phase 3 أعلاه. المقارنة (تشغيل نفس الأمر مع وبدون
تعديلنا، عبر `git stash`) أثبتت إن الرقمين **متطابقان 1268=1268 في
الحالتين** — يعني تعديلنا صفر تأثير على العدد الإجمالي. **مصدر الـ15
خطأ الإضافية لم يُفحص بالتفصيل** (لا grep ولا diff على محتوى الأخطاء
نفسها) — خارج نطاق Phase 4، ومش لازم حل عاجل لأنها مش ناتجة عن أي
تعديل بتاعنا.

---

## [2026-08-10] — Phase 4: حذف دومين auth بالكامل من الباك إند

**الحالة:** ✅ مكتمل (الحذف + التحقق)، مع بند واحد مؤجَّل صراحة (تفصيل تحت)

**السياق:** آخر مرحلة في خطة دمج auth→identity (`.claude/plans/
phase4-remove-auth-backend.md`). نُفِّذت **رغم** إن باغ الـWeb3 الموثَّق
في إدخال Phase 3 أعلاه لسه غير محلول واختبار logout اليدوي لسه معلّق —
قرار صريح من المستخدم بتاريخ اليوم بالمُضي قُدمًا لأن Phase 4
backend-only ومالهاش تداخل تقني مع الباغ ده (frontend rendering issue).

**المنفَّذ بالترتيب:**
1. **Frontend (ملف واحد، `eppne-web/services/auth.service.ts`):**
   استبدال `type RevokeAllSessionsResponse = components['schemas'][...]`
   (كان معتمدًا على schema مولَّدة من `auth/schemas.py` القديم) بـ
   `interface` محلي مطابق لشكل رد `/identity/revoke-all` الفعلي. صفر لمس
   لأي ملف باك إند في الخطوة دي (قرار متعمَّد لتقليل عدد الملفات المتأثرة).
2. **Backend:** حذف `app/domains/auth/` بالكامل (7 ملفات، 732 سطر) —
   `__init__.py`, `models.py`, `schemas.py`, `repository.py`, `service.py`,
   `router.py`, `jwt_service.py`. يشمل إغلاق نهائي لخطر `tenant_id=1`
   المُثبَّت الموثَّق في `PROJECT_AUDIT.md` §5.2 (كان dead code من ناحية
   الاستدعاء الخارجي، لكن حذفه بيقفل احتمال استيراد خاطئ مستقبلي نهائيًا).
3. **Backend (`app/main.py`):** إزالة سطر استيراد `auth_router`/
   `auth_protected_router` (كان سطر 39) وكتلة تسجيلهم (كانت سطور 311-315).
   `identity_router`/`identity_protected_router` لم تُلمس إطلاقًا.
   **توضيح دقيق:** ده إزالة تكرار endpoint (نفس الوظيفة كانت مسجَّلة
   مرتين بمسارين)، **مش** إغلاق فجوة أمنية جديدة — فجوة `api.deps`
   الأضعف في auth_router (`PROJECT_AUDIT.md` §5.1) كانت اتصلحت أصلًا في
   P0 قبل كده، وفجوة "بدون `require_sector`" الهيكلية **لسه موجودة**
   في `identity_router`/`identity_protected_router` بدون تغيير (خارج
   نطاق Phase 4، محتاجة قرار/مهمة منفصلة).
4. **Tests:** `tests/test_auth_router_protection.py` (من P0، كان بيختبر
   `/api/auth/*` مباشرة عبر `find_route`) اتحذف لأنه بيستهدف مسارات
   محذوفة، واتعوَّض بـ`tests/test_identity_router_protection.py` —
   نفس منطق التحقق بالظبط (endpoints عامة بدون `get_current_active_user`،
   endpoints محمية بتعتمد على النسخة القوية من `core.security` مش
   `api.deps` الأضعف) لكن على `/api/identity/*`، بنفس التغطية
   (register/login/logout/refresh عامة؛ me/sessions/revoke-all/password
   محمية). صفر فقدان تغطية اختبارات أمنية نتيجة الحذف.

**التحقق:**
- `pytest tests/` كامل: **5 نجحوا، 0 فشل** (شامل الاختبارين الجديدين).
  تحذير `DeprecationWarning` واحد غير مرتبط (`regex` قديم في
  `employment/router.py`، دومين تاني تمامًا).
- فحص OpenAPI schema مباشرة (`fastapi_app.openapi()`، بدون سيرفر حي):
  **`AUTH_PATHS_COUNT=0`**، **`IDENTITY_PATHS_COUNT=8`** (login, logout,
  me, me/password, refresh, register, revoke-all, sessions) — مطابق
  تمامًا للمتوقع.
- `tsc --noEmit` الكامل (شُغِّل قبل حذف الباك إند، أثناء التحقق من خطوة
  1 فقط): 1268 خطأ، مطابق تمامًا لنفس العدد مع وبدون تعديل
  `auth.service.ts` (اتأكد بـ`git stash`) — صفر تأثير من شغلنا. ملاحظة
  الانحراف عن baseline الـ1253 الموثَّق في Phase 3 مسجَّلة في الإدخال
  اللي قبل ده مباشرة.

**مؤجَّل صراحة (خارج نطاق Phase 4، مش blocking):** إعادة توليد
`eppne-web/src/lib/api-types.ts` عبر `openapi-typescript` — الأداة مش
مثبَّتة حاليًا في `package.json`، و`eppne-backend/openapi.json` (السنابشوت
الثابت) تاريخه 8 يوليو 2026 (قبل حتى Phase 0). الهدف الفعلي من الخطوة دي
(`tsc --noEmit` exit نظيف) **محقَّق بالفعل بدون الحاجة للـregeneration**
(راجع نقطة التحقق فوق) — البقايا الوحيدة (مسارات `/auth/auth/*` شكلية،
ونوع `RevokeAllSessionsResponse` غير مُستخدَم) كود ميت غير مُستورَد من
أي حاجة، صفر تأثير وظيفي. تحديث `openapi-typescript`/`api-types.ts`
يستاهل مهمة منفصلة لاحقًا بموافقة صريحة.

**الملفات المتأثرة:** `eppne-web/services/auth.service.ts` (تعديل)،
`eppne-backend/app/domains/auth/*` (حذف، 7 ملفات)، `eppne-backend/app/main.py`
(تعديل)، `eppne-backend/tests/test_auth_router_protection.py` (حذف)،
`eppne-backend/tests/test_identity_router_protection.py` (إنشاء).

**الحالة الإجمالية لخطة الدمج:** Phase 0-2 و4 مكتملة ومُتحقَّق منها.
Phase 3 (رينيم الفرونت إند) — الكود مكتمل، لكن اختبار logout اليدوي في
متصفح حقيقي **لسه معلّق** بسبب باغ الـWeb3 المذكور أعلاه، غير مرتبط
بـPhase 4.

---

## [2026-08-10] — Phase 5 (Frontend، فحص read-only): لا يوجد تكرار
components/auth مقابل components/identity فعليًا — اتحل من Phase 3.
اكتشاف موثَّق منفصل: `api-types.ts` قديم من قبل بداية خطة الدمج بالكامل

**الحالة:** ✅ Phase 5 مقفولة — الفرضية اللي اتبنت عليها الخطة
(`.claude/plans/phase5-frontend-auth-identity-dedup.md`) مش صحيحة في
الكود الحالي. صفر تعديل أو حذف تم أثناء هذا الفحص (read-only بالكامل،
حسب طلب المستخدم صراحة).

### الفحص (خطوة 1 من الخطة): هل تكرار components/auth/identity لسه موجود؟

خطة Phase 5 افترضت وجود 4 مكونات مكررة بنفس الاسم في `components/auth/`
و`components/identity/` معًا (LoginForm, RegisterForm, SessionCard,
SessionsList)، زائد `AuthProvider.tsx`/`WalletCard.tsx` في identity،
وملف `services/identity.service.ts` مضاعف. الفحص الفعلي بالـ`grep`/`Glob`
أثبت إن الفرضية دي **قديمة ومتجاوزة بالفعل**:

- `components/auth/` **غير موجود إطلاقًا** — صفر نتائج. الموجود فعليًا هو
  `components/identity/` بس (6 ملفات)، وهو ما تم توثيقه فعليًا كمكتمل في
  Phase 3 أعلاه (`git mv` من auth إلى identity، commit `4c7695b`).
- كل الصفحات الحية (`app/(auth)/login`, `app/(auth)/register`,
  `app/(dashboard)/profile`, `app/(dashboard)/privacy/settings`) بتستورد
  من `@/components/identity/*` حصريًا — صفر استيراد من `components/auth`
  في المشروع كله.
- `AuthProvider.tsx` **مش** في `components/identity` (كانت افتراض الخطة
  غلط) — موجود فعليًا في `providers/AuthProvider.tsx` (مجلد منفصل)،
  زي ما موثَّق في Phase 2 أعلاه.
- `WalletCard.tsx` **مش** جزء من دومين auth/identity أصلًا — موجود في
  `components/finance/WalletCard.tsx` (منقول ليها عمدًا في Phase 2، خارج
  نطاق auth/identity تمامًا).
- `services/identity.service.ts` **غير موجود** — اتحذف فعليًا في Phase 2
  (موثَّق أعلاه). الموجود بس `services/auth.service.ts`، وهو ده اللي
  بيستورده `hooks/identity/useAuth.ts` و`hooks/identity/useUserProfile.ts`
  حاليًا — mismatch تسمية (اسم الملف لسه "auth" بينما مجلد الاستهلاك
  "identity") مش تكرار كود فعلي. **لم يُلمس — الـrename ده خارج نطاق
  Phase 5 صراحة بطلب المستخدم.**

**القرار:** التكرار المذكور في الخطة **كان موجود فعلًا وقت كتابتها لكن
اتحل بالكامل ضمن Phase 3** (رينيم `components/auth`→`identity`). لا يوجد
كود ميت أو نسخة مزدوجة تحتاج حسم دلوقتي. خطوات 2-3 من الخطة (تحديد
النسخة الحية وحذف المكرر) **غير مطلوبة** — لا يوجد تكرار يُحذف.

### اكتشاف جانبي موثَّق (خطوة 4 من الخطة، مش تصحيح فعلي — بحث فقط):
مصدر مسارات `/identity/identity/*`

خطوة 4 من خطة Phase 5 طلبت "تأكيد/تصحيح" مسارات `/identity/identity/*`
المضاعفة. الفحص أثبت إنها **مش باج في تسجيل الراوتر بالباك إند**:

- `eppne-backend/app/domains/identity/router.py:18-19`: الراوتر معرَّف
  بـ`prefix="/identity"` **مرة واحدة بس**.
- `eppne-backend/app/main.py:310-314`: `identity_router`/
  `identity_protected_router` بيتضافوا بـ`include_router(..., prefix="/api")`
  بشكل منفصل عن لستة `routers_config` العامة (سطر 267-300) — الناتج
  الفعلي `/api/identity/register` إلخ، **بدون أي تكرار**. (ملاحظة هامشية:
  متغير `prefix_path` جوه اللوب العام سطر 302-308 غير مُستخدَم فعليًا في
  `include_router`، لكن ده مايسببش تكرار مسارات لإن كل راوتر عنده prefix
  داخلي واحد بس زائد `/api` من بره — يستاهل تنظيف كود لاحق، مش باج وظيفي).

**المصدر الحقيقي: `eppne-web/src/lib/api-types.ts` نفسه ملف قديم (stale)،
مش انعكاس لأي schema حالية:**

1. آخر تعديل على الملف: commit `0d9c55b`، بتاريخ **2026-07-21** — قبل
   Phase 0 من خطة الدمج بالكامل (اللي بدأت 2026-08-08)، وقبل الاكتشاف
   المؤجَّل المُسجَّل بالفعل في إدخالي Phase 2 وPhase 4 أعلاه (اللي أشارا
   لقِدَم الملف من غير تأكيد تاريخ الـcommit بالظبط).
2. الملف لسه فيه مسارات `/auth/auth/login`, `/auth/auth/refresh`,
   `/auth/auth/logout`, `/auth/auth/revoke-all`, `/auth/auth/sessions`
   (سطور 1413-1512) رغم إن دومين auth بالكامل **اتحذف من الباك إند في
   Phase 4** (commit `eeaf783`، نفس يوم هذا الفحص) — دليل قاطع إن الملف
   بيعكس API قديم/محذوف مش الحالي.
3. نمط `/{domain}/{domain}/...` المكرر **موجود في كل دومين في الملف من
   غير استثناء** (`academy/academy`, `affiliate/affiliate`, `health/health`,
   `iot/iot`, `finance/finance`... إلخ) — مش خاص بـidentity وبس، يعني مش
   نتيجة تعديل حديث في identity تحديدًا، لكن سمة عامة لطريقة/وقت توليد
   الملف بالكامل.
4. مفيش سكريبت `openapi-typescript` أو أمر توليد مسجَّل في
   `eppne-web/package.json` — مفيش آلية تلقائية لإعادة توليد الملف حاليًا.

**لم يتم أي تصحيح أو تعديل على `api-types.ts` أو أي ملف باك إند —
فحص وبحث فقط، حسب طلب المستخدم صراحة.** الإصلاح الصحيح مش تعديل السطور
المكررة يدويًا، لكن إعادة توليد الملف بالكامل من الـOpenAPI schema
الحالية (بعد تركيب/تفعيل `openapi-typescript` كخطوة أولى) — **مهمة منفصلة
لاحقة، تحتاج موافقة صريحة، خارج نطاق Phase 5**.

**الملفات المفحوصة فقط (بدون أي تعديل):**
`eppne-web/components/identity/*`, `eppne-web/providers/AuthProvider.tsx`,
`eppne-web/components/finance/WalletCard.tsx`, `eppne-web/services/auth.service.ts`,
`eppne-web/hooks/identity/useAuth.ts`, `eppne-web/hooks/identity/useUserProfile.ts`,
`eppne-web/src/lib/api-types.ts`, `eppne-backend/app/domains/identity/router.py`,
`eppne-backend/app/main.py`, `eppne-web/package.json`.

---

## [2026-08-10] — Phase 6 (فحص read-only): PUT /api/ai/routing كان
مُصلَّح بالفعل ضمن P0 — صفر تعديل كود جديد، الاختبار الموجود مسبقًا اتشغّل
ونجح

**الحالة:** ✅ Phase 6 مقفولة بدون أي تعديل كود. خطة
`.claude/plans/phase6-ai-routing-authz-fix.md` افترضت إن `PUT /api/ai/routing`
لسه محمي بـ`get_current_user` فقط (بلا فحص دور) — الفحص الفعلي أثبت إن
ده مش صحيح في الكود الحالي.

### الفحص (خطوات 1-2 من الخطة)
الـendpoint موجود في `eppne-backend/app/main.py:387-391` (مش في
`ai_governance/router.py` زي ما افترضت الخطة)، ومُعتمِد بالفعل على
`Depends(get_current_superuser)` (مستورد من `app.core.security`، سطر 27).
النسخة الضعيفة القديمة (`Depends(get_current_user)`) موجودة فقط في
`app/main.py.bak` — ملف نسخة احتياطية غير مُحمَّل في التطبيق، مش كود حي.
هذا الإصلاح موثَّق فعليًا من قبل، بتاريخ **2026-08-08**، ضمن إدخال
`P0: إصلاح الثغرات الأمنية الحرجة` أعلاه (قسم 5.3 من PROJECT_AUDIT.md)
— أي **قبل بدء Phase 6 بيومين**، ضمن commit `c8c6ad7`.
نمط `Depends(get_current_superuser)` نفسه مستخدَم بشكل قياسي وواسع في
عشرات endpoints تانية عبر المشروع (مثال حي: `app/domains/admin/router.py`
`POST /admin/system/toggle-ai-agents`)، فالإصلاح الأصلي (لو كان لسه
مطلوبًا) كان هيتبع نفس النمط المعمول به فعلاً.

### التحقق الفعلي (خطوات 4-5 من الخطة): تشغيل الاختبار الموجود مسبقًا
`tests/test_ai_routing_security.py` كان موجودًا بالفعل من قبل (يتحقق إن
الـroute بيعتمد على `get_current_superuser` مباشرة وليس `get_current_user`).
تم تشغيله فعليًا: `pytest tests/test_ai_routing_security.py -v` →
**1 passed in 74.18s**. لم يُكتب أي اختبار جديد ولم يُعدَّل الموجود —
كان كافيًا ومطابقًا للمطلوب.

### اكتشاف جانبي غير مرتبط (خارج نطاق Phase 6، توثيق فقط)
أثناء تشغيل pytest، ظهر `DeprecationWarning` من
`app/domains/employment/router.py:377` (استخدام `regex` القديم بدل
`pattern` في Pydantic v2). غير مرتبط بـPUT /api/ai/routing ولا بـ
auth/identity — يستحق تعديل منفصل لاحقًا بموافقة صريحة، لم يُلمس هنا.

### ملاحظة موثّقة غير معالجة: SKILL.md لسه بيذكر الثغرة كأنها قايمة
`.claude/skills/eppne-project/SKILL.md` (قسم "نقاط ضعف معروفة في
المشروع"، سطر 95-96) لسه بيذكر: *"`PUT \api\ai\routing`: محمي بـ
`get_current_user` بس بلا فحص دور"* — وهذا **غير مطابق للواقع** الحالي
(الإصلاح تم من 2026-08-08). يحتاج تحديث لاحق ليعكس إن الثغرة دي
اتصلحت ضمن P0. **لم يُلمس SKILL.md في هذه الجلسة** بطلب صريح من
المستخدم.

**الملفات المفحوصة فقط (بدون أي تعديل):**
`eppne-backend/app/main.py`, `eppne-backend/app/main.py.bak`,
`eppne-backend/tests/test_ai_routing_security.py`,
`eppne-backend/app/domains/admin/router.py`,
`eppne-backend/app/core/security.py`, `eppne-backend/app/api/deps.py`,
`eppne-web/src/lib/api-types.ts`, `.claude/skills/eppne-project/SKILL.md`.

---

## [2026-08-10] — Phase 9b: إصلاح تسريب بيانات حساسة في POST
/api/identity/login (response body)

**الحالة:** ✅ مُصلَح ومُتحقَّق منه فعليًا (curl حقيقي + pytest). خطة
`.claude/plans/phase9b-fix-login-response-leak.md`.

### المشكلة (مؤكدة سابقًا في Phase 9 audit)
`POST /api/identity/login` (`eppne-backend/app/domains/identity/router.py`)
كانت بترجّع الـ User ORM object الخام تقريبًا جوّه مفتاح `"user"` في
الـresponse، بما فيه `hashed_password` (bcrypt hash كامل)، `wallet`،
`tenant` الكامل، `last_login_ip`، `last_login_user_agent`،
`idempotency_key`، `session_version`، `admin_id`، `domain`. السبب:
الـendpoint (سطر 40) مكانش عليه `response_model`، فـ`jsonable_encoder`
سلسل كل attributes الـSQLAlchemy object تلقائيًا. بالمقارنة، `register`
(سطر 28) كان بالفعل صحيح — `response_model=UserResponse` صريح.

### الفحص (خطوات 1-2 من الخطة)
- `login` بترجّع dict مركّب (`access_token`, `token_type`, `message`,
  `user_id`, `user`) مش `user` object لوحده — فحط `response_model=UserResponse`
  على الـdecorator زي `register` كان هيكسر الـendpoint فورًا (validation
  error، لأن حقول الـdict العليا مش متطابقة مع schema `UserResponse`).
  هذا تعارض بين نص الخطة الأصلي والتنفيذ الآمن، اتحل بموافقة صريحة من
  المستخدم في الجلسة.
- `UserResponse` (`eppne-backend/app/domains/identity/schemas.py:35-50`)
  مناسبة كما هي بدون أي تعديل — `model_config = ConfigDict(from_attributes=True)`
  بيتعامل بأمان مع أي حقل مش موجود كattribute (مثل `balances`) برجوعه
  للـdefault.

### الإصلاح الفعلي (سطر واحد)
`eppne-backend/app/domains/identity/router.py:54` —
`"user": user` → `"user": UserResponse.model_validate(user)`. لم يُلمس
الـdecorator (سطر 40) ولا أي endpoint تاني، ولم تُعدَّل `schemas.py`.

### التحقق الفعلي (خطوة 4 من الخطة): register + login حقيقيين
شُغِّل السيرفر محليًا (`uvicorn`، postgres/redis عبر docker containers
موجودة مسبقًا). `POST /api/identity/register` بمستخدم تجريبي
(`login_leak_test_user`) → `201`، response نظيف كالمعتاد. `POST
/api/identity/login` بنفس البيانات → `200`، الـresponse body الكامل
اتفحص يدويًا وتأكد إن **كل** الحقول الحساسة المذكورة أعلاه غير موجودة
إطلاقًا — فقط حقول `UserResponse` القياسية (id, username, email,
tenant_id, sovereign_rank, system_role, kyc_status, balances, ...).
الكوكيز (`access_token`/`refresh_token` كـHttpOnly) شغالة بلا تغيير.
بعد التحقق: المستخدم التجريبي اتحذف من قاعدة البيانات مباشرة (`DELETE
FROM users WHERE username = 'login_leak_test_user'`)، والسيرفر
التجريبي اتوقف بالكامل (تأكيد بـcurl: not reachable).

### تشغيل pytest (خطوة 5 من الخطة)
ملف الـpytest الوحيد اللي بيغطي identity/login هو
`tests/test_identity_router_protection.py` (بيفحص الـdependencies/الصلاحيات
على الـroutes، مش شكل الـresponse body). شُغِّل فعليًا:
`pytest tests/test_identity_router_protection.py -v` → **2 passed in
51.55s**، صفر فشل. التحذير الوحيد الظاهر (`regex` deprecated في
`employment/router.py:377`) غير مرتبط بالإصلاح ده إطلاقًا.

### ⚠️ فجوة تغطية اختبارات موثّقة (لم تُعالَج في هذه الجلسة — خارج النطاق المطلوب)
**لا يوجد حاليًا automated regression test يغطي شكل response body لـ
`/identity/login`.** الاختبار الموجود (`test_identity_router_protection.py`)
يتحقق فقط من صلاحيات الوصول (dependencies)، مش من محتوى الـresponse.
هذا يعني إن رجوع نفس مشكلة التسريب مستقبلاً (مثلاً لو حد رجّع
`"user": user` الخام تاني بالغلط، أو أضاف حقل حساس جديد للـmodel)
**مش هيتلقط تلقائيًا بأي CI/test موجود حاليًا** — الاكتشاف كان يدوي
بالكامل (curl فعلي). **يُنصح بشدة** بإضافة اختبار صريح لاحقًا (خارج
نطاق هذه الجلسة، يحتاج مهمة/موافقة منفصلة) يتحقق إن `hashed_password`
وباقي الحقول الحساسة (`wallet`, `tenant`, `last_login_ip`,
`last_login_user_agent`, `idempotency_key`, `session_version`,
`admin_id`, `domain`) **لا تظهر أبدًا** في أي `/identity/login` response،
لمنع رجوع نفس المشكلة دون أن يلاحظها أحد.

**الملفات المُعدَّلة:** `eppne-backend/app/domains/identity/router.py`
(سطر 54 فقط).
**الملفات المفحوصة فقط (بدون تعديل):**
`eppne-backend/app/domains/identity/schemas.py`,
`eppne-backend/tests/test_identity_router_protection.py`.

---

## [2026-08-10] — Phase 9 (مخرج 1 من 3): تقرير أمني كامل لدومين identity
— تحقق عملي حي على الثغرتين، وربط بـPhase 9b (كانت جارية بالتوازي)

**الحالة:** ✅ مخرج 1 (التقرير الأمني) مكتمل ومُتحقَّق منه بالتنفيذ
الفعلي. مخرجا 2 (الجرد الوظيفي) و3 (تناغم Backend/Frontend) **لم يبدآ
بعد** — المستخدم طلب صراحة عرض مخرج 1 والموافقة عليه أولاً.

**الملف الكامل بكل الأدلة الخام (request/response):**
`.claude/plans/phase9-audit-identity-report.md`.

**منهجية:** بدل الاكتفاء بقراءة الكود، تم تشغيل سيرفر `uvicorn` محلي
فعلي (3 مرات متتالية) متصل بـPostgres وRedis حقيقيين (docker: `eppne_db`
بورت 5435، `redis` بورت 6380)، وتنفيذ طلبات `curl` حقيقية ضد مستخدمين
وtenant تجريبيين throwaway، مع cleanup كامل بعد كل مرحلة (بموافقة صريحة
قبل كل حذف، ومُتحقَّق منه لاحقًا بـ`SELECT` مباشر على القاعدة، مش ملخص
نصي فقط).

### ثغرة 1 — تسريب hashed_password عبر POST /identity/login: نفس الاكتشاف، مصدرين مستقلين

هذه الجلسة اكتشفت نفس المشكلة الموثَّقة بالتفصيل في إدخال **Phase 9b**
أعلاه مباشرة، بشكل مستقل ومتوازٍ (جلسة/agent منفصل كان شغّال على خطة
`.claude/plans/phase9b-fix-login-response-leak.md` في نفس الوقت تقريبًا).
التحقق الحي الأول في هذه الجلسة (مستخدم تجريبي id=9، قبل ما يظهر إصلاح
Phase 9b على القرص) أثبت التسريب فعليًا (`hashed_password` + `wallet` +
`tenant` كاملين ظاهرين في response حقيقي). أثناء التحقيق، لوحظ تغيّر
غير متوقَّع في نتائج اختبار لاحق (response نظيف لمستخدم تجريبي تانٍ) —
افتُرض بدايةً سلوك ORM غير حتمي، واتضح لاحقًا (`git diff`) إن السبب
البسيط هو إن جلسة Phase 9b كانت عدّلت `router.py:54` (`"user": user` →
`"user": UserResponse.model_validate(user)`) بالتوازي، كـuncommitted
change وقتها. **بناءً على طلب صريح من المستخدم في هذه الجلسة، تم عمل
commit للتعديل:** `0a488ba` —
`fix(security): filter hashed_password from login response via
UserResponse.model_validate (Phase 9b)`. تم التحقق الحي بعد الإصلاح
(محاولتين منفصلتين): صفر حقول حساسة، شكل مطابق تمامًا لـ`UserResponse`.

### ثغرة 2 (🔴 لسه قائمة، لم تُصلَح، لا علاقة لها بـPhase 9b) — X-Tenant-ID كمصدر tenant_id بلا تحقق تفويض

`api/deps.py::get_current_tenant` بتاخد `tenant_id` من هيدر
`X-Tenant-ID` مباشرة (افتراضي `1`) بدون أي استعلام DB أو تحقق تفويض.
**تحقق حي:** تم إنشاء tenant ثانٍ حقيقي (id=2) عبر سكربت مستقل خارج
`app/`، وتسجيل مستخدم جديد تحته عبر `POST /identity/register` بهيدر
`X-Tenant-ID: 2` **نجح بدون أي دعوة أو تفويض**. **تحقق حي إضافي (نتيجة
سلبية موثَّقة):** محاولة استغلال نفس الهيدر لتسريب بيانات عبر
`GET /me`/`GET /sessions` (بجلسة مستخدم tenant 1، هيدر لـtenant 2
الحقيقي) **فشلت** (`404`/`[]`) — لأن هذي الـendpoints بتستخدم
`current_user.id` من الـJWT الموقَّع لتحديد الهوية، مش الهيدر. جرد كامل
(10/10 endpoints في identity) أثبت صفر endpoint بياخد `user_id`/
`tenant_id` كـpath/query parameter — النتيجة السلبية شاملة للدومين
كله. **الخطر المتبقي محصور في `register`/`login` (تسجيل تحت tenant غير
مصرَّح بيه)، ولم يُصلَح في هذه الجلسة.** نفس نمط `get_current_tenant`
مستخدَم في 30+ راوتر دومين آخر عبر المشروع — خارج نطاق identity، موثَّق
كملاحظة تصميمية أوسع فقط.

**ملاحظات إضافية موثَّقة في التقرير الكامل:** `WalletRepository.
update_balances`/`freeze` بلا فلترة tenant_id (غير مستدعاة من أي
endpoint في identity)؛ rate limiting غايب على `GET/PUT /me`؛
`identity/router.py.bak` كود ميت غير محمَّل؛ لا يوجد `max_length` على
الباسورد.

**Cleanup:** كل بيانات الاختبار (4 مستخدمين throwaway، tenant تجريبي
واحد) اتحذفت وتأكدت بـ`SELECT` مباشر على `users`/`academy_tenants` —
القاعدة نظيفة 100% من أي أثر لهذه الجلسة. السيرفر التجريبي متوقف
بالكامل.

**الملفات المتأثرة:** `eppne-backend/app/domains/identity/router.py`
(تعديل واحد فقط — نفس تعديل Phase 9b، تم اعتماده بـcommit `0a488ba` في
هذه الجلسة تحديدًا)، `.claude/plans/phase9-audit-identity-report.md`
(إنشاء). باقي ملفات identity/api/core **فُحصت فقط، بدون تعديل**.

**التالي:** مخرج 2 (الجرد الوظيفي لكل endpoint) ثم مخرج 3 (تناغم
Backend/Frontend) — بانتظار موافقة المستخدم على البدء.

---

## [2026-08-10] — Phase 9 (مخرجا 2 و3 من 3): الجرد الوظيفي + تناغم
Backend/Frontend لدومين identity — Phase 9 مكتملة بالكامل

**الحالة:** ✅ مكتمل، read-only بالكامل (صفر تعديل كود). الملف الكامل:
`.claude/plans/phase9-audit-identity-report.md`.

**مخرج 2 (الجرد الوظيفي):** جدول كامل لكل الـ10 endpoints (register,
login, logout, refresh, me GET/PUT, sessions GET, revoke-all, me/password
PUT, me DELETE) مبني على تتبّع فعلي لمسار الكود
`router.py → service.py → repository.py`. **صفر endpoint مكسور فعليًا.**
القصور الوحيد: `birth_date` غايب من `UserUpdate` (`PUT /me`) — موثَّق
سابقًا (`[2026-08-09]` أعلاه)، مش اكتشاف جديد. جزء من الأدلة اعتمد على
تحقق حي سابق (مخرج 1 وPhase 1 E2E)؛ `PUT /me/password` تحديدًا مؤكَّد من
الكود فقط (لم يُختبَر حيًا في هذا المخرج، ذُكر ذلك صراحة).

**مخرج 3 (تناغم Backend/Frontend):** فحص `services/auth.service.ts` (كل
مسارات `/identity/*` في المشروع تمر منه حصريًا) + كل الـhooks/components
المستهلِكة:
- **9 من 10 endpoints مُستهلَكة فعليًا** من الفرونت إند بمسارات مطابقة
  حرفيًا لما هو مسجَّل في الباك إند.
- 🟡 **endpoint يتيم واحد:** `DELETE /identity/me` (تعطيل الحساب) —
  الباك إند شغّال بالكامل، لكن **لا توجد أي واجهة أو حتى دالة service**
  تستدعيه في الفرونت إند. المستخدم حاليًا لا يملك أي طريقة لحذف/تعطيل
  حسابه من الواجهة. قرار المعالجة (إضافة UI أو تركه) يحتاج مهمة/موافقة
  منفصلة.
- **صفر استدعاء فرونت إند لـendpoint غير موجود أو معطوب.**
- **صفر type-mismatch فعلي** مكتشف بين `api-types.ts` القديم (موثَّق
  قِدَمه سابقًا في Phase 5) واستجابات الباك إند الحالية، رغم قِدَم الملف
  عمومًا — فُحص تحديدًا `UserUpdate`/`RevokeAllSessionsResponse` ووُجدا
  متطابقين حرفيًا بالمصادفة.
- **ملاحظة تنظيف كود غير عاجلة:** ميزة "الجلسات النشطة" مُنفَّذة 3 مرات
  مستقلة (`SessionsList.tsx` مُستهلَك من صفحتين + `settings/sessions/page.tsx`
  تطبيق منفصل بالكامل) — نفس الـendpoints، صفر تعارض بيانات، لكن يستحق
  توحيدًا لاحقًا.

**الملفات المفحوصة فقط (بدون أي تعديل):**
`eppne-backend/app/domains/identity/router.py`,
`eppne-backend/app/domains/identity/service.py`,
`eppne-backend/app/domains/identity/repository.py`,
`eppne-backend/app/domains/identity/schemas.py`,
`eppne-web/services/auth.service.ts`, `eppne-web/hooks/identity/useAuth.ts`,
`eppne-web/hooks/identity/useUserProfile.ts`,
`eppne-web/providers/AuthProvider.tsx`, `eppne-web/lib/api-client.ts`,
`eppne-web/types/auth.ts`, `eppne-web/src/lib/api-types.ts`,
`eppne-web/components/identity/*` (6 ملفات), `eppne-web/app/(auth)/login/page.tsx`,
`eppne-web/app/(auth)/register/page.tsx`, `eppne-web/app/(dashboard)/profile/page.tsx`,
`eppne-web/app/(dashboard)/privacy/settings/page.tsx`,
`eppne-web/app/(dashboard)/settings/sessions/page.tsx`.

**الحالة الإجمالية لـPhase 9:** ✅ **مكتملة بالكامل** — المخرجات الثلاثة
(1: تقرير أمني، 2: جرد وظيفي، 3: تناغم Backend/Frontend) منجزة وموثَّقة
في `.claude/plans/phase9-audit-identity-report.md`.

---

## [2026-08-10] — إقفال Phase 9: مراجعة أمنية + جرد وظيفي + تناغم
Backend/Frontend لدومين identity — ملخص ختامي شامل للمهام الثلاث

**الحالة:** ✅ **Phase 9 مقفولة بالكامل.** هذا إدخال ختامي واحد يجمّع
المهام الثلاث الموثَّقة بالتفصيل في الإدخالين أعلاه (`[2026-08-10] —
Phase 9 (مخرج 1 من 3)` و`[2026-08-10] — Phase 9 (مخرجا 2 و3 من 3)`) —
لا يُلغي أو يُعدِّل أيًا منهما، فقط يوفّر نظرة ختامية موحَّدة. التقرير
الكامل بكل الأدلة الخام: `.claude/plans/phase9-audit-identity-report.md`.

### المهمة 1 — التقرير الأمني (تحقق عملي حي، سيرفر uvicorn + Postgres/Redis حقيقيين)
- 🟢 **ثغرة تسريب `hashed_password` عبر `POST /identity/login`:** مؤكَّدة
  حيًا قبل الإصلاح (response خام كامل شامل `hashed_password`, `wallet`,
  `tenant`)، **أُصلحت فعليًا** (`router.py:54` → `UserResponse.model_validate(user)`)
  ومُثبَّتة في commit `0a488ba`، ومؤكَّد التنظيف الكامل حيًا بعد الإصلاح
  (مرتين منفصلتين). هذا الإصلاح اكتُشف بالتوازي من جلسة Phase 9b منفصلة
  وتم اعتماده رسميًا في هذه الجلسة.
- 🔴 **ثغرة `X-Tenant-ID` كمصدر tenant_id بلا تحقق تفويض (لسه قائمة، لم
  تُصلَح):** مؤكَّد حيًا أن `register`/`login` يسمحان بالتسجيل تحت أي
  tenant_id **موجود فعليًا** بلا أي دعوة/تفويض. مؤكَّد حيًا أيضًا (نتيجة
  سلبية) أن الـ6 endpoints المحمية (`me`, `sessions`, إلخ) **غير قابلة
  للاستغلال** عبر نفس الهيدر لتسريب بيانات مستخدمين آخرين، لأنها تعتمد
  حصريًا على `current_user.id` من الـJWT الموقَّع وليس الهيدر. الخطر
  المتبقي محصور في `register`/`login` فقط، ونمط `get_current_tenant`
  الأوسع مستخدَم في 30+ راوتر آخر عبر المشروع (خارج نطاق identity).
- ملاحظات إضافية موثَّقة: rate limiting غايب على `GET/PUT /me`، لا يوجد
  `max_length` على الباسورد، `WalletRepository.update_balances/freeze`
  بلا فلترة tenant_id (لكن غير مستدعاة من identity)، `identity/router.py.bak`
  كود ميت غير محمَّل.
- كل بيانات الاختبار (4 مستخدمين + tenant تجريبي) اتحذفت ومُتحقَّق منها
  بـ`SELECT` مباشر — صفر أثر متبقٍ في القاعدة.

### المهمة 2 — الجرد الوظيفي (10 endpoints، قراءة فعلية router→service→repository)
جدول كامل لكل الـ10 endpoints (register, login, logout, refresh,
me GET/PUT, sessions GET, revoke-all, me/password PUT, me DELETE).
**صفر endpoint مكسور فعليًا.** القصور الوحيد المكتشف: `birth_date` غايب
من `UserUpdate` (`PUT /me`) — قصور معروف وموثَّق مسبقًا (`[2026-08-09]`)،
والفرونت إند متوافق معه فعلاً (حقل معطَّل بوضوح، مش bug جديد).

### المهمة 3 — تناغم Backend/Frontend (فحص `auth.service.ts` + كل الاستهلاك)
- **9 من 10 endpoints مُستهلَكة فعليًا** بمسارات مطابقة حرفيًا لما هو
  مسجَّل بالباك إند.
- 🟡 **endpoint يتيم واحد:** `DELETE /identity/me` (تعطيل الحساب) —
  شغّال بالكامل بالباك إند، **بلا أي واجهة أو دالة service تستدعيه** في
  الفرونت إند. المستخدم حاليًا بلا أي طريقة لحذف/تعطيل حسابه من الواجهة.
- **صفر استدعاء فرونت إند لـendpoint غير موجود أو معطوب.**
- **صفر type-mismatch فعلي** بين `api-types.ts` القديم (قِدَمه موثَّق
  سابقًا في Phase 5) واستجابات الباك إند الحالية، رغم قِدَم الملف عمومًا.
- ملاحظة تنظيف كود غير عاجلة: ميزة "الجلسات النشطة" مُنفَّذة 3 مرات
  مستقلة في الواجهة (نفس الـendpoints، صفر تعارض بيانات).

### الحصيلة الإجمالية لدومين identity (بعد Phase 9)
| البند | العدد |
|---|---|
| Endpoints فحوصة | 10/10 |
| Endpoints مكسورة | 0 |
| ثغرات مؤكَّدة ومُصلَحة | 1 (`hashed_password` leak) |
| ثغرات مؤكَّدة لسه قائمة | 1 (`X-Tenant-ID` بلا تفويض على register/login) |
| Endpoints يتيمة (بلا استهلاك فرونت) | 1 (`DELETE /me`) |
| استدعاءات فرونت لمسار غير موجود/معطوب | 0 |

### القرارات المؤجَّلة صراحة (تحتاج موافقة/جلسة منفصلة — ليست جزءًا من Phase 9)
- إصلاح ثغرة `X-Tenant-ID` على `register`/`login` (وربما النمط الأوسع
  عبر 30+ راوتر آخر في المشروع).
- قرار منتج بخصوص `DELETE /identity/me` اليتيم (إضافة UI أو تركه).
- إضافة `birth_date` إلى `UserUpdate` scheme + تفعيل الحقل في `ProfileForm.tsx`.
- توحيد تكرار "الجلسات النشطة" (3 مسارات UI مستقلة).
- إضافة regression test لشكل response body لـ`/identity/login` (منع رجوع
  تسريب مشابه مستقبلاً).
- إعادة توليد `api-types.ts` من OpenAPI الحالية (تركيب `openapi-typescript`
  أولاً).
- تحديث `.claude/skills/eppne-project/SKILL.md` ليعكس إصلاح `PUT /api/ai/routing` (من Phase 6).

**لا تعديل كود جديد تم في أي من المهام الثلاث — Phase 9 بالكامل read-only،
باستثناء تعديل السطر الواحد (`router.py:54`) الموثَّق أعلاه في المهمة 1
(اعتماد إصلاح Phase 9b، مؤكَّد بـcommit `0a488ba`).**

**الجلسة مُقفَلة عند هذا الإدخال.** أي عمل على البنود المؤجَّلة أعلاه
(بما فيها أي "Phase 10") يبدأ في جلسة منفصلة جديدة بموافقة صريحة.

---

## [2026-08-11] — Phase 10: مراجعة أمنية + جرد وظيفي + تناغم
Backend/Frontend لدومين affiliate (المجموعة 1، ثاني دومين بعد identity)

**الحالة:** ✅ مكتملة بالكامل، read-only بالكامل (صفر تعديل كود). التقرير
الكامل بكل الأدلة: `.claude/plans/phase10-audit-affiliate-report.md`.

**المنهجية:** قراءة كاملة فعلية لكل ملفات الدومين + الملفات المرتبطة
فعليًا (`api/deps.py`, `core/rate_limiter.py`, `core/celery_config.py`,
`tasks/affiliate.py`, `main.py`) + كل ملفات الفرونت إند المستهلِكة.
**بلا أي تحقق ديناميكي حي في هذه الجلسة** — محاولة وحيدة لقراءة
`openapi()['paths']` عبر استيراد `app.main` (بدون سيرفر، بدون طلبات
شبكة) عُلِّقت بطلب المستخدم بعد أن تسببت في hang (اتصال DB/Redis عند
الاستيراد)، والاعتماد بالكامل على قراءة الكود الثابت بعدها. **قبل
البدء، أكَّد المستخدم صراحةً عدم وجود جلسة Claude Code تانية شغّالة على
نفس المشروع.**

**ملاحظة نطاق مهمة أثناء الجلسة:** أثناء تتبّع مسار توزيع العمولات
الحقيقي (لإثبات هل `AffiliateService.distribute_commissions` كود ميت
أو لأ)، تم فتح ملفات `domains/commerce/service.py` و`tasks/commerce.py`
**حصريًا كسياق تكامل** (تتبّع المستدعي الفعلي لمنطق مشابه). المستخدم
لاحظ ده وسأل هل ده تقييم فعلي لدومين commerce (scope creep) — تم
التوضيح إنه سياق تكامل بس، بلا أي جرد وظيفي أو مراجعة أمنية لـcommerce
نفسه. الاستثناء الوحيد: ملاحظة جانبية غير مؤكَّدة لوحظت بالصدفة عن
`commerce.service.ts` (نفس نمط double-prefix المكتشف في affiliate) —
بطلب المستخدم صراحة، اتفصلت في قسم مستقل بعنوان "ملاحظة هامشية غير
مرتبطة" داخل التقرير، بدل دمجها في سرد اكتشافات affiliate، مع توضيح
إنها تحتاج phase مستقل خاص بـcommerce للتحقق منها.

### المهمة 1 — التقرير الأمني (10 ثغرات/ملاحظات، من قراءة الكود فقط)

أخطر اكتشافين (خطورة حرجة، مؤكَّدان قطعيًا من semantics بايثون الثابتة،
بلا حاجة لتشغيل):
- 🔴 **`require_subscription("affiliate")` (`api/deps.py:202-210`)
  مكسور بالكامل** — بينادي `SaaSControlService(db)` بمعامل واحد بينما
  الـ`__init__` الحالي بياخد `tenant_id` إجباري كمان (`saas/service.py:34`)،
  وبعدين `check_and_enforce_access(current_user.tenant_id, service_code)`
  بمعاملين بينما التوقيع الحقيقي معامل واحد (`saas/service.py:229`).
  النتيجة: `TypeError` → 500 قياسي (لا يوجد exception handler عام) —
  **لأي طلب، من أي مستخدم، بغض النظر عن اشتراكه.** يُسقط 5 من 15
  endpoint في affiliate بالكامل: `POST/PATCH /links`, `GET /commissions`,
  `POST /commissions/release`, `POST /withdraw`. نفس الدالة مُستخدَمة
  أيضًا في `academy` و`commerce` (لم يُفحص أثرها هناك، خارج النطاق).
- 🔴 **`@rate_limit(...)` (`core/rate_limiter.py`) غير فعّال فعليًا على
  14 من 15 endpoint في affiliate** — الديكوريتور بيدوّر على كائن
  `Request` في الـkwargs/args، وده مش موجود إلا لو الـendpoint نفسه بيُعلن
  `request: Request` في توقيعه؛ فحص شامل للـ15 endpoint أثبت إن واحد بس
  (`GET /track/{code}`) بيُعلنها. الباقي كله (بما فيهم `/withdraw` و
  `/commissions/release` و`/admin/commissions/bulk-release` — أخطر
  العمليات المالية) بيرجع مباشرة لتنفيذ الدالة الأصلية بلا أي فحص Redis،
  بصمت تام بلا أي تسجيل. الحدود المُعلَنة في الكود (`max_requests=5,
  window_seconds=300`... إلخ) زخرفية بحتة.

باقي الاكتشافات (خطورة عالية/متوسطة): 🟠 `X-Tenant-ID` بلا تحقق تفويض
على الـ4 endpoints الإدارية (`get_current_superuser` بيفحص الدور بس،
بلا مقارنة مع الـtenant الحقيقي) — سوبريوزر من tenant A يقدر (من الكود)
يعدّل نسب عمولات أو يُفرج عمولات مالية تخص tenant B بمجرد تغيير هيدر
HTTP. 🟠 `withdraw_commissions` بيستخدم `sender_id=1` مُثبَّت حرفيًا
لكل الـtenants كمصدر تمويل السحب، بلا أي فحص tenant للمُرسِل (بعكس
المستلم اللي بيتفحص) — اقتران مالي غير مقصود بين tenants. 🟡
`get_or_create_profile` ممكن يرمي `IntegrityError` غير معالَج (500) لو
هيدر tenant مخالف لمستخدم عنده ملف بالفعل (قيد `unique=True` على
`user_id`). ملاحظات إيجابية: صفر خطر mass-assignment (schemas الـUpdate
ضيقة ومقصودة)، tenant_id فعليًا مفلتَر في كل استعلامات
`AffiliateRepository` (نفس معيار Phase 9).

### المهمة 2 — الجرد الوظيفي (15 endpoint، قراءة فعلية router→service→repository)

5 من 15 endpoint مكسورة فعليًا (500 دائمًا، بسبب `require_subscription`).
**اكتشاف جوهري منفصل تمامًا:** محرك توزيع العمولات في دومين affiliate
نفسه (`AffiliateService.distribute_commissions`/`_distribute_levels`،
اللي بيكتب في `affiliate_commissions`) **كود ميت بالكامل** — لا يُستدعى
من أي مسار حي (تتبّع شامل بـ`grep`: المستدعي الوحيد هو Celery task
معزول تمامًا وغير مُطلَق من أي حدث). الآلية الفعلية المُستخدَمة في
الإنتاج لتوزيع عمولات الطلبات مختلفة تمامًا ومنفصلة بالكامل، موجودة في
دومين `commerce` (`CommerceService.distribute_commissions`، بتُستدعى
synchronously وقت الـcheckout)، وبتكتب في جداول commerce الخاصة بيها
(`CommissionRecord`, `AffiliateConfig`) — **مش جداول affiliate على
الإطلاق**، وحتى صيغة "كود الإحالة" مختلفة بين الدومينين (رقم user_id
خام في commerce، مقابل نص ألفانيوميري مولَّد في affiliate). هذا الفحص
المحدود لـcommerce كان **سياق تكامل فقط** (تتبّع مستدعي فعلي)، مش
مراجعة لدومين commerce نفسه — انظر ملاحظة النطاق أعلاه. النتيجة:
`GET /commissions`, `GET /stats`, `GET /tree`, والـadmin endpoints
هترجع دايمًا فاضية/صفرية في أي بيئة إنتاج حقيقية، حتى لو كل الثغرات
الأمنية اتصلحت. بالإضافة: `app/tasks/affiliate.py` بالكامل (3 مهام
Celery) مكسورة بنيويًا (توقيعات لا تطابق `AffiliateService`/
`AffiliateRepository` الحاليين) وغير مُستدعاة من أي مكان، وحتى مهمة
التنظيف الدورية (`clean_expired_links_task`) غير مُسجَّلة في
`celery_config.py::beat_schedule` أصلاً.

### المهمة 3 — تناغم Backend/Frontend

**اكتشاف جوهري:** كل الدوال الثمانية في `services/affiliate.service.ts`
بتستهدف مسارات مزدوجة البادئة حرفيًا (`/affiliate/affiliate/profile`
إلخ) — لا تطابق المسار الحقيقي المسجَّل بالباك إند (`/api/affiliate/profile`،
بادئة واحدة، مؤكَّد من `router.py` + `main.py` معًا؛ حقل `prefix_path`
الإضافي في `routers_config` غير مُستخدَم فعليًا، نفس اكتشاف Phase 5
لـidentity، لكن هنا المسار المزدوج **حرفي داخل الـstring نفسه** مش مجرد
نوع بيانات قديم). `next.config.ts` فارغ تمامًا (بلا `rewrites()`) فلا
يوجد أي تصحيح مسار وسيط. **اكتشاف إضافي منفصل:**
`hooks/affiliate/useAffiliate.ts` بينادي دالتين غير موجودتين إطلاقًا في
`affiliate.service.ts` (`getDashboardStats`, `getTree` — الموجود
فعليًا `getStats`/`getReferralTree`)، وبتوقيع معاملات خاطئ لدالتين
تانيتين (`getLinks`, `getCommissions` — معاملات منفصلة مقابل كائن واحد
متوقَّع). الصفحة الوحيدة الفعلية للدومين
(`app/(dashboard)/affiliate/page.tsx`) بتستخدم مباشرة الـhooks المكسورة
دي. **كل الروابط الخمسة الظاهرة في هذه الصفحة** (`/affiliate/links`,
`/commissions`, `/tree`, `/guidelines`, `/links/create`) **بتشاور على
صفحات غير موجودة إطلاقًا** (Glob شامل: صفر ملفات صفحات تحت
`app/(dashboard)/affiliate/` غير `page.tsx` نفسها) — وبشكل مستقل،
السايدبار (`components/layout/sidebar.tsx`) بيربط لنفس المجموعة من
المسارات غير الموجودة، تأكيد مزدوج مستقل. 6 endpoints
(`PATCH /links/{id}`, `GET /track/{code}`, و4 admin) بلا أي محاولة
استهلاك فرونت إند إطلاقًا.

**ملاحظة هامشية غير مرتبطة (موثَّقة بقسم مستقل في التقرير، بطلب
المستخدم):** لوحظ بالصدفة أثناء الفحص إن `services/commerce.service.ts`
قد يحتوي نفس نمط الـdouble-prefix — **غير مؤكَّد، غير مُتحقَّق منه،
يحتاج phase مستقل خاص بـcommerce.**

### الحصيلة الإجمالية لدومين affiliate (بعد Phase 10)
| البند | العدد |
|---|---|
| Endpoints فُحصت | 15/15 |
| Endpoints مكسورة فعليًا (500 دائمًا) | 5 |
| Endpoints شغّالة تقنيًا لكن بلا بيانات حقيقية عمليًا | 5 إضافية |
| ثغرات/اكتشافات أمنية-وظيفية حرجة | 6 |
| ثغرات متوسطة | 1 |
| استدعاءات فرونت إند بمسار مزدوج غير موجود | 8/8 (100%) |
| Hooks بدوال غير معرَّفة | 2 |
| Hooks بتوقيع معاملات خاطئ | 2 |
| Endpoints بلا أي استهلاك فرونت إند | 6 |
| صفحات فرونت إند فعلية للدومين | 1 فقط (كل الروابط الفرعية يتيمة) |

### القرارات المؤجَّلة صراحة (تحتاج موافقة/جلسة منفصلة — ليست جزءًا من Phase 10)
- إصلاح `require_subscription` (يؤثر أيضًا على academy وcommerce).
- إصلاح/إعادة تصميم `rate_limiter.py` ليعمل فعليًا على كل الـendpoints.
- **قرار معماري حاسم بخصوص ازدواجية نظام العمولات (affiliate مقابل
  commerce)** — أهم قرار مطلوب من هذا التقرير بالكامل.
- حذف أو إصلاح `app/tasks/affiliate.py` (3 مهام ميتة مكسورة).
- إصلاح مسارات `affiliate.service.ts` (البادئة المزدوجة).
- مزامنة `hooks/affiliate/useAffiliate.ts` مع `affiliate.service.ts`.
- إنشاء الصفحات الناقصة أو إزالة الروابط اليتيمة.
- معالجة ثغرة `X-Tenant-ID` الإدارية و`sender_id=1` المُثبَّت.
- معالجة `IntegrityError` غير المعالَج في `get_or_create_profile`.
- تشغيل `tsc --noEmit` للتأكد من type errors الناتجة عن ثغرة hooks.
- فحص باقي الدومينات المستخدمة لـ`require_subscription` (academy, commerce).
- **مهمة/phase مستقل خاص بـcommerce** — يشمل التحقق من ملاحظة
  double-prefix الهامشية أعلاه، وأي مراجعة أمنية/وظيفية كاملة له (لم
  تبدأ إطلاقًا في Phase 10).

**لا تعديل كود تم في أي من المهام الثلاث — Phase 10 بالكامل read-only.**

**ملاحظة: هذا الإدخال تم تصحيحه/تجاوزه جزئيًا بإدخال تحقق حي لاحق في
نفس اليوم (انظر الإدخال التالي مباشرة) — لم يُعدَّل أي سطر هنا (سياسة
append-only)، لكن رقم "5 endpoints مكسورة" في الحصيلة أعلاه أصبح غير
دقيق بعد التحقق الحي (تبيَّن إن الـ15 كلهم مكسورين).**

---

## [2026-08-11] — Phase 10 (متابعة): تحقق حي فعلي على ثغرة X-Tenant-ID
الإدارية — اكتشاف باج جوهري أخطر (`SimpleTenant`) يعطّل الدومين بالكامل
(15/15 endpoint)، ويحجب ثغرة X-Tenant-ID مؤقتًا

**الحالة:** ✅ التحقق الحي مكتمل، بيانات الاختبار اتنظّفت وتأكَّد نظافة
القاعدة، السيرفر التجريبي متوقف. التقرير الكامل مُحدَّث بالكامل ليعكس
هذا الاكتشاف: `.claude/plans/phase10-audit-affiliate-report.md`.

**السياق:** بعد إقفال الإدخال السابق مباشرة، طلب المستخدم توضيحًا دقيقًا
لثغرة X-Tenant-ID الإدارية (أي endpoint بالتحديد، وهل التأكيد من قراءة
كود فقط أو محتاج تحقق حي زي identity Phase 9). بعد التوضيح، طلب المستخدم
صراحة تحقق حي فعلي (سيرفر + بيانات اختبار)، بموافقة صريحة قبل كل خطوة
تنفيذ (تشغيل سيرفر، إنشاء بيانات، حذف بيانات) — نفس منهجية Phase 9
بالضبط.

### الإعداد (بموافقة صريحة لكل خطوة)
- تأكيد إن containers Postgres (`eppne_db`, بورت 5435) وRedis (`redis`,
  بورت 6380) من Phase 9 لسه شغّالين (13 يوم uptime) — لم يُشغَّل شيء
  جديد.
- بيانات اختبار throwaway: Tenant B تجريبي (`id=5`)، مستخدم `SUPER_ADMIN`
  تجريبي (`id=15`، تحت tenant حقيقي `id=1`)، صف `CommissionTier` تجريبي
  (`id=1`، تحت tenant `id=5`، `level_1_pct=13.37` مميزة لسهولة الرصد).
- ملاحظة جانبية أثناء الإعداد: أول محاولة لإنشاء `CommissionTier`
  فشلت بـ`NoReferencedTableError` (جدول `products` غير مُسجَّل في
  الـmetadata) لأن سكربت الإعداد المعزول استورد `affiliate.models` بس،
  من غير `commerce.models` (اللي فيه تعريف `products`، المرجع الفعلي
  لـ`CommissionTier.target_product_id`). **هذا فشل سكربت تجريبي بسيط،
  مش خلل في سكيما التطبيق الحقيقي** (السيرفر الحقيقي بيستورد كل
  الدومينات مع بعض وقت الإقلاع عبر `main.py`، فمكانش هيحصل). تم التأكد
  إن الـtransaction الفاشلة اتلغت بالكامل تلقائيًا (rollback نظيف، صفر
  صفوف يتيمة) قبل إعادة المحاولة بإضافة `import app.domains.commerce.models`.
  **لكن الحادثة نفسها وثَّقت دليل إضافي على ترابط schema حقيقي (مش مجرد
  استدعاء دالة) بين affiliate وcommerce** (`CommissionTier.target_product_id`
  FK فعلي على جدول `products` المُعرَّف في commerce) — يقوّي ملاحظة
  ازدواجية/ترابط النظامين المُسجَّلة سابقًا، ويستاهل يتذكر وقت التخطيط
  لأي phase مستقل خاص بـcommerce لاحقًا.
- تشغيل `uvicorn` محلي حقيقي (`127.0.0.1:8000`) — لوج الإقلاع طلّع كمية
  ضخمة (750KB+) من traceback متكرر غير ضار متعلق بـ`merged_lifespan`
  (encoding warning مكرر، غير مرتبط بـaffiliate، لم يُحقَّق فيه أكتر —
  السيرفر أقلع بنجاح وقتها: "Application startup complete").

### الاختبار الأول: `PUT /api/affiliate/admin/tiers` بهيدر `X-Tenant-ID`
مخالف (سوبريوزر tenant=1، هيدر=5) — النتيجة **500**، مش 200 زي المتوقَّع
من فرضية X-Tenant-ID الأصلية. الـtraceback الحقيقي من لوج السيرفر كشف
السبب: `asyncpg.exceptions.DataError: 'SimpleTenant' object cannot be
interpreted as an integer`.

### الاكتشاف الجوهري: باج `SimpleTenant` (كائن بدل `int`)
`api/deps.py::get_current_tenant` بترجع **كائن** `SimpleTenant` (له
خاصية `.id`)، مش رقم مباشر — **تصحيح لوصف خاطئ مني في التقرير الأصلي**
("بيرجع الرقم من الهيدر كما هو"). كل الـ15 endpoint في
`affiliate/router.py` (فحص شامل، 15/15) بيعلنوا
`tenant_id: int = Depends(get_current_tenant)` — type hint تزييني،
FastAPI ما بيفرضش التطابق، فالكائن الخام (مش الرقم) بيتمرر لـ
`AffiliateService(db, tenant_id)` وبعدها لكل استعلامات DB. **نفس الباج
بالظبط اتصلح فعليًا في identity Phase 0** (موثَّق `[2026-08-08]` أعلاه:
"تم تصحيحها لاستخدام `tenant: SimpleTenant = Depends(...)` ثم
`tenant.id`") — لكن الإصلاح **مبيتعملش في affiliate إطلاقًا**.

**تحقق حي ثانٍ (عزل السبب):** نفس الطلب (`GET /affiliate/profile`،
endpoint بسيط بلا `require_subscription`) بهيدر **صحيح 100%**
(`X-Tenant-ID: 1`، مطابق تمامًا لتينانت المستخدم الحقيقي) — **نفس
النتيجة بالظبط: 500.** يثبت قطعيًا إن الباج **مالوش علاقة بتطابق
الهيدر** — كل طلب لكل endpoint بيفشل، بغض النظر عن صحة الهيدر.

**تحقق DB (read-only):** `level_1_pct` لصف Tenant B فضل `13.37` (لم
يتغيّر) — الطلب انهار عند أول `SELECT`، قبل أي `UPDATE`، صفر تأثير
جزئي.

### فحص إضافي مطلوب صراحة: هل فيه bypass صامت (مقارنة `==` مباشرة بدل
`.id`) بديل عن الـcrash؟
فحص شامل بـ`grep` لكل الـ39 موضع (15 في `router.py` + 24 مقارنة
`== tenant_id` في `service.py`/`repository.py`) — **النتيجة: صفر
bypass صامت.** كل موضع إما تمرير مباشر لـconstructor (`router.py`)
أو مقارنة عمود SQLAlchemy (`Model.tenant_id == tenant_id`) اللي
بترجع تعبير SQL مش `True`/`False` Python — الفشل دايمًا صريح ولاحق
(وقت تنفيذ الاستعلام)، مش صامت ومبكر.

### العلاقة مع ثغرة X-Tenant-ID الإدارية — توضيح صريح للـblocker
ثغرة X-Tenant-ID (غياب مقارنة `current_user.tenant_id` بـ`tenant_id`
الهيدر على 4 endpoints إدارية) **لسه موجودة فعليًا كعيب كود مؤكَّد**،
لكنها **غير قابلة للفحص أو الاستغلال الحي حاليًا** — كل طلب بيتعطل
بباج `SimpleTenant` قبل ما يوصل لنقطة القرار دي. **مش باج middleware**
(فُحصت كل الـ6 middleware في `main.py`، ولا واحد له علاقة بـtenant_id) —
الإصلاح على مستوى توقيع كل endpoint في `router.py`. **تحذير موثَّق
صراحة:** إصلاح باج `SimpleTenant` لوحده من غير إضافة فحص مطابقة
tenant هيفتح ثغرة X-Tenant-ID فورًا للاستغلال.

### التنظيف (بموافقة صريحة، بعد `SELECT` قبل وبعد الحذف)
حذف الثلاثة كيانات بترتيب يحترم الـFK (`affiliate_commission_tiers`
id=1 → `users` id=15 → `academy_tenants` id=5). حذف المستخدم رجّع
cascade تلقائي صحيح لـ3 صفوف `auth_refresh_tokens` (`ondelete="CASCADE"`
في الموديل، متوقَّع وموثَّق). تحقق `SELECT` مباشر بعد الحذف: الثلاثة
اختفوا تمامًا، و`academy_tenants` (`id=1`، الحقيقي) و`users` (`ids
2-8`، القدامى من اختبارات سابقة) سليمين 100% بلا أي تغيير. إيقاف
السيرفر التجريبي: `Stop-Process` على الـPID الصحيح المؤكَّد نجح
(“DONE”)، لكن التحقق النهائي من إغلاق البورت واجه مشاكل shell
integration متكررة (timeouts على أوامر PowerShell بسيطة، حتى
`Get-Process`/`tasklist` — نفس المشكلة الموثَّقة في
`phase8-master-roadmap.md` لجلسات Phase 6/7) — **بطلب صريح من
المستخدم، تم الاكتفاء بدليل نجاح `Stop-Process` + تأكيد الـPID الصحيح
قبل القتل، والتوقف عن محاولات تحقق إضافية.** لو احتاج تأكيد نهائي إن
البورت مغلق، أسهل في بداية جلسة جديدة.

### تحديث تقرير Phase 10 الكامل
`.claude/plans/phase10-audit-affiliate-report.md` اتحدَّث بالكامل:
بند حرج جديد ("البند 0") مضاف بكل الأدلة الخام، الجرد الوظيفي مُعاد
كتابته (15/15 مكسورة بدل 5/15)، جدول الملخص التنفيذي والحصيلة الإجمالية
مُحدَّثين، قائمة الإصلاحات المؤجَّلة مُعاد ترتيبها بالأولوية (إصلاح
باج `SimpleTenant` بقى البند رقم 1 المطلق).

**الملفات المفحوصة فقط (بدون تعديل):** كل ملفات affiliate + `api/deps.py`
(تأكيد إضافي لـ`get_current_tenant`/`SimpleTenant`) + middleware
`main.py`. **بيانات مؤقتة أُنشئت ثم حُذفت بالكامل** (موثَّق أعلاه) —
صفر أثر متبقٍ في القاعدة من هذه الجلسة.

**الجلسة مُقفَلة عند هذا الإدخال.** أي عمل على البنود المؤجَّلة (وعلى
رأسها إصلاح باج `SimpleTenant`) يبدأ في جلسة منفصلة جديدة بموافقة
صريحة.

---

## [2026-08-11] — Phase 10b: إصلاح باج `SimpleTenant` في affiliate + اكتشاف حرج
جديد مؤكَّد بالتنفيذ الفعلي: ثغرة `X-Tenant-ID` (ثغرة 3) قابلة للاستغلال
الحي فعليًا (قراءة + **كتابة**) بمجرد إزالة الـblocker — بانتظار خطة
إصلاح منفصلة (Phase 10c)، **لا commit نهائي تم بعد**

**الحالة:** 🟡 **إصلاح الكود (SimpleTenant) تم في working tree، لسه ملوش
commit بطلب صريح من المستخدم لحد ما تُتفق خطة Phase 10c.** التحقق الحي
كشف ثغرة حرجة إضافية مؤكَّدة بالكتابة الفعلية في DB — موثَّقة بالتفصيل
تحت. بيانات الاختبار اتنضّفت بالكامل (تأكَّد بـSELECT مباشر). السيرفر
التجريبي لسه شغّال وقت كتابة هذا السطر (بانتظار توجيه المستخدم).

### السياق
بعد موافقة صريحة من المستخدم على نطاق محدَّد (إصلاح باج `SimpleTenant`
فقط، بنفس نمط identity Phase 0، بدون إضافة فحص tenant-match)، تم:
1. قراءة `identity/router.py` للتأكد من النمط المُعتمَد فعليًا
   (`tenant: SimpleTenant = Depends(get_current_tenant)` ثم `tenant.id`
   — 9 مواضع، مؤكَّد بـ`grep`).
2. تطبيق نفس النمط حرفيًا على كل الـ15 endpoint في
   `app/domains/affiliate/router.py` (تعديل الاستيراد سطر 8 لإضافة
   `SimpleTenant`، واستبدال ميكانيكي عبر `replace_all` لأن كل الـ15
   موضع كانت متطابقة نصيًا 100% — تأكَّد بـ`grep` قبل التعديل). تحقق
   `ast.parse` بعد التعديل: صفر أخطاء syntax.

### التحقق الحي 1: `GET /affiliate/profile` — الباج اختفى فعليًا
بيانات اختبار throwaway: مستخدم `phase10b_verify_user` (id=16) اتسجَّل
عبر `POST /identity/register` الحقيقي (tenant=1 الحقيقي)، تم تسجيل
دخوله (`POST /identity/login` → 200، كوكي جلسة صالحة). أول محاولة
`GET /affiliate/profile` رجعت **403** (`"User sector not defined"`) —
مش 500 — بسبب `require_sector("affiliate")` في `main.py` (طبقة منفصلة
تمامًا عن باج SimpleTenant، مستخدم عادي بيُصنَّف افتراضيًا `sector=academy`).
بعد ترقية المستخدم لـ`SUPER_ADMIN` مباشرة في DB (عشان `sector="all"`
يتجاوز الفحص)، نفس الطلب رجّع:
```
HTTP/1.1 200 OK
{"referral_code":"EPPNE-16","custom_slug":null,"default_commission_rate":"5.00","id":1,"user_id":16,"tenant_id":1,"is_active":true,"total_clicks":0,"total_conversions":0,"total_earned":0.0,"total_paid":0.0,...}
```
**200 حقيقي، بيانات حقيقية من DB حقيقي — تأكيد قاطع إن باج SimpleTenant
(البند 0 في Phase 10) اختفى فعليًا لهذا الـendpoint.**

### التحقق الحي 2 (الاكتشاف الحرج): `X-Tenant-ID` على `/admin/tiers` —
قراءة **وكتابة** فعلية عبر tenant غير مصرَّح به

بعد نجاح التحقق 1، تم إنشاء Tenant B تجريبي منفصل (`academy_tenants`
id=6، اسم "Phase10b Verify Tenant B") + صف `CommissionTier` تجريبي
تحته (`id=2`, `tenant_id=6`, `level_1_pct=13.37` — قيمة مميزة لسهولة
الرصد). المستخدم `phase10b_verify_user` (`SUPER_ADMIN`، **tenant
الحقيقي = 1**، مؤكَّد من الـJWT claim `tenant_id:1` وقت اللوجن) استُخدم
لإرسال طلبين حقيقيين بهيدر `X-Tenant-ID: 6` (مخالف عمدًا لتينانته
الحقيقي):

**الطلب 1 (قراءة):**
```
GET /api/affiliate/admin/tiers HTTP/1.1
X-Tenant-ID: 6
Cookie: access_token=<جلسة صحيحة، tenant الحقيقي=1>
```
```
HTTP/1.1 200 OK
{"tenant_id":6,"entity_type":"GLOBAL","target_product_id":null,"level_1_pct":"13.37",...,"id":2,...}
```
رجّع بيانات tenant 6 الحقيقية (القيمة المميزة `13.37`) لمستخدم tenant
الحقيقي بتاعه 1.

**الطلب 2 (كتابة):**
```
PUT /api/affiliate/admin/tiers HTTP/1.1
X-Tenant-ID: 6
Cookie: <نفس الجلسة>
Body: {"level_1_pct": 99.99}
```
```
HTTP/1.1 200 OK
{"tenant_id":6,...,"level_1_pct":"99.99",...,"id":2,"updated_at":"2026-08-11T00:20:55.930332Z"}
```

**تحقق DB مباشر (read-only) فور الطلبين:**
```sql
SELECT id, tenant_id, level_1_pct, updated_at FROM affiliate_commission_tiers WHERE tenant_id=6;
-- id=2, tenant_id=6, level_1_pct=99.99, updated_at=2026-08-11 00:20:55.930332+00
```
**الكتابة حقيقية وpersisted فعليًا في القاعدة، مش مجرد response مُرجَع.**
هذا يرقّي ثغرة 3 (الموثَّقة في Phase 10 كـ"مؤكَّدة من الكود، غير قابلة
للاستغلال الحي حاليًا بسبب بند 0") إلى **مؤكَّدة بالتنفيذ الفعلي** —
قراءة وكتابة كاملتين، بتأثير مالي مباشر (نسب عمولة).

### التشخيص المبدئي: فين بالضبط في الكود المصدر الجذري للثقة العمياء
بهيدر `X-Tenant-ID`؟

**المصدر الجذري:** `app/api/deps.py:148-153`:
```python
async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```
الدالة دي بتاخد الـtenant **حصريًا** من الهيدر الخام، بصفر أي رجوع
لهوية المستخدم المُصادَق عليه أو التوكن. دي dependency chain **منفصلة
تمامًا** عن `get_current_user`/`get_current_active_user`.

**بالمقابل، `get_current_user` (`api/deps.py:21-55`) بيستخرج
`tenant_id` الحقيقي والموثوق من التوكن الموقَّع نفسه** (سطر 41:
`token_tenant_id = payload.get("tenant_id")`، سطر 50:
`user = await repo.get_by_id(int(user_id), token_tenant_id)`) — يعني
`current_user.tenant_id` قيمة **موثوقة 100%** (جايه من JWT موقَّع
وقت اللوجن، مش من أي هيدر قابل للتزوير).

**نقطة الفشل الفعلية:** الـ4 admin endpoints في `affiliate/router.py`
(`GET/PUT /admin/tiers`, `POST /admin/tiers/product`,
`POST /admin/commissions/bulk-release`) بتحقن **الاتنين** كـdependencies
منفصلين بلا أي ربط بينهم:
```python
tenant: SimpleTenant = Depends(get_current_tenant),      # من الهيدر (غير موثوق)
current_user: User = Depends(get_current_superuser),      # من التوكن (موثوق)، بيفحص الدور بس
```
`get_current_superuser` (`api/deps.py:67-80`) بيفحص `system_role` فقط
(`EXECUTIVE_DIRECTOR`/`SUPER_ADMIN`) — **صفر مقارنة مع `tenant.id`**.
والكود الفعلي بيستخدم `tenant.id` (من الهيدر) مباشرة في
`AffiliateService(db, tenant.id)`، بصرف النظر تمامًا عن
`current_user.tenant_id` الحقيقي.

**الأخطر: الحل الجاهز موجود فعلاً في نفس الملف ومش مُستخدَم.**
`api/deps.py:156-164`:
```python
async def require_tenant_access(
    current_user: User = Depends(get_current_active_user),
    tenant: SimpleTenant = Depends(get_current_tenant),
) -> User:
    if current_user.tenant_id != tenant.id:
        raise PermissionDeniedError(
            f"عذراً، أنت لا تنتمي إلى المستأجر {tenant.id}. مستأجرك: {current_user.tenant_id}"
        )
    return current_user
```
دالة `require_tenant_access` بتعمل بالظبط الفحص الناقص (مقارنة
`current_user.tenant_id` بـ`tenant.id` من الهيدر) — **لكنها غير
مُستخدَمة في affiliate/router.py إطلاقًا** (تأكَّد بـ`grep`، صفر
استيراد لها في الملف). ده مش قرار معماري معقَّد — الأداة جاهزة، بس
مش موصولة بالـ4 endpoints الإدارية.

### التنظيف (تم بالكامل، تحقَّق بـSELECT مباشر)
حذف بترتيب يحترم الـFK: `affiliate_commission_tiers` (id=2, tenant=6)
→ `affiliate_profiles` (id=1, user=16) → `academy_tenants` (id=6) →
`users` (id=16). **تحقق نهائي بعد الحذف:**
```sql
SELECT 'tenant_6', count(*) FROM academy_tenants WHERE id=6;        -- 0
SELECT 'tier_tenant_6', count(*) FROM affiliate_commission_tiers WHERE tenant_id=6;  -- 0
```
**Tenant B وصف الـCommissionTier بتاعه اتحذفوا بالكامل من القاعدة —
مفيش أي "قيمة متبقية محتاجة ترجع لـ13.37"، لأن الصف نفسه (وtenant B
كله) اتمسحوا خلاص، مش بس القيمة اتغيَّرت.** `academy_tenants` الحقيقي
(`id=1`) وباقي الـ7 مستخدمين القدامى (ids 2-8) سليمين 100% بلا أي أثر.

### الحالة الحالية (صريحة)
- **تعديل الكود** (`affiliate/router.py`، إصلاح SimpleTenant، 15
  endpoint): **موجود في working tree، لسه من غير commit** — بطلب صريح
  من المستخدم، لحد ما تُتفق خطة Phase 10c لثغرة X-Tenant-ID.
- **لا انتقال لأي دومين جديد** حتى تُحسَم Phase 10c.
- **السيرفر التجريبي المحلي لسه شغّال** وقت كتابة هذا السطر (لم يُوقَف
  بعد، بانتظار توجيه المستخدم).
- القرار المطلوب لـPhase 10c: هل نربط `require_tenant_access` (الجاهزة
  فعلاً) بالـ4 admin endpoints، أم نمط تاني؟ — **قرار معلَّق، لا تنفيذ
  حتى الاتفاق.**

---

## [2026-08-11] — Phase 10c: إصلاح ثغرة X-Tenant-ID في affiliate/admin/*
(الاعتماد الكامل على `current_user.tenant_id`) + اكتشاف نظامي أوسع
بكثير (20 من 29 دومين بنفس الشكل) موثَّق منفصلًا (تقرير تشخيصي، بلا تنفيذ)

**الحالة:** 🟢 **إصلاح الـ4 admin endpoints في affiliate تم، اتحقَّق
منه حيًا (قراءة + كتابة)، بيانات الاختبار اتنضّفت، السيرفر التجريبي
اتوقف.** الاكتشاف الأوسع (20 دومين آخرين بنفس نمط الثقة بالهيدر) موثَّق
في تقرير منفصل تمامًا `.claude/plans/critical-finding-xtenant-systemic.md`
— **تشخيص فقط، صفر تنفيذ، قرار الإصلاح المركزي مؤجَّل لجلسة/جلسات
منفصلة كاملة.**

### القرار المعماري (بموافقة صريحة من المستخدم بعد نقاش)
فحصنا: هل فيه استخدام شرعي لهيدر `X-Tenant-ID` في تحديد الـtenant
لعمليات admin/affiliate؟ **النتيجة: لأ.** لا يوجد أي دليل في الـschema
(`users.tenant_id` عمود مفرد، مفيش جدول ربط multi-tenant-admin)، ولا
في الأدوار (`SystemRole`: 4 قيم كلها tenant-scoped)، ولا في أي دومين
تاني (`admin/router.py` — endpoint وحيد عالمي بلا مفهوم tenant). الاستخدام
الشرعي الوحيد للهيدر في المشروع كله محصور بالحالات اللي **مفيش فيها
current_user موثوق أصلًا وقت الطلب** (`identity/register`, `identity/login`,
`affiliate/track/{code}` العام). **القرار: الاعتماد الكامل على
`current_user.tenant_id` (من التوكن الموقَّع) بدل الهيدر في الـ4 admin
endpoints، وإلغاء الثقة في الهيدر نهائيًا لهذا المسار.**

### الإصلاح المُنفَّذ
`app/domains/affiliate/router.py` — الـ4 admin endpoints
(`GET/PUT /admin/tiers`, `POST /admin/tiers/product`,
`POST /admin/commissions/bulk-release`): إزالة
`tenant: SimpleTenant = Depends(get_current_tenant)` بالكامل من
توقيع كل واحدة، واستبدال `AffiliateService(db, tenant.id)` بـ
`AffiliateService(db, current_user.tenant_id)`. باقي الـ11 endpoint
(غير الإدارية) لم تُلمس — خارج نطاق Phase 10c (queries بتاعتها بتعمل
AND مع `current_user.id` الحقيقي أصلًا، شكل خطر مختلف تمامًا، انظر
النقاش قبل التنفيذ في المحادثة).

### التحقق الحي (سيرفر uvicorn محلي، أعيد تشغيله بعد التعديل لأنه
بلا `--reload`)
بيانات اختبار throwaway جديدة (منفصلة عن Phase 10b): مستخدم
`phase10c_verify_user` (id=17، تحت tenant حقيقي=1)، رُقّي لـ
`SUPER_ADMIN`، Tenant B تجريبي (`academy_tenants` id=7)، وصفين
`CommissionTier`: واحد تحت tenant=7 (`id=3`, `level_1_pct=42.42`،
قيمة مميزة لتينانت غريب)، وواحد تحت tenant الحقيقي=1 (`id=4`,
`level_1_pct=7.77`، عشان نتأكد إن الـendpoint لسه شغّال صح للمسار
الشرعي، مش بس بيرفض كل حاجة).

**اختبار 1 (قبل ما يتعمل تير لـtenant 1):**
```
GET /api/affiliate/admin/tiers HTTP/1.1
X-Tenant-ID: 7        ⬅️ مزوَّر عمدًا، تينانت الحقيقي=1
Cookie: <جلسة صحيحة>
```
```
HTTP/1.1 404 Not Found
{"detail":"إعدادات العمولات غير موجودة"}
```
مش 200 ببيانات tenant 7 (زي قبل الإصلاح) — رجّع 404 لأن tenant 1
(الحقيقي) مكانش عنده تير وقتها. **الهيدر بقى بلا أي تأثير.**

**اختبار 2 (بعد إنشاء تير لـtenant 1، نفس الهيدر المزوَّر لسه):**
```
GET /api/affiliate/admin/tiers HTTP/1.1
X-Tenant-ID: 7        ⬅️ لسه مزوَّر
```
```
HTTP/1.1 200 OK
{"tenant_id":1,...,"level_1_pct":"7.77",...}
```
رجّع بيانات **tenant 1** (الحقيقي، `7.77`) — **مش** بيانات tenant 7
(`42.42`) رغم إن الهيدر بيقول 7. تأكيد قاطع إن الهيدر بقى بلا تأثير
نهائيًا، والـscoping بقى فعليًا من `current_user.tenant_id`.

**اختبار 3 (كتابة، PUT بنفس الهيدر المزوَّر):**
```
PUT /api/affiliate/admin/tiers HTTP/1.1
X-Tenant-ID: 7
Body: {"level_1_pct": 8.88}
```
```
HTTP/1.1 200 OK
{"tenant_id":1,...,"level_1_pct":"8.88",...}
```
**تحقق DB مباشر فور الطلب:**
```sql
SELECT id, tenant_id, level_1_pct FROM affiliate_commission_tiers WHERE tenant_id IN (1,7);
-- id=4, tenant_id=1, level_1_pct=8.88   ⬅️ اتغيّر (الحقيقي)
-- id=3, tenant_id=7, level_1_pct=42.42  ⬅️ زي ما هو، لم يُمس
```
**الكتابة أثّرت على tenant الحقيقي بس (1)، وtenant 7 فضل سليم 100%
بلا أي تغيير رغم إرسال هيدره صراحة.** الثغرة مقفولة فعليًا، مؤكَّد
بتحقق حي كامل (قراءة قبل وبعد + كتابة + تحقق DB مباشر)، مش بس قراءة
كود.

### التنظيف (تم بالكامل، تحقَّق بـSELECT مباشر)
حذف `affiliate_commission_tiers` (id=3, id=4) → `academy_tenants`
(id=7) → `users` (id=17). تحقق نهائي: صفر صفوف متبقية من أي منهم.
السيرفر التجريبي اتوقف وتأكَّد توقفه (`curl` رجّع فشل اتصال).

### الاكتشاف النظامي الأوسع (خارج نطاق تنفيذ Phase 10c، موثَّق منفصلًا)
أثناء نقاش القرار المعماري، اتسأل: هل نفس النمط موجود في دومينات
تانية؟ فحص read-only (3 agents متوازية، grep + قراءة كود، بلا أي
اختبار حي) عبر كل الـ29 دومين التاني اللي بيستخدموا `get_current_tenant`
لقى: **20 دومين (منهم affiliate نفسه) عندهم نفس شكل الثغرة أو أسوأ**
(بعضهم بلا حماية admin أصلًا، بعضهم بصفر فحص tenant حتى بالهيدر). 9
دومين طلعوا SAFE (مربوطين بـcurrent_user.id في كل مسار حساس، أو مفيش
admin endpoints أصلًا). التفاصيل الكاملة والتصنيف لكل دومين موثَّقة في
`.claude/plans/critical-finding-xtenant-systemic.md` — **تقرير تشخيصي
بحت، صفر تنفيذ، القرار (إصلاح مركزي محتمل في `get_current_tenant` نفسها
مقابل إصلاح دومين ورا التاني) مؤجَّل بالكامل لجلسة/جلسات منفصلة بخطة
اختبار شاملة.**

**ملاحظة جانبية اتلقت أثناء الفحص (خارج نطاقنا تمامًا):** `agritech/router.py`
طلع نسخة قديمة زايدة من `ai_governance` (تصادم مسارات فعلي في
`main.py`) — بق بنيوي منفصل تمامًا عن ثغرة X-Tenant-ID، يستاهل تبليغ
لفريق المشروع، لم يُفحص أو يُصلَح هنا.

---

## [2026-08-11] — Phase 11، الجزء 1 (توثيق فقط، صفر تعديل كود):
تثبيت باج `agritech/router.py` كـ"معلَّق — يحتاج قرار منفصل"

**الحالة:** ⚠️ اكتشاف موثَّق — **لم يُعالَج، ولن يُعالَج في هذه الجلسة**
(بق وظيفي منفصل تمامًا عن ثغرة X-Tenant-ID، خارج نطاق Phase 10c/11 بالكامل)

**السياق:** كانت ملاحظة جانبية عابرة في ذيل إدخال Phase 10c أعلاه (اتلقت
أثناء فحص الـ29 دومين لثغرة X-Tenant-ID). هذا الإدخال يثبّتها كبند مستقل
موثَّق بالتفصيل الكامل (تأكَّد فعليًا بقراءة الكود، مش نقل عن الملاحظة
القديمة فقط)، تمهيدًا لتبليغه للفريق كمهمة منفصلة.

**التأكيد الفعلي (قراءة كود، بدون أي تعديل):**
- `app/domains/agritech/router.py` **محتواه بالكامل نسخة طبق الأصل من
  `ai_governance/router.py`** — تعليق رأس الملف نفسه لسه بيقول
  `# app/domains/ai_governance/router.py` (سطر 1)، والراوتر معرَّف
  `APIRouter(prefix="/ai-governance", tags=["AI Agent Governance"])`
  (سطر 22) — نفس الـendpoints بالظبط (`/agents/{agent_id}/quotas`,
  `/rate-limit`, `/audit-logs`, `/usage-summary`, `/check-and-consume`,
  `/quotas/reset`)، نفس الاستيراد لـ`AIGovernanceService`.
- `app/main.py:270,272`: `agritech_router` و`ai_governance_router`
  **الاتنين مسجَّلين في نفس `routers_config`**. بما إن حلقة التسجيل
  (`main.py:302-308`) بتضيف بس `prefix="/api"` من بره (متغير
  `prefix_path` زي `/agritech` مش مُستخدَم فعليًا فيها — موثَّق سابقًا في
  إدخال Phase 5 أعلاه)، والـprefix الفعلي بييجي من `APIRouter(prefix=...)`
  الداخلي لكل راوتر، فالناتج: **مسارات `agritech_router` الفعلية هي
  `/api/ai-governance/*` بالظبط — نفس مسارات `ai_governance_router`
  الحقيقي حرفيًا، تصادم كامل**. بما إن `agritech_router` مُسجَّل أولًا
  (سطر 270، قبل `ai_governance_router` في سطر 272)، طلباته بتوصل لنسخة
  agritech المكرَّرة أولًا (نفس المنطق حرفيًا، فالسلوك الوظيفي الظاهري
  للمستخدم مش هيختلف، لكن ده لسه تصادم مسارات حقيقي وكود ميت خطير).
- **كود agritech الحقيقي غير معروض بأي router إطلاقًا:** `agritech/
  service.py` فيه فعليًا منطق كامل لـ`SmartFarm`/`FarmZone`/`CropCycle`
  (المزارع، المناطق، دورات الزراعة — تأكَّد بقراءة `service.py:59-131`
  وما بعده: `create_farm`, `list_farms`, `get_farm`, `add_farm_zone`...
  إلخ)، لكن **صفر endpoint في `agritech/router.py` الحالي بيستدعي أي
  دالة من دي** — كل الملف بيستدعي `AIGovernanceService` بدل خدمة
  agritech الحقيقية. يعني وظيفة agritech الفعلية (المزارع/المناطق/دورات
  الزراعة) **غير قابلة للوصول من الـAPI إطلاقًا**، رغم وجود الكود الكامل
  ليها في `service.py`/`models.py`/`repository.py`.

**القرار:** توثيق فقط، **معلَّق — يحتاج قرار منفصل** (هل يُعاد بناء
`agritech/router.py` ليعرض `AgritechService` الحقيقية، أم يُحذف الملف
المكرَّر ويُكتب من الصفر؟). صفر تنفيذ في هذه الجلسة، صفر لمس لأي ملف في
دومين agritech أو ai_governance.

**الملفات المفحوصة فقط (بدون أي تعديل):** `eppne-backend/app/domains/
agritech/router.py`, `eppne-backend/app/domains/agritech/service.py`,
`eppne-backend/app/domains/ai_governance/router.py`,
`eppne-backend/app/main.py` (سطور 270،272،302-308).

---

## [2026-08-11] — Phase 11، الجزء 2: تحقق حي (read-only على مستوى
الاستغلال) لثغرة `automation/router.py` (secrets) من التقرير النظامي —
النتيجة **أدق ممـا افترضه الفحص الأصلي المبني على قراءة الكود فقط**

**الحالة:** ✅ تحقق حي مكتمل، بيانات الاختبار اتنضّفت بالكامل، السيرفر
التجريبي اتوقف. **صفر إصلاح كود** — تشخيص وتحقق فقط، حسب الطلب الصريح.

**السؤال المطلوب تأكيده/نفيه حيًا:** هل أي **مستخدم عادي (مش سوبريوزر)**
يقدر يقرأ/يمسح secrets تخص tenant تاني عبر `automation/router.py:305-349`
(`create_secret`/`list_secrets`/`delete_secret`)، زي ما صنَّفه تقرير
`.claude/plans/critical-finding-xtenant-systemic.md` (بند 7، وصفه
"أسوأ من affiliate: مفيش حتى فحص superuser")؟

### الفحص الأول (read-only، تأكيد الفهم من الكود قبل أي تحقق حي)
تأكَّد فعليًا إن الـ3 endpoints بتاعت الأسرار محمية بـ
`Depends(get_current_active_user)` بس (`router.py:307-311,325-329,338-343`
— **صفر `get_current_superuser`**)، وإن `tenant_id` بيُستخرج من
`tenant: AcademyTenant = Depends(get_current_tenant)` (الهيدر، غير
موثوق) مش من `current_user.tenant_id`، وإن `repository.py:169-198`
بيفلتر بـ`tenant_id` ده مباشرة في `WHERE`/`DELETE` بلا أي مقارنة إضافية.
هذا الجزء **مطابق تمامًا** لما ورد في التقرير النظامي.

**اكتشاف إضافي أثناء الفحص (خارج هذا الملف، لم يظهر في `router.py` نفسه):**
كل راوتر في `main.py:302-308` بيتسجَّل بـ
`dependencies=[Depends(require_sector(sector))]` — طبقة حماية **منفصلة
تمامًا** ومُطبَّقة **على مستوى main.py**، مش ظاهرة لمين بيقرا `router.py`
لوحده (وده بالظبط السبب اللي خلّى فحص Phase 10 القرائي الأصلي يفوّتها).
`require_sector` (`api/deps.py:86-115`) بيتحقق من `current_user.sector`؛
بما إن موديل `User` (`identity/models.py`) **مالوش عمود `sector`
إطلاقًا**، القيمة دايمًا `None`، فبيقع على fallback: لو الدور
`EXECUTIVE_DIRECTOR`/`SUPER_ADMIN` → `sector="all"` (تجاوز كامل)، **غير
كده** (أي `USER` عادي) → `sector="academy"` دايمًا، ثابت، بغض النظر عن
أي حاجة. يعني بالتصميم الحالي: **مفيش أي مستخدم `USER` عادي (غير
سوبريوزر) يقدر يوصل لأي endpoint تحت `/api/automation/*` أصلًا** —
بيتصدّه `require_sector` قبل ما يوصل حتى لمنطق الـtenant في الراوتر
نفسه.

### التحقق الحي (سيرفر uvicorn محلي، DB/Redis عبر docker الموجودين
مسبقًا — `eppne_db`:5435، `redis`:6380)

**الإعداد:** Tenant B تجريبي (`academy_tenants` id=8، اسم "Phase11
Verify Tenant B")، مستخدم عادي حقيقي تحته (`phase11_tenantb_user`،
id=18، دور `USER`، **تينانته الحقيقي=8** مؤكَّد من الـJWT وقت اللوجن)،
ومستخدم عادي حقيقي تاني تحت التينانت الحقيقي=1 كـ"مهاجم"
(`phase11_tenanta_atk`، id=19، دور `USER`، تينانته الحقيقي=1).

**اختبار 1 (المحاولة الأصلية المطلوبة تحديدًا — إنشاء سر كمستخدم عادي
تحت تينانته الحقيقي، بدون أي تزوير):**
```
POST /api/automation/secrets HTTP/1.1
X-Tenant-ID: 8
Cookie: <جلسة phase11_tenantb_user، دور USER، تينانت حقيقي=8>
Body: {"name":"phase11_verify_secret","value":"TENANT-B-SUPER-SECRET-API-KEY-42"}
```
```
HTTP/1.1 403 Forbidden
{"detail":"User sector not defined. Please contact support.","code":"PermissionDeniedError"}
```
حتى **صاحب التينانت الحقيقي نفسه** (مش مهاجم) اتصدّ — تأكيد إن الطبقة
دي مش خاصة بـtenant، لكن بمنع أي `USER` عادي عن الدومين كله.

**اختبار 2 (القراءة — مهاجم `USER` عادي تينانته الحقيقي=1، بهيدر مزوَّر
X-Tenant-ID: 8):**
```
GET /api/automation/secrets HTTP/1.1
X-Tenant-ID: 8
Cookie: <جلسة phase11_tenanta_atk، دور USER، تينانت حقيقي=1>
```
```
HTTP/1.1 403 Forbidden
{"detail":"User sector not defined. Please contact support.","code":"PermissionDeniedError"}
```

**اختبار 3 (الحذف — نفس المهاجم، نفس الهيدر المزوَّر):**
```
DELETE /api/automation/secrets/phase11_verify_secret HTTP/1.1
X-Tenant-ID: 8
Cookie: <نفس جلسة المهاجم>
```
```
HTTP/1.1 403 Forbidden
{"detail":"User sector not defined. Please contact support.","code":"PermissionDeniedError"}
```
تحقُّق DB مباشر بعد الاختبارات 1-3: `SELECT count(*) FROM
automation_secrets WHERE tenant_id=8` → **0** — مفيش أي سر اتخلق أو
اتسرَّب أو اتمسح، لأن الطبقة الخارجية صدّت كل المحاولات قبل ما توصل
للراوتر.

**الخلاصة الجزئية لهذا السؤال بالضبط (كما طُرح): منفيّة حيًا.** مستخدم
عادي (`USER`، مش سوبريوزر) **مايقدرش** يقرأ ولا يمسح ولا حتى ينشئ أي سر
عبر `automation/router.py` حاليًا — بيتصدّه `require_sector` قبل ما
يوصل لمنطق `X-Tenant-ID` في الراوتر أصلًا، بصرف النظر عن أي تزوير هيدر.

### تحقق إضافي (لتوصيف الفاعل الفعلي القادر على الاستغلال، بنفس نطاق
automation فقط) — الثغرة **حقيقية فعليًا**، لكن للسوبريوزر مش للمستخدم
العادي

بما إن `require_sector` بيدي تجاوز كامل (`sector="all"`) للأدوار
`EXECUTIVE_DIRECTOR`/`SUPER_ADMIN` فقط، اتعمل تحقق تكميلي (بنفس أدوات
الجلسة، صفر خروج عن دومين automation) لمعرفة هل ثغرة X-Tenant-ID
الموصوفة في التقرير النظامي حقيقية **لهذا الفاعل تحديدًا** (نفس فئة
فاعل ثغرة affiliate المُصلَحة في Phase 10c):

رُقّي `phase11_tenantb_user` (id=18) و`phase11_tenanta_atk` (id=19)
لـ`SUPER_ADMIN` عبر `UPDATE users SET system_role='SUPER_ADMIN'`
(الجلستان الحاليتان فضلتا صالحتين — `get_current_user` بيقرا الدور من
DB في كل طلب، مش من الـJWT). أُنشئ سر شرعي كسوبريوزر تينانت B الحقيقي:

```
POST /api/automation/secrets HTTP/1.1
X-Tenant-ID: 8
Cookie: <جلسة phase11_tenantb_user، دور SUPER_ADMIN دلوقتي، تينانت حقيقي=8>
```
```
HTTP/1.1 201 Created
{"id":1,"name":"phase11_verify_secret","created_at":"2026-08-11T14:29:09.686784Z"}
```

بعدين هجوم فعلي بسوبريوزر تينانته الحقيقي=1 (`phase11_tenanta_atk`)
بهيدر مزوَّر `X-Tenant-ID: 8`:

```
GET /api/automation/secrets HTTP/1.1
X-Tenant-ID: 8
Cookie: <جلسة phase11_tenanta_atk، دور SUPER_ADMIN دلوقتي، تينانت حقيقي=1>
```
```
HTTP/1.1 200 OK
[{"id":1,"name":"phase11_verify_secret","created_at":"2026-08-11T14:29:09.686784Z"}]
```
تسريب حقيقي (id/name/created_at) لمورد تينانت تاني — **لكن مش القيمة
الخام للسر**: `SecretResponse` (`schemas.py:274-279`) بيقتصر على
`id/name/created_at` بس، فمفيش أي endpoint بيرجّع `value` الفعلية في
أي استجابة API — القيمة بتتفك تشفيرها داخليًا في `repository.py` بس
بتتفلتر بواسطة `response_model` قبل ما توصل للعميل.

```
DELETE /api/automation/secrets/phase11_verify_secret HTTP/1.1
X-Tenant-ID: 8
Cookie: <نفس جلسة المهاجم السوبريوزر>
```
```
HTTP/1.1 200 OK
{"message":"Secret deleted"}
```
تحقق DB مباشر فور الطلب: `SELECT id, tenant_id, name FROM
automation_secrets WHERE tenant_id=8` → **0 صفوف**. **الحذف حقيقي
ومُنفَّذ فعليًا في القاعدة، مش مجرد استجابة.**

**الخلاصة الكاملة:** ثغرة `X-Tenant-ID` الموصوفة في التقرير النظامي
لـ`automation/router.py` **مؤكَّدة حيًا وحقيقية 100%** (قراءة meta-data
+ حذف فعلي كاملين عبر تينانت غير مصرَّح به) — **لكن الفاعل القادر على
الوصول لها أصلًا محصور بـ`EXECUTIVE_DIRECTOR`/`SUPER_ADMIN` بسبب طبقة
`require_sector` المنفصلة، مش أي مستخدم `USER` عادي** كما وصفها التقرير
النظامي الأصلي (المبني على قراءة `router.py` لوحده بدون رؤية طبقة
`main.py`). هذا **يصحّح دقة التصنيف** (بند 7 في التقرير النظامي) دون
تغيير الخلاصة الجوهرية: نفس فئة الفاعل اللي استغلت affiliate (سوبريوزر
من تينانت مختلف) قادرة على نفس النوع من الاستغلال هنا كمان — أخطر من
حيث الأثر (حذف secrets/API keys فعلي، لا فقط قراءة بيانات مالية)، لكن
أضيق نطاق فاعلين مما ذُكر أصلًا (سوبريوزر بس، مش أي مستخدم مسجَّل).

### التنظيف (تم بالكامل، تحقَّق بـSELECT مباشر)
- `automation_secrets`: 0 صفوف لـtenant_id=8 (اتحذف عبر الهجوم نفسه، تأكَّد).
- `DELETE FROM users WHERE id=19` (المهاجم) + `DELETE FROM academy_tenants
  WHERE id=8` (بيكاسكيد يحذف `user id=18` تلقائيًا عبر
  `fk_users_tenant_id ... ON DELETE CASCADE`). تحقق نهائي: `tenant_8=0`,
  `user_18=0`, `user_19=0`, `secrets_tenant8=0` — كله صفر.
- ملفات كوكيز/لوج مؤقتة اتعملت أثناء التحقق (`phase11_tenantb_cookies.txt`,
  `phase11_tenanta_cookies.txt`, `phase11_server.log`) اتمسحت بالكامل من
  `eppne-backend/`.
- سيرفر uvicorn التجريبي (PID اتأكَّد بـ`netstat`/`tasklist` إنه
  المستمع على المنفذ 8000) اتوقف (`taskkill /F`)، وتأكَّد توقفه فعليًا
  (`curl` رجّع فشل اتصال بعدها).
- **لم يُلمس أي ملف كود** (`router.py`/`service.py`/`repository.py`/
  `api/deps.py`) في أي دومين — تحقق حي وتشخيص فقط، صفر تنفيذ، حسب الطلب
  الصريح. الإصلاح (لو تقرَّر) مهمة منفصلة لاحقة بموافقة صريحة.

**ملاحظة جانبية غير مفحوصة بعمق (خارج نطاق هذه الجلسة، مرشَّحة لتحقق
لاحق):** هل نفس فجوة `require_sector` (كل مستخدم `USER` عادي محصور
تلقائيًا بـ`sector="academy"` لعدم وجود عمود `sector` على الموديل من
الأساس) بتحصل في **كل الدومينات التانية** المسجَّلة عبر نفس حلقة
`routers_config` (مش automation بس)؟ لو كده، فده معناه إن جزء كبير من
الـ20 دومين "SUSPICIOUS" في التقرير النظامي ممكن يكون فعليًا **غير قابل
للوصول من مستخدمين عاديين أصلًا** (نفس نمط automation)، وإن الفاعل
الحقيقي في كل الحالات دي محصور بالسوبريوزر بس — **ده يحتاج تحقق حي
منفصل لكل دومين قبل أي افتراض**، لم يُفحص هنا (خارج نطاق Phase 11
المحدَّد بـagritech توثيق + automation تحقق فقط).

**الملفات المفحوصة فقط (بدون أي تعديل كود):** `eppne-backend/app/
domains/automation/router.py`, `eppne-backend/app/domains/automation/
service.py`, `eppne-backend/app/domains/automation/repository.py`,
`eppne-backend/app/domains/automation/models.py`, `eppne-backend/app/
domains/automation/schemas.py`, `eppne-backend/app/api/deps.py`,
`eppne-backend/app/main.py`.

---

## [2026-08-11] — Phase 12: إصلاح ثغرة X-Tenant-ID في `automation/router.py`
(secrets) — نفس نمط Phase 10c بالظبط

**الحالة:** 🟢 **الإصلاح تم على الـ3 endpoints، اتحقَّق منه حيًا (قراءة +
حذف + مقارنة مع سلوك المالك الشرعي)، بيانات الاختبار اتنضّفت، السيرفر
التجريبي اتوقف.**

### السياق
الثغرة كانت مؤكَّدة حيًا بالكامل في Phase 11 (راجع الإدخال أعلاه): سوبريوزر
(`SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` — الوحيدين القادرين على تخطي
`require_sector`) من تينانت حقيقي مختلف قادر يقرأ metadata أسرار (secrets)
تينانت تاني ويحذفها فعليًا عبر تزوير هيدر `X-Tenant-ID`، لأن
`create_secret`/`list_secrets`/`delete_secret` كانت بتاخد الـ`tenant_id`
من `Depends(get_current_tenant)` (الهيدر) بدل `current_user.tenant_id`
(التوكن الموقَّع).

### الإصلاح المُنفَّذ
`app/domains/automation/router.py` — الـ3 endpoints فقط
(`POST/GET /secrets`, `DELETE /secrets/{secret_name}`): إزالة
`tenant: AcademyTenant = Depends(get_current_tenant)` من توقيع كل واحدة،
واستبدال `tenant_id=cast(int, tenant.id)` بـ
`tenant_id=cast(int, current_user.tenant_id)` في استدعاء
`AutomationService`. لم يُلمس أي endpoint تاني في `automation` (الملف
فيه 12 endpoint تاني — workflows/triggers/webhook/executions/logs —
خارج نطاق الثغرة، لم تُفحص أو تُعدَّل). لم يُلمس أي دومين تاني.

### التحقق الحي (سيرفر uvicorn محلي، DB/Redis عبر docker الموجودين
مسبقًا — `eppne_db`:5435، `redis`:6380؛ الإصلاح طُبِّق على الكود **قبل**
تشغيل السيرفر، فالمرجع لحالة "قبل الإصلاح" هو التحقق الحي الموثَّق فعليًا
في Phase 11 أعلاه — نفس السيناريو بالضبط، بدون إعادة كسر الكود لإعادة
اختباره)

**بيانات throwaway جديدة (منفصلة عن Phase 11):** Tenant B تجريبي
(`academy_tenants` id=9، "Phase12 Verify Tenant B")، مستخدم صاحب تينانت
حقيقي (`phase12_tenantb_user`، id=21، تينانته الحقيقي=9)، مستخدم "مهاجم"
تحت تينانت حقيقي مختلف (`phase12_tenanta_atk`، id=22، تينانته الحقيقي=1)
— الاتنين رُقّيا لـ`SUPER_ADMIN` عبر `UPDATE users SET
system_role='SUPER_ADMIN'` **قبل** تسجيل الدخول (عشان الـJWT يحمل
`tenant_id` الصحيح من الأساس، بما إن `get_current_user`
(`api/deps.py:50`) بيقارن `token_tenant_id` مع DB في `get_by_id` — تغيير
`tenant_id` بعد إصدار التوكن كان هيكسر الجلسة).

**مرجع "قبل" (من Phase 11، حي فعليًا، نفس السيناريو):**
```
GET /api/automation/secrets HTTP/1.1
X-Tenant-ID: 8   ⬅️ مزوَّر، تينانت المهاجم الحقيقي=1
→ HTTP/1.1 200 OK  [{"id":1,"name":"phase11_verify_secret",...}]   (تسريب حقيقي)

DELETE /api/automation/secrets/phase11_verify_secret HTTP/1.1
X-Tenant-ID: 8
→ HTTP/1.1 200 OK  {"message":"Secret deleted"}
تحقق DB فوري: tenant_id=8 → 0 صفوف (حذف فعلي منفَّذ في القاعدة لتينانت تاني)
```

**"بعد" (هذه الجلسة، بالكود المُعدَّل):**

اختبار A — إنشاء شرعي كصاحب التينانت الحقيقي (`phase12_tenantb_user`،
تينانت=9):
```
POST /api/automation/secrets HTTP/1.1
X-Tenant-ID: 9
→ HTTP/1.1 201 Created  {"id":2,"name":"phase12_verify_secret",...}
```
تحقق DB: `automation_secrets` id=2, tenant_id=9.

اختبار B (القراءة — نفس محاولة الاستغلال بالضبط): مهاجم
`phase12_tenanta_atk` (تينانته الحقيقي=1)، بهيدر مزوَّر `X-Tenant-ID: 9`:
```
GET /api/automation/secrets HTTP/1.1
X-Tenant-ID: 9   ⬅️ مزوَّر
→ HTTP/1.1 200 OK  []
```
رجّعت بيانات تينانت المهاجم الحقيقي (1، فاضي) — **مش** سر تينانت 9، رغم
الهيدر. الهيدر بقى بلا أي تأثير.

اختبار C (الحذف — نفس المهاجم، نفس الهيدر المزوَّر):
```
DELETE /api/automation/secrets/phase12_verify_secret HTTP/1.1
X-Tenant-ID: 9   ⬅️ مزوَّر
→ HTTP/1.1 200 OK  {"message":"Secret deleted"}
```
الرسالة عامة (سلوك موجود مسبقًا في `repository.delete_secret` — `DELETE
... WHERE tenant_id=X AND name=Y` بلا rowcount check، لم يتغيَّر بهذا
الإصلاح). **تحقق DB فوري بعد الطلب مباشرة:**
```sql
SELECT id, tenant_id, name FROM automation_secrets;
-- id=2, tenant_id=9, name='phase12_verify_secret'   ⬅️ لسه موجود، لم يُمس
```
الحذف اتنفَّذ فعليًا ضد `tenant_id=1` (تينانت المهاجم الحقيقي، مفيهوش صف
بهذا الاسم) فمفيش أي تأثير — **سر تينانت 9 فضل سليم 100% رغم الهيدر
المزوَّر صراحةً.**

اختبار D/E (تأكيد إن المسار الشرعي لسه شغّال، مش بس إن الهجوم اتصدّ):
صاحب التينانت الحقيقي (`phase12_tenantb_user`) عمل `GET /secrets` بعد
محاولة الهجوم → `200 OK` شاف سره بشكل طبيعي (`[{"id":2,...}]`)، وبعدين
`DELETE /secrets/phase12_verify_secret` → `200 OK`، تحقق DB فوري:
`SELECT count(*) FROM automation_secrets WHERE tenant_id=9` → **0**.
الحذف الحقيقي لصاحب التينانت اشتغل تمام.

**الخلاصة:** الهيدر بقى بلا أي تأثير فعلي على الـ3 endpoints؛ الـscoping
بقى كليًا من `current_user.tenant_id` (من التوكن الموقَّع، غير قابل
للتزوير من العميل)؛ لا كسر لأي وظيفة شرعية. الثغرة الموصوفة في Phase 11
(مؤكَّدة حيًا وقتها لفاعل `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` تحديدًا،
محصورة بـ`require_sector`) **مقفولة فعليًا**.

### التنظيف (تم بالكامل، تحقَّق بـSELECT مباشر)
- `DELETE FROM users WHERE id IN (21,22)` (تينانت B الحقيقي + المهاجم) →
  `DELETE FROM academy_tenants WHERE id=9` → `DELETE FROM users WHERE
  id=20` (المستخدم المؤقت اللي استُخدم كـ`admin_id` عشان إنشاء التينانت
  عبر SQL مباشر، بما إن العمود `NOT NULL`). تحقق نهائي: `tenant_9=0`,
  `users_20_21_22=0`, `secrets_tenant9=0` — كله صفر.
- ملف لوج السيرفر المؤقت (`phase12_uvicorn.log`) وملفات الكوكيز
  (`phase12_tenantb_cookies.txt`, `phase12_tenanta_cookies.txt`) اتمسحوا
  بالكامل من `eppne-backend/`.
- سيرفر uvicorn التجريبي (PID اتأكَّد بـ`netstat`/`tasklist` إنه
  المستمع على المنفذ 8000) اتوقف (`taskkill /F`)، وتأكَّد توقفه فعليًا
  (`curl` رجّع فشل اتصال بعدها).
- **لم يُلمس أي كود غير `automation/router.py`** — نفس نطاق Phase 10c
  بالضبط (endpoint دومين واحد محدَّد، صفر تغيير في `service.py`/
  `repository.py`/`api/deps.py`/أي دومين تاني).

### ملاحظة نطاق (بدون تنفيذ)
الاكتشاف النظامي الأوسع (19 دومين تاني بنفس شكل الثقة بالهيدر، موثَّق في
`.claude/plans/critical-finding-xtenant-systemic.md`) **لسه بدون قرار
مركزي** — Phase 12 دي إصلاح تدريجي لدومين واحد بس (زي Phase 10c بالظبط
لـaffiliate)، مش جزء من أي حل مركزي. الملف المرجعي لم يُعدَّل.

---

## [2026-08-11] — Phase 13: إصلاح تصادم المسارات `agritech` ↔ `ai_governance`
(حذف فوري للملف المكرَّر — بق هيكلي منفصل تمامًا عن ثغرة X-Tenant-ID)

**الحالة:** 🟢 **الإصلاح تم، اتحقَّق منه حيًا (uvicorn فعلي + فحص
OpenAPI + طلبات HTTP حقيقية)، صفر تأثير جانبي، السيرفر التجريبي اتوقف
والملفات المؤقتة اتنضّفت.**

### التأكيد الحي (قبل التنفيذ)
أُعيدت قراءة `agritech/router.py` و`ai_governance/router.py` و
`agritech/service.py`/`models.py`/`schemas.py`/`repository.py` بالكامل و
`main.py` (الاستيرادات + `routers_config` + حلقة التسجيل)، فأكَّدت
اكتشاف Phase 11 بتفصيل أدق: `agritech/router.py` كان نسخة **قديمة** من
`ai_governance/router.py` (ناقص endpoint `GET /quotas/remaining` ومنطق
تفويض أحدث `_check_agent_ownership`)، ومسجَّل **قبل** `ai_governance_router`
في `routers_config` (سطر 270 قبل 272) — يعني كل طلبات `/api/ai-governance/*`
كانت فعليًا بتتخدم من النسخة القديمة المدفونة جوه `agritech/router.py`،
مش من `ai_governance/router.py` الصحيح: `endpoint` المفقود غير قابل
للوصول إطلاقًا، ومنطق التفويض الأحدث متجاوَز فعليًا في الإنتاج. كمان
تأكَّد إن `agritech/models.py`+`schemas.py`+`repository.py`+`service.py`
كاملين ومعماريًا جاهزين (11 جدول، عزل tenant صحيح) لكن **بدون أي router
يعرضهم** — نفس اكتشاف Phase 11 بالظبط.

### القرار (بموافقة صريحة من المستخدم)
اتعرض للمستخدم 3 خيارات (إصلاح فوري فقط / إصلاح فوري + بناء router
كامل الآن / بناء router فقط بدون لمس main.py) — **اختار الخيار 1: إصلاح
فوري فقط**. بناء `router.py` حقيقي لـagritech (feature جديد كامل يعرض
farms/zones/crop-cycles/harvest/bio-assets/supply-chain/certificates/
soil-sensors/weather-alerts) **مؤجَّل بالكامل لمراجعة/جلسة منفصلة لاحقًا،
لم يُنفَّذ هنا**.

### التنفيذ (تم)
- `eppne-backend/app/main.py`: حذف سطر `from app.domains.agritech.router
  import router as agritech_router` (كان سطر 35)، وحذف عنصر
  `(agritech_router, "/agritech", ["Agritech"], "agritech")` من
  `routers_config`. صفر تغيير في `ai_governance/router.py` أو أي دومين
  تاني.
- `eppne-backend/app/domains/agritech/router.py`: **حُذف بالكامل** (كود
  ميت مكرَّر، صفر قيمة وظيفية حقيقية).
- فحصت مراجع تانية لـ`agritech_router`/`agritech.router` في المشروع
  كله: `alembic/env.py` و`migrations/env.py` بيستوردوا `agritech.models`
  فقط (للـmigrations، مش الراوتر)، و`app/tasks/agritech.py` بيستخدم
  `AgriTechRepository`/`AgriTechService` مباشرة (Celery tasks، مش
  الراوتر) — **صفر ملف تاني بيعتمد على `agritech/router.py` المحذوف**.

### التحقق الحي (uvicorn فعلي، مش import بس)
- شغَّلت `uvicorn app.main:app` فعليًا على `127.0.0.1:8000` (عبر
  `venv/Scripts/python.exe`) في الخلفية، اللوج سجَّل `INFO: Application
  startup complete.` و`INFO: Uvicorn running on http://127.0.0.1:8000`
  **بدون أي استثناء أو تحذير تصادم/تسجيل مسارات** (اللوج الضخم اللي
  ظهر كان تكرار تحذير encoding يونيكود قديم في الكونسول العربي
  (`UnicodeEncodeError` على emoji ✅ في `logging_conf.py`) بسبب
  lifespan contexts متداخلة لكل الراوترز — **غير مرتبط بتاتًا بتعديلنا**،
  نفس التحذير ظهر مسبقًا عند اختبار `import app.main` وحده.
- جلبت `GET /openapi.json` حي وفحصته: **صفر مسار فيه `/agritech`**،
  و`/ai-governance` فيه 7 مسارات تتضمن `GET /quotas/remaining` (كان
  غير قابل للوصول قبل الإصلاح).
- طلبات HTTP حقيقية: `GET /api/agritech/farms` → **404** (بدل تصادم
  صامت)، `GET /api/ai-governance/agents/1/quotas/remaining` → **401**
  (المسار موجود وبيتفعّل فحص الهوية بشكل طبيعي، مش 404).
- أوقفت السيرفر التجريبي (`taskkill /F` على الـPID اللي كان مستمع على
  المنفذ 8000، تأكَّد بـ`netstat` إن مفيش listener تاني)، ومسحت ملف
  اللوج المؤقت (`phase13_uvicorn.log`) وملف الـOpenAPI المؤقت من مجلد
  scratchpad الجلسة (خارج شجرة المشروع أصلًا).

### الأثر الوظيفي
`/api/ai-governance/*` بقى بيتخدم فقط من `ai_governance/router.py`
الصحيح والمُحدَّث (endpoint `/quotas/remaining` رجع يشتغل فعليًا،
منطق `_check_agent_ownership` رجع يتطبَّق). `/api/agritech/*` بقى
`404` صريح (بدل وهم إنه شغال وهو فعليًا بيخدم `ai-governance`) — نفس
الوضع الوظيفي الفعلي اللي كان موجود قبل الإصلاح (agritech مكنش متاح
فعليًا أصلًا)، لكن دلوقتي بوضوح بدل تصادم صامت.

### النطاق المتبقي (مؤجَّل، لم يُنفَّذ)
بناء `agritech/router.py` حقيقي يعرض `AgriTechService` — **مهمة منفصلة
تحتاج نطاق واختبار خاص بيها**، خارج Phase 13 بالكامل.

**الملفات المعدَّلة:** `eppne-backend/app/main.py` (تعديل).
**الملفات المحذوفة:** `eppne-backend/app/domains/agritech/router.py`.
**الملفات المفحوصة فقط (بدون تعديل):** `eppne-backend/app/domains/
ai_governance/router.py`, `eppne-backend/app/domains/agritech/
{service,models,schemas,repository}.py`, `eppne-backend/alembic/env.py`,
`eppne-backend/migrations/env.py`, `eppne-backend/app/tasks/agritech.py`.

---

## [2026-08-11] — Phase 14: إكمال الفحص الشامل لثغرة X-Tenant-ID —
سدّ فجوة في تغطية التقرير الأصلي (6 دومينات كانت ناقصة)

**الحالة:** ✅ مكتمل، read-only بالكامل (صفر تعديل كود). الملف الكامل
المُحدَّث: `.claude/plans/critical-finding-xtenant-systemic.md`.

**السياق:** التقرير الأصلي (Phase 10c، `critical-finding-xtenant-
systemic.md`) غطّى 29 دومين بس، رغم إن `app/domains/` فيه 35 مجلد
فعلي. الفحص كان ناقص لـ6 مجلدات: `admin`, `auth`, `identity`,
`invoicing`, `iot`, `privacy`.

**المنهجية:** نفس معيار التقرير الأصلي بالحرف (endpoint محمي بصلاحية
مرتفعة بيقرأ/يكتب مورد غير مرتبط بملكية المستخدم، معتمدًا على
`tenant_id` من `get_current_tenant`/الهيدر بدون مقارنة مع
`current_user.tenant_id`) — قراءة كود فقط، صفر تحقق حي جديد في هذه
الجلسة.

**النتيجة:**
- **`admin`, `invoicing`, `iot`, `privacy` → 🟢 SAFE.** الأربعة صفر
  استخدام لـ`get_current_tenant`/الهيدر إطلاقًا (grep شامل، صفر
  نتائج) — كل تحديد tenant عبر `current_user.tenant_id` الحقيقي من
  الـJWT. `admin` كمان راوترها أصلًا **غير مسجَّل في `main.py`**
  (endpoint وحيد `toggle-ai-agents` غير قابل للوصول حاليًا).
- **`auth` → ⚪ N/A، مستبعد من العدّ.** المجلد فيه `__pycache__` بس،
  صفر ملف `.py` — Phase 4 (commit `eeaf783`) حذفت كوده بالكامل. مفيش
  endpoints تُفحص، فتصنيف SUSPICIOUS/SAFE غير منطبق، مُوثَّق رسميًا
  بدل الاستبعاد الصامت.
- **`identity` → 🟡 فئة مختلفة تمامًا، مش رقم 21 في جدول SUSPICIOUS
  العادي.** بعد نقاش مع المستخدم أثناء المراجعة، تبيَّن إن دمج
  identity في نفس جدول الـ20 دومين (IDOR على مورد موجود) كان سيضلِّل:
  ثغرة identity (`register`, `router.py:30` → `service.py:90`)
  **pre-auth بالكامل** — مفيش `current_user.tenant_id` أصلًا للمقارنة
  معه، والفعل المُستغَل **إنشاء** حساب جديد تحت أي tenant بلا دعوة،
  مش قراءة/تعديل مورد موجود. **هذه نفس الثغرة المؤكَّدة حيًا بالفعل في
  Phase 9** (`phase9-audit-identity-report.md`) — مُدمَجة رسميًا هنا
  في قسمها الخاص بدل ما تفضل ملاحظة منفصلة. **مهم:** الإصلاح المركزي
  المقترح في نفس الملف (تعديل `get_current_tenant` ليتجاهل الهيدر
  للمستخدمين المُصادَق عليهم) **يستثني pre-auth عمدًا، فلا يغطي ولا
  يصلح ثغرة identity دي إطلاقًا** — أُضيفت ملاحظة تحذيرية صريحة في قسم
  "الاقتراح المعماري" نفسه لمنع سوء الفهم ده لاحقًا. باقي endpoints
  identity المحمية (`me`, `sessions`, `revoke-all`...) مؤكَّدة SAFE
  حيًا (نفس Phase 9) — الهيدر المزوَّر بيرجّع 404 fail-safe مش تسريب.
- **ملاحظة منفصلة موثَّقة (خارج نطاق X-Tenant-ID تمامًا):**
  `invoicing/create_invoice` (`router.py:42-70`, تحديدًا سطر 54)
  بياخد `tenant_id` مباشرة من جسم الطلب (`InvoiceCreate.tenant_id`)
  بلا أي admin-gate أو مقارنة مع `current_user.tenant_id` — احتمال
  mass-assignment عبر الـbody (شكل مختلف تمامًا عن ثقة الهيدر، نفس
  سابقة ملاحظة `commerce.create_store` في التقرير الأصلي). **غير
  مؤكَّد حيًا، يحتاج phase منفصل بالكامل.**

**الحصيلة الإجمالية المُحدَّثة:** 20 SUSPICIOUS (زي ما كانت) + 1
مصنَّف في فئة منفصلة (`identity`) + 13 SAFE (9 الأصليين + 4 جدد) = 34
دومين حقيقي مُصنَّف بالكامل (`auth` مستبعد، دومين محذوف).

**لم يُتخذ أي إجراء إصلاحي في هذه الجلسة** — فحص وتوثيق بس، حسب طلب
المستخدم صراحة. القرار بخصوص أي إصلاح (identity، الـ20 دومين،
`invoicing/create_invoice`) لسه مؤجَّل بالكامل لجلسة/جلسات منفصلة.

**الملفات المعدَّلة:** `.claude/plans/critical-finding-xtenant-
systemic.md` (تحديث شامل — جداول التصنيف + قسم identity الجديد +
ملاحظة invoicing + الحصيلة الإجمالية).
**الملفات المفحوصة فقط (بدون تعديل):**
`eppne-backend/app/domains/{admin,auth,identity,invoicing,iot,privacy}/
router.py`، `eppne-backend/app/domains/identity/service.py`،
`eppne-backend/app/main.py` (grep فقط، تأكيد تسجيل/عدم تسجيل الراوترات).

---

## [2026-08-11] — ملاحظة تصميم (Phase 15، أثناء تصميم جدول
`identity_tenant_invitations`): تكرار مفهومي محتمل مع `invitations/models.py`

أثناء تصميم جدول دعوات/إحالة جديد داخل دومين `identity`
(`identity_tenant_invitations` — راجع
`.claude/plans/phase15-identity-registration-invitation-design.md`)،
لوحظ إن دومين `invitations` الموجود بالفعل (نظام CRM/تسويقي منفصل
تمامًا، جدول `sovereign_invitations_v2` عبر
`app/domains/invitations/models.py`) عنده مفهوم "دعوة" بحقول متشابهة
جزئيًا (`target_type`, `target_entity_identifier`, `status`
enum اسمه `invitationstatus` في قاعدة البيانات فعليًا — تأكَّد بفحص حي
لـ`pg_enum`). **لا يوجد أي تداخل وظيفي فعلي حاليًا** — دومين
`invitations` غرضه دعوات عملاء محتملين/حملات تسويقية بمساعدة AI، بينما
الجدول الجديد غرضه دعوات/روابط إحالة انضمام فعلي لتينانت (مرتبط بإصلاح
ثغرة أمنية في `identity/register`). **القرار الصريح لهذه الجلسة:** جدول
منفصل تمامًا (`identity_tenant_invitations`)، صفر توحيد أو ربط مع
`sovereign_invitations_v2`، وصفر لمس لدومين `sovereign_entities` أو
`invitations`. **تُذكَر هنا فقط كملاحظة تستاهل تقييم معماري لاحق منفصل**
(هل الاثنين لازم يفضلوا منفصلين على المدى الطويل، ولا فيه فرصة توحيد
مفيدة؟) — **بدون أي قرار أو تنفيذ في هذا الشأن الآن**.

---

## [2026-08-12] — Phase 15: إصلاح ثغرة self-enrollment في
`identity/register` + بناء مسار دعوة/إحالة جديد

**الحالة:** ✅ **مكتمل بالكامل، مصمَّم ونُفِّذ ونُوثِّق حيًا خطوة خطوة
بموافقة صريحة على كل ملف قبل كتابته**، وتحقَّق منه حيًا (uvicorn فعلي +
11 اختبار HTTP حقيقي + استعلامات DB مباشرة قبل/بعد)، والسيرفر التجريبي
اتوقف والبيانات التجريبية اتنضّفت بالكامل (تحقُّق مستقل بعد التنظيف).

### المشكلة الأصلية (مكتشفة ومؤكَّدة حيًا في Phase 9، مُصنَّفة بدقة في
Phase 14 — `critical-finding-xtenant-systemic.md`)
`POST /identity/register` كانت بتكتب `tenant_id` للمستخدم الجديد من
قيمة هيدر `X-Tenant-ID` مباشرة (عبر `get_current_tenant`،
`api/deps.py:148-153`)، **بلا أي مصادقة أو تفويض** — أي زائر غير
مُصادَق عليه كان يقدر يسجّل حساب تحت أي `tenant_id` موجود بمجرد تغيير
الهيدر (تسجيل فعلي تحت `tenant_id=2` بهيدر مزوَّر، مؤكَّد حيًا في
Phase 9). هذه القيمة كانت بعدين بتتحط كـclaim `tenant_id` في الـJWT
الموقَّع، فتبقى "الهوية" الموثوقة للمستخدم في باقي حياة الجلسة عبر كل
دومين تاني بالمشروع. `login` وباقي الـ8 endpoints المحمية في identity
(`me`, `sessions`, `revoke-all`, `me/password`, `me` DELETE) **كانوا
مؤكَّدين آمنين بالفعل** (Phase 9) ولم يُلمسوا في Phase 15 إطلاقًا.

### الحل المُنفَّذ
1. **`PUBLIC_REGISTRATION_TENANT_ID`** (`app/core/config.py`) — قيمة
   ثابتة (`=1`، مؤكَّدة بفحص حي لقاعدة البيانات المحلية إنه التينانت
   الحقيقي الوحيد الموجود) بمعزل تام عن أي دومين، مع تحقق إلزامي
   (`os.getenv` صريح) في بيئة الإنتاج (fail loud، نفس نمط `SECRET_KEY`).
2. **`POST /identity/register`** — إزالة `Depends(get_current_tenant)`
   نهائيًا، استخدام `settings.PUBLIC_REGISTRATION_TENANT_ID` ثابتًا.
   **هذا هو التعديل الوحيد على مسار حي فعليًا في كل Phase 15.**
3. **جدول جديد `identity_tenant_invitations`** (migration
   `027_create_identity_tenant_invitations`، مُعدَّلة مرة واحدة أثناء
   المراجعة لتحويل `token` من نص صريح لـ`token_hash` مُشفَّر — الجدول
   كان فاضيًا وقتها فصفر فقدان بيانات) — يدعم دعوة انضمام إدارية
   تقليدية (`max_uses=1`) **وكمان** رابط إحالة/عمولة قابل لإعادة
   الاستخدام يُنشئه أي مستخدم مسجّل (`referrer_user_id` + `product_id`
   اختياري لربط عمولة مستقبلي بدومين `affiliate` — **منطق حساب/صرف
   العمولة نفسه خارج نطاق Phase 15 تمامًا، مؤجَّل لجلسة منفصلة**).
4. **`POST /identity/register-with-invitation`** (عام، pre-auth) —
   التينانت بيتحدد من `invitation.tenant_id` نفسها (مُجمَّدة وقت إنشاء
   الدعوة من `current_user.tenant_id` الحقيقي)، **أبدًا من هيدر أو
   جسم الطلب**. حماية من race condition على الدعوات محدودة الاستخدام
   عبر `UPDATE` ذرّي شرطي (`claim_use`/`release_use`) بدل
   `SELECT`-ثم-فحص-ثم-`UPDATE`.
5. **`POST/GET /identity/invitations`, `GET /identity/invitations/{id}`,
   `POST /identity/invitations/{id}/revoke`** — إنشاء متاح لأي مستخدم
   مسجّل (بدون فحص دور)؛ عرض/إبطال دعوة الشخص نفسه دايمًا مسموح، وعرض/
   إبطال دعوة مستخدم تاني محصور بـ`{ADMIN, SUPER_ADMIN,
   EXECUTIVE_DIRECTOR}` (`is_admin_or_above`، دالة جديدة في
   `core/security.py`). التوكن الخام بيظهر مرة واحدة بس وقت الإنشاء
   (`TenantInvitationCreateResponse`)؛ أي استدعاء تاني بيرجّع
   `has_token: bool` بس (صفر تسريب توكنات مستخدمين تانيين).

### التحقق الحي (uvicorn فعلي، 11 اختبار HTTP حقيقي + استعلامات DB مباشرة)
1. تسجيل عام بدون هيدر → `201`, `tenant_id=1` ✅
2. **تسجيل عام مع `X-Tenant-ID` مزوَّر لتينانت اختباري حقيقي منفصل
   (رقم عشوائي مُنشَأ للاختبار) → `201`, لكن `tenant_id=1` مش قيمة
   الهيدر — إثبات مباشر إن الإصلاح شغّال فعليًا، مش بس نظريًا** ✅
3. تسجيل دخول عادي (`login`، بدون أي تعديل) → `200` ✅
4. إنشاء دعوة `max_uses=1` → `201`، توكن خام 43 حرف ✅
5. إنشاء دعوة بلا حد (`max_uses=null`) → `201` ✅
6. تسجيل بدعوة (استخدام أول) → `201`، `tenant_id` المستخدم الجديد =
   تينانت المُحيل بالضبط، `current_uses=1`, `status=ACCEPTED` تلقائيًا ✅
7. **إعادة استخدام نفس التوكن (`max_uses=1` مستنفدة) → `422` رفض،
   صفر مستخدم تاني اتسجل — `claim_use()` الذرّي منع تجاوز الحد** ✅
8. `GET /invitations` (بتاعتي) → `200`, `count=2` ✅
9. **`GET /invitations/{id}` من مستخدم تاني (مش صاحبها، مش إداري) →
   `403` — صفر تسريب بيانات دعوة بين مستخدمين بنفس التينانت** ✅
10. إبطال دعوة بواسطة صاحبها → `200`, `status=REVOKED` ✅
11. تسجيل دخول ارتدادي (تأكيد `login` لسه شغالة زي ما هي) → `200` ✅

### التنظيف (تم بالكامل، تحقُّق مستقل بعد إيقاف السيرفر)
`users WHERE username LIKE 'p15%'` → 0، تينانت الاختبار المؤقت → 0
(اتمسح)، `identity_tenant_invitations` بالكامل → 0 صف متبقي،
`academy_tenants=1`/`users=7` — **نفس القيم بالضبط قبل بدء أي اختبار
في الجلسة كلها**. سيرفر uvicorn التجريبي اتوقف (`taskkill`)، ملفات
اللوج والسكربت المؤقتة اتمسحت.

### ملاحظات نطاق صريحة
- منطق حساب/استحقاق/صرف عمولة الإحالة، وربطه بدومين `affiliate`
  الفعلي — **خارج نطاق Phase 15 تمامًا**، مؤجَّل لجلسة منفصلة. الجدول
  الجديد بيخزّن بيانات الإسناد فقط (`referrer_user_id` + `product_id`).
- الشات بوت / AI-assisted invitation writing / self-service tenant
  creation — **مؤجَّلة**، لم تُناقَش تفصيليًا.
- ربط الدومينات الحقيقية بالتينانتات (بعد الرفع) — **خارج النطاق**،
  `PUBLIC_REGISTRATION_TENANT_ID` قيمة `tenant_id` ثابتة بمعزل تام عن
  أي دومين.
- تبسيط `login` لإزالة اعتماده على `X-Tenant-ID` بالكامل (ممكن نظريًا
  بما إن `username`/`email` unique عالميًا) — **مطروح كملاحظة اختيارية
  فقط، لم يُنفَّذ، `login` لم يُلمس إطلاقًا في Phase 15**.
- تكرار مفهومي مع دومين `invitations` (CRM) — موثَّق في الملاحظة
  السابقة مباشرة أعلاه، صفر توحيد أو لمس.

**الملفات المعدَّلة:** `eppne-backend/app/core/config.py`,
`eppne-backend/app/core/enums.py`, `eppne-backend/app/core/security.py`,
`eppne-backend/app/domains/identity/{models,repository,router,schemas}.py`.
**الملفات الجديدة:** `eppne-backend/app/domains/identity/invitation_service.py`,
`eppne-backend/migrations/versions/027_create_identity_tenant_invitations.py`,
`.claude/plans/phase15-identity-registration-invitation-design.md`.
**لم يُلمس:** `identity/service.py` (`UserService`/`login`/`authenticate`
كما هي بالحرف)، `api/deps.py` (`get_current_tenant` كما هي)، أي دومين
تاني غير `identity` (شامل `affiliate`, `commerce`, `invitations`,
`sovereign_entities`).

---

## [2026-08-12] — Phase 16 (قيد التنفيذ): اكتشافات جانبية في `command`
أثناء التحقق الحي المسبق (Phase 2)، خارج نطاق ثغرة X-Tenant-ID تمامًا

**السياق:** أثناء محاولة التحقق الحي المسبق (قبل تطبيق إصلاح X-Tenant-ID
نفسه) لدومين `command`، ظهرت أخطاء `500` على endpoints أساسية بسبب أباجات
**منفصلة تمامًا عن ثغرة الهيدر**، منعت حتى بدء التحقق الحي. اتلقطت
بالترتيب التالي:

### 1. باجات constructor في `CommandService` — 🟢 اتصلحت (بموافقة صريحة
   كاستثناء مبرَّر، لأنها منعت أي اختبار على الإطلاق)
- `command/service.py` (`__init__`) كان بينشئ `AIAgentsService(db)` و
  `SaaSControlService(db)` بلا `tenant_id` المطلوب في الـconstructor
  الحقيقي لكل منهم → `TypeError` فوري على **كل** endpoint في الدومين
  (18 من 18). `saas_service` تأكَّد إنه dead code (صفر استخدام في
  الملف كله عبر grep). **الحل:** إزالة الاتنين من `__init__`.
- نفس النمط بالظبط في `generate_ai_recommendations`: `AIGovernanceService(self.db)`
  بلا `tenant_id`. **الحل:** `AIGovernanceService(self.db, tenant_id)`
  محليًا (بعد التأكد من التوقيع الحقيقي في `ai_governance/service.py:17`
  و`check_and_consume` سطور 136-146 — لا يقبلوا `tenant_id` كـparameter
  منفصل).
- **باج ثالث من نفس الفئة اتلقط لاحقًا** (`command/service.py:347`):
  الإصلاح الأول شال `self.ai_service` من `__init__` لكن الاستدعاء
  الوحيد ليها (`generate_ai_recommendations`) فضل بيشير لمتغيّر مش
  موجود. **الحل:** `ai_service = AIAgentsService(self.db, tenant_id)`
  محليًا داخل نفس الدالة، بدل `self.ai_service`.

### 2. `GET /command/dashboard` → `ResponseValidationError` — 🔴 موثَّق
   فقط، **لم يُصلَح**، خارج نطاق Phase 16 تمامًا
```
fastapi.exceptions.ResponseValidationError: 1 validation errors:
{'loc': ('response', 'dashboard'), 'msg': 'Input should be a valid dictionary',
 'input': <app.domains.command.models.CommandDashboard object at 0x...>}
```
`command/schemas.py:16` (`DashboardResponse.dashboard: Dict[str, Any]`)
متوقع dict، لكن `command/service.py:126-133` (`get_dashboard`) بيرجّع
كائن ORM خام (`CommandDashboard`) تحت مفتاح `"dashboard"` بلا أي
تحويل. **مؤكَّد إنه باج سابق لأي تعديل في Phase 16**: مسار الكود ده
(`repository.py:19` → `service.py:110-133` → `router.py:22-35`) لم
يُلمس إطلاقًا في هذه الجلسة (التعديلات الوحيدة كانت في `__init__` وفي
`generate_ai_recommendations`، دالتين مختلفتين تمامًا). **الأثر
العملي:** `GET /dashboard` فاشل بـ`500` لأي مستخدم، بغض النظر عن مصدر
`tenant_id` (هيدر أو JWT) — endpoint غير صالح للاستخدام كـ"شاهد وصول
شرعي" في التحقق الحي، اتستبدل بـ`GET /command/brands/me` (endpoint
تينانت-scoped أبسط، `response_model` سليم `BrandSettingsResponse`).

### 3. `agent_id=14` (hardcoded) غير موجود في جدول `ai_agents` —
   🟡 موثَّق، **قيد المناقشة** (قرار seed بيانات اختبار مقابل قرار
   توثيق-بدون-إصلاح، لم يُحسَم بعد وقت كتابة هذا السطر)
```
asyncpg.exceptions.ForeignKeyViolationError: insert or update on table
"agent_usage_logs" violates foreign key constraint
"agent_usage_logs_agent_id_fkey"
DETAIL: Key (agent_id)=(14) is not present in table "ai_agents".
```
`command/service.py:336,348,372` (`generate_ai_recommendations`) بيفترض
وجود AI agent ثابت بـ`id=14` في 3 مواضع مختلفة (`check_and_consume`,
`execute_agent_action`, `create_recommendation`)، بلا أي seed/إنشاء
تلقائي له. في قاعدة البيانات المحلية الحالية (فاضية من بيانات agents
حقيقية) الـid ده مش موجود، فأي استدعاء لـ`generate_ai_recommendations`
بيفشل بـ`ForeignKeyViolationError` — **صفر علاقة بـtenant_id/الهيدر**.

**القرار (لم يُنفَّذ بعد):** لو إنشاء صف اختباري minimal (`INSERT` واحد
بحقول أساسية فقط: `tenant_id`, `owner_id`, `name`, `role`,
`system_prompt` — باقي أعمدة `ai_agents` عندها `default`) هيكفي
لإرضاء الـFK بلا لمس أي منطق KYB/إنشاء agent حقيقي، هيُعمَل كبيانات
اختبار مؤقتة (بادئة `phase16_`، نفس نمط بيانات الاختبار التانية،
تُنضَّف في Phase 5). لو محتاج يلمس workflow حقيقي، هيُوثَّق فقط
كملاحظة "بيانات seed ناقصة لـ`ai_agents` تمنع اختبار حي لـ
`generate_ai_recommendations`" بلا إصلاح.

**الملفات المعدَّلة:** `eppne-backend/app/domains/command/service.py`
(`__init__` + `generate_ai_recommendations`، 3 مواضع).
**الملفات المفحوصة فقط (بدون تعديل):** `eppne-backend/app/domains/
command/{router,repository,schemas}.py`, `eppne-backend/app/domains/
ai_governance/service.py`, `eppne-backend/app/domains/ai_agents/models.py`.

---

## [2026-08-12] — Phase 16 (استثناء نطاق مبرر): إصلاح باج ترانزاكشن في
`ai_governance` — دومين خارج الأربعة الأصليين

**الحالة:** 🟢 **اتصلح، بموافقة صريحة كاستثناء نطاق مبرر — وليس توسيع
اختياري.**

**السبب الصريح للاستثناء:** الباج ده **كان حاجز فعلي قدام التحقق الحي
الإلزامي** لـ`generate_ai_recommendations` (endpoint من ضمن الـ18 في
`command`، أحد الأربعة دومينات الأصلية لـPhase 16) — بدون إصلاحه، كان
مستحيل نثبت حيًا نجاح/فشل الوصول الشرعي مقابل المزوَّر على الـendpoint
ده، رغم إن دومين `ai_governance` نفسه **مش من ضمن نطاق Phase 16
المتفق عليه أصلًا** (الأربعة: `ai_agents`, `sovereign_entities`,
`command`, `saas`).

**الاكتشاف:** أثناء التحقق الحي لـ`generate_ai_recommendations`،
`500` بتراكة:
```
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction
inside context manager.
  ai_governance/service.py:180 → check_and_consume
  ai_governance/repository.py:63 → create_usage_log → self.db.refresh(log)
```
السبب الجذري: `ai_governance/repository.py:59-64` (`create_usage_log`)
كانت بتعمل `await self.db.commit()` مباشرة على الـsession الأساسية
**من جوه** بلوك `async with self.db.begin_nested()` بتاع
`check_and_consume` (`ai_governance/service.py:155-193`). `commit()`
مباشر جوه `begin_nested()` بيقفل الترانزاكشن الخارجي اللي الـSAVEPOINT
معتمد عليه، فبيكسر أي عملية بعده (`refresh(log)` هنا بالظبط). مؤكَّد
إنه مش مرتبط بـ`agent_id=14`/بيانات الـseed: `active_quotas` كانت فاضية
في اختبارنا، فالحلقة اللي بتستدعي `create_or_update_quota`
(سطور 156-178) اتخطّت بالكامل، والباج ظهر مباشرة عند `create_usage_log`
— هيحصل حتى مع quotas كاملة، لأنها مشكلة بنيوية في إدارة الترانزاكشن.

**الإصلاح المطبَّق (سطر واحد فقط):**
```diff
     async def create_usage_log(self, **kwargs) -> AgentUsageLog:
         log = AgentUsageLog(**kwargs)
         self.db.add(log)
-        await self.db.commit()
+        await self.db.flush()
         await self.db.refresh(log)
         return log
```
`flush()` بيكتب الصف جوه نفس الترانزاكشن (قابل للـ`refresh` فورًا) بلا
ما يقفل حاجة؛ الـSAVEPOINT بيتقفل طبيعي لما بلوك `async with` يخلص.
الالتزام النهائي (commit) بيحصل فعليًا بعدين عبر
`command/repository.py:188` (`create_recommendation`، بتتنفذ بعد
`check_and_consume` في نفس الطلب، وعندها `commit()` خاص بيها) — الصف
مش بيضيع.

**نطاق الإصلاح (محدود صراحة، بموافقة المستخدم):** الاستدعاء الوحيد
لـ`create_usage_log` في المشروع كله هو `service.py:180`. **لم تُلمس**
`create_or_update_quota` (`repository.py:20-37`) رغم وجود نفس النمط
بالظبط فيها (`commit()` جوه `begin_nested()` في `service.py:33` و`174`،
دالتين `set_quota` و`check_and_consume`) — غير مفعّلة في مسارنا الحالي
(الحلقة اللي بتستدعيها اتخطّت بالكامل لخلو `active_quotas`)، وسايبينها
كما هي — **قرار صريح بعدم التوسع، حتى لو ظهرت مشاكل جديدة مشابهة.**

**ملاحظة منفصلة موثَّقة (خارج نطاق تمامًا، لم تُفعَّل، لم تُصلَح):**
`ai_governance/service.py:148` بيستدعي
`self.repo.get_usage_log_by_idempotency(idempotency_key)` بـparameter
واحد بس، لكن التوقيع الحقيقي (`repository.py:66`) محتاج `tenant_id`
كـparameter إجباري تاني. ماتفعّلتش في اختبارنا لأن نداء
`command/service.py` لـ`check_and_consume` مبيبعتش `idempotency_key`
(`if idempotency_key:` بترجع `False`)، لكنها كمين `TypeError` جاهز لأي
استدعاء تاني (من أي دومين) بيبعت idempotency key فعلي. **لم تُصلَح —
خارج نطاق الاستثناء المبرَّر أعلاه (مش حاجز قدام مسارنا الحالي).**

**الملفات المعدَّلة:** `eppne-backend/app/domains/ai_governance/repository.py`
(سطر واحد، `create_usage_log`).
**الملفات المفحوصة فقط (بدون تعديل):** `eppne-backend/app/domains/
ai_governance/service.py`، `eppne-backend/app/domains/command/repository.py`.

---

## [2026-08-12] — Phase 16، Phase 2 (تحقق حي قبل الإصلاح): تأكيد حي إضافي
إن ثغرة X-Tenant-ID في `command` **لسه حية بالكامل** (مش دليل على أي حماية)

**السياق:** أثناء محاولة التحقق الحي لـ`generate_ai_recommendations`
(بعد إصلاح باجات constructor/transaction/seed غير المرتبطة بالثغرة)،
ظهر إن الطلب بهيدر `X-Tenant-ID` مزوَّر (`12`) فشل عند
`AIAgentsRepository.get_agent(14, tenant_id=12)` برسالة "الوكيل 14 غير
موجود". **كان لازم تتبُّع دقيق لإثبات مصدر الـ`12` ده قبل اعتباره أي
دليل**، تحديدًا: هل هو `current_user.tenant_id` (المصدر الآمن) ولا لسه
الهيدر الخام؟

**التتبُّع (فك تشفير التوكن المستخدم فعليًا + قراءة كود حي، بدون
افتراض):**
- التوكن المستخدم: `phase16_tenantA_user` (تينانت 1 الحقيقي)، مع هيدر
  مزوَّر `X-Tenant-ID: 12`. فك تشفير الـJWT مباشرة أكَّد:
  `{"sub":"26","tenant_id":1,...}` — `current_user.tenant_id` الحقيقي
  = **1**.
- `command/router.py:272-285` (`generate_recommendations`):
  `tenant_id=cast(int, tenant.id)` بيتبعت للـservice — و`tenant` جايه
  من `Depends(get_current_tenant)`، **مش من `current_user`** (رغم إن
  `current_user` متاح في نفس الـendpoint، `tenant_id` بتاعه غير
  مُستخدَم إطلاقًا في تحديد نطاق العملية).
- `api/deps.py:148-153` (`get_current_tenant`): بترجّع قيمة هيدر
  `X-Tenant-ID` مباشرة (`default=1`)، **صفر تحقق أو ربط بـ`current_user`**.
- تأكَّد (`grep` حي): `command/router.py` **لسه فيها 18 استخدام لـ
  `Depends(get_current_tenant)` بلا أي تعديل** — الملف ده لم يُلمس
  إطلاقًا طول الجلسة (كل الإصلاحات كانت في `service.py`/
  `ai_governance/repository.py`، مش `router.py`).

**الاستنتاج الصحيح (مصحَّح — الاستنتاج الأول كان غير دقيق):**
`tenant_id=12` اللي وصل لـ`get_agent` **مش تسريب في مسار جديد أو منفصل
— دي نفس الثغرة الأصلية الموثَّقة، لسه حية بالكامل**، لأن إصلاح Phase 3
(استبدال `Depends(get_current_tenant)` بـ`current_user.tenant_id` في
الـ18 endpoint) **لم يُطبَّق على `command/router.py` لحد الآن**. رفض
`get_agent` للطلب المزوَّر (٪"الوكيل غير موجود") **كان صدفة بيانات
اختبار** (الوكيل `id=14` مزروع لتينانت 1 بس، مش موجود لتينانت 12)،
**وليس حماية حقيقية على مستوى التطبيق**. لو المهاجم زوَّر الهيدر
لتينانت عنده بيانات AI حقيقية مزروعة، كان الكود هيكمل وينفّذ فعليًا
تحت هوية التينانت الضحية — **الثغرة لسه قابلة للاستغلال الكامل في
`command` حتى وقت كتابة هذا السطر**.

**الخلاصة الصريحة لحالة التحقق الحي لـ`generate_ai_recommendations`:**
1. **آلية عزل التينانت عبر `current_user.tenant_id` — لم تُختبَر بعد،
   لأنها لم تُطبَّق بعد** (فرق مهم عن "مؤكَّدة تعمل"). الفحص الحي الوحيد
   اللي اتنفَّذ لحد الآن أثبت العكس: الثغرة الأصلية (الهيدر) لسه المصدر
   الفعلي الوحيد لـ`tenant_id` في هذا المسار بالكامل.
2. **الـbaseline الناجح كاملًا (end-to-end لغاية نتيجة AI حقيقية) محجوب
   حاليًا بباج غير مرتبط تمامًا** (`RedisClientWrapper.hincrbyfloat` —
   موثَّق منفصل تحت هذا القسم).
3. **لا يمكن اعتبار التحقق الحي لهذا الـendpoint "مكتمل" بأي درجة قبل
   تطبيق إصلاح Phase 3 على `command/router.py` وإعادة الاختبار من
   الصفر.**

### باج منفصل تمامًا (موثَّق فقط، لم يُحقَّق فيه أعمق، خارج نطاق X-Tenant-ID)
أثناء نفس الاختبار (بعد إصلاح مشاكل الـagent seed)، الطلب الشرعي (تينانت
1 الحقيقي) عدّى فحص وجود الوكيل بنجاح، ودخل فعليًا لمنطق
`ai_engine.generate(...)` (`ai_agents/service.py:193-202`) — لكن فشل
بخطأ في subsystem مختلف تمامًا:
```
AI execution failed for agent 14: فشل جميع النماذج:
'RedisClientWrapper' object has no attribute 'hincrbyfloat'
```
على الأرجح مرتبط بتكامل AI engine مع Redis (تتبُّع تكلفة/استهلاك عبر
`hincrbyfloat`)، ومحتمل مرتبط بكون `GEMINI_API_KEY` غير مضبوط في بيئة
التطوير هذه ("AI features will be disabled" — تحذير من أول تشغيل
`uvicorn`). **لم يُحقَّق فيه أعمق بقرار صريح من المستخدم** — خارج نطاق
Phase 16 بالكامل (subsystem مختلف: `app/services/ai/`/
`core/redis_client.py`، صفر علاقة بـX-Tenant-ID أو بالأربعة دومينات).

**الملفات المفحوصة فقط (بدون تعديل):** `eppne-backend/app/domains/
command/router.py`, `eppne-backend/app/api/deps.py`,
`eppne-backend/app/domains/ai_agents/service.py`.

---

## [2026-08-12] — Phase 16 (جزئي، متوقَّف مؤقتًا عند نقطة نظيفة): إصلاح
X-Tenant-ID في `command` فقط، والباقي مؤجَّل

**الحالة:** 🟡 **جزئي — دومين واحد من الأربعة مكتمل ومؤكَّد حيًا
بالكامل، والثلاثة الباقيين لم يُلمَسوا إطلاقًا.** تم إيقاف الجلسة عند
نقطة توقف نظيفة بقرار صريح من المستخدم، بعد اكتشاف مشكلة بنيوية أعمق
تحتاج جلسة مخصصة منفصلة (تفصيل في القسم الحرج تحت).

### 1. `command` — ✅ مكتمل ومؤكَّد حيًا
إصلاح ثغرة X-Tenant-ID الفعلي (استبدال `Depends(get_current_tenant)`
بـ`current_user.tenant_id`) اتطبَّق على كل الـ18 endpoint في
`eppne-backend/app/domains/command/router.py` (+ حذف استيراد
`get_current_tenant`/`AcademyTenant`). تأكيد مزدوج: (أ) `grep` مستقل
بعد التطبيق أثبت صفر استخدام متبقٍّ للهيدر أو `AcademyTenant` في
الملف، (ب) تحقق حي حاسم بعد إعادة تشغيل `uvicorn` من الصفر — 6 طلبات
حقيقية (توكنين مختلفين × هيدر حقيقي/مزوَّر/عشوائي) أثبتت إن نتيجة
`GET /command/brands/me` **متطابقة بالحرف بغض النظر عن قيمة الهيدر**،
في الاتجاهين (تينانت A وB)، مع طلب تحكم بلا توكن أثبت الفرق بين `401`
(مصادقة) و`404` (منطق تطبيق طبيعي). تفاصيل الطلبات والنتائج كاملة في
`.claude/reports/phase16-session-log.md`.

### 2. باجات جانبية اتصلحت في `command` (خارج نطاق X-Tenant-ID، ضرورية
لفتح الطريق أمام التحقق الحي)
- `command/service.py.__init__`: إزالة `AIAgentsService(db)` و
  `SaaSControlService(db)` (كانا بينشئوا بلا `tenant_id` إجباري →
  `TypeError` على كل الـ18 endpoint).
- `generate_ai_recommendations`: `AIGovernanceService(self.db)` →
  `AIGovernanceService(self.db, tenant_id)`.
- نفس الدالة: `self.ai_service.execute_agent_action` (متغيّر مش
  موجود) → `ai_service = AIAgentsService(self.db, tenant_id)` محليًا.
- نفس الدالة: حذف `tenant_id=tenant_id` (kwarg زيادة مرفوضة من توقيع
  `execute_agent_action` الحقيقي).
- بيانات seed اختبارية (`ai_agents id=14`): استكمال `is_deleted=false`،
  `status='ACTIVE'` (كانوا `NULL` بسبب `INSERT` خام تخطّى الـORM
  defaults) — بيانات اختبار مؤقتة، اتشالت بالكامل في التنظيف.

### 3. باج ترانزاكشن في `ai_governance` — ✅ اتصلح، **استثناء نطاق
مبرَّر صراحة** (مش جزء من خطة Phase 16 الأصلية)
`ai_governance/repository.py:62` (`create_usage_log`): `commit()` →
`flush()`. **السبب المُبرِّر:** كان حاجز فعلي قدام التحقق الحي
الإلزامي لـ`generate_ai_recommendations` (endpoint من ضمن الـ18 في
`command`) — مش توسيع نطاق اختياري، بل إزالة عائق كان بيمنع تنفيذ
الالتزام الأصلي لـPhase 16 بالكامل. تفاصيل السبب الجذري والديف كاملة
في القسم أعلاه بتاريخ [2026-08-12] "Phase 16 (استثناء نطاق مبرر)".

### 4. باجات موثَّقة فقط، **بدون إصلاح**، خارج نطاق Phase 16 تمامًا
- **`GET /command/dashboard`** → `ResponseValidationError` (`schemas.py`
  يتوقع dict، `service.py` بيرجّع كائن ORM خام). سابق لأي تعديل في
  الجلسة دي.
- **`ai_governance/service.py:148`** → `get_usage_log_by_idempotency`
  بيتنادى بـparameter ناقص (`tenant_id`). غير مفعّل في أي مسار
  اختبرناه، لم يُصلَح.
- **`RedisClientWrapper.hincrbyfloat`** (مفقودة) → بتمنع
  `ai_agents/service.py::execute_agent_action` من الاكتمال حتى لتينانت
  شرعي 100%، محتمل مرتبط بـ`GEMINI_API_KEY` غير مضبوط في بيئة
  التطوير. لم يُحقَّق فيه أعمق.

---

## 🔴 [2026-08-12] — اكتشاف حرج: نمط منهجي لباج ترانزاكشن (`commit()`
داخل `begin_nested()`) عبر repositories متعددة — **يحتاج جلسة مخصصة
منفصلة وعاجلة قبل استكمال Phase 16**

**هذا القسم منفصل عمدًا عن ملاحظات Phase 16 أعلاه — الأثر يتجاوز
الأربعة دومينات المستهدفة ويمس كود مالي حقيقي.**

### الاكتشاف
أثناء فحص استباقي (`ai_agents`, `sovereign_entities`, `saas` قبل بدء
أي تعديل فيهم)، اتأكَّد إن نفس نمط باج `ai_governance` (قسم 3 أعلاه)
**مش معزول — ده نمط منهجي في طبقة الـrepository بمعظم المشروع تقريبًا**:
كل `repo` method بتعمل `self.db.commit()` فوري بعد أي كتابة، وده بينكسر
فورًا أي وقت بيتنادى من جوه `async with self.db.begin_nested()` (تظهر
كـ`sqlalchemy.exc.InvalidRequestError: Can't operate on closed
transaction inside context manager`).

**مواضع مؤكَّدة بقراءة كود حية (read-only، صفر تعديل):**
- `ai_agents/service.py:289` (`resolve_approval`) →
  `ai_agents/repository.py:181-198` (`resolve_approval`، `commit()`
  سطر 197).
- `sovereign_entities/service.py:364` (`deposit_to_entity_wallet`) و
  `:429` (`transfer_from_entity`) →
  `sovereign_entities/repository.py:97-107` (`update_entity`،
  `commit()` سطر 103).
- `saas/service.py:109` (`create_subscription`) →
  `saas/repository.py:180-185` (`commit()` سطر 183).
- `saas/service.py:159` (`process_auto_renewals`) →
  `saas/repository.py:187-202` (`update_subscription`) و`336-341`
  (`create_invoice`) — باجين منفصلين.
- `saas/service.py:296` (`pay_invoice`) →
  `saas/repository.py:343-356` (`update_invoice`، `commit()` سطر 349)
  — **الأخطر ماليًا، معاملة دفع فعلية**.
- **الأعمق: `finance/service.py:92` (`FinanceService.transfer` —
  دالة تحريك الأموال الفعلية المستخدَمة من `pay_invoice` وعدة دومينات
  أخرى) عندها نفس الباج جوه نفسها، مستقلة تمامًا**: `finance/
  repository.py:48-57` (`WalletRepository.update_balances`، `commit()`
  سطر 52) و`74-79` (`TransactionRepository.create`، `commit()` سطر 77)
  — يعني `finance.transfer()` بتنهار من جوه نفسها بمعزل عن أي
  `begin_nested()` خارجي.

### لماذا `command` نجا من نفس المصير
`command` عنده نفس النمط في `ai_governance` بس (قسم 3 أعلاه، سطر واحد،
مكان واحد) — بالصدفة كان أصغر مدى بكتير من باقي الدومينات، فأمكن حله
باستثناء نطاق مصغَّر. الثلاثة الباقيين (`ai_agents`, `sovereign_entities`,
`saas`) + `finance` المشتركة بينهم **فيهم 6-8 مواضع منفصلة على الأقل**
— نطاق مختلف تمامًا في الحجم، يمس دومينات خارج الأربعة الأصليين
(`finance` مستخدَمة في `invoicing`, `commerce`, وغيرهم).

### القرار
**لم يُصلَح أي من المواضع دي في هذه الجلسة.** Phase 16 اتوقَّف مؤقتًا
عند نقطة نظيفة (`command` مكتمل ومؤكَّد) لحد ما يُتخَذ قرار صريح في
جلسة منفصلة مخصصة لهذا الاكتشاف — تحديدًا بخصوص: (أ) نطاق الإصلاح
(المواضع الستة بس، أم `finance/repository.py` كمان؟)، (ب) الأولوية
(`saas.pay_invoice`/`finance.transfer` أولًا، بما إنهم الأخطر ماليًا؟)،
(ج) هل ده يستأهل مراجعة معمارية أشمل لطبقة الـrepository بالكامل
(نمط `commit()` الفوري) بدل تصحيحات نقطية متفرقة.

**الملفات المفحوصة فقط (بدون أي تعديل):**
`eppne-backend/app/domains/{ai_agents,sovereign_entities,saas,finance}/
{service,repository}.py`.

---

## [2026-08-12] — تنظيف نهائي لبيانات Phase 16 التجريبية + تحقُّق مستقل

**التنظيف المنفَّذ (بالترتيب الآمن حسب الـFK):**
1. `DELETE FROM agent_usage_logs WHERE agent_id = 14` → 2 صف.
2. `DELETE FROM ai_task_logs WHERE agent_id = 14` → 2 صف.
3. `DELETE FROM ai_agents WHERE id = 14` → 1 صف.
4. **اكتشاف جانبي أثناء التنظيف:** `DELETE FROM users WHERE id IN
   (26,27,28)` فشل أول مرة بـ`FK violation` — صف يتيم في
   `command_dashboards` (id=1, **tenant_id=1 الحقيقي**, `created_by=27`)
   اتخلق كأثر جانبي لاختبار `get_dashboard` في وقت سابق من الجلسة (قبل
   ما نكتشف باج `ResponseValidationError` بتاعه — الكود بينشئ dashboard
   تلقائي لو مش موجود، قبل ما يفشل في الـserialization). اتحذف تحديدًا
   (`DELETE FROM command_dashboards WHERE id=1 AND created_by=27`) —
   حذف دقيق لصف واحد ملوَّث بس، صفر لمس لباقي بيانات تينانت 1 الحقيقية.
5. `DELETE FROM users WHERE id IN (26,27,28)` (أعيد التنفيذ بنجاح) →
   3 صف.
6. `DELETE FROM academy_tenants WHERE id = 12` → 1 صف.

**التحقق المستقل بعد التنظيف (7 استعلامات SELECT منفصلة):** `users`
(26/27/28)، `academy_tenants` (12)، `ai_agents` (14)، `agent_usage_logs`
(agent_id=14)، `ai_task_logs` (agent_id=14)،
`command_dashboards` (created_by IN 26/27/28)،
`command_ai_recommendations` (ai_agent_id=14) — **كل السبعة رجّعوا صفر
صف**. فحص أساسي إضافي: `academy_tenants=1, users=7, ai_agents=0` —
**مطابق تمامًا لقيم بداية الجلسة**. سيرفر `uvicorn` التجريبي اتوقف.

---

## 🔴 [2026-08-13] — اكتشاف حرج: 1846 سطر خطأ `tsc --noEmit` عبر 40+
دومين (أكتر بكثير من الحد الأدنى 20)، اكتُشف أثناء التحقق من تعديل بسيط
(10 لينكات معطوبة) في الأكاديمية — **غير مرتبط بشغلنا إطلاقًا** (مؤكَّد
بعزل حي عبر `git stash`)، وخارج نطاق UI/UX بالكامل

**هذا القسم منفصل عمدًا عن أي شغل UI/UX سابق — الأثر هنا على مستوى
عقد الأنواع (type contracts) بين الفرونت والباك إند عبر عشرات
الدومينات، مش تصميم واجهة.**

### تقرير تشخيصي بحت. صفر إصلاح. صفر تعديل كود.
لم يُعدَّل أي ملف كود لإصلاح أي خطأ من الأخطاء الموصوفة تحت. الفحص
بالكامل قراءة/تشغيل أدوات تشخيص (`tsc --noEmit`) و`git stash`/`git
stash pop` مؤقت وقابل للعكس بالكامل — تفاصيله في القسم الأخير تحت.

### السياق
أثناء تدقيق أكاديمية محدود النطاق (`academy-audit.txt`)، اتأكَّد وجود
10 روابط معطوبة (`/academy/classroom/...`) في 5 ملفات — مسار غير موجود
فعليًا كـroute على القرص (`Glob` لـ`app/**/classroom/**` رجّع صفر
نتيجة)، بينما الصفحة الحقيقية هي
`app/(dashboard)/academy/[id]/learn/page.tsx`:
- `components/academy/CourseActionButton.tsx` (4 مواضع)
- `app/(dashboard)/academy/[id]/page.tsx` (2 موضع)
- `app/(dashboard)/academy/my-learning/page.tsx` (موضع واحد)
- `app/(dashboard)/academy/instructor/dashboard/page.tsx` (موضع واحد)
- `app/(dashboard)/academy/certificates/[courseId]/page.tsx` (موضع واحد)

التعديل المطبَّق كان تصحيح نصي بحت لقيمة المسار في الـ10 مواضع دي بس
(`git diff --stat`: 5 ملفات، 9 إضافة + 9 حذف = 18 سطر diff لـ10 استبدال
نصي). أثناء التحقق الإلزامي بـ`tsc --noEmit` بعد التعديل، ظهر عدد ضخم
من الأخطاء غير متوقَّع لتعديل بهذا الحجم — استوجب عزل السبب قبل اعتماد
التعديل.

### الاكتشاف: 1846 سطر خطأ TypeScript، منتشرة عبر 40+ دومين
ناتج `node node_modules/typescript/bin/tsc --noEmit 2>&1 | wc -l`
(موثَّق كامل في `link-fix-verification.txt`، 1872 سطر ملف شاملًا رأس
`git diff --stat`) = **1846 سطر خطأ**. من ضمنها 1268 كود خطأ مستقل
(`error TS####`)، وباقي الأسطر شروحات نوع متداخلة لنفس الأخطاء (زي خطأ
`Variants` في `app/(auth)/login/page.tsx:40` اللي وحده بياخد 8 أسطر).

**عيّنة موثَّقة (file:line) من `link-fix-verification.txt` تثبت الاتساع
عبر دومينات لا علاقة لها بالأكاديمية إطلاقًا:**
- `app/(auth)/login/page.tsx(40,9)` / `register/page.tsx(39,19)` —
  `error TS2322` على `Variants` (framer-motion)، سابق لأي تعديل أكاديمية.
- `components/realestate/InvestorPortfolio.tsx` — 19 خطأ.
- `components/automation/NodeSettingsPanel.tsx` — 10 أخطاء.
- `components/health/AIPrognosisRadar.tsx` — 9 أخطاء.
- `hooks/useFleets.ts(3,21)` / `hooks/useHubs.ts(3,10)` —
  `error TS2305`: أعضاء غير مُصدَّرة من `@/services/transport`.
- `hooks/zamakana/useCampaigns.ts(3,10)` — نفس الشكل من
  `@/services/zamakana`.
- `store/agentStore.ts(3,27)` / `store/digitalTwinStore.ts(3,30)` —
  أنواع غير مُصدَّرة من `ai-agents.service`/`digital-twin.service`.

**بحث منهجي على كل المسارات الفريدة تحت `components/` و`hooks/` في
`link-fix-verification.txt` رجّع 30 دومين فريد تحت `components/` +
20 دومين فريد تحت `hooks/` (باتحاد الاتنين 40+ دومين فريد شاملين:**
`ai-agents, ai-governance, arbitration-syndicates, automation,
brand-builder, command, commerce, communications, digital-twin,
employment, entities, finance, health, insurance, invitations, iot,
logistics, manufacturing, marketplace, privacy, projects, realestate,
saas, social, sovereign-entities, tenders-auctions, tourism-sports,
translation, zamakana, affiliate, agritech, transport` **وغيرهم — أكتر
بكثير من الـ20 دومين كحد أدنى.**

**مثال مباشر يتقاطع مع تعديلنا نفسه (مش سببه):**
`app/(dashboard)/academy/[id]/learn/page.tsx(278,35)`،
`(284,69)`، `(307,38)` — ثلاثة أخطاء `error TS2339` على
`AcademyService.getQuizByNode`/`submitQuiz`/`joinLiveSession` غير
موجودة إطلاقًا كـmethods حقيقية في `services/academy.service.ts`
(تحقُّق منفصل مؤكَّد بقراءة كود كاملة للملف، 816 سطر، صفر مطابقة اسم —
تفاصيل كاملة في `learn-page-service-check.txt`). هذا خطأ حقيقي **سابق
للتعديل**، اكتُشف بالصدفة أثناء نفس الفحص، مش ناتج عنه.

### التحقق الحاسم: عزل حي عبر `git stash` — الرقم قبل وبعد تعديلاتنا
**متطابق تمامًا (1846 = 1846)**
تفاصيل الأوامر والنواتج الكاملة موثَّقة في `stash-verification.txt`.
بالترتيب:
1. `git stash push -m "temp-link-fix-verification" -- <الملفات الخمسة
   بالاسم بس>` (مقصور عمدًا، مش `stash` عام، عشان منلمسش تعديلات
   `eppne-backend` اللي مش بتاعتنا وشغالة عليها جلسة تانية بالتوازي على
   نفس الريبو) → نجح بلا أي conflict.
2. `tsc --noEmit` **بدون** تعديلاتنا (بعد الـstash push) →
   **1846 سطر خطأ**.
3. `git stash pop` → نجح بلا أي conflict.
4. `tsc --noEmit` **مع** تعديلاتنا (بعد الـstash pop) →
   **1846 سطر خطأ**.
5. مقارنة: **1846 = 1846 بالحرف** — فرق = صفر. تعديل نصي داخل
   template literal (قيمة مسار URL) لا يمكن رياضيًا أن يُنتج أو يُزيل
   أي خطأ TypeScript متعلق بالأنواع، والتحقق الحي أثبت هذا عمليًا مش
   افتراضيًا فقط.
6. تأكيد ختامي بـ`git status`: الملفات الخمسة الأصلية ظهرت زي ما هي
   بالضبط تحت "Changes not staged for commit" بعد الـpop، وملفات
   `eppne-backend` (مش بتاعتنا) فضلت في نفس حالتها طول الوقت.

### الخلاصة
الـ1846 سطر خطأ (40+ دومين) موجودين أصلًا في الكود **بشكل مستقل تمامًا
عن أي تعديل قمنا بيه** — أثبتناها بعزل حي (`git stash`)، مش بقراءة كود
فقط. الطبيعة بالكامل type-level (`tsc --noEmit`: أعضاء غير مُصدَّرة،
methods غير موجودة، عدم توافق أنواع بين الفرونت والباك إند) — **صفر
علاقة بـUI/UX** (ألوان، تخطيط، مكوّنات بصرية، تجربة استخدام). التعديل
العشري (10 لينكات) اللي كنا بنتحقق منه **سليم ومعزول بالكامل**، ومفيش
أي داعٍ لربطه بأي من الأخطاء دي.

### القرار
**لم يُصلَح أي من الأخطاء الـ1846 في هذه الجلسة ولا أي جلسة سابقة.**
هذا اكتشاف تشخيصي بحت لحجم مشكلة تتجاوز نطاق أي تعديل UI/UX بمراحل —
يحتاج قرار صريح في جلسة/جلسات منفصلة مخصصة (على غرار
`.claude/plans/critical-finding-xtenant-systemic.md`) بخصوص الأولوية
والنطاق قبل أي محاولة إصلاح.

**الملفات المرجعية الكاملة (كلها قراءة/تشخيص فقط، صفر تعديل كود):**
`academy-audit.txt`، `link-fix-verification.txt`،
`stash-verification.txt`، `learn-page-service-check.txt`.

### قرار الباك اند بخصوص `learn/page.tsx` ونطاق التنظيف البصري المتبقي
بناءً على الاكتشاف أعلاه (`getQuizByNode`/`submitQuiz`/`joinLiveSession`
غير موجودين كـmethods حقيقية في `services/academy.service.ts`)، جاء
قرار صريح من فريق الباك اند: **`app/(dashboard)/academy/[id]/learn/page.tsx`
موقوف بالكامل** عن أي تعديل — بصري أو غيره — لحد ما الباك اند يضيف
الثلاث methods دي فعليًا لطبقة الـservice. ده **خارج نطاقنا تمامًا**
(مش مسؤولية فرونت/UI). بالتوازي، تم فحص قراءة فقط لباقي ملفات الأكاديمية
(موثَّق كامل في `blocked-files-list.txt`) للتأكد من عدم وجود اعتماد
مباشر أو غير مباشر (عبر أي مكوّن مشترك في `components/academy/`) على
الثلاث methods دي في أي ملف تاني. النتيجة: `learn/page.tsx` هو الملف
الوحيد المتأثر، وباقي ملفات الأكاديمية (26 صفحة + 4 مكوّنات مشتركة)
**آمنة ومسموح يكمل عليها التنظيف البصري البحت** بشرط الالتزام بنفس
الشرط (عدم إضافة أي اعتماد جديد على الثلاث methods دي أثناء التنظيف).

---

## [2026-08-13] — إصلاح باج ترانزاكشن منهجي (`commit()` جوه `begin_nested()`) عبر 24 دومين — حالة التحقق النهائية

**الحالة:** 🟡 جزئي — الكود مُصلَح بالكامل عبر كل الـ24 دومين، **لكن التحقق الحي (DB-level) اتأكَّد فعليًا لـ3 دومين بس من أصل 24**. التفاصيل الكاملة (كل ديف، كل تحقق، كل محاولة) في `.claude/reports/transaction-savepoint-bug-session-log.md`.

**المشكلة الأصلية:** عشرات الـrepository methods عبر المشروع كانت بتعمل `self.db.commit()` مباشر وهي متنادية من جوه `async with self.db.begin_nested()` — ده بيقفل الترانزاكشن اللي الـSAVEPOINT معتمد عليه. **الإصلاح:** `commit()` → `flush()` في الـrepo، + إضافة `commit()` صريح واحد في الـservice بعد ما بلوك `begin_nested()` يقفل (مش قبله) — طُبِّق على 89 موضع عبر 24 دومين + `finance/repository.py` (أصل الانتشار، بيتغطى منها 18 موضع تبعية تلقائيًا عبر `finance.transfer`).

### ✅ 1) الدومينات المؤكَّدة حيًا بالكامل (طلب HTTP فعلي + `SELECT` مستقل قبل/بعد) — 3 بس

`finance` (`transfer` ×2 متتاليين + `swap`، تحويلات مالية حقيقية بأرقام دقيقة اتأكَّدت بالـDB)، `ai_agents` (`resolve_approval`)، `ai_governance` (`set_quota`, `update_rate_limits`, `check_and_consume`, `reset_quotas`).

**⚠️ ملاحظة تحذيرية جوهرية (تستاهل تُقرأ في أي جلسة مستقبلية مشابهة):** أول محاولة تحقق لـ`ai_agents.resolve_approval` و`ai_governance.reset_agent_quotas` (قبل إضافة الـcommit الصريح في الـservice) رجعت **نجاح كاذب** — `status 200/204` بلا أي خطأ ظاهر، لكن الـDB مكنش بيتغيّر خالص (rollback صامت عند إغلاق الـsession، لأن `get_db()` صفر auto-commit). **الدرس المستفاد الدائم: نجاح status code + عدم وجود Traceback ≠ نجاح فعلي — أي تعديل بيمس حدود الترانزاكشن لازم تحقق DB-level إجباري، من غير استثناء.**

### 🟡 2) باقي الـ21 دومين — الكود مُصلَح ومُراجَع، **غير مُختبَر حيًا**

من ضمنهم **6 دومين اتراجعت بتفصيل before/after كامل لكل method اتعملها إعادة هيكلة** (تحريك `return` من جوه بلوك `begin_nested` لبرّه)، وتمت **الموافقة الصريحة** على كل واحدة بعد تحليل دقيق (هل فيه شرط بين آخر كتابة والـ`return`؟ هل بيغيّر مسار الخروج ولا مجرد branching على بيانات؟):
`health` (5 methods)، `insurance` (3)، `logistics` (1)، `projects` (2)، `realestate` (2)، `service_marketplace` (2) + `saas.pay_invoice` (1، ميثود واحدة ضمن دومين كان المفروض قابل للتحقق الحي لكن اتحجب — التفاصيل تحت).

**باقي الـ15 دومين** (`digital_twin`, `employment`, `invitations`, `manufacturing`, `social`, `tourism_sports`, `transport`, `communications`, `zamakana`, `agritech`, `academy`, `commerce`, `saas`, `sovereign_entities`, `affiliate`, `privacy`) اتصلحوا ميكانيكيًا بنفس القاعدة (تأكَّدت بـ`grep`/`py_compile` مستقل)، لكن صفر تحقق حي — الأسباب مفصَّلة في القسمين التاليين.

**الحالة الرسمية لكل الـ21 دومين دول: "مُصلَح كود + مُراجَع بالكامل، غير مُختبَر حيًا"** — مش "مُصلَح ومؤكَّد" زي الـ3 الأوائل. أي جلسة مستقبلية تعتمد عليهم لازم تعتبرهم كده بالظبط، مش أكتر.

---

### 🔴🔴 3) اكتشاف نطاق ثانٍ — باج `SimpleTenant`/type mismatch (منفصل تمامًا عن باج الترانزاكشن، يستاهل جلسة ثالثة قريبًا)

أثناء محاولة التحقق الحي، اتكشف إن `api/deps.py`'s `get_current_tenant()` بترجع كائن `SimpleTenant` (فيه `.id`)، مش `int` خام. **`finance/router.py` كانت بتعاني من نفس الباج ده بالظبط، واتصلحت في نفس الجلسة دي** (استبدال `get_current_tenant` بـ`current_user.tenant_id` في الـ8 endpoints، مؤكَّد حيًا). **لكن نفس الباج لسه حي بدون إصلاح في دومينات تانية كتير:**

| الدومين | الدليل | التأثير |
|---|---|---|
| `academy` | `router.py` — **36 استخدام** لـ`tenant_id: int = Depends(get_current_tenant)`، بيتبعت مباشرة لـ`AcademyService(db, tenant_id)` | أي endpoint بيلمس DB بيكراش (`DataError: SimpleTenant object cannot be interpreted as an integer`) |
| `commerce` | نفس النمط بالحرف — **12 استخدام**، `CommerceService(db, tenant_id)` | نفس الكراش |
| `saas` | نفس النمط بالحرف — **17 استخدام**، `SaaSControlService(db, tenant_id)` | نفس الكراش |
| `sovereign_entities` | نفس النمط، مؤكَّد حيًا بمحاولة فعلية (`deposit_to_entity_wallet` كراشت بنفس الخطأ بالظبط) | نفس الكراش |

**التصنيف:** فئة مختلفة تمامًا عن باج الترانزاكشن — نفس عائلة الباج الموثَّق في `.claude/plans/critical-finding-xtenant-systemic.md` (ثقة هيدر `X-Tenant-ID`)، لكن **طبقة تقنية أعمق** (type mismatch بعد إدخال `SimpleTenant`، مش بس مصدر الثقة). **صفر إصلاح تم عليه في هذه الجلسة** (بتوجيه صريح من المستخدم: "لا تفتح أي باج جديد"). **يستاهل جلسة ثالثة مخصَّصة قريبًا** — النطاق غير معروف بالكامل لسه (الأربعة دومين دول اتكشفوا بالصدفة أثناء محاولات تحقق حي لباج تاني، مش من جرد منهجي شامل — ممكن يكون فيه دومينات تانية متأثرة لم تُكتشف بعد).

---

### 🟠 4) باجات متفرقة إضافية (كل واحدة فئة مختلفة، صفر إصلاح، موثَّقة فقط)

| الدومين | الباج | الفئة |
|---|---|---|
| `communications` | `_get_user_tenant` → `self.user_repo.get_user(user_id)` — method غير موجودة (الصح `get_by_id`) | method غير موجودة، بيكسر `send_notification`/`send_mail` بالكامل |
| `zamakana` | `ZamakanaService.__init__` بينشئ `AIAgentsService(db)` بمعامل واحد بدل اتنين (`tenant_id` ناقص) | فئة constructor (نفس عائلة `FinanceService(db)`، لكن لـ`AIAgentsService`) |
| `agritech` | **صفر ملف `router.py`** في `app/domains/agritech/` من الأساس — الكود موجود (`service.py`/`repository.py`) لكن **غير معروض بأي endpoint إطلاقًا** | endpoint غير موجود من الأساس (موثَّق سابقًا في `critical-finding-xtenant-systemic.md`) |
| `sovereign_entities` | `create_entity` (router) → `repository.create_entity()` بترمي `TypeError: got multiple values for keyword argument 'tenant_id'` | باج تمرير معاملات مكرر |
| `privacy` | `is_privacy_officer(admin_id)` بتتنادى بمعامل `int` (الـuser id)، لكن الدالة الحقيقية (`core/security.py`) بتتوقع كائن `User` كامل وبتقرا `user.system_role` منه — تمرير `int` بيخلي الفحص يرجع `False` دايمًا، فبيرفض أي حد (حتى `SUPER_ADMIN`) بشكل غير مشروط | باج تمرير نوع بيانات غلط (type mismatch مختلف عن `SimpleTenant`) |
| `affiliate` | صفر باج — لكن `withdraw_commissions`/`bulk_release_commissions` بتحتاج صف `Commission` موجود، وموديله فيه FK إجبارية (`order_id`, `order_item_id`, `product_id`) لجداول `commerce` (نفسها محجوبة بباج `SimpleTenant` فوق) | تعقيد بيانات اختبار، مش باج كود |

**كل الباجات في القسمين 3 و4 موجودة مسبقًا في الكود، سابقة لأي تعديل بتاعنا في هذه الجلسة، ومن فئات مختلفة تمامًا عن `commit()` جوه `begin_nested()`. صفر إصلاح تم عليها — موثَّقة فقط بتوجيه صريح من المستخدم.**

---

## 🔴🔴🔴 [2026-08-13] — اكتشاف حرج جديد: تسريب بيانات مالية/KYB **بلا أي مصادقة إطلاقًا** في `sovereign_entities` (أخطر من كل باجات `SimpleTenant` المكتشفة في الجلسات الثلاث السابقة، صفر إصلاح، بانتظار توجيه)

**السياق:** اكتُشف أثناء جرد `sovereign_entities/router.py` في جلسة إصلاح `SimpleTenant` (`.claude/reports/simpletenant-fix-session-log.md`). **هذا ليس امتدادًا لباج `SimpleTenant`** — فئة مختلفة تمامًا وأخطر: مش "type mismatch يسبب كراش"، ده **تسريب بيانات فعلي وقابل للاستغلال الآن، بلا حتى الحاجة لتوكن JWT صالح** (كل باجات الجلسات التلاتة السابقة، حتى الأخطر منها، كانت محتاجة توكن مستخدم حقيقي زائف الهيدر — هنا مفيش حتى الحد الأدنى ده).

### الأربعة endpoints المتأثرة (`sovereign_entities/router.py`)

| # | Endpoint | السطر | التوقيع الكامل |
|---|---|---|---|
| 1 | `GET /sovereign-entities/` (`list_entities`) | 41-48 | **بلا أي `Depends` مصادقة إطلاقًا** — بارامتراتها كلها `Query`/`Depends(get_current_tenant)`/`Depends(get_db)` بس |
| 2 | `GET /sovereign-entities/{entity_id}` (`get_entity`) | 73-77 | نفس الشيء — **بلا مصادقة** |
| 3 | `GET /sovereign-entities/templates` (`list_templates`) | 340-343 | نفس الشيء — **بلا مصادقة** |
| 4 | `GET /sovereign-entities/components` (`list_components`) | 350-353 | نفس الشيء — **بلا مصادقة** |

### التأكيد الدقيق (قراءة كود مباشرة، `router.py` → `service.py` → `repository.py`، الثلاث طبقات)

**الاستعلامات نفسها *مفلترة* بـ`tenant_id` على مستوى SQL (مش "بترجع الجدول كامل بلا حدود") — لكن مصدر الـ`tenant_id` ده هو الهيدر `X-Tenant-ID` **بلا أي تحقق مصادقة على الإطلاق**، لأن الـ4 دوال دي **مفيهاش `current_user` في توقيعها من الأساس** (لا إجباري ولا حتى Optional):

```python
# router.py:41-48 — list_entities: صفر current_user
async def list_entities(
    entity_type: Optional[SovereignEntityType] = None,
    kyb_status: Optional[KYBStatus] = None,
    skip: int = 0, limit: int = 50,
    tenant_id: int = Depends(get_current_tenant),   # ← الهيدر مباشرة، صفر مصادقة
    db: AsyncSession = Depends(get_db)
):
```

```python
# repository.py:63-76 — list_entities: فلترة SQL حقيقية، لكن بـtenant_id غير موثوق
query = select(SovereignEntity).where(
    and_(SovereignEntity.tenant_id == tenant_id, SovereignEntity.is_deleted == False)
)
```
نفس النمط بالحرف في `get_entity` (`repository.py:26-36`)، `list_templates` (`:283-285`)، `list_components` (`:287-289`).

### التأثير الفعلي — بيانات حساسة مؤكَّدة بالتصريح (`schemas.py:55-64`)

`SovereignEntityResponse` (اللي بترجع من `list_entities`/`get_entity`) بتحتوي صراحة:
- `treasury_balance_mrusdt` — **رصيد الخزينة المالي الفعلي للكيان**
- `kyb_status` — حالة التحقق من الهوية (KYB)
- `created_by` — معرف المستخدم المُنشئ
- بيانات الكيان الكاملة الأخرى (اسم، نوع، بيانات تسجيل)

**🔴 تصحيح فوري (بعد اختبار حي فعلي، وليس قراءة كود فقط):** الادّعاء الأصلي فوق ("أي زائر مجهول بلا توكن") **غير دقيق على نقطتين، اتصحّح فورًا بعد اختبار حقيقي:**

1. **مصادقة مطلوبة فعليًا:** `app/main.py:300-305` بيلف **كل** الـ30 router (شامل `sovereign_entities`) بـ`Depends(require_sector(sector))` على **مستوى تسجيل الراوتر نفسه** — قبل أي `Depends` خاص بالـendpoint. `require_sector` (`core/security.py:205-226`) بتستخدم `Depends(get_current_active_user)` داخليًا، يعني **بتتطلب توكن JWT صالح لمستخدم حقيقي كحد أدنى، لكل الأربعة endpoints بلا استثناء** — مش "بلا أي مصادقة إطلاقًا" زي ما كان موثَّق. تأكَّد حيًا: طلب بدون أي `Authorization` header رجّع `401 Not authenticated`.
2. **مين بالظبط يقدر يعدّي؟** بما إن `identity/service.py`'s `_issue_tokens` **مش بيبعت claim `sector` إطلاقًا** لأي مستخدم عادي (موثَّق مسبقًا في `critical-finding-xtenant-systemic.md`)، أي مستخدم عادي (`system_role=USER`) هيترفض دايمًا (`user_sector is None`). **الاستثناء الوحيد:** `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` (بيتخطوا فحص الـsector كليًا، `security.py:215-216`). **يعني الاستغلال محصور فعليًا في حساب `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` — مش أي زائر عشوائي.**
3. **🔴 الأهم: الثغرة حاليًا "كامنة" (latent) مش "حية" — اختبار حي فعلي بحساب `SUPER_ADMIN` حقيقي (تينانت14) بهيدر مزوَّر (تينانت1) رجّع `500`، مش تسريب ناجح:**
   ```
   sqlalchemy.exc.DBAPIError: DataError: invalid input for query argument $2:
   <app.api.deps.SimpleTenant object...> ('SimpleTenant' object cannot be interpreted as an integer)
   [parameters: (2, <SimpleTenant object>)]
   ```
   **السبب:** `get_entity`/`list_entities`/`list_templates`/`list_components` **لسه فيهم نفس باج `SimpleTenant` الأصلي** (الكائن الخام بيتبعت كـbind parameter مباشر، مش `.id`) — **بالتصميم، تم استثناؤهم عمدًا من إصلاح `SimpleTenant` في هذه الجلسة بانتظار قرار التصميم ده بالذات.** يعني: **الكراش الحالي (غير المتعلق أصلًا بالسؤال الأمني) هو اللي بيمنع الاستغلال فعليًا الآن.**

**الخلاصة المُصحَّحة:** هذا **مش تسريب بيانات حي وقابل للاستغلال فورًا حاليًا** — ده **عيب تصميمي كامن (latent architectural flaw)**: بمجرد ما حد يصلح باج `SimpleTenant` في الأربعة endpoints دول بنفس الطريقة الميكانيكية المطبَّقة في باقي المشروع (تحويل `tenant.id` بسيط، بديهي وسهل الوقوع فيه)، **هيبقى الاستغلال شغال فورًا** — لأن مفيش أي ربط بين تينانت الطالب الحقيقي (`current_user.tenant_id`) وتينانت البيانات المطلوبة (`X-Tenant-ID`) في أي من الأربعة. **الخطورة الحقيقية: أي حساب `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` من أي تينانت (مش بس تينانت الهدف) هيقدر يشوف رصيد الخزينة وحالة الـKYB لكيانات أي تينانت تاني، لحظة ما حد "يصلح" الكراش الحالي بإصلاح سطحي.** هذا يفرّق هذا الاكتشاف جوهريًا عن باقي أمثلة `SimpleTenant` (اللي إصلاحها بيغلق الثغرة الأمنية تلقائيًا) — هنا **إصلاح الكراش وحده هيفتح الثغرة، مش يقفلها**، ما لم يُضَف فحص مصدر الثقة الصحيح (`current_user.tenant_id`) في نفس الوقت.

### هل هذا موثَّق سابقًا في `critical-finding-xtenant-systemic.md`؟ **لا — اكتشاف جديد بالكامل**

`sovereign_entities` **مذكور** في الملف ده (جدول 🔴 SUSPICIOUS، رقم 18) لكن **فقط بخصوص `review_kyb`** (endpoint إداري محمي بـ`get_current_superuser`، نفس نمط `affiliate`). **الأربعة endpoints دول (`list_entities`, `get_entity`, `list_templates`, `list_components`) غير مذكورين إطلاقًا في أي مكان بالملف** — لأن منهجية الفحص الأصلية ركّزت صراحة على "endpoint محمي بصلاحية مرتفعة... معتمدًا على `tenant_id` من الهيدر" (نص الملف، قسم "المنهجية")، وافترضت إن أي endpoint بلا حماية admin على الأقل هيبقى محمي بمصادقة أساسية (`current_user`) — افتراض غير صحيح هنا، لأن الأربعة دول **بلا أي مصادقة إطلاقًا**، مش حتى `get_current_active_user`. **فجوة في تغطية الفحص الأصلي نفسه، مش بس في الكود.**

### الحالة: 🔴 **صفر إصلاح. بانتظار توجيه المستخدم صراحة.**

هذا الاكتشاف **خارج نطاق جلسة `SimpleTenant` بالكامل** (مش type-mismatch، مش كراش) — تم توثيقه هنا فورًا بمجرد التأكد منه، بدل الانتظار لنهاية الجلسة، نظرًا لخطورته. **لم يُتخذ أي قرار تصميمي** (هل الأربعة دول المفروض تبقى endpoints عامة بتصميم مقصود ومحتاجة توثيق كده بس، ولا سهو حقيقي يستاهل إضافة `current_user` كمصادقة إجبارية؟) — القرار ده محتاج مراجعة أمنية/منتجية صريحة، مش قرار تقني بسيط. باقي الـ21 endpoint في `sovereign_entities` (اللي عندها `current_user` فعلي) استمرت في مسار إصلاح `SimpleTenant` العادي بالتوازي، بمعزل تام عن هذا الاكتشاف.

---

## 🔴🔴 [2026-08-13] — اكتشاف ثانٍ حرج: `review_kyb` و`update_entity` (`sovereign_entities`) بيفقدوا الكتابة صامتًا — regression من جلسة `transaction-savepoint-bug-session-log.md` السابقة، مش من هذه الجلسة

**السياق:** اكتُشف أثناء التحقق الحي (DB-level، مش status code) لـ`sovereign_entities` ضمن جلسة `SimpleTenant`. **هذا مش باج `SimpleTenant`** — فئة "نجاح كاذب" (نفس التحذير الحرفي من جلسة الترانزاكشن السابقة)، اكتشفناه بالصدفة بسبب التزامنا بالتحقق الحي الصارم اللي طلبه المستخدم.

### التأكيد (مؤكَّد بـ`SELECT` مستقل، مش افتراض)

- `PUT /sovereign-entities/{id}/kyb/status` (`review_kyb`): الـAPI رجّع `200 {"kyb_status": "REJECTED"}`. `SELECT` فوري على الـDB: **`kyb_status = PENDING`، لم يتغيّر إطلاقًا.**
- `PUT /sovereign-entities/{id}` (`update_entity`): نفس النتيجة بالحرف — الـresponse رجّع القيمة الجديدة (`legal_name`)، الـDB فاضل بالقيمة القديمة.

### السبب الجذري (قراءة كود مباشرة)

`repository.py:97-107` (`update_entity`) بتعمل `await self.db.flush()` **بس** (مش `commit()`) — **نفس التعديل اللي طُبِّق في جلسة `transaction-savepoint-bug-session-log.md`** على كل الـrepository methods المستدعاة من جوه `begin_nested()`. لكن `service.py`'s `review_kyb` (سطر 193-218) و`update_entity` (سطر 134-140) **معندهمش `async with self.db.begin_nested():` من الأساس** — يعني ماكانوش ضمن جرد/نطاق فحص الجلسة السابقة (اللي كانت بتدوّر على `begin_nested()` تحديدًا)، فمحصلش لهم إضافة `await self.db.commit()` الصريح بعد الكتابة (زي اللي اتضاف لـ24 method تانيين في نفس الجلسة). **النتيجة: أي كتابة عبر الـ2 method دول بتضيع صامتة الآن، بلا أي خطأ ظاهر.**

**تأكيد النطاق (بالقراءة، مش تخمين):** باقي methods الدومين اللي بتنادي `self.repo.update_entity` (`deposit_to_entity_wallet` سطر 366، `transfer_from_entity` سطر 442) **معمولة صح** — ملفوفة بـ`begin_nested()` + `commit()` صريح بعده (سطور 364/392 و431/465 على الترتيب)، لأنها كانت فعليًا ضمن نطاق الجلسة السابقة. **المشكلة محصورة في `review_kyb`/`update_entity` بس داخل هذا الدومين** — لم يُفحَص باقي المشروع بحثًا عن نفس النمط (service method بتنادي repo method بقت flush-only، بلا `begin_nested()`/`commit()` خاص بيها) — **يستاهل جرد منهجي منفصل عبر كل الـ24 دومين اللي اتلمست في الجلسة السابقة، مش بس `sovereign_entities`.**

### الحالة: 🔴 **صفر إصلاح. موثَّق فقط بتوجيه صريح من المستخدم — القرار مؤجَّل لجلسة/مراجعة مخصَّصة.**

**ملاحظة مهمة:** هذا الاكتشاف **يبرهن على قيمة منهجية "التحقق الحي بـ`SELECT` مستقل، مش status code" اللي أصرّ عليها المستخدم طول الجلسات الثلاث** — لولاها كان هيتسجَّل "✅ `review_kyb` نجح حيًا" غلط، بالظبط زي `ai_governance.reset_agent_quotas` في الجلسة السابقة.

### 🔴 تحديث فوري — فحص استباقي سريع (read-only، بتوجيه المستخدم) وسّع النطاق: 3 حالات إضافية في `saas`

بتوجيه صريح من المستخدم ("هذا الاكتشاف يستاهل معاملة استثنائية... فحص سريع 10 دقايق")، اتعمل `grep` مركَّز على `await self.db.flush()` في `repository.py` بتاع الأربعة دومينات (`academy`, `commerce`, `sovereign_entities`, `saas`)، ولكل نتيجة اتفحص الـcaller في `service.py` (هل ملفوف بـ`begin_nested()`+`commit()` صريح، ولا لأ):

| الدومين | النتيجة |
|---|---|
| `academy` | ✅ نظيف — موضع `flush()`-only واحد بس (`enroll`)، والـcaller (`enroll_in_course`) مؤكَّد ملفوف صح (`begin_nested()` + `commit()` من الجلسة السابقة) |
| `commerce` | ✅ نظيف — مؤكَّد تجريبيًا بالفعل (كل الطلبات الحية في هذه الجلسة لـ`checkout`/`create_product` أثبتت كتابة صحيحة عبر `SELECT` مستقل) |
| `sovereign_entities` | 🔴 حالتان مؤكَّدتان مسبقًا (`review_kyb`, `update_entity`) — راجع القسم فوق |
| **`saas`** | 🔴🔴 **3 حالات إضافية جديدة، غير مؤكَّدة حيًا بعد (تأكيد بالقراءة فقط، مش تحقق DB مباشر زي `sovereign_entities`)** |

### الثلاث حالات الجديدة في `saas/service.py`

1. **`cancel_subscription`** (سطر 134-147): بتنادي `self.repo.update_subscription(...)` (flush-only، `repository.py:188-198`) **بلا أي `begin_nested()`/`commit()` إطلاقًا في الدالة كلها**.
2. **`process_auto_renewals`'s فرع `except InsufficientBalanceError`** (سطر 190-198): المسار الناجح (try) ملفوف صح (`begin_nested()` سطر 161 + `commit()` سطر 185)، **لكن فرع الفشل (رصيد غير كافٍ) بينادي `update_subscription(...)` تاني برّه أي `begin_nested()`/`commit()`** — تحديث حالة الاشتراك لـ`PAST_DUE` (مع مهلة سماح) **بيضيع صامت**.
3. **`can_access_service`** (سطر 209-231، سطر 228 تحديدًا): بتنادي `update_subscription_status` (بتستدعي نفس `update_subscription` flush-only) لتحديث اشتراك منتهي الصلاحية لحالة `EXPIRED`، **برّه أي `begin_nested()`/`commit()`**.

---

## 🔴🔴🔴 [2026-08-13] قسم موحَّد — نمط "regression الكتابة الصامتة" عبر `sovereign_entities` + `saas` (5 حالات، درجات تأكيد مختلفة، أولوية عاجلة)

**هذا القسم يجمع ويوحّد كل حالات "نجاح ظاهري + كتابة مفقودة صامتة" المكتشفة في هذه الجلسة، مع تمييز صريح بين مستوى التأكيد لكل حالة — بعضها مؤكَّد بـ`SELECT` مستقل فعلي (DB-level)، وبعضها لسه مؤكَّد بقراءة الكود بس. الخلط بين المستويين غير مقبول، فالجدول التالي يوضّح كل حالة بدقة.**

| # | الدومين.الدالة | مستوى التأكيد | الدليل |
|---|---|---|---|
| 1 | `sovereign_entities.review_kyb` | ✅ **مؤكَّد DB-level** | طلب فعلي (`PUT .../kyb/status`) رجّع `kyb_status=REJECTED`، `SELECT` مستقل فوري رجّع `kyb_status=PENDING` (لم يتغيّر) |
| 2 | `sovereign_entities.update_entity` | ✅ **مؤكَّد DB-level** | طلب فعلي (`PUT /sovereign-entities/{id}`) رجّع `legal_name` الجديد، `SELECT` مستقل رجّع القيمة القديمة (فاضية) |
| 3 | `saas.cancel_subscription` | ✅ **مؤكَّد DB-level (تحقق إضافي مخصَّص، بطلب المستخدم — الأولوية لأنه أعلى أثر مباشر على العميل)** | طلب فعلي (`PUT /saas/subscriptions/1/cancel`) رجّع `status=CANCELLED`، `SELECT` مستقل فوري على `saas_tenant_subscriptions id=1` رجّع **`status=ACTIVE` — لم يتغيّر إطلاقًا**. **يعني: عميل يظن إنه ألغى اشتراكه، والنظام لسه شغّال عليه فعليًا (خطر إعادة خصم/تجديد تلقائي لاحقًا).** |
| 4 | `saas.process_auto_renewals` (فرع `except InsufficientBalanceError`) | 🟡 **مؤكَّد بقراءة الكود فقط — غير مُختبَر DB-level** | نفس النمط البنيوي بالحرف (`update_subscription` خارج أي `begin_nested`/`commit`)، لم يُنفَّذ طلب حي لتفعيل هذا المسار تحديدًا |
| 5 | `saas.can_access_service` (تحديث `EXPIRED`) | 🟡 **مؤكَّد بقراءة الكود فقط — غير مُختبَر DB-level** | نفس النمط البنيوي، لم يُنفَّذ طلب حي |

### السبب الجذري الموحَّد (نفس الآلية بالضبط في الحالات الخمس)

جلسة `transaction-savepoint-bug-session-log.md` السابقة غيّرت عشرات الـrepository methods من `commit()` مباشر إلى `flush()`-only، على افتراض إن كل service method حاضنة ملفوفة بـ`begin_nested()` وهتاخد `commit()` صريح مُضاف بعدها. **الافتراض ده صحيح للـmethods اللي كانت فعليًا ضمن جرد تلك الجلسة (اللي كانت بتدوّر على `begin_nested()` تحديدًا) — لكن أي service method تانية بتنادي نفس الـrepo method flush-only، **بلا `begin_nested()` خاص بيها من الأساس**، مالهاش أي طريقة تاخد `commit()`. النتيجة: كتابة صامتة مفقودة، نجاح ظاهري 100% (status code سليم، صفر خطأ)، **بلا أي أثر فعلي في الـDB**.

### توصية صريحة (بتوجيه المستخدم، أعلى أولوية مسجَّلة في هذه الجلسة)

**هذا الاكتشاف يستحق جلسة تصحيح عاجلة منفصلة، بأولوية أعلى من جلسة "duplicate-kwarg" المقترَحة سابقًا** — لأنه يمس نتائج جلسة سابقة كانت مُعتبَرة مقفولة وآمنة (`transaction-savepoint-bug-session-log.md`، مغلقة بـcommit `a9bbae4`). **الجرد الحالي جزئي بالكامل** (4 دومينات فقط — `academy`, `commerce`, `saas`, `sovereign_entities` — من أصل 24 دومين اتلمست في الجلسة السابقة؛ داخل الأربعة، تأكيد DB-level حصل على 3 حالات بس من أصل 5 المكتشفة). **الخطوة الأولى المقترَحة لأي جلسة مخصَّصة قادمة:** جرد منهجي كامل (`grep` لـ`await self.db.flush()` في كل `repository.py` عبر الـ24 دومين، ثم تتبّع كل caller في `service.py` المقابل: هل ملفوف بـ`begin_nested()`+`commit()` صريح، ولا لأ) — **نفس المنهجية المستخدَمة هنا بالضبط، لكن بنطاق كامل بدل 4 دومينات فقط.**

---

## 📌 [2026-08-14] قاعدة عملية دائمة — `psql -c` متعدد العبارات = ترانزاكشن ضمنية واحدة

**اكتُشفت أثناء تنظيف بيانات throwaway جلسة `SimpleTenant`، بنفس أهمية "درس البورت المعلَّق" المُسجَّل سابقًا في نفس الجلسة.**

`docker exec ... psql -c "DELETE FROM a; DELETE FROM b; DELETE FROM c;"` — لو أي عبارة من الثلاثة فشلت (زي FK constraint)، **كل العبارات التانية في نفس الاستدعاء بترجع (rollback)، حتى اللي طبعت "DELETE N" ناجحة قبل الفشل**. السبب: PostgreSQL's simple query protocol بيعامل الـstring متعدد العبارات دي كترانزاكشن ضمنية واحدة.

**القاعدة:** أي `DELETE`/`UPDATE` متعدد العبارات عبر `psql -c` (أو أي أداة بتبعت multi-statement query واحدة) **لازم إما:**
1. يتقسّم لاستدعاءات `-c` منفصلة (كل واحد ترانزاكشن مستقلة)، أو
2. يُتحقَّق منه بـ`SELECT COUNT` مستقل **بعد** كل محاولة (ناجحة أو فاشلة) — **متعتمدش على رسائل "DELETE N" وحدها كدليل نجاح**، خصوصًا لو الاستدعاء كان فيه أكتر من عبارة.

---

## ✅ [2026-08-14] — إغلاق جلسة `SimpleTenant` — الحالة النهائية

**التفاصيل الكاملة، كل ديف، كل تحقق حي، كل خطوة:** `.claude/reports/simpletenant-fix-session-log.md`.

**المُنجز:** إصلاح باج `SimpleTenant`/type-mismatch (`get_current_tenant()` بترجع كائن، مش `int` خام) عبر **4 دومينات مؤكَّدة مسبقًا** (`academy` 36 موضع، `commerce` 11، `saas` 17، `sovereign_entities` 17) = **81 endpoint مُصلَح بالقاعدة الموحّدة** (`current_user.tenant_id` بدل `X-Tenant-ID` header). **مؤكَّد حيًا بالكامل** عبر endpoints ممثِّلة لكل مستوى حماية (`active_user`/`instructor_or_admin`/`superuser`) في الأربعة دومينات، بمعيار صارم (`SELECT` مستقل قبل/بعد) على كل مسار مالي (`finance` integration في `commerce`, `sovereign_entities`).

**5 مواضع مؤجَّلة عمدًا، بقرار صريح، خارج نطاق أي إصلاح تلقائي مستقبلي:**
- `commerce.visa_webhook` — webhook دفع خارجي بلا `current_user`، يحتاج مراجعة أمنية مخصَّصة لبوابة الدفع كاملة (توقيع، تكرار) قبل أي تعديل على مصدر `tenant_id`.
- `sovereign_entities`: `list_entities`, `get_entity`, `list_templates`, `list_components` — **🔴🔴🔴 تحذير بارز مُضاف في أعلى `critical-finding-xtenant-systemic.md` نفسه** — الأربعة دول endpoints بلا `current_user`، إصلاح الكراش وحده (بدون قرار منتجي بخصوص مصدر المصادقة) هيفتح ثغرة تسريب مالي/KYB حقيقية. تقرير مخصَّص: `.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md`.

**اكتشافان حرجان إضافيان، خارج نطاق `SimpleTenant` بالكامل، صفر إصلاح:**
1. **كشف بيانات مالية/KYB كامن (latent)** في الأربعة endpoints فوق — غير قابل للاستغلال حاليًا (محجوب بنفس كراش `SimpleTenant`)، لكنه هيبقى قابل للاستغلال فورًا لحظة ما حد يصلح الكراش بدون معالجة مصدر المصادقة.
2. **نمط "regression الكتابة الصامتة"** — 5 حالات (`sovereign_entities.review_kyb`, `sovereign_entities.update_entity`, `saas.cancel_subscription` **الثلاثة مؤكَّدة DB-level**؛ `saas.process_auto_renewals` فرع الفشل، `saas.can_access_service` **مؤكَّدتان بقراءة الكود بس**) ناتجة عن تفاعل جلسة `transaction-savepoint-bug-session-log.md` السابقة مع service methods لم تكن ضمن نطاقها. **موصى بجلسة تصحيح عاجلة منفصلة، أعلى أولوية من أي عمل تاني معلَّق** (بما فيه جلسة duplicate-kwarg المقترَحة سابقًا) — لأنها تمس نتائج جلسة كانت مُعتبَرة مقفولة بأمان.

**بيانات throwaway الأربعة دومينات:** اتنضّفت بالكامل، تحقق مستقل شامل (20 استعلام، كلهم صفر) + تأكيد إضافي إن `academy_tenants` رجعت لحالتها الأصلية بالحرف.

**Commit:** معزول واحد، يغطي بالضبط نطاق هذه الجلسة (4 ملفات router.py + التحذير في الملف المرجعي + هذا الملف + تقريرين جدد)، صفر تلوّث من جلسات تانية.

---

## 📌 [2026-08-14] ملاحظة منفصلة — `health_check_deployment_task`'s `is_healthy` مُثبَّتة

`app/tasks/deployment.py`'s `health_check_deployment_task`: `is_healthy = True  # محاكاة` — فحص الصحة الفعلي للخدمة المنشورة (ping, DB connection, API response) **غير منفَّذ بعد**، مجرد قيمة ثابتة. يستاهل جلسة منفصلة مستقبلية لتنفيذ الفحص الحقيقي. **لا علاقة له بباج الكتابة الصامتة** (اكتُشف أثناء التحقق من إصلاح `.claude/reports/silent-write-regression-session-log.md`، موثَّق هناك بالتفصيل).

---

## 📌 [2026-08-14] ملاحظة منفصلة — `academy_tenants.admin_id=1` كانت بالفعل تشاور على مستخدم غير موجود

`academy_tenants(id=1, "Local Test Tenant")`'s `admin_id=1` كانت بالفعل **dangling FK** (تشاور على `users.id=1` غير موجود) **قبل بداية جلسة `silent-write-regression` بالكامل** — اكتُشف بالصدفة أثناء محاولة تنظيف بيانات throwaway (`INSERT INTO users (id=1, ...)` نجح بلا أي تعارض، يعني الـID كان فاضي أصلًا رغم إن التينانت بيشاور عليه من زمان). **غير متعلق بأي عمل في هذه الجلسة أو أي جلسة سابقة موثَّقة** — يستاهل فحص مستقل لسلامة بيانات `academy_tenants` الأساسية (خصوصًا التينانت الافتراضي id=1 المُستخدَم عبر كل الجلسات). **تحذير لأي جلسة مستقبلية:** لو حاولت تمسح أي مستخدم بمعرِّف `id=1`، هتتفاجئ بنفس عائق الـFK ده — التفاصيل الكاملة في `.claude/reports/silent-write-regression-session-log.md`.

---

## ✅🔴 [2026-08-14] — جلسة `silent-write-regression` — الحالة النهائية (جرد كامل + إصلاحان فعليان استثنائيان)

**التفاصيل الكاملة، كل ديف، كل تحقق حي، كل خطوة:** `.claude/reports/silent-write-regression-session-log.md`.

**السياق:** جلسة مخصَّصة لتتبّع النطاق الكامل لـ"regression الكتابة الصامتة" (service methods بترجع نجاح API لكن الكتابة فعليًا مبتترجعش للـDB) المكتشف في نهاية جلسة `SimpleTenant` السابقة — امتداد مباشر لـ`transaction-savepoint-bug-session-log.md` (اللي غيّرت 89 repo method من `commit()` لـ`flush()`، على افتراض إن كل caller محمي بـ`begin_nested()`+`commit()` صريح — افتراض غير صحيح لأي caller خارج نطاق تلك الجلسة).

### ⚠️ استثناء منهجي صريح — هذه الجلسة كانت مفروض تكون "توثيق فقط"، وخرجت عن القاعدة مرتين

**القاعدة الأصلية المتفق عليها بداية الجلسة:** صفر انتقال للمرحلة 3 (إصلاح فعلي) لأي حالة قبل ما التحقق DB-level يخلص لكل الحالات المكتشفة — الحجم كبير جدًا (35 موضع)، وأي افتراض غير مؤكَّد مكلف (فلوس حقيقية). **بتوجيه صريح من المستخدم، تم الخروج عن القاعدة دي مرتين، لسببين مختلفين موثَّقين بالتفصيل:**

1. **`app/tasks/deployment.py`** (3 دوال، 4 مواضع كتابة) — **الوحيدة في كل الجلسة اللي كانت شغالة فعليًا، بلا أي عائق حامي (constructor bug أو غيره)، وبتتفعّل تلقائيًا** بعد كل عملية شراء خدمة حقيقية (`service_marketplace.purchase_service`). نجاح كاذب حي مؤكَّد DB-level (مش نظري ولا محجوب) — **الاستثناء الوحيد اللي بيستاهل فعلًا معاملة "أعلى أولوية من كل حاجة تانية".**
2. **`app/domains/ai_agents/service.py`'s `execute_agent_action`** — مش نجاح كاذب حي مؤكَّد زي الأول (محتاج شرط "تكلفة=0 + بلا موافقة بشرية")، لكن بتوجيه المستخدم اعتُبر إصلاح بسيط وميكانيكي بما يكفي إنه يُطبَّق فورًا بدل انتظار جلسة منفصلة.

**كل الإصلاحين مؤكَّدين DB-level بالكامل (تفاصيل تحت) — أي مراجعة مستقبلية لازم تفهم إن الـcommit ده فيه كود production متغيّر فعليًا، مش بس تعليقات توثيقية/تحذيرية.**

### 1) الجرد الكامل — 160 موضع استدعاء عبر 25 دومين/ملف + 34 موضع `finance.transfer/swap` عبر المشروع كله

**125 (أ) محمي، 35 (ب) غير محمي عبر 32 دالة/method مستقلة.** المنهجية: 6 دفعات جرد متوازية (agents)، كل واحدة غطّت مجموعة دومينات، لكل موضع `flush()`-only تتبّع كل الأماكن اللي بتناديه (جوه الدومين وعبره) وفحص هل الـcommit موجود فعليًا على المسار الناجح.

### 2) الإصلاحان الفعليان (Phase 3، استثنائيان) — مؤكَّدان DB-level بالكامل

**`tasks/deployment.py` (4 مواضع):**
| الموضع | قبل الإصلاح | بعد الإصلاح (مؤكَّد DB-level) |
|---|---|---|
| `_deploy_service_async` | نجاح كاذب (`status=active` لكن `deployment_status` لسه `DEPLOYING`) | ✅ `deployment_status=ACTIVE`, `deployed_domain` صحيح |
| `cleanup_failed_deployment_task` | نجاح كاذب (حتى Celery نفسه سجّل "succeeded") | ✅ `deployment_status=FAILED` صحيح |
| `health_check_deployment_task` (فرع `True`) | لم يكن مختبَرًا حيًا من قبل — اتنفَّذ فعليًا الآن | ✅ `deployment_status=ACTIVE` صحيح |
| `health_check_deployment_task` (فرع `False`) | dead code حاليًا (`is_healthy` مُثبَّتة `True`) | ✅ تحقق بديل أمين لنفس آلية الحماية (سطر الـcommit نفسه) |

**`ai_agents.execute_agent_action` (فرعان):**
- فرع `except Exception`: كان دايمًا بيضيع (صفر منفذ هروب) → ✅ مؤكَّد حيًا (طلب HTTP فعلي اصطدم بباج AI منفصل غير متعلق، فعّل الفرع فعليًا)
- مسار النجاح (سيناريو "تكلفة=0 + بلا موافقة بشرية"): كان بيضيع أحيانًا → ✅ مؤكَّد عبر سكريبت معزول (monkey-patch مؤقت لـ`ai_engine.generate` داخل الـprocess بس، صفر تعديل ملفات)

### 3) تعليقات تحذيرية وقائية — 7 مواضع، صفر تغيير سلوك

`digital_twin/repository.py:create_interaction_log`، `employment/repository.py:update_payroll_status`، `commerce/repository.py:release_commission`، `insurance/repository.py:update_subscription`، `invoicing/repository.py:create_invoice`+`update_invoice`، `projects/repository.py:create_contribution` — كل واحدة بتحذّر من تحويل `commit()` لـ`flush()` بدون معالجة الـservice method المعتمدة عليها بالصدفة أولًا.

### 4) الفئات المؤجَّلة (موثَّقة بالكامل، صفر إصلاح، خارج نطاق هذه الجلسة)

- **باج constructor منتشر** (`FinanceService(db)`/`InvoicingService(db)` بمعامل واحد بدل اتنين): يحجب 7 من أصل 8 مواضع `finance.transfer` المتناثرة (`arbitration_syndicates.join_syndicate`, `insurance.renew_subscription`, `insurance.disburse_monthly_pensions`, `invoicing.update_invoice_status` — مؤكَّد حيًا كمحجوب عبر HTTP فعلي، `iot.settle_carbon_credits`, `projects.add_contribution`, `tasks/billing.py`) + `digital_twin.interact_with_twin` — **صفر خطر فعلي حاليًا لكل الحالات دي**، أولوية غير عاجلة، يحتاج جلسة/جلسات منفصلة.
- **🔴 تنويه خاص — `iot.settle_carbon_credits`:** الوحيدة في كل مجموعة `finance.transfer` اللي لو اتصلح عائق الـconstructor بمعزل عن باقي الملف، **هتكون (ب) حقيقي غير محمي إطلاقًا** (صفر آلية حماية بالصدفة، بعكس باقي المجموعة). يستاهل تنويه بارز لأي جلسة مستقبلية تصلح باج الـconstructor.
- **🟢 `insurance.disburse_monthly_pensions`:** أعمق باج أمان في القائمة كلها — استعلام "المعاشات المستحقة" بيمرر `None` بدل الفلتر الحقيقي، فبيرجع صفر نتيجة دايمًا. مؤكَّد حيًا: صفر معاش هيتصرف أبدًا، بغض النظر عن أي باج تاني.
- **🟠 `health` (3 مواضع، `book_appointment`/`trigger_emergency`/`create_facility`):** crash-bugs حقيقية (`NameError` على متغيّر `job` غير معرَّف، سابق لأي تعديل بتاعنا) — **فئة مختلفة تمامًا عن نمط الترانزاكشن**، إصلاح الـcommit وحده مش هيخلي الـendpoints دي تشتغل. يحتاج جلسة منفصلة تصحح مصدر `audit_log` الملوَّث.
- **`tenders_auctions.close_auction`:** محجوبة ببجّين مستقلين (constructor + method غير موجودة `release_held_funds`) — أقل أولوية.

**5 حالات معروفة سابقًا من جلسة `SimpleTenant` (`sovereign_entities.review_kyb`/`update_entity`, `saas.cancel_subscription`, `saas.process_auto_renewals`, `saas.can_access_service`) — لم تُلمس في هذه الجلسة، لسه محتاجة قرار/إصلاح منفصل.**

### 5) بيانات throwaway وتنظيف

اتنضّفت بالكامل عبر 17 استعلام `COUNT` مستقل (كلهم صفر) + تأكيد `academy_tenants` مطابق للـbaseline. **استثناء واحد موثَّق:** `users id=1` (`p_system_treasury`) متقدرش يتمسح — `academy_tenants(id=1)`'s `admin_id` بيشاور عليه (إشارة كانت dangling من قبل الجلسة أصلًا، تفصيل في الملاحظة المنفصلة فوق) — تم اختيار تركه بدل المساس ببيانات مشتركة بين كل الجلسات.

**Commit:** معزول واحد — 8 ملفات كود (اتنين فيهم تغيير سلوك فعلي: `tasks/deployment.py`, `ai_agents/service.py`؛ الستة الباقيين تعليقات تحذيرية بس) + تقرير الجلسة الجديد + هذا الملف.

---

## 📌 [2026-08-14] ملاحظة منفصلة — `health.book_appointment`'s `NameError` (`job.id`/`job.title`) اتقابلت تاني أثناء جلسة `constructor-mismatch`

أثناء إصلاح باج constructor في `health/service.py` (`self.finance = FinanceService(db)` بمعامل واحد بدل اتنين — راجع `.claude/reports/constructor-mismatch-session-log.md`)، اتأكَّد بالقراءة إن `book_appointment` (`service.py:204-258`) لسه فيها نفس باج `NameError` الموثَّق سابقًا في `silent-write-regression-session-log.md` (سطر أعلى في هذا الملف): استدعاء `audit_log(...)` بعد إنشاء الموعد بيشاور على متغيّر `job` **غير معرَّف إطلاقًا** في scope الدالة (`job.id`, `job.title`) — على الأرجح كود منسوخ بالغلط من دومين وظائف غير متعلق.

**الحالة: باج موجود مسبقًا، سابق لأي تعديل في جلسة `constructor-mismatch` أو أي جلسة قبلها — صفر إصلاح تم عليه في أي جلسة لحد الآن.** إصلاح باج الـconstructor **مش هيخلي `book_appointment` تشتغل بالكامل** — بعد إصلاح الـconstructor، الطلب هيعدّي مرحلة خصم الرسوم المالية بنجاح، لكن هيكراش لاحقًا بـ`NameError` عند الوصول لسطر `audit_log` جوه `async with self.db.begin_nested():` (يعني rollback كامل نظيف للخصم المالي وصف الموعد معًا — نفس session/transaction واحدة، مش فقدان جزئي). **مؤكَّد عمليًا (سكريبت تحقق معزول، تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md`):** منطق الخصم المالي + إنشاء الموعد سليم 100% لما يتعزل عن سطر `audit_log` الملوَّث — المشكلة محصورة في السطر ده بالذات. **يحتاج جلسة منفصلة** تصحح مصدر `job`/`audit_log` الصحيح في `book_appointment` (وأيضًا `trigger_emergency`/`create_facility`، نفس الفئة) — **خارج نطاق جلسة `constructor-mismatch` بالكامل.**

**⚠️ ملاحظة إضافية:** بيانات throwaway الاختبار (`users id=38-40`, `wallets`, `health_facilities id=1`, `medical_appointments id=1`, `transactions id=14`) **متروكة عمدًا في الداتابيز حاليًا** (قرار مؤجَّل، مش نسيان) — التفاصيل الكاملة وسبب الإبقاء عليها في قسم "📦 بيانات اختبار دائمة للجلسة" بملف `.claude/reports/constructor-mismatch-session-log.md`.

---

## 📌 [2026-08-14] ملاحظة منفصلة — `iot.settle_carbon_credits`'s `_get_user_email` بتنادي `UserRepository.get_by_id` بمعامل ناقص (فئة شقيقة لـ constructor-mismatch، مش نفسها)

أثناء التحقق الحي من إصلاح باج constructor في `iot/service.py` (`self.finance = FinanceService(db)` بمعامل واحد بدل اتنين + إضافة `await self.db.commit()` الصريح بعد `begin_nested()` — راجع `.claude/reports/constructor-mismatch-session-log.md`)، اتكشف باج منفصل تمامًا منع اكتمال الاختبار عبر `POST /api/iot/carbon/settle` الحقيقي:

`iot/service.py:29-33` (`_get_user_email`):
```python
async def _get_user_email(self, user_id: int) -> str:
    from app.domains.identity.repository import UserRepository
    user_repo = UserRepository(self.db)
    user = await user_repo.get_by_id(user_id)   # ← معامل واحد بس
    return user.email if user else f"user_{user_id}@eppne.com"
```
التوقيع الحقيقي (`identity/repository.py:21`): `get_by_id(self, user_id: int, tenant_id: int, load_wallet: bool = False)` — `tenant_id` **معامل إجباري ناقص**. مؤكَّد بالتنفيذ الفعلي (طلب HTTP حقيقي، مش قراءة كود بس):
```
app.core.errors.BusinessError: فشل الإيداع المالي: UserRepository.get_by_id() missing 1 required positional argument: 'tenant_id'
```

**التصنيف: فئة شقيقة لباج `constructor-mismatch` (نفس نمط "معامل ناقص عن التوقيع الحقيقي") لكن على استدعاء method في repository، مش على constructor لـservice class** — لذلك **غير مُدرَج ضمن جرد الـ111 موضع الأصلي** لجلسة `constructor-mismatch` (اللي كان مقصور على `XService(db)` مقابل `XService(db, tenant_id)`). **باج موجود مسبقًا، سابق لأي تعديل في هذه الجلسة — صفر إصلاح تم عليه.**

**الأثر:** `settle_carbon_credits` **يمنع `finance.transfer()` من إتمام البحث عن بريد المستلم** — بيتلبع جوه `except Exception` الموجودة أصلًا في `settle_carbon_credits` وترمي `BusinessError` بدل ما تكمل. **يمنع الـendpoint الحقيقي من الاكتمال بالكامل، بغض النظر عن إصلاح الـconstructor.** **يحتاج جلسة منفصلة** تصحح استدعاء `get_by_id` (تمرير `tenant_id` من الـscope المتاح في `_get_user_email`/`settle_carbon_credits`) — **خارج نطاق جلسة `constructor-mismatch` بالكامل.**

**تحقق بديل:** تم استخدام سكريبت تحقق معزول (زي `book_appointment` في `health`) يتجاوز استدعاء `_get_user_email` المكسور بس (بريد المالك مُمرَّر مباشرة كمصدر بديل معزول) — تفاصيل كاملة والنتيجة DB-level في `.claude/reports/constructor-mismatch-session-log.md`.

### 🔴 جرد إضافي (`grep` شامل، صفر إصلاح) — نفس الفئة موجودة في 14 موضع تاني عبر المشروع

بطلب صريح، اتعمل `grep` شامل لـ`.get_by_id(` عبر `app/` كله (32 نتيجة إجمالًا)، وكل نتيجة اتقارنت بالتوقيع الحقيقي (`identity/repository.py:21`، `tenant_id` إجباري). **17 موضع صحيحة** (بتمرّر `tenant_id`، شامل `api/deps.py`, `core/security.py`, `academy`, `affiliate`, `commerce`, `identity` نفسها). **15 موضع ناقصة `tenant_id`** (نفس فئة `iot._get_user_email` بالحرف) — **14 موضع جديد + `iot` الموثَّق فوق**:

| # | الملف:السطر | الـmethod الحاضنة |
|---|---|---|
| 1 | `arbitration_syndicates/service.py:561` | `_register_affiliate_commission(self, user_id, tenant_id, action_type)` |
| 2 | `insurance/service.py:62` | `_get_user(self, user_id)` |
| 3 | `invitations/service.py:58` | `_get_user(self, user_id)` |
| 4 | `iot/service.py:31` | `_get_user_email(self, user_id)` — **موثَّقة بالتفصيل فوق، مؤكَّدة بالتنفيذ الفعلي** |
| 5 | `logistics/service.py:64` | `_get_user(self, user_id)` |
| 6 | `manufacturing/service.py:59` | `_get_user(self, user_id)` |
| 7 | `realestate/service.py:568` | `_get_land_owner_for_unit(self, unit)` |
| 8 | `realestate/service.py:575` | `_register_affiliate_commission(self, user_id, tenant_id, amount)` |
| 9 | `service_marketplace/service.py:477` | `_get_user(self, user_id)` |
| 10 | `social/service.py:678` | `_get_user_email(self, user_id)` |
| 11 | `tenders_auctions/service.py:482` | `_register_affiliate_commission(self, user_id, tenant_id, action_type)` |
| 12 | `tourism_sports/service.py:504` | `_register_affiliate_commission(...)` |
| 13 | `transport/service.py:569` | `_get_user_by_id(self, user_id)` |
| 14 | `transport/service.py:576` | `_register_affiliate_commission(self, user_id, tenant_id, amount)` |
| 15 | `zamakana/service.py:646` | `_register_affiliate_commission(self, user_id, tenant_id, action_type)` |

**ملاحظة نمطية:** أغلب المواضع دي جوه helper methods بأسماء متكررة عبر الدومينات (`_get_user`, `_get_user_email`, `_get_user_by_id`, `_register_affiliate_commission`) — نفس نمط كود منسوخ/مكرر عبر أكتر من دومين شفناه قبل كده مع باج duplicate-kwarg. **الـ14 موضع دول لم تُختبَر حيًا ولا يُعرَف حاليًا أي منهم محمي بالصدفة (زي بعض حالات `finance.transfer` المتناثرة) وأيهم (ب) حقيقي غير محمي — يحتاج جرد DB-level منفصل، زي جلسة `constructor-mismatch` بالظبط لكن لفئة `UserRepository.get_by_id`.** **صفر إصلاح على أي منهم في هذه الجلسة — موثَّقة هنا كقائمة مجمَّعة (بطلب صريح، بدل ما تتكتشف واحدة واحدة عبر جلسات مستقبلية)، يستاهلوا جلسة/جرد مخصَّص لاحقًا.**

---

## 📋 قائمة انتظار الجلسات المستقبلية (Backlog) — بتاريخ 2026-08-14

بند جديد بطلب صريح، عشان الفئات المكتشفة والمؤجَّلة عمدًا عبر الجلسات المختلفة متضيعش وسط تفاصيل كل تقرير على حدة. **بترتيب الأولوية المقترَح حاليًا (قابل للتعديل):**

1. **`user-repository-get-by-id-audit`** (جديدة، اسم مقترَح) — جرد + تحقق DB-level لـ15 موضع `UserRepository.get_by_id(user_id)` بمعامل `tenant_id` ناقص، عبر `arbitration_syndicates`, `insurance`, `invitations`, `iot`, `logistics`, `manufacturing`, `realestate` (×2), `service_marketplace`, `social`, `tenders_auctions`, `tourism_sports`, `transport` (×2), `zamakana` — القائمة الكاملة بالـfile:line في القسم فوق مباشرة. **أولوية بعد `duplicate-kwarg`، قبل استكمال Phase 16 الأصلي.** **🔴 تحديث [2026-08-16]، مؤكَّد حيًا في `service_marketplace._register_affiliate_commission`:** الموضع مش مجرد `TypeError` عادي هيوقف endpoint بوضوح — هو **مُلتقَط بصمت جوه `try/except Exception` عامة** (نفس النمط في `realestate`/`digital_twin` وأي دومين تاني بيستخدم `_register_affiliate_commission`)، يعني **فشل مالي/عمولة صامت بالكامل**: الشراء الأساسي بينجح، الفلوس بتتحول، لكن عمولة الإحالة **بتضيع من غير أي إشارة خطأ للمستخدم أو حتى للـresponse** — بيتسجَّل بس في اللوج الداخلي. هذا يرفع أولوية هذا البند فوق مجرد "تصحيح استدعاء" — فيه فقدان بيانات مالية صامت فعلي (عمولات affiliate) يتراكم بصمت طول ما الباج ده موجود، مش مجرد كراش واضح المصدر.
2. **`duplicate-kwarg-audit`** (مذكورة سابقًا، `simpletenant-fix-session-log.md`) — جرد منهجي لفئة `TypeError: got multiple values for keyword argument` المتكررة (`academy.create_org_entity`, `academy.create_course`, `sovereign_entities.create_entity`, `commerce.create_payment_request`، على الأقل 4 حالات مؤكَّدة، يُشتبه في وجود أكتر).
3. **Phase 16 الأصلي** (استكمال ما تبقى منه، راجع `phase16-session-log.md`).
4. **`silent-write-regression` — الحالات المتبقية غير مؤكَّدة DB-level:** `saas.process_auto_renewals` (فرع `except`), `saas.can_access_service` — مؤكَّدتان بقراءة الكود بس، مش DB-level بعد.
5. **`sovereign_entities` — قرار منتجي معلَّق:** الأربعة endpoints بلا مصادقة (`list_entities`, `get_entity`, `list_templates`, `list_components`) — راجع التحذير 🔴🔴🔴 أعلى `critical-finding-xtenant-systemic.md`.
6. **`commerce.visa_webhook`** — مراجعة أمنية مخصَّصة لبوابة الدفع (توقيع، تكرار، مصدر tenant_id).
7. **`redis-client-wrapper-missing-methods`** (جديدة، اسم مقترَح) — جرد لكل methods مفقودة على `RedisClientWrapper` بتتسبب في `AttributeError` عند الاستخدام الفعلي. حالتان مؤكَّدتان لحد الآن: `hincrbyfloat` (`ai_agents`، موثَّق في `silent-write-regression-session-log.md`) و`setnx` (`projects.add_contribution`، موثَّق في هذه الجلسة) — **نفس النمط بالحرف**: الكود بيفترض الـwrapper بتوفّر method قياسية من مكتبة `redis` الأصلية، لكن `RedisClientWrapper` بتعرّف subset بس. يستاهل جرد شامل لكل استدعاءات `self.redis.<method>` عبر المشروع مقارنة بتعريف `RedisClientWrapper` نفسه، بدل ما تتكتشف واحدة واحدة.
8. **`user-repository-get-user-audit`** (جديدة، اسم مقترَح، فئة مستقلة عن بند 1) — **جرد `grep` كامل مؤكَّد (مش استنتاج)**: `.get_user(` عبر `app/` كله رجّع 6 مواضع بنفس الباج (`UserRepository.get_user()` **غير موجودة أصلًا**، الصح `get_by_id` بمعامل `tenant_id` إجباري كمان): `communications/service.py:29`، `communications/service.py:36`، `digital_twin/service.py:51`، `employment/service.py:89`، `health/service.py:54`. (موضع سابع، `identity/service.py:238`، اتفحص واتأكَّد إنه **صحيح مش باج** — بينادي method حقيقية على `UserService` نفسها). الجدول الكامل + التفاصيل في القسم "📌 ملاحظة منفصلة — `UserRepository.get_user()` غير موجودة أصلًا" فوق مباشرة.
9. **`saas-control-service-missing-methods`** (جديدة، اسم مقترَح) — `SaaSControlService` معندهاش `get_active_subscription` (مستخدَمة في `digital_twin._check_saas_limits`، مؤكَّدة حيًا بـ`AttributeError` فعلي). يحتاج جرد لباقي الاستخدامات المشابهة عبر المشروع (بنفس منهجية بند 7). **🔴🔴 تحذير صريح [2026-08-17] — إلزامي قبل أي إصلاح لهذا البند:** `get_active_subscription` هي نفسها اللي بتحجب (بالصدفة، مش بتصميم آمن) ثغرة حرجة موثَّقة في `invitations.accept_invitation` (يوزر حقيقي بلا محفظة بيتسجَّل على القرص فعليًا — راجع `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`). **قبل إصلاح `get_active_subscription`، يجب أولاً إصلاح أو على الأقل مراجعة التقرير الحرج ده كاملًا** — وإلا فإن إصلاح هذا البند وحده سيفتح ثغرة تسجيل هوية فورية (يوزر `id=52`، `p_ctor_inv_newuser@eppne.com`، هو الدليل الحي). راجع القسم البارز أعلى هذا الملف مباشرة لتفاصيل قرار الأولوية الكامل.
10. **`affiliate-service-missing-methods`** (موثَّقة سابقًا في `transaction-savepoint-bug-session-log.md`، مُعاد تأكيدها هنا) — `AffiliateService` معندهاش `get_user_by_code` ولا `register_commission`، بتمنع `_register_affiliate_commission` في عدة دومينات (`digital_twin` من ضمنهم) من العمل بالكامل.
11. **`realestate-invoicing-savepoint-conflict`** (جديدة، اسم مقترَح، أولوية عالية) — `realestate.buy_fractional_ownership`/`rent_unit` بينادوا `invoicing.create_invoice` (لسه بتعمل `commit()` مباشر عمدًا) من جوه `begin_nested()` بتاعتهم، فبيكسروا الـSAVEPOINT — مؤكَّد بالتنفيذ الفعلي. **كُشف بسبب إصلاح constructor في هذه الجلسة** (كانت الدالتان محجوبتين بالكامل قبل كده). تفاصيل كاملة في القسم أعلاه مباشرة. **🔴🔴 تحديث [2026-08-17] — امتداد أشد خطورة مؤكَّد حيًا:** نفس فئة الباج بالضبط اتكشفت في `invitations.accept_invitation` (سطر 286) عبر `UserService.register()` → `UserRepository.create()`/`WalletRepository.create()` (بدل `InvoicingService`) — **هنا التبعة أوقع بكتير: يوزر حقيقي بيتسجَّل فعليًا على القرص (`commit()` نجح) بلا محفظة، والدعوة نفسها فضلت مش مقبولة، والمستخدم بياخد `500` بلا ما يعرف إن حساب اتسجَّل باسمه.** **تصحيح [2026-08-17]: العبارة "مش rollback آمن زي realestate" هنا كانت غير دقيقة** — تحقق لاحق (تحديث ثالث تحت) أثبت إن `realestate` نفسها بتتبع **نفس نمط "دفع بلا سجل" بالضبط**، مش نمط أأمن. **دي حالة بيانات يتيمة حقيقية على القرص، من نفس فئة باقي الحالات، مش استثناء.** تفاصيل كاملة في القسم الجديد "🔴🔴 [2026-08-17] اكتشاف حرج" تحت مباشرة. **يستاهل جلسة منفصلة عاجلة جدًا** — أعلى أولوية من كل بنود هذا الـBacklog، بما فيها البند نفسه بصيغته الأصلية.

**🔴🔴 تحديث ثانٍ [2026-08-17] — تأكيد حي مزدوج من `insurance`، أول تكرار للنسخة الأصلية (`InvoicingService`) منذ `realestate`:** جدول الأدلة لدومين `insurance` كشف (بالقراءة، قبل أي تحقق حي) إن `subscribe` **و**`review_claim` **الاتنين** بينادوا `finance.transfer()` + `invoicing_service.create_invoice()` من جوّه `begin_nested()` بتاعتهم — **مؤكَّد حيًا بالتنفيذ الفعلي لسكريبتين معزولين مستقلين، الاتنين بنفس التوقيع بالحرف:**
```
finance.transfer() OK -> tx_hash=..., status=COMPLETED
...
File "invoicing/repository.py", line 30, in create_invoice
    await self.db.refresh(invoice)
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager.
```
**تحقق DB مستقل (session منفصلة، قبل/بعد) لكل من الحالتين:**
| الحالة | المبلغ | الطرفان | الفاتورة | النتيجة النهائية |
|---|---|---|---|---|
| `subscribe` | 15 MR_USDT | user 56 → user 57 (`entity_3@eppne.com`) | 🔴 اتحفظت فعليًا (`id=7, status=PENDING`) | **`insurance_subscriptions` = صفر صف — الاشتراك ما اتسجَّلش أبدًا رغم دفع القسط** |
| `review_claim` | 50 MR_USDT | user 3 (المراجع) → user 56 (المطالب) | 🔴 اتحفظت فعليًا (فاتورة ثانية، العدّ زاد لـ2) | **الحالة فضلت `SUBMITTED`، `approved_amount_mrusdt` لسه فاضي — التعويض اتصرف فعليًا لكن المطالبة رسميًا لسه "مقدَّمة" مش "مدفوعة"** |

**نفس فئة "دفع بلا استلام خدمة" المكتشفة في `arbitration_syndicates.join_syndicate`، لكن دي **ثالث ورابع حالة حية مؤكَّدة في نفس الجلسة** (`invitations`=هوية، `arbitration_syndicates`=عضوية، `insurance`×2=اشتراك+تعويض) — **يرفع هذا البند لأعلى أولوية ممكنة، نمط منهجي مؤكَّد عبر 4 دومينات مختلفة على الأقل، مش حالة استثنائية.** صفر إصلاح، توثيق فقط. تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md` (قسم `insurance`).

**🔴🔴 تحديث ثالث [2026-08-17] — نمط واحد مؤكَّد (مش نمطين)، بدليل مباشر من الكود، + توصية تصميمية لحل مستقبلي:**

اتفحص (بطلب صريح) هل `realestate`/`arbitration_syndicates` بتنشئ السجل التجاري الأساسي **قبل** `create_invoice` (نمط أخف، فاتورة يتيمة بس) بعكس `insurance` (نمط أخطر، دفع بلا سجل). **التحقق المباشر من الكود الفعلي (`grep`، مش افتراض) نفى الفرضية دي بالكامل:**
```
realestate.buy_fractional_ownership:        create_invoice (244) ← قبل ← create_ownership (255)
arbitration_syndicates.join_syndicate:      create_invoice (351) ← قبل ← create_membership (363)
insurance.subscribe:                        create_invoice (207) ← قبل ← create_subscription (219)
```
**الثلاثة دومينات كلهم — بما فيهم `realestate` نفسها — بنفس الترتيب بالضبط.** مؤكَّد كمان بالتنفيذ الفعلي: السكريبت المعزول الأصلي لـ`realestate.buy_fractional_ownership` (التشغيلة الأولى، `create_invoice` حقيقية بلا تخطي) خلَّف نفس الأثر بالظبط — فاتورة حقيقية اتحفظت + تحويل مالي حقيقي (`TX-4B6F54E8B37C`)، **بصفر `property_ownerships` مقابل** (الصف اللي ظهر لاحقًا كان من تشغيلة تانية منفصلة تخطَّت `create_invoice` بالكامل). **يعني `realestate` مكانتش استثناء آمن من الأساس — كانت نفس فئة "دفع بلا سجل" زي `insurance` بالظبط، بس ده متلاحظش صراحة وقتها.**

**الخلاصة النهائية: نمط واحد مؤكَّد فقط عبر كل الحالات الأربعة الحية** (`realestate`, `arbitration_syndicates`, `insurance`×2) — `create_invoice` بتتنادى **قبل** السجل التجاري الأساسي دايمًا، فأي كراش داخل `create_invoice` (Backlog #14 الممتد) بيسيب فلوس حقيقية اتحركت بلا أي سجل خدمة مقابل. **صفر دليل على وجود نمط "أسجل-قبل-فاتورة" أأمن في أي دومين اتفحص لحد الآن في هذه الجلسة.**

**توصية تصميمية لحل مستقبلي (مستقلة عن السؤال أعلاه، صالحة بغض النظر عن نتيجته):** أحد الاتجاهات المحتملة لجلسة الإصلاح القادمة هو **نقل استدعاء `create_invoice` ليحصل دايمًا بعد إنشاء/تحديث السجل التجاري الأساسي** (مش قبله) في كل الدومينات المتأثرة — كده لو `create_invoice` كراشت (لحد ما Backlog #14 يتصلح)، أسوأ نتيجة تبقى "فاتورة يتيمة" (ضرر محدود، قابل للتصحيح اليدوي) بدل "دفع حقيقي بلا أي سجل خدمة" (الحالة الحالية في كل مكان). **ده حل تخفيفي مؤقت، مش بديل عن إصلاح Backlog #14 نفسها (audit_log جوه create_invoice) اللي هي السبب الجذري الحقيقي.**

**🔴 تحديث رابع [2026-08-17]، مؤكَّد بالقراءة من `tourism_sports.submit_transfer_bid`:** التوصية التصميمية أعلاه **موجودة فعليًا كنمط حي في الكود** — `repo.create_transfer()` بتتنفَّذ **قبل** `invoicing.create_invoice()` جوّه نفس الـ`begin_nested()` (سطور 433 و444). **لو الـkwarg صح** (هنا `entity_id=` صحيح)، وكان الـcommit الداخلي لـ`create_invoice` ناجح، هيسحب معاه الـ`transfer` الـflush-only فيتحفظ فعليًا — يعني **أخف ضررًا من نمط `insurance`/`arbitration_syndicates`/`realestate` الأصلي.** غير مؤكَّد حيًا بعد (يحتاج تحقق DB-level منفصل)، وده أول مثال فعلي لنمط "سجل قبل فاتورة" يُكتشف في الجلسة — **توثيق فقط، صفر تغيير على الخلاصة السابقة إن النمط السائد في باقي الحالات هو invoice-before-record.**
12. **`saas-control-service-wrong-arity-call`** (جديدة، اسم مقترَح، فئة مستقلة عن بند 9) — `service_marketplace._check_saas_limits` (سطر 70) بتنادي `saas_service.can_access_service(tenant_id, "service_marketplace")` **بمعاملين**، لكن التوقيع الحقيقي (`saas/service.py:209`) `can_access_service(self, service_code: str) -> bool` **بياخد معامل واحد بس بعد `self`** — `tenant_id` بقى جوه الـconstructor نفسه (`self.tenant_id`) بعد إعادة الهيكلة اللي فرضها إصلاح `constructor-mismatch`. **مؤكَّد بالتنفيذ الفعلي** (`TypeError: SaaSControlService.can_access_service() takes 2 positional arguments but 3 were given`، عبر `POST /api/marketplace/purchase` حقيقي). **فئة جديدة: "wrong-arity call بعد تغيير توقيع method" — مختلفة عن بند 9 (method غير موجودة أصلًا)، هذه method موجودة لكن استدعاؤها لم يتحدّث بعد نقل `tenant_id` للـconstructor.** الاستدعاء الخاطئ **موجود من قبل** أي ديف في جلسة `constructor-mismatch` (كنا بس بدّلنا `self.saas_service` بمتغيّر محلي `saas_service`، نفس المعاملين الخاطئين ورثهم الديف بالحرف) — **صفر إصلاح تم أو هيتم على هذا الاستدعاء في جلسة `constructor-mismatch`، خارج نطاقها بالكامل.** **⚠️ تنبيه لأي جلسة مستقبلية:** نفس الفئة محتمل تتكرر في أي دومين تاني بينادي `SaaSControlService.can_access_service` بمعاملين (نفس النمط القديم) بعد نفس إعادة الهيكلة — يشمل بالذات الدومينات اللي اتلمست في هذه الجلسة نفسها (`realestate` عبر `_check_saas_limits` بتستخدم `get_active_subscription` مش `can_access_service`، فمش متأثرة بنفس الاستدعاء تحديدًا؛ `digital_twin` نفس الحال — لكن **صفر تأكيد فعلي لسه لأي دومين تاني، يحتاج `grep` شامل مخصَّص لاحقًا**، غير مُنفَّذ في هذه الجلسة).

**🔴 تحديث [2026-08-17]، متغيّر جديد مؤكَّد حيًا من الدفعة 3 (`app/api/deps.py:207`, `require_subscription`):** نفس فئة الباج بالضبط (`tenant_id` بقى جوه الـconstructor فبقى أي استدعاء بمعاملين هيفشل)، لكن **على method مختلفة تمامًا** — `check_and_enforce_access(service_code)` (مش `can_access_service`). الاستدعاء الفعلي: `service.check_and_enforce_access(current_user.tenant_id, service_code)` — التوقيع الحقيقي (`saas/service.py:233`) بياخد `service_code` بس. `check_and_enforce_access` نفسها بتنادي `can_access_service` داخليًا (بلا `tenant_id`، عبر `self.tenant_id`). **مؤكَّد بالتنفيذ الفعلي عبر HTTP حقيقي على endpoint من دومين `affiliate` (`POST /affiliate/links`) وendpoint من دومين `academy` (`POST /academy/courses`)** — نفس الخطأ بالحرف على الاتنين: `TypeError: SaaSControlService.check_and_enforce_access() takes 2 positional arguments but 3 were given`. **هذا الموضع مشترك (dependency واحدة، `require_subscription`) بيأثر على 7 endpoints عبر دومينين (`affiliate` ×5، `academy` ×2) دفعة واحدة** — تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md`. **صفر إصلاح على هذا الاستدعاء تحديدًا (خارج نطاق constructor-mismatch الصارم)، فقط إصلاح الـconstructor نفسه تم في نفس الجلسة.**
13. **`invoicing-create-invoice-wrong-kwarg`** (جديدة، اسم مقترَح) — `service_marketplace.purchase_service` (سطر 203) بتنادي `invoice_service.create_invoice(tenant_id=buyer_tenant_id, ...)` لكن التوقيع الحقيقي (`invoicing/service.py:51`) اسم المعامل **`entity_id`** مش `tenant_id` — `TypeError` مؤكَّد بالتنفيذ الفعلي (سكريبت معزول). **موجود من قبل جلسة `constructor-mismatch` بالحرف** (الديف بدّل `self.invoice_service` بمتغيّر محلي بس، صفر لمس على أسماء الـkwargs). يستاهل `grep` شامل لباقي استدعاءات `invoice_service.create_invoice`/`self.invoicing.create_invoice` عبر المشروع (`realestate`, `arbitration_syndicates`, وغيرهم من الـ12 دومين اللي بتستخدم `InvoicingService`) للتأكد هل نفس الـkwarg الخطأ متكرر في أماكن تانية — **غير مُنفَّذ في هذه الجلسة**. **🔴🔴 تحديث حرج [2026-08-17]، مؤكَّد حيًا من `manufacturing.start_production`:** المشكلة **أعمق وأوسع أثرًا مما كان موثَّق** — حتى لما الاستدعاء الخارجي يبقى **صحيح 100%** (`entity_id=tenant_id`، زي `manufacturing`/`invitations`)، `InvoicingService.create_invoice()` **نفسها** بتكراش داخليًا عند سطرها الأخير: `await audit_log(user_id=..., tenant_id=entity_id, action=..., resource_id=invoice.id, details=...)` (`invoicing/service.py:90-96`) — نفس فئة Backlog #14 بالضبط (`audit_log` معندهاش `tenant_id`/`resource_id`)، **لكن جوه `InvoicingService` نفسها، مش عند أي call site خارجي**. **الأثر: أي دومين في المشروع كله بينادي `create_invoice` بشكل صحيح هيكراش برضه**، بعد ما فاتورة حقيقية **اتحفظت فعليًا على القرص** (`repo.create_invoice()` بتعمل `commit()` قبل استدعاء `audit_log` المكسور — مؤكَّد بمثال حي: `invoices id=5, tenant_id=1, user_id=53, amount=1.00, status=PENDING` اتحفظت فعليًا رغم الكراش اللي بعدها). **فاتورة "معلَّقة" (dangling) حقيقية — مستند مالي موجود، لكن العملية اللي أنشأته (هنا: بدء إنتاج batch) فشلت وما اكتملتش.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md` (قسم `manufacturing`).

**🔴🔴🔴 تحديث حرج ثانٍ [2026-08-17]، مؤكَّد حيًا من `arbitration_syndicates.join_syndicate` — الميكانيكية دقيقة أوضح، والأثر المالي أوقع من مجرد "فاتورة معلَّقة":**

`InvoicingRepository.create_invoice()` (`invoicing/repository.py:22-31`) فيها تعليق تحذيري موجود بالفعل من جلسة `transaction-savepoint-bug-session-log.md` بيسمّي `arbitration_syndicates.join_syndicate` **بالاسم صراحة** كمثال assumed-safe: *"هذا الـcommit() بيغطي كمان كتابات finance.transfer() جوه service methods تانية (زي arbitration_syndicates.join_syndicate) بتنادي InvoicingService.create_invoice بعد finance.transfer مباشرة"* — يعني الـcommit المباشر ده **تصميم متعمَّد** (حماية بالصدفة لـ`finance.transfer()`'s flush-only writes)، **مش باج في حد ذاته**.

**لكن المؤكَّد حيًا الآن (سكريبت معزول، `finance.transfer` حقيقي + `create_invoice` حقيقي، تخطينا `_check_saas_limits` بس):**
```
finance.transfer() OK -> tx_hash=TX-28F62897CA56, status=COMPLETED
invoice_service.create_invoice() FAILED as predicted (Backlog #13/#14-extended): TypeError: audit_log() got an unexpected keyword argument 'tenant_id'
```
**تحقق DB مستقل (session منفصلة تمامًا، قبل/بعد):**
| الجدول | قبل | بعد |
|---|---|---|
| `wallets` (المشترك، user 54) | `{"MR_USDT": 200}` | 🔴 **`{"MR_USDT": 180.0}`** — **خصم حقيقي، اتحفظ فعليًا** |
| `wallets` (الخزينة، user 55) | `{}` | 🔴 **`{"MR_USDT": 20.0}`** |
| `transactions` (sender=54) | 0 صف | **1 صف، `status=COMPLETED`** |
| `invoices` (user=54) | 0 صف | **1 صف** (نفس نمط `manufacturing` — الحماية بالصدفة اشتغلت لجزئها) |
| `syndicate_memberships` (member=54) | 0 صف | **0 صف — العضوية اتحفظتش أبدًا** |

**الخلاصة (أهم من `manufacturing`):** الحماية بالصدفة (`create_invoice`'s commit) **اشتغلت بالظبط زي ما كانت متصمَّمة** — غطّت `finance.transfer()`'s flush-only ونجحت في تثبيت الفاتورة. **لكن Backlog #14 (audit_log جوه create_invoice نفسها) بيكسر باقي العملية بعدها مباشرة** — النتيجة النهائية: **رسم عضوية حقيقي اتخصم من محفظة المستخدم وتحوَّل للخزينة، فاتورة حقيقية اتسجَّلت، لكن العضوية نفسها ما اتمنحتش أبدًا** — طالب الـendpoint هياخد `500` واضح، بس فلوسه راحت فعليًا بلا خدمة مقابلها. **فئة "دفع بلا استلام خدمة" — نفس خطورة اكتشاف `invitations` (يوزر بلا محفظة)، لكن هنا مالي مباشر بدل هوية.** **صفر إصلاح، توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md` (قسم `arbitration_syndicates`).

**⚠️ ملاحظة منهجية مهمة لأي تحقق حي مستقبلي:** الفرق بين "rollback آمن بالكامل" (زي `service_marketplace.purchase_service`، اللي فيها اسم الـkwarg غلط `tenant_id=` بدل `entity_id=`، فـ`create_invoice`'s body **ما بينفّذش أصلًا**، فصفر commit يحصل) و"كتابة جزئية حقيقية" (زي `manufacturing`/`arbitration_syndicates`، اللي فيها الـkwarg صح، فـ`create_invoice`'s body بينفّذ كامل شامل الـcommit الداخلي، **وده بيسحب معاه أي flush-only pending من نفس الـsession قبله**) — **بيعتمد بالكامل على صحة اسم الـkwarg عند نقطة الاستدعاء، مش على نوع العملية نفسها.** لازم `SELECT` مستقل بعد أي تحقق حي، **حتى لو الاستدعاء الخارجي شكليًا "صحيح"**.
14. **`audit-log-wrong-kwargs`** (جديدة، اسم مقترَح، أولوية عالية — بتأثر على أي دومين بينادي `audit_log` بنفس الأسلوب) — `service_marketplace.purchase_service` (سطر 236-247) بتنادي `audit_log(user_id=..., tenant_id=buyer_tenant_id, action=..., resource_id=license_obj.id, details=...)` لكن التوقيع الحقيقي (`core/audit.py:12-17`) `audit_log(action: str, user_id=None, details=None, ip_address=None)` — **معندهاش `tenant_id` ولا `resource_id` إطلاقًا**، الاستدعاء بيمرر **معاملين غير موجودين** مرة واحدة. `TypeError: audit_log() got an unexpected keyword argument 'tenant_id'` — مؤكَّد بالتنفيذ الفعلي (سكريبت معزول، بعد تخطي باجَي #12 و#13). **موجود من قبل جلسة `constructor-mismatch` بالحرف، صفر لمس من ديفنا.** **فئة رابعة مستقلة** ("wrong-kwarg call على دالة عامة/utility، مش service class") — مختلفة عن #12 (wrong-arity) و#13 (wrong-kwarg-name على service method). **بالنظر لطبيعة `audit_log` كدالة utility عامة مُستخدَمة عبر عشرات الدومينات**، يستاهل أولوية عالية جدًا لـ`grep` شامل (`audit_log(` عبر `app/` كله) لمعرفة كام موضع تاني بيمرر `tenant_id`/`resource_id` بنفس الطريقة الخاطئة — **غير مُنفَّذ في هذه الجلسة، بقرار صريح من المستخدم بالتوقف فور اكتشاف هذا الباج الرابع وعدم ملاحقة المزيد ضمن نفس الجلسة.** **🔴🔴 تحديث حرج [2026-08-17]، مؤكَّد حيًا من `manufacturing.start_production`:** الباج **مش محصور في مواضع الاستدعاء الخارجية بس** (زي `service_marketplace`/`invitations`/`manufacturing` نفسها) — **`InvoicingService.create_invoice()` نفسها بتنادي `audit_log(tenant_id=..., resource_id=...)` داخليًا** (`invoicing/service.py:90-96`)، يعني **حتى الاستدعاءات الخارجية الصحيحة 100% (بـ`entity_id=`) بتكراش برضه**، جوه `create_invoice` نفسها بعد ما الفاتورة تتحفظ فعليًا على القرص. تفاصيل كاملة + مثال حي (`invoices id=5`) في تحديث Backlog #13 فوق مباشرة وفي `.claude/reports/constructor-mismatch-session-log.md` (قسم `manufacturing`).
15. **`ai-governance-check-and-consume-wrong-kwarg`** (جديدة، اسم مقترَح، فئة "wrong-kwarg بعد نقل tenant_id للـconstructor" — نفس عائلة Backlog #12) — مؤكَّدة حيًا من `manufacturing.start_production` (سكريبت معزول): `governance.check_and_consume(tenant_id=tenant_id, agent_id=4, user_id=user_id, action_type=..., tokens=150, cost=...)` لكن التوقيع الحقيقي (`ai_governance/service.py:140-150`) `check_and_consume(self, agent_id, user_id, action_type, tokens, cost, idempotency_key=None, request_tokens=0, completion_tokens=0)` — **معندهاش `tenant_id` إطلاقًا** (بقت جوه الـconstructor، `self.tenant_id`، زي `SaaSControlService.can_access_service`). `TypeError: AIGovernanceService.check_and_consume() got an unexpected keyword argument 'tenant_id'`. **🔴 خطورة إضافية: هذا الاستدعاء في `manufacturing.start_production`/`analyze_and_schedule_maintenance` (وعلى الأرجح دومينات تانية كتير بتستخدم `AIGovernanceService.check_and_consume`) غير ملفوف بـ`try/except` في الكود الحقيقي** (بعكس استدعاء `ai_service.execute_agent_action` المجاور اللي ملفوف) — يعني في الكود الحقيقي (مش سكريبتنا اللي لفّيناه بـtry/except لأغراض الاستكشاف)، هذا الباج **هيوقف الـendpoint بالكامل فورًا**، مش تحذير يُتجاوَز. **موجود من قبل جلسة `constructor-mismatch`، صفر لمس.** يستاهل `grep` شامل لكل استدعاءات `check_and_consume(` عبر المشروع.

**🔴 تحديث دقيق [2026-08-17]، مؤكَّد بالقراءة المباشرة من `arbitration_syndicates.create_dispute` (سطر 96-103) — باج مركَّب حقيقي، مش نفس نمط `manufacturing` بالتكرار البسيط:**

الاستدعاء الفعلي في `arbitration_syndicates/service.py`:
```python
governance = AIGovernanceService(self.db)  # (قبل ديف constructor-mismatch — بعد الديف: AIGovernanceService(self.db, tenant_id))
await governance.check_and_consume(  # type: ignore
    tenant_id=tenant_id,
    agent_id=11,
    user_id=claimant_id,
    tokens=500,
    cost=Decimal("0.05")
)
```
مقارنة دقيقة بالتوقيع الحقيقي `check_and_consume(self, agent_id: int, user_id: int, action_type: str, tokens: int, cost: Decimal, idempotency_key=None, request_tokens=0, completion_tokens=0)`:
1. **`tenant_id=tenant_id`** — كيوورد **زيادة غير موجود** في التوقيع (نفس الفئة الأصلية المسجَّلة من `manufacturing`).
2. **`action_type`** — بارامتر **إجباري بلا default**، **غير ممرَّر إطلاقًا** في هذا الاستدعاء (لا كـkeyword ولا positional) — **مفقود بالكامل، مش مجرد اسم غلط**.

**يعني هذا الاستدعاء تحديدًا فيه خطأين مستقلين مجتمعين في نفس الاستدعاء الواحد:** كيوورد زيادة (`tenant_id`) + معامل إجباري ناقص (`action_type`). لو افترضنا نظريًا إن `tenant_id` اتشالت، الاستدعاء **هيفضل يفشل** بـ`TypeError: check_and_consume() missing 1 required positional argument: 'action_type'` — يعني إصلاح كيوورد الـ`tenant_id` وحده **مش كافٍ** لتصحيح هذا الاستدعاء بالذات، على عكس استدعاءات `check_and_consume`/`execute_agent_action` التانية (زي `manufacturing`) اللي مشكلتها محصورة في `tenant_id` بس. **باج مركَّب مستقل يستاهل تسجيل منفصل، مش وصف "نفس النمط" المبسَّط.** **غير ملفوفة بـ`try/except`** (زي `manufacturing`) — هتوقف `create_dispute` بالكامل فورًا. **صفر إصلاح، توثيق فقط.**
16. **`ai-agents-execute-agent-action-wrong-kwarg`** (جديدة، اسم مقترَح، نفس العائلة) — مؤكَّدة حيًا من نفس السكريبت: `ai_service.execute_agent_action(agent_id=4, tenant_id=tenant_id, action_type=..., payload=..., executor_user_id=user_id)` لكن التوقيع الحقيقي (`ai_agents/service.py:147-154`) `execute_agent_action(self, agent_id, action_type, payload, executor_user_id, idempotency_key)` — **معندهاش `tenant_id`** (بقى جوه الـconstructor)، **و`idempotency_key` بقت `required` بلا default، والاستدعاء في `manufacturing` مبيمررهاش أصلًا** (باج مزدوج: kwarg زيادة + معامل إجباري ناقص). `TypeError: AIAgentsService.execute_agent_action() got an unexpected keyword argument 'tenant_id'`. **هذا الاستدعاء تحديدًا ملفوف بـ`try/except Exception` في الكود الحقيقي (`manufacturing/service.py`)، فبيتلبع بهدوء ويكمل التنفيذ** — مؤكَّد حيًا (اللوج: "AI analysis failed, proceeding without"). **مختلف عن #15 في الأثر (هنا محمي بالصدفة، #15 مش محمي)، لكن نفس فئة الباج.** يستاهل `grep` شامل لكل استدعاءات `execute_agent_action(` عبر المشروع لمعرفة كام موضع محمي وكام موضع مكشوف.
17. **`arbitration-case-model-idempotency-key-mismatch`** (جديدة، اسم مقترَح، فئة مختلفة تمامًا — "repository بيمرر kwarg مش موجود على موديل SQLAlchemy") — مؤكَّدة حيًا من سكريبت معزول لـ`arbitration_syndicates.create_dispute`: `repo.create_case(idempotency_key=idempotency_key, ...)` (`arbitration_syndicates/service.py:120-128`) بينادي `ArbitrationCaseRepository.create_case(self, **kwargs)` (`repository.py:12-17`) اللي بتعمل `ArbitrationCase(**kwargs)` مباشرة — **لكن موديل `ArbitrationCase` (`models.py:36-56`) معندوش عمود `idempotency_key` إطلاقًا** (بعكس 4 موديلات تانية في نفس الملف عندها العمود ده فعليًا: `SyndicateMembership`, وغيرهم). `TypeError: 'idempotency_key' is an invalid keyword argument for ArbitrationCase` — مؤكَّد بالتنفيذ الفعلي، **يحصل حتى لو كل الباجات التانية (#9، #15، #16) اتصلحت** — عائق مستقل تمامًا، **صفر علاقة بـ`constructor-mismatch` أو بأي فئة "wrong-kwarg بعد نقل tenant_id" السابقة**. **الأثر: `create_dispute` مستحيل تكمل حتى النهاية أبدًا** بشكلها الحالي — مش مجرد باج جانبي محجوب، دي عائق بنيوي (schema/repository mismatch) يمنع إنشاء أي قضية تحكيم إطلاقًا. **صفر إصلاح، توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md` (قسم `arbitration_syndicates`).
18. **`finance-service-create-invoice-does-not-exist`** (جديدة، اسم مقترَح، فئة مستقلة تمامًا — "استدعاء method غير موجودة إطلاقًا على FinanceService، مختلفة عن أي فئة سابقة من #9 لـ#17") — مؤكَّدة بالقراءة المباشرة (مش تخمين): `transport/service.py` بتنادي `self.finance.create_invoice(...)` في موضعين (`book_trip` سطر 355، `pay_delivery` سطر 529)، الاتنين معلَّمين بالفعل بـ`# type: ignore[attr-defined]` في الكود الأصلي — لكن `FinanceService` (`finance/service.py`) **معندهاش method اسمها `create_invoice` إطلاقًا** (`grep` شامل على الملف كله رجّع صفر نتيجة). **مختلفة عن Backlog #11/#13 (اللي عن `InvoicingService.create_invoice`)** — `transport` **معندهوش `InvoicingService` مُنشأة أصلًا** (صفر import، صفر `self.invoicing_service` في `__init__`)؛ الاستدعاء ببساطة بينادي method مش موجودة على الكلاس الغلط. `AttributeError: 'FinanceService' object has no attribute 'create_invoice'` (متوقَّع، لسه مش مؤكَّد بالتنفيذ الفعلي وقت كتابة هذا البند). **الخطورة: نفس شكل Backlog #11 (فلوس بتتحوّل فعليًا عبر `finance.transfer()` جوه نفس `begin_nested()`، ثم كراش فوري بعدها مباشرة بسبب الاستدعاء الغلط) — لكن السبب الجذري مختلف كليًا (method غير موجودة على الكلاس، مش commit مبكر يكسر SAVEPOINT).** **صفر إصلاح — خارج نطاق `constructor-mismatch` الصارم (احذف/ابنِ محليًا فقط)، بقرار صريح من المستخدم بالتوثيق والاستمرار.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md` (قسم `transport`).
19. **`cross-tenant-scheduled-task-vs-constructor-mismatch`** (جديدة، اسم مقترَح، فئة مستقلة تمامًا — "تعارض معماري حقيقي بين مهام Celery مصمَّمة أصلًا لتعمل عبر كل المستأجرين، ومتطلب `tenant_id: int` الإجباري في constructor بعد إعادة الهيكلة") — مؤكَّدة بالقراءة المباشرة، 8 مواضع عبر ملفين: `app/tasks/saas_tasks.py` (5 دوال: `process_auto_renewals_task`, `generate_monthly_invoices_task`, `check_expired_trials_task`, `send_trial_expiry_reminders_task`, `cleanup_cancelled_subscriptions_task`) و`app/tasks/governance.py` (3 دوال: `reset_expired_quotas`, `cleanup_old_consumption_logs`, `generate_usage_report_task`) — **صفر `tenant_id` في توقيع أي دالة `_task`** (`generate_usage_report_task` وحدها فيها `tenant_id: Optional[int] = None`، بتصميمها تدعم "تقرير لكل المستأجرين" لو `None`). **دليل قاطع من `process_auto_renewals`** (الوحيدة اللي method بتاعتها موجودة فعليًا على `SaaSControlService`): `async def process_auto_renewals(self, tenant_id: Optional[int] = None)` → `target_tenant = tenant_id if tenant_id is not None else self.tenant_id` → `repo.get_subscriptions_for_renewal(target_tenant)` اللي بتفلتر بكل المستأجرين لو `tenant_id=None`. **التاسك بينادي `service.process_auto_renewals()` بصفر معاملات** — يعني بيعتمد كليًا على `self.tenant_id` من الـconstructor. **لو الـconstructor اتصلح بأي `tenant_id` واحد ملموس (زي ما بيتطلبه توقيعه الحالي)، الـtask هيفضل شغّال لكن هيقتصر تجديد الاشتراكات على مستأجر واحد بس بدل كل المستأجرين — رجوع صامت في السلوك، مش مجرد كراش واضح.** **الأربعة الباقية في `saas_tasks.py` والثلاثة في `governance.py` محجوبة بالكامل بباج مستقل (method غير موجودة على `SaaSControlService`/`AIGovernanceService`، فئة #9 بأسماء مختلفة تمامًا: `generate_monthly_invoices`, `check_and_expire_trials`, `send_trial_expiry_reminders`, `cleanup_cancelled_subscriptions`, `reset_expired_quotas`, `cleanup_old_logs`, `generate_usage_report`) — إصلاح الـconstructor هنا لن يُغيّر النتيجة الفعلية إطلاقًا. **صفر إصلاح — قرار صريح من المستخدم بالتوثيق فقط بدون `Edit` على هذه الـ8 مواضع.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 5، مجموعتا أ وب).
**🔴 تحديث [2026-08-17] — موضع تاسع بنفس الفئة بالحرف:** `app/domains/invoicing/router.py:330` (`POST /invoicing/admin/process-overdue`، `process_overdue_invoices`) — endpoint إداري موثَّق صراحة في الكود إنه "يُستخدم من Celery" لمعالجة **كل** الفواتير المتأخرة عبر **كل** المستأجرين. **صفر `tenant_id` متاح في نطاق الـendpoint إطلاقًا** (`get_current_superuser` مُستخدَمة كـdependency تفويض بس، مش كمصدر بيانات). التوقيع الحقيقي `process_overdue_invoices(self, tenant_id: Optional[int]=None) -> int` (`invoicing/service.py:297`) بيدعم "كل المستأجرين" لو `tenant_id=None`، والـendpoint بينادي `service.process_overdue_invoices()` بصفر معاملات — بيعتمد كليًا على `self.tenant_id`. **نفس التعارض بالحرف: إصلاح الـconstructor بأي `tenant_id` ملموس هيحصر معالجة الفواتير المتأخرة على مستأجر واحد بس بدل كل المستأجرين.** **صفر إصلاح — نفس القرار، توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 10).
20. **`missing-tenant-id-in-background-task-signature`** (جديدة، اسم مقترَح، فئة مستقلة — "استثناء تصميمي جديد كليًا، مختلف عن كل استثناءات tenant_id-object-attribute المعتمَدة سلفًا") — مؤكَّدة بالقراءة المباشرة: `app/tasks/affiliate.py:102` (`release_commissions_task(self, user_id: int, idempotency_key: str)`) — **صفر `tenant_id` في التوقيع، وصفر أي كائن متاح في نطاق الدالة يحمل `tenant_id`** (على عكس `job.tenant_id`/`farm.tenant_id`/`license_obj.tenant_id` — دي كلها كانت عن كائن SQLAlchemy متاح فعليًا جوه الدالة). المصدر الوحيد الممكن نظريًا هو استعلام إضافي `UserRepository.get_by_id(user_id)` لجلب `tenant_id` — **لكن `get_by_id` نفسها من ضمن Backlog #1 المعروف بمشاكلها** (معامل `tenant_id` ناقص في كل استخداماتها الحالية عبر المشروع). **صفر إصلاح — قرار صريح من المستخدم بالتوثيق فقط، صفر محاولة lookup بديلة.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 5، مجموعة د).
21. **`billing-tasks-saas-subscription-import-error`** (جديدة، اسم مقترَح) — 🔴 **مُصنَّفة كـ"حاجب على مستوى الموديول" (module-level blocker)** — فئة مستقلة **أعلى أولوية من التصنيف العادي** (زي #9-#18)، لأنها **بتلغي فائدة أي إصلاح آخر جوه نفس الملف حتى تتحل**: مؤكَّدة بالتنفيذ الفعلي أثناء التحقق الحي لموضع `billing.py:219` (الدفعة 3): محاولة `from app.tasks.billing import _generate_invoices_for_tenant` بتكراش فورًا بـ`ImportError: cannot import name 'SaaSSubscription' from 'app.domains.saas.models'`. **السبب:** `app/tasks/billing.py:27` بتعمل `from app.domains.saas.models import SaaSSubscription` — **لكن الكلاس الحقيقي اسمه `TenantSubscription`** (`saas/models.py:55`)، `SaaSSubscription` **غير موجود إطلاقًا** في الملف. الاستيراد الفاشل ده مُستخدَم في 3 استعلامات JOIN منفصلة داخل `billing.py` (أسطر 63، 80، 96). **الأثر: الموديول `app/tasks/billing.py` بالكامل مستحيل يتحمَّل في أي Celery worker حقيقي** — يعني **كل** التاسكات فيه (`generate_monthly_invoices_task`, `process_twin_subscriptions_task`, وغيرهم) معطَّلة بالكامل عند مستوى الاستيراد، **بما فيها المواضع اللي أصلحناها فعليًا في هذه الجلسة (`billing.py:219`, `billing.py:349`)** — إصلاح الـconstructor فيهم صحيح ومؤكَّد بالتنفيذ الفعلي (بمعزل عن الموديول)، لكن **لن يُفعَّل عمليًا في أي بيئة Celery حقيقية إلا بعد حل هذا الحاجب أولًا**. **موجود من قبل جلسة `constructor-mismatch`، صفر علاقة بأي ديف فيها.** تم تخطي هذا الموضع أثناء التحقق الحي عبر استدعاء مباشر لـ`AIAgentsService`/`generate_monthly_invoice` بمعزل عن استيراد الموديول بالكامل — تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 7).
22. **`finance-transfer-tx-hash-type-mismatch`** (جديدة، اسم مقترَح — 🔴 تحديث [2026-08-17]: اسم مُعمَّم بعد تأكيد إنه نمط متكرر، مش باج منعزل، كان اسمها الأصلي `employment-payroll-transfer-tx-hash-type-mismatch`) — فئة "قيمة إرجاع غير متوافقة النوع مع عمود قاعدة البيانات" — مؤكَّدة بالتنفيذ الفعلي أثناء التحقق الحي لموضع `employment.py:334` (الدفعة 3، سكريبت معزول): `app/tasks/employment.py`'s `pay_payroll_task` بتعمل `tx_hash = await finance.transfer(...)` ثم `await repo.update_payroll_status(payroll_id, PayrollStatus.PAID, payment_tx_hash=tx_hash)` — **لكن `FinanceService.transfer()` بترجع كائن `Transaction` (ORM object) كامل، مش `str`** (`finance/service.py:147`: `return tx`) — بينما عمود `payroll_records.payment_tx_hash` **`VARCHAR`**. `DBAPIError: invalid input for query argument $2: expected str, got Transaction` — مؤكَّد بالتنفيذ الفعلي.
**🔴 مؤكَّد كنمط متكرر، مش حالة منعزلة:** نفس النمط بالحرف موجود في `realestate/service.py:239` (`buy_fractional_ownership`): `tx_hash = await finance.transfer(...)` ثم سطر 262 `purchase_tx_hash=tx_hash` — والعمود `property_ownerships.purchase_tx_hash` **`VARCHAR(100)`** برضه (مؤكَّد بالقراءة المباشرة من schema قاعدة البيانات). **`grep` شامل لنمط `tx_hash = await finance.transfer(` عبر المشروع كشف 8 ملفات بنفس الاستدعاء بالحرف:** `app/tasks/employment.py`, `transport/service.py`, `tourism_sports/service.py`, `insurance/service.py`, `arbitration_syndicates/service.py`, `service_marketplace/service.py`, `realestate/service.py`, `sovereign_entities/service.py` — **كل واحد فيهم بيسمّي المتغيّر `tx_hash` رغم إنه فعليًا كائن `Transaction` كامل**، وأي استخدام لاحق للمتغيّر ده كـstring (تمريره لعمود `VARCHAR`، أو تضمينه في رسالة/JSON بيتوقع نص) هيكرر نفس الباج. **لم يُفحَص كل الـ8 ملفات فرديًا لتأكيد نفس النتيجة (`realestate` و`employment` بس مؤكَّدان بالتنفيذ الفعلي لحد الآن)، لكن نمط الاستدعاء متطابق حرفيًا في الكل — يستاهل جرد شامل مخصَّص لتأكيد/نفي باقي الـ6 ملفات.** **موجود من قبل جلسة `constructor-mismatch`، صفر علاقة بأي ديف فيها** — أغلب هذه المواضع لم تكن ممكن توصل لهذا السطر أصلًا قبل إصلاح الـconstructor (كانت بتكراش فورًا عند إنشاء `FinanceService(db)` بمعامل ناقص). **صفر إصلاح.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 7).
**📌 ملاحظة جودة بيانات إضافية (مش باج كود مستقل، اكتشاف جانبي):** `digital_twin_configs id=1` (بيانات قائمة من قبل هذه الجلسة) عنده `subscription_monthly_mrusdt = NULL` — و`_process_twin_subscription_for_tenant`'s حلقة (`billing.py`) بتعمل `if monthly_fee > 0` **بلا حراسة `None`** — لو نُفِّذت هذه الحلقة فعليًا على بيانات فيها `NULL`، هتكراش بـ`TypeError: '>' not supported between instances of 'NoneType' and 'int'`. **موجود من قبل، صفر علاقة بالديف.**
23. **`invoicing-list-invoices-wrong-kwarg`** (جديدة، اسم مقترَح — متغيّر جديد ضمن عائلة #12/#15/#16: "wrong-kwarg/wrong-arity بعد نقل `tenant_id` للـconstructor"، هنا على `InvoicingService.list_invoices` تحديدًا) — مؤكَّدة بالقراءة المباشرة: `invoicing/router.py:150` (`GET /invoicing/invoices`) بتنادي `service.list_invoices(tenant_id=tenant_id, user_id=..., status=..., invoice_type=..., skip=..., limit=...)` — لكن التوقيع الحقيقي (`invoicing/service.py:132-139`) `list_invoices(self, user_id=None, status=None, invoice_type=None, reference_id=None, skip=0, limit=50)` **معندهاش `tenant_id` كباراميتر إطلاقًا** (بيستخدم `self.tenant_id` داخليًا). `TypeError: list_invoices() got an unexpected keyword argument 'tenant_id'` متوقَّع فور إصلاح الـconstructor. **صفر إصلاح — خارج نطاق `constructor-mismatch` الصارم، توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 10).
24. **`invoicing-get-invoice-stats-wrong-arity`** (جديدة، اسم مقترَح — متغيّر تانٍ ضمن نفس العائلة، على `InvoicingService.get_invoice_stats`) — مؤكَّدة بالقراءة المباشرة: `invoicing/router.py:307` (`GET /invoicing/stats`) بتنادي `service.get_invoice_stats(tenant_id)` — لكن التوقيع الحقيقي (`invoicing/service.py:274`) `get_invoice_stats(self) -> Dict[str, Any]` **صفر معاملات إطلاقًا** (بيستخدم `self.tenant_id` داخليًا بالكامل). `TypeError: get_invoice_stats() takes 1 positional argument but 2 were given` متوقَّع فور إصلاح الـconstructor. **صفر إصلاح — توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 10).
**📌 استثناء تصميمي جديد — "authorization-conditional None passthrough"** (مختلف عن كل استثناءات `object.tenant_id` السابقة — `service_marketplace.license_obj.tenant_id`, `insurance.policy.tenant_id`/`pension.tenant_id`, `employment.job.tenant_id`, `automation.workflow.tenant_id`): مؤكَّد في `invoicing/router.py` مواضع 2 و3 (`get_invoice`, `list_invoices`) — الـrouter بيحسب `tenant_id` محليًا بمنطق تفويض (authorization) شرطي: `None` لو `current_user.system_role in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]`، وإلا `current_user.tenant_id`. **الفرق الجوهري:** الاستثناءات السابقة كانت دايمًا عن **كائن SQLAlchemy متاح فعليًا** (`job.tenant_id` إلخ) — هنا المصدر **منطق تفويض محلي جوه الـrouter نفسه**، والقيمة الممكنة فعليًا تبقى `None` (مش قيمة بديلة زي `0`). **آمن وقت التشغيل تحديدًا لـ`InvoicingService`** (بعكس `SaaSControlService`/`AIGovernanceService`) لأن كل الـmethods المعنية (`get_invoice`, وداخليًا `list_invoices` عبر `self.tenant_id`) بتتعامل مع `tenant_id=None` بأمان (`target_tenant = tenant_id or self.tenant_id` أو مكافئها) — **لكنه لسه نمط جديد يستاهل تتبُّع منفصل لأي تكرار مستقبلي في دومينات/routers تانية بنفس منطق "admin bypass بيؤدي لـ`tenant_id=None` جوه الـconstructor".** تم تطبيقه بموافقة المستخدم الصريحة — تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 10).
25. **`invoicing-get-invoice-null-tenant-admin-bypass-broken`** (جديدة، اسم مقترَح — 🔴 رُفعت من "ملاحظة جانبية" لبند Backlog رسمي مرقّم [2026-08-17] بعد توصيف الأثر) — مؤكَّدة بالتنفيذ الفعلي أثناء التحقق الحي لموضع `get_invoice` (الدفعة 3، مسار `SUPER_ADMIN`): `InvoicingRepository.get_invoice(invoice_id, tenant_id)` (`invoicing/repository.py:33-39`) بتعمل `and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)` **بلا معالجة خاصة لـ`tenant_id=None`** — يعني لما `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` يطلب فاتورة (`tenant_id` بيتحسب `None` عمدًا من الـrouter، `invoicing/router.py:93`، عشان يسمح للأدمن يشوف فواتير أي مستأجر)، الاستعلام بيترجم لـ`Invoice.tenant_id IS NULL` وهي حالة مستحيلة (العمود `NOT NULL` دايمًا) → `404 Not Found` كاذب **حتى لو الفاتورة موجودة فعليًا**. **مختلف عن نمط `saas/repository.py`'s `get_subscriptions_for_renewal`** (اللي بتعامل `None` بشكل صحيح كـ"بلا فلتر"، `if tenant_id is not None: query.where(...)`).
**🔴 توصيف الأثر:** هذا مش مجرد باج تقني هامشي — **صلاحية `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` لعرض فواتير أي مستأجر (المصمَّمة عمدًا في الكود عبر منطق `tenant_id=None`) معطَّلة بالكامل حاليًا لكل فاتورة موجودة فعليًا** — أي محاولة إدارية لجلب فاتورة مستأجر تاني عبر `GET /invoicing/invoices/{id}` هترجع `404` كاذب دايمًا، بغض النظر عن وجود الفاتورة من عدمه. **وظيفة إدارية موثَّقة بالكود (السطر نفسه بيفترض دعم "شوف أي فاتورة")، لكنها غير قابلة للاستخدام فعليًا في الوضع الحالي.** **موجود من قبل جلسة `constructor-mismatch`، صفر علاقة بأي ديف فيها** — لم يكن ممكن اكتشافه قبل كده لأن `InvoicingService(db)` كانت بتكراش فورًا (constructor-mismatch الأصلي) قبل ما توصل لهذا المسار أصلًا. **صفر إصلاح، توثيق فقط.** تفاصيل كاملة في `.claude/reports/constructor-mismatch-batch3-session-log.md` (قسم 13).
**✅ تأكيد سلامة البيانات لكل محاولات `purchase_service` (HTTP + السكريبت المعزول بنسختيه):** `SELECT` مستقل بعد كل كراش أظهر **صفر أثر فعلي في كل مرة** — `wallets`(49)=`{"MR_USDT": 500}` بالحرف طول الوقت، `transactions`(sender=49)=0 صف، `service_licenses`(buyer=49)=0 صف، `affiliate_commissions`(user=49)=0 صف. **`finance.transfer()` نجحت 3 مرات مستقلة (3 محاولات، 3 `tx_hash` مختلفة) لكن كتابتها `flush()`-only، وبما إن كل محاولة كراشت قبل الوصول لـ`commit()` النهائي، الـ`AsyncSession` اتقفلت بلا commit فرجعت كل حاجة — صفر خطر مالي حقيقي من أي محاولة فاشلة.**

---

## 🔴🔴 [2026-08-17] اكتشاف حرج — `invitations.accept_invitation` بتنتج يوزر حقيقي بلا محفظة (orphaned user، مش rollback آمن) عند القبول بيوزر جديد

أثناء التحقق الحي من إصلاح constructor في `invitations/service.py` (راجع `.claude/reports/constructor-mismatch-session-log.md`)، تأكَّد **بالتنفيذ الفعلي** (سكريبت معزول، مش قراءة كود بس) اكتشاف استباقي كان مسجَّل كفرضية وقت جدول الأدلة: `accept_invitation` (سطر 269-353) بتنادي `_create_user_from_invitation` → `UserService(self.db, tenant_id).register(...)` **من جوه `begin_nested()` بتاعتها هي** (سطر 286)، لو `user_id` مش موجود (يوزر جديد بيقبل الدعوة لأول مرة).

**الفرق الجوهري عن كل حالات Backlog #11 السابقة (`realestate`, `service_marketplace`) — دي المرة الأولى في الجلسة كلها اللي بيانات حقيقية بتتسرّب فعليًا على القرص، مش rollback آمن بالكامل:**

**تسلسل الكراش المؤكَّد حيًا:**
```
_create_user_from_invitation
  → UserService.register()
    → self.user_repo.create(user)
      → self.db.add(user)
      → await self.db.commit()          # ← هذا الـcommit المباشر بيقفل الـSAVEPOINT بتاعة accept_invitation
      → await self.db.refresh(user)     # ← ده اللي بيكراش فعليًا، مباشرة بعد الـcommit، جوه نفس الاستدعاء
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager.
```
**الكراش بيحصل أبكر من المتوقَّع** — مش عند `repo.create_lead()` (الاستدعاء التالي في `accept_invitation`) زي ما كان متوقَّع أصلًا، لكن **جوه `UserRepository.create()` نفسها**، عند `db.refresh(user)` اللي بييجي مباشرة بعد الـ`commit()`.

**تحقق DB-level مستقل بعد الكراش (`SELECT` مباشر، مش افتراض):**
| الجدول | النتيجة |
|---|---|
| `users` | **صف حقيقي اتحفظ فعليًا** — `id=52, email=p_ctor_inv_newuser@eppne.com, tenant_id=1` — الـ`commit()` نجح قبل الكراش |
| `wallets` (user=52) | **صفر صف** — `WalletRepository.create()` (السطر اللي بعد `user_repo.create()` جوه `register()`) **معملهاش أصلًا**، لأن الكراش وقف التنفيذ قبل ما يوصلها |
| `crm_leads` | صفر صف (متوقَّع، الكود ما وصلش لهنا) |
| `sovereign_invitations_v2` (id=1) | `status=SENT, current_uses=0` — **الدعوة نفسها فضلت مش مقبولة فعليًا**، رغم إن يوزر اتسجَّل باسمها |

**النتيجة: يوزر حقيقي (id=52) موجود في قاعدة البيانات فعليًا، بلا محفظة، وبلا أي ربط بالدعوة أو الـlead — بيانات ناقصة/يتيمة (orphaned) حقيقية على القرص، مش "نجاح كاذب" ولا "rollback آمن بالكامل" زي كل حالات Backlog #11 السابقة في هذه الجلسة.** المستخدم الحقيقي اللي بيستخدم الـendpoint (`POST /api/invitations/{id}/accept`) هيشوف `500 Internal Server Error` (فشل واضح، مش صامت) — **لكن حساب يوزر جديد هيتسجَّل فعليًا بلا ما يعرف، وبلا محفظة تشتغل معاه لاحقًا.**

**السبب الجذري:** نفس فئة Backlog #11 (`commit()`-جوه-`begin_nested()`) — لكن هنا عبر `UserRepository.create()`/`WalletRepository.create()` (`identity/repository.py:56-60, 231-238`) مش `InvoicingService.create_invoice()`. **`identity` مش من ضمن الـ24 دومين اللي اتحوَّلوا لـ`flush()`-only في جلسة `transaction-savepoint-bug-session-log.md`** — نفس القرار المتعمَّد زي `invoicing`، لكن هنا التبعة أوقع (يوزر حقيقي، مش مجرد فاتورة).

**التصنيف: امتداد لـBacklog #11، لكن بعواقب أشد (بيانات هوية يتيمة على القرص، مش مجرد كراش نظيف).** **صفر إصلاح — خارج نطاق `constructor-mismatch` بالكامل، بقرار صريح متسق مع باقي الجلسة.** يستاهل **أولوية عاجلة جدًا** لجلسة منفصلة — أي endpoint تاني بينادي `UserService.register()` (أو أي service تاني بيعمل `commit()` مباشر) من جوه `begin_nested()` تاني، محتمل يكرر نفس النمط (بيانات هوية/مالية يتيمة، مش مجرد فشل نظيف).

**بيانات throwaway إضافية من هذا الاكتشاف:** `users id=52` (`p_ctor_inv_newuser@eppne.com`، **بلا محفظة** — حالة يتيمة حقيقية، جزء من الدليل نفسه، مش مجرد بيانات اختبار عادية) — مُضافة لقائمة التنظيف الإلزامي قبل أي إطلاق حقيقي.

---

### ⚠️ ملاحظة منهجية عامة (تنطبق على أي تحقق حي/معزول مستقبلي، مش بس هنا)

`finance.transfer()` (وأي دالة مشابهة بترجع/بتطبع كائن نتيجة زي `status=COMPLETED`) **بتنجح وترجع نتيجة "ناجحة" ظاهريًا حتى لو كتابتها `flush()`-only ومحتاجة `commit()` تانٍ بعدها لسه ما وصلش** — نفس الفئة البنيوية بالضبط اللي وثَّقتها جلسة `silent-write-regression-session-log.md` (125 موضع محمي بالصدفة، 35 موضع غير محمي). **الدرس المؤكَّد هنا 3 مرات مستقلة في نفس الجلسة:** طباعة/رجوع "نجاح" من دالة زي `finance.transfer()` **مش دليل كافٍ إطلاقًا** على إن الكتابة فعلاً على القرص — **لازم `SELECT` مستقل (session/connection منفصلة تمامًا عن اللي كتبت) بعد أي "نجاح" ظاهري من هذه الدوال، دايمًا، بلا استثناء**، خصوصًا في أي سيناريو فيه احتمال كراش لاحق قبل الـ`commit()` النهائي (زي كل محاولات `purchase_service` هنا). هذه القاعدة تنطبق على كل تحقق حي/معزول مستقبلي في المشروع، مش مقصورة على `service_marketplace`.
🔴 **BLOCKER قبل أي إطلاق حقيقي (مش أولوية زمنية زي باقي البنود — لازم يتنفَّذ قبل أي production launch بغض النظر عن ترتيب الجلسات):** تنظيف بيانات throwaway جلسة `constructor-mismatch` (راجع قسم "📦 بيانات اختبار دائمة للجلسة" في `.claude/reports/constructor-mismatch-session-log.md`).

هذه القائمة **مرجعية بس، مش التزام بجدول زمني** — الأولوية النهائية والقرار بالبدء في أي بند تعود للمستخدم وقت كل جلسة.

---

## 📌 [2026-08-14] ملاحظة منفصلة — `projects.add_contribution` محجوبة ببج `RedisClientWrapper` (فئة مختلفة تمامًا، مش constructor)

أثناء التحقق الحي من إصلاح باج constructor في `projects/service.py` (`self.finance = FinanceService(db)` بمعامل واحد بدل اتنين — راجع `.claude/reports/constructor-mismatch-session-log.md`)، اتكشف باج منفصل تمامًا منع اكتمال الاختبار عبر `POST /api/projects/contributions` الحقيقي:

`projects/service.py:158` (`add_contribution`، خطوة قفل idempotency):
```python
acquired = await self.redis.setnx(redis_key, json.dumps({"status": "processing"}))
```
مؤكَّد بالتنفيذ الفعلي (طلب HTTP حقيقي):
```
AttributeError: 'RedisClientWrapper' object has no attribute 'setnx'. Did you mean: 'setex'?
```
**التصنيف:** فئة مختلفة تمامًا (method غير موجودة على `RedisClientWrapper` — نفس عائلة `RedisClientWrapper` معندهاش `hincrbyfloat` الموثَّقة سابقًا في `silent-write-regression-session-log.md` لـ`ai_agents`، بس method مختلفة). **باج موجود مسبقًا، سابق لأي تعديل في هذه الجلسة — صفر إصلاح تم عليه.** يمنع `add_contribution` من الاكتمال **لأي طلب فيه `Idempotency-Key`**، بغض النظر عن إصلاح الـconstructor. **محاولة تجاوزه بعدم إرسال الهيدر فشلت أيضًا** — `finance.transfer()` نفسها بترفض `idempotency_key` فاضي/`None` بـ`ValidationError("Idempotency key is required")` (`finance/service.py:70`)، يعني الـendpoint محجوب في الحالتين، بس بسببين مختلفين. **يحتاج جلسة منفصلة** تصحح استدعاء Redis (الصح على الأرجح `setex` بـTTL قصير، أو إضافة `setnx` لـ`RedisClientWrapper`) — **خارج نطاق جلسة `constructor-mismatch` بالكامل.**

**تحقق بديل:** تم استخدام سكريبت تحقق معزول (زي `book_appointment`/`settle_carbon_credits`) يتخطى خطوة قفل الـidempotency عبر Redis بس — تفاصيل كاملة والنتيجة DB-level في `.claude/reports/constructor-mismatch-session-log.md`.

---

## 📌 [2026-08-14] ملاحظة منفصلة — `UserRepository.get_user()` غير موجودة أصلًا (فئة "method غير موجودة"، مش "معامل ناقص") — 6 مواضع عبر 5 دومينات

أثناء التحقق الحي من إصلاح باج constructor في `digital_twin/service.py` (`interact_with_twin` وغيرها — راجع `.claude/reports/constructor-mismatch-session-log.md`)، اتأكَّد إن `_get_user`/`_get_user_email` (`digital_twin/service.py:47-51`) بتنادي `UserRepository(self.db).get_user(user_id)` — لكن **`UserRepository` معندهاش method اسمها `get_user` إطلاقًا** (التعريف الوحيد هو `get_by_id(self, user_id, tenant_id, load_wallet=False)`). هذا **مش نفس فئة `constructor-mismatch` (معامل ناقص) ولا نفس فئة `get_by_id`-الموثَّقة فوق (15 موضع) — دي فئة تالتة: استدعاء method غير موجودة إطلاقًا على الكلاس**، نفس الفئة المذكورة أصلًا في توجيه بداية جلسة `constructor-mismatch` بخصوص `communications._get_user_tenant`.

**`grep` شامل لـ`.get_user(` عبر `app/` كشف 6 مواضع بنفس الباج بالضبط، عبر 5 دومينات (زائد موضع سابع صحيح، مش باج):**

| # | الملف:السطر | السياق |
|---|---|---|
| 1 | `communications/service.py:29` | داخل helper مشابهة (مذكورة أصلًا في توجيه بداية الجلسة) |
| 2 | `communications/service.py:36` | نفس الفئة، موضع تانٍ في نفس الملف |
| 3 | `digital_twin/service.py:51` | `_get_user(self, user_id)` — **مؤكَّدة، بتمنع `interact_with_twin`/`_register_affiliate_commission` من الاكتمال عبر HTTP الحقيقي** |
| 4 | `employment/service.py:89` | نفس النمط |
| 5 | `health/service.py:54` | `_get_user_email(self, user_id)` — **ملاحظة: مختلفة عن `_get_user_email` اللي فحصناها في `book_appointment` (اللي بتستخدم بريد هاردكودد `health@eppne.com` مباشرة، مبتناديش الدالة دي) — هذا مسار منفصل تمامًا جوه نفس الملف، لسه محجوب لأي method تانية تستخدمه مستقبلًا** |

**✅ موضع صحيح، مش باج (للتمييز):** `identity/service.py:238` — `self.get_user(user_id)` بتنادي method حقيقية معرَّفة على `UserService` نفسها (مش `UserRepository`)، بتستخدم `self.user_repo.get_by_id(...)` الصحيحة داخليًا.

**الحالة: باج موجود مسبقًا في كل الحالات الخمس، سابق لأي تعديل في هذه الجلسة — صفر إصلاح تم عليه.** يستاهل يُضاف لقائمة الـBacklog كفئة مستقلة (منفصلة عن `user-repository-get-by-id-audit` اللي هي عن معامل ناقص، مش method غير موجودة).

---

## 📌 [2026-08-14] ملاحظة منفصلة — دليل حي إضافي إن إصلاح constructor بتاع `digital_twin` صحيح، لكن `_check_saas_limits`/`_register_affiliate_commission` محجوبتان بباجات "method غير موجودة" مستقلة تمامًا وموثَّقة مسبقًا

**اختبار حي حقيقي فعلي** (`POST /api/digital-twin/interact/44`، بعد إصلاح الـconstructor في هذه الجلسة) وصل لمرحلة أعمق من أي مرة قبل كده — **صفر `TypeError` على `SaaSControlService`** (دليل قاطع إن إصلاح الـconstructor شغّال)، لكن كراش فوري بعده مباشرة بباج مختلف تمامًا:
```
File "digital_twin/service.py", line 39, in _check_saas_limits
    subscription = await saas_service.get_active_subscription(tenant_id)
AttributeError: 'SaaSControlService' object has no attribute 'get_active_subscription'. Did you mean: 'create_subscription'?
```
**تأكَّد بالقراءة:** `SaaSControlService` (`saas/service.py`) **معندهاش method اسمها `get_active_subscription` إطلاقًا** — أقرب البدائل الموجودة فعليًا: `get_subscription`, `get_tenant_subscriptions`, `can_access_service`. **فئة "method غير موجودة" تالتة** (بعد `UserRepository.get_user` و`RedisClientWrapper.setnx`/`hincrbyfloat`)، هذه المرة على `SaaSControlService`. **باج موجود مسبقًا، صفر إصلاح.**

**`_register_affiliate_commission` محجوبة بباج مشابه موثَّق مسبقًا (مش اكتشاف جديد):** `AffiliateService` (`affiliate/service.py`) **معندهاش `get_user_by_code` ولا `register_commission`** — هذا **مطابق تمامًا** لما كان موثَّق في `transaction-savepoint-bug-session-log.md` ("`_register_affiliate_commission`/`register_commission` غير موجودة على `AffiliateService`" — قائمة دومينات كانت شاملة `digital_twin` أصلًا من ضمنها).

**الخلاصة:** إصلاح constructor `digital_twin` (الثلاثة كلاسات) **صحيح ومؤكَّد** — الدليل: صفر `TypeError` في كل محاولة، والكراشات كلها بقت في مرحلة أعمق (استدعاء methods غير موجودة، فئة مختلفة تمامًا). **لا داعي لإصلاح أي من الباجين دول في جلسة `constructor-mismatch`** — موثَّقان هنا للسجل فقط، الأول جديد (أُضيف لقائمة الـBacklog، بند 8 تحت اسم بديل مقترَح `saas-control-service-missing-methods`)، والثاني معروف مسبقًا.

---

## 🔴 [2026-08-15] ملاحظة منفصلة — `realestate.buy_fractional_ownership`/`rent_unit`: `invoicing.create_invoice`'s `commit()` مباشر بيكسر `begin_nested()` بتاعتهم (فئة `commit()`-جوه-`begin_nested()`، مش constructor)

أثناء التحقق الحي من إصلاح باج constructor في `realestate/service.py` (راجع `.claude/reports/constructor-mismatch-session-log.md`)، اتأكَّد بالقراءة المباشرة (مش تخمين) إن `buy_fractional_ownership` (سطر 244) و`rent_unit` (سطر 378) بينادوا `self.invoicing.create_invoice(...)` **من جوه** `async with self.db.begin_nested():` بتاعتهم — لكن `invoicing/repository.py`'s `create_invoice` (سطر 21-30) **لسه بتعمل `await self.db.commit()` مباشر** (مع تعليق تحذيري موجود بالفعل يوضّح إنها **عمدًا** متسيبة كده، عشان بتغطي كتابات `finance.transfer()` في callers تانيين بره أي `begin_nested()`، زي `arbitration_syndicates.join_syndicate`).

**السبب الجذري:** `invoicing` **مش من ضمن الـ24 دومين** اللي اتحوَّلوا لـ`flush()`-only في جلسة `transaction-savepoint-bug-session-log.md` — القرار وقتها كان الإبقاء على الـcommit المباشر عمدًا. لكن `realestate` **بتنادي `invoicing.create_invoice` من جوه `begin_nested()` بتاعتها هي**، فالـcommit المباشر بيقفل الـSAVEPOINT بالنص، وأي عملية بعده جوه نفس البلوك (`_register_affiliate_commission`, `repo.create_ownership`, `event_bus.publish`, `audit_log`, `_send_notification`) بتفشل بـ`InvalidRequestError: Can't operate on closed transaction inside context manager`.

**مؤكَّد بالتنفيذ الفعلي** (سكريبت تحقق معزول لـ`buy_fractional_ownership`، تفاصيل كاملة في `.claude/reports/constructor-mismatch-session-log.md`): `finance.transfer()` نجح، ثم كراش فوري عند `invoicing.create_invoice`، بنفس رسالة الخطأ بالحرف.

**لماذا لم يُكتشَف هذا من قبل:** `realestate.buy_fractional_ownership`/`rent_unit` **كانتا محجوبتين بالكامل ببج constructor** (`FinanceService(db)` بمعامل واحد) لحد جلسة `constructor-mismatch` — يعني الـendpoint دول ما كانش ممكن يوصلوا لسطر `invoicing.create_invoice` أصلًا في أي محاولة سابقة. إصلاح باج الـconstructor **كشف** هذا الباج المنفصل، بالظبط زي التحذير المسجَّل مسبقًا في خطة الجلسة ("إصلاح أي constructor قد يكشف حالات كتابة صامتة جديدة").

---

## 🔴 [2026-08-16] ملاحظة منفصلة — `service_marketplace._check_saas_limits` بتنادي `can_access_service` بمعامل زيادة (فئة جديدة: "wrong-arity call بعد تغيير توقيع method"، مش constructor)

أثناء التحقق الحي من إصلاح باج constructor في `service_marketplace/service.py` (راجع `.claude/reports/constructor-mismatch-session-log.md`، قسم "الدفعة 2 — دومين 2")، اتكشف باج جانبي مسدود تمامًا لـ`purchase_service` عبر `POST /api/marketplace/purchase` حقيقي:

```
File "app/domains/service_marketplace/service.py", line 70, in _check_saas_limits
    has_access = await saas_service.can_access_service(tenant_id, "service_marketplace")
TypeError: SaaSControlService.can_access_service() takes 2 positional arguments but 3 were given
```

**التصنيف: فئة جديدة، مختلفة عن Backlog #9 (`saas-control-service-missing-methods` — method غير موجودة أصلًا).** هنا الـmethod **موجودة فعلًا** (`saas/service.py:209`: `can_access_service(self, service_code: str) -> bool`) لكن توقيعها **بياخد معامل واحد بس بعد `self`** — `tenant_id` بقى جوه الـconstructor نفسه (`self.tenant_id`)، مش parameter منفصل. الاستدعاء في `service_marketplace/service.py:70` **لسه بيمرره كمعامل positional زيادة** — على الأرجح كود لم يتحدّث بعد إعادة هيكلة سابقة نقلت `tenant_id` من parameter الـmethods لـconstructor الـservice.

**مهم — هذا الاستدعاء الخاطئ موجود من قبل ديف جلسة `constructor-mismatch` بالحرف.** ديفنا بدّل بس `self.saas_service` (كان `SaaSControlService(db)` ناقص) بمتغيّر محلي `saas_service = SaaSSubscriptionService(self.db, tenant_id)` — نفس استدعاء `can_access_service(tenant_id, "service_marketplace")` بمعاملين ورثه الديف زي ما هو، بدون أي تعديل عليه (خارج نطاق الـ7 hunks المتفَق عليها). **صفر إصلاح تم على هذا الاستدعاء — بقرار صريح من المستخدم، خارج نطاق جلسة `constructor-mismatch` بالكامل.**

**الأثر:** `purchase_service` **محجوبة بالكامل عبر HTTP الحقيقي بأي بيانات**، لأنها بتنادي `_check_saas_limits` كأول خطوة بدون أي شرط. **`renew_subscription`/`purchase_addon` غير متأثرتين** (مبينادوش `_check_saas_limits` إطلاقًا) — اتحقق منهم حيًا عبر HTTP حقيقي بنجاح (تفاصيل كاملة في تقرير الجلسة).

**⚠️ تنبيه لأي جلسة مستقبلية:** نفس الفئة ("استدعاء لم يتحدّث بعد نقل `tenant_id` للـconstructor") محتمل تتكرر في أي دومين تاني بينادي `SaaSControlService.can_access_service` بنفس النمط القديم (معاملين). **صفر تأكيد فعلي لأي دومين تاني في هذه الجلسة** — يحتاج `grep` شامل مخصَّص لاحقًا (`can_access_service(` عبر `app/` كله) قبل اعتباره مغلقًا. أُضيف لقائمة الـBacklog كبند #12 (`saas-control-service-wrong-arity-call`).

**تحقق بديل مطلوب لإكمال `purchase_service`:** سكريبت معزول يتخطى `_check_saas_limits` بس، ويكمل تنفيذ باقي المنطق الحقيقي (`finance.transfer`, `invoice_service.create_invoice`, `_register_affiliate_commission`) — تفاصيل النتيجة الكاملة في تقرير الجلسة.

**🔴 تحديث فوري — باج جانبي ثانٍ اتكشف أثناء تشغيل السكريبت المعزول (نفس عائلة "call site لم يتحدّث"، لكن مختلف تمامًا عن باج #12):** بعد تخطي `_check_saas_limits`، السكريبت وصل لـ`finance.transfer()` (نجح فعليًا: `tx_hash=TX-D07B1B7D99D7, status=COMPLETED`) ثم كراش فورًا عند `invoice_service.create_invoice(tenant_id=buyer_tenant_id, ...)`:
```
TypeError: InvoicingService.create_invoice() got an unexpected keyword argument 'tenant_id'
```
**التوقيع الحقيقي** (`invoicing/service.py:51-60`): `create_invoice(self, entity_id: int, user_id: int, amount: Decimal, description: str, due_date=None, invoice_type="SERVICE", reference_id=None, idempotency_key=None)` — اسم المعامل **`entity_id`**، مش `tenant_id`. الاستدعاء في `service_marketplace/service.py:203-210` (**موجود من قبل ديف `constructor-mismatch` بالحرف، الديف بدّل بس `self.invoice_service` بمتغيّر محلي، صفر لمس على أسماء الـkwargs**) بيمرر `tenant_id=` كـkeyword خطأ.

**فئة جديدة: "wrong-kwarg-name call" — مختلفة عن باج #12 (wrong-arity) وعن Backlog #9 (method غير موجودة).** هنا الـmethod موجودة والـarity صح (عدد المعاملات مطابق تقريبًا) لكن **اسم الـkeyword نفسه غلط**.

**✅ تأكيد سلامة البيانات (فحص فعلي، مش افتراض):** رغم إن `finance.transfer()` طبع `status=COMPLETED`، الـ`SELECT` المستقل بعد الكراش أظهر **صفر تغيير فعلي** — `wallets` (user 49) لسه `{"MR_USDT": 500}` بالحرف، و`transactions` (sender=49) **صفر صف**. السبب: `finance.transfer()` كتابتها `flush()`-only (زي باقي الـ24 دومين من جلسة `transaction-savepoint-bug-session-log.md`)، وبما إن السكريبت كراش قبل ما يوصل لـ`await svc.db.commit()` النهائي (نفس ترتيب الكود الحقيقي)، الـ`AsyncSession` اتقفلت من غير commit فرجعت كل حاجة (rollback ضمني) — **صفر أثر مالي حقيقي من المحاولتين الفاشلتين (HTTP + السكريبت)**.

**الأثر:** حتى لو اتصلح باج #12 (`can_access_service`)، `purchase_service` **هتفضل تكراش على باج تانٍ فورًا بعده** عند `invoice_service.create_invoice`، بغض النظر عن أي بيانات. **صفر إصلاح تم على أي من الباجين، بقرار صريح من المستخدم — خارج نطاق `constructor-mismatch` بالكامل.** أُضيف كبند Backlog منفصل (#13) تحت.

**التصنيف: فئة `commit()`-جوه-`begin_nested()` (نفس فئة الـ89 موضع الأصلية من `transaction-savepoint-bug-session-log.md`)، مش constructor — خارج نطاق جلسة `constructor-mismatch` بالكامل. صفر إصلاح تم عليه.** يحتاج قرار تصميمي (هل نلف استدعاء `invoicing.create_invoice` في `realestate` بمعاملة منفصلة برّه الـ`begin_nested`، ولا نضيف `flush()`-only variant، ولا حل تاني؟) — **جلسة منفصلة، أولوية عالية** (بيمنع إكمال أي عملية شراء/إيجار فعلية في `realestate` رغم إصلاح الـconstructor).

---

## 📌 [2026-08-17] ملاحظة منفصلة — `automation.run_workflow_background` بينشئ صف `execution` مستقل تمامًا عن اللي رجعه `trigger_workflow_manual` (فئة مختلفة تمامًا، مش constructor)

أثناء التحقق الحي من إصلاح باج constructor في `automation/service.py` (`_exec_ai_agent` — راجع `.claude/reports/constructor-mismatch-session-log.md`، قسم `automation`)، اتلاحظ إن `POST /api/automation/workflows/{id}/trigger` بيرجع `execution_id` من صف بينشئه `trigger_workflow_manual` (`automation/service.py:923-931`) — **لكن `run_workflow_background`** (الدالة الفعلية اللي بتشغّل الـ`AutomationEngine` عبر `BackgroundTasks`، `automation/service.py:1078-1106`) **بتنادي `repo.create_execution(...)` بنفسها تانِي، بصف جديد كليًا (`id` مختلف)**، بدل ما تستخدم/تستقبل الصف اللي اتنشأ ورجع للـclient أصلاً. **النتيجة المؤكَّدة حيًا:** `POST /trigger` رجّع `execution_id=1`، لكن الصف اللي فعليًا اتنفَّذ وخلص (`status=SUCCESS`) كان `execution_id=2` — **صف `id=1` فضل `PENDING` للأبد، بلا أي تحديث حالة إطلاقًا**، مش حتى `FAILED`.

**التصنيف:** فئة مستقلة تمامًا ("دالتين بينشئوا نفس الـresource بشكل مستقل، مش نفس تدفق البيانات") — **صفر علاقة بـ`constructor-mismatch`**. **الأثر:** أي عميل بيعتمد على `execution_id` المُرجَع من `POST /trigger` عشان يتابع حالة التنفيذ (`GET /executions/{id}`) هيشوف الصف فاضل `PENDING` للأبد، بينما التنفيذ الفعلي بيحصل على صف تاني مختلف الـid تمامًا — **واجهة مستخدم/API غير موثوقة بالكامل لأي تتبع حالة**. **موجود من قبل جلسة `constructor-mismatch`، صفر لمس، صفر إصلاح.**

---

## 🔴 قرار أولوية صريح [2026-08-17] — يقرأه أي حد قبل أي عمل مستقبلي (راجع البانر أعلى الملف)

**جلسة `invitations-user-registration-savepoint-leak`** (توثيقها الكامل في تقرير مستقل: `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`) **هي الجلسة التالية مباشرة بعد الانتهاء الكامل من فحص/إصلاح الـ16 دومين المتبقية في الدفعة 2 + الدفعة 3 (جدول ب) من جلسة `constructor-mismatch`** — **قبل أي جلسة أخرى في قائمة الانتظار** (Backlog #1-#14، Phase 16 الأصلي، `sovereign_entities`، `commerce.visa_webhook`، إلخ).

**السبب: مش اعتماد تقني بين الدومينات — أولوية أمان/سلامة بيانات بحتة.** الثغرة (يوزر حقيقي بلا محفظة بيتسجَّل على القرص فعليًا عبر `invitations.accept_invitation`) **محجوبة حاليًا بالصدفة** ببج مستقل تمامًا (Backlog #9 — `SaaSControlService.get_active_subscription` غير موجودة)، **لا بتصميم آمن مقصود**. أي إصلاح مستقبلي لـBacklog #9 بمعزل عن قراءة التقرير الحرج ده هيفتح الثغرة فورًا.

**تحذير مربوط ببند Backlog #9 نفسه (مُضاف هناك كمان، أعلى مباشرة):** قبل إصلاح `get_active_subscription`، يجب أولاً إصلاح أو على الأقل مراجعة تقرير `invitations.accept_invitation` الحرج كاملًا (يوزر `id=52` نموذج حي)، وإلا فإن الإصلاح سيفتح ثغرة تسجيل هوية فورية.

**🔒 استثناء صريح من أي تنظيف عام لبيانات throwaway:** `users id=52` (`p_ctor_inv_newuser@eppne.com`) **يُستثنى بالكامل** من أي تنظيف عام لبيانات throwaway (بما فيه الـBLOCKER الدائم قبل الإطلاق) **حتى تُغلق جلسة `invitations-savepoint-leak` رسميًا** — لأنه الدليل الحي الوحيد على الثغرة، مش بيانات اختبار عادية قابلة للحذف الروتيني.

---

## 🔴 [2026-08-18] Backlog جديد — `invitations-missing-expiry-max_uses-validation` (اكتُشف أثناء جلسة `invitations-savepoint-leak`، فئة مستقلة تمامًا عن `commit()`-جوه-`begin_nested()`)

**اكتُشف أثناء:** تحليل جدول الأدلة لجلسة `invitations-savepoint-leak-session-log.md` (`.claude/reports/invitations-savepoint-leak-session-log.md`, قسم 3.1) — أثناء التحقق من موضع فحص صلاحية الدعوة في `accept_invitation` بالنسبة لنقطة نقل `_create_user_from_invitation` المقترحة، **قبل أي تعديل كود في هذه الجلسة**.

**الحالة: 🔴 صفر إصلاح تم. توثيق فقط، بقرار صريح من المستخدم — خارج نطاق جلسة `invitations-savepoint-leak` بالكامل (تلك الجلسة عن `commit()`-جوه-`begin_nested()` تحديدًا، مش عن فجوات التحقق من صلاحية الدعوة).**

### الوصف

`InvitationsService.accept_invitation` (`invitations/service.py:267-353`) **لا تتحقق أبدًا من `expires_at` ولا من `current_uses < max_uses` قبل قبول أي دعوة.** الفحص الوحيد الموجود فعليًا (`invitations/service.py:282-284`) هو:
```python
invitation = await self.repo.get_invitation(invitation_id, tenant_id)
if not invitation or invitation.status != InvitationStatus.SENT:
    raise NotFoundError("Invitation not found or not sent")
```
فحص وجود الدعوة + `status == SENT` فقط. **`grep` شامل ومؤكَّد (صفر نتيجة) لـ`expires_at`/`max_uses` عبر الملفات الثلاثة المعنية بالكامل:**

| الملف | `expires_at` | `max_uses` |
|---|---|---|
| `invitations/service.py` (الملف كله) | 0 نتيجة | 0 نتيجة |
| `invitations/router.py` (كل الـendpoints) | 0 نتيجة | 0 نتيجة |
| `invitations/repository.py` (كل الاستعلامات) | 0 نتيجة | 0 نتيجة |

`current_uses` تظهر مرة واحدة بس في الملف كله (`invitations/service.py:311`) — **تحديث** (`current_uses=invitation.current_uses + 1`) لا **فحص**؛ صفر مقارنة بـ`max_uses` في أي مكان قبل القبول.

كلا العمودين موجودان فعليًا في الموديل (`invitations/models.py:114-116`: `max_uses = Column(Integer, default=1)`, `current_uses = Column(Integer, default=0)`, `expires_at = Column(DateTime(timezone=True), nullable=True)`) — **معرَّفان، لكن غير مُستخدَمين إطلاقًا في منطق القبول.**

### الأثر

دعوة **منتهية الصلاحية** (`expires_at` في الماضي) أو دعوة **استنفدت حد استخداماتها** (`current_uses >= max_uses`) لسه ممكن تُقبَل بنجاح طالما `status` لسه `SENT` — تجاوز فعلي لقيد منتجي/أمني مقصود (الحقول موجودة بالموديل تحديدًا لفرض هذا القيد). **مختلفة تمامًا عن النظام المشابه في `identity/invitation_service.py` (تينانت invitations)** الذي يفحص `max_uses` فعليًا (مؤكَّد سابقًا في هذا الملف، سطور 2168-2172) — الفجوة هنا محصورة في نظام `sovereign_invitations_v2`/CRM (`InvitationsService.accept_invitation`) تحديدًا.

### التصنيف

فئة مستقلة تمامًا — **"غياب فحص صلاحية موثَّق بالموديل لكن غير مُنفَّذ في منطق القبول"** — لا علاقة لها بفئة `commit()`-جوه-`begin_nested()` (Backlog #11 وامتداداتها) ولا بأي فئة موثَّقة سابقًا لهذا الدومين. **مؤكَّد بالقراءة المباشرة (`grep` + قراءة الكود)، غير مؤكَّد بعد بالتنفيذ الفعلي/HTTP حي** — يحتاج جلسة منفصلة لتحديد سلوك الإصلاح المطلوب (رفض بـ`ValidationError` واضح عند `expires_at` منتهية أو `current_uses >= max_uses`؟) ومراجعة منتجية لسلوك القبول المطلوب فعليًا. **صفر إصلاح في هذه الجلسة أو أي جلسة سابقة — أولوية أعلى من العادي، تُضاف لقائمة الانتظار.**

---

## 📌 [2026-08-18] Backlog صغير، أولوية منخفضة — `sovereign_invitations_v2`: أعمدة رقمية/boolean قابلة لـ`NULL` بلا `NOT NULL` أو server-side default

**اكتُشف أثناء:** التحقق الحي لجلسة `invitations-savepoint-leak` (`.claude/reports/invitations-savepoint-leak-session-log.md`, قسم 7.3) — أثناء إعداد بيانات throwaway جديدة عبر SQL خام لدعوتي اختبار (`id=2, 3`).

**الوصف:** أعمدة `sovereign_invitations_v2.discount_percentage`, `gift_coins_amount`, `is_deleted` معرَّفة بـ`default=` **على مستوى بايثون/SQLAlchemy ORM فقط** (`invitations/models.py:110-112, 129`) — **بلا `NOT NULL` constraint وبلا server-side default على مستوى قاعدة البيانات نفسها** (مؤكَّد بـ`\d sovereign_invitations_v2`، عمود `Nullable` فاضي لكل الثلاثة). أي إدراج **خارج** مسار `InvitationsRepository.create_invitation` (ORM) — migration مستقبلية، سكريبت إداري، إدراج SQL خام — هيسيب هذه الأعمدة `NULL` فعليًا، مش `0`/`False`. **الأثر المؤكَّد فعليًا في هذه الجلسة:** `NULL` في `is_deleted` بيكسر فلتر `get_invitation`'s `is_deleted == False` (بيرجع `NotFoundError` كاذبة)، و`NULL` في `discount_percentage`/`gift_coins_amount` بيكسر `accept_invitation`'s سطر 304 (`TypeError: '>' not supported between instances of 'NoneType' and 'int'`).

**الحالة:** 🟡 **توثيق فقط، أولوية منخفضة — غير عاجل.** كل الدعوات الحقيقية المُنشأة عبر `POST /invitations` (المسار الوحيد الفعلي في التطبيق) بتاخد القيم الافتراضية تلقائيًا من الـORM، فمش قابل للوصول عبر أي استخدام حقيقي حاليًا — الخطر نظري، محصور في أي إدراج مستقبلي يتخطى الـORM. **صفر إصلاح.**

---

## ✅ [2026-08-18] Backlog #11 (امتداد `invitations`) — إغلاق رسمي: `invitations.accept_invitation` — يوزر حقيقي بلا محفظة عبر `commit()`-جوه-`begin_nested()`

**الحالة: ✅ مُغلَق.** التفاصيل الكاملة (جدول أدلة/تحليل، جولات أسئلة توضيحية، الديف الخام، `git diff`/`git status` بعد التطبيق، والتحقق الحي الكامل) موثَّقة في تقرير جلسة مستقل: **`.claude/reports/invitations-savepoint-leak-session-log.md`**.

**السبب الجذري (كان):** `UserRepository.create()`/`WalletRepository.create()` (`identity/repository.py:56-60, 231-240`) بتعمل `commit()` مباشر — وده كان بيقفل الـSAVEPOINT بتاع `begin_nested()` الخاص بـ`invitations.accept_invitation` (`invitations/service.py:286` سابقًا) لما بتنادي `UserService.register()` من جواه، عبر `_create_user_from_invitation`. النتيجة كانت: يوزر حقيقي يتسجَّل على القرص فعليًا (`commit()` نجح)، بلا محفظة (الكراش بيوقف التنفيذ قبل `WalletRepository.create()`)، والدعوة تفضل `SENT` بلا أي مسار نجاح ممكن.

**الحل المُطبَّق (`invitations/service.py` فقط — صفر لمس على `identity/repository.py`/`identity/service.py`، محترم شرط الإيقاف الأصلي بخصوص الكود المشترك):**
1. نقل استدعاء `_create_user_from_invitation` (إنشاء اليوزر الجديد) بره `begin_nested()` بالكامل — بيتنفَّذ الآن كمعاملة مستقلة غير متداخلة، فـ`UserService.register()`'s `commit()` الداخلي ما بيقفلش SAVEPOINT أي حاجة.
2. تثبيت الـ`idempotency_key` الممرَّر لـ`UserService.register()` من قيمة عشوائية (`uuid.uuid4()`، مختلفة كل مرة) لقيمة ثابتة مشتقة من `tenant_id`+`invitation_id` (`f"INV-ACCEPT-T{tenant_id}-{invitation_id}"`) — لضمان إن أي إعادة محاولة لنفس الدعوة بعد فشل جزئي (كراش في الكود اللي بعد إنشاء اليوزر) بتلاقي نفس اليوزر اللي اتعمل قبل كده (عبر آلية idempotency الموجودة أصلًا في `UserService.register()`)، بدل ما تكراش بـ`ValidationError("البريد الإلكتروني مسجل بالفعل")` وتسيب الدعوة عالقة `SENT` للأبد.

**التحقق الحي (`.claude/reports/invitations-savepoint-leak-session-log.md`, قسم 7):** سيناريوهان مستقلان، بيانات throwaway جديدة تمامًا (**`users id=71, id=72`**، **`sovereign_invitations_v2 id=2, id=3`**) — **`users id=52`/دعوة `id=1` (الدليل الأصلي) لم يُلمَسا إطلاقًا طوال التحقق.**
- **سيناريو قبول نظيف (دعوة `id=2`، يوزر `id=71`):** `sovereign_invitations_v2.status=ACCEPTED`، `wallets` بها صف فعلي (`id=68, user_id=71`)، `crm_leads.status=CONVERTED` — بدل الكراش الأصلي عند `db.refresh()`.
- **سيناريو فشل جزئي مُفتعَل ثم retry (دعوة `id=3`، يوزر `id=72`):** المحاولة الأولى فشلت عمدًا (كراش مُفتعَل بعد إنشاء اليوزر) — اليوزر اتعمل بمحفظة كاملة رغم ذلك، والدعوة فضلت `SENT` مؤقتًا. **المحاولة الثانية نجحت فعليًا** باستخدام **نفس اليوزر بالظبط** (`id=72`، صفر يوزر مكرَّر) — `sovereign_invitations_v2.status=ACCEPTED`، `current_uses=1` (مش 2)، `crm_leads.status=CONVERTED`.

**اكتشافان جانبيان مستقلان تمامًا أثناء التحقق، موثَّقان بنداهما الخاصة، خارج نطاق هذا الإغلاق:**
- `invitations-missing-expiry-max_uses-validation` (بند Backlog منفصل أعلى في هذا الملف) — فجوة تحقق أولوية أعلى من العادي.
- Backlog صغير أولوية منخفضة عن أعمدة `sovereign_invitations_v2` القابلة لـ`NULL` بلا `NOT NULL`/server-side default (البند مباشرة فوق هذا).
- تأكيد إضافي (مش اكتشاف جديد) لفئة Backlog #14 (`audit-log-wrong-kwargs`) موجودة كمان جوه `accept_invitation` نفسها (`invitations/service.py:328`) — بعد `commit()` النهائي، فصفر أثر على سلامة البيانات، صفر إصلاح هنا.

**🔓 القيد على Backlog #9 اتشال:** كان فيه قرار أولوية صريح (`PROGRESS_LOG.md`, بانر [2026-08-17] + قسم "🔴 قرار أولوية صريح") يمنع إصلاح `SaaSControlService.get_active_subscription` (Backlog #9) قبل إغلاق هذه الثغرة، عشان إصلاح #9 كان هيفتح مسار الاستغلال الفوري لباج يوزر بلا محفظة. **الآن بعد الإغلاق الرسمي، هذا القيد مرفوع — Backlog #9 مسموح فتح جلسة مستقلة له وقتما تحب، بلا أي اعتماد إضافي على هذا الملف.**

**تنظيف throwaway:** `users id=52`/دعوة `id=1` (الدليل الأصلي) و`users id=71, 72`/دعوة `id=2, 3` (بيانات التحقق الجديدة) **كلهم يتركوا كما هم الآن** — تنظيف روتيني عادي غير عاجل، مش جزء من هذا الإغلاق، ينضم لقائمة التنظيف العامة قبل أي إطلاق حقيقي.
