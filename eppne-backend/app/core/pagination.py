# app/core/pagination.py
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    نموذج موحد للـ Pagination.
    متوافق مع Pydantic V2 ويستخدم Generics لأنواع بيانات آمنة.
    """
    data: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool = False  # مفيد للـ Frontend لتحديد وجود صفحة تالية

    # تحديث للـ Pydantic V2 (يستبدل class Config)
    model_config = ConfigDict(from_attributes=True)

    # يمكن إضافة دالة مساعدة لتوليد الـ has_more تلقائياً إذا أردت
    # لكن الأفضل حسابها في طبقة الـ Repository لتجنب ضرب استعلام إضافي للـ Count.