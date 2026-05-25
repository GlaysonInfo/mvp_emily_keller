from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.dashboard.e2e_engine import (
    build_alert_item,
    build_current_state_item,
    evaluate_rules,
    infer_test_mode,
    is_virtual_source,
    payload_from_http,
    run_e2e_test,
    sample_payload,
)


def e2e_config() -> dict:
    return {
        "client": {"tenant_id": "cliente_demo", "environment_mode": "Demonstração"},
        "plant": {"plant_id": "lab_virtual", "plant_name": "Bancada Virtual"},
        "data_sources": [
            {
                "source_id": "virtual_bench_01",
                "source_name": "Bancada Virtual",
                "protocol": "Interno",
                "source_type": "Simulação",
                "endpoint": "local/demo",
            }
        ],
        "assets": [
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "asset_type": "Motor elétrico",
                "source_id": "virtual_bench_01",
                "nominal_rpm": 1800,
                "status": "Ativo",
            }
        ],
        "parameters_alerts": [
            {
                "asset_id": "motor_001",
                "metric": "vibration_rms_mm_s",
                "attention_min": 2.8,
                "alert_min": 4.5,
                "critical_min": 7.1,
                "enabled": True,
                "recommended_action": "Inspecionar conjunto mecânico.",
            }
        ],
    }


class FakeE2EDynamoClient:
    def __init__(self) -> None:
        self.state: dict | None = None
        self.alerts: list[dict] = []

    def put_current_state(self, state: dict) -> None:
        self.state = state

    def read_current_state(self, tenant_id: str, asset_id: str) -> dict:
        return self.state or {}

    def put_history(self, state: dict) -> dict:
        return {"tenant_asset": f"{state['tenant_id']}#{state['asset_id']}", "ts_utc_minute": "2026-05-23T18:00:00Z"}

    def query_history(self, tenant_id: str, asset_id: str) -> list[dict]:
        return [{"tenant_asset": f"{tenant_id}#{asset_id}"}]

    def put_alerts(self, state: dict, events: list[dict]) -> list[dict]:
        self.alerts = [build_alert_item(state, event) for event in events]
        return self.alerts

    def query_alerts(self, tenant_id: str, asset_id: str) -> list[dict]:
        return self.alerts


class E2EEngineTest(unittest.TestCase):
    def test_virtual_source_forces_virtual_mode_even_when_http_requested(self) -> None:
        source = e2e_config()["data_sources"][0]

        effective_mode, reason = infer_test_mode(source, "http")

        self.assertTrue(is_virtual_source(source))
        self.assertEqual(effective_mode, "virtual")
        self.assertIn("Fonte virtual", reason)

    def test_payload_from_http_rejects_symbolic_endpoint(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Endpoint inválido"):
            payload_from_http("local/demo")

    def test_evaluate_rules_creates_attention_event(self) -> None:
        config = e2e_config()
        payload = sample_payload(config, "motor_001", "virtual_bench_01")

        status, health, severity, events = evaluate_rules(config, payload)

        self.assertEqual(status, "ATENÇÃO")
        self.assertEqual(health, 70.0)
        self.assertEqual(severity, 30.0)
        self.assertEqual(events[0]["metric"], "vibration_rms_mm_s")

    def test_build_current_state_item_uses_dashboard_key_schema(self) -> None:
        config = e2e_config()
        payload = sample_payload(config, "motor_001", "virtual_bench_01")
        state = build_current_state_item(config, payload, "ATENÇÃO", 70.0, 30.0)

        self.assertEqual(state["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(state["sk"], "LATEST")
        self.assertEqual(state["tenant_plant"], "cliente_demo#lab_virtual")
        self.assertTrue(state["is_e2e_test"])

    def test_build_alert_item_has_both_supported_key_schemas(self) -> None:
        config = e2e_config()
        payload = sample_payload(config, "motor_001", "virtual_bench_01")
        state = build_current_state_item(config, payload, "ATENÇÃO", 70.0, 30.0)
        alert = build_alert_item(
            state,
            {
                "metric": "vibration_rms_mm_s",
                "value": 2.96,
                "threshold": 2.8,
                "status_label": "ATENÇÃO",
            },
        )

        self.assertEqual(alert["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(alert["tenant_asset"], "cliente_demo#motor_001")
        self.assertTrue(alert["sk"].startswith("ALERT#ACTIVE#"))
        self.assertTrue(alert["alert_key"].startswith("open#e2e#"))

    def test_run_e2e_test_returns_checklist_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            path.write_text(json.dumps(e2e_config(), ensure_ascii=False), encoding="utf-8")

            result = run_e2e_test(
                config_path=str(path),
                source_id="virtual_bench_01",
                asset_id="motor_001",
                mode="http",
                dynamodb_client=FakeE2EDynamoClient(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["requested_mode"], "http")
        self.assertEqual(result["effective_mode"], "virtual")
        self.assertEqual(result["status_label"], "ATENÇÃO")
        self.assertEqual(result["history_records"], 1)
        self.assertEqual(result["alerts_records"], 1)
        self.assertEqual([step["ok"] for step in result["steps"]], [True] * len(result["steps"]))
        self.assertIn("Modo de teste definido", [step["step"] for step in result["steps"]])


if __name__ == "__main__":
    unittest.main()
