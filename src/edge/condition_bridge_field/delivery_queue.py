from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConditionDeliveryQueue:
    def __init__(self, path: str | Path | None = None) -> None:
        selected = path or os.getenv("CONDITION_BRIDGE_SPOOL_DIR") or "data/condition_bridge_spool"
        self.path = Path(selected)

    def enqueue(self, payload: dict[str, Any]) -> Path:
        event_id = str(payload.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("Payload sem event_id não pode entrar na fila persistente.")

        self.path.mkdir(parents=True, exist_ok=True)
        destination = self.path / f"{event_id}.json"
        if destination.exists():
            return destination

        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temporary.replace(destination)
        return destination

    def pending(self) -> list[Path]:
        if not self.path.exists():
            return []
        return sorted(self.path.glob("*.json"), key=lambda item: (item.stat().st_mtime_ns, item.name))

    @staticmethod
    def load(item: Path) -> dict[str, Any]:
        return json.loads(item.read_text(encoding="utf-8"))

    @staticmethod
    def acknowledge(item: Path) -> None:
        item.unlink(missing_ok=True)
