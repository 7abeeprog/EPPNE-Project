# جلسة: جرد تقني شامل — قطاع الأكاديمية (Structural Completeness Audit)

**النوع:** تشخيص/جرد فقط — صفر كود، صفر migration، صفر إصلاح.
**النطاق:** `eppne-backend/app/domains/academy/` (router.py 612 سطر، service.py 479 سطر،
repository.py 797 سطر، models.py 510 سطر، schemas.py 397 سطر) + كل نقاط التداخل مع
دومينات أخرى (`employment`, `affiliate`, `identity`, `core/security.py`, `main.py`) +
الفرونت إند المرتبط (`eppne-web/hooks/academy-queries.ts`, `eppne-web/services/academy.service.ts`,
صفحات `app/(dashboard)/academy/*`).

---

## ملخص تنفيذي (اقرأ هذا أولًا)

قطاع الأكاديمية **مبني على معمارية سليمة جزئيًا** (tenant scoping صحيح في القلب: Courses،
Units، Nodes، Enrollments، Tasks، Grading) لكنه يعاني من **نفس النمط المكتشف في كل
الجلسات السابقة اليوم**: طبقات كاملة من الميزات "تبدو مبرمجة" (models + schemas + أحيانًا
service/repo methods كاملة) لكنها **بلا أي مسار حي يكتب أو يقرأ منها فعليًا**، بالإضافة
إلى **كسرين مؤكدين 100% يُنتجان استثناء غير معالَج (500/404) عند الاستخدام الفعلي**، وثغرتي
**عزل مستأجرين (tenant isolation)** حقيقيتين في مسار المواد التعليمية.

### أخطر 3 اكتشافات (كسر مباشر مؤكد):
1. **`employment/service.py:241`** يستدعي `self.academy.get_user_certificates(applicant_id)`
   — **هذه الدالة غير موجودة إطلاقًا** في `AcademyRepository` ولا في أي مكان بالمشروع
   (تأكيد grep شامل). أي طلب توظيف لوظيفة تتطلب `required_certificate_ids` (حقل عادي
   قابل للتعيين من صاحب العمل) سيسقط بـ`AttributeError` → 500 مضمون.
2. **`GET /academy/instructor/stats`** يفشل دائمًا بـ404 لأي مستخدم، دائمًا — بسبب خلط
   `current_user.id` مع `Instructor.id` (PK منفصل تمامًا)، مع كون جدول `academy_instructors`
   **لا يوجد له أي مسار كتابة حي إطلاقًا** في كامل المشروع. الواجهة الأمامية
   (`InstructorDashboard`) تستدعي هذا الـendpoint فعليًا.
3. **`POST /academy/enroll`** (endpoint المبسّط) يفرض `payment_method="FREE"` على أي كورس
   بغض النظر عن سعره الحقيقي، مما ينتج تسجيلًا عالقًا بحالة `PENDING` للأبد لكورس مدفوع —
   وبما أنه لا يوجد أي endpoint لإتمام الدفع أو إلغاء التسجيل، يُحظر المستخدم بشكل دائم من
   إتمام تسجيل حقيقي عبر WALLET لنفس الكورس (فحص "مسجل بالفعل" يمنعه للأبد).

### الصورة الكاملة (خريطة الميزات):
من أصل ~24 ميزة معلَنة (عبر models/schemas)، **7 ميزات كاملة "ميتة" بلا أي مسار حي**
(الشهادات، الشارات، تحليلات الكورس، توصيات AI، أقساط الدفع، حضور الجلسات المباشرة،
سجل إصدار الشهادات blockchain)، **الميزة الأخطر (المدرّبون Instructors) مفصولة بنيويًا
عن نظام الصلاحيات الفعلي** رغم وجود جدول ونموذج كاملين لها، و**الاختبارات (Quizzes)
كتابة فقط بلا أي قراءة أو تسليم أو تصحيح**. بالمقابل: التسجيل الأساسي، الكورسات، الوحدات،
الدروس، المهام والتصحيح، لوحة المتصدرين، ورفع الملفات — **مبرمجة ومتكاملة فعليًا**.

---

## 1) حصر الميزات وخريطة الحالة الكاملة

