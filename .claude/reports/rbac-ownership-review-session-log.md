# جلسة نقاش/قرار — مراجعة موحَّدة لأسئلة RBAC/Ownership المعلَّقة من سويپ الأمان

**نوع الجلسة:** توثيق وتحليل فقط. **صفر كود، صفر Edit على أي ملف دومين.**

## 0) ملاحظة على العدّ قبل الجدول

التعليمات طلبت "8 أمثلة (4 من command + 4 من saas)"، لكن `PROGRESS_LOG.md`
(بند `command-rbac-ownership-review`) والمرجع `command-idor-fix-session-log.md`
§5 يوثّقان **5** أمثلة من `command`: `acknowledge_alert`, `resolve_alert`,
`get_report`, `delete_report`, `apply_recommendation`. لم أحذف أي بند من
الخمسة لتجنّب فقدان معلومة موثَّقة أصلًا — الجدول أدناه فيه **9 صفوف**
(5 command + 4 saas). لو القصد كان استبعاد `get_report` تحديدًا (لأنها
قراءة/`GET` مش "كتابة/حذف" بالحرف كما صاغت التعليمات)، فهو موضّح في
عمود "الفعل" ويسهل تجاهله بصريًا.

---

## 1) الجدول الموحَّد

| # | الدومين | الدالة | الفعل الفعلي (لو اتسيب زي ما هو) | الأثر لو استُغل | رأيي المبدئي |
|---|---|---|---|---|---|
| 1 | command | `acknowledge_alert` | أي `active_user` (حتى دور `USER` العادي) داخل نفس التينانت يقدر يعلّم أي تنبيه — حتى لو أنشأه سوبريوزر تاني — كـ"مُتابَع". مؤكَّد حيًا: مستخدم عادي (id=844) نادى على تنبيه سوبريوزر → `200`، `acknowledged_by` اتسجَّل = هو نفسه. | **معلوماتي/تشغيلي، لكن أمني الطابع.** التنبيهات غالبًا مؤشرات أمن/نظام حسّاسة — أي حساب (حتى لو مخترَق أو موظف عادي بلا صلاحية تقييم) يقدر "يُسكِت" تنبيهًا بمجرد الضغط على acknowledge، بلا أي تصعيد لصاحب صلاحية أعلى. | **فجوة حقيقية محتملة، مش مجرد تصميم تعاوني.** الخطر مش بس "موظف بيتصرف بره اختصاصه" — لو حساب عادي اتخُرق، صاحب الاختراق نفسه يقدر يُسكِت التنبيه اللي بيفضحه. أقل حل معقول: حد أدنى دور (مش لازم `SUPER_ADMIN`، ممكن دور وسيط "MANAGER" لو موجود) بدل فتحها لأي `active_user`. |
| 2 | command | `resolve_alert` | نفس كود/نمط `acknowledge_alert` بالحرف (لم يُختبَر حيًا مباشرة لكن الاستدلال من نفس الملف مؤكَّد بالفحص الثابت) — أي `active_user` يقدر يُغلق تنبيه (حالة نهائية، أقوى من acknowledge) أنشأه/يخصّ غيره. | **نفس فئة #1 لكن أخطر** — "resolve" بيقفل الملف نهائيًا (لا رجوع لحالة "مفتوح" تلقائي)، بعكس acknowledge اللي بيفضل قابل للمراجعة. | **فجوة حقيقية، أقوى من #1.** نفس منطق الإسكات، لكن الأثر أقرب لـ"إخفاء دليل" من "تأجيله" — يستاهل نفس القيد أو أشد (ربما تصعيد لدور أعلى تحديدًا لـ`resolve` حتى لو `acknowledge` فُتحت لأي أحد). |
| 3 | command | `get_report` | أي `active_user` داخل نفس التينانت يقدر يقرأ أي تقرير استراتيجي، بغض النظر عن مين أنشأه أو مستوى حساسيته. (قراءة فقط — `GET`، مش كتابة/حذف كما صاغت التعليمات الأصلية). **✅ مؤكَّد بالفحص (راجع §1.5-ب):** `CommandReport.report_type` فيه قيمة `FINANCIAL` صريحة ضمن 5 أنواع (`FINANCIAL`, `OPERATIONAL`, `USER_GROWTH`, `SECTOR_PERFORMANCE`, `SYSTEM_HEALTH`)، و`CommandReportResponse` بترجّع `report_data: Dict[str, Any]` (الـJSONB الكامل) **بلا أي فلترة/تنقيح حسب النوع أو الدور**. | **معلوماتي، لكن مؤكَّد إنه يشمل بيانات مالية.** موظف `USER` عادي يقدر يقرأ تقرير `report_type=FINANCIAL` كاملًا (كل الـ`report_data`) بنفس سهولة تقرير `SYSTEM_HEALTH` العام — مفيش أي تمايز في الحماية حسب حساسية النوع. | **فجوة حقيقية مؤكَّدة الآن (مش مجرد شك).** وجود `FINANCIAL` كنوع تقرير فعلي + إرجاع `report_data` الكامل بلا تنقيح يعني إن أي موظف عادي يقدر يقرأ تقارير مالية للتينانت بالكامل. هذا تسريب داخلي حقيقي لبيانات حساسة (مش "زي فواتير الشركة العامة") — يستاهل تقييد بحد أدنى دور، أو فلترة `report_data` حسب `report_type`/دور القارئ. |
| 4 | command | `delete_report` | أي `active_user` (حتى `USER` عادي) يقدر يحذف (soft-delete) تقريرًا استراتيجيًا أنشأه سوبريوزر تاني. مؤكَّد حيًا: مستخدم عادي حذف تقرير سوبريوزر → `204`، تحقق DB مستقل أكَّد `is_deleted=true`. | **تخريبي.** حذف بيانات استراتيجية — حتى لو soft-delete (نظريًا قابل للاسترجاع من DB مباشرة)، من منظور المستخدم/الواجهة التقرير اختفى نهائيًا بلا أي موافقة من صاحبه أو من إدارة أعلى. | **فجوة حقيقية واضحة — أقوى بند في القائمة كلها.** حذف بيانات استراتيجية من طرف دور `USER` العادي بلا فحص ملكية أو دور مفيش أي تبرير تعاوني معقول له — الشركات عادةً ما بتديش صلاحية حذف تقارير الإدارة العليا لأي موظف. يستاهل تقييد فوري (على الأقل: مالك التقرير، أو دور `SUPER_ADMIN`/أعلى). |
| 5 | command | `apply_recommendation` | **✅ مؤكَّد بالفحص (راجع §1.5-أ):** الدالة (`service.py:382-400`) بتعمل حصريًا `repo.update_recommendation(rec_id, tenant_id, status="APPLIED", applied_by=user_id, applied_at=...)` + سطر `audit_log()` — **لا تلمس أي جدول/دومين تاني، لا تسعير، لا موارد، لا أي مورد تشغيلي حقيقي.** `AIRecommendation` model نفسه (`models.py:241-268`) مالوش أي علاقة (FK/trigger) بأي كيان تشغيلي آخر — مجرد سجل توصية مستقل بحالة (`status`) فقط. | **معلوماتي/تتبُّعي بحت — أثبت الفحص إنه لا يغيّر أي حاجة تشغيلية أو مالية حقيقية.** أقصى أثر: تسجيل مضلِّل (موظف بلا صلاحية استراتيجية "يعلّم" توصية كـ"مُطبَّقة" رغم إنه مش هو صاحب قرار تطبيقها فعليًا في الواقع خارج النظام) — لكن مُتتبَّع بالكامل (`applied_by` مسجَّل، `audit_log` صريح). | **الأضعف بين كل بنود command — أقرب لتصميم تعاوني مقبول من فجوة حقيقية.** بعد التأكد إن الدالة status/tag فقط بلا أي تنفيذ فعلي، الخطر الوحيد المتبقي هو دقة التتبع الإداري (مين قرر إن التوصية "اتطبّقت")، مش تنفيذ غير مصرَّح به. **تراجع في التصنيف عن التقييم الأولي** — لا يستاهل نفس أولوية `delete_report`؛ لو احتاج تقييد، يكون بدافع "دقة القرار الاستراتيجي" مش "منع ضرر تشغيلي/مالي". |
| 6 | saas | `subscribe_to_plan` | أي `active_user` (موظف عادي، بلا دور إداري) يقدر يشترك التينانت كله في خطة مدفوعة جديدة. (محجوبة حاليًا ببج pre-existing غير متعلق بـRBAC — `get_plan_by_id` بتفشل منطقيًا — لكن هذا لا يغيّر تقييم التصميم المقصود). | **مالي مباشر.** اشتراك = التزام مالي متكرر على حساب/محفظة التينانت بالكامل، بقرار فردي من أي موظف. | **فجوة حقيقية.** الالتزام المالي المتكرر (subscription) قرار عادةً محصور بمن يملك سلطة الميزانية — فتحه لأي `active_user` يعني موظف واحد (بقصد أو بالخطأ) يقدر يُلزم الشركة كلها بفاتورة شهرية جديدة. يستاهل تقييد بدور إداري/مالي على الأقل. |
| 7 | saas | `cancel_subscription` | أي `active_user` يقدر يلغي اشتراك التينانت بالكامل. (حاليًا فيها بج silent-write منفصل تمامًا — الـ`200` بيرجع بس DB مش بتتغيّر فعليًا — لكن هذا بج تنفيذي غير مرتبط بسؤال RBAC؛ التقييم هنا لسلوك التصميم المقصود لو اتصلح البج). | **تخريبي على مستوى الخدمة.** إلغاء اشتراك كامل التينانت = فقدان وصول لكل الخدمات المدفوعة للشركة بأكملها، بقرار موظف واحد بلا مراجعة. | **فجوة حقيقية — من أخطر البنود.** موظف واحد (ساخط، أو بالخطأ، أو حساب مخترَق) يقدر يُطفئ خدمة الشركة كلها فورًا. لا يوجد سيناريو "تعاوني" معقول يبرر ترك هذا مفتوحًا لأي `active_user` — عادة يحتاج تأكيد إداري/دور أعلى، أو حتى تدفق موافقة (approval flow) لا مجرد رفع الدور. |
| 8 | saas | `pay_invoice` | أي `active_user` يقدر يُشغّل عملية دفع فاتورة حقيقية — تحريك أموال فعلي من محفظة/حساب التينانت. (محجوبة حاليًا بانحراف schema منفصل، وموثَّق أيضًا خطر معماري إضافي `sender_id=tenant_id` قد يخصم من محفظة مستخدم عشوائي — بند backlog منفصل `saas-pay-invoice-sender-id-user-id-collision`). | **مالي مباشر — أموال حقيقية تتحرك.** أخطر فئة في القائمة كلها من ناحية الأثر المباشر (نقل أموال فعلي وليس مجرد حالة/بيانات). | **فجوة حقيقية، أولوية عالية جدًا.** عمليات الدفع الفعلي للفواتير من رصيد الشركة عادة ما تُقيَّد بدور مالي/إداري في أي نظام SaaS B2B ناضج — فتحها لأي موظف عادي خطر مالي مباشر، ويتفاقم بوجود بج `sender_id` الموثَّق منفصلًا (قد يخصم من محفظة شخص غلط أصلًا). هذا البند الأعلى أولوية بين التسعة كلها. |
| 9 | saas | `get_my_invoices` | أي `active_user` يقدر يقرأ سجل فواتير التينانت بالكامل. **✅ مؤكَّد بالفحص (راجع §1.5-ج):** `InvoiceResponse` (يرث من `InvoiceBase`) بترجّع فقط: `invoice_number`, `amount`, `currency`, `description`, `items` (تفاصيل الخدمات المشحونة كـ`List[Dict]`)، `status`, `due_date`, `paid_at`, `paid_tx_hash` (هاش معاملة بلوكتشين، مش بيانات دفع خام)، `created_at`/`updated_at`. **صفر أرقام بطاقات، صفر IBAN، صفر بيانات حساب بنكي.** | **معلوماتي بحت، مؤكَّد الآن.** كشف مبلغ/حالة/تاريخ الفاتورة فقط — بيانات فوترة عامة، بلا أي معلومة دفع حساسة قابلة للاستغلال مباشرة. | **✅ تصميم تعاوني منطقي، مؤكَّد بالفحص — أضعف خطورة في القائمة كلها بثقة كاملة الآن.** لا يوجد أي بيانات حساسة في الرد تستدعي تقييدًا. يمكن اعتباره "آمن نهائيًا" من زاوية تصنيف حساسية البيانات — لو احتاج تقييد مستقبلًا، الدافع يكون تنظيمي (مين يقدر يشوف مصاريف الشركة) لا أمني. |

