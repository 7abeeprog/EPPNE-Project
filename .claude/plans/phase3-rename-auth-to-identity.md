# Phase 3 — رينيم components/auth و hooks/auth إلى identity

> **ملاحظة:** الملف الأصلي `.claude/plans/delightful-kindling-wigderson.md`
> غير موجود لا في شجرة العمل ولا في تاريخ git (تأكيد كامل بتاريخ
> 2026-08-09). هذا ملف جديد مستقل باسم مختلف عمدًا، لتوثيق Phase 3 فقط،
> مبني على `.claude/skills/eppne-project/SKILL.md` و`PROGRESS_LOG.md`
> والنطاق المتفق عليه صراحة سطرًا بسطر في جلسة 2026-08-09.

## السياق العام (مراحل سابقة، مكتملة)

| Phase | النطاق | الحالة |
|---|---|---|
| 0 | Backend: إصلاح 3 انهيارات حرجة | ✅ مكتمل |
| 1 | Backend: آلية جلسة حقيقية في identity | ✅ مكتمل، مُتحقَّق E2E |
| 2 | Frontend: إعادة بناء كامل cookie-only على identity | ✅ مكتمل (commit `5b1d241`) |
| 3 | **هذا الملف** | 🔄 موافَق على النطاق، بانتظار إذن التنفيذ |
| 4 | Backend: حذف دومين auth بالكامل | ⏳ لم يبدأ، مسودة منفصلة لاحقًا |

## الهدف

توحيد التسمية بس (المنطق موحّد فعلًا من Phase 1/2). صفر لمس منطق.

## خارج النطاق صراحة

- `app/(auth)/` (route group) — الاسم وأي URL فعلي (`/login`, `/register`) بدون تغيير.
- كل export/hook name (`useAuth`, `useLogin`, `useLogout`, `useRegister`,
  `useMe`, `useUserProfile`, `useUpdateProfile`, `useActiveSessions`,
  `useRevokeAllSessions`, `useChangePassword`, `useCurrentUser`) — بدون تغيير.

## 1) الملفات المنقولة (git mv) — 8 ملفات

`components/auth/` → `components/identity/`:
`SessionsList.tsx`, `SessionCard.tsx`, `RegisterForm.tsx`, `LoginForm.tsx`,
`ChangePasswordForm.tsx`, `ProfileForm.tsx`

`hooks/auth/` → `hooks/identity/`:
`useAuth.ts`, `useUserProfile.ts`

تحديث مصاحب: تعليق المسار الذاتي برأس 7 من الـ8 ملفات (كلهم ما عدا
`LoginForm.tsx` اللي مالوش تعليق زي ده). الاستيرادات الداخلية النسبية
(`./SessionCard` في SessionsList، `./useAuth` في useUserProfile) **بدون
تغيير**.

## 2) الملفات المحدَّث فيها سطر import فقط — 15 ملف (22 سطر)

| # | الملف | الفئة |
|---|---|---|
| 1 | `providers/AuthProvider.tsx` | A (صفر onClick/mutate) |
| 2 | `hooks/communications/useWebSocket.ts` | A |
| 3 | `components/layout/sidebar.tsx` | **C** — سطر import 114، سطر logout الفعلي 1433 (لا يُلمس) |
| 4 | `components/layout/navbar.tsx` | **C** — سطر import 18، سطر logout الفعلي 92 (لا يُلمس) |
| 5 | `app/(dashboard)/health/emergency/page.tsx` | B (onClick لـgetLocation/emergency call) |
| 6 | `app/(dashboard)/finance/admin/page.tsx` | B (onClick لـmint/exchange rates) |
| 7 | `app/(dashboard)/settings/sessions/page.tsx` | B (`revokeAllMutation.mutate()` — إلغاء جلسة، مش logout) |
| 8 | `app/(dashboard)/ai-agents/page.tsx` | B |
| 9 | `app/(dashboard)/ai/approvals/page.tsx` | B |
| 10 | `app/(dashboard)/digital-twin/page.tsx` | B |
| 11 | `app/(dashboard)/dashboard/page.tsx` | B (onClick كله router.push للتنقل) |
| 12 | `app/(dashboard)/profile/page.tsx` | A — 4 سطور import |
| 13 | `app/(dashboard)/privacy/settings/page.tsx` | B |
| 14 | `app/(auth)/register/page.tsx` | A — اسم `(auth)`/URL بدون تغيير |
| 15 | `app/(auth)/login/page.tsx` | A — اسم `(auth)`/URL بدون تغيير |

