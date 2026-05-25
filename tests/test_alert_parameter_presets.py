from __future__ import annotations

import unittest

from src.dashboard.alert_parameter_presets import (
    get_metric_label,
    get_parameter_preset,
    has_any_threshold,
    validate_parameter_rule,
)


class AlertParameterPresetsTest(unittest.TestCase):
    def test_temperature_preset_uses_expected_thresholds(self) -> None:
        preset = get_parameter_preset("temperature_c")

        self.assertEqual(preset["normal_max"], 70)
        self.assertEqual(preset["attention_min"], 70)
        self.assertEqual(preset["alert_min"], 85)
        self.assertEqual(preset["critical_min"], 100)
        self.assertTrue(preset["recommended_action"])

    def test_health_score_preset_uses_lower_is_worse_thresholds(self) -> None:
        preset = get_parameter_preset("health_score")

        self.assertEqual(preset["normal_min"], 75)
        self.assertEqual(preset["attention_max"], 75)
        self.assertEqual(preset["alert_max"], 55)
        self.assertEqual(preset["critical_max"], 35)

    def test_rpm_preset_uses_nominal_rpm_range(self) -> None:
        preset = get_parameter_preset("rpm", {"nominal_rpm": 1800})

        self.assertEqual(preset["normal_min"], 1656)
        self.assertEqual(preset["normal_max"], 1944)
        self.assertEqual(preset["critical_min"], 2124)
        self.assertEqual(preset["critical_max"], 1476)
        self.assertIn("1800", preset["note"])

    def test_validate_parameter_rule_rejects_zero_rule(self) -> None:
        errors = validate_parameter_rule(
            {
                "asset_id": "motor_001",
                "metric": "temperature_c",
                "recommended_action": "Verificar temperatura.",
                "persistence_min": 3,
            }
        )

        self.assertIn("Configure ao menos um limite", errors[0])

    def test_validate_parameter_rule_accepts_preset_rule(self) -> None:
        rule = {
            "asset_id": "motor_001",
            "metric": "vibration_rms_mm_s",
            **get_parameter_preset("vibration_rms_mm_s"),
        }

        self.assertTrue(has_any_threshold(rule))
        self.assertEqual(validate_parameter_rule(rule), [])
        self.assertEqual(get_metric_label("vibration_rms_mm_s"), "Vibração RMS")


if __name__ == "__main__":
    unittest.main()
