from __future__ import annotations

from pathlib import Path

from src.dashboard.hmi.hmi_labels import operator_status_label
from src.dashboard.hmi.hmi_sidebar import (
    DEFAULT_OPERATOR_PAGES,
    DEFAULT_TECH_PAGES,
    _filter_operator_pages,
    _filter_technical_pages,
    _forced_mode_for_role,
    _is_administrative_role,
    _mode_caption_for_role,
    _operator_navigation_groups,
    _technical_navigation_label,
    _technical_navigation_groups,
    load_hmi_menu_config,
)


HMI_SIDEBAR_SOURCE = Path("src/dashboard/hmi/hmi_sidebar.py")


def test_hmi_menu_config_exposes_operator_and_technical_modes() -> None:
    config = load_hmi_menu_config("config/hmi_menu_config.json")

    operator_labels = [item["label"] for item in config["operator_pages"]]

    assert operator_labels == [
        "Equipamentos",
        "Painel da Planta",
        "Equipamento",
        "Operação Lub.",
        "Lubrificação",
        "Eficiência",
        "Alertas",
        "Relatórios",
        "Ajuda",
    ]
    assert "Configuração de Campo — Lubrificação" in config["technical_pages"]
    assert "Bancada Virtual — Equipamentos" in config["technical_pages"]
    assert "Eficiência da Lubrificação" in config["technical_pages"]
    assert "Eficiência da Lubrificação do Motor" in config["technical_pages"]
    assert "Bancada Virtual — Lubrificação" in config["technical_pages"]
    assert "Modo Apresentação" not in config["technical_pages"]


def test_default_technical_pages_keep_support_routes() -> None:
    assert "Monitoramento de Equipamentos" in DEFAULT_TECH_PAGES
    assert "Operação de Lubrificação" in DEFAULT_TECH_PAGES
    assert "Bancada Virtual — Equipamentos" in DEFAULT_TECH_PAGES
    assert "Eficiência da Lubrificação do Motor" in DEFAULT_TECH_PAGES
    assert "Bancada Virtual — Lubrificação" in DEFAULT_TECH_PAGES
    assert "Matriz de Escalonamento" in DEFAULT_TECH_PAGES
    assert "Notification Outbox" in DEFAULT_TECH_PAGES
    assert "Admin do Cliente" in DEFAULT_TECH_PAGES
    assert "Admin da Plataforma" in DEFAULT_TECH_PAGES
    assert "Arquitetura Modular" in DEFAULT_TECH_PAGES
    assert "Teste ponta a ponta" in DEFAULT_TECH_PAGES


def test_operator_status_label_uses_field_language() -> None:
    assert operator_status_label("CRITICO") == ("Crítico", "CRÍTICO")
    assert operator_status_label("NORMAL") == ("Operação normal", "OK")


def test_operator_route_changes_are_applied_before_sidebar_widget_is_created() -> None:
    source = HMI_SIDEBAR_SOURCE.read_text(encoding="utf-8")
    setter_body = source.split("def set_operator_page_for_route", 1)[1].split("\ndef _get", 1)[0]

    assert "st.session_state[PENDING_OPERATOR_PAGE_KEY] = label" in setter_body
    assert 'st.session_state["hmi_operator_page"] = label' not in setter_body
    assert "pending_label = st.session_state.pop(PENDING_OPERATOR_PAGE_KEY, None)" in source
    assert "hmi_operator_button_" in source
    assert 'st.sidebar.radio("Menu do operador"' not in source


def test_sidebar_pages_can_be_filtered_by_allowed_routes() -> None:
    allowed_routes = [
        "Visão Geral da Planta",
        "Operação de Lubrificação",
        "Sistema de Lubrificação",
        "Configurações",
    ]

    operator_pages = _filter_operator_pages(DEFAULT_OPERATOR_PAGES, allowed_routes)
    technical_pages = _filter_technical_pages(DEFAULT_TECH_PAGES, allowed_routes)

    assert [page["route"] for page in operator_pages] == [
        "Visão Geral da Planta",
        "Operação de Lubrificação",
        "Sistema de Lubrificação",
    ]
    assert technical_pages == [
        "Visão Geral da Planta",
        "Operação de Lubrificação",
        "Sistema de Lubrificação",
        "Configurações",
    ]


