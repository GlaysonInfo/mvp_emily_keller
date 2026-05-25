from __future__ import annotations

import unittest

from src.dashboard.intelligence_engine import (
    calculate_metric_anomaly,
    calculate_operational_intelligence,
    current_state_to_metrics,
    intelligence_to_report_text,
    normalize_history_items,
)


def history_items() -> list[dict]:
    rows = []
    for index in range(5):
        rows.append(
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "status_label": "NORMAL",
                "ts_utc_minute": f"2026-05-24T10:0{index}:00Z",
                "temperature_c": 58 + index * 0.2,
                "vibration_rms_mm_s": 2.1,
                "ultrasound_db": 32,
                "health_score": 92,
                "severity_score": 8,
            }
        )
    return rows


class IntelligenceEngineTest(unittest.TestCase):
    def test_current_state_unwraps_nested_metric_values(self) -> None:
        metrics = current_state_to_metrics(
            {
                "metrics": {
                    "temperature_c": {"value": "76.5", "unit": "C"},
                    "vibration_rms_mm_s": {"value": 2.4, "unit": "mm/s"},
                },
                "health_score": 70,
            }
        )

        self.assertEqual(metrics["temperature_c"], 76.5)
        self.assertEqual(metrics["vibration_rms_mm_s"], 2.4)
        self.assertEqual(metrics["health_score"], 70)

    def test_baseline_prefers_healthy_history_and_detects_thermal_anomaly(self) -> None:
        result = calculate_operational_intelligence(
            history_items(),
            {
                "asset_id": "motor_001",
                "status_label": "ATENÇÃO",
                "metrics": {
                    "temperature_c": {"value": 76},
                    "vibration_rms_mm_s": {"value": 2.2},
                    "ultrasound_db": {"value": 43},
                },
                "health_score": 70,
                "severity_score": 30,
            },
        )

        temperature = next(item for item in result["metric_results"] if item["metric"] == "temperature_c")

        self.assertEqual(result["history_samples"], 5)
        self.assertEqual(result["analysis_source"], "baseline_ml")
        self.assertTrue(result["baseline_ready"])
        self.assertEqual(result["baseline"]["temperature_c"]["source"], "healthy_only")
        self.assertGreater(temperature["score"], 80)
        self.assertEqual(temperature["level"], "CRÍTICO")
        self.assertEqual(result["recommendation"]["primary_hypothesis"], "Aquecimento anormal")

    def test_falls_back_to_current_state_when_history_is_missing(self) -> None:
        result = calculate_operational_intelligence(
            [],
            {
                "asset_id": "motor_001",
                "status_label": "ATENÇÃO",
                "health_score": 71.9,
                "severity_score": 28.1,
            },
        )

        self.assertEqual(result["history_samples"], 0)
        self.assertFalse(result["baseline_ready"])
        self.assertEqual(result["analysis_source"], "state_fallback")
        self.assertEqual(result["score_source"], "state_fallback")
        self.assertEqual(result["anomaly_score"], 28.1)
        self.assertEqual(result["anomaly_level"], "ATENÇÃO")

    def test_lower_health_score_is_treated_as_risk(self) -> None:
        anomaly = calculate_metric_anomaly(
            "health_score",
            60,
            {"mean": 92, "std": 2, "samples": 5},
        )

        self.assertGreater(anomaly["score"], 50)
        self.assertIn("abaixo", anomaly["explanation"])

    def test_history_dataframe_sorts_by_timestamp(self) -> None:
        df = normalize_history_items(
            [
                {"ts_utc_minute": "2026-05-24T10:02:00Z", "temperature_c": 60},
                {"ts_utc_minute": "2026-05-24T10:01:00Z", "temperature_c": 58},
            ]
        )

        self.assertEqual(list(df["temperature_c"]), [58, 60])

    def test_report_contains_recommendation_sections(self) -> None:
        result = calculate_operational_intelligence(history_items(), {"asset_id": "motor_001", "temperature_c": 76})
        report = intelligence_to_report_text(result)

        self.assertIn("RELATÓRIO DE INTELIGÊNCIA OPERACIONAL", report)
        self.assertIn("HIPÓTESE PRINCIPAL", report)
        self.assertIn("AÇÕES IMEDIATAS", report)


if __name__ == "__main__":
    unittest.main()
