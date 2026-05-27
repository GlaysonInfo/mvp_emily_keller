from __future__ import annotations

from pathlib import Path

from src.dashboard.hmi.hmi_labels import operator_status_label
from src.dashboard.hmi.hmi_sidebar import DEFAULT_TECH_PAGES, load_hmi_menu_config


HMI_SIDEBAR_SOURCE = Path("src/dashboard/hmi/hmi_sidebar.py")


def test_hmi_menu_config_exposes_operator_and_technical_modes() -> None:
    config = load_hmi_menu_config("config/hmi_menu_config.json")

    operator_labels = [item["label"] for item in config["operator_pages"]]

    assert operator_labels == [
        "Painel da Planta",
        "Equipamento",
        "Lubrificação",
        "Eficiência",
        "Alertas",
        "Relatórios",
        "Ajuda",
    ]
    assert "Configuração de Campo — Lubrificação" in config["technical_pages"]
    assert "Eficiência da Lubrificação" in config["technical_pages"]
    assert "Bancada Virtual — Lubrificação" in config["technical_pages"]
    assert "Modo Apresentação" not in config["technical_pages"]


def test_default_technical_pages_keep_support_routes() -> None:
    assert "Bancada Virtual — Lubrificação" in DEFAULT_TECH_PAGES
    assert "Matriz de Escalonamento" in DEFAULT_TECH_PAGES
    assert "Notification Outbox" in DEFAULT_TECH_PAGES
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
