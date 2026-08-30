# EPPNE - معايير الترميز (Coding Standards)

## 1. باك اند (Python/FastAPI)
- استخدام `async/await` في جميع الدوال التي تتعامل مع I/O (قاعدة البيانات، HTTP، Redis).
- استخدام `pydantic` للتحقق من صحة المدخلات والمخرجات في جميع الـ Schemas.
- تسمية المتغيرات بشكل واضح (مثل `user_id` بدلاً من `uid`).
- استخدام `Black` و `isort` لتنسيق الكود بشكل تلقائي.
- كتابة اختبارات باستخدام `pytest` مع تغطية لا تقل عن 80%.

## 2. فرونت اند (Next.js/TypeScript)
- استخدام TypeScript بشكل إلزامي.
- استخدام الأنواع المُولَّة تلقائياً من `openapi-typescript`.
- استخدام `ESLint` و `Prettier` لتنسيق الكود.
- استخدام `React Query` لإدارة الحالة الخادمة.
- **حقول Decimal/condecimal الراجعة من الباك إند تصل كـ`string` في الـJSON**
  (قرار Pydantic متعمَّد للحفاظ على الدقة العشرية، مش باج). **ممنوع**
  التعامل معها كـ`number` مباشرة (`.toFixed()`، عمليات حسابية،
  `Number()`/`parseFloat()` بدون داعي) — أي حساب فعلي (مبلغ هيتبعت
  للباك إند) يُحسب في الباك إند حصريًا، الفرونت إند يعرض فقط. للعرض،
  استخدم `formatDecimalString()` من `eppne-web/lib/format.ts` حصرًا:

  ```ts
  // قبل — TypeError وقت التشغيل لأن sale_price_mrusdt string فعليًا
  {property.sale_price_mrusdt?.toFixed(2) || 'غير محدد'} MR_USDT

  // بعد
  {formatDecimalString(property.sale_price_mrusdt)} MR_USDT
  ```

  في `types/*.ts` اليدوية (غير `src/lib/api-types.ts` المولَّد)، حقل
  Decimal في schema استجابة لازم يتكتب `string` مش `number` — التسمية
  الخاطئة `number` هي اللي بتخلي `tsc` يفشل يمسك الاستخدام الخاطئ من
  الأساس. استثناء: أنواع الطلبات (Request/FormData) يصح تفضل `number`،
  لأن Pydantic Decimal بيقبل رقم JSON عادي في المدخلات — الفرق يهم بس في
  الاستجابات. استثناء تاني: endpoints الإحصائيات/الملخصات
  (`*StatsResponse`, `*SummaryResponse`) لو الباك إند بيحوّلها لـ`float`
  صراحة قبل الإرجاع — راجع الـschema الفعلي قبل الافتراض، مش كل الدومينات
  متسقة في هذا القرار. مرجع كامل: `.claude/reports/frontend-decimal-standard-convention-session-log.md`.

## 3. البنية التحتية (IaC)
- جميع الموارد يجب أن تُعرَّف عبر Terraform.
- استخدام Kustomize لإدارة إعدادات Kubernetes المختلفة.
- استخدام GitHub Actions مع OIDC للمصادقة مع AWS.