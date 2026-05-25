from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any


TECHNICAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MINIMUM_SIGNAL_METRICS = {"rpm", "vibration_rms_mm_s", "temperature_c"}
ISSUE_ORDER = {"error": 0, "warning": 1, "info": 2}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_accents(value: str) -> bool:
    normalized = unicodedata.normalize("NFKD", value)
    return any(unicodedata.combining(char) for char in normalized)


def is_valid_technical_id(value: Any) -> bool:
    return bool(TECHNICAL_ID_RE.fullmatch(_text(value)))


def _issue(
    issues: list[dict[str, str]],
    *,
    severity: str,
    area: str,
    field: str,
    message: str,
    suggestion: str = "",
    item: str = "",
) -> None:
    issues.append(
        {
            "severity": severity,
            "area": area,
            "item": item,
            "field": field,
            "message": message,
            "suggestion": suggestion,
        }
    )


def _validate_technical_id(
    issues: list[dict[str, str]],
    *,
    value: Any,
    area: str,
    field: str,
    item: str = "",
) -> None:
    text = _text(value)

    if not text:
        _issue(
            issues,
            severity="error",
            area=area,
            item=item,
            field=field,
            message=f"{field} vazio.",
            suggestion="Use uma chave técnica estável, por exemplo cliente_demo, lab_virtual ou motor_001.",
        )
        return

    reasons: list[str] = []
    if text != text.lower():
        reasons.append("contém maiúsculas")
    if any(char.isspace() for char in text):
        reasons.append("contém espaço")
    if _has_accents(text):
        reasons.append("contém acento")
    if not TECHNICAL_ID_RE.fullmatch(text):
        reasons.append("contém caractere especial inválido")

    if reasons:
        _issue(
            issues,
            severity="error",
            area=area,
            item=item,
            field=field,
            message=f"{field} inválido: {', '.join(sorted(set(reasons)))}.",
            suggestion="Use apenas minúsculas, números, hífen ou sublinhado, sem espaços ou acentos.",
        )


def _duplicate_issues(
    issues: list[dict[str, str]],
    *,
    area: str,
    field: str,
    values: list[str],
) -> None:
    counts = Counter(value for value in values if value)

    for value, count in counts.items():
        if count > 1:
            _issue(
                issues,
                severity="error",
                area=area,
                item=value,
                field=field,
                message=f"{field} duplicado: {value}.",
                suggestion="Cada chave técnica deve identificar um único registro.",
            )


def _has_any_limit(rule: dict[str, Any]) -> bool:
    fields = [
        "attention_min",
        "alert_min",
        "critical_min",
        "attention_max",
        "alert_max",
        "critical_max",
        "normal_min",
        "normal_max",
    ]
    return any(_number(rule.get(field)) not in {None, 0.0} for field in fields)


