# #37 (`finance-transfer-payment-tx-hash-broken`) — اكتشاف: الأربعة مواضع كلهم محجوبين قبل ما يوصلوا للباج نفسه

**تاريخ:** 2026-08-28
**الحالة:** 🔴 توقفت قبل أي تعديل كود — اكتشاف يغيّر خطة التحقق المتفق عليها، محتاج قرارك.

---

## الملخص

قرأت الكود الفعلي للأربعة مواضع (مش بس الوصف في `constructor-mismatch-backlog-classification.md`).
النتيجة: **الباج نفسه (تخزين كائن `Transaction` بدل `.tx_hash` نصي) مؤكَّد بصريًا في الأربعة**، لكن
**كل موضع من الأربعة محجوب بباج منفصل تمامًا يمنع الوصول للسطر بتاع `tx_hash` أصلًا** — يعني
مفيش ولا موضع واحد فيهم ممكن يتحقَّق منه حيًا **end-to-end عبر الـservice method العامة** من غير
ما نلمس/نتحايل على باج تاني غير متعلق.

---

## التفصيل — موضع بموضع

| الموضع | سطر الباج المؤكَّد | الحاجب اللي يسبقه | نوع الحاجب |
|---|---|---|---|
| `realestate.buy_fractional_ownership` | `service.py:262` — `purchase_tx_hash=tx_hash` (`repo.create_ownership`) | `service.py:239` — نداء `ai.execute_agent_action(..., tenant_id=tenant_id, ...)` بالتوقيع القديم | **#40** (`realestate-ai-agents-execute-agent-action-stale-signature`) — موثَّق مسبقًا، مؤجَّل لقائمة "قرارات تصميمية" في خطتك |
| `insurance.review_claim` (مسار `approve=True`) | `service.py:475` — `payout_tx_hash=payout_tx` (`repo.update_claim`) | `service.py:431` — `if policy.issuer_entity_id != reviewer_id: raise PermissionDeniedError` | **#41** (`insurance-review-claim-issuer-entity-id-reviewer-id-mismatch`) — موثَّق مسبقًا، مؤجَّل لنفس القائمة، وعندها تحذير أمني إضافي بطلبك |
| `tourism_sports.book_program` | `service.py:179` — `payment_tx_hash=tx_hash` (`repo.create_program_participant`) | `service.py:133` — `_check_saas_limits(tenant_id, "tourism")` (كود **"tourism"**، مش "tourism_sports") | **اكتشاف جديد اليوم**، نفس فئة اكتشاف #28 الجانبي — كود "tourism" مش موجود في `saas_service_catalog` |
| `transport.pay_delivery` | `service.py:531` — `payment_tx_hash=tx_hash` (`UPDATE DeliveryTask`) | جداول `transport` غير موجودة في الـDB أصلًا | **#39** (`transport-domain-tables-never-migrated`) — معروف مسبقًا، ده اللي كنت متوقَّع أصلًا يبقى فحص كود بس |

**يعني:** بدل "3 مواضع تحقق حي كامل + موضع واحد فحص كود"، الواقع بعد قراءة الكود هو **4 مواضع
كلهم محتاجين تعامل خاص عشان يوصلوا حتى لنقطة اختبار الباج المستهدف.**

---

## اكتشاف إضافي مهم — `tourism_sports.book_program` بيستخدم كود مختلف عن اللي أضفته في #28

`_check_saas_limits` الافتراضي في `tourism_sports/service.py` هو `"tourism_sports"`، لكن
`book_program` تحديدًا بتنادي بكود **`"tourism"`** صراحة (`service.py:133`) — كود مختلف تمامًا
عن الافتراضي وعن الكود اللي أضفته في #28. يعني حتى لو كنت وسَّعت #28 يشمل `tourism_sports`
(زي ما كان مقترح كاختيار)، ده **مكانش هيحل حاجب `book_program` تحديدًا** — لازم كود `"tourism"`
نفسه (أو تصحيح الكود الممرَّر في السطر ده، لو ده باج تسمية منفصل كمان).

