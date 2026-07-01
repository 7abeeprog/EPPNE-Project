// services/zamakana.ts
import api from '@/lib/axios';
import type {
  ZamakanaNode,
  ZamakanaEdge,
  PlanetaryCampaign,
  TimePledge,
  FutureScenario,
  HumanFeedback,
  GraphData,
  ZamakanaNodeType,
  ScenarioStatus,
  PledgeStatus,
} from '@/types/zamakana';

// ========== Nodes ==========
export const getNodes = (params?: { node_type?: ZamakanaNodeType; skip?: number; limit?: number }) =>
  api.get<ZamakanaNode[]>('/zamakana/nodes', { params });

export const getNode = (id: number) => api.get<ZamakanaNode>(`/zamakana/nodes/${id}`);

export const createNode = (data: {
  node_type: ZamakanaNodeType;
  title: string;
  description: string;
  timeline_year?: number;
  geo_location?: string;
  verified_sources?: string[];
  extra_data?: Record<string, any>;
}) => api.post<ZamakanaNode>('/zamakana/nodes', data);

export const updateNode = (id: number, data: Partial<Parameters<typeof createNode>[0]>) =>
  api.put<ZamakanaNode>(`/zamakana/nodes/${id}`, data);

export const deleteNode = (id: number) => api.delete(`/zamakana/nodes/${id}`);

// ========== Edges ==========
export const createEdge = (
  data: {
    source_node_id: number;
    target_node_id: number;
    impact_description: string;
    impact_weight?: number;
    is_alternative_timeline?: boolean;
  },
  idempotencyKey?: string
) =>
  api.post<ZamakanaEdge>('/zamakana/edges', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getKnowledgeGraph = (params?: { node_type?: ZamakanaNodeType; limit?: number }) =>
  api.get<GraphData>('/zamakana/graph', { params });

// ========== Campaigns ==========
export const getCampaigns = (params?: { status?: string; skip?: number; limit?: number }) =>
  api.get<PlanetaryCampaign[]>('/zamakana/campaigns', { params });

export const getCampaign = (id: number) => api.get<PlanetaryCampaign>(`/zamakana/campaigns/${id}`);

export const createCampaign = (data: {
  title: string;
  description: string;
  target_time_hours: number;
  end_date: string;
}) => api.post<PlanetaryCampaign>('/zamakana/campaigns', data);

// ========== Pledges ==========
export const getCampaignPledges = (campaignId: number, params?: { status?: PledgeStatus }) =>
  api.get<TimePledge[]>(`/zamakana/campaigns/${campaignId}/pledges`, { params });

export const createPledge = (
  data: {
    campaign_id: number;
    pledged_hours: number;
    skill_category?: string;
  },
  idempotencyKey?: string
) =>
  api.post<TimePledge>('/zamakana/pledges', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const fulfillPledge = (
  pledgeId: number,
  data: { proof_hash: string },
  idempotencyKey?: string
) =>
  api.post<TimePledge>(`/zamakana/pledges/${pledgeId}/fulfill`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Scenarios ==========
export const getScenarios = (params?: { status?: ScenarioStatus; skip?: number; limit?: number }) =>
  api.get<FutureScenario[]>('/zamakana/scenarios', { params });

export const getScenario = (id: number) => api.get<FutureScenario>(`/zamakana/scenarios/${id}`);

export const createScenario = (data: {
  scenario_title: string;
  description: string;
  target_year: number;
  assumptions?: Record<string, any>;
}) => api.post<FutureScenario>('/zamakana/scenarios', data);

export const analyzeScenario = (scenarioId: number, idempotencyKey?: string) =>
  api.post<FutureScenario>(
    `/zamakana/scenarios/${scenarioId}/analyze`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const addFeedback = (data: {
  scenario_id: number;
  feedback_text: string;
  agreement_score?: number;
}) => api.post<HumanFeedback>('/zamakana/scenarios/feedback', data);

export const confirmScenario = (scenarioId: number) =>
  api.post<FutureScenario>(`/zamakana/scenarios/${scenarioId}/confirm`);