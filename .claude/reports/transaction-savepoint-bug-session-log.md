# تقرير جلسة — باج commit() جوه begin_nested() (نمط منهجي عبر المشروع)

**بدأ التسجيل:** 2026-08-12
**الحالة العامة وقت بدء التسجيل:** جلسة منفصلة تمامًا عن Phase 16 (مرجع: `.claude/reports/phase16-session-log.md`، اللي هو المصدر الحاكم لأي قرار سابق موثَّق فيه — أي حاجة موثَّقة هناك كقرار متخذ = نهائية). الجلسة دي مخصصة لباج ترانزاكشن منهجي اكتُشف أثناء الفحص الاستباقي في آخر 3 أقسام من تقرير Phase 16.

---

## الخلفية (من تقرير Phase 16، ملخّص)

عدة repository methods عبر المشروع بتعمل `self.db.commit()` مباشر وهي متنادية من جوه `async with self.db.begin_nested()` في service تاني — ده بيقفل الترانزاكشن اللي الـSAVEPOINT معتمد عليه، وبيكسر أي عملية بعده في نفس البلوك (`InvalidRequestError: Can't operate on closed transaction inside context manager`، أو تسريب صامت لو الاستثناء اتبلع جوه `except Exception`).

**اكتشاف Phase 16 الأصلي:** `ai_governance/repository.py` `create_usage_log` كانت بتعمل `commit()` جوه `begin_nested()` بتاعة `check_and_consume`. **اتصلح** (سطر واحد، `commit()` → `flush()`)، بموافقة كاستثناء نطاق مبرَّر وقتها.

**الفحص الاستباقي اللي تبع كده** (آخر أقسام تقرير Phase 16) لقى نفس النمط في 6 مواضع تانية عبر `ai_agents`, `sovereign_entities`, `saas` — وبعدين اكتشاف أعمق إن `finance/service.py` (`transfer`) عندها نفس الباج **جوه نفسها**، مستقلة تمامًا عن أي `begin_nested()` خارجي. الخلاصة وقتها: **ده مش باج معزول، ده نمط منهجي عبر طبقة الـrepository بالكامل تقريبًا** — النطاق أكبر بكتير من إصلاح `ai_governance` المصغَّر، ومحتاج جلسة منفصلة.

**القاعدة الموحّدة للإصلاح (نهائية، متفق عليها):** الـrepository ما تعملش `commit()` — بس `flush()`. الـservice (أو نقطة `begin_nested()` نفسها) هي اللي بتتحكم في حدود الترانزاكشن. القاعدة دي تتطبق فقط على الأماكن اللي فيها فعليًا `begin_nested()` ملفوف حواليها (المؤكَّدة من الجرد)، مش على كل repo method في المشروع.

---

## [2026-08-12] سؤال البداية — هل `finance.transfer()` مسار إنتاج حقيقي؟

**السؤال:** `finance.transfer()` (`finance/service.py:58-147`) — مسار إنتاج حقيقي مستخدَم فعليًا، ولا دين تقني معزول؟ لو أيوه، مين بيستدعيه (كل الـcaller sites)؟

**التأكيد (قراءة كود مباشرة):** الباج لسه حي 100%. `transfer()` بتفتح `begin_nested()` في `finance/service.py:92`، وجواها بتنادي:
- `self.wallet_repo.update_balances(...)` (مرتين، سطور 115-116) → `finance/repository.py:48-57`، فيها `self.db.commit()` **سطر 52**.
- `self.tx_repo.create(...)` (سطر 119) → `finance/repository.py:74-79`، فيها `self.db.commit()` **سطر 77**.
- (كمان `get_or_create_wallet_for_update` ممكن تنادي `WalletRepository.create` → `finance/repository.py:34-46`، `commit()` **سطر 44**.)

**الإجابة: `finance.transfer()` قناة إنتاج حقيقية ومركزية — مش دين تقني.** 33 موضع استدعاء عبر 24 دومين/ملف:

| الفئة | المواضع |
|---|---|
| Background tasks | `tasks/employment.py:311`, `tasks/billing.py:349` |
| Endpoint مباشر | `finance/router.py:49` |
| Domain services (`self.finance.transfer`) | `transport`(×2), `digital_twin`, `tourism_sports`(×2), `tenders_auctions`, `commerce`(×3), `sovereign_entities`(×2), `social`(×3), `service_marketplace`(×3), `saas`(×2), `realestate`, `arbitration_syndicates`, `projects`, `affiliate`, `iot`, `academy`, `invoicing`, `invitations`, `insurance`(×4), `health` |

**التصنيف: مسار حرج، مش دين تقني.** أي endpoint من الـ33 دول بيفشل حاليًا وقت التنفيذ الفعلي (كل استدعاء لـ`transfer()` هينهار — `InvalidRequestError` بعد أول `commit()`، أو نتيجة ناقصة صامتة لو الاستثناء اتبلع).

**الحالة:** ✅ اتجاب.

---

## [2026-08-12] المرحلة 1 — الجرد الشامل (read-only بالكامل)

**الطلب:** `grep` على المشروع كله (مش بس الأربعة دومينات) لكل استخدام لـ`begin_nested()`، ولكل واحدة: هل فيها أي repo method بتتنادى جواها بتعمل `commit()` مباشر؟

**المنهجية:** `grep -rn "begin_nested(" app/domains app/tasks` (97 نتيجة، صفر في `app/tasks`). لكل موضع: قراءة الـmethod كاملة من `async with self.db.begin_nested():` لحد نهاية البلوك، استخراج كل استدعاء repo/service جواها، وقراءة تعريف كل واحدة من ملفها المصدر (مش افتراض) للتأكد هل فيها `self.db.commit()`. تحقق يدوي إضافي على عيّنة (`commerce/service.py:484`, `invitations/service.py:203`) طابق التقرير بالحرف.

### النتيجة الإجمالية

**97 موضع `begin_nested()` عبر 27 ملف. 89 Buggy، 8 نظيفين (Clean)، 1 مصلَّح جزئيًا مسبقًا (Phase 16).**

**النظيفين (repo بتاعتهم بترجع بلا `commit()` إطلاقًا):**
- `iot/service.py`: 62, 82, 95, 126, 255, 260 (6 مواضع)
- `translation/service.py`: 162, 191 (2 مواضع)

**آلية الانتشار الأخطر:** أي service بينادي `self.finance.transfer(...)` جوه `begin_nested()` بتاعته بيورّث باج `finance/repository.py` تلقائيًا (لأن `transfer()` نفسها فيها `begin_nested()` تانية جواها). ده بيأثر على 18 موضع استدعاء إضافي: `academy`, `commerce`, `digital_twin`, `insurance`(×2), `iot`, `realestate`, `saas`(×2), `service_marketplace`(×2), `social`(×3), `sovereign_entities`(×2), `tourism_sports`(×2), `transport`(×2). **يعني تصليح `finance/repository.py` نفسها هيحل جزء كبير من الانتشار تلقائيًا.**

### الجدول الكامل — 89 موضع Buggy (بالدومين، مع الـrepo method والـcommit line)

**academy/service.py**
- `254` (`enroll_in_course`) — `self.finance.transfer` (وارث)؛ `repo.enroll` (`academy/repository.py:454`, commit `:457`)؛ `affiliate_service.track_referral`→`update_affiliate_profile` (`affiliate/repository.py:61`, commit `:67`) + `create_referral_tree` (commit `:131`)

**affiliate/service.py**
- `474` (`withdraw_commissions`) — `self.finance.transfer` (وارث)؛ `repo.update_commission_status` (`affiliate/repository.py:201`, commit `:207`)
- `618` (`bulk_release_commissions`) — `repo.bulk_update_commission_status` (`affiliate/repository.py:213`, commit `:230`)

**agritech/service.py**
- `251` (`register_harvest`) — `repo.create_harvest` (`agritech/repository.py:120`, commit `:123`)
- `370` (`register_bio_yield`) — `repo.create_bio_yield` (`agritech/repository.py:146`, commit `:149`)

**ai_agents/service.py**
- `289` (`resolve_approval`) — `repo.resolve_approval` (`ai_agents/repository.py:181`, commit `:197`)

**ai_governance/service.py**
- `33` (`set_quota`) — `repo.create_or_update_quota` (`repository.py:20`, commit `:35`)؛ `repo.create_audit_log` (commit `:142`)
- `66` (`update_rate_limits`) — `repo.update_rate_limits` (`repository.py:108`, commit `:123`)؛ `repo.create_audit_log` (commit `:142`)
- `155` (`check_and_consume`) — `repo.create_or_update_quota` (commit `:35`) — لسه Buggy جزئيًا؛ `repo.create_usage_log` **مصلَّحة من Phase 16** (`flush()` سطر 62، مش commit)
- `205` (`reset_quotas`) — `repo.reset_quota_usage` (`repository.py:50`, commit `:56`)؛ `repo.create_audit_log` (commit `:142`)

**commerce/service.py**
- `135` (`checkout`) — `self.finance.transfer` (وارث)
- `475` (`_restore_inventory`) — **`await self.db.commit()` مباشر داخل البلوك، سطر 484** (مؤكَّد يدويًا)

**communications/service.py**
- `68` (`send_notification`) — `repo.create_notification` (`repository.py:25`, commit `:28`)
- `148` (`send_mail`) — `repo.create_thread` (commit `:120`)؛ `repo.create_message` (commit `:131`)؛ `repo.add_to_mailbox` ×2 (commit `:148`)؛ `repo.add_attachment` في loop (commit `:221`)

**digital_twin/service.py**
- `112` (`get_or_create_twin`) — `repo.create_twin_config` (`repository.py:30`, commit `:34`)
- `170` (`interact_with_twin`) — `self.finance.transfer` (وارث)
- `234` (`setup_time_capsule`) — `repo.create_time_capsule` (commit `:88`)؛ `repo.create_beneficiary` في loop (commit `:120`)

**employment/service.py**
- `316` (`create_contract`) — `repo.create_contract` (`employment/repository.py:161`, commit `:164`)

**finance/service.py** (أصل الباج)
- `92` (`transfer`) — `wallet_repo` → `WalletRepository.create` (commit `:44`) ×2؛ `update_balances` (commit `:52`) ×2؛ `tx_repo.create` (commit `:77`)
- `183` (`swap`) — نفس نمط `wallet_repo`/`tx_repo` (commit `:44`/`:52`/`:77`)
- `272` (`mint_currency`) — `update_balances` (commit `:52`)؛ **`await self.db.commit()` مباشر سطر 281**؛ `tx_repo.create` (commit `:77`)

**health/service.py**
- `83` (`get_or_create_profile`) — `repo.create_medical_profile` (`repository.py:38`, commit `:41`)
- `97` (`update_profile`) — `repo.update_medical_profile` (commit `:51`)
- `109` (`process_biometric_data`) — `repo.create_biometric_log` (commit `:59`)؛ `repo.update_medical_profile` (commit `:51`)؛ `repo.create_prognosis` (commit `:73`)
- `236` (`book_appointment`) — `repo.create_appointment` (commit `:88`)
- `282` (`create_consultation`) — `repo.create_consultation` (commit `:112`)
- `292` (`create_prescription`) — `repo.create_prescription` (commit `:124`)
- `331` (`trigger_emergency`) — `repo.create_dispatch` (commit `:132`)
- `372` (`create_facility`) — `repo.create_facility` (commit `:17`)

**insurance/service.py**
- `124` (`create_policy`) — `repo.create_policy` (`repository.py:26`, commit `:29`)
- `193` (`subscribe`) — `self.finance.transfer` (وارث)؛ `invoicing_service.create_invoice` (`invoicing/repository.py:22`, commit `:25`)؛ `repo.create_subscription` (commit `:71`)
- `353` (`submit_claim`) — `repo.create_claim` (commit `:110`)
- `442` (`review_claim`) — `self.finance.transfer` (وارث)؛ `invoicing_service.create_invoice` (commit)؛ `repo.update_claim` (commit `:134`)
- `507` (`create_pension`) — `repo.create_pension` (commit `:145`)
- `550` (`create_employee_insurance_profile`) — `repo.create_employee_profile` (commit `:173`)

**invitations/service.py**
- `190` (`create_invitation`) — `repo.create_invitation` (`repository.py:24`, commit `:27`)؛ **`await self.db.commit()` مباشر سطر 203** (مؤكَّد يدويًا، شرطي)
- `286` (`accept_invitation`) — `repo.create_lead` (commit `:149`)؛ `repo.update_invitation` (commit `:68`)؛ `repo.create_interaction` (commit `:211`)
- `390` (`chat_with_ai`) — `repo.create_conversation` ×2 (commit `:113`)؛ `repo.create_interaction` (commit `:211`)
- `484` (`create_lead`) — `repo.create_lead` (commit `:149`)
- `569` (`create_interaction`) — `repo.create_interaction` (commit `:211`)
- `652` (`create_campaign`) — `repo.create_campaign` (commit `:231`)
- `757` (`create_ticket`) — `repo.create_ticket` (commit `:291`)
- `849` (`add_ticket_comment`) — `repo.create_ticket_comment` (commit `:341`)؛ `repo.update_ticket_status` (commit `:335`)
- `929` (`track_behavior`) — `repo.create_tracking` (commit `:97`)

**logistics/service.py**
- `96` (`create_warehouse`) — `repo.create_warehouse` (`repository.py:24`, commit `:27`)
- `161` (`create_warehouse_zone`) — `repo.create_zone` (commit `:97`)
- `201` (`receive_inventory`) — `repo.create_inventory_item` (commit `:138`)؛ `repo.update_warehouse_usage` (commit `:78`)؛ `repo.create_transaction` (commit `:231`)
- `288` (`issue_inventory`) — `repo.update_inventory_item` (commit `:192`)؛ `repo.update_warehouse_usage` (commit `:78`)؛ `repo.create_transaction` (commit `:231`)
- `363` (`adjust_inventory`) — نفس أعلاه + `update_warehouse_usage` شرطي
- `440` (`create_equipment`) — `repo.create_equipment` (commit `:302`)
- `499` (`create_equipment_maintenance`) — `repo.create_maintenance` (commit `:363`)
- `575` (`generate_forecast`) — `repo.create_forecast` (commit `:489`)

**manufacturing/service.py**
- `105` (`create_facility`) — `repo.create_facility` (`repository.py:19`, commit `:22`)
- `160` (`add_production_line`) — `repo.create_production_line` (commit `:52`)
- `195` (`create_blueprint`) — `repo.create_blueprint` (commit `:74`)
- `244` (`create_batch`) — `repo.create_batch` (commit `:94`)
- `328` (`start_production`) — `repo.bulk_create_items` (commit `:131`)؛ `repo.update_batch_status` (commit `:122`)
- `400` (`register_raw_material_batch`) — `repo.create_raw_material_batch` (commit `:165`)
- `493` (`consume_raw_material`) — `repo.consume_material` (commit `:196`)
- `552` (`create_digital_twin`) — `repo.create_digital_twin` (commit `:207`)
- `594` (`issue_quality_certificate`) — `repo.create_quality_certificate` (commit `:246`)
- `672` (`analyze_and_schedule_maintenance`) — `repo.create_predictive_log` (commit `:268`)؛ `repo.schedule_maintenance` (commit `:291`, شرطي)
- `731` (`create_spare_part`) — `repo.create_spare_part` (commit `:302`)
- `769` (`restock_spare_part`) — `repo.update_spare_part_stock` (commit `:331`)

**privacy/service.py**
- `139` (`process_erasure_request`) — `repo.update_erasure_request` (`repository.py:186`, commit `:196`)

**projects/service.py**
- `253` (`approve_contribution`) — `repo.update_project` (`repository.py:46`, commit `:53`, شرطي)؛ `repo.update_contribution` (commit `:139`)
- `314` (`complete_milestone`) — `repo.update_milestone` (`repository.py:218`, commit `:228`)

**realestate/service.py**
- `213` (`buy_fractional_ownership`) — `self.ai.execute_agent_action`→`create_task_log` (commit `:240`)؛ `self.finance.transfer` (وارث)؛ `self.invoicing.create_invoice` (commit)؛ `repo.create_ownership` (commit `:96`)؛ `repo.update_unit_availability` (commit `:89`)
- `358` (`rent_unit`) — `repo.create_rental_contract` (`repository.py:115`, commit `:118`)؛ `self.invoicing.create_invoice` (commit)

