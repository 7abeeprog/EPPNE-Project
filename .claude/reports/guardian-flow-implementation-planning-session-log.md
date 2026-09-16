# علاقة ولي أمر↔طالب — جلسة تخطيط تنفيذ المرحلة الثانية (service.py/router.py)

**تاريخ:** 2026-09-16
**النطاق:** فحص read-only بحت لتجهيز تصميم دقيق لمنطق التدفق
(service.py/router.py) لعلاقة ولي أمر↔طالب — امتدادًا لـ
[[project_guardian_relationship_foundation_implementation]] (الأساس
migration 056 + models/schemas/repository مبني ومتحقَّق منه من قبل).
**ممنوع أي تعديل كود — تم الالتزام، صفر Edit/Write على كود المشروع.**

---

## 1. `get_current_user`/`get_current_superuser` — التوقيع بالظبط (`core/security.py`)

### `get_current_user` (سطر 99-150)

```python
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    cookie_token: Optional[str] = Cookie(None, alias="access_token"),
) -> User:
```

يقبل Bearer header أو HttpOnly cookie (`access_token`)، يفك التوكن،
يتحقق من `typ == "access"`، `session_version`، تطابق `tenant_id`، ويرجع
كائن `User` كامل. هذا الاعتمادية الأساسية لأي endpoint محمي.

### `get_current_active_user` (سطر 153-158)

```python
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
```

طبقة رقيقة فوق `get_current_user` — فحص `is_active` إضافي. **هذا هو
الاعتمادية المُستخدَمة فعليًا في أغلب الـendpoints العادية بالمشروع**
(مش `get_current_user` مباشرة).

### `get_current_superuser` (سطر 164-170)

```python
async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role
    if role_value not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
        raise PermissionDeniedError("Superuser privileges required")
    return current_user
```

**نطاق الأدوار المقبولة: `SUPER_ADMIN` و`EXECUTIVE_DIRECTOR` فقط** —
**ليس** `ADMIN` (القيمة الموجودة فعليًا في `SystemRole` enum:
`USER/ADMIN/SUPER_ADMIN/EXECUTIVE_DIRECTOR/SYSTEM`، راجع
[[project_guardian_relationship_design_planning]] §4). هذا نفس
الاعتمادية المُستخدَمة فعليًا في `POST /communications/notifications/send`
(`communications/router.py:94`) — **استخدامها لـendpoint "مراجعة طلب
ولي أمر" (`PENDING_ADMIN_REVIEW → VERIFIED/REJECTED`) سيطابق تمامًا نمط
`review_kyb`/`PUT /entities/{id}/kyb/status`** (راجع
[[project_guardian_relationship_design_planning]] §3).

### دوال مساعدة إضافية ذات صلة محتملة (نفس الملف)

- `is_admin_or_above(user: User) -> bool` (سطر 173-175): فحص غير-async،
  يقبل `ADMIN` **بالإضافة إلى** `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` —
  أوسع من `get_current_superuser`. **نطاق أوسع** — قرار تصميمي: هل
  مراجعة طلبات ولي الأمر تحتاج `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` بس
  (زي KYB) ولا `ADMIN` العادي كافٍ؟ خارج نطاق هذه الجلسة القرائية.
- `require_admin_or_above` (سطر 178-183): اعتمادية FastAPI جاهزة تلف
  `is_admin_or_above` — بديل جاهز لو القرار كان "ADMIN كافٍ".

---

## 2. دالة "بحث عن مستخدم بالإيميل/username" — موجودة، لكن بقيود مهمة

**نعم موجودة على مستوى الـrepository والـservice، لكن الـendpoint
الوحيد المُعرَّض منها اليوم مقفول على الأدمن فقط — غير صالح مباشرة
لسيناريو "ولي الأمر يبحث عن ابنه بنفسه".**

### `UserRepository` (`identity/repository.py`) — كل دوال البحث المتاحة

```python
async def get_by_username_or_email(self, login: str, tenant_id: int) -> Optional[User]:
    # تطابق تام (case-insensitive) — إيميل أو username، قيمة واحدة مدخلة
    ...

async def get_by_email(self, email: str, tenant_id: int) -> Optional[User]:
    # تطابق تام، إيميل فقط
    ...

async def get_by_username(self, username: str, tenant_id: int) -> Optional[User]:
    # تطابق تام، username فقط
    ...

async def search_by_username_or_email(self, q: str, tenant_id: int, limit: int = 10) -> List[User]:
    # بحث جزئي (ILIKE %q%) على username وemail معًا، بيرجع List[User]
    ...
```

