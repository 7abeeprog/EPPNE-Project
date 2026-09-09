# تحقيق تكميلي: موديل `SystemState` كامل + بيانات حية

**النطاق:** فحص read-only بحت — صفر تعديل كود، صفر تعديل بيانات (SELECT فقط).
**استكمال لـ:** [finance-router-hardcoded-tenant-investigation-session-log.md](finance-router-hardcoded-tenant-investigation-session-log.md)

## 1. موديل `SystemState` كامل (كل الأعمدة)

المصدر: `eppne-backend/app/domains/finance/models.py:95-130`

```python
class SystemState(Base):
    __tablename__ = "system_state"

    id = Column(Integer, primary_key=True, index=True)
    crypto_mode = Column(String(20), default="FULL_CRYPTO", nullable=False)
    is_trading_active = Column(Boolean, default=True)
    exchange_rates = Column(JSONB, default=lambda: {
        "MR_POUND": 1.0, "MR_USDT": 50.0, "MR7": 5.0, "NBT": 250.0, "MRX": 500.0,
    }, nullable=False)
    max_supply = Column(JSONB, default=lambda: {
        "MR_POUND": 1_000_000_000, "MR_USDT": 100_000_000, "MR7": 10_000_000,
        "NBT": 1_000_000, "MRX": 100_000,
    }, nullable=False)
    total_supply = Column(JSONB, default=lambda: {
        "MR_POUND": 0, "MR_USDT": 0, "MR7": 0, "NBT": 0, "MRX": 0,
    }, nullable=False)
    updated_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

**الأعمدة الثمانية:**

| العمود | النوع | الوصف |
|---|---|---|
| `id` | Integer PK | معرّف الصف (الجدول singleton — صف واحد فقط عمليًا، انظر §2) |
| `crypto_mode` | String(20) | وضع النظام (`FULL_CRYPTO` إلخ) — **ده اللي بيترجع في الـendpoint** |
| `is_trading_active` | Boolean | هل التداول مفعّل عالميًا — **لا يترجع في `/admin/crypto-mode`** |
| `exchange_rates` | JSONB | أسعار الصرف بين العملات — **لا يترجع في `/admin/crypto-mode`** |
| `max_supply` | JSONB | الحد الأقصى للعرض الكلي لكل عملة — **ده اللي بيترجع في الـendpoint** |
| `total_supply` | JSONB | العرض الحالي الفعلي المتداول لكل عملة — **لا يترجع في `/admin/crypto-mode`** |
| `updated_by_id` | BigInteger FK→users.id | آخر مستخدم عدّل الصف |
| `updated_at` | DateTime(tz) | وقت آخر تعديل |

**ملاحظة مهمة:** الـendpoint `GET /finance/admin/crypto-mode` بيرجع بس `crypto_mode` و`max_supply`. لكن نفس الصف فيه `is_trading_active`, `exchange_rates`, `total_supply`, `updated_by_id` — دول مش حساسين بمعنى "بيانات شخصية/مالية لمستخدم"، لكن `exchange_rates` و`total_supply` بيانات تشغيلية جوهرية (لو اتسربت أو اتغيرت لوحدها) لأنها بتأثر مباشرة على منطق التحويل/الصرف في `FinanceService` (انظر التقرير السابق — `state_repo.get_state()` مستخدم في نقاط تانية بالسيرفس، سطور 85, 382, 476 في service.py).

## 2. قيمة فعلية حية من الـDB (SELECT بسيط، صف واحد فقط موجود)

```sql
SELECT id, crypto_mode, is_trading_active, exchange_rates, max_supply, total_supply, updated_by_id, updated_at
FROM system_state ORDER BY id DESC;
```

```json
{
  "id": 1,
  "crypto_mode": "FULL_CRYPTO",
  "is_trading_active": true,
  "exchange_rates": {"MR7": 5.0, "MRX": 500.0, "NBT": 250.0, "MR_USDT": 50.0, "MR_POUND": 1.0},
  "max_supply": {"MR7": 10000000, "MRX": 100000, "NBT": 1000000, "MR_USDT": 100000000, "MR_POUND": 1000000000},
  "total_supply": {"MR7": 0, "MRX": 0, "NBT": 0, "MR_USDT": 0, "MR_POUND": 0},
  "updated_by_id": null,
  "updated_at": "2026-08-12 20:46:23.477344+00:00"
}
```

- **صف واحد فقط (`row_count=1`, `id=1`)** — ده بيأكد الاستنتاج من التقرير السابق: `system_state` جدول singleton عالمي، مفيهوش صفوف لكل تينانت. القيمة الديفولت في الموديل (المعرّفة بـ`lambda`) هي فعليًا نفس القيم الحقيقية في القاعدة دلوقتي (يعني الصف اتعمل مرة واحدة بالـdefault ومحدش عدّله — `updated_by_id` = null و`total_supply` كله أصفار، يعني مفيش تداول حقيقي حصل لحد دلوقتي أو النظام لسه في مرحلة تأسيسية).

## 3. هل `max_supply` رقم عام، ولا فيه تفاصيل حساسة؟

**`max_supply` نفسه رقم عام تمامًا** — سقف تصميمي معلن للعرض الكلي لكل عملة (زي `MR_POUND: 1,000,000,000`)، مش رصيد حد معيّن ومش مفتاح ولا إعداد أمان. طبيعته زي "الحد الأقصى لعدد العملة اللي ممكن تتصك" — رقم نظامي ثابت غالبًا معروف بالفعل للمستخدمين (whitepaper-style economics)، مش سرّي بطبيعته.

**لكن الحقول التانية في نفس الجدول (مش المُرجعة في هذا الـendpoint لكن موجودة جنبه في نفس الصف) فيها حساسية متفاوتة:**

- `total_supply` — **العرض الفعلي المتداول حاليًا لكل عملة**. ده مش سرّي بمعنى مفتاح/بيانات شخصية، لكنه **معلومة تشغيلية/مالية حساسة** (تكشف الحجم الفعلي للنظام المالي، مفيدة لأي حد عايز يعرف "إيه حجم السيولة الفعلي" — عكس `max_supply` اللي هو مجرد سقف نظري).
- `exchange_rates` — أسعار الصرف الداخلية بين العملات. حساسة تشغيليًا لأنها بتتحكم في كل عمليات `swap` (service.py) — لو اتسربت قبل تغييرها ده مش بالضرورة خطر، لكن لو حد عدّلها (مش الحالة هنا لأن الـendpoint دي read-only) هيأثر على كل معاملات المنصة.
- `is_trading_active` — flag تشغيلي (تفعيل/تعطيل التداول عالميًا).
- `updated_by_id` — **معرّف مستخدم داخلي (FK لجدول users)** — مش سرّي بحد ذاته لكنه بيربط تعديل حساس بمستخدم معيّن.

**مفيش في الجدول ده أي مفاتيح تشفير، أرصدة مستخدمين فرديين، أو إعدادات أمان (secrets/keys)** — الأرصدة الفردية للمستخدمين محفوظة في جداول تانية (`Wallet` عبر `WalletRepository`، مش هنا). الجدول ده مقصور على **حالة نظام مالي عامة (system-wide economic parameters)**.

**الخلاصة بخصوص الـendpoint الحالي (`GET /finance/admin/crypto-mode`):**
- البيانات اللي فعليًا بترجع (`crypto_mode` + `max_supply`) — **مش حساسة بشكل خطير**، أقرب لمعلومة تصميمية عامة عن النظام.
- لكن بما إن الـendpoint من غير أي auth، ولازم مراجعة لو حد يحب يوسّع الـresponse مستقبلًا (مثلاً يضيف `total_supply` أو `exchange_rates`) — وقتها هيبقى فيه تسريب معلومة تشغيلية حساسة فعلاً بدون auth. التوصية (بدون تنفيذ أي تعديل الآن): أي تعديل مستقبلي على هذا الجدول أو الـendpoint المرتبط بيه يستأهل مراجعة auth بشكل منفصل عن مشكلة الـ`tenant_id` الأصلية.

**صفر تعديل كود أو بيانات اتنفذ في الجلسة دي — فحص وSELECT للقراءة فقط بالكامل.**
