# علاقة ولي أمر↔طالب — جلسة تنفيذ المرحلة الثانية (منطق التدفق)

**تاريخ:** 2026-09-16
**النطاق:** بناء `service.py`/`router.py` كاملين لعلاقة ولي أمر↔طالب —
6 endpoints بالتصميم المحدَّد بالحرف من المستخدم. فوق الأساس المبني
والمتحقَّق منه سابقًا
([[project_guardian_relationship_foundation_implementation]]) وجلسة
التخطيط read-only ([[project_guardian_flow_implementation_planning]]).

---

## 1. الملفات الجديدة/المعدَّلة

| الملف | التغيير |
|---|---|
| `app/domains/identity/repository.py` | +`UserRepository.list_by_role()` — دالة جديدة بحتة |
| `app/domains/guardian/schemas.py` | +6 schemas جديدة (طلبات/ردود) |
| `app/domains/guardian/repository.py` | +`update_relationship`, +`upsert_visibility_setting` |
| `app/domains/guardian/service.py` | **جديد بالكامل** — `GuardianService` |
| `app/domains/guardian/router.py` | **جديد بالكامل** — 6 endpoints |
| `app/main.py` | تسجيل `guardian_router` (import + سطر في `routers_config`) |
| `tests/test_guardian_relationship_flow_implementation.py` | **جديد** — 6 سيناريوهات حية |

---

## 2. `identity/repository.py` — الإضافة الوحيدة

```python
async def list_by_role(self, tenant_id: int, roles: List[str]) -> List[User]:
    """كل المستخدمين النشطين في هذا الـtenant بأحد الأدوار المُمرَّرة
    (قيم `SystemRole` كنص) — للاستخدام في تنبيه الأدمنز مثلًا."""
    query = select(User).where(
        and_(User.tenant_id == tenant_id, User.system_role.in_(roles), User.is_active == True)  # noqa: E712
    )
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

**صفر تعديل على أي دالة قائمة** — بالضبط الشكل المقترح في جلسة التخطيط
([[project_guardian_flow_implementation_planning]] §3). تم التأكد
بـgrep شامل: `list_by_role` **مُستخدَمة فقط من `guardian/service.py`**
— صفر مستدعٍ تاني في كامل المشروع.

---

## 3. `guardian/schemas.py` — 6 إضافات

- `GuardianRelationshipRequestCreate(ward_user_id, relationship_type)`
  — **بلا `guardian_user_id`** عمدًا (بيتحدد دايمًا من `current_user.id`
  في الراوتر، مش من مدخلات العميل — منع انتحال هوية ولي الأمر).
- `GuardianRelationshipApproveRequest(ward_birth_date_provided: date)`
  — إجباري، مطابق للمطلوب بالحرف.
- `GuardianRelationshipRejectRequest(rejection_reason: Optional[str])`.
- `GuardianRelationshipReviewRequest(status, rejection_reason)` — مع
  `field_validator` يرفض أي قيمة لـ`status` غير `VERIFIED`/`REJECTED`:
  ```python
  @field_validator("status")
  @classmethod
  def _status_must_be_final_decision(cls, v):
      if v not in (GuardianRelationshipStatus.VERIFIED, GuardianRelationshipStatus.REJECTED):
          raise ValueError("status يجب أن يكون VERIFIED أو REJECTED فقط")
      return v
  ```
- `GuardianVisibilityUpdateRequest(settings: List[GuardianVisibilitySettingCreate])`
  — يعيد استخدام schema القسم الموجود من قبل.
- `UserLookupResponse(user_id: int, name: str)` — `name` = `username`،
  نفس اتفاقية `UserSearchResult` القائمة في `identity/schemas.py`.

---

## 4. `guardian/repository.py` — إضافتان

### `update_relationship` (تحديث عام)

```python
async def update_relationship(self, relationship_id: int, tenant_id: int, **kwargs) -> Optional[GuardianRelationship]:
    relationship = await self.get_relationship(relationship_id, tenant_id)
    if not relationship:
        return None
    for key, value in kwargs.items():
        setattr(relationship, key, value)
    await self.db.flush()
    await self.db.refresh(relationship)
    return relationship
