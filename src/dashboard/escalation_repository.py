from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_ESCALATION_DATA: dict[str, Any] = {
    "rules": [
        {
            "rule_id": "attention_dashboard_only",
            "severity": "ATENÇÃO",
            "status_label": "ATENÇÃO",
            "enabled": True,
            "channel_ids": ["dashboard"],
            "notify_channels": ["dashboard"],
            "contact_group_ids": ["operador_local"],
            "target_groups": ["operador_local"],
            "metric": "*",
            "asset_criticality": "*",
            "notify_when_status": ["open"],
            "delay_minutes": 0,
            "repeat_after_minutes": 0,
            "repeat_minutes": 0,
            "escalate_after_minutes": 0,
            "escalate_to_group_ids": [],
            "escalate_to_groups": [],
            "message_template": "ATENÇÃO — {asset_name}: {metric_label} em {value}. Ação recomendada: {recommended_action}",
            "description": "Eventos de atenção permanecem apenas no dashboard, sem notificação externa.",
        },
        {
            "rule_id": "alert_maintenance_telegram",
            "severity": "ALERTA",
            "status_label": "ALERTA",
            "enabled": True,
            "channel_ids": ["dashboard", "telegram"],
            "notify_channels": ["dashboard", "telegram"],
            "contact_group_ids": ["manutencao"],
            "target_groups": ["manutencao"],
            "metric": "*",
            "asset_criticality": "*",
            "notify_when_status": ["open"],
            "delay_minutes": 0,
            "repeat_after_minutes": 30,
            "repeat_minutes": 30,
            "escalate_after_minutes": 60,
            "escalate_to_group_ids": ["supervisor_manutencao"],
            "escalate_to_groups": ["supervisor_manutencao"],
            "message_template": "ALERTA - {asset_name} ({area}): {metric_label}={value}, limite={threshold}. Ação: {recommended_action}",
            "description": "Alertas vão para manutenção e repetem se permanecerem abertos.",
        },
        {
            "rule_id": "critical_immediate_escalation",
            "severity": "CRÍTICO",
            "status_label": "CRÍTICO",
            "enabled": True,
            "channel_ids": ["dashboard", "telegram", "whatsapp"],
            "notify_channels": ["dashboard", "telegram", "whatsapp"],
            "contact_group_ids": ["manutencao", "gestor_planta"],
            "target_groups": ["manutencao", "gestor_planta"],
            "metric": "*",
            "asset_criticality": "*",
            "notify_when_status": ["open"],
            "delay_minutes": 0,
            "repeat_after_minutes": 10,
            "repeat_minutes": 10,
            "escalate_after_minutes": 20,
            "escalate_to_group_ids": ["gerencia_industrial"],
            "escalate_to_groups": ["gerencia_industrial"],
            "message_template": "CRÍTICO - {asset_name} ({area}). {metric_label}={value}, limite={threshold}. Ação imediata: {recommended_action}",
            "description": "Eventos críticos geram notificação imediata e escalonamento rápido.",
        },
        {
            "rule_id": "communication_loss_automation",
            "severity": "SEM COMUNICAÇÃO",
            "status_label": "SEM COMUNICAÇÃO",
            "enabled": True,
            "channel_ids": ["dashboard", "telegram"],
            "notify_channels": ["dashboard", "telegram"],
            "contact_group_ids": ["automacao_ti"],
            "target_groups": ["automacao_ti"],
            "metric": "*",
            "asset_criticality": "*",
            "notify_when_status": ["open"],
            "delay_minutes": 5,
            "repeat_after_minutes": 30,
            "repeat_minutes": 30,
            "escalate_after_minutes": 60,
            "escalate_to_group_ids": ["supervisor_manutencao"],
            "escalate_to_groups": ["supervisor_manutencao"],
            "message_template": "SEM COMUNICAÇÃO - {asset_name} ({area}). Última leitura: {last_detected_at}. Verificar sensor, rede, gateway e bridge.",
            "description": "Eventos de comunicação são direcionados para automação/TI.",
        },
    ],
    "contact_groups": [
        {
            "group_id": "operador_local",
            "name": "Operador local",
            "group_name": "Operador local",
            "responsibility": "Receber ocorrências operacionais e registrar ciência no dashboard.",
            "description": "Equipe operacional da área.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Operador demo", "role": "Operação", "channel_ref": "dashboard"}],
        },
        {
            "group_id": "manutencao",
            "name": "Manutenção",
            "group_name": "Manutenção",
            "responsibility": "Avaliar condição do ativo, planejar intervenção e registrar ação tomada.",
            "description": "Equipe de manutenção.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Técnico manutenção demo", "role": "Manutenção", "channel_ref": "telegram"}],
        },
        {
            "group_id": "gestao_manutencao",
            "name": "Gestor de manutenção",
            "group_name": "Gestor de manutenção",
            "responsibility": "Priorizar recursos e autorizar intervenção em eventos críticos.",
            "description": "Responsável por priorização técnica e gerencial.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Gestor demo", "role": "Gestão", "channel_ref": "whatsapp"}],
        },
        {
            "group_id": "supervisor_manutencao",
            "name": "Supervisor de manutenção",
            "group_name": "Supervisor de manutenção",
            "responsibility": "Priorizar atendimento técnico e acompanhar reincidências.",
            "description": "Responsável por priorização técnica.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Supervisor demo", "role": "Supervisão", "channel_ref": "telegram"}],
        },
        {
            "group_id": "gestor_planta",
            "name": "Gestor da planta",
            "group_name": "Gestor da planta",
            "responsibility": "Acompanhar eventos críticos e decisões operacionais da unidade.",
            "description": "Responsável gerencial da unidade.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Gestor planta demo", "role": "Gestão", "channel_ref": "whatsapp"}],
        },
        {
            "group_id": "gerencia_industrial",
            "name": "Gerência industrial",
            "group_name": "Gerência industrial",
            "responsibility": "Escalonamento executivo para eventos críticos não tratados.",
            "description": "Escalonamento executivo para eventos críticos.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Gerência demo", "role": "Gerência", "channel_ref": "whatsapp"}],
        },
        {
            "group_id": "automacao_ti",
            "name": "Automação/TI",
            "group_name": "Automação/TI",
            "responsibility": "Restabelecer comunicação de campo, gateway, rede ou integração.",
            "description": "Rede, gateway, sensores e conectividade.",
            "telegram_chat_id": "",
            "whatsapp_to": "",
            "email_to": "",
            "contacts": [{"name": "Automação demo", "role": "Automação/TI", "channel_ref": "telegram"}],
        },
    ],
    "channels": [
        {
            "channel_id": "dashboard",
            "name": "Dashboard",
            "enabled": True,
            "configured": True,
            "description": "Registro visual e operacional dentro da Central de Alertas.",
        },
        {
            "channel_id": "telegram",
            "name": "Telegram",
            "enabled": True,
            "configured": False,
            "description": "Canal planejado para MVP de notificações externas.",
        },
        {
            "channel_id": "whatsapp",
            "name": "WhatsApp",
            "enabled": True,
            "configured": False,
            "description": "Canal planejado para escalonamento executivo posterior.",
        },
        {
            "channel_id": "email",
            "name": "E-mail",
            "enabled": False,
            "configured": False,
            "description": "Canal corporativo opcional.",
        },
    ],
}


