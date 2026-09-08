# جلسة: redis-celery-port-mismatch-investigation

**تاريخ:** 2026-09-07
**النوع:** فحص read-only بحت — **صفر تعديل كود**. لا `Edit`/`Write` على أي ملف مصدر أو `.env` في هذه الجلسة (تأكيد أدناه في القسم 6).
**الهدف:** فهم كامل لمشكلة Redis/Celery port mismatch المذكورة في `PROGRESS_LOG.md` (البند 3 تحت "4 بنود backlog اتكشفوا اليوم"، سطر 2160) و`.claude/reports/can-access-service-unification-session-log.md` (§7) قبل أي إصلاح.

---

## ملخص تنفيذي (أهم اكتشاف)

الفرضية الموروثة من الجلسة السابقة كانت: *"`REDIS_URL` صح (6380)، لكن `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` غلط (6379)"*. هذه الفرضية **غير دقيقة** — تحقّقتُ بالكود الفعلي وبتجربة حية:

- `CELERY_BROKER_URL` و`CELERY_RESULT_BACKEND` **متغيّران ميتان تمامًا (dead config)** — لا يقرأهما أي سطر كود في المشروع كله. `celery_app.py` يستخدم `settings.REDIS_URL` حصريًا لكلٍّ من الـbroker والـbackend (سطر 16-17).
- السبب الجذري الحقيقي: **قراءة `.env` بتعتمد على working directory** وقت تشغيل العملية. يوجد ملفان `.env` في المشروع بقيم `REDIS_URL` متضاربة فعليًا:
  - `E:\cc\.env` (الجذر) → `REDIS_URL=redis://localhost:6379/0` (بورت غلط، **بلا كلمة سر أصلًا**) — قديم/متروك.
  - `E:\cc\eppne-backend\.env` → `REDIS_URL=redis://:...@127.0.0.1:6380/0` (صحيح، مطابق لحاوية Docker الفعلية).
- **جرّبتُ الاثنين فعليًا** (قسم 5): لو العملية اتشغّلت بـ`cwd=eppne-backend` (الوضع الطبيعي لـ`uvicorn`/`pytest` في كل الجلسات الموثَّقة سابقًا) → `settings.REDIS_URL` يرجع 6380 **الصحيح**، والاتصال الفعلي بـRedis بـ`PING` نجح (`True`). لو اتشغّلت بـ`cwd=E:\cc` (جذر الريبو) → `settings.REDIS_URL` يرجع 6379 الغلط، والاتصال يفشل فورًا بنفس الخطأ الحرفي الموثَّق في الجلسة السابقة (`Error 10061 ... actively refused it`).
- يعني: **مفيش تناقض CELERY_* حقيقي مؤثِّر في الكود** — المشكلة الفعلية أعمق وأخطر: نسخة `.env` القديمة على الجذر (بدون باسورد، وببورت غلط) بتتحمّل كأولوية لو حد شغّل أي سكريبت/عملية من جذر الريبو بدل `eppne-backend/`.

---

## 1. محتوى `.env` كامل (كل الأسطر المتعلقة بـRedis/Celery)

### 1.1 `E:\cc\.env` (جذر الريبو)

```
# ---------- Redis ----------
REDIS_URL=redis://localhost:6379/0
```

سطر واحد فقط متعلق بـRedis. **لا يوجد** `CELERY_BROKER_URL` ولا `CELERY_RESULT_BACKEND` ولا `REDIS_PASSWORD` ولا `REDIS_PORT` في هذا الملف إطلاقًا. لاحظ: بلا كلمة سر — حتى لو البورت كان صح، الاتصال بحاوية Redis الفعلية (اللي عليها `--requirepass`) كان هيفشل بـ`NOAUTH Authentication required`.

### 1.2 `E:\cc\eppne-backend\.env`

```
REDIS_PASSWORD=***REDACTED***
REDIS_PORT=6379

# 🔥 رابط Redis (تم التصحيح باستخدام 127.0.0.1)
REDIS_URL=redis://:***REDACTED***@127.0.0.1:6380/0

CELERY_BROKER_URL=redis://:***REDACTED***@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:***REDACTED***@127.0.0.1:6379/1
```

