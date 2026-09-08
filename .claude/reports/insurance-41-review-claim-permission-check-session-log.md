# Backlog #41 — insurance.review_claim: issuer_entity_id vs reviewer_id mismatch

**Session date:** 2026-08-29
**Type:** Investigation only — zero code edits until explicit approval
**Trigger:** Surfaced during `constructor-mismatch-backlog` (2026-08-26/29),
documented with an explicit security warning in
`constructor-mismatch-backlog-classification.md`. Also one of the blockers
that prevented full live verification of Backlog #37
(`finance-transfer-payment-tx-hash-broken`) in `insurance.review_claim` —
that session verified at the repository level only, bypassing this specific
check.

**Problem as described:** In `insurance/service.py`, `review_claim`'s
authorization check compares two identifier spaces that may not be the same:

```python
if policy.issuer_entity_id != reviewer_id:
    raise PermissionDeniedError
```

`issuer_entity_id` looks like it references `sovereign_entities` (an entity
id), while `reviewer_id` looks like a `users.id` (the reviewing user). If
these two spaces are actually different, the comparison is either always
false (blocks everyone, including legitimate reviewers) or coincidentally
true/false depending on numeric overlap — not a real ownership check either
way.

**Pre-documented warning:** "الإصلاح الساذج قد يفتح ثغرة صلاحية مختلفة" —
same warning pattern seen previously with `sovereign_entities`/#32. Any fix
must be understood first, not patched quickly.

**Status:** IN PROGRESS

---

## Method

1. Read the full code around this check in `insurance/service.py` — what is
   `issuer_entity_id` (source table, semantic meaning), what is `reviewer_id`
   (source, likely `current_user.id`).
2. Determine precisely: is the current check dangerously permissive (lets
   anyone review any claim), wrongly restrictive (blocks a legitimate
   reviewer), or both depending on scenario? Confirm live (not just by
   reading code) with two scenarios: a real legitimate reviewer (confirm
   they can review), and an unauthorized same-tenant user (confirm
   blocked or not, document which).
3. Determine the correct intended logic: what real relationship should gate
   a reviewer's ability to review a given claim? Look at similar patterns
   in the project (e.g. command/saas ADMIN-role checks) for the established
   EPPNE pattern.

Present a classification table + proposed correct logic for approval —
**zero implementation** until reviewed together, especially given the
pre-documented security warning.

---

## Findings log

### Step 1 — الكود الفعلي حول فحص الصلاحية (اقتباسات سطور حقيقية)

**`eppne-backend/app/domains/insurance/service.py:400-432`** (الدالة كاملة حتى الفحص):

```python
400:    async def review_claim(
401-        self,
402-        claim_id: int,
403-        reviewer_id: int,
404-        tenant_id: int,
405-        approve: bool,
406-        approved_amount: Optional[Decimal] = None,
407-        notes: Optional[str] = None,
408-        idempotency_key: Optional[str] = None
409-    ) -> InsuranceClaim:
...
424:        claim = await self.repo.get_claim(claim_id)
425:        if not claim or cast(int, claim.tenant_id) != tenant_id:
426:            raise NotFoundError("Claim not found")
427:
428:        subscription = await self.repo.get_subscription(claim.subscription_id)
429:        policy = await self.repo.get_policy(subscription.policy_id)
430:
431:        if cast(int, policy.issuer_entity_id) != reviewer_id:
432:            raise PermissionDeniedError("Not authorized to review this claim")
```

**مصدر `issuer_entity_id`** — `eppne-backend/app/domains/insurance/models.py:52`:
```python
issuer_entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id", ondelete="CASCADE"), nullable=False, index=True)
```
معرِّف صف في جدول `sovereign_entities_v2` (كيان سيادي/مُصدِر البوليصة) —
**مساحة معرِّفات كيانات (entities)**، مش مستخدمين.

**مصدر `reviewer_id`** — `eppne-backend/app/domains/insurance/router.py:180-195`:
```python
180: async def review_claim(
...
187:    current_user: User = Depends(get_current_superuser),
...
191:    claim = await service.review_claim(
...
193:        reviewer_id=cast(int, current_user.id),
```
`reviewer_id` = `current_user.id` **مساحة معرِّفات مستخدمين (`users.id`)**
— مساحة مختلفة تمامًا وبلا أي علاقة منطقية بـ`sovereign_entities_v2.id`.

