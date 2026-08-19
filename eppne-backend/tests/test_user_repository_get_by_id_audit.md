# `test_user_repository_get_by_id_audit.py`

## المرجع الأصلي
- `.claude/plans/user-repository-get-by-id-audit-session-instructions.md` (تعليمات الجلسة).
- `.claude/reports/user-repository-get-by-id-audit-session-log.md` (التقرير الكامل، Backlog #1).

## السبب الجذري (كان)
`UserRepository.get_by_id(user_id, tenant_id, load_wallet=False)` (`app/domains/identity/repository.py:21`) توقيعها الحقيقي يطلب `tenant_id` **إجباريًا** كمعامل موضعي ثانٍ. `grep` شامل جديد بالكامل (بلا اعتماد على أي قايمة تاريخية كمرجع نهائي) كشف **15 موضعًا فعليًا** عبر **13 دومين** بينادوها بمعامل واحد بس (`user_id`) → `TypeError: missing 1 required positional argument: 'tenant_id'` فورية، قبل حتى تنفيذ أي استعلام.

## الإصلاح المُطبَّق
تمرير `tenant_id` الفعلي (متاح أصلًا في نطاق كل دالة — إما كمعامل مباشر، أو مُشتق من صف محمَّل زي `pension.tenant_id`) كمعامل ثانٍ لكل استدعاء. أي دالة مساعدة خاصة (`_get_user_by_id`/`_get_user_email`/`_get_user`/`_get_land_owner_for_unit`) ما كانتش بتقبل `tenant_id` إطلاقًا — تم تعديل توقيعها لتقبله كمعامل إجباري. **صفر تغيير** في منطق معالجة الأخطاء الموجود (`try/except`/`begin_nested()`/سلوك الدوال الأصلي) — الإصلاح يقتصر على تصحيح المعامل الناقص فقط.

## القايمة الكاملة الـ15 وحالة كل موضع

| # | الملف:السطر | الآلية | tenant_id (قبل) | tenant_id (بعد) |
|---|---|---|---|---|
| 1 | `zamakana/service.py:650` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 2 | `transport/service.py:569` | `_get_user_by_id` (كسر واضح 500، مُصلَح) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 3 | `transport/service.py:577` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 4 | `tourism_sports/service.py:518` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 5 | `tenders_auctions/service.py:484` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 6 | `social/service.py:678` | `_get_user_email` (كسر واضح 500 داخل `begin_nested()`، مُصلَح) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 7 | `service_marketplace/service.py:476` | `_get_user` (عبر `_register_affiliate_commission`) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 8 | `realestate/service.py:576` | `_get_land_owner_for_unit` (كسر واضح 500، مُصلَح) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 9 | `realestate/service.py:584` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 10 | `arbitration_syndicates/service.py:564` | `_register_affiliate_commission` | ناقص | من معامل الدالة |
| 11 | `manufacturing/service.py:57` | `_get_user` (عبر `_register_affiliate_commission`) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 12 | `logistics/service.py:62` | `_get_user`/`_get_user_email` | ناقص | **بلا لمس — Dead code، صفر مستدعٍ حي، توثيق فقط** |
| 13 | `iot/service.py:31` | `_get_user_email` (كان يتحوَّل لـ`BusinessError`، مُصلَح) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 14 | `invitations/service.py:56` | `_get_user` (عبر `_register_affiliate_commission`) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع |
| 15 | `insurance/service.py:60` | `_get_user`/`_get_user_email` — **3 مسارات استدعاء** (`:68` صامت مُسجَّل، `:464` كسر واضح 500 كان يكراش `review_claim`، `:554` **صمت كامل بلا أي تسجيل** في `disburse_monthly_pensions`) | ناقص، توقيع لا يقبله | معامل جديد بالتوقيع، يغطي الـ3 مسارات بتعديل واحد |

## ⚠️ اكتشاف جانبي حي أثناء التحقق — سلسلة `affiliate`/Backlog #10 (توثيق فقط، خارج نطاق هذه الجلسة صراحة)

كل مواضع `_register_affiliate_commission` (9 دومينات في هذا الملف + `insurance` = **10 دومينات**) بتوصل الآن بنجاح لـ`get_by_id` وتجيب المستخدم الصحيح تمامًا (Backlog #1 مُصلَح ومؤكَّد حيًا لكل واحد منهم)، لكنها فورًا بعدها بتصطدم بطبقة الفشل التالية الموثَّقة مسبقًا في قسم 5.3 من جلسة `affiliate-service-missing-methods`: **`User.referred_by` غير موجود إطلاقًا كحقل على الموديل** (تحقُّق مباشر من `app/domains/identity/models.py` — صفر نتائج) → `AttributeError` (مُبتلَعة بنفس `try/except` الموجود أصلًا، صمت مُسجَّل بـ`logger.error`).

**الاختبارات هنا تتوقع وتتسامح مع** هذا الـ`AttributeError` تحديدًا (`assert any("referred_by" in r ...)`— يثبت إن `get_by_id` نجح فعلًا ووصلنا لمنطق `referred_by`)، بينما **ترفض بشكل قاطع** أي إشارة لـ`TypeError`/`missing`/`positional argument` (كان سيثبت رجوع Backlog #1 نفسه). صفر إصلاح لـ`referred_by` هنا — خارج النطاق صراحة، بند Backlog منفصل مستقل (نظام الإحالة العام).

`digital_twin` و`employment` خارج هذا التوثيق تمامًا — لسه محجوزان عند طبقة أسبق (Backlog #8، `get_user()` غير موجودة إطلاقًا)، ولم يصلوا لـ`get_by_id` من الأساس لا قبل ولا بعد هذا الإصلاح.

## أثر جانبي على اختبار موجود مسبقًا (مُعالَج في نفس الجلسة)

`tests/test_saas_active_subscription.py::test_insurance_review_claim_saas_check_passes_then_hits_known_bug` كان بيعتمد صراحة على `pytest.raises(TypeError, match="tenant_id")` كدليل غير مباشر على الوصول لـ`insurance/service.py:464`. بعد إصلاح #1 هنا، هذا التوقُّع بقى باطل (الكود بيعدي `get_by_id` بنجاح تام) — **تم تحديث الاختبار في نفس الجلسة** ليعتمد على الطبقة التالية الحقيقية المؤكَّدة حيًا (`insurance-review-claim-issuer-entity-id-reviewer-id-conflict` → `PermissionDeniedError("Not authorized to review this claim")`)، بدل ما يُترَك outdated. راجع docstring الاختبار المُحدَّث هناك للتفاصيل الكاملة. تشغيلتان متتاليتان لملف `test_saas_active_subscription.py` كامل بعد التحديث: **4 passed** في الاثنتين.

## إيه اللي بيتحقق منه هذا الملف

**15 اختبارًا — واحد لكل موضع من الـ15** (نفس منهجية التحقق الحي الأصلية، القسم 12.2 من التقرير): استدعاء حقيقي بجلسة DB حقيقية يصل فعليًا لنفس السطر المُصلَح، **بمعاملين صحيحين** (`user_id`, `tenant_id` صحيحين) **و**بـ`tenant_id` خاطئ (`999999`) للتأكد من **عزل tenant فعليًا** — مش بس اختفاء الخطأ:

| # | الاختبار | ما بيثبته |
|---|---|---|
| 1 | `test_zamakana_register_affiliate_commission_get_by_id_fixed` | tenant صحيح → يصل لـ`referred_by` (يثبت `get_by_id` نجح)؛ tenant خاطئ → صمت تام بلا أي خطأ |
| 2 | `test_transport_get_user_by_id_correct_and_wrong_tenant` | tenant صحيح → `User` صحيح؛ tenant خاطئ → `NotFoundError` صريحة (سلوك أصلي محفوظ) |
| 3 | `test_transport_register_affiliate_commission_get_by_id_fixed` | نفس نمط #1، موضع منفصل في نفس الملف |
| 4 | `test_tourism_sports_register_affiliate_commission_get_by_id_fixed` | نفس نمط #1 |
| 5 | `test_tenders_auctions_register_affiliate_commission_get_by_id_fixed` | نفس نمط #1 |
| 6 | `test_social_get_user_email_correct_and_wrong_tenant` | tenant صحيح → إيميل حقيقي؛ tenant خاطئ → fallback نصي (سلوك أصلي محفوظ) |
| 7 | `test_service_marketplace_get_user_correct_and_wrong_tenant` | `_get_user` مباشرة + `_register_affiliate_commission` الكاملة |
| 8 | `test_realestate_land_owner_get_by_id_correct_and_wrong_tenant` | توقيع `_get_land_owner_for_unit` يقبل `tenant_id` + نفس استدعاء `user_repo.get_by_id` الحرفي |
| 9 | `test_realestate_register_affiliate_commission_get_by_id_fixed` | نفس نمط #1، موضع منفصل |
| 10 | `test_arbitration_syndicates_register_affiliate_commission_get_by_id_fixed` | نفس نمط #1 |
| 11 | `test_manufacturing_get_user_correct_and_wrong_tenant` | `_get_user` مباشرة + `_register_affiliate_commission` الكاملة |
| 12 | `test_logistics_get_user_left_untouched_as_documented_dead_code` | **يوثِّق ويقفل** الحالة الحالية (توقيع بمعامل واحد) عمدًا — يفشل تحذيريًا لو حد غيَّرها مستقبلًا بلا مراجعة السياق |
| 13 | `test_iot_get_user_email_correct_and_wrong_tenant` | نفس نمط #6 |
| 14 | `test_invitations_get_user_correct_and_wrong_tenant` | نفس نمط #11 |
| 15 | `test_insurance_get_user_and_get_user_email_all_three_call_paths` | تأكيد نصي إن الـ3 نقاط استدعاء (`:68`, `:464`, `:554`) بتمرر `tenant_id` فعليًا + تحقق حي على مستوى `_get_user`/`_get_user_email` |

## بيانات throwaway
- مستخدم واحد جديد لكل اختبار (`UserService.register`، بادئة `p1audit_*` + `uuid4` فريد) — صفر إعادة استخدام بيانات من جلسات سابقة.
- تنظيف كامل في `finally`: `delete(User)` + `commit()`.
- تحقق مستقل بعد تشغيلتين متتاليتين: `SELECT count(*) FROM users WHERE username LIKE 'p1audit\_%'` = **0**.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_user_repository_get_by_id_audit.py -v
```
يحتاج قاعدة `eppne_v2` حقيقية شغّالة (Docker `eppne_db`، منفذ 5435).

**آخر تشغيل مُوثَّق [2026-08-19]:** 15 passed (تشغيلتان متتاليتان، صفر تذبذب). تحقق مستقل إضافي بعد التشغيلتين أكَّد **صفر بيانات throwaway متبقية**. تشغيل شامل لكل `tests/` بعد هذه الجلسة: **60 passed, 4 xfailed** — صفر تأثير جانبي غير مُعالَج غير الموضَّح أعلاه (`test_saas_active_subscription.py`، مُحدَّث بالفعل).
