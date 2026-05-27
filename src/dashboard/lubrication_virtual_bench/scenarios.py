from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.lubrication.lubrication_engine import evaluate_lubrication_cycle


OUTLETS = ("saida_graxa_01", "saida_graxa_02", "saida_graxa_03", "saida_graxa_04")

BASE_OUTLETS = {
    "saida_graxa_01": {"pressure": 84.2, "peak": 102.3, "min": 2.0, "rise": 3.2, "decay": 4.8},
    "saida_graxa_02": {"pressure": 91.7, "peak": 108.1, "min": 2.0, "rise": 3.5, "decay": 5.1},
    "saida_graxa_03": {"pressure": 88.4, "peak": 104.0, "min": 2.0, "rise": 3.6, "decay": 4.9},
    "saida_graxa_04": {"pressure": 96.8, "peak": 116.2, "min": 3.0, "rise": 3.4, "decay": 5.4},
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "normal": {
        "label": "Operação normal",
        "description": "Todas as saídas apresentam pulso e pressão dentro da faixa esperada.",
        "expected": "Status NORMAL em todas as saídas.",
    },
    "queda_pressao": {
        "label": "Queda progressiva de pressão",
        "description": "A saída 03 perde pressão ciclo a ciclo, simulando vazamento, linha aberta ou alimentação insuficiente.",
        "expected": "A saída 03 deve evoluir para baixa pressão.",
    },
    "aumento_pressao": {
        "label": "Aumento progressivo de pressão",
        "description": "A saída 04 aumenta o pico de pressão gradualmente, indicando restrição crescente.",
        "expected": "A saída 04 deve entrar em ALERTA por alta pressão.",
    },
    "entupimento_parcial": {
        "label": "Entupimento parcial",
        "description": "A saída 04 apresenta alta pressão e alívio lento, compatível com obstrução parcial.",
        "expected": "A saída 04 deve indicar alta pressão + alívio lento.",
    },
    "entupimento_severo": {
        "label": "Entupimento severo",
        "description": "A saída 04 ultrapassa pressão crítica e demora a aliviar, simulando bloqueio severo.",
        "expected": "A saída 04 deve gerar alerta de pico elevado com evidência de limite crítico.",
    },
    "graxa_contaminada": {
        "label": "Graxa contaminada/endurecida",
        "description": "As saídas 02 e 04 ficam mais lentas, com maior pico e alívio prolongado.",
        "expected": "O sistema deve sugerir restrição, graxa endurecida ou ponto pesado.",
    },
    "sem_graxa_ponta": {
        "label": "Ausência completa de graxa na ponta",
        "description": "A saída 03 não desenvolve pulso suficiente durante o ciclo.",
        "expected": "A saída 03 deve ir para CRÍTICO por ausência de pulso.",
    },
    "pulso_intermitente": {
        "label": "Pulso intermitente",
        "description": "A saída 02 alterna entre ciclo normal, baixa pressão e ausência de pulso.",
        "expected": "A timeline deve alternar entre normalidade, atenção e crítico.",
    },
    "recuperacao_pos_manutencao": {
        "label": "Recuperação pós-manutenção",
        "description": "As saídas partem de condição anormal e retornam gradualmente ao padrão normal.",
        "expected": "A sequência deve terminar com status NORMAL.",
    },
}


def scenario_options() -> list[tuple[str, str]]:
    return [(key, value["label"]) for key, value in SCENARIOS.items()]


def scenario_detail(scenario_id: str) -> dict[str, Any]:
    return SCENARIOS.get(scenario_id, SCENARIOS["normal"])


def _round(value: float) -> float:
    return round(float(value), 1)


def _progress(index: int, total: int) -> float:
    if total <= 1:
        return 1.0
    return index / (total - 1)


def _normal_profile(index: int) -> dict[str, dict[str, float]]:
    profile = deepcopy(BASE_OUTLETS)
    offset = (index % 3) - 1
    for outlet in profile.values():
        outlet["pressure"] += offset * 0.7
        outlet["peak"] += offset * 1.0
    return profile


