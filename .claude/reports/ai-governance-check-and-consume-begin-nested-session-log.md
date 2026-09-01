# جلسة: ai-governance-check-and-consume-begin-nested

**تاريخ:** 2026-09-01
**البند:** `ai-governance-check-and-consume-commit-inside-begin-nested` (بند Backlog
موثَّق أثناء جلسة `backlog-16-begin-nested-commit-conflict`، §6 من
`.claude/reports/backlog-16-begin-nested-commit-session-log.md`).

**القاعدة المتبعة:** صفر تنفيذ حتى الموافقة الصريحة — نفس مستوى الحذر المطبَّق
في جلسة #16 (execute_agent_action) بالضبط.

**الحالة: ✅ مُغلَق بالكامل — الموافقة الصريحة صدرت، التنفيذ تم، التحقق الحي نجح.**

---

## 1) الكود الفعلي لـ `check_and_consume` (`ai_governance/service.py:146-205`)

مؤكَّد بالقراءة الكاملة — **نفس بنية `execute_agent_action` بالضبط**: وحدة
معاملة كاملة ومستقلة بذاتها.

```python
async def check_and_consume(self, agent_id, user_id, action_type, tokens, cost,
                             idempotency_key=None, request_tokens=0, completion_tokens=0) -> bool:
    if idempotency_key:
        existing_log = await self.repo.get_usage_log_by_idempotency(idempotency_key)
        if existing_log:
            return True                                    # ⚠ راجع #6 أدناه — TypeError منفصل

    active_quotas = await self.repo.get_active_quotas(agent_id=agent_id, tenant_id=self.tenant_id)

    async with self.db.begin_nested():                     # سطر 165
        for quota in active_quotas:
            ...
            if (current_usage + usage_to_add) > limit_value:
                return False                                 # خروج طبيعي (return)، بلا استثناء — آمن
            await self.repo.create_or_update_quota(...)
        await self.repo.create_usage_log(...)                # سطر 190

    await self.db.commit()                                   # 🔴 سطر 203 — نفس نمط execute_agent_action

    return True
```

---

## 2) جرد كامل لمواضع استدعاء `check_and_consume()` عبر المشروع (15 موضع، 14 دومين + الراوتر)

| # | الموضع | جوّه `begin_nested()`؟ | كتابة قبلها في نفس البلوك؟ |
|---|---|---|---|
| 1 | `zamakana/service.py:498` (`generate_ai_analysis`) | ❌ مستقل | — |
| 2 | `transport/service.py:75` (`_check_ai_governance` helper) | ❌ مستقل | — |
| 3 | `tourism_sports/service.py:432` (`get_match_suggestions`-مكافئ transfer) | ❌ مستقل (قبل `begin_nested()` سطر 441) | — |
| 4 | `tenders_auctions/service.py:202` (تقييم عطاء) | ❌ مستقل (صفر `begin_nested()` بالملف كله) | — |
| 5 | `social/service.py:304` (`get_match_suggestions`) | ❌ مستقل (قبل `begin_nested()` سطر 490) | — |
| 6 | `service_marketplace/service.py:159` (`purchase_service`) | ❌ مستقل (قبل `begin_nested()` سطر 218) | — |
| 7 | `realestate/service.py:72` (`_check_ai_governance` helper) | ✅ **جوّه** `begin_nested()` سطر 288 لـ`buy_fractional_ownership` (استدعاء عبر `_check_ai_governance` سطر 303) | ❌ لا — كله `SELECT` قبلها (`get_unit`, `get_total_ownership_percentage`) |
| 8 | `manufacturing/service.py:297` (`start_production`) | ❌ مستقل (قبل `begin_nested()` سطر 333) | — |
| 9 | `manufacturing/service.py:659` (`analyze_and_schedule_maintenance`) | ❌ مستقل (قبل `begin_nested()` سطر 688) | — |
| 10 | `command/service.py:337` (`generate_ai_recommendations`) | ❌ مستقل (صفر `begin_nested()` بالملف كله) | — |
| 11 | `logistics/service.py:542` (`generate_forecast`) | ❌ مستقل (قبل `begin_nested()` سطر 580؛ `begin_nested()` سطر 504 خاص بميثود مختلف تمامًا `create_equipment_maintenance`، مُغلَق قبل 542) | — |
| 12 | `arbitration_syndicates/service.py:91` (فتح نزاع) | ❌ مستقل (صفر `begin_nested()` بالملف كله) | — |
| 13 | `invitations/service.py:379` (`chat_with_ai`) | ❌ **مستقل بالفعل** — رُفعت عمدًا فوق `begin_nested()` (سطر 418) أثناء إصلاح #16 نفسه (تعليق سطر 390-393 في الكود يوثّق هذا القرار صراحة) | — |
| 14 | `insurance/service.py:339` (`submit_claim`) | ❌ مستقل (قبل `begin_nested()` سطر 362، وملفوفة أصلاً بـ`try/except` مستقل) | — |
| 15 | `ai_governance/router.py:191` (`POST /agents/{id}/check-and-consume`) | ❌ مستقل (نداء مباشر من endpoint، `try/except` عام يمسك كل استثناء ويرجعه كـ`{"allowed": false}`) | — |

