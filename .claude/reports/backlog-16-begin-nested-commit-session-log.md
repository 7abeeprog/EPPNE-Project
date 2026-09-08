# جلسة: backlog-16-begin-nested-commit-conflict

**تاريخ:** 2026-09-01
**البند:** `ai-agents-execute-action-commit-inside-begin-nested` (بند Backlog موثَّق سابقًا في
`.claude/reports/ai-agents-execute-action-fix-session-log.md` §7/§11، اكتُشف أثناء إصلاح
Backlog #16 الأصلي في 2026-08-18).

**الموضعان المؤكَّدان مسبقًا:**
- `realestate/service.py:232` (داخل `buy_fractional_ownership`, `begin_nested()` يبدأ سطر 214)
- `invitations/service.py:415` (داخل `chat_with_ai`, `begin_nested()` يبدأ سطر 394)

**الحالة الحالية الموروثة:** الموضعان ما زالا يفشلان بـ`TypeError` قبل الوصول لجسم
`execute_agent_action` (بسبب `tenant_id=`/`idempotency_key` غير مصحَّحة عمدًا) — الكود لم
يصل فعليًا لحالة "commit جوّه savepoint" بعد. **صفر تنفيذ حتى الآن في هذه الجلسة** — تحقيق فقط.

**القاعدة المتبعة:** صفر تنفيذ حتى الموافقة الصريحة. هذا بند حساس يمس حدود transaction عبر دومينين.

---

## 1) الكود الفعلي لـ `AIAgentsService.execute_agent_action` (`ai_agents/service.py:147-264`)

```python
async def execute_agent_action(self, agent_id, action_type, payload, executor_user_id, idempotency_key) -> Dict[str, Any]:
    cached = await self._validate_idempotency(idempotency_key)
    if cached: return cached
    agent = await self.repo.get_agent(agent_id, self.tenant_id)
    if not agent: raise NotFoundError(...)
    ...
    try:
        task_log = await self.repo.create_task_log(...)          # سطر 180
        result = await ai_engine.generate(...)                    # سطر 193
        ...
    except Exception as e:
        await self.repo.create_task_log(..., task_type="ERROR")   # سطر 211
        await self.db.commit()                                    # 🔴 سطر 223 (مسار الفشل)
        raise
    await self.db.commit()                                        # 🔴 سطر 226 (مسار النجاح)

    if agent.requires_human_approval:
        approval = await self.repo.create_approval_request(...)   # سطر 229
        response = {"status": "PENDING_APPROVAL", ...}
    else:
        response = {"status": "COMPLETED", ...}
    await self._store_idempotency(idempotency_key, response)
    await audit_log(...)
    return response
```

**الغرض من الـ`commit()` الداخلي:** ليس مجرد "تسجيل audit"، بل **الدالة بحد ذاتها هي وحدة معاملة كاملة ومستقلة** (تفتح، تكتب، تلتزم). هذا مؤكَّد بقراءة `app/core/database.py:45-51`:
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try: yield session
        finally: await session.close()
```
**`get_db()` لا يعمل `commit()` تلقائيًا عند نهاية الطلب.** يعني أي service بيتنادى مباشرة من endpoint (زي `ai_agents/router.py:94`) لازم يعمل `commit()` بنفسه، وإلا لا يتحفظ أي شيء في الـDB إطلاقًا. **19 موضع استدعاء لـ`execute_agent_action` عبر المشروع، 17 منهم مستقلين تمامًا (مش جوّه `begin_nested()` لحد تاني)** — لهذول الـ17، الـ`commit()` الداخلي **ضروري وصحيح**، مش اختياري.

---

## 2) الموضعان — الكود الفعلي الكامل (بعد تحديث السطور، مختلفة عن التقرير الأصلي 2026-08-18)

### أ) `realestate/service.py` — `buy_fractional_ownership` (سطر 250-386)

```python
ai = AIAgentsService(self.db, tenant_id)
finance = FinanceService(self.db, tenant_id)
invoicing = InvoicingService(self.db, tenant_id)
async with self.db.begin_nested():                     # سطر 288
    unit = await self.repo.get_unit(unit_id)            # SELECT فقط
    ... تحقق من التوفر/السعر/النسبة المتبقية (SELECT فقط) ...
    await ai.execute_agent_action(                       # 🔴 سطر 306 — النتيجة غير مُستخدَمة إطلاقًا (statement مجرد)
        agent_id=2, action_type="ANALYZE_PROJECT", payload={...},
        executor_user_id=buyer_id,
        idempotency_key=f"REALESTATE-FRAC-T{tenant_id}-{idempotency_key or uuid.uuid4().hex[:8]}",
    )
    await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)  # سطر 308
    owner = ...
    tx_hash = await finance.transfer(...)                # سطر 315 — كتابة فعلية (أموال)
    await self._register_affiliate_commission(...)       # سطر 319
    ownership = await self.repo.create_ownership(...)     # سطر 322 — كتابة فعلية
    ... update_unit_availability, event_bus.publish, audit_log, _send_notification ...
