from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases


PAGE_NAME = "Bancada Virtual — Equipamentos"


def _asset_options(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    options = []
    for asset in assets:
        asset_id = str(asset.get("asset_id") or "").strip()
        if not asset_id:
            continue
        options.append(
            {
                "asset_id": asset_id,
                "label": f"{asset_id} - {asset.get('asset_name') or asset_id}",
            }
        )
    return options or [{"asset_id": "motor_001", "label": "motor_001 - Motor demonstração"}]


def _case_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        metrics = case.get("metrics") or {}
        rows.append(
            {
                "Cenário": case.get("case_name"),
                "Status": case.get("status_label"),
                "Health": case.get("health_score"),
                "Severity": case.get("severity_score"),
                "Vibração": metrics.get("vibration_rms_mm_s"),
                "Temperatura": metrics.get("temperature_c"),
                "Ultrassom": metrics.get("ultrasound_db"),
                "Gera alerta": "Sim" if case.get("alert") else "Não",
            }
        )
    return rows


def _case_detail_rows(case: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = case.get("metrics") or {}
    return [
        {"Item": "Sintoma simulado", "Valor": case.get("symptom_simulated") or "-"},
        {"Item": "Diagnóstico esperado", "Valor": case.get("diagnosis") or "-"},
        {"Item": "Ação recomendada", "Valor": case.get("recommended_action") or "-"},
        {"Item": "Pergunta respondida ao cliente", "Valor": case.get("client_question_answered") or "-"},
        {"Item": "RPM", "Valor": metrics.get("rpm")},
        {"Item": "Vibração RMS", "Valor": metrics.get("vibration_rms_mm_s")},
        {"Item": "Temperatura", "Valor": metrics.get("temperature_c")},
        {"Item": "Ultrassom", "Valor": metrics.get("ultrasound_db")},
    ]


def apply_condition_demo_case(
    repo: Any,
    case: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
    asset_id: str,
) -> None:
    latest_item = build_latest_state_item(case, tenant_id=tenant_id, plant_id=plant_id, asset_id=asset_id)
    alert_item = build_demo_alert_item(
        case,
        tenant_id=tenant_id,
        plant_id=plant_id,
        asset_id=asset_id,
        payload_updated_at=str(latest_item["updated_at"]),
    )

    repo.put_latest_state(latest_item)
    repo.clear_demo_alerts(tenant_id=tenant_id, asset_id=asset_id)
    if alert_item:
        repo.put_active_alert(alert_item)


def render_condition_virtual_bench_page(
    *,
    repo: Any,
    tenant_id: str,
    plant_id: str,
    assets: list[dict[str, Any]] | None = None,
) -> dict[str, str] | None:
    st.header(PAGE_NAME)
    st.caption("Cenários de condição para demonstrar como a tela de monitoramento muda após a simulação.")

    cases = load_demo_cases()
    asset_options = _asset_options(assets or [])

    left, right = st.columns([1.2, 1])
    with left:
        selected_case = st.selectbox(
            "Cenário de teste",
            cases,
            format_func=lambda case: str(case.get("case_name") or case.get("case_id")),
        )
    with right:
        selected_asset = st.selectbox(
            "Ativo demonstrado",
            asset_options,
            format_func=lambda asset: str(asset["label"]),
        )

    st.info(str(selected_case.get("demo_message") or "Cenário pronto para apresentação."))
    st.caption(f"Resultado esperado: {selected_case.get('expected_result') or '-'}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status simulado", str(selected_case.get("status_label") or "-"))
    c2.metric("Health", "-" if selected_case.get("health_score") is None else f"{float(selected_case['health_score']):.1f}")
    c3.metric(
        "Severity",
        "-" if selected_case.get("severity_score") is None else f"{float(selected_case['severity_score']):.1f}",
    )
    c4.metric("Alerta", "Sim" if selected_case.get("alert") else "Não")

    tab_selected, tab_catalog = st.tabs(["Prévia do cenário", "Catálogo"])
    with tab_selected:
        st.dataframe(pd.DataFrame(_case_detail_rows(selected_case)), width="stretch", hide_index=True)
    with tab_catalog:
        st.dataframe(pd.DataFrame(_case_rows(cases)), width="stretch", hide_index=True)

    if st.button("Aplicar cenário no ativo", type="primary", width="stretch"):
        apply_condition_demo_case(
            repo,
            selected_case,
            tenant_id=tenant_id,
            plant_id=plant_id,
            asset_id=selected_asset["asset_id"],
        )
        st.session_state["selected_asset_id"] = selected_asset["asset_id"]
        st.success(
            "Cenário aplicado. Abra Monitoramento de Equipamentos, Detalhe do Ativo ou Alertas para ver o resultado."
        )

    b1, b2, b3 = st.columns(3)
    if b1.button("Ver monitoramento", type="primary", use_container_width=True):
        return {"route": "Monitoramento de Equipamentos", "asset_id": selected_asset["asset_id"]}
    if b2.button("Abrir detalhe do ativo", use_container_width=True):
        return {"route": "Detalhe do Ativo", "asset_id": selected_asset["asset_id"]}
    if b3.button("Ver alertas", use_container_width=True):
        return {"route": "Alertas e Eventos", "asset_id": selected_asset["asset_id"]}
    return None
