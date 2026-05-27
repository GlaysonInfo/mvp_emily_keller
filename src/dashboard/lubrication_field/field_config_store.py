
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_PATH = "config/field_lubrication_config.json"


def config_path(path: str | None = None) -> Path:
    selected = path or os.getenv("GREASE_FIELD_CONFIG") or DEFAULT_PATH
    return Path(selected)


def load_field_config(path: str | None = None) -> dict[str, Any]:
    p = config_path(path)

    if not p.exists():
        example = Path("config/field_lubrication_config.example.json")
        if example.exists():
            return json.loads(example.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Configuração de campo não encontrada: {p}")

    return json.loads(p.read_text(encoding="utf-8"))


def save_field_config(config: dict[str, Any], path: str | None = None) -> None:
    p = config_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_field_config(config: dict[str, Any]) -> list[dict[str, str]]:
    issues = []

    def issue(level, area, message, recommendation):
        issues.append({
            "level": level,
            "area": area,
            "message": message,
            "recommendation": recommendation,
        })

    aws = config.get("aws", {})
    if aws.get("region") != "us-east-1":
        issue("ERRO", "AWS", "Região AWS diferente de us-east-1.", "Ajustar aws.region para us-east-1.")

    gateway = config.get("gateway", {})
    if not gateway.get("endpoint"):
        issue("ATENÇÃO", "Gateway", "Endpoint do gateway IO-Link vazio.", "Preencher o endpoint real do gateway ou bridge local.")

    ingest = config.get("ingest_api", {})
    if not ingest.get("endpoint"):
        issue("ERRO", "Ingest API", "Endpoint /grease/ingest vazio.", "Preencher endpoint da EC2 ou do proxy.")

    system = config.get("lubrication_system", {})
    if float(system.get("recommended_sensor_range_bar") or 0) < 160:
        issue("ATENÇÃO", "Sensor", "Faixa recomendada do sensor inferior a 160 bar.", "Para sistema que pode chegar a 100 bar, considerar 0–250 bar.")

    outlets = config.get("outlets", [])
    if not outlets:
        issue("ERRO", "Saídas", "Nenhuma saída de graxa cadastrada.", "Cadastrar pelo menos uma saída monitorada.")

    for outlet in outlets:
        if not outlet.get("enabled", True):
            continue
        if not outlet.get("gateway_tag_pressure"):
            issue("ERRO", "Mapeamento", f"{outlet.get('outlet_id')} sem tag de pressão.", "Preencher gateway_tag_pressure.")
        if not outlet.get("physical_gauge_present", False):
            issue("ATENÇÃO", "Instalação", f"{outlet.get('outlet_id')} sem manômetro físico marcado.", "No piloto, manter o manômetro físico.")
        if float(outlet.get("sensor_range_bar") or 0) < 160:
            issue("ATENÇÃO", "Sensor", f"{outlet.get('outlet_id')} com faixa de sensor baixa.", "Usar 0–250 bar no piloto, salvo justificativa técnica.")

    outlet_ids = {outlet.get("outlet_id") for outlet in outlets}
    for link in config.get("equipment_links", []) or []:
        if not link.get("enabled", True):
            continue
        if not link.get("asset_id"):
            issue("ERRO", "Vínculos", "Vínculo sem asset_id do equipamento.", "Preencher o equipamento monitorado.")
        if link.get("outlet_id") not in outlet_ids:
            issue("ERRO", "Vínculos", f"Vínculo aponta para saída inexistente: {link.get('outlet_id')}.", "Selecionar uma saída cadastrada.")
        if float(link.get("target_grease_g_per_cycle") or 0) <= 0:
            issue("ATENÇÃO", "Vínculos", f"{link.get('asset_id')} sem dose alvo em gramas.", "Informar dose inicial para análise de eficiência.")
        if float(link.get("cycle_interval_h") or 0) <= 0:
            issue("ATENÇÃO", "Vínculos", f"{link.get('asset_id')} sem intervalo de ciclo.", "Informar intervalo inicial de lubrificação.")

    return issues
