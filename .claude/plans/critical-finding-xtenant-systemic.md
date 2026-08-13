# اكتشاف حرج نظامي — ثقة `X-Tenant-ID` بديلًا عن `current_user.tenant_id` في 20 دومين + فئة مستقلة (identity) من 34 دومين حقيقي (+1 دومين محذوف مستبعد من العدّ)

> # 🔴🔴🔴 تحذير إلزامي — اقرأ قبل أي إصلاح على `sovereign_entities` — يخص أي جلسة `SimpleTenant`/X-Tenant-ID مستقبلية
>
> **لو انت (أو أي Claude Code تاني، أي جلسة، أي سياق) بتفكر تصلح باج
> `SimpleTenant`/type-mismatch في `sovereign_entities/router.py`: توقف
> هنا الأول.**
>
> أربعة endpoints في `sovereign_entities/router.py` — `list_entities`
> (سطر ~41)، `get_entity` (سطر ~72)، `list_templates` (سطر ~339)،
> `list_components` (سطر ~349) — **معندهمش `current_user` في توقيعها
> إطلاقًا**. القاعدة الميكانيكية المعتادة (`tenant_id: int =
> Depends(get_current_tenant)` → `tenant_id = cast(int,
> current_user.tenant_id)`) **غير قابلة للتطبيق عليهم حرفيًا، ولو
> اتطبّقت بأي شكل بديل ساذج (زي مجرد تصحيح `tenant.id` بدون إضافة فحص
> هوية) هتفتح ثغرة تسريب مالي/KYB حقيقية cross-tenant فورًا** —
> التفاصيل الكاملة، الدليل الحي، والتحليل الدقيق في تقرير مخصَّص:
> **`.claude/reports/CRITICAL-sovereign-entities-unauthenticated-endpoints.md`**
> — اقرأه بالكامل أولًا.
>
> **الوضع الحالي (بتاريخ 2026-08-13):** الأربعة endpoints دول **لسه
> فيهم باج `SimpleTenant` الأصلي غير مُصلَح عمدًا** — استُثنوا صراحة من
> إصلاح `SimpleTenant` الشامل اللي اتطبّق على باقي المشروع (راجع
> `.claude/reports/simpletenant-fix-session-log.md`)، **بانتظار قرار
> منتجي/أمني صريح من المستخدم**: هل الأربعة دول المفروض يبقوا public
> بتصميم مقصود (ووقتها لازم مراجعة الحقول المُرجَعة أصلًا — إخفاء
> `treasury_balance_mrusdt`/`kyb_status`/`wallet_address` عن أي نسخة
> عامة)، ولا يتحولوا لمحمية بـ`current_user` إجباري زي باقي الدومين؟
> **القرار ده لسه معلّق، مؤجَّل لجلسة مخصَّصة — صفر افتراض، صفر إصلاح
> تلقائي.**
>
> **باقي الـ21 موضع (18 endpoint) في `sovereign_entities` اتصلحوا
> بالفعل بنجاح** (نفس القاعدة الميكانيكية، مؤكَّدة حيًا) — التحذير ده
> يخص الأربعة دول بالذات بس.

