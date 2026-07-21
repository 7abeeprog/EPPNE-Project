# app/domains/social/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.social.models import PostType, GroupPrivacy, ConnectionType


# ========== Posts ==========
class PostCreate(BaseModel):
    content: Optional[str] = Field(default=None, description="محتوى المنشور")
    post_type: PostType = Field(default=PostType.TEXT, description="نوع المنشور")
    media_urls: List[str] = Field(default=[], description="روابط الوسائط")
    page_id: Optional[int] = Field(default=None, description="معرف الصفحة")
    group_id: Optional[int] = Field(default=None, description="معرف المجموعة")
    share_reward_mr7: Decimal = Field(default=Decimal('0.0'), description="مكافأة المشاركة")

class PostResponse(BaseModel):
    id: int = Field(description="معرف المنشور")
    author_id: int = Field(description="معرف المؤلف")
    content: Optional[str] = Field(description="المحتوى")
    post_type: PostType = Field(description="النوع")
    media_urls: List[str] = Field(description="روابط الوسائط")
    likes_count: int = Field(description="عدد الإعجابات")
    comments_count: int = Field(description="عدد التعليقات")
    shares_count: int = Field(description="عدد المشاركات")
    share_reward_mr7: Decimal = Field(description="مكافأة المشاركة")
    green_tag_verified: bool = Field(description="تم التحقق بالعلامة الخضراء")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    content: str = Field(description="محتوى التعليق")
    parent_comment_id: Optional[int] = Field(default=None, description="معرف التعليق الأب")

# ========== Pages & Groups ==========
class SocialPageCreate(BaseModel):
    name: str = Field(description="اسم الصفحة")
    slug: str = Field(description="الرابط المختصر")
    about: Optional[str] = Field(default=None, description="عن الصفحة")