## 3) تصنيف الحساسية (فحص فعلي بالـgrep على كل ملف)

- **فئة A — صفر onClick/mutate في الملف كله (8 ملفات):** `useAuth.ts`,
  `useUserProfile.ts`, `SessionCard.tsx`, `AuthProvider.tsx`,
  `useWebSocket.ts`, `profile/page.tsx`, `register/page.tsx`, `login/page.tsx`.
- **فئة B — onClick/mutate حقيقي، لمنطق غير logout (13 ملف):**
  `SessionsList.tsx` (revoke-all), `ProfileForm.tsx` (update profile),
  `LoginForm.tsx` (login), `ChangePasswordForm.tsx` (change password),
  `RegisterForm.tsx` (register), `settings/sessions/page.tsx` (revoke-all),
  `health/emergency`, `finance/admin`, `privacy/settings`, `ai-agents`,
  `ai/approvals`, `digital-twin`, `dashboard/page.tsx` (business actions).
- **فئة C — استدعاء logout فعلي، أعلى حساسية (2 ملف):**
  `sidebar.tsx` سطر 1433، `navbar.tsx` سطر 92.

**الخطة لا تلمس أي سطر في فئتي B وC — فقط سطر الimport (والتعليق الذاتي
للملفات المنقولة من فئة A/B).**

## 4) شرط اختبار المتصفح — غير مشروط لملفات فئة C

- **21 ملف (فئة A+B):** `tsc --noEmit` نظيف = كفاية، بدون اختبار متصفح،
  لأنه import-only بلا أي قرب من منطق logout.
- **`sidebar.tsx` و`navbar.tsx` (فئة C) تحديدًا:** اختبار يدوي في المتصفح
  لزرار logout **إجباري دايمًا بعد التنفيذ**، بصرف النظر عن كون التغيير
  "import-only" نظريًا — لأن نفس الملفين دول اتكسرا بصمت قبل كده (زرار
  navbar كان بلا `onClick` إطلاقًا، بدون أي خطأ `tsc`)، فالتحقق اليدوي
  فيهم تأمين إضافي غير قابل للتنازل.
- **لو أي انحراف غير متوقع أثناء التنفيذ استلزم لمس سطر منطق فعلي (مش بس
  import) في أي ملف** — وقف فورًا واعرض على المستخدم قبل الاستكمال.

## 5) خطوات التنفيذ

1. `git mv` للـ8 ملفات.
2. تحديث تعليق المسار الذاتي (7 ملفات).
3. تحديث 22 سطر import في 15 ملف.
4. `grep` نهائي شامل: صفر بقايا `@/components/auth` أو `@/hooks/auth`.
5. `npx tsc --noEmit -p tsconfig.json` على كامل المشروع (exit 0 مطلوب).
6. اختبار يدوي في المتصفح لزرار logout في `sidebar.tsx` و`navbar.tsx`
   (إجباري، انظر §4).
7. توثيق في `PROGRESS_LOG.md` (بند جديد، بدون تعديل قديم): نتيجة tsc +
   نتيجة اختبار المتصفح لكل من الزرّين صراحة.

## 6) معيار النجاح

- `tsc --noEmit` نظيف على كامل المشروع.
- صفر نتائج `grep -r "components/auth\|hooks/auth"` في `eppne-web/`
  (باستثناء `app/(auth)/` كاسم مجلد — سلسلة مختلفة بسبب الأقواس).
- `git diff --stat`: بالظبط 8 rename + 15 ملف تعديل import.
- زرار logout شغال فعليًا (متأكَّد يدويًا في المتصفح) في sidebar وnavbar.

---

## Phase 4 (عنوان فقط، لاحقًا)

حذف دومين `auth` بالكامل من الـBackend، بعد التأكد من صفر اعتماد متبقٍّ.
لا يبدأ إلا بموافقة صريحة منفصلة.
