# البند 3 — جاهزية الـAPI لكل مكوّن UI مرشَّح (فحص فقط، صفر كتابة كود)

**تاريخ:** 2026-09-02
**السياق:** استكمال مباشر بعد إغلاق الثمانية دومينات (commit `1bb70b2`). هذا الملف فحص تحقُّق فقط — **لم يُكتَب أي مكوّن بعد**، بانتظار مراجعتك وتأكيدك.

**القائمة الكاملة النهائية: 7 مكوّنات مرشَّحة** (5 invitations + 1 tourism-sports من الخطة الأصلية + `CreatePostModal` المكتشَف حديثًا في social = السادس/السابع حسب العدّ — راجع بند Backlog `social-createpostmodal-missing-component-decision`).

تحقق مباشر عبر `ls` على كل مجلد components فعليًا (مش افتراضًا من التقرير القديم) + قراءة كل page.tsx مستهلِك + قراءة كل hook مصدر البيانات + تأكيد شكل الـschema الفعلي.

---

## ✅ جاهزة 100% — يمكن الكتابة فورًا (6 من 7)

### 1. `CampaignCard` (invitations)
- **المستهلِك:** `app/(dashboard)/invitations/campaigns/page.tsx:6` — `<CampaignCard key={campaign.id} campaign={campaign} />`
- **مصدر البيانات:** `useCampaigns()` (`hooks/invitations/useCampaigns.ts`) → `InvitationsService.listCampaigns(params)` → `GET /invitations/campaigns`
- **تأكيد الجاهزية:** الهوك مُصلَح ومتحقَّق منه هذه الجلسة (رينيم `getCampaigns`→`listCampaigns` + إزالة باج `.then(res=>res.data)`)، `tsc` صفر أخطاء على هذا الملف. الـbackend endpoint موجود ومسجَّل بالكامل (repo+service+router)، لم يُلمَس هذه الجلسة لأنه كان جاهزًا أصلاً.
- **شكل البيانات (`CampaignResponse`):** `id`, `name`, `description`, `campaign_type`, `status` (`ACTIVE`/`DRAFT`/`PAUSED`/`COMPLETED`/`CANCELLED`), `budget_mrusdt`, تواريخ، قنوات — كل الحقول اللي هيحتاجها المكوّن موجودة في الـschema المولَّد.
- **الحالة:** 🟢 **جاهز 100%**

### 2. `CampaignStatusBadge` (invitations)
- **المستهلِك:** نفس الصفحة (`campaigns/page.tsx:7`)، بالإضافة لاستخدام محتمل داخل `CampaignCard` نفسه.
- **مصدر البيانات:** نفس `campaign.status` من `CampaignResponse` أعلاه — صفر endpoint إضافي، مجرد عرض نصي/لوني بناءً على enum.
- **ملاحظة:** يوجد بالفعل `components/invitations/CampaignStatusBadge.tsx` **مكتمل ومبني فعليًا** (تأكدت بـ`ls` — موجود، مش مفقود!). **هذا البند غير مطلوب فعليًا — كان خطأ في القايمة الأصلية.** راجع القائمة المُصحَّحة في آخر الملف.
- **الحالة:** ✅ **موجود بالفعل — صفر عمل مطلوب**

### 3. `InvitationCard` (invitations)
- **المستهلِك:** `app/(dashboard)/invitations/invitations/page.tsx:6` — `<InvitationCard key={invitation.id} invitation={invitation} />`
- **مصدر البيانات:** `useInvitations()` → `InvitationsService.listInvitations(params)` → `GET /invitations/`
- **تأكيد الجاهزية:** مُصلَح ومتحقَّق منه هذه الجلسة (رينيم `getInvitations`→`listInvitations` + إزالة باج `.then`)، `tsc` صفر أخطاء.
- **شكل البيانات (`InvitationResponse`):** `id`, `title`, `custom_message`, `target_entity_identifier`, `invitation_type` (`GENERAL`/`PRIVATE`), `target_type`, `status` (`DRAFT`/`SENT`/`ACCEPTED`/`DECLINED`/`EXPIRED`)، `invitation_url` — مطابقة تمامًا لما تستهلكه الصفحة (`i.title`, `i.custom_message`, `i.target_entity_identifier`).
- **الحالة:** 🟢 **جاهز 100%**

