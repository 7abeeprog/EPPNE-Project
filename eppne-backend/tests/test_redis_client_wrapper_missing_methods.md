# `test_redis_client_wrapper_missing_methods.py`

## المرجع الأصلي
- `.claude/plans/redis-client-wrapper-missing-methods-session-instructions.md` (تعليمات الجلسة).
- `.claude/reports/redis-client-wrapper-missing-methods-session-log.md` (المرحلة 1.4، Backlog #7).

## السبب الجذري (كان) — ملخص
`RedisClientWrapper` (`app/core/redis_client.py`) لم تكن تملك ستة methods: `hincrbyfloat`, `hgetall`, `lpush`, `ltrim`, `setnx`, `pubsub`. أي كود حقيقي بينادي أي واحدة منهم على الـSingleton كان بيرمي `AttributeError` فورًا.

**الأثر الأخطر المؤكَّد حيًا:** `CostTracker.record_usage()` (`app/services/ai/cost_tracker.py`) بتنادي `hincrbyfloat`/`hgetall`، وهي تُستدعى من `AIEngine.generate()` بلا أي `try/except`. **نطاق الأثر اتّضح إنه أوسع من الموصوف أصلًا في `PROGRESS_LOG.md`** (اللي كان بيصف الأثر كـ"يُسقط `execute_agent_action`" فقط): أي مسار آخر بينادي `ai_engine.generate()` متأثر بنفس الباج بالضبط — مؤكَّد بالقراءة المباشرة إن `app/main.py:356` (`POST /api/ai/chat`) endpoint مستقل تمامًا عن `ai_agents` كان بيتحطم بنفس `AttributeError`.

**نطاق `setnx`/`pubsub`:** الخمسة الأصليًا المُعلَنة في تعليمات الجلسة كانت `hincrbyfloat, pubsub, lpush, ltrim, hgetall`. أثناء التشخيص تبيَّن إن `setnx` موثَّقة أصلًا كجزء من بند #7 نفسه في `PROGRESS_LOG.md` (منذ إنشائه، مع `hincrbyfloat`) ولها استخدام حي مكسور فعليًا في `app/domains/projects/service.py:157` (`add_contribution`، قفل idempotency) — بموافقة صريحة من المستخدم، أُضيفت ضمن نطاق هذه الجلسة.

## الإصلاح المُطبَّق
```python
# app/core/redis_client.py — إضافة صرفة، صفر لمس لأي ملف مستدعٍ
async def hincrbyfloat(self, key: str, field: str, amount):
    client = await self.get_client()
    return await client.hincrbyfloat(key, field, amount)

async def hgetall(self, key: str):
    client = await self.get_client()
    return await client.hgetall(key)

async def lpush(self, key: str, *values):
    client = await self.get_client()
    return await client.lpush(key, *values)

async def ltrim(self, key: str, start: int, end: int):
    client = await self.get_client()
    return await client.ltrim(key, start, end)

async def setnx(self, key: str, value: str):
    client = await self.get_client()
    return await client.setnx(key, value)

def pubsub(self):
    # متزامنة عمدًا (بلا async/await) -- مطابقة لسلوك redis.asyncio.Redis.pubsub()
    # الحقيقية (لا تنفّذ I/O، فقط تُنشئ كائن PubSub).
    if self._client is None:
        raise RuntimeError(...)
    return self._client.pubsub()
```

`pubsub()` هي **أول method متزامنة في الكلاس** (الخمسة الباقية بنفس نمط `async def ... client = await self.get_client() ...` الموحَّد لباقي الـwrapper). القرار مبني على دليلين حيّين مستقلين بيستدعوا `.pubsub()` **بلا `await`**: `app/domains/communications/router.py:48` (endpoint حي مفعَّل `/communications/ws`) و`app/core/event_bus.py:44` (داخل `EventBus.listen()`، غير مُستدعاة حاليًا من أي مكان لكن نفس العقد). تعتمد على أن `main.py:79` بينادي `await redis_client.initialize()` في الـ`lifespan` **قبل** خدمة أي طلب — مؤكَّد بالقراءة المباشرة.

## إيه اللي بيتحقق منه هذا الملف

6 اختبارات — كل الست methods المُضافة، بنفس منهجية "تحقق مستقل" (§8 من التقرير الأصلي):

| # | الاختبار | ما بيثبته | مصدر التوقيع الحقيقي |
|---|---|---|---|
| 1 | `test_hincrbyfloat_accumulates_and_matches_independent_hget` | تراكمان متتاليان، ثم `HGET` مستقل (عميل خام مختلف) يطابق المجموع (1.5+2.25=3.75) | `cost_tracker.py:65-77` |
| 2 | `test_hgetall_returns_all_fields_matching_independent_write` | `HSET` مستقل مسبق، ثم `hgetall()` يرجّع كل الحقول بتطابق كامل | `cost_tracker.py:91,113,126` |
| 3 | `test_lpush_prepends_values_matching_independent_lrange` | `lpush()` مرتين (قيمة واحدة ثم قيمتين)، `LRANGE` مستقل يطابق ترتيب LPUSH الصحيح | `cache.py:117` (`BatchProcessor.add_to_batch`) |
| 4 | `test_ltrim_keeps_only_range_matching_independent_lrange` | 5 عناصر عبر `RPUSH` مستقل، `ltrim(0,2)`، `LRANGE` مستقل يطابق النطاق المتبقي | **صفر استخدام حي على الـwrapper نفسه اليوم** (مؤكَّد بالـgrep الشامل) — توقيع استباقي بقرار مستخدم صريح، هذا الاختبار أول دليل استخدام حقيقي لها |
| 5 | `test_setnx_first_wins_second_rejected_matching_independent_get` | أول `setnx` ينجح، الثاني يُرفض، `GET` مستقل يطابق القيمة الأولى فقط | `projects/service.py:157` (`add_contribution`) |
| 6 | `test_pubsub_sync_call_delivers_message_to_independent_subscriber` | `pubsub()` بلا `await` (نفس الاتفاقية الحرفية الحقيقية) ترجع كائن `PubSub` مباشر (مش coroutine)، subscriber مستقل يستلم رسالة `publish()` فعلية | `communications/router.py:48` + `event_bus.py:44` |

**منهجية موحَّدة:** كل اختبار بينادي الـmethod الجديدة على `redis_client` (الكائن قيد الاختبار)، ثم بيتأكد بأداة **مستقلة تمامًا** (عميل Redis خام عبر `await redis_client.get_client()`، بلا مرور عبر أي method جديدة) — مش مجرد "صفر استثناء". اختبار `pubsub` كمان بيتأكد صراحة إن القيمة الراجعة **مش coroutine** (`asyncio.iscoroutine(subscriber)` لازم تكون `False`) — تأكيد مباشر على القرار المعماري (method متزامنة).

## بيانات throwaway
- **صفر صفوف DB** — الملف بيختبر Redis فقط.
- كل اختبار بيستخدم مفتاح/قناة فريدة ببادئة `REGTEST:redis-wrapper-methods:` + `uuid4` — صفر تصادم بين تشغيلات.
- حذف صريح (`redis_client.delete(key)` في `finally`) بعد كل اختبار، أو `unsubscribe`/`aclose()` لاختبار `pubsub`.
- `fixture` مساعدة (`_redis_event_loop_isolation`, `autouse=True`) بتقفل `redis_client` الـSingleton بعد كل اختبار — نفس نمط `test_eventbus_publish_fix.py` بالحرف (احتياط ضروري على ويندوز لتفادي `RuntimeError: Event loop is closed`).
- اختبار `pubsub` تحديدًا بينادي `await redis_client.get_client()` صراحة في أوله قبل `pubsub()` — بيحاكي ترتيب التهيئة الحقيقي (`lifespan` بينادي `initialize()` قبل أي طلب) بدل الاعتماد على ترتيب تشغيل الاختبارات التانية في نفس الملف لتهيئة `_client` ضمنيًا.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_redis_client_wrapper_missing_methods.py -v
```
يحتاج Redis حقيقي شغّال (`docker` container `redis`, بورت مضيف 6380، مطابق لـ`REDIS_URL` في `.env`).

**آخر تشغيل مُوثَّق [2026-08-19]:** 6 passed (تشغيلتان متتاليتان، صفر تذبذب). تحقق مستقل إضافي بعد التشغيلتين (`redis-cli KEYS "REGTEST:redis-wrapper-methods:*"`) أكَّد **صفر مفاتيح يتيمة متبقية**.
