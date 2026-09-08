# جلسة: realestate-ai-agent-silent-swallow-investigation

**النطاق:** فحص read-only بحت — صفر تعديل كود. الهدف: تحديد هل الـ
`try/except Exception` الملفوف حوالين `execute_agent_action` في
`realestate/service.py:365-368` تصميم متعمَّد ولا رجعة غير مقصودة.

**خلفية:** هذا السؤال كان مفتوحًا صراحة من جلسة سابقة (انظر §5 تحت) —
"لم يُتحقَّق متى بالضبط اتضاف هذا `try/except` ولا في أي جلسة". هذا
التحقيق يجاوب عليه.

---

## 1) متى وفي أي commit اتضاف الـ`try/except`

`git log -p --follow` + `git blame -L 340,380` على
`eppne-backend/app/domains/realestate/service.py` يحددان بالظبط:

**Commit `650fa5b5f5802d6a1a334809f47dcd864543c4bb`**
Author: 7abeeprog — Date: Tue Sep 1 14:11:38 2026 +0300
Title: `fix(realestate,invitations): move execute_agent_action call outside begin_nested() boundaries`

هذا الـcommit هو نفسه اللي:
- نقل استدعاء `execute_agent_action` من جوّه `async with self.db.begin_nested():`
  إلى بعد `await self.db.commit()` (سبب النقل: `execute_agent_action`
  بتعمل `commit()` مستقل جوّاها، ونداؤها من جوّه `begin_nested()` كان
  بيكسر الـSAVEPOINT — `InvalidRequestError: Can't operate on closed
  transaction inside context manager`، وده الشق التاني من Backlog #16:
  `ai-agents-execute-action-commit-inside-begin-nested`).
- **وفي نفس الخطوة**، لفّ الاستدعاء بـ`try/except Exception` مع
  `logger.error(...)` فقط، بلا `raise`.

نص رسالة الـcommit (الجزء الخاص بالموضع ده حرفيًا):

> `realestate.buy_fractional_ownership: execute_agent_action() call moved to after the main commit(), same place/pattern as the adjacent invoicing.create_invoice() call, wrapped in try/except (its result was already unused).`

يعني الـcommit message نفسه بيوثّق **سببين** واضحين للف بـtry/except:
1. **نمط مُقلَّد عمدًا** من `invoicing.create_invoice()` المجاورة له
   مباشرة (نفس الدالة، نفس البنية `try/except Exception` +
   `logger.error` بلا `raise`) — الاستدعاء ده كان مضاف قبلها بأسبوعين
   تقريبًا في commit `4edce05a` (18 أغسطس) بنفس الشكل بالظبط.
2. **نتيجة الاستدعاء غير مستخدمة أصلًا** (`await
   ai.execute_agent_action(...)` بدون `ai_result = `) — بعكس مواضع
   تانية في المشروع بتستخدم النتيجة فعليًا (قسم 3).

الـcommit التالي مباشرة `c5f343f4` (نفس اليوم، 14:45:32) عدّل فقط
التعليق الشارح فوق الكود (ليشمل `_check_ai_governance` كمان) ولم يمسّ
بنية الـ`try/except` نفسها.

**قبل `650fa5b`**: الاستدعاء كان جوّه `begin_nested()` بلا أي
`try/except` إطلاقًا (انظر الـdiff في commit `a113ae5`، 26 أغسطس —
كان مجرد `await ai.execute_agent_action(...)` عاري تمامًا، فشله كان
هيكسر الـsavepoint ويسقط الدالة كلها بـ`InvalidRequestError` غير
معالَج). فالـ`try/except` مش حاجة قديمة من التصميم الأصلي — اتضافت
حصريًا كجزء من إصلاح مشكلة الـtransaction، مش كقرار مستقل بخصوص سياسة
معالجة أخطاء الـAI.

---

## 2) الكود الكامل لـ`buy_fractional_ownership` — هل فيه تعليق يوضّح النية؟

اطّلعت على الدالة كاملة (`realestate/service.py:253-396`). النتيجة:

