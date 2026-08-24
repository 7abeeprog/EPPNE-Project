# جلسة فحص IDOR/أمان عميق في `commerce` — خامس قطاع في سويپ الأمان

**بدأ التسجيل:** 2026-08-24
**الحالة:** ✅ **الإصلاحات الثلاثة مُطبَّقة ومؤكَّدة حيًا بالكامل. لم يُنفَّذ commit بعد — بانتظار مراجعتك للـ`git diff` أدناه (§8) وموافقتك الصريحة.**

**نطاق الجلسة:** `eppne-backend/app/domains/commerce/{router,service,repository,schemas,models}.py` بالكامل (12 endpoint).

**الملفات المرجعية المقروءة كاملة قبل البدء:**
- `.claude/reports/simpletenant-fix-session-log.md` (قسم `commerce` كاملًا — 11/12 endpoint مُصلَحين ومؤكَّدين حيًا بتاريخ 2026-08-13، `visa_webhook` مؤجَّل رسميًا كبند أمني منفصل)
- `.claude/reports/finance-idor-security-fix-session-log.md` (ثغرة `release_commissions` — `sender_id=1` هاردكودد على حساب `p_system_treasury` الحقيقي، **موثَّقة ومؤجَّلة بقرار صريح، لم تُلمس في هذه الجلسة**)
- `.claude/reports/command-idor-fix-session-log.md` + `saas-idor-fix-session-log.md` (درس منهجي: عزل التينانت غالبًا سليم بالفعل، والمشكلة الحقيقية المتبقية RBAC/ownership/silent-write)
- `.claude/plans/critical-finding-xtenant-systemic.md` (إشارتان لـ`commerce`: صف #7 حساب النظام الهاردكودد، وصف `create_store`/`create_product` "ثغرة عزل tenant مختلفة الشكل" — تحقَّق منها بالقراءة الحية، راجع القسم 1)
- `app/domains/commerce/{router,service,repository,schemas,models}.py` (كاملة، 221+603+401+212+313 سطر)

---

## 1) مطابقة المرجع الميكانيكي — `commerce` لسه في نفس حالة 2026-08-13 بالحرف

قراءة `router.py` الحالي (221 سطر) تؤكد: **11/12 endpoint بالفعل `tenant_id = cast(int, current_user.tenant_id)`** (مُصلَحين من جلسة `simpletenant-fix`). الاستثناء الوحيد المتبقي **كما هو موثَّق**:

- `visa_webhook` (`router.py:193-206`): لسه `tenant_id: int = Depends(get_current_tenant)`، بلا `current_user` إطلاقًا. **مؤجَّل رسميًا** من 2026-08-13 كبند أمني منفصل (سببان صريحان: (1) هل فحص `signature` حقيقي؟ (2) هل `order_id` قابل للتخمين؟) — **لم يُعاد فتحه أو اختباره حيًا في هذه الجلسة**، لكن القراءة الحية اليوم تؤكد إضافة معلومة لم تكن موثَّقة صراحة من قبل: **`signature` بارامتر مُستقبَل في `service.handle_visa_webhook()` لكنه غير مُستخدَم إطلاقًا في جسم الدالة** (`service.py:399-428`) — أي **لا يوجد أي تحقق HMAC/توقيع فعلي في الكود الحالي بتاتًا**، ليس فقط "غير مؤكَّد"، بل **مؤكَّد غيابه الكامل بالقراءة المباشرة**. هذا يرفع خطورة البند المؤجَّل، لا يغيّر قرار التأجيل نفسه.

**ملاحظة `critical-finding-xtenant-systemic.md` (صف `create_store`/`create_product`):** القراءة الحية اليوم تؤكد إن الملاحظة ("ثغرة عزل tenant مختلفة الشكل، مش admin-gated") **لم تعد قائمة بنفس الصياغة** — كلا الـendpoint حاليًا `tenant_id = cast(int, current_user.tenant_id)` (من إصلاح 2026-08-13)، **لكن اكتُشف اليوم شيء أعمق وأخطر بكثير في نفس منطقة `checkout`/المنتجات — راجع القسم 3.1، وهو على الأرجح الجوهر الحقيقي وراء تلك الملاحظة القديمة الغامضة.**

**فحص إزالة `require_sector`:** `main.py:274` — `commerce_router` مسجَّل بـ`prefix="/api"` بلا أي `Depends` إضافي على مستوى التسجيل (نفس نمط كل الدومينات الأخرى). كل الـ12 endpoint عندها `current_user` صريح ما عدا `visa_webhook` (بالتصميم، webhook خارجي). **`commerce` غير متأثر بإزالة `require_sector`.**

---

## 2) جدول الـ12 endpoint — المستوى، مصدر tenant_id، فلتر الملكية

| # | الدالة | السطور | `current_user` | مصدر `tenant_id` | فلتر ملكية إضافي؟ | التصنيف الأولي |
|---|---|---|---|---|---|---|
| 1 | `create_store` | 22-31 | active_user | `current_user.tenant_id` ✅ | N/A (متجر واحد/تينانت) | 🟢 آمن |
| 2 | `create_product` | 38-50 | active_user | ✅ | N/A (إنشاء) | 🟢 آمن (تينانت-يًا) |
| 3 | `list_products` | 53-68 | active_user | ✅ | N/A (كتالوج المتجر) | 🟢 آمن |
| 4 | `checkout` | 75-87 | active_user | ✅ | ❌❌ **لا يوجد فحص إن `variant_id`/`product_id` تبع نفس المتجر/التينانت** | 🔴🔴🔴 **مؤكَّد حيًا — أخطر اكتشاف في الجلسة، راجع 3.1** |
| 5 | `get_my_orders` | 90-104 | active_user | ✅ | ✅ `customer_id` مفلتر في الـrepo | 🟢 آمن |
| 6 | `set_affiliate_sponsor` | 111-123 | active_user | ✅ | ❌ **لا يوجد فحص وجود/تينانت لـ`sponsor_id`** | 🔴🔴 **مؤكَّد حيًا — جذر سلسلة الاستغلال، راجع 3.2** |
| 7 | `get_my_commissions` | 126-140 | active_user | ✅ | ✅ (لكن يعرض عمولات مسربة من تينانت آخر، راجع 3.2) | 🟢 آمن-يًا محليًا، لكنه القناة اللي بيظهر بيها الأثر |
| 8 | `release_my_commissions` | 143-151 | active_user | ✅ | ✅ ownership سليم — **لكن الدالة نفسها تحتوي `sender_id=1` الهاردكودد المؤجَّل، لم يُستدعَ إطلاقًا في هذه الجلسة** | ⚪ خارج النطاق تمامًا (مؤجَّل بقرار سابق) |
| 9 | `create_payment_request` | 158-173 | active_user | ✅ | ✅ `order.customer_id != user_id` مُطبَّق صح | 🟡 محجوب ببج pre-existing (duplicate-kwarg)، لم يُختبَر حيًا (راجع 4.1) |
| 10 | `confirm_agent_payment` | 176-190 | active_user | ✅ | N/A بالتصميم (agent_code فعلي) | 🟢 آمن (تصميم متعمَّد) |
| 11 | `visa_webhook` | 193-206 | **بلا current_user** | `Depends(get_current_tenant)` (لسه القديم) | N/A | 🔴 مؤجَّل رسميًا (بند أمني منفصل موجود من 2026-08-13) |
| 12 | `get_payment_status` | 209-221 | active_user | ✅ | ❌ **فحص ملكية موجود بالكود لكنه `pass` — dead code حرفيًا** | 🟡🟡 **مؤكَّد حيًا — راجع 3.3** |

---

## 3) الاكتشافات الحية الثلاثة — بالترتيب من الأخطر

### 3.1 🔴🔴🔴 `checkout` — IDOR عبر-تينانت حقيقي، كتابة فعلية على مخزون تينانت آخر (مؤكَّد حيًا بالكامل)

**السبب الجذري (`service.py:135-166`):** دالة `checkout` تتحقق من ملكية `store_id` للتينانت الحالي (`repo.get_store(store_id, self.tenant_id)`)، **لكنها لا تتحقق إطلاقًا من إن `variant_id` المُرسَل من العميل في `items[]` يخص هذا المتجر أو حتى هذا التينانت**:

```python
variant = await self.repo.get_variant_for_update(cart_item.variant_id)   # ← بلا tenant_id، بلا store_id
...
product = await self.repo.get_product(cast(int, variant.product_id))     # ← بلا tenant_id
...
variant.stock_quantity = cast(int, variant.stock_quantity) - cart_item.quantity   # ← كتابة فعلية!
```

`repository.get_variant_for_update()` (`repository.py:74-78`) و`get_product()` (`repository.py:66-68`) **الاثنان بلا أي فلتر `tenant_id`/`store_id` في الاستعلام** — أي `variant_id` رقمي صالح في قاعدة البيانات كلها (بغض النظر عن التينانت) يمر.

**دليل حي مباشر (بيانات throwaway، `p_commerce2_*`، منضَّفة بالكامل بعد الاختبار):**

1. تينانت1: مستخدم `p_commerce2_a` (id=937) — متجره الموجود مسبقًا (`store_profiles id=4`)، منتج جديد `P_COMMERCE2_PRODUCT_A` (id=2) بمتغيّر واحد (`variant id=2`, `stock_quantity=5`) — أُنشئا عبر الـAPI الحقيقي، ثم `is_published` عُدِّل لـ`true` عبر SQL (المتجر بلا endpoint نشر أصلًا — بج pre-existing منفصل تمامًا، راجع القسم 4.3).
2. تينانت16 (`TEST_TENANT_B`، مُعاد استخدامها من جلسات سابقة): مستخدم `p_commerce2_b` (id=938) أنشأ **متجره الخاص** (`store_profiles id=5`) عبر الـAPI.
3. **الهجوم:** `p_commerce2_b` (تينانت16) نادى `POST /commerce/checkout` بـ`store_id=5` (متجره الشرعي الخاص) و`items=[{"variant_id": 2, "quantity": 1}]` (المتغيّر ده بتاع منتج **تينانت1**، لا علاقة له بمتجر تينانت16 إطلاقًا) و`settlement_type="CASH_ON_DELIVERY"` (لتفادي أي لمس لـ`finance`/محافظ حقيقية).

**النتيجة:** `201 Created`.
```json
{"id":5,"store_id":5,"customer_id":938,"total_amount_mrusdt":"10.00000000","status":"PENDING_PAYMENT","settlement_type":"CASH_ON_DELIVERY", ...}
```

**تحقق DB مستقل (SELECT فقط):**
```sql
orders:        id=5, store_id=5, tenant_id=16, customer_id=938, status=PENDING_PAYMENT
order_items:   order_id=5, product_id=2, variant_id=2, quantity=1   -- منتج/متغيّر تينانت1 بالحرف
product_variants: id=2 → stock_quantity = 4   -- كانت 5 قبل الهجوم، نقصت فعليًا بسبب طلب تينانت16
```

**الأثر:** طلب حقيقي (`order`) اتسجَّل تحت تينانت16 (متجر ومستخدم تينانت16)، **لكن مرجعًا لمنتج/متغيّر يخص تينانت1 بالكامل، وبكتابة فعلية أنقصت مخزون تينانت1 الحقيقي** — بلا أي علاقة شراء أو دفع حقيقي بين التينانتين. أي مستخدم في أي تينانت يقدر (بمجرد تخمين/تعداد `variant_id` تسلسلي) يستنزف مخزون أي تينانت تاني في المنصة كلها عبر `CASH_ON_DELIVERY` (بلا أي مساس بمحفظة حتى)، أو حتى عبر `WALLET_DEDUCTION` (لو دفع، الفلوس بتروح لـ`store.owner_email` بتاع **متجره هو نفسه** (تينانت16)، مش لصاحب المنتج الحقيقي (تينانت1) — يعني ممكن كمان "شراء" منتج تينانت تاني بينما الفلوس بتتحصل لتينانت المهاجم نفسه لو هو صاحب المتجر). **هذا أخطر اكتشاف في الجلسة — كتابة فعلية عبر-تينانت على بيانات مخزون حقيقية، مؤكَّد DB-level، بلا أي تزوير هيدر مطلوب (الاستغلال بالكامل عبر body المُرسَل من العميل).**

---

### 3.2 🔴🔴 `set_affiliate_sponsor` → `checkout(affiliate_code=...)` → `get_my_commissions` — سلسلة استغلال 3 خطوات، تسريب مالي عبر-تينانت (مؤكَّد حيًا بالكامل، صفر لمس لـ`release_commissions`)

**السبب الجذري (`service.py:231-249`، `register_affiliate`):**
```python
sponsor_id = int(sponsor_code) if sponsor_code.isdigit() else None
if not sponsor_id or sponsor_id == user_id:
    raise PermissionDeniedError("كود الداعي غير صالح")
...
sponsor_tree = await self.repo.get_affiliate_tree(sponsor_id, self.tenant_id)   # فقط للتحقق من وجود شجرة سابقة (لحساب depth)
depth = sponsor_tree.network_depth + 1 if sponsor_tree else 1
return await self.repo.create_affiliate_tree(user_id=user_id, sponsor_id=sponsor_id, network_depth=depth)
```
**لا يوجد أي تحقق إن `sponsor_id` مستخدم حقيقي موجود، ولا إنه يخص نفس التينانت** — الفحص الوحيد (`get_affiliate_tree`) بيرجّع `None` بهدوء لو الشجرة مش موجودة (بدل رمي خطأ)، فبيتفسَّر خطأً كـ"سبونسر جديد بعمق 1" بدل "سبونسر غير صالح/خارج التينانت". جدول `affiliate_trees` نفسه **بلا عمود `tenant_id` من الأساس** (تأكَّد من `models.py:191-204`).

**دليل حي مباشر (3 خطوات متتالية، صفر تزوير هيدر، صفر لمس لـ`finance`/`release_commissions`):**

**الخطوة 1 — حقن سبونسر عبر-تينانت (بلا أي تحقق):**
`p_commerce2_c2` (id=940، تينانت1) نادى `POST /commerce/affiliate/link?sponsor_code=938` (**938 = `p_commerce2_b`، مستخدم حقيقي لكن في تينانت16**، لا علاقة له بتينانت1 إطلاقًا) →
```json
{"user_id":940,"sponsor_id":938,"network_depth":1}   -- 200 OK
```
قُبِل بلا أي اعتراض — `affiliate_trees` فيها الآن صف `(user_id=940, sponsor_id=938)` رغم إن 938 تينانت مختلف تمامًا.

**الخطوة 2 — تفعيل السلسلة عبر شراء عادي (زُرعت `affiliate_configs` لتينانت1 عبر SQL — صف إعدادات فقط، صفر مساس بأي رصيد/محفظة، لا يوجد endpoint لإدارته أصلًا):**
`p_commerce2_c1` (id=939، تينانت1) نادى `POST /commerce/checkout` بـ`store_id=4` (متجره الشرعي)، `variant_id=2` (منتجه هو نفسه)، `settlement_type="CASH_ON_DELIVERY"`، **`affiliate_code="940"`** (كود الإحالة بتاع `p_commerce2_c2`) → `201`، `order id=7`، `tenant_id=1`.

**آلية `distribute_commissions` (`service.py:251-292`) بتحسب السلسلة بدءًا من صاحب الكود (940) صعودًا لسبونسره (938):**
```
get_sponsor_chain(940, tenant_id=1):
  current = get_affiliate_tree(940, tenant=1)  → موجودة (940 فعلاً تينانت1) → chain=[938]
  current = get_affiliate_tree(938, tenant=1)  → 938 تينانت16 فعليًا، الـjoin بيرفضها → توقف
→ chain = [938]   -- السبونسر العابر للتينانت وصل لأول مستوى فعليًا
```

**تحقق DB مستقل فوري بعد الطلب:**
```sql
commission_records: id=2, beneficiary_id=938, order_id=7 (تينانت1), level_earned=1, amount=1.0 MR_USDT, status=PENDING
users: id=938 → tenant_id=16   -- المستفيد فعليًا في تينانت مختلف تمامًا عن مصدر الطلب
```

**الخطوة 3 — إثبات الأثر الفعلي (المستفيد شافها بنفسه، عبر توكنه الحقيقي، بلا أي تزوير):**
`p_commerce2_b` (id=938، توكن تينانت16 الحقيقي) نادى `GET /commerce/affiliate/commissions` →
```json
[{"id":2,"beneficiary_id":938,"order_id":7,"level_earned":1,"amount":1.0,"currency":"MR_USDT","status":"PENDING"}]   -- 200 OK
```

**الخلاصة الحاسمة:** مستخدم في تينانت16 اكتسب **مطالبة مالية حقيقية (عمولة PENDING) مصدرها طلب شراء حصل بالكامل داخل تينانت1**، بلا أي علاقة تجارية أو صلاحية مشتركة بين التينانتين — فقط بسبب غياب تحقق ملكية/تينانت على `sponsor_id` وقت التسجيل. **لم يُستدعَ `release_commissions` إطلاقًا** (المؤجَّلة بقرار صريح بسبب `sender_id=1`) — الإثبات توقف عند تأكيد وجود المطالبة المالية العابرة للتينانت وظهورها لصاحبها الحقيقي عبر الـAPI، بلا أي محاولة لتحويل فعلي للأموال.

---

### 3.3 🟡🟡 `get_payment_status` — فحص ملكية موجود بالكود لكنه `pass` حرفيًا (dead code، مؤكَّد حيًا)

**السبب الجذري (`service.py:430-436`):**
```python
async def get_payment_status(self, order_id: int, user_id: int) -> dict:
    order = await self.repo.get_order(order_id, self.tenant_id)   # فلتر تينانت سليم
    if not order:
        raise NotFoundError("الطلب غير موجود")

    if order.customer_id != user_id:
        pass   # ← لا يوجد أي raise هنا — الفحص موجود شكليًا بس معطَّل فعليًا
    ...
```
**بعكس `create_payment_request` في نفس الملف (`service.py:331-332`)** اللي بتعمل نفس الفحص بالظبط لكن بترمي `PermissionDeniedError` فعليًا — التناقض بين الاثنين يرجّح إنه بج (نسيان `raise`)، مش تصميم مقصود.

**دليل حي مباشر (نفس التينانت، مستخدمين مختلفين، صفر تزوير هيدر):**

| الاختبار | النتيجة |
|---|---|
| `p_commerce2_c1` (id=939) ينشئ طلب (`order id=6`, تينانت1) | `201` |
| **`p_commerce2_c2` (id=940، مستخدم مختلف تمامًا، نفس التينانت1) يقرأ `GET /commerce/payment/status/6`** | **`200`** مع `{"order_id":6,"order_status":"PENDING_PAYMENT","payment_requests":{}}` — **بلا أي علاقة ملكية بالطلب** |
| نفس الطلب بلا أي توكن (sanity) | `401 "Not authenticated"` (يفرّق عن نجاح الوصول للـbusiness logic بعد المصادقة) |
| `p_commerce2_c1` (تينانت1) يحاول قراءة طلب تينانت16 (`order id=5`) — عزل التينانت نفسه | `404 "الطلب غير موجود"` ✅ **عزل التينانت سليم، القضية فقط ملكية المستخدم داخل نفس التينانت** |

**الخلاصة:** أي عضو في نفس التينانت يقدر يقرأ حالة دفع/طلب أي عضو تاني في نفس التينانت (تسريب معلومات: حالة الطلب + حالات طلبات الدفع المرتبطة) — **عزل التينانت نفسه سليم 100%، المشكلة حصرًا غياب فحص ملكية المستخدم داخل نفس التينانت**، نفس فئة `command.acknowledge_alert`/`delete_report` الموثَّقة سابقًا (فحص ملكية غائب على عملية "قراءة حساسة" بدل "كتابة/حذف").

---

## 4) باجات جانبية pre-existing (موثَّقة فقط، صفر إصلاح، صفر علاقة بـIDOR)

### 4.1 `create_payment_request` — نفس فئة duplicate-kwarg الموثَّقة سابقًا (4 مرات في جلسات تانية)
`service.py:355` — `self.repo.create_payment_request(self.tenant_id, **pr_data)` و`pr_data` (المبني في نفس الدالة، سطر 342) **فيه مفتاح `"tenant_id"` بالفعل** → `TypeError: got multiple values for keyword argument 'tenant_id'`، فوري، لأي `payment_method`. **يمنع `create_payment_request` بالكامل عبر الـAPI** — لم يُختبَر حيًا في هذه الجلسة (نفس النمط المؤكَّد سابقًا في `academy.create_course`، `sovereign_entities.create_entity`، وهذا الملف نفسه من قبل — القراءة الثابتة كافية، صفر داعٍ لإعادة الإثبات الحي).

### 4.2 `handle_visa_webhook` — غياب تحقق `signature` مؤكَّد بالقراءة (تفصيل إضافي على البند المؤجَّل سابقًا)
راجع القسم 1 — `signature` بارامتر مُستقبَل لكن غير مُستخدَم إطلاقًا في `service.py:399-428`. **لم يُعَد فتح هذا البند للتنفيذ — لسه مؤجَّل رسميًا**، لكن يستاهل تمييزه في أي جلسة تصميم لاحقة: المشكلة أعمق من "مصدر tenant_id" — **لا يوجد تحقق أمني (HMAC) على الإطلاق حاليًا في الكود**.

### 4.3 `products.is_published` بلا أي endpoint لتغييره
`ProductCreate` schema بلا حقل `is_published`، والموديل الافتراضي `False` (`models.py:74`) — **لا يوجد أي `PUT /commerce/products/{id}` في الراوتر بالكامل**، فمنتج مُنشأ عبر الـAPI **لا يمكن نشره أبدًا عبر أي مسار API موجود حاليًا**، ما يمنع `checkout` بالكامل من العمل على أي منتج حقيقي (اضطُررت لتعديل `is_published` عبر SQL خام لإجراء اختبار 3.1). **فجوة وظيفية pre-existing، خارج نطاق IDOR تمامًا.**

### 4.4 `ProductResponse` لا يُرجع `variants` رغم تسجيلها الصحيح في DB
نفس الملاحظة الموثَّقة في 2026-08-13 — serialization فقط، pre-existing، غير مُختبَرة بعمق هنا.

---

## 5) بيانات throwaway — تنظيف كامل ومؤكَّد مستقل

**كل شيء زُرع في هذه الجلسة (بادئة `p_commerce2_*`) اتنضَّف بالكامل بعد الاختبار:**
- `users`: 937, 938, 939, 940
- `store_profiles`: 5 (تينانت16 — جديد بالكامل من هذه الجلسة)
- `products`: 2 / `product_variants`: 2
- `orders`: 5, 6, 7 / `order_items` المرتبطة
- `commission_records`: 2
- `affiliate_trees`: (user_id=940)
- `affiliate_configs`: تينانت1 (صف إعدادات زُرع للاختبار، صفر مساس بأي رصيد)
- `commerce_audit_logs`: 7, 8, 9

**`store_profiles id=4` (تينانت1، "Store_1") لم يُلمس/يُحذف** — كان موجودًا من جلسات سابقة، أُعيد استخدامه بس (نفس نمط `academy`/`saas` السابق).

**تحقق مستقل نهائي (`SELECT COUNT`/معادل) بعد التنظيف: صفر في كل الجداول أعلاه.** السيرفر التجريبي (uvicorn) **أُوقف** (`Stop-Process`)، تأكيد إضافي: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → صفر نتيجة.

---

## 6) الخلاصة والتصنيف النهائي — بانتظار قرارك

**لا يوجد IDOR في "مصدر tenant_id" نفسه (فئة `academy`/`sovereign_entities` الكلاسيكية)** — `commerce` فعلًا في حالتها النهائية من 2026-08-13. **لكن اكتُشف واتأكَّد حيًا 3 أشياء أخطر وأعمق:**

| # | الاكتشاف | الخطورة | النوع | يحتاج قرار |
|---|---|---|---|---|
| 1 | `checkout` — `variant_id`/`product_id` بلا فلتر تينانت/متجر إطلاقًا | 🔴🔴🔴 **الأعلى في الجلسة** | IDOR عبر-تينانت، كتابة فعلية (مخزون) | نعم — إصلاح مقترَح تحت |
| 2 | `set_affiliate_sponsor` → سلسلة عمولات عبر-تينانت | 🔴🔴 | IDOR عبر-تينانت، تسريب مالي (مطالبة PENDING) | نعم — إصلاح مقترَح تحت |
| 3 | `get_payment_status` — فحص ملكية `pass` بدل `raise` | 🟡🟡 | IDOR داخل-تينانت (تسريب معلومات) | نعم — إصلاح سطر واحد بسيط |
| ⚪ | `release_commissions` (`sender_id=1`) | — | مؤجَّل بقرار سابق | **لا — لم يُلمس، مرجع فقط كما طُلب** |
| ⚪ | `visa_webhook` (بلا `current_user` + بلا تحقق signature) | — | مؤجَّل رسميًا كبند أمني منفصل | لا — خارج نطاق هذه الجلسة |
| ⚪ | `create_payment_request` duplicate-kwarg، `is_published` بلا endpoint، serialization variants | — | pre-existing، غير أمني | Backlog فقط |

### الحلول المقترَحة (معروضة للمراجعة فقط — **صفر تنفيذ حتى الآن**)

**1) `checkout` (الأولوية القصوى):** إضافة فحص إن `variant.product_id`'s `product.store_id == checkout_data.store_id` (وبالتبعية نفس التينانت، بما إن `store` أصلًا مفلترة بالتينانت) — إما عبر `JOIN` واحد في استعلام جديد (`get_variant_for_checkout(variant_id, store_id)`)، أو فحص إضافي بعد الجلب الحالي قبل أي كتابة على `stock_quantity`. يحتاج تعديل `repository.py` (استعلام جديد) و`service.py` (استبدال `get_variant_for_update`/`get_product` المنفصلين بالفحص الموحَّد).

