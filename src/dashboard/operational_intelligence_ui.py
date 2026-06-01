from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from dashboard.intelligence_demo_history import seed_demo_history_to_dynamodb
    from dashboard.intelligence_engine import calculate_operational_intelligence, intelligence_to_report_text
    from dashboard.intelligence_repository import OperationalIntelligenceRepository
    from dashboard.lubrication.lubrication_config import load_lubrication_config
    from dashboard.lubrication_operation_ui import _operation_snapshot
    from dashboard.lubrication_efficiency.efficiency_engine import calculate_lubrication_efficiency
    from dashboard.lubrication_efficiency.equipment_links import (
        enabled_equipment_links,
        equipment_link_rows,
        filter_linked_equipment_states,
    )
    from dashboard.multiasset_repository import create_multiasset_repository_from_env
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.intelligence_demo_history import seed_demo_history_to_dynamodb
    from src.dashboard.intelligence_engine import calculate_operational_intelligence, intelligence_to_report_text
    from src.dashboard.intelligence_repository import OperationalIntelligenceRepository
    from src.dashboard.lubrication.lubrication_config import load_lubrication_config
    from src.dashboard.lubrication_operation_ui import _operation_snapshot
    from src.dashboard.lubrication_efficiency.efficiency_engine import calculate_lubrication_efficiency
    from src.dashboard.lubrication_efficiency.equipment_links import (
        enabled_equipment_links,
        equipment_link_rows,
        filter_linked_equipment_states,
    )
    from src.dashboard.multiasset_repository import create_multiasset_repository_from_env


def _exception_code(error: Exception) -> str:
    response = getattr(error, "response", None)
    if isinstance(response, dict):
        return str(response.get("Error", {}).get("Code") or error.__class__.__name__)
    return error.__class__.__name__


def _render_data_error(context: str, error: Exception) -> None:
    code = _exception_code(error)
    if code in {"IncompleteSignatureException", "InvalidSignatureException", "SignatureDoesNotMatch"}:
        message = "As credenciais AWS deste ambiente parecem inválidas ou corrompidas."
    elif code in {"ExpiredToken", "ExpiredTokenException"}:
        message = "A sessão AWS expirou. Renove as credenciais e tente novamente."
    elif code in {"UnrecognizedClientException", "InvalidClientTokenId"}:
        message = "A AWS não reconheceu as credenciais deste ambiente."
    elif code in {"AccessDeniedException", "AccessDenied", "UnauthorizedOperation"}:
        message = "O usuário configurado não tem permissão para consultar estes dados."
    else:
        message = "O serviço de dados não respondeu como esperado. Tente novamente ou acione o suporte."

    st.error(context)
    st.write(message)
    with st.expander("Detalhes técnicos para suporte"):
        st.write(f"Código: `{code}`")
        st.code(str(error), language="text")


def _fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _score_to_risk(score: float) -> str:
    if score >= 75:
        return "CRÍTICO"
    if score >= 55:
        return "ALERTA"
    if score >= 30:
        return "ATENÇÃO"
    return "NORMAL"


def integrated_operational_score(
    condition_result: dict[str, object],
    lubrication_summary: dict[str, object],
) -> dict[str, object]:
    condition_score = float(condition_result.get("anomaly_score") or 0)
    lubrication_efficiency = float(lubrication_summary.get("efficiency_score") or 100)
    lubrication_risk = max(0.0, 100.0 - lubrication_efficiency)
    combined_score = round((condition_score * 0.62) + (lubrication_risk * 0.38), 1)
    return {
        "condition_score": round(condition_score, 1),
        "lubrication_efficiency": round(lubrication_efficiency, 1),
        "lubrication_risk": round(lubrication_risk, 1),
        "combined_score": combined_score,
        "risk_level": _score_to_risk(combined_score),
    }


def integrated_hypothesis(
    *,
    condition_result: dict[str, object],
    lubrication_summary: dict[str, object],
    linked_rows: list[dict[str, object]],
) -> str:
    rec = condition_result.get("recommendation") if isinstance(condition_result.get("recommendation"), dict) else {}
    condition_hypothesis = str(rec.get("primary_hypothesis") or "Anomalia de condição em avaliação")
    lubrication_status = str(lubrication_summary.get("status_label") or "-")
    affected_outlets = int(lubrication_summary.get("affected_outlets") or 0)

    if affected_outlets and linked_rows:
        return (
            f"{condition_hypothesis} com possível contribuição do sistema de lubrificação "
            f"({lubrication_status}, {affected_outlets} saída(s) afetada(s))."
        )
    if affected_outlets:
        return f"{condition_hypothesis}. Há desvio de lubrificação, mas sem vínculo direto confirmado para este ativo."
    return f"{condition_hypothesis}. Lubrificação sem desvio relevante no ciclo atual."


