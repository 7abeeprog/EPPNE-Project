# Session Log — تحقيق قبل-الإصلاح لبند Backlog #2 (`test_saas_active_subscription.py`)

**Date:** 2026-09-08
**النطاق:** فحص read-only بحت. **صفر تعديل على أي كود أو أي صف في الـDB.**
**الهدف:** عرض الأربعة اختبارات المذكورة كاملة، وتحديد (1) هل التينانت
المستخدَم فيهم كلهم `1` بالحرف، و(2) هل الـservices المطلوبة
(`real_estate`/`insurance`) موجودة بالفعل في `saas_service_catalog`، وهل
فعلًا محتاجين بس "ربط تينانت 1" بيهم زي تينانت 16.

---

## 1) الأربعة اختبارات — نص كامل

الملف: `eppne-backend/tests/test_saas_active_subscription.py`
(`TENANT_ID = 1` معرَّف كثابت واحد على مستوى الملف كله، سطر 116).

### 1.1 `test_realestate_rent_unit_saas_check_passes` (سطر 168-211)

```python
TENANT_ID = 1  # (ثابت الملف، سطر 116)

@pytest.mark.asyncio
async def test_realestate_rent_unit_saas_check_passes(db, monkeypatch):
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)

    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-SAAS9-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-SAAS9-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_rent=True, is_available_for_sale=False,
    )
    unit_id = unit.id
    development_id = development.id
    landlord = await _create_funded_user(db, "p_regtest_saas9_re_landlord")
    tenant_user = await _create_funded_user(db, "p_regtest_saas9_re_tenant")
    user_ids = [landlord.id, tenant_user.id]
    service = RealEstateService(db)

    try:
        contract = await service.rent_unit(
            landlord_id=landlord.id, tenant_id=TENANT_ID, unit_id=unit_id,
            tenant_user_id=tenant_user.id, monthly_rent=Decimal("50"),
            start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=365),
            idempotency_key=f"REGTEST-SAAS9-RENT-{_suffix()}",
        )
        assert contract is not None

        refreshed = (await db.execute(
            select(RentalContract).where(RentalContract.id == contract.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "العقد المتوقع مش موجود على القرص — دليل مباشر إن #9 بتعمل صح"
        assert refreshed.tenant_user_id == tenant_user.id
    finally:
        await db.execute(delete(RentalContract).where(RentalContract.unit_id == unit_id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)
```

**التينانت:** `tenant_id=TENANT_ID` صراحة في كل نداء (`create_development`،
`create_unit`، `rent_unit`) — `TENANT_ID` نفسه `= 1` (سطر 116). ✅ حرفيًا `1`.

### 1.2 `test_insurance_subscribe_saas_check_passes` (سطر 219-265)

```python
@pytest.mark.asyncio
async def test_insurance_subscribe_saas_check_passes(db, monkeypatch):
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)

    ins_repo = InsuranceRepository(db)
    buyer = await _create_funded_user(db, "p_regtest_saas9_ins_sub", Decimal("1000"))
    policy = await ins_repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-SAAS9-POLICY-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("20"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("1000"), is_active=True,
        created_by=buyer.id,
    )
    await db.commit()  # create_policy() flush-only
    policy_id = policy.id
    user_ids = [buyer.id]
    service = InsuranceService(db)

    try:
        subscription = await service.subscribe(
            user_id=buyer.id, tenant_id=TENANT_ID,
            data={
                "policy_id": policy_id, "subscriber_user_id": buyer.id,
                "start_date": datetime.utcnow(),
            },
            idempotency_key=f"REGTEST-SAAS9-SUB-{_suffix()}",
        )
        assert subscription is not None

        refreshed = (await db.execute(
            select(InsuranceSubscription).where(InsuranceSubscription.id == subscription.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "الاشتراك المتوقع مش موجود على القرص — دليل مباشر إن #9 بتعمل صح"
        assert refreshed.status == "ACTIVE"

        wallet = await WalletRepository(db).get_by_user_id(buyer.id, TENANT_ID)
        assert wallet is not None
        assert Decimal(str(wallet.balances.get("MR_USDT"))) == Decimal("980"), (
            "دفع القسط لازم يكون التزم فعليًا (خُصم القسط 20 من 1000)"
        )
    finally:
        await db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.policy_id == policy_id))
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)
```

**التينانت:** `tenant_id=TENANT_ID` صراحة (`create_policy`، `subscribe`،
`WalletRepository.get_by_user_id`). ✅ حرفيًا `1`.

### 1.3 `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` (سطر 273-315)