def _apply_scenario(profile: dict[str, dict[str, float]], scenario_id: str, index: int, total: int) -> None:
    p = _progress(index, total)

    if scenario_id == "queda_pressao":
        profile["saida_graxa_03"].update(
            pressure=_round(78.0 - p * 70.0),
            peak=_round(88.0 - p * 78.8),
            min=0.0,
            rise=_round(4.0 + p * 5.5),
            decay=2.4,
        )
    elif scenario_id == "aumento_pressao":
        profile["saida_graxa_04"].update(
            pressure=_round(98.0 + p * 48.0),
            peak=_round(126.0 + p * 58.0),
            min=4.0,
            rise=_round(3.0 + p * 2.0),
            decay=_round(6.0 + p * 8.0),
        )
    elif scenario_id == "entupimento_parcial":
        profile["saida_graxa_04"].update(
            pressure=_round(115.0 + p * 35.0),
            peak=_round(154.0 + p * 32.0),
            min=4.0,
            rise=_round(4.0 + p * 4.0),
            decay=_round(13.0 + p * 9.0),
        )
    elif scenario_id == "entupimento_severo":
        profile["saida_graxa_04"].update(
            pressure=_round(145.0 + p * 55.0),
            peak=_round(182.0 + p * 55.0),
            min=5.0,
            rise=_round(5.0 + p * 6.0),
            decay=_round(18.0 + p * 14.0),
        )
    elif scenario_id == "graxa_contaminada":
        for outlet_id, base_peak in [("saida_graxa_02", 118.0), ("saida_graxa_04", 132.0)]:
            profile[outlet_id].update(
                pressure=_round(base_peak - 20.0 + p * 25.0),
                peak=_round(base_peak + p * 48.0),
                min=3.0,
                rise=_round(7.0 + p * 7.0),
                decay=_round(12.0 + p * 12.0),
            )
    elif scenario_id == "sem_graxa_ponta":
        profile["saida_graxa_03"].update(
            pressure=_round(2.5 + p * 0.5),
            peak=_round(3.0 + p * 1.2),
            min=0.5,
            rise=_round(1.0 + p * 0.5),
            decay=1.2,
        )
    elif scenario_id == "pulso_intermitente":
        if index % 3 == 1:
            profile["saida_graxa_02"].update(pressure=18.0, peak=9.4, min=0.0, rise=9.0, decay=3.0)
        elif index % 3 == 2:
            profile["saida_graxa_02"].update(pressure=2.0, peak=3.4, min=0.5, rise=1.2, decay=1.0)
    elif scenario_id == "recuperacao_pos_manutencao":
        severity = 1.0 - p
        profile["saida_graxa_03"].update(
            pressure=_round(84.0 - severity * 76.0),
            peak=_round(102.0 - severity * 92.0),
            min=0.0,
            rise=_round(3.8 + severity * 5.0),
            decay=3.0,
        )
        profile["saida_graxa_04"].update(
            pressure=_round(96.0 + severity * 48.0),
            peak=_round(116.0 + severity * 62.0),
            min=4.0,
            rise=4.0,
            decay=_round(5.0 + severity * 16.0),
        )


