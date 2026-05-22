from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

try:
    from simulator.contracts import NUMERIC_METRIC_TAGS, UNIT_BY_TAG
except ImportError:  # pragma: no cover - supports python -m src.edge_bridge.main.
    from src.simulator.contracts import NUMERIC_METRIC_TAGS, UNIT_BY_TAG


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_telemetry_payload(
    *,
    tenant_id: str,
    plant_id: str,
    asset_id: str,
    source: str,
    values: dict[str, Any],
    timestamp: str | None = None,
) -> dict[str, Any]:
    metrics = []

    for name, value in values.items():
        if name not in NUMERIC_METRIC_TAGS:
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue

        metrics.append(
            {
                "name": name,
                "value": float(value),
                "unit": UNIT_BY_TAG.get(name, "unknown"),
            }
        )

    return {
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "source": source,
        "timestamp": timestamp or utc_now(),
        "failure_mode_simulated": values.get("failure_mode"),
        "metrics": metrics,
    }