class SocialPageResponse(SocialPageCreate):
    id: int = Field(description="معرف الصفحة")
    owner_id: int = Field(description="معرف المالك")
    is_verified: bool = Field(description="موثقة")
    page_wallet_address: Optional[str] = Field(default=None, description="عنوان المحفظة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class SocialGroupCreate(BaseModel):
    name: str = Field(description="اسم المجموعة")
    description: Optional[str] = Field(default=None, description="وصف المجموعة")
    privacy: GroupPrivacy = Field(default=GroupPrivacy.PUBLIC, description="الخصوصية")
    linked_project_id: Optional[int] = Field(default=None, description="معرف المشروع المرتبط")

class SocialGroupResponse(SocialGroupCreate):
    id: int = Field(description="معرف المجموعة")
    creator_id: int = Field(description="معرف المنشئ")
    dao_contract_address: Optional[str] = Field(default=None, description="عنوان عقد DAO")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Social Contracts ==========
class ContractTemplateCreate(BaseModel):
    name: str = Field(description="اسم القالب")
    template_schema: Dict[str, Any] = Field(description="مخطط القالب")

class SocialContractCreate(BaseModel):
    template_id: Optional[int] = Field(default=None, description="معرف القالب")
    contract_type: str = Field(description="نوع العقد")
    title: str = Field(description="عنوان العقد")
    terms_and_conditions: Dict[str, Any] = Field(description="الشروط والأحكام")

class SocialContractResponse(SocialContractCreate):
    id: int = Field(description="معرف العقد")
    creator_id: int = Field(description="معرف المنشئ")
    status: str = Field(description="الحالة")
    smart_contract_address: Optional[str] = Field(default=None, description="عنوان العقد الذكي")
    blockchain_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة البلوكشين")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class ContractSignRequest(BaseModel):
    contract_id: int = Field(description="معرف العقد")
    digital_signature_hash: str = Field(description="هاش التوقيع الرقمي")

# ========== Events ==========
class SocialEventCreate(BaseModel):
    group_id: Optional[int] = Field(default=None, description="معرف المجموعة")
    page_id: Optional[int] = Field(default=None, description="معرف الصفحة")
    title: str = Field(description="عنوان الفعالية")
    description: Optional[str] = Field(default=None, description="وصف الفعالية")
    event_type: str = Field(description="نوع الفعالية")
    start_time: datetime = Field(description="وقت البدء")
    end_time: datetime = Field(description="وقت الانتهاء")
    location_details: Optional[Dict[str, Any]] = Field(default=None, description="تفاصيل الموقع")
    requires_approval: bool = Field(default=True, description="يتطلب موافقة")

class SocialEventResponse(SocialEventCreate):
    id: int = Field(description="معرف الفعالية")
    creator_id: int = Field(description="معرف المنشئ")
    approval_status: str = Field(description="حالة الموافقة")
    is_published: bool = Field(description="منشورة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== AI Matchmaking ==========
class AIMatchProfileCreate(BaseModel):
    seek_type: Dict[str, Any] = Field(description="نوع البحث")
    ai_preferences: Dict[str, Any] = Field(description="تفضيلات الذكاء الاصطناعي")
    is_discoverable: bool = Field(default=True, description="قابل للاكتشاف")

class AIMatchProfileResponse(AIMatchProfileCreate):
    id: int = Field(description="معرف الملف")
    user_id: int = Field(description="معرف المستخدم")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class ConnectionRequest(BaseModel):
    target_user_id: int = Field(description="معرف المستخدم المستهدف")
    connection_type: ConnectionType = Field(description="نوع الاتصال")

class ConnectionResponse(BaseModel):
    id: int = Field(description="معرف الاتصال")
    user_a_id: int = Field(description="المستخدم الأول")
    user_b_id: int = Field(description="المستخدم الثاني")
    connection_type: ConnectionType = Field(description="نوع الاتصال")
    match_score: Optional[float] = Field(default=None, description="درجة التوافق")
    status: str = Field(description="الحالة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== المناسبات والتذكيرات ==========
class UserOccasionCreate(BaseModel):
    occasion_type: str = Field(description="نوع المناسبة")
    title: Optional[str] = Field(default=None, description="العنوان")
    description: Optional[str] = Field(default=None, description="الوصف")
    occasion_date: datetime = Field(description="تاريخ المناسبة")
    is_public: bool = Field(default=False, description="عامة")
    remind_days_before: int = Field(default=7, description="أيام التذكير قبل الموعد")

class UserOccasionResponse(UserOccasionCreate):
    id: int = Field(description="معرف المناسبة")
    user_id: int = Field(description="معرف المستخدم")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== الهدايا ==========
class DigitalGiftCreate(BaseModel):
    receiver_id: int = Field(description="معرف المتلقي")
    occasion_id: Optional[int] = Field(default=None, description="معرف المناسبة")
    gift_type: str = Field(description="نوع الهدية")
    gift_value_mrusdt: Decimal = Field(default=Decimal('0.0'), description="القيمة")
    gift_message: Optional[str] = Field(default=None, description="رسالة الهدية")
    gift_metadata: Dict[str, Any] = Field(default={}, description="بيانات إضافية")

class DigitalGiftResponse(DigitalGiftCreate):
    id: int = Field(description="معرف الهدية")
    sender_id: int = Field(description="معرف المرسل")
    sent_at: datetime = Field(description="تاريخ الإرسال")
    is_redeemed: bool = Field(description="تم الاستلام")
    model_config = ConfigDict(from_attributes=True)

class PhysicalGiftCreate(BaseModel):
    receiver_id: int = Field(description="معرف المتلقي")
    occasion_id: Optional[int] = Field(default=None, description="معرف المناسبة")
    product_id: Optional[int] = Field(default=None, description="معرف المنتج")
    product_name: str = Field(description="اسم المنتج")
    product_price_mrusdt: Decimal = Field(description="سعر المنتج")
    shipping_address: Dict[str, Any] = Field(description="عنوان الشحن")

class PhysicalGiftResponse(PhysicalGiftCreate):
    id: int = Field(description="معرف الهدية")
    sender_id: int = Field(description="معرف المرسل")
    shipping_status: str = Field(description="حالة الشحن")
    payment_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة الدفع")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== SaaS للمجموعات ==========
class GroupSubscriptionPlanCreate(BaseModel):
    name: str = Field(description="اسم الخطة")
    description: Optional[str] = Field(default=None, description="الوصف")
    price_monthly_mrusdt: Decimal = Field(default=Decimal('0.0'), description="السعر الشهري")
    price_yearly_mrusdt: Decimal = Field(default=Decimal('0.0'), description="السعر السنوي")
    included_features: List[str] = Field(default=[], description="الميزات المشمولة")

class GroupSubscriptionPlanResponse(GroupSubscriptionPlanCreate):
    id: int = Field(description="معرف الخطة")
    is_active: bool = Field(description="نشطة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class GroupSubscriptionCreate(BaseModel):
    plan_id: int = Field(description="معرف الخطة")
    duration_months: int = Field(default=12, description="مدة الاشتراك بالأشهر")

class GroupSubscriptionResponse(BaseModel):
    id: int = Field(description="معرف الاشتراك")
    group_id: int = Field(description="معرف المجموعة")
    plan_id: int = Field(description="معرف الخطة")
    start_date: datetime = Field(description="تاريخ البداية")
    end_date: datetime = Field(description="تاريخ النهاية")
    auto_renew: bool = Field(description="التجديد التلقائي")
    status: str = Field(description="الحالة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)