**اكتشاف إضافي مهم غيّر الصورة كاملةً — الراوتر أصلًا مُقيَّد بـ
`get_current_superuser`:**
`router.py:187` بيستخدم `Depends(get_current_superuser)`، يعني أي حد
مش superuser أصلًا **بيترفض 403 قبل ما يوصل لكود السيرفس بالكامل** —
الفحص جوه `review_claim` (سطر 431) مش أول خط دفاع، هو **فحص ثانٍ فوق
بوابة superuser موجودة بالفعل**.

`get_current_superuser` — `eppne-backend/app/core/security.py:164-170`:
```python
164: async def get_current_superuser(
165:     current_user: User = Depends(get_current_active_user)
166: ) -> User:
167:     role_value = current_user.system_role.value if hasattr(...) else current_user.system_role
168:     if role_value not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
169:         raise PermissionDeniedError("Superuser privileges required")
170:     return current_user
```
ده فحص **ثالث** مختلف تمامًا: `users.system_role` (دور منصة عالمي:
`SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`)، **غير مرتبط إطلاقًا** بـ
`sovereign_entities_v2` ولا بأي عضوية/تمثيل لكيان معيّن.

**خلاصة الصورة الكاملة (3 مساحات معرِّفات/أدوار مختلفة تمامًا في نفس المسار):**

| الفحص | أين | يقارن/يتحقق من | المساحة |
|---|---|---|---|
| 1 | `router.py:187` (`get_current_superuser`) | `current_user.system_role` | دور منصة عالمي (`users.system_role`) |
| 2 | `service.py:431` | `policy.issuer_entity_id != reviewer_id` | معرِّف كيان (`sovereign_entities_v2.id`) **مقابل** معرِّف مستخدم (`users.id`) |

الفحص التاني (سطر 431) بيقارن قيمتين من **مساحتين مختلفتين تمامًا** —
مفيش أي جدول `EntityMembership`/`sovereign_entities` بيتفحص هنا لمعرفة
هل `reviewer_id` (المستخدم) عنده تمثيل/عضوية حقيقية في الكيان
`issuer_entity_id`. **ده مش "منطق ملكية غلط" بس — ده مقارنة بلا معنى
منطقي إطلاقًا بين نوعين مختلفين من المعرِّفات.**

### Step 2 — النمط الصحيح المستخدَم فعليًا في المشروع لهذا النوع من العلاقة

بحث في `sovereign_entities/service.py` كشف إن فيه بنية تحتية جاهزة
ومُستخدَمة بالفعل بالضبط لهذا الغرض — **العلاقة الصحيحة بين مستخدم
وكيان بتتحدد عبر `EntityMembership`، مش عبر مقارنة IDs مباشرة**:

- `app/core/entity_membership_service.py` + `app/core/models.py` —
  `EntityMembership` (`entity_type`, `entity_id`, `user_id`, `tenant_id`,
  `role: EntityMembershipRole`)، حيث
  `EntityMembershipRole = {OWNER, EXECUTIVE_DIRECTOR, SIGNATORY, REPRESENTATIVE}`
  (`app/core/models.py:21-27`).
- `sovereign_entities/service.py:37`: `ENTITY_TYPE = "SOVEREIGN_ENTITY"` —
  الـ`entity_type` الثابت المستخدَم لكل صفوف `sovereign_entities_v2`.
- النمط المُستخدَم فعليًا في نفس الدومين (`sovereign_entities/service.py:548-557`):
  ```python
  async def _is_authorized_representative(
      self, entity_id: int, user_id: int, allowed_roles: List[EntityMembershipRole]
  ) -> bool:
      member = await self.membership.get_member(
          entity_type=ENTITY_TYPE, entity_id=entity_id, user_id=user_id,
      )
      return member is not None and member.role in allowed_roles
  ```
  ومثال استخدام حقيقي (`sovereign_entities/service.py:394`،
  `deposit_to_entity_wallet`):
  ```python
  if not await self._is_authorized_representative(entity_id, admin_user_id, [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]):
      raise PermissionDeniedError("Only owner or executive director can deposit to entity wallet")
  ```