| # | الميزة | الحالة | الدليل المختصر |
|---|--------|--------|-----------------|
| 1 | Tenants & Org Entities | ✅ مبرمج بالكامل | router→service→repo→commit صريح، بلا مشاكل |
| 2 | **Instructors** | 💀 **ميت بنيويًا** | `create_instructor` (repo.py:136) غير مُستدعى من أي مكان بالمشروع؛ `get_current_instructor_or_admin` يتجاهل الجدول كليًا (يفحص `system_role` فقط) |
| 3 | Bootcamps | ✅ مبرمج بالكامل | — |
| 4 | Tracks | ✅ مبرمج بالكامل | — |
| 5 | Cohorts | ✅ مبرمج بالكامل (استخدام محدود لاحقًا) | يُربط بالتسجيل فقط عبر `cohort_id`، لا منطق سعة/جدولة فعلي يستهلكه |
| 6 | Courses (CRUD) | ✅ مبرمج بالكامل | لا يوجد DELETE endpoint (ليس بالضرورة باج) |
| 7 | Course Units | ✅ مبرمج بالكامل، tenant-scoped صحيح | عبر `get_course(course_id, tenant_id)` |
| 8 | Knowledge Nodes | ⚠️ ناقص جزئيًا | `get_node()` (repo.py:397) بلا فلتر tenant_id — يُستخدم لاحقًا بشكل غير آمن (انظر §3.أ) |
| 9 | Live Sessions | ⚠️ ناقص + ثغرة عزل | Create فقط، لا GET/List، لا حضور فعلي (`LiveAttendance` ميت)، ثغرة كتابة عبر مستأجرين (§3.أ) |
| 10 | Node Materials | ⚠️ ناقص + **ثغرة عزل مستأجرين حرجة** | القراءة (`get_node_materials`) بلا أي فلتر tenant_id أو تحقق تسجيل (§3.ب) |
| 11 | Quizzes | 💀 **كتابة فقط، ميت وظيفيًا** | Create فقط؛ `get_quiz_by_node` معرّفة وغير مُستدعاة أبدًا؛ `QuizSubmit`/`QuizResult` schemas غير مستخدَمة إطلاقًا |
| 12 | Enrollment & Progress | ⚠️ مبعثر + **كسر مؤكد** | Endpoint مزدوج متعارض (§2.ج)؛ تتبع إحالة يضرب نظام عمولة ميت بصمت (§4) |
| 13 | Tasks & Submissions | ✅ مبرمج بالكامل، tenant-scoped صحيح | — |
| 14 | Instructor Grading | ✅ مبرمج بالكامل | — |
| 15 | Instructor Statistics | 💀 **كسر مؤكد 100%، دائمًا 404** | خلط `User.id`/`Instructor.id` (§2.أ) |
| 16 | Leaderboard | ✅ مبرمج بالكامل | — |
| 17 | Financial Summary | ⚠️ ناقص جزئيًا | `total_paid` حقيقي، `total_overdue` = 0 للأبد (PaymentInstallment ميت) |
| 18 | Digital Twin | ⚠️ ناقص | ينشئ سجلًا فارغًا فقط؛ `cognitive_map`/`ai_recommendations` لا تُملأ أبدًا (AI engine غير مُستدعى) |
| 19 | Camera Analysis (AI) | 💀 **ميت من ناحية الـAPI** | service+repo مكتملان، صفر caller في كل المشروع (لا endpoint، لا دومين آخر) |
| 20 | Course Analytics | 💀 **ميت تمامًا رغم اكتمال الكود** | `update_course_analytics` مكتملة بالكامل (زيادة تسجيلات/إتمامات/متوسط درجات/إيراد) لكن صفر استدعاء من أي مكان |
| 21 | File Upload (thumbnail) | ✅ مبرمج بالكامل | نمط BackgroundTasks يعمل |
| 22 | Certificates | 💀 **ميت full-stack** | صفر إنشاء (backend)، قراءة تستدعي دالة غير موجودة (employment)، صفر method بالفرونت إند (خطأ TS مؤكد) |
| 23 | Badges/Gamification | 💀 **ميت full-stack** | نفس نمط الشهادات تمامًا، بما فيه صفحة UI حقيقية (`ai-hub`) تستهلك API غير موجود |
| 24 | Payment Installments | 💀 **ميت تمامًا** | schema+model+قراءة تجميعية موجودون، صفر كتابة من أي مكان |

