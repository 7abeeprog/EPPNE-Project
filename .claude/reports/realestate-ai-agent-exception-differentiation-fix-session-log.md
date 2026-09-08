# جلسة: realestate-ai-agent-exception-differentiation-fix

**النطاق:** تعديل ضيق جدًا — سطر الـ`except` بس في
`realestate/service.py:365-369` (جوّه `buy_fractional_ownership`).
بدون `raise`، بدون تغيير سلوك العملية المالية. بناءً على تحقيق
`.claude/reports/realestate-ai-agent-silent-swallow-investigation-session-log.md`.

---

## 1) فحص نظام alerting/monitoring خارجي

```
grep -rn "sentry_sdk\|import sentry\|SENTRY" --include="*.py" .
grep -rni "sentry\|rollbar\|datadog\|bugsnag\|newrelic\|opentelemetry" requirements*.txt pyproject.toml
```

**صفر نتائج.** لا يوجد Sentry SDK ولا أي مكتبة alerting/monitoring
خارجية مُثبَّتة أو مُستخدَمة في أي مكان في المشروع (لا في الكود ولا
في `requirements*.txt`). بالتالي، طبقًا للتعليمات، **اكتُفي بتمييز
مستوى الـlogger المحلي فقط** — بدون أي استدعاء alerting إضافي.

---

## 2) التعديل المُطبَّق

**قبل:**
```python
try:
    await ai.execute_agent_action(agent_id=2, action_type="ANALYZE_PROJECT", payload={"unit_id": unit_id, "price": float(cost), "percentage": float(percentage), "buyer_id": buyer_id}, executor_user_id=buyer_id, idempotency_key=f"REALESTATE-FRAC-T{tenant_id}-{idempotency_key or uuid.uuid4().hex[:8]}")
except Exception as e:
    logger.error(f"AI analysis failed for fractional ownership purchase (unit {unit_id}): {e}")
```

**بعد** (`realestate/service.py:365-369`):
```python
try:
    await ai.execute_agent_action(agent_id=2, action_type="ANALYZE_PROJECT", payload={"unit_id": unit_id, "price": float(cost), "percentage": float(percentage), "buyer_id": buyer_id}, executor_user_id=buyer_id, idempotency_key=f"REALESTATE-FRAC-T{tenant_id}-{idempotency_key or uuid.uuid4().hex[:8]}")
except (NotFoundError, PermissionDeniedError) as e:
    logger.warning(f"AI analysis skipped for fractional ownership purchase (unit {unit_id}): {e}")
except Exception as e:
    logger.error(f"AI analysis failed unexpectedly for fractional ownership purchase (unit {unit_id}): {e}")
```

- `NotFoundError` و`PermissionDeniedError` (`app.core.errors`) كانا
  مستوردين بالفعل في أعلى الملف (`realestate/service.py:19`) —
  صفر import جديد.
- **صفر `raise`** في الفرعين. **صفر لمس** على أي كود قبل أو بعد
  الكتلة — الشراء المالي (`finance.transfer`، إنشاء
  `PropertyOwnership`، الـ`commit()` الرئيسي) بيكمل وينجح تمامًا زي
  ما كان دايمًا، بمعزل عن نجاح أو فشل تحليل الـAI.
- **رسالة `logger.error` اتغيّرت من "failed" لـ"failed unexpectedly"**
  عمدًا (فرق واضح في الرسالة نفسها بين الفرعين لتسهيل الفلترة في
  logs/monitoring مستقبلًا) — التعليمات سمحت بتعديل التفاصيل الدقيقة
  لو الأسماء مختلفة، واستُخدمت هذه الحرية لجعل الرسالتين قابلتين
  للتمييز نصيًا كمان مش بس بمستوى الـlog.

## 3) نطاق اللمس — تأكيد الالتزام بالحدود

`git diff` على `realestate/service.py` (بعد استبعاد hunk تاني موجود
مسبقًا في نفس الملف من جلسة سابقة غير مرتبطة — تعديل
`_check_saas_limits`/`SaaSControlService` كان موجود في working tree
**قبل** بدء هذه الجلسة، لم تُنشئه ولم تلمسه هذه الجلسة):

```diff
         try:
             await ai.execute_agent_action(agent_id=2, action_type="ANALYZE_PROJECT", payload={...}, executor_user_id=buyer_id, idempotency_key=f"...")
+        except (NotFoundError, PermissionDeniedError) as e:
+            logger.warning(f"AI analysis skipped for fractional ownership purchase (unit {unit_id}): {e}")
         except Exception as e:
-            logger.error(f"AI analysis failed for fractional ownership purchase (unit {unit_id}): {e}")
+            logger.error(f"AI analysis failed unexpectedly for fractional ownership purchase (unit {unit_id}): {e}")
```

- **لا لمس** على `invoicing.create_invoice` المجاورة (سطور 370-379) —
  تركت بحالها بنفس `try/except Exception` العام.
