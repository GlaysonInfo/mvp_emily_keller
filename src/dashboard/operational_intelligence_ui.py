from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from dashboard.intelligence_demo_history import seed_demo_history_to_dynamodb
    from dashboard.intelligence_engine import calculate_operational_intelligence, intelligence_to_report_text
    from dashboard.intelligence_repository import OperationalIntelligenceRepository
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.intelligence_demo_history import seed_demo_history_to_dynamodb
    from src.dashboard.intelligence_engine import calculate_operational_intelligence, intelligence_to_report_text
    from src.dashboard.intelligence_repository import OperationalIntelligenceRepository


def _fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


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
        st.error(f"Não foi possível carregar o estado atual para inteligência operacional: {exc}")
        st.stop()

    if not current_state:
        st.warning("Estado atual do ativo não encontrado.")
        st.stop()

    if st.button("Gerar histórico sintético para demonstração", type="primary", use_container_width=True):
        try:
            count = seed_demo_history_to_dynamodb(
                tenant_id=tenant_id,
                plant_id=plant_id,
                asset_id=asset_id,
                current_state=current_state,
                history_repository=repo.history_repository,
            )
        except Exception as exc:
            st.error(f"Não foi possível gerar histórico sintético: {exc}")
        else:
            st.success(f"Histórico sintético gerado com {count} registros para {asset_id}.")
            st.rerun()

    try:
        history_items = repo.query_history(tenant_id=tenant_id, asset_id=asset_id, hours=int(selected_hours))
    except Exception as exc:
        st.error(f"Não foi possível carregar o histórico para inteligência operacional: {exc}")
        st.stop()

    result = calculate_operational_intelligence(history_items=history_items, current_state=current_state)

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
            st.dataframe(df_base, use_container_width=True, hide_index=True)

    with tab_anomalies:
        st.subheader("Anomalias detectadas")
        df_metrics = metric_results_dataframe(result)

        if df_metrics.empty:
            st.info("Sem métricas suficientes para análise.")
        else:
            st.dataframe(df_metrics, use_container_width=True, hide_index=True)

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
            use_container_width=True,
        )

        df_metrics = metric_results_dataframe(result)
        st.download_button(
            "Baixar métricas CSV",
            data=df_metrics.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=f"metricas_ia_{asset_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    return
