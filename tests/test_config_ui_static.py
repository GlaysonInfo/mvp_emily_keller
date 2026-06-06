from __future__ import annotations

from pathlib import Path


CONFIG_UI_SOURCE = Path("src/dashboard/config_ui.py")
CONDITION_MONITORING_SOURCE = Path("src/dashboard/condition_monitoring_ui.py")
ALERTS_UI_SOURCE = Path("src/dashboard/alerts_ui.py")
PLATFORM_ADMIN_SOURCE = Path("src/dashboard/platform_admin_ui.py")


def test_config_save_uses_versioned_repository_for_technical_changes() -> None:
    source = CONFIG_UI_SOURCE.read_text(encoding="utf-8")
    save_block = source.split("def _save", 1)[1].split("\ndef _replace_by_key", 1)[0]

    assert "repo.save_versioned(" in save_block
    assert "audit.current_actor()" in save_block
    assert '"config.save"' in save_block


def test_config_assets_table_exposes_navigation_actions() -> None:
    source = CONFIG_UI_SOURCE.read_text(encoding="utf-8")

    assert "def _render_asset_navigation_table" in source
    assert "_render_asset_navigation_table(assets)" in source
    assert "render_navigation_icon" in source
    assert "PENDING_CONDITION_ASSET_KEY" in source
    asset_table = source.split("def _render_asset_navigation_table", 1)[1].split("\ndef render_config_page", 1)[0]
    assert ".button(" not in asset_table
    assert '"Monitoramento de Equipamentos"' in asset_table
    assert '"Detalhe do Ativo"' in asset_table
    assert '"Alertas e Eventos"' in asset_table
    assert "asset_id=asset_id" in asset_table


def test_platform_inventory_exposes_per_asset_actions() -> None:
    source = PLATFORM_ADMIN_SOURCE.read_text(encoding="utf-8")

    assert "def _render_inventory_action_table" in source
    assert "_render_inventory_action_table(inventory_rows)" in source
    assert "render_navigation_icon" in source
    inventory_table = source.split("def _render_inventory_action_table", 1)[1].split("\ndef _asset_inventory_rows", 1)[0]
    assert ".button(" not in inventory_table
    assert '"Monitoramento de Equipamentos"' in inventory_table
    assert '"Detalhe do Ativo"' in inventory_table
    assert '"Alertas e Eventos"' in inventory_table
    assert "asset_id=asset_id" in inventory_table


def test_condition_monitoring_applies_pending_asset_selection_once() -> None:
    source = CONDITION_MONITORING_SOURCE.read_text(encoding="utf-8")

    assert 'PENDING_SELECTED_ASSET_ID_KEY = "condition_pending_selected_asset_id"' in source
    assert "st.session_state.pop(PENDING_SELECTED_ASSET_ID_KEY, None)" in source
    assert 'st.session_state["condition_operator_asset"] = pending_option' in source
    assert 'st.session_state["condition_technical_asset"] = pending_option' in source
    assert "st.session_state[SELECTED_ASSET_ID_KEY] = asset_id" in source


def test_condition_monitoring_lists_have_action_buttons() -> None:
    source = CONDITION_MONITORING_SOURCE.read_text(encoding="utf-8")

    assert "def _render_actionable_alert_queue" in source
    assert "def _render_actionable_assets_view" in source
    assert "_render_actionable_alert_queue(active_alerts)" in source
    assert "_render_actionable_assets_view(rows, assets)" in source
    assert "render_navigation_icon" in source
    assert '"Detalhe do Ativo",' in source
    assert '"Alertas e Eventos",' in source


def test_alert_center_cards_expose_asset_navigation() -> None:
    source = ALERTS_UI_SOURCE.read_text(encoding="utf-8")

    assert "def _navigate_to" in source
    assert "render_navigation_icon" in source
    assert "label=\"Abrir ativo\"" in source
    assert "label=\"Monitorar ativo\"" in source
    assert "label=\"Abrir detalhe do ativo\"" in source
    assert '"Detalhe do Ativo"' in source
    assert '"Monitoramento de Equipamentos"' in source
    assert "asset_id=asset_id" in source
