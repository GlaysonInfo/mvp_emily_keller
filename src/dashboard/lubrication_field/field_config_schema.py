
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SensorOutletConfig:
    outlet_id: str
    name: str
    sensor_id: str
    gateway_port: str
    gateway_tag_pressure: str
    sensor_range_bar: float = 250
    sensor_signal: str = "IO-Link"
    sensor_model: str = ""
    process_connection: str = ""
    physical_gauge_present: bool = True
    enabled: bool = True


@dataclass
class GatewayConfig:
    source_id: str = "grease_gateway_01"
    name: str = "Gateway IO-Link Lubrificação 01"
    manufacturer: str = ""
    model: str = ""
    protocol: str = "http_json"
    endpoint: str = ""
    read_timeout_sec: int = 5
    authentication: dict[str, Any] = field(default_factory=lambda: {"type": "none", "token_env": ""})


@dataclass
class LubricationSystemConfig:
    asset_id: str = "sistema_lubrificacao_01"
    asset_name: str = "Sistema de Lubrificação Centralizada"
    expected_operating_pressure_bar: float = 100
    recommended_sensor_range_bar: float = 250
    physical_gauges_kept: bool = True
    sample_interval_ms: int = 200
    send_mode: str = "per_cycle"


def to_dict(obj) -> dict:
    return asdict(obj)
