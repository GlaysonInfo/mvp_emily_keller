from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import streamlit as st

try:
    from dashboard.alerts_repository import create_alerts_repository_from_env
    from dashboard.config_repository import ConfigRepository
    from dashboard.hmi.hmi_sidebar import set_operator_page_for_route
    from dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
    from dashboard.multiasset_repository import create_multiasset_repository_from_env
    from dashboard.navigation import render_navigation_icon
    from dashboard.platform_admin_repository import PlatformAdminRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alerts_repository import create_alerts_repository_from_env
    from src.dashboard.config_repository import ConfigRepository
    from src.dashboard.hmi.hmi_sidebar import set_operator_page_for_route
    from src.dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
    from src.dashboard.multiasset_repository import create_multiasset_repository_from_env
    from src.dashboard.navigation import render_navigation_icon
    from src.dashboard.platform_admin_repository import PlatformAdminRepository


PAGE_NAME = "Admin da Plataforma"

TENANT_STATUS = ["Ativo", "Piloto", "Suspenso", "Inativo"]
PLANT_STATUS = ["Ativa", "Piloto", "Inativa"]
CONTRACT_STATUS = ["Ativo", "Piloto", "Suspenso", "Inativo"]
ENVIRONMENTS = ["Demonstração", "Piloto", "Produção"]
SERVICE_DISPLAY_NAMES = {
    "condition": "Monitoramento de Equipamentos",
    "lubrication": "Sistema de Lubrificação",
}
ASSET_TYPE_OPTIONS = [
    "Motor elétrico",
    "Bomba centrífuga",
    "Compressor",
    "Redutor",
    "Ventilador",
    "Exaustor",
    "Transportador",
    "Misturador",
    "Sistema de Lubrificação",
    "Outro",
]
CRITICALITY_OPTIONS = ["Baixa", "Média", "Alta", "Crítica"]
GATEWAY_PROTOCOL_OPTIONS = [
    "HTTP/HTTPS API",
    "OPC UA via HTTPS",
    "IO-Link",
    "Modbus TCP",
    "MQTT",
    "CSV",
    "Manual",
]
GATEWAY_STATUS_OPTIONS = ["Aguardando comissionamento", "Configurada", "Ativa", "Falha", "Inativa"]
SENSOR_KIND_OPTIONS = [
    "Vibração",
    "Temperatura",
    "Pressão",
    "Ultrassom",
    "Corrente",
    "Rotação",
    "Score",
    "Outro",
]
METRIC_TEMPLATE_BY_ASSET_TYPE = {
    "Motor elétrico": ["vibration_rms_mm_s", "temperature_c", "current_a", "rpm", "health_score"],
    "Bomba centrífuga": ["vibration_rms_mm_s", "temperature_c", "pressure_bar", "rpm", "health_score"],
    "Compressor": ["vibration_rms_mm_s", "temperature_c", "pressure_bar", "ultrasound_db", "health_score"],
    "Redutor": ["vibration_rms_mm_s", "temperature_c", "oil_temperature_c", "health_score"],
    "Transportador": ["vibration_rms_mm_s", "temperature_c", "speed_m_min", "health_score"],
    "Sistema de Lubrificação": [
        "pressure_saida_graxa_01_bar",
        "peak_saida_graxa_01_bar",
        "rise_time_saida_graxa_01_sec",
        "decay_time_saida_graxa_01_sec",
    ],
}
DEFAULT_METRIC_OPTIONS = [
    "vibration_rms_mm_s",
    "temperature_c",
    "pressure_bar",
    "ultrasound_db",
    "current_a",
    "rpm",
    "health_score",
    "severity_score",
]
UNIT_BY_METRIC = {
    "vibration_rms_mm_s": "mm/s",
    "temperature_c": "°C",
    "pressure_bar": "bar",
    "ultrasound_db": "dB",
    "current_a": "A",
    "rpm": "rpm",
    "health_score": "score",
    "severity_score": "score",
    "pressure_saida_graxa_01_bar": "bar",
    "peak_saida_graxa_01_bar": "bar",
    "rise_time_saida_graxa_01_sec": "s",
    "decay_time_saida_graxa_01_sec": "s",
}
PAGE_TARGET_KEY = "dashboard_page_target"
PENDING_CONDITION_ASSET_KEY = "condition_pending_selected_asset_id"
INDOOR_COMMUNICATION_TIMEOUT_MIN = 10

ONBOARDING_STEPS = [
    {
        "Etapa": "1. Cliente",
        "Responsável": "Admin Sentinela",
        "Resultado esperado": "Tenant criado, ambiente definido e primeiro Admin do Cliente indicado.",
    },
    {
        "Etapa": "2. Planta",
        "Responsável": "Admin Sentinela",
        "Resultado esperado": "Unidade/planta cadastrada e vinculada ao tenant correto.",
    },
    {
        "Etapa": "3. Contrato",
        "Responsável": "Admin Sentinela",
        "Resultado esperado": "Módulos contratados por planta: condition, lubrication ou ambos.",
    },
    {
        "Etapa": "4. Usuários",
        "Responsável": "Admin do Cliente + Sentinela",
        "Resultado esperado": "Perfis Cognito com grupo de papel e grupo TENANT_<id>.",
    },
    {
        "Etapa": "5. Ativos e sensores",
        "Responsável": "Técnico + Sentinela",
        "Resultado esperado": "Ativos, sensores, gateway, tags e limites iniciais mapeados.",
    },
    {
        "Etapa": "6. Comissionamento",
        "Responsável": "Técnico + Operação",
        "Resultado esperado": "Ingestão validada, alertas revisados e aceite de baseline registrado.",
    },
]

ONBOARDING_STEP_DEFINITIONS = [
    {
        "id": "tenant",
        "etapa": "1. Cliente",
        "responsavel": "Admin Sentinela",
        "criterio": "Tenant ativo, ambiente definido e empresa identificada.",
        "acao": "Cadastrar ou revisar cliente.",
        "rota": "Admin da Plataforma",
    },
    {
        "id": "plant",
        "etapa": "2. Planta",
        "responsavel": "Admin Sentinela",
        "criterio": "Planta vinculada ao tenant e status operacional definido.",
        "acao": "Cadastrar ou revisar planta.",
        "rota": "Admin da Plataforma",
    },
    {
        "id": "contract",
        "etapa": "3. Contrato",
        "responsavel": "Admin Sentinela",
        "criterio": "Módulos contratados habilitados por planta.",
        "acao": "Definir Monitoramento, Lubrificação ou ambos.",
        "rota": "Admin da Plataforma",
    },
    {
        "id": "users",
        "etapa": "4. Usuários",
        "responsavel": "Admin Cliente + Sentinela",
        "criterio": "Admin Cliente, Técnico e Operador previstos para o tenant.",
        "acao": "Criar usuários e grupos Cognito.",
        "rota": "Admin do Cliente",
    },
    {
        "id": "assets_sensors",
        "etapa": "5. Ativos e sensores",
        "responsavel": "Técnico + Sentinela",
        "criterio": "Ativos, fontes, sinais e parâmetros mínimos cadastrados.",
        "acao": "Cadastrar ativos, sensores, gateway, tags e limites.",
        "rota": "Configurações",
    },
    {
        "id": "commissioning",
        "etapa": "6. Comissionamento",
        "responsavel": "Técnico + Operação",
        "criterio": "Ingestão validada, alertas revisados e baseline aceito.",
        "acao": "Validar ponta a ponta e registrar aceite técnico.",
        "rota": "Teste ponta a ponta",
        "manual": True,
    },
    {
        "id": "assisted_production",
        "etapa": "7. Produção assistida",
        "responsavel": "Admin Sentinela + Técnico",
        "criterio": "Máquina real, sensores, gateway, HTTPS, payload e alerta de teste validados.",
        "acao": "Completar checklist indoor antes de liberar operação.",
        "rota": "Onboarding do Cliente",
        "manual": True,
    },
    {
        "id": "release",
        "etapa": "8. Liberação",
        "responsavel": "Admin Sentinela",
        "criterio": "Cliente liberado para operação assistida ou produção.",
        "acao": "Liberar acesso operacional e orientar operação.",
        "rota": "Admin da Plataforma",
        "manual": True,
    },
]

ASSISTED_PRODUCTION_CHECKS = [
    {
        "id": "real_machine_identified",
        "item": "Máquina real identificada",
        "criterion": "Ativo físico, tag/local e criticidade confirmados.",
        "owner": "Sentinela + Cliente",
    },
    {
        "id": "real_sensors_installed",
        "item": "Sensores reais instalados",
        "criterion": "Sensores, grandezas e pontos de medição conferidos em campo.",
        "owner": "Técnico",
    },
    {
        "id": "gateway_registered",
        "item": "Gateway cadastrado",
        "criterion": "Fonte/gateway vinculada à planta e ao ativo correto.",
        "owner": "Sentinela",
    },
    {
        "id": "https_endpoint_validated",
        "item": "Endpoint HTTPS validado",
        "criterion": "Gateway alcança o endpoint de ingestão por HTTPS.",
        "owner": "Técnico",
    },
    {
        "id": "token_configured",
        "item": "Token configurado",
        "criterion": "Token de ingestão configurado no gateway sem exposição em tela ou arquivo versionado.",
        "owner": "Sentinela",
    },
    {
        "id": "first_payload_received",
        "item": "Primeiro payload recebido",
        "criterion": "Payload real gravado com tenant, planta, ativo e timestamp corretos.",
        "owner": "Sentinela",
    },
    {
        "id": "last_communication_visible",
        "item": "Última comunicação visível",
        "criterion": "Dashboard mostra comunicação recente do ativo real.",
        "owner": "Sentinela",
    },
    {
        "id": "test_alert_generated",
        "item": "Alerta de teste gerado",
        "criterion": "Cenário controlado gera alerta esperado sem afetar operação real.",
        "owner": "Sentinela + Técnico",
    },
    {
        "id": "test_alert_acknowledged",
        "item": "Alerta reconhecido/tratado",
        "criterion": "Fluxo de ciência e tratamento foi executado por usuário autorizado.",
        "owner": "Operação",
    },
    {
        "id": "stop_criteria_defined",
        "item": "Critério de parada definido",
        "criterion": "Condições de pausa do teste, contato responsável e fallback documentados.",
        "owner": "Sentinela + Cliente",
    },
]

