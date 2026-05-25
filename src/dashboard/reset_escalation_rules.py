from __future__ import annotations

import json
from pathlib import Path

try:
    from dashboard.escalation_repository import EscalationRepository
except ImportError:  # pragma: no cover - supports execution from repository root.
    from src.dashboard.escalation_repository import EscalationRepository


def main() -> None:
    here = Path(__file__).parent
    default_path = here / "escalation_rules_store_default.json"
    target_path = here / "escalation_rules_store.json"

    data = json.loads(default_path.read_text(encoding="utf-8"))
    EscalationRepository(target_path).save(data)
    print(f"Matriz restaurada: {target_path}")


if __name__ == "__main__":
    main()
