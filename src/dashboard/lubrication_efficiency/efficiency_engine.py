from __future__ import annotations

from typing import Any


STATUS_ORDER = {
    "NORMAL": 0,
    "RECUPERADO": 0,
    "ATENÇÃO": 1,
    "ATENCAO": 1,
    "ALERTA": 2,
    "CRÍTICO": 3,
    "CRITICO": 3,
    "SEM COMUNICAÇÃO": 3,
    "SEM COMUNICACAO": 3,
}


def _to_float(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if value in [None, ""]:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    parsed = _to_float(value)
    return default if parsed is None else int(parsed)


def _status_level(status: Any) -> int:
    return STATUS_ORDER.get(str(status or "").upper(), 0)


def _state_health(state: dict[str, Any]) -> float | None:
    value = _to_float(state.get("health_score"))
    if value is not None:
        return value

    metrics = state.get("metrics")
    if isinstance(metrics, dict):
        return _to_float(metrics.get("health_score"))

    return None


def _state_severity(state: dict[str, Any]) -> float | None:
    value = _to_float(state.get("severity_score"), _to_float(state.get("severity")))
    if value is not None:
        return value

    metrics = state.get("metrics")
    if isinstance(metrics, dict):
        value = _to_float(metrics.get("severity_score"), _to_float(metrics.get("severity")))
        if value is not None:
            return value

    health = _state_health(state)
    if health is not None:
        return max(0.0, 100.0 - health)

    return None


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def lubrication_outlet_score(lubrication_state: dict[str, Any]) -> float:
    total = _to_int(lubrication_state.get("outlet_count")) or len(lubrication_state.get("outlets") or [])
    if total <= 0:
        return 0.0

    normal = _to_int(lubrication_state.get("normal_count"))
    attention = _to_int(lubrication_state.get("attention_count"))
    alert = _to_int(lubrication_state.get("alert_count"))
    critical = _to_int(lubrication_state.get("critical_count"))

    known = normal + attention + alert + critical
    if known == 0 and lubrication_state.get("outlets"):
        for outlet in lubrication_state.get("outlets", []):
            level = _status_level(outlet.get("status_label") or outlet.get("status"))
            if level == 0:
                normal += 1
            elif level == 1:
                attention += 1
            elif level == 2:
                alert += 1
            else:
                critical += 1

    weighted = (normal * 1.0) + (attention * 0.75) + (alert * 0.45) + (critical * 0.10)
    return _clamp_score((weighted / total) * 100.0)


def equipment_condition_score(equipment_states: list[dict[str, Any]]) -> float:
    if not equipment_states:
        return 100.0

    health_values = [_state_health(state) for state in equipment_states]
    health_values = [value for value in health_values if value is not None]
    if health_values:
        health_score = sum(health_values) / len(health_values)
    else:
        severity_values = [_state_severity(state) for state in equipment_states]
        severity_values = [value for value in severity_values if value is not None]
        health_score = 100.0 - max(severity_values or [0.0])

    max_status_penalty = max((_status_level(state.get("status_label")) for state in equipment_states), default=0) * 5.0
    return _clamp_score(health_score - max_status_penalty)


def calculate_lubrication_efficiency(
    lubrication_state: dict[str, Any],
    equipment_states: list[dict[str, Any]],
    equipment_links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    outlet_score = lubrication_outlet_score(lubrication_state)
    equipment_score = equipment_condition_score(equipment_states)
    max_anomaly = _to_float(lubrication_state.get("max_anomaly_score"), 0.0) or 0.0
    anomaly_score = _clamp_score(100.0 - max_anomaly)

    efficiency_score = _clamp_score((outlet_score * 0.55) + (equipment_score * 0.30) + (anomaly_score * 0.15))
    affected_outlets = (
        _to_int(lubrication_state.get("attention_count"))
        + _to_int(lubrication_state.get("alert_count"))
        + _to_int(lubrication_state.get("critical_count"))
    )

    if efficiency_score >= 85:
        status = "EFICIENTE"
        recommendation = "Manter acompanhamento normal e registrar ciclos como evidência operacional."
    elif efficiency_score >= 70:
        status = "ATENÇÃO"
        recommendation = "Verificar saídas com desvio e comparar manômetro físico com leitura eletrônica."
    elif efficiency_score >= 50:
        status = "ALERTA"
        recommendation = "Priorizar inspeção das saídas com baixa pressão, alta pressão ou alívio lento."
    else:
        status = "CRÍTICO"
        recommendation = "Acionar manutenção e avaliar parada controlada se o equipamento lubrificado for crítico."

    return {
        "efficiency_score": efficiency_score,
        "status_label": status,
        "outlet_score": outlet_score,
        "equipment_score": equipment_score,
        "anomaly_score": anomaly_score,
        "affected_outlets": affected_outlets,
        "monitored_equipment": len(equipment_links) if equipment_links else len(equipment_states),
        "recommendation": recommendation,
    }


def equipment_rows(equipment_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for state in equipment_states:
        rows.append(
            {
                "Equipamento": state.get("asset_name") or state.get("asset_id"),
                "Status": state.get("status_label") or "-",
                "Saúde": _state_health(state),
                "Gravidade": _state_severity(state),
                "Área": state.get("area") or "-",
                "Atualizado": state.get("updated_at") or state.get("timestamp") or "-",
            }
        )
    return sorted(rows, key=lambda row: (row["Gravidade"] or 0), reverse=True)
