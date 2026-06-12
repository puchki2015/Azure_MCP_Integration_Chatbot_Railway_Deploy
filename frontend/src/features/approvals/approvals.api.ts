import { request } from "../../services/api";
import type { ApprovalActionResponse } from "./approvals.types";
import type { ApprovalItem } from "./approvals.types";

export function listApprovals(
  status: "PENDING" | "APPROVED" | "REJECTED" | "FAILED",
  scope: "mine" | "all" = "all"
) {
  return request<ApprovalItem[]>(`/approvals?status=${status}&scope=${scope}`);
}

export function approveApproval(approvalId: number, reason: string) {
  return request<ApprovalActionResponse>(`/approvals/${approvalId}/approve`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export function rejectApproval(approvalId: number, reason: string) {
  return request<ApprovalActionResponse>(`/approvals/${approvalId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}
