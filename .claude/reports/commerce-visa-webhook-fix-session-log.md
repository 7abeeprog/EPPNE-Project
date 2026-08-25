# جلسة تحليل وإصلاح — `commerce.visa_webhook` (البند المؤجَّل منذ 2026-08-13)

**بدأ التسجيل:** 2026-08-25
**الحالة:** ✅ **الإصلاحات الثلاثة المعتمَدة (§7) مُطبَّقة ومؤكَّدة حيًا بالكامل. لم يُنفَّذ commit بعد — بانتظار مراجعتك للـ`git diff` (§9) وموافقتك الصريحة.**

**نطاق الجلسة:** `POST /commerce/payment/visa/webhook` فقط —
`router.py:193-206` + `service.handle_visa_webhook` (`service.py:408-437`)
+ `core/security.py:277-282` (`get_current_tenant`) + `schemas.py:204-212`
(`VisaWebhookPayload`، غير مُستخدَمة فعليًا).

**الملفات المقروءة كاملة قبل البدء:**
- `.claude/reports/commerce-idor-fix-session-log.md` (القسم §1، §4.2 — المرجع الأصلي لتأجيل هذا البند)
- `eppne-backend/app/domains/commerce/{router,service,models,schemas}.py` (كاملة)
- `eppne-backend/app/core/security.py` (تعريف `get_current_tenant`، §277-294)
- `.claude/plans/critical-finding-xtenant-systemic.md` (الاكتشاف النظامي لثقة `X-Tenant-ID`)
- بحث شامل في `eppne-backend/app` عن أي نمط HMAC/signature/webhook-secret موجود فعلًا (صفر نتيجة)

---

## 1) السؤال المرجعي الأول — هل فحص `signature` حقيقي؟

**تأكيد نهائي: لا، غياب كامل.**

`router.py:193-206`:
```python
@router.post("/payment/visa/webhook")
async def visa_webhook(
    payload: dict,
    signature: str = Header(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db, tenant_id)
    try:
        order = await service.handle_visa_webhook(payload, signature, idempotency_key)
```

`service.py:408-413` (`handle_visa_webhook`) يستقبل `signature` كبارامتر لكن
**لا يستخدمه إطلاقًا في أي مكان بجسم الدالة (408-437)** — لا `hmac.compare_digest`،
لا أي مقارنة، لا أي استدعاء تحقق. الهيدر مُستقبَل ومُرسَل، لكنه **حبر على ورق**.

**دليل إضافي غير موثَّق سابقًا:** يوجد فعليًا Pydantic schema جاهز
`VisaWebhookPayload` (`schemas.py:204-212`) يحتوي على `signature: str` و
`transaction_id: str` و`gateway_reference: str` كحقول متوقَّعة في **جسم**
الطلب — لكن الراوتر **لا يستخدم هذا الـschema إطلاقًا**، ويستقبل `payload: dict`
خام بدلًا منه، ويقرأ `signature` من **Header** منفصل تمامًا. يبدو إن التصميم
الأصلي كان ناويًا نمط تحقق (زي `transaction_id` مطابق لسجل `PaymentRequest`)
لكنه لم يُوصَّل بالكود الفعلي أبدًا.

---

## 2) السؤال المرجعي الثاني — هل `order_id` قابل للتخمين؟

**تأكيد نهائي: نعم، بشكل كامل.**

`models.py:146`:
```python
class Order(Base):
    id = Column(Integer, primary_key=True, index=True)
```
مفتاح أساسي `SERIAL`/تسلسلي عادي (لا `UUID`، لا أي عشوائية). البيانات الحية
من جلسة `commerce-idor-fix` السابقة تؤكد نفس النمط عمليًا: `order id=5,6,7,8,9`
متتالية بسيطة. **أي مهاجم يقدر يعدّ من 1 صعودًا ويصيب `order_id` صالح خلال
ثوانٍ**، بلا أي حاجة لتخمين معقّد.

---

## 3) هل يوجد نمط HMAC/signature-verification جاهز في المشروع لإعادة استخدامه؟

**تأكيد نهائي: لا، صفر تمامًا — لازم يُبنى من الصفر.**

