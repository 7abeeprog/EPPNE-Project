# جلسة: redis-password-rotation-not-durable — تحقيق (قراءة فقط)

- **التاريخ:** 2026-09-24
- **النوع:** تحقيق read-only. لا تعديل كود، لا بنية تحتية، لا staging/commit، لا كتابة في `PROGRESS_LOG.md`.
- **ملاحظة أمان:** لا توجد أي كلمة سر نصية في هذا التقرير. كل المقارنات تمت بـ **بصمة sha256 (أول 12 حرفًا)** وطول السلسلة فقط.

---

## الخلاصة في سطرين

فرضية "الحاوية تطلب الآن كلمة سر مجهولة" **خاطئة**. الحاوية `redis` **أُعيد تشغيلها اليوم 2026-09-24 03:58:02 UTC** (بعد إعادة إقلاع الجهاز 06:47 بتوقيت +0300)، ففقدت كلمة السر الجديدة المضبوطة بـ`CONFIG SET` في الذاكرة و**رجعت لكلمة السر القديمة المثبَّتة في `Cmd`** — وهي نفسها التي كانت مسرَّبة في تاريخ git قبل الـscrub. أما `.env` فيحمل كلمة السر **الجديدة**. النتيجة: التطبيق يرسل الجديدة، والحاوية تقبل القديمة فقط.

الخوف من فقدان البيانات عند إعادة التشغيل **لم يتحقق**: `restart` (stop/start) حافظ على البيانات (الـ`dump.rdb` في طبقة الكتابة للحاوية). فقط `docker rm` + إنشاء جديد هو ما يمسحها.

---

## 1) التاريخ الكامل (إعادة بناء)

| الوقت | الحدث | المصدر |
|---|---|---|
| 2026-07-26 03:49 UTC | إنشاء الحاوية `redis` يدويًا (`docker run`، بدون labels لـcompose)، image `redis` (بلا tag → حاليًا 8.8.1)، `Cmd=["--requirepass", <قديمة>]`، `Mounts=[]`، `RestartPolicy=no`، منفذ `6380→6379` | `docker inspect redis` |
| قبل 2026-09-23 | كلمة السر القديمة موجودة نصيًا في عدة تقارير/diffs داخل تاريخ git (~10 مرات) | `.claude/reports/pre-push-secret-scan-46-commits-session-log.md:34-48` |
| 2026-09-23 (بعد scrub تاريخ git) | جلسة `e618c13d…` دوَّرت كلمتي سر Postgres وRedis. Redis عبر `CONFIG SET requirepass` حيًا فقط. حُدِّث `eppne-backend/.env` (`REDIS_PASSWORD`، `REDIS_URL`) — آخر تعديل للملف 2026-09-23 04:38:18 +0300 | تقرير الـscratchpad `redis_postgres_password_rotation_report.md` (خارج الريبو، يحوي كلمات السر نصيًا) |
| نفس الجلسة | سُجِّل كـbacklog **بالاسم** `redis-password-rotation-not-durable-across-container-restart` في تقرير الـscratchpad فقط. السبب: الحاوية بلا volume و34 مفتاحًا حيًا (قائمة `celery` ≈ 932 عنصرًا) فلم يُجرَ recreate. الخطة المقترحة وقتها: `BGSAVE` + recreate مع volume، أو `redis-cli --rdb` dump/restore | نفس التقرير، سطر 27 |
| 2026-09-24 06:47 (+0300) = 03:47 UTC | **إعادة إقلاع ويندوز** | `systeminfo` → System Boot Time |
| 2026-09-24 03:56:59 UTC | `eppne_db` بدأ تلقائيًا (`restart=unless-stopped`) | `docker inspect` |
| 2026-09-24 03:58:02–03 UTC | `redis` و`postgres-eppne` بدآ معًا خلال ثانية واحدة. كلاهما `restart=no` ⇒ **بدأهما أحد يدويًا** (أمر `docker start` أو واجهة Docker Desktop) — الفاعل غير محدَّد، لا يوجد أثر في التقارير | `docker inspect` (StartedAt) |
| 03:58:13 UTC | Redis حمَّل `dump.rdb` (آخر حفظ 03:21 UTC قبل الإغلاق)، `rdb_last_save_time=1790222293` = لحظة الإقلاع | `INFO persistence` |
| منذ ذلك الحين (~5 ساعات) | **صفر كتابة ناجحة** (`rdb_changes_since_last_save:0`) — منطقي لأن التطبيق مرفوض المصادقة | `INFO persistence` |
| 2026-09-24 (عدة جلسات) | ظهور `NOAUTH`/`AuthenticationError` في جلسات saas/invitations/insurance؛ فشل إقلاع uvicorn؛ تسرب صفوف من fixtures | `PROGRESS_LOG.md:1090`، ملف الذاكرة |

**لا يوجد صف لهذا البند في `PROGRESS_LOG.md` حتى الآن** (الإشارة الوحيدة داخل صف إغلاق invitations في السطر 1090، وتصف الأمر بشكل غير دقيق: "كلمة سر Redis الحية لا تطابق إعدادات التطبيق" — صحيح، لكن السبب هو الرجوع للقديمة وليس كلمة مجهولة).

---

## 2) الحالة الحالية الفعلية (مُتحقَّق منها حيًا)

### بصمات كلمات السر

| المصدر | الطول | sha256[:12] |
|---|---|---|
| `Cmd` الحاوية `redis` (القديمة) | 20 | `63ccd69a2c2d` |
| `eppne-backend/.env` → `REDIS_PASSWORD` | 32 | `72aa5fba4464` |
| `eppne-backend/.env` → كلمة السر داخل `REDIS_URL` | 32 | `72aa5fba4464` |
| كلمة السر الجديدة في تقرير التدوير 2026-09-23 | 32 | `72aa5fba4464` ✅ مطابقة لـ`.env` |
| `docker-compose.yml` (`--requirepass` و`REDIS_PASSWORD`/`REDIS_URL`) | — | ليست قيمة حرفية: `${REDIS_PASSWORD}` (interpolation من `.env`) |

### اختبار المصادقة الحي (`docker exec redis redis-cli PING` مع `REDISCLI_AUTH`)

