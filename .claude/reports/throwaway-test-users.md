# مستخدمو/تينانتات الاختبار throwaway المُعاد استخدامهم عبر جلسات سويپ IDOR

> ملف مرجعي مركزي — **ليس سجل جلسة**. يُحدَّث كلما تغيّر شيء في بيانات
> الاختبار المُعاد استخدامها (كلمة سر، دور، تينانت) بدل ما كل جلسة سويپ
> جديدة تتفاجأ بفشل تسجيل دخول أو تعيد إنشاء مستخدمين مكرّرين.
> **لا يُستخدم لأي بيئة إنتاج — DB محلي فقط (`eppne_v2`، `localhost:5435`).**
> **تصحيح [2026-08-29]:** البورت كان موثَّقًا خطأً `5433` — تلك الحاوية (`postgres-eppne`)
> ليس فيها حتى قاعدة بيانات `eppne_v2` إطلاقًا (`InvalidCatalogNameError`). البورت الصحيح
> المؤكَّد حيًا `5435` (حاوية `eppne_db`)، مطابق لـ`DATABASE_URL` في `.env`.

---

## المستخدمون

| id | username | email | tenant_id | system_role | كلمة السر الحالية | آخر تحديث |
|---|---|---|---|---|---|---|
| 772 | `TEST_super_a` | `TEST_super_a@example.com` | 1 (Local Test Tenant) | `SUPER_ADMIN` | `TEST_pass_batch3_2026` | 2026-08-25 (جلسة `batch3-audit-security-transport-logistics-manufacturing-tourism-sports`) |
| 773 | `TEST_instr_a` | — | 1 (Local Test Tenant) | `SUPER_ADMIN` | `TEST_pass_dtwin_2026` (لم تُلمَس هذه الجلسة) | 2026-08-24 (جلسة `digital-twin-idor-fix`) |
| 774 | `TEST_instr_b` | `TEST_instr_b@example.com` | 16 (`TEST_TENANT_B`) | `SUPER_ADMIN` | `TEST_pass_batch3_2026` | 2026-08-25 (جلسة `batch3-audit-security-transport-logistics-manufacturing-tourism-sports`) |

**ملاحظة [2026-08-25]:** كلمة سر `772`/`774` كانت فشلت (غير موثَّقة الأخيرة صح) — أُعيد تعيينها لكلمة سر جديدة موحّدة (`TEST_pass_batch3_2026`) عبر نفس آلية `passlib`/`bcrypt`. **مهم لأي جلسة قادمة:** تسجيل الدخول كـ`TEST_instr_b` (تينانت16) يتطلب إرسال هيدر `X-Tenant-ID: 16` مع طلب `/identity/login` نفسه — `login` يفلتر بـ`username/email` **و**`tenant_id` (من الهيدر، افتراضي=1) معًا، فبدون الهيدر الصحيح تسجيل الدخول يفشل بـ"بيانات الدخول غير صحيحة" حتى لو كلمة السر صحيحة.

**اكتشاف بنيوي إضافي [2026-08-25]:** وُجد أن `user_id=774` له **محفظتان حقيقيتان** فعليًا: `wallets.id=747` (`tenant_id=1`، فارغة) و`wallets.id=930` (`tenant_id=16`، محفظته الحقيقية). محفظة `id=747` على الأرجح "محفظة شبح" نتجت من جلسة سابقة استخدمت هيدر مزوَّر بمعزل عن أي كتابة IDOR فعلية — راجع تقرير `batch3-audit-security-...` لتفاصيل كيف هذا النمط ("محفظة شبح فارغة بدل محفظة الضحية الحقيقية") أثبت أن هجمات `finance.transfer` عبر هيدر مزوَّر **لا تسرق رصيد حقيقي لأي مستخدم آخر أبدًا** — نفس الاستنتاج الموثَّق مسبقًا لـ`finance` في `critical-finding-xtenant-systemic.md`.

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

---

## بيانات throwaway إضافية غير-مستخدمين (AI Agents)

**[2026-09-08] وكيل AI حقيقي — أُنشئ عمدًا للاختبار الحي، تُرك موجودًا بقرار
المستخدم (جلسة `paginatedresponse-misuse-fix`):**

| id | name | role | status | owner_id | tenant_id | الغرض |
|---|---|---|---|---|---|---|
| 216 | `TEST_automation_support_agent` | `SUPPORT` | `ACTIVE` | 772 (`TEST_super_a`) | 1 | إثبات حي إن `GET /automation/ai-agents` (بعد إصلاح `automation/service.py:1045` — `agents.data` بدل `agents`) بيرجّع بيانات وكيل حقيقي فعليًا، مش قائمة فاضية |

أُنشئ عبر الـAPI الرسمي (`POST /api/ai/agents` ثم `PATCH
/api/ai/agents/216/status` لتفعيله)، مش SQL مباشر. **صفر تعديل schema أو
بيانات إنتاج — تينانت الاختبار (1) فقط.** لأي جلسة قادمة تحتاج وكيل AI
حقيقي `ACTIVE` مملوك لـ`TEST_super_a` تحت تينانت 1، هذا الوكيل جاهز
للاستخدام بدل إنشاء وكيل جديد.
