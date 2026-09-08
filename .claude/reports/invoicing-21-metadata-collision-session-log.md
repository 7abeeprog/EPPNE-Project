# جلسة #21 — invoicing-invoice-response-metadata-collision

**تاريخ الجلسة:** 2026-08-29
**الحالة النهائية: ✅ البند مُغلَق بالفعل — لا يوجد عطل حالي، لا حاجة لأي تعديل كود.**

---

## الخلاصة المباشرة (قبل التفاصيل)

البند #21 كان مُصنَّفًا في `constructor-mismatch-backlog-classification.md` بأنه
"لسه مفتوحة بالكامل، صفر لمس" (تحديث 2026-08-29). **هذا التصنيف قديم/غير
دقيق.** العطل الموصوف في الجلسة (تصادم `metadata` مع `SQLAlchemy.Base.metadata`
يمنع `list_invoices`) **تم إصلاحه بالفعل** في commit سابق:

```
93e68ac fix(invoicing): close create_invoice mass-assignment, fix masked metadata bug
Author: 7abeeprog <eppne2020@gmail.com>
Date:   Tue Aug 25 14:40:15 2026 +0300
```

هذا الـcommit كان يعالج بند أمني مختلف تمامًا (mass-assignment في
`create_invoice`)، وأصلح تصادم الـ`metadata` كـ"إصلاح جانبي في نفس مسار
الاستجابة" (بالضبط زي ما وصفه commit message نفسه). التصنيف الذي أنتج بند
#21 في 2026-08-25 يبدو أنه أُضيف بدون ملاحظة أن نفس اليوم شهد الإصلاح.

---

## 1. أين كان التصادم فعليًا (اقتباسات حية)

**لم يكن التصادم في الموديل (`models.py`) ولا في الـmigration إطلاقًا.**
كلاهما استخدما `invoice_metadata` من البداية:

`eppne-backend/app/domains/invoicing/models.py:78`
```python
invoice_metadata = Column(JSONB, nullable=True)
```

`eppne-backend/migrations/versions/016_create_invoices_table.py:30`
```python
sa.Column('invoice_metadata', JSONB, nullable=True),
```

**التصادم كان حصريًا في طبقة الـPydantic schema** (`InvoiceBase`)، اللي كانت
بتستخدم اسم `metadata` بينما الموديل بيستخدم `invoice_metadata` — الفرق ده
هو اللي كان بيكسر `model_validate(from_attributes=True)`:

قبل الإصلاح (من `git show 93e68ac`):
```python
-    metadata: Optional[Dict[str, Any]] = Field(None, description="بيانات إضافية (JSON)")
+    invoice_metadata: Optional[Dict[str, Any]] = Field(None, description="بيانات إضافية (JSON)")
```

**آلية العطل الحقيقية:** لما كان schema field اسمه `metadata`، Pydantic (مع
`from_attributes=True`) كان بيحاول يقرأ `invoice.metadata` من كائن الـORM.
لكن `invoice` هو instance من `Invoice(Base)`، و`Base.metadata` هو attribute
محجوز على مستوى الكلاس (`MetaData` instance بتاعة SQLAlchemy)، فبيرجع الكائن
الغلط بدل الـJSONB الفعلي. ده كان بيفشل validation (لأن `MetaData` مش
`Dict[str, Any]` ولا `None`) → **400 مضلِّل حتى لو الكتابة في الـDB نجحت
فعلًا.**

**النطاق الحقيقي للعطل (قبل الإصلاح):** أي endpoint بيستخدم
`InvoiceResponse.model_validate(invoice)` — يعني `POST /invoicing/invoices`
و`GET /invoicing/invoices/{id}` و`GET /invoicing/invoices` (list) و
`PATCH .../status` و`.../pay` و`.../cancel` — **كل واحد فيهم كان هيفشل في
الاستجابة**، مش `list_invoices` بس زي ما كان مفترض في وصف الجلسة الأصلي.

---

## 2. التحقق الحي (بعد الإصلاح — تأكيد إن العطل مش موجود دلوقتي)

شغّلت سكريبت مباشر ضد قاعدة البيانات الحقيقية (`postgresql+asyncpg` عبر
`AsyncSessionLocal`، صفر mock) يجيب صفوف فواتير حقيقية ويمرّرها فعليًا عبر
نفس مسار الاستجابة (`InvoiceResponse.model_validate`):

