# رؤية تصميم: حساب النظام الموحَّد لكل تينانت (Tenant System Account)

> مستند رؤية/تصميم فقط — صفر كود، صفر Edit، صفر migration فعلية.
> تاريخ الجلسة: 2026-08-24 (محدَّث: قرارات نهائية على كل الأسئلة الستة
> المفتوحة — راجع القسم 7)
> يقابل في الأسلوب: رؤية الهرم التنظيمي السابقة.

---

## 0. ملخص تنفيذي

سويپ الأمان كشف 9 مواقع استدعاء عبر 7 دومينات، كلها بتحل نفس المشكلة
الجوهرية — "من يمثّل النظام/التينانت كطرف في تحويل مالي؟" — بثلاثة أنماط
فرعية مختلفة، كلها غير آمنة. القرار المعتمَد: **مستخدم نظام واحد لكل
تينانت** (`User.is_system_account: bool`)، يُنشأ ويُسترجَع عبر دالة
مركزية واحدة.

هذا المستند يغطي:
1. تحليل معماري دقيق لـ `finance/service.py` ونقطة التدخل.
2. تصميم الدالة المركزية (مكان، توقيع، توقيت الإنشاء، حماية).
3. اكتشاف معماري حرج غير متوقَّع (قسم 2.4) يوضح لماذا الحل الحالي **لا
   يعمل فعليًا** عبر أكثر من تينانت واحد — ليس فقط "غير آمن" بل غالبًا
   **معطَّل فعليًا** لأي تينانت غير الأول الذي لمس الكود.
4. Migration مقترحة (وصف فقط).
5. خريطة تحويل لكل الـ9 مواقع.
6. أسئلة مفتوحة صريحة (§6) — و**قراراتها النهائية موثَّقة في §7**.
7. **قرارات نهائية والتبعات التنفيذية (محدَّث 2026-08-24)** — كل الأسئلة
   الستة محسومة الآن؛ §6 تبقى كسجل لتحليل الخيارات، و§7 هي المرجع
   الحاسم لأي تنفيذ لاحق.

---

## 1. تحليل معماري: أين بالضبط تتدخل الدالة؟

قرأت `eppne-backend/app/domains/finance/service.py` بالكامل (361 سطر).
النقاط الجوهرية:

### 1.1 `get_or_create_wallet_for_update` (السطر 34-39)

```python
async def get_or_create_wallet_for_update(self, user_id: int) -> Wallet:
    wallet = await self.wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)
    if not wallet:
        wallet = await self.wallet_repo.create(user_id, self.tenant_id)
        wallet = await self.wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)
    return wallet
```

هذه الدالة **لا تتحقق أبدًا** من وجود `User` حقيقي بالـ`user_id` الممرَّر —
هي فقط تنشئ `Wallet` جديدة وتربطها بـ`user_id` + `self.tenant_id`. الحماية
الوحيدة هي `ForeignKey("users.id")` على `Wallet.user_id`
(`finance/models.py:29`) — قيد على مستوى قاعدة البيانات فقط، **وهو غير
واعٍ بالتينانت إطلاقًا** (FK يتحقق فقط من وجود صف بهذا الـid في جدول
`users` بأكمله، بغض النظر عن تينانته).

**هذا هو جذر الخطر الحقيقي**: `sender_id=1` (مثلاً) ينجح دائمًا طالما
يوجد **أي** مستخدم حقيقي بـ`id=1` في **أي** تينانت — وغالبًا هذا يكون
أول مستخدم اتسجل في المنصة كلها. كل تينانت يستدعي أحد المواقع التسعة
يُنشئ له تلقائيًا محفظة "شبح" (`user_id=1, tenant_id=<هذا التينانت>`)
مربوطة بهوية ذلك المستخدم الحقيقي، ويخصم/يودع منها فعليًا — دون علمه
ودون أي علاقة له بذلك التينانت.

### 1.2 `transfer()` (السطر 58-147) — نقطتا التدخل الفعليتان

`transfer(sender_id: int, receiver_email: str, ...)` تستقبل طرفَين
بشكلَين مختلفين تمامًا:
- **المرسِل دائمًا `int` (user_id)** → يمر مباشرة لـ
  `get_or_create_wallet_for_update` بلا أي تحقق من الهوية أو التينانت.
- **المستقبِل دائمًا `str` (email)** → يمر عبر:
  ```python
  receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)   # سطر 78
  if not receiver:
      raise NotFoundError("المستلم غير موجود")
  if receiver.tenant_id != self.tenant_id:                                  # سطر 82-83
      raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")
  ```

**هاتان النقطتان بالضبط هما مكان تدخل `get_or_create_system_account`:**
كل موقع من الـ9 يستبدل الـ`int` الهاردكودد (أو `tenant_id` المُفسَّر
غلط) في موضع `sender_id=`، أو الـ`str` الهاردكودد في موضع
`receiver_email=`، باستدعاء الدالة المركزية والحصول على `system_user.id`
أو `system_user.email` منها.

### 1.3 `_create_audit_log` (السطر 41-49) و`process_invoice_payment` (353-361)

