# جلسة: ربط `sovereign_entities` بنظام `EntityMembership` (الجلسة 2 من 2)

**⚠️ جلسة حساسة — تلمس منطقة مرتبطة بثغرة أمنية موثَّقة ولا تزال
مفتوحة. أقصى درجة حذر مطلوبة، أعلى من المعتاد.**

## السياق (خلفية كاملة، لا حاجة للرجوع لأي محادثة سابقة)
مشروع **EPPNE** (Backend FastAPI). الجلسة 1 (`entity-membership-foundation`,
مغلقة) بَنَت الأساس العام لنظام عضوية الكيانات (`EntityMembership`,
`EntityPermissionOverride`, `PermissionAuditLog` في `app/core/`) —
**بمعزل تام عن `sovereign_entities`**، متحقَّق منه حيًا بالكامل
ببيانات وهمية.

هذه الجلسة (الجلسة 2 من استراتيجية Strangler Fig، موثَّقة في
`.claude/plans/entity-membership-technical-design.md` §6) هي خطوة
"الخنق" — **ربط `sovereign_entities` فعليًا بالنظام الجديد، وحذف
النظام القديم (`EntityRole`, `EntityRepresentative`, عمود
`can_sign_contracts` المستقل)**.

**اقرأ بالترتيب قبل أي شيء آخر:**
1. `.claude/plans/multilevel-referral-system-design-vision.md`
2. `.claude/plans/entity-permissions-and-lifecycle-vision.md`
3. `.claude/plans/entity-membership-system-vision.md`
4. `.claude/plans/entity-membership-technical-design.md`
5. `.claude/reports/entity-membership-foundation-session-log.md` —
   **الأهم لهذه الجلسة تحديدًا**: يحتوي التوقيعات الفعلية النهائية
   لـ`EntityMembershipService`/`EntityMembershipRepository` كما بُنيت
   فعليًا (لا كما وُصفت في المستندات النظرية — استخدم الكود الحقيقي
   كمرجع، لا الوصف).
6. `.claude/reports/permissions-systems-investigation-session-log.md`
   §3.3 و§3.4 — **إلزامي**: التوثيق الكامل لسلوك `sovereign_entities`
   الحالي (من المخوَّل لكل عملية) والتحذير الأمني الذي يجب عدم لمسه.

## ⚠️ تحذير أمني حرج — يتكرر من الجلسات السابقة، اقرأه بعناية

`sovereign_entities` لديه **4 endpoints بلا مصادقة صريحة في توقيعها**
(`list_entities`, `get_entity`, `list_templates`, `list_components`)
— محجوبة حاليًا فقط بباج `SimpleTenant` منفصل تمامًا (تحويل كائن
لـ`int` يفشل قبل أي استعلام). **هذه الجلسة لا تلمس هذا الباج ولا هذه
الـendpoints بأي شكل** — التركيز حصرًا على منطق الصلاحيات
(`EntityRole`/`EntityRepresentative`)، وهو أمر منفصل تمامًا كما وثَّق
تقرير التشخيص. **لا تُصلح، لا تُغيّر، لا تُشر إليه إلا للتأكيد أنه لم
يُلمَس.**

## نطاق هذه الجلسة بدقة

### 1. خريطة التحويل الكاملة (يجب توثيقها والموافقة عليها قبل أي كود)
من تقرير التشخيص §3.3، لكل عملية في `sovereign_entities/service.py`
حدد التعادل الدقيق بين المنطق القديم والجديد:

| العملية القديمة | المنطق الجديد المقترَح |
|---|---|
| `_is_representative(entity_id, user_id)` | `EntityMembershipService.get_member(entity_type="SOVEREIGN_ENTITY", entity_id=..., user_id=...) is not None` |
| `_is_authorized_representative(entity_id, user_id, allowed_roles)` | نفس أعلاه + فحص `role in allowed_roles` |
| `add_representative`/`remove_representative` | `EntityMembershipService.add_member`/`remove_member` (بعد تحويل `EntityRole` القديم لـ`EntityMembershipRole` — تأكد من تطابق القيم الأربعة بالاسم) |
| `can_sign_contracts` (عمود بوليان على `EntityRepresentative`) | `EntityMembershipService.check_permission(..., permission="can_sign_contracts")` — **انتبه**: القديم كان `True`/`False` فقط؛ الجديد يرجع `Optional[bool]` (`None` = لا يوجد override). **يجب** أن يُعامَل `None` كـ`False` هنا (نفس السلوك المحافظ الحالي: بلا منح صريح = ممنوع) — وثّق هذا القرار صراحة، لا تفترضه ضمنيًا في الكود بلا تعليق |
| `review_kyb` (`Depends(get_current_superuser)`) | **لا تغيير** — هذا يستخدم `system_role` من `identity` مباشرة، خارج نطاق `EntityRole` بالكامل من الأصل (موثَّق في تقرير التشخيص) |

**اعرض هذا الجدول كاملاً ومكتملاً (كل استدعاء فعلي في الكود، لا فقط
الأنماط) للموافقة قبل أي `Edit`.**

