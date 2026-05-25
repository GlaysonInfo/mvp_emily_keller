from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

try:
    from dashboard.escalation_repository import DEFAULT_ESCALATION_DATA, normalize_escalation_data
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.escalation_repository import DEFAULT_ESCALATION_DATA, normalize_escalation_data


PENDING_STATUSES = {"open", "acknowledged", "in_progress"}
FALLBACK_RECOMMENDED_ACTION = (
    "Realizar inspeção técnica no ativo, registrar evidências visuais, verificar vibração anormal, ruído, "
    "temperatura, fixação, lubrificação e necessidade de intervenção corretiva ou preventiva."
)


def normalize_severity_label(status_label: Any) -> str:
    normalized = str(status_label or "NORMAL").strip().upper()
    aliases = {
        "ATENCAO": "ATENÇÃO",
        "ATENCAO ALTA": "ATENÇÃO",
        "ATENÇÃO ALTA": "ATENÇÃO",
        "ATENCAO MEDIA": "ATENÇÃO",
        "ATENÇÃO MEDIA": "ATENÇÃO",
        "ATENÇÃO MÉDIA": "ATENÇÃO",
        "ATENCAO BAIXA": "ATENÇÃO",
        "ATENÇÃO BAIXA": "ATENÇÃO",
        "CRITICO": "CRÍTICO",
        "SEM COMUNICACAO": "SEM COMUNICAÇÃO",
        "COMMUNICATION_LOST": "SEM COMUNICAÇÃO",
        "WARNING": "ATENÇÃO",
        "CRITICAL": "CRÍTICO",
        "NORMAL": "NORMAL",
    }
    return aliases.get(normalized, normalized)


def pretty_metric(metric: Any) -> str:
    labels = {
        "inspecao_visual": "Inspeção visual",
        "vibration_rms_mm_s": "Vibração RMS",
        "temperature_c": "Temperatura",
        "ultrasound_db": "Ultrassom",
        "health_score": "Health Score",
        "severity_score": "Severity Score",
        "rpm": "RPM",
        "communication_lost": "Perda de comunicação",
    }
    metric_text = str(metric or "-")
    return labels.get(metric_text, metric_text)


def severity_from_alert(alert: dict[str, Any]) -> str:
    if str(alert.get("alert_type") or "").lower() == "communication_lost":
        return "SEM COMUNICAÇÃO"

    status_label = alert.get("status_label")
    if status_label:
        return normalize_severity_label(status_label)

    return normalize_severity_label(alert.get("severity"))


def rule_for_severity(status_label: Any, data: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    severity = normalize_severity_label(status_label)

    for rule in loaded["rules"]:
        if normalize_severity_label(rule.get("severity") or rule.get("status_label")) == severity:
            return dict(rule)

    for rule in loaded["rules"]:
        if normalize_severity_label(rule.get("severity") or rule.get("status_label")) == "ATENÇÃO":
            return dict(rule)

    return {}


def rule_matches_alert(rule: dict[str, Any], alert: dict[str, Any], asset: dict[str, Any] | None = None) -> bool:
    if not rule.get("enabled", True):
        return False

    asset = asset or {}
    rule_severity = normalize_severity_label(rule.get("severity") or rule.get("status_label") or "*")
    alert_severity = severity_from_alert(alert)
    if rule_severity != "*" and rule_severity != alert_severity:
        return False

    rule_metric = str(rule.get("metric") or "*")
    alert_metric = str(alert.get("metric") or alert.get("alert_type") or alert.get("probable_cause") or "")
    if rule_metric != "*" and rule_metric != alert_metric:
        return False

    rule_criticality = str(rule.get("asset_criticality") or "*").upper()
    alert_criticality = str(asset.get("criticality") or alert.get("criticality") or "*").upper()
    if rule_criticality != "*" and rule_criticality != alert_criticality:
        return False

    notify_statuses = [str(status).lower() for status in rule.get("notify_when_status", ["open"])]
    if notify_statuses and str(alert.get("status") or "open").lower() not in notify_statuses:
        return False

    return True


def rule_for_alert(
    alert: dict[str, Any],
    data: dict[str, Any] | None = None,
    asset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)

    for rule in loaded["rules"]:
        if rule_matches_alert(rule, alert, asset):
            return dict(rule)

    return rule_for_severity(severity_from_alert(alert), loaded)


def _by_id(items: list[dict[str, Any]], id_key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(id_key)): item for item in items}


