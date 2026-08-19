# app/api/deps.py
"""
Shim مؤقت لإعادة تصدير كل dependencies المصادقة/الصلاحيات من
app.core.security — المصدر الموحَّد الوحيد لهذا المنطق بعد جلسة توحيد
core/security.py + api/deps.py (راجع
.claude/reports/security-deps-unification-session-log.md للتفاصيل
الكاملة و.claude/plans/security-deps-unification-session-instructions.md
للقرار المعتمَد).

لا تُضف أي منطق جديد هنا — أي دالة/تعديل جديد يذهب مباشرة إلى
app/core/security.py. هذا الملف يبقى مؤقتًا عمدًا (re-export shim فقط)
لتفادي تعديل الـ40 ملفًا المستوردة منه دفعة واحدة؛ حذفه النهائي وتحديث
كل المستوردين لاستيراد core.security مباشرة = جلسة تنظيف منفصلة لاحقة
(خارج نطاق هذه الجلسة صراحة).
"""
from app.core.security import (
    security,
    decode_token,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    is_admin_or_above,
    require_admin_or_above,
    is_privacy_officer,
    get_privacy_officer,
    require_sector,
    require_roles,
    get_current_user_optional,
    SimpleTenant,
    get_current_tenant,
    require_tenant_access,
    get_current_instructor_or_admin,
    require_subscription,
)

# اسم قديم (من نسخة deps.py الأصلية) لنفس get_privacy_officer — تأكيد
# grep شامل: لا أحد يستورده فعليًا في أي راوتر اليوم. يبقى كـalias هنا
# فقط (وليس في core/security.py) لتوافق أي استيراد مستقبلي بهذا الاسم
# القديم تحديدًا، بلا تلويث الواجهة العامة الكنسية للملف الموحَّد.
get_current_privacy_officer = get_privacy_officer
