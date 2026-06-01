from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.condition_ingest_api import app
from src.api.condition_ingest_models import ConditionIngestPayload, ConditionIngestResponse
from src.api.condition_ingest_service import process_condition_ingest


def _payload() -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "motor_001",
        "asset_name": "Motor Principal",
        "source": "condition_gateway_01",
        "timestamp": "2026-05-26T18:00:00Z",
        "metrics": [
            {"name": "rpm", "value": 1778.0, "unit": "rpm"},
            {"name": "vibration_rms_mm_s", "value": 4.4, "unit": "mm/s"},
            {"name": "temperature_c", "value": 62.8, "unit": "C"},
            {"name": "ultrasound_db", "value": 33.1, "unit": "dB"},
            {"name": "kurtosis", "value": 3.2, "unit": "index"},
            {"name": "crest_factor", "value": 3.1, "unit": "index"},
            {"name": "health_score", "value": 67.6, "unit": "score"},
        ],
    }


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


def test_condition_health_returns_configured_tables(monkeypatch) -> None:
    monkeypatch.setenv("DYNAMODB_STATE_TABLE", "mvp_asset_state_dev")
    monkeypatch.setenv("CONDITION_HISTORY_TABLE", "condition_history")
    monkeypatch.setenv("CONDITION_ALERTS_TABLE", "condition_alerts")

    response = TestClient(app).get("/condition/health")

    assert response.status_code == 200
    assert response.json()["state_table"] == "mvp_asset_state_dev"
    assert response.json()["history_table"] == "condition_history"
    assert response.json()["alerts_table"] == "condition_alerts"


def test_condition_ingest_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("CONDITION_INGEST_TOKEN", "token_do_piloto")

    response = TestClient(app).post("/condition/ingest", json=_payload())

    assert response.status_code == 401


def test_condition_ingest_fails_closed_without_token(monkeypatch) -> None:
    # Sem token configurado e com a exigência padrão (fail-closed) -> 503.
    monkeypatch.delenv("CONDITION_INGEST_TOKEN", raising=False)
    monkeypatch.delenv("CONDITION_REQUIRE_TOKEN", raising=False)

    response = TestClient(app).post("/condition/ingest", json=_payload())

    assert response.status_code == 503


def test_condition_ingest_accepts_valid_payload(monkeypatch) -> None:
    monkeypatch.setenv("CONDITION_INGEST_TOKEN", "token_do_piloto")

    def fake_process(payload: ConditionIngestPayload) -> ConditionIngestResponse:
        return ConditionIngestResponse(
            ok=True,
            message="ok",
            tenant_id=payload.tenant_id,
            plant_id=payload.plant_id,
            asset_id=payload.asset_id,
            source=payload.source,
            timestamp=str(payload.timestamp),
            status_label="CRÍTICO",
            metrics_received=len(payload.metrics),
            active_alerts_count=1,
            saved_state=True,
            saved_history=True,
            saved_alerts=True,
            details={},
        )

    monkeypatch.setattr("src.api.condition_ingest_api.process_condition_ingest", fake_process)

    response = TestClient(app).post(
        "/condition/ingest",
        headers={"X-API-Key": "token_do_piloto", "X-Trusted-Client-IP": "198.51.100.20"},
        json=_payload(),
    )

    assert response.status_code == 200
    assert response.json()["metrics_received"] == 7
    assert response.json()["status_label"] == "CRÍTICO"


def test_condition_ingest_does_not_trust_forwarded_for_by_default(monkeypatch) -> None:
    monkeypatch.setenv("CONDITION_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.setenv("CONDITION_ALLOWED_SOURCE_IPS", "198.51.100.0/24")
    monkeypatch.delenv("CONDITION_TRUST_X_FORWARDED_FOR", raising=False)

    response = TestClient(app).post(
        "/condition/ingest",
        headers={
            "X-API-Key": "token_do_piloto",
            "X-Forwarded-For": "198.51.100.20",
        },
        json=_payload(),
    )

    assert response.status_code == 403


def test_condition_ingest_rejects_duplicate_metrics(monkeypatch) -> None:
    # Sem token configurado: para validar o corpo (422), desliga a exigência
    # de token (fail-closed) neste caso específico.
    monkeypatch.delenv("CONDITION_INGEST_TOKEN", raising=False)
    monkeypatch.setenv("CONDITION_REQUIRE_TOKEN", "false")
    payload = _payload()
    payload["metrics"].append({"name": "rpm", "value": 1780.0, "unit": "rpm"})

    response = TestClient(app).post("/condition/ingest", json=payload)

    assert response.status_code == 422


def test_process_condition_ingest_saves_state_history_and_alerts(monkeypatch) -> None:
    monkeypatch.setenv("DYNAMODB_STATE_TABLE", "mvp_asset_state_dev")
    monkeypatch.setenv("CONDITION_HISTORY_TABLE", "condition_history")
    monkeypatch.setenv("CONDITION_ALERTS_TABLE", "condition_alerts")
    fake_resource = FakeDynamoResource()

    response = process_condition_ingest(
        ConditionIngestPayload(**_payload()),
        dynamodb_resource=fake_resource,
    )

    assert response.ok is True
    assert response.status_label == "CRÍTICO"
    assert response.metrics_received == 7
    assert response.active_alerts_count == 1

    state_item = fake_resource.tables["mvp_asset_state_dev"].put_items[0]
    assert state_item["pk"] == "TENANT#cliente_demo#ASSET#motor_001"
    assert state_item["sk"] == "LATEST"
    assert state_item["tenant_plant"] == "cliente_demo#lab_virtual"
    assert state_item["status_label"] == "CRÍTICO"
    assert state_item["health_score"].as_tuple()

    history_item = fake_resource.tables["condition_history"].put_items[0]
    assert history_item["tenant_asset"] == "cliente_demo#motor_001"
    assert history_item["status_label"] == "CRÍTICO"

    alert_item = fake_resource.tables["condition_alerts"].put_items[0]
    assert alert_item["tenant_asset"] == "cliente_demo#motor_001"
    assert alert_item["tenant_plant"] == "cliente_demo#lab_virtual"
    assert alert_item["alert_key"] == "open#condition#imbalance"
    assert alert_item["status_label"] == "CRÍTICO"
