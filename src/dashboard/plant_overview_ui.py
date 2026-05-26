from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st


STATUS_ORDER = {
    "SEM COMUNICAÇÃO": 6,
    "SEM COMUNICACAO": 6,
    "CRÍTICO": 5,
    "CRITICO": 5,
    "ALERTA": 4,
    "ATENÇÃO ALTA": 3,
    "ATENCAO ALTA": 3,
    "ATENÇÃO": 2,
    "ATENCAO": 2,
    "RECUPERADO": 1,
    "NORMAL": 0,
}

STATUS_COLORS = {
    "NORMAL": "#2ECC71",
    "RECUPERADO": "#27AE60",
    "ATENÇÃO": "#F1C40F",
    "ATENCAO": "#F1C40F",
    "ATENÇÃO ALTA": "#E67E22",
    "ATENCAO ALTA": "#E67E22",
    "ALERTA": "#E67E22",
    "CRÍTICO": "#E74C3C",
    "CRITICO": "#E74C3C",
    "SEM COMUNICAÇÃO": "#95A5A6",
    "SEM COMUNICACAO": "#95A5A6",
}


def safe_float(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, bool) or value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_metric(item: dict[str, Any], *names: str) -> float | None:
    metrics = item.get("metrics")
    metric_map = metrics if isinstance(metrics, dict) else {}

    for name in names:
        value = safe_float(item.get(name))

        if value is not None:
            return value

        value = safe_float(metric_map.get(name))

        if value is not None:
            return value

    return None


def format_updated_at(value: Any, timezone_str: str = "America/Sao_Paulo") -> str:
    if not value:
        return "-"

    if not isinstance(value, str):
        return str(value)

    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value

    return timestamp.astimezone(ZoneInfo(timezone_str)).strftime("%d/%m/%Y %H:%M")


def status_rank(status: Any) -> int:
    return STATUS_ORDER.get(str(status or "").upper(), 0)


def status_color(status: Any) -> str:
    return STATUS_COLORS.get(str(status or "").upper(), "#7F8C8D")


def state_to_row(item: dict[str, Any]) -> dict[str, Any]:
    status = item.get("status_label") or "-"
    health_score = get_metric(item, "health_score")
    severity_score = get_metric(item, "severity_score", "severity")

    if severity_score is None and health_score is not None:
        severity_score = round(100.0 - health_score, 1)

    return {
        "asset_id": item.get("asset_id", "-"),
        "asset_name": item.get("asset_name") or item.get("asset_id", "-"),
        "asset_type": item.get("asset_type", "-"),
        "area": item.get("area", "-"),
        "criticality": item.get("criticality", "-"),
        "mode": item.get("mode_label") or item.get("failure_mode_simulated") or item.get("mode", "-"),
        "status_label": status,
        "health_score": health_score,
        "severity_score": severity_score or 0.0,
        "rpm": get_metric(item, "rpm"),
        "vibration_rms_mm_s": get_metric(item, "vibration_rms_mm_s", "vibration_rms"),
        "temperature_c": get_metric(item, "temperature_c", "temperature"),
        "ultrasound_db": get_metric(item, "ultrasound_db", "ultrasound"),
        "updated_at": format_updated_at(item.get("updated_at")),
        "diagnosis": item.get("diagnosis", "-"),
        "recommended_action": item.get("recommended_action", "-"),
        "risk_order": status_rank(status),
    }


