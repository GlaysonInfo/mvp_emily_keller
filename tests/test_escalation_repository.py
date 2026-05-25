from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.dashboard.escalation_repository import EscalationRepository, normalize_escalation_data


class EscalationRepositoryTest(unittest.TestCase):
    def test_normalize_defaults_when_data_is_missing(self) -> None:
        data = normalize_escalation_data(None)

        self.assertEqual(data["rules"][0]["severity"], "ATENÇÃO")
        self.assertEqual(data["rules"][1]["repeat_after_minutes"], 30)
        self.assertTrue(data["channels"][0]["configured"])

    def test_save_and_reload_rule_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "escalation_rules.json"
            repo = EscalationRepository(path)
            data = repo.load()
            rule = dict(data["rules"][1])
            rule["repeat_after_minutes"] = 45

            repo.upsert_rule(rule, data)
            reloaded = repo.load()

        alert_rule = next(item for item in reloaded["rules"] if item["rule_id"] == "alert_maintenance_telegram")
        self.assertEqual(alert_rule["repeat_after_minutes"], 45)

    def test_attention_rule_is_forced_to_dashboard_only(self) -> None:
        data = normalize_escalation_data(
            {
                "rules": [
                    {
                        "rule_id": "attention_dashboard_only",
                        "status_label": "ATENÇÃO",
                        "notify_channels": ["dashboard", "telegram", "whatsapp"],
                        "target_groups": ["manutencao"],
                        "notify_when_status": ["open", "acknowledged", "resolved"],
                        "delay_minutes": 15,
                        "repeat_minutes": 30,
                        "escalate_after_minutes": 60,
                    }
                ]
            }
        )

        rule = data["rules"][0]
        self.assertEqual(rule["channel_ids"], ["dashboard"])
        self.assertEqual(rule["contact_group_ids"], ["operador_local"])
        self.assertEqual(rule["notify_when_status"], ["open"])
        self.assertEqual(rule["delay_minutes"], 0)
        self.assertEqual(rule["repeat_after_minutes"], 0)
        self.assertEqual(rule["escalate_after_minutes"], 0)
        self.assertEqual(rule["escalate_to_group_ids"], [])

    def test_save_and_reload_contact_group_and_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "escalation_rules.json"
            repo = EscalationRepository(path)
            data = repo.load()

            repo.upsert_contact_group(
                {
                    "group_id": "manutencao",
                    "name": "Manutenção industrial",
                    "responsibility": "Atender eventos de manutenção.",
                    "contacts": [],
                },
                data,
            )
            data = repo.load()
            repo.upsert_channel(
                {
                    "channel_id": "telegram",
                    "name": "Telegram",
                    "enabled": True,
                    "configured": True,
                    "description": "Bot configurado.",
                },
                data,
            )
            reloaded = repo.load()

        group = next(item for item in reloaded["contact_groups"] if item["group_id"] == "manutencao")
        channel = next(item for item in reloaded["channels"] if item["channel_id"] == "telegram")
        self.assertEqual(group["name"], "Manutenção industrial")
        self.assertTrue(channel["configured"])


if __name__ == "__main__":
    unittest.main()
