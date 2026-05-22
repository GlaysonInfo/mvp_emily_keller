from __future__ import annotations

OPCUA_TAGS: tuple[str, ...] = (
    "rpm",
    "vibration_rms_mm_s",
    "vibration_peak_g",
    "temperature_c",
    "ultrasound_db",
    "horimeter_h",
    "kurtosis",
    "crest_factor",
    "health_score",
    "severity",
    "failure_mode",
)

EXPECTED_OPCUA_TAGS: frozenset[str] = frozenset(OPCUA_TAGS)

NUMERIC_METRIC_TAGS: frozenset[str] = frozenset(
    {
        "rpm",
        "vibration_rms_mm_s",
        "vibration_peak_g",
        "temperature_c",
        "ultrasound_db",
        "horimeter_h",
        "kurtosis",
        "crest_factor",
        "health_score",
    }
)

UNIT_BY_TAG: dict[str, str] = {
    "rpm": "rpm",
    "vibration_rms_mm_s": "mm/s",
    "vibration_peak_g": "g",
    "temperature_c": "C",
    "ultrasound_db": "dB",
    "horimeter_h": "h",
    "kurtosis": "index",
    "crest_factor": "index",
    "health_score": "score",
}