await self.db.commit()                                    # سطر 358
try:
    await invoicing.create_invoice(...)                   # سطر 361 — بعد الـcommit، محمي بـtry/except (نمط #11b)
except Exception as e:
    logger.error(...)
```

**🔴 اكتشاف حرج: هذا الموضع تغيَّر منذ تقرير `ai-agents-execute-action-fix-session-log.md` (2026-08-18).** التقرير الأصلي وثّق قرارًا صريحًا بعدم لمس هذا الموضع (تركه يفشل بـ`TypeError` معروف وآمن). **لكن `git log -p -L 306,306` يثبت أن commit `b4bf356` (2026-08-29، جلسة `constructor-mismatch-backlog-cleanup`، بند #40 في رسالة الـcommit) صحّح الـkwargs هنا فعليًا** (حذف `tenant_id=` الزائدة، إضافة `idempotency_key=`) **بدون أي إشارة إلى بند Backlog `ai-agents-execute-action-commit-inside-begin-nested` الموثَّق مسبقًا في نفس المشروع** — أي أن القرار الصريح "ممنوع لمس هذا الموضع بمعزل عن حل بنية المعاملة" **انتُهك فعليًا في جلسة لاحقة**، على الأرجح لأن جلسة `#40` عالجت هذا كـ"نفس نمط باقي الـ17 موضع" بدون مراجعة التحذير الخاص بهذين الموضعين تحديدًا. **النتيجة: الكود الحالي في `main` يصل الآن فعليًا إلى `execute_agent_action`'s body — بما فيها الـ`commit()` الداخلي — وهو لسه جوّه `begin_nested()`، تمامًا كما حذّر التقرير الأصلي.**

### ب) `invitations/service.py` — `chat_with_ai` (سطر 357-452)

```python
ai_service = AIAgentsService(self.db, tenant_id)
async with self.db.begin_nested():                       # سطر 390
    await self.repo.create_conversation(                  # سطر 391 — كتابة فعلية (رسالة المستخدم)
        tenant_id=tenant_id, invitation_id=invitation_id, ..., is_from_ai=False, ...
    )
    ai_agent_id = invitation.assigned_ai_agent_id or 1
    prompt = f"..."
    ai_response = await ai_service.execute_agent_action(   # 🔴 سطر 410 — لسه فيها tenant_id= (لم تُصلَح كـkwarg بعد)
        agent_id=ai_agent_id, tenant_id=tenant_id, action_type="CHAT",
        payload={"prompt": prompt}, executor_user_id=user_id or 0,
    )
    reply_text = ai_response.get("result", {}).get("reply", "...")
    ai_message = await self.repo.create_conversation(       # سطر 420 — كتابة فعلية (رد الـAI)
        tenant_id=tenant_id, ..., is_from_ai=True, ...
    )
    if user_id:
        lead = await self.repo.get_lead_by_user(user_id, tenant_id)
        if lead:
            await self.repo.create_interaction(...)          # سطر 434
await self.db.commit()                                       # سطر 445
```

**هذا الموضع لسه بحالته الأصلية بالحرف** — `tenant_id=tenant_id` لسه موجودة كـkwarg زائد (لم تُصلَح، بعكس realestate)، فلسه بترمي `TypeError` فورًا **قبل** ما توصل لجسم `execute_agent_action` أصلًا. مؤكَّد أيضًا بوجود اختبار `xfail(strict=True)` قائم (`tests/test_ai_agents_execute_action.py:399`) يوثّق نفس الحالة.

---

## 3) التحقق الحي — إعادة إنتاج فعلية للمشكلة (سكربت throwaway، DB حقيقية `eppne_db`)

### 3.1 تشغيل الاختبار `xfail` الموجود لـrealestate

```
tests/test_ai_agents_execute_action.py::test_realestate_buy_fractional_ownership_execute_agent_action_still_excluded  XFAIL
```
لسه بترجع XFAIL (مش XPASS) — لكن **بسبب مختلف تمامًا عن السبب الموثَّق في نص الـxfail نفسه.** بتشغيلها بـ`--runxfail` (لرؤية السبب الحقيقي):
```
app.core.errors.NotFoundError: الوكيل 2 غير موجود
```
**السبب: `agent_id=2` مُثبَّت (`hardcoded`) في كود `realestate/service.py:306`، ولا يوجد وكيل بمعرّف 2 في قاعدة البيانات الحالية إطلاقًا** (تأكيد مباشر: `SELECT * FROM ai_agents WHERE id=2` = 0 صف). هذا يعني: **نص الـxfail الحالي أصبح غير دقيق** — يدّعي أن السبب لسه `TypeError`، بينما فعليًا صار `NotFoundError` (لأن الـkwargs اتصلحت في `b4bf356`، لكن الاختبار لم يُحدَّث). الاختبار "ينجح" حاليًا بالصدفة (لأي استثناء)، **لا يثبت فعليًا غياب مشكلة begin_nested/commit** — لأن التنفيذ لا يصل لجسم `execute_agent_action` بسبب عائق منفصل تمامًا (وكيل غير موجود)، قبل ما نصل للـcommit() المتنازع عليه أصلًا.

