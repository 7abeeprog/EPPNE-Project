# سجل جلسة: ربط `sovereign_entities` بـ`EntityMembership` (الجلسة 2 من 2)

> جلسة حساسة أمنيًا — تلمس منطقة مرتبطة بثغرة موثَّقة لا تزال مفتوحة.
> مصدر المهمة: `.claude/plans/entity-membership-sovereign-entities-integration-session-instructions.md`

---

## 1. مرحلة القراءة (تمت) — الستة مراجع بالترتيب المطلوب

1. `.claude/plans/multilevel-referral-system-design-vision.md`
2. `.claude/plans/entity-permissions-and-lifecycle-vision.md`
3. `.claude/plans/entity-membership-system-vision.md`
4. `.claude/plans/entity-membership-technical-design.md`
5. `.claude/reports/entity-membership-foundation-session-log.md` — **الأهم**:
   التوقيعات الفعلية الحقيقية لـ`EntityMembershipService`/`EntityMembershipRepository`
   كما بُنيت فعليًا في الجلسة 1 (مو كما وُصفت نظريًا).
6. `.claude/reports/permissions-systems-investigation-session-log.md` §3.3/§3.4 —
   سلوك `sovereign_entities` الحالي + حالة الثغرة الأمنية.

**تأكيد الالتزام بالتحذير الأمني:** لن يُلمَس `SimpleTenant` ولا الأربعة
endpoints بلا مصادقة (`list_entities`, `get_entity`, `list_templates`,
`list_components`) بأي تعديل غير متعلق مباشرة بتحويل EntityRole → EntityMembership.

---

## 2. استكشاف الكود الفعلي (تم) — قبل بناء خريطة التحويل

قُرئت بالكامل: `sovereign_entities/{models,service,repository,router,schemas}.py`،
`app/core/{models,entity_membership_service,entity_membership_repository}.py`.

### 2.1 التحقق من بيانات seed (القسم 2 من التعليمات)

`grep` شامل لـ`EntityRole`/`EntityRepresentative`/`entity_representatives` عبر
المشروع كله. النتيجة ذات الصلة الوحيدة بملفات seed: `scripts/seed_tenant.py:59`
يستخدم `entity_type="HEADQUARTERS"` — **تم التحقق: هذا يخص موديل `OrganizationEntity`
من `app.domains.academy.models` (مستورد صراحة سطر 7)، لا علاقة له إطلاقًا
لا بـ`EntityRole`/`EntityRepresentative` ولا بـ`ReferralTree` القديم** — موديل
ثالث مختلف تمامًا لم يُذكر في أي من المستندات المرجعية. **لا توجد أي بيانات
seed/fixture حية تستخدم `EntityRole`/`EntityRepresentative`.** آمن للحذف من
زاوية بيانات الـseed.

### 2.2 اكتشافات جانبية (توثيق فقط، صفر إصلاح تلقائي)

**(أ) باج ازدواج محتمل موجود بالفعل في `create_entity` — غير مرتبط بالثغرة الأمنية المحذَّر منها:**
`service.py:85-90` (`create_entity`) يضيف الـOWNER مباشرة عبر
`self.repo.add_representative(entity_id=entity.id, user_id=user_id, role=EntityRole.OWNER, can_sign_contracts=True)`.
لكن `router.py:31-35` (نفس الـendpoint) يستدعي **مرة إضافية**
`service.add_representative(entity.id, user_id, {user_id, role=OWNER, can_sign_contracts=True})`
بعد إرجاع `create_entity`. بما أن `_is_authorized_representative` سيجد أن
`user_id` صار OWNER بالفعل (من `create_entity`)، فسيسمح لها بالمرور، ثم
تحاول `repo.add_representative` إدخال صف ثانٍ لنفس `(entity_id, user_id)` —
يصطدم بالقيد الفريد `ix_entity_rep_unique` ويرمي `IntegrityError` غير
مُلتقَط. **لم يُتحقَّق حيًا بعد (يتطلب تشغيل uvicorn فعلي لتأكيد الاستثناء
بدل التحليل الساكن) — لكن التحليل الساكن قاطع.** هذا **خارج نطاق هذه
الجلسة تمامًا** (باج منطقي عادي، لا علاقة بالصلاحيات ولا بالثغرة الأمنية) —
يُوثَّق فقط، **لن يُصلَح هنا**. **ملاحظة حاسمة لضمان "نفس النتيجة قبل/بعد"
المطلوب في التعليمات:** بعد التحويل، القيد الفريد الجديد
(`uq_entity_membership` على `entity_memberships`) سيُنتج **نفس الفشل
بالضبط** (IntegrityError عند محاولة إضافة عضوية مكرَّرة) — لذا هذا الباج
سيبقى **معطوبًا بنفس الطريقة تمامًا** بعد التحويل، لا أسوأ ولا أفضل. هذا
يُعتبَر "نفس النتيجة" ضمن معيار التحقق المطلوب.