**saas/service.py**
- `109` (`create_subscription`) — `repo.create_subscription` (`repository.py:180`, commit `:183`)؛ `repo.create_service_access` (commit `:263`, شرطي)
- `159` (`process_auto_renewals`) — `self.finance.transfer` (وارث)؛ `repo.update_subscription` (commit `:198`)؛ `repo.create_invoice` (commit `:339`)
- `296` (`pay_invoice`) — `self.finance.transfer` (وارث)؛ `repo.update_invoice` (commit `:349`)؛ `repo.update_subscription` (commit `:198`, شرطي)

**service_marketplace/service.py**
- `221` (`purchase_service`) — `repo.create_license` (`repository.py:121`, commit `:125`)
- `346` (`renew_subscription`) — `self.finance.transfer` (وارث)؛ `repo.update_license` (commit `:182`)
- `387` (`purchase_addon`) — `self.finance.transfer` (وارث)؛ `repo.update_license` (commit `:182`)؛ `repo.create_addon_purchase` (commit `:318`)

**social/service.py**
- `490` (`send_digital_gift`) — `self.finance.transfer` (وارث، شرطي)؛ `repo.create_digital_gift` (`repository.py:169`, commit `:172`)
- `553` (`request_physical_gift`) — `self.finance.transfer` (وارث)؛ `repo.create_physical_gift_request` (commit `:179`)
- `629` (`subscribe_group_to_plan`) — `self.finance.transfer` (وارث)؛ `repo.create_group_subscription` (commit `:225`)

**sovereign_entities/service.py**
- `364` (`deposit_to_entity_wallet`) — `repo.update_entity` (`repository.py:97`, commit `:103`)؛ `self.finance.transfer` (وارث)
- `429` (`transfer_from_entity`) — `self.finance.transfer` (وارث)؛ `repo.update_entity` (commit `:103`)

**tourism_sports/service.py**
- `160` (`book_program`) — `self.finance.transfer` (وارث)؛ `invoicing_service.create_invoice` (commit)؛ `repo.create_program_participant` (`repository.py:50`, commit `:53`)
- `277` (`purchase_event_ticket`) — `self.finance.transfer` (وارث)؛ `invoicing_service.create_invoice` (commit)؛ `repo.create_ticket` (commit `:75`)
- `428` (`place_transfer_bid`) — `repo.create_transfer` (commit `:113`)؛ `invoicing_service.create_invoice` (commit)

**transport/service.py**
- `330` (`book_trip`) — `self.finance.transfer` (وارث)؛ `repo.create_booking` (`repository.py:173`, commit `:176`)
- `427` (`create_delivery`) — `repo.create_delivery_task` (commit `:201`)
- `506` (`pay_delivery`) — `self.finance.transfer` (وارث)

**zamakana/service.py**
- `302` (`pledge_time`) — `repo.create_pledge` (`repository.py:162`, commit `:165`)؛ `invoicing_service.create_invoice` (commit، شرطي)
- `378` (`fulfill_pledge`) — `repo.fulfill_pledge` (commit `:214`)؛ `repo.add_collected_hours` (commit `:157`)؛ `repo.update_campaign` (commit `:150`, شرطي)

### الخلاصة

**ده مش باج معزول في `ai_governance`. ده نمط منهجي عبر طبقة الـrepository بالكامل تقريبًا.** 89 موضع Buggy، لكن الإصلاح الفعلي أقل عمليًا من كده — لأن تصليح `finance/repository.py` (3 methods) بيحل 18 موضع تبعية تلقائيًا، فالعدد الحقيقي للـrepo methods المحتاجة تعديل فعلي أقل من 89 (تجميع الجدول أعلاه بيدي القائمة الدقيقة بعد إزالة التكرار).

**الحالة:** ✅ الجرد اتعمل ومؤكَّد بعيّنة يدوية. ⏳ في انتظار قرار المستخدم بخصوص تطبيق القاعدة الموحّدة على الـ89 موضع.

---

## [2026-08-12] اكتشاف حرج تاني — باج constructor في `FinanceService` عبر 16 دومين (خارج نطاق الجلسة، موثَّق فقط)

**السياق:** أثناء التحقق اليدوي من عيّنة المرحلة 1، لوحظ إن `transport/service.py` بتنشئ `FinanceService(db)` بمعامل واحد بس. `FinanceService.__init__(self, db, tenant_id: int)` (`finance/service.py:19`) بياخد `tenant_id` **إجباري بلا default**.

**الفحص الكامل (مؤكَّد، مش تخمين):**

**هل الباج ده بيأثر على `finance.transfer()` نفسها؟ لأ.** `FinanceService` بتتنادى صح من `finance/router.py` (9 endpoints) + 8 دومينات بتستدعيها صح: `sovereign_entities`, `commerce`, `saas`, `invoicing`, `academy`, `ai_agents`, `agritech`, `affiliate` (كلهم `FinanceService(db, tenant_id)`). الباج **منبعه منفصل تمامًا** — 16 دومين تانيين بيكسروا في `__init__` بتاعهم هما، **قبل** ما يوصلوا لأي استدعاء لـ`transfer()` أصلاً.

**تأكيد الاستخدام الحي لكل الـ16 دومين (صفر dead code):**

| الدومين | مُستخدَم فعليًا؟ | عدد الـendpoints المتأثرة |
|---|---|---|
| transport | ✅ آه | 16 |
| health | ✅ آه | 14 |
| insurance | ✅ آه | 14 |
| employment | ✅ آه | 22 |
| tourism_sports | ✅ آه | 10 |
| tenders_auctions | ✅ آه | 6 |
| digital_twin | ✅ آه | 14 |
| social | ✅ آه | 19 |
| service_marketplace | ✅ آه | 15 |
| arbitration_syndicates | ✅ آه | 17 |
| manufacturing | ✅ آه | 20 |
| logistics | ✅ آه | 22 |
| realestate | ✅ آه | 13 |
| projects | ✅ آه | 19 |
| invitations | ✅ آه | 31 |
| iot | ✅ آه | 11 |
| **إجمالي** | | **~263 endpoint** |

كل الـ16 بينشئوا الـService مباشرة (eager) داخل كل endpoint function في `router.py`، مش lazy ومش خلف أي شرط. `__init__` بتاعهم بينفّذ `self.finance = FinanceService(db)` من غير أي شرط → `TypeError: missing 1 required positional argument: 'tenant_id'` فوري، **قبل أي منطق تاني في الـendpoint**. ملاحظة إضافية: `transport/service.py` فيها 4 أسطر `# pyright: report...=false` في أول الملف بتكتم بالظبط نوع الخطأ ده من الـtype checker.

**التصنيف:** نفس فئة باج الـconstructor اللي اتصلحت في Phase 16 (`command/service.py`) — مش باج ترانزاكشن، **باج مختلف تمامًا في الفئة**. لكنه أخطر عمليًا: كل الـ~263 endpoint دي معطّلة بالكامل حاليًا، بغض النظر عن باج الترانزاكشن.

**القرار (بتوجيه المستخدم الصريح):** **متلمسش أي حاجة من الـ16 دومين دول دلوقتي.** موثَّق هنا كقسم منفصل وبارز، خارج نطاق جلسة باج الترانزاكشن بالكامل. يحتاج جلسة/Phase منفصلة وقرار نطاق مستقل.

**الحالة:** ✅ موثَّق بالكامل. صفر تعديل. **خارج النطاق النشط لهذه الجلسة.**

---

## [2026-08-12] الحالة الحالية — قيد الانتظار

**تم:**
1. ✅ تأكيد `finance.transfer()` كمسار إنتاج حرج (33 caller).
2. ✅ المرحلة 1 — الجرد الشامل (97 `begin_nested()`، 89 Buggy، 8 Clean، 1 مصلَّح جزئيًا).
3. ✅ توثيق اكتشاف باج constructor منفصل (16 دومين، ~263 endpoint) — خارج النطاق، صفر لمس.

**قيد الانتظار — قرار المستخدم:**
تطبيق القاعدة الموحّدة (`commit()` → `flush()`) على الـ89 موضع المؤكَّدة، بالترتيب المقترح:
1. `finance/repository.py` أولًا (3 methods: `WalletRepository.create`, `WalletRepository.update_balances`, `TransactionRepository.create`) + السطرين المباشرين (`finance/service.py:281` `mint_currency`) — ده بيحل 18 موضع تبعية تلقائيًا.
2. باقي الدومينات، دومين دومين، بتوثيق أول بأول في التقرير ده.
3. تحقق حي لكل موضع (غير مالي: نفّذ ووثّق بدون انتظار موافقة). لـ`finance.transfer()` تحديدًا: تحويل فعلي بين محفظتين اختباريتين — **نقطة التوقف الوحيدة المطلوب فيها موافقة قبل التنفيذ**.
4. commit نهائي واحد في آخر الجلسة.

**الحالة:** ⏳ في انتظار "كمّل" من المستخدم لبدء التطبيق الفعلي.

---

## [2026-08-12] قرار المستخدم — تسلسل معدَّل لخطوات التنفيذ

**التسلسل المتفق عليه:**
1. إصلاح `finance/repository.py` (3 methods) + `finance/service.py:281` أولًا.
2. **فورًا بعدها**: التحقق الحي على `finance.transfer()` (تحويل فعلي بين محفظتين اختباريتين) — **نقطة التوقف الوحيدة اللي محتاجة موافقة**، قبل ما نبني عليها باقي الشغل.
3. بعد التأكيد: كمّل باقي الـ88 موضع (زائد/ناقص التبعيات اللي اتحلّت تلقائيًا)، دومين دومين، توثيق أول بأول. التحقق الحي على المسارات غير المالية: نفّذ ووثّق مباشرة بلا انتظار موافقة.
4. **تنبيه واحد إضافي متفق عليه:** لو وصلت لموضع فيه شرط (`شرطي` في الجدول) وكان الشرط نفسه بيغيّر سلوك متوقَّع (مش بس commit مشروط)، أوقف واستوضح قبل ما أكمل.
5. commit نهائي واحد في الآخر، مع تنظيف بيانات الاختبار (المحفظتين التجريبيتين) وتحقق مستقل إن اتشالوا.

**الحالة:** ✅ اتفق عليه. بدء التنفيذ.

---

## [2026-08-12] خطوة 1 — إصلاح `finance/repository.py` + `finance/service.py:281`

**الإصلاحات المطبَّقة (3 + 1، `commit()` → `flush()` بالحرف، زي القاعدة الموحّدة):**

`finance/repository.py`:
- `WalletRepository.create` — سطر 44 (كان `commit()`، بقى `flush()`)
- `WalletRepository.update_balances` — سطر 52 (نفس التغيير)
- `TransactionRepository.create` — سطر 77 (نفس التغيير)

`finance/service.py`:
- `mint_currency` — سطر 281 (`await self.db.commit()` مباشر جوه `begin_nested()`، بقى `await self.db.flush()`)

**تأكيد مستقل بعد التطبيق (`grep`):**
- `finance/service.py`: صفر `self.db.commit()` متبقّي في الملف كله.
- `finance/repository.py`: الـ`commit()` المتبقّية (سطور 65, 203, 211, 219, 227, 254) كلها في methods **غير مستدعاة من جوه أي `begin_nested()`** حسب جرد المرحلة 1 (`WalletRepository.freeze`, `SystemStateRepository.*`, `AuditLogRepository.create`) — **لم تُلمس، خارج نطاق الإصلاح المؤكَّد**.

**لم يُلمس** `WalletRepository.get_by_user_id` / `get_by_user_id_for_update` (SELECT فقط، لا commit أصلًا).

**الحالة:** ✅ خطوة 1 مكتملة. الخطوة الجاية: التحقق الحي على `finance.transfer()` (نقطة التوقف الوحيدة).

---

## [2026-08-12/13] قرار المستخدم — تسلسل خطوة 2 مفصَّل + محاولة التنفيذ (توقفت جزئيًا)

**تعليمات المستخدم بالتفصيل لخطوة 2:**
1. إعادة تشغيل `uvicorn` من الصفر، فحص لوج الإقلاع كامل (صفر Traceback).
2. تجهيز محفظتين اختباريتين برصيد معروف (بادئة `phase_finance_`، تينانت اختباري منفصل).
3. تنفيذ `transfer` فعلي بينهم (مبلغ محدد، مش رمزي).
4. تحقق مستقل بعد العملية: `SELECT` مباشر على رصيد المحفظتين (مش بس status code)، تأكيد صف `Transaction` اتسجل.
5. Edge case إضافي: تنفيذ transfer تاني فورًا بعد الأول (نفس المحفظتين) — للتأكد إن الـSAVEPOINT بيتقفل صح ومفيش تراكم/قفل معلّق.

### 1) إعادة تشغيل uvicorn — نتيجة نظيفة

أول محاولة تشغيل (بدون `PYTHONIOENCODING=utf-8`) طلعت لوج ضخم (~10,900 سطر) بسبب `UnicodeEncodeError` متكرر (الـconsole بتاع Windows بيستخدم codepage `cp1256`، مش بيقدر يطبع الإيموجي في رسائل الـlogger — `--- Logging error ---` مش استثناء حقيقي من التطبيق، مجرد فشل كتابة على الـstream). أُعيد التشغيل بـ`PYTHONIOENCODING=utf-8` → لوج نظيف (266 سطر بس)، **صفر `Traceback` حقيقي، صفر `[ERROR]`/`[CRITICAL]`**، 49 `[WARNING]` كلها من نوع واحد فقط ("Skipping index (likely exists)" — محاولات `CREATE INDEX IF NOT EXISTS` بتتصادم مع transaction متوقفة، سلوك موجود من قبل الجلسة دي، مش متعلق بأي تعديل بتاعنا). `Application startup complete` + `Uvicorn running on http://127.0.0.1:8000` في آخر اللوج. Redis متصل صح على `127.0.0.1:6380` (الـcontainer `redis` كان شغال بالفعل، مفيش داعي `docker start`).

**الحالة:** ✅ خطوة (1) في التسلسل الجديد مكتملة، لوج نظيف مؤكَّد.

### 2) تجهيز بيانات الاختبار — محفظتين + تينانت مخصَّص

- تسجيل 2 يوزر حقيقي عبر `POST /api/identity/register` (مش `INSERT` خام — تفاديًا لمشكلة NULL defaults اللي حصلت في Phase 16): `phase_finance_sender` (id=29) و`phase_finance_receiver` (id=30)، كلاهما هبطوا افتراضيًا في `tenant_id=1` (`PUBLIC_REGISTRATION_TENANT_ID` الافتراضي). الـregister بينشئ محفظة تلقائيًا لكل واحد (عبر `identity/repository.py`'s `WalletRepository` — **كلاس منفصل عن `finance/repository.py`'s `WalletRepository`**، بـdefault balances `{}` مش `{"MR_POUND":0,...}`).
- إنشاء تينانت اختباري مخصَّص: `INSERT INTO academy_tenants (name='Phase Finance Test Tenant', domain='phase-finance-test-2026.local', admin_id=29, is_active=true)` → **`id=13`**. (لازم `admin_id` يشاور على يوزر موجود بالفعل بسبب الـFK — استخدمت id=29 كـbootstrap.)
- `UPDATE users SET tenant_id=13 WHERE id IN (29,30)` + `UPDATE wallets SET tenant_id=13 WHERE user_id IN (29,30)` — لمزامنة اليوزرين ومحافظهم مع التينانت الجديد.
- `UPDATE wallets SET balances='{"MR_USDT": 100}' WHERE user_id=29` — زرع رصيد اختباري 100 MR_USDT للمرسل.

**الحالة:** ✅ خطوة (2) مكتملة. بيانات throwaway جاهزة، لسه متلمستش (تنضيفها هيحصل في الخطوة الأخيرة من الجلسة زي المتفق).

### 3) عائق تشغيلي غير متوقع #1 — بوابة "sector" عامة (خارج نطاق باج الترانزاكشن)

أول محاولة استدعاء `GET /api/finance/balances` و`POST /api/finance/transfer` (بتوكن JWT حقيقي لليوزر 29) رجعت **403**: `{"detail":"User sector not defined. Please contact support.","code":"PermissionDeniedError"}`.

