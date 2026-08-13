# 🔴🔴🔴 كشف بيانات مالية غير مصادَق عليه — `sovereign_entities` public endpoints

**تاريخ الاكتشاف:** 2026-08-13
**اكتُشف أثناء:** جلسة إصلاح `SimpleTenant` (`.claude/reports/simpletenant-fix-session-log.md`) — هذا اكتشاف منفصل تمامًا عن `SimpleTenant`، يستحق تقرير قائم بذاته بأولوية تصعيد فورية أعلى من أي عمل آخر في هذه الجلسة أو الجلسات السابقة.
**الحالة: 🔴 صفر إصلاح تم. توثيق فقط.**

---

## 1) الأربعة endpoints بالضبط (file:line، `eppne-backend/app/domains/sovereign_entities/router.py`)

| # | Endpoint | التوقيع | السطر |
|---|---|---|---|
| 1 | `GET /api/sovereign-entities/` (`list_entities`) | بلا `current_user` في التوقيع إطلاقًا | 41-48 (`tenant_id: int = Depends(get_current_tenant)` سطر 46) |
| 2 | `GET /api/sovereign-entities/{entity_id}` (`get_entity`) | بلا `current_user` في التوقيع إطلاقًا | 72-77 (`tenant_id: int = Depends(get_current_tenant)` سطر 75) |
| 3 | `GET /api/sovereign-entities/templates` (`list_templates`) | بلا `current_user` في التوقيع إطلاقًا | 339-343 (`tenant_id: int = Depends(get_current_tenant)` سطر 341) |
| 4 | `GET /api/sovereign-entities/components` (`list_components`) | بلا `current_user` في التوقيع إطلاقًا | 349-353 (`tenant_id: int = Depends(get_current_tenant)` سطر 351) |

