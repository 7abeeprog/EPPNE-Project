# تدقيق شامل على مشروع EPPNE (Backend + Frontend)

> تقرير قراءة فقط — لم يُعدَّل أي كود أثناء إعداد هذا التدقيق.
> تاريخ الإعداد: 2026-08-08
> النطاق: `eppne-backend/` (FastAPI) + `eppne-web/` (Next.js)

ملاحظة منهجية: المشروع يحتوي على 34 دومين في الباك إند، وفحص كل سطر كود في
كل دومين غير ممكن في تدقيق واحد. لذلك تم فحص **كل الدومينز بنيويًا** (وجود
الملفات، `__init__.py`، تغطية `tenant_id`)، وتم أخذ **عينات عميقة** من
الدومينزات الأكثر حساسية (auth، identity، core، academy، communications،
automation، sovereign_entities، iot، privacy، finance، invoicing) لأنها إما
جوهر النظام (الأمان والمصادقة) أو ظهرت عليها مؤشرات مشبوهة أثناء الفحص
البنيوي الأولي. أي حكم مبني على عينة فقط تم توضيحه صراحة.

---

## 1. خريطة الدومينز الفعلية

| الدومين (Backend) | الملفات الموجودة | مكتمل ولا ناقص | ملاحظات |
|---|---|---|---|
| `academy` | models, repository, router, schemas, service, `__init__.py` | ✅ مكتمل | أكبر دومين (23 جدول)؛ يحتضن أيضًا `AcademyTenant` — أي أن جدول الـ tenant الأساسي للمنصة كلها معرّف داخل دومين "الأكاديمية" التعليمية بدل دومين tenancy/core مستقل |
| `admin` | `router.py` فقط | ❌ ناقص جدًا | لا يوجد models/schemas/service/`__init__.py`؛ متغير الراوتر اسمه `admin_router` وليس `router` كباقي الدومينز، لذلك **غير مستورد إطلاقًا في `main.py`** — الدومين ميت فعليًا |
| `affiliate` | models, repository, router, schemas, service, `__init__.py` | ✅ مكتمل | — |
| `agritech` | نفس البنية الكاملة | ✅ مكتمل | — |
| `ai_agents` | نفس البنية الكاملة | ✅ مكتمل | — |
| `ai_governance` | نفس البنية الكاملة | ✅ مكتمل | — |
| `arbitration_syndicates` | نفس البنية الكاملة | ✅ مكتمل | — |
| `auth` | models(`RefreshToken`), repository, router, schemas, service, `jwt_service.py`, `__init__.py` | ⚠️ يتداخل مع identity | انظر قسم 2 |
| `automation` | نفس البنية الكاملة | ✅ مكتمل | تغطية tenant_id جزئية (انظر قسم 4) |
| `command` | نفس البنية الكاملة | ✅ مكتمل | — |
| `commerce` | نفس البنية الكاملة | ✅ مكتمل | — |
| `communications` | + `tasks.py` | ✅ مكتمل | تغطية tenant_id جزئية (انظر قسم 4) |
| `digital_twin` | نفس البنية الكاملة | ✅ مكتمل | — |
| `employment` | نفس البنية الكاملة | ✅ مكتمل | — |
| `finance` | models(`Wallet`,`Transaction`,`SystemState`,`AuditLog`), ... | ⚠️ خطأ تسمية | الملف اسمه `_init__.py` بدل `__init__.py` (ناقص شرطة سفلية) |
| `health` | نفس البنية الكاملة | ✅ مكتمل | — |
| `identity` | models(`User`), repository, router, `router.py.bak`, schemas, service, `__init__.py`, مجلد `tests/` | ⚠️ يتداخل مع auth + ملف بقايا | انظر قسم 2 و3 |
| `insurance` | نفس البنية الكاملة | ✅ مكتمل | — |
| `invitations` | + `router.py.bak` | ⚠️ ملف بقايا | — |
| `invoicing` | models(`Invoice`), repository, router, schemas, service | ❌ لا يوجد `__init__.py` إطلاقًا | — |
| `iot` | نفس البنية الكاملة | ⚠️ خطأ تسمية + tenant_id | `_init__.py` بدل `__init__.py`؛ **صفر** أعمدة tenant_id في 6 جداول (قسم 4) |
| `logistics` | نفس البنية الكاملة | ✅ مكتمل | — |
| `manufacturing` | نفس البنية الكاملة | ✅ مكتمل | — |
| `privacy` | + `tasks.py` | ⚠️ tenant_id | **صفر** أعمدة tenant_id في 4 جداول (قسم 4) |
| `projects` | نفس البنية الكاملة | ⚠️ خطأ تسمية | `_init__.py` بدل `__init__.py` |
| `realestate` | نفس البنية الكاملة | ⚠️ خطأ تسمية | `_init__.py` بدل `__init__.py` |
| `saas` | نفس البنية الكاملة | ✅ مكتمل | يحتوي `TenantSubscription`, `TenantServiceAccess`, `TenantFeatureFlag` |
| `service_marketplace` | نفس البنية الكاملة | ✅ مكتمل | في main.py مسجّل باسم `/marketplace` |
| `social` | نفس البنية الكاملة | ✅ مكتمل | أكبر ثاني دومين (21 جدول) |
| `sovereign_entities` | نفس البنية الكاملة | ⚠️ tenant_id جزئي | انظر قسم 4 |
| `tenders_auctions` | نفس البنية الكاملة | ✅ مكتمل | — |
| `tourism_sports` | نفس البنية الكاملة | ✅ مكتمل | — |
| `translation` | نفس البنية الكاملة | ✅ مكتمل | — |
| `transport` | نفس البنية الكاملة | ✅ مكتمل | — |
| `zamakana` | نفس البنية الكاملة | ✅ مكتمل | — |

