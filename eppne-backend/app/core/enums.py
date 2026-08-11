import enum
from enum import Enum

class AffiliateStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class CommissionStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    
class SystemRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"

class SovereignRank(str, enum.Enum):
    CITIZEN_L1 = "CITIZEN_L1"
    VETERAN_L2 = "VETERAN_L2"
    INVESTOR_L3 = "INVESTOR_L3"
    LEADER_L4 = "LEADER_L4"
    GOVERNOR_L5 = "GOVERNOR_L5"
    MINISTER_L6 = "MINISTER_L6"
    FOUNDER_L7 = "FOUNDER_L7"

class KYCStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class MarriageStatus(str, enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"

class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"