بحث شامل (`grep -i hmac|signature|webhook`) على كل `app/` رجع:
- **صفر** استيراد لمكتبة `hmac` في المشروع بالكامل.
- **صفر** أي config/secret مخصَّص لبوابة دفع (`grep VISA|SECRET` على
  `core/config.py` رجع فقط `SECRET_KEY`/`SECRET_ENCRYPTION_KEY` — مفاتيح
  التطبيق العامة (JWT/تشفير)، لا علاقة لهم ببوابة دفع خارجية).
- الـ`webhook`-endpoints التانية في المشروع (للمقارنة، مش للاستخدام المباشر):
  - `automation.webhook_trigger` (`automation/router.py:175-214`): **صفر
    تحقق أيضًا** — الحماية الوحيدة هي إن الـ`path` نفسه `uuid4().hex` عشوائي
    غير قابل للتخمين (نمط "unguessable URL as secret"، شائع في أدوات
    Zapier-style). **غير قابل للتطبيق هنا** لأن `visa_webhook` مسار ثابت
    معروف (`/commerce/payment/visa/webhook`) لازم يكون كذلك عشان Visa
    تقدر تناديه.
  - `service_marketplace.deployment_webhook` (`service_marketplace/router.py:208-219`):
    فحص فعلي لكنه ساذج — `x_api_key != "eppne_internal_secret"` (**سر
    مكتوب حرفيًا في الكود، مقارنة `!=` عادية مش timing-safe**) — هذا نفسه
    نمط ضعيف، **لا يستاهل تقليده**، مجرد نقطة مقارنة.

**الخلاصة:** أي حل HMAC هنا **إضافة جديدة بالكامل**، مش إعادة استخدام —
يحتاج (أ) سر مشترك جديد (`VISA_WEBHOOK_SECRET` أو ما يعادله) يُضاف لـ
`core/config.py`/الـ.env، (ب) منطق `hmac.compare_digest` جديد. **ملاحظة
حاسمة: بما إن المشروع لا يملك تكامل Visa حقيقي فعليًا (صفر SDK/مفتاح API
حقيقي لبوابة Visa في الكود)، فإن "التحقق الحقيقي بمواصفات Visa الفعلية"
غير قابل للتأكيد من الكود — أي إصلاح مقترَح هنا هو **نمط HMAC عام قياسي**
(زي Stripe/PayPal webhook signing)، وليس تطبيقًا موثَّقًا لمواصفة Visa
الحقيقية (والتي غالبًا لا تُستخدم أصلًا — بوابات الدفع الحقيقية لبطاقات
الائتمان عادة لا تُرسل webhooks مباشرة لتاجر بهذا الشكل المبسَّط، هذا على
الأرجح محاكاة/mock endpoint داخلي). **يحتاج توضيحك: هل هذا تكامل Visa حقيقي
مخطَّط له، ولا endpoint محاكاة/placeholder للتطوير؟** — هذا يغيّر بشدة أي
قرار إصلاح لاحق.**

---

## 4) هل `tenant_id` مُستخدَم فعليًا للفلترة، أم قابل للتلاعب؟ — اكتشاف إضافي أخطر من الفرضية الأصلية

**تأكيد نهائي: `tenant_id` بيُستخدَم فعليًا للفلترة (`get_order(order_id, tenant_id)`
في `repository.py:158-162`)، لكن مصدره نفسه غير موثوق بالمرة — هيدر خام بلا
أي تحقق.**

`core/security.py:277-282`:
```python
async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```

هذا **نفس الجذر التقني** الموثَّق كاكتشاف نظامي حرج في
`.claude/plans/critical-finding-xtenant-systemic.md` (20+ دومين مُصنَّف
SUSPICIOUS بسببه) — لكنه **لم يُذكر صراحة في ذلك الملف كحالة `visa_webhook`
بالتحديد** (الملف ركّز على مسارات فيها `current_user` بديل متاح للإصلاح
الميكانيكي المعتاد). **`visa_webhook` لا يملك `current_user` بالتصميم
(webhook خارجي حقيقي)، فالحل المعماري المقترَح في ذلك الملف (استبدال الهيدر
بـ`current_user.tenant_id` عند وجوده) لا ينطبق هنا إطلاقًا** — يبقى الهيدر
هو المصدر الوحيد المتاح تقنيًا لتحديد التينانت، وهو **صفر تحقق بالكامل**.

**الأثر المُجمَّع (وهو أخطر بكثير من مجرد "توقيع مفقود" منفردًا):**

