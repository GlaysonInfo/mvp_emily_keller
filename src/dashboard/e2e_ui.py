from __future__ import annotations

import json
from typing import Any

import streamlit as st

try:
    from dashboard.e2e_engine import infer_test_mode, is_virtual_source, load_config, run_e2e_test
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.e2e_engine import infer_test_mode, is_virtual_source, load_config, run_e2e_test


def _option_label(item: dict[str, Any], id_key: str, name_key: str) -> str:
    identifier = item.get(id_key, "")
    name = item.get(name_key, "")
    return f"{identifier} - {name}" if name else str(identifier)


def _extract_id(label: str) -> str:
    return label.split(" - ", 1)[0]


def render_e2e_test_page(config_path: str | None = None) -> None:
    st.subheader("Teste ponta a ponta")
    st.caption("Fonte de dados -> payload padronizado -> DynamoDB -> dashboard -> histórico -> alertas")

    config = load_config(config_path)
    sources = config.get("data_sources", [])
    assets = config.get("assets", [])

    if not sources or not assets:
        st.warning("Cadastre fontes de dados e ativos antes de executar o teste ponta a ponta.")
        return

    source_options = [_option_label(source, "source_id", "source_name") for source in sources]
    asset_options = [_option_label(asset, "asset_id", "asset_name") for asset in assets]

    left, right = st.columns(2)

    with left:
        source_choice = st.selectbox("Fonte de dados", source_options)
        source_id = _extract_id(source_choice)

    with right:
        asset_choice = st.selectbox("Ativo", asset_options)
        asset_id = _extract_id(asset_choice)

    source = next((item for item in sources if item.get("source_id") == source_id), {})

    if is_virtual_source(source):
        mode = "virtual"
        st.info("Fonte virtual detectada. O teste usará payload simulado local, sem chamar HTTP.")
    else:
        mode = st.radio(
            "Modo de teste",
            ["virtual", "csv", "http"],
            format_func=lambda value: {
                "virtual": "Bancada virtual / payload simulado",
                "csv": "CSV/manual",
                "http": "HTTP/HTTPS da bridge",
            }[value],
            horizontal=True,
        )

    effective_mode, mode_reason = infer_test_mode(source, mode)
    st.caption(f"Modo efetivo: {effective_mode} - {mode_reason}")

    csv_file = None

    if effective_mode == "csv":
        csv_file = st.file_uploader("Enviar CSV de teste", type=["csv", "txt"])

    st.info(
        "O teste grava estado atual, registra histórico por minuto, avalia regras de alerta "
        "e faz leitura de volta para comprovar a cadeia completa."
    )

    if not st.button("Executar teste ponta a ponta", type="primary", use_container_width=True):
        return

    result = run_e2e_test(
        config_path=config_path,
        source_id=source_id,
        asset_id=asset_id,
        mode=mode,
        csv_file=csv_file,
    )

    if result["ok"]:
        st.success("Teste ponta a ponta concluído com sucesso.")
    else:
        st.warning("Teste concluído com pendências. Verifique o checklist técnico.")

    st.markdown("#### Checklist técnico")

    for step in result["steps"]:
        label = "OK" if step["ok"] else "Falha"
        st.markdown(f"**{label} - {step['step']}**")

        with st.expander(f"Detalhes - {step['step']}", expanded=False):
            st.json(step["details"])

    st.markdown("#### Resumo do resultado")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", result.get("status_label") or "-")
    col2.metric(
        "Health Score",
        "-" if result.get("health_score") is None else f"{float(result['health_score']):.1f}",
    )
    col3.metric(
        "Severity Score",
        "-" if result.get("severity_score") is None else f"{float(result['severity_score']):.1f}",
    )
    col4.metric("Alertas consultáveis", str(result.get("alerts_records", 0)))

    with st.expander("Payload ingerido", expanded=False):
        st.json(result.get("payload"))

    with st.expander("Estado atual lido de volta", expanded=False):
        st.json(result.get("current_state"))

    export = json.dumps(result, ensure_ascii=False, indent=2)
    st.download_button(
        "Baixar relatório técnico JSON",
        data=export.encode("utf-8"),
        file_name=f"e2e_test_{asset_id}.json",
        mime="application/json",
        use_container_width=True,
    )
