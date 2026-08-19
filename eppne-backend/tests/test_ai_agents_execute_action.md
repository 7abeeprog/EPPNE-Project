# `test_ai_agents_execute_action.py`

## المرجع الأصلي
- `.claude/reports/ai-agents-execute-action-fix-session-log.md` (المرحلة 1.3، الجزء ب، Backlog #16).

## السبب الجذري (كان) — ملخص
`AIAgentsService.execute_agent_action(self, agent_id, action_type, payload, executor_user_id, idempotency_key)` — **صفر معامل `tenant_id` في التوقيع أصلًا** (نفس قوة #15: `self.tenant_id` من الـconstructor تُستخدم في كل منطق فعلي). **19 موضع استدعاء** كانوا بيمرروا `tenant_id=` زيادة → `TypeError` فوري، **13 منهم كمان كانوا بيفتقدوا `idempotency_key=`** الإجباري (بلا `default`).

## الإصلاح المُطبَّق — **17 من 19 موضع فقط، إغلاق جزئي بنطاق مُعدَّل عمدًا**
- إزالة `tenant_id=` من كل الـ17 + إضافة `idempotency_key=` بقيم مبنية بنمط `PREFIX-T{tenant_id}-{unique_id}` للـ11 الناقصة.
- 🔴 **موضعان مُستثنيان عمدًا، بقرار صريح موثَّق:** `realestate/service.py:232`، `invitations/service.py:415`.

### لماذا الاستثناء؟ (Backlog `ai-agents-execute-action-commit-inside-begin-nested`)
`execute_agent_action()` نفسها بتنفّذ `await self.db.commit()` داخل جسمها. الموضعان دول بينادوها من **جوّه `async with self.db.begin_nested()`** خارجي، بلا `try/except`. تصحيح الـkwargs بمعزل عن حل بنية المعاملة كان سيجعلهما يصلان لأول مرة فعليًا لـ`commit()` حقيقي وهما لسه جوّه savepoint — **احتمال تلف transaction حقيقي**، نفس فئة #11a/#11b (`realestate:232` داخل عملية شراء ملكية بأموال حقيقية). **لازم يُصلَحا سوا (بنية المعاملة أولًا) في جلسة مستقبلية منفصلة.**

## إيه اللي بيتحقق منه هذا الملف

### أ) منطق `execute_agent_action` نفسها مباشرة (4 اختبارات)
نفس منهجية التحقق الحي الأصلي (§10) — استدعاء الدالة الحقيقية المُصلَحة مباشرة بأشكال `idempotency_key` تمثيلية من دومينات مختلفة فعليًا مُصلَحة، مش استدعاء الدومينات الكاملة:

| # | الاختبار | يثبت |
|---|---|---|
| 1 | `test_execute_agent_action_normal_success_creates_task_log_and_approval` | نجاح عادي، شكل `AI-BATCH-T{tenant}-{id}` (نمط `manufacturing`) |
| 2 | `test_execute_agent_action_retry_same_idempotency_key_is_cached` | كاش idempotency حقيقي — صفر تكرار |
| 3 | `test_execute_agent_action_cross_tenant_same_local_id_no_collision` | تينانتان مختلفان (1، 15) بنفس المعرّف المحلي — صفر تصادم بفضل `T{tenant_id}` |
| 4 | `test_execute_agent_action_raw_idempotency_key_without_tenant_prefix_collides_across_tenants` | تأكيد حي إضافي لخطر مسبق موثَّق (`ai-agents-execute-action-approval-queue-global-unique-collision`) — مفتاح خام بلا تمييز tenant يسبب `IntegrityError` فعلي عبر تينانتين |

### ب) الموضعان المُستثنيان — `xfail(strict=True)` موثَّقان (ممنوع تجاهلهم)
| # | الاختبار | يثبت |
|---|---|---|
| 5 | `test_realestate_buy_fractional_ownership_execute_agent_action_still_excluded` | `realestate/service.py:232` لسه بيرمي `TypeError` معروف، مُستبعَد عمدًا |
| 6 | `test_invitations_chat_with_ai_execute_agent_action_still_excluded` | نفس الشيء لـ`invitations/service.py:415` |

كل واحد بيستدعي الدالة الحقيقية المحيطة (`buy_fractional_ownership`/`chat_with_ai`) حيًا، مش mock — لو حد يصلح بنية المعاملة لاحقًا، الاختبار هيبقى `XPASS` ويفشل تلقائيًا (`strict=True`) كتذكير واضح إن الباج اتصلح ولازم نرفّع مستوى التغطية.

### تجاوز متعمَّد لبج غير مرتبط (Backlog #7، `redis-client-wrapper-missing-methods`)
`ai_engine.generate()` الحقيقية بتنادي `CostTracker.record_usage()` اللي بتستخدم `redis_client.hincrbyfloat()` **غير الموجودة** → `AttributeError` يُسقِط `execute_agent_action` بالكامل. **نفس منهجية التقرير الأصلي §10 بالحرف:** `ai_engine.generate` مُستبدَلة بـ`monkeypatch` بنسخة وهمية **في هذا الملف فقط، صفر تعديل على كود الإنتاج**.

## بيانات throwaway
- `tenant_id=1` و`tenant_id=15` (تينانتان حقيقيان موجودان فعلًا، نفس المستخدَمين في التحقق الحي الأصلي).
- وكلاء AI throwaway جدد لكل اختبار (`uuid4` suffix).
- تنظيف كامل في `finally`؛ اختبار التصادم عبر التينانتين يستخدم **جلسة DB مستقلة تمامًا** (`AsyncSessionLocal` جديدة) للمحاولة المتوقَّع فشلها — لأن `IntegrityError` بتسمّم أي جلسة تحصل فيها (نفس احتياط `test_saas_active_subscription.py`).
- تأكَّد بـ`SELECT` مباشر بعد التشغيل (مرتين متتاليتين): صفر صفوف throwaway متبقية.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_ai_agents_execute_action.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435) و Redis (`docker` container `redis`, بورت 6380).

**آخر تشغيل مُوثَّق [2026-08-19]:** 4 passed, 2 xfailed (تشغيلتان متتاليتان، صفر تذبذب).
