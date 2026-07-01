// services/iot.service.ts
import apiClient from '@/lib/axios'; // نفترض وجود `lib/axios` في الجذر
import { SmartAsset, UtilityReading, MaintenanceLog, CarbonSettlementResponse } from '@/types/iot';

// توليد مفتاح Idempotency تلقائياً
async function generateIdempotencyKey(payload: any): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(JSON.stringify(payload) + Date.now().toString());
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export const iotService = {
  // ---------- الأصول ----------
  getAssets: async (params?: { asset_class?: string; skip?: number; limit?: number }): Promise<SmartAsset[]> => {
    const response = await apiClient.get<SmartAsset[]>('/iot/assets', { params });
    return response.data;
  },

  createAsset: async (data: Omit<SmartAsset, 'id' | 'owner_id' | 'created_at' | 'is_online' | 'health_status'>): Promise<SmartAsset> => {
    const response = await apiClient.post<SmartAsset>('/iot/assets', data);
    return response.data;
  },

  updateAsset: async (id: number, data: Partial<SmartAsset>): Promise<SmartAsset> => {
    const response = await apiClient.patch<SmartAsset>(`/iot/assets/${id}`, data);
    return response.data;
  },

  // ---------- القراءات ----------
  getReadings: async (params?: { asset_id?: number; grid_id?: number; limit?: number }): Promise<UtilityReading[]> => {
    const response = await apiClient.get<UtilityReading[]>('/iot/readings', { params });
    return response.data;
  },

  ingestReading: async (data: Partial<UtilityReading>): Promise<{ status: string; reading_id: number; carbon_credits: number }> => {
    const idemKey = await generateIdempotencyKey(data);
    const response = await apiClient.post('/iot/readings', data, {
      headers: { 'Idempotency-Key': idemKey }
    });
    return response.data;
  },

  // ---------- الكربون ----------
  settleCarbon: async (asset_ids?: number[]): Promise<CarbonSettlementResponse> => {
    const payload = { asset_ids: asset_ids || null };
    const idemKey = await generateIdempotencyKey(payload);
    const response = await apiClient.post('/iot/carbon/settle', payload, {
      headers: { 'Idempotency-Key': idemKey }
    });
    return response.data;
  },

  // ---------- الصيانة ----------
  getMaintenanceLogs: async (asset_id?: number): Promise<MaintenanceLog[]> => {
    const response = await apiClient.get<MaintenanceLog[]>('/iot/maintenance', { params: { asset_id } });
    return response.data;
  },

  createMaintenance: async (data: Omit<MaintenanceLog, 'id' | 'technician_id' | 'is_resolved' | 'resolution_date' | 'created_at'>): Promise<MaintenanceLog> => {
    const response = await apiClient.post<MaintenanceLog>('/iot/maintenance', data);
    return response.data;
  },

  resolveMaintenance: async (log_id: number): Promise<MaintenanceLog> => {
    const response = await apiClient.post<MaintenanceLog>(`/iot/maintenance/${log_id}/resolve`);
    return response.data;
  },
};