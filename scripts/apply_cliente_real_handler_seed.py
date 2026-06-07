from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.config_repository import ConfigRepository
from src.dashboard.platform_admin_repository import PlatformAdminRepository


DEFAULT_PLATFORM_SEED = ROOT / "config" / "cliente_real_indoor_platform_admin_store.json"
DEFAULT_CONFIG_SEED = ROOT / "config" / "cliente_real_indoor_config_store.json"

PLATFORM_LIST_KEYS = {
    "tenants": ("tenant_id",),
    "plants": ("tenant_id", "plant_id"),
    "service_contracts": ("tenant_id", "plant_id"),
    "users": ("tenant_id", "email"),
    "onboarding_runs": ("tenant_id", "plant_id"),
}

OPERATIONAL_LIST_KEYS = {
    "data_sources": ("source_id",),
    "assets": ("asset_id",),
    "sensors": ("sensor_id",),
    "signal_map": ("asset_id", "source_id", "metric", "sensor_id"),
    "parameters_alerts": ("asset_id", "metric"),
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(item: dict[str, Any], keys: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(item.get(name) or "") for name in keys)


def _upsert_many(
    current: list[dict[str, Any]],
    seed: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> tuple[list[dict[str, Any]], int]:
    output = [deepcopy(item) for item in current if isinstance(item, dict)]
    changed = 0

    for new_item in [item for item in seed if isinstance(item, dict)]:
        new_key = _key(new_item, keys)
        found = False
        for index, existing in enumerate(output):
            if _key(existing, keys) != new_key:
                continue
            found = True
            if existing != new_item:
                output[index] = deepcopy(new_item)
                changed += 1
            break
        if not found:
            output.append(deepcopy(new_item))
            changed += 1

    return output, changed


def merge_platform_store(
    current: dict[str, Any],
    seed: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    merged = deepcopy(current)
    counts: dict[str, int] = {}

    for section, keys in PLATFORM_LIST_KEYS.items():
        merged_items, changed = _upsert_many(
            list(current.get(section) or []),
            list(seed.get(section) or []),
            keys,
        )
        merged[section] = merged_items
        counts[section] = changed

    return merged, counts


def merge_operational_config(
    current: dict[str, Any],
    seed: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    merged = deepcopy(current)
    counts: dict[str, int] = {}

    for section, keys in OPERATIONAL_LIST_KEYS.items():
        merged_items, changed = _upsert_many(
            list(current.get(section) or []),
            list(seed.get(section) or []),
            keys,
        )
        merged[section] = merged_items
        counts[section] = changed

    return merged, counts


def _store_path(value: str | None, env_name: str) -> str | None:
    return value or os.getenv(env_name) or None


def apply_seed(
    *,
    platform_store_path: str | None,
    config_store_path: str | None,
    platform_seed_path: Path = DEFAULT_PLATFORM_SEED,
    config_seed_path: Path = DEFAULT_CONFIG_SEED,
    dry_run: bool = False,
) -> dict[str, Any]:
    platform_repo = PlatformAdminRepository(platform_store_path)
    config_repo = ConfigRepository(config_store_path)
    platform_seed = _read_json(platform_seed_path)
    config_seed = _read_json(config_seed_path)

    platform_current = platform_repo.load()
    config_current = config_repo.load()

    platform_merged, platform_counts = merge_platform_store(platform_current, platform_seed)
    config_merged, config_counts = merge_operational_config(config_current, config_seed)

    revision = None
    if not dry_run:
        platform_repo.save(platform_merged)
        revision = config_repo.save_versioned(
            config_merged,
            change_type="seed_indoor_device",
            target="cliente_real/indoor/handler_vegapuls6x_01",
            reason="Aplicar seed do Handler/VEGAPULS 6X para teste indoor do cliente_real.",
            actor={"email": "admin@sentinela.com.br", "role": "admin"},
            tenant_id="cliente_real",
            plant_id="indoor",
        )

    return {
        "platform_store": str(platform_repo.path),
        "config_store": str(config_repo.path),
        "platform_changes": platform_counts,
        "operational_changes": config_counts,
        "technical_revision": revision,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aplica o seed cliente_real/indoor do Handler VEGAPULS 6X nos stores ativos.",
    )
    parser.add_argument("--platform-store", default=None, help="Caminho do PLATFORM_ADMIN_STORE.")
    parser.add_argument("--config-store", default=None, help="Caminho do DASHBOARD_CONFIG_STORE.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que mudaria sem gravar.")
    args = parser.parse_args()

    result = apply_seed(
        platform_store_path=_store_path(args.platform_store, "PLATFORM_ADMIN_STORE"),
        config_store_path=_store_path(args.config_store, "DASHBOARD_CONFIG_STORE"),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
