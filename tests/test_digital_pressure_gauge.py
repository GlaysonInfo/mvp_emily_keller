from src.dashboard.lubrication.digital_pressure_gauge import pressure_gauge_html, pressure_gauge_model


def test_pressure_gauge_model_scales_current_and_peak_pressure() -> None:
    outlet = {
        "outlet_id": "saida_graxa_04",
        "pressure_bar": 146.5,
        "peak_pressure_bar": 181.2,
        "status": "high_pressure_slow_decay",
        "severity": "ALERTA",
        "pulse_detected": True,
    }

    model = pressure_gauge_model(outlet, sensor_range_bar=250)

    assert model["label"] == "Saída de Graxa 04"
    assert model["pressure_text"] == "146.5"
    assert model["peak_text"] == "181.2"
    assert model["severity_class"] == "alert"
    assert model["percent"] == 58.6
    assert model["peak_percent"] == 72.5
    assert model["pulse_text"] == "Pulso OK"


def test_pressure_gauge_html_contains_lcd_display_data() -> None:
    outlet = {
        "outlet_id": "saida_graxa_03",
        "pressure_bar": 7.8,
        "peak_pressure_bar": 9.2,
        "status": "low_pressure",
        "severity": "ATENÇÃO",
        "pulse_detected": True,
    }

    html = pressure_gauge_html(outlet, sensor_range_bar=250)

    assert "pressure-gauge-card pressure-gauge-attention" in html
    assert "Saída de Graxa 03" in html
    assert "7.8" in html
    assert "Pico 9.2 bar" in html
    assert "Baixa pressão" in html
