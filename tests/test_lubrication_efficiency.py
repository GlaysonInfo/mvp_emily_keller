from __future__ import annotations

from src.dashboard.lubrication_efficiency.efficiency_engine import (
    calculate_lubrication_efficiency,
    equipment_condition_score,
    equipment_rows,
    lubrication_outlet_score,
)
from src.dashboard.lubrication_efficiency.equipment_links import (
    enabled_equipment_links,
    equipment_link_rows,
    filter_linked_equipment_states,
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


def test_efficiency_summary_counts_configured_links() -> None:
    lubrication_state = {
        "outlet_count": 4,
        "normal_count": 4,
        "attention_count": 0,
        "alert_count": 0,
        "critical_count": 0,
        "max_anomaly_score": 0,
    }
    summary = calculate_lubrication_efficiency(
        lubrication_state,
        equipment_states=[],
        equipment_links=[{"asset_id": "motor_cli01", "outlet_id": "saida_graxa_03"}],
    )

    assert summary["monitored_equipment"] == 1


def test_equipment_rows_orders_by_severity() -> None:
    rows = equipment_rows(
        [
            {"asset_id": "normal", "status_label": "NORMAL", "health_score": 90},
            {"asset_id": "critical", "status_label": "CRÍTICO", "severity_score": 75},
        ]
    )

    assert [row["Equipamento"] for row in rows] == ["critical", "normal"]


def test_equipment_links_register_motor_to_lubrication_outlet() -> None:
    config = {
        "asset_id": "sistema_lubrificacao_01",
        "equipment_links": [
            {
                "asset_id": "motor_cli01",
                "asset_name": "Motor Cliente 01",
                "outlet_id": "saida_graxa_03",
                "target_grease_g_per_cycle": 12,
                "cycle_interval_h": 24,
            }
        ],
    }

    links = enabled_equipment_links(config)

    assert links[0]["asset_id"] == "motor_cli01"
    assert links[0]["outlet_id"] == "saida_graxa_03"
    assert links[0]["lubrication_system_id"] == "sistema_lubrificacao_01"


def test_linked_equipment_filter_keeps_only_configured_assets() -> None:
    links = [{"asset_id": "motor_cli01"}]
    states = [
        {"asset_id": "motor_cli01", "health_score": 84},
        {"asset_id": "compressor_001", "health_score": 62},
    ]

    filtered = filter_linked_equipment_states(states, links)

    assert filtered == [{"asset_id": "motor_cli01", "health_score": 84}]


def test_equipment_link_rows_show_equipment_and_outlet_status() -> None:
    links = [
        {
            "asset_id": "motor_cli01",
            "asset_name": "Motor Cliente 01",
            "outlet_id": "saida_graxa_03",
            "outlet_name": "Saída de Graxa 03",
            "grease_type": "EP2",
            "target_grease_g_per_cycle": 12.0,
            "cycle_interval_h": 24,
            "baseline_status": "marco_zero_pendente",
            "objective": "Otimizar dose.",
        }
    ]
    states = [{"asset_id": "motor_cli01", "status_label": "ATENÇÃO", "health_score": 72}]
    lubrication_state = {
        "outlets": [
            {"outlet_id": "saida_graxa_03", "severity": "ATENÇÃO", "peak_pressure_bar": 92.4}
        ]
    }

    rows = equipment_link_rows(links, states, lubrication_state)

    assert rows[0]["Equipamento"] == "Motor Cliente 01"
    assert rows[0]["Saída"] == "Saída de Graxa 03"
    assert rows[0]["Dose alvo (g/ciclo)"] == 12.0
    assert rows[0]["Status equipamento"] == "ATENÇÃO"
    assert rows[0]["Status saída"] == "ATENÇÃO"
