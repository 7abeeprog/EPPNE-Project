# `test_eventbus_publish_fix.py`

## المرجع الأصلي
- `.claude/reports/eventbus-publish-fix-session-log.md` (المرحلة 1.1، جلسة `eventbus-redis-wrapper-publish-fix`).

## السبب الجذري (كان) — ملخص
`RedisClientWrapper` (`app/core/redis_client.py`) ما كانتش تملك method اسمها `publish()`. `EventBus.publish()` بتنادي `await self.redis.publish(channel, message)`، و`self.redis` هو نفس الـSingleton `RedisClientWrapper` في **22 دومين من 23** بيستخدموا `EventBus` (`finance` وحدها كانت صحيحة أصلًا، بتستخدم عميل `redis.asyncio.Redis` خام مباشر). أي نشر حدث حقيقي عبر الـ22 دومين كان بيرمي `AttributeError: 'RedisClientWrapper' object has no attribute 'publish'` فورًا.

## الإصلاح المُطبَّق
```python
# app/core/redis_client.py — إضافة صرفة، 5 أسطر
async def publish(self, channel: str, message: str):
    client = await self.get_client()
    return await client.publish(channel, message)
```
نفس نمط باقي الاختصارات الموجودة أصلًا في نفس الكلاس (`ping`, `get`, `setex`, ...). صفر لمس على `EventBus` نفسها أو أي ملف دومين.

## إيه اللي بيتحقق منه هذا الملف
4 اختبارات — **الثلاثة دومينات المُتحقَّق منهم حيًا في الجلسة الأصلية بالكامل** (مش عيّنة واحدة فقط)، زائد اختبار مباشر على الطبقة السفلى نفسها:

| # | الاختبار | ما بيثبته |
|---|---|---|
| 1 | `test_redis_client_wrapper_publish_reaches_independent_subscriber` | `RedisClientWrapper.publish()` نفسها (الإصلاح الفعلي، 5 أسطر) — بمعزل عن `EventBus` |
| 2 | `test_insurance_eventbus_publish_reaches_independent_subscriber` | `EventBus(cast(Any, redis_client))` — نفس نمط `insurance/service.py:35`، حدث `insurance.subscription.created` |
| 3 | `test_zamakana_eventbus_publish_reaches_independent_subscriber` | نفس النمط — `zamakana/service.py:41`، حدث `zamakana.node.created` |
| 4 | `test_arbitration_syndicates_eventbus_publish_reaches_independent_subscriber` | `EventBus(redis_client)  # type: ignore` — نمط بناء نصي مختلف (`arbitration_syndicates/service.py:33`)، حدث `arbitration.case.created` |

**منهجية موحَّدة (مطابقة لقسم 7 من التقرير الأصلي حرفيًا):** كل اختبار بيفتح **subscriber مستقل تمامًا** عن أداة النشر قيد الاختبار (اتصال Redis خام منفصل عبر `pubsub()` مباشرة، مش عبر `EventBus`/`redis_client` نفسها)، بينفذ النشر، وبيتأكد من استلام الرسالة فعليًا على القناة (`events:<event_name>`) مع **تطابق كامل 1:1** لمحتوى `event`/`payload` — مش مجرد "صفر استثناء" (الإثبات الأضعف اللي التقرير الأصلي رفضه صراحة).

## بيانات throwaway
- **صفر صفوف DB** — الملف بيختبر Redis pub/sub فقط، صفر اعتماد على `tenant_id`/بيانات تطبيقية حقيقية.
- كل اختبار بيستخدم `marker`/قناة فريدة (`uuid4`) — صفر تصادم بين تشغيلات.
- التنظيف (`unsubscribe` + `close()` على اتصال الـsubscriber المستقل) في `finally` بعد كل اختبار.
- `fixture` مساعدة (`_redis_event_loop_isolation`, `autouse=True`) بتقفل `redis_client` الـSingleton بعد كل اختبار — احتياط ضروري على ويندوز (نفس نمط `db` fixture في `conftest.py`): `pytest-asyncio` بيفتح event loop جديد لكل اختبار، لكن `redis_client` عالمي بيحتفظ باتصال من الـloop السابق؛ بلا هذا التنظيف، الاختبار التاني بيكراش بـ`RuntimeError: Event loop is closed`.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_eventbus_publish_fix.py -v
```
يحتاج Redis حقيقي شغّال (`docker` container `redis`, بورت مضيف 6380، مطابق لـ`REDIS_URL` في `.env`).

**آخر تشغيل مُوثَّق [2026-08-19]:** 4 passed (تشغيلتان متتاليتان، صفر تذبذب).
