# #45 — تأكيد حي للتعارض قبل أي migration + سؤال على التصميم

**تاريخ:** 2026-08-29
**الحالة:** ✅ السيناريو تكرَّر حيًا فعليًا. صفر migration حتى الآن — بانتظار قرارك على الصياغة.

---

## 0) توضيح أولاً — سؤالك السابق عن الـ7 ملفات

**لأ، مش مُرقَّمة ببند backlog واضح.** مسجَّلة كإدخال باسم
(`iot-translation-service-method-mismatches-post-backlog43-fix`) بعلامة "—" (بلا رقم) في
`PROGRESS_LOG.md` سطر 339، ومُشار ليها من صف #43 في `constructor-mismatch-backlog-classification.md`
— لكن بلا رقم بند مستقل (زي #48) في الملف الموحَّد نفسه. **لسه محتاج قرارك: أرقّمها دلوقتي (#48)
ولا نسيبها كملاحظة تحت #43؟**

---

## 1) التأكيد الحي المطلوب

`translation_cache.text_hash` عمود بقيد `unique=True` **عالمي** (`Column(String(64), unique=True,
index=True, nullable=False)`، `translation/models.py:16`). لكن `TranslationRepository.get_cache_by_hash(tenant_id,
text_hash)` بيفلتر بـ**الاتنين معًا** (`translation/repository.py:13-20`).

**السيناريو المُختبَر (تينانتين حقيقيين: `id=1` و`id=16`، نفس النص بالحرف):**

```
tenant 1, before: get_cache_by_hash -> None (أول مرة)
tenant 1: save_cache committed successfully

tenant 16, before: get_cache_by_hash(16, same hash) -> None
  ← التطبيق فاكر إنه cache miss رغم إن تينانت1 عنده الصف بالفعل

CONFIRMED bug: IntegrityError on tenant 16's commit --
  <class 'asyncpg.exceptions.UniqueViolationError'>:
  duplicate key value violates unique constraint "ix_translation_cache_text_hash"

post-cleanup row count (expect 0): 0
```

**الخلاصة:** السيناريو تكرَّر **بالضبط** زي الموصوف في البند الأصلي — DoS وظيفي حقيقي لأي نص شائع
بين تينانتين مختلفين (مش تسريب بيانات، تينانت16 محاولته بترفض بـ500 بس). تنظيف كامل اتأكد
(`post-cleanup row count: 0`).

---

## 2) اقتراح التصميم — بانتظار موافقتك قبل أي تنفيذ

**المقترَح:**
- إسقاط `unique=True` من عمود `text_hash` نفسه.
- إضافة **composite unique constraint**: `UNIQUE(tenant_id, text_hash)` بدل `UNIQUE(text_hash)`
  وحده — النص هيتخزن لكل تينانت على حدة بأمان، ومطابق تمامًا لمنطق `get_cache_by_hash` الحالي
  (اللي أصلًا بيفلتر بالاتنين معًا).

**البديل المذكور في التصنيف الأصلي:** partial unique index. **رأيي:** composite constraint أبسط
وكافي هنا (مفيش شرط `WHERE` مطلوب فعليًا — كل صف عنده `tenant_id` حقيقي دايمًا، مش زي حالة
`affiliate_commission_tiers`/`GLOBAL` اللي كانت محتاجة partial index بسبب `NULL`). partial index
هيبقى مطلوب بس لو فيه حاجة زي "نفس النص ممكن يتكرر جوه نفس التينانت لسبب تاني" — مش الحالة هنا.

**خطوات التنفيذ المقترَحة (لو وافقت):**
1. migration جديدة: إسقاط `ix_translation_cache_text_hash` (unique)، إضافة index عادي غير unique
   على `text_hash` وحده (يفيد أداء البحث لو احتجناه لاحقًا)، إضافة `UNIQUE(tenant_id, text_hash)`.
2. تحقق حي بعد الـmigration: نفس سيناريو التينانتين فوق يتكرر، لكن المرة دي **بلا** `IntegrityError`
   — تينانت16 يقدر يترجم نفس النص وينشئ صفه المستقل بنجاح.
3. تأكيد إضافي: صفوف tenant1/tenant16 الاتنين بيتخزنوا بـ`text_hash` متطابق لكن `id` مختلف —
   عزل حقيقي.

---

## القرارات المطلوبة منك

1. تأكيد على صياغة الـmigration (composite unique — موافق، ولا partial index، ولا حاجة تانية؟).
2. ترقيم `iot-translation-service-method-mismatches-post-backlog43-fix` كبند رسمي (#48) في الملف
   الموحَّد ولا يفضل ملاحظة تحت #43؟
