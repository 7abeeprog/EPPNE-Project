# Phase 15 — تصميم إصلاح ثغرة self-enrollment في `identity/register`
(مرحلة تصميم وتشخيص فقط — **صفر تنفيذ**، بانتظار موافقة صريحة)

> السياق: هذه الثغرة اكتُشفت واتحقَّق منها حيًا في Phase 9
> (`phase9-audit-identity-report.md`) وأُعيد تصنيفها وتوثيقها بدقة في
> Phase 14 (`critical-finding-xtenant-systemic.md`, قسم "🟡 فئة مختلفة
> تمامًا"). لم يبحث أي phase سابق تصميم الإصلاح — هذا هو أول ملف يفعل ذلك.

---

## 1. فهم الكود الحالي (قراءة مباشرة، بتاريخ اليوم)

### `get_current_tenant` — الجذر التقني (`app/api/deps.py:144-153`)
```python
class SimpleTenant:
    id: int

async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```
**ملاحظة مهمة تصحح افتراض ملف `critical-finding-xtenant-systemic.md`:** النسخة
المعروضة هناك في قسم "الاقتراح المعماري" (اللي بتفحص `current_user` قبل
الرجوع للهيدر) هي نسخة **مقترحة مستقبلية**، مش الكود الفعلي الحالي. الكود
الحالي **أبسط وأخطر**: بيرجّع قيمة الهيدر مباشرة دايمًا (افتراضي `1`)، بلا
أي فحص لوجود مستخدم مُصادَق عليه أصلًا. هذا الفرق غير مؤثر على مسار
`register` نفسه (لأنه أصلًا pre-auth، مفيش `current_user` في اللحظة دي بأي
نسخة)، لكنه مهم للدقة.

### مسار `register` (الثغرة) — `identity/router.py:28-38` → `service.py:61-104`
```python
@router.post("/register", ...)
async def register(user_in: UserCreate, request: Request,
                    tenant: SimpleTenant = Depends(get_current_tenant), ...):
    service = UserService(db, tenant.id)   # tenant.id = قيمة الهيدر مباشرة
    user = await service.register(user_in, idempotency_key)
```
داخل `UserService.register` (`service.py:90`): `tenant_id=self.tenant_id`
بيتكتب مباشرة في صف `User` الجديد. **صفر تحقق من دعوة أو صلاحية أو ملكية —
أي زائر غير مُصادَق عليه يقدر يسجّل حساب تحت أي `tenant_id` موجود بمجرد
تغيير هيدر `X-Tenant-ID`.** هذه القيمة بعدين بتتحط كـclaim `tenant_id` في
الـJWT الموقَّع (`service.py:117`)، فتبقى هي "الهوية" الموثوقة للمستخدم في
باقي حياة الجلسة عبر كل دومين تاني في المشروع.

### مسار `login` (مؤكَّد آمن، **لن يُلمس**) — `router.py:40-54` → `service.py:106-113`
`authenticate()` بيستدعي `get_by_username_or_email(login, tenant_id)`
(`repository.py:27-38`) اللي بيفلتر بـ`username/email` **و**`tenant_id`
الهيدر معًا. بما إن `username`/`email` **unique عالميًا** على مستوى الجدول
كله (`models.py:34-35`: `unique=True` بدون تركيبة مع `tenant_id`)، فأي هيدر
مخالف لتينانت الحساب الحقيقي بيرجّع "مستخدم غير موجود" ويفشل الدخول —
fail-safe فعليًا، ومؤكَّد حيًا في Phase 9. **ملاحظة جانبية (بدون اقتراح
تغيير الآن):** بما إن `username`/`email` unique عالميًا، الهيدر مش ضروري
تقنيًا حتى في `login` — ممكن تحديد `tenant_id` من صف المستخدم نفسه بعد
إيجاده بدل الاعتماد على الهيدر إطلاقًا. مطروحة كخيار تبسيط إضافي اختياري
تحت (قسم 4)، مش قرار.

### باقي الـ8 endpoints المحمية في identity
كلها بتستخدم `current_user.id` + `tenant.id` (من الهيدر) معًا في الفلترة،
ومؤكَّدة SAFE حيًا في Phase 9 (هيدر مزوَّر = 404 fail-safe، مش تسريب). **لن
تُلمس في هذه المرحلة إطلاقًا**، بما فيها `me`, `sessions`, `revoke-all`,
`me/password`, `me` DELETE.

---

## 2. التصميم المقترح

### 2.1 الـtenant الرئيسي الثابت لمسار التسجيل العام

**الملاحظة الحاسمة:** `scripts/seed_tenant.py` بيزرع **أكثر من tenant واحد**
ديناميكيًا (بحث بـ`domain`، مش بـID ثابت) — `localhost.com` و`eppne.com` في
نفس التشغيلة. **لا يوجد حاليًا افتراض آمن إن `tenant_id=1` هو "التينانت
الرئيسي"** — ده مجرد قيمة افتراضية للهيدر، مش قرار معماري موثَّق.

**المقترح:** إضافة حقل صريح في `app/core/config.py` (`Settings`):
```python
PUBLIC_REGISTRATION_TENANT_ID: int = Field(
    default=1,
    description="التينانت الوحيد المسموح بالتسجيل العام المباشر فيه (بدون دعوة)."
)
```
بنفس نمط الحماية الموجود فعلًا لـ`SECRET_KEY`/`FIRST_SUPERUSER_PASSWORD`
(`config.py:222-229`): في `ENVIRONMENT == "production"`، لو القيمة لسه
الافتراضية (`1`) بدون تعيين صريح في `.env`، يُرفع `ValueError` عند الإقلاع
(fail loud, مش fail silent). في بيئة التطوير، تحذير `logger.warning` فقط
(نفس أسلوب السطر 240-243 الحالي).

**قرار مؤكَّد (بتوجيه صريح من المستخدم + تحقق حي من قاعدة البيانات
المحلية بتاريخ اليوم):** القيمة **لازم تكون `tenant_id` ثابت من قاعدة
البيانات فعليًا (رقم/معرّف داخلي)، مش مبنية على الدومين (`eppne.com`/
`localhost.com`) إطلاقًا** — إحنا شغالين على `localhost` دلوقتي وهنربط
بدومينات حقيقية مختلفة بعد الرفع لاحقًا، وربط الدومين بالتينانت **موضوع
منفصل تمامًا خارج نطاق Phase 15**.

**الفحص الحي (read-only، `SELECT` مباشر عبر `asyncpg` على
`DATABASE_URL` من `.env`، صفر تعديل):**
```
academy_tenants: id=1, name='Local Test Tenant', domain='test.local',
                 admin_id=1, is_active=True
users: tenant_id=1 → 7 مستخدم
```
**يوجد تينانت واحد فقط فعليًا في قاعدة البيانات المحلية حاليًا: `id=1`**
(ملاحظة: اسمه ونطاقه مختلفان عن أسماء `seed_tenant.py` —
`localhost.com`/`eppne.com` — يعني `seed_tenant.py` لم يُشغَّل في هذه
البيئة، والصف الحالي جاء من تأسيس مبكر مختلف (Phase 0/1 على الأرجح). غير
مهم لغرضنا هنا؛ المهم إن `id=1` هو التينانت الحقيقي الوحيد الموجود ومعاه
كل المستخدمين الحاليين).

**القرار النهائي:** `PUBLIC_REGISTRATION_TENANT_ID: int = Field(default=1, ...)`
— قيمة ثابتة صريحة تشير لـ`tenant_id=1` الموجود فعليًا، بمعزل تام عن أي
دومين يُستخدم للوصول للسيرفر. لو اتغيّر التينانت "الرئيسي" مستقبلًا (بعد
الرفع، مرحلة ربط الدومينات)، التغيير هيبقى تحديث قيمة واحدة في `.env`، مش
تعديل منطق.

### 2.2 مخطط جدول `Invitation` — مُحدَّث بعد توضيحك (دعوة = رابط إحالة/affiliate، مش دعوة إدارية بس)

**تغيير جوهري عن المسودة الأولى:** التوضيح الجديد بيحوّل مفهوم الجدول من
"دعوة إدارية يُصدرها admin لشخص محدد" إلى **"رابط تسجيل يقدر أي مستخدم
مسجّل يُنشئه لنفسه، لأغراض إحالة/عمولة مرتبطة بمنتج، وبيُستخدم كمان
(اختياريًا) كدعوة إدارية تقليدية"** — نفس الجدول يخدم الحالتين، لأن الفرق
بينهم هو بس *مين أنشأ الرابط ولإيه*، مش شكل البيانات.

**تنبيه تسمية (زي الأول):** دومين `invitations` الموجود
(`app/domains/invitations/`) نظام CRM/تسويقي منفصل تمامًا (جدول
`sovereign_invitations_v2`)، **غير مرتبط إطلاقًا**. الجدول الجديد لسه
`identity_tenant_invitations` (model: `TenantInvitation`) داخل
`app/domains/identity/` فقط.

```python
class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"   # على الأقل استخدام واحد ناجح تم
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

class TenantInvitation(Base):
    __tablename__ = "identity_tenant_invitations"

    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"),
                        nullable=False, index=True)  # تينانت المُنشئ وقت الإنشاء (مجمَّد هنا، مش محسوب لحظيًا)

    token = Column(String(64), nullable=False, unique=True, index=True)  # نص صريح، مش hash — راجع التبرير تحت
    email = Column(String, nullable=True, index=True)  # null = رابط عام قابل لإعادة الاستخدام (حالة الإحالة)؛ قيمة = دعوة شخص بعينه

    referrer_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # مين أنشأ الدعوة/الرابط — أساس ربط العمولة لاحقًا
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)  # المنتج المرتبط بالإحالة، null = دعوة عامة/tenant-only

    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False, index=True)
    max_uses = Column(Integer, nullable=True)   # null = بلا حد أقصى (حالة رابط إحالة قابل لإعادة الاستخدام)؛ رقم = دعوة محدودة الاستخدام (1 = دعوة شخص واحد تقليدية)
    current_uses = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    accepted_at = Column(DateTime(timezone=True), nullable=True)  # آخر استخدام ناجح (مفيد أساسًا لو max_uses=1)
    revoked_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_invitation_tenant_status", "tenant_id", "status"),
        Index("ix_invitation_referrer", "referrer_user_id"),
        Index("ix_invitation_product", "product_id"),
        Index("ix_invitation_email", "email"),
        Index("ix_invitation_status_expiry", "status", "expires_at"),
    )
```

**التغييرات عن المسودة الأولى ومبرراتها:**

- **`invited_by_user_id` → `referrer_user_id`** (نفس الحقل، اسم مطابق لطلبك
  ولغرضه الفعلي: ربط العمولة).
- **`invited_role` اتشال بالكامل.** بما إن أي مستخدم مسجّل هيقدر يُنشئ
  دعوة دلوقتي، السماح بتحديد دور للمدعو كان هيفتح تصعيد صلاحيات مباشر
  (مستخدم عادي يقدر يدعو حد "كـADMIN"). كل تسجيل عبر أي دعوة هينتج
  `USER` عادي بس، **بدون استثناء في هذه المرحلة** — لو احتجنا لاحقًا آلية
  "دعوة بدور إداري" منفصلة، دي هتحتاج تصميم/ضوابط خاصة بيها في جلسة
  تانية، مش امتداد على نفس الجدول ده.
- **`product_id` جديد** — `Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True`.
  اتأكَّدت إن ده **نفس نمط موجود بالفعل** في دومين `affiliate`
  (`affiliate/models.py:157`: `AffiliateLink.product_id` بيعمل FK بالظبط
  لنفس جدول `products.id`) — يعني إضافة FK من جدول identity جديد لجدول
  `products` مش سابقة غريبة على المشروع، ومفيهاش أي لمس لكود دومين
  `commerce`/`affiliate` (الـFK بيتعرَّف في migration جدول identity الجديد
  بس). اخترت `ondelete="SET NULL"` (مش `CASCADE` زي `AffiliateLink`) عشان
  حذف منتج ميمسحش سجل الدعوة التاريخي نفسه، بس يفضّي `product_id`.
- **`max_uses` بقى `nullable` (بدل `default=1` إجباري).** ده تصحيح
  منطقي ضروري: رابط إحالة/عمولة **المفروض يتكرر استخدامه من ناس كتير**،
  مش يُستهلك مرة واحدة زي دعوة الفريق الإدارية التقليدية. `null` = بلا حد،
  `1` = سلوك الدعوة التقليدية القديمة (لسه مدعوم لو حد احتاجه).
- **`token` نص صريح، مش `token_hash`.** هذا تصحيح مهم عن المسودة الأولى:
  التصميم القديم كان مفترض إن التوكن "يُعرض مرة واحدة بس وقت الإنشاء" (زي
  `RefreshToken` — سرّ جلسة حقيقي). لكن رابط إحالة/عمولة **لازم يفضل
  المستخدم قادر يشوفه/يرجعله تاني** (يلزقه في bio، يشاركه أكتر من مرة) —
  تخزينه كـhash بيمنع استرجاعه، وده كسر فعلي لحالة الاستخدام دي. اتأكَّدت
  إن المشروع أصلًا عنده نفس النمط ده (نص صريح، unique) في
  `affiliate/models.py:24`: `AffiliateProfile.referral_code`. الخاصية
  الأمنية المطلوبة هنا هي **عدم القابلية للتخمين** (entropy كافية عبر
  `secrets.token_urlsafe`)، مش السرّية عند التخزين — الرابط بطبيعته
  مُصمَّم للمشاركة العلنية.
- **`idempotency_key` اتشال.** الحاجة الأصلية كانت لمنع تكرار إنشاء نفس
  الدعوة عند retry شبكي — لكن هنا `token` نفسه unique بالفعل، وإنشاء دعوة
  عملية خفيفة (صف واحد، مفيهوش side effects مالية في هذه المرحلة). ممكن
  تتضاف لاحقًا لو ظهرت حاجة فعلية، مش لازمة الآن.

**تنبيه صريح مكرر (بناءً على تأكيدك):** الجدول ده **بيخزّن بيانات الإسناد
فقط** (`referrer_user_id` + `product_id`). **منطق حساب/استحقاق/صرف
العمولة نفسه، وربطه بدومين `affiliate` الفعلي، خارج نطاق Phase 15
بالكامل** — مؤجَّل لجلسة منفصلة. صفر كود في `affiliate/` أو
`commerce/` هيتلمس هنا.

### 2.3 شكل endpoints الجديدة + تعديل التسجيل العام

**أ. إنشاء دعوة/رابط إحالة (محمي — أي مستخدم مسجّل دخوله، مش إداري بس)**
`POST /identity/invitations` — على `protected_router`
- `current_user: User = Depends(get_current_active_user)` **فقط** — **بدون
  أي فحص دور إداري**، بناءً على توضيحك: أي مستخدم مسجّل لازم يقدر يُنشئ
  دعوة مرتبطة بمنتج عشان ياخد عمولة إحالة عليها.
- `tenant_id` بيُشتق من **`current_user.tenant_id`**، **ليس من الهيدر
  إطلاقًا** (نفس المبدأ الحرج زي المسودة الأولى — أي اعتماد على
  `get_current_tenant`/الهيدر هنا هيكرر نفس نمط ثغرات الـ20 دومين
  الموثَّقة في `critical-finding-xtenant-systemic.md`).
- `referrer_user_id = current_user.id` دايمًا (مفيش تمرير قيمة تانية من
  الـbody — منع انتحال هوية مُحيل تاني).
- Body: `TenantInvitationCreate(email?: str, product_id?: int, max_uses?: int, expires_at?: datetime)`
- Response: `TenantInvitationResponse` — يتضمن `token` **بشكل دائم قابل
  للاسترجاع** (مش مرة واحدة بس — راجع تبرير التخزين الصريح في §2.2).

**ب. قائمة/إبطال الدعوات — صلاحية على مستويين**
- `GET /identity/invitations`: **افتراضيًا بيُرجّع دعوات المستخدم الحالي
  فقط** (`WHERE referrer_user_id = current_user.id AND tenant_id =
  current_user.tenant_id`) — **بدون استثناء لأي دور**، حتى الأدمن بيشوف
  بتاعته بس في الوضع الافتراضي.
- لعرض كل دعوات التينانت (احتياج إداري)، endpoint/بارامتر منفصل صراحةً —
  مثلًا `GET /identity/invitations?scope=tenant` — **مسموح فقط لو**
  `current_user.system_role` ضمن `{ADMIN, SUPER_ADMIN, EXECUTIVE_DIRECTOR}`
  **(✅ محسومة الآن — راجع §5)**. **هذا الفصل مقصود**: منع أي التباس بين
  "دعوتي أنا" و"كل دعوات التينانت" بمجرد نسيان فلتر في الكود — الفلتر
  الافتراضي الآمن (بتاعتي أنا بس) هو نفسه بدون أي شرط دور، والتوسعة
  للإداري صريحة وواضحة في الكود.
- `POST /identity/invitations/{id}/revoke`: صاحب الدعوة (`referrer_user_id
  == current_user.id`) يقدر يُبطل بتاعته، أو مستخدم بدور
  `{ADMIN, SUPER_ADMIN, EXECUTIVE_DIRECTOR}` يقدر يُبطل أي دعوة في تينانته.

**ج. التسجيل بدعوة (عام، pre-auth، endpoint جديد كليًا)**
`POST /identity/register-with-invitation` — على `router` (العام)
```python
async def register_with_invitation(data: InvitationRegisterRequest, request: Request, db=Depends(get_db)):
    # 1. بحث مباشر بـ token == data.token في identity_tenant_invitations
    # 2. تحقق: status == PENDING, not expired,
    #    max_uses is None OR current_uses < max_uses
    # 3. لو invitation.email موجود: لازم يطابق data.email (case-insensitive) وإلا رفض
    # 4. tenant_id = invitation.tenant_id  ← من الدعوة نفسها، ليس من الهيدر وليس من الـbody
    # 5. UserService(db, invitation.tenant_id).register(user_create_data, idempotency_key)
    # 6. تحديث invitation: current_uses+=1, accepted_at=now(),
    #    status=ACCEPTED لو (max_uses is not None AND current_uses وصل max_uses)
    #    وإلا يفضل PENDING (رابط إحالة قابل لإعادة الاستخدام)
```
`InvitationRegisterRequest` = نفس حقول `UserCreate` + `token: str`.
Rate limiting **أشد** من `register` العادي (محاولات تخمين التوكن خطر
إضافي) — مثلًا `max_requests=5, window_seconds=60` بدل `10`.

**د. التعديل الوحيد على endpoint موجود بالفعل**
`POST /identity/register` (`router.py:28-38`) — **التغيير الجوهري الوحيد
في كل هذا التصميم على كود مسار حي فعليًا**:
```python
# قبل:
async def register(user_in: UserCreate, request: Request,
                    tenant: SimpleTenant = Depends(get_current_tenant), db=...):
    service = UserService(db, tenant.id)

# بعد:
async def register(user_in: UserCreate, request: Request, db=...):
    service = UserService(db, settings.PUBLIC_REGISTRATION_TENANT_ID)
```
إزالة `Depends(get_current_tenant)` من هذا الـendpoint تحديدًا بالكامل —
هيدر `X-Tenant-ID` هيبقى بلا أي تأثير على مين بيتسجل فين عبر هذا المسار.
`login` **لن يتغيّر** (مؤكَّد آمن، خارج نطاق هذا الإصلاح).

---

## 3. الـmigration وترتيب التنفيذ التدريجي (لما يُعتمد التصميم)

الترتيب مصمَّم بحيث **كل خطوة إضافية وقابلة للتحقق بمعزل عن اللي بعدها**،
والخطوة الوحيدة اللي بتغيّر سلوك endpoint حي فعليًا (5) هي **الأخيرة
عمدًا** — نفس انضباط Phase 9/10c/12 (فحص حي كامل بعد كل خطوة تغيّر سلوك).

1. **`config.py`**: إضافة `PUBLIC_REGISTRATION_TENANT_ID` + منطق تحقق
   production (زي `SECRET_KEY`). صفر تأثير سلوكي (لسه مفيش حد بيستخدمها).
2. **Migration جديدة بالكامل**: `CREATE TABLE identity_tenant_invitations`
   فقط (إضافي بحت، صفر تعديل على جدول موجود). تحقق: الجدول اتنشأ، صفر
   تأثير على أي endpoint حالي.
3. **Model + Repository + Schemas**: `TenantInvitation` في
   `identity/models.py`، `InvitationRepository` في `identity/repository.py`
   (أو ملف منفصل `identity/invitation_repository.py` لو الحجم استدعى)،
   `TenantInvitationCreate/Response` في `identity/schemas.py`. صفر تعديل
   في `router.py`/`service.py` الحاليين، فصفر تأثير سلوكي حي.
4. **Endpoints الجديدة** (`POST/GET/{id}/revoke /identity/invitations*` على
   `protected_router` — إنشاء متاح لأي مستخدم مسجّل، عرض/إبطال مقيّد
   بالملكية أو الدور الإداري كما في §2.3) + **endpoint التسجيل بدعوة
   الجديد** (`POST /identity/register-with-invitation`) — كلها **إضافية
   بحتة**، لا تلمس `register`/`login` الحاليين إطلاقًا. تحقق حي: مستخدم
   عادي يُنشئ رابط إحالة مرتبط بمنتج → رابط تاني يسجّل بيه → تأكيد
   المستخدم الجديد اتسجل تحت نفس تينانت المُحيل، وإن `referrer_user_id`
   محفوظ صح.
5. **التعديل الحرج الأخير**: تغيير `POST /identity/register` القديم ليتوقف
   عن الاعتماد على الهيدر ويستخدم `settings.PUBLIC_REGISTRATION_TENANT_ID`
   ثابتًا. **هذه هي الخطوة الوحيدة اللي بتغيّر سلوك مسار حي فعليًا في كل
   التصميم** — تحتاج تحقق حي كامل قبل وبعد (uvicorn فعلي، محاولة تسجيل
   بهيدر `X-Tenant-ID` مزوَّر تفشل/تُوجَّه للتينانت الثابت بدل التينانت
   المزوَّر، تسجيل شرعي عادي لسه شغال، تسجيل بدعوة لتينانت تاني لسه شغال).

---

## 4. ملاحظات مؤجَّلة (خارج النطاق، بدون نقاش تفصيلي هنا)
- الشات بوت / AI-assisted invitation writing.
- self-service tenant creation.
- تبسيط `login` لإزالة اعتماده على الهيدر بالكامل (مطروح كملاحظة اختيارية
  في قسم 1، ليس قرارًا ولا جزءًا من هذا التصميم).
- **ملاحظة عرضية غير متعلقة (اكتُشفت أثناء القراءة، خارج دومين identity
  بالكامل):** `invitations/service.py:117`
  (`_create_user_from_invitation`) بيستدعي `UserService(self.db)` بمعامل
  واحد فقط، بينما `UserService.__init__` (identity الحالي) بيتطلب
  `tenant_id` كمعامل ثانٍ إجباري — هذا هيفشل بـ`TypeError` وقت التشغيل
  الفعلي. غير مرتبط بمهمة Phase 15 (دومين `invitations`، ليس `identity`)،
  مذكور فقط للتوثيق، **لن يُلمس**.

---

## 5. نقاط قرار — محدَّثة بعد توضيحك

1. ~~قيمة `PUBLIC_REGISTRATION_TENANT_ID` الفعلية~~ — **✅ محسومة**:
   `tenant_id=1` (§2.1، مؤكَّدة بفحص حي لقاعدة البيانات المحلية).
2. ~~مين يقدر يُصدر دعوة أصلًا~~ — **✅ محسومة**: أي مستخدم مسجّل دخوله
   (`get_current_active_user` فقط، بدون فحص دور) — §2.3(أ).
3. ~~`invited_role` مطلوب ولا لأ~~ — **✅ محسومة**: اتشال بالكامل من نطاق
   Phase 15 (كل تسجيل بدعوة = `USER` عادي، بدون استثناء) — §2.2.

4. ~~مين "إداري" لغرض `scope=tenant` والإبطال~~ — **✅ محسومة**:
   `system_role` ضمن `{ADMIN, SUPER_ADMIN, EXECUTIVE_DIRECTOR}` (وليس
   معيار `get_current_superuser` الحالي في `core/security.py:161-167`
   اللي بيقصرها على `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` بس — هنا محتاجين
   دالة/فحص جديد يضيف `ADMIN` كمان). هذا **لا يمنع أي مستخدم من إنشاء/
   رؤية/إبطال دعواته هو شخصيًا** بأي حال، مجرد نطاق رؤية إضافي للإداري.

**صفر نقاط قرار مفتوحة متبقية — التصميم جاهز بالكامل لموافقة التنفيذ.**

**ملاحظة صريحة (خارج نطاق Phase 15، بدون قرار مطلوب الآن):** حساب/صرف
العمولة الفعلي، وربط هذا الجدول بدومين `affiliate`، مؤجَّل بالكامل لجلسة
منفصلة — راجع التنبيه المكرر في نهاية §2.2.
