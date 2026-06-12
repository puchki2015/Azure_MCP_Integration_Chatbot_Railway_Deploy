export type ApprovalItem = {
  id: number;
  user_id: number | null;
  user_email: string | null;
  session_id: number;
  action: string;
  tool_name: string | null;
  payload: Record<string, unknown>;
  status: string;
  approved: boolean;
  approved_by: string | null;
  decision_reason: string | null;
  created_at: string;
  approved_at: string | null;
  executed_at: string | null;
  error_message: string | null;
};

export type ApprovalActionResponse = {
  approval_id: number;
  status: string;
  message: string;
  reason?: string | null;
  result?: unknown;
  error_message?: string | null;
  user_email?: string | null;
};
