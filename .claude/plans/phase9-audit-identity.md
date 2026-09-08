# Phase 9 — مراجعة أمنية + جرد وظيفي لدومين identity

## السياق المرجعي
- راجع SKILL.md، PROGRESS_LOG.md، وphase8-master-roadmap.md قبل أي خطوة.
- identity هو أول دومين في المجموعة الاعتمادية (Group 1) من الخطة الرئيسية —
  أساس تقني لكل الدومينات التانية (auth/login/session).
- Phase 0-5 عالجت الدمج auth→identity بالكامل ومقفولة. هذه المراجعة
  مختلفة: مش عن الدمج، لكن مراجعة أمنية + وظيفية شاملة للدومين
  بحالته الحالية النهائية.
- Phase 7 اكتشفت إن فحص repository.py (عزل tenant_id المنطقي وقت
  الاستعلام الفعلي، مش بس وجود العمود) كان معلّق — لو identity فيه
  نفس النوع من الفحص المطلوب، يُدمَج هنا.

## المطلوب — 3 مخرجات إلزامية (read-only بالكامل، بدون أي تعديل كود)

### 1. تقرير أمني
لكل endpoint في identity/router.py و identity/protected_router:
- ما هو الـ dependency المستخدم؟ (get_current_user / get_current_superuser
  / core.security أو api.deps — انتبه للفرق الموثّق سابقًا بين النسختين)
- هل فيه فحص tenant_id فعلي في كل query بـ repository.py، مش بس وجود
  العمود في الجدول؟
- هل فيه input validation كافي (Pydantic schemas) على كل endpoint؟
- هل فيه rate limiting على endpoints حساسة (login, register, password
  reset)؟
- أي ثغرات مكشوفة أو endpoints بلا حماية كافية؟

### 2. جرد وظيفي (Functional Inventory)
جدول لكل endpoint في identity:
| Method | Path | الغرض | Input | Output | الحالة (شغال/مكسور/كود ميت) |

هذا الجرد أساس بناء user journey لاحقًا — لازم يكون دقيق ومبني على
قراءة فعلية للكود، مش افتراض من اسم الدالة.

### 3. تناغم Backend/Frontend
- كل endpoint في identity — هل له استهلاك فعلي في الفرونت إند
  (services/auth.service.ts أو أي service آخر)؟
- فيه أي endpoint يتيم (بلا استهلاك فرونت)؟
- فيه أي استدعاء فرونت لـ endpoint مش موجود أو معطوب؟

## قواعد صارمة
- read-only بالكامل — بدون أي تعديل كود أو migration.
- لو لقيت ثغرة أو مشكلة، وثّقها في الملف — لا تصلحها في هذه الجلسة.
  الإصلاح (لو احتاج) يكون phase منفصل بموافقة صريحة.
- لا تفترض "شغال" أو "آمن" بدون قراءة الكود الفعلي — لا نتائج مبنية
  على اسم الملف أو الدالة فقط.
- لو الفحص كشف إن حاجة معينة (زي tenant_id filtering) "غير مؤكدة"
  لأنها محتاجة اتصال DB حي، وثّق ده صراحة كـ"غير مؤكد" زي ما عملنا
  في Phase 7 — لا تفترض النجاح.
- اكتب النتائج في ملف جديد `.claude/plans/phase9-audit-identity-report.md`.
- بعد الانتهاء، وثّق ملخص في PROGRESS_LOG.md (إضافة فقط، بدون تعديل قديم).