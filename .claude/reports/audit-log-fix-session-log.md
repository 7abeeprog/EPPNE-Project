# جلسة: audit-log-signature-fix (المرحلة 1.2)

تاريخ البدء: 2026-08-18

## ✅ ختم إغلاق رسمي [2026-08-18]

**الحالة: مُغلَق رسميًا.** Backlog #14 (`audit-log-wrong-kwargs`) في `PROGRESS_LOG.md` محدَّث بحالة "مُغلَق" مع الرقم المصحَّح (95 موضع/18 ملف). الاكتشافان الجانبيان مُوثَّقان: `communications-service-get-user-missing-method` كبند Backlog جديد، وتحديث على بند #10 (affiliate) لموضع `realestate`. راجع الأقسام أدناه للتفصيل الكامل (التشخيص، القرار التصميمي، الديف المطبَّق، والتحقق الحي).

## 1. التعريف الفعلي لـ`audit_log()` — `app/core/audit.py:12-26`

```python
async def audit_log(
    action: str,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "ip": ip_address,
        "details": details or {}
    }
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
```

**حقيقة حاسمة:** الدالة **لا تكتب في أي جدول DB إطلاقًا** — مجرد `logging.info(json.dumps(...))` على logger باسم `eppne.audit`. لا `AsyncSession`، لا `INSERT`، لا استخدام لأي repository. هذا يحسم جزءًا كبيرًا من السؤال الحاسم: **لا يوجد schema/migration لهذه الدالة بالذات لأنها غير مرتبطة بجدول من الأساس.**

## 2. اكتشاف مهم: يوجد جدول `audit_logs` حقيقي في DB — لكنه غير مرتبط بهذه الدالة

- `finance/models.py:124-144` — `class AuditLog(Base)` → `__tablename__ = "audit_logs"`، بيه فعليًا `tenant_id` (NOT NULL، مُضاف عبر migration `002_add_tenant_id_to_audit_logs.py`) — لكن **لا يوجد عمود `resource_id`** حتى في هذا الموديل الصحيح.
- يُستخدم حصريًا عبر `FinanceService._create_audit_log()` (`finance/service.py:41-49`) التي تكتب عبر `self.audit_repo.create(...)` — **دالة منفصلة تمامًا، مستوردة ومستدعاة بشكل مختلف كليًا (`self._create_audit_log(...)` method-call، مش `audit_log()` function مستوردة)**. صفر تقاطع مع البند المطلوب إصلاحه.
- حتى النموذج "الصحيح" ده ما بيسجّلش `resource_id` — يعني **لا يوجد أي سابقة معمارية في المشروع كله لتخزين resource_id في audit trail**، لا في core ولا في finance.

**الخلاصة:** لا حاجة لأي migration/تعديل schema DB لإصلاح `audit_log()` — لأنها أصلاً بره أي DB. هذا يزيل شرط الإيقاف المتعلق بـmigration.

## 3. القرار التصميمي أ/ب — جدول الأدلة

| المعيار | الدليل |
|---|---|
| هل `audit_log()` بتكتب DB؟ | ❌ لا — logger.info فقط (قسم 1) |
| هل فيه جدول `audit_logs` بعمود `tenant_id`؟ | ✅ نعم، لكنه تابع لمسار كود منفصل تمامًا (`_create_audit_log`/`AuditLog` model في `finance`)، غير مستخدَم من `audit_log()` نفسها |
| هل فيه عمود `resource_id` فى أي جدول audit حقيقي بالمشروع؟ | ❌ لا — حتى الموديل الصحيح (`finance.AuditLog`) ما بيدعمهوش |
| تكلفة خيار (ب) الحقيقية هنا | **صفر تقريبًا** — لأن "توسيع الدالة لتستخدم tenant_id/resource_id فعليًا" هنا يعني فقط إضافتهم لـ`log_entry` dict قبل `json.dumps`، مش migration ولا عمود جديد (لأن مفيش جدول من الأساس) |

