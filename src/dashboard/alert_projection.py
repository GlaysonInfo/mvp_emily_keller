from __future__ import annotations

from typing import Any


RISK_STATUSES = {
    "ATENÇÃO",
    "ATENCAO",
    "ATENÇÃO ALTA",
    "ATENCAO ALTA",
    "ALERTA",
    "CRÍTICO",
    "CRITICO",
    "SEM COMUNICAÇÃO",
    "SEM COMUNICACAO",
}

NORMAL_STATUSES = {"NORMAL", "RECUPERADO"}


def to_number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, bool) or value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_number(state: dict[str, Any], *names: str) -> float | None:
    metrics = state.get("metrics")
    metric_map = metrics if isinstance(metrics, dict) else {}

    for name in names:
        value = to_number(state.get(name))

        if value is not None:
            return value

        value = to_number(metric_map.get(name))

        if value is not None:
            return value

    return None


def severity_score(state: dict[str, Any]) -> float | None:
    explicit = metric_number(state, "severity_score", "severity")

    if explicit is not None:
        return explicit

    health = metric_number(state, "health_score")

    if health is None:
        return None

    return round(100.0 - health, 1)


def severity_slug(state: dict[str, Any]) -> str | None:
    status = str(state.get("status_label") or "").upper()
    severity = severity_score(state)
    health = metric_number(state, "health_score")

    if status in {"CRÍTICO", "CRITICO", "SEM COMUNICAÇÃO", "SEM COMUNICACAO"}:
        return "critical"

    if severity is not None and severity >= 65:
        return "critical"

    if health is not None and health <= 35:
        return "critical"

    if status in RISK_STATUSES:
        return "warning"

    if severity is not None and severity >= 25:
        return "warning"

    if health is not None and health < 80:
        return "warning"

    return None


def is_risk_state(state: dict[str, Any]) -> bool:
    status = str(state.get("status_label") or "").upper()

    if status in NORMAL_STATUSES:
        return False

    if status in RISK_STATUSES:
        return True

    return severity_slug(state) is not None


def evidence_from_state(state: dict[str, Any]) -> list[str]:
    evidence = []
    status = state.get("status_label")
    health = metric_number(state, "health_score")
    severity = severity_score(state)

    if status:
        evidence.append(f"Status operacional: {status}")

    if health is not None:
        evidence.append(f"Health Score: {health:.1f}")

    if severity is not None:
        evidence.append(f"Severity Score: {severity:.1f}")

    metric_labels = [
        ("Vibração RMS", "vibration_rms_mm_s", "vibration_rms", "mm/s"),
        ("Temperatura", "temperature_c", "temperature", "°C"),
        ("Ultrassom", "ultrasound_db", "ultrasound", "dB"),
        ("Pico de vibração", "vibration_peak_g", "vibration_peak", "g"),
    ]

    for label, primary, fallback, unit in metric_labels:
        value = metric_number(state, primary, fallback)

        if value is not None:
            evidence.append(f"{label}: {value:.2f} {unit}")

    return evidence


def derived_alert_from_state(state: dict[str, Any]) -> dict[str, Any] | None:
    if not is_risk_state(state):
        return None

    alert_severity = severity_slug(state)

    if alert_severity is None:
        return None

    mode = state.get("failure_mode_simulated") or state.get("mode") or "operational_condition"
    updated_at = state.get("updated_at")

    return {
        "pk": state.get("pk"),
        "sk": f"ALERT#DERIVED#{mode}",
        "alert_id": f"{state.get('tenant_id', '-')}#{state.get('asset_id', '-')}#{mode}#derived",
        "tenant_id": state.get("tenant_id"),
        "plant_id": state.get("plant_id"),
        "asset_id": state.get("asset_id"),
        "alert_type": mode,
        "severity": alert_severity,
        "status": "open",
        "probable_cause": state.get("diagnosis") or state.get("mode_label") or mode,
        "confidence": 1.0,
        "evidence": evidence_from_state(state),
        "recommended_action": state.get("recommended_action") or "Verificar condição operacional do ativo.",
        "failure_mode_simulated": mode,
        "source": "current_state_projection",
        "first_detected_at": updated_at,
        "updated_at": updated_at,
        "last_payload_timestamp": updated_at,
        "is_state_derived": True,
    }


def alerts_for_state(state: dict[str, Any], active_alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    asset_id = state.get("asset_id")
    filtered_alerts = [alert for alert in active_alerts if alert.get("asset_id") in {asset_id, None}]

    if filtered_alerts:
        return filtered_alerts

    derived_alert = derived_alert_from_state(state)
    return [] if derived_alert is None else [derived_alert]


def alerts_with_state_derived(alerts: list[dict[str, Any]], states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = list(alerts)
    assets_with_alert = {alert.get("asset_id") for alert in output}

    for state in states:
        if state.get("asset_id") in assets_with_alert:
            continue

        derived_alert = derived_alert_from_state(state)

        if derived_alert is not None:
            output.append(derived_alert)

    return output
