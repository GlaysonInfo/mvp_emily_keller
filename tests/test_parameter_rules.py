from __future__ import annotations

from src.rules_engine.parameter_rules import classify_parameter_value, evaluate_parameter_rules


def test_classify_parameter_value_supports_all_rule_modes() -> None:
    higher = {
        "rule_mode": "higher_is_worse",
        "attention_min": 3,
        "alert_min": 5,
        "critical_min": 8,
    }
    lower = {
        "rule_mode": "lower_is_worse",
        "attention_max": 70,
        "alert_max": 50,
        "critical_max": 30,
    }
    ideal = {
        "rule_mode": "ideal_range",
        "normal_min": 8,
        "normal_max": 12,
        "attention_min": 7,
        "attention_max": 13,
        "alert_min": 6,
        "alert_max": 14,
        "critical_min": 5,
        "critical_max": 15,
    }

    assert classify_parameter_value(higher, 8.5) == ("CRÍTICO", 8.0)
    assert classify_parameter_value(lower, 45) == ("ALERTA", 50.0)
    assert classify_parameter_value(ideal, 14.5) == ("ALERTA", 14.0)
    assert classify_parameter_value(ideal, 10) == ("NORMAL", None)


def test_parameter_rule_waits_for_persistence() -> None:
    config = {
        "parameters_alerts": [
            {
                "asset_id": "motor_001",
                "metric": "temperature_c",
                "rule_mode": "higher_is_worse",
                "attention_min": 60,
                "alert_min": 70,
                "critical_min": 80,
                "persistence_min": 2,
                "enabled": True,
            }
        ]
    }
    first_payload = {
        "asset_id": "motor_001",
        "timestamp": "2026-06-06T10:00:00Z",
        "metrics": [{"name": "temperature_c", "value": 75}],
    }

    alerts, state, evaluations, has_rules = evaluate_parameter_rules(config, first_payload)
    assert has_rules is True
    assert alerts == []
    assert evaluations[0]["persisted"] is False

    second_payload = {**first_payload, "timestamp": "2026-06-06T10:02:00Z"}
    alerts, _, evaluations, _ = evaluate_parameter_rules(
        config,
        second_payload,
        previous_rule_state=state,
    )
    assert alerts[0]["status_label"] == "ALERTA"
    assert evaluations[0]["persisted"] is True


def test_parameter_rule_requires_stable_recovery() -> None:
    config = {
        "parameters_alerts": [
            {
                "asset_id": "motor_001",
                "metric": "temperature_c",
                "rule_mode": "higher_is_worse",
                "attention_min": 60,
                "alert_min": 70,
                "critical_min": 80,
                "persistence_min": 1,
                "enabled": True,
            }
        ]
    }
    prior = {
        "temperature_c": {
            "status_label": "ALERTA",
            "first_seen_at": "2026-06-06T10:00:00Z",
            "last_seen_at": "2026-06-06T10:01:00Z",
            "value": 75,
            "threshold": 70,
            "persistence_min": 1,
            "persisted": True,
        }
    }
    normal_payload = {
        "asset_id": "motor_001",
        "timestamp": "2026-06-06T10:02:00Z",
        "metrics": [{"name": "temperature_c", "value": 50}],
    }

    alerts, recovering_state, evaluations, _ = evaluate_parameter_rules(
        config,
        normal_payload,
        previous_rule_state=prior,
    )
    assert alerts[0]["probable_cause"].endswith("em validação de recuperação")
    assert evaluations[0]["recovering"] is True

    confirmed_payload = {**normal_payload, "timestamp": "2026-06-06T10:03:00Z"}
    alerts, final_state, evaluations, _ = evaluate_parameter_rules(
        config,
        confirmed_payload,
        previous_rule_state=recovering_state,
    )
    assert alerts == []
    assert final_state == {}
    assert evaluations[0]["recovering"] is False
