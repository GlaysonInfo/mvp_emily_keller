from __future__ import annotations

import unittest

from src.dashboard.history_export import minute_rows, rows_to_csv, rows_to_txt, summary_rows


class HistoryExportTest(unittest.TestCase):
    def test_minute_rows_formats_local_and_utc_time(self) -> None:
        rows = minute_rows(
            [
                {
                    "ts_utc_minute": "2026-05-23T12:11:00Z",
                    "tenant_id": "cliente_demo",
                    "plant_id": "lab_virtual",
                    "asset_id": "motor_001",
                    "temperature_c": 67.91,
                }
            ],
            timezone_str="America/Sao_Paulo",
        )

        self.assertEqual(rows[0]["data_hora_utc"], "2026-05-23T12:11:00Z")
        self.assertEqual(rows[0]["data_hora"], "23/05/2026 09:11:00")
        self.assertEqual(rows[0]["temperature_c"], 67.91)

    def test_summary_rows_aggregate_by_window(self) -> None:
        items = [
            {
                "ts_utc_minute": "2026-05-23T12:00:00Z",
                "mode": "normal_operation",
                "status_label": "NORMAL",
                "rpm": 1780.0,
                "vibration_rms_mm_s": 2.0,
                "temperature_c": 60.0,
                "ultrasound_db": 32.0,
                "health_score": 90.0,
                "severity_score": 10.0,
                "hourmeter_h": 100.0,
            },
            {
                "ts_utc_minute": "2026-05-23T12:01:00Z",
                "mode": "critical_failure_risk",
                "status_label": "CRÍTICO",
                "rpm": 1760.0,
                "vibration_rms_mm_s": 8.0,
                "temperature_c": 96.0,
                "ultrasound_db": 68.0,
                "health_score": 30.0,
                "severity_score": 70.0,
                "hourmeter_h": 100.1,
            },
        ]

        rows = summary_rows(items, window_hours=1, timezone_str="America/Sao_Paulo")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amostras_no_periodo"], 2)
        self.assertEqual(rows[0]["modo_final"], "critical_failure_risk")
        self.assertEqual(rows[0]["vibracao_rms_max_mm_s"], 8.0)
        self.assertEqual(rows[0]["health_score_min"], 30.0)
        self.assertEqual(rows[0]["severity_score_max"], 70.0)
        self.assertEqual(rows[0]["minutos_com_alerta"], 1)
        self.assertEqual(rows[0]["minutos_criticos"], 1)

    def test_export_csv_and_txt(self) -> None:
        rows = [{"data_hora": "23/05/2026 09:11:00", "rpm": 1780.0}]

        csv_data = rows_to_csv(rows, columns=["data_hora", "rpm"])
        txt_data = rows_to_txt(rows, title="Histórico operacional")

        self.assertIn("data_hora,rpm", csv_data)
        self.assertIn("1780.0", csv_data)
        self.assertIn("Histórico operacional", txt_data)
        self.assertIn("Registro 1", txt_data)


if __name__ == "__main__":
    unittest.main()
