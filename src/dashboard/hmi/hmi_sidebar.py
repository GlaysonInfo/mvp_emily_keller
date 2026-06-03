from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


DEFAULT_OPERATOR_PAGES = [
    {"id": "condition_monitoring", "label": "Equipamentos", "route": "Monitoramento de Equipamentos"},
    {"id": "operator_home", "label": "Painel da Planta", "route": "Visão Geral da Planta"},
    {"id": "asset_detail", "label": "Equipamento", "route": "Detalhe do Ativo"},
    {"id": "lubrication_operation", "label": "Operação Lub.", "route": "Operação de Lubrificação"},
    {"id": "lubrication", "label": "Lubrificação", "route": "Sistema de Lubrificação"},
    {"id": "lubrication_efficiency", "label": "Eficiência", "route": "Eficiência da Lubrificação"},
    {"id": "alerts", "label": "Alertas", "route": "Alertas e Eventos"},
    {"id": "reports", "label": "Relatórios", "route": "Relatórios"},
    {"id": "help", "label": "Ajuda", "route": "Ajuda do Operador"},
]

DEFAULT_TECH_PAGES = [
    "Monitoramento de Equipamentos",
    "Visão Geral da Planta",
    "Detalhe do Ativo",
    "Inteligência Operacional",
    "Operação de Lubrificação",
    "Sistema de Lubrificação",
    "Eficiência da Lubrificação",
    "Eficiência da Lubrificação do Motor",
    "Bancada Virtual — Lubrificação",
    "Configuração de Campo — Lubrificação",
    "Alertas e Eventos",
    "Matriz de Escalonamento",
    "Notification Outbox",
    "Bancada Virtual — Equipamentos",
    "Relatórios",
    "Configurações",
    "Admin do Cliente",
    "Admin da Plataforma",
    "Arquitetura Modular",
    "Teste ponta a ponta",
]

OPERATOR_LABEL_BY_ROUTE = {item["route"]: item["label"] for item in DEFAULT_OPERATOR_PAGES}
OPERATOR_LABEL_BY_ROUTE.update(
    {
        "Monitoramento de Equipamentos": "Equipamentos",
        "Visão Geral da Planta": "Painel da planta",
        "Detalhe do Ativo": "Equipamento",
        "Operação de Lubrificação": "Operação Lub.",
        "Sistema de Lubrificação": "Lubrificação",
        "Eficiência da Lubrificação": "Eficiência",
        "Alertas e Eventos": "Alertas",
        "Relatórios": "Relatórios",
        "Ajuda do Operador": "Ajuda",
    }
)
OPERATOR_GROUPS = [
    (
        "Monitoramento de Equipamentos",
        ["Monitoramento de Equipamentos", "Visão Geral da Planta", "Detalhe do Ativo"],
    ),
    (
        "Sistema de Lubrificação",
        ["Operação de Lubrificação", "Sistema de Lubrificação", "Eficiência da Lubrificação"],
    ),
    ("Alertas e Relatórios", ["Alertas e Eventos", "Relatórios"]),
    ("Suporte", ["Ajuda do Operador"]),
]
TECHNICAL_LABEL_BY_ROUTE = {
    "Monitoramento de Equipamentos": "Ativos monitorados",
    "Visão Geral da Planta": "Visão da planta",
    "Detalhe do Ativo": "Diagnóstico do ativo",
    "Inteligência Operacional": "Correlação e recomendações",
    "Operação de Lubrificação": "Operação de campo",
    "Sistema de Lubrificação": "Painel do sistema",
    "Eficiência da Lubrificação": "Ciclos e eficiência",
    "Eficiência da Lubrificação do Motor": "Eficiência integrada do ativo",
    "Bancada Virtual — Lubrificação": "Bancada virtual",
    "Configuração de Campo — Lubrificação": "Parâmetros de campo",
    "Alertas e Eventos": "Alertas ativos",
    "Matriz de Escalonamento": "Escalonamento de alertas",
    "Notification Outbox": "Fila de notificações",
    "Bancada Virtual — Equipamentos": "Bancada de equipamentos",
    "Relatórios": "Relatórios",
    "Configurações": "Configurações",
    "Admin do Cliente": "Admin do Cliente",
    "Admin da Plataforma": "Admin da Plataforma",
    "Arquitetura Modular": "Arquitetura modular",
    "Teste ponta a ponta": "Teste ponta a ponta",
}
TECHNICAL_GROUPS = [
    (
        "Monitoramento de Equipamentos",
        ["Monitoramento de Equipamentos", "Visão Geral da Planta", "Detalhe do Ativo"],
    ),
    (
        "Sistema de Lubrificação",
        [
            "Operação de Lubrificação",
            "Sistema de Lubrificação",
            "Eficiência da Lubrificação",
            "Configuração de Campo — Lubrificação",
        ],
    ),
    (
        "Inteligência Operacional",
        ["Inteligência Operacional"],
    ),
    (
        "Alertas e Notificações",
        ["Alertas e Eventos", "Matriz de Escalonamento", "Notification Outbox"],
    ),
    ("Relatórios", ["Relatórios"]),
    ("Administração do Cliente", ["Admin do Cliente", "Configurações"]),
    ("Administração da Plataforma", ["Admin da Plataforma", "Configurações"]),
    (
        "Demonstrações e Suporte",
        [
            "Bancada Virtual — Equipamentos",
            "Eficiência da Lubrificação do Motor",
            "Bancada Virtual — Lubrificação",
            "Arquitetura Modular",
            "Teste ponta a ponta",
        ],
    ),
]
PENDING_OPERATOR_PAGE_KEY = "hmi_pending_operator_page"
PENDING_TECHNICAL_PAGE_KEY = "hmi_pending_technical_page"
ADMIN_PAGE_SELECT_KEY = "hmi_admin_page_select"


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