**(ب) `signature_pub_key` — لا مكان له في الـschema الجديد:**
`EntityRepresentative.signature_pub_key` (عمود `String(512)`) يُقبَل عبر
`EntityRepresentativeCreate` ويُعاد عبر `EntityRepresentativeResponse`
(schemas.py:72,80) — **لكنه غير مقروء في أي منطق تحقق/عمل بالكودبيس بالكامل**
(تأكيد `grep` شامل: يظهر فقط في schema/model/migration، صفر أي `if`/فحص
يستخدمه). لا `entity_membership_technical_design.md` ولا أي مستند رؤية
أشار لهذا الحقل إطلاقًا — **الجداول الثلاثة الجديدة (`entity_memberships`,
`entity_permission_overrides`, `permission_audit_log`) لا تحتوي عمودًا
يمكن أن يستوعبه.** يحتاج قرارًا صريحًا (راجع القسم 4 أدناه).

**(ج) `EntityRepresentative.is_active` — عمود لا يُطفَأ عمليًا أبدًا (vestigial):**
يُستخدَم كفلتر `WHERE is_active == True` في 3 استعلامات
(`repository.py:136,149,165`)، لكن **لا يوجد أي مكان بالكودبيس يضبطه
`False`** — `remove_representative` يحذف الصف فعليًا (`DELETE`، سطر
172-181)، لا Soft-delete. بما أنه دائمًا `True` فعليًا، حذفه بلا معادل في
`EntityMembership` (التي لا تحمل هذا العمود أصلًا) **لا يغيّر أي سلوك
ملحوظ** — فقط إزالة شرط فلترة كان دائمًا صحيحًا. لا قرار مطلوب هنا، يُذكَر
للتوثيق فقط.

**(د) فجوة سلوكية حقيقية: `remove_member` الجديد لا ينظّف الـoverrides:**
في النظام القديم، `remove_representative` يحذف صف `EntityRepresentative`
بالكامل — **بما فيه `can_sign_contracts` نفسه** (نفس الصف). في النظام
الجديد، `entity_memberships` و`entity_permission_overrides` **جدولان
مستقلان تمامًا بتصميم متعمَّد** (`entity-membership-technical-design.md`
§4) — `EntityMembershipService.remove_member` (الموجود فعليًا،
`entity_membership_service.py:58-63`) **لا يحذف أي صف من
`entity_permission_overrides`**. الأثر العملي: لو مستخدم كان يملك
`can_sign_contracts=True` (override) ثم أُزيل كعضو، ثم أُعيد إضافته لاحقًا
(دور مختلف أو نفس الدور) — **الـoverride القديم يظهر تلقائيًا من جديد
بلا أي منح جديد صريح**، بعكس السلوك الحالي (الإزالة تمحو كل شيء، والإضافة
اللاحقة تبدأ من `can_sign_contracts=False` افتراضيًا دائمًا). **هذا فرق
سلوكي حقيقي غير موثَّق في أي من المستندات الأربعة** — يحتاج قرارًا صريحًا
(راجع القسم 4).

