from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import pi, sin
from random import Random
from typing import Any

try:
    from .contracts import UNIT_BY_TAG
except ImportError:  # pragma: no cover - allows direct script execution.
    from contracts import UNIT_BY_TAG


class FailureMode(StrEnum):
    NORMAL = "normal"
    LUBRICATION_DEGRADATION = "lubrication_degradation"
    IMBALANCE = "imbalance"
    BEARING_FAULT = "bearing_fault"


class Severity(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MotorSample:
    timestamp: datetime
    tenant_id: str
    plant_id: str
    asset_id: str
    source: str
    failure_mode: FailureMode
    rpm: float
    vibration_rms_mm_s: float
    vibration_peak_g: float
    temperature_c: float
    ultrasound_db: float
    horimeter_h: float
    kurtosis: float
    crest_factor: float
    health_score: float
    severity: Severity

    def opcua_values(self) -> dict[str, float | str]:
        return {
            "rpm": self.rpm,
            "vibration_rms_mm_s": self.vibration_rms_mm_s,
            "vibration_peak_g": self.vibration_peak_g,
            "temperature_c": self.temperature_c,
            "ultrasound_db": self.ultrasound_db,
            "horimeter_h": self.horimeter_h,
            "kurtosis": self.kurtosis,
            "crest_factor": self.crest_factor,
            "health_score": self.health_score,
            "severity": self.severity.value,
            "failure_mode": self.failure_mode.value,
        }

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "plant_id": self.plant_id,
            "asset_id": self.asset_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "failure_mode_simulated": self.failure_mode.value,
            "metrics": [
                {"name": "rpm", "value": self.rpm, "unit": UNIT_BY_TAG["rpm"]},
                {
                    "name": "vibration_rms_mm_s",
                    "value": self.vibration_rms_mm_s,
                    "unit": UNIT_BY_TAG["vibration_rms_mm_s"],
                },
                {
                    "name": "vibration_peak_g",
                    "value": self.vibration_peak_g,
                    "unit": UNIT_BY_TAG["vibration_peak_g"],
                },
                {"name": "temperature_c", "value": self.temperature_c, "unit": UNIT_BY_TAG["temperature_c"]},
                {"name": "ultrasound_db", "value": self.ultrasound_db, "unit": UNIT_BY_TAG["ultrasound_db"]},
                {"name": "horimeter_h", "value": self.horimeter_h, "unit": UNIT_BY_TAG["horimeter_h"]},
                {"name": "kurtosis", "value": self.kurtosis, "unit": UNIT_BY_TAG["kurtosis"]},
                {"name": "crest_factor", "value": self.crest_factor, "unit": UNIT_BY_TAG["crest_factor"]},
                {"name": "health_score", "value": self.health_score, "unit": UNIT_BY_TAG["health_score"]},
            ],
        }


