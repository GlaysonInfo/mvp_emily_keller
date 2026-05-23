from __future__ import annotations

import unittest
from decimal import Decimal

from src.dashboard.echarts_gauge_components import (
    axis_segments,
    clamp,
    gauge_values,
    make_gauge_options,
    metric_number,
    percent,
    severity_score,
    status_by_thresholds,
)


class EchartsGaugeComponentsTest(unittest.TestCase):
    def test_metric_number_reads_dynamodb_metric_shape(self) -> None:
        latest_state = {
            "metrics": {
                "temperature_c": {"value": Decimal("67.91"), "unit": "C"},
            }
        }

        self.assertEqual(metric_number(latest_state, "temperature_c"), 67.91)

    def test_metric_number_prefers_top_level_fallbacks(self) -> None:
        latest_state = {
            "severity_score": Decimal("28.1"),
            "metrics": {
                "severity": {"value": Decimal("55.0"), "unit": "score"},
            },
        }

        self.assertEqual(metric_number(latest_state, "severity_score", "severity"), 28.1)

    def test_status_thresholds_support_inverse_health_score(self) -> None:
        self.assertEqual(status_by_thresholds(91.0, 75, 55, 35, inverse=True), "normal")
        self.assertEqual(status_by_thresholds(50.0, 75, 55, 35, inverse=True), "alert")
        self.assertEqual(status_by_thresholds(31.0, 75, 55, 35, inverse=True), "critical")

    def test_severity_score_falls_back_to_inverse_health_score(self) -> None:
        latest_state = {"metrics": {}}

        self.assertEqual(severity_score(latest_state, 71.9), 28.1)

    def test_clamp_and_percent_keep_values_inside_bounds(self) -> None:
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(11, 0, 10), 10)
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(percent(5, 0, 10), 0.5)

    def test_axis_segments_are_normalized_for_inverse_gauge(self) -> None:
        segments = axis_segments(0, 100, 75, 55, 35, inverse=True)

        self.assertEqual(segments[0][0], 0.35)
        self.assertEqual(segments[-1][0], 1)

    def test_make_gauge_options_uses_three_column_friendly_geometry(self) -> None:
        options = make_gauge_options(
            title="Vibração RMS",
            value=5.25,
            unit="mm/s",
            min_value=0,
            max_value=10,
            attention=2.8,
            alert=4.5,
            critical=7.1,
            decimals=2,
        )
        series = options["series"][0]

        self.assertEqual(series["pointer"]["length"], "52%")
        self.assertEqual(series["detail"]["offsetCenter"], [0, "42%"])
        self.assertEqual(options["graphic"][0]["style"]["text"], "ALERTA")

    def test_gauge_values_include_severity_score_fallback(self) -> None:
        latest_state = {
            "metrics": {
                "health_score": {"value": Decimal("71.9"), "unit": "score"},
            }
        }

        values = {gauge["key"]: gauge["value"] for gauge in gauge_values(latest_state)}

        self.assertEqual(values["health_score"], 71.9)
        self.assertEqual(values["severity_score"], 28.1)


if __name__ == "__main__":
    unittest.main()
