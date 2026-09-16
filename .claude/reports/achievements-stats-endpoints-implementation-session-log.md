# جلسة تنفيذ: endpoints إحصائية لـ achievements/router.py

**التاريخ:** 2026-09-15
**النطاق:** إضافة endpoints إحصائية جديدة فقط لدومين `achievements`.
**صفر تعديل على أي جدول، migration، أو منطق منح موجود.**
مرجع التخطيط: `.claude/reports/achievements-admin-dashboard-planning-session-log.md`.

---

## 1. ما اتعمل

### `GET /achievements/stats/by-category` (SUPER_ADMIN)
يرجّع `[{category, count}]` — عدد صفوف `UserAchievement` الفعلي لكل
فئة (`GROUP BY` على `UserAchievement JOIN AchievementDefinition`).

### `GET /achievements/stats/top-users?limit=` (SUPER_ADMIN، default 10، max 50)
يرجّع `[{user_id, user_name, achievement_count}]` مرتبة تنازليًا.

### الملفات المعدَّلة (إضافات فقط)

| ملف | التغيير |
|---|---|
| `app/domains/achievements/schemas.py` | `AchievementCategoryStatItem`, `AchievementTopUserItem` |
| `app/domains/achievements/repository.py` | `count_user_achievements_by_category`, `get_top_users_by_achievement_count` |
| `app/domains/achievements/service.py` | `get_stats_by_category`, `get_top_users` (import إضافي فقط) |
| `app/domains/achievements/router.py` | `GET /stats/by-category`, `GET /stats/top-users` (+ `Query` import) |

**صفر تعديل على `app/main.py`** — الراوتر مسجَّل بالفعل من جلسة
`achievements-foundation-implementation`. **صفر migration جديدة.**

### قرار JOIN (مأخوذ حرفيًا من طلب المستخدم)

`count_user_achievements_by_category` بتعمل **INNER JOIN** بدءًا من
`UserAchievement` (`select(...).select_from(UserAchievement).join(AchievementDefinition, ...)`)
— فئة بدون أي منح فعلي **مش هتظهر إطلاقًا** في النتيجة (مش `count=0`).
ده القرار اللي كان معلَّق في تقرير التخطيط، وحُسم صراحة في طلب هذه
الجلسة ("GROUP BY category على UserAchievement join AchievementDefinition").

### `top-users` — تحسين عن نمط `academy.get_academy_leaderboard`

النمط المرجعي في `academy/repository.py` (`get_academy_leaderboard`)
بيرجّع `user_id` خام بلا اسم. هنا عملت JOIN مباشر مع `User`
(`User.id`, `User.username`) عشان الحقل `user_name` المطلوب صراحة في
الـresponse يطلع جاهز من نفس الاستعلام، بلا N+1 lookup في الفرونت إند.

---

## 2. اكتشاف مهم أثناء التحقق الحي (قبل كتابة أي كود)

الطلب افترض وجود "بيانات حقيقية متراكمة من جلسات اليوم (الفئات
التلاتة)". فحصت DB الحقيقية مباشرة (`AsyncSessionLocal`) قبل أي تعديل:

```
AchievementDefinition rows: 1
  id=2 tenant=1 category=AchievementCategory.TRAINING name='REGTEST-ACHIEVEMENT-DUP-18d7e4ed88'
UserAchievement rows: 1
  id=2 tenant=1 user_id=4880 def_id=2
```

**لا يوجد بيانات متراكمة عبر 3 فئات.** كل اختبارات
`test_achievement_auto_grant_*` (التدريب/بناء الفريق/تمويل المشاريع)
بتنضّف صفوفها بنفسها في `finally` block (تأكدت من قراءة الكود الفعلي —
مثال: `test_achievement_auto_grant_training_implementation.py` بيحذف
`UserAchievement`/`AchievementDefinition`/`User` في `finally` كل اختبار).
الصف الوحيد المتبقي فعليًا هو throwaway واحد من جلسة
`achievements-foundation-implementation` (تعريف اسمه
`REGTEST-ACHIEVEMENT-DUP-*` — تنظيف `finally` بتاعه فشل جزئيًا وقتها، لا
علاقة له بهذه الجلسة).

**الأثر على أسلوب الاختبار:** بدل الاعتماد على قيم مطلقة (اللي كانت
هتتأثر بيه هذا الصف الشاذ)، الاختبار الحي الجديد بيقيس **delta** (قبل
منح جديد / بعده) — نتيجة صحيحة بغض النظر عن أي بيانات throwaway قديمة
متبقية في DB.

---

## 3. الاختبار الحي (`tests/test_achievements_stats_endpoints_implementation.py`)

اختباران، DB حقيقية بالكامل، صفر mock:

### `test_stats_by_category_and_top_users_match_real_grants`
1. إنشاء 3 مستخدمين throwaway (أ، ب، ج) + admin.
2. إنشاء 3 تعريفات (TRAINING، TEAM_BUILDING، PROJECT_FUNDING).
3. 6 منح حقيقية: TRAINING→(أ،ب) [2]، TEAM_BUILDING→(أ) [1]،
   PROJECT_FUNDING→(أ،ب،ج) [3].
4. عبر `AchievementService` مباشرة: تأكيد الـdelta بالظبط لكل فئة
   (2/1/3)، وتأكيد `top-users` (أ=3، ب=2، ج=1) بترتيب تنازلي صحيح
   واسم مستخدم مطابق.
5. ترقية `admin` لـ`SUPER_ADMIN` فعليًا في DB (`UPDATE users SET
   system_role=...`)، ثم استدعاء **HTTP فعلي** (`httpx.AsyncClient` +
   `ASGITransport` ضد `fastapi_app` نفسه، مش استدعاء مباشر للـservice) —
   `dependency_overrides` على `app.core.security.get_current_active_user`
   فقط (الـsub-dependency الحقيقية جوّه `get_current_superuser`، مش
   `get_current_superuser` نفسها) — فمنطق فحص `system_role` بيتنفَّذ
   فعليًا زي الإنتاج بالظبط، مش متجاوَز بالكامل. تأكيد إن أرقام الـHTTP
   مطابقة بالحرف لنفس الأرقام المحسوبة مباشرة عبر الخدمة.
6. تنظيف كامل في `finally` (نفس نمط كل اختبارات achievements الأخرى).

### `test_stats_endpoints_reject_non_superuser_via_http`
مستخدم عادي (`SystemRole.USER` الافتراضي عند التسجيل، بلا أي تعديل) →
403 على الـendpoint-ين، عبر نفس آلية الـoverride فوق.

```
tests/test_achievements_stats_endpoints_implementation.py::test_stats_by_category_and_top_users_match_real_grants PASSED
tests/test_achievements_stats_endpoints_implementation.py::test_stats_endpoints_reject_non_superuser_via_http PASSED
2 passed in 70.48s
```

**تأكيد إضافي:** أُعيد تشغيل كل الـ16 اختبار حي القائم بالفعل لدومين
`achievements` (5 ملفات) منفصلة — **16/16 لسه PASSED**.

**تأكيد إضافي مباشر ضد DB بعد كل التشغيلات:** استعلام مباشر أكَّد رجوع
DB بالظبط لنفس الحالة قبل الجلسة — صف throwaway وحيد قديم
(`REGTEST-ACHIEVEMENT-DUP-18d7e4ed88`)، صفر تسريب بيانات جديدة من
اختبارات هذه الجلسة.

---

## 4. Regression الكامل

```
15 failed, 201 passed, 2 xfailed, 262 warnings in 529.85s (0:08:49)
```
(باستثناء `test_affiliate_service_missing_methods.py` — نفس collection
error مسبق غير مرتبط، خارج نطاق هذه الجلسة).

**مطابقة تامة للأساس الموثَّق** (جلسة `achievement-auto-grant-project-funding`،
آخر جلسة achievements موثَّقة في `PROGRESS_LOG.md`):
`15 failed, 199 passed, 2 xfailed, 260 warnings`.

- `201 = 199 + 2` (الاختبارين الحيين الجديدين).
- `262 = 260 + 2` (نفس تحذير Redis `DeprecationWarning` القياسي لكل
  اختبار حي جديد يستخدم `db` fixture — راجع `conftest.py`).
- **نفس أسماء الـ15 فشل بالحرف** — كلها pre-existing وموثَّقة في تقارير
  investigation منفصلة (`test_realestate_insurance_savepoint`،
  `test_saas_active_subscription` ×2، `test_user_repository_get_by_id_audit`
  ×9، `test_user_repository_get_user_audit` ×2)، لا علاقة لها بهذا
  التعديل.

**صفر regression جديد.**

---

## 5. لم يُلمَس إطلاقًا

- أي migration أو جدول قائم.
- أي دالة/endpoint موجود في `achievements` (فقط إضافات جديدة).
- `app/main.py` (الراوتر مسجَّل بالفعل).
- أي دومين آخر غير `achievements` (باستثناء إضافة §6 تحت، دومين `identity`).

---

## 6. إضافة لاحقة (نفس اليوم): `GET /achievements/stats/by-definition`

بطلب مباشر من جلسة بناء لوحة الأدمن في الفرونت إند — عمود "عدد
المستخدمين اللي حققوه" في جدول التعريفات محتاج بيانات مجمَّعة حسب
`achievement_definition_id`، ومفيش أي endpoint موجود كان بيوفرها.

**يرجّع** `[{achievement_definition_id, achievement_name, count}]` —
نفس نمط `by-category` بالحرف (INNER JOIN من `UserAchievement` لـ
`AchievementDefinition`، `GROUP BY` على `id, name`، تعريف بدون أي منح
فعلي مش هيظهر).

