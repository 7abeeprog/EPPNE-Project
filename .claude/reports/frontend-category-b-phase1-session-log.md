# Phase 1 — أرخص وأضمن الإصلاحات (Category B backlog)

**تاريخ:** 2026-09-01
**المرجع:** `.claude/reports/category-b/group1..group5-*.md` (تصنيف الجلسة السابقة `frontend-category-b-classification-all-domains`)
**النطاق:** 130 حالة تقريبًا — صفر قرار منتجي جديد، فقط توصيل موجود بموجود.

**ملاحظة منهجية:** هذه الجلسة معتمدة بالكامل من المستخدم (رسالة البداية نفسها = خطة مفصّلة بالحالات والدومينات). التعديلات المطبَّقة هنا كلها "توصيل ميكانيكي" (service method + router endpoint يكشف دالة موجودة فعلًا في repository.py، بلا أي قرار تصميم جديد) — بما يطابق منهجية realestate المعتمدة سابقًا. التحقق الحي يتم على مستوى كل دومين/مجموعة قبل الانتقال للتالي، مش على مستوى كل حالة فردية، كما نص المستخدم صراحة في تعليمات الجلسة.

---

## 1. Agritech routing — نتيجة: **عائق موثَّق، لا تفعيل ممكن الآن**

**الفحص:** قارنت `main.py.bak` (نسخة قديمة، فيها `agritech_router` مسجَّل) مقابل `main.py` الحالي (لا وجود لـagritech إطلاقًا).

**الاكتشاف الحرج:** هذا مش "نسيان تسجيل". فحص `git log -- eppne-backend/app/domains/agritech/router.py` كشف commit موثَّق ومقصود:

- `9e01ede` — `fix(agritech): remove duplicate ai_governance router mistakenly mounted at /agritech` (2026-08-26)
- راجع: `.claude/reports/agritech-status-check-2026-08-26.md` (قراءة فقط، جلسة سابقة)

**الحقيقة:** `router.py` القديم لـagritech كان **نسخة مكررة بالغلط من `ai_governance/router.py`** (نفس الـheader، نفس الـendpoints بتستخدم `AIGovernanceService`) — لم يكن يقدّم أي API حقيقي لـagritech حتى وقت ما كان "مسجَّل". الكود الحقيقي (`service.py` + `models.py` + `repository.py` + `schemas.py`, ~1454 سطر، منطق أعمال كامل: farms, crop cycles, harvest, bio assets, traceability QR, certificates, soil sensors) **موجود وسليم لكن orphaned بالكامل** — صفر نقطة استدعاء (لا HTTP، ولا حتى Celery task، `tasks/agritech.py` عنده import ميت). جداول DB موجودة في migration.

**القرار الموثَّق سابقًا (وما زال ساريًا):** بناء `router.py` حقيقي "قرار منتجي مؤجَّل، مش bug fix" — يحتاج تصميم endpoints من الصفر، مش استرجاع القديم (كان تالف). هذا يتعارض مباشرة مع تفويض هذه الجلسة (صفر قرار تصميم جديد).

**الإجراء المتخذ هنا:** توثيق العائق فقط، **بدون** أي محاولة تفعيل أو كتابة router.py جديد — طبقًا لتعليمات المستخدم الصريحة ("لو مش ممكن، وثّق كعائق منفصل قبل أي محاولة تفعيل"). main.py **لم يُلمَس**.

**أثر جانبي على البند 3:** مكوّنات UI الثلاثة الخاصة بـagritech (من قائمة الـ11 مكوّن) **محظورة تلقائيًا** — الشرط المسبق للكتابة هو "API جاهز 100%"، وagritech عنده صفر endpoint قابل للوصول. لن تُكتب في هذه الجلسة.

**✅ موافقة المستخدم (2026-09-01):** أكَّد المستخدم صحة قرار عدم اللمس، ورقّى agritech رسميًا لبند backlog مستقل بحجم "بناء دومين كامل" (زي transport) — مش جزء من هذه الجلسة. سُجِّل في `PROGRESS_LOG.md` تحت `agritech-full-domain-build` (2026-09-01). البند مغلق نهائيًا في نطاق هذه الجلسة.

