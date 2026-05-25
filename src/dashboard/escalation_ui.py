from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    from dashboard.alerts_repository import AlertsRepository
    from dashboard.escalation_engine import escalation_matrix_rows, simulate_alerts
    from dashboard.escalation_repository import EscalationRepository
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alerts_repository import AlertsRepository
    from src.dashboard.escalation_engine import escalation_matrix_rows, simulate_alerts
    from src.dashboard.escalation_repository import EscalationRepository


def _ids(items: list[dict[str, Any]], id_key: str) -> list[str]:
    return [str(item.get(id_key)) for item in items if item.get(id_key)]


def _label(item: dict[str, Any], id_key: str) -> str:
    return f"{item.get(id_key)} - {item.get('name', item.get(id_key))}"


def _contacts_text(contacts: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{contact.get('name', '')};{contact.get('role', '')};{contact.get('channel_ref', '')}" for contact in contacts
    )


def _parse_contacts(text: str) -> list[dict[str, str]]:
    contacts: list[dict[str, str]] = []

    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        name, role, channel_ref = [part.strip() for part in (raw.split(";") + ["", ""])[:3]]
        contacts.append({"name": name, "role": role, "channel_ref": channel_ref})

    return contacts


def restore_default_matrix(repo: EscalationRepository) -> None:
    default_path = Path(__file__).with_name("escalation_rules_store_default.json")

    if not default_path.exists():
        st.error("Arquivo escalation_rules_store_default.json não encontrado.")
        return

    data = json.loads(default_path.read_text(encoding="utf-8"))
    repo.save(data)
    st.success("Matriz de escalonamento restaurada para o padrão seguro.")
    st.rerun()


def render_rules_tab(repo: EscalationRepository, data: dict[str, Any]) -> None:
    st.subheader("Regras")

    c_restore, c_hint = st.columns([1, 3])
    with c_restore:
        if st.button("Restaurar padrão seguro", use_container_width=True):
            restore_default_matrix(repo)
    with c_hint:
        st.caption("Padrão seguro: ATENÇÃO apenas no dashboard; ALERTA/CRÍTICO podem acionar canais externos.")

    st.dataframe(escalation_matrix_rows(data), use_container_width=True, hide_index=True)

    rules = data.get("rules", [])
    channels = data.get("channels", [])
    groups = data.get("contact_groups", [])

    if not rules:
        st.info("Nenhuma regra configurada.")
        return

    with st.expander("Editar regra", expanded=False):
        selected_rule_id = st.selectbox(
            "Regra",
            options=[str(rule.get("rule_id")) for rule in rules],
            format_func=lambda rule_id: next(
                (
                    f"{rule.get('severity')} - {rule.get('rule_id')}"
                    for rule in rules
                    if str(rule.get("rule_id")) == str(rule_id)
                ),
                str(rule_id),
            ),
        )
        rule = next(rule for rule in rules if str(rule.get("rule_id")) == str(selected_rule_id))
        channel_ids = _ids(channels, "channel_id")
        group_ids = _ids(groups, "group_id")

        with st.form(f"edit_rule_{selected_rule_id}"):
            enabled = st.checkbox("Regra ativa", value=bool(rule.get("enabled", True)))
            metric = st.text_input("Métrica específica ou *", value=str(rule.get("metric") or "*"))
            asset_criticality = st.text_input("Criticidade específica ou *", value=str(rule.get("asset_criticality") or "*"))
            notify_statuses = st.multiselect(
                "Status que disparam a regra",
                options=["open", "acknowledged", "in_progress", "resolved", "closed"],
                default=[
                    status
                    for status in rule.get("notify_when_status", ["open"])
                    if status in {"open", "acknowledged", "in_progress", "resolved", "closed"}
                ]
                or ["open"],
            )
            selected_channels = st.multiselect(
                "Canais",
                options=channel_ids,
                default=[item for item in rule.get("channel_ids", []) if item in channel_ids],
            )
            selected_groups = st.multiselect(
                "Grupos de destino",
                options=group_ids,
                default=[item for item in rule.get("contact_group_ids", []) if item in group_ids],
            )
            delay = st.number_input(
                "Aguardar antes de notificar (min)",
                min_value=0,
                max_value=1440,
                value=int(rule.get("delay_minutes") or 0),
            )
            repeat = st.number_input(
                "Repetir após quantos minutos",
                min_value=0,
                max_value=1440,
                value=int(rule.get("repeat_after_minutes") or 0),
            )
            escalate = st.number_input(
                "Escalonar após quantos minutos",
                min_value=0,
                max_value=1440,
                value=int(rule.get("escalate_after_minutes") or 0),
            )
            escalate_groups = st.multiselect(
                "Escalonar para",
                options=group_ids,
                default=[item for item in rule.get("escalate_to_group_ids", []) if item in group_ids],
            )
            message_template = st.text_area(
                "Modelo da mensagem",
                value=str(rule.get("message_template") or "{status_label} - {asset_name}: {metric_label}={value}."),
            )
            description = st.text_area("Descrição da regra", value=str(rule.get("description") or ""))
            submitted = st.form_submit_button("Salvar regra", type="primary", use_container_width=True)

        if submitted:
            repo.upsert_rule(
                {
                    **rule,
                    "enabled": enabled,
                    "metric": metric or "*",
                    "asset_criticality": asset_criticality or "*",
                    "notify_when_status": notify_statuses or ["open"],
                    "channel_ids": selected_channels,
                    "notify_channels": selected_channels,
                    "contact_group_ids": selected_groups,
                    "target_groups": selected_groups,
                    "delay_minutes": int(delay),
                    "repeat_after_minutes": int(repeat),
                    "repeat_minutes": int(repeat),
                    "escalate_after_minutes": int(escalate),
                    "escalate_to_group_ids": escalate_groups,
                    "escalate_to_groups": escalate_groups,
                    "message_template": message_template,
                    "description": description,
                },
                data,
            )
            st.success("Regra salva.")
            st.rerun()