| ملف | التغيير |
|---|---|
| `schemas.py` | `AchievementDefinitionStatItem` |
| `repository.py` | `count_users_by_achievement_definition` |
| `service.py` | `get_stats_by_definition` |
| `router.py` | `GET /stats/by-definition` (`get_current_superuser`) |

**اكتشاف حي (مُعاد التأكيد):** فحص مباشر لـDB قبل الكتابة أثبت من
جديد عدم وجود "3 تعريفات" كما افتُرض — لسه نفس الصف الوحيد
(`REGTEST-ACHIEVEMENT-DUP-*`). الاختبار الحي (امتداد لنفس دالة الاختبار
الموجودة في `test_achievements_stats_endpoints_implementation.py`)
استخدم قيمة **مطلقة** هنا (مش delta) لأن تعريفات الاختبار throwaway
جديدة بـid لسه مفيش له أي منح سابق — 3 تعريفات جديدة (TRAINING،
TEAM_BUILDING، PROJECT_FUNDING) بعدد منح مختلف لكل واحد (2، 1، 3
بالترتيب)، تأكيد الأرقام مباشرة عبر `AchievementService` وعبر HTTP فعلي
(SUPER_ADMIN) بالحرف.

```
tests/test_achievements_stats_endpoints_implementation.py::test_stats_by_category_and_top_users_match_real_grants PASSED
tests/test_achievements_stats_endpoints_implementation.py::test_stats_endpoints_reject_non_superuser_via_http PASSED
2 passed in 65.56s
```

Regression الكامل بعد هذه الإضافة (قبل إضافة §7): `15 failed, 201
passed, 2 xfailed, 262 warnings` — مطابق تمامًا (نفس عدد الاختبارين
الحيين، لأن الإضافة كانت توسيع لدالة موجودة مش دالة جديدة).

---

## 7. إضافة لاحقة تانية (نفس اليوم، دومين `identity`): `GET /identity/users/search`

فورم المنح اليدوي في لوحة الأدمن محتاج "بحث بالاسم/الإيميل عن مستخدم".
**اكتشاف:** لا يوجد أي endpoint بحث/قائمة مستخدمين شغّال في الباك إند
إطلاقًا (تأكَّد بالبحث الكامل في الكودبيز) — الفرونت إند القديم
(`entity-representatives.tsx`) بينادي `/users/search` (بلا `/identity`
prefix)، وهو endpoint **غير موجود إطلاقًا**، بج قديم منفصل تمامًا خارج
نطاق هذه الجلسة (لم يُصلَح، موثَّق هنا كملاحظة بس).

**الحل:** `GET /identity/users/search?q=&limit=` — دومين `identity` (مش
`achievements`)، على `protected_router` الموجود بالفعل:
- `repository.py`: `search_by_username_or_email` — `ILIKE` على
  `username` أو `email`، مقيّد بـ`tenant_id`، `limit`.
- `service.py`: `UserService.search_users`.
- `schemas.py`: `UserSearchResult` (`user_id`, `name`, `email`).
- `router.py`: endpoint جديد، حماية **`is_admin_or_above`** (مش
  `get_current_superuser`) — نفس نمط `GET /identity/invitations?scope=tenant`
  الموجود بالفعل في نفس الدومين بالحرف (الطلب كان صريحًا: "تأكد من الدور
  الصح المستخدَم في endpoints مشابهة بنفس الدومين").

**اختبار حي جديد (2/2 PASSED)** —
`tests/test_identity_users_search_implementation.py`:
- بحث جزئي (ILIKE) بمستخدم throwaway حقيقي من جلسات اليوم + عزل تينانت
  (مستخدم بنفس نص البحث بالظبط في تينانت `16` "TEST_TENANT_B" — تينانت
  `2` مش موجود فعليًا في DB، اتأكَّد واستُبدِل).
- حماية HTTP فعلية: مستخدم عادي (USER) → 403، ADMIN → 200 بالنتيجة
  الصحيحة.

```
tests/test_identity_users_search_implementation.py::test_search_users_matches_partial_username_or_email_with_tenant_isolation PASSED
tests/test_identity_users_search_implementation.py::test_search_users_endpoint_requires_admin_or_above_via_http PASSED
2 passed in 75.62s
```

**Regression الكامل النهائي (بعد §6+§7، باستثناء
`test_affiliate_service_missing_methods.py` غير المرتبط):**
`15 failed, 203 passed, 2 xfailed, 264 warnings in 1509.30s` — مطابقة
تامة للأساس الموثَّق (`199 passed, 260 warnings`): `203 = 199 + 4`
(4 اختبارات حية جديدة عبر الجلستين §القديمة+§6+§7 مجتمعتين)، `264 = 260
+ 4`. **نفس أسماء الـ15 فشل بالحرف**، صفر regression جديد.

**الملفات المعدَّلة إضافيًا:** `app/domains/identity/{schemas,repository,service,router}.py`
(إضافات فقط). **جديدة:** `tests/test_identity_users_search_implementation.py`.
