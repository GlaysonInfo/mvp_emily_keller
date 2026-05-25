from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.dashboard.escalation_engine import (
    alert_age_minutes,
    apply_escalation_rule,
    escalation_matrix_rows,
    normalize_severity_label,
    simulate_alerts,
)


class EscalationEngineTest(unittest.TestCase):
    def test_apply_rule_flags_repeat_and_escalation_for_old_critical_alert(self) -> None:
        now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        decision = apply_escalation_rule(
            {
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "metric": "vibration_rms_mm_s",
                "status_label": "CRÍTICO",
                "status": "open",
                "first_detected_at": "2026-05-24T11:30:00Z",
                "recommended_action": "Inspecionar base e acoplamento.",
            },
            now=now,
        )

        self.assertEqual(decision["rule_id"], "critical_immediate_escalation")
        self.assertEqual(decision["channels"], "Dashboard + Telegram + WhatsApp")
        self.assertEqual(decision["contact_groups"], "Manutenção + Gestor da planta")
        self.assertEqual(decision["age_minutes"], 30)
        self.assertTrue(decision["should_repeat"])
        self.assertTrue(decision["should_escalate"])
        self.assertIn("CRÍTICO", decision["message"])
        self.assertIn("Ação imediata", decision["message"])

    def test_acknowledged_alert_can_repeat_but_does_not_escalate(self) -> None:
        now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        decision = apply_escalation_rule(
            {
                "asset_id": "motor_001",
                "status_label": "ALERTA",
                "status": "acknowledged",
                "first_detected_at": "2026-05-24T10:55:00Z",
            },
            now=now,
        )

        self.assertTrue(decision["should_repeat"])
        self.assertFalse(decision["should_escalate"])

    def test_communication_lost_uses_it_rule(self) -> None:
        decision = apply_escalation_rule(
            {
                "asset_id": "gateway_001",
                "alert_type": "communication_lost",
                "severity": "warning",
                "status": "open",
            }
        )

        self.assertEqual(normalize_severity_label("SEM COMUNICACAO"), "SEM COMUNICAÇÃO")
        self.assertEqual(decision["severity"], "SEM COMUNICAÇÃO")
        self.assertEqual(decision["contact_groups"], "Automação/TI")
        self.assertEqual(decision["repeat_after_minutes"], 30)
        self.assertEqual(decision["escalate_after_minutes"], 60)

    def test_simulation_and_matrix_rows_are_operational(self) -> None:
        decisions = simulate_alerts([{"asset_id": "motor_001", "status_label": "ATENÇÃO"}])
        rows = escalation_matrix_rows()

        self.assertEqual(decisions[0]["rule_id"], "attention_dashboard_only")
        self.assertEqual(rows[0]["Severidade"], "ATENÇÃO")
        self.assertIn("Canal", rows[0])

    def test_attention_variants_use_attention_rule(self) -> None:
        decision = apply_escalation_rule({"asset_id": "motor_001", "status_label": "ATENÇÃO ALTA"})

        self.assertEqual(normalize_severity_label("ATENCAO ALTA"), "ATENÇÃO")
        self.assertEqual(decision["severity"], "ATENÇÃO")
        self.assertEqual(decision["rule_id"], "attention_dashboard_only")
        self.assertEqual(decision["channels"], "Dashboard")

    def test_alert_age_returns_zero_for_invalid_timestamp(self) -> None:
        self.assertEqual(alert_age_minutes({"first_detected_at": "invalid"}), 0)


if __name__ == "__main__":
    unittest.main()
