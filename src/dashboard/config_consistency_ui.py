from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.config_consistency import validate_config_consistency
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.config_consistency import validate_config_consistency


SEVERITY_LABELS = {
    "error": "Crítica",
    "warning": "Revisar",
    "info": "Info",
}


def _issue_rows(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "nível": SEVERITY_LABELS.get(issue.get("severity", ""), issue.get("severity", "")),
            "área": issue.get("area", ""),
            "item": issue.get("item", ""),
            "campo": issue.get("field", ""),
            "mensagem": issue.get("message", ""),
            "correção sugerida": issue.get("suggestion", ""),
        }
        for issue in issues
    ]


def render_config_consistency_panel(data: dict[str, Any]) -> dict[str, Any]:
    result = validate_config_consistency(data)
    status = result["status"]

    if status == "critical":
        st.error(result["message"])
    elif status == "warning":
        st.warning(result["message"])
    else:
        st.success(result["message"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Inconsistências críticas", int(result["errors"]))
    c2.metric("Pontos a revisar", int(result["warnings"]))
    c3.metric("Itens avaliados", len(result["issues"]))

    if result["issues"]:
        with st.expander("Checklist de consistência", expanded=False):
            rows = _issue_rows(result["issues"])
            levels = ["Crítica", "Revisar", "Info"]
            selected_levels = st.multiselect("Filtrar por nível", levels, default=["Crítica", "Revisar"])
            visible_rows = [row for row in rows if not selected_levels or row["nível"] in selected_levels]
            df = pd.DataFrame(visible_rows)

            st.dataframe(df, width="stretch", hide_index=True)
            st.download_button(
                "Exportar checklist CSV",
                data=pd.DataFrame(rows).to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="checklist_configuracao.csv",
                mime="text/csv",
                width="stretch",
            )

    return result
