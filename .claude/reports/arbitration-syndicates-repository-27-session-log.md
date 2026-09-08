# #27 (بقية) — arbitration_syndicates repository missing methods — جلسة تحقيق فقط

**تاريخ:** 2026-08-29
**النطاق:** 5 دوال مُدَّعاة مفقودة/غلط (`get_cases_by_claimant`, `get_election_votes`,
`get_syndicate_memberships`, `list_user_licenses`, `list_candidates`) — **صفر تنفيذ حتى الموافقة**.
**الحالة:** 🔄 قيد التحقيق الحي.

---

## 0) السياق المرجعي (قبل بدء أي فحص)

- `constructor-mismatch-backlog-classification.md:200` — `list_user_cases` (دالة سادسة، **خارج
  نطاق الخمسة المطلوبين هنا**) اتصلحت فعلاً بتاريخ 2026-08-26 كأثر جانبي لإصلاح IDOR في
  `get_my_cases` — مؤكَّدة بقراءة الكود الحالي (`repository.py:23-32` فيها فلترة `tenant_id` +
  `claimant_id OR respondent_id` سليمة).
- `batch2-audit-security-service-marketplace-tenders-auctions-arbitration-syndicates.md` —
  الجلسة اللي اكتشفت البند الأصلي #27، فيها جدول أعطال (§7.7 وحواليها) يوثّق كل الدوال الخمسة
  + **دالة سادسة غير مذكورة في تعليمات هذه الجلسة: `list_syndicate_elections`** (سطر 110 من
  الملف: "`repo.list_syndicate_elections` — غير موجودة في `repository.py` إطلاقًا" →
  `AttributeError`/500 على `GET /syndicates/{id}/elections`).
- **ملاحظة تعليمات الجلسة الحالية تحتاج تصحيح:** طلب المستخدم ذكر "5 دوال" مسؤولة عن endpoint
  واحد لكل من الاثنين `GET /syndicates/{id}/elections` و`GET /elections/{id}/candidates` —
  لكن القراءة المباشرة للكود الحالي (قسم 1 تحت) تُظهر إن سبب عطل `GET /syndicates/{id}/elections`
  دالة **سادسة** (`list_syndicate_elections`) مش من الخمسة المذكورين. هتُعرض في جدول التصنيف
  كبند إضافي واضح، مش هتُدمَج ضمن الخمسة بصمت.

---

## 1) قراءة الكود المباشرة — حالة كل دالة (قبل أي تحقق حي)

قُرئت `repository.py`، `service.py`، `router.py` كاملة (٣ ملفات، غ. مقتطفات).

| # | الدالة | موجودة في `repository.py`؟ | من بيستدعيها ووين | نوع العطل المتوقع كوديًا |
|---|---|---|---|---|
| 1 | `get_cases_by_claimant` | ❌ لأ | `service.py:165` — لكن **فرع ميت**: `service.get_user_cases` بيعمل `hasattr(self.repo, 'list_user_cases')` أولًا (سطر 163) و`list_user_cases` **موجودة فعلاً** (مُصلَحة مسبقًا) → الشرط `True` دايمًا → `get_cases_by_claimant` **لا يُستدعى أبدًا حاليًا** | **لا يوجد عطل حي حاليًا** — كود ميت خطر (لو `list_user_cases` اتحذفت/تعطلت مستقبلًا هيرجع يشتغل بلا تحذير) |
| 2 | `get_election_votes` | ❌ لأ | `service.py:506` — داخل `cast_election_vote`، **فقط** في فرع إعادة تشغيل idempotency (لما `idempotency_key` يبقى مُخزَّن مسبقًا) | `AttributeError` — **لكن فقط عند retry بنفس `Idempotency-Key`** بعد نجاح تصويت سابق؛ التصويت الأول (الحالة الشائعة) ناجح بالكامل |
| 3 | `get_syndicate_memberships` | ❌ لأ | `service.py:319` — داخل `join_syndicate`، **فقط** في نفس فرع إعادة تشغيل idempotency | نفس النمط — `AttributeError` فقط عند retry، مش أول انضمام |
| 4 | `list_user_licenses` | ❌ لأ | `service.py:459` — لكن محمي بـ`hasattr` (سطر 458) اللي بيرجّع `False` → **يقع في `return []` دايمًا (سطر 460)، بلا استثناء إطلاقًا** | **صفر عطل ظاهر — صمت تام.** `GET /licenses/me` بيرجّع `200 []` لأي مستخدم بصرف النظر عن عدد تراخيصه الحقيقي |
| 5 | `list_candidates` | ✅ موجودة، لكن بتوقيع `(self, election_id)` فقط (سطر 118) | `service.py:489` بينادي `self.repo.list_candidates(election_id, tenant_id)` — **وسيطين** | `TypeError: list_candidates() takes 2 positional arguments but 3 were given` — على **كل** استدعاء، بلا استثناء |
| 6 (إضافي، غير مطلوب صراحة لكن مصدر endpoint مذكور في السياق) | `list_syndicate_elections` | ❌ لأ — صفر تطابق في `repository.py` (تأكيد `grep`) | `service.py:477` | `AttributeError` — على **كل** استدعاء، بلا استثناء |

