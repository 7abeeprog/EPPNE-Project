# شجرة Site الأكاديمية — بناء endpoints الإدارة (implementation)

**التاريخ:** 2026-09-17
**النطاق:** POST+GET لإدارة هرمية Site الأكاديمية (مدرسة ← مرحلة ← فصل)
فوق `app/domains/sites/models.py` (migration 057 — كان الملف موجودًا
بصفر service/repository/endpoint فعلي قبل هذه الجلسة، بحسب docstring
الموديل نفسه). مبني مباشرة على جلسة تصميمية سابقة (اقتراح فقط، صفر كود)
اتّفق عليها المستخدم، ثم أُذِن بالتنفيذ بشرط صريح: تأكيد نمط الصلاحيات
أولًا قبل أي كود، POST+GET فقط بلا DELETE، بلا لمس
`classroom_camera_analyses.site_id`.

---

## 1. تحقق ما قبل التنفيذ (بأمر المستخدم، قبل أي سطر كود)

### 1.1 `SiteType.native_enum=False`
تأكَّد من `app/domains/sites/models.py:17-20` — القيمة تُخزَّن كـVARCHAR
بلا نوع ENUM حقيقي في Postgres وبلا CHECK constraint، عمدًا لإضافة قيم
جديدة بصفر migration. أُضيف `GRADE_LEVEL` و`CLASSROOM` على هذا الأساس.

### 1.2 تصحيح افتراض خاطئ: `ClassroomCameraAnalysis.site_id`
الجلسة التصميمية الأصلية افترضت وجود هذا العمود كمرجع مستقبلي للفصل.
**الفحص المباشر لـ`app/domains/academy/models.py:487-507` أثبت العكس:**
الموديل الفعلي يربط بـ`org_entity_id` (FK على `organization_entities`)
فقط — **صفر عمود `site_id`** في الجدول من الأساس. هذا يعني ربط تحليل
الكاميرا بالفصل الفعلي يحتاج **migration جديدة إضافية** غير موجودة بعد،
مش مجرد استخدام عمود موجود. أُبلغ المستخدم بهذا قبل أي كود، وبناءً عليه
تقرر تأجيل الملف ده بالكامل — لم يُلمَس `academy/models.py` في هذه
الجلسة إطلاقًا.

### 1.3 نمط الصلاحيات — هل `get_current_superuser` نمط أصيل أم مخترَع؟
فُحص `app/domains/academy/router.py` بالكامل (`grep` على كل
`@router.post`/`get_current_superuser`): تأكَّد إن `get_current_superuser`
(شرط `system_role in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]`، معرَّف في
`core/security.py:164-170`) هو **نفس النمط المستخدَم فعليًا** لكل
endpoint إنشاء هرمية تنظيمية موجود بالفعل في academy: `/tenants`
(سطر 62)، `/entities` (سطر 85)، `/tracks` (سطر 132)، `/cohorts`
(سطر 164) — مش خاص بـ`create_cohort` وحدها. كذلك تأكَّد إن
`app.api.deps.get_current_superuser` مجرد **re-export shim** لنفس دالة
`core.security` (مش تطبيق أضعف منفصل، بحسب تحذير `api/deps.py:1-14`
نفسه). القرار: اتّبع نفس الدالة بالحرف، صفر نمط صلاحيات جديد.

---

## 2. الملفات الجديدة — `app/domains/sites/`

طبقة عامة قابلة لإعادة الاستخدام لأي نوع `Site` مستقبلي (مش خاصة
بـacademy فقط) — تماشيًا مع docstring الموديل الأصلي (الهدف كان ربط
iot/manufacturing/agritech/health بنفس الجدول لاحقًا).

- **`schemas.py`**: `AcademyCampusCreate`, `GradeLevelCreate`,
  `ClassroomCreate` (فيها `max_capacity: int = Field(ge=20, le=60)`)،
  `SiteResponse` (عام، `from_attributes`).
- **`repository.py`**: `SiteRepository` — `create_site(**kwargs)`،
  `get_site(site_id, tenant_id)`، `list_sites(tenant_id, site_type,
  parent_site_id)`.
