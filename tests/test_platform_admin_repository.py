from __future__ import annotations

from src.dashboard.platform_admin_repository import (
    PlatformAdminRepository,
    normalize_platform_admin_data,
)
from src.dashboard.onboarding_policy import REQUIRED_ASSISTED_CHECK_IDS


def test_default_platform_admin_data_has_demo_contract() -> None:
    data = normalize_platform_admin_data(None)

    assert data["schema_version"] == 2
    assert data["tenants"][0]["tenant_id"] == "cliente_demo"
    assert data["plants"][0]["plant_id"] == "lab_virtual"
    assert data["service_contracts"][0]["services"] == ["condition", "lubrication"]
    assert data["service_contracts"][0]["operational_intelligence"] is True
    assert data["onboarding_runs"][0]["tenant_id"] == "cliente_demo"
    assert data["onboarding_runs"][0]["assisted_checks"] == {}
    assert data["onboarding_runs"][0]["assisted_context"] == {}


def test_repository_upserts_tenant_plant_and_contract(tmp_path) -> None:
    repo = PlatformAdminRepository(tmp_path / "platform.json")

    repo.upsert_tenant(
        {
            "tenant_id": "cliente_a",
            "company_name": "Cliente A",
            "status": "Piloto",
            "environment": "Piloto",
        }
    )
    repo.upsert_plant(
        {
            "tenant_id": "cliente_a",
            "plant_id": "planta_1",
            "plant_name": "Planta 1",
            "city": "Betim",
            "status": "Ativa",
        }
    )
    data = repo.upsert_contract(
        {
            "tenant_id": "cliente_a",
            "plant_id": "planta_1",
            "services": ["condition", "unknown"],
            "status": "Ativo",
        }
    )

    contract = next(item for item in data["service_contracts"] if item["tenant_id"] == "cliente_a")
    assert contract["services"] == ["condition"]
    assert contract["operational_intelligence"] is False


def test_services_for_contract_respects_status_and_missing_contract(tmp_path) -> None:
    repo = PlatformAdminRepository(tmp_path / "platform.json")

    repo.upsert_contract(
        {
            "tenant_id": "cliente_a",
            "plant_id": "planta_1",
            "services": ["lubrication"],
            "status": "Ativo",
        }
    )
    repo.upsert_contract(
        {
            "tenant_id": "cliente_a",
            "plant_id": "planta_2",
            "services": ["condition"],
            "status": "Suspenso",
        }
    )

    assert repo.services_for_contract("cliente_a", "planta_1") == ["lubrication"]
    assert repo.services_for_contract("cliente_a", "planta_2") == []
    assert repo.services_for_contract("cliente_a", "planta_x") is None


def test_repository_scopes_data_by_tenant_and_upserts_users(tmp_path) -> None:
    repo = PlatformAdminRepository(tmp_path / "platform.json")
    repo.upsert_tenant({"tenant_id": "cliente_a", "company_name": "A", "status": "Ativo", "environment": "Piloto"})
    repo.upsert_tenant({"tenant_id": "cliente_b", "company_name": "B", "status": "Ativo", "environment": "Piloto"})
    repo.upsert_plant({"tenant_id": "cliente_a", "plant_id": "planta_a", "plant_name": "A", "status": "Ativa"})
    repo.upsert_plant({"tenant_id": "cliente_b", "plant_id": "planta_b", "plant_name": "B", "status": "Ativa"})
    repo.upsert_user(
        {
            "tenant_id": "cliente_a",
            "email": "USER@EXAMPLE.COM",
            "name": "User A",
            "role": "operador",
            "status": "Ativo",
        }
    )

    scoped = repo.data_for_tenant("cliente_a")

    assert [tenant["tenant_id"] for tenant in scoped["tenants"]] == ["cliente_a"]
    assert [plant["plant_id"] for plant in scoped["plants"]] == ["planta_a"]
    assert scoped["users"][0]["email"] == "user@example.com"


def test_repository_upserts_and_scopes_onboarding_run(tmp_path) -> None:
    repo = PlatformAdminRepository(tmp_path / "platform.json")

    repo.upsert_onboarding_run(
        {
            "tenant_id": "cliente_a",
            "plant_id": "planta_1",
            "status": "Liberado",
            "manual_steps": {"commissioning": True, "release": True},
            "assisted_checks": {check_id: True for check_id in REQUIRED_ASSISTED_CHECK_IDS},
            "assisted_context": {
                "machine_id": "motor_real_01",
                "gateway_id": "gateway_01",
                "responsible": "Técnico Sentinela",
                "endpoint_url": "https://sentinelaindustrial.com.br/condition/ingest",
                "stop_criteria": "Parar ao detectar risco operacional.",
            },
            "notes": "Primeiro cliente liberado.",
        }
    )

    run = repo.onboarding_run_for("cliente_a", "planta_1")
    scoped = repo.data_for_tenant("cliente_a")

    assert run["status"] == "Liberado"
    assert run["manual_steps"]["commissioning"] is True
    assert run["assisted_checks"]["first_payload_received"] is True
    assert run["assisted_context"]["machine_id"] == "motor_real_01"
    assert scoped["onboarding_runs"] == [run]


def test_repository_blocks_release_with_incomplete_indoor_checklist(tmp_path) -> None:
    repo = PlatformAdminRepository(tmp_path / "platform.json")

    try:
        repo.upsert_onboarding_run(
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "status": "Liberado",
                "manual_steps": {"commissioning": True, "release": True},
                "assisted_checks": {"first_payload_received": True},
                "assisted_context": {"machine_id": "motor_real_01"},
            }
        )
    except ValueError as exc:
        assert "não pode ser liberado" in str(exc)
    else:
        raise AssertionError("A liberação incompleta deveria ter sido bloqueada.")
