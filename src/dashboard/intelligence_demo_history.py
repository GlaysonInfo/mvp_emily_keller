from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random
from typing import Any

try:
    from dashboard.history_repository import create_history_repository_from_env, to_dynamodb_safe
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.history_repository import create_history_repository_from_env, to_dynamodb_safe


def _to_float(value: Any, default: float) -> float:
    if isinstance(value, dict):
        value = value.get("value")

    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _metric(current_state: dict[str, Any], key: str, legacy_key: str | None = None, default: float = 0.0) -> float:
    metrics = current_state.get("metrics")
    metric_map = metrics if isinstance(metrics, dict) else {}

    value = metric_map.get(key)
    if value is None and legacy_key:
        value = metric_map.get(legacy_key)
    if value is None:
        value = current_state.get(key)
    if value is None and legacy_key:
        value = current_state.get(legacy_key)

    return _to_float(value, default)


def extract_current_metrics(current_state: dict[str, Any]) -> dict[str, float]:
    return {
        "rpm": _metric(current_state, "rpm", default=1780.0),
        "vibration_rms_mm_s": _metric(current_state, "vibration_rms_mm_s", "vibration_rms", 2.8),
        "temperature_c": _metric(current_state, "temperature_c", "temperature", 70.0),
        "ultrasound_db": _metric(current_state, "ultrasound_db", "ultrasound", 42.0),
        "kurtosis_index": _metric(current_state, "kurtosis_index", "kurtosis", 3.5),
        "crest_factor_index": _metric(current_state, "crest_factor_index", "crest_factor", 3.4),
        "vibration_peak_g": _metric(current_state, "vibration_peak_g", "vibration_peak", 0.7),
        "health_score": _metric(current_state, "health_score", default=72.0),
        "severity_score": _metric(current_state, "severity_score", "severity", 28.0),
    }


def _iso_z(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _bounded(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def create_demo_history_items(
    *,
    tenant_id: str,
    plant_id: str,
    asset_id: str,
    current_state: dict[str, Any],
    minutes_healthy: int = 120,
    minutes_degraded: int = 20,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current = extract_current_metrics(current_state)
    total_minutes = max(1, int(minutes_healthy) + int(minutes_degraded))
    now_utc = (now or datetime.now(UTC)).astimezone(UTC).replace(second=0, microsecond=0)
    rng = Random(f"{tenant_id}:{plant_id}:{asset_id}:{current_state.get('status_label', '')}")

    healthy = {
        "rpm": current["rpm"],
        "vibration_rms_mm_s": min(current["vibration_rms_mm_s"] * 0.72, 2.2),
        "temperature_c": min(current["temperature_c"] - 10.0, 60.0)
        if current["temperature_c"] > 65.0
        else current["temperature_c"] * 0.92,
        "ultrasound_db": min(current["ultrasound_db"] * 0.75, 34.0),
        "kurtosis_index": min(current["kurtosis_index"] * 0.75, 2.6),
        "crest_factor_index": min(current["crest_factor_index"] * 0.75, 2.6),
        "vibration_peak_g": min(current["vibration_peak_g"] * 0.70, 0.45),
        "health_score": 92.0,
        "severity_score": 8.0,
    }

    items: list[dict[str, Any]] = []
    tenant_asset = f"{tenant_id}#{asset_id}"
    target_status = str(current_state.get("status_label") or "ATENÇÃO")
    target_mode = str(current_state.get("failure_mode_simulated") or current_state.get("mode") or "demo_degradation")

    for index in range(total_minutes):
        timestamp = now_utc - timedelta(minutes=total_minutes - index)
        degraded = index >= minutes_healthy
        progress = 0.0 if not degraded else (index - minutes_healthy + 1) / max(int(minutes_degraded), 1)

        def interpolate(metric: str, noise: float, minimum: float = 0.0) -> float:
            start = healthy[metric]
            end = current[metric]
            value = start + (end - start) * progress + rng.normalvariate(0.0, noise)
            return round(max(minimum, value), 4)

        health = _bounded(
            healthy["health_score"] + (current["health_score"] - healthy["health_score"]) * progress + rng.normalvariate(0.0, 1.2)
        )
        severity = _bounded(
            healthy["severity_score"] + (current["severity_score"] - healthy["severity_score"]) * progress + rng.normalvariate(0.0, 1.0)
        )
        ts_text = _iso_z(timestamp)

        items.append(
            {
                "tenant_asset": tenant_asset,
                "ts_utc_minute": ts_text,
                "tenant_id": tenant_id,
                "plant_id": plant_id,
                "asset_id": asset_id,
                "status_label": target_status if degraded else "NORMAL",
                "mode": target_mode if degraded else "demo_baseline_healthy",
                "source": "demo_history_for_intelligence",
                "recorded_at_utc": ts_text,
                "updated_at": ts_text,
                "rpm": interpolate("rpm", 3.0, 0.0),
                "vibration_rms_mm_s": interpolate("vibration_rms_mm_s", 0.12, 0.0),
                "temperature_c": interpolate("temperature_c", 1.2, 0.0),
                "ultrasound_db": interpolate("ultrasound_db", 1.5, 0.0),
                "kurtosis_index": interpolate("kurtosis_index", 0.15, 0.0),
                "crest_factor_index": interpolate("crest_factor_index", 0.15, 0.0),
                "vibration_peak_g": interpolate("vibration_peak_g", 0.04, 0.0),
                "health_score": round(health, 4),
                "severity_score": round(severity, 4),
            }
        )

    return items


def seed_demo_history_to_dynamodb(
    *,
    tenant_id: str,
    plant_id: str,
    asset_id: str,
    current_state: dict[str, Any],
    history_repository: Any | None = None,
) -> int:
    repository = history_repository or create_history_repository_from_env()
    items = create_demo_history_items(
        tenant_id=tenant_id,
        plant_id=plant_id,
        asset_id=asset_id,
        current_state=current_state,
    )

    with repository.table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=to_dynamodb_safe(item))

    return len(items)