def _filter_operator_pages(pages: list[dict[str, str]], allowed_routes: list[str] | None) -> list[dict[str, str]]:
    if allowed_routes is None:
        return pages
    allowed = set(allowed_routes)
    return [page for page in pages if page["route"] in allowed]


def _filter_technical_pages(pages: list[str], allowed_routes: list[str] | None) -> list[str]:
    if allowed_routes is None:
        return pages
    allowed = set(allowed_routes)
    return [page for page in pages if page in allowed]


def _technical_page_label(route: str) -> str:
    return TECHNICAL_LABEL_BY_ROUTE.get(route, route)


def _operator_navigation_groups(pages: list[dict[str, str]]) -> list[dict[str, Any]]:
    page_by_route = {page["route"]: page for page in pages}
    remaining = set(page_by_route)
    groups: list[dict[str, Any]] = []

    for group_label, routes in OPERATOR_GROUPS:
        items = []
        for route in routes:
            page = page_by_route.get(route)
            if page is None:
                continue
            items.append(
                {
                    "route": page["route"],
                    "label": OPERATOR_LABEL_BY_ROUTE.get(page["route"], page["label"]),
                    "state_label": page["label"],
                }
            )
        if not items:
            continue
        groups.append({"label": group_label, "items": items})
        for item in items:
            remaining.discard(item["route"])

    leftovers = [
        {
            "route": page["route"],
            "label": OPERATOR_LABEL_BY_ROUTE.get(page["route"], page["label"]),
            "state_label": page["label"],
        }
        for page in pages
        if page["route"] in remaining
    ]
    if leftovers:
        groups.append({"label": "Outros", "items": leftovers})
    return groups


def _technical_navigation_groups(pages: list[str], user_role: str | None = None) -> list[dict[str, Any]]:
    available = list(dict.fromkeys(pages))
    remaining = set(available)
    role = (user_role or "").strip().lower()
    groups: list[dict[str, Any]] = []

    for group_label, routes in TECHNICAL_GROUPS:
        if group_label == "Administração do Cliente" and role not in {"cliente_admin"}:
            continue
        if group_label == "Administração da Plataforma" and role not in {"admin"}:
            continue
        if group_label == "Demonstrações e Suporte" and role not in {"admin"}:
            continue

        items = [
            {"route": route, "label": _technical_page_label(route)}
            for route in routes
            if route in remaining
        ]
        if not items:
            continue
        groups.append({"label": group_label, "items": items})
        for item in items:
            remaining.discard(item["route"])

    leftovers = [{"route": route, "label": _technical_page_label(route)} for route in available if route in remaining]
    if leftovers:
        groups.append({"label": "Outros", "items": leftovers})
    return groups


def _forced_mode_for_role(user_role: str | None) -> str | None:
    role = (user_role or "").strip().lower()
    if role == "operador":
        return "operator"
    if role in {"tecnico", "cliente_admin", "admin"}:
        return "technical"
    return None


def _mode_caption_for_role(user_role: str | None, forced_mode: str) -> str:
    role = (user_role or "").strip().lower()
    if role == "cliente_admin":
        return "Cliente Admin"
    if role == "admin":
        return "Admin Sentinela"
    return "Operador" if forced_mode == "operator" else "Técnico"


def _technical_navigation_label(user_role: str | None) -> str:
    role = (user_role or "").strip().lower()
    if role == "cliente_admin":
        return "Administração do cliente"
    if role == "admin":
        return "Administração da plataforma"
    return "Navegação técnica"


def _is_administrative_role(user_role: str | None) -> bool:
    return (user_role or "").strip().lower() in {"admin", "cliente_admin"}


