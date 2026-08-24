# جلسة فحص IDOR/أمان عميق في `digital_twin`

**بدأ التسجيل:** 2026-08-24
**الحالة:** ✅ **الجرد + التحقق الحي "قبل" (§5) + الإصلاح (14 endpoint + فحص عضوية إضافي) + التحقق الحي "بعد" (§8) — كل ده مكتمل ومؤكَّد حيًا.** ⏳ **بانتظار موافقتك على `commit` (§9) وقرار تنظيف بيانات throwaway (§10).**

**نطاق الجلسة:** `eppne-backend/app/domains/digital_twin/{router,service,repository,schemas}.py` بالكامل (14 endpoint).

---

## 0) المرجع الميكانيكي — ماذا كان موثَّقًا عن `digital_twin` قبل هذه الجلسة

- **`.claude/reports/simpletenant-fix-session-log.md`**: `digital_twin` مذكور فقط في قائمة "✅ (أ) — `.id` مستخدَمة بشكل صحيح، صفر كراش" (14 موضع). يعني: الدومين **لا يعاني من باج `SimpleTenant`/type-mismatch** (كل استخدام لـ`get_current_tenant` بيستخدم `.id` صح، مفيش تمرير الكائن كامل كـ`int`) — لكن هذا **لا يعني عزل تينانت فعلي**، بس يعني عدم وجود كراش. صفر ذكر لأي إصلاح IDOR فعلي على `digital_twin` في هذا التقرير.
- **`.claude/plans/critical-finding-xtenant-systemic.md`**: `digital_twin` هو **الصف #10** في جدول 🔴 SUSPICIOUS (20 دومين) — نصه بالحرف: *"`router.py:190-208` → `service.py:342-389` — **الأخطر تأثيرًا:** تأكيد وفاة + توزيع تركة/أصول فعلي لمستخدم tenant تاني، بفحص واحد بس (تطابق الهيدر مع tenant الـoracle — الهيدر نفسه مصدر غير موثوق)"*. هذا التقرير **تشخيصي بحت، صفر تنفيذ** — لم يُصلَح أي شيء في `digital_twin` حتى الآن حسب كل المراجع المقروءة.
- **`academy-idor-fix-session-log.md`**: أكَّد أن `GET /academy/digital-twin/me` (سطر 607-610 في `academy/router.py`) هو **endpoint مختلف تمامًا** — جزء من دومين `academy` نفسه (بيانات ملخص أكاديمي/نقاط الطالب على الأرجح)، **ليس** نفس دومين `digital_twin` (`app/domains/digital_twin/`) المطلوب فحصه هنا. صُنِّف في تقرير `academy` كـ"🟢 سليم" ضمن القائمة العامة رقم 35 (`current_user.tenant_id` صحيح). **لا علاقة له بنطاق هذه الجلسة.**

### ✅ تصحيح مقدمة الجلسة — `digital_twin` **ليس ميتًا وظيفيًا**

الافتراض الأولي في طلب الجلسة (نقلًا عن رؤية هرم تنظيمي سابقة) كان صحيحًا **فقط في سياق أكاديمية** (endpoint `academy/digital-twin/me` منفصل تمامًا ولا يمثل الدومين الحقيقي). على مستوى الدومين الحقيقي:

- الملفات الخمسة موجودة وكاملة: `router.py` (280 سطر، 14 endpoint)، `service.py` (457 سطر)، `repository.py` (282 سطر)، `schemas.py` (174 سطر)، `models.py`.
- **مسجَّل فعليًا في `main.py`** (`app/main.py:63` import، `app/main.py:276` تسجيل بـ prefix `/digital-twin`) — قابل للوصول حيًا، مش كود ميت.
- كتابة Backend فعلية موجودة بكثافة: 8 جداول (`DigitalTwinConfig`, `TwinPermission`, `TwinInteractionLog`, `TimeCapsule`, `LegacyBeneficiary`, `DigitalWill`, `DeathOracleCheck`, `LifeMilestone`, `PreBirthRecord`)، تكامل حقيقي مع `finance.transfer` (دفع تفاعل)، `affiliate` (عمولات إحالة)، `saas` (فحص خطة اشتراك)، `event_bus` (نشر أحداث).

**الخلاصة: الدومين حي وظيفيًا بالكامل، فيه كتابة Backend حقيقية، ويستحق نفس عمق الفحص اللي اتطبَّق على `academy`/`sovereign_entities`.**

---

## 1) القراءة الكاملة — الوضع الحالي

قُرئت الملفات الأربعة/الخمسة كاملة. نقطتان بنيويتان حاسمتان اتأكَّدتا بقراءة حية مباشرة (مش نقلًا عن تقارير قديمة):

### 🔴 الجذر لسه غير مُصلَح: `get_current_tenant` لسه بيثق بهيدر `X-Tenant-ID` مباشرة

`app/core/security.py:275-280` (القراءة الحية الحالية، الملف ده معلَّم `M` في `git status` — تعديل غير مرتبط بهذه الجلسة قيد التنفيذ من جلسة تانية، **لم يُلمَس هنا**):

```python
class SimpleTenant:
    id: int

async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```

**صفر مقارنة مع `current_user.tenant_id`** — الاقتراح المعماري المركزي المذكور في `critical-finding-xtenant-systemic.md` (اللي كان سيدمج `current_user.tenant_id` تلقائيًا لو مُصادَق) **لسه غير مُطبَّق**. كل الـ14 endpoint في `digital_twin/router.py` تستخدم `tenant: AcademyTenant = Depends(get_current_tenant)` ثم `tenant_id=cast(int, tenant.id)` — **مصدر `tenant_id` هو هيدر العميل مباشرة، بغض النظر عن هوية `current_user` الحقيقية**، مطابق تمامًا لما توقَّعه `critical-finding-xtenant-systemic.md`.

### 🔴 لا يوجد `require_sector` أو أي حاجز تسجيل راوتر — نفس الوضع النظامي العام

`app/main.py:300-304` (قراءة حية): حلقة تسجيل كل الراوترز **بلا أي `dependencies=[Depends(require_sector(...))]`** — تأكيد أن `require_sector` أُزيلت بالكامل (جلسة منفصلة، 2026-08-20، موثَّقة مسبقًا في `require-sector-removal-subscription-fix-session-log.md`). **هذا نظامي وليس خاص بـ`digital_twin`** — الحاجز الوحيد لكل endpoint هو الـ`Depends` المُعلَن في توقيعها نفسها.

### الجدول العام — كل الـ14 endpoint

