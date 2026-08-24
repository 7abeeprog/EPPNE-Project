# جلسة فحص IDOR/RBAC في `saas` — استكمال مسار `ai_agents`/`sovereign_entities`/`command`

**بدأ التسجيل:** 2026-08-24
**الحالة:** ⏳ **جارية — تحقق حي جزئي منجَز، لم تُعرَض بعد الخلاصة النهائية للموافقة.**

**الملفات المرجعية المقروءة كاملة قبل البدء:** `simpletenant-fix-session-log.md`، `command-idor-fix-session-log.md`، `critical-finding-xtenant-systemic.md` (صف #15 saas)، `app/domains/saas/{router,service,repository,schemas,models}.py` كاملة، `app/main.py` (تسجيل الراوترز)، `app/domains/finance/service.py` (دالة `transfer`/`get_or_create_wallet_for_update`).

---

## 1) تصحيح/تأكيد الافتراض المرجعي — `saas` لسه في نفس حالة `simpletenant-fix` بالحرف

قراءة `router.py` الحالي (275 سطر) تؤكد: **صفر استخدام لـ`get_current_tenant`** — كل الـ17 endpoint المذكورين في التقرير المرجعي بالفعل `tenant_id = cast(int, current_user.tenant_id)`. الاستثناءان المؤجَّلان بالتصميم لسه كما هما، بلا لمس:
- `get_tenant_subscriptions_admin` (`tenant_id: int = Path(...)`, صريح, سوبريوزر) — عرض إداري عبر-تينانت مقصود.
- `trigger_renewals` (`SaaSControlService(db, 0)` هاردكودد + `tenant_id` اختياري كـquery) — مهمة batch نظامية.

**فحص إزالة `require_sector`:** `main.py:300-308` — كل الراوترز بلا `Depends` إضافي على مستوى التسجيل، والفحص الوحيد المتبقي هو `current_user` المُعلَن صراحة بكل endpoint. **كل الـ19 endpoint في `saas/router.py` عندها `current_user` صريح (active_user أو superuser) — صفر endpoint بلا مصادقة.** `saas` غير متأثر بإزالة `require_sector` (نفس نتيجة `command`/`ai_agents`).

---

## 2) جدول الـ19 endpoint — المستوى، مصدر tenant_id، فلتر الملكية

| # | الدالة | المستوى | مصدر tenant_id | فلتر تينانت في repo؟ | ملاحظة |
|---|---|---|---|---|---|
| 1 | list_services | superuser | current_user.tenant_id | N/A (كتالوج عام) | 🟢 |
| 2 | create_service | superuser | current_user.tenant_id | N/A | 🟢 |
| 3 | get_service | active_user | current_user.tenant_id | N/A (كتالوج عام) | 🟢 |
| 4 | list_service_plans | active_user | current_user.tenant_id | N/A | 🟢 |
| 5 | create_plan | superuser | current_user.tenant_id | N/A | 🟢 |
| 6 | get_my_subscriptions | active_user | current_user.tenant_id | ✅ tenant_id | 🟡 خطأ 500 حي مستقل (راجع §4) |
| 7 | subscribe_to_plan | **active_user** | current_user.tenant_id | ✅ | 🔴 محجوب ببج pre-existing (`get_plan_by_id`)، مؤكَّد حيًا اليوم (§3) |
| 8 | cancel_subscription | **active_user** | current_user.tenant_id | ✅ | 🔴🔴 **silent-write مؤكَّد حيًا اليوم** — 200 CANCELLED، DB تفضل ACTIVE (§4) |
| 9 | get_subscription_status | active_user | current_user.tenant_id | ✅ | 🟢 غير مُختبَر حيًا بعد |
| 10 | get_services_access | active_user | current_user.tenant_id | ✅ | غير مُختبَر حيًا بعد |
| 11 | check_service_access | active_user | current_user.tenant_id | ✅ | غير مُختبَر حيًا بعد |
| 12 | get_my_invoices | **active_user** | current_user.tenant_id | ✅ | 🔴 على الأرجح محجوب بانحراف schema (§5)، لم يُختبَر اليوم بعد |
| 13 | get_invoice | active_user | current_user.tenant_id | ✅ | نفس الشيء |
| 14 | **pay_invoice** | **active_user** | current_user.tenant_id | ✅ | ⚠️ مالية + شك تصميمي (`sender_id=tenant_id`, §5) — لم يُختبَر حيًا اليوم بعد |
| 15 | list_feature_flags | superuser | current_user.tenant_id | ✅ | ✅ **مؤكَّد حيًا اليوم 5/5 (§3)** |
| 16 | toggle_feature_flag | superuser | current_user.tenant_id | ✅ | ✅ نفس الاختبار |
| 17 | get_tenant_subscriptions_admin | superuser | Path صريح | N/A (بالتصميم) | 🟡 مؤجَّل، خارج النطاق (إداري صريح) |
| 18 | get_saas_dashboard | superuser | current_user.tenant_id | N/A (تجميع عام) | غير مُختبَر |
| 19 | trigger_renewals | superuser | `0` هاردكودد + query اختياري | N/A (batch) | مؤجَّل، خارج النطاق |

**سؤال RBAC/ownership الخاص بـsaas (بطلب صريح للفحص، قياسًا على `update_my_brand` في `command`):** `subscribe_to_plan`/`cancel_subscription`/`pay_invoice`/`get_my_invoices` كلها **`active_user`** — أي موظف عادي (مش لازم دور إداري) يقدر يلغي اشتراك التينانت كله أو يدفع فاتورة من رصيد التينانت. **مفيش تناقض حماية زي `create_brand`/`update_my_brand`** (مفيش sibling إنشاء بمستوى أعلى لنفس المورد) — يبدو تصميمًا مقصودًا (self-service tenant billing) مش باج كودي، **لكنه يستاهل نفس سؤال القرار المنتجي** المفتوح في `command-rbac-ownership-review`. **لا اقتراح إصلاح بلا توجيه.**

---

## 3) تحقق حي مُنجَز اليوم — بيانات throwaway (بادئة `p_saas_idor_`)

**المستخدمون:** `p_saas_idor_a` (id=847, USER عادي, تينانت1)، `p_saas_idor_super` (id=848, SUPER_ADMIN بعد ترقية SQL, تينانت1)، `p_saas_idor_b` (id=849, SUPER_ADMIN, نُقل لتينانت16 عبر SQL). **الخدمة/الخطة:** `saas_service_catalog id=49` ("P_SAAS_IDOR_SVC")، `saas_service_plans id=50` ("P_SAAS_IDOR_PLAN") — عبر الـAPI الحقيقي.

### ✅ عزل عبر-تينانت — حاسم، 5/5
`toggle_feature_flag`(كتابة, سوبريوزر) + `list_feature_flags`(قراءة): تينانت1 (بلا هيدر/هيدر مزوَّر=16) → نفس النتيجة بالحرف، تينانت16 (بلا هيدر/هيدر مزوَّر=1) → `[]` في الحالتين. **الهيدر بلا أي تأثير، عزل حقيقي مؤكَّد بالاتجاهين.**

### 🔴 `subscribe_to_plan` — لسه محجوب بنفس البج pre-existing الموثَّق من 2026-08-13
`POST /saas/subscriptions/50` (مستخدم USER عادي، أول اشتراك) → `{"detail":"الخطة غير موجودة أو غير متاحة لك"}`. **مؤكَّد اليوم: `repository.get_plan_by_id` لسه بتدوّر على اشتراك موجود بالفعل قبل ما تجيب الخطة نفسها — تناقض منطقي يمنع أي أول اشتراك، لأي تينانت.** صفر تغيير عن التقرير المرجعي، صفر علاقة بـIDOR.

### 🔴🔴 اكتشاف جديد اليوم — `cancel_subscription` silent-write مؤكَّد DB-level (مش مجرد status code)
اشتراك throwaway `id=51` (تينانت1) زُرع عبر SQL خام (بسبب حجب #subscribe_to_plan). `PUT /saas/subscriptions/51/cancel` (مستخدم USER عادي) → **`200` مع `"status":"CANCELLED"` في الرد.** `SELECT` مستقل فوري: **`status=ACTIVE`، `auto_renew=true` — لم يتغيّر إطلاقًا.**

**السبب الجذري:** `cancel_subscription` (service.py:138) بينادي `repo.update_subscription()` اللي بقت `flush()`-only بعد إصلاح commit-a9bbae4 (`fix(transactions): eliminate commit()-inside-begin_nested()`)، **لكن `cancel_subscription` نفسها معندهاش `begin_nested()` ولا `db.commit()` صريح على الإطلاق** — الإصلاح غيّر سلوك `repo.update_subscription()` بالنسبة لكل الـcallers، وغطى بـ`db.commit()` صريح الـcallers اللي بداخل `begin_nested()` (`create_subscription`, `pay_invoice`, `process_auto_renewals` — مؤكَّد بمراجعة ديف الكوميت نفسه)، **لكن نسي `cancel_subscription` تحديدًا** (الطريقة الوحيدة من الأربعة اللي بتنادي `update_subscription` مباشرة بلا أي `begin_nested` حواليها).

**ملاحظة تناقض مع `PROGRESS_LOG.md`:** الفهرس الحالي (سطر ~147) بيوثّق بس حالتين "غير مؤكَّدتين DB-level" (`process_auto_renewals` فرع except، `can_access_service`) من أصل 5 حالات كانت مكتشفة في `simpletenant-fix-session-log.md`، وبيسيب `cancel_subscription`/`review_kyb`/`update_entity` بلا ذكر صريح — رغم إن `cancel_subscription` كان **مؤكَّد DB-level بالفعل من 2026-08-14** (قسم مخصص في التقرير المرجعي). **التحقق الحي اليوم يعيد تأكيد نفس النتيجة بالحرف — البج لسه حي وموجود، بغض النظر عن حالة التوثيق في `PROGRESS_LOG.md`.** هذا خارج نطاق IDOR بالكامل (مفيش تسريب/كتابة عبر تينانت — العزل بالتينانت نفسه سليم، القضية إن الكتابة داخل نفس التينانت مش بتتحفظ) — **موثَّق هنا بأولوية عالية لأنه تأثير مباشر على العميل (يفتكر إنه ألغى الاشتراك ولسه بيتحاسب) واكتُشف بالصدفة أثناء تحضير بيانات اختبار IDOR.**

---

## 4) استكمال التحقق الحي — مُنجَز بالكامل

### `get_my_subscriptions` (500) — السبب الجذري مؤكَّد من اللوج
**ليس بجًا في كود هذه الجلسة، وليس IDOR.** الخطأ (`pydantic_core.ValidationError: 4 validation errors for TenantSubscriptionResponse`) سببه **بيانات throwaway متبقية من جلسة تانية تمامًا** (`require-sector-removal-subscription-fix`، بادئة `TEST_REQSECTOR_*`) — تحديدًا `saas_tenant_subscriptions.id=50` (تينانت1، `payment_method=NULL`) وخطتها `saas_service_plans.id=48` (`max_users`/`max_products`/`max_courses` كلهم `NULL`). هذه الأعمدة عندها `default=` على مستوى Python/SQLAlchemy بس (مش `server_default`/`NOT NULL` على مستوى الـDB) — أي صف اتزرع عبر SQL خام بلا القيم دي صراحة (زي هذه الحالة) هيفشل عند أي قراءة عبر `TenantSubscriptionResponse` (اللي بتتطلبهم non-optional). **نفس فئة "NULL defaults" الموثَّقة مرارًا في جلسات سابقة (Phase 16 وغيرها) — pre-existing، صفر علاقة بتعديلات هذه الجلسة، لم تُنظَّف (بيانات مش بتاعتنا، مش من هذه الجلسة، خارج نطاق التنظيف).**

### `get_my_invoices`/`get_invoice`/`pay_invoice` — مؤكَّد حيًا اليوم: الثلاثة محجوبين 100% بانحراف الـschema
اختبار حي فعلي (مستخدم throwaway جديد `p_saas_inv_check`, id=850, تينانت1) على الثلاثة → **`Internal Server Error` للثلاثة بالحرف.** اللوج يؤكد نفس السبب بالضبط للثلاثة: `asyncpg.exceptions.UndefinedColumnError: column saas_invoices.idempotency_key does not exist` — الموديل (`models.py:138`) بيعرّف العمود، **الجدول الفعلي في قاعدة `eppne_v2` معندوش العمود ده إطلاقًا** (مؤكَّد بـ`\d saas_invoices` مباشر + بالتحقق الحي HTTP اليوم). **صفر تغيير عن حالة 2026-08-13 — الانحراف لسه قائم بالضبط، لم يُصلَح ولن يُصلَح في هذه الجلسة.**

### `pay_invoice`/`process_auto_renewals` — خطر `sender_id=tenant_id` لسه غير قابل للتحقق الحي (محجوب بنفس انحراف الـschema)
`get_invoice()` (أول سطر في `pay_invoice`) بيكراش فورًا بنفس خطأ `idempotency_key` **قبل ما يوصل لـ`finance.transfer()` أصلًا** — فمفيش طريقة لتحقيق حي فعلي للخطر ده حاليًا (تمامًا زي ما كان موثَّق في 2026-08-13). **يفضل موثَّق كخطر تصميمي مؤكَّد بالقراءة فقط (`finance/service.py:34-39,93-98` — `get_or_create_wallet_for_update(user_id, tenant_id)` بتفسّر `sender_id` كـ`user_id` حرفيًا، و`pay_invoice`/`process_auto_renewals` بيمرروا `tenant_id` في مكانه) — غير قابل للتأكيد الحي إلا بعد حل انحراف الـschema أولًا، وده قرار منفصل تمامًا.**

### تنظيف + إيقاف — مكتمل ومؤكَّد
- بيانات throwaway الخاصة بهذه الجلسة (مستخدمون 847/848/849/850، خدمة 49، خطة 50، اشتراك 51، فلاج feature تابع للخدمة 49) — **اتنضّفت بالكامل، 5 استعلامات `SELECT COUNT` مستقلة منفصلة كلها = صفر.**
- السيرفر التجريبي (uvicorn) **اتوقف** (`Stop-Process`)، **تأكيد إضافي منفصل:** `Get-NetTCPConnection -LocalPort 8000 -State Listen` → صفر نتيجة (لا يوجد أي عملية بتستمع على المنفذ، فقط بقايا `TIME_WAIT` من الاتصالات القديمة، غير فعّالة).

---

## 5) الخلاصة النهائية

### الجدول النهائي — 19/19 endpoint

| # | الدالة | المستوى | مصدر tenant_id | التصنيف النهائي |
|---|---|---|---|---|
| 1 | list_services | superuser | current_user.tenant_id | 🟢 آمن |
| 2 | create_service | superuser | current_user.tenant_id | 🟢 آمن |
| 3 | get_service | active_user | current_user.tenant_id | 🟢 آمن |
| 4 | list_service_plans | active_user | current_user.tenant_id | 🟢 آمن |
| 5 | create_plan | superuser | current_user.tenant_id | 🟢 آمن |
| 6 | get_my_subscriptions | active_user | current_user.tenant_id | 🟡 500 — بيانات NULL من جلسة تانية (`TEST_REQSECTOR_*`)، pre-existing، صفر علاقة بالتينانت |
| 7 | subscribe_to_plan | active_user | current_user.tenant_id | 🔴 محجوب ببج منطقي pre-existing (`get_plan_by_id`) — مؤكَّد حيًا اليوم |
| 8 | cancel_subscription | active_user | current_user.tenant_id | 🔴🔴 **silent-write مؤكَّد DB-level اليوم — 200 CANCELLED، DB تفضل ACTIVE** |
| 9 | get_subscription_status | active_user | current_user.tenant_id | 🟢 آمن (عزل تينانت سليم بنائيًا، غير مُختبَر حيًا مباشرة) |
| 10 | get_services_access | active_user | current_user.tenant_id | 🟢 آمن (نفس الشيء) |
| 11 | check_service_access | active_user | current_user.tenant_id | 🟢 آمن (نفس الشيء) |
| 12 | get_my_invoices | active_user | current_user.tenant_id | 🔴 محجوب بانحراف schema — مؤكَّد حيًا اليوم (500، `idempotency_key` مفقود) |
| 13 | get_invoice | active_user | current_user.tenant_id | 🔴 نفس الحجب — مؤكَّد حيًا اليوم |
| 14 | pay_invoice | active_user | current_user.tenant_id | 🔴 نفس الحجب + ⚠️ خطر تصميمي غير مؤكَّد حيًا (`sender_id=tenant_id`) |
| 15 | list_feature_flags | superuser | current_user.tenant_id | ✅ **مؤكَّد حيًا 5/5 — عزل حقيقي، الهيدر بلا تأثير** |
| 16 | toggle_feature_flag | superuser | current_user.tenant_id | ✅ **مؤكَّد حيًا (نفس الاختبار)** |
| 17 | get_tenant_subscriptions_admin | superuser | Path صريح | 🟡 مؤجَّل بالتصميم (إداري عبر-تينانت مقصود) |
| 18 | get_saas_dashboard | superuser | current_user.tenant_id | 🟢 غير مُختبَر حيًا (تجميع عام) |
| 19 | trigger_renewals | superuser | `0` هاردكودد + query اختياري | 🟡 مؤجَّل (batch نظامي) |

### هل saas محتاجة إصلاح IDOR فعلي (مصدر tenant_id)؟

**لا — تمامًا زي `command`.** كل الـ17 endpoint المعنيين بالفعل `cast(int, current_user.tenant_id)` من جلسة `simpletenant-fix` (2026-08-13)، والتحقق الحي اليوم (feature-flags، 5/5، هيدر مزوَّر في الاتجاهين) يؤكد عزل تينانت سليم بنائيًا. **صفر عمل IDOR كلاسيكي مطلوب هنا.** المكتشفات الحقيقية اليوم كلها فئات تانية: silent-write (`cancel_subscription`)، بجات منطقية pre-existing (`subscribe_to_plan`)، انحراف schema (invoices)، وخطر تصميمي مالي (`pay_invoice` sender_id).

---

## 6) بانتظار قرارك — 3 نصوص مقترَحة قبل الكتابة الفعلية في `PROGRESS_LOG.md`

**صفر تنفيذ كود. صفر كتابة في `PROGRESS_LOG.md` بعد.** التحقق الحي (قراءة + كتابة + تزوير هيدر + فحص انحراف schema) **مكتمل بالكامل**، البيانات مُنظَّفة، السيرفر متوقف ومؤكَّد.

**س1 — بند عاجل منفصل (مش backlog عادي) لـ`cancel_subscription`:**
> 🔴🔴 **`saas.cancel_subscription` — silent-write مؤكَّد، معروف من 2026-08-14 ولسه مش متصلح** [2026-08-24 إعادة تأكيد]. الـAPI بيرجع `200 {"status":"CANCELLED"}`، لكن `SELECT` مستقل فوري بيظهر `status=ACTIVE, auto_renew=true` — الكتابة متعملتلهاش `commit()` أبدًا. السبب: إصلاح `a9bbae4` (commit()-inside-begin_nested) حوّل `repo.update_subscription` لـ`flush()`-only وغطى الـcallers اللي جوه `begin_nested()` بـ`commit()` صريح، لكن `cancel_subscription` معندهاش `begin_nested()` من الأساس — فضلت بلا أي commit. **الأثر: أي عميل يفتكر إنه ألغى الاشتراك ولسه بيتحاسب فعليًا.** أولوية قصوى — تأثير مباشر على العميل.

موافق على النص ده كما هو؟

**س2 — بند backlog جديد بأولوية عالية جدًا لخطر `pay_invoice`:**
> 🔴 **`saas.pay_invoice`/`process_auto_renewals` — خطر تصادم `sender_id`/`user_id`** — بينادوا `finance.transfer(sender_id=self.tenant_id, ...)`، و`finance.get_or_create_wallet_for_update` بتفسّر `sender_id` كـ`user_id` حرفيًا. لو تصادف `id` مستخدم حقيقي = رقم التينانت، الدفع هيمس محفظة ذلك المستخدم العشوائي مش محفظة تينانت مخصَّصة. غير قابل للتحقق الحي حاليًا (محجوب بانحراف schema `idempotency_key`) — يحتاج حل الانحراف أولًا ثم مراجعة معمارية منفصلة.

موافق على النص ده كما هو؟

**س3 — توسيع `command-rbac-ownership-review` (نفس البند، مش بند جديد):**
> إضافة: `saas.subscribe_to_plan`/`cancel_subscription`/`pay_invoice`/`get_my_invoices` كلها `active_user` — أي موظف عادي (بلا دور إداري) يقدر يلغي اشتراك التينانت كله أو يحاول الدفع من رصيده. لا يوجد تناقض حماية زي `update_my_brand` (مفيش sibling بمستوى أعلى لنفس المورد)، يبدو تصميم self-service مقصود — لكن يستاهل نفس القرار المنتجي.

موافق على النص ده كما هو؟

**س4 — بجات pre-existing إضافية اتكشفت اليوم (`subscribe_to_plan` المنطقي، `get_my_subscriptions` NULL-defaults، انحراف schema invoices):**
> Backlog فقط، نفس نمط الجلسات السابقة، ولا تفتح بند منفصل جديد؟

**أي توجيه إضافي:**
>

---

## 7) ردّك هنا

اكتب إجابتك في الأسطر تحت كل سؤال (رقم بس كفاية زي "س1 موافق"، أو جملة قصيرة لو حابب تعدّل النص):

**س1 (`cancel_subscription` عاجل):**
>

**س2 (`pay_invoice` backlog عالي جدًا):**
>

**س3 (توسيع `command-rbac-ownership-review`):**
>

**س4 (بجات pre-existing إضافية):**
>

**أي توجيه إضافي:**
>
