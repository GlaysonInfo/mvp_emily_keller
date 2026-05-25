from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.dashboard.escalation_repository import DEFAULT_ESCALATION_DATA
from src.dashboard.notification_outbox_engine import (
    build_outbox_items,
    merge_alert_sources,
    normalize_current_state_as_alert,
    normalize_states_as_alerts,
    notification_kind,
    outbox_kpis,
)
from src.dashboard.notification_outbox_repository import NotificationOutboxRepository


class NotificationOutboxTest(unittest.TestCase):
    def test_normalize_current_state_as_alert_creates_attention_candidate(self) -> None:
        alert = normalize_current_state_as_alert(
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "status_label": "ATENÇÃO",
                "severity_score": 30.0,
                "updated_at": "2026-05-24T12:00:00Z",
            }
        )

        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["source"], "current_state")
        self.assertEqual(alert["status"], "open")
        self.assertEqual(alert["status_label"], "ATENÇÃO")
        self.assertEqual(alert["metric"], "condition_state")

    def test_normalize_states_as_alerts_ignores_normal_state(self) -> None:
        alerts = normalize_states_as_alerts(
            [
                {"asset_id": "normal", "status_label": "NORMAL"},
                {"asset_id": "risk", "status_label": "ALERTA"},
            ]
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["asset_id"], "risk")

    def test_merge_alert_sources_adds_current_state_when_alert_table_is_empty(self) -> None:
        alerts = merge_alert_sources(
            [],
            [
                {
                    "tenant_id": "cliente_demo",
                    "plant_id": "lab_virtual",
                    "asset_id": "motor_001",
                    "status_label": "ATENÇÃO",
                    "updated_at": "2026-05-24T12:00:00Z",
                }
            ],
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["source"], "current_state")

    def test_build_outbox_items_uses_escalation_matrix(self) -> None:
        items = build_outbox_items(
            [
                {
                    "asset_id": "motor_001",
                    "asset_name": "Motor Linha 1",
                    "status_label": "CRÍTICO",
                    "status": "open",
                    "metric": "vibration_rms_mm_s",
                    "first_detected_at": "2026-05-24T11:30:00Z",
                    "recommended_action": "Inspecionar conjunto.",
                }
            ],
            DEFAULT_ESCALATION_DATA,
            created_at="2026-05-24T12:00:00Z",
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["rule_id"], "critical_immediate_escalation")
        self.assertEqual(items[0]["channels"], "Dashboard + Telegram + WhatsApp")
        self.assertEqual(items[0]["status"], "pending")
        self.assertIn("CRÍTICO", items[0]["message"])

    def test_build_outbox_items_uses_current_states_when_alerts_are_empty(self) -> None:
        items = build_outbox_items(
            [],
            DEFAULT_ESCALATION_DATA,
            current_states=[
                {
                    "tenant_id": "cliente_demo",
                    "plant_id": "lab_virtual",
                    "asset_id": "motor_001",
                    "asset_name": "Motor Linha 1",
                    "status_label": "ATENÇÃO",
                    "severity_score": 30.0,
                    "updated_at": "2026-05-24T12:00:00Z",
                }
            ],
            created_at="2026-05-24T12:00:00Z",
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["rule_id"], "attention_dashboard_only")
        self.assertEqual(items[0]["channels"], "Dashboard")
        self.assertEqual(items[0]["status"], "pending")

    def test_notification_kind_prefers_escalation(self) -> None:
        self.assertEqual(notification_kind({"should_repeat": True, "should_escalate": True}), "escalation")
        self.assertEqual(notification_kind({"should_repeat": True, "should_escalate": False}), "repeat")
        self.assertEqual(notification_kind({"should_repeat": False, "should_escalate": False}), "initial")

    def test_repository_deduplicates_and_processes_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = NotificationOutboxRepository(Path(tmpdir) / "outbox.json")
            item = {
                "dedupe_key": "alert#critical#initial",
                "status": "pending",
                "kind": "initial",
                "created_at": "2026-05-24T12:00:00Z",
            }

            added, skipped = repo.add_pending([item, item])
            processed = repo.mark_dry_run_processed()
            items = repo.items()

        self.assertEqual((added, skipped), (1, 1))
        self.assertEqual(processed, 1)
        self.assertEqual(items[0]["status"], "dry_run")

    def test_outbox_kpis(self) -> None:
        kpis = outbox_kpis(
            [
                {"status": "pending", "kind": "initial"},
                {"status": "dry_run", "kind": "escalation"},
            ]
        )

        self.assertEqual(kpis["total"], 2)
        self.assertEqual(kpis["pending"], 1)
        self.assertEqual(kpis["dry_run_processed"], 1)
        self.assertEqual(kpis["escalations"], 1)


if __name__ == "__main__":
    unittest.main()