| # | الدالة | المسار | `current_user`؟ | مصدر `tenant_id` | فلتر الملكية في الـrepository |
|---|---|---|---|---|---|
| 1 | `get_my_twin_config` | `GET /config` | active_user | هيدر (غير موثوق) | `WHERE user_id=current_user.id AND tenant_id=هيدر` |
| 2 | `update_twin_config` | `PUT /config` | active_user | هيدر | نفس أعلاه |
| 3 | `interact_with_twin` | `POST /interact/{owner_id}` | active_user | هيدر | `twin_owner_id` **من الـpath، بلا أي علاقة بـcurrent_user** + `tenant_id=هيدر` |
| 4 | `create_time_capsule` | `POST /time-capsule` | active_user | هيدر | `user_id=current_user.id AND tenant_id=هيدر` |
| 5 | `send_heartbeat` | `POST /time-capsule/heartbeat` | active_user | هيدر | نفس أعلاه |
| 6 | `get_my_time_capsule` | `GET /time-capsule` | active_user | هيدر | نفس أعلاه |
| 7 | `create_digital_will` | `POST /will` | active_user | هيدر | نفس أعلاه |
| 8 | `get_my_digital_will` | `GET /will` | active_user | هيدر | نفس أعلاه |
| 9 | `report_death` | `POST /death-oracle/report-death` | active_user (**ليس superuser**) | هيدر | **`deceased_id` = `data.reporter_user_id` من جسم الطلب — قيمة حرة بالكامل من العميل، صفر تحقق ملكية أو انتماء تينانت** |
| 10 | `confirm_death` | `POST /death-oracle/confirm-death/{deceased_id}` | **superuser** (لكن بلا فحص تينانت السوبريوزر نفسه) | هيدر | `deceased_id` من الـpath + `tenant_id=هيدر`، **صفر تحقق أن السوبريوزر ينتمي لنفس تينانت الضحية** |
| 11 | `get_my_death_oracle` | `GET /death-oracle/me` | active_user | هيدر | `user_id=current_user.id AND tenant_id=هيدر` |
| 12 | `add_life_milestone` | `POST /milestones` | active_user | هيدر | نفس نمط self-scoped |
| 13 | `get_my_milestones` | `GET /milestones` | active_user | هيدر | نفس نمط self-scoped |
| 14 | `reserve_pre_birth_identity` | `POST /pre-birth` | active_user | هيدر | `parent_1_id=current_user.id` (إنشاء) + فحص تكرار بـ`reserved_sovereign_id + tenant_id=هيدر` |

---

## 2) التصنيف التحليلي (قراءة كود فقط — التحقق الحي لسه معلَّق، راجع §4)

### 🟡 الفئة الأولى (9 endpoints: #1-2, 4-8, 11-13) — self-scoped بـ`user_id=current_user.id`، صفر تسريب بيانات مستخدم آخر حقيقي

نفس منطق تصنيف `finance`/`projects` السابق (راجع `critical-finding-xtenant-systemic.md`): بما أن `user_id` **حقل موثوق دائمًا** (من `current_user.id`، غير قابل للتزوير) وهو فريد على مستوى المنصة كلها (مش per-tenant)، تزوير هيدر `X-Tenant-ID` وحده **لا يكفي لقراءة بيانات مستخدم حقيقي آخر** — أقصى أثر هو محاولة القراءة بمزيج `(user_id الحقيقي, tenant_id مزوَّر)` غير موجود أصلًا (404/إنشاء سجل جديد)، أو **تلويث بيانات (ghost record)**: كتابة سجل (`twin_config`/`time_capsule`/`will`/`milestone`) حقيقي لكن تحت `tenant_id` غلط (نفس فئة "المحافظ الشبح" الموثَّقة في `finance` بـ`critical-finding-xtenant-systemic.md`). **ليست IDOR كلاسيكي (لا تسريب بيانات طرف ثالث)، لكنها فجوة عزل بيانات (data pollution) تستحق توثيق منفصل عن IDOR.**

### 🔴 endpoint #3 — `interact_with_twin`: تجاوز حدود العزل "السيادي" بين التينانتات (سؤال تصميمي + أثر مالي)

هذا الوحيد من التسعة اللي فيه `owner_id` **حر تمامًا من الـpath**، غير مرتبط بـ`current_user`. بالتصميم، الميزة نفسها **مقصودة لتكون بين مستخدمين مختلفين** (زائر يدفع لتفاعل مع توأم شخص آخر) — فمجرد "قراءة توأم شخص آخر" مش عيب بالضرورة. **لكن**:
- مصدر `tenant_id` (هيدر) بيحدد مصفوفة العزل: لو نظام التصميم يقصد إن التفاعل محصور *داخل نفس التينانت* (منطقي جدًا في سياق "الكيانات السيادية" — التسمية نفسها `العزل السيادي` مكتوبة كتعليق صريح في `repository.py`)، فتزوير الهيدر يسمح لزائر تينانت A يتفاعل (ويدفع) مع توأم تينانت B بالكامل، متجاوزًا أي حدود عزل تينانتية مقصودة.
- الدفع (`finance.transfer`) بيستخدم نفس `tenant_id` المزوَّر لجلب محفظة الزائر (`sender_id=visitor_id, tenant_id=هيدر`) — حسب تحليل `finance` السابق في `critical-finding-xtenant-systemic.md`، أقصى أثر هو "محفظة شبح" فاضية (فشل الدفع لعدم كفاية الرصيد)، مش سحب من رصيد حقيقي — **لكن لم يُتحقَّق حيًا بعد لهذا المسار تحديدًا**.
- **سؤال تصميمي مفتوح يحتاج توجيهك:** هل التفاعل عبر-تينانت مع التوائم الرقمية سلوك مقصود بالمنتج (منصة عامة موحّدة) أم يُفترض حصره داخل نفس التينانت (نموذج "دول/كيانات سيادية منفصلة")؟ **لا أفترض النية من القراءة وحدها.**

### 🔴🔴🔴🔴 endpoint #9 — `report_death`: كتابة عبر-تينانت بلا أي فحص ملكية، لأي `active_user`

`deceased_id = data.reporter_user_id` (حقل من جسم الطلب، **الاسم نفسه مضلِّل** — تسميته "المُبلِّغ" لكن الكود يستخدمه فعليًا كـ"هوية المتوفى") — **قيمة حرة بالكامل يختارها العميل**، بلا أي تحقق أنها تخص `current_user` أو حتى تنتمي لنفس تينانت المُبلِّغ. مدمجة مع هيدر `X-Tenant-ID` المزوَّر:

**أي `active_user` عادي (بلا أي صلاحية مرتفعة) يقدر:**
1. يختار `deceased_id` عشوائي (أي مستخدم حقيقي في المنصة، بتخمين ID تسلسلي بسيط).
2. يزوّر `X-Tenant-ID` ليطابق تينانت الضحية الحقيقي.
3. يستدعي `POST /digital-twin/death-oracle/report-death` — ده بيكتب سجل `DeathOracleCheck` حقيقي بحالة `DEATH_PENDING` تحت اسم الضحية، ويسجّل `audit_log` بـ`action=DEATH_REPORTED`، بلا أي علاقة حقيقية بين المُبلِّغ والضحية.

**هذا مؤكَّد من قراءة الكود بثقة عالية جدًا (منطق مباشر، صفر تعقيد وسيط) — أعلى أولوية تحقق حي في هذه الجلسة.**

### 🔴🔴🔴🔴 endpoint #10 — `confirm_death`: **"الأخطر تأثيرًا"، مطابق تمامًا لتوقع `critical-finding-xtenant-systemic.md`**

يحتاج `get_current_superuser` — **لكن هذا فحص دور عام، غير مرتبط بتينانت مُعيَّن** (نفس نمط `sovereign_entities`/`ai_governance` الموثَّق سابقًا: سوبريوزر تينانت1 له نفس صلاحية سوبريوزر تينانت16 على مستوى التوكن). المسار:

```
oracle = repo.get_death_oracle(deceased_id, tenant_id=هيدر)   # deceased_id من path، tenant_id من هيدر — كلاهما حر
if oracle.status != "DEATH_PENDING": raise
...
oracle = repo.update_death_oracle_status(deceased_id, tenant_id, "DEATH_CONFIRMED", release_tx=...)
await self._distribute_legacy(deceased_id, tenant_id)   # يجلب capsule + beneficiaries بنفس tenant_id المزوَّر
```

**أي سوبريوزر (من أي تينانت) يقدر:**
1. يستهدف `deceased_id` لمستخدم حقيقي في تينانت تاني تمامًا.
2. يزوّر `X-Tenant-ID` ليطابق تينانت الضحية.
3. يمرر أي 3 أرقام تعسفية كـ`confirmers` (**صفر تحقق أنهم مستخدمون حقيقيون أو لهم علاقة بالضحية** — `len(confirmers) >= 3` هو الفحص الوحيد).
4. يقلب حالة `DeathOracleCheck` الحقيقية لـ`DEATH_CONFIRMED` + `release_tx` وهمي، ويُفعِّل `_distribute_legacy` (حاليًا `pass` — منطق توزيع الأصول الفعلي لسه TODO غير مُنفَّذ، **لكن الكتابة على حالة الأوراكل حقيقية ومؤثرة**، وتفتح الباب لاستدعاء "الوصية منفَّذة" لاحقًا لو أي كود مستقبلي اعتمد على `status=DEATH_CONFIRMED`).

**مطابقة تامة لتحذير `critical-finding-xtenant-systemic.md` الأصلي ("تأكيد وفاة + توزيع تركة فعلي، بفحص واحد بس") — أعلى أولوية تحقق حي ثانية.**

### 🟡 endpoint #14 — `reserve_pre_birth_identity` — تسريب معلومات ضعيف (probing)

فحص التكرار (`get_pre_birth_record(reserved_sovereign_id, tenant_id=هيدر)`) بيسمح لمستخدم يجرّب أسماء سيادية محجوزة عبر تينانتات مختلفة (تزوير الهيدر) — أثر ضعيف (تأكيد وجود/عدم وجود اسم محجوز فقط، صفر بيانات حساسة)، **أقل أولوية**.

---

## 3) بيانات الاختبار المُجهَّزة (throwaway، بادئة `TEST_` معروفة، مُعاد استخدامها من جلسات سابقة)

- **Tenant A `id=1`** ("Local Test Tenant") / **Tenant B `id=16`** ("TEST_TENANT_B") — من جلسات `academy`/`sovereign_entities`/`ai_agents` السابقة، لم تُلمَس.
- **User A `id=772`** (`TEST_super_a@example.com`, تينانت1, `SUPER_ADMIN`) / **User B `id=774`** (`TEST_instr_b@example.com`, تينانت16, `SUPER_ADMIN`) — نفس المستخدمين المُعاد استخدامهم عبر كل الجلسات السابقة.
- **تعديل throwaway محدود جدًا اتنفذ فعلاً (DB فقط، صفر كود):** كلمة سر الاختبارين اتحدَّثت عبر SQL مباشر (`UPDATE users SET hashed_password=... WHERE id IN (772,774)`) لتوليد hash بـ`passlib`/`bcrypt` لكلمة `TEST_pass_dtwin_2026` — عشان أقدر أسجّل دخول حقيقي وأولّد access tokens صالحة. **هذا تعديل بيانات اختبار فقط (نفس فئة "throwaway data" المعتادة في كل الجلسات السابقة)، صفر تعديل كود أو schema.**
- سيرفر `uvicorn` **بدأ التشغيل** (عبر PowerShell background job، `Start-Job -Name uvicorn_dtwin`) — **الحالة وقت كتابة هذا القسم: لسه بيبدأ (`Get-Job` أظهر `Running`)، لم يُؤكَّد بعد بـ`GET /docs` → `200`**، ولا اتنفذ أي طلب حقيقي على `digital-twin` بعد. **إيقاف مؤقت بناءً على طلب المستخدم قبل إطلاق أول طلب.**

---

## 4) بيانات الاختبار — تحديث بعد إعداد التسجيل الحي

