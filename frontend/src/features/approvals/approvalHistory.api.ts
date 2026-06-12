import { request } from "../../services/api";

export type ApprovalActionLogItem = {
  id: number;
  approval_id: number;
  session_id: number | null;
  admin_email: string;
  action: string;
  status: string;
  tool_name: string | null;
  reason: string | null;
  payload: Record<string, unknown> | null;
  result_text: string | null;
  error_message: string | null;
  created_at: string;
};

export function listApprovalActionHistory(scope: "mine" | "all" = "all", limit = 10) {
  return request<ApprovalActionLogItem[]>(`/approvals/action-history?scope=${scope}&limit=${limit}`);
}
