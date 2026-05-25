from __future__ import annotations

import unittest
from decimal import Decimal

from src.dashboard.plant_overview_ui import filter_rows, plant_kpis, state_to_row, states_to_rows


class PlantOverviewUiTest(unittest.TestCase):
    def test_state_to_row_accepts_nested_and_flat_metrics(self) -> None:
        row = state_to_row(
            {
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "asset_type": "Motor elétrico",
                "area": "Linha 1",
                "criticality": "Alta",
                "status_label": "ATENÇÃO",
                "mode_label": "Degradação de lubrificação",
                "health_score": Decimal("71.9"),
                "metrics": {
                    "vibration_rms_mm_s": {"value": Decimal("2.96"), "unit": "mm/s"},
                    "temperature_c": Decimal("67.91"),
                },
            }
        )

        self.assertEqual(row["asset_id"], "motor_001")
        self.assertEqual(row["severity_score"], 28.1)
        self.assertEqual(row["vibration_rms_mm_s"], 2.96)
        self.assertEqual(row["temperature_c"], 67.91)

    def test_states_to_rows_sorts_by_operational_risk(self) -> None:
        rows = states_to_rows(
            [
                {"asset_id": "normal", "status_label": "NORMAL", "health_score": 95},
                {"asset_id": "critical", "status_label": "CRÍTICO", "severity_score": 70},
                {"asset_id": "alert", "status_label": "ALERTA", "severity_score": 50},
            ]
        )

        self.assertEqual([row["asset_id"] for row in rows], ["critical", "alert", "normal"])

    def test_plant_kpis_counts_statuses(self) -> None:
        rows = states_to_rows(
            [
                {"asset_id": "a", "status_label": "NORMAL", "health_score": 90},
                {"asset_id": "b", "status_label": "ATENÇÃO", "health_score": 70},
                {"asset_id": "c", "status_label": "ALERTA", "health_score": 50},
                {"asset_id": "d", "status_label": "CRÍTICO", "health_score": 30},
                {"asset_id": "e", "status_label": "SEM COMUNICAÇÃO"},
            ]
        )

        kpis = plant_kpis(rows)

        self.assertEqual(kpis["total"], 5)
        self.assertEqual(kpis["normal"], 1)
        self.assertEqual(kpis["attention"], 1)
        self.assertEqual(kpis["alert"], 1)
        self.assertEqual(kpis["critical"], 1)
        self.assertEqual(kpis["offline"], 1)
        self.assertEqual(kpis["health_mean"], 60)

    def test_filter_rows_filters_by_area_and_status(self) -> None:
        rows = [
            {"asset_id": "a", "status_label": "NORMAL", "area": "Linha 1", "asset_type": "Motor", "criticality": "Alta"},
            {"asset_id": "b", "status_label": "ALERTA", "area": "Linha 2", "asset_type": "Bomba", "criticality": "Crítica"},
        ]

        filtered = filter_rows(rows, status="ALERTA", area="Linha 2")

        self.assertEqual(filtered, [rows[1]])


if __name__ == "__main__":
    unittest.main()
