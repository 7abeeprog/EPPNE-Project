// types/commerce.ts

export interface Product {
  id: number;
  store_id: number;
  title: string;
  description?: string;
  product_type: 'PHYSICAL' | 'DIGITAL' | 'SERVICE' | 'COURSE';
  base_price_mrusdt: number;
  is_published: boolean;
  is_active: boolean;
  is_affiliate_eligible: boolean;
  variants: ProductVariant[];
  media_gallery: string[];
  created_at: string;
  updated_at: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  sku: string;
  attributes: Record<string, any>;
  price_mrusdt: number;
  discount_price?: number;
  discount_end_date?: string;
  stock_quantity: number;
  is_wholesale_enabled: boolean;
  wholesale_min_qty?: number;
  wholesale_price_mrusdt?: number;
}

export interface CartItem {
  variant_id: number;
  quantity: number;
  product?: Product;
  variant?: ProductVariant;
}

export interface Address {
  id: number;
  country: string;
  city: string;
  state?: string;
  postal_code?: string;
  street_line1: string;
  street_line2?: string;
  is_default: boolean;
}

export interface CheckoutRequest {
  store_id: number;
  items: { variant_id: number; quantity: number }[];
  shipping_address_id?: number;
  settlement_type: 'WALLET_DEDUCTION' | 'AGENT' | 'VISA' | 'CASH_ON_DELIVERY';
  affiliate_code?: string;
  idempotency_key: string;
  tenant_id: number;
}

export interface CheckoutResponse {
  id: number;
  status: string;
  total_amount_mrusdt: number;
  created_at: string;
}

export interface Order {
  id: number;
  store_id: number;
  customer_id: number;
  total_amount_mrusdt: number;
  discount_applied: number;
  tax_amount: number;
  shipping_fee: number;
  status: 'PENDING_PAYMENT' | 'PAID' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';
  settlement_type: string;
  created_at: string;
  items: OrderItem[];
}

export interface OrderItem {
  product_id: number;
  variant_id?: number;
  quantity: number;
  unit_price_mrusdt: number;
  total_price_mrusdt: number;
}

export interface PaymentRequest {
  id: number;
  order_id: number;
  payment_method: 'AGENT' | 'VISA' | 'CASH_ON_DELIVERY';
  amount: number;
  currency: string;
  agent_code?: string;
  status: 'PENDING' | 'PAID' | 'FAILED' | 'CANCELLED';
  created_at: string;
}

export interface AffiliateTree {
  user_id: number;
  sponsor_id: number;
  network_depth: number;
  created_at: string;
}

export interface Commission {
  id: number;
  beneficiary_id: number;
  order_id: number;
  level_earned: number;
  amount: number;
  currency: string;
  status: 'PENDING' | 'RELEASED' | 'CANCELED';
  created_at: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface WalletBalance {
  balances: Record<string, number>;
}