> **تحديث [2026-08-11] — Phase 14 (فحص read-only إضافي لسدّ فجوة في
> الفحص الأصلي، صفر تنفيذ):** الفحص الأصلي (29 دومين) كان ناقصًا — 6
> مجلدات فعلية تحت `app/domains/` لم تُغطَّ إطلاقًا: `admin`, `auth`,
> `identity`, `invoicing`, `iot`, `privacy`. اتفحصت الستة كلهم الآن بنفس
> منهجية التقرير الأصلي بالظبط (قراءة كود فقط، بلا استثناء أي واحد منهم
> من التصنيف). النتيجة: `admin`/`invoicing`/`iot`/`privacy` **🟢 SAFE**،
> `auth` **⚪ N/A** (Phase 4 حذفت كل كوده، صفر ملف `.py` باقٍ)، و
> `identity` **🟡 فئة مختلفة تمامًا، وليست رقم 21 في جدول SUSPICIOUS**
> — بعد تتبّع الكود بدقة تبيَّن إن جذرها التقني هو `get_current_tenant`
> نفسه، لكن شكل الثغرة مختلف جوهريًا عن الـ20 دومين (ثغرة صلاحية على
> **تسجيل** حساب تحت tenant عشوائي، pre-auth، لا يوجد `current_user`
> أصلًا للمقارنة معه — مش IDOR على مورد موجود بالفعل زي باقي الـ20).
> **هذا الفارق حرج لأن الإصلاح المركزي المقترح تحت (قسم "الاقتراح
> المعماري") صراحة بيستثني مسارات pre-auth ولا يغطي ثغرة identity دي
> إطلاقًا** — تفاصيل كاملة في قسمها المخصَّص تحت. الحصيلة الجديدة:
> **20 SUSPICIOUS (نمط IDOR/header-spoofing) + 1 مصنَّف منفصلًا
> (identity) + 13 SAFE = 34 دومين حقيقي مُصنَّف** (من 35 مجلد فعلي
> إجمالًا، `auth` مستبعد من العدّ لعدم وجود كود قابل للفحص).

> **تحديث [2026-08-13] — تصحيح/استكمال تبرير تصنيف `finance` كـSAFE
> (اكتُشف أثناء جلسة منفصلة عن باج `commit()`/`begin_nested()`، راجع
> `.claude/reports/transaction-savepoint-bug-session-log.md`):**
> التبرير الأصلي لـ`finance` في جدول 🟢 SAFE (تحت) — "`SystemState` صف
> عالمي واحد أصلًا (بدون عمود tenant_id)، `mint_currency` مربوط
> بـ`current_user`" — **كان يغطي الـ4 admin endpoints بس**
> (`crypto-mode`, `exchange-rates`, `mint`, `max-supply`)، ولم يفحص
> صراحة الـ4 endpoints العاديين (`transfer`, `swap`, `balances`,
> `history`) رغم استخدامهم لنفس `get_current_tenant`.
>
> **تتبّع دقيق منفصل (2026-08-13) أكَّد إن التصنيف SAFE صحيح لهم
> الأربعة كمان، لكن لسبب مختلف عن اللي كان مكتوب:**
> - `transfer`: `sender_id` دايمًا `current_user.id` (JWT، غير قابل
>   للتزوير). محفظة المرسل مفلترة بـ`user_id` **و** `tenant_id`-هيدر
>   معًا (`finance/repository.py`). المستلم مفلتر بـ`email` **و**
>   `tenant_id` معًا، وعمود `email` **unique عالميًا** على مستوى
>   المنصة (`identity/models.py:35`، مش per-tenant) — تزوير الهيدر
>   بيرجّع "غير موجود"، مش تسريب.
> - `swap`: نفس فلترة `transfer` لمحفظة المستخدم، ومفيش طرف تاني
>   إطلاقًا (أبسط وأأمن من `transfer`).
> - `balances`: نفس الفلترة المزدوجة، تزوير الهيدر بيعمل "محفظة شبح"
>   فاضية بدل ما يوصل لمحفظة حد تاني.
> - `history`: الاستعلام (`get_by_user_paginated`) بيفرض
>   `sender_id=$user_id OR receiver_id=$user_id` **دايمًا** بغض النظر
>   عن أي صف `users` اتربط في الـjoin — مستحيل ترجع معاملة المستخدم
>   مش طرف فيها.
>
> **الخلاصة المُحدَّثة:** الأثر العملي الوحيد المؤكَّد لثقة الهيدر في
> `finance` هو **"محافظ شبح"** (`Wallet` جديد فاضي تحت تينانت غلط لو
> الهيدر ماتطابقش الحقيقي) — تلوث بيانات محتمل، **مش سرقة أموال ولا
> تسريب بيانات cross-tenant**. هذا يفرّق `finance` جوهريًا عن
> `realestate`/`digital_twin`/`automation` (صفر ربط بـ`current_user`،
> ثغرة فعلية مؤكَّدة).
>
> **باج منفصل تمامًا اكتُشف وأُصلح بنفس الجلسة (خارج نطاق X-Tenant-ID
> بالكامل):** `finance/router.py` (كل الـ8 endpoints) كان بيمرّر كائن
> `SimpleTenant` (من `get_current_tenant`) لـ`FinanceService` بدل
> `int` خام — `TypeError`/`DataError` قاطع يمنع أي استخدام لـ
> `finance/router.py` بالكامل، بغض النظر عن أي تصنيف أمني. **الإصلاح
> المطبَّق (2026-08-13) استبدل `get_current_tenant` بـ
> `current_user.tenant_id` في الـ8 endpoints كلهم** (نفس نمط الإصلاح
> المركزي المقترح تحت — قسم "الاقتراح المعماري" — لكن مُطبَّق على
> `finance` فقط، مش مركزيًا على الـ19 دومين الباقيين). تحقق حي كامل
> (تحويلين فعليين متتاليين بين محفظتين اختباريتين + `SELECT` مباشر على
> الأرصدة) أكَّد الإصلاح شغال 100%. التفاصيل الكاملة في
> `transaction-savepoint-bug-session-log.md`.
>
> **الحصيلة المُحدَّثة لـ`finance`:** يبقى 🟢 SAFE (مؤكَّد بتتبّع أعمق
> من الفحص الأصلي)، **وبقى كمان أول دومين من الـ20+ اللي فعليًا
> اتصلح نفس نمط `get_current_tenant` → `current_user.tenant_id`** —
> سابقة عملية لأي قرار مستقبلي (مركزي/تدريجي) بخصوص باقي الدومينات.

## هذا تقرير تشخيصي بحت. صفر تنفيذ. صفر قرار نهائي.
لا يحتوي هذا الملف أي خطوات تنفيذ ولا أي التزام بجدول زمني. القرار
(إصلاح مركزي واحد مقابل إصلاح دومين ورا التاني، ونطاق أي تنفيذ) مؤجَّل
بالكامل لجلسة/جلسات منفصلة، بخطة اختبار شاملة عبر كل الدومينات
المتأثرة — مش رد سريع في نفس جلسة Phase 10c.

## السياق
أثناء تنفيذ Phase 10c (إصلاح ثغرة X-Tenant-ID المؤكَّدة حيًا في
الـ4 admin endpoints بـ`affiliate/router.py` — راجع commit `165e445`
و`PROGRESS_LOG.md` لتفاصيل الإصلاح والتحقق الحي الكامل)، اتسأل سؤال
معماري: هل نفس نمط الثقة العمياء بهيدر `X-Tenant-ID` (بدل
`current_user.tenant_id` الموثوق من التوكن) موجود في دومينات تانية
غير affiliate؟

## المنهجية
- **فحص read-only بالكامل** — 3 agents متوازية، كل واحد غطّى ~9-10
  دومينات، بقراءة كود فقط (`router.py` + الأجزاء ذات الصلة من
  `service.py`/`repository.py`). **صفر اختبار حي، صفر طلب HTTP، صفر
  لمس DB.**
- **معيار التصنيف:** لكل دومين، هل فيه endpoint محمي بصلاحية مرتفعة
  (`get_current_superuser` أو مكافئه) بيقرأ/يكتب مورد **غير مرتبط
  بملكية المستخدم الحالي** (زي إعدادات tenant-wide، سجلات مالية، بيانات
  كيانات تانية) معتمدًا على `tenant_id`/`tenant.id` الجاي من
  `get_current_tenant` (الهيدر)، **بدون** أي مقارنة مع
  `current_user.tenant_id` الحقيقي؟
- **مرجع الشكل المؤكَّد حيًا:** `affiliate/admin/tiers` (قبل إصلاح
  Phase 10c) — سوبريوزر من tenant=1 قرأ وعدَّل `CommissionTier` تخص
  tenant تاني بمجرد تغيير الهيدر، بلا أي فحص.
- **الفارق المهم اللي اتأكَّد أثناء تحليل affiliate نفسها:**
  الـendpoints المرتبطة بملكية مستخدم (`WHERE user_id == current_user.id
  AND tenant_id == header`) **مش عرضة لنفس النوع من التسريب** لأن
  `user_id` مش قابل للتزوير — الهيدر لوحده مايكفيش يجيب بيانات مستخدم
  تاني. الخطر الحقيقي محصور بالموارد اللي **مالهاش مالك على مستوى
  المستخدم** (إعدادات، سجلات إدارية، كيانات مشتركة على مستوى الـtenant).

## نتيجة التصنيف (29 دومين + affiliate كمرجع)

### 🔴 SUSPICIOUS — نفس شكل ثغرة affiliate المؤكَّدة، أو أسوأ (20 دومين شاملين affiliate)

| # | Domain | الدليل (file:line) | الوصف |
|---|---|---|---|
| 1 | **affiliate** | `affiliate/router.py` (قبل commit `165e445`) | **المرجع — مؤكَّد حيًا (قراءة+كتابة)، مُصلَح في Phase 10c** |
| 2 | academy | `academy/router.py:578-585` (`get_financial_summary`)، `:79-87`, `:124-132`, `:154-162` | سوبريوزر يقرأ/يكتب ملخص مالي وبيانات تنظيمية tenant-wide عبر هيدر مزوَّر |
| 3 | agritech | `agritech/router.py:49-58`, `:189-204` | ⚠️ **ملاحظة بنيوية منفصلة تمامًا (خارج نطاق ثغرة X-Tenant-ID):** الملف ده أصلًا نسخة قديمة زايدة من `ai_governance` (`APIRouter(prefix="/ai-governance")`)، بيسبب تصادم مسارات حقيقي مع `ai_governance_router` في `main.py`. كود agritech الحقيقي (farms/zones/crop-cycles في `agritech/service.py`/`models.py`) مش معروض بأي router أصلًا. يستاهل تبليغ منفصل للفريق. |
| 4 | ai_agents | `ai_agents/router.py:105-122` → `service.py:117-141` | سوبريوزر يعدّل/يحذف agent يخص tenant تاني (بلا فحص owner_id) |
| 5 | ai_governance | `ai_governance/router.py:26-43,75-90,93-110,130-145,148-172` | quotas/rate-limits/audit-logs/usage-summary عبر هيدر مزوَّر، بلا فحص الموجود في الـendpoints غير الإدارية بنفس الملف |
| 6 | arbitration_syndicates | `router.py:101-121` → `service.py:255-257` | فحص الملكية بيقارن ضد الهيدر نفسه (`case.tenant_id != tenant_id` — الطرفين من نفس المصدر الملوَّث)، مش ضد `current_user.tenant_id` — إصدار حكم على قضية tenant تاني |
| 7 | automation | `automation/router.py:305-349` (`create_secret`/`list_secrets`/`delete_secret`) | **أسوأ من affiliate:** مفيش حتى فحص superuser — أي مستخدم عادي يقدر يقرأ/يمسح secrets (API keys) بتاعة tenant تاني |
| 8 | command | `command/router.py:42-57,60-89,327-341` | brand settings + platform metrics tenant-wide؛ `get_my_brand`/`update_my_brand` مش محمية بـsuperuser أصلًا |
| 9 | communications | `router.py:398-423,426-433` | قوالب تواصل tenant-wide تُنشأ/تُعرض عبر هيدر مزوَّر |
| 10 | digital_twin | `router.py:190-208` → `service.py:342-389` | **الأخطر تأثيرًا:** تأكيد وفاة + توزيع تركة/أصول فعلي لمستخدم tenant تاني، بفحص واحد بس (تطابق الهيدر مع tenant الـoracle — الهيدر نفسه مصدر غير موثوق) |
| 11 | health | `router.py:211-226` → `service.py:370-381` | إنشاء `HealthFacility` tenant-wide عبر هيدر؛ حاليًا self-DoS ببق `NameError` منفصل تمامًا قبل ما يوصل لنقطة الاستغلال |
| 12 | insurance | `router.py:24-38,209-224,256-271` → `service.py` | بوالص تأمين/معاشات/ملفات موظفين تُنشأ عبر هيدر؛ `disburse_pensions` أسوأ (بيتجاهل الـtenant تمامًا، بيصرف لكل الـtenants) |
| 13 | manufacturing | `router.py:265-279,359-373` → `service.py:583-600,721-735` | شهادات جودة/قطع غيار تُزرع في أي tenant عبر هيدر |
| 14 | realestate | `router.py:48-58` (`revalue_land`) | **الأسوأ في القائمة كلها:** صفر فحص tenant حتى بالهيدر — أي سوبريوزر من أي tenant يقدر يغيّر قيمة أي عقار مباشرة |
| 15 | saas | `router.py:222-234` → `service.py:332-347,361-362` | `TenantFeatureFlag` (إعدادات تنشيط ميزات) تُقرأ/تُكتب عبر هيدر |
| 16 | service_marketplace | `router.py:44-56,151-162,58-81` | إنشاء خدمة/إضافة عبر هيدر مزوَّر؛ `publish/unpublish` **بصفر تحقق tenant إطلاقًا** (أسوأ من الهيدر نفسه) |
| 17 | social | `router.py:315-328` → `service.py:594-597` | 🟠 أقل حدة — إنشاء بس (خطط اشتراك جماعية)، مفيش قراءة/تعديل بيانات موجودة لتينانت تاني |
| 18 | sovereign_entities | `router.py:190-207` → `service.py:193-218` | **تطابق كامل مع شكل affiliate:** مراجعة/اعتماد KYB لكيان tenant تاني موجود بالفعل |
| 19 | tourism_sports | `router.py:17-28,41-52,69-80,150-161` | 🟠 أقل حدة — إنشاء بس (وجهات/برامج/فعاليات/بطولات) |
| 20 | transport | `router.py:68-79` → `service.py:142-149` | **تطابق كامل:** تعديل موقع GPS حي لمركبة tenant تاني موجودة؛ + عدة create-only بنفس النمط |

**ملاحظة صريحة (Phase 14):** `identity` **ليس** رقم 21 في الجدول ده
عمدًا — رغم اعتماده على نفس دالة `get_current_tenant`، شكل ثغرته مختلف
جوهريًا (pre-auth، لا يوجد مورد موجود بالفعل يُقرأ/يُكتب، ولا يوجد
`current_user.tenant_id` أصلًا للمقارنة معه). مُصنَّف في قسم منفصل تحت
("🟡 فئة مختلفة") عشان الخلط بينه وبين نمط IDOR الموجود هنا كان هيوهم
بإن الإصلاح المركزي المقترح (قسم "الاقتراح المعماري") بيغطيه — وهو مش
بيغطيه.

### 🟡 فئة مختلفة تمامًا — ثغرة صلاحية عند التسجيل (Pre-Auth Tenant
Self-Enrollment)، **لا يغطيها الإصلاح المركزي المقترح** (Phase 14)