**(هـ) تعارض تسمية `entity_type` (توضيح توثيقي، لا قرار مطلوب):**
`SovereignEntity.entity_type` (عمود `SQLEnum(SovereignEntityType)`: قيم مثل
`STATE_GOVERNMENT`, `ENTERPRISE`, ...) **مختلف تمامًا** عن
`EntityMembership.entity_type` (نص حر، القيمة المقترحة هنا: الحرف
`"SOVEREIGN_ENTITY"` الثابت كمعرِّف نوع الدومين نفسه — لا علاقة بتصنيف
KYB الداخلي). نفس اسم الحقل، معنيان مختلفان تمامًا، في موديلين مختلفين —
يُذكَر فقط لتفادي لبس أثناء التنفيذ الفعلي.

**(و) `tests/test_audit_log_signature_fix.py` سيتعطّل عند حذف `EntityRepresentative`:**
هذا الاختبار الحي الموجود بالفعل (`tests/test_audit_log_signature_fix.py:80,224`)
يستورد `EntityRepresentative` من `sovereign_entities.models` مباشرة
ويستخدمه في تنظيف بيانات الاختبار (`delete(EntityRepresentative)...`) —
سيفشل بـ`ImportError` بمجرد حذف الموديل القديم. **يحتاج تحديثًا كجزء من
هذه الجلسة** (خارج قائمة الاختبارات المذكورة صراحة في التعليمات
`sovereign_entities` tests، لكنه اعتماد حقيقي مكتشَف بالفحص، لا افتراضًا).

---

## 3. الحالة: خريطة التحويل معتمَدة — استُؤنفت الجلسة (استئناف بعد تجدد حد Claude Code، 2026-08-20)

خريطة التحويل الكاملة + نقطتا القرار المفتوحتان (ب، د) حُسمتا صراحةً
عبر `eppne-handoff-summary-2026-08-19-permissions-track.md` (المرفق في
رسالة الاستئناف):
- (ب) `signature_pub_key` → عمود جديد nullable على `EntityMembership` (migration 030).
- (د) فجوة `remove_member` → يحذف `entity_permission_overrides` المرتبطة تلقائيًا.

---

## 4. الخطوة 1 (`app/core`) — منفَّذة ومُتحقَّق منها حيًا

قبل أي كتابة كود: تحقق مباشر أكَّد أن `git status` نظيف على كل مسارات
هذا المسار (`app/core/`, `migrations/`, `sovereign_entities/`, ملفات
الاختبار) عدا `app/core/security.py` (غير مرتبط، من جلسة أخرى)، ورأس
الـmigrations `029` بلا `030` — نقطة بداية نظيفة تطابق التوثيق تمامًا.

**التعديلان على ملفات موجودة (عُرضا حرفيًا للموافقة قبل الكتابة، طبقًا
لقاعدة "توقف قبل أي تعديل على كود موجود" — راجع memory
`feedback_stop_before_consequential_edits`):**

1. `app/core/models.py` — إضافة `signature_pub_key = Column(String(512), nullable=True)` على `EntityMembership`.
2. `app/core/entity_membership_repository.py` — `remove_member` صار يحذف صفوف `EntityPermissionOverride` المرتبطة (نفس `entity_type`/`entity_id`/`user_id`) **قبل** حذف `EntityMembership`، في نفس الـtransaction.

**✅ موافقة صريحة من المستخدم** على التعديلين حرفيًا قبل الكتابة.

**ملفات جديدة (بلا حاجة لموافقة مسبقة على المحتوى الحرفي):**
- `migrations/versions/030_add_signature_pub_key_to_entity_memberships.py` (`down_revision='029_create_entity_membership_foundation'`، نفس نمط 028/029 اليدوي).
- إضافتان لـ`tests/test_entity_membership_foundation.py` (لا ملف منفصل — نفس سويت الجلسة 1، ليبقى تشغيله شاملًا الإصلاحين):
  - `test_signature_pub_key_column_nullable_and_persists`: العمود `NULL` افتراضيًا، يُخزَّن/يُقرأ فعليًا عبر جلسة `AsyncSessionLocal` مستقلة.
  - `test_remove_member_also_deletes_related_overrides`: منح override → `remove_member` → تحقق مستقل بجلسة منفصلة أن الـoverride اختفى (والـaudit log GRANT بقي كما هو، لم يُحذَف) → إعادة إضافة نفس العضو → `check_permission` يرجع `None` (لا يرث `True` القديم) — تغطية حية كاملة للفجوة السلوكية (د).

