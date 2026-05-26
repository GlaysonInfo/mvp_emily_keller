
from __future__ import annotations

from datetime import datetime, timezone


def build_grease_payload(config: dict, cycle_data: dict) -> dict:
    client = config.get("client", {})
    plant = config.get("plant", {})
    system = config.get("lubrication_system", {})
    gateway = config.get("gateway", {})

    timestamp = cycle_data.get("timestamp_utc") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "tenant_id": client.get("tenant_id"),
        "plant_id": plant.get("plant_id"),
        "asset_id": system.get("asset_id"),
        "source_id": gateway.get("source_id"),
        "timestamp_utc": timestamp,
        "cycle_id": f"cycle_{system.get('asset_id')}_{timestamp.replace(':', '').replace('-', '').replace('.', '').replace('Z', '')}",
        "metrics": cycle_data.get("metrics", {}),
        "quality": {
            "source": "field_iolink_bridge",
            "gateway": gateway.get("source_id"),
            "sample_interval_ms": system.get("sample_interval_ms"),
            "sensor_range_bar": system.get("recommended_sensor_range_bar"),
        }
    }