**ملاحظة IDOR أولية من قراءة الكود (تُتحقَّق حيًا في القسم 3):**
- لا `list_candidates` (لو أُصلح الـarity بسذاجة بتمرير `tenant_id` زيادة فقط) ولا نموذج
  `ElectionCandidate` نفسه فيهم أي ضمان إن الـ`election_id` بتاع endpoint معين ينتمي فعلاً
  لتينانت المستخدم — الفحص الوحيد المحتمل يكون داخل `service.list_candidates`، وهو حاليًا
  **لا يتحقق من ملكية الانتخابات للتينانت إطلاقًا** قبل تمرير الطلب لـ repo (قارن بـ
  `service.get_election` اللي بيعمل `cast(int, election.tenant_id) != tenant_id`). يعني حتى
  لو أُصلح الـTypeError بسذاجة، فيه IDOR قراءة كامن هنا — يحتاج فحص حي.
- نفس الملاحظة لـ`list_syndicate_elections`: `service.list_syndicate_elections` (سطر 476-477)
  بيمرر `tenant_id` للدالة المفقودة مباشرة بلا أي تحقق ملكية `syndicate_id` قبلها — لو نُفِّذت
  الدالة المفقودة صح (بفلترة `tenant_id` داخل الاستعلام) هيبقى آمن، لكن لازم يتأكد إن التنفيذ
  المستقبلي فعلاً بيفلتر وملوش أي مسار تسريب.
- `get_syndicate_memberships`/`get_election_votes`: نفس المخاطرة الكامنة، لكن أثرهم محدود لأنهم
  بس بيرجّعوا بيانات لسجل أنشأه المستخدم نفسه بالفعل (إعادة عرض نتيجة عملية سابقة ناجحة)، مش
  استعلام مفتوح — أولوية IDOR أقل من `list_candidates`/`list_syndicate_elections`.

---

## 2) خطة التحقق الحي (التالي)

سكربت Python مباشر (async) ضد قاعدة البيانات المحلية (`eppne_v2`, `localhost:5435`)، بنفس
منهجية جلسة `translation_cache` (`#45-live-confirmation.md`) — بدون سيرفر uvicorn، استدعاء
مباشر لـ`ArbitrationSyndicatesService`/`Repository` بجلسة `AsyncSession` حقيقية، لتفادي وقت
إعداد سيرفر HTTP لخمس-ست دوال فقط. مستخدمو throwaway: `772`/تينانت1، `774`/تينانت16 (راجع
`throwaway-test-users.md` — **ملاحظة: البورت الموثَّق هناك `5433` يختلف عن `DATABASE_URL`
الحالي `5435`؛ هيُتحقَّق أيهما صحيح فعليًا قبل التنفيذ**).

خطوات مخطَّطة (صفر تنفيذ فعلي حتى الآن):
1. تأكيد بورت DB الصحيح.
2. `GET /licenses/me` (الأخطر) — استدعاء `service.get_user_licenses` مباشرة لمستخدم عنده ترخيص
   حقيقي مزروع مسبقًا (throwaway) → تأكيد إنه بيرجّع `[]` رغم وجود صف حقيقي في الجدول.
3. `GET /elections/{id}/candidates` — استدعاء `service.list_candidates` → تأكيد `TypeError`.
4. `GET /syndicates/{id}/elections` — استدعاء `service.list_syndicate_elections` → تأكيد
   `AttributeError`.
5. `get_election_votes`/`get_syndicate_memberships` — محاكاة فرع idempotency-replay مباشرة
   (استدعاء الدالة المفقودة زي ما `service.py` بينادّيها) → تأكيد `AttributeError`.
6. `get_cases_by_claimant` — تأكيد إنها كود ميت (مفيش استدعاء حي ممكن يوصلها حاليًا) — توثيق
   فقط، بلا حاجة "تحقق حي" فعلي لأنها غير قابلة للوصول.

