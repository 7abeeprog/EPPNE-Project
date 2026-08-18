# جلسة: eventbus-redis-wrapper-publish-fix (المرحلة 1.1 من خطة الجرد الشامل)

**تاريخ:** 2026-08-18
**النوع:** تشخيص (قراءة فقط حتى الآن — صفر Edit) تمهيدًا لإصلاح مركزي واحد بأثر واسع.
**المصدر:** `.claude/reports/technical-pattern-sweep-session-log.md` — بند "🔴🔴 يستوجب انتباه فوري #1" + بند `eventbus-redis-wrapper-missing-publish` في القسم ب.

---

## 1. تصحيح جوهري على رقم النطاق الموثَّق في تقرير الجرد الأصلي

التقرير المصدر يقول **"34 من 35 دومين"**. الفحص المباشر هنا (grep شامل لـ`EventBus(` و`from app.core.event_bus import` عبر `app/` بالكامل، بلا استثناء أي ملف) وجد **رقمًا مختلفًا فعليًا**:

- **35 دومين إجمالي** في `app/domains/` (بما فيها `admin`/`auth` بلا `service.py` أصلًا، فمستبعدان بداهة من أي استخدام EventBus).
- **33 دومين عندهم `service.py`**.
- من الـ33: **23 فقط بيستوردوا/يبنوا `EventBus`** (`zamakana, transport, tourism_sports, invitations, insurance, health, finance, employment, tenders_auctions, sovereign_entities, social, service_marketplace, digital_twin, commerce, command, realestate, projects, manufacturing, logistics, arbitration_syndicates, ai_agents, agritech, invoicing`).
- من الـ23: **`finance` وحدها صحيحة** (`EventBus()` بلا معامل).
- **الباقي (22 دومين) هي الفعليًا المكسورة**، مش 34.

**العشرة دومينات المتبقية من الـ33 (`translation, identity, academy, affiliate, ai_governance, communications, privacy, iot, saas, automation`) لا تبني `EventBus` إطلاقًا** — صفر خطر EventBus فيها (قد يكون عندها مشاكل Redis تانية موثقة في بنود مختلفة، لكن خارج نطاق هذه الجلسة تحديدًا).

**استثناء ثانٍ مكتشَف حديثًا — `app/tasks/agritech.py` (ليس دومين، ملف tasks منفصل) صحيح فعليًا رغم ظهوره في قوائم الجرد الأولي:**

```python
# app/tasks/agritech.py:159-165 و220-224 (نفس النمط في الموضعين)
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client as redis_client_wrapper

redis_client = await redis_client_wrapper.get_client()   # ← await هنا يرجّع العميل الخام الفعلي
event_bus = EventBus(redis_client)                          # ← عميل خام صحيح، مش الـwrapper
```

هذا الملف **بيستدعي `await redis_client_wrapper.get_client()` قبل بناء `EventBus`**، فيمرر عميل `redis.asyncio.Redis` الخام الحقيقي (اللي عنده `publish` أصلًا) — **نفس فلسفة `finance`، لكن بأسلوب مختلف (استخراج يدوي بدل الاعتماد على الـdefault في `__init__`)**. الخمس مواضع `event_bus.publish(...)` في هذا الملف (أسطر 187, 196, 209, 228, 236) **تعمل بنجاح بالفعل الآن، بدون أي إصلاح**.

بالمقابل، `app/tasks/agritech.py:244,258,262` (نفس الملف، دوال `_analyze_medium_priority`/`_analyze_low_priority`) بتستخدم نفس أسلوب `await get_client()` قبل نداء `.setex/.lpush/.ltrim` مباشرة — **هذه أيضًا صحيحة بالفعل** (العميل الخام عنده كل هذه الـmethods أصلًا). يعني بند `#7 redis-client-wrapper-missing-methods` في التقرير الأصلي **مُدرِج هذه المواضع (15-16) بالخطأ** ضمن قائمة "methods مفقودة" — هي مش مفقودة، لأن الكائن المستخدَم فعليًا هنا عميل خام مش الـwrapper. **هذا خارج نطاق مهمة اليوم (نطاقنا: `publish` فقط) لكن يستحق تصحيحًا في تقرير الجرد الأصلي لاحقًا.**

