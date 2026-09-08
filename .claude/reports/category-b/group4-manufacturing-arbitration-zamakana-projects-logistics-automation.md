# تقرير التصنيف ب — المجموعة 4: manufacturing / arbitration-syndicates / zamakana / projects / logistics / automation

منهجية: تمت قراءة كل ملف `services/<domain>.ts` بالكامل (كل المفاتيح الفعلية)، ثم فحص `router.py` و`service.py` و`repository.py` في الباك إند المقابل، مع مقارنة `openapi.json` كفحص سريع إضافي (لوحظ أن `openapi.json` يحمل بادئة مضاعفة `/manufacturing/manufacturing/...` وقد يكون غير محدَّث بالكامل، لذا اعتُمد `router.py` كمصدر الحقيقة الأساسي).

---

## manufacturing

مفاتيح `ManufacturingService` الفعلية حاليًا: `createFacility, addProductionLine, createBlueprint, createBatch, startProduction, listRawMaterials, registerRawMaterial, consumeRawMaterial, createDigitalTwin, getDigitalTwin, issueQualityCertificate, getEntityCertificates, analyzeMaintenance, getPendingMaintenance, scheduleMaintenance, createSparePart, listSpareParts, restockSparePart`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getFacilities` | `hooks/manufacturing/useFacilities.ts` | TS2305 | `GET /manufacturing/facilities` موجود بالكامل: `router.list_facilities` → `service.list_facilities` → `repo.list_facilities`. الفرونت إند فقط لا يصدّرها كدالة مستقلة (فقط `createFacility` مصدَّرة). | (أ) وصلة فقط |
| 2 | `getFacility` | `hooks/manufacturing/useFacilities.ts` | TS2305 | `GET /manufacturing/facilities/{facility_id}` موجود بالكامل (router+service+repo: `get_facility`). | (أ) وصلة فقط |
| 3 | `updateFacility` | `hooks/manufacturing/useFacilities.ts` | TS2305 | لا يوجد `PUT /manufacturing/facilities/{id}` في router.py، ولا `update_facility` في service.py، ولا أي دالة تحديث في repository.py (فقط `create_facility`, `get_facility`, `list_facilities`). | (ب) غير موجود إطلاقًا |
| 4 | `deleteFacility` | `hooks/manufacturing/useFacilities.ts` | TS2305 | لا يوجد `DELETE /manufacturing/facilities/{id}` ولا `delete_facility` في أي طبقة. حقل `is_deleted` موجود على الموديل لكن بلا أي دالة تستخدمه للحذف المنطقي. | (ب) غير موجود إطلاقًا |
| 5 | `getRawMaterials` | `hooks/manufacturing/useRawMaterials.ts` | TS2305 | إعادة تسمية شبه مطابقة لـ `listRawMaterials` الموجودة فعليًا وتضرب نفس `GET /manufacturing/raw-materials` العامل بالكامل. | (أ) وصلة فقط — إعادة تسمية (alias) شبه مجانية |
| 6 | `useProductionLines` (ملف Hook كامل) | `app/(dashboard)/manufacturing/facilities/[id]/page.tsx`, `app/(dashboard)/manufacturing/page.tsx` | TS2307 | لا يوجد أي `GET` لقائمة خطوط الإنتاج في router.py (فقط `POST /facilities/{facility_id}/lines`)، ولا `list_production_lines` في service.py أو repository.py (فقط `get_production_line` المفرد و`create_production_line`). | (ب) غير موجود إطلاقًا |
| 7 | `usePendingMaintenance` (ملف Hook كامل) | `app/(dashboard)/manufacturing/facilities/[id]/page.tsx`, `app/(dashboard)/manufacturing/page.tsx` | TS2307 | القدرة كاملة وتعمل: `GET /manufacturing/production-lines/{line_id}/pending-maintenance` (router+service `get_pending_maintenance`+repo)، وحتى `ManufacturingService.getPendingMaintenance` موجودة في الفرونت. الناقص فقط ملف الـ hook نفسه. | (أ) وصلة فقط |
| 8 | `useStats` (ملف Hook كامل) | `app/(dashboard)/manufacturing/page.tsx` | TS2307 | لا يوجد أي endpoint إحصائيات (`/manufacturing/stats` أو ما شابه) في router.py، ولا أي دالة تجميع إحصائيات في service.py أو repository.py. | (ب) غير موجود إطلاقًا |

**ملخص manufacturing:** (أ) = 4 حالات، (ب) = 4 حالات. حجم بناء كل حالات (ب): **migration بسيطة** — لا حاجة لأي تعديل DB جديد (كل الحقول والجداول المطلوبة موجودة أصلاً: `ManufacturingFacility.is_deleted`, جدول `production_lines`)، المطلوب فقط إضافة 4 دوال CRUD/تجميع ميكانيكية عبر الطبقات الثلاث (router+service+repo) بدون تصميم schema جديد.

---

## arbitration-syndicates

مفاتيح `ArbitrationSyndicatesService` الفعلية حاليًا: `getMyCases, createDispute, castJuryVote, issueVerdict, listSyndicates, createSyndicate, joinSyndicate, getMyLicenses, issueLicense, createElection, nominateCandidate, voteInElection`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getCase` | `hooks/arbitration-syndicates/useCases.ts` | TS2305 | `GET /arbitration-syndicates/cases/{case_id}` موجود بالكامل (router `get_case` + service `get_case` + repo `get_case`). | (أ) وصلة فقط |
| 2 | `createCase` | `hooks/arbitration-syndicates/useCases.ts` | TS2305 | إعادة تسمية لـ `createDispute` الموجودة فعليًا وتضرب `POST /arbitration-syndicates/cases`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 3 | `getElections` | `hooks/arbitration-syndicates/useElections.ts` | TS2305 | يوجد جزئيًا: `GET /arbitration-syndicates/syndicates/{syndicate_id}/elections` (`list_syndicate_elections` في router+service+repo) لكنه يتطلب `syndicate_id` كجزء من المسار وليس endpoint عام بمعاملات `syndicate_id?`/`status?` اختيارية كما يتوقعه الـ hook. لا يوجد `GET /elections` عام. | (أ) وصلة جزئية — القدرة الأساسية (list بحسب نقابة) موجودة على مستوى router، تحتاج تكييف/توسعة بسيطة لدعم فلترة عامة |
| 4 | `getElection` | `hooks/arbitration-syndicates/useElections.ts` | TS2305 | `GET /arbitration-syndicates/elections/{election_id}` موجود بالكامل (router+service+repo). | (أ) وصلة فقط |
| 5 | `castVote` | `hooks/arbitration-syndicates/useElections.ts` | TS2305 | إعادة تسمية لـ `voteInElection` الموجودة فعليًا وتضرب `POST /arbitration-syndicates/elections/{election_id}/vote`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 6 | `getSyndicates` | `hooks/arbitration-syndicates/useSyndicates.ts` | TS2305 | إعادة تسمية لـ `listSyndicates` الموجودة فعليًا وتضرب `GET /arbitration-syndicates/syndicates`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 7 | `getSyndicate` | `hooks/arbitration-syndicates/useSyndicates.ts` | TS2305 | `GET /arbitration-syndicates/syndicates/{syndicate_id}` موجود بالكامل (router `get_syndicate` + service + repo). | (أ) وصلة فقط |

