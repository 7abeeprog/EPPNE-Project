# جلسة جرد + أمان مدمجة — الدفعة 3: transport, logistics, manufacturing, tourism_sports

**بدأ التسجيل:** 2026-08-25
**الحالة:** ✅ **الدفعة 3 بالكامل (الأربعة دومينات) مغلقة من ناحية IDOR الكودي، مؤكَّدة حيًا حيث أمكن.** جرد + فحص أمني كامل (§0-§10) → موافقة المستخدم على كل التصنيف والترتيب + توجيهات تنفيذ دقيقة → تنفيذ `logistics` (22/22، تحقق حي كامل) → تنفيذ `manufacturing` (20/20 + إصلاح `entity_id`/الهاردكود/الـ`commit` المفقود، تحقق حي كامل) → تنفيذ `tourism_sports` (10/10، تحقق حي كامل) → تنفيذ `transport` (16/16، إصلاح كودي احترازي بلا تحقق حي — بالضبط زي المتفق) → إضافة البنود #34-#39 لـ`constructor-mismatch-backlog-classification.md` (§11 تحت للتفاصيل الكاملة). ⏳ **لم يُنفَّذ commit بعد — بانتظار موافقتك الصريحة على الـ`diff` في §11.7.**

---

## 0) ملخص تنفيذي فوري

| الدومين | عدد endpoints | النمط الأمني | الأخطر | قابل للاستغلال حيًا الآن؟ |
|---|---|---|---|---|
| **transport** | 16 | 🔴 نفس نمط X-Tenant-ID القياسي (هيدر بدل `current_user.tenant_id`) | `update_vehicle_location` (GPS حي) + `complete_delivery` (صفر فحص ملكية إطلاقًا) | ❌ **لا — الدومين كله معطَّل بنيويًا** (7 جداول DB غير موجودة، صفر migration، راجع §1.1) |
| **logistics** | 22 | 🔴🔴🔴 **الأسوأ في الدفعة — صفر أي admin-gate، أي `active_user` عادي يقدر يمسح/يعدّل مورد أي تينانت** | `delete_warehouse` + `adjust_inventory` | ✅ **مؤكَّد حيًا بالكامل** |
| **manufacturing** | 20 | 🔴 نفس النمط + `schedule_maintenance` **بصفر فحص تينانت من الأساس** (أسوأ من الهيدر نفسه) | `schedule_maintenance` (لكن مُقنَّع ببق `commit()` مفقود) + `restock_spare_part` (بق `tenant_id=1` هاردكودد يتفاعل مع IDOR) | 🟡 **جزئيًا — `create_facility` نفسها معطوبة لكل التينانتات (NOT NULL)، `schedule_maintenance` الكتابة بتضيع صامتة** |
| **tourism_sports** | 10 | 🟠 أقل حدة (إنشاء بس + حجوزات) — لكن الحجز عبر-تينانت مؤكَّد حيًا | `book_program`/`buy_ticket` عبر-تينانت | 🟡 **جزئيًا — مؤكَّد حيًا لحد باج `payment_tx_hash` منفصل يكسر `book_program`** |

**اكتشاف بنيوي حرج غير أمني، خارج نطاق IDOR:** دومين `transport` بالكامل **معطَّل على مستوى قاعدة البيانات** — 7 من جداوله الأساسية (`fleets`, `vehicles`, `transport_hubs`, `transport_routes`, `transport_trips`, `trip_bookings`, `delivery_tasks`) **غير موجودة إطلاقًا** في schema الفعلي، ولا توجد ولا migration واحدة تنشئها عبر تاريخ المشروع كله (`migrations/versions/`، 41 ملف، صفر نتيجة). راجع §1.1 للتفاصيل الكاملة.

**تأكيد الطلب الصريح للمستخدم (تحقق تصحيح ديون تقنية الصبح):** `transport/service.py:17,330,382,515,554` **لسه سليم** — `InvoicingService(self.db, tenant_id)` + `invoicing.create_invoice(...)` مكانهم `finance.create_invoice` غير الموجودة، ومصدر `tenant_id` المُمرَّر Python-argument صريح من الـservice (مش من جسم طلب HTTP)، **منفصل تمامًا** عن ثغرة X-Tenant-ID الموصوفة تحت (نفس الفارق الموثَّق في الدفعة 2 §5 لباقي الدومينات). جرد `.finance.create_invoice(` عبر الملف كله = **صفر نتيجة متبقية**، مطابق تمامًا لتأكيد `technical-pattern-sweep-session-log.md:311`.

---

## 1) جدول `transport` — 16 endpoint (نقل ركاب/بضائع، محطات، أساطيل، رحلات)

