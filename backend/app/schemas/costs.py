from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class CostEstimateLineInput(BaseModel):
    resource_type: str
    resource_name: str | None = None
    quantity: float
    unit_name: str
    hourly_rate: float
    monthly_rate: float
    lookup_key: dict[str, Any] | None = None
    matched_exactly: bool = False
    match_confidence: str | None = None
    assumptions: dict[str, Any] | None = None


class CostEstimateCreateRequest(BaseModel):
    raw_input: str
    normalized_request: dict[str, Any]
    region: str | None = None
    currency_code: str = "USD"
    assumptions: dict[str, Any] | None = None
    confidence: str | None = None
    source_session_id: int | None = None
    user_id: int | None = None
    lines: list[CostEstimateLineInput] = Field(default_factory=list)


class PricingSnapshotIngestRequest(BaseModel):
    lookup_key: dict[str, Any]
    api_url: str
    raw_payload: dict[str, Any]
    request_params: dict[str, Any] | None = None


class PriceRefreshRunCreateRequest(BaseModel):
    trigger_type: str = "manual"
    refresh_metadata: dict[str, Any] | None = None


class PricingLookupKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_name: str
    arm_sku: str | None = None
    meter_name: str | None = None
    product_name: str | None = None
    region: str | None = None
    currency_code: str
    unit_of_measure: str | None = None
    tier: str | None = None
    normalized_key: str
    is_active: bool
    last_checked_at: datetime | None = None
    last_refresh_at: datetime | None = None
    last_snapshot_id: int | None = None


class PricingSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lookup_key_id: int
    source: str
    source_item_id: str | None = None
    sku_name: str | None = None
    product_name: str | None = None
    meter_name: str | None = None
    region: str | None = None
    currency_code: str
    unit_of_measure: str | None = None
    price_type: str | None = None
    retail_price: float
    unit_price: float
    effective_start: datetime | None = None
    effective_end: datetime | None = None
    fetched_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_current: bool
    payload_hash: str
    raw_payload: dict[str, Any]
    api_url: str
    request_params: dict[str, Any] | None = None


class CostEstimateLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estimate_id: int
    lookup_key_id: int | None = None
    snapshot_id: int | None = None
    resource_type: str
    resource_name: str | None = None
    quantity: float
    unit_name: str
    hourly_rate: float
    monthly_rate: float
    matched_exactly: bool
    match_confidence: str | None = None
    assumptions: dict[str, Any] | None = None
    created_at: datetime


class CostEstimateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    source_session_id: int | None = None
    raw_input: str
    normalized_request: dict[str, Any]
    region: str | None = None
    currency_code: str
    status: str
    created_at: datetime
    updated_at: datetime
    total_hourly: float | None = None
    total_monthly: float | None = None
    assumptions: dict[str, Any] | None = None
    confidence: str | None = None
    lines: list[CostEstimateLineResponse] = Field(default_factory=list)


class PriceRefreshRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    trigger_type: str
    requested_by: str | None = None
    keys_processed: int
    keys_refreshed: int
    keys_unchanged: int
    keys_failed: int
    error_summary: str | None = None
    refresh_metadata: dict[str, Any] | None = None
