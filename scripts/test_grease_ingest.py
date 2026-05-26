from __future__ import annotations

import json, os, urllib.request
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    endpoint = os.getenv("GREASE_INGEST_ENDPOINT", "http://127.0.0.1:8000/grease/ingest")
    token = os.getenv("GREASE_INGEST_TOKEN")
    payload = {
        "tenant_id": "cliente_demo", "plant_id": "lab_virtual", "asset_id": "sistema_lubrificacao_01", "source_id": "grease_gateway_01",
        "timestamp_utc": now_utc(), "cycle_id": "cycle_test_python",
        "metrics": {
            "pressure_saida_graxa_01_bar": 84.2, "pressure_saida_graxa_02_bar": 91.7, "pressure_saida_graxa_03_bar": 7.8, "pressure_saida_graxa_04_bar": 146.5,
            "peak_saida_graxa_01_bar": 102.3, "peak_saida_graxa_02_bar": 108.1, "peak_saida_graxa_03_bar": 9.2, "peak_saida_graxa_04_bar": 181.2,
            "min_saida_graxa_01_bar": 2.0, "min_saida_graxa_02_bar": 2.0, "min_saida_graxa_03_bar": 0.0, "min_saida_graxa_04_bar": 4.0,
            "rise_time_saida_graxa_01_sec": 3.2, "rise_time_saida_graxa_02_sec": 3.5, "rise_time_saida_graxa_03_sec": 8.9, "rise_time_saida_graxa_04_sec": 2.1,
            "decay_time_saida_graxa_01_sec": 4.8, "decay_time_saida_graxa_02_sec": 5.1, "decay_time_saida_graxa_03_sec": 2.4, "decay_time_saida_graxa_04_sec": 18.6,
        },
        "quality": {"source": "python_test", "sensor_range_bar": 250},
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["X-API-Key"] = token
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(resp.read().decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