**ملخص arbitration-syndicates:** (أ) = 7 حالات، (ب) = 0. لا حاجة لأي بناء جديد؛ كل الحالات إما وصلة مباشرة أو إعادة تسمية شبه مجانية.

---

## zamakana

مفاتيح `ZamakanaService` الفعلية حاليًا: `listNodes, createNode, getNode, updateNode, deleteNode, createEdge, getKnowledgeGraph, createCampaign, listCampaigns, getCampaign, pledgeTime, fulfillPledge, getCampaignPledges, createScenario, listScenarios, getScenario, analyzeScenario, addFeedback, confirmScenario`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getCampaigns` | `hooks/zamakana/useCampaigns.ts` | TS2305 | إعادة تسمية لـ `listCampaigns` الموجودة فعليًا وتضرب `GET /zamakana/campaigns`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 2 | `getNodes` | `hooks/zamakana/useNodes.ts` | TS2305 | إعادة تسمية لـ `listNodes` الموجودة فعليًا وتضرب `GET /zamakana/nodes`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 3 | `getScenarios` | `hooks/zamakana/useScenarios.ts` | TS2305 | إعادة تسمية لـ `listScenarios` الموجودة فعليًا وتضرب `GET /zamakana/scenarios`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 4 | `usePledges` (ملف Hook، يُستهلك كـ `useCampaignPledges`) | `app/(dashboard)/zamakana/campaigns/[id]/page.tsx` | TS2307 | القدرة كاملة وتعمل: `GET /zamakana/campaigns/{campaign_id}/pledges` (router `get_campaign_pledges` + service `list_pledges` + repo)، وحتى `ZamakanaService.getCampaignPledges` موجودة فعليًا في الفرونت. الناقص فقط ملف الـ hook. | (أ) وصلة فقط |
| 5 | `PledgeForm` (مكوّن) | نفس الصفحة أعلاه | TS2307 | بيانات ونداءات الدعم موجودة بالكامل: `POST /zamakana/pledges` (`pledgeTime`) و`POST /zamakana/pledges/{id}/fulfill` (`fulfillPledge`) — كلاهما مفعّل في الفرونت والباك إند. النقص هو مكوّن نموذج UI فقط. | (أ) وصلة فقط — طبقة UI فقط |
| 6 | `PledgeCard` (مكوّن) | نفس الصفحة أعلاه | TS2307 | بيانات العرض (`TimePledgeResponse`) متاحة بالكامل عبر `getCampaignPledges` العامل. النقص هو مكوّن عرض UI فقط. | (أ) وصلة فقط — طبقة UI فقط |

**ملخص zamakana:** (أ) = 6 حالات، (ب) = 0. لا حاجة لأي بناء باك إند جديد؛ كل شيء إما إعادة تسمية أو نقص في طبقة الواجهة (hook/مكوّنات) فقط فوق قدرة باك إند جاهزة بالكامل.

---

## projects

مفاتيح `ProjectsService` الفعلية حاليًا: `listProjects, createProject, updateProject, deleteProject, publishProject, listProducts, addContribution, approveContribution, getContribution, getMilestones, addMilestone, completeMilestone, followProject, unfollowProject, getFollowers, getProjectUpdates, addProjectUpdate, getAnalytics`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getProject` | `app/(dashboard)/projects/[id]/page.tsx`, `components/projects/AdvancedMilestones.tsx`, `components/projects/MilestoneTimeline.tsx` | TS2305 | `GET /projects/{project_id}` موجود بالكامل (router `get_project` + service `get_project` + repo `get_project`). الفرونت فقط لديه `listProjects` وليس جلب مشروع مفرد. | (أ) وصلة فقط |
| 2 | `getProjectAnalytics` | `app/(dashboard)/projects/[id]/page.tsx`, `components/projects/ProjectAnalysisDashboard.tsx` | TS2305 | إعادة تسمية لـ `getAnalytics` الموجودة فعليًا وتضرب `GET /projects/{project_id}/analytics`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 3 | `releaseMilestoneFunds` | `components/projects/AdvancedMilestones.tsx` | TS2305 | غير موجود فعليًا كإجراء مستقل: `complete_milestone` في service.py (سطر 336) يكتفي بنشر حدث `event.publish("project.milestone.completed", {...funds_to_release...})` — تم التحقق ولا يوجد أي مستمع (subscriber) لهذا الحدث في كامل الباك إند، ولا أي endpoint أو دالة service/repository منفصلة تُنفّذ فعليًا تحويل الأموال (مثل استدعاء `FinanceService.transfer`). الحدث يُنشر ولا يُستهلك — الإفراج الفعلي عن الأموال غير منفَّذ. | (ب) غير موجود إطلاقًا |