**النتيجة: 14 من 15 موضع مستقلون تمامًا (يعتمدون على الـ`commit()` الداخلي، بالضبط
زي 17 من 19 في تحليل `execute_agent_action`) — موضع واحد بس جوّه `begin_nested()`
لحد تاني: `realestate.buy_fractional_ownership` (عبر `_check_ai_governance`).**
هذا نفس النمط البنيوي بالحرف اللي أدى لقرار #16 (نقل النداء بره حدود
`begin_nested()` بدل تعديل الدالة المشتركة).

**الفرق الوحيد المهم عن #16:** هنا **صفر موضع تاني بحاجة لرفع (hoist) معقّد
زي invitations** — الموضع الوحيد المتأثر (`realestate`) نتيجته (`result`)
غير مُستخدَمة فعليًا خارج `_check_ai_governance` نفسها (بترجع `result` لكن
الكولر `buy_fractional_ownership` سطر 303 بينادي `_check_ai_governance` كـ
statement مجرد، بلا `await result =`) — يعني نفس نمط "نقل بعد الـcommit"
البسيط زي `execute_agent_action` في نفس الدالة بالضبط، مش نمط "رفع" invitations.

---

## 3) التحقق الحي — نتائج فعلية (سكربت مستقل، DB حقيقية `eppne_db`، تينانت 1)

سكربت throwaway (`scratchpad/repro_ai_governance_begin_nested.py`، صفر لمس على كود
الإنتاج) يحاكي بنية `buy_fractional_ownership` بالحرف: `async with db.begin_nested():`
→ `SELECT` (مكافئ `get_unit`) → نداء `check_and_consume()` الحقيقي **ملفوف بـ
`try/except` مطابق لـ`_check_ai_governance` بالضبط** → `SELECT` تالية (مكافئ
`_get_land_owner_for_unit`) **داخل نفس الـ`begin_nested()`**، بوكيل throwaway حقيقي
(FK-safe، `owner_id=772`).

**🔴 اكتشاف مهم: الآلية مختلفة قليلًا عن `execute_agent_action`، لكن النتيجة النهائية
لنفس الخطورة بالضبط:**

**تشغيلة 1 (بدون SELECT تالية):**
```
[step] pre-read done inside begin_nested(), now calling check_and_consume()...
[step] check_and_consume() returned normally (no exception)     <- 🔴 غير متوقَّع! لا استثناء هنا إطلاقًا
[step] outer db.commit() succeeded without error
[step] session still usable, AgentUsageLog rows for agent=1
```
**السبب:** خلافًا لـ`execute_agent_action` (اللي بتكتب مباشرة بلا `begin_nested()`
خاص بيها ثم تعمل `commit()`)، `check_and_consume()` **بتفتح `begin_nested()` خاصة
بيها هي (سطر 165)، تكتب جوّاها، ثم تُغلقها بشكل طبيعي (`__aexit__` سليم)، وبعد
كده بس** بتعمل `await self.db.commit()` (سطر 203). لما بيتنفذ الـ`commit()` ده،
الترانزاكشن النشطة الوحيدة المتبقية هي `begin_nested()` **الخارجية** (بتاعة
الكولر)، فـ`commit()` بيقفلها **فعليًا على مستوى الـSession** — لكن بهدوء، بدون
استثناء فوري، لأن `check_and_consume()` نفسها خلصت شغلها بنجاح ورجعت.

**تشغيلة 2 (مع SELECT تالية داخل نفس البلوك — يحاكي `_get_land_owner_for_unit`):**
```
[step] check_and_consume() returned normally (no exception)
[step] now attempting post-call SELECT inside the SAME begin_nested...
[RESULT] Exception raised (escaped the outer begin_nested/async-with entirely):
  sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside
  context manager. Please complete the context manager before emitting further commands.
[step] outer db.commit() succeeded without error
[step] session still usable, AgentUsageLog rows for agent=1
[VERIFY, fresh session] AgentUsageLog rows = 1, AgentQuota rows = 0
```

