from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Iterator


NUMERIC_TYPES = (int, float)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def parse_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Accept API Gateway events or direct telemetry payloads."""
    body = event.get("body")

    if body is None:
        return event

    if isinstance(body, str):
        return json.loads(body)

    if isinstance(body, dict):
        return body

    raise ValueError("Formato de body invalido")


def validate_payload(payload: dict[str, Any]) -> None:
    required_fields = [
        "tenant_id",
        "plant_id",
        "asset_id",
        "source",
        "timestamp",
        "metrics",
    ]

    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Campo obrigatorio ausente: {field}")

    if not isinstance(payload["metrics"], list) or not payload["metrics"]:
        raise ValueError("metrics deve ser uma lista nao vazia")

    for metric in payload["metrics"]:
        if "name" not in metric:
            raise ValueError("Metrica sem campo name")

        if "value" not in metric:
            raise ValueError("Metrica sem campo value")

        if "unit" not in metric:
            raise ValueError("Metrica sem campo unit")

        if isinstance(metric["value"], bool) or not isinstance(metric["value"], NUMERIC_TYPES):
            raise ValueError(f"Metrica {metric['name']} possui valor nao numerico")


def build_raw_s3_key(payload: dict[str, Any], event_id: str) -> str:
    ts = parse_timestamp(payload["timestamp"])
    tenant_id = payload["tenant_id"]
    plant_id = payload["plant_id"]
    asset_id = payload["asset_id"]

    return (
        f"raw/tenant={tenant_id}/plant={plant_id}/asset={asset_id}/"
        f"date={ts.date().isoformat()}/{event_id}.json"
    )


def build_timestream_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ts = parse_timestamp(payload["timestamp"])
    ts_ms = str(int(ts.timestamp() * 1000))

    tenant_id = str(payload["tenant_id"])
    plant_id = str(payload["plant_id"])
    asset_id = str(payload["asset_id"])
    source = str(payload["source"])

    records = []

    for metric in payload["metrics"]:
        records.append(
            {
                "Dimensions": [
                    {"Name": "tenant_id", "Value": tenant_id},
                    {"Name": "plant_id", "Value": plant_id},
                    {"Name": "asset_id", "Value": asset_id},
                    {"Name": "source", "Value": source},
                    {"Name": "unit", "Value": str(metric["unit"])},
                ],
                "MeasureName": str(metric["name"]),
                "MeasureValue": str(float(metric["value"])),
                "MeasureValueType": "DOUBLE",
                "Time": ts_ms,
                "TimeUnit": "MILLISECONDS",
            }
        )

    return records


def build_dynamodb_latest_item(
    payload: dict[str, Any],
    event_id: str,
    raw_s3_key: str,
) -> dict[str, Any]:
    tenant_id = str(payload["tenant_id"])
    plant_id = str(payload["plant_id"])
    asset_id = str(payload["asset_id"])

    metrics = {}

    for metric in payload["metrics"]:
        metrics[str(metric["name"])] = {
            "value": Decimal(str(metric["value"])),
            "unit": str(metric["unit"]),
        }

    return {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": "LATEST",
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "source": str(payload["source"]),
        "event_id": event_id,
        "updated_at": str(payload["timestamp"]),
        "received_at": utc_now(),
        "failure_mode_simulated": payload.get("failure_mode_simulated"),
        "metrics": metrics,
        "raw_s3_key": raw_s3_key,
    }


def chunked(items: list[dict[str, Any]], size: int = 100) -> Iterator[list[dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def get_boto3_clients() -> dict[str, Any]:
    import boto3

    return {
        "s3": boto3.client("s3"),
        "timestream": boto3.client("timestream-write"),
        "dynamodb": boto3.resource("dynamodb"),
        "eventbridge": boto3.client("events"),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        payload = parse_event_payload(event)
        validate_payload(payload)

        event_id = payload.get("event_id") or str(uuid.uuid4())

        raw_bucket = os.environ["RAW_BUCKET"]
        timestream_db = os.environ["TIMESTREAM_DB"]
        timestream_table = os.environ["TIMESTREAM_TABLE"]
        dynamodb_table = os.environ["DYNAMODB_TABLE"]
        event_bus = os.environ.get("EVENT_BUS", "default")

        raw_s3_key = build_raw_s3_key(payload, event_id)
        timestream_records = build_timestream_records(payload)
        dynamodb_item = build_dynamodb_latest_item(payload, event_id, raw_s3_key)

        clients = get_boto3_clients()

        clients["s3"].put_object(
            Bucket=raw_bucket,
            Key=raw_s3_key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        for batch in chunked(timestream_records, size=100):
            clients["timestream"].write_records(
                DatabaseName=timestream_db,
                TableName=timestream_table,
                Records=batch,
            )

        table = clients["dynamodb"].Table(dynamodb_table)
        table.put_item(Item=dynamodb_item)

        clients["eventbridge"].put_events(
            Entries=[
                {
                    "Source": "condition-monitoring.ingestion",
                    "DetailType": "TelemetryNormalized",
                    "EventBusName": event_bus,
                    "Detail": json.dumps(
                        {
                            "event_id": event_id,
                            "tenant_id": payload["tenant_id"],
                            "plant_id": payload["plant_id"],
                            "asset_id": payload["asset_id"],
                            "timestamp": payload["timestamp"],
                            "raw_s3_key": raw_s3_key,
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        )

        return response(
            202,
            {
                "status": "accepted",
                "event_id": event_id,
                "raw_s3_key": raw_s3_key,
                "metrics_received": len(payload["metrics"]),
            },
        )

    except ValueError as exc:
        return response(400, {"status": "invalid_payload", "error": str(exc)})

    except Exception as exc:
        return response(500, {"status": "internal_error", "error": str(exc)})

