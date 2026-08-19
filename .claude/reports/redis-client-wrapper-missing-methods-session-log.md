# جلسة: redis-client-wrapper-missing-methods (المرحلة 1.4 — Backlog #7)

**تاريخ:** 2026-08-19
**النوع:** تشخيص فقط (قراءة/grep، صفر Edit حتى الآن) — تمهيدًا لإصلاح مركزي واحد في `RedisClientWrapper`.
**المصدر:** `.claude/plans/redis-client-wrapper-missing-methods-session-instructions.md`.
**جلسة منفصلة تمامًا** عن `regression-tests-backfill` (مغلقة، commit `0c1db51`) — هذه أول جلسة تعالج Backlog #7 فعليًا.

**النطاق المعلن:** خمسة methods مفقودة على `RedisClientWrapper` (`app/core/redis_client.py`):
`hincrbyfloat`, `pubsub`, `lpush`, `ltrim`, `hgetall`.

**القاعدة الصارمة لهذه المرحلة:** صفر كود. المطلوب فقط: قراءة `RedisClientWrapper` كاملة، ثم `grep` شامل لكل استخدام فعلي حالي للخمسة methods عبر المشروع كله، وتحديد التوقيع المطلوب من طريقة الاستخدام الحقيقية (مش من توثيق Redis العام) — ثم عرض القايمة الكاملة للموافقة والتوقف.

---

## 1. قراءة `RedisClientWrapper` كاملة

**الملف:** `eppne-backend/app/core/redis_client.py` (143 سطر إجمالي).

**كل الـmethods الموجودة فعليًا حاليًا (بالترتيب):**
`initialize`, `get_client`, `close`, `ping`, `get`, `setex`, `set`, `delete`,
`exists`, `incr`, `expire`, **`publish`** (مُضافة من جلسة `eventbus-publish-fix`
السابقة، سطر 115-117، `commit` سابق — غير هذه الجلسة), `get_json`, `set_json`.

**تأكيد مباشر: الخمسة methods المستهدَفة في هذه الجلسة غير موجودة إطلاقًا**
(بحث نصي كامل في الملف بأكمله، صفر تطابق):
`hincrbyfloat` ❌, `pubsub` ❌, `lpush` ❌, `ltrim` ❌, `hgetall` ❌.

**نمط الكود الموحَّد لكل method اختصار موجودة** (بلا استثناء):
```python
async def <name>(self, <params>):
    client = await self.get_client()
    return await client.<name>(<args>)
```
أي إضافة يجب أن تتبع نفس النمط الحرفي — صفر انحراف معماري.

**نقطة إدراج منطقية:** بعد `publish()` (سطر 117) وقبل تعليق قسم
"عمليات التخزين المؤقت الجماعية" (سطر 119) — نفس منطقة "الاختصارات
البسيطة"، اتساقًا مع كل الإضافات السابقة.

---

## 2. `grep` شامل لكل استخدام فعلي للخمسة methods عبر المشروع

**المنهجية:** `grep -rn` مباشر على `eppne-backend/` بالكامل (بلا استثناء أي مجلد)
لكل نص `redis_client\.(hincrbyfloat|pubsub|lpush|ltrim|hgetall)\b` أولاً
(الاستخدام المباشر على الـSingleton)، ثم توسيع البحث لـ`\.pubsub\(\)`،
`\.lpush\(`، `\.ltrim\(`، `\.hgetall\(`، `\.hincrbyfloat\(` بدون قيد اسم
المتغير (لالتقاط أي alias زي `self.redis` في `event_bus.py`)، ثم قراءة كل
ملف كامل لتحديد: (أ) هل الكائن المستدعى عليه فعلاً هو الـwrapper نفسه أم
عميل خام مُستخرَج مسبقًا عبر `await get_client()`؟ (ب) هل النداء بـ`await`
أم لأ؟ (ج) ما القيم/الأنواع الفعلية المُمرَّرة؟

### 2.1 `hincrbyfloat`

| الملف | السطر | الكائن | `await`? |
|---|---|---|---|
| `app/services/ai/cost_tracker.py` | 65-77 (9 نداءات) | `redis_client` (wrapper، `from app.core.redis_client import redis_client`) | ✅ نعم في كل التسعة |

**الاستخدام الحرفي:**
```python
await redis_client.hincrbyfloat(total_key, "input_tokens", input_tokens)
await redis_client.hincrbyfloat(total_key, "output_tokens", output_tokens)
await redis_client.hincrbyfloat(total_key, "total_cost", total_cost)
```
`total_key`/`daily_key`/`monthly_key`: `str`. الحقل الثاني: `str` ثابت
(`"input_tokens"`, `"output_tokens"`, `"total_cost"`). القيمة الثالثة:
`input_tokens`/`output_tokens` = `int`، `total_cost` = `float` (حساب
`Decimal`-free عادي، سطر 40-42) — يعني لازم `amount: int | float`. القيمة
الراجعة **غير مُستخدَمة/غير مُلتقَطة** في أي من التسعة نداءات (fire-and-forget).