**بعد التحقق الحي: عرض جدول تصنيف نهائي للموافقة، صفر تنفيذ إصلاح قبل موافقتك الصريحة.**

---

## 3) التحقق الحي — النتائج (منفَّذ، صفر إصلاح)

**المنهجية الفعلية:** بورت DB الصحيح تأكَّد `5435` (`eppne_db`، مطابق لـ`DATABASE_URL` الحالي في
`.env`) — **`throwaway-test-users.md` فيه معلومة بورت قديمة/خاطئة (`5433`)، الحاوية دي حتى مفيهاش
قاعدة بيانات `eppne_v2` إطلاقًا** (`InvalidCatalogNameError`). سيُصحَّح المرجع المركزي بعد موافقتك.

سكربت Python مباشر (`scratchpad/verify27.py`) — جلسة `AsyncSessionLocal` حقيقية من تطبيق الباك
إند نفسه (مش mock)، استدعاء `ArbitrationSyndicatesService`/`.repo` مباشرة (نفس الكائنات اللي
الراوتر الحقيقي بيستخدمها). زُرعت 3 صفوف throwaway مباشرة عبر SQL (تفادي بوابة `_check_saas_limits`
لأنها مش جزء من نطاق هذا البند، وplans الحاليين لتينانت1/16 ما فيهاش features `arbitration`/
`syndicates` مفعَّلة دلوقتي): `professional_licenses` (تينانت16/مستخدم774)، `syndicate_elections`
(تينانت1/نقابة1)، `election_candidates` (نفس الانتخابات). الثلاثة اتنضّفوا بالكامل بعد التحقق
(`post-cleanup count = 0` للثلاثة).

**النتائج (مطابقة 100% لتوقع قراءة الكود، بلا أي مفاجأة):**

| # | الاستدعاء الحي | النتيجة الفعلية | يطابق endpoint |
|---|---|---|---|
| 1 | `get_user_licenses(user_id=774, tenant_id=16)` رغم وجود صف حقيقي (`id=1`) في `professional_licenses` لنفس المستخدم/التينانت | `[]` — **صمت تام، بلا استثناء، بلا أي إشارة لعطل** | `GET /licenses/me` |
| 2 | `list_candidates(election_id=3, tenant_id=1)` | `TypeError: ArbitrationSyndicatesRepository.list_candidates() takes 2 positional arguments but 3 were given` | `GET /elections/{id}/candidates` |
| 3 | `list_syndicate_elections(syndicate_id=1, tenant_id=1)` | `AttributeError: 'ArbitrationSyndicatesRepository' object has no attribute 'list_syndicate_elections'` | `GET /syndicates/{id}/elections` |
| 4 | `repo.get_election_votes(election_id=3, tenant_id=1)` (محاكاة فرع idempotency-replay لـ`cast_election_vote`) | `AttributeError: ... has no attribute 'get_election_votes'` | لا يوجد endpoint مباشر — فقط retry بنفس `Idempotency-Key` بعد تصويت ناجح |
| 5 | `repo.get_syndicate_memberships(syndicate_id=1)` (محاكاة فرع idempotency-replay لـ`join_syndicate`) | `AttributeError: ... has no attribute 'get_syndicate_memberships'` | لا يوجد endpoint مباشر — فقط retry بنفس `Idempotency-Key` بعد انضمام ناجح |
| 6 | `hasattr(repo,'list_user_cases')` | `True` (و`hasattr(repo,'get_cases_by_claimant')` → `False`) | يؤكد: `get_cases_by_claimant` **كود ميت غير قابل للوصول حاليًا إطلاقًا** — `GET /cases/me` سليمة تمامًا حاليًا (مُصلَحة مسبقًا، خارج هذا البند) |

### فحص IDOR الحي المطلوب صراحة في التعليمات

