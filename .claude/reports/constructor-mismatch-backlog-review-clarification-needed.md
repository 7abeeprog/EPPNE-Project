# جلسة مراجعة constructor-mismatch-backlog-classification.md — بانتظار توضيح

**تاريخ:** 2026-08-26
**الحالة:** 🔴 متوقفة — بانتظار رد المستخدم على السؤال أدناه. صفر تنفيذ حتى الآن.

---

## المطلوب أصلاً

مراجعة كاملة لـ`.claude/reports/constructor-mismatch-backlog-classification.md`، ثم عرض **كل
البنود المتبقية غير المُصلَحة** — بعد استبعاد:
1. البنود #23 إلى #26.
2. أي بند تم إصلاحه *سابقًا اليوم* عبر جلستي **`technical-debt-cleanup`** و**`backend-bugs-cleanup`**.

المطلوب: جدول شامل مصنَّف حسب سهولة الإصلاح (سطر واحد / migration بسيطة / قرار تصميمي)، **للموافقة فقط — صفر تنفيذ فوري**، مكتوب في ملف تقرير جديد.

---

## المشكلة اللي أوقفت التنفيذ

بحثت في الريبو (`grep`/`glob` شامل على أسماء الملفات والمحتوى + `git log`) عن جلستي
`technical-debt-cleanup` و`backend-bugs-cleanup` بالاسم الحرفي ده — **صفر نتيجة**، لا كملف
تقرير (`.claude/reports/*.md`)، ولا كملف خطة (`.claude/plans/*.md`)، ولا كرسالة commit.

اللي لقيته بدل كده تعديلات **غير مُلتزَم بها (uncommitted)** حاليًا في:
- `eppne-backend/app/core/security.py` — إلغاء `require_sector` + إضافة `SUBSCRIPTION_CHECK_EXEMPT_SERVICES`
- `eppne-backend/app/main.py` — إزالة `Depends(require_sector(...))` من تسجيل الراوترات
- `eppne-backend/app/domains/health/service.py` — تمرير `tenant_id` لمنشئ `FinanceService`
- `eppne-backend/app/tasks/affiliate.py` — تمرير `tenant_id` لمنشئ `AffiliateService`
- `eppne-backend/app/tasks/billing.py` — تمرير `tenant_id` لمنشئات `AIAgentsService`/`FinanceService`
- `eppne-backend/tests/conftest.py` — إضافة fixture `db` حقيقي (regression tests)

هذه التعديلات **لا تحمل نفس الاسمين** ولا تُطابق حرفيًا أي بند مرقّم بعلامة ✅ داخل
`constructor-mismatch-backlog-classification.md` (البنود المُعلَّمة ✅ فعليًا هناك: #25، #27
جزئيًا، #44، #46، #47 — كلها مؤرَّخة 2026-08-26 لكن بأسماء جلسات مختلفة تمامًا:
`batch5-audit-security-...`، `frontend-url-prefix-comprehensive-audit-session-log.md`).

---

## السؤال المطروح للمستخدم

سألت عبر AskUserQuestion عن مصدر الاستبعاد الصحيح، وكانت الخيارات:
1. التغييرات غير المُلتزَمة الحالية (uncommitted) المذكورة فوق.
2. فقط ما هو مُعلَّم ✅ فعليًا داخل الملف نفسه (بغض النظر عن اسم الجلسة).
3. أسماء مختلفة/جلسة أخرى.

**رد المستخدم:** اختار **"أسماء مختلفة/جلسة أخرى — سأوضح"** — ثم طلب أكتب السؤال في ملف
بدل التيرمنال (هذا الملف)، بدون ما يوضح الأسماء الصحيحة بعد.

---

## المطلوب من المستخدم الآن

يرجى الرد بأحد الآتي (في المحادثة، أو بالتعديل المباشر في هذا الملف):

- الاسمين الصحيحين للجلستين (أو مكان ملفاتهما لو موجودة بمسار غير معتاد)، **أو**
- تأكيد إن قائمة البنود ✅ الموجودة فعليًا داخل `constructor-mismatch-backlog-classification.md`
  (بأسمائها الحالية: `batch5-audit-security-...`، `frontend-url-prefix-comprehensive-audit-...`)
  هي المقصودة فعلاً بـ"technical-debt-cleanup"/"backend-bugs-cleanup" (يعني الاسمين كانا وصف
  عام مش اسم ملف حرفي)، **أو**
- تفاصيل يدوية عن إيه اللي اتصلح تحديدًا (أسماء بنود/أرقام) لو مفيش ملف تقرير مكتوب أصلاً.

بمجرد التوضيح، هكمل الجرد والتصنيف والجدول النهائي في ملف تقرير جديد منفصل، بصفر تنفيذ فوري
كما طُلب أصلاً.