**القرار: خيار (ب) المعدَّل — بلا أي حاجة لتصنيفه "استثناء تصميمي غير قياسي" ولا لأي migration.** بما إن `audit_log()` غير مرتبطة بـDB إطلاقًا، فـ"الاستخدام الفعلي" لـ`tenant_id`/`resource_id` هو ببساطة تضمينهم في نفس الـJSON log entry اللي بيتكتب فعليًا الآن — بدون أي فرق تكلفة عن الخيار (أ) "استقبل وتجاهل". يعني عمليًا **أ وب بيصبحوا نفس التكلفة البرمجية هنا** (فرق سطرين في جسم الدالة)، فلا داعي للمفاضلة الاقتصادية — نأخذ (ب) لأنها بلا مقابل: توسيع التوقيع + تسجيل الحقلين فعليًا في الـJSON بدل تجاهلهم بصمت.

**التوقيع المقترح (بدون كود فعلي حتى الموافقة):**
```python
async def audit_log(
    action: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
```
مع إضافة `"tenant_id": tenant_id, "resource_id": resource_id` لـ`log_entry`.

---

## 4. جرد شامل مُتحقَّق مباشرة (قراءة كل موضع، مش عيّنة فقط) — تصحيحات جوهرية عن تقرير الجرد الأصلي

**كل الـ22 ملف اتقروا بالكامل (كل استدعاء audit_log لوحده، سطر بسطر) — مش عيّنة 15-20 كما طُلب، لأن التناقضات المكتشَفة أول 3 ملفات استوجبت الفحص الشامل.**

| # | الملف | عدد `audit_log(` الكلي | **مكسور فعليًا** (يمرر `tenant_id=`/`resource_id=` top-level) | **آمن فعليًا** (يطابق التوقيع الحالي 4 معاملات) | ملاحظة |
|---|---|---|---|---|---|
| 1 | `zamakana/service.py` | 9 | 9 | 0 | `user_id, tenant_id, action, resource_id, details` — ثابت في كل التسع |
| 2 | `invitations/service.py` | 7 | 7 | 0 | نفس الترتيب بالحرف |
| 3 | `manufacturing/service.py` | 12 | 12 | 0 | نمط `audit_log(**{...})` — نفس الحقول، سلوكيًا مطابق |
| 4 | `insurance/service.py` | 6 | 6 | 0 | نفس الترتيب |
| 5 | `arbitration_syndicates/service.py` | 6 | 6 | 0 | نفس الترتيب |
| 6 | `tenders_auctions/service.py` | 6 | 6 | 0 | نفس الترتيب |
| 7 | `social/service.py` | 8 | 8 | 0 | نفس الترتيب |
| 8 | `transport/service.py` | 5 | 5 | 0 | نفس الترتيب |
| 9 | `logistics/service.py` | 5 | 5 | 0 | نفس الترتيب |
| 10 | `realestate/service.py` | 4 | 4 | 0 | نمط `**{...}` أيضًا |
| 11 | `sovereign_entities/service.py` | 3 | 3 | 0 | نفس الترتيب |
| 12 | `digital_twin/service.py` | 3 | 3 | 0 | نفس الترتيب |
| 13 | `tourism_sports/service.py` | 3 | 3 | 0 | نفس الترتيب |
| 14 | `command/service.py` | 3 | 3 | 0 | ✅ تحقَّق مرتين بعد تناقض داخلي أثناء الفحص (راجع ملاحظة أسفل) |
| 15 | `health/service.py` | 3 | 3 | 0 | نفس الترتيب |
| 16 | `employment/service.py` | 2 | 2 | 0 | نفس الترتيب |
| 17 | `invoicing/service.py` | 2 | 2 | 0 | نفس الترتيب |
| 18 | `service_marketplace/service.py` | 1 | 1 | 0 | نفس الترتيب |
| 19 | `communications/router.py` | 8 | **7** | **1** | 🆕 تصحيح: `DEVICE_REGISTER` (سطر 190) بيمرر `user_id, action, details` فقط — آمن بالفعل. الباقي (7) بيمرروا `resource_id=` فقط (بلا `tenant_id` إطلاقًا — الراوتر مالوش `self.tenant_id`) → مكسورة لنفس السبب (`resource_id` غير موجود بالتوقيع) |
| 20 | `agritech/service.py` | 11 | **0** | **11** | 🆕 تصحيح جوهري: كل الاستدعاءات `user_id=, action=, details={"tenant_id": self.tenant_id, ...}` — **`tenant_id` مدموج جوّه `details` من الأساس، صفر `tenant_id=`/`resource_id=` top-level**. الدومين أصلًا غير موصول بـmain.py فمفيش تأثير حي، لكنه أيضًا **مش من ضمن الـTypeError bug إطلاقًا حتى لو اتوصل** |
| 21 | `ai_agents/service.py` | 4 | **0** | **4** | 🆕 نفس نمط `agritech` تمامًا — `tenant_id` جوّه `details`، صفر top-level kwargs زيادة |
| 22 | `commerce/service.py` | 1 | 0 | 1 | مطابق لملاحظة التقرير الأصلي (`_create_audit_log` الداخلية آمنة، والاستدعاء المباشر الوحيد سطر 554 بيمرر `user_id, action, details` فقط) |

