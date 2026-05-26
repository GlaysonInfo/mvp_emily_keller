from __future__ import annotations

from html import escape

import streamlit as st

from .lubrication_labels import outlet_label, status_label


SEVERITY_CLASS = {
    "NORMAL": "normal",
    "ATENÇÃO": "attention",
    "ATENCAO": "attention",
    "ALERTA": "alert",
    "CRÍTICO": "critical",
    "CRITICO": "critical",
}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in [None, ""]:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt_number(value: object, decimals: int = 1) -> str:
    if value in [None, ""]:
        return "--"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def _severity_class(outlet: dict) -> str:
    severity = str(outlet.get("severity") or "").upper()
    return SEVERITY_CLASS.get(severity, "normal")


def pressure_gauge_model(outlet: dict, sensor_range_bar: float = 250) -> dict[str, object]:
    pressure = _to_float(outlet.get("pressure_bar"))
    peak = _to_float(outlet.get("peak_pressure_bar"))
    max_range = max(float(sensor_range_bar or 250), 1.0)
    percent = max(0.0, min((pressure / max_range) * 100, 100.0))
    peak_percent = max(0.0, min((peak / max_range) * 100, 100.0))

    return {
        "label": outlet_label(outlet.get("outlet_id", "")),
        "pressure": pressure,
        "pressure_text": _fmt_number(outlet.get("pressure_bar")),
        "peak_text": _fmt_number(outlet.get("peak_pressure_bar")),
        "status_text": status_label(outlet.get("status")),
        "severity": outlet.get("severity") or "NORMAL",
        "severity_class": _severity_class(outlet),
        "percent": round(percent, 1),
        "peak_percent": round(peak_percent, 1),
        "range_text": f"0-{_fmt_number(sensor_range_bar, 0)} bar",
        "pulse_text": "Pulso OK" if outlet.get("pulse_detected") else "Sem pulso",
    }


def pressure_gauge_html(outlet: dict, sensor_range_bar: float = 250) -> str:
    model = pressure_gauge_model(outlet, sensor_range_bar)

    label = escape(str(model["label"]))
    pressure_text = escape(str(model["pressure_text"]))
    peak_text = escape(str(model["peak_text"]))
    status_text = escape(str(model["status_text"]))
    severity = escape(str(model["severity"]))
    severity_class = escape(str(model["severity_class"]))
    range_text = escape(str(model["range_text"]))
    pulse_text = escape(str(model["pulse_text"]))
    percent = model["percent"]
    peak_percent = model["peak_percent"]

    return f"""
    <div class="pressure-gauge-card pressure-gauge-{severity_class}">
      <div class="pressure-gauge-head">
        <div class="pressure-gauge-title">{label}</div>
        <div class="pressure-gauge-range">{range_text}</div>
      </div>
      <div class="pressure-gauge-body">
        <div class="pressure-gauge-brand">PRESSÃO</div>
        <div class="pressure-gauge-display">
          <span class="pressure-gauge-digits">{pressure_text}</span>
          <span class="pressure-gauge-unit">bar</span>
        </div>
        <div class="pressure-gauge-scale">
          <div class="pressure-gauge-fill" style="width: {percent}%"></div>
          <div class="pressure-gauge-peak" style="left: {peak_percent}%"></div>
        </div>
        <div class="pressure-gauge-meta">
          <span>Pico {peak_text} bar</span>
          <span>{pulse_text}</span>
        </div>
      </div>
      <div class="pressure-gauge-status">
        <span>{severity}</span>
        <span>{status_text}</span>
      </div>
    </div>
    """


def pressure_gauge_styles() -> str:
    return """
    <style>
    .pressure-gauge-grid-note {
        margin-top: 0.15rem;
        margin-bottom: 0.75rem;
        color: #6b7280;
        font-size: 0.88rem;
    }
    .pressure-gauge-card {
        width: 100%;
        min-height: 228px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background: #f8fafc;
        padding: 0.7rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }
    .pressure-gauge-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.5rem;
        min-height: 40px;
    }
    .pressure-gauge-title {
        color: #111827;
        font-size: 0.92rem;
        font-weight: 800;
        line-height: 1.15;
    }
    .pressure-gauge-range {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .pressure-gauge-body {
        margin: 0.35rem auto 0.55rem;
        border: 6px solid #1f2937;
        border-radius: 8px;
        background: #e5e7eb;
        padding: 0.55rem;
    }
    .pressure-gauge-brand {
        color: #475569;
        font-size: 0.7rem;
        font-weight: 900;
        letter-spacing: 0;
        margin-bottom: 0.25rem;
    }
    .pressure-gauge-display {
        height: 58px;
        border: 2px solid #9ca3af;
        border-radius: 6px;
        background: #dbe8d4;
        color: #111827;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.35rem;
        padding: 0 0.55rem;
        font-family: "Consolas", "Courier New", monospace;
        overflow: hidden;
    }
    .pressure-gauge-digits {
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
    }
    .pressure-gauge-unit {
        align-self: flex-end;
        padding-bottom: 0.65rem;
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    .pressure-gauge-scale {
        position: relative;
        height: 12px;
        margin-top: 0.55rem;
        border-radius: 6px;
        background: #cbd5e1;
        overflow: hidden;
    }
    .pressure-gauge-fill {
        height: 100%;
        border-radius: 6px;
        background: #16a34a;
    }
    .pressure-gauge-peak {
        position: absolute;
        top: -2px;
        width: 3px;
        height: 16px;
        border-radius: 2px;
        background: #111827;
    }
    .pressure-gauge-meta,
    .pressure-gauge-status {
        display: flex;
        justify-content: space-between;
        gap: 0.45rem;
        color: #475569;
        font-size: 0.76rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .pressure-gauge-meta {
        margin-top: 0.45rem;
    }
    .pressure-gauge-status {
        min-height: 34px;
        align-items: center;
        border-top: 1px solid #d1d5db;
        padding-top: 0.45rem;
        color: #111827;
    }
    .pressure-gauge-attention .pressure-gauge-fill {
        background: #f59e0b;
    }
    .pressure-gauge-alert .pressure-gauge-fill {
        background: #ea580c;
    }
    .pressure-gauge-critical .pressure-gauge-fill {
        background: #dc2626;
    }
    .pressure-gauge-attention {
        border-color: #f59e0b;
    }
    .pressure-gauge-alert {
        border-color: #ea580c;
    }
    .pressure-gauge-critical {
        border-color: #dc2626;
    }
    </style>
    """


def render_pressure_gauges(state_or_cycle: dict, sensor_range_bar: float = 250) -> None:
    outlets = state_or_cycle.get("outlets", [])
    if not outlets:
        st.info("Nenhuma saída de graxa disponível para exibir no manômetro digital.")
        return

    st.markdown(pressure_gauge_styles(), unsafe_allow_html=True)
    st.markdown(
        '<div class="pressure-gauge-grid-note">Leitura digital por saída de graxa.</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(min(len(outlets), 4))
    for index, outlet in enumerate(outlets):
        with columns[index % len(columns)]:
            st.markdown(pressure_gauge_html(outlet, sensor_range_bar), unsafe_allow_html=True)
