from __future__ import annotations

from datetime import UTC, datetime

from src.dashboard.platform_admin_ui import (
    ASSISTED_PRODUCTION_CHECKS,
    ONBOARDING_STEP_DEFINITIONS,
    ONBOARDING_STEPS,
    SUPPORT_SCOPES,
    _assisted_production_rows,
    _assisted_production_summary,
    _asset_inventory_rows,
    _contract_rows,
    _gateway_inventory_rows,
    _indoor_health_rows,
    _indoor_health_summary,
    _indoor_registry_warning_rows,
    _latest_alert_summary,
    _metric_options_for_asset_type,
    _onboarding_step_rows,
    _onboarding_summary,
    _parameter_rule_for_metric,
    _plant_for,
    _platform_summary,
    _replace_by_keys,
    _sensor_inventory_rows,
    _technical_history_for_context,
    _technical_history_rows,
    _technical_parameter_rule_for_metric,
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
    assert [step["id"] for step in ONBOARDING_STEP_DEFINITIONS][-3:] == [
        "commissioning",
        "assisted_production",
        "release",
    ]
    assert len(ASSISTED_PRODUCTION_CHECKS) == 10
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
        "sensors": [{"sensor_id": "sensor_01", "asset_id": "motor_001", "source_id": "opcua_01"}],
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
    assert rows[-2]["Status"] == "Pendente"
    assert rows[-1]["Status"] == "Pendente"
    assert rows[4]["Evidência"] == "Ativos: 1 | Sensores: 1 | Fontes: 1 | Sinais: 1 | Parâmetros: 1"
    assert summary == {"percent": 75, "done": 6, "total": 8, "status": "Em implantação"}


def test_assisted_production_checklist_rows_and_summary() -> None:
    run = {
        "assisted_checks": {
            "real_machine_identified": True,
            "real_sensors_installed": True,
            "gateway_registered": False,
        }
    }

    rows = _assisted_production_rows(run)
    summary = _assisted_production_summary(run)

    assert rows[0]["Status"] == "OK"
    assert rows[0]["Item"] == "Máquina real identificada"
    assert rows[2]["Status"] == "Pendente"
    assert summary == {"done": 2, "total": 10, "percent": 20}


def test_indoor_health_rows_classify_communication_and_registry_warnings() -> None:
    inventory = [
        {"Ativo": "motor_001", "Nome": "Motor 001", "Fonte": "gateway_01"},
        {"Ativo": "motor_002", "Nome": "Motor 002", "Fonte": "gateway_01"},
        {"Ativo": "esteira_001", "Nome": "Esteira 001", "Fonte": "gateway_02"},
    ]
    states = [
        {
            "asset_id": "motor_001",
            "updated_at": "2026-06-05T12:00:00Z",
            "status_label": "NORMAL",
            "health_score": 94,
            "registry_validation_status": "ok",
        },
        {
            "asset_id": "motor_002",
            "updated_at": "2026-06-05T11:40:00Z",
            "status_label": "ATENÇÃO",
            "registry_validation_status": "warning",
            "registry_warnings": [{"code": "unexpected_metrics", "message": "Métrica fora do cadastro."}],
        },
    ]

    rows = _indoor_health_rows(
        inventory,
        states,
        now=datetime(2026, 6, 5, 12, 5, tzinfo=UTC),
        timeout_min=10,
    )
    summary = _indoor_health_summary(rows)
    warning_rows = _indoor_registry_warning_rows(inventory, states)

    assert [row["Comunicação"] for row in rows] == ["Comunicando", "Sem comunicação", "Sem payload"]
    assert rows[0]["Idade"] == "5 min"
    assert rows[1]["Cadastro"] == "Avisos"
    assert summary["gateway_status"] == "Parcial"
    assert summary["communicating"] == 1
    assert summary["silent"] == 1
    assert summary["without_payload"] == 1
    assert summary["registry_warnings"] == 1
    assert warning_rows[0]["Ativo"] == "motor_002"
    assert warning_rows[0]["Código"] == "unexpected_metrics"


def test_latest_alert_summary_uses_most_recent_detection() -> None:
    summary = _latest_alert_summary(
        [
            {
                "asset_id": "motor_001",
                "status_label": "ATENÇÃO",
                "last_detected_at": "2026-06-05T11:00:00Z",
            },
            {
                "asset_name": "Esteira principal",
                "status_label": "CRÍTICO",
                "last_detected_at": "2026-06-05T12:00:00Z",
            },
        ]
    )

    assert summary == {
        "count": 2,
        "label": "Esteira principal | CRÍTICO",
        "timestamp": "2026-06-05T12:00:00Z",
    }


def test_multivendor_asset_templates_suggest_expected_metrics() -> None:
    motor_options = _metric_options_for_asset_type("Motor elétrico")
    lubrication_options = _metric_options_for_asset_type("Sistema de Lubrificação")
    unknown_options = _metric_options_for_asset_type("Outro")

    assert "vibration_rms_mm_s" in motor_options
    assert "current_a" in motor_options
    assert "pressure_saida_graxa_01_bar" in lubrication_options
    assert "health_score" in unknown_options


def test_parameter_rule_supports_higher_or_lower_is_worse() -> None:
    higher = _parameter_rule_for_metric(
        asset_id="motor_real_01",
        metric="vibration_rms_mm_s",
        direction="Maior é pior",
        normal_limit=2.8,
        attention_limit=2.8,
        alert_limit=4.5,
        critical_limit=7.1,
        persistence_min=3,
        recommended_action="Inspecionar.",
    )
    lower = _parameter_rule_for_metric(
        asset_id="motor_real_01",
        metric="health_score",
        direction="Menor é pior",
        normal_limit=75,
        attention_limit=75,
        alert_limit=55,
        critical_limit=35,
        persistence_min=2,
        recommended_action="Avaliar.",
    )

    assert higher["critical_min"] == 7.1
    assert higher["critical_max"] == 0
    assert lower["normal_min"] == 75
    assert lower["critical_max"] == 35


def test_technical_parameter_rule_supports_ideal_range_and_notes() -> None:
    rule = _technical_parameter_rule_for_metric(
        asset_id="motor_real_01",
        metric="current_a",
        direction="Faixa ideal",
        normal_limit=0,
        attention_limit=0,
        alert_limit=0,
        critical_limit=0,
        persistence_min=3,
        recommended_action="Verificar carga elétrica.",
        unit="A",
        technical_note="Faixa inicial baseada na placa do motor.",
        normal_min=8,
        normal_max=12,
        attention_min=7,
        attention_max=13,
        alert_min=6,
        alert_max=14,
        critical_min=5,
        critical_max=15,
    )

    assert rule["rule_mode"] == "ideal_range"
    assert rule["normal_min"] == 8
    assert rule["normal_max"] == 12
    assert rule["critical_min"] == 5
    assert rule["critical_max"] == 15
    assert rule["unit"] == "A"
    assert rule["technical_note"].startswith("Faixa inicial")


def test_gateway_and_sensor_inventory_expose_technical_links() -> None:
    config = {
        "assets": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "asset_id": "motor_001",
                "source_id": "gateway_01",
            }
        ],
        "data_sources": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "source_id": "gateway_01",
                "source_name": "Gateway 01",
                "source_type": "IO-Link Master",
                "manufacturer": "IFM",
                "model": "AL1350",
                "protocol": "IO-Link",
                "endpoint": "http://gateway.local",
                "status": "Ativa",
            }
        ],
        "sensors": [
            {
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "sensor_id": "sensor_01",
                "asset_id": "motor_001",
                "source_id": "gateway_01",
                "sensor_kind": "Vibração",
                "manufacturer": "IFM",
                "model": "VVB001",
                "installation_point": "Mancal lado acoplado",
                "measured_quantity": "Vibração RMS",
                "metric": "vibration_rms_mm_s",
                "expected_min": 0,
                "expected_max": 10,
                "unit": "mm/s",
                "status": "Ativo",
            }
        ],
    }

    gateways = _gateway_inventory_rows(config, tenant_id="cliente_a", plant_id="planta_1")
    sensors = _sensor_inventory_rows(config, tenant_id="cliente_a", plant_id="planta_1")

    assert gateways[0]["Ativos vinculados"] == "motor_001"
    assert gateways[0]["Fabricante / modelo"] == "IFM / AL1350"
    assert sensors[0]["Ativo"] == "motor_001"
    assert sensors[0]["Ponto de instalação"] == "Mancal lado acoplado"
    assert sensors[0]["Faixa esperada"] == "0 a 10 mm/s"


