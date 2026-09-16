# تخطيط: ربط فئة TRAINING بنظام الإنجازات — "إكمال كورس/بوتكامب"

**النوع:** فحص read-only بحت — ممنوع أي تعديل كود، ولم يتم تعديل أي ملف.
**التاريخ:** 2026-09-15

---

## الخلاصة المباشرة

1. **المكان الدقيق اللي بيحدّد "الكورس خلص" مش في `service.py` — هو في `repository.py`.** الفحص السابق (`achievement-trigger-events-inventory-session-log.md`) كان دقيق بخصوص الـservice (مفيش منطق اكتمال هناك)، لكن المنطق الفعلي `if progress >= 100: is_completed = True` موجود سطر واحد بس، جوّه `AcademyRepository.update_progress`، مش `AcademyService.update_progress`.
2. **مفيش حدث لسه يتنشر من هنا إطلاقًا** — نفس التأكيد السابق، مفيش تغيير.
3. **⚠️ اكتشاف جديد حرج للتصميم:** المنطق ده **بلا أي حارس idempotency** — بينفَّذ في كل استدعاء لـ`update_progress` بغض النظر عن القيمة القديمة لـ`is_completed`. يعني نفس الـenrollment ممكن "يكمل" أكتر من مرة (استدعاءات متكررة بـ`progress=100`) — التكرار وارد فعلًا، لكن مش عبر إعادة تسجيل (ده ممنوع معماريًا)، عبر تكرار نداء تحديث التقدّم نفسه.
4. **مفيش تمييز بوتكامب/كورس عادي في نقطة الإكمال نهائيًا** — نفس الفجوة اللي كانت موجودة عند التسجيل قبل الجلسة السابقة؛ لازم fetch إضافي لـ`Course.bootcamp_id` لو الحدث المستقبلي هيحتاج يميّز.
5. **الفكرة "إنجاز لكل كورس مختلف" مش مدعومة بالـschema الحالي أصلًا** — `AchievementDefinition` مالهاش أي عمود بيربطها بكورس/entity محدَّد، و`UserAchievement`'s القيد الفريد (`user_id`, `achievement_definition_id`) بيمنع أكتر من منح واحد لنفس التعريف، بغض النظر عن أي كورس. التصميم المتّسق مع النمط اللي اتبنى بالفعل لـTEAM_BUILDING هو **عدّاد + عتبة** (زي `bootcamp_network_size`)، مش "تعريف منفصل لكل كورس".

---

## 1. المكان الدقيق — بالسطر

### `app/domains/academy/service.py:439-445` (الـservice — تفويض بس)

```python
async def update_progress(self, user_id: int, course_id: int, progress: float):
    enrollment = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
    if not enrollment:
        raise NotFoundError("غير مسجل في هذا الكورس")
    updated = await self.repo.update_progress(user_id, course_id, self.tenant_id, progress)
    await self.repo._invalidate_cache(f"enrollment_{user_id}_{course_id}")
    return updated
```

الـservice بيتحقق بس من وجود التسجيل، وبيفوّض المنطق الفعلي للـrepository. **مفيش أي فحص هنا على القيمة القديمة، ومفيش أي مكان طبيعي لنشر حدث من غير ما نلمس الـrepository أو نجيب بيانات إضافية.**

### `app/domains/academy/repository.py:531-540` (المكان الحقيقي — هنا بالظبط)

```python
async def update_progress(self, user_id: int, course_id: int, tenant_id: int, progress: float) -> Optional[Enrollment]:
    enrollment = await self.get_enrollment(user_id, course_id, tenant_id)
    if enrollment:
        setattr(enrollment, "progress_percentage", progress)
        if progress >= 100:
            setattr(enrollment, "is_completed", True)
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
    return enrollment
```

**ده المكان الدقيق بالحرف** اللي بيحدّد "الكورس خلص": `if progress >= 100: setattr(enrollment, "is_completed", True)`. مفيش أي حالة `COMPLETED` صريحة على مستوى `Enrollment.status` — الحقل ده بيفضل `"ACTIVE"` حتى بعد الإكمال (تأكيد أدناه، قسم 3.1).

### التأكيد الإضافي: `is_completed` بيتقرا مكان تاني؟

