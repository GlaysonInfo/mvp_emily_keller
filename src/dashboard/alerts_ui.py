from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.alerts_repository import AlertsRepository, create_alerts_repository_from_env
    from dashboard.audit_events import record_sensitive_action
    from dashboard.escalation_engine import (
        apply_escalation_rule,
        escalation_matrix_rows as engine_escalation_matrix_rows,
        normalize_severity_label,
        pretty_metric,
        rule_for_severity,
    )
    from dashboard.escalation_repository import DEFAULT_ESCALATION_DATA, EscalationRepository, normalize_escalation_data
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alerts_repository import AlertsRepository, create_alerts_repository_from_env
    from src.dashboard.audit_events import record_sensitive_action
    from src.dashboard.escalation_engine import (
        apply_escalation_rule,
        escalation_matrix_rows as engine_escalation_matrix_rows,
        normalize_severity_label,
        pretty_metric,
        rule_for_severity,
    )
    from src.dashboard.escalation_repository import (
        DEFAULT_ESCALATION_DATA,
        EscalationRepository,
        normalize_escalation_data,
    )


STATUS_PT = {
    "open": "Aberto",
    "acknowledged": "Ciente",
    "in_progress": "Em tratamento",
    "resolved": "Resolvido",
    "closed": "Fechado",
}
STATUS_COLORS = {
    "ATENÇÃO": "#F1C40F",
    "ATENCAO": "#F1C40F",
    "ALERTA": "#E67E22",
    "CRÍTICO": "#E74C3C",
    "CRITICO": "#E74C3C",
    "SEM COMUNICAÇÃO": "#95A5A6",
    "SEM COMUNICACAO": "#95A5A6",
    "NORMAL": "#2ECC71",
}
STATUS_PRIORITY = {"open": 5, "acknowledged": 4, "in_progress": 3, "resolved": 2, "closed": 1}
SEVERITY_PRIORITY = {
    "SEM COMUNICAÇÃO": 6,
    "SEM COMUNICACAO": 6,
    "CRÍTICO": 5,
    "CRITICO": 5,
    "ALERTA": 4,
    "ATENÇÃO": 2,
    "ATENCAO": 2,
    "NORMAL": 0,
}
DEFAULT_MANUAL_RECOMMENDED_ACTION = (
    "Realizar inspeção técnica no ativo, registrar evidências e avaliar necessidade de intervenção corretiva ou "
    "preventiva."
)
FALLBACK_RECOMMENDED_ACTION = (
    "Realizar inspeção técnica no ativo, registrar evidências visuais, verificar vibração anormal, ruído, "
    "temperatura, fixação, lubrificação e necessidade de intervenção corretiva ou preventiva."
)


def escalation_rule(status_label: Any, data: dict[str, Any] | None = None) -> dict[str, str]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    decision = apply_escalation_rule({"status_label": status_label}, loaded)
    rule = rule_for_severity(status_label, loaded)
    repeat_after = int(rule.get("repeat_after_minutes") or 0)
    escalate_after = int(rule.get("escalate_after_minutes") or 0)

    if repeat_after and escalate_after:
        repeat_policy = f"Repetir a cada {repeat_after} min; escalar após {escalate_after} min"
    elif repeat_after:
        repeat_policy = f"Repetir a cada {repeat_after} min"
    elif escalate_after:
        repeat_policy = f"Escalonar após {escalate_after} min"
    else:
        repeat_policy = "Não repetir"

    return {
        "severity": decision["severity"],
        "recipients": decision["contact_groups"],
        "channels": decision["channels"],
        "notify_when": "Conforme status e severidade",
        "repeat_policy": repeat_policy,
    }


def escalation_matrix_rows(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "Severidade": row["Severidade"],
            "Vai para quem": row["Destino"],
            "Quando notifica": "Conforme status e severidade",
            "Repetição / escalonamento": f"{row['Repetição']} | {row['Escalonamento']}",
            "Canais previstos": row["Canal"],
        }
        for row in engine_escalation_matrix_rows(data or DEFAULT_ESCALATION_DATA)
    ]