### 4. `InvitationStatusBadge` (invitations)
- **المستهلِك:** نفس الصفحة (`invitations/page.tsx:7`).
- **تأكيد:** `ls components/invitations/` **لا يحتوي** على `InvitationStatusBadge.tsx` — **مفقود فعليًا** (بعكس `CampaignStatusBadge` أعلاه). صفر endpoint إضافي مطلوب — نفس `invitation.status` من البيانات الجاهزة أعلاه.
- **الحالة:** 🟢 **جاهز 100%** (بيانات جاهزة، المكوّن نفسه فعلاً مفقود)

### 5. `TicketCard` (invitations — **تنبيه تسمية:** يوجد مكوّن بنفس الاسم في `components/tourism-sports/TicketCard.tsx`، مختلف تمامًا وغير ذي صلة)
- **المستهلِك:** `app/(dashboard)/invitations/tickets/page.tsx:6` — `<TicketCard key={ticket.id} ticket={ticket} />`
- **مصدر البيانات:** `useTickets()` → `InvitationsService.listTickets(params)` → `GET /invitations/tickets`
- **تأكيد الجاهزية:** مُصلَح ومتحقَّق منه هذه الجلسة (رينيم `getTickets`→`listTickets`)، `tsc` صفر أخطاء.
- **شكل البيانات (`TicketResponse`):** `id`, `subject`, `description`, `priority`, `status` (`OPEN`/`IN_PROGRESS`/`RESOLVED`/`CLOSED`)، `user_name`, `comments` — مطابقة لما تستهلكه الصفحة (`t.subject`, `t.description`).
- **الحالة:** 🟢 **جاهز 100%** — لازم يُبنى في `components/invitations/TicketCard.tsx` (مسار مختلف عن نظيره في tourism-sports، صفر تعارض فعلي بمجرد وضعه في المجلد الصحيح)

### 6. `TicketStatusBadge` (invitations)
- **المستهلِك:** نفس الصفحة (`tickets/page.tsx:7`).
- **تأكيد:** `ls components/invitations/` **لا يحتوي** عليه — مفقود فعليًا. صفر endpoint إضافي — نفس `ticket.status` من البيانات الجاهزة أعلاه.
- **الحالة:** 🟢 **جاهز 100%**

### 7. `CreatePostModal` (social)
- **المستهلِك:** `app/(dashboard)/social/page.tsx:9` — `<CreatePostModal isOpen={createPostOpen} onClose={...} />`
- **مصدر البيانات:** `useCreatePost()` (`hooks/social/usePosts.ts`) → `SocialService.createPost(data)` → `POST /social/posts`
- **تأكيد الجاهزية:** هذا الـendpoint كان جاهزًا **قبل بداية أي جلسة من هذه السلسلة بالكامل** (لم يُلمَس لا في هذه الجلسة ولا في التصنيف — كان دايمًا "أ" مكتمل). `useCreatePost` سليم ومتحقَّق منه.
- **شكل البيانات (`PostCreate`):** `content?`, `post_type` (افتراضي `TEXT`), `media_urls?` (افتراضي `[]`), `page_id?`, `group_id?` — كل الحقول اختيارية عدا `post_type`/`media_urls` (وليهم قيم افتراضية) — نموذج بسيط قابل للبناء فورًا.
- **ملاحظة:** يوجد مكوّن `components/social/PostComposer.tsx` بالفعل لكنه **مكوّن مختلف** (مش modal، مش مستورَد في `page.tsx` أصلاً) — لا يغطي هذه الحالة.
- **الحالة:** 🟢 **جاهز 100%**

---

## 🔴 غير جاهز — ممنوع البناء الآن (1 من 7)

