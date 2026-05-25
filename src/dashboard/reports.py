from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

try:
    from dashboard.history_export import rows_to_csv, rows_to_txt, summary_rows
    from dashboard.plant_overview_ui import get_metric, plant_kpis, states_to_rows
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.history_export import rows_to_csv, rows_to_txt, summary_rows
    from src.dashboard.plant_overview_ui import get_metric, plant_kpis, states_to_rows


PERIODS: dict[str, timedelta] = {
    "Última 1 hora": timedelta(hours=1),
    "Últimas 6 horas": timedelta(hours=6),
    "Últimas 12 horas": timedelta(hours=12),
    "Últimas 24 horas": timedelta(hours=24),
    "Últimos 7 dias": timedelta(days=7),
}

REPORTS_BY_TYPE = {
    "Gerais": ["Visão geral da planta", "Ranking de risco"],
    "Operacionais": ["Relatório individual do ativo", "Tendência operacional"],
    "Eventos": ["Alertas ativos", "Histórico de alertas"],
}

REPORT_FILENAMES = {
    "Visão geral da planta": "visao_geral_planta",
    "Ranking de risco": "ranking_risco",
    "Relatório individual do ativo": "relatorio_individual_ativo",
    "Tendência operacional": "tendencia_operacional",
    "Alertas ativos": "alertas_ativos",
    "Histórico de alertas": "historico_alertas",
}


def safe_number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, bool) or value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percent(part: int | float, total: int | float) -> str:
    if not total:
        return "-"

    return f"{(float(part) / float(total)) * 100:.1f}%"


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


def now_utc() -> datetime:
    return datetime.now(UTC)


