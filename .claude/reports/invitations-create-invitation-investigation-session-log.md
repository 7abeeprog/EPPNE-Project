# تقرير جلسة — تحقيق (read-only) في `create_invitation` (`POST /api/invitations/`)

**نوع الجلسة:** فحص read-only بحت — **صفر تعديل كود**. الهدف: فهم كامل
لعطل `create_invitation` قبل أي إصلاح مستقبلي.

**البند في `PROGRESS_LOG.md`:** `backlog-invitations-create-invitation-broken`
(قسم `## [2026-09-07] backlog-invitations-create-invitation-broken`، حوالي
السطر 2222).

**المصدر الأصلي للاكتشاف:**
`.claude/reports/remaining-7-domains-can-access-service-migration-session-log.md`
§7.4.1 — اكتُشف بالصدفة أثناء جلسة توحيد `can_access_service` لدومين
`invitations`، **بلا أي لمس** لـ`create_invitation`/`_assign_ai_agent` في
تلك الجلسة (تأكَّد وقتها بـ`git diff`).

---

## 1) كود `create_invitation` كامل (`invitations/service.py`, سطر 152–234)

```python
async def create_invitation(
    self,
    sender_id: int,
    tenant_id: int,
    data: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    analyze_target: bool = True
) -> SovereignInvitation:
    await self._check_saas_limits(tenant_id, "crm")

    if idempotency_key:
        cached = await self._validate_idempotency(idempotency_key)
        if cached is not None:
            invitation_id = cached.get("invitation_id")
            if invitation_id:
                invitation = await self.repo.get_invitation(invitation_id, tenant_id)
                if invitation:
                    return invitation
            raise ValidationError("Idempotency record exists but invitation not found.")

    sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
    sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
    sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)

    client_insight = None
    if analyze_target and data.get("target_user_id"):
        analysis = await self._analyze_target_user(data["target_user_id"], tenant_id)
        client_insight = await self.repo.create_client_insight(
            tenant_id=tenant_id,  # type: ignore
            invitation_id=0,
            ai_analysis=analysis["analysis"],
            recommended_discount=analysis["recommended_discount"],
            recommended_message_template=analysis["recommended_message"],
            readiness_score=analysis["readiness_score"]
        )
        if analysis["recommended_message"] and not data.get("custom_message"):
            data["custom_message"] = analysis["recommended_message"]
        if analysis["recommended_discount"] and data.get("discount_percentage", 0) == 0:
            data["discount_percentage"] = analysis["recommended_discount"]

    async with self.db.begin_nested():
        invitation = await self.repo.create_invitation(
            tenant_id=tenant_id,  # type: ignore
            sender_user_id=sender_id,
            title=sanitized_title,
            custom_message=sanitized_message,
            target_entity_identifier=sanitized_identifier,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in ["title", "custom_message", "target_entity_identifier"]}
        )

        if client_insight:
            client_insight.invitation_id = invitation.id  # type: ignore
            await self.db.flush()

    ai_agent = await self._assign_ai_agent(invitation)
    if ai_agent:
        invitation = await self.repo.update_invitation(
            cast(int, invitation.id), tenant_id, assigned_ai_agent_id=ai_agent.id
        )

    await self.db.commit()

    await self._register_affiliate_commission(sender_id, tenant_id, "INVITATION_CREATED")

    await audit_log(
        user_id=sender_id,
        tenant_id=tenant_id,  # type: ignore
        action="INVITATION_CREATED",
        resource_id=invitation.id,  # type: ignore
        details={"title": invitation.title}
    )

    await self.event_bus.publish("invitation.created", {
        "invitation_id": invitation.id,
        "tenant_id": tenant_id,
        "sender_id": sender_id
    })

    if idempotency_key:
        await self._store_idempotency(idempotency_key, {"invitation_id": invitation.id})

    return invitation
```

---

## 2) `_assign_ai_agent` كامل (`invitations/service.py`, سطر 108–115)

```python
async def _assign_ai_agent(self, invitation: SovereignInvitation):
    from app.domains.ai_agents.repository import AIAgentsRepository
    agents_repo = AIAgentsRepository(self.db)
    agents = await agents_repo.list_agents(
        tenant_id=invitation.tenant_id,  # type: ignore
        role="SUPPORT"
    )
    return agents[0] if agents else None
```

