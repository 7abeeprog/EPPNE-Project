# جلسة: تحويل المواقع التسعة لحساب النظام الموحَّد (Phase 3)

**تاريخ:** 2026-08-24 → 2026-08-25
**المرجع:** `.claude/plans/tenant-system-account-design-vision.md` (§4 خريطة التحويل، §7 القرارات النهائية)
**البنية التحتية المُستخدَمة:** `app/core/system_account_service.py` — أُنشئت وتحقَّق منها حيًّا في Phase 2 (commit `edb5694`، غير مُعدَّل في هذه الجلسة إلا تعديل واحد لكسر دورة استيراد — راجع القسم 3).

**النطاق:** استبدال الأنماط الثلاثة الخطرة (رقم هاردكودد كـ`sender_id`، `tenant_id` مُفسَّر غلط كـ`user_id`، بريد ثابت غير مضمون كـ`receiver_email`) عبر 9 مواقع استدعاء في 7 دومينات بحساب النظام المركزي `get_or_create_system_account(db, tenant_id)`.

**النتيجة النهائية: 9/9 مواقع محوَّلة ومُتحقَّق منها حيًّا (7 بالكامل من طرف لطرف عبر الدالة الفعلية، 2 عبر تحقق معزول بسبب باج منفصل مؤكَّد يمنع التحقق الكامل — راجع القسم 4).**

---

## 1. جدول النتائج

| # | الموقع | القيمة القديمة | القيمة الجديدة | التحقق الحي |
|---|---|---|---|---|
| 1 | `commerce.release_commissions` | `sender_id=1` | حساب نظام التينانت (مُحمَّل مرة واحدة قبل الحلقة) | ✅ كامل — `TX-33D105A27E3D` |
| 2 | `affiliate.withdraw_commissions` | `sender_id=1` | حساب نظام التينانت | ✅ كامل — `TX-44DCF13DB123` |
| 3 | `iot.settle_carbon_credits` | `sender_id=1` | حساب نظام التينانت (بمتغير `tenant_id` المحلي، ليس `self.tenant_id`) | ✅ كامل — `TX-EDCFA482B7E8` |
| 4 | `social.subscribe_group_to_plan` | `sender_id=0` + `receiver_email="saas@eppne.com"` | `sender_id=group.creator_id` + حساب النظام كمستقبِل | ✅ كامل — `TX-38BAB6852D92` |
| 5 | `social.request_physical_gift` | `receiver_email="shop@eppne.com"` | حساب النظام | ✅ كامل — `TX-2E1F21F80ACF` |
| 6 | `saas.pay_invoice` | `sender_id=self.tenant_id` + `receiver_email="system@eppne.com"` | `sender_id=AcademyTenant.admin_id` + حساب النظام | ⚠️ منطق مُتحقَّق منه بشكل معزول فقط — راجع §4 |
| 7 | `saas.process_auto_renewals` | نفس نمط #6 بـ`target_tenant` | نفس الحل بـ`target_tenant` | ⚠️ نفس ملاحظة #6 |
| 8 | `projects.add_contribution` | `receiver_email="system@eppne.com"` | حساب النظام | ✅ كامل — `TX-96676F7EDA56` |
| 9 | `academy.enroll_in_course` | `receiver_email="academy@eppne.com"` | حساب النظام | ✅ كامل — `TX-5BA65D11CD01` |

**الثابت المحوري لكل اختبار:** محفظة المستخدم `id=1` (`wallet.id=39`، `p_system_treasury`، تينانت 1) — الضحية المحتملة لأي نمط `sender_id=1` القديم — رُصدت **قبل** كل الاختبارات (`{"MR_USDT": 875.0}`) وأُعيد فحصها **بعد** كل موقع من التسعة وبعد التنظيف النهائي: **لم تتغيّر إطلاقًا طوال الجلسة**.

---

## 2. القرار المعماري الجديد لموقع #4 (`subscribe_group_to_plan`)

