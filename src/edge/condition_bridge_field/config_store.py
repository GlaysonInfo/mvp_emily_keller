from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_PATH = "config/field_condition_config.json"
EXAMPLE_PATH = "config/field_condition_config.example.json"


def config_path(path: str | None = None) -> Path:
    selected = path or os.getenv("CONDITION_FIELD_CONFIG") or DEFAULT_PATH
    return Path(selected)


def load_condition_field_config(path: str | None = None) -> dict[str, Any]:
    selected = config_path(path)
    if selected.exists():
        return json.loads(selected.read_text(encoding="utf-8"))

    example = Path(EXAMPLE_PATH)
    if example.exists():
        return json.loads(example.read_text(encoding="utf-8"))

    raise FileNotFoundError(f"Condition field config not found: {selected}")


def save_condition_field_config(config: dict[str, Any], path: str | None = None) -> None:
    selected = config_path(path)
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_condition_field_config(config: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def issue(level: str, area: str, message: str, recommendation: str) -> None:
        issues.append(
            {
                "level": level,
                "area": area,
                "message": message,
                "recommendation": recommendation,
            }
        )

    aws = config.get("aws", {})
    if aws.get("region") != "us-east-1":
        issue("ERRO", "AWS", "Regiao AWS diferente de us-east-1.", "Ajustar aws.region para us-east-1.")

    client = config.get("client", {})
    if not client.get("tenant_id"):
        issue("ERRO", "Cliente", "tenant_id vazio.", "Definir tenant_id tecnico estavel.")

    plant = config.get("plant", {})
    if not plant.get("plant_id"):
        issue("ERRO", "Planta", "plant_id vazio.", "Definir plant_id tecnico estavel.")

    gateway = config.get("gateway", {})
    if not gateway.get("source_id"):
        issue("ERRO", "Gateway", "source_id do gateway vazio.", "Definir source_id do gateway de equipamentos.")

    protocol = gateway.get("protocol", "http_json")
    if protocol not in {"http_json", "simulated_json"}:
        issue("ERRO", "Gateway", f"Protocolo nao suportado: {protocol}.", "Usar http_json ou simulated_json.")

    endpoint = str(gateway.get("endpoint") or "")
    if protocol == "http_json" and not endpoint.startswith(("http://", "https://")):
        issue("ERRO", "Gateway", "Endpoint HTTP do gateway invalido.", "Usar URL iniciada por http:// ou https://.")

    ingest = config.get("ingest_api", {})
    if "/condition/ingest" not in str(ingest.get("endpoint") or ""):
        issue("ERRO", "Ingest API", "Endpoint /condition/ingest vazio ou invalido.", "Preencher endpoint publico da EC2.")

    assets = [asset for asset in config.get("assets", []) if asset.get("enabled", True)]
    if not assets:
        issue("ERRO", "Ativos", "Nenhum equipamento habilitado.", "Habilitar pelo menos um ativo monitorado.")

    for asset in assets:
        asset_id = asset.get("asset_id")
        if not asset_id:
            issue("ERRO", "Ativos", "Ativo sem asset_id.", "Preencher asset_id tecnico.")

        signals = [signal for signal in asset.get("signals", []) if signal.get("metric")]
        if not signals:
            issue("ERRO", "Sinais", f"{asset_id or 'ativo'} sem sinais mapeados.", "Mapear metric, tag e unit.")

        mapped_metrics = {signal.get("metric") for signal in signals}
        for recommended in ["vibration_rms_mm_s", "temperature_c"]:
            if recommended not in mapped_metrics:
                issue(
                    "ATENÇÃO",
                    "Sinais",
                    f"{asset_id or 'ativo'} sem {recommended}.",
                    "Mapear vibracao e temperatura para diagnostico minimo.",
                )

        for signal in signals:
            if not signal.get("tag"):
                issue("ERRO", "Sinais", f"{asset_id or 'ativo'}: {signal.get('metric')} sem tag.", "Preencher tag do gateway.")

    return issues
