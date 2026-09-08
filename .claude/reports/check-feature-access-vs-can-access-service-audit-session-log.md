# check_feature_access مقابل can_access_service — سجل جلسة الفحص

**بدأت:** 2026-09-07
**النوع:** فحص read-only بحت — صفر تعديل على أي ملف.
**الهدف:** تحديد أي الدومينات (من ضمن الدومينات المحمية بـ`_check_saas_limits`)
بتستخدم `check_feature_access` (الدالة اللي وثّقها [[saas-feature-flags-drift-session-log]]
كمعرَّضة لعيب تصميم أمني كامن، §6 من هذا التقرير) مقابل `can_access_service`
(الدالة الآمنة، بتفحص `saas_tenant_service_access` + اشتراك فعّال مربوط
بـ`service_id` تحديدًا).

**الحالة:** ✅ الفحص اكتمل، النتائج موثّقة تحت. بانتظار رد المستخدم.

---

## طريقة الفحص

```
grep -rn "check_feature_access" app/domains/ --include="*.py"
grep -rn "can_access_service" app/domains/ --include="*.py"
```

لكل نتيجة اتحدد: اسم الدومين، اسم الملف، وهل الاستدعاء فعلي (جوه دالة
service حقيقية بتُستدعى من endpoints) ولا مجرد تعريف الدالة نفسها. اتأكدت
من "فعلي" عن طريق عدّ مرات ظهور `_check_saas_limits(` في كل ملف (أكتر من
مرة واحدة = فيه تعريف + استدعاء حقيقي واحد على الأقل من داخل نفس السيرفس).

---

## الجدول النهائي

| الدومين | الدالة المستخدمة | الملف |
|---|---|---|
| employment | check_feature_access (المعرَّضة) | `app/domains/employment/service.py:72` |
| digital_twin | check_feature_access (المعرَّضة) | `app/domains/digital_twin/service.py:39` |
| arbitration_syndicates | check_feature_access (المعرَّضة) | `app/domains/arbitration_syndicates/service.py:40` |
| realestate | check_feature_access (المعرَّضة) | `app/domains/realestate/service.py:62` |
| manufacturing | check_feature_access (المعرَّضة) | `app/domains/manufacturing/service.py:44` |
| logistics | check_feature_access (المعرَّضة) | `app/domains/logistics/service.py:49` |
| insurance | check_feature_access (المعرَّضة) | `app/domains/insurance/service.py:49` |
| invitations | check_feature_access (المعرَّضة) | `app/domains/invitations/service.py:43` |
| zamakana | can_access_service (الآمنة) | `app/domains/zamakana/service.py:64` |
| transport | can_access_service (الآمنة) | `app/domains/transport/service.py:67` |
| tourism_sports | can_access_service (الآمنة) | `app/domains/tourism_sports/service.py:61` |
| tenders_auctions | can_access_service (الآمنة) | `app/domains/tenders_auctions/service.py:59` |
| social | can_access_service (الآمنة) | `app/domains/social/service.py:64` |
| service_marketplace | can_access_service (الآمنة) | `app/domains/service_marketplace/service.py:70` |
| saas (مصدر التعريف) | يعرّف الدالتين، ويستخدم can_access_service داخليًا فقط | `app/domains/saas/service.py:126, 328, 353, 362` |

**الخلاصة الرقمية:** 8 دومينات على `check_feature_access` المعرَّضة، 6
دومينات على `can_access_service` الآمنة. كل النتائج المذكورة استدعاءات
فعلية داخل `_check_saas_limits` بكل ملف (تعدد نقاط الاستدعاء لكل دالة
مؤكَّد بالعدّ)، مش مجرد تعريفات ميتة — ما عدا الحالات المُعلَّمة صراحة كـ
"تعريف الدالة" في `saas/service.py`.

**هذه النتيجة مطابقة تمامًا لما وثّقه [[saas-feature-flags-drift-session-log]]
في §9.2** (فحص مستقل، جلسة مختلفة، نفس الـ8/6 بالضبط) — يعمل كتأكيد ثانٍ
مستقل لنفس التصنيف، صفر تناقض.

---

## ملاحظة نطاق — لم يُلمس في هذه الجلسة

بناءً على تعليمات المستخدم الصريحة: لم يتم تعديل أي كود، ولم يُقترح أي
إصلاح لـ`get_plan_by_id` أو أي نقطة تانية. هذا الملف توثيق فحص فقط.

---

## بانتظار رد المستخدم
