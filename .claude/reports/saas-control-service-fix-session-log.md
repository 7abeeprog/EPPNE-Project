# تقرير جلسة — `saas-control-service-get-active-subscription-fix` (Backlog #9، إكمال)

**بدأ التسجيل:** 2026-08-18
**نطاق الجلسة المعلن:** إضافة `get_active_subscription(self, tenant_id: int)` على `SaaSControlService` لحل Backlog #9، محصور في 4 دوال عبر دومينين (`realestate.buy_fractional_ownership`, `realestate.rent_unit`, `insurance.subscribe`, `insurance.review_claim`).

**هذا التقرير مرجع مستقل بالكامل لهذه الجلسة — لا يُدمج مع أي تقرير سابق.**

---

## 0) قراءة المصادر المطلوبة قبل أي حركة — تم بالكامل

1. `PROGRESS_LOG.md` — بند #9 (سطر 35): `🔴 مفتوح — القيد اتشال [2026-08-18]، #11b مُغلَقة`. بانر الحالة (سطور 9-17) وجدول الـBacklog كامل.
2. `.claude/reports/saas-control-service-missing-methods-session-log.md` بالكامل (127 سطر) — التشخيص الأصلي: التعريف الحقيقي `SaaSRepository.get_active_subscription(tenant_id, service_id)` (`saas/repository.py:122`)، الاستدعاء الناقص `SaaSControlService.get_active_subscription(tenant_id)` (معامل واحد فقط) في 8 دومينات، لا يوجد دليل حذف عرضي — لم تُكتب من الأساس.
3. `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` بالكامل (1206 سطر) — جلسة #11b الموسَّعة (8 دوال/4 دومينات)، مُغلَقة رسميًا. أهم نقاط أخذتها: جدول 17.1 (مستوى تحقق كل دالة)، جدول 17.2 (3 بنود Backlog جانبية: `tourism-place-transfer-bid-player-id-user-id-conflict`, `finance-transfer-returns-transaction-object-not-tx-hash-string`, `eventbus-redis-wrapper-missing-publish`)، وتأكيد قسم 13 إن `buy_fractional_ownership`/`review_claim` (الاتنين في نطاق #9 هنا) هيوصلوا لباج `tx_hash`/`Transaction` المنفصل بمجرد ما #9 تتصلح — متوقَّع، موثَّق مسبقًا، مش اكتشاف جديد.

---

## 1) 🔴🔴 جدول الأدلة — فحص الموديل قبل أي اقتراح ديف، واكتشاف حرج جديد

### 1.1) توقيع الـrepository الفعلي

`saas/repository.py:122-140`:
```python
async def get_active_subscription(self, tenant_id: int, service_id: int) -> Optional[TenantSubscription]:
    result = await self.db.execute(
        select(TenantSubscription)
        .join(ServicePlan)
        .where(and_(
            TenantSubscription.tenant_id == tenant_id,
            ServicePlan.service_id == service_id,
            TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
        ))
        .order_by(TenantSubscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```
تحتاج `service_id` إجباريًا — لا قيمة افتراضية.

### 1.2) كيف بتُستخدم القيمة الراجعة في الثمانية دومينات — نمط موحّد 100%

فحصت الثمانية `_check_saas_limits` بالقراءة المباشرة (`realestate:60-68`, `insurance:42-50`, `digital_twin:36-44`, `employment:67-75`, `arbitration_syndicates:38-46`, `invitations:41-49`, `manufacturing:42-50`, `logistics:47-55`) — **نفس النمط بالحرف في الثمانية، بدون استثناء واحد:**

```python
subscription = await saas_service.get_active_subscription(tenant_id)   # معامل واحد فقط، صفر service_id
if not subscription:
    raise PermissionDeniedError(...)
features = subscription.features or {}          # ← وصول مباشر على subscription، مش subscription.plan
if not features.get(feature, False):             # feature = نص خاص بكل دومين ("real_estate", "insurance", "crm", ...)
    raise PermissionDeniedError(...)
```

**النتيجة الحتمية من هذا النمط:** الثمانية دومينات بتفترض معماريًا **اشتراك واحد شامل لكل tenant** (بلا تحديد خدمة)، وبتفحص داخل `features` بتاعته علَم مُخصَّص لكل دومين (`real_estate`, `insurance`, `crm`, `hr_management`, `manufacturing`, `logistics`, `arbitration`, `digital_twin`...) — **مش** نمط "اشتراك مستقل لكل خدمة" المطبَّق فعليًا في `saas/service.py:102, 219` (`create_subscription`/`can_access_service`، اللي بيستخدموا `service_id` حقيقي لكل خدمة منفصلة).

### 1.3) 🔴🔴 اكتشاف حرج جديد — `subscription.features` غير موجودة على `TenantSubscription` إطلاقًا

فحصت `saas/models.py` بالكامل (سطور 1-110):

| Model | `features` عمود؟ |
|---|---|
| `TenantSubscription` (`models.py:55-87`) | ❌ **لا يوجد عمود `features` على الإطلاق** — الأعمدة: `id, tenant_id, plan_id, idempotency_key, status, grace_period_end_date, trial_end_date, start_date, end_date, next_billing_date, payment_method, auto_renew, created_at, updated_at` + علاقة `plan = relationship("ServicePlan", lazy="selectin")` |
| `ServicePlan` (`models.py:28-52`) | ✅ `features = Column(JSONB, default=list)` (سطر 45) — **موجودة هنا فقط**، وعلى `plan` مش على `subscription` |

**الأثر الحتمي:** `subscription.features` (حيث `subscription` كائن `TenantSubscription` حقيقي راجع من `get_active_subscription`) بترفع **`AttributeError: 'TenantSubscription' object has no attribute 'features'`** — نفس فئة الكراش بالحرف اللي بنحاول نصلحها بـ#9، **لكن سطر واحد بعدها بالضبط**، في **كل الثمانية دومينات بلا استثناء** (مش بس الأربعة في نطاق هذه الجلسة).

**معنى ذلك عمليًا:** إضافة `get_active_subscription(self, tenant_id)` على `SaaSControlService` (الحل المقترح في نطاق الجلسة) **لن تحل شيئًا فعليًا لأي من الدومينات الثمانية** — الكراش هيتحرك من `AttributeError` على استدعاء method غير موجودة، إلى `AttributeError` على attribute غير موجود على السطر التالي مباشرة. **صفر وصول فعلي لمنطق `_check_saas_limits` (فحص الـfeature flag) أو لأي كود بعده في أي من الأربعة دومينات في نطاق هذه الجلسة (`buy_fractional_ownership`, `rent_unit`, `subscribe`, `review_claim`) بمجرد إصلاح #9 وحدها.**

