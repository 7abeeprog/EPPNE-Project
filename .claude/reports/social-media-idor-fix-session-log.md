# جلسة فحص IDOR/أمان عميق في `social` (القطاع العاشر والأخير في السويپ)

**بدأ التسجيل:** 2026-08-24
**الحالة:** 🔴 **متوقفة عند نقطة قرار — الدومين بالكامل معطوب وظيفيًا (100% من الـendpoints)، التحقق الحي عبر الـAPI مستحيل قبل حل هذه النقطة أولًا.** صفر تنفيذ/تعديل كود حتى الآن، بالكامل قراءة + تحقق حي محدود بالحدود اللي أمكن الوصول لها.

**نطاق الجلسة:** `eppne-backend/app/domains/social/{router,service,repository,schemas,models}.py` بالكامل (18 endpoint).

---

## 0) المرجع الميكانيكي — ماذا كان موثَّقًا عن `social` قبل هذه الجلسة

- **`.claude/reports/simpletenant-fix-session-log.md`** (سطر 77، ضمن قائمة "✅ (أ) — `.id` مستخدَمة بشكل صحيح، صفر كراش"): `social` مذكور بـ**19 موضع**، كلها `tenant: AcademyTenant = Depends(get_current_tenant)` ثم `cast(int, tenant.id)` صح. **تأكَّد بقراءة حية لـ`router.py` كامل اليوم: لا يعاني من باج `SimpleTenant`/type-mismatch إطلاقًا.**
- **`.claude/plans/critical-finding-xtenant-systemic.md`** (سطر 300): `social` هو **الصف #17** في جدول 🔴 SUSPICIOUS (شكل ثغرة X-Tenant-ID العام) — نصه بالحرف: *"`router.py:315-328` → `service.py:594-597` — 🟠 أقل حدة — إنشاء بس (خطط اشتراك جماعية)، مفيش قراءة/تعديل بيانات موجودة لتينانت تاني"*. هذا يشير تحديدًا لـ`create_subscription_plan` (سوبريوزر، `tenant_id` من الهيدر مباشرة بلا مقارنة مع `current_user.tenant_id`) — **نفس النمط الميكانيكي المُصلَح بالفعل في `academy`/`digital_twin`/`projects`/... (`get_current_tenant` → `cast(int, current_user.tenant_id)`)**.
  - نفس الملف (سطر 210) يوثِّق **`social.subscribe_group_to_plan`** ضمن فئة منفصلة تمامًا (hardcoded system account): `service.py:633` — `sender_id=0` هاردكودد، `user_id=0` غير موجود أصلًا (الـPK يبدأ من 1) → **`IntegrityError` قاطع لكل محاولة اشتراك جماعي، فشل وظيفي مش تسريب مالي**. **موثَّقة، مؤجَّلة، جزء من قرار معماري منفصل — لم تُلمَس في هذه الجلسة، فقط مُشار لها هنا كمرجع.**
- **`.claude/reports/finance-idor-security-fix-session-log.md`** (سطر 55): نفس الإشارة لـ`subscribe_group_to_plan`/`sender_id=0` — **مؤكَّدة أعلى كمرجع فقط، لا لمس.**
- **`.claude/reports/digital-twin-idor-fix-session-log.md`** + **`academy-idor-fix-session-log.md`**: اعتُمدت منهجيتهما بالحرف هنا (قراءة كاملة → جدول شامل → تصنيف تحليلي → تحقق حي → عرض للموافقة قبل أي تنفيذ).

**الخلاصة: صفر تناقض بين المراجع، صفر إصلاح سابق فعلي على `social` — دومين لم يُلمَس بعد بأي جلسة IDOR سابقة.**

---

## 1) 🔴🔴🔴🔴 اكتشاف حاسم غير متوقَّع — الدومين بالكامل معطوب وظيفيًا، 100% من الـ18 endpoint

قبل أي تحليل IDOR، محاولة التحقق الحي الأولى (`POST /social/posts` بمستخدم حقيقي مُصادَق، بيانات صحيحة) فشلت بـ`500 Internal Server Error`. تتبُّع اللوج الحي كشف:

```
File "app/domains/social/service.py", line 63, in _check_saas_limits
    has_access = await saas_service.can_access_service(tenant_id, feature)
TypeError: SaaSControlService.can_access_service() takes 2 positional arguments but 3 were given
```

