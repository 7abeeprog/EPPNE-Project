# فحص read-only: بند backlog — `InsurancePolicyResponse.issuer_entity_id` غير Optional

**التاريخ:** 2026-09-10
**النطاق:** فحص read-only بحت — **صفر تعديل كود**. بناءً على البند رقم 5
المفتوح في
`.claude/reports/insurance-entity-membership-gap-fix-session-log.md`
(نفس الجلسة اللي طبّقت migration `049_insurance_issuer_entity_id_set_null.py`).

---

## 1) `InsurancePolicyResponse` كاملة

من `eppne-backend/app/domains/insurance/schemas.py:15-48`:

```python
class InsurancePolicyCreate(BaseModel):
    issuer_entity_id: int = Field(description="معرف الكيان المصدر")
    name: str = Field(..., min_length=3, max_length=255, description="اسم البوليصة")
    policy_type: PolicyType = Field(description="نوع التأمين")
    description: Optional[str] = Field(default=None, description="وصف البوليصة")
    base_premium_mrusdt: Decimal = Field(..., gt=0, description="القسط الأساسي")
    premium_cycle: PremiumCycle = Field(default=PremiumCycle.MONTHLY, description="دورة القسط")
    max_coverage_limit_mrusdt: Decimal = Field(..., gt=0, description="الحد الأقصى للتغطية")
    terms_and_conditions: Optional[Dict[str, Any]] = Field(default=None, description="الشروط والأحكام")
    smart_contract_address: Optional[str] = Field(
        default=None,
        pattern="^0x[a-fA-F0-9]{40}$",
        description="عنوان العقد الذكي"
    )


class InsurancePolicyUpdate(BaseModel):
    name: Optional[str] = ...
    description: Optional[str] = ...
    base_premium_mrusdt: Optional[Decimal] = ...
    premium_cycle: Optional[PremiumCycle] = ...
    max_coverage_limit_mrusdt: Optional[Decimal] = ...
    terms_and_conditions: Optional[Dict[str, Any]] = ...
    is_active: Optional[bool] = ...
    # لا يوجد issuer_entity_id — غير قابل للتعديل بعد الإنشاء


class InsurancePolicyResponse(InsurancePolicyCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

## 2) هل `InsurancePolicyResponse` فعلًا وارثة `InsurancePolicyCreate`؟

**نعم، وراثة مباشرة (`class InsurancePolicyResponse(InsurancePolicyCreate)`)،
لا يوجد أي إعادة تعريف لـ`issuer_entity_id` في `Response`.** أي تعديل على
النوع أو القيمة الافتراضية للحقل في `InsurancePolicyCreate` هيؤثر تلقائيًا
على الاتنين، لأن Pydantic بيورّث تعريف الحقل بالكامل (النوع + `Field(...)`)
إلا لو اتكتب override صريح في الابن.

### هل `InsurancePolicyCreate` لازم تفضل `int` إجباري؟

**أيوه، مؤكَّد من `service.py:126-133`:**

```python
async def create_policy(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> InsurancePolicy:
    """إنشاء بوليصة تأمين جديدة (للمشرفين فقط، وأعضاء الكيان المُصدِر فقط)."""
    member = await self.membership.get_member(
        entity_type=ENTITY_TYPE, entity_id=data["issuer_entity_id"],
        user_id=user_id,
    )
    if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
        raise PermissionDeniedError("Not authorized to create policy for this entity")
```

فحص الصلاحية بيستخدم `data["issuer_entity_id"]` مباشرة كـ`entity_id` في
استعلام عضوية حقيقي — لازم يكون رقم فعلي موجود وقت الإنشاء، مفيش أي مسار
منطقي لإنشاء بوليصة بدون كيان مُصدِر حقيقي. **`InsurancePolicyCreate` صح
كما هي، ومينفعش تتغيّر لـ`Optional`.**

### الخلاصة: الإصلاح الصحيح هو **override في `InsurancePolicyResponse` فقط**

```python
class InsurancePolicyResponse(InsurancePolicyCreate):
    issuer_entity_id: Optional[int] = None   # override — الأب يفضل int إجباري
    id: int
    ...
```

هذا يطابق نمط "الأب لغرض الإنشاء (صارم)، الابن لغرض القراءة (متسامح مع
حالات ما بعد migration 049)" بدون المساس بمنطق `create_policy`.

**نقطة إضافية لوحظت أثناء الفحص (خارج نطاق البند المطلوب، للتوثيق فقط):**
`update_policy` (`service.py:172-177`) بيستخدم
`cast(int, policy.issuer_entity_id)` كـ`entity_id` في نفس فحص العضوية —
لو `issuer_entity_id` بقى `NULL` فعليًا (بعد حذف الكيان)، الـ`cast` هيمرّر
`None` كـ`entity_id` لـ`EntityMembershipService.get_member`، وده هيرجّع
`member is None` غالبًا (رفض صامت بـ403) بدل خطأ واضح — سلوك مقبول
(refuse-safe) بس مش موثَّق كقرار مقصود. لا يحتاج تدخّل في نطاق هذا البند.

---

## 3) Grep شامل: هل فيه frontend/consumer تاني بيعتمد إن `issuer_entity_id` دايمًا رقم؟

بحث على مستوى المشروع كله عن `issuer_entity_id` (28 نتيجة، أغلبها تقارير/
migrations/اختبارات سابقة). الملفات ذات الصلة الفعلية بالـresponse schema:

| الملف | الاستخدام |
|---|---|
| `eppne-web/types/insurance.ts:10` | `issuer_entity_id: number;` — تعريف نوع يدوي غير-Optional |
| `eppne-web/src/lib/api-types.ts:10746,10769` | نفس الشيء، لكن **مولَّد تلقائيًا من `openapi.json`** (`openapi-typescript`) — هيتحدَّث تلقائيًا لو الـbackend schema اتغيّرت وأُعيد توليد الملف، **ممنوع تعديله يدويًا** حسب معايير المشروع |
| `eppne-web/components/insurance/PolicyCard.tsx:54` | `الجهة المصدرة: #{policy.issuer_entity_id}` — استخدام مباشر بدون أي فحص null |

**لا يوجد أي مستهلك آخر** (لا hooks، لا صفحات أخرى، لا استدعاءات API خارج
هذين الملفين).

### أثر عملي لو اتعمل الـoverride بدون لمس الفرونت إند:

`PolicyCard.tsx` بتستخدم `{policy.issuer_entity_id}` كـJSX expression مش
template string — لو القيمة `null`/`undefined`، React مايعرضش النص
`"null"`/`"undefined"`، لكن السطر هيطلع `"الجهة المصدرة: #"` (بدون رقم
بعد الـ`#`) — مش crash، لكن UX غامض للمستخدم (بالضبط المشكلة المذكورة في
الطلب). **لازم تعديل `PolicyCard.tsx` (وتحديث `types/insurance.ts`
يدويًا + إعادة توليد `api-types.ts`) في نفس مهمة الإصلاح الفعلي**، مش
جزء من هذا الفحص read-only.

---

## 4) هل فيه حقل تاني مفيد نضيفه؟

بحثت عن دالة موجودة فعلًا لجلب اسم/بيانات الكيان المُصدِر لاستخدامها في
enrichment. الموجود الوحيد هو placeholder غير حقيقي:

```python
# service.py:57-58
async def _get_entity_email(self, entity_id: int) -> str:
    return f"entity_{entity_id}@eppne.com"
```

ده stub (مش استعلام حقيقي على DB) — مش مصدر موثوق لبناء `issuer_entity_name`
عليه، وخارج نطاق هذا البند أصلًا (مشكلة منفصلة في email hardcoding، شبيهة
بمشكلة موثقة سابقًا في [[project_retry_failed_payments_hardcoded_receiver_email_backlog]]).

`SovereignEntity` (`sovereign_entities/models.py:47`) عندها عمود `name`
حقيقي (`String(255), nullable=False`)، فمن الناحية الفنية ممكن `join` وقت
القراءة يجيب `issuer_entity_name` للبوالص اللي لسه كيانها موجود.

**لكن نقطة حاسمة من migration 049 نفسها:** الحذف حذف فعلي (hard delete،
`ondelete="SET NULL"`)، مش soft-delete. يعني لما الكيان يتمسح فعلًا،
سجله بيروح خالص من `sovereign_entities_v2` — مفيش نسخة تاريخية نقدر
نجيب منها `issuer_entity_name` وقت القراءة بعد الحذف. الاسم يبقى غير
قابل للاسترجاع بمجرد الحذف، بالظبط اللحظة اللي محتاجين فيها نعرضه
للمستخدم كـ"كانت الجهة اسمها كذا وانمسحت".

**يعني:**
- `issuer_entity_name` (join حي على `SovereignEntity.name`) — مفيد فقط
  للبوالص اللي كيانها **لسه موجود** (يوفّر استدعاء تاني للفرونت إند)،
  لكنه `null` بالظبط في نفس الحالة اللي محتاجين نوضّحها (بعد الحذف) —
  فمابيحلّش المشكلة الأساسية المطروحة في السؤال.
- `is_issuer_deleted: bool` — **حقل زيادة بيانات لا يحمل معلومة جديدة**:
  بما إن `issuer_entity_id` كانت دايمًا إجبارية `int` وقت الإنشاء ومفيش
  أي مسار تاني يخليها `NULL` غير الحذف الفعلي للكيان (migration 049 هي
  المصدر الوحيد)، فـ`issuer_entity_id is None` **بيساوي حرفيًا**
  `is_issuer_deleted == True`. إضافته تكرار منطقي لنفس المعلومة بشكل
  تاني، مش معلومة إضافية.

**التوصية:** أبسط حل يحل المشكلة المطروحة فعلًا هو تعديل الفرونت إند
(`PolicyCard.tsx`) ليعرض نص واضح زي `"جهة مُصدِرة محذوفة"` لما
`issuer_entity_id` تبقى `null`/`undefined` بدل الاعتماد على `#{id}`
الغامض — بدون أي إضافة حقول جديدة في الـbackend schema. لو حبينا لاحقًا
نسهّل على الفرونت إند عرض اسم الجهة للبوالص النشطة (تحسين UX، مش إصلاح
باج)، فـ`issuer_entity_name` (نُل عند الحذف بطبيعة الحال) ممكن يتضاف
كبند منفصل — لكنه ليس جزءًا من إصلاح الـ500 نفسه.

---

## 5) ملخص القرار الموصى به (للجلسة القادمة اللي هتنفّذ الإصلاح الفعلي)

1. **`schemas.py`**: إضافة override وحيد في `InsurancePolicyResponse`:
   `issuer_entity_id: Optional[int] = None`. **عدم لمس `InsurancePolicyCreate`
   إطلاقًا** — لازم تفضل `int` إجبارية لأن `create_policy` بتعتمد عليها
   مباشرة في فحص عضوية حقيقي (`service.py:128-129`).
2. **`eppne-web/types/insurance.ts`**: `issuer_entity_id: number | null;`
   (تعديل يدوي، الملف مش مولَّد).
3. **`eppne-web/src/lib/api-types.ts`**: يتحدَّث تلقائيًا بإعادة توليد
   `openapi.json` بعد تعديل الـbackend schema — **ممنوع تعديله يدويًا**.
4. **`PolicyCard.tsx:54`**: فحص `null` صريح + نص بديل واضح بدل `#{undefined}`.
5. لا حاجة لإضافة `issuer_entity_name` أو `is_issuer_deleted` كجزء من هذا
   الإصلاح — الأول لا يحل المشكلة (نُل في نفس الحالة)، والثاني تكرار
   منطقي لمعلومة موجودة بالفعل في `issuer_entity_id is None`.
6. نطاق الإصلاح صغير جدًا (سطر واحد backend + سطرين فرونت إند) — لا
   يستدعي migration جديدة (الـDB schema سليمة بالفعل من migration 049،
   المشكلة كانت في طبقة الـPydantic response فقط).

**لم يُعدَّل أي كود في هذا الفحص — بحث read-only بحت فقط.**
