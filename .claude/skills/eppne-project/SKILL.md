---
name: eppne-project
description: معايير الترميز وحالة البنية الحالية لمشروع EPPNE (Backend FastAPI + Frontend Next.js). استخدم هذا الملف دائمًا قبل التعديل على auth/identity، أو أي دومين باك إند/فرونت إند، أو عند إضافة كود جديد للمشروع.
---

# EPPNE — سياق المشروع الدائم

> هذا الملف مرجع سريع لأي جلسة عمل جديدة على المشروع. المصادر التفصيلية:
> - `PROJECT_AUDIT.md` (جذر المشروع) — تدقيق شامل بتاريخ 2026-08-08
> - `PROGRESS_LOG.md` (جذر المشروع) — سجل تراكمي لكل مهمة مكتملة، **لا يُعدَّل قديمه أبدًا**
> - `.claude/plans/phase3-rename-auth-to-identity.md` — خطة Phase 3 (rename)
> - `.claude/plans/phase4-remove-auth-backend.md` — خطة Phase 4 (حذف auth)
> - `CODING_STANDARDS.md` (جذر المشروع)
>
> **ملاحظة تاريخية:** الملف الأصلي `.claude/plans/delightful-kindling-
> wigderson.md` (كان المرجع لخطة الدمج الكاملة) **غير موجود** لا في شجرة
> العمل ولا في تاريخ git — تأكدنا من ده بتاريخ 2026-08-09. الخطط الحالية
> (phase3/phase4) أُعيد بناؤها من الصفر بأسماء واضحة مختلفة عمدًا.

---

## ⚠️ الحالة الحالية: دمج auth → identity (شارف على الاكتمال)

المشروع كان فيه نظاما مصادقة كاملان يعملان بالتوازي: `auth` (Bearer/JSON) و
`identity` (HttpOnly Cookies). القرار المعتمد: **`identity` هو الناجي**،
و`auth` بيتحذف بالكامل في Phase 4.

| Phase | النطاق | الحالة |
|---|---|---|
| 0 | Backend: إصلاح 3 انهيارات حرجة كانت تكسر كل تسجيل دخول | ✅ مكتمل ومُتحقَّق منه |
| 1 | Backend: بناء آلية جلسة حقيقية داخل identity (تخزين/إبطال refresh tokens فعلي) | ✅ مكتمل ومُتحقَّق منه (E2E) |
| 2 | Frontend: توحيد كل شيء على `identity` (كوكيز)، `AuthProvider.tsx` يستعلم `GET /identity/me` بدل `localStorage` | ✅ مكتمل (commit `5b1d241`) |
| 3 | Rename: `components/auth`→`identity`, `hooks/auth`→`identity`، تحديث كل الاستيرادات | ✅ **الكود مكتمل ومتحقَّق منه بدقة** (tsc نظيف + مقارنة baseline عبر `git worktree` أثبتت صفر تأثير جانبي). ⏸️ **اختبار logout اليدوي في المتصفح لسه معلّق** — بسبب باج منفصل تمامًا وقديم (`lit`/`@reown/appkit-ui`، من الـInitial commit)، مش تقصير في Phase 3 نفسها |
| 4 | Backend: حذف دومين `auth` بالكامل (7 ملفات + إزالة تسجيله من `main.py`) | 🔄 **قيد التنفيذ** — الملفات اتحذفت، `main.py` بيتعدّل، باقي: `pytest` + تأكيد `GET /docs` خالي من `/auth/*` |

**Phase 4 هي المرحلة الأخيرة المخطط لها لخطة الدمج — لا توجد مرحلة 5 موثقة.**
أي اكتشاف جديد يظهر أثناء التنفيذ (زي باج web3 في Phase 3) يُوثَّق كمهمة
منفصلة في PROGRESS_LOG.md، مش كمرحلة رسمية جديدة.

**قواعد صارمة أثناء العمل على هذا الدمج:**
- ممنوع الاعتماد على `localStorage` لتحديد حالة تسجيل الدخول — المصدر الوحيد
  للحقيقة هو استعلام حقيقي للسيرفر (`GET /identity/me` عبر كوكي HttpOnly).
- ممنوع استيراد أي حاجة من `auth/jwt_service.py` — (بعد Phase 4، الملف ده
  **محذوف بالكامل**؛ كان فيه دوال توافقية بتُنشئ توكنات بـ `tenant_id=1`
  مُثبَّت، خطر أمني حقيقي).
- عند لمس أي endpoint في `identity`، تأكد إنه بيستخدم `core/security.py`
  (يفحص `session_version` و`tenant_id`) مش `api/deps.py` الأضعف.
- أي 401 جاي من استدعاء بيانات (زي `getMe()`) **مايعملش redirect إجباري من
  جوّه** — القرار محصور في `AuthProvider`، والدالة نفسها تستخدم
  `handleError(error, msg, { silent401: true })`.
