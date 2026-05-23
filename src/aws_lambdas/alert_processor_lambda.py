from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

try:
    from rules_engine.diagnostics import evaluate_payload
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.rules_engine.diagnostics import evaluate_payload


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def decimal_to_float(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict):
        return {key: decimal_to_float(item) for key, item in value.items()}

    if isinstance(value, list):
        return [decimal_to_float(item) for item in value]

    return value


def to_dynamodb_safe(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {key: to_dynamodb_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_dynamodb_safe(item) for item in value]

    return value


def get_event_detail(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail")

    if not isinstance(detail, dict):
        raise ValueError("Evento sem detail valido")

    required = ["tenant_id", "plant_id", "asset_id"]

    for field in required:
        if field not in detail:
            raise ValueError(f"detail sem campo obrigatorio: {field}")

    return detail


def build_latest_key(tenant_id: str, asset_id: str) -> dict[str, str]:
    return {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": "LATEST",
    }


def latest_item_to_payload(item: dict[str, Any]) -> dict[str, Any]:
    item = decimal_to_float(item)
    metrics = []

    for metric_name, metric_data in item.get("metrics", {}).items():
        value = metric_data.get("value")
        unit = metric_data.get("unit", "unknown")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics.append(
                {
                    "name": metric_name,
                    "value": float(value),
                    "unit": unit,
                }
            )

    return {
        "tenant_id": item["tenant_id"],
        "plant_id": item["plant_id"],
        "asset_id": item["asset_id"],
        "source": item.get("source", "unknown"),
        "timestamp": item["updated_at"],
        "failure_mode_simulated": item.get("failure_mode_simulated"),
        "metrics": metrics,
    }


def build_alert_item(
    payload: dict[str, Any],
    alert: dict[str, Any],
    existing_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now()

    tenant_id = payload["tenant_id"]
    plant_id = payload["plant_id"]
    asset_id = payload["asset_id"]
    alert_type = alert["alert_type"]

    first_detected_at = now

    if existing_item and existing_item.get("first_detected_at"):
        first_detected_at = existing_item["first_detected_at"]

    item = {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": f"ALERT#ACTIVE#{alert_type}",
        "alert_id": f"{tenant_id}#{asset_id}#{alert_type}#active",
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "alert_type": alert_type,
        "severity": alert["severity"],
        "status": "open",
        "probable_cause": alert["probable_cause"],
        "confidence": alert.get("confidence", 0.0),
        "evidence": alert.get("evidence", []),
        "recommended_action": alert["recommended_action"],
        "failure_mode_simulated": payload.get("failure_mode_simulated"),
        "source": payload.get("source"),
        "first_detected_at": first_detected_at,
        "updated_at": now,
        "last_payload_timestamp": payload.get("timestamp"),
    }

    return to_dynamodb_safe(item)


def get_dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        detail = get_event_detail(event)

        tenant_id = detail["tenant_id"]
        asset_id = detail["asset_id"]

        state_table_name = os.environ["DYNAMODB_TABLE"]
        alerts_table_name = os.environ["ALERTS_TABLE"]

        dynamodb = get_dynamodb_resource()
        state_table = dynamodb.Table(state_table_name)
        alerts_table = dynamodb.Table(alerts_table_name)

        latest_key = build_latest_key(tenant_id, asset_id)
        latest_result = state_table.get_item(Key=latest_key, ConsistentRead=True)
        latest_item = latest_result.get("Item")

        if not latest_item:
            return response(
                404,
                {
                    "status": "latest_state_not_found",
                    "tenant_id": tenant_id,
                    "asset_id": asset_id,
                },
            )

        payload = latest_item_to_payload(latest_item)
        alerts = evaluate_payload(payload)

        written = 0

        for alert in alerts:
            alert_key = {
                "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
                "sk": f"ALERT#ACTIVE#{alert['alert_type']}",
            }

            existing_result = alerts_table.get_item(Key=alert_key)
            existing_item = existing_result.get("Item")

            alert_item = build_alert_item(
                payload=payload,
                alert=alert,
                existing_item=existing_item,
            )

            alerts_table.put_item(Item=alert_item)
            written += 1

        return response(
            200,
            {
                "status": "processed",
                "tenant_id": tenant_id,
                "asset_id": asset_id,
                "alerts_detected": len(alerts),
                "alerts_written": written,
            },
        )

    except ValueError as exc:
        return response(400, {"status": "invalid_event", "error": str(exc)})

    except Exception as exc:
        return response(500, {"status": "internal_error", "error": str(exc)})
