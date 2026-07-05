// types/finance.ts

// ==========================================
// 1. المحفظة والأرصدة
// ==========================================

export interface WalletBalance {
  balances: Record<string, number>;
}

export interface WalletBalanceWithRates extends WalletBalance {
  total_value: number;
  rates: ExchangeRates;
}

// ==========================================
// 2. التحويلات
// ==========================================

export interface TransferRequest {
  receiver_email: string;
  currency: string;
  amount: number;
  notes?: string | null;
  idempotency_key?: string | null; // ✅ اختياري وقابل للـ null
}

export interface TransferResponse {
  tx_hash: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
}

// ==========================================
// 3. الصرافة
// ==========================================

export interface SwapRequest {
  from_currency: string;
  to_currency: string;
  amount_in: number;
  idempotency_key?: string | null; // ✅ اختياري وقابل للـ null
}

export interface SwapResponse {
  from_amount: number;
  from_currency: string;
  to_amount: number;
  to_currency: string;
  rate_applied: number;
  tx_hash: string;
}

// ==========================================
// 4. سجل المعاملات
// ==========================================

export interface Transaction {
  id: number; // ✅ مطلوب حسب الطلب
  tx_hash: string;
  tx_type: string;
  amount: number;
  currency: string;
  status: string; // ✅ أصبح string بدلاً من union
  notes?: string | null;
  created_at: string;
  sender_id?: number | null; // ✅ اختياري
  receiver_id?: number | null; // ✅ اختياري
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}

// ==========================================
// 5. إدارة النظام (للمشرفين)
// ==========================================

export interface CryptoMode {
  crypto_mode: 'FULL_CRYPTO' | 'POINTS_ONLY';
}

export interface ExchangeRates {
  [currency: string]: number;
}

export interface MintRequest {
  currency: string;
  amount: number;
}

export interface SystemState {
  // الخصائص المطلوبة (مع تعديل total_supply لتكون اختيارية وإضافة active_users)
  total_supply?: Record<string, number>;
  active_users?: number;

  // الخصائص الإضافية الموجودة فعلياً في النظام (محتفظ بها)
  crypto_mode: string;
  is_trading_active: boolean;
  exchange_rates: ExchangeRates;
  max_supply: ExchangeRates;
  updated_at: string;
}

// ==========================================
// 6. عملات مدعومة (ثابتة)
// ==========================================

export const SUPPORTED_CURRENCIES = [
  'MR_POUND',
  'MR_USDT',
  'MR7',
  'NBT',
  'MRX',
  'LOYALTY_POINTS',
] as const;

export type SupportedCurrency = typeof SUPPORTED_CURRENCIES[number];

export const CURRENCY_LABELS: Record<SupportedCurrency, string> = {
  MR_POUND: 'الجنيه السيادي',
  MR_USDT: 'الدولار السيادي',
  MR7: 'نبت 7',
  NBT: 'نبت',
  MRX: 'ماركس',
  LOYALTY_POINTS: 'نقاط الولاء',
};

export const CURRENCY_ICONS: Record<SupportedCurrency, string> = {
  MR_POUND: '£',
  MR_USDT: '$',
  MR7: '₿',
  NBT: 'Ⓝ',
  MRX: 'Ⓜ',
  LOYALTY_POINTS: '⭐',
};

export const CURRENCY_COLORS: Record<SupportedCurrency, string> = {
  MR_POUND: 'text-emerald-500',
  MR_USDT: 'text-blue-500',
  MR7: 'text-amber-500',
  NBT: 'text-purple-500',
  MRX: 'text-rose-500',
  LOYALTY_POINTS: 'text-amber-400',
};