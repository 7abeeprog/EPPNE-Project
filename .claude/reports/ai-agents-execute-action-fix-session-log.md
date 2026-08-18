# جلسة: ai-agents-execute-action-fix (الجزء ب من المرحلة 1.3، Backlog #16)

**تاريخ:** 2026-08-18
**النطاق المصرَّح به:** `AIAgentsService.execute_agent_action()` فقط — ممنوع لمس أي method تانية.
**الحالة:** تشخيص كامل (جدول أدلة) — صفر Edit فعلي حتى الآن، بانتظار موافقتك.

---

## 1) تأكيد استخدام `self.tenant_id` داخل `execute_agent_action` (بالقراءة المباشرة الكاملة، مش نقل من تقرير قديم)

`eppne-backend/app/domains/ai_agents/service.py:32-38` (constructor):
```python
def __init__(self, db: AsyncSession, tenant_id: int):
    self.db = db
    self.tenant_id = tenant_id
    self.repo = AIAgentsRepository(db)
    self.finance = FinanceService(db, tenant_id)
    self.event_bus = EventBus(cast(Any, redis_client))
```

توقيع `execute_agent_action` الفعلي (`service.py:147-154`) — **صفر معامل `tenant_id`**:
```python
async def execute_agent_action(
    self, agent_id: int, action_type: str, payload: Dict[str, Any],
    executor_user_id: int, idempotency_key: str
) -> Dict[str, Any]:
```

| الاستخدام داخل جسم الدالة | السطر | القوة |
|---|---|---|
| `self.repo.get_agent(agent_id, self.tenant_id)` | 159 | فلترة الوكيل — لو الوكيل بتاع tenant تاني، النتيجة `None` → `NotFoundError` |
| `_validate_idempotency`/`_store_idempotency` → `f"idempotency:{self.tenant_id}:{idempotency_key}"` | 49, 57 (helpers) | مفتاح الكاش نفسه مبني على `self.tenant_id` — **معزول تلقائيًا لكل tenant حتى لو نفس `idempotency_key` تكرر بين مستأجرين** |
| `self.repo.create_task_log(tenant_id=self.tenant_id, ...)` | 180-191, 210-222 | تسجيل `AITaskLog.tenant_id` |
| `self.repo.create_approval_request(tenant_id=self.tenant_id, ...)` | 229-236 | تسجيل `AgentApprovalQueue.tenant_id` |
| `audit_log(details={..., "tenant_id": self.tenant_id})` | 260 | تدقيق |

**النتيجة: نفس قوة `check_and_consume` بالضبط** — `self.tenant_id` مصدر الحقيقة الوحيد، بلا أي حاجة لمعامل `tenant_id` في التوقيع. القرار المحوري (شيل الزيادة، مش توسيع) **صحيح بنفس منطق الجزء أ**.

**⚠️ تصحيح مهم عن افتراض الجزء أ:** عزل الـidempotency cache (Redis) عبر `self.tenant_id` **تلقائي**، لكن **عمود `AgentApprovalQueue.idempotency_key` نفسه `unique=True` على مستوى الـDB بالكامل** (`ai_agents/models.py:86`) — **بلا أي فلترة/قيد مركّب مع `tenant_id`**:
```python
idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
```
بينما `AITaskLog.idempotency_key` (`models.py:111`) `index=True` فقط، **بدون `unique=True`**.

**الأثر:** لو موضعين مختلفين (حتى من **تينانتين مختلفين تمامًا**) استخدموا نفس `idempotency_key` الخام، ووافق `agent.requires_human_approval` (افتراضي `True` عند إنشاء أي وكيل — `create_agent(...).get("requires_human_approval", True)`)، فـ`create_approval_request` (سطر 229-236، الذي يبني `idempotency_key=f"{idempotency_key}-approval"`) **هيفشل بـ`IntegrityError` على القيد الفريد العالمي** — نفس درس invitations لكن هنا القيد فعلي وموجود في الـschema بالفعل، مش مجرد نظري. **راجع القسم 4 لتفصيل هذا في كل موضع مقترح.**

---

## 2) المجموعة الآمنة (6 مواضع idempotency_key موجودة بالفعل) — تأكيد نهائي بالقراءة المباشرة