استدعاء **غير مشروط بالكامل** — لا `if` قبله في `create_invitation` (سطر
207)، ولا `try/except` حوله. يعني أي طلب ناجح حتى هذه النقطة سيفشل هنا
دائمًا.

## 3) `AIAgentsRepository.list_agents()` — التوقيع الكامل (`ai_agents/repository.py`, سطر 59–94)

```python
async def list_agents(
    self,
    tenant_id: int,
    owner_id: Optional[int] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> PaginatedResponse[AIAgentResponse]:
    query = select(AIAgent).where(
        and_(
            AIAgent.tenant_id == tenant_id,
            AIAgent.is_deleted == False
        )
    )
    if owner_id:
        query = query.where(AIAgent.owner_id == owner_id)
    if role:
        query = query.where(AIAgent.role == role)
    if status:
        query = query.where(AIAgent.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await self.db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await self.db.execute(query)
    items = [AIAgentResponse.model_validate(agent) for agent in result.scalars().all()]

    return PaginatedResponse[AIAgentResponse](
        data=items,
        total=total,
        skip=skip,
        limit=limit
    )
```

**شكل `PaginatedResponse` الفعلي** (`app/core/pagination.py`, كامل):

```python
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    نموذج موحد للـ Pagination.
    متوافق مع Pydantic V2 ويستخدم Generics لأنواع بيانات آمنة.
    """
    data: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool = False  # مفيد للـ Frontend لتحديد وجود صفحة تالية

    model_config = ConfigDict(from_attributes=True)
```

**الخلاصة:** `PaginatedResponse` هو `pydantic.BaseModel` عادي — **بدون
`__getitem__`**. الشكل الصحيح للوصول للعناصر هو `.data` (مش `.items`
ولا `.results`)، أي: `agents.data[0] if agents.data else None`.

`agents[0]` بيفشل بـ`TypeError: 'PaginatedResponse[...]' object is not
subscriptable`.

أما `if agents else None`: بما إن `PaginatedResponse` كائن `BaseModel`
عادي بلا `__bool__`/`__len__` معرَّفين، فهو **دايمًا truthy** (كائن غير
`None` عادي) — يعني الشرط `if agents` لا يحمي من أي شيء عمليًا، حتى لو
`agents.data` فاضية (`[]`)، فالتنفيذ هيوصل لـ`agents[0]` ويفشل بنفس
الطريقة.

---

## 4) `InvitationCreate` — الـSchema كامل (`invitations/schemas.py`, سطر 19–46)

```python
class InvitationCreate(BaseModel):
    invitation_type: InvitationType = Field(description="نوع الدعوة")
    target_type: InvitationTargetType = Field(description="نوع الهدف")
    target_user_id: Optional[int] = Field(default=None, description="معرف المستخدم المستهدف")
    target_entity_identifier: Optional[str] = Field(default=None, description="معرف الكيان المستهدف")
    custom_message: Optional[str] = Field(default=None, description="رسالة مخصصة")
    title: Optional[str] = Field(default=None, description="عنوان الدعوة")
    campaign_type: CampaignType = Field(description="نوع الحملة")
    campaign_id: int = Field(description="معرف الحملة")
    discount_percentage: Decimal = Field(default=Decimal("0.0"), ge=0, le=100, description="نسبة الخصم")
    gift_coins_amount: Decimal = Field(default=Decimal("0.0"), ge=0, description="مبلغ الهدية")
    gift_currency: Optional[str] = Field(default="MR_USDT", description="عملة الهدية")
    max_uses: int = Field(default=1, ge=1, description="الحد الأقصى للاستخدام")
    expires_at: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")

    @field_validator("discount_percentage", "gift_coins_amount", mode="before")
    @classmethod
    def _coerce_none_to_zero(cls, v):
        return Decimal("0.0") if v is None else v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and "created_at" in info.data:
            created = info.data.get("created_at")
            if created and v <= created:
                raise ValueError("expires_at must be after created_at")
        return v
```

### تصنيف كل الحقول من زاوية "ممكن تكسر `bleach.clean(None)` أو لأ؟"