**2) `set_affiliate_sponsor`:** إضافة تحقق إن `sponsor_id` يخص **مستخدمًا حقيقيًا موجودًا في نفس التينانت** قبل إنشاء `AffiliateTree` — عبر `UserRepository.get_by_id(sponsor_id, self.tenant_id)` (نفس النمط المستخدَم بالفعل للمستخدم الحالي في نفس الدالة، سطر 238) بدل الاكتفاء بفحص وجود شجرة سابقة فقط.

**3) `get_payment_status`:** استبدال `pass` بـ`raise PermissionDeniedError("ليس لديك صلاحية لهذا الطلب")` — نفس الرسالة والنمط المستخدَم بالفعل في `create_payment_request` بنفس الملف. **إصلاح سطر واحد، صفر تغيير في مستوى `current_user`.**

**سؤال تصميمي مفتوح (لا اقتراح إصلاح بلا توجيهك):** هل عمولة `commission_records id=2` (لو كانت بيانات حقيقية لا throwaway) يُفترض تُحذف/تُعلَّق عند اكتشاف زرعها بسبونسر غير صالح؟ خارج نطاق هذه الجلسة (بيانات throwaway هنا فقط)، لكن يستاهل سؤال منتجي منفصل: هل يحتاج الإصلاح رقم 2 backfill/تدقيق لبيانات `affiliate_trees`/`commission_records` الحالية في الإنتاج (لو موجودة) بعد التطبيق؟