**الدومين:** `identity`. **الجذر التقني:** نفس `get_current_tenant`
(`api/deps.py:148-153`) المستخدَم في الـ20 دومين فوق، لكن **الاستغلال
مختلف تمامًا في الشكل والتأثير والإصلاح المطلوب**:

| الفرق | الـ20 دومين (IDOR / header-spoofing) | identity (هذه الفئة) |
|---|---|---|
| هل المستخدم مُصادَق عليه وقت الهجوم؟ | نعم — عنده JWT صالح لتينانته الحقيقي | **لا** — `register`/`login` قبل وجود أي هوية |
| هل فيه `current_user.tenant_id` موثوق يُقارَن به؟ | نعم، موجود ومُتجاهَل | **لا يوجد أصلًا** — دي المشكلة |
| الفعل المُستغَل | قراءة/تعديل **مورد موجود بالفعل** يخص tenant تاني | **إنشاء** حساب جديد تحت أي tenant، بلا دعوة/تفويض |
| هل يغطيه الإصلاح المركزي المقترح تحت؟ | نعم، مباشرة | **لا — الإصلاح المقترح نفسه بيستثني مسارات pre-auth عمدًا** (راجع `api/deps.py` المقترح، تعليق "pre-auth فقط") |

**الدليل (file:line):**
- `identity/router.py:30` (`register`) → `identity/service.py:90` —
  `tenant_id=self.tenant_id` (قيمة من الهيدر عبر `get_current_tenant`)
  بيتكتب مباشرة في صف `User` جديد، **بدون أي مصادقة أو تفويض إطلاقًا**.
