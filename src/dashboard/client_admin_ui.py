from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from dashboard.module_registry import SERVICE_BLUEPRINTS, has_operational_intelligence
    from dashboard.platform_admin_repository import PlatformAdminRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.module_registry import SERVICE_BLUEPRINTS, has_operational_intelligence
    from src.dashboard.platform_admin_repository import PlatformAdminRepository


PAGE_NAME = "Admin do Cliente"

USER_ROLES = ["operador", "tecnico", "cliente_admin"]
USER_STATUS = ["Ativo", "Convidado", "Suspenso", "Inativo"]
PLANT_STATUS = ["Ativa", "Piloto", "Inativa"]
CONTRACT_STATUS = ["Ativo", "Piloto", "Suspenso", "Inativo"]


def _service_options() -> dict[str, str]:
    return {str(service["module_key"]): str(service["service"]) for service in SERVICE_BLUEPRINTS}


def _render_table(items: list[dict[str, Any]], empty_message: str) -> None:
    if not items:
        st.info(empty_message)
        return
    st.dataframe(items, width="stretch", hide_index=True)


def render_client_admin_page(tenant_id: str, path: str | None = None) -> None:
    repo = PlatformAdminRepository(path)
    data = repo.data_for_tenant(tenant_id)
    company_name = data["tenants"][0].get("company_name") if data["tenants"] else tenant_id

    st.header("Admin do Cliente")
    st.caption("Gestão local de plantas, usuários e serviços do próprio tenant.")
    st.subheader(str(company_name or tenant_id))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Plantas", str(len(data["plants"])))
    c2.metric("Usuários", str(len(data["users"])))
    c3.metric("Contratos", str(len(data["service_contracts"])))
    c4.metric(
        "Inteligência",
        str(sum(1 for contract in data["service_contracts"] if contract.get("operational_intelligence"))),
    )

    tabs = st.tabs(["Plantas", "Usuários", "Serviços"])
    with tabs[0]:
        _render_plants_tab(repo, tenant_id, data)
    with tabs[1]:
        _render_users_tab(repo, tenant_id, data)
    with tabs[2]:
        _render_contracts_tab(repo, tenant_id, data)


def _render_plants_tab(repo: PlatformAdminRepository, tenant_id: str, data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Plantas")
    _render_table(data["plants"], "Nenhuma planta cadastrada para este cliente.")

    with st.form("client_admin_plant_form"):
        left, right = st.columns(2)
        with left:
            plant_id = st.text_input("Plant ID", "planta_1")
            plant_name = st.text_input("Nome da planta", "Planta 1")
        with right:
            city = st.text_input("Cidade", "")
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


def _render_users_tab(repo: PlatformAdminRepository, tenant_id: str, data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Usuários")
    _render_table(data["users"], "Nenhum usuário cadastrado para este cliente.")

    with st.form("client_admin_user_form"):
        left, right = st.columns(2)
        with left:
            email = st.text_input("E-mail", "")
            name = st.text_input("Nome", "")
        with right:
            role = st.selectbox("Perfil", USER_ROLES)
            status = st.selectbox("Status", USER_STATUS)

        if st.form_submit_button("Salvar usuário", type="primary"):
            try:
                repo.upsert_user(
                    {
                        "tenant_id": tenant_id,
                        "email": email,
                        "name": name,
                        "role": role,
                        "status": status,
                    }
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Usuário salvo.")
                st.rerun()


def _render_contracts_tab(repo: PlatformAdminRepository, tenant_id: str, data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Serviços por planta")
    rows = [
        {
            **contract,
            "services": ", ".join(contract.get("services") or []),
            "operational_intelligence": "Sim" if contract.get("operational_intelligence") else "Não",
        }
        for contract in data["service_contracts"]
    ]
    _render_table(rows, "Nenhum contrato cadastrado para este cliente.")

    plant_ids = [plant["plant_id"] for plant in data["plants"]]
    service_labels = _service_options()
    with st.form("client_admin_contract_form"):
        plant_id = st.selectbox("Planta", plant_ids) if plant_ids else st.text_input("Plant ID")
        selected_services = st.multiselect(
            "Serviços contratados",
            list(service_labels.keys()),
            default=list(service_labels.keys()),
            format_func=lambda key: service_labels.get(key, key),
        )
        status = st.selectbox("Status", CONTRACT_STATUS)
        intelligence_label = "habilitada" if has_operational_intelligence(selected_services) else "parcial"
        st.caption(f"Inteligência Operacional: {intelligence_label}")

        if st.form_submit_button("Salvar serviços", type="primary"):
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
                st.success("Serviços salvos.")
                st.rerun()
