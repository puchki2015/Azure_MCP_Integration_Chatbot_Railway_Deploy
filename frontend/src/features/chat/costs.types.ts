export type CostEstimateLineInput = {
  resource_type: string;
  resource_name: string;
  quantity: number;
  unit_name: string;
  hourly_rate: number;
  monthly_rate: number;
  lookup_key?: {
    service_name: string;
    arm_sku?: string;
    meter_name?: string;
    product_name?: string;
    region?: string;
    currency_code?: string;
    unit_of_measure?: string;
    tier?: string;
  };
  matched_exactly?: boolean;
  match_confidence?: string;
  assumptions?: Record<string, unknown>;
};

export type CostEstimateCreateRequest = {
  raw_input: string;
  normalized_request: Record<string, unknown>;
  region?: string;
  currency_code: string;
  assumptions?: Record<string, unknown>;
  confidence?: string;
  source_session_id?: number;
  user_id?: number;
  lines: CostEstimateLineInput[];
};

export type CostEstimateLine = {
  id: number;
  estimate_id: number;
  lookup_key_id: number | null;
  snapshot_id: number | null;
  resource_type: string;
  resource_name: string | null;
  quantity: number;
  unit_name: string;
  hourly_rate: number;
  monthly_rate: number;
  matched_exactly: boolean;
  match_confidence: string | null;
  assumptions: Record<string, unknown> | null;
  created_at: string;
};

export type CostEstimate = {
  id: number;
  user_id: number | null;
  source_session_id: number | null;
  raw_input: string;
  normalized_request: Record<string, unknown>;
  region: string | null;
  currency_code: string;
  status: string;
  created_at: string;
  updated_at: string;
  total_hourly: number | null;
  total_monthly: number | null;
  assumptions: Record<string, unknown> | null;
  confidence: string | null;
  lines: CostEstimateLine[];
};

export type CostEstimateListItem = CostEstimate;