def test_technical_history_rows_scope_and_summarize_revisions() -> None:
    config = {
        "configuration_version": 3,
        "technical_change_history": [
            {
                "revision": 2,
                "change_id": "change-2",
                "changed_at": "2026-06-05T12:00:00Z",
                "changed_by": "admin@sentinela.com.br",
                "changed_by_role": "admin",
                "tenant_id": "cliente_a",
                "plant_id": "planta_1",
                "change_type": "technical_registry.upsert",
                "target": "asset:motor_001",
                "reason": "Ajuste de criticidade.",
                "changes": [
                    {
                        "section": "assets",
                        "entity_key": "motor_001",
                        "operation": "updated",
                    },
                    {
                        "section": "parameters_alerts",
                        "entity_key": "motor_001#vibration_rms_mm_s",
                        "operation": "updated",
                    },
                ],
            },
            {
                "revision": 3,
                "change_id": "change-3",
                "tenant_id": "cliente_b",
                "plant_id": "planta_2",
                "changes": [],
            },
            {
                "revision": 4,
                "change_id": "change-without-context",
                "changes": [],
            },
        ],
    }

    history = _technical_history_for_context(config, tenant_id="cliente_a", plant_id="planta_1")
    rows = _technical_history_rows(config, tenant_id="cliente_a", plant_id="planta_1")

    assert [revision["revision"] for revision in history] == [2]
    assert rows[0]["Versão"] == 2
    assert rows[0]["Autor"] == "admin@sentinela.com.br"
    assert rows[0]["Motivo"] == "Ajuste de criticidade."
    assert rows[0]["Seções"] == "assets, parameters_alerts"
    assert rows[0]["Alterações"] == 2