- `identity/service.py:117-123` (`_issue_tokens`) — القيمة دي بعدين
  بتتحط كـclaim `tenant_id` في الـJWT الموقَّع الصادر، فتبقى هي
  `current_user.tenant_id` "الموثوق" لباقي حياة الجلسة عبر كل دومين
  تاني في المشروع.
- **مؤكَّد حيًا مسبقًا (Phase 9، `phase9-audit-identity-report.md`،
  2026-08-10):** تسجيل مستخدم فعلي تحت `tenant_id=2` بهيدر
  `X-Tenant-ID: 2` نجح **بلا أي دعوة أو تفويض**.
- `identity/router.py:42` (`login`) → `service.py:107` — **فحص هذا
  المسار تحديدًا أثبت إنه SAFE فعليًا**: `get_by_username_or_email(...,
  self.tenant_id)` بيفلتر بالاتنين معًا (username/email **و** tenant من
  الهيدر)، فهيدر مخالف لتينانت الحساب الحقيقي بيرجّع "مستخدم غير موجود"
  ويفشل تسجيل الدخول — مفيش تسريب أو تجاوز ممكن هنا، الخطر محصور في
  `register` بس.
- **الـ8 endpoints المحمية الباقية في identity (`me`, `sessions`,
  `revoke-all`, `me/password`, `me` DELETE) مؤكَّدة SAFE حيًا في نفس
  جلسة Phase 9** — مثال `service.py:232`
  (`get_by_id(user_id, self.tenant_id)`) بيفلتر بـ`current_user.id`
  **و** `tenant.id` معًا، فهيدر مزوَّر بيرجّع 404 (fail-safe)، مش
  تسريب بيانات مستخدم تاني.

