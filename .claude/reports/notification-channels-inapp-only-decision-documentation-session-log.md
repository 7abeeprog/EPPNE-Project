# توثيق/توضيح فقط: `backlog-notification-delivery-stub-empty-non-inapp-channels`

**النطاق:** توثيق فقط — **صفر تغيير وظيفي**. الكود المنطقي لكل من
تعريفَي `send_notification_task` بقي كما هو تمامًا (حتى المسافات
البادئة والتعليقات المُعلَّقة `# pass` القديمة جوّه
`communications/tasks.py` لم تُلمَس). التعديل الوحيد: إضافة كتلة
تعليق واحدة فوق كل تعريف.

**البند المستهدف:** `PROGRESS_LOG.md` سطر 2448،
`backlog-notification-delivery-stub-empty-non-inapp-channels` (🔴🔴
أولوية بارزة، مفتوح، لم يُصلَح).

---

## 1) التعليقات المُضافة

### `app/core/celery_app.py` (فوق تعريف `send_notification_task`، السطر كان 67)

```python
# ⚠️ القنوات EMAIL/SMS/PUSH غير مُفعَّلة حاليًا (لا تكامل حقيقي مع أي
# مزوّد خارجي) — IN_APP هي القناة الوحيدة المدعومة فعليًا. راجع
# backlog-notification-delivery-stub-empty-non-inapp-channels.
@shared_task(name="send_notification_task")
def send_notification_task(*args, **kwargs):
    """مهمة إرسال إشعار (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass
```

### `app/domains/communications/tasks.py` (فوق تعريف `send_notification_task`، كان السطر 10)

```python
# ⚠️ القنوات EMAIL/SMS/PUSH غير مُفعَّلة حاليًا (لا تكامل حقيقي مع أي
# مزوّد خارجي) — IN_APP هي القناة الوحيدة المدعومة فعليًا. راجع
# backlog-notification-delivery-stub-empty-non-inapp-channels.
@celery_app.task
def send_notification_task(notification_id: int, user_id: int, title: str, body: str, data: dict, channel: str):
    ...
```

**تأكيد `git diff`:** كل التعديل في الملفين اقتصر على 3 أسطر تعليق
مُضافة فوق كل `def` — صفر أي سطر منطق تغيّر (`git diff` كامل معروض
في §4 أدناه).

---

## 2) grep شامل — كل نقطة استدعاء فعلية لـ `CommunicationsService.send_notification(...)`

`grep -rn "\.send_notification\(" app/domains/` (استثنى تعريف الدالة
نفسها في `communications/service.py`) أظهر **5 نقاط استدعاء فعلية
فقط** في المشروع كله:

| # | الملف:السطر | القناة الممرَّرة فعليًا | ملاحظة |
|---|---|---|---|
| 1 | `app/domains/transport/service.py:875` | `channel="IN_APP"` (صراحة) | عبر helper داخلي `_send_notification` (مُستدعاة من `service.py:489`) |
| 2 | `app/domains/realestate/service.py:729` | `channel="IN_APP"` (صراحة) | عبر helper داخلي `_send_notification` (مُستدعاة من `service.py:348`) |
| 3 | `app/domains/automation/service.py:553` | بلا `channel` (موضعي: `user_id, title, body, data`) | يقع على القيمة الافتراضية `channel: str = NotificationChannel.IN_APP` في توقيع `send_notification` (`communications/service.py:49`) — يعني IN_APP فعليًا برضو |
| 4 | `app/domains/saas/service.py:396` | `channel="IN_APP"` (صراحة) | جوّه `check_past_due_subscriptions` (إشعارات فترة السماح) |
| 5 | `app/domains/communications/router.py:105` | `channel="IN_APP"` (صراحة، **مُثبَّتة كودًا في جسم الراوتر نفسه** — مش قيمة قادمة من جسم الطلب `NotificationCreate`) | `POST` endpoint عام لإرسال إشعار يدوي |

**بحث تكميلي** (`channel\s*=\s*["']?(EMAIL\|SMS\|PUSH)["']?` و
`NotificationChannel\.(EMAIL\|SMS\|PUSH)` عبر الباك إند بالكامل، مش
بس `send_notification(`) — تطابق واحد فقط:

```
app/domains/communications/models.py:164:
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.EMAIL)
```