**هذا هو النمط المعتمَد في EPPNE للسؤال "هل هذا المستخدم مخوَّل يتصرف
باسم هذا الكيان؟"** — مش أي مقارنة IDs مباشرة. `insurance/service.py`
**لا يستورد `EntityMembershipService` إطلاقًا حاليًا** (تأكَّد بالبحث
الكامل في الملف) — الفحص الحالي (سطر 431) بديل ساذج/خاطئ لمنطق
`EntityMembership` الصحيح المستخدَم في باقي المشروع لنفس السؤال بالضبط.

**ملاحظة جانبية غير مرتبطة، اتلاحظت أثناء القراءة (صفر لمس، مجرد
توثيق):** `_get_entity_email` (`insurance/service.py:54-55`) هي دالة
placeholder ثابتة `f"entity_{entity_id}@eppne.com"` — مش بحث حقيقي عن
بريد الكيان (`SovereignEntity.official_email`). مستخدَمة في مسارات
دفع premium حقيقية (سطر 200، 282) — احتمال بج منفصل تمامًا عن #41،
مش جزء من نطاق هذه الجلسة، موثَّق هنا للمرجعية بس.

### Step 3 — التحقق الحي (سكريبت تحقيقي مؤقت، صفر تعديل على كود المشروع)

بُني سيناريو حي كامل (كيان سيادي حقيقي → بوليصة → اشتراك → مطالبة) عبر
الـrepositories الحقيقية، واستُدعيت `InsuranceService.review_claim()`
الحالية (غير مُعدَّلة) مباشرة بثلاث قيم `reviewer_id` مختلفة، لتوصيف
السلوك الفعلي الحي للفحص الحالي (سطر 431):

- **سيناريو A** — مستخدم superuser حقيقي (`system_role=SUPER_ADMIN`)
  **و** عضو `EntityMembership` حقيقي بدور `OWNER` على نفس الكيان المُصدِر
  للبوليصة — أقرب تعريف ممكن لـ"مراجع شرعي" منطقيًا.
- **سيناريو B** — مستخدم حقيقي عشوائي، مش superuser، ومالوش أي علاقة
  بالكيان — يُفترض يترفض.
- **سيناريو C** — مستخدم حقيقي (لا superuser، لا عضوية) **بمحض
  الصدفة الرقمية** `user.id == entity.id` — لاختبار هل الفحص بيسمح
  بالخطأ لمجرد تطابق رقمي عرضي.

**النتائج الحية الفعلية (سكريبت `investigate_backlog41.py`، استدعاء مباشر
لـ`InsuranceService.review_claim()` غير المُعدَّلة، DB حقيقية، صفر mock):**

#### سيناريو A — أقرب تعريف ممكن لـ"مراجع شرعي"

مستخدم حقيقي: `system_role=SUPER_ADMIN` (نفس شرط `get_current_superuser`
في الراوتر) **و** عضو `EntityMembership` حقيقي بدور `OWNER` على نفس
الكيان `issuer_entity_id` بتاع البوليصة (نفس نمط
`_is_authorized_representative` المستخدَم في `sovereign_entities`).

```
entity.id=25  reviewer.id=1038  policy.issuer_entity_id=25
RESULT: BLOCKED with PermissionDeniedError: Not authorized to review this claim
```

**النتيجة: اتحجب.** حتى المراجع اللي بأي تعريف منطقي معقول (superuser +
مالك فعلي للكيان المُصدِر) بيترفض — الفحص الحالي (سطر 431) بيمنعه لمجرد
إن `25 != 1038` (معرِّف الكيان != معرِّف المستخدم، مساحتان مختلفتان
تمامًا). **دليل قاطع على إن الميزة معطّلة بالكامل حاليًا للمراجعين
الشرعيين.**

#### سيناريو B — مستخدم عشوائي مالوش أي علاقة

```
entity.id=26  reviewer.id=1041  policy.issuer_entity_id=26
RESULT: BLOCKED with PermissionDeniedError: Not authorized to review this claim
```

**النتيجة: اتحجب** (متوقَّع، ولو لسبب غلط — نفس رسالة الخطأ بالحرف
زي سيناريو A، يعني الفحص مش بيفرّق أصلًا بين الاتنين؛ كلاهما "false"
بنفس الطريقة العشوائية).

