# علاقة "ولي أمر↔طالب" — جلسة تخطيط تصميم دقيق (read-only)

**تاريخ:** 2026-09-16
**النطاق:** فحص read-only بحت لتجهيز تصميم علاقة "ولي أمر↔طالب" (موافقة
متبادلة + تحقق إداري للقاصرين)، امتدادًا لـ
[[project_targeted_notifications_planning]] (نفس الجلسة السابقة اليوم لاحظت
غياب هذا الرابط تمامًا).
**ممنوع أي تعديل كود — تم الالتزام، صفر Edit/Write على كود المشروع.**

---

## 1. هل عندنا وسيلة نعرف بيها "الطالب قاصر"؟

**نعم جزئيًا — `birth_date` موجود ومُستخدَم فعليًا عند التسجيل (بعكس
`father_id`/`mother_id`)، لكن لا يوجد أي منطق "حساب العمر" أو "تحديد
القاصر" في أي مكان بالمشروع اليوم.**

### `User` model كامل (`identity/models.py:14-101`)

```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username_lower", func.lower("username")),
        Index("ix_users_email_lower", func.lower("email")),
        Index("ix_users_public_id", "public_id"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_last_login_at", "last_login_at"),
        CheckConstraint("char_length(username) >= 4", name="ck_username_min_length"),
        CheckConstraint("char_length(email) > 0", name="ck_email_not_empty"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String, unique=True, index=True, nullable=True)
    uid = Column(String(20), unique=True, index=True, nullable=True)
    did = Column(String, unique=True, nullable=True)

    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    name_ar = Column(String(100), nullable=True)
    name_en = Column(String, nullable=True)

    birth_date = Column(Date, nullable=True)
    death_date = Column(Date, nullable=True)
    marriage_status = Column(SQLEnum(MarriageStatus), default=MarriageStatus.SINGLE)

    father_id = Column(BigInteger, nullable=True)
    mother_id = Column(BigInteger, nullable=True)
    spouse_id = Column(BigInteger, nullable=True)

    sovereign_rank = Column(SQLEnum(SovereignRank), default=SovereignRank.CITIZEN_L1)
    system_role = Column(SQLEnum(SystemRole), default=SystemRole.USER, nullable=False)
    kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.UNVERIFIED)
    reputation_score = Column(Integer, default=100)

    language_preference = Column(String, default="ar")
    profile_metadata = Column(JSONB, default=dict)
    preferences = Column(JSONB, default=dict)

    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    is_system_account = Column(Boolean, default=False, nullable=False, server_default="false")
    session_version = Column(Integer, default=1)

    referred_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_login_user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    wallet = relationship("app.domains.finance.models.Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    tenant = relationship("app.domains.academy.models.AcademyTenant", foreign_keys=[tenant_id], lazy="selectin")
```

**لا يوجد عمود `age` أو `is_minor` مباشر** — العمود الوحيد ذو الصلة هو
`birth_date` (سطر 41)، من نوع `Date`، **`nullable=True`** (اختياري، مش
إجباري عند التسجيل).

### هل `birth_date` مستخدَم فعليًا، ولا عمود ميت زي `father_id`/`mother_id`؟

**مستخدَم جزئيًا — يُكتب فعليًا عند التسجيل، لكن لا يُقرأ أبدًا لحساب
العمر أو تحديد القاصر.** بحث شامل عن
`date_of_birth|age|birth_date|is_minor|minor|قاصر` في كامل `eppne-backend/app`:

| الملف | الاستخدام |
|---|---|
| `identity/models.py:41` | تعريف العمود (`Column(Date, nullable=True)`) |
| `identity/schemas.py:13` | `UserBase.birth_date: Optional[datetime]` — يظهر في `UserCreate` (عبر الوراثة) و`UserResponse` |
| `identity/service.py:86` | `birth_date=data.birth_date` — **يُكتب فعليًا** في `UserService.register()` |

**صفر مطابقة** لأي من `is_minor`, `minor`, `قاصر`, أو أي عملية حسابية على
`birth_date` (زي `relativedelta`, `age >=`, `age <`) **في كامل المشروع**.
بمعنى آخر: البيانات الخام موجودة ومحفوظة (لو المستخدم أدخلها — الحقل
اختياري وممكن يفضل `NULL`)، لكن **لا يوجد أي كود يحوّلها إلى قرار "قاصر/
راشد"**. هذا مختلف عن حالة `father_id`/`mother_id` (أعمدة ميتة 100%، بلا
قراءة ولا كتابة إطلاقًا) — `birth_date` **نصف حي**: يُكتب، لا يُقرأ
لهذا الغرض.

