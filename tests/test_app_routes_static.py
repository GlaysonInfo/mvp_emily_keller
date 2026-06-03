from __future__ import annotations

from pathlib import Path


APP_SOURCE = Path("src/dashboard/app.py")
OPERATIONAL_INTELLIGENCE_SOURCE = Path("src/dashboard/operational_intelligence_ui.py")


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


def test_condition_monitoring_route_stops_before_plant_overview() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "CONDITION_MONITORING_PAGE" in source
    assert "render_condition_monitoring_page(" in source
    condition_route = source.split("if page == CONDITION_MONITORING_PAGE:", 1)[1].split(
        "\n    if mode == \"operator\"",
        1,
    )[0]

    assert "render_condition_monitoring_page(" in condition_route
    assert "render_plant_overview" not in condition_route
    assert "st.stop()" in condition_route
    assert "return" in condition_route


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


def test_lubrication_operation_route_stops_before_specialized_lubrication_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "LUBRICATION_OPERATION_PAGE" in source
    assert "render_lubrication_operation_page(" in source
    operation_route = source.split("elif page == LUBRICATION_OPERATION_PAGE:", 1)[1].split(
        "\n    elif page ==",
        1,
    )[0]

    assert "render_lubrication_operation_page(" in operation_route
    assert "render_lubrication_page(" not in operation_route
    assert "render_plant_overview" not in operation_route
    assert "st.stop()" in operation_route
    assert "return" in operation_route


def test_lubrication_efficiency_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    efficiency_route = _route_block(source, "Eficiência da Lubrificação")

    assert "render_lubrication_efficiency_page(" in efficiency_route
    assert "render_lubrication_page(" not in efficiency_route
    assert "render_plant_overview" not in efficiency_route
    assert "st.stop()" in efficiency_route
    assert "return" in efficiency_route


def test_motor_lubrication_efficiency_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    motor_efficiency_route = _route_block(source, "Eficiência da Lubrificação do Motor")

    assert "render_motor_lubrication_efficiency_page(" in motor_efficiency_route
    assert "render_lubrication_page(" not in motor_efficiency_route
    assert "render_plant_overview" not in motor_efficiency_route
    assert "st.stop()" in motor_efficiency_route
    assert "return" in motor_efficiency_route


def test_lubrication_virtual_bench_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    bench_route = _route_block(source, "Bancada Virtual — Lubrificação")

    assert "render_lubrication_virtual_bench_page(" in bench_route
    assert "render_lubrication_page(" not in bench_route
    assert "render_plant_overview" not in bench_route
    assert "st.stop()" in bench_route
    assert "return" in bench_route


def test_condition_virtual_bench_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "CONDITION_VIRTUAL_BENCH_PAGE" in source
    assert "render_condition_virtual_bench_page(" in source
    bench_route = source.split("elif page == CONDITION_VIRTUAL_BENCH_PAGE:", 1)[1].split(
        "\n    elif page ==",
        1,
    )[0]

    assert "render_condition_virtual_bench_page(" in bench_route
    assert "render_lubrication_virtual_bench_page(" not in bench_route
    assert "render_plant_overview" not in bench_route
    assert "st.stop()" in bench_route
    assert "return" in bench_route


def test_lubrication_field_config_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    field_config_route = _route_block(source, "Configuração de Campo — Lubrificação")

    assert "render_lubrication_field_config_page(" in field_config_route
    assert "render_lubrication_page(" not in field_config_route
    assert "render_plant_overview" not in field_config_route
    assert "st.stop()" in field_config_route
    assert "return" in field_config_route


def test_app_uses_hmi_sidebar_instead_of_raw_technical_menu() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "render_hmi_sidebar(" in source
    assert "user_role=identity.role if identity is not None else None" in source
    assert "allowed_routes_for_context" in source
    assert "contracted_services_for_context" in source
    assert "default_route_for_role(identity.role, allowed_routes)" in source
    assert "ROLE_ROUTE_INIT_KEY" in source
    assert "enforce_modular_page_access" in source
    assert "st.session_state[DASHBOARD_PAGE_KEY] = page" in source
    assert "render_operator_home(operator_states)" in source
    assert "render_operator_help()" in source
    assert 'st.radio(\n            "Navegação",' not in source


def test_modular_architecture_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "MODULAR_ARCHITECTURE_PAGE" in source
    assert "render_modular_architecture_page()" in source
    modular_route = source.split("elif page == MODULAR_ARCHITECTURE_PAGE:", 1)[1].split(
        "\n    elif page ==",
        1,
    )[0]

    assert "render_modular_architecture_page()" in modular_route
    assert "st.stop()" in modular_route
    assert "return" in modular_route


def test_platform_admin_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "PLATFORM_ADMIN_PAGE" in source
    assert "render_platform_admin_page(" in source
    admin_route = source.split("elif page == PLATFORM_ADMIN_PAGE:", 1)[1].split(
        "\n    elif page ==",
        1,
    )[0]

    assert "render_platform_admin_page(" in admin_route
    assert "st.stop()" in admin_route
    assert "return" in admin_route


def test_client_admin_route_stops_before_other_pages() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "CLIENT_ADMIN_PAGE" in source
    assert "render_client_admin_page(" in source
    client_admin_route = source.split("elif page == CLIENT_ADMIN_PAGE:", 1)[1].split(
        "\n    elif page ==",
        1,
    )[0]

    assert "render_client_admin_page(" in client_admin_route
    assert "st.stop()" in client_admin_route
    assert "return" in client_admin_route


def test_data_errors_are_not_rendered_raw_to_user() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")
    intelligence_source = OPERATIONAL_INTELLIGENCE_SOURCE.read_text(encoding="utf-8")

    assert "render_client_error(" in source
    assert "client_error_user_message(" in source
    assert "IncompleteSignatureException" in source
    assert 'st.error(f"Não foi possível carregar' not in source
    assert 'st.error(f"Não foi possível carregar' not in intelligence_source
    assert "_render_data_error(" in intelligence_source
