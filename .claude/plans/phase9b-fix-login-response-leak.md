# Phase 9b — إصلاح تسريب البيانات في POST /identity/login

## السياق المرجعي
- راجع SKILL.md، PROGRESS_LOG.md، phase9-audit-identity.md/report.md
  قبل أي خطوة.
- اكتُشف ومؤكد بالكامل (بطلب curl حقيقي، مش افتراض): endpoint
  POST /api/identity/login بيرجّع الـ User ORM object الخام تقريبًا،
  بما فيه: hashed_password (bcrypt hash كامل)، wallet (بيانات مالية)،
  tenant الكامل، last_login_ip، last_login_user_agent، idempotency_key،
  session_version، admin_id، domain.
- السبب المرجّح: الـ endpoint مش مستخدم response_model صريح، فـ
  jsonable_encoder بيسلسل كل حقول الـ SQLAlchemy ORM object تلقائيًا.
- المقارنة المرجعية: POST /identity/register بيستخدم بالفعل
  response_model=UserResponse بشكل صحيح، ورجّع response نظيف 100%
  بدون أي حقول حساسة — هذا هو النمط المطلوب تطبيقه على login أيضًا.

## المطلوب
1. **فحص أول (read-only)**: اقرأ identity/router.py — دالة login بالظبط،
   شوف السطر اللي بيرجّع الـ response، وقارنه بدالة register.
2. **فحص UserResponse schema**: تأكد هل UserResponse (الموجودة بالفعل)
   مناسبة لإرجاعها من login كمان، ولا محتاجة تعديل بسيط.
3. **الإصلاح**: أضف response_model=UserResponse على login endpoint،
   وتأكد إن الـ return statement بيتوافق مع الـ schema (ممكن يحتاج
   تحويل صريح للـ ORM object لو مش بيحصل تلقائيًا).
4. **تحقق حقيقي (زي Phase 6/7/9)**: شغّل السيرفر محليًا، اعمل
   register + login بمستخدم تجريبي واضح الاسم، اعرض الـ response
   body الكامل، وتأكد إن hashed_password وباقي الحقول الحساسة
   اختفت تمامًا. بعدها cleanup (حذف المستخدم التجريبي) ووقف السيرفر.
5. شغّل أي pytest موجود متعلق بـ identity/login للتأكد من عدم كسر
   أي حاجة.
6. وثّق في PROGRESS_LOG.md (إضافة فقط).

## قواعد صارمة
- الإصلاح محدود بـ login endpoint فقط — لا تلمس أي endpoint تاني حتى
  لو لقيت نفس النمط في مكان تاني (وثّقه كملاحظة بس، لخطوة منفصلة).
- لا تعتبر الإصلاح "تم" بدون تحقق فعلي بـ curl (زي ما عملنا وقت
  الاكتشاف) — مش بس قراءة الكود أو "لازم يشتغل نظريًا".
- بعد أي اختبار فعلي، لازم cleanup كامل + إيقاف أي سيرفر تجريبي —
  بدون استثناء.
- لا تفتح أي ملفات تانية أو phase تانية من نفس الجلسة دي.