from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from dashboard.alert_parameter_presets import get_metric_label, get_parameter_preset, validate_parameter_rule
    from dashboard.config_consistency_ui import render_config_consistency_panel
    from dashboard.config_repository import ConfigRepository
    from dashboard.config_validation_ui import render_validation_panel
    from dashboard.hmi.hmi_sidebar import set_operator_page_for_route
    from dashboard.navigation import render_navigation_icon
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alert_parameter_presets import get_metric_label, get_parameter_preset, validate_parameter_rule
    from src.dashboard.config_consistency_ui import render_config_consistency_panel
    from src.dashboard.config_repository import ConfigRepository
    from src.dashboard.config_validation_ui import render_validation_panel
    from src.dashboard.hmi.hmi_sidebar import set_operator_page_for_route
    from src.dashboard.navigation import render_navigation_icon


PROTOCOLS = [
    "Interno",
    "OPC UA via HTTPS",
    "MQTT",
    "HTTP/HTTPS API",
    "Modbus TCP",
    "CSV",
    "Manual",
]
SOURCE_STATUS = ["Ativa", "Configurada", "Disponível", "Aguardando credencial", "Falha", "Inativa"]
ASSET_TYPES = [
    "Motor elétrico",
    "Bomba centrífuga",
    "Compressor",
    "Redutor",
    "Ventilador",
    "Exaustor",
    "Transportador",
    "Misturador",
    "Outro",
]
CRITICALITIES = ["Baixa", "Média", "Alta", "Crítica"]
METRICS = [
    "rpm",
    "vibration_rms_mm_s",
    "temperature_c",
    "ultrasound_db",
    "kurtosis_index",
    "crest_factor_index",
    "vibration_peak_g",
    "hourmeter_h",
    "health_score",
    "severity_score",
]
PAGE_TARGET_KEY = "dashboard_page_target"
SELECTED_ASSET_ID_KEY = "selected_asset_id"
PENDING_CONDITION_ASSET_KEY = "condition_pending_selected_asset_id"


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    return str(value)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _index(options: list[str], value: Any, default: int = 0) -> int:
    try:
        return options.index(str(value))
    except ValueError:
        return default


def _save(repo: ConfigRepository, data: dict[str, Any], message: str) -> None:
    repo.save(data)
    try:
        from dashboard.auth import audit
    except ImportError:  # pragma: no cover - execução a partir da raiz do repo
        try:
            from src.dashboard.auth import audit
        except ImportError:
            audit = None
    if audit is not None:
        audit.record("config.save", target=message)
    st.success(message)
    st.rerun()


def _replace_by_key(items: list[dict[str, Any]], key: str, value: str, new_item: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in items if item.get(key) != value] + [new_item]


def _render_table(items: list[dict[str, Any]], columns: list[str]) -> None:
    if not items:
        st.info("Nenhum registro cadastrado.")
        return

    rows = [{column: item.get(column, "") for column in columns} for item in items]
    st.dataframe(rows, width="stretch", hide_index=True)


def _navigate_to(route: str, *, asset_id: str | None = None) -> None:
    if asset_id:
        st.session_state[SELECTED_ASSET_ID_KEY] = asset_id
        st.session_state[PENDING_CONDITION_ASSET_KEY] = asset_id
    st.session_state[PAGE_TARGET_KEY] = route
    set_operator_page_for_route(route)
    st.rerun()


def _render_asset_navigation_table(assets: list[dict[str, Any]]) -> None:
    if not assets:
        st.info("Nenhum registro cadastrado.")
        return

    header = st.columns([1.05, 1.7, 1.2, 1.05, 0.8, 1.05, 0.8])
    header[0].caption("asset_id")
    header[1].caption("asset_name")
    header[2].caption("asset_type")
    header[3].caption("area")
    header[4].caption("status")
    header[5].caption("source_id")
    header[6].caption("Ações")

    for asset in assets:
        asset_id = str(asset.get("asset_id") or "").strip()
        if not asset_id:
            continue
        row = st.columns([1.05, 1.7, 1.2, 1.05, 0.8, 1.05, 0.8])
        row[0].write(asset_id)
        row[1].write(_text(asset.get("asset_name"), "-"))
        row[2].write(_text(asset.get("asset_type"), "-"))
        row[3].write(_text(asset.get("area"), "-"))
        row[4].write(_text(asset.get("status"), "Ativo"))
        row[5].write(_text(asset.get("source_id"), "-"))
        action_cols = row[6].columns(3)
        with action_cols[0]:
            render_navigation_icon(
                "Monitoramento de Equipamentos",
                label="Monitorar ativo",
                icon=":material/monitoring:",
                asset_id=asset_id,
            )
        with action_cols[1]:
            render_navigation_icon(
                "Detalhe do Ativo",
                label="Abrir detalhe do ativo",
                icon=":material/manage_search:",
                asset_id=asset_id,
            )
        with action_cols[2]:
            render_navigation_icon(
                "Alertas e Eventos",
                label="Ver alertas do ativo",
                icon=":material/notifications_active:",
                asset_id=asset_id,
            )