---

## 1.5) فحص إضافي (قراءة فقط) — الثلاث نقاط الغامضة، مُنجَز بالكامل

### أ) `command.apply_recommendation` — `service.py:382-400`

```python
async def apply_recommendation(self, rec_id, tenant_id, user_id) -> AIRecommendation:
    recommendation = await self.repo.update_recommendation(
        rec_id, tenant_id,
        status="APPLIED", applied_by=user_id, applied_at=datetime.utcnow()
    )
    await audit_log(user_id=..., tenant_id=..., action="RECOMMENDATION_APPLIED", ...)
    return recommendation
```

`repo.update_recommendation` (`repository.py:208`) بتعمل `UPDATE` على جدول
`command_ai_recommendations` فقط (`status`/`applied_by`/`applied_at`). موديل
`AIRecommendation` (`models.py:241-268`) مستقل تمامًا — مفيش FK ولا استدعاء
لأي دومين تاني (تسعير، موارد، مالية). **النتيجة: الدالة status/tag فقط،
صفر تنفيذ فعلي حقيقي.** أثرها الوحيد معلوماتي/تتبُّعي (`applied_by` مسجَّل
+ `audit_log` صريح).

### ب) `command.get_report` — `models.py:206-236` + `schemas.py:115-125`

`CommandReport.report_type` (`SQLEnum(ReportType)`) له 5 قيم فعلية
(`models.py:35-40`): `FINANCIAL`, `OPERATIONAL`, `USER_GROWTH`,
`SECTOR_PERFORMANCE`, `SYSTEM_HEALTH`. `CommandReportResponse` (المُستخدَم
في رد `get_report`) بترجّع `report_data: Dict[str, Any]` — الـJSONB الكامل
بلا أي تنقيح حسب `report_type` أو دور القارئ. **النتيجة: تقرير
`report_type=FINANCIAL` بكل بياناته المالية يُقرأ بنفس سهولة تقرير
`SYSTEM_HEALTH` العام، لأي `active_user`.**