def integrated_action_plan(
    *,
    condition_result: dict[str, object],
    lubrication_summary: dict[str, object],
    linked_rows: list[dict[str, object]],
) -> list[dict[str, str]]:
    rec = condition_result.get("recommendation") if isinstance(condition_result.get("recommendation"), dict) else {}
    immediate_actions = [str(action) for action in rec.get("immediate_actions", [])] if isinstance(rec, dict) else []
    plan = [{"Origem": "Condição", "Prioridade": "Alta", "Ação": action} for action in immediate_actions[:3]]

    lubrication_recommendation = str(lubrication_summary.get("recommendation") or "").strip()
    if lubrication_recommendation:
        plan.append({"Origem": "Lubrificação", "Prioridade": "Alta" if linked_rows else "Média", "Ação": lubrication_recommendation})

    for row in linked_rows[:3]:
        plan.append(
            {
                "Origem": "Correlação",
                "Prioridade": "Alta",
                "Ação": (
                    f"Verificar {row.get('Saída')} ligada a {row.get('Equipamento')}: "
                    f"status saída {row.get('Status saída')} e status equipamento {row.get('Status equipamento')}."
                ),
            }
        )

    if not plan:
        plan.append({"Origem": "Rotina", "Prioridade": "Normal", "Ação": "Manter acompanhamento integrado dos dois serviços."})
    return plan


def integrated_evidence_rows(
    *,
    condition_result: dict[str, object],
    lubrication_summary: dict[str, object],
    linked_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    score = integrated_operational_score(condition_result, lubrication_summary)
    return [
        {"Evidência": "Score condição", "Valor": score["condition_score"]},
        {"Evidência": "Eficiência lubrificação", "Valor": score["lubrication_efficiency"]},
        {"Evidência": "Risco combinado", "Valor": score["combined_score"]},
        {"Evidência": "Nível combinado", "Valor": score["risk_level"]},
        {"Evidência": "Saídas afetadas", "Valor": lubrication_summary.get("affected_outlets", 0)},
        {"Evidência": "Equipamentos vinculados", "Valor": lubrication_summary.get("monitored_equipment", 0)},
        {"Evidência": "Vínculos correlacionados", "Valor": len(linked_rows)},
    ]


def _load_integrated_context(tenant_id: str, plant_id: str, asset_id: str) -> dict[str, object]:
    config = load_lubrication_config()
    links = enabled_equipment_links(config)
    lubrication_state, _, _, _ = _operation_snapshot(config)

    try:
        multi_repo = create_multiasset_repository_from_env()
        equipment_states = [
            state
            for state in multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
            if state.get("asset_id") != config.get("asset_id")
        ]
    except Exception:
        equipment_states = []

    linked_states = filter_linked_equipment_states(equipment_states, links)
    selected_links = [link for link in links if link.get("asset_id") == asset_id]
    selected_states = [state for state in linked_states if state.get("asset_id") == asset_id]
    summary_states = selected_states or linked_states
    summary_links = selected_links or links
    lubrication_summary = calculate_lubrication_efficiency(lubrication_state, summary_states, summary_links)
    linked_rows = equipment_link_rows(selected_links or links, equipment_states, lubrication_state)
    if selected_links:
        linked_rows = [row for row in linked_rows if row.get("Asset ID") == asset_id]

    return {
        "config": config,
        "lubrication_state": lubrication_state,
        "equipment_states": equipment_states,
        "links": links,
        "linked_rows": linked_rows,
        "lubrication_summary": lubrication_summary,
    }


def render_integrated_intelligence(
    *,
    condition_result: dict[str, object],
    integrated_context: dict[str, object],
) -> None:
    lubrication_summary = integrated_context.get("lubrication_summary")
    linked_rows = integrated_context.get("linked_rows")
    if not isinstance(lubrication_summary, dict):
        lubrication_summary = {}
    if not isinstance(linked_rows, list):
        linked_rows = []

    score = integrated_operational_score(condition_result, lubrication_summary)
    st.subheader("Inteligência integrada: condição + lubrificação")
    cols = st.columns(5)
    cols[0].metric("Risco combinado", _fmt(score["combined_score"], 1))
    cols[1].metric("Nível", score["risk_level"])
    cols[2].metric("Score condição", _fmt(score["condition_score"], 1))
    cols[3].metric("Eficiência lub.", f"{_fmt(score['lubrication_efficiency'], 1)}%")
    cols[4].metric("Vínculos", len(linked_rows))

    st.info(
        integrated_hypothesis(
            condition_result=condition_result,
            lubrication_summary=lubrication_summary,
            linked_rows=linked_rows,
        )
    )

    tab_corr, tab_plan, tab_evidence = st.tabs(["Correlação", "Plano integrado", "Evidências"])
    with tab_corr:
        if linked_rows:
            st.dataframe(pd.DataFrame(linked_rows), width="stretch", hide_index=True)
        else:
            st.warning("Nenhum vínculo direto entre o ativo selecionado e uma saída de lubrificação foi encontrado.")

    with tab_plan:
        st.dataframe(
            pd.DataFrame(
                integrated_action_plan(
                    condition_result=condition_result,
                    lubrication_summary=lubrication_summary,
                    linked_rows=linked_rows,
                )
            ),
            width="stretch",
            hide_index=True,
        )

    with tab_evidence:
        st.dataframe(
            pd.DataFrame(
                integrated_evidence_rows(
                    condition_result=condition_result,
                    lubrication_summary=lubrication_summary,
                    linked_rows=linked_rows,
                )
            ),
            width="stretch",
            hide_index=True,
        )


def metric_results_dataframe(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Métrica": item.get("label"),
                "Atual": item.get("current"),
                "Baseline": item.get("baseline_mean"),
                "Desvio %": item.get("deviation_pct"),
                "Z-score": item.get("z_score"),
                "Score": item.get("score"),
                "Nível": item.get("level"),
                "Amostras": item.get("samples"),
                "Explicação": item.get("explanation"),
            }
            for item in result.get("metric_results", [])
        ]
    )


