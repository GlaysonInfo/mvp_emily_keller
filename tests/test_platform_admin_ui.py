from __future__ import annotations

from src.dashboard.platform_admin_ui import (
    ONBOARDING_STEP_DEFINITIONS,
    ONBOARDING_STEPS,
    SUPPORT_SCOPES,
    _asset_inventory_rows,
    _contract_rows,
    _onboarding_step_rows,
    _onboarding_summary,
    _plant_for,
    _platform_summary,
    _tenant_for,
    _tenant_onboarding_rows,
)


PLATFORM_ADMIN_UI_SOURCE = "src/dashboard/platform_admin_ui.py"


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
    assert [step["id"] for step in ONBOARDING_STEP_DEFINITIONS][-2:] == ["commissioning", "release"]
    assert any(scope["Domínio"] == "Suporte remoto" for scope in SUPPORT_SCOPES)
    assert any("auditoria" in scope["Controle exigido"].lower() for scope in SUPPORT_SCOPES)


def test_asset_inventory_rows_scope_assets_to_selected_plant() -> None:
    data = _sample_platform_data()
    operational_config = {
        "assets": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "asset_id": "motor_001",
                "asset_name": "Motor 001",
                "asset_type": "Motor",
                "area": "Linha 1",
                "criticality": "Alta",
                "source_id": "opcua_01",
                "status": "Ativo",
            },
            {
                "tenant_id": "cliente_b",
                "plant_id": "planta_2",
                "asset_id": "esteira_001",
                "asset_name": "Esteira 001",
            },
        ],
        "signal_map": [
            {"asset_id": "motor_001", "metric": "vibration_rms_mm_s"},
            {"asset_id": "motor_001", "metric": "temperature_c"},
        ],
        "parameters_alerts": [{"asset_id": "motor_001", "metric": "vibration_rms_mm_s"}],
    }

    rows = _asset_inventory_rows(data, operational_config, tenant_id="cliente_a", plant_id="planta_1")

    assert rows == [
        {
            "Ativo": "motor_001",
            "Nome": "Motor 001",
            "Tipo": "Motor",
            "Área": "Linha 1",
            "Criticidade": "Alta",
            "Fonte": "opcua_01",
            "Sinais": 2,
            "Parâmetros": 1,
            "Status": "Ativo",
        }
    ]


def test_onboarding_step_rows_combine_admin_store_and_operational_config() -> None:
    data = _sample_platform_data()
    data["users"].extend(
        [
            {"tenant_id": "cliente_a", "email": "tecnico@cliente-a.com", "role": "tecnico", "status": "Ativo"},
            {"tenant_id": "cliente_a", "email": "operador@cliente-a.com", "role": "operador", "status": "Ativo"},
        ]
    )
    operational_config = {
        "assets": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "asset_id": "motor_001",
                "asset_name": "Motor 001",
                "source_id": "opcua_01",
            }
        ],
        "data_sources": [{"source_id": "opcua_01"}],
        "signal_map": [{"asset_id": "motor_001", "metric": "vibration_rms_mm_s"}],
        "parameters_alerts": [{"asset_id": "motor_001", "metric": "vibration_rms_mm_s"}],
    }
    run = {
        "tenant_id": "cliente_a",
        "plant_id": "planta_1",
        "manual_steps": {"commissioning": True, "release": False},
    }

    rows = _onboarding_step_rows(data, operational_config, run, tenant_id="cliente_a", plant_id="planta_1")
    summary = _onboarding_summary(rows)

    assert [row["Status"] for row in rows[:6]] == ["OK", "OK", "OK", "OK", "OK", "OK"]
    assert rows[-1]["Status"] == "Pendente"
    assert rows[4]["Evidência"] == "Ativos: 1 | Fontes: 1 | Sinais: 1 | Parâmetros: 1"
    assert summary == {"percent": 86, "done": 6, "total": 7, "status": "Em implantação"}


def test_onboarding_lookup_helpers_find_focused_tenant_and_plant() -> None:
    data = _sample_platform_data()

    assert _tenant_for(data, "cliente_a")["company_name"] == "Cliente A"
    assert _plant_for(data, "cliente_a", "planta_1")["plant_name"] == "Planta 1"
    assert _tenant_for(data, "cliente_x") is None
    assert _plant_for(data, "cliente_a", "planta_x") is None


def test_onboarding_page_exposes_guided_registration_forms() -> None:
    from pathlib import Path

    source = Path(PLATFORM_ADMIN_UI_SOURCE).read_text(encoding="utf-8")

    assert "Cadastro guiado" in source
    assert "platform_onboarding_tenant_form" in source
    assert "platform_onboarding_plant_form" in source
    assert "platform_onboarding_contract_form" in source