**لماذا مهم إفراده عن الجدول:** الاقتراح المعماري المطروح في هذا الملف
(قسم "الاقتراح المعماري للنقاش" تحت) بيفترض صراحة إن استخدام الهيدر في
`register`/`login` "استخدام شرعي" لأنه pre-auth، وبيبقيه كما هو حتى بعد
أي إصلاح مركزي. **هذا الافتراض صحيح تقنيًا (مفيش `current_user` بديل)
لكنه لا يعني إن ثغرة identity محلولة أو غير موجودة** — فقط يعني إنها
**خارج نطاق أي إصلاح مركزي لباقي الـ20 دومين، ومحتاجة تصميم إصلاح مستقل
بالكامل** (مثال: آلية دعوة/تفويض حقيقية لانضمام tenant عند التسجيل،
مش أي تعديل على `get_current_tenant` نفسها).

### 🟢 SAFE (بتحفظات مسجَّلة لكل واحد — مش "نظيف 100%" بالضرورة)

| Domain | السبب | تحفظ |
|---|---|---|
| commerce | كل المسارات الحساسة AND مع `current_user.id` | `create_store`/`create_product` فيها ثغرة عزل tenant مختلفة الشكل (مش admin-gated، إنشاء فقط) — غير مصنَّفة SUSPICIOUS لأنها مش نفس الشكل، لكن تستاهل نظر منفصل |
| employment | لا admin endpoints | — |
| finance | `SystemState` صف عالمي واحد أصلًا (بدون عمود tenant_id)، `mint_currency` مربوط بـ`current_user` | سؤال منتجي منفصل: هل أي سوبريوزر من أي tenant يُفترض يقدر يغيّر إعدادات عالمية؟ (مش ثغرة header-spoofing، لكن سؤال صلاحيات) |
| invitations | لا admin endpoints | — |
| logistics | استيراد `get_current_superuser` ميت، لا admin endpoints فعلية | — |
| projects | لا admin endpoints | — |
| tenders_auctions | لا admin endpoints | — |
| translation | كل شيء مربوط بـ`current_user` | — |
| zamakana | مربوط بـ`user_id` في العمليات الحساسة | — |
| **admin** (Phase 14) | endpoint واحد بس (`toggle-ai-agents`, `router.py:9-21`)، محمي بـ`get_current_superuser`، بيغيّر flag نظامي عالمي (مش مورد tenant-scoped)، **صفر استخدام لـ`get_current_tenant`/الهيدر** (grep شامل على المجلد كله، صفر نتائج) | الراوتر أصلًا **غير مسجَّل في `main.py`** (grep صفر نتائج) — الـendpoint غير قابل للوصول حاليًا بأي حال، بغض النظر عن التصنيف |
| **invoicing** (Phase 14) | **صفر استخدام لـ`get_current_tenant`/`X-Tenant-ID` في كامل الدومين** (`router.py` + `service.py`، grep شامل صفر نتائج). التحكم بالـtenant كله عبر `current_user.tenant_id`/`system_role` (`router.py:93,128-135,299-304`). الـendpoint الإداري الوحيد (`process_overdue_invoices`, `router.py:318-324`) بلا معامل tenant، بيعالج كل الفواتير عالميًا بتصميم | ⚠️ **ملاحظة أمنية منفصلة تمامًا عن نمط X-Tenant-ID — راجع قسم مخصَّص تحت** (`create_invoice` بياخد `tenant_id` من جسم الطلب مباشرة بلا أي فحص) |
| **iot** (Phase 14) | كل الـ11 استخدام لـ`tenant_id` (شامل الـendpoint الإداري الوحيد `create_grid`, `router.py:99-103`) بتستخدم `current_user.tenant_id` الحقيقي (`router.py:31,49,68,85,103,118,144,165,192,213,228`). **صفر استخدام لـ`get_current_tenant`/الهيدر** (grep صفر نتائج) | — |
| **privacy** (Phase 14) | كل الـ7 استخدامات لـ`tenant_id` بتستخدم `current_user.tenant_id` الحقيقي (`router.py:35,56,94,131,173,204,242`). **صفر استخدام لـ`get_current_tenant`/الهيدر** (grep صفر نتائج) | — |

