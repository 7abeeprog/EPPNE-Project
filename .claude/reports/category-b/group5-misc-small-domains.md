# تصنيف Category B — دومينات متفرقة (Group 5)

تحقيق توثيقي بحت (بدون تعديل أي ملف مصدر). تاريخ: 2026-09-01.

منهجية: قُرئ كل `services/<domain>.ts`/`.service.ts` بالكامل (كل المفاتيح الفعلية)، ثم
قُورن باستدعاء الملف المستهلك، ثم فُحص `router.py` → `service.py` → `repository.py`
لكل دومين باك إند ذي صلة، مع مراجعة `openapi.json` كفحص تقاطعي.

ملاحظة عامة مهمة: كل الأسماء المفقودة في هذه المجموعة (`getMyProfile`, `getServices`,
`getJob`, `getMyContract`, `getMyAgents`, `getSystemAlerts`, `getTimeCapsule`,
`getEntityCourses`...) تُستدعى في الملفات المستهلكة بنمط **دوال مستقلة (named
exports)** تُعيد كائن axios خام (`.then(res => res.data)`), بينما الأنماط الموجودة
فعليًا في كل `services/*.ts` هي **كائن واحد (`XService = {...}`)** تُعيد البيانات
مباشرة بعد فك التغليف (`try { return data } catch { throw handleError(...) }`).
هذا يعني أن مجرد "alias" بإعادة تصدير الاسم لا يكفي وحده لإصلاح هذه الأخطاء — الشكل
(shape) يختلف أيضًا. هذا موثق تحت كل حالة بعبارة "نمط استدعاء مختلف".

---

