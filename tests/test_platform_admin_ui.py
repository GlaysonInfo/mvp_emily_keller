from __future__ import annotations

from src.dashboard.platform_admin_ui import (
    ONBOARDING_STEPS,
    SUPPORT_SCOPES,
    _contract_rows,
    _platform_summary,
    _tenant_onboarding_rows,
)


def _sample_platform_data() -> dict:
    return {
        "tenants": [
            {
                "tenant_id": "cliente_a",
                "company_name": "Cliente A",
                "status": "Ativo",
                "environment": "Produção",
            },
            {
                "tenant_id": "cliente_b",
                "company_name": "Cliente B",
                "status": "Piloto",
                "environment": "Piloto",
            },
        ],
        "plants": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "plant_name": "Planta 1",
                "city": "Betim",
                "status": "Ativa",
            }
        ],
        "service_contracts": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "services": ["condition", "lubrication"],
                "operational_intelligence": True,
                "status": "Ativo",
            },
            {
                "tenant_id": "cliente_b",
                "plant_id": "planta_2",
                "services": ["condition"],
                "operational_intelligence": False,
                "status": "Suspenso",
            },
        ],
        "users": [
            {
                "tenant_id": "cliente_a",
                "email": "admin@cliente-a.com",
                "role": "cliente_admin",
                "status": "Ativo",
            }
        ],
    }


def test_platform_summary_counts_contracts_and_modules() -> None:
    summary = _platform_summary(_sample_platform_data())

    assert summary == {
        "tenants": 2,
        "active_tenants": 1,
        "plants": 1,
        "contracts": 2,
        "active_contracts": 1,
        "condition_contracts": 2,
        "lubrication_contracts": 1,
        "dual_service_contracts": 1,
    }


def test_contract_rows_use_business_labels() -> None:
    rows = _contract_rows(_sample_platform_data())

    assert rows[0]["Cliente"] == "cliente_a"
    assert rows[0]["Planta"] == "planta_1"
    assert "Monitoramento de Equipamentos" in rows[0]["Módulos contratados"]
    assert "Sistema de Lubrificação" in rows[0]["Módulos contratados"]
    assert rows[0]["Inteligência Operacional"] == "Sim"


def test_tenant_onboarding_rows_expose_next_actions() -> None:
    rows = _tenant_onboarding_rows(_sample_platform_data())

    assert rows[0]["Cliente"] == "cliente_a"
    assert rows[0]["Próxima ação"] == "OK"
    assert rows[1]["Cliente"] == "cliente_b"
    assert rows[1]["Próxima ação"] == "Cadastrar planta, admin do cliente"


def test_admin_sentinela_guidance_has_onboarding_and_support_scope() -> None:
    assert [step["Etapa"] for step in ONBOARDING_STEPS][:3] == [
        "1. Cliente",
        "2. Planta",
        "3. Contrato",
    ]
    assert any(scope["Domínio"] == "Suporte remoto" for scope in SUPPORT_SCOPES)
    assert any("auditoria" in scope["Controle exigido"].lower() for scope in SUPPORT_SCOPES)
