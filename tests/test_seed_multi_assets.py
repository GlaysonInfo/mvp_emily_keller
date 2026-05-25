from __future__ import annotations

import unittest
from decimal import Decimal

from seed_multi_assets import build_state_item


class SeedMultiAssetsTest(unittest.TestCase):
    def test_build_state_item_matches_latest_state_contract(self) -> None:
        item = build_state_item(
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "mode": "lubrication_degradation",
                "health_score": 71.9,
                "metrics": {
                    "rpm": 1779.57,
                    "temperature_c": 67.91,
                    "hourmeter_h": 1284.03,
                },
            },
            updated_at="2026-05-23T18:37:41Z",
        )

        self.assertEqual(item["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(item["sk"], "LATEST")
        self.assertEqual(item["tenant_plant"], "cliente_demo#lab_virtual")
        self.assertEqual(item["failure_mode_simulated"], "lubrication_degradation")
        self.assertEqual(item["metrics"]["rpm"], {"value": Decimal("1779.57"), "unit": "rpm"})
        self.assertEqual(item["metrics"]["temperature_c"], {"value": Decimal("67.91"), "unit": "C"})
        self.assertTrue(item["is_demo_multiasset"])


if __name__ == "__main__":
    unittest.main()