**السبب الجذري (قراءة حية لـ`app/domains/saas/service.py:34-38,215`):**
```python
class SaaSControlService:
    def __init__(self, db: AsyncSession, tenant_id: int):   # tenant_id مربوط بالفعل في الـconstructor
        self.tenant_id = tenant_id
        ...
    async def can_access_service(self, service_code: str) -> bool:   # ياخد service_code بس، تاني
```

بينما `social/service.py:61-66`:
```python
async def _check_saas_limits(self, tenant_id: int, feature: str = "social"):
    saas_service = SaaSSubscriptionService(self.db, tenant_id)          # tenant_id اتربط هنا صح
    has_access = await saas_service.can_access_service(tenant_id, feature)   # 🔴 تمرير tenant_id تاني + feature = 3 args لدالة تاخد 2 بس
```

**الأثر: `_check_saas_limits` هي **أول سطر تنفيذي في كل دالة واحدة من الـ15 دالة في `SocialService`** (كل الـendpoints بلا استثناء، شاملة `get_feed` القراءة البسيطة) — **كل استدعاء لأي endpoint في `/social/*` يفشل فورًا بـ`500` قبل ما يوصل لأي منطق فعلي، بما فيه أي فحص ملكية/تينانت.**

هذه **فئة خامسة** من نمط "باج توقيع استدعاء" الموثَّق مسبقًا في `simpletenant-fix-session-log.md` (duplicate-kwarg، اتكشف 4 مرات في `academy`/`sovereign_entities`/`commerce`) — لكن هنا الفئة الفرعية مختلفة (عدد args غلط، مش تكرار مفتاح)، **وأخطر أثرًا بكثير: مش endpoint واحد أو دالة واحدة، دي **كل** الدومين، لأن الفحص ده shared bottleneck في أول كل دالة.**

**الأثر العملي على نطاق هذه الجلسة:** التحقق الحي عبر الـAPI الحقيقي (المطلوب صراحة قبل أي إصلاح IDOR) **مستحيل حاليًا لأي endpoint في `social`** — القراءة المفتوحة (`get_feed`) والكتابات الحساسة (`subscribe_group`, إلخ) كلهم بيفشلوا بنفس الـ`500` قبل الوصول لأي كود IDOR-relevant. **هذا اكتشاف منفصل تمامًا عن نطاق "السويپ IDOR" الأصلي، لكنه يمنع تنفيذ الطلب الأصلي (تحقق حي) بالكامل حتى يُحل.**

---

## 2) الجدول الكامل — 18 endpoint (تحليل كود ثابت، غير قابل للتحقق الحي بسبب §1)

