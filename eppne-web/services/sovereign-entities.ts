// services/sovereign-entities.ts
import api from '@/lib/axios';
import type {
  SovereignEntity,
  SovereignEntityType,
  KYBStatus,
  EntityRepresentative,
  EntityPage,
  EntityDocument,
  EntityFormData,
  EntityTreeItem,
  KYBDocumentUpload
} from '@/types/sovereign-entities';

// ========== Helper: Generate Idempotency Key ==========
export const generateIdempotencyKey = (payload: any): string => {
  // ربط المفتاح ببيانات الطلب لمنع تكرار العمليات بنفس البيانات
  const stableString = JSON.stringify(payload);
  let hash = 0;
  for (let i = 0; i < stableString.length; i++) {
    const char = stableString.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return `entity-${Date.now()}-${Math.abs(hash)}`;
};

// ========== Entities ==========
export const getMyEntities = (params?: { entity_type?: SovereignEntityType; kyb_status?: KYBStatus }) =>
  api.get<SovereignEntity[]>('/sovereign-entities/me', { params });

export const getEntity = (entityId: number) =>
  api.get<SovereignEntity>(`/sovereign-entities/${entityId}`);

export const createEntity = (data: FormData) =>
  api.post<SovereignEntity>('/sovereign-entities/', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

export const updateEntity = (entityId: number, data: Partial<EntityFormData>) =>
  api.put<SovereignEntity>(`/sovereign-entities/${entityId}`, data);

export const deleteEntity = (entityId: number, soft: boolean = true) =>
  api.delete(`/sovereign-entities/${entityId}?soft=${soft}`);

// ========== Entity Tree ==========
export const getEntityTree = (entityId: number) =>
  api.get<EntityTreeItem>(`/sovereign-entities/${entityId}/tree`);

// ========== Representatives ==========
export const getRepresentatives = (entityId: number) =>
  api.get<EntityRepresentative[]>(`/sovereign-entities/${entityId}/representatives`);

export const addRepresentative = (entityId: number, data: { user_id: number; role: string; can_sign_contracts: boolean }) =>
  api.post<EntityRepresentative>(`/sovereign-entities/${entityId}/representatives`, data);

export const removeRepresentative = (entityId: number, userId: number) =>
  api.delete(`/sovereign-entities/${entityId}/representatives/${userId}`);

// ========== Wallet ==========
export const getEntityBalance = (entityId: number) =>
  api.get<{ entity_id: number; balance_mrusdt: number }>(`/sovereign-entities/${entityId}/balance`);

export const depositToEntity = (
  entityId: number,
  data: { amount: number; currency: string; notes?: string },
  idempotencyKey: string
) =>
  api.post(`/sovereign-entities/${entityId}/deposit`, data, {
    headers: { 'Idempotency-Key': idempotencyKey }
  });

export const transferFromEntity = (
  entityId: number,
  data: { to_address: string; amount: number; currency: string; notes?: string },
  idempotencyKey: string
) =>
  api.post(`/sovereign-entities/${entityId}/transfer`, data, {
    headers: { 'Idempotency-Key': idempotencyKey }
  });

// ========== KYB Documents ==========
export const uploadKYBDocument = (entityId: number, data: { document_type: string; document_url: string }) =>
  api.post<EntityDocument>(`/sovereign-entities/${entityId}/kyb/documents`, data);

export const getKYBDocuments = (entityId: number) =>
  api.get<EntityDocument[]>(`/sovereign-entities/${entityId}/kyb/documents`);

export const reviewKYB = (entityId: number, data: { status: KYBStatus; rejection_reason?: string }) =>
  api.put<SovereignEntity>(`/sovereign-entities/${entityId}/kyb/status`, data);

// ========== Entity Page (Brand Builder) ==========
export const getEntityPage = (entityId: number) =>
  api.get<{ entity: any; page: EntityPage }>(`/sovereign-entities/${entityId}/page`);

export const updateEntityPage = (entityId: number, data: Partial<EntityPage>) =>
  api.put<EntityPage>(`/sovereign-entities/${entityId}/page`, data);

export const publishEntityPage = (entityId: number) =>
  api.post<EntityPage>(`/sovereign-entities/${entityId}/page/publish`);

// ========== Public Page (no auth) ==========
export const getPublicEntityPage = (slug: string) =>
  api.get<{ entity: any; page: any }>(`/sovereign-entities/public/${slug}`);
// services/sovereign-entities.ts (إضافة)
export const getPublicEntityPage = (slug: string) =>
  api.get<{ entity: any; page: any }>(`/sovereign-entities/public/${slug}`).then(res => res.data);