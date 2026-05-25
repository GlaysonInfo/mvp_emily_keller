from __future__ import annotations

METRIC_LABELS = {
    "rpm": "RPM",
    "vibration_rms_mm_s": "Vibração RMS",
    "temperature_c": "Temperatura",
    "ultrasound_db": "Ultrassom",
    "kurtosis_index": "Kurtosis",
    "crest_factor_index": "Crest Factor",
    "vibration_peak_g": "Pico de vibração",
    "hourmeter_h": "Horímetro",
    "health_score": "Health Score",
    "severity_score": "Severity Score",
}

METRIC_UNITS = {
    "rpm": "rpm",
    "vibration_rms_mm_s": "mm/s",
    "temperature_c": "°C",
    "ultrasound_db": "dB",
    "kurtosis_index": "index",
    "crest_factor_index": "index",
    "vibration_peak_g": "g",
    "hourmeter_h": "h",
    "health_score": "",
    "severity_score": "",
}

METRIC_DIRECTIONS = {
    "vibration_rms_mm_s": "higher_is_worse",
    "temperature_c": "higher_is_worse",
    "ultrasound_db": "higher_is_worse",
    "kurtosis_index": "higher_is_worse",
    "crest_factor_index": "higher_is_worse",
    "vibration_peak_g": "higher_is_worse",
    "severity_score": "higher_is_worse",
    "health_score": "lower_is_worse",
    "rpm": "range",
    "hourmeter_h": "accumulator",
}

ANALYSIS_METRICS = [
    "rpm",
    "vibration_rms_mm_s",
    "temperature_c",
    "ultrasound_db",
    "kurtosis_index",
    "crest_factor_index",
    "vibration_peak_g",
    "health_score",
    "severity_score",
]


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


def metric_unit(metric: str) -> str:
    return METRIC_UNITS.get(metric, "")


def metric_direction(metric: str) -> str:
    return METRIC_DIRECTIONS.get(metric, "higher_is_worse")
