from __future__ import annotations

from pathlib import Path


APP_SOURCE = Path("src/dashboard/app.py")


def _route_block(source: str, route_name: str) -> str:
    marker = f'elif page == "{route_name}":'
    start = source.index(marker)
    next_route = source.find("\n    elif page ==", start + len(marker))
    fallback = source.find("\n    st.error(", start + len(marker))
    end_candidates = [index for index in [next_route, fallback] if index != -1]
    end = min(end_candidates) if end_candidates else len(source)
    return source[start:end]


def test_plant_overview_render_stays_inside_plant_route() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    plant_route = _route_block(source, "Visão Geral da Planta")

    assert source.count("render_plant_overview(states)") == 1
    assert "render_plant_overview(states)" in plant_route


def test_asset_detail_route_stops_before_any_other_page() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    detail_route = _route_block(source, "Detalhe do Ativo")

    assert "render_asset_detail(" in detail_route
    assert "render_plant_overview" not in detail_route
    assert "st.stop()" in detail_route
    assert "return" in detail_route


def test_lubrication_route_stops_before_plant_overview() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    lubrication_route = _route_block(source, "Sistema de Lubrificação")

    assert "render_lubrication_page(" in lubrication_route
    assert "render_plant_overview" not in lubrication_route
    assert "st.stop()" in lubrication_route
    assert "return" in lubrication_route
