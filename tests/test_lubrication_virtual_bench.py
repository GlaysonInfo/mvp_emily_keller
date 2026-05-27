from __future__ import annotations

from datetime import datetime, timezone

from src.dashboard.lubrication.lubrication_config import default_lubrication_config
from src.dashboard.lubrication_virtual_bench.scenarios import (
    build_lubrication_scenario_payloads,
    evaluate_lubrication_scenario,
    pressure_curve_from_metrics,
    scenario_options,
)


def _outlets(result: dict) -> dict[str, dict]:
    return {outlet["outlet_id"]: outlet for outlet in result["outlets"]}


def test_scenario_catalog_contains_field_failures() -> None:
    scenario_ids = {scenario_id for scenario_id, _label in scenario_options()}

    assert {
        "queda_pressao",
        "aumento_pressao",
        "entupimento_parcial",
        "entupimento_severo",
        "graxa_contaminada",
        "sem_graxa_ponta",
        "pulso_intermitente",
    }.issubset(scenario_ids)


def test_pressure_drop_scenario_is_temporal_and_finishes_low_pressure() -> None:
    config = default_lubrication_config()
    payloads = build_lubrication_scenario_payloads(
        config,
        "queda_pressao",
        cycles=5,
        start_time=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )
    results = evaluate_lubrication_scenario(config, "queda_pressao", cycles=5)

    first_peak = payloads[0]["metrics"]["peak_saida_graxa_03_bar"]
    last_peak = payloads[-1]["metrics"]["peak_saida_graxa_03_bar"]
    final_outlet = _outlets(results[-1])["saida_graxa_03"]

    assert first_peak > last_peak
    assert final_outlet["status"] == "low_pressure"
    assert final_outlet["severity"] == "ATENÇÃO"


def test_partial_blockage_finishes_with_high_pressure_and_slow_decay() -> None:
    config = default_lubrication_config()
    results = evaluate_lubrication_scenario(config, "entupimento_parcial", cycles=6)
    final_outlet = _outlets(results[-1])["saida_graxa_04"]

    assert final_outlet["status"] == "high_pressure_slow_decay"
    assert final_outlet["severity"] == "ALERTA"
    assert results[-1]["status_label"] == "ALERTA"


def test_no_grease_at_tip_finishes_critical_without_pulse() -> None:
    config = default_lubrication_config()
    results = evaluate_lubrication_scenario(config, "sem_graxa_ponta", cycles=4)
    final_outlet = _outlets(results[-1])["saida_graxa_03"]

    assert final_outlet["status"] == "no_pulse"
    assert final_outlet["pulse_detected"] is False
    assert final_outlet["severity"] == "CRÍTICO"
    assert results[-1]["status_label"] == "CRÍTICO"


def test_contaminated_grease_generates_curve_and_restriction_evidence() -> None:
    config = default_lubrication_config()
    payload = build_lubrication_scenario_payloads(config, "graxa_contaminada", cycles=6)[-1]
    results = evaluate_lubrication_scenario(config, "graxa_contaminada", cycles=6)
    final_outlet = _outlets(results[-1])["saida_graxa_04"]

    assert payload["curves"]["saida_graxa_04"][0]["ts_sec"] == 0.0
    assert len(payload["curves"]["saida_graxa_04"]) >= 5
    assert final_outlet["status"] == "high_pressure_slow_decay"
    assert any("alívio" in reason for reason in final_outlet["reasons"])


def test_pressure_curve_has_rise_peak_and_relief_points() -> None:
    metrics = {
        "min_saida_graxa_01_bar": 2.0,
        "pressure_saida_graxa_01_bar": 80.0,
        "peak_saida_graxa_01_bar": 120.0,
        "rise_time_saida_graxa_01_sec": 4.0,
        "decay_time_saida_graxa_01_sec": 8.0,
    }

    curve = pressure_curve_from_metrics(metrics, "saida_graxa_01")

    assert curve[0] == {"ts_sec": 0.0, "pressure_bar": 2.0}
    assert curve[2] == {"ts_sec": 4.0, "pressure_bar": 120.0}
    assert curve[-1] == {"ts_sec": 12.0, "pressure_bar": 2.0}