---

## 7) بانتظار توجيهك

**صفر تنفيذ كود. صفر كتابة في `PROGRESS_LOG.md` بعد.** الجرد (12/12 endpoint) + التحقق الحي (3 اكتشافات، تسلسل استغلال كامل لاثنين منهم) **مكتمل بالكامل**، البيانات مُنظَّفة ومؤكَّدة، السيرفر متوقف.

**القرار المطلوب:** ~~تم — راجع §8/§9 تحت.~~

---

## 8) قرار المستخدم [2026-08-24] — موافقة على الثلاثة بالترتيب + تأجيل سؤال الـbackfill

- **موافقة صريحة على تنفيذ الثلاثة بالترتيب:** `checkout` أولًا، `set_affiliate_sponsor` ثانيًا، `get_payment_status` أخيرًا.
- **س2 (الـbackfill):** مؤجَّل — التطبيق مش شغال بمستخدمين حقيقيين حاليًا، فمفيش بيانات إنتاج تحتاج تدقيق الآن. **يُوثَّق كبند "يُراجَع وقت الإطلاق الفعلي" فقط** (راجع §10 تحت — بند Backlog مستقبلي، مش عاجل).
- **س3 مؤكَّد:** `release_commissions` و`visa_webhook` بلا أي لمس — مؤجَّلين كما هما.
- **س4:** باجات pre-existing (§4) → Backlog فقط.
- **توجيه إضافي:** تحقق حي بعد كل إصلاح (نفس سيناريو الاستغلال بالضبط)، عرض `git status` + `git diff --stat` قبل أي commit.