**تطبيق migration 030:**
```
$ python -m alembic current
029_create_entity_membership_foundation

$ python -m alembic upgrade head
Running upgrade 029_... -> 030_add_signature_pub_key_to_entity_memberships
```
نجح بلا أخطاء. تحقق حي مستقل عبر `psql` (`\d entity_memberships`) أكَّد:
`signature_pub_key character varying(512)`، `Nullable` بلا `not null`،
كل باقي الأعمدة/القيود/الفهارس/الـFKs كما هي بلا أي تأثير جانبي.

**تشغيل سويت الجلسة 1 كاملًا (10 اختبارات — 8 أصلية + 2 جديدان):**
```
================= 10 passed, 11 warnings in 211.88s (0:03:31) =================
```
صفر تراجع. تحقق مستقل عبر `psql` بعد التشغيل أكَّد **صفر بيانات throwaway
متبقية** (`entity_memberships`/`entity_permission_overrides`/
`permission_audit_log` بـ`entity_type='_TEST_ENTITY'`، و`users` بـ
`username LIKE 'em_%'` — كلها `0`).

**✅ موافقة المستخدم على الخطوة 1 (راجع الـdiff المعروض) — "مطابق تمامًا
للمتفق عليه". انتقلنا للبند 3.**

---

## 5. البند 3 — ربط `sovereign_entities` (الـ12 بند) — منفَّذ

### 5.1 فجوتان تنفيذيتان إضافيتان اكتُشفتا أثناء التنفيذ (موافَق عليهما صراحةً)

قبل الكتابة، ظهرت فجوتان ميكانيكيتان لم تحسمهما خريطة §6 حرفيًا (حسمت
*أين* تُخزَّن القيمة، لا *كيف* تُقرأ/تُكتب عبر الـAPI الحالي):

1. **`signature_pub_key` عند الإضافة:** `EntityMembershipService.add_member`
   (من الجلسة 1) لم يكن يقبل `signature_pub_key` رغم وجود العمود. **الحل
   المعتمَد:** باراميتر اختياري جديد `signature_pub_key: Optional[str] = None`
   على `add_member` في كل من `EntityMembershipRepository`/`Service`
   (`app/core/`) — افتراضي `None`، صفر تأثير على اختبارات الجلسة 1 (تأكَّد
   لاحقًا: 10/10 لسه ناجحة).
2. **`can_sign_contracts` في الـresponse:** `EntityMembership` الجديد
   بلا عمود `can_sign_contracts` (بقى في `entity_permission_overrides`
   المنفصل) — إرجاع صف `EntityMembership` الخام مباشرة لـ
   `EntityRepresentativeResponse` كان سيفشل (حقل مفقود). **الحل المعتمَد:**
   `SovereignEntitiesService._to_representative_response()` يبني `dict`
   يدمج بيانات العضوية + نتيجة `check_permission("can_sign_contracts")`
   (`None`→`False` صراحةً).

**اكتشاف إضافي أثناء التنفيذ (ميكانيكي، غير مطروح للنقاش):** الخريطة
سمّت صراحةً `EntityMembershipService.get_member(...)` كبديل مباشر لـ
`_is_representative` — لكن الجلسة 1 كانت بنت `get_members` (جمع) فقط
على الـService (الـsingular موجودة على الـRepository فقط). أُضيف
passthrough `get_member` مطابق تمامًا لاسم الطريقة الموثَّق في الخريطة
نفسها — ليس قرارًا جديدًا، إكمال حرفي لما هو معتمَد بالفعل.

### 5.2 خريطة التحويل — التنفيذ الفعلي (كل بند من الـ12)