| المرشح | النتيجة |
|---|---|
| بدون كلمة سر | `NOAUTH Authentication required.` |
| كلمة `Cmd` القديمة | **`PONG`** ✅ ← **هذه هي كلمة السر الحية الآن** |
| كلمة `.env` (الجديدة) | `WRONGPASS invalid username-password pair` |

### أين انفصلت القيم ومتى
- `.env` والحاوية كانا متطابقين من 2026-09-23 04:38 (+0300) حتى 2026-09-24 03:58 UTC.
- الانفصال حدث لحظة إعادة تشغيل الحاوية. لا علاقة لـ`docker-compose.yml` بهذا: الحاوية الحية ليست من compose أصلًا.

### كيف يقرأ التطبيق الإعداد
- `app/core/config.py:76-80` → `REDIS_URL` و`REDIS_PASSWORD` من `.env`.
- `app/core/redis_client.py:33-34` → يستخدمهما (هذا ما يستدعيه الـlifespan hook ⇒ فشل إقلاع uvicorn).
- `app/core/celery_app.py:16-17` → `broker=backend=settings.REDIS_URL` ⇒ Celery أيضًا مرفوض.

---

## 3) هل للحاوية volume؟

- `Mounts=[]` و`Config.Volumes=null` (الـimage المستخدم لا يعلن `VOLUME /data` في هذا البناء).
- `/data/dump.rdb` (643,875 بايت) موجود في **طبقة الكتابة للحاوية**. قاعدة `save` مفعَّلة (`3600 1 300 100 60 10000`)، `appendonly` معطَّل، لا ملف config (`config_file:` فارغ) ⇒ `CONFIG REWRITE` مستحيل.
- **الاستنتاج:**
  - `docker restart`/`stop`+`start` ⇒ البيانات تبقى، كلمة السر ترجع للقديمة (هذا ما حدث اليوم).
  - `docker rm` + `docker run` ⇒ البيانات تُفقد (ما لم تُنسخ `dump.rdb` أولًا).
- `RestartPolicy=no` مشكلة موازية: بعد أي إعادة إقلاع للجهاز لا تعود `redis` تلقائيًا (بعكس `eppne_db`).

---

## 4) الأثر الحالي (مُؤكَّد)

- كل عميل يستخدم `settings.REDIS_URL` يحصل على `WRONGPASS`/`AuthenticationError`: uvicorn (lifespan)، Celery broker/backend، كاش `UserService.register`.
- لا توجد كتابة ناجحة على Redis منذ 03:58 UTC (مؤكَّد بـ`rdb_changes_since_last_save:0`).
- `redis-cli` بدون مصادقة ⇒ `NOAUTH` (سلوك طبيعي، ليس دليلًا على كلمة سر مجهولة).
- تسرب صفوف pytest: الـfixtures تُنفِّذ commit للمستخدم/المحفظة قبل استدعاء Redis وخارج `try/finally` ⇒ كل تشغيل يسرِّب. إصلاح كلمة السر **يزيل المُحفِّز فقط**؛ هشاشة الـfixtures نفسها بند مستقل (مقترح أدناه).

---

## 5) البيانات المعرَّضة للخطر (38 مفتاحًا حاليًا، مقابل 34 وقت التدوير)

| المفتاح/النوع | الحجم | TTL | التقييم |
|---|---|---|---|
| `celery` (list) | **936** | دائم | **كلها** `send_notification_task`، `eta=null`. لا يوجد worker يعمل (`eppne_beat` متوقف منذ 6 أيام، لا حاوية worker). عند تشغيل أي worker مستقبلًا ستُرسَل 936 إشعارًا دفعة واحدة — غالبًا مخلفات اختبارات. **قيمة منخفضة، خطر إغراق عالٍ.** |
| `events` (list) | 100 | دائم | أحداث `academy.bootcamp_enrollment.created` بمعرفات مستخدمين مثل 13211/6377 — تبدو بيانات اختبار/seed. قيمة منخفضة. |
| `idempotent:*` (string) | 18 | 2.2–3 ساعات متبقية | مفاتيح dedup (منها `REGTEST-*`) — ستنتهي اليوم تلقائيًا. قيمة شبه معدومة. |
| `ai:cost:*` (hash) | 4 | 3.5–33 يومًا | تتبع تكلفة AI (أغسطس + total). القيمة الوحيدة ذات المعنى المحتمل. |
| `unacked`/`unacked_index` | 1/1 | دائم | رسالة Celery واحدة غير مؤكَّدة. |
| `_kombu.binding.*` (set) | 12 | دائم | تُعاد تلقائيًا عند اتصال Celery. |

**الخلاصة:** لا شيء حرج، لكن التوصية هي **الحفاظ على كل شيء كما هو** (نقل `dump.rdb` بالكامل) وعدم خلط قرار "تفريغ قائمة celery" مع إصلاح كلمة السر — ذلك قرار منفصل.

---

## 6) السبب الجذري

1. التدوير نُفِّذ بـ`CONFIG SET` فقط — يعيش في ذاكرة العملية.
2. الحاوية مُنشأة يدويًا بكلمة السر القديمة مثبَّتة في `Cmd`، بلا ملف config يمكن `CONFIG REWRITE` إليه.
3. `.env` حُدِّث للجديدة ⇒ الدائم (`.env`) والدائم الآخر (`Cmd`) كانا مختلفين منذ لحظة التدوير؛ كان التطابق مؤقتًا بفضل الذاكرة فقط.
4. إعادة إقلاع الجهاز 2026-09-24 + تشغيل الحاوية يدويًا ⇒ انكشف الانفصال.

---

## 7) الإصلاح المقترح (لم يُنفَّذ — ينتظر الموافقة)

### الخيار (أ) — مرفوض كتوصية: إرجاع `.env` لكلمة السر القديمة
أسرع، صفر مخاطرة بيانات، دائم فورًا. **لكنه يعيد كلمة سر كانت مسرَّبة في تاريخ git** ويلغي هدف تدوير 2026-09-23، والمنفذ `6380` مربوط على `0.0.0.0`. لا أوصي به.