### 2. تحويل بيانات "seed" (لو وُجدت)
`grep` عن أي بيانات seed/fixture تستخدم `EntityRole`/`EntityRepresentative`
حاليًا (`scripts/seed_tenant.py` مذكور في تقرير التشخيص كمستخدم لـ
`entity_type="HEADQUARTERS"` — تأكد إن كان هذا يخص `ReferralTree`
القديم [نظام عمولات محذوف بالفعل] أم `EntityRole` — ميّز بدقة، لا
تخلط). إن وُجدت بيانات فعلية على القاعدة الحية تستخدم النظام القديم
(حتى بيانات تطوير/seed)، وثّق ذلك وتوقف لسؤال المستخدم قبل أي حذف —
لا تفترض أنها throwaway.

### 3. حذف النظام القديم
بعد التحويل الكامل والتحقق منه فقط: حذف `EntityRole` (Enum) و
`EntityRepresentative` (الجدول) من `sovereign_entities/models.py`،
وعمود `can_sign_contracts` (كان على `EntityRepresentative`). Migration
منفصلة لحذف الجدول القديم (`down_revision` = migration 029 من الجلسة
1).

### 4. Router
`sovereign_entities/router.py` — تحقق إن كانت أي endpoint تعتمد على
بنية استجابة تكشف تفاصيل `EntityRole`/`EntityRepresentative` مباشرة
(schemas)، وحدّث الـschemas المرتبطة إن لزم لتعكس `EntityMembership`
الجديد دون كسر أي عقد API موثَّق. **لا تلمس الـ4 endpoints المذكورة
في التحذير الأمني بأي تعديل غير متعلق مباشرة بهذا التحويل.**

## القاعدة الصارمة (أعلى حذرًا من كل الجلسات السابقة)
- **صفر تنفيذ فوري.** اعرض خريطة التحويل الكاملة (القسم 1) ومكان كل
  تعديل مقترَح، سطرًا بسطر إن أمكن، للموافقة الصريحة أولاً.
- **تنفيذ تدريجي بخطوات صغيرة متتابعة**، مثل جلسة توحيد
  `security.py`/`deps.py` بالضبط:
  1. أولاً: أضف طبقة توافق (استدعِ `EntityMembershipService` من داخل
     `_is_representative`/`_is_authorized_representative` بينما تبقي
     `EntityRole`/`EntityRepresentative` القديمين موجودين لكن غير
     مُستخدَمين من هذا المسار) — أو نهج بديل تراه أوضح، اعرضه للموافقة.
  2. تحقق حي: كل عملية من جدول القسم 1 تعطي **نفس النتيجة بالضبط**
     قبل وبعد — لكل الأدوار الأربعة، ولحالة `can_sign_contracts` الثلاث
     (ممنوح صراحة/ممنوع صراحة/بلا override).
  3. فقط بعد التحقق الكامل: احذف النظام القديم والكود الميت.
  4. تحقق حي نهائي شامل بعد الحذف — الـsuite الكامل، وسيناريو HTTP حي
     واحد على الأقل (نفس معيار جلسة الأمان: سيرفر uvicorn حقيقي، طلب
     فعلي) لعملية `sovereign_entities` كاملة (مثلاً: إضافة ممثِّل جديد
     ثم التحقق من ظهوره في `list` عبر API فعلي).
- **بيانات throwaway** لهذا التحقق: استخدم كيان `sovereign_entities`
  حقيقي جديد يُنشأ خصيصًا للتحقق (لا كيان إنتاج موجود)، مع تنظيف كامل.
- **regression test دائم**: تحديث/توسيع اختبارات `sovereign_entities`
  الموجودة (إن وُجدت) لتغطي المسار الجديد بالكامل، بما يشمل تحديدًا
  حالة `can_sign_contracts=None → False`.
- **أي اكتشاف جانبي**: توثيق فوري، صفر إصلاح تلقائي — **وبالذات أي
  شيء يمس الثغرة الأمنية المذكورة، مهما بدا بسيطًا أو "سهل الإصلاح"،
  يُوثَّق فقط ولا يُلمَس مهما كان الإغراء.**
- **Commit معزول واحد** (أو أكثر بتقسيم منطقي تعرضه للموافقة، بنفس
  نمط جلسة الأمان). اعرض `git status` نهائي قبل أي commit فعلي.

## خارج النطاق صراحة
- الثغرة الأمنية (4 endpoints بلا مصادقة، باج `SimpleTenant`) — توثيق
  فقط، صفر لمس، مهما بدا الإصلاح بسيطًا.
- بناء منطق `Platform RBAC` (المكوّن 1 — بوابات الموافقة الإدارية
  `approve_entity_public_listing` إلخ) — نظام منفصل، لم يُبنَ بعد،
  جلسة أخرى.
- ربط أي كيان جديد غير `sovereign_entities` (كورسات، متاجر) بالنظام
  — خارج النطاق، مستقبلي.
- أي تعديل على `identity`/`security.py`/`deps.py` — لا علاقة لهذه
  الجلسة بها.

## عند الإغلاق
وثّق في `PROGRESS_LOG.md`: خريطة التحويل الكاملة المُنفَّذة، نتيجة كل
تحقق حي (بما فيه المقارنة "قبل/بعد" لكل عملية)، تأكيد صريح أن الثغرة
الأمنية لم تُلمَس (حالتها كما كانت)، ونتيجة الـsuite الكامل.

**ابدأ بإنشاء ملف تقرير مخصص** في
`.claude/reports/entity-membership-sovereign-entities-integration-session-log.md`،
ووثّق فيه أول بأول من بداية التخطيط.