**الرموز:** ✅ مكتمل فعليًا · ⚠️ ناقص/مبعثر · 💀 ميت (لا مسار حي) أو كسر مؤكد

---

## 2) الكسور المؤكدة (500/404 — أعلى خطورة)

### 2.أ — `GET /academy/instructor/stats` يفشل دائمًا 404

**السلسلة الكاملة:**
- `router.py:566-573`:
  ```python
  @router.get("/instructor/stats")
  async def get_instructor_stats(
      current_user: User = Depends(get_current_instructor_or_admin),
      db: AsyncSession = Depends(get_db)
  ):
      tenant_id = cast(int, current_user.tenant_id)
      service = AcademyService(db, tenant_id)
      return await service.get_instructor_stats(cast(int, current_user.id))
  ```
- `service.py:378-391`:
  ```python
  async def get_instructor_stats(self, instructor_id: int) -> dict:
      instructor = await self.repo.get_instructor(instructor_id, self.tenant_id)
      if not instructor:
          raise NotFoundError("المدرب غير موجود")
      ...
  ```
- `repository.py:143-149`:
  ```python
  async def get_instructor(self, instructor_id: int, tenant_id: int) -> Optional[Instructor]:
      result = await self.db.execute(
          select(Instructor).where(
              and_(Instructor.id == instructor_id, Instructor.tenant_id == tenant_id)
          )
      )
      return result.scalar_one_or_none()
  ```

**المشكلة المزدوجة:**
1. `current_user.id` (هوية المستخدم في `users`) يُمرَّر كـ`instructor_id` ويُقارَن مباشرة
   بـ`Instructor.id` — وهو **PK مستقل تمامًا** (auto-increment على جدول `academy_instructors`)،
   وليس `Instructor.user_id`. لا علاقة رياضية تربط القيمتين.
2. حتى لو أُصلح الخلط أعلاه، **جدول `academy_instructors` لا يمكن أن يحتوي أي صف** —
   انظر §3.أ (لا مسار كتابة حي إطلاقًا).

**النتيجة:** هذا الـendpoint يرمي `NotFoundError` (→ 404) لكل مستخدم، في كل مرة، بلا استثناء.
مؤكد أن الفرونت إند يستدعيه فعليًا: `eppne-web/hooks/academy-queries.ts` عبر
`useInstructorStats()` → `AcademyService.getInstructorStats()` (`academy.service.ts:457-469`
`GET /academy/instructor/stats`) — تُستهلك في `app/(dashboard)/academy/instructor/dashboard/page.tsx:52`.

**⚠️ تحديث [2026-08-20، جلسة `academy-priority-fix`]:** نفس الانفصال البنيوي بين
`Instructor`/`academy_instructors` و`User`/الأدوار (الموصوف أعلاه) اتأكد بزاوية إضافية
أعمق أثناء التحقق الحي من إصلاح باج منفصل تمامًا (`academy-create-course-instructor-id-duplicate-kwarg`،
`academy/service.py:112`، `PROGRESS_LOG.md`): **`academy_courses.instructor_id` نفسها
مربوطة FK على `academy_instructors.id`** — وليس `users.id` مباشرة — رغم أن كل مسار
الإنشاء الفعلي (`router.py`→`service.py:create_course`) يُمرِّر `current_user.id` (من
نطاق `users.id`) كـ`instructor_id` مباشرة، بلا أي بحث أو إنشاء صف مقابل في
`academy_instructors`. بما أن `academy_instructors` **لا يمكن أن يحتوي أي صف حاليًا**
(نفس السبب الموثَّق في §3.أ — `create_instructor` غير مُستدعاة من أي مكان)، فأي محاولة
إنشاء كورس حقيقية (حتى بعد إصلاح باج الـkwarg المكرر) تفشل بـ
`sqlalchemy.exc.IntegrityError: ForeignKeyViolationError` — مؤكَّد حيًا. **هذا يعني أن
حل هذا الانفصال البنيوي (وليس مجرد `instructor/stats`) شرط أساسي لأي إنشاء كورس ناجح
عبر الـAPI من نقطة الصفر.** بانتظار قرار مستند رؤية `EntityMembership` (استبدال
`academy_instructors` بنظام العضوية/الأدوار الموحَّد الجديد بدل إصلاح موضعي) — **صفر
إصلاح كود لهذا البند نفسه**؛ للتحقق الحي من إصلاح باج الـkwarg المكرر فقط، أُدرج صف
throwaway واحد يدويًا في `academy_instructors` (`id` مطابق لـ`user_id`) — بيانات فقط.
تفصيل: `.claude/reports/academy-priority-fix-session-log.md`.