**دومين `agritech` (الـservice وليس tasks) نفسه عنده كود ميت مثير للانتباه:**

```python
# app/domains/agritech/service.py:33-35
redis = redis_client.client if hasattr(redis_client, 'client') else redis_client
self.event_bus = EventBus(redis)
```

`RedisClientWrapper` **ليس عندها attribute اسمه `client`** (عندها `_client` خاص + `get_client()` كـasync method). `hasattr(redis_client, 'client')` بترجع **`False` دائمًا** → الشرط بيسقط دايمًا على `else: redis = redis_client` (الـwrapper نفسه). **نفس الباج بالضبط الموجود في الـ21 دومين التانية، لكن ملفوف في محاولة (فاشلة) للتحايل عليه.** يبقى ضمن الـ22 المكسورة فعليًا، لا استثناء.

**الخلاصة العددية الصحيحة:**

| الفئة | العدد |
|---|---|
| دومينات مكسورة فعليًا (تبني `EventBus(wrapper)` وتستدعي `.publish()` لاحقًا أو حتى بدونه) | **22** |
| دومين صحيح أصلاً (`finance`) | 1 |
| ملف tasks صحيح فعليًا رغم الظهور في القوائم الأولى (`tasks/agritech.py`) | 1 (ليس دومين) |
| دومينات لا تستخدم EventBus إطلاقًا | 10 |
| موضع مستقل خارج EventBus لكن نفس الجذر (`communications/router.py:84`) | 1 |
| **الإجمالي (35 دومين + tasks + router المستقل)** | يطابق |

---

## 2. جدول الأدلة — الخيار أ مقابل الخيار ب

### الخيار أ: إضافة `publish()` حقيقية على `RedisClientWrapper`

```python
# app/core/redis_client.py — إضافة داخل class RedisClientWrapper، بجوار باقي الاختصارات
async def publish(self, channel: str, message: str):
    client = await self.get_client()
    return await client.publish(channel, message)
```

| دليل | التفاصيل |
|---|---|
| هل `RedisClientWrapper` بتحتفظ بعميل خام يمكن الوصول له؟ | ✅ **نعم** — `self._client: Optional[redis.Redis]` (نفس `redis.asyncio.Redis` الحقيقية اللي عندها `.publish()` أصلًا). الوصول الآمن الموحَّد المستخدَم في كل الـmethods التانية هو `client = await self.get_client()` — نفس النمط اللي هطبّقه هنا حرفيًا (صف واحد إضافي، صفر انحراف عن الأسلوب الموجود). |
| هل تستخدم مكتبة مختلفة بواجهة مختلفة؟ | ❌ لا — نفس `redis.asyncio` (`import redis.asyncio as redis`, سطر 2). لا `aioredis` منفصلة ولا واجهة بديلة. `publish(channel, message)` هو التوقيع القياسي 1:1 لمكتبة `redis-py` نفسها. |
| حجم التغيير | **5 أسطر** (method واحدة، بنفس نمط `ping`/`get`/`setex` الموجودة أصلًا سطر 83-113). |
| نقطة تأثير واحدة أم متعددة؟ | **نقطة واحدة** (`app/core/redis_client.py`) تصلح كل الـ22 دومين + `communications/router.py:84` تلقائيًا، بلا لمس أي ملف دومين. |
| خطر الانحراف عن نمط EventBus نفسه | صفر — `EventBus.__init__`/`publish()` تبقى كما هي تمامًا، غير ممسوسة. |

### الخيار ب: تعديل `EventBus.__init__` لاستخراج العميل الخام من الـwrapper

```python
# احتمال توضيحي فقط — غير موصى به
def __init__(self, redis_client=None):
    if redis_client is not None and hasattr(redis_client, "get_client"):
        # يحتاج async — لكن __init__ لا يمكن أن يكون async!
        ...
```