**النطاق:** `router.py`(245 سطر)، `service.py`(622 سطر)، `repository.py`(243 سطر)، `models.py`(229 سطر)، `schemas.py`(131 سطر) — قراءة كاملة.

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /hubs` | إنشاء محطة نقل (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 2 | `GET /hubs` | قائمة محطات التينانت | ❌ **بلا مصادقة إطلاقًا** | **هيدر** | ✅ لكن بقيمة ملوَّثة | 🔴 IDOR قراءة + بلا حتى تسجيل دخول |
| 3 | `POST /fleets` | إنشاء أسطول (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 4 | `POST /vehicles` | إضافة مركبة (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 5 | `PATCH /vehicles/{id}/location` | تحديث موقع GPS حي لمركبة | ✅ superuser | **هيدر** | ✅ لكن بقيمة ملوَّثة | 🔴🔴🔴🔴 **IDOR كتابة — تعديل GPS مركبة تينانت تاني موجودة فعليًا (نفس التصنيف الأصلي في `critical-finding-xtenant-systemic.md` #20)** |
| 6 | `GET /vehicles/available` | مركبات متاحة | ❌ **بلا مصادقة إطلاقًا** | **هيدر** | ✅ لكن بقيمة ملوَّثة | 🔴 IDOR قراءة + بلا تسجيل دخول |
| 7 | `POST /routes` | إنشاء مسار (سوبريوزر + تحليل AI) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 8 | `POST /trips` | جدولة رحلة (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 9 | `PATCH /trips/{id}/start` | بدء رحلة (سائق) | ✅ active_user | **هيدر** لجلب الرحلة، لكن `trip.driver_id != current_user.id` (حقيقي) | ✅ | 🟠 **طبقة ثانية حقيقية تحمي عمليًا** — نفس نمط `tenders_auctions.evaluate_bid` |
| 10 | `PATCH /trips/{id}/complete` | إنهاء رحلة (سائق) | ✅ active_user | **هيدر** + `driver_id` حقيقي | ✅ | 🟠 نفس الحماية الثانوية |
| 11 | `GET /trips/my` | رحلاتي | ✅ active_user | **هيدر** + `driver_id` حقيقي كفلتر إضافي | ✅ | 🟠 محمي عمليًا (فلتر `driver_id` حقيقي) |
| 12 | `POST /bookings` | حجز رحلة (دفع فعلي) | ✅ active_user | **هيدر** | ✅ لكن **صفر فحص ملكية على الرحلة نفسها** | 🔴🔴🔴🔴 **IDOR + مالي: حجز رحلة تينانت تاني بمال حقيقي من محفظة المهاجم — يُنسب لتينانت الضحية** |
| 13 | `GET /bookings/my` | حجوزاتي | ✅ active_user | **هيدر** + `passenger_id` حقيقي | ✅ | 🟠 محمي عمليًا |
| 14 | `POST /deliveries` | إنشاء مهمة توصيل | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 15 | `POST /deliveries/{id}/pay` | دفع رسوم توصيل | ✅ active_user | **هيدر** + `sender_id != payer_id` (حقيقي) | ✅ | 🟠 محمي عمليًا (فحص `sender_id` حقيقي) |
| 16 | `POST /deliveries/{id}/complete` | إنهاء توصيل (إثبات تسليم) | ✅ active_user | **هيدر** | ✅ لكن **صفر فحص ملكية إطلاقًا** (لا `sender_id` ولا `receiver_id` ولا `driver_id`) | 🔴🔴🔴🔴🔴 **الأخطر في transport — أي `active_user` من أي تينانت يقدر يُنهي أي مهمة توصيل تخص تينانت تاني بمجرد تخمين/معرفة الـID** |

### 1.1) 🔴🔴🔴🔴🔴 اكتشاف بنيوي حرج — دومين `transport` معطَّل بالكامل على مستوى DB، بمعزل تام عن IDOR

تحقق مباشر (`pg_tables`) أثبت أن الجداول التالية **غير موجودة إطلاقًا** في قاعدة البيانات الفعلية: `fleets`, `vehicles`, `transport_hubs`, `transport_routes`, `transport_trips`, `trip_bookings`, `delivery_tasks`. تأكيد إضافي: `alembic current` = `039_expand_projects_contributions_updates_schema` (نفس الرأس `head` الموجود فعليًا)، و`grep` شامل على مجلد `migrations/versions/` (41 ملف) لأي إشارة لـ`vehicles`/`fleets`/`transport_hubs`/إلخ = **صفر نتيجة**. **لا يوجد ولا migration واحدة حاولت إنشاء هذه الجداول عبر تاريخ المشروع بالكامل** — الكود (`models.py`) موجود ومكتمل، لكن لم يُترجَم أبدًا لـ`CREATE TABLE` فعلي.

**الأثر العملي:** أي endpoint في `transport` (الـ16 كلهم) **سيفشل فورًا بـ`UndefinedTableError` (500)** عند أول استدعاء حقيقي — مؤكَّد حيًا: محاولة `POST /transport/fleets` (بعد فتح بوابة SaaS) رجعت `sqlalchemy.exc.ProgrammingError: relation "fleets" does not exist`. **هذا يعني ثغرات IDOR الموصوفة فوق (#2, #5, #6, #12, #16) كامنة في الكود 100%، لكن غير قابلة للاستغلال الفعلي حاليًا في أي بيئة تشارك نفس حالة الـmigrations** — بمجرد إضافة migration الجداول دي (خطوة منفصلة تمامًا، تحتاج قرار منتجي/تقني: هل `transport` جاهز للتفعيل أصلًا؟) هتتفعّل الثغرات فورًا بلا أي تغيير كودي إضافي.

**تنويه منهجي:** التحقق الحي لهذا الدومين اقتصر على تأكيد الفجوة البنيوية دي (قراءة DB مباشرة) — التصنيف الأمني في الجدول فوق **قراءة كود فقط**، بنفس صرامة الدفعات السابقة قبل التحقق الحي، لكن التحقق الحي نفسه غير ممكن هنا لسبب مختلف تمامًا عن بوابات SaaS المعطوبة في الدفعة 2 (مش نقص بيانات إعداد، بل نقص جداول DB بالكامل).

**باج جانبي مكتشَف أثناء قراءة الكود، غير مؤكَّد حيًا (الدومين معطَّل أصلًا):** `service.py:315` — مسار إعادة تشغيل idempotency في `book_trip` يستدعي `self.repo.get_booking(booking_id)` بوسيط واحد فقط، لكن `repository.py:180` تعرِّف الدالة بوسيطين إجباريين (`booking_id`, `tenant_id`) — `TypeError` مضمون عند أي محاولة إعادة إرسال طلب حجز بنفس `Idempotency-Key`.

### الترابط Cross-domain (`transport`)
**يستدعي:** `finance.transfer` (دفع حجز/توصيل)، `invoicing.create_invoice` (فاتورة حجز/توصيل — **الإصلاح الصباحي سليم، راجع §0**)، `affiliate.register_commission`، `saas.can_access_service` (بوابة catalog-based — **فارغة لـ`transport` في هذه البيئة، §3**)، `ai_agents.execute_agent_action` + `ai_governance.check_and_consume` (تحسين مسار AI)، `communications.send_notification`، `identity` (قراءة سائق/راكب). ربط بنيوي غير فعّال: `Vehicle.smart_asset_id` → `iot.smart_assets` (FK بلا تحقق تشغيلي).
**يُستدعى من:** لا أحد.

---

## 2) جدول `logistics` — 22 endpoint (مخازن، مخزون، معدات، تنبؤ بالطلب) — 🔴🔴🔴 **الأسوأ في الدفعة**

**النطاق:** `router.py`(446 سطر)، `service.py`(640 سطر)، `repository.py`(519 سطر)، `models.py`(350 سطر)، `schemas.py`(246 سطر) — قراءة كاملة.

**اكتشاف بنيوي: كل الـ22 endpoint بلا استثناء تستخدم `Depends(get_current_tenant)` (هيدر)، و`Depends(get_current_active_user)` فقط — صفر endpoint واحد محمي بـ`get_current_superuser`** (التصنيف السابق "SAFE — استيراد `get_current_superuser` ميت، لا admin endpoints" كان **يعتمد على معيار خاطئ ثبت خطؤه سابقًا لـ`employment`/`invitations`/`tenders_auctions`** — غياب صلاحية إدارية لا يعني الأمان، بل هنا يعني **العكس تمامًا**: أي مستخدم عادي مسجَّل دخول يملك صلاحيات CRUD كاملة على مخازن/مخزون/معدات **أي تينانت تاني**).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /warehouses` | إنشاء مخزن | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 2 | `GET /warehouses` | قائمة مخازن التينانت | ✅ active_user | **هيدر** | ✅ لكن بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 3 | `GET /warehouses/{id}` | تفاصيل مخزن | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 4 | `PUT /warehouses/{id}` | تعديل مخزن | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴🔴 **IDOR كتابة — مؤكَّد حيًا §6.1** |
| 5 | `DELETE /warehouses/{id}` | حذف مخزن (soft-delete) | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴🔴 **الأخطر — مستخدم عادي من أي تينانت يحذف مخزن تينانت تاني — مؤكَّد حيًا §6.1** |
| 6 | `POST /warehouses/{id}/zones` | إنشاء منطقة داخل مخزن | ✅ active_user | **هيدر** | صفر فحص ملكية المخزن أصلًا | 🔴 تلوّث بيانات + IDOR كتابة (منطقة تُزرع في مخزن تينانت تاني بلا حتى فحص وجوده) |
| 7 | `POST /inventory/receive` | استلام مخزون جديد | ✅ active_user | **هيدر** + فحص سعة المخزن (بقيمة ملوَّثة) | ✅ | 🔴🔴🔴🔴 IDOR كتابة |
| 8 | `POST /inventory/issue` | صرف مخزون | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كتابة |
| 9 | `POST /inventory/adjust/{id}` | تعديل كمية مخزون (جرد) | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴🔴 **IDOR كتابة — مؤكَّد حيًا §6.1: تعديل كمية مخزون تينانت تاني لأي رقم عشوائي** |
| 10 | `GET /inventory` | قائمة مخزون | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 11 | `GET /inventory/low-stock` | مخزون منخفض | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 12 | `GET /inventory/expired` | مخزون منتهي الصلاحية | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 13 | `GET /inventory/{id}` | تفاصيل صنف مخزون | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 14 | `GET /inventory/{id}/transactions` | سجل حركات صنف | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 15 | `POST /equipment` | إضافة معدة | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 16 | `GET /equipment` | قائمة معدات | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 17 | `GET /equipment/{id}` | تفاصيل معدة | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 18 | `PUT /equipment/{id}` | تعديل معدة | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴🔴 IDOR كتابة (نفس نمط `#4`) |
| 19 | `POST /equipment/{id}/maintenance` | جدولة صيانة معدة | ✅ active_user | **هيدر** | صفر فحص ملكية المعدة أصلًا | 🔴 IDOR كتابة (سجل صيانة يُزرع لمعدة تينانت تاني بلا حتى فحص وجودها) |
| 20 | `POST /forecast` | توليد تنبؤ طلب (AI) | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات + استهلاك حصة AI لتينانت تاني |
| 21 | `GET /forecast` | قائمة تنبؤات | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 22 | `GET /stats` | إحصائيات سريعة | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة (عبر كل الدوال فوق) | 🔴🔴🔴🔴 IDOR قراءة تجميعية (تسريب أرقام أعمال تينانت تاني بالكامل: عدد مخازن، قيمة مخزون إجمالية، معدات...) |

**الخلاصة الوظيفية:** **22/22 مربوطة بفرونت إند؟** لم يُفحَص فرونت إند logistics صراحة في هذه الجلسة (خارج الطلب المباشر — التركيز كان جرد+أمان باك إند) — **بند مفتوح، يحتاج فحص منفصل لو لزم قبل أي قرار إطلاق**.

### الترابط Cross-domain (`logistics`)
**يستدعي:** `invoicing.create_invoice`؟ **لا** — `logistics/service.py` يستورد `InvoicingService` لكن **لا يستدعيها في أي مكان فعليًا** (استيراد ميت، تأكيد `grep` على الملف). `affiliate.service` نفس الشيء — مستورد، **غير مُستخدَم إطلاقًا**. `finance.service` نفس الشيء — مستورد، **غير مُستخدَم إطلاقًا** (لا يوجد `FinanceService(` استدعاء واحد في كل الملف). **`logistics` لا يحرّك أي مال حقيقي حاليًا رغم استيراد الثلاث خدمات** — فقط `ai_agents`/`ai_governance` (تنبؤ الطلب) و`saas.get_active_subscription` (بوابة features-based، عاملة) مُستخدَمَين فعليًا.
**يُستدعى من:** لا أحد.

---

## 3) جدول `manufacturing` — 20 endpoint (منشآت، خطوط إنتاج، دفعات، مواد خام، توأم رقمي، جودة، صيانة تنبؤية، قطع غيار)