def _status_label_from_severity(severity: Any) -> str:
    normalized = str(severity or "").lower()

    if normalized == "critical":
        return "CRÍTICO"

    if normalized == "warning":
        return "ATENÇÃO"

    if normalized == "normal":
        return "NORMAL"

    return str(severity or "-").upper()


def _tenant_asset(alert: dict[str, Any]) -> str:
    if alert.get("tenant_asset"):
        return str(alert["tenant_asset"])

    tenant_id = str(alert.get("tenant_id") or "")
    asset_id = str(alert.get("asset_id") or "")
    return f"{tenant_id}#{asset_id}" if tenant_id and asset_id else ""


def _alert_key(alert: dict[str, Any]) -> str:
    return str(alert.get("alert_key") or alert.get("sk") or "")


def alerts_df(
    alerts: list[dict[str, Any]],
    timezone_str: str = "America/Sao_Paulo",
    escalation_data: dict[str, Any] | None = None,
) -> pd.DataFrame:
    if not alerts:
        return pd.DataFrame()

    loaded_escalation_data = normalize_escalation_data(escalation_data or DEFAULT_ESCALATION_DATA)
    rows = []
    for alert in alerts:
        status_label = str(alert.get("status_label") or _status_label_from_severity(alert.get("severity")))
        if str(alert.get("alert_type") or "").lower() == "communication_lost":
            status_label = "SEM COMUNICAÇÃO"
        status_label = normalize_severity_label(status_label)
        recommended_action = str(alert.get("recommended_action") or "").strip() or FALLBACK_RECOMMENDED_ACTION
        normalized_alert = {**alert, "status_label": status_label, "recommended_action": recommended_action}
        escalation = apply_escalation_rule(normalized_alert, loaded_escalation_data)
        metric = alert.get("metric") or alert.get("alert_type") or alert.get("probable_cause")
        first_detected_at = alert.get("first_detected_at")
        last_detected_at = alert.get("last_detected_at") or alert.get("updated_at") or alert.get("last_payload_timestamp")

        rows.append(
            {
                "tenant_asset": _tenant_asset(alert),
                "alert_key": _alert_key(alert),
                "pk": alert.get("pk"),
                "sk": alert.get("sk"),
                "alert_id": alert.get("alert_id") or f"{_tenant_asset(alert)}#{_alert_key(alert)}",
                "asset_id": alert.get("asset_id"),
                "asset_name": alert.get("asset_name", alert.get("asset_id")),
                "metric": metric,
                "value": alert.get("value"),
                "threshold": alert.get("threshold"),
                "status_label": status_label,
                "status": alert.get("status", "open"),
                "first_detected_at": first_detected_at,
                "last_detected_at": last_detected_at,
                "recommended_action": recommended_action,
                "last_note": alert.get("last_note", alert.get("note", "")),
                "last_action_taken": alert.get("last_action_taken", ""),
                "escalation_recipients": escalation["contact_groups"],
                "escalation_channels": escalation["channels"],
                "escalation_notify_when": "Conforme status e severidade",
                "escalation_repeat_policy": (
                    f"Repetir: {escalation['repeat_after_minutes']} min | "
                    f"Escalonar: {escalation['escalate_after_minutes']} min"
                ),
            }
        )

    df = pd.DataFrame(rows)

    for column in ["first_detected_at", "last_detected_at"]:
        datetimes = pd.to_datetime(df[column], utc=True, errors="coerce")
        df[column + "_local"] = datetimes.dt.tz_convert(timezone_str).dt.strftime("%d/%m/%Y %H:%M:%S")
        df[column + "_local"] = df[column + "_local"].fillna("-")

    df["status_priority"] = df["status"].map(STATUS_PRIORITY).fillna(0)
    df["severity_priority"] = df["status_label"].map(SEVERITY_PRIORITY).fillna(0)
    return df.sort_values(["status_priority", "severity_priority", "last_detected_at"], ascending=[False, False, False])