لا تأثير مباشر — لكن يجب ملاحظة أن `_create_audit_log` تسجّل `user_id`
كطرف في السجل. إذا كان الحساب النظامي هو المرسِل، ستظهر سجلات تدقيق
بـ`user_id=<system_account_id>` — سلوك مقصود ومفيد فعليًا (تتبّع أوضح
من `user_id=1` الحالي بلا معنى).

### 1.4 اكتشاف حرج: قيد `receiver.tenant_id != self.tenant_id` يُثبت أن الأنماط الحالية (٣) مكسورة فعليًا عبر التينانتات — وليست فقط غير آمنة

`User.email` **فريد عالميًا** (`identity/models.py:35`:
`unique=True, index=True, nullable=False`) — **ليس فريدًا لكل تينانت**.

هذا يعني أن `"system@eppne.com"` (أو `"academy@eppne.com"`,
`"shop@eppne.com"`, `"saas@eppne.com"`) يمكن أن يوجد **لصفٍّ واحد فقط**
في كامل جدول `users`، مملوك لتينانت واحد بعينه (أيًا كان أول تينانت
أُنشئ له هذا الصف يدويًا/عرضيًا).

بتتبع `transfer()` سطر 78 و82-83:
- لأي تينانت **آخر** غير مالك ذلك الصف: `get_by_email(..., self.tenant_id)`
  تُرجع `None` (لأنها مفلترة بالتينانت) → `NotFoundError("المستلم غير موجود")`.
- إذا حدث تصادم وأنشأ تينانت آخر مستخدمًا بنفس الإيميل، `UNIQUE constraint`
  في قاعدة البيانات نفسها يرفض الإدراج من الأساس.

**الخلاصة:** أنماط `receiver_email="system@eppne.com"` (saas.pay_invoice,
process_auto_renewals, projects.add_contribution, academy.enroll_in_course,
social.request_physical_gift, social.subscribe_group_to_plan) **لا يمكن
أن تعمل بنجاح إلا لتينانت واحد في كل قاعدة بيانات** — كل تينانت آخر يحصل
على فشل حتمي (`NotFoundError`) في كل مرة يُستدعى فيها أحد هذه المسارات.
هذا ليس افتراضًا نظريًا — هو نتيجة مباشرة لقيدَي `unique=True` على
`User.email` وفحص `receiver.tenant_id` في `transfer()`.

→ هذا يرفع أولوية الحل من "إغلاق ثغرة أمنية" إلى "إصلاح عطل وظيفي متعدد
التينانتات فعلي"، ويُثبت معماريًا أن **حساب نظام واحد لكل تينانت هو
الحل الوحيد الممكن أصلًا** (وليس مجرد الخيار الأفضل) — لأن أي بريد/معرّف
ثابت مشترك بين كل التينانتات يصطدم مباشرة بقيد الـuniqueness العالمي على
`email` وبفحص `receiver.tenant_id`.

### 1.5 اكتشاف حرج ثانٍ: `UserRepository.create()` يعمل `commit()` داخلي — خطر على السياقات المُغلَّفة بـ`begin_nested()`

`identity/repository.py:64-68`:
```python
async def create(self, user: User) -> User:
    self.db.add(user)
    await self.db.commit()          # ⚠️ commit كامل، وليس flush
    await self.db.refresh(user)
    return user
```

بينما `WalletRepository.create()` (`finance/repository.py:34-46`) تعمل
`flush()` + `refresh()` فقط — **بلا commit**.

**التأثير**: 6 من الـ9 مواقع تستدعي `finance.transfer(...)` من **داخل**
`async with self.db.begin_nested()` (savepoint)، مثل
`saas.pay_invoice` (`saas/service.py:306`) و
`social.request_physical_gift` (`social/service.py:556`) و
`social.subscribe_group_to_plan` (`social/service.py:640`). لو كان
الإنشاء الكسول (lazy) لحساب النظام يستخدم `UserRepository.create()`
كما هي، واستُدعي لأول مرة من داخل أحد هذه الـsavepoints، فسيُنفَّذ
`commit()` **كامل على الـsession الخارجية بأكملها** في منتصف معاملة
متداخلة — سلوك غير متوقَّع يكسر مبدأ الذرّية (atomicity) للعملية
المحيطة بالكامل، وليس مجرد مشكلة أسلوبية.

**الاستنتاج المعماري**: أي مسار إنشاء (create) داخل الدالة المركزية
الجديدة **يجب** أن يستخدم `add()` + `flush()` + `refresh()` (مثل نمط
`WalletRepository.create`)، **وليس** `UserRepository.create()` الحالية
كما هي — أو يجب إضافة نسخة جديدة `create_no_commit()`/تعديل الدالة
الحالية لقبول `commit: bool = True`. هذا تفصيل تنفيذي حاسم لأي جلسة
تنفيذ لاحقة، حتى لو كان خارج نطاق التوثيق الحالي.

---

## 2. تصميم الدالة المركزية

### 2.1 المكان

`app/core/system_account_service.py`

يتبع نمطًا موجودًا فعليًا في المشروع: `app/core/entity_membership_service.py`
+ `app/core/entity_membership_repository.py` (منطق مشترك عابر للدومينات
موضوع في `app/core/` بنفس الأسلوب). لا حاجة لملف repository منفصل —
الدالة بسيطة كفاية لتُبنى مباشرة فوق `UserRepository` و`WalletRepository`
الموجودتين.

