from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ConditionMetric(BaseModel):
    name: str = Field(..., min_length=1)
    value: float
    unit: str = Field(default="")

    @field_validator("name", "unit")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return str(value).strip()


class ConditionIngestPayload(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    plant_id: str = Field(..., min_length=1)
    asset_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    timestamp: str | None = None
    metrics: list[ConditionMetric] = Field(default_factory=list)
    failure_mode_simulated: str | None = None
    asset_name: str | None = None
    area: str | None = None
    asset_type: str | None = None
    criticality: str | None = None
    quality: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant_id", "plant_id", "asset_id", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str | None) -> str:
        if value in [None, ""]:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return str(value)
        except Exception as exc:
            raise ValueError("timestamp deve estar em ISO-8601, exemplo 2026-05-26T18:00:00Z") from exc

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value: list[ConditionMetric]) -> list[ConditionMetric]:
        if not value:
            raise ValueError("metrics deve ser uma lista não vazia.")
        return value

    @model_validator(mode="after")
    def validate_unique_metric_names(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("metrics não pode conter métricas duplicadas.")
        return self


class ConditionIngestResponse(BaseModel):
    ok: bool
    message: str
    tenant_id: str
    plant_id: str
    asset_id: str
    source: str
    timestamp: str
    status_label: str
    metrics_received: int
    active_alerts_count: int
    saved_state: bool
    saved_history: bool
    saved_alerts: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ConditionHealthResponse(BaseModel):
    ok: bool
    service: str
    region: str
    state_table: str
    history_table: str
    alerts_table: str
