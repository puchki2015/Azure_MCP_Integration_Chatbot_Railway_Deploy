from __future__ import annotations

import re

from app.schemas.costs import CostAnalysisResponse
from app.schemas.costs import CostClarificationItem
from app.schemas.costs import CostResourceIntent


class CostAnalysisService:

    REGION_ALIASES = {
        "east us": "eastus",
        "eastus": "eastus",
        "west us": "westus",
        "westus": "westus",
        "uk south": "uksouth",
        "uksouth": "uksouth",
        "central us": "centralus",
        "centralus": "centralus",
        "east us 2": "eastus2",
        "eastus2": "eastus2",
        "west us 2": "westus2",
        "westus2": "westus2"
    }

    MYSQL_DEPLOYMENT_MODEL_ALIASES = {
        "single server": "Single Server",
        "single": "Single Server",
        "flexible server": "Flexible Server",
        "flexible": "Flexible Server"
    }

    MYSQL_TIER_ALIASES = {
        "basic": "Basic",
        "burstable": "Burstable",
        "storage": "Storage",
        "general purpose": "General Purpose",
        "gp": "General Purpose",
        "memory optimized": "Memory Optimized",
        "mem optimized": "Memory Optimized",
        "business critical": "Business Critical",
        "bc": "Business Critical"
    }

    MYSQL_COMPUTE_GENERATION_ALIASES = {
        "gen4": "Gen4",
        "gen5": "Gen5",
        "dsv3": "Dsv3",
        "dsv5": "Dsv5",
        "dsv6": "Dsv6",
        "dasv5": "Dasv5",
        "dasv6": "Dasv6",
        "dadsv5": "Dasv6",
        "dadsv6": "Dasv6",
        "ddsv5": "Ddsv5",
        "ddsv6": "Ddsv6",
        "esv6": "Esv6",
        "easv6": "Easv6",
        "eadsv5": "Eadsv5",
        "eadsv6": "Eadsv6",
        "edsv5": "Edsv5",
        "edsv6": "Edsv6"
    }

    AMBIGUOUS_PHRASES = [
        "latest ubuntu configuration",
        "average medium optimized",
        "minimum configuration",
        "best fit",
        "optimized",
        "small",
        "medium",
        "large",
        "cheap"
    ]

    def normalize_text(self, raw_input: str) -> str:
        text = raw_input.strip()
        lower = text.lower()
        for alias, normalized in sorted(self.REGION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            lower = re.sub(rf"\b{re.escape(alias)}\b", normalized, lower)
        return lower

    def _find_alias_value(self, text: str, aliases: dict[str, str]) -> str | None:
        for alias, normalized in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                return normalized
        return None

    def _extract_quantity(self, text: str, default: float | None = None) -> float | None:
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:x|vm|vms|virtual machines|sql databases?|databases?)\b", text, re.IGNORECASE)
        if match:
            return float(match.group(1))

        if default is not None:
            return default

        match = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
        return float(match.group(1)) if match else None

    def analyze(self, raw_input: str) -> CostAnalysisResponse:
        normalized_text = self.normalize_text(raw_input)
        intents: list[CostResourceIntent] = []
        clarifications: list[CostClarificationItem] = []
        assumptions: list[str] = []

        vm_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:vms?|virtual machines?)\b", normalized_text, re.IGNORECASE)
        has_vm_keyword = bool(
            re.search(r"\b(?:vm|vms|virtual machine|virtual machines)\b", normalized_text, re.IGNORECASE)
        )
        if vm_match or has_vm_keyword:
            quantity = self._extract_quantity(normalized_text)
            region = next((normalized for alias, normalized in self.REGION_ALIASES.items() if alias in normalized_text), None)
            sku_match = re.search(r"\bstandard_[a-z0-9_]+|\bb\d+ms?\b|\bd\d+s?_v\d+\b", normalized_text, re.IGNORECASE)
            os_image = "ubuntu" if "ubuntu" in normalized_text else None
            intents.append(
                CostResourceIntent(
                    resource_type="Virtual Machine",
                    quantity=quantity,
                    region=region,
                    sku=sku_match.group(0) if sku_match else None,
                    os_image=os_image,
                    unit_name="hour",
                    confidence="medium" if sku_match else "low"
                )
            )
            if not sku_match:
                clarifications.append(
                    CostClarificationItem(
                        field_name="vm_size",
                        message="VM size is ambiguous. Please confirm the exact SKU you want priced.",
                        suggested_values=["Standard_B4ms", "Standard_D4s_v5", "Standard_B2s"]
                    )
                )
            if os_image is None:
                clarifications.append(
                    CostClarificationItem(
                        field_name="os_image",
                        message="OS image is unclear. Please confirm the image family.",
                        suggested_values=["Ubuntu", "Windows Server"]
                    )
                )

        if "mysql" in normalized_text:
            quantity = self._extract_quantity(normalized_text, default=1)
            region = self._find_alias_value(normalized_text, self.REGION_ALIASES)
            deployment_model = self._find_alias_value(normalized_text, self.MYSQL_DEPLOYMENT_MODEL_ALIASES)
            tier = self._find_alias_value(normalized_text, self.MYSQL_TIER_ALIASES)
            compute_generation = self._find_alias_value(normalized_text, self.MYSQL_COMPUTE_GENERATION_ALIASES)
            unit_name = "GB/Month" if tier == "Storage" else "vCore Hour"

            mysql_descriptor_parts = [value for value in [deployment_model, tier, compute_generation] if value]
            mysql_descriptor = " ".join(mysql_descriptor_parts).strip() or None
            intents.append(
                CostResourceIntent(
                    resource_type="Azure Database for MySQL",
                    quantity=quantity,
                    region=region,
                    sku=tier,
                    deployment_model=deployment_model,
                    compute_generation=compute_generation,
                    unit_name=unit_name,
                    confidence="low" if mysql_descriptor is None else "medium"
                )
            )
            if not region:
                clarifications.append(
                    CostClarificationItem(
                        field_name="region",
                        message="Region is required for MySQL pricing.",
                        suggested_values=["eastus", "eastus2", "westus", "westus2", "centralus", "uksouth"]
                    )
                )
            if not deployment_model:
                clarifications.append(
                    CostClarificationItem(
                        field_name="deployment_model",
                        message="Choose the MySQL deployment model.",
                        suggested_values=["Single Server", "Flexible Server"]
                    )
                )
            if not tier:
                clarifications.append(
                    CostClarificationItem(
                        field_name="tier",
                        message="Choose the MySQL pricing tier.",
                        suggested_values=["Basic", "Storage", "Burstable", "General Purpose", "Memory Optimized", "Business Critical"]
                    )
                )
            if tier != "Storage" and not compute_generation:
                clarifications.append(
                    CostClarificationItem(
                        field_name="compute_generation",
                        message="Choose the MySQL compute generation.",
                        suggested_values=["Gen4", "Gen5", "Dsv3", "Dsv5", "Dsv6", "Dasv5", "Dasv6", "Ddsv5", "Ddsv6", "Esv6", "Easv6", "Eadsv5", "Eadsv6", "Edsv5", "Edsv6"]
                    )
                )

        if re.search(r"\bsql\b", normalized_text) and "mysql" not in normalized_text:
            quantity = self._extract_quantity(normalized_text, default=1)
            region = next((normalized for alias, normalized in self.REGION_ALIASES.items() if alias in normalized_text), None)
            intents.append(
                CostResourceIntent(
                    resource_type="Azure SQL Database",
                    quantity=quantity,
                    region=region,
                    sku="minimum" if "minimum" in normalized_text else None,
                    unit_name="vCore Hour",
                    confidence="low" if "minimum" in normalized_text else "medium"
                )
            )
            clarifications.append(
                CostClarificationItem(
                    field_name="sql_tier",
                    message="SQL Database configuration is ambiguous. Please confirm the tier or minimum configuration you want priced.",
                    suggested_values=["General Purpose", "Business Critical", "Serverless"]
                )
            )

        for phrase in self.AMBIGUOUS_PHRASES:
            if phrase in normalized_text:
                assumptions.append(f"Detected ambiguous phrase: {phrase}")

        needs_confirmation = bool(clarifications)
        return CostAnalysisResponse(
            raw_input=raw_input,
            normalized_text=normalized_text,
            intents=intents,
            needs_confirmation=needs_confirmation,
            clarification_items=clarifications,
            assumptions=assumptions,
            ready_to_price=not needs_confirmation and bool(intents)
        )


cost_analysis_service = CostAnalysisService()
