from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from dashboard.intelligence_labels import ANALYSIS_METRICS, metric_direction, metric_label, metric_unit
    from dashboard.intelligence_rules import build_ai_recommendation, classify_anomaly_level, explain_metric
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.intelligence_labels import ANALYSIS_METRICS, metric_direction, metric_label, metric_unit
    from src.dashboard.intelligence_rules import build_ai_recommendation, classify_anomaly_level, explain_metric


def _to_float(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, bool) or value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_metric(item: dict[str, Any], metric: str) -> Any:
    if metric in item:
        return item.get(metric)

    metrics = item.get("metrics") or {}
    if isinstance(metrics, dict) and metric in metrics:
        return metrics.get(metric)

    legacy_map = {
        "vibration_rms_mm_s": "vibration_rms",
        "temperature_c": "temperature",
        "ultrasound_db": "ultrasound",
        "kurtosis_index": "kurtosis",
        "crest_factor_index": "crest_factor",
        "vibration_peak_g": "vibration_peak",
        "hourmeter_h": "hourmeter",
    }

    if metric in legacy_map:
        return item.get(legacy_map[metric])

    return None


def normalize_history_items(items: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for item in items or []:
        row = {
            "tenant_id": item.get("tenant_id"),
            "plant_id": item.get("plant_id"),
            "asset_id": item.get("asset_id"),
            "status_label": item.get("status_label"),
            "mode": item.get("mode"),
            "timestamp": item.get("ts_utc_minute") or item.get("ts_utc") or item.get("updated_at"),
        }

        for metric in ANALYSIS_METRICS:
            row[metric] = _to_float(extract_metric(item, metric))

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.sort_values("timestamp")


def current_state_to_metrics(current_state: dict[str, Any]) -> dict[str, float | None]:
    return {metric: _to_float(extract_metric(current_state, metric)) for metric in ANALYSIS_METRICS}


def calculate_baseline(history_df: pd.DataFrame, *, prefer_healthy: bool = True, min_samples: int = 3) -> dict[str, dict[str, Any]]:
    if history_df is None or history_df.empty:
        return {}

    healthy_df = history_df[history_df["status_label"].isin(["NORMAL", "RECUPERADO"])]
    if prefer_healthy and len(healthy_df) >= min_samples:
        base_df = healthy_df
        source = "healthy_only"
    else:
        base_df = history_df
        source = "all_history"

    baseline: dict[str, dict[str, Any]] = {}

    for metric in ANALYSIS_METRICS:
        series = pd.to_numeric(base_df[metric], errors="coerce").dropna()
        if series.empty:
            baseline[metric] = {
                "metric": metric,
                "label": metric_label(metric),
                "unit": metric_unit(metric),
                "samples": 0,
                "source": source,
                "mean": None,
                "std": None,
                "min": None,
                "max": None,
            }
            continue

        std = float(series.std(ddof=0)) if len(series) > 1 else 0.0
        baseline[metric] = {
            "metric": metric,
            "label": metric_label(metric),
            "unit": metric_unit(metric),
            "samples": int(len(series)),
            "source": source,
            "mean": float(series.mean()),
            "std": std,
            "min": float(series.min()),
            "max": float(series.max()),
        }

    return baseline


def calculate_metric_anomaly(metric: str, current_value: Any, baseline_info: dict[str, Any]) -> dict[str, Any]:
    current = _to_float(current_value)
    mean = baseline_info.get("mean")
    std = baseline_info.get("std")
    samples = int(baseline_info.get("samples") or 0)
    direction = metric_direction(metric)

    if current is None:
        return {
            "metric": metric,
            "label": metric_label(metric),
            "unit": metric_unit(metric),
            "current": None,
            "baseline_mean": mean,
            "baseline_std": std,
            "deviation_pct": None,
            "z_score": 0.0,
            "score": 0.0,
            "level": "SEM DADO",
            "explanation": f"{metric_label(metric)} sem valor atual.",
        }

    if mean is None or samples < 2:
        return {
            "metric": metric,
            "label": metric_label(metric),
            "unit": metric_unit(metric),
            "current": current,
            "baseline_mean": mean,
            "baseline_std": std,
            "deviation_pct": None,
            "z_score": 0.0,
            "score": 10.0,
            "level": "BASELINE INSUFICIENTE",
            "explanation": f"{metric_label(metric)} ainda não possui baseline suficiente.",
        }

    std_safe = std if std and std > 0 else max(abs(float(mean)) * 0.03, 0.01)
    z_score = (current - float(mean)) / std_safe
    deviation_pct = ((current - float(mean)) / abs(float(mean)) * 100) if float(mean) != 0 else 0

    if direction == "lower_is_worse":
        risk_z = max(0.0, -z_score)
        risk_pct = max(0.0, -deviation_pct)
    elif direction == "range":
        risk_z = abs(z_score)
        risk_pct = abs(deviation_pct)
    elif direction == "accumulator":
        risk_z = 0.0
        risk_pct = 0.0
    else:
        risk_z = max(0.0, z_score)
        risk_pct = max(0.0, deviation_pct)

    score = round(max(min(100.0, risk_z * 25.0), min(100.0, risk_pct * 1.2)), 1)
    level = classify_anomaly_level(score)

    return {
        "metric": metric,
        "label": metric_label(metric),
        "unit": metric_unit(metric),
        "current": current,
        "baseline_mean": mean,
        "baseline_std": std,
        "baseline_min": baseline_info.get("min"),
        "baseline_max": baseline_info.get("max"),
        "samples": samples,
        "deviation_pct": round(deviation_pct, 2),
        "z_score": round(z_score, 2),
        "score": score,
        "level": level,
        "explanation": explain_metric(metric, current, float(mean), deviation_pct, z_score, level),
    }


def _normalize_status_key(status: Any) -> str:
    return (
        str(status or "")
        .strip()
        .upper()
        .replace("Í", "I")
        .replace("É", "E")
        .replace("Ã", "A")
        .replace("Ç", "C")
    )


def _operational_level_from_score(score: float) -> str:
    if score >= 60:
        return "CRÍTICO"
    if score >= 45:
        return "ALERTA"
    if score >= 25:
        return "ATENÇÃO"
    return "NORMAL"


def state_based_fallback_score(current_state: dict[str, Any]) -> tuple[float, str]:
    status_key = _normalize_status_key(current_state.get("status_label"))
    severity = _to_float(current_state.get("severity_score"))
    health = _to_float(current_state.get("health_score"))

    if severity is not None:
        score = max(0.0, min(100.0, severity))
    elif health is not None:
        score = max(0.0, min(100.0, 100.0 - health))
    elif status_key == "CRITICO":
        score = 80.0
    elif status_key == "ALERTA":
        score = 55.0
    elif status_key.startswith("ATENCAO"):
        score = 30.0
    elif status_key == "SEM COMUNICACAO":
        score = 55.0
    else:
        score = 0.0

    if status_key == "CRITICO":
        level = "CRÍTICO"
    elif status_key == "ALERTA":
        level = "ALERTA"
    elif status_key.startswith("ATENCAO"):
        level = "ATENÇÃO"
    elif status_key == "SEM COMUNICACAO":
        level = "SEM COMUNICAÇÃO"
    else:
        level = _operational_level_from_score(score)

    return round(score, 1), level


def calculate_operational_intelligence(history_items: list[dict[str, Any]], current_state: dict[str, Any]) -> dict[str, Any]:
    history_df = normalize_history_items(history_items)
    baseline = calculate_baseline(history_df)
    current_metrics = current_state_to_metrics(current_state)
    metric_results = [
        calculate_metric_anomaly(metric, current_metrics.get(metric), baseline.get(metric, {}))
        for metric in ANALYSIS_METRICS
    ]

    valid_scores = sorted(
        [
            float(item["score"])
            for item in metric_results
            if item.get("level") not in {"SEM DADO", "BASELINE INSUFICIENTE"}
        ],
        reverse=True,
    )

    baseline_ready = bool(valid_scores)

    if baseline_ready:
        anomaly_score = round(sum(valid_scores[:5]) / len(valid_scores[:5]), 1)
        anomaly_level = classify_anomaly_level(anomaly_score)
        analysis_source = "baseline_ml"
    else:
        anomaly_score, anomaly_level = state_based_fallback_score(current_state)
        analysis_source = "state_fallback"

    ranked_contributors = sorted(metric_results, key=lambda item: float(item.get("score", 0) or 0), reverse=True)

    return {
        "history_samples": len(history_df) if history_df is not None else 0,
        "baseline_ready": baseline_ready,
        "analysis_source": analysis_source,
        "score_source": analysis_source,
        "baseline": baseline,
        "metric_results": metric_results,
        "ranked_contributors": ranked_contributors,
        "anomaly_score": anomaly_score,
        "anomaly_level": anomaly_level,
        "recommendation": build_ai_recommendation(metric_results, current_state),
        "current_state": current_state,
    }


def intelligence_to_report_text(result: dict[str, Any]) -> str:
    rec = result.get("recommendation", {})
    lines = [
        "RELATÓRIO DE INTELIGÊNCIA OPERACIONAL",
        "",
        f"Fonte da análise: {result.get('analysis_source') or result.get('score_source') or '-'}",
        f"Baseline disponível: {'Sim' if result.get('baseline_ready') else 'Não'}",
        f"Score de anomalia: {result.get('anomaly_score')}",
        f"Nível: {result.get('anomaly_level')}",
        f"Amostras históricas: {result.get('history_samples')}",
        "",
        "HIPÓTESE PRINCIPAL",
        f"{rec.get('primary_hypothesis')} | confiança {rec.get('confidence')}",
        "",
        "EVIDÊNCIAS",
    ]

    lines.extend(f"- {item}" for item in rec.get("evidence", []))
    lines.extend(["", "AÇÕES IMEDIATAS"])
    lines.extend(f"- {item}" for item in rec.get("immediate_actions", []))
    lines.extend(["", "AÇÕES PREVENTIVAS"])
    lines.extend(f"- {item}" for item in rec.get("preventive_actions", []))
    lines.extend(["", "RISCO SE NÃO TRATADO", str(rec.get("risk_if_ignored", ""))])

    return "\n".join(lines)
