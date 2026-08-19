# جلسة: توحيد dependencies المصادقة/الصلاحيات — `core/security.py` + `api/deps.py`

**النوع:** جلسة أمنية عاجلة. المرحلة الحالية: **قراءة وتخطيط فقط — صفر كود**.

**التاريخ:** 2026-08-19

**المراجع المقروءة بالكامل قبل البدء:**
- `.claude/plans/security-deps-unification-session-instructions.md`
- `.claude/reports/permissions-systems-investigation-session-log.md`
- Skill `eppne-project` (معايير الترميز + حالة البنية الحالية)

---

## سجل التقدم (Live Log)

- [تم] قراءة تعليمات الجلسة + تقرير التشخيص الخلفي كاملَين.
- [تم] قراءة `app/core/security.py` كاملًا (257 سطر) — 16 دالة/كائن.
- [تم] قراءة `app/api/deps.py` كاملًا (234 سطر) — 15 دالة/كائن.
- [تم] قراءة `app/core/errors.py` لتوثيق أكواد الحالة الفعلية وراء
  `AuthenticationError` (401) و`PermissionDeniedError` (403).
- [تم] فحص الأربعة ملفات المزدوجة الاستيراد سطرًا بسطر
  (`communications/router.py`, `identity/router.py`, `privacy/router.py`,
  `tests/test_identity_router_protection.py`).
- [تم] فحص `UserRepository.get_by_id` (`identity/repository.py:21-26`) —
  اكتشاف جانبي مهم (راجع §0 أدناه).
- [تم] فحص مخاطر الاستيراد الدائري لنقل `require_subscription`
  (`SaaSControlService`) إلى `security.py` — **صفر خطر مؤكَّد**.
- [تم] `grep` شامل لاستخدامات `get_current_privacy_officer` /
  `get_privacy_officer` / `get_current_user_optional` / الكائن `security`
  (HTTPBearer) عبر كل المشروع.
- [تم] بناء خطة الدمج الكاملة، دالة بدالة — **معروضة للموافقة، لم يُكتب أي كود بعد.**

---

## §0 — اكتشاف جانبي مهم (يوضّح خطورة فحص `tenant_id` في `security.py`)

`UserRepository.get_by_id(user_id, tenant_id, ...)` (`identity/repository.py:21-26`)
يفلتر الاستعلام نفسه بـ`WHERE User.id == user_id AND User.tenant_id == tenant_id`.
**كلا الملفين** (`security.py` و`deps.py`) يستدعيانها بنفس الطريقة
(`repo.get_by_id(int(user_id), token_tenant_id)`).

**الأثر:** فحص "تطابق tenant الصارم" في `security.py`
(`if token_tenant_id is not None and user.tenant_id != token_tenant_id: raise ...`)
هو عمليًا **كود ميت اليوم** في الحالة الشائعة — لأن أي مستخدم بـ`tenant_id`
مختلف عن التوكن أصلًا **لن يُرجعه الاستعلام نفسه** (يرجع `None` → تُرفع
"User not found" قبل الوصول لفحص المطابقة). الفحص يبقى ذا قيمة فقط
كـ**دفاع ثانٍ صريح** (defense-in-depth، يوثّق النية بوضوح، ويحمي من أي
تعديل مستقبلي على `get_by_id` يزيل الفلترة من الاستعلام). **لا يُغيّر هذا
شيئًا في القرار المعتمد** (الفحص غير قابل للتفاوض ويُنقَل بالحرف) — يُذكَر
هنا فقط للشفافية الكاملة، بلا أي إصلاح أو حذف.

---

## §1 — قائمة كاملة بكل دالة/كائن في الملفين

### `app/core/security.py` (16 اسمًا عامًا)
1. `pwd_context`, `security` (كائنا وحدة، ليسا دوال)
2. `verify_password`
3. `get_password_hash`
4. `create_access_token`
5. `create_refresh_token`
6. `decode_token`
7. `encrypt_ip`
8. `get_current_user` ⚠️ مشترك بالاسم
9. `get_current_active_user` ⚠️ مشترك بالاسم
10. `get_current_superuser` ⚠️ مشترك بالاسم
11. `is_admin_or_above`
12. `require_admin_or_above`
13. `is_privacy_officer` ⚠️ مشترك بالاسم
14. `get_privacy_officer`
15. `require_sector` ⚠️ مشترك بالاسم
16. `require_roles` ⚠️ مشترك بالاسم
17. `get_current_user_optional` ⚠️ مشترك بالاسم (منطق مختلف تمامًا)

### `app/api/deps.py` (15 اسمًا عامًا)
1. `security` (كائن وحدة مكرر)
2. `get_current_user` ⚠️
3. `get_current_active_user` ⚠️
4. `get_current_superuser` ⚠️
5. `require_sector` ⚠️ (معطَّلة فعليًا — باج `sector` غير موجود)
6. `is_privacy_officer` ⚠️
7. `get_current_privacy_officer` (اسم مختلف لنفس وظيفة `get_privacy_officer`)
8. `SimpleTenant`
9. `get_current_tenant`
10. `require_tenant_access`
11. `require_roles` ⚠️
12. `get_current_instructor_or_admin`
13. `require_subscription`
14. `get_current_user_optional` ⚠️ (منطق مختلف تمامًا — Request خام، بلا كوكيز)

**استيراد غير مستخدَم مكتشَف:** `NotFoundError` مستورَد في `deps.py:10` بلا أي
استخدام فعلي في الملف — يختفي تلقائيًا عند إعادة كتابة الملف كـshim، لا
يحتاج قرارًا منفصلًا.

