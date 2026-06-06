from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.aws_lambdas.ingest_lambda import build_dynamodb_latest_item
from src.dashboard.dynamodb_repository import normalize_active_alert_item, tenant_plant_key
from src.dashboard.history_repository import build_history_item, resolve_status_label, to_dynamodb_safe
from src.rules_engine.diagnostics import evaluate_payload

from .condition_ingest_models import ConditionIngestPayload, ConditionIngestResponse
from .condition_registry_validation import validate_condition_payload_against_registry


def ensure_region() -> str:
    region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = region
    return region


def state_table_name_from_env() -> str:
    return os.getenv("DYNAMODB_STATE_TABLE") or os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev")


def history_table_name_from_env() -> str:
    return os.getenv("CONDITION_HISTORY_TABLE", "condition_history")


def alerts_table_name_from_env() -> str:
    return os.getenv("CONDITION_ALERTS_TABLE") or os.getenv("ALERTS_TABLE", "condition_alerts")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _metric_map(payload: ConditionIngestPayload) -> dict[str, dict[str, Any]]:
    return {metric.name: {"value": metric.value, "unit": metric.unit} for metric in payload.metrics}


def _metric_value(metric_map: dict[str, dict[str, Any]], *names: str) -> float | None:
    for name in names:
        metric = metric_map.get(name)
        if not metric:
            continue
        try:
            return float(metric.get("value"))
        except (TypeError, ValueError):
            continue
    return None


def _enrich_latest_state(state_item: dict[str, Any], payload: ConditionIngestPayload) -> dict[str, Any]:
    metric_map = _metric_map(payload)
    health_score = _metric_value(metric_map, "health_score")
    severity_score = _metric_value(metric_map, "severity_score", "severity")

    if severity_score is None and health_score is not None:
        severity_score = round(100.0 - health_score, 1)

    status_label = resolve_status_label(state_item, severity_score, health_score)

    enriched = {
        **state_item,
        "tenant_asset": f"{payload.tenant_id}#{payload.asset_id}",
        "tenant_plant": tenant_plant_key(payload.tenant_id, payload.plant_id),
        "status_label": status_label,
        "ingest_source": "condition_ingest_api",
    }

    optional_fields = {
        "asset_name": payload.asset_name,
        "area": payload.area,
        "asset_type": payload.asset_type,
        "criticality": payload.criticality,
        "quality": payload.quality,
        "raw": payload.raw,
    }
    for key, value in optional_fields.items():
        if value not in [None, {}, ""]:
            enriched[key] = value

    for name, metric in metric_map.items():
        enriched[name] = Decimal(str(metric["value"]))

    if severity_score is not None:
        enriched["severity_score"] = Decimal(str(severity_score))

    return enriched


def _alert_status_label(severity: str) -> str:
    return "CRÍTICO" if str(severity).lower() == "critical" else "ATENÇÃO"


def _status_from_alerts(alerts: list[dict[str, Any]]) -> str | None:
    if not alerts:
        return None

    if any(str(alert.get("severity") or "").lower() == "critical" for alert in alerts):
        return "CRÍTICO"

    return "ATENÇÃO"