**الأثر على التصميم:** حساب "هل الطالب قاصر؟" ممكن تقنيًا (البيانات
موجودة لو المستخدم أدخل `birth_date`)، لكن يحتاج:
1. دالة حساب عمر جديدة بالكامل (غير موجودة اليوم).
2. معالجة حالة `birth_date IS NULL` (الحقل اختياري — نسبة غير معروفة من
   المستخدمين الحاليين عمرهم `NULL`، يحتاج فحص DB مباشر قبل الاعتماد
   عليه كمصدر وحيد للقرار).
3. قرار منتجي: هل نجعل `birth_date` إجباريًا عند التسجيل مستقبلًا لتفعيل
   هذا المنطق بثقة؟ (خارج نطاق هذه الجلسة القرائية).

---

## 2. نمط "طلب + موافقة متبادلة" — هل فيه سابقة نعيد استخدامها؟

**دومين `app/domains/invitations/` (`SovereignInvitation`) موجود
ومُطبَّق بالكامل، لكنه مبني خصيصًا لسياق CRM/تسويقي، وليس تصميمًا عامًا
لـ"موافقة متبادلة بين طرفين" — إعادة استخدامه لعلاقة ولي أمر↔طالب غير
مناسبة معماريًا.**

⚠️ **ملحوظة توضيح مهمة:** يوجد **موديلان منفصلان بنفس الاسم التصوري
"دعوة" في المشروع**، ولازم عدم الخلط بينهما:
- `app/domains/invitations/models.py` → `SovereignInvitation` (الدومين
  المطلوب فحصه هنا، اسم الفولدر نفسه `invitations`).
- `app/domains/identity/models.py:148-192` → `TenantInvitation` (دعوة
  انضمام لـ tenant، `identity_tenant_invitations`، مختلفة تمامًا، ولها
  `InvitationStatus` خاص بها من `app.core.enums` — `PENDING/ACCEPTED/
  REVOKED/EXPIRED` — بعكس `invitations.models.InvitationStatus`
  الخاص بـ`SovereignInvitation` — `DRAFT/SENT/ACCEPTED/DECLINED/
  EXPIRED`. اسمان متطابقان، enum مختلف، جدول مختلف).

### دومين `invitations` كامل (البنية)

**`models.py`** — 8 موديلات: `SovereignInvitation` (الدعوة نفسها)،
`InvitationTracking` (تتبع سلوك الزائر)، `InvitationConversation`
(محادثة AI)، `ClientInsight` (تحليل AI للعميل)، `Lead` (عميل محتمل –
CRM)، `CustomerInteraction`, `MarketingCampaign`, `SupportTicket` +
`TicketComment`.

**`SovereignInvitation`** (`invitations/models.py:88-138`) — الحقول
الجوهرية:
```python
sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
sender_entity_id = Column(Integer, nullable=True)
invitation_type = Column(SQLEnum(InvitationType), nullable=False)      # GENERAL, PRIVATE
target_type = Column(SQLEnum(InvitationTargetType), nullable=False)    # PERSON, CIVIL_ORGANIZATION, GOVERNMENT_BODY, INTERNATIONAL_ORGANIZATION, UNIVERSITY, COMPANY
target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
target_entity_identifier = Column(String(255), nullable=True)
campaign_type = Column(SQLEnum(CampaignType), nullable=False)          # BOOTCAMP, COURSE, SERVICE, PRODUCT, EVENT
campaign_id = Column(Integer, nullable=False)
discount_percentage = Column(Numeric(5, 2), default=0)
gift_coins_amount = Column(Numeric(30, 8), default=0)
status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.DRAFT)  # DRAFT, SENT, ACCEPTED, DECLINED, EXPIRED
assigned_ai_agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True)
first_clicked_at / last_clicked_at / click_count  # تتبّع تسويقي
```

**`service.py`** (1026 سطر) — الدوال الجوهرية: `create_invitation`
(تحليل AI للهدف + خصم/هدية + وكيل AI مُسنَد تلقائيًا)، `accept_invitation`
(تحويل الدعوة لـ`Lead` محوَّل + عمولة affiliate + إنشاء مستخدم جديد لو
مش موجود)، `chat_with_ai` (محادثة AI كاملة مع الزائر)، + دوال CRM كاملة
(leads, campaigns, support tickets).

### هل تصميمه عام بما يكفي لإعادة الاستخدام، ولا خاص بسياق تاني؟

