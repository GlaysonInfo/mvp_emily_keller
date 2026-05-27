
from __future__ import annotations

import pandas as pd
import streamlit as st

from .field_config_store import load_field_config, save_field_config, validate_field_config


def render_lubrication_field_config_page(path: str = "config/field_lubrication_config.json") -> None:
    st.header("Configuração de Campo — Sistema de Lubrificação")
    st.caption("Gateway IO-Link, sensores por saída, baseline, curva de pressão, relatórios e segurança.")

    try:
        config = load_field_config(path)
    except FileNotFoundError:
        config = load_field_config("config/field_lubrication_config.example.json")
        st.warning("Configuração real não encontrada. Carregado exemplo.")

    issues = validate_field_config(config)

    if not issues:
        st.success("Configuração de campo consistente para piloto.")
    else:
        errors = [i for i in issues if i["level"] == "ERRO"]
        warnings = [i for i in issues if i["level"] == "ATENÇÃO"]
        if errors:
            st.error(f"{len(errors)} erro(s) crítico(s) na configuração de campo.")
        elif warnings:
            st.warning(f"{len(warnings)} ponto(s) a revisar na configuração de campo.")

        with st.expander("Checklist da configuração de campo", expanded=True):
            st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)

    tab_general, tab_gateway, tab_outlets, tab_links, tab_rules, tab_security, tab_report = st.tabs(
        [
            "Sistema",
            "Gateway IO-Link",
            "Saídas/Sensores",
            "Vínculos",
            "Regras e Baseline",
            "Segurança",
            "Relatórios",
        ]
    )

    with tab_general:
        st.subheader("Sistema de lubrificação")
        system = config.setdefault("lubrication_system", {})
        client = config.setdefault("client", {})
        plant = config.setdefault("plant", {})

        client["tenant_id"] = st.text_input("Tenant ID", client.get("tenant_id", "cliente_demo"))
        client["company_name"] = st.text_input("Cliente", client.get("company_name", "Cliente Demonstração"))
        plant["plant_id"] = st.text_input("Plant ID", plant.get("plant_id", "lab_virtual"))
        plant["plant_name"] = st.text_input("Planta", plant.get("plant_name", "Piloto"))

        system["asset_id"] = st.text_input("Asset ID", system.get("asset_id", "sistema_lubrificacao_01"))
        system["asset_name"] = st.text_input("Nome do sistema", system.get("asset_name", "Sistema de Lubrificação Centralizada"))
        system["expected_operating_pressure_bar"] = st.number_input(
            "Pressão operacional esperada (bar)",
            min_value=0.0,
            value=float(system.get("expected_operating_pressure_bar", 100)),
        )
        system["recommended_sensor_range_bar"] = st.number_input(
            "Faixa recomendada do sensor (bar)",
            min_value=0.0,
            value=float(system.get("recommended_sensor_range_bar", 250)),
        )
        system["physical_gauges_kept"] = st.checkbox(
            "Manômetros físicos mantidos no piloto",
            value=bool(system.get("physical_gauges_kept", True)),
        )

    with tab_gateway:
        st.subheader("Gateway IO-Link / Bridge")
        gateway = config.setdefault("gateway", {})

        gateway["source_id"] = st.text_input("Source ID", gateway.get("source_id", "grease_gateway_01"))
        gateway["name"] = st.text_input("Nome", gateway.get("name", "Gateway IO-Link Lubrificação 01"))
        gateway["manufacturer"] = st.text_input("Fabricante", gateway.get("manufacturer", ""))
        gateway["model"] = st.text_input("Modelo", gateway.get("model", ""))
        gateway["protocol"] = st.selectbox(
            "Protocolo",
            ["http_json", "mqtt", "opcua", "modbus_tcp", "manual_csv"],
            index=["http_json", "mqtt", "opcua", "modbus_tcp", "manual_csv"].index(gateway.get("protocol", "http_json"))
            if gateway.get("protocol", "http_json") in ["http_json", "mqtt", "opcua", "modbus_tcp", "manual_csv"] else 0,
        )
        gateway["endpoint"] = st.text_input("Endpoint do gateway", gateway.get("endpoint", ""))
        gateway["read_timeout_sec"] = st.number_input(
            "Timeout de leitura (s)",
            min_value=1,
            value=int(gateway.get("read_timeout_sec", 5)),
        )

    with tab_outlets:
        st.subheader("Saídas de graxa e sensores")
        outlets = config.setdefault("outlets", [])

        rows = []
        for outlet in outlets:
            rows.append({
                "enabled": outlet.get("enabled", True),
                "outlet_id": outlet.get("outlet_id"),
                "name": outlet.get("name"),
                "gateway_port": outlet.get("gateway_port"),
                "gateway_tag_pressure": outlet.get("gateway_tag_pressure"),
                "sensor_id": outlet.get("sensor_id"),
                "sensor_model": outlet.get("sensor_model"),
                "sensor_range_bar": outlet.get("sensor_range_bar"),
                "process_connection": outlet.get("process_connection"),
                "physical_gauge_present": outlet.get("physical_gauge_present", True),
            })

        edited = st.data_editor(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
        )

        config["outlets"] = edited.to_dict(orient="records")

    with tab_links:
        st.subheader("Vínculos entre equipamento e saída de graxa")
        st.caption("Use para correlacionar resposta do motor, dose em gramas e saída de lubrificação.")
        links = config.setdefault("equipment_links", [])

        rows = []
        for link in links:
            rows.append({
                "enabled": link.get("enabled", True),
                "link_id": link.get("link_id"),
                "asset_id": link.get("asset_id"),
                "asset_name": link.get("asset_name"),
                "outlet_id": link.get("outlet_id"),
                "outlet_name": link.get("outlet_name"),
                "grease_type": link.get("grease_type"),
                "target_grease_g_per_cycle": link.get("target_grease_g_per_cycle"),
                "cycle_interval_h": link.get("cycle_interval_h"),
                "baseline_status": link.get("baseline_status"),
                "objective": link.get("objective"),
            })

        edited_links = st.data_editor(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
        )

        config["equipment_links"] = edited_links.to_dict(orient="records")

    with tab_rules:
        st.subheader("Regras iniciais e baseline")
        rules = config.setdefault("rules", {})
        c1, c2, c3 = st.columns(3)
        rules["low_pressure_bar"] = c1.number_input("Baixa pressão até (bar)", value=float(rules.get("low_pressure_bar", 10)))
        rules["high_pressure_bar"] = c2.number_input("Alta pressão a partir de (bar)", value=float(rules.get("high_pressure_bar", 160)))
        rules["critical_pressure_bar"] = c3.number_input("Crítico a partir de (bar)", value=float(rules.get("critical_pressure_bar", 220)))

        c4, c5, c6 = st.columns(3)
        rules["max_rise_time_sec"] = c4.number_input("Subida lenta acima de (s)", value=float(rules.get("max_rise_time_sec", 10)))
        rules["max_decay_time_sec"] = c5.number_input("Alívio lento acima de (s)", value=float(rules.get("max_decay_time_sec", 15)))
        rules["pulse_min_delta_bar"] = c6.number_input("Delta mínimo para pulso (bar)", value=float(rules.get("pulse_min_delta_bar", 8)))

        c7, c8, c9 = st.columns(3)
        rules["min_samples_for_baseline"] = c7.number_input("Amostras mínimas para baseline", value=int(rules.get("min_samples_for_baseline", 20)))
        rules["baseline_warning_pct"] = c8.number_input("Desvio atenção baseline (%)", value=float(rules.get("baseline_warning_pct", 30)))
        rules["baseline_alert_pct"] = c9.number_input("Desvio alerta baseline (%)", value=float(rules.get("baseline_alert_pct", 50)))

    with tab_security:
        st.subheader("Segurança do endpoint")
        ingest = config.setdefault("ingest_api", {})
        ingest["endpoint"] = st.text_input(
            "Endpoint /grease/ingest",
            ingest.get("endpoint", "https://sentinelaindustrial.com.br/grease/ingest"),
        )
        ingest["token_env"] = st.text_input("Variável do token", ingest.get("token_env", "GREASE_INGEST_TOKEN"))
        ingest["require_token"] = st.checkbox("Exigir token no campo", value=bool(ingest.get("require_token", True)))

        allowed_ips = "\n".join(ingest.get("allowed_source_ips", []))
        allowed_ips_text = st.text_area("IPs permitidos, um por linha", value=allowed_ips)
        ingest["allowed_source_ips"] = [x.strip() for x in allowed_ips_text.splitlines() if x.strip()]

    with tab_report:
        st.subheader("Relatórios")
        reporting = config.setdefault("reporting", {})
        reporting["default_period_hours"] = st.number_input("Período padrão do relatório (h)", value=int(reporting.get("default_period_hours", 24)))
        reporting["include_raw_curve"] = st.checkbox("Incluir curva bruta quando disponível", value=bool(reporting.get("include_raw_curve", True)))
        reporting["include_baseline"] = st.checkbox("Incluir baseline por saída", value=bool(reporting.get("include_baseline", True)))
        reporting["include_recommendations"] = st.checkbox("Incluir recomendações da IA", value=bool(reporting.get("include_recommendations", True)))

    if st.button("Salvar configuração de campo", type="primary", use_container_width=True):
        save_field_config(config, path)
        st.success("Configuração de campo salva.")
        st.rerun()