**النتيجة: لا يوجد IDOR قابل للاستغلال حاليًا في أي من الخمسة/الستة — لأن كل استدعاء يفشل فورًا
(`TypeError`/`AttributeError`) قبل ما يوصل لأي منطق فلترة تينانت أصلًا.** هذا نفس نمط "تسريب كامن
غير قابل للاستغلال" الموثَّق سابقًا لبنود مشابهة في `batch2-audit-...md` (مثال: `service_marketplace
.get_my_licenses`, §7.2). لكن **الخطورة الكامنة تختلف حسب الدالة لو أُصلحت الأعطال بسذاجة (بلا
إضافة فلترة تينانت مقصودة أثناء الإصلاح):**

- **`list_candidates`** — الأخطر كامنًا: `service.list_candidates` (الطبقة الوسيطة) **لا يتحقق
  إطلاقًا** من ملكية `election_id` للتينانت الحالي قبل التمرير للـ repo (قارن بـ`service.get_election`
  اللي بيعمل `election.tenant_id != tenant_id` صراحة). لو الإصلاح كان مجرد "أضف `tenant_id` لتوقيع
  `repo.list_candidates` بلا استخدامه فعليًا في الفلتر" هيفضل IDOR كامل — أي مستخدم يقدر يقرأ مرشحي
  انتخابات أي تينانت تاني بمجرد تخمين `election_id`.
- **`list_syndicate_elections`** — نفس المخاطرة بالضبط: `service.list_syndicate_elections` بيمرر
  `tenant_id` للدالة المفقودة بلا أي تحقق ملكية `syndicate_id` قبله.
- **`get_syndicate_memberships`/`get_election_votes`** — خطورة أقل: بيُستدعوا فقط بعد عملية idempotent
  ناجحة (المستخدم نفسه أنشأ العضوية/الصوت لتوّه)، لكن **حتى في الاستخدام الحالي المقصود، `get_syndicate_memberships(syndicate_id)` بلا `tenant_id` إطلاقًا في نداء `join_syndicate`** — لو أُعيد استخدامها لاحقًا في مكان تاني بلا احتراس، ممكن تسرّب كل أعضاء نقابة عبر كل التينانتات (النموذج `SyndicateMembership.tenant_id` موجود لكن الاستدعاء الحالي مايستخدموش).
- **`get_cases_by_claimant`** — غير قابل للتقييم (كود ميت، مش هيتنفذ أبدًا في الوضع الحالي لـ
  `list_user_cases`).

---

## 4) جدول التصنيف النهائي — بانتظار موافقتك (صفر تنفيذ)

| # | الدالة | endpoint المتأثر | تصنيف العطل | IDOR محتمل لو أُصلح بسذاجة؟ | ملاحظة أولوية |
|---|---|---|---|---|---|
| 1 | `list_user_licenses` (+ `get_user_licenses` في service) | `GET /licenses/me` | **منطق أعمق** — مش مجرد سطر: الدالة المفقودة كليًا، والبديل الوحيد الموجود (`get_licenses_for_user`) بلا فلترة `tenant_id` إطلاقًا رغم إن `ProfessionalLicense.tenant_id` موجود في الموديل — لازم تُكتب من الصفر بفلترة `user_id` **و**`tenant_id` معًا (نفس نمط `list_user_cases` المُصلَحة) | ⚠️ متوسط — لو استُخدم `get_licenses_for_user` كما هو (بلا تعديل) بدل كتابة دالة جديدة، هيرجّع تراخيص المستخدم عبر كل التينانتات | **الأعلى أولوية** — الوحيدة اللي بتوهم المستخدم إن مفيش نتائج بدل إظهار عطل واضح |
| 2 | `list_candidates` (repository) | `GET /elections/{id}/candidates` | **سطر واحد ظاهريًا** (إضافة `tenant_id` للتوقيع) **لكن يخفي IDOR حقيقي** — لازم فلترة فعلية بـ`tenant_id` جوه الاستعلام + تحقق ملكية `election_id` في `service.list_candidates` (مفقود بالكامل حاليًا) | 🔴 **الأعلى كمونًا** — أي تخمين `election_id` صحيح يكشف مرشحي تينانت تاني لو اتصلح الـarity بلا فلترة حقيقية | عالية — نفس نمط IDOR اللي اتصلح للنقابات/القضايا في جلسة `batch2-audit` سابقًا |
| 3 | `list_syndicate_elections` (repository) — **دالة سادسة إضافية غير مذكورة صراحة في تعليمات الجلسة، لكنها السبب الفعلي الوحيد لعطل** `GET /syndicates/{id}/elections` | `GET /syndicates/{id}/elections` | **غير موجودة إطلاقًا** — تحتاج كتابة كاملة (لا يوجد كود سابق حتى بتوقيع غلط) | 🔴 نفس مستوى #2 — لازم فلترة `tenant_id` صريحة عند الكتابة | عالية — **يجب توضيح إنها مش من الخمسة المطلوبين أصلًا قبل أي تنفيذ** |
| 4 | `get_election_votes` (repository) | لا يوجد مباشر — فقط retry بـ`Idempotency-Key` بعد تصويت ناجح في `cast_election_vote` | **سطر واحد نسبيًا** — نمط مطابق لـ`get_jury_votes_for_case` الموجودة بالفعل (`election_id`+فلتر) | ⚠️ منخفض-متوسط — استخدامها الحالي محصور بعد عملية شرعية للمستخدم نفسه، لكن لازم `tenant_id` في الفلتر لو أُضيف param زيادة | منخفضة — Edge case نادر (retry فقط) |
| 5 | `get_syndicate_memberships` (repository) | لا يوجد مباشر — فقط retry بـ`Idempotency-Key` بعد انضمام ناجح في `join_syndicate` | **سطر واحد نسبيًا** — لكن نداء الخدمة الحالي بيمرر `syndicate_id` بس (بلا `tenant_id`) | ⚠️ منخفض-متوسط — نفس ملاحظة #4، بالإضافة لغياب `tenant_id` من توقيع النداء الحالي نفسه | منخفضة — نفس السبب |
| 6 | `get_cases_by_claimant` (repository) | لا شيء — **كود ميت غير قابل للوصول** (الفرع `hasattr` بيختار `list_user_cases` الصحيحة دايمًا) | **تنظيف فقط** — إما حذف الفرع الميت أو حذف الدالة تمامًا (قرارك) | لا ينطبق — لن يُنفَّذ أبدًا في الوضع الحالي | الأقل أولوية — صفر أثر وظيفي حاليًا، خطر مستقبلي فقط لو الظرف تغيّر |

---

## 5) القرارات المطلوبة منك قبل أي تنفيذ

1. **الأولوية:** أبدأ بـ#1 (`list_user_licenses`، الأخطر لأنه صامت) و#2/#3 (IDOR كامن)، ولا ترتيب تاني؟
2. **نطاق #3:** موافق إنها تُضاف رسميًا لنطاق البند رغم إنها مش من الخمسة المذكورين صراحة؟ (بدونها هتفضل `GET /syndicates/{id}/elections` معطوبة حتى لو الخمسة الأصليين اتصلحوا بالكامل)
3. **#6:** حذف الفرع الميت (`get_cases_by_claimant` + شرط `hasattr`) بالكامل من `service.py`، ولا حذف الدالة الميتة فقط وترك التبسيط لجلسة تانية؟
4. **تصحيح مرجعي منفصل (غير مرتبط بالتنفيذ):** تحديث بورت DB في `throwaway-test-users.md` من `5433` (خطأ/قديم) لـ`5435` (الصحيح المؤكَّد اليوم) — موافق؟

**صفر تنفيذ إصلاح حتى الآن، بانتظار توجيهك.**

---

## 6) التنفيذ — مكتمل، مؤكَّد حيًا لكل دالة (6/6)

**موافقتك على الأربعة قرارات:** الترتيب المقترح، ضم `list_syndicate_elections` رسميًا للنطاق،
حذف الفرع الميت بالكامل، تحديث بورت `throwaway-test-users.md` لـ`5435` — **الأربعة مُنفَّذة**.

**منهجية كل خطوة:** إصلاح الدالة → سكربت Python مباشر (نفس أسلوب §3) يزرع صف throwaway حقيقي
**+ صف "decoy" مصطنَع بنفس المعرِّف (`election_id`/`syndicate_id`) لكن `tenant_id` مختلف** → نداء
حي عبر نفس الكائنات اللي الراوتر الحقيقي بيستخدمها → تأكيد إن الفلترة `tenant_id` فعلية (مش موجودة
بس في التوقيع) عبر مسارين: الشرعي (بيرجّع بس صف تينانته) والهجوم (تينانت تاني بيرجّعله بس صفه
هو، مش صف الضحية) → تنظيف كامل + تأكيد `count = 0`.

| # | الدالة | التغيير | التحقق الحي | IDOR بعد الإصلاح؟ |
|---|---|---|---|---|
| 1 | `list_user_licenses` | دالة جديدة في `repository.py`، فلترة `user_id`+`tenant_id` معًا. `service.py` لم يُلمَس (شرط `hasattr` الموجود مسبقًا بقى `True` تلقائيًا) | صف حقيقي (تينانت16) + decoy (نفس `user_id`، تينانت1) → كل استدعاء رجّع صفه فقط | ✅ **لا يوجد** — الفلترة فعلية ومؤكَّدة بالاتجاهين |
| 2 | `list_candidates` | `repository.py`: أُضيف `tenant_id` للتوقيع + فلترة فعلية في `WHERE`. `service.py` مالوش تغيير (كان بينادي بوسيطين بالفعل) | نفس `election_id`، مرشح تينانت1 + decoy مرشح تينانت16 → كل تينانت شاف بس مرشحه | ✅ **لا يوجد** — أعلى بند خطورة كامنة، اتقفل بالكامل |
| 3 | `list_syndicate_elections` (إضافية، خارج الخمسة الأصليين) | دالة جديدة بالكامل في `repository.py` (كتابة من الصفر) | نفس `syndicate_id`، انتخاب تينانت1 + decoy انتخاب تينانت16 → عزل كامل مؤكَّد | ✅ **لا يوجد** |
| 4 | `get_election_votes` | دالة جديدة، فلترة `election_id`+`tenant_id` | نفس `election_id`، صوت تينانت1 + decoy صوت تينانت16 → عزل كامل | ✅ **لا يوجد** |
| 5 | `get_syndicate_memberships` | دالة جديدة **+ تعديل `service.py`** (نداء `join_syndicate` idempotency-replay كان بيمرر `syndicate_id` بس، بقى بيمرر `tenant_id` كمان) | نفس `syndicate_id`، عضوية تينانت1 + decoy عضوية تينانت16 → عزل كامل | ✅ **لا يوجد** |
| 6 | `get_cases_by_claimant` (كود ميت) | حذف الفرع بالكامل من `get_user_cases` في `service.py` — نداء مباشر لـ`list_user_cases` فقط | تأكيد إن `get_user_cases` لسه شغالة صح بعد الحذف (تينانت1 حقيقي + decoy تينانت16) + `hasattr(repo,'get_cases_by_claimant')=False` | لا ينطبق (تنظيف فقط) |

**النتيجة النهائية: صفر IDOR اتلقى أثناء التنفيذ في أي من الست دوال — كل واحدة اتقفلت بفلترة
`tenant_id` فعلية من أول تنفيذها، مش بعد اكتشاف تسريب لاحقًا (بعكس سيناريو `list_user_cases`
الأصلي في الجلسة السابقة).** كل بيانات throwaway اتنضّفت بالكامل بعد كل خطوة (`count=0` مؤكَّد
لكل جدول لمسناه). صفر migration، صفر تغيير schema.

**ملف مرجعي مُحدَّث:** `throwaway-test-users.md` — بورت `5433` (خطأ) → `5435` (صحيح، مؤكَّد حيًا
عبر محاولة اتصال فعلية بالحاويتين، `postgres-eppne`/`5433` طلعت مفيهاش قاعدة بيانات `eppne_v2`
إطلاقًا).

**الحالة النهائية:** ✅ **6/6 دوال مُصلَحة ومؤكَّدة حيًا بالكامل (هجوم مرفوض + مسار شرعي صحيح +
تنظيف مؤكَّد لكل واحدة). لم يُنفَّذ commit بعد — بانتظار موافقتك الصريحة على الـ`diff`.**

---

## 7) تأكيد كتابي صريح — ردًا على 3 أسئلة تحقق ما بعد التنفيذ [2026-08-29]

### سؤال 1 — `list_candidates`: هل كان فيه IDOR حقيقي فعلي قبل الإصلاح؟

**الإجابة المباشرة: لأ.** الفرق الجوهري عن `list_user_cases`:

**الدليل الحي — الحالة قبل أي تعديل في `repository.py`** (من أول سكربت تحقق نفَّذته في مرحلة
التحقيق، **قبل** لمس أي كود):

```
[2] list_candidates raised TypeError: ArbitrationSyndicatesRepository.list_candidates()
    takes 2 positional arguments but 3 were given