def states_to_rows(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [state_to_row(state) for state in states]
    return sorted(rows, key=lambda row: (row["risk_order"], row["severity_score"]), reverse=True)


def plant_kpis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counter = Counter(str(row["status_label"]).upper() for row in rows)
    health_values = [row["health_score"] for row in rows if row["health_score"] is not None]
    severity_values = [row["severity_score"] for row in rows if row["severity_score"] is not None]

    return {
        "total": len(rows),
        "normal": status_counter["NORMAL"],
        "attention": status_counter["ATENÇÃO"] + status_counter["ATENCAO"] + status_counter["ATENÇÃO ALTA"] + status_counter["ATENCAO ALTA"],
        "alert": status_counter["ALERTA"],
        "critical": status_counter["CRÍTICO"] + status_counter["CRITICO"],
        "offline": status_counter["SEM COMUNICAÇÃO"] + status_counter["SEM COMUNICACAO"],
        "health_mean": sum(health_values) / len(health_values) if health_values else None,
        "severity_max": max(severity_values) if severity_values else None,
    }


def filter_rows(
    rows: list[dict[str, Any]],
    *,
    status: str = "Todos",
    area: str = "Todas",
    asset_type: str = "Todos",
    criticality: str = "Todas",
) -> list[dict[str, Any]]:
    filtered = list(rows)

    if status != "Todos":
        filtered = [row for row in filtered if row["status_label"] == status]

    if area != "Todas":
        filtered = [row for row in filtered if row["area"] == area]

    if asset_type != "Todos":
        filtered = [row for row in filtered if row["asset_type"] == asset_type]

    if criticality != "Todas":
        filtered = [row for row in filtered if row["criticality"] == criticality]

    return filtered


def render_plant_kpis(rows: list[dict[str, Any]]) -> None:
    kpis = plant_kpis(rows)
    severity_max_display = "-" if kpis["severity_max"] is None else f"{kpis['severity_max']:.1f}"
    cols = st.columns(7)

    cols[0].metric("Ativos", kpis["total"])
    cols[1].metric("Normais", kpis["normal"])
    cols[2].metric("Atenção", kpis["attention"])
    cols[3].metric("Alertas", kpis["alert"])
    cols[4].metric("Críticos", kpis["critical"])
    cols[5].metric("Sem comunicação", kpis["offline"])
    cols[6].metric("Health médio", "-" if kpis["health_mean"] is None else f"{kpis['health_mean']:.1f}")
    st.caption(f"Maior Severity Score da planta: {severity_max_display}")


def render_filters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    st.subheader("Filtros da planta")
    c1, c2, c3, c4 = st.columns(4)
    statuses = sorted({row["status_label"] for row in rows if row["status_label"]})
    areas = sorted({row["area"] for row in rows if row["area"]})
    asset_types = sorted({row["asset_type"] for row in rows if row["asset_type"]})
    criticalities = sorted({row["criticality"] for row in rows if row["criticality"]})

    status = c1.selectbox("Status", ["Todos"] + statuses)
    area = c2.selectbox("Área", ["Todas"] + areas)
    asset_type = c3.selectbox("Tipo", ["Todos"] + asset_types)
    criticality = c4.selectbox("Criticidade", ["Todas"] + criticalities)

    return filter_rows(rows, status=status, area=area, asset_type=asset_type, criticality=criticality)


def render_risk_ranking(rows: list[dict[str, Any]]) -> str | None:
    st.subheader("Ranking de risco operacional")

    if not rows:
        st.info("Nenhum ativo encontrado para os filtros selecionados.")
        return None

    for index, row in enumerate(rows[:5], start=1):
        color = status_color(row["status_label"])
        health = "-" if row["health_score"] is None else f"{row['health_score']:.1f}"
        st.markdown(
            f"""
            <div style="border-left:6px solid {color};padding:10px 14px;margin-bottom:8px;border-radius:8px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.08);">
                <b>{index}º - {row["asset_name"]}</b><br>
                <span>{row["asset_type"]} | {row["area"]} | Criticidade: {row["criticality"]}</span><br>
                <span>Status: <b>{row["status_label"]}</b> | Health: <b>{health}</b> | Severity: <b>{row["severity_score"]:.1f}</b></span><br>
                <span>Modo: {row["mode"]}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    options = [f"{row['asset_id']} - {row['asset_name']}" for row in rows]
    selected = st.selectbox("Abrir detalhe do ativo", [""] + options)

    if not selected:
        return None

    return selected.split(" - ", 1)[0]


def render_status_summary(rows: list[dict[str, Any]]) -> None:
    st.subheader("Resumo por status")
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"ativos": 0, "health": [], "severity": []})

    for row in rows:
        group = grouped[str(row["status_label"])]
        group["ativos"] += 1

        if row["health_score"] is not None:
            group["health"].append(row["health_score"])

        if row["severity_score"] is not None:
            group["severity"].append(row["severity_score"])

    summary = []
    for status, group in sorted(grouped.items(), key=lambda item: status_rank(item[0]), reverse=True):
        health_values = group["health"]
        severity_values = group["severity"]
        summary.append(
            {
                "Status": status,
                "Ativos": group["ativos"],
                "Health médio": "-" if not health_values else round(sum(health_values) / len(health_values), 1),
                "Severity máximo": "-" if not severity_values else round(max(severity_values), 1),
            }
        )

    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_asset_cards(rows: list[dict[str, Any]]) -> str | None:
    st.subheader("Mapa visual dos ativos")
    selected = None
    cols_per_row = 3

    for row_start in range(0, len(rows), cols_per_row):
        cols = st.columns(cols_per_row)

        for col, row in zip(cols, rows[row_start : row_start + cols_per_row]):
            with col:
                color = status_color(row["status_label"])
                health = "-" if row["health_score"] is None else f"{row['health_score']:.1f}"
                st.markdown(
                    f"""
                    <div style="border:1px solid #E5E7EB;border-top:6px solid {color};border-radius:8px;padding:14px;background:#fff;min-height:170px;box-shadow:0 2px 8px rgba(0,0,0,.06);">
                        <div style="font-size:17px;font-weight:700;">{row["asset_name"]}</div>
                        <div style="font-size:13px;color:#6B7280;">{row["asset_type"]} | {row["area"]}</div>
                        <hr style="margin:10px 0;">
                        <div>Status: <b style="color:{color};">{row["status_label"]}</b></div>
                        <div>Health: <b>{health}</b></div>
                        <div>Severity: <b>{row["severity_score"]:.1f}</b></div>
                        <div style="font-size:13px;margin-top:6px;">{row["mode"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("Abrir detalhe", key=f"open_asset_{row['asset_id']}", use_container_width=True):
                    selected = row["asset_id"]

    return selected


def render_assets_table(rows: list[dict[str, Any]]) -> None:
    st.subheader("Tabela operacional multiativos")
    table_rows = [
        {
            "Ativo": row["asset_id"],
            "Nome": row["asset_name"],
            "Tipo": row["asset_type"],
            "Área": row["area"],
            "Criticidade": row["criticality"],
            "Status": row["status_label"],
            "Modo": row["mode"],
            "Health": row["health_score"],
            "Severity": row["severity_score"],
            "Vibração RMS": row["vibration_rms_mm_s"],
            "Temperatura": row["temperature_c"],
            "Ultrassom": row["ultrasound_db"],
            "Atualizado": row["updated_at"],
        }
        for row in rows
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)


def render_asset_priority_list(rows: list[dict[str, Any]]) -> str | None:
    st.subheader("Ativos por prioridade")

    if not rows:
        st.info("Nenhum ativo encontrado para os filtros selecionados.")
        return None

    selected = None

    for index, row in enumerate(rows, start=1):
        color = status_color(row["status_label"])
        health = "-" if row["health_score"] is None else f"{row['health_score']:.1f}"
        cols = st.columns([3.2, 1.1, 1.2])

        if cols[0].button(f"{index}º {row['asset_name']}", key=f"select_asset_{row['asset_id']}", use_container_width=True):
            selected = row["asset_id"]

        cols[1].markdown(
            f"<span style='color:{color};font-weight:700'>{row['status_label']}</span>",
            unsafe_allow_html=True,
        )
        cols[2].write(f"H {health} | S {row['severity_score']:.1f}")
        st.caption(
            f"{row['asset_type']} | {row['area']} | Criticidade: {row['criticality']} | "
            f"{row['mode']} | Atualizado: {row['updated_at']}"
        )

    return selected


def render_plant_overview(states: list[dict[str, Any]]) -> str | None:
    if st.session_state.get("dashboard_page") == "Sistema de Lubrificação":
        return None

    st.subheader("Parque Industrial - Visão Geral")
    rows = states_to_rows(states)

    if not rows:
        st.warning("Nenhum estado de ativo foi encontrado para esta planta.")
        return None

    render_plant_kpis(rows)
    st.divider()
    filtered_rows = render_filters(rows)
    st.divider()

    return render_asset_priority_list(filtered_rows)