- **يوجد تعليق فوق الكتلة كلها** (سطور 356-362)، لكنه **يشرح فقط
  لماذا الاستدعاء اتنقل لبعد الـ`commit()`** (تعارض
  `begin_nested()`/`commit()` الداخلي)، **مش ليه بيتلبَّس بـ
  `try/except` وبيتبلع صامت**:

  ```
  # ========================================
  # فحص/استهلاك حوكمة الذكاء الاصطناعي + استدعاء الوكيل الذكي (بعد commit()
  # الرئيسي عمدًا — كلاهما تنفّذ commit() مستقل داخلها؛ نداؤهما من جوّه
  # begin_nested() أعلاه كان يكسر الـSAVEPOINT. راجع
  # .claude/reports/backlog-16-begin-nested-commit-session-log.md و
  # .claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md)
  # ========================================
  await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)

  try:
      await ai.execute_agent_action(agent_id=2, action_type="ANALYZE_PROJECT", payload={...}, executor_user_id=buyer_id, idempotency_key=f"...")
  except Exception as e:
      logger.error(f"AI analysis failed for fractional ownership purchase (unit {unit_id}): {e}")
  ```

- **لا يوجد أي تعليق** (لا inline ولا فوق الكتلة) يوضّح صراحة نية زي
  "AI تحليل اختياري، مش حرج للعملية" أو "فشل التحليل مقبول ومش لازم
  يوقف الشراء". التبرير الوحيد الموجود فعليًا هو داخل **رسالة
  الـcommit** (قسم 1 أعلاه: "نتيجته غير مستخدمة" + "نفس نمط
  `invoicing.create_invoice` المجاورة") — مش داخل الكود نفسه ولا في
  تقرير مرجعي مخصص لقرار الـ`except`.
- بالمقارنة: كتلة `invoicing.create_invoice` المجاورة مباشرة (سطور
  370-379) نفس البنية بالظبط (`try/except Exception` +
  `logger.error` بلا `raise`)، وبنفس غياب أي تعليق يبرر الابتلاع.

**الخلاصة الجزئية:** فيه نية موثَّقة (في الـcommit message، مش في
الكود) إن الابتلاع **مقصود بالنسبة لكون النتيجة غير مستخدمة**، لكن
مفيش أي تحليل موثَّق وقت الإضافة لسؤال "هل الفشل هنا ممكن يكون خطأ
برمجي حقيقي يستاهل يظهر؟" — القرار اتاخد بمعيار "النتيجة مش
مستخدمة" فقط، مش بمعيار "نوع الفشل المحتمل" (قسم 4).

---

## 3) هل باقي الدومينات بتلف نفس النمط؟ (نمط مشروع-عام ولا استثناء realestate)

`grep -rn "execute_agent_action"` عبر `eppne-backend/app` رجّعت 17
ملف. بالتصنيف حسب هل الاستدعاء ملفوف بـ`try/except` وهل النتيجة
مستخدمة بعدها:

| الموضع | `try/except`؟ | النتيجة مستخدمة بعد الـ`except`؟ | سلوك الـ`except` |
|---|---|---|---|
| `realestate.buy_fractional_ownership:365-368` | ✅ | ❌ (النتيجة أصلًا مش متخزنة في متغير) | `logger.error` فقط، بلا `raise`، بلا fallback |
| `invitations._analyze_target_user:85-` | ✅ | (فحص لم يُعمَّق — خارج نطاق السطور المطلوبة) | — |
| `invitations.chat_with_ai:411` | ❌ **لا يوجد try/except** | ✅ `reply_text` بيُستخدم مباشرة في الرد للعميل | أي استثناء هنا **يتصعّد (`raise`) طبيعيًا** لأعلى، عمدًا (رسالة commit `650fa5b`: "its reply_text is actually used") |
| `employment._calculate_ai_match_score:132-153` | ✅ | ✅ (`result.get(...)`) | `except` بيرجّع **fallback قيمة افتراضية** (`Decimal(50.0)`) بدل تمرير صمت فارغ |
| `zamakana` (~521) | ✅ | ✅ (`ai_result.get(...)` بعد الـtry مباشرة، مع fallback `dict` افتراضي داخل `.get`) | نفس نمط fallback |
| `tourism_sports` (297, 464) | ✅ (٢ موضع) | جزئي | — |
| `tenders_auctions` (247, 397) | ✅ (٢ موضع) | ✅ | — |
| `manufacturing` (312, 674) | ✅ (٢ موضع) | ✅ | — |
| `logistics` (557) | ✅ | ✅ | — |
| `insurance` (369, 477) | ✅ (٢ موضع) | ✅ | — |
| `social` (338) | ✅ | ✅ | — |
| `command` (354) | ✅ | ✅ | — |
| `automation` (707) | ✅ | ✅ | — |
| `arbitration_syndicates` (104) | ✅ | ✅ | — |
| `transport` (240) | ✅ | ✅ | — |
| `tasks/agritech.py` (168) | ✅ | ✅ | — |

**النتيجة:** لف الاستدعاء بـ`try/except Exception` هو **النمط
السائد فعلاً عبر كل الدومينات تقريبًا** (16 من 17 موضع استدعاء
فعلي) — realestate **مش استثناء منفرد** في مجرد وجود الـ`try/except`.

لكن فيه **فرق جوهري واحد** يميّز realestate عن كل المواضع التانية
اللي فحصتها واستخدمت النتيجة: في كل موضع تاني، الـ`except` إما (أ)
بيرجّع **fallback قيمة بديلة** يُستخدم مكان نتيجة الـAI الفاشلة
(`employment`: `Decimal(50.0)`, `zamakana`: قاموس افتراضي ثابت)، أو
(ب) الاستدعاء نفسه **بلا try/except إطلاقًا** لما النتيجة حرجة فعليًا
(`invitations.chat_with_ai`). realestate هي الحالة الوحيدة اللي فيها
النتيجة **غير مستخدمة من الأساس** (`await` بدون تخزين)، فالـ`except`
مجرد "بلع واستمرار" بلا أي بديل يُستخدم — وده يطابق نمط
`invoicing.create_invoice` المجاورة لها بالظبط (نفس الدالة)، مش نمط
باقي الدومينات اللي بتعتمد فعليًا على نتيجة الـAI.

**الخلاصة:** النمط "استدعاء AI + `try/except Exception` +
`logger.error` بلا `raise`" **متعمَّد ومنتشر عبر المشروع** كسياسة
عامة "فشل الـAI مش لازم يكسر العملية الأساسية". لكن تفصيلة "الابتلاع
الكامل بلا fallback ولا استخدام للنتيجة" خاصة بـrealestate (ومثيلتها
invoicing المجاورة) بسبب طبيعة الاستدعاء نفسه (تحليل "جانبي" مش
مُدخل في منطق العملية) — مش لأنها نُسيت أو اتضافت باستعجال.