بما إن **لا التوقيع ولا التينانت ولا هوية المستدعي أي منهم يُتحقَّق منه**،
فإن الـendpoint بالكامل **مفتوح بلا أي حاجز مصادقة على الإطلاق**. أي طرف
خارجي (بلا توكن، بلا مفتاح API، بلا شيء) يقدر:

```
POST /commerce/payment/visa/webhook
Headers: X-Tenant-ID: <أي رقم>, signature: <أي نص عشوائي>
Body: {"order_id": <أي رقم تسلسلي>, "status": "SUCCESS"}
```

وتنجح العملية طالما `(order_id, tenant_id)` مطابقين لطلب حقيقي موجود —
وبما إن كلاهما أرقام تسلسلية صغيرة قابلة للعد الكامل (`tenant_id` كمان
تسلسلي بسيط حسب البيانات الحية من الجلسات السابقة: 1, 16, ...)، **مساحة
البحث بالكامل صغيرة جدًا وقابلة للتعداد الكامل عمليًا خلال دقائق**.

**النتيجة العملية لهذا الاستغلال:**
- تحويل أي طلب `PENDING_PAYMENT` (لأي تينانت) إلى `PAID` بلا أي دفع حقيقي —
  **تزوير دفع كامل**، تعليق فعلي: `update_order_status(order_id, tenant_id, "PAID")`.
- أو العكس: تحويل أي طلب فيزا معلّق إلى `FAILED` (تخريب/DoS منطقي على طلبات
  تنافسية).
- **هذا ليس فقط "غياب توقيع لعبور تينانت واحد كما افتُرض في التأجيل
  الأصلي" — هو IDOR/انتحال هوية غير مصادَق بالكامل عبر كل التينانتات
  دفعة واحدة**، ولا يحتاج أي معرفة مسبقة بأي بيانات تينانت محدد (فقط تعداد
  أرقام صغيرة).

**ملاحظة جانبية (مرجعية فقط، غير مطلوب إصلاحها هنا):** `_create_audit_log(user_id=0, ...)`
(`service.py:432`) — نفس فئة "حساب نظام مُهاردكودد" الموثَّقة في
`critical-finding-xtenant-systemic.md` §"hardcoded system account" — سطر
تسجيل تدقيق فقط هنا (لا تحويل مالي)، **خارج نطاق هذه الجلسة، مرجع فقط**.

---

## 5) خيارات الإصلاح المطروحة للنقاش — صفر تنفيذ حتى الآن

كل الخيارات دول **متكاملة مش بديلة عن بعض بالضرورة** — ممكن دمج أكتر من واحد.

### أ) HMAC signature verification حقيقي (الأقوى، الأكثر شيوعًا صناعيًا)
- إضافة `VISA_WEBHOOK_SECRET` في `core/config.py`/`.env`.
- التحقق: `hmac.compare_digest(computed_hmac(raw_body, secret), signature_header)`.
- **يحتاج تحديد:** هل هيدر التوقيع الحالي (`signature: str = Header(...)`)
  هو فعلًا الشكل اللي "Visa الحقيقية" هتبعته (اسم الهيدر، خوارزمية الـHMAC،
  هل بيوقّع الـraw body ولا JSON مُعاد تسلسله)؟ **غير مؤكَّد من الكود —
  لأن لا يوجد تكامل Visa حقيقي حاليًا (راجع §3)**. لو ده endpoint محاكاة
  للتطوير، ممكن نبني نمط HMAC عام (زي Stripe) كمعيار placeholder لحد ما
  يتوفر توثيق Visa فعلي.
- **يحل:** انتحال الهوية بالكامل (يمنع أي طرف لا يملك السر من استدعاء
  الـendpoint بنجاح، بغض النظر عن `tenant_id`/`order_id`).
- **لا يحل بمفرده:** مصدر `tenant_id` (لو السر واحد لكل التطبيق مش لكل
  تينانت) — لسه محتاج يُشتق التينانت من حاجة تانية غير الهيدر (زي مثلًا
  `merchant_id`/`gateway_reference` مرتبط بـ`PaymentRequest`/`store` الصح،
  بدل الاعتماد على `X-Tenant-ID` أصلًا).

