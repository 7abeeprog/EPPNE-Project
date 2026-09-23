# جلسة: التحقق من `review_claim` (insurance) — خطر الدفع المزدوج

**التاريخ:** 2026-09-23
**البند:** `insurance-review-claim-no-status-guard-and-random-payout-idempotency` (من Batch 0-A، §F4 — "غير مُتحقَّق، أولوية عالية").
**القواعد:** قراءة فقط. لا تعديل كود، لا staging/commit، لا كتابة في `PROGRESS_LOG.md`، لا push.
**الحالة:** مكتمل حتى §18 (mutation check: يفشل 3/3 على HEAD، يمر 3/3 على الإصلاح، zero-diff) — **staged، متوقف قبل `git commit` ومسودات `PROGRESS_LOG.md` غير مكتوبة، بانتظار موافقة المستخدم.**

---

## 1. الموقع الحالي للكود

- `eppne-backend/app/domains/insurance/service.py:452-575` — `review_claim` (تقرير Batch 0-A ذكر 452–578؛ الأسطر 576-578 هي رأس القسم التالي — الدالة لم تتحرك).
- `eppne-backend/app/domains/insurance/router.py:219-241` — `PUT /insurance/claims/{claim_id}/review` (هيدر `Idempotency-Key` **اختياري**؛ rate limit 10/دقيقة).
- ملفات insurance نظيفة في شجرة العمل (لا تعديلات غير committed) — آخر commit عليها `44f1d0e` (Batch 0-A).
- المعتمَد عليه: `FinanceService.transfer` في `app/domains/finance/service.py:58-147`، و`app/core/idempotency.py` (Redis).

## 2. تتبّع المسار الكامل

| الخطوة | السطر | ما يحدث |
|---|---|---|
| 1 | 463 | `_check_saas_limits` |
| 2 | 466-474 | **فقط إذا** أُرسل هيدر `Idempotency-Key`: يُقرأ من Redis؛ إن وُجد → يُرجع المطالبة بلا أي أثر |
| 3 | 476-478 | جلب المطالبة + فحص التينانت (404) |
| 4 | 480-488 | جلب الاشتراك/البوليصة + فحص عضوية المراجِع (OWNER/EXECUTIVE_DIRECTOR) |
| 5 | 490-505 | مراجعة AI (أي استثناء يُبلَع — لا يوقف شيئًا) |
| 6 | 511-540 | `begin_nested()`: approve → `transfer` + `status=PAID`؛ reject → `status=REJECTED` |
| 7 | 541 | `commit()` |
| 8 | 543-553 | approve → `create_invoice` (خطؤها يُبلَع) |
| 9 | 555-568 | event_bus + audit_log |
| 10 | 572-573 | تخزين `{"claim_id"}` في Redis **فقط إذا** كان هناك هيدر |

### 2.1 فحوصات الحالة الموجودة: **صفر**

الإشارات الوحيدة لـ`ClaimStatus` داخل الدالة هي **كتابة** الحالة (سطر 529، 537). لا يوجد أي قراءة لـ`claim.status` قبل الدفع. لا `SELECT ... FOR UPDATE` على صف المطالبة (`repository.py:117-119` — `select` عادي).

### 2.2 مفتاح idempotency الخاص بالدفع — عشوائي في كل استدعاء

```python
# service.py:517
payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
```

حماية `transfer` الوحيدة ضد التكرار هي البحث بالمفتاح (`finance/service.py:72-75`):

```python
existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
if existing_tx:
    return existing_tx
```

لأن المفتاح يحتوي `uuid4` جديدًا في كل استدعاء، **هذا الفحص لا يتطابق أبدًا** بين استدعاءين → كل استدعاء = تحويل جديد حقيقي.

### 2.3 هيدر `Idempotency-Key` لا يحمي من هذا السيناريو

- اختياري (`Header(None)`) — العميل الذي لا يرسله لا حماية له إطلاقًا.
- إعادة المحاولة بهيدر **مختلف** (أو مراجِع ثانٍ في نفس الكيان) لا تُكتشف.
- حتى بنفس الهيدر: الفحص (سطر 466) والتخزين (سطر 572) غير ذريين — طلبان متزامنان يمرّان كلاهما قبل التخزين (check-then-act). `get_idempotency_result` يتعامل مع `"LOCKED"` كـ`None` لكن `review_claim` لا يضع قفلًا أصلًا.

## 3. التشخيص

### 3.1 السيناريو A — `approve=true` مرتين على نفس المطالبة → **دفع مزدوج حقيقي (من قراءة الكود)**

الاستدعاء الثاني: المطالبة بحالة `PAID` → لا شيء يوقفه → مفتاح `uuid` جديد → `transfer` ينفّذ تحويلًا ثانيًا كاملًا (خصم من محفظة المراجِع، إضافة للمطالِب) → `update_claim` **يستبدل** `payout_tx_hash` بالـhash الجديد (أثر الدفعة الأولى يختفي من سجل المطالبة، ويبقى فقط في جدول `transactions`) → فاتورة ثانية → حدث `insurance.claim.resolved` ثانٍ + audit log ثانٍ.

الحد الوحيد: رصيد محفظة المراجِع (`InsufficientBalanceError`) و rate limit 10/دقيقة. **لا حد لعدد مرات الدفع لنفس المطالبة.**

ملاحظة: يمكن أيضًا أن يكون المبلغ في الاستدعاء الثاني مختلفًا (`approved_amount` جديد) — فلا حتى ثبات للمبلغ.

### 3.2 السيناريو B — `approve=false` بعد `PAID` → **حالة غير متسقة حقيقية (لا دفع مزدوج)**

لا تتحرك أموال، لكن: `status` يصبح `REJECTED` بينما الأموال مدفوعة فعلًا، و`approved_amount_mrusdt` و`payout_tx_hash` يبقيان كما هما (لا يُصفَّران). النتيجة سجل يقول "مرفوضة" ومعها hash دفع ومبلغ معتمد. والعكس أيضًا: `REJECTED` ثم `approve=true` → يدفع مطالبة سبق رفضها.

### 3.3 الحكم

**الخطر حقيقي، ليس نظريًا — على مستوى الكود.** الفجوة بالضبط:
1. **لا status guard** قبل سطر 511 (لا شيء يمنع مراجعة مطالبة حالتها نهائية `PAID`/`REJECTED`).
2. **مفتاح الدفع غير حتمي** (سطر 517) فيُعطّل حماية `transfer` الداخلية.
3. **لا قفل صف** → حتى بعد إضافة (1) يبقى سباق بين طلبين متزامنين.

⚠️ **لم يُثبَت حيًا بعد** — الحكم أعلاه من قراءة الكود. خطة التحقق الحي في §5.

## 4. الإصلاح المقترح (لم يُنفَّذ)

ثلاث طبقات، كلها داخل `review_claim` فقط، بلا migration:

**(1) قفل الصف + status guard** — جلب المطالبة مع `with_for_update()` داخل `begin_nested()` ثم الرفض إن لم تكن قابلة للمراجعة:

```python
REVIEWABLE = {ClaimStatus.SUBMITTED, ClaimStatus.UNDER_INVESTIGATION}
...
async with self.db.begin_nested():
    locked = (await self.db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id).with_for_update()
    )).scalar_one()
    if locked.status not in REVIEWABLE:
        raise ValidationError(f"Claim already reviewed (status={locked.status.value})")
    ...
```

(الأنظف: دالة repo جديدة `get_claim_for_update(claim_id)` بدل `select` مباشر في الخدمة — نمط opt-in، لا تغيير لـ`get_claim` الحالية.)

سؤال للمستخدم: هل `APPROVED` حالة قابلة للمراجعة؟ لا يوجد مسار في `review_claim` يكتب `APPROVED` (يقفز مباشرة لـ`PAID`)؛ فقط `update_claim` (superuser، PATCH) يمكنه ضبطها. اقتراحي: **لا** (قابلة للمراجعة = `SUBMITTED` و`UNDER_INVESTIGATION` فقط) — لكن هذا قرار منتج.

**(2) مفتاح دفع حتمي** — كحزام أمان ثانٍ يُفعّل حماية `transfer` الموجودة:

```python
payment_idempotency = f"claim_payout_{claim_id}"
```

(بما أن المطالبة تُدفع مرة واحدة فقط عبر هذا المسار، المفتاح يجب أن يكون فريدًا لكل مطالبة لا لكل استدعاء. **مُتحقَّق على مستوى الموديل:** `finance/models.py:61` فهرس unique جزئي `ix_transactions_idempotency_key` (`WHERE idempotency_key IS NOT NULL`) + `unique=True` في سطر 70 → أي إدراج ثانٍ بنفس المفتاح يفشل بـIntegrityError حتى لو فات فحص `get_by_idempotency_key`. وجود الفهرس فعليًا في قاعدة البيانات الحية سيُؤكَّد بـ`\d transactions` في بداية التحقق الحي.)

**(3) لا تغيير على هيدر Redis** — يبقى كما هو (تحسين استجابة للإعادة، لا حماية). القفل + الـguard هما الحماية الحقيقية.

**خارج النطاق عمدًا:** الدفع من محفظة المراجِع الشخصية (بند موجود `insurance-review-claim-payout-from-reviewer-personal-wallet`)، `renew_subscription` المفتاح العشوائي المماثل (`renew_{id}_{uuid}` ~سطر 305)، `update_claim` بلا صرف.

**السلوك المتوقَّع بعد الإصلاح:** السيناريو A: الاستدعاء الثاني → 400/422 (`ValidationError`)، صفر حركة أموال. السيناريو B: → 400/422، الحالة تبقى `PAID`.

## 5. خطة التحقق الحي (قبل الإصلاح — لإثبات السلوك الحالي)

نفس انضباط جلسات اليوم: HTTP حقيقي، بيانات throwaway، لقطة قبل/بعد، تنظيف كامل.

**الإعداد (مباشرة في DB، لأن `submit_claim` مكسور — بند `insurance-submit-claim-500`):**
1. تينانت throwaway + 3 مستخدمين: `reviewer` (OWNER على كيان مُصدِر، محفظة MR_USDT = 500)، `claimant` (محفظة = 0)، ومستخدم ثالث لمطالبة السيناريو B.
2. كيان + `EntityMembership` (OWNER) للـreviewer، بوليصة (`max_coverage_limit_mrusdt=1000`)، اشتراكان ACTIVE.
3. مطالبتان `SUBMITTED`: C1 (`claimed=20`) للسيناريو A، C2 (`claimed=20`) للسيناريو B.
4. لقطة: أرصدة المحفظتين، عدد صفوف `transactions` و`invoices` للتينانت، صف C1/C2 كاملًا، محفظة user 1 (تأكيد عدم المساس).

**السيناريو A — approve مرتين (بلا هيدر `Idempotency-Key`):**
- `PUT /insurance/claims/C1/review?approve=true` ×2 متتاليين.
- **المتوقَّع حاليًا (لو الكود كما قرأته):** كلاهما 200؛ reviewer 500→480→460؛ claimant 0→20→40؛ صفّان في `transactions` بمفتاحين `claim_payout_C1_<مختلف>`؛ `payout_tx_hash` في C1 = hash التحويل **الثاني**.
- A2 (اختياري): نفس التجربة بهيدرين `Idempotency-Key` مختلفين — لإثبات أن الهيدر لا يحمي.

**السيناريو B — reject بعد PAID:**
- `approve=true` على C2 (→ PAID) ثم `approve=false`.
- **المتوقَّع حاليًا:** 200، `status=REJECTED` مع بقاء `approved_amount_mrusdt=20` و`payout_tx_hash` غير فارغ؛ لا حركة أموال في الاستدعاء الثاني.

**الإثبات:** ملف evidence `insurance-review-claim-double-payment-evidence-before.txt` (استجابات HTTP + أرصدة + صفوف `transactions`).

**بعد الإصلاح (عند الموافقة):** إعادة نفس السيناريوهين → الثاني 4xx، صفر حركة أموال إضافية + مسار المراجعة الأولى المشروع مطابق للسلوك قبل الإصلاح + اختبار regression دائم في `tests/`.

**التنظيف:** حذف التينانت وكل ما تحته + صفوف `transactions`/`invoices` المنشأة، ومقارنة لقطة الجداول zero-diff، ومحفظة user 1 بلا تغيير.

## 6. ملاحظات جانبية (لم تُصلَح — للتوثيق فقط)

- 🔴 **اكتشاف مُعلَّم (FLAGGED) — `approved_amount` سالب غير مرفوض → احتمال سرقة أموال من المطالِب بواسطة مراجِع خبيث.** اسم البند المقترح: `insurance-review-claim-negative-approved-amount-reverses-transfer`. **قرار المستخدم (2026-09-23):** أخطر محتملًا من الدفع المزدوج نفسه (سرقة متعمَّدة، لا مجرد عدم اتساق بيانات)؛ **جلسة منفصلة ضيقة بعد إغلاق إصلاح `review_claim` هذا؛ لا تحقيق إضافي في هذه الجلسة.**
  - **ما قُرئ فقط (غير مُجرَّب):**
    - `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`/`ge=0`.
    - `insurance/service.py:513-515` — `final_amount = approved_amount or claimed`؛ الـcap يقارن الحد الأعلى فقط (`> max_coverage_limit`)، لا حد أدنى.
    - `finance/service.py:90-113` (`transfer`) — لا فحص `amount > 0`. مع `amount=-50`: `sender_current < -50` خطأ (الرصيد غير السالب دائمًا أكبر) → الفحص يمر؛ `sender = current - (-50)` → **رصيد المراجِع يزيد 50**؛ `receiver = current + (-50)` → **رصيد المطالِب ينقص 50** — وقد يصبح سالبًا (لا فحص رصيد على المستلم).
    - ثم `status=PAID` و`approved_amount_mrusdt=-50` تُكتب على المطالبة، وفاتورة بمبلغ سالب.
  - **شرط الهجوم:** المهاجم يجب أن يكون OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة (فحص العضوية سطر 484-488) — أي مُصدِر تأمين خبيث يسرق من مشتركيه عبر "مراجعة" مطالباتهم.
  - **نطاق أوسع يجب فحصه في تلك الجلسة:** `FinanceService.transfer` مشترك بين كل الدومينات — أي نقطة استدعاء تمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّضة لنفس الانعكاس. وأيضًا `hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا.
  - **نقطة البداية للجلسة القادمة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`) لإثبات الانعكاس؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس في `transfer` نفسه (`amount <= 0 → ValidationError`، دفاع مركزي) + `gt=0` في الـrouter.
  - **ملاحظة ترتيب:** إصلاح هذه الجلسة (status guard) **لا يغلق** هذا المسار — المطالبة `SUBMITTED` ما زالت تقبل مراجعة أولى بمبلغ سالب.
