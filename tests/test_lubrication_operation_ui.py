from __future__ import annotations

from src.dashboard.lubrication.lubrication_config import default_lubrication_config
from src.dashboard.lubrication_operation_ui import (
    _operation_snapshot,
    action_for_lubrication_anomaly,
    field_anomaly_rows,
    lubrication_operator_kpis,
    lubrication_points_rows,
    planned_executed_cycles,
    technical_parameter_rows,
    technician_failure_analysis_rows,
)


class FakeLubricationRepository:
    def __init__(self, state: dict | None = None):
        self.state = state or {}

    def get_state(self, tenant_id: str, asset_id: str) -> dict:
        return self.state

    def list_cycles(self, tenant_id: str, asset_id: str, limit: int = 10) -> list[dict]:
        return [self.state] if self.state else []

    def list_alerts(self, tenant_id: str, asset_id: str) -> list[dict]:
        return self.state.get("active_alerts", []) if self.state else []


class FailingLubricationRepository:
    def get_state(self, tenant_id: str, asset_id: str) -> dict:
        raise RuntimeError("repository unavailable")


def test_operation_snapshot_uses_repository_state_when_available() -> None:
    config = default_lubrication_config()
    state = {
        "tenant_id": "cliente_demo",
        "asset_id": "sistema_lubrificacao_01",
        "status_label": "NORMAL",
        "outlets": [],
        "active_alerts": [],
    }

    snapshot, cycles, alerts, source = _operation_snapshot(config, FakeLubricationRepository(state))

    assert snapshot == state
    assert cycles == [state]
    assert alerts == []
    assert source == "Repositório de ciclos"


def test_operation_snapshot_falls_back_to_demo_cycle_without_repository() -> None:
    config = default_lubrication_config()

    snapshot, cycles, alerts, source = _operation_snapshot(config, FailingLubricationRepository())

    assert source == "Ciclo demonstrativo em memória"
    assert snapshot["asset_id"] == "sistema_lubrificacao_01"
    assert len(snapshot["outlets"]) == 4
    assert cycles == [snapshot]
    assert alerts == snapshot["active_alerts"]


def test_operator_kpis_include_cycles_alerts_and_pressure() -> None:
    config = default_lubrication_config()
    snapshot, cycles, alerts, _ = _operation_snapshot(config, FailingLubricationRepository())

    kpis = lubrication_operator_kpis(snapshot, cycles, alerts)

    assert kpis["outlets"] == 4
    assert kpis["executed_cycles"] == 1
    assert kpis["alerts"] == len(alerts)
    assert kpis["max_pressure_bar"] == snapshot["max_pressure_bar"]


def test_lubrication_points_rows_merge_state_and_config() -> None:
    config = default_lubrication_config()
    snapshot, _, _, _ = _operation_snapshot(config, FailingLubricationRepository())

    rows = lubrication_points_rows(snapshot, config)

    assert len(rows) == 4
    assert rows[0]["name"].startswith("Saída")
    assert "pressure_bar" in rows[0]
    assert "anomaly_score" in rows[0]


def test_planned_executed_cycles_uses_equipment_links() -> None:
    config = default_lubrication_config()
    snapshot, cycles, _, _ = _operation_snapshot(config, FailingLubricationRepository())

    rows = planned_executed_cycles(config, cycles)

    assert rows
    assert rows[0]["Ciclos executados"] == 1
    assert rows[0]["Status"] == snapshot["status_label"]


def test_field_anomaly_rows_extracts_outlet_failures() -> None:
    config = default_lubrication_config()
    snapshot, _, alerts, _ = _operation_snapshot(config, FailingLubricationRepository())

    rows = field_anomaly_rows(snapshot, alerts)

    assert rows
    assert all(row["Ação sugerida"] for row in rows)


def test_action_for_lubrication_anomaly_maps_common_failures() -> None:
    assert "falta de graxa" in action_for_lubrication_anomaly({"status": "low_pressure"})
    assert "obstrução" in action_for_lubrication_anomaly({"status": "high_pressure"})


def test_technician_failure_analysis_rows_include_plan() -> None:
    config = default_lubrication_config()
    snapshot, _, _, _ = _operation_snapshot(config, FailingLubricationRepository())

    rows = technician_failure_analysis_rows(snapshot)

    assert len(rows) == 4
    assert "Plano de ação" in rows[0]
    assert "Pico" in rows[0]


def test_technical_parameter_rows_expose_thresholds() -> None:
    rows = technical_parameter_rows(default_lubrication_config())

    assert {row["Parâmetro"] for row in rows} >= {
        "Pressão baixa",
        "Pressão alta",
        "Pressão crítica",
        "Tempo máximo de subida",
        "Tempo máximo de alívio",
        "Delta mínimo de pulso",
    }