```

### `upsert_visibility_setting` (INSERT...ON CONFLICT DO UPDATE ذرّي)

نفس نمط `AchievementRepository.increment_bootcamp_network_size` بالحرف
— بلا `SELECT` أول، القيد الفريد `uq_guardian_visibility_relationship_sector`
هو الحارس.

**⚠️ باج حقيقي اتكشف واتصلح هنا أثناء الاختبار** (راجع قسم 6 تحت).

---

## 5. `guardian/service.py` — `GuardianService` (جديد بالكامل)

`__init__(self, db, tenant_id)` — نفس نمط `AchievementService` بالحرف.

### 5.1 `find_user(email, username)` — تطابق تام

```python
async def find_user(self, email: Optional[str], username: Optional[str]) -> User:
    if bool(email) == bool(username):
        raise ValidationError("مطلوب إما email أو username، واحد بس")
    user = (
        await self.user_repo.get_by_email(email, self.tenant_id)
        if email else
        await self.user_repo.get_by_username(username, self.tenant_id)
    )
    if not user:
        raise NotFoundError("المستخدم غير موجود")
    return user
```

`bool(email) == bool(username)` بترفض الحالتين معًا: **كلاهما مُرسَل**
أو **لا شيء مُرسَل** — دقيقًا زي "بتطابق تام" المطلوب. تستخدم
`get_by_email`/`get_by_username` الموجودتين فعليًا (كانتا مُستخدَمتين
داخليًا بس في `register()` قبل كده، راجع
[[project_guardian_flow_implementation_planning]] §2).

### 5.2 `create_relationship_request` — طلب الربط

فحص: `guardian_user_id != ward_user_id`، الطالب موجود فعليًا في نفس
الـtenant (`user_repo.get_by_id`)، pre-check تكرار عبر
`get_relationship_by_guardian_and_ward` (→`AlreadyExistsError`)، ثم
`IntegrityError` fallback (سباق نظري، نفس نمط achievements بالحرف).
الحالة تُنشأ صراحةً `PENDING_WARD_APPROVAL` (مش الاعتماد على الافتراضي
بس، توضيحًا).

### 5.3 `approve_relationship` — قلب منطق التدفق

```python
input_is_valid = ward_birth_date_provided <= date.today()
age = _calculate_age(ward_birth_date_provided) if input_is_valid else None

if input_is_valid and age is not None and age >= MINOR_AGE_THRESHOLD:
    # → VERIFIED فورًا، verified_by=None (self-attested)
    ...
    await self._ensure_default_visibility_settings(relationship_id)
else:
    # قاصر أو تاريخ في المستقبل ("إدخال مرفوض") → PENDING_ADMIN_REVIEW
    ...
    await self._notify_admins_pending_review(updated)
