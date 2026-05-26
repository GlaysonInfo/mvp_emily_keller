from __future__ import annotations

import pandas as pd
import streamlit as st

from .lubrication_config import load_lubrication_config
from .lubrication_engine import evaluate_lubrication_cycle
from .lubrication_labels import outlet_label, status_label
from .lubrication_repository import LubricationRepository


OUTLET_IDS = ("saida_graxa_01", "saida_graxa_02", "saida_graxa_03", "saida_graxa_04")


def _pretty_text(value: object) -> str:
    text = str(value or "")
    for outlet_id in OUTLET_IDS:
        text = text.replace(outlet_id, outlet_label(outlet_id))
    return text


def outlets_df(state_or_cycle: dict) -> pd.DataFrame:
    rows = []
    for outlet in state_or_cycle.get("outlets", []):
        rows.append(
            {
                "Saída": outlet_label(outlet.get("outlet_id")),
                "Pressão atual (bar)": outlet.get("pressure_bar"),
                "Pico do ciclo (bar)": outlet.get("peak_pressure_bar"),
                "Subida (s)": outlet.get("rise_time_sec"),
                "Alívio (s)": outlet.get("decay_time_sec"),
                "Pulso": "Sim" if outlet.get("pulse_detected") else "Não",
                "Status": status_label(outlet.get("status")),
                "Severidade": outlet.get("severity"),
                "Score": outlet.get("anomaly_score"),
            }
        )
    return pd.DataFrame(rows)


def alerts_df(alerts: list[dict]) -> pd.DataFrame:
    rows = []
    for alert in alerts:
        rows.append(
            {
                "Saída": outlet_label(alert.get("outlet_id", "")),
                "Severidade": alert.get("status_label"),
                "Descrição": _pretty_text(alert.get("description")),
                "Valor": alert.get("value"),
                "Ação recomendada": alert.get("recommended_action"),
                "Status": alert.get("status"),
            }
        )
    return pd.DataFrame(rows)


def cycles_df(cycles: list[dict]) -> pd.DataFrame:
    rows = []
    for cycle in cycles:
        rows.append(
            {
                "Data/Hora": cycle.get("cycle_timestamp"),
                "Ciclo": cycle.get("cycle_id"),
                "Status": cycle.get("status_label"),
                "Saídas": cycle.get("outlet_count"),
                "Normais": cycle.get("normal_count"),
                "Atenção": cycle.get("attention_count"),
                "Alertas": cycle.get("alert_count"),
                "Críticos": cycle.get("critical_count"),
                "Maior pressão (bar)": cycle.get("max_pressure_bar"),
                "Maior score": cycle.get("max_anomaly_score"),
            }
        )
    return pd.DataFrame(rows)


def sample_payload_from_config(config: dict) -> dict:
    return {
        "tenant_id": config.get("tenant_id"),
        "plant_id": config.get("plant_id"),
        "asset_id": config.get("asset_id"),
        "source_id": config.get("source_id"),
        "timestamp_utc": "2026-05-25T23:30:00Z",
        "cycle_id": "cycle_demo_dashboard",
        "metrics": {
            "pressure_saida_graxa_01_bar": 84.2,
            "pressure_saida_graxa_02_bar": 91.7,
            "pressure_saida_graxa_03_bar": 7.8,
            "pressure_saida_graxa_04_bar": 146.5,
            "peak_saida_graxa_01_bar": 102.3,
            "peak_saida_graxa_02_bar": 108.1,
            "peak_saida_graxa_03_bar": 9.2,
            "peak_saida_graxa_04_bar": 181.2,
            "min_saida_graxa_01_bar": 2.0,
            "min_saida_graxa_02_bar": 2.0,
            "min_saida_graxa_03_bar": 0.0,
            "min_saida_graxa_04_bar": 4.0,
            "rise_time_saida_graxa_01_sec": 3.2,
            "rise_time_saida_graxa_02_sec": 3.5,
            "rise_time_saida_graxa_03_sec": 8.9,
            "rise_time_saida_graxa_04_sec": 2.1,
            "decay_time_saida_graxa_01_sec": 4.8,
            "decay_time_saida_graxa_02_sec": 5.1,
            "decay_time_saida_graxa_03_sec": 2.4,
            "decay_time_saida_graxa_04_sec": 18.6,
        },
    }


