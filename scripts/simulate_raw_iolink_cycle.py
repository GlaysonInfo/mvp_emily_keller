
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.lubrication_field.cycle_curve_engine import build_metrics_from_curves


def make_curve(peak: float, decay_slow: bool = False):
    samples = []
    for i in range(60):
        ts = i * 200
        t = i / 10
        if i < 15:
            pressure = peak * (i / 15)
        elif i < 25:
            pressure = peak
        else:
            decay_factor = 0.04 if decay_slow else 0.12
            pressure = peak * math.exp(-(i - 25) * decay_factor)
        samples.append({"ts_ms": ts, "pressure_bar": round(pressure, 2)})
    return samples


curves = {
    "saida_graxa_01": make_curve(105),
    "saida_graxa_02": make_curve(110),
    "saida_graxa_03": make_curve(9),
    "saida_graxa_04": make_curve(175, decay_slow=True),
}

metrics = build_metrics_from_curves(curves)

payload = {
    "tenant_id": "cliente_demo",
    "plant_id": "lab_virtual",
    "asset_id": "sistema_lubrificacao_01",
    "source_id": "grease_gateway_01",
    "timestamp_utc": "2026-05-26T12:00:00Z",
    "cycle_id": "cycle_simulated_curve",
    "metrics": metrics,
    "raw_curve": curves,
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
