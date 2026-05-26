from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_payload() -> dict:
    return {
        "tenant_id": os.getenv("CONDITION_TENANT_ID", "cliente_demo"),
        "plant_id": os.getenv("CONDITION_PLANT_ID", "lab_virtual"),
        "asset_id": os.getenv("CONDITION_ASSET_ID", "motor_001"),
        "asset_name": os.getenv("CONDITION_ASSET_NAME", "Motor Principal"),
        "source": os.getenv("CONDITION_SOURCE", "condition_gateway_01"),
        "timestamp": now_utc(),
        "metrics": [
            {"name": "rpm", "value": 1778.0, "unit": "rpm"},
            {"name": "vibration_rms_mm_s", "value": 4.4, "unit": "mm/s"},
            {"name": "vibration_peak_g", "value": 0.82, "unit": "g"},
            {"name": "temperature_c", "value": 62.8, "unit": "C"},
            {"name": "ultrasound_db", "value": 33.1, "unit": "dB"},
            {"name": "kurtosis", "value": 3.2, "unit": "index"},
            {"name": "crest_factor", "value": 3.1, "unit": "index"},
            {"name": "health_score", "value": 67.6, "unit": "score"},
            {"name": "severity_score", "value": 32.4, "unit": "score"},
        ],
        "quality": {"source": "python_test", "sample_rate_hz": 1},
    }


def main() -> None:
    endpoint = os.getenv("CONDITION_INGEST_ENDPOINT", "http://127.0.0.1:8001/condition/ingest")
    token = os.getenv("CONDITION_INGEST_TOKEN")
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