```python
@pytest.mark.asyncio
async def test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug(db):
    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-SAAS9-DEV2-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-SAAS9-UNIT2-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_sale=True, is_available_for_rent=False,
        sale_price_mrusdt=Decimal("500"),
    )
    unit_id = unit.id
    development_id = development.id
    buyer = await _create_funded_user(db, "p_regtest_saas9_re_buyer")
    user_ids = [buyer.id]
    service = RealEstateService(db)

    try:
        with pytest.raises(TypeError, match="tenant_id"):
            await service.buy_fractional_ownership(
                buyer_id=buyer.id, tenant_id=TENANT_ID, unit_id=unit_id,
                percentage=Decimal("10"),
                idempotency_key=f"REGTEST-SAAS9-BUY-{_suffix()}",
            )

        ownership_count = (await db.execute(
            select(PropertyOwnership).where(PropertyOwnership.owner_user_id == buyer.id)
        )).scalars().all()
        assert len(ownership_count) == 0, "صفر ownership كان المتوقع — الكراش قبل الوصول لـfinance.transfer أصلًا"
    finally:
        await db.execute(delete(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)
```

**التينانت:** `tenant_id=TENANT_ID` صراحة. ✅ حرفيًا `1`.
(ملاحظة: `pytest.raises(TypeError, match="tenant_id")` هنا بيفترض إن
التنفيذ **عدَّى** بوابة الـSaaS ووصل لبج `AIAgentsService.execute_agent_action`
اللاحق — الفحص تحت في §3 بيوضح إن الافتراض ده بقى غير صحيح دلوقتي.)

### 1.4 `test_insurance_review_claim_saas_check_passes_then_hits_known_bug` (سطر 323-416)

```python
@pytest.mark.asyncio
async def test_insurance_review_claim_saas_check_passes_then_hits_known_bug(db):
    ins_repo = InsuranceRepository(db)
    claimant = await _create_funded_user(db, "p_regtest_saas9_ins_claimant")
    user_ids = [claimant.id]

    policy = await ins_repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-SAAS9-POLICY2-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("20"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("1000"), is_active=True,
        created_by=claimant.id,
    )
    subscription = await ins_repo.create_subscription(
        tenant_id=TENANT_ID, policy_id=policy.id, subscriber_user_id=claimant.id,
        start_date=datetime.utcnow(), status="ACTIVE",
        policy_nft_id=f"INS-REGTEST-{_suffix()}", subscription_tx_hash=f"SUB-REGTEST-{_suffix()}",
    )
    claim = await ins_repo.create_claim(
        tenant_id=TENANT_ID, subscription_id=subscription.id, claimant_user_id=claimant.id,
        incident_date=datetime.utcnow(), incident_description="Regression test incident",
        claimed_amount_mrusdt=Decimal("100"), status=ClaimStatus.SUBMITTED,
    )
    await db.commit()  # create_policy/create_subscription/create_claim كلهم flush-only
    policy_id = policy.id
    subscription_id = subscription.id
    claim_id = claim.id
    service = InsuranceService(db)

    try:
        with pytest.raises(PermissionDeniedError, match="Not authorized to review this claim"):
            await service.review_claim(
                claim_id=claim_id, reviewer_id=claimant.id, tenant_id=TENANT_ID,
                approve=True,
                idempotency_key=f"REGTEST-SAAS9-CLAIM-{_suffix()}",
            )

        refreshed_claim = (await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )).scalar_one_or_none()
        assert refreshed_claim is not None
        assert refreshed_claim.status == ClaimStatus.SUBMITTED, (
            "حالة المطالبة لازم تفضل SUBMITTED — الكراش قبل الوصول لـupdate_claim أصلًا"
        )
        assert refreshed_claim.payout_tx_hash is None
    finally:
        await db.execute(delete(InsuranceClaim).where(InsuranceClaim.id == claim_id))
        await db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.id == subscription_id))
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)
```

**التينانت:** `tenant_id=TENANT_ID` صراحة. ✅ حرفيًا `1`.
(نفس الملاحظة: `pytest.raises(PermissionDeniedError, match="Not authorized
to review this claim")` بيفترض الوصول الناجح لطبقة `review_claim` الداخلية
— الفحص تحت بيوضح إن التنفيذ هيتوقف **قبل** الوصول لهذه الطبقة أصلًا.)

**خلاصة السؤال الأول:** الأربعة اختبارات كلهم بيستخدموا `TENANT_ID` — وهو
ثابت واحد معرَّف مرة واحدة أعلى الملف (سطر 116) بقيمة **`1` بالحرف**، ومُمرَّر
صراحة كـ`tenant_id=TENANT_ID` في كل نداء داخل الأربعة اختبارات (development،
unit، policy، subscription, claim، rent_unit، buy_fractional_ownership،
subscribe، review_claim). **لا يوجد أي تباين — تينانت واحد ثابت للأربعة.**

---

## 2) هل `real_estate`/`insurance` موجودين في `saas_service_catalog`؟

