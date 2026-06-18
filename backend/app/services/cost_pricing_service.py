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
        lower_value = value.lower()

        if lower_value.startswith("standard_"):
            suffix = value.split("_", 1)[1] if "_" in value else ""
            if not suffix:
                return "Standard"
            return f"Standard_{suffix[0].upper()}{suffix[1:]}"

        if lower_value.startswith(("b", "d", "e", "f", "g", "m", "l")):
            return f"Standard_{value[0].upper()}{value[1:]}"

        return value

    def _canonical_vm_meter(self, sku: str | None) -> str | None:
        if not sku:
            return None
        value = sku.strip()
        if value.lower().startswith("standard_"):
            suffix = value.split("_", 1)[1] if "_" in value else ""
            if not suffix:
                return None
            return f"{suffix[0].upper()}{suffix[1:]}"
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

    def _build_vm_query_for_lookup(self, lookup: PricingLookupKey) -> RetailPriceQuery:
        canonical_sku = self._canonical_vm_sku(lookup.arm_sku or lookup.tier)
        meter_name = self._canonical_vm_meter(canonical_sku or lookup.meter_name)

        return RetailPriceQuery(
            service_name="Virtual Machines",
            arm_region_name=lookup.region,
            arm_sku_name=canonical_sku,
            sku_name=canonical_sku,
            product_name=lookup.product_name or "Virtual Machines",
            meter_name=meter_name or lookup.meter_name,
            price_type="Consumption",
            currency_code=lookup.currency_code or "USD"
        )

    def _vm_query_candidates(self, lookup: PricingLookupKey) -> list[RetailPriceQuery]:
        canonical_sku = self._canonical_vm_sku(lookup.arm_sku or lookup.tier)
        meter_name = self._canonical_vm_meter(canonical_sku or lookup.meter_name)
        currency_code = lookup.currency_code or "USD"
        region = lookup.region

        candidates = [
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name=region,
                arm_sku_name=canonical_sku,
                sku_name=canonical_sku,
                product_name=lookup.product_name or "Virtual Machines",
                meter_name=meter_name,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name=region,
                arm_sku_name=canonical_sku,
                sku_name=canonical_sku,
                meter_name=meter_name,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name=region,
                arm_sku_name=canonical_sku,
                sku_name=canonical_sku,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name=region,
                meter_name=meter_name,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name=region,
                price_type="Consumption",
                currency_code=currency_code
            )
        ]

        deduped: list[RetailPriceQuery] = []
        seen: set[tuple[Any, ...]] = set()
        for candidate in candidates:
            signature = (
                candidate.service_name,
                candidate.service_family,
                candidate.arm_region_name,
                candidate.arm_sku_name,
                candidate.sku_name,
                candidate.product_name,
                candidate.meter_name,
                candidate.price_type,
                candidate.currency_code
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(candidate)
        return deduped

    def _fetch_best_vm_item(
        self,
        lookup: PricingLookupKey
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str, dict[str, Any]]:
        last_items: list[dict[str, Any]] = []
        last_api_url = "https://prices.azure.com/api/retail/prices"
        last_request_params: dict[str, Any] = {}

        for query in self._vm_query_candidates(lookup):
            best_item, items, api_url, request_params = azure_retail_prices_service.fetch_best_item(query)
            last_items = items
            last_api_url = api_url
            last_request_params = request_params
            if best_item is not None:
                return best_item, items, api_url, request_params

        return None, last_items, last_api_url, last_request_params

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

    def _mysql_deployment_model(self, intent: CostResourceIntent, selections: dict[str, str]) -> str | None:
        return self._first_selection(selections, "mysql_deployment_model", "deployment_model") or intent.deployment_model

    def _mysql_tier(self, intent: CostResourceIntent, selections: dict[str, str]) -> str | None:
        return self._first_selection(selections, "mysql_tier", "tier") or intent.sku

    def _mysql_compute_generation(self, intent: CostResourceIntent, selections: dict[str, str]) -> str | None:
        return self._first_selection(selections, "mysql_compute_generation", "compute_generation") or intent.compute_generation

    def _mysql_product_name(
        self,
        deployment_model: str | None,
        tier: str | None = None,
        compute_generation: str | None = None
    ) -> str:
        parts = ["Azure Database for MySQL"]
        if deployment_model:
            parts.append(deployment_model)
        if tier:
            parts.append(tier)
        if compute_generation:
            parts.append(f"{compute_generation} Series Compute")
        return " ".join(parts)

    def _mysql_meter_name(self, tier: str | None, compute_generation: str | None) -> str | None:
        parts = [part for part in [tier, f"Compute {compute_generation}" if compute_generation else None] if part]
        return " - ".join(parts) if parts else None

    def _sql_query_candidates(self, lookup: PricingLookupKey) -> list[RetailPriceQuery]:
        region = lookup.region
        currency_code = lookup.currency_code or "USD"
        tier = lookup.tier or lookup.meter_name

        candidates = [
            RetailPriceQuery(
                service_name="Azure SQL Database",
                arm_region_name=region,
                product_name=lookup.product_name or "Azure SQL Database",
                meter_name=tier,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Azure SQL Database",
                arm_region_name=region,
                product_name=lookup.product_name or "Azure SQL Database",
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Azure SQL Database",
                arm_region_name=region,
                price_type="Consumption",
                currency_code=currency_code
            )
        ]

        deduped: list[RetailPriceQuery] = []
        seen: set[tuple[Any, ...]] = set()
        for candidate in candidates:
            signature = (
                candidate.service_name,
                candidate.service_family,
                candidate.arm_region_name,
                candidate.arm_sku_name,
                candidate.sku_name,
                candidate.product_name,
                candidate.meter_name,
                candidate.price_type,
                candidate.currency_code
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(candidate)
        return deduped

    def _resolve_mysql(self, intent: CostResourceIntent, selections: dict[str, str]) -> ResolvedPricingLine:
        region = self._first_selection(selections, "region") or intent.region
        deployment_model = self._mysql_deployment_model(intent, selections)
        tier = self._mysql_tier(intent, selections)
        compute_generation = self._mysql_compute_generation(intent, selections)
        descriptor = self._mysql_meter_name(tier, compute_generation)
        product_name = self._mysql_product_name(deployment_model, tier, compute_generation)

        if not region:
            raise HTTPException(
                status_code=422,
                detail="MySQL region is required before pricing can continue."
            )

        if not deployment_model or not tier or not compute_generation:
            raise HTTPException(
                status_code=422,
                detail="MySQL deployment model, tier, and compute generation are required before pricing can continue."
            )

        lookup_spec = {
            "service_name": "Azure Database for MySQL",
            "product_name": product_name,
            "meter_name": descriptor,
            "region": region,
            "currency_code": "USD",
            "unit_of_measure": "1 vCore Hour",
            "tier": tier,
            "deployment_model": deployment_model,
            "compute_generation": compute_generation
        }
        query = RetailPriceQuery(
            service_name="Azure Database for MySQL",
            arm_region_name=region,
            product_name=product_name,
            price_type="Consumption",
            currency_code="USD"
        )
        return ResolvedPricingLine(
            intent=intent,
            lookup_spec=lookup_spec,
            query=query,
            resource_name=f"{deployment_model} {tier} {compute_generation}".strip(),
            matched_exactly=False,
            match_confidence="confirmed" if selections else "parsed_intent",
            assumptions={
                "tier": tier,
                "deployment_model": deployment_model,
                "compute_generation": compute_generation,
                "resolution_source": "confirmed_selection" if selections else "parsed_intent"
            }
        )

    def _mysql_query_candidates(self, lookup: PricingLookupKey) -> list[RetailPriceQuery]:
        region = lookup.region
        currency_code = lookup.currency_code or "USD"
        tier = lookup.tier or lookup.meter_name
        compute_generation = None
        if lookup.meter_name:
            generation_match = re.search(r"\b(Gen\d+)\b", lookup.meter_name, re.IGNORECASE)
            if generation_match:
                compute_generation = generation_match.group(1)
        deployment_model = None
        if lookup.product_name:
            if "single server" in lookup.product_name.lower():
                deployment_model = "Single Server"
            elif "flexible server" in lookup.product_name.lower():
                deployment_model = "Flexible Server"

        product_name = lookup.product_name or self._mysql_product_name(deployment_model, tier, compute_generation)
        relaxed_product_name = self._mysql_product_name(deployment_model, None, None)

        candidates = [
            RetailPriceQuery(
                service_name="Azure Database for MySQL",
                arm_region_name=region,
                product_name=product_name,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Azure Database for MySQL",
                arm_region_name=region,
                product_name=relaxed_product_name,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Azure Database for MySQL",
                arm_region_name=region,
                price_type="Consumption",
                currency_code=currency_code
            ),
            RetailPriceQuery(
                service_name="Azure Database for MySQL",
                arm_region_name=region,
                price_type="Consumption",
                currency_code=currency_code
            )
        ]

        deduped: list[RetailPriceQuery] = []
        seen: set[tuple[Any, ...]] = set()
        for candidate in candidates:
            signature = (
                candidate.service_name,
                candidate.service_family,
                candidate.arm_region_name,
                candidate.arm_sku_name,
                candidate.sku_name,
                candidate.product_name,
                candidate.meter_name,
                candidate.price_type,
                candidate.currency_code
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(candidate)
        return deduped

    def _fetch_best_mysql_item(
        self,
        lookup: PricingLookupKey
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str, dict[str, Any]]:
        last_items: list[dict[str, Any]] = []
        last_api_url = "https://prices.azure.com/api/retail/prices"
        last_request_params: dict[str, Any] = {}

        for query in self._mysql_query_candidates(lookup):
            best_item, items, api_url, request_params = azure_retail_prices_service.fetch_best_item(query)
            last_items = items
            last_api_url = api_url
            last_request_params = request_params
            if best_item is not None:
                return best_item, items, api_url, request_params

        return None, last_items, last_api_url, last_request_params

    def _fetch_best_sql_item(
        self,
        lookup: PricingLookupKey
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str, dict[str, Any]]:
        last_items: list[dict[str, Any]] = []
        last_api_url = "https://prices.azure.com/api/retail/prices"
        last_request_params: dict[str, Any] = {}

        for query in self._sql_query_candidates(lookup):
            best_item, items, api_url, request_params = azure_retail_prices_service.fetch_best_item(query)
            last_items = items
            last_api_url = api_url
            last_request_params = request_params
            if best_item is not None:
                return best_item, items, api_url, request_params

        return None, last_items, last_api_url, last_request_params

    def _resolve_intent(
        self,
        intent: CostResourceIntent,
        selections: dict[str, str]
    ) -> ResolvedPricingLine:
        resource_type = intent.resource_type.lower()
        if "virtual machine" in resource_type:
            return self._resolve_vm(intent, selections)
        if "mysql" in resource_type:
            return self._resolve_mysql(intent, selections)
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
        candidate_records: list[dict[str, Any]] = []
        api_url = "https://prices.azure.com/api/retail/prices"
        request_params: dict[str, Any] = {}

        if snapshot is None or price_cache_service.should_refresh(lookup):
            if resolved.intent.resource_type.lower().startswith("virtual machine"):
                best_item, items, api_url, request_params = self._fetch_best_vm_item(lookup)
            elif "mysql" in resolved.intent.resource_type.lower():
                best_item, items, api_url, request_params = self._fetch_best_mysql_item(lookup)
            elif "sql" in resolved.intent.resource_type.lower():
                best_item, items, api_url, request_params = self._fetch_best_sql_item(lookup)
            else:
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
            candidate_records = items
            snapshot = price_cache_service.refresh_lookup_key(
                db=db,
                lookup_key=lookup,
                api_url=api_url,
                raw_payload=best_item,
                request_params=request_params
            )
        elif snapshot.raw_payload:
            candidate_records = [snapshot.raw_payload]

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
                "quantity": quantity,
                "candidate_count": len(candidate_records),
                "candidate_records": candidate_records
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

    def refresh_all_vm_prices(
        self,
        db: Session,
        requested_by: str | None = None
    ) -> PriceRefreshRun:
        run = price_cache_service.start_refresh_run(
            db=db,
            trigger_type="manual",
            requested_by=requested_by,
            refresh_metadata={
                "scope": "virtual_machines",
                "source": "refresh_all_vm_prices"
            }
        )

        try:
            lookup_keys = (
                db.query(PricingLookupKey)
                .filter(
                    PricingLookupKey.is_active.is_(True),
                    PricingLookupKey.service_name == "Virtual Machines"
                )
                .all()
            )

            for lookup_key in lookup_keys:
                run.keys_processed += 1
                try:
                    best_item, items, api_url, request_params = self._fetch_best_vm_item(lookup_key)
                    if best_item is None:
                        run.keys_unchanged += 1
                        if not run.error_summary:
                            run.error_summary = f"{lookup_key.normalized_key}: no live Azure VM price matched"
                        else:
                            run.error_summary = f"{run.error_summary}\n{lookup_key.normalized_key}: no live Azure VM price matched"
                        continue

                    before_snapshot = price_cache_service.get_current_snapshot(
                        db=db,
                        lookup_key_id=lookup_key.id
                    )
                    after_snapshot = price_cache_service.refresh_lookup_key(
                        db=db,
                        lookup_key=lookup_key,
                        api_url=api_url,
                        raw_payload=best_item,
                        request_params={
                            **request_params,
                            "candidate_count": len(items),
                            "source": "refresh_all_vm_prices"
                        }
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
            return price_cache_service.finish_refresh_run(
                db=db,
                run=run,
                status="SUCCESS" if run.keys_failed == 0 else "PARTIAL",
                error_summary=run.error_summary
            )
        except Exception as ex:
            return price_cache_service.finish_refresh_run(
                db=db,
                run=run,
                status="FAILED",
                error_summary=str(ex)
            )


cost_pricing_service = CostPricingService()
