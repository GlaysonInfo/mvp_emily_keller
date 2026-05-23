from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

COLORS = {
    "normal": "#2ECC71",
    "attention": "#F1C40F",
    "alert": "#E67E22",
    "critical": "#E74C3C",
    "offline": "#95A5A6",
}

STATUS_LABELS = {
    "normal": "NORMAL",
    "attention": "ATENÇÃO",
    "alert": "ALERTA",
    "critical": "CRÍTICO",
    "offline": "SEM DADO",
}

GAUGE_DEFINITIONS = [
    {
        "key": "rpm",
        "title": "RPM",
        "unit": "rpm",
        "names": ("rpm",),
        "min_value": 0,
        "max_value": 3600,
        "attention": 2100,
        "alert": 2800,
        "critical": 3300,
        "decimals": 0,
        "inverse": False,
    },
    {
        "key": "health_score",
        "title": "Health Score",
        "unit": "",
        "names": ("health_score",),
        "min_value": 0,
        "max_value": 100,
        "attention": 75,
        "alert": 55,
        "critical": 35,
        "decimals": 1,
        "inverse": True,
    },
    {
        "key": "severity_score",
        "title": "Severity Score",
        "unit": "",
        "names": ("severity_score", "severity"),
        "min_value": 0,
        "max_value": 100,
        "attention": 25,
        "alert": 45,
        "critical": 65,
        "decimals": 1,
        "inverse": False,
    },
    {
        "key": "vibration",
        "title": "Vibração RMS",
        "unit": "mm/s",
        "names": ("vibration_rms_mm_s", "vibration_rms"),
        "min_value": 0,
        "max_value": 10,
        "attention": 2.8,
        "alert": 4.5,
        "critical": 7.1,
        "decimals": 2,
        "inverse": False,
    },
    {
        "key": "temperature",
        "title": "Temperatura",
        "unit": "°C",
        "names": ("temperature_c", "temperature"),
        "min_value": 0,
        "max_value": 120,
        "attention": 70,
        "alert": 85,
        "critical": 100,
        "decimals": 1,
        "inverse": False,
    },
    {
        "key": "ultrasound",
        "title": "Ultrassom",
        "unit": "dB",
        "names": ("ultrasound_db", "ultrasound"),
        "min_value": 0,
        "max_value": 90,
        "attention": 40,
        "alert": 55,
        "critical": 70,
        "decimals": 1,
        "inverse": False,
    },
    {
        "key": "kurtosis",
        "title": "Kurtosis",
        "unit": "index",
        "names": ("kurtosis", "kurtosis_index"),
        "min_value": 0,
        "max_value": 10,
        "attention": 3.5,
        "alert": 5.0,
        "critical": 7.0,
        "decimals": 2,
        "inverse": False,
    },
    {
        "key": "crest_factor",
        "title": "Crest Factor",
        "unit": "index",
        "names": ("crest_factor", "crest_factor_index"),
        "min_value": 0,
        "max_value": 10,
        "attention": 3.5,
        "alert": 5.0,
        "critical": 7.0,
        "decimals": 2,
        "inverse": False,
    },
    {
        "key": "vibration_peak",
        "title": "Pico de vibração",
        "unit": "g",
        "names": ("vibration_peak_g", "vibration_peak"),
        "min_value": 0,
        "max_value": 5,
        "attention": 0.8,
        "alert": 1.5,
        "critical": 2.5,
        "decimals": 2,
        "inverse": False,
    },
]


