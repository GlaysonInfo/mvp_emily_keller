from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


DEMO_CASES_FILE = Path(__file__).with_name("demo_cases_cliente.json")

UNIT_BY_METRIC: dict[str, str] = {
    "rpm": "rpm",
    "vibration_rms_mm_s": "mm/s",
    "vibration_peak_g": "g",
    "temperature_c": "C",
    "ultrasound_db": "dB",
    "horimeter_h": "h",
    "kurtosis": "index",
    "crest_factor": "index",
    "health_score": "score",
}

PRIMARY_METRIC_BY_ALERT_TYPE: dict[str, str] = {
    "lubrication_degradation": "ultrasound_db",
    "mechanical_unbalance": "vibration_rms_mm_s",
    "thermal_stress": "temperature_c",
    "bearing_fault_initial": "ultrasound_db",
    "critical_failure_risk": "vibration_rms_mm_s",
    "communication_lost": "communication_lost",
}

DEFAULT_RECOMMENDED_ACTION = (
    "Realizar inspeção técnica no ativo, registrar evidências e avaliar necessidade de intervenção corretiva "
    "ou preventiva."
)


def utc_now_iso(*, stale_minutes: int = 0) -> str:
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    return timestamp.isoformat().replace("+00:00", "Z")


def load_demo_cases(path: str | Path | None = None) -> list[dict[str, Any]]:
    demo_path = Path(path) if path else DEMO_CASES_FILE

    with demo_path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    return sorted(cases, key=lambda item: item["presentation_order"])


def get_demo_case(case_id: str, path: str | Path | None = None) -> dict[str, Any]:
    for case in load_demo_cases(path):
        if case["case_id"] == case_id:
            return case

    raise ValueError(f"Demo case not found: {case_id}")


def to_dynamodb_safe(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value

    if isinstance(value, int | float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {key: to_dynamodb_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_dynamodb_safe(item) for item in value]

    return value


def build_metric_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_metrics = case.get("metrics") or {}
    metrics: dict[str, dict[str, Any]] = {}

    for name, unit in UNIT_BY_METRIC.items():
        value = raw_metrics.get(name)

        if name == "health_score" and value is None:
            value = case.get("health_score")

        if name in raw_metrics or value is not None:
            metrics[name] = {"value": value, "unit": unit}

    return metrics


def build_latest_state_item(
    case: dict[str, Any],
    *,
    tenant_id: str = "cliente_demo",
    plant_id: str = "lab_virtual",
    asset_id: str = "motor_001",
    updated_at: str | None = None,
) -> dict[str, Any]:
    stale_minutes = int(case.get("stale_minutes") or 0)
    state_updated_at = updated_at or utc_now_iso(stale_minutes=stale_minutes)

    item = {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": "LATEST",
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "source": case.get("source", "demo_case_loader"),
        "simulated_source": case.get("simulated_source", "opcua_edge_bridge"),
        "loaded_by": "demo_case_loader",
        "event_id": f"demo-{case['case_id']}",
        "updated_at": state_updated_at,
        "received_at": utc_now_iso(),
        "failure_mode_simulated": case["mode"],
        "status_label": case.get("status_label"),
        "health_score": case.get("health_score"),
        "severity_score": case.get("severity_score"),
        "diagnosis": case.get("diagnosis"),
        "recommended_action": case.get("recommended_action"),
        "client_question_answered": case.get("client_question_answered"),
        "expected_result": case.get("expected_result"),
        "symptom_simulated": case.get("symptom_simulated"),
        "demo_message": case.get("demo_message"),
        "demo_case_id": case["case_id"],
        "demo_case_name": case["case_name"],
        "presentation_order": case["presentation_order"],
        "is_demo_case": True,
        "metrics": build_metric_map(case),
        "raw_s3_key": f"demo_cases/{case['case_id']}.json",
    }

    return to_dynamodb_safe(item)


def build_demo_alert_item(
    case: dict[str, Any],
    *,
    tenant_id: str = "cliente_demo",
    plant_id: str = "lab_virtual",
    asset_id: str = "motor_001",
    payload_updated_at: str | None = None,
) -> dict[str, Any] | None:
    alert = case.get("alert")

    if not alert:
        return None

    alert_type = alert.get("alert_type", case["case_id"])
    now = utc_now_iso()
    detected_at = payload_updated_at or now
    metric = PRIMARY_METRIC_BY_ALERT_TYPE.get(alert_type, alert_type)
    metric_value = (case.get("metrics") or {}).get(metric)
    recommended_action = case.get("recommended_action") or DEFAULT_RECOMMENDED_ACTION

    item = {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": f"ALERT#ACTIVE#{alert_type}",
        "tenant_asset": f"{tenant_id}#{asset_id}",
        "alert_key": f"open#demo#{alert_type}",
        "alert_id": f"{tenant_id}#{asset_id}#{alert_type}#demo",
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "asset_name": asset_id,
        "alert_type": alert_type,
        "metric": metric,
        "value": metric_value,
        "threshold": alert.get("threshold"),
        "severity": alert.get("severity", "warning"),
        "status_label": case.get("status_label") or alert.get("status_label"),
        "status": "open",
        "probable_cause": alert.get("probable_cause", case.get("diagnosis", "Demo alert")),
        "confidence": alert.get("confidence", 0.7),
        "evidence": case.get("evidence", []),
        "recommended_action": recommended_action,
        "failure_mode_simulated": case["mode"],
        "source": case.get("source", "demo_case_loader"),
        "loaded_by": "demo_case_loader",
        "first_detected_at": now,
        "last_detected_at": detected_at,
        "updated_at": now,
        "last_payload_timestamp": detected_at,
        "demo_case_id": case["case_id"],
        "demo_case_name": case["case_name"],
        "timeline": [
            {
                "at": now,
                "by": "demo_case_loader",
                "from_status": None,
                "to_status": "open",
                "note": case.get("demo_message", ""),
                "action_taken": "Cenário de apresentação aplicado.",
            }
        ],
        "is_demo_case": True,
    }

    return to_dynamodb_safe(item)