---

## 9) التنفيذ — الثلاثة مُطبَّقين، مؤكَّدين حيًا بالكامل

### 9.1 الديف المُطبَّق (ملف واحد فقط: `service.py`، +8/-1 سطر)

**إصلاح 1 — `checkout` (`service.py:141-148`):**
```diff
                 product = await self.repo.get_product(cast(int, variant.product_id))
                 if not product or not cast(bool, product.is_published):
                     raise NotFoundError(f"المنتج {variant.product_id} غير منشور")

+                if cast(int, product.store_id) != cast(int, store.id):
+                    raise NotFoundError(f"المتغير {cart_item.variant_id} غير موجود")
+
                 if cast(int, variant.stock_quantity) < cart_item.quantity:
```
رسالة الخطأ **مطابقة حرفيًا** لرسالة "المتغير غير موجود" الموجودة فوقها (سطر 139) — تعمُّدًا لتفادي تسريب معلومة "المتغير موجود لكن في متجر آخر" مقابل "غير موجود إطلاقًا".

**إصلاح 2 — `register_affiliate`/`set_affiliate_sponsor` (`service.py:238-247`):**
```diff
         user = await user_repo.get_by_id(user_id, self.tenant_id)
         if not user:
             raise NotFoundError("المستخدم غير موجود")

+        sponsor = await user_repo.get_by_id(sponsor_id, self.tenant_id)
+        if not sponsor:
+            raise PermissionDeniedError("كود الداعي غير صالح")
+
         sponsor_tree = await self.repo.get_affiliate_tree(sponsor_id, self.tenant_id)
```
نفس رسالة "كود الداعي غير صالح" الموجودة فوق (سطر 237) — تعمُّدًا لتوحيد رسالة الرفض بغض النظر عن سبب الرفض (كود غير رقمي، سبونسر=نفسه، أو سبونسر غير موجود/خارج التينانت).

