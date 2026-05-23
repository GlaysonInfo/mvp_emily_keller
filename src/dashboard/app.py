from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.dynamodb_repository import create_repository_from_env
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.dynamodb_repository import create_repository_from_env


st.set_page_config(
    page_title="MVP Monitoramento de Condicao",
    page_icon=":material/monitoring:",
    layout="wide",
)


def metric_value(metrics: dict[str, Any], name: str, default: str = "-") -> str:
    metric = metrics.get(name)

    if not metric:
        return default

    value = metric.get("value")
    unit = metric.get("unit", "")

    if isinstance(value, float):
        return f"{value:.2f} {unit}".strip()

    if value is None:
        return default

    return f"{value} {unit}".strip()


def severity_badge(severity: str) -> str:
    severity = severity.lower()

    if severity == "critical":
        return "CRITICAL"

    if severity == "warning":
        return "WARNING"

    if severity == "normal":
        return "NORMAL"

    return severity.upper() if severity else "UNKNOWN"


def render_metric_grid(metrics: dict[str, Any]) -> None:
    m1, m2, m3, m4 = st.columns(4)

    m1.metric("RPM", metric_value(metrics, "rpm"))
    m2.metric("Vibracao RMS", metric_value(metrics, "vibration_rms_mm_s"))
    m3.metric("Temperatura", metric_value(metrics, "temperature_c"))
    m4.metric("Ultrassom", metric_value(metrics, "ultrasound_db"))

    m5, m6, m7, m8 = st.columns(4)

    m5.metric("Kurtosis", metric_value(metrics, "kurtosis"))
    m6.metric("Crest Factor", metric_value(metrics, "crest_factor"))
    m7.metric("Pico Vibracao", metric_value(metrics, "vibration_peak_g"))
    m8.metric("Horimetro", metric_value(metrics, "horimeter_h"))


def render_alerts(active_alerts: list[dict[str, Any]]) -> None:
    st.subheader("Alertas ativos")

    if not active_alerts:
        st.success("Nenhum alerta ativo para este ativo.")
        return

    alerts_df = pd.DataFrame(
        [
            {
                "Tipo": alert.get("alert_type"),
                "Severidade": severity_badge(str(alert.get("severity", ""))),
                "Status": alert.get("status"),
                "Causa provavel": alert.get("probable_cause"),
                "Atualizado em": alert.get("updated_at"),
            }
            for alert in active_alerts
        ]
    )

    st.dataframe(alerts_df, use_container_width=True, hide_index=True)

    for alert in active_alerts:
        severity = severity_badge(str(alert.get("severity", "")))
        title = f"{severity} - {alert.get('probable_cause', 'Alerta ativo')}"

        with st.expander(title, expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("Tipo", alert.get("alert_type", "-"))
            c2.metric("Status", alert.get("status", "-"))
            c3.metric("Confianca", str(alert.get("confidence", "-")))

            st.write(f"Primeira deteccao: `{alert.get('first_detected_at', '-')}`")
            st.write(f"Ultima atualizacao: `{alert.get('updated_at', '-')}`")
            st.write(f"Modo simulado: `{alert.get('failure_mode_simulated', '-')}`")

            st.markdown("**Evidencias**")
            for evidence in alert.get("evidence", []):
                st.write(f"- {evidence}")

            st.markdown("**Acao recomendada**")
            st.info(alert.get("recommended_action", "-"))


def main() -> None:
    tenant_id = os.getenv("TENANT_ID", "cliente_demo")
    plant_id = os.getenv("PLANT_ID", "lab_virtual")
    asset_id = os.getenv("ASSET_ID", "motor_001")

    st.title("MVP Monitoramento de Condicao")
    st.caption("Bancada virtual OPC UA -> Bridge HTTPS -> AWS -> Diagnostico")

    with st.sidebar:
        st.header("Configuracao")
        st.write(f"Tenant: `{tenant_id}`")
        st.write(f"Planta: `{plant_id}`")
        st.write(f"Ativo: `{asset_id}`")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_seconds = st.number_input(
            "Intervalo de atualizacao em segundos",
            min_value=2,
            max_value=60,
            value=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5")),
        )

        if st.button("Atualizar agora", type="primary"):
            st.rerun()

    repo = create_repository_from_env()
    latest_state = repo.get_latest_state(tenant_id=tenant_id, asset_id=asset_id)
    active_alerts = repo.get_active_alerts(tenant_id=tenant_id, asset_id=asset_id)

    if not latest_state:
        st.warning("Nenhum estado atual encontrado no DynamoDB.")
        st.stop()

    metrics = latest_state.get("metrics", {})
    failure_mode = latest_state.get("failure_mode_simulated", "unknown")
    source = latest_state.get("source", "unknown")
    updated_at = latest_state.get("updated_at", "-")
    health_score = metrics.get("health_score", {}).get("value")
    severity_score = metrics.get("severity", {}).get("value")

    st.subheader("Estado atual do ativo")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Ativo", asset_id)
    col2.metric("Modo atual", failure_mode)
    col3.metric("Health Score", f"{health_score}" if health_score is not None else "-")
    col4.metric("Severity Score", f"{severity_score}" if severity_score is not None else "-")

    st.caption(f"Fonte: `{source}` | Atualizado em: `{updated_at}`")

    st.divider()
    st.subheader("Metricas atuais")
    render_metric_grid(metrics)

    st.divider()
    render_alerts(active_alerts)

    if auto_refresh:
        time.sleep(float(refresh_seconds))
        st.rerun()


if __name__ == "__main__":
    main()