---

## §2 — خطة الدمج الكاملة (دالة بدالة) — **معروضة للموافقة**

### أ) تبقى في `security.py` بلا أي تغيير (منقولة بالحرف كما هي اليوم)
`verify_password`, `get_password_hash`, `create_access_token`,
`create_refresh_token`, `decode_token`, `encrypt_ip`, `is_admin_or_above`,
`require_admin_or_above`, `get_privacy_officer`.

### ب) الدوال الست المشتركة بالاسم — القرار التفصيلي لكل واحدة

| # | الدالة | القرار | التفاصيل |
|---|---|---|---|
| 1 | `get_current_user` | **نسخة `security.py` تفوز بالكامل**، نسخة `deps.py` تُحذَف تمامًا | غير قابل للتفاوض حسب قرار المستخدم: فحص `session_version` + تطابق `tenant_id` الصارم يبقيان بالحرف |
| 2 | `get_current_active_user` | **نسخة `security.py`** (401 عبر `AuthenticationError`) | نسخة `deps.py` (400 `HTTPException`) تُحذَف. **ملاحظة:** كلا الفحصين داخل هذه الدالة عمليًا كود ميت في الحالتين — `get_current_user` (بأي من نسختيه القديمتين) كانت أصلًا ترفض المستخدم غير النشط قبل الوصول لهذه الدالة. يُبقيها الدمج فقط كطبقة دفاع ثانية متسقة مع بقية الملف |
| 3 | `get_current_superuser` | **نسخة `security.py`** (منطق مطابق فعليًا، رسالة إنجليزية "Superuser privileges required") | نسخة `deps.py` (نفس المنطق، رسالة عربية) تُحذَف. كلاهما `PermissionDeniedError` (403) — لا فرق سلوكي حقيقي، فرق نص الرسالة فقط |
| 4 | `require_sector` | **نسخة `security.py`** (آلية `ContextVar` الفعلية) — **هذا هو إصلاح الباج المطلوب صراحة في النطاق** | نسخة `deps.py` (تعتمد على `getattr(user, "sector", None)` غير الموجود + fallback خاطئ إلى `"academy"`) تُحذَف بالكامل |
| 5 | `is_privacy_officer` | **نسخة `security.py`** | فرق ترتيب عناصر القائمة فقط عن نسخة `deps.py` — لا فرق سلوكي |
| 6 | `require_roles` | **نسخة `security.py`** (أبسط) | نسخة `deps.py` فيها فحص إضافي `not role_value or` زائد عن الحاجة (لأن `None not in list` أصلًا `True`) — لا فرق سلوكي فعلي |

### ج) دالة بنفس الاسم، منطق مختلف تمامًا (وليست مجرد فرق أمان بسيط) — **تحتاج قرارك الصريح**

**`get_current_user_optional`** — الحالة الأخطر بعد الست المذكورة أعلاه:

| | `security.py` (اليوم) | `deps.py` (اليوم) |
|---|---|---|
| آلية الاستخراج | `Depends(security)` (HTTPBearer) فقط | `Request` خام، parsing يدوي لـ`Authorization: Bearer` فقط |
| دعم كوكيز `access_token` | ❌ **غير موجود حتى في `security.py` نفسها** | ❌ غير موجود |
| يفحص `session_version`/tenant الصارم؟ | ✅ نعم (يستدعي `get_current_user` داخليًا) | ❌ **لا إطلاقًا** — يستدعي `decode_token` + `UserRepository.get_by_id` مباشرة، بدون المرور عبر `get_current_user` |
| من يستخدمها اليوم | `main.py` (2 endpoints) | `communications/router.py`, `sovereign_entities/router.py`, `invitations/router.py` (بينها endpoints ضيوف حقيقية) |

