import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.base import Base
from app.database.models import CostEstimate
from app.database.models import CostEstimateLine
from app.database.models import PricingLookupKey
from app.database.models import PricingSnapshot
from app.services.azure_retail_prices_service import RetailPriceQuery
from app.services.azure_retail_prices_service import azure_retail_prices_service
from app.services.cost_analysis_service import cost_analysis_service
from app.services.cost_pricing_service import cost_pricing_service
from app.services.price_cache_service import price_cache_service


class CostCacheTests(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_build_filter_generates_expected_odata_clause(self):
        query = RetailPriceQuery(
            service_name="Virtual Machines",
            arm_region_name="eastus",
            arm_sku_name="Standard_B4ms"
        )

        filter_expr = azure_retail_prices_service.build_filter(query)

        self.assertIn("serviceName eq 'Virtual Machines'", filter_expr)
        self.assertIn("armRegionName eq 'eastus'", filter_expr)
        self.assertIn("armSkuName eq 'Standard_B4ms'", filter_expr)
        self.assertIn("priceType eq 'Consumption'", filter_expr)

    def test_select_best_item_prefers_more_specific_match(self):
        query = RetailPriceQuery(
            service_name="Virtual Machines",
            arm_region_name="eastus",
            arm_sku_name="Standard_B4ms",
            sku_name="B4ms"
        )

        items = [
            {
                "serviceName": "Virtual Machines",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "skuName": "B2s",
                "retailPrice": 0.05,
                "type": "Consumption"
            },
            {
                "serviceName": "Virtual Machines",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B4ms",
                "skuName": "B4ms",
                "retailPrice": 0.08,
                "type": "Consumption"
            }
        ]

        selected = azure_retail_prices_service.select_best_item(items, query)

        self.assertIsNotNone(selected)
        self.assertEqual(selected["armSkuName"], "Standard_B4ms")

    def test_lookup_snapshot_estimate_lifecycle(self):
        lookup = price_cache_service.get_or_create_lookup_key(
            db=self.db,
            spec={
                "service_name": "Virtual Machines",
                "arm_sku": "Standard_B4ms",
                "meter_name": "B4ms",
                "product_name": "Virtual Machines Bsv2 Series",
                "region": "eastus",
                "currency_code": "USD",
                "unit_of_measure": "1 Hour",
                "tier": "Standard"
            }
        )

        snapshot = price_cache_service.refresh_lookup_key(
            db=self.db,
            lookup_key=lookup,
            api_url="https://prices.azure.com/api/retail/prices",
            raw_payload={
                "id": "vm-row-001",
                "skuName": "Standard_B4ms",
                "productName": "Virtual Machines Bsv2 Series",
                "meterName": "B4ms",
                "armRegionName": "eastus",
                "currencyCode": "USD",
                "unitOfMeasure": "1 Hour",
                "type": "Consumption",
                "retailPrice": 0.08,
                "unitPrice": 0.08
            },
            request_params={
                "service_name": "Virtual Machines",
                "region": "eastus"
            }
        )

        estimate = price_cache_service.create_estimate(
            db=self.db,
            raw_input="Estimate 100 VM hours",
            normalized_request={
                "resources": [
                    {
                        "resource_type": "Virtual Machine",
                        "quantity": 100
                    }
                ]
            },
            user_id=1,
            source_session_id=1,
            region="eastus",
            currency_code="USD",
            assumptions={"note": "unit test"},
            confidence="high"
        )

        line = price_cache_service.add_estimate_line(
            db=self.db,
            estimate_id=estimate.id,
            lookup_key_id=lookup.id,
            snapshot_id=snapshot.id,
            resource_type="Virtual Machine",
            resource_name="vm-group",
            quantity=100,
            unit_name="hour",
            hourly_rate=8.0,
            monthly_rate=5840.0,
            matched_exactly=True,
            match_confidence="high",
            assumptions={"region": "eastus"}
        )

        final_estimate = price_cache_service.finalize_estimate(
            db=self.db,
            estimate_id=estimate.id
        )

        self.assertIsInstance(lookup, PricingLookupKey)
        self.assertIsInstance(snapshot, PricingSnapshot)
        self.assertIsInstance(line, CostEstimateLine)
        self.assertIsInstance(final_estimate, CostEstimate)
        self.assertEqual(final_estimate.status, "COMPLETE")
        self.assertAlmostEqual(float(final_estimate.total_hourly), 8.0)
        self.assertAlmostEqual(float(final_estimate.total_monthly), 5840.0)
        self.assertEqual(final_estimate.lines[0].snapshot_id, snapshot.id)

        current_snapshot = price_cache_service.get_current_snapshot(
            db=self.db,
            lookup_key_id=lookup.id
        )
        self.assertEqual(current_snapshot.id, snapshot.id)
        self.assertTrue(current_snapshot.is_current)

    def test_cost_pricing_service_resolves_analysis_into_estimate(self):
        analysis = cost_analysis_service.analyze(
            "Estimate 2 Standard_B4ms virtual machines in east us using Ubuntu"
        )

        best_item = {
            "id": "vm-row-002",
            "skuName": "Standard_B4ms",
            "productName": "Virtual Machines Bsv2 Series",
            "meterName": "B4ms",
            "armRegionName": "eastus",
            "currencyCode": "USD",
            "unitOfMeasure": "1 Hour",
            "type": "Consumption",
            "retailPrice": 0.08,
            "unitPrice": 0.08
        }

        with patch(
            "app.services.cost_pricing_service.azure_retail_prices_service.fetch_best_item",
            return_value=(best_item, [best_item], "https://prices.azure.com/api/retail/prices", {})
        ):
            _, estimate = cost_pricing_service.create_estimate_from_analysis(
                db=self.db,
                raw_input="Estimate 2 Standard_B4ms virtual machines in east us using Ubuntu",
                analysis=analysis
            )

        self.assertIsNotNone(estimate)
        self.assertEqual(estimate.kind if hasattr(estimate, "kind") else "estimate", "estimate")
        self.assertGreaterEqual(len(estimate.lines), 1)
        self.assertAlmostEqual(float(estimate.total_hourly), 0.16)
        self.assertAlmostEqual(float(estimate.total_monthly), 116.8)


if __name__ == "__main__":
    unittest.main()