```
invoices table row count: 16
fetched 5 invoice rows for live validation
OK invoice_number=INV-1-000001 invoice_metadata=None
OK invoice_number=INV-1-000002 invoice_metadata=None
OK invoice_number=INV-1-000003 invoice_metadata=None
OK invoice_number=INV-1-000004 invoice_metadata=None
OK invoice_number=INV-1-000005 invoice_metadata=None
```

صفر استثناءات على الـ5 صفوف الحقيقية (تينانت `1`). لو كان التصادم لسه موجود
كان هيرمي `ValidationError` واضح على كل صف. **مؤكَّد حيًا: العطل الموصوف
مش موجود في الكود الحالي.**

(لم يشغَّل عبر HTTP endpoint فعلي/uvicorn لأن السيناريو المُتحقَّق منه —
قراءة الموديل وتمريره عبر نفس دالة الـserialization اللي كان بيستخدمها
الـrouter حرفيًا — كافٍ لإثبات/نفي مسار العطل، وهو نفس الأسلوب المتبع في
جلسات تحقق سابقة بالمشروع.)

---

## 3. هل فيه نمط تسمية متبع في المشروع؟ (لتحديد الحل الصحيح لو كان العطل لسه موجود)

بحثت في كل الموديلات (`grep` شامل على `Column(JSONB`) عن أي حقل تاني اسمه
حرفيًا `metadata`. **صفر نتائج** — كل حقل JSONB في المشروع بيستخدم اسم مركّب
(`<entity>_metadata` أو اسم وصفي مختلف تمامًا)، مثلًا:

| الدومين | اسم العمود الفعلي في DB |
|---|---|
| `invoicing` | `invoice_metadata` |
| `identity` | `profile_metadata` |
| `manufacturing` | `item_metadata` |
| `academy` | `ai_training_metadata` |
| `commerce` | `seo_metadata` |
| `social` | `gift_metadata` |
| `realestate` | `contract_metadata` |
| `invitations` (`CustomerInteraction`) | `meta_data` |

**النمط المتبع = الخيار (ب) بمعنى أوسع:** مفيش أي مكان في المشروع بيستخدم
`Column("metadata", key="x")` (الخيار أ). كل الحالات غيّرت **اسم العمود في
الـDB نفسه من البداية** ليكون مركّبًا — مفيش حالة واحدة فيها العمود اسمه
`metadata` في الـDB والـPython attribute بس مختلف. بالنسبة لـ`invoicing`
تحديدًا، الحظ إن العمود في الـDB **كان أصلًا `invoice_metadata`** من أول
migration (016) — يعني مفيش حتى حاجة تتغير في الـDB، كان بس الـPydantic
schema هو اللي متأخر عن التسمية الصحيحة، وده اتصلح فعلًا في 93e68ac.

**لو كان السؤال لسه مطروحًا اليوم (لبند جديد مشابه):** التوصية بناءً على
النمط الموجود فعلاً في المشروع هي تسمية العمود نفسه `<entity>_metadata` في
الـDB من البداية (زي كل الحالات التسعة أعلاه) — مش استخدام `key=` كـalias
بايثوني فقط، حتى يفضل اسم العمود في الـDB متسقًا مع اسم الـattribute
ومايحصلش لبس لأي حد بيكتب SQL يدوي أو بيقرأ الـschema مباشرة.

---

## 4. كل الأماكن اللي بتستخدم `Invoice.invoice_metadata` / كانت بتستخدم `metadata`

بحث شامل (`grep -rn`) في الباك إند كله:

- `eppne-backend/app/domains/invoicing/models.py:78` — تعريف العمود (`invoice_metadata`)
- `eppne-backend/app/domains/invoicing/schemas.py:17` — `InvoiceBase.invoice_metadata` (بعد الإصلاح)
- **صفر** استخدامات تانية لـ`.metadata` أو `.invoice_metadata` في
  `service.py`, `repository.py`, `router.py` بدومين `invoicing` — الحقل
  مش مُستخدَم فعليًا في أي منطق عمل حاليًا (بيتقرأ/يتكتب بس عبر
  الـschema/الموديل، مفيش كود بيعالج قيمته).