| دليل | التفاصيل |
|---|---|
| المشكلة الجوهرية | `RedisClientWrapper.get_client()` هي **`async`** (لأنها قد تستدعي `initialize()` عند أول استخدام). `EventBus.__init__` **sync بالكامل** — لا يمكن نداء `await` داخل `__init__` عادي. الحل يحتاج إما (أ) جعل `EventBus` تدعم "lazy resolution" لعميلها الفعلي عند أول `publish()` بدل `__init__` (تغيير معماري أوسع من مجرد إصلاح)، أو (ب) تمرير `redis_client._client` مباشرة (خاص/private attribute، وهش لو `initialize()` لسه ما اتنادتش بعد — بيرجع `None` ويكسر بصمت بدل `AttributeError` واضح). |
| حجم التغيير | أوسع (يمس `EventBus` + منطق async/sync، ويحتاج تعديل كل الـ23 موضع نداء `EventBus(...)` لو الحل يقتضي تغيير التوقيع لدالة async factory بدل `__init__`) أو حل هش (`._client` مباشرة). |
| نقطة تأثير | ملف واحد (`event_bus.py`) لكن **يمس السلوك حتى في `finance` الصحيحة أصلاً** — خطر انحدار (regression) على الحالة الوحيدة الشغالة فعلاً. |
| التوصية | ❌ **غير موصى به** — أعلى خطرًا وأعقد لغير داعٍ، وبيلمس الحالة الصحيحة الوحيدة الموجودة. |

### ✅ التوصية: **الخيار أ** — أقل تغييرًا (5 أسطر، ملف واحد)، أقل خطرًا (إضافة صرفة، صفر لمس لأي ملف يعمل حاليًا بما فيها `finance`)، ومتسق 100% مع النمط المعماري الموجود فعلاً في نفس الكلاس (`get_client()` ثم استدعاء method مطابقة على العميل الخام).

---

## 3. فحص التعارض — إضافة `publish` على Singleton مستخدَم في أماكن كتير

- **الاسم `publish` غير مستخدَم حاليًا كـattribute/method على `RedisClientWrapper`** (تأكيد بقراءة الملف كاملاً: `ping, get, setex, set, delete, exists, incr, expire, get_json, set_json, initialize, get_client, close` — لا شيء اسمه `publish`).
- **صفر كود حالي بينادي `redis_client.publish(...)` ويتوقع فشلها** (لا يوجد أي `except AttributeError` مبني على غياب `publish` تحديدًا يعتمد عليه أي منطق).
- الإضافة **صرفة (additive)** — بلا تعديل توقيع أي method موجودة، بلا حذف، بلا تغيير سلوك أي استدعاء حالي لـ`get/set/setex/...`. مطابقة تمامًا لمعيار "إضافة صرفة" المستخدَم مسبقًا مع Backlog #9.

**✅ تأكيد صريح: لا تعارض متوقَّع أو مكتشَف.**

---

## 4. فحص `communications/router.py:84` — هل نفس الحل هيغطيها؟

```python
# communications/router.py:82-84
async def broadcast_to_user_redis(user_id: int, message: dict):
    from app.core.redis_client import redis_client
    channel = f"user:{user_id}:notifications"
    await redis_client.publish(channel, json.dumps(message))  # type: ignore
```

هذا الموضع بينادي `redis_client.publish(channel, message: str)` **مباشرة على نفس الـSingleton** (`RedisClientWrapper` instance)، **بنفس توقيع الـmethod المقترحة بالضبط** (`channel: str, message: str`). **✅ نعم، الخيار أ بيغطيها تلقائيًا بالكامل، صفر تعديل إضافي مطلوب في `communications/router.py`.**

**ملاحظة هامشية (خارج النطاق، موثَّقة فقط):** `communications/router.py:48` — `redis_client.pubsub()` — **method مختلفة تمامًا (`pubsub`, مش `publish`)**، غير مغطاة بهذا الإصلاح، وغير مطلوبة في نطاق هذه الجلسة (موثقة في `#7` كموضع منفصل رقم 17). لا حركة عليها اليوم.

---

## 5. الخلاصة قبل أي كود