**ملاحظة حرجة على المقارنة بين A وB:** الفحص الحالي رجع **نفس النتيجة
بالحرف الواحد** (نفس الاستثناء، نفس الرسالة) للمراجع الشرعي المثالي
وللمستخدم العشوائي تمامًا. ده مش مجرد "فحص خاطئ" — **ده فحص عديم
الفائدة تمامًا حاليًا**: صفر قدرة تمييز بين الاتنين. النتيجة العملية:
**لا يوجد أي مسار عملي حاليًا لمراجعة أي مطالبة تأمين في الإنتاج** —
الميزة بأكملها معطّلة، مش بس فيها ثغرة.

#### سيناريو C — تصادم رقمي عرضي (`user.id == entity.id`)

```
No existing user with id=27 found in this DB -- cannot demonstrate
coincidental collision safely (would require forging a user id).
Skipping scenario C.
```

**النتيجة: اتخطى — غير قابل للتحقق حيًا في بيئة التطوير الحالية بدون
تلاعب مصطنع بمعرِّفات المستخدمين** (تسلسل `users.id` في هذه القاعدة
وصل بالفعل لأرقام كبيرة (~1000+) بسبب بيانات throwaway من جلسات سابقة،
بينما `sovereign_entities_v2.id` لسه في العشرات — تصادم طبيعي غير وارد
عمليًا في هذه البيئة تحديدًا). **هذا لا ينفي الخطر نظريًا** — لو
`entity_id` و`user_id` أُنشِئا من نفس نطاق تسلسلي متقارب (بيئة جديدة/
production مبكرة، أو حتى بالصدفة البحتة لاحقًا)، الفحص هيسمح بالخطأ
لمستخدم لا علاقة له بالكيان إطلاقًا. **موثَّق كمخاطرة بنيوية مؤكَّدة من
قراءة الكود (مساحتا معرِّفات مستقلتان تمامًا رياضيًا قابلتان للتصادم)،
مش مؤكَّدة بتجربة حية في هذه البيئة تحديدًا.**

**ملاحظة منهجية:** أثناء السكريبت التحقيقي، حصلت مرتين علقة/تعليق
(hang) غير متوقَّعة في مرحلة تنظيف البيانات (فتح `AsyncSessionLocal()`
متداخلة داخل سيشن مفتوحة بالفعل) — اتعاملنا معها بإيقاف العملية يدويًا
وتنظيف الصفوف المتبقية (`entity_id` 24، 27 + policies 62، 65 + 2
مستخدمين throwaway) بسكريبت تنظيف منفصل، مؤكَّد إن قاعدة البيانات
نظيفة الآن. **هذا التعليق خاص بالسكريبت التحقيقي نفسه (طريقة فتح
sessions متداخلة) — لا علاقة له بكود `insurance/service.py` أو
`review_claim` قيد الفحص، ولا يمثّل أي اكتشاف عن كود المشروع.**

### الخلاصة: تصنيف الفحص الحالي

| السؤال | الإجابة |
|---|---|
| هل الفحص الحالي permissive بشكل خطير (يسمح لأي حد)؟ | **لأ** — مؤكَّد حيًا: مستخدم عشوائي (سيناريو B) اتحجب فعليًا |
| هل الفحص الحالي restrictive بشكل خاطئ (يمنع المراجع الشرعي)؟ | **آه، بشكل قاطع** — مؤكَّد حيًا: superuser + مالك فعلي حقيقي للكيان (سيناريو A) اتحجب برضه، بنفس رسالة الخطأ اللي اتحجب بيها المستخدم العشوائي |
| هل فيه أي سيناريو حقيقي بيعدي من الفحص الحالي؟ | **لأ، غير عمليًا** — المسار الوحيد النظري هو تصادم رقمي عرضي بين `user.id` و`entity.id` (سيناريو C، مخاطرة بنيوية موثَّقة لكن غير قابلة للتفعيل حيًا في هذه البيئة) |
| **التصنيف النهائي** | **🔴 الميزة معطّلة بالكامل حاليًا لكل المستخدمين الشرعيين — مش "فيها ثغرة"، هي ببساطة لا تعمل. أي إصلاح يستبدل هذا الفحص لازم يستخدم `EntityMembership` الحقيقية، مش أي مقارنة IDs مباشرة.** |

---

## المنطق الصحيح المقترَح (للموافقة — صفر تنفيذ)

استبدال `service.py:431-432`:

```python
if cast(int, policy.issuer_entity_id) != reviewer_id:  # type: ignore
    raise PermissionDeniedError("Not authorized to review this claim")
```