### 3.2 سكربت تحقيق مستقل — تجاوز عائق `agent_id=2` بوكيل throwaway حقيقي

لعزل سلوك **آلية begin_nested/commit نفسها** (بمعزل عن باج `agent_id=2` الثابت، خارج نطاق هذه الجلسة)، أُنشئ سكربت مستقل (`scratchpad/repro_begin_nested_commit.py`، صفر لمس على كود الإنتاج) يحاكي بنية الكولر بالحرف: وكيل AI throwaway حقيقي (tenant=1)، `async with db.begin_nested():`، كتابة حقيقية داخل البلوك *قبل* نداء `execute_agent_action` (لمحاكاة `create_conversation` في invitations)، ثم نداء `execute_agent_action` الحقيقي (مع `ai_engine.generate` مُستبدَلة بموك محلي لتفادي بج #7 غير المرتبط، نفس منهجية كل الجلسات السابقة).

**النتيجة الحية (مُشغَّلة فعليًا على `eppne_db`، تينانت 1):**

```
[step] pre-write done inside begin_nested() (agent renamed)، now calling execute_agent_action()...
[RESULT] Exception raised: sqlalchemy.exc.InvalidRequestError:
  Can't operate on closed transaction inside context manager.
  Please complete the context manager before emitting further commands.

[step] outer db.commit() succeeded without error
[step] session still usable, rows=1        <- ai_task_logs الخاص بالمحاولة موجود فعلاً!

[VERIFY, fresh session] agent.name in DB now = 'REPRO-BN-AGENT-RENAMED-...'
  (القيمة اللي اتكتبت *قبل* نداء execute_agent_action، جوّه نفس begin_nested() اللي انهار بعده)
```

**تفسير الآلية الفعلية المؤكَّدة (مش نظرية):**

1. `execute_agent_action()`'s الخاص بها `await self.db.commit()` (سطر 226، مسار النجاح) — لما يتنفذ وهو لسه جوّه `begin_nested()` خارجي — **يرمي فورًا** `InvalidRequestError` (نفس الاستثناء الموثَّق مسبقًا في `transaction-savepoint-bug-session-log.md` §"[2026-08-13] عائق تشغيلي غير متوقع" لنفس النمط العام). الاستثناء غير مُعالَج (`execute_agent_action`'s الخاص `except Exception` لا يغطي هذا السطر — هو *بعد* الـtry/except، مسار النجاح فقط).
2. **لكن الـ`commit()` نفسه ينفّذ فعليًا commit حقيقي على مستوى الـDB قبل ما يرمي الاستثناء** — مؤكَّد بقراءة مستقلة (جلسة DB جديدة تمامًا، بعد نهاية كل شيء): الصف اللي اتكتب *قبل* نداء `execute_agent_action` (تعديل اسم الوكيل، بمحاكاة `create_conversation` في invitations) **موجود فعليًا وبشكل دائم في الـDB** — رغم إن الاستثناء انهار البلوك بالكامل ومنع أي كتابة بعده.
3. الاستثناء ينتشر عبر `async with self.db.begin_nested():` بالكامل (بلا `try/except` في الكولر) → **العملية المحيطة (`buy_fractional_ownership`/`chat_with_ai`) تنهار بالكامل بـ500 غير معالَج** — لا شراء، لا رد AI، لا فاتورة.
4. الجلسة (`db` نفسها) **تتعافى تلقائيًا بعد كده** — `commit()`/`SELECT` تاليين نجحوا بلا مشاكل، صفر تلوث دائم على مستوى الـconnection.

**الأثر العملي المختلف بين الموضعين، مؤكَّد حيًا:**
- **`invitations.chat_with_ai`**: فيه كتابة حقيقية (`create_conversation` لرسالة المستخدم) **قبل** نداء `execute_agent_action` **داخل نفس البلوك** — بالضبط زي السيناريو المحاكى في السكربت. **يعني: رسالة المستخدم ستُحفَظ دائمًا في `invitation_conversations`، لكن رد الـAI/الـinteraction لن يُكتَبا أبدًا، والطلب بالكامل ينهار بـ500** — تناقض بيانات فعلي (رسالة يتيمة بلا رد)، بمجرد ما الـkwargs تتصلح هنا كمان (لسه ما اتصلحتش، فالباج الحالي هنا لسه `TypeError` آمن).
- **`realestate.buy_fractional_ownership`**: **لا توجد أي كتابة قبل نداء `execute_agent_action`** داخل البلوك (كله SELECT قبلها) — فلا يوجد خطر تناقض بيانات مالية حاليًا. لكن **الكود الحالي (بعد `b4bf356`) سيصل الآن فعليًا لهذا الانهيار في كل مرة يوجد فيها وكيل بمعرّف 2 فعليًا** (حاليًا "محمي" بالصدفة بس لأن `agent_id=2` غير موجود في الـDB) — أي أن شراء الملكية الجزئية **معطوب بالكامل حاليًا**، لكن بآلية فشل مختلفة تمامًا عن الموثَّق سابقًا (`InvalidRequestError` بدل `TypeError`)، وبأثر جانبي جديد: صف `ai_task_logs` يتيم (بلا موافقة/شراء مرتبط) يُكتَب فعليًا في كل محاولة فاشلة.

