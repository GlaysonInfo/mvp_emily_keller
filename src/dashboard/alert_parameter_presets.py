from __future__ import annotations

from typing import Any


METRIC_LABELS = {
    "rpm": "RPM",
    "vibration_rms_mm_s": "Vibração RMS",
    "temperature_c": "Temperatura",
    "ultrasound_db": "Ultrassom",
    "kurtosis_index": "Kurtosis",
    "crest_factor_index": "Crest Factor",
    "vibration_peak_g": "Pico de vibração",
    "hourmeter_h": "Horímetro",
    "health_score": "Health Score",
    "severity_score": "Severity Score",
}

PARAMETER_PRESETS: dict[str, dict[str, Any]] = {
    "rpm": {
        "mode": "range",
        "normal_min": 0,
        "normal_max": 0,
        "attention_min": 0,
        "alert_min": 0,
        "critical_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": (
            "Verificar variação de rotação em relação ao RPM nominal, carga aplicada, inversor de frequência, "
            "acoplamento e condição operacional do processo."
        ),
        "note": "RPM depende do RPM nominal do ativo. Use regra de faixa/tolerância em vez de limite fixo simples.",
    },
    "vibration_rms_mm_s": {
        "mode": "higher_is_worse",
        "normal_max": 2.8,
        "attention_min": 2.8,
        "alert_min": 4.5,
        "critical_min": 7.1,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": (
            "Inspecionar base, fixação, acoplamento, alinhamento, balanceamento, rolamentos e condição mecânica "
            "do conjunto."
        ),
        "note": "Valores iniciais de referência para MVP. Ajustar por classe do equipamento e baseline real.",
    },
    "temperature_c": {
        "mode": "higher_is_worse",
        "normal_max": 70,
        "attention_min": 70,
        "alert_min": 85,
        "critical_min": 100,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": "Verificar carga, ventilação, sujeira, rolamentos, corrente elétrica, atrito e condição de lubrificação.",
        "note": "Usar com cautela quando o ambiente for severo ou houver processo quente.",
    },
    "ultrasound_db": {
        "mode": "higher_is_worse",
        "normal_max": 40,
        "attention_min": 40,
        "alert_min": 55,
        "critical_min": 70,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": "Verificar lubrificação, vazamentos, atrito, rolamentos, ruídos anormais e contaminação.",
        "note": "Útil para identificar degradação antes de vibração/temperatura ficarem críticas.",
    },
    "kurtosis_index": {
        "mode": "higher_is_worse",
        "normal_max": 3.5,
        "attention_min": 3.5,
        "alert_min": 5.0,
        "critical_min": 7.0,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": "Investigar impactos, defeitos incipientes em rolamentos, folgas, batimentos e irregularidades mecânicas.",
        "note": "Indicador sensível para eventos impulsivos e falhas iniciais.",
    },
    "crest_factor_index": {
        "mode": "higher_is_worse",
        "normal_max": 3.5,
        "attention_min": 3.5,
        "alert_min": 5.0,
        "critical_min": 7.0,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": "Avaliar impactos, rolamentos, folgas mecânicas e eventos transitórios de vibração.",
        "note": "Complementa Kurtosis e pico de vibração.",
    },
    "vibration_peak_g": {
        "mode": "higher_is_worse",
        "normal_max": 0.8,
        "attention_min": 0.8,
        "alert_min": 1.5,
        "critical_min": 2.5,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 3,
        "recommended_action": "Verificar impactos mecânicos, folgas, batimentos, rolamentos e ocorrência de picos anormais de vibração.",
        "note": "Usar como reforço para falha de rolamento/desbalanceamento.",
    },
    "health_score": {
        "mode": "lower_is_worse",
        "normal_max": 0,
        "attention_min": 0,
        "alert_min": 0,
        "critical_min": 0,
        "normal_min": 75,
        "attention_max": 75,
        "alert_max": 55,
        "critical_max": 35,
        "persistence_min": 2,
        "recommended_action": "Avaliar a métrica dominante que reduziu o Health Score e priorizar inspeção técnica conforme severidade.",
        "note": "Quanto menor, pior.",
    },
    "severity_score": {
        "mode": "higher_is_worse",
        "normal_max": 25,
        "attention_min": 25,
        "alert_min": 45,
        "critical_min": 65,
        "normal_min": 0,
        "attention_max": 0,
        "alert_max": 0,
        "critical_max": 0,
        "persistence_min": 2,
        "recommended_action": "Avaliar causa dominante do aumento de severidade e aplicar matriz de escalonamento conforme criticidade.",
        "note": "Quanto maior, pior.",
    },
}


def get_metric_label(metric: Any) -> str:
    metric_text = str(metric or "")
    return METRIC_LABELS.get(metric_text, metric_text)


def get_parameter_preset(metric: str, asset: dict[str, Any] | None = None) -> dict[str, Any]:
    preset = dict(PARAMETER_PRESETS.get(metric, PARAMETER_PRESETS["vibration_rms_mm_s"]))

    if metric == "rpm" and asset:
        try:
            nominal = float(asset.get("nominal_rpm") or 0)
        except (TypeError, ValueError):
            nominal = 0

        if nominal > 0:
            preset.update(
                {
                    "mode": "range",
                    "normal_min": round(nominal * 0.92, 2),
                    "normal_max": round(nominal * 1.08, 2),
                    "attention_min": round(nominal * 1.08, 2),
                    "alert_min": round(nominal * 1.12, 2),
                    "critical_min": round(nominal * 1.18, 2),
                    "attention_max": round(nominal * 0.92, 2),
                    "alert_max": round(nominal * 0.88, 2),
                    "critical_max": round(nominal * 0.82, 2),
                    "note": f"Preset calculado com base em RPM nominal de {nominal:.0f}.",
                }
            )

    return preset


def has_any_threshold(rule: dict[str, Any]) -> bool:
    keys = [
        "normal_max",
        "attention_min",
        "alert_min",
        "critical_min",
        "normal_min",
        "attention_max",
        "alert_max",
        "critical_max",
    ]

    for key in keys:
        try:
            if float(rule.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue

    return False


def validate_parameter_rule(rule: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not rule.get("asset_id"):
        errors.append("Selecione um ativo.")

    if not rule.get("metric"):
        errors.append("Selecione uma métrica.")

    if not has_any_threshold(rule):
        errors.append("Configure ao menos um limite de atenção, alerta ou crítico.")

    if not str(rule.get("recommended_action") or "").strip():
        errors.append("Informe uma ação recomendada.")

    try:
        persistence = int(rule.get("persistence_min") or 0)
        if persistence <= 0:
            errors.append("Persistência mínima deve ser maior que zero.")
    except (TypeError, ValueError):
        errors.append("Persistência mínima inválida.")

    return errors
