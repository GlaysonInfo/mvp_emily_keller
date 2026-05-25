from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_outbox_path() -> Path:
    return Path(__file__).with_name("notification_outbox_store.json")


def normalize_outbox_data(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"items": []}

    items = data.get("items")
    return {"items": list(items) if isinstance(items, list) else []}


class NotificationOutboxRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = self._resolve_path(path)

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is None or str(path).strip() == "":
            return default_outbox_path()

        candidate = Path(path)
        if candidate.is_absolute():
            return candidate

        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return cwd_candidate

        return Path(__file__).parent / candidate

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"items": []}

        return normalize_outbox_data(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(normalize_outbox_data(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_pending(self, new_items: list[dict[str, Any]]) -> tuple[int, int]:
        data = self.load()
        existing_keys = {str(item.get("dedupe_key")) for item in data["items"]}
        added = 0
        skipped = 0

        for item in new_items:
            dedupe_key = str(item.get("dedupe_key") or "")
            if dedupe_key in existing_keys:
                skipped += 1
                continue

            data["items"].append(item)
            existing_keys.add(dedupe_key)
            added += 1

        self.save(data)
        return added, skipped

    def items(self, status: str | None = None) -> list[dict[str, Any]]:
        items = self.load()["items"]
        if status is None or status == "Todos":
            return items
        return [item for item in items if item.get("status") == status]

    def mark_dry_run_processed(self, limit: int | None = None) -> int:
        data = self.load()
        processed = 0

        for item in data["items"]:
            if item.get("status") != "pending":
                continue

            item["status"] = "dry_run"
            item["dry_run_processed_at"] = item.get("updated_at") or item.get("created_at")
            processed += 1

            if limit is not None and processed >= limit:
                break

        self.save(data)
        return processed