**البنية القياسية لكل دومين سليم**: `models.py`, `repository.py`, `router.py`, `schemas.py`, `service.py`, `__init__.py` (نمط Repository/Service متّسق عبر كل الدومينز تقريبًا — نقطة إيجابية).

### دومينز الفرونت إند (مقارنة أولية — التفاصيل الكاملة في قسم 6)
`eppne-web/components/`: academy, affiliate, agritech, ai-agents, ai-governance,
arbitration-syndicates, auth, automation, **brand-builder**, command, commerce,
communications, digital-twin, employment, **entities**, finance, health, identity,
insurance, invitations, iot, **layout**, logistics, manufacturing, marketplace,
privacy, projects, realestate, saas, **shared**, social, sovereign-entities,
tenders-auctions, tourism-sports, translation, transport, **ui**, **web3**, zamakana.

العناصر بالخط الغامق (brand-builder, entities, layout, shared, ui, web3) لا
تقابل أي دومين باك إند مباشر — بعضها بنية مشتركة مشروعة (layout, shared, ui)
وبعضها تكرار فعلي (entities، انظر قسم 2 و6).

---

## 2. التعارضات والتكرار

### 2.1 `auth` مقابل `identity` (Backend) — التعارض الأهم في المشروع

كلا الدومينين يوفّران **نفس الوظائف بالضبط** بتطبيقين مختلفين تمامًا:

| الوظيفة | `app/domains/auth/router.py` | `app/domains/identity/router.py` |
|---|---|---|
| تسجيل الدخول | `POST /api/auth/login` — عبر `AuthService`، يُرجع التوكنات في جسم JSON | `POST /api/identity/login` — عبر `UserService`، يخزّن التوكنات في **HttpOnly cookies** |
| تجديد التوكن | `POST /api/auth/refresh` (JSON body) | `POST /api/identity/refresh` (يقرأ من الكوكيز) |
| تسجيل الخروج | `POST /api/auth/logout` | `POST /api/identity/logout` |
| إبطال كل الجلسات | `POST /api/auth/revoke-all` | `POST /api/identity/revoke-all` |
| الجلسات النشطة | `GET /api/auth/sessions` | غير موجود |
| التسجيل (Register) | غير موجود في auth | `POST /api/identity/register` |
| تغيير كلمة المرور | غير موجود | `PUT /api/identity/me/password` |

**الفرق الجوهري**: `auth` يستخدم نمط Bearer token (JSON)، بينما `identity`
يستخدم نمط HttpOnly Cookie. هذان نمطان أمنيان مختلفان تمامًا للتعامل مع
نفس الغرض (الجلسة)، مسجَّلان في نفس التطبيق تحت مسارين مختلفين، وكلاهما
يستهدف نفس جدول المستخدمين (`users`) ونفس جدول `auth_refresh_tokens`.

- **الموديل**: `auth/models.py` يعرّف `RefreshToken` فقط (جدول
  `auth_refresh_tokens`). `identity/models.py` يعرّف `User` فقط (جدول
  `users`). الموديلان لا يتكرران على مستوى الجدول، لكن **منطق الأعمال
  (login/logout/refresh/revoke) مكرر بالكامل** بين `auth/service.py`
  و`identity/service.py`.