**الوصول الصحيح المفترض (بناءً على الموديل الفعلي):** `subscription.plan.features` (عبر العلاقة `plan`, `lazy="selectin"` — محمَّلة تلقائيًا، آمنة في async context). لاحظ كمان إن الـdefault على العمود نفسه `list` مش `dict` (`Column(JSONB, default=list)`) — لو فعلاً استُخدمت القيمة الافتراضية وقت الإنشاء، حتى `.get()` على `list` هترفع `AttributeError` تانية (`'list' object has no attribute 'get'`) — تحتاج تأكيد بيانات فعلية وقت التحقق الحي، مش افتراض.

### 1.4) لماذا هذا اكتشاف جديد كليًا (مش من الفئات الموثَّقة مسبقًا)

راجعت الثلاثة بجات الموثَّقة من #11b (`tx_hash/Transaction`, `player_id conflict`, `EventBus.publish`) — **لا علاقة لأي منهم بـ`subscription.features`**. هذا اكتشاف مستقل تمامًا، غير موثَّق في أي من التقريرين المرجعيين، ويفعِّل **شرط الإيقاف #4** (باج جديد كليًا خارج الفئات الموثَّقة) — **وليس مجرد تأكيد إضافي**، لأنه يمس **مباشرة** نتيجة إصلاح #9 نفسها (لا يمكن اعتباره "بعيد عن نطاق #9" — هو حرفيًا السطر التالي داخل نفس `_check_saas_limits` اللي #9 بتحاول تصلحها).

### 1.5) 🔑 السؤال التصميمي الأصلي (service_id=None أم منطق مختلف؟) — الجواب الآن أوضح لكن يفتح تناقضًا معماريًا

بناءً على 1.2، الإجابة **ليست** "مرّر `service_id=None`" (الـrepository method مش بتقبل `None` أصلًا — `service_id: int` إجباري بلا `Optional`). النمط الفعلي المُستخدَم من الثمانية دومينات يطابق **"اشتراك واحد شامل لكل tenant، بمعزل عن أي خدمة محدَّدة"** — وهذا **يتعارض بنيويًا** مع الطريقة الوحيدة المتاحة حاليًا لجلب اشتراك (`SaaSRepository.get_active_subscription(tenant_id, service_id)`، مبنية على `join(ServicePlan).where(ServicePlan.service_id == service_id)`).

**خياران فعليان فقط لسد الفجوة، وكلاهما يحتاج قرار تصميمي منك (وليس تفصيلًا تنفيذيًا بسيطًا):**

| الخيار | الوصف | الأثر |
|---|---|---|
| **أ) استعلام جديد "أي اشتراك نشط للـtenant بغض النظر عن الخدمة"** | method جديدة على `SaaSRepository` (مثلاً `get_any_active_subscription(tenant_id)`) — `select(TenantSubscription).where(tenant_id=..., status IN (...)).order_by(created_at.desc()).limit(1)`، بلا `join(ServicePlan)`/`service_id` إطلاقًا | يطابق فعليًا النمط المُستخدَم في الثمانية دومينات (اشتراك واحد + قاموس features متعدد الأعلام). **لا يمس** `get_active_subscription` الموجودة (`service_id`) ولا أي caller حالي لها (`saas/service.py:102,219`) — إضافة صرفة. |
| **ب) استنتاج `service_id` من `feature` string** (يحتاج mapping دومين↔خدمة في `ServiceCatalog`، ثم استخدام `get_active_subscription(tenant_id, service_id)` الموجودة فعليًا) | يطابق تصميم "اشتراك مستقل لكل خدمة" الأصلي (`create_subscription`/`can_access_service`) | يتطلب تأكيد وجود صف `ServiceCatalog` لكل من الثمانية features (`real_estate`, `insurance`, `crm`...) — **لا يوجد أي بيانات seed لـ`saas_service_catalog`/`saas_service_plans`** في المشروع (تأكَّدت: صفر `INSERT`/seed script، الجداول فاضية افتراضيًا وتُملأ فقط عبر API الإداري `create_service`/`create_plan`). لو الجداول فاضية في بيئة التحقق الحي، هذا الخيار هيرجع `None` دائمًا → `PermissionDeniedError("No active subscription found")` بدل الوصول للمنطق — **نفس نتيجة الكراش عمليًا بس بشكل "نظيف" (استثناء متوقَّع مش AttributeError)**. |