### ج) `saas.get_my_invoices` — `schemas.py:125-148`

`InvoiceBase`: `invoice_number`, `amount`, `currency`, `description`,
`items: List[Dict[str, Any]]` (تفاصيل الخدمات)، `status`, `due_date`.
`InvoiceResponse` يضيف: `paid_at`, `paid_tx_hash` (هاش معاملة بلوكتشين
— مرجع تتبُّع، مش بيانات دفع خام)، `created_at`/`updated_at`. **صفر
أرقام بطاقات/IBAN/بيانات حساب بنكي في أي مكان بالـschema.**

---

## 1.6) فحص إضافي (قراءة فقط) — هل يوجد دور وسيط بين `USER` و`SUPER_ADMIN` بالفعل؟

**✅ نعم، موجود بالفعل — `ADMIN`.** `SystemRole` (`core/enums.py:16-21`):

```python
class SystemRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"                 # ← الدور الوسيط، موجود من الأساس
    SUPER_ADMIN = "SUPER_ADMIN"
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"
    SYSTEM = "SYSTEM"                # ← أُضيف النهاردة (migration 035)
```

**مش دور جديد مقترَح — موجود على مستوى الـDB من الميجريشن الأولي نفسه**
(`71820e4fe1f3_initial_migration_all_34_sectors_final.py:109`):
`sa.Enum('USER', 'ADMIN', 'SUPER_ADMIN', 'EXECUTIVE_DIRECTOR', name='systemrole')`
— أي **`ADMIN` كان موجود في `systemrole` enum على الـDB قبل ما `SYSTEM`
تتضاف النهاردة أصلًا، وقبل أي شغل في هذه الجلسة.**

