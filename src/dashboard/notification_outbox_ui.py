from __future__ import annotations

import pandas as pd
import streamlit as st
from botocore.exceptions import ClientError

try:
    from dashboard.alerts_repository import AlertsRepository
    from dashboard.escalation_repository import EscalationRepository
    from dashboard.notification_outbox_engine import build_outbox_items, outbox_kpis
    from dashboard.notification_outbox_repository import NotificationOutboxRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alerts_repository import AlertsRepository
    from src.dashboard.escalation_repository import EscalationRepository
    from src.dashboard.notification_outbox_engine import build_outbox_items, outbox_kpis
    from src.dashboard.notification_outbox_repository import NotificationOutboxRepository


def _rows(items: list[dict]) -> list[dict]:
    return [
        {
            "status": item.get("status"),
            "tipo": item.get("kind"),
            "regra": item.get("rule_id"),
            "ativo": item.get("asset_name") or item.get("asset_id"),
            "severidade": item.get("severity"),
            "métrica": item.get("metric_label") or item.get("metric"),
            "canais": item.get("channels"),
            "grupos": item.get("contact_groups"),
            "mensagem": item.get("message"),
        }
        for item in items
    ]


def render_notification_outbox_page(
    tenant_id: str,
    plant_id: str,
    assets: list[dict] | None = None,
    escalation_path: str | None = None,
    current_states: list[dict] | None = None,
) -> None:
    st.header("Notification Outbox")
    st.caption("Fila de notificações calculada pela matriz. Nesta etapa o processamento é dry-run.")

    assets = assets or []
    alerts_repo = AlertsRepository()
    escalation_repo = EscalationRepository(escalation_path)
    outbox_repo = NotificationOutboxRepository()

    try:
        alerts = alerts_repo.list_alerts(tenant_id=tenant_id, plant_id=plant_id, status="open")
    except ClientError:
        raise

    escalation_data = escalation_repo.load()
    pending_candidates = build_outbox_items(alerts, escalation_data, assets, current_states=current_states)
    items = outbox_repo.items()
    kpis = outbox_kpis(items)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Na fila", kpis["total"])
    k2.metric("Pendentes", kpis["pending"])
    k3.metric("Dry-run", kpis["dry_run_processed"])
    k4.metric("Escalonamentos", kpis["escalations"])

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Gerar/atualizar fila de notificações", type="primary", use_container_width=True):
            added, skipped = outbox_repo.add_pending(pending_candidates)
            st.success(f"{added} notificação(ões) adicionada(s). {skipped} duplicada(s) ignorada(s).")
            st.rerun()

    with c2:
        if st.button("Processar em dry-run", use_container_width=True):
            processed = outbox_repo.mark_dry_run_processed()
            st.success(f"{processed} notificação(ões) processada(s) em dry-run.")
            st.rerun()

    st.subheader("Fila")
    if items:
        status = st.selectbox("Status da fila", ["Todos", "pending", "dry_run", "dry_run_processed"])
        visible = outbox_repo.items(status)
        st.dataframe(pd.DataFrame(_rows(visible)), use_container_width=True, hide_index=True)
    else:
        st.info("A fila ainda está vazia.")