**هذا يطابق حرفيًا الاكتشاف الموثَّق سابقًا في §6 من الجلسة الأصلية:** الاستثناء
**لا** يحدث عند نداء `check_and_consume()` نفسه (وبالتالي try/except الموجودة
فعليًا في `_check_ai_governance` **لن تمسكه أبدًا** — هي بتغلّف نداء
`check_and_consume` بس، مش أي كود بعده)، بل عند **أول عملية DB تالية** داخل نفس
`begin_nested()` الخارجي (هنا: `_get_land_owner_for_unit` الحقيقية في الكود،
سطر 306). هذا الاستثناء **غير معالَج إطلاقًا** (`begin_nested()` بره try/except
في `buy_fractional_ownership`) → **الدالة كلها تنهار بـ500**، بالضبط زي
`execute_agent_action`، لكن بآلية تأخير مختلفة (تأجيل خطوة واحدة).

**تأكيد إضافي:** صف `AgentUsageLog` اتكتب فعليًا وبشكل دائم (تحقق بجلسة DB مستقلة
تمامًا) رغم انهيار العملية بالكامل — **نفس نمط "صف يتيم" الموثَّق لـ`ai_task_logs`
في الجلسة الأصلية**: استهلاك حصة/تسجيل استخدام AI محفوظ دائمًا، رغم إن الشراء نفسه
(الملكية، تحويل الأموال) لم يحدث. الجلسة تعافت تلقائيًا بعد كده (نفس سلوك
`execute_agent_action`). بيانات الـthrowaway اتنضّفت بالكامل (تأكيد
`[cleanup] throwaway agent/usage_log/quota removed`).

**ملاحظة جانبية مكتشَفة أثناء القراءة (خارج نطاق begin_nested، توثيق فقط):**
`_check_ai_governance` (`realestate/service.py:69-81`) بترجع `result` (`bool`)
من `check_and_consume`، لكن الكولر (`buy_fractional_ownership:303`) بينادي
`await self._check_ai_governance(...)` **كـstatement مجرد، بلا استخدام القيمة
المُرجَعة إطلاقًا** — يعني حتى لو الحصة اتجاوزت فعليًا (`check_and_consume`
ترجع `False`)، الشراء **لا يُمنَع حاليًا** أبدًا؛ الحوكمة غير مُفعَّلة فعليًا
كبوابة. بند منفصل تمامًا يستاهل توثيق (مش جزء من هذا الإصلاح): **هذا يعني نقل
النداء لبعد الـcommit (كما هو مقترح تحت) لا يغيّر أي سلوك وظيفي فعلي — القيمة
المُرجَعة كانت وهتفضل غير مستخدَمة على أي حال.**

---

## 4) التصميم المقترح (للموافقة — صفر تنفيذ حتى الآن)

**القرار المعماري: لا تُلمَس `check_and_consume()` نفسها إطلاقًا** — نفس منطق
القرار الأصلي في §16 بالحرف. `commit()` الداخلي (سطر 203) **ضروري وصحيح** لـ14
من أصل 15 موضع استدعاء (مستقلة تمامًا، `get_db()` لا يعمل commit تلقائي —
مؤكَّد سابقًا). لو حوّلناها لـ`flush()`، الـ14 موضع المستقل هيتعطّل فورًا (صفر
تحفّظ فعلي في الـDB).

**الإصلاح الصحيح: نفس نمط `#11b`/realestate بالحرف — نقل النداء (عبر
`_check_ai_governance`) بره حدود `begin_nested()`، مش تعديل الدالة المشتركة.**

الموضع الوحيد المتأثر هو `realestate.buy_fractional_ownership` — ونتيجته
(كما تأكَّد أعلاه) **غير مستخدَمة أصلًا حاليًا في الكولر**، فالحل هو **نفس نمط
النقل البسيط** المُطبَّق بالفعل على `ai.execute_agent_action` قبل يوم واحد في
نفس الدالة (سطر 360-363) — بلا حاجة لأي "رفع" (hoist) معقّد زي invitations.

**قبل → بعد (تصوري، غير مُنفَّذ):**
```python
# جوّه begin_nested() (سطر 288-353): يُحذف السطر التالي من هنا
#     await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)
# ... باقي البلوك بلا تغيير (owner, finance.transfer, create_ownership, ...) ...

await self.db.commit()                                    # سطر 353 (بدون تغيير)

# ========================================
# فحص/استهلاك حوكمة الذكاء الاصطناعي (بعد commit() الرئيسي عمدًا —
# check_and_consume() تنفّذ commit() مستقل داخلها؛ نداؤها من جوّه begin_nested()
# أعلاه كان يكسر الـSAVEPOINT. راجع
# .claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md)
# ========================================
await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)
# _check_ai_governance عندها try/except داخلية بالفعل (سطر 70-81) — كافية،
# صفر حاجة لـtry/except إضافية هنا (بعكس execute_agent_action اللي مالهاش
# try/except داخلية، فاحتاجت try/except في مكان النداء الجديد)

try:
    await ai.execute_agent_action(...)                     # بدون تغيير، مكانها كما هو
except Exception as e:
    logger.error(...)

try:
    await invoicing.create_invoice(...)                    # بدون تغيير
except Exception as e:
    logger.error(...)
```

