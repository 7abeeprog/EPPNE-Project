# فئة (ب) — realestate + insurance + invitations

## realestate

منقول/ملخَّص من `E:\cc\.claude\reports\realestate-design-decision-session-log.md`
(جلسة `realestate-hooks-layer-design-decision`، 2026-08-31 — **صفر تنفيذ إضافي
مطلوب هنا، فقط توثيق**). تلك الجلسة نفّذت وتحقّقت حيًا (pytest + DB حقيقية)
من الحالات الثمانية أدناه بالكامل في الباك إند. تم التحقق السريع بالـGrep إن
الحقائق الأساسية لسه صحيحة (`repository.py` فيه `list_units`/`list_units_for_sale`/
`list_property_units` و`router.py` فيه `GET /units`, `GET /units/for-sale`,
`GET /units/{unit_id}`, `PATCH /units/{unit_id}`, `DELETE /units/{unit_id}`,
`GET /units/{unit_id}/ownerships`, `GET /units/{unit_id}/tokenization`,
`GET /smart-contracts/{contract_id}` — كلها موجودة فعليًا الآن).

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getProperties` | `hooks/realestate/useProperties.ts` | TS2305 | ✅ مُنفَّذ بالكامل: `service.list_property_units` + `GET /realestate/units` (migration 043 أضافت 5 أعمدة تسويقية لـ`PropertyUnit`) | **(أ) وصلة فقط** — الباك إند جاهز، ناقص فقط تصدير الاسم من `services/realestate.ts` وربط الهوك |
| 2 | `getProperty` | `hooks/realestate/useProperties.ts` | TS2305 | ✅ مُنفَّذ: `service.get_property_unit` + `GET /realestate/units/{unit_id}` | **(أ) وصلة فقط** |
| 3 | `createProperty` | `hooks/realestate/useProperties.ts` | TS2305 | ✅ موجودة أصلًا باسم `createPropertyUnit` في `services/realestate.ts` (`POST /realestate/units`) — الحقول التسويقية تتدفق تلقائيًا عبر `model_dump()` | **(أ) aliasing** — إعادة تسمية فقط لدالة موجودة بنفس الوظيفة، صفر عمل باك إند |
| 4 | `updateProperty` | `hooks/realestate/useProperties.ts` | TS2305 | ✅ مُنفَّذ: `service.update_property_unit` (فحص ملكية + `PropertyUnitUpdate` schema) + `PATCH /realestate/units/{unit_id}` | **(أ) وصلة فقط** |
| 5 | `deleteProperty` | `hooks/realestate/useProperties.ts` | TS2305 | ✅ مُنفَّذ: `service.delete_property_unit` (فحص ملكية + منع حذف مع ملكيات/تجزئة فعّالة) + `DELETE /realestate/units/{unit_id}` | **(أ) وصلة فقط** |
| 6 | `getPropertyOwnerships` | `hooks/realestate/usePropertyOwnerships.ts` | TS2305 | ✅ مُنفَّذ: `service.get_unit_ownerships` (كان جاهزًا كـ`repo.get_ownerships_by_unit` غير مكشوف) + `GET /realestate/units/{unit_id}/ownerships` | **(أ) وصلة فقط** |
| 7 | `getSmartContractStatus` | `components/realestate/InvestorPortfolio.tsx` | TS2305 | ✅ مُنفَّذ: `service.get_smart_contract_status` (كان `repo.get_smart_contract` غير مستخدَم إطلاقًا) + `GET /realestate/smart-contracts/{contract_id}` | **(أ) وصلة فقط** — ملاحظة: المكوّن المستهلِك (`SmartContractStatusMonitor`) كود يتيم غير مستورَد في أي صفحة فعليًا؛ وفروقات تسمية حقول (`status`/`tx_hash` بالفرونت إند مقابل `execution_status`/`blockchain_tx_hash` في الـschema) تحتاج تعديل استهلاك بسيط لاحقًا |
| 8 | `getAssetTokenization` | `hooks/realestate/useTokenization.ts` | TS2305 | ✅ مُنفَّذ: `service.get_asset_tokenization` (كان `repo.get_tokenization_by_unit` مستخدَمة داخليًا فقط) + `GET /realestate/units/{unit_id}/tokenization` | **(أ) وصلة فقط** |
| 9 | `getAvailableProperties` | `app/(dashboard)/realestate/page.tsx` (فعليًا محتوى الملف هو صفحة تجزئة الأصول — دروب-داون لاختيار عقار مؤهَّل بحقول `title`/`area_sqm`) | TS2305 | ✅ نفس الحالة منطقيًا — إما `RealEstateService.listUnitsForSale` الموجودة فعليًا (`GET /realestate/units/for-sale`)، أو `GET /realestate/units` العامة (من حالة #1) — كلاهما يرجع `PropertyUnitResponse` بالحقول التسويقية المطلوبة (`title`, `area_sqm`) | **(أ) aliasing** — لم تُذكر بالاسم في الجلسة السابقة لكنها تغطية إضافية لنفس البنية المُنجَزة؛ تحتاج فقط تصدير اسم `getAvailableProperties` (كـalias لـ`listUnitsForSale` أو غلاف بسيط حولها) في `services/realestate.ts`، صفر عمل باك إند |
| 10 | `Property` (type) | `hooks/realestate/useProperties.ts` (`types/realestate.ts`) | TS2305 | `PropertyUnitResponse` من `components['schemas']` (عبر `openapi.json`) يحتوي كل الحقول المطلوبة بعد migration 043 | **(أ)** — إضافة type alias/إعادة تصدير في `types/realestate.ts` (`export type Property = PropertyUnitResponse`)، صفر باك إند |
| 11 | `PropertyFormData` (type) | نفس الملف | TS2305 | `PropertyUnitCreate`/`PropertyUnitUpdate` من الـschemas جاهزة | **(أ)** — type alias فرونت إند فقط |
| 12 | `TokenizationFormData` (type) | `hooks/realestate/useTokenization.ts` | TS2305 | `TokenizationCreate` schema جاهزة (`unit_id` + `total_shares` + `share_price_mrusdt` + `minimum_investment_shares` — نفس الحقول المستخدَمة فعليًا في `useCreateTokenization`) | **(أ)** — type alias فرونت إند فقط |

**ملخص realestate:** 12 حالة، **كلها (أ)** — صفر حالات (ب) متبقية.
الحالات الثمانية الأساسية (#1-8) منفَّذة ومتحقَّق منها حيًا بالكامل في جلسة
`realestate-design-decision-session-log.md` (Migration 043 + 10 ملفات اختبار
جديدة، صفر رجعية). الحالات الإضافية الأربع (#9-12) هنا هي تغطية فجوات لم
تُسمَّ صراحة في تلك الجلسة لكنها امتداد مباشر لنفس البنية المُنجَزة — لا تحتاج
أي عمل باك إند إضافي، فقط: (أ) تصدير أسماء/aliases في `services/realestate.ts`
و`types/realestate.ts`، (ب) ربط الهوكس المتبقية بالـendpoints الجاهزة.

---

## insurance

فحص كامل حي لـ `router.py` + `service.py` + `repository.py` + `schemas.py` +
`models.py` (دومين `insurance`). لا توجد أي أدلة على جلسة تصميم سابقة لهذا
الدومين.

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getClaim` | `hooks/insurance/useClaims.ts` | TS2305 | `repository.get_claim(claim_id)` موجودة (سطر 117) لكن **بدون فلترة `tenant_id`** — لا service method ولا router endpoint يكشفها (فقط `get_my_claims`/`submit_claim`/`review_claim` موجودة) | **(أ) وصلة فقط** — الطبقة العميقة جاهزة، ناقص service wrapper (مع تحقق `claim.tenant_id == tenant_id`) + `GET /insurance/claims/{claim_id}` |
| 2 | `updateClaim` | `hooks/insurance/useClaims.ts` | TS2305 | `repository.update_claim(claim_id, **kwargs)` موجودة (سطر 136، تُستخدَم داخليًا في `review_claim`)، وschema `InsuranceClaimUpdate` (schemas.py سطر 88: `status`, `approved_amount_mrusdt`, `investigation_notes`, `oracle_verification_hash`) **موجودة بالفعل وغير مُستخدَمة في أي endpoint عام** | **(أ) وصلة فقط** — كل الطبقات (repo+schema) جاهزة؛ ملاحظة: `review_claim` الموجودة أصلًا تغطي مسار الموافقة/الرفض مع منطق الدفع — `updateClaim` عام قد يحتاج قرار تصميم بسيط عن نطاقه مقابل `reviewClaim` |
| 3 | `updateEmployeeProfile` | `hooks/insurance/useEmployeeProfile.ts` | TS2305 | `repository.update_employee_profile(user_id, **kwargs)` موجودة (سطر 184) — غير مستخدَمة في `service.py` ولا `router.py` (فقط `create_employee_profile`/`get_employee_profile` موجودتان) | **(أ) وصلة فقط** — ناقص service wrapper + `PUT /insurance/employee-profiles/me` (أو مسار مشابه) |
| 4 | `getInsuranceStats` | `hooks/insurance/useInsuranceStats.ts` | TS2305 | **لا يوجد أي أثر لإحصائيات مُجمَّعة** في أي من `router.py`/`service.py`/`repository.py` (بحث `grep -i stats` رجّع صفر نتائج) | **(ب) غير موجود إطلاقًا** — يحتاج دالة `get_stats` جديدة (نفس نمط `InvitationsService.get_stats` الموجودة في دومين `invitations`: تجميع `list_policies`+`list_subscriptions`+`list_claims`+... يدويًا) + endpoint `GET /insurance/stats` جديد كليًا |
| 5 | `getPension` | `hooks/insurance/usePensions.ts` | TS2305 | `repository.get_pension(pension_id)` موجودة (سطر 152) — لا service method ولا router endpoint (فقط `get_my_pensions`/`create_pension`) | **(أ) وصلة فقط** — ناقص service wrapper (تحقق ملكية/tenant) + `GET /insurance/pensions/{pension_id}` |
| 6 | `updatePension` | `hooks/insurance/usePensions.ts` | TS2305 | `repository.update_pension(pension_id, **kwargs)` موجودة (سطر 164، تُستخدَم داخليًا في `disburse_monthly_pensions` لتحديث `last_payout_tx`) | **(أ) وصلة فقط** — ناقص service wrapper عام + `PATCH /insurance/pensions/{pension_id}` |
| 7 | `suspendPension` | `hooks/insurance/usePensions.ts` | TS2305 | `PensionStatus.SUSPENDED` enum موجودة فعليًا في `models.py` (سطر 42) — `repository.update_pension` قادرة على تعيين `status=SUSPENDED` مباشرة، لكن لا دالة/endpoint مخصَّصة | **(أ) وصلة فقط** — نفس نمط `launch_campaign` في دومين `invitations` (wrapper بسيط حول تحديث الحالة) + `POST /insurance/pensions/{pension_id}/suspend` |
| 8 | `getPolicies` | `hooks/insurance/usePolicies.ts` | TS2305 | ✅ موجودة بالكامل باسم `InsuranceService.listPolicies` في `services/insurance.ts` (تُطابق تمامًا `GET /insurance/policies` مع نفس الـparams: `policy_type`, `is_active`, `skip`, `limit`) | **(أ) aliasing** — إعادة تسمية فقط، صفر عمل باك إند |
| 9 | `updatePolicy` | `hooks/insurance/usePolicies.ts` | TS2305 | `repository.update_policy(policy_id, **kwargs)` موجودة (سطر 59) — لا service method ولا router endpoint | **(أ) وصلة فقط** — ناقص service wrapper + `PATCH /insurance/policies/{policy_id}` |
| 10 | `deletePolicy` | `hooks/insurance/usePolicies.ts` | TS2305 | **لا توجد دالة حذف على أي طبقة** — لا `repository.delete_policy`، لا service، لا router. عمود `is_deleted` موجود على `InsurancePolicy` (models.py سطر 71) ومُستخدَم فعليًا للفلترة في `get_policy`/`list_policies`، لكن لا شيء يكتب إليه فعليًا | **(ب) غير موجود إطلاقًا** — يحتاج `repository.soft_delete_policy` جديدة + service (مع فحص صلاحية — من يملك حق حذف بوليصة؟) + `DELETE /insurance/policies/{policy_id}` |
| 11 | `getSubscription` | `hooks/insurance/useSubscriptions.ts` | TS2305 | `repository.get_subscription(subscription_id)` موجودة (سطر 75) — لا service method عام (فقط `get_my_subscriptions`) ولا router endpoint فردي | **(أ) وصلة فقط** — ناقص service wrapper + `GET /insurance/subscriptions/{subscription_id}` |
| 12 | `cancelSubscription` | `hooks/insurance/useSubscriptions.ts` | TS2305 | لا توجد دالة "cancel" مخصَّصة، لكن `repository.update_subscription(subscription_id, **kwargs)` عامة موجودة (سطر 98، تُستخدَم فعليًا في `renew_subscription` لتعيين `status="ACTIVE"`) — قادرة تمامًا على تعيين `status="CANCELLED"` | **(أ) وصلة فقط** — نفس نمط `renew_subscription` الموجودة (wrapper بسيط) + `POST /insurance/subscriptions/{subscription_id}/cancel` |

