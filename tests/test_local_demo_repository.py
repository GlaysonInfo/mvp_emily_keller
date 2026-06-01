from __future__ import annotations

from src.dashboard.local_demo_repository import LocalDemoHistoryRepository, LocalDemoRepository


def test_local_demo_repository_loads_seed_states() -> None:
    repo = LocalDemoRepository()

    states = repo.list_current_states("cliente_demo", "lab_virtual")
    latest = repo.get_latest_state("cliente_demo", "motor_001")

    assert len(states) >= 1
    assert latest is not None
    assert latest["asset_id"] == "motor_001"
    assert latest["sk"] == "LATEST"


def test_local_demo_repository_supports_demo_case_updates() -> None:
    repo = LocalDemoRepository()
    state = {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "asset_local_test",
        "status_label": "ALERTA",
        "metrics": {},
    }

    repo.put_latest_state(state)
    repo.put_active_alert(
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "asset_id": "asset_local_test",
            "alert_type": "demo",
            "severity": "warning",
            "is_demo_case": True,
        }
    )

    assert repo.get_latest_state("cliente_demo", "asset_local_test") is not None
    assert len(repo.get_active_alerts("cliente_demo", "asset_local_test")) == 1
    assert repo.clear_demo_alerts("cliente_demo", "asset_local_test") == 1


def test_local_demo_repository_supports_alert_center_workflow() -> None:
    repo = LocalDemoRepository()
    alert = repo.create_manual_alert(
        "cliente_demo",
        "lab_virtual",
        "asset_local_alert_center",
        "Ativo Local",
        "inspecao_visual",
        "ALERTA",
        8.0,
        7.0,
        "Inspecionar ativo.",
        "Ana",
        "Ruído observado.",
    )

    listed = repo.list_alerts("cliente_demo", "lab_virtual", "asset_local_alert_center", "open")
    full = repo.get_alert(str(alert["tenant_asset"]), str(alert["alert_key"]))
    updated = repo.update_status(str(alert["tenant_asset"]), str(alert["alert_key"]), "acknowledged", "Ana")

    assert len(listed) == 1
    assert full["alert_id"] == alert["alert_id"]
    assert updated["status"] == "acknowledged"
    assert updated["timeline"][-1]["to_status"] == "acknowledged"


def test_local_demo_history_repository_is_noop_but_returns_snapshot() -> None:
    repo = LocalDemoHistoryRepository()

    item = repo.put_minute_snapshot({"tenant_id": "cliente_demo", "asset_id": "motor_001", "metrics": {}})

    assert item["tenant_asset"] == "cliente_demo#motor_001"
    assert repo.query_history(tenant_id="cliente_demo", asset_id="motor_001") == []
