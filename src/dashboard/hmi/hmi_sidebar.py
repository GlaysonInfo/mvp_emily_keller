from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


DEFAULT_OPERATOR_PAGES = [
    {"id": "operator_home", "label": "Painel da Planta", "route": "Visão Geral da Planta"},
    {"id": "asset_detail", "label": "Equipamento", "route": "Detalhe do Ativo"},
    {"id": "lubrication", "label": "Lubrificação", "route": "Sistema de Lubrificação"},
    {"id": "alerts", "label": "Alertas", "route": "Alertas e Eventos"},
    {"id": "reports", "label": "Relatórios", "route": "Relatórios"},
    {"id": "help", "label": "Ajuda", "route": "Ajuda do Operador"},
]

DEFAULT_TECH_PAGES = [
    "Visão Geral da Planta",
    "Detalhe do Ativo",
    "Inteligência Operacional",
    "Sistema de Lubrificação",
    "Configuração de Campo — Lubrificação",
    "Alertas e Eventos",
    "Matriz de Escalonamento",
    "Notification Outbox",
    "Relatórios",
    "Configurações",
    "Teste ponta a ponta",
]

OPERATOR_LABEL_BY_ROUTE = {item["route"]: item["label"] for item in DEFAULT_OPERATOR_PAGES}
PENDING_OPERATOR_PAGE_KEY = "hmi_pending_operator_page"
PENDING_TECHNICAL_PAGE_KEY = "hmi_pending_technical_page"


def load_hmi_menu_config(path: str = "config/hmi_menu_config.json") -> dict[str, Any]:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "default_mode": "operator",
        "operator_pages": DEFAULT_OPERATOR_PAGES,
        "technical_pages": DEFAULT_TECH_PAGES,
    }


def set_operator_page_for_route(route: str) -> None:
    label = OPERATOR_LABEL_BY_ROUTE.get(route)
    if label:
        st.session_state[PENDING_OPERATOR_PAGE_KEY] = label
    if route in DEFAULT_TECH_PAGES:
        st.session_state[PENDING_TECHNICAL_PAGE_KEY] = route


def _get(config: dict, *keys: str, default: str = "-") -> str:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return str(current) if current not in [None, ""] else default


def _normal_operator_pages(menu_config: dict[str, Any]) -> list[dict[str, str]]:
    pages = menu_config.get("operator_pages") or DEFAULT_OPERATOR_PAGES
    normalized = []
    for page in pages:
        label = str(page.get("label") or page.get("route") or "-")
        route = str(page.get("route") or label)
        normalized.append({"id": str(page.get("id") or route), "label": label, "route": route})
    return normalized


def render_hmi_sidebar(config: dict | None = None, menu_config_path: str = "config/hmi_menu_config.json") -> dict[str, Any]:
    menu_config = load_hmi_menu_config(menu_config_path)
    config = config or {}

    if "hmi_mode" not in st.session_state:
        st.session_state["hmi_mode"] = menu_config.get("default_mode", "operator")
    if "selected_asset_id" not in st.session_state:
        st.session_state["selected_asset_id"] = "motor_001"

    st.sidebar.markdown("## Ambiente")
    environment = _get(config, "client", "environment_mode", default="Piloto")
    plant_name = _get(config, "plant", "plant_name", default="Bancada Virtual")
    st.sidebar.caption(f"Atual: {environment} - {plant_name}")

    mode_choice = st.sidebar.radio(
        "Modo",
        ["Operador", "Técnico"],
        index=0 if st.session_state["hmi_mode"] == "operator" else 1,
        horizontal=True,
        key="hmi_mode_radio",
    )
    st.session_state["hmi_mode"] = "operator" if mode_choice == "Operador" else "technical"

    st.sidebar.divider()

    if st.session_state["hmi_mode"] == "operator":
        page_map = _normal_operator_pages(menu_config)
        labels = [item["label"] for item in page_map]
        pending_label = st.session_state.pop(PENDING_OPERATOR_PAGE_KEY, None)
        if pending_label in labels:
            st.session_state["hmi_operator_page"] = pending_label
        if st.session_state.get("hmi_operator_page") not in labels:
            st.session_state["hmi_operator_page"] = labels[0]
        selected_label = st.sidebar.radio("Menu do operador", labels, key="hmi_operator_page")
        selected_item = page_map[labels.index(selected_label)]
        page = selected_item["route"]
        visible_label = selected_item["label"]
        auto_refresh = page != "Ajuda do Operador"
        refresh_interval = 5
    else:
        technical_pages = menu_config.get("technical_pages") or DEFAULT_TECH_PAGES
        technical_pages = [str(page) for page in technical_pages if str(page) != "Modo Apresentação"]
        pending_page = st.session_state.pop(PENDING_TECHNICAL_PAGE_KEY, None)
        if pending_page in technical_pages:
            st.session_state["hmi_technical_page"] = pending_page
        if st.session_state.get("hmi_technical_page") not in technical_pages:
            st.session_state["hmi_technical_page"] = technical_pages[0]
        page = st.sidebar.radio("Navegação técnica", technical_pages, key="hmi_technical_page")
        visible_label = page
        auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True, key="auto_refresh")
        refresh_interval = int(
            st.sidebar.number_input("Intervalo em segundos", min_value=2, max_value=60, value=5, step=1)
        )

    st.sidebar.divider()
    st.sidebar.markdown("### Equipamento")
    st.sidebar.markdown(f"Selecionado: `{st.session_state['selected_asset_id']}`")

    col_update, col_change = st.sidebar.columns(2)
    with col_update:
        if st.button("Atualizar", type="primary", use_container_width=True):
            st.rerun()
    with col_change:
        if st.button("Trocar", use_container_width=True):
            set_operator_page_for_route("Visão Geral da Planta")
            st.rerun()

    if st.session_state["hmi_mode"] == "operator":
        st.sidebar.caption("Tela simplificada para operação de campo.")

    return {
        "mode": st.session_state["hmi_mode"],
        "page": page,
        "operator_label": visible_label,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval,
    }
