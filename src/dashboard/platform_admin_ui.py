from __future__ import annotations

import os
from typing import Any

import streamlit as st

try:
    from dashboard.config_repository import ConfigRepository
    from dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
    from dashboard.platform_admin_repository import PlatformAdminRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.config_repository import ConfigRepository
    from src.dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
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


def _render_table(items: list[dict[str, Any]], empty_message: str) -> None:
    if not items:
        st.info(empty_message)
        return
    st.dataframe(items, width="stretch", hide_index=True)


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


def render_platform_admin_page(path: str | None = None, config_path: str | None = None) -> None:
    repo = PlatformAdminRepository(path)
    data = repo.load()
    operational_config = ConfigRepository(config_path or os.getenv("DASHBOARD_CONFIG_STORE") or None).load()
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

    tabs = st.tabs(
        [
            "Painel",
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
        _render_tenants_tab(repo, data)
    with tabs[2]:
        _render_plants_tab(repo, data, operational_config)
    with tabs[3]:
        _render_contracts_tab(repo, data)
    with tabs[4]:
        _render_support_tab()
    with tabs[5]:
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


def _render_support_tab() -> None:
    st.subheader("Suporte, demonstrações e acesso assistido")
    st.caption(
        "Ferramentas exclusivas do Admin Sentinela. O acesso a contexto de cliente deve ter tenant, planta, motivo e auditoria."
    )
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
        _render_table(inventory_rows, "Nenhum ativo cadastrado para esta planta.")

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