- **كلمة سر `772`/`774` وثِّقت مركزيًا** في `.claude/reports/throwaway-test-users.md` (ملف جديد) + سطر مرجعي في `PROGRESS_LOG.md` (بند `throwaway-test-users-password-documented`) — تنفيذًا لطلب صريح **قبل** إكمال التحقق الحي.
- السيرفر شغّال فعليًا (`GET /docs` → `200`، `Application startup complete`، صفر Traceback عند الإقلاع) — عملية Python منفصلة (`Start-Process` بدل PowerShell job، لأن الـjobs مابتعيشش بين استدعاءات الأداة المنفصلة).
- تسجيل دخول حقيقي لـUser A (`POST /api/identity/login`، بلا هيدر تينانت — الحساب أصلاً تينانت1) وUser B (نفس المسار + `X-Tenant-ID: 16` وقت اللوجن تحديدًا، نفس نمط `academy-idor-fix` — `login` يفلتر بالهيدر بتصميم SAFE موثَّق مسبقًا).
- **إضافة throwaway لتفعيل ميزة `digital_twin`:** كل الـendpoints غير المرتبطة بـ`death-oracle` بتعتمد على `_check_saas_limits()` اللي بترفض أي طلب بلا اشتراك فعال يحتوي `"digital_twin"` في `features`. تينانت1/16 الحاليين (بيانات throwaway من جلسات سابقة) عندهم خطط فعالة بلا هذه الميزة. **تم إنشاء خطة SaaS throwaway مخصَّصة** (`saas_service_plans.id=60`, `code=TEST_DTWIN_PLAN_CODE`, `features=["digital_twin"]`, `service_id=2` — نفس الخدمة المستخدَمة في الخطط الموجودة أصلًا) + اشتراكين throwaway جديدين (`saas_tenant_subscriptions.id=61` تينانت1، `id=62` تينانت16، كلاهما `ACTIVE`) — **صفوف جديدة فقط، صفر لمس لأي خطة/اشتراك موجود من قبل** (تجنبًا لأي أثر جانبي على تينانتات/جلسات أخرى قد تستخدم نفس الخطط المشتركة). `get_any_active_subscription` بترجع الأحدث (`ORDER BY created_at DESC LIMIT 1`)، فالخطة الجديدة أصبحت هي الفعالة تلقائيًا للتينانتين.

---

## 5) التحقق الحي — النتائج (بالأولوية المتفق عليها)

### 5.1 🔴🔴🔴🔴 `report_death` (#9) — IDOR مؤكَّد حيًا، بلا أي صلاحية مرتفعة

**السيناريو:** User A (`id=772`, `SUPER_ADMIN`، لكن الفحص يكفي `active_user` عادي — الدور هنا غير مؤثر) بتوكنه الحقيقي (تينانت1)، مزوِّرًا `X-Tenant-ID: 16` (تينانت الضحية الحقيقي)، بيستهدف `deceased_id=774` (User B، مستخدم حقيقي، صفر علاقة بالمهاجم):

```
POST /api/digital-twin/death-oracle/report-death
Authorization: Bearer <token A, تينانت1>
X-Tenant-ID: 16
{"reporter_user_id": 774, "evidence_ipfs_hash": "QmATTACK_FAKE_DEATH_HASH_774"}

→ 200 {"status": "DEATH_PENDING", "message": "Death reported, pending confirmation"}
```

**تحقق DB مستقل (SELECT منفصل، صفر اعتماد على status code):**
```sql
SELECT id,user_id,tenant_id,status,official_death_certificate_ipfs FROM death_oracle_checks;
 id | user_id | tenant_id |    status     | official_death_certificate_ipfs
----+---------+-----------+---------------+---------------------------------
  1 |     774 |        16 | DEATH_PENDING | QmATTACK_FAKE_DEATH_HASH_774
```

**حاسم:** صف حقيقي اتكتب في جدول `death_oracle_checks` لمستخدم (774) بمعرفة مهاجم (772) ما بينهم أي علاقة، بمجرد تخمين ID + تزوير هيدر — صفر فحص ملكية/تينانت من أي نوع.

### 5.2 🔴🔴🔴🔴 `confirm_death` (#10) — IDOR مؤكَّد حيًا، "الأخطر تأثيرًا" كما توقَّع `critical-finding-xtenant-systemic.md` بالحرف

**السيناريو (استكمال مباشر لـ5.1، نفس الأوراكل):** User A (سوبريوزر، لكن **من تينانت مختلف تمامًا عن الضحية**)، نفس الهيدر المزوَّر، `confirmers` تعسفية (`[1,2,3]`، صفر تحقق أنهم مستخدمون حقيقيون أو لهم علاقة بالضحية):

```
POST /api/digital-twin/death-oracle/confirm-death/774?confirmers=1&confirmers=2&confirmers=3
Authorization: Bearer <token A, تينانت1>
X-Tenant-ID: 16

→ 200 {"status": "DEATH_CONFIRMED", "release_tx": "LEGACY-RELEASE-6DC45D72F9B342AB"}
```

**تحقق DB مستقل:**
```sql
SELECT id,user_id,tenant_id,status,release_tx_hash FROM death_oracle_checks;
 id | user_id | tenant_id |     status      |         release_tx_hash
----+---------+-----------+-----------------+---------------------------------
  1 |     774 |        16 | DEATH_CONFIRMED | LEGACY-RELEASE-6DC45D72F9B342AB
```

**حاسم:** سوبريوزر من تينانت1 (ما لهوش أي انتماء رسمي لتينانت16) قدر يقلب حالة أوراكل موت حقيقية لمستخدم تينانت16 لـ`DEATH_CONFIRMED` ويولّد `release_tx` — **مطابقة تامة لتحذير `critical-finding-xtenant-systemic.md` الأصلي**. (`_distribute_legacy` الفعلي لسه `pass`/TODO غير مُنفَّذ فعليًا — فصفر تحريك أصول حقيقي حاليًا، لكن قلب حالة الأوراكل نفسه تأثير حقيقي وخطير: أي كود مستقبلي يعتمد على `status=DEATH_CONFIRMED` لتفعيل التوزيع الفعلي سيتفعّل خطأً لضحية حية تمامًا.)

### 5.3 🟡 عيّنة self-scoped — نتيجتان مختلفتان، أدق من التصنيف التحليلي الأولي

اختُبر endpoint واحد **قراءة/إنشاء** (`get_my_twin_config`) وواحد **كتابة قائمة** (`add_life_milestone`)، كلاهما بمزيج (تينانت حقيقي / تينانت مزوَّر) لنفس User A.

**اكتشاف بنيوي جديد أثناء التحقق: بعض الجداول عندها `UNIQUE` عالمي على `user_id` (مش composite مع `tenant_id`):**
```sql
\d digital_twin_configs → "ix_digital_twin_configs_user_id" UNIQUE, btree (user_id)
\d time_capsules        → "ix_time_capsules_user_id" UNIQUE, btree (user_id)
\d digital_wills        → "ix_digital_wills_user_id" UNIQUE, btree (user_id)
\d death_oracle_checks  → "ix_death_oracle_checks_user_id" UNIQUE, btree (user_id)
```
هذا يعني إن أي مستخدم **مايقدرش يكون عنده أكتر من صف واحد إجمالًا في المنصة كلها** لكل من الجداول الأربعة دي (بغض النظر عن التينانت) — عكس الافتراض الأولي في التصنيف التحليلي (§2) اللي فرض إمكانية "سجل شبح" منفصل تحت كل تينانت.