| الحقل | النوع | القيمة الافتراضية | بيتعرَّض لـ`bleach.clean()` في `create_invitation`؟ | الخلاصة |
|---|---|---|---|---|
| `invitation_type` | `InvitationType` (enum) | **إلزامي**، لا default | لا | آمن — إلزامي فمينفعش يبقى `None` |
| `target_type` | `InvitationTargetType` (enum) | **إلزامي**، لا default | لا | آمن |
| `target_user_id` | `Optional[int]` | `None` | لا (بيتفحص بس بـ`data.get("target_user_id")` كـtruthy check لتفعيل تحليل AI، وبيتمرَّر كـ`int`/`None` مباشرة للـrepo) | آمن — عمود DB `Integer` قابل للـ`NULL` غالبًا (لم يُتحقَّق من الموديل بالتفصيل هنا لأنه خارج نطاق `bleach`) |
| `target_entity_identifier` | `Optional[str]` | `None` | **نعم** — سطر 174 | **🔴 معروف مسبقًا — يكسر** |
| `custom_message` | `Optional[str]` | `None` | **نعم** — سطر 173 | **🔴 معروف مسبقًا — يكسر** |
| `title` | `Optional[str]` | `None` | **نعم** — سطر 172 | **🔴🆕 مكتشَف في هذه الجلسة — نفس النمط بالضبط، وهو فعليًا **أول** حقل يفشل في ترتيب التنفيذ (قبل الاتنين المعروفين) |
| `campaign_type` | `CampaignType` (enum) | **إلزامي**، لا default | لا | آمن |
| `campaign_id` | `int` | **إلزامي**، لا default | لا | آمن |
| `discount_percentage` | `Decimal` | `Decimal("0.0")` + validator يحوّل `None`→`0.0` قبل التحقق من النوع | لا | آمن — محمي بـ`_coerce_none_to_zero` |
| `gift_coins_amount` | `Decimal` | نفس الحماية | لا | آمن — نفس الـvalidator |
| `gift_currency` | `Optional[str]` | `"MR_USDT"` (**مش `None`**) | لا | آمن من زاوية bleach، لكن الـdefault نفسه Optional فلو المستخدم بعت `null` صراحة في الـJSON بيتغلب على الـdefault ويبقى فعليًا `None` عند الوصول لـ`repo.create_invitation` — اتُختبر حيًا (§6) ومرّ بسلام لأنه مش بيتلمس بـbleach ولا فيه أي فحص `NOT NULL` صريح ظهر أثناء التحقيق |
| `max_uses` | `int` | `1` | لا | آمن |
| `expires_at` | `Optional[datetime]` | `None` | لا | آمن |

**الخلاصة الحاسمة:** الحقول اللي فعليًا بتتعرَّض لـ`bleach.clean()` في
`create_invitation` هي **3 مش 2**: `title`, `custom_message`,
`target_entity_identifier` — بنفس النمط بالضبط (`data.get(key, "")`
بيرجع `None` صراحة لو المفتاح موجود بقيمة `None`، مش الـdefault
`""`، لأن `.get()` بيفعّل الـdefault بس لو المفتاح **غايب** تمامًا —
و`data.model_dump()` من الراوتر بيرجّع كل المفاتيح دايمًا حتى لو
`None`). الاتنين اللي ظهروا "بالصدفة" في التحقيق الأصلي (§7.4.1 من
تقرير `remaining-7-domains`) كانوا `custom_message`/
`target_entity_identifier` بس لأن `title` كان متبعوت بقيمة حقيقية
(`"title":"..."`) في كل محاولاتهم الثلاث — يعني الجلسة دي أول مرة
`title` بيتسجَّل `None` صراحة.

---

## 5) الحقول الأخرى في نفس الملف بنفس نمط `Optional[str] = None` — فحص سريع لباقي الـSchemas

بالفحص، باقي الـSchemas في `invitations/schemas.py` (`LeadCreate`,
`InteractionCreate`, `CampaignCreate`, `TicketCreate`,
`TicketCommentCreate`, إلخ) فيها حقول `Optional[str] = None` كتير
(`notes`, `company`, `position`...) لكن **مفيش أي `bleach.clean()`
تاني في `service.py` غير الحالات المذكورة فوق زائد**:
`user_message` في `chat_with_ai` (سطر 393 — بارامتر مباشر مش من
schema، إلزامي `str` في `ConversationMessage.message`، آمن)،
و`data.get("subject"/"description")` في `create_ticket` (سطر
774–775) و`data.get("comment")` في `add_ticket_comment` (سطر 873) —
دول **خارج نطاق هذا التحقيق** (مرتبطين بـ`create_ticket`/
`add_ticket_comment` مش `create_invitation`)، لكن بنفس النمط
بالضبط (`TicketCreate.subject`/`description` إلزاميين `str` فآمنين،
لكن `TicketCommentCreate.comment` أيضًا إلزامي `str` فآمن). لم
يُختبَروا حيًا في هذه الجلسة لأنهم خارج نطاق `create_invitation`
الصريح المطلوب.