def default_store_path() -> Path:
    return Path(__file__).with_name("escalation_rules_store.json")


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int_minutes(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def normalize_escalation_data(data: dict[str, Any] | None) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_ESCALATION_DATA)

    if not isinstance(data, dict):
        return normalized

    for key in ["rules", "contact_groups"]:
        if isinstance(data.get(key), list):
            normalized[key] = deepcopy(data[key])

    channels = data.get("channels")
    if isinstance(channels, list):
        normalized["channels"] = deepcopy(channels)
    elif isinstance(channels, dict):
        normalized["channels"] = [
            {
                "channel_id": channel_id,
                "name": str(channel_id).replace("_", " ").title(),
                **(channel_data if isinstance(channel_data, dict) else {}),
            }
            for channel_id, channel_data in channels.items()
        ]

    for rule in normalized["rules"]:
        rule["rule_id"] = str(rule.get("rule_id") or rule.get("severity") or rule.get("status_label") or "").strip()
        rule["severity"] = str(rule.get("severity") or rule.get("status_label") or "").strip()
        rule["status_label"] = str(rule.get("status_label") or rule.get("severity") or "").strip()
        rule["enabled"] = bool(rule.get("enabled", True))
        channel_ids = _list(rule.get("channel_ids")) or _list(rule.get("notify_channels"))
        contact_group_ids = _list(rule.get("contact_group_ids")) or _list(rule.get("target_groups"))
        escalate_to_group_ids = _list(rule.get("escalate_to_group_ids")) or _list(rule.get("escalate_to_groups"))
        rule["channel_ids"] = [str(item) for item in channel_ids if str(item)]
        rule["notify_channels"] = list(rule["channel_ids"])
        rule["contact_group_ids"] = [str(item) for item in contact_group_ids if str(item)]
        rule["target_groups"] = list(rule["contact_group_ids"])
        rule["escalate_to_group_ids"] = [str(item) for item in escalate_to_group_ids if str(item)]
        rule["escalate_to_groups"] = list(rule["escalate_to_group_ids"])
        rule["metric"] = str(rule.get("metric") or "*")
        rule["asset_criticality"] = str(rule.get("asset_criticality") or "*")
        rule["notify_when_status"] = [str(item) for item in (_list(rule.get("notify_when_status")) or ["open"])]
        rule["delay_minutes"] = _int_minutes(rule.get("delay_minutes"))
        rule["repeat_after_minutes"] = _int_minutes(
            rule.get("repeat_after_minutes") if "repeat_after_minutes" in rule else rule.get("repeat_minutes")
        )
        rule["repeat_minutes"] = rule["repeat_after_minutes"]
        rule["escalate_after_minutes"] = _int_minutes(rule.get("escalate_after_minutes"))
        rule["message_template"] = str(rule.get("message_template") or "")
        rule["description"] = str(rule.get("description") or "")

        if rule["rule_id"] == "attention_dashboard_only" or rule["status_label"].upper() in {"ATENÇÃO", "ATENCAO"}:
            rule["channel_ids"] = ["dashboard"]
            rule["notify_channels"] = ["dashboard"]
            rule["contact_group_ids"] = ["operador_local"]
            rule["target_groups"] = ["operador_local"]
            rule["notify_when_status"] = ["open"]
            rule["delay_minutes"] = 0
            rule["repeat_after_minutes"] = 0
            rule["repeat_minutes"] = 0
            rule["escalate_after_minutes"] = 0
            rule["escalate_to_group_ids"] = []
            rule["escalate_to_groups"] = []
            if not rule["message_template"]:
                rule["message_template"] = (
                    "ATENÇÃO — {asset_name}: {metric_label} em {value}. "
                    "Ação recomendada: {recommended_action}"
                )
            rule["description"] = "Eventos de atenção permanecem apenas no dashboard, sem notificação externa."

    for group in normalized["contact_groups"]:
        group["group_id"] = str(group.get("group_id") or group.get("name") or "").strip()
        group["name"] = str(group.get("name") or group.get("group_name") or group.get("group_id") or "").strip()
        group["group_name"] = group["name"]
        group["responsibility"] = str(group.get("responsibility") or group.get("description") or "")
        group["description"] = str(group.get("description") or group.get("responsibility") or "")
        group["telegram_chat_id"] = str(group.get("telegram_chat_id") or "")
        group["whatsapp_to"] = str(group.get("whatsapp_to") or "")
        group["email_to"] = str(group.get("email_to") or "")
        group["contacts"] = _list(group.get("contacts"))

    for channel in normalized["channels"]:
        channel["channel_id"] = str(channel.get("channel_id") or channel.get("name") or "").strip()
        channel["name"] = str(channel.get("name") or channel.get("channel_id") or "").strip()
        channel["enabled"] = bool(channel.get("enabled", True))
        channel["configured"] = bool(channel.get("configured", False))
        channel["description"] = str(channel.get("description") or "")

    return normalized


class EscalationRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = self._resolve_path(path)

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is None or str(path).strip() == "":
            return default_store_path()

        candidate = Path(path)
        if candidate.is_absolute():
            return candidate

        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return cwd_candidate

        return Path(__file__).parent / candidate

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return normalize_escalation_data(None)

        return normalize_escalation_data(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_escalation_data(data)
        self.path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

    def rules(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("rules", []))

    def contact_groups(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("contact_groups", []))

    def channels(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("channels", []))

    def upsert_rule(self, rule: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
        loaded = normalize_escalation_data(data or self.load())
        rule_id = str(rule.get("rule_id") or "").strip()
        rules = loaded["rules"]

        for index, existing in enumerate(rules):
            if existing.get("rule_id") == rule_id:
                rules[index] = {**existing, **rule}
                break
        else:
            rules.append(rule)

        self.save(loaded)
        return self.load()

    def upsert_contact_group(self, group: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
        loaded = normalize_escalation_data(data or self.load())
        group_id = str(group.get("group_id") or "").strip()
        groups = loaded["contact_groups"]

        for index, existing in enumerate(groups):
            if existing.get("group_id") == group_id:
                groups[index] = {**existing, **group}
                break
        else:
            groups.append(group)

        self.save(loaded)
        return self.load()

    def upsert_channel(self, channel: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
        loaded = normalize_escalation_data(data or self.load())
        channel_id = str(channel.get("channel_id") or "").strip()
        channels = loaded["channels"]

        for index, existing in enumerate(channels):
            if existing.get("channel_id") == channel_id:
                channels[index] = {**existing, **channel}
                break
        else:
            channels.append(channel)

        self.save(loaded)
        return self.load()