```

هذا الخطأ كان بيحصل **لأي استدعاء، بصرف النظر تمامًا عن هوية أو تينانت المستخدم** — مستخدم شرعي
بيطلب مرشحي انتخاباته هو نفسه كان بياخد نفس الـ`TypeError`/500 بالظبط اللي كان هياخده مهاجم بيحاول
يقرأ مرشحي تينانت تاني. **مفيش أي بيانات اتسربت لأي حد قبل الإصلاح — لأن مفيش استجابة ناجحة
حصلت أصلًا لأي طرف.** ده مختلف جوهريًا عن أنماط IDOR التانية الموثَّقة في `critical-finding-
xtenant-systemic.md` (زي `issue_verdict`) حيث الطلب الشرعي والطلب المزوَّر **الاتنين كانوا
بينجحوا**، والفرق كان بس في مين صاحب البيانات المُرجَعة.

**ليه كنت لسه محتاج أحذر؟** لأن `repository.list_candidates(election_id)` الأصلية كانت بتاخد
`election_id` بس، بلا أي إشارة لـ`tenant_id` في الاستعلام نفسه. لو كنت أصلحت الـ`TypeError`
بإضافة `tenant_id` **للتوقيع فقط** (عشان الاستدعاء بوسيطين ينجح) **بلا** استخدامه فعليًا في
`WHERE`، كان هيبقى فيه IDOR حقيقي جديد **من لحظة أول commit للإصلاح نفسه** — مش موجود قبل كده،
لكن كان هيتولد كأثر جانبي لإصلاح ساذَج. **هذا احتمال نظري كنت بتفاداه أثناء الكتابة، مش سلوك
حي رُصِد فعليًا في أي نسخة اتشغَّلت من الكود** (لا قبل الإصلاح ولا في نسخة وسيطة أثناءه — الإصلاح
اللي طبَّقته كان فلترة `tenant_id` من أول تعديل واحد، بلا مرحلة وسيطة بلا فلترة).

**الدليل الحي — بعد الإصلاح (سيناريو هجوم كامل، مقارنة مباشرة بمنهجية `list_user_cases`):**

بيانات الاختبار: انتخابات (`election_id=4`) خلقها تينانت1 (نقابة1). مرشح شرعي (`id=3`) تابع لنفس
الانتخابات، تينانت1. مرشح "صوري" (`id=4`) اتزرع بنفس `election_id=4` بالظبط لكن `tenant_id=16`
(محاكاة "لو تينانت16 كان عنده مرشح بنفس رقم الانتخابات" — سيناريو استغلال IDOR الكلاسيكي: تخمين
`election_id` بتاع تينانت تاني).

```
[legit] list_candidates(4, tenant=1) -> ids=[3] manifestos=['VERIFY27_LEGIT_CANDIDATE']
  PASS: only tenant-1's real candidate returned, decoy tenant-16 row NOT leaked