SUPPORT_SCOPES = [
    {
        "Domínio": "Suporte remoto",
        "Uso": "Atendimento a incidente, dúvida técnica ou ajuste assistido em cliente.",
        "Controle exigido": "Selecionar tenant/planta, motivo ou ticket e registrar auditoria.",
    },
    {
        "Domínio": "Demonstrações",
        "Uso": "Bancada virtual, eficiência integrada e simulações para novos clientes.",
        "Controle exigido": "Restrito ao Admin Sentinela ou ambiente de demonstração.",
    },
    {
        "Domínio": "Notificações",
        "Uso": "Auditar fila de notificações, falhas de envio e reprocessamento.",
        "Controle exigido": "Acesso administrativo; Cliente Admin no futuro apenas read-only.",
    },
    {
        "Domínio": "Escalonamento",
        "Uso": "Definir quem é avisado por severidade, tempo sem ciência e SLA.",
        "Controle exigido": "Template global Sentinela + política local do cliente.",
    },
]


def _index(options: list[str], value: Any, default: int = 0) -> int:
    try:
        return options.index(str(value))
    except ValueError:
        return default


def _service_options() -> dict[str, str]:
    return {
        str(service["module_key"]): SERVICE_DISPLAY_NAMES.get(str(service["module_key"]), str(service["service"]))
        for service in SERVICE_BLUEPRINTS
    }


def _status_is_active(value: Any) -> bool:
    return str(value or "").strip().lower() == "ativo"


def _platform_summary(data: dict[str, Any]) -> dict[str, int]:
    contracts = list(data.get("service_contracts") or [])
    tenants = list(data.get("tenants") or [])
    plants = list(data.get("plants") or [])
    return {
        "tenants": len(tenants),
        "active_tenants": sum(1 for tenant in tenants if _status_is_active(tenant.get("status"))),
        "plants": len(plants),
        "contracts": len(contracts),
        "active_contracts": sum(1 for contract in contracts if _status_is_active(contract.get("status"))),
        "condition_contracts": sum(1 for contract in contracts if "condition" in (contract.get("services") or [])),
        "lubrication_contracts": sum(1 for contract in contracts if "lubrication" in (contract.get("services") or [])),
        "dual_service_contracts": sum(1 for contract in contracts if contract.get("operational_intelligence")),
    }


def _contract_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    service_labels = _service_options()
    rows = []
    for contract in data.get("service_contracts") or []:
        service_names = [service_labels.get(service, service) for service in contract.get("services") or []]
        rows.append(
            {
                "Cliente": contract.get("tenant_id"),
                "Planta": contract.get("plant_id"),
                "Módulos contratados": ", ".join(service_names) or "-",
                "Inteligência Operacional": "Sim" if contract.get("operational_intelligence") else "Não",
                "Status": contract.get("status"),
            }
        )
    return rows


def _tenant_onboarding_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    plants_by_tenant: dict[str, int] = {}
    contracts_by_tenant: dict[str, int] = {}
    users_by_tenant: dict[str, int] = {}
    for plant in data.get("plants") or []:
        tenant_id = str(plant.get("tenant_id") or "")
        plants_by_tenant[tenant_id] = plants_by_tenant.get(tenant_id, 0) + 1
    for contract in data.get("service_contracts") or []:
        tenant_id = str(contract.get("tenant_id") or "")
        contracts_by_tenant[tenant_id] = contracts_by_tenant.get(tenant_id, 0) + 1
    for user in data.get("users") or []:
        tenant_id = str(user.get("tenant_id") or "")
        users_by_tenant[tenant_id] = users_by_tenant.get(tenant_id, 0) + 1

    rows = []
    for tenant in data.get("tenants") or []:
        tenant_id = str(tenant.get("tenant_id") or "")
        missing = []
        if plants_by_tenant.get(tenant_id, 0) == 0:
            missing.append("planta")
        if contracts_by_tenant.get(tenant_id, 0) == 0:
            missing.append("contrato")
        if users_by_tenant.get(tenant_id, 0) == 0:
            missing.append("admin do cliente")
        rows.append(
            {
                "Cliente": tenant_id,
                "Empresa": tenant.get("company_name"),
                "Ambiente": tenant.get("environment"),
                "Status": tenant.get("status"),
                "Plantas": plants_by_tenant.get(tenant_id, 0),
                "Contratos": contracts_by_tenant.get(tenant_id, 0),
                "Usuários": users_by_tenant.get(tenant_id, 0),
                "Próxima ação": "OK" if not missing else "Cadastrar " + ", ".join(missing),
            }
        )
    return rows


def _contract_for(data: dict[str, Any], tenant_id: str, plant_id: str) -> dict[str, Any] | None:
    for contract in data.get("service_contracts") or []:
        if contract.get("tenant_id") == tenant_id and contract.get("plant_id") == plant_id:
            return contract
    return None


def _tenant_for(data: dict[str, Any], tenant_id: str) -> dict[str, Any] | None:
    for tenant in data.get("tenants") or []:
        if tenant.get("tenant_id") == tenant_id:
            return tenant
    return None


def _plant_for(data: dict[str, Any], tenant_id: str, plant_id: str) -> dict[str, Any] | None:
    for plant in data.get("plants") or []:
        if plant.get("tenant_id") == tenant_id and plant.get("plant_id") == plant_id:
            return plant
    return None


def _metric_options_for_asset_type(asset_type: str) -> list[str]:
    options = list(METRIC_TEMPLATE_BY_ASSET_TYPE.get(asset_type) or DEFAULT_METRIC_OPTIONS)
    for metric in DEFAULT_METRIC_OPTIONS:
        if metric not in options:
            options.append(metric)
    return options


