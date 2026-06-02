from __future__ import annotations

from src.dashboard.module_registry import (
    ADMIN_DEV_PAGES,
    ROLE_ADMIN,
    ROLE_CLIENTE_ADMIN,
    ROLE_OPERADOR,
    ROLE_TECNICO,
    SERVICE_CONDITION,
    SERVICE_LUBRICATION,
    has_operational_intelligence,
    default_route_for_role,
    normalize_service_keys,
    routes_for_context,
    service_keys,
    services_for_contract,
)


def test_service_registry_exposes_contractable_modules() -> None:
    assert service_keys() == {SERVICE_CONDITION, SERVICE_LUBRICATION}
    assert [service["module_key"] for service in services_for_contract("condition,lubrication")] == [
        SERVICE_CONDITION,
        SERVICE_LUBRICATION,
    ]


def test_service_key_normalization_ignores_unknown_modules() -> None:
    assert normalize_service_keys(["condition", "unknown", "LUBRICATION"]) == {
        SERVICE_CONDITION,
        SERVICE_LUBRICATION,
    }


def test_operational_intelligence_requires_both_services() -> None:
    assert has_operational_intelligence([SERVICE_CONDITION, SERVICE_LUBRICATION])
    assert not has_operational_intelligence([SERVICE_CONDITION])
    assert not has_operational_intelligence([SERVICE_LUBRICATION])


def test_routes_are_filtered_by_role_and_contract() -> None:
    condition_operator = routes_for_context(ROLE_OPERADOR, [SERVICE_CONDITION])
    lubrication_operator = routes_for_context(ROLE_OPERADOR, [SERVICE_LUBRICATION])
    condition_technician = routes_for_context(ROLE_TECNICO, [SERVICE_CONDITION])
    lubrication_technician = routes_for_context(ROLE_TECNICO, [SERVICE_LUBRICATION])
    dual_technician = routes_for_context(ROLE_TECNICO, [SERVICE_CONDITION, SERVICE_LUBRICATION])
    client_admin = routes_for_context(ROLE_CLIENTE_ADMIN, [SERVICE_CONDITION])
    system_admin = routes_for_context(ROLE_ADMIN, [SERVICE_CONDITION, SERVICE_LUBRICATION])

    assert "Detalhe do Ativo" in condition_operator
    assert "Monitoramento de Equipamentos" in condition_operator
    assert "Sistema de Lubrificação" not in condition_operator
    assert "Operação de Lubrificação" in lubrication_operator
    assert "Sistema de Lubrificação" in lubrication_operator
    assert "Inteligência Operacional" not in condition_technician
    assert "Inteligência Operacional" not in lubrication_technician
    assert "Inteligência Operacional" in dual_technician
    assert "Bancada Virtual — Lubrificação" not in dual_technician
    assert "Eficiência da Lubrificação do Motor" not in dual_technician
    assert "Matriz de Escalonamento" not in dual_technician
    assert "Notification Outbox" not in dual_technician
    assert "Configuração de Campo — Lubrificação" in lubrication_technician
    assert "Configurações" in client_admin
    assert "Admin do Cliente" in client_admin
    assert "Monitoramento de Equipamentos" not in client_admin
    assert "Configuração de Campo — Lubrificação" not in client_admin
    assert "Notification Outbox" not in client_admin
    assert "Admin da Plataforma" not in client_admin
    assert "Arquitetura Modular" not in client_admin
    assert "Admin da Plataforma" in system_admin
    assert "Configurações" in system_admin
    assert "Bancada Virtual — Lubrificação" in system_admin
    assert "Notification Outbox" in system_admin
    assert "Admin do Cliente" not in system_admin
    assert "Monitoramento de Equipamentos" not in system_admin
    assert "Configuração de Campo — Lubrificação" not in system_admin
    assert "Arquitetura Modular" not in system_admin


def test_default_route_prefers_role_specific_entry_points() -> None:
    dual_routes = routes_for_context(ROLE_ADMIN, [SERVICE_CONDITION, SERVICE_LUBRICATION])
    client_admin_routes = routes_for_context(ROLE_CLIENTE_ADMIN, [SERVICE_CONDITION])
    technician_routes = routes_for_context(ROLE_TECNICO, [SERVICE_CONDITION])
    operator_routes = routes_for_context(ROLE_OPERADOR, [SERVICE_CONDITION])
    lubrication_operator_routes = routes_for_context(ROLE_OPERADOR, [SERVICE_LUBRICATION])
    lubrication_technician_routes = routes_for_context(ROLE_TECNICO, [SERVICE_LUBRICATION])

    assert default_route_for_role(ROLE_ADMIN, dual_routes) == "Admin da Plataforma"
    assert default_route_for_role(ROLE_CLIENTE_ADMIN, client_admin_routes) == "Admin do Cliente"
    assert default_route_for_role(ROLE_TECNICO, technician_routes) == "Monitoramento de Equipamentos"
    assert default_route_for_role(ROLE_OPERADOR, operator_routes) == "Monitoramento de Equipamentos"
    assert default_route_for_role(ROLE_OPERADOR, lubrication_operator_routes) == "Operação de Lubrificação"
    assert default_route_for_role(ROLE_TECNICO, lubrication_technician_routes) == "Operação de Lubrificação"


def test_admin_dev_routes_are_hidden_by_default_and_can_be_enabled(monkeypatch) -> None:
    monkeypatch.delenv("DASHBOARD_SHOW_ADMIN_DEV_TOOLS", raising=False)
    default_routes = routes_for_context(ROLE_ADMIN, [SERVICE_CONDITION, SERVICE_LUBRICATION])

    assert not set(ADMIN_DEV_PAGES) & set(default_routes)

    monkeypatch.setenv("DASHBOARD_SHOW_ADMIN_DEV_TOOLS", "true")
    dev_routes = routes_for_context(ROLE_ADMIN, [SERVICE_CONDITION, SERVICE_LUBRICATION])

    assert set(ADMIN_DEV_PAGES) <= set(dev_routes)