كل الأربعة بتاخد `tenant_id` **حصريًا** من هيدر `X-Tenant-ID` (عبر `api/deps.py:148-153`'s `get_current_tenant()`)، بلا أي مقارنة مع هوية الطالب الحقيقية — صفر ربط بـ`current_user.tenant_id` لأنه مش موجود أصلًا في توقيع أي من الأربعة.

**الاستعلامات فعليًا مفلترة بـ`tenant_id` على مستوى SQL** (مش bug من نوع "بترجع الجدول كامل") — المشكلة إن مصدر قيمة الفلتر نفسها غير موثوق:

```python
# repository.py:63-76 — list_entities
query = select(SovereignEntity).where(
    and_(SovereignEntity.tenant_id == tenant_id, SovereignEntity.is_deleted == False)
)
```
نفس النمط بالحرف في `get_entity` (`repository.py:26-36`), `list_templates` (`:283-285`), `list_components` (`:287-289`).

---

## 2) مستوى المصادقة الحقيقي المطلوب (مُصحَّح بعد اختبار حي — **ليس** "بلا أي مصادقة")

`app/main.py:300-305` بيلف **كل** الـ30 router (شامل هذا الدومين) بـ`Depends(require_sector(sector))` على مستوى تسجيل الراوتر نفسه، قبل أي `Depends` خاص بالـendpoint. `require_sector` (`core/security.py:205-226`) بتستخدم `Depends(get_current_active_user)` داخليًا — **يعني توكن JWT صالح مطلوب كحد أدنى**، مؤكَّد حيًا:

```
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/sovereign-entities/2
401
```

**لكن** أي مستخدم عادي (`system_role=USER`) هيترفض دايمًا من `require_sector` نفسها (لأن `identity/service.py`'s `_issue_tokens` مش بيبعت `sector` claim لأي حد، موثَّق مسبقًا في `critical-finding-xtenant-systemic.md`) — **الاستثناء الوحيد اللي بيعدّي هو `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`** (`security.py:215-216`).

**الخلاصة: الاستغلال محصور في حساب `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` — مش أي زائر مجهول.**

---

## 3) مثال curl فعلي — الحالة الحالية (latent، مش live، وده مهم)

**بيانات throwaway الجلسة (حقيقية، مُستخدَمة فعلًا في الاختبار):**
- User B: `p_academy_b`، `SUPER_ADMIN`، تينانت حقيقي = **14**
- Entity id=**2** ("p_sovereign_entity_A")، تينانت حقيقي = **1** (تينانت مختلف تمامًا عن يوزر B)

```bash
# User B (SUPER_ADMIN, تينانت حقيقي=14) يحاول قراءة كيان بيتبع تينانت1
# عبر هيدر مزوَّر — لا علاقة له بتينانته الحقيقي
curl -s http://127.0.0.1:8000/api/sovereign-entities/2 \
  -H "Authorization: Bearer <TOKEN_USER_B_TENANT_14>" \
  -H "X-Tenant-ID: 1"
```

**النتيجة الفعلية الآن (مؤكَّدة حيًا، مش نظرية):**
```
HTTP 500
sqlalchemy.exc.DBAPIError: DataError: invalid input for query argument $2:
<app.api.deps.SimpleTenant object at 0x...> ('SimpleTenant' object cannot be interpreted as an integer)
[SQL: SELECT ... FROM sovereign_entities_v2 WHERE id = $1::INTEGER AND tenant_id = $2::INTEGER ...]
[parameters: (2, <SimpleTenant object>)]
```
(نفس السلوك تأكَّد حيًا لـ`list_entities` أيضًا — `GET /api/sovereign-entities/?limit=5` بنفس الهيدر/التوكن رجّع `500` بنفس السبب.)

### 🔴 لماذا هذا مهم: الثغرة "كامنة" حاليًا، مش "حية" — والسبب عارض

الأربعة endpoints **لسه فيهم نفس باج `SimpleTenant`** (الكائن الخام بيتبعت كـbind parameter مباشر بدل `.id`) — **استُثنيت عمدًا من إصلاح `SimpleTenant` المُطبَّق على باقي المشروع في هذه الجلسة، بانتظار قرار تصميمي بخصوص مصدر المصادقة نفسه** (راجع `simpletenant-fix-session-log.md`). **الكراش الحالي (غير متعلق بالسؤال الأمني إطلاقًا) هو اللي بيمنع الاستغلال الفعلي الآن — مش أي حماية مقصودة.**

**بمجرد ما حد يصلح كراش `SimpleTenant` ده بالطريقة الميكانيكية البديهية المطبَّقة في كل مكان تاني بالمشروع (`tenant_id.id` بدل الكائن الخام)** — وده إصلاح سطر واحد سهل الوقوع فيه بدون انتباه لعمق المشكلة — **الاستغلال هيشتغل فورًا**، لأن مفيش أي فحص يربط تينانت الطالب الحقيقي (`current_user.tenant_id`) بالتينانت المطلوب (`X-Tenant-ID`). **هذا يفرّق الاكتشاف ده جوهريًا عن كل أمثلة `SimpleTenant` التانية** (اللي إصلاحها بيقفل الثغرة الأمنية تلقائيًا بنفس الحركة) — **هنا إصلاح الكراش وحده هيفتح ثغرة تسريب مالي/KYB cross-tenant، مش يقفلها**، ما لم يُضاف فحص `current_user.tenant_id` في نفس وقت إصلاح النوع.

---

## 4) الحقول الحساسة المكشوفة بالضبط (`schemas.py`)

`SovereignEntityResponse` (المُرجَعة من `list_entities`/`get_entity`) — `schemas.py:55-64`، وراثةً من `SovereignEntityCreate` (`schemas.py:12-29`):

| الحقل | السطر | الحساسية |
|---|---|---|
| `treasury_balance_mrusdt` | 58 | **رصيد الخزينة المالي الفعلي للكيان (Decimal)** |
| `kyb_status` | 59 | حالة التحقق من الهوية المؤسسية (KYB) |
| `created_by` | 61 | معرف المستخدم المُنشئ (تسريب معرف داخلي) |
| `official_email` | 21 (موروث) | البريد الإلكتروني الرسمي للكيان |
| `tax_id` | 17 (موروث) | الرقم الضريبي |
| `registration_number` | 16 (موروث) | رقم التسجيل التجاري |
| `wallet_address` | 24 (موروث) | عنوان محفظة العملة الرقمية (`0x...`) |
| `legal_name`, `official_phone`, `address`, `city`, `country_of_origin` | 14, 18-20, 22 (موروثة) | بيانات تعريفية/اتصال كاملة |

**`list_templates`/`list_components` بترجع قوالب ومكونات صفحات خاصة بالتينانت — أقل حساسية ماليًا، لكن نفس آلية التسريب بالضبط.**

---

## 5) التوصية

**لا تُصلَح الأربعة endpoints دول بنفس القاعدة الميكانيكية المستخدمة في باقي `SimpleTenant`** (`cast(int, current_user.tenant_id)`) **بدون قرار تصميمي واضح أولًا** — لأنه مفيش `current_user` في توقيعها، والقرار (endpoints عامة بتصميم مقصود تحتاج مصدر تينانت بديل، أم لازم تتحول لمحمية بـ`current_user` إجباري) قرار أمني/منتجي، مش تقني بسيط. **أي "إصلاح" سطحي لكراش `SimpleTenant` وحده، من غير معالجة السؤال ده، هيفتح ثغرة تسريب مالي/KYB حقيقية فورًا.**