### الخيار (ب) — الموصى به: إعادة إنشاء الحاوية بكلمة السر الجديدة، مع نقل البيانات
الخطوات (كل خطوة بموافقة):
1. **لقطة قبل:** `DBSIZE` + قائمة المفاتيح بأنواعها وأحجامها (المرجع للمقارنة: 38 مفتاحًا، `celery`=936، `events`=100).
2. **حفظ متسق:** `SAVE` (بكلمة السر القديمة) ثم `docker cp redis:/data/dump.rdb` إلى مسار نسخة احتياطية خارج الريبو.
3. **إيقاف والاحتفاظ للرجوع:** `docker stop redis` ثم `docker rename redis redis-old-20260924` (لا `rm` حتى ينجح التحقق).
4. **volume مسمّى:** `docker volume create eppne_redis_data` ونسخ `dump.rdb` إليه (عبر حاوية مؤقتة).
5. **إنشاء الحاوية الجديدة** بنفس الاسم `redis` ونفس المنفذ `6380:6379`:
   - image مُثبَّت الإصدار `redis:8.8.1` (تفادي مشاكل صيغة RDB مع image بلا tag).
   - `-v eppne_redis_data:/data`
   - `--restart unless-stopped` (يحل مشكلة عدم العودة بعد الإقلاع).
   - كلمة السر تُمرَّر من `.env` وقت الإنشاء (`--requirepass` بالقيمة الجديدة)، **و**متغير بيئة `REDISCLI_AUTH` بنفس القيمة داخل الحاوية ⇒ `docker exec redis redis-cli …` يعمل مباشرة للتصحيح اليدوي بلا كتابة كلمة السر.
   - اختياري للنقاش: `--appendonly yes` لمتانة أفضل (الـcompose يستخدمه).
6. **لا تغيير على `.env`** (هو أصلًا صحيح)، **لا تغيير على الكود**، **لا تغيير على `docker-compose.yml`**.

ملاحظة: كلمة السر ستظهر في `docker inspect` (Cmd/Env) كما كانت القديمة — مقبول لبيئة تطوير محلية ومطابق للوضع السابق. البديل (ملف `redis.conf` في الـvolume) أنظف لكنه أكثر تعقيدًا؛ أتركه للنقاش.

### ما يُفقد
لا شيء إذا نجحت الخطوة 2 — كل الـ38 مفتاحًا تنتقل. الـTTL تُحفظ في RDB. مفاتيح `idempotent:*` ستكون غالبًا منتهية طبيعيًا وقت التنفيذ.

### خارج النطاق (بنود مقترحة منفصلة — لا تُدمج في هذا الإصلاح)
- **قائمة `celery` (936 `send_notification_task`)**: قرار منفصل (تفريغ/فحص) قبل تشغيل أي worker.
- **هشاشة fixtures الاختبارات** (commit قبل Redis وخارج `try/finally`): بند مستقل؛ يجب البحث في `PROGRESS_LOG.md` عن صف موجود بنفس العَرَض قبل فتح صف جديد.
- **تكرار تعريف Redis**: `docker-compose.yml` يعرِّف `eppne_redis` (redis:7-alpine، منفذ `${REDIS_PORT:-6379}`=6379، متوقف منذ 6 أيام) بينما التطبيق يستخدم الحاوية اليدوية على 6380. `REDIS_PORT=6379` في `.env` لا يطابق `REDIS_URL` (6380). مصدر ارتباك دائم.
- `E:\cc\.env` الجذري: `REDIS_URL` قديم (6379 بلا مصادقة) — موثَّق سابقًا.
- `postgres-eppne` الشارد — backlog موجود مسبقًا.

---

## 8) خطة التحقق الحي (بعد التنفيذ)

1. `docker exec redis redis-cli PING` (بدون تمرير كلمة سر، عبر `REDISCLI_AUTH` المدمج) ⇒ `PONG`.
2. `DBSIZE` ومقارنة المفاتيح بلقطة الخطوة 1 (العدد، `LLEN celery`، `LLEN events`، `ai:cost:*`، `unacked`).
3. من المضيف بمسار التطبيق الحقيقي: سكربت Python صغير يستخدم `settings.REDIS_URL` ⇒ `ping()` ناجح؛ ومحاولة بكلمة السر القديمة ⇒ `WRONGPASS` (إثبات أن القديمة ماتت).
4. **إثبات المتانة (الأهم):** `docker restart redis` ثم إعادة 1–3 ⇒ نفس النتائج. هذا بالضبط الاختبار الذي كان سيفشل قبل الإصلاح.
5. uvicorn: تشغيل التطبيق والتأكد من `Application startup complete` وعدم وجود `AuthenticationError` في اللوج، ثم إيقافه.
6. pytest: تشغيل اختبار واحد تستدعي fixture الخاصة به `UserService.register()` (يُحدَّد بالاسم قبل التشغيل)، مع عدّ `users`/`wallets`/`tenants` قبل وبعد ⇒ صفر تسرب وصفر `AuthenticationError`.
7. بعد نجاح كل ما سبق فقط: `docker rm redis-old-20260924` وحذف نسخة `dump.rdb` الاحتياطية (بموافقة).
8. التوثيق (بموافقة): صف `PROGRESS_LOG.md` جديد للإغلاق، وتحديث ملف الذاكرة.

---

## سجل الأوامر (كلها قراءة فقط)

- `docker ps -a`، `docker inspect redis|eppne_db|postgres-eppne` (كلمات السر محجوبة/مبصومة).
- `docker exec redis redis-cli` مع `REDISCLI_AUTH`: `PING`، `INFO server|persistence|keyspace`، `DBSIZE`، `CONFIG GET dir|save`، `--scan` + `TYPE/LLEN/HLEN/SCARD/ZCARD/TTL`، `LRANGE celery` (أسماء المهام فقط)، `LINDEX events`.
- `ls /data` داخل الحاوية؛ `systeminfo` (وقت الإقلاع).
- قراءة `eppne-backend/.env` (بصمات فقط)، `docker-compose.yml` + `git log`/`git diff` له، `app/core/config.py`، `redis_client.py`، `celery_app.py`.
- قراءة تقرير التدوير في scratchpad جلسة 2026-09-23 وتقرير فحص الأسرار.
- ملف مؤقت واحد يحتوي كلمة السر القديمة أُنشئ عرضًا في scratchpad هذه الجلسة ثم **حُذف فورًا**.
- **لم يُعدَّل أي ملف في الريبو سوى إنشاء هذا التقرير.**

