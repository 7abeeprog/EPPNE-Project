# ملخص نهائي: توحيد نظامي Referral/Affiliate

**تاريخ:** 2026-09-05 → 2026-09-07 (3 جلسات متتالية)
**الحالة:** ✅ Phases 0-9 مكتملة ومُتحقَّق منها حيًا (migration مطبَّقة +
6/6 pytest ناجحة). **لم يُنفَّذ بعد:** الـcommit النهائي (بانتظار
موافقتك الصريحة على القائمة).

هذا الملف فهرس/ملخص فقط — التفاصيل الكاملة (كل قرار، كل اكتشاف حي، كل
سطر كود) موزَّعة على 4 تقارير مرجعية أسفل، بترتيب زمني.

---

## المشكلة الأصلية

3 أنظمة إحالة/عمولة منفصلة تمامًا في المشروع، بلا تنسيق بينها:
- **A** (`affiliate` domain): 10 مستويات، Product-Scoped، لكن ميت
  تشغيليًا (غير موصول بأي عملية شراء حقيقية).
- **B** (`commerce` domain): 10 مستويات Sponsor Chain، الحي فعليًا،
  لكن بلا أي تمايز منتج.
- **C** (12 دومين، Backlog #10): عمولة مباشرة مستوى واحد، معطَّلة
  بسبب `User.referred_by` غير موجود كعمود أصلًا.

## القرار المعتمد

توحيد الثلاثة على نظام A، حذف نظام B بالكامل، ربط الـ12 دومين بنفس
الآلية — عبر مفهوم جديد `AffiliateScope` يسمح بشجر/عمولات منفصلة تمامًا
لكل نطاق (منتج فردي / مجموعة منتجات / كل مبيعات الـtenant)، بدل الربط
المباشر بـ`product_id`.

## ما تم تنفيذه (Phases 0-9)

| Phase | المحتوى |
|---|---|
| 0 | Migration `045` — جداول/أعمدة جديدة، حذف نظامي B وC، seed خدمة SaaS. طُبِّقت فعليًا على DB (`eppne_v2`) بعد إصلاح باجين اكتُشفا وقت التطبيق. Round-trip `downgrade→upgrade` ناجح. |
| 1-2 | Models + Repository — بما فيها إصلاح باج `MultipleResultsFound` الموثَّق من جلسات سابقة. |
| 3 | Service — تعميم `distribute_commissions` ليقبل أي مصدر بيع (مش بس `commerce.Order`)، `ensure_referral_link` موحَّدة. |
| 4 + 7 | Router/Schemas جديدة + Hook تفعيل SaaS تلقائي (`ENTITY_WIDE` scope عند أول اشتراك). |
| 5 | ربط `academy` — اكتشاف: تسجيل كورس بكود إحالة كان بيسجّل الشجرة بس، **صفر عمولة اتوزّعت فعليًا من أي وقت مضى**. اتصلح. |
| 6 | ربط الـ12 دومين (`zamakana`, `transport`, `insurance`, إلخ) — من مستوى واحد لـ10 مستويات فعلية. |
| 8 | إصلاح 3 أعطال Celery مستقلة + تسجيل `clean_expired_links` في `beat_schedule` لأول مرة. |
| 9 | ملف `pytest` رسمي دائم — **6/6 اختبارات ناجحة**، يغطي 5 سيناريوهات معتمدة صراحة (تفاصيل تحت). |

## اكتشاف جانبي مهم — باج أمني منفصل تمامًا

أثناء Phase 9 (اختبار تفعيل SaaS)، اكتُشف إن `POST /saas/subscriptions/{plan_id}`
معطَّل بالكامل حاليًا لأي tenant/خدمة (باج `get_plan_by_id` chicken-and-egg)،
وإن إصلاحه بمعزل عن ثغرة موثَّقة سابقًا (`check_feature_access` بلا ربط
`feature→service_id`) هيعيد فتحها. **بقرارك:** لم يُلمَس — اختُبر
الـhook بمعزل (Option 3)، وسُجِّل بند backlog أمني منفصل وواضح في
`PROGRESS_LOG.md` تحت اسم `saas-check-feature-access-missing-service-id-binding`.

## التحقق النهائي

- `import app.main` ناجح بعد كل مرحلة تراكميًا.
- اختبار حي يدوي كامل end-to-end (مُنظَّف بعده بالكامل).
- **`pytest tests/test_referral_affiliate_unified_system.py` — 6/6 ناجحة**،
  تغطي: الأساسي (10%)، سلة بنطاقين مختلطة (تقسيم صحيح)، تفعيل SaaS
  (hook + idempotency)، zamakana (مرجع الـ12 دومين)، digital_twin
  (حالة affiliate_code المباشر)، عدم تفعيل SaaS (تخطٍّ صامت آمن).
- `git diff --stat` نهائي مُقيَّد: **28 ملف معدَّل + 6 ملفات جديدة = 34 ملف**،
  مفصول تمامًا عن كومة تعديلات غير مرتبطة من جلسات سابقة موجودة في نفس الـrepo.

## المتبقي (بانتظارك)

**الـcommit النهائي فقط** — القائمة المُقيَّدة بـ34 ملفًا جاهزة ومعروضة
في المحادثة، لم يُنفَّذ `git add`/`git commit` بعد.

---

## التقارير المرجعية الكاملة (بالترتيب الزمني)

1. `.claude/reports/referral-affiliate-system-design-session-log.md` —
   التحقيق الأولي، اكتشاف الأنظمة الثلاثة.
2. `.claude/reports/referral-affiliate-unified-implementation-session-log.md` —
   التصميم التفصيلي الكامل (AffiliateScope، خطة المراحل، الأسئلة
   المفتوحة وإجاباتها).
3. `.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md` —
   سجل التنفيذ الفعلي لكل مرحلة (0-9)، كل باج اكتُشف وأُصلح أثناء
   التطبيق الحي، نتائج التحقق.
4. `.claude/reports/saas-get-plan-by-id-security-tradeoff-note.md` —
   توضيح الباج الأمني المكتشَف جانبيًا + الخيارات الأربعة.
