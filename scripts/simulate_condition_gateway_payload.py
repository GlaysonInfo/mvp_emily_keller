from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.edge.condition_bridge_field.config_store import load_condition_field_config
from src.edge.condition_bridge_field.gateway_client import ConditionGatewayClient
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads


def main() -> None:
    config = load_condition_field_config(os.getenv("CONDITION_FIELD_CONFIG"))
    raw = ConditionGatewayClient(config).read_raw()
    payloads = build_condition_payloads(config, raw)
    print(json.dumps(payloads, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