- **جهة JWT**: هناك 3 تطبيقات مختلفة لإصدار/فك JWT (انظر قسم 5) — واحد منها
  (`auth/jwt_service.py`) غير مستخدم فعليًا في الراوترين أعلاه، وهو كود ميت
  خطر (انظر قسم 5).

**التوصية**: البقاء على `identity` كنقطة الدخول الوحيدة (لأنه الأحدث منطقيًا
ويحتوي على التسجيل/الحساب الكامل)، وحذف/دمج نمط auth الخاص بـ Bearer إن لم
يكن مستخدمًا من عميل فعلي (يُنصح بالتحقق من الفرونت إند أولًا — انظر قسم 6،
الفرونت يستخدم فعليًا كلا الملفين `services/auth.service.ts`
و`services/identity.service.ts`، ما يعني أن كلا المسارين **مُستهلَكان فعليًا
من الفرونت** حاليًا، وهذا تعقيد تشغيلي حقيقي وليس مجرد كود ميت).

### 2.2 `entities` مقابل `sovereign-entities` (Frontend)

`eppne-web/components/entities/` و`eppne-web/components/sovereign-entities/`
كلاهما يغطي نفس المفهوم (الكيانات السيادية) بأسماء ملفات متوازية:

| entities/ (kebab-case) | sovereign-entities/ (PascalCase) |
|---|---|
| `entity-card.tsx` | `EntityCard.tsx` |
| `entity-form.tsx` | `EntityForm.tsx` |
| `entity-documents.tsx` | `KYBDocumentUploader.tsx` |
| `entity-representatives.tsx` | `RepresentativeList.tsx` |
| `entity-brand-settings.tsx` | `BrandEditor.tsx` |
| `entity-basic-info.tsx`, `entity-tabs.tsx` | `EntityTreeView.tsx`, `WalletActions.tsx`, `WalletBalance.tsx` |

كلاهما يقابل دومين الباك إند الواحد `sovereign_entities`. من الواضح أن أحد
المجلدين كُتب في مرحلة زمنية مختلفة عن الآخر بقواعد تسمية مختلفة (kebab-case
vs PascalCase — كل باقي مكونات المشروع تستخدم PascalCase، لذلك `entities/`
هو الشاذ عن النمط العام). **التوصية**: الاحتفاظ بـ `sovereign-entities/`
(متّسق مع تسمية بقية المشروع ويحتوي منطق Wallet/KYB الأكثر اكتمالًا)، ومراجعة
`entities/` لدمج أي حقول غير موجودة ثم حذفه.

### 2.3 علاقة SQLAlchemy مكسورة بين `identity` و`academy`

`identity/models.py` يعرّف:
```python
tenant = relationship("app.domains.academy.models.Tenant", foreign_keys=[tenant_id], lazy="selectin")
```
لكن الكلاس الفعلي في `academy/models.py` اسمه **`AcademyTenant`** وليس
`Tenant` (تم التحقق: لا يوجد أي `class Tenant(Base)` في كامل الباك إند —
فقط `AcademyTenant`). هذا مرجع مكسور سيفشل عند تهيئة SQLAlchemy mapper بمجرد
محاولة استخدام `User.tenant` (خطأ `InvalidRequestError: expression ... failed
to locate a name`). هذه ليست "تسمية سيئة" فقط، بل **خطأ فعلي يمنع تشغيل هذا
المسار من الكود** إن استُدعي.

### 2.4 دومينات أخرى بأسماء متشابهة (تم فحصها ولا يوجد تعارض فعلي)
- `finance` مقابل `invoicing`: لا تكرار — `finance` يغطي المحفظة والمعاملات
  (`Wallet`, `Transaction`, `SystemState`, `AuditLog`)، و`invoicing` يغطي
  الفواتير فقط (`Invoice`). علاقة تكامل طبيعية وليست تكرارًا.
- `service_marketplace` (باك إند) مقابل `marketplace` (فرونت، مسار `/marketplace`
  في main.py): نفس الدومين بتسمية مختصرة على الفرونت — ليس تكرارًا، لكنه
  عدم اتساق تسموي بسيط.
- `sovereign_entities` (باك إند، underscore) مقابل `sovereign-entities`
  (فرونت، kebab) — تسمية فقط، ليس تكرارًا.

---

## 3. أخطاء بنيوية فعلية

1. **`__init__.py` بتسمية خاطئة** (الشرطة السفلية الأولى ناقصة، فتصبح
   `_init__.py` بدل `__init__.py`) في 4 دومينز:
   `finance`, `iot`, `projects`, `realestate`.
   ملف بهذا الاسم **لا يُعامَل كـ package marker** من Python بنفس طريقة
   `__init__.py` القياسي؛ الاستيراد قد ينجح فقط بالاعتماد على namespace
   packages الضمنية (PEP 420)، وهو سلوك هش يعتمد على إصدار Python وطريقة
   التشغيل، وغير متّسق مع بقية الدومينز.