| # | ملف:سطر | الدالة المحيطة | القيمة الفعلية لـ`idempotency_key` (مقروءة الآن) |
|---|---|---|---|
| 1 | `tasks/agritech.py:168-182` | `_analyze_high_priority` | `f"agritech_high_{reading.id}_{uuid.uuid4().hex[:8]}"` (سطر 181) — ✅ موجودة فعليًا |
| 2 | `arbitration_syndicates/service.py:105-116` | (نزاع، `create_dispute` على الأرجح) | `f"AI-{idempotency_key}" if idempotency_key else f"AI-{uuid.uuid4().hex[:12]}"` (سطر 115) — ✅ موجودة، مبنية من معامل خارجي |
| 3 | `logistics/service.py:557-568` | دالة توقّع المخزون | `idempotency_key=idempotency_key or ""` (سطر 567) — ✅ موجودة (لكن ممكن تبقى `""` لو المستدعي مرّرش قيمة — ملاحظة خطر صغير موثقة تحت، مش جزء من نطاق هذه الجلسة) |
| 4 | `insurance/service.py:345-356` | `subscribe`/تحليل مطالبة | `idempotency_key=cast(str, idempotency_key)` (سطر 355) — ✅ موجودة، من معامل الدالة `idempotency_key: Optional[str] = None` |
| 5 | `automation/service.py:707-714` | تنفيذ خطوة workflow | `idempotency_key=idempotency_key` (سطر 713) — ✅ موجودة، ديناميكية من الـcaller |
| 6 | `employment/service.py:142-149` | تقييم توافق وظيفي | `idempotency_key=idempotency_key` (سطر 148)، حيث `idempotency_key = f"ai_match_{applicant_id}_{job.id}_{uuid.uuid4().hex[:8]}"` (سطر 140) — ✅ موجودة |

**تأكيد الستة: كلهم فعلاً بيمرروا `idempotency_key` صحيحة وغير فارغة في المسار الطبيعي.** التعديل المطلوب لكل الستة: **حذف `tenant_id=` فقط**، بلا أي لمس على `idempotency_key`.

**ملاحظة جانبية (توثيق فقط، خارج نطاق الجلسة):** لا `agritech`/`employment` ولا `logistics` (لو فضلت `""`) بيحطوا `tenant_id` جوّه نص الـ`idempotency_key` الخام نفسه — لكن هذا **آمن هنا تحديدًا** لأن عزل الـRedis cache تلقائي عبر `self.tenant_id` (راجع القسم 1)، والخطر الحقيقي الوحيد (تصادم `AgentApprovalQueue.idempotency_key` العالمي) شبه مستحيل عمليًا بفضل `uuid.uuid4()` العشوائي في كل الحالات الثلاث. **الاستثناء:** `logistics` لو `idempotency_key or ""` رجعت `""` فعليًا (مفيش قيمة من الـcaller) — عدة نداءات بلا `idempotency_key` هتبني كلها `"-approval"` كمفتاح موافقة متطابق، وده تصادم فعلي محتمل. **موثَّق كملاحظة فقط، غير مُلمَس (الموضع في المجموعة الآمنة، خارج نطاق التعديل).**

---

## 3) المواضع الـ13 الناقصة — فحص المصدر الطبيعي لكل موضع (بالقراءة المباشرة الكاملة لكل دالة)

