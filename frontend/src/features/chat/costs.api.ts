import { request } from "../../services/api";
import type {
  CostAnalysis,
  CostEstimate,
  CostEstimateCreateRequest,
  CostResolutionRequest,
  CostResolutionResult
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