def csv_bytes(df: pd.DataFrame) -> bytes:
    return (
        df.drop(columns=["status_priority", "severity_priority"], errors="ignore")
        .to_csv(index=False, sep=";", encoding="utf-8-sig")
        .encode("utf-8-sig")
    )


def txt_bytes(df: pd.DataFrame) -> bytes:
    out = df.drop(columns=["status_priority", "severity_priority"], errors="ignore")
    return out.to_string(index=False).encode("utf-8") if not out.empty else b"Sem alertas."


def render_kpis(df: pd.DataFrame) -> None:
    cols = st.columns(6)
    cols[0].metric("Eventos", len(df))
    cols[1].metric("Abertos", int((df["status"] == "open").sum()) if not df.empty else 0)
    cols[2].metric("Cientes", int((df["status"] == "acknowledged").sum()) if not df.empty else 0)
    cols[3].metric("Em tratamento", int((df["status"] == "in_progress").sum()) if not df.empty else 0)
    cols[4].metric("Críticos", int(df["status_label"].isin(["CRÍTICO", "CRITICO"]).sum()) if not df.empty else 0)
    cols[5].metric(
        "Sem comunicação",
        int(df["status_label"].isin(["SEM COMUNICAÇÃO", "SEM COMUNICACAO"]).sum()) if not df.empty else 0,
    )


def render_operational_status(df: pd.DataFrame) -> None:
    if df.empty:
        return

    open_count = int((df["status"] == "open").sum())
    critical_count = int(df["status_label"].isin(["CRÍTICO", "CRITICO"]).sum())
    communication_count = int(df["status_label"].isin(["SEM COMUNICAÇÃO", "SEM COMUNICACAO"]).sum())

    if critical_count > 0:
        st.error(f"Existem {critical_count} evento(s) crítico(s) exigindo atenção imediata.")
    elif communication_count > 0:
        st.warning(f"Existem {communication_count} evento(s) sem comunicação exigindo atuação de Automação/TI.")
    elif open_count > 0:
        st.warning(f"Existem {open_count} evento(s) aberto(s) aguardando tratamento.")
    else:
        st.success("Não há eventos abertos pendentes no filtro selecionado.")


def render_escalation_matrix(escalation_data: dict[str, Any]) -> None:
    with st.expander("Matriz de escalonamento de alertas", expanded=True):
        st.dataframe(escalation_matrix_rows(escalation_data), width="stretch", hide_index=True)