def period_bounds(period_label: str, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = (now or now_utc()).astimezone(UTC)
    return end - PERIODS[period_label], end


def normalize_asset_options(states: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows = states_to_rows(states)
    return [(str(row["asset_id"]), f"{row['asset_id']} - {row['asset_name']}") for row in rows]


def find_state(states: list[dict[str, Any]], asset_id: str) -> dict[str, Any] | None:
    for state in states:
        if state.get("asset_id") == asset_id:
            return state

    return None


def most_critical_asset(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None

    return max(rows, key=lambda row: (row["risk_order"], row["severity_score"]))


def most_critical_area(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "-"

    area_scores: dict[str, tuple[int, float]] = {}

    for row in rows:
        area = str(row.get("area") or "-")
        current_count, current_severity = area_scores.get(area, (0, 0.0))
        risk_count = 1 if row["risk_order"] >= 2 else 0
        area_scores[area] = (current_count + risk_count, max(current_severity, row["severity_score"]))

    area, _score = max(area_scores.items(), key=lambda item: item[1])
    return area


def plant_overview_report(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = states_to_rows(states)
    kpis = plant_kpis(rows)
    total = kpis["total"]
    critical = most_critical_asset(rows)

    return [
        {"Indicador": "Total de ativos monitorados", "Valor": total, "Percentual": "100.0%" if total else "-"},
        {"Indicador": "Ativos normais", "Valor": kpis["normal"], "Percentual": percent(kpis["normal"], total)},
        {"Indicador": "Ativos em atenção", "Valor": kpis["attention"], "Percentual": percent(kpis["attention"], total)},
        {"Indicador": "Ativos em alerta", "Valor": kpis["alert"], "Percentual": percent(kpis["alert"], total)},
        {"Indicador": "Ativos críticos", "Valor": kpis["critical"], "Percentual": percent(kpis["critical"], total)},
        {"Indicador": "Ativos sem comunicação", "Valor": kpis["offline"], "Percentual": percent(kpis["offline"], total)},
        {"Indicador": "Health Score médio", "Valor": None if kpis["health_mean"] is None else round(kpis["health_mean"], 1), "Percentual": "-"},
        {"Indicador": "Severity Score máximo", "Valor": None if kpis["severity_max"] is None else round(kpis["severity_max"], 1), "Percentual": "-"},
        {"Indicador": "Ativo mais crítico", "Valor": "-" if critical is None else critical["asset_name"], "Percentual": "-"},
        {"Indicador": "Área mais crítica", "Valor": most_critical_area(rows), "Percentual": "-"},
    ]


def risk_ranking_report(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = states_to_rows(states)
    report_rows = []

    for index, row in enumerate(rows, start=1):
        report_rows.append(
            {
                "Posição": index,
                "Ativo": row["asset_id"],
                "Nome": row["asset_name"],
                "Área": row["area"],
                "Tipo": row["asset_type"],
                "Criticidade": row["criticality"],
                "Status": row["status_label"],
                "Health Score": row["health_score"],
                "Severity Score": row["severity_score"],
                "Modo atual": row["mode"],
                "Última atualização": row["updated_at"],
                "Ação recomendada": row["recommended_action"],
            }
        )

    return report_rows


def individual_asset_report(state: dict[str, Any] | None) -> list[dict[str, Any]]:
    if state is None:
        return []

    metrics = [
        ("RPM", get_metric(state, "rpm")),
        ("Vibração RMS", get_metric(state, "vibration_rms_mm_s", "vibration_rms")),
        ("Temperatura", get_metric(state, "temperature_c", "temperature")),
        ("Ultrassom", get_metric(state, "ultrasound_db", "ultrasound")),
        ("Kurtosis", get_metric(state, "kurtosis", "kurtosis_index")),
        ("Crest Factor", get_metric(state, "crest_factor", "crest_factor_index")),
        ("Pico de vibração", get_metric(state, "vibration_peak_g", "vibration_peak")),
        ("Horímetro", get_metric(state, "hourmeter_h", "horimeter_h")),
    ]
    health = get_metric(state, "health_score")
    severity = get_metric(state, "severity_score", "severity")

    if severity is None and health is not None:
        severity = round(100.0 - health, 1)

    rows = [
        {"Campo": "Ativo", "Valor": state.get("asset_id")},
        {"Campo": "Nome", "Valor": state.get("asset_name", state.get("asset_id"))},
        {"Campo": "Tipo", "Valor": state.get("asset_type", "-")},
        {"Campo": "Área", "Valor": state.get("area", "-")},
        {"Campo": "Criticidade", "Valor": state.get("criticality", "-")},
        {"Campo": "Status atual", "Valor": state.get("status_label", "-")},
        {"Campo": "Health Score", "Valor": health},
        {"Campo": "Severity Score", "Valor": severity},
        {"Campo": "Modo atual", "Valor": state.get("mode_label") or state.get("mode") or state.get("failure_mode_simulated")},
        {"Campo": "Diagnóstico", "Valor": state.get("diagnosis", "-")},
        {"Campo": "Ação recomendada", "Valor": state.get("recommended_action", "-")},
    ]

    rows.extend({"Campo": name, "Valor": value} for name, value in metrics)
    return rows


def trend_report(history_items: list[dict[str, Any]], *, period_label: str) -> list[dict[str, Any]]:
    window_hours = 24 if period_label == "Últimos 7 dias" else 1
    return summary_rows(history_items, window_hours=window_hours)


def alert_rows(alerts: list[dict[str, Any]], states: list[dict[str, Any]], *, active_only: bool) -> list[dict[str, Any]]:
    state_by_asset = {str(state.get("asset_id")): state for state in states}
    rows = []

    for alert in sorted(alerts, key=lambda item: str(item.get("updated_at") or ""), reverse=True):
        status = str(alert.get("status") or "")

        if active_only and status.lower() in {"resolved", "closed"}:
            continue

        state = state_by_asset.get(str(alert.get("asset_id"))) or {}
        rows.append(
            {
                "Primeira detecção": alert.get("first_detected_at", "-"),
                "Última atualização": alert.get("updated_at", "-"),
                "Ativo": alert.get("asset_id", "-"),
                "Nome": state.get("asset_name", alert.get("asset_id", "-")),
                "Área": state.get("area", alert.get("plant_id", "-")),
                "Tipo de alerta": alert.get("alert_type", "-"),
                "Status": alert.get("status", "-"),
                "Severidade": alert.get("severity", "-"),
                "Confiança": alert.get("confidence", "-"),
                "Modo": alert.get("failure_mode_simulated", "-"),
                "Ação recomendada": alert.get("recommended_action", "-"),
                "Evidências": "; ".join(str(item) for item in alert.get("evidence", []) or []),
            }
        )

    return rows


def filter_alerts_by_period(alerts: list[dict[str, Any]], period_label: str, *, now: datetime | None = None) -> list[dict[str, Any]]:
    start, end = period_bounds(period_label, now=now)
    filtered = []

    for alert in alerts:
        timestamp = parse_utc(alert.get("updated_at") or alert.get("first_detected_at"))

        if timestamp is None or start <= timestamp <= end:
            filtered.append(alert)

    return filtered


def export_csv(rows: list[dict[str, Any]]) -> str:
    return rows_to_csv(rows)


def export_txt(rows: list[dict[str, Any]], title: str) -> str:
    return rows_to_txt(rows, title=title)
