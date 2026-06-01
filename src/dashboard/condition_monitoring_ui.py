from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import streamlit as st

try:
    from dashboard.history_export import summary_rows
    from dashboard.plant_overview_ui import get_metric, plant_kpis, states_to_rows, status_color, status_rank
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.history_export import summary_rows
    from src.dashboard.plant_overview_ui import get_metric, plant_kpis, states_to_rows, status_color, status_rank


PAGE_NAME = "Monitoramento de Equipamentos"

OPERATOR_WORKFLOWS = [
    {
        "Fluxo": "Painel operacional",
        "Objetivo": "Ver rapidamente quais máquinas exigem atenção.",
        "Ações": "Abrir ativo, reconhecer evento, seguir ação recomendada.",
    },
    {
        "Fluxo": "Detalhe do ativo",
        "Objetivo": "Consultar vibração, temperatura, ultrassom, horímetro e status.",
        "Ações": "Comparar tendência, registrar atendimento, acionar manutenção.",
    },
    {
        "Fluxo": "Alertas e eventos",
        "Objetivo": "Priorizar ocorrências por severidade e criticidade.",
        "Ações": "Atualizar status, informar responsável e acompanhar escalonamento.",
    },
]

TECHNICIAN_WORKFLOWS = [
    {
        "Fluxo": "Configuração técnica",
        "Objetivo": "Cadastrar ativos, fontes de dados, sensores e mapeamento de sinais.",
        "Ações": "Validar tags, protocolos, métricas e vínculos por planta.",
    },
    {
        "Fluxo": "Regras e diagnóstico",
        "Objetivo": "Ajustar thresholds, severidade, evidências e recomendações.",
        "Ações": "Revisar parâmetros, testar eventos e calibrar diagnósticos.",
    },
    {
        "Fluxo": "Inteligência operacional",
        "Objetivo": "Analisar histórico, hipóteses, tendências e correlação com lubrificação.",
        "Ações": "Gerar recomendação técnica e plano de intervenção.",
    },
]