### `TransferCard` (tourism-sports)
- **المستهلِك:** `app/(dashboard)/tourism-sports/sports/transfers/page.tsx:5` — `<TransferCard key={transfer.id} transfer={transfer} />`
- **مصدر البيانات المطلوب:** `useTransfers()` (`hooks/tourism-sports/useTransfers.ts`) — **لسه بيستدعي `getTransfers` كـbare import مكسور** (تأكدت بقراءة الملف الحالي الآن، بعد كل تعديلات هذه الجلسة — لم يُصلَح عمدًا، كان مُدرَجًا في قائمة "تحتاج قرار" لـtourism-sports).
- **سبب عدم الجاهزية (مؤكَّد من الباك إند):** `TendersAuctionsRepository`... آسف، تصحيح: `TourismSportsRepository` **لا تملك `get_transfer`/`list_transfers` إطلاقًا** — حتى `service.py: place_transfer_bid` نفسها بتستدعي `self.repo.get_transfer(transfer_id)` **داخليًا في مسار الـidempotency-cache بس**، وهي دالة **غير مُعرَّفة فعليًا في `repository.py`** (استدعاء معطوب موجود بالفعل في الكود الأصلي، لم نلمسه). صفر `list` endpoint لأي شكل من أشكال عمليات الانتقال.
- **الحالة:** 🔴 **غير جاهز — API غير موجود إطلاقًا (لا endpoint، لا حتى دالة repository حقيقية).** بناء هذا المكوّن الآن هيعرض بيانات وهمية أو يفشل بصمت. **ممنوع الكتابة** لحد ما يُبنى `list_transfers`/`get_transfer` في الباك إند أولاً (قرار/عمل منفصل تمامًا، خارج نطاق "مكوّن UI فوق API جاهز").

---

## 📋 الخلاصة — القائمة المُصحَّحة النهائية

| # | المكوّن | الدومين | جاهزية الـAPI | ملاحظة |
|---|---|---|---|---|
| 1 | `CampaignCard` | invitations | 🟢 جاهز | ابنِه |
| 2 | `CampaignStatusBadge` | invitations | ✅ موجود بالفعل | **لا تبنِه — موجود** |
| 3 | `InvitationCard` | invitations | 🟢 جاهز | ابنِه |
| 4 | `InvitationStatusBadge` | invitations | 🟢 جاهز | ابنِه |
| 5 | `TicketCard` | invitations | 🟢 جاهز | ابنِه (مسار: `components/invitations/`) |
| 6 | `TicketStatusBadge` | invitations | 🟢 جاهز | ابنِه |
| 7 | `CreatePostModal` | social | 🟢 جاهز | ابنِه |
| — | `TransferCard` | tourism-sports | 🔴 غير جاهز | **لا تبنِه — API غير موجود** |

**العدد الفعلي القابل للتنفيذ الآن: 5 مكوّنات** (`CampaignCard`, `InvitationCard`, `InvitationStatusBadge`, `TicketCard`, `TicketStatusBadge`, `CreatePostModal` — 6 فعليًا لو حسبنا CreatePostModal، لكن `CampaignStatusBadge` يخرج من القائمة لأنه موجود بالفعل). **التصحيح الجوهري عن الخطة الأصلية:** العدّ الأصلي "5 invitations" كان يتضمَّن `CampaignStatusBadge` كأنه مفقود — **هو مش مفقود**، اكتُشف بالـ`ls` المباشر في هذه الجلسة. فبدل "5 invitations + 1 tourism-sports + 1 social جديد = 7"، الرقم الحقيقي هو **4 invitations (بعد استبعاد CampaignStatusBadge) + 1 social (CreatePostModal) = 5 مكوّنات جاهزة للبناء الآن**، + `TransferCard` واحد محظور.

**بانتظار مراجعتك وتأكيدك قبل أي كتابة كود فعلية.**

---

## ✅ التنفيذ (2026-09-02/03) — الستة مكوّنات مبنية ومتحقَّق منها

بعد موافقتك، بُنيت الستة مكوّنات (`CampaignCard`, `InvitationCard`,
`InvitationStatusBadge`, `TicketCard` [في `components/invitations/`، صفر
تعارض مع `components/tourism-sports/TicketCard.tsx`], `TicketStatusBadge`,
`CreatePostModal`)، باستخدام نفس أسلوب مكوّنات موجودة في نفس الدومين
كمرجع تصميم: `LeadCard.tsx`/`LeadStatusBadge.tsx`/`CampaignStatusBadge.tsx`
(بطاقات وbadges invitations)، `CreateOccasionModal.tsx` (نمط المودال في
social)، `PostCard.tsx` (أسلوب عرض المنشورات).

### 🔴 اكتشاف حرج أثناء التحقق — 3 حقول كانت تُسقَط صامتًا من الـAPI

