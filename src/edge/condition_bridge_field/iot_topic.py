from __future__ import annotations

from typing import Any


DEFAULT_TOPIC_TEMPLATE = "sentinela/{tenant_id}/{plant_id}/{asset_id}/telemetry"


def iot_topic_template(config: dict[str, Any]) -> str:
    iot_core = config.get("iot_core", {})
    return str(iot_core.get("topic_template") or DEFAULT_TOPIC_TEMPLATE)


def build_iot_topic(config: dict[str, Any], payload: dict[str, Any]) -> str:
    template = iot_topic_template(config)
    values = {
        "tenant_id": payload.get("tenant_id") or config.get("client", {}).get("tenant_id") or "unknown_tenant",
        "plant_id": payload.get("plant_id") or config.get("plant", {}).get("plant_id") or "unknown_plant",
        "asset_id": payload.get("asset_id") or "unknown_asset",
        "source": payload.get("source") or config.get("gateway", {}).get("source_id") or "unknown_source",
    }
    return template.format(**values)