def to_float(value: Any) -> float | None:
    if isinstance(value, Mapping):
        value = value.get("value")

    if isinstance(value, bool) or value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def percent(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 0.0

    return clamp((value - min_value) / (max_value - min_value), 0.0, 1.0)


def status_by_thresholds(
    value: float | None,
    attention: float,
    alert: float,
    critical: float,
    *,
    inverse: bool = False,
) -> str:
    if value is None:
        return "offline"

    if inverse:
        if value <= critical:
            return "critical"
        if value <= alert:
            return "alert"
        if value <= attention:
            return "attention"
        return "normal"

    if value >= critical:
        return "critical"
    if value >= alert:
        return "alert"
    if value >= attention:
        return "attention"
    return "normal"


def axis_segments(
    min_value: float,
    max_value: float,
    attention: float,
    alert: float,
    critical: float,
    *,
    inverse: bool = False,
) -> list[list[Any]]:
    if inverse:
        return [
            [percent(critical, min_value, max_value), "#FADBD8"],
            [percent(alert, min_value, max_value), "#FDEBD0"],
            [percent(attention, min_value, max_value), "#FCF3CF"],
            [1, "#D5F5E3"],
        ]

    return [
        [percent(attention, min_value, max_value), "#D5F5E3"],
        [percent(alert, min_value, max_value), "#FCF3CF"],
        [percent(critical, min_value, max_value), "#FDEBD0"],
        [1, "#FADBD8"],
    ]


def metric_number(latest_state: Mapping[str, Any], *names: str) -> float | None:
    metrics = latest_state.get("metrics")
    metric_map = metrics if isinstance(metrics, Mapping) else {}

    for name in names:
        value = to_float(latest_state.get(name))

        if value is not None:
            return value

        value = to_float(metric_map.get(name))

        if value is not None:
            return value

    return None


def severity_score(latest_state: Mapping[str, Any], health_score: float | None) -> float | None:
    value = metric_number(latest_state, "severity_score", "severity")

    if value is not None:
        return value

    if health_score is None:
        return None

    return round(100.0 - health_score, 1)


def make_gauge_options(
    *,
    title: str,
    value: Any,
    unit: str,
    min_value: float,
    max_value: float,
    attention: float,
    alert: float,
    critical: float,
    decimals: int = 1,
    inverse: bool = False,
) -> dict[str, Any]:
    numeric_value = to_float(value)

    if numeric_value is None:
        display_value = min_value
        status = "offline"
        detail_formatter: Any = "SEM DADO"
    else:
        display_value = round(clamp(numeric_value, min_value, max_value), decimals)
        status = status_by_thresholds(
            display_value,
            attention=attention,
            alert=alert,
            critical=critical,
            inverse=inverse,
        )
        detail_formatter = "{value}" if not unit else f"{{value}} {unit}"

    pointer_color = COLORS[status]

    return {
        "backgroundColor": "transparent",
        "series": [
            {
                "type": "gauge",
                "min": min_value,
                "max": max_value,
                "startAngle": 205,
                "endAngle": -25,
                "splitNumber": 4,
                "center": ["50%", "58%"],
                "radius": "96%",
                "axisLine": {
                    "roundCap": True,
                    "lineStyle": {
                        "width": 16,
                        "color": axis_segments(
                            min_value=min_value,
                            max_value=max_value,
                            attention=attention,
                            alert=alert,
                            critical=critical,
                            inverse=inverse,
                        ),
                    },
                },
                "pointer": {
                    "show": True,
                    "length": "52%",
                    "width": 5,
                    "itemStyle": {"color": pointer_color},
                },
                "anchor": {
                    "show": True,
                    "showAbove": True,
                    "size": 10,
                    "itemStyle": {
                        "color": pointer_color,
                        "borderColor": "#FFFFFF",
                        "borderWidth": 2,
                    },
                },
                "axisTick": {
                    "distance": -20,
                    "length": 6,
                    "lineStyle": {"color": "#7F8C8D", "width": 1},
                },
                "splitLine": {
                    "distance": -24,
                    "length": 12,
                    "lineStyle": {"color": "#7F8C8D", "width": 2},
                },
                "axisLabel": {
                    "distance": 2,
                    "fontSize": 10,
                    "color": "#34495E",
                },
                "progress": {
                    "show": True,
                    "roundCap": True,
                    "width": 5,
                    "itemStyle": {"color": pointer_color},
                },
                "title": {
                    "show": True,
                    "offsetCenter": [0, "-78%"],
                    "fontSize": 16,
                    "fontWeight": "bold",
                    "color": "#1F2D3D",
                },
                "detail": {
                    "valueAnimation": True,
                    "offsetCenter": [0, "42%"],
                    "fontSize": 22,
                    "fontWeight": "normal",
                    "color": "#1F2D3D",
                    "formatter": detail_formatter,
                },
                "data": [{"value": display_value, "name": title}],
            }
        ],
        "graphic": [
            {
                "type": "text",
                "left": "center",
                "top": "83%",
                "style": {
                    "text": STATUS_LABELS[status],
                    "fill": pointer_color,
                    "fontSize": 12,
                    "fontWeight": "bold",
                },
            }
        ],
    }


def gauge_values(latest_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    health = metric_number(latest_state, "health_score")
    severity = severity_score(latest_state, health)
    values: list[dict[str, Any]] = []

    for definition in GAUGE_DEFINITIONS:
        names = definition["names"]
        value = severity if definition["key"] == "severity_score" else metric_number(latest_state, *names)

        values.append({**definition, "value": value})

    return values


def render_asset_gauges_echarts(latest_state: Mapping[str, Any], cols_per_row: int = 3) -> None:
    st.subheader("Painel visual de variação")

    try:
        from streamlit_echarts import st_echarts
    except Exception:  # pragma: no cover - depends on Streamlit component runtime.
        st.warning("Instale uma versão compatível de `streamlit-echarts` para habilitar os relógios industriais.")
        return

    cols_per_row = max(1, cols_per_row)
    gauges = gauge_values(latest_state)

    for row_start in range(0, len(gauges), cols_per_row):
        columns = st.columns(cols_per_row)

        for column, gauge in zip(columns, gauges[row_start : row_start + cols_per_row]):
            with column:
                options = make_gauge_options(
                    title=gauge["title"],
                    value=gauge["value"],
                    unit=gauge["unit"],
                    min_value=gauge["min_value"],
                    max_value=gauge["max_value"],
                    attention=gauge["attention"],
                    alert=gauge["alert"],
                    critical=gauge["critical"],
                    decimals=gauge["decimals"],
                    inverse=gauge["inverse"],
                )
                st_echarts(
                    options=options,
                    height="255px",
                    key=f"echarts_gauge_{gauge['key']}",
                )