### الاستخدام الحالي — مُفعَّل فعليًا، مش مجرد تعريف بلا استخدام

`core/security.py:173-183`:
```python
def is_admin_or_above(user: User) -> bool:
    role_value = ...
    return role_value in ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]

async def require_admin_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    if not is_admin_or_above(current_user):
        raise PermissionDeniedError("Admin privileges required")
    return current_user
```

- **`is_admin_or_above()` مُستخدَمة فعليًا في 3 مواضع حقيقية** داخل
  `identity/router.py` (`list_invitations` مع `scope=tenant`,
  `get_invitation`, `revoke_invitation`) — بتتحكم فعليًا في مين يقدر
  يشوف/يلغي دعوات التينانت بالكامل (`ADMIN` فأعلى) مقابل دعواته الشخصية
  بس (`USER` عادي). **منطق إنتاجي حقيقي، مش كود ميت.**
- **`require_admin_or_above` (نسخة `Depends()` الجاهزة للاستخدام
  كـ"gate" على أي endpoint مباشرة) معرَّفة ومُصدَّرة عبر `api/deps.py`،
  لكن `grep` عبر المشروع كله يؤكد: صفر `Depends(require_admin_or_above)`
  في أي راوتر حاليًا** — يعني الأداة جاهزة ومُختبَرة (نفس منطق
  `is_admin_or_above` المُستخدَم فعليًا في `identity`)، لكن **لسه مش
  مُطبَّقة على أي endpoint في `command` أو `saas`** تحديدًا.

### الأثر المباشر على قرار التنفيذ

**مفيش حاجة لدور جديد ولا migration جديدة لحل أي بند من التسعة.**
الأداة (`require_admin_or_above`/`is_admin_or_above`) موجودة، مُختبَرة في
الإنتاج (`identity`)، وجاهزة للاستيراد المباشر في `command/router.py`
و`saas/router.py` بلا أي تغيير schema — فقط `Depends(require_admin_or_above)`
بدل `Depends(get_current_active_user)` على الـendpoints المطلوب تقييدها،
نفس نمط إصلاح `update_my_brand` (سطر واحد لكل endpoint).