ملاحظات على هذا الملف نفسه (بمعزل عن أي ملف تاني):
- `REDIS_URL` = بورت **6380** (صحيح، مُصحَّح يدويًا حسب التعليق العربي فوقه).
- `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` = بورت **6379** (غلط — ولم يُصحَّحا رغم تعليق "تم التصحيح" فوق `REDIS_URL` مباشرة، ما يوحي إن التصحيح طبّق على `REDIS_URL` فقط ونُسي الاثنين التانيين).
- `REDIS_PORT=6379` — متغيّر بيُستخدم فقط في `docker-compose.yml` لتحديد **بورت الاستضافة (host mapping)** لخدمة `eppne_redis` (التي عرّفها docker-compose نفسه)، مش لحاوية Redis الفعلية الشغّالة حاليًا (قسم 2). القيمة دي بالذات غير مستخدَمة في أي كود بايثون.

---

## 2. `docker-compose.yml` مقابل الحاوية الفعلية الشغّالة (`docker ps`)

**الملف** (`eppne-backend/docker-compose.yml`, خدمة `redis`, سطر 65-88):
```yaml
redis:
  image: redis:7-alpine
  container_name: eppne_redis
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} ...
  ports:
    - "${REDIS_PORT:-6379}:6379"
```
لو اتشغّل هذا الملف كما هو (`REDIS_PORT=6379` من `.env`)، هيطلع حاوية اسمها `eppne_redis` مبنّتة `6379:6379`.

**لكن `docker ps -a` الفعلي الآن:**
```
NAMES            IMAGE                PORTS                                         STATUS
eppne_db         postgres:16          0.0.0.0:5435->5432/tcp                        Up 2 weeks (healthy)
postgres-eppne   postgres:15-alpine   0.0.0.0:5433->5432/tcp                        Up 2 weeks
redis            redis                0.0.0.0:6380->6379/tcp                        Up 2 weeks
```

**مفيش `eppne_redis` (خدمة docker-compose) شغّالة إطلاقًا.** الحاوية الشغّالة اسمها `redis` (بلا بادئة `eppne_`)، `docker inspect redis` بيأكّد:
- **بلا `com.docker.compose.project` label** → اتشغّلت بـ`docker run` يدوي، مش عبر `docker-compose up`.
- `Cmd: [--requirepass ***REDACTED***]` → نفس الباسورد الموجود في `eppne-backend/.env`.
- Port mapping: `6379/tcp → HostPort 6380` (تأكيد: الحاوية بتستمع داخليًا على 6379 الافتراضي، لكن مبنّتة على بورت 6380 على الجهاز المضيف).
- `docker exec redis redis-cli -a "***REDACTED***" ping` → `PONG` (الحاوية سليمة وبتشتغل بهذا الباسورد بالذات).
- `Get-NetTCPConnection -LocalPort 6379,6380 -State Listen` → **بورت 6380 فقط هو المستمع فعليًا على الجهاز**. مفيش أي حاجة تستمع على 6379.

**الخلاصة:** الحاوية الفعلية الوحيدة الشغّالة اتعملها `docker run` منفصل تمامًا عن `docker-compose.yml` بتاع المشروع (ملف compose نفسه — بخدماته `backend`/`worker`/`flower` — مش شغّال إطلاقًا حاليًا، صفر container من الـ8 خدمات المعرَّفة فيه ما عدا `postgres`/`redis` اللي حد شغّلهم يدويًا بأسماء/بورتات مختلفة عن المُعرَّف في الملف).

---

## 3. Grep شامل: كل مكان بيقرأ `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` مباشرة في الكود

بحث على مستوى الريبو كله (باستثناء `venv/`, `node_modules/`, `.git/`, `__pycache__/`) عن `REDIS_URL|CELERY_BROKER_URL|CELERY_RESULT_BACKEND|6379|6380` — 31 ملف طابق، بعد استبعاد التقارير/التوثيق/الاختبارات النصية، الملفات الفعلية ذات الصلة:

| الملف | الاستخدام |
|---|---|
| `app/core/config.py:70-72` | تعريف حقل `REDIS_URL: str` في `Settings` (pydantic), افتراضي `redis://localhost:6379/0` لو الحقل غير موجود إطلاقًا في أي مصدر. |
| `app/core/celery_app.py:16-17` | `Celery("eppne_worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)` — **المصدر الوحيد الفعلي** لبروكر/باكند Celery للتطبيق بالكامل. |
| `app/core/redis_client.py:33` | `getattr(settings, "REDIS_URL", "redis://localhost:6379/0")` — نفس النمط، احتياطي دفاعي بحت (الحقل موجود دايمًا فعليًا فمفيش سيناريو بيفعّل هذا الافتراضي). |
| `app/core/event_bus.py:20` | `Redis.from_url(settings.REDIS_URL)`. |
| `app/domains/communications/tasks.py:7` | `Celery("communications", broker=settings.REDIS_URL)` — تطبيق Celery **ثانٍ منفصل** لكنه بردو بيستخدم `settings.REDIS_URL` نفسه، مش `CELERY_BROKER_URL`. |
| `app/core/celery_config.py` | إعدادات طوابير/routing/beat schedule فقط (`config_from_object`) — **لا يحتوي أي تعريف broker/backend** يقدر يجاوز القيمة أعلاه. |
| `docker-compose.yml` (سطور 188, 231, 265) | يبني `REDIS_URL` بنفسه من `${REDIS_PASSWORD}`+`${REDIS_PORT:-6379}` لخدمات `backend`/`worker`/`flower` — **لا يستخدم `CELERY_BROKER_URL` من `.env` إطلاقًا هو كمان**. |

**تأكيد صريح:** لا يوجد أي سطر كود بايثون واحد (خارج ملفات Celery الداخلية نفسها تحت `venv/`) يقرأ `CELERY_BROKER_URL` أو `CELERY_RESULT_BACKEND` من `settings` أو `os.environ`. الاستخدام الوحيد لهذين الاسمين هو داخل مكتبة Celery نفسها (`venv/Lib/site-packages/celery/app/utils.py:103,110-111`) كـ**احتياطي داخلي لمكتبة Celery** يُستخدم فقط لو التطبيق اتعمل `Celery()` **بدون** تمرير `broker=`/`backend=` صراحةً — وهو ليس الحال هنا (`celery_app.py` بيمرّرهم صراحةً)، فهذا الاحتياطي لا يتفعّل أبدًا في هذا المشروع.

**النتيجة:** `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` في `.env` **قيم ميتة بالكامل** — تصحيحهم لن يغيّر أي سلوك فعلي، لأن ولا سطر كود بيقرأهم.

---

## 4. هل حاليًا في fallback/retry بيغطي المشكلة، ولا كل استخدام فعلي بيفشل؟

### 4.1 `celery -A app.core.celery_app inspect ping` (من `cwd=eppne-backend`)
نفّذته فعليًا (`timeout=5`) → **انتهت المهلة (exit 124)**، بدون أي رد. هذا **ليس فشل اتصال بالبروكر** (لو كان الاتصال فشل كان هيرجع خطأ فورًا) — بل معناه: الاتصال بالبروكر (6380) نجح والرسالة اتبعتت، لكن **لا يوجد أي Celery worker فعلي شغّال حاليًا** على الجهاز يرد على `inspect ping` (تأكيد إضافي: `docker ps` ما فيهاش container اسمه `eppne_worker`، وكل الجلسات الموثَّقة سابقًا شغّلت `uvicorn app.main:app` فقط، ولا جلسة شغّلت `celery worker` فعليًا).

### 4.2 اختبار اتصال مباشر بـ`redis-py` باستخدام `settings.REDIS_URL` الفعلي — بالتجربة الحية

**من `cwd=E:\cc\eppne-backend`** (الوضع الطبيعي لكل الجلسات الموثَّقة سابقًا التي شغّلت `uvicorn`):
```
settings.REDIS_URL = redis://:***REDACTED***@127.0.0.1:6380/0
PING result: True
```
✅ **يعمل فعليًا** — لا مشكلة إطلاقًا في هذا السيناريو.

