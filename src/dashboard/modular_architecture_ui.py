from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from dashboard.module_registry import (
        ADMIN_DOMAINS,
        DUAL_SERVICE_REQUIREMENTS,
        INCREMENTAL_DELIVERY_STEPS,
        ROLE_REQUIREMENTS,
        SERVICE_BLUEPRINTS,
        has_operational_intelligence,
        routes_for_context,
    )
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.module_registry import (
        ADMIN_DOMAINS,
        DUAL_SERVICE_REQUIREMENTS,
        INCREMENTAL_DELIVERY_STEPS,
        ROLE_REQUIREMENTS,
        SERVICE_BLUEPRINTS,
        has_operational_intelligence,
        routes_for_context,
    )


PAGE_NAME = "Arquitetura Modular"


def _rows_for_service(service: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "Perfil": "Operador",
            "Visao no modulo": "\n".join(f"- {item}" for item in service["operator_view"]),
        },
        {
            "Perfil": "Tecnico",
            "Visao no modulo": "\n".join(f"- {item}" for item in service["technician_view"]),
        },
        {
            "Perfil": "Admin",
            "Visao no modulo": "\n".join(f"- {item}" for item in service["admin_view"]),
        },
    ]


def _route_rows() -> list[dict[str, str]]:
    services = [str(service["module_key"]) for service in SERVICE_BLUEPRINTS]
    rows = []
    for role, label in [
        ("operador", "Operador"),
        ("tecnico", "Tecnico"),
        ("cliente_admin", "Cliente Admin"),
        ("admin", "Admin do Sistema"),
    ]:
        rows.append(
            {
                "Perfil": label,
                "Servicos ativos": ", ".join(services),
                "Rotas habilitadas": "\n".join(f"- {route}" for route in routes_for_context(role, services)),
            }
        )
    return rows


def render_modular_architecture_page() -> None:
    st.header("Arquitetura Modular")
    st.caption("Estrutura proposta para separar cliente/admin, servicos contratados e perfis de acesso.")

    st.info(
        "Objetivo deste passo: validar a experiencia alvo antes de refatorar menu, RBAC e autenticacao. "
        "A mesma empresa pode contratar Lubrificacao, Monitoramento de Equipamentos ou ambos."
    )

    service_keys = [str(service["module_key"]) for service in SERVICE_BLUEPRINTS]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Servicos", str(len(SERVICE_BLUEPRINTS)))
    c2.metric("Perfis alvo", "4")
    c3.metric("Contrato", "por tenant/planta")
    c4.metric("Inteligencia", "habilitada" if has_operational_intelligence(service_keys) else "parcial")

    st.subheader("Servicos contrataveis")
    service_rows = [
        {
            "Servico": service["service"],
            "Chave": service["module_key"],
            "Escopo contratado": service["contract_scope"],
        }
        for service in SERVICE_BLUEPRINTS
    ]
    st.dataframe(service_rows, width="stretch", hide_index=True)

    for service in SERVICE_BLUEPRINTS:
        with st.expander(service["service"], expanded=True):
            st.caption(service["contract_scope"])
            st.dataframe(_rows_for_service(service), width="stretch", hide_index=True)

    st.subheader("Perfis e limites")
    st.dataframe(ROLE_REQUIREMENTS, width="stretch", hide_index=True)

    st.subheader("Rotas por contrato e perfil")
    st.dataframe(_route_rows(), width="stretch", hide_index=True)

    st.subheader("Area Admin")
    st.write("A area admin precisa nascer em dois niveis: Cliente Admin para o proprio tenant e Admin do Sistema para a plataforma.")
    st.markdown("\n".join(f"- {item}" for item in ADMIN_DOMAINS))

    st.subheader("Cliente com dois servicos")
    st.markdown("\n".join(f"- {item}" for item in DUAL_SERVICE_REQUIREMENTS))

    st.subheader("Entrega incremental proposta")
    st.dataframe(INCREMENTAL_DELIVERY_STEPS, width="stretch", hide_index=True)
