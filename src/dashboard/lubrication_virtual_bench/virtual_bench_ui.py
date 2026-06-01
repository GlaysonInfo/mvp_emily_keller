from __future__ import annotations

import json

import pandas as pd
import streamlit as st

try:
    from dashboard.lubrication.lubrication_config import load_lubrication_config
    from dashboard.lubrication.lubrication_labels import outlet_label, status_label
    from dashboard.lubrication.lubrication_repository import LubricationRepository
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.lubrication.lubrication_config import load_lubrication_config
    from src.dashboard.lubrication.lubrication_labels import outlet_label, status_label
    from src.dashboard.lubrication.lubrication_repository import LubricationRepository

from .scenarios import (
    OUTLETS,
    build_lubrication_scenario_payloads,
    evaluate_lubrication_payloads,
    scenario_detail,
    scenario_options,
    scenario_results_table,
)


def _scenario_label_map() -> dict[str, str]:
    return {label: key for key, label in scenario_options()}


def _last_cycle_outlet_rows(result: dict) -> list[dict]:
    rows = []
    for outlet in result.get("outlets", []):
        rows.append(
            {
                "Saída": outlet_label(outlet.get("outlet_id", "-")),
                "Status": outlet.get("severity"),
                "Diagnóstico": status_label(outlet.get("status", "-")),
                "Pressão": outlet.get("pressure_bar"),
                "Pico": outlet.get("peak_pressure_bar"),
                "Subida": outlet.get("rise_time_sec"),
                "Alívio": outlet.get("decay_time_sec"),
                "Pulso": "OK" if outlet.get("pulse_detected") else "Não detectado",
            }
        )
    return rows


def _curves_table(payload: dict) -> pd.DataFrame:
    rows = []
    for outlet_id in OUTLETS:
        for point in payload.get("curves", {}).get(outlet_id, []):
            rows.append(
                {
                    "Saída": outlet_label(outlet_id),
                    "Tempo (s)": point["ts_sec"],
                    "Pressão (bar)": point["pressure_bar"],
                }
            )
    return pd.DataFrame(rows)


def render_lubrication_virtual_bench_page(config_path: str = "config/lubrication_pilot_config.json") -> None:
    st.header("Bancada Virtual — Lubrificação")
    st.caption("Sequências temporais de pressão para demonstrar falhas reais de lubrificação.")

    config = load_lubrication_config(config_path)
    label_to_id = _scenario_label_map()
    selected_label = st.selectbox("Cenário", list(label_to_id.keys()))
    scenario_id = label_to_id[selected_label]
    detail = scenario_detail(scenario_id)

    col_cycles, col_interval, col_save = st.columns([1, 1, 1.2])
    cycles = int(col_cycles.number_input("Ciclos da sequência", min_value=1, max_value=20, value=6, step=1))
    interval = int(col_interval.number_input("Intervalo entre ciclos (s)", min_value=10, max_value=600, value=60, step=10))
    save_sequence = col_save.checkbox("Gravar no DynamoDB", value=True)

    st.info(detail["description"])
    st.caption(f"Resultado esperado: {detail['expected']}")

    payloads = build_lubrication_scenario_payloads(config, scenario_id, cycles=cycles, interval_seconds=interval)
    results = evaluate_lubrication_payloads(payloads, config)
    last_result = results[-1]
    last_payload = payloads[-1]

    st.subheader("Prévia da sequência")
    st.dataframe(pd.DataFrame(scenario_results_table(results)), width="stretch", hide_index=True)

    col_status, col_pressure, col_anomaly, col_alerts = st.columns(4)
    col_status.metric("Status final", last_result.get("status_label"))
    col_pressure.metric("Maior pressão final", f"{float(last_result.get('max_pressure_bar') or 0):.1f} bar")
    col_anomaly.metric("Maior anomalia final", f"{float(last_result.get('max_anomaly_score') or 0):.1f}")
    col_alerts.metric("Alertas finais", len(last_result.get("active_alerts", [])))

    tab_outlets, tab_curves, tab_payload = st.tabs(["Último Ciclo", "Curva pressão x tempo", "Payload"])

    with tab_outlets:
        st.dataframe(pd.DataFrame(_last_cycle_outlet_rows(last_result)), width="stretch", hide_index=True)

    with tab_curves:
        st.dataframe(_curves_table(last_payload), width="stretch", hide_index=True)

    with tab_payload:
        st.code(json.dumps(last_payload, ensure_ascii=False, indent=2), language="json")

    if st.button("Aplicar sequência temporal", type="primary", width="stretch"):
        if save_sequence:
            repo = LubricationRepository()
            for result in results:
                repo.save_cycle_result(result)
            st.success(f"{len(results)} ciclo(s) gravado(s). Abra Sistema de Lubrificação para ver o estado final.")
        else:
            st.success("Sequência simulada sem gravação.")
