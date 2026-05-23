from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rules_engine.diagnostics import extract_metric_values
from rules_engine.rules import evaluate_payload


def canonical_payload(metrics: dict[str, float], failure_mode: str = "normal") -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "motor_001",
        "source": "opcua_edge_bridge",
        "timestamp": "2026-05-23T03:02:29.019870Z",
        "failure_mode_simulated": failure_mode,
        "metrics": [
            {"name": name, "value": value, "unit": "unit"}
            for name, value in metrics.items()
        ],
    }


class RulesEngineTest(unittest.TestCase):
    def test_normal_payload_does_not_generate_alert(self) -> None:
        payload = canonical_payload(
            {
                "rpm": 1780.0,
                "vibration_rms_mm_s": 2.0,
                "temperature_c": 60.0,
                "ultrasound_db": 32.0,
                "kurtosis": 3.1,
                "crest_factor": 3.0,
                "health_score": 96.0,
            }
        )

        alerts = evaluate_payload(payload)

        self.assertEqual(alerts, [])

    def test_lubrication_degradation_generates_warning(self) -> None:
        payload = canonical_payload(
            {
                "vibration_rms_mm_s": 3.2,
                "temperature_c": 68.0,
                "ultrasound_db": 42.0,
                "kurtosis": 3.2,
                "crest_factor": 3.1,
            },
            failure_mode="lubrication_degradation",
        )

        alerts = evaluate_payload(payload)

        self.assertEqual(len(alerts), 1)
        alert = alerts[0].to_dict()
        self.assertEqual(alert["alert_type"], "lubrication_degradation")
        self.assertEqual(alert["severity"], "warning")
        self.assertEqual(alert["status"], "open")
        self.assertEqual(alert["asset_id"], "motor_001")
        self.assertIn("probable_cause", alert)
        self.assertIn("evidence", alert)
        self.assertIn("recommended_action", alert)

    def test_imbalance_generates_critical_alert(self) -> None:
        payload = canonical_payload(
            {
                "vibration_rms_mm_s": 4.4,
                "temperature_c": 63.0,
                "ultrasound_db": 33.0,
                "kurtosis": 3.4,
                "crest_factor": 3.2,
            },
            failure_mode="imbalance",
        )

        alerts = evaluate_payload(payload)

        self.assertEqual(len(alerts), 1)
        alert = alerts[0].to_dict()
        self.assertEqual(alert["alert_type"], "imbalance")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["probable_cause"], "Possivel desbalanceamento")
        self.assertGreaterEqual(alert["confidence"], 0.8)
        self.assertIn("Vibracao RMS acima de 4.0 mm/s", alert["evidence"])

    def test_bearing_fault_generates_critical_alert(self) -> None:
        payload = canonical_payload(
            {
                "vibration_rms_mm_s": 3.8,
                "temperature_c": 64.0,
                "ultrasound_db": 35.0,
                "kurtosis": 5.4,
                "crest_factor": 4.8,
            },
            failure_mode="bearing_fault",
        )

        alerts = evaluate_payload(payload)

        self.assertEqual(len(alerts), 1)
        alert = alerts[0].to_dict()
        self.assertEqual(alert["alert_type"], "bearing_fault")
        self.assertEqual(alert["severity"], "critical")
        self.assertIn("Kurtosis acima ou igual a 5.0", alert["evidence"])

    def test_extract_metric_values_accepts_dynamodb_latest_shape(self) -> None:
        payload = {
            "metrics": {
                "rpm": {"value": Decimal("1778.51"), "unit": "rpm"},
                "vibration_rms_mm_s": {"value": Decimal("4.44"), "unit": "mm/s"},
                "failure_mode": {"value": "imbalance", "unit": "text"},
            }
        }

        values = extract_metric_values(payload)

        self.assertEqual(values["rpm"], 1778.51)
        self.assertEqual(values["vibration_rms_mm_s"], 4.44)
        self.assertNotIn("failure_mode", values)


if __name__ == "__main__":
    unittest.main()