**إصلاح 3 — `get_payment_status` (`service.py:442-443`):**
```diff
         if order.customer_id != user_id:
-            pass
+            raise PermissionDeniedError("ليس لديك صلاحية لهذا الطلب")
```
نفس الرسالة ونفس نوع الاستثناء المستخدَمين بالفعل في `create_payment_request` بنفس الملف (سطر 332).

`python -m py_compile app/domains/commerce/service.py` → `exit code 0`. **صفر import جديد** (`PermissionDeniedError`/`UserRepository` مستوردين بالفعل).

### 9.2 إعادة تشغيل uvicorn

تأكيد فعلي إن البورت 8000 فاضي قبل التشغيل، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، لوج إقلاع نظيف تمامًا (`Application startup complete`، صفر `Traceback` — نفس تحذيرات dev/فهرسة pre-existing المعتادة بس).

### 9.3 التحقق الحي بعد كل إصلاح — بيانات throwaway جديدة (بادئة `p_commerce3_*`، منفصلة تمامًا عن دفعة الاكتشاف الأولى `p_commerce2_*`)

**الإعداد:** 4 مستخدمين جدد (`p_commerce3_a`=941 تينانت1، `p_commerce3_b`=942→تينانت16، `p_commerce3_c1`=943 تينانت1، `p_commerce3_c2`=944 تينانت1) + متجر تينانت16 جديد (`store_profiles id=6`) + منتج/متغيّر تينانت1 جديدين (`products id=3`/`product_variants id=3`, `stock_quantity=5`، نُشر عبر SQL لنفس سبب pre-existing الموثَّق في §4.3).

