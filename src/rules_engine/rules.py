from __future__ import annotations

from typing import Any, Mapping

from .alert_models import Alert
from .diagnostics import extract_alert_context, extract_metric_values


def evaluate_payload(payload: Mapping[str, Any]) -> list[Alert]:
    metrics = extract_metric_values(payload)
    context = extract_alert_context(payload)

    return evaluate_metrics(metrics, context=context)


def evaluate_metrics(
    metrics: Mapping[str, float],
    *,
    context: Mapping[str, str] | None = None,
) -> list[Alert]:
    context = context or {}
    alerts = []

    if _is_lubrication_degradation(metrics):
        alerts.append(_build_lubrication_alert(context))

    if _is_imbalance(metrics):
        alerts.append(_build_imbalance_alert(context))

    if _is_bearing_fault(metrics):
        alerts.append(_build_bearing_fault_alert(context))

    return alerts


def _is_lubrication_degradation(metrics: Mapping[str, float]) -> bool:
    return (
        metrics.get("ultrasound_db", 0.0) > 38.0
        and metrics.get("temperature_c", 0.0) > 65.0
        and metrics.get("vibration_rms_mm_s", 0.0) < 4.0
    )


def _is_imbalance(metrics: Mapping[str, float]) -> bool:
    return (
        metrics.get("vibration_rms_mm_s", 0.0) >= 4.0
        and metrics.get("ultrasound_db", 999.0) < 38.0
        and metrics.get("kurtosis", 999.0) < 4.5
    )


def _is_bearing_fault(metrics: Mapping[str, float]) -> bool:
    return metrics.get("kurtosis", 0.0) >= 5.0 and metrics.get("crest_factor", 0.0) >= 4.5


def _build_lubrication_alert(context: Mapping[str, str]) -> Alert:
    return Alert(
        alert_type="lubrication_degradation",
        severity="warning",
        status="open",
        probable_cause="Possivel degradacao de lubrificacao",
        confidence=0.76,
        evidence=[
            "Ultrassom acima de 38 dB",
            "Temperatura acima de 65 C",
            "Vibracao RMS ainda abaixo de 4.0 mm/s",
        ],
        recommended_action="Verificar lubrificacao, contaminacao e rotina de relubrificacao",
        **context,
    )


def _build_imbalance_alert(context: Mapping[str, str]) -> Alert:
    return Alert(
        alert_type="imbalance",
        severity="critical",
        status="open",
        probable_cause="Possivel desbalanceamento",
        confidence=0.82,
        evidence=[
            "Vibracao RMS acima de 4.0 mm/s",
            "Ultrassom dentro da faixa esperada",
            "Kurtosis sem forte evidencia de impacto de rolamento",
        ],
        recommended_action="Verificar balanceamento, fixacao, acoplamento e base do motor",
        **context,
    )


def _build_bearing_fault_alert(context: Mapping[str, str]) -> Alert:
    return Alert(
        alert_type="bearing_fault",
        severity="critical",
        status="open",
        probable_cause="Possivel falha inicial em rolamento",
        confidence=0.86,
        evidence=[
            "Kurtosis acima ou igual a 5.0",
            "Crest factor acima ou igual a 4.5",
            "Evidencia de impactos impulsivos no sinal de vibracao",
        ],
        recommended_action="Inspecionar rolamento, envelope de vibracao, lubrificacao e alinhamento",
        **context,
    )