الاستيراد من `app.domains.identity.models`/`repository` داخل `app/core/`
**نمط مقبول فعليًا في المشروع** — `finance/service.py` نفسها تستورد
`from app.domains.identity.models import User` و
`from app.domains.identity.repository import UserRepository` بلا أي
حاجز طبقي (layering barrier) ظاهر.

### 2.2 التوقيع المقترح

```python
async def get_or_create_system_account(db: AsyncSession, tenant_id: int) -> User:
    """
    يُرجع حساب النظام الخاص بهذا التينانت، وينشئه إذا لم يكن موجودًا.
    Idempotent: استدعاءات متكررة بنفس tenant_id تُرجع نفس الصف دائمًا.
    """
```

- دالة مستقلة (module-level)، وليست methodعلى class — لا يوجد حالة
  (state) تحتاج تُحفظ بين استدعاءين، ونمط `FinanceService`/`AcademyService`
  في المشروع أصلًا يُنشئ instance جديد لكل request بـ`(db, tenant_id)`،
  فدالة حرة أبسط وتتجنب دورة استيراد غير ضرورية (import cycle) بين
  `core` والدومينات لو حُوّلت لـclass.
- **لا تُرجع فقط `int` أو `str`** — تُرجع كائن `User` كامل، لأن مواقع
  الاستدعاء التسعة تحتاج أحيانًا `.id` (كـ`sender_id`) وأحيانًا `.email`
  (كـ`receiver_email`) من **نفس** الحساب. إرجاع الكائن الكامل يغطي
  الحالتين بدالة واحدة بدل دالتين متوازيتين.

### 2.3 متى يُنشأ الحساب؟ — راجع السؤال المفتوح رقم 1 في القسم 6

نقطتا تكامل ممكنتان محدَّدتان بدقة من الكود الفعلي:

**الخيار أ — عند إنشاء التينانت (Eager)**: نقطة تكامل واحدة نظيفة:
`AcademyService.create_tenant()` (`academy/service.py:55-58`)، التي
تُستدعى حصريًا من `POST /academy/tenants`
(`academy/router.py:59-66`, محمي بـ`get_current_superuser`). هذا هو
**موقع الإنشاء الوحيد الموجود فعليًا في الكود** لصف `AcademyTenant`
(`academy/repository.py:92-97` — `create_tenant`). عملية إدارية نادرة
ومحمية بصلاحية سوبر أدمن أصلًا — إضافة استدعاء واحد هنا آمنة ومركزية
تمامًا.

⚠️ ملاحظة معمارية مهمة: `AcademyTenant.admin_id` عمود **إجباري**
(`nullable=False`, FK إلى `users.id`) — أي التينانت لا يمكن أن يُنشأ
أصلًا بدون وجود مستخدم admin حقيقي مسبقًا. هذا يعني أن تسلسل الإنشاء
الفعلي هو: (١) تسجيل مستخدم admin عبر `identity/register` بتينانت
مؤقت/سياق مختلف → (٢) استدعاء `POST /academy/tenants` بـ`admin_id`
ذلك المستخدم. حساب النظام يمكن إنشاؤه بأمان في الخطوة (٢) لأن
`tenant_id` يصبح معروفًا لحظتها لأول مرة.

**الخيار ب — عند أول استخدام (Lazy)**: كل موقع من الـ9 يستدعي
`get_or_create_system_account(db, tenant_id)` مباشرة قبل `transfer()`؛
الدالة تتحقق أولًا (`SELECT ... WHERE tenant_id=X AND is_system_account=True`)
وتنشئ فقط إن لم يوجد.

**لماذا هذا سؤال مفتوح وليس قرارًا محسومًا:**
- الخيار أ نظيف لكل تينانت **جديد**، لكنه **لا يغطي التينانتات
  الموجودة فعليًا في قاعدة البيانات حاليًا قبل هذا التغيير** — تلك
  ستظل بلا حساب نظام حتى تُستدعى، فتحتاج مسار احتياطي (fallback) على
  أي حال.
- الخيار ب (كسول ودائمًا idempotent) يغطي كلتا الحالتين تلقائيًا
  بمنطق واحد، بلا حاجة لـ backfill منفصل — لكنه يعني أن أول استدعاء
  من أي دومين من الـ7 يتحمّل تكلفة إنشاء الحساب (INSERT إضافي)،
  وهذا القرار يمس تصميم الـidempotency والأداء على مسار حرج (transfer).

**توصيتي (غير ملزمة، للنقاش)**: تنفيذ الدالة نفسها كـ**كسولة دائمًا**
(idempotent get-or-create حقيقي، بصرف النظر عمّن يستدعيها) — هذا يحل
مشكلة الـbackfill للتينانتات الموجودة تلقائيًا بلا migration بيانات
منفصلة. **ثم** إضافة استدعاء لها أيضًا داخل
`AcademyService.create_tenant()` كـ"تسخين مسبق" (eager warm-up) اختياري
لتقليل زمن أول عملية مالية لكل تينانت جديد. أي، الخيارين معًا وليس
أحدهما فقط — الكسل يضمن الصحة، والإنشاء المسبق يضمن الأداء.

### 2.4 الحماية من تسجيل الدخول والظهور في القوائم