def _existing_alert(table: Any, item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        result = table.get_item(Key={"tenant_asset": item["tenant_asset"], "alert_key": item["alert_key"]})
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ValidationException":
            raise
        result = table.get_item(Key={"pk": item["pk"], "sk": item["sk"]})
    return result.get("Item")


def _condition_alert_item(
    payload: ConditionIngestPayload,
    alert: dict[str, Any],
    *,
    existing_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alert_type = str(alert["alert_type"])
    tenant_asset = f"{payload.tenant_id}#{payload.asset_id}"
    detected_at = payload.timestamp or utc_now()
    first_detected_at = detected_at

    if existing_item and existing_item.get("first_detected_at"):
        first_detected_at = str(existing_item["first_detected_at"])

    item = {
        "pk": f"TENANT#{payload.tenant_id}#ASSET#{payload.asset_id}",
        "sk": f"ALERT#ACTIVE#{alert_type}",
        "tenant_asset": tenant_asset,
        "alert_key": f"open#condition#{alert_type}",
        "alert_id": f"{payload.tenant_id}#{payload.asset_id}#{alert_type}#active",
        "tenant_id": payload.tenant_id,
        "plant_id": payload.plant_id,
        "asset_id": payload.asset_id,
        "asset_name": payload.asset_name or payload.asset_id,
        "alert_type": alert_type,
        "metric": alert_type,
        "severity": alert.get("severity"),
        "status_label": _alert_status_label(str(alert.get("severity"))),
        "status": "open",
        "probable_cause": alert.get("probable_cause"),
        "description": alert.get("probable_cause"),
        "confidence": alert.get("confidence", 0.0),
        "evidence": alert.get("evidence", []),
        "recommended_action": alert.get("recommended_action"),
        "failure_mode_simulated": payload.failure_mode_simulated,
        "source": payload.source,
        "ingest_source": "condition_ingest_api",
        "first_detected_at": first_detected_at,
        "last_detected_at": detected_at,
        "updated_at": utc_now(),
        "last_payload_timestamp": payload.timestamp,
    }

    return to_dynamodb_safe(normalize_active_alert_item(item))


class ConditionIngestRepository:
    def __init__(
        self,
        *,
        state_table_name: str,
        history_table_name: str,
        alerts_table_name: str,
        region_name: str,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if dynamodb_resource is None:
            dynamodb_resource = boto3.resource("dynamodb", region_name=region_name)

        self.state_table = dynamodb_resource.Table(state_table_name)
        self.history_table = dynamodb_resource.Table(history_table_name)
        self.alerts_table = dynamodb_resource.Table(alerts_table_name)

    def save_state(self, item: dict[str, Any]) -> None:
        self.state_table.put_item(Item=to_dynamodb_safe(item))

    def save_history(self, latest_state: dict[str, Any]) -> dict[str, Any]:
        item = build_history_item(latest_state)
        self.history_table.put_item(Item=item)
        return item

    def save_alerts(self, payload: ConditionIngestPayload, alerts: list[dict[str, Any]]) -> int:
        written = 0
        for alert in alerts:
            base_item = _condition_alert_item(payload, alert)
            existing_item = _existing_alert(self.alerts_table, base_item)
            item = _condition_alert_item(payload, alert, existing_item=existing_item)
            self.alerts_table.put_item(Item=item)
            written += 1
        return written


def process_condition_ingest(
    payload: ConditionIngestPayload,
    *,
    dynamodb_resource: Any | None = None,
) -> ConditionIngestResponse:
    region = ensure_region()
    event_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    state_item = build_dynamodb_latest_item(
        payload=payload_dict,
        event_id=event_id,
        raw_s3_key=f"condition-ingest/direct/{event_id}.json",
    )
    state_item = _enrich_latest_state(state_item, payload)
    registry_warnings = validate_condition_payload_against_registry(payload)
    registry_status = "warning" if registry_warnings else "ok"
    state_item["registry_validation_status"] = registry_status
    if registry_warnings:
        state_item["registry_warnings"] = registry_warnings

    alerts = evaluate_payload(payload_dict)
    alert_status = _status_from_alerts(alerts)
    if alert_status:
        current_status = str(state_item.get("status_label") or "NORMAL").upper()
        if alert_status == "CRÍTICO" and current_status != "CRÍTICO":
            state_item["status_label"] = alert_status
        elif current_status in ["NORMAL", "RECUPERADO", "-", ""]:
            state_item["status_label"] = alert_status

    repo = ConditionIngestRepository(
        state_table_name=state_table_name_from_env(),
        history_table_name=history_table_name_from_env(),
        alerts_table_name=alerts_table_name_from_env(),
        region_name=region,
        dynamodb_resource=dynamodb_resource,
    )
    repo.save_state(state_item)
    history_item = repo.save_history(state_item)
    alerts_written = repo.save_alerts(payload, alerts)

    return ConditionIngestResponse(
        ok=True,
        message="Telemetria de condição recebida, avaliada e salva com sucesso.",
        tenant_id=payload.tenant_id,
        plant_id=payload.plant_id,
        asset_id=payload.asset_id,
        source=payload.source,
        timestamp=str(payload.timestamp),
        status_label=str(state_item.get("status_label") or "NORMAL"),
        metrics_received=len(payload.metrics),
        active_alerts_count=len(alerts),
        saved_state=True,
        saved_history=True,
        saved_alerts=True,
        registry_validation_status=registry_status,
        registry_warnings=registry_warnings,
        details={
            "state_table": state_table_name_from_env(),
            "history_table": history_table_name_from_env(),
            "alerts_table": alerts_table_name_from_env(),
            "history_key": {
                "tenant_asset": history_item.get("tenant_asset"),
                "ts_utc_minute": history_item.get("ts_utc_minute"),
            },
            "alerts_written": alerts_written,
            "alerts": alerts,
        },
    )
