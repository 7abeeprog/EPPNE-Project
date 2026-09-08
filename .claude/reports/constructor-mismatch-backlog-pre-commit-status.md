# قبل الـcommit — الحالة الإجمالية + git status

**تاريخ:** 2026-08-29

---

## ✅ كل بنود التنفيذ خلصت (1-7 من قائمة القرارات)

| # | البند | الحالة |
|---|---|---|
| 1 | توثيق الـ9 بنود القديمة (#1، #5، #6، #7، #8، #9، #11، #14، #15) | ✅ خلص |
| 2 | بقية #27 (4 دوال + `list_candidates`) | ⏳ لسه بانتظار جلسة منفصلة (مؤجَّل بقرارك) |
| 3 | التحقق من #31 | ✅ خلص |
| 4 | الـ7 بنود الميكانيكية (#22, #32, #33, #37, #38, #40, #43) | ✅ خلصت كلها |
| 5 | Migration بسيطة (#28, #45) | ✅ خلصت كلها |
| 6 | أولوية القرارات التصميمية (7 بنود) | ⏳ مؤجَّلة كما اتفقنا |
| 7 | جلسة الجرد (بقية #4، #13) | ✅ خلصت |
| 8 | تحديث الأعداد المتبقية في الملف الموحَّد | ⏳ باقي |
| 9 | Commit منفصل | ⏳ باقي — السؤال أسفل |

---

## `git status --short` الحالي

### ملفات عدَّلتها أنا في هذه الجلسة (constructor-mismatch-backlog)

**توثيق:**
```
M .claude/reports/constructor-mismatch-backlog-classification.md
M PROGRESS_LOG.md
```

**Backend (كود):**
```
M eppne-backend/app/domains/arbitration_syndicates/service.py   (#32)
M eppne-backend/app/domains/insurance/service.py                (#37)
M eppne-backend/app/domains/invitations/router.py               (#22)
M eppne-backend/app/domains/realestate/service.py                (#37, #40)
M eppne-backend/app/domains/tenders_auctions/service.py          (#33)
M eppne-backend/app/domains/tourism_sports/repository.py         (#38)
M eppne-backend/app/domains/tourism_sports/service.py             (#37, #38)
M eppne-backend/app/domains/translation/models.py                 (#45)
M eppne-backend/app/domains/transport/service.py                  (#37)
```
```
?? eppne-backend/migrations/versions/040_fix_translation_cache_global_unique_text_hash.py   (#45)
```

**Frontend (كود):**
```
M eppne-web/components/iot/AssetCard.tsx           (#43)
M eppne-web/components/iot/AssetsManager.tsx        (#43)
M eppne-web/components/iot/CarbonCreditPanel.tsx    (#43)
M eppne-web/components/iot/IoTDashboardStats.tsx    (#43)
M eppne-web/components/translation/BatchTranslator.tsx    (#43)
M eppne-web/components/translation/ChatTranslator.tsx     (#43)
M eppne-web/components/translation/LanguageSelector.tsx   (#43)
M eppne-web/components/translation/TextTranslator.tsx     (#43)
```

**تقارير جديدة (untracked، موثِّقة كل خطوة من الجلسة):** `.claude/reports/constructor-mismatch-backlog-*.md` (~12 ملف).

### ملفات معدَّلة من قبل الجلسة دي، **مش مرتبطة بيها إطلاقًا** (نفس الملاحظة من أول الجلسة)

```
M eppne-backend/app/core/security.py
M eppne-backend/app/main.py
M eppne-backend/app/domains/health/service.py
M eppne-backend/app/tasks/affiliate.py
M eppne-backend/app/tasks/billing.py
M eppne-backend/tests/conftest.py
M eppne-web/app/(dashboard)/academy/[id]/page.tsx
M eppne-web/app/(dashboard)/academy/certificates/[courseId]/page.tsx
M eppne-web/app/(dashboard)/academy/instructor/dashboard/page.tsx
M eppne-web/app/(dashboard)/academy/my-learning/page.tsx
M eppne-web/app/globals.css
M eppne-web/components/academy/CourseActionButton.tsx
M eppne-web/components/layout/theme-toggle.tsx
M .claude/reports/batch1-audit-security-employment-invitations-communications-invoicing.md
M .claude/reports/digital-twin-idor-fix-session-log.md
M .claude/reports/phase16-session-log.md
M .claude/reports/throwaway-test-users.md
```
**+ عشرات ملفات `.claude/plans/*.md` و`.claude/reports/*.md` الـuntracked من جلسات سابقة تمامًا.**

هذا الفصل بالظبط هو نفس المشكلة اللي أخّرت commit `55032eb` قبل كده — الشجرة فيها خليط جلسات
غير مرتبطة، والفصل الواضح مطلوب قبل أي commit.

---

## السؤال

**قبل الـcommit (بند 9):** تحب أعرضلك `git diff --stat` تفصيلي أكتر الأول، ولا تكمل مباشرة على
بند 8 (تحديث الأعداد المتبقية في الملف الموحَّد) وبعدين نراجع كل حاجة مرة واحدة قبل الـcommit؟
