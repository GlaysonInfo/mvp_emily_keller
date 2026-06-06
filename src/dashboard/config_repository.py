from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TECHNICAL_SECTIONS = (
    "data_sources",
    "assets",
    "sensors",
    "signal_map",
    "parameters_alerts",
)
TECHNICAL_SECTION_KEYS = {
    "data_sources": ("source_id",),
    "assets": ("asset_id",),
    "sensors": ("sensor_id",),
    "signal_map": ("asset_id", "source_id", "metric", "sensor_id"),
    "parameters_alerts": ("asset_id", "metric"),
}
TECHNICAL_HISTORY_LIMIT = 250


DEFAULT_CONFIG: dict[str, Any] = {
    "configuration_version": 0,
    "technical_change_history": [],
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
    "sensors": [],
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

    for list_key in [
        "data_sources",
        "assets",
        "sensors",
        "signal_map",
        "parameters_alerts",
        "technical_change_history",
    ]:
        if not isinstance(normalized.get(list_key), list):
            normalized[list_key] = []

    try:
        normalized["configuration_version"] = max(0, int(normalized.get("configuration_version") or 0))
    except (TypeError, ValueError):
        normalized["configuration_version"] = 0

    for sensor in normalized["sensors"]:
        if not isinstance(sensor, dict):
            continue
        if "process_expected_min" not in sensor and "expected_min" in sensor:
            sensor["process_expected_min"] = sensor.get("expected_min")
        if "process_expected_max" not in sensor and "expected_max" in sensor:
            sensor["process_expected_max"] = sensor.get("expected_max")

    return normalized


def _entity_key(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    return "#".join(str(item.get(key) or "-") for key in keys)


def _section_changes(
    before: dict[str, Any],
    after: dict[str, Any],
    section: str,
) -> list[dict[str, Any]]:
    keys = TECHNICAL_SECTION_KEYS[section]
    before_items = {
        _entity_key(item, keys): deepcopy(item)
        for item in list(before.get(section) or [])
        if isinstance(item, dict)
    }
    after_items = {
        _entity_key(item, keys): deepcopy(item)
        for item in list(after.get(section) or [])
        if isinstance(item, dict)
    }
    changes: list[dict[str, Any]] = []

    for entity_key in sorted(set(before_items) | set(after_items)):
        old_item = before_items.get(entity_key)
        new_item = after_items.get(entity_key)
        if old_item == new_item:
            continue
        operation = "updated"
        if old_item is None:
            operation = "created"
        elif new_item is None:
            operation = "removed"
        changes.append(
            {
                "section": section,
                "entity_key": entity_key,
                "operation": operation,
                "before": old_item,
                "after": new_item,
            }
        )

    return changes


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
        self._write(normalize_config(data))

    def _write(self, normalized: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.path)

    def save_versioned(
        self,
        data: dict[str, Any],
        *,
        change_type: str,
        target: str,
        reason: str,
        actor: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        plant_id: str | None = None,
        sections: tuple[str, ...] = TECHNICAL_SECTIONS,
    ) -> dict[str, Any] | None:
        before = self.load()
        after = normalize_config(data)
        clean_reason = str(reason).strip()
        if not clean_reason:
            raise ValueError("O motivo da alteração técnica é obrigatório.")

        changes: list[dict[str, Any]] = []
        for section in sections:
            if section not in TECHNICAL_SECTION_KEYS:
                raise ValueError(f"Seção técnica não suportada para versionamento: {section}.")
            changes.extend(_section_changes(before, after, section))

        if not changes:
            return None

        actor = dict(actor or {})
        revision_number = int(before.get("configuration_version") or 0) + 1
        revision = {
            "revision": revision_number,
            "change_id": uuid.uuid4().hex[:12],
            "changed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "changed_by": actor.get("email") or "anon",
            "changed_by_role": actor.get("role"),
            "tenant_id": tenant_id or actor.get("tenant_id") or "-",
            "plant_id": plant_id or "-",
            "change_type": str(change_type),
            "target": str(target),
            "reason": clean_reason,
            "changes": changes,
        }
        history = list(before.get("technical_change_history") or [])
        history.append(revision)
        after["configuration_version"] = revision_number
        after["technical_change_history"] = history[-TECHNICAL_HISTORY_LIMIT:]
        self._write(after)
        return deepcopy(revision)

    def client(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict((data or self.load()).get("client", {}))

    def plant(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict((data or self.load()).get("plant", {}))

    def data_sources(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("data_sources", []))

    def assets(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("assets", []))

    def sensors(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("sensors", []))

    def signal_map(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        loaded = data or self.load()
        return list(loaded.get("signal_map") or loaded.get("asset_signal_map") or [])

    def parameters_alerts(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("parameters_alerts", []))

    def technical_change_history(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list((data or self.load()).get("technical_change_history", []))

    def get_data_source(self, source_id: str, data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return next((source for source in self.data_sources(data) if source.get("source_id") == source_id), None)

    def get_asset(self, asset_id: str, data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return next((asset for asset in self.assets(data) if asset.get("asset_id") == asset_id), None)

    def signal_map_for_asset(self, asset_id: str, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [item for item in self.signal_map(data) if item.get("asset_id") == asset_id]

    def sensors_for_asset(self, asset_id: str, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [item for item in self.sensors(data) if item.get("asset_id") == asset_id]

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
        sensor_ids = {str(sensor.get("sensor_id")) for sensor in self.sensors(loaded) if sensor.get("sensor_id")}

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

        seen_signal_keys: set[tuple[str, str, str, str]] = set()

        for sensor in self.sensors(loaded):
            sensor_id = str(sensor.get("sensor_id") or "-")
            asset_id = str(sensor.get("asset_id") or "")
            source_id = str(sensor.get("source_id") or "")

            if asset_id and asset_id not in asset_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Sensor {sensor_id} referencia ativo inexistente: {asset_id}.",
                    }
                )

            if source_id and source_id not in source_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Sensor {sensor_id} referencia fonte inexistente: {source_id}.",
                    }
                )

            for range_label, minimum_key, maximum_key in [
                ("faixa esperada do processo", "process_expected_min", "process_expected_max"),
                ("faixa física do instrumento", "instrument_range_min", "instrument_range_max"),
            ]:
                minimum = sensor.get(minimum_key)
                maximum = sensor.get(maximum_key)
                if minimum is None or maximum is None:
                    continue
                try:
                    invalid_range = float(minimum) > float(maximum)
                except (TypeError, ValueError):
                    invalid_range = True
                if invalid_range:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Sensor {sensor_id} possui {range_label} inválida.",
                        }
                    )

            process_min = sensor.get("process_expected_min")
            process_max = sensor.get("process_expected_max")
            instrument_min = sensor.get("instrument_range_min")
            instrument_max = sensor.get("instrument_range_max")
            if all(
                value is not None
                for value in [process_min, process_max, instrument_min, instrument_max]
            ):
                try:
                    process_outside_instrument = (
                        float(process_min) < float(instrument_min)
                        or float(process_max) > float(instrument_max)
                    )
                except (TypeError, ValueError):
                    process_outside_instrument = True
                if process_outside_instrument:
                    issues.append(
                        {
                            "severity": "error",
                            "message": (
                                f"Sensor {sensor_id} possui faixa do processo fora da faixa física "
                                "do instrumento."
                            ),
                        }
                    )

        for signal in self.signal_map(loaded):
            asset_id = str(signal.get("asset_id") or "")
            source_id = str(signal.get("source_id") or "")
            metric = str(signal.get("metric") or signal.get("internal_metric") or "")
            sensor_id = str(signal.get("sensor_id") or "")

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

            if sensor_id and sensor_id not in sensor_ids:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Mapeamento de sinal referencia sensor inexistente: {sensor_id}.",
                    }
                )

            signal_key = (asset_id, source_id, metric, sensor_id)

            if signal_key in seen_signal_keys:
                issues.append(
                    {
                        "severity": "warning",
                        "message": (
                            f"Mapeamento duplicado para {asset_id} / {source_id} / "
                            f"{metric} / {sensor_id or 'sem sensor'}."
                        ),
                    }
                )

            seen_signal_keys.add(signal_key)

        return issues