- قبل ما تعتبر أي تعديل فرونت إند "خلص"، شغّل `npx tsc --noEmit -p tsconfig.json`
  وتأكد من `exit code 0`. **باقي +15 خطأ drift طبيعي عن baseline الموثقة
  (1253) غير مرتبط بشغلنا — تم تأكيده عبر git stash مقارنة، راجع
  PROGRESS_LOG.md بتاريخ 2026-08-10.**
- **مكتشف مهم:** حذف `auth_router` في Phase 4 بيقفل تلقائيًا فجوة أمنية
  كانت موثقة في PROJECT_AUDIT.md §5.1 — كان `auth_router` هو الاستثناء
  الوحيد المسجَّل بدون `dependencies=[Depends(require_sector(...))]`.

---

## معايير الترميز (ملخّص من CODING_STANDARDS.md)

**Backend (Python/FastAPI):**
- `async/await` إجباري لكل I/O (DB, HTTP, Redis).
- `pydantic` لكل Schemas (مدخلات ومخرجات).
- تسمية واضحة (`user_id` مش `uid`).
- تنسيق عبر `Black` + `isort`.
- اختبارات `pytest`، تغطية ≥ 80%.

**Frontend (Next.js/TypeScript):**
- TypeScript إجباري، بدون `any` عشوائي.
- الأنواع من `openapi-typescript` (مولّدة تلقائيًا، ما تكتبهاش يدوي).
- `ESLint` + `Prettier`.
- `React Query` لإدارة حالة السيرفر.

**IaC:**
- كل الموارد عبر Terraform.
- Kustomize لإعدادات Kubernetes.
- GitHub Actions + OIDC للمصادقة مع AWS.

---

## نقاط ضعف معروفة في المشروع (من PROJECT_AUDIT.md) — لا تتجاهلها لو لمست هذي الدومينز

- **`iot` و`privacy`**: صفر أعمدة `tenant_id` في 6 و4 جداول على التوالي —
  ثغرة عزل بيانات حرجة، ممنوع الإطلاق متعدد المستأجرين قبل السد الكامل.
  (P0 عالج جزء منها — راجع `PROGRESS_LOG.md` قبل الافتراض إنها لسه موجودة).
- **`admin`**: دومين شبه فارغ وغير موصول بـ `main.py` إطلاقًا (متغير الراوتر
  اسمه `admin_router` مش `router`).
- **`finance`, `projects`, `realestate`, `iot`**: خطأ تسمية `_init__.py`
  بدل `__init__.py`.
- **`invoicing`**: لا يوجد `__init__.py` إطلاقًا، ولا واجهة فرونت إند مقابلة.
- **`entities` مقابل `sovereign-entities` (Frontend)**: تكرار كامل بأسماء
  ملفات مختلفة لنفس المفهوم — الاحتفاظ بـ `sovereign-entities/` هو القرار.
- **`PUT /api/ai/routing`**: محمي بـ `get_current_user` بس بلا فحص دور
  (role/superuser) — endpoint إداري حساس بحماية مستخدم عادي.
- **`GET /ready`, `GET /metrics`**: مفتوحان بالكامل بدون مصادقة — يُفترض
  حمايتهما على مستوى الشبكة (Ingress/NetworkPolicy) مش الكود.
- **باج `lit`/`@reown/appkit-ui` (web3-provider)**: يكسر كل صفحات الموقع
  بـ 500 في بيئة الديف. قديم جدًا (موجود من الـInitial commit، 01-07-2026).
  **غير مرتبط بأي شغل auth/identity.** بيمنع اختبار logout اليدوي في
  المتصفح لحد ما يتصلح. مهمة منفصلة تمامًا لسه محتاجة تُفتح.
- **مصدر الـ+15 خطأ tsc الإضافية عن baseline الموثقة (1253 → 1268)**: لم
  يُفحص بالتفصيل — خارج نطاق Phase 3/4، غير عاجل.

---

## قواعد عمل عامة لأي مهمة في المشروع

1. **`PROGRESS_LOG.md` سجل تراكمي فقط** — أي مهمة جديدة تُضاف كسطر جديد في
   الأسفل، لا يُحذف ولا يُعدَّل أي إدخال قديم أبدًا.
2. أي تغيير معماري كبير (زي دمج auth/identity، أو حل باج web3) يحتاج
   **موافقة صريحة في جلسة منفصلة** قبل تنفيذه — لا تفترض الموافقة من مجرد
   التخطيط.
3. عند الشك في نطاق ملف أو دومين، ارجع لـ `PROJECT_AUDIT.md` قبل الافتراض.
4. **قبل أي "اكتمال" لخطوة تلمس auth/identity flow الفعلي (login, logout,
   session)**: لا تكتفِ بـ `tsc` نظيف كدليل. اطلب اختبار يدوي حقيقي في
   متصفح، ووثّق حالته بدقة (نجح / فشل / معلّق) — لا تدّعِ تحقق لم يحصل.