- **لا لمس** على أي من الـ16 موضع الآخر لـ`execute_agent_action` في
  المشروع (`employment`, `zamakana`, `tourism_sports`,
  `tenders_auctions`, `manufacturing`, `logistics`, `insurance`,
  `social`, `command`, `automation`, `arbitration_syndicates`,
  `transport`, `invitations`, `tasks/agritech.py`).
- **لا `raise`** أُضيف في أي فرع.

---

## 4) تحقق حي

سكريبت throwaway منفصل (`verify_realestate_except_split.py`، بنفس
منهجية `tests/test_ai_agents_execute_action.py`: `TENANT_ID=1`،
`EXISTING_LAND_ASSET_ID=1`، مستخدمين/وحدة/تطوير throwaway، `db`
حقيقية عبر `AsyncSessionLocal`، تنظيف كامل في `finally`) — **صفر
تعديل على أي ملف اختبار أو كود إنتاج**. تم تشغيله بـ
`venv/Scripts/python.exe` (بيئة المشروع الفعلية).

### سيناريو 1 — `NotFoundError` (agent_id=2 غير موجود فعليًا في بيئة الـdev الحالية)

استُدعيت `buy_fractional_ownership` بشكل حقيقي كامل (`_check_saas_limits`
و`_check_ai_governance` بس اتعملهم monkeypatch لـno-op لعزل التركيز
على الاستثناء المستهدف، بنفس أسلوب الاختبارات الرسمية الموجودة في
الملف). النتيجة الفعلية من تشغيل حي:

```
[WARNING] eppne: AI analysis skipped for fractional ownership purchase (unit 235): وكيل 2 غير موجود
OK: الشراء المالي نجح -> ownership.id=27, owner_user_id=1971
PASS: logger.warning ظهر بالظبط، صفر logger.error، والشراء نجح رغم فشل تحليل الـAI.
```

مطابقة تامة للمتوقَّع: `NotFoundError` (فشل "متوقَّع وسليم" — نفس
السيناريو الموثَّق حيًا سابقًا في `PROGRESS_LOG.md` لـ
`ai-agent-id-2-missing-seed-masks-execute-action-old-bug`) ظهرت
بمستوى `WARNING` فقط، والعملية المالية (`PropertyOwnership` id=27،
`owner_user_id` مطابق للمشتري) نجحت كاملة بلا أي أثر جانبي.

### سيناريو 2 — فشل برمجي مصطنع (`TypeError`، محاكاة باج #16 الأصلي)

بمحاكاة `AIAgentsService.execute_agent_action` نفسها (monkeypatch في
السكريبت فقط، صفر لمس على `ai_agents/service.py` الحقيقية) لترمي
`TypeError` مباشرة — بنفس طبيعة باج Backlog #16 الأصلي الموثَّق
(معامل زايد على التوقيع). النتيجة الفعلية:

```
[ERROR] eppne: AI analysis failed unexpectedly for fractional ownership purchase (unit 236): execute_agent_action() got an unexpected keyword argument 'tenant_id' (simulated Backlog #16 regression)
OK: الشراء المالي نجح -> ownership.id=28, owner_user_id=1973
PASS: logger.error ظهر بالظبط (بكلمة unexpectedly)، صفر logger.warning، والشراء نجح رغم الخطأ البرمجي في الـAI.
```

مطابقة تامة للمتوقَّع: `TypeError` (فشل برمجي حقيقي) ظهرت بمستوى
`ERROR` مع كلمة "unexpectedly" الجديدة في الرسالة، والعملية المالية
نجحت كاملة برضه (`ownership.id=28`).

### تنظيف وتحقق مستقل بعد التشغيل

فحص مستقل بعد انتهاء السكريبت (استعلامات SQL منفصلة تمامًا عن
منطق التنظيف الداخلي بالسكريبت):

```
leftover verify users: 0
agent id=2 exists: None
leftover verify developments: 0
leftover verify units: 0
leftover verify ownerships: 0
```

**صفر أثر throwaway متبقي.**

---

## 5) الخلاصة

- الابتلاع الصامت الكامل السابق (`except Exception` بلا تمييز) اتحل
  محله فرعان: `NotFoundError`/`PermissionDeniedError` (فشل متوقَّع
  — agent غير موجود/غير نشط) → `logger.warning`، وأي فشل تاني (خطأ
  برمجي حقيقي) → `logger.error` برسالة مميّزة ("unexpectedly").
- **العملية المالية غير متأثرة إطلاقًا** — تأكد حيًا في السيناريوهين:
  الشراء ينجح ويُنشئ `PropertyOwnership` بغض النظر تمامًا عن نتيجة
  تحليل الـAI، بلا أي `raise` جديد.
- **مفيش نظام alerting خارجي في المشروع أصلًا** (تأكيد grep)، فالحل
  اكتفى بتمييز مستوى الـlogger المحلي فقط، بدون أي كود alerting
  إضافي غير موجود له بنية تحتية.
- **صفر لمس** على `invoicing.create_invoice` المجاورة أو أي من الـ16
  موضع الآخر لـ`execute_agent_action` في المشروع — بند اليوم يخص
  `realestate` فقط كما طُلب.