- الـ13 دومين اللي بتستدعي `InvoicingService` مباشرة (`transport`,
  `tourism_sports`, `realestate`, `manufacturing`, `insurance`,
  `arbitration_syndicates`, `zamakana`, `tenders_auctions`,
  `service_marketplace`, `ai_agents`, `invitations`, `employment` [task],
  إلخ) — **صفر واحد منهم بيمرر أو بيقرأ `metadata`/`invoice_metadata` في
  نداءاته لـ`create_invoice()`** (الدالة أصلًا مش بتاخد `metadata` كـkwarg،
  راجع `service.py:51-61`).

**الخلاصة: حجم التغيير المطلوب لو كان لسه محتاج إصلاح = صفر استدعاءات خارجية
متأثرة.** الإصلاح اللي حصل بالفعل كان محصور 100% في ملف `schemas.py` بدون
أي أثر جانبي على أي دومين تاني، بالظبط زي ما وصف commit message.

---

## 5. اكتشاف جانبي خارج نطاق هذه الجلسة (للتوثيق فقط — صفر لمس)

نفس **فئة** العطل (قراءة `.metadata` من كائن SQLAlchemy declarative فيرجع
`Base.metadata` الخطأ بدل العمود الفعلي) موجودة **حيًا الآن** في دومين
مختلف تمامًا، غير مرتبط بـ`invoicing`:

`eppne-backend/app/domains/invitations/models.py:270`
```python
class CustomerInteraction(Base):
    __tablename__ = "crm_interactions"
    ...
    meta_data = Column(JSONB, default=dict)   # اسم العمود الفعلي: meta_data
```

`eppne-backend/app/domains/invitations/service.py:606`
```python
"metadata": interaction.metadata,   # ⚠️ بيقرأ Base.metadata مش meta_data
```

هذا **لم يكن جزء من مهمة الجلسة الحالية** (نطاقها `invoicing` #21 فقط)، ومش
مؤكَّد حيًا هنا، ومفيش أي تعديل عليه. موثَّق كاكتشاف جانبي عشان يُضاف كبند
جديد في `constructor-mismatch-backlog-classification.md` في جلسة لاحقة، مش
مُعالَج الآن.

كمان لوحظ (بدون فحص أو لمس) أن `router.py:330` بيستدعي
`InvoicingService(db)` بدون `tenant_id` بينما الـconstructor بيطلبه كـ
parameter إجباري (`service.py:23`) — احتمال TypeError عند استدعاء
`POST /invoicing/admin/process-overdue`. غير مرتبط ببند #21، غير محقَّق حيًا،
موثَّق فقط للمرجعية المستقبلية.

---

## 6. التوصية النهائية

**لا يوجد قرار مطلوب اتخاذه — لا يوجد عطل نشط.** البند #21 يُغلَق كـ
"**مُغلَق بالفعل، اكتُشف الإغلاق أثناء التحقيق [2026-08-29]**" مع الإشارة
لـ commit `93e68ac` كمصدر الإصلاح، بدلًا من كونه بندًا مفتوحًا يحتاج قرار
تصميمي (أ) أو (ب).

**✅ نُفِّذ [2026-08-29]:** بموافقة صريحة، تحديث توثيقي فقط (صفر تعديل كود):
- `constructor-mismatch-backlog-classification.md` — سطر #21 حُدِّث لـ"✅ مُغلَق
  بالفعل"، وعدّاد "المجموعة ب" حُدِّث (12 مُغلَقة بدل 11، 2 مفتوحة بدل 3).
- `PROGRESS_LOG.md` سطر 223 (`invoicing-invoice-model-metadata-attribute-
  collision`) — نفس بند #21 بالحرف، كان موجودًا مسبقًا بحالة "مفتوح"،
  اكتُشف أثناء المراجعة قبل التنفيذ (بطلب المستخدم صريح: تحقق أولاً قبل
  إضافة بند جديد) — حُدِّث في مكانه بدل إضافة بند مكرر، طبقًا لقاعدة الملف
  نفسه ("جدول الـBacklog هو مصدر الحقيقة الوحيد، يُحدَّث بالتعديل في مكانه").
- أُضيف بندان جديدان فعليًا (مختلفان، غير مكررين) في `PROGRESS_LOG.md`:
  `invitations-customer-interaction-metadata-attribute-collision` و
  `invoicing-process-overdue-invoices-missing-tenant-id-arg` — كلاهما صفر
  تحقق حي، صفر لمس، توثيق اكتشاف فقط.

**الجلسة مُقفلة.**