بمنطق `EntityMembership` حقيقي، بنفس نمط `sovereign_entities/service.py`
(نفس الاستيراد `from app.core.entity_membership_service import
EntityMembershipService`، `from app.core.models import EntityMembershipRole`،
وثابت `ENTITY_TYPE = "SOVEREIGN_ENTITY"` نفسه المستخدَم هناك — لازم يكون
نفس القيمة بالحرف عشان `issuer_entity_id` بيشاور لنفس جدول
`sovereign_entities_v2`).

**خياران مطروحان للأدوار المسموح لها (`allowed_roles`) — قرار منتجي
يحتاج اختيارك:**

| الخيار | الأدوار المسموحة | التبرير | المخاطرة |
|---|---|---|---|
| **أ (الأضيق، الأقرب لنمط `deposit_to_entity_wallet` الموجود)** | `[OWNER, EXECUTIVE_DIRECTOR]` | نفس النمط المستخدَم فعليًا في `sovereign_entities/service.py:394` لعمليات مالية حساسة مشابهة (صرف من محفظة الكيان) — مراجعة مطالبة تأمين وصرف تعويض حقيقي عملية مالية بنفس الحساسية | قد تكون أضيق من اللازم لو فيه موظفين تشغيليين (`SIGNATORY`/`REPRESENTATIVE`) مفروض يراجعوا مطالبات يوميًا |
| **ب (أوسع)** | `[OWNER, EXECUTIVE_DIRECTOR, SIGNATORY]` | `SIGNATORY` منطقيًا "مخوَّل يوقّع/يعتمد" — قد يكون الدور المقصود فعليًا لمراجعة/اعتماد مطالبات (عملية توقيع اعتماد)، مش بالضرورة تحويل أموال مباشر زي `deposit`/`transfer` | توسيع الصلاحية عن النمط المرجعي الوحيد الموجود فعليًا في الكودبيس؛ لا يوجد دليل حالي (كود أو توثيق) يؤكد نية `SIGNATORY` تحديدًا لهذا الدور |

**الكود المقترَح (بافتراض الخيار أ — قابل للتعديل فور اختيارك):**

```python
from app.core.entity_membership_service import EntityMembershipService
from app.core.models import EntityMembershipRole

ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py

# ... داخل __init__:
self.membership = EntityMembershipService(db)

# ... يستبدل سطر 431-432 داخل review_claim:
member = await self.membership.get_member(
    entity_type=ENTITY_TYPE, entity_id=cast(int, policy.issuer_entity_id),
    user_id=reviewer_id,
)
if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
    raise PermissionDeniedError("Not authorized to review this claim")
```

**سؤال إضافي مهم قبل التنفيذ:** هل بوابة `get_current_superuser` على
مستوى الراوتر (`router.py:187` — دور منصة عالمي `SUPER_ADMIN`/
`EXECUTIVE_DIRECTOR`) المفروض **تفضل زي ما هي فوق** فحص الـ
`EntityMembership` الجديد (يعني: لازم تكون superuser عالمي **و**
ممثّل مخوَّل للكيان — تشديد مزدوج)، ولا المفروض **تتشال/تتخفَّف**
(مثلاً تتحول لـ`get_current_active_user` عادي، ويبقى فحص
`EntityMembership` هو الحارس الوحيد والكافي — زي باقي endpoints
`sovereign_entities` اللي بتعتمد على `EntityMembership` بس بلا شرط
`system_role` عالمي إضافي)؟ **الخيار الحالي (المزدوج) هو الأكثر أمانًا
افتراضيًا وأقل تغييرًا (صفر لمس على الراوتر) — مقترَح كنقطة بداية، لكن
يحتاج تأكيدك.**

