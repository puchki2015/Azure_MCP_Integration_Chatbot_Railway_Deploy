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

export type PricingLookupKey = {
  id: number;
  service_name: string;
  arm_sku: string | null;
  meter_name: string | null;
  product_name: string | null;
  region: string | null;
  currency_code: string;
  unit_of_measure: string | null;
  tier: string | null;
  normalized_key: string;
  is_active: boolean;
  last_checked_at: string | null;
  last_refresh_at: string | null;
  last_snapshot_id: number | null;
};

export type PricingSnapshot = {
  id: number;
  lookup_key_id: number;
  source: string;
  source_item_id: string | null;
  sku_name: string | null;
  product_name: string | null;
  meter_name: string | null;
  region: string | null;
  currency_code: string;
  unit_of_measure: string | null;
  price_type: string | null;
  retail_price: number;
  unit_price: number;
  effective_start: string | null;
  effective_end: string | null;
  fetched_at: string;
  valid_from: string | null;
  valid_to: string | null;
  is_current: boolean;
  payload_hash: string;
  raw_payload: Record<string, unknown>;
  api_url: string;
  request_params: Record<string, unknown> | null;
};

export type VmPriceOverview = {
  lookup_key: PricingLookupKey;
  current_snapshot: PricingSnapshot | null;
  snapshot_count: number;
};

export type PriceCatalogItem = VmPriceOverview;

export type PriceCatalog = {
  items: PriceCatalogItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type PriceCatalogService = "Virtual Machines" | "Azure SQL Database" | "Azure Database for MySQL";

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
