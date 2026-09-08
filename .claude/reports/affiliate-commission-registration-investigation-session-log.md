# تقرير جلسة — تحقيق: هل `_register_affiliate_commission` بتفشل فعليًا، ولا الاختبار بيفترض سلوك قديم؟

**تاريخ الجلسة:** 2026-09-07
**النطاق (حرفيًا):** فحص read-only بحت — **صفر تعديل كود**. الهدف: تحديد
هل `_register_affiliate_commission` بتفشل فعليًا وقت التنفيذ الحي، ولا
الاختبار بيفترض سلوك قديم. البند موضوع التحقيق:
`backlog-affiliate-commission-registration-systemwide-broken` (أولوية
عالية)، مذكور في `PROGRESS_LOG.md` (السطور ~2185-2212 وقت كتابة هذا
التقرير).

**الخلاصة المباشرة (TL;DR):** **الكود مش بيفشل — الاختبار هو اللي بيفترض
سلوك قديم انتهى فعليًا.** الاختبارات كتبتها جلسة سابقة (commit `33f5b71`،
2026-08-19) لما `User.referred_by` كان عمود غير موجود إطلاقًا، فكانت
الاختبارات مصممة عمدًا تتسامح مع `AttributeError` كدليل نجاح
(`get_by_id` وصل، بس بعدها اصطدم بعمود مفقود). جه commit `2960d9d`
(2026-09-07، 00:30) وأضاف العمود الحقيقي `User.referred_by_user_id`،
وعدَّل كل مواضع `_register_affiliate_commission` تستخدمه. النتيجة: الدالة
دلوقتي **بتنجح فعليًا وبصمت** لأي مستخدم اختبار جديد (لسه معندهوش محيل،
`referred_by_user_id IS NULL`) — يعني بترجع من غير أي log وبلا أي
استثناء، وده يكسر افتراض الاختبار القديم اللي كان بيتوقع رسالة فيها كلمة
`referred_by` (سواء نجاح أو AttributeError) كدليل تنفيذ. الاختبار بيفشل
بـ`AssertionError` بسيطة (`assert any(...)` على قائمة فاضية)، **مش**
بـ`TypeError`/`missing`/`positional argument` (اللي كان سيثبت رجوع
Backlog #1 الأصلي فعلًا).

**بند مستقل تمامًا اتكشف أثناء التحقيق:** واحد من الـ11 فشل
(`test_social_get_user_email_correct_and_wrong_tenant`) **مش له علاقة
بـ`_register_affiliate_commission` ولا بـcommit `2960d9d` إطلاقًا** —
تفصيل في القسم 5.

---

## 1. كود `_register_affiliate_commission` كامل — المسار + المحتوى الحرفي

الدالة **مش دالة واحدة مشتركة** — منسوخة (duplicated) بنفس الاسم عبر
10 ملفات دومين مختلفة (كلها بتفشل في الاختبار الحي، القسم 4). كل نسخة
منسوخة أدناه **حرفيًا كما هي في الكود الحالي**، بلا أي تلخيص أو تصرف.

### 1.1 `eppne-backend/app/domains/zamakana/service.py:645-663`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = Decimal("2.00") if action_type in ["NODE_CREATED", "CAMPAIGN_CREATED"] else Decimal("1.00")
                scope_id = await affiliate_service.resolve_scope_id_for_member("ZAMAKANA")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="ZAMAKANA",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.2 `eppne-backend/app/domains/transport/service.py:855-871`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self.user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = amount * Decimal("0.02")
                scope_id = await affiliate_service.resolve_scope_id_for_member("TRANSPORT")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="TRANSPORT",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.3 `eppne-backend/app/domains/tourism_sports/service.py:569-593`

```python
    async def _register_affiliate_commission(
        self,
        user_id: int,
        tenant_id: int,
        action_type: str,
        amount: Decimal
    ):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = amount * Decimal("0.05")
                scope_id = await affiliate_service.resolve_scope_id_for_member("TOURISM_SPORTS")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="TOURISM_SPORTS",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.4 `eppne-backend/app/domains/tenders_auctions/service.py:560-577`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = Decimal("5.00") if action_type == "TENDER_CREATED" else Decimal("25.00")
                scope_id = await affiliate_service.resolve_scope_id_for_member("TENDERS_AUCTIONS")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="TENDERS_AUCTIONS",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.5 `eppne-backend/app/domains/service_marketplace/service.py:489-506`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal, description: str):
        """تسجيل عمولة إحالة (10% من قيمة الشراء)."""
        try:
            affiliate_service = AffiliateService(self.db, tenant_id)
            user = await self._get_user(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission_amount = amount * Decimal("0.10")
                if commission_amount > 0:
                    scope_id = await affiliate_service.resolve_scope_id_for_member("SERVICE_MARKETPLACE")
                    if scope_id:
                        await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                        await affiliate_service.distribute_commissions_for_sale_event(
                            referred_user_id=user_id,
                            scope_id=scope_id,
                            sale_amount=commission_amount,
                            source_type="SERVICE_MARKETPLACE",
                        )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.6 `eppne-backend/app/domains/realestate/service.py:697-713`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        try:
            affiliate = AffiliateService(self.db, tenant_id)
            user = await self.user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = amount * Decimal("0.02")
                scope_id = await affiliate.resolve_scope_id_for_member("REALESTATE")
                if scope_id:
                    await affiliate.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="REALESTATE",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.7 `eppne-backend/app/domains/arbitration_syndicates/service.py:556-573`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = Decimal("5.00") if action_type == "ARBITRATION_CASE_CREATED" else Decimal("2.00")
                scope_id = await affiliate_service.resolve_scope_id_for_member("ARBITRATION_SYNDICATES")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="ARBITRATION_SYNDICATES",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.8 `eppne-backend/app/domains/manufacturing/service.py:62-78`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id, tenant_id)
            if user and user.referred_by_user_id:  # type: ignore
                commission = Decimal("10.00") if action_type == "FACILITY_CREATED" else Decimal("5.00")
                scope_id = await affiliate_service.resolve_scope_id_for_member("MANUFACTURING")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)  # type: ignore
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="MANUFACTURING",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.9 `eppne-backend/app/domains/invitations/service.py:65-81`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id, tenant_id)
            if user and user.referred_by_user_id:  # type: ignore
                commission = Decimal("2.00") if action_type in ["INVITATION_CREATED", "CAMPAIGN_CREATED"] else Decimal("5.00")
                scope_id = await affiliate_service.resolve_scope_id_for_member("INVITATIONS")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)  # type: ignore
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="INVITATIONS",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

### 1.10 `eppne-backend/app/domains/insurance/service.py:87-103`

```python
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str, amount: Decimal):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id, tenant_id)
            if user and user.referred_by_user_id:  # type: ignore
                commission = amount * Decimal("0.02")
                scope_id = await affiliate_service.resolve_scope_id_for_member("INSURANCE")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)  # type: ignore
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="INSURANCE",
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")
```

**ملاحظة مهمة:** `social/service.py` **لا يحتوي على `_register_affiliate_commission`
إطلاقًا** رغم إن اسمه مذكور ضمن قائمة الـ11 دومين في `PROGRESS_LOG.md` —
تفصيل كامل في القسم 5. كذلك `digital_twin`/`employment` عندهم الدالة
دي فعليًا لكنهم **محجوزون عمدًا خارج هذا الـbacklog** (Backlog #8 منفصل،
`_get_user`/`get_user()` غير موجودة — موثَّق في docstring الاختبار
سطر 56-57).

**النمط المشترك عبر كل الـ10 نسخة:** الشرط `if user and user.referred_by_user_id:`
هو نقطة التحكم الوحيدة. لو `referred_by_user_id` قيمته `None` (الحالة
الطبيعية لأي مستخدم اتسجل بلا كود إحالة، بما فيهم كل مستخدمي هذا
الاختبار)، الدالة **بترجع فورًا من غير أي عملية، وبلا أي `log`، وبلا أي
استثناء** — الجسم الداخلي (حساب العمولة، `resolve_scope_id_for_member`،
`ensure_referral_link`، `distribute_commissions_for_sale_event`) **لا
يُنفَّذ إطلاقًا** في هذه الحالة.

---

## 2. الاختبار اللي بيفشل — الجزء اللي بيفحص العمولة حرفيًا

**الملف:** `eppne-backend/tests/test_user_repository_get_by_id_audit.py`
(573 سطر، أنشأه commit `33f5b71` بتاريخ **2026-08-19** — أي **قبل**
commit `2960d9d` بـ19 يوم).

### 2.1 الـhelper المشترك (سطور 102-117)

```python
class _LogCapture(logging.Handler):
    """يلتقط سجلات logger 'eppne' أثناء الاختبار — نفس الأسلوب المُستخدَم
    في التحقق الحي الأصلي (قسم 12.2) لإثبات غياب TypeError دون الاعتماد
    على استثناء يوصل خارج try/except الموجود أصلاً في _register_affiliate_commission."""

    def __init__(self):
        super().__init__()
        self.records: List[str] = []

    def emit(self, record):
        self.records.append(record.getMessage())