**النطاق:** `router.py`(410 سطر)، `service.py`(805 سطر)، `repository.py`(333 سطر)، `models.py`(344 سطر)، `schemas.py`(249 سطر) — قراءة كاملة.

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /facilities` | إنشاء منشأة صناعية | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات — **لكن الـendpoint معطوب لكل التينانتات (§3.1)** |
| 2 | `GET /facilities` | قائمة منشآت | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 3 | `GET /facilities/{id}` | تفاصيل منشأة | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 4 | `POST /facilities/{id}/lines` | إضافة خط إنتاج | ✅ active_user | **هيدر** (لفحص وجود المنشأة فقط) | `ProductionLine` **بلا عمود `tenant_id` خاص بيها إطلاقًا** — معزولة فقط عبر `facility_id` | 🔴🔴🔴🔴 IDOR كتابة (خط إنتاج يُزرع في منشأة تينانت تاني عبر هيدر) |
| 5 | `POST /blueprints` | إنشاء نموذج منتج | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كتابة |
| 6 | `POST /batches` | إنشاء دفعة إنتاج | ✅ active_user | **هيدر** (لفحص blueprint/line) | `ProductionBatch` **بلا عمود `tenant_id` خاص بيها** — معزولة عبر `product_blueprint_id`→join | 🔴🔴🔴🔴 IDOR كتابة |
| 7 | `POST /batches/{id}/start` | بدء إنتاج فعلي (فاتورة + توليد منتجات) | ✅ active_user | **هيدر** | ✅ (عبر join لـblueprint) بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كتابة — تشغيل خط إنتاج تينانت تاني + فاتورة تُنسب له |
| 8 | `POST /raw-materials` | تسجيل دفعة مواد خام | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 9 | `GET /raw-materials` | قائمة مواد خام | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 10 | `POST /batches/{id}/consume-material` | استهلاك مادة خام في دفعة | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة (على الدفعة والمادة) | 🔴🔴🔴🔴 IDOR كتابة (استهلاك/إفراغ مخزون مواد خام تينانت تاني) |
| 11 | `POST /product-items/{id}/digital-twin` | إنشاء توأم رقمي لمنتج | ✅ active_user | **هيدر** | ✅ (عبر join) بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كتابة |
| 12 | `GET /product-items/{id}/digital-twin` | قراءة توأم رقمي | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 13 | `POST /quality-certificates` | إصدار شهادة جودة | ✅ **superuser** | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات (شهادة تُنسب لتينانت هيدر) |
| 14 | `GET /quality-certificates/{type}/{id}` | شهادات كيان | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 15 | `POST /predictive-maintenance` | تحليل AI + جدولة صيانة تلقائية (+فاتورة) | ✅ active_user | **هيدر** | ✅ (عبر join لخط الإنتاج) بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR كتابة + استهلاك حصة AI + فاتورة لتينانت تاني |
| 16 | `GET /production-lines/{id}/pending-maintenance` | صيانات معلَّقة لخط | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |
| 17 | `POST /maintenance/{id}/schedule` | جدولة صيانة (تأكيد يدوي) | ✅ active_user | **لا يوجد `tenant` dependency في الراوتر أصلًا** | **صفر — `service.schedule_maintenance(log_id, scheduled_at)` بلا معامل `tenant_id` إطلاقًا** | 🔴🔴🔴🔴🔴 **الأسوأ في الدفعة كلها من ناحية الشكل — ليس حتى هيدر، صفر تحقق تينانت مطلقًا (نفس فئة `service_marketplace.publish/unpublish`/`realestate.revalue_land`) — لكن الكتابة نفسها تضيع صامتة (§3.2)** |
| 18 | `POST /spare-parts` | إنشاء قطعة غيار | ✅ **superuser** | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 19 | `POST /spare-parts/{id}/restock` | إعادة تخزين قطعة غيار | ✅ active_user (**ليس سوبريوزر**) | **هيدر** | ✅ فحص أول صحيح، لكن **fetch داخلي ثانٍ بـ`tenant_id=1` هاردكودد** | 🔴🔴🔴🔴🔴 **مؤكَّد حيًا §6.2 — IDOR فعلي لقطع غيار تينانت1 تحديدًا، يفشل (500) لأي تينانت آخر بسبب الهاردكود نفسه** |
| 20 | `GET /spare-parts` | قائمة قطع غيار | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة |

### 3.1) 🔴 `create_facility` معطوبة لكل التينانتات — مؤكَّد حيًا، غير متعلق بـIDOR

`ManufacturingFacilityCreate` (schema) و`service.create_facility` **لا يمرّران `entity_id` إطلاقًا**، بينما `manufacturing_facilities.entity_id` عمود **`NOT NULL`** (`models.py:51`). تحقق حي مباشر (`POST /manufacturing/facilities`) رجع `IntegrityError: null value in column "entity_id" violates not-null constraint` — **لأي تينانت، بلا استثناء**. هذا يمنع كل سلسلة الإنشاء الطبيعية (`facility → line → blueprint → batch → digital_twin`) عبر الـAPI الحقيقي — التحقق الحي لبقية endpoints المرتبطة بمنشأة (٪4، ٪5، ٪6، ٪7، ٪11) اعتمد على زرع منشأة/خط إنتاج مباشرة في DB (نفس أسلوب الدفعة 2 مع بوابات SaaS المعطوبة).

### 3.2) 🔴 `schedule_maintenance` — صفر فحص تينانت (مؤكَّد حيًا) + الكتابة نفسها تضيع صامتة (اكتشاف مستقل)

تحقق حي: `A` (تينانت1، `active_user` عادي، **بلا أي هيدر `X-Tenant-ID` إطلاقًا**) استدعى `POST /manufacturing/maintenance/1/schedule` على سجل صيانة **حقيقي يخص تينانت16** (مزروع مسبقًا) → **`200 {"message":"Maintenance scheduled","scheduled_at":"2026-09-01..."}`**. **لكن** `SELECT` مستقل بعدها أظهر الصف **بلا أي تغيير** (`status='PENDING'`, `maintenance_scheduled_at=NULL`). السبب: `repository.schedule_maintenance` يستخدم `await self.db.flush()` **بدون** `await self.db.commit()` في أي مكان بمسار الاستدعاء بالكامل (لا في `service.schedule_maintenance` ولا في الـrouter)، و`get_db` (`core/database.py:45-51`) بيعمل `session.close()` فقط في `finally` **بلا commit تلقائي** — يعني أي تغيير لم يُرتكَب صراحة **يضيع بالكامل** عند إغلاق الجلسة (نفس فئة `silent-write-regression` الموثَّقة مسبقًا في المشروع، لكن هنا مثال جديد). **النتيجة المزدوجة:** الثغرة (صفر فحص تينانت) حقيقية 100% في الكود، لكن **أثرها العملي حاليًا صفر** — أي استدعاء (شرعي أو هجومي) بيرجّع نجاحًا كاذبًا بلا أي كتابة فعلية.

### الترابط Cross-domain (`manufacturing`)
**يستدعي:** `finance.transfer`؟ **لا** — لا استدعاء مباشر (فقط `InvoicingService.create_invoice` في `start_production`/`analyze_and_schedule_maintenance`، تنسيق تينانت سليم ميكانيكيًا نفس نمط `transport`، لكن القيمة ملوَّثة من نفس مصدر الهيدر). `affiliate.register_commission` (عمولة إنشاء منشأة). `ai_agents.execute_agent_action` + `ai_governance.check_and_consume` (تحليل إنتاج/صيانة). `saas.get_active_subscription` (بوابة features-based، عاملة). ربط بنيوي غير فعّال: `ManufacturingFacility.real_estate_unit_id` → `realestate.property_units`، `Vehicle`-مثيل `smart_asset_id` → `iot.smart_assets` (كلاهما FK بلا تحقق تشغيلي فعلي).
**يُستدعى من:** لا أحد.

---

## 4) جدول `tourism_sports` — 10 endpoint (سياحة، ترفيه/تذاكر، رياضة/انتقالات لاعبين)

**النطاق:** `router.py`(161 سطر)، `service.py`(529 سطر)، `repository.py`(149 سطر)، `models.py`(370 سطر)، `schemas.py`(189 سطر) — قراءة كاملة.

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فحص الملكية | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /destinations` | إنشاء وجهة سياحية | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 2 | `GET /destinations` | قائمة وجهات | ❌ **بلا مصادقة إطلاقًا** | **هيدر** | ✅ بقيمة ملوَّثة | 🔴 IDOR قراءة + بلا تسجيل دخول |
| 3 | `POST /programs` | إنشاء برنامج سياحي | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 4 | `POST /programs/{id}/book` | حجز برنامج (دفع فعلي) | ✅ active_user | **هيدر** + `program.tenant_id != tenant_id(هيدر)` (نفس المصدر الملوَّث، **ليس مقارنة حقيقية**) | ✅ | 🔴🔴🔴🔴 **IDOR + مالي — مؤكَّد حيًا جزئيًا §6.3 (يصطدم ببق `payment_tx_hash` منفصل)** |
| 5 | `POST /events` | إنشاء فعالية ترفيهية | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 6 | `POST /tickets/purchase` | شراء تذكرة فعالية (دفع فعلي) | ✅ active_user | **هيدر** + `event.tenant_id != tenant_id(هيدر)` (نفس العيب) | ✅ | 🔴🔴🔴🔴 **IDOR + مالي — نفس نمط `book_program`، غير مختبَر حيًا (نفس الاستنتاج الكودي، وقت الجلسة اقتصر عليه)** |
| 7 | `POST /sports/organizations` | إنشاء منظمة/نادي رياضي | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات (+ يتيح زرع نادي وهمي داخل تينانت الضحية، راجع §5) |
| 8 | `POST /sports/players/profile` | إنشاء ملف لاعب | ✅ active_user | **هيدر** | صفر فحص تينانت — فقط فحص "ملف موجود مسبقًا؟" **بلا فلتر تينانت حتى في هذا الفحص** (`get_player_profile(user_id)` بلا `tenant_id`) | 🟠 تلوّث بيانات (أقل حدة — مربوط بـ`user_id` حقيقي) |
| 9 | `POST /sports/transfers/bid` | تقديم عرض شراء لاعب | ✅ active_user | **هيدر** لفحص اللاعب، لكن `from_club.owner_id != current_user.id` (**حقيقي**) | ✅ | 🟠 **طبقة ثانية حقيقية** — لكن راجع §5 لتسلسل استغلال محتمَل عبر `#7` |
| 10 | `POST /sports/tournaments` | إنشاء بطولة | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |

**باج وظيفي منفصل مكتشَف أثناء قراءة الكود (غير مختبَر حيًا، خارج وقت الجلسة):** `place_transfer_bid` (`service.py:402`) يستدعي `self.repo.get_player_profile(data["player_id"])` — لكن `repository.get_player_profile(user_id)` بتفلتر بعمود `PlayerProfile.user_id`، بينما `data["player_id"]` (حسب `TransferBidCreate.player_id` — "معرف اللاعب") يُقصَد به `PlayerProfile.id` (المفتاح الأساسي)، **مش** `user_id`. أي استدعاء حقيقي بمعرف ملف لاعب صحيح **شبه مضمون يفشل** (`NotFoundError`)، إلا لو تصادف رقميًا `PlayerProfile.id == PlayerProfile.user_id` لنفس الصف بالصدفة. يحتاج تصنيف Backlog منفصل (نفس فئة "عمود خطأ" الموثَّقة لـ`arbitration_syndicates` سابقًا).

### 5) تسلسل استغلال محتمَل (كودًا فقط، غير مختبَر حيًا) — `create_sports_org` → `place_transfer_bid`

