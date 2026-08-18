# تقرير جلسة — `saas-control-service-missing-methods` (Backlog #9)

**بدأ التسجيل:** 2026-08-18
**نطاق الجلسة:** فحص/إصلاح `SaaSControlService.get_active_subscription` غير الموجودة (Backlog #9، `PROGRESS_LOG.md` جدول الـBacklog النشط بند #9، أرشيف ~3076/3260-3272).

**هذا التقرير مرجع مستقل بالكامل لهذه الجلسة — لا يُدمج مع أي تقرير سابق.**

---

## 0) قراءة المصادر المطلوبة قبل أي حركة — تم بالكامل

1. `PROGRESS_LOG.md` — بند #9 في جدول الـBacklog النشط (سطر 33): `🟢 مسموح البدء الآن — القيد السابق (بانتظار إغلاق #11a) اتشال [2026-08-18]`.
2. `PROGRESS_LOG_ARCHIVE_2026-08-18.md` — كل إشارات `get_active_subscription`/`SaaSControlService` (سطور 1027، 2228، 2469، 2756، 3260-3320، 3336-3338).
3. `.claude/reports/invitations-savepoint-leak-session-log.md` — بالكامل. الدرس الأساسي منها: كراش #9 (`AttributeError` على `get_active_subscription`) كان بيمنع `invitations.accept_invitation` من الوصول لمنطقها الخطير (يوزر بلا محفظة عبر `commit()`-جوه-`begin_nested()`) **بالصدفة، لا بتصميم آمن مقصود**. تلك الثغرة اتقفلت رسميًا [2026-08-18] (Backlog #11a)، والقيد على #9 اتشال بناءً عليها.

---

## 1) أين المتوقَّع وجود `get_active_subscription`، ولماذا غير موجودة

**`grep` شامل على `eppne-backend/` بالكامل (مش بس الملف اللي ظهر فيه الباج الأول):**

- **التعريف الفعلي الموجود:** `saas/repository.py:122` — `SaaSRepository.get_active_subscription(self, tenant_id, service_id)` (تاخد `service_id` كمان). مستخدمة داخليًا من `saas/service.py:102, 219` (عبر `self.repo.get_active_subscription(self.tenant_id, service_id)`).
- **الاستدعاء الناقص:** 8 دومينات بتنادي `saas_service.get_active_subscription(tenant_id)` **مباشرة على `SaaSControlService`** (الـservice، مش الـrepository)، **بمعامل واحد بس (`tenant_id`، بدون `service_id`)** — method بهذا التوقيع **غير موجودة إطلاقًا على `SaaSControlService`** (`saas/service.py`). أقرب البدائل الفعلية: `get_subscription`, `get_tenant_subscriptions`, `can_access_service` — لا شيء منها بنفس الاسم/التوقيع.

**السبب الأرجح (لا يوجد commit سابق يحذفها — لم تُكتب من الأساس):** كل الـ8 استدعاءات موجودة داخل نفس دالة helper بنفس الاسم `_check_saas_limits` في كل دومين (نمط مُكرَّر يدويًا 8 مرات عبر دومينات مختلفة)، وكلها بنفس التوقيع الخاطئ بالحرف (`get_active_subscription(tenant_id)` بمعامل واحد). هذا نمط "نسخ/لصق" لدالة `_check_saas_limits` عبر دومينات متعددة أثناء تطوير أولي، افترض واضع الكود وجود method بسيطة `get_active_subscription(tenant_id)` مباشرة على `SaaSControlService` (ربما تصميم أصلي مخطَّط له ولم يُنفَّذ، أو تعارض مع `SaaSRepository.get_active_subscription(tenant_id, service_id)` الموجودة فعلًا على الـ**repository** لا الـ**service**) — **لا يوجد دليل على حذف عرضي** (صفر إشارة في أي مكان أرشيف/كود لوجود سابق ثم إزالته).

---

## 2) جدول كل موضع نداء `get_active_subscription` على `SaaSControlService` (الاستدعاء الناقص)

| # | الدومين:السطر | داخل | مسار حرج (مالي/هوية) أم ثانوي؟ |
|---|---|---|---|
| 1 | `arbitration_syndicates/service.py:40` | `_check_saas_limits` (تُستدعى من `create_dispute:74`, `:181`, `:241`, `create_syndicate:290`, `join_syndicate:311`, `:402`, `:466`, `:479`, `:498`) | ثانوي بالنسبة لـ#9 نفسها (بوابة صلاحية فيتشر) — **لكن راجع القسم 4 لتفاصيل حرجة إضافية** |
| 2 | `realestate/service.py:62` | `_check_saas_limits` (تُستدعى من `buy_fractional_ownership:183`, `rent_unit:330`, وغيرها) | 🔴 **حرج — راجع القسم 4** |
| 3 | `manufacturing/service.py:44` | `_check_saas_limits` (12 موضع نداء عبر الملف) | ثانوي — تحقَّق من موضعين (`analyze_and_schedule_maintenance`)، `invoice_service.create_invoice` فيهم **خارج** أي `begin_nested()` |
| 4 | `logistics/service.py:49` | `_check_saas_limits` (6 مواضع نداء) | ثانوي — صفر استدعاء `invoicing`/`InvoicingService` في الملف كله |
| 5 | `invitations/service.py:43` | `_check_saas_limits` (9 مواضع نداء، منها `accept_invitation:275`) | ثانوي الآن — `accept_invitation` نفسها أُصلحت في #11a؛ باقي الاستدعاءات التسعة بوابات فيتشر `crm` عادية |
| 6 | `employment/service.py:72` | `_check_saas_limits` (4 مواضع نداء) | ثانوي — صفر استدعاء `invoicing`/`InvoicingService` في الملف |
| 7 | `digital_twin/service.py:39` | `_check_saas_limits` (4 مواضع نداء) | ثانوي — موضع الاكتشاف الأصلي لـ#9 (أرشيف 3260)، صفر `invoicing` في الملف |
| 8 | `insurance/service.py:44` | `_check_saas_limits` (3 مواضع نداء: `:165`, `:304`, `:407`) | 🔴 **حرج — راجع القسم 4** |

**ملاحظة تصنيف:** `saas/service.py:102, 219` و`social/repository.py:229/242` **ليست جزءًا من الباج** — الأولى استدعاء صحيح على `self.repo` (الـrepository الحقيقية بتوقيعها الصحيح)، والثانية method مختلفة تمامًا بالاسم فقط (`get_active_subscription_for_group`، خاصة بـ`social` group subscriptions، لا علاقة لها بـ`SaaSControlService`).

---

## 3) خيارات الإصلاح المحتملة (توثيق أولي فقط — صفر قرار/كود حتى الآن)

كل الاستدعاءات الثمانية بنفس التوقيع بالحرف: `await saas_service.get_active_subscription(tenant_id)` حيث `saas_service = SaaSControlService(self.db, tenant_id)` (الـ`tenant_id` بالفعل جوه الـconstructor). الحل الأقرب سطحيًا: إضافة method `get_active_subscription(self, tenant_id: int)` على `SaaSControlService` نفسها (wrapper بسيطة حول `self.repo.get_active_subscription(...)` — لكن الـrepository method بتاخد `service_id` كمان، فمحتاجة قرار: هل فيه "اشتراك نشط واحد لكل tenant" بمنطق مختلف، ولا لازم تمرير `service_id` افتراضي/`None`؟). **هذا تفصيل تصميمي يحتاج فحص إضافي لموديل `saas` قبل أي اقتراح ديف فعلي — غير مطروح للتنفيذ في هذه الجلسة لحد ما نحسم القسم 4 تحت.**

---

## 4) 🔴🔴 نقطة الإيقاف الفوري — دومينان (غير `invitations`) يعتمدان حاليًا على كراش #9 كحماية بالصدفة من باج `commit()`-جوه-`begin_nested()` مفتوح (Backlog #11b)

**بالضبط نفس نمط `invitations` قبل إغلاقها.** تحقَّق بالقراءة المباشرة للكود (مش تخمين):

### 4.1) `realestate.buy_fractional_ownership` (`realestate/service.py`)

```
183:  await self._check_saas_limits(tenant_id, "real_estate")   ← يكراش هنا حاليًا (#9)
...
212:  async with self.db.begin_nested():
...
239:      tx_hash = await finance.transfer(...)      ← تحويل مالي حقيقي
244:      await invoicing.create_invoice(...)        ← invoicing.repository.create_invoice() بتعمل commit() مباشر (السطر 29 هناك) — يقفل الـSAVEPOINT بالنص
252:      await self._register_affiliate_commission(...)
```

### 4.2) `realestate.rent_unit` (`realestate/service.py`)

```
330:  await self._check_saas_limits(tenant_id, "real_estate")   ← يكراش هنا حاليًا (#9)
...
360:  async with self.db.begin_nested():
...
378:      await invoicing.create_invoice(...)        ← نفس الـcommit() المباشر جوه الـSAVEPOINT
```

### 4.3) `insurance.subscribe` (`insurance/service.py`)

```
165:  await self._check_saas_limits(tenant_id, "insurance")   ← يكراش هنا حاليًا (#9)
...
193:  async with self.db.begin_nested():
196:      tx_hash = await finance.transfer(...)      ← تحويل مالي حقيقي (premium)
207:      await invoice_service.create_invoice(...)  ← نفس الـcommit() المباشر جوه الـSAVEPOINT
215:      await self._register_affiliate_commission(...)
```

### 4.4) `insurance.review_claim`/الموافقة على مطالبة (`insurance/service.py`)

```
407:  await self._check_saas_limits(tenant_id, "insurance")   ← يكراش هنا حاليًا (#9)
...
451:  async with self.db.begin_nested():
458:      payout_tx = await finance.transfer(...)    ← صرف تعويض مالي حقيقي
467:      await invoice_service.create_invoice(...)  ← نفس الـcommit() المباشر جوه الـSAVEPOINT
```

**السبب الجذري المشترك (مطابق تمامًا لما كان في `invitations` قبل #11a):** `InvoicingRepository.create_invoice()` (`invoicing/repository.py:22-31`) بتعمل `await self.db.commit()` **مباشر** — تعليق تحذيري موجود بالفعل فوقها بالحرف: *"هذا الـcommit() بيغطي كمان كتابات finance.transfer() جوه service methods تانية ... لا تحوّل الـcommit() ده لـflush() بدون فحص شامل لكل الـcallers أولًا."* هذا هو **Backlog #11b** (`realestate-invoicing-savepoint-conflict`) — **مفتوح تمامًا حاليًا، صفر إصلاح عليه**، موثَّق في `PROGRESS_LOG.md` سطر 36 كـ"نفس السبب الجذري زي 11a، لم يُصلَح، يحتاج جلسة منفصلة".

**الأثر لو اتصلح #9 بمعزل عن #11b:**
- حاليًا: أي طلب لـ`buy_fractional_ownership`/`rent_unit`/`insurance.subscribe`/`insurance.review_claim` **يكراش فورًا عند `_check_saas_limits`** (قبل أي كتابة) بـ`AttributeError` — **صفر أثر مالي**، صفر تحويل، صفر فاتورة جزئية.
- لو اتصلحت #9 وحدها (method `get_active_subscription` بقت موجودة وشغالة): الكود هيعدي `_check_saas_limits` بنجاح، ويوصل لأول مرة فعليًا لـ`begin_nested()` → `finance.transfer()` (تحويل مالي حقيقي، **بينجح ويتنفذ فعليًا**) → `invoicing.create_invoice()` (بيقفل الـSAVEPOINT بالنص بـ`commit()` مباشر) → أي كود بعده جوه نفس البلوك (`_register_affiliate_commission`، إنشاء deed NFT، تحديث حالة العقد، إلخ) **هيكراش بـ`InvalidRequestError: Can't operate on closed transaction inside context manager`**.
- **النتيجة العملية:** فلوس حقيقية بتتحوَّل (`finance.transfer` نجح فعليًا) وفاتورة بتتسجَّل، لكن باقي العملية (تسجيل الملكية الفعلية/العقد/عمولة الأفلييت) **بتفشل جزئيًا** — **بالضبط نفس فئة "كتابة حقيقية جزئية على القرص" اللي كانت في `invitations`**، لكن هنا بفلوس حقيقية (تحويل مالي) مش مجرد يوزر بلا محفظة.

**هذا يفعِّل شرط الإيقاف الفوري #3 المذكور صراحة في تعليمات بداية هذه الجلسة.** صفر كود، صفر اقتراح ديف حتى الآن على #9 نفسها.

### 4.5) دومينات فُحصت ولم يُوجَد فيها نفس النمط (للشفافية، مش افتراض)

- `manufacturing`: فُحص موضعا `invoicing.create_invoice` الوحيدين في الملف (سطر 327 و712) — **الاتنين خارج أي `begin_nested()`** (السطر 712 تحديدًا بعد إغلاق بلوك `begin_nested()` في `analyze_and_schedule_maintenance`، مش جواه — تأكَّد بفحص الإندنتيشن مباشرة).
- `logistics`, `employment`, `digital_twin`: صفر استدعاء لـ`invoicing`/`InvoicingService` في الملفات الثلاثة (`grep` شامل، صفر نتيجة).
- `arbitration_syndicates`: 3 مواضع `invoicing.create_invoice` (`create_dispute:133`, `join_syndicate:351`, `issue_license:435`) — **الثلاثة خارج أي `begin_nested()`** (مطابق للتعليق التحذيري في `invoicing/repository.py` نفسه اللي بيذكر `join_syndicate` تحديدًا كمثال على استخدام آمن للنمط الحالي). **صفر اعتماد على كراش #9 لحماية هذا الدومين من #11b.**
- `service_marketplace`: `_check_saas_limits` (`service_marketplace/service.py:67-73`) **لا تنادي `get_active_subscription` إطلاقًا** — بتنادي `can_access_service(tenant_id, "service_marketplace")` (باج مختلف تمامًا، موثَّق مسبقًا كـBacklog #12، wrong-arity). **`service_marketplace` محجوبة حاليًا ببج #12، صفر علاقة بكراش #9.**

---

## 5) ✅ ختم إغلاق الجلسة [2026-08-18] — تعليق رسمي، لا إغلاق كامل

**قرار المستخدم بعد مراجعة القسم 4 كاملًا:**

1. **حالة Backlog #9 النهائية لهذه الجلسة: 🟡 معلَّقة — محظورة بسبب #11b.** ليست "مفتوحة" عادية ولا "مُغلَقة" — إصلاحها ممنوع صراحة قبل إغلاق #11b أولًا (نفس منطق القيد السابق الذي كان مفروضًا على #9 بسبب #11a، لكن هذه المرة السبب هو #11b).
2. **صفر كود، صفر جدول أدلة/حلول تم كتابته لـ#9 نفسها في هذه الجلسة** — القسم 3 أعلاه بقي عند مستوى "خيارات محتملة، توثيق أولي فقط" بالتصميم، ولم يُستكمل لأن القسم 4 أوقف الجلسة قبل أي انتقال لمرحلة الحل.
3. **القيد الجديد على #9:** لا يجوز فتح جلسة إصلاح فعلية لـ#9 قبل إغلاق Backlog #11b رسميًا (بنفس معيار الإغلاق المستخدم في #11a: جدول أدلة، ديف كامل بموافقة صريحة، `git diff`/`git status` خام، تحقق حي بـ`SELECT` مستقل، ختم إغلاق). بعد إغلاق #11b، القيد على #9 يُشال تلقائيًا (بافتراض عدم اكتشاف اعتماد صدفة ثالث أثناء إصلاح #11b — يحتاج تأكيد وقتها).
4. **نطاق #11b المؤكَّد الآن بالقراءة المباشرة (وليس افتراضًا من الأرشيف فقط):** 4 دوال عبر دومينين — `realestate.buy_fractional_ownership` (سطر 244)، `realestate.rent_unit` (سطر 378)، `insurance.subscribe` (سطر 207)، `insurance.review_claim`/الموافقة على مطالبة (سطر 467). **الدومينات المذكورة سابقًا في `PROGRESS_LOG.md` كجزء من #11b (`service_marketplace`, `arbitration_syndicates`) لم تُؤكَّد بنفس النمط الدقيق في هذه الجلسة** — `arbitration_syndicates` تحديدًا تم فحص 3 مواضع `invoicing.create_invoice` فيها ووُجدت **خارج** أي `begin_nested()` (راجع 4.5) — **يحتاج تدقيق منفصل ضمن جلسة #11b نفسها** لتأكيد/نفي دخولها الفعلي ضمن نطاق الإصلاح، بدل افتراض تطابقها التلقائي مع `realestate`/`insurance`.

**الحالة النهائية: 🟡 معلَّقة رسميًا. لا كود. تنتقل المهمة لجلسة مستقلة جديدة لـ#11b.**