### للتوثيق فقط — لو الدور مكانش موجود، هل إضافته بسيطة زي `SYSTEM`؟

غير منطبق هنا (الدور موجود بالفعل)، لكن للمرجعية المستقبلية: ميجريشن 035
(`035_add_system_to_systemrole_enum.py`) بتوضّح النمط العام — `ALTER TYPE
systemrole ADD VALUE IF NOT EXISTS 'X'` سطر واحد، **لكن بقيدين مهمين لو
احتجنا دور تاني مستقبلًا:**
1. القيمة الجديدة **متستخدمش في نفس الـtransaction اللي أضافتها** (قيد
   PostgreSQL — موثَّق صراحة في تعليق الميجريشن).
2. **صفر `DROP VALUE` في PostgreSQL** — الـ`downgrade()` هنا بترفع
   `NotImplementedError` عمدًا؛ التراجع عن دور مُضاف يحتاج إعادة بناء
   الـenum type بالكامل يدويًا، مش خطوة تلقائية.

---

## 2) خلاصة التصنيف النهائي (حاسم — بعد الفحص الإضافي)

| الأولوية | البند | السبب | تغيّر عن التقييم الأولي؟ |
|---|---|---|---|
| 🔴🔴🔴 | `saas.pay_invoice` | أموال حقيقية تتحرك + بج معماري إضافي موثَّق (`sender_id` collision) يضاعف الخطر | لا — لم يُفحَص في هذه الجولة |
| 🔴🔴🔴 | `saas.cancel_subscription` | يقدر يُطفئ خدمة الشركة كلها بقرار فردي | لا |
| 🔴🔴 | `command.delete_report` | حذف بيانات استراتيجية، مؤكَّد حيًا، أقوى دليل ملموس في القائمة | لا |
| 🔴🔴 | `saas.subscribe_to_plan` | التزام مالي متكرر بقرار فردي | لا |
| 🟠 | `command.get_report` | **مؤكَّد الآن (مش شك):** `report_type=FINANCIAL` فعلي + `report_data` كامل بلا تنقيح | **↑ ارتفع** من "🟡 غير مؤكَّد" إلى "🟠 فجوة مؤكَّدة" |
| 🟠 | `command.resolve_alert` | إغلاق نهائي لتنبيه أمني/نظامي بلا تصعيد | لا |
| 🟠 | `command.acknowledge_alert` | إسكات تنبيه أمني بلا تصعيد (أخف من resolve لأنه قابل للمراجعة) | لا |
| 🟡 | `command.apply_recommendation` | **مؤكَّد الآن:** status/tag فقط، صفر تنفيذ فعلي — خطر تتبُّعي بحت | **↓ انخفض** من "فجوة محتملة تستاهل نفس أولوية delete_report" إلى "الأضعف بين بنود command" |
| 🟢 | `saas.get_my_invoices` | **مؤكَّد الآن بثقة كاملة:** صفر بيانات دفع حساسة في الـschema | **✅ تثبيت** التقييم الأولي (كان مشروطًا، بقى نهائيًا) |

**الحاسم النهائي:**
- **أعلى أولوية تنفيذ (لو تقرر الإصلاح):** `pay_invoice`, `cancel_subscription` (مالية/تخريبية مباشرة) ثم `delete_report`, `subscribe_to_plan`.
- **أولوية متوسطة:** `get_report` (بعد التأكيد — تسريب مالي داخلي حقيقي)، `resolve_alert`, `acknowledge_alert` (إسكات أمني).
- **أولوية منخفضة/شبه معلوماتي:** `apply_recommendation` (تتبُّع فقط، لو يُقيَّد فبدافع دقة القرار لا منع ضرر).
- **الوحيد الآمن بثقة كاملة بلا أي تحفظ:** `get_my_invoices` — تصميم تعاوني مقبول، مؤكَّد بالفحص.

## 3) الحالة الآن

**هذه جلسة توثيق/قرار فقط — صفر كود اتلمس، صفر Edit على أي ملف دومين.**
كل الثلاث نقاط الغامضة اتفحصت (قراءة فقط) وتم تحديث التصنيف بناءً عليها.
الملف ده بيمثّل تحليلي النهائي الحاسم بناءً على:
- `PROGRESS_LOG.md` (بند `command-rbac-ownership-review`)
- `.claude/reports/command-idor-fix-session-log.md` §5
- `.claude/reports/saas-idor-fix-session-log.md` §2
- فحص مباشر لـ`command/service.py`, `command/repository.py`,
  `command/models.py`, `command/schemas.py`, `saas/schemas.py` (هذه الجولة)

