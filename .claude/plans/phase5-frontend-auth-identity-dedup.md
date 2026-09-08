# Phase 5 — حسم تكرار components/auth مقابل components/identity (Frontend)

## السياق المرجعي
- راجع `SKILL.md` (جذر المشروع) و`PROGRESS_LOG.md` قبل أي خطوة.
- Phase 4 اتقفلت وموثّقة (commit eeaf783): auth domain اتحذف بالكامل من
  الباك إند، identity هو المصدر الوحيد لـ /api/identity/*. صفر مسارات
  /auth في OpenAPI schema، pytest 5/5.
- الباك إند خلاص بالنسبة لـ auth/identity. المرحلة دي فرونت إند بس.

## المشكلة (موثّقة في PROJECT_AUDIT.md §6.2)
فيه 4 مكونات بنفس الاسم بالظبط موجودة في مجلدين مختلفين:
- `components/auth/`: LoginForm.tsx, RegisterForm.tsx, SessionCard.tsx, SessionsList.tsx
- `components/identity/`: نفس الأسماء + AuthProvider.tsx, ProfileForm.tsx, WalletCard.tsx

كمان `services/auth.service.ts` و`services/identity.service.ts` موجودين
معًا، وفيه إشارة إن `identity.service.ts` فيه مسارات مضاعفة خاطئة
(`/identity/identity/*`) محتاجة تأكيد.

من PROGRESS_LOG (2026-08-09، Phase 2 مكتملة): تم بالفعل حذف
`components/identity/*` بالكامل (7 ملفات) واستبدالها بنسخ في
`components/auth/*` (ده اسم المجلد بس المحتوى بقى identity-based).
**⚠️ لازم تتأكد إن ده لسه صحيح دلوقتي ومفيش تراجع أو تعارض حصل بعد Phase 3/4.**

## المطلوب (بالترتيب — read-only أولاً)
1. **فحص، مش تعديل**: `grep -r` على `eppne-web/app` و`eppne-web/components`
   لكل استيراد من `components/identity/` أو `services/identity.service.ts`
   القديمة، وتأكيد هل فعلاً محذوفة زي ما موثّق ولا لسه موجودة/متستخدمة.
2. لو فيه تكرار فعلي لسه موجود: حدد أي نسخة مستخدمة فعليًا في الصفحات
   الحية (`app/(auth)/login`, `app/(auth)/register`, إلخ) قبل ما تحذف
   أي حاجة.
3. حسم نهائي: نسخة واحدة بس، مسار واحد بس، بدون كود ميت.
4. `services/identity.service.ts`: تأكيد/تصحيح أي مسارات `/identity/identity/*`
   مضاعفة.
5. تحقق: `npx tsc --noEmit -p tsconfig.json` (exit code 0)، وبعدها اختبار
   يدوي حقيقي في المتصفح لـ: login, logout, register — مش تعويل على tsc
   بس (زي ما هو مبدأ ثابت في المشروع).
6. توثيق في PROGRESS_LOG.md كبند جديد بالتاريخ.

## قواعد صارمة
- ممنوع حذف أي حاجة قبل ما تتأكد إنها فعلاً مش مستخدمة في أي صفحة حية.
- باج web3/lit (lit/@reown/appkit-ui) — **منفصل تمامًا، ممنوع تتلمس هنا
  بدون موافقة صريحة منفصلة في جلسة تالتة**.
- لو لقيت أي اكتشاف جانبي مالوش علاقة بالنطاق ده، وثّقه في PROGRESS_LOG
  كملاحظة منفصلة وكمل، متتلهيش بيه.
- Phase 5 دي، مش Phase 6 — لو حسيت إنك عايز تفتح حاجة تانية بعد الانتهاء،
  استنى موافقة صريحة.