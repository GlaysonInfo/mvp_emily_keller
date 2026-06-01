from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from dashboard.connection_validators import (
        validate_csv_file,
        validate_secret_reference,
        validate_signal_map_for_csv,
        validate_signal_map_for_source,
        validate_source_connection,
    )
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.connection_validators import (
        validate_csv_file,
        validate_secret_reference,
        validate_signal_map_for_csv,
        validate_signal_map_for_source,
        validate_source_connection,
    )


def _show_result(result: Any, title: str = "Resultado") -> None:
    data = result.to_dict() if hasattr(result, "to_dict") else result

    if data.get("ok"):
        st.success(data.get("message", "OK"))
    elif data.get("status") in {"atenção", "pendente"}:
        st.warning(data.get("message", "Atenção"))
    else:
        st.error(data.get("message", "Falha"))

    with st.expander(f"Detalhes técnicos - {title}", expanded=False):
        st.json(data)


def render_validation_panel(
    *,
    data: dict[str, Any],
    selected_source: dict[str, Any] | None,
    selected_asset_id: str | None = None,
) -> None:
    if not selected_source:
        st.info("Selecione ou cadastre uma fonte de dados para validar.")
        return

    st.markdown("#### Validação real da fonte de dados")

    source_id = selected_source.get("source_id")
    protocol = str(selected_source.get("protocol", ""))

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Testar conexão selecionada", width="stretch"):
            _show_result(validate_source_connection(selected_source), "conexão")

    with col2:
        if st.button("Validar credencial", width="stretch"):
            _show_result(validate_secret_reference(selected_source), "credencial")

    with col3:
        if st.button("Validar tags mapeadas", width="stretch"):
            _show_result(
                validate_signal_map_for_source(
                    selected_source,
                    data.get("signal_map", []),
                    asset_id=selected_asset_id,
                ),
                "tags mapeadas",
            )

    if "CSV" not in protocol.upper() and "MANUAL" not in protocol.upper():
        return

    st.markdown("#### Validação de arquivo CSV/manual")

    uploaded = st.file_uploader(
        "Enviar CSV para testar leitura e colunas",
        type=["csv", "txt"],
        key=f"csv_validation_{source_id}",
    )

    col_csv1, col_csv2 = st.columns(2)

    with col_csv1:
        if st.button("Ler CSV", width="stretch"):
            _show_result(validate_csv_file(uploaded), "CSV")

    with col_csv2:
        if st.button("Validar CSV contra mapeamento", width="stretch"):
            _show_result(
                validate_signal_map_for_csv(
                    data.get("signal_map", []),
                    uploaded,
                    asset_id=selected_asset_id,
                    source_id=str(source_id) if source_id else None,
                ),
                "CSV x mapeamento",
            )
