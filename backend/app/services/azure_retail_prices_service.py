from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


AZURE_RETAIL_PRICES_URL = "https://prices.azure.com/api/retail/prices"


@dataclass(frozen=True)
class RetailPriceQuery:
    service_name: str | None = None
    service_family: str | None = None
    arm_region_name: str | None = None
    arm_sku_name: str | None = None
    sku_name: str | None = None
    product_name: str | None = None
    meter_name: str | None = None
    price_type: str | None = "Consumption"
    currency_code: str = "USD"


class AzureRetailPricesService:

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _odata_quote(self, value: str) -> str:
        return value.replace("'", "''")

    def _field_matches(self, item_value: Any, query_value: str | None) -> bool:
        if not query_value:
            return False

        if item_value is None:
            return False

        item_text = str(item_value).strip().lower()
        query_text = str(query_value).strip().lower()
        return item_text == query_text or query_text in item_text or item_text in query_text

    def build_filter(self, query: RetailPriceQuery) -> str:
        clauses: list[str] = []
        if query.service_name:
            clauses.append(f"serviceName eq '{self._odata_quote(query.service_name)}'")
        if query.service_family:
            clauses.append(f"serviceFamily eq '{self._odata_quote(query.service_family)}'")
        if query.arm_region_name:
            clauses.append(f"armRegionName eq '{self._odata_quote(query.arm_region_name)}'")
        if query.arm_sku_name:
            clauses.append(f"armSkuName eq '{self._odata_quote(query.arm_sku_name)}'")
        if query.sku_name:
            clauses.append(f"skuName eq '{self._odata_quote(query.sku_name)}'")
        if query.product_name:
            clauses.append(f"productName eq '{self._odata_quote(query.product_name)}'")
        if query.meter_name:
            clauses.append(f"meterName eq '{self._odata_quote(query.meter_name)}'")
        if query.price_type:
            clauses.append(f"priceType eq '{self._odata_quote(query.price_type)}'")

        return " and ".join(clauses)

    def _request_params(self, query: RetailPriceQuery) -> dict[str, str]:
        params: dict[str, str] = {"currencyCode": f"'{query.currency_code.upper()}'"}
        filter_expr = self.build_filter(query)
        if filter_expr:
            params["$filter"] = filter_expr
        return params

    def fetch_items(
        self,
        query: RetailPriceQuery,
        max_items: int = 1000
    ) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        items: list[dict[str, Any]] = []
        params = self._request_params(query)
        request_params: dict[str, Any] = {
            **params,
            "api_version": "2023-01-01-preview"
        }

        next_url: str | None = AZURE_RETAIL_PRICES_URL
        next_params: dict[str, Any] | None = {
            **params,
            "api-version": "2023-01-01-preview"
        }

        with httpx.Client(timeout=self.timeout) as client:
            while next_url and len(items) < max_items:
                response = client.get(next_url, params=next_params if next_url == AZURE_RETAIL_PRICES_URL else None)
                response.raise_for_status()
                payload = response.json()
                items.extend(payload.get("Items", []))

                next_url = payload.get("NextPageLink")
                next_params = None

        return items[:max_items], AZURE_RETAIL_PRICES_URL, request_params

    def _score_item(self, item: dict[str, Any], query: RetailPriceQuery) -> int:
        score = 0
        if self._field_matches(item.get("serviceName"), query.service_name):
            score += 20
        if self._field_matches(item.get("serviceFamily"), query.service_family):
            score += 10
        if self._field_matches(item.get("armRegionName"), query.arm_region_name):
            score += 10
        if self._field_matches(item.get("armSkuName"), query.arm_sku_name):
            score += 20
        if self._field_matches(item.get("skuName"), query.sku_name):
            score += 15
        if self._field_matches(item.get("productName"), query.product_name):
            score += 15
        if self._field_matches(item.get("meterName"), query.meter_name):
            score += 20
        if item.get("currencyCode", "").upper() == query.currency_code.upper():
            score += 5
        if item.get("type") == (query.price_type or "Consumption"):
            score += 5
        if item.get("isPrimaryMeterRegion") is True:
            score += 1
        if self._field_matches(item.get("meterName"), "storage") or self._field_matches(item.get("productName"), "storage"):
            score += 1
        if self._field_matches(item.get("meterName"), "bandwidth") or self._field_matches(item.get("productName"), "bandwidth"):
            score += 1
        return score

    def select_best_item(
        self,
        items: list[dict[str, Any]],
        query: RetailPriceQuery
    ) -> dict[str, Any] | None:
        if not items:
            return None

        scored = sorted(
            items,
            key=lambda item: (
                self._score_item(item, query),
                float(item.get("retailPrice") or 0),
                str(item.get("effectiveStartDate") or "")
            ),
            reverse=True
        )
        return scored[0]

    def fetch_best_item(
        self,
        query: RetailPriceQuery,
        max_items: int = 1000
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str, dict[str, Any]]:
        items, api_url, request_params = self.fetch_items(query, max_items=max_items)
        return self.select_best_item(items, query), items, api_url, request_params


azure_retail_prices_service = AzureRetailPricesService()
