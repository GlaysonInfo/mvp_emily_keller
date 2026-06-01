from __future__ import annotations

from src.dashboard.lubrication.lubrication_ui import local_demo_lubrication_snapshot, sample_payload_from_config


def _config() -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "sistema_lubrificacao_01",
        "source_id": "grease_gateway_01",
        "sensor_range_bar": 250,
        "outlets": [
            {"outlet_id": "saida_graxa_01", "nominal_pressure_bar": 100, "min_pressure_bar": 40, "max_pressure_bar": 160},
            {"outlet_id": "saida_graxa_02", "nominal_pressure_bar": 100, "min_pressure_bar": 40, "max_pressure_bar": 160},
            {"outlet_id": "saida_graxa_03", "nominal_pressure_bar": 100, "min_pressure_bar": 40, "max_pressure_bar": 160},
            {"outlet_id": "saida_graxa_04", "nominal_pressure_bar": 100, "min_pressure_bar": 40, "max_pressure_bar": 160},
        ],
    }


def test_sample_payload_from_config_uses_config_identity() -> None:
    payload = sample_payload_from_config(_config())

    assert payload["tenant_id"] == "cliente_demo"
    assert payload["plant_id"] == "lab_virtual"
    assert payload["asset_id"] == "sistema_lubrificacao_01"
    assert payload["source_id"] == "grease_gateway_01"


def test_local_demo_lubrication_snapshot_builds_state_without_repository() -> None:
    state, cycles, alerts = local_demo_lubrication_snapshot(_config())

    assert state["asset_id"] == "sistema_lubrificacao_01"
    assert len(state["outlets"]) == 4
    assert cycles == [state]
    assert alerts == state["active_alerts"]