**أ. حظر تسجيل الدخول (فعليًا موجود بالفعل عبر `is_active`):**

`identity/service.py:106-109` (`authenticate`):
```python
async def authenticate(self, username_or_email: str, password: str, ...) -> Optional[User]:
    user = await self.user_repo.get_by_username_or_email(username_or_email, self.tenant_id)
    if not user or not verify_password(password, user.hashed_password) or not user.is_active:
        return None
```

و`core/security.py:137` (`get_current_user`، يتحقق من كل توكن):
```python
if not user.is_active:
    raise AuthenticationError("User is inactive")
```

**كلا المسارين** (تسجيل الدخول بكلمة مرور، والتحقق من التوكن) يرفضان
أي مستخدم `is_active=False` بالفعل — بلا أي تعديل إضافي. لذلك:
- حساب النظام يُنشأ بـ`is_active=False` منذ البداية.
- `hashed_password` يُملأ بقيمة غير قابلة للتحقق أصلًا (مثلًا
  `get_password_hash(uuid.uuid4().hex)` — قيمة عشوائية لا يعرفها أحد،
  وليست `nullable` أصلًا في الموديل فيجب ملؤها بشيء).
- هذا **يكفي وحده** لمنع تسجيل الدخول فعليًا، حتى بدون `is_system_account`.

**ب. لماذا نحتاج `is_system_account` رغم أن `is_active=False` يكفي للحظر؟**