```
grep -rn "is_completed" app/domains/academy/
→ models.py:270   Index("ix_enrollment_completed", "is_completed")   [فهرس بس]
→ models.py:290   is_completed = Column(Boolean, default=False)      [تعريف العمود]
→ repository.py:536   setattr(enrollment, "is_completed", True)     [المكان الوحيد اللي بيتكتب فيه]
→ schemas.py:275  is_completed: bool                                 [معروض في EnrollmentResponse بس]
```

**تأكيد قاطع: العمود ده بيتكتب في مكان واحد بس في كل الدومين، وبيتقرا في مكان واحد بس (schema العرض). مفيش أي منطق تاني — لا certificate issuance، لا course analytics، لا أي حاجة — بيعتمد عليه حاليًا.**

### ملحوظة جانبية: `CourseAnalytics.total_completions` كود شبه ميت

فيه `AcademyService.update_course_analytics(increment_completions=True)` وريبو مطابقة، لكن **مفيش أي استدعاء ليها من `update_progress` ولا من أي endpoint في `router.py`** (grep شامل رجّع صفر نتائج). يعني حتى العداد التجميعي على مستوى الكورس نفسه (`CourseAnalytics.total_completions`) مش بيتحدّث فعليًا لحد دلوقتي — مش بس عمود `user_network_stats` هو اللي فاضي، `total_completions` كمان.

---

## 2. فرق "كورس عادي" vs "بوتكامب" — مفيش تمييز جاهز، ومحتاج قرار تصميم

### الوضع الحالي: صفر معلومة بوتكامب في نقطة الإكمال

`AcademyRepository.update_progress` بتجيب `Enrollment` بس (`get_enrollment`) — **مش** `Course`. يعني معرفة "هل الكورس ده جزء من بوتكامب؟" محتاجة fetch إضافي لـ`Course` (عبر `enrollment.course_id`) عشان نقرا `course.bootcamp_id` — بالظبط نفس النمط اللي اتعمل في `enroll_in_course` (اللي أصلًا بيجيب `course` كامل من البداية لأسباب تانية زي الدفع، فالمعلومة كانت "مجانية" هناك؛ هنا محتاجة query إضافي صراحة).

### سابقة مهمة من الجلسة اللي فاتت — الحدث الوحيد الموجود دلوقتي "بوتكامب-فقط"

الحدث الوحيد اللي بيتنشر من `academy` حاليًا (`academy.bootcamp_enrollment.created`) **مش حدث عام "تسجيل في كورس"** — هو حدث **مخصص للبوتكامب بس**، بيتنشر بشرط `course.bootcamp_id is not None` صراحة. **مفيش أي حدث عام "academy.course.enrolled" بيتنشر لكل تسجيل** — القرار المعتمَد فعليًا في الجلسة اللي فاتت كان: حدث واحد ضيّق ومخصص، مش حدث عام بعلامة إضافية.

### خياران للحدث الجديد (إكمال) — للنقاش، بدون قرار هنا

| الخيار | الشكل | الاتساق مع السابقة |
|---|---|---|
| **أ) حدث واحد بس، مخصص بوتكامب** (`academy.bootcamp.completed` أو مشابه) | بيتنشر بس لو `course.bootcamp_id is not None`، بالظبط زي `academy.bootcamp_enrollment.created` | ✅ **متّسق 100% مع القرار الموجود بالفعل** — نفس النمط بالحرف. لكن: لو TRAINING المقصود بيها "أي كورس عادي كمان"، الحدث ده مش هيغطيها إطلاقًا |
| **ب) حدث عام + معلومة `bootcamp_id` في الـpayload** (`academy.course.completed`، `{..., bootcamp_id: Optional[int]}`) | بيتنشر لكل إكمال كورس (عادي أو بوتكامب)، والمستهلك (handler الإنجازات) هو اللي بيفلتر حسب `bootcamp_id is not None` لو محتاج | يغطي TRAINING (أي كورس) وكمان ممكن يُستخدَم لاحقًا لإنجاز بوتكامب-تحديدًا لو احتجنا، لكن **يخالف** النمط الضيّق اللي اتبنى في الإكمال السابق (حدث واحد مخصص، مش حدث عام بعلامة) |