**السبب (قراءة كود):** `app/main.py:300-305` بيلف **كل الـ30 router دومين** (شامل `finance`) بـ`Depends(require_sector(sector))` كجزء من تسجيل الراوتر نفسه. `require_sector` (`core/security.py:205-224`) بيرفض أي مستخدم لو الـJWT مالوش claim `"sector"` — **إلا لو دوره `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`** (استثناء صريح في الكود، سطر 215-216). تتبّعت مصدر الـclaim: `identity/service.py`'s `_issue_tokens` (سطر 116-119) **مش بيبعت `sector` إطلاقًا** وقت إصدار التوكن — يعني أي يوزر عادي (`system_role=USER`) حاليًا **معندوش طريقة يعدّي بيها البوابة دي على أي دومين من الـ30**، بغض النظر عن الباج اللي بنحقق فيه.

**التصنيف:** فئة مختلفة تمامًا (بوابة صلاحيات عامة على مستوى كل الـrouters، مش مرتبطة بـtenant/SAVEPOINT). **قرار تنفيذي بسيط اتخد بدون سؤال** (يطابق سابقة Phase 16 اللي رفّعت يوزرات الاختبار لـ`SUPER_ADMIN` لتفادي بوابات غير متعلقة بالباج المستهدف): `UPDATE users SET system_role='SUPER_ADMIN' WHERE id IN (29,30)` — تجاوز مؤقت لليوزرين الاختباريين بس، صفر لمس لكود `require_sector`/`_issue_tokens` نفسه. **موثَّق هنا كملاحظة جانبية فقط — مش مقترَح للإصلاح، خارج النطاق بالكامل.**

**الحالة:** ✅ عائق (3) اتلف حواليه (بيانات اختبار بس)، مفيش تعديل كود.

### 4) عائق تشغيلي غير متوقع #2 — كراش قاطع في `finance/router.py` نفسه (مانع تمامًا، خارج نمط الباج المستهدف)

بعد تجاوز بوابة الـsector، نفس الطلبين (`balances`, `transfer`) رجعوا **500** (`Internal Server Error` بدون تفاصيل JSON). تتبُّع اللوج الحي:

```
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>:
invalid input for query argument $2: <app.api.deps.SimpleTenant object at 0x...>
('SimpleTenant' object cannot be interpreted as an integer)

[SQL: SELECT transactions... FROM transactions JOIN users ON ...
      WHERE transactions.idempotency_key = $1::VARCHAR AND users.tenant_id = $2::INTEGER]
[parameters: ('phase_finance_tx1', <app.api.deps.SimpleTenant object at 0x000001C7B9CE1430>)]

Traceback (مختصر):
  finance/router.py:49 (transfer_funds) → service.transfer(...)
  finance/service.py:72 (transfer) → self.tx_repo.get_by_idempotency_key(...)
  finance/repository.py:84 (get_by_idempotency_key) → self.db.execute(...)
  → DataError من asyncpg
```

**السبب الجذري (قراءة كود، مؤكَّد):**
- `api/deps.py:148-153` — `get_current_tenant()` بترجع كائن `SimpleTenant` (فيه `.id`)، **مش `int` خام**:
  ```python
  async def get_current_tenant(x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")) -> SimpleTenant:
      tenant = SimpleTenant()
      tenant.id = x_tenant_id
      return tenant
  ```
- `finance/router.py` — **كل الـ8 endpoints** (سطور 27, 44, 74, 101, 135, 147, 160, 185) لسه بتستخدم التوقيع القديم:
  ```python
  tenant_id: int = Depends(get_current_tenant),   # type hint مضلِّل — القيمة الفعلية كائن SimpleTenant
  ...
  service = FinanceService(db, tenant_id)          # بيتبعت الكائن كامل بدل .id
  ```
  الـ`: int` مجرد تعليق بصري (FastAPI بتحقن القيمة الفعلية من `get_current_tenant()` بغض النظر عن الـtype hint). أي استخدام لاحق لـ`tenant_id` كـinteger (زي هنا، bind parameter في SQL) بينفجر.

**التأثير:** `finance/router.py` بالكامل (كل الـ8 endpoints — `transfer`, `swap`, `balances`, `history`, وكل admin endpoints) **معطّل 100% حاليًا**، بغض النظر عن باج الترانزاكشن اللي أصلحناه في خطوة 1. ده بيمنع أي تحقق حي حاسم لـ`finance.transfer()` بشكل قاطع.

**endpoint سطر 123 (`get_crypto_mode`) مستثنى:** بيستخدم `FinanceService(db, 1)` هاردكودد مباشرة، صفر استخدام لـ`get_current_tenant` — مش متأثر بالكراش ده (لكن برضه بيثبت `tenant_id=1` بتصميم، خارج نطاق النقاش ده).

**قرار المستخدم عند هذه النقطة:** رفض الديف المقترح فوريًا قبل التنفيذ، وطلب توضيح 4 نقاط قبل أي استكمال. **صفر تعديل كود اتنفّذ فعليًا على `finance/router.py` أو أي ملف تاني بعد خطوة 1.**

**الحالة:** ⏳ **متوقف بالكامل، في انتظار قرار المستخدم.**

---

## [2026-08-13] توضيح المستخدم المطلوب — 4 نقاط + التحليل الكامل

### السؤال 1: الديف المعروض (المرفوض) — مصدر `tenant_id` النهائي كان إيه؟

الديف اللي عُرض في الـpreview:
```python
tenant: SimpleTenant = Depends(get_current_tenant),
...
service = FinanceService(db, tenant.id)
```
**تأكيد صريح: `tenant.id` مصدره لسه الهيدر `X-Tenant-ID` مباشرة، صفر اعتماد على `current_user`.** الديف ده كان **تصحيح type فقط** (attribute access صحيح `tenant.id` بدل تمرير الكائن كامل) — **مش تصحيح مصدر الثقة**. عرضه كـ"Recommended" من غير ما أوضّح الفرق ده كان قصور — المستخدم صح إنه وقف قبل التنفيذ.

### السؤال 2: الإصلاح المركّب المطلوب (لسه لم يُنفَّذ)

القرار المتفق عليه (لم يُطبَّق بعد، مستني موافقة نهائية): إزالة `get_current_tenant` بالكامل من الـ8 endpoints، واستبداله بـ:
```python
current_user: User = Depends(get_current_active_user),   # أغلب الـendpoints أصلًا بتاخده
...
tenant_id = cast(int, current_user.tenant_id)
```
نفس نمط Phase 16 بالحرف (`command/router.py`) — تصحيح **مصدر** الثقة، مش بس النوع.

### السؤال 3: جرد `get_current_tenant` في `finance/router.py` — كامل (بالـfile:line)

| السطر | الـendpoint | الحماية الحالية |
|---|---|---|
| 27 | `get_balances` | `get_current_active_user` (مستخدم عادي) |
| 44 | `transfer_funds` | `get_current_active_user` |
| 74 | `swap_currencies` | `get_current_active_user` |
| 101 | `get_history` | `get_current_active_user` |
| 135 | `set_crypto_mode` | `get_current_superuser` |
| 147 | `set_exchange_rates` | `get_current_superuser` |
| 160 | `mint_funds` | `get_current_superuser` |
| 185 | `set_max_supply` | `get_current_superuser` |

استثناء: سطر 123 (`get_crypto_mode`، عام) — `FinanceService(db, 1)` هاردكودد، صفر استخدام لـ`get_current_tenant`، بتصميم صريح.

### السؤال 4: هل `finance` مذكورة في `critical-finding-xtenant-systemic.md`؟ **أيوه — بتصنيف SAFE**

من الملف الأصلي (سطر 145، جدول 🟢 SAFE):
> `finance` | `SystemState` صف عالمي واحد أصلًا (بدون عمود tenant_id)، `mint_currency` مربوط بـ`current_user` | سؤال منتجي منفصل: هل أي سوبريوزر من أي tenant يُفترض يقدر يغيّر إعدادات عالمية؟ (مش ثغرة header-spoofing، لكن سؤال صلاحيات)

**يعني الآلية التقنية (الاعتماد على `get_current_tenant`) كانت معروفة ومفحوصة مسبقًا — مش اكتشاف جديد بالكامل خارج كل جرد سابق.** لكن التحليل الأصلي غطّى بس الـ4 admin endpoints صراحة؛ منهجيته استبعدت أي endpoint مربوط بملكية `current_user.id` (نص الملف، سطر 50-55: "الـendpoints المرتبطة بملكية مستخدم... مش عرضة لنفس النوع من التسريب لأن `user_id` مش قابل للتزوير") — وده كان بيغطي `transfer`/`swap`/`balances`/`history` **ضمنيًا** بدون فحص صريح.

**تتبّع دقيق منفصل (تم الآن، مش في الملف الأصلي) لتأكيد هل فيه مسار سرقة/تسريب فعلي عبر الأربعة دول:**
- `sender_id` في `transfer()` مصدره `current_user.id` (JWT) دايمًا — **غير قابل للتزوير**.
- محفظة المرسل: `get_or_create_wallet_for_update(sender_id, self.tenant_id)` — مفلترة بـ`user_id` **و** `tenant_id`-من-الهيدر معًا. تزوير الهيدر بيمنع الوصول لمحفظة المهاجم الحقيقية (بينشئله محفظة جديدة فاضية تحت تينانت غلط) — **مش بيوصله لمحفظة حد تاني**.
- `receiver = get_by_email(receiver_email, self.tenant_id)` (`identity/repository.py:41-42`) — مفلتر بـ`email` **و** `tenant_id` معًا. وأكَّدت `email` عمود **unique عالميًا** على مستوى المنصة (`identity/models.py:35`، مش per-tenant) — يعني تزوير الهيدر لتينانت غلط بيرجّع "المستلم غير موجود"، **مش بيسرّب حساب حد تاني**.

**الخلاصة الدقيقة:** نفس آلية ثقة الهيدر موجودة تقنيًا، **لكن مفيش مسار سرقة أموال أو تسريب بيانات cross-tenant فعلي مؤكَّد عبر `/finance/transfer|swap|balances|history`** — لأن كل عملية حساسة مربوطة إضافيًا بـ`current_user.id` غير القابل للتزوير. ده **بيفرق جوهريًا** عن `realestate`/`digital_twin`/`automation` (المذكورين في الملف الأصلي كـSUSPICIOUS بصفر ربط بـcurrent_user، ثغرة سرقة/تسريب فعلية). التصنيف SAFE الأصلي كان صح في نتيجته، لكن السبب المذكور (SystemState عالمي) كان غطى admin endpoints بس، مش الأربعة العاديين.

**الأثر العملي الوحيد المؤكَّد لثقة الهيدر هنا:** إنشاء "محافظ شبح" (`Wallet` جديد فاضي تحت تينانت غلط لو الهيدر ماتطابقش الحقيقي) — تلوث بيانات محتمل، **مش سرقة**. لم يُفحص بعد تأثيره على بيانات حقيقية موجودة.

**تقييم صريح (رأي، معروض للمراجعة):** ده **مش أولوية أعلى من الجلستين الحاليتين مجتمعين** — غير قابل للاستغلال فعليًا لسرقة أموال حسب التتبع أعلاه. لكنه **لازم يتصلح بنفس الديف المركّب (`current_user.tenant_id`)** قبل أي تحقق حي — لأنه (أ) بيحل الكراش المانع بشكل نهائي، (ب) بيوحّد النمط مع باقي الدومينات المصلَّحة، (ج) بيقفل أي شك مستقبلي بلا حاجة لتحقيق إضافي.

### الحالة الحالية — بيانات throwaway معلَّقة (لسه متلمستش، هتتنضف في خطوة التنظيف النهائية)

- `academy_tenants id=13` ("Phase Finance Test Tenant")
- `users id=29` (`phase_finance_sender`, رُفِّع مؤقتًا لـ`SUPER_ADMIN`), `id=30` (`phase_finance_receiver`, نفس الترقية)
- `wallets id=25` (user 29, رصيد مزروع `{"MR_USDT": 100}`), `id=26` (user 30, `{}`)
- **صفر transfer حقيقي اتنفّذ لحد الآن** — الكراش منع أي عملية فعلية، فمفيش صف `Transaction` أو تغيير رصيد حقيقي للتحقق منه بعد.
- `uvicorn` شغال حاليًا (لوج نظيف، `PYTHONIOENCODING=utf-8`)، السيرفر متاح على `127.0.0.1:8000`.

**الحالة:** ⏳ **الجلسة متوقفة بالكامل، صفر تنفيذ إضافي، في انتظار رد المستخدم بعد قراءة هذا التقرير.**

---

## [2026-08-13] رد المستخدم — تتبّع `get_balances`/`get_history`/`swap_currencies` + تطبيق الإصلاح المركّب + التحقق الحي الكامل

### تتبّع دقيق: هل `balances`/`history`/`swap` عندهم نفس حماية `transfer` (ربط بـ`current_user.id`)؟

**`get_balances`** (`router.py:23-35` → `service.py:28-32` → `repository.py:18-24`):
```sql
SELECT * FROM wallets WHERE user_id = $1 AND tenant_id = $2
```
`$1 = current_user.id` (JWT، غير قابل للتزوير)، `$2 = tenant_id` (كان هيدر). فلترة مزدوجة — تزوير الهيدر بيمنع الوصول لمحفظة المستخدم الحقيقية (بيعمل محفظة شبح فاضية)، **مش بيوصّل لمحفظة حد تاني**.

**`swap_currencies`** (`router.py:68-88` → `service.py:149-182`): عملية على محفظة المستخدم نفسه بس (مفيش طرف تاني إطلاقًا) — `get_or_create_wallet_for_update(user_id)` بنفس الفلترة المزدوجة. أبسط وأأمن من `transfer` (معندهاش حتى مستلم).

**`get_history`** (`router.py:91-115` → `service.py:311-333` → `repository.py:96-154`) — النص الحرفي للاستعلام:
```sql
SELECT transactions.* FROM transactions
JOIN users ON users.id = transactions.sender_id OR users.id = transactions.receiver_id
WHERE (transactions.sender_id = $user_id OR transactions.receiver_id = $user_id)
  AND users.tenant_id = $tenant_id_header
```
`$user_id = current_user.id` ثابت دايمًا، والشرط `sender_id=$user_id OR receiver_id=$user_id` موجود بغض النظر عن أي صف `users` اتربط في الـjoin — **مستحيل ترجع معاملة المستخدم مش طرف فيها**. أقصى أثر لتزوير الهيدر: تغيير أي معاملات المستخدم نفسه تظهر (نتيجة جانبية من شكل join غريب)، مش كشف بيانات مستخدم تاني.

**الخلاصة النهائية (تُضاف كتصحيح لتبرير SAFE الأصلي — راجع القسم الجديد في `critical-finding-xtenant-systemic.md`):** الأربعة `transfer`/`swap`/`balances`/`history` كلهم بلا استثناء مربوطين بـ`current_user.id` في كل استعلام حساس. **صفر مسار سرقة/تسريب cross-tenant حقيقي مؤكَّد.** التصنيف يفضل SAFE — الإصلاح المركّب مطلوب لسببين تشغيليين (حل الكراش + توحيد النمط) مش لسبب أمني حرج.

### تطبيق الإصلاح المركّب — `finance/router.py` (8 endpoints)

**التعديلات (3 `Edit`، مؤكَّدة بـ`grep` مستقل بعدها = صفر نتيجة لـ`get_current_tenant`):**
1. حذف `get_current_tenant` من سطر الاستيراد (`from app.api.deps import get_current_active_user, get_current_superuser`).
2. `replace_all`: حذف كل سطر `tenant_id: int = Depends(get_current_tenant),` (8 مواضع، سطر واحد بالحرف).
3. `replace_all`: `service = FinanceService(db, tenant_id)` → `service = FinanceService(db, cast(int, current_user.tenant_id))` (8 مواضع).

قراءة الملف كامل بعد التعديل أكَّدت: الـ8 endpoints كلها بقت بتستخدم `current_user.tenant_id` حصريًا، الـtype hint اتحل مع المصدر مع بعض بضربة واحدة. `get_crypto_mode` (سطر 114-124، العام، `FinanceService(db, 1)` هاردكودد) **متلمسش** — برّه النطاق بتصميم صريح.

### إعادة تشغيل uvicorn — لوج نظيف

أُعيد التشغيل (`PYTHONIOENCODING=utf-8`، PID جديد بعد إيقاف القديم). فحص كامل: **صفر `Traceback`، صفر `[ERROR]`/`[CRITICAL]`**، نفس أنماط الـWARNING المعروفة بتاعة "Skipping index" (49 تقريبًا، غير متعلقة). `Application startup complete` + `HTTP 200` على `/docs`.