**ملخص insurance:** 12 حالة — **10 (أ)** (منها حالة واحدة aliasing صفري
التكلفة: `getPolicies`) و**2 (ب)** حقيقيتان: `getInsuranceStats` (endpoint
تجميعي جديد كليًا، لا وجود له مطلقًا) و`deletePolicy` (لا وجود لأي عملية حذف
لبوليصة تأمين رغم استعداد الـschema/الموديل لنمط soft-delete).

---

## invitations

فحص كامل حي لـ `router.py` + `service.py` + `repository.py` (دومين
`invitations`)، بالإضافة لفحص مجلد `components/invitations/` فعليًا (عبر
`Glob`، وليس افتراضًا).

### أ) الهوكس (استدعاءات service مفقودة)

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | ما وُجد في الباك إند | التصنيف |
|---|---|---|---|---|---|
| 1 | `getCampaigns` | `hooks/invitations/useCampaigns.ts` | TS2305 | ✅ موجودة بالكامل باسم `InvitationsService.listCampaigns` (`GET /invitations/campaigns`، نفس الـparams تمامًا: `status`, `campaign_type`, `skip`, `limit`) | **(أ) aliasing** — إعادة تسمية فقط، صفر عمل باك إند |
| 2 | `getInvitations` | `hooks/invitations/useInvitations.ts` | TS2305 | ✅ موجودة بالكامل باسم `InvitationsService.listInvitations` (`GET /invitations/`) | **(أ) aliasing** — صفر عمل باك إند |
| 3 | `getLeads` | `hooks/invitations/useLeads.ts` | TS2305 | ✅ موجودة بالكامل باسم `InvitationsService.listLeads` (`GET /invitations/leads`) | **(أ) aliasing** — صفر عمل باك إند |
| 4 | `getTickets` | `hooks/invitations/useTickets.ts` | TS2305 | ✅ موجودة بالكامل باسم `InvitationsService.listTickets` (`GET /invitations/tickets`) | **(أ) aliasing** — صفر عمل باك إند |
| 5 | `createTicketComment` | `hooks/invitations/useTickets.ts` | TS2305 | ✅ موجودة بالكامل باسم `InvitationsService.addTicketComment` (`POST /invitations/tickets/{ticket_id}/comments`) | **(أ) aliasing** — صفر عمل باك إند |