| # | الاختبار | قبل الإصلاح (مرجعي، §3) | بعد الإصلاح | الحكم |
|---|---|---|---|---|
| 1 | **`checkout`**: تينانت16 يحاول شراء `variant_id=3` (تينانت1) عبر متجره الخاص (`store_id=6`) | `201`، مخزون تينانت1 نقص فعليًا | **`404 "المتغير 3 غير موجود"`** — تحقق DB مستقل: `stock_quantity` لسه `5` (لم يتغيّر)، **صفر order** لـ`store_id=6` | ✅ **الهجوم مرفوض بالكامل، صفر أثر جانبي** |
| 1s | Sanity: تينانت1 يشتري من متجره الخاص (`store_id=4`, نفس `variant_id=3`) | — | `201`، `order id=8` نجح طبيعيًا | ✅ **المسار الشرعي سليم 100%** |
| 2 | **`set_affiliate_sponsor`**: `p_commerce3_c2` (تينانت1) يحاول `sponsor_code=942` (تينانت16) | `200`، صف `affiliate_trees` اتكتب | **`403 "كود الداعي غير صالح"`** — تحقق DB مستقل: `count(affiliate_trees WHERE user_id=944) = 0` | ✅ **الهجوم مرفوض، صفر كتابة** |
| 2s | Sanity: نفس المستخدم `sponsor_code=941` (تينانت1، مستخدم حقيقي في نفس التينانت) | — | `200`، الشجرة اتكتبت طبيعيًا | ✅ **المسار الشرعي سليم 100%** |
| 3 | **`get_payment_status`**: `p_commerce3_c2` يقرأ طلب `p_commerce3_c1` (`order id=9`، نفس التينانت، مستخدم مختلف) | `200` مع بيانات الطلب | **`403 "ليس لديك صلاحية لهذا الطلب"`** | ✅ **الهجوم مرفوض** |
| 3s | Sanity: `p_commerce3_c1` (المالك الحقيقي) يقرأ نفس الطلب | — | `200` مع بيانات صحيحة | ✅ **المسار الشرعي سليم 100%** |