### 2.ب — `employment/service.py:241` يستدعي دالة غير موجودة → 500 مضمون

**السلسلة الكاملة:**
- `employment/service.py:225-255` (`apply_for_job`):
  ```python
  async def apply_for_job(self, applicant_id, tenant_id, job_id, cover_letter=None, resume_url=None):
      job = await self.repo.get_job_listing(job_id, tenant_id)
      ...
      if job.required_certificate_ids:
          certificates = await self.academy.get_user_certificates(applicant_id)   # ← غير موجودة
          cert_course_ids = [c.course_id for c in certificates]
          missing = set(job.required_certificate_ids) - set(cert_course_ids)
          if missing:
              raise PermissionDeniedError(f"أنت لا تمتلك الشهادات المطلوبة: {missing}")
      ...
  ```
- `self.academy` مُهيّأ في `employment/service.py:59` كـ`AcademyRepository(db)` — **الاستهلاك
  الوحيد لـ`AcademyRepository` من خارج دومين الأكاديمية بالمشروع كله** (تأكيد grep شامل).
- **تأكيد grep شامل**: `get_user_certificates` غير معرَّفة في `AcademyRepository` ولا في أي
  ملف آخر بالمشروع. الاستدعاء الوحيد لها هو هذا السطر بالضبط.
- `required_certificate_ids` **حقل عادي قابل للتعيين** عند إنشاء وظيفة —
  `employment/schemas.py:17`: `required_certificate_ids: List[int] = Field(default_factory=list)`،
  ويُستهلك مباشرة عند الإنشاء: `employment/service.py:167`.

**النتيجة:** أي صاحب عمل يضع `required_certificate_ids` غير فارغة عند نشر وظيفة → أي متقدّم
لهذه الوظيفة يُسقِط الطلب بـ`AttributeError: 'AcademyRepository' object has no attribute
'get_user_certificates'` → استثناء غير معالَج (500). **هذا أوضح كسر مباشر في الجلسة** —
بنفس فئة `get_user`/`register_commission` المكتشفة سابقًا.

**ملاحظة إضافية:** حتى لو أُضيفت هذه الدالة مستقبلًا، ستُعيد دائمًا قائمة فارغة — لأن
`SpiritualCertificate` لا تُنشأ أبدًا في أي مسار حي (§3.ج) — أي أن مسار "التوظيف المشروط
بشهادة" معطَّل بنيويًا من طرفيه معًا.

### 2.ج — `POST /academy/enroll` ينتج تسجيلًا عالقًا دائمًا لكورس مدفوع

**السلسلة:**
- `router.py:272-286`:
  ```python
  @router.post("/enroll", response_model=EnrollmentResponse)
  async def enroll_in_course_simple(course_id: int, current_user: User = ..., db=...):
      ...
      return await service.enroll_in_course(
          user_id=cast(int, current_user.id),
          course_id=course_id,
          cohort_id=None,
          payment_method="FREE",     # ← مفروض دائمًا، بغض النظر عن سعر الكورس الحقيقي
          payment_ref=""
      )
  ```
- `service.py:275-277` (داخل `enroll_in_course`):
  ```python
  else:
      payment_status = "COMPLETED" if is_free or amount == 0 else "PENDING"
      enrollment_status = "ACTIVE" if is_free or amount == 0 else "PENDING"
  ```