---

## 4) التصميم المقترح (للموافقة — صفر تنفيذ حتى الآن)

**القرار المعماري: لا تُلمَس `execute_agent_action()` نفسها إطلاقًا.**

**السبب المؤكَّد بالقراءة/التحقق:** `commit()` الداخلي **ضروري وصحيح** لـ17 من أصل 19 موضع استدعاء — كلها مستقلة تمامًا (مش جوّه `begin_nested()` لحد تاني)، بما فيها استدعاء مباشر من `ai_agents/router.py:94` بلا أي معاملة محيطة. بما إن `get_db()` **لا يعمل commit تلقائي** (مؤكَّد بالقراءة، `database.py:45-51`)، فلو أزلنا الـ`commit()` الداخلي (حوّلناه لـ`flush()` زي نمط `finance.transfer()`)، **الـ17 موضع الآمن كله هيتعطّل فورًا** (صفر تحفّظ فعلي في الـDB لأي استدعاء مستقل لـ`execute_agent_action`). هذا يخالف بالضبط الدرس المستفاد من `finance.transfer()` — الفرق الجوهري: `finance.transfer()` **دايمًا** بتتنادى من جوّه معاملة كولر أكبر (33 caller، كلهم بيعملوا commit خاص بيهم لاحقًا)، أما `execute_agent_action()` فبتتنادى **غالبًا كوحدة مستقلة بذاتها** (17 من 19).

**الإصلاح الصحيح: نفس نمط `#11b` (`create_invoice` جوّه `begin_nested`) بالحرف — نقل نداء `execute_agent_action` **بره** حدود `begin_nested()` في الكولرين، مش تعديل الدالة المشتركة:**

### أ) `realestate.buy_fractional_ownership`
نتيجة `execute_agent_action` **غير مُستخدَمة إطلاقًا حاليًا** (استدعاء مجرد، بلا `await result = `). الحل الأبسط والأقل خطورة: **نقل السطر 306 لبعد `await self.db.commit()` (سطر 358)، بنفس نمط/موقع نداء `invoicing.create_invoice()` الموجود أصلاً في نفس الدالة (سطر 360-369)** — أي بعد الـcommit، ملفوف بـ`try/except` (فشل الـAI لا يفشّل عملية الشراء اللي خلصت بالفعل).

**قبل → بعد (تصوري، غير مُنفَّذ):**
```python
# جوّه begin_nested() (سطر 288-357): يُحذف نداء execute_agent_action من هنا
...
await self.db.commit()                                    # سطر 358 (بدون تغيير)

try:
    await ai.execute_agent_action(
        agent_id=2, action_type="ANALYZE_PROJECT",
        payload={"unit_id": unit_id, "price": float(cost), "percentage": float(percentage), "buyer_id": buyer_id},
        executor_user_id=buyer_id,
        idempotency_key=f"REALESTATE-FRAC-T{tenant_id}-{idempotency_key or uuid.uuid4().hex[:8]}",
    )
except Exception as e:
    logger.error(f"AI analysis failed for fractional ownership purchase (unit {unit_id}): {e}")

try:
    await invoicing.create_invoice(...)                    # بدون تغيير
except Exception as e:
    logger.error(...)
```
**ملاحظة جانبية مكتشَفة أثناء الفحص (خارج نطاق هذا الإصلاح، توثيق فقط):** `agent_id=2` مُثبَّت (hardcoded) وغير موجود في الـDB الحالية — `buy_fractional_ownership` سيستمر بالفشل في مرحلة الـAI حتى لو الإصلاح ده اتطبق، **لكن بعد الإصلاح سيفشل بأمان (try/except) بدل ما يكسر الشراء نفسه** — الشراء سينجح رغم فشل خطوة الـAI. هذا تحسين حقيقي بغض النظر عن باج `agent_id=2` المنفصل.

### ب) `invitations.chat_with_ai`
نتيجة `execute_agent_action` (`ai_response`) **مُستخدَمة فعليًا** (`reply_text`) في بناء رد الـAI وقيمة الإرجاع — لا يمكن نقلها لمجرد "بعد الـcommit" زي realestate. الحل: **رفع (hoist) بناء الـprompt + نداء `execute_agent_action` لأعلى، قبل `async with self.db.begin_nested():` تمامًا، ثم كتابة رسالتي المحادثة (المستخدم + الـAI) والـinteraction سوا في بلوك واحد بعد الحصول على `ai_response`.**