- `get_by_email`/`get_by_username`: **تطابق تام فقط**، ومُستخدَمتان
  اليوم **حصريًا داخليًا** في `UserService.register()` للتحقق من عدم
  التكرار (سطر 71، 74) — **صفر أي service method أو router endpoint
  يعرضهما للاستخدام العام.**
- `search_by_username_or_email`: بحث جزئي، مُستخدَمة عبر
  `UserService.search_users(q, limit)` (`identity/service.py:61-62`)،
  و**معرَّضة فعليًا** عبر endpoint حي:

```python
@protected_router.get("/users/search", response_model=List[UserSearchResult])
@rate_limit(max_requests=30, window_seconds=60)
async def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin_or_above(current_user):
        raise PermissionDeniedError("صلاحية إدارية مطلوبة للبحث عن مستخدمين")
    ...
```

(`identity/router.py:214-229`) — **⚠️ محمي بفحص `is_admin_or_above`
صريح داخل جسم الدالة نفسها، فوق `get_current_active_user`**. يعني: **أي
مستخدم عادي (ولي أمر بلا دور إداري) هيترفض فورًا بـ`PermissionDeniedError`
لو حاول يستخدم هذا الـendpoint.** هذا مصمَّم أصلًا كأداة بحث إدارية
(زي دعم فني يلاقي حساب مستخدم)، مش أداة عامة لأي مستخدم.

**الأثر على تصميم endpoint "ولي الأمر يلاقي ابنه":**
1. **لا يمكن إعادة استخدام `GET /identity/users/search` كما هو** —
   قفلها الإداري يمنع أي ولي أمر عادي من استخدامها.
