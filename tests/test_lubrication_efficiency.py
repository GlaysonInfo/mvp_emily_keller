from __future__ import annotations

from src.dashboard.lubrication_efficiency.efficiency_engine import (
    calculate_lubrication_efficiency,
    equipment_condition_score,
    equipment_rows,
    lubrication_outlet_score,
)


def test_lubrication_outlet_score_weights_attention_alert_and_critical() -> None:
    state = {
        "outlet_count": 4,
        "normal_count": 1,
        "attention_count": 1,
        "alert_count": 1,
        "critical_count": 1,
    }

    assert lubrication_outlet_score(state) == 57.5


def test_equipment_condition_score_uses_health_and_status_penalty() -> None:
    states = [
        {"asset_id": "motor_001", "status_label": "CRÍTICO", "health_score": 60},
        {"asset_id": "bomba_001", "status_label": "NORMAL", "health_score": 90},
    ]

    assert equipment_condition_score(states) == 60.0


def test_efficiency_summary_combines_lubrication_and_equipment_condition() -> None:
    lubrication_state = {
        "outlet_count": 4,
        "normal_count": 2,
        "attention_count": 1,
        "alert_count": 1,
        "critical_count": 0,
        "max_anomaly_score": 72,
    }
    equipment_states = [
        {"asset_id": "motor_001", "status_label": "CRÍTICO", "health_score": 67.6},
    ]

    summary = calculate_lubrication_efficiency(lubrication_state, equipment_states)

    assert summary["status_label"] == "ALERTA"
    assert summary["affected_outlets"] == 2
    assert summary["monitored_equipment"] == 1
    assert summary["efficiency_score"] == 64.0


def test_equipment_rows_orders_by_severity() -> None:
    rows = equipment_rows(
        [
            {"asset_id": "normal", "status_label": "NORMAL", "health_score": 90},
            {"asset_id": "critical", "status_label": "CRÍTICO", "severity_score": 75},
        ]
    )

    assert [row["Equipamento"] for row in rows] == ["critical", "normal"]