**هذا تناقض معماري حقيقي بين "تصميم مقصود" (الخيار أ، مطابق للنمط الفعلي المكتوب 8 مرات) و"التصميم الأصلي الموثَّق في `saas/service.py`" (الخيار ب، اشتراك-لكل-خدمة) — وليس تفصيلًا تنفيذيًا (\"service_id=None أم لأ\") كما صيغ في طلب الجلسة الأصلي. هذا يفعِّل شرط الإيقاف #1 (استثناء تصميمي غير قياسي) بالإضافة لشرط الإيقاف #4 أعلاه.**

---

## 2) ✅ جرد شامل — مستدعيات `get_active_subscription` على `SaaSControlService` في المشروع كله

`grep -rn "get_active_subscription" eppne-backend/app`:

| # | الموقع | التصنيف |
|---|---|---|
| 1 | `employment/service.py:72` | الاستدعاء الناقص (نفس الثمانية القديمة) |
| 2 | `digital_twin/service.py:39` | الاستدعاء الناقص |
| 3 | `arbitration_syndicates/service.py:40` | الاستدعاء الناقص |
| 4 | `realestate/service.py:62` | الاستدعاء الناقص — **في نطاق هذه الجلسة** (يغطي `buy_fractional_ownership` و`rent_unit` عبر `_check_saas_limits` المشتركة) |
| 5 | `manufacturing/service.py:44` | الاستدعاء الناقص |
| 6 | `logistics/service.py:49` | الاستدعاء الناقص |
| 7 | `invitations/service.py:43` | الاستدعاء الناقص |
| 8 | `insurance/service.py:44` | الاستدعاء الناقص — **في نطاق هذه الجلسة** (يغطي `subscribe` و`review_claim` عبر `_check_saas_limits` المشتركة) |
| — | `saas/service.py:102` | ✅ استدعاء صحيح على `self.repo.get_active_subscription(self.tenant_id, service_id)` — ليست جزءًا من الباج |
| — | `saas/service.py:219` | ✅ استدعاء صحيح، نفس السبب |
| — | `saas/repository.py:122` (التعريف), `saas/repository.py:250` (`can_access_service` الخاصة بالـrepo — استدعاء داخلي صحيح) | ✅ ليست جزءًا من الباج |
| — | `social/repository.py:229,242` | ❌ method مختلفة تمامًا بالاسم فقط (`get_active_subscription_for_group`) — صفر علاقة |

**✅ تأكيد صريح:** **نفس الثمانية مواضع الموثَّقة سابقًا بالحرف — صفر موضع تاسع.** لا تغيير في الجرد منذ تقرير #9 الأصلي أو تقرير #11b.

---

## 3) 🔴 فحص حرج — هل إضافة method جديدة على `SaaSControlService` ممكن تأثر على أي حاجة تانية؟

**الجواب: لا، بشرط الالتزام بإضافة صرفة (زيادة method جديدة، صفر لمس على أي method موجودة).**

- `SaaSControlService` مُستخدَمة حاليًا في: `saas/router.py` (مسارات الـAPI المباشرة)، والثمانية دومينات (`realestate`, `insurance`, `digital_twin`, `employment`, `arbitration_syndicates`, `invitations`, `manufacturing`, `logistics` — عبر `SaaSSubscriptionService`/`SaaSControlService`، لاحظ إن بعض الدومينات بتسمّيها `SaaSSubscriptionService` كـalias استيراد لنفس الكلاس، مش كلاس مختلف — تأكَّد من `employment/service.py`/`arbitration_syndicates/service.py` بيستوردوا نفس `SaaSControlService` تحت اسم مستعار).
- إضافة method جديدة بالكامل (اسم `get_active_subscription` غير مُعرَّف حاليًا على الكلاس نفسه — فقط على `self.repo`) **لا يوجد أي تعارض تسمية أو Override لأي method موجودة على `SaaSControlService` نفسها.**
- **لا يوجد أي كود حالي بيعتمد على غياب الـmethod** (أي `hasattr`/`try: AttributeError` معالجة صريحة تتحول لسلوك مختلف عمدًا) — الكراش الحالي غير معالَج، بيتصعّد كـ500 خام.
- **الخطر الوحيد غير المباشر:** لو الحل المُختار (القسم 1.5) أضاف method جديدة على `SaaSRepository` (الخيار أ)، هذا كمان إضافة صرفة، صفر تعارض.

**✅ تأكيد صريح: إضافة method جديدة (بأي من الخيارين أ/ب في القسم 1.5) لن تمس أي method موجودة على `SaaSControlService` أو `SaaSRepository` — شرط الإيقاف #5 غير مُفعَّل.**

---

## 4) 🛑 ملخص أسباب التوقف قبل أي كود

| # | الشرط | مُفعَّل؟ | التفصيل |
|---|---|---|---|
| 1 | استثناء تصميمي غير قياسي | ✅ **مُفعَّل** | تناقض معماري حقيقي بين نمط "اشتراك واحد شامل + features bag" (مطبَّق في الثمانية دومينات) ونمط "اشتراك لكل خدمة" (الموجود فعليًا في `saas/repository.py`/`saas/service.py`) — قرار تصميمي مطلوب (خيار أ/ب في القسم 1.5)، مش تفصيل "service_id=None". |
| 2 | اكتشاف حرج (بيانات/فلوس تتسرب) | ❌ غير مُفعَّل مباشرة | لا تسريب بيانات/فلوس — لكن القسم 4 التالي (اكتشاف #4) يمنع أي قيمة فعلية من إصلاح #9 وحدها. |
| 3 | دومين إضافي تاسع بنفس نمط #9 | ❌ غير مُفعَّل | القسم 2 يؤكد: صفر موضع تاسع. |
| 4 | باج جديد كليًا خارج الفئات الموثَّقة | ✅ **مُفعَّل** | `subscription.features` غير موجودة على `TenantSubscription` (القسم 1.3) — اكتشاف مستقل تمامًا عن الثلاثة بجات المعروفة من #11b، وبيمنع أي وصول فعلي لمنطق `_check_saas_limits` حتى بعد إصلاح #9. |
| 5 | حل يمس method موجودة على `SaaSControlService`/`SaaSRepository` | ❌ غير مُفعَّل | القسم 3: كل الخيارات المطروحة إضافة صرفة. |

---

## 5) الحالة — متوقفة، بانتظار توجيهك

**صفر كود، صفر Edit. الجلسة متوقفة عند نقطتين تحتاجان قرارك الصريح قبل أي متابعة:**

1. **القسم 1.5 (تصميمي):** هل نعتمد الخيار أ (method جديدة "أي اشتراك نشط للـtenant بغض النظر عن الخدمة" — يطابق النمط الفعلي المكتوب 8 مرات، صفر مساس بأي شيء موجود)، أم الخيار ب (ربط `feature` string بـ`service_id` حقيقي عبر `ServiceCatalog` — يحتاج تأكيد/إنشاء بيانات seed غير موجودة حاليًا)؟ **توصيتي: الخيار أ** — يطابق الاستخدام الفعلي 100%، صفر بيانات ناقصة، صفر تغيير على الأربعة استخدامات الصحيحة الحالية (`saas/service.py:102,219`).
2. **القسم 1.3/1.4 (باج جديد):** هل نوسّع نطاق هذه الجلسة ليشمل إصلاح `subscription.features` → `subscription.plan.features` في نفس الأربعة دومينات (أو الثمانية كلها، بما يماثل قرار توسيع نطاق #11b سابقًا)، أم نوثّقه كبند Backlog منفصل تمامًا (زي الثلاثة بجات من #11b) ونكتفي بإصلاح #9 وحدها — مع العلم إن ده معناه **صفر دومين من الأربعة هيوصل فعليًا لمنطق حقيقي شغال بنهاية هذه الجلسة** (هيكراش على `AttributeError` جديد بدل القديم)، عكس التوقع الأصلي في وصف الجلسة ("4 منهم... بقوا يوصلوا فعليًا لمنطق مالي حقيقي شغال وصحيح")؟

**بانتظار قرارك على النقطتين قبل أي جدول ديف/كود.**

---

## 6) ✅ قرارات المستخدم [2026-08-18]

1. **القسم 1.5:** ✅ الخيار أ معتمَد — method جديدة `get_any_active_subscription(tenant_id)` على `SaaSRepository` (اشتراك واحد شامل لكل tenant، بلا `service_id`)، صفر لمس على `get_active_subscription(tenant_id, service_id)` الموجودة.
2. **القسم 1.3/1.4:** ✅ نطاق موسَّع — تصحيح `subscription.features` → `subscription.plan.features` في **الثمانية دومينات كلهم** (نفس السبب الجذري، نفس منطق توسيع #11b).
3. **طلب إضافي قبل أي ديف:** تحقق حي بـ`SELECT` مباشر من القيمة الفعلية لعمود `features` على `saas_service_plans` — لمعرفة `list` أم `dict` قبل كتابة أي كود لـ`.get()`.

---

## 7) ✅ التحقق الحي المطلوب [2026-08-18] — القيمة الفعلية لعمود `features`

**قاعدة البيانات الفعلية اللي بيتصل بيها الباك إند:** تأكَّدت من `eppne-backend/.env` (`DATABASE_URL=postgresql+asyncpg://eppne:eppne123@127.0.0.1:5435/eppne_v2`) — بورت `5435` بيتطابق مع الكونتينر `eppne_db` (`docker ps`: `eppne_db 0.0.0.0:5435->5432/tcp`)، مش `postgres-eppne` (بورت `5433`، قاعدة بيانات مختلفة `eppne` مش `eppne_v2`). **هذا نفس الكونتينر المستخدَم فعليًا في التحقق الحي لجلسة #11b السابقة** (نفس أسماء اليوزرات/الجداول المذكورة هناك موجودة فيه).

### 7.1) نتيجة `SELECT` المباشر

```sql
SELECT id, service_id, name, code, features, pg_typeof(features) FROM saas_service_plans;
-- (0 rows)

SELECT count(*) FROM saas_tenant_subscriptions;  -- 0
SELECT count(*) FROM saas_service_catalog;       -- 0
```

**صفر صفوف في الثلاثة جداول (`saas_service_catalog`, `saas_service_plans`, `saas_tenant_subscriptions`) — مؤكِّد لملاحظة القسم 1.5 السابقة (صفر بيانات seed).** لا يمكن تحديد "list أم dict" من بيانات فعلية على القرص حاليًا — الجدول فاضي بالكامل.

### 7.2) ✅ التحديد القاطع من مصدر أدق من الـSELECT — تعريف الـSchema/الـModel نفسه

بما إن الجدول فاضي، رجعت لمصدر الحقيقة التالي: **كود إنشاء الـplan نفسه** (`saas/schemas.py:42`):

```python
features: List[str] = Field(default=[], description="قائمة الميزات")
```

و`saas/models.py:45`:
```python
features = Column(JSONB, default=list)
```

**النتيجة القاطعة: `features` مصمَّمة بنيويًا كـ`List[str]` (قائمة أكواد الميزات المفعَّلة، مثلاً `["real_estate", "crm", "insurance"]`) — مش `Dict[str, bool]`.** الـSchema والـModel متطابقان بالكامل على `list`. **صفر مصدر في الكود بيدعم افتراض `dict` من الأساس.**

### 7.3) 🔴 أثر إضافي على الحل — `.get(feature, False)` غلط بغض النظر عن مصدر `features` (`subscription` أم `plan`)

هذا يعني إن نمط `.get(feature, False)` المستخدَم في الثمانية دومينات **غلط من ناحيتين مستقلتين، مش ناحية واحدة:**
1. مصدر خاطئ: `subscription.features` (غير موجودة) بدل `subscription.plan.features` (القسم 1.3، مُصلَحة بالفعل بالقرار #2).
2. **نمط وصول خاطئ: `.get(feature, False)` أسلوب `dict`، لكن النوع الفعلي `list` — حتى بعد تصحيح المصدر، `.get()` على `list` هترفع `AttributeError: 'list' object has no attribute 'get'` مباشرة.** الفحص الصحيح المطابق للتصميم الفعلي هو **عضوية (`in`)**: `feature in (subscription.plan.features or [])`.

**هذا الاكتشاف امتداد طبيعي لنفس القرار #2 (توسيع تصحيح `.features`) — مش اكتشاف مستقل يحتاج قرار إيقاف جديد**، لأنه يقع تحت نفس العنوان اللي وافقت عليه بالفعل ("تصحيح `.features`... للثمانية دومينات")، وأنت طلبت صراحة التحقق من نوع البيانات "عشان نعرف الإصلاح الصح لـ`.get()`" — وده بالظبط الجواب: **الإصلاح الصح مش تعديل `.get()`، هو استبداله بالكامل بفحص عضوية `in`.**

---

## 8) 🔑 جدول الحل النهائي الموحَّد (يغطي القرارين معًا) — قبل أي كود

### 8.1) الإضافة الأولى — `SaaSRepository.get_any_active_subscription` (جديدة بالكامل)

**الموقع المقترح:** `saas/repository.py`، مباشرة بعد `get_active_subscription` الموجودة (بعد سطر 140، قبل `get_subscriptions_for_renewal`).

```python
async def get_any_active_subscription(self, tenant_id: int) -> Optional[TenantSubscription]:
    result = await self.db.execute(
        select(TenantSubscription)
        .where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
            )
        )
        .order_by(TenantSubscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

نفس بنية `get_active_subscription` بالحرف (نفس `status.in_([...])`, نفس `order_by`/`limit(1)`) لكن بلا `join(ServicePlan)`/`service_id` — أحدث اشتراك نشط/تجريبي للـtenant بغض النظر عن الخدمة. صفر لمس على `get_active_subscription` الموجودة.

### 8.2) الإضافة الثانية — `SaaSControlService.get_active_subscription` (جديدة بالكامل، wrapper)

**الموقع المقترح:** `saas/service.py`، بعد `get_subscription_status` (سطر 88)، قبل `create_subscription` (سطر 90) — نفس قسم "3. اشتراكات المستأجر".

```python
async def get_active_subscription(self, tenant_id: int) -> Optional[TenantSubscription]:
    return await self.repo.get_any_active_subscription(tenant_id)
```

**لماذا `tenant_id` كمعامل رغم وجوده أصلًا في `self.tenant_id`؟** للحفاظ على التوافق الحرفي مع الثمانية استدعاءات الحالية (`saas_service.get_active_subscription(tenant_id)`) بلا أي تعديل إضافي على توقيع الاستدعاء نفسه في الدومينات — الـwrapper بيقبل المعامل ويتجاهل `self.tenant_id` (نفس القيمة عمليًا في كل الاستخدامات الحالية، بما إن `SaaSControlService`/`SaaSSubscriptionService` بتتنشأ دائمًا بـ`tenant_id` نفسه الممرَّر لاحقًا). صفر تغيير مطلوب على أي سطر استدعاء في الثمانية دومينات.

### 8.3) التصحيح الثالث — الثمانية دومينات: `subscription.features` (dict-style) → `subscription.plan.features` (list-membership)

**نمط موحَّد للتصحيح في الثمانية مواضع (نفس التغيير بالحرف في كل مكان):**

```diff
-        features = subscription.features or {}
-        if not features.get(feature, False):
+        features = subscription.plan.features or []
+        if feature not in features:
```

(في `digital_twin`، الفحص بيستخدم `"digital_twin"` نصًا حرفيًا بدل متغير `feature` — نفس القاعدة: `if "digital_twin" not in features:`)

**جدول المواضع الثمانية بالتحديد الدقيق (سطور حالية):**

| # | الملف | سطر `features = ...` | سطر `if not features.get(...)` | ملاحظة خاصة |
|---|---|---|---|---|
| 1 | `realestate/service.py` | 65 | 66 | `feature` متغير |
| 2 | `insurance/service.py` | 47 | 48 | `feature` متغير |
| 3 | `digital_twin/service.py` | 42 | 43 | `"digital_twin"` نص حرفي، مش متغير |
| 4 | `employment/service.py` | 75 | 76-79 (رسالة خطأ متعددة الأسطر) | `feature` متغير |
| 5 | `arbitration_syndicates/service.py` | 43 | 44 | `feature` متغير |
| 6 | `invitations/service.py` | 46 | 47 | `feature` متغير |
| 7 | `manufacturing/service.py` | 47 | 48 | `feature` متغير |
| 8 | `logistics/service.py` | 52 | 53 | `feature` متغير |

**صفر تغيير في:** توقيع `_check_saas_limits` نفسها، رسائل الأخطاء (نصها زي ما هي)، `return subscription, features` (في المواضع اللي بترجعها) — القيمة الراجعة `features` هتبقى `list` بدل `dict`، **لازم تأكيد إن مفيش أي `caller` لـ`_check_saas_limits` بيستخدم القيمة الراجعة التانية (`features`) بأسلوب `dict` في مكان تاني** (فحص إضافي مطلوب قبل الديف النهائي — قسم 9 التالي).

---

## 9) ✅ فحص إضافي — هل أي `caller` بيستخدم القيمة الراجعة `features` (التاني في `return subscription, features`) بأسلوب `dict` في مكان تاني؟

`grep` شامل لـ`_check_saas_limits(` على كامل `eppne-backend/app/domains` (كل الدومينات، مش بس الثمانية) — **كل استدعاء بلا استثناء واحد هو `await self._check_saas_limits(tenant_id, "...")` كجملة مستقلة، صفر `=` أو `subscription, features =` في أي مكان.** القيمة الراجعة (`return subscription, features`، حيث موجودة) **غير مُستخدَمة إطلاقًا من أي caller في المشروع كله.** ✅ **آمن تمامًا تغيير نوع `features` من `dict` إلى `list` — صفر تأثير جانبي على أي كود مستدعي.**

---

## 10) 🛑 الديف الحرفي الكامل (٣ أجزاء) — بانتظار موافقتك الصريحة قبل أي `Edit`

### 10.1) `saas/repository.py` — إضافة `get_any_active_subscription`

```diff
@@ eppne-backend/app/domains/saas/repository.py @@
     async def get_active_subscription(
         self,
         tenant_id: int,
         service_id: int
     ) -> Optional[TenantSubscription]:
         result = await self.db.execute(
             select(TenantSubscription)
             .join(ServicePlan)
             .where(
                 and_(
                     TenantSubscription.tenant_id == tenant_id,
                     ServicePlan.service_id == service_id,
                     TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                 )
             )
             .order_by(TenantSubscription.created_at.desc())
             .limit(1)
         )
         return result.scalar_one_or_none()
 
+    async def get_any_active_subscription(
+        self,
+        tenant_id: int
+    ) -> Optional[TenantSubscription]:
+        """اشتراك واحد شامل نشط/تجريبي للـtenant، بغض النظر عن الخدمة (يستخدمه _check_saas_limits عبر الدومينات)."""
+        result = await self.db.execute(
+            select(TenantSubscription)
+            .where(
+                and_(
+                    TenantSubscription.tenant_id == tenant_id,
+                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
+                )
+            )
+            .order_by(TenantSubscription.created_at.desc())
+            .limit(1)
+        )
+        return result.scalar_one_or_none()
+
     async def get_subscriptions_for_renewal(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
```

### 10.2) `saas/service.py` — إضافة `get_active_subscription` (wrapper)

```diff
@@ eppne-backend/app/domains/saas/service.py @@
     async def get_subscription_status(self, subscription_id: int) -> dict:
         sub = await self.get_subscription(subscription_id)
         plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
         return {
             "id": sub.id,
             "status": sub.status,
             "plan": plan.name if plan else None,
             "grace_period_end_date": sub.grace_period_end_date,
             "next_billing_date": sub.next_billing_date,
             "is_active": sub.status in ["ACTIVE", "TRIAL"],
         }
 
+    async def get_active_subscription(self, tenant_id: int) -> Optional[TenantSubscription]:
+        """اشتراك واحد شامل نشط/تجريبي للـtenant (wrapper حول SaaSRepository.get_any_active_subscription) — تُستخدَم من _check_saas_limits عبر 8 دومينات."""
+        return await self.repo.get_any_active_subscription(tenant_id)
+
     async def create_subscription(
```

### 10.3) الثمانية دومينات — `subscription.features`/`.get()` → `subscription.plan.features`/`in` + فحص دفاعي `belt-and-suspenders`

**✅ تحديث [2026-08-18] — قرار مستخدم صريح:** رغم تأكيد كفاية الـFK (`plan_id NOT NULL` + `ForeignKeyConstraint` بلا `CASCADE`/`SET NULL`، السلوك الافتراضي `NO ACTION`/`RESTRICT` يمنع حذف `ServicePlan` مُشار إليه + صفر `delete_plan` endpoint في الكود كله)، **تمت إضافة فحص دفاعي `if not subscription.plan: raise PermissionDeniedError(...)`** في الثمانية مواضع كتحوّط ضد تدخل يدوي مستقبلي على الـDB يتخطى الـORM (نفس الفئة اللي حصلت فعليًا مع `sovereign_invitations_v2` في جلسة `invitations` سابقًا) — تكلفة الفحص صفر تقريبًا (فحص `None` بسيط، صفر استعلام DB إضافي لأن `subscription.plan` مُحمَّلة مسبقًا عبر `lazy="selectin"`).

**نفس نمط التغيير بالحرف في السبعة (كل الدومينات ماعدا `digital_twin`):**

```diff
         if not subscription:
             raise PermissionDeniedError("No active subscription found.")
-        features = subscription.features or {}
-        if not features.get(feature, False):
+        if not subscription.plan:
+            raise PermissionDeniedError("No valid subscription plan found.")
+        features = subscription.plan.features or []
+        if feature not in features:
```

**`digital_twin` (نص حرفي بدل متغير، ورسالة "no active subscription" مختلفة الصياغة):**

```diff
         if not subscription:
             raise PermissionDeniedError("No active subscription found for this entity.")
-        features = subscription.features or {}
-        if not features.get("digital_twin", False):
+        if not subscription.plan:
+            raise PermissionDeniedError("No valid subscription plan found.")
+        features = subscription.plan.features or []
+        if "digital_twin" not in features:
```

**`employment` تحديدًا (رسالة الخطأ الرئيسية متعددة الأسطر، صفر تغيير في نصها):**

```diff
         if not subscription:
             raise PermissionDeniedError("No active subscription found for this entity.")
-        features = subscription.features or {}
-        if not features.get(feature, False):
+        if not subscription.plan:
+            raise PermissionDeniedError("No valid subscription plan found.")
+        features = subscription.plan.features or []
+        if feature not in features:
             raise PermissionDeniedError(
                 f"Feature '{feature}' is not included in your current plan."
             )
```

**جدول التطبيق الدقيق على الثمانية ملفات (سطور القرص الحالية قبل التعديل):**

| # | الملف | سطر `if not subscription:` | سطر `features = ...` (يُستبدَل بـ3 أسطر: فحص دفاعي + `features=` + `if ... not in`) |
|---|---|---|---|
| 1 | `realestate/service.py` | 63-64 | 65-66 |
| 2 | `insurance/service.py` | 45-46 | 47-48 |
| 3 | `digital_twin/service.py` | 40-41 | 42-43 |
| 4 | `employment/service.py` | 73-74 | 75-79 |
| 5 | `arbitration_syndicates/service.py` | 41-42 | 43-44 |
| 6 | `invitations/service.py` | 44-45 | 46-47 |
| 7 | `manufacturing/service.py` | 45-46 | 47-48 |
| 8 | `logistics/service.py` | 50-51 | 52-53 |

**صفر تغيير في:** توقيع `_check_saas_limits`، نصوص رسائل الأخطاء الموجودة سابقًا، `return subscription, features` (حيث موجودة — القيمة التانية `list` بدل `dict`، مؤكَّد آمن في القسم 9)، أي سطر تاني في الملفات الثمانية. رسالة الفحص الدفاعي الجديدة (`"No valid subscription plan found."`) موحَّدة بالحرف في الثمانية مواضع.

---

**الملخص الكامل النهائي:** 2 ملف إضافة صرفة (`saas/repository.py`, `saas/service.py`، method جديدة لكل واحد) + 8 ملفات تصحيح 3 أسطر بدل سطرين لكل واحد (بسبب الفحص الدفاعي الإضافي) = **10 ملفات، صفر لمس على أي method/سطر تاني غير المذكور أعلاه في أي ملف.**

**بانتظار موافقتك النهائية الصريحة على الديف الثلاثي المُحدَّث أعلاه (10.1 + 10.2 + 10.3) قبل أي `Edit` فعلي.**

---

## 11) ✅ فحص إضافي [2026-08-18] — تأكيد كفاية FK `plan_id`، ثم قرار المستخدم بإضافة فحص دفاعي `belt-and-suspenders`

**فحصت مباشرة:**
- `saas/models.py:68`: `plan_id = Column(Integer, ForeignKey("saas_service_plans.id"), nullable=False, index=True)` — **`NOT NULL`** على مستوى العمود.
- Migration (`71820e4fe1f3...py:1609`): `ForeignKeyConstraint(['plan_id'], ['saas_service_plans.id'])` **بلا `ondelete=`** → سلوك افتراضي `NO ACTION`/`RESTRICT` (يمنع حذف `ServicePlan` مُشار إليه).
- `grep` شامل لأي `delete_plan`/`DELETE FROM saas_service_plans` في `app/` كله — **صفر نتيجة**، لا يوجد مسار حذف خطة في الكود إطلاقًا.

**الخلاصة:** الـconstraint كافٍ فعليًا — `subscription.plan` لا يمكن يبقى `None` عبر أي مسار تطبيقي شرعي. **✅ قرار المستخدم:** إضافة الفحص الدفاعي `belt-and-suspenders` رغم كفاية الـconstraint، كتحوّط ضد تدخل يدوي مستقبلي على الـDB (نفس فئة `sovereign_invitations_v2` في جلسة `invitations`) — تكلفته صفر تقريبًا (`subscription.plan` مُحمَّلة سلفًا عبر `lazy="selectin"`، صفر استعلام إضافي). **الديف النهائي المعتمَد أصبح قسم 10.3 المُحدَّث أعلاه (بإضافة `if not subscription.plan: raise PermissionDeniedError("No valid subscription plan found.")` في الثمانية مواضع، قبل سطر `features = subscription.plan.features or []`).**

**✅ موافقة نهائية صريحة مستلَمة على الديف الكامل (10.1+10.2+10.3).**

---

## 12) ✅ التطبيق [2026-08-18] — `git diff`/`git status` خام

**تم التطبيق عبر 10 عمليات `Edit` (ملفين إضافة صرفة + 8 ملفات تصحيح 3 أسطر) — مطابقة تمامًا للديف المعتمَد، صفر انحراف.** `git diff` كامل خام في الجزء المرفق للمستخدم في المحادثة (يشمل ضوضاء `constructor-mismatch` مسبقة في نفس الملفات الثمانية، غير مرتبطة بهذه الجلسة، مؤكَّدة من `git status` الأصلي في أول المحادثة). `git status --porcelain` يظهر `saas/repository.py` و`saas/service.py` كملفين `M` جديدين + الثمانية دومينات ضمن قائمة `M` الموجودة مسبقًا — صفر ملف إضافي غير متوقَّع.

---

## 13) ✅ التحقق الحي [2026-08-18] — الأربعة دومينات في نطاق الجلسة

**السكريبت:** `.../scratchpad/verify_saas_9_fix.py` — Scratchpad فقط، صفر تعديل على `app/`. **الفرق الجوهري عن منهجية تحقق #11b السابقة: صفر `monkeypatch` على `_check_saas_limits` نفسها هذه المرة** — تم زرع اشتراك SaaS حقيقي (`ServiceCatalog`+`ServicePlan` بـ`features=["real_estate","insurance"]`+`TenantSubscription` حالة `ACTIVE`) لتنفيذ `_check_saas_limits` الحقيقية (المُصلَحة) فعليًا، بما إن هذا بالظبط جوهر ما بنتحقق منه اليوم. التجاوز الوحيد المتبقي: `audit_log` (بج #14 مسبق موثَّق، بره نطاق #9).

### 13.1) نتائج التنفيذ الحي

| الدالة | النتيجة الراجعة من الدالة | تفسير |
|---|---|---|
| `realestate.rent_unit` | ✅ `{'ok': True, 'contract_id': 5}` | **نجاح كامل** — `_check_saas_limits` الحقيقية عدّت بنجاح (إثبات مباشر إن #9 اتصلحت فعليًا)، العقد اتسجل والتزم. |
| `realestate.buy_fractional_ownership` | 🟡 `{'ok': False, 'error': "TypeError: AIAgentsService.execute_agent_action() got an unexpected keyword argument 'tenant_id'"}` | `_check_saas_limits` عدّت بنجاح (#9 مؤكَّدة)، لكن الدالة كراشت **قبل الوصول حتى لباج `tx_hash` المتوقَّع** — عند `ai.execute_agent_action(...)` غير المحمية بـ`try/except` (سطر 232) — **نفس فئة Backlog #16 الموثَّق مسبقًا (`ai-agents-execute-agent-action-wrong-kwarg`)، مش اكتشاف جديد، لكن أول تأكيد حي لهذا الموضع تحديدًا**. الكراش يحصل **قبل** `finance.transfer` أصلًا (سطر 241)، جوه `begin_nested()` — يعني تراجع (rollback) كامل ونظيف، صفر أثر جزئي (مؤكَّد بالـSELECT تحت). |
| `insurance.subscribe` | 🟡 `{'ok': False, 'error': "AttributeError: 'RedisClientWrapper' object has no attribute 'publish'"}` | **نفس باج `EventBus.publish` المسبق الموثَّق من #11b (قسم 15.1)، مؤكَّد تاني هنا** — لكن هذه المرة `_check_saas_limits` الحقيقية (غير الـmonkeypatched) هي اللي عدّت بنجاح ووصلت للمنطق المالي الحقيقي بالكامل (`commit()` + `create_subscription` نجحوا، مؤكَّد بـSELECT تحت) قبل ما تكراش على الباج المسبق. |
| `insurance.review_claim` | 🟡 `{'ok': False, 'error': "TypeError: UserRepository.get_by_id() missing 1 required positional argument: 'tenant_id'"}` | `_check_saas_limits` عدّت بنجاح (#9 مؤكَّدة). الكراش هنا **قبل الوصول لباج `tx_hash` المتوقَّع كمان** — نفس فئة **Backlog #1 الموثَّق مسبقًا (`user-repository-get-by-id-audit`، أولوية مرفوعة بالفعل في الجدول)**، تأكيد حي إضافي في مسار جديد (مسار صرف تعويض التأمين). الكراش جوه `begin_nested()`، قبل `commit()` — تراجع كامل نظيف (مؤكَّد بالـSELECT تحت). |

**ملاحظة صريحة مهمة:** التوقع الأصلي (قسم 13 من التقرير السابق قبل هذه الجلسة، ومن #11b) كان إن `buy_fractional_ownership`/`review_claim` هيوصلوا **لباج `tx_hash`/`Transaction`** تحديدًا. الحي أظهر إنهم بيكراشوا **قبل** الوصول لذلك الباج، على بجين مسبقين موثَّقين آخرين (**#16** و**#1** على التوالي) — **الاتنين معروفين ومُوثَّقين من قبل في `PROGRESS_LOG.md` (مش اكتشاف جديد)**، لكن نقطة الكراش الفعلية مختلفة عن التوقع الحرفي. هذا **لا يغيّر** التصنيف العام (الدالتان "مراجعة ديف/كود بس، محجوبتان ببجات مسبقة منفصلة عن #9") — فقط يُصحِّح **أي باج مسبق بالتحديد** هو الحاجب الفعلي. باج `tx_hash`/`Transaction` نفسه **لسه غير مؤكَّد حيًا** لهاتين الدالتين تحديدًا (الكراش الأسبق منعه)، يبقى مؤكَّد بالقراءة فقط (كما كان في القسم 13 السابق).

### 13.2) ✅ تحقق مستقل بـ`SELECT` مباشر (`eppne_db`/`eppne_v2`)

```sql
-- rent_unit
SELECT id, unit_id, landlord_user_id, tenant_user_id, monthly_rent_mrusdt, contract_tx_hash
FROM rental_contracts WHERE id=5;
--  5 | 4 | 113 | 114 | 50.00000000 | RENT-45A8DF963ADB   ✅ موجود، ملتزم فعليًا

-- buy_fractional_ownership (تأكيد تراجع نظيف)
SELECT count(*) FROM property_ownerships WHERE owner_user_id=116;   -- 0   ✅ صفر أثر جزئي
SELECT balances->>'MR_USDT' FROM wallets WHERE user_id=116;         -- 1000.0   ✅ محفظة المشتري بلا مساس (لم يوصل حتى لـfinance.transfer)

-- insurance.subscribe (تأكيد المسار المالي الحقيقي نجح بالكامل)
SELECT id, status, subscription_tx_hash FROM insurance_subscriptions WHERE subscriber_user_id=117;
--  7 | ACTIVE | SUB-BB8123F6B03E   ✅ الاشتراك اتسجل والتزم فعليًا
SELECT balances->>'MR_USDT' FROM wallets WHERE user_id=117;         -- 980.0 (كان 1000، خُصم القسط 20)   ✅ التحويل نجح فعليًا
SELECT id, sender_id, receiver_id, amount, status FROM transactions WHERE sender_id=117;
--  39 | 117 | 121 | 20.00000000 | COMPLETED   ✅

-- insurance.review_claim (تأكيد تراجع نظيف)
SELECT id, status, payout_tx_hash, approved_amount_mrusdt FROM insurance_claims WHERE id=2;
--  2 | SUBMITTED | (فاضي) | 0.00000000   ✅ صفر أثر جزئي — المطالبة زي ما هي، صفر تعويض اتصرف، صفر تحديث حالة وهمي
```

### 13.3) الخلاصة القاطعة

**Backlog #9 مُصلَحة فعليًا ومؤكَّدة حيًا بشكل قاطع** — `_check_saas_limits` الحقيقية (بلا أي `monkeypatch`) عدّت بنجاح في **كل الأربعة دوال بلا استثناء** (صفر `AttributeError` على `get_active_subscription` في أي منها). **دالتان (`rent_unit`, `subscribe`) وصلتا فعليًا لمنطق مالي/تسجيلي حقيقي شغال وصحيح بالكامل، ملتزم على القرص، مؤكَّد بـSELECT مستقل** — تمامًا كما كان متوقَّعًا في وصف الجلسة الأصلي. **الدالتان الأخريان (`buy_fractional_ownership`, `review_claim`) محجوبتان ببجات مسبقة موثَّقة (Backlog #16 و#1 على التوالي، مش #9 ومش اكتشاف جديد)** — تراجع نظيف مؤكَّد بـSELECT، صفر أثر جزئي/بيانات فاسدة على القرص في الحالتين.

---

## 14) ✅ ختم الإغلاق الرسمي [2026-08-18] — Backlog #9

### 14.1) جدول مستوى التحقق النهائي

| # | الدالة | الديف مطبَّق؟ | `_check_saas_limits` عدّت؟ (إثبات #9) | مستوى التحقق | الحاجب الحالي (إن وُجد) |
|---|---|---|---|---|---|
| 1 | `realestate.rent_unit` | ✅ | ✅ | ✅ **تحقق حي كامل، نجاح تام** | لا يوجد |
| 2 | `insurance.subscribe` | ✅ | ✅ | ✅ **تحقق حي كامل للمسار المالي** (`commit`+`create_subscription` مؤكَّدان بـSELECT) | بج مسبق موثَّق (`eventbus-redis-wrapper-missing-publish`) بعد نجاح #9 |
| 3 | `realestate.buy_fractional_ownership` | ✅ | ✅ | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب) | بج مسبق موثَّق (Backlog #16، `ai-agents-execute-agent-action-wrong-kwarg`) — أسبق من `tx_hash` |
| 4 | `insurance.review_claim` | ✅ | ✅ | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب) | بج مسبق موثَّق (Backlog #1، `user-repository-get-by-id-audit`) — أسبق من `tx_hash` |

**الرقم الحاسم: 4 من 4 دوال أثبتت حيًا إن `_check_saas_limits` (ومن ضمنها إصلاح #9 + إصلاح `subscription.plan.features`) بقت شغالة فعليًا بلا استثناء — 100%.**

### 14.2) الملخص التنفيذي

**السبب الجذري (كان):** `SaaSControlService.get_active_subscription(tenant_id)` غير موجودة إطلاقًا — method لم تُكتب من الأساس، مستخدَمة من 8 دومينات بنفس التوقيع الخاطئ.

**الحل المُطبَّق:**
1. `SaaSRepository.get_any_active_subscription(tenant_id)` (جديدة) — اشتراك واحد شامل نشط/تجريبي للـtenant، بغض النظر عن الخدمة (يطابق النمط الفعلي المستخدَم في الثمانية دومينات: اشتراك واحد + قاموس/قائمة ميزات).
2. `SaaSControlService.get_active_subscription(tenant_id)` (جديدة) — wrapper صرف حولها.
3. **اكتشاف حرج إضافي أثناء الفحص (خارج الفئات الموثَّقة من #11b):** `subscription.features` غير موجودة على `TenantSubscription` أصلًا (موجودة على `ServicePlan` فقط، عبر `subscription.plan`)، **و**`features` مصممة كـ`List[str]` (مؤكَّد من `saas/schemas.py`) مش `Dict[str,bool]` — يعني `.get(feature, False)` غلط من ناحيتين. **صُحِّح الاتنين معًا** في الثمانية دومينات: `subscription.plan.features or []` + `feature not in features`.
4. **فحص دفاعي إضافي (`belt-and-suspenders`، بطلب المستخدم):** `if not subscription.plan: raise PermissionDeniedError(...)` قبل الوصول لـ`.plan.features` — رغم تأكيد كفاية الـFK constraint (`NOT NULL` + `RESTRICT`)، كتحوّط ضد تدخل يدوي مستقبلي على الـDB.

**النطاق الفعلي المُصلَح:** الثمانية دومينات كلهم (`realestate`, `insurance`, `digital_twin`, `employment`, `arbitration_syndicates`, `invitations`, `manufacturing`, `logistics`) — رغم إن نطاق التحقق الحي المطلوب في هذه الجلسة اقتصر على الأربعة الأصليين (`realestate`×2, `insurance`×2) بموجب تعليمات الجلسة.

**التحقق الحي:** 4 من 4 دوال في نطاق الجلسة أثبتت حيًا نجاح `_check_saas_limits` الحقيقية (إثبات #9). دالتان (`rent_unit`, `subscribe`) وصلتا لتنفيذ كامل ناجح موثَّق بـSELECT مستقل. دالتان (`buy_fractional_ownership`, `review_claim`) محجوبتان ببجات مسبقة موثَّقة (#16, #1 — ليس #9)، مع تأكيد حي إضافي (تراجع نظيف بلا أي أثر جزئي على القرص، بـSELECT مستقل).

**اكتشافات جانبية جديدة موثَّقة (تأكيدات لبجات مسبقة، صفر بند Backlog جديد):**
- Backlog #16 (`ai-agents-execute-agent-action-wrong-kwarg`) — تأكيد حي جديد في `realestate.buy_fractional_ownership:232` (استدعاء غير محمي بـ`try/except`، بعكس نظيره المحمي في `review_claim`).
- Backlog #1 (`user-repository-get-by-id-audit`) — تأكيد حي جديد في مسار `insurance.review_claim` (صرف تعويض).
- Backlog #14 (`audit-log-wrong-kwargs`) — تأكيد حي إضافي **داخل `InvoicingService.create_invoice()` نفسها** (مش بس في `_check_saas_limits`/الدومينات المستدعية كما كان موثَّقًا سابقًا) — ظهر في `rent_unit` و`subscribe` كـ"Invoice creation failed... audit_log() got an unexpected keyword argument 'tenant_id'"، مُلتقَط بأمان بفضل `try/except` #11b.

**الحالة النهائية: ✅ Backlog #9 مُغلَقة رسميًا [2026-08-18].**

**تنظيف throwaway:** بيانات التحقق (`p_saas9_verify_*` يوزرات، أرض/تطوير/وحدتين، بوليصة/كيان/اشتراك تأميني/مطالبة، خطة/كتالوج/اشتراك SaaS) تُترك كما هي — تنظيف روتيني غير عاجل، بنفس سياسة الجلسات السابقة (`throwaway-cleanup` النشط في `PROGRESS_LOG.md`).

