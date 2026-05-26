from src.dashboard.lubrication.lubrication_config import default_lubrication_config
from src.dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle


def test_lubrication_demo_cycle_flags_low_pressure_and_slow_decay() -> None:
    config = default_lubrication_config()
    payload = {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "sistema_lubrificacao_01",
        "source_id": "grease_gateway_01",
        "timestamp_utc": "2026-05-25T23:30:00Z",
        "cycle_id": "cycle_demo_test",
        "metrics": {
            "pressure_saida_graxa_01_bar": 84.2,
            "pressure_saida_graxa_02_bar": 91.7,
            "pressure_saida_graxa_03_bar": 7.8,
            "pressure_saida_graxa_04_bar": 146.5,
            "peak_saida_graxa_01_bar": 102.3,
            "peak_saida_graxa_02_bar": 108.1,
            "peak_saida_graxa_03_bar": 9.2,
            "peak_saida_graxa_04_bar": 181.2,
            "min_saida_graxa_01_bar": 2.0,
            "min_saida_graxa_02_bar": 2.0,
            "min_saida_graxa_03_bar": 0.0,
            "min_saida_graxa_04_bar": 4.0,
            "rise_time_saida_graxa_01_sec": 3.2,
            "rise_time_saida_graxa_02_sec": 3.5,
            "rise_time_saida_graxa_03_sec": 8.9,
            "rise_time_saida_graxa_04_sec": 2.1,
            "decay_time_saida_graxa_01_sec": 4.8,
            "decay_time_saida_graxa_02_sec": 5.1,
            "decay_time_saida_graxa_03_sec": 2.4,
            "decay_time_saida_graxa_04_sec": 18.6,
        },
    }

    result = evaluate_lubrication_cycle(payload, config)

    outlets = {outlet["outlet_id"]: outlet for outlet in result["outlets"]}
    assert outlets["saida_graxa_03"]["status"] == "low_pressure"
    assert outlets["saida_graxa_04"]["status"] == "high_pressure_slow_decay"
    assert result["attention_count"] == 1
    assert result["alert_count"] == 1
    assert len(result["active_alerts"]) == 2
    assert set(result["recommendation"]["affected_outlets"]) == {"saida_graxa_03", "saida_graxa_04"}


def test_lubrication_cycle_without_pressure_pulse_is_critical() -> None:
    config = {
        **default_lubrication_config(),
        "outlets": [{"outlet_id": "saida_graxa_01", "name": "Saida de Graxa 01"}],
    }
    payload = {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "sistema_lubrificacao_01",
        "source_id": "grease_gateway_01",
        "metrics": {
            "pressure_saida_graxa_01_bar": 2.0,
            "peak_saida_graxa_01_bar": 3.5,
            "min_saida_graxa_01_bar": 1.0,
        },
    }

    result = evaluate_lubrication_cycle(payload, config)

    assert result["critical_count"] == 1
    assert result["outlets"][0]["status"] == "no_pulse"
    assert result["active_alerts"][0]["status"] == "open"
