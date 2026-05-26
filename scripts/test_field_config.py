
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.lubrication_field.field_config_store import load_field_config, validate_field_config


def main() -> None:
    config = load_field_config("config/field_lubrication_config.example.json")
    issues = validate_field_config(config)

    print(json.dumps({
        "ok": not any(i["level"] == "ERRO" for i in issues),
        "issues": issues,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