---

## 9) الخلاصة المرفوعة للمستخدم + القرار المطلوب (نهاية الخطوة 2)

**السبب الجذري:** كلمة السر الحية ليست مجهولة، بل هي **القديمة**. أُعيد إقلاع ويندوز اليوم الساعة 06:47 (+0300). الحاوية `redis` مضبوطة على `restart=no`، وشغّلها أحدهم يدويًا الساعة 03:58 UTC مع `postgres-eppne` (الفاعل غير معروف). رجعت الحاوية بكلمة السر القديمة المكتوبة في أمر تشغيلها، لأن كلمة السر الجديدة من تدوير 2026-09-23 كانت في الذاكرة فقط (`CONFIG SET`)، ولا يوجد ملف config يمكن حفظها فيه بـ`CONFIG REWRITE`.

**الاختبار الحي:**

| كلمة السر المُجرَّبة | النتيجة |
|---|---|
| بدون كلمة سر | `NOAUTH` |
| كلمة أمر تشغيل الحاوية (القديمة) | `PONG` |
| كلمة `.env` (الجديدة) | `WRONGPASS` |

- كلمة `.env` هي الجديدة فعلًا: بصمتها تطابق تقرير التدوير (2026-09-23).
- `docker-compose.yml` لا علاقة له بالمشكلة: الحاوية الحية أُنشئت يدويًا وليست من compose.
- صفر كتابة على Redis منذ إعادة التشغيل، وهذا متسق مع رفض كل العملاء: uvicorn عند الإقلاع، وCelery (`celery_app.py:16-17`)، وكاش `UserService.register`.

**البيانات لم تُفقد:** الإيقاف والتشغيل حافظا على `dump.rdb` (داخل نظام ملفات الحاوية نفسها). فقط حذف الحاوية وإعادة إنشائها يمسحها. يوجد 38 مفتاحًا حاليًا:
- قائمة `celery`: 936 عنصرًا كلها `send_notification_task`. لا يوجد worker يعمل، فتشغيل أي worker سيرسلها كلها دفعة واحدة. تبدو مخلفات اختبارات.
- `events`: 100 عنصر تبدو بيانات اختبار/seed.
- مفاتيح idempotency: 18، كلها تنتهي خلال حوالي 3 ساعات.
- `ai:cost`: 4 مفاتيح، وهي الوحيدة التي قد تستحق الحفاظ عليها.

**الإصلاح المقترح (الخيار ب — الموصى به):**
1. حفظ على القرص ونسخ `dump.rdb` خارج الحاوية.
2. إعادة تسمية الحاوية القديمة والاحتفاظ بها للرجوع.
3. إنشاء volume مسمّى ووضع البيانات المحفوظة فيه.
4. إنشاء حاوية `redis` جديدة: `redis:8.8.1` مثبَّت، نفس المنفذ 6380، `--restart unless-stopped`، كلمة السر الجديدة في `--requirepass`، ومتغير `REDISCLI_AUTH` ليعمل `docker exec redis redis-cli` بدون كتابة كلمة السر.
5. بدون أي تغيير على `.env` أو الكود أو ملف compose.

**غير موصى به (الخيار أ):** إرجاع `.env` لكلمة السر القديمة. هو الأسرع وبلا مخاطرة على البيانات، لكن تلك الكلمة كانت مكشوفة في تاريخ git، فهذا يلغي التدوير.

**خطة التحقق:**
1. `PING` من `redis-cli` ومن `settings.REDIS_URL` الخاص بالتطبيق، والتأكد أن الكلمة القديمة أصبحت مرفوضة.
2. مقارنة المفاتيح مع لقطة مأخوذة قبل التغيير.
3. `docker restart redis` ثم إعادة الخطوة 1. هذا هو الاختبار الذي كان سيفشل قبل الإصلاح.
4. التأكد من وصول uvicorn إلى `Application startup complete`.
5. تشغيل اختبار pytest واحد تستدعي fixture الخاصة به `UserService.register()`، مع عدّ users/wallets/tenants قبل وبعد للتأكد من عدم التسرب.
6. بعد نجاح كل ذلك فقط: حذف الحاوية القديمة.

**خارج هذا الإصلاح (بنود backlog منفصلة محتملة):**
- قائمة `celery` (936 عنصرًا) تحتاج قرارًا مستقلًا: تفريغ أو فحص.
- fixtures الاختبارات تعمل commit قبل استدعاء Redis وخارج `try/finally`. إصلاح كلمة السر يوقف تسربات اليوم لكنه لا يعالج هذا الضعف.
- `docker-compose.yml` يعرِّف Redis ثانيًا (`eppne_redis`، منفذ 6379، متوقف) لا يستخدمه التطبيق، و`.env` فيه `REDIS_PORT=6379` بينما `REDIS_URL` يستخدم 6380.

**حالة التوثيق:** لا يوجد صف لهذا البند في `PROGRESS_LOG.md` حتى الآن.

**القرار المطلوب من المستخدم:** هل ننفّذ الخيار (ب) بدءًا باللقطة والنسخة الاحتياطية (الخطوتان 1–2)؟ — **بانتظار الموافقة؛ لم يُنفَّذ شيء.**

---

# التنفيذ — الخيار (ب) (موافَق عليه من المستخدم 2026-09-24، خطوة بخطوة)

**ملاحظات المستخدم للسجل (خارج النطاق، لا تنفيذ الآن):**
- تكرار تعريف Redis في `docker-compose.yml` (`eppne_redis`، منفذ 6379، متوقف وغير مستخدم) مع عدم تطابق `REDIS_PORT=6379` و`REDIS_URL` (6380) في `.env` — مصدر ارتباك دائم، يستحق التنظيف في جلسة مستقبلية رغم عدم وجود ضرر فعلي اليوم.
- قائمة `celery` القديمة (936) وهشاشة fixtures الاختبارات (commit قبل Redis وخارج `try/finally`) — قراران منفصلان، ليسا جزءًا من هذا الإصلاح.

## الخطوة 1 — اللقطة (قراءة فقط) ✅