---

## 4) `AIAgentsService.execute_agent_action` — طبيعة الفشل المحتمل

من قراءة `ai_agents/service.py:147-` كاملة، الاستثناءات المحتملة
تنقسم فعليًا لفئتين مختلفتين تمامًا، والـ`except Exception` الحالي
في realestate **بيبلعهم بنفس الطريقة من غير أي تمييز**:

**(أ) فشل "متوقَّع وسليم" (business/domain errors)** — بيتصعّدوا
**قبل** كتلة الـ`try` الداخلية، من التحقق الأولي:
- `NotFoundError(f"الوكيل {agent_id} غير موجود")` — لو الـagent
  مش موجود في الـDB (سطر ~161). هذا **حدث فعليًا وموثَّق حي** في
  PROGRESS_LOG.md (بند `ai-agent-id-2-missing-seed-masks-execute-action-old-bug`،
  2026-08-31): بعد إصلاح باج تاني، الكود فعليًا وصل لنداء
  `execute_agent_action(agent_id=2, ...)` من `realestate` واصطدم
  بـ`NotFoundError("وكيل 2 غير موجود")` لأن الـagent id=2 غير موجود
  في بيانات الـdev DB الحالية.
- `PermissionDeniedError(f"الوكيل {agent_id} غير نشط")` — لو الـagent
  موجود لكن حالته مش `ACTIVE`.

**(ب) فشل "خطأ برمجي حقيقي"** — بيحصل جوّه كتلة الـ`try` الداخلية
(سطور ~172-206: `create_task_log`, `ai_engine.generate(...)`,
`update_task_log_cost`)، وأي استثناء هنا بيتلقفه الـ`except` الداخلي
بتاع `execute_agent_action` نفسها (بيعمل `task_log` بحالة `"ERROR"`،
`commit()`، وبعدين **`raise`** — أي بيصعّد الاستثناء الأصلي زي ما هو
لأعلى للـcaller). المثال الموثَّق تاريخيًا لنفس الفئة: **باج
Backlog #16 الأصلي نفسه** — `TypeError` ناتج من تمرير معامل
`tenant_id=` زايد على توقيع `execute_agent_action` (اتصلح لاحقًا في
19 موضع استدعاء، commit 18 أغسطس)، وهو بالضبط نوع "خطأ برمجي" ولا
علاقة له بتوفّر الـagent أو حالته.

