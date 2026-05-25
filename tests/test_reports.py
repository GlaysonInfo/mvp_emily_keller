from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.dashboard.reports import (
    alert_rows,
    filter_alerts_by_period,
    individual_asset_report,
    period_bounds,
    plant_overview_report,
    risk_ranking_report,
    trend_report,
)


class ReportsTest(unittest.TestCase):
    def test_plant_overview_report_returns_executive_kpis(self) -> None:
        rows = plant_overview_report(
            [
                {"asset_id": "motor_001", "asset_name": "Motor 1", "status_label": "ATENÇÃO", "health_score": 71.9},
                {"asset_id": "compressor_001", "asset_name": "Compressor 1", "status_label": "CRÍTICO", "health_score": 32.8},
                {"asset_id": "motor_002", "asset_name": "Motor 2", "status_label": "NORMAL", "health_score": 94.2},
            ]
        )

        by_indicator = {row["Indicador"]: row for row in rows}

        self.assertEqual(by_indicator["Total de ativos monitorados"]["Valor"], 3)
        self.assertEqual(by_indicator["Ativos críticos"]["Valor"], 1)
        self.assertEqual(by_indicator["Ativo mais crítico"]["Valor"], "Compressor 1")

    def test_risk_ranking_report_orders_worst_first(self) -> None:
        rows = risk_ranking_report(
            [
                {"asset_id": "normal", "asset_name": "Normal", "status_label": "NORMAL", "health_score": 95},
                {"asset_id": "critical", "asset_name": "Critical", "status_label": "CRÍTICO", "severity_score": 67.2},
            ]
        )

        self.assertEqual(rows[0]["Ativo"], "critical")
        self.assertEqual(rows[0]["Posição"], 1)

    def test_individual_asset_report_includes_metrics_and_recommendation(self) -> None:
        rows = individual_asset_report(
            {
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "status_label": "ATENÇÃO",
                "health_score": 71.9,
                "recommended_action": "Verificar lubrificação.",
                "metrics": {
                    "rpm": {"value": 1779.57, "unit": "rpm"},
                    "temperature_c": {"value": 67.91, "unit": "C"},
                },
            }
        )
        by_field = {row["Campo"]: row["Valor"] for row in rows}

        self.assertEqual(by_field["Ativo"], "motor_001")
        self.assertEqual(by_field["Severity Score"], 28.1)
        self.assertEqual(by_field["Temperatura"], 67.91)
        self.assertEqual(by_field["Ação recomendada"], "Verificar lubrificação.")

    def test_filter_alerts_by_period_keeps_recent_alerts(self) -> None:
        now = datetime(2026, 5, 23, 18, 0, tzinfo=UTC)
        alerts = [
            {"alert_id": "recent", "updated_at": "2026-05-23T17:30:00Z"},
            {"alert_id": "old", "updated_at": "2026-05-22T17:30:00Z"},
        ]

        filtered = filter_alerts_by_period(alerts, "Última 1 hora", now=now)

        self.assertEqual([alert["alert_id"] for alert in filtered], ["recent"])

    def test_alert_rows_enriches_alerts_with_asset_area(self) -> None:
        rows = alert_rows(
            [
                {
                    "asset_id": "motor_001",
                    "alert_type": "lubrication_degradation",
                    "status": "open",
                    "severity": "warning",
                    "evidence": ["vibração elevada"],
                }
            ],
            [{"asset_id": "motor_001", "asset_name": "Motor Linha 1", "area": "Linha 1"}],
            active_only=True,
        )

        self.assertEqual(rows[0]["Nome"], "Motor Linha 1")
        self.assertEqual(rows[0]["Área"], "Linha 1")
        self.assertEqual(rows[0]["Evidências"], "vibração elevada")

    def test_trend_report_uses_daily_window_for_7_days(self) -> None:
        history_items = [
            {
                "ts_utc_minute": "2026-05-23T12:00:00Z",
                "status_label": "NORMAL",
                "rpm": 1800,
                "temperature_c": 50,
                "health_score": 90,
                "severity_score": 10,
            }
        ]

        rows = trend_report(history_items, period_label="Últimos 7 dias")

        self.assertEqual(rows[0]["amostras_no_periodo"], 1)
        self.assertEqual(rows[0]["rpm_media"], 1800)

    def test_period_bounds_uses_expected_duration(self) -> None:
        now = datetime(2026, 5, 23, 18, 0, tzinfo=UTC)
        start, end = period_bounds("Últimas 6 horas", now=now)

        self.assertEqual((end - start).total_seconds(), 6 * 60 * 60)


if __name__ == "__main__":
    unittest.main()