**ملخص projects:** (أ) = 2 حالة، (ب) = 1 حالة. حجم بناء حالة (ب): **migration بسيطة** — لا حاجة لتصميم schema جديد (حقل `funds_to_release` موجود أصلاً على `ProjectMilestone`)، لكن يتطلب إضافة endpoint + دالة service جديدة تربط `complete_milestone`/معلم مكتمل بنداء فعلي لـ `FinanceService.transfer` (نمط موجود ومستخدم في دومينات أخرى)، مع تحديث حالة الإفراج على السجل.

---

## logistics

مفاتيح `LogisticsService` الفعلية حاليًا: `createWarehouse, listWarehouses, getWarehouse, updateWarehouse, deleteWarehouse, createWarehouseZone, receiveInventory, issueInventory, adjustInventory, listInventory, getLowStock, getExpired, getInventoryItem, getInventoryTransactions, createEquipment, listEquipment, getEquipment, updateEquipment, createMaintenance, generateForecast, listForecasts, getLogisticsStats`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `useStats` (ملف Hook كامل) | `app/(dashboard)/logistics/page.tsx` | TS2307 | القدرة كاملة وتعمل: `GET /logistics/stats` (router `get_logistics_stats` مؤكَّد) و`LogisticsService.getLogisticsStats` موجودة فعليًا في الفرونت. الناقص فقط ملف الـ hook. | (أ) وصلة فقط |
| 2 | `getEquipmentItem` | `hooks/logistics/useEquipment.ts` | TS2305 | موجودة فعليًا بنفس الاسم تمامًا كخاصية على `LogisticsService.getEquipmentItem` (تضرب `GET /logistics/equipment/{id}`)، لكنها غير مصدَّرة كدالة مستقلة (named export) يستوردها الـ hook مباشرة. | (أ) وصلة فقط — نفس الاسم موجود، فقط نمط تصدير مختلف |
| 3 | `getForecasts` | `hooks/logistics/useForecast.ts` | TS2305 | إعادة تسمية لـ `listForecasts` الموجودة فعليًا وتضرب `GET /logistics/forecast`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 4 | `getInventory` | `hooks/logistics/useInventory.ts` | TS2305 | إعادة تسمية لـ `listInventory` الموجودة فعليًا وتضرب `GET /logistics/inventory`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 5 | `getInventoryItem` | `hooks/logistics/useInventory.ts` | TS2305 | موجودة فعليًا بنفس الاسم تمامًا كخاصية على `LogisticsService.getInventoryItem` (تضرب `GET /logistics/inventory/{item_id}`)، لكنها غير مصدَّرة كدالة مستقلة. | (أ) وصلة فقط — نفس الاسم موجود، فقط نمط تصدير مختلف |
| 6 | `getWarehouses` | `hooks/logistics/useWarehouses.ts` | TS2305 | إعادة تسمية لـ `listWarehouses` الموجودة فعليًا وتضرب `GET /logistics/warehouses`. | (أ) وصلة فقط — إعادة تسمية (alias) |