def _replace_by_keys(items: list[dict[str, Any]], new_item: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    new_key = tuple(str(new_item.get(key) or "") for key in keys)
    return [item for item in items if tuple(str(item.get(key) or "") for key in keys) != new_key] + [new_item]


def _parameter_rule_for_metric(
    *,
    asset_id: str,
    metric: str,
    direction: str,
    normal_limit: float,
    attention_limit: float,
    alert_limit: float,
    critical_limit: float,
    persistence_min: int,
    recommended_action: str,
) -> dict[str, Any]:
    base = {
        "asset_id": asset_id,
        "metric": metric,
        "normal_max": 0,
        "attention_min": 0,
        "alert_min": 0,
        "critical_min": 0,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": persistence_min,
        "enabled": True,
        "recommended_action": recommended_action,
    }
    if direction == "Menor é pior":
        base.update(
            {
                "normal_min": normal_limit,
                "attention_max": attention_limit,
                "alert_max": alert_limit,
                "critical_max": critical_limit,
            }
        )
    else:
        base.update(
            {
                "normal_max": normal_limit,
                "attention_min": attention_limit,
                "alert_min": alert_limit,
                "critical_min": critical_limit,
            }
        )
    return base


def _technical_parameter_rule_for_metric(
    *,
    asset_id: str,
    metric: str,
    direction: str,
    normal_limit: float,
    attention_limit: float,
    alert_limit: float,
    critical_limit: float,
    persistence_min: int,
    recommended_action: str,
    unit: str = "",
    technical_note: str = "",
    normal_min: float = 0,
    normal_max: float = 0,
    attention_min: float = 0,
    attention_max: float = 0,
    alert_min: float = 0,
    alert_max: float = 0,
    critical_min: float = 0,
    critical_max: float = 0,
) -> dict[str, Any]:
    rule = {
        "asset_id": asset_id,
        "metric": metric,
        "normal_max": 0,
        "attention_min": 0,
        "alert_min": 0,
        "critical_min": 0,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": persistence_min,
        "enabled": True,
        "recommended_action": recommended_action,
    }
    if direction == "Faixa ideal":
        rule.update(
            {
                "rule_mode": "ideal_range",
                "normal_min": normal_min,
                "normal_max": normal_max,
                "attention_min": attention_min,
                "attention_max": attention_max,
                "alert_min": alert_min,
                "alert_max": alert_max,
                "critical_min": critical_min,
                "critical_max": critical_max,
            }
        )
    elif direction == "Menor é pior":
        rule.update(
            {
                "rule_mode": "lower_is_worse",
                "normal_min": normal_limit,
                "attention_max": attention_limit,
                "alert_max": alert_limit,
                "critical_max": critical_limit,
            }
        )
    else:
        rule.update(
            {
                "rule_mode": "higher_is_worse",
                "normal_max": normal_limit,
                "attention_min": attention_limit,
                "alert_min": alert_limit,
                "critical_min": critical_limit,
            }
        )

    rule["unit"] = unit
    rule["technical_note"] = technical_note
    return rule


def _operational_assets_for(
    data: dict[str, Any],
    operational_config: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> list[dict[str, Any]]:
    return _asset_inventory_rows(data, operational_config, tenant_id=tenant_id, plant_id=plant_id)


def _onboarding_step_rows(
    data: dict[str, Any],
    operational_config: dict[str, Any],
    run: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> list[dict[str, Any]]:
    tenant = next((item for item in data.get("tenants") or [] if item.get("tenant_id") == tenant_id), None)
    plant = next(
        (
            item
            for item in data.get("plants") or []
            if item.get("tenant_id") == tenant_id and item.get("plant_id") == plant_id
        ),
        None,
    )
    contract = _contract_for(data, tenant_id, plant_id)
    services = set(contract.get("services") or []) if contract else set()
    users = [item for item in data.get("users") or [] if item.get("tenant_id") == tenant_id]
    roles = {str(item.get("role") or "").strip() for item in users}
    assets = _operational_assets_for(data, operational_config, tenant_id=tenant_id, plant_id=plant_id)
    source_count = len(operational_config.get("data_sources") or [])
    sensor_count = len(operational_config.get("sensors") or [])
    signal_count = len(operational_config.get("signal_map") or operational_config.get("asset_signal_map") or [])
    parameter_count = len(operational_config.get("parameters_alerts") or [])
    manual_steps = dict(run.get("manual_steps") or {})
    assisted_checks = dict(run.get("assisted_checks") or {})
    assisted_done = sum(1 for item in ASSISTED_PRODUCTION_CHECKS if assisted_checks.get(str(item["id"])))
    assisted_total = len(ASSISTED_PRODUCTION_CHECKS)

    evidence_by_step = {
        "tenant": bool(tenant and str(tenant.get("status") or "").strip()),
        "plant": bool(plant and str(plant.get("status") or "").strip()),
        "contract": bool(contract and services),
        "users": {"cliente_admin", "tecnico", "operador"}.issubset(roles),
        "assets_sensors": bool(assets and source_count and sensor_count and signal_count and parameter_count),
        "commissioning": bool(manual_steps.get("commissioning")),
        "assisted_production": bool(assisted_total and assisted_done == assisted_total),
        "release": bool(manual_steps.get("release")),
    }
    detail_by_step = {
        "tenant": tenant.get("company_name") if tenant else "Cliente não cadastrado",
        "plant": plant.get("plant_name") if plant else "Planta não cadastrada",
        "contract": ", ".join(SERVICE_DISPLAY_NAMES.get(service, service) for service in sorted(services)) or "Sem módulos",
        "users": f"Perfis: {', '.join(sorted(role for role in roles if role)) or '-'}",
        "assets_sensors": (
            f"Ativos: {len(assets)} | Sensores: {sensor_count} | Fontes: {source_count} | "
            f"Sinais: {signal_count} | Parâmetros: {parameter_count}"
        ),
        "commissioning": "Aceite técnico registrado" if manual_steps.get("commissioning") else "Aguardando validação",
        "assisted_production": f"Itens validados: {assisted_done}/{assisted_total}",
        "release": "Liberado" if manual_steps.get("release") else "Aguardando liberação",
    }

    rows = []
    for definition in ONBOARDING_STEP_DEFINITIONS:
        step_id = str(definition["id"])
        done = bool(evidence_by_step.get(step_id))
        rows.append(
            {
                "Status": "OK" if done else "Pendente",
                "Etapa": definition["etapa"],
                "Responsável": definition["responsavel"],
                "Critério": definition["criterio"],
                "Evidência": detail_by_step.get(step_id, "-"),
                "Próxima ação": "Concluído" if done else definition["acao"],
                "Rota": definition["rota"],
                "step_id": step_id,
                "done": done,
            }
        )
    return rows


def _onboarding_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    done = sum(1 for row in rows if row.get("done"))
    percent = int(round((done / total) * 100)) if total else 0
    return {
        "done": done,
        "total": total,
        "percent": percent,
        "status": "Pronto para liberação" if done == total else "Em implantação",
    }


def _assisted_production_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    checks = dict(run.get("assisted_checks") or {})
    rows = []
    for item in ASSISTED_PRODUCTION_CHECKS:
        done = bool(checks.get(str(item["id"])))
        rows.append(
            {
                "Status": "OK" if done else "Pendente",
                "Item": item["item"],
                "Critério": item["criterion"],
                "Responsável": item["owner"],
                "check_id": item["id"],
                "done": done,
            }
        )
    return rows


def _assisted_production_summary(run: dict[str, Any]) -> dict[str, int]:
    rows = _assisted_production_rows(run)
    total = len(rows)
    done = sum(1 for row in rows if row.get("done"))
    percent = int(round((done / total) * 100)) if total else 0
    return {"done": done, "total": total, "percent": percent}


def _render_table(items: list[dict[str, Any]], empty_message: str) -> None:
    if not items:
        st.info(empty_message)
        return
    st.dataframe(items, width="stretch", hide_index=True)


def _navigate_to(route: str, *, asset_id: str | None = None, outlet_id: str | None = None) -> None:
    if asset_id:
        st.session_state["selected_asset_id"] = asset_id
        st.session_state[PENDING_CONDITION_ASSET_KEY] = asset_id
    if outlet_id:
        st.session_state["selected_outlet_id"] = outlet_id
    st.session_state[PAGE_TARGET_KEY] = route
    set_operator_page_for_route(route)
    st.rerun()


def _render_inventory_action_table(inventory_rows: list[dict[str, Any]]) -> None:
    if not inventory_rows:
        st.info("Nenhum ativo cadastrado para esta planta.")
        return

    header = st.columns([1.0, 1.5, 1.1, 1.0, 0.85, 0.75, 0.75, 0.8])
    header[0].caption("Ativo")
    header[1].caption("Nome")
    header[2].caption("Tipo")
    header[3].caption("Área")
    header[4].caption("Status")
    header[5].caption("Sinais")
    header[6].caption("Parâmetros")
    header[7].caption("Ações")

    for item in inventory_rows:
        asset_id = str(item.get("Ativo") or "").strip()
        if not asset_id:
            continue
        row = st.columns([1.0, 1.5, 1.1, 1.0, 0.85, 0.75, 0.75, 0.8])
        row[0].write(asset_id)
        row[1].write(str(item.get("Nome") or "-"))
        row[2].write(str(item.get("Tipo") or "-"))
        row[3].write(str(item.get("Área") or item.get("Ãrea") or "-"))
        row[4].write(str(item.get("Status") or "-"))
        row[5].write(str(item.get("Sinais") or 0))
        row[6].write(str(item.get("Parâmetros") or item.get("ParÃ¢metros") or 0))
        actions = row[7].columns(3)
        with actions[0]:
            render_navigation_icon(
                "Monitoramento de Equipamentos",
                label="Monitorar ativo",
                icon=":material/monitoring:",
                asset_id=asset_id,
            )
        with actions[1]:
            render_navigation_icon(
                "Detalhe do Ativo",
                label="Abrir detalhe do ativo",
                icon=":material/manage_search:",
                asset_id=asset_id,
            )
        with actions[2]:
            render_navigation_icon(
                "Alertas e Eventos",
                label="Ver alertas do ativo",
                icon=":material/notifications_active:",
                asset_id=asset_id,
            )


def _asset_inventory_rows(
    data: dict[str, Any],
    operational_config: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> list[dict[str, Any]]:
    assets = list(data.get("assets") or []) + list(operational_config.get("assets") or [])
    signal_map = list(operational_config.get("signal_map") or operational_config.get("asset_signal_map") or [])
    parameters = list(operational_config.get("parameters_alerts") or [])

    rows = []
    seen: set[str] = set()
    for asset in assets:
        asset_tenant = str(asset.get("tenant_id") or tenant_id)
        asset_plant = str(asset.get("plant_id") or plant_id)
        if asset_tenant != tenant_id or asset_plant != plant_id:
            continue
        asset_id = str(asset.get("asset_id") or "").strip()
        if not asset_id or asset_id in seen:
            continue
        seen.add(asset_id)
        asset_signals = [item for item in signal_map if str(item.get("asset_id") or "") == asset_id]
        asset_parameters = [item for item in parameters if str(item.get("asset_id") or "") == asset_id]
        rows.append(
            {
                "Ativo": asset_id,
                "Nome": asset.get("asset_name") or asset.get("name") or asset_id,
                "Tipo": asset.get("asset_type") or asset.get("type") or "-",
                "Área": asset.get("area") or "-",
                "Criticidade": asset.get("criticality") or "-",
                "Fonte": asset.get("source_id") or "-",
                "Sinais": len(asset_signals),
                "Parâmetros": len(asset_parameters),
                "Status": asset.get("status") or "Ativo",
            }
        )
    return rows


def _data_source_rows(operational_config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for source in operational_config.get("data_sources") or []:
        rows.append(
            {
                "Fonte": source.get("source_id"),
                "Nome": source.get("source_name"),
                "Tipo": source.get("source_type"),
                "Protocolo": source.get("protocol"),
                "Status": source.get("status"),
            }
        )
    return rows


def _sensor_inventory_rows(
    operational_config: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> list[dict[str, Any]]:
    asset_ids = {
        str(asset.get("asset_id") or "")
        for asset in operational_config.get("assets") or []
        if str(asset.get("tenant_id") or tenant_id) == tenant_id
        and str(asset.get("plant_id") or plant_id) == plant_id
    }
    rows = []
    for sensor in operational_config.get("sensors") or []:
        asset_id = str(sensor.get("asset_id") or "")
        if asset_ids and asset_id not in asset_ids:
            continue
        rows.append(
            {
                "Sensor": sensor.get("sensor_id") or "-",
                "Ativo": asset_id or "-",
                "Tipo": sensor.get("sensor_kind") or "-",
                "Fabricante / modelo": " / ".join(
                    value
                    for value in [str(sensor.get("manufacturer") or ""), str(sensor.get("model") or "")]
                    if value
                )
                or "-",
                "Ponto de instalação": sensor.get("installation_point") or "-",
                "Grandeza": sensor.get("measured_quantity") or sensor.get("metric") or "-",
                "Métrica": sensor.get("metric") or "-",
                "Faixa esperada": f"{sensor.get('expected_min', '-')} a {sensor.get('expected_max', '-')} {sensor.get('unit', '')}".strip(),
                "Fonte": sensor.get("source_id") or "-",
                "Status": sensor.get("status") or "Aguardando comissionamento",
            }
        )
    return rows


def _gateway_inventory_rows(
    operational_config: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> list[dict[str, Any]]:
    assets = [
        asset
        for asset in operational_config.get("assets") or []
        if str(asset.get("tenant_id") or tenant_id) == tenant_id
        and str(asset.get("plant_id") or plant_id) == plant_id
    ]
    rows = []
    for source in operational_config.get("data_sources") or []:
        source_tenant = str(source.get("tenant_id") or tenant_id)
        source_plant = str(source.get("plant_id") or plant_id)
        if source_tenant != tenant_id or source_plant != plant_id:
            continue
        source_id = str(source.get("source_id") or "")
        linked_assets = [
            str(asset.get("asset_id") or "")
            for asset in assets
            if str(asset.get("source_id") or "") == source_id
        ]
        rows.append(
            {
                "Gateway": source_id or "-",
                "Nome": source.get("source_name") or "-",
                "Tipo": source.get("source_type") or "-",
                "Fabricante / modelo": " / ".join(
                    value
                    for value in [str(source.get("manufacturer") or ""), str(source.get("model") or "")]
                    if value
                )
                or "-",
                "Protocolo": source.get("protocol") or "-",
                "Endpoint": source.get("endpoint") or "-",
                "Ativos vinculados": ", ".join(linked_assets) or "-",
                "Status": source.get("status") or "-",
            }
        )
    return rows


def _parse_utc_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _state_timestamp(state: dict[str, Any]) -> datetime | None:
    for key in ["updated_at", "last_payload_timestamp", "source_updated_at_utc", "received_at"]:
        parsed = _parse_utc_datetime(state.get(key))
        if parsed:
            return parsed
    return None


def _age_minutes(timestamp: datetime | None, *, now: datetime | None = None) -> int | None:
    if not timestamp:
        return None
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    delta = reference.astimezone(UTC) - timestamp.astimezone(UTC)
    return max(0, int(delta.total_seconds() // 60))


def _age_label(minutes: int | None) -> str:
    if minutes is None:
        return "Sem payload"
    if minutes < 1:
        return "Agora"
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    remaining = minutes % 60
    return f"{hours}h {remaining}min" if remaining else f"{hours}h"


def _registry_warning_count(state: dict[str, Any]) -> int:
    warnings = state.get("registry_warnings")
    return len(warnings) if isinstance(warnings, list) else 0


def _indoor_health_rows(
    inventory_rows: list[dict[str, Any]],
    current_states: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    timeout_min: int = INDOOR_COMMUNICATION_TIMEOUT_MIN,
) -> list[dict[str, Any]]:
    states_by_asset = {str(state.get("asset_id") or ""): state for state in current_states}
    rows: list[dict[str, Any]] = []

    for asset in inventory_rows:
        asset_id = str(asset.get("Ativo") or "").strip()
        state = states_by_asset.get(asset_id, {})
        timestamp = _state_timestamp(state)
        age = _age_minutes(timestamp, now=now)
        warning_count = _registry_warning_count(state)

        if age is None:
            communication = "Sem payload"
        elif age > timeout_min:
            communication = "Sem comunicação"
        else:
            communication = "Comunicando"

        registry_status = str(state.get("registry_validation_status") or "sem_validacao")
        if registry_status == "ok":
            registry_label = "OK"
        elif registry_status == "warning":
            registry_label = "Avisos"
        else:
            registry_label = "Sem validação"

        health_value = state.get("health_score")
        try:
            health_label = f"{float(health_value):.1f}" if health_value is not None else "-"
        except (TypeError, ValueError):
            health_label = str(health_value or "-")

        rows.append(
            {
                "Ativo": asset_id,
                "Nome": asset.get("Nome") or asset_id,
                "Fonte": asset.get("Fonte") or state.get("source") or "-",
                "Comunicação": communication,
                "Idade": _age_label(age),
                "Último payload": timestamp.isoformat().replace("+00:00", "Z") if timestamp else "-",
                "Estado": state.get("status_label") or "Sem estado",
                "Health": health_label,
                "Cadastro": registry_label,
                "Pendências": warning_count,
            }
        )

    return rows


def _indoor_health_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    communicating = sum(1 for row in rows if row.get("Comunicação") == "Comunicando")
    silent = sum(1 for row in rows if row.get("Comunicação") == "Sem comunicação")
    without_payload = sum(1 for row in rows if row.get("Comunicação") == "Sem payload")
    warnings = sum(int(row.get("Pendências") or 0) for row in rows)
    latest_payloads = [row.get("Último payload") for row in rows if row.get("Último payload") not in [None, "-"]]
    latest_payload = max(latest_payloads) if latest_payloads else "-"

    if communicating and not silent and not without_payload:
        gateway_status = "Online"
    elif communicating:
        gateway_status = "Parcial"
    elif rows:
        gateway_status = "Sem comunicação"
    else:
        gateway_status = "Sem ativos"

    return {
        "assets": len(rows),
        "communicating": communicating,
        "silent": silent,
        "without_payload": without_payload,
        "registry_warnings": warnings,
        "latest_payload": latest_payload,
        "gateway_status": gateway_status,
    }


def _indoor_registry_warning_rows(
    inventory_rows: list[dict[str, Any]],
    current_states: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    states_by_asset = {str(state.get("asset_id") or ""): state for state in current_states}
    rows: list[dict[str, Any]] = []

    for asset in inventory_rows:
        asset_id = str(asset.get("Ativo") or "").strip()
        state = states_by_asset.get(asset_id, {})
        for warning in state.get("registry_warnings") or []:
            if not isinstance(warning, dict):
                continue
            rows.append(
                {
                    "Ativo": asset_id,
                    "Fonte": asset.get("Fonte") or state.get("source") or "-",
                    "Campo": warning.get("field") or "-",
                    "Código": warning.get("code") or "-",
                    "Pendência": warning.get("message") or "-",
                }
            )

    return rows


def _latest_alert_summary(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    def alert_timestamp(alert: dict[str, Any]) -> datetime:
        for key in ["last_detected_at", "updated_at", "first_detected_at"]:
            parsed = _parse_utc_datetime(alert.get(key))
            if parsed:
                return parsed
        return datetime.min.replace(tzinfo=UTC)

    if not alerts:
        return {"count": 0, "label": "Nenhum alerta ativo", "timestamp": "-"}

    latest = max(alerts, key=alert_timestamp)
    label = (
        latest.get("asset_name")
        or latest.get("asset_id")
        or latest.get("alert_type")
        or latest.get("metric")
        or "Alerta ativo"
    )
    status = latest.get("status_label") or latest.get("severity") or "Ativo"
    timestamp = alert_timestamp(latest)
    return {
        "count": len(alerts),
        "label": f"{label} | {status}",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z")
        if timestamp != datetime.min.replace(tzinfo=UTC)
        else "-",
    }


def _code_version_label() -> str:
    for key in ["APP_VERSION", "GIT_COMMIT", "SOURCE_VERSION", "RELEASE_VERSION"]:
        value = str(os.getenv(key) or "").strip()
        if value:
            return value
    return "Não informado"


def render_platform_admin_page(
    path: str | None = None,
    config_path: str | None = None,
    initial_section: str | None = None,
) -> None:
    repo = PlatformAdminRepository(path)
    data = repo.load()
    config_repo = ConfigRepository(config_path or os.getenv("DASHBOARD_CONFIG_STORE") or None)
    operational_config = config_repo.load()
    summary = _platform_summary(data)

    st.header("Admin Sentinela")
    st.caption(
        "Operação multi-tenant da plataforma: clientes, plantas, contratos, módulos, suporte, demonstrações e governança."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes ativos", f"{summary['active_tenants']}/{summary['tenants']}")
    c2.metric("Plantas", str(summary["plants"]))
    c3.metric("Contratos ativos", f"{summary['active_contracts']}/{summary['contracts']}")
    c4.metric("Com inteligência", str(summary["dual_service_contracts"]))

    if initial_section == "onboarding":
        _render_onboarding_tab(repo, data, operational_config, config_repo)
        return

    tabs = st.tabs(
        [
            "Painel",
            "Onboarding",
            "Saúde Indoor",
            "Clientes",
            "Plantas",
            "Contratos",
            "Suporte e Demo",
            "Governança",
        ]
    )
    with tabs[0]:
        _render_overview_tab(data, summary)
    with tabs[1]:
        _render_onboarding_tab(repo, data, operational_config, config_repo)
    with tabs[2]:
        _render_indoor_health_tab(data, operational_config, repo)
    with tabs[3]:
        _render_tenants_tab(repo, data)
    with tabs[4]:
        _render_plants_tab(repo, data, operational_config)
    with tabs[5]:
        _render_contracts_tab(repo, data)
    with tabs[6]:
        _render_support_tab()
    with tabs[7]:
        _render_governance_tab()


def _render_overview_tab(data: dict[str, Any], summary: dict[str, int]) -> None:
    st.subheader("Painel da plataforma")
    st.caption("Visão executiva para abertura de clientes, acompanhamento de contratos e preparação de suporte.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Monitoramento de equipamentos", str(summary["condition_contracts"]))
    c2.metric("Sistema de lubrificação", str(summary["lubrication_contracts"]))
    c3.metric("Ambos os módulos", str(summary["dual_service_contracts"]))

    st.subheader("Contratos por planta")
    _render_table(_contract_rows(data), "Nenhum contrato configurado para a plataforma.")

    st.subheader("Próximas ações por cliente")
    _render_table(_tenant_onboarding_rows(data), "Nenhum cliente cadastrado.")

    st.subheader("Ordem de implantação do primeiro cliente")
    _render_table(ONBOARDING_STEPS, "Nenhuma etapa de onboarding configurada.")


def _render_indoor_health_tab(
    data: dict[str, Any],
    operational_config: dict[str, Any],
    repo: PlatformAdminRepository,
) -> None:
    st.subheader("Saúde do teste indoor")
    st.caption(
        "Acompanhamento da produção assistida: último payload, comunicação por ativo, gateway, alertas e pendências de cadastro."
    )

    plant_options = [f"{plant['tenant_id']}#{plant['plant_id']}" for plant in data.get("plants") or []]
    if not plant_options:
        st.info("Cadastre uma planta antes de iniciar a produção assistida indoor.")
        return

    selected_plant = st.selectbox("Cliente e planta", plant_options, key="platform_indoor_health_plant")
    tenant_id, _, plant_id = selected_plant.partition("#")
    run = repo.onboarding_run_for(tenant_id, plant_id)
    context = dict(run.get("assisted_context") or {})
    inventory_rows = _asset_inventory_rows(data, operational_config, tenant_id=tenant_id, plant_id=plant_id)

    try:
        current_states = create_multiasset_repository_from_env().list_current_states(tenant_id, plant_id)
        state_load_error = ""
    except Exception as exc:
        current_states = []
        state_load_error = str(exc)

    try:
        active_alerts = create_alerts_repository_from_env().list_alerts(
            tenant_id=tenant_id,
            plant_id=plant_id,
            active_only=True,
        )
        alert_load_error = ""
    except Exception as exc:
        active_alerts = []
        alert_load_error = str(exc)

    rows = _indoor_health_rows(inventory_rows, current_states)
    summary = _indoor_health_summary(rows)
    alert_summary = _latest_alert_summary(active_alerts)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gateway", summary["gateway_status"])
    c2.metric("Comunicando", f"{summary['communicating']}/{summary['assets']}")
    c3.metric("Sem comunicação", str(summary["silent"] + summary["without_payload"]))
    c4.metric("Pendências cadastro", str(summary["registry_warnings"]))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Último payload", str(summary["latest_payload"]))
    c6.metric("Alertas ativos", str(alert_summary["count"]))
    c7.metric("Endpoint", str(context.get("endpoint_url") or "https://sentinelaindustrial.com.br/condition/ingest"))
    c8.metric("Versão em produção", _code_version_label())
    st.caption(f"Último alerta ativo: {alert_summary['label']} | {alert_summary['timestamp']}")

    if state_load_error or alert_load_error:
        st.warning(
            "Não foi possível carregar todos os dados da produção assistida. Verifique credenciais AWS, tabelas e permissões do serviço."
        )
        with st.expander("Detalhes técnicos para suporte", expanded=False):
            if state_load_error:
                st.code(f"Estado atual: {state_load_error}")
            if alert_load_error:
                st.code(f"Alertas: {alert_load_error}")

    st.markdown("#### Comunicação por ativo")
    _render_table(
        rows,
        "Nenhum ativo cadastrado para esta planta. Cadastre ativo, sensor e gateway no onboarding antes do teste indoor.",
    )

    warning_rows = _indoor_registry_warning_rows(inventory_rows, current_states)
    st.markdown("#### Pendências de cadastro detectadas pela ingestão")
    _render_table(
        warning_rows,
        "Nenhuma pendência de cadastro detectada nos últimos estados recebidos.",
    )

    st.markdown("#### Alertas ativos no teste")
    alert_rows = [
        {
            "Ativo": alert.get("asset_name") or alert.get("asset_id") or "-",
            "Tipo": alert.get("alert_type") or alert.get("metric") or "-",
            "Severidade": alert.get("status_label") or alert.get("severity") or "-",
            "Status": alert.get("status") or "-",
            "Última detecção": alert.get("last_detected_at") or alert.get("updated_at") or "-",
            "Ação recomendada": alert.get("recommended_action") or "-",
        }
        for alert in active_alerts
    ]
    _render_table(alert_rows, "Nenhum alerta ativo para a planta selecionada.")

    st.markdown("#### Ações rápidas")
    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("Abrir onboarding", type="primary", use_container_width=True, key="platform_indoor_open_onboarding"):
            _navigate_to("Onboarding do Cliente")
    with action_cols[1]:
        if st.button("Ver monitoramento", use_container_width=True, key="platform_indoor_open_condition"):
            _navigate_to("Monitoramento de Equipamentos")
    with action_cols[2]:
        if st.button("Ver alertas", use_container_width=True, key="platform_indoor_open_alerts"):
            _navigate_to("Alertas e Eventos")


def _render_onboarding_registration_forms(
    repo: PlatformAdminRepository,
    data: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> None:
    st.markdown("#### Cadastro guiado")
    st.caption("Cadastre ou ajuste os dados mínimos para liberar o cliente sem sair do fluxo de onboarding.")

    tenant = _tenant_for(data, tenant_id) or {}
    plant = _plant_for(data, tenant_id, plant_id) or {}
    contract = _contract_for(data, tenant_id, plant_id) or {}
    service_labels = _service_options()

    with st.expander("1. Cliente", expanded=not bool(tenant)):
        with st.form("platform_onboarding_tenant_form"):
            left, right = st.columns(2)
            with left:
                tenant_input = st.text_input(
                    "Tenant ID",
                    value=str(tenant.get("tenant_id") or tenant_id or "cliente_novo"),
                    key="platform_onboarding_tenant_id",
                )
                company_name = st.text_input(
                    "Nome da empresa",
                    value=str(tenant.get("company_name") or ""),
                    key="platform_onboarding_company_name",
                )
            with right:
                tenant_status = st.selectbox(
                    "Status do cliente",
                    TENANT_STATUS,
                    index=_index(TENANT_STATUS, tenant.get("status") or "Piloto", 1),
                    key="platform_onboarding_tenant_status",
                )
                environment = st.selectbox(
                    "Ambiente",
                    ENVIRONMENTS,
                    index=_index(ENVIRONMENTS, tenant.get("environment") or "Piloto", 1),
                    key="platform_onboarding_environment",
                )
            if st.form_submit_button("Salvar cliente", type="primary"):
                try:
                    repo.upsert_tenant(
                        {
                            "tenant_id": tenant_input,
                            "company_name": company_name,
                            "status": tenant_status,
                            "environment": environment,
                        }
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("Cliente salvo no onboarding.")
                    st.rerun()

    with st.expander("2. Planta", expanded=bool(tenant) and not bool(plant)):
        tenant_ids = [str(item.get("tenant_id")) for item in data.get("tenants") or [] if item.get("tenant_id")]
        if tenant_id and tenant_id not in tenant_ids:
            tenant_ids.append(tenant_id)
        with st.form("platform_onboarding_plant_form"):
            left, right = st.columns(2)
            with left:
                plant_tenant = st.selectbox(
                    "Cliente da planta",
                    tenant_ids or [tenant_id or "cliente_novo"],
                    index=_index(tenant_ids or [tenant_id or "cliente_novo"], tenant_id, 0),
                    key="platform_onboarding_plant_tenant",
                )
                plant_input = st.text_input(
                    "Plant ID",
                    value=str(plant.get("plant_id") or plant_id or "planta_1"),
                    key="platform_onboarding_plant_id",
                )
                plant_name = st.text_input(
                    "Nome da planta",
                    value=str(plant.get("plant_name") or ""),
                    key="platform_onboarding_plant_name",
                )
            with right:
                city = st.text_input(
                    "Cidade",
                    value=str(plant.get("city") or ""),
                    key="platform_onboarding_city",
                )
                plant_status = st.selectbox(
                    "Status da planta",
                    PLANT_STATUS,
                    index=_index(PLANT_STATUS, plant.get("status") or "Piloto", 1),
                    key="platform_onboarding_plant_status",
                )
            if st.form_submit_button("Salvar planta", type="primary"):
                try:
                    repo.upsert_plant(
                        {
                            "tenant_id": plant_tenant,
                            "plant_id": plant_input,
                            "plant_name": plant_name,
                            "city": city,
                            "status": plant_status,
                        }
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("Planta salva no onboarding.")
                    st.rerun()

    with st.expander("3. Contrato e módulos", expanded=bool(plant) and not bool(contract)):
        plant_options = [f"{item['tenant_id']}#{item['plant_id']}" for item in data.get("plants") or []]
        selected_contract_plant = f"{tenant_id}#{plant_id}" if tenant_id and plant_id else ""
        if selected_contract_plant and selected_contract_plant not in plant_options:
            plant_options.append(selected_contract_plant)
        default_services = list(contract.get("services") or [])
        with st.form("platform_onboarding_contract_form"):
            selected_plant = st.selectbox(
                "Planta contratada",
                plant_options or [selected_contract_plant or "cliente_novo#planta_1"],
                index=_index(
                    plant_options or [selected_contract_plant or "cliente_novo#planta_1"],
                    selected_contract_plant,
                    0,
                ),
                key="platform_onboarding_contract_plant",
            )
            selected_services = st.multiselect(
                "Módulos contratados",
                options=list(service_labels.keys()),
                default=default_services or ["condition"],
                format_func=lambda value: service_labels.get(value, value),
                key="platform_onboarding_contract_services",
            )
            contract_status = st.selectbox(
                "Status do contrato",
                CONTRACT_STATUS,
                index=_index(CONTRACT_STATUS, contract.get("status") or "Piloto", 1),
                key="platform_onboarding_contract_status",
            )
            intelligence_label = "habilitada" if has_operational_intelligence(selected_services) else "parcial"
            st.caption(f"Inteligência Operacional: {intelligence_label}")
            if st.form_submit_button("Salvar contrato", type="primary"):
                contract_tenant, _, contract_plant = selected_plant.partition("#")
                try:
                    repo.upsert_contract(
                        {
                            "tenant_id": contract_tenant,
                            "plant_id": contract_plant,
                            "services": selected_services,
                            "status": contract_status,
                        }
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("Contrato salvo no onboarding.")
                    st.rerun()


def _render_real_asset_sensor_gateway_form(
    config_repo: ConfigRepository,
    operational_config: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
    contract_services: list[str] | None = None,
) -> None:
    st.markdown("#### Ativo, sensor e gateway")
    st.caption(
        "Cadastro multifabricante parametrizado: comece com o mínimo técnico e refine fabricante, modelo e limites depois."
    )

    inventory = _asset_inventory_rows({}, operational_config, tenant_id=tenant_id, plant_id=plant_id)
    if inventory:
        _render_inventory_action_table(inventory)

    gateway_rows = _gateway_inventory_rows(operational_config, tenant_id=tenant_id, plant_id=plant_id)
    sensor_rows = _sensor_inventory_rows(operational_config, tenant_id=tenant_id, plant_id=plant_id)
    with st.expander("Gateways e ativos vinculados", expanded=bool(gateway_rows)):
        _render_table(gateway_rows, "Nenhum gateway cadastrado para esta planta.")
    with st.expander("Sensores cadastrados por ativo", expanded=bool(sensor_rows)):
        _render_table(sensor_rows, "Nenhum sensor técnico cadastrado para esta planta.")

    service_labels = _service_options()
    contracted_labels = [
        service_labels.get(service, service)
        for service in (contract_services or [])
    ]
    st.caption(
        "Cobertura contratada da planta: "
        + (", ".join(contracted_labels) if contracted_labels else "não definida")
        + ". O contrato governa os módulos disponíveis para todos os ativos da planta."
    )

    with st.form("platform_real_asset_sensor_gateway_form"):
        st.markdown("**Gateway / fonte de dados**")
        g1, g2 = st.columns(2)
        with g1:
            source_id = st.text_input("Identificador lógico do gateway", "gateway_indoor_01")
            source_name = st.text_input("Nome do gateway", "Gateway Indoor 01")
            source_type = st.text_input("Tipo do gateway", "Gateway Edge")
            source_manufacturer = st.text_input("Fabricante do gateway", "")
            source_model = st.text_input("Modelo do gateway", "")
        with g2:
            protocol = st.selectbox("Protocolo", GATEWAY_PROTOCOL_OPTIONS)
            endpoint = st.text_input("Endpoint/fonte", "https://sentinelaindustrial.com.br/condition/ingest")
            credential_ref = st.text_input("Referência do token/credencial", "env:CONDITION_INGEST_TOKEN")
            source_serial_number = st.text_input("Número de série do gateway", "")
            source_status = st.selectbox("Status do gateway", GATEWAY_STATUS_OPTIONS)

        st.markdown("**Ativo real**")
        a1, a2 = st.columns(2)
        with a1:
            asset_id = st.text_input("Asset ID", "motor_real_01")
            asset_name = st.text_input("Nome/tag do ativo", "Motor Real 01")
            asset_type = st.selectbox("Tipo de ativo", ASSET_TYPE_OPTIONS)
            area = st.text_input("Área", "Teste indoor")
        with a2:
            criticality = st.selectbox("Criticidade", CRITICALITY_OPTIONS, index=2)
            manufacturer = st.text_input("Fabricante", "")
            model = st.text_input("Modelo", "")
            serial_number = st.text_input("Número de série", "")
            asset_status = st.selectbox("Status do ativo", ["Ativo", "Aguardando comissionamento", "Inativo"])

        st.markdown("**Sensor e ponto de medição**")
        metric_options = _metric_options_for_asset_type(asset_type)
        s1, s2, s3 = st.columns(3)
        with s1:
            sensor_id = st.text_input("Identificador do sensor", "sensor_real_01")
            sensor_kind = st.selectbox("Tipo de sensor", SENSOR_KIND_OPTIONS)
            sensor_manufacturer = st.text_input("Fabricante do sensor", "")
            sensor_model = st.text_input("Modelo do sensor", "")
        with s2:
            sensor_serial_number = st.text_input("Número de série do sensor", "")
            installation_point = st.text_input("Ponto de instalação", "Mancal lado acoplado")
            measured_quantity = st.text_input("Grandeza medida", "Vibração RMS")
            metric = st.selectbox("Métrica interna esperada", metric_options)
        with s3:
            external_tag = st.text_input("Tag externa / canal", f"{asset_id}.{metric}")
            unit = st.text_input("Unidade", UNIT_BY_METRIC.get(metric, ""))
            expected_min = st.number_input("Faixa esperada mínima", value=0.0)
            expected_max = st.number_input("Faixa esperada máxima", value=10.0)
            sensor_status = st.selectbox(
                "Status do sensor",
                ["Aguardando comissionamento", "Ativo", "Falha", "Inativo"],
            )

        st.markdown("**Limites e regra inicial**")
        direction = st.selectbox("Regra", ["Maior é pior", "Menor é pior", "Faixa ideal"])
        normal_min = normal_max = attention_min = attention_max = 0.0
        alert_min = alert_max = critical_min = critical_max = 0.0
        if direction == "Faixa ideal":
            r1, r2 = st.columns(2)
            with r1:
                normal_min = st.number_input("Normal mínimo", value=0.0)
                attention_min = st.number_input("Atenção inferior", value=0.0)
                alert_min = st.number_input("Alerta inferior", value=0.0)
                critical_min = st.number_input("Crítico inferior", value=0.0)
            with r2:
                normal_max = st.number_input("Normal máximo", value=10.0)
                attention_max = st.number_input("Atenção superior", value=11.0)
                alert_max = st.number_input("Alerta superior", value=12.0)
                critical_max = st.number_input("Crítico superior", value=13.0)
            normal_limit = attention_limit = alert_limit = critical_limit = 0.0
        else:
            r1, r2 = st.columns(2)
            with r1:
                normal_limit = st.number_input("Limite normal", value=2.8)
                attention_limit = st.number_input("Limite atenção", value=2.8)
            with r2:
                alert_limit = st.number_input("Limite alerta", value=4.5)
                critical_limit = st.number_input("Limite crítico", value=7.1)

        persistence_min = st.number_input("Persistência mínima (min)", min_value=1, value=3, step=1)
        recommended_action = st.text_area(
            "Ação recomendada inicial",
            "Inspecionar instalação, sensor, acoplamento, rolamentos e condição operacional.",
        )
        technical_note = st.text_area(
            "Observação técnica",
            "Limites iniciais sujeitos a ajuste após baseline da máquina real.",
        )

        if st.form_submit_button("Salvar ativo, sensor e gateway", type="primary"):
            config = config_repo.load()
            config["data_sources"] = _replace_by_keys(
                list(config.get("data_sources") or []),
                {
                    "tenant_id": tenant_id,
                    "plant_id": plant_id,
                    "source_id": source_id.strip(),
                    "source_name": source_name.strip(),
                    "source_type": source_type.strip(),
                    "manufacturer": source_manufacturer.strip(),
                    "model": source_model.strip(),
                    "serial_number": source_serial_number.strip(),
                    "protocol": protocol,
                    "endpoint": endpoint.strip(),
                    "polling_interval_sec": 5,
                    "history_interval_sec": 60,
                    "status": source_status,
                    "credential_ref": credential_ref.strip(),
                    "description": "Fonte cadastrada pelo onboarding de teste indoor.",
                },
                ["source_id"],
            )
            config["assets"] = _replace_by_keys(
                list(config.get("assets") or []),
                {
                    "tenant_id": tenant_id,
                    "plant_id": plant_id,
                    "asset_id": asset_id.strip(),
                    "asset_name": asset_name.strip(),
                    "asset_type": asset_type,
                    "area": area.strip(),
                    "criticality": criticality,
                    "manufacturer": manufacturer.strip(),
                    "model": model.strip(),
                    "serial_number": serial_number.strip(),
                    "source_id": source_id.strip(),
                    "baseline_status": "Aguardando baseline real do teste indoor.",
                    "status": asset_status,
                },
                ["asset_id"],
            )
            config["sensors"] = _replace_by_keys(
                list(config.get("sensors") or []),
                {
                    "tenant_id": tenant_id,
                    "plant_id": plant_id,
                    "sensor_id": sensor_id.strip(),
                    "asset_id": asset_id.strip(),
                    "source_id": source_id.strip(),
                    "sensor_kind": sensor_kind,
                    "manufacturer": sensor_manufacturer.strip(),
                    "model": sensor_model.strip(),
                    "serial_number": sensor_serial_number.strip(),
                    "installation_point": installation_point.strip(),
                    "measured_quantity": measured_quantity.strip(),
                    "metric": metric,
                    "unit": unit.strip(),
                    "expected_min": float(expected_min),
                    "expected_max": float(expected_max),
                    "external_tag": external_tag.strip(),
                    "status": sensor_status,
                    "commissioning_mode": "indoor_assisted",
                },
                ["sensor_id"],
            )
            config["signal_map"] = _replace_by_keys(
                list(config.get("signal_map") or []),
                {
                    "asset_id": asset_id.strip(),
                    "source_id": source_id.strip(),
                    "sensor_id": sensor_id.strip(),
                    "metric": metric,
                    "external_tag": external_tag.strip(),
                    "unit": unit.strip(),
                    "expected_min": float(expected_min),
                    "expected_max": float(expected_max),
                    "scale": 1.0,
                    "offset": 0.0,
                    "enabled": True,
                    "sensor_kind": sensor_kind,
                    "commissioning_mode": "indoor_assisted",
                },
                ["asset_id", "source_id", "metric", "sensor_id"],
            )
            config["parameters_alerts"] = _replace_by_keys(
                list(config.get("parameters_alerts") or []),
                _technical_parameter_rule_for_metric(
                    asset_id=asset_id.strip(),
                    metric=metric,
                    direction=direction,
                    normal_limit=float(normal_limit),
                    attention_limit=float(attention_limit),
                    alert_limit=float(alert_limit),
                    critical_limit=float(critical_limit),
                    persistence_min=int(persistence_min),
                    recommended_action=recommended_action.strip(),
                    unit=unit.strip(),
                    technical_note=technical_note.strip(),
                    normal_min=float(normal_min),
                    normal_max=float(normal_max),
                    attention_min=float(attention_min),
                    attention_max=float(attention_max),
                    alert_min=float(alert_min),
                    alert_max=float(alert_max),
                    critical_min=float(critical_min),
                    critical_max=float(critical_max),
                ),
                ["asset_id", "metric"],
            )
            config_repo.save(config)
            st.success("Ativo, sensor e gateway salvos para o teste indoor.")
            st.rerun()


def _render_assisted_production_checklist(
    repo: PlatformAdminRepository,
    run: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
) -> None:
    st.markdown("#### Checklist de produção assistida indoor")
    st.caption(
        "Portão operacional para teste real com máquina, sensores, gateway e ingestão HTTPS acompanhada pela Sentinela."
    )

    summary = _assisted_production_summary(run)
    c1, c2, c3 = st.columns(3)
    c1.metric("Readiness indoor", f"{summary['percent']}%")
    c2.metric("Itens validados", f"{summary['done']}/{summary['total']}")
    c3.metric("Pendências", str(summary["total"] - summary["done"]))
    st.progress(int(summary["percent"]))

    rows = [
        {key: value for key, value in row.items() if key not in {"check_id", "done"}}
        for row in _assisted_production_rows(run)
    ]
    _render_table(rows, "Nenhum item de produção assistida configurado.")

    checks = dict(run.get("assisted_checks") or {})
    context = dict(run.get("assisted_context") or {})
    with st.form("platform_assisted_production_form"):
        left, right = st.columns(2)
        with left:
            machine_id = st.text_input(
                "Máquina real / tag do ativo",
                value=str(context.get("machine_id") or ""),
                key="platform_assisted_machine_id",
            )
            gateway_id = st.text_input(
                "Gateway / fonte de dados",
                value=str(context.get("gateway_id") or ""),
                key="platform_assisted_gateway_id",
            )
            responsible = st.text_input(
                "Responsável técnico pelo teste",
                value=str(context.get("responsible") or ""),
                key="platform_assisted_responsible",
            )
        with right:
            endpoint_url = st.text_input(
                "Endpoint HTTPS usado",
                value=str(context.get("endpoint_url") or "https://sentinelaindustrial.com.br/condition/ingest"),
                key="platform_assisted_endpoint_url",
            )
            stop_criteria = st.text_area(
                "Critério de parada / fallback",
                value=str(context.get("stop_criteria") or ""),
                key="platform_assisted_stop_criteria",
            )

        st.markdown("**Validações obrigatórias**")
        updated_checks: dict[str, bool] = {}
        for item in ASSISTED_PRODUCTION_CHECKS:
            check_id = str(item["id"])
            updated_checks[check_id] = st.checkbox(
                item["item"],
                value=bool(checks.get(check_id)),
                help=item["criterion"],
                key=f"platform_assisted_check_{check_id}",
            )

        if st.form_submit_button("Salvar checklist indoor", type="primary"):
            repo.upsert_onboarding_run(
                {
                    "tenant_id": tenant_id,
                    "plant_id": plant_id,
                    "status": run.get("status") or "Em andamento",
                    "manual_steps": dict(run.get("manual_steps") or {}),
                    "assisted_checks": updated_checks,
                    "assisted_context": {
                        "machine_id": machine_id,
                        "gateway_id": gateway_id,
                        "responsible": responsible,
                        "endpoint_url": endpoint_url,
                        "stop_criteria": stop_criteria,
                    },
                    "notes": str(run.get("notes") or ""),
                }
            )
            st.success("Checklist de produção assistida salvo.")
            st.rerun()


def _render_onboarding_tab(
    repo: PlatformAdminRepository,
    data: dict[str, Any],
    operational_config: dict[str, Any],
    config_repo: ConfigRepository,
) -> None:
    st.subheader("Onboarding guiado do cliente")
    st.caption(
        "Sequência operacional para preparar cliente, planta, usuários, ativos e aceite antes da liberação de uso."
    )

    plant_options = [f"{plant['tenant_id']}#{plant['plant_id']}" for plant in data.get("plants") or []]
    tenant_options = [str(tenant.get("tenant_id")) for tenant in data.get("tenants") or [] if tenant.get("tenant_id")]
    default_focus = f"{tenant_options[0]}#planta_1" if tenant_options else "cliente_novo#planta_1"
    selected_plant = st.selectbox(
        "Cliente e planta",
        plant_options or [default_focus],
        key="platform_onboarding_plant",
    )
    tenant_id, _, plant_id = selected_plant.partition("#")
    run = repo.onboarding_run_for(tenant_id, plant_id)
    rows = _onboarding_step_rows(data, operational_config, run, tenant_id=tenant_id, plant_id=plant_id)
    summary = _onboarding_summary(rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conclusão", f"{summary['percent']}%")
    c2.metric("Etapas OK", f"{summary['done']}/{summary['total']}")
    c3.metric("Status", str(run.get("status") or summary["status"]))
    c4.metric("Pendências", str(summary["total"] - summary["done"]))
    st.progress(int(summary["percent"]))

    checklist_rows = [
        {key: value for key, value in row.items() if key not in {"step_id", "done"}}
        for row in rows
    ]
    _render_table(checklist_rows, "Nenhuma etapa de onboarding configurada.")

    _render_onboarding_registration_forms(repo, data, tenant_id=tenant_id, plant_id=plant_id)
    contract = _contract_for(data, tenant_id, plant_id) or {}
    _render_real_asset_sensor_gateway_form(
        config_repo,
        operational_config,
        tenant_id=tenant_id,
        plant_id=plant_id,
        contract_services=list(contract.get("services") or []),
    )
    _render_assisted_production_checklist(repo, run, tenant_id=tenant_id, plant_id=plant_id)

    st.markdown("#### Registro de comissionamento")
    manual_steps = dict(run.get("manual_steps") or {})
    status_options = ["Em andamento", "Aguardando cliente", "Pronto para liberação", "Liberado"]
    with st.form("platform_onboarding_manual_form"):
        commissioning = st.checkbox(
            "Ingestão, baseline e alertas validados",
            value=bool(manual_steps.get("commissioning")),
        )
        release = st.checkbox(
            "Cliente liberado para operação assistida/produção",
            value=bool(manual_steps.get("release")),
        )
        status = st.selectbox(
            "Status do onboarding",
            status_options,
            index=_index(status_options, run.get("status"), 0),
        )
        notes = st.text_area("Notas internas", str(run.get("notes") or ""))

        if st.form_submit_button("Salvar onboarding", type="primary"):
            repo.upsert_onboarding_run(
                {
                    "tenant_id": tenant_id,
                    "plant_id": plant_id,
                    "status": status,
                    "manual_steps": {
                        "commissioning": commissioning,
                        "release": release,
                    },
                    "assisted_checks": dict(run.get("assisted_checks") or {}),
                    "assisted_context": dict(run.get("assisted_context") or {}),
                    "notes": notes,
                }
            )
            st.success("Onboarding salvo.")
            st.rerun()

    st.markdown("#### Próxima persistência para produção")
    _render_table(
        [
            {
                "Tabela futura": "platform_tenants",
                "Conteúdo": "Cliente, ambiente, status, plano contratado e metadados comerciais.",
                "Origem atual": "platform_admin_store.json / DynamoDB futuro",
            },
            {
                "Tabela futura": "platform_plants",
                "Conteúdo": "Plantas, áreas, contexto operacional e vínculo com tenant.",
                "Origem atual": "platform_admin_store.json / config operacional",
            },
            {
                "Tabela futura": "platform_assets",
                "Conteúdo": "Ativos, fontes, tags, sinais, parâmetros e criticidade por planta.",
                "Origem atual": "config operacional versionada",
            },
            {
                "Tabela futura": "platform_onboarding_runs",
                "Conteúdo": "Checklist, evidências, aceite técnico, liberação e auditoria.",
                "Origem atual": "onboarding_runs no store versionado",
            },
        ],
        "Nenhum modelo de persistência definido.",
    )


def _render_support_tab() -> None:
    st.subheader("Suporte, demonstrações e acesso assistido")
    st.caption(
        "Ferramentas exclusivas do Admin Sentinela. O acesso a contexto de cliente deve ter tenant, planta, motivo e auditoria."
    )
    st.markdown("#### Demonstrações para cliente")
    demo_cols = st.columns(3)
    with demo_cols[0]:
        st.markdown("**Monitoramento de Equipamentos**")
        st.caption("Cenários de condição, alerta por ativo e painel de monitoramento.")
        if st.button(
            "Abrir bancada de equipamentos",
            type="primary",
            use_container_width=True,
            key="admin_open_condition_bench",
        ):
            _navigate_to("Bancada Virtual — Equipamentos")
    with demo_cols[1]:
        st.markdown("**Sistema de Lubrificação**")
        st.caption("Cenários por saída de graxa, ciclo final, alertas e painel do sistema.")
        if st.button("Abrir bancada de lubrificação", use_container_width=True, key="admin_open_lubrication_bench"):
            _navigate_to("Bancada Virtual — Lubrificação")
    with demo_cols[2]:
        st.markdown("**Resultado operacional**")
        st.caption("Ir direto aos painéis depois de aplicar um cenário.")
        if st.button("Ver monitoramento", use_container_width=True, key="admin_open_condition_monitoring"):
            _navigate_to("Monitoramento de Equipamentos")
        if st.button("Ver sistema de lubrificação", use_container_width=True, key="admin_open_lubrication_dashboard"):
            _navigate_to("Sistema de Lubrificação")

    st.divider()
    _render_table(SUPPORT_SCOPES, "Nenhum escopo de suporte configurado.")
    st.warning(
        "Admin Sentinela não deve atuar como operador invisível do cliente. Qualquer suporte remoto precisa de contexto explícito e trilha de auditoria."
    )


def _render_governance_tab() -> None:
    st.subheader("Governança da plataforma")
    rows = [{"Domínio": item} for item in ADMIN_DOMAINS]
    _render_table(rows, "Nenhum domínio de governança configurado.")
    st.subheader("Funções exclusivas do Admin Sentinela")
    _render_table(
        [
            {"Função": "Criar tenants, plantas e contratos por módulo."},
            {"Função": "Habilitar ou suspender serviços por planta."},
            {"Função": "Governar conectores, protocolos, templates e credenciais."},
            {"Função": "Acompanhar suporte, demonstrações, filas de notificação e auditoria."},
            {"Função": "Preparar o onboarding antes de liberar operação ao cliente."},
        ],
        "Nenhuma função exclusiva configurada.",
    )
    st.info(
        "As telas de arquitetura modular e teste ponta a ponta são ferramentas internas de evolução do MVP. "
        "Elas ficam fora do menu padrão do Admin Sentinela."
    )


def _render_tenants_tab(repo: PlatformAdminRepository, data: dict[str, Any]) -> None:
    st.subheader("Clientes")
    _render_table(data["tenants"], "Nenhum cliente cadastrado.")

    with st.form("platform_admin_tenant_form"):
        left, right = st.columns(2)
        with left:
            tenant_id = st.text_input("Tenant ID", "cliente_demo")
            company_name = st.text_input("Nome da empresa", "Cliente Demonstração")
        with right:
            status = st.selectbox("Status", TENANT_STATUS)
            environment = st.selectbox("Ambiente", ENVIRONMENTS, index=1)

        if st.form_submit_button("Salvar cliente", type="primary"):
            try:
                repo.upsert_tenant(
                    {
                        "tenant_id": tenant_id,
                        "company_name": company_name,
                        "status": status,
                        "environment": environment,
                    }
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Cliente salvo.")
                st.rerun()


def _render_plants_tab(
    repo: PlatformAdminRepository,
    data: dict[str, Any],
    operational_config: dict[str, Any],
) -> None:
    st.subheader("Plantas")
    _render_table(data["plants"], "Nenhuma planta cadastrada.")
    tenant_ids = [tenant["tenant_id"] for tenant in data["tenants"]]
    plant_options = [f"{plant['tenant_id']}#{plant['plant_id']}" for plant in data["plants"]]

    if plant_options:
        st.subheader("Inventário operacional da planta")
        selected_inventory = st.selectbox("Planta para suporte", plant_options, key="platform_admin_inventory_plant")
        tenant_id_inventory, _, plant_id_inventory = selected_inventory.partition("#")
        inventory_rows = _asset_inventory_rows(
            data,
            operational_config,
            tenant_id=tenant_id_inventory,
            plant_id=plant_id_inventory,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ativos", str(len(inventory_rows)))
        c2.metric("Fontes", str(len(_data_source_rows(operational_config))))
        c3.metric("Sinais", str(len(operational_config.get("signal_map") or operational_config.get("asset_signal_map") or [])))
        c4.metric("Parâmetros", str(len(operational_config.get("parameters_alerts") or [])))

        st.caption(
            "Visão administrativa para suporte e configuração remota. Não exibe payload bruto, histórico sensível ou dados de produção fora do contexto selecionado."
        )
        _render_inventory_action_table(inventory_rows)
        if inventory_rows:
            selected_asset = st.selectbox(
                "Ativo para suporte remoto",
                inventory_rows,
                format_func=lambda row: f"{row['Ativo']} - {row['Nome']}",
                key="platform_admin_support_asset",
            )
            action_cols = st.columns(4)
            with action_cols[0]:
                if st.button(
                    "Abrir monitoramento",
                    type="primary",
                    use_container_width=True,
                    key="platform_admin_asset_monitoring",
                ):
                    _navigate_to("Monitoramento de Equipamentos", asset_id=str(selected_asset["Ativo"]))
            with action_cols[1]:
                if st.button("Abrir detalhe", use_container_width=True, key="platform_admin_asset_detail"):
                    _navigate_to("Detalhe do Ativo", asset_id=str(selected_asset["Ativo"]))
            with action_cols[2]:
                if st.button("Ver alertas", use_container_width=True, key="platform_admin_asset_alerts"):
                    _navigate_to("Alertas e Eventos", asset_id=str(selected_asset["Ativo"]))
            with action_cols[3]:
                if st.button("Configurações", use_container_width=True, key="platform_admin_asset_config"):
                    _navigate_to("Configurações", asset_id=str(selected_asset["Ativo"]))

        with st.expander("Fontes de dados e conectores da planta"):
            _render_table(_data_source_rows(operational_config), "Nenhuma fonte de dados cadastrada.")

    with st.form("platform_admin_plant_form"):
        left, right = st.columns(2)
        with left:
            tenant_id = st.selectbox("Cliente", tenant_ids) if tenant_ids else st.text_input("Tenant ID")
            plant_id = st.text_input("Plant ID", "lab_virtual")
            plant_name = st.text_input("Nome da planta", "Bancada Virtual")
        with right:
            city = st.text_input("Cidade", "Betim")
            status = st.selectbox("Status", PLANT_STATUS)

        if st.form_submit_button("Salvar planta", type="primary"):
            try:
                repo.upsert_plant(
                    {
                        "tenant_id": tenant_id,
                        "plant_id": plant_id,
                        "plant_name": plant_name,
                        "city": city,
                        "status": status,
                    }
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Planta salva.")
                st.rerun()


def _render_contracts_tab(repo: PlatformAdminRepository, data: dict[str, Any]) -> None:
    st.subheader("Serviços contratados por planta")
    _render_table(_contract_rows(data), "Nenhum contrato cadastrado.")

    plant_options = [f"{plant['tenant_id']}#{plant['plant_id']}" for plant in data["plants"]]
    service_labels = _service_options()

    with st.form("platform_admin_contract_form"):
        selected_plant = st.selectbox("Planta", plant_options) if plant_options else st.text_input("tenant_id#plant_id")
        selected_services = st.multiselect(
            "Serviços contratados",
            list(service_labels.keys()),
            default=list(service_labels.keys()),
            format_func=lambda key: service_labels.get(key, key),
        )
        status = st.selectbox("Status", CONTRACT_STATUS)
        intelligence_label = "habilitada" if has_operational_intelligence(selected_services) else "parcial"
        st.caption(f"Inteligência Operacional: {intelligence_label}")

        if st.form_submit_button("Salvar contrato", type="primary"):
            tenant_id, _, plant_id = selected_plant.partition("#")
            try:
                repo.upsert_contract(
                    {
                        "tenant_id": tenant_id,
                        "plant_id": plant_id,
                        "services": selected_services,
                        "status": status,
                    }
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Contrato salvo.")
                st.rerun()
