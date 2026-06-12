from datetime import UTC
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)



class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    entra_oid: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    display_name: Mapped[str] = mapped_column(
        String(255)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )

    sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    approvals = relationship(
        "ApprovalRequest",
        back_populates="user"
    )


class ChatSession(Base):

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )

    user = relationship(
        "User",
        back_populates="sessions"
    )

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id")
    )

    role: Mapped[str] = mapped_column(
        String(20)
    )

    content: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )


class SessionMemory(Base):

    __tablename__ = "session_memory"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=False,
        unique=True,
        index=True
    )

    source_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=True
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )


class ApprovalRequest(Base):

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    tool_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING"
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="approvals"
    )

    session = relationship(
        "ChatSession"
    )


class ApprovalActionLog(Base):

    __tablename__ = "approval_action_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    approval_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id"),
        nullable=False,
        index=True
    )

    admin_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    result_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )

class AuditLog(Base):

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    action: Mapped[str] = mapped_column(
        Text
    )

    result: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now
    )


Index(
    "idx_chat_messages_session",
    ChatMessage.session_id
)

Index(
    "idx_audit_logs_user",
    AuditLog.user_id
)

Index(
    "idx_approval_session",
    ApprovalRequest.session_id
)            