def render_hmi_sidebar(
    config: dict | None = None,
    menu_config_path: str = "config/hmi_menu_config.json",
    allowed_routes: list[str] | None = None,
    user_role: str | None = None,
) -> dict[str, Any]:
    menu_config = load_hmi_menu_config(menu_config_path)
    config = config or {}
    forced_mode = _forced_mode_for_role(user_role)

    if forced_mode:
        st.session_state["hmi_mode"] = forced_mode
    elif "hmi_mode" not in st.session_state:
        st.session_state["hmi_mode"] = menu_config.get("default_mode", "operator")
    if "selected_asset_id" not in st.session_state:
        st.session_state["selected_asset_id"] = "motor_001"

    st.sidebar.markdown("## Ambiente")
    environment = _get(config, "client", "environment_mode", default="Piloto")
    plant_name = _get(config, "plant", "plant_name", default="Bancada Virtual")
    st.sidebar.caption(f"Atual: {environment} - {plant_name}")

    if forced_mode:
        st.sidebar.markdown("Modo")
        st.sidebar.caption(_mode_caption_for_role(user_role, forced_mode))
    else:
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
        page_map = _filter_operator_pages(_normal_operator_pages(menu_config), allowed_routes)
        if not page_map:
            page_map = [{"id": "no_access", "label": "Sem páginas", "route": "Acesso indisponível"}]
        labels = [item["label"] for item in page_map]
        pending_label = st.session_state.pop(PENDING_OPERATOR_PAGE_KEY, None)
        if pending_label in labels:
            st.session_state["hmi_operator_page"] = pending_label
        if st.session_state.get("hmi_operator_page") not in labels:
            st.session_state["hmi_operator_page"] = labels[0]
        st.sidebar.markdown("Menu do operador")
        groups = _operator_navigation_groups(page_map)
        for group in groups:
            st.sidebar.caption(str(group["label"]))
            for item in group["items"]:
                state_label = str(item["state_label"])
                selected = st.session_state.get("hmi_operator_page") == state_label
                if st.sidebar.button(
                    str(item["label"]),
                    key=f"hmi_operator_button_{item['route']}",
                    type="primary" if selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["hmi_operator_page"] = state_label
                    st.rerun()
        selected_label = st.session_state["hmi_operator_page"]
        selected_item = page_map[labels.index(selected_label)]
        page = selected_item["route"]
        visible_label = selected_item["label"]
        auto_refresh = page != "Ajuda do Operador"
        refresh_interval = 5
    else:
        technical_pages = menu_config.get("technical_pages") or DEFAULT_TECH_PAGES
        technical_pages = [str(page) for page in technical_pages if str(page) != "Modo Apresentação"]
        technical_pages = _filter_technical_pages(technical_pages, allowed_routes)
        if not technical_pages:
            technical_pages = ["Acesso indisponível"]
        applied_pending_page = None
        pending_page = st.session_state.pop(PENDING_TECHNICAL_PAGE_KEY, None)
        if pending_page in technical_pages:
            st.session_state["hmi_technical_page"] = pending_page
            applied_pending_page = pending_page
        if st.session_state.get("hmi_technical_page") not in technical_pages:
            st.session_state["hmi_technical_page"] = technical_pages[0]
        st.sidebar.markdown(_technical_navigation_label(user_role))
        if _is_administrative_role(user_role):
            if applied_pending_page:
                st.session_state[ADMIN_PAGE_SELECT_KEY] = applied_pending_page
            elif st.session_state.get(ADMIN_PAGE_SELECT_KEY) not in technical_pages:
                st.session_state[ADMIN_PAGE_SELECT_KEY] = st.session_state["hmi_technical_page"]
            selected_admin_page = st.sidebar.selectbox(
                "Ir para",
                technical_pages,
                format_func=_technical_page_label,
                key=ADMIN_PAGE_SELECT_KEY,
            )
            st.session_state["hmi_technical_page"] = selected_admin_page
        groups = _technical_navigation_groups(technical_pages, user_role)
        for group in groups:
            st.sidebar.caption(str(group["label"]))
            for item in group["items"]:
                route = str(item["route"])
                selected = st.session_state.get("hmi_technical_page") == route
                if st.sidebar.button(
                    str(item["label"]),
                    key=f"hmi_technical_button_{route}",
                    type="primary" if selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["hmi_technical_page"] = route
                    st.session_state[PENDING_TECHNICAL_PAGE_KEY] = route
                    st.rerun()
        page = st.session_state["hmi_technical_page"]
        visible_label = page
        if _is_administrative_role(user_role):
            auto_refresh = False
            refresh_interval = 5
        else:
            auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True, key="auto_refresh")
            refresh_interval = int(
                st.sidebar.number_input("Intervalo em segundos", min_value=2, max_value=60, value=5, step=1)
            )

    if not _is_administrative_role(user_role):
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
