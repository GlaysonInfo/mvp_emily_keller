from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class GreaseIngestPayload(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    plant_id: str = Field(..., min_length=1)
    asset_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    timestamp_utc: Optional[str] = None
    cycle_id: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    quality: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp_utc")
    @classmethod
    def validate_timestamp(cls, value):
        if value in [None, ""]:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return value
        except Exception as exc:
            raise ValueError("timestamp_utc deve estar em ISO-8601, exemplo 2026-05-25T23:30:00Z") from exc

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value):
        if not isinstance(value, dict) or not value:
            raise ValueError("metrics não pode ser vazio.")
        pressure_keys = [k for k in value if k.startswith("pressure_") or k.startswith("peak_")]
        if not pressure_keys:
            raise ValueError("metrics deve conter ao menos uma chave pressure_* ou peak_* para as saídas de graxa.")
        return value

    @model_validator(mode="after")
    def normalize_cycle_id(self):
        if not self.cycle_id:
            clean_ts = str(self.timestamp_utc).replace("-", "").replace(":", "").replace(".", "").replace("Z", "")
            self.cycle_id = f"cycle_{self.asset_id}_{clean_ts}"
        return self


class GreaseIngestResponse(BaseModel):
    ok: bool
    message: str
    tenant_id: str
    plant_id: str
    asset_id: str
    source_id: str
    cycle_id: str
    status_label: str
    outlet_count: int
    active_alerts_count: int
    saved_state: bool
    saved_cycle: bool
    saved_alerts: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class GreaseHealthResponse(BaseModel):
    ok: bool
    service: str
    region: str
    state_table: str
    cycles_table: str
    alerts_table: str
