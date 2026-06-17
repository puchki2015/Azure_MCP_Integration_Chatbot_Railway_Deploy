import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.cost_analysis_service import cost_analysis_service


class CostAnalysisTests(unittest.TestCase):

    def test_analyze_vm_and_sql_request_requests_confirmation(self):
        result = cost_analysis_service.analyze(
            "provide me the cost estimates for 100 vms in east us location of size B4ms and 2 azure sql database with minimum configuration"
        )

        self.assertTrue(result.needs_confirmation)
        self.assertFalse(result.ready_to_price)
        self.assertGreaterEqual(len(result.intents), 2)
        self.assertGreaterEqual(len(result.clarification_items), 1)

    def test_analyze_clear_vm_request_is_more_specific(self):
        result = cost_analysis_service.analyze(
            "Estimate 200 Standard_B4ms virtual machines in east us using Ubuntu"
        )

        self.assertFalse(result.needs_confirmation)
        self.assertTrue(result.ready_to_price)
        self.assertGreaterEqual(len(result.intents), 1)
        self.assertFalse(any(item.field_name == "os_image" for item in result.clarification_items))

    def test_analyze_mysql_request_preserves_mysql_fields(self):
        result = cost_analysis_service.analyze(
            "provide me the estimate of MySQL Single Server General Purpose Compute Gen5 in UK South"
        )

        self.assertTrue(result.ready_to_price)
        self.assertEqual(len(result.intents), 1)
        intent = result.intents[0]
        self.assertEqual(intent.resource_type, "Azure Database for MySQL")
        self.assertEqual(intent.region, "uksouth")
        self.assertEqual(intent.deployment_model, "Single Server")
        self.assertEqual(intent.sku, "General Purpose")
        self.assertEqual(intent.compute_generation, "Gen5")
        self.assertFalse(any(item.field_name == "mysql_configuration" for item in result.clarification_items))
        self.assertFalse(any(item.field_name == "deployment_model" for item in result.clarification_items))
        self.assertFalse(any(item.field_name == "tier" for item in result.clarification_items))
        self.assertFalse(any(item.field_name == "compute_generation" for item in result.clarification_items))

    def test_analyze_mysql_request_parses_dropdown_style_values(self):
        result = cost_analysis_service.analyze(
            "Price Azure Database for MySQL Flexible Server General Purpose Ddsv6 in west us"
        )

        self.assertTrue(result.ready_to_price)
        self.assertEqual(len(result.intents), 1)
        intent = result.intents[0]
        self.assertEqual(intent.resource_type, "Azure Database for MySQL")
        self.assertEqual(intent.region, "westus")
        self.assertEqual(intent.deployment_model, "Flexible Server")
        self.assertEqual(intent.sku, "General Purpose")
        self.assertEqual(intent.compute_generation, "Ddsv6")
        self.assertFalse(result.clarification_items)

    def test_analyze_mysql_request_requests_only_missing_fields(self):
        result = cost_analysis_service.analyze(
            "Price Azure Database for MySQL in west us"
        )

        self.assertTrue(result.needs_confirmation)
        self.assertFalse(result.ready_to_price)
        field_names = {item.field_name for item in result.clarification_items}
        self.assertSetEqual(field_names, {"deployment_model", "tier", "compute_generation"})


if __name__ == "__main__":
    unittest.main()
