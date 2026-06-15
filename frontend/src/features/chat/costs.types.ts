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

export type CostResourceIntent = {
  resource_type: string;
  quantity: number | null;
  region: string | null;
  sku: string | null;
  os_image: string | null;
  unit_name: string | null;
  confidence: string;
};

export type CostClarificationItem = {
  field_name: string;
  message: string;
  suggested_values: string[];
};

export type CostAnalysis = {
  raw_input: string;
  normalized_text: string;
  intents: CostResourceIntent[];
  needs_confirmation: boolean;
  clarification_items: CostClarificationItem[];
  assumptions: string[];
  ready_to_price: boolean;
};

export type CostResolutionRequest = {
  raw_input: string;
  selections?: Record<string, string>;
  source_session_id?: number;
};

export type CostResolutionResult =
  | {
      kind: "analysis";
      analysis: CostAnalysis;
    }
  | {
      kind: "estimate";
      estimate: CostEstimate;
    };

export type PriceRefreshRun = {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  trigger_type: string;
  requested_by: string | null;
  keys_processed: number;
  keys_refreshed: number;
  keys_unchanged: number;
  keys_failed: number;
  error_summary: string | null;
  refresh_metadata: Record<string, unknown> | null;
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
