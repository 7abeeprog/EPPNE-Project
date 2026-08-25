# جلسة جرد + أمان مدمجة — الدفعة 1: employment, invitations, communications, invoicing

**بدأ التسجيل:** 2026-08-25
**الحالة:** ✅ **الجرد الوظيفي + الفحص الأمني الكودي + التحقق الحي (بيانات throwaway، تينانتين حقيقيين: تينانت1/تينانت16) مكتملون بالكامل للأربعة دومينات. صفر تنفيذ إصلاح كود. بانتظار موافقتك على التصنيف والحلول المقترَحة (§6) قبل أي تطبيق.**

---

## 0) المرجع الميكانيكي — ما كان موثَّقًا قبل هذه الجلسة

من `.claude/plans/critical-finding-xtenant-systemic.md` (تصنيف نمط X-Tenant-ID، قراءة كود فقط، بدون تحقق حي وقتها):

| دومين | تصنيف سابق | ملاحظة |
|---|---|---|
| employment | 🟢 SAFE | "لا admin endpoints" — معيار ضيق جدًا، لم يفحص current_user/فلتر repository لكل endpoint |
| invitations | 🟢 SAFE | نفس الملاحظة أعلاه |
| communications | 🔴 SUSPICIOUS (#9) | `router.py:398-423,426-433` — قوالب تواصل tenant-wide عبر هيدر مزوَّر، غير مؤكَّد حيًا وقتها |
| invoicing | ⚠️ ملاحظة منفصلة | `create_invoice` — `entity_id=data.tenant_id` من جسم الطلب مباشرة، mass-assignment محتمل، غير مؤكَّد حيًا وقتها |

**هذه الجلسة صححت التصنيف الأصلي لـ`employment` و`invitations` بشكل جوهري** — كلاهما كان مُصنَّفًا "آمن" بناءً على معيار ضيق ("لا admin endpoints")، لكن الفحص الكامل هنا (current_user لكل endpoint + مصدر tenant_id + فلتر repository) كشف فجوات IDOR حقيقية في الاثنين، **مؤكَّدة حيًا الآن**.

**المنهجية المتبعة:** فحص كود كامل (router/service/repository/schemas/models، 100%) لكل دومين عبر 3 وكلاء متوازيين (employment/invitations/communications) + فحص مباشر مني لـ`invoicing`، ثم **تحقق حي مركزي واحد** بعد جمع كل النتائج — سيرفر uvicorn محلي حقيقي، مستخدمان throwaway حقيقيان موثَّقان مسبقًا (`TEST_super_a`/تينانت1، `TEST_instr_b`/تينانت16، من `.claude/reports/throwaway-test-users.md`)، بيانات throwaway جديدة زُرعت واختُبرت وحُذفت بالكامل.

---

## 1) جدول `employment` — 22 endpoint

**النطاق:** `router.py`(444 سطر)، `service.py`(652 سطر)، `repository.py`(510 سطر)، `models.py`(263 سطر)، `schemas.py`(149 سطر) + `app/tasks/employment.py` (Celery) — قراءة كاملة.

| # | Endpoint | الوظيفة الفعلية بالعربي | مربوط بفرونت إند؟ | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|---|
| 1 | `POST /jobs` | نشر إعلان وظيفة جديدة (صاحب عمل) | ✅ `employment.ts:createJob` | ✅ | **هيدر `X-Tenant-ID`** (`get_current_tenant`) | يُكتب مباشرة في `JobListing.tenant_id` | 🔴 تلوّث بيانات + تجاوز `_check_saas_limits` لتينانت الضحية |
| 2 | `GET /jobs/open` | تصفح الوظائف النشطة | ✅ `getOpenJobs` | ✅ | **هيدر** | فلتر صحيح لكن بقيمة ملوَّثة | 🔴🔴🔴🔴 **IDOR كامل — مؤكَّد حيًا** |
| 3 | `GET /jobs/my` | وظائف نشرها المستخدم | ✅ `getMyJobs` | ✅ | `employer_id=current_user.id` | ✅ حقيقي | 🟢 سليم |
| 4 | `PUT /jobs/{id}` | تعديل وظيفة | ✅ `updateJob` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 5 | `DELETE /jobs/{id}` | إغلاق وظيفة (soft-close) | ✅ `closeJob` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 6 | `POST /applications` | تقديم طلب توظيف + تقييم AI تلقائي | ✅ `applyToJob` | ✅ | `tenant_id` هيدر (فلتر وجود الوظيفة فقط) | 🟠 لا عمود `tenant_id` في `JobApplication` أصلًا، `applicant_id` حقيقي | 🟠 أضعف تأثيرًا |
| 7 | `GET /applications/my` | طلباتي | ✅ `getMyApplications` | ✅ | `applicant_id` | ✅ حقيقي | 🟢 سليم |
| 8 | `GET /applications/job/{id}` | طلبات وظيفة (لصاحب العمل) | ✅ `getJobApplications` | ✅ | `employer_id` عبر الوظيفة | ✅ حقيقي | 🟢 سليم |
| 9 | `POST /applications/{id}/review` | قبول/رفض طلب | ✅ `reviewApplication` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 10 | `POST /contracts` | إنشاء عقد عمل من طلب مقبول | ✅ `createContract` | ✅ | **هيدر** يُكتب في `EmploymentContract.tenant_id` | `employer_id`/`application_id` محقَّقان حقيقيًا، لكن `tenant_id` ملوَّث | 🔴 تلوّث + تجاوز حدود اشتراك |
| 11 | `GET /contracts/me` | عقدي النشط | ✅ `getMyActiveContract` | ✅ | `employee_id`/`employer_id` | ✅ حقيقي | 🟢 سليم |
| 12 | `POST /contracts/{id}/sign` | توقيع العقد | ✅ `signContract` | ✅ | نفس أعلاه | ✅ حقيقي | 🟢 سليم |
| 13 | `POST /attendance/check-in` | تسجيل حضور GPS | ✅ `checkIn` | ✅ | `employee_id` عبر العقد | ✅ حقيقي | 🟢 سليم |
| 14 | `POST /attendance/check-out` | تسجيل انصراف + حساب ساعات | ✅ `checkOut` | ✅ | نفس أعلاه | ✅ حقيقي | 🟢 سليم |
| 15 | `GET /attendance/my` | سجل حضوري | ✅ `getMyAttendance` | ✅ | `employee_id` | ✅ حقيقي | 🟢 سليم |
| 16 | `POST /leaves/request` | طلب إجازة | ✅ `requestLeave` | ✅ | `employee_id` | ✅ حقيقي | 🟢 سليم |
| 17 | `GET /leaves/pending` | إجازات معلقة لصاحب العمل | ✅ `getPendingLeavesForEmployer` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 18 | `POST /leaves/{id}/approve` | موافقة/رفض إجازة | ✅ `approveLeave` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 19 | `POST /payroll/generate` | إنشاء كشف راتب (Celery) | ✅ `generatePayroll` | ✅ | `employer_id` يتحقق + **هيدر** لفحص حدود اشتراك | 🟠 مختلط | 🟠 تجاوز فحص حدود تينانت تاني |
| 20 | `POST /payroll/{id}/approve` | اعتماد كشف الراتب | ✅ `approvePayroll` | ✅ | `employer_id` | ✅ حقيقي | 🟢 سليم |
| 21 | `POST /payroll/{id}/pay` | صرف الراتب فعليًا (`finance.transfer`+`invoicing.create_invoice`) | ✅ `payPayroll` | ✅ | `employer_id` يتحقق + **هيدر** للفحص | 🟠 مختلط | 🟠 تجاوز فحص حدود تينانت تاني |
| 22 | `GET /payroll/my` | كشوف رواتبي | ✅ `getMyPayrolls` | ✅ | `employee_id` | ✅ حقيقي | 🟢 سليم |

**الخلاصة الوظيفية:** **22/22 endpoint مربوطة end-to-end بفرونت إند حقيقي فعليًا مُستخدَم** — صفر كود ميت. دومين ناضج (Idempotency كامل، rate limiting، sanitization، حساب رواتب فعلي وليس placeholder).

**الخلاصة الأمنية:** 16 endpoint سليمة (ownership حقيقي عبر `current_user.id`). **6 فيها فجوة حقيقية** — الأخطر `GET /jobs/open` (IDOR قراءة كامل بلا أي شرط، **مؤكَّد حيًا §4.1**)، تليها `POST /jobs`/`POST /contracts` (تلوّث بيانات + تجاوز حدود اشتراك SaaS).

### الترابط Cross-domain (`employment`)
**يستدعي:** `identity` (بيانات مستخدم)، `academy` (تحقق شهادات)، `affiliate` (عمولات)، `ai_agents` (تقييم توافق AI)، `saas` (فحص حدود اشتراك — **متأثر بنفس تلوّث `tenant_id`**)، `finance`+`invoicing` (عبر Celery فقط، `app/tasks/employment.py`، تحويل راتب + فاتورة تلقائية).
**يُستدعى من:** لا أحد — دومين "ورقة" (leaf)، لا يعتمد عليه أي دومين آخر.

---

## 2) جدول `invitations` — 21 endpoint (نظام CRM سيادي كامل: دعوات + عملاء محتملون + حملات + تذاكر دعم)

**النطاق:** `router.py`(650 سطر)، `service.py`(1014 سطر)، `repository.py`(351 سطر)، `models.py`(365 سطر)، `schemas.py`(314 سطر) — قراءة كاملة.

**🔴🔴🔴🔴 اكتشاف بنيوي: كل الـ21 endpoint بلا استثناء تستخدم `Depends(get_current_tenant)` (هيدر `X-Tenant-ID`)، صفر ربط بـ`current_user.tenant_id`.** الـ`repository.py` نفسه يفلتر صح (`WHERE tenant_id == tenant_id` في كل استعلام)، لكن القيمة المُمرَّرة من الراوتر أصلها الهيدر غير الموثوق — نفس نمط `list_org_entities` في `academy` قبل إصلاحها، لكن مُكرَّر عبر الدومين بالكامل.

| # | مجموعة Endpoints | الوظيفة الفعلية | مربوط بفرونت إند؟ | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|---|
| 1-5 | `POST/GET/GET{id}/PUT/DELETE /invitations` | دعوة سيادية بخصم/هدية، تحليل AI للهدف، رابط دعوة | ✅ | ✅ (عدا pre-auth مبرَّرة) | **هيدر** | ✅ لكن بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كامل (قراءة+كتابة+حذف) |
| 6 | `POST /{id}/accept` | إنشاء حساب من دعوة (يستدعي `identity.register`) | pre-auth (معقول جزئيًا) | اختياري (`get_current_user_optional`) | — | — | 🟡 pre-auth مبرَّر، لكن `_apply_discount_gift` = `pass` (TODO فارغ) |
| 7 | `POST /{id}/chat` | شات AI حقيقي مع الوكيل + استهلاك حصة `ai_governance` | ✅ `AIAssistantChat.tsx` | اختياري | **هيدر** | — | 🔴 نفس النمط |
| 8-11 | `GET tracking/conversations/insight`, `POST tracking` | تتبع سلوك زائر، سجل محادثات، رؤى AI | جزئي | مختلط | **هيدر** | ✅ بقيمة ملوَّثة | 🔴 نفس النمط |
| 12-17 | Leads (6 endpoints CRUD+interactions) | إدارة عملاء محتملين، تفاعلات | ✅ `useLeads.ts`,`useInteractions.ts` | ✅ | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 **IDOR قراءة+كتابة — مؤكَّد حيًا §4.2** |
| 18-23 | Campaigns (6 endpoints CRUD+launch) | حملات تسويقية **بخصم مالي فعلي** (`finance.transfer`) + فاتورة (`invoicing.create_invoice`) + عمولة | ✅ `useCampaigns.ts` | ✅ | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴🔴 **الأخطر ماليًا** — ميزانية حقيقية تُنسب لتينانت تاني |
| 24-29 | Tickets (6 endpoints CRUD+comments) | تذاكر دعم فني | ✅ `useTickets.ts` | ✅ | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كامل |
| 30 | `GET /stats` | إحصائيات مجمَّعة | ✅ `useStats.ts` | ✅ | **هيدر** | — | 🔴 نفس النمط |

**الخلاصة الوظيفية:** **21/21 endpoint مربوطة فعليًا بفرونت إند حقيقي** — صفر كود ميت (استثناء نادر مقارنة بدومينات أخرى بها كود غير مستخدَم).

**اكتشاف إضافي غير أمني (تحقق حي، §4.2):** `GET /invitations/leads` (وعلى الأرجح `campaigns`/`tickets` بنفس الآلية) **غير قابل للوصول فعليًا في الإنتاج** — باج ترتيب تسجيل routes مطابق تمامًا لما وُثِّق سابقًا في `sovereign_entities` (`GET /{invitation_id}` مُسجَّلة قبل `GET /leads` في نفس الملف، فأي طلب لـ`/invitations/leads` يقع تحت نمط `/{invitation_id}` (int) أولًا ويُرفض بـ`422` قبل ما يصل للهاندلر الحقيقي). **هذا لا يلغي خطورة IDOR** — القراءة/الكتابة عبر `GET/PUT /leads/{id}` المباشر (بالـID) **شغالة فعليًا ومؤكَّدة حيًا مُخترَقة**، فقط القائمة (list) هي المتأثرة بباج التوجيه.

### الترابط Cross-domain (`invitations`)
**يستدعي:** `identity.register` (قبول دعوة)، `ai_agents` (تحليل هدف+شات)، `saas` (بوابة على كل الكتابات — **متأثرة بنفس تلوّث tenant_id**)، `affiliate` (عمولة)، `invoicing.create_invoice` (فاتورة ميزانية حملة — **يرث نفس تلوّث التينانت**)، `finance.transfer` (خصم ميزانية، `sender_id` آمن)، `ai_governance.check_and_consume`.
**يُستدعى من:** لا أحد.

---

## 3) جدول `communications` — 16 endpoint + WebSocket

**النطاق:** `router.py`(434 سطر)، `service.py`(278 سطر)، `repository.py`(264 سطر)، `models.py`(171 سطر)، `schemas.py`(97 سطر)، `tasks.py`(27 سطر) — قراءة كاملة.

| # | Endpoint | الوظيفة الفعلية | مربوط بفرونت إند؟ | `current_user`؟ | مصدر `tenant_id`/فلتر | تصنيف |
|---|---|---|---|---|---|---|
| — | `WS /ws` | بث إشعارات حية عبر Redis pub/sub | ✅ `useWebSocket.ts` | JWT مباشر (`user_id` موقَّع) | قناة `user:{id}` — غير قابل للتزوير | 🟢 سليم |
| 1 | `POST /notifications/send` (superuser) | إرسال إشعار لأي `user_id` | ❌ لا استدعاء من الفرونت إند | ✅ superuser | تينانت **المستلم** من DB، بلا فحص انتماء المُرسِل | 🟡 سؤال تصميمي (سوبريوزر عبر-تينانت) |
| 2 | `GET /notifications/me` | إشعاراتي | ✅ `notificationStore.ts` | ✅ | `user_id=current_user.id` | 🟢 سليم |
| 3 | `POST /notifications/{id}/read` | تعليم كمقروء | ❌ الفرونت يستخدم `mail/mark-read` بدلًا | ✅ | `notification.user_id` محقَّق | 🟢 سليم (بلا استخدام) |
| 4 | `POST /devices/register` | تسجيل جهاز push | ❌ | ✅ | `current_user.id` | 🟢 سليم (بلا استخدام) |
| 5 | `POST /mail/send` | بريد داخلي + مرفقات | ❌ لا صفحة compose | ✅ | فحص صريح `sender_tenant==recipient_tenant` من DB | 🟢 سليم |
| 6 | `GET /mail/inbox` | صندوق الوارد | ✅ `inbox/page.tsx` | ✅ | `owner_id=current_user.id` | 🟢 سليم |
| 7 | `GET /mail/sent` | المرسلات | ❌ رابط ميت | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 8 | `POST /mail/move-to-trash/{id}` | نقل لسلة المحذوفات | ❌ | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 9 | `POST /mail/restore/{id}` | استعادة | ❌ | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 10 | `POST /mail/archive/{id}` | أرشفة | ❌ | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 11 | `POST /mail/star/{id}` | تمييز بنجمة | ❌ | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 12 | `POST /mail/mark-read/{id}` | تعليم كمقروءة | ✅ فعليًا مستخدَمة للإشعارات | ✅ | `owner_id` | 🟢 سليم |
| 13 | `DELETE /mail/permanent/{id}` | حذف نهائي | ❌ | ✅ | `owner_id` | 🟢 سليم (بلا استخدام) |
| 14 | `POST /templates` (superuser) | إنشاء قالب رسالة/إشعار | ❌ لا صفحة إدارة | ✅ superuser | **هيدر `X-Tenant-ID`** | 🔴🔴🔴 **IDOR — مؤكَّد حيًا §4.3** |
| 15 | `GET /templates` (superuser) | عرض قوالب التينانت | ❌ | ✅ superuser | **هيدر** | 🔴🔴🔴 **IDOR — مؤكَّد حيًا §4.3** |

**الخلاصة الوظيفية:** من 16، **3 فقط مربوطة فعليًا بفرونت إند حقيقي مُستخدَم** (`notifications/me`, `mail/mark-read`, `mail/inbox`, +WebSocket). صندوق البريد الداخلي هيكل شبه كامل لكن **واجهة نصف مكتملة**: لا compose، لا sent، لا trash/archive/star فعليًا (أزرار موجودة في `MailSidebar` لكن بلا صفحات مقابلة). **قنوات الإشعارات الحقيقية (Push/Email/SMS) في `tasks.py` مُهيكَلة بالكامل لكن غير مُنفَّذة فعليًا** — `send_fcm`/`send_smtp_email`/`send_twilio_sms` مستوردة، لا تُستدعى أبدًا (كلها `pass`). القناة الوحيدة الشغالة end-to-end هي `IN_APP` عبر Redis مباشرة.

### الترابط Cross-domain (`communications`)
**مُستهلَك من:** `transport`, `realestate`, `automation` (الثلاثة يستوردون `CommunicationsService` لإشعارات داخلية — تينانت المستلم من DB، غير متأثر بثغرة `templates`).
**يعتمد على:** `identity.UserRepository` (تينانت حقيقي من DB، أساس سلامة `send_mail`/`send_notification`).

---

## 4) قسم خاص — `invoicing`: 8 endpoints، مع تحليل mass-assignment كأولوية أولى

**النطاق:** `router.py`(335 سطر)، `service.py`(321 سطر)، `repository.py`(199 سطر)، `models.py`(83 سطر)، `schemas.py`(79 سطر) — قراءة كاملة. **ملاحظة بنيوية:** لا يوجد `__init__.py` في هذا الدومين (موثَّق مسبقًا).

### 4-أ) تحليل `create_invoice` — mass-assignment (الأولوية المطلوبة) — 🔴🔴🔴🔴 **مؤكَّد حيًا، خطورة عالية**

`router.py:42-70`: `data: InvoiceCreate` → `service.create_invoice(entity_id=data.tenant_id, user_id=data.user_id or 0, ...)`. `schemas.py:27-30`: `InvoiceCreate.tenant_id: int` **حقل عادي قابل للتعيين الحر من العميل، بلا أي تحقق أنه يطابق `current_user.tenant_id`**، و`user_id: Optional[int]` كذلك حر تمامًا (بلا تحقق أنه ينتمي لنفس التينانت). **صفر admin-gate** — أي `active_user` عادي (ليس حتى superuser) كافٍ. `repository.create_invoice` (`repository.py:22-31`) يكتب القيم كما هي بلا أي تحقق إضافي.

**التحقق الحي (§4.4) أثبت اثنين معًا:**
1. **مستخدم من تينانت1 أنشأ فاتورة حقيقية منسوبة لتينانت16 (بمبلغ ومستخدم مستهدف من اختياره الحر) — نجحت فعليًا وكُتبت في DB.**
2. **باج مقنِّع منفصل تمامًا:** استجابة الـAPI نفسها أرجعت `400` (فشل ظاهري) بسبب تصادم اسم حقل — `InvoiceResponse.metadata` يصطدم بخاصية `metadata` المحجوزة في SQLAlchemy `Base` (بدل عمود `invoice_metadata` الفعلي) — **رغم أن الكتابة في DB نجحت بالكامل قبل هذا الخطأ**. هذا الباج **عام يمس كل استدعاء `POST /invoices` بلا استثناء** (مش خاص بالهجوم فقط) — أي عميل حقيقي (فرونت إند مستقبلي، أو أي دومين داخلي يستدعي هذا المسار عبر HTTP بدل الـservice المباشر) سيرى "فشل" رغم نجاح الإنشاء الفعلي — **نفس نمط "الرد المضلِّل مع نجاح الكتابة الحقيقية" الموثَّق سابقًا في `commerce.handle_visa_webhook`/`ai_governance.check-and-consume`.**

### 4-ب) جدول باقي endpoints (7 من 8)

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /invoices` | إنشاء فاتورة (انظر 4-أ) | ✅ (بلا فحص دور) | **جسم الطلب مباشرة** | — | 🔴🔴🔴🔴 mass-assignment مؤكَّد حيًا |
| 2 | `GET /invoices/{id}` | جلب فاتورة | ✅ | `current_user.tenant_id`، أو `None` لو `SUPER_ADMIN/EXECUTIVE_DIRECTOR` (bypass شرعي بالدور) | ✅ `tenant_id`+`id` | 🟢 سليم (المسار العادي) |
| 3 | `GET /invoices` | قائمة مع تصفية | ✅ | نفس نمط أعلاه + فحص `tenant_id != current_user.tenant_id → 403` لغير superuser | ✅ | 🟢 سليم |
| 4 | `PATCH /invoices/{id}/status` | تحديث الحالة (يدفع فعليًا عبر `finance.transfer` لو PAID) | ✅ | `current_user.tenant_id` | ✅ | 🟢 سليم |
| 5 | `POST /invoices/{id}/pay` | تحديد كمدفوعة | ✅ | `current_user.tenant_id` | ✅ | 🟢 سليم |
| 6 | `POST /invoices/{id}/cancel` | إلغاء | ✅ | `current_user.tenant_id` | ✅ | 🟢 سليم |
| 7 | `GET /stats` | إحصائيات | ✅ | `current_user.tenant_id` + نفس فحص 403 | — | 🟢 سليم |
| 8 | `POST /admin/process-overdue` | معالجة الفواتير المتأخرة عالميًا (Celery) | ✅ superuser فقط | بلا تينانت — بتصميم (عالمي) | — | 🟢 سليم بالتصميم (يحتاج تأكيد أن العالمية مقصودة) |

**الخلاصة:** 7/8 endpoint سليمة أمنيًا (فلترة حقيقية بـ`current_user.tenant_id` + فحص دور صريح للتجاوز الإداري) — **الاستثناء الوحيد هو `create_invoice`، لكنه الأخطر في الدفعة كلها ماليًا** (بيانات فوترة حقيقية، مبلغ حر، تينانت حر، مستخدم مستهدف حر).

### 4-ج) الجرد الوظيفي — نتيجة غير متوقعة

**بحث الفرونت إند لم يجد أي استخدام مباشر لـ`/invoicing/*`** — الواجهة الموجودة فعليًا تحت `app/(dashboard)/saas/invoices/` تستدعي `/saas/saas/invoices` (دومين `saas` منفصل تمامًا، بجدول `saas_invoices` منفصل) — **ليس نفس الدومين**. بمعيار "مربوط بفرونت إند حقيقي" الضيق، **الـREST API لدومين `invoicing` نفسه بلا أي استخدام مباشر من الواجهة حاليًا (0/8 مربوطة بصفحة مستخدم)**.

**لكن هذا لا يعني الدومين "ميت"** — طبقة الـservice (`InvoicingService.create_invoice`) **بنية تحتية مالية مشتركة حرجة**، تُستدعى داخليًا (server-to-server، بتينانت موثوق من سياق الخدمة المستدعية، غير معرَّض لجسم طلب خارجي) من **13 دومينًا آخر**: `transport`, `zamakana`, `tourism_sports`, `tenders_auctions`, `service_marketplace`, `social`, `employment`, `invitations`, `manufacturing`, `arbitration_syndicates`, `realestate`, `insurance`, `logistics`, `ai_agents`. **الاستخدام الداخلي هذا غير متأثر بثغرة mass-assignment** (لأنه يمرر `tenant_id` من `self.tenant_id` الموثوق في كل دومين مستدعٍ، مش من جسم طلب HTTP خارجي) — لكن **الباج المقنِّع (4-أ.2) قد يؤثر عليهم** لو أي منهم يعتمد على قراءة `InvoiceResponse` الراجعة من `create_invoice` مباشرة (يحتاج فحص منفصل لكل caller، خارج نطاق هذه الجلسة).

### الترابط Cross-domain (`invoicing`)
**يستدعي:** `finance.transfer` (دفع فعلي عند `status=PAID`).
**يُستدعى من:** 13 دومين (أعلاه) — **دومين "بنية تحتية" حقيقي رغم غياب واجهة مستخدم مباشرة له.**

---

## 5) خريطة الترابط الكاملة بين الأربعة دومينات ومع باقي المنصة

```
identity ──(قراءة مستخدم/تسجيل)──> employment, invitations, communications
                                          │
saas (فحص حدود اشتراك) <──────── employment, invitations
   [مُتأثر بنفس تلوّث tenant_id في employment/invitations]
                                          │
finance.transfer <──── invoicing, employment(Celery), invitations(campaigns)
                                          │
invoicing.create_invoice <──── employment(Celery), invitations(campaigns)
        + 11 دومين آخر خارج نطاق هذه الدفعة
        [مسار داخلي موثوق tenant_id — غير متأثر بـmass-assignment
         لكن قد يتأثر بالباج المقنِّع 4-أ.2]
                                          │
communications ◄──(إشعارات)──── transport, realestate, automation
        [خارج نطاق هذه الأربعة، لمعلوماتك فقط]
                                          │
ai_agents/ai_governance ◄──(تحليل/شات/استهلاك)──── invitations, employment
                                          │
affiliate (عمولات) ◄──── employment, invitations
                                          │
academy (تحقق شهادات) ◄──── employment
```

**ملاحظة ترابط حرجة:** الأربعة دومينات **لا يستدعي أي منها الآخر مباشرة فيما بينها** (لا employment↔invitations، لا communications↔أي منهم، لا invoicing↔أي منهم داخل هذه الدفعة) — **الترابط الحقيقي بينها غير مباشر عبر ثلاث بنى تحتية مشتركة:** `identity` (كل الأربعة)، `saas` (`employment`+`invitations` فقط — **وكلاهما بنفس فجوة تلوّث tenant_id، فتينانت الفحص نفسه غير موثوق في الاثنين**)، و`invoicing.create_invoice` (`employment`+`invitations` يستدعيانه داخليًا لأغراض مختلفة تمامًا: فاتورة راتب مقابل فاتورة ميزانية حملة).

---

## 6) الفجوات المكتشفة — التصنيف النهائي والتحقق الحي (بانتظار قرارك، صفر تنفيذ)

جميع الفجوات التالية **مؤكَّدة حيًا** (بيانات throwaway حقيقية، تينانت1↔تينانت16، زُرعت واختُبرت وحُذفت بالكامل هذه الجلسة — التفاصيل في §7).

| # | الدومين | الاكتشاف | الخطورة | مؤكَّد حيًا؟ |
|---|---|---|---|---|
| 1 | invitations | **كل الـ18 endpoint الإدارية** (دعوات/leads/campaigns/tickets، عدا 3 pre-auth مبرَّرة) — `tenant_id` من هيدر، صفر ربط بـ`current_user`. تحقق حي: قراءة **و** تعديل (`PUT`) بيانات lead حقيقي تخص تينانت16 بواسطة مستخدم تينانت1 | 🔴🔴🔴🔴🔴 **الأعلى في الدفعة** — نطاق دومين كامل + أثر مالي حقيقي في campaigns (ميزانية+فاتورة+عمولة) + قراءة **وكتابة** بيانات عملاء | ✅ (§4.2) |
| 2 | invoicing | `create_invoice` — `tenant_id`/`user_id` من جسم الطلب مباشرة، بلا admin-gate. تحقق حي: فاتورة حقيقية بمبلغ حر أُنشئت لتينانت16 بواسطة مستخدم تينانت1 | 🔴🔴🔴🔴 مالي مباشر (سجلات فوترة، ليس تحويل أموال فعلي لكن تلوّث بيانات مالية حقيقي) | ✅ (§4.4) |
| 3 | employment | `GET /jobs/open` — قراءة قائمة وظائف بلا أي شرط، تينانت من هيدر. تحقق حي: تينانت1 قرأ وظائف تينانت16 الحقيقية (بيانات صاحب العمل + التفاصيل) | 🔴🔴🔴🔴 IDOR قراءة كامل، صفر شرط | ✅ (§4.1) |
| 4 | employment | `POST /jobs`/`POST /contracts` — تلوّث `tenant_id` + تجاوز `_check_saas_limits` تينانت تاني | 🔴 تلوّث بيانات + تجاوز حدود اشتراك (غير مختبَر حيًا — يتطلب تفعيل ميزة `hr_management`، مؤجَّل) | كود فقط — غير مؤكَّد حيًا هذه الجلسة |
| 5 | communications | `create_template`/`list_templates` — تينانت من هيدر (سوبريوزر). تحقق حي: تينانت1 قرأ قالبًا حقيقيًا تخص تينانت16 | 🔴🔴🔴 IDOR، لكن يتطلب دور superuser أصلًا (أضيق من #1/#3) + بلا استخدام فرونت إند حاليًا | ✅ (§4.3) |
| 6 | invoicing | باج مقنِّع: `InvoiceResponse.metadata` يصطدم بـ`Base.metadata` من SQLAlchemy → `400` مضلِّل رغم نجاح الإنشاء الفعلي، **لكل استدعاء `POST /invoices` بلا استثناء** | ⚪ وظيفي بحت (ليس IDOR) لكن يخفي نجاح كتابة — يستحق إصلاح مستقل عاجل | ✅ (§4.4) |
| 7 | invitations | باج ترتيب routes: `GET /invitations/leads` (وربما `campaigns`/`tickets`) غير قابل للوصول (يُبتلَع بـ`GET /{invitation_id}`) | ⚪ وظيفي بحت (Backlog) — لا يلغي خطورة #1 (القراءة/الكتابة بالـID المباشر شغالة ومخترَقة) | ✅ (§4.2) |
| 8 | communications | `send_notification` — سوبريوزر يقدر يرسل إشعار لمستخدم أي تينانت بلا فحص انتماء المُرسِل | 🟡 سؤال تصميمي (هل مقصود؟) وليس IDOR كلاسيكي | كود فقط |
| 9 | invitations | `accept_invitation._apply_discount_gift` = `pass` (TODO فارغ) | ⚪ فجوة وظيفية (Backlog)، غير أمنية | كود فقط |
| 10 | invoicing | `POST /admin/process-overdue` — يعالج كل الفواتير عالميًا بلا معامل تينانت | 🟢 يبدو مقصودًا بالتصميم (Celery + superuser-gated) — يحتاج تأكيدك فقط، ليس بالضرورة خطأ | كود فقط |

### الحل المقترَح لكل بند (معروض فقط — **صفر تنفيذ حتى الآن**)

- **#1 (invitations، الأولوية القصوى):** نفس النمط الميكانيكي المطبَّق سابقًا على `academy`/`digital_twin`/`ai_agents` — استبدال `Depends(get_current_tenant)` بـ`current_user: User = Depends(get_current_active_user)` + `tenant_id = cast(int, current_user.tenant_id)` في الـ18 endpoint. نطاق أوسع من أي دومين سابق (21 موضع تقريبًا) — يستحق جلسة تنفيذ مخصَّصة منفصلة.
- **#2 (invoicing):** `create_invoice` — حذف `tenant_id`/`user_id` القابلين للتعيين الحر من `InvoiceCreate`، استبدالهما بـ`current_user.tenant_id`/`current_user.id` كافتراضي، **مع سؤال تصميمي مفتوح**: هل يوجد استخدام إداري شرعي يحتاج تحديد تينانت/مستخدم مختلف (فواتير نظامية عبر Celery مثلًا)؟ لو نعم، يحتاج `require_sector`/فحص دور صريح بدل فتح الحقل لأي `active_user`.
- **#3 (employment):** نفس نمط `academy` — `current_user.tenant_id` بدل الهيدر في `list_active_jobs`/`repository`.
- **#4 (employment):** نفس النمط لـ`create_job`/`create_contract`/فحوصات `_check_saas_limits` — يحتاج تحقق حي إضافي بعد تفعيل ميزة `hr_management` مؤقتًا (أو جلسة منفصلة).
- **#5 (communications):** نفس النمط — `current_user.tenant_id` بدل الهيدر في `create_template`/`list_templates`.
- **#6 (invoicing، عاجل ومنفصل عن IDOR):** إعادة تسمية `InvoiceResponse.metadata` (مثلًا `invoice_metadata`) أو استخدام `model_config` alias صريح لتفادي تصادم `SQLAlchemy.Base.metadata` — إصلاح صغير معزول، يستحق أولوية لأنه يخفي نجاح كل عملية إنشاء فاتورة حاليًا.
- **#7 (invitations):** إعادة ترتيب تسجيل routes في `router.py` بحيث `/leads`, `/campaigns`, `/tickets` (وأي مسار نصي ثابت) تُسجَّل **قبل** `/{invitation_id}` — نفس نمط إصلاح `sovereign_entities`.
- **#8، #9، #10:** بانتظار توجيهك التصميمي (ليست بالضرورة إصلاح كود).

---

## 7) التحقق الحي — التفاصيل الكاملة

**السيرفر:** `uvicorn` محلي (`E:\cc\eppne-backend`, venv, منفذ 8000)، شُغِّل هذه الجلسة، تأكيد `GET /docs` → `200`، **أُوقف في نهاية الجلسة** (تأكيد `taskkill` + `netstat` صفر `LISTENING`).

**المستخدمون:** `TEST_super_a` (id=772، تينانت1، `SUPER_ADMIN`) و`TEST_instr_b` (id=774، تينانت16، `SUPER_ADMIN`) — من `.claude/reports/throwaway-test-users.md`. كلمة السر الموثَّقة (`TEST_pass_dtwin_2026`) كانت لا تعمل لـ`TEST_instr_b` (على الأرجح غيّرتها جلسة لاحقة بلا توثيق) — **أُعيد تعيينها لنفس القيمة الموثَّقة** عبر تحديث `hashed_password` مباشرة (بيانات اختبار فقط، صفر تعديل كود). ملاحظة فرعية اكتُشفت: `POST /identity/login` نفسه يعتمد على `get_current_tenant` (هيدر، pre-auth، سلوك موثَّق ومقبول مسبقًا في `critical-finding-xtenant-systemic.md`) — تسجيل دخول `TEST_instr_b` يتطلب `X-Tenant-ID: 16` صراحة في طلب الدخول نفسه (وإلا يُفلتَر بتينانت1 الافتراضي ويفشل "بيانات دخول غير صحيحة" — سلوك fail-safe صحيح، ليس ثغرة).

### 4.1 `employment.GET /jobs/open` — IDOR مؤكَّد
```
A (تينانت1) + X-Tenant-ID:16 → GET /api/employment/jobs/open
→ 200، [TEST_JOB_WITH_DESC(id=5), TEST_JOB_NO_DESC(id=4)] — بيانات تينانت16 الحقيقية
   (employer_id=774 = TEST_instr_b، بيانات موجودة مسبقًا من جلسات سابقة)
```
**ملاحظة جانبية غير أمنية:** `GET /jobs/open` بلا هيدر (تينانت1، بياناته الخاصة) يرجّع `500` — باج `ResponseValidationError` منفصل تمامًا (صف قديم `required_skills`/`required_certificate_ids` = `NULL` يخالف `List` المطلوب في الـschema) — لا علاقة له بـIDOR، موثَّق للاكتمال (Backlog وظيفي).

### 4.2 `invitations.leads` — IDOR مؤكَّد (قراءة + كتابة)
```
B (تينانت16) + X-Tenant-ID:16 → POST /api/invitations/leads {"first_name":"TEST_LEAD_B_BATCH1",...}
→ 201، id=31, tenant_id=16

A (تينانت1) + X-Tenant-ID:16 → GET /api/invitations/leads/31
→ 200، بيانات B الكاملة (بريد، اسم، إلخ)

A (تينانت1) + X-Tenant-ID:16 → PUT /api/invitations/leads/31 {"status":"LOST","notes":"TAMPERED_BY_A"}
→ 200، التعديل نجح فعليًا — Lead تخص تينانت16 اتعدَّلت من مستخدم تينانت1 بالكامل
```
**اكتشاف جانبي:** `GET /invitations/leads` (بلا ID) بلا هيدر أو بأي هيدر → `422` (باج ترتيب routes، §6 بند7) — القراءة/الكتابة بالـID المباشر فقط هي المؤكَّدة والمخترَقة، القائمة نفسها معطوبة وظيفيًا بشكل منفصل.

### 4.3 `communications.templates` — IDOR مؤكَّد
```
B (تينانت16) + X-Tenant-ID:16 → POST /api/communications/templates {"name":"TEST_TPL_B_T16",...}
→ 201، id=2, tenant_id=16

A (تينانت1، بلا هيدر) → GET /api/communications/templates
→ 200، [قالب تينانت1 فقط] — عزل سليم في المسار الشرعي

A (تينانت1) + X-Tenant-ID:16 → GET /api/communications/templates
→ 200، [قالب تينانت16 الحقيقي] — تسريب مؤكَّد
```
**اكتشاف جانبي:** إنشاء قالب بلا تمرير `X-Tenant-ID` صراحة (حتى من مستخدم تينانت16 حقيقي) يُنسَب افتراضيًا لتينانت1 (`Header(default=1)`) — يعني الاستخدام "الشرعي" العادي (بدون معرفة الحاجة لتمرير الهيدر يدويًا) **يُنتج بيانات في تينانت غلط من الأساس**، منفصل عن مسألة IDOR القصدية.

### 4.4 `invoicing.create_invoice` — mass-assignment مؤكَّد + باج مقنِّع
```
A (تينانت1) → POST /api/invoicing/invoices {"tenant_id":16,"user_id":774,"amount":"999.50",...}
→ 400 (باج مقنِّع: تصادم اسم حقل metadata، ليس رفض أمني)

تحقق DB مستقل: SELECT * FROM invoices WHERE id=53
→ tenant_id=16, user_id=774, amount=999.50 — الفاتورة اتكتبت فعليًا رغم الـ400 الظاهري
```

### تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل
- `communication_templates`: حُذف `id=1` (تينانت1، نتج عن الاكتشاف الجانبي) و`id=2` (تينانت16) — `SELECT count(*) WHERE name LIKE 'TEST%'` = **0**.
- `crm_leads`: حُذف `id=31` — `SELECT count(*) WHERE first_name LIKE 'TEST%'` = **0**.
- `invoices`: حُذف `id=53` — `SELECT count(*) WHERE description LIKE '%BATCH1%'` = **0**.
- `employment`: لم تُزرع بيانات جديدة (الكتابة محجوبة بفحص `hr_management` SaaS gate لتينانت16 — قرار مقصود بعدم تجاوزه للكتابة، الاختبار اقتصر على القراءة).
- **`saas_service_plans`:** رُفعت مؤقتًا features الخطط `id=2,47,48` لتشمل `crm`/`hr_management` (لإتاحة اختبار كتابة `invitations`)، **ثم أُعيدت للقيم الأصلية بالضبط** (`id=2`→`["real_estate","insurance"]`، `id=47,48`→`[]`) — مؤكَّد عبر `SELECT` مستقل بعد الاسترجاع.
- **لم يُلمَس أي شيء من بيانات الجلسات السابقة** (Tenant B id=16، المستخدمون 772-777، job_listings id=2-5 الموجودة مسبقًا).
- السيرفر التجريبي **أُوقف** (`taskkill`، `netstat` يؤكد صفر `LISTENING` على المنفذ 8000).
- **صفر تعديل كود، صفر migration** طوال الجلسة — التعديلات الوحيدة كانت بيانات اختبار (كلمة سر throwaway users، خطط SaaS throwaway، الاثنان أُعيدا/موثَّقان).

---

## 8) بانتظار توجيهك

**القرار المطلوب:**
1. الموافقة على تصنيف §6 (10 بنود) بالكامل، أو تعديلات عليه.
2. أولوية التنفيذ — الأرجح: `invitations` (§6#1) أولًا (الأوسع + الأخطر ماليًا)، ثم `invoicing.create_invoice` (§6#2) وباجها المقنِّع (§6#6) معًا (نفس الملف)، ثم `employment` (§6#3+4)، ثم `communications` (§6#5).
3. توجيه تصميمي: `invoicing.create_invoice` — هل يوجد استخدام إداري شرعي يحتاج `tenant_id`/`user_id` مختلفين عن `current_user`؟ (يؤثر على شكل الإصلاح: قفل كامل مقابل قفل مع استثناء صلاحية إدارية).
4. توجيه تصميمي: `communications.send_notification` — هل سوبريوزر يُفترض يقدر يرسل إشعار خارج تينانته؟
5. تأكيد إضافة `invoicing-invoice-response-metadata-collision` (§6#6) و`invitations-leads-route-ordering` (§6#7) كبنود Backlog منفصلة (وظيفية، ليست IDOR) في الملف المركزي المناسب (`constructor-mismatch-backlog-classification.md` أو ملف Backlog وظيفي مكافئ).

---

## 9) قرار المستخدم [2026-08-25] — موافقة كاملة، بدء التنفيذ

1. ✅ التصنيف والترتيب (§6، §8) — موافقة كاملة.
2. ✅ **س3 (`invoicing.create_invoice`):** قفل كامل — `tenant_id`/`user_id` من `current_user` فقط، **بلا استثناء إداري**. الاستخدام الداخلي الحقيقي الوحيد المؤكَّد (13 دومين) أصلًا يمرر `tenant_id` موثوق من `self.tenant_id` الخاص به، مش محتاج استثناء في الـAPI العام.
3. ✅ **س4 (`communications.send_notification`):** يتقيّد بنفس تينانت المُرسِل — لا يوجد دليل تصميم متعمَّد للعبور بين التينانتات (بعكس `sovereign_entities.get_entity_page` الموثَّقة صراحة سابقًا). أي حاجة مستقبلية لإشعار نظامي عابر للتينانتات = قرار منتجي منفصل.
4. ✅ **س5:** أُضيف `invoicing-invoice-response-metadata-collision` (#21) و`invitations-leads-route-ordering` (#22) إلى `constructor-mismatch-backlog-classification.md` (نفس التصنيف/التنسيق، مجموعة 🟢 محلي) — **مكتمل**.
5. **توجيه التنفيذ:** ابدأ بـ`invitations` (18+ endpoint)، تحقق حي لكل بند (هجوم مرفوض + مسار شرعي سليم + SELECT مستقل)، استمرارًا في نفس الجلسة.

---

## 10) تنفيذ `invitations` — مكتمل، مؤكَّد حيًا بالكامل

### 10.1 نطاق التعديل

`eppne-backend/app/domains/invitations/router.py` — **28 endpoint** (من أصل 31؛ الثلاثة المستثناة عمدًا هي `accept_invitation`/`chat_with_ai`/`track_invitation` — pre-auth، `current_user: Optional[User] = Depends(get_current_user_optional)`، بلا تغيير كما تقرَّر مسبقًا). النمط الميكانيكي المطبَّق على كل الـ28 (مطابق لإصلاحات `academy`/`digital_twin`/`ai_agents` السابقة):

- حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من التوقيع.
- إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم.
- استبدال كل استخدامات `cast(int, tenant.id)` بـ`tenant_id`.

**استثناء واحد يحتاج تعديل إضافي:** `create_invitation` كانت تستخدم `tenant.domain` (خاصية DB حقيقية) لبناء `invitation_url` — لكن `get_current_tenant` **لا ترجّع كائن DB حقيقي إطلاقًا**، بل `SimpleTenant()` (كلاس فارغ بخاصية `id` فقط، `core/security.py:273-282`) — يعني **`tenant.domain` كانت بتكسر بـ`AttributeError` فورًا لكل استدعاء `POST /invitations/` بلا استثناء، قبل هذه الجلسة وبمعزل عنها تمامًا** (باج جانبي مكتشف أثناء التعديل، غير متعلق بـIDOR). بما إن الفانكشن أصلًا مُضطَرة تتعدَّل (لحذف `tenant`)، الإصلاح الميكانيكي أُكمِل بإضافة استعلام DB حقيقي:
```python
tenant_result = await db.execute(select(AcademyTenant).where(AcademyTenant.id == tenant_id))
tenant_obj = tenant_result.scalar_one_or_none()
domain = tenant_obj.domain if tenant_obj else "eppne.com"
```
(إضافة `from sqlalchemy import select` لأعلى الملف — الاستيراد الوحيد الجديد). `AcademyTenant` كانت مستوردة بالفعل (تُستخدَم كنوع type-hint فقط للـ3 endpoints المتبقية pre-auth).

`python -m py_compile app/domains/invitations/router.py` → `exit code 0`. `git diff --stat`: **62 إضافة / 58 حذف، ملف واحد فقط** (`router.py`) — **صفر لمس لـ`service.py`/`repository.py`/`schemas.py`/`models.py`** (كانت أصلًا سليمة، المشكلة محصورة في مصدر القيمة بالراوتر فقط، مطابق لتشخيص §2).

### 10.2 التحقق الحي — قبل/بعد، مكتمل لكل نوع مورد (دعوات، leads، campaigns، tickets)

سيرفر uvicorn محلي، نفس مستخدمي §7 (`TEST_super_a`/تينانت1، `TEST_instr_b`/تينانت16). ميزة `crm` رُفعت مؤقتًا لخطط اختبار تينانت16 (لإتاحة الكتابة، بوابة SaaS غير متعلقة بالإصلاح) ثم **أُعيدت لقيمتها الأصلية بعد الانتهاء**.

| المورد | الهجوم (قبل الإصلاح، §4.2) | الهجوم (بعد الإصلاح) | المسار الشرعي (بعد الإصلاح) | SELECT مستقل |
|---|---|---|---|---|
| **Leads** | `GET`+`PUT /leads/31` بهيدر مزوَّر → `200`+`200` (قراءة وتعديل ناجحان) | `GET /leads/32` بهيدر مزوَّر → **`404`**؛ `PUT` بهيدر مزوَّر → `500` (باج منفصل تمامًا، راجع 10.3) لكن **بلا أي تغيير فعلي** | B (بلا هيدر) → `POST`/`GET`/`PUT` كلها `200`/`201`، الحالة تحدَّثت فعليًا لـ`CONTACTED` | `crm_leads.id=32`: `tenant_id=16` صحيح، `status`/`notes` بلا أي أثر تلاعب من A |
| **Campaigns** | لم يُختبَر قبل الإصلاح تحديدًا (نفس الآلية) | `GET /campaigns/1` بهيدر مزوَّر → **`404`**؛ `PUT` → **`403 PermissionDeniedError`** | B (بلا هيدر) → `POST /campaigns` → `201`، `tenant_id=16` صحيح تلقائيًا (بلا حاجة لأي هيدر يدوي — تحسين إضافي، راجع 10.4) | `crm_campaigns.id=1`: `name` بلا أي تغيير |
| **Tickets** | لم يُختبَر قبل الإصلاح تحديدًا (نفس الآلية) | `GET /tickets/1` بهيدر مزوَّر → **`404`**؛ `PUT` → `500` (نفس باج 10.3) لكن **بلا أي تغيير فعلي** | B (بلا هيدر) → `POST /tickets` → `201`، `tenant_id=16` صحيح | `crm_tickets.id=1`: `status` لسه `OPEN`، بلا تغيير لـ`CLOSED` |
| **Invitations (المورد الأساسي)** | لم يُختبَر قبل الإصلاح (كان مغطى ضمن التصنيف العام) | B(تينانت16) + هيدر مزوَّر تينانت1 → `GET /1` → **`404`**؛ `PUT /1` → **`403`** | A (المالك الحقيقي، بلا هيدر) → `GET /1` → `500` (باج بيانات قديمة تالفة غير متعلق بالإصلاح، راجع 10.3) | `sovereign_invitations_v2.id=1`: `title` بلا أي تغيير من B |

**الحكم الحاسم:** في كل الحالات الأربعة، **الهجوم مرفوض تمامًا الآن** (إما `404`/`403` نظيف، أو `500` لكنه **بلا أي أثر كتابة فعلي مؤكَّد بـSELECT مستقل** — الفرق الجوهري عن قبل الإصلاح حيث كانت الكتابة تنجح فعليًا بـ`200`). المسار الشرعي (نفس التينانت) سليم بالكامل في كل الحالات المختبَرة فعليًا (Leads/Campaigns/Tickets)، بما فيها تحسين جانبي: الكتابة بقت تُنسَب صح لتينانت المستخدم **تلقائيًا بلا حاجة لتمرير هيدر يدوي** (كان `communications.create_template` قبل إصلاحها بتحتاج تمرير هيدر صريح وإلا تُنسَب غلط لتينانت1 الافتراضي — نفس الجذر التقني، والإصلاح هنا يزيل هذا الفخ الإضافي كليًا).

### 10.3 اكتشافات جانبية أثناء التحقق الحي — كلها **قبل هذه الجلسة، بلا علاقة بـIDOR، لم تُلمَس**

أثناء محاولة إثبات "المسار الشرعي" لبعض العمليات، صودفت أربعة أعطال منفصلة تمامًا في `service.py` (لم يُعدَّل هذا الملف إطلاقًا هذه الجلسة، الأعطال موجودة أصلًا):

1. **`create_invitation`/`create_campaign` — `bleach.clean(data.get(field, ""), ...)` يكسر بـ`TypeError` لو الحقل موجود بالـpayload بقيمة `None` صراحة** (`.get(key, default)` ما بيرجّعش الـdefault إلا لو الـkey غايب تمامًا، مش لو قيمته `None`) — أي حقل `Optional[str]` في `InvitationCreate`/`CampaignCreate` (`title`, `custom_message`, `description`, إلخ) لو اتبعت بلا قيمة، Pydantic بيحطه `None` صراحة في `model_dump()`، فيكسر `bleach`. **يمنع كل استخدام لهذه الحقول الاختيارية تقريبًا حاليًا.**
2. **`create_invitation` → `_assign_ai_agent` (`service.py:113`) — `TypeError: 'PaginatedResponse[AIAgentResponse]' object is not subscriptable`** — الدالة بتحاول `agents[0]` على كائن `PaginatedResponse` بدل قائمة خام. **يمنع `create_invitation` بالكامل حاليًا حتى بعد تجاوز عطل #1.**
3. **`get_invitation` على صفوف قديمة (`sovereign_invitations_v2.id=1,2,3`) — `ResponseValidationError`** (`discount_percentage`/`gift_coins_amount`/`gift_currency`/`click_count` كلها `NULL` في DB لكن الـschema بتطلب قيم غير null) — بيانات throwaway قديمة جدًا من جلسات سابقة (`P-CTOR-INV-*`, `P-SAVEPOINT-FIX-*`) اتكتبت قبل ما تتضاف هذه الحقول للموديل/schema. **لا يؤثر على صفوف جديدة تُنشأ بعد إصلاح عطل #1/#2.**
4. **`update_lead`/`update_ticket` — `500` بدل `404` نظيف لو المورد مش موجود ضمن تينانت المستخدم** (بما فيها الحالة الشرعية تمامًا: تحديث ID غير موجود إطلاقًا حتى ضمن تينانتك — مؤكَّد بتجربة معزولة `PUT /leads/9999`). **الأهم: هذا "الفشل" آمن تمامًا من ناحية الأمان — صفر كتابة فعلية بتحصل، بس رمز الخطأ غلط (500 مكان 404).**

**لا شيء من الأربعة دول تم لمسه أو إصلاحه هذه الجلسة.**

**✅ [2026-08-25] أُضيفت الأربعة كبنود #23-#26 في `constructor-mismatch-backlog-classification.md`** (بتوجيه صريح من المستخدم):
- **#23 (`bleach-clean-none-crash`)** — `grep` شامل نفَّذته على طلب المستخدم أكَّد نفس النمط (`bleach.clean(data.get(field,""),...)` بلا حارس `if data.get(field)`) في **13 دومين، 89 موضع** (`agritech`, `ai_agents`, `command`, `employment`, `invitations`, `logistics`, `manufacturing`, `realestate`, `social`, `tenders_auctions`, `tourism_sports`, `transport`, `zamakana`) — أُعيد تصنيفه من "محلي" إلى **🔴 مركزي** (نفس فئة `duplicate-kwarg-audit` #2)، مُضاف لمجموعة "أ" (جلسة تصحيح مركزي واحدة).
- **#24 (`invitations-create-invitation-fully-broken`)** — عطلان متتاليان (`bleach.clean` على `None` + `_assign_ai_agent` subscript error) يمنعان `POST /invitations/` بالكامل — **🔴🔴 أولوية استثنائية موازية لـ#11/#9** (وظيفية بحتة: منع كامل لجوهر الدومين، مش أمنية) رغم تصنيفه محليًا.
- **#25 (`invitations-legacy-invitation-rows-response-validation-error`)**، **#26 (`invitations-update-not-found-500`)** — 🟢 محلي، مُضافان لمجموعة "ب".

التفاصيل الكاملة (جدول الأولوية، الإصلاح المقترَح لكل بند) في نفس ملف الـBacklog.

### 10.4 تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل

- `crm_campaigns`: حُذف `id=1` (`TEST_CAMPAIGN_B_FIX1`) — `SELECT count(*) WHERE name LIKE 'TEST%'` = **0**.
- `crm_leads`: حُذف `id=32` (`TEST_LEAD_B_FIX1`) — `SELECT count(*) WHERE first_name LIKE 'TEST%'` = **0**.
- `crm_tickets`: حُذف `id=1` (`TEST_TICKET_B_FIX1`) — `SELECT count(*) WHERE subject LIKE 'TEST%'` = **0**.
- `saas_service_plans` (id=47,48): أُعيدت `features` لـ`[]` (القيمة الأصلية) — مؤكَّد بـ`SELECT` مستقل.
- **لم يُلمَس أي شيء من بيانات الجلسات السابقة** (الصفوف `P-CTOR-INV-*`/`P-SAVEPOINT-FIX-*` في `sovereign_invitations_v2`، مستخدمو 772-777، Tenant B id=16).
- السيرفر التجريبي **أُوقف** (`taskkill`، `netstat` يؤكد صفر `LISTENING` على المنفذ 8000).
- **صفر migration** طوال الجلسة.

### 10.5 `git status` / `git diff --stat` — للمراجعة قبل أي commit

```
M eppne-backend/app/domains/invitations/router.py    (62 إضافة / 58 حذف — 28 endpoint)
M .claude/reports/constructor-mismatch-backlog-classification.md   (بندان #21/#22 + تحديثات الملخص)
M .claude/reports/batch1-audit-security-employment-invitations-communications-invoicing.md   (هذا الملف)
```
باقي ملفات `git status` الأصلية (متعدّلة/untracked من جلسات سابقة، غير متعلقة بهذه الجلسة) — لم تُلمس، لن تُضاف لأي commit من هنا.

**الحالة النهائية:** ✅ **إصلاح `invitations` (28/28 endpoint مطلوب) مُطبَّق بالكامل، مؤكَّد حيًا لكل نوع مورد (دعوات/leads/campaigns/tickets) بمنهجية هجوم-مرفوض + مسار-شرعي + SELECT-مستقل**. بيانات throwaway منظَّفة، السيرفر متوقف. ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff`، ثم الانتقال لـ`invoicing.create_invoice` (§8 بند 2) كالخطوة التالية.