def render_groups_tab(repo: EscalationRepository, data: dict[str, Any]) -> None:
    st.subheader("Grupos de Contato")
    groups = data.get("contact_groups", [])
    rows = [
        {
            "group_id": group.get("group_id"),
            "nome": group.get("name"),
            "responsabilidade": group.get("responsibility"),
            "telegram": group.get("telegram_chat_id"),
            "whatsapp": group.get("whatsapp_to"),
            "email": group.get("email_to"),
            "contatos": len(group.get("contacts", [])),
        }
        for group in groups
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if not groups:
        return

    with st.expander("Editar grupo", expanded=False):
        selected_group_id = st.selectbox(
            "Grupo",
            options=[str(group.get("group_id")) for group in groups],
            format_func=lambda group_id: next(
                (_label(group, "group_id") for group in groups if str(group.get("group_id")) == str(group_id)),
                str(group_id),
            ),
        )
        group = next(group for group in groups if str(group.get("group_id")) == str(selected_group_id))

        with st.form(f"edit_group_{selected_group_id}"):
            name = st.text_input("Nome", value=str(group.get("name") or ""))
            responsibility = st.text_area("Responsabilidade", value=str(group.get("responsibility") or ""))
            telegram_chat_id = st.text_input("Telegram Chat ID", value=str(group.get("telegram_chat_id") or ""))
            whatsapp_to = st.text_input("WhatsApp destino", value=str(group.get("whatsapp_to") or ""))
            email_to = st.text_input("E-mail destino", value=str(group.get("email_to") or ""))
            contacts = st.text_area(
                "Contatos",
                value=_contacts_text(group.get("contacts", [])),
                help="Use uma linha por contato no formato: nome;função;canal",
            )
            submitted = st.form_submit_button("Salvar grupo", type="primary", use_container_width=True)

        if submitted:
            repo.upsert_contact_group(
                {
                    **group,
                    "name": name,
                    "group_name": name,
                    "responsibility": responsibility,
                    "description": responsibility,
                    "telegram_chat_id": telegram_chat_id,
                    "whatsapp_to": whatsapp_to,
                    "email_to": email_to,
                    "contacts": _parse_contacts(contacts),
                },
                data,
            )
            st.success("Grupo salvo.")
            st.rerun()


def render_channels_tab(repo: EscalationRepository, data: dict[str, Any]) -> None:
    st.subheader("Canais")
    channels = data.get("channels", [])
    rows = [
        {
            "channel_id": channel.get("channel_id"),
            "nome": channel.get("name"),
            "ativo": channel.get("enabled"),
            "configurado": channel.get("configured"),
            "referência": channel.get("bot_token_ref") or channel.get("token_ref") or channel.get("smtp_ref") or "",
            "descrição": channel.get("description"),
        }
        for channel in channels
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if not channels:
        return

    with st.expander("Editar canal", expanded=False):
        selected_channel_id = st.selectbox(
            "Canal",
            options=[str(channel.get("channel_id")) for channel in channels],
            format_func=lambda channel_id: next(
                (
                    _label(channel, "channel_id")
                    for channel in channels
                    if str(channel.get("channel_id")) == str(channel_id)
                ),
                str(channel_id),
            ),
        )
        channel = next(channel for channel in channels if str(channel.get("channel_id")) == str(selected_channel_id))

        with st.form(f"edit_channel_{selected_channel_id}"):
            name = st.text_input("Nome", value=str(channel.get("name") or ""))
            enabled = st.checkbox("Canal ativo na matriz", value=bool(channel.get("enabled", True)))
            configured = st.checkbox("Canal tecnicamente configurado", value=bool(channel.get("configured", False)))
            secret_ref = st.text_input(
                "Referência de segredo/configuração",
                value=str(channel.get("bot_token_ref") or channel.get("token_ref") or channel.get("smtp_ref") or ""),
            )
            description = st.text_area("Descrição", value=str(channel.get("description") or ""))
            submitted = st.form_submit_button("Salvar canal", type="primary", use_container_width=True)

        if submitted:
            ref_key = "bot_token_ref" if selected_channel_id == "telegram" else "token_ref"
            if selected_channel_id == "email":
                ref_key = "smtp_ref"

            repo.upsert_channel(
                {
                    **channel,
                    "name": name,
                    "enabled": enabled,
                    "configured": configured,
                    ref_key: secret_ref,
                    "description": description,
                },
                data,
            )
            st.success("Canal salvo.")
            st.rerun()


def render_simulation_tab(
    data: dict[str, Any],
    *,
    tenant_id: str,
    plant_id: str,
    assets: list[dict[str, Any]],
) -> None:
    st.subheader("Simulação")
    alerts_repo = AlertsRepository()
    asset_options = ["Todos"] + [
        f"{asset.get('asset_id')} - {asset.get('asset_name', asset.get('asset_id'))}" for asset in assets
    ]
    status = st.selectbox("Status", ["Todos", "open", "acknowledged", "in_progress", "resolved", "closed"])
    asset_selection = st.selectbox("Ativo", asset_options)
    asset_id = None if asset_selection == "Todos" else asset_selection.split(" - ", 1)[0]

    alerts = alerts_repo.list_alerts(tenant_id, plant_id, asset_id, None if status == "Todos" else status)
    decisions = simulate_alerts(alerts, data, assets=assets)

    if not decisions:
        st.info("Nenhum alerta atual encontrado para simular.")
        return

    rows = [
        {
            "regra": decision["rule_id"],
            "ativo": decision["asset_name"],
            "severidade": decision["severity"],
            "métrica": decision["metric_label"],
            "canais": decision["channels"],
            "grupos de destino": decision["contact_groups"],
            "notificação_liberada": decision["notification_due"],
            "idade_min": decision["age_minutes"],
            "deve_repetir": decision["should_repeat"],
            "deve_escalar": decision["should_escalate"],
            "mensagem": decision["message"],
        }
        for decision in decisions
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    escalations = int(df["deve_escalar"].sum()) if not df.empty else 0
    repeats = int(df["deve_repetir"].sum()) if not df.empty else 0

    if escalations:
        st.error(f"{escalations} alerta(s) já cumpriram critério de escalonamento.")
    elif repeats:
        st.warning(f"{repeats} alerta(s) já cumpriram critério de repetição.")
    else:
        st.success("Nenhum alerta exige repetição ou escalonamento neste momento.")


def render_escalation_page(
    tenant_id: str,
    plant_id: str,
    assets: list[dict[str, Any]] | None = None,
) -> None:
    st.header("Matriz de Escalonamento")
    st.caption("Define qual severidade usa qual canal, grupo, repetição e escalonamento.")

    repo = EscalationRepository()
    data = repo.load()
    assets = assets or []

    rules_tab, groups_tab, channels_tab, simulation_tab = st.tabs(["Regras", "Grupos de Contato", "Canais", "Simulação"])

    with rules_tab:
        render_rules_tab(repo, data)

    with groups_tab:
        render_groups_tab(repo, data)

    with channels_tab:
        render_channels_tab(repo, data)

    with simulation_tab:
        render_simulation_tab(data, tenant_id=tenant_id, plant_id=plant_id, assets=assets)
