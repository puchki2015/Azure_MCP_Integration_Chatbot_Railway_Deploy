from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CreateSessionResponse(BaseModel):
    session_id: int
    previous_session_summary: Optional[str] = None
    previous_session_summary_created_at: Optional[datetime] = None
    previous_session_id: Optional[int] = None


class ChatSessionSummary(BaseModel):
    id: int
    status: str
    created_at: datetime
    message_count: int = 0


class ChatRequest(BaseModel):
    session_id: int
    message: str


class ChatResponse(BaseModel):
    session_id: int
    response: str
    requires_approval: bool = False
    approval_id: Optional[int] = None
    approval_user_email: Optional[str] = None


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionSummaryResponse(BaseModel):
    session_id: int
    source_session_id: Optional[int] = None
    summary: str
    created_at: datetime