2. **`invoicing` بلا `__init__.py` إطلاقًا** — لا يوجد حتى النسخة الخاطئة.

3. **`admin` دومين شبه فارغ وغير موصول**:
   - يحتوي فقط على `router.py` (لا `models.py`, `schemas.py`, `service.py`,
     `__init__.py`).
   - متغير الراوتر داخل الملف اسمه `admin_router = APIRouter(...)` بينما كل
     الدومينز الأخرى تصدّر متغيرًا اسمه `router` (هذا هو الاسم الذي
     `main.py` يستورده: `from app.domains.X.router import router as
     X_router`). بسبب هذا الاختلاف، **`admin` غير مستورد وغير مسجَّل في
     `main.py` إطلاقًا** — أي أن كل مسارات `/api/admin/system/*` (بما فيها
     التحقق من `get_current_superuser`) غير موجودة فعليًا في التطبيق قيد
     التشغيل. هذا دومين ميت بالكامل، ليس مجرد ناقص.

4. **ملفات بقايا (`.bak`) داخل شجرة الكود الحيّة**:
   - `app/domains/identity/router.py.bak`
   - `app/domains/invitations/router.py.bak`
   هذه ليست مشكلة استيراد (لاحقة `.py.bak` لا يستوردها Python)، لكنها بقايا
   تعديل يدوي/AI لم تُنظَّف، وتخاطر بالالتباس مع النسخة الحيّة عند القراءة
   اليدوية للكود لاحقًا.

5. **علاقة SQLAlchemy مكسورة** `identity.User.tenant` → `academy.models.Tenant`
   (التفصيل في القسم 2.3) — خطأ استيراد/تشغيل فعلي وليس مجرد تسمية.

6. **نموذج مكرر لنفس الجدول**: لم يُعثر على موديلين مختلفين يشيران لنفس
   `__tablename__` عبر الدومينز التي تم فحصها. **لا يوجد** تكرار جداول على
   مستوى `models.py`، والتكرار الحقيقي في هذا المشروع هو على مستوى **منطق
   الأعمال والـ endpoints** (auth/identity)، وليس على مستوى تعريف الجداول.

---

## 4. قاعدة البيانات والـ migrations

### 4.1 مجلدان منفصلان لـ Alembic — أحدهما ميت

- `eppne-backend/alembic/` يحتوي `env.py`, `script.py.mako`, `versions/`
  لكن **`versions/` فارغ تمامًا (0 ملفات)**.
- `eppne-backend/migrations/` يحتوي نفس البنية لكن مع **18 ملف migration
  فعلي**.
- `eppne-backend/alembic.ini` يحدد صراحة: `script_location = migrations`.

⇒ `alembic/` مجلد أشباح متروك من مرحلة إعداد أولى، لا يُستخدم فعليًا، لكنه
خطر مستقبلي: أي مطوّر يشغّل `alembic revision` بدون التحقق من `alembic.ini`
قد يفترض أن `alembic/` هو المكان الصحيح. **يُنصح بحذفه** لتفادي اللبس (فقط
بعد تأكيد عدم وجود أي سكربت CI/CD يشير إليه).

### 4.2 سلسلة الهجرات (migrations/versions) — بها بقايا placeholder لم تُستبدل

ترتيب السلسلة الفعلي بعد تتبع `revision`/`down_revision`:

```
71820e4fe1f3_initial_migration_all_34_sectors_final.py   (root, down_revision=None)
  → 71820e4fe1f3_add_tenant_id_to_auth_refresh_tokens.py.py
  → 003_add_tenant_id_to_users.py
  → 001_add_tenant_id_to_wallets.py
  → 002_add_tenant_id_to_audit_logs.py
  → 004 → 005 → 006 → 007 → 008 → 009 → 010
  → 011_drop_saas_plans_and_subscriptions.py
  → 012 → 013 → 014_add_tenant_id_to_payment_installments.py
  → 016_create_invoices_table.py   (head)
```

مشاكل محددة:
- ملف `71820e4fe1f3_add_tenant_id_to_auth_refresh_tokens.py.py` **لاحقته
  مكرّرة فعليًا `.py.py`** (خطأ كتابة اسم ملف).