**التوصية للمناقشة (مش قرار نهائي):** يعتمد بالكامل على تعريف TRAINING الفعلي المقصود — لو TRAINING معناها "أكمل أي كورس" (بغض النظر عن بوتكامب)، الخيار (ب) إجباري (الخيار أ مش هيغطي كورسات عادية إطلاقًا). لو TRAINING معناها "أكمل بوتكامب تحديدًا" (أقرب لمعنى تدريب مكثّف)، الخيار (أ) أبسط وأكثر اتساقًا مع القرار الموجود. **ده قرار منتج/معماري محتاج توضيح صريح قبل التنفيذ — خارج نطاق هذا الفحص.**

---

## 3. التكرار — وارد فعلًا، لكن مش من المصدر المتوقَّع

### 3.1 إعادة التسجيل في نفس الكورس؟ **مستحيل معماريًا**

```python
# enroll_in_course
existing = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
if existing:
    raise PermissionDeniedError("أنت مسجل بالفعل في هذا الكورس")
```

`get_enrollment` بيرجّع **أي صف موجود** بغض النظر عن `status` (مفيش فلترة على `CANCELLED`) — وحتى لو الفحص التطبيقي ده اتشال، القيد الفريد على مستوى DB (`ix_enrollment_user_course` — `UniqueConstraint(user_id, course_id)`) هيمنع صف تاني على أي حال. **يعني: نفس المستخدم مايقدرش يسجّل في نفس الكورس مرتين أبدًا — ولو اتلغى تسجيله الأول، مفيش رجوع.** `Enrollment.status` كمان بيفضل `"ACTIVE"` (أو `"PENDING"`/`"CANCELLED"`) — **مفيش قيمة `"COMPLETED"` صريحة إطلاقًا** في أي مكان بالكود (grep شامل، صفر نتائج) — الإكمال متمثّل حصريًا بـ`is_completed=True` جنب `status="ACTIVE"` الأصلي.

### 3.2 التكرار الفعلي الوارد: نداءات متكررة لـ`update_progress` على **نفس** الـenrollment

بما إن `PUT /academy/student/enrollments/{course_id}/progress` مفتوح للمستخدم نفسه بلا أي قيد على عدد المرات، ومفيش فحص `if enrollment.is_completed: return` أو أي حارس مشابه — **نفس المستخدم يقدر ينادي بـ`progress=100` عدة مرات على نفس الـenrollment**، وكل مرة `is_completed = True` بتتكتب تاني (بلا تأثير عملي على القيمة نفسها، لكن لو حدث جديد هيتنشر من هنا مستقبلًا، **هيتنشر في كل مرة**، مش مرة واحدة بس، من غير حارس صريح).

**ده الفرق الجوهري عن `bootcamp_network_size`:** هناك، الـ`INSERT...ON CONFLICT DO UPDATE` نفسه هو اللي بيضمن التراكم الصحيح (كل حدث تسجيل بوتكامب فريد فعلًا — مينفعش تسجّل في نفس الكورس مرتين). هنا، **نفس الحدث المنطقي** ("اكتمل الكورس") ممكن يتكرر عدة مرات لنفس الـ(user, course) — أي تصميم حدث مستقبلي هنا لازم يحتوي حارس صريح (زي: قارن `enrollment.is_completed` القديمة قبل التحديث، انشر الحدث بس لو كانت `False` وبقت `True` — انتقال حقيقي، مش تكرار).

---

## 4. القيد الفريد الموجود — كافي لمنع منح مكرر، لكن بيفرض تصميم معيّن

### السؤال: هل القيد الفريد `unique(user_id, achievement_definition_id)` كافي؟

**الجواب: كافي 100% لمنع منح مكرر لنفس (المستخدم، التعريف) — بالضبط زي ما حصل مع TEAM_BUILDING.** حتى لو حدث الإكمال اتنشر عدة مرات (بسبب فجوة الـidempotency في قسم 3.2)، محاولة المنح التانية والتالتة هتترفض بصمت بنفس آلية `grant_achievement_if_not_exists` (`INSERT...ON CONFLICT DO NOTHING`) الموجودة بالفعل — **صفر تعديل إضافي على القيد أو الآلية مطلوب لمنع هذا النوع من التكرار.**

### السؤال الأعمق: "إنجاز لكل كورس مختلف" ولا "إنجاز واحد عام"؟

هنا القيد الفريد **بيفرض إجابة واحدة بس، مش بيحمي الاتنين:**