def _metrics_from_profile(profile: dict[str, dict[str, float]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for outlet_id, values in profile.items():
        metrics[f"pressure_{outlet_id}_bar"] = _round(values["pressure"])
        metrics[f"peak_{outlet_id}_bar"] = _round(values["peak"])
        metrics[f"min_{outlet_id}_bar"] = _round(values["min"])
        metrics[f"avg_{outlet_id}_bar"] = _round((values["pressure"] + values["peak"] + values["min"]) / 3)
        metrics[f"rise_time_{outlet_id}_sec"] = _round(values["rise"])
        metrics[f"decay_time_{outlet_id}_sec"] = _round(values["decay"])
    return metrics


def pressure_curve_from_metrics(metrics: dict[str, float], outlet_id: str) -> list[dict[str, float]]:
    peak = float(metrics.get(f"peak_{outlet_id}_bar", 0.0))
    pressure = float(metrics.get(f"pressure_{outlet_id}_bar", peak))
    min_pressure = float(metrics.get(f"min_{outlet_id}_bar", 0.0))
    rise = max(float(metrics.get(f"rise_time_{outlet_id}_sec", 3.0)), 0.5)
    decay = max(float(metrics.get(f"decay_time_{outlet_id}_sec", 3.0)), 0.5)

    return [
        {"ts_sec": 0.0, "pressure_bar": _round(min_pressure)},
        {"ts_sec": _round(rise * 0.4), "pressure_bar": _round((pressure + min_pressure) / 2)},
        {"ts_sec": _round(rise), "pressure_bar": _round(peak)},
        {"ts_sec": _round(rise + decay * 0.5), "pressure_bar": _round((peak + min_pressure) / 2)},
        {"ts_sec": _round(rise + decay), "pressure_bar": _round(min_pressure)},
    ]


def build_lubrication_scenario_payloads(
    config: dict[str, Any],
    scenario_id: str,
    *,
    cycles: int = 6,
    start_time: datetime | None = None,
    interval_seconds: int = 60,
) -> list[dict[str, Any]]:
    cycles = max(1, int(cycles))
    scenario_id = scenario_id if scenario_id in SCENARIOS else "normal"
    start_time = start_time or datetime.now(timezone.utc)

    payloads = []
    for index in range(cycles):
        timestamp = start_time + timedelta(seconds=index * interval_seconds)
        profile = _normal_profile(index)
        _apply_scenario(profile, scenario_id, index, cycles)
        metrics = _metrics_from_profile(profile)

        payloads.append(
            {
                "tenant_id": config.get("tenant_id", "cliente_demo"),
                "plant_id": config.get("plant_id", "lab_virtual"),
                "asset_id": config.get("asset_id", "sistema_lubrificacao_01"),
                "source_id": config.get("source_id", "grease_gateway_01"),
                "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
                "cycle_id": f"cycle_virtual_{scenario_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                "scenario_id": scenario_id,
                "scenario_label": scenario_detail(scenario_id)["label"],
                "metrics": metrics,
                "curves": {outlet_id: pressure_curve_from_metrics(metrics, outlet_id) for outlet_id in OUTLETS},
                "quality": {
                    "source": "lubrication_virtual_bench",
                    "sample_type": "temporal_scenario",
                    "cycle_index": index + 1,
                    "cycle_count": cycles,
                },
            }
        )

    return payloads


def evaluate_lubrication_payloads(payloads: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    return [evaluate_lubrication_cycle(payload, config) for payload in payloads]


def evaluate_lubrication_scenario(config: dict[str, Any], scenario_id: str, *, cycles: int = 6) -> list[dict[str, Any]]:
    payloads = build_lubrication_scenario_payloads(config, scenario_id, cycles=cycles)
    return evaluate_lubrication_payloads(payloads, config)


def scenario_results_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, result in enumerate(results, start=1):
        outlets = {outlet["outlet_id"]: outlet for outlet in result.get("outlets", [])}
        rows.append(
            {
                "Ciclo": index,
                "Status": result.get("status_label"),
                "Normais": result.get("normal_count"),
                "Atenção": result.get("attention_count"),
                "Alertas": result.get("alert_count"),
                "Críticos": result.get("critical_count"),
                "Saída 02": outlets.get("saida_graxa_02", {}).get("status", "-"),
                "Saída 03": outlets.get("saida_graxa_03", {}).get("status", "-"),
                "Saída 04": outlets.get("saida_graxa_04", {}).get("status", "-"),
                "Maior pressão": result.get("max_pressure_bar"),
                "Maior anomalia": result.get("max_anomaly_score"),
            }
        )
    return rows