مستند التصميم الأصلي (§4) اقترح "حذف `sender_id=0` بالكامل" — لكن `FinanceService.transfer()` يشترط `sender_id` إجباريًا بلا استثناء، فهذا الحل غير قابل للتنفيذ حرفيًا كما كُتب. أثناء التنفيذ، اكتُشف أن `SocialGroup.creator_id` (`social/models.py:143`، FK إجباري لـ`users.id`) يطابق تمامًا نمط `AcademyTenant.admin_id` المستخدَم بالفعل لحل نفس المعضلة في المواقع #6/#7 (§7 بند 4) — القرار المعتمَد: **منشئ المجموعة هو الدافع، حساب النظام هو المستقبِل**، بنفس منطق "استخدم حقل ملكية موجود بالفعل بدل اختراع مفهوم جديد".

---

## 3. اكتشاف تقني: دورة استيراد (circular import)

أول محاولة استيراد لكل الدومينات الثمانية فشلت:
```
core.security → saas.service.SaaSControlService
saas.service → core.system_account_service (بعد التحويل)
core.system_account_service → core.security.get_password_hash
```
**الحل:** نقل `from app.core.security import get_password_hash` داخل جسم الدالة `get_or_create_system_account` (استيراد مؤجَّل)، بدل استيراد على مستوى الموديول — نمط موجود بالفعل في المشروع (`iot/service.py`, `_get_tenant_admin_id` نفسها). لا تعديل آخر على `system_account_service.py` من Phase 2.

---

## 4. باجان منفصلان تمامًا اكتُشفا أثناء التحقق — يمنعان التحقق الكامل من طرف لطرف للموقعين #6/#7 فقط

### 4.1 `saas_invoices.idempotency_key` — انجراف مخطط (schema drift) حقيقي، سابق لهذه الجلسة

الموديل (`saas/models.py:138`) يُعرِّف `idempotency_key`، لكن الجدول الفعلي في قاعدة البيانات الحية **لا يملك هذا العمود إطلاقًا** (مؤكَّد بـ`\d saas_invoices`). النتيجة: **أي** `SELECT`/`INSERT` على `Invoice` عبر الـORM يفشل بـ`UndefinedColumnError` — مؤكَّد بتجربة مباشرة حتى مع `SELECT` مجردة بلا أي علاقة بتعديلات هذه الجلسة. يعني هذا أن `pay_invoice()` و`_generate_invoice()` (تُستدعى من `process_auto_renewals`) **كانتا معطَّلتين بالكامل قبل هذه الجلسة وبعدها على حدٍّ سواء** — لا علاقة لهذا العطل بتحويل حساب النظام.

**لم يُصلَح — خارج نطاق هذه الجلسة، يحتاج migration منفصلة (إضافة العمود الناقص) بموافقة صريحة.**

### 4.2 كيف تحقَّقنا من المنطق الجديد رغم الحجب

استُدعيت الدالتان الخاصتان الحقيقيتان (`SaaSControlService._get_tenant_admin_id`) و`get_or_create_system_account` و`FinanceService.transfer` مباشرة — بنفس المعاملات الحرفية التي يستخدمها `pay_invoice`/`process_auto_renewals` — بدون المرور بمسار `Invoice` المكسور:

```
_get_tenant_admin_id(16) -> 774   (الأدمن الحقيقي لتينانت 16، وليس 16 نفسها كما كان الباج القديم)
system_account لتينانت 16 -> 956  (نفس الحساب الذي أنشأته Phase 2)
transfer(sender_id=774, receiver_email=<system956>, amount=50) -> TX-A7ACCF01B33F، sender_id=774, receiver_id=956
```
محفظة `admin 774` انخفضت من 1000 إلى 950 MR_USDT، محفظة `النظام 956` زادت من 0 إلى 50 — دليل مباشر على صحة منطق الاستبدال، رغم استحالة تشغيل `pay_invoice()` الكاملة بسبب §4.1.

### 4.3 ثلاثة اكتشافات إضافية غير مرتبطة، وثِّقت بلا إصلاح