2. الخيارات المتاحة: (أ) endpoint جديد مخصص لـ`guardian` بتطابق تام فقط
   (عبر `get_by_email`/`get_by_username` الموجودتين فعليًا لكن غير
   مُعرَّضتين — يحتاج service method جديدة تلفّهما)، بحيث ولي الأمر
   يدخل الإيميل/username **بالظبط** فيرجع مستخدم واحد أو لا شيء (أأمن
   من بحث جزئي يكشف قائمة مستخدمين لغير الأدمن)؛ أو (ب) توسيع
   `search_users` نفسها بفحص شرطي إضافي (لو الطلب من سياق "طلب ربط ولي
   أمر" وليس بحث عام) — تغيير أوسع في endpoint قائم، خطر أعلى. **قرار
   تصميمي خارج نطاق هذه الجلسة القرائية** — لكن الخيار (أ) أقرب لنمط
   المشروع (نقطة نهاية جديدة ضيقة النطاق بدل تعديل سلوك endpoint إداري
   قائم).

---

## 3. `UserRepository` كامل — تأكيد نهائي: صفر `list_by_role`/`get_users_by_role`

تم عرض الكلاس **كاملًا بلا اقتطاع** (`identity/repository.py:12-132`،
14 دالة async بالإجمالي):

`get_by_id`, `list_active_by_tenant`, `get_by_username_or_email`,
`get_by_email`, `get_by_username`, `get_by_idempotency_key`,
`search_by_username_or_email`, `get_tenant_id_by_user_id`, `create`,
`update`, `delete`, `update_last_login`, `increment_session_version`
(+ `_apply_tenant_filter` مساعدة غير-async).

**تأكيد نهائي: لا توجد `list_by_role` ولا `get_users_by_role` ولا أي
دالة مشابهة تفلتر المستخدمين حسب `system_role`.** هذا يطابق تمامًا
النتيجة السابقة في
[[project_guardian_relationship_design_planning]] §4 — **لا يوجد أي
تغيير من وقتها**. أقرب دالة موجودة فعليًا هي `list_active_by_tenant`
(تفلتر بـ`tenant_id` + `is_active` بس، بلا أي فلتر على `system_role`).

**الأثر:** `get_tenant_admins()` المطلوب بناؤها للمرحلة الثانية
(لتحديد مين يتبلّغ عند `PENDING_ADMIN_REVIEW`) **لازم تُبنى من الصفر
بالكامل** — لا يوجد أي دالة جزئية أو معطَّلة يمكن البناء عليها. أبسط
شكل ممكن (بنفس نمط `list_active_by_tenant`):

```python
async def list_by_role(self, tenant_id: int, roles: List[str]) -> List[User]:
    query = select(User).where(
        and_(User.tenant_id == tenant_id, User.system_role.in_(roles), User.is_active == True)
    )
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

(مجرد اقتراح شكلي للمرحلة القادمة — **لم يُكتَب أو يُضَف أي كود في هذه
الجلسة**).

---

## 4. `send_notification` — تأكيد نهائي للتوقيع

تم إعادة قراءة الملف الحالي بالكامل (`communications/service.py:1-51`)
— **صفر تغيير عن التوثيق السابق**
([[project_targeted_notifications_planning]]):

```python
async def send_notification(
    self,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    priority: str = NotificationPriority.NORMAL,
    channel: str = NotificationChannel.IN_APP,
    idempotency_key: Optional[str] = None
) -> Notification:
```

**التوقيع مؤكَّد حرفيًا كما ورد في السؤال: `(user_id, title, body, data,
priority, channel, idempotency_key)`.** لسه **مستلم واحد فقط**
(`user_id: int` مفرد) — صفر دعم لقائمة مستلمين، بلا تغيير عن الجلسة
السابقة.

### قيم الـenums المتاحة فعليًا (`communications/models.py:10-21`)

```python
class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WEBSOCKET = "WEBSOCKET"
    IN_APP = "IN_APP"

class NotificationPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

**الأثر على استدعاء تنبيه الأدمن:** بما إن `send_notification` تقبل
مستلم واحد بس، وبما إن `get_tenant_admins()` (المطلوب بناؤها، قسم 3)
هترجع **قائمة** أدمنز، الاستدعاء الفعلي في المرحلة القادمة لازم يكون
**loop خارجي** — نداء `send_notification` مرة منفصلة لكل أدمن في
القائمة، بنفس النمط المستخدَم بالفعل مع كل استدعاءات `send_notification`
الحالية بالمشروع (كلها مستلم واحد، صفر سابقة لبث جماعي — راجع
[[project_targeted_notifications_planning]] §3).

مثال شكلي للاستدعاء المتوقَّع (اقتراح توضيحي فقط، **لم يُكتَب أي كود**):

```python
admins = await user_repo.list_by_role(tenant_id, ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"])
for admin in admins:
    await comm_service.send_notification(
        user_id=admin.id,
        title="طلب ربط ولي أمر يحتاج مراجعة",
        body=f"طلب علاقة ولي أمر↔طالب رقم {relationship.id} وصل لمرحلة المراجعة الإدارية",
        data={"guardian_relationship_id": relationship.id},
        priority=NotificationPriority.HIGH,
        channel=NotificationChannel.IN_APP,
        idempotency_key=f"GUARDIAN-ADMIN-REVIEW-{relationship.id}",
    )
```

---

## خلاصة الأثر على تصميم service.py/router.py (المرحلة القادمة)

هذه الجلسة تخطيط فقط، بدون قرار تصميم نهائي:

1. **اعتماديات الأمان جاهزة ومباشرة**: `get_current_active_user` لكل
   endpoints العادية (طلب الربط، موافقة الطالب)، `get_current_superuser`
   (`SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` فقط) لـendpoint المراجعة الإدارية
   — بنفس نمط `review_kyb` بالحرف. قرار مفتوح: هل `ADMIN` العادي
   (`is_admin_or_above`) كافٍ بدل حصره على superuser فقط؟
2. **"لقاء ولي الأمر بابنه" يحتاج endpoint جديد** — `GET
   /identity/users/search` القائمة **مقفولة على الأدمن ولا يمكن
   إعادة استخدامها** لمستخدم عادي. الحل الأقرب لنمط المشروع: endpoint
   جديد بتطابق تام (`get_by_email`/`get_by_username` الموجودتين
   فعليًا، غير مُعرَّضتين حاليًا) بدل بحث جزئي عام.
3. **`get_tenant_admins()` تُبنى من الصفر بالكامل** — تأكيد نهائي: صفر
   `list_by_role` أو أي دالة جزئية في `UserRepository` (14 دالة، كلها
   مُعروضة بالكامل في هذا التقرير).
4. **تنبيه الأدمن = loop على `send_notification` المفردة** — لا يوجد
   ولن يظهر فجأة أي دعم لمستلمين متعددين؛ التصميم لازم يفترض نداء واحد
   لكل أدمن صراحةً.

**التنفيذ الفعلي (service.py/router.py الحقيقيين) يحتاج جلسة تنفيذ
منفصلة بموافقة صريحة**، نفس القاعدة المتَّبعة في كل الجلسات السابقة.
