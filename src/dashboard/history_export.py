from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo


MINUTE_COLUMNS = [
    "data_hora",
    "data_hora_utc",
    "tenant_id",
    "plant_id",
    "asset_id",
    "mode",
    "status_label",
    "rpm",
    "vibration_rms_mm_s",
    "temperature_c",
    "ultrasound_db",
    "kurtosis_index",
    "crest_factor_index",
    "vibration_peak_g",
    "hourmeter_h",
    "health_score",
    "severity_score",
    "source",
]

SUMMARY_COLUMNS = [
    "data_hora_periodo",
    "data_hora_periodo_utc",
    "modo_final",
    "status_final",
    "amostras_no_periodo",
    "rpm_inst_final",
    "rpm_media",
    "vibracao_rms_media_mm_s",
    "vibracao_rms_max_mm_s",
    "temperatura_media_c",
    "temperatura_max_c",
    "ultrassom_media_db",
    "ultrassom_max_db",
    "kurtosis_media",
    "kurtosis_max",
    "crest_factor_media",
    "crest_factor_max",
    "pico_vibracao_max_g",
    "health_score_final",
    "health_score_media",
    "health_score_min",
    "severity_score_final",
    "severity_score_media",
    "severity_score_max",
    "horimetro_inicial_h",
    "horimetro_final_h",
    "horas_operadas_periodo",
    "minutos_com_alerta",
    "minutos_criticos",
]


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def format_local(value: Any, timezone_str: str) -> str:
    parsed = parse_utc(value)

    if parsed is None:
        return "-"

    return parsed.astimezone(ZoneInfo(timezone_str)).strftime("%d/%m/%Y %H:%M:%S")


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rounded(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None

    return round(value, digits)


def average(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]

    if not valid:
        return None

    return sum(valid) / len(valid)


def max_value(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None


def min_value(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return min(valid) if valid else None


def is_alert_status(status: Any) -> bool:
    return str(status or "").upper() in {"ATENÇÃO", "ATENCAO", "ATENÇÃO ALTA", "ALERTA", "CRÍTICO", "CRITICO"}


def is_critical_status(status: Any, severity_score: Any) -> bool:
    severity = number(severity_score)
    return str(status or "").upper() in {"CRÍTICO", "CRITICO"} or (severity is not None and severity >= 60)


def minute_rows(items: list[dict[str, Any]], timezone_str: str = "America/Sao_Paulo") -> list[dict[str, Any]]:
    rows = []

    for item in sorted(items, key=lambda row: str(row.get("ts_utc_minute", ""))):
        row = {
            "data_hora": format_local(item.get("ts_utc_minute"), timezone_str),
            "data_hora_utc": item.get("ts_utc_minute"),
            "tenant_id": item.get("tenant_id"),
            "plant_id": item.get("plant_id"),
            "asset_id": item.get("asset_id"),
            "mode": item.get("mode"),
            "status_label": item.get("status_label"),
            "rpm": item.get("rpm"),
            "vibration_rms_mm_s": item.get("vibration_rms_mm_s"),
            "temperature_c": item.get("temperature_c"),
            "ultrasound_db": item.get("ultrasound_db"),
            "kurtosis_index": item.get("kurtosis_index"),
            "crest_factor_index": item.get("crest_factor_index"),
            "vibration_peak_g": item.get("vibration_peak_g"),
            "hourmeter_h": item.get("hourmeter_h"),
            "health_score": item.get("health_score"),
            "severity_score": item.get("severity_score"),
            "source": item.get("source"),
        }
        rows.append(row)

    return rows


def window_start(timestamp: datetime, window_hours: int) -> datetime:
    timestamp = timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    hour = timestamp.hour - (timestamp.hour % window_hours)
    return timestamp.replace(hour=hour)


def grouped_by_window(items: list[dict[str, Any]], window_hours: int) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}

    for item in sorted(items, key=lambda row: str(row.get("ts_utc_minute", ""))):
        parsed = parse_utc(item.get("ts_utc_minute"))

        if parsed is None:
            continue

        key = window_start(parsed, window_hours).isoformat().replace("+00:00", "Z")
        groups.setdefault(key, []).append(item)

    return [groups[key] for key in sorted(groups)]


def summary_rows(
    items: list[dict[str, Any]],
    *,
    window_hours: int,
    timezone_str: str = "America/Sao_Paulo",
) -> list[dict[str, Any]]:
    rows = []

    for group in grouped_by_window(items, window_hours):
        first = group[0]
        last = group[-1]
        period_utc = window_start(parse_utc(first.get("ts_utc_minute")) or datetime.now(UTC), window_hours)
        hourmeter_initial = number(first.get("hourmeter_h"))
        hourmeter_final = number(last.get("hourmeter_h"))

        def values(name: str) -> list[float | None]:
            return [number(item.get(name)) for item in group]

        row = {
            "data_hora_periodo": format_local(period_utc.isoformat().replace("+00:00", "Z"), timezone_str),
            "data_hora_periodo_utc": period_utc.isoformat().replace("+00:00", "Z"),
            "modo_final": last.get("mode"),
            "status_final": last.get("status_label"),
            "amostras_no_periodo": len(group),
            "rpm_inst_final": last.get("rpm"),
            "rpm_media": rounded(average(values("rpm"))),
            "vibracao_rms_media_mm_s": rounded(average(values("vibration_rms_mm_s"))),
            "vibracao_rms_max_mm_s": rounded(max_value(values("vibration_rms_mm_s"))),
            "temperatura_media_c": rounded(average(values("temperature_c"))),
            "temperatura_max_c": rounded(max_value(values("temperature_c"))),
            "ultrassom_media_db": rounded(average(values("ultrasound_db"))),
            "ultrassom_max_db": rounded(max_value(values("ultrasound_db"))),
            "kurtosis_media": rounded(average(values("kurtosis_index"))),
            "kurtosis_max": rounded(max_value(values("kurtosis_index"))),
            "crest_factor_media": rounded(average(values("crest_factor_index"))),
            "crest_factor_max": rounded(max_value(values("crest_factor_index"))),
            "pico_vibracao_max_g": rounded(max_value(values("vibration_peak_g"))),
            "health_score_final": last.get("health_score"),
            "health_score_media": rounded(average(values("health_score"))),
            "health_score_min": rounded(min_value(values("health_score"))),
            "severity_score_final": last.get("severity_score"),
            "severity_score_media": rounded(average(values("severity_score"))),
            "severity_score_max": rounded(max_value(values("severity_score"))),
            "horimetro_inicial_h": hourmeter_initial,
            "horimetro_final_h": hourmeter_final,
            "horas_operadas_periodo": rounded(
                None if hourmeter_initial is None or hourmeter_final is None else hourmeter_final - hourmeter_initial,
                4,
            ),
            "minutos_com_alerta": sum(1 for item in group if is_alert_status(item.get("status_label"))),
            "minutos_criticos": sum(
                1 for item in group if is_critical_status(item.get("status_label"), item.get("severity_score"))
            ),
        }
        rows.append(row)

    return rows


def rows_to_csv(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if not rows:
        return ""

    output = io.StringIO()
    fieldnames = columns or list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def rows_to_txt(rows: list[dict[str, Any]], *, title: str) -> str:
    lines = [title, "=" * len(title), ""]

    if not rows:
        lines.append("Nenhum registro encontrado.")
        return "\n".join(lines)

    for index, row in enumerate(rows, start=1):
        lines.append(f"Registro {index}")

        for key, value in row.items():
            lines.append(f"{key}: {value}")

        lines.append("")

    return "\n".join(lines)