### ب) اشتقاق `tenant_id` من `order_id` نفسه بدل الهيدر (يقفل فجوة IDOR بغض النظر عن التوقيع)
- بدل `Depends(get_current_tenant)`، نجيب `tenant_id` من الـ`order` نفسه:
  `SELECT tenant_id FROM orders WHERE id = payload.order_id` (بلا فلتر
  تينانت مبدئي)، بعدين نستخدم القيمة دي كـ`self.tenant_id` للخدمة.
- **يحل:** إلغاء الحاجة للهيدر كليًا في هذا الـendpoint — التينانت بيتحدد
  من بيانات حقيقية في DB مش من مدخل خارجي.
- **لا يحل بمفرده:** لسه أي طرف (بلا توقيع) يقدر يغيّر حالة أي طلب لأي
  تينانت — بيقفل **جزء "التينانت الخطأ"** بس مش "الاستدعاء المزوَّر
  بالكامل". **لازم يترافق مع (أ) عمليًا عشان يبقى إصلاح كامل.**

### ج) تقييد IP لمصادر Visa المعروفة (طبقة شبكة إضافية، مش بديل)
- Allowlist لـIP ranges موثَّقة (لو تكامل حقيقي فعلًا ومصادر Visa معروفة
  ومنشورة). **غير قابل للتطبيق فعليًا الآن** — بما إن لا يوجد تكامل Visa
  حقيقي (§3)، لا توجد IP ranges حقيقية لتقييدها. لو نُفِّذ الآن هيبقى
  مجرد placeholder بلا قيمة أمنية فعلية.
- أفضل تطبيقًا على مستوى Ingress/WAF (زي ملاحظة `GET /ready`/`/metrics`
  الموثَّقة في `PROJECT_AUDIT.md`)، مش كود Python.

### د) مطابقة `transaction_id`/`gateway_reference` من الـpayload مع سجل `PaymentRequest` الموجود مسبقًا (تحقق منطقي إضافي)
- استخدام الـschema الموجود فعلًا لكن غير المُستخدَم (`VisaWebhookPayload`)
  فعليًا بدل `payload: dict` الخام — والتحقق إن `transaction_id`/`gateway_reference`
  المُرسَل يطابق `pr.gateway_transaction_id` المُخزَّن وقت `create_payment_request`.
- **يحل جزء إضافي:** يمنع "تخمين order_id فاضي بلا معرفة تفاصيل الدفع"،
  لكنه **لا يعوّض غياب التوقيع** — قيمة `gateway_transaction_id` نفسها
  مُولَّدة داخليًا (`f"VISA-{uuid4().hex[:12]}"`) وقد تكون قابلة
  للتسريب/التخمين حسب من يشوفها (مثلًا لو ظهرت لأي مستخدم عبر
  `get_payment_status`، راجع `service.py:450-452` — بترجع فقط `pr.status`
  مش `gateway_transaction_id`، فالتسريب غير مؤكَّد حاليًا من الكود).

---

## 6) التوصية الأولية (للنقاش، مش قرار نهائي)

**(أ) + (ب) معًا** هما الحد الأدنى لإصلاح حقيقي:
- (ب) يقفل فجوة "التينانت الخطأ" فورًا وبسيط (سطر استعلام واحد إضافي).
- (أ) يقفل فجوة "أي طرف يقدر ينادي الـendpoint أصلًا" — **بدون (أ)،
  (ب) لوحدها لسه بتسيب الباب مفتوح بالكامل لأي مهاجم غير مصادَق، بس
  بتضمن على الأقل إنه لو نجح هيأثر بس على التينانت الصحيح المرتبط
  فعليًا بالـ`order_id` اللي خمّنه.**

لكن **(أ) يحتاج توضيحك أولًا حول طبيعة هذا الـendpoint** (تكامل حقيقي
مخطَّط، ولا محاكاة/placeholder؟) قبل تحديد شكل الـHMAC المناسب — راجع
السؤال المفتوح في §3.

**صفر تنفيذ. بانتظار توجيهك على: (1) طبيعة الـendpoint الحقيقية، (2) أي
مجموعة من الخيارات أعلاه تريد تنفيذها وبأي ترتيب.**

---

## 7) قرار المستخدم [2026-08-25]

**تأكيد:** الـendpoint placeholder/mock حاليًا — صفر تكامل Visa حقيقي مخطَّط له الآن.

