from __future__ import annotations

from src.dashboard.operational_intelligence_ui import (
    integrated_action_plan,
    integrated_evidence_rows,
    integrated_hypothesis,
    integrated_operational_score,
)


def _condition_result() -> dict:
    return {
        "anomaly_score": 60,
        "recommendation": {
            "primary_hypothesis": "Aquecimento anormal",
            "immediate_actions": ["Inspecionar carga e ventilação."],
        },
    }


def _lubrication_summary() -> dict:
    return {
        "efficiency_score": 70,
        "status_label": "ATENÇÃO",
        "affected_outlets": 1,
        "monitored_equipment": 1,
        "recommendation": "Verificar saída com desvio de pressão.",
    }


def _linked_rows() -> list[dict]:
    return [
        {
            "Equipamento": "Motor Cliente 01",
            "Asset ID": "motor_cli01",
            "Saída": "Saída de Graxa 03",
            "Status equipamento": "ATENÇÃO",
            "Status saída": "ATENÇÃO",
        }
    ]


def test_integrated_operational_score_combines_condition_and_lubrication_risk() -> None:
    score = integrated_operational_score(_condition_result(), _lubrication_summary())

    assert score["condition_score"] == 60
    assert score["lubrication_efficiency"] == 70
    assert score["lubrication_risk"] == 30
    assert score["combined_score"] == 48.6
    assert score["risk_level"] == "ATENÇÃO"


def test_integrated_hypothesis_mentions_lubrication_when_linked_outlet_is_affected() -> None:
    hypothesis = integrated_hypothesis(
        condition_result=_condition_result(),
        lubrication_summary=_lubrication_summary(),
        linked_rows=_linked_rows(),
    )

    assert "Aquecimento anormal" in hypothesis
    assert "possível contribuição do sistema de lubrificação" in hypothesis


def test_integrated_action_plan_includes_condition_lubrication_and_correlation() -> None:
    plan = integrated_action_plan(
        condition_result=_condition_result(),
        lubrication_summary=_lubrication_summary(),
        linked_rows=_linked_rows(),
    )

    origins = [row["Origem"] for row in plan]
    assert origins == ["Condição", "Lubrificação", "Correlação"]
    assert "Saída de Graxa 03" in plan[-1]["Ação"]


def test_integrated_evidence_rows_expose_dual_service_signals() -> None:
    evidence = integrated_evidence_rows(
        condition_result=_condition_result(),
        lubrication_summary=_lubrication_summary(),
        linked_rows=_linked_rows(),
    )

    values = {row["Evidência"]: row["Valor"] for row in evidence}
    assert values["Score condição"] == 60
    assert values["Eficiência lubrificação"] == 70
    assert values["Saídas afetadas"] == 1
    assert values["Vínculos correlacionados"] == 1