- `service.py:245-247`:
  ```python
  existing = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
  if existing:
      raise PermissionDeniedError("أنت مسجل بالفعل في هذا الكورس")
  ```

**التسلسل الفعلي:** استدعاء `POST /academy/enroll?course_id=X` لكورس **مدفوع** (`is_free=False`,
`price_mrusdt>0`) ينتج `payment_status="PENDING"`, `status="PENDING"` — تسجيل حقيقي يُكتب فعليًا
في `academy_enrollments` (عبر `commit()` صريح في `service.py:304`)، **وليس مجرد رفض**. من هذه
اللحظة، `get_enrollment` يجد هذا الصف دائمًا → أي محاولة لاحقة لتسجيل حقيقي عبر
`POST /store/courses/{course_id}/enroll` مع `payment_method="WALLET"` تُرفض فورًا بـ
"أنت مسجل بالفعل في هذا الكورس" — رغم عدم دفع أي مبلغ فعليًا.

**لا يوجد أي مسار استرداد:** لا endpoint لتحديث `payment_status`، ولا لإلغاء/حذف تسجيل
`PENDING`. المستخدم محظور بنيويًا وبشكل دائم من إتمام تسجيل حقيقي لهذا الكورس عبر الـAPI.

---

## 3) ثغرتا عزل المستأجرين (Tenant Isolation) في مسار الدروس/المواد

### 3.أ — كتابة عبر مستأجرين: `create_node_material` / `create_quiz` / `create_live_session`

**الجذر المشترك:** الثلاثة تعتمد على `AcademyRepository.get_node(node_id)`:
```python
# repository.py:397-399
async def get_node(self, node_id: int) -> Optional[KnowledgeNode]:
    result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
    return result.scalar_one_or_none()
```
**بلا فلتر `tenant_id` مطلقًا.** يُقارَن هذا بـ`update_node`/`delete_node` في نفس الملف
(repository.py:401-421) اللذين **يتحققان لاحقًا** من ملكية الكورس عبر `get_course(course_id,
tenant_id)` — أي أن نمط التحقق الصحيح موجود ومُطبَّق في مكان، لكنه **غير مُطبَّق في**:
- `service.py:196-202` (`create_live_session`): `node = await self.repo.get_node(node_id)` فقط
- `service.py:207-213` (`create_node_material`): نفس النمط
- `service.py:221-227` (`create_quiz`): نفس النمط

**طبقة الحماية الوحيدة** على هذه الـ3 endpoints هي `get_current_instructor_or_admin`
(`core/security.py:294-305`) التي تفحص **فقط** `current_user.system_role in
["INSTRUCTOR","SUPER_ADMIN","EXECUTIVE_DIRECTOR","ADMIN"]` — **بلا أي علاقة بملكية العقدة
(node) أو المستأجر (tenant) المستهدف.**

**الأثر:** أي مستخدم بدور INSTRUCTOR/ADMIN في المستأجر A يمكنه إرفاق مواد/اختبار/جلسة مباشرة
بأي `node_id` (رقم تسلسلي بسيط) يخص مستأجرًا آخر تمامًا B، بمجرد تخمين/تكرار الرقم.

### 3.ب — قراءة عبر مستأجرين + بلا تحقق تسجيل: `GET /nodes/{node_id}/materials`

**السلسلة الكاملة:**
- `router.py:431-439` → `service.py:215-216` (`get_node_materials`) → `repository.py:434-438`:
  ```python
  async def get_node_materials(self, node_id: int) -> List[NodeMaterial]:
      result = await self.db.execute(
          select(NodeMaterial).where(NodeMaterial.node_id == node_id)
      )
      return list(result.scalars().all())
  ```
**بلا أي فلتر tenant_id، وبلا أي تحقق من أن المستخدم مسجَّل (enrolled) في الكورس أصلًا.**
الحماية الوحيدة على الـendpoint هي `get_current_active_user` (أي مستخدم نشط، أي دور، أي
مستأجر طالما `sector="academy"` في الـJWT — انظر §5). أي مستخدم مصادَق يمكنه قراءة
`file_url` لأي مادة تعليمية عبر كل المستأجرين بمجرد تعداد `node_id`.

