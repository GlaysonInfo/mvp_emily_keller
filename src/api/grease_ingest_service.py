from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .grease_ingest_models import GreaseIngestPayload, GreaseIngestResponse


def ensure_region() -> str:
    # Região real do piloto. Não usar fallback sa-east-1 neste módulo.
    region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = region
    return region


def import_lubrication_modules():
    import sys
    here = Path(__file__).resolve()
    candidates = [here.parents[1], here.parents[2] / "src", Path.cwd() / "src", Path.cwd() / "src" / "dashboard"]
    for c in candidates:
        if c.exists() and str(c) not in sys.path:
            sys.path.insert(0, str(c))
    try:
        from dashboard.lubrication.lubrication_config import load_lubrication_config
        from dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle
        from dashboard.lubrication.lubrication_repository import LubricationRepository
        return load_lubrication_config, evaluate_lubrication_cycle, LubricationRepository
    except Exception:
        from lubrication.lubrication_config import load_lubrication_config
        from lubrication.lubrication_engine import evaluate_lubrication_cycle
        from lubrication.lubrication_repository import LubricationRepository
        return load_lubrication_config, evaluate_lubrication_cycle, LubricationRepository


def load_config_for_payload(payload: GreaseIngestPayload) -> dict[str, Any]:
    load_lubrication_config, _, _ = import_lubrication_modules()
    config_path = os.getenv("LUBRICATION_CONFIG_PATH", "config/lubrication_pilot_config.json")
    config = load_lubrication_config(config_path)
    config["tenant_id"] = payload.tenant_id
    config["plant_id"] = payload.plant_id
    config["asset_id"] = payload.asset_id
    config["source_id"] = payload.source_id
    if not config.get("asset_name"):
        config["asset_name"] = payload.asset_id
    return config


def process_grease_ingest(payload: GreaseIngestPayload) -> GreaseIngestResponse:
    ensure_region()
    _, evaluate_lubrication_cycle, LubricationRepository = import_lubrication_modules()
    config = load_config_for_payload(payload)
    cycle_result = evaluate_lubrication_cycle(payload.model_dump(), config)
    repo = LubricationRepository()
    repo.save_cycle_result(cycle_result)
    active_alerts = cycle_result.get("active_alerts", [])
    return GreaseIngestResponse(
        ok=True,
        message="Ciclo de lubrificação recebido, avaliado e salvo com sucesso.",
        tenant_id=cycle_result.get("tenant_id"),
        plant_id=cycle_result.get("plant_id"),
        asset_id=cycle_result.get("asset_id"),
        source_id=cycle_result.get("source_id"),
        cycle_id=cycle_result.get("cycle_id"),
        status_label=cycle_result.get("status_label"),
        outlet_count=int(cycle_result.get("outlet_count") or 0),
        active_alerts_count=len(active_alerts),
        saved_state=True,
        saved_cycle=True,
        saved_alerts=True,
        details={
            "normal_count": cycle_result.get("normal_count"),
            "attention_count": cycle_result.get("attention_count"),
            "alert_count": cycle_result.get("alert_count"),
            "critical_count": cycle_result.get("critical_count"),
            "max_pressure_bar": cycle_result.get("max_pressure_bar"),
            "max_anomaly_score": cycle_result.get("max_anomaly_score"),
            "recommendation": cycle_result.get("recommendation"),
            "active_alerts": active_alerts,
        },
    )
