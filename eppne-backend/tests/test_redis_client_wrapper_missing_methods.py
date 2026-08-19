"""
regression test لجلسة `redis-client-wrapper-missing-methods` (المرحلة 1.4، Backlog #7).
تقرير الجلسة الأصلية: .claude/reports/redis-client-wrapper-missing-methods-session-log.md

السبب الجذري (كان): `RedisClientWrapper` (`app/core/redis_client.py`) لم تكن
تملك ستة methods: `hincrbyfloat`, `hgetall`, `lpush`, `ltrim`, `setnx`
(الخمسة الأولى + `setnx` مذكورة في `PROGRESS_LOG.md` منذ بداية بند #7 نفسه)،
و`pubsub` (من الخمسة الأصليًا المُعلَنة في تعليمات هذه الجلسة). أي كود
حقيقي بينادي أي واحدة منهم على الـSingleton كان بيرمي `AttributeError`
فورًا. **الأثر الأخطر المؤكَّد حيًا:** `CostTracker.record_usage()`
(`app/services/ai/cost_tracker.py`) بتنادي `hincrbyfloat`/`hgetall` —
وهي تُستدعى من `AIEngine.generate()` بلا أي `try/except`، يعني **أي نجاح
لأي استدعاء AI عبر المنصة بالكامل** (مش بس `AIAgentsService.execute_agent_action`
كما كان مفترضًا أصلًا في `PROGRESS_LOG.md` — نطاق الأثر اتّضح إنه أوسع أثناء
تشخيص هذه الجلسة: أي مسار آخر بينادي `ai_engine.generate()`، مؤكَّد بالقراءة
المباشرة أن `app/main.py:356` [`POST /api/ai/chat`] مسار مستقل تمامًا عن
`ai_agents` كان متأثرًا بنفس الباج بالضبط) كان بيتحطم بـ`AttributeError`.

الإصلاح المُطبَّق (`app/core/redis_client.py`، إضافة صرفة، صفر لمس لأي
ملف مستدعٍ):
```python
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
    # الحقيقية (لا تنفّذ I/O، فقط تُنشئ كائن PubSub). تعتمد على initialize()
    # اللي بتتنادى فعليًا في lifespan (main.py) قبل خدمة أي طلب.
    if self._client is None:
        raise RuntimeError(...)
    return self._client.pubsub()
```
`pubsub()` هي أول method متزامنة في الكلاس (الخمسة الباقية بنفس نمط
`async def ... client = await self.get_client() ...` الموحَّد). التصميم
هذا **مؤكَّد بدليلين حيّين مستقلين** بيستدعوا `.pubsub()` بلا `await`
(`app/domains/communications/router.py:48`، endpoint حي مفعَّل
`/communications/ws`، و`app/core/event_bus.py:44` داخل `EventBus.listen()`).

هذا الملف يعيد إنتاج التحقق الحي الموثَّق في قسم 8 من التقرير الأصلي —
لكل method: نداء عبر `RedisClientWrapper` (الكائن قيد الاختبار) + **تحقق
مستقل** عبر عميل Redis خام منفصل (`await redis_client.get_client()`، بلا
مرور عبر أي method جديدة) — نفس معيار جلسة `eventbus-publish-fix`. صفر
اعتماد على "صفر استثناء" وحدها كإثبات.

**بيانات throwaway:** صفر صفوف DB (الملف بيختبر Redis فقط). كل اختبار
بيستخدم مفتاح/قناة فريدة ببادئة `REGTEST:redis-wrapper-methods:` +
`uuid4` — صفر تصادم بين تشغيلات، وحذف صريح (`redis_client.delete`) في
`finally`/نهاية كل اختبار.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio

from app.core.redis_client import redis_client

PREFIX = "REGTEST:redis-wrapper-methods:"


@pytest_asyncio.fixture(autouse=True)
async def _redis_event_loop_isolation():
    """يقفل اتصال redis_client (الـSingleton) بعد كل اختبار — نفس احتياط
    fixture مطابقة في test_eventbus_publish_fix.py: pytest-asyncio بيفتح
    event loop جديد لكل test function على ويندوز، لكن redis_client عالمي
    بيحتفظ باتصال من الـloop السابق. بلا هذا التنظيف، أول استخدام لـ
    redis_client في أي اختبار بعد الأول بيكراش بـ`RuntimeError: Event loop is closed`."""
    yield
    await redis_client.close()


def _key(name: str) -> str:
    return f"{PREFIX}{name}:{uuid.uuid4().hex[:10]}"


# ============================================================
# 1) hincrbyfloat — نفس استخدام cost_tracker.py:65-77 (تراكم تكلفة AI)
# ============================================================

@pytest.mark.asyncio
async def test_hincrbyfloat_accumulates_and_matches_independent_hget():
    client = await redis_client.get_client()
    key = _key("hincrbyfloat")
    try:
        r1 = await redis_client.hincrbyfloat(key, "total_cost", 1.5)
        r2 = await redis_client.hincrbyfloat(key, "total_cost", 2.25)
        assert r1 == 1.5
        assert r2 == 3.75

        independent = await client.hget(key, "total_cost")
        assert independent is not None
        assert float(independent) == 3.75, (
            "HGET مستقل لم يطابق التراكم المتوقَّع — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (hincrbyfloat)"
        )
    finally:
        await redis_client.delete(key)


# ============================================================
# 2) hgetall — نفس استخدام cost_tracker.py:91,113,126 (قراءة إجمالي التكلفة)
# ============================================================

@pytest.mark.asyncio
async def test_hgetall_returns_all_fields_matching_independent_write():
    client = await redis_client.get_client()
    key = _key("hgetall")
    try:
        await client.hset(key, mapping={"a": "1", "b": "2", "c": "3"})
        data = await redis_client.hgetall(key)
        assert data == {"a": "1", "b": "2", "c": "3"}, (
            "hgetall لم يرجع كل الحقول المكتوبة مستقلًا — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (hgetall)"
        )
    finally:
        await redis_client.delete(key)


# ============================================================
# 3) lpush — نفس استخدام cache.py:117 (BatchProcessor.add_to_batch)
# ============================================================

@pytest.mark.asyncio
async def test_lpush_prepends_values_matching_independent_lrange():
    client = await redis_client.get_client()
    key = _key("lpush")
    try:
        await redis_client.lpush(key, "v1")
        await redis_client.lpush(key, "v2", "v3")

        independent_range = await client.lrange(key, 0, -1)
        assert independent_range == ["v3", "v2", "v1"], (
            "LRANGE مستقل لم يطابق ترتيب LPUSH المتوقَّع — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (lpush)"
        )
    finally:
        await redis_client.delete(key)


# ============================================================
# 4) ltrim — صفر استخدام حي على الـwrapper نفسه اليوم (مؤكَّد بالـgrep في
#    التقرير الأصلي §2.4)؛ التوقيع مبني على نمط LTRIM القياسي + قرار مستخدم
#    صريح بإضافتها استباقيًا. الاختبار هنا هو أول دليل استخدام حقيقي لها.
# ============================================================

@pytest.mark.asyncio
async def test_ltrim_keeps_only_range_matching_independent_lrange():
    client = await redis_client.get_client()
    key = _key("ltrim")
    try:
        for v in ["a", "b", "c", "d", "e"]:
            await client.rpush(key, v)

        before = await client.lrange(key, 0, -1)
        assert before == ["a", "b", "c", "d", "e"]

        await redis_client.ltrim(key, 0, 2)

        after = await client.lrange(key, 0, -1)
        assert after == ["a", "b", "c"], (
            "LRANGE مستقل بعد LTRIM لم يطابق النطاق المتوقَّع — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (ltrim)"
        )
    finally:
        await redis_client.delete(key)


# ============================================================
# 5) setnx — نفس استخدام projects/service.py:157 (add_contribution، قفل idempotency)
# ============================================================

@pytest.mark.asyncio
async def test_setnx_first_wins_second_rejected_matching_independent_get():
    client = await redis_client.get_client()
    key = _key("setnx")
    try:
        first = await redis_client.setnx(key, "first-value")
        second = await redis_client.setnx(key, "second-value")

        assert first is True
        assert second is False

        independent_get = await client.get(key)
        assert independent_get == "first-value", (
            "GET مستقل لم يطابق القيمة الأولى المتوقَّعة — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (setnx)"
        )
    finally:
        await redis_client.delete(key)


# ============================================================
# 6) pubsub — نفس اتفاقية النداء المتزامن في communications/router.py:48
#    و event_bus.py:44 (بلا await على pubsub() نفسها)
# ============================================================

@pytest.mark.asyncio
async def test_pubsub_sync_call_delivers_message_to_independent_subscriber():
    channel = _key("pubsub")

    # في التطبيق الحقيقي، lifespan (main.py:79) بينادي `await redis_client.initialize()`
    # مرة واحدة قبل خدمة أي طلب، فـ`_client` دايمًا موجودة وقت ما أي endpoint
    # بينادي `pubsub()` المتزامنة. هنا بنحاكي نفس الترتيب صراحة (بدل الاعتماد على
    # ترتيب تشغيل الاختبارات التانية في نفس الملف).
    await redis_client.get_client()

    # نفس الاتفاقية الحرفية المستخدَمة في الكودين الحقيقيين: بلا await هنا
    subscriber = redis_client.pubsub()
    assert not asyncio.iscoroutine(subscriber), (
        "redis_client.pubsub() رجعت coroutine بدل كائن PubSub مباشر — "
        "هذا يكسر كل الاستدعاءات الحقيقية الحية اللي بتستدعيها بلا await"
    )

    try:
        await subscriber.subscribe(channel)
        # استهلاك رسالة تأكيد الاشتراك
        confirm = await subscriber.get_message(timeout=2.0)
        assert confirm is not None and confirm["type"] == "subscribe"

        await redis_client.publish(channel, "hello-from-regtest")

        msg = await subscriber.get_message(timeout=3.0, ignore_subscribe_messages=True)
        assert msg is not None and msg["type"] == "message", (
            "subscriber مستقل لم يستلم الرسالة — رجوع محتمل لباج "
            "redis-client-wrapper-missing-methods (pubsub)"
        )
        assert msg["data"] == "hello-from-regtest"
    finally:
        await subscriber.unsubscribe(channel)
        await subscriber.aclose()
