from __future__ import annotations

from src.dashboard.platform_admin_repository import (
    PlatformAdminRepository,
    normalize_platform_admin_data,
)


def test_default_platform_admin_data_has_demo_contract() -> None:
    data = normalize_platform_admin_data(None)

    assert data["tenants"][0]["tenant_id"] == "cliente_demo"
    assert data["plants"][0]["plant_id"] == "lab_virtual"
    assert data["service_contracts"][0]["services"] == ["condition", "lubrication"]
    assert data["service_contracts"][0]["operational_intelligence"] is True


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
