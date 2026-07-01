// types/affiliate.ts

export interface AffiliateProfile {
  id: number;
  user_id: number;
  tenant_id: number;
  referral_code: string;
  custom_slug?: string;
  default_commission_rate: number;
  is_active: boolean;
  total_clicks: number;
  total_conversions: number;
  total_earned: number;
  total_paid: number;
  created_at: string;
  updated_at: string;
}

export interface ReferralTree {
  user_id: number;
  referrer_id: number;
  depth: number;
  entity_type: 'GLOBAL' | 'PRODUCT' | 'SERVICE_CATEGORY';
  entity_id?: number;
  created_at: string;
}

export interface Commission {
  id: number;
  affiliate_id: number;
  user_id: number;
  order_id: number;
  product_id: number;
  order_item_id: number;
  item_amount: number;
  commission_rate: number;
  commission_amount: number;
  currency: string;
  referral_level: number;
  status: 'PENDING' | 'CONFIRMED' | 'PAID' | 'CANCELLED';
  paid_at?: string;
  paid_tx_hash?: string;
  created_at: string;
  updated_at: string;
  product?: {
    id: number;
    title: string;
  };
  order?: {
    id: number;
    total_amount_mrusdt: number;
  };
}

export interface AffiliateLink {
  id: number;
  affiliate_id: number;
  target: string;
  target_id?: number;
  product_id?: number;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  clicks: number;
  conversions: number;
  created_at: string;
  updated_at: string;
  product?: {
    id: number;
    title: string;
  };
}

export interface AffiliateStats {
  user_id: number;
  referral_code: string;
  total_referrals: number;
  active_referrals: number;
  total_clicks: number;
  total_conversions: number;
  total_earned: number;
  pending_earned: number;
  paid_earned: number;
  conversion_rate: number;
  top_performing_product?: {
    product_id: number;
    title: string;
    conversions: number;
  };
}

export interface WithdrawRequest {
  amount: number;
  idempotency_key?: string;
}

export interface WithdrawResponse {
  message: string;
  tx_hash: string;
  amount: number;
  currency: string;
  paid_commissions: number;
  created_at: string;
}

export interface AffiliateDashboardStats {
  total_referrals: number;
  total_earned: number;
  pending_earned: number;
  total_clicks: number;
  conversion_rate: number;
  recent_commissions: Commission[];
  top_links: AffiliateLink[];
}