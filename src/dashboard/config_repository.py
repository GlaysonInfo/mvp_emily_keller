from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "client": {
        "tenant_id": "cliente_demo",
        "company_name": "Cliente Demonstração",
        "cnpj": "",
        "segment": "Indústria",
        "responsible_name": "Responsável Técnico",
        "responsible_email": "",
        "responsible_phone": "",
        "timezone": "America/Sao_Paulo",
        "environment_mode": "Demonstração",
    },
    "plant": {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "plant_name": "Bancada Virtual",
        "country": "Brasil",
        "state": "MG",
        "city": "Betim",
        "address": "",
        "latitude": "",
        "longitude": "",
        "operation_regime": "24x7",
        "environment_conditions": "Laboratório / demonstração",
    },
    "data_sources": [],
    "assets": [],
    "signal_map": [],
    "parameters_alerts": [],
}


def _default_path() -> Path:
    return Path(__file__).with_name("config_store.json")


def normalize_config(data: dict[str, Any] | None) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_CONFIG)

    if not isinstance(data, dict):
        return normalized

    for key, value in data.items():
        if key in {"client", "plant"} and isinstance(value, dict):
            normalized[key].update(value)
        elif key == "asset_signal_map" and "signal_map" not in data:
            normalized["signal_map"] = list(value or [])
        else:
            normalized[key] = value

    for list_key in ["data_sources", "assets", "signal_map", "parameters_alerts"]:
        if not isinstance(normalized.get(list_key), list):
            normalized[list_key] = []

    return normalized


class ConfigRepository:
    """Repositório JSON local para a primeira entrega de Configurações."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = self._resolve_path(path)

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is None or str(path).strip() == "":
            return _default_path()

        candidate = Path(path)

        if candidate.is_absolute():
            return candidate

        cwd_candidate = Path.cwd() / candidate

        if cwd_candidate.exists():
            return cwd_candidate

        return Path(__file__).parent / candidate

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return normalize_config(None)

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return normalize_config(data)

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_config(data)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def client(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict((data or self.load()).get("client", {}))

    def plant(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict((data or self.load()).get("plant", {}))

    def data_sources(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("data_sources", []))

    def assets(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("assets", []))

    def signal_map(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        loaded = data or self.load()
        return list(loaded.get("signal_map") or loaded.get("asset_signal_map") or [])

    def parameters_alerts(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("parameters_alerts", []))

    def get_data_source(self, source_id: str, data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return next((source for source in self.data_sources(data) if source.get("source_id") == source_id), None)

    def get_asset(self, asset_id: str, data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return next((asset for asset in self.assets(data) if asset.get("asset_id") == asset_id), None)

    def signal_map_for_asset(self, asset_id: str, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [item for item in self.signal_map(data) if item.get("asset_id") == asset_id]

    def default_asset_id(self, data: dict[str, Any] | None = None) -> str:
        assets = self.assets(data)
        active = next((asset for asset in assets if asset.get("status", "Ativo") == "Ativo"), None)
        fallback = active or (assets[0] if assets else {})
        return str(fallback.get("asset_id") or "motor_001")

    def environment_label(self, data: dict[str, Any] | None = None) -> str:
        loaded = data or self.load()
        client = loaded.get("client", {})
        plant = loaded.get("plant", {})
        mode = client.get("environment_mode") or client.get("environment") or "Demonstração"
        plant_name = plant.get("plant_name") or plant.get("name") or "Bancada Virtual"
        return f"{mode} - {plant_name}"

    def validate(self, data: dict[str, Any] | None = None) -> list[dict[str, str]]:
        loaded = data or self.load()
        issues: list[dict[str, str]] = []
        source_ids = {str(source.get("source_id")) for source in self.data_sources(loaded) if source.get("source_id")}
        asset_ids = {str(asset.get("asset_id")) for asset in self.assets(loaded) if asset.get("asset_id")}

        if not loaded.get("client", {}).get("tenant_id"):
            issues.append({"severity": "error", "message": "Cliente sem tenant_id configurado."})

        if not loaded.get("plant", {}).get("plant_id"):
            issues.append({"severity": "error", "message": "Planta sem plant_id configurado."})

        for asset in self.assets(loaded):
            source_id = asset.get("source_id")
            asset_id = asset.get("asset_id", "-")

            if source_id and source_id not in source_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Ativo {asset_id} referencia fonte inexistente: {source_id}.",
                    }
                )

        seen_signal_keys: set[tuple[str, str, str]] = set()

        for signal in self.signal_map(loaded):
            asset_id = str(signal.get("asset_id") or "")
            source_id = str(signal.get("source_id") or "")
            metric = str(signal.get("metric") or signal.get("internal_metric") or "")

            if asset_id and asset_id not in asset_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Mapeamento de sinal referencia ativo inexistente: {asset_id}.",
                    }
                )

            if source_id and source_id not in source_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Mapeamento de sinal referencia fonte inexistente: {source_id}.",
                    }
                )

            signal_key = (asset_id, source_id, metric)

            if signal_key in seen_signal_keys:
                issues.append(
                    {
                        "severity": "warning",
                        "message": f"Mapeamento duplicado para {asset_id} / {source_id} / {metric}.",
                    }
                )

            seen_signal_keys.add(signal_key)

        return issues
