from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

try:
    from dashboard.dynamodb_repository import decimal_to_native
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.dynamodb_repository import decimal_to_native


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_utc_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def floor_to_minute(timestamp: datetime) -> datetime:
    return timestamp.astimezone(UTC).replace(second=0, microsecond=0)


def iso_z(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


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


def metric_value(latest_state: dict[str, Any], *names: str) -> float | None:
    metrics = latest_state.get("metrics")
    metric_map = metrics if isinstance(metrics, dict) else {}

    for name in names:
        value = latest_state.get(name)

        if value is None:
            metric = metric_map.get(name)

            if isinstance(metric, dict):
                value = metric.get("value")
            else:
                value = metric

        if isinstance(value, bool) or value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return None


def resolve_severity_score(latest_state: dict[str, Any]) -> float | None:
    explicit_score = metric_value(latest_state, "severity_score", "severity")

    if explicit_score is not None:
        return explicit_score

    health_score = metric_value(latest_state, "health_score")

    if health_score is None:
        return None

    return round(100.0 - health_score, 1)


def resolve_status_label(latest_state: dict[str, Any], severity_score: float | None, health_score: float | None) -> str:
    status = latest_state.get("status_label")

    if status:
        return str(status)

    mode = str(latest_state.get("failure_mode_simulated") or latest_state.get("mode") or "")

    if mode == "communication_lost":
        return "SEM COMUNICAÇÃO"

    if mode == "post_maintenance_recovery":
        return "RECUPERADO"

    if severity_score is not None:
        if severity_score >= 60:
            return "CRÍTICO"
        if severity_score >= 45:
            return "ALERTA"
        if severity_score >= 25:
            return "ATENÇÃO"

    if health_score is not None:
        if health_score < 40:
            return "CRÍTICO"
        if health_score < 60:
            return "ALERTA"
        if health_score < 80:
            return "ATENÇÃO"

    return "NORMAL"


def build_history_item(
    latest_state: dict[str, Any],
    *,
    retention_days: int = 365,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    tenant_id = str(latest_state.get("tenant_id", "cliente_demo"))
    plant_id = str(latest_state.get("plant_id", "lab_virtual"))
    asset_id = str(latest_state.get("asset_id", "motor_001"))
    recorded_minute = floor_to_minute(recorded_at or utc_now())
    ttl_epoch = int((recorded_minute + timedelta(days=retention_days)).timestamp())

    health_score = metric_value(latest_state, "health_score")
    severity_score = resolve_severity_score(latest_state)
    hourmeter_h = metric_value(latest_state, "hourmeter_h", "horimeter_h")

    item = {
        "tenant_asset": f"{tenant_id}#{asset_id}",
        "ts_utc_minute": iso_z(recorded_minute),
        "ttl_epoch": ttl_epoch,
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "source": latest_state.get("source"),
        "mode": latest_state.get("failure_mode_simulated") or latest_state.get("mode"),
        "status_label": resolve_status_label(latest_state, severity_score, health_score),
        "source_updated_at_utc": latest_state.get("updated_at"),
        "recorded_at_utc": iso_z(recorded_minute),
        "rpm": metric_value(latest_state, "rpm"),
        "vibration_rms_mm_s": metric_value(latest_state, "vibration_rms_mm_s", "vibration_rms"),
        "temperature_c": metric_value(latest_state, "temperature_c", "temperature"),
        "ultrasound_db": metric_value(latest_state, "ultrasound_db", "ultrasound"),
        "kurtosis_index": metric_value(latest_state, "kurtosis", "kurtosis_index"),
        "crest_factor_index": metric_value(latest_state, "crest_factor", "crest_factor_index"),
        "vibration_peak_g": metric_value(latest_state, "vibration_peak_g", "vibration_peak"),
        "hourmeter_h": hourmeter_h,
        "health_score": health_score,
        "severity_score": severity_score,
    }

    return to_dynamodb_safe(item)


class ConditionHistoryRepository:
    def __init__(
        self,
        table_name: str,
        region_name: str,
        profile_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if dynamodb_resource is None:
            if profile_name:
                session = boto3.Session(profile_name=profile_name, region_name=region_name)
            else:
                session = boto3.Session(region_name=region_name)

            dynamodb_resource = session.resource("dynamodb")

        self.table = dynamodb_resource.Table(table_name)

    def put_minute_snapshot(self, latest_state: dict[str, Any], *, retention_days: int = 365) -> dict[str, Any]:
        item = build_history_item(latest_state, retention_days=retention_days)
        self.table.put_item(Item=item)
        return item

    def query_history(
        self,
        *,
        tenant_id: str,
        asset_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[dict[str, Any]]:
        tenant_asset = f"{tenant_id}#{asset_id}"
        result = self.table.query(
            KeyConditionExpression=Key("tenant_asset").eq(tenant_asset)
            & Key("ts_utc_minute").between(iso_z(floor_to_minute(start_utc)), iso_z(floor_to_minute(end_utc))),
            ScanIndexForward=True,
        )

        items = result.get("Items", [])
        return [decimal_to_native(item) for item in items]


def create_history_repository_from_env() -> ConditionHistoryRepository:
    try:
        from dashboard.local_demo_repository import create_local_demo_history_repository, local_demo_enabled
    except ImportError:  # pragma: no cover - supports streamlit run from repository root.
        from src.dashboard.local_demo_repository import create_local_demo_history_repository, local_demo_enabled

    if local_demo_enabled():
        return create_local_demo_history_repository()  # type: ignore[return-value]

    return ConditionHistoryRepository(
        table_name=os.getenv("CONDITION_HISTORY_TABLE", "condition_history"),
        region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        profile_name=os.getenv("AWS_PROFILE") or None,
    )