استعلام مباشر على قاعدة البيانات الفعلية اللي بيستخدمها الاختبار
(`DATABASE_URL` في `eppne-backend/.env` → `postgresql+asyncpg://eppne:***@127.0.0.1:5435/eppne_v2`،
حاوية `eppne_db`):

```sql
SELECT id, name, code, is_active FROM saas_service_catalog
WHERE code IN ('insurance', 'real_estate');
```

```
 id  |           name             |    code     | is_active
-----+----------------------------+-------------+-----------
 101 | التأمين السيادي (Pilot)   | insurance   | t
 107 | العقارات السيادية (Pilot) | real_estate | t
```

✅ **موجودين بالفعل، مفعَّلين (`is_active=true`)** — تم إنشاؤهم في جلسة
`insurance-can-access-service-pilot` (وجلسة realestate اللاحقة ضمن
`remaining-7-domains-can-access-service-migration`). `saas_service_catalog`
جدول **عام غير مرتبط بتينانت** (`app/domains/saas/models.py:12-25` — لا
يوجد عمود `tenant_id` أصلًا، `code` فريد globally). فمفهوم "الـservice
اتعمل لتينانت 16" غير دقيق حرفيًا على مستوى هذا الجدول تحديدًا — الصفّان
دول عامّان ومتاحان لأي تينانت من حيث المبدأ. **الفرق الفعلي بين تينانت
16 وتينانت 1 موجود في جدولين تانيين تمامًا**، موضَّحين تحت.

---

## 3) الفجوة الفعلية: تينانت 16 مقابل تينانت 1

`can_access_service(service_code)` (`app/domains/saas/service.py:328-350`)
بتطلب **طبقتين** ناجحتين معًا، مش طبقة واحدة:

```python
async def can_access_service(self, service_code: str) -> bool:
    service = await self.repo.get_service_by_code(service_code)
    if not service:
        return False
    service_id = cast(int, service.id)

    # الطبقة 1: TenantServiceAccess (صف صريح تينانت↔خدمة)
    access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
    if access is None or not cast(bool, access.is_active):
        return False

    # الطبقة 2: اشتراك نشط عبر saas_plan_service_access
    subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
    if subscription is None:
        return False

    ...
    return subscription.status in ["ACTIVE", "TRIAL"]
```

### 3.1 الربط الخاص بالخطط (`saas_plan_service_access`)

```sql
SELECT sc.code, sp.id AS plan_id, sp.name, sp.is_active
FROM saas_plan_service_access psa
JOIN saas_service_catalog sc ON sc.id = psa.service_id
JOIN saas_service_plans sp ON sp.id = psa.plan_id
WHERE sc.code IN ('insurance', 'real_estate');
```

```
    code     | plan_id |           plan_name             | is_active
-------------+---------+----------------------------------+-----------
 insurance   |     101 | خطة التأمين التجريبية (Pilot)   | t
 real_estate |     110 | خطة العقارات التجريبية (Pilot)  | t
```

الخطتان موجودتان ومربوطتان صح بالخدمتين (مستوى الـcatalog/plan-access —
عام، بلا تينانت).

### 3.2 `saas_tenant_subscriptions` — هنا الفرق الحقيقي

```sql
SELECT ts.tenant_id, ts.plan_id, sp.code AS plan_code, ts.status
FROM saas_tenant_subscriptions ts
JOIN saas_service_plans sp ON sp.id = ts.plan_id
WHERE ts.plan_id IN (101, 110);
```

```
 tenant_id | plan_id |       plan_code        | status
-----------+---------+-------------------------+--------
        16 |     101 | insurance-pilot-plan    | ACTIVE
        16 |     110 | real-estate-pilot-plan  | ACTIVE
```

**تينانت 16 فقط** عنده اشتراك `ACTIVE` على الخطتين. صفر صف لتينانت 1.

### 3.3 `saas_tenant_service_access` — نفس الفجوة، طبقة إضافية

```sql
SELECT tenant_id, service_id, access_level, is_active
FROM saas_tenant_service_access
WHERE service_id IN (101, 107);
```

```
 tenant_id | service_id | access_level | is_active
-----------+------------+--------------+-----------
        16 |        101 | BASIC        | t
        16 |        107 | BASIC        | t
```

**تينانت 16 فقط** عنده صف `TenantServiceAccess` للخدمتين. صفر صف لتينانت 1
(تأكَّد أيضًا: `SELECT ... WHERE tenant_id=1 AND service_id IN (101,107)`
→ `0 rows`).

### 3.4 اشتراكات تينانت 1 الفعلية (للمقارنة — لا علاقة لها بـ`insurance`/`real_estate`)

