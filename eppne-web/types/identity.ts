// types/identity.ts

export interface User {
  id: number;
  username: string;
  email: string;
  name_ar: string;
  name_en: string;
  system_role: 'USER' | 'ADMIN' | 'SUPER_ADMIN' | 'EXECUTIVE_DIRECTOR';
  sovereign_rank: string;
  kyc_status: string;
  reputation_score: number;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username_or_email: string;
  password: string;
}

export interface LoginResponse {
  message: string;
  user_id: number;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  name_ar: string;
  name_en: string;
  idempotency_key: string;
}

export interface RegisterResponse {
  id: number;
  username: string;
  email: string;
  message: string;
}

export interface UserProfile extends User {
  birth_date?: string;
  marriage_status: string;
  language_preference: string;
  profile_metadata: Record<string, any>;
  preferences: Record<string, any>;
}

export interface UpdateProfileRequest {
  name_ar?: string;
  name_en?: string;
  email?: string;
  birth_date?: string;
  marriage_status?: string;
  language_preference?: string;
  profile_metadata?: Record<string, any>;
  preferences?: Record<string, any>;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface Session {
  id: number;
  device_name?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  expires_at: string;
  is_active: boolean;
}

export interface Wallet {
  id: number;
  user_id: number;
  wallet_address?: string;
  is_custodial: boolean;
  is_frozen: boolean;
  balances: Record<string, number>;
  created_at: string;
  updated_at: string;
}