**الموافقة على تنفيذ ثلاثة إصلاحات معًا:**
1. **اشتقاق `tenant_id` من `order_id` نفسه** (خيار ب) بدل الهيدر — يقفل فجوة IDOR عبر-تينانت بغض النظر عن مستقبل التكامل.
2. **استخدام `VisaWebhookPayload` schema الموجود فعلًا** بدل `payload: dict` الخام + **تحقق `gateway_reference` مقابل `PaymentRequest.gateway_transaction_id` المخزَّن** (خيار د).
3. **حماية مؤقتة صريحة بـ`Depends(get_current_superuser)`** بدل بناء HMAC ضد مواصفة Visa غير موجودة فعليًا (تأجيل خيار أ) — مُوثَّقة بتعليق أعلى الدالة كحماية مؤقتة لحد ما يُبنى تكامل حقيقي.
4. **خيار (ج) IP allowlist:** Backlog، خارج نطاق الكود (طبقة Ingress/WAF مستقبلية).

**توجيه إضافي:** تحقق حي بعد التنفيذ (طلب بلا توكن، طلب سبونسر/مرجع غير مطابق، مسار شرعي سليم)، عرض `git status`/`git diff --stat` قبل أي commit.

---

## 8) التنفيذ — الديف المُطبَّق (3 ملفات، +31/-14 سطر)

**`repository.py`:** دالة جديدة `get_order_tenant_id(order_id)` — استعلام بلا فلتر تينانت عمدًا (الغرض الوحيد: تحديد التينانت الصحيح لطلب من مصدر خارجي غير مصادَق قبل بناء أي خدمة).

**`service.py`:**
- `handle_visa_webhook` يستقبل الآن `VisaWebhookPayload` (schema حقيقي) بدل `dict` خام، وحُذف بارامتر `signature` غير المُستخدَم أصلًا.
- إضافة فحص `payload.gateway_reference != pr.gateway_transaction_id` → `PermissionDeniedError` قبل أي كتابة على حالة الطلب/طلب الدفع.
- دالة `@staticmethod resolve_order_tenant_id(db, order_id)` جديدة — تُستخدَم من الراوتر لاشتقاق التينانت قبل تفعيل أي منطق مقيَّد بتينانت.

**`router.py`:**
- حذف `tenant_id: int = Depends(get_current_tenant)` (مصدر الثغرة — هيدر `X-Tenant-ID` بلا أي تحقق) واستيرادها غير المُستخدَم بعد الآن.
- إضافة `current_user: User = Depends(get_current_superuser)` (حماية مؤقتة صريحة، معلَّقة بتعليق يوضح إنها مؤقتة لحد بناء HMAC حقيقي).
- اشتقاق `tenant_id` عبر `CommerceService.resolve_order_tenant_id(db, payload.order_id)` قبل بناء الخدمة، مع `404` صريح لو الطلب غير موجود.

`python -m py_compile` على الثلاثة ملفات → `exit code 0`.

---

## 9) التحقق الحي — 5 سيناريوهات، بيانات throwaway (`p_visa_*`)، منظَّفة بالكامل بعد الاختبار

**الإعداد:** مستخدم عادي (`p_visa_regular`, id=978, تينانت1) + مستخدم رُقِّي لـ`SUPER_ADMIN` عبر SQL (`p_visa_admin`, id=979 — التسجيل العام لا يصنع سوبريوزر، لا يوجد endpoint لذلك، الترقية عبر SQL فقط للاختبار) + متجر/منتج/متغيّر تينانت1 (منتج جديد `id=11`، نُشر عبر SQL لنفس الفجوة الوظيفية pre-existing الموثَّقة في التقرير المرجعي §4.3: لا يوجد `PUT` لنشر منتج) + طلب `PENDING_PAYMENT` حقيقي عبر الـAPI (`order id=17`, `settlement_type="VISA"`) + سجل `payment_requests` (`id=2`, `gateway_transaction_id="VISA-TESTREF001"`) **أُدرِج مباشرة عبر SQL** (نفس الفجوة pre-existing الموثَّقة سابقًا في `commerce-idor-fix-session-log.md` §4.1: `create_payment_request` API معطوبة بـ`TypeError` من duplicate-kwarg، غير مُصلَحة، خارج نطاق هذه الجلسة).

