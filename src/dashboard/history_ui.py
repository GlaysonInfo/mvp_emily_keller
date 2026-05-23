from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import streamlit as st

try:
    from dashboard.history_export import MINUTE_COLUMNS, SUMMARY_COLUMNS, minute_rows, rows_to_csv, rows_to_txt, summary_rows
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.history_export import (
        MINUTE_COLUMNS,
        SUMMARY_COLUMNS,
        minute_rows,
        rows_to_csv,
        rows_to_txt,
        summary_rows,
    )


HISTORY_VISIBLE_KEY = "history_visible"

PERIOD_OPTIONS = {
    "Última 1 hora": timedelta(hours=1),
    "Últimas 6 horas": timedelta(hours=6),
    "Últimas 12 horas": timedelta(hours=12),
    "Últimas 24 horas": timedelta(hours=24),
    "Últimos 7 dias": timedelta(days=7),
}

FORMAT_OPTIONS = {
    "Minuto a minuto": None,
    "Resumo 1h": 1,
    "Resumo 6h": 6,
    "Resumo 12h": 12,
    "Resumo 24h": 24,
}


def render_history_button(
    *,
    history_repo: Any,
    tenant_id: str,
    asset_id: str,
    timezone_str: str = "America/Sao_Paulo",
) -> None:
    if st.button("Histórico", type="secondary"):
        st.session_state[HISTORY_VISIBLE_KEY] = not st.session_state.get(HISTORY_VISIBLE_KEY, False)

    if not st.session_state.get(HISTORY_VISIBLE_KEY, False):
        return

    st.divider()
    st.subheader("Histórico operacional exportável")

    c1, c2 = st.columns(2)
    period_label = c1.selectbox("Período", options=list(PERIOD_OPTIONS.keys()))
    format_label = c2.selectbox("Formato", options=list(FORMAT_OPTIONS.keys()))

    end_utc = datetime.now(UTC)
    start_utc = end_utc - PERIOD_OPTIONS[period_label]
    items = history_repo.query_history(
        tenant_id=tenant_id,
        asset_id=asset_id,
        start_utc=start_utc,
        end_utc=end_utc,
    )

    window_hours = FORMAT_OPTIONS[format_label]

    if window_hours is None:
        rows = minute_rows(items, timezone_str=timezone_str)
        columns = MINUTE_COLUMNS
    else:
        rows = summary_rows(items, window_hours=window_hours, timezone_str=timezone_str)
        columns = SUMMARY_COLUMNS

    st.caption(f"{len(rows)} registro(s) encontrados.")

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro histórico encontrado para o período selecionado.")

    csv_data = rows_to_csv(rows, columns=columns)
    txt_data = rows_to_txt(rows, title=f"Histórico operacional - {format_label} - {period_label}")
    file_suffix = format_label.lower().replace(" ", "_").replace("ú", "u")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Exportar CSV",
        data=csv_data,
        file_name=f"historico_{asset_id}_{file_suffix}.csv",
        mime="text/csv",
        disabled=not rows,
        use_container_width=True,
    )
    d2.download_button(
        "Exportar TXT",
        data=txt_data,
        file_name=f"historico_{asset_id}_{file_suffix}.txt",
        mime="text/plain",
        disabled=not rows,
        use_container_width=True,
    )
