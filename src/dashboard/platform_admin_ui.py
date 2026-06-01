from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
    from dashboard.platform_admin_repository import PlatformAdminRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.module_registry import ADMIN_DOMAINS, SERVICE_BLUEPRINTS, has_operational_intelligence
    from src.dashboard.platform_admin_repository import PlatformAdminRepository


PAGE_NAME = "Admin da Plataforma"

TENANT_STATUS = ["Ativo", "Piloto", "Suspenso", "Inativo"]
PLANT_STATUS = ["Ativa", "Piloto", "Inativa"]
CONTRACT_STATUS = ["Ativo", "Piloto", "Suspenso", "Inativo"]
ENVIRONMENTS = ["Demonstração", "Piloto", "Produção"]


def _index(options: list[str], value: Any, default: int = 0) -> int:
    try:
        return options.index(str(value))
    except ValueError:
        return default


def _service_options() -> dict[str, str]:
    return {str(service["module_key"]): str(service["service"]) for service in SERVICE_BLUEPRINTS}


def _render_table(items: list[dict[str, Any]], empty_message: str) -> None:
    if not items:
        st.info(empty_message)
        return
    st.dataframe(items, width="stretch", hide_index=True)


def render_platform_admin_page(path: str | None = None) -> None:
    repo = PlatformAdminRepository(path)
    data = repo.load()

    st.header("Admin da Plataforma")
    st.caption("Operação multi-tenant da Sentinela: clientes, plantas, contratos, serviços e governança da plataforma.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes", str(len(data["tenants"])))
    c2.metric("Plantas", str(len(data["plants"])))
    c3.metric("Contratos", str(len(data["service_contracts"])))
    c4.metric(
        "Inteligência",
        str(sum(1 for contract in data["service_contracts"] if contract.get("operational_intelligence"))),
    )

    tabs = st.tabs(["Visão Geral", "Clientes", "Plantas", "Serviços Contratados", "Governança"])
    with tabs[0]:
        _render_overview_tab(data)
    with tabs[1]:
        _render_tenants_tab(repo, data)
    with tabs[2]:
        _render_plants_tab(repo, data)
    with tabs[3]:
        _render_contracts_tab(repo, data)
    with tabs[4]:
        _render_governance_tab()


def _render_overview_tab(data: dict[str, Any]) -> None:
    st.subheader("Resumo da plataforma")
    active_tenants = sum(1 for tenant in data["tenants"] if str(tenant.get("status")) == "Ativo")
    active_contracts = sum(1 for contract in data["service_contracts"] if str(contract.get("status")) == "Ativo")
    dual_service_contracts = sum(1 for contract in data["service_contracts"] if contract.get("operational_intelligence"))

    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes ativos", str(active_tenants))
    c2.metric("Contratos ativos", str(active_contracts))
    c3.metric("Com inteligência operacional", str(dual_service_contracts))

    service_labels = _service_options()
    rows = []
    for contract in data["service_contracts"]:
        service_names = [service_labels.get(service, service) for service in contract.get("services") or []]
        rows.append(
            {
                "Cliente": contract.get("tenant_id"),
                "Planta": contract.get("plant_id"),
                "Serviços": ", ".join(service_names) or "-",
                "Inteligência Operacional": "Sim" if contract.get("operational_intelligence") else "Não",
                "Status": contract.get("status"),
            }
        )
    _render_table(rows, "Nenhum contrato configurado para a plataforma.")


def _render_governance_tab() -> None:
    st.subheader("Governança da plataforma")
    rows = [{"Domínio": item} for item in ADMIN_DOMAINS]
    _render_table(rows, "Nenhum domínio de governança configurado.")
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


def _render_plants_tab(repo: PlatformAdminRepository, data: dict[str, Any]) -> None:
    st.subheader("Plantas")
    _render_table(data["plants"], "Nenhuma planta cadastrada.")
    tenant_ids = [tenant["tenant_id"] for tenant in data["tenants"]]

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
    rows = [
        {
            **contract,
            "services": ", ".join(contract.get("services") or []),
            "operational_intelligence": "Sim" if contract.get("operational_intelligence") else "Não",
        }
        for contract in data["service_contracts"]
    ]
    _render_table(rows, "Nenhum contrato cadastrado.")

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