- `DBSIZE=38`، `db0:keys=38,expires=22`، `rdb_changes_since_last_save:0`، `redis_version:8.8.1`.
- التوزيع: 18 string (`idempotent:*`، TTL المتبقي 7078–10196 ث)، 12 set (`_kombu.binding.*`)، 5 hash (`unacked` + 4 `ai:cost:*`)، 2 list (`celery`=936، `events`=100)، 1 zset (`unacked_index`).
- لكل مفتاح بصمة sha256 لمحتواه (وليس العدد فقط) للمقارنة بعد الاستعادة. أمثلة: `celery`=`8dd4e5ce12350199`، `events`=`680d70e0494dce29`، `unacked`=`79cfc255902f04e2`، `ai:cost:kimi-k2.6:total`=`7172528d27621c04`.
- الملفات الكاملة (خارج الريبو، في scratchpad الجلسة): `redis_snapshot_before.txt` (النوع/الحجم/TTL/الاسم) و`redis_snapshot_before_digests.txt` (38 بصمة).
- **ملاحظة متوقعة:** مفاتيح `idempotent:*` الـ18 ستنتهي خلال ~2–2.8 ساعة؛ إن انتهت قبل التحقق فغيابها طبيعي وليس فقدانًا.

## الخطوة 2 — SAVE + نسخ احتياطي ✅

- `SAVE` ⇒ `OK`، `rdb_last_bgsave_status:ok`، `DBSIZE=38` (بلا تغيير)، `rdb_changes_since_last_save:0`.
- `/data/dump.rdb` داخل الحاوية: **643,724 بايت**، 2026-09-24 09:27:50 UTC، sha256 `ebf1aba47eeb4aa3…8484b6d70`.
- النسخة: `C:\Users\Hp\eppne-redis-backup-20260924\dump.rdb` (خارج الريبو وخارج scratchpad) — **643,724 بايت، sha256 مطابق تمامًا**، ترويسة الملف `REDIS0014` (صيغة RDB v14 صالحة).
- الفرق عن 643,875 بايت المذكورة سابقًا (−151 بايت): الملف السابق كُتب 03:21 UTC قبل الإغلاق؛ الجديد يعكس نفس الـ38 مفتاحًا بعد التحميل (TTL مطلقة وضغط مختلف قليلًا). لا كتابة جديدة (`rdb_changes_since_last_save:0` قبل SAVE)، فلا فقدان.
- لم يُوقَف أو يُعدَّل أي شيء في الحاوية بعد.

## الخطوة 3 — إيقاف وإعادة تسمية ✅

- `docker stop redis` ⇒ `Exited (0)` (إغلاق نظيف؛ Redis يحفظ RDB عند الإغلاق — لا كتابات جديدة كانت منذ SAVE).
- `docker rename redis redis-old-20260924` ⇒ الحاوية القديمة محفوظة بالاسم الجديد، **لم تُحذف**.
- التحقق: لا حاوية باسم `redis` (0)، لا حاوية تعمل تنشر 6380 (0)، `netstat` لا يُظهر أي مستمع على `:6380` (0).
- `eppne_redis` (compose) لم يُمَس — متوقف منذ 6 أيام كما هو.

## الخطوة 4 — volume + حاوية جديدة ✅

- `docker volume create eppne_redis_data`.
- نسخ `dump.rdb` عبر حاوية مؤقتة (`--rm`، الـbackup مُركَّب read-only) + `chown redis:redis`. sha256 داخل الـvolume = `ebf1aba47eeb4aa3…8484b6d70` **مطابق** للنسخة الاحتياطية، 643,724 بايت (تم التحقق قبل إنشاء الحاوية الحقيقية).
- سُحب `redis:8.8.1` (digest `sha256:3eafabb4c93f…`).
- الحاوية الجديدة `redis`: `redis:8.8.1`، `-p 6380:6379`، `--restart unless-stopped`، `-v eppne_redis_data:/data`، `--requirepass` و`REDISCLI_AUTH` من `eppne-backend/.env` داخل الـshell (فحص طول 32 قبل الاستخدام، لم تُطبع).
- اللوج: `Loading RDB produced by version 8.8.1` ⇒ `Done loading RDB, keys loaded: 38, keys expired: 0` ⇒ `DB loaded from disk: 0.177 seconds` ⇒ `Ready to accept connections tcp`.
- لاحظ: الـimage يحمّل modules (RedisBloom/Search/TimeSeries/JSON) — افتراضي لـredis 8، نفس الحاوية القديمة (8.8.1 أيضًا).

## الخطوة 5 — التحقق + إثبات المتانة ✅

سكربتا فحص في scratchpad: `checks.sh` (فحوص 1–2) و`app_ping.py` (فحص 3، يستخدم `app.core.config.settings` عبر `venv` الخاص بالباك إند؛ كلمة السر القديمة تُقرأ من `docker inspect redis-old-20260924` داخل الـshell ولا تُطبع).

| الفحص | قبل `docker restart` | بعد `docker restart` (09:48:40 UTC) |
|---|---|---|
| [1] `docker exec redis redis-cli PING` بلا تمرير كلمة سر | `PONG` | `PONG` |
| [2] `DBSIZE` | 38 | 38 |
| [2] بصمات المحتوى مقارنة بلقطة الخطوة 1 | 38/38 متطابقة؛ صفر مفقود، صفر جديد، صفر متغيّر | 38/38 متطابقة؛ صفر مفقود، صفر جديد، صفر متغيّر |
| [2] `LLEN celery` / `LLEN events` | 936 / 100 | 936 / 100 |
| [3] `settings.REDIS_URL` (127.0.0.1:6380/0) `ping()` | `True` (DBSIZE 38) | `True` (DBSIZE 38) |
| [3] كلمة السر القديمة | `AuthenticationError` (مرفوضة) | `AuthenticationError` (مرفوضة) |

- لوج إعادة التشغيل: `Done loading RDB, keys loaded: 38, keys expired: 0` ⇒ `DB loaded from disk: 0.135 seconds`.
- مفاتيح `idempotent:*` الـ18 لم تنتهِ بعد (كلها موجودة بمحتوى مطابق) — لا شيء للإبلاغ عنه.
- **النتيجة:** سيناريو الفشل الذي حدث اليوم (إعادة تشغيل الحاوية) لم يعد يغيّر كلمة السر ولا يفقد البيانات. كلمة السر القديمة المسرَّبة لم تعد تعمل.

