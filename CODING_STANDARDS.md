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

## 3. البنية التحتية (IaC)
- جميع الموارد يجب أن تُعرَّف عبر Terraform.
- استخدام Kustomize لإدارة إعدادات Kubernetes المختلفة.
- استخدام GitHub Actions مع OIDC للمصادقة مع AWS.