def _names(ids: list[str], lookup: dict[str, dict[str, Any]]) -> list[str]:
    return [str(lookup.get(item_id, {}).get("name") or item_id) for item_id in ids]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def alert_age_minutes(alert: dict[str, Any], now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    detected_at = _parse_datetime(alert.get("first_detected_at")) or _parse_datetime(alert.get("updated_at"))

    if detected_at is None:
        return 0

    return max(0, int((now - detected_at).total_seconds() // 60))


def is_pending_status(status: Any) -> bool:
    return str(status or "open").lower() in PENDING_STATUSES


def notification_due(alert: dict[str, Any], rule: dict[str, Any], now: datetime | None = None) -> bool:
    delay = int(rule.get("delay_minutes") or 0)
    return bool(rule.get("enabled", True)) and is_pending_status(alert.get("status")) and alert_age_minutes(alert, now) >= delay


def should_repeat(alert: dict[str, Any], rule: dict[str, Any], now: datetime | None = None) -> bool:
    repeat_after = int(rule.get("repeat_after_minutes") or 0)
    return notification_due(alert, rule, now) and repeat_after > 0 and (
        alert_age_minutes(alert, now) >= repeat_after
    )


def should_escalate(alert: dict[str, Any], rule: dict[str, Any], now: datetime | None = None) -> bool:
    escalate_after = int(rule.get("escalate_after_minutes") or 0)
    return notification_due(alert, rule, now) and escalate_after > 0 and str(alert.get("status") or "open").lower() == "open" and (
        alert_age_minutes(alert, now) >= escalate_after
    )


def notification_context(alert: dict[str, Any], asset: dict[str, Any] | None = None) -> dict[str, Any]:
    asset = asset or {}
    metric = alert.get("metric") or alert.get("alert_type") or alert.get("probable_cause")
    return {
        **alert,
        "asset_name": alert.get("asset_name") or asset.get("asset_name") or alert.get("asset_id") or "-",
        "area": asset.get("area", alert.get("area", "-")),
        "criticality": asset.get("criticality", alert.get("criticality", "-")),
        "metric_label": pretty_metric(metric),
        "value": alert.get("value", "-"),
        "threshold": alert.get("threshold", "-"),
        "recommended_action": alert.get("recommended_action") or FALLBACK_RECOMMENDED_ACTION,
        "last_detected_at": alert.get("last_detected_at") or alert.get("updated_at") or "-",
        "minutes_open": alert_age_minutes(alert),
        "status_label": severity_from_alert(alert),
    }


def notification_message(
    alert: dict[str, Any],
    rule: dict[str, Any],
    data: dict[str, Any] | None = None,
    asset: dict[str, Any] | None = None,
) -> str:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    channel_lookup = _by_id(loaded["channels"], "channel_id")
    group_lookup = _by_id(loaded["contact_groups"], "group_id")
    channels = " + ".join(_names(rule.get("channel_ids", []), channel_lookup))
    groups = " + ".join(_names(rule.get("contact_group_ids", []), group_lookup))
    ctx = notification_context(alert, asset)

    if rule.get("message_template"):
        try:
            return str(rule["message_template"]).format(**ctx)
        except Exception:
            pass

    return (
        f"[{ctx['status_label']}] {ctx['asset_name']} | Evento: {ctx['metric_label']} | "
        f"Destino: {groups} | Canal: {channels} | Ação: {ctx['recommended_action']}"
    )


def apply_escalation_rule(
    alert: dict[str, Any],
    data: dict[str, Any] | None = None,
    now: datetime | None = None,
    asset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    severity = severity_from_alert(alert)
    rule = rule_for_alert(alert, loaded, asset)
    channel_lookup = _by_id(loaded["channels"], "channel_id")
    group_lookup = _by_id(loaded["contact_groups"], "group_id")
    channel_ids = list(rule.get("channel_ids", []))
    group_ids = list(rule.get("contact_group_ids", []))
    escalate_to_group_ids = list(rule.get("escalate_to_group_ids", []))

    return {
        "rule_id": rule.get("rule_id", "-"),
        "rule_enabled": bool(rule.get("enabled", True)),
        "asset_id": alert.get("asset_id"),
        "asset_name": alert.get("asset_name") or alert.get("asset_id"),
        "severity": severity,
        "metric": alert.get("metric") or alert.get("alert_type") or alert.get("probable_cause"),
        "metric_label": pretty_metric(alert.get("metric") or alert.get("alert_type") or alert.get("probable_cause")),
        "status": alert.get("status", "open"),
        "channel_ids": channel_ids,
        "channels": " + ".join(_names(channel_ids, channel_lookup)),
        "contact_group_ids": group_ids,
        "contact_groups": " + ".join(_names(group_ids, group_lookup)),
        "repeat_after_minutes": int(rule.get("repeat_after_minutes") or 0),
        "escalate_after_minutes": int(rule.get("escalate_after_minutes") or 0),
        "escalate_to_group_ids": escalate_to_group_ids,
        "escalate_to_groups": " + ".join(_names(escalate_to_group_ids, group_lookup)),
        "age_minutes": alert_age_minutes(alert, now),
        "delay_minutes": int(rule.get("delay_minutes") or 0),
        "notification_due": notification_due(alert, rule, now),
        "should_repeat": should_repeat(alert, rule, now),
        "should_escalate": should_escalate(alert, rule, now),
        "message": notification_message(alert, rule, loaded, asset),
    }


def simulate_alerts(
    alerts: list[dict[str, Any]],
    data: dict[str, Any] | None = None,
    now: datetime | None = None,
    assets: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    assets_by_id = {str(asset.get("asset_id")): asset for asset in (assets or []) if asset.get("asset_id")}
    return [
        apply_escalation_rule(alert, loaded, now, assets_by_id.get(str(alert.get("asset_id"))))
        for alert in alerts
    ]


def escalation_matrix_rows(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    loaded = normalize_escalation_data(data or DEFAULT_ESCALATION_DATA)
    channel_lookup = _by_id(loaded["channels"], "channel_id")
    group_lookup = _by_id(loaded["contact_groups"], "group_id")
    rows: list[dict[str, Any]] = []

    for rule in loaded["rules"]:
        rows.append(
            {
                "Severidade": normalize_severity_label(rule.get("severity")),
                "Canal": " + ".join(_names(rule.get("channel_ids", []), channel_lookup)),
                "Destino": " + ".join(_names(rule.get("contact_group_ids", []), group_lookup)),
                "Repetição": "Não repete"
                if int(rule.get("repeat_after_minutes") or 0) == 0
                else f"{int(rule.get('repeat_after_minutes') or 0)} min",
                "Escalonamento": "Não escala"
                if int(rule.get("escalate_after_minutes") or 0) == 0
                else f"{int(rule.get('escalate_after_minutes') or 0)} min",
                "Ativa": bool(rule.get("enabled", True)),
            }
        )

    return rows
