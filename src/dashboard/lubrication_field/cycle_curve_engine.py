
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PressureSample:
    ts_ms: int
    pressure_bar: float


def detect_cycle_from_curve(samples: list[dict], start_threshold_bar: float = 10, end_threshold_bar: float = 5) -> dict[str, Any]:
    """
    Recebe amostras brutas de uma saída:
      [{"ts_ms":0, "pressure_bar":0.2}, {"ts_ms":200, "pressure_bar":15.0}, ...]

    Retorna indicadores do ciclo:
      pico, tempo de subida, tempo de alívio, pulso detectado.
    """
    if not samples:
        return {
            "pulse_detected": False,
            "peak_pressure_bar": None,
            "rise_time_sec": None,
            "decay_time_sec": None,
            "message": "Sem amostras."
        }

    normalized = [
        {"ts_ms": int(s["ts_ms"]), "pressure_bar": float(s["pressure_bar"])}
        for s in samples
        if s.get("pressure_bar") is not None
    ]

    if not normalized:
        return {"pulse_detected": False, "message": "Amostras sem pressão válida."}

    peak_sample = max(normalized, key=lambda x: x["pressure_bar"])
    peak = peak_sample["pressure_bar"]

    start = next((s for s in normalized if s["pressure_bar"] >= start_threshold_bar), None)
    after_peak = [s for s in normalized if s["ts_ms"] >= peak_sample["ts_ms"]]
    end = next((s for s in after_peak if s["pressure_bar"] <= end_threshold_bar), None)

    pulse_detected = peak >= start_threshold_bar

    rise_time_sec = None
    if start:
        rise_time_sec = max(0, (peak_sample["ts_ms"] - start["ts_ms"]) / 1000)

    decay_time_sec = None
    if end:
        decay_time_sec = max(0, (end["ts_ms"] - peak_sample["ts_ms"]) / 1000)

    return {
        "pulse_detected": pulse_detected,
        "peak_pressure_bar": round(peak, 3),
        "min_pressure_bar": round(min(s["pressure_bar"] for s in normalized), 3),
        "avg_pressure_bar": round(sum(s["pressure_bar"] for s in normalized) / len(normalized), 3),
        "rise_time_sec": rise_time_sec,
        "decay_time_sec": decay_time_sec,
        "samples": len(normalized),
        "start_ts_ms": start["ts_ms"] if start else None,
        "peak_ts_ms": peak_sample["ts_ms"],
        "end_ts_ms": end["ts_ms"] if end else None,
    }


def build_metrics_from_curves(curves_by_outlet: dict[str, list[dict]]) -> dict[str, float]:
    metrics = {}

    for outlet_id, samples in curves_by_outlet.items():
        result = detect_cycle_from_curve(samples)

        metrics[f"pressure_{outlet_id}_bar"] = samples[-1]["pressure_bar"] if samples else None
        metrics[f"peak_{outlet_id}_bar"] = result.get("peak_pressure_bar")
        metrics[f"min_{outlet_id}_bar"] = result.get("min_pressure_bar")
        metrics[f"avg_{outlet_id}_bar"] = result.get("avg_pressure_bar")
        metrics[f"rise_time_{outlet_id}_sec"] = result.get("rise_time_sec")
        metrics[f"decay_time_{outlet_id}_sec"] = result.get("decay_time_sec")

    return metrics
