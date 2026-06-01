from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle
    from dashboard.lubrication.lubrication_labels import outlet_label
    from dashboard.lubrication.lubrication_repository import LubricationRepository
    from dashboard.lubrication.lubrication_ui import alerts_df, cycles_df, outlets_df, sample_payload_from_config
    from dashboard.lubrication_efficiency.efficiency_engine import calculate_lubrication_efficiency
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle
    from src.dashboard.lubrication.lubrication_labels import outlet_label
    from src.dashboard.lubrication.lubrication_repository import LubricationRepository
    from src.dashboard.lubrication.lubrication_ui import alerts_df, cycles_df, outlets_df, sample_payload_from_config
    from src.dashboard.lubrication_efficiency.efficiency_engine import calculate_lubrication_efficiency


PAGE_NAME = "Operação de Lubrificação"


def _load_lubrication_config(config_path: str) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _outlet_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for outlet in config.get("outlets") or []:
        rows.append(
            {
                "Saída": str(outlet.get("outlet_id") or "-"),
                "Nome": str(outlet.get("name") or outlet_label(outlet.get("outlet_id"))),
                "Sensor": str(outlet.get("sensor_id") or "-"),
                "Status": str(outlet.get("status") or "Configurada"),
            }
        )
    return rows


def _equipment_link_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for link in config.get("equipment_links") or []:
        rows.append(
            {
                "Ativo": str(link.get("asset_name") or link.get("asset_id") or "-"),
                "Saída": str(link.get("outlet_name") or outlet_label(link.get("outlet_id"))),
                "Graxa": str(link.get("grease_type") or "-"),
                "Dose alvo": f"{link.get('target_grease_g_per_cycle', '-')} g/ciclo",
                "Intervalo": f"{link.get('cycle_interval_h', '-')} h",
                "Baseline": str(link.get("baseline_status") or "-"),
            }
        )
    return rows