def validate_config_consistency(data: dict[str, Any] | None) -> dict[str, Any]:
    loaded = data or {}
    issues: list[dict[str, str]] = []

    client = loaded.get("client") if isinstance(loaded.get("client"), dict) else {}
    plant = loaded.get("plant") if isinstance(loaded.get("plant"), dict) else {}
    sources = loaded.get("data_sources") if isinstance(loaded.get("data_sources"), list) else []
    assets = loaded.get("assets") if isinstance(loaded.get("assets"), list) else []
    signal_map = loaded.get("signal_map") if isinstance(loaded.get("signal_map"), list) else []
    parameters = loaded.get("parameters_alerts") if isinstance(loaded.get("parameters_alerts"), list) else []

    tenant_id = _text(client.get("tenant_id"))
    plant_id = _text(plant.get("plant_id"))

    _validate_technical_id(issues, value=tenant_id, area="Cliente", field="tenant_id")

    if not _text(client.get("company_name")):
        _issue(
            issues,
            severity="warning",
            area="Cliente",
            field="company_name",
            message="Nome da empresa não informado.",
            suggestion="Use este campo para o nome comercial; mantenha tenant_id como chave técnica.",
        )

    _validate_technical_id(issues, value=plant_id, area="Planta", field="plant_id")

    plant_tenant = _text(plant.get("tenant_id"))
    if tenant_id and plant_tenant and plant_tenant != tenant_id:
        _issue(
            issues,
            severity="error",
            area="Planta",
            item=plant_id,
            field="tenant_id",
            message=f"Planta usa tenant_id {plant_tenant}, diferente do cliente {tenant_id}.",
            suggestion="Mantenha planta, ativos e dados operacionais no mesmo tenant_id técnico.",
        )

    source_ids = [_text(source.get("source_id")) for source in sources if isinstance(source, dict)]
    asset_ids = [_text(asset.get("asset_id")) for asset in assets if isinstance(asset, dict)]
    source_id_set = {value for value in source_ids if value}
    asset_id_set = {value for value in asset_ids if value}

    _duplicate_issues(issues, area="Fontes de Dados", field="source_id", values=source_ids)
    _duplicate_issues(issues, area="Ativos", field="asset_id", values=asset_ids)

    for source in sources:
        if not isinstance(source, dict):
            continue

        source_id = _text(source.get("source_id"))
        _validate_technical_id(issues, value=source_id, area="Fontes de Dados", item=source_id, field="source_id")

        protocol = _text(source.get("protocol"))
        if not protocol:
            _issue(
                issues,
                severity="error",
                area="Fontes de Dados",
                item=source_id,
                field="protocol",
                message="Fonte de dados sem protocolo.",
                suggestion="Informe OPC UA, MQTT, HTTP/HTTPS, CSV, Manual ou equivalente.",
            )

        endpoint = _text(source.get("endpoint"))
        if protocol not in {"Interno", "Manual"} and not endpoint:
            _issue(
                issues,
                severity="warning",
                area="Fontes de Dados",
                item=source_id,
                field="endpoint",
                message="Fonte de dados sem endpoint/caminho configurado.",
                suggestion="Informe URL, broker, servidor, caminho CSV ou referência operacional.",
            )

        if not _text(source.get("status")):
            _issue(
                issues,
                severity="warning",
                area="Fontes de Dados",
                item=source_id,
                field="status",
                message="Fonte de dados sem status cadastral.",
                suggestion="Informe se está ativa, configurada, aguardando credencial, falha ou inativa.",
            )

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        asset_id = _text(asset.get("asset_id"))
        _validate_technical_id(issues, value=asset_id, area="Ativos", item=asset_id, field="asset_id")

        if not _text(asset.get("asset_name")):
            _issue(
                issues,
                severity="warning",
                area="Ativos",
                item=asset_id,
                field="asset_name",
                message="Ativo sem nome operacional.",
                suggestion="Use asset_name para o nome visível ao cliente; preserve asset_id como chave técnica.",
            )

        source_id = _text(asset.get("source_id"))
        if not source_id or source_id not in source_id_set:
            _issue(
                issues,
                severity="error",
                area="Ativos",
                item=asset_id,
                field="source_id",
                message=f"Ativo referencia fonte inexistente ou vazia: {source_id or '-'}",
                suggestion="Associe o ativo a uma fonte de dados cadastrada.",
            )

        asset_tenant = _text(asset.get("tenant_id"))
        if tenant_id and asset_tenant and asset_tenant != tenant_id:
            _issue(
                issues,
                severity="error",
                area="Ativos",
                item=asset_id,
                field="tenant_id",
                message=f"Ativo usa tenant_id {asset_tenant}, diferente do cliente {tenant_id}.",
                suggestion="Não edite tenant_id livremente depois de gravar dados operacionais.",
            )

        asset_plant = _text(asset.get("plant_id"))
        if plant_id and asset_plant and asset_plant != plant_id:
            _issue(
                issues,
                severity="error",
                area="Ativos",
                item=asset_id,
                field="plant_id",
                message=f"Ativo usa plant_id {asset_plant}, diferente da planta {plant_id}.",
                suggestion="Mantenha todos os ativos vinculados à planta técnica correta.",
            )

        if _number(asset.get("nominal_rpm")) in {None, 0.0}:
            _issue(
                issues,
                severity="warning",
                area="Ativos",
                item=asset_id,
                field="nominal_rpm",
                message="RPM nominal não informado.",
                suggestion="Informe o RPM nominal para melhorar diagnóstico e demonstração.",
            )

    enabled_signals_by_asset: dict[str, set[str]] = defaultdict(set)

    for signal in signal_map:
        if not isinstance(signal, dict):
            continue

        asset_id = _text(signal.get("asset_id"))
        source_id = _text(signal.get("source_id"))
        metric = _text(signal.get("metric") or signal.get("internal_metric"))
        enabled = bool(signal.get("enabled", True))
        label = " / ".join(part for part in [asset_id, source_id, metric] if part)

        if asset_id not in asset_id_set:
            _issue(
                issues,
                severity="error",
                area="Mapeamento de Sinais",
                item=label,
                field="asset_id",
                message=f"Mapeamento referencia ativo inexistente: {asset_id or '-'}",
                suggestion="Selecione um ativo cadastrado.",
            )

        if source_id not in source_id_set:
            _issue(
                issues,
                severity="error",
                area="Mapeamento de Sinais",
                item=label,
                field="source_id",
                message=f"Mapeamento referencia fonte inexistente: {source_id or '-'}",
                suggestion="Selecione uma fonte de dados cadastrada.",
            )

        if enabled and not _text(signal.get("external_tag")):
            _issue(
                issues,
                severity="warning",
                area="Mapeamento de Sinais",
                item=label,
                field="external_tag",
                message="Sinal ativo sem tag externa/campo de origem.",
                suggestion="Informe tag OPC UA, tópico MQTT, campo JSON ou coluna CSV.",
            )

        if enabled and asset_id and metric:
            enabled_signals_by_asset[asset_id].add(metric)

    for asset_id in asset_id_set:
        metrics = enabled_signals_by_asset.get(asset_id, set())
        if not metrics:
            _issue(
                issues,
                severity="warning",
                area="Mapeamento de Sinais",
                item=asset_id,
                field="signal_map",
                message="Ativo sem sinais mapeados.",
                suggestion="Mapeie pelo menos rpm, vibração e temperatura para a demonstração.",
            )
            continue

        missing = sorted(MINIMUM_SIGNAL_METRICS - metrics)
        if missing:
            _issue(
                issues,
                severity="warning",
                area="Mapeamento de Sinais",
                item=asset_id,
                field="metric",
                message=f"Ativo sem métricas mínimas: {', '.join(missing)}.",
                suggestion="Complete o mapeamento mínimo para diagnóstico operacional consistente.",
            )

    for rule in parameters:
        if not isinstance(rule, dict):
            continue

        asset_id = _text(rule.get("asset_id"))
        metric = _text(rule.get("metric"))
        label = " / ".join(part for part in [asset_id, metric] if part)

        if asset_id not in asset_id_set:
            _issue(
                issues,
                severity="error",
                area="Parâmetros e Alertas",
                item=label,
                field="asset_id",
                message=f"Regra referencia ativo inexistente: {asset_id or '-'}",
                suggestion="Associe a regra a um ativo cadastrado.",
            )

        if not metric:
            _issue(
                issues,
                severity="error",
                area="Parâmetros e Alertas",
                item=label,
                field="metric",
                message="Regra sem métrica.",
                suggestion="Informe a métrica avaliada pela regra.",
            )

        if not _has_any_limit(rule):
            _issue(
                issues,
                severity="warning",
                area="Parâmetros e Alertas",
                item=label,
                field="limits",
                message="Regra sem limites técnicos configurados.",
                suggestion="Informe limites de atenção, alerta ou crítico.",
            )

    issues.sort(key=lambda issue: (ISSUE_ORDER.get(issue["severity"], 9), issue["area"], issue["item"], issue["field"]))
    errors = sum(1 for issue in issues if issue["severity"] == "error")
    warnings = sum(1 for issue in issues if issue["severity"] == "warning")

    if errors:
        status = "critical"
        message = "Configuração com inconsistências críticas."
    elif warnings:
        status = "warning"
        message = "Configuração utilizável, mas com pontos a revisar."
    else:
        status = "ok"
        message = "Configuração consistente para demonstração."

    return {
        "status": status,
        "message": message,
        "errors": errors,
        "warnings": warnings,
        "issues": issues,
    }