| # | البند | التنفيذ الفعلي | تحقق حي HTTP |
|---|---|---|---|
| 1 | `_is_representative` | `SovereignEntitiesService._is_representative` → `self.membership.get_member(...) is not None` | غير مباشر (يُستخدَم داخليًا في `update_entity`/`delete_entity`/`upload_kyb_document`/`get_kyb_documents`/`update_entity_page`/`publish_entity_page`) |
| 2 | `_is_authorized_representative` | + فحص `member.role in allowed_roles` | ✅ رفض حي 403 لعضو REPRESENTATIVE يحاول `remove_representative` |
| 3 | `add_representative`/`remove_representative` | `EntityMembershipService.add_member`/`remove_member` | ✅ `POST`/`DELETE /{entity_id}/representatives` حيّان، مع تحقق `psql` مستقل |
| 4 | `can_sign_contracts` | `check_permission(...)`، `None`→`False` صراحةً (تعليق فى الكود) | ✅ حي في `transfer_from_entity`: عضو بلا override → 403، عضو بـTrue → يتجاوز فحص التفويض (يفشل لاحقًا بـ`InsufficientBalanceError` غير متعلق) |
| 5 | `review_kyb` | **صفر تغيير** — تأكَّد بقراءة الكود | ✅ حي: `PUT /{entity_id}/kyb/status` كسوبر أدمن نجح (200، `kyb_status: VERIFIED`) بلا أي علاقة بـ`EntityMembership` |
| 6 | `signature_pub_key` | عمود nullable + migration 030 + باراميتر `add_member` (راجع §5.1) | ✅ حي: تمرير `signature_pub_key` في `POST .../representatives` رجع بالضبط في الـresponse وفي `psql` |
| 7 | فجوة إزالة/إعادة إضافة | `remove_member` (الخطوة 1) يحذف الـoverride المرتبط | ✅ حي كامل: منح True → إزالة → `psql` صفر overrides → إعادة إضافة بلا `can_sign_contracts` → `GET representatives` يرجع `False` (لا وراثة) |
| 8 | `test_audit_log_signature_fix.py` | يستخدم `EntityMembership`/`EntityPermissionOverride`/`PermissionAuditLog` بدل الموديلات المحذوفة | ✅ 3/3 اختبارات ناجحة (شامل `sovereign_entities.create_entity`) |
| 9 | باج ازدواج `create_entity`/router.py | **خارج النطاق، توثيق فقط — لم يُلمَس** | راجع §5.3 — اكتشاف حي غيَّر التوصيف |
| 10 | `is_active` على `EntityRepresentative` | **خارج النطاق، توثيق فقط** — العمود حُذف تلقائيًا مع حذف الموديل كله (لا معادل له في `EntityMembership` أصلًا)، بلا أي أثر سلوكي إضافي يتجاوز ما وُثِّق مسبقًا | — |
| 11 | حذف `EntityRole`/`EntityRepresentative`/`can_sign_contracts` القديمين | حذف مباشر من `models.py` (بلا migration ترحيل، الجدول `entity_representatives` القديم بقي **orphan** غير مُشار إليه من أي موديل — لم تُكتَب migration DROP TABLE، خارج ما وُثِّق في الخريطة) | تحقق `grep` شامل: صفر مرجع متبقٍّ في الكودبيس بالكامل |
| 12 | الأمن — 4 endpoints بلا `current_user` | **لم تُلمَس إطلاقًا** — تأكيد مباشر: `list_entities`, `get_entity`, `list_templates`, `list_components` لم تتغيّر توقيعاتها في أي diff من هذه الجلسة | — |

### 5.3 اكتشاف حي جديد — باج ثالث غير موثَّق سابقًا (توثيق فقط، **لم يُلمَس**)

أثناء محاولة التحقق الحي عبر `POST /api/sovereign-entities/` (endpoint
الإنشاء الحقيقي)، ظهر **باج مختلف تمامًا** عن باج الازدواج الموثَّق
(البند 9 أعلاه) — يمنع الوصول لباج الازدواج أصلًا لأنه يفشل قبله:

```
TypeError: SovereignEntitiesRepository.create_entity() got multiple
values for keyword argument 'tenant_id'
```

