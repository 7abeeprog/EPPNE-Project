# الستة البنود الميكانيكية الباقية — ملخص كامل [2026-08-29]

**الحالة:** ✅ كلهم خلصوا ومُتحقَّق منهم حيًا. `constructor-mismatch-backlog-classification.md` و
`PROGRESS_LOG.md` اتحدَّثوا لكل بند.

---

## #22 — `invitations-leads-route-ordering`

**النطاق طلع أوسع من الموصوف:** مش `/leads` بس — `/stats`، `/campaigns`، `/tickets` كانوا محجوبين
بنفس الآلية بالظبط (كل route بادئته ثابتة كان مُسجَّل بعد `/{invitation_id}` الديناميكي). أعدت
ترتيب الراوتر كله (نقل الأقسام 1-5 الثابتة قبل قسم `/{invitation_id}`).

**تحقق حي عبر Starlette route matching الحقيقي** (مش تخمين):
```
GET /api/invitations/leads     -> handler='list_leads'      (كان get_invitation قبل الإصلاح)
GET /api/invitations/stats     -> handler='get_invitation_stats'
GET /api/invitations/campaigns -> handler='list_campaigns'
GET /api/invitations/tickets   -> handler='list_tickets'
GET /api/invitations/999       -> handler='get_invitation'   (المسار الشرعي لسه شغال صح)
```

## #32 — `arbitration-syndicates-nominate-candidate-wrong-kwarg`

`candidate_user_id=` → `user_id=`. **grep تأكيدي: صفر انتشار** (موضع واحد بس في كل السورس).
دليل قبل/بعد: `TypeError: 'candidate_user_id' is an invalid keyword argument` → `create_candidate()
succeeded: id=1, user_id=991`.

## #33 — `tenders-auctions-naive-vs-aware-datetime`

`datetime.utcnow()` → `datetime.now(timezone.utc)` في الموضعين (`submit_bid`, `place_bid`). دليل
قبل/بعد للاتنين: `TypeError: can't compare offset-naive and offset-aware datetimes` → مقارنة صحيحة
بلا استثناء.

## #38 — `tourism-sports-player-profile-wrong-column-filter`

method جديدة `get_player_profile_by_id(profile_id)` (تفلتر بـ`.id`)، `place_transfer_bid` بقت
تناديها بدل `get_player_profile` (اللي فضلت لموضعها الشرعي التاني). دليل حي (بيانات `id != user_id`
متعمَّد): `get_player_profile(profile_id=4) -> None` (الباج المؤكَّد) → `get_player_profile_by_id(4)
-> id=4, user_id=998` (صحيح).

## #40 — `realestate-ai-agents-execute-agent-action-stale-signature`

حذف `tenant_id=` + إضافة `idempotency_key=`. **grep تأكيدي: صفر مواضع إضافية** بنفس الباج عبر كل
الدومينات. دليل قبل/بعد: `TypeError: got an unexpected keyword argument 'tenant_id'` →
`{'status': 'COMPLETED', ...}` (تنفيذ AI حقيقي كامل + audit log).

## #43 — `frontend-service-export-import-name-mismatch`

**تصحيح دقيق على النطاق الموصوف أصلًا:** `grep` شامل حقيقي (32 ملف، كل الاستيرادات) طلع النتيجة:
**`iot` (4 ملفات) + `translation` (4 ملفات) = 8 ملفات بالظبط، صفر انتشار إضافي** — دول الوحيدين
بنمط camelCase-object. اتصلحوا كلهم (`iotService`→`IoTService`، `translationService`→`TranslationService`).

**`realestate` طلع مش نفس الفئة إطلاقًا** — مشكلة أعمق بكتير (`hooks/realestate/*.ts` بتستورد
دوال مباشرة **غير موجودة إطلاقًا**، أسماء مختلفة تمامًا عن methods الكائن الحقيقية، مش مجرد اختلاف
حالة أحرف). **صفر إصلاح لها — بند Backlog جديد منفصل، يحتاج قرار تصميمي.**

**اكتشاف جانبي إضافي بعد إصلاح الـ8 ملفات:** `tsc --noEmit` كشف إن `IoTService`/`TranslationService`
أنفسهم عندهم أعطال method-name/type-signature حقيقية مستخبية سابقًا خلف باج #43 (`getAssets` غير
موجودة، الصح `getAsset`؛ عدم توافق أنواع في `TranslationService`). **`LanguageSelector.tsx` بس هي
اللي بقت نضيفة 100%** — 7 ملفات تانية لسه فيهم أعطال (منفصلة، مش جزء من #43).

---

## اكتشافان جانبيان جديدان — مُسجَّلان في PROGRESS_LOG.md، صفر إصلاح

1. **`realestate-hooks-layer-nonexistent-function-imports`** — يعطّل الـbuild لـ4 مكوّنات + صفحة
   `realestate` كاملة. أولوية عالية.
2. **`iot-translation-service-method-mismatches-post-backlog43-fix`** — 7 ملفات، أعطال build كانت
   مستخبية خلف #43.

## ملاحظة توثيقية إضافية

اكتشاف `invoicing-generate-invoice-number-count-based-collision` (من جلسة #37 أمس) طلع مش جديد
فعليًا — نفس البج مسجَّل من **2026-08-18**. أضفت تصحيح صريح في PROGRESS_LOG.md يوضّح ده (تقاطع
دليلين مستقلين، لكن التاريخ الصحيح للاكتشاف الأول هو 18/8 مش 29/8).

---

## الحالة الإجمالية لقائمة القرارات (9 بنود)

| # | البند | الحالة |
|---|---|---|
| 1 | توثيق الـ9 بنود القديمة | ✅ خلص |
| 2 | بقية #27 | ⏳ لسه بانتظار جلسة منفصلة |
| 3 | التحقق من #31 | ✅ خلص |
| 4 | الـ7 بنود الميكانيكية (بما فيهم #37) | ✅ **خلصوا كلهم دلوقتي** |
| 5 | Migration بسيطة (#28, #45) | 🟡 #28 خلص — #45 لسه محتاج تحقق حي أول |
| 6 | أولوية القرارات التصميمية | ⏳ مؤجَّلة |
| 7 | جلسة الجرد (بقية #4، #13) | ⏳ لسه ماحصلش |
| 8 | تحديث الأعداد المتبقية في الملف الموحَّد | ⏳ مؤجَّلة لآخر الجلسة |
| 9 | Commit منفصل | ⏳ لسه ماحصلش |

**التالي المقترَح:** #45 (تحقق حي أول قبل أي migration) ← بند 7 (الجرد) ← commit ← تحديث الأقسام
المتبقية.