- نفس الملف لديه `revision = 'xxxx_add_tenant_id_to_auth_refresh_tokens'` —
  القيمة الحرفية `xxxx_...` هي placeholder لم يُستبدل بمعرّف حقيقي؛ السلسلة
  "تعمل" فقط لأن `003_add_tenant_id_to_users.py` يشير بالصدفة لنفس النص
  الحرفي في `down_revision`. هذا يعمل تقنيًا (Alembic لا يفرض أن تكون
  المعرّفات hashes)، لكنه دليل واضح على أن تصحيح سلسلة الهجرات تم يدويًا/بأداة
  آلية ولم يُكمَل بشكل نظيف — التعليقات المتروكة داخل نفس الملفات (`# ⚠️
  استبدل بالرقم الصحيح`, `# ← استبدل بالقيمة الصحيحة`) تؤكد ذلك.
- **الترقيم يقفز من `014` إلى `016` — لا يوجد ملف `015` إطلاقًا.** إما ملف
  محذوف/مفقود، أو ترقيم غير متسلسل عن قصد؛ في كلتا الحالتين يستحق التحقق
  اليدوي قبل أي migration جديدة.
- لا يوجد أكثر من head واحد (لا تفرّع فعلي) — إيجابية: السلسلة خطية رغم
  المشاكل أعلاه.

### 4.3 تغطية `tenant_id` — الجداول الناقصة بالاسم

**دومينز بدون أي عمود `tenant_id` في أي جدول (الأخطر):**

| الدومين | الجداول المتأثرة (كلها بلا tenant_id) |
|---|---|
| `iot` | `smart_assets`, `utility_grids`, `utility_readings`, `maintenance_logs`, `idempotency_records`, `iot_request_logs` |
| `privacy` | `privacy_settings`, `data_consent_logs`, `data_erasure_requests`, `tombstone_records` |

هذان الدومينان بالكامل بلا عزل بين المستأجرين (tenants) على مستوى قاعدة
البيانات — أي مستخدم من أي tenant يمكنه نظريًا الوصول لبيانات IoT أو
الخصوصية الخاصة بـ tenant آخر إن لم يُطبَّق الفلترة يدويًا وبشكل صارم في
طبقة service/repository (وهو أمر لم يُتحقق منه في هذا التدقيق البنيوي لأنه
يتطلب قراءة كل استعلام SQL — يُنصح بمراجعة `iot/repository.py` و
`privacy/repository.py` تحديدًا في تدقيق أمني لاحق).

**دومينز بها جداول فرعية (child tables) بلا `tenant_id` رغم أن الجدول
الأب في نفس الدومين يملكه** (نمط شائع لجداول مرتبطة بـ FK لجدول أب مُعزول
بالفعل — أقل خطورة لكنه غير متسق):

| الدومين | جدول أب (له tenant_id) | جداول فرعية بلا tenant_id |
|---|---|---|
| `communications` | `notifications`, `mail_threads`, `communication_templates` | `notification_devices`, `mail_messages`, `mailbox_items`, `mail_attachments` |
| `automation` | `automation_workflows`, `automation_secrets` | `automation_executions`, `automation_node_logs` |
| `sovereign_entities` | `sovereign_entities_v2`, `entity_page_templates`, `entity_pages`, `page_components` | `entity_representatives`, `entity_documents` |

ملاحظة نطاق: تم أخذ عينة من ~7 دومينز بعمق لهذا القسم؛ باقي الـ 27 دومين تم
فحصها فقط بعدّ إجمالي (عدد الجداول مقابل عدد ذكر `tenant_id`) دون تحديد
الجدول الناقص بالاسم — الأرقام الكاملة موجودة في قسم 1 لكل دومين، ومعظمها
يُظهر عدد ذكر `tenant_id` ≥ عدد الجداول (مؤشر تغطية جيدة على الأرجح)، باستثناء
`iot` و`privacy` أعلاه واللذين هما تأكيد كامل 100%.

---

## 5. الأمان الأساسي (core/)

### 5.1 لا يوجد آلية auth موحّدة واحدة — بل 3 تطبيقات مختلفة

| الملف | آلية الحصول على المستخدم | يتحقق من `session_version`؟ | مصدر التوكن |
|---|---|---|---|
| `app/core/security.py::get_current_user` | Bearer header فقط | ✅ نعم (يرفض الجلسات المُبطَلة) | Header فقط |
| `app/api/deps.py::get_current_user` | Bearer **أو** Cookie | ❌ لا | Header أو Cookie |
| `app/domains/auth/jwt_service.py::JWTService` | كلاس منفصل تمامًا بمفتاحه ومنطقه الخاص | له `verify_token` منفصل، لكن دوال الإبطال (`revoke_refresh_token`, `revoke_all_user_tokens`) هي **stubs لا تفعل شيئًا فعليًا** (تسجّل تحذيرًا وتُرجع `True`/`0` فقط) | — |

