from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


METRIC_LABELS = {
    "health_score": "Saúde",
    "severity_score": "Gravidade",
    "vibration_rms_mm_s": "Vibração RMS",
    "temperature_c": "Temperatura",
    "ultrasound_db": "Ultrassom",
}


def parse_utc(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def numeric(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if value in [None, ""] or isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_value(item: dict[str, Any] | None, *names: str) -> float | None:
    if not item:
        return None

    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}

    for name in names:
        value = numeric(item.get(name))
        if value is not None:
            return value

        value = numeric(metrics.get(name))
        if value is not None:
            return value

    return None


def severity_value(item: dict[str, Any] | None) -> float | None:
    value = metric_value(item, "severity_score", "severity")
    if value is not None:
        return value

    health = metric_value(item, "health_score")
    if health is not None:
        return max(0.0, 100.0 - health)

    return None


def history_timestamp(item: dict[str, Any]) -> datetime | None:
    return parse_utc(
        item.get("ts_utc_minute")
        or item.get("recorded_at_utc")
        or item.get("updated_at")
        or item.get("timestamp")
    )


def sorted_history(history_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(history_items, key=lambda item: history_timestamp(item) or datetime.min.replace(tzinfo=UTC))


def build_marco_zero(history_items: list[dict[str, Any]], current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    ordered = sorted_history(history_items)
    first = ordered[0] if ordered else None
    latest = current_state or (ordered[-1] if ordered else None)

    return {
        "has_history": bool(first),
        "timestamp": first.get("ts_utc_minute") if first else "-",
        "health_score": metric_value(first, "health_score"),
        "severity_score": severity_value(first),
        "vibration_rms_mm_s": metric_value(first, "vibration_rms_mm_s"),
        "temperature_c": metric_value(first, "temperature_c"),
        "ultrasound_db": metric_value(first, "ultrasound_db"),
        "latest_health_score": metric_value(latest, "health_score"),
        "latest_severity_score": severity_value(latest),
    }


def outlet_from_cycle(cycle: dict[str, Any], outlet_id: str) -> dict[str, Any]:
    for outlet in cycle.get("outlets", []) or []:
        if outlet.get("outlet_id") == outlet_id:
            return outlet

    return {}


def find_before_after(
    history_items: list[dict[str, Any]],
    cycle_timestamp: datetime,
    *,
    response_window_hours: int = 24,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    ordered = sorted_history(history_items)
    before = None
    after = None
    end = cycle_timestamp + timedelta(hours=response_window_hours)

    for item in ordered:
        timestamp = history_timestamp(item)
        if timestamp is None:
            continue

        if timestamp <= cycle_timestamp:
            before = item
        elif timestamp <= end:
            after = item

    return before, after


def percentage_reduction(before: float | None, after: float | None) -> float | None:
    if before in [None, 0] or after is None:
        return None

    return round(((before - after) / before) * 100.0, 1)


def delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None

    return round(after - before, 2)


def _positive_reduction(before: float | None, after: float | None) -> float:
    if before is None or after is None:
        return 0.0

    return before - after


def response_score(before: dict[str, Any] | None, after: dict[str, Any] | None) -> float | None:
    if not before or not after:
        return None

    health_before = metric_value(before, "health_score")
    health_after = metric_value(after, "health_score")
    health_delta = (health_after - health_before) if health_before is not None and health_after is not None else 0.0
    severity_delta = _positive_reduction(severity_value(before), severity_value(after))
    vibration_reduction_pct = percentage_reduction(
        metric_value(before, "vibration_rms_mm_s"),
        metric_value(after, "vibration_rms_mm_s"),
    ) or 0.0
    temperature_reduction = _positive_reduction(
        metric_value(before, "temperature_c"),
        metric_value(after, "temperature_c"),
    )
    ultrasound_reduction = _positive_reduction(
        metric_value(before, "ultrasound_db"),
        metric_value(after, "ultrasound_db"),
    )

    score = (
        (health_delta * 1.2)
        + (severity_delta * 0.8)
        + (vibration_reduction_pct * 0.15)
        + (temperature_reduction * 0.8)
        + (ultrasound_reduction * 0.5)
    )
    return round(max(-100.0, min(100.0, score)), 1)


def response_label(score: float | None) -> str:
    if score is None:
        return "SEM DADOS"
    if score >= 10:
        return "EXCELENTE"
    if score >= 4:
        return "BOA"
    if score >= -3:
        return "NEUTRA"
    return "RUIM"


def cycle_dose(cycle: dict[str, Any], link: dict[str, Any]) -> float | None:
    return numeric(cycle.get("grease_amount_g")) or numeric(link.get("target_grease_g_per_cycle"))


def cycle_grease_type(cycle: dict[str, Any], link: dict[str, Any]) -> str:
    return str(cycle.get("grease_type") or link.get("grease_type") or "-")


def build_response_rows(
    *,
    link: dict[str, Any],
    cycles: list[dict[str, Any]],
    history_items: list[dict[str, Any]],
    response_window_hours: int = 24,
) -> list[dict[str, Any]]:
    rows = []
    outlet_id = str(link.get("outlet_id") or "")

    for cycle in sorted(cycles, key=lambda item: parse_utc(item.get("cycle_timestamp")) or datetime.min.replace(tzinfo=UTC), reverse=True):
        timestamp = parse_utc(cycle.get("cycle_timestamp") or cycle.get("updated_at"))
        if timestamp is None:
            continue

        before, after = find_before_after(history_items, timestamp, response_window_hours=response_window_hours)
        score = response_score(before, after)
        outlet = outlet_from_cycle(cycle, outlet_id)
        dose = cycle_dose(cycle, link)

        rows.append(
            {
                "cycle_id": cycle.get("cycle_id"),
                "cycle_timestamp": cycle.get("cycle_timestamp") or cycle.get("updated_at"),
                "asset_id": link.get("asset_id"),
                "outlet_id": outlet_id,
                "grease_type": cycle_grease_type(cycle, link),
                "grease_amount_g": dose,
                "cycle_interval_h": numeric(cycle.get("cycle_interval_h")) or numeric(link.get("cycle_interval_h")),
                "outlet_status": outlet.get("severity") or outlet.get("status_label") or outlet.get("status") or "-",
                "peak_pressure_bar": outlet.get("peak_pressure_bar"),
                "before_timestamp": before.get("ts_utc_minute") if before else "-",
                "after_timestamp": after.get("ts_utc_minute") if after else "-",
                "health_before": metric_value(before, "health_score"),
                "health_after": metric_value(after, "health_score"),
                "health_delta": delta(metric_value(before, "health_score"), metric_value(after, "health_score")),
                "severity_before": severity_value(before),
                "severity_after": severity_value(after),
                "severity_delta": delta(severity_value(after), severity_value(before)),
                "vibration_reduction_pct": percentage_reduction(
                    metric_value(before, "vibration_rms_mm_s"),
                    metric_value(after, "vibration_rms_mm_s"),
                ),
                "temperature_delta_c": delta(metric_value(before, "temperature_c"), metric_value(after, "temperature_c")),
                "ultrasound_delta_db": delta(metric_value(before, "ultrasound_db"), metric_value(after, "ultrasound_db")),
                "response_score": score,
                "response_label": response_label(score),
            }
        )

    return rows


def recommend_dose(link: dict[str, Any], response_rows: list[dict[str, Any]]) -> dict[str, Any]:
    dose = numeric(link.get("target_grease_g_per_cycle"))
    interval_h = numeric(link.get("cycle_interval_h"))

    if not response_rows:
        return {
            "decision": "AGUARDAR",
            "recommended_dose_g": dose,
            "confidence": "baixa",
            "message": "Registrar ciclos de graxa e histórico do motor para calcular a resposta antes/depois.",
        }

    latest = response_rows[0]
    score = numeric(latest.get("response_score"))
    latest_dose = numeric(latest.get("grease_amount_g")) or dose
    temp_delta = numeric(latest.get("temperature_delta_c"))

    if score is None:
        return {
            "decision": "AGUARDAR",
            "recommended_dose_g": latest_dose,
            "confidence": "baixa",
            "message": "Há ciclo de graxa registrado, mas ainda falta histórico antes/depois do motor.",
        }

    if temp_delta is not None and temp_delta >= 3 and latest_dose:
        recommended = round(latest_dose * 0.9, 1)
        return {
            "decision": "REDUZIR",
            "recommended_dose_g": recommended,
            "confidence": "média",
            "message": "A temperatura subiu após o ciclo. Validar excesso de graxa e testar redução controlada da dose.",
        }

    if score >= 4:
        return {
            "decision": "MANTER",
            "recommended_dose_g": latest_dose,
            "confidence": "média",
            "message": f"A resposta do motor foi {latest['response_label'].lower()}. Manter dose e intervalo atuais para confirmar repetibilidade.",
        }

    if latest_dose:
        recommended = round(latest_dose * 1.1, 1)
    else:
        recommended = None

    return {
        "decision": "AUMENTAR",
        "recommended_dose_g": recommended,
        "confidence": "baixa" if len(response_rows) < 3 else "média",
        "message": "A resposta do motor foi fraca ou neutra. Testar aumento controlado da dose e acompanhar vibração, ultrassom e temperatura.",
        "current_interval_h": interval_h,
    }


def grease_comparison_rows(response_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in response_rows:
        grouped[str(row.get("grease_type") or "-")].append(row)

    rows = []
    for grease_type, items in grouped.items():
        scores = [numeric(item.get("response_score")) for item in items]
        scores = [score for score in scores if score is not None]
        doses = [numeric(item.get("grease_amount_g")) for item in items]
        doses = [dose for dose in doses if dose is not None]

        rows.append(
            {
                "Graxa": grease_type,
                "Ciclos": len(items),
                "Resposta média": round(sum(scores) / len(scores), 1) if scores else None,
                "Dose média (g)": round(sum(doses) / len(doses), 1) if doses else None,
                "Melhor resposta": max(scores) if scores else None,
            }
        )

    return sorted(rows, key=lambda row: row["Resposta média"] if row["Resposta média"] is not None else -999, reverse=True)
