from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    id: int
    user_id: int | None
    user_email: str | None
    session_id: int
    action: str
    tool_name: str | None
    payload: dict[str, Any]
    status: str
    approved: bool
    approved_by: str | None
    decision_reason: str | None
    created_at: datetime
    approved_at: datetime | None
    executed_at: datetime | None
    error_message: str | None


class ApprovalDecisionRequest(BaseModel):
    reason: str


class ApprovalActionResponse(BaseModel):
    approval_id: int
    status: str
    message: str
    reason: str | None = None
    result: Any | None = None
    error_message: str | None = None
    user_email: str | None = None
