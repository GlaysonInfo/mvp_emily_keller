from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from dashboard.lubrication.lubrication_config import load_lubrication_config
    from dashboard.lubrication.lubrication_labels import outlet_label
    from dashboard.lubrication.lubrication_repository import LubricationRepository
    from dashboard.multiasset_repository import create_multiasset_repository_from_env
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.lubrication.lubrication_config import load_lubrication_config
    from src.dashboard.lubrication.lubrication_labels import outlet_label
    from src.dashboard.lubrication.lubrication_repository import LubricationRepository
    from src.dashboard.multiasset_repository import create_multiasset_repository_from_env

from .efficiency_engine import calculate_lubrication_efficiency, equipment_rows
from .equipment_links import enabled_equipment_links, equipment_link_rows, filter_linked_equipment_states


def _outlet_rows(state: dict) -> list[dict]:
    rows = []
    for outlet in state.get("outlets", []):
        rows.append(
            {
                "Saída": outlet_label(outlet.get("outlet_id", "-")),
                "Status": outlet.get("status_label") or outlet.get("severity") or outlet.get("status") or "-",
                "Pressão atual": outlet.get("pressure_bar"),
                "Pico": outlet.get("peak_pressure_bar"),
                "Tempo subida": outlet.get("rise_time_sec"),
                "Tempo alívio": outlet.get("decay_time_sec"),
                "Diagnóstico": outlet.get("diagnosis") or outlet.get("status") or "-",
            }
        )
    return rows


def _status_message(summary: dict) -> None:
    status = summary["status_label"]
    score = summary["efficiency_score"]

    if status == "EFICIENTE":
        st.success(f"Eficiência da lubrificação em {score:.1f}%. Sistema operando dentro do esperado.")
    elif status == "ATENÇÃO":
        st.warning(f"Eficiência da lubrificação em {score:.1f}%. Há pontos para acompanhar.")
    else:
        st.error(f"Eficiência da lubrificação em {score:.1f}%. Intervenção recomendada.")


def render_lubrication_efficiency_page(
    tenant_id: str,
    plant_id: str,
    config_path: str = "config/lubrication_pilot_config.json",
) -> None:
    st.header("Eficiência da Lubrificação")
    st.caption("Correlação entre saídas de graxa, condição dos equipamentos e risco operacional.")

    config = load_lubrication_config(config_path)
    lubrication_asset_id = config.get("asset_id", "sistema_lubrificacao_01")
    links = enabled_equipment_links(config)

    lubrication_repo = LubricationRepository()
    lubrication_state = lubrication_repo.get_state(tenant_id, lubrication_asset_id)
    cycles = lubrication_repo.list_cycles(tenant_id, lubrication_asset_id, limit=10)
    alerts = lubrication_repo.list_alerts(tenant_id, lubrication_asset_id)

    multi_repo = create_multiasset_repository_from_env()
    equipment_states = [
        state
        for state in multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
        if state.get("asset_id") != lubrication_asset_id
    ]
    linked_equipment_states = filter_linked_equipment_states(equipment_states, links)

    if not lubrication_state:
        st.warning("Ainda não há ciclo de lubrificação salvo para calcular eficiência.")
        return

    summary = calculate_lubrication_efficiency(lubrication_state, linked_equipment_states, links)
    _status_message(summary)

    col_score, col_outlets, col_equipment, col_anomaly = st.columns(4)
    col_score.metric("Eficiência", f"{summary['efficiency_score']:.1f}%")
    col_outlets.metric("Saídas afetadas", summary["affected_outlets"])
    col_equipment.metric("Equipamentos correlacionados", summary["monitored_equipment"])
    col_anomaly.metric("Score de anomalia", f"{float(lubrication_state.get('max_anomaly_score') or 0):.1f}")

    col_lub, col_cond, col_risk = st.columns(3)
    col_lub.metric("Pontuação das saídas", f"{summary['outlet_score']:.1f}%")
    col_cond.metric("Condição dos equipamentos", f"{summary['equipment_score']:.1f}%")
    col_risk.metric("Reserva contra anomalia", f"{summary['anomaly_score']:.1f}%")

    st.subheader("Leitura operacional")
    st.info(summary["recommendation"])

    tab_links, tab_outlets, tab_equipment, tab_cycles, tab_alerts = st.tabs(
        ["Vínculos", "Saídas de Graxa", "Equipamentos", "Últimos Ciclos", "Alertas"]
    )

    with tab_links:
        link_rows = equipment_link_rows(links, equipment_states, lubrication_state)
        if not link_rows:
            st.info("Nenhum vínculo ativo entre equipamento monitorado e saída de graxa.")
        else:
            st.dataframe(pd.DataFrame(link_rows), use_container_width=True, hide_index=True)

    with tab_outlets:
        outlet_df = pd.DataFrame(_outlet_rows(lubrication_state))
        if outlet_df.empty:
            st.info("Nenhuma saída encontrada no ciclo atual.")
        else:
            st.dataframe(outlet_df, use_container_width=True, hide_index=True)

    with tab_equipment:
        equipment_df = pd.DataFrame(equipment_rows(linked_equipment_states))
        if equipment_df.empty:
            st.info("Nenhum estado atual encontrado para os equipamentos vinculados.")
        else:
            st.dataframe(equipment_df, use_container_width=True, hide_index=True)

    with tab_cycles:
        cycle_rows = [
            {
                "Ciclo": cycle.get("cycle_id"),
                "Status": cycle.get("status_label"),
                "Normais": cycle.get("normal_count"),
                "Atenção": cycle.get("attention_count"),
                "Alertas": cycle.get("alert_count"),
                "Críticos": cycle.get("critical_count"),
                "Maior pressão": cycle.get("max_pressure_bar"),
                "Atualizado": cycle.get("cycle_timestamp") or cycle.get("updated_at"),
            }
            for cycle in cycles
        ]
        st.dataframe(pd.DataFrame(cycle_rows), use_container_width=True, hide_index=True)

    with tab_alerts:
        alert_rows = [
            {
                "Saída": outlet_label(alert.get("outlet_id", "-")),
                "Status": alert.get("status_label"),
                "Descrição": alert.get("description"),
                "Ação recomendada": alert.get("recommended_action"),
            }
            for alert in alerts
        ]
        if not alert_rows:
            st.success("Nenhum alerta ativo de lubrificação.")
        else:
            st.dataframe(pd.DataFrame(alert_rows), use_container_width=True, hide_index=True)