**مصدر الطلب الفعلي:** `CostTracker.record_usage()` تُستدعى من
`app/services/ai/engine.py:138` (`AIEngine.generate()`) **بلا أي
`try/except`** — أي نجاح لأي نموذج AI عبر المنصة بالكامل. **مؤكَّد بقراءة
مباشرة لملف `engine.py` (سطر 100-142): استدعاء `CostTracker.record_usage`
غير مشروط بأي دومين محدد — نقطة مركزية واحدة يمر منها كل استخدام AI في
المشروع.**

**تضخيم نطاق الأثر عن الموصوف في تعليمات الجلسة:** التعليمات تصف الأثر
كـ"يُسقط `execute_agent_action` بالكامل" فقط. **القراءة المباشرة هنا تكشف
نطاقًا أوسع فعليًا:** أي مسار آخر يستدعي `ai_engine.generate()` (مؤكَّد:
`app/main.py:356` — endpoint AI عام مستقل تمامًا عن `ai_agents`، بجانب
`app/domains/ai_agents/service.py`) **يتحطم بنفس الـ`AttributeError`
حرفيًا**، مش فقط مسار الوكلاء. هذا لا يغيّر التوصية (لسه ملف واحد/نقطة
تعديل واحدة) لكنه يرفع الأولوية الفعلية لهذا البند فوق ما هو موصوف.

### 2.2 `hgetall`

| الملف | السطر | الكائن | `await`? |
|---|---|---|---|
| `app/services/ai/cost_tracker.py` | 91, 113, 126 | `redis_client` (wrapper) | ✅ نعم في الثلاثة |

**الاستخدام الحرفي:**
```python
data = await redis_client.hgetall(key)
return {
    "input_tokens": float(data.get("input_tokens", 0)),
    "output_tokens": float(data.get("output_tokens", 0)),
    "total_cost": float(data.get("total_cost", 0)),
}
```
`key: str`. الناتج يُستخدَم كـ`dict` عبر `.get(field, default)` ثم
`float(...)` — يعني القيم المتوقَّعة نصوص قابلة للتحويل لـ`float`
(متوافق تمامًا مع `decode_responses=True` المضبوطة فعليًا في
`ConnectionPool.from_url(...)` سطر 50 من `redis_client.py` — القيم
الراجعة من `redis.asyncio` بالفعل `str` مش `bytes`).

**تصحيح جوهري على افتراض تعليمات الجلسة:** التعليمات تقول
"`services/ai/cache.py` — على الأرجح `hgetall`/`get_json` مرتبطة" وتطلب
عدم الافتراض. **بالقراءة المباشرة: `cache.py` لا تستخدم `hgetall` إطلاقًا**
(تستخدم فقط `get_json`/`set_json`/`expire`، الموجودة مسبقًا، +`lpush`
+`rpop` — راجع §3 تحت). **`hgetall` مستخدَمة حصريًا في `cost_tracker.py`.**

### 2.3 `lpush`

| الملف | السطر | الكائن | `await`? |
|---|---|---|---|
| `app/services/ai/cache.py` | 117 (`BatchProcessor.add_to_batch`) | `redis_client` (wrapper) | ✅ نعم |
| `app/tasks/agritech.py` | 257 (`_analyze_low_priority`) | عميل خام (`redis_client = await redis_client_wrapper.get_client()` سطر 255 — **ليس الـwrapper**) | ❌ لا (باج مستقل، راجع §3) |

**الاستخدام الحرفي المؤثر فعليًا (`cache.py:117`، على الـwrapper):**
```python
await redis_client.lpush(cls.BATCH_KEY, json.dumps({...}))
```
`BATCH_KEY: str` ثابت (`"ai:batch:queue"`)، القيمة الثانية: `str` واحدة
(نتيجة `json.dumps`). الاستخدام الحقيقي هنا **قيمة واحدة فقط**، لكن
`LPUSH` الأصلية في Redis/`redis-py` variadic (`*values`) — التوقيع
المقترح `*values` **لضمان توافق أي استخدام مستقبلي أو استخدامات أخرى غير
مكتشَفة بنفس الاسم دون تضييق غير مبرَّر**، مع العلم أن **الدليل الحي
الوحيد المتاح اليوم يمرر قيمة واحدة بالظبط**.

**موضع `agritech.py:257` لا يتأثر بهذا الإصلاح** — نفس الاستنتاج الموثَّق
مسبقًا في جلسة `eventbus-publish-fix` (تقرير `eventbus-publish-fix-session-log.md`
§1): الكائن `redis_client` في هذه الدالة مُعاد تعريفه محليًا كعميل خام
(`redis.asyncio.Redis` الحقيقي عبر `get_client()`)، عنده `lpush` أصلًا.
**لكن الاستدعاء هنا بلا `await` — باج مستقل، راجع §3 (اكتشاف جانبي).**

### 2.4 `ltrim`

| الملف | السطر | الكائن | `await`? |
|---|---|---|---|
| `app/tasks/agritech.py` | 261 (`_analyze_low_priority`) | عميل خام (نفس سياق §2.3 — **ليس الـwrapper**) | ❌ لا (نفس باج §3) |