تحقق `tsc` على الصفحات المستهلِكة كشف إن schemas الاستجابة (Pydantic)
في الباك إند **كانت بتُسقط حقولًا موجودة فعليًا على الموديل من كل
استجابة API** — نفس فئة اكتشاف `createAuction` بالجلسة السابقة، لكن هنا
فقدان بيانات فعلي (silent data loss) مش مجرد wrapper مفقود:

1. **`CampaignResponse.status`** — العمود موجود على `MarketingCampaign`
   (نموذج DB) بقيمة افتراضية `DRAFT`، لكن الـschema ماكانتش بتصدّره
   إطلاقًا. **كل استجابة API لحملة تسويقية كانت بتُخفي حالتها الفعلية
   تمامًا** — `CampaignStatusBadge` (الموجود من قبل) كان هيعرض دايمًا
   بيانات ناقصة لو استُخدم فعليًا مع بيانات حقيقية من الـAPI.
2. **`InvitationResponse.current_uses`** — نفس النمط بالضبط.
3. **`TicketCreate/TicketResponse.priority`** — كان `str` عام
   (regex-validated بس، مش enum) بدل `Literal["LOW","MEDIUM","HIGH","URGENT"]`
   دقيق. لا فقدان بيانات هنا (القيمة كانت بتوصل صح)، بس دقة النوع اتحسّنت
   لتطابق الفعل الحقيقي.

**الإصلاح:** أضفت الحقول/الدقة الناقصة لـ`eppne-backend/app/domains/invitations/schemas.py`
(mechanical بحت — الحقول موجودة على الموديل بالفعل، صفر migration، صفر
قرار تصميم). **تحقق حي:** `tests/test_invitations_response_schema_fields_wiring.py`
(3 اختبارات، DB حقيقية) — **3 passed** (exit code صريح مؤكَّد، بدون أي pipe).

### 🟡 اكتشاف إضافي — تصادم منهجي `null` مقابل `undefined` عبر ملفات types اليدوية

بعد إصلاح الحقول الثلاثة، ظهر تصادم نوع مختلف تمامًا: ملفات
`types/invitations.ts`/`types/social.ts` (يدوية، مش مولَّدة) بتستخدم
`field?: X` (يعني `X | undefined`) لكل حقل اختياري، بينما schemas
الباك إند الفعلية بترجع `X | null` لأي حقل `Optional[...] = None` في
Pydantic (تسلسل JSON قياسي). هذا تصادم **موجود مسبقًا وعابر لكل الملف**
— نفس الفئة بالضبط ظاهرة أصلاً على `Lead`/`LeadCard` الموجودَين قبل أي
جلسة من هذه السلسلة (`leads/page.tsx` عنده نفس الخطأ حاليًا، غير ملموس،
خارج النطاق). لم ألمس الملف بالكامل (نطاق ضخم، قرار منفصل) — أصلحت فقط
الحقول الدقيقة اللي مكوّناتي الستة بتستهلكها فعليًا في `SovereignInvitation`،
`MarketingCampaign`، `SupportTicket`، `TicketComment`، `Post` (تحويل
`?: X` إلى `?: X | null` + تصحيح نوعين لحقول Decimal مُسلسَلة كـstring
`discount_percentage`/`gift_coins_amount`/`share_reward_mr7`).

### التحقق النهائي

- `tsc` مُصفَّى على الستة مكوّنات + 4 صفحات مستهلِكة: **صفر أخطاء** عدا
  خطأ واحد **معروف ومُوثَّق مسبقًا وغير مرتبط** (`social/page.tsx`:
  `gift` implicit-any، ناتج عن `getDigitalGifts` — بند "ب" موثَّق من
  التصنيف الأصلي، صفر لمس بالتصميم).
- `tsc` غير مُصفَّى (كامل المشروع): 1447 سطر مخرجات (777 خطأ) — قريب
  جدًا من الأساس التاريخي الموثَّق (1253-1268) ولا يتضمن أي ملف من
  الملفات اللي عدّلتها بشكل غير متوقَّع (تأكدت بفحص كل مستهلِك آخر
  لنفس الأنواع: `CampaignPerformanceChart.tsx`, `useTickets.ts` — صفر
  استخدام للحقول اللي وسّعت نوعها).
- الباك إند: `python -c "from app.main import app"` نجح بعد كل تعديلات
  `schemas.py`.

**الحالة: مكتمل، متحقَّق منه بالكامل. جاهز لعرض git diff --stat قبل الـcommit.**