def render_config_page(config_path: str | None = None) -> None:
    repo = ConfigRepository(config_path)
    data = repo.load()

    st.subheader("Configurações")
    st.caption(
        "Implantação técnica: cliente, planta, fontes de dados, ativos, sinais, parâmetros e alertas."
    )

    render_config_consistency_panel(data)

    tabs = st.tabs(
        [
            "Cliente",
            "Planta",
            "Fontes de Dados",
            "Ativos",
            "Mapeamento de Sinais",
            "Parâmetros e Alertas",
        ]
    )

    with tabs[0]:
        _render_client_tab(repo, data)
    with tabs[1]:
        _render_plant_tab(repo, data)
    with tabs[2]:
        _render_sources_tab(repo, data)
    with tabs[3]:
        _render_assets_tab(repo, data)
    with tabs[4]:
        _render_signal_map_tab(repo, data)
    with tabs[5]:
        _render_parameters_tab(repo, data)


def _render_client_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Cadastro do Cliente")
    client = data.get("client", {})

    with st.form("config_client_form"):
        left, right = st.columns(2)
        current_tenant_id = _text(client.get("tenant_id"), "cliente_demo")

        with left:
            tenant_id = st.text_input(
                "Tenant ID técnico",
                current_tenant_id,
                disabled=bool(current_tenant_id),
                help="Chave técnica estável. Edite o nome da empresa, não o tenant_id, depois que houver dados gravados.",
            )
            company_name = st.text_input("Nome da empresa", _text(client.get("company_name")))
            cnpj = st.text_input("CNPJ / identificador", _text(client.get("cnpj")))
            segment = st.text_input("Atividade / segmento", _text(client.get("segment")))

        with right:
            responsible_name = st.text_input("Responsável técnico", _text(client.get("responsible_name")))
            responsible_email = st.text_input("E-mail", _text(client.get("responsible_email")))
            responsible_phone = st.text_input("Telefone", _text(client.get("responsible_phone")))
            timezone = st.text_input("Fuso horário", _text(client.get("timezone"), "America/Sao_Paulo"))

        modes = ["Demonstração", "Piloto", "Produção"]
        environment_mode = st.selectbox(
            "Ambiente",
            modes,
            index=_index(modes, client.get("environment_mode"), 0),
        )

        if st.form_submit_button("Salvar cliente", type="primary"):
            data["client"] = {
                **client,
                "tenant_id": current_tenant_id or tenant_id.strip() or "cliente_demo",
                "company_name": company_name.strip(),
                "cnpj": cnpj.strip(),
                "segment": segment.strip(),
                "responsible_name": responsible_name.strip(),
                "responsible_email": responsible_email.strip(),
                "responsible_phone": responsible_phone.strip(),
                "timezone": timezone.strip() or "America/Sao_Paulo",
                "environment_mode": environment_mode,
            }
            _save(repo, data, "Cliente salvo com sucesso.")


