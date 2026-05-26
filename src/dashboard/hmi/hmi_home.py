from __future__ import annotations

import streamlit as st

from .hmi_labels import operator_status_label
from .hmi_sidebar import set_operator_page_for_route


def _status_text(value: object) -> str:
    return str(value or "").upper()


def render_operator_home(current_states: list[dict] | None = None) -> None:
    current_states = current_states or []

    total = len(current_states)
    critical = sum(1 for s in current_states if _status_text(s.get("status_label")) in ["CRÍTICO", "CRITICO"])
    alerts = sum(1 for s in current_states if _status_text(s.get("status_label")) in ["ALERTA", "ATENÇÃO ALTA"])
    attention = sum(1 for s in current_states if _status_text(s.get("status_label")) == "ATENÇÃO")
    normal = sum(1 for s in current_states if _status_text(s.get("status_label")) in ["NORMAL", "RECUPERADO"])

    st.markdown('<div class="hmi-title">Painel da Planta</div>', unsafe_allow_html=True)
    st.markdown('<div class="hmi-subtitle">Visão simples para operação de campo.</div>', unsafe_allow_html=True)

    if critical:
        st.markdown(
            f'<div class="hmi-status-critical">CRÍTICO: {critical} equipamento(s) exigem verificação imediata.</div>',
            unsafe_allow_html=True,
        )
    elif alerts or attention:
        st.markdown(
            '<div class="hmi-status-warning">ATENÇÃO: há equipamentos com alerta ou desvio para verificar.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="hmi-status-ok">NORMAL: planta sem alertas críticos no momento.</div>',
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Equipamentos", total)
    c2.metric("Normais", normal)
    c3.metric("Atenção", attention)
    c4.metric("Alertas", alerts)
    c5.metric("Críticos", critical)

    st.subheader("Prioridade de verificação")

    if not current_states:
        st.info("Nenhum equipamento carregado para a visão do operador.")
        return

    rank = {"CRÍTICO": 1, "CRITICO": 1, "ALERTA": 2, "ATENÇÃO ALTA": 3, "ATENÇÃO": 4, "RECUPERADO": 5, "NORMAL": 6}
    ordered = sorted(
        current_states,
        key=lambda s: (rank.get(_status_text(s.get("status_label")), 99), float(s.get("health_score", 100) or 100)),
    )

    for idx, state in enumerate(ordered[:8], start=1):
        status, badge = operator_status_label(state.get("status_label"))
        asset_name = state.get("asset_name") or state.get("asset_id")
        area = state.get("area", "-")
        mode = state.get("mode_label") or state.get("mode", "-")
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.markdown(f"**{idx}. [{badge}] {asset_name}**")
            col1.caption(f"{area} | {status} | {mode}")
            col2.metric("Saúde", state.get("health_score", "-"))
            col3.metric("Gravidade", state.get("severity_score", "-"))
            if st.button("Abrir equipamento", key=f"open_asset_{state.get('asset_id')}", use_container_width=True):
                st.session_state["selected_asset_id"] = state.get("asset_id")
                set_operator_page_for_route("Detalhe do Ativo")
                st.rerun()
