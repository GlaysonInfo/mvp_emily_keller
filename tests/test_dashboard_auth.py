from __future__ import annotations

import importlib

from src.dashboard.auth import guard as guard_module
from src.dashboard.auth.identity import Identity
from src.dashboard.auth import identity as identity_module
from src.dashboard.platform_admin_repository import PlatformAdminRepository
from src.dashboard.auth.rbac import (
    ROLE_ADMIN,
    ROLE_CLIENTE_ADMIN,
    ROLE_OPERADOR,
    ROLE_TECNICO,
    allowed_pages,
    can,
    can_access,
    role_from_groups,
)
from src.dashboard.hmi.hmi_sidebar import DEFAULT_OPERATOR_PAGES, DEFAULT_TECH_PAGES


def test_rbac_covers_default_hmi_routes() -> None:
    operator_routes = {item["route"] for item in DEFAULT_OPERATOR_PAGES}
    technical_routes = set(DEFAULT_TECH_PAGES)

    assert operator_routes <= allowed_pages(ROLE_OPERADOR)
    assert technical_routes - {
        "Eficiência da Lubrificação do Motor",
        "Bancada Virtual — Equipamentos",
        "Bancada Virtual — Lubrificação",
        "Matriz de Escalonamento",
        "Notification Outbox",
        "Configurações",
        "Admin do Cliente",
        "Admin da Plataforma",
        "Arquitetura Modular",
        "Teste ponta a ponta",
    } <= allowed_pages(ROLE_TECNICO)
    assert not can_access(ROLE_OPERADOR, "Configurações")
    assert not can_access(ROLE_TECNICO, "Arquitetura Modular")
    assert not can_access(ROLE_TECNICO, "Bancada Virtual — Equipamentos")
    assert not can_access(ROLE_TECNICO, "Bancada Virtual — Lubrificação")
    assert not can_access(ROLE_TECNICO, "Notification Outbox")
    assert can_access(ROLE_CLIENTE_ADMIN, "Configurações")
    assert can_access(ROLE_CLIENTE_ADMIN, "Admin do Cliente")
    assert not can_access(ROLE_CLIENTE_ADMIN, "Monitoramento de Equipamentos")
    assert not can_access(ROLE_CLIENTE_ADMIN, "Configuração de Campo — Lubrificação")
    assert not can_access(ROLE_CLIENTE_ADMIN, "Notification Outbox")
    assert not can_access(ROLE_CLIENTE_ADMIN, "Admin da Plataforma")
    assert not can_access(ROLE_CLIENTE_ADMIN, "Arquitetura Modular")
    assert can_access(ROLE_ADMIN, "Admin da Plataforma")
    assert can_access(ROLE_ADMIN, "Configurações")
    assert can_access(ROLE_ADMIN, "Bancada Virtual — Equipamentos")
    assert can_access(ROLE_ADMIN, "Bancada Virtual — Lubrificação")
    assert can_access(ROLE_ADMIN, "Notification Outbox")
    assert not can_access(ROLE_ADMIN, "Admin do Cliente")
    assert not can_access(ROLE_ADMIN, "Monitoramento de Equipamentos")
    assert not can_access(ROLE_ADMIN, "Configuração de Campo — Lubrificação")
    assert can_access(ROLE_ADMIN, "Arquitetura Modular")
    assert can(ROLE_CLIENTE_ADMIN, "manage_client_users")
    assert not can(ROLE_CLIENTE_ADMIN, "edit_field_config")
    assert not can(ROLE_CLIENTE_ADMIN, "edit_alert_params")
    assert not can(ROLE_CLIENTE_ADMIN, "cross_tenant")
    assert can(ROLE_ADMIN, "cross_tenant")
    assert not can(ROLE_TECNICO, "cross_tenant")


def test_role_from_groups_uses_admin_precedence() -> None:
    assert role_from_groups(["CLIENTE_OPERADOR", "ADMIN_SERVER"]) == ROLE_ADMIN
    assert role_from_groups(["CLIENTE_TECNICO", "CLIENTE_ADMIN"]) == ROLE_CLIENTE_ADMIN
    assert role_from_groups(["CLIENTE_OPERADOR", "CLIENTE_TECNICO"]) == ROLE_TECNICO
    assert role_from_groups(["TENANT_cliente_demo"]) is None


