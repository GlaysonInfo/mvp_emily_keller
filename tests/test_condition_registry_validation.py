from __future__ import annotations

import json

from src.api.condition_ingest_models import ConditionIngestPayload
from src.api.condition_ingest_service import process_condition_ingest


def payload(asset_id: str = "motor_001", source: str = "condition_gateway_01") -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": asset_id,
        "asset_name": "Motor Principal",
        "source": source,
        "timestamp": "2026-05-26T18:00:00Z",
        "metrics": [
            {"name": "rpm", "value": 1778.0, "unit": "rpm"},
            {"name": "vibration_rms_mm_s", "value": 4.4, "unit": "mm/s"},
            {"name": "temperature_c", "value": 62.8, "unit": "C"},
            {"name": "health_score", "value": 67.6, "unit": "score"},
        ],
    }


def registry_config() -> dict:
    return {
        "client": {"tenant_id": "cliente_demo"},
        "plant": {"tenant_id": "cliente_demo", "plant_id": "lab_virtual"},
        "data_sources": [
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "source_id": "condition_gateway_01",
            }
        ],
        "assets": [
            {
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "source_id": "condition_gateway_01",
                "status": "Ativo",
            }
        ],
        "signal_map": [
            {"asset_id": "motor_001", "source_id": "condition_gateway_01", "metric": "rpm", "enabled": True},
            {
                "asset_id": "motor_001",
                "source_id": "condition_gateway_01",
                "metric": "vibration_rms_mm_s",
                "enabled": True,
            },
            {
                "asset_id": "motor_001",
                "source_id": "condition_gateway_01",
                "metric": "temperature_c",
                "enabled": True,
            },
            {
                "asset_id": "motor_001",
                "source_id": "condition_gateway_01",
                "metric": "health_score",
                "enabled": True,
            },
        ],
        "parameters_alerts": [],
    }


def write_registry_config(tmp_path, config: dict | None = None):
    path = tmp_path / "config_store.json"
    path.write_text(json.dumps(config or registry_config()), encoding="utf-8")
    return path


class FakeTable:
    def __init__(self) -> None:
        self.put_items: list[dict] = []
        self.get_requests: list[dict] = []

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {}

    def get_item(self, **kwargs) -> dict:
        self.get_requests.append(kwargs)
        return {}


class FakeDynamoResource:
    def __init__(self) -> None:
        self.tables = {
            "mvp_asset_state_dev": FakeTable(),
            "condition_history": FakeTable(),
            "condition_alerts": FakeTable(),
        }

    def Table(self, table_name: str) -> FakeTable:
        return self.tables[table_name]


def test_process_condition_ingest_marks_registry_ok_when_payload_matches_cadastro(monkeypatch, tmp_path) -> None:
    registry_path = write_registry_config(tmp_path)
    monkeypatch.setenv("CONDITION_REGISTRY_CONFIG_PATH", str(registry_path))
    monkeypatch.setenv("DYNAMODB_STATE_TABLE", "mvp_asset_state_dev")
    monkeypatch.setenv("CONDITION_HISTORY_TABLE", "condition_history")
    monkeypatch.setenv("CONDITION_ALERTS_TABLE", "condition_alerts")
    fake_resource = FakeDynamoResource()

    response = process_condition_ingest(
        ConditionIngestPayload(**payload()),
        dynamodb_resource=fake_resource,
    )

    assert response.registry_validation_status == "ok"
    assert response.registry_warnings == []

    state_item = fake_resource.tables["mvp_asset_state_dev"].put_items[0]
    assert state_item["registry_validation_status"] == "ok"
    assert "registry_warnings" not in state_item

    history_item = fake_resource.tables["condition_history"].put_items[0]
    assert history_item["registry_validation_status"] == "ok"


def test_process_condition_ingest_warns_without_blocking_when_payload_does_not_match_cadastro(
    monkeypatch,
    tmp_path,
) -> None:
    registry_path = write_registry_config(tmp_path)
    monkeypatch.setenv("CONDITION_REGISTRY_CONFIG_PATH", str(registry_path))
    monkeypatch.setenv("DYNAMODB_STATE_TABLE", "mvp_asset_state_dev")
    monkeypatch.setenv("CONDITION_HISTORY_TABLE", "condition_history")
    monkeypatch.setenv("CONDITION_ALERTS_TABLE", "condition_alerts")
    fake_resource = FakeDynamoResource()
    received = payload(asset_id="motor_nao_cadastrado", source="gateway_desconhecido")
    received["metrics"].append({"name": "corrente_a", "value": 10.5, "unit": "A"})

    response = process_condition_ingest(
        ConditionIngestPayload(**received),
        dynamodb_resource=fake_resource,
    )

    warning_codes = {item["code"] for item in response.registry_warnings}
    assert response.ok is True
    assert response.saved_state is True
    assert response.registry_validation_status == "warning"
    assert {"asset_not_registered", "source_not_registered", "asset_without_expected_metrics"}.issubset(warning_codes)

    state_item = fake_resource.tables["mvp_asset_state_dev"].put_items[0]
    assert state_item["registry_validation_status"] == "warning"
    assert state_item["registry_warnings"]

    history_item = fake_resource.tables["condition_history"].put_items[0]
    assert history_item["registry_validation_status"] == "warning"
    assert history_item["registry_warnings"]
