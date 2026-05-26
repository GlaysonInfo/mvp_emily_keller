
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.dashboard.lubrication_field.cycle_curve_engine import build_metrics_from_curves


class GreaseCycleDetector:
    """
    Detector simples de ciclo baseado em pressão.

    O runner acumula amostras por saída e chama `ingest_sample`.
    Quando a pressão passa do limiar e depois retorna ao repouso, fecha ciclo.
    """

    def __init__(self, config: dict):
        self.config = config
        cycle_cfg = config.get("gateway", {}).get("cycle_detection", {})
        self.start_threshold = float(config.get("rules", {}).get("low_pressure_bar", 10))
        self.end_threshold = float(cycle_cfg.get("end_threshold_bar", 5))
        self.in_cycle = False
        self.cycle_start_ms = None
        self.samples_by_outlet: dict[str, list[dict]] = {}

    def ingest_sample(self, elapsed_ms: int, pressures: dict[str, float]) -> dict[str, Any] | None:
        max_pressure = max(pressures.values(), default=0)

        if not self.in_cycle and max_pressure >= self.start_threshold:
            self.in_cycle = True
            self.cycle_start_ms = elapsed_ms
            self.samples_by_outlet = {outlet_id: [] for outlet_id in pressures}

        if self.in_cycle:
            for outlet_id, pressure in pressures.items():
                self.samples_by_outlet.setdefault(outlet_id, []).append({
                    "ts_ms": elapsed_ms - (self.cycle_start_ms or 0),
                    "pressure_bar": pressure,
                })

            if max_pressure <= self.end_threshold:
                metrics = build_metrics_from_curves(self.samples_by_outlet)
                self.in_cycle = False
                self.cycle_start_ms = None
                self.samples_by_outlet = {}

                return {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "metrics": metrics,
                }

        return None