```

- **حساب العمر يدوي** (`_calculate_age`)، بلا أي مكتبة خارجية جديدة
  (`dateutil.relativedelta` غير مثبَّتة أصلًا بالمشروع).
- **"رفض الإدخال" = تاريخ ميلاد في المستقبل** — بدل رفضه بخطأ 4xx
  صريح، بيتحوّل لنفس مسار القاصر (`PENDING_ADMIN_REVIEW`) بالحرف حسب
  صياغة المستخدم ("لو أقل/رفض الإدخال → PENDING_ADMIN_REVIEW").
  `ward_birth_date_provided` بتتخزن دايمًا كما هي (حتى لو مشكوك فيها)
  عشان الأدمن يشوفها وقت المراجعة.
- **`verified_by=None` للراشد الذاتي** — قرار تصميمي موثَّق في الكود:
  مفيش أدمن تدخّل، فمفيش قيمة "مين وثَّق" حقيقية.
- **الحالة تتفحص أولًا** (`PENDING_WARD_APPROVAL` فقط) — منع معالجة
  مزدوجة.

### 5.4 `reject_relationship` — رفض الطالب

نفس فحوصات التفويض والحالة، `status=REJECTED` + `rejection_reason`
اختياري.

### 5.5 `review_relationship` — مراجعة الأدمن

يتطلب الحالة `PENDING_ADMIN_REVIEW` بالضبط (مش أي حالة تانية — لو
الأدمن حاول يراجع طلب لسه `PENDING_WARD_APPROVAL` مثلًا، بيترفض
بـ`ValidationError`). `REJECTED` بيتطلب `rejection_reason` غير فارغ.
`VERIFIED` → `verified_by=admin_id`, `verified_at=now()` + إنشاء
إعدادات الرؤية الافتراضية (نفس دالة القسم 5.3).

### 5.6 `update_visibility` — تحكّم الطالب

يتطلب `relationship.ward_user_id == ward_user_id` (تفويض) **و**
`status == VERIFIED` (العلاقة لازم تكون مُفعَّلة). `upsert` لكل عنصر
مُرسَل، يرجّع القائمة الكاملة المُحدَّثة (4 صفوف).

### 5.7 `_notify_admins_pending_review` — تنبيه الأدمن

```python
admins = await self.user_repo.list_by_role(self.tenant_id, ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"])
comm_service = CommunicationsService(self.db)
for admin in admins:
    await comm_service.send_notification(
        user_id=admin.id, title="...", body="...",
        data={"guardian_relationship_id": relationship.id},
        priority=NotificationPriority.HIGH, channel=NotificationChannel.IN_APP,
        idempotency_key=f"GUARDIAN-ADMIN-REVIEW-{relationship.id}-{admin.id}",
    )
```

`ADMIN_ROLES = ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]` — **نفس نطاق
`get_current_superuser` بالحرف** (بدون `ADMIN` العادي)، مطابق لصياغة
طلب المستخدم. **`idempotency_key` لازم يشمل `admin.id`** — لو كان
مشترك بين كل الأدمنز، كان `send_notification` هيبعت لأول أدمن بس
(idempotency check بيرجّع الموجود لأي استدعاء لاحق بنفس المفتاح).

---

## 6. `guardian/router.py` — 6 endpoints

| Method | Path | Auth | ملاحظة |
|---|---|---|---|
| GET | `/guardian/find-user` | `get_current_active_user` | query: `email` أو `username` |
| POST | `/guardian/relationships` | `get_current_active_user` | ولي الأمر |
| POST | `/guardian/relationships/{id}/approve` | `get_current_active_user` | الطالب |
| POST | `/guardian/relationships/{id}/reject` | `get_current_active_user` | الطالب |
| PUT | `/guardian/relationships/{id}/review` | `get_current_superuser` | الأدمن |
| PUT | `/guardian/relationships/{id}/visibility` | `get_current_active_user` | الطالب |

`guardian_user_id`/`ward_user_id`/`admin_id` بتتحدد دايمًا من
`current_user.id` في الراوتر، مش من الـbody — التفويض الفعلي بيحصل
جوّه الـservice (مقارنة `relationship.ward_user_id` بـ`current_user.id`
المُمرَّر). سجَّلتهم فعليًا في `main.py` وتأكَّدت بالتشغيل الفعلي إن
الـ6 مسارات موجودة تحت `/api/guardian/...`:

```
{'GET'} /api/guardian/find-user
{'POST'} /api/guardian/relationships
{'POST'} /api/guardian/relationships/{relationship_id}/approve
{'POST'} /api/guardian/relationships/{relationship_id}/reject
{'PUT'} /api/guardian/relationships/{relationship_id}/review
{'PUT'} /api/guardian/relationships/{relationship_id}/visibility
```

---

## 7. باج حقيقي اتكشف واتصلح: identity map قديمة بعد upsert

أول تشغيلة لـ`test_adult_ward_self_verifies_and_controls_visibility`
فشلت: بعد `update_visibility(..., is_visible=False)` لقطاع `ACADEMY`،
القيمة المرجَّعة فضلت `True`:

```
AssertionError: assert True is False
where True = <GuardianVisibilitySetting>.is_visible
```

**السبب:** `upsert_visibility_setting` بتنفّذ `INSERT...ON CONFLICT DO
UPDATE` عبر Core statement خام (`pg_insert`)، وده بيتخطّى الـORM unit-
of-work بالكامل. الصف كان **محمَّل بالفعل في identity map** الخاصة
بالـsession (من `_ensure_default_visibility_settings` وقت إنشاء
العلاقة). لما عملت `SELECT` عادي بعد الـUPDATE عشان أرجّع القيمة
الطازة، SQLAlchemy رجّعت الكائن **المخزَّن في الـidentity map** (القديم)
بدل قراءة الصف الفعلي من DB — **بالضبط نفس الباج الموثَّق بالفعل في
تعليق `AchievementRepository.get_network_stats`** (لم أطبّق نفس الدرس
هنا من أول مرة).

**الإصلاح:**

```python
refreshed = await self.db.execute(
    select(GuardianVisibilitySetting)
    .where(GuardianVisibilitySetting.id == setting_id)
    .execution_options(populate_existing=True)  # ← الإضافة
)
return refreshed.scalar_one()
```

اتأكَّد بالفشل الفعلي قبل الإصلاح والنجاح الكامل بعده (إعادة تشغيل
الاختبار بالكامل).

---

## 8. الاختبار الحي

`tests/test_guardian_relationship_flow_implementation.py` — 6
سيناريوهات، عبر `GuardianService` مباشرة (بلا HTTP client، نفس نمط
باقي regression tests بالمشروع)، فوق DB حقيقية:

1. **`test_find_user_exact_match_not_found_and_validation`** — نجاح
   بالإيميل، نجاح باسم المستخدم، `NotFoundError` لمستخدم غير موجود،
   `ValidationError` لـ(لا شيء) و(الاثنين معًا). **PASSED**.
2. **`test_adult_ward_self_verifies_and_controls_visibility`** — طلب
   → موافقة براشد → `VERIFIED` فورًا (`verified_by=None`) → 4 إعدادات
   رؤية افتراضية (`True` كلهم) → الطالب يقفل `ACADEMY` بس → باقي
   القطاعات فضلت `True`. **PASSED** (بعد إصلاح باج قسم 7).
3. **`test_minor_ward_goes_to_admin_review_notifies_admins_then_verified`**
   — طلب → موافقة بتاريخ ميلاد قاصر → `PENDING_ADMIN_REVIEW` →
   **تحقق فعلي من DB** (مش mock) إن صف `Notification` حقيقي اتنشأ
   للأدمن بـ`idempotency_key` مطابق → صفر إعدادات رؤية قبل المراجعة →
   مراجعة أدمن `VERIFIED` → 4 إعدادات رؤية اتنشأت. **PASSED**.
4. **`test_ward_reject_flow_and_double_processing_blocked`** — رفض
   الطالب مع سبب → `REJECTED` → محاولة موافقة/رفض تانية على نفس الطلب
   ترفض بـ`ValidationError`. **PASSED**.
5. **`test_duplicate_relationship_request_rejected`** — نفس زوج
   (guardian, ward) مرتين → `AlreadyExistsError`. **PASSED**.
6. **`test_wrong_user_cannot_approve_or_reject`** — مستخدم غريب يحاول
   يوافق/يرفض → `PermissionDeniedError`؛ مراجعة أدمن مبكرة (لسه
   `PENDING_WARD_APPROVAL`) → `ValidationError`؛ تحكّم في الرؤية قبل
   `VERIFIED` → `ValidationError`. **PASSED**.

**النتيجة: 6/6 نجحوا** (مع أساس الجلسة السابقة: **9/9** لكل ملفات
guardian معًا).

### اكتشاف جانبي بيئي (غير مرتبط بالكود، لم يُلمَس)

أول تشغيلة كشفت إن `list_by_role` بترجع **24 حساب `SUPER_ADMIN` حقيقي**
في `tenant_id=1` — throwaway قديمة تمامًا من جلسات اختبار غير مرتبطة
(`p_ctor_*`, `TEST_*`)، محذوف منها التنظيف من قبل. الكود الجديد سليم
(بيبعت فعلًا لكل الأدمنز زي المطلوب) — المشكلة تراكم بيانات throwaway
قديمة. **الإصلاح الوحيد:** تصحيح `_cleanup()` في ملف الاختبار الجديد
نفسه عشان يمسح كل إشعار مرتبط بـ`relationship_id` (بغض النظر عن
المستلم)، مش بس مستخدمي الاختبار — **صفر لمس على أي كود أو بيانات من
جلسات تانية**. اتأكَّد بعدها: `count(*) = 0` على `guardian_relationships`,
`guardian_visibility_settings`, مستخدمي `p_regtest_flow_*`, وإشعارات
`GUARDIAN-ADMIN-REVIEW-%`.

---

## 9. Regression

- **`pytest --collect-only` على كامل `tests/`** (232 اختبار): صفر خطأ
  استيراد جديد. نفس الخطأ المسبق الوحيد (`ActionCommission` من
  `affiliate.models`) — موثَّق سابقًا، صفر علاقة بهذه الجلسة.
- **كل اختبارات guardian معًا** (foundation + flow، 9 اختبارات):
  **9/9 نجحوا**.
- **عيّنة أوسع** (`test_identity_router_protection.py` +
  `test_user_repository_get_by_id_audit.py` +
  `test_user_repository_get_user_audit.py`، 37 اختبار): **25 نجحوا،
  12 فشلوا**. تم التحقق بالتفصيل: **الـ12 فشل صفر علاقة بهذه الجلسة**:
  - كلهم عن "Backlog #8" (`_register_affiliate_commission` +
    `referred_by`) عبر دومينات `zamakana/transport/tourism_sports/
    tenders_auctions/service_marketplace/realestate/
    arbitration_syndicates/manufacturing/invitations/insurance/
    employment/digital_twin` — **صفر أي منها له علاقة بـ`guardian`**.
  - `list_by_role` (الإضافة الوحيدة لـ`identity/repository.py`) تم
    التأكد بـgrep شامل إنها **مُستخدَمة فقط من `guardian/service.py`**
    — لا يمكن بنيويًا أن تؤثر على منطق `_register_affiliate_commission`
    في أي دومين تاني.
  - `identity/router.py`/`service.py`/`schemas.py` كان عندهم بالفعل
    تعديلات **uncommitted من قبل بداية هذه الجلسة** (موجودة في git
    status الأصلي لبداية المحادثة، قبل أي عمل على `guardian` اليوم) —
    الفشل مرتبط غالبًا بيها.
  - **لم يُصلَح — خارج نطاق هذه الجلسة بالكامل.** يحتاج جلسة منفصلة
    مخصصة لـBacklog #8، بنفس قاعدة
    [[feedback_split_urgent_side_findings_from_broader_investigation]].

---

## الحالة النهائية

- **مبني ومتحقَّق منه حيًا بالكامل:** `GuardianService` + `guardian/router.py`
  (6 endpoints)، `UserRepository.list_by_role` جديدة، اختبار حي 6/6
  (9/9 مع الأساس).
- **باج حقيقي اتكشف واتصلح** (`upsert_visibility_setting` +
  `populate_existing=True`).
- **اكتشاف جانبي بيئي موثَّق** (24 حساب SUPER_ADMIN throwaway قديم) —
  لم يُلمَس، خارج النطاق.
- **12 فشل تنظيمي مسبق غير مرتبط اتأكَّد وتوثَّق** — لم يُصلَح، خارج
  النطاق بالكامل (Backlog #8).
- **لم يُعمَل commit على git بعد** — بانتظار طلب المستخدم.
- **PROGRESS_LOG.md** اتحدَّث بإدخال جديد لهذه الجلسة.