**حاسم:** الثلاثة هجمات المستخدَمة أصلًا لإثبات الثغرات في §3 **مرفوضة الآن بالكامل**، وكل مسار شرعي مقابل **سليم 100% بلا أي تأثير جانبي على الوظائف العادية**.

### 9.4 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

```sql
DELETE FROM commerce_audit_logs WHERE id IN (12,13);
DELETE FROM order_items WHERE order_id IN (8,9);
DELETE FROM orders WHERE id IN (8,9);
DELETE FROM affiliate_trees WHERE user_id=944;
DELETE FROM product_variants WHERE id=3;
DELETE FROM products WHERE id=3;
DELETE FROM store_profiles WHERE id=6;
DELETE FROM users WHERE id IN (941,942,943,944);
```
تحقق `SELECT COUNT` مستقل بعد الحذف: **صفر في كل الجداول السبعة.** (بيانات الاكتشاف الأولى `p_commerce2_*` كانت اتنضَّفت بالفعل قبل التنفيذ، راجع §5). السيرفر التجريبي أُوقف (`Stop-Process`)، تأكيد إضافي: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → صفر نتيجة.

---

## 10) بند Backlog جديد — مؤجَّل لوقت الإطلاق الفعلي (بطلب المستخدم، س2)

**العنوان المقترَح:** `commerce-affiliate-backfill-review-at-launch` — بعد إصلاح `set_affiliate_sponsor` (منع سبونسرات عبر-تينانت/وهمية من الآن فصاعدًا)، **لو كان فيه بيانات إنتاج حقيقية وقت الإطلاق الفعلي للتطبيق**، يحتاج فحص `affiliate_trees`/`commission_records` الموجودة وقتها لتدقيق أي صفوف قديمة (قبل هذا الإصلاح) بسبونسر غير صالح/عبر-تينانت اتسربت قبل الإصلاح. **غير عاجل الآن — التطبيق حاليًا بلا مستخدمين حقيقيين، صفر بيانات إنتاج للتدقيق.** لم يُنشأ ملف backlog منفصل — مجرد سطر مرجعي هنا + إشارة في `PROGRESS_LOG.md` لو رغبت.

---

## 11) `git status` / `git diff --stat` — للمراجعة قبل أي commit

**الملف الوحيد الذي عدّلته هذه الجلسة:**
```
M eppne-backend/app/domains/commerce/service.py   | 9 ++++++++- (8 insertions, 1 deletion)
?? .claude/reports/commerce-idor-fix-session-log.md       (جديد، هذا الملف)
```

**باقي الملفات الظاهرة في `git status` (متعدّلة/untracked) من جلسات/أعمال سابقة غير متعلقة بهذه الجلسة إطلاقًا** — `security.py`, `main.py`, `agritech/router.py` (محذوف)، `health/service.py`, `invoicing/router.py`, `projects/service.py`, `tasks/affiliate.py`, `tasks/billing.py`, `tests/conftest.py`, ملفات `eppne-web/*` الكثيرة، وخطط/تقارير `.claude/` أخرى — **لم تُلمس، ولن تُضاف لأي commit من هذه الجلسة.**

**الحالة النهائية:** ✅ **الثلاثة إصلاحات مُطبَّقة، مؤكَّدة حيًا (هجوم مرفوض + مسار شرعي سليم لكل واحد)، بيانات throwaway منضَّفة بالكامل.** ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.
