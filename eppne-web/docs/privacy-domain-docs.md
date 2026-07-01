# توثيق قطاع الخصوصية (Privacy Domain) - EPPNE.COM

**الإصدار:** 1.0.0  
**تاريخ الإصدار:** 27 يونيو 2026  
**الحالة:** معتمد للإنتاج (Production-Ready)

---

## 1. نظرة عامة

قطاع الخصوصية هو المسؤول عن إدارة إعدادات الخصوصية للمستخدمين، وتسجيل موافقاتهم على معالجة البيانات، ومعالجة طلبات محو البيانات (Data Erasure). تم تصميم هذا القطاع وفقاً لأعلى معايير الأمان والأداء لدعم أكثر من 10 ملايين مستخدم.

### 1.1 الأهداف الرئيسية
- تمكين المستخدمين من التحكم الكامل في بياناتهم الشخصية.
- ضمان الامتثال لقوانين حماية البيانات (GDPR, CCPA, PDPL).
- توفير سجل تدقيق كامل (Audit Trail) لجميع عمليات البيانات الحساسة.
- أداء فائق تحت الحمل الأقصى باستخدام طوابير المهام والفهارس المحسّنة.

---

## 2. المكونات الرئيسية

### 2.1 الباك إند (Backend)

| المكون | المسار | الوظيفة |
| :--- | :--- | :--- |
| **Models** | `app/domains/privacy/models.py` | تعريف جداول قاعدة البيانات (PrivacySettings, DataConsentLog, DataErasureRequest, TombstoneRecord). |
| **Repository** | `app/domains/privacy/repository.py` | طبقة الوصول إلى البيانات (CRUD، Pagination، Row Estimation). |
| **Service** | `app/domains/privacy/service.py` | منطق الأعمال (تحديث الإعدادات، تسجيل الموافقات، معالجة طلبات المحو). |
| **Router** | `app/domains/privacy/router.py` | واجهة API (نقاط النهاية مع Rate Limiting و RBAC). |
| **Schemas** | `app/domains/privacy/schemas.py` | تعريفات Pydantic للطلبات والاستجابات. |

### 2.2 الفرونت إند (Frontend)

| الصفحة | المسار | الوظيفة |
| :--- | :--- | :--- |
| إعدادات الخصوصية | `/privacy/settings` | عرض وتحديث إعدادات الخصوصية للمستخدم. |
| طلبات المحو | `/privacy/erasure` | عرض طلبات المحو وإنشاء طلب جديد. |
| لوحة المشرفين | `/privacy/admin/erasure` | إدارة الطلبات المعلقة (قبول/رفض) مع صلاحيات RBAC. |

### 2.3 البنية التحتية (Infrastructure)

| المكون | التكنولوجيا | الوظيفة |
| :--- | :--- | :--- |
| **قاعدة البيانات** | PostgreSQL 16 | تخزين البيانات الأساسية مع دعم المعاملات الذرية. |
| **طابور المهام** | Redis 7 + Celery | معالجة المهام غير المتزامنة (IPFS Unpin، حرق التوكنات). |
| **المراقبة** | Flower + Grafana | مراقبة أداء المهام وحالة النظام. |

---

## 3. تدفق البيانات (Data Flow)

### 3.1 طلب محو البيانات

### 3.2 معالجة طلب المحو

---

## 4. معايير الأمن والأداء

### 4.1 الأمان
- **تشفير IP:** يتم تشفير عناوين IP باستخدام SHA-256 قبل التخزين.
- **RBAC:** صلاحية `Privacy Officer` مطلوبة لمعالجة الطلبات.
- **Rate Limiting:** جميع نقاط النهاية محمية بـ `@rate_limit` لمنع هجمات DoS.
- **SQL Injection:** استخدام Parameterized Queries مع `text()`.
- **Row-Level Security (RLS):** موصى به على مستوى قاعدة البيانات.

### 4.2 الأداء
- **Pagination إلزامي:** جميع نقاط النهاية التي تعيد قوائم تدعم `skip` و `limit`.
- **فهارس جزئية (Partial Indexes):** `ix_erasure_pending` لتسريع استعلامات الطلبات المعلقة.
- **تقدير عدد الصفوف:** استخدام `pg_class` لتجنب استعلامات `COUNT(*)` البطيئة.
- **Task Queue:** معالجة المهام الثقيلة (IPFS, Blockchain) بشكل غير متزامن.
- **Polling:** في الفرونت إند، يتم تحديث حالة الطلبات المعلقة تلقائياً كل 5 ثوانٍ.

---

## 5. إعدادات الإنتاج (Production Setup)

### 5.1 متغيرات البيئة (.env)

```env
# قاعدة البيانات
DATABASE_URL=postgresql://user:pass@localhost:5432/eppne

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# الأمان
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# IPFS
IPFS_GATEWAY_URL=https://ipfs.io/ipfs/
IPFS_PIN_URL=https://pinata.cloud/

# Blockchain
BLOCKCHAIN_RPC_URL=https://mainnet.infura.io/v3/your-project-id