# جلسة `regression-tests-backfill` — تعليمات البدء

## السياق (خلفية كاملة، لا حاجة للرجوع لأي محادثة سابقة)
مشروع **EPPNE** (Backend FastAPI). كل جلسة إصلاح سابقة اعتمدت في تحققها
الحي على سكريبت مؤقت (`scratchpad/verify_*.py`) يُشغَّل يدويًا ثم يُمسح
بعد التأكيد. لا يوجد حاليًا أي `pytest` دائم يمنع رجوع نفس الأخطاء لو
عدَّل حد نفس الملفات لاحقًا بلا علم بالسياق. هذه الجلسة **لا تصلح أي
باج جديد** — غرضها الوحيد تحويل منطق التحقق المُثبَت فعليًا من 6 جلسات
مغلقة سابقًا إلى ملفات `tests/` دائمة.

## قاعدة صارمة قبل أي حاجة
**هذه الجلسة يجب أن تُنفَّذ قبل بدء المرحلة 1.4 (`redis-client-wrapper-missing-methods`).**
لا تنتقل لأي مهمة تانية غير المذكورة هنا.

## الجلسات الست المطلوب تغطيتها (بالترتيب)

1. **`invitations-savepoint-leak`** (Backlog #11a)
   تقرير: `.claude/reports/invitations-savepoint-leak-session-log.md`
   المنطق المطلوب تحويله: `accept_invitation` — التأكد أن المستخدم
   الناتج **دايمًا** له محفظة (`create_user` بره `begin_nested()`)، وأن
   استدعاء متكرر بنفس `idempotency_key` لا يخلق تكرار (retry-safe).

2. **`realestate-insurance-savepoint-fix`** (Backlog #11b)
   تقرير: `.claude/reports/realestate-insurance-savepoint-fix-session-log.md`
   المنطق: نفس نمط savepoint-commit لكن عبر **8 دوال/4 دومينات**
   (`realestate`×2, `insurance`×2, `tourism_sports`×3, `zamakana`×1) —
   لازم test مستقل لكل دالة من الثمانية، بنفس منطق التحقق الموثَّق
   لكل واحدة في التقرير (مش نسخ/لصق test واحد بتغيير الاسم).

3. **`saas-control-service-get-active-subscription-fix`** (Backlog #9، الإكمال)
   تقرير: `.claude/reports/saas-control-service-fix-session-log.md`
   المنطق: `get_any_active_subscription` + `SaaSControlService.get_active_subscription`
   يرجعوا صح، و`subscription.features` (list-membership عبر `plan.features`)
   يشتغل صح عبر الدومينات الموثَّقة.

4. **`eventbus-redis-wrapper-publish-fix`** (المرحلة 1.1)
   تقرير: `.claude/reports/eventbus-publish-fix-session-log.md`
   المنطق: `RedisClientWrapper.publish()` — subscriber مستقل يستلم فعليًا
   رسالة منشورة عبر EventBus، على الأقل لدومين واحد من الثلاثة
   المُختبَرين حيًا في الجلسة الأصلية (الأفضل: كلهم الثلاثة لو ممكن
   بدون تعقيد زيادة).

5. **`audit-log-signature-fix`** (المرحلة 1.2)
   تقرير: `.claude/reports/audit-log-fix-session-log.md`
   المنطق: `audit_log()` بـ`tenant_id`/`resource_id` **لا يسبب 500 ولا
   rollback صامت** للعملية الأساسية. اختَر 2-3 مواضع تمثيلية من الـ18
   ملف (مش كلهم الـ95 موضع — غطِّ التنوع: endpoint مالي، endpoint إداري،
   endpoint عادي).

6. **`check_and_consume` + `execute_agent_action`** (Backlog #15 و#16)
   تقارير: `.claude/reports/ai-governance-agents-fix-session-log.md`
   و`.claude/reports/ai-agents-execute-action-fix-session-log.md`
   المنطق (جزءان منفصلان، كل واحد test مستقل):
   - `check_and_consume`: نجاح عادي + تراكم صحيح + **رفض فعلي عند
     تجاوز الحصة** (الحالة الحرجة اللي اتحققت حيًا في الجلسة الأصلية).
   - `execute_agent_action`: الـ17 موضع المُصلَحين (اختَر تمثيلي، مش
     الـ17 كلهم بالضرورة). **مهم:** الموضعان المستثنيان عمدًا
     (`realestate:232`, `invitations:415`) **لا يُكتب لهما test نجاح**
     — لسه فيهم خطر transaction موثَّق، أي test هنا المفروض يكون
     `xfail`/`skip` موثَّق بسبب واضح يشير للبند المفتوح
     `ai-agents-execute-action-commit-inside-begin-nested`، مش تجاهله.

## قواعد التنفيذ (نفس منهجية كل الجلسات السابقة)
- **مبني على المنطق المُحقَّق منه فعليًا فقط** — ممنوع إعادة تصميم أو
  "تحسين" أثناء النقل. لو سكريبت التحقق الأصلي فيه ثغرة أو نطاق ناقص،
  وثِّق الملاحظة ولا تصلحها هنا، اقترحها كبند Backlog منفصل.
- كل test بيستخدم بيانات throwaway منفصلة (نفس نمط الجلسات الأصلية)،
  مع تنظيف تلقائي بعد كل test (`fixture` بـ`yield` + cleanup، أو
  `rollback` على transaction مخصصة للاختبار — اختَر النمط اللي متوافق
  مع باقي ملفات `tests/` الموجودة فعلاً في المشروع، افحصها الأول).
- شغّل كل ملف tests جديد فعليًا وتأكد إنه **بيعدي فعلاً** ضد قاعدة
  البيانات الحقيقية (Docker `eppne_db`, بورت 5435) — مش mock/stub.
  لو أي test فشل، ده يعني إما الإصلاح الأصلي مش كامل أو فيه regression
  جديد — **توقف وأبلغ فورًا، لا تُصلح الكود من غير موافقة صريحة** (خارج
  نطاق هذه الجلسة).
- منتظرين ملف واحد لكل جلسة مغطاة (7 ملفات: البند 6 اتنين منفصلين) في
  `tests/`، بأسماء واضحة تربط الملف بالتقرير الأصلي، مثلاً:
  `tests/test_invitations_savepoint_leak.py`,
  `tests/test_realestate_insurance_savepoint.py`, إلخ.
- بعد كل ملف: `pytest <الملف الجديد> -v` فعليًا، وثِّق النتيجة (عدد
  passed، أي skip/xfail وسببه) في `PROGRESS_LOG.md` كإدخال واحد لهذه
  الجلسة (مش سطر لكل ملف).
- **معيار الإغلاق الرسمي لهذه الجلسة تحديدًا:** الـ7 ملفات موجودة،
  اتشغّلوا كلهم مرة واحدة مجمَّعين (`pytest tests/ -k "..."` أو تشغيل
  الملفات السبعة معًا) وصفر فشل غير متوقَّع (skip/xfail الموثَّق مقبول).
- Commit معزول واحد لهذه الجلسة فقط (الملفات السبعة الجديدة +
  PROGRESS_LOG.md)، صفر لمس لأي كود إنتاج.

## خارج النطاق صراحة
- أي إصلاح لباج جديد يظهر أثناء كتابة الاختبارات.
- `technical-pattern-sweep` — دي كانت جلسة جرد قراءة فقط، بلا سكريبت
  تحقق حي واحد يستحق تحويل (نتايجها لسه غير مُصلَحة أصلاً).
- المرحلة 1.4 وأي حاجة بعدها من الخطة العامة.