**النتيجة العملية**: 35 من 36 ملف router يستوردون `get_current_user` من
`app.api.deps` (النسخة **الأضعف**، بلا فحص `session_version`)، بينما 4 ملفات
فقط (`communications`, `privacy` router/service، و`identity/service.py`)
تستخدم أيضًا `app.core.security`.

**الفجوة الأمنية الفعلية**: كل الراوترز الـ32 المسجَّلة في `main.py` عبر
`routers_config` تُحمى على مستوى الراوتر بـ
`dependencies=[Depends(require_sector(sector))]`، و`require_sector` من
`core/security.py` يعتمد داخليًا على `get_current_user` **القوي** (مع فحص
session_version) — لذلك هذه الراوترات محمية فعليًا حتى لو استخدمت داخليًا
نسخة `api/deps` الأضعف (لأن بوابة الراوتر تُرفض الطلب أولًا).

**لكن `auth_router` استثناء**: هو الوحيد المسجَّل بدون أي
`dependencies=[Depends(require_sector(...))]` على مستوى الراوتر
(`fastapi_app.include_router(auth_router, prefix="/api",
tags=["Authentication"])` — بدون `dependencies`). هذا منطقي جزئيًا (لازم
الوصول لـ `/auth/login` قبل تسجيل الدخول)، لكنه يعني أن endpoints المحمية
داخل نفس الراوتر (`/auth/logout`, `/auth/revoke-all`, `/auth/sessions`)
تعتمد **فقط** على `api.deps.get_current_active_user` الأضعف — أي أن توكن
تم إبطاله عبر "تسجيل خروج من كل الأجهزة" (session_version bump) **قد يظل
صالحًا لاستدعاء `/api/auth/logout` أو `/api/auth/sessions`** حتى ينتهي
عمر التوكن الطبيعي (15 دقيقة افتراضيًا حسب `ACCESS_TOKEN_EXPIRE_MINUTES`).
هذه فجوة محددة وقابلة للإصلاح بسطر واحد (استبدال الاستيراد بنسخة core.security
أو إضافة dependency على مستوى راوتر auth).

### 5.2 كود ميت خطير: `auth/jwt_service.py`

دوال `create_access_token`/`create_refresh_token` "التوافقية" (Adapter
Functions) في هذا الملف تُنشئ توكنات بـ **`tenant_id=1` و`session_version=1`
مُثبَّتين (hardcoded)** بغضّ النظر عن المستخدم الفعلي. لم يظهر أي استدعاء
فعلي لهذه الدوال من الراوترات المفحوصة (auth/identity يستخدمان
`AuthService`/`UserService` مباشرة، ليس `jwt_service`)، لكن وجود ملف بهذا
الخطورة (توكنات بـ tenant ثابت) في شجرة الكود الحيّة، قابل للاستيراد من أي
مكان مستقبلًا، يستحق إما حذفه أو تحويله لملف اختبار معزول بوضوح.

### 5.3 Endpoints بلا حماية واضحة (بالتصميم، ومقصودة على الأرجح)

- `GET /health`, `GET /ready`, `GET /metrics` — بلا Depends، متوقع لنقاط
  health check، لكن `/metrics` (يكشف مقاييس Prometheus تفصيلية) و`/ready`
  (يكشف حالة اتصال قاعدة البيانات/Redis) **مفتوحان بالكامل بدون أي مصادقة أو
  IP allowlist** — يُنصح بحمايتهما على مستوى الشبكة (Ingress/K8s NetworkPolicy)
  إن لم تكن محمية هناك بالفعل.
- `POST /api/ai/chat`, `GET /api/ai/cost` — يستخدمان
  `get_current_user_optional` (يسمح بمستخدم `None`) — أي أن أي زائر غير
  مسجَّل دخول يمكنه استدعاء الـ AI chat واستهلاك تكلفة نموذج LLM حقيقية دون
  حساب. هذا قد يكون قرارًا منتجيًا مقصودًا (ميزة تجريبية للزوار)، لكنه يستحق
  تأكيدًا صريحًا لأنه بوابة استهلاك تكلفة مالية مفتوحة.