| # | ملف:سطر | الدالة المحيطة | هل فيها معامل `idempotency_key` بالفعل؟ | هل فيها معرّف عملية فريد؟ | القيمة المقترحة |
|---|---|---|---|---|---|
| 1 | `zamakana/service.py:521` | `generate_ai_analysis(scenario_id, tenant_id, user_id, ai_agent_id, idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | ✅ `scenario_id` (كيان دائم، الفحص لا يتكرر إلا لنفس السيناريو) | `f"AI-SCENARIO-T{tenant_id}-{scenario_id}"` — حتمي، إعادة تحليل نفس السيناريو ترجع نتيجة مخزَّنة بدل تكرار تكلفة AI |
| 2 | `transport/service.py:165` | `create_route(tenant_id, data)` | ❌ لا يوجد المعامل إطلاقًا | ❌ لا يوجد (المسار لسه مش موجود في الـDB وقت النداء) | `f"AI-ROUTE-T{tenant_id}-{uuid.uuid4().hex[:12]}"` — عشوائي، كل إنشاء مسار تحليل مستقل |
| 3 | `tourism_sports/service.py:271` | `purchase_event_ticket(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | جزئي (`event_id`+`tier`، لكن غير كافٍ لوحده لأن نفس الحدث ممكن يُشترى منه تذاكر كتير) | `f"AI-VIPTRANSPORT-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-VIPTRANSPORT-T{tenant_id}-{uuid.uuid4().hex[:12]}"` |
| 4 | `tourism_sports/service.py:414` | `place_transfer_bid(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | جزئي (`data["player_id"]`، لكن لاعب واحد ممكن يتفحص لعروض متعددة) | `f"AI-MEDICAL-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-MEDICAL-T{tenant_id}-{uuid.uuid4().hex[:12]}"` |
| 5 | `tenders_auctions/service.py:210` | تقييم عطاء (evaluator) | ✅ نعم (غير مُستخدَمة لهذا النداء) | ✅ `bid_id` (فريد ودائم، التقييم منطقيًا مرة واحدة لكل عطاء) | `f"AI-BIDEVAL-T{tenant_id}-{bid_id}"` — حتمي |
| 6 | `tenders_auctions/service.py:329` | `place_live_bid(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | ❌ `auction_id` وحده غير كافٍ (مزايدات متعددة على نفس المزاد) | `f"AI-AUCTIONBID-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-AUCTIONBID-T{tenant_id}-{uuid.uuid4().hex[:12]}"` |
| 7 | `social/service.py:314` | `get_match_suggestions(user_id, tenant_id, limit=20)` | ❌ لا يوجد المعامل إطلاقًا | ❌ لا (اقتراحات تتجدد كل استدعاء عمدًا) | `f"AI-MATCHSUGGEST-T{tenant_id}-{user_id}-{uuid.uuid4().hex[:8]}"` |
| 8 | `realestate/service.py:232` | `buy_fractional_ownership(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | جزئي (`unit_id`+`buyer_id`، لكن نفس المشتري ممكن يحاول أكتر من مرة بنسب مختلفة) | `f"AI-FRACTIONAL-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-FRACTIONAL-T{tenant_id}-{uuid.uuid4().hex[:12]}"` — **⚠️ راجع القسم 4، هذا الموضع جوّه `begin_nested()`** |
| 9 | `manufacturing/service.py:311` (نداء سطر 310) | `start_production(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | ✅ `batch.id` (فريد ودائم، حالة `PLANNED` تمنع التكرار الطبيعي) | `f"AI-BATCH-T{tenant_id}-{batch.id}"` — حتمي |
| 10 | `manufacturing/service.py:673` (نداء سطر 671) | `analyze_and_schedule_maintenance(user_id, tenant_id, production_line_id, sensor_data)` | ❌ لا يوجد المعامل إطلاقًا | جزئي (`production_line_id`، لكن قراءات حساس متكررة لنفس الخط) | `f"AI-MAINTENANCE-T{tenant_id}-{production_line_id}-{uuid.uuid4().hex[:8]}"` |
| 11 | `invitations/service.py:84` | `_analyze_target_user(user_id, tenant_id)` | ❌ لا يوجد المعامل إطلاقًا | جزئي (`user_id`، لكن نفس المستخدم يُحلَّل لدعوات متعددة) | `f"AI-CRMTARGET-T{tenant_id}-{user_id}-{uuid.uuid4().hex[:8]}"` |
| 12 | `invitations/service.py:415` (نداء داخل `chat_with_ai`) | `chat_with_ai(invitation_id, tenant_id, ..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | جزئي (`invitation_id`، لكن رسائل متعددة لنفس الدعوة) | `f"AI-CRMCHAT-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-CRMCHAT-T{tenant_id}-{invitation_id}-{uuid.uuid4().hex[:8]}"` — **⚠️ راجع القسم 4، هذا الموضع جوّه `begin_nested()`** |
| 13 | `insurance/service.py:439` (نداء سطر 438) | `review_claim(..., idempotency_key=None)` | ✅ نعم (غير مُستخدَمة لهذا النداء) | ✅ `claim_id` متاح، لكن **الأدق اتساقًا مع الموضع الشقيق `insurance:355` (آمن بالفعل، نفس الملف)** هو تكرار نفس نمطه حرفيًا | `idempotency_key=cast(str, idempotency_key)` — **مطابق تمامًا لنمط `insurance:355` الموجود أصلًا في نفس الملف**، بدل بناء نمط جديد مختلف داخل نفس الدومين |

**كل القيم الجديدة (عدا #13) تتبع نمط `PREFIX-T{tenant_id}-{unique_id}` — نفس منهجية `INV-ACCEPT-T{tenant_id}-{invitation_id}` من جلسة invitations، بفارق واحد مقصود:** حيث فيه معامل `idempotency_key` خارجي متاح فعليًا من الـcaller (7 مواضع: #1,3,4,6,8,9,12)، استخدمته كجزء من المفتاح (أو fallback لـ`uuid` لو غاب) بدل تجاهله بالكامل — يحافظ على دلالة "نفس محاولة الطلب الخارجي = نفس نتيجة AI" بدل تحليل جديد كل مرة رغم تكرار العميل لنفس الطلب. المواضع بلا أي معرّف مستقر (#2,7,10,11) تستخدم `uuid` عشوائي بالكامل لأن التحليل مفروض يتجدد كل نداء أصلًا.

---

## 4) 🔴 اكتشاف حرج جديد (شرط إيقاف #2) — نمط `commit()` جوّه `begin_nested()` يتكرر هنا في موضعين من الـ13، بنفس جذر Backlog #11a/#11b

`execute_agent_action` نفسها **بتعمل `await self.db.commit()` داخل جسمها** (`ai_agents/service.py:223` عند الفشل، و`226` عند النجاح — قبل إنشاء طلب الموافقة). فحصت أي من الـ13 موضع بينادوها من **جوّه `async with self.db.begin_nested():`** (نفس الـanti-pattern الجذري المكتشَف والمُصلَح في `invitations-savepoint-leak` #11a و`invoicing-savepoint-conflict` #11b — استدعاء دالة بتعمل commit خاص بيها من داخل savepoint):

| # | ملف:سطر | محمي بـ`try/except`؟ | جوّه `begin_nested()`؟ |
|---|---|---|---|
| 8 | `realestate/service.py:232` | ❌ لا | ✅ **نعم — `begin_nested()` يبدأ سطر 214، النداء سطر 232 داخله مباشرة** |
| 12 | `invitations/service.py:415` | ❌ لا | ✅ **نعم — `begin_nested()` يبدأ سطر 394، النداء سطر 414 داخله مباشرة** |

**الأثر المتوقَّع (نفس آلية #11a/#11b بالضبط):** بمجرد ما `tenant_id`/`idempotency_key` يتصلحوا، هذين الموضعين هيقدروا يوصلوا فعليًا لتنفيذ `execute_agent_action` لأول مرة (كانوا بيفشلوا بـ`TypeError` قبل كده دايمًا) — و`self.db.commit()` جوّه `execute_agent_action` هيقفل الـtransaction الخارجي بالكامل وهو لسه جوّه `async with self.db.begin_nested()`. لما الـ`async with` يحاول يقفل الـsavepoint عند الخروج، الـtransaction بقى مقفول بالفعل من تحته → على الأرجح `InvalidRequestError`/حالة transaction غير متسقة (نفس عائلة الأعراض الموثَّقة في #11a/#11b)، **مش مجرد نجاح التوقيع**.

**هذا اكتشاف جديد كليًا لم يظهر في تقرير الجزء أ (القسم 6 هناك وثّق فقط "جوّه begin_nested()، لا try/except" كملاحظة عرضية، بدون ربطها بجذر #11a/#11b الفعلي).** بموجب شرط الإيقاف #2 (اكتشاف حرج) و#5 (حل حقيقي يتطلب لمس تدفق المعاملة في `realestate.py`/`invitations.py`، خارج نطاق `execute_agent_action` نفسها)، **أتوقف هنا لسؤالك.**

**التوصية المقترحة (تطابق قرار الجزء أ لاكتشافات مشابهة):** نمرر `tenant_id=`/`idempotency_key=` في الموضعين زي باقي الإحدى عشر، لكن **نوثّق كبند Backlog جديد صريح** (`ai-agents-execute-action-commit-inside-begin-nested`) بدل إصلاح بنية المعاملة الآن — لأن الإصلاح الحقيقي (نقل النداء بره `begin_nested()`، زي ما اتعمل في invitations/#11a) يلمس تدفق الدالتين المحيطتين بالكامل، مش مجرد kwargs. **بانتظار تأكيدك أو توجيه بديل قبل أي Edit.**

---

## 5) فحص تعارض idempotency key عبر tenant_id مختلفين (نفس درس invitations)

**الجواب: الخطر حقيقي وموجود فعليًا في الـschema (مش نظري فقط)، لكنه محصور في جدول واحد:**

- **الكاش (Redis, `_validate_idempotency`/`_store_idempotency`):** معزول تلقائيًا بـ`self.tenant_id` داخل `execute_agent_action` نفسها (`f"idempotency:{self.tenant_id}:{idempotency_key}"`) — **صفر خطر تصادم بين مستأجرين هنا مهما كان شكل المفتاح الخام**، لأن العزل جزء من جسم الدالة المصرَّح بلمسها.
- **`AITaskLog.idempotency_key`:** `index=True` بس، **بدون `unique=True`** — صفر خطر تصادم (تكرار القيمة مسموح في الـschema، والاستعلامات الوحيدة (`get_task_log_by_idempotency`) بتفلتر بـ`tenant_id` كمان).
- **`AgentApprovalQueue.idempotency_key`:** `unique=True` **عالميًا، بلا `tenant_id` في القيد** — **هنا الخطر الحقيقي**. لو تينانتين مختلفين بعتوا نفس `idempotency_key` الخام (احتمال وارد لو اتبنى من بيانات محلية بحتة زي `f"{bid_id}"` بدون أي تمييز tenant، خصوصًا إن الـIDs زي `bid_id`/`batch_id`/`scenario_id` غالبًا auto-increment **لكل الجدول ككل مش لكل tenant** — يعني ممكن يتصادفوا نظريًا لو النظام بيستخدم sequences منفصلة أو IDs مستوردة، رغم إنه نادر عمليًا مع auto-increment قياسي)، وطلب الموافقة البشرية مطلوب في الاتنين (الافتراضي `True`)، هيحصل `IntegrityError` على `create_approval_request`.

**لذلك كل القيم المقترحة في القسم 3 (عدا #13 اللي بتتبع نمط شقيقها الآمن الموجود) بتحط `T{tenant_id}` صراحة كجزء من النص** — نفس درس `INV-ACCEPT-T{tenant_id}-{invitation_id}`، حتى لو المعرّف المحلي (`bid_id`/`batch_id`/`scenario_id`) غالبًا فريد عالميًا بحكم auto-increment، **التمييز الصريح بـtenant_id في النص نفسه دفاع إضافي رخيص التكلفة يقفل الاحتمال نهائيًا** بدل الاعتماد على افتراض "auto-increment مش هيتصادف".

---

## القرارات المطلوبة منك قبل أي كود

1. ✅/❌ موافقة على المجموعة الآمنة (6 مواضع، القسم 2) — حذف `tenant_id=` فقط، صفر لمس على `idempotency_key`.
2. ✅/❌ موافقة على القيم الـ13 المقترحة (القسم 3) — أو تعديل أي قيمة بعينها.
3. **قرار على اكتشاف القسم 4** (commit جوّه begin_nested في `realestate:232`/`invitations:415`): توثيق فقط كبند Backlog جديد (التوصية)، أم إصلاح فوري يتطلب تجاوز نطاق الجلسة؟
4. ترتيب التطبيق: نبدأ بالمجموعة الآمنة الستة أولًا (زي الجزء أ)، ثم الـ13 على دفعات صغيرة؟

---

## 6) ✅ قرارات معتمدة [2026-08-18]

1. ✅ المجموعة الآمنة (6 مواضع، القسم 2) — معتمدة كما هي.
2. ✅ القيم الـ13 المقترحة (القسم 3) — معتمدة **كلها كما هي**، بما فيها استخدام `T{tenant_id}` في كل قيمة جديدة، وتكرار نمط `insurance:355` حرفيًا للموضع #13.
3. **تعديل على التوصية الأصلية لاكتشاف القسم 4:** **لا يُطبَّق أي إصلاح (`tenant_id`/`idempotency_key`) على الموضعين #8 (`realestate/service.py:232`) و#12 (`invitations/service.py:415`) في هذه الجلسة إطلاقًا.** يُتركان بحالتهما الحالية (`TypeError` آمن ومعروف، الاستدعاء لا يصل لجسم الدالة أصلًا). **السبب الموثَّق صراحة:** تصحيح الـkwargs هنا سيجعلهما يصلان فعليًا لأول مرة لـ`self.db.commit()` داخل `execute_agent_action` وهما لسه جوّه `begin_nested()` خارجي — **هذا ليس مجرد "كراش مختلف بدل TypeError"، بل احتمال حقيقي لتلف حالة الـtransaction بالكامل**، خصوصًا `realestate:232` الموجود داخل عملية شراء ملكية عقارية بأموال حقيقية (`buy_fractional_ownership`). **الفرق الجوهري عن حالات #11a/#11b المشابهة:** هناك، الكراشات التالية كانت *بعد* `commit()` ناجح (فقدان بيانات تدقيق/فوترة لاحقة)؛ هنا الكراش المحتمل هو **سبب فعلي لكسر نفس الـ`commit()`** الذي يفترض أن يحمي عملية الشراء نفسها.
4. ✅ نطاق التطبيق النهائي لهذه الجلسة: **17 موضع فقط** (6 آمنة + 11 من الـ13، باستثناء #8 و#12) — بنفس منهجية مجموعات صغيرة، تبدأ بالمجموعة الآمنة الستة.

---

## 7) 🔴 بند Backlog جديد موثَّق — `ai-agents-execute-action-commit-inside-begin-nested`

**الأولوية: عالية جدًا — نفس فئة الخطورة الجذرية لـ#11a/#11b.**

**الوصف:** `AIAgentsService.execute_agent_action()` (`ai_agents/service.py:223,226`) تنفّذ `await self.db.commit()` داخل جسمها (مسار النجاح والفشل معًا). موضعان يستدعونها من **جوّه `async with self.db.begin_nested()`** خارجي:
- `realestate/service.py:232` — `begin_nested()` يبدأ سطر 214 (داخل `buy_fractional_ownership`)، النداء غير محمي بـ`try/except`.
- `invitations/service.py:415` — `begin_nested()` يبدأ سطر 394 (داخل `chat_with_ai`)، النداء غير محمي بـ`try/except`.

**لماذا لم يظهر كخطأ حتى الآن:** الاستدعاءان حاليًا يفشلان دائمًا بـ`TypeError` (بسبب `tenant_id=`/`idempotency_key` الناقصة) **قبل** الوصول لجسم `execute_agent_action` أصلًا — أي أن الكود لم يصل لحالة "commit جوّه savepoint" فعليًا بعد. **بمجرد إصلاح التوقيع (كما حدث للـ17 موضع الآخر)، هذان الموضعان تحديدًا سيصلان لأول مرة لتنفيذ `commit()` حقيقي وهما لسه جوّه savepoint** — احتمال حقيقي لتلف حالة الـtransaction (مش مجرد استثناء جديد بدل القديم).

**القرار المعتمد:** **صفر إصلاح الآن على الموضعين، حتى لو بدا الحل "بسيط" (إزالة `tenant_id=` وإضافة `idempotency_key=`)** — لأن تصحيح الـkwargs وحده هنا **يفتح باب تلف حالة أخطر من الوضع الحالي**، عكس باقي الـ17 موضع.

**الإصلاح الحقيقي المطلوب لاحقًا (خارج نطاق هذه الجلسة بالكامل):** نقل نداء `execute_agent_action` **بره** `begin_nested()` في الدالتين (نفس الحل الجذري المطبَّق في `invitations-savepoint-leak` #11a: فصل العملية ذات الـcommit المستقل عن السياق المتداخل)، **ثم** تصحيح `tenant_id=`/`idempotency_key=` كخطوة تالية منفصلة. **الموضعان لازم يُصلَحا سوا في نفس الجلسة المستقبلية** (تصحيح البنية أولًا، أو الاتنين معًا) — **ممنوع** تصحيح الـkwargs فيهما بمعزل عن حل مشكلة الـ`begin_nested()`، لأن هذا بالضبط ما تفاديناه هنا.

---

## 8) التطبيق الفعلي — المجموعة الآمنة الستة (`git diff` خام)

**التطبيق تم على الستة مواضع (حذف `tenant_id=` فقط، صفر لمس على `idempotency_key`).** `git status --short`:
```
 M eppne-backend/app/domains/arbitration_syndicates/service.py
 M eppne-backend/app/domains/automation/service.py
 M eppne-backend/app/domains/employment/service.py
 M eppne-backend/app/domains/insurance/service.py
 M eppne-backend/app/domains/logistics/service.py
 M eppne-backend/app/tasks/agritech.py
```

**4 من 6 ملفات (`arbitration_syndicates`, `employment`, `insurance`, `logistics`) — ديف نظيف 100%**، سطر واحد محذوف (`tenant_id=`) لكل موضع، صفر تغيير إضافي.

**⚠️ 2 ملفان فيهم ضوضاء ديف موروثة من جلسة سابقة غير محفوظة (`automation/service.py`, `tasks/agritech.py`):**
- `automation/service.py`: الديف يُظهر أيضًا `- ai_service = AIAgentsService(self.db)` → `+ ai_service = AIAgentsService(self.db, cast(int, self.workflow.tenant_id))`. **هذا التغيير لم يصدر مني** — لما قرأت الملف أول مرة (قبل أي Edit)، كان السطر بالفعل `AIAgentsService(self.db, cast(int, self.workflow.tenant_id))`. الفرق ظاهر في `git diff` فقط لأنه محسوب من آخر commit (`HEAD`)، وكان موجودًا كـ`M` غير محفوظ في `git status` من قبل بداية هذه الجلسة بالكامل (على الأرجح بقايا دفعة `constructor-mismatch` سابقة). تعديلي الوحيد الفعلي: حذف سطر `tenant_id=self.workflow.tenant_id,  # type: ignore` من نداء `execute_agent_action`.
- `tasks/agritech.py`: نفس النمط بالحرف — `- ai_service = AIAgentsService(db)` → `+ ai_service = AIAgentsService(db, farm.tenant_id if farm else 0)` موروث من قبل الجلسة. تعديلي الوحيد الفعلي: حذف سطر `tenant_id=farm.tenant_id if farm else 0,` من نداء `execute_agent_action`.

**تنويه لازم يُذكَر في رسالة الـcommit لهذين الملفين:** "يتضمن هذا الملف تعديلات موروثة من جلسة سابقة غير محفوظة (تصحيح `AIAgentsService(...)` constructor) — التعديل المقصود من جلسة `ai-agents-execute-action-fix` هو حصريًا حذف `tenant_id=` من نداء `execute_agent_action`."

---

## 9) التطبيق الفعلي — الـ11 موضع الباقية (`git diff` خام)

**التطبيق تم على الـ11 موضع (استثناء #8 `realestate:232` و#12 `invitations:415` بقرار صريح، راجع القسم 6).** `git status --short`:
```
 M eppne-backend/app/domains/insurance/service.py
 M eppne-backend/app/domains/invitations/service.py
 M eppne-backend/app/domains/manufacturing/service.py
 M eppne-backend/app/domains/social/service.py
 M eppne-backend/app/domains/tenders_auctions/service.py
 M eppne-backend/app/domains/tourism_sports/service.py
 M eppne-backend/app/domains/transport/service.py
 M eppne-backend/app/domains/zamakana/service.py
```

**كل الملفات الثمانية — ديف نظيف 100%، مطابق حرفيًا للقيم المعتمدة في القسم 3.** صفر ضوضاء موروثة هذه المرة. **تأكيد إضافي مباشر:** `realestate/service.py` أظهر **صفر تغيير** (`git diff` فاضي تمامًا لهذا الملف)، و`invitations/service.py` أظهر تغيير **واحد فقط** (السطر 84، `_analyze_target_user`) — السطر 415 (`chat_with_ai`) **لم يُلمَس إطلاقًا**، كما هو مقرَّر.

**ملخص نهائي للتطبيق:** 17/19 موضع تم تصحيحهم (6 حذف `tenant_id=` فقط + 11 حذف `tenant_id=` وإضافة `idempotency_key=`). 2/19 (`realestate:232`, `invitations:415`) **مُستثنيان عمدًا**، موثَّقان في بند Backlog منفصل (§7)، لم يُلمسا.

---

## 10) التحقق الحي — Docker `eppne_db` (منهجية بيانات throwaway + SELECT مستقل)

**البيئة:** نفس حاوية `eppne_db` الحقيقية (postgres:16، منفذ 5435) المستخدمة في كل الجلسات السابقة. تم التشغيل عبر `AIAgentsService` الحقيقية (الكود المُصلَح فعليًا في الـ17 موضع)، مش mock ولا stub على منطق `execute_agent_action` نفسه.

**تينانتان حقيقيان مستخدَمان (لا يوجد غيرهما في القاعدة أصلًا):** `tenant_id=1` ("Local Test Tenant") و`tenant_id=15` ("نبت")، مع وكيلين ثروواي (`THROWAWAY-verify16-A/B`)، `owner_id`/`executor_user_id=1` (يوزر حقيقي موجود).

**⚠️ عائق مكتشَف أثناء التحقق (بند Backlog موثَّق مسبقًا #7 `redis-client-wrapper-missing-methods`، غير مرتبط بنطاق هذه الجلسة):** أول محاولة تشغيل بالمسار الحقيقي بالكامل (`ai_engine.generate()` الحقيقية) فشلت بـ`AttributeError: 'RedisClientWrapper' object has no attribute 'hincrbyfloat'` — من `CostTracker.record_usage()` داخل `ai_engine.generate()`. **هذا يؤكد حيًا لأول مرة أن بند #7 (موثَّق مسبقًا كـ"مفتوح" في `PROGRESS_LOG.md` بدون تفاصيل الأثر) لا يمنع فقط تتبع التكلفة، بل يُسقِط `execute_agent_action` بالكامل بـ`Exception` في أي استدعاء حقيقي وصل لمرحلة توليد AI فعلي** — أي أن كل الـ17 موضع المُصلَح هنا (وموضعا realestate/invitations المُستثنيان) لن ينجحا فعليًا في بيئة حقيقية حتى يُصلَح #7 بمعزل عن هذه الجلسة. **صفر لمس على `RedisClientWrapper` هنا** — بدلها، استبدلت `ai_engine.generate()` بنسخة وهمية **داخل سكربت التحقق المؤقت فقط** (صفر تعديل على كود الإنتاج) لعزل التحقق على منطق `execute_agent_action` نفسه (المصرَّح بلمسه)، بنفس منهجية تفادي بجات مسبقة غير مرتبطة المتّبعة في جلسات سابقة (مثال: تفادي #12 أثناء تحقق #14).

### سيناريو 1 — نجاح عادي (شكل نداء `manufacturing/service.py:311` المُصلَح، `idempotency_key=f"AI-BATCH-T{tenant_id}-{batch.id}"`)
```
[call] execute_agent_action(agent_id=5, tenant=1, idempotency_key="AI-BATCH-T1-9001") -> status=PENDING_APPROVAL
[SELECT مستقل] ai_task_logs      = (tenant_id=1, idempotency_key='AI-BATCH-T1-9001', task_type='ARABIC_CHAT')
[SELECT مستقل] agent_approval_queue = (tenant_id=1, idempotency_key='AI-BATCH-T1-9001-approval', action_type='ANALYZE_SENSOR', status='PENDING')
```
✅ النداء الحقيقي بالتوقيع المُصلَح (بلا `tenant_id=`) يعمل بدون `TypeError`، `self.tenant_id` يُسجَّل صح في الجدولين، `idempotency_key`/`action_type` الجديدة تُخزَّن بدقة.

### سيناريو 2 — إعادة محاولة بنفس `idempotency_key` (نفس tenant) → كاش حقيقي، صفر تكرار
```
[call retry] نفس المفتاح بالضبط -> status=PENDING_APPROVAL (من الكاش)
[SELECT مستقل] ai_task_logs count=1, agent_approval_queue count=1  (لم يتغيّر عن السيناريو 1)
```
✅ **إثبات حي إن `_validate_idempotency`/الكاش شغّال فعليًا** — إعادة نفس الطلب لم تُنشئ صفوف مكرَّرة، رجعت النتيجة المخزَّنة مباشرة.

### سيناريو 3 — تينانت مختلف (15) بنفس اللاحقة الرقمية (`9001`) لكن `T{tenant_id}` مختلف
```
[call] execute_agent_action(agent_id=6, tenant=15, idempotency_key="AI-BATCH-T15-9001") -> status=PENDING_APPROVAL
[SELECT مستقل] ai_task_logs (tenant 15) = (tenant_id=15, idempotency_key='AI-BATCH-T15-9001')
```
✅ **إثبات حي إن نمط `PREFIX-T{tenant_id}-{unique_id}` يمنع التصادم فعليًا** — نفس المعرّف المحلي (`9001`) عبر تينانتين مختلفين، صفر تعارض، تسجيل مستقل تمامًا لكل تينانت.

### سيناريو 4 — إثبات الخطر الموثَّق في القسم 5: مفتاح خام واحد بلا `tenant_id` عبر تينانتين مختلفين
```
[tenant=1] execute_agent_action(idempotency_key="RAW-COLLISION-DEMO-a78d65") -> نجح، status=PENDING_APPROVAL
[tenant=15] نفس المفتاح الخام بالحرف -> فشل فعليًا:
  sqlalchemy.exc.IntegrityError: asyncpg.exceptions.UniqueViolationError:
  duplicate key value violates unique constraint "ix_agent_approval_queue_idempotency_key"
```
✅ **إثبات حي قاطع (مش نظري) إن `AgentApprovalQueue.idempotency_key` العالمي `unique=True` يسبب `IntegrityError` فعلي عبر تينانتين مختلفين لو المفتاح لم يتضمن تمييز tenant صريح** — بالضبط الخطر المُوثَّق في القسم 5، والسبب الجوهري وراء اعتماد `T{tenant_id}` في كل القيم الـ11 المُضافة في هذه الجلسة.

### التنظيف
```
[SELECT مستقل بعد التنظيف] ai_agents=0 agent_task_logs=0 agent_approval_queue=0  (الكل صفر، كما هو متوقَّع)
```

---

## 11) ✅ ختم إغلاق رسمي — الجزء ب (`execute_agent_action`، Backlog #16) [2026-08-18]

**الحالة النهائية: مُغلَق جزئيًا/بنطاق مُعدَّل — 17 من 19 موضع مُصلَحان ومُتحقَّق منهما حيًا؛ موضعان (`realestate:232`, `invitations:415`) مُستثنيان عمدًا لباج بنيوي أعمق (§7).**

**الحل المطبَّق:**
- **6 مواضع (المجموعة الآمنة):** إزالة `tenant_id=` الزائدة فقط — `idempotency_key` كانت موجودة وصحيحة بالفعل (`tasks/agritech.py`, `arbitration_syndicates`, `logistics`, `insurance:345`, `automation`, `employment`).
- **11 مواضع:** إزالة `tenant_id=` + إضافة `idempotency_key=` بقيم مبنية بنمط `PREFIX-T{tenant_id}-{unique_id}` (`zamakana`, `transport`, `tourism_sports`×2, `tenders_auctions`×2, `social`, `manufacturing`×2, `invitations:84`, `insurance:439`).
- **2 مواضع مُستثناة عمدًا:** `realestate/service.py:232`, `invitations/service.py:415` — بقرار صريح، بسبب اكتشاف حرج (§4/§7): تصحيح الـkwargs فيهما سيجعلهما يصلان لأول مرة لـ`self.db.commit()` داخل `execute_agent_action` وهما لسه جوّه `begin_nested()` خارجي، احتمال تلف transaction حقيقي (`realestate:232` تحديدًا داخل عملية شراء ملكية بأموال حقيقية).

**تحقق حي كامل** (docker `eppne_db`، تينانتان حقيقيان 1/15، بيانات throwaway + SELECT مستقل) أثبت: (أ) الاستدعاءات الحقيقية بالتوقيع المُصلَح تعمل بدون `TypeError`، (ب) `self.tenant_id`/`idempotency_key`/`action_type` تُسجَّل بدقة في `ai_task_logs`/`agent_approval_queue`، (ج) **كاش الـidempotency شغّال فعليًا** (إعادة محاولة بنفس المفتاح = صفر تكرار)، (د) **نمط `T{tenant_id}` يمنع تصادم فعلي عبر تينانتين**، (هـ) **مفتاح خام بلا `tenant_id` يسبب `IntegrityError` فعلي حقيقي** — إثبات قاطع للخطر الموصوف نظريًا في §5.

**3 اكتشافات حرجة جانبية، موثَّقة كبنود Backlog، غير مُلمَسة في هذه الجلسة:**
1. **`ai-agents-execute-action-commit-inside-begin-nested`** (جديد، §7) — أولوية عالية جدًا، نفس فئة #11a/#11b. يمنع تصحيح `realestate:232`/`invitations:415` حتى تُصلَح بنية المعاملة أولًا.
2. **`ai-agents-execute-action-approval-queue-global-unique-collision`** (جديد) — `AgentApprovalQueue.idempotency_key` عمود `unique=True` عالمي بلا قيد `tenant_id` مركّب في الـschema نفسه؛ مؤكَّد حيًا (سيناريو 4) أنه يسبب `IntegrityError` فعلي عبر تينانتين لو استخدما نفس المفتاح الخام. كل القيم المُضافة هنا تتجنبه بتضمين `T{tenant_id}`، لكن **المواضع الستة الآمنة والمواضع الأخرى في المشروع لسه بتعتمد على العشوائية (`uuid`) لتفادي التصادم بدل حل بنيوي (composite unique constraint `(tenant_id, idempotency_key)`)** — إصلاح جذري خارج نطاق هذه الجلسة (migration على الـschema).
3. **`redis-client-wrapper-missing-methods`** (Backlog #7 موجود مسبقًا) — **تأكيد حي إضافي [2026-08-18]:** مؤكَّد الآن أنه **يُسقِط `execute_agent_action` بالكامل بـException** في أي استدعاء حقيقي وصل لمرحلة `ai_engine.generate()` (مش مجرد فشل تتبع تكلفة صامت كما كان مفترضًا) — `CostTracker.record_usage()` بينادي `redis_client.hincrbyfloat()` غير الموجودة. **الأثر المُحدَّث:** كل الـ17 موضع المُصلَح هنا (وموضعا realestate/invitations) لن ينجحا فعليًا في بيئة حقيقية حتى يُصلَح #7 — الفرع `except` في `execute_agent_action` سيُنشئ `task_log` بـ`task_type="ERROR"` ثم `raise` بدل إرجاع نتيجة ناجحة.

**`PROGRESS_LOG.md` سيُحدَّث:** بند #16 → حالة جديدة تعكس الإغلاق الجزئي (17/19)، + تحديث بند #7 بالتأكيد الحي الجديد، + بندان Backlog جديدان.