- `SocialService._check_saas_limits` يتحقق من كتالوج خدمات SaaS غير مزروع (`code='social'` صفر صفوف) — حُجب مؤقتًا بـmonkeypatch على مستوى الـinstance في سكربت الاختبار فقط، **لا تعديل على الكود المصدري**.
- مستخدم متبقٍّ من جلسة سابقة بالبريد `system@eppne.com` (`id=43`, `p_ctor_proj_sysrecv`, أُنشئ 2026-08-14) — بيانات خاملة من إصلاح الباج القديم، لا علاقة له بالكود الحالي.
- الفهرس الفريد على `affiliate_commission_tiers (tenant_id, entity_type, target_product_id)` لا يمنع فعليًا تكرار صفوف `GLOBAL` لنفس التينانت (Postgres يعامل كل `NULL` كقيمة مختلفة) — ثغرة سلامة بيانات كامنة حقيقية، خارج النطاق.

---

## 5. تنظيف بيانات الاختبار (بعد التحقق الكامل، بموافقة المستخدم)

كل بيانات الاختبار (throwaway) حُذفت بالكامل، وأُعيدت أرصدة الحسابات "الحقيقية" الآن (حسابات النظام، وأدمن تينانت 16) للصفر بعد أن تراكمت فيها عائدات اختبار اصطناعية بالكامل:

- **محذوف نهائيًا (14 مستخدمًا throwaway + كل ما يتبعهم عبر سلسلة FK كاملة):** `users` (961-973, 975)، `wallets` (cascade تلقائي)، `transactions` (9)، `audit_logs` (4)، `iot_request_logs` (2)، `group_subscriptions`(1)، `social_groups`(1)، `group_subscription_plans`(1)، `order_items`(5)، `commission_records`(3، منها واحد يتيم كان يشير لمستخدم حقيقي سابق `id=3` دون أي تأثير مالي عليه)، `orders`(5)، `products`(4)، `contributions`(1)، `affiliate_profiles`(2)، `affiliate_commissions`(2، حُذفت تلقائيًا عبر cascade عند حذف `orders`)، `affiliate_commission_tiers`(1)، `utility_readings`(2)، `smart_assets`(2)، `projects`(1)، `academy_courses`(1).
- **أُعيد ضبطها للصفر (حسابات حقيقية باقية، أرصدتها فقط كانت اصطناعية):** محفظة حساب نظام تينانت 1 (`wallet.id=929`, كانت `100017.0 MR_USDT`)، محفظة أدمن تينانت 16 (`wallet.id=930`)، محفظة حساب نظام تينانت 16 (`wallet.id=931`).
- **تحقق نهائي مستقل بعد التنظيف الكامل:** كل الجداول أعلاه = صفر صف throwaway متبقٍّ، ومحفظة `wallet.id=39` (الضحية المحتملة الأصلية) لا تزال `{"MR_USDT": 875.0}` — بلا أي تغيير من أول الجلسة لآخرها.

---

## 6. الملفات المعدَّلة (Phase 3، صفر commit بعد — بانتظار المراجعة)

```
 app/core/system_account_service.py       |  6 +++++-  (استيراد مؤجَّل فقط، §3)
 app/domains/academy/service.py           |  3 ++-
 app/domains/affiliate/service.py         |  4 +++-
 app/domains/commerce/service.py          |  4 +++-
 app/domains/iot/service.py               |  4 +++-
 app/domains/projects/service.py          |  4 +++-
 app/domains/saas/service.py              | 24 ++++++++++++++++++++----  (+ _get_tenant_admin_id الجديدة)
 app/domains/social/service.py            | 15 +++++++++++----
 8 files changed, 50 insertions(+), 14 deletions(-)
```
كل الملفات الثمانية كانت نظيفة قبل هذه الجلسة (لا تعديلات سابقة غير مرتبطة مختلطة بها، على عكس `core/security.py` في Phase 2) — جاهزة للـstage والـcommit الكامل بلا حاجة لعزل.
