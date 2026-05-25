from __future__ import annotations

import unittest

from src.dashboard.alert_projection import (
    alerts_for_state,
    alerts_with_state_derived,
    derived_alert_from_state,
    severity_score,
)


class AlertProjectionTest(unittest.TestCase):
    def test_severity_score_falls_back_to_health_score(self) -> None:
        self.assertEqual(severity_score({"health_score": 32.8}), 67.2)

    def test_derived_alert_from_critical_state(self) -> None:
        alert = derived_alert_from_state(
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "compressor_001",
                "status_label": "CRÍTICO",
                "mode": "critical_failure_risk",
                "health_score": 32.8,
                "severity_score": 67.2,
                "diagnosis": "Risco crítico de parada.",
                "recommended_action": "Avaliar parada controlada.",
                "metrics": {
                    "vibration_rms_mm_s": {"value": 8.2, "unit": "mm/s"},
                    "temperature_c": {"value": 96.8, "unit": "C"},
                },
                "updated_at": "2026-05-23T18:52:31Z",
            }
        )

        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["asset_id"], "compressor_001")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["probable_cause"], "Risco crítico de parada.")
        self.assertTrue(alert["is_state_derived"])
        self.assertIn("Vibração RMS: 8.20 mm/s", alert["evidence"])

    def test_normal_state_does_not_create_derived_alert(self) -> None:
        self.assertIsNone(
            derived_alert_from_state(
                {
                    "asset_id": "motor_002",
                    "status_label": "NORMAL",
                    "health_score": 94.2,
                    "severity_score": 5.8,
                }
            )
        )

    def test_alerts_for_state_uses_formal_alert_when_present(self) -> None:
        formal = {"asset_id": "motor_001", "alert_type": "formal"}

        alerts = alerts_for_state(
            {"asset_id": "motor_001", "status_label": "CRÍTICO", "health_score": 30},
            [formal],
        )

        self.assertEqual(alerts, [formal])

    def test_alerts_with_state_derived_keeps_alerts_asset_scoped(self) -> None:
        alerts = alerts_with_state_derived(
            [{"asset_id": "motor_001", "alert_type": "formal"}],
            [
                {"asset_id": "motor_001", "status_label": "CRÍTICO", "health_score": 30},
                {"asset_id": "compressor_001", "status_label": "CRÍTICO", "health_score": 32.8},
                {"asset_id": "motor_002", "status_label": "NORMAL", "health_score": 94.2},
            ],
        )

        self.assertEqual([alert["asset_id"] for alert in alerts], ["motor_001", "compressor_001"])
        self.assertTrue(alerts[1]["is_state_derived"])


if __name__ == "__main__":
    unittest.main()
