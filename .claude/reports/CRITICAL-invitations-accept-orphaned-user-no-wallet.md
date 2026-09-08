# 🔴🔴 يوزر حقيقي بلا محفظة بيتسجَّل على القرص فعليًا — `invitations.accept_invitation`

**تاريخ الاكتشاف:** 2026-08-17
**اكتُشف أثناء:** جلسة `constructor-mismatch` (`.claude/reports/constructor-mismatch-session-log.md`) — دومين `invitations`، أثناء التحقق الحي من إصلاح الـconstructor. هذا اكتشاف منفصل تمامًا عن باج الـconstructor نفسه، ويستحق تقرير قائم بذاته بأولوية عاجلة جدًا.
**الحالة: 🔴 صفر إصلاح تم. توثيق فقط، بقرار صريح من المستخدم يتّسق مع نطاق جلسة `constructor-mismatch` (لا تُصلَح باجات جانبية غير مرتبطة بالـconstructor داخل تلك الجلسة).**

---

## 1) الملخص التنفيذي

`POST /api/invitations/{id}/accept` — لما مستخدم **جديد** (بلا حساب من قبل) يحاول يقبل دعوة CRM تسويقية، الـendpoint بيرجع `500 Internal Server Error` واضح للمستخدم. **لكن ورا الكواليس، حساب مستخدم حقيقي بيتسجَّل فعليًا في قاعدة البيانات (`commit()` ناجح) قبل الكراش — بلا محفظة، بلا أي ربط بالدعوة أو بالـlead التسويقي المفروض يتسجَّل معاه.** المستخدم مش هيعرف إن حساب اتعمل باسمه، والحساب ده لو حد استخدمه بعدين (نسيت كلمة السر / login) هيلاقي حساب بلا محفظة، أي عملية مالية هتفشل.

هذا **أول اكتشاف في كل جلسات `constructor-mismatch`/`transaction-savepoint-bug`/`silent-write-regression` السابقة** اللي فيه **بيانات هوية حقيقية بتتسرّب فعليًا على القرص** بسبب تعارض `commit()`-جوه-`begin_nested()` — كل الحالات السابقة (`realestate`, `service_marketplace`) كانت rollback آمن بالكامل (الكتابة المالية `flush()`-only، بترجع لو كراش حصل قبل الـcommit النهائي).

---

## 2) السبب الجذري (مؤكَّد بالقراءة المباشرة + التنفيذ الفعلي)

### تسلسل الاستدعاء

```
InvitationsService.accept_invitation(invitation_id, tenant_id, accept_data, user_id=None, ...)
  [service.py:269]
    async with self.db.begin_nested():          # ← SAVEPOINT يُفتح هنا [سطر 286]
        if not user_id:
            new_user = await self._create_user_from_invitation(accept_data, tenant_id)   # [سطر 288]
                → identity_service = UserService(self.db, tenant_id)   # [service.py:117]
                → return await identity_service.register(user_create, idempotency_key)   # [service.py:124]
                    → UserService.register()   [identity/service.py:61-104]
                        user = await self.user_repo.create(user)   # [سطر 92]
                            → UserRepository.create()   [identity/repository.py:56-60]
                                self.db.add(user)
                                await self.db.commit()      # 🔴 هذا الـcommit المباشر بيقفل الـSAVEPOINT
                                await self.db.refresh(user) # 🔴 هذا اللي بيكراش فعليًا
```

### الملفات والأسطر بالضبط

| الملف | السطر | الكود |
|---|---|---|
| `invitations/service.py` | 286 | `async with self.db.begin_nested():` |
| `invitations/service.py` | 288 | `new_user = await self._create_user_from_invitation(accept_data, tenant_id)` |
| `invitations/service.py` | 115-124 | `_create_user_from_invitation` — بتنادي `UserService(self.db, tenant_id).register(...)` |
| `identity/service.py` | 61-104 | `UserService.register()` — بتنادي `self.user_repo.create(user)` ثم `self.wallet_repo.create(...)` |
| `identity/repository.py` | 56-60 | `UserRepository.create()` — `self.db.add(user)` ثم **`await self.db.commit()` مباشر** ثم `await self.db.refresh(user)` |
| `identity/repository.py` | 231-238 | `WalletRepository.create()` — **`await self.db.commit()` مباشر** كمان (لكن الكود ما بيوصلهاش أصلًا، الكراش بيحصل قبلها) |