### 3.ج — حقل `is_free_preview` موجود ومُخزَّن لكن غير مُنفَّذ إطلاقًا

`KnowledgeNode.is_free_preview` (`models.py:202`, `schemas.py:163`) — تأكيد grep شامل: لا
يظهر في أي شرط/فلتر داخل `service.py` أو `repository.py`. لا يوجد أي مكان في الكود يميّز
بين عقدة "معاينة مجانية" وعقدة مدفوعة. بالإضافة لعدم وجود أي تحقق تسجيل على مسارات القراءة
أصلًا (§3.ب وأعلاه)، فإن التمييز بين محتوى مجاني/مدفوع **غير موجود فعليًا في أي طبقة**.

---

## 4) نقطة التداخل مع نظام العمولات (§5 من التعليمات — `track_referral`)

**السؤال المطلوب:** هل الاستدعاء عند `academy/service.py:295,298` (لنظام العمولة A الميت)
لا يزال موجودًا اليوم؟ ما أثره الفعلي؟

**التأكيد:** نعم، لا يزال موجودًا حرفيًا — `service.py:291-302`:
```python
if affiliate_code:
    try:
        from app.domains.affiliate.service import AffiliateService
        affiliate_service = AffiliateService(self.db, self.tenant_id)
        await affiliate_service.track_referral(
            referrer_code=affiliate_code,
            referred_user_id=user_id,
            entity_type="COURSE",
            entity_id=course_id,
        )
    except Exception as e:
        print(f"⚠️ [Affiliate Tracking] Failed to track referral: {str(e)}")
```
تتبّعت السلسلة إلى `affiliate/service.py:167-208` (`track_referral`) — لا تزال تكتب فعليًا
صفًا في `ReferralTree` عبر `self.repo.create_referral_tree(...)` (السطر الأخير، 202-208).

**الأثر الفعلي اليوم:**
- الكتابة لا تزال تحدث فعليًا (ليست معطَّلة بأي شكل آخر) — تُنشئ صفًا حقيقيًا في جدول
  `ReferralTree` (نظام العمولة A) في كل مرة يُستخدم فيها `affiliate_code` عند التسجيل.
- حسب جلسة `referral-system-multilevel-investigation` السابقة: **لا يوجد أي مسار حي يقرأ
  `ReferralTree` لتوزيع عمولات فعلية** — أي أن هذه الكتابة **بلا أي أثر مالي حقيقي اليوم**،
  فقط تراكم بيانات في جدول تقرَّر حذفه بالكامل مستقبلًا.
- الاستدعاء مُغلَّف بـ`try/except Exception` صامت (`print` فقط، لا إعادة رفع، لا تسجيل
  structured) — فشل `track_referral` (لأي سبب: كود إحالة غير صالح، مستخدم غير موجود، إلخ)
  **لا يمنع اكتمال التسجيل ولا يظهر للمستخدم أو للمراقبة** — نفس نمط الفشل الصامت المكتشف
  سابقًا في `user-repository-get-by-id-audit`.

**فحص سريع لنقطتي §5 الأخريين (كما طُلب، بلا إعادة فحص عميق):**
- `academy/service.py:129,250,342` — استدعاءات `user_repo.get_by_id(user_id, self.tenant_id)`
  — **لا تزال صحيحة**: تطابق التوقيع الفعلي `UserRepository.get_by_id(self, user_id, tenant_id,
  load_wallet=False)` (`identity/repository.py:21`). لا تراجع.
- `academy_tenants` — تأكيد الدور الكامل: هذا الجدول (المُعرَّف داخل دومين الأكاديمية،
  `models.py:12-27`) هو **المرجع الفعلي لـ`tenant_id` FK عبر 27 دومينًا آخر، 176 إعلان FK
  إجمالاً بالمشروع** (تأكيد grep شامل: `agritech`, `commerce`, `finance`-محيطة, `transport`,
  `zamakana`, `sovereign_entities`, `projects`, `health`, `insurance`, `logistics`,
  `manufacturing`, `realestate`, `social`, إلخ). أي قرار مستقبلي بفصل/نقل/إعادة تسمية دومين
  الأكاديمية يجب أن يأخذ هذا بعين الاعتبار — الأكاديمية ليست دومين ميزات هامشي، بل بنية
  تحتية أساسية لتعدد المستأجرين بالمشروع بأكمله.