- 🟡 `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`approved_amount or claimed`) → يُدفع المبلغ المطالَب به كاملًا.
- ⚪ مسار إعادة Redis (سطر 466-474) يُرجع المطالبة المخزَّنة **بلا فحص تينانت**، ومفتاح Redis غير مقيَّد بالتينانت. خطر منخفض (يحتاج معرفة مفتاح شخص آخر).
- ⚪ فشل `create_invoice` بعد `commit()` يُتبَع بـ`rollback()` — لا ضرر، لكن الدفعة تتم بلا فاتورة بصمت.

## 7. أسئلة طُرحت على المستخدم

1. تنفيذ خطة التحقق الحي (§5) كما هي؟
2. الإصلاح المقترح (§4) — وقرار: هل `APPROVED` حالة قابلة للمراجعة؟
3. معالجة `approved_amount` السالب: جلسة منفصلة (اقتراحي) أم ضمن هذه الجلسة؟

## 8. قرارات المستخدم (2026-09-23)

- **(أ) خطة التحقق الحي:** ✅ موافَق عليها كما وُصفت (السيناريو A وB، لقطة قبل/بعد، تنظيف zero-diff). التنفيذ **بعد** اطّلاع المستخدم على التقرير الكامل وإعطاء الموافقة النهائية.
- **(ب) `APPROVED`:** ✅ **غير قابلة لإعادة المراجعة** عبر `review_claim` (ولا `PAID`/`REJECTED`). الحالات القابلة للمراجعة = `SUBMITTED` و`UNDER_INVESTIGATION` فقط. أي تصحيح بعد ذلك يحتاج مسارًا منفصلًا للـsuperuser فقط، ليس هذا الـendpoint.
- **(ج) `approved_amount` السالب:** ✅ جلسة منفصلة ضيقة **بعد** إغلاق هذا الإصلاح؛ وُثِّق كاكتشاف مُعلَّم في §6 بتفاصيل كافية للاستئناف؛ لا تحقيق إضافي هنا.

**تسلسل التنفيذ المعتمَد (بعد الموافقة النهائية):** إثبات BEFORE حي → تطبيق الإصلاح → تحقق AFTER → فحص regression → عرض أوامر التنظيف قبل تشغيلها → كتابة الـdiff في هذا الملف → staging/commit فقط بعد موافقة صريحة.

**الحالة:** ⏸️ بانتظار الموافقة النهائية من المستخدم.

---

## 9. الكود الحالي الحرفي لـ`review_claim` (بأرقام الأسطر — HEAD `44f1d0e`، بلا تعديلات في شجرة العمل)

### 9.1 `eppne-backend/app/domains/insurance/service.py:452-575` (+ 576-578 رأس القسم التالي للسياق)

```python
 452      async def review_claim(
 453          self,
 454          claim_id: int,
 455          reviewer_id: int,
 456          tenant_id: int,
 457          approve: bool,
 458          approved_amount: Optional[Decimal] = None,
 459          notes: Optional[str] = None,
 460          idempotency_key: Optional[str] = None
 461      ) -> InsuranceClaim:
 462          """مراجعة مطالبة تعويض مع صرف التعويض في حال الموافقة."""
 463          await self._check_saas_limits(tenant_id, "insurance")
 464  
 465          # 1. التحقق من Idempotency
 466          if idempotency_key:
 467              cached = await self._validate_idempotency(idempotency_key)
 468              if cached is not None:
 469                  claim_id_cached = cached.get("claim_id")
 470                  if claim_id_cached:
 471                      claim = await self.repo.get_claim(claim_id_cached)
 472                      if claim:
 473                          return claim
 474                  raise ValidationError("Idempotency record exists but claim not found.")
 475  
 476          claim = await self.repo.get_claim(claim_id)
 477          if not claim or cast(int, claim.tenant_id) != tenant_id:  # type: ignore
 478              raise NotFoundError("Claim not found")
 479  
 480          subscription = await self.repo.get_subscription(claim.subscription_id)  # type: ignore
 481          policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore
 482  
 483          member = await self.membership.get_member(
 484              entity_type=ENTITY_TYPE, entity_id=cast(int, policy.issuer_entity_id),  # type: ignore
 485              user_id=reviewer_id,
 486          )
 487          if member is None or member.role not in [EntityMembershipRole.OWNER, EntityMembershipRole.EXECUTIVE_DIRECTOR]:
 488              raise PermissionDeniedError("Not authorized to review this claim")
 489  
 490          # AI Review
 491          ai_service = AIAgentsService(self.db, tenant_id)
 492          try:
 493              ai_result = await ai_service.execute_agent_action(
 494                  agent_id=10,
 495                  action_type="ANALYZE_SENSOR",
 496                  payload={
 497                      "claim_id": claim_id,
 498                      "claimed_amount": float(claim.claimed_amount_mrusdt),  # type: ignore
 499                      "evidence_urls": claim.evidence_urls  # type: ignore
 500                  },
 501                  executor_user_id=reviewer_id,
 502                  idempotency_key=cast(str, idempotency_key)
 503              )
 504              logger.info(f"AI claim review: {ai_result}")
 505          except Exception as e:
 506              logger.warning(f"AI claim review failed: {e}")
 507  
 508          finance = FinanceService(self.db, tenant_id)
 509          invoice_service = InvoicingService(self.db, tenant_id)
 510          # 🔥 معاملة ذرية للموافقة والصرف
 511          async with self.db.begin_nested():
 512              if approve:
 513                  final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
 514                  if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
 515                      final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore
 516  
 517                  payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
 518                  payout_tx = await finance.transfer(
 519                      sender_id=reviewer_id,
 520                      receiver_email=await self._get_user_email(claim.claimant_user_id, tenant_id),  # type: ignore
 521                      currency="MR_USDT",
 522                      amount=final_amount,
 523                      notes=f"Insurance claim payout for {cast(Any, policy).name}",
 524                      idempotency_key=payment_idempotency
 525                  )
 526  
 527                  claim = await self.repo.update_claim(
 528                      claim_id,
 529                      status=ClaimStatus.PAID,
 530                      approved_amount_mrusdt=final_amount,
 531                      payout_tx_hash=cast(str, payout_tx.tx_hash),
 532                      investigation_notes=notes
 533                  )
 534              else:
 535                  claim = await self.repo.update_claim(
 536                      claim_id,
 537                      status=ClaimStatus.REJECTED,
 538                      investigation_notes=notes
 539                  )
 540  
 541          await self.db.commit()
 542  
 543          if approve:
 544              try:
 545                  await invoice_service.create_invoice(  # type: ignore
 546                      entity_id=tenant_id,
 547                      user_id=claim.claimant_user_id,  # type: ignore
 548                      amount=final_amount,
 549                      description=f"Insurance claim payout: {cast(Any, policy).name}",
 550                      due_date=datetime.utcnow()
 551                  )
 552              except Exception as e:
 553                  await self.db.rollback()
 554                  logger.error(f"Invoice creation failed for insurance claim payout {claim_id}: {e}")
 555  
 556          await self.event_bus.publish("insurance.claim.resolved", {
 557              "claim_id": claim.id,
 558              "tenant_id": tenant_id,
 559              "status": claim.status.value if hasattr(claim.status, 'value') else str(claim.status),  # type: ignore
 560              "amount": float(claim.approved_amount_mrusdt)  # type: ignore
 561          })
 562  
 563          await audit_log(
 564              user_id=reviewer_id,
 565              tenant_id=tenant_id,  # type: ignore
 566              action="INSURANCE_CLAIM_REVIEWED",
 567              resource_id=claim.id,  # type: ignore
 568              details={"approved": approve, "amount": float(final_amount) if approve else 0}
 569          )
 570  
 571          # تخزين معرف المطالبة فقط
 572          if idempotency_key:
 573              await self._store_idempotency(idempotency_key, {"claim_id": claim.id})
 574  
 575          return claim
 576  
 577      # ============================================================
 578      # 4. المعاشات (Pensions)
```

### 9.2 `eppne-backend/app/domains/insurance/repository.py:117-119` و`:136-139` (جلب/تحديث المطالبة — بلا قفل)

```python
 117      async def get_claim(self, claim_id: int) -> Optional[InsuranceClaim]:
 118          result = await self.db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))  # type: ignore
 119          return result.scalar_one_or_none()
...
 136      async def update_claim(self, claim_id: int, **kwargs) -> InsuranceClaim:
 137          await self.db.execute(update(InsuranceClaim).where(InsuranceClaim.id == claim_id).values(**kwargs))  # type: ignore
 138          await self.db.flush()
 139          return await self.get_claim(claim_id)
```

### 9.3 `eppne-backend/app/domains/insurance/router.py:219-241`

```python
 219  
 220  @router.put("/claims/{claim_id}/review", response_model=InsuranceClaimResponse)
 221  @rate_limit(max_requests=10, window_seconds=60)
 222  async def review_claim(
 223      claim_id: int,
 224      approve: bool = Query(..., description="true للموافقة، false للرفض"),
 225      approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
 226      notes: Optional[str] = Query(None, description="ملاحظات المراجعة"),
 227      idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
 228      current_user: User = Depends(get_current_active_user),
 229      db: AsyncSession = Depends(get_db)
 230  ):
 231      tenant_id = cast(int, current_user.tenant_id)
 232      service = InsuranceService(db)
 233      claim = await service.review_claim(
 234          claim_id=claim_id,
 235          reviewer_id=cast(int, current_user.id),
 236          tenant_id=tenant_id,
 237          approve=approve,
 238          approved_amount=approved_amount,
 239          notes=notes,
 240          idempotency_key=idempotency_key
 241      )
```

### 9.4 `eppne-backend/app/domains/finance/service.py:58-75` (حماية التكرار الوحيدة في `transfer`)

```python
  58      async def transfer(
  59          self,
  60          sender_id: int,
  61          receiver_email: str,
  62          currency: str,
  63          amount: Decimal,
  64          idempotency_key: str,
  65          notes: Optional[str] = None,
  66          ip: Optional[str] = None,
  67          ua: Optional[str] = None
  68      ):
  69          if not idempotency_key:
  70              raise ValidationError("Idempotency key is required")
  71  
  72          existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
  73          if existing_tx:
  74              logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
  75              return existing_tx
```

## 10. [⚠️ نسخة أولى — أُلغيت بـ§12] الـdiff المقترح الحرفي (لم يُطبَّق — مُولَّد على نسخ في scratchpad، `py_compile` نجح، نهايات أسطر CRLF محفوظة)

ملفان فقط: `repository.py` (+10) و`service.py` (+14 / −1). لا migration، لا تغيير في الـrouter ولا في `finance`.

```diff
--- a/eppne-backend/app/domains/insurance/repository.py
+++ b/eppne-backend/app/domains/insurance/repository.py
@@ -118,6 +118,16 @@
         result = await self.db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))  # type: ignore
         return result.scalar_one_or_none()
 