---

## 6) الاختبار الحي — المنهجية والنتائج الكاملة

**الطريقة:** استدعاء `InvitationsService(db).create_invitation()`
مباشرة (بلا HTTP/JWT، بنفس نمط `tests/test_invitations_savepoint_leak.py`
— `db` = جلسة `AsyncSessionLocal` حقيقية ضد قاعدة البيانات الفعلية،
مع `import app.main` أولًا لضمان تسجيل كل الـmodels قبل أي استعلام).

**التينانت:** `tenant_id=16` — نفس التينانت المستخدم في التحقيق
الأصلي (`remaining-7-domains...` §7.4.2)، عنده اشتراك `ACTIVE` حقيقي +
تفعيل خدمة `crm` فعلي، فـ`_check_saas_limits` بتعدّي بنجاح ويوصل
التنفيذ فعليًا لجسم الدالة.

**المستخدم:** `sender_id=774` (`TEST_instr_b`, `tenant_id=16`) — نفس
المستخدم المستخدَم في كل اختبارات الجلسة الأصلية.

**البيانات:** `InvitationCreate(...).model_dump()` بالظبط زي ما
الراوتر بيعمل (سطر 39 في `router.py`: `data.model_dump()` بلا
`exclude_unset`) — يعني كل الحقول الـOptional موجودة بمفاتيحها بقيمة
`None` صراحة لو متبعوتش، مطابق 100% لسلوك أي طلب `POST
/api/invitations/` حقيقي بيسيب هذي الحقول فاضية.

**تنظيف:** `await db.rollback()` في كل محاولة (سواء نجحت أو فشلت) —
اتأكَّد بعدها بـ`SELECT` مباشر إن **صفر صفوف orphan** اتسجَّلت في
`sovereign_invitations_v2` من أي محاولة (تفاصيل تحت).

### الخطوة 0 — كل الحقول الاختيارية `None` صراحة (السيناريو المطلوب بالضبط من المستخدم)

```python
InvitationCreate(
    invitation_type=InvitationType.GENERAL,
    target_type=InvitationTargetType.PERSON,
    target_user_id=None,
    target_entity_identifier=None,
    custom_message=None,
    title=None,
    campaign_type=CampaignType.SERVICE,
    campaign_id=1,
    gift_currency=None,
    expires_at=None,
)
```

**`data.model_dump()` المُرسَلة فعليًا:**
```
invitation_type = InvitationType.GENERAL
target_type = InvitationTargetType.PERSON
target_user_id = None
target_entity_identifier = None
custom_message = None
title = None
campaign_type = CampaignType.SERVICE
campaign_id = 1
discount_percentage = Decimal('0.0')
gift_coins_amount = Decimal('0.0')
gift_currency = None
max_uses = 1
expires_at = None
```

**النتيجة الفعلية — traceback كامل:**
```
File "app/domains/invitations/service.py", line 172, in create_invitation
    sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
File "bleach/__init__.py", line 82, in clean
    return cleaner.clean(text)
File "bleach/sanitizer.py", line 186, in clean
    raise TypeError(message)
TypeError: argument cannot be of 'NoneType' type, must be of text type
```

**🆕 هذا هو العطل الثالث المطلوب اكتشافه.** بترتيب التنفيذ الفعلي،
`title` (سطر 172) هو **أول** سطر بيفشل — قبل `custom_message` (سطر
173) وقبل `target_entity_identifier` (سطر 174) اللي كانا معروفين من
قبل. نفس الـroot cause بالضبط (`bleach.clean(None)`)، بس على حقل
تالت لم يُذكر صراحة في backlog الأصلي.

### الخطوة 1 — `title` بقيمة حقيقية، الباقي `None`

بعد تثبيت `title="STEP1-TITLE"` وإبقاء `custom_message`/
`target_entity_identifier` على `None`:

```
File "app/domains/invitations/service.py", line 173, in create_invitation
    sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
TypeError: argument cannot be of 'NoneType' type, must be of text type
```