### لماذا `identity` معندهاش نفس حماية باقي الدومينات؟

`identity` (زي `invoicing`) **مش من ضمن الـ24 دومين اللي اتحوَّلوا لـ`flush()`-only** في جلسة `transaction-savepoint-bug-session-log.md` — قرار متعمَّد وقتها إن `UserRepository.create()`/`WalletRepository.create()` يفضلوا بيعملوا `commit()` مباشر (منطقي تمامًا لتسجيل مستخدم جديد كعملية مستقلة عبر `POST /api/identity/register` العادي — **ده شغّال صح 100% في كل هذه الجلسة**، اتسجَّل بيه أكتر من 5 يوزرز throwaway بنجاح). **المشكلة تحديدًا لما `UserService.register()` بيتنادى من جوه `begin_nested()` تبع service تاني** — وهو استخدام غير متوقَّع وقت ما اتصمم `identity/repository.py`.

---

## 3) إعادة الإنتاج الفعلية (سكريبت معزول، مش نظري)

**السكريبت:** `verify_accept_invitation.py` (Scratchpad، صفر تعديل على `app/`) — بيكرر جسم `accept_invitation` الحقيقي (`service.py:269-353`) بالحرف، **متخطيًا فقط** `await self._check_saas_limits(tenant_id, "crm")` (باج جانبي مستقل تمامًا، Backlog #9 — `SaaSControlService` معندهاش `get_active_subscription`، موثَّق مسبقًا من `digital_twin`).

**بيانات الاختبار:** `sovereign_invitations_v2 id=1` (زُرعت عبر SQL خام: `tenant_id=1, sender_user_id=51, status=SENT, max_uses=5`)، `accept_data={"email": "p_ctor_inv_newuser@eppne.com", "name": "P-CTOR-INV-NEWUSER", ...}`، **`user_id=None` عمدًا** (لتفعيل مسار "يوزر جديد").

**ناتج التشغيل:**
```
invitation found -> id=1, status=InvitationStatus.SENT
-> calling _create_user_from_invitation (real UserService.register)...
Traceback (most recent call last):
  File "invitations/service.py", line 122, in _create_user_from_invitation
    return await identity_service.register(user_create, f"INV-{uuid.uuid4().hex[:12]}")
  File "identity/service.py", line 92, in register
    user = await self.user_repo.create(user)
  File "identity/repository.py", line 59, in create
    await self.db.refresh(user)
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager. Please complete the context manager before emitting further commands.
```

**الكراش بيحصل أبكر من الفرضية الأصلية** (كانت متوقَّعة عند `repo.create_lead()`، الاستدعاء التالي في `accept_invitation`) — لكن فعليًا **جوه `UserRepository.create()` نفسها**، عند `db.refresh(user)` مباشرة بعد `commit()`.

---

## 4) تحقق DB-level مستقل (قبل/بعد، `SELECT` مباشر — مش افتراض ولا اعتماد على رسائل نجاح)

| الجدول | قبل | بعد | ملاحظة |
|---|---|---|---|
| `users` (`email='p_ctor_inv_newuser@eppne.com'`) | 0 صف | 🔴 **1 صف — `id=52, tenant_id=1`** | **اتحفظ فعليًا على القرص، الـ`commit()` نجح قبل الكراش** |
| `wallets` (`user_id=52`) | — | **0 صف** | `WalletRepository.create()` معملهاش أصلًا — الكراش وقف التنفيذ قبلها |
| `crm_leads` | 0 صف | 0 صف | الكود ما وصلش لـ`repo.create_lead()` أصلًا |
| `sovereign_invitations_v2` (`id=1`) | `status=SENT, current_uses=0` | **`status=SENT, current_uses=0` — بلا تغيير** | الدعوة نفسها فضلت "مش مقبولة" رسميًا |

**الخلاصة: حالة بيانات غير متسقة حقيقية على القرص — يوزر id=52 موجود، نشط (`is_active` افتراضيًا `True`)، بإيميل وباسورد صالحين، لكن بلا محفظة إطلاقًا.**

---

## 5) تحليل الأثر (Impact)

### مين المتأثر؟
أي مستخدم **جديد** (مفيش حساب EPPNE قبل كده) يحاول يقبل دعوة CRM تسويقية (`POST /api/invitations/{id}/accept` بدون `user_id` — يعني مش عبر session مسجَّل دخول بالفعل). المستخدمين اللي عندهم حساب بالفعل (`user_id` متوفر) **غير متأثرين** — المسار بتاعهم بيتخطى `_create_user_from_invitation` بالكامل (شرط `if not user_id:`).

### إيه اللي بيحصل من وجهة نظر المستخدم؟
1. يملأ فورم قبول الدعوة (إيميل، اسم، باسورد).
2. يستقبل `500 Internal Server Error` — رسالة فشل واضحة، **مش صامتة**.
3. **لكن حساب اتعمل باسمه فعليًا** — لو حاول يسجّل دخول بنفس الإيميل/الباسورد اللي كتبهم في الفورم، هينجح الدخول (الحساب موجود وactive)، لكن أي عملية مالية (شراء، تحويل) هتفشل لأنه بلا محفظة.
4. لو حاول "ينسى كلمة السر" أو يعيد التسجيل بنفس الإيميل، هيلاقي `ValidationError("البريد الإلكتروني مسجل بالفعل")` من `register()` نفسها — **مقفول من التسجيل تاني بنفس الإيميل، بلا معرفة إن حساب موجود أصلًا.**

### هل الباج ده قابل للاستغلال حاليًا؟
**لأ، محجوب حاليًا بالكامل** بباج مستقل تمامًا (Backlog #9 — `_check_saas_limits` بتكراش `AttributeError` قبل ما توصل لأي منطق فعلي في `accept_invitation`). **لكن لو حد صلح Backlog #9 بمعزل عن الباج ده، الاستغلال هيبقى فوري ومباشر** — نفس التحذير المتكرر عبر كل جلسات هذه السلسلة ("إصلاح باج واحد بيكشف باج تاني محجوب وراه").

### نطاق الانتشار (Blast Radius) — فحص استباقي إضافي
`grep` شامل لكل استدعاءات `UserService(` عبر المشروع (`app/domains/identity/router.py`, `app/domains/identity/invitation_service.py`, `app/domains/invitations/service.py`) — **`invitations.accept_invitation` هي الحالة الوحيدة المؤكَّدة** اللي بتنادي `UserService.register()` من جوه `begin_nested()` تبع service تاني. الحالة التانية المشابهة ظاهريًا (`identity/invitation_service.py:74`'s `register_with_invitation` — نظام دعوات مختلف تمامًا، دعوات تينانت لا علاقة له بـCRM) **اتفحصت وتأكَّد إنها آمنة** — بتنادي `UserService.register()` جوه `try/except` عادي، **بلا أي `begin_nested()` محيط بالاستدعاء** (`grep` لـ`begin_nested` في `identity/invitation_service.py` رجّع صفر نتيجة).

---

## 6) لماذا لم يُكتشَف هذا من قبل؟

`accept_invitation` كانت محجوبة بالكامل ببج الـconstructor (`UserService(self.db)` بمعامل واحد ناقص) لحد جلسة `constructor-mismatch` — يعني الـendpoint ده ما كانش ممكن يوصل لسطر `_create_user_from_invitation` أصلًا في أي محاولة سابقة. إصلاح باج الـconstructor **كشف** هذا الباج المنفصل — بالظبط زي نفس النمط المتكرر مع `realestate`/`service_marketplace` (Backlog #11 الأصلي)، لكن هنا بعواقب أشد لأنه بيمس هوية مستخدم حقيقية مش مجرد فاتورة.

---

## 7) العلاقة بـ Backlog #11 الأصلي (`realestate-invoicing-savepoint-conflict`)

| | Backlog #11 الأصلي (`realestate`/`service_marketplace`) | هذا الاكتشاف (`invitations`) |
|---|---|---|
| الـservice المسبِّبة | `InvoicingService.create_invoice()` | `UserService.register()` → `UserRepository.create()`/`WalletRepository.create()` |
| هل الكتابة اتحفظت فعليًا على القرص؟ | **لأ** — الكتابة المالية الأساسية (`finance.transfer`) `flush()`-only، بترجع بالكامل لو كراش قبل commit نهائي | **أيوه** — `commit()` مباشر جوه `UserRepository.create()` نجح فعليًا قبل الكراش |
| الأثر الفعلي على القرص | صفر (rollback آمن بالكامل، مؤكَّد بـ`SELECT` مستقل في كل الحالات) | 🔴 **يوزر حقيقي بلا محفظة، بيانات يتيمة فعلية** |
| خطورة | متوسطة (endpoint معطّل، صفر تسرّب بيانات) | 🔴🔴 **عالية** (بيانات هوية حقيقية غير متسقة على القرص) |

**التصنيف المقترَح:** امتداد مباشر لنفس فئة Backlog #11 (`commit()`-جوه-`begin_nested()`)، لكن يستاهل تتبّع منفصل بسبب اختلاف شدة الأثر. **أُضيف كتحديث بارز على بند #11 في `PROGRESS_LOG.md`، مع إحالة لهذا التقرير المستقل.**

---

## 8) بيانات throwaway (جزء من الدليل نفسه، مش بيانات اختبار عادية)

| الجدول | الـID | التفاصيل |
|---|---|---|
| `sovereign_invitations_v2` | `1` | `P-CTOR-INV-ACCEPT-TEST`, `status=SENT` (لسه، لم تتغيّر) |
| `users` | `52` | `p_ctor_inv_newuser@eppne.com` — **🔴 حالة يتيمة حقيقية: يوزر نشط بلا محفظة، دليل الاكتشاف نفسه، لازم يتحفظ لحد ما يتراجع لهذا التقرير، بعدين يُنظَّف ضمن الـBLOCKER الدائم** |

---

## 9) التوصية (توثيق فقط، صفر تنفيذ في هذه الجلسة)

**خارج نطاق `constructor-mismatch` بالكامل — قرار صريح بعدم الإصلاح هنا.** لجلسة مستقبلية مخصَّصة، الاتجاهات المحتملة (تحتاج قرار منتجي/هندسي منفصل، مش قرار تلقائي):
1. تحويل `_create_user_from_invitation` لاستدعاء منطق تسجيل بلا `commit()` داخلي (مسار بديل لـ`UserService.register()` يعتمد على `flush()` بس، يُدار الـcommit من المستدعي)، **أو**
2. نقل استدعاء `_create_user_from_invitation` بره أي `begin_nested()` في `accept_invitation` (زي ما بيحصل في مسارات تانية ناجحة بالفعل — `finance.transfer`/`invoice_service.create_invoice` في نفس الملف بره أي nested block)، **أو**
3. إضافة تعويض (compensating action) صريح لو الكراش حصل بعد إنشاء اليوزر — حذف اليوزر اليتيم أو استكمال إنشاء المحفظة يدويًا.

**أي قرار من دول محتاج فهم أعمق لباقي استخدامات `UserService.register()` في المشروع، ومراجعة منتجية لسلوك "قبول دعوة بيوزر جديد" المطلوب فعليًا.**

---

## 10) الحالة النهائية

🔴 **موثَّق بالكامل، مؤكَّد بالتنفيذ الفعلي + `SELECT` مستقل. صفر إصلاح. أولوية عاجلة جدًا لجلسة منفصلة — أعلى من كل بنود Backlog الحالية، بسبب طبيعة الأثر (بيانات هوية حقيقية، مش مجرد endpoint معطّل).**

**مرجع:** `.claude/reports/constructor-mismatch-session-log.md` (قسم "🔴🔴 اكتشاف حرج مؤكَّد حيًا")، `PROGRESS_LOG.md` (تحديث بند #11 + قسم منفصل بتاريخ 2026-08-17).