### ⚪ N/A — دومين محذوف بالكامل، غير قابل للتصنيف (Phase 14)

| Domain | السبب | الدليل |
|---|---|---|
| **auth** | Phase 4 (commit `eeaf783`، موثَّق في `PROGRESS_LOG.md` بتاريخ 2026-08-10) حذفت كل كوده فعليًا (7 ملفات، 732 سطر) | `ls app/domains/auth/` → `__pycache__` بس، **صفر ملف `.py`** (لا `router.py` ولا حتى `__init__.py`). `grep` على `main.py` لـ`domains.auth`/`auth_router`/`auth_protected_router` → **صفر نتيجة**. لا يوجد كود قابل للفحص، فتصنيف SUSPICIOUS/SAFE غير منطبق أصلًا — مُدرَج هنا للتوثيق الرسمي بدل الاستبعاد الصامت |

### ⚠️ ملاحظة أمنية منفصلة (Phase 14، خارج نطاق نمط X-Tenant-ID): `invoicing/create_invoice`

فئة ثغرة مختلفة تمامًا عن ثقة الهيدر (نفس سابقة `commerce.create_store`/
`create_product` في التقرير الأصلي) — **لا تُحسب ضمن عدّ SUSPICIOUS/SAFE
لنمط X-Tenant-ID، موثَّقة هنا فقط لأنها اكتُشفت بالصدفة أثناء فحص
invoicing**:

`POST /invoicing/invoices` (`invoicing/router.py:42-70`) بيمرّر
`entity_id=data.tenant_id` (`router.py:54`) مباشرة من جسم الطلب
(`InvoiceCreate.tenant_id`) لإنشاء الفاتورة، **بدون أي admin-gate وبدون
أي مقارنة مع `current_user.tenant_id`**. أي مستخدم مصادَق عادي
(`get_current_active_user` فقط، مش superuser) يقدر نظريًا يحدد
`tenant_id` عشوائي في جسم الطلب وينشئ فاتورة تحت tenant تاني بالكامل —
شكل mass-assignment عبر الـbody، مش هيدر. **غير مؤكَّد حيًا، ومحتاج
مراجعة/phase منفصل بالكامل لاحقًا** (يشمل التحقق: هل ده سلوك مقصود
لحالة استخدام إدارية معينة، ولا فعلًا فجوة تحتاج ربط `entity_id` بـ
`current_user.tenant_id` عند عدم وجود صلاحية إدارية؟).

**الحصيلة: 20 SUSPICIOUS (منهم affiliate، دلوقتي مُصلَحة) + 1 مصنَّف
في فئة منفصلة (identity — راجع قسمها المخصَّص فوق) + 13 SAFE (9 من
التقرير الأصلي + 4 من Phase 14) = 34 دومين حقيقي مُصنَّف بالكامل.
`auth` مستبعد من هذا العدّ (دومين محذوف بالكامل، صفر كود). صفر
NEEDS_DEEP_INSPECTION عبر كل الـ34.**

**تنبيه مهم:** التصنيف ده كله من قراءة كود (زي Phase 10 قبل التحقق
الحي). زي ما حصل بالظبط مع affiliate (قراءة الكود قالت "الغالب آمن"
لحد ما التحقق الحي كشف باج `SimpleTenant` وقلب النتيجة)، **أي دومين
SUSPICIOUS هنا محتاج تحقق حي فعلي قبل ما يتصلح فعلًا** — الأولوية
المرشَّحة من شدة الأثر: `realestate` (صفر فحص من الأساس)، `digital_twin`
(توزيع أصول/تركة)، `automation` (secrets بلا حماية admin أصلًا)،
`insurance.disburse_pensions` (يتجاهل الـtenant تمامًا).

