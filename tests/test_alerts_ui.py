from __future__ import annotations

import unittest

from src.dashboard.alerts_ui import (
    alerts_df,
    csv_bytes,
    escalation_matrix_rows,
    escalation_rule,
    normalize_severity_label,
    pretty_metric,
    txt_bytes,
)


class AlertsUiDataFrameTest(unittest.TestCase):
    def test_pretty_metric_uses_commercial_labels(self) -> None:
        self.assertEqual(pretty_metric("inspecao_visual"), "Inspeção visual")
        self.assertEqual(pretty_metric("vibration_rms_mm_s"), "Vibração RMS")
        self.assertEqual(pretty_metric("custom_metric"), "custom_metric")

    def test_escalation_rule_maps_severity_to_operational_governance(self) -> None:
        self.assertEqual(normalize_severity_label("CRITICO"), "CRÍTICO")
        self.assertEqual(escalation_rule("ALERTA")["recipients"], "Manutenção")
        self.assertEqual(escalation_rule("ALERTA")["channels"], "Dashboard + Telegram")
        self.assertEqual(escalation_rule("CRÍTICO")["recipients"], "Manutenção + Gestor da planta")
        self.assertEqual(escalation_rule("CRÍTICO")["channels"], "Dashboard + Telegram + WhatsApp")
        self.assertEqual(escalation_rule("SEM COMUNICACAO")["recipients"], "Automação/TI")

        matrix = escalation_matrix_rows()
        self.assertEqual(matrix[0]["Severidade"], "ATENÇÃO")
        self.assertIn("Repetição / escalonamento", matrix[0])

    def test_alerts_df_normalizes_legacy_alert_processor_item(self) -> None:
        df = alerts_df(
            [
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#imbalance",
                    "alert_id": "cliente_demo#motor_001#imbalance#active",
                    "tenant_id": "cliente_demo",
                    "asset_id": "motor_001",
                    "alert_type": "imbalance",
                    "severity": "critical",
                    "status": "open",
                    "first_detected_at": "2026-05-23T12:00:00Z",
                    "updated_at": "2026-05-23T12:05:00Z",
                    "recommended_action": "Verificar balanceamento.",
                }
            ]
        )

        row = df.iloc[0]
        self.assertEqual(row["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(row["alert_key"], "ALERT#ACTIVE#imbalance")
        self.assertEqual(row["status_label"], "CRÍTICO")
        self.assertEqual(row["metric"], "imbalance")
        self.assertEqual(row["last_detected_at_local"], "23/05/2026 09:05:00")
        self.assertEqual(row["escalation_recipients"], "Manutenção + Gestor da planta")
        self.assertEqual(row["escalation_channels"], "Dashboard + Telegram + WhatsApp")

    def test_alerts_df_maps_communication_lost_to_it_escalation(self) -> None:
        df = alerts_df(
            [
                {
                    "tenant_asset": "cliente_demo#motor_001",
                    "alert_key": "open#communication_lost",
                    "alert_id": "alert-1",
                    "asset_id": "motor_001",
                    "alert_type": "communication_lost",
                    "severity": "warning",
                    "status": "open",
                    "first_detected_at": "2026-05-23T12:00:00Z",
                    "updated_at": "2026-05-23T12:05:00Z",
                }
            ]
        )

        row = df.iloc[0]
        self.assertEqual(row["status_label"], "SEM COMUNICAÇÃO")
        self.assertEqual(row["escalation_recipients"], "Automação/TI")
        self.assertEqual(row["escalation_channels"], "Dashboard + Telegram")
        self.assertIn("30 min", row["escalation_repeat_policy"])
        self.assertIn("60 min", row["escalation_repeat_policy"])

    def test_exports_hide_internal_priority_columns(self) -> None:
        df = alerts_df(
            [
                {
                    "tenant_asset": "cliente_demo#motor_001",
                    "alert_key": "open#e2e#vibration_rms_mm_s",
                    "alert_id": "alert-1",
                    "asset_id": "motor_001",
                    "metric": "vibration_rms_mm_s",
                    "status_label": "ALERTA",
                    "status": "open",
                    "first_detected_at": "2026-05-23T12:00:00Z",
                    "last_detected_at": "2026-05-23T12:05:00Z",
                }
            ]
        )

        csv_text = csv_bytes(df).decode("utf-8-sig")
        txt_text = txt_bytes(df).decode("utf-8")

        self.assertIn("vibration_rms_mm_s", csv_text)
        self.assertNotIn("status_priority", csv_text)
        self.assertNotIn("severity_priority", txt_text)


if __name__ == "__main__":
    unittest.main()