- **دفاع متعدد الطبقات (defense in depth)**: لو غيَّر أحدهم `is_active`
  لحساب النظام بالخطأ مستقبلًا (مثلًا عبر سكربت إداري عام "فعّل كل
  المستخدمين غير النشطين")، يبقى `is_system_account=True` علامة صريحة
  منفصلة يمكن فحصها بشكل مستقل.
- **الفلترة من القوائم**: لا توجد حاليًا في الكود أي نقطة نهاية (endpoint)
  فعلية تسرد كل مستخدمي التينانت (تحققت من `identity/router.py` — لا
  يوجد `GET /users` أو ما شابه). لكن هذا يعني أن أي endpoint من هذا
  النوع يُضاف **مستقبلًا** يجب أن يفلتر
  `WHERE is_system_account = False` بشكل افتراضي — `is_active=False`
  وحده غير كافٍ هنا لأنه قد يخفي أيضًا مستخدمين حقيقيين مُعطَّلين
  (banned) بالخطأ عن هذا التمييز.
- **التوضيح الدلالي في `authenticate()` و`get_current_user`**: أضف فحصًا
  صريحًا `if user.is_system_account: raise/return None` **بمعزل** عن
  `is_active`، لتوثيق النية بوضوح في الكود نفسه (لا تعتمد فقط على تأثير
  جانبي لعلم آخر).

**ج. لا حاجة لتعديل `require_sector`/`require_roles`/`get_current_superuser`**
— هذه كلها dependencies تُشغَّل فقط بعد نجاح `get_current_user`، وحساب
النظام لن يصل إليها أصلًا لأنه لا يستطيع حتى الحصول على توكن صالح
(لا يعرف أحد كلمة مروره، ولو حاول فسيُرفض في `authenticate`).

---

## 3. Migration مقترحة (وصف فقط — بلا تنفيذ)

يتبع نمط الملفات الموجودة فعليًا في `eppne-backend/migrations/versions/`
(آخر رقم موجود: `033_drop_entity_representatives_table.py`، بأسلوب
`op.add_column` بسيط كما في
`030_add_signature_pub_key_to_entity_memberships.py`).

**اسم الملف المقترح**: `034_add_is_system_account_to_users.py`

| البند | القيمة المقترحة |
|---|---|
| الجدول | `users` |
| العمود | `is_system_account` |
| النوع | `Boolean` |
| `nullable` | `False` |
| `server_default` | `'false'` (حتى لا تفشل الصفوف الملايين الموجودة فعليًا) |
| Index؟ | نعم — `Index("ix_users_tenant_system_account", "tenant_id", "is_system_account")` مركّب، لأن نمط البحث الأساسي للدالة هو "أعطني حساب النظام لهذا التينانت تحديدًا" (`WHERE tenant_id = X AND is_system_account = True`) — مطابق تمامًا لأسلوب الفهارس المركّبة الموجودة فعليًا في نفس الملف (`ix_audit_logs_tenant_user` في `finance/models.py:133`). |
| `downgrade()` | `op.drop_column('users', 'is_system_account')` |

**✅ القرار (2026-08-24، راجع §7 بند 2): نعم — أضف partial UNIQUE index.**

قبل الإطلاق، تكلفة إضافة القيد الآن صفر تقريبًا مقابل تكلفة إصلاح
تصادم بيانات حقيقي بعد الإطلاق. نفس أسلوب partial index **موجود فعليًا
في المشروع** كسابقة مباشرة —
`Transaction.__table_args__` في `finance/models.py:52`:
```python
Index("ix_transactions_idempotency_key", "idempotency_key", unique=True,
      postgresql_where=text("idempotency_key IS NOT NULL"))
```
بنفس الأسلوب تمامًا، يُضاف لجدول `users`:
```python
op.create_index(
    "uq_users_tenant_system_account",
    "users",
    ["tenant_id"],
    unique=True,
    postgresql_where=sa.text("is_system_account = true"),
)
```
هذا يمنع على مستوى قاعدة البيانات (وليس فقط منطق التطبيق) وجود أكثر من
صف واحد بـ`is_system_account=True` لنفس `tenant_id` — يغلق تمامًا
احتمال الـrace condition بين طلبين متزامنين لأول عملية مالية لتينانت
جديد (راجع §7 بند 2 للتفصيل الكامل).

**إضافة ثانية لنفس الـmigration (أو migration منفصلة تالية مباشرة،
`035_add_system_to_systemrole_enum.py`) — بند القرار §7-6:**

`system_role` في `identity/models.py:50` معرَّف كـ
`Column(SQLEnum(SystemRole), ...)`، وهو **Postgres native ENUM type**
فعليًا في القاعدة (مؤكَّد من
`migrations/versions/71820e4fe1f3_initial_migration_all_34_sectors_final.py:109`:
`sa.Enum('USER', 'ADMIN', 'SUPER_ADMIN', 'EXECUTIVE_DIRECTOR', name='systemrole')`).
إضافة قيمة جديدة لـenum من نوع Postgres native **ليست** `ALTER COLUMN`
عادية — هي:
```python
def upgrade() -> None:
    op.execute("ALTER TYPE systemrole ADD VALUE IF NOT EXISTS 'SYSTEM'")
```
⚠️ **تحذير تشغيلي معروف في Postgres**: `ALTER TYPE ... ADD VALUE` لا يمكن
استخدام القيمة الجديدة في **نفس المعاملة (transaction)** التي أُضيفت
فيها (قيد حتى في Postgres 12+ الذي سمح بتشغيلها داخل transaction لأول
مرة). إذا كان Alembic هنا يُشغّل كل migration داخل transaction واحدة
(الوضع الافتراضي)، فقد تحتاج هذه الـmigration تحديدًا فصلًا صريحًا
(`op.execute("COMMIT")` قبلها، أو تفعيل autocommit block) حتى لا يفشل
أي كود لاحق في **نفس الـdeployment** يحاول استخدام `SystemRole.SYSTEM`
فورًا. تفصيل تنفيذي يستحق تحققًا مباشرًا من إعداد `alembic/env.py` وقت
التنفيذ الفعلي — خارج نطاق التوثيق هنا لكن موثَّق كتحذير صريح.
لا `downgrade()` نظيف مقابل لحذف قيمة enum في Postgres (يتطلب إعادة
بناء النوع بالكامل) — يُوثَّق كقيد معروف في تعليق أعلى الدالة، بلا حل
فعلي مطلوب.

---

## 4. خريطة التحويل: كل موقع من الـ9، الكود الحالي → الكود بعد الاستبدال

| # | الدومين.الدالة | الموقع (ملف:سطر) | النمط الفرعي الحالي | القيمة الحالية | بعد الاستبدال |
|---|---|---|---|---|---|
| 1 | `commerce.release_commissions` | `commerce/service.py:310` | (١) رقم هاردكودد كـ`sender_id` | `sender_id=1` | `sender_id=(await get_or_create_system_account(self.db, self.tenant_id)).id` |
| 2 | `affiliate.withdraw_commissions` | `affiliate/service.py:477` | (١) رقم هاردكودد كـ`sender_id` | `sender_id=1` | نفس النمط أعلاه |
| 3 | `iot.settle_carbon_credits` | `iot/service.py:213` | (١) رقم هاردكودد كـ`sender_id` | `sender_id=1` | نفس النمط أعلاه (ملاحظة: الدالة هنا تُنشئ `FinanceService(self.db, tenant_id)` محليًا بمتغير `tenant_id` الممرَّر كباراميتر، وليس `self.tenant_id` — استخدم نفس المتغير المحلي عند استدعاء الدالة المركزية) |
| 4 | `social.subscribe_group_to_plan` | `social/service.py:642-643` | **مزدوج**: (١) رقم هاردكودد **أسوأ من `1`** كـ`sender_id` + (٣) بريد ثابت غير مضمون كـ`receiver_email` في **نفس الاستدعاء** | `sender_id=0, receiver_email="saas@eppne.com"` | ✅ **محسوم (§7 بند 3)** — حساب نظام واحد شامل لكل تينانت، لا حساب منفصل لكل دومين: `receiver_email=(await get_or_create_system_account(self.db, tenant_id)).email` — ويُحذف `sender_id=0` بالكامل (المجموعة `group_id` هي الطرف الدافع فعليًا، لا حاجة لطرف مُرسِل نظامي هنا أصلًا؛ هذا الموقع كان يحتاج مستقبِلًا فقط، والقيمة `sender_id=0` كانت زائدة عن الحاجة وليست بديلًا شرعيًا لأي شيء) |
| 5 | `social.request_physical_gift` | `social/service.py:559` | (٣) بريد ثابت غير مضمون كـ`receiver_email` | `receiver_email="shop@eppne.com"` | `receiver_email=(await get_or_create_system_account(self.db, tenant_id)).email` |
| 6 | `saas.pay_invoice` | `saas/service.py:309-310` | **مزدوج**: (٢) `tenant_id` مُفسَّر غلط كـ`sender_id` + (٣) بريد ثابت غير مضمون كـ`receiver_email` في **نفس الاستدعاء** | `sender_id=self.tenant_id, receiver_email="system@eppne.com"` | ✅ **محسوم (§7 بند 4)** — الدافع الرسمي = `AcademyTenant.admin_id` بتاع نفس التينانت: `sender_id=(await get_tenant_admin_id(self.db, self.tenant_id))`, `receiver_email=(await get_or_create_system_account(self.db, self.tenant_id)).email` — ⚠️ يتطلب إضافة `AcademyRepository.get_tenant_by_id` (غير موجودة حاليًا، راجع §7 بند 4 للتفصيل) |
| 7 | `saas.process_auto_renewals` | `saas/service.py:169-170` | **مزدوج**: (٢) `tenant_id` مُفسَّر غلط كـ`sender_id` + (٣) بريد ثابت غير مضمون كـ`receiver_email` | `sender_id=target_tenant, receiver_email="system@eppne.com"` | نفس نمط #6 بالضبط، لكن بـ`target_tenant` بدل `self.tenant_id`: `sender_id=(await get_tenant_admin_id(self.db, target_tenant))`, `receiver_email=(await get_or_create_system_account(self.db, target_tenant)).email` |
| 8 | `projects.add_contribution` | `projects/service.py:185` | (٣) بريد ثابت غير مضمون كـ`receiver_email` | `receiver_email="system@eppne.com"` | `receiver_email=(await get_or_create_system_account(self.db, tenant_id)).email` |
| 9 | `academy.enroll_in_course` | `academy/service.py:349` | (٣) بريد ثابت غير مضمون كـ`receiver_email` | `receiver_email="academy@eppne.com"` | `receiver_email=(await get_or_create_system_account(self.db, self.tenant_id)).email` |

**ملاحظة على العدّ**: طلبك ذكر "7 دومينات" — هذا صحيح لعدد الدومينات
(commerce, affiliate, iot, social, saas, projects, academy)، لكن عدد
**مواقع الاستدعاء الفعلية** 9 لأن `social` (مواقع 4+5) و`saas`
(مواقع 6+7) لكل منهما موقعان منفصلان. كما اكتشفتُ أثناء القراءة أن
الموقعين #4 و#6 يحملان **نمطين فرعيين معًا في نفس الاستدعاء**، وليس
نمطًا واحدًا كما قد يوحي التصنيف الأصلي — موثَّق أعلاه بدقة.

---

## 5. أنماط مجاورة لوحظت أثناء القراءة — خارج نطاق هذا المستند عمدًا

أثناء قراءة الكود وجدتُ نمطًا **مختلفًا تمامًا** منتشرًا في أكثر من 10
دومينات إضافية (`commerce`, `health`, `employment`, `digital_twin`,
`communications`, `manufacturing`, `logistics`, `insurance`,
`invitations`, ...): دالة `_get_user_email` تُرجع بريدًا **مُلفَّقًا**
(`f"user_{user_id}@eppne.com"`) كـfallback عند فشل جلب المستخدم الحقيقي
— أحيانًا حتى **بلا أي محاولة استعلام فعلية** (`commerce/service.py:36-37`).

هذا نمط بق مختلف (بريد وهمي كـfallback على مستخدم عادي، وليس حساب نظام
مفقود) — **لم يُطلب مني تناوله اليوم وأتركه كما هو**، لكنه يستحق سويپ
أمان منفصل لاحقًا إن رغبت.

---

## 6. أسئلة مفتوحة صريحة — لا افتراضات، بانتظار قرارك

> **كل الأسئلة الستة أدناه محسومة الآن — راجع §7 للقرار النهائي والتبعات
> التنفيذية لكل واحد. هذا القسم باقٍ كسجل لتحليل الخيارات الذي بُني عليه
> كل قرار.**

**1) توقيت الإنشاء (Eager vs Lazy vs كلاهما)** — راجع القسم 2.3 بالتفصيل.
   توصيتي: كلاهما (كسول دائمًا داخل الدالة نفسها + استدعاء تسخين مسبق
   من `create_tenant`)، لكن هذا قرارك.

