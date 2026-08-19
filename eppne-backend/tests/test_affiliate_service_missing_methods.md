# `test_affiliate_service_missing_methods.py`

## المرجع الأصلي
- `.claude/plans/affiliate-service-missing-methods-session-instructions.md` (تعليمات الجلسة).
- `.claude/reports/affiliate-service-missing-methods-session-log.md` (المرحلة 2، Backlog #10).

## السبب الجذري (كان) — ملخص
`AffiliateService` لم تكن تملك `register_commission` ولا `get_user_by_code` إطلاقًا. مستدعاتان من **12 دومين** (36 موضع استدعاء فعلي، `grep` شامل) عبر ميثود خاص `_register_affiliate_commission` مُعرَّف داخل كل دومين، كلها ملفوفة بـ`try/except Exception` صامت — الطلب الأساسي ينجح ظاهريًا (200/201) والعمولة تضيع بصمت.

**الاكتشاف الحرج اللي غيَّر التشخيص بالكامل:** جدول `Commission` الموجود (`affiliate_commissions`) مصمَّم حصريًا لعمولات مرتبطة بـOrder تجاري حقيقي (`order_id`/`order_item_id`/`product_id` كلها FK **NOT NULL**) — لكن الـ12 موضع كلها أحداث بلا أي Order (إنشاء عقدة zamakana، حجز سياحي، توظيف، اشتراك تأمين، تفاعل توأم رقمي...). `register_commission` **يستحيل تُبنى كنداء مباشر لـ`repo.create_commission`** بدون كسر صرامة الـschema التجاري. القرار المعتمَد صراحة من المستخدم: **جدول منفصل تمامًا** بدل توسيع الجدول التجاري بأعمدة nullable.

اكتشاف إضافي: كل الـ12 موضع بيمرروا `affiliate_id=user.referred_by` — وهي قيمة من نطاق `users.id`، بينما `Commission.affiliate_id` (ونفس التصميم في الجدول الجديد) FK على `affiliate_profiles.id` — التباس نطاق IDs (نفس فئة البج الموثَّقة سابقًا `tourism-place-transfer-bid-player-id-user-id-conflict`/`insurance-review-claim-issuer-entity-id-reviewer-id-conflict`).

## الإصلاح المُطبَّق

1. **Migration `028_create_affiliate_action_commissions`** — جدول جديد `affiliate_action_commissions` / موديل `ActionCommission`:
   ```python
   tenant_id, affiliate_profile_id (FK affiliate_profiles.id),
   user_id (FK users.id), amount, currency="MR_USDT", description,
   entity_type, action_type (nullable), status="PENDING",
   paid_at, paid_tx_hash, created_at, updated_at
   ```
2. **`AffiliateRepository.create_action_commission(tenant_id, **kwargs)`** — إضافة صرفة، نفس نمط `create_commission` الموجود بالضبط.
3. **`AffiliateService.register_commission(...)`**:
   ```python
   async def register_commission(
       self, affiliate_id: int, user_id: int, amount: Decimal,
       description: str, status: str = "PENDING",
       entity_type: str = "CROSS_DOMAIN", action_type: Optional[str] = None,
   ) -> ActionCommission:
       profile = await self.get_or_create_profile(affiliate_id)
       return await self.repo.create_action_commission(
           tenant_id=self.tenant_id, affiliate_profile_id=profile.id,
           user_id=user_id, amount=amount, description=description,
           status=status, entity_type=entity_type, action_type=action_type,
       )
   ```
   `get_or_create_profile(affiliate_id)` تحل التباس نطاق users.id/affiliate_profiles.id تلقائيًا — تُنشئ بروفايل لو مش موجود.
   `entity_type` افتراضيًا `"CROSS_DOMAIN"` لأن الـ12 موضع الحاليين **لا يمررونه إطلاقًا** (خارج نطاق هذه الجلسة تعديل الـ12 ملف — قرار نطاق صريح). التمييز بين الدومينات لسه متاح نصيًا فقط عبر `description`.
4. **`AffiliateService.get_user_by_code(referral_code)`** — wrapper حول `repo.get_affiliate_by_code`، يرجع `AffiliateProfile`.
5. **إصلاح ضروري ملازم**: `digital_twin/service.py:82` كان `referrer_id = referrer.id` (profile id) — صُحِّح لـ`referrer_id = referrer.user_id` لأن `register_commission.affiliate_id` مصمَّم يستقبل user_id (نفس نمط الـ11 دومين الباقيين). بدون هذا التصحيح، مسار `digital_twin`/`affiliate_code` كان سيعيد نفس باج خلط النطاق اللي هذه الجلسة مصمَّمة تحله.

## ⚠️ تنبيه صريح — هذا الإصلاح ضروري لكنه غير كافٍ لوحده

`register_commission`/`get_user_by_code` **أنفسهم يعملون بشكل صحيح ومعزول** (مؤكَّد حيًا هنا وفي الجلسة الأصلية). لكن **لم يُصلَح** استدعاء الـwrapper الفعلي (`_register_affiliate_commission`) من داخل أي من الـ12 دومين — دول لسه هيفشلوا صامتين **قبل ما يوصلوا حتى لـ`register_commission`**، بسبب ثلاث طبقات فشل سابقة، **خارج نطاق هذه الجلسة صراحة بقرار مستخدم**:

| الطبقة | الوصف | حالة التتبع |
|---|---|---|
| Backlog #1 | `UserRepository.get_by_id()` بتتنادى من 10 من الـ12 دومين بمعامل واحد بس، لكن توقيعها الحقيقي يطلب `tenant_id` إجباريًا → `TypeError` | مفتوح، جلسة منفصلة |
| Backlog #8 | دومينان (`employment`, `digital_twin`) بينادوا `user_repo.get_user()` غير الموجودة | مفتوح، جلسة منفصلة |
| اكتشاف جديد (قسم 5.3 من التقرير) | `User.referred_by` **غير موجود إطلاقًا** كحقل على موديل `User` — أي وصول له `AttributeError`، حتى بعد حل #1/#8 | مفتوح، يستاهل جلسة تصميم مستقلة (نظام الإحالة العام) |

كل هذه الطبقات مبتلَعة صامتة بنفس `except Exception` — **الفقدان الصامت الفعلي في الإنتاج لسه قائم اليوم**، رغم إصلاح هذا البند. هذا الملف **لا يختبر استدعاء الـwrapper الفعلي من أي دومين** — فقط `AffiliateService.register_commission`/`get_user_by_code` مباشرة، بمعزل عن الطبقات المعطوبة فوقها (بنفس منهجية "تجاوز الـwrapper المكسور" الموثَّقة في قسم 13 من التقرير الأصلي).

**بند Backlog إضافي وُثِّق في `PROGRESS_LOG.md`:** `affiliate-action-commissions-not-integrated-with-balance` — العمولات الجديدة تُسجَّل فعليًا الآن لكنها غير مرئية في `get_affiliate_stats`/غير قابلة للسحب عبر `withdraw_commissions` (قرار نطاق صريح — يلمس منطق سحب فلوس حقيقي، يستاهل جلسة مخصَّصة).

## إيه اللي بيتحقق منه هذا الملف

6 اختبارات — بمنهجية "تحقق مستقل" (SELECT من نفس الجلسة بعد commit، مش مجرد صفر استثناء):

| # | الاختبار | ما بيثبته |
|---|---|---|
| 1 | `test_register_commission_default_call_pattern_matches_real_call_sites` | نفس التوقيع الحرفي المستخدَم في كل الـ12 موضع فعليًا (بلا `entity_type`/`action_type`) — يتسجَّل بـ`entity_type="CROSS_DOMAIN"` و`action_type=None` افتراضيًا |
| 2 | `test_register_commission_percentage_pattern_with_explicit_entity_type` | نمط نسبة مئوية (محاكاة `transport`: 2%) مع `entity_type`/`action_type` صريحين |
| 3 | `test_register_commission_flat_amount_pattern` | نمط مبلغ ثابت (محاكاة `tenders_auctions`: 25.00 لـ`AUCTION_WON`) |
| 4 | `test_get_user_by_code_valid_and_invalid` | كود صحيح → `AffiliateProfile` صحيح؛ كود غير موجود → `None` |
| 5 | `test_digital_twin_affiliate_code_pattern_end_to_end` | المسار الكامل الخاص بـ`digital_twin`: `get_or_create_profile` → كود → `get_user_by_code(code)` → `.user_id` → `register_commission` — يثبت التصحيح المطبَّق فعليًا في `digital_twin/service.py:82` (لو اتمرر `referrer.id` غلط بدل `referrer.user_id`، `affiliate_profile_id` الناتج كان هيختلف عن بروفايل المُحيل الحقيقي) |
| 6 | `test_register_commission_reuses_same_profile_across_separate_sessions` | **حالة حافة مطلوبة صراحة**: نفس `affiliate_id` عبر **جلستين DB مستقلتين تمامًا** (`AsyncSessionLocal()` منفصلة، مش نفس session) — يثبت `get_or_create_profile` idempotent حقيقيًا (محاكاة طلبين HTTP منفصلين لنفس المُحيل)، مش بس داخل نفس session زي التحقق الحي الأصلي في التقرير |

## بيانات throwaway
- مستخدمان جديدان لكل اختبار (`UserService.register`، بادئة `p10_*` + `uuid4` فريد) — صفر إعادة استخدام بيانات من جلسات سابقة.
- تنظيف كامل في `finally`: `ActionCommission` → `AffiliateProfile` → `User` (بالترتيب الصحيح لتفادي FK)، مع `commit()`.
- تحقق مستقل بعد تشغيلتين متتاليتين: `SELECT count(*) FROM users WHERE username LIKE 'p10_%'` و`SELECT count(*) FROM affiliate_action_commissions WHERE description LIKE ...` كلاهما `0`.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_affiliate_service_missing_methods.py -v
```
يحتاج قاعدة `eppne_v2` حقيقية شغّالة (Docker `eppne_db`، منفذ 5435) بعد تطبيق migration `028_create_affiliate_action_commissions` (`PYTHONIOENCODING=utf-8 ./venv/Scripts/alembic.exe upgrade head`).

**آخر تشغيل مُوثَّق [2026-08-19]:** 6 passed (تشغيلتان متتاليتان، صفر تذبذب). تحقق مستقل إضافي بعد التشغيلتين أكَّد **صفر بيانات throwaway متبقية**.
