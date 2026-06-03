from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from dashboard.module_registry import SERVICE_CONDITION, SERVICE_LUBRICATION, normalize_service_keys
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.module_registry import SERVICE_CONDITION, SERVICE_LUBRICATION, normalize_service_keys


DEFAULT_PLATFORM_ADMIN_DATA: dict[str, Any] = {
    "schema_version": 2,
    "tenants": [
        {
            "tenant_id": "cliente_demo",
            "company_name": "Cliente Demonstração",
            "status": "Ativo",
            "environment": "Piloto",
        }
    ],
    "plants": [
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "plant_name": "Bancada Virtual",
            "city": "Betim",
            "status": "Ativa",
        }
    ],
    "service_contracts": [
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "services": [SERVICE_CONDITION, SERVICE_LUBRICATION],
            "operational_intelligence": True,
            "status": "Ativo",
        }
    ],
    "users": [
        {
            "tenant_id": "cliente_demo",
            "email": "admin@cliente.demo",
            "name": "Admin Cliente Demo",
            "role": "cliente_admin",
            "status": "Ativo",
        }
    ],
    "onboarding_runs": [
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "status": "Em andamento",
            "manual_steps": {},
            "notes": "Fluxo demo criado automaticamente para orientar o onboarding do primeiro cliente.",
        }
    ],
}

ACTIVE_CONTRACT_STATUSES = {"ativo", "piloto"}


def _default_path() -> Path:
    return Path(__file__).with_name("platform_admin_store.json")


def _unique_by(items: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = tuple(str(item.get(name) or "") for name in keys)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def normalize_platform_admin_data(data: dict[str, Any] | None) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_PLATFORM_ADMIN_DATA)
    if isinstance(data, dict):
        if data.get("schema_version"):
            normalized["schema_version"] = int(data.get("schema_version") or 1)
        for key in ["tenants", "plants", "service_contracts", "users", "onboarding_runs"]:
            if isinstance(data.get(key), list):
                normalized[key] = list(data[key])
    normalized["schema_version"] = max(2, int(normalized.get("schema_version") or 1))

    normalized["tenants"] = _unique_by(
        [
            {
                "tenant_id": str(item.get("tenant_id") or "").strip(),
                "company_name": str(item.get("company_name") or "").strip(),
                "status": str(item.get("status") or "Ativo"),
                "environment": str(item.get("environment") or "Piloto"),
            }
            for item in normalized["tenants"]
            if str(item.get("tenant_id") or "").strip()
        ],
        "tenant_id",
    )
    normalized["plants"] = _unique_by(
        [
            {
                "tenant_id": str(item.get("tenant_id") or "").strip(),
                "plant_id": str(item.get("plant_id") or "").strip(),
                "plant_name": str(item.get("plant_name") or "").strip(),
                "city": str(item.get("city") or ""),
                "status": str(item.get("status") or "Ativa"),
            }
            for item in normalized["plants"]
            if str(item.get("tenant_id") or "").strip() and str(item.get("plant_id") or "").strip()
        ],
        "tenant_id",
        "plant_id",
    )
    normalized["service_contracts"] = _unique_by(
        [
            {
                "tenant_id": str(item.get("tenant_id") or "").strip(),
                "plant_id": str(item.get("plant_id") or "").strip(),
                "services": sorted(normalize_service_keys(item.get("services"))),
                "operational_intelligence": bool(
                    {SERVICE_CONDITION, SERVICE_LUBRICATION}.issubset(normalize_service_keys(item.get("services")))
                ),
                "status": str(item.get("status") or "Ativo"),
            }
            for item in normalized["service_contracts"]
            if str(item.get("tenant_id") or "").strip() and str(item.get("plant_id") or "").strip()
        ],
        "tenant_id",
        "plant_id",
    )
    normalized["users"] = _unique_by(
        [
            {
                "tenant_id": str(item.get("tenant_id") or "").strip(),
                "email": str(item.get("email") or "").strip().lower(),
                "name": str(item.get("name") or "").strip(),
                "role": str(item.get("role") or "operador").strip(),
                "status": str(item.get("status") or "Ativo"),
            }
            for item in normalized["users"]
            if str(item.get("tenant_id") or "").strip() and str(item.get("email") or "").strip()
        ],
        "tenant_id",
        "email",
    )
    normalized["onboarding_runs"] = _unique_by(
        [
            {
                "tenant_id": str(item.get("tenant_id") or "").strip(),
                "plant_id": str(item.get("plant_id") or "").strip(),
                "status": str(item.get("status") or "Em andamento"),
                "manual_steps": dict(item.get("manual_steps") or {}),
                "notes": str(item.get("notes") or ""),
            }
            for item in normalized["onboarding_runs"]
            if str(item.get("tenant_id") or "").strip() and str(item.get("plant_id") or "").strip()
        ],
        "tenant_id",
        "plant_id",
    )
    return normalized


class PlatformAdminRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = self._resolve_path(path)

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is None or str(path).strip() == "":
            return _default_path()
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return Path.cwd() / candidate

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return normalize_platform_admin_data(None)
        return normalize_platform_admin_data(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(normalize_platform_admin_data(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert_tenant(self, tenant: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        tenant_id = str(tenant.get("tenant_id") or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id é obrigatório.")
        data["tenants"] = [item for item in data["tenants"] if item.get("tenant_id") != tenant_id] + [tenant]
        self.save(data)
        return self.load()

    def upsert_plant(self, plant: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        tenant_id = str(plant.get("tenant_id") or "").strip()
        plant_id = str(plant.get("plant_id") or "").strip()
        if not tenant_id or not plant_id:
            raise ValueError("tenant_id e plant_id são obrigatórios.")
        data["plants"] = [
            item
            for item in data["plants"]
            if not (item.get("tenant_id") == tenant_id and item.get("plant_id") == plant_id)
        ] + [plant]
        self.save(data)
        return self.load()

    def upsert_contract(self, contract: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        tenant_id = str(contract.get("tenant_id") or "").strip()
        plant_id = str(contract.get("plant_id") or "").strip()
        if not tenant_id or not plant_id:
            raise ValueError("tenant_id e plant_id são obrigatórios.")
        data["service_contracts"] = [
            item
            for item in data["service_contracts"]
            if not (item.get("tenant_id") == tenant_id and item.get("plant_id") == plant_id)
        ] + [contract]
        self.save(data)
        return self.load()

    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        tenant_id = str(user.get("tenant_id") or "").strip()
        email = str(user.get("email") or "").strip().lower()
        if not tenant_id or not email:
            raise ValueError("tenant_id e email são obrigatórios.")
        data["users"] = [
            item
            for item in data["users"]
            if not (item.get("tenant_id") == tenant_id and item.get("email") == email)
        ] + [{**user, "email": email}]
        self.save(data)
        return self.load()

    def upsert_onboarding_run(self, run: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        tenant_id = str(run.get("tenant_id") or "").strip()
        plant_id = str(run.get("plant_id") or "").strip()
        if not tenant_id or not plant_id:
            raise ValueError("tenant_id e plant_id sÃ£o obrigatÃ³rios.")
        data["onboarding_runs"] = [
            item
            for item in data["onboarding_runs"]
            if not (item.get("tenant_id") == tenant_id and item.get("plant_id") == plant_id)
        ] + [run]
        self.save(data)
        return self.load()

    def onboarding_run_for(self, tenant_id: str, plant_id: str) -> dict[str, Any]:
        tenant_id = str(tenant_id or "").strip()
        plant_id = str(plant_id or "").strip()
        for run in self.load()["onboarding_runs"]:
            if run.get("tenant_id") == tenant_id and run.get("plant_id") == plant_id:
                return run
        return {
            "tenant_id": tenant_id,
            "plant_id": plant_id,
            "status": "Em andamento",
            "manual_steps": {},
            "notes": "",
        }

    def services_for_contract(self, tenant_id: str, plant_id: str) -> list[str] | None:
        tenant_id = str(tenant_id or "").strip()
        plant_id = str(plant_id or "").strip()
        if not tenant_id or not plant_id:
            return None

        for contract in self.load()["service_contracts"]:
            if contract.get("tenant_id") != tenant_id or contract.get("plant_id") != plant_id:
                continue
            if str(contract.get("status") or "").strip().lower() not in ACTIVE_CONTRACT_STATUSES:
                return []
            return list(contract.get("services") or [])

        return None

    def data_for_tenant(self, tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        tenant_id = str(tenant_id or "").strip()
        data = self.load()
        return {
            "tenants": [item for item in data["tenants"] if item.get("tenant_id") == tenant_id],
            "plants": [item for item in data["plants"] if item.get("tenant_id") == tenant_id],
            "service_contracts": [
                item for item in data["service_contracts"] if item.get("tenant_id") == tenant_id
            ],
            "users": [item for item in data["users"] if item.get("tenant_id") == tenant_id],
            "onboarding_runs": [item for item in data["onboarding_runs"] if item.get("tenant_id") == tenant_id],
        }
