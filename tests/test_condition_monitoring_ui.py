from __future__ import annotations

from src.dashboard.condition_monitoring_ui import (
    active_operator_alerts,
    alerts_for_asset,
    alert_is_persisted,
    dominant_metric,
    next_operator_action,
    operator_kpis,
    operator_rows,
    persist_or_update_quick_alert,
    technical_evidence_rows,
    technical_diagnostic_rows,
    technical_summary,
    technical_trend_summary,
)


class FakeAlertsRepository:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.updated: list[dict] = []

    def create_manual_alert(
        self,
        tenant_id: str,
        plant_id: str,
        asset_id: str,
        asset_name: str,
        metric: str,
        status_label: str,
        value: float | None,
        threshold: float | None,
        recommended_action: str,
        created_by: str = "operador_demo",
        note: str = "",
    ) -> dict:
        item = {
            "tenant_asset": f"{tenant_id}#{asset_id}",
            "alert_key": f"open#manual#{metric}",
            "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
            "sk": f"ALERT#ACTIVE#MANUAL#{metric}",
            "tenant_id": tenant_id,
            "plant_id": plant_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "metric": metric,
            "status_label": status_label,
            "value": value,
            "threshold": threshold,
            "recommended_action": recommended_action,
            "created_by": created_by,
            "note": note,
        }
        self.created.append(item)
        return item

    def update_status(
        self,
        tenant_asset: str,
        alert_key: str,
        new_status: str,
        user_name: str,
        note: str = "",
        action_taken: str = "",
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict:
        item = {
            "tenant_asset": tenant_asset,
            "alert_key": alert_key,
            "status": new_status,
            "last_status_update_by": user_name,
            "last_note": note,
            "last_action_taken": action_taken,
            "pk": pk,
            "sk": sk,
        }
        self.updated.append(item)
        return item


def test_operator_rows_prioritize_riskiest_current_states() -> None:
    rows = operator_rows(
        [
            {
                "asset_id": "normal",
                "asset_name": "Normal",
                "asset_type": "Motor",
                "status_label": "NORMAL",
                "severity_score": 2,
            },
            {
                "asset_id": "critical",
                "asset_name": "Critical",
                "asset_type": "Motor",
                "status_label": "CRITICO",
                "severity_score": 91,
            },
        ],
        [],
    )

    assert [row["asset_id"] for row in rows] == ["critical", "normal"]


def test_operator_kpis_counts_field_queue_and_generated_alerts() -> None:
    rows = operator_rows(
        [
            {"asset_id": "normal", "status_label": "NORMAL", "severity_score": 2},
            {"asset_id": "attention", "status_label": "ATENCAO", "severity_score": 30},
            {"asset_id": "critical", "status_label": "CRITICO", "severity_score": 91},
        ],
        [],
    )

    kpis = operator_kpis(rows)

    assert kpis["total"] == 3
    assert kpis["field_queue"] == 2
    assert kpis["alerts_active"] == 2
    assert kpis["critical"] == 1


def test_active_operator_alerts_prefers_repository_alerts_when_available() -> None:
    rows = operator_rows([{"asset_id": "attention", "status_label": "ATENCAO"}], [])
    alerts = [{"asset_id": "external", "metric": "vibration"}]

    assert active_operator_alerts(rows, alerts) == alerts


def test_generated_operator_alerts_are_marked_as_not_persisted() -> None:
    rows = operator_rows([{"asset_id": "attention", "status_label": "ATENCAO"}], [])

    alerts = active_operator_alerts(rows, [])

    assert len(alerts) == 1
    assert not alert_is_persisted(alerts[0])


def test_next_operator_action_uses_recommendation_for_attention_state() -> None:
    action = next_operator_action(
        {
            "status_label": "ATENCAO",
            "recommended_action": "Inspecionar mancais e registrar observacao.",
        }
    )

    assert action == "Inspecionar mancais e registrar observacao."


def test_quick_treatment_updates_existing_alert() -> None:
    repo = FakeAlertsRepository()

    updated = persist_or_update_quick_alert(
        repo=repo,
        alert={
            "tenant_asset": "cliente_demo#motor_001",
            "alert_key": "open#condition_state",
            "pk": "TENANT#cliente_demo#ASSET#motor_001",
            "sk": "ALERT#ACTIVE#condition_state",
        },
        tenant_id="cliente_demo",
        plant_id="lab_virtual",
        new_status="acknowledged",
        user_name="Ana",
        note="Ciente.",
        action_taken="Operador avisado.",
    )

    assert updated["status"] == "acknowledged"
    assert repo.created == []
    assert repo.updated[0]["tenant_asset"] == "cliente_demo#motor_001"


def test_quick_treatment_creates_manual_alert_for_state_derived_event() -> None:
    repo = FakeAlertsRepository()

    updated = persist_or_update_quick_alert(
        repo=repo,
        alert={
            "asset_id": "motor_001",
            "asset_name": "Motor Linha 1",
            "metric": "condition_state",
            "status_label": "ATENCAO",
            "value": 35.0,
            "recommended_action": "Inspecionar mancais.",
        },
        tenant_id="cliente_demo",
        plant_id="lab_virtual",
        new_status="in_progress",
        user_name="Ana",
        note="Atendimento iniciado.",
        action_taken="Equipe em campo.",
    )

    assert len(repo.created) == 1
    assert updated["status"] == "in_progress"
    assert updated["tenant_asset"] == "cliente_demo#motor_001"


def test_dominant_metric_identifies_highest_relative_metric() -> None:
    assert dominant_metric(
        {
            "vibration_rms_mm_s": 2.0,
            "temperature_c": 90.0,
            "ultrasound_db": 20.0,
            "severity_score": 20.0,
        }
    ) == "Temperatura"


def test_technical_diagnostic_rows_prioritize_risk_and_include_dominant_metric() -> None:
    rows = operator_rows(
        [
            {
                "asset_id": "normal",
                "asset_name": "Normal",
                "asset_type": "Motor",
                "status_label": "NORMAL",
                "severity_score": 2,
                "temperature_c": 45,
            },
            {
                "asset_id": "alert",
                "asset_name": "Alert",
                "asset_type": "Motor",
                "status_label": "ALERTA",
                "severity_score": 55,
                "vibration_rms_mm_s": 6.0,
            },
        ],
        [],
    )

    diagnostics = technical_diagnostic_rows(rows)

    assert [row["asset_id"] for row in diagnostics] == ["alert", "normal"]
    assert diagnostics[0]["dominant_metric"] == "Vibração"


def test_technical_summary_exposes_diagnostic_queue_and_top_hypothesis() -> None:
    rows = operator_rows(
        [
            {"asset_id": "normal", "asset_name": "Normal", "status_label": "NORMAL", "severity_score": 2},
            {"asset_id": "critical", "asset_name": "Critical", "status_label": "CRITICO", "severity_score": 90},
        ],
        [],
    )

    summary = technical_summary(rows, [{"asset_id": "critical"}])

    assert summary["assets"] == 2
    assert summary["diagnostic_queue"] == 1
    assert summary["active_alerts"] == 1
    assert summary["top_asset_id"] == "critical"


def test_alerts_for_asset_filters_correlated_events() -> None:
    alerts = [
        {"asset_id": "motor_001", "metric": "temperature"},
        {"asset_id": "motor_002", "metric": "vibration"},
    ]

    assert alerts_for_asset(alerts, "motor_001") == [{"asset_id": "motor_001", "metric": "temperature"}]


def test_technical_trend_summary_calculates_deltas_from_history_to_current() -> None:
    trend = technical_trend_summary(
        [
            {"ts_utc_minute": "2026-06-01T10:00:00Z", "severity_score": 20, "health_score": 80},
            {"ts_utc_minute": "2026-06-01T11:00:00Z", "severity_score": 25, "health_score": 75},
        ],
        {"severity_score": 35, "health_score": 65},
    )

    assert trend["has_history"] is True
    assert trend["samples"] == 2
    assert trend["severity_delta"] == 15
    assert trend["health_delta"] == -15
    assert trend["trend_label"] == "Piora relevante"


def test_technical_trend_summary_reports_missing_history() -> None:
    trend = technical_trend_summary([], {"severity_score": 35, "health_score": 65})

    assert trend["has_history"] is False
    assert trend["samples"] == 0
    assert trend["trend_label"] == "Histórico indisponível"


def test_technical_evidence_rows_include_current_state_trend_and_alerts() -> None:
    row = operator_rows(
        [
            {
                "asset_id": "motor_001",
                "asset_name": "Motor Linha 1",
                "status_label": "ALERTA",
                "severity_score": 45,
                "health_score": 55,
                "vibration_rms_mm_s": 5.4,
                "temperature_c": 70,
                "ultrasound_db": 40,
                "diagnosis": "Vibração elevada.",
                "recommended_action": "Inspecionar base.",
            }
        ],
        [],
    )[0]
    trend = {"trend_label": "Piora relevante", "severity_delta": 12, "health_delta": -10}

    evidence = technical_evidence_rows(
        row=row,
        alerts=[{"asset_id": "motor_001"}, {"asset_id": "motor_002"}],
        trend=trend,
    )

    values = {item["Evidência"]: item["Valor"] for item in evidence}
    assert values["Ativo"] == "Motor Linha 1"
    assert values["Tendência"] == "Piora relevante"
    assert values["Eventos correlacionados"] == 1
    assert values["Diagnóstico"] == "Vibração elevada."