+    async def get_claim_for_update(self, claim_id: int) -> Optional[InsuranceClaim]:
+        # SELECT ... FOR UPDATE + populate_existing: يقفل الصف لحد commit ويقرأ الحالة
+        # الحالية من الـDB حتى لو الكائن موجود بالفعل في identity map
+        result = await self.db.execute(
+            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)  # type: ignore
+            .with_for_update()
+            .execution_options(populate_existing=True)
+        )
+        return result.scalar_one_or_none()
+
     async def list_claims_for_subscription(self, subscription_id: int) -> List[InsuranceClaim]:
         result = await self.db.execute(
             select(InsuranceClaim).where(InsuranceClaim.subscription_id == subscription_id)  # type: ignore
--- a/eppne-backend/app/domains/insurance/service.py
+++ b/eppne-backend/app/domains/insurance/service.py
@@ -30,6 +30,8 @@
 from app.domains.identity.models import User
 
 ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py
+# review_claim يقبل فقط مطالبات لم تُحسَم بعد؛ APPROVED/PAID/REJECTED نهائية لهذا المسار
+REVIEWABLE_CLAIM_STATUSES = {ClaimStatus.SUBMITTED, ClaimStatus.UNDER_INVESTIGATION}
 
 
 class InsuranceService:
@@ -476,6 +478,9 @@
         claim = await self.repo.get_claim(claim_id)
         if not claim or cast(int, claim.tenant_id) != tenant_id:  # type: ignore
             raise NotFoundError("Claim not found")
+        # فحص مبكر (بلا قفل) قبل مراجعة AI — الفحص الحاسم تحت القفل أدناه
+        if claim.status not in REVIEWABLE_CLAIM_STATUSES:
+            raise ValidationError(f"Claim already reviewed (status={claim.status.value})")  # type: ignore
 
         subscription = await self.repo.get_subscription(claim.subscription_id)  # type: ignore
         policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore
@@ -509,12 +514,19 @@
         invoice_service = InvoicingService(self.db, tenant_id)
         # 🔥 معاملة ذرية للموافقة والصرف
         async with self.db.begin_nested():
+            # قفل صف المطالبة وإعادة فحص الحالة: يمنع الدفع المزدوج (طلبين متتاليين أو متزامنين)
+            # ويمنع تحويل مطالبة PAID إلى REJECTED
+            locked_claim = await self.repo.get_claim_for_update(claim_id)
+            if locked_claim is None or locked_claim.status not in REVIEWABLE_CLAIM_STATUSES:
+                raise ValidationError("Claim already reviewed")
+
             if approve:
                 final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
                 if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
                     final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore
 
-                payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
+                # مفتاح حتمي لكل مطالبة: حماية transfer من التكرار تشتغل فعلًا
+                payment_idempotency = f"claim_payout_{claim_id}"
                 payout_tx = await finance.transfer(
                     sender_id=reviewer_id,
                     receiver_email=await self._get_user_email(claim.claimant_user_id, tenant_id),  # type: ignore
```

### 10.1 ملاحظات التصميم

- **فحصان للحالة، لا واحد:** (أ) فحص مبكر بلا قفل بعد فحص التينانت مباشرة → يرفض الإعادة **قبل** استدعاء مراجعة AI (لا استهلاك agent ولا أثر جانبي)؛ (ب) الفحص **الحاسم** تحت `SELECT ... FOR UPDATE` داخل `begin_nested()` → يغلق السباق بين طلبين متزامنين (الثاني ينتظر القفل حتى `commit()` سطر 541، ثم يقرأ `PAID` فيُرفض).
- **لماذا القفل داخل `begin_nested()` لا عند سطر 476:** لتجنّب إمساك قفل الصف طوال استدعاء AI (مسار خارجي قد يكون بطيئًا، وقد يعمل commit داخليًا فيُسقط القفل أصلًا).
- **`populate_existing=True` ضروري:** `get_claim` (سطر 476) حمّل الكائن في identity map؛ بدونه يُرجع `SELECT ... FOR UPDATE` نفس الكائن بحالته **القديمة** (نفس فئة باج الـidentity-map staleness المُكتشَف في جلسة guardian).
- **مفتاح الدفع الحتمي `claim_payout_{claim_id}`:** حزام أمان ثانٍ — لو تجاوز أي مسار مستقبلي الـguard، `transfer` يُرجع التحويل الموجود (سطر 72-75) أو يفشل الإدراج على الفهرس الفريد. `uuid` يبقى مستوردًا (مستخدَم في أسطر 216، 242، 243، 305).
- **الخطأ المُرجَع:** `ValidationError` → **422** (مستورد أصلًا في الملف). بديل ممكن: 409 — لكن الموجود في `app/core/errors.py` بـ409 هو `AlreadyExistsError` و`IdempotencyError` واسماهما مضلِّلان هنا؛ اخترت 422 لتقليل الاستيرادات. قابل للتغيير بقرارك.
- **مسار إعادة Redis (466-474) لم يُمَس:** إعادة بنفس الهيدر ما زالت تُرجع المطالبة المخزَّنة 200 (سلوك idempotent صحيح).
- **الإصلاح لا يغطي:** `approved_amount` السالب (§6/§11)، الدفع من محفظة المراجِع، `renew_subscription`.

## 11. تفاصيل التأكيد للنقطة (ج) — `approved_amount` السالب (للجلسة المنفصلة؛ قراءة فقط، غير مُجرَّب)

الأسطر الحرفية التي بُني عليها الاستنتاج في §6:

**(1) الـrouter — لا قيد على الإشارة:** `insurance/router.py:225`

```python
 225      approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
```

**(2) الخدمة — cap للحد الأعلى فقط، ولا حد أدنى:** `insurance/service.py:513-515`

```python
 513                  final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
 514                  if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
 515                      final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore
```

**(3) `transfer` — لا فحص `amount > 0`، والحساب يعكس الاتجاه مع مبلغ سالب:** `finance/service.py:90-116`

```python
  90          amount_decimal = Decimal(str(amount))
  91  
  92          async with self.db.begin_nested():
  93              first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
  94              first_wallet = await self.get_or_create_wallet_for_update(first_id)
  95              second_wallet = await self.get_or_create_wallet_for_update(second_id)
  96  
  97              sender_wallet = first_wallet if first_id == sender_id else second_wallet
  98              receiver_wallet = second_wallet if second_id == receiver.id else first_wallet
  99  
 100              # 🛠️ تجاهل خطأ Pylance باستخدام # type: ignore
 101              if cast(bool, sender_wallet.is_frozen):  # type: ignore
 102                  raise PermissionDeniedError("محفظتك مجمدة. يرجى التواصل مع الدعم.")
 103              if cast(bool, receiver_wallet.is_frozen):  # type: ignore
 104                  raise PermissionDeniedError("محفظة المستلم مجمدة.")
 105  
 106              sender_balances = getattr(sender_wallet, "balances", {}).copy()
 107              sender_current = Decimal(str(sender_balances.get(currency, 0)))
 108              if sender_current < amount_decimal:
 109                  raise InsufficientBalanceError(f"رصيد غير كافٍ من {currency}")
 110  
 111              sender_balances[currency] = float(sender_current - amount_decimal)
 112              receiver_balances = getattr(receiver_wallet, "balances", {}).copy()
 113              receiver_balances[currency] = float(Decimal(str(receiver_balances.get(currency, 0))) + amount_decimal)
 114  
 115              await self.wallet_repo.update_balances(cast(int, sender_wallet.id), sender_balances)
 116              await self.wallet_repo.update_balances(cast(int, receiver_wallet.id), receiver_balances)
```

**التتبّع بمبلغ `-50` (من القراءة):** سطر 108 `sender_current < -50` → False لأي رصيد ≥ 0 → لا `InsufficientBalanceError`؛ سطر 111 رصيد المراجِع = `current + 50`؛ سطر 113 رصيد المطالِب = `current - 50` (بلا أي فحص → قد يصبح سالبًا)؛ ثم في `review_claim` تُكتب `status=PAID` و`approved_amount_mrusdt=-50`، وفاتورة بمبلغ سالب (سطر 545).

**حالة هذا البند:** 🔴 مُعلَّم، **غير مُتحقَّق حيًا**، مؤجَّل لجلسة ضيقة منفصلة بعد إغلاق هذا الإصلاح (قرار المستخدم ج). نقطة البداية مكتوبة في §6.

---

## 12. [2026-09-23 — تحديث] قرار رمز الحالة 409 + الـdiff النهائي الكامل + توضيح `populate_existing`

**هذا القسم يلغي ويحلّ محل الـdiff في §10** (الذي كان يستخدم `ValidationError`/422). لم يُلمَس أي كود حقيقي — الـdiff مُولَّد على نسخ في scratchpad فقط.

### 12.1 قرار المستخدم: 409 باستثناء جديد

- **القرار:** رفض "المطالبة ليست في حالة قابلة للمراجعة" يُرجع **409**، باستثناء **جديد** — لا `AlreadyExistsError` ولا `IdempotencyError` (كلاهما مضلِّل).
- **الاسم:** `ClaimStatusConflictError` — مطابق لنمط `app/core/errors.py`: `<Noun><Kind>Error`، يرث `SovereignError`، `__init__(self, message: str = "<رسالة عربية افتراضية>")` ثم `super().__init__(message, status_code=...)`. أضفتُ `code="CLAIM_STATUS_CONFLICT"` بنفس أسلوب `IdempotencyError`/`RateLimitError`/`QuotaExceededError`/`AISystemSuspendedError` (بدونه يصبح `code` تلقائيًا اسم الكلاس — `SovereignError.__init__`).
- **الموضع:** قسم `# 6. أخطاء القطاعات (مخصصة)` بعد `VoiceAssistantError` مباشرة (قسم الأخطاء الخاصة بالقطاعات؛ `CarbonSettlementError` سابقة).
- **الربط بـHTTP:** مُتحقَّق — `app/main.py:110-115` معالج `SovereignError` العام يُرجع `status_code=exc.status_code` و`{"detail", "code"}` → لا حاجة لمعالج جديد. الاسم غير مستخدَم حاليًا في أي مكان (grep = 0).
- **`ValidationError` يبقى مستوردًا في `service.py`** — ما زال مستخدَمًا (مثلًا سطر 474 في `review_claim` نفسه، وأماكن أخرى).

### 12.2 الـdiff النهائي الحرفي الكامل (3 ملفات)

| الملف | التغيير |
|---|---|
| `app/core/errors.py` | **+5** (الكلاس الجديد + سطر فارغ) |
| `app/domains/insurance/repository.py` | **+10** (`get_claim_for_update`) |
| `app/domains/insurance/service.py` | **+14 / −2** — تصحيح: §10 والترمينال قالا "+14/−1" وهذا كان **خطأ عدّ مني**؛ النسخة الأولى كانت فعليًا **+13/−1** (السطر الفارغ المضاف لم يُعَدّ). الآن: +1 سطر استيراد مُعاد كتابته (و−1 للقديم)، +2 الثابت، +3 الفحص المبكر، +6 كتلة القفل (شاملًا سطرًا فارغًا)، +2 المفتاح الحتمي (و−1 للقديم) = **+14/−2** (مُتحقَّق بالعدّ على الـdiff) |

نهايات الأسطر محفوظة كما في الأصل (CRLF في الملفات الثلاثة، مُتحقَّق بالعدّ). `py_compile` نجح على الثلاثة.

```diff
--- a/eppne-backend/app/core/errors.py
+++ b/eppne-backend/app/core/errors.py
@@ -97,6 +97,11 @@
     def __init__(self, message: str = "فشل في معالجة الأمر الصوتي"):
         super().__init__(message, status_code=500)
 
+class ClaimStatusConflictError(SovereignError):
+    """مطالبة تأمين ليست في حالة تسمح بالمراجعة (سبق حسمها: APPROVED/PAID/REJECTED)"""
+    def __init__(self, message: str = "المطالبة ليست في حالة قابلة للمراجعة"):
+        super().__init__(message, status_code=409, code="CLAIM_STATUS_CONFLICT")
+
 # ==========================================
 # 7. أخطاء الذكاء الاصطناعي
 # ==========================================
--- a/eppne-backend/app/domains/insurance/repository.py
+++ b/eppne-backend/app/domains/insurance/repository.py
@@ -118,6 +118,16 @@
         result = await self.db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))  # type: ignore
         return result.scalar_one_or_none()
 
+    async def get_claim_for_update(self, claim_id: int) -> Optional[InsuranceClaim]:
+        # SELECT ... FOR UPDATE + populate_existing: يقفل الصف لحد commit ويقرأ الحالة
+        # الحالية من الـDB حتى لو الكائن موجود بالفعل في identity map
+        result = await self.db.execute(
+            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)  # type: ignore
+            .with_for_update()
+            .execution_options(populate_existing=True)
+        )
+        return result.scalar_one_or_none()
+
     async def list_claims_for_subscription(self, subscription_id: int) -> List[InsuranceClaim]:
         result = await self.db.execute(
             select(InsuranceClaim).where(InsuranceClaim.subscription_id == subscription_id)  # type: ignore
--- a/eppne-backend/app/domains/insurance/service.py
+++ b/eppne-backend/app/domains/insurance/service.py
@@ -15,7 +15,7 @@
 from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 from app.domains.affiliate.service import AffiliateService
 from app.domains.invoicing.service import InvoicingService
-from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
+from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError, ClaimStatusConflictError
 from app.core.idempotency import get_idempotency_result, store_idempotency_result
 from app.core.audit import audit_log
 from app.core.event_bus import EventBus
@@ -30,6 +30,8 @@
 from app.domains.identity.models import User
 
 ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py
+# review_claim يقبل فقط مطالبات لم تُحسَم بعد؛ APPROVED/PAID/REJECTED نهائية لهذا المسار
+REVIEWABLE_CLAIM_STATUSES = {ClaimStatus.SUBMITTED, ClaimStatus.UNDER_INVESTIGATION}
 
 
 class InsuranceService:
@@ -476,6 +478,9 @@
         claim = await self.repo.get_claim(claim_id)
         if not claim or cast(int, claim.tenant_id) != tenant_id:  # type: ignore
             raise NotFoundError("Claim not found")
+        # فحص مبكر (بلا قفل) قبل مراجعة AI — الفحص الحاسم تحت القفل أدناه
+        if claim.status not in REVIEWABLE_CLAIM_STATUSES:
+            raise ClaimStatusConflictError(f"Claim already reviewed (status={claim.status.value})")  # type: ignore
 
         subscription = await self.repo.get_subscription(claim.subscription_id)  # type: ignore
         policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore
@@ -509,12 +514,19 @@
         invoice_service = InvoicingService(self.db, tenant_id)
         # 🔥 معاملة ذرية للموافقة والصرف
         async with self.db.begin_nested():
+            # قفل صف المطالبة وإعادة فحص الحالة: يمنع الدفع المزدوج (طلبين متتاليين أو متزامنين)
+            # ويمنع تحويل مطالبة PAID إلى REJECTED
+            locked_claim = await self.repo.get_claim_for_update(claim_id)
+            if locked_claim is None or locked_claim.status not in REVIEWABLE_CLAIM_STATUSES:
+                raise ClaimStatusConflictError("Claim already reviewed")
+
             if approve:
                 final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
                 if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
                     final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore
 
-                payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
+                # مفتاح حتمي لكل مطالبة: حماية transfer من التكرار تشتغل فعلًا
+                payment_idempotency = f"claim_payout_{claim_id}"
                 payout_tx = await finance.transfer(
                     sender_id=reviewer_id,
                     receiver_email=await self._get_user_email(claim.claimant_user_id, tenant_id),  # type: ignore
```

### 12.3 توضيح `populate_existing=True` — هل تحقّقتُ أن الخطر ينطبق على هذا المسار؟

**الجواب الصريح:** عند كتابة §10.1 كانت **عادة دفاعية منقولة من جلسة guardian** — لم أكن قد تحقّقتُ من شروطها في هذا المسار تحديدًا (لم أكن قد فحصتُ `expire_on_commit` ولا ما يفعله استدعاء AI بالجلسة). **الآن تحقّقتُ منها بقراءة الكود — وهي تنطبق فعلًا، لكن على مسار التزامن فقط، ولم تُثبَت بالتنفيذ.** التفاصيل:

**ما تحقّقتُ منه (قراءة كود + إعدادات):**
1. `review_claim` سطر 476 يحمّل المطالبة عبر `get_claim` → الكائن يدخل identity map الخاص بالجلسة بالحالة التي كانت وقت القراءة.
2. `app/core/database.py:27-30` — `async_sessionmaker(..., expire_on_commit=False)` → **الـcommit لا يُبطل الكائنات المحمّلة**.
3. `ai_agents/service.py::execute_agent_action` (سطر 148+) يستدعي `self.db.commit()` (سطر 227 في مسار الخطأ، 230 في مسار النجاح) **على نفس الجلسة** (`AIAgentsService(self.db, ...)` في `review_claim` سطر ~493). فبين سطر 476 والقفل داخل `begin_nested()` يحدث commit — لكن بسبب (2) الكائن **لا يُحدَّث**.
4. سلوك SQLAlchemy الموثَّق: عندما يُرجع `SELECT` صفًا مفتاحه موجود في identity map، **لا يكتب فوق** سمات الكائن الموجود إلا إذا كان منتهيًا (expired) أو طُلب `populate_existing`.

**السيناريوهات:**
- **طلبان متتاليان (السيناريو A في خطة التحقق):** كل طلب HTTP له جلسة جديدة → الطلب الثاني يقرأ `PAID` من الـDB في سطر 476 → **الفحص المبكر يرفضه**. هنا `populate_existing` **غير لازم** والخطر لا ينطبق.
- **طلبان متزامنان (سباق):** الطلب 2 يقرأ سطر 476 بينما الطلب 1 لم يعمل commit بعد → كائنه `SUBMITTED` → يمرّ الفحص المبكر → ينتظر `FOR UPDATE` → بعد commit الطلب 1 يعود الصف من الـDB بحالة `PAID`، **لكن بدون `populate_existing` يُرجع SQLAlchemy نفس الكائن بسمة `SUBMITTED` القديمة** → الفحص الحاسم يمرّ خطأً. هنا الخطر **ينطبق فعلًا** على هذا المسار (بسبب 1+2+4؛ و3 يؤكد أن الكائن لا يُبطَل حتى بالـcommit الوسيط).
  - حتى في هذه الحالة، المفتاح الحتمي `claim_payout_{claim_id}` يعمل كحزام ثانٍ: `transfer` سيجد التحويل الموجود (سطر 72-75) فيُرجعه بلا دفع ثانٍ — لكن المطالبة ستُحدَّث مرة ثانية (فاتورة ثانية، حدث ثانٍ، audit ثانٍ). لذا `populate_existing` هو ما يجعل الفحص الحاسم صحيحًا، والمفتاح شبكة أمان فقط.

**التصنيف النهائي:** **خطر مُتحقَّق منه بالقراءة لهذا المسار (مسار التزامن)**، أصله عادة من جلسة guardian، **غير مُثبَت بالتنفيذ**. خطة التحقق الحي المعتمَدة (§5) تختبر الطلبات المتتالية فقط، **فلن تُمرّن هذا الفرع**. اقتراح (يحتاج موافقتك، ليس ضمن الخطة المعتمَدة): إضافة اختبار تزامن في مرحلة AFTER — طلبان `approve=true` عبر `asyncio.gather` بجلستين منفصلتين — والتحقق من دفعة واحدة فقط ورفض الثاني بـ409. (ملاحظة: `asyncio.gather` هنا آمن لأنه على جلستين مستقلتين، بخلاف سابقة `projects/service.py` التي كانت على جلسة واحدة.)

**ملاحظة جانبية ناتجة (للعلم فقط):** الـcommit داخل `execute_agent_action` يعني أن `review_claim` **ليس معاملة واحدة** أصلًا — كل ما قبل استدعاء AI يُثبَّت قبل منطق الدفع. لا يؤثر على هذا الإصلاح (القفل يُؤخذ بعد استدعاء AI عمدًا)، لكنه سبب إضافي لعدم أخذ القفل عند سطر 476: الـcommit الوسيط كان سيُسقطه.

**الحالة:** ⏸️ بانتظار مراجعة المستخدم والموافقة النهائية لبدء اختبار BEFORE الحي. لم يُلمَس أي كود.

---

## 13. [2026-09-23] إثبات BEFORE الحي — على الكود الحالي غير المُصلَح

**الموافقة:** المستخدم وقّع نهائيًا على §12.2 (الـdiff) + 409/`ClaimStatusConflictError` + منطق `populate_existing`، وأضاف **السيناريو C** (تزامن حقيقي عبر `asyncio.gather` بجلستين منفصلتين) لمرحلة AFTER. الترتيب المعتمَد: BEFORE → تطبيق الـdiff → AFTER (A+B+C) → regression → عرض أوامر التنظيف قبل التشغيل → الـdiff والأدلة في التقرير → توقف قبل أي staging/commit. **المستخدم طلب التوقف للمراجعة بعد BEFORE.**

### 13.1 البيئة وحالة الكود

- **الكود:** HEAD بلا أي تعديل (`git status` على `insurance/` و`core/errors.py` = فارغ) — أي السلوك الحالي في الإنتاج.
- `uvicorn app.main:app` محلي على `127.0.0.1:8000` (أُوقف بعد الانتهاء)، DB `eppne_v2` (`eppne_db`، `localhost:5435`)، Redis `6380`.
- **لقطة baseline** قبل أي زرع: 259 جدولًا (`baseline_before.json` في scratchpad) + محفظة user 1 = `39|1|710.0`.
- **تأكيد الفهرس في DB الحية (§12.2 وعد به):** `\d transactions` → `"ix_transactions_idempotency_key" UNIQUE, btree (idempotency_key)` ✅ (فريد كامل، ليس جزئيًا كما في الموديل — أقوى، والنتيجة نفسها).
- **البيانات الـthrowaway** (سكربت `setup_rc.py` معدَّل من سكربت Batch 0-A): تينانت **130** (`TMPRC_TENANT_f4a3da`)؛ `reviewer`=13786 (SUPER_ADMIN، OWNER على الكيان 1177، محفظة MR_USDT=500)؛ `claimant`=13787 و`claimant2`=13788 (محفظتان=0)؛ بوليصة 665 (`max_coverage=1000`)؛ اشتراكان 368/369 ACTIVE؛ **5 مطالبات `SUBMITTED` بـ20 لكلٍّ:** C1=174 (A-before)، C2=175 (B-before)، C3=176 (A-after)، C4=177 (B-after)، C5=178 (C-after). صف SaaS (خطة 101) للتينانت.
- كل الاستدعاءات **HTTP حقيقي** بتوكن `reviewer` الحقيقي، **بلا هيدر `Idempotency-Key`**.

### 13.2 السيناريو A — `approve=true` مرتين على C1 (174)

| النقطة | HTTP | reviewer | claimant | المطالبة | صفوف `transactions` | فواتير التينانت |
|---|---|---|---|---|---|---|
| البداية | — | 500 | 0 | `SUBMITTED`، 0، hash فارغ | 0 | 0 |
| بعد الاستدعاء 1 | **200** `PAID` | **480** | **20** | `PAID`، 20، `TX-63F260DEA6C3` | 1: #942 مفتاح `claim_payout_174_84e16ed10d0e` | 1 (20) |
| بعد الاستدعاء 2 | **200** `PAID` | **460** | **40** | `PAID`، 20، **`TX-F4E2E3721A14`** (استُبدل) | **2**: #942 + **#943 مفتاح `claim_payout_174_b480007bcf58`** | **2 (40)** |

**النتيجة: ✅ الدفع المزدوج مُثبَت حيًا.** مطالبة بـ20 دُفعت **40**. المفتاحان مختلفان (uuid عشوائي، §2.2) فلم تتعرّف حماية `transfer`. وسجل المطالبة يشير الآن للتحويل **الثاني فقط** — التحويل الأول (#942) لم يعد مرئيًا من المطالبة. فاتورة ثانية أيضًا.

### 13.3 السيناريو B — `approve=true` ثم `approve=false` على C2 (175)

| النقطة | HTTP | reviewer | claimant2 | المطالبة | صفوف `transactions` |
|---|---|---|---|---|---|
| البداية | — | 460 | 0 | `SUBMITTED`، 0، فارغ | 0 |
| بعد approve | **200** `PAID` | 440 | 20 | `PAID`، 20، `TX-F04C4D93D45A` | 1: #944 |
| بعد reject | **200** `REJECTED` | 440 | 20 | **`REJECTED`، 20، `TX-F04C4D93D45A`** | 1 (بلا تغيير) |

**النتيجة: ✅ الحالة غير المتسقة مُثبَتة حيًا.** الـreject على مطالبة `PAID` نجح 200؛ المطالبة الآن `REJECTED` بينما الأموال مدفوعة فعلًا، ومعها `approved_amount=20` و`payout_tx_hash` للدفعة. لا حركة أموال في الاستدعاء الثاني (كما توقّع §3.2).

### 13.4 ما لم يُشغَّل (بصدق)

- **A2** (هيدرا `Idempotency-Key` مختلفان) — كان "اختياريًا" في §5؛ **لم يُشغَّل** للحفاظ على المطالبات C3–C5 لمرحلة AFTER. الاستنتاج من الكود (§2.3) قائم لكنه غير مُثبَت حيًا.
- **السيناريو C** (التزامن) — **لم يُشغَّل على الكود القديم**؛ المستخدم طلبه لمرحلة AFTER فقط. (لو أردتَ إثبات أن السباق يدفع مرتين قبل الإصلاح أيضًا، أحتاج مطالبة إضافية — قرارك.)

### 13.5 سلامة المحيط

- محفظة user 1: `710.0` في البداية والنهاية ✅.
- لوج السيرفر: لا أخطاء متعلقة بـ`review_claim`. الأخطاء الموجودة هي أخطاء بدء التشغيل المعروفة (فهارس `user_id` + `InFailedSQLTransactionError`) وأخطاء ترميز cp1256 في الـlogging — البند الموجود `server-startup-index-creation-failure-and-cp1256-logging-errors`. تحذيرات "طلب بطيء" (2.6–18 ثانية) لكل استدعاء review (مسار AI + الفاتورة).
- **الحالة الحالية للبيانات:** تينانت 130 **باقٍ** عمدًا (C3/C4/C5 `SUBMITTED` لازمة لـAFTER). صفوف `transactions` #942/#943/#944 و3 فواتير موجودة. التنظيف في نهاية الجلسة بعد عرض الأوامر عليك.

**الأدلة الخام الكاملة:** `.claude/reports/insurance-review-claim-double-payment-evidence-before.txt`

**الحالة:** ⏸️ BEFORE مكتمل — **متوقف لمراجعة المستخدم قبل تطبيق الـdiff (§12.2).** لم يُلمَس أي كود.

---

## 14. [2026-09-23] تطبيق الإصلاح + تحقق AFTER + regression + التنظيف

### 14.4 أوامر التنظيف — مكتوبة هنا **قبل** تشغيلها (بموافقة المستخدم المسبقة على التنظيف في نفس الرسالة)

```bash
# 1) صفوف transactions (الجدول بلا عمود tenant_id فلا يغطيه cleanup.py) — الـ6 صفوف المنشأة في الجلسة فقط، مقيّدة بالـid والمفتاح معًا
docker exec eppne_db psql -U eppne -d eppne_v2 -c "DELETE FROM transactions WHERE id IN (942,943,944,945,946,947) AND idempotency_key LIKE 'claim_payout_17%';"   # متوقَّع: DELETE 6
# 2) كل صفوف تينانت 130 في كل جدول فيه tenant_id (users/wallets/insurance_*/invoices/audit/memberships/saas/...) ثم صف التينانت نفسه — نفس سكربت Batch 0-A
venv/Scripts/python.exe <scratchpad>/cleanup.py 130
# 3) لقطة بعد التنظيف ومقارنتها بلقطة baseline (259 جدولًا + محفظة user 1)
venv/Scripts/python.exe <scratchpad>/snapshot.py <scratchpad>/baseline_after_cleanup.json
python -c "compare baseline_before.json vs baseline_after_cleanup.json"   # متوقَّع: zero-diff
```

- Redis: فُحص — **صفر مفاتيح** تطابق `*TMPRC*` (لا شيء لتنظيفه هناك).
- السيرفر `uvicorn` أُوقف قبل التنظيف (pid 15460، تأكيد عبر `netstat`).

### 14.1 الإصلاح المطبَّق — `git diff` الحرفي الكامل (الشجرة الحالية)

طُبِّق بنسخ ملفات scratchpad المعتمَدة فوق الأصلية بعد التأكد (`cmp`) أن الأصلية مطابقة بايت-ببايت لنسخة "قبل". `git diff --stat`: **3 ملفات، +29 / −2** (errors +5، repository +10، service +14/−2). مقارنة أسطر +/− للـ`git diff` الفعلي مع §12.2 المعتمَد = **مطابقة تامة**. نهايات أسطر CRLF محفوظة (لا churn في الـstat). `py_compile` نجح.

```diff
diff --git a/eppne-backend/app/core/errors.py b/eppne-backend/app/core/errors.py
index c72a2e4..b745478 100644
--- a/eppne-backend/app/core/errors.py
+++ b/eppne-backend/app/core/errors.py
@@ -97,6 +97,11 @@ class VoiceAssistantError(SovereignError):
     def __init__(self, message: str = "فشل في معالجة الأمر الصوتي"):
         super().__init__(message, status_code=500)
 
+class ClaimStatusConflictError(SovereignError):
+    """مطالبة تأمين ليست في حالة تسمح بالمراجعة (سبق حسمها: APPROVED/PAID/REJECTED)"""
+    def __init__(self, message: str = "المطالبة ليست في حالة قابلة للمراجعة"):
+        super().__init__(message, status_code=409, code="CLAIM_STATUS_CONFLICT")
+
 # ==========================================
 # 7. أخطاء الذكاء الاصطناعي
 # ==========================================
diff --git a/eppne-backend/app/domains/insurance/repository.py b/eppne-backend/app/domains/insurance/repository.py
index a307516..98148f3 100644
--- a/eppne-backend/app/domains/insurance/repository.py
+++ b/eppne-backend/app/domains/insurance/repository.py
@@ -118,6 +118,16 @@ class InsuranceRepository:
         result = await self.db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))  # type: ignore
         return result.scalar_one_or_none()
 
+    async def get_claim_for_update(self, claim_id: int) -> Optional[InsuranceClaim]:
+        # SELECT ... FOR UPDATE + populate_existing: يقفل الصف لحد commit ويقرأ الحالة
+        # الحالية من الـDB حتى لو الكائن موجود بالفعل في identity map
+        result = await self.db.execute(
+            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)  # type: ignore
+            .with_for_update()
+            .execution_options(populate_existing=True)
+        )
+        return result.scalar_one_or_none()
+
     async def list_claims_for_subscription(self, subscription_id: int) -> List[InsuranceClaim]:
         result = await self.db.execute(
             select(InsuranceClaim).where(InsuranceClaim.subscription_id == subscription_id)  # type: ignore
diff --git a/eppne-backend/app/domains/insurance/service.py b/eppne-backend/app/domains/insurance/service.py
index 992fa6d..99d86a7 100644
--- a/eppne-backend/app/domains/insurance/service.py
+++ b/eppne-backend/app/domains/insurance/service.py
@@ -15,7 +15,7 @@ from app.domains.ai_agents.service import AIAgentsService
 from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 from app.domains.affiliate.service import AffiliateService
 from app.domains.invoicing.service import InvoicingService
-from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
+from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError, ClaimStatusConflictError
 from app.core.idempotency import get_idempotency_result, store_idempotency_result
 from app.core.audit import audit_log
 from app.core.event_bus import EventBus
@@ -30,6 +30,8 @@ from app.domains.insurance.models import (
 from app.domains.identity.models import User
 
 ENTITY_TYPE = "SOVEREIGN_ENTITY"  # نفس القيمة المستخدَمة في sovereign_entities/service.py
+# review_claim يقبل فقط مطالبات لم تُحسَم بعد؛ APPROVED/PAID/REJECTED نهائية لهذا المسار
+REVIEWABLE_CLAIM_STATUSES = {ClaimStatus.SUBMITTED, ClaimStatus.UNDER_INVESTIGATION}
 
 
 class InsuranceService:
@@ -476,6 +478,9 @@ class InsuranceService:
         claim = await self.repo.get_claim(claim_id)
         if not claim or cast(int, claim.tenant_id) != tenant_id:  # type: ignore
             raise NotFoundError("Claim not found")
+        # فحص مبكر (بلا قفل) قبل مراجعة AI — الفحص الحاسم تحت القفل أدناه
+        if claim.status not in REVIEWABLE_CLAIM_STATUSES:
+            raise ClaimStatusConflictError(f"Claim already reviewed (status={claim.status.value})")  # type: ignore
 
         subscription = await self.repo.get_subscription(claim.subscription_id)  # type: ignore
         policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore
@@ -509,12 +514,19 @@ class InsuranceService:
         invoice_service = InvoicingService(self.db, tenant_id)
         # 🔥 معاملة ذرية للموافقة والصرف
         async with self.db.begin_nested():
+            # قفل صف المطالبة وإعادة فحص الحالة: يمنع الدفع المزدوج (طلبين متتاليين أو متزامنين)
+            # ويمنع تحويل مطالبة PAID إلى REJECTED
+            locked_claim = await self.repo.get_claim_for_update(claim_id)
+            if locked_claim is None or locked_claim.status not in REVIEWABLE_CLAIM_STATUSES:
+                raise ClaimStatusConflictError("Claim already reviewed")
+
             if approve:
                 final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
                 if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
                     final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore
 
-                payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
+                # مفتاح حتمي لكل مطالبة: حماية transfer من التكرار تشتغل فعلًا
+                payment_idempotency = f"claim_payout_{claim_id}"
                 payout_tx = await finance.transfer(
                     sender_id=reviewer_id,
                     receiver_email=await self._get_user_email(claim.claimant_user_id, tenant_id),  # type: ignore
```

### 14.2 تحقق AFTER الحي (نفس التينانت 130، سيرفر أُعيد تشغيله على الكود المُصلَح)

**السيناريو A — `approve=true` مرتين على C3 (176):**

| النقطة | HTTP | reviewer | claimant | المطالبة | `transactions` | فواتير |
|---|---|---|---|---|---|---|
| البداية | — | 440 | 40 | `SUBMITTED` | 0 | 3 |
| استدعاء 1 | **200** `PAID` | 420 | 60 | `PAID`، 20، `TX-FB2BF0367ECA` | 1: #945 مفتاح **`claim_payout_176`** (حتمي) | 4 |
| استدعاء 2 | **409** `{"detail":"Claim already reviewed (status=PAID)","code":"CLAIM_STATUS_CONFLICT"}` | **420** | **60** | بلا تغيير (الـhash والملاحظات الأولى باقية) | **1** | **4** |

✅ صفر حركة أموال إضافية، صفر فاتورة إضافية، `payout_tx_hash` لم يُستبدل. الرفض جاء من **الفحص المبكر** (الرسالة تحمل الحالة) — قبل استدعاء AI.

**السيناريو B — approve ثم reject على C4 (177):**

| النقطة | HTTP | reviewer | claimant2 | المطالبة | `transactions` |
|---|---|---|---|---|---|
| البداية | — | 420 | 20 | `SUBMITTED` | 0 |
| approve | **200** `PAID` | 400 | 40 | `PAID`، 20، `TX-2DC85B9DC248` | 1: #946 `claim_payout_177` |
| reject | **409** `(status=PAID)` `CLAIM_STATUS_CONFLICT` | 400 | 40 | **`PAID` باقية** (لا `REJECTED`) | 1 |

✅ الحالة تبقى `PAID` ومتسقة مع الدفع. صفر حركة أموال.

**السيناريو C — تزامن حقيقي على C5 (178):** طلبان `approve=true` عبر `asyncio.gather` على `httpx.AsyncClient` منفصلين (اتصالان HTTP منفصلان → جلستا DB منفصلتان على السيرفر).

| الطلب | HTTP | الاستجابة |
|---|---|---|
| C-req1 | **200** | `PAID`، `TX-F55492A5774A` |
| C-req2 | **409** | `{"detail":"Claim already reviewed","code":"CLAIM_STATUS_CONFLICT"}` |

الحالة النهائية: reviewer 400→**380**، claimant 60→**80** (دفعة **واحدة**)، `transactions` = **1** (#947 `claim_payout_178`)، فواتير 5→**6** (واحدة).

**دليل أن التزامن كان حقيقيًا وأن فرع القفل هو الذي أمسك الطلب الثاني:**
- رسالة الـ409 للطلب الثاني هي **`"Claim already reviewed"` بلا حالة** — وهي رسالة **الفحص تحت القفل** (داخل `begin_nested()`)، لا رسالة الفحص المبكر (`"... (status=PAID)"`). أي أن الطلب الثاني **اجتاز الفحص المبكر** بحالة `SUBMITTED` (قرأها قبل commit الأول)، ثم أُمسك عند `SELECT ... FOR UPDATE` + `populate_existing`.
- لوج السيرفر: الطلبان كلاهما وصلا لخطوة AI (`AI claim review failed` في 08:37:09 و08:37:12 محليًا، trace `4adbea15…` و`f5a765d5…`)، ومدتاهما 6.24s و6.34s — متداخلان زمنيًا.
- هذا بالضبط الفرع الذي وصفه §12.3 (غير قابل للإثبات بالسيناريوهات المتتالية) — **الآن مُثبَت حيًا.**

محفظة user 1 أثناء تشغيل AFTER: `710.0` في البداية والنهاية ✅. الأدلة الخام: `.claude/reports/insurance-review-claim-double-payment-evidence-after.txt`.

ملاحظة: `AI claim review failed` (agent 10) يظهر في BEFORE وAFTER بالتساوي — سلوك مسبق، الاستثناء يُبلَع (سطر 490-505)، غير متعلق.

### 14.3 Regression (insurance + finance)

**التشغيل 1** (بعد الإصلاح): `test_insurance_batch0a_tenant_isolation`، `test_insurance_entity_membership_gap_fix`، `test_insurance_getter_endpoints_wiring`، `test_insurance_policy_response_null_issuer`، `test_realestate_insurance_savepoint` (كامل)، `test_financeservice_tenant_binding_fix`، `test_tenders_auctions_finance_hold_release_settle`، `test_saas_active_subscription::test_insurance_review_claim_saas_check_passes_then_hits_known_bug` → **24 passed، 1 xfailed، 2 failed** (12:04 دقيقة).

**التشغيل 2:** `test_saas_active_subscription::test_insurance_subscribe_saas_check_passes` + `test_user_repository_get_by_id_audit::test_insurance_get_user_and_get_user_email_all_three_call_paths` + إعادة الفاشلَين → **1 passed، 3 failed**.

**الفشلات الثلاثة — كلها مسبقة، مُثبَتة بالتشغيل على نسخة HEAD من ملفاتي:** نسختُ مؤقتًا نسخ "قبل" (HEAD) للملفات الثلاثة فوق المُصلَحة (`git diff --stat` = فارغ)، شغّلت الثلاثة → **نفس الفشلات الثلاثة بنفس الرسائل**، ثم أعدتُ الملفات المُصلَحة (`cmp` = مطابق، `git diff --stat` = +29/−2 مرة أخرى).

| الاختبار | السبب | الحالة |
|---|---|---|
| `test_realestate_buy_fractional_ownership_invoice_ordering` | فحص بنيوي على `realestate/service.py` (`create_invoice` غير مُغلَّفة بـtry/except) | مسبق، **معروف** (موثَّق في Batch 0-A) |
| `test_insurance_get_user_and_get_user_email_all_three_call_paths` (:569) | `assert any("referred_by" ...)` على `_register_affiliate_commission` — دالة لم تُلمَس | مسبق، **معروف** (Batch 0-A، Backlog #10) |
| `test_tourism_sports_place_transfer_bid_invoice_ordering` | فحص بنيوي على `tourism_sports/service.py::place_transfer_bid` (`create_invoice` لم تعد داخل try/except بعد commit) | مسبق — **غير موثَّق في أي مكان** (grep على `PROGRESS_LOG.md` والتقارير = 0). ملف لم أمسه؛ على الأرجح أثر جانبي لتعديلات tourism_sports اليوم (`cc9e5c4`/`edb5e5e` + تعديل غير committed في نفس الملف). **لم أحقّق أكثر** — اكتشاف جانبي (§14.6). |

الاختبار الذي يستدعي `review_claim` مباشرة (`test_insurance_review_claim_saas_check_passes_then_hits_known_bug`) — **نجح** (مطالبة `SUBMITTED`). الفحص البنيوي `test_insurance_review_claim_invoice_ordering` — **نجح** (الـdiff لم يغيّر ترتيب commit/الفاتورة).

### 14.5 نتيجة التنظيف

- `DELETE FROM transactions ...` → **DELETE 6** (#942–#947).
- `cleanup.py 130` → حُذف: audit_logs 6، auth_refresh_tokens 2، entity_memberships 1، insurance_claims 5، insurance_subscriptions 2، invoices 6، saas_tenant_service_access 1، saas_tenant_subscriptions 1، sovereign_entities_v2 1، wallets 3، insurance_policies 1، users 3، ثم التينانت 130 نفسه.
- **مقارنة اللقطة (259 جدولًا): ليست zero-diff** ⚠️:

| البند | baseline | بعد التنظيف | الفرق |
|---|---|---|---|
| `transactions` | 192 | 194 | +2 |
| `audit_logs` | 248 | 250 | +2 |
| محفظة user 1 (MR_USDT) | **710.0** | **708.0** | −2 |

**السبب (مُتحقَّق من الصفوف):** ليس الإصلاح ولا بيانات TMPRC. الصفّان الجديدان هما tx **#948** (`AUTO-RENEW-851-2026-09`، "تجديد اشتراك REGTEST-FINBIND-PLAN-cheap-…"، 05:50:12 UTC) و**#950** (`PAY-INV-161`، 05:50:47 UTC) — كلاهما **1 MR_USDT من user 1 → حساب نظام تينانت 1 (user 957)** + صفّا audit مطابقان (#946، #947). المصدر: **اختبار الـregression `test_financeservice_tenant_binding_fix.py`** الذي شغّلته في §14.3 — دوال `_cleanup` فيه تحذف الاشتراك/الخطة/الخدمة لكن **لا تعكس التحويل ولا تحذف صف الـtransaction/audit**. **سلوك مسبق للاختبار:** نفس البصمة موجودة من تشغيل 2026-09-18 (tx #907 `PAY-INV-158` و#920 `AUTO-RENEW-834`) — أي أن رقم 710.0 نفسه كان بعد تسرّب سابق من نفس الاختبار. محفظة 957 حاليًا 167.0.

محفظة user 1 أثناء كل تشغيلات HTTP في هذه الجلسة (BEFORE + AFTER): 710.0 ثابتة ✅ — النقص حدث فقط أثناء الـregression.

**⏸️ قرار مطلوب من المستخدم — لم يُنفَّذ (كتابة على محفظة user 1 الحقيقية وحساب النظام):** عكس التسرّب لإعادة zero-diff:
**⚠️ مسودة أولى — أُلغيت ويحلّ محلها النص المُحرَس في §15.2 (أسطر 934-978) وملف `insurance-review-claim-double-payment-leak-reversal.sql`. هذه المسودة لن تُشغَّل.**


```sql
BEGIN;
DELETE FROM audit_logs   WHERE id IN (946,947) AND user_id=1 AND action='TRANSFER';
DELETE FROM transactions WHERE id IN (948,950) AND sender_id=1 AND receiver_id=957
       AND idempotency_key IN ('AUTO-RENEW-851-2026-09','PAY-INV-161');
UPDATE wallets SET balances = jsonb_set(balances,'{MR_USDT}', to_jsonb((balances->>'MR_USDT')::numeric + 2))
       WHERE user_id=1   AND tenant_id=1;   -- 708 → 710
UPDATE wallets SET balances = jsonb_set(balances,'{MR_USDT}', to_jsonb((balances->>'MR_USDT')::numeric - 2))
       WHERE user_id=957 AND tenant_id=1;   -- 167 → 165
COMMIT;
```

(البديل: ترك التسرّب وتوثيقه فقط، كما حدث ضمنيًا مع تشغيل 09-18.)

### 14.6 اكتشافات جانبية جديدة (لم تُصلَح، لم يُحقَّق فيها أكثر)

1. 🟡 **`test_financeservice_tenant_binding_fix.py` يسرّب أموالًا حقيقية من user 1 في كل تشغيل** (2 MR_USDT → حساب نظام تينانت 1) ولا ينظّف `transactions`/`audit_logs`. اسم مقترح: `test-financeservice-tenant-binding-leaks-user1-funds`.
2. 🟡 **`test_tourism_sports_place_transfer_bid_invoice_ordering` يفشل على الشجرة الحالية** وغير موثَّق — حارس #11b (savepoint leak) على `place_transfer_bid`. اسم مقترح: `tourism-place-transfer-bid-invoice-not-wrapped-regression`.
3. (من قبل، §6/§11) 🔴 `insurance-review-claim-negative-approved-amount-reverses-transfer` — الجلسة المنفصلة التالية. **الإصلاح الحالي لا يغلقه** (مطالبة `SUBMITTED` ما زالت تقبل مبلغًا سالبًا في أول مراجعة).

### 14.7 الحالة

- ✅ الإصلاح مطبَّق (3 ملفات، +29/−2، مطابق لـ§12.2) — **غير staged، غير committed.** لا كتابة في `PROGRESS_LOG.md`.
- ✅ AFTER: A=409 وصفر أموال، B=409 والحالة `PAID` محفوظة، C=دفعة واحدة تحت تزامن حقيقي وفرع القفل مُثبَت.
- ✅ Regression: لا فشل جديد بسبب الإصلاح (3 فشلات مسبقة مُثبَتة على HEAD).
- ⚠️ التنظيف: بيانات TMPRC محذوفة بالكامل، لكن **ليس zero-diff** بسبب تسرّب اختبار الـfinance (§14.5) — **بانتظار قرار المستخدم** على أوامر العكس.
- لا اختبار regression دائم لهذا الإصلاح بعد — مقترح: `tests/test_insurance_review_claim_status_guard.py` (A + B + C على مستوى الخدمة بجلستين) — بانتظار موافقتك.
- ⏸️ **متوقف لمراجعة المستخدم.**

---

## 15. [2026-09-23] SQL العكس الحرفي + توضيحات + بند backlog + اختبار regression دائم

**الحالة:** ⏸️ **لم يُشغَّل أي شيء في هذا القسم** — SQL العكس بانتظار موافقة المستخدم على النص الحرفي أدناه؛ الاختبار الدائم مكتوب لكن **لم يُشغَّل** بعد.

### 15.1 التحقق من الأرقام قبل كتابة SQL (استعلامات قراءة فقط، الآن)

| البند | القيمة الحالية في DB | المُشخَّص في §14.5 | مطابق؟ |
|---|---|---|---|
| محفظة user 1 (wallet_id 39، tenant 1) `MR_USDT` | **708.0** | 708.0 | ✅ |
| محفظة user 957 (wallet_id 929، tenant 1، حساب النظام) `MR_USDT` | **167.0** | 167.0 | ✅ |
| كل صفوف `transactions` خلال آخر 24 ساعة تمس user 1 أو 957 (مرسِلًا أو مستلمًا) | **صفّان فقط:** #948 (`AUTO-RENEW-851-2026-09`، 1 → 957، 1.0، 05:50:12 UTC) و#950 (`PAY-INV-161`، 1 → 957، 1.0، 05:50:47 UTC) | نفسهما | ✅ |
| صفوف `audit_logs` الجديدة (id ≥ 940) | **صفّان فقط:** #946 (user 1، `TRANSFER`، `TX-1BC7A30BC462` = hash الـtx #948) و#947 (user 1، `TRANSFER`، `TX-83DC0E1589E9` = hash الـtx #950) | نفسهما | ✅ |
| عدد `transactions` / `audit_logs` الكلي | 194 / 250 (baseline: 192 / 248) | +2 / +2 | ✅ |

**الاستنتاج — الأرقام مؤكَّدة:** user 1: **708 → 710** (+2)؛ حساب النظام 957: **167 → 165** (−2). لا حركة أخرى على أيٍّ منهما منذ الـbaseline، فقيمة 957 قبل تسرّب الاختبار كانت 165 بالضرورة (167 − 1 − 1).

**ملاحظة واحدة لن يعيدها العكس:** عمود `wallets.updated_at` لكلا المحفظتين تغيّر (05:50:47 UTC) وسيتغيّر مرة أخرى بالـUPDATE؛ وتسلسل `transactions.id` تقدّم (الـid 949 فجوة — على الأرجح محاولة تجديد الاشتراك "الباهظ" التي فشلت بالرصيد داخل savepoint). لقطة المقارنة (عدد الصفوف + أرصدة user 1) لا تقيس هذين، فستعود zero-diff؛ أذكرهما للأمانة فقط.

### 15.2 SQL العكس — النص الحرفي الذي سيُشغَّل (معاملة واحدة، ذرّية، بحراسات)

كل عبارة مقيّدة بالـid **و**بالقيم المتوقَّعة (المرسِل/المستلم/المفتاح/الرصيد الحالي)، وكتلة `DO` ترمي استثناء — فتُلغي المعاملة بالكامل — لو عدد الصفوف المتأثرة لأي عبارة ≠ المتوقَّع. تُشغَّل عبر `psql -v ON_ERROR_STOP=1`.

```sql
BEGIN;

DO $$
DECLARE n integer;
BEGIN
    -- 1) صفّا audit_logs الخاصان بالتحويلين المسرَّبين
    DELETE FROM audit_logs
     WHERE id IN (946, 947)
       AND user_id = 1
       AND action = 'TRANSFER'
       AND details->>'tx_hash' IN ('TX-1BC7A30BC462', 'TX-83DC0E1589E9');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 2 THEN RAISE EXCEPTION 'audit_logs: expected 2 rows, got %', n; END IF;

    -- 2) صفّا transactions المسرَّبان (1 MR_USDT لكلٍّ، user 1 -> 957)
    DELETE FROM transactions
     WHERE id IN (948, 950)
       AND sender_id = 1
       AND receiver_id = 957
       AND amount = 1
       AND currency = 'MR_USDT'
       AND idempotency_key IN ('AUTO-RENEW-851-2026-09', 'PAY-INV-161');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 2 THEN RAISE EXCEPTION 'transactions: expected 2 rows, got %', n; END IF;

    -- 3) محفظة user 1: 708 -> 710 (فقط لو الرصيد الحالي 708 بالضبط)
    UPDATE wallets
       SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(710.0))
     WHERE id = 39 AND user_id = 1 AND tenant_id = 1
       AND (balances->>'MR_USDT')::numeric = 708;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'wallet user 1: expected 1 row at 708, got %', n; END IF;

    -- 4) محفظة حساب النظام 957: 167 -> 165 (فقط لو الرصيد الحالي 167 بالضبط)
    UPDATE wallets
       SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(165.0))
     WHERE id = 929 AND user_id = 957 AND tenant_id = 1
       AND (balances->>'MR_USDT')::numeric = 167;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'wallet 957: expected 1 row at 167, got %', n; END IF;
END $$;

COMMIT;
```

**بعد التشغيل (تحقق):** (1) `select balances->>'MR_USDT' from wallets where user_id=1` → متوقَّع `710.0`؛ (2) محفظة 957 → `165.0`؛ (3) لقطة 259 جدولًا جديدة ومقارنتها بـ`baseline_before.json` → متوقَّع **zero-diff** (بما فيها `__wallets_user1 = 710.0`).

**ترتيب التنفيذ المقترح بعد موافقتك:** SQL العكس → لقطة + مقارنة (zero-diff) → تشغيل الاختبار الدائم §15.6 → لقطة + مقارنة ثانية (لإثبات أن الاختبار الجديد نفسه لا يترك أثرًا).

### 15.3 البند 1 — مسودة بند backlog جديد لسبب التسرّب (نص حرفي؛ **لم يُكتب في `PROGRESS_LOG.md`** — بانتظار موافقة الكتابة حسب قاعدة الجلسة)

> | — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification`: اختبارا `tests/test_financeservice_tenant_binding_fix.py` (`test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` — اشتراك `REGTEST-FINBIND-PLAN-cheap-*` — و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance`) يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929) — 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة (والفاتورة) لكنها **لا تعكس التحويل** ولا تحذف صفّي `transactions` و`audit_logs` → كل تشغيل للملف يُنقص محفظة user 1 بـ2 MR_USDT ويزيد حساب النظام بـ2 ويترك 2+2 صف. **مؤكَّد مرتين:** تشغيل 2026-09-18 (tx #907 `PAY-INV-158` و#920 `AUTO-RENEW-834-2026-09`) وتشغيل 2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09` و#950 `PAY-INV-161`). **أثر جانبي على كل الجلسات:** رقم "محفظة user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وهذه الجلسة كان **بعد** تسرّب 09-18 أصلًا. تسرّب 09-23 عُكِس يدويًا في هذه الجلسة (§15.2 من تقريرها)؛ تسرّب 09-18 **لم يُعكَس**. **الحل المتوقَّع (لم يُنفَّذ):** إما (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1، أو (ب) إضافة عكس صريح في `_cleanup` (حذف صفوف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). (أ) أنظف ويتسق مع نمط التينانت throwaway في باقي الاختبارات. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression ويكسر أي تحقق zero-diff | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1، §15.3 |

### 15.4 البند 3 — تأكيد: الفشلان معروفان من قبل (فُحص، لا توثيق جديد)

- **`test_realestate_buy_fractional_ownership_invoice_ordering`:** ✅ فحصتُ — موثَّق في تقرير Batch 0-A (`insurance-batch0a-tenant-isolation-session-log.md` سطر 210 وجدول سطر 300) وفي `PROGRESS_LOG.md` (سطر ~1055 ضمن `admin-kill-switch-regression-suite-side-effects`، وسطر ~4356، وبنده الجذري `test-savepoint-fragile-source-position-parsing` [2026-09-17] سطر ~4385 الذي يذكره بالاسم كـ"الأثر المؤكَّد حيًا"). **لا بند جديد.**
- **`test_insurance_get_user_and_get_user_email_all_three_call_paths` (:569 `referred_by`):** ✅ فحصتُ — موثَّق في تقرير Batch 0-A (سطر 210 وجدول سطر 299، "Backlog #10") وفي `PROGRESS_LOG.md` (سطر ~4320، إغلاق Batch 0-A). **لا بند جديد.**

### 15.5 البند 4 — فشل `test_tourism_sports_place_transfer_bid_invoice_ordering`: ليس `invoice_number`، وليس جديدًا — **تصحيح لما كتبتُه في §14.3/§14.6**

**ليس** `invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`: ذلك البند خطأ **وقت التشغيل** (`count(*)+1` → duplicate key عند INSERT فاتورة). هذا الاختبار **لا يشغّل أي كود** — هو فحص بنيوي على نص المصدر (`inspect.getsource` + `str.index`)، والفشل `AssertionError` في `tests/test_realestate_insurance_savepoint.py:159` ("create_invoice() لازم تكون مُغلَّفة بـtry/except")، لا أي خطأ DB.

**السبب الفعلي (بالقراءة المباشرة، `tourism_sports/service.py`):** بعد `await self.db.commit()` (سطر 564) أضاف commit **`cc9e5c4`** (B-E3، 2026-09-22 — مُثبَت بـ`git blame` على الأسطر 571-573) كتلة `if requires_medical_review: try: ... except Exception as e: ...` (أسطر 570-599، `except` في سطر 596) **قبل** كتلة الفاتورة. كتلة الفاتورة نفسها سليمة: `try:` (سطر 601) `await invoice_service.create_invoice(...)` (سطر 602) و`except Exception as e: rollback + refresh + log` (أسطر 609-612) — أي `create_invoice` **لا تزال بعد commit ومُغلَّفة بـtry/except خاصة بها**. دالة الفحص `_assert_invoice_after_commit_and_wrapped` تأخذ **أول** `try:`/`except` بعد الـcommit (بتاعة المراجعة الطبية) فتجد `create_invoice` بعد ذلك الـ`except` → فشل كاذب.

**هذا حرفيًا البند الموجود `test-savepoint-fragile-source-position-parsing` [2026-09-17]** (`PROGRESS_LOG.md` سطر ~4385): نفس الدالة، نفس الافتراض ("try/except واحد بس بين commit و`create_invoice`")، نفس النمط (كتلة try/except شرعية أُضيفت قبل كتلة الفاتورة) — كان أثره المؤكَّد على `realestate.buy_fractional_ownership`، والآن حالة ثانية على `tourism_sports.place_transfer_bid`. **الكود الإنتاجي سليم؛ لا حاجة لبند جديد.**

**تصحيح:** في §14.3 و§14.6 وصفتُه بأنه "غير موثَّق في أي مكان" واقترحتُ بندًا جديدًا (`tourism-place-transfer-bid-invoice-not-wrapped-regression`) — **هذا كان خطأ**: بحثتُ عن اسم الاختبار فقط لا عن اسم الدالة المساعدة. **أسحب البند المقترح.** الاقتراح البديل (قرارك): سطر تحديث مؤرَّخ واحد تحت `test-savepoint-fragile-source-position-parsing` يذكر الحالة الثانية (`place_transfer_bid`، سببها `cc9e5c4`) — أو لا شيء.

### 15.6 البند 2 — الاختبار الدائم (مكتوب، **لم يُشغَّل**)

`eppne-backend/tests/test_insurance_review_claim_status_guard.py` — ملف جديد (untracked)، `py_compile` نجح. 3 اختبارات على مستوى الخدمة، DB حقيقية، صفر mock:

| الاختبار | ما يثبته |
|---|---|
| `test_review_claim_approve_twice_pays_once_and_second_call_conflicts` | A: الثاني `ClaimStatusConflictError` بـ`status_code == 409`؛ الحالة بعده (الأرصدة، الحالة، المبلغ، الـhash، عدد الدفعات، عدد الفواتير) **مطابقة تمامًا** لما بعد الأول |
| `test_review_claim_reject_after_paid_conflicts_and_keeps_paid` | B: reject بعد `PAID` → `ClaimStatusConflictError`، الحالة تبقى `PAID` بالـhash |
| `test_review_claim_concurrent_approves_pay_exactly_once` | C: `asyncio.gather` لاستدعاءين بجلستين `AsyncSessionLocal` منفصلتين → نجاح واحد + تعارض واحد بالضبط، دفعة واحدة، reviewer 480، claimant 20، فاتورة واحدة |

**تصميم مقصود لتجنّب مشكلة §15.3:** كل اختبار ينشئ **تينانت throwaway خاصًا** (`REGTEST_RCGUARD_*`، مراجِع مموَّل 500 + مطالِب 0 + كيان + عضوية OWNER + خطة SaaS 101 + بوليصة + اشتراك + مطالبة)، **لا يلمس user 1 ولا أي تينانت حقيقي**، وكل استدعاء `review_claim` في جلسة مستقلة (مثل طلب HTTP). الـ`finally` يحذف صفوف `transactions` بالمفتاح `claim_payout_{id}` (الجدول بلا `tenant_id`) ثم كل صفوف التينانت في كل جدول فيه `tenant_id` (بجولات لحل ترتيب الـFK — نفس منطق `cleanup.py` المُثبَت في هذه الجلسة) ثم التينانت نفسه. سيُثبَت "لا أثر" بلقطة قبل/بعد تشغيله (§15.2، الترتيب المقترح).

**قيد معروف:** في C على مستوى الخدمة، ليس مضمونًا أن **كلا** الاستدعاءين يتجاوزان الفحص المبكر (يعتمد على توقيت الـevent loop) — الاختبار يثبت النتيجة (دفعة واحدة + تعارض واحد) أيًّا كان الفحص الذي أمسك الثاني. إثبات أن **فرع القفل تحديدًا** أمسكه موجود في التحقق الحي HTTP (§14.2، رسالة `"Claim already reviewed"` بلا حالة).

---

## 16. [2026-09-23] تنفيذ العكس + zero-diff + الاختبار الدائم

**موافقة المستخدم:** SQL العكس في §15.2 (ونسخته المطابقة `.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`) موافَق عليه بنصه الحرفي، مع الترتيب: عكس → لقطة zero-diff → الاختبار الدائم → لقطة ثانية → التوقف قبل staging/commit.

### 16.1 تنفيذ SQL العكس

الأمر: `docker exec -i eppne_db psql -U eppne -d eppne_v2 -v ON_ERROR_STOP=1 < .claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`

الخرج: `BEGIN` / `DO` / `COMMIT` — **exit 0**. أي أن كل الحراسات الأربع في كتلة `DO` تحققت (2 + 2 + 1 + 1 صف بالضبط)، وإلا كانت ستُرمى استثناء وتُلغى المعاملة.

| المحفظة | قبل | بعد |
|---|---|---|
| user 1 (wallet 39، tenant 1) | 708.0 | **710.0** ✅ |
| حساب النظام 957 (wallet 929، tenant 1) | 167.0 | **165.0** ✅ |

### 16.2 لقطة بعد العكس

`snapshot.py` → `snap_after_reversal.json` (259 جدولًا). مقارنة مع `baseline_before.json` (المأخوذة قبل أي زرع في §13): **ZERO-DIFF** — كل الجداول الـ259 بنفس عدد الصفوف، و`__wallets_user1 = [[39, 1, {"MR_USDT": 710.0}]]` ✅.

### 16.3 تشغيل الاختبار الدائم `tests/test_insurance_review_claim_status_guard.py`

```
tests/test_insurance_review_claim_status_guard.py::test_review_claim_approve_twice_pays_once_and_second_call_conflicts PASSED [ 33%]
tests/test_insurance_review_claim_status_guard.py::test_review_claim_reject_after_paid_conflicts_and_keeps_paid PASSED [ 66%]
tests/test_insurance_review_claim_status_guard.py::test_review_claim_concurrent_approves_pay_exactly_once PASSED [100%]
======================== 3 passed in 234.92s (0:03:54) ========================
```

**3/3 passed** على الكود المُصلَح.

### 16.4 لقطة ثانية بعد الاختبار (إثبات أنه لا يترك أثرًا)

`snap_after_newtest.json` (259 جدولًا):
- مقابل `baseline_before.json`: **ZERO-DIFF**، user 1 = 710.0 ✅
- مقابل `snap_after_reversal.json`: **ZERO-DIFF** ✅

فحوص صريحة إضافية بعد الاختبار: تينانتات `REGTEST_RCGUARD%` = **0**، مستخدمو `p_rcguard%` = **0**، محفظة 957 = **165.0** (لم تتغير). صفوف `transactions` بمفتاح `claim_payout_%` = **1** — وهو الصف #26 (`claim_payout_1_89be280b7f4a`، 2026-08-17، user 3 → 56) **موجود مسبقًا وجزء من الـbaseline**، لا علاقة له بهذه الجلسة (المقارنة zero-diff تؤكد ذلك).

### 16.5 ملخص الـregression الكامل للجلسة

| المجموعة | النتيجة |
|---|---|
| insurance + finance (§14.3، التشغيلتان) | 25 passed، 1 xfailed، 3 failed — **الثلاثة مسبقة ومُثبَتة على HEAD**: `realestate_buy_fractional` و`tourism place_transfer_bid` (كلاهما البند الموجود `test-savepoint-fragile-source-position-parsing`، §15.5) و`referred_by` :569 (Backlog #10) |
| الاختبار الدائم الجديد (§16.3) | **3/3 passed** |
| سلامة DB | zero-diff مقابل baseline بعد العكس **وبعد** الاختبار الجديد؛ user 1 = 710.0 |

**ملاحظة لم تُنفَّذ (قرارك):** لم أُشغّل الاختبار الجديد على الكود **غير المُصلَح** لإثبات أنه يفشل هناك (mutation check). الدليل الحالي أنه يلتقط الباج هو التحقق الحي BEFORE (§13) الذي أظهر نفس السيناريوهات تدفع مرتين. يمكن تشغيله على نسخ HEAD مؤقتًا (نفس أسلوب §14.3) — التكلفة ~4 دقائق وحركة أموال على تينانت throwaway فقط يحذفه الاختبار نفسه.

### 16.6 الحالة النهائية قبل staging/commit

**ملفات الكود (غير staged، غير committed):**
- `eppne-backend/app/core/errors.py` — M (+5)
- `eppne-backend/app/domains/insurance/repository.py` — M (+10)
- `eppne-backend/app/domains/insurance/service.py` — M (+14/−2)
- `eppne-backend/tests/test_insurance_review_claim_status_guard.py` — جديد (untracked)

**ملفات التقارير (جديدة):**
- `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` (هذا الملف)
- `.claude/reports/insurance-review-claim-double-payment-evidence-before.txt`
- `.claude/reports/insurance-review-claim-double-payment-evidence-after.txt`
- `.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`

**لم يُكتب في `PROGRESS_LOG.md` بعد** (بانتظار موافقة):
1. إغلاق البند `insurance-review-claim-no-status-guard-and-random-payout-idempotency`.
2. البند الجديد `test-financeservice-tenant-binding-leaks-user1-funds` (النص الحرفي في §15.3؛ يُحدَّث ليذكر أن تسرّب 09-23 عُكِس فعليًا في §16.1).
3. البند المُعلَّم `insurance-review-claim-negative-approved-amount-reverses-transfer` (§6/§11) — الجلسة التالية.
4. اختياري: سطر تحديث مؤرَّخ تحت `test-savepoint-fragile-source-position-parsing` (الحالة الثانية `place_transfer_bid`، سببها `cc9e5c4`).

⚠️ **تنبيه staging:** شجرة العمل تحوي تعديلات كثيرة أخرى غير متعلقة (تشمل ملفات insurance-adjacent مثل `tourism_sports/service.py`). الـstaging لهذه الجلسة يجب أن يكون **بمسارات صريحة للملفات الأربعة فقط** (كلها ملفات كاملة لا hunks جزئية — `errors.py` و`repository.py` و`service.py` في insurance لم يكن عليها أي تعديل آخر قبل الجلسة، مُثبَت بـ`git status` في §1)، ثم `git show --stat` للتحقق.

⏸️ **متوقف قبل staging/commit — بانتظار موافقة المستخدم الصريحة.**

---

## 17. [2026-09-23] قبل mutation check: عائقان اكتُشفا — + مسودات `PROGRESS_LOG.md`

**الحالة:** ⏸️ **لم يُشغَّل mutation check ولم يُلمَس أي ملف كود أو اختبار ولم يُعمَل staging** — توقفتُ لأن تنفيذ الـmutation check حرفيًا كما طُلب كان سيفشل لسبب خاطئ **ويسرّب بيانات**. التفاصيل والاقتراح أدناه.

### 17.1 العائق 1 — إرجاع `errors.py` لـHEAD يجعل الاختبار يفشل بـ`ImportError` لا بالباج

الاختبار يستورد `from app.core.errors import ClaimStatusConflictError`. في HEAD هذا الكلاس **غير موجود** → الملف يفشل عند الـcollection بـ`ImportError` قبل تشغيل أي سيناريو. هذا "فشل" لا يثبت شيئًا عن الباج (كان سيفشل بنفس الطريقة لو كان الاختبار فارغًا).

**الاقتراح:** إرجاع **`service.py` و`repository.py` فقط** لـHEAD، وإبقاء `errors.py` المُصلَح (إضافة كلاس غير مستخدَم في HEAD — صفر أثر سلوكي على `review_claim`). بهذا يعمل `review_claim` بسلوكه الأصلي غير المُصلَح بالضبط، والاختبار يفشل **على assertion السلوك** (دفع مزدوج / reject بعد PAID يمر). المتوقَّع على الكود غير المُصلَح:

| الاختبار | الفشل المتوقَّع |
|---|---|
| A (`approve_twice`) | `Failed: DID NOT RAISE ClaimStatusConflictError` — الاستدعاء الثاني ينجح ويدفع مرة ثانية |
| B (`reject_after_paid`) | `Failed: DID NOT RAISE` — الـreject ينجح ويقلب الحالة لـ`REJECTED` |
| C (`concurrent`) | `assert len(succeeded) == 1 and len(conflicts) == 1` يفشل — كلاهما ينجح (نجاحان + صفر تعارض، ودفعتان) |

### 17.2 العائق 2 — `_cleanup` في الاختبار **كان سيسرّب** على الكود غير المُصلَح (عيب حقيقي في الاختبار نفسه)

`_cleanup` الحالي يحذف `transactions` بالمفتاح الحتمي **الدقيق** `claim_payout_{claim_id}`. على الكود غير المُصلَح المفاتيح عشوائية (`claim_payout_{id}_{uuid}`) → **لن تُحذف**. وبما أن `transactions.sender_id`/`receiver_id` عليهما FK إلى `users(id)` (مُتحقَّق: `transactions_sender_id_fkey`، `transactions_receiver_id_fkey`؛ وأيضًا `from_wallet_id`/`to_wallet_id` → `wallets(id)`)، فحذف المحافظ والمستخدمين ثم التينانت **سيفشل** → تسرّب تينانت كامل + مستخدمين + محافظ + transactions. أي: الاختبار **ينظّف فقط حين ينجح** — وهو بالضبط نفس فئة عيب `test-financeservice-tenant-binding-leaks-user1-funds` (تسرّب عند مسار غير متوقَّع). على الكود المُصلَح كان سليمًا (§16.4 zero-diff) لأن المفتاح حتمي.

**الإصلاح المقترح (تعديل على ملف الاختبار الجديد — لم يُطبَّق، بانتظار موافقتك):** حذف `transactions` **بمستخدمي الاختبار** بدل المفتاح — يلتقط أي تحويل مهما كان مفتاحه. مُولَّد على نسخة scratchpad، `py_compile` نجح، نهايات CRLF محفوظة:

```diff
--- a/eppne-backend/tests/test_insurance_review_claim_status_guard.py
+++ b/eppne-backend/tests/test_insurance_review_claim_status_guard.py
@@ -9,7 +9,8 @@
    ClaimStatusConflictError، دفعة واحدة فقط (يمرّن فرع SELECT ... FOR UPDATE + populate_existing).
 
 كل استدعاء في جلسة DB مستقلة (زي طلب HTTP حقيقي). تينانت throwaway خاص بالاختبار
-يُحذف بالكامل في finally مع صفوف transactions (الجدول بلا tenant_id) — لا تسرّب أموال.
+يُحذف بالكامل في finally مع صفوف transactions الخاصة بمستخدميه (الجدول بلا tenant_id) — لا تسرّب أموال،
+حتى لو فشل الاختبار على كود غير مُصلَح (mutation check).
 """
 import asyncio
 import json
@@ -100,13 +101,15 @@
 
 
 async def _cleanup(s: dict) -> None:
-    """يحذف كل صفوف التينانت (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) + صفوف
-    transactions الخاصة بالمطالبات (الجدول بلا tenant_id) ثم التينانت نفسه."""
+    """يحذف صفوف transactions الخاصة بمستخدمي الاختبار (الجدول بلا tenant_id) ثم كل صفوف
+    التينانت (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) ثم التينانت نفسه."""
     tid = s["tenant_id"]
     async with AsyncSessionLocal() as db:
-        keys = [f"claim_payout_{cid}" for cid in s.get("claims", [])]
-        if keys:
-            await db.execute(text("delete from transactions where idempotency_key = any(:k)"), {"k": keys})
+        # بالمستخدمين لا بالمفتاح: يلتقط أي تحويل مهما كان مفتاحه (مثلًا claim_payout_{id}_{uuid}
+        # العشوائي لو الإصلاح اتشال) — وإلا الـFK من transactions لـusers يمنع حذف المستخدمين والتينانت
+        user_ids = [s[k] for k in ("reviewer", "claimant") if k in s]
+        if user_ids:
+            await db.execute(text("delete from transactions where sender_id = any(:u) or receiver_id = any(:u)"), {"u": user_ids})
             await db.commit()
         tables = [r[0] for r in (await db.execute(text(
             """select c.table_name from information_schema.columns c
```

**آمن؟** نعم — `reviewer`/`claimant` مستخدمون أُنشئوا داخل تينانت throwaway خاص بالاختبار نفسه في نفس التشغيل؛ لا يمكن أن يكون لهم تحويلات خارج الاختبار.

### 17.3 تسلسل mutation check المقترح (بعد موافقتك على 17.1 + 17.2)

1. تطبيق الـdiff في 17.2 على ملف الاختبار.
2. تشغيل الاختبار على الكود **المُصلَح** → متوقَّع 3/3 passed (إثبات أن تعديل الـcleanup لم يكسر شيئًا) + لقطة zero-diff.
3. نسخ نسخ HEAD لـ`service.py` و`repository.py` فوق المُصلَحة (`git diff --stat` لهما = فارغ؛ `errors.py` يبقى +5).
4. تشغيل الاختبار → متوقَّع **3 failed** بالأسباب في جدول 17.1.
5. إعادة الملفين المُصلَحين (`cmp` مع نسخ scratchpad المعتمَدة + `git diff --stat` = +29/−2 مجددًا).
6. تشغيل الاختبار مرة أخرى → متوقَّع 3/3 passed.
7. لقطة نهائية → متوقَّع zero-diff مقابل `baseline_before.json` (إثبات أن التشغيل الفاشل في الخطوة 4 نظّف نفسه أيضًا — وهو ما يثبت إصلاح 17.2).

ثم staging كما طلبت (§17.5).

### 17.4 مسودات `PROGRESS_LOG.md` (نص حرفي — **لم يُكتب شيء**)

**أ) إغلاق مؤرَّخ لـ`insurance-review-claim-no-status-guard-and-random-payout-idempotency`** — يُدرَج كفقرة جديدة **مباشرة بعد صف البند** (السطر 1033 حاليًا)، بنفس نمط "✅ إغلاق مؤرَّخ" المستخدَم في السطرين 1038 و1051؛ **صف البند الأصلي لا يُعدَّل**. ⚠️ **الإغلاق جزئي لا كامل:** البند الأصلي له 3 أجزاء، والجزء (3) (`renew_subscription`) خارج نطاق هذه الجلسة ولم يُلمَس:

> **✅ إغلاق جزئي مؤرَّخ [2026-09-23] — الجزءان (1) و(2) مُغلَقان، الجزء (3) مفتوح:** الفرضية **تأكدت حيًا** ثم أُصلحت (جلسة `insurance-review-claim-double-payment-verification`). **BEFORE (HTTP حقيقي، تينانت throwaway 130، الكود غير المُصلَح):** `approve=true` مرتين على مطالبة بـ20 → **200 مرتين ودفع مزدوج فعلي** (المراجِع 500→480→460، المطالِب 0→20→40، صفّا `transactions` بمفتاحين عشوائيين مختلفين، فاتورتان، و`payout_tx_hash` استُبدل بالثاني)؛ `approve=false` بعد `PAID` → **200 والمطالبة `REJECTED`** مع بقاء `approved_amount=20` و`payout_tx_hash` والأموال مدفوعة. **الإصلاح (3 ملفات، +29/−2):** (1) `REVIEWABLE_CLAIM_STATUSES = {SUBMITTED, UNDER_INVESTIGATION}` — فحص مبكر قبل استدعاء AI + فحص حاسم تحت `SELECT ... FOR UPDATE` داخل `begin_nested()` عبر دالة repo جديدة `get_claim_for_update` (مع `populate_existing=True` — لازم لأن `expire_on_commit=False` واستدعاء AI يعمل commit وسيط فيبقى الكائن المحمَّل قديمًا)؛ (2) مفتاح دفع حتمي `claim_payout_{claim_id}`؛ (3) استثناء جديد `ClaimStatusConflictError` → **409** `CLAIM_STATUS_CONFLICT` (`core/errors.py`). `APPROVED`/`PAID`/`REJECTED` نهائية لهذا المسار — أي تصحيح لاحق يحتاج مسارًا منفصلًا للـsuperuser (قرار المستخدم). **AFTER:** الاستدعاء الثاني 409 وصفر حركة أموال/فواتير؛ reject بعد `PAID` → 409 والحالة تبقى `PAID`؛ **تزامن حقيقي** (طلبان عبر `asyncio.gather`) → 200 + 409 ودفعة واحدة فقط، ورسالة الـ409 أثبتت أن **فرع القفل** هو من أمسك الطلب الثاني. اختبار دائم `tests/test_insurance_review_claim_status_guard.py` (3/3، A+B+C على مستوى الخدمة بجلسات منفصلة، تينانت throwaway خاص؛ **mutation check:** يفشل 3/3 على الكود غير المُصلَح). Regression insurance+finance: لا فشل جديد (3 فشلات مسبقة مُثبَتة على HEAD). تنظيف zero-diff (259 جدولًا). **الجزء (3) لم يُلمَس — ما زال مفتوحًا:** `renew_subscription` بمفتاح `renew_{subscription_id}_{uuid}` عشوائي (~سطر 305) وبلا هيدر idempotency — لم يُتحقَّق منه حيًا. **اكتشاف جانبي من نفس الجلسة (بند منفصل أدناه):** `insurance-review-claim-negative-approved-amount-reverses-transfer`. | commit: `<يُملأ بعد الـcommit>` | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §13، §14، §16؛ `.claude/reports/insurance-review-claim-double-payment-evidence-{before,after}.txt`

(ملاحظة: جملة "mutation check: يفشل 3/3" تُكتب فقط **إذا** تأكدت فعلًا في §17.3؛ وإلا تُحذف/تُعدَّل بصدق.)

**ب) صف backlog جديد `test-financeservice-tenant-binding-leaks-user1-funds`** — يُضاف في آخر جدول الـBacklog (بعد السطر 1055 حاليًا، قبل `---`)، بنفس تنسيق الصفوف (`| — | **\`name\`** [date] — ... | الحالة | المراجع |`):

> | — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا (الرصيد "الحقيقي" قبل التسرّبين 712). **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |

(ملاحظة تحتاج تأكيدك قبل الكتابة: رقم "712" استنتاج حسابي — 710 + 2 من تسرّب 09-18 — بافتراض عدم وجود حركات أخرى بين 09-18 و09-23 على محفظة user 1؛ **لم أتحقق من ذلك**. أقترح حذف هذه الجملة الاعتراضية أو التحقق منها أولًا — الأسلم حذفها.)

**ج) صف backlog جديد `insurance-review-claim-negative-approved-amount-reverses-transfer`** — **توصيتي: نعم، صف في `PROGRESS_LOG.md` الآن** (لا يبقى في التقرير فقط). **السبب:** (1) هو 🔴 احتمال سرقة أموال — أخطر من البند الذي أغلقناه للتو، وقرارك نفسه صنّفه كذلك؛ (2) الجلسة المخصصة له لم تُجدوَل بعد، والتقارير لا تُقرأ عند بدء الجلسات — جدول الـBacklog هو ما يُقرأ؛ لو بقي في التقرير فقط وأُغلق البند الأم، يختفي من الرؤية؛ (3) سابقة مباشرة: `insurance-review-claim-no-status-guard-...` نفسه أُدرج كصف وهو "غير مُتحقَّق، ليس ثغرة مؤكَّدة" — نفس وضع هذا البند الآن. يُضاف بعد صف (ب):

> | — | **`insurance-review-claim-negative-approved-amount-reverses-transfer`** [2026-09-23] — *ملاحظة بالقراءة الثابتة أثناء جلسة `insurance-review-claim-double-payment-verification`، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* `PUT /insurance/claims/{id}/review` يقبل `approved_amount` **سالبًا**: (1) `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`؛ (2) `insurance/service.py` (`final_amount = approved_amount or claimed`، سطر 524 بعد الإصلاح) — الـcap على الحد الأعلى فقط (`> max_coverage_limit`)؛ (3) **`FinanceService.transfer` (`finance/service.py:90-113`) لا يفحص `amount > 0`**: مع `amount=-50` فحص الرصيد `sender_current < -50` خطأ دائمًا → يمر، ثم رصيد المُرسِل (المراجِع) **يزيد** 50 ورصيد المستلم (المطالِب) **ينقص** 50 — وقد يصبح سالبًا (لا فحص على المستلم) — ثم `status=PAID` و`approved_amount_mrusdt=-50` وفاتورة بمبلغ سالب. **شرط الهجوم:** OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة — أي مُصدِر تأمين خبيث يسحب من مشتركيه بـ"مراجعة" مطالباتهم. **إصلاح `review_claim` [2026-09-23] لا يغلقه** (مطالبة `SUBMITTED` تقبل مراجعة أولى بمبلغ سالب). **نطاق أوسع:** `FinanceService.transfer` مشترك بين كل الدومينات — أي مستدعٍ يمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّض لنفس الانعكاس؛ و`hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا. **نقطة البداية للجلسة المخصصة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`)؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس مركزي في `transfer` (`amount <= 0 → ValidationError`) + `gt=0` في الـrouter. **ملاحظة جانبية:** `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`or`) فيُدفع المبلغ المطالَب به كاملًا. | 🔴 **غير مُتحقَّق منه — أولوية عالية (احتمال سرقة أموال)**؛ جلسة مخصصة ضيقة (قرار المستخدم 2026-09-23) | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §6، §11 |

**د) `test-savepoint-fragile-source-position-parsing` — قراري: أضيف سطر تحديث مؤرَّخ واحد، وأعتبره ضروريًا فعلًا (لا تجميليًا).** **السبب الملموس:** في هذه الجلسة بحثتُ عن اسم الاختبار الفاشل `test_tourism_sports_place_transfer_bid_invoice_ordering` في `PROGRESS_LOG.md` فلم أجد شيئًا، **فأعلنتُه خطأً "غير موثَّق" واقترحتُ بندًا مكرَّرًا** (§14.3/§14.6، ثم سحبته في §15.5). البند الموجود يذكر اسم اختبار `realestate` فقط؛ أي جلسة قادمة تشغّل الـregression ستواجه نفس الفشل وتبحث بنفس الطريقة وتقع في نفس الخطأ. سطر واحد يذكر اسم الاختبار الثاني يجعله قابلًا للبحث ويمنع ذلك — كما أنه يغيّر حجم البند (اختباران فاشلان لا واحد) وهو معلومة لمن سيصلحه. **لا يغيّر حالة البند ولا أولويته.** يُدرَج كفقرة بعد سطر `**الحالة:**` الخاص بالبند (~سطر 4406):

> **تحديث [2026-09-23] — حالة ثانية:** `test_realestate_insurance_savepoint.py::test_tourism_sports_place_transfer_bid_invoice_ordering` يفشل الآن بنفس السبب بالضبط: commit `cc9e5c4` (B-E3) أضاف كتلة `if requires_medical_review: try: ... except Exception` بعد `commit()` وقبل try/except الفاتورة في `TourismSportsService.place_transfer_bid` (`tourism_sports/service.py` ~570-599)، و`create_invoice` نفسها لا تزال بعد `commit()` ومُغلَّفة بـtry/except خاصة بها (~601-612) — فشل كاذب، الكود الإنتاجي سليم. مُثبَت أنه مسبق (يفشل على HEAD) في جلسة `insurance-review-claim-double-payment-verification` (§14.3، §15.5). الحالة والأولوية بلا تغيير.

(إن فضّلتَ عدم إضافته، البديل: لا شيء — والثمن أن الجلسة القادمة قد تكرر نفس التحقيق.)

### 17.5 خطة الـstaging (بعد mutation check — لم يُنفَّذ شيء)

- **تأكيد "لا hunk-splitting":** ✅ `git diff HEAD --stat` على الملفات الثلاثة الآن = **+5 / +10 / +14−2 بالضبط**، ومقارنة أسطر +/− لهذا الـdiff مع §12.2 المعتمَد كانت مطابقة تامة (§14.1) — أي أن **كل** الفرق بين كل ملف وHEAD هو تعديلات هذه الجلسة، ولا توجد تعديلات أخرى غير committed فيها (وكان `git status` لـinsurance فارغًا عند البدء، §1). ملف الاختبار جديد (untracked). → staging الملفات الأربعة **كاملة** بمسارات صريحة.
- الأوامر: `git add -- eppne-backend/app/core/errors.py eppne-backend/app/domains/insurance/repository.py eppne-backend/app/domains/insurance/service.py eppne-backend/tests/test_insurance_review_claim_status_guard.py` ثم `git diff --cached --name-only` و`git diff --cached --stat` → عرضها عليك و**انتظار موافقتك الصريحة** قبل `git commit`. بعد الـcommit: `git show --stat` للتحقق أن النطاق 4 ملفات فقط.
- **سؤال — التقارير:** `.claude/reports/` متتبَّع في git (194 ملفًا). السابقة المباشرة لنفس الدومين، commit Batch 0-A `44f1d0e`، ضمّت التقرير + ملفات evidence **مع الكود والاختبار في نفس الـcommit**، ثم `PROGRESS_LOG.md` وحده في commit `docs:` لاحق (نمط `26c9834`/`8e9a091` أيضًا: `PROGRESS_LOG.md` فقط). **توصيتي:** نفس النمط — commit الكود يضم الملفات الأربعة + التقارير الأربعة (`...-verification-session-log.md`، `...-evidence-before.txt`، `...-evidence-after.txt`، `...-leak-reversal.sql`)، ثم commit `docs:` لـ`PROGRESS_LOG.md` بعد موافقتك على المسودات. **لكنك طلبت صراحةً staging الملفات الأربعة فقط — فلن أضيف التقارير إلا بموافقتك.**

---

## 18. [2026-09-23] mutation check + المسودات النهائية لـ`PROGRESS_LOG.md` + الـstaging

**موافقات المستخدم:** المسودات (أ)–(د) موافَق عليها مع تصحيح في (ب)؛ ضم ملفات التقارير الأربعة لنفس commit الكود (سابقة Batch 0-A `44f1d0e`)؛ تنفيذ mutation check بإرجاع `service.py` و`repository.py` فقط (تسلسل §17.3، الذي يبدأ بتطبيق إصلاح `_cleanup` في §17.2).

### 18.1 تصحيح (ب) — "708" لا تحل محل "712"، والجملة حُذفت

طلب المستخدم وضع **708** بدل **712**. للتوضيح قبل الكتابة: **708** هو رصيد user 1 **بعد** تسرّب 09-23 والذي عُكِس (710 → 708 أثناء الـregression → 710 بالـSQL في §16.1) — وهذا مذكور **أصلًا** في نص (ب) ("user 1 708→710"). أما الجملة الاعتراضية التي حوت "712" فكانت تقول شيئًا **آخر**: تقدير الرصيد **قبل تسرّب 09-18** (710 + 2) — استنتاج حسابي غير مُتحقَّق. وضع 708 مكانها يجعل الجملة خاطئة. **القرار المطبَّق:** حذف الجملة الاعتراضية بالكامل (توصيتي في §17.4)، والإبقاء على "708→710" المُتحقَّق. النص النهائي لـ(ب) أدناه لا يحوي "712".

### 18.2 نتائج mutation check (التسلسل §17.3)

**الخطوة 1 — إصلاح `_cleanup` في الاختبار (§17.2):** طُبِّق بنسخ نسخة scratchpad المُعدَّلة بعد `cmp` يثبت أن الملف الحالي مطابق للنسخة قبل التعديل؛ `py_compile` نجح. الـdiff الحرفي المطبَّق:

```diff
--- a/eppne-backend/tests/test_insurance_review_claim_status_guard.py
+++ b/eppne-backend/tests/test_insurance_review_claim_status_guard.py
@@ -9,7 +9,8 @@
    ClaimStatusConflictError، دفعة واحدة فقط (يمرّن فرع SELECT ... FOR UPDATE + populate_existing).
 
 كل استدعاء في جلسة DB مستقلة (زي طلب HTTP حقيقي). تينانت throwaway خاص بالاختبار
-يُحذف بالكامل في finally مع صفوف transactions (الجدول بلا tenant_id) — لا تسرّب أموال.
+يُحذف بالكامل في finally مع صفوف transactions الخاصة بمستخدميه (الجدول بلا tenant_id) — لا تسرّب أموال،
+حتى لو فشل الاختبار على كود غير مُصلَح (mutation check).
 """
 import asyncio
 import json
@@ -100,13 +101,15 @@
 
 
 async def _cleanup(s: dict) -> None:
-    """يحذف كل صفوف التينانت (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) + صفوف
-    transactions الخاصة بالمطالبات (الجدول بلا tenant_id) ثم التينانت نفسه."""
+    """يحذف صفوف transactions الخاصة بمستخدمي الاختبار (الجدول بلا tenant_id) ثم كل صفوف
+    التينانت (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) ثم التينانت نفسه."""
     tid = s["tenant_id"]
     async with AsyncSessionLocal() as db:
-        keys = [f"claim_payout_{cid}" for cid in s.get("claims", [])]
-        if keys:
-            await db.execute(text("delete from transactions where idempotency_key = any(:k)"), {"k": keys})
+        # بالمستخدمين لا بالمفتاح: يلتقط أي تحويل مهما كان مفتاحه (مثلًا claim_payout_{id}_{uuid}
+        # العشوائي لو الإصلاح اتشال) — وإلا الـFK من transactions لـusers يمنع حذف المستخدمين والتينانت
+        user_ids = [s[k] for k in ("reviewer", "claimant") if k in s]
+        if user_ids:
+            await db.execute(text("delete from transactions where sender_id = any(:u) or receiver_id = any(:u)"), {"u": user_ids})
             await db.commit()
         tables = [r[0] for r in (await db.execute(text(
             """select c.table_name from information_schema.columns c
```

**الخطوة 2 — على الكود المُصلَح:** **3 passed** (4:33) → لقطة `snap_mut_step2.json`: **ZERO-DIFF** مقابل baseline، user 1 = 710.0.

**الخطوة 3 — إرجاع الإصلاح:** نُسخت نسخ "قبل" لـ`service.py` و`repository.py` (مُتحقَّق أنها مطابقة لـ`git show HEAD:` بعد تجاهل CR — `core.autocrlf=true`). `git diff --stat -- app/domains/insurance` = **فارغ**؛ `errors.py` بقي +5 (الكلاس موجود لكن غير مستخدَم في `review_claim` الأصلي).

**الخطوة 4 — على الكود غير المُصلَح: 3 failed** (4:22)، كلها على assertion السلوك:

| الاختبار | الفشل الفعلي |
|---|---|
| A `approve_twice` | `tests/...status_guard.py:166: Failed: DID NOT RAISE <class 'app.core.errors.ClaimStatusConflictError'>` — الاستدعاء الثاني نجح |
| B `reject_after_paid` | `tests/...status_guard.py:185: Failed: DID NOT RAISE <class 'app.core.errors.ClaimStatusConflictError'>` — الـreject نجح |
| C `concurrent` | (أُعيد تشغيله منفردًا لالتقاط الرسالة، ما زال على الكود غير المُصلَح) `AssertionError: متوقَّع نجاح واحد + تعارض واحد، الفعلي: [<InsuranceClaim ...>, <InsuranceClaim ...>]` / `assert (2 == 1)` — **الطلبان المتزامنان نجحا كلاهما** |

**الخطوة 5 — إعادة الإصلاح:** `cmp` مع نسخ scratchpad المعتمَدة = مطابق للملفين؛ `git diff --stat` = **3 files, +29/−2** كما كان.

**الخطوة 6 — على الكود المُصلَح مجددًا:** **3 passed** (4:18).

**الخطوة 7 — لقطة نهائية `snap_mut_final.json`:** **ZERO-DIFF** مقابل `baseline_before.json`، user 1 = **710.0**. هذا يثبت أيضًا أن **تشغيلَي الفشل** (الخطوة 4 + إعادة C) نظّفا نفسيهما — أي أن إصلاح `_cleanup` يعمل على مسار الفشل (بدونه كان سيتسرّب تينانت كامل بسبب الـFK).

**الخلاصة:** الاختبار الدائم **يلتقط الباج الذي سُمّي به** (يفشل 3/3 على HEAD لأسباب سلوكية صحيحة) ويمر 3/3 على الإصلاح، ولا يترك أثرًا في أي من الحالتين.

### 18.3 النص النهائي الحرفي لـ`PROGRESS_LOG.md` — **لم يُكتب بعد، بانتظار موافقتك**

**(أ) فقرة جديدة مباشرة بعد صف `insurance-review-claim-no-status-guard-and-random-payout-idempotency` (السطر 1033 حاليًا)، صف البند لا يُعدَّل:**

**✅ إغلاق جزئي مؤرَّخ [2026-09-23] — الجزءان (1) و(2) مُغلَقان، الجزء (3) مفتوح:** الفرضية **تأكدت حيًا** ثم أُصلحت (جلسة `insurance-review-claim-double-payment-verification`). **BEFORE (HTTP حقيقي، تينانت throwaway 130، الكود غير المُصلَح):** `approve=true` مرتين على مطالبة بـ20 → **200 مرتين ودفع مزدوج فعلي** (المراجِع 500→480→460، المطالِب 0→20→40، صفّا `transactions` بمفتاحين عشوائيين مختلفين، فاتورتان، و`payout_tx_hash` استُبدل بالثاني)؛ `approve=false` بعد `PAID` → **200 والمطالبة `REJECTED`** مع بقاء `approved_amount=20` و`payout_tx_hash` والأموال مدفوعة. **الإصلاح (3 ملفات، +29/−2):** (1) `REVIEWABLE_CLAIM_STATUSES = {SUBMITTED, UNDER_INVESTIGATION}` — فحص مبكر قبل استدعاء AI + فحص حاسم تحت `SELECT ... FOR UPDATE` داخل `begin_nested()` عبر دالة repo جديدة `get_claim_for_update` (مع `populate_existing=True` — لازم لأن `expire_on_commit=False` واستدعاء AI يعمل commit وسيط فيبقى الكائن المحمَّل قديمًا)؛ (2) مفتاح دفع حتمي `claim_payout_{claim_id}`؛ (3) استثناء جديد `ClaimStatusConflictError` → **409** `CLAIM_STATUS_CONFLICT` (`core/errors.py`). `APPROVED`/`PAID`/`REJECTED` نهائية لهذا المسار — أي تصحيح لاحق يحتاج مسارًا منفصلًا للـsuperuser (قرار المستخدم). **AFTER:** الاستدعاء الثاني 409 وصفر حركة أموال/فواتير؛ reject بعد `PAID` → 409 والحالة تبقى `PAID`؛ **تزامن حقيقي** (طلبان عبر `asyncio.gather`) → 200 + 409 ودفعة واحدة فقط، ورسالة الـ409 أثبتت أن **فرع القفل** هو من أمسك الطلب الثاني. اختبار دائم `tests/test_insurance_review_claim_status_guard.py` (3/3، A+B+C على مستوى الخدمة بجلسات منفصلة، تينانت throwaway خاص؛ **mutation check مُنفَّذ:** بإرجاع `service.py`/`repository.py` لـHEAD يفشل 3/3 على السلوك نفسه — A وB `DID NOT RAISE ClaimStatusConflictError`، وC نجاحان متزامنان بدل نجاح + تعارض — ثم 3/3 passed بعد إعادة الإصلاح، وzero-diff بعد التشغيلين؛ `_cleanup` في الاختبار يحذف `transactions` بمستخدمي الاختبار لا بالمفتاح، فينظّف حتى عند الفشل). Regression insurance+finance: لا فشل جديد (3 فشلات مسبقة مُثبَتة على HEAD). تنظيف zero-diff (259 جدولًا). **الجزء (3) لم يُلمَس — ما زال مفتوحًا:** `renew_subscription` بمفتاح `renew_{subscription_id}_{uuid}` عشوائي (~سطر 305) وبلا هيدر idempotency — لم يُتحقَّق منه حيًا. **اكتشاف جانبي من نفس الجلسة (بند منفصل أدناه):** `insurance-review-claim-negative-approved-amount-reverses-transfer`. | commit: `<يُملأ بعد الـcommit>` | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §13، §14، §16؛ `.claude/reports/insurance-review-claim-double-payment-evidence-{before,after}.txt`

**(ب) صف جديد في آخر جدول الـBacklog (بعد السطر 1055 حاليًا):**

| — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا. **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |

**(ج) صف جديد بعد (ب):**

| — | **`insurance-review-claim-negative-approved-amount-reverses-transfer`** [2026-09-23] — *ملاحظة بالقراءة الثابتة أثناء جلسة `insurance-review-claim-double-payment-verification`، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* `PUT /insurance/claims/{id}/review` يقبل `approved_amount` **سالبًا**: (1) `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`؛ (2) `insurance/service.py` (`final_amount = approved_amount or claimed`، سطر 524 بعد الإصلاح) — الـcap على الحد الأعلى فقط (`> max_coverage_limit`)؛ (3) **`FinanceService.transfer` (`finance/service.py:90-113`) لا يفحص `amount > 0`**: مع `amount=-50` فحص الرصيد `sender_current < -50` خطأ دائمًا → يمر، ثم رصيد المُرسِل (المراجِع) **يزيد** 50 ورصيد المستلم (المطالِب) **ينقص** 50 — وقد يصبح سالبًا (لا فحص على المستلم) — ثم `status=PAID` و`approved_amount_mrusdt=-50` وفاتورة بمبلغ سالب. **شرط الهجوم:** OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة — أي مُصدِر تأمين خبيث يسحب من مشتركيه بـ"مراجعة" مطالباتهم. **إصلاح `review_claim` [2026-09-23] لا يغلقه** (مطالبة `SUBMITTED` تقبل مراجعة أولى بمبلغ سالب). **نطاق أوسع:** `FinanceService.transfer` مشترك بين كل الدومينات — أي مستدعٍ يمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّض لنفس الانعكاس؛ و`hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا. **نقطة البداية للجلسة المخصصة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`)؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس مركزي في `transfer` (`amount <= 0 → ValidationError`) + `gt=0` في الـrouter. **ملاحظة جانبية:** `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`or`) فيُدفع المبلغ المطالَب به كاملًا. | 🔴 **غير مُتحقَّق منه — أولوية عالية (احتمال سرقة أموال)**؛ جلسة مخصصة ضيقة (قرار المستخدم 2026-09-23) | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §6، §11 |

**(د) فقرة جديدة بعد سطر `**الحالة:**` لبند `test-savepoint-fragile-source-position-parsing` (بعد السطر 4411 حاليًا، قبل `---`):**

**تحديث [2026-09-23] — حالة ثانية:** `test_realestate_insurance_savepoint.py::test_tourism_sports_place_transfer_bid_invoice_ordering` يفشل الآن بنفس السبب بالضبط: commit `cc9e5c4` (B-E3) أضاف كتلة `if requires_medical_review: try: ... except Exception` بعد `commit()` وقبل try/except الفاتورة في `TourismSportsService.place_transfer_bid` (`tourism_sports/service.py` ~570-599)، و`create_invoice` نفسها لا تزال بعد `commit()` ومُغلَّفة بـtry/except خاصة بها (~601-612) — فشل كاذب، الكود الإنتاجي سليم. مُثبَت أنه مسبق (يفشل على HEAD) في جلسة `insurance-review-claim-double-payment-verification` (§14.3، §15.5). الحالة والأولوية بلا تغيير.

**ملاحظات:** (1) `commit: <يُملأ بعد الـcommit>` في (أ) يُستبدل بـhash الـcommit الفعلي عند الكتابة. (2) أرقام الأسطر 1033/1055/4411 هي مواضع الإدراج في `PROGRESS_LOG.md` الحالي (المعدَّل غير committed — لا تعارض مع هذه المواضع). (3) كل ذلك في commit `docs:` منفصل لاحق.

### 18.4 الـstaging — الأوامر التي ستُنفَّذ بعد حفظ هذا القسم

```bash
git add -- eppne-backend/app/core/errors.py            eppne-backend/app/domains/insurance/repository.py            eppne-backend/app/domains/insurance/service.py            eppne-backend/tests/test_insurance_review_claim_status_guard.py            .claude/reports/insurance-review-claim-double-payment-verification-session-log.md            .claude/reports/insurance-review-claim-double-payment-evidence-before.txt            .claude/reports/insurance-review-claim-double-payment-evidence-after.txt            .claude/reports/insurance-review-claim-double-payment-leak-reversal.sql
git diff --cached --name-only
git diff --cached --stat
```

**تأكيد "لا hunk-splitting":** الملفات الثمانية كلها إما جديدة (untracked: الاختبار + التقارير الأربعة) أو كل فرقها عن HEAD هو تعديلات هذه الجلسة فقط (الثلاثة: +5 / +10 / +14−2، مطابقة لـ§12.2). لا يوجد أي شيء staged حاليًا (`git diff --cached --name-only` = فارغ). **هذا القسم هو آخر تعديل على التقرير قبل الـstaging** — كي لا يبقى على التقرير تعديل غير staged.

⏸️ **بعد الـstaging: متوقف قبل `git commit` بانتظار موافقتك الصريحة.**