**قبل → بعد (تصوري، غير مُنفَّذ):**
```python
ai_service = AIAgentsService(self.db, tenant_id)
ai_agent_id = invitation.assigned_ai_agent_id or 1
prompt = f"""... {user_message} ..."""

ai_response = await ai_service.execute_agent_action(         # ⬅ رُفعت لبره begin_nested()، tenant_id= هتتشال هنا كمان (جزء من نفس الإصلاح)
    agent_id=ai_agent_id, action_type="CHAT",
    payload={"prompt": prompt}, executor_user_id=user_id or 0,
    idempotency_key=f"AI-CRMCHAT-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-CRMCHAT-T{tenant_id}-{invitation_id}-{uuid.uuid4().hex[:8]}",
)
reply_text = ai_response.get("result", {}).get("reply", "شكراً لتواصلك. كيف يمكنني مساعدتك؟")

async with self.db.begin_nested():
    await self.repo.create_conversation(..., is_from_ai=False, ...)   # رسالة المستخدم
    ai_message = await self.repo.create_conversation(..., is_from_ai=True, ...)  # رد الـAI (نفس المكان، بعد ما بقى عندنا reply_text بالفعل)
    if user_id:
        lead = await self.repo.get_lead_by_user(user_id, tenant_id)
        if lead:
            await self.repo.create_interaction(...)
await self.db.commit()
```
**فائدة إضافية:** هذا الإصلاح كمان بيصلح الـkwarg (`tenant_id=` الزائدة، `idempotency_key` الناقصة) بنفس الخطوة — **بس فقط بعد** ما بنية المعاملة بقت صحيحة، بالضبط زي القرار الأصلي المُوصى به في `ai-agents-execute-action-fix-session-log.md` §7 ("لازم يُصلَحا سوا... تصحيح بنية المعاملة أولًا، ثم tenant_id=/idempotency_key= كخطوة تالية").

### القرار المطلوب اعتماده صراحة قبل أي تنفيذ:
1. ✅/❌ عدم لمس `execute_agent_action()` نفسها (السبب: 17 كولر مستقل يعتمدون على الـcommit الداخلي، `get_db()` لا يعمل commit تلقائي).
2. ✅/❌ تصميم realestate (نقل نداء `execute_agent_action` بعد `self.db.commit()`, try/except، بلا تغيير على القيمة المُمرَّرة).
3. ✅/❌ تصميم invitations (رفع نداء `execute_agent_action` قبل `begin_nested()`, تصحيح الـkwargs في نفس الخطوة، دمج كتابتي المحادثة في بلوك واحد بعد الحصول على `ai_response`).
4. تحديث اختبار `test_ai_agents_execute_action.py` (السطور 309-415 — الاختبارين `xfail`) بعد التنفيذ: يُتوقع أن يصبحا XPASS (وبالتالي يفشلا بسبب `strict=True`) ما لم يُعدَّلا ليصبحا اختباري نجاح حقيقي — هل تُدرَج هذه الخطوة كجزء من نفس الجلسة، أم جلسة تحقق منفصلة بعد التنفيذ؟

**صفر تعديل على أي كود إنتاج تم في هذه الجلسة حتى الآن.** بيانات throwaway السكربت (§3.2) اتنضّفت بالكامل (تأكيد: `[cleanup] throwaway agent/owner/task_logs/approvals removed`، والتحقق النهائي بجلسة DB مستقلة تمامًا لم يترك أي أثر إضافي).

---

## 5) ✅ موافقة المستخدم [2026-09-01] — التنفيذ الفعلي جارٍ

المستخدم وافق على التصميم بالكامل + طلب: (1) تنفيذ الإصلاحين، (2) تحديث اختباري `xfail` ليصبحا اختباري نجاح حقيقيين، (3) تحقق حي بعد كل تعديل (إعادة تشغيل سيناريو السكربت + تأكيد عدم وجود صفوف يتيمة)، (4) ملاحظة في `PROGRESS_LOG.md` عن انتهاك التحذير السابق كدرس عام، (5) `git diff --stat` قبل commit واحد شامل.

### 5.1 ✅ `realestate/service.py` — التطبيق

`buy_fractional_ownership`: نداء `ai.execute_agent_action(...)` نُقل من داخل `begin_nested()` (كان سطر 306) لبعد `await self.db.commit()` (بعد سطر 353 الحالي)، بنفس نمط/مكان `invoicing.create_invoice()` المجاور — `try/except` مع `logger.error()`، صفر تغيير على القيم الممرَّرة (`agent_id=2`, نفس بناء `idempotency_key`). `_check_ai_governance` بقيت في مكانها الأصلي (قبل الشراء، كبوابة quota). `git diff` نظيف: حذف سطرين (النداء + السطر الفارغ بعده من مكانهما القديم)، إضافة كتلة 7 أسطر (تعليق + try/except) في المكان الجديد.