- **التصحيح الأهم:** النطاق الحقيقي **22 دومين مكسور** (مش 34) + موضع مستقل واحد (`communications/router.py:84`، مغطى تلقائيًا). **رياضيات التحقق المطلوبة في الجلسة تتغير:** بعد عيّنة 3 دومينات، الباقي للفحص القرائي هو **22 - 3 = 19 دومين**، مش 31.
- **استثناءان صحيحان مسبقًا (غير `finance`):** `app/tasks/agritech.py` (كلا الدالتين `_analyze_high_priority`/`_analyze_medium_priority`) — يستخدم نمط "استخراج العميل الخام يدويًا عبر `await get_client()`" بدل الاعتماد على `EventBus.__init__` الافتراضي. **هذا نمط ثالث مختلف عن نمط الـ22 المكسورة (`EventBus(cast(Any, redis_client))`) ومختلف عن نمط `finance` (`EventBus()` بلا معامل) — لكنه صحيح وظيفيًا وما يحتاج إصلاح.**
- **الخيار الموصى به: أ** — إضافة `async def publish(self, channel: str, message: str)` على `RedisClientWrapper` في `app/core/redis_client.py`، 5 أسطر، صفر لمس لأي ملف تاني.
- **صفر تعارض متوقَّع.**
- **صفر كود اتكتب حتى الآن — بانتظار موافقتكم الصريحة على المتابعة قبل عرض الـdiff الكامل.**

**✅ موافقة صريحة مستلمة على الخيار أ (بما فيها اعتماد الرقم المصحَّح 22 بدل 34).**

---

## 6. الديف الكامل المقترح — بانتظار موافقة صريحة عليه تحديدًا (صفر Edit حتى الآن)

```diff
--- a/app/core/redis_client.py
+++ b/app/core/redis_client.py
@@
     async def expire(self, key: str, time: int):
         client = await self.get_client()
         return await client.expire(key, time)
 
+    async def publish(self, channel: str, message: str):
+        client = await self.get_client()
+        return await client.publish(channel, message)
+
     # ========== عمليات التخزين المؤقت الجماعية (لـ Cache Aside) ==========
     async def get_json(self, key: str):
         """جلب قيمة JSON وتحويلها إلى قاموس (dict)"""
```

**التفاصيل:**
- إضافة صرفة (3 أسطر method + سطر فاصل) بين `expire()` (آخر method في قسم "الاختصارات") وتعليق قسم "التخزين المؤقت الجماعية" — نفس المكان المنطقي (لسه في مجموعة الاختصارات البسيطة).
- نفس النمط الحرفي لكل method سابقة في نفس القسم: `client = await self.get_client()` ثم `return await client.<method>(...)`.
- بلا type hints إضافية غير موجودة أصلاً في باقي الـmethods بنفس القسم (`ping`, `delete`, إلخ لا تحمل return type hints هي كمان — اتساق كامل مع الأسلوب الموجود، مش نقص توثيق جديد).
- صفر تغيير على أي سطر آخر في الملف.

**حالة الموافقة على هذا الديف تحديدًا:** ✅ موافقة نهائية مستلمة — **تم التطبيق فعليًا.**

### git diff الخام بعد التطبيق

```diff
diff --git a/eppne-backend/app/core/redis_client.py b/eppne-backend/app/core/redis_client.py
index 9f6a0b2..9e27756 100644
--- a/eppne-backend/app/core/redis_client.py
+++ b/eppne-backend/app/core/redis_client.py
@@ -112,6 +112,10 @@ class RedisClientWrapper:
         client = await self.get_client()
         return await client.expire(key, time)
 
+    async def publish(self, channel: str, message: str):
+        client = await self.get_client()
+        return await client.publish(channel, message)
+
     # ========== عمليات التخزين المؤقت الجماعية (لـ Cache Aside) ==========
     async def get_json(self, key: str):
         """جلب قيمة JSON وتحويلها إلى قاموس (dict)"""
```

### git status بعد التطبيق