[cross-tenant attack] list_candidates(4, tenant=16) -> ids=[4] manifestos=['VERIFY27_DECOY_WRONG_TENANT']
  PASS: tenant-16 caller sees only their own decoy row, NOT tenant-1's real candidate manifesto
```

**تفسير النتيجة:** مهاجم تينانت16 بيطلب `GET /elections/4/candidates` (نفس `election_id` بتاع
تينانت1 بالظبط) — بيرجّعله بس صف تينانته هو (`id=4`)، **صفر رؤية لمرشح تينانت1 الحقيقي (`id=3`)
أو لمحتوى `manifesto` بتاعه**. الفلترة `ElectionCandidate.tenant_id == tenant_id` جوه الـ`WHERE`
هي اللي منعت التسريب.

**الخلاصة الدقيقة:** صفر IDOR حي اتلقى أو استُغل في أي لحظة (قبل أو أثناء أو بعد الإصلاح) — لكن
كان فيه **مسار محتمل لثغرة جديدة لو الإصلاح كان ساذَجًا**، واتقفل بالتصميم من أول تعديل.

---

### سؤال 2 — تأكيد التحقق الحي لكل الست دوال (مسار شرعي + هجوم عبر تينانتين + تنظيف)

**نعم، مؤكَّد. الجدول تحت فيه الدليل الحرفي (مقتطف مباشر من مخرجات كل سكربت، بلا تلخيص) لكل
دالة من الست — كل واحدة اتنفَّذت بنفس المنهجية: صف حقيقي + صف "صوري" بنفس المعرِّف المشترك لكن
`tenant_id` مختلف، نداء شرعي، نداء هجوم عبر تينانت، تنظيف، تأكيد `count=0`.**

**1) `list_user_licenses`** (تينانت16 حقيقي/774، صف "صوري" تينانت1 بنفس `user_id`):
```
[legit] get_user_licenses(774, 16) -> ids=[5] names=['VERIFY27_LEGIT']
  PASS: only the tenant-16 row returned, decoy tenant-1 row NOT leaked