**بانتظار قرارك النهائي على كل بند** (خصوصًا هل يُفتح بند تنفيذ منفصل
للبنود المالية في `saas` أولًا، ثم `get_report`/`delete_report`) قبل فتح
أي جلسة تنفيذ لاحقة — لسه صفر كود.

**تبسيط مهم لأي قرار تنفيذ لاحق (بعد فحص §1.6):** الحل الميكانيكي لكل
بنود "تحتاج تقييد بدور" في هذا الملف **جاهز فعليًا بلا أي migration أو
تغيير schema** — دور `ADMIN` موجود من الأساس + `require_admin_or_above`
مُختبَرة إنتاجيًا في `identity`. أي قرار تنفيذ لاحق يكون على الأرجح
سطر واحد لكل endpoint (تبديل `Depends`)، بنفس نمط إصلاح `update_my_brand`
السابق — مش تصميم معماري جديد.

---

## 4) التنفيذ — القرار النهائي، مكتمل، مؤكَّد حيًا بالكامل للثمانية

**القرار المعتمَد:** تطبيق `Depends(require_admin_or_above)` بدل
`Depends(get_current_active_user)` على 8 endpoints (5 `command` + 3
`saas` المالية)، دفعة واحدة. `get_my_invoices` **بلا أي تعديل** (مؤكَّدة
آمنة في §1.5-ج/§2).

### الديف المُطبَّق (8 أسطر + سطرا import، مطابق تمامًا لنمط `update_my_brand`)

`command/router.py`: import سطر واحد (`require_admin_or_above` مضافة)
+ 5 مواضع `Depends(get_current_active_user)` → `Depends(require_admin_or_above)`
(`acknowledge_alert`, `resolve_alert`, `get_report`, `delete_report`,
`apply_recommendation`).

`saas/router.py`: نفس النمط بالحرف — import سطر واحد + 3 مواضع
(`subscribe_to_plan`, `cancel_subscription`, `pay_invoice`).

`git diff --stat` (نطاق الجلسة فقط):
```
eppne-backend/app/domains/command/router.py | 12 ++++++------
eppne-backend/app/domains/saas/router.py    |  8 ++++----
2 files changed, 10 insertions(+), 10 deletions(-)
```
صفر تعديل على `service.py`/`repository.py`/`schemas.py` في الدومينين.

### الإعداد للتحقق الحي

`uvicorn` شُغِّل نظيف (نفس تحذيرات dev/فهرسة pre-existing المعتادة —
`Application startup complete`، صفر Traceback إقلاع). مستخدمان throwaway
جدد عبر التسجيل الحقيقي (`POST /api/identity/register`، تينانت1
الافتراضي): `p_rbac_user` (id=976, `USER` عادي) و`p_rbac_admin`
(id=977, تُرقّي لـ`SUPER_ADMIN` عبر SQL بعد التسجيل — تمثيلًا لأي دور
`ADMIN` فأعلى، بما إن `require_admin_or_above` بتقبل `ADMIN`/`SUPER_ADMIN`/
`EXECUTIVE_DIRECTOR` كلهم). بيانات موارد throwaway (تنبيه/تقرير/توصية/
اشتراك موجود مسبقًا/فاتورة) اتزرعت عبر الـAPI الحقيقي حيث أمكن، وSQL
مباشر فقط لما endpoint الإنشاء الرسمي كان محجوبًا ببج pre-existing غير
متعلق بـRBAC (راجع الملاحظات لكل بند تحت).

### جدول التحقق الحي — الثمانية كلهم، 403/نجاح + تأكيد DB مستقل

