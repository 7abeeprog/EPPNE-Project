// types/auth.ts
import type { components } from "@/src/lib/api-types";

// إعادة تصدير الأنواع من api-types مع أسماء مختصرة
export type User = components['schemas']['UserResponse'];
export type LoginRequest = components['schemas']['LoginRequest'];
export type LoginResponse = components['schemas']['LoginResponse'];
export type RefreshTokenResponse = components['schemas']['RefreshTokenResponse'];
export type RegisterRequest = components['schemas']['UserCreate'];
export type RegisterResponse = components['schemas']['UserResponse'];
export type RevokeAllSessionsResponse = components['schemas']['RevokeAllSessionsResponse'];
export type SessionInfo = components['schemas']['SessionInfoResponse'];

// ✅ إضافة نوع إضافي إذا لزم الأمر
export type SystemRole = components['schemas']['SystemRole'];
export type SovereignRank = components['schemas']['SovereignRank'];