الملف الوحيد المعدَّل من هذه الجلسة: `eppne-backend/app/core/redis_client.py`. باقي القائمة في `git status` (deps.py، agritech/router.py المحذوف، main.py، tasks/*.py، إلخ) موجودة مسبقًا من جلسات سابقة غير مرتبطة بهذه الجلسة، لم تُلمس هنا.

**خطة التحقق الحي بعد التطبيق (معتمدة من المستخدم):** 3 دومينات عيّنة من الـ22 —
1. `insurance` (مكان الاكتشاف الأصلي للباج)
2. `zamakana` (الأبسط)
3. `arbitration_syndicates` أو `commerce` (سياق event متعدد الأنواع)

لكل واحد: نداء `event_bus.publish()` فعلي حي + إثبات مباشر (subscribe على القناة أو فحص Redis) إن الرسالة اتنشرت فعليًا، مش بس صفر استثناء.

---

## 7. التحقق الحي — تنفيذ فعلي، صفر محاكاة

**البيئة:** Redis حقيقي يعمل بالفعل عبر Docker (`container: redis`, منفذ مضيف `6380 → 6379`)، مطابق لـ`REDIS_URL` الفعلية في `eppne-backend/.env` (`redis://:***@127.0.0.1:6380/0`). التنفيذ عبر بايثون الحقيقي للمشروع (`eppne-backend/venv/Scripts/python.exe`)، `ENVIRONMENT=development` (تأكيد: صفر استدعاء AWS Secrets Manager).

**المنهجية لكل دومين من الثلاثة:**
1. فتح `subscriber` **مستقل تمامًا** — اتصال redis خام منفصل عبر `redis_client.get_client()` ثم `.pubsub()`، **مش عبر EventBus نفسها** — لضمان أن الإثبات مستقل عن أداة النشر قيد الاختبار.
2. بناء `event_bus` بنفس **النمط الحرفي المستخدَم فعليًا في كود الدومين نفسه** (`EventBus(cast(Any, redis_client))` لـ`insurance`/`zamakana`، و`EventBus(redis_client)  # type: ignore` لـ`arbitration_syndicates` — مطابق لسطر 33 الفعلي في ملفه).
3. نداء `event_bus.publish(event_name, payload)` بنفس **اسم الحدث والـpayload الحقيقيين** المستخدَمين فعليًا في كود كل دومين (منسوخين حرفيًا من `service.py` الخاص بكل واحد).
4. انتظار الرسالة على الـsubscriber المستقل بـ`timeout`، وفك الـJSON، ومقارنة `event`/`payload` مع المُرسَل فعليًا.

**النتيجة الخام (تنفيذ حقيقي، لم يُحرَّر):**

```
=== insurance ===
construct: EventBus(cast(Any, redis_client))
event: insurance.subscription.created
publish(): نجح بدون استثناء (لا يكفي وحده -- التحقق التالي هو الحاسم)
رسالة مُستلمة فعليًا على القناة events:insurance.subscription.created:
  {"event": "insurance.subscription.created", "payload": {"subscription_id": 999001, "tenant_id": 1, "user_id": 1, "policy_id": 42}, "timestamp": 538877.921}
✅ الإثبات: تطابق كامل (event + payload)

=== zamakana ===
construct: EventBus(cast(Any, redis_client))
event: zamakana.node.created
publish(): نجح بدون استثناء (لا يكفي وحده -- التحقق التالي هو الحاسم)
رسالة مُستلمة فعليًا على القناة events:zamakana.node.created:
  {"event": "zamakana.node.created", "payload": {"node_id": 999002, "tenant_id": 1, "user_id": 1, "title": "verification-node"}, "timestamp": 538878.5}
✅ الإثبات: تطابق كامل (event + payload)

=== arbitration_syndicates ===
construct: EventBus(redis_client  # type: ignore)
event: arbitration.case.created
publish(): نجح بدون استثناء (لا يكفي وحده -- التحقق التالي هو الحاسم)
رسالة مُستلمة فعليًا على القناة events:arbitration.case.created:
  {"event": "arbitration.case.created", "payload": {"case_id": 999003, "tenant_id": 1, "claimant_id": 1, "judging_mode": "AI"}, "timestamp": 538878.593}
✅ الإثبات: تطابق كامل (event + payload)

=== الخلاصة ===
insurance: ✅ PASS
zamakana: ✅ PASS
arbitration_syndicates: ✅ PASS
```

**✅ التأكيد: الإثبات ليس مجرد "صفر استثناء" — كل حدث اتأكد استلامه فعليًا على القناة الصحيحة (`events:<event_name>`) عبر subscriber مستقل تمامًا عن أداة النشر، مع تطابق كامل 1:1 لمحتوى `event`/`payload` المُرسَل. الفحص غطّى نمطي البناء الحرفيين الموجودين فعليًا في الكود (`cast(Any, ...)` و`redis_client  # type: ignore` المباشر) — لا نمط بناء ثالث غير مغطى ضمن الـ22.**

**ملف السكريبت المستخدَم (للمرجعية، خارج شجرة المشروع):** `scratchpad/verify_eventbus_publish.py` — قراءة فقط على كود التطبيق، صفر تعديل على أي ملف تطبيق أثناء التحقق (السكريبت نفسه خارج `eppne-backend/`).

---

## 8. فحص قرائي (بلا تنفيذ) — الـ19 دومين المتبقية من الـ22

**الهدف:** التأكد إن كل دومين من الـ19 (22 مكسور إجمالاً، ناقص الثلاثة المتحقَّق منهم حيًا: `insurance`, `zamakana`, `arbitration_syndicates`) بينادي `EventBus` بنمط يؤول وقت التشغيل لنفس التعبير المُصلَح (`EventBus(redis_client)` حيث `redis_client` هو الـSingleton نفسه)، وصفر نمط رابع غير متوقَّع.

**المنهجية:** `grep` شامل مؤكَّد سابقًا لكل `EventBus(` و`from app.core.event_bus import` عبر `app/` بالكامل (القسم 1) — نفس البيانات الخام، مُعاد تصنيفها هنا صراحة حسب الشكل النصي للاستدعاء + التأكد من مصدر `redis_client` (import واحد موحَّد `from app.core.redis_client import redis_client` في كل ملف، بلا استثناء).

| # | الدومين | السطر | الشكل النصي الحرفي | التصنيف |
|---|---|---|---|---|
| 1 | `transport` | `service.py:41` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 2 | `tourism_sports` | `service.py:38` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 3 | `invitations` | `service.py:34` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 4 | `health` | `service.py:44` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 5 | `tenders_auctions` | `service.py:36` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 6 | `sovereign_entities` | `service.py:42` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 7 | `social` | `service.py:40` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 8 | `service_marketplace` | `service.py:44` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 9 | `digital_twin` | `service.py:30` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 10 | `command` | `service.py:34` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 11 | `realestate` | `service.py:38` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 12 | `projects` | `service.py:37` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 13 | `manufacturing` | `service.py:35` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 14 | `logistics` | `service.py:40` | `EventBus(cast(Any, redis_client))` | نمط أ |
| 15 | `ai_agents` | `service.py:37` | `EventBus(cast(Any, redis_client))  # ✅ تجاهل النوع` | نمط أ |
| 16 | `commerce` | `service.py:30` | `EventBus(redis_client)  # type: ignore` | نمط ب |
| 17 | `employment` | `service.py:60` | `EventBus(redis_client)` — بلا `cast`، بلا تعليق | نمط ج (نصي فقط) |
| 18 | `invoicing` | `service.py:28` | `EventBus(redis_client)` — بلا `cast`، بلا تعليق | نمط ج (نصي فقط) |
| 19 | `agritech` (دومين، مش tasks) | `service.py:33-35` | `redis = redis_client.client if hasattr(redis_client, 'client') else redis_client` ثم `EventBus(redis)` | كود ميت موثَّق سابقًا (§1) — `hasattr` بترجع `False` دايمًا (`RedisClientWrapper` مالهاش attribute اسمه `client`)، فبيسقط دايمًا على `redis = redis_client` |

**التوزيع العددي:** نمط أ (`cast(Any, redis_client)`) × 15 + `insurance`/`zamakana` المتحقَّق منهم حيًا (نفس النمط) × 2 = **17 إجمالاً** — يطابق `grep -c "EventBus(cast(Any, redis_client))"` (17 ملف). نمط ب (`# type: ignore` مباشر) × 1 هنا (`commerce`) + `arbitration_syndicates` المتحقَّق حيًا = **2 إجمالاً**. نمط ج (بلا تعليق) × 2 (`employment`, `invoicing`). كود ميت × 1 (`agritech`). **المجموع: 17+2+2+1 = 22 — مطابق تمامًا للعدد الكلي المؤكَّد في القسم 1.**

**فحص "هل نمط ج فعليًا نمط رابع مختلف؟"** لا — تأكيد بقراءة مباشرة لاستيراد `redis_client` في `employment/service.py:27` و`invoicing/service.py:16`: `from app.core.redis_client import redis_client` — **نفس الـSingleton المستورَد بالضبط في كل الملفات التانية**، بلا استثناء أو alias مختلف. الفارق الوحيد نصي/تجميلي: غياب `cast(Any, ...)`/`# type: ignore` حول الاستدعاء (على الأرجح لأن المطوّر في هذين الملفين لم يشغّل mypy على الكود، أو لم يهتم بإسكات التحذير). **لا فرق وقت التشغيل إطلاقًا** — `typing.cast(T, x)` دالة no-op قياسية في مكتبة `typing` (بترجع `x` كما هو بلا أي تحقق أو تحويل)، و`# type: ignore` مجرد تعليق يُقرَأ بواسطة type checkers فقط، صفر تأثير على مُفسِّر بايثون وقت التشغيل. **كل الأربع صيغ النصية (`cast(Any,...)`, `# type: ignore` مباشر, بلا تعليق, كود `hasattr` الميت) تنتج نفس القيمة الفعلية بالضبط وقت التشغيل: `self.event_bus.redis = redis_client` (الـSingleton).**

**✅ الخلاصة: صفر نمط بناء خامس أو سلوك رابع غير متوقَّع. الإصلاح (إضافة `RedisClientWrapper.publish()`) يغطي الـ22 دومين بالكامل بلا استثناء واحد، مؤكَّد بقراءة مباشرة كاملة (صفر تخمين) لكل الـ19 المتبقية زيادة على الثلاثة المتحقَّق منهم حيًا.**

---

## 9. ختم الإغلاق الرسمي

**الحالة النهائية: ✅ مُغلَق رسميًا [2026-08-18].**

| المعيار | الحالة |
|---|---|
| جدول أدلة كامل قبل أي كود (الخيار أ مقابل ب) | ✅ (القسم 2) |
| عرض الديف الكامل، صفر Edit قبل موافقة صريحة | ✅ (القسم 6) |
| `git diff`/`git status` خام بعد التطبيق | ✅ (القسم 6) |
| تحقق حي على 3 دومينات متنوعة — إثبات استلام فعلي مش بس صفر استثناء | ✅ (القسم 7 — `insurance`, `zamakana`, `arbitration_syndicates`) |
| فحص قرائي (بلا تنفيذ) لباقي الدومينات (19) للتأكد من توحُّد النمط | ✅ (القسم 8 — صفر نمط رابع فعلي) |
| تحديث `PROGRESS_LOG.md` (بند فعلي + إغلاق) | ✅ — تحديث السطر الموجود مسبقًا (كان مُضافًا فعلاً كبند بلا رقم من جلسة `#11b`، بحالة 🔴 مفتوح) بدل إضافة سطر مكرر — التزامًا بقاعدة المشروع الصريحة "يُحدَّث بالتعديل في مكانه، مش بالإضافة في الآخر" (`PROGRESS_LOG.md` سطر 5) |
| `git commit` نهائي بالـhash | ⏳ التالي |

**ملاحظة تصحيح إجرائي على تعليمات الجلسة:** طُلب "إضافة بند جديد فعلي… لسه ما اتضافش كبند مستقل" — لكن الفحص وجد إن البند **كان مُضافًا مسبقًا** (بلا رقم، من جلسة `invoicing-savepoint-conflict` [#11b] بتاريخ 2026-08-18 نفسه، بحالة 🔴 مفتوح، مُشيرًا لـ`realestate-insurance-savepoint-fix-session-log.md` قسم 15). **الإجراء المتخذ:** تحديث نفس السطر الموجود (تصحيح الرقم 34→22، تفاصيل الحل، حالة الإغلاق، الإشارة لملف هذه الجلسة) بدل إنشاء سطر مكرر — طبقًا لقاعدة الملف الصريحة نفسها. تم توضيح هذا صراحة بدل التنفيذ الحرفي الأعمى للتعليمة.
