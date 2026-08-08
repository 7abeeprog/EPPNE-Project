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
