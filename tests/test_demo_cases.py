from __future__ import annotations

import unittest
from decimal import Decimal

from src.dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, get_demo_case, load_demo_cases


class DemoCasesTest(unittest.TestCase):
    def test_load_demo_cases_returns_expected_order(self) -> None:
        cases = load_demo_cases()

        self.assertEqual(len(cases), 8)
        self.assertEqual(cases[0]["case_id"], "normal_operation")
        self.assertEqual(cases[-1]["case_id"], "communication_lost")

    def test_build_latest_state_item_matches_dashboard_contract(self) -> None:
        case = get_demo_case("lubrication_degradation")

        item = build_latest_state_item(
            case,
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
            updated_at="2026-05-23T13:45:24Z",
        )

        self.assertEqual(item["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(item["sk"], "LATEST")
        self.assertEqual(item["failure_mode_simulated"], "lubrication_degradation")
        self.assertEqual(item["metrics"]["temperature_c"], {"value": Decimal("67.91"), "unit": "C"})
        self.assertEqual(item["metrics"]["horimeter_h"], {"value": Decimal("1284.03"), "unit": "h"})
        self.assertEqual(item["severity_score"], Decimal("28.1"))
        self.assertTrue(item["is_demo_case"])

    def test_build_demo_alert_item_uses_active_alert_key(self) -> None:
        case = get_demo_case("bearing_fault_initial")

        alert = build_demo_alert_item(
            case,
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
            payload_updated_at="2026-05-23T13:45:24Z",
        )

        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["sk"], "ALERT#ACTIVE#bearing_fault_initial")
        self.assertEqual(alert["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(alert["alert_key"], "open#demo#bearing_fault_initial")
        self.assertEqual(alert["metric"], "ultrasound_db")
        self.assertEqual(alert["status_label"], "ALERTA")
        self.assertEqual(alert["asset_name"], "motor_001")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["last_detected_at"], "2026-05-23T13:45:24Z")
        self.assertEqual(alert["last_payload_timestamp"], "2026-05-23T13:45:24Z")
        self.assertTrue(alert["recommended_action"])
        self.assertTrue(alert["is_demo_case"])
        self.assertGreater(len(alert["evidence"]), 0)
        self.assertGreater(len(alert["timeline"]), 0)

    def test_normal_operation_has_no_active_alert(self) -> None:
        case = get_demo_case("normal_operation")

        self.assertIsNone(build_demo_alert_item(case))


if __name__ == "__main__":
    unittest.main()
