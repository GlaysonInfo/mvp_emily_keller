from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError
import streamlit as st

try:
    from dashboard.alert_projection import alerts_with_state_derived
    from dashboard.reports import (
        PERIODS,
        REPORT_FILENAMES,
        REPORTS_BY_TYPE,
        alert_rows,
        export_csv,
        export_txt,
        filter_alerts_by_period,
        find_state,
        individual_asset_report,
        normalize_asset_options,
        period_bounds,
        plant_overview_report,
        risk_ranking_report,
        trend_report,
    )
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alert_projection import alerts_with_state_derived
    from src.dashboard.reports import (
        PERIODS,
        REPORT_FILENAMES,
        REPORTS_BY_TYPE,
        alert_rows,
        export_csv,
        export_txt,
        filter_alerts_by_period,
        find_state,
        individual_asset_report,
        normalize_asset_options,
        period_bounds,
        plant_overview_report,
        risk_ranking_report,
        trend_report,
    )


def download_name(report_name: str, extension: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = REPORT_FILENAMES.get(report_name, "relatorio")
    return f"{base}_{stamp}.{extension}"


def render_downloads(rows: list[dict[str, Any]], report_name: str) -> None:
    c1, c2 = st.columns(2)
    csv_content = export_csv(rows)
    txt_content = export_txt(rows, report_name)

    c1.download_button(
        "Exportar CSV",
        data=csv_content.encode("utf-8-sig"),
        file_name=download_name(report_name, "csv"),
        mime="text/csv",
        disabled=not rows,
        use_container_width=True,
    )
    c2.download_button(
        "Exportar TXT",
        data=txt_content.encode("utf-8"),
        file_name=download_name(report_name, "txt"),
        mime="text/plain",
        disabled=not rows,
        use_container_width=True,
    )


def render_report_preview(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("Nenhum dado encontrado para este relatório.")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)


def asset_selectbox(states: list[dict[str, Any]], selected_asset_id: str, *, include_all: bool = False) -> str:
    options = normalize_asset_options(states)

    if not options:
        return selected_asset_id

    values = [asset_id for asset_id, _label in options]
    labels = {asset_id: label for asset_id, label in options}

    if include_all:
        values = ["Todos"] + values
        labels["Todos"] = "Todos"

    index = values.index(selected_asset_id) if selected_asset_id in values else 0

    return st.selectbox(
        "Ativo",
        values,
        index=index,
        format_func=lambda asset_id: labels.get(asset_id, asset_id),
    )


def render_reports_page(
    *,
    states: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    history_repo: Any | None,
    tenant_id: str,
    selected_asset_id: str,
) -> None:
    st.subheader("Relatórios")

    report_type = st.selectbox("Tipo de relatório", list(REPORTS_BY_TYPE.keys()))
    report_name = st.selectbox("Relatório", REPORTS_BY_TYPE[report_type])
    period_label = st.selectbox("Período", list(PERIODS.keys()), index=3)
    requires_asset = report_name in {"Relatório individual do ativo", "Tendência operacional"}
    asset_id = asset_selectbox(states, selected_asset_id, include_all=not requires_asset)

    st.button("Gerar relatório", type="primary")

    rows: list[dict[str, Any]]

    if report_name == "Visão geral da planta":
        rows = plant_overview_report(states)
    elif report_name == "Ranking de risco":
        rows = risk_ranking_report(states)
    elif report_name == "Relatório individual do ativo":
        rows = individual_asset_report(find_state(states, asset_id))
    elif report_name == "Tendência operacional":
        rows = []

        if history_repo is None:
            st.warning("Histórico indisponível. Crie ou configure a tabela `condition_history` para gerar tendência.")
        else:
            start, end = period_bounds(period_label)
            try:
                history_items = history_repo.query_history(
                    tenant_id=tenant_id,
                    asset_id=asset_id,
                    start_utc=start,
                    end_utc=end,
                )
            except ClientError as exc:
                st.warning(f"Não foi possível consultar o histórico: {exc}")
            else:
                rows = trend_report(history_items, period_label=period_label)
    elif report_name == "Alertas ativos":
        report_alerts = alerts if asset_id == "Todos" else [alert for alert in alerts if alert.get("asset_id") == asset_id]
        report_states = states if asset_id == "Todos" else [state for state in states if state.get("asset_id") == asset_id]
        rows = alert_rows(alerts_with_state_derived(report_alerts, report_states), states, active_only=True)
    elif report_name == "Histórico de alertas":
        report_alerts = alerts if asset_id == "Todos" else [alert for alert in alerts if alert.get("asset_id") == asset_id]
        filtered_alerts = filter_alerts_by_period(report_alerts, period_label)
        rows = alert_rows(filtered_alerts, states, active_only=False)
    else:
        rows = []

    render_report_preview(rows)
    render_downloads(rows, report_name)