class MotorSimulator:
    """Synthetic Motor_001 signal generator for the OPC UA lab server."""

    def __init__(
        self,
        *,
        tenant_id: str = "cliente_demo",
        plant_id: str = "lab_virtual",
        asset_id: str = "motor_001",
        source: str = "opcua_lab_simulator",
        scenario_duration_seconds: float = 90.0,
        random_seed: int | None = 42,
        initial_horimeter_h: float = 1284.0,
    ) -> None:
        if scenario_duration_seconds <= 0:
            raise ValueError("scenario_duration_seconds must be greater than zero")

        self.tenant_id = tenant_id
        self.plant_id = plant_id
        self.asset_id = asset_id
        self.source = source
        self.scenario_duration_seconds = scenario_duration_seconds
        self.initial_horimeter_h = initial_horimeter_h
        self._noise = Random(random_seed)

    def sample(
        self,
        elapsed_seconds: float,
        *,
        timestamp: datetime | None = None,
    ) -> MotorSample:
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be greater than or equal to zero")

        failure_mode, progress = self._scenario_at(elapsed_seconds)
        timestamp = timestamp or datetime.now(UTC)
        waveform = sin((elapsed_seconds / 12.0) * 2.0 * pi)
        noise = self._noise.uniform

        if failure_mode is FailureMode.NORMAL:
            rpm = 1780.0 + (4.0 * waveform) + noise(-2.0, 2.0)
            vibration_rms = 1.9 + (0.08 * waveform) + noise(-0.04, 0.04)
            vibration_peak = 0.36 + noise(-0.03, 0.03)
            temperature = 59.5 + (0.6 * waveform) + noise(-0.25, 0.25)
            ultrasound = 32.0 + noise(-0.6, 0.6)
            kurtosis = 3.1 + noise(-0.12, 0.12)
            crest_factor = 3.0 + noise(-0.10, 0.10)
            health_score = 97.0 + noise(-1.2, 1.2)
            severity = Severity.NORMAL
        elif failure_mode is FailureMode.LUBRICATION_DEGRADATION:
            rpm = 1777.0 + (5.0 * waveform) + noise(-3.0, 3.0)
            vibration_rms = 2.1 + (1.25 * progress) + noise(-0.08, 0.08)
            vibration_peak = 0.45 + (0.35 * progress) + noise(-0.04, 0.04)
            temperature = 60.5 + (11.0 * progress) + noise(-0.35, 0.35)
            ultrasound = 35.0 + (10.0 * progress) + noise(-0.5, 0.5)
            kurtosis = 3.2 + (0.5 * progress) + noise(-0.12, 0.12)
            crest_factor = 3.1 + (0.45 * progress) + noise(-0.10, 0.10)
            health_score = 92.0 - (28.0 * progress) + noise(-1.5, 1.0)
            severity = Severity.WARNING if progress >= 0.35 else Severity.NORMAL
        elif failure_mode is FailureMode.IMBALANCE:
            rpm = 1772.0 + (9.0 * waveform) + noise(-4.0, 4.0)
            vibration_rms = 3.2 + (3.0 * progress) + noise(-0.10, 0.10)
            vibration_peak = 0.65 + (0.95 * progress) + noise(-0.06, 0.06)
            temperature = 61.0 + (5.0 * progress) + noise(-0.4, 0.4)
            ultrasound = 33.0 + (1.0 * progress) + noise(-0.6, 0.6)
            kurtosis = 3.2 + (0.7 * progress) + noise(-0.12, 0.12)
            crest_factor = 3.0 + (0.55 * progress) + noise(-0.12, 0.12)
            health_score = 86.0 - (48.0 * progress) + noise(-1.4, 1.0)
            severity = Severity.CRITICAL if progress >= 0.45 else Severity.WARNING
        else:
            rpm = 1775.0 + (6.0 * waveform) + noise(-4.0, 4.0)
            vibration_rms = 2.35 + (2.25 * progress) + noise(-0.12, 0.12)
            vibration_peak = 0.82 + (1.80 * progress) + noise(-0.08, 0.08)
            temperature = 60.5 + (6.5 * progress) + noise(-0.4, 0.4)
            ultrasound = 34.5 + (4.5 * progress) + noise(-0.7, 0.7)
            kurtosis = 4.2 + (3.1 * progress) + noise(-0.15, 0.15)
            crest_factor = 4.0 + (2.55 * progress) + noise(-0.14, 0.14)
            health_score = 82.0 - (55.0 * progress) + noise(-1.6, 1.0)
            severity = Severity.CRITICAL if progress >= 0.35 else Severity.WARNING

        return MotorSample(
            timestamp=timestamp,
            tenant_id=self.tenant_id,
            plant_id=self.plant_id,
            asset_id=self.asset_id,
            source=self.source,
            failure_mode=failure_mode,
            rpm=self._round(rpm),
            vibration_rms_mm_s=self._round(vibration_rms),
            vibration_peak_g=self._round(vibration_peak),
            temperature_c=self._round(temperature),
            ultrasound_db=self._round(ultrasound),
            horimeter_h=self._round(self.initial_horimeter_h + (elapsed_seconds / 3600.0), 4),
            kurtosis=self._round(kurtosis),
            crest_factor=self._round(crest_factor),
            health_score=max(0.0, min(100.0, self._round(health_score))),
            severity=severity,
        )

    def _scenario_at(self, elapsed_seconds: float) -> tuple[FailureMode, float]:
        sequence = (
            FailureMode.NORMAL,
            FailureMode.LUBRICATION_DEGRADATION,
            FailureMode.IMBALANCE,
            FailureMode.BEARING_FAULT,
        )
        scenario_index = int(elapsed_seconds // self.scenario_duration_seconds) % len(sequence)
        scenario_elapsed = elapsed_seconds % self.scenario_duration_seconds
        progress = scenario_elapsed / self.scenario_duration_seconds
        return sequence[scenario_index], progress

    @staticmethod
    def _round(value: float, digits: int = 2) -> float:
        return round(float(value), digits)


class MotorModel:
    """Compatibility facade used by simple tests and notebooks."""

    def __init__(
        self,
        *,
        asset_id: str = "motor_001",
        seed: int | None = 42,
        scenario_duration_seconds: float = 60.0,
    ) -> None:
        self._simulator = MotorSimulator(
            asset_id=asset_id,
            random_seed=seed,
            scenario_duration_seconds=scenario_duration_seconds,
        )

    def simulate(self, elapsed_seconds: float) -> dict[str, float | str]:
        return self._simulator.sample(elapsed_seconds).opcua_values()

