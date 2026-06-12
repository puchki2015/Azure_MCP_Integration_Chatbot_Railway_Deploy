import { request } from "../../services/api";
import type {
  ChatMessage,
  ChatResponse,
  ChatSession,
  CreateSessionResponse,
  SessionSummary
} from "./chat.types";

export function createChatSession() {
  return request<CreateSessionResponse>("/chat/session", { method: "POST", body: "{}" });
}

export function listChatSessions() {
  return request<ChatSession[]>("/chat/sessions");
}

export function listChatHistory(sessionId: number) {
  return request<ChatMessage[]>(`/chat/history/${sessionId}`);
}

export function sendChatMessage(sessionId: number, message: string) {
  return request<ChatResponse>("/chat/message", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message })
  });
}

export function getChatSessionSummary(sessionId: number) {
  return request<SessionSummary | null>(`/chat/summaries/${sessionId}`);
}

export function getLatestChatSessionSummary() {
  return request<SessionSummary | null>("/chat/summaries/latest");
}