- **`UserAchievement` مالهاش عمود `course_id`** — القيد الفريد (`user_id`, `achievement_definition_id`) مش (`user_id`, `achievement_definition_id`, `course_id`). يعني لو عندنا تعريف واحد "TRAINING - أكملت كورس" (`trigger_event_name="academy.course.completed"`)، وأول مرة المستخدم يكمل كورس A بيتمنح الإنجاز، **أي إكمال لاحق لكورس B مختلف تمامًا هيترفض بنفس القيد** (نفس `user_id` + نفس `achievement_definition_id`) — مش لأنه تكرار حقيقي، لأن الـschema مبنية أصلًا على افتراض "تعريف واحد = إنجاز واحد للمستخدم للأبد"، مش "لكل كورس".

- **`AchievementDefinition` نفسها مالهاش أي عمود بيربطها بكورس محدَّد** (لا `course_id`، لا `scope_id` زي `affiliate_scopes`، ولا أي مفهوم مشابه). يعني حتى لو حبينا "إنجاز مختلف لكل كورس"، مفيش طريقة نمثّل بيها "هذا التعريف خاص بكورس X تحديدًا" في الـschema الحالي إطلاقًا — كنا محتاجين تعديل بنيوي (عمود جديد + تخفيف القيد الفريد ليشمل بُعد إضافي)، مش مجرد قرار تطبيقي.

### التوصية للمناقشة (مش قرار نهائي)

**النمط المتّسق مع اللي اتبنى بالفعل لـTEAM_BUILDING هو الأنسب هنا كمان: عدّاد + عتبة، مش تعريف منفصل لكل كورس.** يعني بدل "إنجاز لكل كورس"، المسار الطبيعي هو:
- عمود تراكمي جديد (زي `courses_completed_count`، ممكن يتضاف كعمود في `user_network_stats` أو جدول/عمود مشابه منفصل)، بيتزوّد بـ1 كل ما `is_completed` تنتقل من `False` لـ`True` (مش كل نداء `update_progress`).
- تعريفات TRAINING بعتبات متدرّجة (زي: أول كورس=1، 5 كورسات=5، 10=10) — بالضبط نفس فلسفة `bootcamp_network_size >= 3` الموجودة بالفعل.
- **مفيش حاجة لأي تعديل على `UserAchievement`/القيد الفريد** — الآلية الحالية (`grant_achievement_if_not_exists`) هتشتغل كما هي تمامًا لو العتبة اتحسبت صح.

ده **توصية للمناقشة فقط** — القرار النهائي (هل TRAINING فعلًا معناها "تراكمي" ولا في الحقيقة المقصود بيها حاجة تانية زي شهادة لكل كورس بعينه) محتاج توضيح صريح من المستخدم قبل أي تنفيذ.

---

## ملخص نهائي للأسئلة الثلاثة

| السؤال | الإجابة المختصرة |
|---|---|
| مكان "الكورس خلص" بالضبط؟ | `AcademyRepository.update_progress` (`repository.py:531-540`)، **مش** `AcademyService.update_progress` — سطر واحد: `if progress >= 100: is_completed = True`. بلا حارس idempotency، بلا حالة `status="COMPLETED"` صريحة |
| فرق كورس عادي/بوتكامب في شكل الحدث؟ | صفر تمييز جاهز — محتاج fetch إضافي لـ`Course.bootcamp_id`. السابقة الموجودة (`academy.bootcamp_enrollment.created`) بتستخدم حدث واحد مخصص بوتكامب-بس، مش حدث عام بعلامة — القرار بين النمطين معلَّق على تعريف TRAINING الفعلي |
| هل التكرار وارد، والقيد الفريد كافي؟ | التكرار وارد فعلًا — **مش** عبر إعادة تسجيل (مستحيل معماريًا)، لكن عبر نداءات متكررة لـ`update_progress` على نفس التسجيل (صفر حارس idempotency حاليًا). القيد الفريد كافي 100% لمنع منح مكرر لنفس (مستخدم، تعريف) — لكنه **بيفرض** تصميم "عدّاد+عتبة" (زي TEAM_BUILDING)، مش "إنجاز منفصل لكل كورس" (غير مدعوم بالـschema الحالي إطلاقًا بلا تعديل بنيوي) |

هذا التقرير فحص read-only بالكامل — لم يُنفَّذ أي تعديل كود. القرارات التصميمية المطروحة (شكل الحدث، عدّاد مقابل تعريف لكل كورس) للنقاش فقط.