**خاص بسياق تاني تمامًا — تحويل مبيعات/تسويق (Sales Conversion)، مش
"طلب علاقة بين هويتين محتاج موافقة الطرفين":**

1. **اتجاه واحد فقط (One-directional)، مش موافقة متبادلة حقيقية**:
   `sender` يبعت، `target` يقبل (`accept_invitation`) أو يترك تنتهي
   (`EXPIRED`). لا يوجد أي مفهوم "الطرف التاني يقدر يرفض بفعل صريح
   ويظهر ده كحالة منفصلة قابلة للاستعلام لاحقًا" (`DECLINED` موجود في
   الـenum لكن **لا يوجد أي endpoint أو دالة service تكتبها** — بحث في
   `service.py` و`router.py`: صفر مطابقة لـ`DECLINED` خارج تعريف الـenum
   نفسه في `models.py:33`. حالة مُعرَّفة بلا مسار تنفيذي حي).
2. **`accept_invitation` بتفترض دايمًا نية "تحويل عميل"**: بتنشئ `Lead`
   (`LeadSource.INVITATION`)، بتسجّل عمولة affiliate
   (`_register_affiliate_commission`)، وبترجع `redirect_url:
   /campaign/{campaign_id}` — **مربوطة بنيويًا بمفهوم "حملة تسويقية"
   (`campaign_id` عمود إجباري `nullable=False`)**. علاقة ولي أمر↔طالب
   مالهاش أي حملة تسويقية ترتبط بيها — إعادة الاستخدام هنا تعني إما
   إنشاء "حملة وهمية" لكل علاقة (هندسة معكوسة قبيحة)، أو تعديل الموديل
   ليصير `campaign_id` اختياريًا (تغيير معماري في جوهر الدومين).
3. **محمّل بمنطق تجاري غير ذي صلة إطلاقًا**: تحليل AI للهدف
   (`_analyze_target_user` → `AIAgentsService.execute_agent_action`)،
   خصومات (`discount_percentage`)، هدايا عملة (`gift_coins_amount`)،
   وكيل AI مُسنَد تلقائيًا (`_assign_ai_agent`)، تتبع نقرات/جلسات
   (`InvitationTracking`)، محادثة AI كاملة. كل هذا **صفر فائدة** لعلاقة
   ولي أمر↔طالب، وسحبه يعني عمليًا كتابة موديل/service جديدين من الصفر
   وليس "إعادة استخدام".
4. **`target_type` لا يشمل "قرابة عائلية"** — القيم المتاحة
   (`InvitationTargetType`, `invitations/models.py:20-26`): `PERSON,
   CIVIL_ORGANIZATION, GOVERNMENT_BODY, INTERNATIONAL_ORGANIZATION,
   UNIVERSITY, COMPANY`. `PERSON` أقرب قيمة لكنها عامة (أي شخص، مش
   تحديدًا "ولي أمر لطالب معيّن")، ولا يوجد أي حقل يربط الدعوة بـ"طالب
   مستهدَف" تحديدًا (فيه `target_user_id` بس ده المستلم نفسه، مش طرف
   ثالث "الطالب" لو المُرسَل إليه هو ولي الأمر).

**الخلاصة: `TenantInvitation`** (`identity/models.py:148-192`) هي
**الأقرب هيكليًا** (بلا أي حمولة CRM/تسويق): `token_hash` (hash فقط،
بلا secret مكشوف)، `status` (enum بسيط)، `expires_at`, `max_uses/
current_uses`, `accepted_at`, `revoked_by_user_id/revoked_at`. لكنها
**برضه اتجاه واحد** (referrer يدعو، مفيش رفض صريح من الطرف التاني —
بس قبول أو انتهاء صلاحية) — **مش نمط "موافقة متبادلة" حقيقي (كلا
الطرفين يوافق بفعل صريح) موجود في أي مكان بالمشروع اليوم.** تصميم
علاقة ولي أمر↔طالب سيكون **أول نمط موافقة-متبادلة-حقيقي** في المشروع،
مش تكرارًا لسابقة قائمة.

---

## 3. نمط "طابور تحقق إداري" — هل موجود بالفعل؟

**نعم، موجود ومكرَّر مرتين بنفس الشكل بالضبط في `sovereign_entities`
— هذا أقرب سابقة جاهزة للاقتباس شكليًا (status enum + verified_by +
verified_at + rejection_reason)، لكنه "طابور بلا تنبيه" (تفصيل حرج في
قسم 4).**

### النمط الأول: `SovereignEntity.kyb_status` (`sovereign_entities/models.py:74-78`)