**الإجمالي المُصحَّح: 95 موضع مكسور فعليًا (مش ~112) عبر 18 ملف (مش 22)** — الفرق:
- `agritech` (11) و`ai_agents` (4): آمنة بالفعل، تحمل `tenant_id` جوّه `details` مسبقًا.
- `commerce` (1): آمنة بالفعل (مؤكَّدة أصلًا في التقرير السابق).
- `communications/router.py`: 7 من 8 مكسورة، مش 8.

**ملاحظة منهجية عن `command/service.py`:** أثناء الفحص وقع خلط داخلي مؤقت (نتيجة تشغيل عدة استعلامات متوازية بترتيب غير متطابق مع التسميات) أدى لاستنتاج خاطئ عابر بأن الملف آمن — تم اكتشاف التناقض ذاتيًا وإعادة الفحص المباشر فورًا، والنتيجة النهائية المؤكَّدة: **3/3 مكسورة** (`BRAND_CREATED`, `REPORT_GENERATED`, `RECOMMENDATION_APPLIED` — كلها تمرر `tenant_id=`/`resource_id=` top-level). مذكور هنا للشفافية فقط، لا يؤثر على النتيجة النهائية.

## 5. تأكيد أنماط الاستدعاء — صفر نمط خامس/سادس جديد

كل الـ95 موضع المكسور يتبعوا **حرفيًا** واحد من نمطين سلوكيًا متطابقين:
- **كwargs مباشرة:** `audit_log(user_id=, tenant_id=, action=, resource_id=, details=)` — الترتيب دايمًا نفسه: `user_id → tenant_id → action → resource_id → details` (فيه استثناء ترتيب بسيط جدًا زي `zamakana`/`insurance` بيحطوا `# type: ignore` بعد `tenant_id=` مباشرة، تفصيل تعليقي مش بنيوي).
- **`**{...}` unpacking:** (`manufacturing` كل الـ12، `realestate` كل الـ4) — نفس المفاتيح الخمسة بالحرف كـdict، سلوكيًا مطابق 100% للكwargs المباشرة عند التنفيذ.

`communications/router.py` فيه تنويع حقيقي واحد: بيمرر `resource_id` **بلا `tenant_id`** (7 من 8 مرات) — موثَّق أعلاه، مش نمط سادس جديد، فقط subset من نفس الحقول الخمسة.

**لا يوجد استدعاء واحد يمرر kwarg بغير `user_id/tenant_id/action/resource_id/details` من أي نوع.** السؤال (2) في طلب المستخدم مُجاب: صفر تنويعات غير متوقَّعة.

## 6. فحص الدوال المستثناة — تأكيد الفصل التام

- `ai_governance/service.py` (3 مواضع) — `self.repo.create_audit_log(tenant_id=, agent_id=, admin_user_id=, action=, new_value=/old_value=, ip_address=)` — **method مختلفة تمامًا على `repo`، تقبل أي kwargs بنيويًا (repository pattern)، صفر علاقة بدالة `audit_log()` المستوردة.** غير متأثرة بأي تعديل.
- `finance/service.py._create_audit_log` و`commerce` (الاستخدام الداخلي) — دوال منفصلة كليًا (قسم 2 أعلاه). غير متأثرة.

