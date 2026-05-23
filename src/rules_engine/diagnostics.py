from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping


def extract_metric_values(payload: Mapping[str, Any]) -> dict[str, float]:
    metrics = payload.get("metrics", {})

    if isinstance(metrics, list):
        return _extract_from_metric_list(metrics)

    if isinstance(metrics, Mapping):
        return _extract_from_metric_map(metrics)

    return {}


def extract_alert_context(payload: Mapping[str, Any]) -> dict[str, str]:
    context = {}

    for key in [
        "tenant_id",
        "plant_id",
        "asset_id",
        "source",
        "timestamp",
        "failure_mode_simulated",
    ]:
        value = payload.get(key)
        if value is not None:
            context[key] = str(value)

    return context


def _extract_from_metric_list(metrics: list[Any]) -> dict[str, float]:
    values = {}

    for metric in metrics:
        if not isinstance(metric, Mapping):
            continue

        name = metric.get("name")
        value = metric.get("value")

        if isinstance(name, str) and _is_number(value):
            values[name] = float(value)

    return values


def _extract_from_metric_map(metrics: Mapping[str, Any]) -> dict[str, float]:
    values = {}

    for name, metric in metrics.items():
        if isinstance(metric, Mapping):
            value = metric.get("value")
        else:
            value = metric

        if _is_number(value):
            values[str(name)] = float(value)

    return values


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