[cross-tenant] get_user_licenses(774, 1) -> ids=[6] names=['VERIFY27_WRONG_TENANT']
  PASS: querying with tenant=1 returns ONLY the tenant-1 row, not the tenant-16 legit row
post-cleanup count professional_licenses: 0
```

**2) `list_candidates`** — راجع سؤال 1 فوق (نفس المخرجات الحرفية).

**3) `list_syndicate_elections`** (نفس `syndicate_id=1`، انتخاب تينانت1 حقيقي + انتخاب صوري تينانت16):
```
[legit] list_syndicate_elections(1, tenant=1) -> ids=[5] titles=['VERIFY27_STEP3_LEGIT']
  PASS: legit election 5 present, decoy tenant-16 election 6 NOT leaked
[cross-tenant attack] list_syndicate_elections(1, tenant=16) -> ids=[6] titles=['VERIFY27_STEP3_DECOY_WRONG_TENANT']
  PASS: tenant-16 caller sees only their own decoy election, NOT tenant-1's real election
post-cleanup count syndicate_elections: 0
```

**4) `get_election_votes`** (نفس `election_id=7`، صوت تينانت1 حقيقي + صوت صوري تينانت16):
```
[legit] repo.get_election_votes(7, tenant=1) -> ids=[1]
  PASS: only tenant-1's real vote returned, decoy tenant-16 vote NOT leaked