def test_dev_identity_resolves_role_and_tenant_from_tenant_group(monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTH_DEV_IDENTITY",
        '{"email":"tec@cliente.com","groups":["CLIENTE_TECNICO","TENANT_cliente_demo"]}',
    )

    identity = identity_module.resolve_identity()

    assert identity is not None
    assert identity.email == "tec@cliente.com"
    assert identity.role == ROLE_TECNICO
    assert identity.tenant_id == "cliente_demo"
    assert identity.service_keys == []
    assert identity.is_authenticated


def test_dev_identity_resolves_contracted_services(monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTH_DEV_IDENTITY",
        (
            '{"email":"admin@cliente.com","groups":["CLIENTE_ADMIN","TENANT_cliente_demo"],'
            '"services":["condition","lubrication","unknown"]}'
        ),
    )

    identity = identity_module.resolve_identity()

    assert identity is not None
    assert identity.role == ROLE_CLIENTE_ADMIN
    assert identity.tenant_id == "cliente_demo"
    assert identity.service_keys == ["condition", "lubrication"]


def test_allowed_routes_for_identity_follow_service_contract(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_DEFAULT_SERVICES", raising=False)
    identity = Identity(
        email="op@cliente.com",
        name="Operador",
        role=ROLE_OPERADOR,
        tenant_id="cliente_demo",
        service_keys=["condition"],
    )

    routes = guard_module.allowed_routes_for_identity(identity)

    assert "Detalhe do Ativo" in routes
    assert "Sistema de Lubrificação" not in routes


def test_allowed_routes_for_context_use_platform_admin_contract(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AUTH_DEFAULT_SERVICES", raising=False)
    store_path = tmp_path / "platform.json"
    repo = PlatformAdminRepository(store_path)
    repo.upsert_contract(
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "services": ["lubrication"],
            "status": "Ativo",
        }
    )
    monkeypatch.setenv("PLATFORM_ADMIN_STORE", str(store_path))
    identity = Identity(
        email="op@cliente.com",
        name="Operador",
        role=ROLE_OPERADOR,
        tenant_id="cliente_demo",
    )

    routes = guard_module.allowed_routes_for_context(identity, "cliente_demo", "lab_virtual")

    assert "Sistema de Lubrificação" in routes
    assert "Detalhe do Ativo" not in routes


def test_modular_access_blocks_hidden_admin_dev_routes_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_DEFAULT_SERVICES", raising=False)
    monkeypatch.delenv("DASHBOARD_SHOW_ADMIN_DEV_TOOLS", raising=False)
    identity = Identity(
        email="admin@sentinela.com",
        name="Admin",
        role=ROLE_ADMIN,
        tenant_id=None,
    )

    routes = guard_module.allowed_routes_for_context(identity, "cliente_demo", "lab_virtual")

    assert "Admin da Plataforma" in routes
    assert "Arquitetura Modular" not in routes


def test_configured_header_names_are_normalized(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_HEADER_EMAIL", "X-Forwarded-Email")
    monkeypatch.setenv("AUTH_HEADER_GROUPS", "X-Forwarded-Groups")

    reloaded = importlib.reload(identity_module)

    assert reloaded._HDR_EMAIL == "x-forwarded-email"
    assert reloaded._HDR_GROUPS == "x-forwarded-groups"

    monkeypatch.delenv("AUTH_HEADER_EMAIL", raising=False)
    monkeypatch.delenv("AUTH_HEADER_GROUPS", raising=False)
    importlib.reload(identity_module)


def test_signout_url_defaults_to_app_logout(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_SIGNOUT_URL", raising=False)
    monkeypatch.delenv("INSTITUTIONAL_SITE_URL", raising=False)
    monkeypatch.delenv("AUTH_DEV_IDENTITY", raising=False)
    monkeypatch.delenv("DASHBOARD_DATA_MODE", raising=False)

    assert guard_module._signout_url() == "https://app.sentinelaindustrial.com.br/oauth2/sign_out"


def test_signout_url_returns_local_site_in_dev_identity(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_SIGNOUT_URL", raising=False)
    monkeypatch.delenv("INSTITUTIONAL_SITE_URL", raising=False)
    monkeypatch.setenv("AUTH_DEV_IDENTITY", '{"email":"op@cliente.com"}')

    assert guard_module._signout_url() == "http://127.0.0.1:8081/"


def test_signout_url_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_SIGNOUT_URL", "https://auth.example.com/logout")
    monkeypatch.setenv("INSTITUTIONAL_SITE_URL", "https://sentinela.example.com/")

    assert guard_module._signout_url() == "https://auth.example.com/logout"