**السبب الجذري:** `router.py::create_entity` يضبط
`entity_data["tenant_id"] = tenant_id` في الـdict المُمرَّر لـ
`service.create_entity(user_id, entity_data)`، والتي بدورها تستدعي
`self.repo.create_entity(tenant_id=self.tenant_id, created_by=user_id, **data)`
— `tenant_id` يُمرَّر مرتين (باراميتر صريح + داخل `**data`) →
`TypeError` فوري، قبل أي لمس لقاعدة البيانات (لا صف يُنشَأ، صفر تنظيف
مطلوب).

**تأكيد: هذا الباج موجود مسبقًا في الكود، لا علاقة له بأي تعديل من
هذه الجلسة ولا الجلسة السابقة** (لم يُلمَس أي من السطرين المسؤولين —
`router.py:29` و`service.py` استدعاء `self.repo.create_entity` — في أي
diff من الجلستين). **خارج نطاق هذه الجلسة تمامًا، توثيق فقط، لم يُصلَح.**
يعني عمليًا: `POST /sovereign-entities/` (endpoint الإنشاء) **معطوب
بالكامل حاليًا في الإنتاج**، بصرف النظر عن باج الازدواج (البند 9) —
لو صُلح هذا الباج الأول مستقبلًا، باج الازدواج (IntegrityError) سيظهر
فورًا بعده كما هو موثَّق.

**الأثر على منهجية التحقق الحي:** استُخدم مسار بديل مطابق تمامًا لنمط
`test_audit_log_signature_fix.py` المُتحقَّق منه فعليًا (استدعاء مباشر
لـ`SovereignEntitiesService.create_entity()` من سكريبت، بدل المرور عبر
الـrouter المعطوب) لتوليد كيان throwaway واحد (`id=17`)، ثم **كل** بقية
العمليات (`add_representative`, `remove_representative`,
`can_sign_contracts` بحالاته الثلاث, `review_kyb`) تحقَّقت عبر HTTP حي
حقيقي (uvicorn فعلي، منفذ 8123) ضد هذا الكيان.

### 5.4 نتائج التشغيل الآلي (بعد كل التعديلات)

```
tests/test_entity_membership_foundation.py: 10 passed (0:03:21)
tests/test_audit_log_signature_fix.py:        3 passed (0:01:25)
tests/ --collect-only:                       98 collected, 0 errors
```

تحقق `psql` مستقل بعد كل خطوة تنظيف: صفر بيانات throwaway متبقية
(كيان `id=17`، مستخدمو الاختبار الثلاثة، كل صفوف
`entity_memberships`/`entity_permission_overrides`/`permission_audit_log`
المرتبطة).

### 5.5 الحالة النهائية — بانتظار موافقة الـcommit

**التنفيذ الفعلي (`git status --short`، مقتصر على مسارات هذه الجلسة):**
```
 M eppne-backend/app/core/entity_membership_repository.py
 M eppne-backend/app/core/entity_membership_service.py
 M eppne-backend/app/core/models.py
 M eppne-backend/app/domains/sovereign_entities/models.py
 M eppne-backend/app/domains/sovereign_entities/repository.py
 M eppne-backend/app/domains/sovereign_entities/router.py
 M eppne-backend/app/domains/sovereign_entities/schemas.py
 M eppne-backend/app/domains/sovereign_entities/service.py
 M eppne-backend/tests/test_audit_log_signature_fix.py
 M eppne-backend/tests/test_entity_membership_foundation.py
?? eppne-backend/migrations/versions/030_add_signature_pub_key_to_entity_memberships.py
```

**الثغرة الأمنية المعروفة (4 endpoints) لم تُلمَس. باج ازدواج
`create_entity` والباج الثالث المكتشَف حديثًا (§5.3) لم يُلمَسا. عمود
`is_active` حُذف تلقائيًا مع حذف الموديل، بلا أثر إضافي.**

**لم يحدث أي `git commit` بعد — بانتظار مراجعة المستخدم للملخص الكامل
(معروض في رسالة الرد المباشرة) قبل التنفيذ.**
