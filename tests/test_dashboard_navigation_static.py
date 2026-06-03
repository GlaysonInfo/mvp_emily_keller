from __future__ import annotations

from pathlib import Path

from src.dashboard.navigation import navigation_url


APP_SOURCE = Path("src/dashboard/app.py")
CONDITION_BENCH_SOURCE = Path("src/dashboard/condition_virtual_bench_ui.py")
LUBRICATION_BENCH_SOURCE = Path("src/dashboard/lubrication_virtual_bench/virtual_bench_ui.py")
NAVIGATION_SOURCE = Path("src/dashboard/navigation.py")


def test_navigation_url_encodes_route_and_selection_context() -> None:
    url = navigation_url("Sistema de Lubrificação", asset_id="motor_001", outlet_id="outlet_01")

    assert url.startswith("?")
    assert "route=Sistema+de+Lubrifica%C3%A7%C3%A3o" in url
    assert "asset_id=motor_001" in url
    assert "outlet_id=outlet_01" in url


def test_app_consumes_query_navigation_before_sidebar_route_resolution() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "consume_query_navigation" in source
    assert "query_page_target = consume_query_navigation()" in source
    assert "requested_page_target = query_page_target or st.session_state.pop(PAGE_TARGET_KEY, None)" in source


def test_navigation_helper_renders_same_tab_internal_links() -> None:
    source = NAVIGATION_SOURCE.read_text(encoding="utf-8")

    assert 'target="_self"' in source
    assert 'href="{href}"' in source
    assert "st.query_params.get(\"route\")" in source
    assert "st.query_params.clear()" in source


def test_virtual_benches_use_navigation_links_for_result_views() -> None:
    condition_source = CONDITION_BENCH_SOURCE.read_text(encoding="utf-8")
    lubrication_source = LUBRICATION_BENCH_SOURCE.read_text(encoding="utf-8")

    assert "render_navigation_link" in condition_source
    assert "navigate_to(\"Monitoramento de Equipamentos\"" in condition_source
    assert "render_navigation_link(\"Ver monitoramento\"" in condition_source
    assert "render_navigation_link(\"Abrir detalhe do ativo\"" in condition_source
    assert "render_navigation_link(\"Ver alertas\"" in condition_source

    assert "render_navigation_link" in lubrication_source
    assert "navigate_to(\"Sistema de Lubrificação\"" in lubrication_source
    assert "render_navigation_link(label, \"Sistema de Lubrificação\"" in lubrication_source
    assert "render_navigation_link(\"Ver alertas de lubrificação\"" in lubrication_source
    assert "render_navigation_link(\"Ver eficiência\"" in lubrication_source