def _asset_rows(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for asset in assets:
        rows.append(
            {
                "Ativo": str(asset.get("asset_id") or "-"),
                "Nome": str(asset.get("asset_name") or asset.get("name") or "-"),
                "Tipo": str(asset.get("asset_type") or asset.get("type") or "-"),
                "Criticidade": str(asset.get("criticality") or "-"),
                "Status": str(asset.get("status") or "Ativo"),
            }
        )
    return rows


def _rows_from_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in assets:
        rows.append(
            {
                "asset_id": str(asset.get("asset_id") or "-"),
                "asset_name": str(asset.get("asset_name") or asset.get("name") or asset.get("asset_id") or "-"),
                "asset_type": str(asset.get("asset_type") or asset.get("type") or "-"),
                "area": str(asset.get("area") or "-"),
                "criticality": str(asset.get("criticality") or "-"),
                "mode": "-",
                "status_label": str(asset.get("status_label") or asset.get("status") or "NORMAL"),
                "health_score": get_metric(asset, "health_score"),
                "severity_score": get_metric(asset, "severity_score", "severity") or 0.0,
                "rpm": get_metric(asset, "rpm"),
                "vibration_rms_mm_s": get_metric(asset, "vibration_rms_mm_s", "vibration_rms"),
                "temperature_c": get_metric(asset, "temperature_c", "temperature"),
                "ultrasound_db": get_metric(asset, "ultrasound_db", "ultrasound"),
                "updated_at": str(asset.get("updated_at") or "-"),
                "diagnosis": str(asset.get("diagnosis") or "-"),
                "recommended_action": str(asset.get("recommended_action") or "Manter monitoramento de rotina."),
                "risk_order": status_rank(asset.get("status_label") or asset.get("status") or "NORMAL"),
            }
        )
    return sorted(rows, key=lambda row: (row["risk_order"], row["severity_score"]), reverse=True)


def operator_rows(current_states: list[dict[str, Any]] | None, assets: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    states = current_states or []
    if states:
        return states_to_rows(states)
    return _rows_from_assets(assets or [])


def operator_kpis(rows: list[dict[str, Any]], active_alerts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    kpis = plant_kpis(rows)
    kpis["alerts_active"] = len(active_alerts or active_operator_alerts(rows, []))
    kpis["field_queue"] = sum(1 for row in rows if status_rank(row.get("status_label")) >= 2)
    return kpis


def active_operator_alerts(rows: list[dict[str, Any]], active_alerts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    alerts = list(active_alerts or [])
    if alerts:
        return alerts

    generated: list[dict[str, Any]] = []
    for row in rows:
        if status_rank(row.get("status_label")) < 2:
            continue
        generated.append(
            {
                "tenant_asset": "",
                "alert_key": "",
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "status_label": row["status_label"],
                "metric": "condition_state",
                "value": row.get("severity_score"),
                "threshold": None,
                "recommended_action": row["recommended_action"],
                "updated_at": row["updated_at"],
                "source": "current_state",
            }
        )
    return generated


def alert_tenant_asset(alert: dict[str, Any], tenant_id: str | None = None) -> str:
    if alert.get("tenant_asset"):
        return str(alert["tenant_asset"])
    asset_id = str(alert.get("asset_id") or "")
    return f"{tenant_id}#{asset_id}" if tenant_id and asset_id else ""


def alert_key(alert: dict[str, Any]) -> str:
    return str(alert.get("alert_key") or alert.get("sk") or "")


def alert_is_persisted(alert: dict[str, Any]) -> bool:
    return bool(alert_tenant_asset(alert) and alert_key(alert))


def alert_option_label(alert: dict[str, Any], index: int) -> str:
    asset = alert.get("asset_name") or alert.get("asset_id") or "-"
    metric = alert.get("metric") or alert.get("alert_type") or "evento"
    status = alert.get("status_label") or alert.get("severity") or "-"
    treatment = alert.get("status") or ("derivado" if not alert_is_persisted(alert) else "open")
    return f"{index}. {asset} | {metric} | {status} | {treatment}"


def persist_or_update_quick_alert(
    *,
    repo: Any,
    alert: dict[str, Any],
    tenant_id: str,
    plant_id: str,
    new_status: str,
    user_name: str,
    note: str,
    action_taken: str,
) -> dict[str, Any]:
    tenant_asset = alert_tenant_asset(alert, tenant_id)
    key = alert_key(alert)
    pk = str(alert["pk"]) if alert.get("pk") else None
    sk = str(alert["sk"]) if alert.get("sk") else None

    if tenant_asset and key:
        return repo.update_status(
            tenant_asset,
            key,
            new_status,
            user_name,
            note,
            action_taken,
            pk=pk,
            sk=sk,
        )

    created = repo.create_manual_alert(
        tenant_id,
        plant_id,
        str(alert.get("asset_id") or ""),
        str(alert.get("asset_name") or alert.get("asset_id") or ""),
        str(alert.get("metric") or alert.get("alert_type") or "condition_state"),
        str(alert.get("status_label") or "ATENÇÃO"),
        alert.get("value"),
        alert.get("threshold"),
        str(alert.get("recommended_action") or next_operator_action(alert)),
        created_by=user_name,
        note=note,
    )
    return repo.update_status(
        str(created["tenant_asset"]),
        str(created["alert_key"]),
        new_status,
        user_name,
        note,
        action_taken,
        pk=str(created["pk"]) if created.get("pk") else None,
        sk=str(created["sk"]) if created.get("sk") else None,
    )


def next_operator_action(row: dict[str, Any]) -> str:
    status = str(row.get("status_label") or "").upper()
    recommended = str(row.get("recommended_action") or "").strip()
    if "CR" in status:
        return recommended or "Parar e acionar manutenção conforme procedimento da planta."
    if "ALERTA" in status or "ATEN" in status:
        return recommended or "Inspecionar o ativo e registrar a ocorrência."
    if "COMUNICA" in status:
        return "Verificar gateway, sensor, alimentação e última comunicação."
    return recommended or "Manter monitoramento de rotina."


def technical_diagnostic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for row in rows:
        diagnostics.append(
            {
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "area": row["area"],
                "asset_type": row["asset_type"],
                "criticality": row["criticality"],
                "status_label": row["status_label"],
                "mode": row["mode"],
                "health_score": row["health_score"],
                "severity_score": row["severity_score"],
                "dominant_metric": dominant_metric(row),
                "diagnosis": row["diagnosis"],
                "recommended_action": row["recommended_action"],
                "risk_order": row["risk_order"],
            }
        )
    return sorted(diagnostics, key=lambda item: (item["risk_order"], item["severity_score"]), reverse=True)


def dominant_metric(row: dict[str, Any]) -> str:
    candidates = [
        ("Vibração", row.get("vibration_rms_mm_s"), 4.5),
        ("Temperatura", row.get("temperature_c"), 75.0),
        ("Ultrassom", row.get("ultrasound_db"), 45.0),
    ]
    scored: list[tuple[float, str]] = []
    for label, value, reference in candidates:
        if isinstance(value, (int, float)) and reference > 0:
            scored.append((float(value) / reference, label))
    if scored:
        return max(scored)[1]
    return "Severity" if isinstance(row.get("severity_score"), (int, float)) else "-"


def technical_summary(rows: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = technical_diagnostic_rows(rows)
    top = diagnostics[0] if diagnostics else None
    health_values = [row["health_score"] for row in rows if row.get("health_score") is not None]
    return {
        "assets": len(rows),
        "diagnostic_queue": sum(1 for row in diagnostics if status_rank(row.get("status_label")) >= 2),
        "active_alerts": len(alerts),
        "max_severity": max([float(row.get("severity_score") or 0) for row in rows], default=0.0),
        "health_mean": sum(health_values) / len(health_values) if health_values else None,
        "top_asset_id": top["asset_id"] if top else None,
        "top_asset_name": top["asset_name"] if top else "-",
        "top_dominant_metric": top["dominant_metric"] if top else "-",
    }


def alerts_for_asset(alerts: list[dict[str, Any]], asset_id: str | None) -> list[dict[str, Any]]:
    if not asset_id:
        return []
    return [alert for alert in alerts if str(alert.get("asset_id") or "") == str(asset_id)]


def technical_trend_summary(history_items: list[dict[str, Any]], current_row: dict[str, Any] | None) -> dict[str, Any]:
    if not history_items:
        return {
            "has_history": False,
            "samples": 0,
            "severity_delta": None,
            "health_delta": None,
            "trend_label": "Histórico indisponível",
            "summary_rows": [],
        }

    ordered = sorted(history_items, key=lambda item: str(item.get("ts_utc_minute") or item.get("updated_at") or ""))
    first = ordered[0]
    last = ordered[-1]

    current = current_row or {}
    first_severity = get_metric(first, "severity_score", "severity")
    last_severity = get_metric(current, "severity_score", "severity") if current else get_metric(last, "severity_score", "severity")
    first_health = get_metric(first, "health_score")
    last_health = get_metric(current, "health_score") if current else get_metric(last, "health_score")
    severity_delta = None if first_severity is None or last_severity is None else round(last_severity - first_severity, 2)
    health_delta = None if first_health is None or last_health is None else round(last_health - first_health, 2)

    if severity_delta is None:
        trend_label = "Tendência sem métrica suficiente"
    elif severity_delta >= 10:
        trend_label = "Piora relevante"
    elif severity_delta <= -10:
        trend_label = "Melhora relevante"
    elif abs(severity_delta) >= 3:
        trend_label = "Variação moderada"
    else:
        trend_label = "Estável"

    return {
        "has_history": True,
        "samples": len(ordered),
        "severity_delta": severity_delta,
        "health_delta": health_delta,
        "trend_label": trend_label,
        "summary_rows": summary_rows(ordered, window_hours=24),
    }


def technical_evidence_rows(
    *,
    row: dict[str, Any] | None,
    alerts: list[dict[str, Any]],
    trend: dict[str, Any],
) -> list[dict[str, Any]]:
    if row is None:
        return []

    correlated_alerts = alerts_for_asset(alerts, str(row.get("asset_id")))
    return [
        {"Evidência": "Ativo", "Valor": row.get("asset_name", "-")},
        {"Evidência": "Status atual", "Valor": row.get("status_label", "-")},
        {"Evidência": "Métrica dominante", "Valor": dominant_metric(row)},
        {"Evidência": "Vibração RMS", "Valor": _metric_display(row.get("vibration_rms_mm_s"), " mm/s")},
        {"Evidência": "Temperatura", "Valor": _metric_display(row.get("temperature_c"), " °C")},
        {"Evidência": "Ultrassom", "Valor": _metric_display(row.get("ultrasound_db"), " dB")},
        {"Evidência": "Health", "Valor": _metric_display(row.get("health_score"))},
        {"Evidência": "Severity", "Valor": _metric_display(row.get("severity_score"))},
        {"Evidência": "Tendência", "Valor": trend.get("trend_label", "-")},
        {"Evidência": "Delta Severity", "Valor": _metric_display(trend.get("severity_delta"))},
        {"Evidência": "Delta Health", "Valor": _metric_display(trend.get("health_delta"))},
        {"Evidência": "Eventos correlacionados", "Valor": len(correlated_alerts)},
        {"Evidência": "Diagnóstico", "Valor": row.get("diagnosis", "-")},
        {"Evidência": "Recomendação técnica", "Valor": row.get("recommended_action", "-")},
    ]


def _metric_display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _render_operator_kpis(rows: list[dict[str, Any]], active_alerts: list[dict[str, Any]]) -> None:
    kpis = operator_kpis(rows, active_alerts)
    cols = st.columns(5)
    cols[0].metric("Ativos", kpis["total"])
    cols[1].metric("Fila de campo", kpis["field_queue"])
    cols[2].metric("Alertas ativos", kpis["alerts_active"])
    cols[3].metric("Críticos", kpis["critical"])
    cols[4].metric("Health médio", "-" if kpis["health_mean"] is None else f"{kpis['health_mean']:.1f}")


def _render_priority_cards(rows: list[dict[str, Any]]) -> None:
    st.subheader("Prioridade de campo")
    if not rows:
        st.info("Nenhum ativo encontrado para esta planta.")
        return

    for index, row in enumerate(rows[:4], start=1):
        color = status_color(row["status_label"])
        st.markdown(
            f"""
            <div style="border-left:6px solid {color};padding:10px 14px;margin-bottom:8px;border-radius:8px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.08);">
                <b>{index}. {row["asset_name"]}</b><br>
                <span>{row["asset_type"]} | {row["area"]} | Criticidade: {row["criticality"]}</span><br>
                <span>Status: <b style="color:{color};">{row["status_label"]}</b> | Health: <b>{_metric_display(row["health_score"])}</b> | Severity: <b>{_metric_display(row["severity_score"])}</b></span><br>
                <span>{next_operator_action(row)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _selected_asset_id(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    options = [f"{row['asset_id']} - {row['asset_name']}" for row in rows]
    selected = st.selectbox("Ativo para ação", options, key="condition_operator_asset")
    return selected.split(" - ", 1)[0]


def _find_row(rows: list[dict[str, Any]], asset_id: str | None) -> dict[str, Any] | None:
    for row in rows:
        if row["asset_id"] == asset_id:
            return row
    return rows[0] if rows else None


def _render_asset_action_panel(rows: list[dict[str, Any]]) -> dict[str, str] | None:
    st.subheader("Ação do operador")
    selected_asset_id = _selected_asset_id(rows)
    row = _find_row(rows, selected_asset_id)
    if row is None:
        st.info("Nenhum ativo disponível para ação.")
        return None

    color = status_color(row["status_label"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", row["status_label"])
    c2.metric("Vibração", _metric_display(row["vibration_rms_mm_s"], " mm/s"))
    c3.metric("Temperatura", _metric_display(row["temperature_c"], " °C"))
    c4.metric("Ultrassom", _metric_display(row["ultrasound_db"], " dB"))
    st.markdown(f"<b style='color:{color};'>Próximo passo:</b> {next_operator_action(row)}", unsafe_allow_html=True)
    st.caption(f"Diagnóstico: {row['diagnosis']} | Atualizado: {row['updated_at']}")

    b1, b2, b3 = st.columns(3)
    if b1.button("Abrir ativo", type="primary", use_container_width=True):
        return {"route": "Detalhe do Ativo", "asset_id": str(row["asset_id"])}
    if b2.button("Ver alertas", use_container_width=True):
        return {"route": "Alertas e Eventos", "asset_id": str(row["asset_id"])}
    if b3.button("Registrar evento", use_container_width=True):
        return {"route": "Alertas e Eventos", "asset_id": str(row["asset_id"])}
    return None


def _render_alert_queue(alerts: list[dict[str, Any]]) -> None:
    st.subheader("Alertas e eventos em aberto")
    if not alerts:
        st.success("Nenhum alerta ativo para os ativos monitorados.")
        return

    rows = []
    for alert in alerts:
        rows.append(
            {
                "Ativo": alert.get("asset_name") or alert.get("asset_id") or "-",
                "Status": alert.get("status_label") or alert.get("severity") or "-",
                "Métrica": alert.get("metric") or alert.get("alert_type") or "-",
                "Ação recomendada": alert.get("recommended_action") or "-",
                "Atualizado": alert.get("updated_at") or alert.get("last_detected_at") or "-",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_quick_alert_treatment(
    *,
    alerts: list[dict[str, Any]],
    repo: Any | None,
    tenant_id: str,
    plant_id: str,
    operator_name: str,
) -> None:
    st.subheader("Tratamento rápido do alerta")
    if not alerts:
        st.success("Sem alerta para reconhecer ou comentar.")
        return
    if repo is None:
        st.info("Tratamento rápido indisponível nesta sessão. Use a Central de Alertas.")
        return

    options = list(enumerate(alerts, start=1))
    selected = st.selectbox(
        "Alerta",
        options,
        format_func=lambda item: alert_option_label(item[1], item[0]),
        key="condition_quick_alert",
    )
    alert = selected[1]
    st.caption(str(alert.get("recommended_action") or "Sem ação recomendada registrada."))

    with st.form("condition_quick_alert_treatment"):
        status = st.selectbox(
            "Tratamento",
            ["acknowledged", "in_progress"],
            format_func=lambda value: {"acknowledged": "Reconhecer ciência", "in_progress": "Registrar atendimento"}[value],
        )
        user = st.text_input("Responsável", value=operator_name or "operador_demo")
        note = st.text_area("Observação")
        action_taken = st.text_area(
            "Ação tomada",
            value="Ciência operacional registrada." if status == "acknowledged" else "",
        )
        submitted = st.form_submit_button("Salvar tratamento", type="primary", use_container_width=True)

    if not submitted:
        return

    if not note.strip() and status == "in_progress":
        st.error("Informe uma observação para registrar o atendimento.")
        return

    persist_or_update_quick_alert(
        repo=repo,
        alert=alert,
        tenant_id=tenant_id,
        plant_id=plant_id,
        new_status=status,
        user_name=user or operator_name or "operador_demo",
        note=note,
        action_taken=action_taken,
    )
    st.success("Tratamento registrado.")
    st.rerun()


def _render_technical_kpis(rows: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> None:
    summary = technical_summary(rows, alerts)
    cols = st.columns(5)
    cols[0].metric("Ativos", summary["assets"])
    cols[1].metric("Fila técnica", summary["diagnostic_queue"])
    cols[2].metric("Alertas ativos", summary["active_alerts"])
    cols[3].metric("Severity máximo", f"{summary['max_severity']:.1f}")
    cols[4].metric("Health médio", "-" if summary["health_mean"] is None else f"{summary['health_mean']:.1f}")
    st.caption(
        f"Principal hipótese técnica: {summary['top_asset_name']} | Métrica dominante: {summary['top_dominant_metric']}"
    )


def _render_technical_ranking(rows: list[dict[str, Any]]) -> str | None:
    st.subheader("Ranking técnico de diagnóstico")
    diagnostics = technical_diagnostic_rows(rows)
    if not diagnostics:
        st.info("Nenhum ativo disponível para diagnóstico técnico.")
        return None

    table_rows = [
        {
            "Ativo": row["asset_name"],
            "Área": row["area"],
            "Status": row["status_label"],
            "Modo": row["mode"],
            "Métrica dominante": row["dominant_metric"],
            "Health": row["health_score"],
            "Severity": row["severity_score"],
            "Diagnóstico": row["diagnosis"],
            "Ação recomendada": row["recommended_action"],
        }
        for row in diagnostics
    ]
    st.dataframe(table_rows, width="stretch", hide_index=True)

    options = [f"{row['asset_id']} - {row['asset_name']}" for row in diagnostics]
    selected = st.selectbox("Ativo para análise técnica", options, key="condition_technical_asset")
    return selected.split(" - ", 1)[0]


def _render_technical_asset_detail(rows: list[dict[str, Any]], selected_asset_id: str | None) -> dict[str, str] | None:
    row = _find_row(rows, selected_asset_id)
    if row is None:
        return None

    st.subheader("Leitura técnica do ativo")
    color = status_color(row["status_label"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", row["status_label"])
    c2.metric("RPM", _metric_display(row["rpm"]))
    c3.metric("Vibração", _metric_display(row["vibration_rms_mm_s"], " mm/s"))
    c4.metric("Temperatura", _metric_display(row["temperature_c"], " °C"))

    c5, c6, c7 = st.columns(3)
    c5.metric("Ultrassom", _metric_display(row["ultrasound_db"], " dB"))
    c6.metric("Health", _metric_display(row["health_score"]))
    c7.metric("Severity", _metric_display(row["severity_score"]))

    st.markdown(f"<b style='color:{color};'>Hipótese:</b> {row['diagnosis']}", unsafe_allow_html=True)
    st.markdown(f"**Recomendação técnica:** {row['recommended_action']}")
    st.caption(f"Modo: {row['mode']} | Área: {row['area']} | Criticidade: {row['criticality']} | Atualizado: {row['updated_at']}")

    b1, b2, b3 = st.columns(3)
    if b1.button("Abrir detalhe técnico", type="primary", use_container_width=True):
        return {"route": "Detalhe do Ativo", "asset_id": str(row["asset_id"])}
    if b2.button("Analisar inteligência", use_container_width=True):
        return {"route": "Inteligência Operacional", "asset_id": str(row["asset_id"])}
    if b3.button("Gerar relatório", use_container_width=True):
        return {"route": "Relatórios", "asset_id": str(row["asset_id"])}
    return None


def _query_history_for_asset(
    *,
    history_repo: Any | None,
    tenant_id: str,
    asset_id: str | None,
    hours: int,
) -> list[dict[str, Any]]:
    if history_repo is None or not asset_id:
        return []
    end_utc = datetime.now(UTC)
    start_utc = end_utc - timedelta(hours=hours)
    return history_repo.query_history(tenant_id=tenant_id, asset_id=asset_id, start_utc=start_utc, end_utc=end_utc)


def _render_technical_history_and_evidence(
    *,
    row: dict[str, Any] | None,
    alerts: list[dict[str, Any]],
    history_repo: Any | None,
    tenant_id: str,
) -> None:
    st.subheader("Histórico, tendência e evidências")
    if row is None:
        st.info("Selecione um ativo para montar tendência e evidências.")
        return

    hours = int(st.selectbox("Janela histórica", [6, 24, 72, 168], index=1, format_func=lambda value: f"{value} h"))
    try:
        history_items = _query_history_for_asset(
            history_repo=history_repo,
            tenant_id=tenant_id,
            asset_id=str(row.get("asset_id")),
            hours=hours,
        )
    except Exception:
        history_items = []
        st.warning("Histórico indisponível para este ativo no momento.")

    trend = technical_trend_summary(history_items, row)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Amostras", trend["samples"])
    c2.metric("Tendência", trend["trend_label"])
    c3.metric("Delta Severity", _metric_display(trend["severity_delta"]))
    c4.metric("Delta Health", _metric_display(trend["health_delta"]))

    if trend["summary_rows"]:
        st.dataframe(trend["summary_rows"], width="stretch", hide_index=True)
    else:
        st.info("Sem histórico suficiente para montar tendência nesta janela.")

    evidence = technical_evidence_rows(row=row, alerts=alerts, trend=trend)
    st.markdown("#### Evidências para relatório")
    st.dataframe(evidence, width="stretch", hide_index=True)
    st.download_button(
        "Baixar evidências TXT",
        "\n".join(f"{item['Evidência']}: {item['Valor']}" for item in evidence).encode("utf-8"),
        file_name=f"evidencias_{row.get('asset_id', 'ativo')}.txt",
        mime="text/plain",
        use_container_width=True,
    )


def _render_technical_alert_context(alerts: list[dict[str, Any]], selected_asset_id: str | None = None) -> None:
    st.subheader("Eventos correlacionados")
    scoped_alerts = alerts_for_asset(alerts, selected_asset_id) if selected_asset_id else alerts
    if not scoped_alerts:
        st.success("Nenhum alerta ativo correlacionado ao ativo selecionado.")
        return

    rows = [
        {
            "Ativo": alert.get("asset_name") or alert.get("asset_id") or "-",
            "Status": alert.get("status_label") or alert.get("severity") or "-",
            "Métrica": alert.get("metric") or alert.get("alert_type") or "-",
            "Tratamento": alert.get("status") or "derivado",
            "Ação recomendada": alert.get("recommended_action") or "-",
            "Última atualização": alert.get("updated_at") or alert.get("last_detected_at") or "-",
        }
        for alert in scoped_alerts
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_technician_view(
    *,
    rows: list[dict[str, Any]],
    active_alerts: list[dict[str, Any]],
    tenant_id: str,
    history_repo: Any | None,
) -> dict[str, str] | None:
    _render_technical_kpis(rows, active_alerts)
    st.divider()
    selected_asset_id = _render_technical_ranking(rows)
    selected_row = _find_row(rows, selected_asset_id)
    st.divider()
    action = _render_technical_asset_detail(rows, selected_asset_id)
    st.divider()
    _render_technical_history_and_evidence(
        row=selected_row,
        alerts=active_alerts,
        history_repo=history_repo,
        tenant_id=tenant_id,
    )
    st.divider()
    _render_technical_alert_context(active_alerts, selected_asset_id)
    return action


def _render_operator_view(
    *,
    rows: list[dict[str, Any]],
    active_alerts: list[dict[str, Any]],
    tenant_id: str,
    plant_id: str,
    alerts_repo: Any | None,
    operator_name: str,
) -> dict[str, str] | None:
    _render_operator_kpis(rows, active_alerts)
    st.divider()

    c1, c2 = st.columns([1.15, 1])
    with c1:
        _render_priority_cards(rows)
    with c2:
        action = _render_asset_action_panel(rows)

    st.divider()
    _render_alert_queue(active_alerts)
    _render_quick_alert_treatment(
        alerts=active_alerts,
        repo=alerts_repo,
        tenant_id=tenant_id,
        plant_id=plant_id,
        operator_name=operator_name,
    )
    return action


def _render_assets_view(rows: list[dict[str, Any]], assets: list[dict[str, Any]]) -> None:
    st.subheader("Ativos do serviço")
    if rows:
        table_rows = [
            {
                "Ativo": row["asset_id"],
                "Nome": row["asset_name"],
                "Área": row["area"],
                "Tipo": row["asset_type"],
                "Criticidade": row["criticality"],
                "Status": row["status_label"],
                "Health": row["health_score"],
                "Severity": row["severity_score"],
                "Ação recomendada": next_operator_action(row),
            }
            for row in rows
        ]
        st.dataframe(table_rows, width="stretch", hide_index=True)
        return

    asset_rows = _asset_rows(assets)
    if asset_rows:
        st.dataframe(asset_rows, width="stretch", hide_index=True)
    else:
        st.warning("Nenhum ativo cadastrado para esta planta no modo local.")


def render_condition_monitoring_page(
    *,
    mode: str,
    tenant_id: str,
    plant_id: str,
    assets: list[dict[str, Any]] | None = None,
    current_states: list[dict[str, Any]] | None = None,
    active_alerts: list[dict[str, Any]] | None = None,
    alerts_repo: Any | None = None,
    history_repo: Any | None = None,
    operator_name: str = "operador_demo",
) -> dict[str, str] | None:
    assets = assets or []
    rows = operator_rows(current_states, assets)
    alerts = active_operator_alerts(rows, active_alerts)

    st.header("Monitoramento de Equipamentos e Máquinas")
    st.caption("Entrada operacional do serviço de condição: priorizar, abrir ativo e tratar eventos de campo.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cliente", tenant_id)
    c2.metric("Planta", plant_id)
    c3.metric("Ativos monitorados", str(len(rows)))
    c4.metric("Modo atual", "Técnico" if mode == "technical" else "Operador")

    if mode == "operator":
        return _render_operator_view(
            rows=rows,
            active_alerts=alerts,
            tenant_id=tenant_id,
            plant_id=plant_id,
            alerts_repo=alerts_repo,
            operator_name=operator_name,
        )

    action = None
    if mode == "technical":
        tab_technical, tab_operation, tab_assets = st.tabs(["Técnico", "Operação", "Ativos"])
        with tab_technical:
            action = _render_technician_view(
                rows=rows,
                active_alerts=alerts,
                tenant_id=tenant_id,
                history_repo=history_repo,
            )
        with tab_operation:
            operator_action = _render_operator_view(
                rows=rows,
                active_alerts=alerts,
                tenant_id=tenant_id,
                plant_id=plant_id,
                alerts_repo=alerts_repo,
                operator_name=operator_name,
            )
            action = action or operator_action
        with tab_assets:
            _render_assets_view(rows, assets)
        return action

    tab_operation, tab_technical, tab_assets = st.tabs(["Operação", "Técnico", "Ativos"])
    with tab_operation:
        action = _render_operator_view(
            rows=rows,
            active_alerts=alerts,
            tenant_id=tenant_id,
            plant_id=plant_id,
            alerts_repo=alerts_repo,
            operator_name=operator_name,
        )
    with tab_technical:
        technical_action = _render_technician_view(
            rows=rows,
            active_alerts=alerts,
            tenant_id=tenant_id,
            history_repo=history_repo,
        )
        action = action or technical_action
    with tab_assets:
        _render_assets_view(rows, assets)
    return action