---

## الخيارات المتاحة لكل موضع (بلا تنفيذ حتى الآن)

### `realestate` و`insurance` (محجوبين بـ#40/#41 — بنود مؤجَّلة صراحة بقرارك في الجلسة السابقة)
- **(أ)** اختبار على مستوى الـrepository مباشرة (تجاوز الـservice method كليًا) — أثبت إن
  `.tx_hash` (مش الكائن الكامل) بيتخزَّن صح في العمود، بمعزل تام عن #40/#41. **هيثبت إصلاح #37
  نفسه بدقة، لكنه مش "تحقق حي end-to-end عبر الـAPI/الـservice الحقيقية".**
- **(ب)** `monkeypatch` مؤقت **للفحص المحجوب فقط** (نفس السابقة اللي استُخدمت في جلسة #9:
  "بلا أي `monkeypatch`" كان هدف مثالي لكنه اتقبل جزئيًا وقتها) — يسمح بالوصول لسطر `tx_hash`
  عبر الـservice method الحقيقية، بصفر لمس على منطق #40/#41 نفسه.
- **(ج)** بيانات throwaway مصمَّمة عمدًا تتفادى الحاجب (زي: تعيين `reviewer_id` = نفس رقم
  `issuer_entity_id` بالصدفة المتعمَّدة لـinsurance) — ممكن لـ`insurance` (رقم واحد يتوافق)،
  **مش ممكن عمليًا لـ`realestate`** (لازم تصحيح توقيع `execute_agent_action` نفسه، مش مجرد قيمة).
- **(د)** تأجيل التحقق الحي للاثنين دول لحد ما #40/#41 يتصلحوا (يعني #37 يتصلح كودًا الآن، لكن
  التحقق الحي الكامل بيتأجّل)، ونكتفي دلوقتي بمراجعة كود دقيقة + تحقق "تراجع نظيف" (نفس مستوى
  التحقق اللي قُبل سابقًا لنفس الدالتين بالضبط في جلسة #9).

### `tourism_sports.book_program`
- **(أ)** إضافة كود `"tourism"` لـ`saas_service_catalog` كمان (توسيع فعلي لـ#28، خارج الأربعة
  أكواد اللي وافقت عليها أصلًا) — بيانات فقط، صفر كود، نفس مخاطرة #28 المنخفضة.
- **(ب)** نفس خيارات (أ)/(ب)/(ج) فوق (repo مباشرة / monkeypatch / تأجيل).

### `transport.pay_delivery`
نفس معاملة #18 بالضبط (فحص سورس كود فقط + تأكيد التوقيع، بلا تحقق حي — الجداول مش موجودة).
هعلّمه بنفس التحفظ الموثَّق هناك.

---

## السؤال

إزاي تحب تتعامل مع `realestate`/`insurance`/`tourism_sports`؟ الخيارات اللي أميل ليها كأقل
مخاطرة وأعلى دقة:
- **`tourism_sports`:** أضيف كود `"tourism"` لـ`saas_service_catalog` (توسيع بسيط لـ#28، بيانات
  بس) عشان أقدر أتحقق حيًا end-to-end زي ما كان مخطَّط أصلًا.
- **`realestate`/`insurance`:** أستخدم تحقق على مستوى الـrepository مباشرة (خيار أ) لإثبات إصلاح
  #37 نفسه بدقة كاملة، بمعزل عن #40/#41 (بلا `monkeypatch` وبلا تأجيل) — وأوثّق بوضوح إن التحقق
  ده مش end-to-end كامل عبر الـservice، نفس نمط "تحفظ موثَّق" اللي طبَّقناه مع #18/`transport`.

**موافق على المنهج ده، ولا تفضّل حاجة تانية (monkeypatch / تأجيل / حاجة تانية)؟**