## الخطوة 6 — إقلاع uvicorn ✅

- الأمر: `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (في الخلفية، لوج في scratchpad `uvicorn_step6.log`، 263 سطرًا). المنفذ 8000 كان فارغًا قبل التشغيل.
- `redis_client`: `جاري الاتصال بـ Redis على: 127.0.0.1:6380/0` ⇒ `✅ تم الاتصال بـ Redis بنجاح`.
- `Application startup complete.` + `Uvicorn running on http://127.0.0.1:8000` خلال ~31 ثانية.
- grep: `AuthenticationError|NOAUTH|WRONGPASS` = **0**، `Traceback` = **0**، `[ERROR]/[CRITICAL]` = **0**. التحذيرات 48 كلها من نوع "Skipping index (likely exists)" — سلوك موجود مسبقًا وموثَّق في جلسات سابقة، غير متعلق بـRedis.
- `GET /health` ⇒ `HTTP 200` `{"status":"Sovereign System Operational","version":"2.0.0"}`.
- أُوقف uvicorn؛ المنفذ 8000 فارغ بعد الإيقاف، لا عملية python متبقية.

## الخطوة 7 — pytest مع `UserService.register()` ✅ (مع خطأ إجرائي من جهتي)

- الاختبار: `tests/test_health_appointments_tenant_isolation_fix.py` (اختبار واحد، استدعاءا `register()`: مريض + طبيب، ثم `finally` يحذف الموعد/المنشأة/الموقع/المستخدمَين).
- النتيجة: **`1 passed` في 40.91 ث**، exit 0، **صفر** سطور `AuthenticationError|NOAUTH|WRONGPASS` (لوج `pytest_step7.log` في scratchpad).
- **خطأ إجرائي:** استعلام العدّ "قبل" فشل (`relation "tenants" does not exist` — الجدول الفعلي `academy_tenants`) ولم يتوقف الأمر، فجرى الاختبار بلا لقطة "قبل" صالحة.
- **البديل (تحقق مباشر لصفوف هذا التشغيل تحديدًا):** المستخدمان المُنشآن `14126` و`14127` (معرّفاهما من مفاتيح كاش Redis `user:14126:1` و`user:14127:1`):
  - `users` بهذين المعرّفين = 0، `wallets` لهما = 0 (`wallets.user_id` عليه `ON DELETE CASCADE`)، مواعيد = 0.
  - أي مستخدم `p_regtest_health_%` = 0، مواقع `REGTEST-HEALTH-SITE-%` = 0، منشآت `REGTEST-CLINIC-%` = 0.
  - الاختبار لا ينشئ tenants (يستخدم `TENANT_ID=1` الموجود).
  - ⇒ **صفر تسرب** من هذا التشغيل.
- Redis: `DBSIZE` من 38 إلى 40 — المفتاحان الجديدان هما كاش المستخدمَين `user:*:1` (TTL=3600) كما هو متوقع من `register()`. مفاتيح `idempotent:REGTEST-p_regtest_health*` لم تُنشأ (مسار `register` لا يكتبها في Redis).
- ملاحظة: `max(users.id)`=13185 أقل من 14126 — الـsequence متقدم بسبب تشغيلات سابقة (سلوك طبيعي لـsequences، ليس تسربًا).
- الأعداد الحالية بعد التشغيل (خط أساس لأي إعادة تشغيل): `users`=123، `wallets`=98، `academy_tenants`=3.

## الخطوة 8 — التنظيف ✅ (بموافقة المستخدم)