**النتيجة الفعلية المؤكَّدة حيًا لـ`get_my_twin_config`/`update_twin_config` (وبنفس المنطق `time_capsule`/`will`/`death_oracle` self-scoped):**
- أول إنشاء (تينانت حقيقي أو مزوَّر، أيهما أسبق) ينجح عاديًا.
- أي محاولة إنشاء **تانية** (نفس المستخدم، أي تينانت، حقيقي أو مزوَّر) تصطدم بـ`IntegrityError: duplicate key value violates unique constraint "ix_digital_twin_configs_user_id"` → **`500 Internal Server Error`** غير معالَج (مؤكَّد حيًا: `curl`/`Invoke-RestMethod` من User A بهيدر مزوَّر=16 بعد إنشاء ناجح على تينانت1 الحقيقي → `500`).
- **الخلاصة المُحدَّثة:** لا يوجد "تلوث بيانات" فعلي ممكن على الجداول الأربعة دي أصلًا (القيد على مستوى الـDB يمنعه ميكانيكيًا) — أقصى أثر هو **كراش 500 غير نظيف** لو حاول نفس المستخدم يستخدم تينانت مختلف عن تينانت أول سجل له. **هذا باج وظيفي (كراش على تعارض قيد)، ليس IDOR** — بند جانبي منفصل يستحق توثيق Backlog.

**النتيجة الفعلية المؤكَّدة حيًا لـ`add_life_milestone`/`get_my_milestones` (`life_milestones` — بلا `UNIQUE` على `user_id`، فقط على `milestone_nft_id` المولَّد عشوائيًا):**

```
POST /api/digital-twin/milestones  (User A، هيدر مزوَّر X-Tenant-ID: 16)
{"milestone_type":"GRADUATION","title":"TEST_GHOST_MILESTONE_A_UNDER_TENANT16","occurrence_date":"2026-01-01T00:00:00Z"}
→ 201 نجاح كامل

GET /api/digital-twin/milestones (User A، تينانته الحقيقي X-Tenant-ID: 1) → [] (فاضية!)
GET /api/digital-twin/milestones (User A، نفس الهيدر المزوَّر X-Tenant-ID: 16) → [TEST_GHOST_MILESTONE_A_UNDER_TENANT16]
```

**تحقق DB مستقل:**
```sql
SELECT id,user_id,tenant_id,title FROM life_milestones WHERE user_id=772;
 id | user_id | tenant_id |                 title
----+---------+-----------+----------------------------------------
  1 |     772 |        16 | TEST_GHOST_MILESTONE_A_UNDER_TENANT16
```

**مؤكَّد حيًا: تلوث بيانات فعلي — بيانات حقيقية (محطة حياة حقيقية لمستخدم حقيقي) اتسجَّلت بشكل دائم تحت تينانت غلط تمامًا، غير مرئية أصلًا تحت تينانت المستخدم الحقيقي.** **صفر تسريب لبيانات مستخدم آخر** (المطابقة `user_id=current_user.id` سليمة 100%، ده تأكيد إضافي إن الفئة دي مش IDOR كلاسيكي) — لكنها **فجوة سلامة بيانات حقيقية** (tenant misattribution) على الأقل لـ`life_milestones`، وعلى الأرجح `pre_birth_records` كمان (بلا `UNIQUE` على `parent_1_id`/`user_id`، بس على `reserved_sovereign_id` — لم يُختبَر حيًا بعد، نفس المنطق متوقَّع).

### 5.4 🔴🔴🔴🔴 `interact_with_twin` (#3) — قرار تصميمي مستخدم: العزل بين التينانتات **مقصود**؛ الثغرة مؤكَّدة حيًا

**قرار المستخدم [2026-08-24]:** العزل السيادي بين التينانتات في `digital_twin` **مقصود** (التعليقات الصريحة "العزل السيادي" في `repository.py` كافية كدليل نية) — التفاعل مع توأم رقمي يُفترض يبقى محصورًا داخل نفس التينانت، مش سلوك منصة موحّدة عامة. **نفس النمط الميكانيكي المطبَّق على باقي الـ13 endpoint مطلوب هنا كمان.**

**بيانات throwaway إضافية:** مستخدم throwaway ثالث اتفعّل (`773`/`TEST_instr_a`، **تينانت1 حقيقي**، مُعاد استخدامه من جلسات سابقة، بادئة `TEST_` معروفة) — كلمة سره حُدِّثت بنفس الطريقة، ليكون "زائر شرعي حقيقي داخل نفس تينانت المالك" (بعكس `772`/`774` اللي كانا زوج الهجوم المعتاد عبر-التينانت). موثَّق في `.claude/reports/throwaway-test-users.md`.

**السيناريو 1 — مسار شرعي (بلا أي تزوير):** User C (`773`, تينانت1 حقيقي) بتوكنه الحقيقي وهيدر صادق `X-Tenant-ID: 1`، يتفاعل مع توأم User A (`772`, تينانت1 حقيقي، نفس التينانت فعليًا):

```
POST /api/digital-twin/interact/772
Authorization: Bearer <token C, تينانت1 حقيقي>
X-Tenant-ID: 1
{"interaction_type":"TEXT","duration_minutes":1}

→ 201 {"id":2, "twin_config_id":3, "visitor_id":773, "fee_paid_mrusdt":0.0, ...}
```
**نجح كما هو متوقَّع — الميزة الأساسية سليمة.**

**السيناريو 2 — هجوم عبر-تينانت (تزوير الهيدر):** User B (`774`, **تينانت16 حقيقي**) بتوكنه الحقيقي، **مزوِّرًا** `X-Tenant-ID: 1` (ليطابق تينانت المالك، مش تينانته الحقيقي)، يتفاعل مع نفس التوأم:

```
POST /api/digital-twin/interact/772
Authorization: Bearer <token B, تينانت16 حقيقي>
X-Tenant-ID: 1   ← مزوَّر، تينانت B الحقيقي هو 16
{"interaction_type":"TEXT","duration_minutes":1}

→ 201 {"id":3, "twin_config_id":3, "visitor_id":774, "fee_paid_mrusdt":0.0, ...}
```
**نجح أيضًا — بلا أي فحص لتينانت الزائر الحقيقي.**

**تحقق DB مستقل (كلا السطرين):**
```sql
SELECT id,twin_config_id,visitor_id,tenant_id,interaction_type,fee_paid_mrusdt FROM twin_interaction_logs WHERE id IN (2,3);
 id | twin_config_id | visitor_id | tenant_id | interaction_type | fee_paid_mrusdt
----+----------------+------------+-----------+-------------------+-----------------
  2 |              3 |        773 |         1 | TEXT              |      0.00000000
  3 |              3 |        774 |         1 | TEXT              |      0.00000000
```