**من `cwd=E:\cc`** (جذر الريبو):
```
settings.REDIS_URL = redis://localhost:6379/0
FAILED: ConnectionError Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```
❌ **فشل فوري متطابق حرفيًا** مع الخطأ الموثَّق سابقًا في `can-access-service-unification-session-log.md` §7 (`kombu.exceptions.OperationalError: Error 10061 connecting to 127.0.0.1:6379`), عندما استُدعِيَ `deploy_service_task.delay(...)` من داخل معالج HTTP فعلي وأدّى لاستجابة 500.

### 4.3 لماذا الفشل بلا أي تغطية fallback/retry
- الخطأ بيحصل **وقت النشر (publish) نفسه** — أي وقت استدعاء `.delay()` من كود الـAPI (producer side) — قبل ما المهمة توصل لأي worker إطلاقًا. آلية `self.retry(...)` المكتوبة جوه `deploy_service_task` (سطر 76-80 من `app/tasks/deployment.py`) **لا تتفعّل أبدًا** في هذا المسار، لأنها منطق داخل جسم المهمة نفسها اللي بتتنفذ على الـworker — والمهمة أصلًا فشلت قبل ما توصل للـworker.
- النتيجة الفعلية الموثَّقة سابقًا: الاستثناء بيتصعّد لأعلى مباشرة لمعالج HTTP، ويرجع **500 فورًا لكل طلب**، بلا أي محاولة إعادة أو تأخير يغطي المشكلة.
- **الخلاصة القاطعة لهذا البند:** لا يوجد أي fallback يغطي المشكلة. إما الاتصال بالبورت الصحيح (6380) وينجح فعليًا بشكل كامل (لو `cwd=eppne-backend`)، أو الاتصال بالبورت الغلط (6379) ويفشل فورًا 100% من المرات (لو `cwd=E:\cc` أو أي `cwd` تاني فيه ملف `.env` بديل بنفس القيمة الغلط) — لا حالة وسطى ولا نجاح متقطع.

---

## 5. السبب الجذري الفعلي (مؤكَّد بالتجربة، وليس افتراضًا)

`app/core/config.py:14` بيستدعي `load_dotenv()` (بدون تحديد مسار) قبل تعريف كلاس `Settings`، وكمان `model_config = SettingsConfigDict(env_file=".env", ...)` (سطر 217-218) بمسار **نسبي**. كلا الآليتين بيتأثروا بـ working directory العملية وقت التشغيل، مش بمكان ملف `config.py` نفسه على القرص. بالتجربة الفعلية (قسم 4.2 فوق):

| `cwd` وقت تشغيل العملية | أي `.env` بيتحمّل فعليًا | `settings.REDIS_URL` الناتج | النتيجة |
|---|---|---|---|
| `E:\cc\eppne-backend` (الوضع الطبيعي لكل جلسات `uvicorn`/`pytest` الموثَّقة) | `eppne-backend/.env` | `...127.0.0.1:6380/0` | ✅ يعمل |
| `E:\cc` (جذر الريبو) | `E:\cc\.env` | `redis://localhost:6379/0` | ❌ يفشل فورًا (بورت غلط + بلا باسورد أصلًا) |

هذا يفسّر تمامًا ليه كل الجلسات الموثَّقة سابقًا اللي شغّلت السيرفر (`academy-priority-fix-session-log.md`, `academy-live-testing-session-log.md`, إلخ) وثّقت "Redis على 6380" شغّال وناجح — كانت كلها بـ`cwd=eppne-backend`. وليه جلسة `service_marketplace` الحية (اللي استخدمت نفس البيئة) فشلت فجأة بـ500 على خطوة الـCelery تحديدًا — على الأرجح لأن العملية أو السكريبت اللي استدعى الـ`.delay()` وقتها كان شغّال (أو بيقرأ إعدادات) من مسار مختلف عن `eppne-backend/`، فالتقط `.env` الجذر الخطأ (أو نسخة مكافئة له). **لم أؤكّد بالضبط أي عملية/سكريبت بالتحديد كان شغّالًا وقتها بـ`cwd` مختلف** — هذا يحتاج مراجعة سجلات تلك الجلسة تحديدًا لو الهدف تأكيد ذلك بدقة أكتر؛ خارج نطاق هذه الجلسة (read-only فقط).