## 7. 🔴🔴 اكتشاف حرج جديد — يستوجب توقف فوري قبل أي قرار نهائي

**هذا البند يغيّر تأطير خطورة الباج بالكامل، ومطلوب تأكيد المستخدم قبل الاستمرار (شرط إيقاف #2 في طلب الجلسة: "اكتشاف حرج جديد").**

الافتراض الأصلي في وصف المهمة كان: "الأثر الحقيقي هو إن الـaudit log بيفشل يتسجل بصمت في كل مكان تقريبًا" — **تم التحقق المباشر وهذا غير دقيق لمعظم المواضع الـ95:**

1. **لا يوجد `try/except` حوالين أي من الاستدعاءات المكسورة الـ95** (تم فحص السياق الكامل لكل موضع في القسم 4 — القسم ج من تقرير الجرد الأصلي وثّق `try/except` صامتة حوالين أنماط تانية تمامًا (`register_commission`, `check_and_consume`, `execute_agent_action`, `create_invoice`) لكن **صفر منها يغلّف `audit_log()` نفسها**).
2. **`app/main.py` مسجَّل فيه بس 3 exception handlers مخصَّصة**: `SovereignError`, `IdempotencyError`, `RateLimitError` — **لا يوجد generic `Exception` handler**. أي `TypeError` من `audit_log()` غير المتوقَّع = Starlette الافتراضي (`ServerErrorMiddleware`) بيرجع **500 خام مباشر للـclient الحقيقي**.
3. **`app/core/database.py.get_db()`**: `async with AsyncSessionLocal() as session: try: yield session; finally: await session.close()` — **لا commit تلقائي، ولا rollback صريح** — بس `close()` في `finally`. الـcommit مسؤولية كل service method صراحة (`await self.db.commit()`).
4. **تأكَّد بالقراءة المباشرة (`insurance/service.py:121-137`, `health/service.py:255-263`): الـ`commit()` بييجي *بعد* استدعاء `audit_log()` المكسور في نفس الدالة.** يعني لما `audit_log()` يرمي `TypeError`:
   - الاستثناء يتصعّد (uncaught) → الطلب يرجع 500 للمستخدم الحقيقي.
   - `self.db.commit()` **ماينفَّذش أبدًا** → أي `INSERT` سابق في نفس الدالة (البوليصة، الوظيفة، الكيان، الفاتورة...) **بيترفَض ضمنيًا** (session بتتقفل من غير commit في `finally`).
   - `insurance/service.py:121-137` تحديدًا جوّه `async with self.db.begin_nested()` — يعني الاستثناء بيتصعّد من جوّه savepoint كمان.

**الخلاصة الحرجة:** لأغلب الـ95 موضع (لسه محتاج تأكيد commit-ordering لكل ملف على حدة، عيّنة insurance/health تؤكد النمط)، البج ده **مش "audit trail ناقص بصمت"** — هو **"العملية الأساسية (إنشاء بوليصة تأمين، وظيفة، كيان سيادي، فاتورة، منشور اجتماعي...) بترجع 500 وما بتتحفظش في الـDB إطلاقًا"** لأي endpoint حي بيلمس أي دالة من الـ18 ملف دي. ده أوسع وأخطر بكتير من مجرد فقدان سجل تدقيق — ده يعني أجزاء كاملة من المنصة الحية (insurance, health, invoicing, communications, social...) معطَّلة فعليًا API-level لأي عملية كتابة بتستدعي `audit_log()`.

**ما لم يتأكَّد بعد (يحتاج قرارك قبل التوسّع فيه، لأنه خارج نطاق "أصلح audit_log فقط"):**
- ترتيب `commit()` مقابل `audit_log()` في باقي الـ16 ملف (لسه اتفحص insurance وhealth بس بدقة لهذا التفصيل تحديدًا).
- هل فيه اختبارات E2E/يدوية سبق نفّذت أي من العمليات دي فعليًا واكتشفت الـ500 ده، ولا الكود ده مجرد "مكتوب ومش متحقَّق منه" زي أنماط تانية موثَّقة سابقًا في المشروع (EventBus كان مثال مطابق).

---

## الحالة: متوقف بانتظار توجيهك

**السؤال المطروح عليك:**
1. هل تريد المتابعة بنفس نطاق المهمة الأصلي (توسيع توقيع `audit_log()` فقط) مع توثيق هذا الاكتشاف كـ"أثر جانبي متوقَّع سيُصلَح تلقائيًا بمجرد إصلاح التوقيع" (لأن التوقيع الأوسع هيمنع الـTypeError من الأساس، فالـ500 هيختفي تلقائيًا كنتيجة مباشرة لنفس الإصلاح، بلا حاجة لأي كود إضافي)؟
2. أم تريد فتح نطاق فحص منفصل أولًا لتحديد بالضبط كام endpoint حي متأثر بالـ"500 + rollback الصامت" ده قبل المتابعة، باعتباره اكتشافًا يستحق توثيق Backlog مستقل؟

بالنظر لأن الإصلاح المقترح (توسيع التوقيع ليقبل `tenant_id`/`resource_id`) **يحل الـ500 تلقائيًا كأثر جانبي مباشر** (لأن الـTypeError مصدره فقط kwargs غير معروفة)، رأيي: **نمضي بنفس خطة الإصلاح الأصلية**، ونوثّق هذا الاكتشاف كسبب إضافي يرفع أولوية الإصلاح (مش مجرد تحسين audit trail، بل استعادة عمليات كتابة حية كسورة)، ونضيفه كبند Backlog موثَّق بعد الإغلاق. لكن القرار لك.

---

## قرار المستخدم (2026-08-18)

✅ موافقة على القرار 1 — نكمل بنفس نطاق الإصلاح الأصلي (توسيع التوقيع فقط)، اكتشاف الـ500/rollback الصامت يُوثَّق كسبب إضافي يرفع الأولوية، مش نطاق منفصل.
✅ الأرقام المصحَّحة (95 موضع/18 ملف) معتمدة.
✅ قرار عدم لمس `agritech`/`ai_agents`/`commerce` (آمنة أصلاً) و`communications/router.py` (هيتصلح تلقائيًا رغم غياب `tenant_id`) — مقبول ومنطقي.
📌 تعديل على خطة التحقق الحي: لكل دومين عيّنة، التحقق لازم يثبت **اثنين معًا**: (1) `audit_log()` نجحت بلا `TypeError`، (2) العملية الأساسية (بوليصة/وظيفة/فاتورة/إلخ) اتحفظت فعليًا على القرص عبر `SELECT` مستقل — تأكيد كامل إن الـ500/rollback الصامت (القسم 7) اختفى فعليًا، مش بس "صفر استثناء".

## 8. الديف الكامل المقترح — `app/core/audit.py` (بانتظار الموافقة النهائية لتطبيقه)

```diff
--- a/eppne-backend/app/core/audit.py
+++ b/eppne-backend/app/core/audit.py
@@ -9,17 +9,21 @@ audit_logger = logging.getLogger("eppne.audit")
 audit_logger.setLevel(logging.INFO)
 
 # سيتم إرفاق معالج ملف خاص به في logging_conf.py لاحقاً
-async def audit_log(
-    action: str, 
-    user_id: Optional[int] = None, 
-    details: Optional[Dict[str, Any]] = None,
-    ip_address: Optional[str] = None
-) -> None:
+async def audit_log(
+    action: str,
+    user_id: Optional[int] = None,
+    tenant_id: Optional[int] = None,
+    resource_id: Optional[int] = None,
+    details: Optional[Dict[str, Any]] = None,
+    ip_address: Optional[str] = None
+) -> None:
     """تسجيل حركات النظام بصيغة JSON منظمة للامتثال."""
     log_entry = {
         "timestamp": datetime.now(timezone.utc).isoformat(),
         "action": action,
         "user_id": user_id,
+        "tenant_id": tenant_id,
+        "resource_id": resource_id,
         "ip": ip_address,  # سيتم تشفيره في طبقة الأمان قبل الوصول لهنا
         "details": details or {}
     }
     audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
```

**الملف كامل بعد التطبيق (للمرجعية، مش جزء من الـdiff نفسه):**

```python
# app/core/audit.py
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Logger مخصص للسجلات الأمنية
audit_logger = logging.getLogger("eppne.audit")
audit_logger.setLevel(logging.INFO)

# سيتم إرفاق معالج ملف خاص به في logging_conf.py لاحقاً
async def audit_log(
    action: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    """تسجيل حركات النظام بصيغة JSON منظمة للامتثال."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "resource_id": resource_id,
        "ip": ip_address,  # سيتم تشفيره في طبقة الأمان قبل الوصول لهنا
        "details": details or {}
    }
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
```

**نطاق التغيير:** ملف واحد فقط (`app/core/audit.py`)، صفر لمس لأي من الـ95 موضع الاستدعاء، صفر migration، صفر تعديل على أي دالة تانية (`_create_audit_log`, `repo.create_audit_log`).

---

## 9. التطبيق الفعلي — git diff/status خام (2026-08-18)

```
$ git diff -- app/core/audit.py
diff --git a/eppne-backend/app/core/audit.py b/eppne-backend/app/core/audit.py
index 8f05c91..78b825a 100644
--- a/eppne-backend/app/core/audit.py
+++ b/eppne-backend/app/core/audit.py
@@ -10,8 +10,10 @@ audit_logger.setLevel(logging.INFO)
 
 # سيتم إرفاق معالج ملف خاص به في logging_conf.py لاحقاً
 async def audit_log(
-    action: str, 
-    user_id: Optional[int] = None, 
+    action: str,
+    user_id: Optional[int] = None,
+    tenant_id: Optional[int] = None,
+    resource_id: Optional[int] = None,
     details: Optional[Dict[str, Any]] = None,
     ip_address: Optional[str] = None
 ) -> None:
@@ -20,6 +22,8 @@ async def audit_log(
         "timestamp": datetime.now(timezone.utc).isoformat(),
         "action": action,
         "user_id": user_id,
+        "tenant_id": tenant_id,
+        "resource_id": resource_id,
         "ip": ip_address,  # سيتم تشفيره في طبقة الأمان قبل الوصول لهنا
         "details": details or {}
     }

$ git status --short app/core/audit.py
 M app/core/audit.py
```

مطابق تمامًا للديف المعتمَد في القسم 8 — صفر انحراف.

## 10. التحقق الحي — نتائج فعلية (DB حقيقي: `eppne_db` container، DATABASE_URL من `.env`)

المنهجية لكل عيّنة: (1) التقاط سجل `eppne.audit` logger فعليًا لإثبات `audit_log()` نجحت بلا `TypeError`، (2) `SELECT` من **جلسة/اتصال DB جديد تمامًا** (مش نفس الجلسة اللي كتبت) لإثبات إن العملية الأساسية اتحفظت فعليًا — يعني الـ500/rollback الصامت (القسم 7) اختفى فعليًا، مش بس "صفر استثناء". الكود الكامل: `scratchpad/verify_audit_log_fix.py`. بيانات الاختبار (سياسة تأمين، عقدة زمكان، رسالة بريد، عقد إيجار) اتنضّفت من الـDB بعد التحقق (`DELETE` مباشر، مش جزء من منطق التطبيق).

| # | العيّنة | النمط المُختبَر | audit_log() نجحت؟ | دليل السجل الملتقَط | SELECT مستقل يثبت الحفظ |
|---|---|---|---|---|---|
| 1 | `insurance.create_policy` | kwargs مباشرة (`user_id, tenant_id, action, resource_id, details`)، جوّه `begin_nested()` | ✅ | `{"action": "POLICY_CREATED", "user_id": 2, "tenant_id": 1, "resource_id": 6, ...}` | ✅ `(6, 'AUDIT-FIX-VERIFY-POLICY', 'MEDICAL')` من `insurance_policies` |
| 2 | `zamakana` (نمط `ZAMAKANA_NODE_CREATED`) | نفس kwargs، لكن عبر `ZamakanaRepository.create_node` مباشرة + استدعاء `audit_log()` بنفس شكل السطر 92-98 الحقيقي بالحرف — **تجاوزنا `ZamakanaService.create_node()` كاملة عمدًا** لأنها بتصطدم ببج منفصل تمامًا وموثَّق مسبقًا (#12: `SaaSControlService.can_access_service(tenant_id, feature)` بمعاملين زيادة عن التوقيع الحقيقي `can_access_service(service_code)`) — بج غير مرتبط بـaudit_log، خارج نطاق هذا الإصلاح | ✅ | `{"action": "ZAMAKANA_NODE_CREATED", "user_id": 2, "tenant_id": 1, "resource_id": 1, ...}` | ✅ `(1, 'AUDIT-FIX-VERIFY-NODE', 'ERA')` من `zamakana_nodes` |
| 3 | `communications/router.py` (`MAIL_MOVE_TO_TRASH`) | النمط الناقص (`user_id, action, resource_id` فقط — **بلا `tenant_id` وبلا `details`**) | ✅ | `{"action": "MAIL_MOVE_TO_TRASH", "user_id": 3, "tenant_id": null, "resource_id": 1, "details": {}}` | ✅ `(1, 'TRASH')` من `mailbox_items` — الـfolder اتغيّر فعليًا |
| 4 | `realestate.rent_unit` | نمط `audit_log(**{...})` unpacking | ✅ | `{"action": "RENTAL_CONTRACT_CREATED", "user_id": 2, "tenant_id": 1, "resource_id": 7, ...}` (+ `INVOICE_CREATED` من `invoicing` كمكسب إضافي غير مقصود — نفس الإصلاح) | ✅ `(7, 2, Decimal('500.00000000'))` من `rental_contracts` |

### اكتشافان جديدان أثناء التحقق (موثَّقان، غير مُصلَحان — خارج النطاق)

1. **`communications/service.py:29,36` — `CommunicationsService._get_user_tenant`/`_get_user_email` بيستدعوا `self.user_repo.get_user(user_id)` — الدالة دي مش موجودة على `UserRepository` (الصحيحة `get_by_id`).** هذا اكتُشف أثناء محاولة اختبار `send_notification` الأصلي (العيّنة رقم 3 المخطَّطة أولًا) — الاستثناء `AttributeError: 'UserRepository' object has no attribute 'get_user'` بيحصل **قبل الوصول لـ`audit_log()` من الأساس**، يعني `NOTIFICATION_SEND` endpoint معطَّل بالكامل حاليًا لسبب مختلف تمامًا عن بند #14. تم استبدال العيّنة بـ`MAIL_MOVE_TO_TRASH` (نفس الملف، نفس نمط audit_log الناقص، بدون الاعتماد على الدالة المكسورة) لإتمام التحقق المطلوب. **موصى بفتح بند Backlog منفصل له.**
2. **`realestate/service.py:581-595` (`_register_affiliate_commission`) — `self.user_repo.get_by_id(user_id)` بيتنادى بمعامل واحد بس (`user_id`)، لكن `UserRepository.get_by_id` الحقيقية محتاجة `tenant_id` كمان.** ظهر فعليًا في اختبار العيّنة 4 (`Affiliate registration failed: UserRepository.get_by_id() missing 1 required positional argument: 'tenant_id'`) — لكنه **مُحتوى بالكامل** داخل `try/except` صامت موثَّق مسبقًا في القسم ج من تقرير الجرد الأصلي (فقدان عمولة affiliate بصمت)، فمفيش تأثير على نتيجة الاختبار أو على استمرارية العملية. **موصى بضمّه لبند affiliate الموثَّق مسبقًا (#10) بدل فتح بند جديد.**

**كلا الاكتشافين لا يمسّان `audit_log()` ولا أي من الـ95 موضع المُصلَحة — مجرد ملاحظات جانبية ظهرت أثناء التحقق الحي، موثَّقة هنا للشفافية فقط.**

### الخلاصة

✅ **الإصلاح يعمل بنجاح تام عبر الأنماط الأربعة الموثَّقة كلها** (kwargs مباشرة، `**{...}` unpacking، نمط ناقص بلا `tenant_id`). ✅ **الـ500/rollback الصامت الموثَّق في القسم 7 اختفى فعليًا** — تأكَّد بالـSELECT المستقل إن العمليات الأساسية (بوليصة، عقدة معرفية، بريد، عقد إيجار) اتحفظت على القرص بنجاح، وليس فقط "صفر استثناء ظاهري".