## health

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getMyProfile` | `app/(dashboard)/health/page.tsx` | TS2305 (دالة مستقلة) | `HealthService.getMyMedicalProfile()` موجود بالكامل في `services/health.service.ts`، ووصلته الباك إند `GET /health/profile/me` موجودة في `router.py`/`service.py` | (أ) وصلة فقط — إعادة تسمية شبه طبق الأصل + نمط استدعاء مختلف (axios خام مقابل بيانات مفكوكة) |
| 2 | `updateMyProfile` | `components/health/BioProfileManager.tsx` | TS2305 (دالة مستقلة) | `HealthService.updateMyMedicalProfile()` موجود، `PUT /health/profile/me` موجود بالكامل | (أ) وصلة فقط — نفس الملاحظة أعلاه |

**ملخص health:** (أ)=2, (ب)=0. كلا الاسمين قريب التسمية جدًا من مفتاح فعلي موجود (`getMyMedicalProfile`/`updateMyMedicalProfile`)، والوصلة الخلفية (backend endpoint) مكتملة تمامًا. الفجوة الوحيدة فرونت-إند بحتة (تصدير دوال مستقلة إضافية بنفس التوقيع الذي تتوقعه صفحات الاستهلاك).

---

## iot

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 3 | `@/components/iot/ReadingsChart` | `app/(dashboard)/iot/page.tsx` | TS2307 (وحدة كاملة) | `GET /iot/readings` موجود بالكامل في `router.py` (`get_readings`)، والبيانات (`UtilityReadingResponse`) جاهزة للاستهلاك | (أ) وصلة فقط — البيانات جاهزة، الناقص هو ملف مكوّن الرسم البياني نفسه (لا خدمة API) |
| 4 | `@/components/iot/MaintenanceLogs` | `app/(dashboard)/iot/page.tsx` | TS2307 (وحدة كاملة) | يوجد فقط `POST /iot/maintenance` (إنشاء) و`POST /iot/maintenance/{log_id}/resolve` (حل). **لا يوجد أي `GET` لعرض/سرد سجلات الصيانة** — لا في `router.py` ولا `service.py` ولا `repository.py` (فقط `create_maintenance`/`resolve_maintenance`) | (ب) غير موجود إطلاقًا — جزئيًا: عملية الإنشاء/الحل موجودة، لكن نقطة القراءة/السرد (list) غير موجودة على أي طبقة |

**ملخص iot:** (أ)=1, (ب)=1. حجم (ب): [migration بسيطة] — الجدول `MaintenanceLog` موجود أصلًا في `models.py`، الناقص فقط دالة `list_maintenance` في `repository.py` + `service.py` + مسار `GET /iot/maintenance` في `router.py`.

---

## marketplace

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 5 | `getServices` | `app/(dashboard)/marketplace/page.tsx` | TS2305 (دالة مستقلة) | `MarketplaceService.listServices({service_type, featured, skip, limit})` موجود بالضبط بنفس المعاملات المُستخدمة في الاستدعاء (`service_type`, `featured`, `limit`)، `GET /marketplace/services` مكتمل | (أ) وصلة فقط — إعادة تسمية طبق الأصل (معاملات متطابقة 100%) + نمط استدعاء مختلف |
| 6 | `getAddons` | `components/marketplace/ServiceDetails.tsx` | TS2305 (دالة مستقلة) | `MarketplaceService.listAddons({compatible_with})` موجود بنفس المعامل المُستخدم (`compatible_with: service?.service_type`)، `GET /marketplace/addons` مكتمل | (أ) وصلة فقط — إعادة تسمية طبق الأصل + نمط استدعاء مختلف |

**ملخص marketplace:** (أ)=2, (ب)=0. كلا الاسمين تطابق كامل مع مفتاح موجود بنفس التوقيع؛ لا حاجة لأي تصميم schema، فقط تصدير دوال مستقلة.

---

## employment

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 7 | `getJob` | `app/(dashboard)/employment/jobs/[jobId]/page.tsx` | TS2305 (دالة مستقلة) | **لا يوجد** `GET /employment/jobs/{job_id}` في `router.py` (الموجود فقط: `POST /jobs`, `GET /jobs/open`, `GET /jobs/my`, `PUT /jobs/{job_id}`, `DELETE /jobs/{job_id}`). لكن `EmploymentRepository.get_job_listing(job_id, tenant_id)` (سطر 35) **موجود وجاهز** في `repository.py`، وكذلك `service.py` يستخدمه داخليًا (مثلاً `get_job_applications`) | (أ) وصلة فقط — موجود في `repository.py` غير مكشوف عبر `router.py`/`service.py` كنقطة عامة |
| 8 | `getMyContract` | `app/(dashboard)/employment/page.tsx` | TS2305 (دالة مستقلة) | `EmploymentService.getMyActiveContract()` موجود، `GET /employment/contracts/me` مكتمل بالكامل | (أ) وصلة فقط — إعادة تسمية شبه طبق الأصل (`getMyActiveContract` → `getMyContract`) + نمط استدعاء مختلف (يتبعه `.catch(() => null)` في نفس الملف) |
| 9 | `getMyContract` | `components/employment/AttendanceWidget.tsx` | TS2305 (دالة مستقلة) | نفس السطر 8 أعلاه (نفس الاستيراد يتكرر في ملف ثانٍ) | (أ) وصلة فقط — نفس الملاحظة |

**ملخص employment:** (أ)=3, (ب)=0. `getJob` يحتاج فقط كشف endpoint عام جديد (`GET /employment/jobs/{job_id}`) يستدعي دالة repository موجودة فعليًا — حجم بسيط. البقية alias صرف.

---

## ai-governance / ai-agents

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 10 | `getMyAgents` (من `@/services/ai-agents.service`) | `app/(dashboard)/ai-governance/page.tsx` | TS2305 (دالة مستقلة) | **مطابقة وظيفية كاملة**: نقطة `GET /ai/agents` في `router.py` (سطر 44-62) تُصفّي دائمًا بـ `owner_id=current_user.id` — أي أن `listAgents()` الموجود فعليًا **هو بالفعل** "وكلائي فقط"، لا يوجد endpoint منفصل لكل الوكلاء | (أ) وصلة فقط — alias كامل 100%، `AIAgentsService.listAgents()` يفعل تمامًا ما يطلبه `getMyAgents` |
| 11 | `@/services/ai-governance` (وحدة كاملة) | `components/ai-governance/AuditLogViewer.tsx` | TS2307 | `GET /ai-governance/agents/{agent_id}/audit-logs` موجود بالكامل في `router.py` (`get_agent_audit_logs`) + `service.get_audit_logs()` + `repository.get_audit_logs()` | (أ) وصلة فقط — الملف الفرونت `services/ai-governance.ts` غير موجود إطلاقًا، لكن كل endpoint خلفي مطلوب مكتمل |
| 12 | `@/services/ai-governance` (وحدة كاملة) — `getAgentQuotas`, `setAgentQuota`, `getAgentRateLimits`, `updateAgentRateLimits` | `components/ai-governance/QuotaManager.tsx` | TS2307 | كل الأربعة موجودة بالكامل: `POST/GET /ai-governance/agents/{id}/quotas`, `PUT/GET /ai-governance/agents/{id}/rate-limit` — في `router.py` + `service.py` + `repository.py` | (أ) وصلة فقط — endpoints كاملة، فقط الملف الفرونت مفقود |
| 13 | `@/services/ai-governance` (وحدة كاملة) — `getAgentUsageSummary`, `getAgentQuotas` | `components/ai-governance/UsageDashboard.tsx` | TS2307 | `GET /ai-governance/agents/{id}/usage-summary` موجود بالكامل (`get_usage_summary`) | (أ) وصلة فقط — endpoint كامل، فقط الملف الفرونت مفقود |

**ملخص ai-governance/ai-agents:** (أ)=4, (ب)=0. الدومين الخلفي `ai_governance` **مكتمل تمامًا** (router+service+repository لكل من quotas, rate-limits, audit-logs, usage-summary, check-and-consume). الفجوة الوحيدة هي أن `eppne-web/services/ai-governance.ts` (أو `.service.ts`) **غير موجود إطلاقًا** كملف — تحقق مباشر: `ls services/ai-governance*` أرجع "No such file or directory". حجم العمل لو أُريد سده لاحقًا: إنشاء ملف خدمة واحد يغلّف 6 endpoints موجودة أصلًا (لا حاجة backend).

---

## command

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 14 | `getSystemAlerts` | `hooks/command/useAlerts.ts` | TS2305 (دالة مستقلة) | `CommandService.listAlerts({status, severity, limit})` موجود، `GET /command/alerts` مكتمل | (أ) وصلة فقط — إعادة تسمية طبق الأصل + نمط استدعاء مختلف |
| 15 | `dismissAlert` | `hooks/command/useAlerts.ts` | TS2305 (دالة مستقلة) | `AlertStatus` enum في `models.py` يحوي فقط `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED` — **لا توجد حالة `DISMISSED` إطلاقًا**. أقرب مكافئ وظيفي هو `resolveAlert`/`acknowledgeAlert` الموجودان لكنهما ليسا نفس المعنى (dismiss = تجاهل بدون حل) | (ب) غير موجود إطلاقًا — لا مسار ولا enum value لمفهوم "تجاهل" منفصل عن "حل"/"تأكيد استلام" |
| 16 | `getCommandStats` | `hooks/command/useCommandStats.ts` | TS2305 (دالة مستقلة) | لا يوجد endpoint مستقل باسم "stats". لكن `service.py` يحتوي `_get_core_stats(tenant_id)` و`_get_sector_stats(tenant_id)` (دوال خاصة `_`) وتُدمَج داخل `get_dashboard()` → `GET /command/dashboard` (`DashboardResponse.stats`) | (أ) وصلة فقط — البيانات موجودة كحقل ضمن `GET /command/dashboard` الموجود، لكن كدالة خدمة داخلية غير مكشوفة كـ endpoint منفصل خفيف |
| 17 | `getDashboardMetrics` | `hooks/command/useCommandStats.ts` | TS2305 (دالة مستقلة) | لا يوجد endpoint بهذا الاسم تحديدًا. الأقرب: `GET /command/metrics` (`list_metrics` مع فلاتر `metric_name`/`start_date`/`end_date`) لكنه مخصص لسجلات `PlatformMetric` الفردية وليس "مقاييس لوحة القيادة" المجمّعة كما يوحي `period?: string` في الـ hook | (ب) غير موجود إطلاقًا — لا يوجد مسار مخصص لتجميع مقاييس اللوحة حسب فترة (`period`)؛ الموجود مسار عام لسجلات مقاييس خام فقط |

**ملخص command:** (أ)=2, (ب)=2. حجم (ب): `dismissAlert` = [سطر واحد على enum + endpoint جديد بسيط، migration بسيطة لإضافة قيمة `DISMISSED`]. `getDashboardMetrics` = [migration بسيطة/تصميم schema بسيط] لتجميع مقاييس اللوحة حسب `period` (endpoint جديد فوق بيانات `PlatformMetric` الموجودة أصلًا).

---

## digital-twin

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 18 | `getTimeCapsule` | `app/(dashboard)/digital-twin/legacy/page.tsx` | TS2305 (دالة مستقلة) | `DigitalTwinService.getMyTimeCapsule()` موجود، `GET /digital-twin/time-capsule` مكتمل بالكامل | (أ) وصلة فقط — إعادة تسمية طبق الأصل + نمط استدعاء مختلف |
| 19 | `TwinConfig` (استيراد نوع type-only) | `store/digitalTwinStore.ts` | TS2305 (نوع) | الشكل الكامل موجود في `app/domains/digital_twin/schemas.py` كـ `class TwinConfigResponse(TwinConfigCreate)` (سطر 24) بكل الحقول. لكن `services/digital-twin.service.ts` نفسه يستخدم حاليًا `type TwinConfigResponse = any;` (fallback مؤقت، موثّق بتعليق صريح فيه: "schema types missing from api-types.ts"). تأكيد إضافي: `grep -c "TwinConfigResponse" openapi.json` = **0** — النوع غير مُصدَّر إطلاقًا في `openapi.json` الحالي رغم وجوده في `schemas.py` | (أ) نوع فقط، البيانات موجودة — الـ Pydantic schema كامل في الباك إند، لكنه غير منعكس في `openapi.json`/`api-types.ts` المولّدة (drift توليد قديم)، بالإضافة لعدم تصدير أي اسم `TwinConfig` (الاسم الفعلي القريب هو `TwinConfigResponse`) من ملف الخدمة الفرونت |

**ملخص digital-twin:** (أ)=2, (ب)=0. ملف `digital-twin.service.ts` بأكمله حاليًا معطّل الأنواع عمدًا (١٨+ نوع `any` بتعليق تحذيري صريح من مؤلف الكود) — هذا نطاق أوسع من هذين السطرين فقط، لكن كلا السطرين المطلوبين هنا تحديدًا لا يحتاجان تصميم schema جديد، فقط إعادة توليد الأنواع + تصدير الاسم الصحيح.

---

## saas

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 20 | `@/components/saas/CreatePlanModal` | `app/(dashboard)/saas/plans/page.tsx` | TS2307 (وحدة كاملة) | `SaaSService.createPlan(data: ServicePlanCreate)` موجود بالكامل، `POST /saas/plans` مكتمل. مكوّنات مشابهة (`PlanCard.tsx`, `PlanComparison.tsx`) موجودة فعلًا في `components/saas/` لكن `CreatePlanModal.tsx` تحديدًا غائب | (أ) وصلة فقط — الـ API الخلفي كامل، الناقص ملف مكوّن UI فقط |

**ملخص saas:** (أ)=1, (ب)=0.

---

## finance / wallet

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 21 | `@/components/finance/web3-deposit-withdraw` | `app/(dashboard)/wallet/page.tsx` | TS2307 (وحدة كاملة) | فحص شامل لدومين `finance` بالكامل (`router.py`+`service.py`+`repository.py`) بحثًا عن "deposit"/"withdraw"/"web3" — **لا توجد أي نتيجة**. الموجود فقط: `/balances`, `/transfer`, `/swap`, `/history`, `/admin/crypto-mode`, `/admin/exchange-rates`, `/admin/mint`, `/admin/max-supply` | (ب) غير موجود إطلاقًا — لا يوجد أي مفهوم إيداع/سحب من/إلى شبكة خارجية (bridge) في الباك إند |
| 22 | `@/components/finance/admin-mint-card` | `app/(dashboard)/wallet/page.tsx` | TS2307 (وحدة كاملة) | `FinanceService.mintFunds()` و`FinanceService.setMaxSupply()` موجودان بالكامل، `POST /finance/admin/mint` و`POST /finance/admin/max-supply` مكتملان | (أ) وصلة فقط — الـ API الخلفي كامل، الناقص ملف مكوّن UI فقط |

**ملخص finance/wallet:** (أ)=1, (ب)=1. حجم (ب) لـ `web3-deposit-withdraw`: [تصميم schema جديد] — يتطلب مفهوم جديد كليًا (ربط عناوين محافظ خارجية، تتبع معاملات on-chain للإيداع/السحب)، ليس مجرد endpoint إضافي فوق جدول موجود.

---

## academy (سطر الصفحة العامة فقط)

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 23 | `getEntityCourses` | `app/(public)/public/[slug]/page.tsx` | TS2305 (دالة مستقلة) | جدول `Course` في `academy/models.py` يحوي `org_entity_id` (FK إلى `organization_entities.id`، سطر 133) — **لكن هذا جدول مختلف تمامًا** عن `sovereign_entities_v2` (المُستخدم في `SovereignEntitiesService.getPublicEntityPage`, `sovereign_entities/models.py` سطر 41). لا يوجد أي FK يربط `organization_entities` بـ `sovereign_entities_v2` | (ب) غير موجود إطلاقًا — لا يوجد ربط schema بين كورسات الأكاديمية والكيان السيادي العام |

**ملخص academy (سطر واحد):** (أ)=0, (ب)=1. حجم: [migration بسيطة] — إضافة عمود `sovereign_entity_id` (FK اختياري) إلى `Course` (أو جدول ربط) + endpoint فلترة به؛ الجداول الأساسية نفسها موجودة أصلًا فلا حاجة لتصميم دومين جديد.

---

## commerce

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 24 | `getEntityProducts` | `app/(public)/public/[slug]/page.tsx` | TS2305 (دالة مستقلة) | فحص `commerce/models.py` بالكامل — **لا يوجد أي عمود/مفهوم `entity_id` أو `sovereign_entity_id`** في أي جدول تجاري (`Store`, `Product`, ...) | (ب) غير موجود إطلاقًا |
| 25 | `@/hooks/commerce/useOrders` | `components/commerce/OrderList.tsx` | TS2307 (وحدة كاملة) | `CommerceService.getMyOrders()` موجود، `GET /commerce/orders/me` (`get_my_orders`, يدعم `skip`/`limit`) موجود بالكامل في `router.py` — **لكن** يُرجع `List[OrderResponse]` مباشرة (بدون `total`)، بينما `OrderList.tsx` يتوقع كائن Pagination فيه `data.total` (`skip + limit < data.total`) | (أ) وصلة فقط جزئيًا — الـ hook الفرونتي مفقود بالكامل كملف، والـ endpoint موجود ويدعم `skip`/`limit`، لكن شكل الاستجابة الحالي (مصفوفة بلا `total`) لا يطابق ما يتوقعه استهلاك `OrderList.tsx` |

**ملخص commerce:** (أ)=1(جزئي), (ب)=1. حجم (ب) لـ `getEntityProducts`: [migration بسيطة] — نفس منطق academy أعلاه (لا يوجد أصلًا مفهوم entity في commerce).

---

## communications

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 26 | `getNotifications` | `components/communications/NotificationList.tsx` | TS2305 (دالة مستقلة) | `CommunicationsService.getMyNotifications({is_read, skip, limit})` موجود بالكامل، `GET /communications/notifications/me` مكتمل | (أ) وصلة فقط — إعادة تسمية طبق الأصل (`limit: 50` متوافق) + نمط استدعاء مختلف |

**ملخص communications:** (أ)=1, (ب)=0.

---

## projects (سطر الصفحة العامة فقط)

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 27 | `getEntityProjects` | `app/(public)/public/[slug]/page.tsx` | TS2305 (دالة مستقلة) | فحص `projects/models.py` بالكامل — **لا يوجد أي عمود/مفهوم `entity_id` أو `sovereign_entity_id`** مرتبط بجدول المشاريع | (ب) غير موجود إطلاقًا |

**ملخص projects (سطر واحد):** (أ)=0, (ب)=1. حجم: [migration بسيطة] — نفس النمط المتكرر عبر الصفحة العامة (academy/commerce/projects) — الحل الأمثل غالبًا migration واحدة موحّدة تضيف `sovereign_entity_id` عبر الثلاثة دومينات معًا بدل ثلاث migrations منفصلة، لكن هذا قرار تصميم خارج نطاق هذا التوثيق.

---

## غير قابل للتطبيق — مش استيراد backend

هذه الأسطر الثلاثة ليست مرتبطة بأي `service.ts` أو دومين باك إند — وحدات فرونت إند عامة (utility/UI) لم تُنشأ قط، تم فحص عدم وجودها فقط دون أي تحقيق إضافي:

| # | الاسم المفقود | الملف المستهلك | ملاحظة |
|---|---|---|---|
| 28 | `@/lib/auth-utils` | `app/(dashboard)/academy/admin/studio/page.tsx` | غير قابل للتطبيق — وحدة أدوات عامة، لا علاقة لها بأي service.ts |
| 29 | `@/hooks/use-debounce` | `app/(dashboard)/academy/page.tsx` | غير قابل للتطبيق — hook فرونت إند عام، لا علاقة له بأي service.ts |
| 30 | `@/components/ui/tooltip` | `components/finance/TransactionItem.tsx` | غير قابل للتطبيق — مكوّن UI kit عام، لا علاقة له بأي service.ts |

---

## إجمالي المجموعة

| الدومين | (أ) | (ب) |
|---|---|---|
| health | 2 | 0 |
| iot | 1 | 1 |
| marketplace | 2 | 0 |
| employment | 3 | 0 |
| ai-governance/ai-agents | 4 | 0 |
| command | 2 | 2 |
| digital-twin | 2 | 0 |
| saas | 1 | 0 |
| finance/wallet | 1 | 1 |
| academy (سطر واحد) | 0 | 1 |
| commerce | 1(جزئي) | 1 |
| communications | 1 | 0 |
| projects (سطر واحد) | 0 | 1 |
| **المجموع** | **20** | **7** |

+ 3 أسطر "غير قابل للتطبيق" (auth-utils, use-debounce, ui/tooltip).
