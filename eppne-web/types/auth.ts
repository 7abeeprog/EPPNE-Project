// types/auth.ts

export interface User {
  id: number;
  username: string;
  email: string;
  system_role: 'STUDENT' | 'INSTRUCTOR' | 'ENTERPRISE' | 'ADMIN' | 'SUPER_ADMIN' | 'EXECUTIVE_DIRECTOR';
  sovereign_rank: string;
  tenant_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
  device_name?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  tenant_id?: number;
}

export interface RegisterResponse {
  id: number;
  username: string;
  email: string;
  message: string;
}

export interface RevokeAllSessionsResponse {
  message: string;
  revoked_count: number;
}

export interface SessionInfo {
  id: number;
  device_name?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  expires_at: string;
  is_active: boolean;
}

// ❌ تم حذف RefreshTokenRequest و LogoutRequest نهائياً