from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from edge_bridge.payload_builder import build_telemetry_payload


class PayloadBuilderTest(unittest.TestCase):
    def test_builds_canonical_payload_from_opcua_values(self) -> None:
        payload = build_telemetry_payload(
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
            source="opcua_edge_bridge",
            timestamp="2026-05-22T13:00:00Z",
            values={
                "rpm": 1780.2,
                "vibration_rms_mm_s": 1.9,
                "vibration_peak_g": 0.36,
                "temperature_c": 60.1,
                "ultrasound_db": 32.0,
                "horimeter_h": 1284.5,
                "kurtosis": 3.1,
                "crest_factor": 3.0,
                "health_score": 97.5,
                "severity": "normal",
                "failure_mode": "normal",
            },
        )

        metric_names = {metric["name"] for metric in payload["metrics"]}

        self.assertEqual(payload["tenant_id"], "cliente_demo")
        self.assertEqual(payload["plant_id"], "lab_virtual")
        self.assertEqual(payload["asset_id"], "motor_001")
        self.assertEqual(payload["source"], "opcua_edge_bridge")
        self.assertEqual(payload["timestamp"], "2026-05-22T13:00:00Z")
        self.assertEqual(payload["failure_mode_simulated"], "normal")
        self.assertEqual(len(payload["metrics"]), 9)
        self.assertIn("rpm", metric_names)
        self.assertIn("health_score", metric_names)
        self.assertNotIn("severity", metric_names)
        self.assertNotIn("failure_mode", metric_names)


if __name__ == "__main__":
    unittest.main()