مطابق تمامًا للمكتشَف في `remaining-7-domains...` §7.4.1 محاولة رقم 1.

### الخطوة 2 — `title` و`custom_message` بقيمة حقيقية، `target_entity_identifier` لسه `None`

```
File "app/domains/invitations/service.py", line 174, in create_invitation
    sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)
TypeError: argument cannot be of 'NoneType' type, must be of text type
```

مطابق تمامًا لمحاولة رقم 2 في التقرير الأصلي.

### الخطوة 3 — الثلاثة حقول بقيم حقيقية (`target_user_id`, `gift_currency`, `expires_at` لسه `None` صراحة)

```
File "app/domains/invitations/service.py", line 207, in create_invitation
    ai_agent = await self._assign_ai_agent(invitation)
File "app/domains/invitations/service.py", line 115, in _assign_ai_agent
    return agents[0] if agents else None
TypeError: 'PaginatedResponse[AIAgentResponse]' object is not subscriptable
```

مطابق تمامًا لمحاولة رقم 3 (الأخيرة) في التقرير الأصلي. **مفيش أي عطل
رابع جديد ظهر** — التنفيذ وصل بنجاح لـ`await self.repo.create_invitation(...)`
(إدراج فعلي داخل `begin_nested()`/savepoint) رغم إن `target_user_id`,
`gift_currency`, `expires_at` كانوا لسه `None` صراحة في هذه الخطوة —
يعني الـ3 حقول دول (زي ما اتوقَّعنا من فحص الجدول في §4) آمنة فعلًا
ومفيش أي مسار كسر تاني مرتبط بيهم داخل `create_invitation` نفسها.

### تأكيد صفر تلوث DB

بعد الخطوة 3 (اللي فيها إدراج فعلي داخل savepoint قبل الفشل):
```sql
SELECT id, title, tenant_id FROM sovereign_invitations_v2 WHERE title = 'STEP1-TITLE';
-- 0 صفوف
```
`db.rollback()` في نهاية كل محاولة كفى لإلغاء أي savepoint/insert لم
يوصل لـ`await self.db.commit()` الصريحة (سطر 213) — لم تُنفَّذ أبدًا
في أي من المحاولات الأربعة لأن كلها فشلت قبلها.

---

## 7) الخلاصة الكاملة — سلسلة الأعطال الحقيقية لـ`create_invitation` بترتيب التنفيذ

| الترتيب | السطر | العطل | معروف مسبقًا؟ |
|---|---|---|---|
| 1 | `service.py:172` | `bleach.clean(None)` على `title` | 🆕 لأ — مكتشَف في هذه الجلسة |
| 2 | `service.py:173` | `bleach.clean(None)` على `custom_message` | ✅ نعم (`remaining-7-domains` §7.4.1) |
| 3 | `service.py:174` | `bleach.clean(None)` على `target_entity_identifier` | ✅ نعم (نفس المصدر) |
| 4 | `service.py:115` (`_assign_ai_agent`) | `PaginatedResponse[...]` مش قابلة للفهرسة (`agents[0]`) | ✅ نعم (نفس المصدر) — **هذا هو العطل الجذري الحقيقي** اللي بيمنع **أي** طلب `POST /api/invitations/` ناجح من إتمام العملية، بغض النظر عن أي حقل فاضي |

**نقطة مهمة:** حتى لو الحقول الثلاثة (`title`/`custom_message`/
`target_entity_identifier`) اتبعتت كلها بقيم نصية حقيقية (مش `None`)
— أي طلب `create_invitation` **هيفضل يفشل بـ500 دايمًا** بسبب العطل
رقم 4 (`_assign_ai_agent`)، لأنه استدعاء غير مشروط بلا أي حماية. أعطال
1–3 بتتلخبط بس ترتيب الاكتشاف لو الحقول فاضية، لكن العطل الحقيقي
الوحيد اللي بيمنع الـendpoint من النجاح **حتى لو كل الحقول اتملت
صح** هو رقم 4.

**الحالة النهائية:** لا تعديل كود تم في هذه الجلسة. البند لسه backlog
مفتوح (`backlog-invitations-create-invitation-broken`). هذا التقرير
يوثّق الصورة الكاملة (4 أعطال بترتيب تنفيذ مؤكَّد حيًا، بدل 2 فقط)
تحضيرًا لأي جلسة إصلاح مستقبلية.