```python
class KYBStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"

# على الموديل:
kyb_status = Column(SQLEnum(KYBStatus), default=KYBStatus.PENDING, index=True)
kyb_documents = Column(JSONB, default=list)
verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
verified_at = Column(DateTime(timezone=True), nullable=True)
rejection_reason = Column(Text, nullable=True)
```

### النمط الثاني: `EntityDocument.status` (`sovereign_entities/models.py:171-186`)

```python
class EntityDocument(Base):
    __tablename__ = "entity_documents"
    ...
    status = Column(String(50), default="PENDING")      # PENDING, APPROVED, REJECTED
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
```

**نفس الشكل بالحرف**: `status` (enum أو `String` حر) + `verified_by`
(FK للأدمن اللي راجع) + `verified_at` (توقيت المراجعة) + `rejection_reason`
(سبب الرفض النصي، `nullable`). هذا **قابل للاقتباس مباشرة** لتصميم علاقة
ولي أمر↔طالب: مثلًا `GuardianRelationship.status` (`PENDING_STUDENT_APPROVAL
/ PENDING_ADMIN_REVIEW / VERIFIED / REJECTED`) + `verified_by` + `verified_at`
+ `rejection_reason`.

### دالة التحقق الفعلية: `review_kyb` (`sovereign_entities/service.py:236-261`)

```python
async def review_kyb(
    self,
    entity_id: int,
    admin_id: int,
    status: str,
    rejection_reason: Optional[str] = None
) -> SovereignEntity:
    entity = await self.repo.get_entity(entity_id, self.tenant_id)
    if not entity:
        raise NotFoundError("Entity not found")
    if status == "VERIFIED":
        await self.repo.update_entity(
            entity_id, self.tenant_id,
            kyb_status=KYBStatus.VERIFIED, verified_by=admin_id, verified_at=func.now()
        )
    else:
        await self.repo.update_entity(
            entity_id, self.tenant_id,
            kyb_status=KYBStatus.REJECTED, rejection_reason=rejection_reason
        )
    return await self.repo.get_entity(entity_id, self.tenant_id)
```

مسار الاكتشاف الإداري: `GET /entities?kyb_status=PENDING`
(`sovereign_entities/router.py:37-45`, عبر `service.list_entities
(entity_type, kyb_status, ...)`) — الأدمن **يفلتر بنفسه** يدويًا عن
`PENDING`، ثم يستدعي `PUT /entities/{entity_id}/kyb/status`
(`router.py:186-197`) لتنفيذ `review_kyb`.

### `PermissionAuditLog` (`app/core/models.py:83-...`)

موديل منفصل تمامًا عن نمط "التحقق"، بيسجّل **بعد وقوع** فعل صلاحية
(`GRANT`/`REVOKE`) — ليس طابور طلبات معلَّقة، بل سجل تدقيق (audit trail)
لأحداث اكتملت بالفعل. **غير مناسب كنمط "طلب معلَّق"** — لا يحتوي على
`status=PENDING` ولا `verified_by/verified_at` بمعنى "قرار لسه منتظر".
`EntityMembership` نفسها (`app/core/models.py:40-57`) أيضًا **منح مباشر
فوري** بلا حالة `PENDING` — بتتكتب مباشرة بلا طابور موافقة (تم التحقق:
صفر عمود `status` على الموديل).

**الخلاصة: النمط الجاهز للاقتباس هو `kyb_status`/`EntityDocument.status`
في `sovereign_entities`، مش `PermissionAuditLog` ولا `EntityMembership`.**

---

## 4. أي حدث حرج/إشعار موجود حاليًا بيتبعت لأدمن؟

**لا يوجد أي إشعار push فعلي يتبعت لأدمن اليوم في كامل المشروع — حتى في
نفس نمط KYB أعلاه الذي يُفترض أنه "طابور يحتاج مراجعة أدمن".**

- بحث شامل عن `notify_admin|admin_notification|ADMIN_ALERT` وعن أي
  استدعاء `send_notification` مقترن بدور أدمن/superuser: **صفر مطابقة**
  في كامل `eppne-backend/app`.
- بحث عن أي دالة `get_superusers`/`list_superusers` (لجلب كل الأدمنز
  المسؤولين عن tenant عشان تُبعث لهم إشعارات): **صفر مطابقة**. لا توجد
  آلية حتى لتحديد "مين الأدمنز اللي المفروض يتبلغوا" برمجيًا.
