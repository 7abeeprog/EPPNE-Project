// types/privacy.ts

// ==========================================
// 1. إعدادات الخصوصية (Privacy Settings)
// ==========================================

export interface PrivacySettings {
    id: number;
    user_id: number;
    profile_visibility: 'PUBLIC' | 'FRIENDS_ONLY' | 'PRIVATE';
    search_engine_indexing: boolean;
    allow_ai_training: boolean;
    allow_targeted_ads: boolean;
    share_live_location: boolean;
    created_at: string;
    updated_at: string;
}

// ==========================================
// 2. طلبات محو البيانات (Erasure Requests)
// ==========================================

export type TargetModule =
    | 'identity'
    | 'academy'
    | 'finance'
    | 'commerce'
    | 'health'
    | 'iot'
    | 'realestate'
    | 'all';

export type ErasureStatus =
    | 'PENDING'
    | 'PROCESSING'
    | 'COMPLETED'
    | 'PARTIAL_ON_CHAIN'
    | 'REJECTED';

export interface ErasureRequest {
    id: number;
    user_id: number;
    target_module: TargetModule;
    reason?: string;
    status: ErasureStatus;
    processed_at?: string;
    erasure_receipt_tx?: string;
    created_at: string;
}

// ==========================================
// 3. سجلات الموافقات (Consent Logs)
// ==========================================

export type ConsentType =
    | 'DATA_PROCESSING'
    | 'AI_TRAINING'
    | 'MARKETING'
    | 'THIRD_PARTY';

export interface ConsentLog {
    id: number;
    user_id: number;
    consent_type: ConsentType;
    is_granted: boolean;
    ip_address?: string;
    user_agent?: string;
    consent_tx_hash?: string;
    created_at: string;
}

// ==========================================
// 4. دعم Pagination
// ==========================================

export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    skip: number;
    limit: number;
}

// ==========================================
// 5. مخططات الإرسال (Payloads)
// ==========================================

export interface UpdatePrivacySettingsPayload {
    profile_visibility?: 'PUBLIC' | 'FRIENDS_ONLY' | 'PRIVATE';
    search_engine_indexing?: boolean;
    allow_ai_training?: boolean;
    allow_targeted_ads?: boolean;
    share_live_location?: boolean;
}

export interface CreateErasureRequestPayload {
    target_module: TargetModule;
    reason?: string;
}

export interface ProcessErasureRequestPayload {
    approve: boolean;
    notes?: string;
}

// ==========================================
// 6. قائمة القطاعات المتاحة (للواجهة)
// ==========================================

export const TARGET_MODULES: { value: TargetModule; label: string }[] = [
    { value: 'identity', label: 'الهوية الشخصية' },
    { value: 'academy', label: 'الأكاديمية' },
    { value: 'finance', label: 'المالية' },
    { value: 'commerce', label: 'التجارة' },
    { value: 'health', label: 'الصحة' },
    { value: 'iot', label: 'إنترنت الأشياء' },
    { value: 'realestate', label: 'العقارات' },
    { value: 'all', label: 'جميع القطاعات' },
];

export const CONSENT_TYPES: { value: ConsentType; label: string }[] = [
    { value: 'DATA_PROCESSING', label: 'معالجة البيانات' },
    { value: 'AI_TRAINING', label: 'تدريب الذكاء الاصطناعي' },
    { value: 'MARKETING', label: 'التسويق' },
    { value: 'THIRD_PARTY', label: 'أطراف ثالثة' },
];

export const ERASURE_STATUS: { value: ErasureStatus; label: string; color: string }[] = [
    { value: 'PENDING', label: 'قيد الانتظار', color: 'text-yellow-500' },
    { value: 'PROCESSING', label: 'جاري المعالجة', color: 'text-blue-500' },
    { value: 'COMPLETED', label: 'مكتمل', color: 'text-emerald-500' },
    { value: 'PARTIAL_ON_CHAIN', label: 'مكتمل جزئياً', color: 'text-purple-500' },
    { value: 'REJECTED', label: 'مرفوض', color: 'text-destructive' },
];