[cross-tenant] repo.get_election_votes(7, tenant=16) -> ids=[2]
  PASS: tenant-16 caller sees only their own decoy vote, NOT tenant-1's real vote
post-cleanup count election_votes: 0
post-cleanup count election_candidates: 0
post-cleanup count syndicate_elections: 0
```

**5) `get_syndicate_memberships`** (نفس `syndicate_id=1`، عضوية تينانت1 حقيقي + عضوية صورية تينانت16):
```
[legit] repo.get_syndicate_memberships(syndicate=1, tenant=1) -> ids=[3]
  PASS: only tenant-1's real membership returned, decoy tenant-16 membership NOT leaked
[cross-tenant] repo.get_syndicate_memberships(syndicate=1, tenant=16) -> ids=[4]
  PASS: tenant-16 caller sees only their own decoy membership, NOT tenant-1's real one
post-cleanup count syndicate_memberships: 0
```

**6) `get_user_cases` بعد حذف الفرع الميت** (تفاصيل كاملة في سؤال 3 تحت):
```
get_user_cases(772, tenant=1) -> ids=[4] reasons=['VERIFY27_STEP6_LEGIT']
  PASS: still works correctly after removing dead get_cases_by_claimant branch; tenant isolation intact
hasattr(repo, 'get_cases_by_claimant') = False (expected False)
post-cleanup count arbitration_cases: 0
```

**كل الست دوال: مسار شرعي ✅ + مسار هجوم عبر تينانت مرفوض بشكل صحيح ✅ + تنظيف مؤكَّد بـ`count=0`
✅. صفر دالة اتحقَّق منها بقراءة كود فقط بلا تنفيذ حي.**

---

### سؤال 3 — تأكيد حذف الكود الميت (`get_cases_by_claimant` + شرط `hasattr`)

**نعم، محذوف بالكامل. الدليل:**

**١. الـ`diff` الفعلي في `service.py`:**
```diff
     async def get_user_cases(self, user_id: int, tenant_id: int) -> List[ArbitrationCase]:
-        if hasattr(self.repo, 'list_user_cases'):
-            return await self.repo.list_user_cases(user_id, tenant_id)  # type: ignore
-        return await self.repo.get_cases_by_claimant(user_id, tenant_id)  # type: ignore
+        return await self.repo.list_user_cases(user_id, tenant_id)
```
لا الدالة الميتة `get_cases_by_claimant` ولا شرط `hasattr` باقيين — نداء مباشر ووحيد لـ
`list_user_cases`.

**٢. `get_cases_by_claimant` لم توجد في `repository.py` أصلًا** (كانت مُستدعاة بس، مش معرَّفة —
هي "الدالة الميتة" لأنها غير قابلة للوصول، مش لأنها اتحذفت من مكان موجودة فيه). تأكيد `grep`
شامل على مجلد `app/` بالكامل بعد كل التعديلات:
```
grep -rn "get_cases_by_claimant" app/    →   صفر نتائج (exit code 1)
```

**٣. تأكيد حي مباشر من مخرجات سكربت التحقق نفسه (سؤال 2، دالة #6):**
```
hasattr(repo, 'get_cases_by_claimant') = False (expected False)
```

**الخلاصة: الدالة الميتة محذوفة بالكامل من كل مسارات الاستدعاء، وشرط `hasattr` اللي كان بيغطي
عليها اتحذف من `service.py` زي ما اتفقنا بالظبط.**

---

**صفر commit لسه.** الملف ده + الـ`diff` الكامل جاهزين لمراجعتك النهائية قبل أي `git commit`.