**تحذير التصميم (نفس نمط التحذير الموثَّق مسبقًا مع #32):** الإصلاح
المقترَح **لا يغيّر** بوابة الراوتر (`get_current_superuser`) — فقط
بيستبدل الفحص الداخلي غير المنطقي بفحص `EntityMembership` حقيقي. **هذا
يعني تشديد الصلاحية فعليًا (defense in depth)، مش تخفيفها** — أي حد
كان بيعدي الفحص القديم (نظريًا فقط، عبر تصادم رقمي) لسه هيحتاج يكون
عضو حقيقي بدور `OWNER`/`EXECUTIVE_DIRECTOR` على الكيان بعد الإصلاح.
**لا يوجد مسار في الإصلاح المقترَح يفتح صلاحية كانت مرفوضة صح من قبل.**

**STATUS (كان): تحقيق حي مكتمل (A/B مؤكَّدان حيًا بشكل قاطع، C موثَّق
كمخاطرة بنيوية غير قابلة للتفعيل حيًا في هذه البيئة). المنطق المقترَح
كان جاهز للمراجعة.**

---

## قرار المستخدم [2026-08-29]

- **الأدوار المسموحة:** الخيار (أ) — `[OWNER, EXECUTIVE_DIRECTOR]`.
- **بوابة `get_current_superuser`:** **تُشال بالكامل**، تُستبدل بـ
  `get_current_active_user` + فحص `EntityMembership` كحارس وحيد وكافي
  — نفس نمط `sovereign_entities` (لا يوجد شرط `system_role` عالمي
  إضافي مكدَّس فوق فحص العضوية في أي endpoint مشابه هناك). **توصية
  الجلسة كانت متفقة مع هذا الاختيار**: الفحص المزدوج كان سيترك الميزة
  معطّلة عمليًا (نادر جدًا يكون المستخدم superuser عالمي *و* عضو كيان
  تأمين معًا)، ولا يوجد سابقة في الكودبيس لتكديس بوابتين من نوعين
  مختلفين (دور منصة + عضوية كيان) فوق بعض لنفس القرار.

## الإصلاح المُطبَّق

**`eppne-backend/app/domains/insurance/router.py:187`:**
```diff
-    current_user: User = Depends(get_current_superuser),
+    current_user: User = Depends(get_current_active_user),
```

**`eppne-backend/app/domains/insurance/service.py`** — استيرادات جديدة +
`ENTITY_TYPE` + `self.membership` في `__init__` + استبدال الفحص (سطر
431-432 الأصلي):
```diff
+from app.core.entity_membership_service import EntityMembershipService
+from app.core.models import EntityMembershipRole
 from app.domains.insurance.models import (...)
 from app.domains.identity.models import User

+ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py

 class InsuranceService:
     def __init__(self, db: AsyncSession):
         self.db = db
         self.repo = InsuranceRepository(db)
         self.event_bus = EventBus(cast(Any, redis_client))
         self.redis = redis_client
+        self.membership = EntityMembershipService(db)
     ...
-        if cast(int, policy.issuer_entity_id) != reviewer_id:
+        member = await self.membership.get_member(
+            entity_type=ENTITY_TYPE, entity_id=cast(int, policy.issuer_entity_id),
+            user_id=reviewer_id,
+        )
+        if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
             raise PermissionDeniedError("Not authorized to review this claim")
```

نفس النمط الحرفي المستخدَم في `sovereign_entities/service.py:394`
(`_is_authorized_representative`) — بلا أي تغيير في منطق التخويل نفسه،
بس منقول لدومين `insurance`.

## التحقق الحي الكامل للإصلاح النهائي (سكريبت `investigate_backlog41_fix_verify.py`)

بُني سيناريو حي كامل: كيان سيادي حقيقي → بوليصة → مستخدمين حقيقيين
بعضوية `EntityMembership` فعلية على نفس الكيان (واحد بدور `OWNER`،
التاني بدور `REPRESENTATIVE`) → استُدعيت `InsuranceService.review_claim()`
**بعد تطبيق الإصلاح** مباشرة (صفر mock، DB حقيقية):

#### سيناريو A (بعد الإصلاح) — عضو حقيقي بدور مسموح (`OWNER`) → **لازم ينجح**

```
entity.id=28  owner_reviewer.id=1046 (role=OWNER)  rep_reviewer.id=1047 (role=REPRESENTATIVE)

=== SCENARIO A: real EntityMembership OWNER -> expect SUCCESS ===
RESULT: SUCCEEDED as expected -> claim.status=ClaimStatus.REJECTED
DB-independent verify: claim 30 status=ClaimStatus.REJECTED (expected REJECTED)
```

**✅ نجح فعليًا.** المطالبة اتحدّثت لحالة `REJECTED` (استُخدم
`approve=False` عمدًا لتفادي مسار الصرف/`finance.transfer` غير المرتبط
بهذا الإصلاح — نفس منهجية العزل المستخدَمة في جلسات سابقة). اتأكد
بـSELECT مستقل من DB (session منفصلة تمامًا) إن الحالة فعلاً `REJECTED`
— التغيير كان حقيقي ومُلتزَم (`commit`)، مش مجرد قيمة في الذاكرة.

#### سيناريو B (بعد الإصلاح) — عضو حقيقي بدور غير مسموح (`REPRESENTATIVE`) → **لازم يترفض**

```
=== SCENARIO B: real EntityMembership REPRESENTATIVE (disallowed role) -> expect PermissionDeniedError ===
RESULT: BLOCKED as expected with PermissionDeniedError: Not authorized to review this claim
```

**✅ اترفض فعليًا بـ`PermissionDeniedError`** (→ 403 عبر الراوتر)، رغم
إن هذا المستخدم **عضو حقيقي فعلي في نفس الكيان** (`EntityMembership`
موجودة بالفعل، مش مستخدم عشوائي زي سيناريو B في التحقيق الأول) — **دليل
قاطع إن الإصلاح واعٍ بالدور (`role-aware`) مش مجرد "أي عضوية كافية"**.
هذا بالتحديد هو الفرق الجوهري بين الإصلاح الصحيح والإصلاح الساذج
اللي حذّر منه التوثيق المسبق (`constructor-mismatch-backlog-classification.md`):
لو الإصلاح كان بس "فيه `EntityMembership` = مسموح" بلا فلترة على
`role`، كان `REPRESENTATIVE` هيعدي غلط. الإصلاح المُطبَّق فعليًا فلتر
صح.

**ملاحظة منهجية (صفر علاقة بكود المشروع):** سكريبت التحقق نفسه صادف
خطأ فني بسيط بعد طباعة نتيجة سيناريو B (حاول يتأكد من حالة claim غير
مُلتزَمة `commit` بعد من session منفصلة → `NoResultFound` متوقَّع
تمامًا، لأن الاستثناء `PermissionDeniedError` بيتصاعد **قبل** أي
`self.db.commit()` داخل `review_claim` — نفس السلوك الصحيح المطلوب:
صفر أثر جانبي على DB لمحاولة مراجعة مرفوضة). النتيجة الجوهرية
(`RESULT: BLOCKED as expected`) كانت مُسجَّلة ومؤكَّدة بالفعل قبل هذا
الخطأ الفني في السكريبت. تم تنظيف كل البيانات المتبقية بعد كده
(`entity 28`, `policy 66`, `subscription 60`, `claim 30`, 4 مستخدمين
throwaway) بسكريبت تنظيف منفصل — DB نظيفة الآن، مؤكَّد.

## الخلاصة النهائية

| المسار | قبل الإصلاح | بعد الإصلاح |
|---|---|---|
| Router gate | `get_current_superuser` (دور منصة عالمي، غير مرتبط بالكيان) | `get_current_active_user` (بلا قيد عالمي — الفحص الحقيقي بقى داخل السيرفس) |
| Service check | `policy.issuer_entity_id != reviewer_id` (مقارنة IDs من مساحتين مختلفتين — دايمًا تقريبًا false) | `EntityMembership.role in [OWNER, EXECUTIVE_DIRECTOR]` على نفس الكيان |
| مراجع شرعي (عضو `OWNER`/`EXECUTIVE_DIRECTOR` حقيقي) | ❌ اتحجب دايمًا (مؤكَّد حيًا، سيناريو A الأصلي) | ✅ بينجح فعليًا (مؤكَّد حيًا، سيناريو A بعد الإصلاح) |
| عضو بدور غير كافٍ (`REPRESENTATIVE`/`SIGNATORY`) | ❌ اتحجب (لكن بلا معنى — نفس رسالة أي حد تاني) | ❌ لسه بيترفض، **لكن دلوقتي لسبب صحيح ومقصود** (مؤكَّد حيًا، سيناريو B بعد الإصلاح) |
| مستخدم عشوائي مالوش أي علاقة | ❌ اتحجب (بالصدفة، مساحتا IDs مختلفتين) | ❌ بيترفض بالتصميم (`member is None`) |

**STATUS: الإصلاح مُطبَّق، مُتحقَّق منه حيًا 100% لكلا المسارين
(نجاح شرعي + رفض غير مخوَّل بدور محدَّد)، DB نظيفة. جاهز للـcommit
بموافقة المستخدم.**
