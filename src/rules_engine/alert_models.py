from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_SEVERITIES = {"warning", "critical"}
ALLOWED_STATUSES = {"open", "acknowledged", "closed"}


@dataclass(frozen=True)
class Alert:
    alert_type: str
    severity: str
    status: str
    probable_cause: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = ""
    tenant_id: str | None = None
    plant_id: str | None = None
    asset_id: str | None = None
    source: str | None = None
    timestamp: str | None = None
    failure_mode_simulated: str | None = None

    def __post_init__(self) -> None:
        if not self.alert_type:
            raise ValueError("alert_type is required")

        if self.severity not in ALLOWED_SEVERITIES:
            raise ValueError(f"invalid severity: {self.severity}")

        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"invalid status: {self.status}")

        if not self.probable_cause:
            raise ValueError("probable_cause is required")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if not self.evidence:
            raise ValueError("evidence must not be empty")

        if not self.recommended_action:
            raise ValueError("recommended_action is required")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "status": self.status,
            "probable_cause": self.probable_cause,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "recommended_action": self.recommended_action,
        }

        optional_fields = {
            "tenant_id": self.tenant_id,
            "plant_id": self.plant_id,
            "asset_id": self.asset_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "failure_mode_simulated": self.failure_mode_simulated,
        }

        for key, value in optional_fields.items():
            if value is not None:
                data[key] = value

        return data