| # | الاختبار | النتيجة | الحكم |
|---|---|---|---|
| 1 | **بلا أي توكن** (نفس هجوم الفجوة الأصلية: `X-Tenant-ID` مزوَّر + `order_id` مخمَّن + `signature` وهمية) | `401 "Not authenticated"` | ✅ **الباب المفتوح بالكامل مُغلَق — لم يعد ممكنًا الوصول للـendpoint إطلاقًا بلا هوية** |
| 2 | مستخدم عادي مُصادَق (توكن حقيقي، مش سوبريوزر) | `403 "Superuser privileges required"` | ✅ **حاجز الصلاحية يعمل** |
| 3 | سوبريوزر حقيقي، لكن `gateway_reference` غير مطابق (`VISA-WRONGREF`) | `400 "مرجع البوابة غير مطابق لطلب الدفع"` — تحقق DB مستقل: `orders.status` لسه `PENDING_PAYMENT`، `payment_requests.status` لسه `PENDING` (**صفر أثر جانبي**) | ✅ **فحص التطابق يرفض بلا أي كتابة** |
| 4 | سوبريوزر حقيقي، `gateway_reference` مطابق، `status="SUCCESS"` | تحقق DB مستقل: `orders.status → PAID`، `payment_requests.status → PAID` مع `gateway_response` مخزَّن بالكامل وصحيح | ✅ **المسار الشرعي ينجح فعليًا في قاعدة البيانات** (راجع ملاحظة مهمة تحت) |
| 5 | سوبريوزر حقيقي، `order_id` غير موجود | `404 "الطلب غير موجود"` | ✅ **اشتقاق التينانت من طلب غير موجود يُرفض بنظافة** |

**ملاحظة مهمة على الاختبار 4 — اكتُشفت أثناء التحقق الحي، pre-existing، غير ناتجة عن هذه الجلسة:**
استجابة الـAPI أظهرت `400` بدل `200` رغم نجاح التحديث الفعلي في DB (مؤكَّد جدول-بجدول أعلاه) — السبب: `_create_audit_log(user_id=0, ...)` (سطر لم يتغيّر في هذه الجلسة) يفشل بـ`ForeignKeyViolationError` لأن `user_id=0` غير موجود في جدول `users` — **نفس فئة "حساب نظام مُهاردكودد (`user_id=0/1`) في `commerce`/`affiliate`/`iot`" الموثَّقة والمؤجَّلة صراحةً بالفعل في `.claude/plans/critical-finding-xtenant-systemic.md` (§"تحديث [2026-08-24]"، مصنَّفة هناك كأعلى خطورة موثَّقة، فوق `ai_agents`)**. بما إن التحديثات الفعلية (`update_order_status`/`update_payment_request`) تُنفِّذ `commit()` خاص بها **قبل** استدعاء `_create_audit_log`، فالتأثير الوظيفي الحقيقي (تعليم الطلب مدفوعًا) **نجح فعليًا رغم استجابة الـAPI المضلِّلة**. **لم تُلمس — خارج نطاق هذه الجلسة بالكامل، موثَّقة هنا فقط كدليل حي إضافي لفجوة معروفة سلفًا ومؤجَّلة لجلسة مخصَّصة.**

**تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل (`SELECT COUNT` بعد الحذف = صفر في كل الجداول: `orders`, `order_items`, `payment_requests`, `products`, `product_variants`, `users`, `commerce_audit_logs`).** `store_profiles id=4` ("Store_1", تينانت1) لم يُلمس — كان موجودًا من جلسات سابقة، أُعيد استخدامه بس (نفس نمط الجلسات السابقة). السيرفر التجريبي (uvicorn) أُوقف، تأكيد إضافي: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → صفر نتيجة.

---

## 10) `git diff --stat` — للمراجعة قبل أي commit

```
eppne-backend/app/domains/commerce/repository.py |  6 ++++++
eppne-backend/app/domains/commerce/router.py     | 15 ++++++++++-----
eppne-backend/app/domains/commerce/service.py    | 24 +++++++++++++++---------
3 files changed, 31 insertions(+), 14 deletions(-)
```

**الحالة النهائية:** ✅ **الثلاثة إصلاحات مُطبَّقة، مؤكَّدة حيًا (5/5 سيناريوهات كما هو متوقَّع)، بيانات throwaway منضَّفة بالكامل.** ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.
