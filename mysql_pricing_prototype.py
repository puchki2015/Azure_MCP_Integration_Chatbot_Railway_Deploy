#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from enum import Enum
from typing import Any

import requests
from pydantic import BaseModel
from pydantic import Field


AZURE_RETAIL_PRICES_URL = "https://prices.azure.com/api/retail/prices"


SYSTEM_PROMPT = """
You are a pricing-intent extraction assistant for Azure Database for MySQL.

Goal:
- Convert free-form user text into a structured pricing request.
- Use values that the user already provided.
- Do not ask the user again for any field that is already explicit in the text.
- Ask only for missing or ambiguous fields.

Pricing-critical fields for Azure Database for MySQL:
- region
- deployment_model
- tier
- compute_generation

Rules:
1. Read the user text carefully and extract every explicit value.
2. Normalize synonyms into the dropdown values below.
3. If a field is present in text, do not request it again.
4. If a field is missing, mark it as missing and ask for it.
5. Do not invent defaults like "General Purpose" or "Flexible Server".
6. If the query already has enough information for a single price lookup, output a runnable query object.
7. If not enough information exists, output a clarification object with only the missing fields.
8. Keep the response structured and deterministic.

Allowed dropdown values:

deployment_model:
- Single Server
- Flexible Server

tier:
- Basic
- Burstable
- General Purpose
- Memory Optimized
- Business Critical

compute_generation:
- Gen4
- Gen5
- Dsv3
- Dsv5
- Dsv6
- Dasv5
- Dasv6
- Ddsv5
- Ddsv6
- Esv6
- Easv6
- Eadsv5
- Eadsv6
- Edsv5
- Edsv6

Normalization examples:
- "flexible" -> "Flexible Server"
- "single" -> "Single Server"
- "gp" -> "General Purpose"
- "mem optimized" -> "Memory Optimized"
- "bc" -> "Business Critical"
- "dsv6" -> "Dsv6"
- "dadsv6" -> "Dasv6"
- "eddsv5" -> "Edsv5"

Output requirements:
- Return the extracted draft object.
- Return the missing fields only when needed.
- Return the runnable query only when all required fields are present.
""".strip()


class MySQLDeploymentModel(str, Enum):
    single_server = "Single Server"
    flexible_server = "Flexible Server"


class MySQLTier(str, Enum):
    basic = "Basic"
    burstable = "Burstable"
    general_purpose = "General Purpose"
    memory_optimized = "Memory Optimized"
    business_critical = "Business Critical"


class MySQLComputeGeneration(str, Enum):
    gen4 = "Gen4"
    gen5 = "Gen5"
    dsv3 = "Dsv3"
    dsv5 = "Dsv5"
    dsv6 = "Dsv6"
    dasv5 = "Dasv5"
    dasv6 = "Dasv6"
    ddsv5 = "Ddsv5"
    ddsv6 = "Ddsv6"
    esv6 = "Esv6"
    easv6 = "Easv6"
    eadsv5 = "Eadsv5"
    eadsv6 = "Eadsv6"
    edsv5 = "Edsv5"
    edsv6 = "Edsv6"


class MySQLPricingDraft(BaseModel):
    service_name: str = "Azure Database for MySQL"
    region: str | None = None
    deployment_model: MySQLDeploymentModel | None = None
    tier: MySQLTier | None = None
    compute_generation: MySQLComputeGeneration | None = None
    quantity: float = 1
    currency_code: str = "USD"
    price_type: str = "Consumption"


class MySQLPricingQuery(BaseModel):
    service_name: str = "Azure Database for MySQL"
    region: str
    deployment_model: MySQLDeploymentModel
    tier: MySQLTier
    compute_generation: MySQLComputeGeneration
    quantity: float = 1
    currency_code: str = "USD"
    price_type: str = "Consumption"


class MySQLClarificationItem(BaseModel):
    field_name: str
    message: str
    suggested_values: list[str] = Field(default_factory=list)


