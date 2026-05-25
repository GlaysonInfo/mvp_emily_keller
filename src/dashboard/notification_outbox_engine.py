from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

try:
    from dashboard.escalation_engine import simulate_alerts
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.escalation_engine import simulate_alerts


NON_NOTIFIABLE_STATE_LABELS = {"", "NORMAL", "RECUPERADO"}
STATE_RECOMMENDED_ACTION = "Avaliar condição operacional do ativo e registrar ação de manutenção."


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _alert_identity(decision: dict[str, Any]) -> str:
    parts = [
        decision.get("asset_id"),
        decision.get("severity"),
        decision.get("metric"),
        decision.get("status"),
        decision.get("rule_id"),
    ]
    return "#".join(str(part or "-") for part in parts)


def _state_status_label(state: dict[str, Any]) -> str:
    return str(state.get("status_label") or "").strip().upper()


def _state_metric(state: dict[str, Any]) -> str:
    status_label = _state_status_label(state)
    mode = str(state.get("failure_mode_simulated") or state.get("mode") or "")

    if status_label in {"SEM COMUNICAÇÃO", "SEM COMUNICACAO"} or mode == "communication_lost":
        return "communication_lost"

    if mode in {"lubrication_degradation", "bearing_fault_initial"}:
        return mode

    if mode == "thermal_stress":
        return "temperature_c"

    if mode in {"mechanical_unbalance", "imbalance"}:
        return "vibration_rms_mm_s"

    return "condition_state"


def _state_value(state: dict[str, Any]) -> Any:
    for key in ["severity_score", "health_score"]:
        value = state.get(key)
        if value is not None:
            return value

    metrics = state.get("metrics")
    if isinstance(metrics, dict):
        for key in ["severity_score", "severity", "health_score"]:
            metric = metrics.get(key)
            if isinstance(metric, dict) and metric.get("value") is not None:
                return metric.get("value")
            if metric is not None:
                return metric

    return None


def normalize_current_state_as_alert(state: dict[str, Any]) -> dict[str, Any] | None:
    status_label = _state_status_label(state)

    if status_label in NON_NOTIFIABLE_STATE_LABELS:
        return None

    asset_id = state.get("asset_id")
    if not asset_id:
        return None

    tenant_id = state.get("tenant_id")
    updated_at = state.get("updated_at") or now_utc()
    metric = _state_metric(state)

    return {
        "tenant_asset": f"{tenant_id}#{asset_id}",
        "alert_key": f"state#{metric}",
        "alert_id": f"{asset_id}#state#{metric}",
        "tenant_id": tenant_id,
        "plant_id": state.get("plant_id"),
        "asset_id": asset_id,
        "asset_name": state.get("asset_name", asset_id),
        "area": state.get("area", "-"),
        "criticality": state.get("criticality", "-"),
        "metric": metric,
        "value": _state_value(state),
        "threshold": None,
        "status_label": status_label,
        "status": "open",
        "first_detected_at": updated_at,
        "last_detected_at": updated_at,
        "updated_at": updated_at,
        "recommended_action": state.get("recommended_action") or STATE_RECOMMENDED_ACTION,
        "created_by": "current_state_candidate",
        "source": "current_state",
    }


def normalize_states_as_alerts(states: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    for state in states or []:
        candidate = normalize_current_state_as_alert(state)
        if candidate:
            alerts.append(candidate)

    return alerts


def merge_alert_sources(
    persisted_alerts: list[dict[str, Any]] | None,
    current_states: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    alerts = list(persisted_alerts or [])
    existing_ids = {str(alert.get("alert_id")) for alert in alerts if alert.get("alert_id")}

    for state_alert in normalize_states_as_alerts(current_states):
        alert_id = str(state_alert.get("alert_id") or "")
        if alert_id and alert_id in existing_ids:
            continue
        alerts.append(state_alert)
        if alert_id:
            existing_ids.add(alert_id)

    return alerts


def notification_kind(decision: dict[str, Any]) -> str:
    if decision.get("should_escalate"):
        return "escalation"

    if decision.get("should_repeat"):
        return "repeat"

    return "initial"


def build_outbox_items(
    alerts: list[dict[str, Any]],
    escalation_data: dict[str, Any],
    assets: list[dict[str, Any]] | None = None,
    *,
    created_at: str | None = None,
    current_states: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    created_at = created_at or now_utc()
    candidate_alerts = merge_alert_sources(alerts, current_states)
    decisions = simulate_alerts(candidate_alerts, escalation_data, now=_parse_utc(created_at), assets=assets)
    items: list[dict[str, Any]] = []

    for decision in decisions:
        if not decision.get("notification_due"):
            continue

        kind = notification_kind(decision)
        dedupe_key = f"{_alert_identity(decision)}#{kind}"
        items.append(
            {
                "dedupe_key": dedupe_key,
                "status": "pending",
                "kind": kind,
                "created_at": created_at,
                "updated_at": created_at,
                "rule_id": decision.get("rule_id"),
                "asset_id": decision.get("asset_id"),
                "asset_name": decision.get("asset_name"),
                "severity": decision.get("severity"),
                "metric": decision.get("metric"),
                "metric_label": decision.get("metric_label"),
                "channels": decision.get("channels"),
                "contact_groups": decision.get("contact_groups"),
                "should_repeat": decision.get("should_repeat"),
                "should_escalate": decision.get("should_escalate"),
                "message": decision.get("message"),
            }
        )

    return items


def outbox_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(items),
        "pending": sum(1 for item in items if item.get("status") == "pending"),
        "dry_run_processed": sum(
            1 for item in items if item.get("status") in {"dry_run", "dry_run_processed"}
        ),
        "escalations": sum(1 for item in items if item.get("kind") == "escalation"),
    }
