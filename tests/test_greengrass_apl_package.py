from __future__ import annotations

import json
from pathlib import Path

from src.edge.condition_bridge_field.config_store import load_condition_field_config
from src.edge.condition_bridge_field.iot_topic import build_iot_topic
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads


CONFIG_PATH = "config/ethernet_apl_greengrass_condition_config.example.json"
SAMPLE_PATH = "src/edge/condition_bridge_field/sample_ethernet_apl_response.json"


def test_ethernet_apl_greengrass_config_builds_condition_payload() -> None:
    config = load_condition_field_config(CONFIG_PATH)
    raw = json.loads(Path(SAMPLE_PATH).read_text(encoding="utf-8"))

    payloads = build_condition_payloads(config, raw)

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["tenant_id"] == "cliente_real"
    assert payload["plant_id"] == "indoor"
    assert payload["asset_id"] == "apl_process_sensor_01"
    assert payload["source"] == "greengrass_apl_gateway_01"
    assert {metric["name"] for metric in payload["metrics"]} >= {
        "pressure_bar",
        "flow_rate_l_min",
        "temperature_c",
        "level_percent",
        "vibration_rms_mm_s",
        "device_state",
    }


def test_iot_topic_uses_sentinela_tenant_plant_asset_contract() -> None:
    config = load_condition_field_config(CONFIG_PATH)
    raw = json.loads(Path(SAMPLE_PATH).read_text(encoding="utf-8"))
    payload = build_condition_payloads(config, raw)[0]

    assert build_iot_topic(config, payload) == "sentinela/cliente_real/indoor/apl_process_sensor_01/telemetry"


def test_greengrass_package_contains_installation_artifacts() -> None:
    required_paths = [
        "deploy/greengrass/README.md",
        "deploy/greengrass/sentinela-condition-apl/recipe.yaml",
        "deploy/greengrass/scripts/provision_iot_core_gateway.sh",
        "deploy/greengrass/scripts/install_core_device.sh",
        "deploy/greengrass/scripts/build_component_package.ps1",
        "deploy/greengrass/templates/iot-policy-sentinela-greengrass.json",
        "deploy/greengrass/templates/iot-rule-condition-to-lambda.json",
        "deploy/greengrass/templates/iot-rule-condition-raw-dynamodb.json",
        "docs/ethernet_apl_greengrass_aws_iot_sentinela.md",
    ]

    for path in required_paths:
        assert Path(path).exists(), path

    recipe = Path("deploy/greengrass/sentinela-condition-apl/recipe.yaml").read_text(encoding="utf-8")
    assert "com.sentinela.ConditionAplBridge" in recipe
    assert "greengrass_iot_publisher" in recipe

    install = Path("deploy/greengrass/scripts/install_core_device.sh").read_text(encoding="utf-8")
    assert "--init-config" in install
    assert "config.yaml" in install