### التحقق الحي الكامل (زي المتفق بالحرف)

**1) `GET /api/finance/balances` — بدون أي هيدر `X-Tenant-ID` إطلاقًا (لإثبات إن المصدر بقى JWT فقط):**
```
{"balances":{"MR_USDT":100.0}}   HTTP 200
```

**2) `POST /api/finance/transfer` — تحويل فعلي #1، 30 MR_USDT، بدون هيدر:**
```
{"tx_hash":"TX-1B20C6B9C7B1","amount":30.0,"currency":"MR_USDT","status":"COMPLETED",...}   HTTP 200
```
**تحقق مستقل مباشر على DB (مش status code):**
```sql
wallets: user 29 → {"MR_USDT": 70.0}   |   user 30 → {"MR_USDT": 30.0}
transactions: id=1, TX-1B20C6B9C7B1, sender=29, receiver=30, amount=30, status=COMPLETED
```
مطابق تمامًا للمتوقَّع (100-30=70، 0+30=30). **صفر `InvalidRequestError`، صفر Traceback في اللوج لهذا الطلب.**

**3) Edge case — تحويل فعلي #2 فورًا بعد الأول، نفس المحفظتين، 15 MR_USDT:**
```
{"tx_hash":"TX-BDAFF83E0DB0","amount":15.0,"currency":"MR_USDT","status":"COMPLETED",...}   HTTP 200
```
**تحقق مستقل على DB:**
```sql
wallets: user 29 → {"MR_USDT": 55.0}   |   user 30 → {"MR_USDT": 45.0}
transactions: 2 صف بالظبط (tx1 + tx2)، كلاهما COMPLETED، صفر تكرار/صف يتيم
```
مطابق تمامًا (70-15=55، 30+15=45). **الـSAVEPOINT بيتقفل صح بعد كل عملية — مفيش تراكم ولا قفل معلّق بين الطلبين المتتاليين.**

**4) `GET /api/finance/history` (بدون هيدر) — 🔴 باج جديد، غير متعلق بالترانزاكشن/tenant إطلاقًا:**
```
HTTP 500 — sqlalchemy.exc.ArgumentError: expected ORM mapped attribute for loader strategy argument
  File "finance/repository.py", line 120, in get_by_user_paginated
    load_only(  # type: ignore
```
**السبب:** `repository.py:119-126` بيستخدم `load_only("id", "tx_hash", "amount", ...)` بـ**أسماء أعمدة كـstrings**، لكن نسخة SQLAlchemy الحالية بتاعة المشروع محتاجة **كائنات attribute حقيقية** (`Transaction.id`, `Transaction.tx_hash`, ...) مش نصوص خام. باج pre-existing في بناء الاستعلام نفسه، **صفر علاقة بـ`begin_nested()`/`commit()` أو بإصلاح `X-Tenant-ID` اللي عملناه تو** (السطر ده مكانه من الأساس، متلمسش في أي تعديل بتاعنا). **مش هيتصلح — موثَّق فقط، خارج نطاق الجلستين، زي `get_dashboard`/`RedisClientWrapper` في Phase 16.**

**5) `GET /api/finance/balances` (نهائي، بعد التحويلين، بدون هيدر):**
```
{"balances":{"MR_USDT":55.0}}   HTTP 200
```
مطابق للمتوقَّع.

### الخلاصة

**✅ `finance.transfer()` مؤكَّدة حيًا بالكامل الآن** — مسارها الحرج (33 caller عبر المشروع) بقى شغال فعليًا بعد إصلاح خطوة 1 (باج الترانزاكشن) + الإصلاح المركّب (باج الـtenant-trust/type). `balances`/`swap` مؤكَّدين من نفس الأدلة (مسار مطابق بنيويًا لـ`transfer`). `history` معطوبة لسبب منفصل تمامًا، موثَّق بدون إصلاح.

**بيانات throwaway لسه معلَّقة (تينانت 13، يوزرين 29/30، محفظتين، 2 صف transaction) — هتتنضف في خطوة التنظيف النهائية للجلسة زي المتفق، مش دلوقتي.**

**الحالة:** ✅ **نقطة الموافقة الوحيدة (خطوة 2) مكتملة ومؤكَّدة بالكامل.** جاهزين نكمل باقي الـ88 موضع (دومين دومين) حسب التسلسل المتفق عليه.

---

## [2026-08-13] بدء تطبيق باقي الـ88 موضع — `ai_governance` (إكمال Phase 16) + اكتشاف باج فئة مختلفة (تلوّث connection pool)

### إصلاح `ai_governance/repository.py` — 4 methods متبقية

`commit()` → `flush()` بالحرف في:
- `create_or_update_quota` (سطر 35) — مستدعاة من `set_quota`/`check_and_consume`/`reset_quotas` (`service.py:33,155,205`)
- `reset_quota_usage` (سطر 56) — `service.py:205`
- `update_rate_limits` (سطر 123) — `service.py:66`
- `create_audit_log` (سطر 142) — `service.py:33,66,205`

تأكيد مستقل (`grep`): صفر `self.db.commit()` متبقّي في `ai_governance/repository.py`. (`create_usage_log` كانت مصلَّحة بالفعل من Phase 16.) **دومين `ai_governance` مغلق بالكامل الآن — كل الـ4 مواضع الـBuggy الأصلية اتصلحت.**

### التحقق الحي

زرعت `ai_agents` throwaway (`id=1`, `tenant_id=13`, `owner_id=29`, `status=ACTIVE`, `is_deleted=false`) لاختبار endpoints الدومين.

**محاولة #1 — `POST /agents/1/quotas` (`set_agent_quota`):** `500` — `IntegrityError: null value in column "reset_at"`. **باج pre-existing منفصل تمامًا** (`service.py`'s `set_quota` مبيحسبش/مبيبعتش `reset_at` وقت إنشاء quota جديدة، والعمود `NOT NULL`). صفر علاقة بـ`begin_nested()`/`commit()` — موثَّق فقط، مش هيتصلح (نفس نمط `get_dashboard`/`history`).

**محاولة #2 — `POST /agents/1/quotas/reset` (`reset_agent_quotas`، فورًا بعد المحاولة الفاشلة، نفس الـuvicorn process):** `500` — لكن هالمرة:
```
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager.
  repository.py:141 (create_audit_log) → self.db.add(log) → _autobegin_t()
```