- `PUT /api/ai/routing` — محمي بـ `get_current_user` (إجباري) لكن **بلا أي
  فحص صلاحية دور (role/superuser)** — أي مستخدم مسجَّل دخول عاديًا (ليس بالضرورة
  admin) يستطيع تغيير نسب توجيه نماذج الـ AI على مستوى النظام بالكامل. هذا
  endpoint إداري حساس بمستوى حماية مستخدم عادي فقط — يستحق `get_current_superuser`
  بدل `get_current_user`.

### 5.4 نقطة إيجابية
`core/security.py::get_current_user` مُصمَّم جيدًا: يتحقق من نوع التوكن
(`typ == "access"`)، تطابق `tenant_id`، تطابق `session_version` (لإبطال
الجلسات فعليًا)، وحالة `is_active` — وهو الأساس الصحيح الذي يجب أن يكون
المصدر الوحيد المستخدم في كل مكان بدل تفرّعه إلى `api/deps.py`.

---

## 6. حالة الفرونت إند مقابل الباك إند

### 6.1 جدول تطابق الدومينز (مختصر — الفروقات فقط)

| الدومين | Backend | Frontend components | ملاحظة |
|---|---|---|---|
| `admin` | ✅ (لكن ميت، قسم 3) | ❌ لا يوجد | متسق مع كون الدومين غير مفعّل خلفيًا |
| `invoicing` | ✅ | ❌ لا يوجد مجلد مخصص | لا واجهة مستخدم للفوترة رغم وجود API كامل |
| `entities` | — (لا يقابله دومين مباشر) | ✅ (مكرر مع sovereign-entities) | انظر قسم 2.2 |
| `brand-builder` | — | ✅ | لا يقابله دومين باك إند مخصص (قد يكون جزءًا من `sovereign_entities` أو `academy` — لم يُؤكَّد الربط) |
| `web3` | — | ✅ | لا يوجد دومين `web3` في الباك إند إطلاقًا — واجهة أمامية بلا API مقابل، أو تعتمد على خدمة خارجية لم تُفحص |
| `commerce` (dashboard route) | ✅ `commerce` | مكوّن موجود (`components/commerce`) لكن **صفحة dashboard تستخدم اسم `store`** | تعارض تسموي بين طبقة components وطبقة routes داخل نفس الفرونت |
| باقي الـ ~27 دومين | ✅ | ✅ (مطابقة اسمية مباشرة أو بفرق kebab/underscore فقط) | تطابق سليم |

### 6.2 `auth` مقابل `identity` على الفرونت — نفس التعارض الخلفي منعكس تمامًا

- `components/auth/`: `LoginForm.tsx`, `RegisterForm.tsx`, `SessionCard.tsx`,
  `SessionsList.tsx`
- `components/identity/`: `LoginForm.tsx`, `RegisterForm.tsx`,
  `SessionCard.tsx`, `SessionsList.tsx` (**نفس الأسماء حرفيًا**) + `AuthProvider.tsx`,
  `ProfileForm.tsx`, `WalletCard.tsx`

أربعة مكونات بنفس الاسم بالضبط موجودة في مجلدين مختلفين. هذا يعني أن أحدهما
على الأقل غير مستخدم فعليًا في أي صفحة (كود ميت)، أو أن صفحات مختلفة تستورد
نسخًا مختلفة من "نفس" الفورم بسلوك مختلف (يستهلك `/api/auth/*` أو
`/api/identity/*` حسب أي نسخة استُوردت) — وهو خطر تشغيلي حقيقي (سلوك تسجيل
دخول غير متسق حسب الصفحة). كذلك على مستوى الـ services:
`services/auth.service.ts` و`services/identity.service.ts` موجودان معًا،
وعلى مستوى الـ hooks: `hooks/auth/useAuth.ts` موجود، بلا `hooks/identity/`
مقابل — ما يرجّح أن `identity` هو الأحدث/الأشمل و`auth` بقايا من مرحلة سابقة
لم تُزَل، لكن هذا يحتاج تأكيدًا بفحص أي الصفحات الفعلية (`app/(auth)/login`,
`app/(auth)/register`) تستورد أيهما (لم يُقرأ محتوى هذين الملفين في هذا
التدقيق البنيوي).

### 6.3 عميل API — نقطة إيجابية
يوجد عميل مركزي واحد: `eppne-web/lib/api-client.ts` (بالإضافة إلى
`error-handler.ts`, `utils.ts`, و`src/lib/api-types.ts`). هذا نمط سليم
ومتّسق — لا يوجد دليل على تعدد أنماط استدعاء API متضاربة على مستوى البنية
التحتية (كل ملفات `services/*.ts` الـ 32 من المفترض أنها تستخدم نفس العميل،
لم تُفحص كل الاستدعاءات الفردية بعمق).