def baseline_dataframe(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Métrica": info.get("label"),
                "Unidade": info.get("unit"),
                "Amostras": info.get("samples"),
                "Fonte": info.get("source"),
                "Média": info.get("mean"),
                "Desvio padrão": info.get("std"),
                "Mínimo": info.get("min"),
                "Máximo": info.get("max"),
            }
            for info in (result.get("baseline") or {}).values()
        ]
    )


def render_recommendation(result: dict) -> None:
    rec = result.get("recommendation", {})

    st.subheader("Recomendações da IA explicável")

    c1, c2 = st.columns(2)
    c1.metric("Hipótese principal", rec.get("primary_hypothesis", "-"))
    c2.metric("Confiança", f"{float(rec.get('confidence', 0) or 0) * 100:.0f}%")

    st.markdown("#### Evidências")
    for evidence in rec.get("evidence", []):
        st.markdown(f"- {evidence}")

    st.markdown("#### Ações imediatas recomendadas")
    for action in rec.get("immediate_actions", []):
        st.markdown(f"- {action}")

    st.markdown("#### Ações preventivas")
    for action in rec.get("preventive_actions", []):
        st.markdown(f"- {action}")

    st.markdown("#### Risco se não tratado")
    st.warning(rec.get("risk_if_ignored", "-"))

    alternatives = rec.get("alternatives", [])
    if alternatives:
        with st.expander("Hipóteses alternativas", expanded=False):
            for item in alternatives:
                st.markdown(f"**{item.get('hypothesis')}** - confiança {float(item.get('confidence', 0) or 0) * 100:.0f}%")
                for evidence in item.get("evidence", []):
                    st.markdown(f"- {evidence}")


