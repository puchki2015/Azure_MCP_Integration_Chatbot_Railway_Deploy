export type ChatSession = {
  id: number;
  status: string;
  created_at: string;
  message_count: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type ChatResponse = {
  session_id: number;
  response: string;
  requires_approval: boolean;
  approval_id: number | null;
  approval_user_email: string | null;
};

export type SessionSummary = {
  session_id: number;
  source_session_id: number | null;
  summary: string;
  created_at: string;
};

export type CreateSessionResponse = {
  session_id: number;
  previous_session_summary: string | null;
  previous_session_summary_created_at: string | null;
  previous_session_id: number | null;
};