def _operation_snapshot(
    config: dict[str, Any],
    repository: Any | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    tenant_id = config.get("tenant_id")
    asset_id = config.get("asset_id")
    if tenant_id and asset_id:
        try:
            repo = repository or LubricationRepository()
            state = repo.get_state(tenant_id, asset_id)
            cycles = repo.list_cycles(tenant_id, asset_id, limit=10)
            alerts = repo.list_alerts(tenant_id, asset_id)
            if state:
                return state, cycles, alerts, "Repositório de ciclos"
        except Exception:
            pass

    demo_cycle = evaluate_lubrication_cycle(sample_payload_from_config(config), config)
    return demo_cycle, [demo_cycle], demo_cycle.get("active_alerts", []), "Ciclo demonstrativo em memória"


def _metric_display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def lubrication_operator_kpis(state: dict[str, Any], cycles: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": state.get("status_label", "-"),
        "outlets": state.get("outlet_count", len(state.get("outlets", []))),
        "normal": state.get("normal_count", 0),
        "attention": state.get("attention_count", 0),
        "alerts": len(alerts) if alerts else state.get("alert_count", 0),
        "critical": state.get("critical_count", 0),
        "executed_cycles": len(cycles),
        "max_pressure_bar": state.get("max_pressure_bar"),
        "max_anomaly_score": state.get("max_anomaly_score"),
    }


def lubrication_points_rows(state: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    outlet_config = {item.get("outlet_id"): item for item in config.get("outlets", [])}
    rows: list[dict[str, Any]] = []
    for outlet in state.get("outlets", []):
        outlet_id = outlet.get("outlet_id")
        configured = outlet_config.get(outlet_id, {})
        rows.append(
            {
                "outlet_id": outlet_id,
                "name": configured.get("name") or outlet_label(outlet_id),
                "sensor_id": configured.get("sensor_id", "-"),
                "pressure_bar": outlet.get("pressure_bar"),
                "peak_pressure_bar": outlet.get("peak_pressure_bar"),
                "rise_time_sec": outlet.get("rise_time_sec"),
                "decay_time_sec": outlet.get("decay_time_sec"),
                "pulse_detected": outlet.get("pulse_detected"),
                "status": outlet.get("status"),
                "status_label": outlet.get("severity"),
                "anomaly_score": outlet.get("anomaly_score"),
                "reasons": outlet.get("reasons", []),
            }
        )
    return rows


def planned_executed_cycles(config: dict[str, Any], cycles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = config.get("equipment_links") or []
    if not links:
        return [
            {
                "Ponto": "Sistema",
                "Ciclos previstos": "-",
                "Ciclos executados": len(cycles),
                "Último ciclo": cycles[0].get("cycle_timestamp") if cycles else "-",
                "Status": cycles[0].get("status_label") if cycles else "-",
            }
        ]

    rows: list[dict[str, Any]] = []
    for link in links:
        rows.append(
            {
                "Ponto": link.get("outlet_name") or outlet_label(link.get("outlet_id")),
                "Ativo": link.get("asset_name") or link.get("asset_id") or "-",
                "Ciclos previstos": f"1 a cada {link.get('cycle_interval_h', '-')} h",
                "Ciclos executados": len(cycles),
                "Último ciclo": cycles[0].get("cycle_timestamp") if cycles else "-",
                "Status": cycles[0].get("status_label") if cycles else "-",
            }
        )
    return rows


def field_anomaly_rows(state: dict[str, Any], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for outlet in state.get("outlets", []):
        if outlet.get("status") == "normal":
            continue
        rows.append(
            {
                "Ponto": outlet_label(outlet.get("outlet_id")),
                "Anomalia": outlet.get("status"),
                "Severidade": outlet.get("severity"),
                "Score": outlet.get("anomaly_score"),
                "Evidência": "; ".join(outlet.get("reasons") or []) or "-",
                "Ação sugerida": action_for_lubrication_anomaly(outlet),
            }
        )

    for alert in alerts:
        if any(row["Ponto"] == outlet_label(alert.get("outlet_id")) for row in rows):
            continue
        rows.append(
            {
                "Ponto": outlet_label(alert.get("outlet_id")),
                "Anomalia": alert.get("metric") or alert.get("description") or "-",
                "Severidade": alert.get("status_label") or "-",
                "Score": "-",
                "Evidência": "; ".join(alert.get("evidence") or []) or alert.get("description") or "-",
                "Ação sugerida": alert.get("recommended_action") or "-",
            }
        )
    return rows


def action_for_lubrication_anomaly(outlet: dict[str, Any]) -> str:
    status = str(outlet.get("status") or "")
    if status == "low_pressure":
        return "Verificar falta de graxa, vazamento, linha aberta, conexão, pistão e bico."
    if status == "no_pulse":
        return "Verificar pistão, linha da saída, distribuidor e alimentação de graxa."
    if status in {"high_pressure", "high_pressure_slow_decay"}:
        return "Inspecionar obstrução, graxa endurecida, restrição na linha ou bico bloqueado."
    if status == "slow_decay":
        return "Verificar retorno, restrição ou ponto de aplicação pesado."
    if status == "slow_rise":
        return "Verificar alimentação, viscosidade da graxa e atuação do pistão."
    return "Inspecionar a saída de graxa e confirmar funcionamento do ciclo."


def technician_failure_analysis_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for outlet in state.get("outlets", []):
        rows.append(
            {
                "Ponto": outlet_label(outlet.get("outlet_id")),
                "Falha provável": outlet.get("status"),
                "Pressão atual": outlet.get("pressure_bar"),
                "Pico": outlet.get("peak_pressure_bar"),
                "Subida": outlet.get("rise_time_sec"),
                "Alívio": outlet.get("decay_time_sec"),
                "Pulso": "Sim" if outlet.get("pulse_detected") else "Não",
                "Score": outlet.get("anomaly_score"),
                "Evidências": "; ".join(outlet.get("reasons") or []) or "-",
                "Plano de ação": action_for_lubrication_anomaly(outlet),
            }
        )
    return rows


def technical_parameter_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rules = config.get("rules") or {}
    return [
        {"Parâmetro": "Pressão baixa", "Valor": rules.get("low_pressure_bar"), "Unidade": "bar"},
        {"Parâmetro": "Pressão alta", "Valor": rules.get("high_pressure_bar"), "Unidade": "bar"},
        {"Parâmetro": "Pressão crítica", "Valor": rules.get("critical_pressure_bar"), "Unidade": "bar"},
        {"Parâmetro": "Tempo máximo de subida", "Valor": rules.get("max_rise_time_sec"), "Unidade": "s"},
        {"Parâmetro": "Tempo máximo de alívio", "Valor": rules.get("max_decay_time_sec"), "Unidade": "s"},
        {"Parâmetro": "Delta mínimo de pulso", "Valor": rules.get("pulse_min_delta_bar"), "Unidade": "bar"},
    ]


def _render_operator_view(
    *,
    state: dict[str, Any],
    cycles: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    kpis = lubrication_operator_kpis(state, cycles, alerts)
    cols = st.columns(5)
    cols[0].metric("Status", kpis["status"])
    cols[1].metric("Pontos", kpis["outlets"])
    cols[2].metric("Ciclos executados", kpis["executed_cycles"])
    cols[3].metric("Alertas", kpis["alerts"])
    cols[4].metric("Maior pressão", _metric_display(kpis["max_pressure_bar"], " bar"))

    tab_points, tab_cycles, tab_anomalies, tab_execution = st.tabs(
        ["Pontos", "Ciclos", "Anomalias", "Registro"]
    )
    with tab_points:
        st.subheader("Pontos de lubrificação")
        st.dataframe(lubrication_points_rows(state, config), width="stretch", hide_index=True)

    with tab_cycles:
        st.subheader("Ciclos previstos e executados")
        st.dataframe(planned_executed_cycles(config, cycles), width="stretch", hide_index=True)

    with tab_anomalies:
        st.subheader("Anomalias de campo")
        anomalies = field_anomaly_rows(state, alerts)
        if anomalies:
            st.dataframe(anomalies, width="stretch", hide_index=True)
        else:
            st.success("Nenhuma anomalia de campo no ciclo atual.")

    with tab_execution:
        st.subheader("Registro simples de execução")
        point_options = [row["name"] for row in lubrication_points_rows(state, config)]
        with st.form("lubrication_execution_record"):
            point = st.selectbox("Ponto", point_options or ["Sistema"])
            execution_status = st.selectbox("Resultado", ["Executado", "Executado com observação", "Não executado"])
            responsible = st.text_input("Responsável", value="operador_demo")
            note = st.text_area("Observação")
            submitted = st.form_submit_button("Registrar execução", type="primary", use_container_width=True)
        if submitted:
            st.session_state["last_lubrication_execution"] = {
                "point": point,
                "status": execution_status,
                "responsible": responsible,
                "note": note,
            }
            st.success("Execução registrada nesta sessão.")
        if st.session_state.get("last_lubrication_execution"):
            st.caption(f"Último registro: {st.session_state['last_lubrication_execution']}")


def _render_technical_view(
    *,
    state: dict[str, Any],
    cycles: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    efficiency = calculate_lubrication_efficiency(state, [], [])
    cols = st.columns(5)
    cols[0].metric("Eficiência", f"{efficiency['efficiency_score']:.1f}%")
    cols[1].metric("Saídas afetadas", efficiency["affected_outlets"])
    cols[2].metric("Score anomalia", _metric_display(state.get("max_anomaly_score")))
    cols[3].metric("Ciclos", len(cycles))
    cols[4].metric("Alertas", len(alerts))

    tab_pressure, tab_params, tab_failures, tab_plan = st.tabs(
        ["Pressão/Ciclo", "Parametrização", "Falhas", "Plano de ação"]
    )
    with tab_pressure:
        st.subheader("Eficiência, motor, pressão e ciclo")
        st.info(efficiency["recommendation"])
        st.dataframe(outlets_df(state), width="stretch", hide_index=True)
        st.subheader("Últimos ciclos")
        df_cycles = cycles_df(cycles)
        if df_cycles.empty:
            st.info("Nenhum ciclo histórico encontrado.")
        else:
            st.dataframe(df_cycles, width="stretch", hide_index=True)

    with tab_params:
        st.subheader("Parametrização técnica")
        st.dataframe(technical_parameter_rows(config), width="stretch", hide_index=True)
        links = _equipment_link_rows(config)
        if links:
            st.subheader("Vínculos equipamento-saída")
            st.dataframe(links, width="stretch", hide_index=True)

    with tab_failures:
        st.subheader("Análise de falhas de lubrificação")
        st.dataframe(technician_failure_analysis_rows(state), width="stretch", hide_index=True)

    with tab_plan:
        st.subheader("Recomendações e plano de ação")
        recommendation = state.get("recommendation") or {}
        st.metric("Hipótese principal", recommendation.get("primary_hypothesis", "-"))
        confidence = recommendation.get("confidence")
        if confidence is not None:
            st.metric("Confiança", f"{float(confidence) * 100:.0f}%")

        plan_rows = []
        for action in recommendation.get("recommended_actions", []):
            plan_rows.append({"Prioridade": "Alta" if alerts else "Rotina", "Ação": action})
        if not plan_rows:
            plan_rows.append({"Prioridade": "Rotina", "Ação": "Manter monitoramento e registrar próximos ciclos."})
        st.dataframe(plan_rows, width="stretch", hide_index=True)

        evidence_rows = [{"Evidência": item} for item in recommendation.get("evidence", [])]
        if evidence_rows:
            st.subheader("Evidências")
            st.dataframe(evidence_rows, width="stretch", hide_index=True)


def _render_system_config(config: dict[str, Any]) -> None:
    pilot_scope = config.get("pilot_scope") if isinstance(config.get("pilot_scope"), dict) else {}
    outlets = _outlet_rows(config)
    equipment_links = _equipment_link_rows(config)

    st.subheader("Sistema configurado")
    scope_rows = [
        {"Item": "Sistema", "Valor": str(config.get("asset_name") or config.get("asset_id") or "-")},
        {"Item": "Gateway", "Valor": str(pilot_scope.get("gateway") or config.get("source_id") or "-")},
        {"Item": "Sensores", "Valor": str(pilot_scope.get("sensors") or "-")},
        {"Item": "Unidade de pressão", "Valor": str(config.get("pressure_unit") or "-")},
    ]
    st.dataframe(scope_rows, width="stretch", hide_index=True)

    st.subheader("Saídas de graxa")
    if outlets:
        st.dataframe(outlets, width="stretch", hide_index=True)
    else:
        st.warning("Nenhuma saída cadastrada para esta planta no modo local.")

    st.subheader("Vínculos com equipamentos")
    if equipment_links:
        st.dataframe(equipment_links, width="stretch", hide_index=True)
    else:
        st.warning("Nenhum vínculo equipamento-saída configurado para esta planta.")


def render_lubrication_operation_page(
    *,
    mode: str,
    tenant_id: str,
    plant_id: str,
    config_path: str,
) -> None:
    config = _load_lubrication_config(config_path)
    pilot_scope = config.get("pilot_scope") if isinstance(config.get("pilot_scope"), dict) else {}
    state, cycles, alerts, snapshot_source = _operation_snapshot(config)

    st.header("Operação de Lubrificação")
    st.caption("Pontos, ciclos, anomalias, execução de campo e diagnóstico técnico do sistema.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cliente", tenant_id)
    c2.metric("Planta", plant_id)
    c3.metric("Saídas monitoradas", str(len(config.get("outlets") or []) or pilot_scope.get("monitored_outlets") or "-"))
    c4.metric("Modo atual", "Técnico" if mode == "technical" else "Operador")
    st.caption(f"Fonte operacional: {snapshot_source}")

    if mode == "operator":
        _render_operator_view(state=state, cycles=cycles, alerts=alerts, config=config)
        return

    tab_technical, tab_operator, tab_system = st.tabs(["Técnico", "Operação", "Sistema"])
    with tab_technical:
        _render_technical_view(state=state, cycles=cycles, alerts=alerts, config=config)
    with tab_operator:
        _render_operator_view(state=state, cycles=cycles, alerts=alerts, config=config)
    with tab_system:
        _render_system_config(config)