**المشكلة المؤكَّدة:** الـ`try/except Exception` في
`realestate/service.py:365-368` بيمسك **كل** حاجة — `NotFoundError`،
`PermissionDeniedError`، `TypeError`، `AttributeError`، أي
`SQLAlchemyError` من `create_task_log`/`update_task_log_cost` — بنفس
سطر `logger.error(...)` وبدون أي تمييز. بالتحديد:

- لو `agent_id=2` مش موجود في بيئة (dev/staging/إنتاج) — كما حصل
  فعليًا وموثَّق أعلاه — العملية المالية (`finance.transfer` + إنشاء
  `PropertyOwnership`) بتكمل وتنجح **100%**، والمستخدم ولا أي مراقب
  خارجي بياخد أي إشارة إن "تحليل الـAI" اتبلع بصمت لأن الـagent كله
  مش موجود — ده مختلف جوهريًا عن "تحليل فشل مؤقتًا"، وهو تحديدًا نوع
  الفشل اللي مفروض يوصل لمراقبة/alerting، مش `logger.error` داخلي بس.
- لو حصل رجوع لباج مشابه لـ#16 (تغيير مستقبلي في توقيع
  `execute_agent_action` مثلاً)، الـ`except` الحالي هيبلعه **بصمت
  كامل** بنفس الطريقة، وهيكون أصعب في الاكتشاف من قبل النقل (لما كان
  الاستدعاء عاري بلا `try/except` وكان بيكسر الدالة كلها بشكل واضح).

هذه النقطة **موثَّقة مسبقًا كسؤال مفتوح صريح** في
`PROGRESS_LOG.md:2415-2421` (جلسة `plan-features-tests-fix-*`،
2026‑09‑02 تقريبًا)، حرفيًا: *"القرار المطلوب صراحةً: هل ابتلاع بج
#16 صمتًا هنا **سلوك مقصود**... أم **رجعة غير مقصودة**... لم يُتحقَّق
متى بالضبط اتضاف هذا `try/except` ولا في أي جلسة — خارج نطاق هذا
التحقيق"*. هذا التحقيق الحالي يسدّ بالظبط الفجوة دي (قسم 1).

---

## 5) الخلاصة النهائية

- **التوقيت والسبب المباشر للإضافة موثَّقان بدقة الآن**: commit
  `650fa5b5` (1 سبتمبر 2026، 14:11:38)، كجزء من إصلاح تعارض
  `begin_nested()`/`commit()` الداخلي بتاع `execute_agent_action`
  (Backlog #16 شق ب)، بنمط مقلَّد حرفيًا من `invoicing.create_invoice`
  المجاورة، بمبرر موثَّق في رسالة الـcommit فقط ("نتيجته غير مستخدمة
  أصلًا") — مش في تعليق داخل الكود ومش في تقرير مخصص.
- **مش استثناء معماري لـrealestate وحدها** — نفس نمط "AI استدعاء +
  `try/except Exception` + `logger.error` بلا `raise`" موجود في 16
  من أصل 17 موضع استدعاء `execute_agent_action` عبر المشروع، فهو
  سياسة عامة متعمَّدة ("فشل الـAI الجانبي مش لازم يوقف العملية
  الأساسية").
- **لكن التصميم عنده فجوة حقيقية غير مُعالَجة صراحةً وقت اتخاذ
  القرار**: الابتلاع بلا تمييز بين فشل متوقَّع (`NotFoundError`/
  `PermissionDeniedError` — agent غير موجود/غير نشط) وفشل برمجي حقيقي
  (زي باج #16 الأصلي، `TypeError`)، وهذه الفجوة **تحققت فعليًا حيًا**
  (agent id=2 غير موجود في dev DB أدّى لـ`NotFoundError` تُبتلع بنفس
  الطريقة). القرار اتاخد بمعيار "النتيجة مش مستخدمة" فقط، بدون تحليل
  موازٍ لأنواع الفشل الممكنة — فهو **قرار متعمَّد جزئيًا** (اللف نفسه
  مقصود ومطابق للنمط العام) **لكن نطاقه (بلع كل شيء بلا تمييز ولا
  مراقبة خارجية) لم يكن قرارًا مدروسًا صراحة وقت الإضافة** — وهي بالضبط
  النقطة اللي تركتها الجلسة السابقة مفتوحة وطلبت قرار مستخدم بشأنها.

**لم يتم أي تعديل على الكود في هذا التحقيق.**