def _render_plant_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Cadastro da Planta")
    plant = data.get("plant", {})
    tenant_id = data.get("client", {}).get("tenant_id", plant.get("tenant_id", "cliente_demo"))

    with st.form("config_plant_form"):
        left, right = st.columns(2)
        current_plant_id = _text(plant.get("plant_id"), "lab_virtual")

        with left:
            plant_id = st.text_input(
                "Plant ID técnico",
                current_plant_id,
                disabled=bool(current_plant_id),
                help="Chave técnica estável da planta. Edite o nome da planta para exibição ao cliente.",
            )
            plant_name = st.text_input("Nome da planta", _text(plant.get("plant_name"), "Bancada Virtual"))
            country = st.text_input("País", _text(plant.get("country"), "Brasil"))
            state = st.text_input("Estado", _text(plant.get("state")))

        with right:
            city = st.text_input("Cidade", _text(plant.get("city")))
            address = st.text_input("Endereço", _text(plant.get("address")))
            latitude = st.text_input("Latitude", _text(plant.get("latitude")))
            longitude = st.text_input("Longitude", _text(plant.get("longitude")))

        operation_regime = st.text_input("Regime operacional", _text(plant.get("operation_regime"), "24x7"))
        environment_conditions = st.text_area(
            "Condições ambientais e operacionais",
            _text(plant.get("environment_conditions")),
        )

        if st.form_submit_button("Salvar planta", type="primary"):
            data["plant"] = {
                "tenant_id": tenant_id,
                "plant_id": current_plant_id or plant_id.strip() or "lab_virtual",
                "plant_name": plant_name.strip() or "Bancada Virtual",
                "country": country.strip(),
                "state": state.strip(),
                "city": city.strip(),
                "address": address.strip(),
                "latitude": latitude.strip(),
                "longitude": longitude.strip(),
                "operation_regime": operation_regime.strip(),
                "environment_conditions": environment_conditions.strip(),
            }
            _save(repo, data, "Planta salva com sucesso.")


def _render_sources_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Fontes de Dados / Gateways / Conectores")
    st.info(
        "O ativo físico é o objeto monitorado. A comunicação fica na Fonte de Dados: "
        "gateway, CLP, OPC UA Server, broker MQTT, API, CSV ou bancada virtual."
    )

    sources = repo.data_sources(data)
    _render_table(
        sources,
        [
            "source_id",
            "source_name",
            "source_type",
            "protocol",
            "status",
            "polling_interval_sec",
            "history_interval_sec",
            "credential_ref",
        ],
    )

    with st.expander("Cadastrar ou atualizar fonte de dados"):
        source_ids = [source.get("source_id") for source in sources if source.get("source_id")]
        selected = st.selectbox("Fonte existente", ["Nova fonte"] + source_ids)
        current = next((source for source in sources if source.get("source_id") == selected), {})

        with st.form("config_source_form"):
            left, right = st.columns(2)
            current_source_id = _text(current.get("source_id"))
            source_id_locked = bool(current_source_id)

            with left:
                source_id = st.text_input(
                    "Source ID técnico",
                    current_source_id,
                    disabled=source_id_locked,
                    help="Chave técnica da fonte. Para trocar a chave, cadastre uma nova fonte e remapeie os ativos.",
                )
                source_name = st.text_input("Nome da fonte", _text(current.get("source_name")))
                source_type = st.text_input("Tipo", _text(current.get("source_type"), "Gateway Edge"))
                protocol = st.selectbox(
                    "Protocolo",
                    PROTOCOLS,
                    index=_index(PROTOCOLS, current.get("protocol"), 1),
                )

            with right:
                endpoint = st.text_input("Endpoint / broker / URL / caminho", _text(current.get("endpoint")))
                polling_interval_sec = st.number_input(
                    "Frequência de coleta em segundos",
                    min_value=0,
                    value=_int(current.get("polling_interval_sec"), 5),
                )
                history_interval_sec = st.number_input(
                    "Frequência de histórico em segundos",
                    min_value=0,
                    value=_int(current.get("history_interval_sec"), 60),
                )
                status = st.selectbox(
                    "Status",
                    SOURCE_STATUS,
                    index=_index(SOURCE_STATUS, current.get("status"), 1),
                )

            credential_ref = st.text_input(
                "Referência segura da credencial",
                _text(current.get("credential_ref")),
                help="Não salve senha em texto puro. Use AWS Secrets Manager, variável de ambiente ou cofre equivalente.",
            )
            description = st.text_area("Descrição", _text(current.get("description")))

            if st.form_submit_button("Salvar fonte de dados", type="primary"):
                source_identity = current_source_id or source_id.strip()
                if not source_identity:
                    st.error("Informe o Source ID.")
                else:
                    new_source = {
                        "source_id": source_identity,
                        "source_name": source_name.strip(),
                        "source_type": source_type.strip(),
                        "protocol": protocol,
                        "endpoint": endpoint.strip(),
                        "polling_interval_sec": polling_interval_sec,
                        "history_interval_sec": history_interval_sec,
                        "status": status,
                        "credential_ref": credential_ref.strip(),
                        "description": description.strip(),
                    }
                    data["data_sources"] = _replace_by_key(sources, "source_id", source_identity, new_source)
                    _save(repo, data, "Fonte de dados salva com sucesso.")

    st.divider()
    st.markdown("#### Validação da fonte")

    source_ids = [source.get("source_id") for source in sources if source.get("source_id")]

    if not source_ids:
        st.info("Cadastre uma fonte de dados para habilitar validações reais.")
        return

    selected_source_id = st.selectbox(
        "Fonte para validação",
        source_ids,
        key="selected_source_validation",
    )
    selected_source = next(
        (source for source in sources if source.get("source_id") == selected_source_id),
        None,
    )

    asset_ids = [asset.get("asset_id") for asset in repo.assets(data) if asset.get("asset_id")]
    selected_asset_for_validation = st.selectbox(
        "Ativo para validar tags",
        ["Todos"] + asset_ids,
        key="selected_asset_validation",
    )

    render_validation_panel(
        data=data,
        selected_source=selected_source,
        selected_asset_id=None if selected_asset_for_validation == "Todos" else selected_asset_for_validation,
    )


