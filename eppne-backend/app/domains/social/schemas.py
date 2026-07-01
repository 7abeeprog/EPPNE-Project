# app/domains/social/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.social.models import PostType, GroupPrivacy, ConnectionType

# ========== Posts ==========
class PostCreate(BaseModel):
    content: Optional[str] = None
    post_type: PostType = PostType.TEXT
    media_urls: List[str] = []
    page_id: Optional[int] = None
    group_id: Optional[int] = None
    share_reward_mr7: Decimal = 0

class PostResponse(BaseModel):
    id: int
    author_id: int
    content: Optional[str]
    post_type: PostType
    media_urls: List[str]
    likes_count: int
    comments_count: int
    shares_count: int
    share_reward_mr7: Decimal
    green_tag_verified: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None

# ========== Pages & Groups ==========
class SocialPageCreate(BaseModel):
    name: str
    slug: str
    about: Optional[str] = None

class SocialPageResponse(SocialPageCreate):
    id: int
    owner_id: int
    is_verified: bool
    page_wallet_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SocialGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    privacy: GroupPrivacy = GroupPrivacy.PUBLIC
    linked_project_id: Optional[int] = None

class SocialGroupResponse(SocialGroupCreate):
    id: int
    creator_id: int
    dao_contract_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Social Contracts ==========
class ContractTemplateCreate(BaseModel):
    name: str
    template_schema: Dict[str, Any]

class SocialContractCreate(BaseModel):
    template_id: Optional[int] = None
    contract_type: str
    title: str
    terms_and_conditions: Dict[str, Any]

class SocialContractResponse(SocialContractCreate):
    id: int
    creator_id: int
    status: str
    smart_contract_address: Optional[str]
    blockchain_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ContractSignRequest(BaseModel):
    contract_id: int
    digital_signature_hash: str

# ========== Events ==========
class SocialEventCreate(BaseModel):
    group_id: Optional[int] = None
    page_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    event_type: str
    start_time: datetime
    end_time: datetime
    location_details: Optional[Dict[str, Any]] = None
    requires_approval: bool = True

class SocialEventResponse(SocialEventCreate):
    id: int
    creator_id: int
    approval_status: str
    is_published: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== AI Matchmaking ==========
class AIMatchProfileCreate(BaseModel):
    seek_type: Dict[str, Any]
    ai_preferences: Dict[str, Any]
    is_discoverable: bool = True

class AIMatchProfileResponse(AIMatchProfileCreate):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConnectionRequest(BaseModel):
    target_user_id: int
    connection_type: ConnectionType

class ConnectionResponse(BaseModel):
    id: int
    user_a_id: int
    user_b_id: int
    connection_type: ConnectionType
    match_score: Optional[float]
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== المناسبات والتذكيرات ==========
class UserOccasionCreate(BaseModel):
    occasion_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    occasion_date: datetime
    is_public: bool = False
    remind_days_before: int = 7

class UserOccasionResponse(UserOccasionCreate):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== الهدايا ==========
class DigitalGiftCreate(BaseModel):
    receiver_id: int
    occasion_id: Optional[int] = None
    gift_type: str
    gift_value_mrusdt: Decimal = 0
    gift_message: Optional[str] = None
    gift_metadata: Dict[str, Any] = {}

class DigitalGiftResponse(DigitalGiftCreate):
    id: int
    sender_id: int
    sent_at: datetime
    is_redeemed: bool
    model_config = ConfigDict(from_attributes=True)

class PhysicalGiftCreate(BaseModel):
    receiver_id: int
    occasion_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str
    product_price_mrusdt: Decimal
    shipping_address: Dict[str, Any]

class PhysicalGiftResponse(PhysicalGiftCreate):
    id: int
    sender_id: int
    shipping_status: str
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== SaaS للمجموعات ==========
class GroupSubscriptionPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_monthly_mrusdt: Decimal = 0
    price_yearly_mrusdt: Decimal = 0
    included_features: List[str] = []

class GroupSubscriptionPlanResponse(GroupSubscriptionPlanCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GroupSubscriptionCreate(BaseModel):
    plan_id: int
    duration_months: int = 12

class GroupSubscriptionResponse(BaseModel):
    id: int
    group_id: int
    plan_id: int
    start_date: datetime
    end_date: datetime
    auto_renew: bool
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)