**حاسم:** السجل رقم 3 يثبت أن مستخدمًا **حقيقيًا من تينانت16** (`774`) تفاعل بنجاح مع توأم مستخدم **تينانت1** بمجرد تزوير الهيدر — تجاوز كامل لحدود "العزل السيادي" المقصود، **بلا أي علاقة حقيقية بين الزائر والمالك أو تينانتيهما**. (رسوم التفاعل هنا `0` — التوأم المستخدَم للاختبار مُهيَّأ برسوم صفرية عمدًا لتفادي أي أثر مالي حقيقي على `finance.transfer` أثناء الفحص؛ رسوم غير صفرية كانت ستُثبت نفس الثغرة + دفعًا ماليًا فعليًا عبر-تينانت، لكن لم يُختبَر بقصد لتفادي المخاطرة على بيانات مستخدمين حقيقيين آخرين موجودين مسبقًا في القاعدة — `twin_config id=1`, رسوم 15 MR_USDT حقيقية، **لم يُلمَس**).

---

## 6) جدول التصنيف النهائي الكامل — 14/14 endpoint + الحل المقترَح

**النمط الميكانيكي الموحَّد (مطابق لـ`academy`/`sovereign_entities`/`ai_agents`/...):** لكل الـ14، حذف `tenant: X = Depends(get_current_tenant)` من التوقيع، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم، إزالة `get_current_tenant`/`AcademyTenant` من الاستيراد لو أصبح غير مُستخدَم. **هذا وحده يكفي لإغلاق 12 من الـ14 — لكن endpoint-ين محتاجين طبقة حماية إضافية فوق التبديل الميكانيكي، موضَّحة تحت.**

