# app/core/pagination.py
from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """نموذج قياسي موحد للـ Pagination."""
    data: List[T]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True # لضمان توافق Pydantic V2 مع SQLAlchemy