## الاقتراح المعماري للنقاش (غير مُقرَّر، غير مُنفَّذ)

بما إن الأصل التقني واحد في كل الحالات (`get_current_tenant` في
`api/deps.py:148-153`)، وبما إن الفحص أثبت **صفر استخدام شرعي مقصود**
للهيدر في أي مسار مُصادَق عليه عبر كل الـ29 دومين (الاستخدام الشرعي
الوحيد محصور بمسارات pre-auth زي `identity/register`/`login`، اللي
مفيهاش `current_user` أصلًا)، الاقتراح المطروح للنقاش (**مش قرار،
محتاج تحقق حي واسع جدًا قبل أي التزام**):

> ⚠️ **تحديث Phase 14:** الكلمة "استخدام شرعي" هنا وصف **تقني** بس
> (مفيش `current_user` بديل يُقارَن بيه في pre-auth) — **مش تأكيد إن
> استخدام الهيدر في `register` آمن فعليًا**. Phase 9 أثبت حيًا إن
> `identity/register` بالذات فيه ثغرة صلاحية حقيقية (تسجيل تحت أي
> tenant بلا دعوة). الإصلاح المقترح تحت **بيبقي هذا الاستخدام كما هو
> عمدًا** (سطر "pre-auth فقط" تحت) — يعني **لا يغطي ولا يصلح** ثغرة
> identity دي. راجع قسم "🟡 فئة مختلفة تمامًا" فوق لتفاصيل كاملة
> والفرق الجوهري عن باقي الـ20 دومين.

```python
async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> SimpleTenant:
    tenant = SimpleTenant()
    if current_user is not None:
        tenant.id = current_user.tenant_id   # مُصادَق عليه → تجاهل الهيدر تمامًا
    else:
        tenant.id = x_tenant_id               # pre-auth فقط (register/login/track العام)
    return tenant
```

**ليه ده جذاب:** بيصلح الـ19 دومين الباقي (مش affiliate، دي خلصت) في
مكان واحد، بدل 19 PR منفصل بنفس النمط بالضبط.

**ليه ده خطير ومحتاج جلسة/جلسات منفصلة كاملة:**
- بيغيّر سلوك المصادقة على **مستوى المنصة كلها** دفعة واحدة — أي خطأ
  فيه بيأثر على كل دومين شغّال، مش دومين واحد.
- محتاج تحقق حي (مش قراءة كود) على **كل واحد من الـ19 دومين على الأقل
  لأعلى endpoint حساسية فيه**، مش عينة — نفس منهجية Phase 9/10/10b/10c
  بالظبط، لكن مضروبة في 19.
- `get_current_user_optional` موجودة فعلًا (`api/deps.py:216`)
  ومُستخدَمة في مسارات عامة تانية — لازم تحقق إنها بترجع `None` بأمان
  (مش تستثني) لو مفيش توكن، بدون كسر أي مسار pre-auth حالي
  (register/login/`affiliate/track/{code}`).
- بعض الدومينات (زي `finance`) عندها سيناريوهات فيها "الهيدر بلا تأثير
  أصلًا" (مورد عالمي بدون tenant_id) — الإصلاح المركزي مش هيأثر عليها
  سلبًا، لكن لازم يتأكَّد لكل حالة على حدة.
- محتاج pytest كامل + `tsc`/فحص frontend (لو فيه أي frontend بيبعت
  الهيدر عمدًا لسبب شرعي محتاج مراجعة) قبل أي اعتماد.

**البديل المرفوض حاليًا (إصلاح دومين ورا التاني، زي affiliate):** أبطأ
(19 دورة إصلاح+تحقق منفصلة)، لكن أقل خطرًا لكل تغيير (نطاق ضيق، تحقق
مركّز). قرار الاختيار بين الاتنين **مؤجَّل بالكامل**.

## الخطوة الجاية (لما يُقرَّر، مش دلوقتي)
لا خطوة جاية محدَّدة في هذا الملف. القرار (مركزي/تدريجي) وتفاصيل خطة
الاختبار يحتاجوا جلسة مخصَّصة منفصلة، بعد ما يهدى الاكتشاف ده ويتراجع
بعناية — مش استمرارية مباشرة لجلسة Phase 10c.
