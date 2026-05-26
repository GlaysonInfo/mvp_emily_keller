from __future__ import annotations

from src.dashboard.hmi.hmi_labels import operator_status_label
from src.dashboard.hmi.hmi_sidebar import DEFAULT_TECH_PAGES, load_hmi_menu_config


def test_hmi_menu_config_exposes_operator_and_technical_modes() -> None:
    config = load_hmi_menu_config("config/hmi_menu_config.json")

    operator_labels = [item["label"] for item in config["operator_pages"]]

    assert operator_labels == [
        "Painel da Planta",
        "Equipamento",
        "Lubrificação",
        "Alertas",
        "Relatórios",
        "Ajuda",
    ]
    assert "Configuração de Campo — Lubrificação" in config["technical_pages"]
    assert "Modo Apresentação" not in config["technical_pages"]


def test_default_technical_pages_keep_support_routes() -> None:
    assert "Matriz de Escalonamento" in DEFAULT_TECH_PAGES
    assert "Notification Outbox" in DEFAULT_TECH_PAGES
    assert "Teste ponta a ponta" in DEFAULT_TECH_PAGES


def test_operator_status_label_uses_field_language() -> None:
    assert operator_status_label("CRITICO") == ("Crítico", "CRÍTICO")
    assert operator_status_label("NORMAL") == ("Operação normal", "OK")