- قبل الحذف: `redis-old-20260924` (`Exited (0)`) والمجلد `C:\Users\Hp\eppne-redis-backup-20260924\` يحوي `dump.rdb` (643,724 بايت) فقط.
- `docker rm redis-old-20260924` ✅، حذف `dump.rdb` والمجلد ✅.
- بعد الحذف: الحاوية الوحيدة `redis` (`redis:8.8.1`، Up، 6380)، `PING`⇒`PONG`، `DBSIZE`=40 (38 + مفتاحا كاش الخطوة 7).
- لم يُحذف: image `redis` القديم (بلا tag)، ملفات اللقطة/البصمات في scratchpad (لا تحوي كلمات سر).

---

# مسودات التوثيق — للمراجعة، لم يُكتب شيء في `PROGRESS_LOG.md` بعد

## فحص التكرار قبل الصياغة (بحث بالعَرَض لا بالاسم)

- لا يوجد أي صف/إغلاق سابق لهذا البند (`AuthenticationError`/`NOAUTH`/`WRONGPASS`/`CONFIG SET`/`redis-password`): الذِكر الوحيد داخل إغلاق invitations (السطر 1090).
- قائمة `celery` القديمة **مُتتبَّعة أصلًا** في `admin-kill-switch-regression-suite-side-effects` (السطر 1060، "931 رسالة متراكمة") ⇒ لا صف جديد لها؛ تُذكر بالإحالة.
- هشاشة الـfixtures (commit قبل Redis وخارج `try/finally`): لا صف موجود.
- تكرار Redis في compose / `REDIS_PORT`: لا صف مطابق. قريب منه البند 3 تحت السطر 2269 (`CELERY_BROKER_URL` على 6379) — `.env` الحالي لم يعد يحوي `CELERY_BROKER_URL`، فهو مختلف.

## المسودة 1 — إغلاق جديد (يُدرَج بعد السطر 1094، قبل الفاصل `---` في 1096)

> **✅ إغلاق مؤرَّخ [2026-09-24] — `redis-password-rotation-not-durable-across-container-restart` (لا صف سابق في هذا الملف — كان مُسجَّلًا فقط في تقرير scratchpad لجلسة التدوير 2026-09-23): مُغلَق — تغيير بنية تحتية محلية فقط، صفر تعديل كود.** جلسة `redis-password-rotation-fix` (`.claude/reports/redis-password-rotation-fix-session-log.md`). **السبب الجذري:** تدوير 2026-09-23 (بعد scrub تاريخ git) طبّق كلمة سر Redis الجديدة بـ`CONFIG SET requirepass` فقط (في الذاكرة) على الحاوية اليدوية `redis` (6380، `docker run` بلا compose، بلا volume، بلا ملف config، `restart=no`) التي تحمل كلمة السر **القديمة المسرَّبة** مثبَّتة في `Cmd`، بينما حُدِّث `eppne-backend/.env` للجديدة. بعد إعادة إقلاع الجهاز 2026-09-24 (06:47 +0300) وتشغيل الحاوية يدويًا 03:58 UTC رجعت للقديمة ⇒ كل عملاء `settings.REDIS_URL` مرفوضون (`WRONGPASS`/`AuthenticationError`): فشل إقلاع uvicorn (lifespan)، Celery broker/backend، وكاش `UserService.register` ⇒ fixtures الاختبارات انهارت قبل `try/finally` وسرّبت مستخدمين/محافظ/تينانتات في جلسات اليوم. **تصحيح تشخيص سابق:** كلمة السر الحية لم تكن "مجهولة" — كانت القديمة (تحقق حي: `PONG`)؛ والبيانات **لم تُفقد** بإعادة التشغيل (`dump.rdb` في طبقة كتابة الحاوية). **الإصلاح (الخيار ب؛ رُفض إرجاع `.env` للقديمة لأنها كانت في تاريخ git):** لقطة 38 مفتاحًا ببصمات محتوى ⇒ `SAVE` + نسخة احتياطية مطابقة sha256 ⇒ إيقاف/إعادة تسمية ⇒ volume مسمّى `eppne_redis_data` ⇒ حاوية جديدة `redis:8.8.1` (مُثبَّت)، `-p 6380:6379`، `--restart unless-stopped`، `--requirepass` + `REDISCLI_AUTH` من `.env` (لا تغيير على `.env`/الكود/`docker-compose.yml`). **تحقق حي:** قبل وبعد `docker restart redis`: `redis-cli PING` بلا كلمة سر ⇒ `PONG`؛ 38/38 بصمة محتوى مطابقة (`celery`=936، `events`=100)؛ `settings.REDIS_URL` ⇒ `ping()=True`؛ كلمة السر القديمة ⇒ `AuthenticationError`. uvicorn: `Application startup complete`، صفر `AuthenticationError`/`Traceback`/`[ERROR]`، `/health` ⇒ 200. pytest `test_health_appointments_tenant_isolation_fix.py` (استدعاءا `register()`) ⇒ `1 passed`، صفر أخطاء مصادقة، صفر صفوف متبقية للمستخدمَين المُنشأين (14126/14127). حُذفت الحاوية القديمة والنسخة الاحتياطية بعد النجاح. **خارج النطاق (لم يُنفَّذ):** (1) قائمة `celery` (936 `send_notification_task`، لا worker) — مُتتبَّعة في `admin-kill-switch-regression-suite-side-effects` أعلاه؛ (2) الصف الجديد `test-fixtures-register-commits-before-redis-outside-try-finally` أدناه؛ (3) الصف الجديد `redis-compose-duplicate-definition-and-redis-port-mismatch` أدناه. **ما زال مفتوحًا:** `postgres-eppne` الشارد (مذكور في `alembic-ini-points-to-stray-container` أعلاه) — لم يُلمَس.

## المسودة 1-ب — صفّا backlog جديدان (جدول البنود المفتوحة، بنفس صيغة `| — | **slug** [تاريخ] — … | أولوية | مرجع |`)

> | — | **`test-fixtures-register-commits-before-redis-outside-try-finally`** [2026-09-24] — اكتُشف عبر جلسات insurance/saas/invitations وأُكِّد في `redis-password-rotation-fix`: fixtures تستدعي `UserService.register()` (commit للمستخدم والمحفظة ثم كتابة كاش Redis) **قبل** كتلة `try/finally` الخاصة بالتنظيف ⇒ أي فشل في Redis (أو أي خطوة بعد الـcommit) يسرّب صفوفًا حقيقية في DB التطوير (60+ مستخدمًا/محفظة و6+ تينانتات في جلسة واحدة، نُظِّفت يدويًا). المُحفِّز الحالي أُزيل بإصلاح Redis، لكن الهشاشة باقية في ~60 ملف اختبار. | 🟡 متوسط | `.claude/reports/redis-password-rotation-fix-session-log.md` §4 |

> | — | **`redis-compose-duplicate-definition-and-redis-port-mismatch`** [2026-09-24] — `docker-compose.yml` يعرِّف خدمة `redis` (`eppne_redis`، `redis:7-alpine`، منفذ `${REDIS_PORT:-6379}`، متوقفة منذ ~6 أيام) لا يستخدمها التطبيق، بينما التطبيق يستخدم الحاوية اليدوية `redis` على 6380؛ و`.env` فيه `REDIS_PORT=6379` مقابل `REDIS_URL` على 6380. لا ضرر فعلي اليوم لكنه مصدر ارتباك دائم — يستحق التوحيد في جلسة مستقبلية. | 🟢 منخفض | `.claude/reports/redis-password-rotation-fix-session-log.md` §7 |

## المسودة 2 — تصحيح الإشارة في إغلاق invitations (السطر 1090)

**النص الحالي (مقطع):**
> مفتاح Redis `user:52:1` **لم يُتحقَّق منه** (`NOAUTH`: كلمة سر Redis الحية لا تطابق إعدادات التطبيق، متسق مع تدوير 2026-09-23 عبر `CONFIG SET` غير الدائم، ولا صف backlog له في هذا الملف بعد)؛ المتوقع أنه منتهٍ (TTL=3600ث)، غير مانع.

**النص المقترح:**
> مفتاح Redis `user:52:1` **لم يُتحقَّق منه وقتها** (`NOAUTH`: كلمة سر Redis الحية لا تطابق إعدادات التطبيق — *[تصحيح 2026-09-24: الحية كانت كلمة السر القديمة، إذ رجعت الحاوية إليها عند إعادة تشغيلها لأن تدوير 2026-09-23 كان `CONFIG SET` فقط؛ أُغلق في `redis-password-rotation-not-durable-across-container-restart` أدناه]*)؛ المتوقع أنه منتهٍ (TTL=3600ث)، غير مانع. *[تحقق لاحق 2026-09-24: `EXISTS user:52:1` ⇒ `0` — غير موجود.]*

(تعديل موضعي لهذا المقطع فقط؛ بقية السطر 1090 كما هو.)

## ملاحظة للـcommit لاحقًا

`PROGRESS_LOG.md` يحمل حاليًا diff غير مُلتزَم +670/−1 من جلسات أخرى (مُتتبَّع في `academy-camera-stack-uncommitted-implementation-deferred-session`). commit هذا الإغلاق يجب أن يكون معزولًا عبر patch (نفس أسلوب `insurance-disburse-pensions-progress-log-isolated.patch`)، لا `git add PROGRESS_LOG.md`، مع التحقق من `git show --stat` بعده.

---

# الـstaging المعزول — patch للمراجعة (لم يُطبَّق بعد)

**التقنية (أنظف من جلسة insurance: لا تعديل لشجرة العمل قبل الموافقة):** `git show HEAD:PROGRESS_LOG.md` ⇒ نسخة في scratchpad ⇒ سكربت Python يطبّق المسودات الثلاث **حرفيًا من هذا التقرير** (يستخرج أسطر `> ` مع `assert` على السطر المستهدف وعلى وجود المقطع القديم مرة واحدة بالضبط) ⇒ `git diff --no-index` ⇒ patch. الـdiff المسبق غير المُلتزَم (+670/−1) يبدأ عند `@@ -4637` — بعيد عن منطقة التعديل (1080–1100)، فلا تداخل.

- ملف الـpatch: **`.claude/reports/redis-password-rotation-progress-log-isolated.patch`**
- `--numstat`: `5 1 PROGRESS_LOG.md` — hunkان فقط:
  - `@@ -1080,6 +1080,8 @@` ⇒ +2: صفا backlog الجديدان بعد `users-row-count-unexplained-drop-2026-09-24` (آخر صف في جدول البنود المفتوحة).
  - `@@ -1087,12 +1089,14 @@` ⇒ −1/+1 تصحيح مقطع Redis داخل إغلاق invitations (السطر 1090)، و+2 (سطر فارغ + فقرة الإغلاق الجديدة) بعد تصحيح خارطة الطريق (السطر 1094)، قبل الفاصل `---`.
- `index <blob>` في رأس الـpatch يطابق `HEAD:PROGRESS_LOG.md`.
- `git apply --check --cached` ✅ و`git apply --check` (شجرة العمل) ✅.

**التطبيق المقترح بعد الموافقة:** `git apply --cached <patch>` (الـindex) + `git apply <patch>` (شجرة العمل، ليبقى الـdiff المسبق غير مُلتزَم كما هو) ⇒ `git diff --cached --stat` يجب أن يُظهر `PROGRESS_LOG.md | 6 +++++-` فقط ⇒ `git diff --stat PROGRESS_LOG.md` (غير المُلتزَم) يجب أن يبقى `+670/−1`.

## الـstaging — مُطبَّق ✅

- `git apply --cached` + `git apply` (شجرة العمل) ⇒ نجحا.
- `git diff --cached --stat` ⇒ `PROGRESS_LOG.md | 6 +++++-` (5+/1−) فقط. الـhunks المُجهَّزة: `-1082,0 +1083,2` (الصفّان)، `-1090 +1092` (تصحيح invitations)، `-1095,0 +1098,2` (الإغلاق).
- غير المُجهَّز: `PROGRESS_LOG.md | 671` (+670/−1) كما هو؛ الـhunk انزاح فقط من `@@ -4637` إلى `@@ -4641` (+4 أسطر أُدرجت فوقه) — متوقع.

## مسودة رسالة commit لـ`PROGRESS_LOG.md` (للموافقة)

```
docs: close redis-password-rotation-not-durable — restart reverted redis to old leaked password; recreated with durable password + volume, 2 backlog rows added, invitations Redis note corrected