**ليس المتغيرين `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` هما "السبب"** — هما فقط قيم ميتة موجودة صدفة في نفس الملف اللي فيه القيمة الصح، وأثارت الانتباه بصريًا وقت المراجعة السابقة، لكن تصحيحهم وحده **لن يصلح شيئًا فعليًا** طالما مشكلة الـ`cwd`/ملف `.env` الجذر القديم قائمة.

---

## 6. تأكيد الالتزام بحدود النطاق

- **صفر تعديل** على أي ملف `.env` أو أي ملف كود (`.py`, `.yml`, إلخ) في هذه الجلسة — تم التحقق فقط عبر `Read`/`Grep`/`Bash` (قراءة، `docker ps`/`docker inspect`/`docker exec ... redis-cli ping` للقراءة فقط، `Get-NetTCPConnection`، وتشغيل سكريبتات بايثون مؤقتة عبر `python -c` لاختبار الاتصال فقط دون كتابة أي ملف).
- الأمر الوحيد اللي كان ممكن يُفهم كـ"تنفيذ مهمة" هو `celery inspect ping` — قراءة/فحص فقط، لم يُرسَل أي `.delay()` حقيقي لمهمة إنتاجية (استخدمت `redis.ping()` المباشر بدل استدعاء أي `task.delay()` فعلي لتفادي إنشاء أي صف عمل حقيقي في الطابور).
- لم يتم لمس `docker-compose.yml`، ولا أي حاوية تم إيقافها أو إعادة تشغيلها أو تعديلها.

---

## الخلاصة النهائية

1. **`REDIS_URL` في `eppne-backend/.env` صحيح فعلًا (6380)** ومطابق للحاوية الشغّالة، **بشرط** تشغيل أي عملية (uvicorn/celery worker/سكريبت) من داخل `eppne-backend/` كـ`cwd`.
2. **`E:\cc\.env` (الجذر) فيه `REDIS_URL` قديم/خطأ (6379، بلا باسورد)** — أي عملية تُشغَّل من جذر الريبو هتلتقطه بدل نسخة `eppne-backend/`، وتفشل فورًا 100% من المرات عند أي استخدام حقيقي لـRedis/Celery.
3. **`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` غير مستخدَمين إطلاقًا في الكود** — قيم ميتة، تصحيحهم غير كافٍ وغير مؤثِّر بمفرده.
4. **الحاوية الفعلية الشغّالة اسمها `redis` (بدون بادئة)، مش `eppne_redis`**، واتعملها `docker run` يدوي منفصل تمامًا عن `docker-compose.yml` — ملف الـcompose نفسه (بخدماته الـ8: postgres/redis/minio/prometheus/grafana/backend/worker/flower) غير شغّال حاليًا كوحدة واحدة.
5. لا يوجد fallback أو retry يغطي المشكلة عند حدوثها — إما نجاح كامل أو فشل فوري وواضح (500 على مستوى الـAPI).

**بنود قرار مفتوحة لجلسة إصلاح منفصلة (لم تُتَّخذ هنا أي قرار تصميمي):**
- توحيد مصدر الحقيقة: إما حذف `E:\cc\.env` (أو تصحيح قيمته لتطابق `eppne-backend/.env`)، أو جعل `config.py` يحدّد مسار `.env` بشكل مطلق (غير معتمد على `cwd`) بدل الاعتماد على `load_dotenv()`/`env_file="."` النسبيين.
- حذف `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` من `eppne-backend/.env` (قيم ميتة) أو توضيح أنهم غير مستخدَمين، لتفادي تضليل أي مراجعة مستقبلية بنفس الطريقة اللي حصلت في الجلسة السابقة.
- قرار: هل الاعتماد المطلوب فعليًا هو الحاوية اليدوية `redis` (6380) الحالية، أم تفعيل `docker-compose.yml` بخدماته الكاملة (`eppne_redis` + `worker` + `flower`)؟ حاليًا المشروع في حالة هجينة غير متسقة.

---

**Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>**
**Claude-Session:** https://claude.ai/code/session_013DdyJkSm7DXHCPiecauya2
