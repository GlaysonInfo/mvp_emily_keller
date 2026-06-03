from __future__ import annotations

from src.dashboard.condition_virtual_bench_ui import PAGE_NAME, _asset_options, _case_rows


def test_condition_virtual_bench_has_business_page_name() -> None:
    assert PAGE_NAME == "Bancada Virtual — Equipamentos"


def test_asset_options_use_configured_assets_or_demo_fallback() -> None:
    assert _asset_options([]) == [{"asset_id": "motor_001", "label": "motor_001 - Motor demonstração"}]

    options = _asset_options(
        [
            {"asset_id": "motor_001", "asset_name": "Motor Linha 1"},
            {"asset_id": "", "asset_name": "Ignorado"},
        ]
    )

    assert options == [{"asset_id": "motor_001", "label": "motor_001 - Motor Linha 1"}]


def test_case_rows_summarize_demo_impact() -> None:
    rows = _case_rows(
        [
            {
                "case_name": "Risco Crítico",
                "status_label": "CRÍTICO",
                "health_score": 31.6,
                "severity_score": 68.4,
                "metrics": {
                    "vibration_rms_mm_s": 8.7,
                    "temperature_c": 96.2,
                    "ultrasound_db": 68.1,
                },
                "alert": {"severity": "critical"},
            }
        ]
    )

    assert rows == [
        {
            "Cenário": "Risco Crítico",
            "Status": "CRÍTICO",
            "Health": 31.6,
            "Severity": 68.4,
            "Vibração": 8.7,
            "Temperatura": 96.2,
            "Ultrassom": 68.1,
            "Gera alerta": "Sim",
        }
    ]