---

## 5) الكود اليتيم الكامل (Orphaned Code — جداول/نماذج بلا أي مسار كتابة حي)

لكل عنصر: تأكيد **grep شامل على كامل المشروع** لغياب أي استدعاء إنشاء (`Model(...)`) خارج
تعريف الكلاس نفسه.

| النموذج/الجدول | ما هو مكتوب فعليًا | من يقرأه | الحالة |
|---|---|---|---|
| `Instructor` / `academy_instructors` | **لا شيء أبدًا** (`create_instructor` repo.py:136 غير مستدعاة) | `get_instructor` (يفشل دائمًا، §2.أ) | ميت 100%، ومنفصل عن نظام الصلاحيات الفعلي (`system_role`) |
| `SpiritualCertificate` / `spiritual_certificates` | **لا شيء أبدًا** | `count_certificates_for_instructor` (COUNT فقط) | ميت — لا مسار إصدار شهادة في أي مكان رغم `QuizResult.certificate_issued` |
| `CertificateIssuanceLog` / `certificate_issuance_logs` | لا شيء | لا شيء | ميت كليًا — import فقط، صفر استخدام |
| `SovereignBadge` / `sovereign_badges` | لا شيء | لا شيء (backend) | ميت full-stack (انظر §6) |
| `LiveAttendance` / `live_attendance` | لا شيء | لا شيء | ميت — لا تتبع حضور فعلي رغم `LiveSession` قابلة للإنشاء |
| `PaymentInstallment` / `payment_installments` | لا شيء | `get_financial_summary` (SUM فقط، دائمًا 0) | ميت — `PaymentInstallmentCreate` schema موجودة بلا endpoint |
| `CourseAnalytics` / `course_analytics` | لا شيء (رغم `update_course_analytics` **مكتملة الكود بالكامل**، service.py:420-435 + repo.py:656-692) | لا شيء (لا GET endpoint) | ميت تمامًا رغم اكتمال المنطق — صفر caller |
| `analyze_and_recommend_courses` (AI engine) | — | مستورَدة (service.py:18) وغير مُستدعاة أبدًا | dead import — `StudentDigitalTwin.ai_recommendations/cognitive_map` تبقى فارغة للأبد |
| `get_quiz_by_node` (repo.py:447) | — | غير مُستدعاة من أي مكان | orphaned method — لا مسار لقراءة اختبار بعد إنشائه |
| `create_camera_analysis` (service.py:414, repo.py:641) | جاهزة للاستخدام لكن **صفر caller** | — | orphaned — لا endpoint، لا دومين آخر يستدعيها (تحقَّق عبر grep شامل) |

---

## 6) التكرار/التداخل الأشد إثارة للريبة: الشهادات والشارات ميتة عبر الـFull Stack بالكامل

هذا الاكتشاف يتجاوز الباك إند وحده — راجعت ملفات الفرونت إند المعدَّلة فعليًا في هذه الجلسة
(`git status` يُظهرها كملفات معدَّلة: `academy/[id]/page.tsx`, `academy/certificates/[courseId]/page.tsx`,
`academy/instructor/dashboard/page.tsx`, `academy/my-learning/page.tsx`, `CourseActionButton.tsx`).

