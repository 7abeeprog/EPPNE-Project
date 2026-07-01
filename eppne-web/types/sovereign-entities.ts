// types/sovereign-entities.ts
export type SovereignEntityType = 
  | 'STATE_GOVERNMENT' 
  | 'MINISTRY_AUTHORITY' 
  | 'INTERNATIONAL_ORGANIZATION'
  | 'MULTINATIONAL_CORP'
  | 'ENTERPRISE'
  | 'NGO_CIVIL_SOCIETY'
  | 'ACADEMIC_INSTITUTION'
  | 'DIVISION'
  | 'TEAM';

export type KYBStatus = 'PENDING' | 'UNDER_REVIEW' | 'VERIFIED' | 'REJECTED' | 'SUSPENDED';
export type EntityRole = 'OWNER' | 'EXECUTIVE_DIRECTOR' | 'SIGNATORY' | 'REPRESENTATIVE';

export interface SovereignEntity {
  id: number;
  tenant_id: number;
  name: string;
  legal_name?: string;
  entity_type: SovereignEntityType;
  registration_number?: string;
  tax_id?: string;
  country_of_origin: string;
  city?: string;
  address?: string;
  official_email: string;
  official_phone?: string;
  website?: string;
  wallet_address?: string;
  treasury_balance_mrusdt: number;
  logo_url?: string;
  cover_image_url?: string;
  primary_color: string;
  secondary_color: string;
  kyb_status: KYBStatus;
  kyb_documents: any[];
  is_active: boolean;
  parent_id?: number;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface EntityRepresentative {
  id: number;
  entity_id: number;
  user_id: number;
  role: EntityRole;
  is_active: boolean;
  can_sign_contracts: boolean;
  signature_pub_key?: string;
  created_at: string;
}

export interface EntityPage {
  id: number;
  entity_id: number;
  template_id?: number;
  custom_structure?: any;
  slug: string;
  meta_title?: string;
  meta_description?: string;
  custom_domain?: string;
  visits_count: number;
  last_visit_at?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

export interface EntityDocument {
  id: number;
  entity_id: number;
  document_type: string;
  document_url: string;
  ipfs_hash?: string;
  uploaded_by: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  verified_by?: number;
  verified_at?: string;
  rejection_reason?: string;
  created_at: string;
}

// ========== UI-specific Types ==========
export interface EntityFormData {
  name: string;
  legal_name?: string;
  entity_type: SovereignEntityType;
  registration_number?: string;
  tax_id?: string;
  country_of_origin: string;
  city?: string;
  address?: string;
  official_email: string;
  official_phone?: string;
  website?: string;
  wallet_address?: string;
  logo_file?: File;
  cover_image_file?: File;
  primary_color: string;
  secondary_color: string;
  parent_id?: number;
}

export interface EntityTreeItem {
  id: number;
  name: string;
  entity_type: SovereignEntityType;
  logo_url?: string;
  children: EntityTreeItem[];
}

// ========== KYB Document Upload ==========
export interface KYBDocumentUpload {
  document_type: string;
  document_url: string;
}

// ============================================================
// 🆕 الإضافات الجديدة للعمليات المالية
// ============================================================

export interface EntityDepositRequest {
  /** المبلغ المراد إيداعه في محفظة الكيان */
  amount: number;
  /** عملة الإيداع (افتراضي: MR_USDT) */
  currency: string;
  /** ملاحظات اختيارية */
  notes?: string;
}

export interface EntityTransferRequest {
  /** العنوان المستهدف (بريد إلكتروني أو محفظة) */
  to_address: string;
  /** المبلغ المراد تحويله */
  amount: number;
  /** عملة التحويل (افتراضي: MR_USDT) */
  currency: string;
  /** ملاحظات اختيارية */
  notes?: string;
}