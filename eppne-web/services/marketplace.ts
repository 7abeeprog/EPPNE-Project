// services/marketplace.ts
import api from '@/lib/axios';
import type {
  MarketplaceService,
  ServiceLicense,
  ServiceAddon,
  CustomizationRequest,
  PurchaseData,
  DeploymentStatusResponse,
  ServiceType,
  SubscriptionPlan,
} from '@/types/marketplace';

// ========== Services ==========
export const getServices = (params?: {
  service_type?: ServiceType;
  featured?: boolean;
  skip?: number;
  limit?: number;
}) => api.get<MarketplaceService[]>('/marketplace/services', { params });

export const getService = (serviceId: number) =>
  api.get<MarketplaceService>(`/marketplace/services/${serviceId}`);

// ========== Licenses ==========
export const getMyLicenses = (params?: { skip?: number; limit?: number }) =>
  api.get<ServiceLicense[]>('/marketplace/licenses/me', { params });

export const getDeploymentStatus = (licenseId: number) =>
  api.get<DeploymentStatusResponse>(`/marketplace/licenses/${licenseId}/status`);

export const purchaseService = (data: PurchaseData, idempotencyKey?: string) =>
  api.post<ServiceLicense>('/marketplace/purchase', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const renewLicense = (licenseId: number, idempotencyKey?: string) =>
  api.post<ServiceLicense>(`/marketplace/licenses/${licenseId}/renew`, null, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Add-ons ==========
export const getAddons = (params?: { compatible_with?: ServiceType }) =>
  api.get<ServiceAddon[]>('/marketplace/addons', { params });

export const purchaseAddon = (licenseId: number, addonId: number, idempotencyKey?: string) =>
  api.post<ServiceLicense>(`/marketplace/licenses/${licenseId}/addons/${addonId}`, null, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Customization ==========
export const requestCustomization = (licenseId: number, data: {
  title: string;
  description: string;
  proposed_budget_mrusdt?: number;
}) => api.post<CustomizationRequest>(`/marketplace/licenses/${licenseId}/customize`, data);

export const getCustomizationRequests = (licenseId: number) =>
  api.get<CustomizationRequest[]>(`/marketplace/licenses/${licenseId}/customizations`);