| # | الدالة | المسار | `current_user`؟ | مصدر `tenant_id` | فلتر تينانت/ملكية فعلي في الـrepository |
|---|---|---|---|---|---|
| 1 | `create_post` | `POST /posts` | active_user | هيدر (`.id`) | يكتب `tenant_id`/`author_id` صح عند الإنشاء |
| 2 | `get_feed` | `GET /feed` | **لا يوجد** | هيدر | 🔴 **`get_global_feed(skip, limit)` — صفر فلتر `tenant_id` في الاستعلام نفسه، رغم إن `tenant_id` بيوصلها من الراوتر أصلًا ومش بتتمرر** |
| 3 | `like_post` | `POST /posts/{id}/like` | active_user | هيدر | ✅ `post.tenant_id != tenant_id` → `NotFoundError` قبل أي تعديل |
| 4 | `share_post` | `POST /posts/{id}/share` | active_user | هيدر | ✅ نفس الفحص أعلاه |
| 5 | `create_group` | `POST /groups` | active_user | هيدر | يكتب `tenant_id` صح؛ 🔴 لكن `add_group_member` (منادى داخليًا لإضافة المنشئ) **ما بيمررش `tenant_id`** رغم إن العمود `NOT NULL` في الموديل |
| 6 | `join_group` | `POST /groups/{id}/join` | active_user | هيدر | ✅ فحص `SocialGroup.id==group_id AND tenant_id==tenant_id` قبل الإضافة؛ 🔴 لكن نفس باج `add_group_member` (بند 5) |
| 7 | `create_contract` | `POST /contracts` | active_user | هيدر | يكتب `tenant_id` صح |
| 8 | `sign_contract` | `POST /contracts/{id}/sign` | active_user | هيدر | ✅ `contract.tenant_id != tenant_id` → `NotFoundError`؛ 🔴 لكن `add_signature` **ما بيمررش `tenant_id`** رغم `NOT NULL` |
| 9 | `setup_match_profile` | `POST /match/profile` | active_user | هيدر | 🟡 `create_or_update_match_profile` بتبحث بـ`user_id` بس (`get_match_profile`، صفر فلتر `tenant_id`) — بروفايل واحد **عالمي لكل مستخدم**، بيتحرك بين التينانتات مع كل استدعاء (تلوث بيانات ذاتي، مش IDOR كلاسيكي) |
| 10 | `get_match_suggestions` | `GET /match/suggestions` | active_user | هيدر | ✅ `profile.tenant_id != tenant_id` → `NotFoundError` (لكن نفس البروفايل العالمي من بند 9) |
| 11 | `request_connection` | `POST /connections/request` | active_user | هيدر | 🔴 **`repo.create_connection(user_a_id, user_b_id, connection_type)` — التوقيع الحقيقي 3 معاملات بس، والـservice بينادّيها بـ`tenant_id=`, `status=`, `idempotency_key=` كمان → `TypeError` فوري لكل استدعاء (بعد تخطي §1)**؛ + `repo.get_connection` **غير موجودة إطلاقًا** (تُستدعى فقط في مسار cache-hit الخاص بالـidempotency) |
| 12 | `get_my_connections` | `GET /connections` | active_user | هيدر | 🔴 **`get_user_connections(user_id)` — صفر فلتر `tenant_id`، بترجع كل الاتصالات لنفس `user_id` عبر كل التينانتات** |
| 13 | `create_occasion` | `POST /occasions` | active_user | هيدر | يكتب `tenant_id`/`user_id` صح |
| 14 | `get_upcoming_occasions` | `GET /occasions/upcoming` | active_user | هيدر | ✅ فلتر مزدوج `user_id AND tenant_id` في الاستعلام نفسه |
| 15 | `send_digital_gift` | `POST /gifts/digital` | active_user | هيدر | 🟡 `receiver_id` غير مُتحقَّق من انتمائه لنفس التينانت — `_get_user_email` بترجع بريد وهمي (`user_{id}@eppne.com`) بصمت لو المستلم من تينانت تاني، فالتحويل المالي يذهب لبريد غير حقيقي بدل رفض العملية |
| 16 | `request_physical_gift` | `POST /gifts/physical` | active_user | هيدر | 🟡 نفس ملاحظة `receiver_id`/`product_id` غير مُتحقَّقين من التينانت |
| 17 | `create_subscription_plan` | `POST /groups/subscriptions/plans` | **superuser** | هيدر مباشر، **صفر مقارنة مع `current_user.tenant_id`** | 🔴 **نفس نمط X-Tenant-ID العام الموثَّق مسبقًا (`critical-finding-xtenant-systemic.md` #17)** — سوبريوزر تينانت1 يقدر ينشئ خطة اشتراك جماعية تحت أي `tenant_id` بمجرد تزوير الهيدر |
| 18 | `subscribe_group` | `POST /groups/{id}/subscribe` | active_user | هيدر | 🔴 **جديد، غير موثَّق سابقًا:** `subscribe_group_to_plan` بتتحقق من `plan.tenant_id == tenant_id` بس — **صفر تحقق إن `group_id` نفسه ملك نفس التينانت** — أي مستخدم عادي (بلا تزوير هيدر حتى) يقدر يمرر `group_id` لمجموعة **تخص تينانت تاني بالكامل** ويشترك فيها بخطة تحت تينانته هو؛ (ملاحظة: تنفيذ هذا الاستدعاء حاليًا هيفشل قبل ما يوصل هنا بسبب `sender_id=0` الموثَّق أعلاه — **لم يُختبر حيًا بناءً على توجيه الجلسة**) + 🔴 `repo.get_group_subscription` **غير موجودة إطلاقًا** (مسار cache-hit) |
| — | `get_group_features` | `GET /groups/{id}/features` | active_user | هيدر | ✅ مفلترة بـ`tenant_id` بالكامل، إرجاع `[]` بأمان لو `group_id` مش تابع للتينانت |

**ملخص التصنيف:**
- **🔴 IDOR/تسريب بيانات حقيقي (بلا الحاجة لتزوير هيدر حتى):** #2 (`get_feed` — قراءة مفتوحة عالمية بلا مصادقة أصلًا)، #12 (`get_my_connections` — تسريب عبر-تينانت لنفس المستخدم)، #18 (`subscribe_group` — كتابة على مورد `group_id` بلا فحص ملكية).
- **🔴 نمط X-Tenant-ID العام (نفس الفئة المُصلَحة في 9 دومينات أخرى):** #17 (`create_subscription_plan`).
- **🔴 باجات كراش (مش IDOR، لكن تمنع الميزة بالكامل):** #1 عام (§1)، #5/#6 (`add_group_member` بلا `tenant_id`)، #8 (`add_signature` بلا `tenant_id`)، #11 (`create_connection`/`get_connection`)، #18 الفرعي (`get_group_subscription` غائبة).
- **🟡 تلوث بيانات / صفة تحقق ضعيفة:** #9/#10 (بروفايل matchmaking عالمي)، #15/#16 (مستلم هدية غير مُتحقَّق من التينانت).
- **✅ سليم فعليًا (فحص ملكية/تينانت حقيقي موجود):** #3, #4, #6 (فحص الانضمام نفسه)، #8 (فحص التوقيع نفسه)، #10 (فحص البروفايل نفسه)، #14، الـ`get_group_features` الأخيرة.

---

## 3) التحقق الحي — ما أمكن تنفيذه فعليًا، وما تعذَّر بسبب §1

**البيئة:** `uvicorn` شُغِّل محليًا (venv المشروع، DB الحقيقية `eppne_db`/`5435`، تأكَّد اتصال Redis). **مستخدمو throwaway مُعاد استخدامهم بلا تعديل** (موثَّقين مركزيًا في `throwaway-test-users.md`): `772` (`TEST_super_a`, تينانت1, SUPER_ADMIN)، `773` (`TEST_instr_a`, تينانت1, SUPER_ADMIN)، `774` (`TEST_instr_b`, تينانت16, SUPER_ADMIN). تسجيل دخول حي ناجح للثلاثة (توكنات JWT صالحة مؤكَّدة، بلا تعديل بيانات).

**أول محاولة تحقق حي (`POST /social/posts` بتوكن `772` حقيقي، بيانات صحيحة) اصطدمت فورًا بباج §1 (`500`, `TypeError` في `_check_saas_limits`).**

بما إن `_check_saas_limits` أول سطر في **كل** دالة service (شاملة `get_feed` القراءة البسيطة اللي هي أعلى أولوية تحقق في هذه الجلسة)، **لا يوجد أي endpoint واحد في `social` قابل للتحقق الحي عبر الـAPI الحقيقي حاليًا** — بلا استثناء. تم إيقاف محاولات التحقق الحي الإضافية عند هذه النقطة (بدل الالتفاف حول الباج بتعديل كود بلا موافقة، أو بزرع بيانات SQL خام لاختبار مسارات تعتمد أصلًا على منطق معطوب) تنفيذًا لقاعدة الجلسة الصريحة: **صفر تنفيذ/تعديل كود قبل الموافقة.**

**السيرفر التجريبي أُوقِف بالكامل** (تأكيد: `GET /docs` → لا استجابة، `netstat` على المنفذ 8000 فاضي) — **لم يُترك شغالًا** خلافًا لجلسات سابقة، لأن التحقق الحي الفعلي لأي بند IDOR لم يبدأ أصلًا.

---

## 4) خيارات مقترَحة — قرار مطلوب منك قبل أي استكمال

هذه الجلسة وصلت لنقطة لا يمكن تجاوزها بقراءة كود فقط ولا بتحقق حي حقيقي بدون قرارك:

**الخيار أ — إصلاح باج §1 فقط الآن (سطر واحد، `social/service.py:64`)، ثم استكمال التحقق الحي الكامل لكل بنود §2، ثم عرض جدول IDOR نهائي + حل مقترَح لكل بند للموافقة.**
سطر الإصلاح المقترَح (لسه معروض، مش مطبَّق):
```python
# قبل
has_access = await saas_service.can_access_service(tenant_id, feature)
# بعد
has_access = await saas_service.can_access_service(feature)
```
هذا إصلاح **منفصل تمامًا عن أي قرار IDOR** — باج توقيع استدعاء بسيط، بلا أي تغيير في الصلاحيات أو المنطق الأمني. لكنه لا يزال **تعديل كود على ملف موجود**، يحتاج موافقتك الصريحة قبل التنفيذ (نفس قاعدة الجلسة).

**الخيار ب — الاكتفاء بتحليل الكود الثابت (§2 أعلاه) كأساس للقرار، بلا أي تحقق حي، والانتقال مباشرة لعرض حلول IDOR المقترَحة اعتمادًا على قراءة الكود وحدها.**
أضعف من ناحية "دليل قاطع" (كل التقارير السابقة في السويپ اعتمدت SELECT/curl مستقل كدليل حاسم)، لكنه يحترم حرفيًا "صفر تنفيذ" لو ده المطلوب لهذه الجلسة تحديدًا.

**الخيار ج — توثيق باج §1 فقط الآن (بدون إصلاح)، وإغلاق الجلسة عند هذه النقطة، وفتح قرار الإصلاح (باج §1 ثم IDOR) في جلسة/خطوة منفصلة لاحقة بموافقة صريحة مسبقة.**

---

## 5) الحلول المقترَحة لكل بند IDOR (بانتظار قرارك في §4 — **صفر تنفيذ حتى الآن**)

| # | البند | الحل المقترَح (مفهومي، لم يُصَغ ككود بعد) |
|---|---|---|
| §2.2 | `get_feed` بلا فلتر تينانت | تمرير `tenant_id` من الراوتر لـ`get_global_feed` + إضافة `WHERE Post.tenant_id == tenant_id` في الاستعلام |
| §2.12 | `get_my_connections` بلا فلتر تينانت | إضافة `tenant_id` لتوقيع `get_user_connections` وفلترة الاستعلام به |
| §2.18 | `subscribe_group` بلا فحص ملكية `group_id` | إضافة `SocialGroup` lookup بفلتر `id==group_id AND tenant_id==tenant_id` قبل إنشاء الاشتراك (نفس نمط فحص الانضمام الموجود بالفعل في `join_group`)، **بدون لمس `sender_id=0` (مؤجَّل، خارج النطاق)** |
| §2.17 | `create_subscription_plan` — نمط X-Tenant-ID العام | نفس القاعدة الميكانيكية المُطبَّقة على 9 دومينات أخرى: إزالة `Depends(get_current_tenant)`، استبدالها بـ`cast(int, current_user.tenant_id)` |
| §2.5/6, §2.8 | `add_group_member`/`add_signature` بلا `tenant_id` (كراش NOT NULL) | تمرير `tenant_id` صراحة في الاستدعاءين |
| §2.11 | `create_connection`/`get_connection` مفقودة/توقيع خاطئ | مواءمة توقيع `create_connection` مع الاستدعاء الفعلي (`tenant_id`, `status`, `idempotency_key`) + إضافة `get_connection` مفلترة بالتينانت |
| §2.18 الفرعي | `get_group_subscription` مفقودة | إضافة الدالة (مفلترة بـ`tenant_id`) |
| §2.9/10 | بروفايل matchmaking عالمي | قرار تصميمي: هل البروفايل يُفترض واحد لكل مستخدم عبر كل التينانتات (بالتصميم) أم لكل (مستخدم+تينانت)؟ يحتاج توجيهك قبل أي تغيير في الفلتر |
| §2.15/16 | مستلم هدية غير مُتحقَّق من التينانت | إضافة فحص صريح إن `receiver_id` (والـ`product_id` للهدايا المادية) تابع لنفس `tenant_id`، رفض بـ`NotFoundError` بدل fallback صامت |

**كل الحلول أعلاه مفاهيمية فقط، بانتظار موافقتك على الترتيب/النطاق قبل أي ديف يُعرض أو يُطبَّق — تمامًا زي كل الجلسات السابقة في السويپ.**

---

## 6) [2026-08-24] موافقة المستخدم — الخيار أ + قرارات إضافية، والتنفيذ الكامل

**موافقة صريحة على الخيار أ** (إصلاح باج §1 أولًا، تحقق حي سريع، ثم استكمال كل بنود §2) + 3 قرارات إضافية:
1. §2.9/10 (بروفايل matchmaking عالمي): **قرار تصميمي مقصود** — بروفايل واحد لكل مستخدم عبر كل التينانتات (matchmaking مش مرتبط بمنظمة/تينانت منطقيًا كمنتج). **صفر تغيير كود** — موثَّق هنا فقط.
2. §2.15/16 (هدايا لمستلم غير مُتحقَّق): فحص صريح `receiver_id` ضمن نفس التينانت.
3. باقي باجات الكراش (§2.5/6, §2.8, §2.11, §18 الفرعي): تُصلَح كلها كجزء من نفس الجلسة، شرط لإتمام التحقق الحي.

### 6.1 اكتشاف إضافي أثناء التنفيذ — باجان جديدان غير موثَّقين في §2 الأصلي

أثناء محاولة التحقق الحي لـ`create_group`، ظهر باج ثالث من نفس عائلة "توقيع استدعاء خاطئ" (بعد §1): `service.create_group` كانت بتمرر `idempotency_key=idempotency_key` لـ`repo.create_group(**kwargs)` → `SocialGroup(**kwargs)`، لكن **موديل `SocialGroup` هو الوحيد بين كل موديلات الدومين اللي معندوش عمود `idempotency_key` إطلاقًا** (تأكَّد بـ`grep` شامل على `models.py` — كل موديل تاني بيدعم idempotency عنده العمود، `SocialGroup` وحدها الاستثناء) → `TypeError: 'idempotency_key' is an invalid keyword argument for SocialGroup`، فوري لكل `create_group`. **الإصلاح المطبَّق:** حذف تمرير `idempotency_key` من الاستدعاء (الحماية الحقيقية من التكرار بتحصل بالفعل عبر Redis idempotency cache في `_validate_idempotency`/`_store_idempotency`، مش عبر عمود الموديل). **إضافة الموديل للعمود (لو الـidempotency على مستوى DB مطلوبة فعليًا) قرار منفصل يحتاج migration — خارج نطاق هذه الجلسة.**

بالتزامن، اكتُشف إن `repo.get_group(group_id, tenant_id)` (تُستدعى من `service.create_group` في مسار cache-hit، سطر 152) **غير موجودة إطلاقًا** — نفس فئة `get_connection`/`get_digital_gift`/`get_group_subscription` المُصلَحة أصلًا. **أُضيفت بنفس النمط** (مفلترة بـ`tenant_id`، اتساقًا مع باقي الدومين).

### 6.2 كل الإصلاحات المُطبَّقة فعليًا (3 ملفات، صفر لمس لـ`models.py`/`schemas.py` — صفر migration)

| # | الملف:الدالة | التغيير |
|---|---|---|
| 1 | `service.py:_check_saas_limits` | إصلاح §1 — `can_access_service(tenant_id, feature)` → `can_access_service(feature)` |
| 2 | `repository.py:get_global_feed` + `service.py:get_feed` | إضافة `tenant_id` كفلتر في الاستعلام (§2.2) |
| 3 | `repository.py:get_user_connections` + `service.py:get_my_connections` | إضافة `tenant_id` كفلتر (§2.12) |
| 4 | `repository.py:create_connection` | إصلاح التوقيع الكامل (`tenant_id`, `status`, `idempotency_key`) ليطابق الاستدعاء الفعلي (§2.11) |
| 5 | `repository.py:get_connection` (جديدة) | إضافة، لمسار cache-hit في `request_connection` (§2.11) |
| 6 | `repository.py:add_group_member` + استدعاءاتها (`create_group` الداخلي و`join_group`) | إضافة `tenant_id` (عمود `NOT NULL` كان بيتكسر) (§2.5/6) |
| 7 | `repository.py:add_signature` + `service.py:sign_contract` | إضافة `tenant_id` (نفس فئة NOT NULL) (§2.8) |
| 8 | `repository.py:get_digital_gift` (جديدة) | لمسار cache-hit في `send_digital_gift` |
| 9 | `service.py:request_physical_gift` | تصحيح استدعاء `get_physical_gift_request` (كان ناقص `tenant_id`) |
| 10 | `repository.py:get_group_subscription` (جديدة) | لمسار cache-hit في `subscribe_group_to_plan` (§18 الفرعي) |
| 11 | `router.py:create_subscription_plan` | إزالة `Depends(get_current_tenant)` → `cast(int, current_user.tenant_id)` (§2.17، نفس نمط academy/digital_twin) |
| 12 | `service.py:subscribe_group_to_plan` | فحص ملكية `group_id` (`SocialGroup.tenant_id == tenant_id`) قبل أي كتابة، **قبل** الوصول لكود `sender_id=0` المؤجَّل (§2.18) |
| 13 | `service.py:_get_user_email` | ترفع `NotFoundError` بدل fallback صامت لبريد وهمي؛ `send_digital_gift`/`request_physical_gift` بيستدعوها **قبل** أي معاملة مالية (§2.15/16) |
| 14 | `service.py:create_group` + `repository.py:get_group` (جديدة) | حذف `idempotency_key` غير المدعوم من `SocialGroup` + إضافة `get_group` لمسار cache-hit (اكتشاف §6.1) |

### 6.3 التحقق الحي الكامل — بيئة ومنهجية

`uvicorn` محلي (venv المشروع)، DB الحقيقية (`eppne_db`/`5435`)، Redis مؤكَّد. **مستخدمو throwaway مُعاد استخدامهم بلا أي تعديل بيانات المستخدمين أنفسهم:** `772`/`773` (تينانت1)، `774` (تينانت16).

**سد فجوة إضافية اكتُشفت قبل أي إصلاح كود:** خدمة `"social"` **غير موجودة إطلاقًا** في `saas_service_catalog` (`can_access_service` كانت هترجع `False` دايمًا لكل تينانت، بشكل مستقل تمامًا عن باج §1) — زُرعت بيانات throwaway واضحة العنوان (`TEST_Social_Service`, `saas_service_catalog.id=59`؛ خطة `test_social_free`, `id=61`؛ `saas_tenant_service_access` + `saas_tenant_subscriptions` نشطة لتينانت1 و16) لفتح القفل أمام التحقق الحي — **بيانات اختبار فقط، صفر تعديل كود لهذا الجزء.**

**النتائج (كل الاختبارات بـ`curl` + تحقق `SELECT` مستقل من الـDB، مش status code بس):**

| البند | السيناريو | قبل الإصلاح | بعد الإصلاح | الدليل |
|---|---|---|---|---|
| §1 | `POST /social/posts` مستخدم حقيقي | `500 TypeError` | `201` نجاح | رد JSON كامل |
| §2.2 `get_feed` | A(تينانت1) ينشر، B(تينانت16) ينشر، كل واحد يقرأ الفيد بهيدره الحقيقي | (لم يُختبر — كان معطوبًا بـ§1) | A يشوف بوسته بس، B يشوف بوسته بس، طلب بلا مصادقة بهيدر=1 يشوف بوست تينانت1 بس | ردود JSON مطابقة تمامًا للتوقع |
| §2.11/12 `request_connection`/`get_my_connections` | C(773) يطلب اتصال بـA(772)، A يفحص اتصالاته بهيدر حقيقي(1) ثم بهيدر مزوَّر(16) | (كان بيكراش `TypeError` قبل الإصلاح) | إنشاء ناجح (`201`)، هيدر حقيقي يُرجع الاتصال، هيدر مزوَّر يُرجع `[]` | `SELECT` مستقل: `user_connections.id=1, tenant_id=1` مطابق |
| §2.5/6 `create_group`/`join_group` | A ينشئ مجموعة، C ينضم لها | (كان بيكراش `NOT NULL` بعد إصلاح §1 وإصلاح §6.1) | إنشاء ناجح + انضمام ناجح | `SELECT` مستقل: صفَّين في `social_group_members`، `tenant_id=1` للاثنين |
| §2.8 `create_contract`/`sign_contract` | A ينشئ عقد، يوقّعه | (كان بيكراش `NOT NULL`) | إنشاء + توقيع ناجحين | `SELECT` مستقل: `social_contract_signatures.tenant_id=1` |
| §2.17 `create_subscription_plan` | B(774, سوبريوزر، تينانت16 حقيقي) ينشئ خطة بهيدر مزوَّر `X-Tenant-ID: 1` | (غير مُختبَر — النمط نفسه مؤكَّد حيًا في 9 دومينات أخرى) | الخطة اتنشأت تحت **تينانت16 الحقيقي**، الهيدر المزوَّر بلا أي تأثير | `SELECT` مستقل: `group_subscription_plans.tenant_id=16` (مش 1) |
| §2.18 `subscribe_group` | **هجوم:** A(تينانت1 حقيقي) يحاول اشتراك مجموعة B (id=2, تينانت16) بخطة A نفسه (id=2, تينانت1) | (كان بينجح المرور من فحص الملكية، وصولًا لكود `sender_id=0` المؤجَّل) | `404 "Group not found"` — **رُفض قبل الوصول لكود `sender_id=0` المؤجَّل نهائيًا** | `SELECT COUNT(*) FROM group_subscriptions` = `0` (صفر كتابة) — **لم يُختبَر المسار الشرعي (نفس التينانت) عمدًا، تجنبًا لباج `sender_id=0` الموثَّق والمؤجَّل** |
| §2.15/16 `send_digital_gift` | **هجوم:** A يرسل هدية رقمية (قيمة=0) لـB(774, تينانت16) | (كان بينجح صامتًا ببريد وهمي) | `404 "Receiver not found in your tenant"` | — |
| §2.15/16 (ضبط) | A يرسل نفس الهدية لـC(773, نفس تينانته) | — | `201` نجاح | رد JSON كامل، `gift.id=1` |
| §2.15/16 `request_physical_gift` | **هجوم:** A يطلب هدية مادية (سعر=0) لـB(774, تينانت16) | (كان بينجح صامتًا) | `404 "Receiver not found in your tenant"` | — |
| §2.15/16 (ضبط) | A لنفس الطلب لـC(773) بـ`Idempotency-Key` | — | تجاوز فحص المستلم بنجاح (وصل لخطأ منفصل تمامًا خارج النطاق، تفصيل تحت) | — |
| اكتشاف §6.1 | idempotency cache-hit لـ`send_digital_gift` (نفس المفتاح مرتين) | (كانت `get_digital_gift` غير موجودة، كراش مضمون لو اتنفَّذ) | الطلب الثاني رجّع **نفس السجل بالحرف** (`id=2`) بدل إنشاء تاني | ردود JSON متطابقة 100% |

### 6.4 ملاحظة جانبية اكتُشفت أثناء §2.15/16 (موثَّقة فقط، صفر إصلاح، خارج النطاق تمامًا)

اختبار الضبط لـ`request_physical_gift` (A→C، نفس التينانت، مع `Idempotency-Key`) اجتاز فحص المستلم الجديد بنجاح (صفر رفض خاطئ)، لكن اصطدم بخطأ منفصل تمامًا: `"المستلم غير موجود"` (رسالة عربية، من طبقة تانية غير طبقتي) — على الأرجح `finance.transfer` بتحاول تجيب حساب حقيقي بالبريد الثابت `"shop@eppne.com"` والحساب ده مش موجود في الـDB المحلي. **نفس فئة "حساب نظام هاردكودد غير موجود" الموثَّقة بالفعل في `critical-finding-xtenant-systemic.md` لـ`commerce`/`affiliate`/`iot`/نفس `social.subscribe_group_to_plan`** — **لم تُلمَس، خارج النطاق، موثَّقة هنا فقط كدليل إن فحص §2.15/16 نفسه بيشتغل صح (مايرفضش نفس التينانت) وإن الخطأ اللاحق مصدره منطق تاني تمامًا.**

### 6.5 محاولة اختبار إضافية توقَّفت عمدًا (احترامًا لحدود الجلسة الأصلية)

محاولة تجربة idempotency cache-hit لـ`request_connection` (نفس المفتاح مرتين، زوج مستخدمين مختلف) اصطدمت بقيد DB شرعي مسبق الوجود (`ix_user_connection_pair` — فريد لكل زوج، بغض النظر عن idempotency key) بسبب إعادة استخدام نفس زوج المستخدمين من اختبار سابق في نفس الجلسة — **قيد عمل شرعي، صفر علاقة بأي من إصلاحات هذه الجلسة**، لم يُعَد المحاولة بزوج نظيف (نفس نمط الكود مؤكَّد شغال بالفعل عبر اختبار `get_digital_gift` المطابق في §6.3).

### 6.6 `git status`/`git diff --stat` — 3 ملفات فقط، صفر لمس لـ`models.py`/`schemas.py`

```
 M eppne-backend/app/domains/social/repository.py
 M eppne-backend/app/domains/social/router.py
 M eppne-backend/app/domains/social/service.py

 eppne-backend/app/domains/social/repository.py | 58 +++++++++++++++++++++-----
 eppne-backend/app/domains/social/router.py     |  4 +-
 eppne-backend/app/domains/social/service.py    | 31 +++++++++-----
 3 files changed, 70 insertions(+), 23 deletions(-)
```

### 6.7 الحالة النهائية

**✅ كل بنود §2 المتفَق عليها مُصلَحة ومؤكَّدة حيًا** (عدا المسار الشرعي لـ`subscribe_group_to_plan` نفسه، متروك عمدًا بسبب `sender_id=0` المؤجَّل — الجزء اللي أُصلح منه، فحص ملكية `group_id`، **اتأكَّد حيًا بالكامل**). بيانات throwaway (`saas_service_catalog id=59`, `saas_service_plans id=61`, `saas_tenant_service_access ids=3,4`, `saas_tenant_subscriptions ids=63,64`, بوستات/مجموعات/عقود/اتصالات/هدايا/خطط اشتراك تحت تينانت1/16 ببادئة `TEST_SOCIAL_`) **متروكة حاليًا بلا تنظيف** — بانتظار توجيهك (تنظيف الآن، أم بعد commit، أم تُترَك لإعادة استخدام مستقبلي زي بقية جلسات السويپ). **السيرفر التجريبي أُوقِف بالكامل** (تأكيد: منفذ 8000 فاضي).

**صفر commit حتى الآن — بانتظار موافقتك.**
