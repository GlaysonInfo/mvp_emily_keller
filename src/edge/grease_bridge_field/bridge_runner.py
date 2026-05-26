
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Permite rodar pela raiz do projeto.
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.lubrication_field.field_config_store import load_field_config
from src.edge.grease_bridge_field.iolink_gateway_client import IOLinkGatewayClient
from src.edge.grease_bridge_field.cycle_detector import GreaseCycleDetector
from src.edge.grease_bridge_field.payload_builder import build_grease_payload
from src.edge.grease_bridge_field.sender import GreaseIngestSender


def main():
    config_path = os.getenv("GREASE_FIELD_CONFIG", "config/field_lubrication_config.json")
    config = load_field_config(config_path)

    client = IOLinkGatewayClient(config)
    detector = GreaseCycleDetector(config)
    sender = GreaseIngestSender(config)

    sample_interval_ms = int(config.get("lubrication_system", {}).get("sample_interval_ms", 200))
    sleep_sec = sample_interval_ms / 1000

    start = time.perf_counter()

    print("Bridge de campo iniciada.")
    print(f"Config: {config_path}")
    print(f"Ingest: {config.get('ingest_api', {}).get('endpoint')}")

    while True:
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        try:
            pressures = client.read_pressures()
            cycle = detector.ingest_sample(elapsed_ms, pressures)

            if cycle:
                payload = build_grease_payload(config, cycle)
                result = sender.send(payload)
                print(f"Ciclo enviado: {result.get('cycle_id')} | Status: {result.get('status_label')}")

        except Exception as exc:
            print(f"ERRO bridge: {type(exc).__name__}: {exc}")

        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
