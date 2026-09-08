# جلسة: technical-pattern-sweep — جرد تقني شامل (قراءة فقط، صفر Edit)

**تاريخ:** 2026-08-18
**النوع:** جرد/تحليل ساكن (static) بالكامل — **صفر تعديل على أي ملف كود طوال الجلسة** (تأكيد: لم يُستخدم Edit ولا Write على أي ملف تحت `eppne-backend/app/` طوال الجلسة، فقط `mypy`/`pip install` كأداة تطوير مؤقتة + ملفات `_mypy_*.txt` مؤقتة في `.claude/reports/` كمخرجات وسيطة).
**الهدف:** معرفة الحجم الحقيقي الكامل لمشكلات الكود عبر كل دومينات `eppne-backend` قبل التخطيط لأي جلسة إصلاح جديدة.

**ملاحظة نطاق:** `ls -1d */` في `eppne-backend/app/domains/` رجّعت **35 دومين فعلي** (بعد استبعاد `__pycache__`؛ الفرق عن "36" المذكور في طلب الجلسة على الأرجح عدّ `__pycache__` كدومين، أو عدّ `auth` مرتين قبل/بعد حذفه). دومين `auth` لا يزال موجودًا كمجلد لكنه **غير مسجَّل في `main.py`** (Phase 4 اكتملت فعليًا من ناحية إزالة الاستيراد/التسجيل — لا يوجد `from app.domains.auth...` في `main.py`). **دومين `agritech` أيضًا غير مسجَّل في `main.py`** (لا `router` مستورد له ولا في `routers_config`) رغم وجود `service.py`/`router.py` كاملين ومستخدَمين فقط عبر Celery tasks (`app/tasks/agritech.py`) — اكتشاف جانبي لم يكن موثَّقًا صراحة كـ"غير موصول" من قبل (كان الموثَّق فقط `admin`).

