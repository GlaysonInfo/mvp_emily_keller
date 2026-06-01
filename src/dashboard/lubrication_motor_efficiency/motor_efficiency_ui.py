from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.history_repository import create_history_repository_from_env
    from dashboard.lubrication.lubrication_config import load_lubrication_config
    from dashboard.lubrication.lubrication_labels import outlet_label
    from dashboard.lubrication.lubrication_repository import LubricationRepository
    from dashboard.lubrication_efficiency.equipment_links import enabled_equipment_links
    from dashboard.multiasset_repository import create_multiasset_repository_from_env
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.history_repository import create_history_repository_from_env
    from src.dashboard.lubrication.lubrication_config import load_lubrication_config
    from src.dashboard.lubrication.lubrication_labels import outlet_label
    from src.dashboard.lubrication.lubrication_repository import LubricationRepository
    from src.dashboard.lubrication_efficiency.equipment_links import enabled_equipment_links
    from src.dashboard.multiasset_repository import create_multiasset_repository_from_env

from .motor_efficiency_engine import (
    build_marco_zero,
    build_response_rows,
    grease_comparison_rows,
    metric_value,
    recommend_dose,
    severity_value,
)


def _format_number(value: Any, suffix: str = "") -> str:
    if value in [None, ""]:
        return "-"

    try:
        return f"{float(value):.1f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def _link_label(link: dict[str, Any]) -> str:
    return f"{link.get('asset_name') or link.get('asset_id')} -> {link.get('outlet_name') or outlet_label(link.get('outlet_id', ''))}"


def _find_current_state(states: list[dict[str, Any]], asset_id: str) -> dict[str, Any] | None:
    return next((state for state in states if state.get("asset_id") == asset_id), None)


def _cycle_label(cycle: dict[str, Any]) -> str:
    timestamp = cycle.get("cycle_timestamp") or cycle.get("updated_at") or "-"
    return f"{timestamp} | {cycle.get('cycle_id') or 'ciclo'}"


