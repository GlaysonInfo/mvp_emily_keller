from __future__ import annotations

import os
from typing import Any

from src.dashboard.config_repository import ConfigRepository


RegistryWarning = dict[str, str]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _warning(code: str, message: str, field: str = "") -> RegistryWarning:
    item = {"severity": "warning", "code": code, "message": message}
    if field:
        item["field"] = field
    return item


def _config_path_from_env() -> str | None:
    return os.getenv("CONDITION_REGISTRY_CONFIG_PATH") or os.getenv("DASHBOARD_CONFIG_STORE") or None


def load_condition_registry_config() -> dict[str, Any]:
    return ConfigRepository(_config_path_from_env()).load()


def validate_condition_payload_against_registry(
    payload: Any,
    *,
    config: dict[str, Any] | None = None,
) -> list[RegistryWarning]:
    """Validate indoor/field condition payloads against the operational registry.

    This is intentionally warning-only for assisted production: it gives the
    Sentinela team evidence of missing cadastro without interrupting telemetry.
    """

    try:
        loaded = config if config is not None else load_condition_registry_config()
    except Exception as exc:
        return [
            _warning(
                "registry_config_unavailable",
                f"Cadastro operacional indisponivel para validacao: {exc}",
            )
        ]

    warnings: list[RegistryWarning] = []
    tenant_id = _text(getattr(payload, "tenant_id", ""))
    plant_id = _text(getattr(payload, "plant_id", ""))
    asset_id = _text(getattr(payload, "asset_id", ""))
    source_id = _text(getattr(payload, "source", ""))
    received_metrics = {_text(metric.name) for metric in getattr(payload, "metrics", []) if _text(metric.name)}

    client = loaded.get("client") or {}
    plant = loaded.get("plant") or {}
    assets = [item for item in loaded.get("assets", []) or [] if isinstance(item, dict)]
    sources = [item for item in loaded.get("data_sources", []) or [] if isinstance(item, dict)]
    signal_map = [item for item in loaded.get("signal_map", []) or [] if isinstance(item, dict)]

    tenant_ids = {_text(client.get("tenant_id"))}
    tenant_ids.update(_text(item.get("tenant_id")) for item in assets + sources if _text(item.get("tenant_id")))
    tenant_ids.discard("")

    plant_ids = {_text(plant.get("plant_id"))}
    plant_ids.update(_text(item.get("plant_id")) for item in assets + sources if _text(item.get("plant_id")))
    plant_ids.discard("")

    if tenant_ids and tenant_id not in tenant_ids:
        warnings.append(
            _warning(
                "tenant_not_registered",
                f"tenant_id {tenant_id} nao encontrado no cadastro operacional.",
                "tenant_id",
            )
        )

    if plant_ids and plant_id not in plant_ids:
        warnings.append(
            _warning(
                "plant_not_registered",
                f"plant_id {plant_id} nao encontrado no cadastro operacional.",
                "plant_id",
            )
        )

    asset = next(
        (
            item
            for item in assets
            if _text(item.get("asset_id")) == asset_id
            and _text(item.get("tenant_id") or tenant_id) == tenant_id
            and _text(item.get("plant_id") or plant_id) == plant_id
        ),
        None,
    )
    if asset is None:
        asset = next((item for item in assets if _text(item.get("asset_id")) == asset_id), None)

    if asset is None:
        warnings.append(
            _warning(
                "asset_not_registered",
                f"asset_id {asset_id} nao cadastrado para monitoramento.",
                "asset_id",
            )
        )
    else:
        asset_tenant = _text(asset.get("tenant_id"))
        asset_plant = _text(asset.get("plant_id"))
        asset_source = _text(asset.get("source_id"))

        if asset_tenant and asset_tenant != tenant_id:
            warnings.append(
                _warning(
                    "asset_tenant_mismatch",
                    f"Ativo {asset_id} pertence ao tenant {asset_tenant}, mas o payload veio como {tenant_id}.",
                    "tenant_id",
                )
            )
        if asset_plant and asset_plant != plant_id:
            warnings.append(
                _warning(
                    "asset_plant_mismatch",
                    f"Ativo {asset_id} pertence a planta {asset_plant}, mas o payload veio como {plant_id}.",
                    "plant_id",
                )
            )
        if asset_source and source_id and asset_source != source_id:
            warnings.append(
                _warning(
                    "asset_source_mismatch",
                    f"Ativo {asset_id} esta vinculado a fonte {asset_source}, mas o payload veio de {source_id}.",
                    "source",
                )
            )

    source = next((item for item in sources if _text(item.get("source_id")) == source_id), None)
    if source is None:
        warnings.append(
            _warning(
                "source_not_registered",
                f"Fonte/gateway {source_id} nao cadastrado para a planta.",
                "source",
            )
        )
    else:
        source_tenant = _text(source.get("tenant_id"))
        source_plant = _text(source.get("plant_id"))
        if source_tenant and source_tenant != tenant_id:
            warnings.append(
                _warning(
                    "source_tenant_mismatch",
                    f"Fonte {source_id} pertence ao tenant {source_tenant}, mas o payload veio como {tenant_id}.",
                    "source",
                )
            )
        if source_plant and source_plant != plant_id:
            warnings.append(
                _warning(
                    "source_plant_mismatch",
                    f"Fonte {source_id} pertence a planta {source_plant}, mas o payload veio como {plant_id}.",
                    "source",
                )
            )

    expected_metrics = {
        _text(item.get("metric") or item.get("internal_metric"))
        for item in signal_map
        if _text(item.get("asset_id")) == asset_id
        and _text(item.get("source_id") or source_id) == source_id
        and item.get("enabled", True) is not False
        and _text(item.get("metric") or item.get("internal_metric"))
    }

    if not expected_metrics:
        warnings.append(
            _warning(
                "asset_without_expected_metrics",
                f"Ativo {asset_id} ainda nao possui mapa de sinais para a fonte {source_id}.",
                "metrics",
            )
        )
    else:
        unexpected_metrics = sorted(received_metrics - expected_metrics)
        if unexpected_metrics:
            warnings.append(
                _warning(
                    "unexpected_metrics",
                    "Metricas recebidas sem cadastro no mapa de sinais: " + ", ".join(unexpected_metrics),
                    "metrics",
                )
            )

    return warnings