**🔴 اكتشاف حاسم: صفر استخدام فعلي لـ`ltrim` على الـwrapper نفسه في كل
المشروع.** `grep` شامل لـ`\.ltrim\(` عبر `eppne-backend/` بالكامل (بلا أي
قيد على اسم المتغير) رجّع **موضعًا واحدًا فقط**، وهو على العميل الخام
(`_analyze_low_priority`)، **مش على `RedisClientWrapper`**. يعني: لا يوجد
اليوم أي كود مكسور فعليًا بسبب غياب `ltrim` على الـwrapper — إضافتها هنا
**استباقية (preventive)**، مش تصحيح لباج حي مؤكَّد بنفس معيار الأربعة
الباقية. **التوقيع المقترح مبني على قياس نمط `LTRIM` القياسي في
`redis-py` + نفس ترتيب المعاملات المستخدَم فعليًا في السطر 261 على
العميل الخام** (`key, start, end`)، لأن التعليمات تمنع صراحة الاعتماد
على توثيق Redis العام بمعزل عن أي دليل استخدام حقيقي — هذا أقرب دليل
متاح رغم أنه على كائن مختلف. **هذه نقطة تحتاج قرارك صراحة (راجع الخلاصة
تحت).**

### 2.5 `pubsub`

| الملف | السطر | الكائن | `await`? |
|---|---|---|---|
| `app/domains/communications/router.py` | 48 (`websocket_notifications`, endpoint حي مفعَّل `/communications/ws`) | `redis_client` (wrapper، `from app.core.redis_client import redis_client` سطر 46) | ❌ لا — نداء متزامن صراحة |
| `app/core/event_bus.py` | 44 (`EventBus.listen()`) | `self.redis` (= الـwrapper نفسه في ~22 دومين حسب `EventBus(cast(Any, redis_client))`، موثَّق مسبقًا في `eventbus-publish-fix-session-log.md`) | ❌ لا — نداء متزامن صراحة |

**الاستخدام الحرفي:**
```python
# communications/router.py:48 — endpoint حي، بيتنفَّذ فعليًا عند أي اتصال WebSocket
pubsub = redis_client.pubsub()  # type: ignore
await pubsub.subscribe(channel)
...
async for message in pubsub.listen():

# event_bus.py:44 — تعريف method، لكن EventBus.listen() نفسها بلا أي مستدعٍ حاليًا
pubsub = self.redis.pubsub()
await pubsub.subscribe(f"events:{event_name}")
```

**تأكيد حي مزدوج مهم:** الموضعان **مستقلان تمامًا** (ملفان مختلفان،
مسارا كود مختلفان) و**متفقان 100% على نفس اتفاقية النداء: بلا `await`،
نتيجة الاستدعاء المباشر عليها `.subscribe()`/`.listen()`/`.unsubscribe()`/
`.close()` لاحقًا** — هذا يطابق فعليًا سلوك `redis.asyncio.Redis.pubsub()`
الحقيقية نفسها (method متزامنة، بترجع كائن `PubSub` فورًا بلا I/O، الـI/O
الفعلي بيحصل لاحقًا في `.subscribe()`/`.listen()` المُنتظَرتين بـ`await`
بالفعل في الكودين). **الدليل الحي القاطع لتوقيع sync، مش من توثيق Redis
العام.**

**أثر الأولوية:** `communications/router.py:48` هو **مسار إنتاج حي
ومُفعَّل فعليًا** (`/communications/ws`) — أي اتصال WebSocket لأي مستخدم
لأي إشعارات حية يتحطم فورًا بـ`AttributeError: 'RedisClientWrapper'
object has no attribute 'pubsub'`. `event_bus.py:44` **كود مُعرَّف لكنه
غير مُستدعًى من أي مكان حاليًا** (`grep` شامل لـ`event_bus.listen(` و
`.listen_all(` عبر `app/` بالكامل: صفر تطابق) — لا يزال يستحق الإصلاح
لاتساق العقد نفسه، لكن بلا أثر إنتاج حي حاليًا.

**تعقيد تصميمي يحتاج قرارًا صريحًا:** `get_client()` (الطريقة الموحَّدة
للوصول للعميل الخام في كل method أخرى بالـwrapper) هي `async` (ممكن
تستدعي `initialize()`). لكن نقطتي الاستخدام الحقيقيتين بتنادوا `pubsub()`
**بلا `await`**. **الحل المتسق مع الدليل الحي (بلا لمس أي ملف مستدعٍ):**
method **متزامنة (`def` عادية مش `async def`)** تقرأ `self._client`
مباشرة (بلا `await self.get_client()`)، معتمدة على إن `main.py:79`
بينادي `await redis_client.initialize()` في الـ`lifespan` **قبل** خدمة
أي طلب — مؤكَّد بالقراءة المباشرة. هذا **أول method متزامنة في الكلاس**
(كل الباقي `async`) — انحراف طفيف عن النمط المعماري الموحَّد، لكنه
الوحيد اللي بيحقق "صفر لمس لأي ملف مستدعٍ" (القاعدة الصارمة المعلَنة في
تعليمات الجلسة) **و** بيطابق سلوك المكتبة الأصلية 1:1.

---