```sql
SELECT ts.id, ts.plan_id, sp.code, sp.name, ts.status
FROM saas_tenant_subscriptions ts JOIN saas_service_plans sp ON sp.id = ts.plan_id
WHERE ts.tenant_id = 1;
```

```
 id  | plan_id |           plan_code           |             name              |  status
-----+---------+--------------------------------+--------------------------------+-----------
   2 |       2 | p_saas9_plan_8fa402           | P-SAAS9-VERIFY-PLAN-8fa402    | ACTIVE
  50 |      48 | test_reqsector_affiliate_plan | TEST_REQSECTOR_AFFILIATE_PLAN | CANCELLED
  89 |      77 | test-tenders                  | TEST plan tenders             | ACTIVE
  90 |      78 | test-auctions                 | TEST plan auctions            | ACTIVE
 130 |     105 | transport-pilot-plan          | خطة النقل التجريبية (Pilot)   | ACTIVE
```

تينانت 1 عنده اشتراكات حقيقية نشطة — لكن ولا واحدة منهم مربوطة
بـ`insurance`(101)/`real_estate`(107) عبر `saas_plan_service_access`.

---

## 4) الخلاصة النهائية (رد مباشر على السؤالين)

1. **التينانت المستخدَم في الأربعة اختبارات كلهم `1` بالحرف؟** ✅ **نعم،
   بلا استثناء.** ثابت واحد (`TENANT_ID = 1`، سطر 116) مُستخدَم صراحة في
   كل الأربعة اختبارات وكل نداء داخلهم.

2. **هل `real_estate`/`insurance` موجودين بالفعل في `saas_service_catalog`
   من جلسات سابقة لتينانت 16، ومحتاجين بس "ربط تينانت 1 بيهم"؟**
   ✅ **صحيح من ناحية النتيجة العملية، مع تصحيح دقيق للآلية:**
   - `saas_service_catalog` نفسه **عام غير مرتبط بتينانت أصلًا** — الصفّان
     (`insurance`=101، `real_estate`=107) موجودان ومفعَّلان، ومتاحان من
     حيث المبدأ لأي تينانت.
   - الخطط (`saas_service_plans` 101/110) وربطها بالخدمات
     (`saas_plan_service_access`) موجودان وصحيحان أيضًا — عامّان بلا تينانت.
   - **الفجوة الفعلية اللي بتمنع تينانت 1 من المرور هي في جدولين
     تينانت-specific**: تينانت 16 عنده صف `ACTIVE` في
     `saas_tenant_subscriptions` (على الخطتين 101/110) **و** صف
     `is_active=true` في `saas_tenant_service_access` (للخدمتين 101/107).
     تينانت 1 **صفر صف في الاتنين**. الاتنين مطلوبين معًا —
     `can_access_service` بترجع `False` لو أي واحد منهم غايب، بغض النظر عن
     التاني.
   - إذن: "ربط تينانت 1" فعليًا = seed صفّين جديدين لكل خدمة (صف
     `saas_tenant_subscriptions` + صف `saas_tenant_service_access`) لتينانت
     1، إما بإعادة استخدام نفس الخطتين الموجودتين (101/110) أو بخطط جديدة
     مخصَّصة — **قرار تصميمي** (نفس الخطة التجريبية المشتركة لتينانت 16،
     أو خطة seed منفصلة لتينانت 1) لسه مفتوح، لم يُتَّخذ في هذا التحقيق
     (خارج نطاق read-only المطلوب).

هذا يؤكد حرفيًا بند `PROGRESS_LOG.md` #2 (والتحديث الموسَّع في تقرير
`remaining-7-domains-can-access-service-migration-session-log.md`، §4.5
سطر 638-642 و§7.5 سطر 1120): **الأربعة اختبارات الأربعة** (مش بس
الاتنين الخاصين بـ`insurance` كما كان موثَّقًا أول مرة) هيفشلوا حاليًا
عند بوابة `can_access_service` — تينانت 1 مرفوض قبل ما يوصل لأي منطق
لاحق موثَّق في `docstring` كل اختبار (بما فيهم بجات `buy_fractional_ownership`/
`review_claim` المُوثَّقة مسبقًا، اللي بقت غير قابلة للوصول أصلًا خلف
بوابة الـSaaS الجديدة).

---

## 5) ملاحظة منهجية — صفر تعديل

كل الاستعلامات أعلاه **قراءة فقط** (`SELECT` حصرًا) عبر
`docker exec eppne_db psql`. صفر `INSERT`/`UPDATE`/`DELETE`. صفر تعديل
على أي ملف كود. تأكيد إضافي: `git status` قبل وبعد هذا التحقيق يُظهر
نفس مجموعة الملفات المعدَّلة مسبقًا (من جلسات تانية سابقة على هذه
الجلسة) — هذه الجلسة لم تلمس أي ملف غير هذا التقرير نفسه.
