# `test_saas_active_subscription.py`

## المرجع الأصلي
- `.claude/reports/saas-control-service-fix-session-log.md` (Backlog #9، جلسة `saas-control-service-get-active-subscription-fix`، إكمال).

## السبب الجذري (كان) — ملخص
`SaaSControlService.get_active_subscription(tenant_id)` غير موجودة إطلاقًا — لم تُكتب من الأساس، مستخدَمة من 8 دومينات (`realestate`, `insurance`, `digital_twin`, `employment`, `arbitration_syndicates`, `invitations`, `manufacturing`, `logistics`) بنفس التوقيع الناقص. اكتشاف حرج إضافي أثناء الإصلاح: `subscription.features` غير موجودة على `TenantSubscription` أصلًا (موجودة فقط على `ServicePlan` عبر `subscription.plan`)، ومصممة كـ`List[str]` مش `Dict[str,bool]`.

## الإصلاح المُطبَّق
1. `SaaSRepository.get_any_active_subscription(tenant_id)` (جديدة) — اشتراك واحد شامل نشط/تجريبي للـtenant، بغض النظر عن الخدمة.
2. `SaaSControlService.get_active_subscription(tenant_id)` (جديدة) — wrapper صرف حولها.
3. الثمانية دومينات: `subscription.features`/`.get()` → `subscription.plan.features`/`in` (list-membership) + فحص دفاعي `if not subscription.plan: raise PermissionDeniedError(...)`.

## إيه اللي بيتحقق منه هذا الملف
4 اختبارات حية (بلا `monkeypatch` على `_check_saas_limits` نفسها — هذا جوهر ما بنتحقق منه)، نفس الأربعة دوال المُتحقَّق منها حيًا في التقرير الأصلي (قسم 14.1):

| الدالة | مستوى التحقق |
|---|---|
| `realestate.rent_unit` | ✅ تحقق حي كامل، نجاح تام |
| `insurance.subscribe` | ✅ تحقق حي كامل للمسار المالي (تحويل القسط + إنشاء الاشتراك) |
| `realestate.buy_fractional_ownership` | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب ببج مسبق منفصل: Backlog #16) |
| `insurance.review_claim` | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب ببج مسبق منفصل: Backlog #1) |

**منهجية موحَّدة:** نجاح `_check_saas_limits` الحقيقية (صفر `AttributeError` على `get_active_subscription`/`subscription.features`) هو الإثبات المباشر لإصلاح #9، بغض النظر عمّا يحصل بعده في الدالة. الدالتان المحجوبتان (`buy_fractional_ownership`, `review_claim`) بيستخدموا `pytest.raises` بمطابقة نص الخطأ المحدَّد لإثبات إن الاستدعاء وصل فعليًا لما بعد `_check_saas_limits` قبل ما يفشل ببج تاني موثَّق مسبقًا، مع تأكيد تراجع نظيف (صفر أثر جزئي).

### تجاوز متعمَّد لبج غير مرتبط (`invoicing-generate-invoice-number-count-based-collision`)
`rent_unit`/`subscribe` بتستدعي `InvoicingService.create_invoice()` بعد `commit()`. هذا الاستدعاء بيفشل حاليًا حتميًا لـ`tenant_id=1` ببج مسبق موثَّق بالكامل في `tests/test_realestate_insurance_savepoint.py`/`PROGRESS_LOG.md` (فجوة ترقيم مستهلَكة بالكامل). هذا الملف بيتجاوزه عمدًا بـ`monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)` — مش لأنه جزء من #9، لكن لعزل التحقق هنا على منطق #9 تحديدًا بلا تلوّث من بج تاني، متسقًا مع قاعدة "المنطق المُحقَّق منه فعليًا فقط" لكل جلسة على حدة. **صفر لمس على `invoicing/service.py`.**

## 🔴 اكتشاف بج production حقيقي أثناء استكمال الجلسة [2026-08-19] — `insurance-review-claim-issuer-entity-id-reviewer-id-conflict`
اختبار `review_claim` كان بيفشل بـ`ForeignKeyViolationError` — الكود الأصلي (مكتوب قبل هنج VS Code) مرَّر `reviewer.id` (يوزر throwaway عادي) كـ`InsurancePolicy.issuer_entity_id`، لكن العمود ده FK حقيقي على `sovereign_entities_v2.id` مش `users.id`. الفحص بالقراءة المباشرة كشف حاجة أعمق من مجرد بيانات throwaway غلط: **`InsuranceService.review_claim()` (`insurance/service.py:431`) بتقارن `policy.issuer_entity_id` (نطاق `sovereign_entities_v2.id`) مباشرة بـ`reviewer_id`، بينما `insurance/router.py:195` بيمرر `reviewer_id=current_user.id` (نطاق `users.id` مختلف تمامًا) في أي استدعاء حقيقي من الـAPI.** يعني أي `superuser` حقيقي هيفشل بـ`PermissionDeniedError("Not authorized to review this claim")` دايمًا تقريبًا — **ميزة مراجعة/الموافقة على مطالبات التأمين معطَّلة فعليًا في الإنتاج.** نفس فئة البج المسبق الموثَّق `tourism-place-transfer-bid-player-id-user-id-conflict` (خلط نطاقي IDs مختلفين).

**مُوثَّق كبند Backlog منفصل جديد في `PROGRESS_LOG.md` (`insurance-review-claim-issuer-entity-id-reviewer-id-conflict`) — صفر لمس على `insurance/service.py`/`insurance/router.py`.**

**التجاوز هنا (مش إصلاح):** استخدام `EXISTING_ISSUER_ENTITY_ID = 4` (صف throwaway موجود بالفعل، قراءة فقط، نفس نمط `EXISTING_LAND_ASSET_ID`) كـ`issuer_entity_id` **و**كـ`reviewer_id` معًا عند استدعاء `review_claim()` — بيخلي الفحص المكسور (سطر 431) يعدي بالصدفة، عشان الاختبار يوصل فعليًا لهدفه (تأكيد #9 ثم Backlog #1 بعده). **هذا مش سيناريو واقعي لمسار المراجع الحقيقي — الاختبار بيتجنب البج الجديد عمدًا، مش بيثبته ولا بيفحصه.**

## بيانات throwaway
- `tenant_id=1` ("Local Test Tenant").
- `EXISTING_LAND_ASSET_ID=1`, `EXISTING_ISSUER_ENTITY_ID=4` — صفوف موجودة بالفعل، قراءة فقط، صفر تعديل/حذف.
- كل اختبار يستخدم بيانات جديدة (`uuid4` suffix) — صفر تصادم بين تشغيلات.
- تنظيف كامل في `finally` بعد كل اختبار؛ تأكَّد بـ`SELECT` مباشر بعد التشغيل: صفر صفوف throwaway متبقية.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_saas_active_subscription.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435).

**آخر تشغيل مُوثَّق [2026-08-19]:** 4 passed.
