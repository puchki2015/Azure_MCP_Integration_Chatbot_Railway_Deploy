import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Spinner } from "../../components/ui/Spinner";
import { VoiceInputButton } from "../../components/voice/VoiceInputButton";
import { useVoiceInput } from "../../components/voice/useVoiceInput";
import { formatDate } from "../../utils/formatDate";
import {
  createChatSession,
  getChatSessionSummary,
  listChatHistory,
  listChatSessions,
  sendChatMessage
} from "./chat.api";
import type { ChatMessage, ChatSession, SessionSummary } from "./chat.types";

export function ChatPage() {
  const navigate = useNavigate();
  const params = useParams();
  const parsedSessionId = params.sessionId ? Number(params.sessionId) : null;
  const initialSessionId = parsedSessionId && Number.isFinite(parsedSessionId) ? parsedSessionId : null;
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(initialSessionId);
  const [message, setMessage] = useState("");
  const [sessionSummary, setSessionSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const voiceInput = useVoiceInput((transcript) => {
    setMessage((current) => {
      const next = [current.trim(), transcript.trim()].filter(Boolean).join(" ");
      return next;
    });
  });

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [sessions, activeSessionId]
  );

  const refreshSessions = async () => {
    const data = await listChatSessions();
    setSessions(data);
    return data;
  };

  const refreshMessages = async (sessionId: number) => {
    const data = await listChatHistory(sessionId);
    setMessages(data);
  };

  const refreshSessionSummary = async (sessionId: number) => {
    try {
      const summary = await getChatSessionSummary(sessionId);
      setSessionSummary(summary);
    } catch {
      setSessionSummary(null);
    }
  };

  useEffect(() => {
    let mounted = true;

    const bootstrap = async () => {
      try {
        setLoading(true);
        const sessionList = await refreshSessions();
        let sessionId = activeSessionId;
        let createdNewSession = false;

        if (!sessionId) {
          const created = await createChatSession();
          createdNewSession = true;
          sessionId = created.session_id;
          navigate(`/chat/${sessionId}`, { replace: true });
          await refreshSessions();
          if (created.previous_session_summary) {
            setSessionSummary({
              session_id: created.previous_session_id ?? sessionId,
              source_session_id: created.previous_session_id,
              summary: created.previous_session_summary,
              created_at: created.previous_session_summary_created_at ?? new Date().toISOString()
            });
          } else {
            setSessionSummary(null);
          }
        } else if (!sessionList.some((session) => session.id === sessionId)) {
          sessionId = sessionList[0]?.id ?? null;
          if (sessionId) {
            navigate(`/chat/${sessionId}`, { replace: true });
          }
        }

        if (sessionId) {
          setActiveSessionId(sessionId);
          await refreshMessages(sessionId);
          if (!createdNewSession) {
            await refreshSessionSummary(sessionId);
          }
        } else {
          setMessages([]);
          setSessionSummary(null);
        }
      } catch (ex) {
        setError(ex instanceof Error ? ex.message : "Failed to load chat");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSessionSelect = async (sessionId: number) => {
    setActiveSessionId(sessionId);
    navigate(`/chat/${sessionId}`);
    await refreshMessages(sessionId);
    await refreshSessionSummary(sessionId);
  };

  const handleSend = async () => {
    if (!activeSessionId || !message.trim()) {
      return;
    }

    const userMessage = message.trim();
    setMessage("");
    setSending(true);
    setError(null);

    try {
      await sendChatMessage(activeSessionId, userMessage);
      await refreshSessions();
      await refreshMessages(activeSessionId);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="screen-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="chat-layout">
      <section className="chat-panel">
        <header className="chat-panel__header">
          <div>
            <div className="eyebrow">Session {activeSession?.id ?? "New"}</div>
            <h1>Chat with Azure AI Ops</h1>
          </div>
          {error ? <div className="error-banner">{error}</div> : null}
        </header>

        <div className="chat-panel__body">
          <Card className="approvals-summary-card">
            <div className="eyebrow">My approvals</div>
            <p className="approvals-summary-card__text">
              Track your own pending, approved, and rejected requests from here.
            </p>
            <div className="approvals-summary-card__links">
              <Link to="/approvals/pending">Pending</Link>
              <Link to="/approvals/approved">Approved</Link>
              <Link to="/approvals/rejected">Rejected</Link>
            </div>
          </Card>

          {sessionSummary ? (
            <Card className="session-summary-card">
              <div className="eyebrow">Previous session summary</div>
              <p className="session-summary-card__text">{sessionSummary.summary}</p>
              <small className="session-summary-card__meta">
                Stored {formatDate(sessionSummary.created_at)}
                {sessionSummary.source_session_id ? ` · from session ${sessionSummary.source_session_id}` : ""}
              </small>
            </Card>
          ) : null}

          {messages.length === 0 ? (
            <EmptyState
              title="No messages yet"
              description="Start a conversation by asking for an Azure resource action."
            />
          ) : (
            <div className="message-list">
              {messages.map((item, index) => (
                <div key={`${item.created_at}-${index}`} className={["message", `message--${item.role}`].join(" ")}>
                  <div className="message__bubble">{item.content}</div>
                  <div className="message__meta">{formatDate(item.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="chat-panel__composer">
          <div className="chat-panel__composerMain">
            <Input
              value={message}
              placeholder={voiceInput.listening ? "Listening for speech..." : "Ask for an Azure operation..."}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  void handleSend();
                }
              }}
            />
            {voiceInput.error ? <small className="approval-error-text">{voiceInput.error}</small> : null}
          </div>
          <div className="chat-panel__composerActions">
            <VoiceInputButton
              listening={voiceInput.listening}
              onClick={() => void voiceInput.start()}
              disabled={sending || voiceInput.listening}
            />
            <Button onClick={() => void handleSend()} disabled={sending}>
              {sending ? "Sending..." : "Send"}
            </Button>
          </div>
        </footer>
      </section>

      <aside className="chat-sidebar">
        <Card>
          <h2>Chat history</h2>
          <div className="session-list">
            {sessions.map((session) => (
              <button
                key={session.id}
                className={["session-item", session.id === activeSessionId ? "session-item--active" : ""].join(" ")}
                onClick={() => void handleSessionSelect(session.id)}
              >
                <strong>Session {session.id}</strong>
                <span>{session.message_count} messages</span>
                <small>{formatDate(session.created_at)}</small>
              </button>
            ))}
          </div>
        </Card>
      </aside>
    </div>
  );
}
