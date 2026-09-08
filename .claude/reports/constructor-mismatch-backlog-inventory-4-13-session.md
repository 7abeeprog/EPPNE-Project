# جلسة جرد — بقية #4 و#13 [2026-08-29]

**الحالة:** توثيق فقط، صفر إصلاح، زي ما اتفقنا (بند 7 من قائمة القرارات).

---

## #13 — `invoicing-create-invoice-wrong-kwarg` (اسم الـkwarg)

**`grep` شامل حقيقي:** كل الـ21 موضع `create_invoice(` عبر كل الدومينات (استُبعِد `saas.repo.create_invoice`
— method مختلفة تمامًا على `SaaSRepository`، لا علاقة لها بـ`InvoicingService`):

| الدومين | عدد المواضع | الـkwarg المستخدَم |
|---|---|---|
| `service_marketplace` | 1 | ❌ `tenant_id=` (**الباج المؤكَّد الوحيد**) |
| `ai_agents` | 1 | ✅ `entity_id=` |
| `arbitration_syndicates` | 3 | ✅ `entity_id=` |
| `insurance` | 2 | ✅ `entity_id=` |
| `invitations` | 1 | ✅ `entity_id=` |
| `manufacturing` | 2 | ✅ `entity_id=` |
| `realestate` | 2 | ✅ `entity_id=` |
| `tenders_auctions` | 1 | ✅ `entity_id=` |
| `tourism_sports` | 3 | ✅ `entity_id=` |
| `transport` | 2 | ✅ `entity_id=` |
| `zamakana` | 2 | ✅ `entity_id=` |

**النتيجة: صفر انتشار.** `service_marketplace/service.py:203` هو الموضع الوحيد المؤكَّد من الأساس
— باقي الـ12 دومين (20 موضع) سليمين. **القرار العملي الأصلي (معالجته ضمن جلسة #14) كان صحيح —
لم يكن هناك شيء إضافي يحتاج معالجة.**

**صفر إصلاح — التوجيه الأصلي كان تصنيفي فقط.**

---

## #4 — بقية `silent-write-regression`

جرد كودي (قراءة + تتبع استدعاءات `commit()`، بلا بيانات throwaway/تحقق حي كامل — متسق مع نطاق
"جرد رخيص" المتفق عليه).

### `saas.process_auto_renewals` — فرع `except InsufficientBalanceError`

`saas/service.py:167-224`. فرع النجاح (`try`, سطر 181-208) عنده `await self.db.commit()` صريح
(سطر 205). **فرع `except InsufficientBalanceError` (210-218) بلا أي `commit()`:**

```python
except InsufficientBalanceError:
    await self.repo.update_subscription(
        cast(int, sub.id), target_tenant,
        status="PAST_DUE",
        grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
    )
    results.append({"subscription_id": cast(int, sub.id), "status": "PAST_DUE"})
```

`repo.update_subscription()` (`saas/repository.py:216-227`) مؤكَّد `flush()` بس، بلا `commit()`
داخلي. **نفس البنية بالحرف اللي كانت في `cancel_subscription` قبل إصلاحها [2026-08-24].** النتيجة
المتوقَّعة: `PAST_DUE` بترجع للمستدعي كنجاح، لكن الكتابة الفعلية (`status`, `grace_period_end_date`)
تضيع صامتة عند إغلاق الجلسة.

### `can_access_service`

`saas/service.py:229-251`، سطر 248: فرع `PAST_DUE` منتهي الصلاحية:

```python
else:
    await self.repo.update_subscription_status(cast(int, subscription.id), self.tenant_id, "EXPIRED")
    return False
```

`update_subscription_status` (`saas/repository.py:233-239`) wrapper حول نفس `update_subscription`
(`flush()` بس). **أخطر من `process_auto_renewals`:** `can_access_service` بتتنادى كـ**فحص قراءة
بحت** من كل المستدعين (`check_and_enforce_access`, `check_service_access`, وعبر `_check_saas_limits`
في تقريبًا كل الـ30 دومين) — ولا واحد فيهم متوقَّع/محتاج يعمل `commit()` بعد فحص صلاحية. يعني هذه
الكتابة **شبه دايمًا** بتضيع صامتة، مش حالة حافة نادرة.

**صفر إصلاح — ثقة عالية من قراءة الكود (نفس نمط `cancel_subscription` المُصلَح بالضبط)، لكن بلا
تحقق حي فعلي (بيانات throwaway) في هذه الجلسة تحديدًا — الاتنين يستاهلوا جلسة إصلاح مخصَّصة
(نفس معالجة `cancel_subscription`: `commit()` صريح في الموضعين).**

---

## الحالة الإجمالية النهائية لقائمة القرارات (9 بنود)

| # | البند | الحالة |
|---|---|---|
| 1 | توثيق الـ9 بنود القديمة | ✅ خلص |
| 2 | بقية #27 | ⏳ لسه بانتظار جلسة منفصلة |
| 3 | التحقق من #31 | ✅ خلص |
| 4 | الـ7 بنود الميكانيكية | ✅ خلصت كلها |
| 5 | Migration بسيطة (#28, #45) | ✅ خلصت كلها |
| 6 | أولوية القرارات التصميمية (7 بنود) | ⏳ مؤجَّلة كما اتفقنا |
| 7 | جلسة الجرد (بقية #4، #13) | ✅ **خلصت الآن** |
| 8 | تحديث الأعداد المتبقية في الملف الموحَّد | ⏳ آخر حاجة |
| 9 | Commit منفصل | ⏳ لسه ماحصلش |

**التالي:** commit منفصل (بند 9) ← تحديث الأقسام المتبقية (بند 8، آخر حاجة).