**2) هل نحتاج partial UNIQUE index يمنع أكثر من حساب نظام واحد لكل
   تينانت؟** (القسم 3) — أم أن `get_or_create` بمنطق تطبيقي (SELECT ثم
   INSERT إن لم يوجد) كافٍ دون قيد على مستوى قاعدة البيانات؟ الفرق
   مهم عند تزامن (race condition) طلبين لأول عملية مالية لنفس التينانت
   الجديد في نفس اللحظة تقريبًا.

**3) الموقع #4 (`social.subscribe_group_to_plan`)** — الكود الحالي
   يحوّل من `sender_id=0` (وهمي بالكامل) إلى `receiver_email="saas@eppne.com"`
   (حساب نظام آخر مختلف دلاليًا عن `"system@eppne.com"` المستخدم في باقي
   المواقع!). هل يُفترض أن **كل** الدومينات السبعة تتشارك **نفس** حساب
   النظام لكل تينانت (حساب واحد شامل)، أم أن كل دومين (saas, academy,
   shop) يحتاج حسابه النظامي **الخاص به** ضمن نفس التينانت (عدة حسابات
   نظام لكل تينانت، مصنَّفة بنوع/دومين)؟ هذا يغيّر توقيع الدالة جذريًا:
   `get_or_create_system_account(db, tenant_id)` مقابل
   `get_or_create_system_account(db, tenant_id, domain: str)`.