## 3. اكتشافات جانبية (خارج نطاق #7 بصيغته المُعلَنة في التعليمات) — توثيق فقط، صفر إصلاح تلقائي

طبقًا للقاعدة الصارمة المعلَنة في تعليمات الجلسة ("أي اكتشاف جانبي جديد...
توثيق فوري... صفر إصلاح تلقائي، توقف واعرض على المستخدم قبل أي قرار").

### 3.1 `setnx` — سادس method مفقودة، **مذكورة أصلًا في بند #7 نفسه بـ`PROGRESS_LOG.md`، لكن غائبة من قائمة الخمسة في تعليمات هذه الجلسة**

**تناقض مباشر بين مصدرين:** تعليمات هذه الجلسة تحصر البند في خمسة methods
(`hincrbyfloat, pubsub, lpush, ltrim, hgetall`). **لكن `PROGRESS_LOG.md`
سطر 41 (بند #7 نفسه) يوثّق صراحة حالتين مؤكَّدتين تاريخيًا:
`hincrbyfloat` **و`setnx`** (`projects.add_contribution`)`.** تأكيد
مباشر بالقراءة الحية إن `setnx` **لسه مفقودة وموجود استخدامها حيًا الآن**:

```python
# app/domains/projects/service.py:146-163 (add_contribution)
acquired = await self.redis.setnx(redis_key, json.dumps({"status": "processing"}))  # type: ignore
if not acquired:
    cached = await self.redis.get(redis_key)
    ...
await self.redis.expire(redis_key, 3600)
```
(`self.redis` هنا = الـwrapper نفسه، مستوردة كـ`redis_client` على
مستوى الـconstructor — لم أتحقق من alias الدقيق لكنه نفس الـSingleton
حسب الاستيراد الموحَّد في كل الدومينات). التوقيع الظاهر من الاستخدام:
`setnx(key: str, value: str) -> bool` (نفس اتفاقية `SETNX` القياسية).

**القرار مطلوب منك صراحة:** هل تُضاف `setnx` ضمن هذه الجلسة (بما إنها
موثَّقة أصلًا كجزء من بند #7 نفسه في `PROGRESS_LOG.md`، ونفس منهجية
الإصلاح تمامًا)، أم تُستبعَد بدقة لأن تعليمات هذه الجلسة تحديدًا سمّت
خمسة أسماء فقط بلا `setnx` صراحة؟ **لن أقرر بنفسي — هذا بالضبط نوع
"الاكتشاف الجانبي" اللي التعليمات بتطلب التوقف عنده.**

### 3.2 `agritech.py:243,257,261` — نداءات على العميل الخام بلا `await` (باج مختلف تمامًا عن #7)

**غير مرتبط بميثودز الـwrapper الناقصة إطلاقًا** — هذه المواضع الثلاثة
(`redis_client.setex(...)` سطر 243، `redis_client.lpush(...)` سطر 257،
`redis_client.ltrim(...)` سطر 261، كلها في `_analyze_low_priority`/
`_analyze_medium_priority`) بتستخدم **عميل Redis خام حقيقي** (عنده كل
الـmethods دي أصلًا) لكن **بلا `await`** قبل النداء. بما إن هذه
methods من `redis.asyncio.Redis` كلها `async def` (بترجع coroutine)،
النداء بلا `await` **لا ينفّذ العملية إطلاقًا** — بيُنشئ coroutine
"يُتيم" (orphaned) لا يُشغَّل أبدًا (بايثون بيطبع
`RuntimeWarning: coroutine '...' was never awaited` في أفضل الأحوال،
بصمت في التطبيق العملي بدون تفعيل تحذيرات `asyncio` صراحة). **الأثر
العملي المحتمل:** بيانات القراءات الزراعية (`agritech:zone:*`) اللي
المفروض تتخزّن/تُقصّ (`setex`/`lpush`/`ltrim`) **مش بتتسجَّل في Redis
فعليًا إطلاقًا رغم إن الكود شكليًا "بينفّذ" بلا استثناء**. لم أتحقق
حيًا من هذا (خارج نطاق التشخيص المطلوب اليوم بالحرف) — مجرد توثيق قراءة
مباشرة للكود.

### 3.3 اتساق الفحص — لا اكتشافات جانبية أخرى في الملفات الخمسة/الست المفحوصة

`cost_tracker.py`, `cache.py`, `communications/router.py`, `event_bus.py`,
`agritech.py`, `projects/service.py` — تمت قراءتها بالكامل أو بالسياق
الكافي حول كل نداء ذي صلة؛ صفر اكتشاف إضافي غير مذكور أعلاه.

---

## 4. جدول التوقيعات المقترحة (خمسة methods المُعلنة + `setnx` كبند منفصل بانتظار قرارك)

| Method | التوقيع المقترح | الدليل الحي | ثقة |
|---|---|---|---|
| `hincrbyfloat` | `async def hincrbyfloat(self, key: str, field: str, amount)` → `client.hincrbyfloat(key, field, amount)` | `cost_tracker.py:65-77`، 9 نداءات، `await` في كل مرة | ✅ عالية — نمط مطابق حرفيًا لبقية الـwrapper |
| `hgetall` | `async def hgetall(self, key: str)` → `client.hgetall(key)` | `cost_tracker.py:91,113,126`، الناتج يُستخدَم كـ`dict.get(...)` | ✅ عالية |
| `lpush` | `async def lpush(self, key: str, *values)` → `client.lpush(key, *values)` | `cache.py:117`، قيمة واحدة فعليًا اليوم، `*values` لمطابقة LPUSH الأصلية بلا تضييق | ✅ عالية (الاستخدام الحي أحادي القيمة، لكن التوقيع variadic آمن ومتوافق) |
| `ltrim` | `async def ltrim(self, key: str, start: int, end: int)` → `client.ltrim(key, start, end)` | **صفر استخدام حي على الـwrapper نفسه** — مبني على نمط `LTRIM` القياسي + دليل غير مباشر من `agritech.py:261` (عميل خام، نفس ترتيب المعاملات) | 🟡 متوسطة — **يحتاج تأكيدك الصريح بما إنها استباقية** |
| `pubsub` | `def pubsub(self)` **(متزامنة، بلا `async`/`await`)** → `self._client.pubsub()` | `communications/router.py:48` (حي، مُفعَّل) + `event_bus.py:44` (مُعرَّفة، غير مُستدعاة حاليًا) — الاتنين بنفس اتفاقية النداء المتزامن بالحرف | ✅ عالية — دليلان مستقلان متفقان، **لكن التصميم (method متزامنة، أول واحدة في الكلاس) يحتاج موافقتك الصريحة كقرار معماري** |
| `setnx` *(خارج الخمسة المُعلَنة — قرارك مطلوب)* | `async def setnx(self, key: str, value: str)` → `client.setnx(key, value)` | `projects/service.py:157`، `await`، الناتج `bool` يُفحَص بـ`if not acquired` | ✅ عالية (لو تقرر ضمّها) |

---

## 5. حالة الجلسة: تشخيص مكتمل — بانتظار موافقتك الصريحة

**صفر Edit، صفر كتابة كود حتى الآن.** كل ما سبق قراءة/`grep` فقط.
النقاط المفتوحة اللي محتاجة قرارك قبل أي سطر كود (ملخَّصة في الرسالة
المرافقة لهذا التقرير):
1. توقيع `pubsub` كـmethod **متزامنة** (أول واحدة في الكلاس) — موافق؟
2. `ltrim` — تُضاف استباقيًا بالتوقيع القياسي رغم صفر استخدام حي على
   الـwrapper، ولا تُستبعَد من هذه الجلسة لحد ما يظهر استخدام حي فعلي؟
3. `setnx` — تُضاف ضمن هذه الجلسة (موثَّقة أصلًا في بند #7 بـ
   `PROGRESS_LOG.md`) ولا تُستبعَد بدقة لأنها غير مذكورة في تعليمات
   الجلسة الحالية؟
4. الاكتشافان الجانبيان (§3.1 `setnx` نفسها كتناقض توثيقي، و§3.2 نداءات
   `agritech.py` بلا `await`) — مؤكَّد: **لن يُلمَسا في هذه الجلسة** إلا
   لو قررت غير كده صراحة لبند `setnx` تحديدًا (بند 3.2 خارج نطاق #7
   جذريًا بغض النظر عن قرارك — باج مختلف تمامًا، مش method مفقودة).

*(هذا القسم سيُستكمَل لاحقًا بنتائج التحقق الحي بعد موافقتك على التوقيعات وكتابة الكود.)*

---

## 6. قرارات المستخدم الصريحة [2026-08-19] — بعد عرض §1-§5

1. **`pubsub`** → ✅ موافقة على التصميم المقترح بالحرف: method متزامنة (`def pubsub(self)`، بلا `async`/`await`) تقرأ `self._client` مباشرة.
2. **`ltrim`** → ✅ موافقة على الإضافة بالتوقيع المقترح (`key, start, end`)، **رغم صفر استخدام حي على الـwrapper اليوم** — بقرار صريح إنها كانت أصلًا ضمن النطاق المُعلَن. **شرط إضافي من المستخدم:** التحقق الحي لازم يكون عبر استدعاء تجريبي مكتوب خصيصًا لهذه الجلسة (مش انتظار كود إنتاج موجود يستخدمها فعليًا).
3. **`setnx`** → ✅ موافقة على الإضافة ضمن هذه الجلسة. **تصحيح من المستخدم على تعليمات الجلسة نفسها:** كانت تعليمات التسليم ناقصة (اعتمدت على وصف مختصر بدل قراءة `PROGRESS_LOG.md` مباشرة، اللي موثَّق فيه `setnx` صراحة كجزء أصيل من بند #7 نفسه منذ البداية). تُضاف بنفس التوقيع المقترح في §4 (`key: str, value: str`).
4. **§3.1 (تناقض التوثيق حول `setnx`)** → **اتحل بالقرار رقم 3 أعلاه** — لا يحتاج بند Backlog منفصل، لأنه أصبح جزءًا من نطاق هذه الجلسة رسميًا.
5. **§3.2 (`agritech.py` نداءات Redis بلا `await`)** → **اكتشاف حقيقي منفصل تمامًا عن #7، خارج النطاق نهائيًا.** قرار صريح: يُوثَّق فورًا كبند Backlog مستقل جديد في `PROGRESS_LOG.md` (`agritech-redis-calls-missing-await-orphaned-coroutines`)، **صفر لمس على `agritech.py`** في هذه الجلسة.

**النطاق النهائي المعتمد لهذه الجلسة: ست methods** — `hincrbyfloat`, `pubsub`, `lpush`, `ltrim`, `hgetall`, `setnx`.

---

## 7. الديف المُطبَّق فعليًا — `app/core/redis_client.py`

```diff
@@ -116,6 +116,34 @@ class RedisClientWrapper:
         client = await self.get_client()
         return await client.publish(channel, message)
 
+    async def hincrbyfloat(self, key: str, field: str, amount):
+        client = await self.get_client()
+        return await client.hincrbyfloat(key, field, amount)
+
+    async def hgetall(self, key: str):
+        client = await self.get_client()
+        return await client.hgetall(key)
+
+    async def lpush(self, key: str, *values):
+        client = await self.get_client()
+        return await client.lpush(key, *values)
+
+    async def ltrim(self, key: str, start: int, end: int):
+        client = await self.get_client()
+        return await client.ltrim(key, start, end)
+
+    async def setnx(self, key: str, value: str):
+        client = await self.get_client()
+        return await client.setnx(key, value)
+
+    def pubsub(self):
+        """متزامنة عمدًا (بلا async/await) — مطابقة لسلوك redis.asyncio.Redis.pubsub()
+        الحقيقية (لا تنفّذ I/O، فقط تُنشئ كائن PubSub). تعتمد على أن initialize()
+        استُدعيت بالفعل في الـ lifespan قبل خدمة أي طلب."""
+        if self._client is None:
+            raise RuntimeError("Redis client غير مُهيَّأ بعد — استدعِ initialize() أولاً (عادة عبر lifespan في main.py).")
+        return self._client.pubsub()
+
     # ========== عمليات التخزين المؤقت الجماعية (لـ Cache Aside) ==========
     async def get_json(self, key: str):
         """جلب قيمة JSON وتحويلها إلى قاموس (dict)"""
```

**إضافة صرفة بالكامل** — صفر تعديل على أي سطر آخر في الملف، صفر لمس لأي ملف مستدعٍ (`cost_tracker.py`, `cache.py`, `communications/router.py`, `event_bus.py`, `projects/service.py`). `pubsub()` هي أول method متزامنة في الكلاس (بقية الخمسة تتبع نمط `async def ... client = await self.get_client() ...` الموحَّد حرفيًا).

---

## 8. التحقق الحي — الست methods (بيانات throwaway، `REGTEST:` prefix، تنظيف كامل)

**البيئة:** نفس بيئة الجلسات السابقة — Redis حقيقي عبر Docker (`container: redis`, `127.0.0.1:6380→6379`)، بايثون venv الحقيقي للمشروع، `ENVIRONMENT=development`.
**السكريبت:** `scratchpad/verify_redis_wrapper_methods.py` (خارج شجرة `eppne-backend/` عمدًا، قراءة فقط على كود التطبيق).
**المنهجية لكل method:** نداء عبر `RedisClientWrapper` (الكائن قيد الاختبار) + **تحقق مستقل** عبر عميل Redis خام منفصل (`await redis_client.get_client()`، بلا مرور عبر أي method جديدة) — نفس معيار جلسة `eventbus-publish-fix` (صفر ثقة في "صفر استثناء" وحدها).

**النتيجة الخام الكاملة (تنفيذ فعلي، لم يُحرَّر):**

```
--- hincrbyfloat: PASS ---
  call1_return: 1.5
  call2_return: 3.75
  independent_hget: '3.75'          ← HGET مستقل عبر العميل الخام، يطابق التراكم 1.5+2.25=3.75 تمامًا
  expected: 3.75

--- hgetall: PASS ---
  returned: {'a': '1', 'b': '2', 'c': '3'}
  expected: {'a': '1', 'b': '2', 'c': '3'}   ← تطابق كامل لكل الحقول

--- lpush: PASS ---
  independent_lrange: ['v3', 'v2', 'v1']    ← LRANGE مستقل، ترتيب LPUSH صحيح (v1 ثم v2,v3 → v3,v2,v1)
  expected: ['v3', 'v2', 'v1']

--- ltrim: PASS ---
  before: ['a', 'b', 'c', 'd', 'e']
  after: ['a', 'b', 'c']                     ← LRANGE مستقل بعد LTRIM(0,2)، القص صحيح تمامًا
  expected_after: ['a', 'b', 'c']

--- setnx: PASS ---
  first_acquired: True                       ← أول SETNX نجح (مفتاح جديد)
  second_acquired: False                      ← ثاني SETNX فشل كما متوقَّع (مفتاح موجود)
  independent_get: 'first-value'              ← GET مستقل يثبت القيمة الأولى محفوظة، الثانية اتجاهلت
  expected_value: 'first-value'

--- pubsub: PASS ---
  subscribe_confirm_type: 'subscribe'
  received: 'hello-from-regtest'              ← subscriber حقيقي (عبر pubsub() الجديدة) استلم رسالة publish() فعلية من نفس العملية، عبر asyncio.create_task منفصلة
  expected: 'hello-from-regtest'

=== الخلاصة: ✅ كل الست methods PASS ===

مفاتيح REGTEST متبقية بعد التنظيف: []   ← تأكيد صفر مفاتيح يتيمة (SCAN مستقل بنمط REGTEST:*)
```

**✅ تأكيد: التحقق ليس مجرد "صفر استثناء" — كل method اتفحصت بأداة تحقق مستقلة عن أداة النداء نفسها (`HGET`/`LRANGE`/`GET`/subscriber منفصل)، ونظافة كاملة مؤكَّدة بـ`SCAN` مستقل بعد الحذف.**

---

## 9. التحقق الحي الحاسم — `execute_agent_action` + مسار `main.py:356` (بلا أي `monkeypatch`)

**اكتشاف مهَّد الطريق لتحقق أنظف من المتوقَّع:** بالقراءة المباشرة لـ`app/services/ai/engine.py:195-298` (`AIEngine._call_model`)، تبيَّن إن **الاستدعاء الفعلي عبر الشبكة لواجهات الذكاء الاصطناعي الخارجية معطَّل ومُعلَّق بالكامل في الكود حاليًا** (`# الكود الفعلي (معلق):` سطر 290-298) — الدالة بترجع **محاكاة داخلية جاهزة** (`await asyncio.sleep(0.5)` ثم رد نصي ثابت + `usage` وهمية، سطر 278-288)، بمفاتيح API وهمية أصلًا (`API_KEYS` معرَّفة صراحة كـ"محاكاة"، سطر 28-34). **هذا يعني: نداء `ai_engine.generate()` الحقيقي غير المعدَّل، بلا أي `monkeypatch`، آمن 100% (صفر اتصال شبكي فعلي، صفر تكلفة API حقيقية) ويُنفِّذ فعليًا `CostTracker.record_usage()` الحقيقية** — عكس جلسة `ai-agents-execute-action-fix` السابقة اللي اضطرت تستبدل `ai_engine.generate` بالكامل بـ`_fake_generate` **تحديدًا بسبب بج #7 نفسه** (موثَّق صراحة في docstring الملف هناك). بما إن #7 اتصلح الآن، **التحقق هنا أنظف وأكثر واقعية من التحقق السابق نفسه.**

**السكريبت:** `scratchpad/verify_execute_agent_action_live.py` (خارج شجرة `eppne-backend/`).

### 9.1 خطوة 1 — `CostTracker.record_usage()` مباشرة (نفس السطر اللي كان بيكراش قبل الإصلاح بالحرف)

```
النتيجة: {'cost': 0.0, 'input_cost': 0.0, 'output_cost': 0.0}
get_total_cost بعدها مباشرة (يستخدم hgetall): {'input_tokens': 123.0, 'output_tokens': 45.0, 'total_cost': 0.0}
✅ PASS -- صفر AttributeError، القيم اتسجَّلت وترجعت صح.
```
(تكلفة صفرية لأن `hunyuan-mt-7b` نموذج مجاني في `MODEL_CONFIGS` — سلوك متوقَّع وصحيح، مش خطأ).

### 9.2 خطوة 2 — `ai_engine.generate()` مباشرة (نفس مسار `main.py:356`، `/api/ai/chat`، بلا `monkeypatch`)

```
text: 'رد من mistral-saba: REGTEST live verification prompt... (محاكاة)'
model: mistral-saba
usage: {'input_tokens': 8, 'output_tokens': 50, 'total_tokens': 58}
✅ PASS -- صفر AttributeError، رجعت نتيجة كاملة (يعني CostTracker.record_usage جوّاها نجح).
```

### 9.3 خطوة 3 — `AIAgentsService.execute_agent_action()` حي كامل، بلا `monkeypatch` إطلاقًا (الاختبار الحاسم)

بيانات throwaway: `tenant_id=1`، يوزر جديد (`id=313`)، وكيل AI جديد (`id=53`، `requires_human_approval=True`)، عبر `AsyncSessionLocal` حقيقية (docker `eppne_db`).

```
response: {'status': 'PENDING_APPROVAL', 'approval_id': 36,
  'message': 'الإجراء معلق بانتظار الموافقة البشرية',
  'result': {'text': 'رد من mistral-saba: regtest #7 ... (محاكاة)',
    'model': 'mistral-saba',
    'usage': {'input_tokens': 13, 'output_tokens': 50, 'total_tokens': 63},
    'cost': {'cost': 3.26e-05, 'input_cost': 2.6e-06, 'output_cost': 3e-05},
    ...}}
AITaskLog.task_type: ARABIC_CHAT (مش ERROR -- تأكيد صريح إن ai_engine.generate نجحت)
AgentApprovalQueue أُنشئت: id=36, tenant_id=1
✅ PASS -- execute_agent_action اكتملت بالكامل بلا أي AttributeError، بلا أي monkeypatch.
```

**التحقق الحاسم: `AITaskLog.task_type == "ARABIC_CHAT"`، مش `"ERROR"`.** لو كان `hincrbyfloat` لسه ناقصة، الكود كان هيدخل مسار `except Exception` (سطر 205-219 من `ai_agents/service.py`)، يسجّل `task_type="ERROR"`، ويعيد رفع (`raise`) الاستثناء — بالظبط السلوك الموثَّق سابقًا في `ai-agents-execute-action-fix-session-log.md` وبند #7 في `PROGRESS_LOG.md`. **النتيجة هنا تثبت إن هذا المسار لم يُنفَّذ إطلاقًا.**

**تنظيف + تحقق مستقل بعد الحذف (خارج السكريبت الأصلي، استعلامات منفصلة تمامًا):**
- `SELECT` مستقل على `users`/`ai_agents`/`ai_task_logs`/`agent_approval_queue` بـ`id`/`agent_id` المحدَّدين → **كل النتائج فارغة** (`None`/`[]`) — صفر أثر متبقٍ.
- `SELECT` مستقل على `finance.Wallet` بـ`user_id=313` → **`[]`** (صفر محفظة يتيمة).
- `redis-cli KEYS "ai:cost:*"` مستقل (docker `redis`) → **صفر نتائج** — كل مفاتيح التكلفة (`hunyuan-mt-7b`, `mistral-saba`, وتنظيف احترازي لباقي الموديلات الأربعة المحتملة) اتحذفت بالكامل، صفر أثر على عدادات التكلفة الحقيقية.

**✅ خلاصة قاطعة: `execute_agent_action` (أخطر موضع متأثر بـ#7) شغّالة فعليًا الآن بالكامل، ومسار `/api/ai/chat` العام (`main.py:356`) شغّال فعليًا كمان — الاتنين بنداء حقيقي غير مُعدَّل، صفر `monkeypatch`، صفر أثر جانبي متبقٍ.**

---

## 10. حالة الجلسة الآن: تنفيذ + تحقق حي مكتملان — بانتظار موافقتك قبل الـregression test النهائي والـcommit

طبقًا لتعليماتك الصريحة: **توقفت هنا.** لسه ماكتبتش `tests/test_redis_client_wrapper_missing_methods.py` ولا README المخصَّص جنبه، ولا عملت أي `git add`/`commit`.

**ملخص الحالة:**
- ✅ الست methods مُضافة في `app/core/redis_client.py` (§7).
- ✅ تحقق حي مباشر للست methods بأدوات تحقق مستقلة (§8) — كله PASS.
- ✅ تحقق حي حاسم لـ`execute_agent_action` (بلا `monkeypatch`) + مسار `main.py:356` العام (§9) — كله PASS، مع تحقق مستقل إضافي (SELECT/redis-cli) يثبت صفر أثر جانبي متبقٍ.
- ✅ `PROGRESS_LOG.md` محدَّث ببند Backlog جديد منفصل (`agritech-redis-calls-missing-await-orphaned-coroutines`) — صفر لمس على `agritech.py` نفسه.
- ⏳ **التالي (بانتظار موافقتك):** كتابة `tests/test_redis_client_wrapper_missing_methods.py` + README مخصَّص، ثم تحديث `PROGRESS_LOG.md` (إغلاق بند #7 رسميًا)، ثم `git commit` واحد معزول.

---

## 11. اكتمال المرحلة الأخيرة [2026-08-19]

- ✅ **`tests/test_redis_client_wrapper_missing_methods.py`** — 6 اختبارات (واحد لكل method)، كل واحد بتحقق مستقل (HGET/LRANGE/GET/subscriber منفصل عبر `await redis_client.get_client()`)، مش مجرد "صفر استثناء". **تشغيلتان متتاليتان: 6 passed في الاثنتين، صفر تذبذب.** اكتشاف صغير أثناء الكتابة: اختبار `pubsub` احتاج نداء صريح `await redis_client.get_client()` في أوله (بيحاكي ترتيب تهيئة `lifespan` الحقيقي) لأن `fixture` التنظيف (`_redis_event_loop_isolation`) بتقفل `_client` بعد كل اختبار، و`pubsub()` (متزامنة) مش بتعمل lazy-init زي باقي الـmethods — بعد الإصلاح، الاختبار عدّى بلا مشاكل.
- ✅ **`tests/test_redis_client_wrapper_missing_methods.md`** — README مخصَّص، نفس نمط `test_eventbus_publish_fix.md` بالحرف.
- ✅ **تحقق مستقل إضافي بعد التشغيلتين:** `redis-cli KEYS "REGTEST:redis-wrapper-methods:*"` → صفر نتائج (صفر مفاتيح يتيمة).
- ✅ **`PROGRESS_LOG.md`** — تحديث بند #7 في جدول الـBacklog (إغلاق رسمي، تفصيل كامل)، إضافة سطر في "الجلسات المُقفلة"، وتحديث بانر الحالة العلوي ليعكس هذه الجلسة كآخر إغلاق رسمي (مع نقل بانر #16 لتصنيف "إغلاق سابق ذو صلة").
- ⏳ **التالي:** عرض `git status` نهائي على المستخدم، ثم `commit` واحد معزول عند التأكيد.