**🔴 اكتشاف جديد، فئة مختلفة تمامًا عن باج الجلسة (تأكَّد بعزل مضبوط):** أعدت تشغيل `uvicorn` من الصفر (connection pool جديد تمامًا)، ونادّيت **نفس** `POST /agents/1/quotas/reset` **بمفردها** (من غير أي طلب فاشل قبلها) → **`204` نجاح تام، فورًا**. هذا يثبت قطعيًا: الكود نفسه سليم بعد إصلاحنا — لكن **استثناء DB غير معالَج (زي `IntegrityError` المحاولة #1) أثناء `flush()`/`commit()` جوه `begin_nested()` بيسيب الـconnection المُستخدَمة في الـpool في حالة "متسخة"** (على الأرجح transaction معلّقة/aborted على مستوى asyncpg نفسه لم تُعاد تنظيفها بشكل كامل قبل ما `get_db()`'s `finally: await session.close()` يرجّعها للـpool)، وأي request تاني — حتى غير متعلق تمامًا — لو طلع له نفس الـconnection من الـpool، بيفشل فورًا بـ"closed transaction" بغض النظر عن سلامة كوده هو.

**التصنيف:** فئة مختلفة تمامًا (session/connection-pool lifecycle عند استثناءات DB غير معالَجة) — **مش نمط `commit()` جوه `begin_nested()`** اللي إحنا بنصلحه. لكنه مهم عمليًا لأنه بيفسّر نتائج تحقق حي غلط لو حصل استثناء قبله في نفس الـprocess (زي ما حصل هنا بالظبط).

**قرار تنفيذي (بدون سؤال، منهجية اختبار بس — صفر لمس كود):** من دلوقتي، أي اختبار حي بيرجّع `500` (باستثناء الأخطاء المتوقعة/الموثَّقة) → **إعادة تشغيل `uvicorn` فورًا قبل تصديق أي نتيجة تحقق حي تالية**، لتفادي نتائج ملوَّثة من pool متسخ. **صفر تعديل كود لهذا الباج — موثَّق فقط، خارج نطاق الجلسة، زي باقي الاكتشافات الجانبية.**

**الحالة:** ✅ `ai_governance` مغلق (4 methods مصلَّحة، تحقق حي "نجح" ظاهريًا — `204` نظيف). ⚠️ **تصحيح لاحق: هذا الحكم كان غير دقيق — راجع القسم الحرج تحت.**

---

## [2026-08-13] تطبيق ميكانيكي على باقي الـ23 دومين — `commit()` → `flush()`

**تم تطبيق نفس القاعدة الموحّدة (`commit()` → `flush()`) بالحرف على كل الـmethods المؤكَّدة من جرد المرحلة 1**، دومين دومين:

`academy` (1: `enroll`)، `affiliate` (4: `update_affiliate_profile`, `create_referral_tree`, `update_commission_status`, `bulk_update_commission_status`)، `agritech` (2: `create_harvest`, `create_bio_yield`)، `ai_agents` (2: `resolve_approval`, `create_task_log`)، `commerce` (1 مباشر في `service.py:484`)، `communications` (5: `create_notification`, `create_thread`, `create_message`, `add_to_mailbox`, `add_attachment`)، `digital_twin` (3: `create_twin_config`, `create_time_capsule`, `create_beneficiary`)، `employment` (1: `create_contract`)، `health` (9: `create_facility`, `create_medical_profile`, `update_medical_profile`, `create_biometric_log`, `create_prognosis`, `create_appointment`, `create_consultation`, `create_prescription`, `create_dispatch`)، `insurance` (6: `create_policy`, `create_subscription`, `create_claim`, `update_claim`, `create_pension`, `create_employee_profile`)، `invitations` (10 + 1 مباشر في `service.py:203`)، `logistics` (9)، `manufacturing` (14)، `privacy` (1: `update_erasure_request`)، `projects` (3)، `realestate` (3)، `saas` (5)، `service_marketplace` (3)، `social` (3)، `sovereign_entities` (1: `update_entity`)، `tourism_sports` (3)، `transport` (2)، `zamakana` (4).

**تأكيد مستقل شامل (`grep` عبر كل الملفات المتأثرة):** كل موضع مؤكَّد من المرحلة 1 اتصلح بالظبط، وصفر موضع غير مؤكَّد اتلمس (الـ`commit()` المتبقية في كل ملف تطابق تمامًا قائمة الـmethods **غير** المستدعاة من جوه `begin_nested()`).

**إعادة تشغيل uvicorn بعد كل التعديلات:** لوج نظيف تمامًا، صفر `Traceback`، `Application startup complete`.

**الحالة عند هذه النقطة:** الاعتقاد وقتها كان "الإصلاح الميكانيكي كافٍ، زي finance وai_governance بالظبط." **هذا الاعتقاد غلط، واتصحح فورًا في القسم التالي.**

---

## 🔴 [2026-08-13] توقف حرج — اكتشاف خلل في منهجية الإصلاح نفسها (مش باج فئة منفصلة)

### التسلسل اللي كشف المشكلة

التحقق الحي على `ai_agents.resolve_approval` (بعد زرع صف throwaway في `agent_approval_queue`، id=1، tenant=13):
```
POST /api/ai/approvals/1/resolve  {"status":"APPROVED","human_feedback":"..."}
→ 200 {"message":"Approval ApprovalStatus.APPROVED","approval_id":1,"status":"APPROVED"}
```
**تحقق مستقل فوري على الـDB (مش status code):**
```sql
SELECT id, status, human_feedback, resolved_at FROM agent_approval_queue WHERE id=1;
→ id=1, status=PENDING, human_feedback=NULL, resolved_at=NULL   -- ❌ متغيّرش خالص
```
**الـresponse رجّع نجاح كامل، لكن الكتابة مترجعتش للـDB إطلاقًا.**

### السبب الجذري (مؤكَّد بقراءة الكود)

`app/core/database.py`'s `get_db()`:
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```
**صفر `commit()` تلقائي على مستوى الـrequest.** `session.close()` بترولباك أي ترانزاكشن معلّقة (السلوك الافتراضي لـSQLAlchemy)، مش تعمل commit. تأكَّدت كمان (`grep` شامل على `main.py`) إن مفيش أي middleware بيعمل commit نهائي بعد كل request.

**يعني:** الكود الأصلي (قبل أي تعديل بتاعنا، في كل المشروع) كان شغال **فقط** لأن كل repository method بتعمل `self.db.commit()` **فوري لنفسها** — نمط معماري غير نظيف، لكنه كان الآلية الوحيدة اللي بتضمن حفظ أي كتابة نهائيًا على القرص.

**لما شلنا الـ`commit()` من جوه `begin_nested()` وحطينا `flush()` بدالها**، أصلحنا كراش الـSAVEPOINT فعلاً — لكن **شلنا كمان الآلية الوحيدة اللي كانت بتخلي الكتابة دي تتحفظ نهائيًا**. القاعدة الأصلية المتفق عليها نصّت على: *"الـservice (أو نقطة begin_nested نفسها) هي اللي بتتحكم في حدود الترانزاكشن"* — نُفِّذ نص الجزء الأول (الـrepo تعمل `flush()` بس) بس **اتنسى تنفيذ الجزء التاني**: لازم الـservice تضيف `commit()` صريح بعد ما بلوك `begin_nested()` يخلص بنجاح. من غيره، أي كتابة جوه البلوك بترجع فاضية (rollback صامت) لحظة ما الـsession تتقفل — **بلا أي خطأ ظاهر، status 200/204 كاذبة تمامًا.**

### إعادة فحص النتائج "الناجحة" السابقة — كانت غلط

**`ai_governance.reset_agent_quotas`** (وُثِّقت سابقًا كـ"✅ نجاح، `204` نظيف بعد العزل الصحيح"): تحقق DB الآن:
```sql
SELECT id, action, agent_id FROM agent_audit_logs WHERE agent_id=1 ORDER BY id DESC LIMIT 5;
→ 0 rows   -- ❌ الـaudit log اللي المفروض اتسجل من create_audit_log متسجّلش خالص
```
**كانت أيضًا نجاح كاذب.** حكمي وقتها بالاعتماد على status code بس كان قصور.

**`finance.transfer()` (خطوة 2، الوحيدة اللي نجت فعليًا):** تأكَّدت إنها نجحت **بالصدفة البحتة**، مش بالتصميم: `_create_audit_log` (بتتنادى بعد بلوك `begin_nested()` في `transfer()`) بتستخدم `AuditLogRepository.create()` اللي فيها `commit()` مباشر — **دي method مش من ضمن الـ89 موضع المؤكَّدة (مش مستدعاة من جوه أي `begin_nested()`)، فمتلمستش في أي تعديل**. الـ`commit()` بتاعها بيحفظ **كل حاجة معلّقة في نفس الـsession** (شامل تعديلات المحفظة والـtransaction اللي اتعملوا بـ`flush()` قبلها)، مش بس الـaudit log نفسه. **صدفة معمارية، مش ضمان.**

### التصنيف

**ده مش "باج فئة مختلفة" نوثّقه ونمشي زي `get_dashboard`/`RedisClientWrapper`/`history` — ده خلل في الإصلاح اللي إحنا بنطبّقه بالظبط على الجلسة دي.** التأثير المحتمل: **كل الـ23 دومين اللي اتعدلوا (ما عدا `finance`)** ممكن يكونوا وقعوا في نفس الفخ — الكتابة بتاعتهم مش بتتحفظ خالص حاليًا، إلا لو فيه `commit()` تاني (زي `finance`) بيحصل بالصدفة بعد بلوك الـ`begin_nested()` في نفس الطلب. **لازم فحص كل دومين على حدة** لمعرفة مين فعلاً بيحفظ (بالصدفة) ومين لأ.

**الأخطر:** الإصلاح الحالي حوّل المشكلة من **كراش ظاهر** (`InvalidRequestError`, 500) لـ**فقدان بيانات صامت** (200/204 نجاح، صفر كتابة فعلية) — ده أسوأ من الوضع الأصلي من ناحية سهولة الاكتشاف.

### الحل المقترح (لسه لم يُطبَّق، معروض للمراجعة)

إضافة `await self.db.commit()` صريح **فورًا بعد** كل بلوك `async with self.db.begin_nested():` في الـ24 `service.py` المتأثرة (لو مفيش commit موجود بالفعل بعده في نفس الـmethod) — يطابق بالضبط نص القاعدة الأصلية غير المكتمل التنفيذ.

**الحالة:** ⏳ **متوقف بالكامل. صفر تعديل إضافي. مستني قرارك.**

---

## [2026-08-13] موافقة المستخدم على الحل + تنفيذ كامل عبر الـ24 دومين (صفر تحقق حي لسه — الجلسة اتقطعت قبل التحقق)

**القرار:** موافقة على إضافة `await self.db.commit()` صريح فورًا بعد كل بلوك `begin_nested()` في الـ24 `service.py` (شامل إكمال `ai_governance` اللي كانت جزئية). **شرط إلزامي مطلوب بعد التنفيذ:** تحقق DB-level (مش status code) لكل الـ24 دومين من غير استثناء، جدول واحد شامل. **هذا التحقق لسه لم يبدأ — الجلسة اتقطعت فور الانتهاء من التطبيق الميكانيكي، قبل أي إعادة تشغيل أو تحقق.**

### اكتشاف حرج إضافي أثناء التنفيذ — `finance.transfer/swap` لازم يبطلوا الـself-commit

أثناء إضافة الـcommit لـ`commerce.checkout`، لقيت إن `finance.transfer()` بتتنادى من **جوه** بلوك `begin_nested()` بتاعة `commerce.checkout` نفسها (وكذلك 17 موضع تاني عبر academy, digital_twin, insurance×2, iot, realestate, saas×2, service_marketplace×2, social×3, sovereign_entities×2, tourism_sports×2, transport×2). في نفس الوقت، `finance.transfer/swap/mint_currency` نفسها لازم تعمل commit خاص بيها لما تتنادى **مباشرة** (مش متداخلة) من `finance/router.py` — تعارض معماري حقيقي (نفس method، سياقين مختلفين).

**الحل المطبَّق:**
1. `finance/repository.py` — `AuditLogRepository.create` (سطر 254): `commit()` → `flush()` (كانت السبب المباشر — بتتنادى بعد أي `begin_nested()` في `transfer/swap/mint_currency`، وكانت بتقفل أي `begin_nested()` خارجي لو `finance.transfer()` اتنادت من جواه).
2. `finance/service.py` — `transfer()` و`swap()`: **صفر commit ذاتي** (اتشال، بعد ما كان اتضاف بالغلط مؤقتًا). `mint_currency()` **احتفظت بالـcommit الذاتي بتاعها** (مؤكَّد إنها مش بتتنادى نستد من أي دومين تاني — استدعاء top-level بس عبر `finance/router.py`).
3. `finance/router.py` — أُضيف `await db.commit()` صريح بعد `service.transfer(...)` و`service.swap(...)` في `transfer_funds`/`swap_currencies` (الـcommit اللي كان مفروض يحصل من جوه الـservice، دلوقتي مسؤولية الـrouter بصفته أعلى نقطة في الطلب).

**النتيجة المنطقية:** أي دومين بينادي `self.finance.transfer(...)` من جوه `begin_nested()` بتاعته دلوقتي **مش هيتقفلش** (لأن `transfer()` نفسها بقت flush-only بالكامل)، وأي commit بيتضاف لنهاية method الدومين الحاضن هيغطي كتابات `finance.transfer()` كمان تلقائيًا (لأنها كلها في نفس الـsession).

### التطبيق الكامل — 24 دومين، كل الـmethods المؤكَّدة من المرحلة 1 + المتفرعة

**لكل method: أُضيف `await self.db.commit()` مباشرة بعد آخر بلوك `begin_nested()` في نفس التسلسل، أو (لو الـ`return`/كود تاني كان جوه البلوك نفسه) تم **إعادة هيكلة بسيطة** (dedent الجزء اللي بعد آخر كتابة DB، ونقل الـ`return` برّه البلوك) — لضمان الـcommit يحصل **بعد** ما بلوك الـSAVEPOINT يتقفل طبيعي، مش جواه.**

| الدومين | الـmethods المُعدَّلة | ملاحظات خاصة |
|---|---|---|
| `academy` | `enroll_in_course` | commit بعد البلوك، قبل استدعاء `_register_affiliate_commission` (اللي هيكراش بباج منفصل موجود مسبقًا) |
| `affiliate` | `withdraw_commissions`, `bulk_release_commissions` | `withdraw_commissions`: الـcommit اتنقل لبعد `update_affiliate_stats` (استدعاء منفصل خارج البلوك، بيستخدم repo method بقت flush-only) عشان يتغطى برضه |
| `agritech` | `register_harvest`, `register_bio_yield` | مباشر |
| `ai_agents` | `resolve_approval` | مباشر |
| `ai_governance` | `set_quota`, `update_rate_limits`, `check_and_consume`, `reset_quotas` | `check_and_consume`: الـ`return False` المبكر عند تجاوز الحصة **مقصود بلا commit** (rollback صحيح لعملية مرفوضة بالكامل) |
| `commerce` | `checkout`, `_restore_inventory` | `checkout`: الـcommit بعد `_create_audit_log` (بعد البلوك)، يغطي `finance.transfer` الداخلية كمان |
| `communications` | `send_notification`, `send_mail` | مباشر (ملاحظة: الاتنين لسه معطوبين ببق منفصل — `_get_user_tenant`→`UserRepository.get_user` غير موجود، `AttributeError` قبل الوصول للبلوك أصلًا) |
| `digital_twin` | `get_or_create_twin`, `setup_time_capsule` | `interact_with_twin`: **صفر تعديل** — `create_interaction_log` (بعد البلوك) لسه بتعمل commit ذاتي (مش من ضمن المؤكَّدين)، بيغطي كل حاجة تلقائيًا |
| `employment` | `create_contract` | commit قبل `_register_affiliate_commission` (هيكراش، باج منفصل) |
| `health` | `get_or_create_profile`, `update_profile`, `process_biometric_data`, `book_appointment`, `create_consultation`, `create_prescription`, `trigger_emergency`, `create_facility` | **إعادة هيكلة في 5 methods** (`update_profile`, `process_biometric_data`, `create_consultation`, `create_prescription`, `create_facility`) — الـ`return` كان جوه البلوك |
| `insurance` | `create_policy`, `subscribe`, `submit_claim`, `review_claim`, `create_pension`, `create_employee_insurance_profile` | `create_policy`, `create_pension`, `create_employee_insurance_profile`: إعادة هيكلة (`return` جوه البلوك) |
| `invitations` | `create_invitation`, `accept_invitation`, `chat_with_ai`, `create_lead`, `create_interaction`, `create_campaign`, `create_ticket`, `add_ticket_comment`, `track_behavior` | `create_invitation`: الـcommit بعد استدعاء `update_invitation` الشرطي (خارج البلوك، repo method بقت flush-only) |
| `logistics` | `create_warehouse`, `create_warehouse_zone`, `receive_inventory`, `issue_inventory`, `adjust_inventory`, `create_equipment`, `create_equipment_maintenance`, `generate_forecast` | `create_warehouse_zone`: إعادة هيكلة (`return` جوه البلوك) |
| `manufacturing` | كل الـ12 method (`create_facility` → `restock_spare_part`) | `start_production`, `analyze_and_schedule_maintenance`: الـcommit بعد استدعاء `create_invoice` (خارج البلوك) |
| `privacy` | `process_erasure_request` | مباشر |
| `projects` | `approve_contribution`, `complete_milestone` | إعادة هيكلة (الاتنين، `return` جوه البلوك) |
| `realestate` | `buy_fractional_ownership`, `rent_unit` | إعادة هيكلة كبيرة (الميثودين بالكامل تقريبًا كانوا جوه البلوك) |
| `saas` | `create_subscription`, `process_auto_renewals`, `pay_invoice` | `process_auto_renewals`: الـcommit **جوه اللوب**، بعد كل بلوك تجديد فردي (عزل صحيح بين الاشتراكات). `pay_invoice`: إعادة هيكلة (`return` جوه `try`/`async with`) |
| `service_marketplace` | `purchase_service`, `renew_subscription`, `purchase_addon` | `renew_subscription`, `purchase_addon`: إعادة هيكلة |
| `social` | `send_digital_gift`, `request_physical_gift`, `subscribe_group_to_plan` | إعادة هيكلة (الثلاثة) |
| `sovereign_entities` | `deposit_to_entity_wallet`, `transfer_from_entity` | مباشر |
| `tourism_sports` | `book_program`, `purchase_event_ticket`, `place_transfer_bid` | مباشر |
| `transport` | `book_trip`, `create_delivery`, `pay_delivery` | مباشر |
| `zamakana` | `pledge_time`, `fulfill_pledge` | مباشر |

### باجات جانبية إضافية اتكشفت أثناء القراءة الدقيقة (موثَّقة فقط، صفر إصلاح، خارج النطاق)

- **`_register_affiliate_commission`/`register_commission` غير موجودة على `AffiliateService`** — تتكرر في أماكن أكتر من المتوقَّع: `academy.enroll_in_course`, `digital_twin.get_or_create_twin`/`interact_with_twin`, `employment.create_contract`, `manufacturing.create_facility`, `realestate.buy_fractional_ownership`/`rent_unit`, `invitations` (عدة methods)، `tourism_sports.book_program`, `transport.book_trip`/`pay_delivery`, `zamakana.fulfill_pledge`. بتكراش بـ`AttributeError` بعد أي commit ناجح (يعني الكتابة الأساسية بتتحفظ، بس الجزء الخاص بعمولة الإحالة بيفشل).
- **`AIGovernanceService(self.db)` بمعامل واحد بدل اتنين** — نفس فئة باج الـ16 دومين، لكن **لـ`AIGovernanceService` تحديدًا مش `FinanceService`**، ولوحظ في أماكن جديدة تمامًا: `insurance.submit_claim` (متبلوعة جوه try/except، فشل صامت)، `invitations.chat_with_ai` (غير محمية، كراش مباشر)، `logistics.generate_forecast` (غير محمية)، `manufacturing.start_production`/`analyze_and_schedule_maintenance` (غير محمية)، `tourism_sports.place_transfer_bid` (غير محمية). **نطاق أوسع من الموثَّق سابقًا — يستاهل جرد منفصل لاحقًا.**
- **`self.finance.create_invoice` غير موجودة** (الصح `self.invoicing_service.create_invoice`) — `transport.book_trip`, `transport.pay_delivery`. كراش مباشر.
- **`health/service.py`** — 5 استدعاءات `audit_log(...)` بترجع لمتغيرات `job`/`tenant_id` غير معرَّفة (نفس الباج الموثَّق سابقًا في الجرد الأصلي، أعمّ مما كان موثَّق).
- **`communications._get_user_tenant`** → `UserRepository.get_user` غير موجودة (الصح `get_by_id`) — بتكسر `send_notification`/`send_mail` بالكامل قبل الوصول لأي بلوك `begin_nested`.

هذه كلها **باجات موجودة مسبقًا في الكود، غير متعلقة بتعديلات الجلسة دي، مؤكَّدة بالقراءة المباشرة أثناء تتبّع كل method** — صفر إصلاح، موثَّقة فقط زي باقي الاكتشافات الجانبية بالجلسة.

### المتبقي (لم يبدأ بعد — الجلسة اتقطعت هنا)

1. **Sweep نهائي بـ`grep`** للتأكد إن كل بلوك `begin_nested()` في الـ24 دومين له commit مقابل (أو مغطّى بتصميم زي `interact_with_twin`)، وصفر بلوك اتفاته.
2. **إعادة تشغيل `uvicorn`** من الصفر، فحص لوج نظيف.
3. **تحقق DB-level لكل الـ24 دومين بلا استثناء** (زي ما طلبت بالظبط) — طلب فعلي + `SELECT` مستقل بعده لكل method، **شامل إعادة تحقق `finance.transfer`/`ai_agents.resolve_approval`/`ai_governance.reset_agent_quotas`** (اللي اتفحصوا قبل التعديل الأخير على `finance`، لازم تحقق تاني بعده).
4. **جدول التحقق الشامل** (دومين | method | نجح DB-level؟).
5. **التنظيف النهائي + commit واحد معزول** (Phase 16 partial + finance/transaction session sama).

**الحالة:** ⏳ **التطبيق الميكانيكي لكل الـ24 دومين مكتمل. صفر تحقق حي حتى الآن. الجلسة متوقفة، مستني تعليماتك للمتابعة.**

---

## [2026-08-13] استئناف — ترتيب أولويات معدَّل من المستخدم + تنفيذ الأولوية 1 و2

**الترتيب المتفق عليه:** (1) إعادة تحقق `finance.transfer` من الصفر بالكامل أولًا (أعلى خطورة مالية) (2) sweep + restart + لوج نظيف (3) تحقق DB-level للـ24 دومين، بتصنيف: الـmethods اللي اتعملها إعادة هيكلة → ديف قبل/بعد يُعرض للمراجعة **قبل** التحقق الحي، مش بعده. باقي الـmethods → تحقق DB-level مباشر (4) الباجات الجانبية → قسم منفصل بارز في `PROGRESS_LOG.md` كـ"دين تقني منهجي ثاني". **صفر commit نهائي لحد ما 1-3 تخلص وتتأكد بالكامل.**

### باج حقيقي اتلقط فورًا: `IndentationError` في `saas/service.py`

أول محاولة `uvicorn restart` فشلت فورًا (`Traceback` في startup نفسه، مش عند طلب): `saas/service.py:188` — `logger.info(...)` بإزاحة زايدة (نتيجة تعديل `Edit` سابق أثّر على السطر اللي بعده بالغلط). **اتصلح فورًا** (إزاحة السطر اتظبطت لتطابق `results.append` اللي قبله). بعدها: `py_compile` على كل الـ24 ملف `service.py` + `finance/repository.py` + `finance/router.py` → **صفر أخطاء syntax في كل الباقي**.

### إعادة تشغيل uvicorn — لوج نظيف

`Application startup complete`، `HTTP 200` على `/docs`، **صفر `Traceback`**.

### الأولوية 1 — إعادة التحقق الكامل على `finance.transfer`/`swap` من الصفر

أُعيد ضبط محفظتي الاختبار لأرقام واضحة (`user 29 → 100 MR_USDT`, `user 30 → 0`) قبل البدء، لضمان نتيجة نظيفة لا تعتمد على أي رصيد قديم.

**1) `GET /finance/balances` (قبل أي تحويل):** `{"MR_USDT":100.0}` — مطابق.

**2) `POST /finance/transfer` #1 — 30 MR_USDT:**
```
{"tx_hash":"TX-7534E1E225A4","status":"COMPLETED",...}   HTTP 200
```
تحقق DB مستقل:
```sql
wallets: user 29 → {"MR_USDT": 70.0}  |  user 30 → {"MR_USDT": 30.0}
transactions: tx_hash=TX-7534E1E225A4, sender=29, receiver=30, amount=30, COMPLETED
```
مطابق (100-30=70، 0+30=30).

**3) `POST /finance/transfer` #2 — فورًا بعد الأول، 15 MR_USDT (edge case التكرار الفوري):**
```
{"tx_hash":"TX-658956BC4521","status":"COMPLETED",...}   HTTP 200
```
تحقق DB مستقل:
```sql
wallets: user 29 → {"MR_USDT": 55.0}  |  user 30 → {"MR_USDT": 45.0}
transactions (لكل sender=29): 4 صفوف (2 قديمة من التحقق الأول + 2 جديدة)، كلها COMPLETED
```
مطابق (70-15=55، 30+15=45). **صفر تكرار/صف يتيم.**

**4) `POST /finance/swap` — اختبار إضافي (نفس التعديل المعماري بالظبط، لم يُختبر حيًا من قبل): 10 MR_USDT → MR_POUND:**
```
{"from_amount":10.0,"to_amount":500.0,"tx_hash":"SWAP-IN-1A690570B903"}   HTTP 200
```
تحقق DB مستقل:
```sql
wallets: user 29 → {"MR_USDT": 45.0, "MR_POUND": 500.0}
transactions: SWAP-OUT (10 MR_USDT) + SWAP-IN (500 MR_POUND)، الاتنين COMPLETED
```
مطابق (55-10=45 MR_USDT، 10/0.02=500 MR_POUND بالسعر الصحيح).

**فحص اللوج بعد الأربعة طلبات:** صفر `Traceback`، صفر `InvalidRequestError`، صفر `[ERROR]`.

**الخلاصة:** النتيجة القديمة (70/55/45 قبل إعادة الهيكلة) **كانت صدفة** (زي ما تأكَّد سابقًا) — **دلوقتي نفس الأرقام (55/45) مؤكَّدة بالتصميم**: `finance/repository.py`'s `AuditLogRepository.create` (flush)، `finance/service.py`'s `transfer/swap` (صفر commit ذاتي)، `finance/router.py`'s commit صريح بعد كل استدعاء — الثلاثة بيشتغلوا مع بعض صح، مؤكَّد بـ3 عمليات مالية حقيقية متتالية + عملية swap إضافية.

**الحالة:** ✅ **الأولوية 1 مكتملة بالكامل ومؤكَّدة.** ✅ **الأولوية 2 (sweep/restart/لوج نظيف) مكتملة.** ⏳ التالي: الأولوية 3 (عرض ديف الـmethods المعاد هيكلتها للمراجعة، قبل التحقق الحي عليها).

---

## [2026-08-13] الأولوية 3 — تصحيح تصنيف "إعادة الهيكلة" + عرض الديف دومين دومين (بدأ بـ`realestate`)

### تصحيح: القائمة الصحيحة لـ"إعادة هيكلة حقيقية" (تحريك `return`) = 16 method بالظبط

راجعت كل الـ`Edit` اللي اتعملت بدقة قبل ما أعرض أي ديف. **3 methods كانت متصنَّفة غلط في الجدول السابق كـ"إعادة هيكلة"** (`social.send_digital_gift`, `request_physical_gift`, `subscribe_group_to_plan`) — الـ`return` فيهم كان أصلًا **برّه** البلوك في الكود الأصلي؛ اللي حصل كان مجرد إضافة `commit()` قبله، مش نقل. اتصحّحت.

**القائمة الصحيحة (16 method، تحريك `return` فعلي):**
- **مجموعة أ (11، مخاطرة شبه صفرية — صفر شرط بين آخر كتابة والـ`return`):** `health.update_profile`, `health.create_consultation`, `health.create_prescription`, `insurance.create_policy`, `insurance.create_pension`, `insurance.create_employee_insurance_profile`, `logistics.create_warehouse_zone`, `service_marketplace.renew_subscription`, `service_marketplace.purchase_addon` (+ `health.process_biometric_data`, `health.create_facility` — مجموعة ب تحت)
- **مجموعة ب (2، الـreturn عبارة عن dict مبني من متغيّرات محلية، صفر مشكلة scope في بايثون):** `health.process_biometric_data`, `health.create_facility` (الأخيرة فيها باج NameError موجود مسبقًا (`job`/`tenant_id` غير معرَّفين) — بتكراش قبل الوصول للـreturn في الحالتين، قبل وبعد)
- **مجموعة ج (3، فيها شروط/`raise` حقيقية قبل الـreturn، لكن كلها بتخرج بـexception مش بتغيّر مسار النجاح):** `projects.approve_contribution`, `projects.complete_milestone`, `saas.pay_invoice`
- **مجموعة د (2، الأكبر — `realestate`، تفصيل كامل تحت):** `buy_fractional_ownership`, `rent_unit`

### `realestate.buy_fractional_ownership` — الديف الكامل

**الجزء الثابت (سطور 213-290، من `async with begin_nested()` لحد `_send_notification`) — متلمسش، نفس الترتيب/الشروط/الـraise بالحرف:** `get_unit` → فحص توفر → فحص نسبة الملكية → `ai.execute_agent_action` → `_check_ai_governance` → `finance.transfer` (try/except `InsufficientBalanceError`) → `invoicing.create_invoice` → `_register_affiliate_commission` (بتكراش، باج معروف) → `create_ownership` → `update_unit_availability` الشرطي → `event_bus.publish` → `audit_log` → `_send_notification`.

**الجزء اللي اتغيّر (نهاية الـmethod فقط):**
```python
# قبل
            await self._send_notification(...)
            if idempotency_key:
                acquisition_date = cast(datetime, ownership.acquisition_date)
                result_data = {...}
                await self._store_idempotency(idempotency_key, result_data)
            return ownership          # ← كان جوه async with

# بعد
            await self._send_notification(...)
        await self.db.commit()        # ← برّه async with دلوقتي
        if idempotency_key:
            acquisition_date = cast(datetime, ownership.acquisition_date)
            result_data = {...}
            await self._store_idempotency(idempotency_key, result_data)
        return ownership
```
**اللي اتحرك:** `_store_idempotency` (كتابة Redis، مش DB) + `return` بس. **صفر شرط اتحرك، صفر raise اتلمس.**

**التأثير السلوكي:** لو `_store_idempotency` فشلت (Redis)، قبل كده كانت بتلغي الشراء بالكامل (rollback). دلوقتي الشراء بيفضل محفوظ، الفشل بيأثر بس على تخزين مفتاح idempotency. **تحسين مقصود، مش عرضي.**

### `realestate.rent_unit` — الديف الكامل (أهم من الأول)

```python
# قبل (كله جوه async with)
            contract = await self.repo.create_rental_contract(...)
            first_payment = monthly_rent * Decimal(1)
            await self.invoicing.create_invoice(...)
            await self._register_affiliate_commission(tenant_user_id, tenant_id, first_payment)   # ← بتكراش دايمًا (باج معروف)
            await audit_log(**{...})
            if idempotency_key:
                ... await self._store_idempotency(idempotency_key, result_data)
            return contract

# بعد
            contract = await self.repo.create_rental_contract(...)
            first_payment = monthly_rent * Decimal(1)
            await self.invoicing.create_invoice(...)
        await self.db.commit()                                                                      # ← برّه SAVEPOINT
        await self._register_affiliate_commission(tenant_user_id, tenant_id, first_payment)          # ← لسه بتكراش، بعد الـcommit
        await audit_log(**{...})
        if idempotency_key:
            ... await self._store_idempotency(idempotency_key, result_data)
        return contract
```

**🔴 تأثير سلوكي حقيقي وموجود فعليًا الآن (مش نظري):**
- **قبل التعديل:** `_register_affiliate_commission` بتكراش (بتكراش دايمًا، باج موجود مسبقًا) → الـSAVEPOINT بيعمل rollback لعقد الإيجار والفاتورة → `rent_unit` بترجع `500` **وصفر أثر في الـDB** (فشل كامل ونظيف).
- **بعد التعديل:** عقد الإيجار والفاتورة بيتسجّلوا فعليًا (commit ناجح) **قبل** ما `_register_affiliate_commission` تكراش → العميل لسه بياخد `500`، **لكن العقد يبقى موجود فعليًا في قاعدة البيانات** (نجاح صامت خلف رسالة فشل).
- **السبب:** نقل `_register_affiliate_commission` من جوه الـSAVEPOINT لبرّه، عشان الـcommit يحصل قبلها.
- **التقييم:** العقد فعلي وحقيقي (مالك أجّر وحدة) — إبقاؤه أفضل من فقدانه بسبب باج غير متعلق بمنطق الإيجار نفسه. لكن تجربة المستخدم مربكة (`500` رغم نجاح العملية فعليًا) لحد ما باج الـaffiliate يتصلح في جلسة منفصلة.

**الحالة:** ⏳ عرض `realestate` كامل. **مستني موافقة/تعديل قبل الانتقال لـ`health` (5 methods).**

---

## [2026-08-13] قرار المستخدم على `rent_unit` — ثم تصحيح جوهري بعد التحقق الفعلي من كل المواقع

**قرار المستخدم الأصلي:** اعتبار مشكلة `_register_affiliate_commission` في `rent_unit` قرار منتجي يحتاج معالجة فورية (مش توثيق وتأجيل) — لفّها في `try/except Exception` محلي بعد الـcommit، تسجّل warning بدل ما ترجّع 500. **مطلوب كقاعدة عامة على كل الـ10+ موقع المكتشفة سابقًا** (academy, digital_twin, employment, manufacturing, invitations, tourism_sports, transport, zamakana) قبل التطبيق، مع عرض القائمة الكاملة أولًا.

### 🔴 تصحيح جوهري — القائمة الأصلية كانت غير دقيقة، اتحقّقت من كل موقع فعليًا قبل التطبيق

قبل ما أطبّق أي حاجة، فتحت تعريف `_register_affiliate_commission` في **كل** الدومينات المذكورة (مش استنتاج من الاسم بس). النتيجة تناقض الافتراض اللي بُني عليه التوثيق السابق طول الجلسة:

**10 دومين من أصل 12 عندهم الـhelper method نفسها ملفوفة بالفعل بـ`try/except Exception` (بتعمل `logger.error(...)` وتكمل، صفر crash فعلي)، من الأساس، قبل أي تعديل بتاعنا النهاردة:**
`realestate` (`service.py:573-586`), `employment` (`:96-116`), `manufacturing` (`:65-78`), `invitations` (`:67-80`), `tourism_sports` (`:494-...`), `transport` (`:574-586`), `zamakana` (`:642-...`), `insurance` (`:86-99`), `arbitration_syndicates` (`:557-...`), `tenders_auctions` (`:478-...`).

**يترتب على كده:** `realestate.rent_unit` **معندهاش مشكلة الـ500 اللي اتوصفت في القسم السابق** — التحليل ده كان **غلط**، مبني على افتراض عام (من ملاحظة جانبية في جرد المرحلة 1: "`register_commission` غير موجودة على `AffiliateService`") من غير التحقق المباشر من كل تعريف `_register_affiliate_commission` لوحده. **`rent_unit` تفضل زي ما هي، صفر تعديل إضافي مطلوب عليها.**

**`academy`:** مش من ضمن الباج ده أصلًا — بتستخدم `affiliate_service.track_referral(...)` (method **حقيقية موجودة**، مش `register_commission`)، وملفوفة بـ`try/except` في `academy/service.py` نفسها. **تصنيف خاطئ سابق، اتصحح.**

### القائمة الصحيحة النهائية — دومينين بس فعليًا معرَّضين (صفر try/except، كراش حقيقي)

| الدومين | تعريف الـhelper | استدعاءات متأثرة |
|---|---|---|
| `digital_twin` | `service.py:59-100` — **صفر `try/except`** | `get_or_create_twin` (سطر 118)، `interact_with_twin` (سطر 184-190) |
| `service_marketplace` | `service.py:483-495` — **صفر `try/except`** | `purchase_service` (سطر 215) |

**الحالة:** ⏳ التصحيح موثَّق. **مستني تأكيد المستخدم قبل تطبيق الـtry/except على الدومينين دول بس** (بنفس نمط الـ10 دومين الآمنين بالفعل، جوه تعريف الـhelper نفسها — بيصلح كل استدعاءاتها في الدومين مرة واحدة). صفر تعديل تاني على `realestate`/`academy`/باقي الدومينات المذكورة غلطًا.

### ✅ الإصلاح المطبَّق — `digital_twin` و`service_marketplace`

**`digital_twin/service.py`:**
- أُضيف `from app.core.logging_conf import logger` (الملف مكنش بيستورد `logger` أصلًا).
- `_register_affiliate_commission` (سطر 59-100): الجسم كامل اتلف في `try:`، مع `except Exception as e: logger.error(f"Affiliate registration failed: {e}")` في الآخر. كل الـ`return` المبكرة (منطق العمل الطبيعي — مفيش referrer، إلخ) فضلت زي ما هي جوه الـ`try` (بترجع عادي، مش بتتلمس بالـ`except`).

**`service_marketplace/service.py`:**
- `logger` كانت متستوردة بالفعل. `_register_affiliate_commission` (سطر 483-495): نفس النمط بالحرف — الجسم كامل جوه `try/except Exception`.

**تأكيد `py_compile`:** `exit code: 0` على الملفين، صفر أخطاء syntax.

**صفر تعديل على `realestate` أو `academy`** — زي المتفق، كانوا آمنين من الأساس.

**الحالة:** ✅ **الإصلاح مكتمل ومؤكَّد syntax-wise.** التالي: عرض ديف `health` (5 methods) — الخطوة اللي كانت قايمة قبل استطراد `realestate`/الـaffiliate.

---

## [2026-08-13] دومين 2: `health` — الديف الكامل بالحرف لكل الـ5 methods (راجعها المستخدم، وافق على الكل)

**توجيه المستخدم لهذا الدومين:** عرض before/after **بالحرف** (مش وصف) لكل method، معيار المراجعة اترفع بعد تجربة `realestate` ("الشك ظهر بعد فحص فعلي مش قبله") — يعني معيار "لو مفيش شك واضح" مبقاش كافي، لازم ديف كامل لكل الـ16 method بلا استثناء، في دفعات 2-3.

### `update_profile` — صفر شرط
```python
# قبل
    async def update_profile(self, user_id: int, data: Dict[str, Any]) -> MedicalProfile:
        """تحديث الملف الطبي."""
        async with self.db.begin_nested():
            profile = await self.repo.update_medical_profile(user_id, **data)
            return profile

# بعد
    async def update_profile(self, user_id: int, data: Dict[str, Any]) -> MedicalProfile:
        """تحديث الملف الطبي."""
        async with self.db.begin_nested():
            profile = await self.repo.update_medical_profile(user_id, **data)
        await self.db.commit()
        return profile
```
**✅ موافَق عليه.**

### `create_consultation` — صفر شرط
```python
# قبل
    async def create_consultation(self, data: Dict[str, Any]) -> HealthConsultation:
        """إنشاء استشارة طبية بعد الموعد."""
        async with self.db.begin_nested():
            consultation = await self.repo.create_consultation(**data)
            return consultation

# بعد
    async def create_consultation(self, data: Dict[str, Any]) -> HealthConsultation:
        """إنشاء استشارة طبية بعد الموعد."""
        async with self.db.begin_nested():
            consultation = await self.repo.create_consultation(**data)
        await self.db.commit()
        return consultation
```
**✅ موافَق عليه.**

### `create_prescription` — `raise` واحد قبل الكتابة، بيخرج بـexception عادي
```python
# قبل
    async def create_prescription(self, data: Dict[str, Any]) -> Prescription:
        """إنشاء روشتة طبية."""
        async with self.db.begin_nested():
            consultation = await self.repo.get_consultation(cast(int, data.get("consultation_id")))
            if not consultation:
                raise NotFoundError("الاستشارة غير موجودة")
            prescription_data = {
                "tenant_id": consultation.tenant_id,  # type: ignore
                "consultation_id": consultation.id,
                "patient_id": data.get("patient_id"),
                "medications": data.get("medications"),
                "doctor_notes": data.get("doctor_notes"),
                "pharmacy_store_id": data.get("pharmacy_store_id"),
                "status": "ISSUED"
            }
            prescription = await self.repo.create_prescription(**prescription_data)
            return prescription

# بعد
    async def create_prescription(self, data: Dict[str, Any]) -> Prescription:
        """إنشاء روشتة طبية."""
        async with self.db.begin_nested():
            consultation = await self.repo.get_consultation(cast(int, data.get("consultation_id")))
            if not consultation:
                raise NotFoundError("الاستشارة غير موجودة")
            prescription_data = {
                "tenant_id": consultation.tenant_id,  # type: ignore
                "consultation_id": consultation.id,
                "patient_id": data.get("patient_id"),
                "medications": data.get("medications"),
                "doctor_notes": data.get("doctor_notes"),
                "pharmacy_store_id": data.get("pharmacy_store_id"),
                "status": "ISSUED"
            }
            prescription = await self.repo.create_prescription(**prescription_data)
        await self.db.commit()
        return prescription
```
الـ`raise` نفس السطر بالحرف، نفس الموضع، في الحالتين. **✅ موافَق عليه.**

### `process_biometric_data` — فيها شرطين، **branching على بيانات بس، صفر تأثير على مسار الخروج**
```python
# قبل
    async def process_biometric_data(self, user_id: int, data: Dict[str, Any]) -> Dict:
        """معالجة البيانات الحيوية الواردة من الأجهزة أو التطبيقات."""
        profile = await self.get_or_create_profile(user_id)
        async with self.db.begin_nested():
            log_data = {
                "medical_profile_id": profile.id, "source": data.get("source"),
                "device_id": data.get("device_id"), "aggregated_metrics": data.get("aggregated_metrics"),
                "recorded_at": data.get("recorded_at", datetime.utcnow())
            }
            log = await self.repo.create_biometric_log(**log_data)
            metrics = data.get("aggregated_metrics", {})
            heart_rate = metrics.get("heart_rate", 70)
            health_delta = 0
            if heart_rate < 50 or heart_rate > 110:
                health_delta = -5
            elif 50 <= heart_rate <= 60 or 100 <= heart_rate <= 110:
                health_delta = -2
            else:
                health_delta = 1
            new_score = max(0, min(100, profile.health_score + health_delta))  # type: ignore
            await self.repo.update_medical_profile(user_id, health_score=new_score)
            prognosis = None
            if len(metrics) >= 3:
                prognosis = await self._call_ai_prognosis(cast(int, profile.id), metrics)
            return {
                "status": "success", "log_id": log.id,
                "new_health_score": new_score,
                "prognosis_id": prognosis.id if prognosis else None
            }

# بعد
    async def process_biometric_data(self, user_id: int, data: Dict[str, Any]) -> Dict:
        """معالجة البيانات الحيوية الواردة من الأجهزة أو التطبيقات."""
        profile = await self.get_or_create_profile(user_id)
        async with self.db.begin_nested():
            log_data = {
                "medical_profile_id": profile.id, "source": data.get("source"),
                "device_id": data.get("device_id"), "aggregated_metrics": data.get("aggregated_metrics"),
                "recorded_at": data.get("recorded_at", datetime.utcnow())
            }
            log = await self.repo.create_biometric_log(**log_data)
            metrics = data.get("aggregated_metrics", {})
            heart_rate = metrics.get("heart_rate", 70)
            health_delta = 0
            if heart_rate < 50 or heart_rate > 110:
                health_delta = -5
            elif 50 <= heart_rate <= 60 or 100 <= heart_rate <= 110:
                health_delta = -2
            else:
                health_delta = 1
            new_score = max(0, min(100, profile.health_score + health_delta))  # type: ignore
            await self.repo.update_medical_profile(user_id, health_score=new_score)
            prognosis = None
            if len(metrics) >= 3:
                prognosis = await self._call_ai_prognosis(cast(int, profile.id), metrics)
        await self.db.commit()
        return {
            "status": "success", "log_id": log.id,
            "new_health_score": new_score,
            "prognosis_id": prognosis.id if prognosis else None
        }
```
**تحليل الشرطين (مطلوب توضيح صريح):**
- الشرط الأول (`heart_rate`) بيحدد قيمة `health_delta` بس — الفروع التلاتة كلها بتكمل لنفس السطر التالي (`new_score = ...`)، مفيش فرع بيعمل `return`/`raise`/`break`. **branching على بيانات بس.**
- الشرط التاني (`len(metrics) >= 3`) بيحدد قيمة `prognosis` بس (None أو كائن)، نفس الشيء.
- الاتنين في نفس المكان بالضبط قبل الـ`return` في الحالتين. `log`, `new_score`, `prognosis` متغيّرات في scope الـfunction (مش scope منفصل لـ`async with` في بايثون) — قيمهم بتفضل صحيحة برّه البلوك. **صفر تغيير في منطق التحكم، صفر "early-return validation" اتلمس.**

**✅ موافَق عليه من المستخدم — كل الـ5 methods في `health` تمت الموافقة عليها.**

**الحالة:** ✅ **دومين `health` مكتمل المراجعة والموافقة بالكامل.** التالي: `insurance` (3) + `logistics` (1) كدفعة، بنفس مستوى التفصيل (before/after بالحرف).

---

## [2026-08-13] دفعة 2: `insurance` (3 methods) + `logistics` (1 method) — الديف الكامل بالحرف (راجعها المستخدم، وافق على الكل)

### `insurance.create_policy` — صفر شرط
```python
# قبل
    async def create_policy(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> InsurancePolicy:
        """إنشاء بوليصة تأمين جديدة (للمشرفين فقط)."""
        async with self.db.begin_nested():
            policy = await self.repo.create_policy(
                tenant_id=tenant_id,
                created_by=user_id,
                **data
            )
            await audit_log(
                user_id=user_id,
                tenant_id=tenant_id,  # type: ignore
                action="POLICY_CREATED",
                resource_id=policy.id,  # type: ignore
                details={"name": policy.name, "type": policy.policy_type}  # type: ignore
            )
            return policy

# بعد
    async def create_policy(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> InsurancePolicy:
        """إنشاء بوليصة تأمين جديدة (للمشرفين فقط)."""
        async with self.db.begin_nested():
            policy = await self.repo.create_policy(
                tenant_id=tenant_id,
                created_by=user_id,
                **data
            )
            await audit_log(
                user_id=user_id,
                tenant_id=tenant_id,  # type: ignore
                action="POLICY_CREATED",
                resource_id=policy.id,  # type: ignore
                details={"name": policy.name, "type": policy.policy_type}  # type: ignore
            )
        await self.db.commit()
        return policy
```
`audit_log(...)` هنا بمتغيّرات حقيقية (`user_id`/`tenant_id` بارامترات، `policy.name`/`policy.policy_type` من الكائن المُنشأ) — **بعكس `health.create_facility`، مفيش باج `NameError` هنا.** صفر شرط.

### `insurance.create_pension` — نفس النمط، صفر شرط
```python
# قبل
    async def create_pension(self, user_id: int, data: Dict[str, Any]) -> PensionRecord:
        """إنشاء سجل معاش (للمشرفين فقط)."""
        async with self.db.begin_nested():
            pension = await self.repo.create_pension(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="PENSION_CREATED",
                resource_id=pension.id,  # type: ignore
                details={"beneficiary": data.get("beneficiary_id"), "amount": float(data.get("monthly_amount_mrusdt", 0))}
            )
            return pension

# بعد
    async def create_pension(self, user_id: int, data: Dict[str, Any]) -> PensionRecord:
        """إنشاء سجل معاش (للمشرفين فقط)."""
        async with self.db.begin_nested():
            pension = await self.repo.create_pension(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="PENSION_CREATED",
                resource_id=pension.id,  # type: ignore
                details={"beneficiary": data.get("beneficiary_id"), "amount": float(data.get("monthly_amount_mrusdt", 0))}
            )
        await self.db.commit()
        return pension
```

### `insurance.create_employee_insurance_profile` — نفس النمط، صفر شرط
```python
# قبل
    async def create_employee_insurance_profile(self, user_id: int, data: Dict[str, Any]) -> EmployeeInsuranceProfile:
        """إنشاء ملف تأميني للموظف."""
        async with self.db.begin_nested():
            profile = await self.repo.create_employee_profile(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="EMPLOYEE_INSURANCE_PROFILE_CREATED",
                resource_id=profile.id,  # type: ignore
                details={"employee": data.get("user_id")}
            )
            return profile

# بعد
    async def create_employee_insurance_profile(self, user_id: int, data: Dict[str, Any]) -> EmployeeInsuranceProfile:
        """إنشاء ملف تأميني للموظف."""
        async with self.db.begin_nested():
            profile = await self.repo.create_employee_profile(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="EMPLOYEE_INSURANCE_PROFILE_CREATED",
                resource_id=profile.id,  # type: ignore
                details={"employee": data.get("user_id")}
            )
        await self.db.commit()
        return profile
```

### `logistics.create_warehouse_zone` — صفر شرط
```python
# قبل
    async def create_warehouse_zone(
        self, tenant_id: int, warehouse_id: int, data: Dict[str, Any]
    ) -> WarehouseZone:
        async with self.db.begin_nested():
            zone = await self.repo.create_zone(
                tenant_id=tenant_id,  # type: ignore
                warehouse_id=warehouse_id,
                **data
            )
            return zone

# بعد
    async def create_warehouse_zone(
        self, tenant_id: int, warehouse_id: int, data: Dict[str, Any]
    ) -> WarehouseZone:
        async with self.db.begin_nested():
            zone = await self.repo.create_zone(
                tenant_id=tenant_id,  # type: ignore
                warehouse_id=warehouse_id,
                **data
            )
        await self.db.commit()
        return zone
```

**خلاصة الدفعة:** الأربعة methods نفس النمط الأبسط (زي `health.update_profile`/`create_consultation`) — صفر شرط، صفر `raise` إضافي، كتابة واحدة → `audit_log`/`return`.

**✅ موافَق عليها من المستخدم بالكامل — `insurance` (3) + `logistics` (1) خلصوا مراجعة.**

**الحالة:** ⏳ التالي: دفعة 3 — `projects` (2) + `service_marketplace` (2)، بنفس المستوى.

---

## [2026-08-13] دفعة 3: `projects` (2) + `service_marketplace` (2) — الديف الكامل بالحرف

### `projects.approve_contribution` — عدة `raise`، شرط واحد على كتابة إضافية (مش على الخروج)
```python
# قبل
    async def approve_contribution(
        self, contribution_id: int, owner_id: int, tenant_id: int,
        approved: bool, notes: Optional[str] = None
    ) -> Contribution:
        async with self.db.begin_nested():
            contribution = await self.repo.get_contribution(contribution_id, tenant_id)
            if not contribution:
                raise NotFoundError("Contribution not found")
            project = await self.repo.get_project(cast(int, contribution.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to approve this contribution")
            status = "APPROVED" if approved else "REJECTED"
            if approved:
                new_funding = project.current_funding_mrusdt + contribution.equivalent_value_mrusdt  # type: ignore
                await self.repo.update_project(cast(int, project.id), tenant_id, current_funding_mrusdt=new_funding)
            updated = await self.repo.update_contribution(contribution_id, tenant_id, status=status)
            if not updated:
                raise NotFoundError("Contribution not found after update")
            await invalidate_cache(f"project_analytics_{project.id}")
            return updated

# بعد
    async def approve_contribution(
        self, contribution_id: int, owner_id: int, tenant_id: int,
        approved: bool, notes: Optional[str] = None
    ) -> Contribution:
        async with self.db.begin_nested():
            contribution = await self.repo.get_contribution(contribution_id, tenant_id)
            if not contribution:
                raise NotFoundError("Contribution not found")
            project = await self.repo.get_project(cast(int, contribution.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to approve this contribution")
            status = "APPROVED" if approved else "REJECTED"
            if approved:
                new_funding = project.current_funding_mrusdt + contribution.equivalent_value_mrusdt  # type: ignore
                await self.repo.update_project(cast(int, project.id), tenant_id, current_funding_mrusdt=new_funding)
            updated = await self.repo.update_contribution(contribution_id, tenant_id, status=status)
            if not updated:
                raise NotFoundError("Contribution not found after update")
            await invalidate_cache(f"project_analytics_{project.id}")
        await self.db.commit()
        return updated
```
**التحليل:** 3 `raise` (validation، خروج بـexception، نفس المكان بالحرف). الشرط غير الـ`raise` (`if approved`) بيتحكم في كتابة إضافية (`update_project`) بس — `updated` بيتحدد غير شرطي بعده مباشرة. **مسار وصول واحد للـ`return`.**

### `projects.complete_milestone` — نفس البنية بالضبط
```python
# قبل
    async def complete_milestone(self, milestone_id: int, owner_id: int, tenant_id: int, data) -> ProjectMilestone:
        async with self.db.begin_nested():
            milestone = await self.repo.get_milestone(milestone_id, tenant_id)
            if not milestone:
                raise NotFoundError("Milestone not found")
            project = await self.repo.get_project(cast(int, milestone.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to complete this milestone")
            updated = await self.repo.update_milestone(milestone_id, tenant_id, is_completed=True, actual_date=data.actual_date)
            if not updated:
                raise NotFoundError("Milestone not found after update")
            if milestone.funds_to_release > 0:  # type: ignore
                await self.event_bus.publish("project.milestone.completed", {...})
            await invalidate_cache(f"project_analytics_{project.id}")
            return updated

# بعد
    async def complete_milestone(self, milestone_id: int, owner_id: int, tenant_id: int, data) -> ProjectMilestone:
        async with self.db.begin_nested():
            milestone = await self.repo.get_milestone(milestone_id, tenant_id)
            if not milestone:
                raise NotFoundError("Milestone not found")
            project = await self.repo.get_project(cast(int, milestone.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to complete this milestone")
            updated = await self.repo.update_milestone(milestone_id, tenant_id, is_completed=True, actual_date=data.actual_date)
            if not updated:
                raise NotFoundError("Milestone not found after update")
            if milestone.funds_to_release > 0:  # type: ignore
                await self.event_bus.publish("project.milestone.completed", {...})
            await invalidate_cache(f"project_analytics_{project.id}")
        await self.db.commit()
        return updated
```
**التحليل:** نفس نمط `approve_contribution` — 3 `raise`، شرط واحد (`funds_to_release > 0`) بيتحكم في `event_bus.publish` بس (side effect، مش write حرج ولا exit)، `updated` محدد غير شرطي قبله.

### `service_marketplace.renew_subscription` — 2 `raise`، شرط واحد على تنفيذ `finance.transfer`
```python
# قبل
    async def renew_subscription(self, license_id: int, user_id: int) -> ServiceLicense:
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            service = await self.repo.get_service(license_obj.service_id)
            if not service:
                raise NotFoundError("Service not found")
            plan = license_obj.subscription_plan
            base_price = {...}.get(plan, Decimal(0))
            if base_price > 0:
                await self.finance.transfer(sender_id=user_id, receiver_email=await self._get_owner_email(service.tenant_id), currency="MR_USDT", amount=base_price, notes=f"Renewal of service: {service.name}", idempotency_key=f"RENEW-{license_id}-{datetime.utcnow().strftime('%Y-%m')}")
            new_end = (license_obj.subscription_end or datetime.utcnow()) + timedelta(days=365)
            updated = await self.repo.update_license(license_id, subscription_end=new_end, is_active=True)
            return updated

# بعد
    async def renew_subscription(self, license_id: int, user_id: int) -> ServiceLicense:
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            service = await self.repo.get_service(license_obj.service_id)
            if not service:
                raise NotFoundError("Service not found")
            plan = license_obj.subscription_plan
            base_price = {...}.get(plan, Decimal(0))
            if base_price > 0:
                await self.finance.transfer(sender_id=user_id, receiver_email=await self._get_owner_email(service.tenant_id), currency="MR_USDT", amount=base_price, notes=f"Renewal of service: {service.name}", idempotency_key=f"RENEW-{license_id}-{datetime.utcnow().strftime('%Y-%m')}")
            new_end = (license_obj.subscription_end or datetime.utcnow()) + timedelta(days=365)
            updated = await self.repo.update_license(license_id, subscription_end=new_end, is_active=True)
        await self.db.commit()
        return updated
```
**التحليل:** 2 `raise`. الشرط (`base_price > 0`) بيتحكم في هل `finance.transfer` بتتنفذ (اشتراك مجاني vs مدفوع) — منطق عمل حقيقي، لكن مش بيغيّر مسار الخروج: سواء اتنفذت ولا لأ، الكود بيكمل لنفس السطرين (`update_license` ثم `return`). **ملاحظة مهمة:** `finance.transfer()` هنا بتتنادى جوه نفس الـSAVEPOINT، وبقت بلا commit ذاتي (التعديل المعماري الأساسي) — الـcommit هنا بيغطيها صح.

### `service_marketplace.purchase_addon` — نفس البنية + كتابتين إضافيتين بعد الشرط
```python
# قبل
    async def purchase_addon(self, license_id: int, addon_id: int, user_id: int) -> ServiceLicense:
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            addon = await self.repo.get_addon(addon_id, license_obj.tenant_id)
            if not addon:
                raise NotFoundError("Addon not found")
            addon_price = addon.price_mrusdt
            if addon_price > 0:
                await self.finance.transfer(sender_id=user_id, receiver_email=await self._get_owner_email(license_obj.tenant_id), currency="MR_USDT", amount=addon_price, notes=f"Addon purchase: {addon.name}", idempotency_key=f"ADDON-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}")
            purchased = license_obj.purchased_addons or []
            purchased.append(addon_id)
            new_total = license_obj.paid_amount_mrusdt + addon_price
            updated = await self.repo.update_license(license_id, purchased_addons=purchased, paid_amount_mrusdt=new_total)
            await self.repo.create_addon_purchase(license_id=license_id, addon_id=addon_id, price_paid_mrusdt=addon_price, idempotency_key=f"ADDON-PURCHASE-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}")
            return updated

# بعد
    async def purchase_addon(self, license_id: int, addon_id: int, user_id: int) -> ServiceLicense:
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            addon = await self.repo.get_addon(addon_id, license_obj.tenant_id)
            if not addon:
                raise NotFoundError("Addon not found")
            addon_price = addon.price_mrusdt
            if addon_price > 0:
                await self.finance.transfer(sender_id=user_id, receiver_email=await self._get_owner_email(license_obj.tenant_id), currency="MR_USDT", amount=addon_price, notes=f"Addon purchase: {addon.name}", idempotency_key=f"ADDON-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}")
            purchased = license_obj.purchased_addons or []
            purchased.append(addon_id)
            new_total = license_obj.paid_amount_mrusdt + addon_price
            updated = await self.repo.update_license(license_id, purchased_addons=purchased, paid_amount_mrusdt=new_total)
            await self.repo.create_addon_purchase(license_id=license_id, addon_id=addon_id, price_paid_mrusdt=addon_price, idempotency_key=f"ADDON-PURCHASE-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}")
        await self.db.commit()
        return updated
```
**التحليل:** نفس نمط `renew_subscription` — 2 `raise`، شرط مالي واحد (`addon_price > 0`) بيتحكم في `finance.transfer` بس، مسار واحد بعده (`update_license` + `create_addon_purchase` + `return`) بغض النظر عن الشرط.

**خلاصة الدفعة:** الأربعة فيهم `raise`ات validation (آمنة، خروج بـexception زي الأول بالحرف) وشروط بتتحكم في **كتابات إضافية أو استدعاءات مالية شرطية** (مش في مسار الوصول للـ`return` نفسه) — نفس فئة `health.process_biometric_data`، بمنطق عمل بدل حساب بيانات. **صفر مسار بديل للخروج غير المسار الواحد اللي بيوصل للـcommit ثم الـreturn.**

**الحالة:** ⏳ مستني مراجعة/موافقة المستخدم على دفعة 3.

---

## [2026-08-13] موافقة نهائية على كل الـ16 method (شامل `saas.pay_invoice` — آخر واحدة)

`saas.pay_invoice` (فيها `try/except InsufficientBalanceError` حقيقي): الـ`except` لسه بتعمل `raise` بالحرف (rollback صحيح، الكود بعد البلوك — الـcommit والـreturn — مش بيتنفذش في مسار الفشل). الفرق الوحيد: مسار النجاح بيوصل لـ`return invoice` بعد الـcommit بدل قبله. **✅ موافَق عليها.**

**كل الـ16 method (المجموعات أ/ب/ج/د) خلصوا مراجعة وموافقة بالكامل.** ملاحظة المستخدم الإيجابية: `service_marketplace.renew_subscription`/`purchase_addon` بيأكدوا عمليًا إن حل تعارض `finance.transfer` (الأولوية 1) شغال صح مع دومينات تانية بتستدعيها متداخلة، مش بس finance.transfer المباشرة.

---

## [2026-08-13] التحقق الحي الشامل — بدأ بإعادة تحقق النجاحين الكاذبين

### إعادة تشغيل uvicorn نهائية
`py_compile` على كل الـ24 `service.py` + `finance/repository.py` + `finance/router.py` → صفر أخطاء. Restart → `Application startup complete`، صفر `Traceback`، `HTTP 200`.

### `ai_agents.resolve_approval` — إعادة تحقق كاملة
**قبل:** `SELECT status FROM agent_approval_queue WHERE id=1` → `PENDING` (تأكيد إن النتيجة القديمة كانت كاذبة).
**الطلب:** `POST /api/ai/approvals/1/resolve` → `200 {"status":"APPROVED"}`.
**بعد (DB مستقل):** `status=APPROVED`, `human_feedback='post-commit-fix reverification'`, `resolved_at=2026-08-13 06:11:33` — **✅ نجاح حقيقي مؤكَّد.**

### `ai_governance.reset_agent_quotas` — إعادة تحقق كاملة
**قبل:** `SELECT COUNT(*) FROM agent_audit_logs WHERE agent_id=1` → `0`.
**الطلب:** `POST /api/ai-governance/agents/1/quotas/reset` → `204`.
**بعد (DB مستقل):** صف جديد `id=2, agent_id=1, action=RESET_QUOTA, admin_user_id=29, new_value={"current_usage": 0}` — **✅ نجاح حقيقي مؤكَّد.**

### ⚠️ قيد مهم على نطاق التحقق الحي المتبقي

من أصل الـ24 دومين، **13 دومين محجوبين بالكامل عن أي تحقق حي (HTTP) بسبب باج منفصل تمامًا، موثَّق مسبقًا، خارج نطاق الجلسة دي بالكامل** — باج constructor في `FinanceService(db)` (معامل واحد بدل `tenant_id`) في 16 دومين (موثَّق كـ"اكتشاف حرج تاني" وقت العمل على `finance/router.py`). أي endpoint في الدومينات دي بيكراش فورًا وقت إنشاء الـService نفسها (`TypeError`)، **قبل أي وصول لأي كود بتاعنا النهاردة**:

`digital_twin`, `employment`, `health`, `insurance`, `invitations`, `logistics`, `manufacturing`, `projects`, `realestate`, `service_marketplace`, `social`, `tourism_sports`, `transport`.

**الدومينات القابلة للتحقق الحي فعليًا (11):** `finance` ✅ (خطوة 2 + الأولوية 1، مؤكَّد)، `ai_governance` ✅، `ai_agents` ✅ (فوق)، + `academy`, `affiliate`, `agritech`, `commerce`, `communications`, `privacy`, `saas`, `sovereign_entities`, `zamakana` (قيد التنفيذ الآن).

**لهذه الـ13 دومين المحجوبة:** التحقق البديل المتاح هو **مراجعة الكود المباشرة** (اللي اتعملت بالفعل بالتفصيل لكل الـmethods المعاد هيكلتها فيها — `health`, `insurance`, `logistics`, `projects`, `realestate`, `service_marketplace` — بموافقة صريحة على كل واحدة) + التأكيد الميكانيكي (`grep`/`py_compile`) — **مش تحقق DB-level حي**، لأن باج تاني يمنع الوصول أصلًا. هذا القيد **موجود مسبقًا وموثَّق**، مش جديد، ومش نتيجة أي تقصير في الجلسة دي.

**الحالة:** ⏳ جاري التحقق الحي على الـ9 دومين المتبقية القابلة للاختبار.

---

## 🔴 [2026-08-13] تصحيح كبير — نطاق "القابل للتحقق الحي" أصغر بكتير مما قُدِّر، بسبب باجات منفصلة إضافية اتكشفت أثناء المحاولة الفعلية

بدأت التحقق على الـ9 دومين المتبقية (`academy, affiliate, agritech, commerce, communications, privacy, saas, sovereign_entities, zamakana`)، وواحد واحد ظهرت باجات **منفصلة تمامًا عن باج الترانزاكشن**، كل واحدة فئة مختلفة:

| الدومين | السبب | الفئة |
|---|---|---|
| `communications` | `_get_user_tenant` → `UserRepository.get_user` غير موجودة (الصح `get_by_id`) | method غير موجودة |
| `zamakana` | `ZamakanaService.__init__` بينشئ `AIAgentsService(db)` بمعامل واحد بدل اتنين | فئة constructor (زي الـ16 دومين، بس لـ`AIAgentsService` مش `FinanceService`) |
| `sovereign_entities` | `router.py` بيستخدم `tenant_id: int = Depends(get_current_tenant)` ثم بيبعتها مباشرة لـSQL — بترجع كائن `SimpleTenant` مش `int` (نفس باج `finance/router.py` الأصلي، **غير مُصلَح هنا**) | فئة SimpleTenant/type mismatch |
| `academy` | نفس باج `SimpleTenant` بالضبط (`AcademyService(db, tenant_id)`, تأكَّدت بـgrep: 36 استخدام) | نفس الفئة |
| `commerce` | نفس باج `SimpleTenant` بالضبط (`CommerceService(db, tenant_id)`, 12 استخدام) | نفس الفئة |
| `saas` | نفس باج `SimpleTenant` بالضبط (`SaaSControlService(db, tenant_id)`, 17 استخدام) | نفس الفئة |
| `agritech` | **صفر `router.py`** — لا يوجد ملف أصلًا في `app/domains/agritech/` (مؤكَّد بـ`find`) — نفس الاكتشاف الموثَّق سابقًا في `critical-finding-xtenant-systemic.md` ("كود agritech الحقيقي مش معروض بأي router أصلًا") | endpoint غير موجود من الأساس |
| `affiliate` | **مفيش باج** — لكن `withdraw_commissions`/`bulk_release_commissions` بتحتاج صف `Commission` موجود بالفعل، والموديل بتاعه فيه FK إجبارية (`order_id`, `order_item_id`, `product_id`) لجداول `commerce` (`orders`, `order_items`, `products`) — و`commerce` نفسها محجوبة (السطر اللي فوق) فمينفعش نجهزها عبر API، وزرعها بـraw SQL محتاج سلسلة كاملة (طلب → عناصر طلب → منتج) قبل حتى ما نوصل للعمولة نفسها | تعقيد إعداد، مش باج |
| `privacy` | **صفر باج** — `router.py` بيستخدم `current_user.tenant_id` صح (مؤكَّد بـgrep) | ✅ قابل للاختبار فعليًا |

### الخلاصة الصادمة

**من أصل الـ24 دومين، دومينين بس تبقّوا قابلين للتحقق الحي الفعلي غير المختبَرين لسه** (`affiliate` — معلَّق على تعقيد الإعداد، `privacy` — جاهز مباشرة)، **فوق الـ3 اللي اتأكَّدوا بالفعل** (`finance`, `ai_agents`, `ai_governance`). **الـ19 الباقيين محجوبين، لكن بأسباب متفرقة ومختلفة تمامًا عن بعض** — مش كلهم نفس باج الـ`FinanceService(db)` الموثَّق أول الجلسة. ده أوسع بكتير من التقدير الأولي ("13 دومين محجوبين بباج واحد").

**كل هذه الباجات بلا استثناء:**
- **موجودة مسبقًا في الكود، سابقة لأي تعديل بتاعنا النهاردة.**
- **من فئات مختلفة تمامًا عن `commit()` جوه `begin_nested()`** (constructor، type mismatch، method غير موجودة، endpoint غير موجود، تعقيد بيانات اختبار).
- **صفر إصلاح تم عليها** — موثَّقة فقط، زي باقي الاكتشافات الجانبية طول الجلسة.

**الحالة:** ⏳ **متوقف. مستني توجيهك:** هل نكمل بـ`privacy` بس (القابلة للاختبار المباشر)، أو نستثمر وقت إضافي في تجهيز سلسلة `commerce`/`affiliate` (طلب → عنصر طلب → منتج → عمولة)، أو نعتبر الاثنين (`affiliate`/`privacy`) كافيين كعيّنة تمثيلية إضافية ونقفل التحقق الحي هنا موثَّقين الباقي كـ"مُراجَع كود بس"؟

---

## [2026-08-13] `privacy` كمان طلعت محجوبة — إغلاق الجلسة

### محاولة `privacy.process_erasure_request`

1. أنشأت طلب محو بيانات throwaway عبر API فعلي (`POST /privacy/erasure/request`, يوزر 30, `target_module="iot"`) → `201`, `id=1, status=PENDING`.
2. حاولت الموافقة عليه كـSUPER_ADMIN (يوزر 29) → `POST /privacy/admin/erasure/1/process?approved=true` → **`400`**: `"تعذر معالجة الطلب. يرجى التأكد من الصلاحيات والبيانات."`
3. تتبُّع اللوج كشف السبب الحقيقي: `PermissionDeniedError: Only Privacy Officers can process erasure requests.`

**السبب الجذري (قراءة كود):** `privacy/service.py:124` — `if not await is_privacy_officer(admin_id):` بتبعت `admin_id` (رقم `int`)، لكن الدالة الحقيقية (`core/security.py`) توقيعها `is_privacy_officer(user: User)` وبتقرا `user.system_role` من الكائن. تمرير `int` بدل كائن `User` بيخلي `getattr(int, "system_role", None)` يرجع `None` دايمًا → الفحص بيفشل لأي حد، **حتى `SUPER_ADMIN`**. باج pre-existing، فئة مختلفة تمامًا (type mismatch)، **خارج النطاق، صفر إصلاح**.

**النتيجة: صفر دومين من الـ9 المتبقية (`academy, affiliate, agritech, commerce, communications, privacy, saas, sovereign_entities, zamakana`) قابل للتحقق الحي فعليًا** — كل واحد فيهم اتكشف فيه باج منفصل مختلف تمامًا وقت المحاولة الفعلية.

### الحصيلة النهائية للتحقق الحي

**3 دومين بس مؤكَّدين حيًا بالكامل (طلب HTTP فعلي + `SELECT` مستقل):** `finance`, `ai_agents`, `ai_governance`. **21 دومين الباقيين: مُصلَحين كود بالكامل + مُراجَعين (6 منهم بتفصيل before/after كامل وموافقة صريحة)، لكن غير مُختبَرين حيًا** لأسباب متفرقة (فئات باجات مختلفة تمامًا، موثَّقة كل واحدة على حدة، صفر علاقة بباج الترانزاكشن).

---

## [2026-08-13] إغلاق الجلسة — التوثيق النهائي + Sweep + التنظيف

### 1. التوثيق الشامل في `PROGRESS_LOG.md`

اتضاف قسم كبير وبارز (`## [2026-08-13] — إصلاح باج ترانزاكشن منهجي...`) يغطي: (أ) الـ3 دومين المؤكَّدين حيًا + الدرس المستفاد الدائم عن النجاح الكاذب، (ب) الـ21 الباقيين وتصنيفهم الرسمي "مُصلَح + مُراجَع، غير مُختبَر"، (ج) **🔴🔴 قسم منفصل وبارز جدًا** لاكتشاف باج `SimpleTenant`/type mismatch في `academy` (36 استخدام)، `commerce` (12)، `saas` (17)، `sovereign_entities` — نفس فئة باج `finance/router.py` الأصلي، غير مُصلَح، يستاهل جلسة ثالثة، (د) 🟠 قسم للباجات المتفرقة الستة الأخرى (كل واحدة بفئتها المستقلة: `communications`, `zamakana`, `agritech`, `sovereign_entities.create_entity`, `privacy.is_privacy_officer`, `affiliate` تعقيد بيانات).

### 2. Sweep نهائي (`grep`)

تأكيد مستقل: `ai_governance/repository.py`, `finance/service.py` (ما عدا `mint_currency`'s المشروع self-commit)، `invitations/service.py` (9 commits جديدة + 1 flush قديم) — كل الأرقام مطابقة للمتوقَّع بعد فحص كل تباين (كلها ترجع لـcommits pre-existing غير مؤكَّدة، مش أخطاء). عدّ `begin_nested` مقابل `commit` عبر كل الـ24 ملف `service.py` — كل التباينات اتفسّرت ومؤكَّدة (مثال: `digital_twin` عمدًا 3 بلوكات/2 commit لأن `interact_with_twin` مغطاة بـcommit موجود مسبقًا في `create_interaction_log`).

### 3. تنظيف بيانات throwaway (الجلستين) + تحقق مستقل

**حُذف بترتيب FK صحيح:** `entity_representatives`(1) → `sovereign_entities_v2`(1) → `data_erasure_requests`(1) → `agent_audit_logs`(1) → `agent_approval_queue`(1) → `ai_agents`(1) → `affiliate_profiles`(1) → `transactions`(6) → `wallets`(2) → `academy_tenants`(1، بيعمل CASCADE لحذف `users` 29/30 تلقائيًا).

**تحقق مستقل بعد الحذف — 11 استعلام، كلهم صفر:** `users_29_30=0`, `wallets=0`, `academy_tenants_13=0`, `transactions=0`, `ai_agents=0`, `agent_approval_queue=0`, `agent_audit_logs=0`, `affiliate_profiles=0`, `data_erasure_requests=0`, `sovereign_entities_v2=0`, `entity_representatives=0`.

**تحقق مستقل إضافي — حالة Phase 16 لسه سليمة (مقارنة بالحالة النهائية الموثَّقة في نهاية تقرير Phase 16):** `academy_tenants=1, users=7, ai_agents=0, wallets=6` — **مطابق تمامًا**، مفيش أي تأثير على بيانات الجلسة التانية. يوزرات `p0smoke_*`/`p1smoke_*`/`phase2test*` (مش بتاعتنا) فضلت زي ما هي.

**uvicorn التجريبي اتوقف** (PID 15760).

**الحالة:** ✅ الخطوات 1-3 مكتملة. التالي: commit واحد معزول.
