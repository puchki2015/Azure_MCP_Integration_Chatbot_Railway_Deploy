import { request } from "../../services/api";
import type {
  CostAnalysis,
  CostEstimate,
  CostEstimateCreateRequest,
  CostResolutionRequest,
  CostResolutionResult,
  PriceRefreshRun,
  VmPriceCatalog
} from "./costs.types";

export function analyzeCostRequest(payload: { raw_input: string }) {
  return request<CostAnalysis>("/costs/analyze", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resolveCostRequest(payload: CostResolutionRequest) {
  return request<CostResolutionResult>("/costs/resolve", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createCostEstimate(payload: CostEstimateCreateRequest) {
  return request<CostEstimate>("/costs/estimates", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listCostEstimates() {
  return request<CostEstimate[]>("/costs/estimates");
}

export function getCostEstimate(estimateId: number) {
  return request<CostEstimate>(`/costs/estimates/${estimateId}`);
}

export function refreshVmPrices() {
  return request<PriceRefreshRun>("/costs/refresh-vms", {
    method: "POST"
  });
}

export function listVmPrices(page = 1, pageSize = 10) {
  return request<VmPriceCatalog>(`/costs/vm-prices?page=${page}&page_size=${pageSize}`);
}
