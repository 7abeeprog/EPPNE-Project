// types/entity.ts

export enum SovereignEntityType {
  STATE_GOVERNMENT = "STATE_GOVERNMENT",
  MINISTRY_AUTHORITY = "MINISTRY_AUTHORITY",
  INTERNATIONAL_ORGANIZATION = "INTERNATIONAL_ORGANIZATION",
  MULTINATIONAL_CORP = "MULTINATIONAL_CORP",
  ENTERPRISE = "ENTERPRISE",
  NGO_CIVIL_SOCIETY = "NGO_CIVIL_SOCIETY",
  ACADEMIC_INSTITUTION = "ACADEMIC_INSTITUTION",
}

export enum KYBStatus {
  PENDING = "PENDING",
  UNDER_REVIEW = "UNDER_REVIEW",
  VERIFIED = "VERIFIED",
  REJECTED = "REJECTED",
  SUSPENDED = "SUSPENDED",
}

export enum EntityRole {
  OWNER = "OWNER",
  EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR",
  SIGNATORY = "SIGNATORY",
  REPRESENTATIVE = "REPRESENTATIVE",
}

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
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EntityRepresentative {
  id: number;
  entity_id: number;
  user_id: number;
  role: EntityRole;
  can_sign_contracts: boolean;
  signature_pub_key?: string;
  is_active: boolean;
  created_at: string;
}

export interface EntityDocument {
  id: number;
  entity_id: number;
  document_type: string;
  document_url: string;
  ipfs_hash?: string;
  status: string;
  rejection_reason?: string;
  created_at: string;
}

export interface CreateEntityPayload {
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
  logo_url?: string;
  cover_image_url?: string;
  primary_color?: string;
  secondary_color?: string;
  parent_id?: number;
}

export interface AddRepresentativePayload {
  user_id: number;
  role: EntityRole;
  can_sign_contracts: boolean;
  signature_pub_key?: string;
}

export interface KYBDocumentUploadPayload {
  document_type: string;
  document_url: string;
}
export interface AddRepresentativePayload {
  user_id: number;
  role: EntityRole;
  can_sign_contracts: boolean;
  signature_pub_key?: string;
}