def test_replace_by_keys_upserts_without_duplicating_operational_records() -> None:
    items = [
        {"asset_id": "motor_001", "metric": "temperature_c", "value": 1},
        {"asset_id": "motor_001", "metric": "vibration_rms_mm_s", "value": 2},
    ]

    result = _replace_by_keys(
        items,
        {"asset_id": "motor_001", "metric": "vibration_rms_mm_s", "value": 3},
        ["asset_id", "metric"],
    )

    assert len(result) == 2
    assert result[-1]["value"] == 3


def test_onboarding_step_rows_require_assisted_production_before_release() -> None:
    data = _sample_platform_data()
    data["users"].extend(
        [
            {"tenant_id": "cliente_a", "email": "tecnico@cliente-a.com", "role": "tecnico", "status": "Ativo"},
            {"tenant_id": "cliente_a", "email": "operador@cliente-a.com", "role": "operador", "status": "Ativo"},
        ]
    )
    operational_config = {
        "assets": [{"tenant_id": "cliente_a", "plant_id": "planta_1", "asset_id": "motor_001"}],
        "data_sources": [{"source_id": "gateway_01"}],
        "sensors": [{"sensor_id": "sensor_01", "asset_id": "motor_001", "source_id": "gateway_01"}],
        "signal_map": [{"asset_id": "motor_001", "metric": "vibration_rms_mm_s"}],
        "parameters_alerts": [{"asset_id": "motor_001", "metric": "vibration_rms_mm_s"}],
    }
    run = {
        "manual_steps": {"commissioning": True, "release": False},
        "assisted_checks": {str(item["id"]): True for item in ASSISTED_PRODUCTION_CHECKS},
    }

    rows = _onboarding_step_rows(data, operational_config, run, tenant_id="cliente_a", plant_id="planta_1")
    summary = _onboarding_summary(rows)

    assert rows[-2]["Status"] == "OK"
    assert rows[-2]["Evidência"] == "Itens validados: 10/10"
    assert rows[-1]["Status"] == "Pendente"
    assert summary == {"percent": 88, "done": 7, "total": 8, "status": "Em implantação"}


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
    assert "platform_real_asset_sensor_gateway_form" in source
    assert "platform_assisted_production_form" in source
