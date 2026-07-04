# app/core/errors.py
from typing import Optional, Any

class BaseAppError(Exception):
    """الفئة الأساسية لجميع أخطاء النظام"""
    def __init__(self, message: str = "حدث خطأ في النظام"):
        self.message = message
        super().__init__(self.message)

class BusinessError(Exception):
    """خطأ عام في منطق العمل (Business Logic)"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

# ==========================================
# 1. الأخطاء الأساسية (Sovereign)
# ==========================================
class SovereignError(BaseAppError):
    """الخطأ العام لمنصة EPPNE Sovereign"""
    def __init__(
        self,
        message: str = "خطأ في المنصة السيادية",
        status_code: int = 400,
        code: Optional[str] = None
    ):
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        super().__init__(message)

# ==========================================
# 2. أخطاء المصادقة والصلاحيات
# ==========================================
class AuthenticationError(SovereignError):
    def __init__(self, message: str = "غير مصرح بالدخول (فشل المصادقة)"):
        super().__init__(message, status_code=401)

class PermissionDeniedError(SovereignError):
    def __init__(self, message: str = "صلاحية غير كافية"):
        super().__init__(message, status_code=403)

# ==========================================
# 3. أخطاء الموارد
# ==========================================
class NotFoundError(SovereignError):
    def __init__(self, message: str = "المورد غير موجود"):
        super().__init__(message, status_code=404)

class AlreadyExistsError(SovereignError):
    def __init__(self, message: str = "المورد موجود بالفعل"):
        super().__init__(message, status_code=409)

class ValidationError(SovereignError):
    def __init__(self, message: str = "بيانات غير صالحة"):
        super().__init__(message, status_code=422)

# ==========================================
# 4. أخطاء مالية
# ==========================================
class InsufficientBalanceError(SovereignError):
    def __init__(self, message: str = "الرصيد غير كافٍ"):
        super().__init__(message, status_code=402)

class TransactionError(SovereignError):
    def __init__(self, message: str = "فشل تنفيذ المعاملة المالية"):
        super().__init__(message, status_code=400)

# ==========================================
# 5. أخطاء الأمان والتكرار والحصص
# ==========================================
class IdempotencyError(SovereignError):
    def __init__(self, message: str = "مفتاح Idempotency مكرر أو منتهي الصلاحية"):
        super().__init__(message, status_code=409, code="IDEMPOTENCY_CONFLICT")

class RateLimitError(SovereignError):
    def __init__(self, message: str = "تجاوزت الحد المسموح به من الطلبات، حاول لاحقاً"):
        super().__init__(message, status_code=429, code="RATE_LIMIT_EXCEEDED")

class QuotaExceededError(SovereignError):
    """خطأ عند تجاوز الحصة أو الحد المسموح به (مثلاً استهلاك الذكاء الاصطناعي)"""
    def __init__(self, message: str = "تجاوزت الحصة المسموح بها"):
        super().__init__(message, status_code=403, code="QUOTA_EXCEEDED")

# ==========================================
# 6. أخطاء القطاعات (مخصصة)
# ==========================================
class TranslationError(SovereignError):
    def __init__(self, message: str = "فشل في عملية الترجمة"):
        super().__init__(message, status_code=500)

class CarbonSettlementError(SovereignError):
    def __init__(self, message: str = "فشل في تسييل أرصدة الكربون"):
        super().__init__(message, status_code=500)

class VoiceAssistantError(SovereignError):
    def __init__(self, message: str = "فشل في معالجة الأمر الصوتي"):
        super().__init__(message, status_code=500)

# ==========================================
# 7. أخطاء الذكاء الاصطناعي
# ==========================================
class AIProviderError(SovereignError):
    def __init__(self, message: str = "فشل الاتصال بمزود الذكاء الاصطناعي"):
        super().__init__(message, status_code=503)
class NetworkError(Exception):
    """خطأ في الاتصال بالشبكة أو واجهات برمجة التطبيقات الخارجية (APIs)"""
    pass

class TimeoutError(Exception):
    """خطأ تجاوز وقت الاستجابة المحدد"""
    pass