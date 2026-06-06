from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping


SEVERITY_RANK = {"NORMAL": 0, "ATENÇÃO": 1, "ALERTA": 2, "CRÍTICO": 3}


def _float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def configured_rules_for_asset(config: Mapping[str, Any], asset_id: str) -> list[dict[str, Any]]:
    return [
        dict(rule)
        for rule in config.get("parameters_alerts", []) or []
        if isinstance(rule, Mapping)
        and str(rule.get("asset_id") or "") == asset_id
        and rule.get("enabled", True) is not False
        and str(rule.get("metric") or "")
    ]


def _outside(value: float, minimum: float | None, maximum: float | None) -> bool:
    return (minimum is not None and value <= minimum) or (maximum is not None and value >= maximum)


def classify_parameter_value(rule: Mapping[str, Any], value: float) -> tuple[str, float | None]:
    mode = str(rule.get("rule_mode") or "").strip()
    if not mode:
        mode = "lower_is_worse" if _float(rule.get("critical_max")) not in [None, 0.0] else "higher_is_worse"

    if mode == "ideal_range":
        levels = [
            ("CRÍTICO", _float(rule.get("critical_min")), _float(rule.get("critical_max"))),
            ("ALERTA", _float(rule.get("alert_min")), _float(rule.get("alert_max"))),
            ("ATENÇÃO", _float(rule.get("attention_min")), _float(rule.get("attention_max"))),
        ]
        for label, minimum, maximum in levels:
            if _outside(value, minimum, maximum):
                threshold = minimum if minimum is not None and value <= minimum else maximum
                return label, threshold
        return "NORMAL", None

    if mode == "lower_is_worse":
        for label, key in [
            ("CRÍTICO", "critical_max"),
            ("ALERTA", "alert_max"),
            ("ATENÇÃO", "attention_max"),
        ]:
            threshold = _float(rule.get(key))
            if threshold is not None and value <= threshold:
                return label, threshold
        return "NORMAL", None

    for label, key in [
        ("CRÍTICO", "critical_min"),
        ("ALERTA", "alert_min"),
        ("ATENÇÃO", "attention_min"),
    ]:
        threshold = _float(rule.get(key))
        if threshold is not None and value >= threshold:
            return label, threshold
    return "NORMAL", None


def evaluate_parameter_rules(
    config: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    previous_rule_state: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], bool]:
    asset_id = str(payload.get("asset_id") or "")
    rules = configured_rules_for_asset(config, asset_id)
    if not rules:
        return [], {}, [], False

    metrics = {
        str(metric.get("name") or ""): _float(metric.get("value"))
        for metric in payload.get("metrics", []) or []
        if isinstance(metric, Mapping)
    }
    observed_at = _timestamp(payload.get("timestamp"))
    previous_rule_state = previous_rule_state or {}
    next_state: dict[str, Any] = {}
    alerts: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []

    for rule in rules:
        metric = str(rule["metric"])
        value = metrics.get(metric)
        if value is None:
            continue

        label, threshold = classify_parameter_value(rule, value)
        persistence_min = max(0, int(rule.get("persistence_min") or 0))
        recovery_persistence_min = max(
            0,
            int(rule.get("recovery_persistence_min") or persistence_min),
        )
        persisted = label == "NORMAL"
        first_seen_at: str | None = None
        prior = previous_rule_state.get(metric)

        if label == "NORMAL" and isinstance(prior, Mapping) and prior.get("persisted"):
            recovery_started_at = str(prior.get("recovery_started_at") or payload.get("timestamp"))
            recovery_elapsed_sec = max(
                0.0,
                (observed_at - _timestamp(recovery_started_at)).total_seconds(),
            )
            recovering = recovery_elapsed_sec < recovery_persistence_min * 60
            if recovering:
                prior_label = str(prior.get("status_label") or "ATENÇÃO")
                prior_threshold = _float(prior.get("threshold"))
                next_state[metric] = {
                    **dict(prior),
                    "last_seen_at": str(payload.get("timestamp")),
                    "last_normal_value": value,
                    "recovery_started_at": recovery_started_at,
                    "recovery_persistence_min": recovery_persistence_min,
                    "recovering": True,
                }
                unit = str(rule.get("unit") or "")
                alerts.append(
                    {
                        "alert_type": f"parameter_{metric}",
                        "metric": metric,
                        "severity": "critical" if prior_label == "CRÍTICO" else "warning",
                        "status_label": prior_label,
                        "probable_cause": f"{metric} em validação de recuperação",
                        "confidence": 1.0,
                        "evidence": [
                            f"Valor atual normal: {value:g}{(' ' + unit) if unit else ''}",
                            f"Normalidade deve persistir por {recovery_persistence_min} min",
                        ],
                        "recommended_action": str(
                            rule.get("recommended_action") or "Manter acompanhamento até confirmar a recuperação."
                        ),
                        "technical_note": str(rule.get("technical_note") or ""),
                    }
                )
                persisted = True

        if label != "NORMAL":
            if isinstance(prior, Mapping) and str(prior.get("status_label")) == label:
                first_seen_at = str(prior.get("first_seen_at") or payload.get("timestamp"))
            else:
                first_seen_at = str(payload.get("timestamp"))

            elapsed_sec = max(0.0, (observed_at - _timestamp(first_seen_at)).total_seconds())
            persisted = elapsed_sec >= persistence_min * 60
            next_state[metric] = {
                "status_label": label,
                "first_seen_at": first_seen_at,
                "last_seen_at": str(payload.get("timestamp")),
                "value": value,
                "threshold": threshold,
                "persistence_min": persistence_min,
                "recovery_persistence_min": recovery_persistence_min,
                "persisted": persisted,
            }

            if persisted:
                unit = str(rule.get("unit") or "")
                alerts.append(
                    {
                        "alert_type": f"parameter_{metric}",
                        "metric": metric,
                        "severity": "critical" if label == "CRÍTICO" else "warning",
                        "status_label": label,
                        "probable_cause": f"{metric} fora da faixa parametrizada",
                        "confidence": 1.0,
                        "evidence": [
                            f"Valor recebido: {value:g}{(' ' + unit) if unit else ''}",
                            f"Limite de referência: {threshold:g}{(' ' + unit) if unit and threshold is not None else ''}",
                            f"Persistência mínima atendida: {persistence_min} min",
                        ],
                        "recommended_action": str(
                            rule.get("recommended_action") or "Inspecionar o ativo e validar a medição em campo."
                        ),
                        "technical_note": str(rule.get("technical_note") or ""),
                        "first_detected_at": first_seen_at,
                    }
                )

        evaluations.append(
            {
                "metric": metric,
                "value": value,
                "status_label": label,
                "threshold": threshold,
                "persistence_min": persistence_min,
                "recovery_persistence_min": recovery_persistence_min,
                "persisted": persisted,
                "first_seen_at": first_seen_at,
                "recovering": bool(next_state.get(metric, {}).get("recovering")),
            }
        )

    alerts.sort(key=lambda item: SEVERITY_RANK.get(str(item.get("status_label")), 0), reverse=True)
    return alerts, next_state, evaluations, True