**4) المواقع #6 و#7 (`saas.pay_invoice`, `process_auto_renewals`)** —
   حاليًا الطرفان (المرسِل والمستقبِل) **كلاهما خاطئ** في نفس الاستدعاء
   (`sender_id` = تفسير غلط لـ`tenant_id`، و`receiver_email` = بريد
   ثابت غير مضمون). استبدال `receiver_email` وحده بحساب النظام المركزي
   واضح، لكن من يجب أن يكون **المرسِل** الفعلي لدفع فاتورة؟ لا يوجد
   حاليًا مفهوم "محفظة خزينة التينانت" منفصلة عن محافظ المستخدمين
   الأفراد (`Wallet` مرتبطة دائمًا بـ`user_id` فردي، ليس بـ`tenant_id`
   وحده) — فهل الحل هو: (أ) حساب النظام نفسه يصبح كِلا الطرفين بمعنى
   مختلف (تحويل داخلي/محاسبي رمزي)، أم (ب) `pay_invoice`/
   `process_auto_renewals` يحتاجان باراميتر `payer_id` صريح غير موجود
   حاليًا في توقيعهما، يُمرَّر من الـrouter (من هوية الطالب/العميل
   الفعلي الذي يدفع)؟ هذا قرار منطق أعمال (business logic) وليس مجرد
   استبدال قيمة تقنية.

**5) اسم/توقيع الحساب النظامي في قاعدة البيانات** —
   `User.email` و`User.username` كلاهما **فريد عالميًا** (وليس لكل
   تينانت). ما نمط التوليد المفضَّل لديك؟ مثلًا:
   - Email: `system+tenant-{tenant_id}@internal.eppne.local`
   - Username: `__system_tenant_{tenant_id}__`

   أم نمط آخر تفضّله؟ هذا التفصيل حاسم لأن أي محاولة لاستخدام نفس
   القيمة الحرفية (`"system@eppne.com"`) لكل التينانتات ستصطدم فورًا
   بقيد `UNIQUE` (وهي بالضبط المشكلة الموثّقة في القسم 1.4).

**6) `system_role`** — هل يبقى الحساب النظامي بـ`SystemRole.USER`
   الافتراضي (لا فرق عمليًا لأنه لن يسجّل دخول أصلًا)، أم تفضّل قيمة
   جديدة صريحة في الـenum (مثل `SYSTEM`) لوضوح إضافي في أي استعلام
   تحليلي/تقرير مستقبلي يفحص `system_role` مباشرة؟

---

## 7. القرارات النهائية والتبعات التنفيذية (محدَّث 2026-08-24)

كل الأسئلة الستة محسومة. هذا القسم هو المرجع الحاسم لأي جلسة تنفيذ
لاحقة — يوثّق القرار + أي تبعية تقنية جديدة اكتشفتُها أثناء التحقق من
قابلية التنفيذ الفعلية لكل قرار (لا تزال هذه جلسة توثيق فقط؛ التحقق
كان بالقراءة فقط، بلا أي Edit).

### بند 1 — توقيت الإنشاء: Eager + Lazy معًا ✅

قرار نهائي: الدالة `get_or_create_system_account` نفسها كسولة دائمًا
(idempotent get-or-create حقيقي)، ويُضاف استدعاء تسخين مسبق لها داخل
`AcademyService.create_tenant()` (`academy/service.py:55-58`) مباشرة
بعد إنشاء صف `AcademyTenant`. لا تبعية تقنية جديدة — كلا الموقعين
(الدالة المركزية + نقطة `create_tenant`) موثَّقان بالفعل في §2.3.

### بند 2 — Partial UNIQUE index: نعم ✅

موثَّق بالتفصيل الكامل (بما فيه الكود الدقيق بأسلوب المشروع نفسه، مطابقًا
لسابقة `ix_transactions_idempotency_key` الموجودة فعليًا) في §3 أعلاه.
لا حاجة لتكرار هنا — راجع §3.

### بند 3 — حساب واحد شامل لكل تينانت (لا حسابات منفصلة لكل دومين) ✅

يؤكد التوقيع الأصلي المقترح في §2.2:
`get_or_create_system_account(db: AsyncSession, tenant_id: int) -> User`
— **بلا** باراميتر `domain` إضافي. هذا يحل تلقائيًا تناقض الموقع #4
الموثَّق في جدول §4 (لم يعد هناك `"saas@eppne.com"` منفصل عن
`"system@eppne.com"` — كلاهما يصبحان استدعاءً واحدًا لنفس الدالة بنفس
`tenant_id`).

