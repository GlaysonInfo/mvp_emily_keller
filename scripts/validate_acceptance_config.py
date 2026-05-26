
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path(os.getenv("ACCEPTANCE_CONFIG", "config/acceptance_config.json"))
EXAMPLE_CONFIG_PATH = Path("config/acceptance_config.example.json")


def load_acceptance_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    config = load_acceptance_config()
    issues = []

    if config.get("aws_region") != "us-east-1":
        issues.append("aws_region deve ser us-east-1.")

    if not config.get("endpoint_ingest", "").endswith("/grease/ingest"):
        issues.append("endpoint_ingest deve apontar para /grease/ingest.")

    if not config.get("endpoint_health", "").endswith("/grease/health"):
        issues.append("endpoint_health deve apontar para /grease/health.")

    if not config.get("pilot_scope", {}).get("physical_gauges_kept"):
        issues.append("No piloto, os manômetros físicos devem ser mantidos.")

    if float(config.get("pilot_scope", {}).get("sensor_range_bar") or 0) < 160:
        issues.append("Faixa do sensor menor que 160 bar. Recomendado 0–250 bar.")

    result = {
        "ok": not issues,
        "issues": issues,
        "config": config,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
