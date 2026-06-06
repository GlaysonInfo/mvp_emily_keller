from __future__ import annotations

import json
from pathlib import Path

from src.edge.condition_bridge_field.config_store import load_condition_field_config, validate_condition_field_config
from src.edge.condition_bridge_field.delivery_queue import ConditionDeliveryQueue
from src.edge.condition_bridge_field.gateway_client import ConditionGatewayClient, get_nested_value
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads
from src.edge.condition_bridge_field.sender import ConditionIngestSender


def test_condition_field_config_example_is_valid() -> None:
    config = load_condition_field_config("config/field_condition_config.example.json")
    issues = validate_condition_field_config(config)

    assert not [issue for issue in issues if issue["level"] == "ERRO"]
    assert config["ingest_api"]["endpoint"] == "https://sentinelaindustrial.com.br/condition/ingest"


def test_nested_value_supports_dict_and_list_paths() -> None:
    raw = {"ports": [{"value": 10}, {"value": 20}], "motor": {"rpm": 1780}}

    assert get_nested_value(raw, "motor.rpm") == 1780
    assert get_nested_value(raw, "ports.1.value") == 20
    assert get_nested_value(raw, "ports.9.value") is None


def test_payload_builder_maps_gateway_tags_to_condition_metrics() -> None:
    config = json.loads(Path("config/field_condition_config.example.json").read_text(encoding="utf-8"))
    raw = json.loads(Path("src/edge/condition_bridge_field/sample_raw_gateway_response.json").read_text(encoding="utf-8"))

    payloads = build_condition_payloads(config, raw)
    motor_payload = next(payload for payload in payloads if payload["asset_id"] == "motor_001")

    metrics = {metric["name"]: metric for metric in motor_payload["metrics"]}
    assert motor_payload["tenant_id"] == "cliente_demo"
    assert motor_payload["plant_id"] == "lab_virtual"
    assert motor_payload["source"] == "condition_gateway_01"
    assert motor_payload["event_id"]
    assert metrics["vibration_rms_mm_s"]["value"] == 4.4
    assert metrics["temperature_c"]["unit"] == "C"


def test_simulated_gateway_client_reads_sample_file() -> None:
    config = load_condition_field_config("config/field_condition_config.example.json")
    raw = ConditionGatewayClient(config).read_raw()

    assert raw["motor_001"]["rpm"] == 1778.0


def test_sender_allows_endpoint_override(monkeypatch) -> None:
    config = load_condition_field_config("config/field_condition_config.example.json")
    monkeypatch.setenv("CONDITION_INGEST_ENDPOINT", "http://127.0.0.1:8001/condition/ingest")

    sender = ConditionIngestSender(config)

    assert sender.endpoint == "http://127.0.0.1:8001/condition/ingest"


def test_delivery_queue_persists_and_acknowledges_payload(tmp_path) -> None:
    queue = ConditionDeliveryQueue(tmp_path / "spool")
    payload = {"event_id": "evt-001", "asset_id": "motor_001"}

    queued = queue.enqueue(payload)

    assert queue.pending() == [queued]
    assert queue.load(queued) == payload
    queue.acknowledge(queued)
    assert queue.pending() == []


def test_sender_retries_with_exponential_backoff(monkeypatch) -> None:
    config = load_condition_field_config("config/field_condition_config.example.json")
    config["ingest_api"]["max_attempts"] = 3
    config["ingest_api"]["backoff_sec"] = 0.01
    sender = ConditionIngestSender(config)
    attempts: list[int] = []
    sleeps: list[float] = []

    def fake_send(payload, timeout_sec=15):
        attempts.append(timeout_sec)
        if len(attempts) < 3:
            raise OSError("offline")
        return {"ok": True}

    monkeypatch.setattr(sender, "send", fake_send)
    monkeypatch.setattr("src.edge.condition_bridge_field.sender.time.sleep", sleeps.append)

    assert sender.send_with_retry({"event_id": "evt-001"}) == {"ok": True}
    assert len(attempts) == 3
    assert sleeps == [0.01, 0.02]