- New dated closure (after the roadmap correction): root cause was a
  CONFIG SET-only rotation on a hand-made container whose Cmd still held the
  pre-scrub password; 2026-09-24 reboot + restart reverted it. Fix: redis:8.8.1
  on named volume eppne_redis_data, --restart unless-stopped, password from
  .env; 38/38 key digests preserved across a docker restart, old password
  rejected, uvicorn boots, register() test passes with zero leaked rows.
- New backlog rows: test-fixtures-register-commits-before-redis-outside-try-finally,
  redis-compose-duplicate-definition-and-redis-port-mismatch.
- invitations-accept-orphaned-user-no-wallet closure: Redis note corrected
  (live password was the old one) and user:52:1 now verified absent.

Infrastructure-only fix; no code changes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## الـcommits

| # | المحتوى | commit |
|---|---|---|
| 1 | `PROGRESS_LOG.md` (5+/1−: الإغلاق + صفّا backlog + تصحيح invitations) عبر الـpatch المعزول | **`864542f`** — `git show --stat`: `PROGRESS_LOG.md | 6 +++++-` فقط؛ الـdiff غير المُلتزَم (+670/−1) باقٍ كما هو |
| 2 | هذا التقرير + `redis-password-rotation-progress-log-isolated.patch` (دليل) | `docs: add session report for redis password rotation durability fix` (الـhash يُذكر في رد الجلسة) |

لم يُنفَّذ `push`.

## الحالة النهائية

- حاوية `redis`: `redis:8.8.1`، `0.0.0.0:6380->6379`، `--restart unless-stopped`، volume `eppne_redis_data:/data`، كلمة السر الجديدة (من `.env`) دائمة في أمر التشغيل، `REDISCLI_AUTH` مضبوط.
- كلمة السر القديمة المسرَّبة لم تعد مقبولة في أي مكان.
- لا تغيير على `.env` أو الكود أو `docker-compose.yml`.
- بنود مفتوحة مرتبطة: `test-fixtures-register-commits-before-redis-outside-try-finally`، `redis-compose-duplicate-definition-and-redis-port-mismatch`، قائمة `celery` (ضمن `admin-kill-switch-regression-suite-side-effects`)، `postgres-eppne` (ضمن `alembic-ini-points-to-stray-container`).