### 5.2 ✅ `invitations/service.py` — التطبيق

`chat_with_ai`: بناء الـ`prompt` + نداء `execute_agent_action(...)` رُفعا لأعلى، قبل `async with self.db.begin_nested():` مباشرة. في نفس الخطوة: `tenant_id=tenant_id` الزائدة اتشالت، `idempotency_key=` أُضيفت بالقيمة المعتمدة سابقًا في `ai-agents-execute-action-fix-session-log.md` §3 (`AI-CRMCHAT-T{tenant_id}-{idempotency_key}` أو fallback بـ`uuid` لو مفيش `idempotency_key` خارجي). البلوك `begin_nested()` بقى يكتب رسالتي المحادثة (مستخدم + AI، باستخدام `reply_text` المتاح بالفعل) والـinteraction سوا، ذرّيًا، زي ما كان قبل كده بالظبط (نفس الشكل، بس بعد ما بقى عندنا `ai_response` من نداء مستقل تمامًا). فائدة جانبية مؤكَّدة: لو `execute_agent_action` فشلت الآن (أي سبب)، الفشل يحصل *قبل* أي كتابة على الإطلاق — صفر احتمال "رسالة مستخدم بلا رد" حتى في سيناريو الفشل، لأن begin_nested لسه ما اتفتحش أصلاً وقت الفشل.

`py_compile`/`ast.parse` لكلا الملفين: ✅ نظيف.

### 5.3 تحديث اختباري `xfail` → اختباري نجاح حقيقيين + اختبار فشل آمن إضافي

الاختباران `xfail(strict=True)` القدام (§ realestate/invitations) اتحوّلوا لاختباري نجاح حقيقيين
(`..._now_fixed`)، + اختبار ثالث جديد لـinvitations (`..._failure_leaves_no_orphan_message`) يثبت
إن مسار الفشل الآمن (لو `execute_agent_action` فشلت لأي سبب) مايسيبش رسالة مستخدم يتيمة.

**اكتشافان جانبيان (خارج نطاق هذه الجلسة، موثَّقان فقط، صفر إصلاح) ظهروا أثناء محاولة تشغيل
الاختبار الحي لـrealestate:**

1. **`ai_governance.check_and_consume()` (`ai_governance/service.py:165-200`) عندها نفس بالضبط
   عيب `begin_nested()`+`commit()` داخلي** — وبتتنادى من `realestate._check_ai_governance()`
   من **جوّه** `begin_nested()` الخارجي بتاعة `buy_fractional_ownership()` نفسها (سطر 303، غير
   متأثر بهذا الإصلاح). الاستثناء بيتبلع بـ`try/except` موجودة أصلاً في `_check_ai_governance`،
   لكن الجلسة بتفضل بحالة transaction مقفولة، فأي عملية DB تالية (`_get_land_owner_for_unit`)
   بتفشل بـ`InvalidRequestError` غير معالَجة. **هذا يعني `buy_fractional_ownership` كانت
   وهتفضل معطوبة بالكامل حتى بعد إصلاح #16، لكن بسبب مختلف (call-site مختلف: `ai_governance`
   مش `ai_agents`).** بند Backlog جديد يستاهل جلسة منفصلة: `ai-governance-check-and-consume-commit-inside-begin-nested`.
2. **`invitations.chat_with_ai()`'s `reply_text = ai_response.get("result", {}).get("reply", <fallback>)`
   بيدوّر على مفتاح `"reply"` غير موجود إطلاقًا** في القيمة الحقيقية المُرجَعة من
   `ai_engine.generate()` (`services/ai/engine.py:157`، المفتاح الفعلي `"text"`) — يعني
   `chat_with_ai` **بترجع نص الـfallback الثابت دايمًا**، مش رد الـAI الفعلي، في الإنتاج
   الحقيقي وبعد هذا الإصلاح على حد سواء. باج مستقل تمامًا عن begin_nested/commit، موجود من
   قبل هذه الجلسة. بند Backlog جديد: `invitations-chat-with-ai-reply-key-mismatch`.