### 6.4 صفحات `app/(dashboard)` بلا مقابل دومين واضح
`payroll`, `store`, `wallet`, `settings`, `profile`, `dashboard` — صفحات
منطقية (وظيفتها تتقاطع مع `employment`/`finance`/`commerce`) وليست بالضرورة
مشكلة، لكنها تستحق توثيقًا صريحًا لأي مطوّر جديد لمعرفة أي API خلفي تستهلكه
كل صفحة، لأن الاسم وحده لا يكشف الربط.

---

## 7. تقييم عام لكل دومين

| الدومين | التقييم | السبب الرئيسي |
|---|---|---|
| `auth` | ❌ مشاكل جذرية | تكرار كامل مع identity بنمطين أمنيين مختلفين (قسم 2.1، 5.1) |
| `identity` | ⚠️ يحتاج إصلاح | نفس تكرار auth + علاقة SQLAlchemy مكسورة (قسم 2.3) + ملف `.bak` |
| `admin` | ❌ مشاكل جذرية | دومين شبه فارغ وغير موصول بالتطبيق إطلاقًا (قسم 3) |
| `iot` | ❌ مشاكل جذرية | صفر عزل tenant على 6 جداول (قسم 4.3) + خطأ تسمية init |
| `privacy` | ❌ مشاكل جذرية | صفر عزل tenant على 4 جداول لدومين حسّاس بطبيعته (بيانات الخصوصية!) |
| `invoicing` | ⚠️ يحتاج إصلاح | لا `__init__.py`، لا واجهة أمامية مقابلة |
| `finance`, `projects`, `realestate` | ⚠️ يحتاج إصلاح | خطأ تسمية `_init__.py` (سهل الإصلاح لكنه يجب إصلاحه) |
| `communications`, `automation`, `sovereign_entities` | ⚠️ يحتاج إصلاح | جداول فرعية بلا tenant_id (قسم 4.3) |
| `invitations` | ⚠️ يحتاج إصلاح | ملف `.bak` متروك في الشجرة الحيّة |
| `academy` | ⚠️ يحتاج إصلاح | يحتضن جدول tenancy الأساسي للمنصة كلها (`AcademyTenant`) رغم كونه دومين تعليمي — قرار معماري مربك يستحق مراجعة (نقل tenancy لدومين core مستقل) |
| باقي الدومينز (~24 دومين: affiliate, agritech, ai_agents, ai_governance, arbitration_syndicates, command, commerce, digital_twin, employment, health, insurance, logistics, manufacturing, saas, service_marketplace, social, tenders_auctions, tourism_sports, translation, transport, zamakana) | ✅ سليم بنيويًا | بنية ملفات كاملة ومتسقة، تغطية tenant_id تبدو جيدة من عدّ المذكورات؛ **لم تُفحص منطقيًا بعمق** (لا فحص أعمال/أمان تفصيلي لكل واحد) |

---

## الخلاصة

المشروع **ليس قريبًا من الاكتمال بالمعنى الإنتاجي**، رغم أن الهيكل العام
(34 دومين بنمط Repository/Service متّسق، عميل API مركزي في الفرونت، طبقة
middleware جيدة في main.py) يدل على تخطيط معماري جدّي وليس فوضى عشوائية.
المشكلة الأعمق ليست "نقص ميزات" بل **ازدواجية قرار غير محسومة**: نظاما
مصادقة كاملان (auth وidentity) يعملان بالتوازي في الباك والفرونت معًا، وهذا
النوع من التعارض لا يُصلَح بترقيع بل يتطلب قرار حاسم بدمج/إلغاء أحدهما قبل
أي عمل آخر، لأن كل ميزة جديدة تُبنى فوق هذا الأساس المزدوج تُضاعف كلفة
الإصلاح لاحقًا. إلى جانب ذلك توجد ثغرات عزل بيانات (`iot`, `privacy` بلا
`tenant_id` إطلاقًا) يجب سدّها قبل أي إطلاق متعدد المستأجرين، وسلسلة
migrations تحمل آثار تصحيح يدوي غير مكتمل. التوصية: **تجميد إضافة دومينز
جديدة مؤقتًا**، وتخصيص جولة إصلاح مركّزة على قسمي 2 و5 (حسم auth/identity
وتوحيد آلية المصادقة) و4.3 (سد ثغرات tenant_id)، ثم استئناف التوسع — إعادة
تفكير معماري كامل غير مطلوبة، لكن "إكمال" المشروع بحالته الحالية دون هذه
الجولة سيُثبّت التعارضات بدل حلّها.