---

## 2. حالات "وصلة فقط" (أ) — التقدم حسب الدومين

_(قيد التنفيذ — يُحدَّث أول بأول)_

| الدومين | عدد الحالات | الحالة | تحقق حي |
|---|---|---|---|
| arbitration-syndicates | 7 (6 مُنفَّذة + 1 مؤجَّلة) | ✅ | tsc مستهدَف: `getCase`/`createCase`/`getSyndicates`/`getSyndicate`/`getElection`/`castVote` — صفر أخطاء "no exported member" متبقية لهذه الأسماء. `getElections` (#3) **مؤجَّلة عمدًا**: لا يوجد `list_all_elections`/فلترة عامة في `repository.py` إطلاقًا (فقط `list_syndicate_elections(syndicate_id)`) — بناؤها يتطلب استعلام repository جديد كليًا، خارج حدود "زيرو قرار تصميم" لهذه الجلسة. باقي أخطاء tsc الظاهرة في نفس الدومين (JSX `cn`/`CheckCircle` مفقودة، توقيعات `issueLicense`/`joinSyndicate`/`nominateCandidate`/`castJuryVote` مع idempotencyKey كسلسلة بدل كائن، `getMyLicenses().then(res=>res.data)` على مصفوفة) **موجودة مسبقًا وخارج نطاق الـ119 حالة المصنَّفة** — لم تُلمَس. |
| zamakana | 6/6 | ✅ | أُضيفت named exports `getCampaigns`/`getNodes`/`getScenarios` (aliases لـ`listCampaigns`/`listNodes`/`listScenarios` الموجودة، بشكل `{data}`) في `services/zamakana.ts`. أُنشئ `hooks/zamakana/usePledges.ts` (`useCampaignPledges`/`usePledgeTime`/`useFulfillPledge`) + مكوّنين جديدين `components/zamakana/PledgeCard.tsx` و`PledgeForm.tsx` (بنفس نمط `CampaignCard.tsx`/`JuryVoteModal.tsx` كمرجع تصميم). tsc مستهدَف: صفر أخطاء "no exported member"/"cannot find module" لهذه الأسماء الستة. أخطاء متبقية غير مرتبطة (مفقود `cn` import في `page.tsx`، `tenant_id`/`updated_at` مفقودة من كائنات mock في صفحات أخرى، `PledgeCard` بنفس نمط `CampaignCard`/`NodeCard` الموجود مسبقًا يظهر نفس فجوة الأنواع القديمة بين `types/zamakana.ts` يدوي و`TimePledgeResponse` الفعلي من الـAPI — نمط ما قبل هذه الجلسة عبر الدومين بالكامل، لم يُلمَس). |
| logistics | 6/6 | ✅ | أُضيفت named exports `getEquipmentItem` (يغلّف `getEquipment` الموجودة)، `getInventory`/`getWarehouses` (aliases، بنوع `Parameters<typeof Service.listX>[0]` لتفادي تعارض unions صارمة اكتُشفت أثناء التحقق)، `getInventoryItem` (يغلّف method موجودة)، `getForecasts` (alias) في `services/logistics.ts`. أُنشئ `hooks/logistics/useStats.ts` (`useLogisticsStats`). tsc مستهدَف: صفر أخطاء على `services/logistics.ts`/`hooks/logistics/useStats.ts`. ملاحظة تصحيح ذاتي أثناء التحقق: أول محاولة لـ`getInventory`/`getWarehouses` بنوع params يدوي (`string` بدل union صارم) سبّبت TS2345 حقيقي — أُصلحت فورًا باستخدام `Parameters<typeof ...>[0]`. أخطاء متبقية غير مرتبطة (`useEquipment` list hook بينادي `getEquipment(params)` المفرد بدل `listEquipment(params)`، `.then(res=>res.data)` على methods مُفكَّكة أصلًا في `useInventory`/`useWarehouses`/`useForecast`، أخطاء أنواع صفحات أخرى) — لم تُلمَس. |
| automation | 6/6 | ✅ | أُضيفت named exports `getSecrets` (alias `listSecrets`)، `getAvailableAgents` (alias `listAvailableAgents`)، `toggleWorkflowActive(id, isActive)` (يغلّف `updateWorkflow(id, {is_active})` الموجودة) في `services/automation.service.ts`. أُنشئت 3 مكوّنات جديدة `components/automation/node-configs/{SlackConfig,DatabaseConfig,HttpResponseConfig}.tsx` (بنفس نمط `SQLConfig.tsx`/`NotificationConfig.tsx` كمرجع)، بمفاتيح config مطابقة تمامًا لمعالِجات التنفيذ الفعلية في الباك إند (`service.py`: `_exec_slack`→`webhook_url/message/channel`, `_exec_database`→`query/params/connection_string`, `_exec_http_response`→`status_code/body/headers`). tsc مستهدَف: صفر أخطاء على الملفات الثلاثة الجديدة وعلى الأسماء الثلاثة المُضافة للخدمة. أخطاء متبقية غير مرتبطة (`WorkflowBuilder.tsx`/`NodeSettingsPanel.tsx`/`TriggerSettings.tsx`/صفحات executions — أخطاء أنواع pre-existing لا علاقة لها بالحالات الست) — لم تُلمَس. ملاحظة: توثيق `NodeType` enum رسميًا لتشمل SLACK/DATABASE/HTTP_RESPONSE تحسين اتساق اختياري غير مطلوب (القدرة تعمل فعليًا الآن) — لم يُنفَّذ. |
| health | 2/2 | ✅ | أُضيفت named exports `getMyProfile` (يغلّف `getMyMedicalProfile`، شكل `{data}`) و`updateMyProfile` (يغلّف `updateMyMedicalProfile`) في `services/health.service.ts`. tsc مستهدَف: صفر أخطاء "no exported member" لهذين الاسمين. ملاحظة: `BioProfileManager.tsx` بينادي `updateMyProfile` بنوع محلي `Partial<MedicalProfile>` (من `types/health.ts`) لا يطابق تمامًا `MedicalProfileCreate` المولَّد من الـAPI (يتطلب `health_score`) — نفس نمط فجوة type محلي/مولَّد الملاحَظ في zamakana، pre-existing، خارج النطاق. باقي أخطاء tsc في الدومين (`HealthState` store مفقودة الحقول، `AIPrognosisRadar`/`EmergencySOSButton` أخطاء أنواع أخرى) غير مرتبطة بالحالتين — لم تُلمَس. |
| marketplace | 2/2 | ✅ | أُضيفت named exports `getServices`/`getAddons` (aliases لـ`listServices`/`listAddons`، بنوع `Parameters<typeof Service.listX>[0]`) في `services/marketplace.ts`. tsc مستهدَف: صفر أخطاء "no exported member"/"cannot find module". أخطاء متبقية (type محلي `MarketplaceService`/`ServiceAddon` لا يطابق النوع المولَّد من الـAPI في `page.tsx`/`ServiceDetails.tsx`) pre-existing، لم تُلمَس. |
| employment | 3/3 | ✅ | **الحالة الوحيدة في هذه الدفعة اللي احتاجت تعديل باك إند حقيقي**: `getJob` — أُضيف `EmploymentService.get_job(job_id, tenant_id)` (`service.py`، يستخدم `repo.get_job_listing` الموجودة، يرفع `NotFoundError`) + `GET /employment/jobs/{job_id}` في `router.py` (أُدرج **بعد** `/jobs/open` و`/jobs/my` الثابتين لتفادي تعارض ترتيب المسارات مع FastAPI). **تحقق حي حقيقي** عبر اختبار جديد `tests/test_employment_get_job_wiring.py` (نفس منهجية `test_realestate_getter_endpoints_wiring.py`: DB حقيقية، إنشاء مستخدم+وظيفة فعليين، تأكيد الإرجاع الصحيح + `NotFoundError` لمعرف غير موجود + `NotFoundError` لـtenant_id غلط) — **PASSED** (`pytest`, 73.85s, صفر mock). بعدها أُضيفت named exports `getJob`/`getMyContract` (يغلّف `getMyActiveContract`) في `services/employment.ts` (frontend). tsc مستهدَف: **صفر أخطاء إطلاقًا** في كل ملفات دومين employment (الأنظف حتى الآن في هذه الجلسة). |
| ai-governance/ai-agents | 4/4 | ✅ | `getMyAgents`: named export مضافة في `services/ai-agents.service.ts` (تغلّف `listAgents` الموجودة — بالفعل مُصفّاة بـ`owner_id=current_user.id` في الباك إند، alias كامل). **أُنشئ ملف فرونت إند جديد بالكامل `services/ai-governance.ts`** (6 دوال: `getAgentQuotas`, `setAgentQuota`, `getAgentRateLimits`, `updateAgentRateLimits`, `getAgentUsageSummary`, `getAgentAuditLogs`) — كلها أغلفة رفيعة فوق endpoints باك إند جاهزة بالكامل (`router.py`/`service.py`/`repository.py` لدومين `ai_governance` مكتمل تمامًا، صفر تعديل باك إند). tsc مستهدَف (مُعاد التحقق من `eppne-web/` الصحيح بعد اكتشاف خطأ cwd — انظر ملاحظة تصحيح ذاتي أسفل الجدول): صفر أخطاء "no exported member" على الأسماء الأربعة. أخطاء متبقية غير مرتبطة (`cn`/`Clock` مفقودة، `store/agentStore.ts` بيستورد أنواع تانية أصلًا غير مُصدَّرة من نفس الملف — pre-existing) لم تُلمَس. |

---

| saas | 1/1 | ✅ | أُنشئ مكوّن جديد `components/saas/CreatePlanModal.tsx` (نموذج إنشاء/تعديل خطة، بنفس نمط `SubscribeModal.tsx` كمرجع تصميم) — الـAPI الخلفي (`createPlan`/`updatePlan`) جاهز بالكامل، صفر تعديل باك إند. تصحيح ذاتي أثناء التحقق: أول نسخة من نوع `onSubmit` استبعدت `is_active` فسبّبت TS2345 حقيقي عند تمرير البيانات لـ`useCreatePlan` (يتوقع `Omit<ServicePlan,'id'\|'created_at'\|'updated_at'>` أي `is_active` مطلوب) — أُصلحت فورًا بتضمين `is_active` (افتراضي `true`، أو القيمة الحالية عند التعديل). tsc مستهدَف: صفر أخطاء على المكوّن الجديد. |
| communications | 1/1 | ✅ | أُضيفت named export `getNotifications` (تغلّف `getMyNotifications` الموجودة، بنوع `Parameters<typeof Service.getMyNotifications>[0]`) في `services/communications.service.ts`. tsc مستهدَف: صفر أخطاء "no exported member". |

**ملاحظة تصحيح ذاتي مهمة (2026-09-01):** بعد تشغيل اختبار pytest حي لـemployment (`cd eppne-backend`)، استمر working directory في bash tool على `eppne-backend` — الفحوصات اللاحقة الثلاثة (`employment`, `ai-governance/ai-agents`, `digital-twin`) شُغِّلت بأمر `npx tsc --noEmit -p tsconfig.json` **من مجلد eppne-backend الخطأ** (لا يوجد `tsconfig.json` فيه)، فرجعت صفر أسطر output — بدت "نظيفة" لكنها في الحقيقة لم تُشغَّل إطلاقًا (false negative). تم اكتشاف هذا فورًا (توقّع غريب لصفر أخطاء على `digital-twin` رغم معرفة مسبقة بمشاكل type فيه)، وأُعيد تشغيل tsc الثلاثة من `cd /e/cc/eppne-web &&` صراحة — **النتائج الفعلية مطابقة لما كان مسجَّلًا** (الأسماء الأربعة/الثلاثة/الاثنين المستهدَفة صفر أخطاء، باقي الأخطاء pre-existing كما هو موثَّق أعلاه)، فلا حاجة لتراجع، لكن التسجيل أعلاه لـemployment/ai-governance/digital-twin مبني على إعادة التشغيل الصحيحة. كل tsc بعد هذه النقطة يُشغَّل بـ`cd /e/cc/eppne-web &&` صراحة لتفادي تكرار الخطأ.

## 3. مكوّنات UI فوق API جاهز

_(لم تبدأ بعد)_

---

## ملخص تقدم (نقطة توقف منطقية — 2026-09-01)

**البند 1 (agritech):** ✅ مغلق بالكامل — عائق موثَّق، رُقِّي لبند backlog مستقل (`agritech-full-domain-build` في `PROGRESS_LOG.md`)، بموافقة المستخدم الصريحة.

**البند 2 (119 حالة "وصلة فقط"):** أُنجزت **11 دومين كاملة (40 حالة)** من قائمة "الأسهل" اللي حددها المستخدم صراحة:

| # | الدومين | حالات | باك إند لُمس؟ |
|---|---|---|---|
| 1 | arbitration-syndicates | 6/7 (1 مؤجَّلة) | لا |
| 2 | zamakana | 6/6 | لا |
| 3 | logistics | 6/6 | لا |
| 4 | automation | 6/6 | لا |
| 5 | health | 2/2 | لا |
| 6 | marketplace | 2/2 | لا |
| 7 | employment | 3/3 | **نعم** (endpoint جديد + pytest حي PASSED) |
| 8 | ai-governance/ai-agents | 4/4 | لا |
| 9 | digital-twin | 2/2 | لا |
| 10 | saas | 1/1 | لا |
| 11 | communications | 1/1 | لا |

كل دومين تحقَّق منه حيًا بـtsc مستهدَف (صفر أخطاء "no exported member"/"cannot find module" للأسماء المطلوبة تحديدًا)، ودومين employment تحقَّق منه إضافيًا بـpytest حي ضد DB حقيقية (الحالة الوحيدة اللي احتاجت تعديل باك إند).

**تصحيح ذاتي مسجَّل:** خطأ مؤقت في working directory (بعد `cd eppne-backend` لتشغيل pytest) خلّى 3 فحوصات tsc تُشغَّل من مجلد خطأ فترجع صفر output مضلِّل — اكتُشف فورًا وأُعيد التشغيل الصحيح، والنتائج المسجَّلة أعلاه كلها من التشغيل الصحيح.

**الباقي من البند 2 (~79 حالة عبر دومينات إضافية):** لم يبدأ — يشمل: realestate (12 حالة، الباك إند جاهز من جلسة سابقة، الفرونت إند لسه محتاج تصدير أسماء — اكتُشف أثناء هذه الجلسة إن الجلسة السابقة نفّذت الباك إند فقط)، insurance (10)، invitations (5 aliases فقط، الـ5 مكوّنات UI منها تنتمي للبند 3)، social (11)، transport (9)، tourism-sports (4)، tenders-auctions (10)، manufacturing (4)، command (2), commerce/academy/projects/finance-wallet (سطور متفرقة ~5).

**البند 3 (11 مكوّن UI فوق API جاهز):** لم يبدأ — 5 invitations + 3 agritech (**محظورة** بسبب قرار agritech) + 1 tourism-sports + غير محدد بدقة الباقي (زامكانا مُنجَزة ضمن البند 2 أعلاه).

**التوصية:** التوقف هنا كنقطة منطقية (اكتملت كل الدومينات "السهلة" المحدَّدة صراحة) بدل الاستمرار في كل الـ~79 حالة الباقية دفعة واحدة — طبقًا لتعليمات الجلسة نفسها.
