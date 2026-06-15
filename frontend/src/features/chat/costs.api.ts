import { request } from "../../services/api";
import type { CostEstimate, CostEstimateCreateRequest } from "./costs.types";

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
