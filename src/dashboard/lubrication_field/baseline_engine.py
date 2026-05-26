
from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def compute_outlet_baseline(cycles: list[dict], outlet_id: str, min_samples: int = 20) -> dict[str, Any]:
    peaks = []
    rise_times = []
    decay_times = []

    for cycle in cycles:
        for outlet in cycle.get("outlets", []):
            if outlet.get("outlet_id") != outlet_id:
                continue

            if outlet.get("peak_pressure_bar") is not None:
                peaks.append(float(outlet["peak_pressure_bar"]))
            if outlet.get("rise_time_sec") is not None:
                rise_times.append(float(outlet["rise_time_sec"]))
            if outlet.get("decay_time_sec") is not None:
                decay_times.append(float(outlet["decay_time_sec"]))

    def stats(values):
        if not values:
            return {"samples": 0, "mean": None, "std": None, "min": None, "max": None}
        return {
            "samples": len(values),
            "mean": round(mean(values), 3),
            "std": round(pstdev(values), 3) if len(values) > 1 else 0,
            "min": round(min(values), 3),
            "max": round(max(values), 3),
        }

    baseline = {
        "outlet_id": outlet_id,
        "ready": len(peaks) >= min_samples,
        "min_samples": min_samples,
        "peak_pressure_bar": stats(peaks),
        "rise_time_sec": stats(rise_times),
        "decay_time_sec": stats(decay_times),
    }

    return baseline


def compare_cycle_to_baseline(outlet_result: dict, baseline: dict, warning_pct: float = 30, alert_pct: float = 50) -> dict:
    peak = outlet_result.get("peak_pressure_bar")
    peak_base = (baseline.get("peak_pressure_bar") or {}).get("mean")

    if peak is None or not peak_base:
        return {
            "outlet_id": outlet_result.get("outlet_id"),
            "baseline_ready": baseline.get("ready", False),
            "deviation_pct": None,
            "baseline_status": "sem_baseline",
            "message": "Baseline insuficiente para comparação."
        }

    deviation_pct = ((float(peak) - float(peak_base)) / float(peak_base)) * 100
    abs_dev = abs(deviation_pct)

    if abs_dev >= alert_pct:
        status = "ALERTA"
    elif abs_dev >= warning_pct:
        status = "ATENÇÃO"
    else:
        status = "NORMAL"

    direction = "acima" if deviation_pct > 0 else "abaixo"

    return {
        "outlet_id": outlet_result.get("outlet_id"),
        "baseline_ready": baseline.get("ready", False),
        "current_peak_bar": peak,
        "baseline_peak_bar": peak_base,
        "deviation_pct": round(deviation_pct, 2),
        "baseline_status": status,
        "message": f"Pico atual {abs(deviation_pct):.1f}% {direction} do baseline da saída."
    }