def render_operational_intelligence_page(
    tenant_id: str,
    plant_id: str,
    asset_id: str,
    history_hours: int = 24,
) -> None:
    st.header("Inteligência Operacional")
    st.caption("Baseline estatístico, anomalias detectadas e recomendações de IA explicável.")

    left, right = st.columns([2, 1])
    selected_hours = left.selectbox(
        "Janela histórica",
        [1, 6, 12, 24, 72, 168],
        index=[1, 6, 12, 24, 72, 168].index(history_hours) if history_hours in [1, 6, 12, 24, 72, 168] else 3,
        format_func=lambda hours: f"Últimas {hours} horas" if hours < 168 else "Últimos 7 dias",
    )
    right.metric("Ativo", asset_id)

    repo = OperationalIntelligenceRepository()

    try:
        current_state = repo.get_current_state(tenant_id=tenant_id, asset_id=asset_id)
    except Exception as exc:
        _render_data_error("Não foi possível carregar o estado atual para inteligência operacional.", exc)
        st.stop()

    if not current_state:
        st.warning("Estado atual do ativo não encontrado.")
        st.stop()

    if st.button("Gerar histórico sintético para demonstração", type="primary", width="stretch"):
        try:
            count = seed_demo_history_to_dynamodb(
                tenant_id=tenant_id,
                plant_id=plant_id,
                asset_id=asset_id,
                current_state=current_state,
                history_repository=repo.history_repository,
            )
        except Exception as exc:
            _render_data_error("Não foi possível gerar histórico sintético.", exc)
        else:
            st.success(f"Histórico sintético gerado com {count} registros para {asset_id}.")
            st.rerun()

    try:
        history_items = repo.query_history(tenant_id=tenant_id, asset_id=asset_id, hours=int(selected_hours))
    except Exception as exc:
        _render_data_error("Não foi possível carregar o histórico para inteligência operacional.", exc)
        st.stop()

    result = calculate_operational_intelligence(history_items=history_items, current_state=current_state)
    integrated_context = _load_integrated_context(tenant_id, plant_id, asset_id)

    if result.get("analysis_source") == "state_fallback":
        st.warning(
            "Baseline histórico ainda insuficiente. A análise está usando o estado atual "
            "e o Severity/Health Score como fallback até haver histórico suficiente."
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Score de anomalia", _fmt(result.get("anomaly_score"), 1))
    c2.metric("Nível", result.get("anomaly_level", "-"))
    c3.metric("Amostras históricas", result.get("history_samples", 0))
    c4.metric("Status atual", current_state.get("status_label", "-"))
    c5.metric("Fonte", result.get("analysis_source") or result.get("score_source") or "-")

    render_integrated_intelligence(condition_result=result, integrated_context=integrated_context)
    st.divider()

    tab_baseline, tab_anomalies, tab_recommendation, tab_report = st.tabs(
        ["Baseline do Ativo", "Anomalias Detectadas", "Recomendações da IA", "Relatório"]
    )

    with tab_baseline:
        st.subheader("Baseline estatístico do ativo")
        st.caption("O baseline usa preferencialmente registros saudáveis. Se houver poucos, usa todo o histórico disponível.")
        df_base = baseline_dataframe(result)

        if df_base.empty or result.get("history_samples", 0) == 0:
            st.info("Ainda não há histórico suficiente para calcular baseline.")
        else:
            st.dataframe(df_base, width="stretch", hide_index=True)

    with tab_anomalies:
        st.subheader("Anomalias detectadas")
        df_metrics = metric_results_dataframe(result)

        if df_metrics.empty:
            st.info("Sem métricas suficientes para análise.")
        else:
            st.dataframe(df_metrics, width="stretch", hide_index=True)

            st.markdown("#### Principais contribuições para o score")
            for item in result.get("ranked_contributors", [])[:5]:
                st.markdown(
                    f"**{item.get('label')}** - score {item.get('score')} | "
                    f"nível {item.get('level')} | {item.get('explanation')}"
                )

    with tab_recommendation:
        render_recommendation(result)

    with tab_report:
        st.subheader("Relatório automático")
        report_text = intelligence_to_report_text(result)
        st.text_area("Relatório técnico gerado", value=report_text, height=380)
        st.download_button(
            "Baixar relatório TXT",
            data=report_text.encode("utf-8"),
            file_name=f"relatorio_ia_{asset_id}.txt",
            mime="text/plain",
            width="stretch",
        )

        df_metrics = metric_results_dataframe(result)
        st.download_button(
            "Baixar métricas CSV",
            data=df_metrics.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=f"metricas_ia_{asset_id}.csv",
            mime="text/csv",
            width="stretch",
        )

    return