class MySQLPricingAnalysis(BaseModel):
    raw_input: str
    normalized_text: str
    draft: MySQLPricingDraft
    runnable_query: MySQLPricingQuery | None = None
    needs_confirmation: bool = False
    clarification_items: list[MySQLClarificationItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    ready_to_price: bool = False


class MySQLPricingLookupResult(BaseModel):
    api_url: str
    request_params: dict[str, Any]
    candidate_count: int
    best_item: dict[str, Any] | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    lookup_mode: str = "strict"


SAMPLE_OFFLINE_ITEM: dict[str, Any] = {
    "serviceName": "Azure Database for MySQL",
    "serviceFamily": "Databases",
    "armRegionName": "westus",
    "productName": "Azure Database for MySQL Flexible Server General Purpose Ddsv6 Series Compute",
    "meterName": "General Purpose Compute Ddsv6",
    "skuName": "vCore",
    "armSkuName": "AzureDB_MySQL_Flexible_Server_General_Purpose_Compute_Ddsv6_Series",
    "unitOfMeasure": "1 Hour",
    "currencyCode": "USD",
    "type": "Consumption",
    "retailPrice": 0.146,
    "effectiveStartDate": "2026-01-01T00:00:00Z",
}


REGION_ALIASES: dict[str, str] = {
    "east us": "eastus",
    "eastus": "eastus",
    "east us 2": "eastus2",
    "eastus2": "eastus2",
    "west us": "westus",
    "westus": "westus",
    "west us 2": "westus2",
    "westus2": "westus2",
    "central us": "centralus",
    "centralus": "centralus",
    "uk south": "uksouth",
    "uksouth": "uksouth",
}


DEPLOYMENT_MODEL_ALIASES: dict[str, MySQLDeploymentModel] = {
    "flexible server": MySQLDeploymentModel.flexible_server,
    "flexible": MySQLDeploymentModel.flexible_server,
    "single server": MySQLDeploymentModel.single_server,
    "single": MySQLDeploymentModel.single_server,
}


TIER_ALIASES: dict[str, MySQLTier] = {
    "general purpose": MySQLTier.general_purpose,
    "gp": MySQLTier.general_purpose,
    "memory optimized": MySQLTier.memory_optimized,
    "mem optimized": MySQLTier.memory_optimized,
    "business critical": MySQLTier.business_critical,
    "bc": MySQLTier.business_critical,
    "burstable": MySQLTier.burstable,
    "basic": MySQLTier.basic,
}


COMPUTE_GENERATION_ALIASES: dict[str, MySQLComputeGeneration] = {
    "gen4": MySQLComputeGeneration.gen4,
    "gen5": MySQLComputeGeneration.gen5,
    "dsv3": MySQLComputeGeneration.dsv3,
    "dsv5": MySQLComputeGeneration.dsv5,
    "dsv6": MySQLComputeGeneration.dsv6,
    "dasv5": MySQLComputeGeneration.dasv5,
    "dasv6": MySQLComputeGeneration.dasv6,
    "dadsv5": MySQLComputeGeneration.dasv6,
    "dadsv6": MySQLComputeGeneration.dasv6,
    "ddsv5": MySQLComputeGeneration.ddsv5,
    "ddsv6": MySQLComputeGeneration.ddsv6,
    "esv6": MySQLComputeGeneration.esv6,
    "easv6": MySQLComputeGeneration.easv6,
    "eadsv5": MySQLComputeGeneration.eadsv5,
    "eadsv6": MySQLComputeGeneration.eadsv6,
    "edsv5": MySQLComputeGeneration.edsv5,
    "edsv6": MySQLComputeGeneration.edsv6,
}


def normalize_text(raw_input: str) -> str:
    text = raw_input.strip().lower()
    for alias, normalized in sorted(REGION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(alias)}\b", normalized, text)
    return re.sub(r"\s+", " ", text)


def detect_region(text: str) -> str | None:
    for alias, normalized in sorted(REGION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return normalized
    return None


def detect_enum_value(text: str, mapping: dict[str, Any]) -> Any | None:
    for alias, enum_value in mapping.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return enum_value
    return None


def detect_quantity(text: str) -> float:
    match = re.search(r"\b(?:qty|quantity|count)\s*(?:is\s*)?(\d+(?:\.\d+)?)\b", text)
    if match:
        return float(match.group(1))

    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:x\s*)?(?:mysql|database|databases|server|servers|instance|instances)\b", text)
    if match:
        return float(match.group(1))

    return 1


def build_azure_retail_filter(query: MySQLPricingQuery) -> str:
    clauses = [
        "serviceFamily eq 'Databases'",
        f"serviceName eq '{query.service_name}'",
        f"armRegionName eq '{query.region}'",
        f"priceType eq '{query.price_type}'",
        f"productName eq '{build_product_name(query)}'",
    ]
    return " and ".join(clauses)


def build_relaxed_azure_retail_filter(query: MySQLPricingQuery) -> str:
    clauses = [
        "serviceFamily eq 'Databases'",
        f"serviceName eq '{query.service_name}'",
        f"armRegionName eq '{query.region}'",
        f"priceType eq '{query.price_type}'",
    ]
    return " and ".join(clauses)


def build_product_name(query: MySQLPricingQuery) -> str:
    return (
        f"{query.service_name} "
        f"{query.deployment_model.value} "
        f"{query.tier.value} "
        f"{query.compute_generation.value} Series Compute"
    )


def build_request_params(query: MySQLPricingQuery) -> dict[str, Any]:
    return {
        "currencyCode": f"'{query.currency_code.upper()}'",
        "$filter": build_azure_retail_filter(query),
        "api-version": "2023-01-01-preview",
    }


def build_relaxed_request_params(query: MySQLPricingQuery) -> dict[str, Any]:
    return {
        "currencyCode": f"'{query.currency_code.upper()}'",
        "$filter": build_relaxed_azure_retail_filter(query),
        "api-version": "2023-01-01-preview",
    }


def format_api_call(query: MySQLPricingQuery) -> str:
    params = build_request_params(query)
    return (
        f"GET {AZURE_RETAIL_PRICES_URL} "
        f"?currencyCode={params['currencyCode']} "
        f"&$filter={params['$filter']} "
        f"&api-version={params['api-version']}"
    )


def format_relaxed_api_call(query: MySQLPricingQuery) -> str:
    params = build_relaxed_request_params(query)
    return (
        f"GET {AZURE_RETAIL_PRICES_URL} "
        f"?currencyCode={params['currencyCode']} "
        f"&$filter={params['$filter']} "
        f"&api-version={params['api-version']}"
    )


def fetch_price_items(query: MySQLPricingQuery, max_items: int = 100) -> MySQLPricingLookupResult:
    params = build_request_params(query)
    items: list[dict[str, Any]] = []
    next_url: str | None = AZURE_RETAIL_PRICES_URL
    next_params: dict[str, Any] | None = {
        "currencyCode": params["currencyCode"],
        "$filter": params["$filter"],
        "api-version": params["api-version"],
    }

    with requests.Session() as session:
        while next_url and len(items) < max_items:
            response = session.get(next_url, params=next_params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("Items", []))
            next_url = payload.get("NextPageLink")
            next_params = None

    return MySQLPricingLookupResult(
        api_url=AZURE_RETAIL_PRICES_URL,
        request_params=params,
        candidate_count=len(items),
        items=items[:max_items],
        best_item=select_best_item(items, query),
        lookup_mode="strict",
    )


def fetch_price_items_relaxed(query: MySQLPricingQuery, max_items: int = 100) -> MySQLPricingLookupResult:
    params = build_relaxed_request_params(query)
    items: list[dict[str, Any]] = []
    next_url: str | None = AZURE_RETAIL_PRICES_URL
    next_params: dict[str, Any] | None = {
        "currencyCode": params["currencyCode"],
        "$filter": params["$filter"],
        "api-version": params["api-version"],
    }

    with requests.Session() as session:
        while next_url and len(items) < max_items:
            response = session.get(next_url, params=next_params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("Items", []))
            next_url = payload.get("NextPageLink")
            next_params = None

    return MySQLPricingLookupResult(
        api_url=AZURE_RETAIL_PRICES_URL,
        request_params=params,
        candidate_count=len(items),
        items=items[:max_items],
        best_item=select_best_item(items, query),
        lookup_mode="relaxed",
    )


def fetch_price_items_offline(query: MySQLPricingQuery) -> MySQLPricingLookupResult:
    return MySQLPricingLookupResult(
        api_url=AZURE_RETAIL_PRICES_URL,
        request_params=build_request_params(query),
        candidate_count=1,
        items=[SAMPLE_OFFLINE_ITEM],
        best_item=SAMPLE_OFFLINE_ITEM,
    )


def score_item(item: dict[str, Any], query: MySQLPricingQuery) -> int:
    score = 0
    if str(item.get("serviceName") or "").strip().lower() == query.service_name.lower():
        score += 20
    if str(item.get("armRegionName") or "").strip().lower() == query.region.lower():
        score += 10
    if str(item.get("productName") or "").strip().lower() == build_product_name(query).lower():
        score += 15
    if str(item.get("meterName") or "").strip().lower() == f"{query.tier.value} compute {query.compute_generation.value}".lower():
        score += 20
    if str(item.get("skuName") or "").strip().lower() == query.compute_generation.value.lower():
        score += 8
    if str(item.get("currencyCode") or "").strip().upper() == query.currency_code.upper():
        score += 5
    if str(item.get("type") or "").strip().lower() == query.price_type.lower():
        score += 5
    return score


def select_best_item(items: list[dict[str, Any]], query: MySQLPricingQuery) -> dict[str, Any] | None:
    if not items:
        return None

    scored = sorted(
        items,
        key=lambda item: (
            score_item(item, query),
            float(item.get("retailPrice") or 0),
            str(item.get("effectiveStartDate") or "")
        ),
        reverse=True,
    )
    return scored[0]


def summarize_best_item(best_item: dict[str, Any] | None) -> str:
    if not best_item:
        return "No matching Azure price was found."

    meter_name = best_item.get("meterName") or "n/a"
    product_name = best_item.get("productName") or "n/a"
    sku_name = best_item.get("skuName") or "n/a"
    unit_of_measure = best_item.get("unitOfMeasure") or "n/a"
    retail_price = best_item.get("retailPrice")
    currency = best_item.get("currencyCode") or "USD"
    arm_sku_name = best_item.get("armSkuName") or "n/a"
    region = best_item.get("armRegionName") or "n/a"
    price_type = best_item.get("type") or "n/a"

    try:
        price_text = f"{float(retail_price):.6f}"
    except Exception:
        price_text = str(retail_price)

    return "\n".join([
        f"Best match: {product_name}",
        f"Meter: {meter_name}",
        f"SKU: {sku_name}",
        f"ARM SKU: {arm_sku_name}",
        f"Region: {region}",
        f"Unit: {unit_of_measure}",
        f"Price: {price_text} {currency}",
        f"Price type: {price_type}",
    ])


def render_item_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No rows returned."

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.append(f"Row {index}:")
        lines.append(f"  productName: {item.get('productName', 'n/a')}")
        lines.append(f"  meterName: {item.get('meterName', 'n/a')}")
        lines.append(f"  skuName: {item.get('skuName', 'n/a')}")
        lines.append(f"  armSkuName: {item.get('armSkuName', 'n/a')}")
        lines.append(f"  region: {item.get('armRegionName', 'n/a')}")
        lines.append(f"  unitOfMeasure: {item.get('unitOfMeasure', 'n/a')}")
        lines.append(f"  retailPrice: {item.get('retailPrice', 'n/a')}")
        lines.append(f"  currencyCode: {item.get('currencyCode', 'n/a')}")
        lines.append(f"  priceType: {item.get('type', 'n/a')}")
    return "\n".join(lines)


def build_clarification_items(draft: MySQLPricingDraft) -> tuple[list[MySQLClarificationItem], list[str]]:
    clarifications: list[MySQLClarificationItem] = []
    missing_fields: list[str] = []

    if not draft.region:
        missing_fields.append("region")
        clarifications.append(
            MySQLClarificationItem(
                field_name="region",
                message="Region is required for MySQL pricing.",
                suggested_values=sorted(set(REGION_ALIASES.values()))
            )
        )
    if not draft.deployment_model:
        missing_fields.append("deployment_model")
        clarifications.append(
            MySQLClarificationItem(
                field_name="deployment_model",
                message="Choose the MySQL deployment model.",
                suggested_values=[item.value for item in MySQLDeploymentModel]
            )
        )
    if not draft.tier:
        missing_fields.append("tier")
        clarifications.append(
            MySQLClarificationItem(
                field_name="tier",
                message="Choose the MySQL pricing tier.",
                suggested_values=[item.value for item in MySQLTier]
            )
        )
    if not draft.compute_generation:
        missing_fields.append("compute_generation")
        clarifications.append(
            MySQLClarificationItem(
                field_name="compute_generation",
                message="Choose the MySQL compute generation.",
                suggested_values=[item.value for item in MySQLComputeGeneration]
            )
        )

    return clarifications, missing_fields


def finalize_query(draft: MySQLPricingDraft) -> MySQLPricingQuery | None:
    if not draft.region or not draft.deployment_model or not draft.tier or not draft.compute_generation:
        return None

    return MySQLPricingQuery(
        service_name=draft.service_name,
        region=draft.region,
        deployment_model=draft.deployment_model,
        tier=draft.tier,
        compute_generation=draft.compute_generation,
        quantity=draft.quantity,
        currency_code=draft.currency_code,
        price_type=draft.price_type,
    )


def apply_selections_to_draft(
    draft: MySQLPricingDraft,
    selections: dict[str, str]
) -> MySQLPricingDraft:
    return MySQLPricingDraft(
        service_name=draft.service_name,
        region=selections.get("region", draft.region),
        deployment_model=selections.get("deployment_model", draft.deployment_model),
        tier=selections.get("tier", draft.tier),
        compute_generation=selections.get("compute_generation", draft.compute_generation),
        quantity=draft.quantity,
        currency_code=draft.currency_code,
        price_type=draft.price_type,
    )


def prompt_for_missing_fields(
    raw_input: str,
    draft: MySQLPricingDraft,
    clarifications: list[MySQLClarificationItem]
) -> dict[str, str]:
    selections: dict[str, str] = {}
    print()
    print("Original query:")
    print(raw_input)
    print()
    print("Already extracted:")
    print(json.dumps(draft.model_dump(mode="json"), indent=2))

    for item in clarifications:
        options = item.suggested_values
        print()
        print(f"{item.field_name}: {item.message}")
        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")

        while True:
            answer = input(f"Select {item.field_name} [1-{len(options)}]: ").strip()
            if not answer:
                continue
            if answer.isdigit():
                choice = int(answer)
                if 1 <= choice <= len(options):
                    selections[item.field_name] = options[choice - 1]
                    break
            if answer in options:
                selections[item.field_name] = answer
                break
            print("Invalid choice. Enter the option number or the exact value.")

    return selections


def analyze_user_text(raw_input: str) -> MySQLPricingAnalysis:
    normalized_text = normalize_text(raw_input)
    draft = MySQLPricingDraft(
        region=detect_region(normalized_text),
        deployment_model=detect_enum_value(normalized_text, DEPLOYMENT_MODEL_ALIASES),
        tier=detect_enum_value(normalized_text, TIER_ALIASES),
        compute_generation=detect_enum_value(normalized_text, COMPUTE_GENERATION_ALIASES),
        quantity=detect_quantity(normalized_text),
    )
    clarifications, missing_fields = build_clarification_items(draft)
    runnable_query = finalize_query(draft)
    ready_to_price = runnable_query is not None

    return MySQLPricingAnalysis(
        raw_input=raw_input,
        normalized_text=normalized_text,
        draft=draft,
        runnable_query=runnable_query,
        needs_confirmation=not ready_to_price,
        clarification_items=clarifications,
        missing_fields=missing_fields,
        ready_to_price=ready_to_price,
    )


def run_samples(
    samples: list[str],
    show_json: bool = True,
    show_summary: bool = True,
    offline_fallback: bool = False
) -> None:
    print("SYSTEM PROMPT")
    print("=" * 80)
    print(SYSTEM_PROMPT)
    print()

    for index, sample in enumerate(samples, start=1):
        result = analyze_user_text(sample)
        print(f"SAMPLE {index}")
        print("-" * 80)
        print("RAW INPUT:", result.raw_input)
        print("NORMALIZED:", result.normalized_text)
        print("DRAFT:", result.draft.model_dump())
        print("READY TO PRICE:", result.ready_to_price)
        print("MISSING FIELDS:", result.missing_fields)
        print("CLARIFICATIONS:", json.dumps([item.model_dump() for item in result.clarification_items], indent=2))
        if result.runnable_query:
            print("RUNNABLE QUERY:", result.runnable_query.model_dump())
            print("AZURE FILTER:", build_azure_retail_filter(result.runnable_query))
            print("API CALL:", format_api_call(result.runnable_query))
            try:
                lookup = fetch_price_items_offline(result.runnable_query) if offline_fallback else fetch_price_items(result.runnable_query)
                if lookup.candidate_count == 0 and not offline_fallback:
                    lookup = fetch_price_items_relaxed(result.runnable_query)
                    print("RELAXED FILTER:", build_relaxed_azure_retail_filter(result.runnable_query))
                    print("RELAXED API CALL:", format_relaxed_api_call(result.runnable_query))
                print("CANDIDATE COUNT:", lookup.candidate_count)
                if show_summary:
                    print(summarize_best_item(lookup.best_item))
                if lookup.lookup_mode == "relaxed":
                    print("RELAXED MATCH SET:")
                    print(render_item_list(lookup.items))
                if show_json:
                    if lookup.lookup_mode == "relaxed":
                        print("ALL ITEMS:", json.dumps(lookup.items, indent=2))
                    print("BEST ITEM:", json.dumps(lookup.best_item, indent=2))
            except Exception as ex:
                print("AZURE LOOKUP ERROR:", str(ex))
                if offline_fallback:
                    lookup = fetch_price_items_offline(result.runnable_query)
                    print("CANDIDATE COUNT:", lookup.candidate_count)
                    if show_summary:
                        print(summarize_best_item(lookup.best_item))
                    if show_json:
                        print("ALL ITEMS:", json.dumps(lookup.items, indent=2))
                        print("BEST ITEM:", json.dumps(lookup.best_item, indent=2))
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone MySQL pricing parser prototype.")
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="User query to analyze. Can be provided multiple times."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start a simple REPL for entering MySQL pricing queries."
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Hide the raw JSON best item output."
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Hide the human-readable summary output."
    )
    parser.add_argument(
        "--offline-fallback",
        action="store_true",
        help="Use a local sample pricing row if the live Azure API is unavailable."
    )
    args = parser.parse_args()

    if args.interactive:
        print("Interactive MySQL pricing parser")
        print("Type a query and press Enter. Submit an empty line or 'exit' to quit.")
        print()
        while True:
            try:
                raw_input_value = input("mysql> ").strip()
            except EOFError:
                print()
                break

            if not raw_input_value or raw_input_value.lower() in {"exit", "quit"}:
                break

            result = analyze_user_text(raw_input_value)
            print(json.dumps(result.model_dump(mode="json"), indent=2))
            runnable_query = result.runnable_query
            if not runnable_query and result.clarification_items:
                selections = prompt_for_missing_fields(
                    result.raw_input,
                    result.draft,
                    result.clarification_items
                )
                filled_draft = apply_selections_to_draft(result.draft, selections)
                runnable_query = finalize_query(filled_draft)
                if runnable_query:
                    print("FILLED QUERY:", runnable_query.model_dump())

            if runnable_query:
                print("AZURE FILTER:", build_azure_retail_filter(runnable_query))
                print("API CALL:", format_api_call(runnable_query))
                try:
                    lookup = fetch_price_items_offline(runnable_query) if args.offline_fallback else fetch_price_items(runnable_query)
                    if lookup.candidate_count == 0 and not args.offline_fallback:
                        lookup = fetch_price_items_relaxed(runnable_query)
                        print("RELAXED FILTER:", build_relaxed_azure_retail_filter(runnable_query))
                        print("RELAXED API CALL:", format_relaxed_api_call(runnable_query))
                    print("CANDIDATE COUNT:", lookup.candidate_count)
                    if not args.no_summary:
                        print(summarize_best_item(lookup.best_item))
                    if lookup.lookup_mode == "relaxed":
                        print("RELAXED MATCH SET:")
                        print(render_item_list(lookup.items))
                    if not args.no_json:
                        if lookup.lookup_mode == "relaxed":
                            print("ALL ITEMS:", json.dumps(lookup.items, indent=2))
                        print("BEST ITEM:", json.dumps(lookup.best_item, indent=2))
                except Exception as ex:
                    print("AZURE LOOKUP ERROR:", str(ex))
                    if args.offline_fallback:
                        lookup = fetch_price_items_offline(runnable_query)
                        print("CANDIDATE COUNT:", lookup.candidate_count)
                        if not args.no_summary:
                            print(summarize_best_item(lookup.best_item))
                        if not args.no_json:
                            print("ALL ITEMS:", json.dumps(lookup.items, indent=2))
                            print("BEST ITEM:", json.dumps(lookup.best_item, indent=2))
            print()
        return

    samples = args.queries or [
        "Price Azure Database for MySQL Flexible Server General Purpose Ddsv6 in west us",
        "Price Azure Database for MySQL in west us",
        "Need MySQL flexible general purpose in east us 2 with Edsv5"
    ]
    run_samples(
        samples,
        show_json=not args.no_json,
        show_summary=not args.no_summary,
        offline_fallback=args.offline_fallback
    )


if __name__ == "__main__":
    main()
