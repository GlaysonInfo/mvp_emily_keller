from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

endpoint = os.getenv("GREASE_INGEST_ENDPOINT", "https://sentinelaindustrial.com.br/grease/ingest")
token = os.getenv("GREASE_INGEST_TOKEN")

def build_payload():
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "sistema_lubrificacao_01",
        "source_id": "grease_gateway_01",
        "timestamp_utc": now_utc(),
        "cycle_id": "cycle_remote_test_python_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "metrics": {
            "pressure_saida_graxa_01_bar": 84.2,
            "pressure_saida_graxa_02_bar": 91.7,
            "pressure_saida_graxa_03_bar": 7.8,
            "pressure_saida_graxa_04_bar": 146.5,
            "peak_saida_graxa_01_bar": 103.3,
            "peak_saida_graxa_02_bar": 112.1,
            "peak_saida_graxa_03_bar": 9.2,
            "peak_saida_graxa_04_bar": 181.2,
            "min_saida_graxa_01_bar": 2.0,
            "min_saida_graxa_02_bar": 2.0,
            "min_saida_graxa_03_bar": 0.0,
            "min_saida_graxa_04_bar": 4.0,
            "rise_time_saida_graxa_01_sec": 2.7,
            "rise_time_saida_graxa_02_sec": 3.6,
            "rise_time_saida_graxa_03_sec": 8.5,
            "rise_time_saida_graxa_04_sec": 2.1,
            "decay_time_saida_graxa_01_sec": 4.7,
            "decay_time_saida_graxa_02_sec": 4.9,
            "decay_time_saida_graxa_03_sec": 2.3,
            "decay_time_saida_graxa_04_sec": 18.6,
        },
        "quality": {"source": "remote_python_test", "sensor_range_bar": 250}
    }


def main():
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["X-API-Key"] = token

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(build_payload()).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