**ملخص logistics:** (أ) = 6 حالات، (ب) = 0. لا حاجة لأي بناء باك إند؛ كل القدرات جاهزة بالكامل (بعضها بنفس الاسم حرفيًا لكن بنمط تصدير مختلف، وبعضها إعادة تسمية).

---

## automation

مفاتيح `AutomationService` الفعلية حاليًا (`services/automation.service.ts`): `listWorkflows, getWorkflow, createWorkflow, updateWorkflow, deleteWorkflow, triggerWorkflowManual, getWorkflowExecutions, getExecution, getExecutionLogs, listSecrets, createSecret, deleteSecret, listAvailableAgents, triggerWebhook`.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getSecrets` | `app/(dashboard)/automation/secrets/page.tsx` | TS2305 | إعادة تسمية لـ `listSecrets` الموجودة فعليًا وتضرب `GET /automation/secrets`. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 2 | `toggleWorkflowActive` | `app/(dashboard)/automation/workflows/[id]/page.tsx` | TS2305 | لا يوجد endpoint تبديل مخصص، لكن `PUT /automation/workflows/{workflow_id}` (`updateWorkflow`) موجود بالكامل ويقبل `WorkflowUpdate` التي تحوي حقل `is_active: Optional[bool]` (schemas.py:199) — أي أن التبديل ممكن تمامًا عبر `updateWorkflow(id, { is_active: !current })`. | (أ) وصلة فقط — القدرة موجودة عبر endpoint تحديث عام، تحتاج غلاف (wrapper) بسيط في الفرونت فقط |
| 3 | `getAvailableAgents` | `components/automation/node-configs/AIAgentConfig.tsx` | TS2305 | إعادة تسمية لـ `listAvailableAgents` الموجودة فعليًا وتضرب `GET /automation/ai-agents` (مؤكَّد في router.py سطر 219). لم تكن هناك حاجة للبحث في دومين `ai_agents` المنفصل لأن هذا الـ endpoint خاص بدومين automation نفسه ويعمل بالفعل. | (أ) وصلة فقط — إعادة تسمية (alias) |
| 4 | `SlackConfig` (مكوّن) | `components/automation/NodeSettingsPanel.tsx` | TS2307 | نوع العقدة `SLACK` منفَّذ بالكامل في محرك التنفيذ بـ `service.py` (معالج تنفيذ عند السطر ~308 و~616: "إرسال رسالة إلى Slack"). النقص هو مكوّن نموذج إعداد UI فقط لهذا النوع من العقد. | (أ) وصلة فقط — طبقة UI فقط |
| 5 | `DatabaseConfig` (مكوّن) | `components/automation/NodeSettingsPanel.tsx` | TS2307 | نوع العقدة `DATABASE` منفَّذ بالكامل في محرك التنفيذ بـ `service.py` (معالج تنفيذ عند السطر ~310 و~637: تنفيذ استعلامات قاعدة بيانات مع دعم المعاملات). النقص هو مكوّن نموذج إعداد UI فقط. | (أ) وصلة فقط — طبقة UI فقط |
| 6 | `HttpResponseConfig` (مكوّن) | `components/automation/NodeSettingsPanel.tsx` | TS2307 | نوع العقدة `HTTP_RESPONSE` منفَّذ بالكامل في محرك التنفيذ بـ `service.py` (معالج تنفيذ عند السطر ~312 و~662: رد HTTP للعقدة النهائية). النقص هو مكوّن نموذج إعداد UI فقط. | (أ) وصلة فقط — طبقة UI فقط |

ملاحظة: أنواع العقد `SLACK`/`DATABASE`/`HTTP_RESPONSE` غير مُدرجة رسميًا ضمن enum `NodeType` في `models.py` (السطور 24-56) رغم أن محرك التنفيذ في `service.py` يتعامل معها كسلاسل نصية مباشرة (elif على `node_type`) وينفّذها فعليًا — أي أن القدرة تعمل في وقت التشغيل لكنها غير موثّقة/معتمدة رسميًا في تعريف الـ enum.

**ملخص automation:** (أ) = 6 حالات، (ب) = 0. لا حاجة لأي بناء باك إند؛ الأقرب لعمل مطلوب هو توثيق/إضافة `SLACK`, `DATABASE`, `HTTP_RESPONSE` إلى enum `NodeType` رسميًا (تحسين اتساق، وليس فجوة وظيفية) — سطر واحد لكل قيمة إن أُريد التوثيق الرسمي، لكنه لا يندرج ضمن (ب) لأن القدرة تعمل فعليًا الآن.

---

## الإجمالي عبر المجموعة

| الدومين | (أ) | (ب) |
|---|---|---|
| manufacturing | 4 | 4 |
| arbitration-syndicates | 7 | 0 |
| zamakana | 6 | 0 |
| projects | 2 | 1 |
| logistics | 6 | 0 |
| automation | 6 | 0 |
| **المجموع** | **31** | **5** |
