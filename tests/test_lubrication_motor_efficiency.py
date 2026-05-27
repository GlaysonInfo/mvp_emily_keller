from __future__ import annotations

from src.dashboard.lubrication_motor_efficiency.motor_efficiency_engine import (
    build_marco_zero,
    build_response_rows,
    grease_comparison_rows,
    recommend_dose,
)
from src.dashboard.lubrication.lubrication_repository import LubricationRepository


class FakeCycleTable:
    def __init__(self) -> None:
        self.request = None

    def update_item(self, **kwargs):
        self.request = kwargs
        return {
            "Attributes": {
                "tenant_asset": kwargs["Key"]["tenant_asset"],
                "cycle_timestamp": kwargs["Key"]["cycle_timestamp"],
                "grease_amount_g": kwargs["ExpressionAttributeValues"][":amount"],
            }
        }


def test_marco_zero_uses_first_history_item_and_current_state() -> None:
    history = [
        {
            "ts_utc_minute": "2026-05-26T10:00:00Z",
            "health_score": 82,
            "severity_score": 18,
            "vibration_rms_mm_s": 2.4,
            "temperature_c": 58,
            "ultrasound_db": 31,
        },
        {"ts_utc_minute": "2026-05-26T12:00:00Z", "health_score": 88, "severity_score": 12},
    ]

    marco_zero = build_marco_zero(history, {"health_score": 90, "severity_score": 10})

    assert marco_zero["has_history"] is True
    assert marco_zero["health_score"] == 82
    assert marco_zero["latest_health_score"] == 90


def test_response_rows_compare_motor_before_and_after_grease_cycle() -> None:
    link = {
        "asset_id": "motor_cli01",
        "outlet_id": "saida_graxa_03",
        "grease_type": "EP2",
        "target_grease_g_per_cycle": 12,
        "cycle_interval_h": 24,
    }
    cycles = [
        {
            "cycle_id": "cycle_1",
            "cycle_timestamp": "2026-05-26T11:00:00Z",
            "outlets": [{"outlet_id": "saida_graxa_03", "severity": "NORMAL", "peak_pressure_bar": 104}],
        }
    ]
    history = [
        {
            "ts_utc_minute": "2026-05-26T10:50:00Z",
            "health_score": 70,
            "severity_score": 30,
            "vibration_rms_mm_s": 4.0,
            "temperature_c": 66,
            "ultrasound_db": 42,
        },
        {
            "ts_utc_minute": "2026-05-26T13:00:00Z",
            "health_score": 78,
            "severity_score": 22,
            "vibration_rms_mm_s": 3.0,
            "temperature_c": 62,
            "ultrasound_db": 36,
        },
    ]

    rows = build_response_rows(link=link, cycles=cycles, history_items=history)

    assert rows[0]["grease_amount_g"] == 12
    assert rows[0]["health_delta"] == 8
    assert rows[0]["vibration_reduction_pct"] == 25.0
    assert rows[0]["response_label"] in {"BOA", "EXCELENTE"}


def test_recommendation_maintains_dose_when_response_is_good() -> None:
    recommendation = recommend_dose(
        {"target_grease_g_per_cycle": 12, "cycle_interval_h": 24},
        [{"response_score": 12.5, "response_label": "EXCELENTE", "grease_amount_g": 12}],
    )

    assert recommendation["decision"] == "MANTER"
    assert recommendation["recommended_dose_g"] == 12


def test_recommendation_reduces_dose_when_temperature_rises_after_cycle() -> None:
    recommendation = recommend_dose(
        {"target_grease_g_per_cycle": 12, "cycle_interval_h": 24},
        [{"response_score": 1.0, "temperature_delta_c": 4.0, "grease_amount_g": 12}],
    )

    assert recommendation["decision"] == "REDUZIR"
    assert recommendation["recommended_dose_g"] == 10.8


def test_grease_comparison_groups_response_by_grease_type() -> None:
    rows = grease_comparison_rows(
        [
            {"grease_type": "EP2 A", "response_score": 8, "grease_amount_g": 12},
            {"grease_type": "EP2 A", "response_score": 12, "grease_amount_g": 10},
            {"grease_type": "EP2 B", "response_score": 4, "grease_amount_g": 14},
        ]
    )

    assert rows[0]["Graxa"] == "EP2 A"
    assert rows[0]["Resposta média"] == 10.0
    assert rows[0]["Dose média (g)"] == 11.0


def test_repository_updates_cycle_dose_metadata() -> None:
    repo = LubricationRepository.__new__(LubricationRepository)
    repo.cycles_table = FakeCycleTable()

    updated = repo.update_cycle_dose(
        "cliente_demo",
        "sistema_lubrificacao_01",
        "2026-05-26T11:00:00Z",
        linked_asset_id="motor_cli01",
        outlet_id="saida_graxa_03",
        grease_amount_g=12.5,
        grease_type="EP2",
        cycle_interval_h=24,
    )

    assert repo.cycles_table.request["Key"] == {
        "tenant_asset": "cliente_demo#sistema_lubrificacao_01",
        "cycle_timestamp": "2026-05-26T11:00:00Z",
    }
    assert updated["grease_amount_g"] == 12.5
