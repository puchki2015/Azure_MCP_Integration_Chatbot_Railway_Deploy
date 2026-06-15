import hashlib
import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Callable

from sqlalchemy.orm import Session

from app.database.models import (
    CostEstimate,
    CostEstimateLine,
    PriceRefreshRun,
    PricingLookupKey,
    PricingSnapshot,
    utc_now
)


class PriceCacheService:

    DEFAULT_TTL_HOURS = 24

    def _normalize_value(self, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, str):
            return value.strip().lower()

        return value

    def build_normalized_key(self, spec: dict[str, Any]) -> str:
        canonical_spec = {
            "service_name": self._normalize_value(spec.get("service_name")),
            "arm_sku": self._normalize_value(spec.get("arm_sku")),
            "meter_name": self._normalize_value(spec.get("meter_name")),
            "product_name": self._normalize_value(spec.get("product_name")),
            "region": self._normalize_value(spec.get("region")),
            "currency_code": self._normalize_value(spec.get("currency_code") or "usd"),
            "unit_of_measure": self._normalize_value(spec.get("unit_of_measure")),
            "tier": self._normalize_value(spec.get("tier"))
        }

        payload = json.dumps(
            canonical_spec,
            sort_keys=True,
            separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_or_create_lookup_key(
        self,
        db: Session,
        spec: dict[str, Any]
    ) -> PricingLookupKey:
        normalized_key = self.build_normalized_key(spec)
        lookup_key = (
            db.query(PricingLookupKey)
            .filter(PricingLookupKey.normalized_key == normalized_key)
            .first()
        )

        if lookup_key:
            lookup_key.last_checked_at = utc_now()
            db.commit()
            db.refresh(lookup_key)
            return lookup_key

        lookup_key = PricingLookupKey(
            service_name=spec.get("service_name", "").strip(),
            arm_sku=spec.get("arm_sku"),
            meter_name=spec.get("meter_name"),
            product_name=spec.get("product_name"),
            region=spec.get("region"),
            currency_code=(spec.get("currency_code") or "USD").upper(),
            unit_of_measure=spec.get("unit_of_measure"),
            tier=spec.get("tier"),
            normalized_key=normalized_key,
            last_checked_at=utc_now()
        )
        db.add(lookup_key)
        db.commit()
        db.refresh(lookup_key)
        return lookup_key

    def get_current_snapshot(
        self,
        db: Session,
        lookup_key_id: int
    ) -> PricingSnapshot | None:
        return (
            db.query(PricingSnapshot)
            .filter(
                PricingSnapshot.lookup_key_id == lookup_key_id,
                PricingSnapshot.is_current.is_(True)
            )
            .order_by(PricingSnapshot.fetched_at.desc())
            .first()
        )

    def should_refresh(
        self,
        lookup_key: PricingLookupKey,
        ttl_hours: int | None = None
    ) -> bool:
        ttl = ttl_hours or self.DEFAULT_TTL_HOURS
        if lookup_key.last_refresh_at is None:
            return True

        return lookup_key.last_refresh_at <= datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=ttl)

    def start_refresh_run(
        self,
        db: Session,
        trigger_type: str,
        requested_by: str | None = None,
        refresh_metadata: dict[str, Any] | None = None
    ) -> PriceRefreshRun:
        run = PriceRefreshRun(
            trigger_type=trigger_type,
            requested_by=requested_by,
            status="RUNNING",
            refresh_metadata=refresh_metadata or {}
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def finish_refresh_run(
        self,
        db: Session,
        run: PriceRefreshRun,
        status: str = "SUCCESS",
        error_summary: str | None = None
    ) -> PriceRefreshRun:
        run.status = status
        run.finished_at = utc_now()
        run.error_summary = error_summary
        db.commit()
        db.refresh(run)
        return run

    def store_snapshot(
        self,
        db: Session,
        lookup_key: PricingLookupKey,
        api_url: str,
        raw_payload: dict[str, Any],
        request_params: dict[str, Any] | None = None
    ) -> PricingSnapshot:
        payload_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        existing_snapshot = (
            db.query(PricingSnapshot)
            .filter(PricingSnapshot.payload_hash == payload_hash)
            .first()
        )
        if existing_snapshot:
            lookup_key.last_snapshot_id = existing_snapshot.id
            lookup_key.last_refresh_at = utc_now()
            lookup_key.last_checked_at = utc_now()
            db.commit()
            db.refresh(existing_snapshot)
            return existing_snapshot

        for snapshot in lookup_key.snapshots:
            snapshot.is_current = False

        snapshot = PricingSnapshot(
            lookup_key_id=lookup_key.id,
            source="azure_retail_prices_api",
            source_item_id=str(raw_payload.get("id") or raw_payload.get("skuId") or "") or None,
            sku_name=raw_payload.get("skuName"),
            product_name=raw_payload.get("productName"),
            meter_name=raw_payload.get("meterName"),
            region=raw_payload.get("armRegionName") or raw_payload.get("location"),
            currency_code=(raw_payload.get("currencyCode") or lookup_key.currency_code or "USD").upper(),
            unit_of_measure=raw_payload.get("unitOfMeasure"),
            price_type=raw_payload.get("type"),
            retail_price=raw_payload.get("retailPrice") or 0,
            unit_price=raw_payload.get("unitPrice") or raw_payload.get("retailPrice") or 0,
            effective_start=None,
            effective_end=None,
            fetched_at=utc_now(),
            valid_from=None,
            valid_to=None,
            is_current=True,
            payload_hash=payload_hash,
            raw_payload=raw_payload,
            api_url=api_url,
            request_params=request_params or {}
        )

        db.add(snapshot)
        db.flush()
        lookup_key.last_snapshot_id = snapshot.id
        lookup_key.last_refresh_at = utc_now()
        lookup_key.last_checked_at = utc_now()
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def create_estimate(
        self,
        db: Session,
        raw_input: str,
        normalized_request: dict[str, Any],
        user_id: int | None = None,
        source_session_id: int | None = None,
        region: str | None = None,
        currency_code: str = "USD",
        assumptions: dict[str, Any] | None = None,
        confidence: str | None = None
    ) -> CostEstimate:
        estimate = CostEstimate(
            user_id=user_id,
            source_session_id=source_session_id,
            raw_input=raw_input,
            normalized_request=normalized_request,
            region=region,
            currency_code=currency_code.upper(),
            assumptions=assumptions or {},
            confidence=confidence,
            status="PENDING"
        )
        db.add(estimate)
        db.commit()
        db.refresh(estimate)
        return estimate

    def add_estimate_line(
        self,
        db: Session,
        estimate_id: int,
        resource_type: str,
        quantity: float,
        unit_name: str,
        hourly_rate: float,
        monthly_rate: float,
        lookup_key_id: int | None = None,
        snapshot_id: int | None = None,
        resource_name: str | None = None,
        matched_exactly: bool = False,
        match_confidence: str | None = None,
        assumptions: dict[str, Any] | None = None
    ) -> CostEstimateLine:
        line = CostEstimateLine(
            estimate_id=estimate_id,
            lookup_key_id=lookup_key_id,
            snapshot_id=snapshot_id,
            resource_type=resource_type,
            resource_name=resource_name,
            quantity=quantity,
            unit_name=unit_name,
            hourly_rate=hourly_rate,
            monthly_rate=monthly_rate,
            matched_exactly=matched_exactly,
            match_confidence=match_confidence,
            assumptions=assumptions or {}
        )
        db.add(line)
        db.commit()
        db.refresh(line)
        return line

    def finalize_estimate(
        self,
        db: Session,
        estimate_id: int
    ) -> CostEstimate | None:
        estimate = (
            db.query(CostEstimate)
            .filter(CostEstimate.id == estimate_id)
            .first()
        )
        if not estimate:
            return None

        totals = (
            db.query(CostEstimateLine)
            .filter(CostEstimateLine.estimate_id == estimate_id)
            .all()
        )
        estimate.total_hourly = sum(float(line.hourly_rate) for line in totals)
        estimate.total_monthly = sum(float(line.monthly_rate) for line in totals)
        estimate.status = "COMPLETE"
        estimate.updated_at = utc_now()

        db.commit()
        db.refresh(estimate)
        return estimate

    def due_for_refresh(
        self,
        db: Session,
        ttl_hours: int | None = None
    ) -> list[PricingLookupKey]:
        ttl = ttl_hours or self.DEFAULT_TTL_HOURS
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=ttl)
        return (
            db.query(PricingLookupKey)
            .filter(
                PricingLookupKey.is_active.is_(True),
                (
                    (PricingLookupKey.last_refresh_at.is_(None))
                    | (PricingLookupKey.last_refresh_at <= cutoff)
                )
            )
            .all()
        )

    def refresh_lookup_key(
        self,
        db: Session,
        lookup_key: PricingLookupKey,
        api_url: str,
        raw_payload: dict[str, Any],
        request_params: dict[str, Any] | None = None
    ) -> PricingSnapshot:
        return self.store_snapshot(
            db=db,
            lookup_key=lookup_key,
            api_url=api_url,
            raw_payload=raw_payload,
            request_params=request_params
        )

    def refresh_due_lookup_keys(
        self,
        db: Session,
        trigger_type: str,
        fetch_candidates: Callable[[PricingLookupKey], tuple[list[dict[str, Any]], str, dict[str, Any] | None]],
        ttl_hours: int | None = None,
        requested_by: str | None = None
    ) -> PriceRefreshRun:
        run = self.start_refresh_run(
            db=db,
            trigger_type=trigger_type,
            requested_by=requested_by
        )

        try:
            keys = self.due_for_refresh(
                db=db,
                ttl_hours=ttl_hours
            )

            for lookup_key in keys:
                run.keys_processed += 1
                try:
                    candidates, api_url, request_params = fetch_candidates(lookup_key)
                    if not candidates:
                        lookup_key.last_checked_at = utc_now()
                        run.keys_unchanged += 1
                        continue

                    selected_candidate = candidates[0]
                    before_snapshot = self.get_current_snapshot(db, lookup_key.id)
                    after_snapshot = self.refresh_lookup_key(
                        db=db,
                        lookup_key=lookup_key,
                        api_url=api_url,
                        raw_payload=selected_candidate,
                        request_params=request_params
                    )

                    if before_snapshot and before_snapshot.payload_hash == after_snapshot.payload_hash:
                        run.keys_unchanged += 1
                    else:
                        run.keys_refreshed += 1
                except Exception as ex:
                    run.keys_failed += 1
                    run.error_summary = (
                        f"{run.error_summary}\n{lookup_key.normalized_key}: {ex}"
                        if run.error_summary
                        else f"{lookup_key.normalized_key}: {ex}"
                    )

            db.commit()
            return self.finish_refresh_run(
                db=db,
                run=run,
                status="SUCCESS" if run.keys_failed == 0 else "PARTIAL",
                error_summary=run.error_summary
            )
        except Exception as ex:
            return self.finish_refresh_run(
                db=db,
                run=run,
                status="FAILED",
                error_summary=str(ex)
            )


price_cache_service = PriceCacheService()
