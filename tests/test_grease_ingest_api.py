from fastapi.testclient import TestClient

from src.api.grease_ingest_api import app
from src.api.grease_ingest_models import GreaseIngestResponse


def _payload() -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "sistema_lubrificacao_01",
        "source_id": "grease_gateway_01",
        "timestamp_utc": "2026-05-25T23:30:00Z",
        "cycle_id": "cycle_test_api",
        "metrics": {
            "pressure_saida_graxa_03_bar": 7.8,
            "peak_saida_graxa_03_bar": 9.2,
        },
    }


def test_grease_health_uses_default_tables(monkeypatch) -> None:
    monkeypatch.delenv("GREASE_INGEST_TOKEN", raising=False)
    monkeypatch.delenv("GREASE_ALLOWED_SOURCE_IPS", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    response = TestClient(app).get("/grease/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["region"] == "us-east-1"
    assert body["state_table"] == "grease_lubrication_state"


def test_grease_ingest_rejects_missing_token(monkeypatch) -> None:
    monkeypatch.setenv("GREASE_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.delenv("GREASE_ALLOWED_SOURCE_IPS", raising=False)

    response = TestClient(app).post("/grease/ingest", json=_payload())

    assert response.status_code == 401


def test_grease_ingest_accepts_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GREASE_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.delenv("GREASE_ALLOWED_SOURCE_IPS", raising=False)

    def fake_process(payload):
        return GreaseIngestResponse(
            ok=True,
            message="ok",
            tenant_id=payload.tenant_id,
            plant_id=payload.plant_id,
            asset_id=payload.asset_id,
            source_id=payload.source_id,
            cycle_id=payload.cycle_id,
            status_label="ALERTA",
            outlet_count=4,
            active_alerts_count=2,
            saved_state=True,
            saved_cycle=True,
            saved_alerts=True,
            details={"alert_count": 1},
        )

    monkeypatch.setattr("src.api.grease_ingest_api.process_grease_ingest", fake_process)

    response = TestClient(app).post(
        "/grease/ingest",
        headers={"X-API-Key": "token_do_piloto"},
        json=_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status_label"] == "ALERTA"
    assert body["active_alerts_count"] == 2


def test_grease_ingest_rejects_disallowed_source_ip(monkeypatch) -> None:
    monkeypatch.setenv("GREASE_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.setenv("GREASE_ALLOWED_SOURCE_IPS", "203.0.113.10")

    response = TestClient(app).post(
        "/grease/ingest",
        headers={
            "X-API-Key": "token_do_piloto",
            "X-Trusted-Client-IP": "198.51.100.20",
        },
        json=_payload(),
    )

    assert response.status_code == 403


def test_grease_ingest_accepts_allowed_forwarded_ip(monkeypatch) -> None:
    monkeypatch.setenv("GREASE_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.setenv("GREASE_ALLOWED_SOURCE_IPS", "198.51.100.0/24")

    def fake_process(payload):
        return GreaseIngestResponse(
            ok=True,
            message="ok",
            tenant_id=payload.tenant_id,
            plant_id=payload.plant_id,
            asset_id=payload.asset_id,
            source_id=payload.source_id,
            cycle_id=payload.cycle_id,
            status_label="ALERTA",
            outlet_count=4,
            active_alerts_count=2,
            saved_state=True,
            saved_cycle=True,
            saved_alerts=True,
            details={"alert_count": 1},
        )

    monkeypatch.setattr("src.api.grease_ingest_api.process_grease_ingest", fake_process)

    response = TestClient(app).post(
        "/grease/ingest",
        headers={
            "X-API-Key": "token_do_piloto",
            "X-Trusted-Client-IP": "198.51.100.20",
        },
        json=_payload(),
    )

    assert response.status_code == 200


def test_grease_ingest_does_not_trust_forwarded_for_by_default(monkeypatch) -> None:
    monkeypatch.setenv("GREASE_INGEST_TOKEN", "token_do_piloto")
    monkeypatch.setenv("GREASE_ALLOWED_SOURCE_IPS", "198.51.100.0/24")
    monkeypatch.delenv("GREASE_TRUST_X_FORWARDED_FOR", raising=False)

    response = TestClient(app).post(
        "/grease/ingest",
        headers={
            "X-API-Key": "token_do_piloto",
            "X-Forwarded-For": "198.51.100.20",
        },
        json=_payload(),
    )

    assert response.status_code == 403


def test_grease_ingest_fails_closed_without_token(monkeypatch) -> None:
    # Sem token configurado e com a exigência padrão (fail-closed) -> 503.
    monkeypatch.delenv("GREASE_INGEST_TOKEN", raising=False)
    monkeypatch.delenv("GREASE_REQUIRE_TOKEN", raising=False)
    monkeypatch.delenv("GREASE_ALLOWED_SOURCE_IPS", raising=False)

    response = TestClient(app).post("/grease/ingest", json=_payload())

    assert response.status_code == 503