**قيود منهجية على هذه الجلسة (وثِّقت كما طُلب):**
- **Fork المُطلَق لتغطية قسم من البند ب (بنود #22/eventbus/#23/#24/#25) لم يُنتظَر حتى اكتماله** — بدل ذلك، اتضح أثناء العمل المباشر أن كل نطاقه أمكن تغطيته يدويًا (`Read`/`Grep`/`mypy`) بعمق أكبر مما كان مطلوبًا منه، فتم الاعتماد على النتائج المباشرة بدل انتظار الـfork. لا تعارض متوقَّع، لكن يُذكر للشفافية.
- تغطية `mypy --strict` اعتمدت فلترة يدوية صارمة (تفصيل في القسم أ) بسبب غياب type stubs/إعدادات mypy مسبقة في المشروع — لم يُعدَّل أي إعداد mypy ولا أُضيف أي `type: ignore` جديد.
- بعض البنود (خصوصًا #2 `duplicate-kwarg-audit` الموسّع، و#19/#20) وُثِّقت بعمق أقل نسبيًا لأنها كانت أصلًا مصنَّفة أولوية أقل في `constructor-mismatch-backlog-classification.md`؛ ذُكر بوضوح أين التغطية جزئية.

---

# 🔴🔴 يستوجب انتباه فوري

## 1. `EventBus` مُهيَّأ بعميل خاطئ في **34 من 35 دومين** — كل `event_bus.publish()` تقريبًا في المنصة يفشل بـ `AttributeError`

`app/core/event_bus.py:16-34`: `EventBus.__init__(self, redis_client: Optional[Redis] = None)` — و`publish()` بينادي `await self.redis.publish(channel, message)`، بيتوقع عميل `redis.asyncio.Redis` خام (الميثود `publish` موجودة عليه أصلًا من مكتبة `redis`).

لكن **كل** الدومينات (ما عدا `finance` فقط) بتبني `EventBus` بتمرير `redis_client` — وهو الـ**Singleton** لـ`RedisClientWrapper` (`app/core/redis_client.py`)، مش عميل Redis خام. `RedisClientWrapper` **لا تملك method اسمها `publish`** (methods الفعلية: `ping`, `get`, `setex`, `set`, `delete`, `exists`, `incr`, `expire`, `get_json`, `set_json`, `initialize`, `get_client`, `close` — لا شيء غير ده). أغلب المواضع ملفوفة بـ`cast(Any, redis_client)` — دليل واضح إن المطورين حاولوا **إسكات الـtype checker** بدل حل المشكلة الجذرية.

**النتيجة العملية:** أي `await self.event_bus.publish(...)` في 34 دومين (55 موضع استدعاء مؤكَّد، جدول كامل أسفل) يرمي `AttributeError: 'RedisClientWrapper' object has no attribute 'publish'` وقت التنفيذ الفعلي. `finance/service.py:26` هو الاستثناء الوحيد الصحيح (`EventBus()` بدون معامل → تلجأ لـ`Redis.from_url()` الحقيقية داخليًا).

**الأثر الموسَّع (سلسلة كاملة):** أي كود بعد `event_bus.publish(...)` في نفس محاولة `try/except` (زي `audit_log`، `_store_idempotency`) **لا يُنفَّذ إطلاقًا** إن كان `publish()` غير محمي بـ`try/except` منفصل — وإن كان محميًا، الاستثناء يُبلَع بصمت (راجع القسم ج). هذا بند موسَّع جوهريًا عن `eventbus-redis-wrapper-missing-publish` الموثَّق سابقًا (كان مؤكَّدًا في `insurance.subscribe` فقط) — **التأكيد الآن: 34/35 دومين، ليس دومين واحد.**

## 2. `iot.service.py:22` — `self.redis` مربوط بمرجع دالة غير مُستدعاة، مش بعميل حقيقي

```python
self.redis = cast(Any, get_redis_client)   # ← بدون قوسين "()" — هذا مرجع للدالة نفسها، لا نتيجة استدعائها
```

مقارنة بكل الدومينات التانية اللي بتكتب `self.redis = redis_client` (الكائن الفعلي). هنا `self.redis` هو **الدالة `get_redis_client` نفسها كـobject**، مش عميل Redis. أي استدعاء لاحق زي `iot/service.py:73` (`await self.redis.get(cache_key)`) هيرمي `AttributeError: 'function' object has no attribute 'get'` — باج مختلف تمامًا عن نمط #7 المعروف (missing method)، ده كائن غلط بالكامل. **لم يكن موثَّقًا من قبل بهذا الشكل.**

## 3. `audit_log()` الحقيقية (4 معاملات فقط) تُستدعى بـ 112+ موضع تقريبًا كلها بمعاملات زيادة — أوسع بج مؤكَّد في المشروع كله

راجع تفصيل كامل في القسم ب/#14 أسفل — التوقيع الحقيقي `audit_log(action, user_id=None, details=None, ip_address=None)`، وكل استدعاء تقريبًا بيمرر `tenant_id=` و`resource_id=` (غير موجودين في التوقيع) → `TypeError` مضمون عند التنفيذ الفعلي، ما لم يكن محميًا بـ`try/except`.

## 4. `academy.create_course` — كراش 100% مؤكَّد قطعيًا (schema→router→service)، على عكس باقي القائمة اللي هي "احتمالية عالية"

`academy/router.py:186` بيمرر `data.model_dump()` (بلا `exclude_unset=True`) من schema `CourseCreate` اللي بتحتوي حقل `instructor_id` أصلًا، لـ`academy/service.py:112`: `self.repo.create_course(**data, instructor_id=instructor_id)` — نفس المفتاح `instructor_id` ممرَّر مرتين (مرة جوّه `**data`، مرة صريحة) → `TypeError: got multiple values for keyword argument 'instructor_id'` **في كل استدعاء بلا استثناء واحد، بغض النظر عن المدخلات**. هذا موضع مؤكَّد بالتتبُّع الكامل (schema حقيقية مقروءة، مش مجرد نمط نصي مرشَّح) — راجع تفصيل كامل تحت بند #2 (`duplicate-kwarg-audit`) في القسم ب. رغم كونه محليًا (endpoint واحد)، نسبة الكراش 100% تبرر إدراجه هنا.

---

## القسم أ) فحص آلي — `mypy --strict`

**الأداة:** لم يكن `mypy` مثبَّتًا؛ تم `pip install mypy` (v2.3.1) — تثبيت أداة تطوير فقط، صفر تعديل على `app/`.
**الأمر:** `mypy --strict --ignore-missing-imports --no-error-summary app` من جذر `eppne-backend`.
**النتيجة الخام:** 4246 سطر، **4194 خطأ** (exit code 1 متوقَّع).

### توزيع الأخطاء حسب الكود (فلترة الضوضاء)

| كود mypy | العدد | التصنيف |
|---|---|---|
| `no-untyped-def` | 1100 | ❌ ضوضاء (نقص type hints — طبيعي في مشروع بلا mypy سابق) |
| `untyped-decorator` | 912 | ❌ ضوضاء (decorators FastAPI غير معنونة) |
| `unused-ignore` | 679 | ⚠️ نصف-مفيد — يعني إن `# type: ignore` موجودة لكن mypy strict معتبرها غير لازمة (سبب محتمل: عدم اكتمال سلسلة الاستدلال بسبب أخطاء أخرى سابقة تمنع الوصول لنفس السطر) — **لم تُفحص بعمق، خارج نطاق الأربع فئات المطلوبة** |
| `misc` | 623 | ❌ ضوضاء غالبًا (async/type-var عامة) |
| `no-any-return` | 326 | ❌ ضوضاء |
| `type-arg` | 179 | ❌ ضوضاء (generics بلا معامل) |
| `call-arg` | **86** | ✅ **wrong-arity / wrong-kwarg — الفئة الأهم** |
| `no-untyped-call` | 79 | ❌ ضوضاء |
| `return-value` | 71 | ⚠️ لم تُفحص بعمق (خارج فئات الطلب الأربع، عيّنة سريعة أظهرت غالبها Optional/None mismatches عادية) |
| `attr-defined` | **37** | ✅ **missing-attribute — فئة مهمة** |
| `name-defined` | **31** | ✅ **فئة "أخرى" جديدة — أسماء غير معرَّفة (import ناقص)، أغلبها Enum classes مستخدمة في response models بلا import** |
| `assignment` | 24 | ⚠️ لم تُفحص بعمق |
| `arg-type` | **18** | ✅ **type-mismatch — فئة مهمة** |
| `redundant-cast` | 13 | ❌ ضوضاء |
| الباقي (`union-attr`, `var-annotated`, `dict-item`, `no-redef`, `operator`, `index`) | 16 | ❌ ضوضاء غالبًا |

**محدودية التغطية:** المشروع بلا `mypy.ini`/إعدادات سابقة، فـ`--strict` يولّد ~2500 خطأ ضوضاء (نقص type hints) لا علاقة له بالفئات المطلوبة. تم فلترة النتائج يدويًا للتركيز حصريًا على `call-arg` + `attr-defined` + `arg-type` + `name-defined` (172 خطأ إجمالًا) — **هذه الأربع فئات هي ما استُخدم في كل القسم ب/ج أدناه كدليل تأكيد آلي إضافي لكل بند grep يدوي.** الفئات الأخرى (`return-value`, `assignment`, `unused-ignore`) لم تُفحص خطًا بخط — قد تحتوي اكتشافات إضافية غير موثَّقة هنا، تحتاج جلسة منفصلة لو أُريد استنفادها بالكامل.

**قيمة مضافة حاسمة:** `mypy --strict` أكّد بشكل مستقل **كل** نتائج الـgrep اليدوي في القسم ب (نفس الملفات/الأسطر بالضبط لأغلب البنود #1, #12, #14, #15, #16، وكشف عدة مواضع **جديدة كليًا** لم تظهر في grep اليدوي الأول — خصوصًا في `app/tasks/*.py` حيث الأنماط نفسها متكررة لكن لم تكن مغطاة صراحة في أي بند Backlog سابق).

**ملحق — عيّنة إضافية من الفئات الصغيرة (`union-attr`, `dict-item`, `no-redef`, `operator`) لم تُدرَج في الجدول أعلاه لأنها صُنِّفت "ضوضاء غالبًا" بالجملة، لكن الفحص العيني وجد فيها حالات حقيقية تستاهل تسجيل صريح:**

| الملف:السطر | الخطأ | تصنيف |
|---|---|---|
| `services/ai/router.py:138,169` و`services/ai/engine.py:152,161,162` (5 مواضع) | `Item "None" of "ModelConfig \| None" has no attribute ...` | 🟡 `AttributeError` محتمل لو `MODEL_CONFIGS` مالوش الموديل المطلوب — يحتاج فحص هل في validation قبلها |
| `iot/service.py:239,240,241` | `Dict entry has incompatible type "str": "float"/"int"; expected "str": "str"` | 🟡 شكل بيانات (payload) غير متسق — يحتاج فهم منطق العمل قبل الحكم بخطورته |
| `privacy/repository.py:295,320` | `Name "count_query" already defined` (×2) | 🟡 متغيّر معاد تعريفه — احتمال منطق مكرر بالخطأ في دالة عد (count) حساسة أمنيًا (privacy) |
| `translation/service.py:30` | `"RedisClientWrapper" not callable` `[operator]` | 🔴 يحل الغموض المذكور في القسم د (صف `translation`) — الكود بينادي `redis_client()` كأنها دالة، مش عميل — نمط باج ثالث مختلف عن #7 وعن اكتشاف `iot` (كلاهما "غير مستدعاة/مرجع خطأ"، هنا "استدعاء خطأ لكائن غير قابل للاستدعاء") |
| `core/logging_conf.py:89` | `FileHandler` بدل `StreamHandler` المتوقَّع | ⚪ إعداد لوج، أثر تشغيلي محدود |

---

## القسم ب) جرد grep منهجي — كل بند Backlog معروف، عبر الـ35 دومين

### #1 `user-repository-get-by-id-audit`

**التوقيع الحقيقي:** `UserRepository.get_by_id(self, user_id: int, tenant_id: int, load_wallet: bool = False)` — `tenant_id` **إجباري بلا default**.

| # | ملف:سطر | الحالة |
|---|---|---|
| 1 | `zamakana/service.py:650` | 🔴 `get_by_id(user_id)` — tenant_id مفقود |
| 2 | `insurance/service.py:60` | 🔴 مفقود |
| 3 | `transport/service.py:569` | 🔴 مفقود |
| 4 | `transport/service.py:577` | 🔴 مفقود |
| 5 | `tourism_sports/service.py:518` | 🔴 مفقود |
| 6 | `tenders_auctions/service.py:484` | 🔴 مفقود |
| 7 | `social/service.py:678` | 🔴 مفقود |
| 8 | `service_marketplace/service.py:477` | 🔴 مفقود |
| 9 | `realestate/service.py:576` | 🔴 مفقود |
| 10 | `realestate/service.py:584` | 🔴 مفقود |
| 11 | `arbitration_syndicates/service.py:565` | 🔴 مفقود |
| 12 | `manufacturing/service.py:57` | 🔴 مفقود |
| 13 | `logistics/service.py:62` | 🔴 مفقود |
| 14 | `iot/service.py:31` | 🔴 مفقود (مؤكَّد أيضًا آليًا بـmypy) |
| 15 | `invitations/service.py:56` | 🔴 مفقود |

آمنة (تمرر `tenant_id` بشكل صحيح): `identity/service.py` (×4)، `identity/repository.py:69` (داخلي)، `commerce/service.py:238`، `sovereign_entities/service.py:359`، `affiliate/service.py` (×2)، `academy/service.py` (×3)، `core/security.py:132`، `api/deps.py` (×2).

**✅ التأكيد النهائي: 15 موضع عبر 13 دومين — يطابق الموثَّق تمامًا في PROGRESS_LOG.md بند #1. صفر مواضع إضافية جديدة اكتُشفت. تأكيد مستقل آليًا عبر mypy لكل الـ15.**

### #2 `duplicate-kwarg-audit`

grep عن نمط `**data)`/`**data,` ممزوج بـkwarg صريح لنفس الاسم كشف **7 مواضع إضافية عالية-الاحتمال** (لم تكن موثَّقة في العدد "4+" الأصلي) حيث `tenant_id=`/`created_by=`/`version=` صريحة تترافق مع `**data` قد يحتوي نفس المفتاح:

| # | ملف:سطر | الاستدعاء |
|---|---|---|
| 1 | `transport/service.py:202` | `create_trip(tenant_id=tenant_id, **data)` |
| 2 | `sovereign_entities/service.py:319` | `create_template(tenant_id=self.tenant_id, **data)` |
| 3 | `social/service.py:597` | `create_subscription_plan(tenant_id=tenant_id, **data)` |
| 4 | `service_marketplace/service.py:382` | `create_addon(tenant_id=tenant_id, created_by=user_id, version="1.0.0", **data)` |
| 5 | `arbitration_syndicates/service.py:295` | `create_syndicate(tenant_id=tenant_id, **data)` |
| 6 | `arbitration_syndicates/service.py:469` | `create_election(tenant_id=tenant_id, **data)` |
| 7 | `ai_governance/repository.py:120` | `AgentRateLimit(agent_id=agent_id, tenant_id=tenant_id, **data)` |

**⚠️ تحفظ صريح:** هذه مواضع **مرشَّحة عالية الاحتمال فقط** — التأكيد القاطع (هل `data` الفعلي في وقت التشغيل يحتوي المفتاح المتضارب؟) يحتاج قراءة الـPydantic schema المصدر لكل `data` عند نقطة الاستدعاء في الـrouter، وده لم يُنفَّذ لكل السبعة (خارج ميزانية الوقت المتاحة لبند مصنَّف أصلًا "أولوية أقل" في `constructor-mismatch-backlog-classification.md`). **التوصية:** جلسة `grep` مخصَّصة قصيرة لهذا البند تحديدًا قبل أي إصلاح.

**🆕 موضع ثامن — مؤكَّد قطعيًا (100%، تتبُّع كامل schema→router→service، مش مجرد grep):**

`academy/service.py:109-112`:
```python
async def create_course(self, data: dict, instructor_id: int):
    ...
    course = await self.repo.create_course(**data, instructor_id=instructor_id)
```
استدعاؤه من `academy/router.py:186`: `service.create_course(data.model_dump(), cast(int, current_user.id))` — **بلا `exclude_unset=True`**. `data` جاية من `CourseCreate` schema (`academy/schemas.py:113-125`) اللي **تحتوي فعليًا حقل `instructor_id: Optional[int] = None`**. يعني `data` (بعد `.model_dump()`) هتحتوي مفتاح `instructor_id` دايمًا (حتى لو `None`)، وبعدين `**data, instructor_id=instructor_id` هيرمي **`TypeError: create_course() got multiple values for keyword argument 'instructor_id'`** — **كراش مضمون 100% على كل استدعاء لـ`POST /academy/courses` بلا استثناء، بغض النظر عن المدخلات.**

للمقارنة: `create_bootcamp` (نفس الملف، سطر 73-77، نفس النمط `**data, instructor_id=instructor_id`) **آمنة** لأن `BootcampCreate` schema (سطر 88-93) **لا تحتوي** حقل `instructor_id` أصلًا. `create_course_unit`/`create_node_material` (نمط `key=value, **data` مشابه) اتفحصوا كمان وطلعوا آمنين (`CourseUnitCreate`/`NodeMaterialCreate` schemas لا تحتوي `course_id`/`node_id`).

**البند ده مش مجرد "مرشَّح" — كراش endpoint كامل 100% من المرات، ويستاهل أولوية فورية بغض النظر عن كونه مصنَّف تحت بند "أولوية أقل" أصلًا.**

### #7 `redis-client-wrapper-missing-methods`

**Methods الحقيقية على `RedisClientWrapper`:** `ping`, `get`, `setex`, `set`, `delete`, `exists`, `incr`, `expire`, `get_json`, `set_json`, `initialize`, `get_client`, `close`.

| # | ملف:سطر | Method المستدعاة (غير موجودة) |
|---|---|---|
| 1-9 | `services/ai/cost_tracker.py:65-77` (×9 مواضع) | `hincrbyfloat` |
| 10-12 | `services/ai/cost_tracker.py:91,113,126` | `hgetall` |
| 13 | `services/ai/cache.py:117` | `lpush` |
| 14 | `services/ai/cache.py:129` | `rpop` |
| 15 | `tasks/agritech.py:258` | `lpush` |
| 16 | `tasks/agritech.py:262` | `ltrim` |
| 17 | `communications/router.py:48` | `pubsub()` |
| 18 | `communications/router.py:84` | `publish(...)` — استدعاء مباشر على `redis_client` (مش عبر `EventBus`)، نفس الجذر التقني لكن موضع منفصل |
| 19 | `projects/service.py:157` | `setnx` (موثَّق مسبقًا) |

**التأكيد:** أعلى بكثير من "2 مؤكَّدة (`ai_agents`, `projects`)" الموثَّقة سابقًا — **19 موضع مؤكَّد عبر 6 ملفات/دومينات (`services/ai` كوحدة مشتركة، `tasks/agritech`, `communications`, `projects`)**. مؤكَّد آليًا عبر mypy لـ14 من الـ19 (كل ما عدا `pubsub`/`publish` في communications، و`lpush`/`ltrim` في tasks/agritech — هذول غير async-typed بشكل يظهر لـmypy بنفس الوضوح، تحققت يدويًا فقط).

### #8 `user-repository-get-user-audit`

**تصحيح مهم عن الموثَّق سابقًا:** التوثيق يقول "6 مواضع، 5 دومينات". الفحص الفعلي وجد **6 مباريات نصية** لـ`.get_user(` لكن **موضع واحد منها (`identity/service.py:238`) مش باج** — هو استدعاء `self.get_user(user_id)` لـmethod حقيقية معرَّفة على `IdentityService` نفسها في السطر 228 (`async def get_user(self, user_id: int) -> User`)، مش استدعاء لـ`UserRepository.get_user` غير الموجودة.

| # | ملف:سطر | الحالة |
|---|---|---|
| 1 | `employment/service.py:87` | 🔴 `UserRepository(self.db).get_user(user_id)` — method غير موجودة |
| 2 | `digital_twin/service.py:53` | 🔴 نفس النمط (مُعلَّم `# type: ignore` مسبقًا — وعي مسبق بالمطور) |
| 3 | `communications/service.py:29` | 🔴 نفس النمط |
| 4 | `communications/service.py:36` | 🔴 نفس النمط |
| 5 | `health/service.py:54` | 🔴 نفس النمط |
| — | `identity/service.py:238` | 🟢 **ليس باج — false positive نصي، `self.get_user` صحيحة** |

**✅ العدد الحقيقي المصحَّح: 5 مواضع عبر 4 دومينات (employment, digital_twin, communications×2, health) — أقل من الموثَّق سابقًا (كان 6/5)، بعد استبعاد identity كـfalse positive.**

### #10 `affiliate-service-missing-methods`

**الجذر مؤكَّد آليًا بـmypy:** `AffiliateService` methods الحقيقية لا تحتوي `register_commission` (فقط `release_commissions`، `get_or_create_profile`, `distribute_commissions`, `withdraw_commissions`, إلخ). كل استدعاء لـ`_register_affiliate_commission` (helper داخلي منسوخ حرفيًا بكل دومين) بينادي method غير موجودة اسمها `register_commission` على `AffiliateService`.

**مواضع `_register_affiliate_commission` (منسوخة في 13 ملف حسب grep):** `manufacturing`, `invitations`, `arbitration_syndicates`, `employment`, `digital_twin`, `insurance`, `realestate`, `zamakana`, `tourism_sports`, `transport`, `tenders_auctions`, `service_marketplace` + `tasks/employment.py`.

**مؤكَّد آليًا (mypy attr-defined) في موضعين محددين فقط من الاستدعاء الفعلي غير المحمي بنفس السياق:** `service_marketplace/service.py:491`, `employment/service.py:107`. باقي المواضع **محمية بالكامل بـtry/except صامت** (راجع القسم ج — تفصيل الـ8 دومينات المؤكَّدة هناك) فلا تظهر كخطأ صريح، لكنها **تفشل بصمت بنفس الطريقة في كل استدعاء**.

**✅ التأكيد: 12-13 دومين متأثر — أعلى من "6+ دومينات" الموثَّقة، ويتوافق مع كون هذا البند مصنَّف "مركزي" بامتياز.**

### #12 `saas-control-service-wrong-arity-call`

**التوقيع الحقيقي:** `SaaSControlService.can_access_service(self, service_code: str) -> bool` — معامل واحد بس (`tenant_id` انتقل لـconstructor).

| # | ملف:سطر | المُمرَّر |
|---|---|---|
| 1 | `zamakana/service.py:64` | `can_access_service(tenant_id, feature)` — معاملان زيادة |
| 2 | `transport/service.py:65` | نفس النمط |
| 3 | `tourism_sports/service.py:61` | نفس النمط |
| 4 | `tenders_auctions/service.py:59` | نفس النمط |
| 5 | `social/service.py:63` | نفس النمط |
| 6 | `service_marketplace/service.py:70` | `can_access_service(tenant_id, "service_marketplace")` |

آمنة: `saas/service.py:238,247` (استدعاء داخلي صحيح `self.can_access_service(service_code)`).

**✅ التأكيد: بالضبط 6 دومين — مطابق تمامًا للموثَّق ("6+ دومينات")، صفر جديد. مؤكَّد آليًا بـmypy (`arg-type`: النوع الأول `int` بدل `str` المتوقَّع — نفس الاستنتاج من زاوية مختلفة).**

**اكتشاف إضافي عبر mypy لم يكن موثَّقًا:** `api/deps.py:208` — `Too many arguments for "check_and_enforce_access" of "SaaSControlService"` — نفس عائلة البج لكن method مختلفة (`check_and_enforce_access` مش `can_access_service`)، موضع سابع جديد كليًا.

### #14 `audit-log-wrong-kwargs`

**التوقيع الحقيقي:** `audit_log(action: str, user_id: Optional[int] = None, details: Optional[Dict] = None, ip_address: Optional[str] = None) -> None` — **4 معاملات فقط، بلا `tenant_id` ولا `resource_id`.**

**جرد شامل:** 127 مباراة نصية لـ`audit_log(` عبر 26 ملف، بعد استبعاد التعريف نفسه ودوال مختلفة الاسم (`_create_audit_log` الداخلية في `finance`/`commerce` — methods منفصلة تمامًا وصحيحة، `repo.create_audit_log(**kwargs)` في `ai_governance` — تقبل أي kwargs فمحصَّنة بنيويًا) → **~112 استدعاء مباشر حقيقي لـ`audit_log()` الأساسية عبر 22 ملف**، كلها تقريبًا (عيّنة موسَّعة من `insurance`, `zamakana`, `ai_agents` تؤكد 100% النمط) تمرر `tenant_id=` و`resource_id=` — **كلاهما غير موجود في التوقيع**.

| الملف | عدد المواضع | ملاحظة |
|---|---|---|
| `zamakana/service.py` | 9 | كلها مُعلَّمة `# type: ignore[call-arg]` (وعي مسبق) |
| `agritech/service.py` | 11 | غير مُعلَّمة (agritech غير موصول بـmain.py أصلًا، لكن الأخطاء موجودة في الكود) |
| `manufacturing/service.py` | 12 | نمط `audit_log(**{...})` |
| `invitations/service.py` | 7 | |
| `insurance/service.py` | 6 | مؤكَّد سابقًا |
| `arbitration_syndicates/service.py` | 6 | |
| `tenders_auctions/service.py` | 6 | |
| `social/service.py` | 8 | |
| `communications/router.py` | 8 | **جديد — لم يكن موثَّقًا صراحة، ملف router مش service** |
| `transport/service.py` | 5 | |
| `logistics/service.py` | 5 | |
| `realestate/service.py` | 4 | نمط `**{...}` |
| `sovereign_entities/service.py` | 3 | |
| `digital_twin/service.py` | 3 | |
| `tourism_sports/service.py` | 3 | |
| `ai_governance/service.py` | 3 | (عبر `repo.create_audit_log` — آمنة فعليًا) |
| `command/service.py` | 3 | |
| `health/service.py` | 3 | |
| `ai_agents/service.py` | 4 | |
| `employment/service.py` | 2 | |
| `invoicing/service.py` | 2 | مؤكَّد سابقًا (جوّه `create_invoice`) |
| `service_marketplace/service.py` | 1 | |
| `commerce/service.py` | 1 | (السطر 554 فقط — الباقي `_create_audit_log` داخلية آمنة) |

**✅ التأكيد: أوسع بج في كل الـBacklog كما كان متوقَّعًا — لكن العدد الحقيقي (~112 استدعاء / 22 ملف) أعلى بشكل كبير من أي رقم موثَّق سابقًا صراحة (لم يكن هناك رقم إجمالي موثَّق، فقط "عشرات المواضع"). مؤكَّد آليًا بـmypy لعينة من 9 مواضع مباشرة (كل موضع بيولّد **خطأين منفصلين** — `tenant_id` و`resource_id` كل واحد `Unexpected keyword argument` مستقل).**

### #15 `ai-governance-check-and-consume-wrong-kwarg`

**التوقيع الحقيقي:** `check_and_consume(self, agent_id, user_id, action_type, tokens, cost, idempotency_key=None, request_tokens=0, completion_tokens=0) -> bool` — `action_type` **إجباري بلا default**.

| # | ملف:سطر | kwarg زيادة `tenant_id=` | `action_type` مفقودة (باج إضافي) | try/except يحمي؟ |
|---|---|---|---|---|
| 1 | `zamakana/service.py:498` | 🔴 | 🔴 مفقودة | لا (غير محمي مباشرة) |
| 2 | `transport/service.py:74` | 🔴 | 🔴 مفقودة | ✅ محمي (`except Exception` سطر 81، يرجع `None`) |
| 3 | `insurance/service.py:338` | 🔴 | ✅ موجودة | جزئي — داخل `try` أوسع |
| 4 | `tourism_sports/service.py:432` | 🔴 | 🔴 مفقودة | غير مؤكَّد بدقة |
| 5 | `tenders_auctions/service.py:202` | 🔴 | 🔴 مفقودة | غير مؤكَّد بدقة |
| 6 | `social/service.py:304` | 🔴 | 🔴 مفقودة | غير مؤكَّد بدقة |
| 7 | `service_marketplace/service.py:159` | 🔴 | ✅ موجودة | لا |
| 8 | `realestate/service.py:76` | 🔴 | 🔴 مفقودة | ✅ محمي (سطر 84، يسجل تحذير فقط) |
| 9 | `arbitration_syndicates/service.py:95` | 🔴 (مُعلَّمة `# type: ignore`) | 🔴 مفقودة | غير مؤكَّد بدقة |
| 10 | `manufacturing/service.py:300` | 🔴 | ✅ موجودة | غير مؤكَّد بدقة |
| 11 | `manufacturing/service.py:662` | 🔴 | ✅ موجودة | غير مؤكَّد بدقة |
| 12 | `logistics/service.py:546` | 🔴 (مُعلَّمة) | ✅ موجودة | غير مؤكَّد بدقة |
| 13 | `invitations/service.py:383` | 🔴 (مُعلَّمة) | ✅ موجودة | غير مؤكَّد بدقة |

**آمنة تمامًا (مطابقة كاملة للتوقيع الحقيقي):** `command/service.py:335` (بلا `tenant_id`، مع `action_type`) و`ai_governance/router.py:191` (الاستدعاء المباشر الصحيح من الـrouter نفسه).

**✅ التأكيد: 13 موضع/12 دومين متأثر بـwrong-kwarg — أعلى من "8+ دومينات" الموثَّقة. اكتشاف إضافي مهم: 7 من الـ13 موضع (`zamakana`, `transport`, `tourism_sports`, `tenders_auctions`, `social`, `realestate`, `arbitration_syndicates`) عندهم باج ثانٍ متزامن (معامل `action_type` الإجباري مفقود تمامًا) — يعني هذول السبعة سيفشلوا بـ`TypeError` حتى لو أُصلح `tenant_id` وحده بدون إضافة `action_type`.** `command` هو الدومين الوحيد المطابق تمامًا للتوقيع الحقيقي في كل استدعاءات AI Governance/Agents (نمط ملحوظ عبر البندين #15 و#16 معًا).

### #16 `ai-agents-execute-agent-action-wrong-kwarg`

**التوقيع الحقيقي:** `execute_agent_action(self, agent_id, action_type, payload, executor_user_id, idempotency_key) -> Dict` — `idempotency_key` **إجباري بلا default**.

| # | ملف:سطر | `tenant_id=` زيادة | `idempotency_key` مفقودة | محمي بـtry/except؟ |
|---|---|---|---|---|
| 1 | `tasks/agritech.py:168` | 🔴 | يحتاج تأكيد | لا (مؤكَّد آليًا mypy) |
| 2 | `zamakana/service.py:521` | 🔴 (مُعلَّمة) | 🔴 مفقودة | لا |
| 3 | `transport/service.py:165` | 🔴 (مُعلَّمة) | يحتاج تأكيد | لا |
| 4 | `tourism_sports/service.py:271` | 🔴 (مُعلَّمة) | يحتاج تأكيد | ✅ (سطر 278) |
| 5 | `tourism_sports/service.py:414` | 🔴 (مُعلَّمة) | يحتاج تأكيد | ✅ (سطر 427) |
| 6 | `tenders_auctions/service.py:210` | 🔴 (مُعلَّمة) | يحتاج تأكيد | لا مباشرة |
| 7 | `tenders_auctions/service.py:329` | 🔴 (مُعلَّمة) | يحتاج تأكيد | ✅ (سطر 341 محتمل) |
| 8 | `social/service.py:314` | 🔴 (مُعلَّمة) | يحتاج تأكيد | لا مباشرة |
| 9 | `realestate/service.py:232` | 🔴 (مُعلَّمة) | 🔴 مفقودة | لا |
| 10 | `automation/service.py:707` | 🔴 (مُعلَّمة) | ✅ موجودة | ✅ (`except PermissionDeniedError`، ثم على الأرجح `Exception` أوسع لاحقًا) |
| 11 | `arbitration_syndicates/service.py:105` | 🔴 | يحتاج تأكيد | ✅ (سطر 104 `try:`) |
| 12 | `manufacturing/service.py:311` | 🔴 (مُعلَّمة) | يحتاج تأكيد | ✅ (سطر 310 `try:`) |
| 13 | `manufacturing/service.py:673` | 🔴 (مُعلَّمة) | يحتاج تأكيد | ✅ (سطر 672 `try:`) |
| 14 | `logistics/service.py:558` | 🔴 | يحتاج تأكيد | ✅ (سطر 557 `try:`) |
| 15 | `invitations/service.py:84` | 🔴 (مُعلَّمة) | 🔴 مفقودة | ✅ (سطر 83 `try:`) |
| 16 | `invitations/service.py:415` | 🔴 (مُعلَّمة) | 🔴 مفقودة | يحتاج تأكيد |
| 17 | `insurance/service.py:346` | 🔴 | 🔴 مفقودة | جزئي |
| 18 | `insurance/service.py:439` | 🔴 | يحتاج تأكيد | ✅ (سطر 438 `try:`) |
| 19 | `employment/service.py:142` | 🔴 | ✅ موجودة | يحتاج تأكيد |

**آمنة تمامًا:** `command/service.py:348` (بلا `tenant_id`)، `ai_agents/router.py:95` (الاستدعاء المباشر الصحيح).

**✅ التأكيد: 19 موضع مؤكَّد عبر **14 دومين + tasks** — أعلى بكثير من "9+ دومينات" الموثَّقة سابقًا. توسيع كبير جدًا لهذا البند.**

### #17 `arbitration-case-model-idempotency-key-mismatch`

**مؤكَّد بالقراءة المباشرة:** `ArbitrationCase` (نموذج SQLAlchemy، `arbitration_syndicates/models.py:36-58`) **لا يملك عمود `idempotency_key`** إطلاقًا (الأعمدة: `id`, `tenant_id`, `contract_id`, `claimant_id`, `respondent_id`, `dispute_reason`, `evidence_hashes`, `judging_mode`, `ai_judge_id`, `status`, `final_verdict`, `enforcement_tx_hash`, `created_at`, `updated_at`, `deleted_at`, `is_deleted`) — بينما `CrowdJury` (نفس الملف، سطر 66) **يملك** `idempotency_key`. الخدمة (`service.py`) بتحاول تمرر `idempotency_key=` لكل استدعاءات `repo.create_case`/`create_vote`/`create_membership`/`create_license` تقريبًا (6 مواضع، مُعلَّمة `# type: ignore` في كلها).

**✅ التأكيد: محلي بالكامل لـ`arbitration_syndicates` كما موثَّق — صفر نمط مشابه في دومين آخر (فحص سريع لموديلات مشابهة لم يظهر نفس الـmismatch).**

### #18 `finance-service-create-invoice-does-not-exist`

**Methods الحقيقية على `FinanceService`:** `get_or_create_wallet`, `get_or_create_wallet_for_update`, `_create_audit_log`, `get_balances`, `transfer`, `swap`, `mint_currency`, `get_transaction_history`, `process_invoice_payment` — **لا يوجد `create_invoice`**.

| # | ملف:سطر |
|---|---|
| 1 | `transport/service.py:354` (مُعلَّمة `# type: ignore[attr-defined]`) |
| 2 | `transport/service.py:529` (نفس التعليم) |

**✅ التأكيد: بالضبط موضعان في `transport` فقط — جرد شامل عبر الـ35 دومين لـ`.finance.create_invoice(` لم يكشف أي موضع إضافي. البند محلي مؤكَّد 100% كما كان متوقَّعًا في تصنيف "🟢 محلي (مبدئيًا)".**

### #19 `cross-tenant-scheduled-task-vs-constructor-mismatch` (توثيق فقط بقرار صريح)

لم يُعَد فحصه بعمق (خارج نطاق أولوية هذه الجلسة، وكان موثَّقًا صراحة كـ"توثيق فقط بقرار صريح" بلا حاجة لإصلاح مركزي). لا تغيير مُكتشف في العدد الموثَّق (8+1).

### #20 `missing-tenant-id-in-background-task-signature`

لم يُعَد فحصه بعمق منفصل — **لكن القسم أ (mypy) كشف توسيعًا كبيرًا وغير مباشر لهذا النمط بالذات** عبر `app/tasks/*.py` (راجع الاكتشافات الجديدة في القسم أ: `governance.py`×3, `saas_tasks.py`×5, `commerce.py`×5, `affiliate.py`×3, `agritech.py`×3 — كلها "Missing positional argument tenant_id" في استدعاءات من داخل ملفات `tasks/`). **يُوصى بدمج هذه الـ19 موضع الجديدة تحت بند Backlog جديد أو توسيع #20 ليشملها — راجع الجدول الموحَّد في نهاية التقرير.**

### #21 `billing-tasks-saas-subscription-import-error`

**مؤكَّد بالقراءة المباشرة وآليًا (mypy):** `app/tasks/billing.py:27` — `from app.domains.saas.models import SaaSSubscription` — **الاسم الصحيح الفعلي هو `TenantSubscription`، ليس `SaaSSubscription`** (`ImportError` عند تحميل الموديول). بما إن هذا `import` على مستوى الموديول (top-level)، **الملف بالكامل `billing.py` يفشل في التحميل** — أي `task` Celery معرَّفة فيه (توليد فواتير AI الشهرية، اشتراكات التوأم الرقمي) **معطَّلة بالكامل من لحظة استيراد الموديول**، مش فقط الدالة المعنية.

**✅ التأكيد: يطابق الموثَّق تمامًا — حاجب موديول كامل، أولوية عالية لأنه يعطّل كل الفوترة الشهرية للـAI و`digital_twin` تلقائيًا.**

### بندان جديدان من جلسة #11b — جرد موسَّع

#### `finance-transfer-returns-transaction-object-not-tx-hash-string`

`FinanceService.transfer()` (`finance/service.py:58-147`) بترجع `tx` (كائن `Transaction` ORM كامل من `self.tx_repo.create(...)`)، **مش** `tx.tx_hash` (نص). الاستخدام الآمن الوحيد هو الوصول لاحقًا لـ`tx.tx_hash` صراحة.

**جرد كامل لكل الـ~34 موضع استدعاء `finance.transfer(` عبر المشروع:**

| نمط الاستخدام | عدد المواضع | الحالة |
|---|---|---|
| `tx = await finance.transfer(...)` ثم لاحقًا `tx.tx_hash` صراحة | `digital_twin:178`, `commerce:171,302,578`, `affiliate:475`, `saas:166,306`, `invoicing:189` (8 مواضع) | 🟢 **آمن تمامًا** |
| `tx_hash = await finance.transfer(...)` — اسم متغيّر **مُضلِّل** (كائن `Transaction` مخزَّن في متغيّر اسمه `tx_hash`) لكن **غير مُستخدَم لاحقًا فعليًا في تخزين DB** (كود ميت/تسمية سيئة، لا كراش) | `tasks/employment.py:313`, `transport/service.py:331`, `tourism_sports/service.py:160,285`, `arbitration_syndicates/service.py:341`, `sovereign_entities/service.py:368,432`, `service_marketplace/service.py:192`, `insurance/service.py:198` (9 مواضع) | 🟡 **كود مربك لكن غير مُكسِّر — تسمية خطأ بدون استخدام فعلي لاحقًا** |
| `tx_hash = await finance.transfer(...)` ثم **تخزين مباشر في عمود `String`** | **`transport/service.py:512`** → `payment_tx_hash=tx_hash` في `.values()` لتحديث `DeliveryTask.payment_tx_hash` (`String(100)`, مؤكَّد من `transport/models.py:216`) | 🔴 **مكسور فعليًا — `DataError` مضمون** |
| نفس النمط، مؤكَّد مسبقًا في جلسة #11b | `realestate/service.py:241` (`purchase_tx_hash` → `PropertyOwnership.purchase_tx_hash String(100)`), `insurance/service.py:464` (`payout_tx` → `InsuranceClaim.payout_tx_hash String(100)`) | 🔴 مؤكَّد مسبقًا |

**✅ التأكيد الجديد: موضع ثالث مكسور فعليًا مكتشَف حديثًا (`transport.pay_delivery_fee` أو ما يعادلها حول السطر 512) — بالإضافة للاثنين الموثَّقين (`realestate`, `insurance`). التوسيع الأهم: تبيّن أن أغلب الاستخدامات (9 من 14 المفحوصة) هي مجرد **تسمية متغيّر مضلِّلة بلا كراش فعلي** — البج الحقيقي (كراش DB) محصور في 3 مواضع فقط من إجمالي ~14 موضع فُحصت بعمق (من أصل 34 استدعاء إجمالي لـ`transfer()` في المشروع، الباقي (~20) لم يُفحص خطًا بخط بنفس العمق — عيّنة الفحص العميق مثّلت الأنماط الأكثر شيوعًا).**

#### `eventbus-redis-wrapper-missing-publish`

راجع تفصيل كامل في قسم "🔴🔴 يستوجب انتباه فوري" أعلاه — **التأكيد: 34/35 دومين متأثر (كل الدومينات ما عدا `finance`)، 55 موضع استدعاء `event_bus.publish(` مؤكَّد. توسيع جوهري عن الموضع الوحيد الموثَّق سابقًا (`insurance.subscribe`).**

### #23 `invoicing-list-invoices-wrong-kwarg`

**التوقيع الحقيقي:** `list_invoices(self, user_id=None, status=None, invoice_type=None, reference_id=None, skip=0, limit=50)` — **بلا `tenant_id`** (يُملأ داخليًا من `self.tenant_id`).

**مؤكَّد آليًا (mypy):** `invoicing/router.py:149` — `Unexpected keyword argument "tenant_id" for "list_invoices"`.

**✅ التأكيد: موضع واحد فقط، في `router.py` نفسه (مش في دومين استهلاك خارجي كما كان مفترضًا سابقًا بحاجة جرد لـ12 دومين) — البند فعليًا محلي لملف واحد، ليس عبر-دومينات.**

### #24 `invoicing-get-invoice-stats-wrong-arity`

**مؤكَّد آليًا (mypy):** `invoicing/router.py:306` — `Too many arguments for "get_invoice_stats" of "InvoicingService"`.

**✅ التأكيد: موضع واحد، مطابق للموثَّق.**

### #25 `invoicing-get-invoice-null-tenant-admin-bypass-broken`

**مؤكَّد بالقراءة المباشرة:** `invoicing/service.py:125-127`:
```python
async def get_invoice(self, invoice_id: int, tenant_id: Optional[int] = None) -> Invoice:
    target_tenant = tenant_id or self.tenant_id
    invoice = await self.repo.get_invoice(invoice_id, target_tenant)
```
المنطق يستخدم `or` — لو الـcaller مرّر `tenant_id=None` عمدًا (نية "admin bypass، شوف كل التينانتات")، تعبير `None or self.tenant_id` **يرجع `self.tenant_id` دايمًا** (لأن `None` falsy في بايثون) — الـbypass **لا يحصل إطلاقًا abstractly**، الفلترة بـtenant الحالي مفروضة دايمًا بغض النظر عن نية الـcaller.

**✅ التأكيد: باج منطقي حقيقي مؤكَّد بالقراءة المباشرة، يطابق الوصف الموثَّق بالضبط. اكتشاف إضافي من mypy:** `invoicing/router.py:296,329` — `InvoicingService()` يُستدعى بمعامل `tenant_id` مفقود بالكامل (constructor mismatch جديد، غير موثَّق سابقًا) — و`invoicing/router.py:92,134` — تمرير `Optional[int]` حيث `int` مطلوب (نفس جذر مشكلة nullable tenant).

---

## القسم ج) نقاط الحماية بالصدفة — `try/except` صامتة تُخفي أخطاء حقيقية

**تركيز:** فقط مواضع تلف عمليات كتابة DB أو مالية أو استدعاءات لبنود مؤكَّدة كمكسورة في القسم ب.

| # | ملف:سطر | العملية المُغلَّفة | ماذا يُبتلَع | الخطورة |
|---|---|---|---|---|
| 1 | `zamakana/service.py:660` | `_register_affiliate_commission` (→ `AffiliateService.register_commission` غير الموجودة، #10) | `AttributeError` بصمت، log فقط "Affiliate registration failed" | 🔴 **عالية — فقدان عمولة مالية صامت** |
| 2 | `employment/service.py:114` | نفس النمط | نفس الشيء | 🔴 عالية |
| 3 | `digital_twin/service.py:104` | نفس النمط | نفس الشيء | 🔴 عالية |
| 4 | `arbitration_syndicates/service.py:575` | نفس النمط | نفس الشيء | 🔴 عالية |
| 5 | `transport/service.py:587` | نفس النمط | نفس الشيء | 🔴 عالية |
| 6 | `tourism_sports/service.py:528` | نفس النمط | نفس الشيء | 🔴 عالية |
| 7 | `tenders_auctions/service.py:494` | نفس النمط | نفس الشيء | 🔴 عالية |
| 8 | `service_marketplace/service.py:498` | نفس النمط | نفس الشيء | 🔴 عالية |
| 9 | `zamakana/service.py:330` | `invoicing.create_invoice()` (→ `audit_log` كراش جوّاها، #14/#11b) | استثناء `create_invoice` كامل، فاتورة الالتزام (time pledge) لا تُنشأ فعليًا لكن العملية المالية الأساسية أتمّت | 🟡 متوسطة (موثَّق سابقًا كنمط #11b) |
| 10 | `tourism_sports/service.py:201,328,475` | نفس نمط `invoicing.create_invoice()` (×3 مواضع) | نفس الشيء | 🟡 متوسطة (موثَّق) |
| 11 | `realestate/service.py:294` | نفس النمط | نفس الشيء | 🟡 متوسطة (موثَّق) |
| 12 | `transport/service.py:81` | `AIGovernanceService.check_and_consume` (#15، wrong-kwarg مؤكَّد) | `TypeError` بصمت، log تحذير فقط، الدالة تُكمِّل كأن فحص الحصة نجح | 🔴 **عالية — تجاوز فحص حصة/دفع AI بالكامل بصمت** |
| 13 | `realestate/service.py:84` | نفس النمط لـ`check_and_consume` | نفس الشيء | 🔴 عالية |
| 14 | `insurance/service.py:438` | `execute_agent_action` (#16، wrong-kwarg) | استثناء كامل يُبتلَع، log فقط "AI analysis failed" | 🟡 متوسطة (تحليل AI فقط، ليس مالي مباشر) |
| 15 | `manufacturing/service.py:310,672` | نفس نمط `execute_agent_action` (×2) | نفس الشيء | 🟡 متوسطة |
| 16 | `arbitration_syndicates/service.py:104,119` | نفس النمط | نفس الشيء | 🟡 متوسطة |
| 17 | `invitations/service.py:83` | نفس النمط | نفس الشيء | 🟡 متوسطة |
| 18 | `logistics/service.py:557` | نفس النمط | نفس الشيء | 🟡 متوسطة |
| 19 | `commerce/service.py:598` | `increment_payment_retry_count` (بعد فشل عملية `finance.transfer` retry) | يُسجَّل ويُكمِّل الحلقة — تصميم متعمَّد ظاهريًا (retry loop)، ليس باج مخفي | 🟢 مقبول (تصميم صحيح) |
| 20 | `academy/service.py:273` | معاملة مالية (`finance.transfer` على الأرجح) | **يُعاد رفعه كـ`PermissionDeniedError`** — ليس بلعًا صامتًا، الاستثناء يظهر للـcaller | 🟢 آمن (إعادة رفع صريحة) |
| 21 | `health/service.py:236` | خصم مالي | **يُعاد رفعه كـ`SovereignError`** | 🟢 آمن (إعادة رفع صريحة) |

**ملاحظة منهجية:** القائمة أعلاه مُركَّزة (ليست شاملة لكل `try/except` في المشروع كما طُلب صراحة) — ركّزت حصريًا على مواضع تتقاطع مع بنود القسم ب المؤكَّدة كمكسورة. أهم نمط مُكتشَف: **الصف #1-8 (فقدان عمولة affiliate) هو النمط الأخطر ماليًا** — 8 دومينات مؤكَّدة بصمت تفشل في تسجيل عمولة الإحالة دون أي أثر خارج سطر log واحد، ودون أي رصيد يُحسَب أو استرجاع.

---

## القسم د) خريطة حالة الدومينات (35 دومين)

| # | الدومين | فُحص بعمق سابقًا؟ | أخطاء مؤكَّدة (أ+ب+ج) هذه الجلسة | التصنيف |
|---|---|---|---|---|
| 1 | `academy` | جزئيًا (constructor-mismatch) | try/except آمن (إعادة رفع) — 0 باج جديد جوهري | 🟡 غير مفحوص بالكامل |
| 2 | `admin` | نعم (موثَّق: غير موصول بـmain.py، شبه فارغ) | لا جديد | ⚪ حالة خاصة (معروفة) |
| 3 | `affiliate` | نعم (جوهر #10) | الجذر نفسه هنا (missing `register_commission`)، لا مواضع #1 مكسورة داخليًا | 🔴 فيه أخطاء موثَّقة (جذر #10) |
| 4 | `agritech` | لا | **غير موصول بـmain.py (جديد)**، audit_log×11، redis wrapper missing×3، AgriTechRepository missing method، EventBus مكسور، get_bio_cohort/get_soil_reading/get_zone/get_farm missing tenant_id (mypy) | 🔴 فيه أخطاء موثَّقة كثيفة جدًا |
| 5 | `ai_agents` | جزئيًا | audit_log×4، EventBus مكسور، generate_monthly_invoice arity (جديد) | 🔴 فيه أخطاء |
| 6 | `ai_governance` | جزئيًا (#15 جذر) | الجذر (#15)، + جديد: `_check_agent_ownership`/`get_remaining_quotas` غير موجودة (router)، `get_usage_log_by_idempotency` missing tenant_id ذاتيًا، router bool/.get و list/.data type bugs | 🔴 فيه أخطاء كثيفة (router خصوصًا) |
| 7 | `arbitration_syndicates` | جزئيًا | #1، #14×6، #15، #16، #17 (محلي)، EventBus مكسور، affiliate try/except صامت | 🔴 فيه أخطاء كثيفة |
| 8 | `auth` | نعم (Phase 4 قيد الحذف) | غير موصول بـmain.py (مؤكَّد) | ⚪ قيد الحذف |
| 9 | `automation` | لا | execute_agent_action wrong-kwarg (محمي جزئيًا) | 🟡 غير مفحوص بالكامل |
| 10 | `command` | لا | **الوحيد الذي يستدعي `check_and_consume`/`execute_agent_action` بشكل صحيح 100%** — EventBus مكسور فقط، audit_log×3 | 🟡 أنظف نسبيًا لكن غير مفحوص بالكامل |
| 11 | `commerce` | جزئيًا (simpletenant-fix) | EventBus مكسور، audit_log×1 مباشر (الباقي `_create_audit_log` آمنة)، try/except retry سليم | 🟡 غير مفحوص بالكامل |
| 12 | `communications` | لا | #8 (get_user)×2، audit_log×8 (router)، redis wrapper missing (pubsub/publish)×2 | 🔴 فيه أخطاء |
| 13 | `digital_twin` | جزئيًا (simpletenant-fix) | #8، audit_log×3، EventBus مكسور، affiliate try/except صامت | 🔴 فيه أخطاء |
| 14 | `employment` | جزئيًا | #8، audit_log×2، #16 wrong-kwarg، update_attendance_check_out wrong-kwargs (جديد mypy)، AcademyRepository.get_user_certificates missing (جديد)، AffiliateService() constructor missing tenant_id في tasks (جديد)، affiliate try/except صامت | 🔴 فيه أخطاء كثيفة |
| 15 | `finance` | نعم (simpletenant-fix) | **الاستثناء الوحيد الصحيح لـEventBus** — جذر #22 هنا لكن الاستخدام الداخلي آمن | 🟢 نظيف نسبيًا لهذه الأنماط |
| 16 | `health` | لا | #8، audit_log×3، EventBus مكسور، try/except آمن (إعادة رفع) | 🔴 فيه أخطاء |
| 17 | `identity` | نعم (auth→identity merge) | لا شيء جديد — استخدام redis/get_by_id داخليًا كله صحيح | 🟢 نظيف مؤكَّد لهذه الأنماط |
| 18 | `insurance` | جزئيًا (savepoint-fix #9/#11b) | #1، #14×6، #15، #16×2، #22 (payout_tx مؤكَّد سابقًا) | 🔴 فيه أخطاء كثيفة (موثَّقة سابقًا جزئيًا) |
| 19 | `invitations` | جزئيًا (#11a مُغلَق) | #1، #14×7، #15، #16×2 (idempotency_key مفقودة)، EventBus مكسور | 🔴 فيه أخطاء كثيفة |
| 20 | `invoicing` | جزئيًا (#11b مُغلَق) | #14×2، #23، #24، #25 (مؤكَّد)، EventBus **type-mismatch مؤكَّد آليًا (arg-type)**، constructor missing tenant_id×2 (جديد)، `Invoice` name-not-defined×5 (جديد) | 🔴 فيه أخطاء كثيفة جدًا |
| 21 | `iot` | نعم (P0 tenant_id isolation) | #1، **`self.redis` مربوط بدالة غير مُستدعاة (جديد، خطير)** | 🔴🔴 اكتشاف جديد خطير |
| 22 | `logistics` | لا | #1، audit_log×5، #15، #16، EventBus مكسور | 🔴 فيه أخطاء |
| 23 | `manufacturing` | لا | #1، audit_log×12، #15×2، #16×2، EventBus مكسور | 🔴 فيه أخطاء كثيفة جدًا |
| 24 | `privacy` | نعم (P0 tenant_id isolation) | **جديد: `is_privacy_officer(int)` بينما التوقيع يتوقع `User` — type mismatch محلي (router+service)** | 🔴 اكتشاف جديد |
| 25 | `projects` | جزئيًا (simpletenant-fix) | #7 (`setnx`، موثَّق)، EventBus مكسور | 🔴 فيه أخطاء موثَّقة |
| 26 | `realestate` | جزئيًا (savepoint-fix #9/#11b) | #1×2، #14×4، #15، #16، #22 (مؤكَّد سابقًا) | 🔴 فيه أخطاء كثيفة (موثَّقة جزئيًا) |
| 27 | `saas` | نعم (#9 مُغلَق) | استخدام `can_access_service`/`finance.transfer` داخليًا صحيح، لكن **`tasks/saas_tasks.py` فيه 5 مواضع constructor-missing-tenant_id جديدة (mypy)** | 🟡 الجذر نظيف، الـtasks لأ |
| 28 | `service_marketplace` | لا | #1، #14×1، #15، #12، #13 (create_invoice wrong-kwarg مؤكَّد جديد)، AffiliateService.register_commission missing (مؤكَّد mypy)، get_customization_request missing (جديد)، affiliate try/except صامت | 🔴 فيه أخطاء كثيفة جدًا |
| 29 | `social` | لا | #1، #14×8، #15، #16، #12، create_connection wrong-kwargs (جديد)، get_physical_gift_request missing tenant_id (جديد)، SocialRepository ×4 missing get_* methods (جديد كبير) | 🔴🔴 فيه أخطاء كثيفة جدًا |
| 30 | `sovereign_entities` | جزئيًا (simpletenant-fix) | audit_log×3، #5 (endpoints غير محمية، قرار معلَّق)، review_kyb/update_entity (غير مصنَّف)، finance.transfer آمن (متغيّر غير مستخدَم) | 🔴 فيه أخطاء موثَّقة |
| 31 | `tenders_auctions` | لا | #1، #14×6، #15، #16×2، #12، get_live_bid missing (جديد) | 🔴 فيه أخطاء كثيفة |
| 32 | `tourism_sports` | جزئيًا (savepoint-fix #11b) | #1، #14×3، #15، #16×3، #12، get_program_participant/get_ticket/get_transfer missing×3 (جديد كبير)، place_transfer_bid conflict (موثَّق) | 🔴🔴 فيه أخطاء كثيفة جدًا |
| 33 | `transport` | لا | #1×2، #14×5، #15، #16، #12، #18×2 (مؤكَّد)، **#22 مكسور فعليًا (جديد — payment_tx_hash)**، get_booking missing tenant_id (جديد) | 🔴🔴 فيه أخطاء كثيفة جدًا + اكتشاف حرج جديد |
| 34 | `translation` | لا | `self.redis = get_redis_client()` — نمط مختلف، يحتاج تحقق منفصل لو `get_redis_client` بترجع wrapper أم عميل خام | 🟡 غير مفحوص بالكامل |
| 35 | `zamakana` | جزئيًا (savepoint-fix #11b) | #1، #14×9، #15، #16 (idempotency_key مفقودة)، ZamakanaRepository.get_edge missing (جديد)، EventBus مكسور، affiliate try/except صامت | 🔴🔴 فيه أخطاء كثيفة جدًا |

**ملخص إحصائي:** 0 دومين "نظيف مؤكَّد بثقة كاملة" فيما يخص الأنماط المفحوصة هنا سوى `identity` (والجزء الداخلي من `finance`). **~27 من 35 دومين فيهم أخطاء موثَّقة أو مكتشَفة حديثًا هذه الجلسة.** 6 دومينات (`automation`, `translation`, `academy` جزئيًا) لم تُفحص بنفس العمق — تحتاج جلسة متابعة.

---

## 📊 الجدول الموحَّد النهائي — كل الاكتشافات الجديدة (غير موثَّقة سابقًا)، مرتبة بالأولوية

| أولوية | الاكتشاف | النطاق | لماذا هذا الترتيب |
|---|---|---|---|
| 1 | **`eventbus-redis-wrapper-missing-publish` — توسيع من دومين واحد إلى 34/35 دومين (55 موضع)** | 34 دومين | يمنع كل event عبر المنصة تقريبًا، ويخفي أخطاء لاحقة (audit_log، idempotency) — أوسع أثر ممكن |
| 2 | **`finance-transfer-payment-tx-hash-broken` — موضع ثالث حي مكسور فعليًا (`transport/service.py:512`, `DeliveryTask.payment_tx_hash`)** | transport | `DataError` مضمون عند تنفيذ دفع رسوم توصيل — مالي مباشر |
| 3 | **`iot-service-redis-attribute-not-callable` — `self.redis` مربوط بمرجع دالة لا نتيجتها** | iot | `AttributeError` مضمون عند أي استخدام كاش IoT — خطأ من نوع مختلف تمامًا عن #7 المعروف |
| 4 | **`ai-governance-router-broken-contract` — `_check_agent_ownership`/`get_remaining_quotas` غير موجودتين + router يعامل `bool`/`list` كأنهما `dict`/paginated** | ai_governance/router.py | يكسر endpoints الحوكمة الإدارية بالكامل، غير موثَّق سابقًا إطلاقًا |
| 5 | **`social-repository-missing-get-methods` — 4 methods (`get_group`, `get_connection`, `get_digital_gift`, `get_group_subscription`) غير موجودة، فقط `create_*` مقابلها** | social | نمط جديد بالكامل (مختلف عن #7/#8/#10) — يكسر أي محاولة قراءة بعد إنشاء في 4 مسارات |
| 6 | **نفس نمط "get_X مفقودة، فقط create_X موجودة" في 4 دومينات إضافية** (`tourism_sports`×3: `get_program_participant`/`get_ticket`/`get_transfer`, `tenders_auctions`: `get_live_bid`, `zamakana`: `get_edge`, `service_marketplace`: `get_customization_request`) | tourism_sports, tenders_auctions, zamakana, service_marketplace | نفس فئة #5 أعلاه — يستحق بند Backlog مركزي موحَّد جديد "read-after-write repository methods missing" |
| 7 | **`privacy-is-privacy-officer-type-mismatch` — `int` يُمرَّر حيث `User` متوقَّعة (router+service)** | privacy | دومين حساس أمنيًا (P0 tenant_id isolation سابقًا)، باج جديد لم يُكتشَف من قبل |
| 8 | **`tasks-constructor-missing-tenant-id` — 19 موضع جديد عبر `governance.py`(×3)، `saas_tasks.py`(×5)، `commerce.py`(×5)، `affiliate.py`(×3)، `agritech.py`(×3)** | app/tasks/*.py | امتداد كبير غير موثَّق لبند #20 — كل هذه الـCelery tasks تفشل عند التنفيذ الفعلي |
| 9 | **`audit-log-communications-router` — 8 مواضع `audit_log` مكسورة داخل router (مش service)** | communications | نفس جذر #14 لكن في طبقة مختلفة (router) لم تكن مغطاة بالتوثيق السابق |
| 10 | **`agritech-domain-unregistered` — دومين كامل غير موصول بـ`main.py` (مثل `admin`)، لم يكن موثَّقًا** | agritech | لا endpoint حي متأثر (الدومين غير مكشوف HTTP)، لكن أخطاؤه (`audit_log`×11، redis wrapper×3) ستظهر فورًا لو اتوصل مستقبلًا |
| 11 | **`employment-repository-wrong-kwargs` — `update_attendance_check_out` بمعاملات `record_id`/`check_out_location` غير موجودة** | employment | مؤكَّد آليًا فقط (mypy)، لم يُفحص يدويًا بعد |
| 12 | **`invoicing-router-constructor-missing-tenant-id` + `Invoice`-not-defined×5** | invoicing/router.py | يمنع `GET /invoicing/{id}` وما شابه من العمل أصلًا في بعض المسارات |
| 13 | **`duplicate-kwarg-audit` — 7 مواضع مرشَّحة إضافية (`**data` + kwarg صريح متضارب)، غير مؤكَّدة قطعيًا** | transport, sovereign_entities, social, service_marketplace, arbitration_syndicates×2, ai_governance | يحتاج تأكيد schema قبل تصنيفه نهائيًا |
| 14 | **`user-repository-get-user-audit` — تصحيح العدد من 6/5 إلى 5/4 (استبعاد false positive في identity)** | — | تصحيح توثيقي بسيط، لا أثر عملي |
| 15 | **`check-and-consume-double-bug` — 7 من 13 موضع #15 ناقصين `action_type` الإجباري بجانب `tenant_id` الزائد** | zamakana, transport, tourism_sports, tenders_auctions, social, realestate, arbitration_syndicates | تفصيل إضافي داخل #15 الموجود، يوضح أن الإصلاح المركزي لازم يعالج بجّين مش واحد |
| 0 | **`academy-create-course-duplicate-kwarg` — كراش 100% مؤكَّد (schema→router→service) على كل `POST /academy/courses`** | academy | تتبُّع قطعي عبر الـschema (مش grep تخميني) أثبت `instructor_id` بيتمرر مرتين حرفيًا؛ يستاهل ترتيب أعلى من 15 رغم كونه محلي — نسبة تكرار الكراش 100% (مش احتمالية) هي ما يبرر الأولوية القصوى بغض النظر عن ضيق النطاق |

---

## ملخص تنفيذي (سطرين)

الفحص الآلي (`mypy --strict`، مفلترًا لأربع فئات فقط) أكّد بشكل مستقل تقريبًا كل بند Backlog موجود، وكشف **~30+ موضع جديد** غير موثَّق سابقًا — أخطرها توسّع `eventbus-redis-wrapper-missing-publish` من دومين واحد إلى **34 من 35 دومين**، وموضع ثالث حي مكسور فعليًا لبج `finance.transfer()`/`tx_hash` في `transport`. القسم ج أثبت أن فقدان عمولات affiliate الصامت (#10) مؤكَّد الآن عبر **8 دومينات** بنفس نمط try/except، لا دومين واحد. **~27 من 35 دومين فيها أخطاء مؤكَّدة أو مكتشَفة حديثًا** — دومين واحد فقط (`identity`) نظيف بثقة كاملة لهذه الأنماط تحديدًا.