هذا عمود `default` في موديل `CommunicationTemplate` (جدول قوالب
البريد/الإشعارات، `communications/models.py:155-172`) — **schema
default لحقل قالب، مش استدعاء فعلي لـ`send_notification` بقناة
EMAIL**. لا علاقة مباشرة بمسار الإرسال الفعلي (`send_notification` →
`send_notification_task`). ذُكر هنا للاكتمال فقط، خارج نطاق التوثيق
المطلوب.

---

## 3) الخلاصة والقرار

**صفر نقطة استدعاء فعلية في المشروع كله بتحاول تستخدم `EMAIL`/`SMS`/`PUSH`.**
كل الاستدعاءات الخمسة (وحتى الحالة الافتراضية بلا `channel` صريح)
تحل فعليًا على `IN_APP` — القناة الوحيدة الكاملة فعليًا (لأنها مجرد
صف يُقرأ لاحقًا من جدول `notifications`، بلا حاجة لتسليم خارجي).

**بالتالي القرار الثنائي المطروح في التعليمة الأصلية (تغيير النقاط
الفعلية لـIN_APP الآن، أو تركها backlog منفصل) أصبح غير ذي موضوع —
لا توجد نقطة تحتاج تغيير أصلًا.** التوثيق (التعليقات + تحديث
`PROGRESS_LOG.md`) كافٍ حاليًا لإغلاق الجانب "الالتباس" من البند —
الجانب المتبقي (بناء تكامل SMTP/FCM/Twilio حقيقي) يبقى مرتبطًا
بتوفر بنية تحتية خارجية (حسابات/مفاتيح فعلية من الفريق)، مش قرار
تقني معلَّق.

---

## 4) `git diff` كامل (للتأكيد — صفر تغيير منطقي)

```diff
diff --git a/eppne-backend/app/core/celery_app.py b/eppne-backend/app/core/celery_app.py
@@ -64,6 +64,9 @@ celery_app.conf.update(
 # ============================================================
 # 5. مهام وهمية (Fallback) لتجنب أخطاء الاستيراد في الكود القديم
 # ============================================================
+# ⚠️ القنوات EMAIL/SMS/PUSH غير مُفعَّلة حاليًا (لا تكامل حقيقي مع أي
+# مزوّد خارجي) — IN_APP هي القناة الوحيدة المدعومة فعليًا. راجع
+# backlog-notification-delivery-stub-empty-non-inapp-channels.
 @shared_task(name="send_notification_task")
 def send_notification_task(*args, **kwargs):
     """مهمة إرسال إشعار (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""

diff --git a/eppne-backend/app/domains/communications/tasks.py b/eppne-backend/app/domains/communications/tasks.py
@@ -6,6 +6,9 @@ from app.services.sms import send_twilio_sms
 
 celery_app = Celery("communications", broker=settings.REDIS_URL)
 
+# ⚠️ القنوات EMAIL/SMS/PUSH غير مُفعَّلة حاليًا (لا تكامل حقيقي مع أي
+# مزوّد خارجي) — IN_APP هي القناة الوحيدة المدعومة فعليًا. راجع
+# backlog-notification-delivery-stub-empty-non-inapp-channels.
 @celery_app.task
 def send_notification_task(notification_id: int, user_id: int, title: str, body: str, data: dict, channel: str):
     # هنا يتم جلب تفاصيل المستخدم من قاعدة البيانات (رقم الهاتف، البريد)
```

`router.py`, `service.py` (أي دومين)، `models.py` — **صفر diff** في
أي منها هذه الجلسة.

---

## 5) تحديث `PROGRESS_LOG.md`

أُضيف قسم جديد في آخر الملف (سجل تراكمي، القديم لم يُعدَّل):
`## [2026-09-08] تحديث backlog-notification-delivery-stub-empty-non-inapp-channels — 🟡 قرار مُتَّخذ`
— يتضمن جدول نقاط الاستدعاء الخمسة، نتيجة البحث التكميلي، والحالة
الجديدة بالنص المطلوب بالحرف.

---

## 6) الحالة النهائية

**`backlog-notification-delivery-stub-empty-non-inapp-channels` →
🟡 قرار مُتَّخذ وموثَّق.** صفر تعديل وظيفي، صفر قرار تقني معلَّق يحتاج
جلسة إضافية — الانتظار الوحيد المتبقي هو توفر بنية تحتية خارجية
(SMTP/FCM/Twilio) من الفريق، خارج نطاق أي عمل كود.
