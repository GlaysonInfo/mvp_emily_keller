from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st

try:
    from dashboard.hmi.hmi_sidebar import set_operator_page_for_route
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.hmi.hmi_sidebar import set_operator_page_for_route


PAGE_TARGET_KEY = "dashboard_page_target"
SELECTED_ASSET_ID_KEY = "selected_asset_id"
SELECTED_OUTLET_ID_KEY = "selected_outlet_id"
PENDING_CONDITION_ASSET_KEY = "condition_pending_selected_asset_id"


def set_dashboard_target(route: str, *, asset_id: str | None = None, outlet_id: str | None = None) -> None:
    if asset_id:
        st.session_state[SELECTED_ASSET_ID_KEY] = asset_id
        st.session_state[PENDING_CONDITION_ASSET_KEY] = asset_id
    if outlet_id:
        st.session_state[SELECTED_OUTLET_ID_KEY] = outlet_id
    st.session_state[PAGE_TARGET_KEY] = route
    set_operator_page_for_route(route)


def navigation_url(route: str, *, asset_id: str | None = None, outlet_id: str | None = None) -> str:
    params = {"route": route}
    if asset_id:
        params["asset_id"] = asset_id
    if outlet_id:
        params["outlet_id"] = outlet_id
    return "?" + urlencode(params)


def consume_query_navigation() -> str | None:
    route = st.query_params.get("route")
    if not route:
        return None

    asset_id = st.query_params.get("asset_id")
    outlet_id = st.query_params.get("outlet_id")
    set_dashboard_target(str(route), asset_id=str(asset_id) if asset_id else None, outlet_id=str(outlet_id) if outlet_id else None)
    st.query_params.clear()
    return str(route)


def navigate_to(route: str, *, asset_id: str | None = None, outlet_id: str | None = None) -> None:
    set_dashboard_target(route, asset_id=asset_id, outlet_id=outlet_id)
    st.rerun()


def render_navigation_link(
    label: str,
    route: str,
    *,
    asset_id: str | None = None,
    outlet_id: str | None = None,
    primary: bool = False,
) -> None:
    href = navigation_url(route, asset_id=asset_id, outlet_id=outlet_id)
    background = "#ff4b4b" if primary else "#ffffff"
    border = "#ff4b4b" if primary else "#d0d5dd"
    color = "#ffffff" if primary else "#111827"
    st.markdown(
        f"""
        <a href="{href}" target="_self" style="
            display:block;
            width:100%;
            box-sizing:border-box;
            text-align:center;
            padding:0.5rem 0.75rem;
            margin:0.15rem 0;
            border:1px solid {border};
            border-radius:0.5rem;
            background:{background};
            color:{color};
            text-decoration:none;
            font-weight:500;">
            {label}
        </a>
        """,
        unsafe_allow_html=True,
    )


def render_navigation_icon(
    route: str,
    *,
    label: str,
    icon: str,
    asset_id: str | None = None,
    outlet_id: str | None = None,
    primary: bool = False,
) -> None:
    st.link_button(
        " ",
        navigation_url(route, asset_id=asset_id, outlet_id=outlet_id),
        help=label,
        type="primary" if primary else "secondary",
        icon=icon,
        width="stretch",
    )
