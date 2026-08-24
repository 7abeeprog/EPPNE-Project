# مستخدمو/تينانتات الاختبار throwaway المُعاد استخدامهم عبر جلسات سويپ IDOR

> ملف مرجعي مركزي — **ليس سجل جلسة**. يُحدَّث كلما تغيّر شيء في بيانات
> الاختبار المُعاد استخدامها (كلمة سر، دور، تينانت) بدل ما كل جلسة سويپ
> جديدة تتفاجأ بفشل تسجيل دخول أو تعيد إنشاء مستخدمين مكرّرين.
> **لا يُستخدم لأي بيئة إنتاج — DB محلي فقط (`eppne_v2`، `localhost:5433`).**

---

## المستخدمون

| id | username | email | tenant_id | system_role | كلمة السر الحالية | آخر تحديث |
|---|---|---|---|---|---|---|
| 772 | `TEST_super_a` | `TEST_super_a@example.com` | 1 (Local Test Tenant) | `SUPER_ADMIN` | `TEST_pass_dtwin_2026` | 2026-08-24 (جلسة `digital-twin-idor-fix`) |
| 773 | `TEST_instr_a` | — | 1 (Local Test Tenant) | `SUPER_ADMIN` | `TEST_pass_dtwin_2026` | 2026-08-24 (جلسة `digital-twin-idor-fix`) |
| 774 | `TEST_instr_b` | `TEST_instr_b@example.com` | 16 (`TEST_TENANT_B`) | `SUPER_ADMIN` | `TEST_pass_dtwin_2026` | 2026-08-24 (جلسة `digital-twin-idor-fix`) |

**مستخدمون throwaway إضافيون موجودون بالفعل تحت تينانت1 (بادئة `TEST_`، لم تُحدَّث كلمة سرهم بعد — حدِّث هنا لو استُخدموا):** `775`/`TEST_student_a`، `776`/`TEST_applicant`، `777`/`TEST_employer`.

**ملاحظة مهمة:** قبل 2026-08-24، كانت هذه الحسابات مُستخدَمة عبر عدة جلسات سابقة
(`academy-idor-fix`, `sovereign-entities-idor-fix`, `ai-agents-idor-fix`, ...)
لكن **كلمة السر الأصلية لم تكن موثَّقة في أي مكان مركزي** — على الأرجح كل
جلسة كانت بتفترض أن حسابها لسه شغّال بجلسة تسجيل دخول (توكن) سابقة، أو
كانت بتعيد التوليد محليًا بلا توثيق. **كلمة السر الموثَّقة هنا (`TEST_pass_dtwin_2026`)
هي أول تعيين موثَّق رسميًا** — أُنشئت بتوليد `bcrypt` hash عبر `passlib`
(نفس مكتبة `app/core/security.py`) وتحديث عمود `users.hashed_password` مباشرة
عبر SQL (`UPDATE users SET hashed_password=... WHERE id IN (772,774)`).
**صفر تعديل كود أو schema — تعديل بيانات اختبار فقط.**

**لأي جلسة سويپ قادمة:** لو حاولت تسجّل دخول بحساب `772`/`774` وفشل
(كلمة سر غلط)، **الأرجح إن جلسة تانية غيّرت كلمة السر بعدك** — حدِّث الجدول
فوق بالقيمة الجديدة بدل ما تفترض الحساب معطوب.

---

## التينانتات

| id | name | الغرض |
|---|---|---|
| 1 | `Local Test Tenant` | التينانت "الشرعي" الافتراضي — تينانت A في كل سيناريوهات الهجوم عبر-التينانت |
| 16 | `TEST_TENANT_B` | التينانت "الضحية"/الثاني — تينانت B في كل سيناريوهات الهجوم عبر-التينانت |

---

## كيفية الحصول على `access_token` حي

```
POST /identity/login
{"username_or_email": "TEST_super_a", "password": "TEST_pass_dtwin_2026"}
```

نفس الشيء لـ`TEST_instr_b`. الحقل `username_or_email` هو اسم الحقل الحالي
في الـschema (مؤكَّد من جلسات سابقة، `academy-idor-fix-session-log.md` §3).