| # | Endpoint | `USER` عادي | `ADMIN`/`SUPER_ADMIN` | تأكيد DB مستقل | ملاحظة |
|---|---|---|---|---|---|
| 1 | `command.acknowledge_alert` | `403 "Admin privileges required"` | `200`، `status=ACKNOWLEDGED` | — | نظيف بالكامل |
| 2 | `command.resolve_alert` | `403` | `200`، `status=RESOLVED` | — | نظيف بالكامل |
| 3 | `command.get_report` | `403` | `200`، `report_data` الكامل (`report_type=FINANCIAL`) يرجع كامل للأدمن فقط الآن | — | يقفل فعليًا فجوة §1.5-ب |
| 4 | `command.delete_report` | `403` | `204` | `SELECT` مستقل: `is_deleted` بقيت `false` بعد محاولة `USER`، بقت `true` بعد `ADMIN` | تحقق DB صريح قبل/بعد |
| 5 | `command.apply_recommendation` | `403` | `200`، `status=APPLIED`, `applied_by=977` | `SELECT` مستقل قبل/بعد يطابق الرد | **ملاحظة منهجية:** أول محاولة `ADMIN` رجعت `500` (`ResponseValidationError: confidence_score`) رغم إن الكتابة نجحت فعليًا في DB — السبب **بيانات throwaway مزروعة يدويًا بـSQL ناقصة `confidence_score`** (نفس فئة "NULL defaults" الموثَّقة سابقًا في Phase 16/`saas-test-reqsector`)، **مش بج في تعديل RBAC نفسه ولا حتى بج pre-existing في الكود الحقيقي** — بعد تصحيح قيمة الصف الاختباري، إعادة المحاولة رجعت `200` نظيف. مسار `POST /recommendations/generate` الرسمي (توليد حقيقي) محجوب بالكامل ببج pre-existing منفصل تمامًا (`agent_usage_logs_agent_id_fkey` — `agent_id=14` غير موجود في `ai_agents`)، **صفر علاقة بتعديل اليوم** — لم يُصلَح، خارج النطاق. |
| 6 | `saas.subscribe_to_plan` | `403` | `422 "يوجد اشتراك نشط لهذه الخدمة بالفعل"` | N/A (رفض منطقي، صفر كتابة) | **الگيت بيمرّر الأدمن لمنطق العمل الحقيقي بنجاح** (مش 403) — الرفض `422` قاعدة عمل شرعية (تينانت1 عنده اشتراك نشط بالفعل لنفس الخدمة من بيانات موجودة مسبقًا)، مش نفس بج "الخطة غير موجودة" الموثَّق سابقًا. لم يُختبَر "أول اشتراك حقيقي" (يحتاج تنظيف الاشتراك الموجود مسبقًا، خارج نطاق التحقق المطلوب هنا) |
| 7 | `saas.cancel_subscription` | `403` | `200`، `status=CANCELLED` | `SELECT` مستقل: بقيت `ACTIVE` بعد `USER`، بقت `CANCELLED` فعليًا بعد `ADMIN` | **✅ السبب مؤكَّد الآن بثقة كاملة — راجع §4.1 تحت.** التناقض مع التوثيق السابق سببه commit فعلي أصلح البج بين وقت التوثيق ووقت اختباري اليوم، مش اختلاف مسار اختبار. الاشتراك أُعيد لحالته الأصلية (`ACTIVE`) بعد الاختبار |
| 8 | `saas.pay_invoice` | `403` | `200`، `status=PAID`, `paid_tx_hash` مُولَّد | `SELECT` مستقل: بقيت `PENDING` بعد `USER`، بقت `PAID` فعليًا بعد `ADMIN` | نظيف بالكامل — فاتورة throwaway مزروعة SQL (بما إن مفيش endpoint إنشاء فاتورة مباشر في الراوتر) |
| 9 | `saas.get_my_invoices` | `200` (بلا تغيير — **لم يُلمَس**) | N/A | — | تأكيد إضافي: `git diff` لهذا الـendpoint = صفر أسطر |

**النتيجة الحاسمة:** كل الثمانية اتقفلت بـ`403` لمستخدم `USER` عادي،
وكل الثمانية فضلت شغالة طبيعي 100% لمستخدم `ADMIN`/`SUPER_ADMIN`
(تحقق DB مستقل حيث الفعل كتابة/حذف). **صفر أثر جانبي على المسار
الشرعي.** البندان الوحيدان اللي فيهم ملاحظة خارج نطاق RBAC مباشرة
(`apply_recommendation` — بج بيانات اختبار ذاتي مؤقت، و`cancel_subscription`
— تناقض مع توثيق سابق لبج غير متعلق) موثَّقان بوضوح ولم يُلمَس فيهم كود.

### 4.1) توضيح مطلوب — لماذا اختفى بج `cancel_subscription` silent-write بين التوثيق واختبار اليوم؟

**الإجابة الحاسمة: (أ) — فيه commit فعلي أصلح الباج، بين وقت التوثيق ووقت
اختباري.** مؤكَّد بـ`git log`:

```
45eb4bf fix(saas): commit() explicit in cancel_subscription (silent-write)
Author: 7abeeprog <eppne2020@gmail.com>
Date:   Mon Aug 24 11:32:52 2026 +0300
```

**الديف الفعلي** (`saas/service.py`, دالة `cancel_subscription`):
```diff
-        return await self.repo.update_subscription(
+        result = await self.repo.update_subscription(
             subscription_id, self.tenant_id,
             status="CANCELLED", auto_renew=False,
         )
+        await self.db.commit()
+        return result
```

