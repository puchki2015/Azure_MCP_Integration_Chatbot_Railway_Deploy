from datetime import UTC
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
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


class PricingLookupKey(Base):

    __tablename__ = "pricing_lookup_keys"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    arm_sku: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    meter_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    product_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    region: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    currency_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="USD"
    )

    unit_of_measure: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    tier: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    normalized_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    last_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    last_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("pricing_snapshots.id"),
        nullable=True
    )

    snapshots = relationship(
        "PricingSnapshot",
        back_populates="lookup_key",
        foreign_keys="PricingSnapshot.lookup_key_id",
        cascade="all, delete-orphan"
    )

    current_snapshot = relationship(
        "PricingSnapshot",
        foreign_keys=[last_snapshot_id],
        post_update=True
    )


class PricingSnapshot(Base):

    __tablename__ = "pricing_snapshots"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    lookup_key_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_lookup_keys.id"),
        nullable=False,
        index=True
    )

    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="azure_retail_prices_api"
    )

    source_item_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    sku_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    product_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    meter_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    region: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    currency_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False
    )

    unit_of_measure: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    price_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    retail_price: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False
    )

    unit_price: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False
    )

    effective_start: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    effective_end: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    payload_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True
    )

    raw_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    api_url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    request_params: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    lookup_key = relationship(
        "PricingLookupKey",
        back_populates="snapshots",
        foreign_keys=[lookup_key_id]
    )


class PriceRefreshRun(Base):

    __tablename__ = "price_refresh_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="RUNNING"
    )

    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    requested_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    keys_processed: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    keys_refreshed: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    keys_unchanged: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    keys_failed: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    refresh_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )


class CostEstimate(Base):

    __tablename__ = "cost_estimates"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    source_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=True,
        index=True
    )

    raw_input: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    normalized_request: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    region: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    currency_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="USD"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    total_hourly: Mapped[float | None] = mapped_column(
        Numeric(18, 6),
        nullable=True
    )

    total_monthly: Mapped[float | None] = mapped_column(
        Numeric(18, 2),
        nullable=True
    )

    assumptions: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    confidence: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    lines = relationship(
        "CostEstimateLine",
        back_populates="estimate",
        cascade="all, delete-orphan"
    )


class CostEstimateLine(Base):

    __tablename__ = "cost_estimate_lines"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    estimate_id: Mapped[int] = mapped_column(
        ForeignKey("cost_estimates.id"),
        nullable=False,
        index=True
    )

    lookup_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("pricing_lookup_keys.id"),
        nullable=True,
        index=True
    )

    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("pricing_snapshots.id"),
        nullable=True,
        index=True
    )

    resource_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    resource_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False
    )

    unit_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    hourly_rate: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False
    )

    monthly_rate: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    matched_exactly: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    match_confidence: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    assumptions: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    estimate = relationship(
        "CostEstimate",
        back_populates="lines"
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

Index(
    "idx_pricing_lookup_keys_currency_region",
    PricingLookupKey.currency_code,
    PricingLookupKey.region
)

Index(
    "idx_pricing_snapshots_lookup_current",
    PricingSnapshot.lookup_key_id,
    PricingSnapshot.is_current
)

Index(
    "idx_price_refresh_runs_started_at",
    PriceRefreshRun.started_at
)

Index(
    "idx_cost_estimates_created_at",
    CostEstimate.created_at
)

Index(
    "idx_cost_estimate_lines_estimate_id",
    CostEstimateLine.estimate_id
)

