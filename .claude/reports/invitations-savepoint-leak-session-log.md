# تقرير جلسة — `invitations-user-registration-savepoint-leak`

**بدأ التسجيل:** 2026-08-18
**نطاق الجلسة:** إصلاح ثغرة "يوزر حقيقي بلا محفظة بيتسجَّل على القرص فعليًا" في `invitations.accept_invitation` — موثَّقة كاملة في `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`، أُشير لها كأولوية عاجلة جدًا في `constructor-mismatch-session-log.md` (قسم "🔴🔴 قرار أولوية صريح [2026-08-17]") و`PROGRESS_LOG.md` (بانر أعلى الملف + قسم "🔴 قرار أولوية صريح [2026-08-17]" في آخره).

**هذا التقرير مرجع مستقل بالكامل لهذه الجلسة — لا يُدمج مع أي تقرير سابق.**

---

## 0) تأكيد الفهم قبل أي كود

1. `users id=52` (`p_ctor_inv_newuser@eppne.com`, `tenant_id=1`) هو الدليل الحي — **مستثنى من أي تنظيف throwaway حتى تُغلق هذه الجلسة رسميًا.**
2. السبب الجذري: `commit()` مباشر جوه `UserRepository.create()`/`WalletRepository.create()` (`identity/repository.py:56-60, 231-240`) بيقفل السطر الـSAVEPOINT بتاع `begin_nested()` الخاص بـ`accept_invitation` (`invitations/service.py:286`).
3. الثغرة محجوبة حاليًا بالصدفة ببج مستقل (Backlog #9) — أي تعديل مستقبلي على `get_active_subscription` خارج هذه الجلسة يجب أن يراعي هذا.

## 0.1) تحقق حي أساسي (baseline) — قبل أي تعديل

```
docker exec -i eppne_db psql -U eppne -d eppne_v2
```

| الاستعلام | النتيجة |
|---|---|
| `SELECT id, email, tenant_id, is_active FROM users WHERE id=52;` | `52 \| p_ctor_inv_newuser@eppne.com \| 1 \| t` — لسه موجود، نشط |
| `SELECT id, user_id, tenant_id, balances FROM wallets WHERE user_id=52;` | **0 صف** — لسه بلا محفظة |
| `SELECT id, status, current_uses FROM sovereign_invitations_v2 WHERE id=1;` | `1 \| SENT \| 0` — لسه مش مقبولة |

مطابق تمامًا لما هو موثَّق في التقرير الحرج — الحالة لم تتغيّر منذ 2026-08-17.

## 0.2) تأكيد مطابقة الكود الحالي للسطور الموثَّقة في التقرير الحرج

قُرئت الملفات مباشرة (`git status` يُظهر `invitations/service.py` كملف معدَّل حاليًا — تعديلات جلسة `constructor-mismatch` غير المرتبطة بهذا الباج، لا علاقة لها بمسار الكراش نفسه):

| الملف | السطر | الكود الحالي | مطابق للتقرير؟ |
|---|---|---|---|
| `invitations/service.py` | 286 | `async with self.db.begin_nested():` | ✅ |
| `invitations/service.py` | 287-289 | `if not user_id: new_user = await self._create_user_from_invitation(...); user_id = cast(int, new_user.id)` | ✅ |
| `invitations/service.py` | 113-122 | `_create_user_from_invitation` → `UserService(self.db, tenant_id).register(...)` | ✅ |
| `identity/service.py` | 92-93 | `user = await self.user_repo.create(user)` ثم `await self.wallet_repo.create(cast(int, user.id), self.tenant_id)` | ✅ |
| `identity/repository.py` | 56-60 | `UserRepository.create()`: `db.add` → `db.commit()` مباشر → `db.refresh()` | ✅ |
| `identity/repository.py` | 231-240 | `WalletRepository.create()`: نفس النمط — `db.commit()` مباشر | ✅ |
| `invitations/service.py` | 324 | `await self.db.commit()` (الـcommit الخارجي لـ`accept_invitation` نفسها، بعد نهاية بلوك `begin_nested`) | ✅ (سياق إضافي) |

**صفر تناقض بين التقرير والكود الحالي.**

---

## 1) جدول الأدلة/التحليل الكامل للحلول المقترحة (من التقرير الحرج، قسم 9) — قبل أي كود

### الخيار أ — نقل استدعاء `_create_user_from_invitation` بره `begin_nested()`

**الآلية:** إعادة ترتيب `accept_invitation` بحيث `if not user_id: user_id = await self._create_user_from_invitation(...)` يُنفَّذ **قبل** فتح `async with self.db.begin_nested():` (مباشرة بعد التحقق من الدعوة، سطر 284)، بدل ما يكون أول سطر جوه البلوك.

| المعيار | التحليل |
|---|---|
| **يعالج السبب الجذري؟** | ✅ نعم مباشرة — `UserService.register()` (بكل ما فيها من `commit()` داخلي) هتشتغل على معاملة عادية غير متداخلة (`begin_nested()` لسه ما اتفتحش)، فمفيش تعارض SAVEPOINT إطلاقًا. |
| **الملفات المتأثرة** | `invitations/service.py` فقط — إعادة ترتيب أسطر، صفر تعديل على أي دالة تانية. |
| **يمس `UserRepository.create()`/`WalletRepository.create()`؟** | ❌ لا إطلاقًا — صفر لمس على `identity/repository.py` أو `identity/service.py`. **يحترم شرط الإيقاف #5 بشكل طبيعي.** |
| **متسق مع نمط موجود في المشروع؟** | ✅ نعم — نفس التوصية المذكورة في التقرير الحرج نفسه (بند 2)، وموجودة كنمط ناجح فعليًا في أماكن تانية (`finance.transfer`/`invoice_service.create_invoice` بره أي nested block). |
| **الأثر على سلوك `/api/identity/register` العادي** | ✅ صفر أثر — المسار العادي أصلًا بينادي `UserService.register()` مباشرة، بره أي `begin_nested()`؛ هذا التعديل بيخلي مسار `accept_invitation` يتصرف **بنفس الطريقة بالظبط**. |
| **هل بيحل "يوزر بلا محفظة" تحديدًا؟** | ✅ نعم — `register()` هتكمل بالكامل بلا انقطاع (نفس معاملة واحدة غير متداخلة)، يعني `user_repo.create()` **و**`wallet_repo.create()` هيتنفذوا الاتنين بنجاح. لو كراشت `register()` نفسها لأي سبب، هترجع بصفر يوزر (rollback عادي لمعاملة غير متداخلة) — مش حالة يتيمة. |
| **مخاطر متبقية / أثر جانبي** | 🟡 لو الكود بعد إنشاء اليوزر (جوه `begin_nested()`: `create_lead`, `update_invitation`, `create_interaction`) كراش لأي سبب، **اليوزر هيفضل موجود بمحفظة كاملة، لكن مش مرتبط بدعوة/lead مُحوَّل** — حساب حقيقي شغّال 100%، بس الدعوة نفسها هتفضل `SENT` مش `ACCEPTED`. **ضرر محدود جدًا مقارنة بالوضع الحالي** (حساب بلا محفظة) — أسوأ سيناريو هنا "حساب يعمل لكن دعوة لم تُسجَّل كمقبولة"، قابل للتصحيح يدويًا أو بإعادة محاولة القبول (`user_id` هيبقى متاح في المحاولة التالية). |
| **التعقيد / الجهد** | منخفض جدًا — تعديل بترتيب ~4 أسطر، صفر دالة جديدة، صفر تغيير توقيع. |
| **قابلية الاختبار** | عالية — سيناريو واحد بسيط (يوزر جديد بلا `user_id`) يغطي التغيير بالكامل. |

### الخيار ب — تحويل `_create_user_from_invitation` لمسار flush-only (بديل لـ`UserService.register()` بلا `commit()` داخلي، الـcommit يُدار من المستدعي)

**الآلية:** إضافة مسار/method بديلة (في `UserRepository`/`WalletRepository`/`UserService`) تعمل `flush()` بدل `commit()`، يُستخدَم بدل `register()` العادية لما الاستدعاء جاي من جوه معاملة متداخلة زي `accept_invitation`.

| المعيار | التحليل |
|---|---|
| **يعالج السبب الجذري؟** | ✅ نعم، بشكل أعمّ (يحل الفئة كاملة لأي استدعاء مستقبلي من جوه `begin_nested()`، مش بس `accept_invitation`). |
| **الملفات المتأثرة** | `identity/repository.py` (إضافة method جديدة أو تعديل `create()` بمعامل `commit: bool`)، `identity/service.py` (تعديل/إضافة على `register()`)، **بالإضافة لـ`invitations/service.py`**. |
| **يمس `UserRepository.create()`/`WalletRepository.create()`؟** | 🔴 **نعم — بشكل مباشر، بغض النظر عن الشكل الدقيق للتنفيذ** (سواء تعديل الدالة الموجودة بمعامل اختياري، أو إضافة دالة شقيقة تعيد استخدام نفس منطق الإنشاء). **هذا يُفعِّل شرط الإيقاف الفوري #5 صراحة** — كود مشترك يمس مسار `/api/identity/register` الأساسي الشغّال حاليًا بنجاح، ويحتاج تحقق إضافي إن التسجيل العادي لسه شغال 100% بعد أي تعديل. |
| **الأثر على سلوك `/api/identity/register` العادي** | 🟡 **مخاطرة حقيقية إن لم يُنفَّذ بعناية فائقة** — أي تعديل على `create()`/`register()` نفسها (حتى لو بمعامل افتراضي `commit=True` يحافظ على السلوك القديم) يفرض إعادة اختبار المسار العادي بالكامل (تسجيل مستخدم جديد فعلي عبر `/api/identity/register`) للتأكد من عدم كسره — **تحديدًا الشرط اللي طلب المستخدم الالتزام به لو لُمس هذا الكود.** |
| **التعقيد / الجهد** | متوسط-عالي — تصميم API إضافي (متى نستخدم flush ومتى commit)، تعديل على كود مشترك، اختبار مضاعف (المسار الجديد + المسار العادي). |
| **الخلاصة** | **محظور فعليًا من نطاق هذه الجلسة** بموجب شرط الإيقاف #5 الصريح، إلا بموافقة استثنائية صريحة من المستخدم يعلن فيها تجاوز هذا الشرط عمدًا. **لن يُطبَّق بدون توقف وسؤال مباشر أولًا.** |

### الخيار ج — تعويض صريح (compensating action) لو الكراش حصل بعد إنشاء اليوزر

**الآلية:** لفّ `_create_user_from_invitation` بـ`try/except` جوه `accept_invitation`؛ لو أي كود بعدها (جوه نفس الـ`begin_nested()` أو بعده) كراش، تنفيذ حذف صريح لليوزر اليتيم أو استكمال إنشاء المحفظة يدويًا كتعويض.

| المعيار | التحليل |
|---|---|
| **يعالج السبب الجذري؟** | ❌ لا — بيسيب `commit()`-جوه-`begin_nested()` زي ما هو، بيحاول يمسح الأثر بعد ما يحصل، مش يمنعه. |
| **الملفات المتأثرة** | `invitations/service.py` فقط (نظريًا) — لكن التنفيذ الفعلي معقَّد. |
| **يمس `UserRepository.create()`/`WalletRepository.create()`؟** | ❌ لا مباشرة، لكن **يحتاج تعامل يدوي مع نفس الجداول** (`DELETE FROM users` أو `INSERT INTO wallets` يدوي) خارج مسار الـrepository الرسمي — إعادة تنفيذ منطق موجود أصلًا بطريقة موازية غير آمنة. |
| **عقبة تقنية جوهرية** | 🔴 بمجرد ما `InvalidRequestError: Can't operate on closed transaction inside context manager` تحصل، **الـ`AsyncSession` (`self.db`) نفسها بتبقى في حالة غير صالحة للاستخدام العادي** — أي محاولة `try/except` حوالين البلوك هتحتاج جلسة/اتصال منفصل تمامًا لعمل الـDELETE التعويضي، مش مجرد `except` عادي على نفس `self.db`. هذا تعقيد بنيوي حقيقي، مش تفصيل تنفيذي بسيط. |
| **مخاطر إضافية** | لو التعويض هو "حذف اليوزر"، وكان فيه محاولة تسجيل دخول متزامنة (race condition نظري) بين لحظة إنشاء اليوزر ولحظة حذفه، ممكن نتائج غير متوقَّعة. لو التعويض هو "استكمال إنشاء المحفظة يدويًا"، برضه محتاج جلسة/اتصال منفصل، وبيفترض إن كل حالات الكراش نوعها "توقف بعد إنشاء اليوزر تحديدًا" — افتراض هش. |
| **التعقيد / الجهد** | الأعلى بين الخيارات الثلاثة — يحتاج تصميم إدارة جلسة منفصلة، معالجة أخطاء دقيقة، واختبار سيناريوهات فشل متعددة. |
| **الخلاصة** | حل تلطيفي (mitigation) وليس علاجًا جذريًا، وتعقيده التقني (جلسة منفصلة للتعويض) أعلى من الخيارين التانيين بلا فائدة مقابلة واضحة. |

---

## 2) التوصية

**الخيار أ (نقل الاستدعاء بره `begin_nested()`)** هو الموصى به بوضوح:
- يعالج السبب الجذري مباشرة (يحل "يوزر بلا محفظة" بالكامل — `register()` هتكمل بمعاملة واحدة غير متداخلة).
- صفر لمس على `UserRepository.create()`/`WalletRepository.create()` — يحترم شرط الإيقاف #5 دون الحاجة لتجاوزه.
- أقل تعقيدًا وأثرًا جانبيًا بين الخيارات الثلاثة.
- متسق مع نمط موجود بالفعل في نفس الملف والمشروع.

**الخيار ب** يفعّل شرط الإيقاف #5 صراحة — **لن يُقترَح كتنفيذ إلا بموافقة استثنائية صريحة إضافية.**
**الخيار ج** معقَّد تقنيًا (يحتاج جلسة DB منفصلة للتعويض) بلا ميزة تعالج السبب الجذري.

---

## 3) جولة أسئلة توضيحية قبل أي ديف [2026-08-18]

### 3.0) تأكيد صريح — `id=52` مستثنى بالكامل، التحقق الحي هيستخدم دعوة/يوزر جديدين

**مؤكَّد ومفهوم:** `users id=52` (`p_ctor_inv_newuser@eppne.com`) و`sovereign_invitations_v2 id=1` **يفضلوا زي ما هم بالضبط، صفر لمس، صفر محاولة "تصحيح" ليطابقوا أي نمط جديد.** التحقق الحي المطلوب في البند 4 من معيار الجلسة (إعادة إنتاج نفس السيناريو) **هيستخدم دعوة جديدة تمامًا ويوزر بإيميل جديد تمامًا** — لن يُستخدَم `id=52`/دعوة `id=1` في أي تحقق حي لهذه الجلسة. هذا مسجَّل هنا كالتزام صريح، مش مجرد نية.

### 3.1) السؤال الأول — موضع فحص صلاحية الدعوة (إجابة نهائية بأرقام سطور دقيقة)

**الكود الكامل لـ`accept_invitation` من نقطة التحقق حتى نقطة النقل المقترحة** (`invitations/service.py:282-290`):

```python
282  invitation = await self.repo.get_invitation(invitation_id, tenant_id)
283  if not invitation or invitation.status != InvitationStatus.SENT:  # type: ignore
284      raise NotFoundError("Invitation not found or not sent")
285
286  async with self.db.begin_nested():        # ← نقطة النقل المقترحة: قبل هذا السطر مباشرة
287      if not user_id:
288          new_user = await self._create_user_from_invitation(accept_data, tenant_id)
289          user_id = cast(int, new_user.id)
```

**الفحص الوحيد الموجود فعليًا في الدالة كلها هو سطرين: 282 (جلب الدعوة) و283 (`status != SENT`) — والاتنين قبل سطر 286 (نقطة النقل) بشكل قاطع.** نقل `_create_user_from_invitation` لتنفَّذ فور بعد سطر 284 **لا يتخطى ولا يُعيد ترتيب أي فحص موجود** — لأن كل فحص موجود أصلًا سابق للنقطة دي بالفعل.

**بخصوص `expires_at`/`max_uses` تحديدًا — تحقَّقت بـ`grep` مباشر على الملفات الثلاثة المعنية، صفر تخمين:**

| الملف | نتيجة `grep expires_at` | نتيجة `grep max_uses` |
|---|---|---|
| `invitations/service.py` (الملف كله، مش بس `accept_invitation`) | **0 نتيجة** | **0 نتيجة** |
| `invitations/router.py` (كل endpoints الدومين) | **0 نتيجة** | **0 نتيجة** |
| `invitations/repository.py` (كل الاستعلامات) | **0 نتيجة** | **0 نتيجة** |

`current_uses` نفسها تظهر مرة واحدة بس في الملف كله — سطر 311، جوه `begin_nested()`، وهي **تحديث** (`current_uses=invitation.current_uses + 1`) مش **فحص** (لا توجد أي مقارنة `current_uses >= max_uses` أو مشابه في أي مكان).

**الخلاصة الدقيقة المطلوبة:** الفحص الوحيد الموجود (`status == SENT`) **قبل** نقطة النقل — إجابتك الشرطية الأولى تنطبق، توثيق بس مقبول لهذا الفحص. أما `expires_at`/`max_uses`: **مفيش فحص لهم في الكود من الأساس — لا قبل نقطة النقل ولا بعدها ولا جوّها** — يعني مش حالة "فحص هيتنقل مكانه فيسبب باج"، دي حالة "الفحص مش موجود إطلاقًا، بمعزل تام عن أي تعديل في هذه الجلسة". نقل `_create_user_from_invitation` **لا يُنشئ هذه الفجوة ولا يغيّر منها أي شيء** — هي موجودة بالضبط بنفس الشكل في الكود الحالي **قبل** أي تعديل مني. بالتالي، بمعيارك الخاص المذكور ("لو الفحص بيحصل قبل نقطة النقل — تمام، توثيق بس مقبول لأن مفيش باج فعلي")، ولأن الفجوة دي غير متأثرة إطلاقًا بمكان النقل (معدومة قبله وبعده على حدٍ سواء)، **فهي خارج نطاق هذا التعديل تحديدًا** — لكنها تستاهل توثيقها كبند Backlog منفصل بصفتها اكتشاف جديد (شرط الإيقاف #4)، بانتظار تأكيدك على هذا التصنيف تحديدًا قبل ما أكمل.

### 3.2) السؤال الثاني — سيناريو إعادة المحاولة (إجابة كاملة، الحل جزء من نفس التعديل)

**لأ، `accept_invitation` لا تبحث عن يوزر موجود بالإيميل قبل نداء `_create_user_from_invitation`.** الشرط الوحيد (`invitations/service.py:287`) هو `if not user_id:` — بيفحص باراميتر الدالة نفسه بس، مش وجود يوزر بنفس الإيميل.

**ما يحصل فعليًا عند إعادة المحاولة (بعد الخيار أ بدون أي تعديل إضافي):**
`_create_user_from_invitation` (`invitations/service.py:122`) بتولّد `idempotency_key` عشوائي جديد كل مرة: `f"INV-{uuid.uuid4().hex[:12]}"`. آلية idempotency الموجودة فعليًا جوه `UserService.register()` (`identity/service.py:62-66`، عبر `get_by_idempotency_key`) بتبقى معطَّلة عمليًا لأن المفتاح مش ثابت بين المحاولات. عند إعادة المحاولة، `register()` بتوصل لـ`get_by_email` (`identity/service.py:68-70`) وتلاقي الإيميل موجود من المحاولة الأولى → **`ValidationError("البريد الإلكتروني مسجل بالفعل")`**. الخطأ ده بيطلع من `_create_user_from_invitation` (خارج `begin_nested()` بعد النقل)، فـ`accept_invitation` بالكامل بتفشل — **الدعوة تفضل `SENT` للأبد بلا أي مسار نجاح ممكن**، والعميل معندوش `user_id` من محاولته الأولى الفاشلة عشان يبعته في التانية.

**الحل — جزء من نفس التعديل، مش بند منفصل لاحقًا:** تثبيت الـ`idempotency_key` الممرَّر لـ`identity_service.register(...)` في `invitations/service.py:122` ليكون **قيمة ثابتة مشتقة من `tenant_id` + `invitation_id`** (مقترَح: `f"INV-ACCEPT-T{tenant_id}-{invitation_id}"`) بدل `uuid.uuid4()` العشوائي. عند إعادة المحاولة، `get_by_idempotency_key` (موجودة بالفعل، قراءة فقط، **صفر لمس على `create()`**) هتلاقي نفس اليوزر من المحاولة الأولى (وبقى معاه محفظة كاملة بفضل نقل الخيار أ) وترجّعه، فـ`accept_invitation` تكمل عادي لـ`create_lead`/`update_invitation`/`create_interaction`.

**ليه مش استخدمت بحث مباشر بالإيميل بدل الـidempotency key؟** لأنه بيفتح ثغرة أمان: طلب مجهول الهوية (`user_id=None`) لو بعت إيميل حقيقي لحساب موجود بالفعل (مش بالضرورة صاحب المحاولة الأولى)، هيتلصق تلقائيًا بيوزر حقيقي تاني بلا أي تحقق باسورد. مفتاح idempotency الثابت آمن لأنه بيطابق **بس** سجل اتعمل من محاولة سابقة لنفس الدعوة تحديدًا (تركيبة `tenant_id+invitation_id` فريدة)، مش أي حساب بالإيميل.

**تحقَّق إضافي بخصوص تفرُّد المفتاح عبر المستأجرين:** عمود `users.idempotency_key` هو `unique=True` **على مستوى قاعدة البيانات كله**، مش مقيَّد بالمستأجر (`identity/models.py:70`). لو المفتاح المقترَح كان `f"INV-ACCEPT-{invitation_id}"` بدون `tenant_id`، مستأجرين مختلفين عندهم دعوة بنفس الـ`id` الرقمي (تسلسل مستقل لكل مستأجر) كانوا هيتصادموا على `IntegrityError`. **لذلك الصيغة المقترَحة تتضمَّن `tenant_id` صراحة** (`f"INV-ACCEPT-T{tenant_id}-{invitation_id}"`) لضمان تفرُّد عالمي حقيقي.

**⚠️ ملاحظة على `id=52` تحديدًا (تفصيل تقني، صفر لمس فعلي):** فحصت قيمة `idempotency_key` المخزّنة له فعليًا: `INV-11ad40e555cb` (نمط عشوائي قديم، سابق لأي تعديل). لو اتعمل retry فعلي بالكود الجديد على دعوة `id=1`، مش هيلاقي `id=52` عبر المفتاح الثابت الجديد (مختلف تمامًا)، وهيوصل لنفس جدار `ValidationError` القديم — **متوقَّع ومقبول تمامًا**، لأن `id=52`/دعوة `id=1` لن يُستخدَما في التحقق الحي أصلًا (راجع 3.0).

---

## 4) القرارات المعتمَدة [2026-08-18]

1. **فجوة `expires_at`/`max_uses`:** خارج نطاق هذه الجلسة تمامًا — **موثَّقة الآن (مش بعد القفل)** كبند Backlog جديد صريح في `PROGRESS_LOG.md` بعنوان `invitations-missing-expiry-max_uses-validation`، بأولوية أعلى من العادي. **صفر إصلاح في هذه الجلسة.**
2. **حل الـretry:** موافقة صريحة نهائية على الحل المُجمَّع — نقل `_create_user_from_invitation` بره `begin_nested()` + تثبيت `idempotency_key` بصيغة `f"INV-ACCEPT-T{tenant_id}-{invitation_id}"`. كله جوه `invitations/service.py` فقط.

## 5) الديف الكامل — بانتظار الموافقة قبل أي `Edit` فعلي

**ملاحظة توضيح:** الديف ده **مبني يدويًا** (مش ناتج `git diff` فعلي) لأنه لسه صفر تعديل على القرص — لكنه **النص الحرفي بالظبط** اللي هيتطبَّق لو اتوافق عليه، سطر بسطر، بلا أي فرق. بعد الموافقة والتطبيق هيُعرَض `git diff`/`git status` خام حقيقي من القرص (متطلَّب رقم 3 في معيار الجلسة).

**تحقق إضافي قبل العرض:**
- `grep` شامل على المشروع كله: `_create_user_from_invitation` لها **مستدعٍ واحد فقط** (`accept_invitation` نفسها) — توسيع توقيعها بمعامل `invitation_id` آمن، صفر كسر لأي مكان تاني.
- `uuid` import (`invitations/service.py:6`) لسه مطلوبة (تُستخدم في سطر 643 لسياق مختلف تمامًا) — صفر حاجة لتعديل الـimports.
- الملف الوحيد المتأثر: `invitations/service.py`. **صفر لمس على `identity/service.py`/`identity/repository.py`.**

```diff
diff --git a/eppne-backend/app/domains/invitations/service.py b/eppne-backend/app/domains/invitations/service.py
index 0000000..0000000 100644
--- a/eppne-backend/app/domains/invitations/service.py
+++ b/eppne-backend/app/domains/invitations/service.py
@@ -110,7 +110,7 @@
         return agents[0] if agents else None

-    async def _create_user_from_invitation(self, data: dict, tenant_id: int):
+    async def _create_user_from_invitation(self, data: dict, tenant_id: int, invitation_id: int):
         from app.domains.identity.service import UserService
         identity_service = UserService(self.db, tenant_id)
         from app.domains.identity.schemas import UserCreate
@@ -119,7 +119,7 @@
             email=cast(str, data.get("email")),
             password=data.get("password", "TempPass123!")
         )
-        return await identity_service.register(user_create, f"INV-{uuid.uuid4().hex[:12]}")
+        return await identity_service.register(user_create, f"INV-ACCEPT-T{tenant_id}-{invitation_id}")

     async def _apply_discount_gift(self, user_id: int, invitation: SovereignInvitation):
         pass
@@ -283,15 +283,15 @@
         if not invitation or invitation.status != InvitationStatus.SENT:  # type: ignore
             raise NotFoundError("Invitation not found or not sent")

-        async with self.db.begin_nested():
-            if not user_id:
-                new_user = await self._create_user_from_invitation(accept_data, tenant_id)
-                user_id = cast(int, new_user.id)
+        if not user_id:
+            new_user = await self._create_user_from_invitation(accept_data, tenant_id, invitation_id)
+            user_id = cast(int, new_user.id)

+        async with self.db.begin_nested():
             lead = await self.repo.create_lead(
                 tenant_id=tenant_id,  # type: ignore
                 source=LeadSource.INVITATION,
                 source_reference=f"INV-{invitation_id}",
                 status=LeadStatus.CONVERTED,
                 converted_user_id=user_id,
                 converted_at=datetime.utcnow(),
                 email=accept_data.get("email"),
                 first_name=accept_data.get("name"),
                 phone=accept_data.get("phone"),
                 idempotency_key=idempotency_key
             )
```

## 6) التطبيق [2026-08-18]

✅ **الديف تم تطبيقه بالحرف كما هو معروض في القسم 5.** `git diff`/`git status` الخام بعد التطبيق تم عرضهم وتأكيدهم — التعديل الوحيد بتاعي في `invitations/service.py` محصور في: (1) توسيع توقيع `_create_user_from_invitation` بمعامل `invitation_id`، (2) تثبيت الـ`idempotency_key`، (3) نقل بلوك `if not user_id` بره `begin_nested()`. **صفر لمس على أي ملف تاني.** (الديف الخام كان فيه تعديلات إضافية من جلسة `constructor-mismatch` غير المُثبَّتة بعد، سبق توضيحها كمنفصلة تمامًا عن تعديلي).

---

## 7) التحقق الحي [2026-08-18] — قيد التنفيذ

### 7.0) التزام صريح
`users id=52` و`sovereign_invitations_v2 id=1` **لم يُلمَسا إطلاقًا** ولن يُلمَسا. التحقق الحي بيستخدم دعوتين جديدتين تمامًا (`id=2`, `id=3`) وإيميلات جديدة تمامًا (`p_savepoint_fix_verify_clean@eppne.com`, `p_savepoint_fix_verify_retry@eppne.com`).

### 7.1) بيانات throwaway جديدة للتحقق
عبر `docker exec eppne_db psql` (SQL خام، خارج app/):
| `sovereign_invitations_v2 id` | `title` | الغرض |
|---|---|---|
| `2` | `P-SAVEPOINT-FIX-VERIFY-CLEAN` | سيناريو قبول نظيف (يوزر جديد، بلا أي فشل) |
| `3` | `P-SAVEPOINT-FIX-VERIFY-RETRY` | سيناريو فشل جزئي متعمَّد بعد إنشاء اليوزر، ثم إعادة محاولة |

### 7.2) سكريبت التحقق
`verify_savepoint_fix.py` (Scratchpad، صفر تعديل على `app/`) — بينادي `InvitationsService.accept_invitation` **الحقيقية** مباشرة (مش إعادة كتابة منطقها)، بيتخطى فقط `_check_saas_limits` (Backlog #9 غير المرتبط، موثَّق مسبقًا). سيناريو 2 بيعطّل `repo.create_lead` مؤقتًا في المحاولة الأولى بس، لمحاكاة فشل حقيقي بعد إنشاء اليوزر داخل `begin_nested()`.

### 7.3) عقبتان في بيانات الـseed نفسها (مش في الكود، اتصلحوا في بيانات التحقق فقط)
1. **`is_deleted` كان `NULL`** بعد الـINSERT الخام (الموديل بيحط `default=False` على مستوى بايثون/ORM بس، الإدراج الخام بالـSQL مبيطبّقوش) — `get_invitation`'s فلتر `is_deleted == False` مبيطابقش `NULL` في SQL، فرجّعت `NotFoundError` كاذبة. **اتصلح بتحديث `is_deleted=false` صراحة على الدعوتين.**
2. **`discount_percentage`/`gift_coins_amount` كانوا `NULL`** لنفس السبب (نفس نمط الإدراج الخام). لما التنفيذ وصل فعليًا لسطر 304 (`if invitation.discount_percentage > 0 or invitation.gift_coins_amount > 0`) — **أول مرة الكود يوصل للسطر ده في كل تاريخ الجلسات** (كل التحقق الحي السابق كان بيكراش أبكر بكتير، عند `db.refresh()` بتاعة الـSAVEPOINT) — `TypeError: '>' not supported between instances of 'NoneType' and 'int'`. **تأكَّد إنه نفس النمط بالظبط موجود في `id=1` الأصلية نفسها** (نفس القيم فاضية في `SELECT *` من قسم 0.1) — يعني ده أثر جانبي لأسلوب إدراج بيانات الاختبار عبر SQL خام في كل الجلسات السابقة (بما فيها التقرير الحرج الأصلي)، **مش باج جديد في الكود** — أي دعوة حقيقية بتتعمل عبر `create_invitation` (الـendpoint الفعلي) بتاخد `default=0` تلقائيًا من الـORM عند الإدراج. **اتصلح بتحديث `discount_percentage=0, gift_coins_amount=0, gift_currency='MR_USDT'` صراحة على الدعوتين (بيانات الاختبار فقط، صفر لمس على الكود).**

**⚠️ ملاحظة للسجل (مش بند إيقاف #4، توضيح ليه):** هل ده "باج جديد"؟ من الناحية النظرية DB-level العمودين فعلًا `nullable` (صفر `NOT NULL` constraint)، فلو أي مسار غير الـORM (migration، seed خام، إلخ) حط `NULL` فعليًا في هذين العمودين لأي دعوة حقيقية، `accept_invitation` هتكراش. **لكن هذا يختلف عن اكتشاف `expires_at`/`max_uses` (قسم 3.1/Backlog الجديد)** — هناك الفحص **غير موجود إطلاقًا** بغض النظر عن مصدر البيانات (فجوة منطقية حقيقية تنطبق على كل الدعوات). هنا المشكلة **محصورة في كيفية إدخال بيانات الاختبار عبر SQL خام تحديدًا** — أي دعوة حقيقية عبر التطبيق نفسه لن تصل لهذه الحالة أبدًا. **قرار:** يُذكَر هنا للشفافية الكاملة، **بلا فتح بند Backlog منفصل له** إلا لو رأيت غير ذلك — لأنه ليس مسارًا قابلًا للوصول عبر أي استخدام حقيقي للتطبيق، بعكس فجوة `expires_at`/`max_uses`.

### 7.4) نتيجة تشغيل السكريبت (بعد إصلاح بيانات الـseed)

**سيناريو 1 (دعوة `id=2`, قبول نظيف):** السكريبت طبع **`FAILED: TypeError: audit_log() got an unexpected keyword argument 'tenant_id'`**.
**سيناريو 2 (دعوة `id=3`, فشل جزئي متعمَّد ثم إعادة محاولة):** المحاولة الأولى فشلت **كما هو مخطَّط** (`RuntimeError: SIMULATED-FAILURE-AFTER-USER-CREATION`). المحاولة الثانية (retry) طبعت **نفس خطأ `audit_log`** أعلاه.

**⚠️ توضيح حاسم — هذا الخطأ المطبوع مش فشل حقيقي لإصلاح هذه الجلسة، هو باج مستقل تمامًا موثَّق مسبقًا (Backlog #14، `audit-log-wrong-kwargs`):** الاستدعاء `audit_log(user_id=..., tenant_id=..., action=..., resource_id=..., details=...)` (`invitations/service.py:328-334`) بيحصل **بعد** `await self.db.commit()` (سطر 324) — يعني كل الكتابة الحرجة (اليوزر، المحفظة، الـlead، تحديث حالة الدعوة) **اتحفظت فعليًا على القرص قبل ما الكراش يحصل**. نفس النمط بالحرف الموثَّق سابقًا لـ`manufacturing.start_production`/`arbitration_syndicates.join_syndicate` (`constructor-mismatch-session-log.md`). **هذا استدعاء `audit_log` تحديدًا لم يكن ممكن الوصول له في أي جلسة سابقة** (كل محاولة سابقة كانت بتكراش أبكر بكتير، عند إغلاق الـSAVEPOINT) — فهو تأكيد إضافي (مش اكتشاف جديد خارج الفئات الموثقة، فئة Backlog #14 نفسها موجودة ومعروفة) على مدى انتشار هذه الفئة، **صفر علاقة بإصلاح هذه الجلسة، صفر إصلاح عليه هنا.**

**كمان لاحظت لوج مهم: `Duplicate registration blocked for key: INV-ACCEPT-T1-2` (وبالمثل `INV-ACCEPT-T1-3`)** — دليل مباشر إن آلية الـidempotency الثابتة اشتغلت: التشغيلة السابقة (قبل إصلاح بيانات `discount_percentage`) كانت فعلًا وصلت لإنشاء اليوزر بنجاح قبل ما تكراش على `NULL` في سطر 304 — فلما اتعاد التشغيل، `register()` لقت نفس اليوزر عبر المفتاح الثابت ورجّعته **بدل ما تنشئ يوزر مكرَّر**.

### 7.5) التحقق المستقل النهائي — `SELECT` مباشر بعد كل المحاولات (Session/اتصال منفصل تمامًا)

```sql
SELECT id, title, status, current_uses FROM sovereign_invitations_v2 WHERE id IN (2,3);
SELECT id, email, tenant_id, is_active, idempotency_key FROM users WHERE email IN (...);
SELECT w.id, w.user_id, w.tenant_id, w.balances FROM wallets w JOIN users u ON u.id=w.user_id WHERE u.email IN (...);
SELECT id, tenant_id, converted_user_id, source_reference, status FROM crm_leads WHERE source_reference IN ('INV-2','INV-3');
```

| الجدول | دعوة `id=2` (قبول نظيف) | دعوة `id=3` (فشل جزئي ثم retry) |
|---|---|---|
| `sovereign_invitations_v2.status` | **`ACCEPTED`** | **`ACCEPTED`** |
| `sovereign_invitations_v2.current_uses` | **`1`** | **`1`** (مش `2` — صفر ازدواج رغم محاولتين) |
| `users` | **`id=71`, `p_savepoint_fix_verify_clean@eppne.com`, `is_active=t`, `idempotency_key=INV-ACCEPT-T1-2`** — **يوزر واحد فقط** | **`id=72`, `p_savepoint_fix_verify_retry@eppne.com`, `is_active=t`, `idempotency_key=INV-ACCEPT-T1-3`** — **يوزر واحد فقط رغم محاولتين** |
| `wallets` | **`id=68, user_id=71`** — **محفظة موجودة فعليًا** | **`id=69, user_id=72`** — **محفظة موجودة فعليًا** |
| `crm_leads` | **`id=3, converted_user_id=71, status=CONVERTED`** | **`id=4, converted_user_id=72, status=CONVERTED`** |

**الخلاصة القاطعة:** السلوك الأصلي للباج (يوزر حقيقي بلا محفظة، دعوة تفضل `SENT` للأبد) **اختفى بالكامل** في السيناريوهين:
- **السيناريو النظيف:** يوزر واحد **بمحفظة كاملة**، دعوة **`ACCEPTED`**، lead **`CONVERTED`** — بدل الكراش الأصلي عند `db.refresh()`.
- **سيناريو الـretry:** المحاولة الأولى فشلت (فشل مُفتعَل بعد إنشاء اليوزر) — اليوزر اتعمل بمحفظة كاملة (بفضل نقل الاستدعاء بره `begin_nested()`)، **لكن الدعوة فضلت `SENT` مؤقتًا**. المحاولة الثانية **نجحت فعليًا وأكملت القبول** (`ACCEPTED`, lead `CONVERTED`) باستخدام **نفس اليوزر بالظبط** (`id=72` مش يوزر جديد) — **صفر ازدواج، صفر يوزر يتيم متروك**. هذا يثبت حل مشكلة الـretry (السؤال 2 من الجولة التوضيحية) بشكل قاطع، مش نظري فقط.

---

## 8) ✅ ختم الإغلاق الرسمي [2026-08-18]

**الحالة النهائية: 🟢 مُغلَق.** موافقة صريحة من المستخدم بعد مراجعة كل قسم من هذا التقرير خطوة بخطوة (جدول الأدلة، جولتا الأسئلة التوضيحية، الديف الخام، `git diff`/`git status` بعد التطبيق، والتحقق الحي الكامل).

### الملخص التنفيذي النهائي

**السبب الجذري (كان):** `UserRepository.create()`/`WalletRepository.create()` (`identity/repository.py:56-60, 231-240`) بتعمل `commit()` مباشر — بيقفل الـSAVEPOINT بتاع `begin_nested()` الخاص بـ`invitations.accept_invitation` (كان سطر 286) لما بتنادي `UserService.register()` من جواه عبر `_create_user_from_invitation`. النتيجة: يوزر حقيقي بيتسجَّل فعليًا على القرص (`commit()` ناجح)، **بلا محفظة** (الكراش بيوقف التنفيذ قبل `WalletRepository.create()`)، والدعوة تفضل `SENT` بلا أي مسار نجاح ممكن. الدليل الحي: `users id=52` (`p_ctor_inv_newuser@eppne.com`).

**الحل المُطبَّق (`invitations/service.py` فقط، صفر لمس على `identity/repository.py`/`identity/service.py`):**
1. نقل استدعاء `_create_user_from_invitation` بره `begin_nested()` بالكامل — معاملة مستقلة غير متداخلة.
2. تثبيت `idempotency_key` الممرَّر لـ`UserService.register()` بصيغة `f"INV-ACCEPT-T{tenant_id}-{invitation_id}"` بدل `uuid.uuid4()` العشوائي — لضمان أمان إعادة المحاولة بعد أي فشل جزئي لاحق، عبر آلية idempotency الموجودة أصلًا (`get_by_idempotency_key`، قراءة فقط، صفر لمس على `create()`).

**التحقق الحي:** سيناريوهان (قبول نظيف + فشل جزئي مُفتعَل ثم retry)، بيانات جديدة تمامًا (`users id=71, 72`، دعوات `id=2, 3`) — `users id=52`/دعوة `id=1` لم يُلمَسا إطلاقًا. **النتيجة في الحالتين: يوزر واحد بمحفظة كاملة، دعوة `ACCEPTED`، lead `CONVERTED`** — مؤكَّد بـ`SELECT` مستقل (قسم 7.5). سيناريو الـretry أثبت تحديدًا: صفر يوزر مكرَّر رغم محاولتين، `current_uses=1` مش `2`.

**اكتشافات جانبية موثَّقة (خارج نطاق هذا الإغلاق، بنود Backlog منفصلة في `PROGRESS_LOG.md`):**
- `invitations-missing-expiry-max_uses-validation` — فجوة تحقق `expires_at`/`max_uses` غير منفَّذة، أولوية أعلى من العادي.
- بند صغير أولوية منخفضة عن أعمدة `sovereign_invitations_v2` القابلة لـ`NULL` بلا `NOT NULL`/server-side default.
- تأكيد إضافي (فئة موثَّقة مسبقًا، Backlog #14) لوجود `audit-log-wrong-kwargs` جوه `accept_invitation` نفسها — بعد الـ`commit()` النهائي، صفر أثر على سلامة البيانات.

**القيد على Backlog #9 اتشال رسميًا** — كان ممنوع إصلاحه قبل إغلاق هذه الثغرة (كان هيفتح مسار استغلال فوري)؛ الآن مسموح فتح جلسة مستقلة له.

**تنظيف throwaway:** `users id=52` (الدليل الأصلي) + `users id=71, 72`/دعوات `id=2, 3` (بيانات التحقق) **يُتركوا كما هم** — تنظيف روتيني عادي غير عاجل، مش جزء من هذا الإغلاق.

**الحالة: 🟢 مُغلَق. صفر عمل متبقٍ في هذه الجلسة.**