نفس السبب الجذري الموثَّق سابقًا بالحرف (`repo.update_subscription`
بقت `flush()`-only بعد إصلاح `a9bbae4`، و`cancel_subscription` معندهاش
`begin_nested()` يغطيها بـ`commit()` تلقائي زي بقية الـcallers) —
**الإصلاح: `await self.db.commit()` صريح سطر واحد بعدها مباشرة.**
تقرير الجلسة الكامل: `.claude/reports/saas-cancel-subscription-silent-write-fix-session-log.md`
(176 سطر، commit نفسه بتاريخ **2026-08-24 11:32:52** — أي **بعد**
جلسة `saas-idor-fix` اللي وثّقت الباج (نفس اليوم، وقت أبكر) **وقبل**
اختباري اليوم 2026-08-25 بحوالي 19 ساعة).

**تأكيد إضافي مستقل (بطلبك، بدل إعادة الـrepro اليدوي الكامل):** الكوميت
نفسه جاب معاه regression test مخصَّص
(`tests/test_saas_cancel_subscription_silent_write.py`) بيتحقق عبر
`AsyncSessionLocal` **منفصلة تمامًا** (نفس منهجية `test_entity_membership_foundation.py`)
— شغّلته الآن مستقلًا عن أي حاجة تانية في الجلسة:

```
tests/test_saas_cancel_subscription_silent_write.py::test_cancel_subscription_persists_cancelled_status_independent_session PASSED
tests/test_saas_cancel_subscription_silent_write.py::test_cancel_already_cancelled_subscription_raises_validation_error PASSED
2 passed, 1 warning in 49.00s
```

**الخلاصة:** صفر لغز — الباج كان حقيقي وموثَّق صح، اتصلح فعليًا بـcommit
منفصل تمامًا عن هذه الجلسة (`45eb4bf`)، والإصلاح مؤكَّد بثلاث طبقات
مستقلة (كوميت أصلي وثّق قبل/بعد، regression test مستقل شغّال الآن،
واختباري الحي اليوم لنفس الـendpoint تحت تعديل RBAC). **⚠️ ملاحظة
توثيق منفصلة (خارج نطاق RBAC، للمرجعية فقط):** `PROGRESS_LOG.md` السطر
~147 **لسه بيوثّق البج كـ"🔴🔴 مفتوح — أولوية قصوى"** رغم إنه اتقفل
فعليًا من commit `45eb4bf` بنفس اليوم — الفهرس ده بقى قديم (stale) على
هذا البند تحديدًا، يستاهل تحديث في جلسة منفصلة (ليس ضمن نطاق قرار RBAC
اليوم، ولا يُلمَس هنا).

---

### تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

`DELETE`/`UPDATE` لكل الصفوف المزروعة (تنبيه id=2، تقرير id=3، توصية
id=1، فاتورة id=3، استعادة اشتراك id=2 لـ`ACTIVE`، حذف المستخدمين
976/977). `SELECT COUNT` مستقل بعد التنظيف: **صفر في كل الجداول
الخمسة.** `uvicorn` أُوقف نظيف (`taskkill` على PID الاستماع الفعلي على
المنفذ 8000، تأكيد `curl` بعدها: connection refused).

### `git status` / `git diff --stat` — للمراجعة قبل أي commit

**⚠️ ملاحظة مهمة: شجرة العمل فيها تعديلات كتيرة تانية غير مرتبطة
بالإطلاق بهذه الجلسة** (موجودة من قبل بداية هذه الجلسة — راجع
`git status` الأصلي في أول المحادثة: حذف `agritech/router.py`،
تعديلات على `health/service.py`, `invoicing/router.py`, `main.py`,
`tasks/affiliate.py`, `tasks/billing.py`, `tests/conftest.py`، وملفات
`eppne-web/` متعددة، + عشرات الملفات untracked في `.claude/plans`/
`.claude/reports`). **نطاق هذه الجلسة محصور حصريًا في:**
`eppne-backend/app/domains/command/router.py`,
`eppne-backend/app/domains/saas/router.py`, وهذا الملف نفسه
(`rbac-ownership-review-session-log.md`، untracked من الأساس).
**لا تعميم `git add -A`/commit شامل — أي commit لاحق يجب يقتصر على
الملفات التلاتة دي تحديدًا.**

```
eppne-backend/app/domains/command/router.py | 12 ++++++------
eppne-backend/app/domains/saas/router.py    |  8 ++++----
2 files changed, 10 insertions(+), 10 deletions(-)
```

**بانتظار توجيهك: أعمل commit للملفين + تقرير الجلسة (بمعزل تام عن باقي
التعديلات غير المرتبطة في الشجرة)، ولا لسه فيه حاجة تانية تتراجع؟**