**ملاحظة على الترتيب:** لا فرق وظيفي بين وضع `_check_ai_governance` قبل أو بعد
`ai.execute_agent_action` في القسم الجديد (كلاهما بعد الـcommit، كلاهما نتيجته
غير مستخدَمة) — الاقتراح يضعها أولًا بس عشان تحافظ على نفس الترتيب المنطقي
الأصلي (فحص الحوكمة كان قبل باقي العملية).

### القرار المطلوب اعتماده صراحة قبل أي تنفيذ:
1. ✅/❌ عدم لمس `check_and_consume()` نفسها (السبب: 14 كولر مستقل يعتمدون على
   الـcommit الداخلي، بنفس منطق §16).
2. ✅/❌ تصميم realestate: نقل نداء `self._check_ai_governance(...)` من داخل
   `begin_nested()` (سطر 303) لبعد `self.db.commit()` (بجوار/قبل نداء
   `ai.execute_agent_action` الموجود بالفعل هناك من إصلاح #16)، بلا `try/except`
   إضافية (الدالة عندها واحدة داخلية بالفعل)، صفر تغيير على القيم الممرَّرة.
3. تحديث اختبار جديد يثبت السيناريو (مشابه لـ`test_ai_agents_execute_action.py`) —
   هل يُضاف لملف `test_ai_governance_check_and_consume.py` الموجود، أم ملف جديد
   مخصَّص لسيناريو begin_nested (زي `test_ai_agents_execute_action.py`)؟
4. تحديث `PROGRESS_LOG.md` بملاحظة قصيرة (اكتشاف تابع لدرس §16 العام، مش درس
   جديد) — مطلوب أم لا؟
5. **اكتشاف جانبي موثَّق فقط (§3 أعلاه)، خارج نطاق هذا الإصلاح:** `_check_ai_governance`
   لا تُفعِّل حوكمة الحصة فعليًا (نتيجة `check_and_consume` غير مستخدَمة) —
   يستاهل بند Backlog منفصل (`realestate-ai-governance-quota-not-enforced`)؟

**صفر تعديل على أي كود إنتاج تم في هذه الجلسة. بيانات throwaway السكربت (§3)
اتنضّفت بالكامل ومُتحقَّق منها بجلسة DB مستقلة.**

---

## 5) ✅ موافقة المستخدم [2026-09-01] — التنفيذ الفعلي

المستخدم وافق على التصميم بالكامل + طلب: (1) التنفيذ، (2) ملف اختبار جديد
مخصَّص، (3) تحقق حي بعد التنفيذ عبر `buy_fractional_ownership` الحقيقية،
(4) ملاحظة `PROGRESS_LOG.md` تربط بدرس #16 صراحة، (5) بند backlog منفصل
لاكتشاف "الحوكمة غير مُفعَّلة فعليًا كبوابة" (§3 أعلاه). `git diff --stat`
قبل commit واحد شامل.

### 5.1 ✅ `realestate/service.py` — التطبيق

`buy_fractional_ownership`: نداء `self._check_ai_governance(tenant_id,
buyer_id, "FRACTIONAL_PURCHASE", cost)` نُقل من داخل `begin_nested()` (كان
سطر 303، بعد حساب `cost` مباشرة) لبعد `await self.db.commit()`، بجوار نداء
`ai.execute_agent_action(...)` الموجود بالفعل هناك من إصلاح #16 أمس —
**بلا** `try/except` إضافية حول النداء الجديد (الدالة `_check_ai_governance`
عندها `try/except` داخلية أصلًا، سطر 70-81). صفر تغيير على القيم الممرَّرة.
`py_compile`: ✅ نظيف.

### 5.2 ✅ ملف اختبار جديد — `tests/test_ai_governance_begin_nested.py`

اختباران، كلاهما **بلا** أي `monkeypatch` على `_check_ai_governance`/
`check_and_consume` (خلافًا للاختبار الموجود في `test_ai_agents_execute_action.py`
اللي بيعزلها عمدًا بسبب هذا العطل بالتحديد):

1. `test_buy_fractional_ownership_full_flow_succeeds_with_real_ai_governance` —
   استدعاء حي حقيقي لـ`buy_fractional_ownership()` نفسها (بيانات throwaway،
   وكيل `id=2` حقيقي)، يثبت: الشراء نجح، الملكية محفوظة، تحويل الأموال تم
   (كلاهما جوّه `begin_nested()`، بعد الموضع القديم للفحص مباشرة — الدليل
   المباشر إن البلوك كمّل بسلام)، `AgentUsageLog` حقيقي اتسجل (دليل
   `check_and_consume()` اتنفذت بنجاح بعد الـcommit)، `AITaskLog` حقيقي
   اتسجل (`execute_agent_action` اتنفذت بنجاح بجوارها بلا تعارض).
2. `test_check_and_consume_independent_call_then_followup_select_succeeds` —
   نداء مستقل مباشر (بلا `begin_nested()` خارجي)، بالظبط زي نمط الـ14 دومين
   الآخرين، + عملية DB تالية في نفس الجلسة — يثبت الشكل الصحيح الوحيد
   المدعوم.

**نتيجة التشغيل الفعلي (DB حقيقية):**
```
tests/test_ai_governance_begin_nested.py::test_buy_fractional_ownership_full_flow_succeeds_with_real_ai_governance PASSED
tests/test_ai_governance_begin_nested.py::test_check_and_consume_independent_call_then_followup_select_succeeds PASSED
2 passed, 5 warnings in 115.44s
```

### 5.3 ✅ التحقق الحي بعد الإصلاح — تأكيد اختفاء `InvalidRequestError`

الاختبار 5.2/1 أعلاه **هو نفسه** طلب التحقق المطلوب (إعادة سيناريو "تشغيلة 2"
— SELECT/كتابة تالية داخل نفس البلوك — لكن عبر `buy_fractional_ownership()`
الحقيقية بعد الإصلاح، مش السكربت الصناعي): نجح بالكامل، `InvalidRequestError`
لم يظهر إطلاقًا، كل العمليات التالية جوّه `begin_nested()` (owner lookup,
`finance.transfer`, `create_ownership`, `event_bus.publish`, `audit_log`,
`_send_notification`) نجحت. **ملاحظة منهجية (نفس الدرس من جلسة #16 §5.4):**
إعادة تشغيل السكربت الصناعي الأصلي (`repro_ai_governance_begin_nested.py`)
بعد الإصلاح **هتفضل ترمي نفس `InvalidRequestError`** — متوقَّع وصحيح، مش
تراجع: السكربت بيحاكي نداء `check_and_consume()` **مباشرة** جوّه `begin_nested()`
صناعي (نفس الـanti-pattern المتعمَّد لإثبات آليته)، ولا ينادي
`buy_fractional_ownership()` الحقيقية. الإصلاح غيَّر **الكولر الحقيقي** فقط
(نقل موضع النداء) — لم يغيّر ولا يفترض أن يغيّر حقيقة إن `check_and_consume()`
لسه غير آمنة النداء من جوّه أي `begin_nested()` خارجي (قرار معماري متعمَّد،
راجع §4).

### 5.4 ✅ `PROGRESS_LOG.md`

قسمان جديدان مُضافان في الأسفل (بلا تعديل أي إدخال قديم): (1) إغلاق صريح
لبند `ai-governance-check-and-consume-commit-inside-begin-nested` المفتوح
من أمس، **مصنَّف بوضوح كتابع مباشر لدرس #16** (مش اكتشاف جديد مستقل)، (2)
بند Backlog جديد `realestate-ai-governance-quota-not-enforced`.

### 5.5 ✅ بند Backlog جديد — `realestate-ai-governance-quota-not-enforced`

موثَّق بالتفصيل في `PROGRESS_LOG.md` (القسم الجديد) — ملخّص: نتيجة
`check_and_consume()` (`bool`) غير مستخدَمة إطلاقًا في `buy_fractional_ownership`،
يعني تجاوز حصة الـAI **لا يمنع الشراء فعليًا**. إصلاح begin_nested (هذه
الجلسة) **لا يغيّر هذا السلوك** — القيمة كانت وهتفضل غير مستخدَمة قبل النقل
وبعده. يحتاج قرار منتج منفصل (فرض/توثيق كاستشاري)، خارج نطاق هذه الجلسة.

**الحالة النهائية: مُغلَق بالكامل.** `realestate/service.py`،
`tests/test_ai_governance_begin_nested.py`، `PROGRESS_LOG.md` مُعدَّلة
ومُتحقَّق منها حيًا. `git diff --stat` + commit واحد شامل تاليان.
