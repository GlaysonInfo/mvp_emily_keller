from __future__ import annotations

import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.edge.condition_bridge_field.config_store import load_condition_field_config
from src.edge.condition_bridge_field.gateway_client import ConditionGatewayClient
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads
from src.edge.condition_bridge_field.sender import ConditionIngestSender


def _max_iterations() -> int | None:
    if os.getenv("CONDITION_BRIDGE_ONCE"):
        return 1

    value = os.getenv("CONDITION_BRIDGE_MAX_ITERATIONS")
    if value:
        return int(value)

    return None


def main() -> None:
    config_path = os.getenv("CONDITION_FIELD_CONFIG", "config/field_condition_config.json")
    config = load_condition_field_config(config_path)

    client = ConditionGatewayClient(config)
    sender = ConditionIngestSender(config)
    poll_interval_ms = int(config.get("gateway", {}).get("poll_interval_ms", 1000))
    sleep_sec = poll_interval_ms / 1000
    max_iterations = _max_iterations()
    iterations = 0

    print("Condition field bridge started.")
    print(f"Config: {config_path}")
    print(f"Ingest: {config.get('ingest_api', {}).get('endpoint')}")

    while True:
        try:
            raw = client.read_raw()
            payloads = build_condition_payloads(config, raw)
            for payload in payloads:
                result = sender.send(payload)
                print(
                    f"Sent {result.get('asset_id')} | "
                    f"status={result.get('status_label')} | "
                    f"metrics={result.get('metrics_received')}"
                )
        except Exception as exc:
            print(f"Condition bridge error: {type(exc).__name__}: {exc}")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break

        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