- **`upload_kyb_document`** (`sovereign_entities/service.py:214-229`) —
  الفعل اللي المفروض "يفتح" حاجة في طابور تحقق الأدمن — **لا يستدعي
  `send_notification` ولا `event_bus.publish` إطلاقًا**. تم قراءة الدالة
  كاملة، صفر أي جانب تنبيهي.
- الاكتشاف الوحيد المتاح لأدمن اليوم هو **pull-based بالكامل**: الأدمن
  لازم يفتح `GET /sovereign-entities?kyb_status=PENDING` بنفسه بشكل
  دوري عشان يلاقي طلبات جديدة — **لا يوجد push notification في اللحظة
  اللي يتقدَّم فيها الطلب**.
- التحقق من `get_current_superuser` (`core/security.py:164-170`) يؤكد
  إن "الأدمن" في هذا المشروع = `system_role in ["SUPER_ADMIN",
  "EXECUTIVE_DIRECTOR"]` — دور موجود ومُستخدَم في endpoints حساسة (زي
  `POST /notifications/send` نفسها، `communications/router.py:94`)،
  لكن **لا يوجد أي مكان في الكود يستعلم "كل مستخدمين هذا الدور في هذا
  الـtenant" عشان يبعتلهم حاجة** — أي تصميم جديد لإشعار الأدمن سيحتاج
  بناء هذا الاستعلام من الصفر (`UserRepository` الحالية لا تحتوي على
  دالة كهذه — تم التأكد بقراءة توقيعات `UserRepository` المُستخدَمة في
  هذه الجلسة: `get_by_id`, `get_tenant_id_by_user_id`، لا وجود لأي
  `list_by_role`).

**الخلاصة: تنبيه الأدمن بطلبات ولي أمر↔طالب المعلَّقة سيكون أول تنفيذ
push notification لأدمن في المشروع كله — لا يوجد أي كود جاهز يُستدعى،
فقط نمط بيانات جاهز للاقتباس (قسم 3) بلا أي طبقة تنبيه فوقه.**

---

## خلاصة الأثر على تصميم علاقة "ولي أمر↔طالب"

هذه الجلسة تخطيط فقط، بدون قرار تصميم نهائي — توثيق الفجوات الفعلية:

1. **تحديد القاصر ممكن تقنيًا لكن غير جاهز**: `birth_date` موجود ومكتوب
   فعليًا (بعكس `father_id`/`mother_id` الميتين تمامًا)، لكن بلا أي
   منطق حساب عمر قائم، وبلا ضمان إن كل مستخدم عنده قيمة (الحقل
   `nullable`). أي تصميم يعتمد عليه يحتاج فحص DB لنسبة الـ`NULL` الفعلية
   أولًا، وقرار: هل نجعله إجباريًا مستقبلًا أم نبني fallback لغيابه؟
2. **لا توجد سابقة "موافقة متبادلة" حقيقية بالمشروع** — لا `invitations`
   (CRM أحادي الاتجاه، محمَّل بمنطق تجاري غير ذي صلة) ولا `TenantInvitation`
   (أحادي الاتجاه، بلا رفض صريح) يصلحان كقالب مباشر. تصميم ولي أمر↔طالب
   سيكون **أول نمط موافقة-متبادلة-حقيقي** (كلا الطرفين يوافق بفعل صريح
   قابل للاستعلام) في المشروع.
3. **نمط "طابور تحقق إداري" جاهز شكليًا للاقتباس** (`status` enum +
   `verified_by` + `verified_at` + `rejection_reason`, من
   `SovereignEntity.kyb_status`/`EntityDocument.status`) — هذا أقرب
   سابقة فعلية قابلة لإعادة الاستخدام كنمط بيانات (مش ككود مُستورَد
   مباشرة، الدومين مختلف).
4. **صفر بنية تنبيه أدمن قائمة** — حتى نمط KYB نفسه (الأقرب مفاهيميًا)
   pull-based بالكامل بلا أي push notification. تصميم تنبيه الأدمن هنا
   يبدأ من الصفر: يحتاج (أ) دالة جديدة لجلب كل `SUPER_ADMIN`/
   `EXECUTIVE_DIRECTOR` في الـtenant، (ب) ربطها بـ`send_notification`
   (اللي هي نفسها مصمَّمة لمستلم واحد فقط — راجع
   [[project_targeted_notifications_planning]]).

**التنفيذ الفعلي (موديل جديد، migration، منطق موافقة متبادلة، تحقق
إداري، تنبيهات) يحتاج جلسة تصميم/موافقة صريحة منفصلة**، نفس القاعدة
المتبعة في كل قرارات معمارية سابقة بالمشروع.
