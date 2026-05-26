from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.edge.condition_bridge_field.gateway_client import get_nested_value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(raw: dict[str, Any]) -> str:
    return str(raw.get("timestamp_utc") or raw.get("timestamp") or utc_now())


def build_condition_payload(config: dict[str, Any], raw: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    client = config.get("client", {})
    plant = config.get("plant", {})
    gateway = config.get("gateway", {})
    quality = config.get("quality", {})

    metrics = []
    missing_required = []

    for signal in asset.get("signals", []):
        if not signal.get("metric"):
            continue

        value = get_nested_value(raw, str(signal.get("tag") or ""))
        if value is None:
            if signal.get("required", False):
                missing_required.append(signal.get("metric"))
            continue

        metrics.append(
            {
                "name": signal["metric"],
                "value": float(value),
                "unit": signal.get("unit", ""),
            }
        )

    if not metrics:
        raise ValueError(f"No metrics found for asset {asset.get('asset_id')}.")

    payload = {
        "tenant_id": client.get("tenant_id"),
        "plant_id": plant.get("plant_id"),
        "asset_id": asset.get("asset_id"),
        "asset_name": asset.get("asset_name"),
        "asset_type": asset.get("asset_type"),
        "area": asset.get("area") or plant.get("area"),
        "criticality": asset.get("criticality"),
        "source": gateway.get("source_id"),
        "timestamp": _timestamp(raw),
        "metrics": metrics,
        "quality": {
            "source": quality.get("source", "field_condition_bridge"),
            "gateway": gateway.get("source_id"),
            "gateway_protocol": gateway.get("protocol"),
            "sample_rate_hz": quality.get("sample_rate_hz"),
            "missing_required_signals": missing_required,
        },
    }

    if asset.get("failure_mode_simulated"):
        payload["failure_mode_simulated"] = asset["failure_mode_simulated"]

    if config.get("include_raw_payload", False):
        payload["raw"] = raw

    return payload


def build_condition_payloads(config: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    payloads = []
    for asset in config.get("assets", []):
        if not asset.get("enabled", True):
            continue
        payloads.append(build_condition_payload(config, raw, asset))
    return payloads
