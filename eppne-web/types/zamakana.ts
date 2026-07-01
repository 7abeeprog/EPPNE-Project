// types/zamakana.ts
export type ZamakanaNodeType = 'ERA' | 'INNOVATION' | 'PERSON' | 'EVENT';
export type ScenarioStatus = 'DRAFTING' | 'HUMAN_REVIEW' | 'CONFIRMED';
export type PledgeStatus = 'PENDING' | 'FULFILLED' | 'CANCELLED';

export interface ZamakanaNode {
  id: number;
  tenant_id: number;
  node_type: ZamakanaNodeType;
  title: string;
  description: string;
  timeline_year?: number;
  geo_location?: string;
  verified_sources: string[];
  extra_data: Record<string, any>;
  created_by: number;
  created_at: string;
  updated_at: string;
  outgoing_edges?: ZamakanaEdge[];
  incoming_edges?: ZamakanaEdge[];
}

export interface ZamakanaEdge {
  id: number;
  tenant_id: number;
  source_node_id: number;
  target_node_id: number;
  impact_description: string;
  impact_weight: number;
  is_alternative_timeline: boolean;
  created_by: number;
  created_at: string;
  source_node?: ZamakanaNode;
  target_node?: ZamakanaNode;
}

export interface PlanetaryCampaign {
  id: number;
  tenant_id: number;
  created_by: number;
  title: string;
  description: string;
  target_time_hours: number;
  collected_time_hours: number;
  start_date: string;
  end_date: string;
  status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  campaign_contract_address?: string;
  created_at: string;
  updated_at: string;
  pledges?: TimePledge[];
}

export interface TimePledge {
  id: number;
  tenant_id: number;
  campaign_id: number;
  user_id: number;
  user_name?: string;
  pledged_hours: number;
  skill_category?: string;
  status: PledgeStatus;
  proof_hash?: string;
  verified_by?: number;
  verified_at?: string;
  created_at: string;
  updated_at: string;
}

export interface FutureScenario {
  id: number;
  tenant_id: number;
  created_by: number;
  creator_name?: string;
  scenario_title: string;
  description: string;
  target_year: number;
  assumptions: Record<string, any>;
  ai_analysis_report?: Record<string, any>;
  ai_agent_id?: number;
  status: ScenarioStatus;
  created_at: string;
  updated_at: string;
  feedbacks?: HumanFeedback[];
}

export interface HumanFeedback {
  id: number;
  tenant_id: number;
  scenario_id: number;
  reviewer_id: number;
  reviewer_name?: string;
  feedback_text: string;
  agreement_score?: number;
  created_at: string;
}

export interface GraphData {
  nodes: Array<{
    id: number;
    type: ZamakanaNodeType;
    title: string;
    year?: number;
    location?: string;
  }>;
  edges: Array<{
    source: number;
    target: number;
    weight: number;
    alternative: boolean;
    description: string;
  }>;
}

// ========== UI Types ==========
export interface ZamakanaStats {
  total_nodes: number;
  total_edges: number;
  total_campaigns: number;
  total_pledged_hours: number;
  total_scenarios: number;
}