للتحقق الحي المعزول (نفس منهجية تفادي بج #7 المُسبَّق)، الاختبارات بتعمل `monkeypatch` لـ
`_check_ai_governance` (realestate) وتتحقق من نص الـfallback الفعلي (invitations) بدل نص AI
وهمي — بدون لمس أي كود إنتاج لهذين الاكتشافين.

### 5.4 التحقق الحي — نتائج التشغيل الفعلي

**سلسلة تصحيحات على الاختبار نفسه (صفر تعديل على كود الإنتاج) قبل الوصول لتشغيلة ناجحة —
موثَّقة بالكامل لأنها كشفت 3 أعطال بيئة/بيانات throwaway حقيقية وواحد اكتشاف جانبي جديد:**

1. **`MultipleResultsFound`** — `UserService.register()` بينشئ محفظة تلقائيًا (`balances={}`) لكل
   مستخدم جديد؛ محاولة إضافة `Wallet` ثانية لنفس المشتري بالاختبار سبَّبت صفين. **الحل:**
   `UPDATE` على الصف الموجود بدل `INSERT` جديد.
2. **`PendingRollbackError`/`MissingGreenlet`** — الوصول لـ`.id`/خصائص ORM بعد `db.rollback()`
   (بعد فشل `invoicing.create_invoice()` — راجع البند التالي) على كائنات منتهية الصلاحية
   (`expire_on_commit=True` الافتراضي) بيفشل خارج سياق greenlet صحيح. **الحل:** لقط كل الـ
   IDs كمتغيرات Python عادية (`unit_id`, `development_id`, `buyer_id`, `owner_id`) فور
   الإنشاء، بدل الاعتماد على `.id` بعد أي commit/rollback لاحق.
3. **اكتشاف جانبي جديد [موثَّق، غير مُصلَح — خارج نطاق هذه الجلسة]:** `invoicing.create_invoice()`
   بتفشل باستمرار بـ`IntegrityError` على `invoice_number` مكرر (`INV-1-000015` تكرر حرفيًا عبر
   3 تشغيلات throwaway مختلفة تمامًا) — **نفس الاكتشاف الموثَّق سابقًا في رسالة commit `b4bf356`**
   ("an invoice-numbering collision surfaced while testing #37"، لسه غير مُصلَح). production
   code بيمسكها بـ`try/except` (الشراء نفسه سليم)، لكن **الفلاش الفاشل بيسيب الجلسة بحالة
   `PendingRollbackError` حقيقية** — أي وصول تالٍ لخاصية ORM منتهية الصلاحية (زي
   `ownership.acquisition_date` في فرع تخزين الـidempotency) بيفشل ويُسقِط `buy_fractional_ownership`
   بالكامل بلا معالجة. **هذا تفاعل جديد بين بجين معروفين مسبقًا (invoice numbering +
   عدم `rollback()` صريح بعد استثناء DB مُمسوك) ظهر فقط الآن لأن إصلاح begin_nested سمح للكود
   يوصل لعمق أكبر من أي وقت مضى** — **بند Backlog إضافي يستاهل التوثيق:**
   `invoicing-create-invoice-numbering-collision-poisons-session-on-idempotency-store`.
   **للتحقق المعزول (نفس منهجية Redis #7)، الاختبار بيعمل monkeypatch لـ
   `InvoicingService.create_invoice` (noop) — صفر لمس على كود الإنتاج.**

**النتيجة النهائية:**
```
tests/test_ai_agents_execute_action.py::test_realestate_buy_fractional_ownership_execute_agent_action_now_fixed PASSED
```
كل الـ4 assertions الحاسمة نجحت (الشراء تم، الملكية محفوظة، `execute_agent_action` نُفِّذت
فعليًا بعد `commit()` الرئيسي بلا `InvalidRequestError`، طلب الموافقة مسجَّل بنفس الـidempotency_key)
— **الدليل القاطع إن إصلاح begin_nested/commit شغّال فعليًا في `realestate`.** تحقق مستقل بعد
التشغيلة الناجحة: صفر بيانات throwaway متبقية (`ai_agents`, `users`, `property_units` = 0).

**تشغيلة الملف كامل بعد كل التصحيحات:**
```
7 passed, 10 warnings in 194.54s
```
كل الـ7 اختبارات نجحت (4 مرتبطة بمنطق `execute_agent_action` الأصلي غير المتأثر + 3 جديدة/محدَّثة
لهذه الجلسة: `realestate` نجاح، `invitations` نجاح، `invitations` فشل آمن). **تحقق مستقل بعد
التشغيلة الكاملة: صفر بيانات throwaway متبقية** (`ai_agents=0`, `users` بادئة `p_regtest_agents16=0`,
`property_units=0`, `invitation_conversations` المرتبطة بدعوات throwaway `=0`).

**ملاحظة منهجية عن `scratchpad/repro_begin_nested_commit.py` (سكربت التحقيق الأصلي، §3):**
أُعيد تشغيله بعد الإصلاح للتأكد — **لسه بيرمي نفس `InvalidRequestError` بالضبط.** هذا **متوقَّع
وصحيح، مش تراجع**: السكربت بيبني نمط `begin_nested()` صناعي بيدوي ثم ينادي `execute_agent_action()`
منه مباشرة (تكرار مقصود للـanti-pattern نفسه لإثبات آليته)، **ولا ينادي `buy_fractional_ownership()`/
`chat_with_ai()` الحقيقيتين إطلاقًا.** الإصلاح الفعلي غيَّر **الكولرين الحقيقيين** (نقل/رفع نداء
`execute_agent_action` بره حدود `begin_nested()` بتاعتهم) — لم يغيّر ولا يفترض أن يغيّر حقيقة إن
"نداء `execute_agent_action` من جوّه أي `begin_nested()`" لسه بينكسر (وهذا صحيح تصميميًا، راجع
القرار في §4: `execute_agent_action()` نفسها لم تُلمَس عمدًا). **الدليل الحقيقي على نجاح الإصلاح
هو تشغيل الدالتين الفعليتين المُعدَّلتين (`test_realestate_...`, `test_invitations_..._now_fixed`)
عبر `pytest` أعلاه، مش إعادة تشغيل السكربت الصناعي.**

---

## 6) ✅ ختم إغلاق — 5 نقاط طلبها المستخدم [2026-09-01]

1. ✅ **`realestate/service.py`** — نداء `execute_agent_action` نُقل لبعد `self.db.commit()` الرئيسي،
   نفس نمط/مكان `invoicing.create_invoice()` المجاور، `try/except`. صفر تغيير على القيم الممرَّرة.
2. ✅ **`invitations/service.py`** — بناء الـ`prompt` + نداء `execute_agent_action` رُفعا لقبل
   `begin_nested()`، `tenant_id=` الزائدة اتشالت، `idempotency_key=` أُضيفت (نمط `AI-CRMCHAT-T{tenant_id}-...`
   المعتمد سابقًا)، كتابتا المحادثة (مستخدم+AI) + الـinteraction دُمجوا في بلوك `begin_nested` واحد
   بعد الحصول على `reply_text`.
3. ✅ **الاختباران `xfail(strict=True)`** تحوّلوا لاختباري نجاح حقيقيين (`..._now_fixed`) + اختبار
   ثالث جديد لـ`invitations` (`..._failure_leaves_no_orphan_message`) يثبت صفر رسالة يتيمة حتى في
   مسار الفشل الآمن.
4. ✅ **تحقق حي كامل بعد كل تعديل** — تشغيل الملف كامل (7/7 نجح)، تأكيد `InvalidRequestError` لم
   يعد يحصل في الكولرين الحقيقيين (اختبارا النجاح يثبتان تنفيذ `execute_agent_action` كاملًا بلا
   استثناء)، تأكيد صفر صف يتيم (`realestate`: `AITaskLog`/`AgentApprovalQueue` بنفس الـidempotency_key
   المتوقَّع، صفر صف بلا موافقة مطابقة؛ `invitations`: رسالتا محادثة سوا في النجاح، صفر رسالة عند الفشل).
5. ✅ **ملاحظة `PROGRESS_LOG.md`** — قسم جديد ["[2026-09-01] درس عام — انتهاك تحذير Backlog موثَّق
   صراحة أثناء 'إصلاح نمطي' لاحق"] يوثّق أن commit `b4bf356` صحّح `realestate:306` بدون مراجعة
   التحذير الصريح الموثَّق في `ai-agents-execute-action-fix-session-log.md`، + توصية عامة (`grep`
   عن اسم الموضع في التقارير/`PROGRESS_LOG.md` قبل أي دفعة "إصلاحات نمطية متشابهة").

**اكتشافان جانبيان جدد، موثَّقان فقط (صفر إصلاح، خارج نطاق الموافقة الحالية):**
- `ai-governance-check-and-consume-commit-inside-begin-nested` — نفس فئة الباج بالضبط، لكن في
  `ai_governance.check_and_consume()` (لا `ai_agents.execute_agent_action`)، مستدعاة من
  `realestate._check_ai_governance()` من جوّه `begin_nested()` الخارجي بتاعة `buy_fractional_ownership`
  نفسها (سطر 303، غير مُلمَس هنا). مُبلَعة حاليًا بـ`try/except` موجودة، لكنها بتترك الجلسة بحالة
  transaction مقفولة لأي عملية DB تالية.
- `invitations-chat-with-ai-reply-key-mismatch` — `reply_text = ai_response.get("result", {}).get("reply", ...)`
  بيدوّر على مفتاح `"reply"` غير موجود إطلاقًا في القيمة الحقيقية المُرجَعة من `ai_engine.generate()`
  (المفتاح الفعلي `"text"`) — `chat_with_ai` بترجع نص fallback ثابت دايمًا، مش رد الـAI الفعلي. باج
  مستقل تمامًا، موجود من قبل هذه الجلسة وبعدها.
- (معروف مسبقًا، تأكيد إضافي فقط) `invoicing-create-invoice-numbering-collision` — راجع §5.4 نقطة 3.

**الحالة النهائية: مُغلَق بالكامل.** كل الملفات الثلاثة (`realestate/service.py`,
`invitations/service.py`, `tests/test_ai_agents_execute_action.py`) + `PROGRESS_LOG.md` مُعدَّلة
ومُتحقَّق منها حيًا. `git diff --stat` + commit التاليان.