**تبعية للتنفيذ المستقبلي (ليست جزءًا من نطاق اليوم، لمجرد الأمانة
التقنية)**: بما أن كل التحويلات المالية للدومينات السبعة ستمر الآن عبر
**نفس** حساب النظام لكل تينانت، فإن `Wallet` الخاصة بهذا الحساب ستُراكم
حركة مالية من كل الدومينات مجتمعة بلا تمييز في `Transaction.notes`
سوى النص الحر الموجود بالفعل في كل موقع (`notes=f"..."`) — كافٍ للتتبع
اليدوي، لكن أي تقرير تحليلي مستقبلي يريد فصل الإيرادات حسب الدومين
سيحتاج تحليل `Transaction.notes` نصيًا بدل عمود مخصَّص. ليس عيبًا في
القرار (القرار صحيح ومبرَّر) — فقط ملاحظة جانبية تستحق التوثيق.

### بند 4 — الدافع في `pay_invoice`/`process_auto_renewals` = `AcademyTenant.admin_id` ✅

القرار سليم معماريًا ويستخدم بنية موجودة فعليًا بدل اختراع مفهوم جديد،
كما وصفت. تحقّقتُ من قابلية التنفيذ الفعلية وهذه هي التبعيات الدقيقة:

**أ. لا توجد حاليًا دالة `get_tenant_by_id` في `AcademyRepository`.**
تحققت من `academy/repository.py` بالكامل — الدالة الوحيدة المتعلقة
بجلب تينانت هي `get_tenant_by_domain(domain: str)`
(`academy/repository.py:99-110`)، وليس بحث بالـ`id`. تنفيذ هذا القرار
لاحقًا سيحتاج إضافة دالة جديدة بسيطة على نفس النمط:
```python
async def get_tenant_by_id(self, tenant_id: int) -> Optional[AcademyTenant]:
    result = await self.db.execute(
        select(AcademyTenant).where(AcademyTenant.id == tenant_id)
    )
    return result.scalar_one_or_none()
```
(لا تنفيذ الآن — فقط توثيق أن هذه التبعية موجودة وغير مسدودة بأي عائق
معماري، لمجرد أنها غير مكتوبة بعد).

**ب. الاستيراد عبر الدومينات (`saas` → `academy`) نمط مقبول فعليًا
ومُستخدَم على نطاق واسع في المشروع.** تحققت عبر بحث شامل: أكثر من 20
ملف عبر دومينات مختلفة (`commerce`, `social`, `health`, `employment`,
`insurance`, ...) يستوردون بالفعل
`from app.domains.academy.models import AcademyTenant` مباشرة، و
`employment/service.py:28` يستورد حتى `AcademyRepository` نفسها
(`from app.domains.academy.repository import AcademyRepository`) —
تمامًا نفس النمط المطلوب هنا لـ`saas/service.py`. **لا حاجز طبقي
(layering barrier) يمنع هذا القرار.**

**ج. حالة حافة (edge case) تستحق ملاحظة، بلا حاجة لقرار إضافي الآن**:
`admin_id` يمكن أن يتغيّر بمرور الوقت (تينانت يغيّر مسؤوله الإداري) —
القيمة المستخدَمة كـ`sender_id` في `pay_invoice` ستكون **دائمًا** أيًا
كان الـadmin الحالي وقت الدفع، وليس ذلك الذي أنشأ التينانت أصلًا. هذا
سلوك منطقي ومتوقَّع (الفاتورة تُنسب لإدارة التينانت الحالية، ليست
مجمَّدة على شخص تاريخي)، ولا يحتاج تدخلًا إضافيًا — فقط توثيق أن هذا هو
السلوك الضمني المترتب على القرار.

### بند 5 — نمط التسمية ✅

`system+tenant-{tenant_id}@internal.eppne.local` +
`__system_tenant_{tenant_id}__` كما هو، بلا تعديل. راجع §6 بند 5
للتفاصيل الكاملة (سبب الحاجة، القيدان `UNIQUE` على `email`/`username`).

### بند 6 — `SystemRole.SYSTEM` جديد ✅

موثَّق بالتفصيل الكامل (بما فيه تحذير `ALTER TYPE ... ADD VALUE`
التشغيلي في Postgres) في §3 أعلاه ضمن قسم الـmigration. راجع §3.

---

### ملخص جاهز للتنفيذ — كل ما يحتاجه أي جلسة تنفيذ لاحقة

1. Migration `034_add_is_system_account_to_users.py`: عمود
   `is_system_account` + partial unique index (§3).
2. Migration `035_add_system_to_systemrole_enum.py`: قيمة enum جديدة
   `SYSTEM` + تحذير الـtransaction (§3).
3. `app/core/system_account_service.py`: دالة
   `get_or_create_system_account(db, tenant_id) -> User` — كسولة
   idempotent، تستخدم `add()+flush()+refresh()` **وليس**
   `UserRepository.create()` كما هي (§1.5).
4. إضافة `AcademyRepository.get_tenant_by_id(tenant_id) -> Optional[AcademyTenant]`
   (§7 بند 4-أ) — تبعية جديدة لدعم قرار §7 بند 4.
5. استدعاء تسخين مسبق داخل `AcademyService.create_tenant()` (§7 بند 1).
6. استبدال المواقع التسعة حسب جدول §4 المحدَّث (بما فيه القرارات
   النهائية للمواقع #4، #6، #7).
7. إضافة فحص صريح `if user.is_system_account: ...` في `authenticate()`
   و`get_current_user` (§2.4-ب)، بمعزل عن الاعتماد الضمني على
   `is_active=False` فقط.
