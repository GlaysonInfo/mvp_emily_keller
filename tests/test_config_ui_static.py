from __future__ import annotations

from pathlib import Path


CONFIG_UI_SOURCE = Path("src/dashboard/config_ui.py")
CONDITION_MONITORING_SOURCE = Path("src/dashboard/condition_monitoring_ui.py")


def test_config_assets_table_exposes_navigation_actions() -> None:
    source = CONFIG_UI_SOURCE.read_text(encoding="utf-8")

    assert "def _render_asset_navigation_table" in source
    assert "_render_asset_navigation_table(assets)" in source
    assert '"Monitoramento de Equipamentos", asset_id=asset_id' in source
    assert '"Detalhe do Ativo", asset_id=asset_id' in source
    assert '"Alertas e Eventos", asset_id=asset_id' in source
    assert "PENDING_CONDITION_ASSET_KEY" in source


def test_condition_monitoring_applies_pending_asset_selection_once() -> None:
    source = CONDITION_MONITORING_SOURCE.read_text(encoding="utf-8")

    assert 'PENDING_SELECTED_ASSET_ID_KEY = "condition_pending_selected_asset_id"' in source
    assert "st.session_state.pop(PENDING_SELECTED_ASSET_ID_KEY, None)" in source
    assert 'st.session_state["condition_operator_asset"] = pending_option' in source
    assert 'st.session_state["condition_technical_asset"] = pending_option' in source
    assert "st.session_state[SELECTED_ASSET_ID_KEY] = asset_id" in source