def _render_assets_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Ativos Monitorados")

    assets = repo.assets(data)
    sources = repo.data_sources(data)
    source_ids = [source.get("source_id") for source in sources if source.get("source_id")]

    _render_asset_navigation_table(assets)

    with st.expander("Cadastrar ou atualizar ativo"):
        asset_ids = [asset.get("asset_id") for asset in assets if asset.get("asset_id")]
        selected = st.selectbox("Ativo existente", ["Novo ativo"] + asset_ids)
        current = next((asset for asset in assets if asset.get("asset_id") == selected), {})

        with st.form("config_asset_form"):
            left, right = st.columns(2)
            current_asset_id = _text(current.get("asset_id"))
            asset_id_locked = bool(current_asset_id)

            with left:
                asset_id = st.text_input(
                    "Asset ID técnico",
                    current_asset_id,
                    disabled=asset_id_locked,
                    help="Chave técnica do ativo. Para trocar a chave, cadastre um novo ativo e migre histórico/alertas.",
                )
                asset_name = st.text_input("Nome operacional", _text(current.get("asset_name")))
                asset_type = st.selectbox(
                    "Tipo de ativo",
                    ASSET_TYPES,
                    index=_index(ASSET_TYPES, current.get("asset_type"), 0),
                )
                area = st.text_input("Área", _text(current.get("area")))

            with right:
                criticality = st.selectbox(
                    "Criticidade",
                    CRITICALITIES,
                    index=_index(CRITICALITIES, current.get("criticality"), 2),
                )
                source_options = source_ids or [""]
                source_id = st.selectbox(
                    "Fonte de dados principal",
                    source_options,
                    index=_index(source_options, current.get("source_id"), 0),
                )
                manufacturer = st.text_input("Fabricante", _text(current.get("manufacturer")))
                model = st.text_input("Modelo", _text(current.get("model")))

            col1, col2, col3, col4 = st.columns(4)
            serial_number = col1.text_input("Número de série", _text(current.get("serial_number")))
            nominal_rpm = col2.number_input("RPM nominal", min_value=0, value=_int(current.get("nominal_rpm")))
            power_kw = col3.text_input("Potência kW/cv", _text(current.get("power_kw")))
            voltage_v = col4.text_input("Tensão V", _text(current.get("voltage_v")))

            current_a = st.text_input("Corrente nominal A", _text(current.get("current_a")))
            baseline_status = st.text_area(
                "Marco zero / condição inicial resumida",
                _text(current.get("baseline_status")),
            )
            status_options = ["Ativo", "Inativo", "Em implantação"]
            status = st.selectbox(
                "Status cadastral",
                status_options,
                index=_index(status_options, current.get("status"), 0),
            )

            if st.form_submit_button("Salvar ativo", type="primary"):
                asset_identity = current_asset_id or asset_id.strip()
                if not asset_identity:
                    st.error("Informe o Asset ID.")
                else:
                    client = data.get("client", {})
                    plant = data.get("plant", {})
                    new_asset = {
                        "tenant_id": client.get("tenant_id", "cliente_demo"),
                        "plant_id": plant.get("plant_id", "lab_virtual"),
                        "asset_id": asset_identity,
                        "asset_name": asset_name.strip(),
                        "asset_type": asset_type,
                        "area": area.strip(),
                        "criticality": criticality,
                        "manufacturer": manufacturer.strip(),
                        "model": model.strip(),
                        "serial_number": serial_number.strip(),
                        "nominal_rpm": nominal_rpm,
                        "power_kw": power_kw.strip(),
                        "voltage_v": voltage_v.strip(),
                        "current_a": current_a.strip(),
                        "source_id": source_id,
                        "baseline_status": baseline_status.strip(),
                        "status": status,
                    }
                    data["assets"] = _replace_by_key(assets, "asset_id", asset_identity, new_asset)
                    _save(repo, data, "Ativo salvo com sucesso.")


