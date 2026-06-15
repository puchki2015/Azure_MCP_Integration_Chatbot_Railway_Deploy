from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models import CostEstimate
from app.database.models import CostEstimateLine
from app.database.models import PricingLookupKey
from app.database.models import PricingSnapshot
from app.schemas.costs import CostAnalysisResponse
from app.schemas.costs import CostEstimateLineResponse
from app.schemas.costs import CostEstimateResponse
from app.schemas.costs import CostResourceIntent
from app.services.azure_retail_prices_service import RetailPriceQuery
from app.services.azure_retail_prices_service import azure_retail_prices_service
from app.services.price_cache_service import price_cache_service


@dataclass(frozen=True)
class ResolvedPricingLine:
    intent: CostResourceIntent
    lookup_spec: dict[str, Any]
    query: RetailPriceQuery
    resource_name: str
    matched_exactly: bool
    match_confidence: str
    assumptions: dict[str, Any]


class CostPricingService:

    HOURS_PER_MONTH = 730

    def _canonical_vm_sku(self, sku: str | None) -> str | None:
        if not sku:
            return None

        value = sku.strip()
        if value.lower().startswith("standard_"):
            return value
        if value.lower().startswith(("b", "d", "e", "f", "g", "m", "l")):
            return f"Standard_{value}"
        return value

    def _canonical_vm_meter(self, sku: str | None) -> str | None:
        if not sku:
            return None
        value = sku.strip()
        if value.lower().startswith("standard_"):
            return value.split("_", 1)[1]
        return value

    def _first_selection(self, selections: dict[str, str], *field_names: str) -> str | None:
        for field_name in field_names:
            value = selections.get(field_name)
            if value:
                return value
        return None

    def _resolve_vm(self, intent: CostResourceIntent, selections: dict[str, str]) -> ResolvedPricingLine:
        sku = self._first_selection(selections, "vm_size", "sku", "vm_sku") or intent.sku
        region = self._first_selection(selections, "region") or intent.region
        os_image = self._first_selection(selections, "os_image") or intent.os_image

        if not sku:
            raise HTTPException(
                status_code=422,
                detail="VM size is required before pricing can continue."
            )
        if not region:
            raise HTTPException(
                status_code=422,
                detail="VM region is required before pricing can continue."
            )

        canonical_sku = self._canonical_vm_sku(sku)
        meter_name = self._canonical_vm_meter(canonical_sku)
        lookup_spec = {
            "service_name": "Virtual Machines",
            "arm_sku": canonical_sku,
            "meter_name": meter_name,
            "product_name": "Virtual Machines",
            "region": region,
            "currency_code": "USD",
            "unit_of_measure": "1 Hour"
        }
        query = RetailPriceQuery(
            service_name="Virtual Machines",
            arm_region_name=region,
            arm_sku_name=canonical_sku,
            sku_name=canonical_sku,
            product_name="Virtual Machines",
            meter_name=meter_name,
            price_type="Consumption",
            currency_code="USD"
        )
        return ResolvedPricingLine(
            intent=intent,
            lookup_spec=lookup_spec,
            query=query,
            resource_name=canonical_sku,
            matched_exactly=True,
            match_confidence="confirmed",
            assumptions={
                "os_image": os_image,
                "resolution_source": "confirmed_selection" if selections else "parsed_intent"
            }
        )

    def _resolve_sql(self, intent: CostResourceIntent, selections: dict[str, str]) -> ResolvedPricingLine:
        region = self._first_selection(selections, "region") or intent.region
        tier = self._first_selection(selections, "sql_tier", "tier") or intent.sku

        if not region:
            raise HTTPException(
                status_code=422,
                detail="SQL region is required before pricing can continue."
            )

        if not tier:
            raise HTTPException(
                status_code=422,
                detail="SQL tier is required before pricing can continue."
            )

        lookup_spec = {
            "service_name": "Azure SQL Database",
            "product_name": "Azure SQL Database",
            "meter_name": tier,
            "region": region,
            "currency_code": "USD",
            "unit_of_measure": "1 vCore Hour",
            "tier": tier
        }
        query = RetailPriceQuery(
            service_name="Azure SQL Database",
            arm_region_name=region,
            product_name="Azure SQL Database",
            meter_name=tier,
            price_type="Consumption",
            currency_code="USD"
        )
        return ResolvedPricingLine(
            intent=intent,
            lookup_spec=lookup_spec,
            query=query,
            resource_name=tier,
            matched_exactly=False,
            match_confidence="confirmed" if selections else "parsed_intent",
            assumptions={
                "tier": tier,
                "resolution_source": "confirmed_selection" if selections else "parsed_intent"
            }
        )

    def _resolve_intent(
        self,
        intent: CostResourceIntent,
        selections: dict[str, str]
    ) -> ResolvedPricingLine:
        resource_type = intent.resource_type.lower()
        if "virtual machine" in resource_type:
            return self._resolve_vm(intent, selections)
        if "sql" in resource_type:
            return self._resolve_sql(intent, selections)

        raise HTTPException(
            status_code=422,
            detail=f"Unsupported resource type: {intent.resource_type}"
        )

    def _price_line(
        self,
        db: Session,
        estimate_id: int,
        resolved: ResolvedPricingLine
    ) -> CostEstimateLine:
        quantity = float(resolved.intent.quantity or 1)
        lookup = price_cache_service.get_or_create_lookup_key(
            db=db,
            spec=resolved.lookup_spec
        )

        snapshot = price_cache_service.get_current_snapshot(
            db=db,
            lookup_key_id=lookup.id
        )

        if snapshot is None or price_cache_service.should_refresh(lookup):
            best_item, items, api_url, request_params = azure_retail_prices_service.fetch_best_item(
                resolved.query
            )
            if best_item is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": f"Unable to find a live Azure price for {resolved.intent.resource_type}",
                        "resource_type": resolved.intent.resource_type,
                        "lookup_spec": resolved.lookup_spec,
                        "candidate_count": len(items)
                    }
                )
            snapshot = price_cache_service.refresh_lookup_key(
                db=db,
                lookup_key=lookup,
                api_url=api_url,
                raw_payload=best_item,
                request_params=request_params
            )

        unit_price = float(snapshot.unit_price or snapshot.retail_price or 0)
        hourly_rate = quantity * unit_price
        monthly_rate = hourly_rate * self.HOURS_PER_MONTH

        return price_cache_service.add_estimate_line(
            db=db,
            estimate_id=estimate_id,
            lookup_key_id=lookup.id,
            snapshot_id=snapshot.id,
            resource_type=resolved.intent.resource_type,
            resource_name=resolved.resource_name,
            quantity=quantity,
            unit_name=resolved.intent.unit_name or "hour",
            hourly_rate=hourly_rate,
            monthly_rate=monthly_rate,
            matched_exactly=resolved.matched_exactly,
            match_confidence=resolved.match_confidence,
            assumptions={
                **resolved.assumptions,
                "lookup_key": resolved.lookup_spec,
                "unit_price": unit_price,
                "quantity": quantity
            }
        )

    def create_estimate_from_analysis(
        self,
        db: Session,
        raw_input: str,
        analysis: CostAnalysisResponse,
        selections: dict[str, str] | None = None,
        user_id: int | None = None,
        source_session_id: int | None = None
    ) -> tuple[CostAnalysisResponse, CostEstimateResponse | None]:
        selections = selections or {}

        if analysis.needs_confirmation and not selections:
            return analysis, None

        if not analysis.intents:
            raise HTTPException(
                status_code=422,
                detail="No priced resources were found in the request."
            )

        estimate = price_cache_service.create_estimate(
            db=db,
            raw_input=raw_input,
            normalized_request={
                "normalized_text": analysis.normalized_text,
                "intents": [intent.model_dump() for intent in analysis.intents],
                "selections": selections
            },
            user_id=user_id,
            source_session_id=source_session_id,
            region=next((intent.region for intent in analysis.intents if intent.region), None),
            currency_code="USD",
            assumptions={
                "analysis_assumptions": analysis.assumptions,
                "clarification_selections": selections
            },
            confidence="confirmed" if selections else "auto"
        )

        stored_lines: list[CostEstimateLine] = []
        for intent in analysis.intents:
            resolved = self._resolve_intent(intent, selections)
            quantity = float(resolved.intent.quantity or 1)
            line = self._price_line(
                db=db,
                estimate_id=estimate.id,
                resolved=resolved
            )
            stored_lines.append(line)

        estimate = price_cache_service.finalize_estimate(
            db=db,
            estimate_id=estimate.id
        )
        if estimate is None:
            raise HTTPException(
                status_code=404,
                detail="Estimate not found"
            )

        estimate_response = CostEstimateResponse.model_validate(estimate)
        estimate_response.lines = [
            CostEstimateLineResponse.model_validate(line)
            for line in stored_lines
        ]
        return analysis, estimate_response


cost_pricing_service = CostPricingService()