**المشكلة:** نسخة `deps.py` تعني اليوم أن توكن مُبطَل (بعد "تسجيل خروج من كل
الأجهزة") **لا يزال يُقبَل كـ"مستخدم اختياري مسجَّل"** في الملفات الثلاثة
التي تستخدمها — نفس فئة الثغرة المذكورة في تعليمات الجلسة، لكنها لم
تُذكَر صراحة بالاسم لأنها ليست من "الست دوال" المحددة سلفًا.

**اقتراحي (يحتاج موافقتك الصريحة قبل التنفيذ):** دمجها في نسخة واحدة تُبنى
فوق `get_current_user` الموحَّدة الآمنة، بنفس نمط النسخة الحالية في
`security.py`، **مع توسيعها لدعم `cookie_token` أيضًا** (تمريره لـ
`get_current_user` تمامًا كما تفعل النسخة الإجبارية) — هذا يسد فجوة كانت
كامنة حتى في `security.py` نفسها، وليس فقط في `deps.py`. الفرق الوحيد عن
`get_current_user` الإجبارية: تلف كل استثناء (`HTTPException`,
`AuthenticationError`) وتُرجع `None` بدلًا من الرفع.

**هل توافق على توسيع النطاق ليشمل هذا الإصلاح (دعم الكوكيز + فحص
session_version لكل استخدامات "المستخدم الاختياري")، أم تفضّل الإبقاء على
سلوك `security.py` الحالي لهذه الدالة تحديدًا (بلا دعم كوكيز) وتوثيق فجوة
`deps.py` فيها فقط كاكتشاف جانبي منفصل خارج النطاق؟**

### د) أدوات عملية من `deps.py` تُنقَل بالحرف إلى `security.py` (بلا تغيير منطقي، فقط تُبنى فوق القاعدة الآمنة تلقائيًا لأنها أصلًا تعتمد على `get_current_active_user`)
- `SimpleTenant` (class) — نقل حرفي، **بلا لمس** لباجها المعروف في
  `sovereign_entities` (خارج النطاق صراحة).
- `get_current_tenant`
- `require_tenant_access`
- `get_current_instructor_or_admin`
- `require_subscription` — يستورد `SaaSControlService` من
  `app.domains.saas.service`؛ تحقَّقتُ: هذا الملف **لا يستورد** من
  `core.security` ولا `api.deps` إطلاقًا → **صفر خطر استيراد دائري** من نقلها.

### هـ) اسمان مختلفان لنفس الوظيفة
`get_current_privacy_officer` (`deps.py`) و`get_privacy_officer`
(`security.py`) — نفس المنطق تمامًا. `grep` شامل أكّد: **لا أحد يستورد أيًا
من الاسمين كـdependency فعلي في أي راوتر اليوم** (كلاهما غير مُستخدَم
عمليًا حاليًا). القرار المقترَح: الاسم الكنسي الوحيد في `security.py` يبقى
`get_privacy_officer`؛ يُضاف alias `get_current_privacy_officer =
get_privacy_officer` **داخل الـshim نفسه فقط** (وليس في `security.py`) —
حفاظًا على واجهة عامة نظيفة اسم-واحد-لكل-دالة في الملف الجديد، مع ضمان
عدم كسر أي استيراد مستقبلي محتمل باسم `deps.py` القديم.

---

## §3 — الأربعة ملفات المزدوجة الاستيراد: ماذا يحدث لكل منها بعد الدمج

| الملف | الاستيراد الحالي | الأثر بعد تحويل `deps.py` لـshim |
|---|---|---|
| `communications/router.py` | `get_current_active_user, get_current_tenant, get_current_superuser, get_current_user_optional` من `deps` + `decode_token` من `security` | **صفر تعديل مطلوب** — الأسماء الأربعة من `deps` تصبح نفس الكائنات المُعرَّفة في `security.py` حرفيًا (إعادة تصدير شفافة) — لا تعارض، لا استيراد دائري. الـendpoints تُرقَّى تلقائيًا للفحص الصارم (الأثر المطلوب) |
| `identity/router.py` | `get_current_tenant, SimpleTenant` من `deps` + `get_current_active_user, is_admin_or_above` مباشرة من `security` | **صفر تعديل مطلوب** — نفس المنطق أعلاه، الاسمان من `deps` يصبحان نفس كائنات `security.py` |
| `privacy/router.py` | `get_current_active_user` من `deps` (مستوى الملف) + `is_privacy_officer` من `security` (محليًا داخل دالة، سطر 236) | **صفر تعديل مطلوب** — نفس الكائن فعليًا بعد الدمج |
| `tests/test_identity_router_protection.py` | `strong_get_current_active_user` من `security` + `weak_get_current_active_user` من `deps`، مع تأكيدات صريحة أنهما **مختلفان سلوكيًا** | ⚠️ **يَكسر فعليًا ولا بد من إعادة كتابته** — راجع §4 |

**لا استيراد دائري في أي من الحالات الأربع**: `deps.py` (الشِم) سيستورد فقط
من `core.security`؛ `core.security` لا يستورد من `api.deps` إطلاقًا (تأكيد
من القراءة الكاملة أعلاه) — اتجاه الاعتماد يبقى أحاديًا بعد الدمج.

---

## §4 — لماذا `test_identity_router_protection.py` يَكسر، ومقترَح إعادة الكتابة

بعد تحويل `deps.py` لشِم، `from app.api.deps import get_current_active_user
as weak_get_current_active_user` يعيد **نفس كائن الدالة بالحرف** الموجود في
`core.security` (`is` تكون `True` بينهما). الاختبار الحالي يفترض العكس:

```python
assert weak_get_current_active_user not in calls  # للـpaths المحمية
```

هذا سيفشل بالضرورة على `PROTECTED_PATHS` لأن `calls` تحتوي الكائن المشترك،
و`weak` **هو نفسه** ذلك الكائن الآن. هذا ليس خللًا في الدمج — هو **الدليل
المباشر على نجاح التوحيد**: لم يعد هناك "نسخة ضعيفة" منفصلة كائنيًا لتُميَّز
عنها.

**مقترَح إعادة الكتابة (يحتاج موافقتك):**
- استبدال `assert weak_get_current_active_user not in calls` (على
  `PROTECTED_PATHS`) بتأكيد إيجابي مباشر: `assert weak_get_current_active_user
  is strong_get_current_active_user` (تحقّق حي أن الشِم شفاف فعليًا) — يُنقَل
  كتأكيد عام أول في الملف بدل تكراره داخل الحلقة.
- الإبقاء على `assert strong_get_current_active_user in calls` كما هو
  (يبقى صحيحًا وذا معنى).
- على `PUBLIC_PATHS`: `assert strong_get_current_active_user not in calls`
  يبقى كما هو ومعناه سليم (لا حاجة لتكرار `weak` بعد إثبات أنهما نفس
  الكائن مرة واحدة أعلى الملف).
- **إضافة اختبارات حية جديدة** (مطلوبة إجباريًا حسب التعليمات) تغطي: توكن
  صالح، توكن منتهي، توكن مُبطَل (`session_version` مختلف)، توكن بـ
  `tenant_id` غير مطابق — لكل من `get_current_user` والدوال المبنية فوقها.
  سأقترح تفاصيلها كـخطوة تنفيذ منفصلة بعد موافقتك على خطة الدمج نفسها، لا
  أكتبها الآن.

---

## §5 — تسلسل التنفيذ المقترَح بعد الموافقة (للعِلم فقط، لم يبدأ)

1. بناء `security.py` الموحَّد الجديد (إضافة الدوال المنقولة فقط) — بلا لمس
   `deps.py` أو أي مستدعٍ.
2. تحقق حي: كل دوال `security.py` القديمة سلوكها لم يتغيّر.
3. تحويل `deps.py` لشِم كامل (إعادة تصدير كل الأسماء + alias
   `get_current_privacy_officer`).
4. تحقق حي: `pytest` كامل — 100% بدون فشل جديد (بعد تحديث الاختبار
   المذكور في §4 أولًا).
5. تحقق حي مخصص: سيناريو "تسجيل خروج من كل الأجهزة" عبر endpoint كان
   يستخدم `deps.get_current_user` قبل الدمج (مثلًا من
   `communications`/`sovereign_entities`/`invitations`).
6. تحقق حي مخصص لإصلاح `require_sector`.
7. مراجعة الأربعة ملفات المزدوجة (§3) بعد الدمج فعليًا (لا افتراض).
8. commits مقترَحة (تُعرَض للموافقة عند الوصول لهذه الخطوة فعليًا):
   - Commit 1: بناء `security.py` الموحَّد (بلا أثر على أي مستهلك بعد).
   - Commit 2: تحويل `deps.py` لشِم + تحديث الاختبار + توثيق
     `PROGRESS_LOG.md`.

**لم يُكتب أي سطر كود بعد. في انتظار الموافقة الصريحة على خطة §2 (خصوصًا
القرار المفتوح في §2-ج والمقترَح في §4) قبل أي `Edit`.**

---

## §6 — الموافقة الصريحة المُستلَمة (2026-08-19)

- **`get_current_user_optional`**: تمت الموافقة على دمجها ضمن نطاق الجلسة
  (توسيع النطاق المعتمَد صراحة)، بما يشمل توسيعها لدعم `cookie_token` —
  القرار: "أدمجها ضمن النطاق (موصى به)".
- **خطة الدمج الكاملة (§2) + مقترَح إعادة كتابة
  `test_identity_router_protection.py` (§4)**: موافَق عليهما بالكامل —
  "موافق، ابدأ التنفيذ".
- **البدء بالتنفيذ الفعلي** حسب التسلسل في §5، خطوة بخطوة، مع تحقق حي بعد
  كل خطوة كما تنص التعليمات.

---

## §7 — تنفيذ الخطوة 1: بناء `security.py` الموحَّد (تم)

**التعديلات على `app/core/security.py` فقط — صفر لمس على `deps.py` أو أي
مستدعٍ:**

1. إضافة `Header` لاستيراد `fastapi`.
2. إضافة `from app.domains.saas.service import SaaSControlService` —
   تحقَّقت مسبقًا (§2-د) من عدم وجود استيراد دائري: `saas/service.py` و
   `finance/service.py` لا يستوردان من `core.security` ولا `api.deps`
   إطلاقًا (تأكيد `grep` مباشر قبل الإضافة).
3. **تحديث `get_current_user_optional` في مكانها** (دمج القرار المعتمَد
   في §6): أضيف `cookie_token: Optional[str] = Cookie(None, alias="access_token")`
   للتوقيع، وأصبحت تُمرِّره لـ`get_current_user` — الآن تدعم كوكيز
   بالإضافة لـHeader، وتفحص `session_version`/tenant الصارم بنفس منطق
   النسخة الإجبارية بالكامل (سد الفجوة الموسَّعة المعتمَدة).
4. **إضافة 3 أقسام جديدة منقولة بالحرف من `api/deps.py`** (قسم 10، 11، 12):
   - `SimpleTenant` + `get_current_tenant` + `require_tenant_access`.
   - `get_current_instructor_or_admin`.
   - `require_subscription`.
   كلها تعتمد على `get_current_active_user`/`get_current_user` الموحَّدة
   الآمنة تلقائيًا (لم تُغيَّر أي كلمة في منطقها الداخلي، فقط مكان
   تعريفها).

**تحقق حي 1 — الاستيراد المعزول:**
```
./venv/Scripts/python.exe -c "import app.core.security as s; print('IMPORT_OK')"
```
→ **نجح** (`IMPORT_OK`)، بعد تحذيرات `[DEV]` المعتادة فقط (SECRET_KEY/
FIRST_SUPERUSER_PASSWORD الافتراضيين — غير متعلقة بهذا التغيير). يثبت:
صفر خطأ استيراد دائري من نقل `SaaSControlService`/الدوال الجديدة.

**تحقق حي 2 — Suite الاختبارات الكامل (`pytest`):**
```
71 passed, 4 xfailed, 79 warnings in 221.07s
```
→ **100% بدون أي فشل جديد** — نفس نتيجة ما قبل التعديل (الـ4 `xfailed`
معروفة ومقصودة مسبقًا، غير متعلقة بهذه الجلسة). يثبت: دوال `security.py`
القديمة **لم يتغيّر سلوكها إطلاقًا**، ولا شيء يستورد الدوال الجديدة بعد
(لأن `deps.py` لم يُلمَس بعد) فلا أثر متوقَّع أصلًا على أي مستهلك حاليًا.

**الخلاصة: الخطوة 1 والتحقق الحي المطلوب في الخطوة 2 من §5 مكتملان
بنجاح. متوقف الآن بانتظار تأكيدك للانتقال لتحويل `deps.py` لشِم (الخطوة 3).**

---

## §8 — تنفيذ الخطوة 3: تحويل `deps.py` لشِم + تحديث الاختبار (تم)

### أ) `app/api/deps.py` أصبح شِم كامل (234 سطر → 39 سطر)

يعيد تصدير **كل الأسماء الـ15** التي كانت مُعرَّفة فيه سابقًا من
`app.core.security` مباشرة (بلا أي منطق محلي)، زائد alias واحد:
`get_current_privacy_officer = get_privacy_officer` (كما اتفقنا — داخل
الشِم فقط، وليس في `security.py`).

**تحقق حي — تطابق الكائنات:** استيراد الملفين معًا وفحص `is` لكل اسم
مشترك:
```
get_current_user True
get_current_active_user True
get_current_superuser True
require_sector True
is_privacy_officer True
require_roles True
get_current_user_optional True
SimpleTenant True
get_current_tenant True
require_tenant_access True
get_current_instructor_or_admin True
require_subscription True
get_privacy_officer True
get_current_privacy_officer True
```
كل الأسماء `True` — الشِم شفاف 100%، صفر نسخة منطق منفصلة متبقية.

### ب) إعادة كتابة `tests/test_identity_router_protection.py` (حسب §4 المعتمَد)

- استُبدل `assert weak_get_current_active_user not in calls` (على
  `PROTECTED_PATHS`، كان سيفشل حتمًا) بتأكيد إيجابي واحد أعلى الملف:
  `test_shim_re_export_is_transparent` (`weak is strong`).
- أُبقي `assert strong_get_current_active_user in calls` على
  `PROTECTED_PATHS` و`assert strong_get_current_active_user not in calls`
  على `PUBLIC_PATHS` كما هما (لا يزالان صحيحين ومفيدين).
- **أُضيفت 8 اختبارات حية جديدة** لـ`get_current_user`/
  `get_current_user_optional` الموحَّدتين، بمستخدمين حقيقيين throwaway
  (نفس منهجية `test_user_repository_get_user_audit.py`، تنظيف كامل في
  `finally`):
  1. توكن صالح عبر Header.
  2. توكن صالح عبر Cookie (يثبت الدعم الجديد المُضاف في الخطوة 1).
  3. توكن منتهي الصلاحية → 401.
  4. توكن مُبطَل (`session_version` بعد `increment_session_version`) →
     `AuthenticationError("Session has been revoked")` — **هذا الاختبار
     تحديدًا هو الإثبات الحي المباشر لإغلاق الثغرة الأمنية الأصلية لهذه
     الجلسة كلها.**
  5. توكن بـ`tenant_id` مزوَّر مختلف عن tenant المستخدم الحقيقي → يُرفض
     (`AuthenticationError`) — مع توثيق صريح في الاختبار نفسه أن السبب
     الفعلي "User not found" (فلترة `get_by_id` على مستوى الاستعلام) لا
     "Tenant mismatch" حرفيًا، اتساقًا مع اكتشاف §0.
  6. `get_current_user_optional` بلا توكن → `None` بلا استثناء.
  7. `get_current_user_optional` بتوكن صالح → المستخدم الصحيح.
  8. `get_current_user_optional` بتوكن مُبطَل → `None` (وليس قبولًا
     صامتًا كما كانت نسخة `deps.py` القديمة) — يثبت سد الفجوة الموسَّعة
     المعتمَدة في §6.

### ج) نتيجة `pytest` الكامل (الخطوة 4 من §5)

```
80 passed, 4 xfailed, 93 warnings in 269.89s (0:04:29)
```

**صفر فشل جديد.** الحساب: 71 (قبل هذه الخطوة) + 9 اختبارات صافية جديدة
في `test_identity_router_protection.py` (11 إجمالي في الملف بعد إعادة
الكتابة − 2 كانا موجودين أصلًا) = 80. الـ4 `xfailed` نفسها كما هي، غير
متعلقة بهذه الجلسة. **لم يظهر أي فشل غير متوقَّع في أي من الـ40 ملفًا
الأخرى المستوردة من `deps.py`/`security.py`** — الشِم لم يكسر شيئًا عبر
كل المشروع.

**متوقف الآن بانتظار تأكيدك قبل الانتقال للخطوة 5 (التحقق الحي المخصص
لسيناريو session_version عبر endpoint HTTP فعلي كان يستخدم
`deps.get_current_user` قبل الدمج).**

---

## §9 — تنفيذ الخطوة 5: التحقق الحي عبر HTTP فعلي لسيناريو `session_version`

**المنهجية:** شغَّلت سيرفر `uvicorn` حقيقي (`127.0.0.1:8123`)، وأرسلت طلبات
HTTP حقيقية عبر الشبكة (`curl`) — **لا استدعاء دالة Python مباشر ولا
`TestClient` داخل نفس العملية.**

**اختيار الـendpoint:** `GET /api/communications/notifications/me`
(`communications/router.py:144`) — أحد الـ endpoints التي كانت تعتمد على
`get_current_active_user` المستورَدة من `app.api.deps` (النسخة الأضعف،
بلا فحص `session_version`) قبل الدمج مباشرة (`communications/router.py:13`).

**المستخدم:** حساب throwaway حقيقي (`SUPER_ADMIN` — لتخطي فحص
`require_sector` المسجَّل على مستوى الراوتر لكل الدومينات، وهو منفصل عن
موضوع هذا التحقق، ويُختبَر تحديدًا في §10 التالية). أُنشئ عبر
`UserService.register` الحقيقية ثم رُقّي دوره مباشرة في القاعدة، وسُجِّل
دخول عبر `POST /api/identity/login` الحقيقي (لا توكن مصنوع يدويًا).

**النتيجة (ثلاث طلبات HTTP متتالية بنفس التوكن):**

```
1) قبل الإبطال: GET /api/communications/notifications/me
   → []                                    HTTP_STATUS: 200

2) POST /api/identity/revoke-all (نفس التوكن، لسه صالح وقتها)
   → {"message":"تم إبطال جميع الجلسات (1 جلسة)","revoked_count":1}
                                            HTTP_STATUS: 200

3) بعد الإبطال، بنفس التوكن القديم بالحرف: GET /api/communications/notifications/me
   → {"detail":"Session has been revoked","code":"AuthenticationError"}
                                            HTTP_STATUS: 401
```

**الخلاصة: الثغرة الأمنية الأصلية لهذه الجلسة كلها مغلقة فعليًا ومُثبَتة
عبر HTTP حقيقي.** توكن كان صالحًا شكليًا (لم تنتهِ صلاحيته الزمنية) لكن
جلسته أُبطلت عبر "تسجيل خروج من كل الأجهزة" **يُرفض الآن فورًا** من
endpoint كانت تستخدم `deps.get_current_active_user` قبل تحويل `deps.py`
لشِم — بالضبط السيناريو المحذَّر منه في تعليمات الجلسة الأصلية
(§"الأثر الأمني الحالي" في `security-deps-unification-session-instructions.md`).

**التنظيف:** أوقفت السيرفر (`TaskStop`)، وحذفت المستخدم التجريبي من
القاعدة (`DELETED_ROWS` مؤكَّد).

---

## §10 — تنفيذ الخطوة 6: التحقق الحي عبر HTTP فعلي لإصلاح `require_sector`

**المنهجية:** نفس مبدأ §9 (سيرفر حقيقي + `curl` عبر الشبكة)، لكن بحساب
**غير إداري** (`system_role=USER` افتراضي، لم يُرقَّ) — ضروري هنا تحديدًا
لأن `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` تتخطى فحص `require_sector` بالكامل
(`security.py:216`)، فلا تصلح لاختبار منطق `sector_checker` نفسه.

**قيد معروف ومُوثَّق (غير متعلق بهذه الجلسة):** `identity/service.py` لا
يُصدر `claim` باسم `sector` في أي توكن حقيقي عبر `/login` اليوم (تأكيد
سابق في تقرير التشخيص §1.3). لذلك، ولإثبات آلية `ContextVar` نفسها بدقة
(وليس فجوة إصدار الـclaim، خارج نطاق هذه الجلسة)، تم توليد التوكنين
مباشرة عبر `create_access_token` الحقيقية (بنفس آلية التوقيع
والتشفير الفعلية) بحقل `sector` صريح، ثم استخدامهما في طلبات HTTP حقيقية
- الفرق الوحيد عن `/login` هو مصدر توليد التوكن، لا آلية التحقق منه على
الخادم (وهي نفسها المُختبَرة هنا فعليًا وحيًّا).

**النتيجة (ثلاث طلبات HTTP بتوكنات مختلفة الـsector):**

```
1) توكن sector=communications → GET /api/communications/notifications/me
   → []                                                    HTTP_STATUS: 200

2) نفس توكن sector=communications → GET /api/academy/entities?tenant_id=1
   → {"detail":"عذراً، لا تملك صلاحية الوصول إلى قطاع academy.
      قطاعك الحالي: communications","code":"PermissionDeniedError"}
                                                             HTTP_STATUS: 403

3) توكن sector=academy → GET /api/academy/entities?tenant_id=1
   → []                                                    HTTP_STATUS: 200
```

**الخلاصة: `require_sector` تعمل الآن بدقة عبر `ContextVar` الحقيقي،
تعكس قيمة `sector` الفعلية من كل توكن على حدة.** الطلب #2 يثبت الإصلاح
تحديدًا: رسالة الرفض تعرض **"قطاعك الحالي: communications"** — القيمة
الحقيقية من التوكن نفسه عبر `get_sector()`. **النسخة القديمة المعطَّلة في
`deps.py` (قبل الدمج) كانت تتجاهل قيمة `sector` الحقيقية في التوكن
تمامًا** (تعتمد على `getattr(user, "sector", None)` غير الموجود على
الموديل، فتسقط دائمًا لنفس fallback ثابت: `"academy"` لأي مستخدم غير
إداري، بصرف النظر عن القطاع الحقيقي المصرَّح به في توكنه) — أي أن الطلب
#1 (نجاح `communications` بتوكن `sector=communications` فعلي) كان
مستحيلًا عمليًا تحت المنطق القديم بلا صلاحيات إدارية، بينما الآن يعمل
بصحة كاملة.

**التنظيف:** حذفت المستخدم التجريبي الثاني من القاعدة (نفس عملية `DELETED_ROWS`
أعلاه، دفعة واحدة مع مستخدم §9: `DELETED_ROWS=2`).

**متوقف الآن بانتظار مراجعتك لنتيجتَي الخطوتين 5 و6 قبل الانتقال للخطوة 7
(مراجعة الأربعة ملفات المزدوجة فعليًا بعد الدمج) وأي commit.**

---

## §11 — تنفيذ الخطوة 7: مراجعة الأربعة ملفات المزدوجة فعليًا بعد الدمج (تم)

استوردت الأربعة ملفات معًا في عملية Python واحدة، وفحصت `is` مباشرة لكل
اسم مشترك بينها وبين `core.security` (لا مجرد "يستورد بلا خطأ" — تطابق
هوية الكائن الفعلي):

```
IMPORT_OK: all 4 dual-import files loaded cleanly (zero circular import)

comms.get_current_active_user is sec.get_current_active_user: True
comms.get_current_tenant is sec.get_current_tenant: True
comms.get_current_superuser is sec.get_current_superuser: True
comms.get_current_user_optional is sec.get_current_user_optional: True
comms.decode_token is sec.decode_token: True

identity_r.get_current_tenant is sec.get_current_tenant: True
identity_r.SimpleTenant is sec.SimpleTenant: True
identity_r.get_current_active_user is sec.get_current_active_user: True
identity_r.is_admin_or_above is sec.is_admin_or_above: True

privacy_r.get_current_active_user is sec.get_current_active_user: True
privacy local import line present: True  (is_privacy_officer، سطر 236 داخل الدالة)
```

**النتيجة: صفر تعارض، صفر استيراد دائري، كل الأسماء المشترَكة نفس كائن
الدالة بالحرف في الأربعة ملفات.** الملف الرابع
(`tests/test_identity_router_protection.py`) مؤكَّد سابقًا في §8 (أُعيد
كتابته، ونجح ضمن الـ`pytest` الكامل). **مطابق تمامًا لما خُطِّط في §3 —
لم يحتج أي من الملفات الأربعة أي تعديل فعلي غير إعادة كتابة الاختبار
الرابع.**

---

## §12 — regression test إضافي دائم لسيناريو `require_sector`

الثمانية اختبارات المضافة في §8 غطت `get_current_user`/
`get_current_user_optional` (سيناريو `session_version`) بالكامل — لم
يكن هناك أي pytest دائم لسيناريو `require_sector` (§10) قبل الآن، كان
التحقق يدويًا عبر HTTP فقط. أضفت ملفًا جديدًا مخصَّصًا:
`tests/test_security_deps_unification.py` (4 اختبارات)، بنفس منهجية
استدعاء الدوال الحقيقية بنفس نمط بيانات §10 (لا HTTP، استدعاء مباشر —
`get_current_user` أولًا لضبط الـContextVar كأثر جانبي حقيقي، بالضبط
كترتيب تنفيذ FastAPI الحقيقي، ثم `sector_checker` الناتج من
`require_sector(...)`):

1. `test_require_sector_matching_sector_allows_access` — sector مطابق
   → يمر.
2. `test_require_sector_mismatched_sector_rejected_with_real_sector_in_message`
   — sector مختلف → `PermissionDeniedError`، والرسالة تعكس القيمة
   الحقيقية من التوكن (مطابق لـ§10).
3. `test_require_sector_no_sector_claim_rejected_not_silently_defaulted`
   — بلا `sector` claim إطلاقًا (الحالة الافتراضية الحقيقية اليوم لأي
   تسجيل دخول عادي) → يُرفض بوضوح، لا ينزلق لـfallback صامت.
4. `test_require_sector_super_admin_bypasses_regardless_of_sector` —
   تأكيد أن تخطي `SUPER_ADMIN` (سلوك مقصود محفوظ من الأصل) لا يزال
   يعمل رغم الدمج.

**نتيجة الملف منفردًا:** `4 passed, 9 warnings in 64.72s`.

**نتيجة `pytest` الكامل النهائي (كل الملفات):**
```
84 passed, 4 xfailed, 101 warnings in 382.63s (0:06:22)
```
الحساب: 80 (بعد §8) + 4 (هذا الملف) = 84. **صفر فشل جديد.**

---

## §13 — تحديث `PROGRESS_LOG.md` (تم)

وثَّقت الجلسة بأعلى مستوى تفصيل معتاد في المشروع، في موضعين (مطابق
لقاعدة الملف: البانر العلوي يُستبدَل بأحدث إغلاق، قائمة الجلسات
المُقفلة أسفل الملف append-only):

1. **بانر الحالة العلوي** (`## 📌 بانر الحالة`) — أصبحت هذه الجلسة
   "آخر إغلاق رسمي"، والإغلاق السابق (`user-repository-get-user-audit`،
   Backlog #8) تحوَّل لسطر "إغلاق سابق ذو صلة" (نفس نمط السلسلة
   الموجودة أصلًا في الملف). يوثِّق: الخلفية الكاملة، القرار المعتمَد
   (دمج لا اختيار)، قرار الست دوال، توسيع نطاق `get_current_user_optional`،
   تسلسل التنفيذ بالثمان خطوات، **مقتطفات §9/§10 الحرفية** (نتائج HTTP
   الكاملة لسيناريوَي `session_version`/`require_sector`)، مراجعة
   الملفات الأربعة، الاختبارات الجديدة، نتيجة `pytest` النهائية
   (84 passed)، والتنظيف.
2. **قائمة الجلسات المُقفلة** (أسفل الملف، append-only) — سطر جديد
   `security-deps-unification` بنفس الكثافة/الأسلوب المعتاد لبقية
   الإدخالات، يلخِّص كل ما سبق في فقرة واحدة كثيفة + رابط التقرير الكامل.

**لم يُلمَس أي إدخال قديم في الملف** (لا الجدول ولا القائمة) — الإضافة
فقط، مطابقًا للقاعدة الصارمة في الملف نفسه.

**متوقف الآن بانتظار مراجعتك، قبل عرض `git status` النهائي ومقترَح
تقسيم الـcommits للموافقة.**

---

## §14 — `git status` نهائي + مقترَح تقسيم الـcommits (بانتظار الموافقة)

**تحقق مهم قبل أي اقتراح commit:** المستودع فيه عدد كبير من التعديلات
غير المرتبطة بهذه الجلسة إطلاقًا (من جلسات أخرى سابقة، لسه بلا commit).
تحققت بـ`git diff --stat` مخصَّص لكل ملف لمستهم هذه الجلسة، للتأكد إن
الـdiff الفعلي مطابق **تمامًا** لعملي فقط، بلا أي محتوى مُجمَّع من جلسات
تانية بالصدفة:

```
app/api/deps.py                      | 272 +++------------------  (234→39 سطر، شِم كامل)
app/core/security.py                 |  76 +++++-                (الدوال المنقولة + الإصلاحات)
tests/test_identity_router_protection.py | 219 ++++++++++++++++-  (إعادة الكتابة + 8 اختبارات)
PROGRESS_LOG.md                      |  92 insertions(+), 1 deletion(-)  (بانر + سطر جلسات مقفلة فقط)
```

كل الأرقام مطابقة تمامًا لحجم عملي المتوقَّع — **صفر محتوى مُجمَّع بالصدفة
من جلسات أخرى** في أي من هذه الملفات.

### الملفات المرتبطة بهذه الجلسة فقط (المرشَّحة للـcommit):
- `eppne-backend/app/core/security.py` (معدَّل)
- `eppne-backend/app/api/deps.py` (معدَّل → شِم)
- `eppne-backend/tests/test_identity_router_protection.py` (معدَّل)
- `eppne-backend/tests/test_security_deps_unification.py` (جديد)
- `PROGRESS_LOG.md` (معدَّل)
- `.claude/reports/security-deps-unification-session-log.md` (جديد — هذا الملف)

### ⚠️ ملفان untracked إضافيان لهما علاقة بخلفية هذه الجلسة، لكن لم أُنشئهما أنا في هذه المحادثة:
- `.claude/plans/security-deps-unification-session-instructions.md`
- `.claude/reports/permissions-systems-investigation-session-log.md`

كانا موجودين على القرص **قبل بدء هذه المحادثة** (untracked من جلسة/جلسات
سابقة — تعليمات هذه الجلسة والتشخيص الذي بُنيت عليه). لم ألمسهما، وهما
خارج نطاق commit عملي المقترَح أدناه افتراضيًا — أذكرهما فقط للشفافية
الكاملة. أخبرني لو تريد ضمهما لنفس الـcommit أو تركهما لجلسة/قرار منفصل.

### ملفات أخرى كثيرة معدَّلة/untracked في المستودع — **غير مرتبطة إطلاقًا**
(`app/main.py`, `app/tasks/affiliate.py`, `app/tasks/billing.py`,
`app/domains/health/service.py`, `app/domains/invoicing/router.py`,
`app/domains/projects/service.py`, حذف `app/domains/agritech/router.py`,
`tests/conftest.py`, كل ملفات `eppne-web/*`، وعشرات ملفات `.claude/plans/`
و`.claude/reports/` الأخرى) — **من جلسات عمل مختلفة تمامًا، سابقة لهذه
المحادثة بالكامل. لن ألمسها ولن أُدرجها في أي commit هنا.**

### مقترَح تقسيم الـcommits (كما اتفقنا في §5/§8 — للموافقة قبل أي تنفيذ):

**Commit 1 — بناء القاعدة الآمنة الموحَّدة (بلا أثر على أي مستهلك بعد):**
```
git add eppne-backend/app/core/security.py
```
رسالة مقترَحة:
```
feat(security): unify auth dependencies into core/security.py

Merge api/deps.py's practical tools (SimpleTenant, get_current_tenant,
require_tenant_access, require_subscription,
get_current_instructor_or_admin) on top of security.py's strict
get_current_user (session_version + tenant checks). Extend
get_current_user_optional to support cookie auth and route through the
same secure get_current_user.
```

**Commit 2 — تحويل الشِم + الاختبارات + التوثيق (يُفعِّل الإصلاح فعليًا
عبر كل الـ40 ملفًا المستوردة):**
```
git add eppne-backend/app/api/deps.py \
        eppne-backend/tests/test_identity_router_protection.py \
        eppne-backend/tests/test_security_deps_unification.py \
        PROGRESS_LOG.md \
        .claude/reports/security-deps-unification-session-log.md
```
رسالة مقترَحة:
```
fix(security): convert api/deps.py into a transparent re-export shim

Close the session_version/tenant-mismatch gap that existed whenever an
endpoint imported get_current_user (or *_active_user/*_optional) from
api.deps instead of core.security — deps.py's version never checked
session revocation or strict tenant match, and its require_sector was
fully broken (referenced a non-existent User.sector field).

Verified live over real HTTP: a token surviving "logout from all
devices" is now rejected (401) on an endpoint that used to rely on
deps.py's weak get_current_active_user; require_sector now reflects
the token's real sector via its ContextVar instead of a hardcoded
fallback.

Rewrote test_identity_router_protection.py (its old assertions assumed
deps.py's functions were distinct objects from security.py's — they
are now the same object post-shim) and added
test_security_deps_unification.py for permanent require_sector
regression coverage. Full suite: 84 passed, 4 xfailed.
```

**بانتظار موافقتك الصريحة على هذا التقسيم (أو أي تعديل عليه) قبل أي
`git add`/`git commit` فعلي.**