def render_cards(df: pd.DataFrame) -> None:
    st.subheader("Eventos priorizados")

    for row in df.head(8).itertuples():
        color = STATUS_COLORS.get(str(row.status_label).upper(), "#7F8C8D")
        st.markdown(
            f"""
            <div style="border-left:8px solid {color};background:white;border-radius:8px;
                        padding:12px 14px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);">
              <b>{row.asset_name}</b><br>
              Evento: <b>{pretty_metric(row.metric)}</b><br>
              Severidade: <b style="color:{color};">{row.status_label}</b> |
              Tratamento: <b>{STATUS_PT.get(row.status, row.status)}</b><br>
              Valor: <b>{row.value}</b> | Limite: <b>{row.threshold}</b><br>
              Destino: <b>{row.escalation_recipients}</b> | Canais: <b>{row.escalation_channels}</b><br>
              Política: {row.escalation_repeat_policy}<br>
              Primeira detecção: {getattr(row, "first_detected_at_local", "-")}<br>
              Ação recomendada: {row.recommended_action}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_detail(repo: AlertsRepository, df: pd.DataFrame) -> None:
    st.subheader("Tratamento do evento")
    if df.empty:
        return

    option_rows = list(df.reset_index(drop=True).itertuples())
    options = [
        f"{index + 1}. {row.asset_name} | {pretty_metric(row.metric)} | {row.status_label} | "
        f"{STATUS_PT.get(row.status, row.status)}"
        for index, row in enumerate(option_rows)
    ]
    selected_index = st.selectbox("Selecionar evento", range(len(options)), format_func=lambda index: options[index])
    row = df.reset_index(drop=True).iloc[int(selected_index)]
    full = repo.get_alert(
        str(row["tenant_asset"]),
        str(row["alert_key"]),
        pk=str(row["pk"]) if row.get("pk") else None,
        sk=str(row["sk"]) if row.get("sk") else None,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Ativo", full.get("asset_name", full.get("asset_id", row.get("asset_name"))))
    c2.metric("Métrica", pretty_metric(full.get("metric", row.get("metric"))))
    c3.metric("Severidade", full.get("status_label", row.get("status_label")))
    st.markdown(f"**Ação recomendada:** {full.get('recommended_action', row.get('recommended_action', '-'))}")
    st.markdown(f"**Última observação:** {full.get('last_note', full.get('note', row.get('last_note', '-')))}")
    st.markdown(f"**Matriz de escalonamento:** {row.get('escalation_recipients', '-')}")
    st.markdown(f"**Canais previstos:** {row.get('escalation_channels', '-')}")
    st.markdown(f"**Política:** {row.get('escalation_repeat_policy', '-')}")

    with st.expander("Timeline do evento", expanded=False):
        timeline = full.get("timeline", [])
        if timeline:
            st.dataframe(pd.DataFrame(timeline), width="stretch", hide_index=True)
        else:
            st.info("Sem timeline registrada.")

    with st.form("update_alert_status"):
        new_status = st.selectbox(
            "Novo status",
            ["acknowledged", "in_progress", "resolved", "closed"],
            format_func=lambda value: STATUS_PT.get(value, value),
        )
        user = st.text_input("Responsável", value="operador_demo")
        note = st.text_area("Observação")
        action = st.text_area("Ação tomada")
        ok = st.form_submit_button(
            "Registrar atualização do evento",
            type="primary",
            width="stretch",
        )

    if ok:
        repo.update_status(
            str(row["tenant_asset"]),
            str(row["alert_key"]),
            new_status,
            user,
            note,
            action,
            pk=str(row["pk"]) if row.get("pk") else None,
            sk=str(row["sk"]) if row.get("sk") else None,
        )
        record_sensitive_action(
            "alert.update_status",
            target=str(row["alert_key"]),
            tenant_id=str(row["tenant_asset"]).split("#", 1)[0],
            details={
                "tenant_asset": str(row["tenant_asset"]),
                "new_status": new_status,
                "responsavel": user,
                "asset_id": row.get("asset_id"),
                "metric": row.get("metric"),
            },
        )
        st.success(f"Evento atualizado para {STATUS_PT.get(new_status, new_status)}.")
        st.rerun()


def render_manual_alert(repo: AlertsRepository, tenant_id: str, plant_id: str, assets: list[dict[str, Any]]) -> None:
    with st.expander("Criar evento manual", expanded=False):
        options = [f"{asset.get('asset_id')} - {asset.get('asset_name', asset.get('asset_id'))}" for asset in assets]

        with st.form("manual_alert"):
            if options:
                selected = st.selectbox("Ativo", options)
                asset_id, asset_name = selected.split(" - ", 1)
            else:
                asset_id = st.text_input("Asset ID")
                asset_name = st.text_input("Nome do ativo")

            metric = st.text_input("Métrica/evento", value="inspecao_visual")
            severity = st.selectbox("Severidade", ["ATENÇÃO", "ALERTA", "CRÍTICO", "SEM COMUNICAÇÃO"])
            value = st.number_input("Valor observado", value=0.0)
            threshold = st.number_input("Limite/referência", value=0.0)
            recommended_action = st.text_area("Ação recomendada", value=DEFAULT_MANUAL_RECOMMENDED_ACTION)
            user = st.text_input("Criado por", value="operador_demo")
            note = st.text_area("Observação inicial")
            ok = st.form_submit_button("Criar evento")

        if ok:
            if not recommended_action.strip():
                st.error("Informe uma ação recomendada antes de criar o evento.")
                st.stop()

            repo.create_manual_alert(
                tenant_id,
                plant_id,
                asset_id,
                asset_name,
                metric,
                severity,
                value,
                threshold,
                recommended_action,
                user,
                note,
            )
            record_sensitive_action(
                "alert.create_manual",
                target=f"{asset_id}#{metric}",
                tenant_id=tenant_id,
                details={
                    "plant_id": plant_id,
                    "asset_id": asset_id,
                    "severity": severity,
                    "metric": metric,
                    "created_by": user,
                },
            )
            st.success("Evento manual criado.")
            st.rerun()


def render_alerts_center(
    tenant_id: str,
    plant_id: str,
    assets: list[dict[str, Any]] | None = None,
    timezone_str: str = "America/Sao_Paulo",
) -> None:
    st.header("Central de Alertas e Eventos")
    st.caption("Detectar -> registrar -> reconhecer ciência -> tratar -> resolver -> fechar -> auditar.")
    assets = assets or []
    repo = create_alerts_repository_from_env()
    escalation_data = EscalationRepository().load()

    asset_options = ["Todos"] + [
        f"{asset.get('asset_id')} - {asset.get('asset_name', asset.get('asset_id'))}" for asset in assets
    ]
    c1, c2, c3 = st.columns(3)

    with c1:
        status = st.selectbox(
            "Status de tratamento",
            ["Todos", "open", "acknowledged", "in_progress", "resolved", "closed"],
            format_func=lambda value: STATUS_PT.get(value, value),
        )

    with c2:
        asset_selection = st.selectbox("Ativo", asset_options)

    with c3:
        severity = st.selectbox("Severidade", ["Todas", "ATENÇÃO", "ALERTA", "CRÍTICO", "SEM COMUNICAÇÃO"])

    asset_id = None if asset_selection == "Todos" else asset_selection.split(" - ", 1)[0]
    data = repo.list_alerts(tenant_id, plant_id, asset_id, None if status == "Todos" else status)
    df = alerts_df(data, timezone_str, escalation_data)

    if not df.empty and severity != "Todas":
        if severity == "CRÍTICO":
            df = df[df["status_label"].isin(["CRÍTICO", "CRITICO"])]
        elif severity == "SEM COMUNICAÇÃO":
            df = df[df["status_label"].isin(["SEM COMUNICAÇÃO", "SEM COMUNICACAO"])]
        else:
            df = df[df["status_label"] == severity]

    render_operational_status(df)
    render_kpis(df)
    render_escalation_matrix(escalation_data)
    if df.empty:
        st.info("Nenhum evento encontrado para os filtros atuais.")
        render_manual_alert(repo, tenant_id, plant_id, assets)
        return

    st.divider()
    left, right = st.columns([1, 1])

    with left:
        render_cards(df)

    with right:
        st.subheader("Resumo por status")
        summary = df.groupby(["status", "status_label"]).agg(
            quantidade=("alert_id", "count"),
            ativos_distintos=("asset_id", "nunique"),
        ).reset_index()
        summary["tratamento"] = summary["status"].map(STATUS_PT).fillna(summary["status"])
        summary = summary[
            [
                "tratamento",
                "status_label",
                "quantidade",
                "ativos_distintos",
            ]
        ]
        st.dataframe(summary, width="stretch", hide_index=True)

    st.divider()
    render_detail(repo, df)

    st.divider()
    st.subheader("Tabela de eventos")
    columns = [
        "asset_id",
        "asset_name",
        "metric",
        "value",
        "threshold",
        "status_label",
        "status",
        "first_detected_at_local",
        "last_detected_at_local",
        "recommended_action",
        "escalation_recipients",
        "escalation_channels",
        "escalation_repeat_policy",
        "last_note",
        "last_action_taken",
    ]
    st.dataframe(df[[column for column in columns if column in df.columns]], width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    c1.download_button(
        "Exportar CSV",
        data=csv_bytes(df),
        file_name="alertas_eventos.csv",
        mime="text/csv",
        width="stretch",
    )
    c2.download_button(
        "Exportar TXT",
        data=txt_bytes(df),
        file_name="alertas_eventos.txt",
        mime="text/plain",
        width="stretch",
    )

    render_manual_alert(repo, tenant_id, plant_id, assets)