- **`service.py`**: `SiteService` — `create_academy_campus`،
  `create_grade_level` (يتحقق `parent.site_type == ACADEMY_CAMPUS` قبل
  الإنشاء، `NotFoundError`/`ValidationError` عبر `core/errors.py`)،
  `create_classroom` (نفس التحقق مع `GRADE_LEVEL`)، + 3 دوال `list_*`
  مقابلة.

**قرار نطاق واعٍ — `max_capacity` بلا عمود مخصص:** الموديل `Site` ما
فيهوش عمود `max_capacity`. بدل فتح migration جديدة لحقل واحد، اتخزّن
جوّه `Site.geo_metadata` (JSONB موجود بالفعل، `{"max_capacity": N}`)
للفصول فقط. **تنبيه صريح:** اسم العمود "geo_metadata" مش دقيق دلاليًا
لبيانات غير جغرافية زي السعة — قرار عملي لتفادي migration في هذه
الدفعة، مش حل نهائي. لو الفريق حاب عمود `capacity` مخصص لاحقًا، الحل
الأنظف migration منفصلة.

---

## 3. `app/domains/sites/models.py` — تعديل سطري واحد

```python
ACADEMY_CAMPUS = "ACADEMY_CAMPUS"
GRADE_LEVEL = "GRADE_LEVEL"  # ابن مباشر لـACADEMY_CAMPUS
CLASSROOM = "CLASSROOM"      # ابن مباشر لـGRADE_LEVEL
```

صفر migration (راجع §1.1).

---

## 4. `app/domains/academy/router.py` — 6 endpoints جديدة

مُلحَقة في آخر الملف تحت قسم `Site Hierarchy`، فوق prefix `/academy`
الموجود أصلًا (يعني المسار الفعلي `/api/academy/sites/...`):

| Method | Path | صلاحية | ملاحظة |
|---|---|---|---|
| POST | `/academy/sites` | `get_current_superuser` | ينشئ `ACADEMY_CAMPUS`، `parent_site_id=None` |
| GET | `/academy/sites` | `get_current_active_user` | كل مدارس التينانت الحالي |
| POST | `/academy/sites/{school_id}/grades` | `get_current_superuser` | يتحقق أب من نوع `ACADEMY_CAMPUS` |
| GET | `/academy/sites/{school_id}/grades` | `get_current_active_user` | مراحل مدرسة معينة |
| POST | `/academy/sites/{grade_id}/classes` | `get_current_superuser` | يتحقق أب من نوع `GRADE_LEVEL` + `max_capacity` 20-60 |
| GET | `/academy/sites/{grade_id}/classes` | `get_current_active_user` | فصول مرحلة معينة |

نمط GET بلا `superuser` (بس `get_current_active_user`) مطابق لنفس
تناسق `list_cohorts`/`list_tracks` المجاورين — القراءة أوسع من الكتابة
في نفس الدومين أصلًا.

---

## 5. الاختبار الحي — `tests/test_academy_site_hierarchy_endpoints_implementation.py`

4 اختبارات، **4/4 PASSED**:

1. **`test_create_campus_requires_superuser_via_http`** — HTTP فعلي
   (`httpx.ASGITransport` + `dependency_overrides`، نفس نمط
   `test_identity_users_search_implementation.py`): مستخدم عادي → 403،
   `SUPER_ADMIN` → 201 مع `site_type=ACADEMY_CAMPUS`،
   `parent_site_id=None`.
2. **`test_hierarchy_parent_type_validation_and_capacity_range`** —
   منطق الخدمة مباشرة: سلسلة مدرسة→مرحلة→فصل تنجح، `geo_metadata.max_capacity
   == 30` بعد الإنشاء، أب من نوع خطأ لكل من grade/classroom يرفع
   `ValidationError`، أب غير موجود يرفع `NotFoundError`.
3. **`test_classroom_capacity_out_of_range_rejected_via_http`** —
   `max_capacity=5` و`200` كلاهما يرجّع 422 عند مستوى Pydantic (قبل ما
   يوصل للخدمة أصلًا).
4. **`test_list_endpoints_scoped_by_tenant_and_parent`** — عزل تينانت
   (مدرسة تينانت تاني ميظهرش في القائمة) + `parent_site_id` صحيح لكل من
   grades/classrooms.

