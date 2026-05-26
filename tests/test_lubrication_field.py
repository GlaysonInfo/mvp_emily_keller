from __future__ import annotations

import json
from pathlib import Path

from src.dashboard.lubrication_field.baseline_engine import (
    compare_cycle_to_baseline,
    compute_outlet_baseline,
)
from src.dashboard.lubrication_field.cycle_curve_engine import build_metrics_from_curves
from src.dashboard.lubrication_field.field_config_store import load_field_config, validate_field_config
from src.edge.grease_bridge_field.payload_builder import build_grease_payload


def test_field_config_example_is_valid() -> None:
    config = load_field_config("config/field_lubrication_config.example.json")
    issues = validate_field_config(config)

    assert not [issue for issue in issues if issue["level"] == "ERRO"]
    assert config["ingest_api"]["endpoint"] == "https://sentinelaindustrial.com.br/grease/ingest"


def test_curve_engine_builds_pressure_metrics() -> None:
    curves = {
        "saida_graxa_01": [
            {"ts_ms": 0, "pressure_bar": 0},
            {"ts_ms": 1000, "pressure_bar": 20},
            {"ts_ms": 2000, "pressure_bar": 100},
            {"ts_ms": 3000, "pressure_bar": 4},
        ]
    }

    metrics = build_metrics_from_curves(curves)

    assert metrics["pressure_saida_graxa_01_bar"] == 4
    assert metrics["peak_saida_graxa_01_bar"] == 100
    assert metrics["rise_time_saida_graxa_01_sec"] == 1
    assert metrics["decay_time_saida_graxa_01_sec"] == 1


def test_baseline_marks_ready_and_detects_deviation() -> None:
    cycles = [
        {"outlets": [{"outlet_id": "saida_graxa_01", "peak_pressure_bar": 100 + i}]}
        for i in range(20)
    ]

    baseline = compute_outlet_baseline(cycles, "saida_graxa_01", min_samples=20)
    comparison = compare_cycle_to_baseline(
        {"outlet_id": "saida_graxa_01", "peak_pressure_bar": 180},
        baseline,
        warning_pct=20,
        alert_pct=50,
    )

    assert baseline["ready"] is True
    assert baseline["peak_pressure_bar"]["samples"] == 20
    assert comparison["baseline_status"] == "ALERTA"


def test_payload_builder_uses_field_identity() -> None:
    config = json.loads(Path("config/field_lubrication_config.example.json").read_text(encoding="utf-8"))
    payload = build_grease_payload(
        config,
        {
            "timestamp_utc": "2026-05-26T12:00:00Z",
            "metrics": {"peak_saida_graxa_01_bar": 105},
        },
    )

    assert payload["tenant_id"] == "cliente_demo"
    assert payload["asset_id"] == "sistema_lubrificacao_01"
    assert payload["source_id"] == "grease_gateway_01"
    assert payload["metrics"]["peak_saida_graxa_01_bar"] == 105