def _render_signal_map_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Mapeamento de Sinais")
    st.caption("Vincula ativo, fonte de dados e tag externa ao modelo interno padronizado.")

    signal_map = repo.signal_map(data)
    assets = [asset.get("asset_id") for asset in repo.assets(data) if asset.get("asset_id")]
    sources = [source.get("source_id") for source in repo.data_sources(data) if source.get("source_id")]

    _render_table(
        signal_map,
        ["asset_id", "source_id", "metric", "external_tag", "unit", "scale", "offset", "enabled"],
    )

    with st.expander("Adicionar ou atualizar mapeamento de sinal"):
        with st.form("config_signal_form"):
            left, right = st.columns(2)

            with left:
                asset_id = st.selectbox("Ativo", assets or [""])
                source_id = st.selectbox("Fonte de dados", sources or [""])
                metric = st.selectbox("Métrica interna", METRICS)

            with right:
                external_tag = st.text_input("Tag externa / tópico / campo JSON / coluna CSV")
                unit = st.text_input("Unidade")
                enabled = st.checkbox("Ativo", value=True)

            col1, col2 = st.columns(2)
            scale = col1.number_input("Fator de escala", value=1.0)
            offset = col2.number_input("Offset", value=0.0)

            if st.form_submit_button("Salvar mapeamento", type="primary"):
                new_signal = {
                    "asset_id": asset_id,
                    "source_id": source_id,
                    "metric": metric,
                    "external_tag": external_tag.strip(),
                    "unit": unit.strip(),
                    "scale": scale,
                    "offset": offset,
                    "enabled": enabled,
                }
                data["signal_map"] = [
                    item
                    for item in signal_map
                    if not (
                        item.get("asset_id") == asset_id
                        and item.get("source_id") == source_id
                        and item.get("metric") == metric
                    )
                ] + [new_signal]
                _save(repo, data, "Mapeamento salvo com sucesso.")

    st.caption("A validação real de tags está na aba Fontes de Dados, vinculada à fonte e ao ativo selecionados.")


def _apply_parameter_preset_to_session(preset: dict[str, Any], context: str) -> None:
    st.session_state["param_preset_context"] = context
    st.session_state["param_normal_max"] = float(preset.get("normal_max", 0) or 0)
    st.session_state["param_attention_min"] = float(preset.get("attention_min", 0) or 0)
    st.session_state["param_alert_min"] = float(preset.get("alert_min", 0) or 0)
    st.session_state["param_critical_min"] = float(preset.get("critical_min", 0) or 0)
    st.session_state["param_normal_min"] = float(preset.get("normal_min", 0) or 0)
    st.session_state["param_attention_max"] = float(preset.get("attention_max", 0) or 0)
    st.session_state["param_alert_max"] = float(preset.get("alert_max", 0) or 0)
    st.session_state["param_critical_max"] = float(preset.get("critical_max", 0) or 0)
    st.session_state["param_persistence_min"] = int(preset.get("persistence_min", 3) or 3)
    st.session_state["param_recommended_action"] = str(preset.get("recommended_action", ""))