def _assert_no_typeerror_leak(records: List[str]):
    bad = [r for r in records if any(x in r.lower() for x in ("missing", "positional argument", "typeerror"))]
    assert not bad, f"رجوع TypeError الخاص بـBacklog #1: {bad}"
```

### 2.2 مثال نموذجي كامل — `zamakana` (سطور 124-151)، الشكل مطابق حرفيًا في الـ9 اختبارات الباقية

```python
@pytest.mark.asyncio
async def test_zamakana_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #1 — zamakana/service.py:650 داخل _register_affiliate_commission.
    tenant_id صحيح → get_by_id ينجح ويوصل لطبقة referred_by (AttributeError
    متسامَح بها، خارج نطاق #1). tenant_id خاطئ → get_by_id يرجع None، صفر
    أي خطأ إطلاقًا (لا TypeError ولا AttributeError)."""
    from app.domains.zamakana.service import ZamakanaService

    user = await _create_user(db, "p1audit_zamakana")
    user_ids = [user.id]
    try:
        svc = ZamakanaService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TEST_ACTION")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records), (
                "المتوقع: وصلنا لطبقة referred_by المفقودة (يثبت get_by_id نجح)"
            )

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "TEST_ACTION")
            assert cap.records == [], f"tenant خاطئ لازم يرجع None بصمت تام، لا أخطاء: {cap.records}"
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)
```

**نقطة الفشل بالضبط:** السطر
`assert any("referred_by" in r for r in cap.records), (...)`. الاختبار
بيتوقع **صراحة** إن `cap.records` (اللي التقطت أي `logger.error(...)`
اتنفذ) تحتوي على رسالة فيها substring `"referred_by"` — سواء نجاح كامل
(لو كان فيه log نجاح) أو رسالة الـ`AttributeError` القديمة
(`'User' object has no attribute 'referred_by'`، اللي كانت بتظهر لما
العمود مكانش موجود أصلًا). **الاختبار لا يفرّق بين الاثنين** — أي رسالة
فيها الكلمة كافية لإثبات "وصلنا لمنطق referred_by".

### 2.3 docstring الملف نفسه — دليل صريح إن هذا كان سلوك متوقَّع ومقصود وقتها (سطور 46-57)

```
**⚠️ اكتشاف جانبي حي أثناء التحقق (القسم 13 من التقرير، خارج نطاق هذه
الجلسة صراحة — توثيق فقط، بلا إصلاح):** كل مواضع `_register_affiliate_commission`
(9 دومينات + insurance = 10) بتوصل الآن بنجاح لـ`get_by_id` وتجيب
المستخدم الصحيح، لكن فورًا بعدها بتصطدم بطبقة الفشل التالية الموثَّقة
مسبقًا في جلسة `affiliate-service-missing-methods` (قسم 5.3): **`User.referred_by`
غير موجود إطلاقًا كحقل على الموديل** → `AttributeError` (مُبتلَعة بنفس
`try/except` الموجود، صمت مُسجَّل). الاختبارات هنا **تتوقع وتتسامح مع**
هذا الـ`AttributeError` تحديدًا (يثبت إن `get_by_id` نجح ووصلنا لمنطق
`referred_by`) بينما **ترفض بشكل قاطع** أي إشارة لـ`TypeError`/
`missing`/`positional argument` (كان سيثبت رجوع Backlog #1 نفسه).
```

هذا يؤكد: الاختبار **صُمِّم عمدًا** حوالين واقع "`referred_by` كحقل
غير موجود" — مش خطأ كتابة، بل قرار توثيقي واعٍ وقتها. المشكلة إن الواقع
ده **اتغيَّر جوهريًا** بعد 19 يوم (commit `2960d9d`)، والاختبار لم
يُحدَّث معاه.

---

## 3. المقارنة: هل commit `2960d9d` غيَّر شكل الرسالة، ولا الكود بقى مش بيسجّل العمولة؟

**الإجابة المؤكَّدة حيًا (القسم 4): لا الاثنين بالضبط.** التفصيل:

- **الكود لسه بيحاول يسجّل العمولة فعليًا** — الجسم الداخلي (حساب
  `commission`، `resolve_scope_id_for_member`, `ensure_referral_link`,
  `distribute_commissions_for_sale_event`) **لم يُحذَف ولا يُعطَّل** —
  هو موجود وسليم داخل الشرط `if user and user.referred_by_user_id:`.
- **لكن الشرط نفسه بقى حقيقي وفعّال** بدل ما يكسر بـ`AttributeError`
  زي الأول. `commit 2960d9d` أضاف عمود `User.referred_by_user_id` فعليًا
  (migration 045) وعدَّل كل الدومينات تستخدم الاسم الجديد الصحيح
  (بدل `user.referred_by` القديم اللي مكانش موجود أصلًا كعمود).
- **لأي مستخدم اختبار جديد** (زي كل مستخدمي هذا الاختبار — `UserService.register`
  بلا أي كود إحالة) — `referred_by_user_id` قيمته `None` بشكل طبيعي
  وصحيح (معندوش حد أحاله). الشرط `if user and user.referred_by_user_id:`
  بيبقى `False`، فالدالة **بترجع فورًا بلا أي عملية، وبلا أي `log`
  إطلاقًا (لا نجاح ولا فشل)** — سلوك **صحيح ومتوقَّع منطقيًا** (مفيش
  محيل يستحق عمولة)، لكنه **مختلف تمامًا** عن افتراض الاختبار (اللي كان
  متبني على وجود *أي* رسالة فيها `referred_by`).
- **النتيجة:** مفيش رسالة إطلاقًا (لا نجاح، لا خطأ) → `cap.records`
  فاضية → `assert any("referred_by" in r for r in cap.records)` بيفشل
  بـ`AssertionError` بسيطة، **مش** `TypeError`/`AttributeError`.
  هذا **تأكيد مباشر إن الكود بيشتغل صح** (مفيش استثناء اتبلع، مفيش
  regression فعلي) — **الاختبار هو اللي اتقدَّم عليه الزمن**.

**تصحيح دقيق لصياغة الطلب:** العنوان "هل غيَّر شكل الـlog/الرسالة" مش
دقيق 100% — الأدق: **الكود قبل التوحيد كان بيولِّد رسالة (AttributeError
مُسجَّلة) لكل استدعاء ناجح لـ`get_by_id`، وبعد التوحيد بقى مش بيولِّد أي
رسالة إطلاقًا في الحالة الطبيعية (بدون محيل)** — الفرق مش "تغيير شكل
رسالة"، بل "وجود رسالة أصلًا".

---

## 4. الإثبات الحي — نتيجة تشغيل فعلي لملف الاختبار كاملًا

**البيئة:** `E:\cc\eppne-backend\venv` (Python 3.12.10، pytest 8.3.4).
**الأمر:** `python -m pytest tests/test_user_repository_get_by_id_audit.py -v --tb=short`

**النتيجة الكاملة: `11 failed, 4 passed`** (مطابق تمامًا لعدد الـ11 دومين
المذكور في بند الـbacklog).

```
tests/test_user_repository_get_by_id_audit.py::test_zamakana_register_affiliate_commission_get_by_id_fixed FAILED [  6%]
tests/test_user_repository_get_by_id_audit.py::test_transport_get_user_by_id_correct_and_wrong_tenant PASSED [ 13%]
tests/test_user_repository_get_by_id_audit.py::test_transport_register_affiliate_commission_get_by_id_fixed FAILED [ 20%]
tests/test_user_repository_get_by_id_audit.py::test_tourism_sports_register_affiliate_commission_get_by_id_fixed FAILED [ 26%]
tests/test_user_repository_get_by_id_audit.py::test_tenders_auctions_register_affiliate_commission_get_by_id_fixed FAILED [ 33%]
tests/test_user_repository_get_by_id_audit.py::test_social_get_user_email_correct_and_wrong_tenant FAILED [ 40%]
tests/test_user_repository_get_by_id_audit.py::test_service_marketplace_get_user_correct_and_wrong_tenant FAILED [ 46%]
tests/test_user_repository_get_by_id_audit.py::test_realestate_land_owner_get_by_id_correct_and_wrong_tenant PASSED [ 53%]
tests/test_user_repository_get_by_id_audit.py::test_realestate_register_affiliate_commission_get_by_id_fixed FAILED [ 60%]
tests/test_user_repository_get_by_id_audit.py::test_arbitration_syndicates_register_affiliate_commission_get_by_id_fixed FAILED [ 66%]
tests/test_user_repository_get_by_id_audit.py::test_manufacturing_get_user_correct_and_wrong_tenant FAILED [ 73%]
tests/test_user_repository_get_by_id_audit.py::test_logistics_get_user_left_untouched_as_documented_dead_code PASSED [ 80%]
tests/test_user_repository_get_by_id_audit.py::test_iot_get_user_email_correct_and_wrong_tenant PASSED [ 86%]
tests/test_user_repository_get_by_id_audit.py::test_invitations_get_user_correct_and_wrong_tenant FAILED [ 93%]
tests/test_user_repository_get_by_id_audit.py::test_insurance_get_user_and_get_user_email_all_three_call_paths FAILED [100%]
```

**الـtraceback الفعلي لكل الـ10 فشل المتعلقين بالعمولة (نمط مطابق حرفيًا
في كل واحد منهم، مثال `zamakana`):**

```
_________ test_zamakana_register_affiliate_commission_get_by_id_fixed _________
tests\test_user_repository_get_by_id_audit.py:141: in test_zamakana_register_affiliate_commission_get_by_id_fixed
    assert any("referred_by" in r for r in cap.records), (
E   AssertionError: المتوقع: وصلنا لطبقة referred_by المفقودة (يثبت get_by_id نجح)
E   assert False
E    +  where False = any(<generator object test_zamakana_register_affiliate_commission_get_by_id_fixed.<locals>.<genexpr> at 0x00000191BF37FE00>)
```

نفس الشكل بالظبط (`assert False` على `any(...)` فاضية، بلا أي `TypeError`
أو `AttributeError` في الرسالة) تكرر حرفيًا في: `transport`,
`tourism_sports`, `tenders_auctions`, `service_marketplace`, `realestate`,
`arbitration_syndicates`, `manufacturing`, `invitations`, `insurance`
(9 دومينات إضافية = 10 إجمالًا).

**لا فشل واحد من العشرة يحتوي على `TypeError`/`missing`/`positional argument`
في أي مكان بالـtraceback أو الرسالة** — أي **صفر دليل على regression
حقيقي في مسار التنفيذ نفسه**. `_assert_no_typeerror_leak(cap.records)`
نجحت في كل الحالات العشر (سطر التنفيذ فعليًا قبل سطر الفشل في كل
اختبار) — دليل إضافي إن الكود نفَّذ من غير أي استثناء يتبلع بشكل غير
متوقَّع.

---

## 5. اكتشاف جانبي: الفشل الـ11 (`social`) غير مرتبط بهذا التحقيق إطلاقًا

الفشل الوحيد المختلف شكلًا بين الـ11:

```
_____________ test_social_get_user_email_correct_and_wrong_tenant _____________
tests\test_user_repository_get_by_id_audit.py:281: in test_social_get_user_email_correct_and_wrong_tenant
    fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
app\domains\social\service.py:723: in _get_user_email
    raise NotFoundError("Receiver not found in your tenant")
E   app.core.errors.NotFoundError: Receiver not found in your tenant
```

**كود `_get_user_email` الحالي في `social/service.py:718-724` (حرفيًا):**

```python
    async def _get_user_email(self, user_id: int, tenant_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise NotFoundError("Receiver not found in your tenant")
        return cast(str, user.email)
```

الاختبار (سطر 267-282) كان بيتوقع إن `tenant_id` خاطئ يرجّع **fallback
نصي** (`f"user_{user.id}@eppne.com"`) بدل استثناء — لكن الكود الفعلي
بيرمي `NotFoundError` صراحةً بدل أي fallback.

**السبب الجذري مختلف تمامًا، وغير مرتبط بـcommit `2960d9d`:**

1. `social/service.py` **مش موجود إطلاقًا** في قائمة الـ35 ملف اللي غيّرها
   commit `2960d9d` (تأكَّد بـ`git show --stat 2960d9d`) — الملف ده لم
   يُلمَس في جلسة التوحيد بالمرة.
2. `_register_affiliate_commission` **غير موجودة أصلًا** في
   `social/service.py` (تأكَّد بـ`grep` — القسم 1 أعلاه) — رغم إن
   `social` مذكور ضمن قائمة الـ11 دومين في بند الـbacklog بـ`PROGRESS_LOG.md`
   على إنه نفس نمط الفشل. **هذا خطأ تصنيف في نص البند نفسه** — فشل
   `social` سببه دالة تانية خالص (`_get_user_email`) بمنطق مختلف تمامًا
   (استثناء صريح بدل fallback)، مش نفس نمط `referred_by`/العمولة.
3. آخر تعديل حقيقي على `social/service.py` (`git log --follow`) هو
   commit `5003196` — "fix(social): repair fully-broken domain (100%
   endpoints 500) + close real IDOR gaps" — سابق لكتابة اختبار
   `user-repository-get-by-id-audit` نفسه أصلًا على الأرجح، ما يستبعد
   أي علاقة بمسار الـaffiliate/referral الحالي كمان.

**الخلاصة لهذا البند الفرعي:** فشل `social` هو **باج ثالث منفصل تمامًا**
(اختلاف افتراض قديم عن سلوك `_get_user_email` الفعلي) — لا علاقة له
بـ`_register_affiliate_commission` ولا بـcommit `2960d9d`. يحتاج قرار
تصميمي منفصل (هل `_get_user_email` في `social` المفروض يرمي استثناء ولا
يرجّع fallback؟) خارج نطاق هذا التحقيق تمامًا.

---

## 6. `git show 2960d9d` — الفرق بالظبط (نموذج تمثيلي: `zamakana` + `identity/models.py`)

### 6.1 `eppne-backend/app/domains/identity/models.py` — إضافة العمود نفسه

```diff
--- a/eppne-backend/app/domains/identity/models.py
+++ b/eppne-backend/app/domains/identity/models.py
@@ -62,6 +62,11 @@ class User(Base):
     is_system_account = Column(Boolean, default=False, nullable=False, server_default="false")
     session_version = Column(Integer, default=1)
 
+    # مصدر "من أحال من" الموحَّد (migration 045) — يُملأ فقط وقت
+    # POST /identity/register، immutable بعد ذلك على مستوى التطبيق
+    # (لا قيد DB يمنع UPDATE — نفس نمط created_at في هذا المشروع).
+    referred_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
+
     last_login_at = Column(DateTime(timezone=True), nullable=True)
     last_login_ip = Column(String(45), nullable=True)
     last_login_user_agent = Column(String(255), nullable=True)
```

### 6.2 `eppne-backend/app/domains/zamakana/service.py` — التغيير الفعلي في منطق العمولة (نمط مطابق في الـ9 دومينات الباقية بنفس الفلسفة، تفاصيل الأسماء/المبالغ تختلف فقط)

```diff
--- a/eppne-backend/app/domains/zamakana/service.py
+++ b/eppne-backend/app/domains/zamakana/service.py
@@ -648,14 +648,16 @@ class ZamakanaService:
             from app.domains.identity.repository import UserRepository
             user_repo = UserRepository(self.db)
             user = await user_repo.get_by_id(user_id, tenant_id)
-            if user and user.referred_by:
+            if user and user.referred_by_user_id:
                 commission = Decimal("2.00") if action_type in ["NODE_CREATED", "CAMPAIGN_CREATED"] else Decimal("1.00")
-                await affiliate_service.register_commission(  # type: ignore[attr-defined]
-                    affiliate_id=user.referred_by,
-                    user_id=user_id,
-                    amount=commission,
-                    description=f"Affiliate commission for {action_type}",
-                    status="PENDING"
-                )
+                scope_id = await affiliate_service.resolve_scope_id_for_member("ZAMAKANA")
+                if scope_id:
+                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
+                    await affiliate_service.distribute_commissions_for_sale_event(
+                        referred_user_id=user_id,
+                        scope_id=scope_id,
+                        sale_amount=commission,
+                        source_type="ZAMAKANA",
+                    )
         except Exception as e:
             logger.error(f"Affiliate registration failed: {e}")
```

**ملاحظة توضيحية على الـdiff:** قبل `2960d9d`، السطر
`if user and user.referred_by:` كان بيرمي `AttributeError` فورًا (العمود
مكانش موجود إطلاقًا — تأكَّد من رسالة commit نفسها: *"12 domains
(single-level, disabled because `User.referred_by` never existed as a
column)"*)، يعني **الجسم الداخلي القديم (`affiliate_service.register_commission(...)`)
لم يكن يُنفَّذ إطلاقًا في أي وقت من قبل** — مش بس دلوقتي. يعني الدالة
كانت "معطوبة بصمت" 100% من البداية (Dead code فعليًا)، والتوحيد هو أول
مرة بيبقى فيها الكود ده **قابل للتنفيذ فعليًا** لو فيه محيل حقيقي.

**سجل commit كامل (رسالة الالتزام، للسياق الكامل):**

```
commit 2960d9ded49faf07999866a8d7bbdedcee72ba47
Author: 7abeeprog <eppne2020@gmail.com>
Date:   Mon Sep 7 00:30:49 2026 +0300

    Unify 3 conflicting referral/affiliate systems into one scope-based model

    1. feat: unify 3 conflicting referral/affiliate systems into one
       (10-level, scope-based commission via new AffiliateScope concept)

       Three separate, uncoordinated systems existed: affiliate domain
       (10-level, product-scoped, operationally dead), commerce domain
       (10-level sponsor chain, the only live path, but with zero product
       differentiation), and 12 domains (single-level, disabled because
       User.referred_by never existed as a column). Consolidated onto the
       affiliate domain with a new AffiliateScope/AffiliateScopeMember
       concept (single product / product group / entity-wide) replacing
       direct product_id coupling. commerce's old AffiliateTree/
       CommissionRecord/AffiliateConfig removed entirely. All 12 domains
       now feed the same unified 10-level Commission pipeline via the new
       User.referred_by_user_id column. Affiliate is now activatable as a
       per-tenant SaaS service, auto-provisioning a default ENTITY_WIDE
       scope on first subscription.

    [... 4 بنود إضافية غير متعلقة بالعمولة مباشرة: get_referral_tree
    MultipleResultsFound، academy commission distribution، 3 Celery task
    signature bugs، latent check_feature_access gap ...]

    Verified live: migration 045 applied to dev DB with a full
    downgrade/upgrade round-trip, and 6/6 pytest scenarios pass in
    tests/test_referral_affiliate_unified_system.py (basic commission,
    mixed-scope cart splitting, SaaS activation hook + idempotency,
    zamakana as the 12-domain reference, digital_twin's direct-code path,
    and silent skip when no scope is active).

    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

**قائمة كل الـ35 ملف اللي غيَّرهم commit `2960d9d`** (لإثبات إن
`social/service.py` مش من بينهم، القسم 5):

```
 ...referral-affiliate-system-design-session-log.md | 236 ++++++++
 ...-implementation-phase0-execution-session-log.md | 538 +++++++++++++++++
 ...affiliate-unified-implementation-session-log.md | 671 +++++++++++++++++++++
 ...erral-affiliate-unified-system-final-summary.md |  81 +++
 .../saas-get-plan-by-id-security-tradeoff-note.md  | 141 +++++
 PROGRESS_LOG.md                                    | 251 +++++++-
 eppne-backend/app/core/celery_config.py            |   9 +
 eppne-backend/app/domains/academy/service.py       |  27 +-
 eppne-backend/app/domains/affiliate/models.py      | 133 ++--
 eppne-backend/app/domains/affiliate/repository.py  | 139 +++--
 eppne-backend/app/domains/affiliate/router.py      |  45 +-
 eppne-backend/app/domains/affiliate/schemas.py     |  47 +-
 eppne-backend/app/domains/affiliate/service.py     | 260 +++++---
 .../app/domains/arbitration_syndicates/service.py  |  18 +-
 eppne-backend/app/domains/commerce/models.py       |  69 +--
 eppne-backend/app/domains/commerce/repository.py   |  96 +--
 eppne-backend/app/domains/commerce/router.py       |  49 +-
 eppne-backend/app/domains/commerce/schemas.py      |  32 +-
 eppne-backend/app/domains/commerce/service.py      | 106 +---
 eppne-backend/app/domains/digital_twin/service.py  |  22 +-
 eppne-backend/app/domains/employment/service.py    |  18 +-
 eppne-backend/app/domains/identity/models.py       |   5 +
 eppne-backend/app/domains/insurance/service.py     |  18 +-
 eppne-backend/app/domains/invitations/service.py   |  18 +-
 eppne-backend/app/domains/manufacturing/service.py |  18 +-
 eppne-backend/app/domains/realestate/service.py    |  18 +-
 eppne-backend/app/domains/saas/service.py          |  28 +
 .../app/domains/service_marketplace/service.py     |  18 +-
 .../app/domains/tenders_auctions/service.py        |  18 +-
 .../app/domains/tourism_sports/service.py          |  18 +-
 eppne-backend/app/domains/transport/service.py     |  18 +-
 eppne-backend/app/domains/zamakana/service.py      |  18 +-
 eppne-backend/app/tasks/affiliate.py               |  47 +-
 ...create_affiliate_scopes_and_unify_commission.py | 402 ++++++++++++
 .../test_referral_affiliate_unified_system.py      | 508 ++++++++++++++++
 35 files changed, 3507 insertions(+), 633 deletions(-)
```

**تأكيد تاريخي إضافي (`git log`):** commit اختبار الـaudit
(`33f5b71`) بتاريخ **2026-08-19 10:23**، وcommit التوحيد (`2960d9d`)
بتاريخ **2026-09-07 00:30** — أي **19 يوم فاصل** بين كتابة الاختبار
وبين التغيير اللي خلّى افتراضه غير صالح.

---

## 7. الإجابة النهائية على السؤال المفتوح (من بند الـbacklog)

> "هل ده regression حقيقي من التوحيد نفسه (الكود بيفشل فعليًا وقت
> التسجيل)، ولا الاختبارات القديمة بتفترض سلوك النظام قبل التوحيد (والكود
> شغال صح، بس الاختبار قديم)؟"

**الإجابة المؤكَّدة حيًا:** **الاحتمال الثاني — الاختبارات قديمة
وبتفترض سلوك ما قبل التوحيد.** الكود شغّال صح فعليًا (لا استثناء، لا
regression). البند التاني اللي كان مذكور كـ"غير حرج/جانبي" (`social`)
اتضح إنه **باج ثالث مستقل تمامًا**، غير مرتبط بموضوع البحث الأصلي ولا
بـcommit `2960d9d`.

**ما يترتب على هذا (توصية، خارج نطاق هذه الجلسة التنفيذي — فحص فقط):**
- الـ10 اختبارات المتعلقة بالعمولة تحتاج تحديث ليعكسوا الواقع الجديد
  الصحيح (مفيش رسالة log لمستخدم بلا محيل = سلوك سليم، مش دليل فشل) —
  أو إضافة سيناريو مستخدم *معاه* `referred_by_user_id` فعلي عشان
  الاختبار يغطي المسار الناجح الحقيقي (توزيع العمولة فعليًا) بدل
  الاعتماد على استثناء قديم كدليل غير مباشر.
- اختبار `social` منفصل تمامًا ويحتاج قرار تصميمي مستقل (fallback نصي
  ولا استثناء صريح لـ`_get_user_email`؟) — لا علاقة له بالعمولة.

**لم يُنفَّذ أي من التوصيتين أعلاه في هذه الجلسة** — النطاق كان فحص
read-only بحت بموافقة صريحة مسبقة، صفر تعديل كود أو اختبار.