def render_lubrication_page(config_path: str = "config/lubrication_pilot_config.json") -> None:
    st.header("Sistema de Lubrificação")
    st.caption("Monitoramento inteligente de pressão por saída de graxa.")

    config = load_lubrication_config(config_path)
    repo = LubricationRepository()

    tenant_id = config.get("tenant_id")
    asset_id = config.get("asset_id")

    col_asset, col_outlets, col_sensor, col_source = st.columns(4)
    col_asset.metric("Ativo", config.get("asset_name", asset_id))
    col_outlets.metric("Saídas monitoradas", len(config.get("outlets", [])))
    col_sensor.metric("Sensor sugerido", f"0-{config.get('sensor_range_bar', 250)} bar")
    col_source.metric("Fonte", config.get("source_id"))

    state = repo.get_state(tenant_id, asset_id)
    cycles = repo.list_cycles(tenant_id, asset_id, limit=30)
    alerts = repo.list_alerts(tenant_id, asset_id)

    if not state:
        st.warning("Ainda não há ciclo salvo para este sistema de lubrificação.")
        if st.button("Gerar ciclo demonstrativo", type="primary", use_container_width=True):
            result = evaluate_lubrication_cycle(sample_payload_from_config(config), config)
            repo.save_cycle_result(result)
            st.success("Ciclo demonstrativo salvo.")
            st.rerun()
        return

    kpi_status, kpi_normal, kpi_attention, kpi_alert, kpi_critical = st.columns(5)
    kpi_status.metric("Status geral", state.get("status_label", "-"))
    kpi_normal.metric("Normais", state.get("normal_count", 0))
    kpi_attention.metric("Atenção", state.get("attention_count", 0))
    kpi_alert.metric("Alertas", state.get("alert_count", 0))
    kpi_critical.metric("Críticos", state.get("critical_count", 0))

    tab_overview, tab_pressure, tab_cycles, tab_alerts, tab_ai = st.tabs(
        ["Visão Geral", "Pressão por Saída", "Últimos Ciclos", "Alertas Ativos", "Recomendação da IA"]
    )

    with tab_overview:
        st.subheader("Ciclo atual")
        st.dataframe(outlets_df(state), use_container_width=True, hide_index=True)
        if st.button("Gerar novo ciclo demonstrativo", use_container_width=True):
            result = evaluate_lubrication_cycle(sample_payload_from_config(config), config)
            repo.save_cycle_result(result)
            st.success("Novo ciclo demonstrativo salvo.")
            st.rerun()

    with tab_pressure:
        df = outlets_df(state)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Exportar pressão por saída CSV",
            df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
            "pressao_por_saida.csv",
            "text/csv",
            use_container_width=True,
        )

    with tab_cycles:
        df_cycles = cycles_df(cycles)
        if df_cycles.empty:
            st.info("Nenhum ciclo histórico encontrado.")
        else:
            st.dataframe(df_cycles, use_container_width=True, hide_index=True)

    with tab_alerts:
        df_alerts = alerts_df(alerts)
        if df_alerts.empty:
            st.success("Nenhum alerta ativo registrado para o sistema de lubrificação.")
        else:
            st.dataframe(df_alerts, use_container_width=True, hide_index=True)

    with tab_ai:
        rec = state.get("recommendation", {})
        st.metric("Hipótese principal", _pretty_text(rec.get("primary_hypothesis", "-")))
        st.metric("Confiança", f"{float(rec.get('confidence', 0)) * 100:.0f}%")

        st.markdown("#### Evidências")
        for evidence in rec.get("evidence", []):
            st.markdown(f"- {_pretty_text(evidence)}")

        st.markdown("#### Ações recomendadas")
        for action in rec.get("recommended_actions", []):
            st.markdown(f"- {_pretty_text(action)}")

        if rec.get("affected_outlets"):
            affected = [outlet_label(outlet) for outlet in rec["affected_outlets"]]
            st.warning("Saídas afetadas: " + ", ".join(affected))

    return