| # | الدالة | التصنيف | التبديل الميكانيكي كافٍ؟ | ملاحظة |
|---|---|---|---|---|
| 1 | `get_my_twin_config` | 🟡 self-scoped، صفر IDOR (مؤكَّد حيًا) | ✅ كافٍ | — |
| 2 | `update_twin_config` | 🟡 self-scoped | ✅ كافٍ | — |
| 3 | `interact_with_twin` | 🔴🔴🔴🔴 IDOR — تجاوز عزل سيادي مقصود (مؤكَّد حيًا) | ✅ كافٍ | التبديل وحده يحل المشكلة بالكامل: `tenant_id` هيبقى تينانت الزائر الحقيقي، فلو مختلف عن تينانت `twin_owner_id` هيرجع `404 "غير موجود"` تلقائيًا (نفس `get_twin_config` الحالية) — **صفر كود إضافي مطلوب هنا تحديدًا** |
| 4 | `create_time_capsule` | 🟡 self-scoped | ✅ كافٍ | — |
| 5 | `send_heartbeat` | 🟡 self-scoped | ✅ كافٍ | — |
| 6 | `get_my_time_capsule` | 🟡 self-scoped | ✅ كافٍ | — |
| 7 | `create_digital_will` | 🟡 self-scoped | ✅ كافٍ | — |
| 8 | `get_my_digital_will` | 🟡 self-scoped | ✅ كافٍ | — |
| 9 | `report_death` | 🔴🔴🔴🔴 IDOR (مؤكَّد حيًا) | ⚠️ **غير كافٍ وحده** | راجع "طبقة إضافية" تحت |
| 10 | `confirm_death` | 🔴🔴🔴🔴 IDOR — "الأخطر تأثيرًا" (مؤكَّد حيًا) | ⚠️ **غير كافٍ وحده** | راجع "طبقة إضافية" تحت |
| 11 | `get_my_death_oracle` | 🟡 self-scoped | ✅ كافٍ | — |
| 12 | `add_life_milestone` | 🟠 تلوث بيانات عبر-تينانت (مؤكَّد حيًا) | ✅ كافٍ | التبديل يمنع التلوث بالكامل (تينانت المستخدم الحقيقي دايمًا، مش هيدر) |
| 13 | `get_my_milestones` | 🟡 self-scoped للقراءة | ✅ كافٍ | — |
| 14 | `reserve_pre_birth_identity` | 🟡 تلوث/probing محتمل (لم يُختبَر حيًا، نفس منطق #12) | ✅ كافٍ | — |

### ⚠️ طبقة حماية إضافية مطلوبة لـ`report_death`/`confirm_death` — التبديل الميكانيكي وحده غير كافٍ

بعد التبديل، `tenant_id` هيبقى تينانت **المُبلِّغ/المؤكِّد** الحقيقي (`current_user.tenant_id`) — ده بيقفل تمامًا سيناريو الهجوم المُثبَت حيًا في §5.1/§5.2 (تزوير الهيدر). **لكن `deceased_id` نفسه يفضل قيمة حرة تمامًا** (من جسم الطلب في `report_death`، من الـpath في `confirm_death`) **بلا أي تحقق أن الشخص المُبلَّغ عن وفاته فعلًا عضو في تينانت المُبلِّغ/المؤكِّد**. يعني حتى بعد التبديل، User A (تينانت1) لسه يقدر يستدعي `report_death(deceased_id=774)` — بما إن `tenant_id` بقى `1` (تينانت A الحقيقي، مش هيدر)، هيتكتب صف `DeathOracleCheck(user_id=774, tenant_id=1)` — **نفس فئة تلوث `life_milestones` (§5.3) بالحرف، بس في دومين أخطر بكتير (الموت/الميراث)**، مش IDOR كلاسيكي بعد التبديل (محدش هيقدر يقرا/يأكد بيانات تينانت تاني بتزوير هيدر)، لكنها تسمح بكتابة تعسفية تنسب مستخدمًا حقيقيًا من أي تينانت لسجل موت تحت تينانت مختلف.

**الحل المقترَح (إضافي، فوق التبديل الميكانيكي):** قبل `report_death`/`confirm_death`، إضافة تحقق صريح إن `deceased_id` فعلاً عضو في `tenant_id` (نفس تينانت المُبلِّغ/المؤكِّد) — مثلاً `user_repo.get_by_id(deceased_id, tenant_id)`؛ لو رجع `None`، `raise NotFoundError`. **هذا قرار يحتاج موافقتك الصريحة كجزء من نطاق هذا الإصلاح** (مش مجرد تبديل ميكانيكي بسيط زي باقي الـ12) — البديل هو تطبيق التبديل الميكانيكي فقط الآن وتوثيق فجوة "تلوث بيانات الموت عبر deceased_id حر" كبند Backlog منفصل، زي `life_milestones`/`pre_birth`.

---

## 7) بانتظار موافقتك

**القرار المطلوب:**
1. الموافقة على التصنيف الكامل أعلاه (14/14) + التبديل الميكانيكي الموحَّد لكل الـ14.
2. تحديد نطاق `report_death`/`confirm_death`: **(أ)** تبديل ميكانيكي فقط الآن + توثيق فجوة `deceased_id` الحر كبند Backlog منفصل (نفس معاملة `life_milestones`/`pre_birth`)، أو **(ب)** تبديل ميكانيكي + إضافة فحص عضوية `deceased_id` في نفس تينانت المُبلِّغ ضمن هذا الإصلاح نفسه (يقفل الفجوتين معًا في نفس الجلسة).
3. تأكيد إضافة بند `digital-twin-unique-user-id-crash-on-tenant-mismatch` لـ`PROGRESS_LOG.md` — **✅ تم بالفعل** (بند مضاف، صفر لمس/إصلاح، بطلبك الصريح).

## 7ب) قرار المستخدم [2026-08-24] — موافقة كاملة + نطاق موسَّع لـ`death-oracle`

1. ✅ التصنيف الكامل (14/14) + التبديل الميكانيكي — موافقة كاملة.
2. ✅ **الخيار (ب) لـ`report_death`/`confirm_death`:** فحص عضوية `deceased_id` في نفس `tenant_id` (المُبلِّغ/المؤكِّد) **ضمن هذا الإصلاح نفسه**، مش بند Backlog مؤجَّل — بتوجيه صريح: "الخطورة هنا (سجل موت/ميراث حقيقي) أعلى بكتير من `life_milestones`/`pre_birth`، ومفيش سبب نأجل فحص بسيط زي ده."
3. ✅ بند `digital-twin-unique-user-id-crash-on-tenant-mismatch` مؤكَّد كما هو (مضاف مسبقًا لـ`PROGRESS_LOG.md`، صفر لمس).

## 8) التنفيذ — مكتمل، مؤكَّد حيًا بالكامل

### 8.1 الديف المُطبَّق

**`router.py` (14 endpoint):** لكل واحد — حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من التوقيع، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم، استبدال كل استخدام `cast(int, tenant.id)` بـ`tenant_id`. إزالة `get_current_tenant` من `from app.api.deps import ...` وإزالة `from app.domains.academy.models import AcademyTenant` بالكامل (أصبح غير مُستخدَم).

**`service.py` (تحسين إضافي، endpoint-ين فقط):**
```python
# report_death — أول سطر بالجسم، قبل audit_log
deceased_user = await self._get_user(deceased_id, tenant_id)
if not deceased_user:
    raise NotFoundError("المستخدم المُبلَّغ عن وفاته غير موجود في تينانتك")

# confirm_death — أول سطر بالجسم، قبل get_death_oracle
deceased_user = await self._get_user(deceased_id, tenant_id)
if not deceased_user:
    raise NotFoundError("المستخدم المُراد تأكيد وفاته غير موجود في تينانتك")
```
`_get_user()` كانت موجودة بالفعل في `service.py` (`UserRepository.get_by_id(user_id, tenant_id)` — مفلترة بالتينانت أصلًا) — صفر import جديد.

`python -m py_compile app/domains/digital_twin/router.py app/domains/digital_twin/service.py` → `exit code 0`. `grep "get_current_tenant\|AcademyTenant\|tenant\.id"` على `router.py` → **صفر نتيجة**.

### 8.2 إعادة تشغيل uvicorn — لوج نظيف

إيقاف العملية القديمة (`Stop-Process`)، تشغيل جديد (`Start-Process` منفصل عن جلسة PowerShell — الطريقة الوحيدة اللي عاشت بين استدعاءات الأداة). تأكيد `GET /docs` → `200`، `Application startup complete`، صفر Traceback. تسجيل دخول جديد لكل الثلاثة (A/B/C — التوكنات القديمة انتهت بإعادة تشغيل السيرفر).

### 8.3 التحقق الحي "بعد" — إعادة تنفيذ كل سيناريوهات §5 بالحرف + مسارات شرعية

| # | الاختبار | قبل الإصلاح (§5) | بعد الإصلاح | الحكم |
|---|---|---|---|---|
| 1 | **هجوم** `report_death`: A(تينانت1) ← `deceased_id=774`(تينانت16)، هيدر لم يعد مؤثرًا | `200 DEATH_PENDING` (تسريب) | **`404 {"detail":"المستخدم المُبلَّغ عن وفاته غير موجود في تينانتك"}`** | ✅ **حاسم** |
| 2 | **شرعي** `report_death`: C(773,تينانت1) ← `deceased_id=772`(A، نفس التينانت) | — | `200 DEATH_PENDING` | ✅ **المسار الشرعي سليم** |
| 3 | **هجوم** `confirm_death`: A(سوبريوزر تينانت1) ← `deceased_id=774`(تينانت16) | `200 DEATH_CONFIRMED` + `release_tx` (تسريب "الأخطر تأثيرًا") | **`404 {"detail":"المستخدم المُراد تأكيد وفاته غير موجود في تينانتك"}`** | ✅ **حاسم** |
| 4 | **شرعي** `confirm_death`: A ← `deceased_id=772` (نفس تينانته، `DEATH_PENDING` من #2) | — | `200 DEATH_CONFIRMED` + `release_tx` جديد | ✅ **المسار الشرعي سليم** |
| 5 | **هجوم** `interact_with_twin`: B(تينانت16 حقيقي) ← `owner_id=772`(توأم تينانت1)، هيدر مزوَّر=1 | `201` نجاح (تجاوز عزل سيادي) | **`404 {"detail":"التوأم الرقمي غير موجود أو غير نشط"}`** | ✅ **حاسم** |
| 6 | **شرعي** `interact_with_twin`: C(تينانت1 حقيقي) ← `owner_id=772`(نفس تينانته) | `201` (من §5.4) | `201` (`id=4`) | ✅ **المسار الشرعي سليم** |
| 7 | **تلوث بيانات** `add_life_milestone`: A ← هيدر مزوَّر=16 | `201` مع `tenant_id=16` (تلوث) | **`201` مع `tenant_id=1`** (تينانت A الحقيقي — الهيدر أصبح بلا أي تأثير) | ✅ **حاسم — التلوث مقفول بالكامل** |
| 8 | **ارتداد (regression)** `GET /config`: A، هيدر صادق=1 مقابل مزوَّر=16 | — | **نفس النتيجة بالحرف في الحالتين** (`id=3`, تينانت1) — الهيدر بلا أي تأثير على القراءة | ✅ **سليم، صفر ارتداد** |
| 9 | **ارتداد** `GET /milestones`: A، هيدر صادق=1 | — | يعرض فقط `id=2` (تينانت1 الحقيقي) — **لا يعرض `id=1` (الشبح القديم تحت تينانت16 من قبل الإصلاح)** | ✅ **الفلترة على القراءة سليمة** |

**تحقق DB مستقل (SELECT مباشر، صفر اعتماد على status code) لكل الصفوف الجديدة:**
```sql
SELECT id,user_id,tenant_id,title FROM life_milestones WHERE user_id=772;
 id | user_id | tenant_id |                 title
----+---------+-----------+----------------------------------------
  1 |     772 |        16 | TEST_GHOST_MILESTONE_A_UNDER_TENANT16   -- من قبل الإصلاح، لسه موجود لحد التنظيف
  2 |     772 |         1 | TEST_MILESTONE_A_AFTER_FIX               -- بعد الإصلاح، تينانت صحيح رغم الهيدر المزوَّر

SELECT id,user_id,tenant_id,status FROM death_oracle_checks;
 id | user_id | tenant_id |     status
----+---------+-----------+-----------------
  1 |     774 |        16 | DEATH_CONFIRMED   -- دليل الهجوم قبل الإصلاح، لسه موجود لحد التنظيف
  2 |     772 |         1 | DEATH_CONFIRMED   -- دليل المسار الشرعي بعد الإصلاح، تينانت صحيح

SELECT id,twin_config_id,visitor_id,tenant_id FROM twin_interaction_logs WHERE id=4;
 id | twin_config_id | visitor_id | tenant_id
----+----------------+------------+-----------
  4 |              3 |        773 |         1   -- دليل المسار الشرعي بعد الإصلاح
```

**الخلاصة: كل الخمسة سيناريوهات هجوم (§5.1, §5.2, §5.3-milestone, §5.4×2) فشلت بعد الإصلاح كما هو متوقَّع، وكل المسارات الشرعية (نفس التينانت) نجحت بلا أي ارتداد وظيفي.**

---

## 9) `git status` / `git diff --stat` — للمراجعة قبل أي commit

```
M eppne-backend/app/domains/digital_twin/router.py   (37 إضافة، 30 حذف)
M eppne-backend/app/domains/digital_twin/service.py   (8 إضافات فقط)
```

**باقي الملفات الظاهرة في `git status` الأصلي (متعدّلة/untracked من جلسات سابقة غير متعلقة بهذه الجلسة إطلاقًا)** — `security.py`, `main.py`, `agritech/router.py`, `health/service.py`, `invoicing/router.py`, `tasks/affiliate.py`, `tasks/billing.py`, `tests/conftest.py`, ملفات `eppne-web/*`، وباقي خطط/تقارير `.claude/*` الأخرى — **لم تُلمس، لن تُضاف لأي commit من هذه الجلسة.**

**الملفات الوحيدة المُعدَّلة فعليًا في هذه الجلسة (كود إنتاجي):** `digital_twin/router.py`, `digital_twin/service.py`. + `PROGRESS_LOG.md` (بندان مرجعيان، §مذكور فوق) + ملفا `.claude/reports/` الجديدان (`digital-twin-idor-fix-session-log.md`, `throwaway-test-users.md`).

**الحالة النهائية:** ✅ **الإصلاح الكامل (14 endpoint + فحص عضوية إضافي على 2 منهم) مُطبَّق، مؤكَّد حيًا بالكامل (5 سيناريوهات هجوم مرفوضة الآن + 4 مسارات شرعية/ارتداد سليمة).** ⏳ **لم يُنفَّذ `commit` بعد — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.**

---

## 10) بيانات throwaway — بانتظار قرار التنظيف

جدول §8 (السابق) محدَّث بالصفوف الجديدة من التحقق البعدي:

| الجدول | المعرف | الوصف |
|---|---|---|
| `users.hashed_password` | `772`, `773`, `774` | **يبقى كما هو** (موثَّق مركزيًا بطلب صريح، `throwaway-test-users.md`) |
| `saas_service_plans` | `id=60` | خطة throwaway — **مرشَّحة للحذف** |
| `saas_tenant_subscriptions` | `id=61`, `id=62` | اشتراكات throwaway — **مرشَّحة للحذف** |
| `digital_twin_configs` | `id=3` | **مرشَّح للحذف** |
| `life_milestones` | `id=1` (قبل الإصلاح، تينانت16)، `id=2` (بعد الإصلاح، تينانت1) | **كلاهما مرشَّح للحذف** |
| `death_oracle_checks` | `id=1` (قبل الإصلاح، تينانت16)، `id=2` (بعد الإصلاح، تينانت1) | **كلاهما مرشَّح للحذف** |
| `twin_interaction_logs` | `id=2`, `id=3`, `id=4` | **مرشَّح للحذف** |

**لم يُنفَّذ التنظيف بعد — بانتظار توجيهك (تنظيف الآن مع الـcommit، أم بعده؟).** سيرفر `uvicorn` لسه شغّال (PID جديد في `scratchpad/uvicorn_dtwin.pid`).

---

## 8) بيانات throwaway المُنشأة هذه الجلسة — للتنظيف في النهاية (بعد موافقتك + التحقق البعدي)

| الجدول | المعرف | الوصف |
|---|---|---|
| `users.hashed_password` | `772`, `773`, `774` | تحديث كلمة سر فقط (لا حذف — يبقى موثَّقًا في `throwaway-test-users.md` بطلب صريح) |
| `saas_service_plans` | `id=60` (`TEST_DTWIN_PLAN_CODE`) | خطة throwaway لتفعيل ميزة `digital_twin` |
| `saas_tenant_subscriptions` | `id=61` (تينانت1), `id=62` (تينانت16) | اشتراكات throwaway على الخطة أعلاه |
| `digital_twin_configs` | `id=3` (`user_id=772`, تينانت1) | تلقائي من `get_my_twin_config` |
| `life_milestones` | `id=1` (`user_id=772`, تينانت16 — دليل التلوث) | من اختبار §5.3 |
| `death_oracle_checks` | `id=1` (`user_id=774`, تينانت16، `DEATH_CONFIRMED`) | دليل §5.1/§5.2 |
| `twin_interaction_logs` | `id=2` (شرعي), `id=3` (هجوم) | دليل §5.4 |

سيرفر `uvicorn` التجريبي **لسه شغّال** (PID محفوظ في `scratchpad/uvicorn_dtwin.pid`) — هيتوقف بعد التحقق البعدي على الإصلاح، مش قبله.

**لم يُلمَس أي كود إنتاجي حتى الآن. لم يتم أي `commit`. صفر تنفيذ إصلاح.**