def _render_parameters_tab(repo: ConfigRepository, data: dict[str, Any]) -> None:
    st.markdown("#### Parâmetros Técnicos e Regras de Alerta")

    parameters = repo.parameters_alerts(data)
    assets = repo.assets(data)
    asset_ids = [asset.get("asset_id") for asset in assets if asset.get("asset_id")]
    asset_by_id = {asset.get("asset_id"): asset for asset in assets if asset.get("asset_id")}

    if parameters:
        rows = [
            {
                "Ativo": parameter.get("asset_id"),
                "Métrica": get_metric_label(parameter.get("metric")),
                "Normal até": parameter.get("normal_max", 0),
                "Atenção >=": parameter.get("attention_min", 0),
                "Alerta >=": parameter.get("alert_min", 0),
                "Crítico >=": parameter.get("critical_min", 0),
                "Normal acima": parameter.get("normal_min", 0),
                "Atenção abaixo": parameter.get("attention_max", 0),
                "Alerta abaixo": parameter.get("alert_max", 0),
                "Crítico abaixo": parameter.get("critical_max", 0),
                "Persistência": parameter.get("persistence_min", 0),
                "Ativa": parameter.get("enabled", True),
                "Ação recomendada": parameter.get("recommended_action", ""),
            }
            for parameter in parameters
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Nenhuma regra cadastrada.")

    with st.expander("Cadastrar regra de parâmetro ou alerta", expanded=False):
        if not asset_ids:
            st.warning("Cadastre ao menos um ativo antes de criar parâmetros de alerta.")
            return

        col_asset, col_metric = st.columns(2)
        asset_id = col_asset.selectbox("Ativo", asset_ids, key="param_asset_id")
        metric = col_metric.selectbox("Métrica", METRICS, format_func=get_metric_label, key="param_metric")

        selected_asset = asset_by_id.get(asset_id, {})
        preset = get_parameter_preset(metric, selected_asset)
        context = f"{asset_id}:{metric}"

        if st.session_state.get("param_preset_context") != context:
            _apply_parameter_preset_to_session(preset, context)

        st.caption(f"Preset sugerido: {preset.get('note', '')}")

        if st.button("Aplicar preset da métrica", width="stretch"):
            _apply_parameter_preset_to_session(preset, context)
            st.rerun()

        with st.form("config_parameter_form"):
            left, right = st.columns(2)

            with left:
                enabled = st.checkbox("Regra ativa", value=True)
                persistence_min = st.number_input(
                    "Persistência mínima em leituras",
                    min_value=1,
                    step=1,
                    key="param_persistence_min",
                )

            with right:
                recommended_action = st.text_area("Ação recomendada", key="param_recommended_action")

            st.markdown("##### Valor maior é pior")
            col1, col2, col3, col4 = st.columns(4)
            normal_max = col1.number_input("Normal até", key="param_normal_max")
            attention_min = col2.number_input("Atenção a partir de", key="param_attention_min")
            alert_min = col3.number_input("Alerta a partir de", key="param_alert_min")
            critical_min = col4.number_input("Crítico a partir de", key="param_critical_min")

            st.markdown("##### Valor menor é pior, exemplo Health Score")
            col5, col6, col7, col8 = st.columns(4)
            normal_min = col5.number_input("Normal acima de", key="param_normal_min")
            attention_max = col6.number_input("Atenção abaixo de", key="param_attention_max")
            alert_max = col7.number_input("Alerta abaixo de", key="param_alert_max")
            critical_max = col8.number_input("Crítico abaixo de", key="param_critical_max")

            submitted = st.form_submit_button("Salvar parâmetro/alerta", type="primary")

        if submitted:
            new_parameter = {
                "asset_id": asset_id,
                "metric": metric,
                "normal_max": normal_max,
                "attention_min": attention_min,
                "alert_min": alert_min,
                "critical_min": critical_min,
                "normal_min": normal_min,
                "attention_max": attention_max,
                "alert_max": alert_max,
                "critical_max": critical_max,
                "persistence_min": persistence_min,
                "enabled": enabled,
                "recommended_action": str(recommended_action or "").strip(),
            }
            errors = validate_parameter_rule(new_parameter)
            if errors:
                for error in errors:
                    st.error(error)
                return

            data["parameters_alerts"] = [
                item
                for item in parameters
                if not (item.get("asset_id") == asset_id and item.get("metric") == metric)
            ] + [new_parameter]
            _save(repo, data, "Parâmetro e alerta salvos com sucesso.")