### باج حقيقي وُجد وأُصلح — في نمط الاختبار، مش في الكود المُنتَج

أول تشغيلة كاملة للملف كشفت فشل واحد (`test_list_endpoints_scoped_by_tenant_and_parent`)
يظهر **بس** لما الاختبارات تتشغّل بالتتابع، مش منفردة:

```
AttributeError: 'NoneType' object has no attribute 'send'
RuntimeError: Event loop is closed
```

**السبب الجذري:** `test_classroom_capacity_out_of_range_rejected_via_http`
كانت بتفتح `AsyncSessionLocal()` يدويًا بلا طلب fixture الـ`db` من
`tests/conftest.py`. الـfixture ده مسؤول عن `await engine.dispose()`
بعد كل اختبار — موثَّق صراحة في `conftest.py:19-25` كضرورة على Windows
(pytest-asyncio بيفتح event loop جديد لكل test function، لكن engine
الداتابيز العالمي بيحتفظ باتصالات من الـloop القديم). لما الاختبار
تخطّى الـfixture، سابت اتصالات متسربة من event loop قديم، والاختبار
اللي بعده كراش وهو بيحاول يستخدمها.

**الإصلاح:** الاختبار بقى ياخد `db` كـfixture بدل `AsyncSessionLocal()`
يدوي — تعليق مباشر في الكود يوثّق السبب لمنع تكرار نفس الخطأ مستقبلًا.
بعد الإصلاح: 4/4 PASSED منفردة ومع بعض.

---

## 6. Regression — الاختبار الكامل (مرتين، قبل وبعد إصلاح الباج)

استُثني `tests/test_affiliate_service_missing_methods.py` (فشل
`ImportError` على `ActionCommission` معروف مسبقًا من جلسات سابقة، غير
متعلق بهذه الجلسة).

```
13 failed, 229 passed, 2 xfailed, 289 warnings in 724.75s
```

**مطابقة حرفية 100%** لنفس أسماء الـ13 فشل المعروفة مسبقًا (كلها في
`test_realestate_insurance_savepoint.py`،
`test_user_repository_get_by_id_audit.py`،
`test_user_repository_get_user_audit.py`) — صفر تغيير في القائمة، صفر
regression. الـ4 اختبارات الجديدة ضمن الـ229 الناجحة.

---

## 7. `PROGRESS_LOG.md`

أُضيف سطر جديد في آخر الملف (سجل تراكمي، صفر تعديل على أي إدخال قديم)
تحت عنوان `## جلسة academy-site-hierarchy-endpoints-implementation
(2026-09-17)` — يغطي كل نقاط هذا التقرير باختصار.

---

## الملفات المُعدَّلة/المُنشأة في هذه الجلسة

**تعديل:**
- `eppne-backend/app/domains/sites/models.py` (سطرين إضافة enum)
- `eppne-backend/app/domains/academy/router.py` (استيراد + 6 endpoints جديدة)
- `PROGRESS_LOG.md` (سطر جديد في الآخر)

**إنشاء:**
- `eppne-backend/app/domains/sites/schemas.py`
- `eppne-backend/app/domains/sites/repository.py`
- `eppne-backend/app/domains/sites/service.py`
- `eppne-backend/tests/test_academy_site_hierarchy_endpoints_implementation.py`
- هذا التقرير

**لم يُلمَس عمدًا (بقرار نطاق صريح من المستخدم):**
- `academy/models.py` / `classroom_camera_analyses` (صفر عمود `site_id`،
  محتاج migration منفصلة مستقبلًا)
- DELETE endpoints لأي مستوى من الشجرة
- زرع بيانات مدرسة pilot فعلية أو ربط كاميرا حقيقي

**الحالة النهائية:** 6 endpoints مبنية بالكامل ومتحقَّق منها حيًا (4/4)،
regression نظيف (13 فشل موروث بالحرف، صفر جديد)، تم توثيق باج اختبار حي
تم اكتشافه وإصلاحه (تسرّب اتصال DB عبر event loop). **لم يُعمَل commit
بعد** — بانتظار طلب المستخدم صراحةً، وبانتظار موافقة منفصلة قبل أي خطوة
تالية (زرع بيانات pilot، أو ربط الكاميرا).
