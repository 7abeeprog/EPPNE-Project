# `test_ai_governance_check_and_consume.py`

## المرجع الأصلي
- `.claude/reports/ai-governance-agents-fix-session-log.md` (المرحلة 1.3، الجزء أ، Backlog #15).

## السبب الجذري (كان) — ملخص
`AIGovernanceService.check_and_consume(self, agent_id, user_id, action_type, tokens, cost, idempotency_key=None, ...)` — **صفر معامل `tenant_id` في التوقيع أصلًا** (الـmethod تستخدم `self.tenant_id` من الـconstructor في كل منطق فعلي). **13 موضع استدعاء عبر 13 دومين** كانوا بيمرروا `tenant_id=` زيادة → `TypeError` فوري. **7 من الـ13 كان عندهم بج ثانٍ متزامن**: `action_type` الإجباري مفقود بالكامل.

## الإصلاح المُطبَّق
- إزالة `tenant_id=` الزائدة من كل الـ13 موضع (**عكس اتجاه** إصلاح `audit_log`/#14 عمدًا — هنا الـmethod تملك السياق بالفعل عبر الـconstructor).
- إضافة `action_type=` بقيم معبِّرة عن السياق الفعلي للسبعة الناقصة (`SCENARIO_ANALYSIS`, `PLAYER_TRANSFER_ANALYSIS`, `BID_EVALUATION`, `MATCH_SUGGESTIONS`, `AI_JUDGE_ANALYSIS`، واتنين بحل أدق: `action_type=action` — تمرير معامل موجود أصلًا في helper محيط بدل نص ثابت).
- صفر لمس على جسم `check_and_consume` نفسها أو `AIGovernanceRepository`.

## إيه اللي بيتحقق منه هذا الملف
اختبارات على **منطق `check_and_consume` نفسها مباشرة** (نفس منهجية التحقق الحي الأصلي — استدعاء الدالة الحقيقية المُصلَحة، بيانات throwaway حقيقية، `SELECT` مستقل):

| # | الاختبار | يثبت |
|---|---|---|
| 1 | `test_check_and_consume_normal_success_records_usage` | نجاح عادي — استهلاك ضمن الحد، `usage_log` يُسجَّل بدقة |
| 2 | `test_check_and_consume_accumulates_usage_across_calls` | تراكم صحيح — استدعاءان متتاليان (500+500=1000، حد الحصة بالضبط)، مطابق لسيناريو 2 من التقرير الأصلي |
| 3 | `test_check_and_consume_rejects_when_quota_exceeded` | **الحالة الحرجة** — رفض فعلي عند تجاوز الحصة، صفر استهلاك جزئي، صفر `usage_log` للمحاولة المرفوضة |
| 4 | `test_check_and_consume_with_idempotency_key_hits_wrong_arity_bug` | `xfail(strict=True)` — اكتشاف جديد (تفصيل تحت) |

## 🔴 اكتشاف جديد [2026-08-19] — `ai-governance-usage-log-idempotency-wrong-arity`
أثناء كتابة الاختبار الرابع، تبيَّن إن `check_and_consume()` (`ai_governance/service.py:152`) بتنادي `self.repo.get_usage_log_by_idempotency(idempotency_key)` بمعامل واحد بس، لكن `AIGovernanceRepository.get_usage_log_by_idempotency()` (`repository.py:66`) توقيعها الحقيقي `(idempotency_key: str, tenant_id: int)` — `tenant_id` إجباري بلا `default`. **أي استدعاء `check_and_consume()` بـ`idempotency_key` حقيقي يكراش فورًا بـ`TypeError`.**

**هذا باج داخل جسم `check_and_consume` نفسها (نداء داخلي لدالة تانية) — منفصل تمامًا عن بج `tenant_id`/`action_type` الموثَّق في #15 (الأخير في توقيعها الخارجي).** الموضع الوحيد من الـ13 المُصلَحة اللي بيمرر `idempotency_key` فعليًا هو `service_marketplace/service.py:159` — مسار الشراء هناك معطَّل بالكامل حاليًا كلما تحاول تستخدم idempotency فعليًا.

**مُوثَّق كبند Backlog منفصل جديد (`ai-governance-usage-log-idempotency-wrong-arity`) في `PROGRESS_LOG.md`. صفر لمس على `ai_governance/service.py`/`repository.py`.**

## بيانات throwaway
- `tenant_id=1`. وكيل AI (`AIAgent`) وحصة (`AgentQuota`) throwaway جديدين لكل اختبار (`uuid4` suffix) — صفر تعارض مع وكلاء حقيقيين.
- تنظيف كامل في `finally` بعد كل اختبار؛ تأكَّد بـ`SELECT` مباشر بعد التشغيل (مرتين متتاليتين): صفر صفوف throwaway متبقية.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_ai_governance_check_and_consume.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435) و Redis (`docker` container `redis`, بورت 6380).

**آخر تشغيل مُوثَّق [2026-08-19]:** 3 passed, 1 xfailed (تشغيلتان متتاليتان، صفر تذبذب).