def test_operator_navigation_groups_routes_by_operational_domain() -> None:
    pages = _filter_operator_pages(
        DEFAULT_OPERATOR_PAGES,
        [
            "Monitoramento de Equipamentos",
            "Detalhe do Ativo",
            "Operação de Lubrificação",
            "Sistema de Lubrificação",
            "Alertas e Eventos",
            "Relatórios",
        ],
    )

    groups = _operator_navigation_groups(pages)

    assert [group["label"] for group in groups] == [
        "Monitoramento de Equipamentos",
        "Sistema de Lubrificação",
        "Alertas e Relatórios",
    ]
    assert groups[0]["items"][0] == {
        "route": "Monitoramento de Equipamentos",
        "label": "Equipamentos",
        "state_label": "Equipamentos",
    }
    assert {
        "route": "Operação de Lubrificação",
        "label": "Operação Lub.",
        "state_label": "Operação Lub.",
    } in groups[1]["items"]


def test_technical_navigation_groups_routes_by_professional_domain() -> None:
    pages = [
        "Monitoramento de Equipamentos",
        "Detalhe do Ativo",
        "Operação de Lubrificação",
        "Configuração de Campo — Lubrificação",
        "Inteligência Operacional",
        "Alertas e Eventos",
        "Relatórios",
    ]

    groups = _technical_navigation_groups(pages, "tecnico")

    assert [group["label"] for group in groups] == [
        "Monitoramento de Equipamentos",
        "Sistema de Lubrificação",
        "Inteligência Operacional",
        "Alertas e Notificações",
        "Relatórios",
    ]
    assert groups[0]["items"][0] == {
        "route": "Monitoramento de Equipamentos",
        "label": "Ativos monitorados",
    }
    assert {
        "route": "Configuração de Campo — Lubrificação",
        "label": "Parâmetros de campo",
    } in groups[1]["items"]


def test_admin_navigation_groups_keep_demo_and_support_tools_separate() -> None:
    pages = [
        "Admin da Plataforma",
        "Configurações",
        "Matriz de Escalonamento",
        "Notification Outbox",
        "Bancada Virtual — Equipamentos",
        "Eficiência da Lubrificação do Motor",
        "Bancada Virtual — Lubrificação",
    ]

    groups = _technical_navigation_groups(pages, "admin")

    assert [group["label"] for group in groups] == [
        "Alertas e Notificações",
        "Administração da Plataforma",
        "Demonstrações e Suporte",
    ]
    assert {
        "route": "Notification Outbox",
        "label": "Fila de notificações",
    } in groups[0]["items"]
    assert {
        "route": "Bancada Virtual — Equipamentos",
        "label": "Bancada de equipamentos",
    } in groups[2]["items"]
    assert {
        "route": "Bancada Virtual — Lubrificação",
        "label": "Bancada virtual",
    } in groups[2]["items"]


def test_authenticated_roles_force_expected_sidebar_mode() -> None:
    assert _forced_mode_for_role("operador") == "operator"
    assert _forced_mode_for_role("tecnico") == "technical"
    assert _forced_mode_for_role("cliente_admin") == "technical"
    assert _forced_mode_for_role("admin") == "technical"
    assert _forced_mode_for_role(None) is None


def test_authenticated_admin_roles_use_specific_sidebar_labels() -> None:
    assert _mode_caption_for_role("cliente_admin", "technical") == "Cliente Admin"
    assert _mode_caption_for_role("admin", "technical") == "Admin Sentinela"
    assert _mode_caption_for_role("tecnico", "technical") == "Técnico"
    assert _technical_navigation_label("cliente_admin") == "Administração do cliente"
    assert _technical_navigation_label("admin") == "Administração da plataforma"
    assert _technical_navigation_label("tecnico") == "Navegação técnica"
    assert _is_administrative_role("cliente_admin")
    assert _is_administrative_role("admin")
    assert not _is_administrative_role("tecnico")
    assert not _is_administrative_role("operador")