**اكتشاف حاسم:** ملف موجود بالفعل في المشروع، `eppne-web/link-fix-verification.txt`، يحتوي
سجل أخطاء TypeScript compiler **موثَّق ومؤكَّد مسبقًا** (وليس استنتاجًا مني):
```
hooks/academy-queries.ts(584,35): error TS2339: Property 'getCertificates' does not exist ...
hooks/academy-queries.ts(593,35): error TS2339: Property 'getMyCertificates' does not exist ...
hooks/academy-queries.ts(740,35): error TS2339: Property 'getBadges' does not exist ...
```
تحققت من `eppne-web/services/academy.service.ts` مباشرة: **لا توجد فعليًا** أي من
`getCertificates` / `getMyCertificates` / `getBadges` في تعريف `AcademyService` الحالي —
تطابق تام مع سجل الأخطاء. أي صفحة تستهلك `useMyCertificates` (`certificates/[courseId]/page.tsx`,
`profile/page.tsx:369`) أو `useBadges` (`ai-hub/page.tsx:68-71`) أو `useCertificates`
(`admin/sovereign-ops/page.tsx:84`) **تستدعي دالة غير موجودة في عميل الـAPI نفسه** — هذا
أعمق من مجرد "endpoint مفقود بالباك إند"؛ الواجهة الأمامية نفسها مبنية على افتراض وجود ميزة
لم تُبنَ إطلاقًا في أي من الطرفين.

**الخلاصة المزدوجة:**
- Backend: لا `SpiritualCertificate`/`SovereignBadge` تُكتب أبدًا (§5)، ولا أي router endpoint
  لقراءتها.
- Frontend: لا توجد حتى دوال `AcademyService.getCertificates/getMyCertificates/getBadges`
  لاستدعاء endpoint افتراضي لو وُجد.
- 3 صفحات UI كاملة (`certificates/[courseId]`, `ai-hub` badges section, `admin/sovereign-ops`)
  مبنية بالكامل حول ميزة لا وجود لها في أي طبقة من طبقات النظام.

---

## 7) ملاحظات عامة (أقل خطورة، للسجل)

- `router.py:64` — `POST /tenants` يبني `AcademyService(db, 0)` بـ`tenant_id=0` وهمي؛ غير
  ضار لأن `create_tenant` لا يقرأ `self.tenant_id` إطلاقًا، لكنه code smell (لا سياق مستأجر
  عند إنشاء أول تينانت).
- كل endpoints الأكاديمية محكومة إضافيًا بـ`require_sector("academy")`
  (`main.py:267,305`؛ `core/security.py:206-226`) — مصدرها `sector` claim داخل الـJWT عبر
  ContextVar (`set_sector`/`get_sector`، `security.py:146`) — **ليس** من جدول
  `Instructor` أو أي دور أكاديمي. هذا نمط مشروع بالكامل موثَّق هنا فقط كجزء من توثيق
  `Depends` الفعلية لكل endpoint حسب المطلوب في §2 من التعليمات — لم يُعَد فتح نقاشه.
- `main.py:266-306` — كل tuple في `routers_config` يحمل عنصرًا ثانيًا غير مُستخدَم فعليًا
  (مثال: `"/academy"` في `(academy_router, "/academy", ["Academy"], "academy")`) —
  `include_router` يستخدم `prefix="/api"` الثابت فقط. نمط عام لكل الـ30 دومين، مذكور هنا
  فقط لأنه ظهر أثناء تتبع تسجيل موجّه الأكاديمية — لم يُفحَص بعمق أكبر (خارج نطاق قطاع
  واحد).
- لا يوجد DELETE endpoint لكورس، أو endpoint لإلغاء تسجيل — قد يكون قرارًا تصميميًا
  مقصودًا (لا دليل على أنه باج)، يُذكر فقط لاكتمال الخريطة.

---

## الخلاصة (للمراجعة قبل أي قرار)

القطاع يحتوي **3 كسور مؤكدة 100%** (تُنتج استثناء عند الاستخدام الفعلي)، **ثغرتي عزل
مستأجرين حقيقيتين** في مسار المواد/الاختبارات/الجلسات المباشرة، **7 أنظمة فرعية كاملة ميتة**
(بعضها مكتمل الكود من ناحية service/repo لكن بصفر caller)، وميزة **الشهادات/الشارات ميتة
عبر الـFull Stack** بشكل مؤكد بأدلة من كلا الطرفين. الأجزاء السليمة (الكورسات، الوحدات،
الدروس، التسجيل الأساسي عبر المسار الصحيح، المهام والتصحيح، لوحة المتصدرين) مبنية بمعمارية
tenant-scoping صحيحة ويمكن الوثوق بها كنموذج للإصلاحات القادمة.

**لم يُجرَ أي إصلاح أو تعديل كود في هذه الجلسة، بحسب التعليمات.**