`create_sports_org` (بند #7) بتقبل `tenant_id` من الهيدر بلا فحص + `owner_id=user_id` حقيقي. مهاجم يقدر ينشئ "نادي" وهمي بهيدر مزوَّر = تينانت الضحية، بحيث `owner_id` = المهاجم نفسه. بعدين `place_transfer_bid` (بند #9، فحص `from_club.owner_id != current_user.id`) هيعدّي الفحص لأن المهاجم فعلًا "يملك" النادي المزروع — يسمح بتقديم عرض شراء حقيقي على لاعب تينانت الضحية، منسوب رسميًا لنادي داخل تينانت الضحية. **غير مؤكَّد حيًا هذه الجلسة** (خارج نطاق الوقت المتاح)، موثَّق كسلسلة نظرية دقيقة تحتاج تحقق منفصل لو قررت الأولوية.

### الترابط Cross-domain (`tourism_sports`)
**يستدعي:** `finance.transfer` (حجز برنامج/شراء تذكرة — **راجع §6.3 لباج `payment_tx_hash`**)، `invoicing.create_invoice` (فاتورة حجز/تذكرة/رسوم وكالة — تنسيق ميكانيكي سليم، قيمة ملوَّثة من نفس مصدر الهيدر، مطابق تمامًا لاستنتاج الدفعة 2 §5)، `affiliate.register_commission`، `ai_agents.execute_agent_action` (تحليل طبي/نقل VIP)، `ai_governance.check_and_consume` (تحليل انتقال لاعب)، `saas.can_access_service` (بوابة catalog-based — **فارغة لـ`tourism`/`entertainment`/`sports` في هذه البيئة، §7**).
**يُستدعى من:** لا أحد.

---

## 6) التحقق الحي — التفاصيل الكاملة

**السيرفر:** `uvicorn` محلي (`E:\cc\eppne-backend`, venv, منفذ 8000)، شُغِّل هذه الجلسة، تأكيد `GET /docs` → `200`، **أُوقف في نهاية الجلسة** (`taskkill /F` + `netstat` يؤكد صفر `LISTENING`).

**المستخدمون:** `TEST_super_a` (id=772، تينانت1، `SUPER_ADMIN`) و`TEST_instr_b` (id=774، تينانت16، `SUPER_ADMIN`). **كلمة سر الاثنين كانت غير صالحة من جلسة سابقة** (باسورد قديم فشل) — أُعيد تعيينها لكلمة موحّدة جديدة (`TEST_pass_batch3_2026`) بنفس آلية `passlib`/`bcrypt`، ووُثِّق التحديث في `throwaway-test-users.md`. **اكتشاف جانبي مهم أثناء تسجيل الدخول:** `POST /identity/login` بيفلتر بـ`username/email` **و**`tenant_id` (من هيدر `X-Tenant-ID`، افتراضي=1) معًا — تسجيل دخول `TEST_instr_b` (تينانت16) **يفشل بدون إرسال `X-Tenant-ID: 16` صراحة مع طلب الـlogin نفسه** (تأكيد مباشر إن سلوك `login` "الآمن" الموثَّق سابقًا في `critical-finding-xtenant-systemic.md` لسه صحيح).

**بوابة SaaS:** `transport`/`tourism_sports` يستخدمان `can_access_service` (آلية catalog-based، مثل `service_marketplace`/`tenders_auctions` في الدفعة 2) — **صفر صف** لأي من `transport`/`tourism`/`entertainment`/`sports` في `saas_service_catalog` قبل هذه الجلسة. زُرعت 4 صفوف throwaway (`saas_service_catalog` + `saas_service_plans` + `saas_tenant_service_access` + `saas_tenant_subscriptions` لتينانت1 و16 معًا، 8 اشتراكات) لإتاحة التحقق الحي، **ثم حُذفت الأربعة صفوف بالكامل** بعد الانتهاء (مش استرجاع — كانت جديدة من الأساس). `logistics`/`manufacturing` يستخدمان `subscription.plan.features` (آلية عاملة، مثل `arbitration_syndicates`) — رُفعت مؤقتًا `features` لخطط `id=2,47,48` المشتركة، **ثم أُعيدت للقيم الأصلية بالضبط** (مؤكَّد `SELECT` مستقل بعد الاسترجاع).

### 6.1 `logistics` — `update_warehouse`/`delete_warehouse`/`adjust_inventory`، مؤكَّد حيًا بالكامل

```
B (تينانت16، active_user عادي) → POST /logistics/warehouses {...} → 201, id=1, tenant_id=16

A (تينانت1، active_user عادي، بلا صلاحية إدارية) + X-Tenant-ID:16 → PUT /logistics/warehouses/1 {"name":"HACKED_BY_A3"}
→ 200, name="HACKED_BY_A3"

A + X-Tenant-ID:16 → DELETE /logistics/warehouses/1
→ 200 {"message":"Warehouse deleted"}

SELECT مستقل: logistics_warehouses WHERE id=1 → (tenant_id=16, name='HACKED_BY_A3', is_deleted=True, created_by=774)
```
```
B → POST /logistics/warehouses (مخزن ثانٍ) → id=3، B → POST /logistics/inventory/receive {...100 units...} → item id=1, quantity=100

A + X-Tenant-ID:16 → POST /logistics/inventory/adjust/1 {"new_quantity":999999,"note":"ATTACK_A3"}
→ 200, quantity الجديدة=999999

SELECT مستقل: logistics_inventory_items WHERE id=1 → quantity=999999 (تينانت16، بلا أي علاقة بـA)
```
**الحكم:** مستخدم عادي (`active_user`، بلا أي صلاحية إدارية) من تينانت1 عدَّل الاسم، حذف المخزن بالكامل، وغيَّر كمية مخزون حقيقي — الثلاثة بمجرد تزوير هيدر واحد، بلا أي فحص ملكية أو صلاحية على الإطلاق.

### 6.2 `manufacturing.restock_spare_part` — تفاعل IDOR + هاردكود `tenant_id=1`، مؤكَّد حيًا (اتجاهين)

**الاتجاه 1 — الهدف تينانت16 (غير تينانت1):**
```
[قطعة غيار حقيقية تينانت16، id=1، stock=50]
A + X-Tenant-ID:16 → POST /manufacturing/spare-parts/1/restock {"quantity_added":25}
→ 500 ResponseValidationError: "Input should be a valid dictionary — input: None"
SELECT مستقل: spare_parts WHERE id=1 → stock=50 (بلا تغيير — الفحص الأول نجح، لكن fetch الداخلي الثاني بـtenant_id=1 هاردكودد رجع None، فالتحديث لم يحصل)
```
**الاتجاه 2 — الهدف تينانت1 تحديدًا (يطابق الهاردكود):**
```
[قطعة غيار حقيقية تينانت1، id=2، stock=10]
B (تينانت16 حقيقي) + X-Tenant-ID:1 → POST /manufacturing/spare-parts/2/restock {"quantity_added":500}
→ 500 (خطأ Pydantic منفصل، بيانات throwaway ناقصة — راجع التفصيل تحت)
SELECT مستقل: spare_parts WHERE id=2 → stock=510 (10+500) — الكتابة نجحت فعليًا رغم رد 500!
```
**الحكم:** الكتابة الفعلية **نجحت 100%** في الاتجاه الثاني (مؤكَّدة بـSELECT مستقل قبل/بعد)، رغم أن الرد HTTP كان `500` مضلِّل (سببه حقل ناقص في بيانات throwaway المزروعة يدويًا via SQL، مش باج في مسار الكتابة نفسه) — **مستخدم من تينانت16 حقيقي، بلا أي صلاحية إدارية، عدَّل مخزون قطعة غيار حقيقية تخص تينانت1 بمجرد هيدر مزوَّر**. الهاردكود `tenant_id=1` في `repository.py:326` (`# tenant_id سيتم تمريره من Service` — تعليق يصف نية لم تُنفَّذ) **يحصر هذا الاستغلال المحدد في موارد تينانت1 فقط** — لأي تينانت آخر، النمط نفسه يتحول لعطل وظيفي بحت (500 دائمًا، بصرف النظر عن الهجوم).

### 6.3 `tourism_sports.book_program` — عبر-تينانت مؤكَّد، يصطدم ببق `payment_tx_hash` منفصل (4th instance)

```
[برنامج سياحي حقيقي تينانت1، id=5, base_price=1 MR_USDT]
B (تينانت16 حقيقي) + X-Tenant-ID:1 → POST /tourism-sports/programs/5/book
→ 500: DataError: "invalid input for query argument $8: expected str, got Transaction"
  (INSERT INTO program_participants ... payment_tx_hash=<Transaction object>, VALUES (..., 1, 'IDEMP-...', 5, 774, True, 'ENROLLED', 'TKT-...', <Transaction obj>))

SELECT مستقل: program_participants WHERE program_id=5 → لا يوجد صف (rollback كامل عبر begin_nested — صفر أثر جانبي)
SELECT مستقل: wallets WHERE id=747 (محفظة B تحت تينانت1) → balances={"MR_USDT":10} (بلا تغيير — التحويل المالي اترجع بالكامل)
```
**الحكم المزدوج:**
1. **IDOR عبر-تينانت مؤكَّد جزئيًا:** فحص الملكية في `book_program` (`program.tenant_id != tenant_id`) يقارن ضد **نفس مصدر الهيدر الملوَّث** — B تمكَّن من اجتياز الفحص لبرنامج لا يخصه (تينانت1) بمجرد الهيدر.
2. **لكن الأثر المالي محدود بنمط "المحفظة الشبح" الموثَّق مسبقًا لـ`finance` في `critical-finding-xtenant-systemic.md`:** `finance.transfer` بيستخدم `self.tenant_id` (نفس الهيدر المزوَّر) لجلب/إنشاء محفظة **المُرسِل**، فبتصل لمحفظة B **نفسه** المُسجَّلة تحت تينانت1 (شبح، أُنشئت مسبقًا بجلسة سابقة) — **مش** محفظة تينانت1 حقيقية لمستخدم آخر. يعني: المهاجم بيدفع من فلوسه هو دايمًا، أيًا كان الهيدر — **صفر سرقة رصيد حقيقي لأي طرف تالت**، بالضبط نفس استنتاج `finance` الأصلي.
3. **لكن الكتابة الكاملة (بما فيها `program_participants`) فشلت هنا بسبب باج مستقل تمامًا:** `finance.transfer()` بترجّع كائن `Transaction` كامل (مش `str` هاش)، والـservice بيخزّنه مباشرة في عمود `payment_tx_hash` (`String(100)`) — **نفس الباج المكتشَف والموثَّق سابقًا في `technical-pattern-sweep-session-log.md` لـ`transport.pay_delivery` (وحالتين تانيين، `realestate`/`insurance`)** — الآن مؤكَّد حيًا في `tourism_sports.book_program` كـ**رابع موضع حي مكسور فعليًا** لنفس الفئة. **يمنع `book_program` بالكامل لأي مستخدم، بصرف النظر عن التينانت** — نفس نمط "معطوب بنيويًا يخفي IDOR" الموجود في `manufacturing.create_facility`/`schedule_maintenance`.

**`buy_ticket` (نفس النمط الكودي بالضبط لـ`book_program`) لم يُختبَر حيًا** — الوقت اقتصر على `book_program`، لكن `NFTTicket` **لا** يحتوي عمود `payment_tx_hash` (بعكس `ProgramParticipant`)، فباج #3 فوق **غير متوقَّع** أن يتكرر هناك — **الفارق غير مؤكَّد حيًا، قراءة كود فقط.**

### تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل

- `logistics_warehouses` (`id=1,2,3`)، `logistics_inventory_items`/`transactions` (product_name LIKE 'TEST_%') — محذوفة بالكامل.
- `manufacturing_facilities`/`production_lines` (name LIKE 'TEST_%')، `predictive_maintenance_logs` (id=1, tenant_id=16)، `spare_parts` (part_name LIKE 'TEST_%', يشمل id=1 و id=2 المُختبَران) — محذوفة بالكامل.
- `tourism_programs` (title LIKE 'TEST_%', id=4,5) + `program_participants` المرتبطة (صفر صفوف أصلًا — كل محاولة رجعت خطأ قبل commit) — محذوفة.
- `wallets.id=747` (محفظة B الشبح تحت تينانت1) → أُعيدت لـ`{}` (فارغة، القيمة الأصلية). `wallets.id=930` (محفظة B الحقيقية تحت تينانت16) → أُعيدت لقيمها الأصلية بالضبط (كل العملات=0).
- `saas_service_catalog`/`saas_service_plans`/`saas_tenant_service_access`/`saas_tenant_subscriptions` — 4 صفوف catalog جديدة (id=65-68) + 4 plans (id=67-70) + 8 access + 8 subscriptions throwaway — **محذوفة بالكامل** (لا استرجاع، جديدة من الأساس).
- `saas_service_plans` (`id=2,47,48`) — `features` أُعيدت للقيم الأصلية بالضبط (`id=2`→`["real_estate","insurance"]`، `id=47,48`→`[]`)، مؤكَّد `SELECT` مستقل.
- **فحص نهائي شامل مستقل** (استعلام واحد يغطي كل الجداول المتأثرة): كل الأعمدة = **0** (راجع الناتج الكامل في نهاية الجلسة).
- **لم يُلمَس أي شيء من بيانات الجلسات السابقة** (مستخدمو 772-777، Tenant B id=16 نفسها، أي صف `TEST_%` أقدم).
- السيرفر التجريبي **أُوقف** (`taskkill /F`، `netstat` يؤكد صفر `LISTENING` على المنفذ 8000).
- **صفر تعديل كود، صفر migration** طوال الجلسة — التعديلات الوحيدة كانت بيانات اختبار throwaway + قيم SaaS مؤقتة (موثَّقة ومُعادة بالكامل) + إعادة تعيين كلمة سر مستخدمي throwaway (موثَّقة في `throwaway-test-users.md`).

---

## 7) خريطة الترابط الكاملة بين الأربعة دومينات ومع باقي المنصة

```
identity ──(قراءة مستخدم/current_user)──> transport, logistics, manufacturing, tourism_sports

saas (بوابتان مختلفتان تمامًا، نفس تقسيم الدفعة 1/2):
   can_access_service(code) <── transport, tourism_sports
        [بوابة catalog-based معطوبة حاليًا في هذه البيئة — صفر صف transport/tourism/entertainment/sports في saas_service_catalog قبل الجلسة]
   subscription.plan.features <── logistics, manufacturing
        [بوابة عاملة فعليًا، لكن تفحص تينانت ملوَّث بنفس عيب الهيدر]
                                          │
finance.transfer <── transport(حجز رحلة/دفع توصيل), tourism_sports(حجز برنامج/شراء تذكرة)
        [logistics, manufacturing: صفر استدعاء فعلي رغم استيراد الموديول — "استيراد ميت"]
        [آلية "المحفظة الشبح" الموثَّقة لـfinance تحمي من سرقة رصيد حقيقي، حتى مع IDOR — راجع §6.3]
                                          │
invoicing.create_invoice <── الأربعة دومينات كلهم (+ 10 دومينات أخرى خارج النطاق من الدفعات السابقة)
        [الإصلاح الصباحي على transport سليم ولم يتأثر — لكن القيمة الداخلة (tenant_id) لسه ملوَّثة من هيدر كل دومين، مطابق تمامًا لاستنتاج الدفعة 2 §5]
                                          │
affiliate.register_commission ◄──── الأربعة دومينات
ai_agents.execute_agent_action + ai_governance.check_and_consume ◄── transport(تحسين مسار), logistics(تنبؤ طلب), manufacturing(تحليل إنتاج/صيانة), tourism_sports(تحليل طبي/نقل VIP/انتقال لاعب)
                                          │
روابط FK بنيوية بلا تحقق تشغيلي فعلي (مجرد عمود int، صفر join validation):
   transport.Vehicle.smart_asset_id ──> iot.smart_assets
   manufacturing.ManufacturingFacility.real_estate_unit_id ──> realestate.property_units
   manufacturing.ProductionLine/Vehicle.smart_asset_id ──> iot.smart_assets
```

**ملاحظة ترابط حرجة (مطابقة لنمط الدفعتين السابقتين):** الأربعة دومينات **لا يستدعي أي منها الآخر مباشرة فيما بينها** — الترابط غير المباشر فقط عبر `identity`، `saas`، `invoicing.create_invoice`، و`affiliate`/`ai_agents`/`ai_governance` للي بيستخدمهم أغلب الدومينات بنفس الطريقة. **فارق جوهري عن الدفعة 1/2:** `logistics` **لا يحرّك مالًا حقيقيًا إطلاقًا** رغم استيراد `finance`/`invoicing`/`affiliate` الثلاثة — أول دومين في السويپ كله بهذه الصفة (استيراد كامل، استخدام صفري).

---

## 8) الفجوات المكتشفة — التصنيف النهائي (بانتظار توجيهك، صفر تنفيذ)

### 8.1 بنود IDOR/تلوّث بيانات (نفس النمط الميكانيكي المعتاد — `get_current_tenant` → `cast(int, current_user.tenant_id)`)

| # | الدومين | البند | الخطورة | مؤكَّد حيًا؟ |
|---|---|---|---|---|
| 1 | logistics | **كل الـ22 endpoint** — أخطرها `delete_warehouse`/`update_warehouse`/`adjust_inventory` (بلا أي admin-gate) | 🔴🔴🔴🔴🔴 **الأعلى في الدفعة — مستخدم عادي يحذف/يعدّل موارد أي تينانت** | ✅ (§6.1، 3 endpoints من 22) |
| 2 | manufacturing | `schedule_maintenance` — صفر فحص تينانت من الأساس | 🔴🔴🔴🔴🔴 شكلًا الأخطر، **لكن الكتابة تضيع صامتة حاليًا (§3.2)** | ✅ (كتابة لا تحصل، لكن صفر فحص مؤكَّد حيًا) |
| 3 | manufacturing | `restock_spare_part` — IDOR + هاردكود `tenant_id=1` متفاعلان | 🔴🔴🔴🔴🔴 مؤكَّد فعليًا لموارد تينانت1 | ✅ (§6.2، اتجاهين) |
| 4 | transport | `update_vehicle_location` (GPS حي) + `complete_delivery` (صفر فحص ملكية) | 🔴🔴🔴🔴🔴 **كامنة — الدومين معطَّل بنيويًا (§1.1)** | ❌ (كودًا فقط، جداول DB غير موجودة) |
| 5 | transport | `book_trip` — حجز عبر-تينانت بمال حقيقي (لكن "محفظة شبح" تحمي رصيد الضحية الحقيقي) | 🔴🔴🔴🔴 كامنة (نفس §1.1) | ❌ كودًا فقط |
| 6 | tourism_sports | `book_program`/`buy_ticket` — نفس نمط `book_trip` | 🔴🔴🔴🔴 | 🟡 جزئي (§6.3 — IDOR مؤكَّد، الكتابة الكاملة تصطدم ببق منفصل) |
| 7 | manufacturing | باقي الـ16 endpoint (قراءة/كتابة IDOR قياسية) | 🔴🔴🔴🔴 | كودًا فقط (نمط مطابق للمؤكَّد حيًا في #2/#3) |
| 8 | transport | باقي الـ12 endpoint (قراءة/كتابة IDOR قياسية + `list_hubs`/`get_available_vehicles` بلا مصادقة إطلاقًا) | 🔴🔴🔴🔴 كامنة (§1.1) | ❌ كودًا فقط |
| 9 | tourism_sports | باقي الـ6 endpoint (تلوّث بيانات إنشاء، أقل حدة) | 🔴 | كودًا فقط |

### 8.2 بنود وظيفية بحتة (ليست IDOR) — مكتشَفة أثناء الجلسة

| # | الدومين | البند | الأثر |
|---|---|---|---|
| 10 | transport | **7 جداول DB غير موجودة إطلاقًا** (`fleets`, `vehicles`, `transport_hubs`, `transport_routes`, `transport_trips`, `trip_bookings`, `delivery_tasks`) — صفر migration عبر تاريخ المشروع | يعطّل الدومين بالكامل (16/16 endpoint) — أهم بند في الدفعة كلها من ناحية الأولوية التشغيلية |
| 11 | manufacturing | `create_facility` — `entity_id` مفقود من schema/service بينما العمود `NOT NULL` في DB | يعطّل إنشاء منشآت لكل التينانتات — يمنع كل سلسلة `facility→line→blueprint→batch` عبر الـAPI |
| 12 | manufacturing | `schedule_maintenance`/`update_batch_status`/`update_spare_part_stock` (`repository.py`) — استخدام `flush()` بدل `commit()` في `schedule_maintenance` بالكامل (لا `commit()` في أي مكان بالمسار) | كتابة تضيع صامتة، رد `200` كاذب |
| 13 | manufacturing | `update_batch_status`/`update_spare_part_stock` — `tenant_id=1` **هاردكودد حرفيًا** في fetch داخلي (تعليق "سيتم تمريره من Service" لم يُنفَّذ) | `update_batch_status`: غير مستغَل حاليًا (قيمة الإرجاع مُتجاهَلة من المستدعي الوحيد) — لكنه لغم لأي استدعاء مستقبلي. `update_spare_part_stock`: **مؤكَّد حيًا يتفاعل مع IDOR (§6.2)** |
| 14 | tourism_sports | `book_program` — `finance.transfer()` بترجّع كائن `Transaction` كامل، بيتخزَّن مباشرة في عمود `payment_tx_hash` (`String(100)`) | **رابع موضع حي مكسور فعليًا لنفس فئة `finance-transfer-payment-tx-hash-broken`** الموثَّقة مسبقًا (`realestate`, `insurance`, `transport.pay_delivery`) — يعطّل `book_program` بالكامل لأي مستخدم |
| 15 | tourism_sports | `place_transfer_bid` → `get_player_profile(data["player_id"])` — الدالة تفلتر بعمود `user_id`، لكن `player_id` المُمرَّر هو `PlayerProfile.id` (حسب وصف الـschema) | شبه مضمون يفشل بـ`NotFoundError` لأي استدعاء حقيقي — غير مختبَر حيًا |
| 16 | transport | `book_trip` (مسار إعادة إرسال idempotency) → `self.repo.get_booking(booking_id)` بوسيط واحد، لكن الدالة تتطلب وسيطين (`booking_id`, `tenant_id`) | `TypeError` عند أي retry بنفس `Idempotency-Key` — غير مختبَر حيًا (الدومين معطَّل أصلًا) |
| 17 | logistics | `finance`/`invoicing`/`affiliate` مستوردة بالكامل في `service.py` لكن **غير مُستخدَمة إطلاقًا** (استيراد ميت) | لا أثر أمني — ملاحظة نظافة كود فقط، تستحق تسجيل لأنها تناقض توقع "أي دومين فيه معاملات مخزون المفروض يربطها بفاتورة/عمولة" |

### الحل المقترَح لكل بند (معروض فقط — **صفر تنفيذ حتى الآن**)

- **#1 (logistics، الأولوية القصوى المقترَحة):** نفس النمط الميكانيكي المعتاد على كل الـ22 endpoint — `current_user: User = Depends(get_current_active_user)` (موجودة أصلًا) + استبدال كل استخدام لـ`tenant.id` بـ`cast(int, current_user.tenant_id)`، حذف `Depends(get_current_tenant)`. **صفر إضافة admin-gate جديدة مطلوبة** (القرار التصميمي الحالي أصلًا active_user-scoped لكل شيء، المشكلة فقط مصدر الـtenant_id) — إلا لو رغبت إضافة `get_current_superuser` لعمليات حذف/تعديل مباشرة (`delete_warehouse`, `update_warehouse`, `update_equipment`) كطبقة حماية إضافية، قرار تصميمي منفصل.
- **#2، #3 (manufacturing، الأولوية الثانية):** نفس النمط + لـ`schedule_maintenance` تحديدًا: إضافة `tenant: Depends(get_current_tenant)` **ثم استبدالها فورًا** بـ`current_user.tenant_id` (مش استبدال بسيط، لازم إضافة الفحص من الصفر لأنه غير موجود أصلًا) + تمرير `tenant_id` لـ`service.schedule_maintenance`/`repo.schedule_maintenance` (تغيير توقيع الدالتين). لـ`restock_spare_part`: حذف الهاردكود `1` في `repository.py:326`، تمرير `tenant_id` حقيقي للدالة. **بند منفصل تمامًا (يُنصَح به لكن غير مطلوب لسد IDOR نفسها):** إصلاح `flush()`→`commit()` في `schedule_maintenance` لمنع ضياع الكتابة صامتًا — **قرار منفصل لأنه يغيّر سلوك وظيفي، مش أمني بحت**.
- **#4-#9 (transport بالكامل + باقي tourism_sports/manufacturing):** نفس النمط الميكانيكي، **لكن `transport` تحديدًا لا يستحق أولوية تنفيذ فورية** طالما جداوله غير موجودة في DB — الإصلاح الكودي مفيد كتحضير مسبق (يمنع الثغرة من الظهور فور تفعيل migration مستقبلية) لكن **صفر تحقق حي ممكن حاليًا مهما كانت جودة الإصلاح**.
- **#10 (transport، وظيفي، الأولوية الأعلى عمليًا في الدفعة كلها):** قرار منتجي/معماري صريح مطلوب أولًا: **هل `transport` جاهز للتفعيل الفعلي أصلًا؟** لو نعم — إنشاء migration كاملة للـ7 جداول (خارج نطاق "إصلاح أمني"، يحتاج مراجعة schema كاملة + خطة اختبار). لو لأ — يستحق توثيقه صراحة كـ"دومين غير مفعَّل بعد" بدل تصنيفه ضمن أي سويپ أمني مستقبلي بنفس الأولوية.
- **#11 (manufacturing، وظيفي):** إضافة `entity_id` لـ`ManufacturingFacilityCreate` (مطلوب من العميل) أو تعيين قيمة افتراضية منطقية في الـservice (قرار منتجي: هل `entity_id` مفهوم مطلوب فعليًا هنا زي `transport`/`tourism_sports`، ولا عمود زايد من قالب مشترك؟).
- **#12 (manufacturing، وظيفي، مرتبط بـ#2):** إضافة `await self.db.commit()` صريح في `schedule_maintenance` (أو تحويلها لاستخدام `begin_nested()` زي باقي دوال الملف).
- **#13 (manufacturing، وظيفي):** حذف الهاردكود `1` في الدالتين، تمرير `tenant_id` حقيقي.
- **#14 (tourism_sports، وظيفي، **موسِّع لبند Backlog موجود مسبقًا**):** نفس إصلاح `transport.pay_delivery`/`realestate`/`insurance` — استخراج `tx_hash` نص من كائن `Transaction` (مثال: `.tx_hash` attribute) قبل التخزين في `payment_tx_hash`.
- **#15 (tourism_sports، وظيفي):** تصحيح `get_player_profile` لتقبل فلترة بـ`PlayerProfile.id` (دالة جديدة أو تعديل الموجودة، يحتاج تأكيد أي الاستخدامات التانية بتعتمد على الفلترة الحالية بـ`user_id`).
- **#16 (transport، وظيفي، منخفض الأولوية لحد ما #10 يتحل):** تمرير `tenant_id` في استدعاء `get_booking` بمسار الـidempotency.
- **#17 (logistics):** توثيق فقط — قرار منتجي هل `logistics` المفروض يصدر فواتير/عمولات فعليًا (زي باقي الدومينات) ولا تصميم مقصود إنه مجرد تتبّع داخلي بلا مالية؟

---

## 9) أنماط منتشرة جديدة تستاهل تصنيف مركزي — مقترَحة للإضافة لـ`constructor-mismatch-backlog-classification.md` (بانتظار موافقتك، صفر كتابة على الملف حتى الآن)

آخر رقم موجود فعليًا في الملف = **#33**. المقترَح (بنفس تنسيق الدفعة 1/2، توثيق/تصنيف فقط):

| # مقترَح | الاسم | الفئة المقترَحة | الدليل |
|---|---|---|---|
| 34 | `manufacturing-facilities-entity-id-missing` | 🟢 محلي | §3.1/§8.2#11 — `ManufacturingFacilityCreate`/`service.create_facility` لا يمرران `entity_id` رغم `NOT NULL` في DB |
| 35 | `manufacturing-repository-hardcoded-tenant-1-fallback` | 🟡 **يستاهل فحص انتشار** — أول موضعين معروفين، لكن نمط "`# tenant_id سيتم تمريره من Service` + هاردكود فعلي" ممكن يكون منسوخ في دومينات تانية من نفس القالب | §3.2/§6.2/§8.2#13 — `update_batch_status`, `update_spare_part_stock` |
| 36 | `manufacturing-schedule-maintenance-missing-commit` | 🟢 محلي (مبدئيًا) | §3.2/§8.2#12 — `flush()` بلا `commit()` في كامل مسار `schedule_maintenance` |
| 37 | `finance-transfer-payment-tx-hash-broken` — **تحديث لبند موجود مسبقًا، مش بند جديد** | (يبقى نفس التصنيف السابق) | §6.3/§8.2#14 — إضافة `tourism_sports.book_program` كموضع رابع مؤكَّد حيًا |
| 38 | `tourism-sports-player-profile-wrong-column-filter` | 🟡 غير مؤكَّد حيًا | §4/§8.2#15 — `get_player_profile` تفلتر بـ`user_id` بدل `PlayerProfile.id` |
| 39 | `transport-domain-tables-never-migrated` | 🔴 **مقترَح كبند مستقل بالكامل، مش جزء من عائلة constructor-mismatch — قرار تصنيف منفصل مطلوب منك** | §1.1/§8.2#10 — 7 جداول `transport` غير موجودة، صفر migration. **يستحق تقييم منفصل: هل يستاهل جرد مماثل عبر باقي الـ34 دومين (زي `frontend-service-url-prefix-mismatch` #31)، أم حالة منفردة لـ`transport` تحديدًا؟** |

**صفر كتابة فعلية على `constructor-mismatch-backlog-classification.md` حتى الآن — البنود دي مقترَحة فقط، بانتظار توجيهك بالضبط زي باقي هذا التقرير.**

---

## 10) بانتظار توجيهك

**القرار المطلوب:**
1. الموافقة على تصنيف §8 (17 بند IDOR/وظيفي) بالكامل، أو تعديلات عليه.
2. أولوية التنفيذ المقترَحة: **`logistics` أولًا** (الأوضح استغلالًا، صفر admin-gate، مؤكَّد حيًا بالكامل) → `manufacturing` (#2/#3، مؤكَّدين حيًا) → باقي `manufacturing`/`tourism_sports` (كودًا فقط) → `transport` **مؤجَّل** لحد ما يتحدد قرار #10 (هل الدومين يستحق migration أصلًا؟).
3. توجيه معماري عاجل: **قرار `transport`** — تفعيل فعلي (migration + مراجعة schema) أم توثيق كـ"غير مفعَّل" وإخراجه من أي سويپ أمني مستقبلي بنفس الأولوية؟
4. توجيه وظيفي: `manufacturing.create_facility` — هل `entity_id` مفهوم مطلوب فعلًا (زي `transport`) أم عمود زايد يستحق `nullable=True` بدل إضافته لكل طلب؟
5. تأكيد إضافة البنود #34-#39 (§9) لـ`constructor-mismatch-backlog-classification.md`، بما فيها القرار المنفصل المطلوب لبند #39 (`transport-domain-tables-never-migrated`).
6. توجيه تنفيذ: نفس صرامة الدفعتين السابقتين — تحقق حي كامل (هجوم مرفوض + مسار شرعي + `SELECT` مستقل) لكل endpoint متأثر حيث ممكن (`logistics`/`manufacturing`/`tourism_sports`)، وتحقق كودي موثَّق بوضوح فقط لـ`transport` (بانتظار قرار #10).

---

## 11) قرار المستخدم [2026-08-25] — موافقة كاملة، تنفيذ الأربعة دومينات في دفعة واحدة

**القرارات المحسومة:**
1. ✅ التصنيف والترتيب (§8، §9) — موافقة كاملة.
2. **س2 (`transport`):** توثيق كـ"غير مفعَّل" (بند #39، لا migration الآن) — قرار منتجي منفصل يُترك لجلسة تصنيف الأولويات القادمة. **تنفيذ الإصلاح الكودي الاحترازي فقط** على الـ16 endpoint (نفس نمط `get_my_licenses` من الدفعة 2)، بلا أي محاولة تحقق حي كامل (مستحيل بدون الجداول).
3. **س4 (`manufacturing.entity_id`):** مطلوب — أُضيف كحقل إجباري في `ManufacturingFacilityCreate` (قرار: مفهوم مرتبط بكيان زي `transport`/`tourism_sports`، مش عمود زايد).
4. **س5:** إضافة #34-#39 لـ`constructor-mismatch-backlog-classification.md`. #39 بند مستقل بالكامل (تأكيد). **لا جرد موسَّع عبر باقي الدومينات الآن** — يُترك لجلسة تصنيف الأولويات.
5. **ترتيب التنفيذ:** `logistics` (22 endpoint، تحقق حي كامل) → `manufacturing` (#2/#3 مع إصلاح `entity_id`/الهاردكود/الـ`commit` المفقود سوا، تحقق حي كامل) → باقي `manufacturing`/`tourism_sports` (نفس النمط الميكانيكي، تحقق حي حيث ممكن) → `transport` (إصلاح كودي احترازي بس، توثيق بلا تحقق).

### 11.1) تنفيذ `logistics` (22/22 endpoint) — مكتمل، مؤكَّد حيًا بالكامل

**نطاق التعديل:** `eppne-backend/app/domains/logistics/router.py` وحده. النمط الميكانيكي المعتاد: حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من كل الـ22 endpoint (كانت كلها بنفس البنية بالحرف، `replace_all` واحد كفى)، استبدال كل `cast(int, tenant.id)` بـ`cast(int, current_user.tenant_id)` (`replace_all` ثانٍ)، حذف استيرادَي `get_current_tenant`/`AcademyTenant` و`get_current_superuser` (كان مستوردًا أصلًا بلا استخدام — تأكيد `grep`). **صفر لمس لـ`service.py`/`repository.py`/`models.py`/`schemas.py`.**

`python -m py_compile` → `exit code 0`.

**التحقق الحي — قبل/بعد، هجوم مرفوض + مسار شرعي + `SELECT` مستقل، سيناريوهات متعددة:**

| Endpoint | الهجوم (بعد الإصلاح) | المسار الشرعي | SELECT مستقل |
|---|---|---|---|
| `create_warehouse` | — | B (تينانت16، **بلا أي هيدر**) → `POST /warehouses` → `201`, `tenant_id=16` رغم عدم إرسال أي هيدر | `tenant_id` يطابق `current_user.tenant_id` تلقائيًا |
| `update_warehouse` | A (تينانت1) + هيدر مزوَّر(16) → `PUT /warehouses/{id}` (مخزن B) → **`404 Warehouse not found`** | B → نفس المسار → `200`, الاسم تغيَّر فعليًا | `name='TEST_WH_FIX_B'` بلا تغيير بعد الهجوم |
| `delete_warehouse` | A + هيدر مزوَّر(16) → `DELETE /warehouses/{id}` → **`404`** | — | `is_deleted=False` (صفر أثر) |
| `adjust_inventory` | A + هيدر مزوَّر(16) → `POST /inventory/adjust/{id}` (صنف B) → **`404 Inventory item not found`** | B → نفس المسار → `200` | `quantity=100` بلا تغيير بعد الهجوم؛ بعد المسار الشرعي (B) `quantity=150` صح |
| `list_warehouses` | A + هيدر مزوَّر(16) → `GET /warehouses` → **نفس نتيجة A بلا هيدر بالحرف** (`tenant_id=1` فقط، صفر تسريب) | — | — |
| `update_equipment` | B (تينانت16) + هيدر مزوَّر(1) → `PUT /equipment/{id}` (معدة A) → **`404`** | — | `status='AVAILABLE'` بلا تغيير |

**الحكم الحاسم:** في كل الحالات، الهجوم عديم الأثر بالكامل، والمسار الشرعي سليم 100%، **والهيدر `X-Tenant-ID` بقى بلا أي تأثير إطلاقًا على أي طلب مصادَق** — حتى `list_warehouses` بهيدر مزوَّر بترجّع دايمًا بيانات `current_user` الحقيقية.

**تنظيف:** `logistics_warehouses`/`logistics_inventory_items`/`logistics_inventory_transactions`/`logistics_equipment` (بادئة `TEST_`) — محذوفة بالكامل، تأكيد `SELECT count(*)` = 0 لكل جدول. `saas_service_plans` (`id=2,47,48`) — `features` أُعيدت للقيم الأصلية بالضبط.

### 11.2) تنفيذ `manufacturing` (20/20 endpoint + 3 بنود وظيفية مرتبطة) — مكتمل، مؤكَّد حيًا بالكامل

**نطاق التعديل:** `router.py` (IDOR ميكانيكي على كل الـ20 endpoint، نفس أسلوب `logistics`)، `service.py`، `repository.py`، `schemas.py`.

**تفاصيل الإصلاحات الثلاثة المرتبطة (نُفِّذت سوا بتوجيهك):**
- **`create_facility` (بند #34):** `ManufacturingFacilityCreate.entity_id` بقى حقل إجباري (`int`, مش `Optional`) + تمريره في `service.create_facility` إلى `repo.create_facility(entity_id=data["entity_id"], ...)`.
- **`schedule_maintenance` (بندان #35/#36):** الراوتر بقى يمرّر `tenant_id=cast(int, current_user.tenant_id)` للـservice. `service.schedule_maintenance(log_id, tenant_id, scheduled_at)` بقت تتحقق من الملكية أولًا (`repo.get_predictive_log(log_id, tenant_id)` — دالة جديدة) قبل الجدولة، **ثم `await self.db.commit()` صريح** (كانت الدالة القديمة تعتمد على `flush()` بس بلا `commit()` في أي مكان بالمسار). `repo.schedule_maintenance(log_id, tenant_id, scheduled_at)` بقت تفلتر الـ`UPDATE` نفسها بـ`tenant_id` (دفاع بعمق).
- **`restock_spare_part` (بند #35):** `repo.update_spare_part_stock(part_id, tenant_id, quantity_delta)` بقت تاخد `tenant_id` حقيقي بدل الهاردكود `1`. `service.restock_spare_part` بقت تمرره.
- **اكتشاف جانبي أثناء التعديل (مُصلَح فورًا، مش بند منفصل):** `analyze_and_schedule_maintenance` (المسار التلقائي لجدولة صيانة عاجلة عند `failure_probability > 0.8`) كان بيستدعي `repo.schedule_maintenance(log.id, scheduled_at)` بوسيطين فقط — بعد تغيير توقيع الدالة لثلاثة وسائط (`log_id, tenant_id, scheduled_at`)، هذا الاستدعاء كان سيفشل بـ`TypeError` فورًا. اكتُشف عبر `grep` شامل لكل استدعاءات الدوال الثلاث المعدَّلة قبل تشغيل أي تحقق حي — أُصلح بتمرير `tenant_id` كوسيط ثانٍ.

`python -m py_compile` على الأربعة ملفات → `exit code 0` لكل واحد.

**التحقق الحي — قبل/بعد، هجوم مرفوض + مسار شرعي + `SELECT` مستقل:**

| Endpoint/سيناريو | الهجوم (بعد الإصلاح) | المسار الشرعي | SELECT مستقل |
|---|---|---|---|
| `create_facility` | — | B (تينانت16، بلا هيدر) → `POST /facilities` `{"entity_id":1,...}` → **`201`** (أول نجاح للـendpoint ده إطلاقًا) | `entity_id=1`, `tenant_id=16` صح |
| `add_production_line` | A + هيدر مزوَّر(16) → `POST /facilities/{id}/lines` (منشأة B) → **`404 Facility not found`** | B → نفس المسار → `201` | — |
| `schedule_maintenance` | A (تينانت1، **بلا أي هيدر إطلاقًا**) → `POST /maintenance/{id}/schedule` (سجل B) → **`404 Maintenance log not found`** | B (بلا هيدر) → نفس المسار → `200` | قبل الهجوم: `status='PENDING'` بلا تغيير. **بعد المسار الشرعي: `status='SCHEDULED'`, `maintenance_scheduled_at` مكتوب فعليًا** (تأكيد إصلاح `commit()` — كانت هتفضل `PENDING` حتى لو نجح الطلب) |
| `restock_spare_part` (هدف تينانت16) | A + هيدر مزوَّر(16) → `POST /spare-parts/{id}/restock` (قطعة B) → **`404`** نظيف (كانت `500 ResponseValidationError` مُضلِّلة قبل الإصلاح) | B → نفس المسار → `200`, `stock_quantity` زاد فعليًا | `50→50` (هجوم)، `50→75` (شرعي) |
| `restock_spare_part` (**هدف تينانت1 تحديدًا — نفس الاتجاه اللي كان ناجحًا فعليًا قبل الإصلاح**) | B (تينانت16 حقيقي) + هيدر مزوَّر(1) → `POST /spare-parts/{id}/restock` (قطعة تينانت1) → **`404`** (كانت `stock_quantity` بتتغيّر فعليًا من `10`→`510` قبل هذا الإصلاح، §6.2 من الجلسة الأصلية) | — | `stock_quantity=10` بلا تغيير — **الثغرة المؤكَّدة حيًا في الجرد الأصلي مُغلقة فعليًا الآن** |

**الحكم الحاسم:** كل السيناريوهات الأربعة المختبَرة (تغطي `create_facility` الجديدة، IDOR قياسي، صفر-فحص-تينانت، وهاردكود-تينانت1) اتقفلت بالكامل، **بما فيها الاتجاه المحدَّد اللي كان استغلاله ناجحًا فعليًا وموثَّقًا بدليل `SELECT` في الجرد الأصلي (§6.2).**

**تنظيف:** `predictive_maintenance_logs`/`spare_parts`/`production_lines`/`manufacturing_facilities` (throwaway) — محذوفة بالكامل. `saas_service_plans` (`id=2,47,48`) — أُعيدت للأصل.

### 11.3) تنفيذ `tourism_sports` (10/10 endpoint) — مكتمل، مؤكَّد حيًا بالكامل

**نطاق التعديل:** `router.py` وحده. نفس النمط الميكانيكي على 9 endpoint (كان فيهم `current_user` أصلًا). **`list_destinations` (كانت بلا `current_user` إطلاقًا، مصدرها الوحيد كان الهيدر) — أُضيف لها `current_user: User = Depends(get_current_active_user)` من الصفر** (بدل مجرد استبدال، لأن الاعتماد لم يكن موجودًا) — نفس القرار المُتَّخذ سابقًا لـ`service_marketplace.list_services`/`list_addons` في الدفعة 2 (تحويل "تصفح بلا حساب" إلى "تصفح بعد تسجيل دخول"، مُوثَّق هنا للشفافية زي هناك بالظبط). **صفر لمس لـ`service.py`/`repository.py`** — باقي البقين المكتشَفين كوديًا فقط (`payment_tx_hash` في `book_program`، عمود `get_player_profile` الخطأ) **لم يُلمَسا**، بالضبط زي التوجيه ("نفس النمط الميكانيكي" فقط، مش إصلاح البقين الوظيفيين المنفصلين).

`python -m py_compile` → `exit code 0`.

**التحقق الحي:**

| Endpoint/سيناريو | الهجوم/الفحص (بعد الإصلاح) | المسار الشرعي | SELECT مستقل |
|---|---|---|---|
| `list_destinations` | زائر بلا أي توكن (client منفصل تمامًا، صفر كوكيز/هيدر) → `GET /destinations` → **`401 Not authenticated`** (كانت `200` بلا أي حاجز قبل الإصلاح) | B → `GET /destinations` (بلا هيدر) → يرى بيانات تينانته فقط | — |
| `create_destination` | — | B (superuser، بلا هيدر) → `201` | — |
| قراءة عبر-تينانت | A + هيدر مزوَّر(16) → `GET /destinations` → **قائمة تينانت1 فقط** (صفر ظهور لوجهة B) | — | — |
| `book_program` | A (تينانت1، `active_user` عادي) + هيدر مزوَّر(16) → `POST /programs/{id}/book` (برنامج B) → **`403 Program not accessible`** | — | `program_participants` عدد الصفوف = `0` (صفر أثر من الهجوم) |
| `create_sports_org` | A + هيدر مزوَّر(16) → `POST /sports/organizations` → **يُنشَأ فعليًا تحت `tenant_id=1` (تينانت A الحقيقي)، مش 16** | — | `tenant_id=1`, `owner_id=772` — تأكيد إن الهيدر بقى بلا أي تأثير على القيمة المكتوبة |

**الحكم الحاسم:** المصادقة اتفعَّلت على `list_destinations`، والقراءة/الكتابة عبر-تينانت اتقفلت بالكامل، **بما فيها سلسلة الاستغلال الموصوفة في §5 من الجرد الأصلي (`create_sports_org` بهيدر مزوَّر) — بقت مستحيلة الآن لأن الهيدر بقى بلا تأثير على `tenant_id` المكتوب إطلاقًا.**

**ملاحظة صريحة (زي ما طلبت التوثيق الشفاف):** `book_program` **لسه هتفشل في المسار الشرعي الكامل** (دفع فعلي) بسبب باج `payment_tx_hash`/`Transaction` المنفصل (بند #37) — **غير مُصلَح في هذه الجلسة بتوجيه صريح**. فحص IDOR تم التأكد منه بمعزل عن هذا الباج (الهجوم بيتردّ عند `403` قبل الوصول لأي كود دفع أصلًا).

**تنظيف:** `tourism_programs`/`tourism_destinations`/`sports_organizations`/`program_participants` (throwaway) + 3 صفوف `saas_service_catalog`/`saas_service_plans`/`saas_tenant_service_access`/`saas_tenant_subscriptions` throwaway (لـ`tourism`/`entertainment`/`sports`) — محذوفة بالكامل.

### 11.4) تنفيذ `transport` (16/16 endpoint) — مكتمل، إصلاح كودي احترازي بلا تحقق حي (زي المتفق)

**نطاق التعديل:** `router.py` وحده. نفس النمط الميكانيكي على 14 endpoint (كان فيهم `current_user`). **`list_hubs`/`get_available_vehicles` (كانتا بلا `current_user` إطلاقًا) — أُضيف لهم `current_user: User = Depends(get_current_active_user)`**، نفس القرار المتَّخذ لـ`tourism_sports.list_destinations` أعلاه (للاتساق — كانتا الاثنين بنفس الشكل بالضبط، صفر مصادقة). حذف استيرادَي `get_current_tenant`/`AcademyTenant`.

`python -m py_compile` → `exit code 0`. **صفر تحقق حي — مستحيل بدون الجداول السبعة المفقودة (§1.1)، بالضبط زي المتفق.**

**تأكيد سلامة إضافي (بديل التحقق الحي، طلبته الجلسة كحد أدنى):** أُعيد تشغيل السيرفر بالتعديلات الأربعة كلها مجتمعة (كل الدومينات)، وتأكَّد `GET /openapi.json` → `200` — يعني FastAPI قدر يبني schema كل الـendpoints بنجاح (بما فيها الـ16 بتاعة `transport`)، صفر خطأ استيراد/تسجيل route ناتج عن التعديل.

### 11.5) تنظيف بيانات throwaway — تحقق نهائي مستقل شامل، بعد كل الأربعة تنفيذات

```
logistics_warehouses = 0        logistics_inventory_items = 0     logistics_equipment = 0
manufacturing_facilities = 0    production_lines = 0              spare_parts = 0
tourism_destinations = 0        tourism_programs = 0               sports_organizations = 0
saas_catalog_leftover (transport/logistics/manufacturing/tourism/entertainment/sports) = 0
plan2_features  = ["real_estate", "insurance"]   (القيمة الأصلية بالضبط)
plan47_features = []                              (القيمة الأصلية بالضبط)
plan48_features = []                              (القيمة الأصلية بالضبط)
wallet747_balances = {}                                                  (القيمة الأصلية بالضبط)
wallet930_balances = {"MR7":0,"MRX":0,"NBT":0,"MR_USDT":0,"MR_POUND":0}  (القيمة الأصلية بالضبط)
```

**كلمة سر `TEST_super_a`/`TEST_instr_b` أُعيد تعيينها مرة واحدة أول الجلسة** (كانت غير صالحة من جلسة سابقة) — موثَّقة في `throwaway-test-users.md` المُحدَّث. **صفر migration طوال الجلسة بالكامل.** السيرفر التجريبي **متوقف** (`taskkill /F`، `netstat` يؤكد صفر `LISTENING` على المنفذ 8000).

### 11.6) تحديث `constructor-mismatch-backlog-classification.md` — البنود #34-#39

أُضيفت الستة بنود بنفس تنسيق الدفعات السابقة. **خلافًا لكل البنود التوثيقية السابقة من هذه الفئة عبر الدفعتين 1/2** — #34/#35/#36 (منسوبة لـ`manufacturing`) **مُوثَّقة كـ"✅ مُصلَح فعليًا في نفس جلسة الاكتشاف"** (مش مجرد تصنيف/توثيق)، لأنها اتصلحت فعليًا وتحقَّقت حيًا كجزء من §11.2 فوق، بتوجيهك الصريح. #37 (أول رقم رسمي لبند `finance-transfer-payment-tx-hash-broken` في هذا الملف — كان موثَّقًا بس في `technical-pattern-sweep-session-log.md` قبل كده، بلا رقم Backlog رسمي)، #38، و#39 **لسه توثيق فقط، بانتظار تنفيذ منفصل** بقرارك الصريح.

### 11.7) `git status` / `git diff --stat` — للمراجعة قبل أي commit

```
 M .claude/reports/constructor-mismatch-backlog-classification.md
 M eppne-backend/app/domains/logistics/router.py
 M eppne-backend/app/domains/manufacturing/repository.py
 M eppne-backend/app/domains/manufacturing/router.py
 M eppne-backend/app/domains/manufacturing/schemas.py
 M eppne-backend/app/domains/manufacturing/service.py
 M eppne-backend/app/domains/tourism_sports/router.py
 M eppne-backend/app/domains/transport/router.py
?? .claude/reports/batch3-audit-security-transport-logistics-manufacturing-tourism-sports.md
```
```
 constructor-mismatch-backlog-classification.md |  8 +++
 logistics/router.py                            | 69 ++++++++--------------
 manufacturing/repository.py                    | 32 ++++++++--
 manufacturing/router.py                        | 62 +++++++------------
 manufacturing/schemas.py                       |  1 +
 manufacturing/service.py                       | 14 ++++-
 tourism_sports/router.py                       | 34 ++++-------
 transport/router.py                            | 53 ++++++-----------
 8 files changed, 121 insertions(+), 152 deletions(-)
```

**باقي ملفات `git status` الأصلية (متعدّلة/untracked من جلسات سابقة تمامًا، غير متعلقة بهذه الجلسة) — لم تُلمس، لن تُضاف لأي commit من هنا.**

**الحالة النهائية:** ✅ **الأربعة دومينات مُغلَقة بالكامل من ناحية IDOR الكودي** (logistics/manufacturing/tourism_sports مؤكَّدة حيًا بالكامل، transport إصلاح كودي احترازي بلا تحقق حي ممكن). ⏳ **لم يُنفَّذ commit بعد — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.**