### ب) مكوّنات UI مفقودة بالكامل (استيراد ملفات غير موجودة)

تأكيد حي عبر `Glob` على `components/invitations/*`: الملفات الموجودة فعليًا
هي `LeadStatusBadge.tsx`, `CampaignStatusBadge.tsx`, `CampaignPerformanceChart.tsx`,
`LeadCard.tsx`, `AIAssistantChat.tsx` فقط. الخمسة التالية **غير موجودة إطلاقًا**:

| # | الاسم المفقود | الملف المستهلك | نوع الخطأ | البيانات الأساسية موجودة في الباك إند؟ | التصنيف |
|---|---|---|---|---|---|
| 6 | `CampaignCard` | `app/(dashboard)/invitations/campaigns/page.tsx` | TS2307 (ملف كامل) | نعم — `CampaignResponse` كاملة عبر `GET /invitations/campaigns` (اسم، وصف، حالة، ميزانية، تواريخ، قنوات) | **(ب) — مكوّن UI مفقود بالكامل، مش مرتبط بـservice.ts** — البيانات جاهزة بالكامل، المكوّن نفسه (JSX) لم يُكتَب مطلقًا |
| 7 | `InvitationCard` | `app/(dashboard)/invitations/invitations/page.tsx` | TS2307 | نعم — `InvitationResponse` كاملة عبر `GET /invitations/` | **(ب) — مكوّن UI مفقود بالكامل** |
| 8 | `InvitationStatusBadge` | `app/(dashboard)/invitations/invitations/page.tsx` | TS2307 | نعم — `InvitationStatus` enum (`DRAFT`/`SENT`/`ACCEPTED`/`DECLINED`/`EXPIRED`) موجود في schemas ومُرجَع فعليًا ضمن `InvitationResponse` | **(ب) — مكوّن UI مفقود بالكامل** (نفس نمط `CampaignStatusBadge`/`LeadStatusBadge` الموجودَين فعليًا كمرجع) |
| 9 | `TicketCard` | `app/(dashboard)/invitations/tickets/page.tsx` | TS2307 | نعم — `TicketResponse` (تحديدًا `app__domains__invitations__schemas__TicketResponse`) كاملة عبر `GET /invitations/tickets` | **(ب) — مكوّن UI مفقود بالكامل** |
| 10 | `TicketStatusBadge` | `app/(dashboard)/invitations/tickets/page.tsx` | TS2307 | نعم — `TicketStatus` enum (`OPEN`/`IN_PROGRESS`/`RESOLVED`/`CLOSED`) موجود في schemas | **(ب) — مكوّن UI مفقود بالكامل** |

**ملخص invitations:** 10 حالات — **5 (أ) aliasing** (كل الأسماء الخمسة
المفقودة من الهوكس لها مقابل حرفي كامل الوظيفة في `services/invitations.ts`،
صفر عمل باك إند) و**5 (ب)** (مكوّنات React كاملة لم تُكتَب إطلاقًا — لكن في
كل الحالات الخمس البيانات التي كانت ستعرضها هذه المكوّنات **جاهزة بالكامل**
في الباك إند عبر endpoints موجودة وموثَّقة أعلاه؛ الفجوة فرونت إند بحتة).

---

## الملخص الإجمالي

| الدومين | عدد الحالات | (أ) | (ب) |
|---|---|---|---|
| realestate | 12 | 12 | 0 |
| insurance | 12 | 10 | 2 |
| invitations | 10 | 5 | 5 |
| **الإجمالي** | **34** | **27** | **7** |

الحالات (ب) السبعة: `getInsuranceStats`، `deletePolicy` (insurance) +
`CampaignCard`، `InvitationCard`، `InvitationStatusBadge`، `TicketCard`،
`TicketStatusBadge` (invitations — مكوّنات UI فقط، بياناتها جاهزة في الباك إند).