def _cycles_rows(cycles: list[dict[str, Any]], link: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    outlet_id = str(link.get("outlet_id") or "")

    for cycle in cycles:
        outlet = next((item for item in cycle.get("outlets", []) if item.get("outlet_id") == outlet_id), {})
        rows.append(
            {
                "Ciclo": cycle.get("cycle_id"),
                "Data": cycle.get("cycle_timestamp") or cycle.get("updated_at"),
                "Saída": outlet_label(outlet_id),
                "Status saída": outlet.get("severity") or outlet.get("status") or "-",
                "Pico (bar)": outlet.get("peak_pressure_bar"),
                "Dose registrada (g)": cycle.get("grease_amount_g") or "-",
                "Graxa": cycle.get("grease_type") or link.get("grease_type") or "-",
                "Intervalo (h)": cycle.get("cycle_interval_h") or link.get("cycle_interval_h") or "-",
            }
        )

    return rows


def _response_dataframe(response_rows: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in response_rows:
        rows.append(
            {
                "Ciclo": row.get("cycle_id"),
                "Data": row.get("cycle_timestamp"),
                "Dose (g)": row.get("grease_amount_g"),
                "Graxa": row.get("grease_type"),
                "Resposta": row.get("response_label"),
                "Score": row.get("response_score"),
                "Saúde antes": row.get("health_before"),
                "Saúde depois": row.get("health_after"),
                "Delta saúde": row.get("health_delta"),
                "Redução vibração (%)": row.get("vibration_reduction_pct"),
                "Delta temperatura (°C)": row.get("temperature_delta_c"),
                "Delta ultrassom (dB)": row.get("ultrasound_delta_db"),
                "Status saída": row.get("outlet_status"),
            }
        )

    return pd.DataFrame(rows)


def _render_marco_zero(link: dict[str, Any], marco_zero: dict[str, Any], current_state: dict[str, Any] | None) -> None:
    st.subheader("Marco zero do motor")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equipamento", link.get("asset_name") or link.get("asset_id"))
    c2.metric("Saída vinculada", link.get("outlet_name") or outlet_label(link.get("outlet_id", "")))
    c3.metric("Dose alvo", _format_number(link.get("target_grease_g_per_cycle"), " g"))
    c4.metric("Intervalo", _format_number(link.get("cycle_interval_h"), " h"))

    if not marco_zero["has_history"]:
        st.warning("Ainda não há histórico suficiente para fixar o marco zero do motor.")
    else:
        st.caption(f"Primeiro ponto histórico usado como marco zero: {marco_zero['timestamp']}")

    c5, c6, c7, c8, c9 = st.columns(5)
    c5.metric("Saúde inicial", _format_number(marco_zero.get("health_score")))
    c6.metric("Gravidade inicial", _format_number(marco_zero.get("severity_score")))
    c7.metric("Vibração inicial", _format_number(marco_zero.get("vibration_rms_mm_s"), " mm/s"))
    c8.metric("Temperatura inicial", _format_number(marco_zero.get("temperature_c"), " °C"))
    c9.metric("Ultrassom inicial", _format_number(marco_zero.get("ultrasound_db"), " dB"))

    if current_state:
        st.subheader("Estado atual para comparação")
        c10, c11, c12 = st.columns(3)
        c10.metric("Status atual", current_state.get("status_label") or "-")
        c11.metric("Saúde atual", _format_number(metric_value(current_state, "health_score")))
        c12.metric("Gravidade atual", _format_number(severity_value(current_state)))


def _render_cycle_registration(
    *,
    repo: LubricationRepository,
    tenant_id: str,
    lubrication_asset_id: str,
    link: dict[str, Any],
    cycles: list[dict[str, Any]],
) -> None:
    st.subheader("Registro manual da dose aplicada")

    if not cycles:
        st.info("Nenhum ciclo de lubrificação encontrado para registrar dose.")
        return

    labels = [_cycle_label(cycle) for cycle in cycles]
    selected_label = st.selectbox("Ciclo de graxa", labels)
    selected_cycle = cycles[labels.index(selected_label)]

    with st.form("motor_lubrication_dose_form"):
        c1, c2, c3 = st.columns(3)
        grease_amount = c1.number_input(
            "Graxa aplicada (g)",
            min_value=0.0,
            value=float(selected_cycle.get("grease_amount_g") or link.get("target_grease_g_per_cycle") or 0.0),
            step=0.5,
        )
        grease_type = c2.text_input("Tipo de graxa", value=str(selected_cycle.get("grease_type") or link.get("grease_type") or ""))
        interval_h = c3.number_input(
            "Intervalo do ciclo (h)",
            min_value=0.0,
            value=float(selected_cycle.get("cycle_interval_h") or link.get("cycle_interval_h") or 0.0),
            step=1.0,
        )

        submitted = st.form_submit_button("Salvar dose no ciclo", type="primary", width="stretch")

    if submitted:
        repo.update_cycle_dose(
            tenant_id,
            lubrication_asset_id,
            selected_cycle["cycle_timestamp"],
            linked_asset_id=link["asset_id"],
            outlet_id=link["outlet_id"],
            grease_amount_g=grease_amount,
            grease_type=grease_type,
            cycle_interval_h=interval_h,
        )
        st.success("Dose registrada no ciclo de graxa.")
        st.rerun()


def _render_recommendation(recommendation: dict[str, Any]) -> None:
    decision = recommendation.get("decision")
    dose = recommendation.get("recommended_dose_g")

    c1, c2, c3 = st.columns(3)
    c1.metric("Recomendação", decision or "-")
    c2.metric("Dose sugerida", _format_number(dose, " g"))
    c3.metric("Confiança", recommendation.get("confidence", "-"))

    message = recommendation.get("message", "")
    if decision == "MANTER":
        st.success(message)
    elif decision in {"AUMENTAR", "REDUZIR"}:
        st.warning(message)
    else:
        st.info(message)


def render_motor_lubrication_efficiency_page(
    *,
    tenant_id: str,
    plant_id: str,
    config_path: str = "config/lubrication_pilot_config.json",
) -> None:
    st.header("Eficiência da Lubrificação do Motor")
    st.caption("Dose de graxa, resposta do motor e recomendação para otimizar vida útil e custo.")

    config = load_lubrication_config(config_path)
    links = enabled_equipment_links(config)

    if not links:
        st.warning("Nenhum vínculo ativo entre equipamento e saída de graxa.")
        return

    selected_label = st.selectbox("Vínculo monitorado", [_link_label(link) for link in links])
    link = links[[_link_label(item) for item in links].index(selected_label)]

    history_hours = int(st.number_input("Janela de histórico do motor (h)", min_value=1, max_value=720, value=168, step=24))
    response_window_hours = int(st.number_input("Janela para medir resposta após graxa (h)", min_value=1, max_value=168, value=24, step=1))

    lubrication_asset_id = str(config.get("asset_id") or link.get("lubrication_system_id") or "sistema_lubrificacao_01")
    lubrication_repo = LubricationRepository()
    cycles = lubrication_repo.list_cycles(tenant_id, lubrication_asset_id, limit=50)

    end_utc = datetime.now(UTC)
    start_utc = end_utc - timedelta(hours=history_hours)
    history_repo = create_history_repository_from_env()
    history_items = history_repo.query_history(
        tenant_id=tenant_id,
        asset_id=link["asset_id"],
        start_utc=start_utc,
        end_utc=end_utc,
    )

    multi_repo = create_multiasset_repository_from_env()
    current_states = multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
    current_state = _find_current_state(current_states, link["asset_id"])

    marco_zero = build_marco_zero(history_items, current_state)
    response_rows = build_response_rows(
        link=link,
        cycles=cycles,
        history_items=history_items,
        response_window_hours=response_window_hours,
    )
    recommendation = recommend_dose(link, response_rows)

    tab_zero, tab_cycles, tab_response, tab_dose, tab_greases = st.tabs(
        ["Marco Zero", "Ciclos de Graxa", "Resposta do Motor", "Dose Recomendada", "Comparativo de Graxas"]
    )

    with tab_zero:
        _render_marco_zero(link, marco_zero, current_state)

    with tab_cycles:
        _render_cycle_registration(
            repo=lubrication_repo,
            tenant_id=tenant_id,
            lubrication_asset_id=lubrication_asset_id,
            link=link,
            cycles=cycles,
        )
        st.divider()
        st.dataframe(pd.DataFrame(_cycles_rows(cycles, link)), width="stretch", hide_index=True)

    with tab_response:
        response_df = _response_dataframe(response_rows)
        if response_df.empty:
            st.info("Ainda não há ciclos com histórico antes/depois suficiente para calcular resposta.")
        else:
            st.dataframe(response_df, width="stretch", hide_index=True)

    with tab_dose:
        _render_recommendation(recommendation)

    with tab_greases:
        comparison = pd.DataFrame(grease_comparison_rows(response_rows))
        if comparison.empty:
            st.info("Comparativo será exibido após ciclos com dose e tipo de graxa registrados.")
        else:
            st.dataframe(comparison, width="stretch", hide_index=True)
