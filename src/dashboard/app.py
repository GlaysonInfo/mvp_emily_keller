from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
import streamlit as st

try:
    from dashboard.alert_projection import alerts_for_state
    from dashboard.alerts_ui import render_alerts_center
    from dashboard.config_repository import ConfigRepository
    from dashboard.config_ui import render_config_page
    from dashboard.dynamodb_repository import create_repository_from_env
    from dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases
    from dashboard.e2e_ui import render_e2e_test_page
    from dashboard.echarts_gauge_components import render_asset_gauges_echarts
    from dashboard.escalation_ui import render_escalation_page
    from dashboard.history_repository import create_history_repository_from_env
    from dashboard.history_ui import render_history_button
    from dashboard.multiasset_repository import create_multiasset_repository_from_env
    from dashboard.notification_outbox_ui import render_notification_outbox_page
    from dashboard.operational_intelligence_ui import render_operational_intelligence_page
    from dashboard.plant_overview_ui import render_plant_overview
    from dashboard.reports_ui import render_reports_page
    from dashboard.lubrication.lubrication_ui import render_lubrication_page
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alert_projection import alerts_for_state
    from src.dashboard.alerts_ui import render_alerts_center
    from src.dashboard.config_repository import ConfigRepository
    from src.dashboard.config_ui import render_config_page
    from src.dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases
    from src.dashboard.dynamodb_repository import create_repository_from_env
    from src.dashboard.e2e_ui import render_e2e_test_page
    from src.dashboard.echarts_gauge_components import render_asset_gauges_echarts
    from src.dashboard.escalation_ui import render_escalation_page
    from src.dashboard.history_repository import create_history_repository_from_env
    from src.dashboard.history_ui import render_history_button
    from src.dashboard.multiasset_repository import create_multiasset_repository_from_env
    from src.dashboard.notification_outbox_ui import render_notification_outbox_page
    from src.dashboard.operational_intelligence_ui import render_operational_intelligence_page
    from src.dashboard.plant_overview_ui import render_plant_overview
    from src.dashboard.reports_ui import render_reports_page
    from src.dashboard.lubrication.lubrication_ui import render_lubrication_page


st.set_page_config(
    page_title="MVP Monitoramento de Condição",
    page_icon=":material/monitoring:",
    layout="wide",
)

MODE_LABELS = {
    "normal": "Operação normal",
    "normal_operation": "Operação normal",
    "lubrication_degradation": "Degradação de lubrificação",
    "imbalance": "Desbalanceamento ou desalinhamento",
    "mechanical_unbalance": "Desbalanceamento ou desalinhamento",
    "thermal_stress": "Aquecimento anormal",
    "bearing_fault": "Falha em rolamento",
    "bearing_fault_initial": "Falha inicial em rolamento",
    "critical_failure_risk": "Risco crítico de parada",
    "post_maintenance_recovery": "Pós-manutenção / recuperação",
    "communication_lost": "Perda de comunicação",
    "unknown": "-",
}

STATUS_LABELS = {
    "normal": "NORMAL",
    "warning": "ATENÇÃO",
    "critical": "CRÍTICO",
    "NORMAL": "NORMAL",
    "ATENCAO": "ATENÇÃO",
    "ATENCAO ALTA": "ATENÇÃO ALTA",
    "ALERTA": "ALERTA",
    "CRITICO": "CRÍTICO",
    "RECUPERADO": "RECUPERADO",
    "SEM COMUNICACAO": "SEM COMUNICAÇÃO",
}

DEMO_PRESENTATION_INDEX_KEY = "demo_presentation_index"
DASHBOARD_PAGE_KEY = "dashboard_page"
PAGE_TARGET_KEY = "dashboard_page_target"
SELECTED_ASSET_ID_KEY = "selected_asset_id"


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1160px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        h1 {
            font-size: 2.1rem !important;
            line-height: 1.15 !important;
            margin-bottom: 0.25rem !important;
        }

        h2 {
            font-size: 1.35rem !important;
            line-height: 1.2 !important;
        }

        h3 {
            font-size: 1.05rem !important;
            line-height: 1.2 !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.78rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.45rem !important;
            line-height: 1.15 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        [data-testid="stMetric"] {
            min-height: 62px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def number_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, bool) or value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_value(metrics: dict[str, Any], *names: str, default: str = "-") -> str:
    if not isinstance(metrics, dict):
        return default

    value = None
    unit = ""

    for name in names:
        metric = metrics.get(name)

        if metric is None:
            continue

        if isinstance(metric, dict):
            value = metric.get("value")
            unit = display_unit(str(metric.get("unit", "")))
        else:
            value = metric
            unit = ""

        break

    if value is None:
        return default

    if isinstance(value, float):
        return f"{value:.2f} {unit}".strip()

    if value is None:
        return default

    return f"{value} {unit}".strip()


def display_unit(unit: str) -> str:
    if unit == "C":
        return "\N{DEGREE SIGN}C"

    return unit


def metric_number(metrics: dict[str, Any], *names: str) -> float | None:
    if not isinstance(metrics, dict):
        return None

    for name in names:
        value = number_value(metrics.get(name))

        if value is not None:
            return value

    return None


def state_number(latest_state: dict[str, Any], *names: str) -> float | None:
    metrics = latest_state.get("metrics")
    metric_map = metrics if isinstance(metrics, dict) else {}

    for name in names:
        value = number_value(latest_state.get(name))

        if value is not None:
            return value

        value = metric_number(metric_map, name)

        if value is not None:
            return value

    return None


def format_score(value: float | int | str | None) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def resolve_severity_score(latest_state: dict[str, Any], metrics: dict[str, Any]) -> float | None:
    metric_score = state_number(latest_state, "severity_score", "severity")

    if metric_score is not None:
        return metric_score

    health_score = state_number(latest_state, "health_score")

    if health_score is not None:
        return round(100.0 - health_score, 1)

    return None


def format_brazil_time(timestamp: Any) -> str:
    if not timestamp:
        return "-"

    if not isinstance(timestamp, str):
        return str(timestamp)

    try:
        dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp

    return dt_utc.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")


def severity_badge(severity: str) -> str:
    severity = severity.lower()

    if severity == "critical":
        return "CRÍTICO"

    if severity == "warning":
        return "ATENÇÃO"

    if severity == "normal":
        return "NORMAL"

    return severity.upper() if severity else "UNKNOWN"


def mode_label(mode: Any) -> str:
    if not mode:
        return "-"

    mode_text = str(mode)
    return MODE_LABELS.get(mode_text, mode_text)


def status_label(status: Any) -> str:
    if not status:
        return "-"

    status_text = str(status)
    return STATUS_LABELS.get(status_text, status_text)


def resolve_status_label(
    latest_state: dict[str, Any],
    failure_mode: str,
    health_score: float | None,
    severity_score: float | None,
) -> str:
    explicit_status = latest_state.get("status_label")

    if explicit_status:
        return status_label(explicit_status)

    if failure_mode == "communication_lost":
        return "SEM COMUNICAÇÃO"

    if failure_mode == "post_maintenance_recovery":
        return "RECUPERADO"

    if severity_score is not None:
        if severity_score >= 60:
            return "CRÍTICO"
        if severity_score >= 45:
            return "ALERTA"
        if severity_score >= 25:
            return "ATENÇÃO"

    if health_score is not None:
        if health_score < 40:
            return "CRÍTICO"
        if health_score < 60:
            return "ALERTA"
        if health_score < 80:
            return "ATENÇÃO"

    if failure_mode not in {"normal", "normal_operation", "unknown", "-"}:
        return "ATENÇÃO"

    return "NORMAL"


def clamp_demo_index(index: int, cases_count: int) -> int:
    if cases_count <= 0:
        return 0

    return max(0, min(index, cases_count - 1))


def current_demo_index(cases: list[dict[str, Any]]) -> int:
    raw_index = st.session_state.get(DEMO_PRESENTATION_INDEX_KEY, 0)

    try:
        index = int(raw_index)
    except (TypeError, ValueError):
        index = 0

    index = clamp_demo_index(index, len(cases))
    st.session_state[DEMO_PRESENTATION_INDEX_KEY] = index
    return index


def apply_demo_case(repo: Any, case: dict[str, Any], tenant_id: str, plant_id: str, asset_id: str) -> None:
    latest_item = build_latest_state_item(
        case,
        tenant_id=tenant_id,
        plant_id=plant_id,
        asset_id=asset_id,
    )
    alert_item = build_demo_alert_item(
        case,
        tenant_id=tenant_id,
        plant_id=plant_id,
        asset_id=asset_id,
        payload_updated_at=str(latest_item["updated_at"]),
    )

    repo.put_latest_state(latest_item)
    repo.clear_demo_alerts(tenant_id=tenant_id, asset_id=asset_id)

    if alert_item:
        repo.put_active_alert(alert_item)


def render_demo_selector(repo: Any, tenant_id: str, plant_id: str, asset_id: str) -> None:
    cases = load_demo_cases()

    if not cases:
        return

    index = current_demo_index(cases)
    selected_case = cases[index]

    st.divider()
    st.subheader("Modo Apresentação")
    st.markdown(f"**{index + 1}/{len(cases)} - {selected_case['case_name']}**")
    st.caption(selected_case.get("demo_message", ""))

    if st.button("⬅ Cenário anterior", disabled=index == 0, use_container_width=True):
        st.session_state[DEMO_PRESENTATION_INDEX_KEY] = clamp_demo_index(index - 1, len(cases))
        st.rerun()

    if st.button("Aplicar cenário", type="primary", use_container_width=True):
        try:
            apply_demo_case(repo, selected_case, tenant_id=tenant_id, plant_id=plant_id, asset_id=asset_id)
        except NoCredentialsError:
            st.error("Credenciais AWS não encontradas. Configure o AWS CLI antes de aplicar cenários.")
        else:
            st.success(f"Cenário aplicado: {selected_case['case_name']}")
            st.rerun()

    if st.button("Próximo cenário ➡", disabled=index == len(cases) - 1, use_container_width=True):
        st.session_state[DEMO_PRESENTATION_INDEX_KEY] = clamp_demo_index(index + 1, len(cases))
        st.rerun()


def render_metric_grid(metrics: dict[str, Any]) -> None:
    m1, m2, m3, m4 = st.columns(4)

    m1.metric("RPM", metric_value(metrics, "rpm"))
    m2.metric("Vibração RMS", metric_value(metrics, "vibration_rms_mm_s"))
    m3.metric("Temperatura", metric_value(metrics, "temperature_c"))
    m4.metric("Ultrassom", metric_value(metrics, "ultrasound_db"))

    m5, m6, m7, m8 = st.columns(4)

    m5.metric("Kurtosis", metric_value(metrics, "kurtosis"))
    m6.metric("Crest Factor", metric_value(metrics, "crest_factor"))
    m7.metric("Pico de vibração", metric_value(metrics, "vibration_peak_g"))
    m8.metric("Horímetro", metric_value(metrics, "horimeter_h", "hourmeter_h"))


def render_alerts(active_alerts: list[dict[str, Any]]) -> None:
    st.subheader("Alertas ativos")

    if not active_alerts:
        st.success("Nenhum alerta ativo para este ativo.")
        return

    alerts_df = [
        {
            "Tipo": mode_label(alert.get("alert_type")),
            "Severidade": severity_badge(str(alert.get("severity", ""))),
            "Status": alert.get("status"),
            "Causa provável": alert.get("probable_cause"),
            "Atualizado em": format_brazil_time(alert.get("updated_at")),
        }
        for alert in active_alerts
    ]

    st.dataframe(alerts_df, use_container_width=True, hide_index=True)

    for alert in active_alerts:
        severity = severity_badge(str(alert.get("severity", "")))
        title = f"{severity} - {alert.get('probable_cause', 'Alerta ativo')}"

        with st.expander(title, expanded=True):
            if alert.get("is_state_derived"):
                st.caption("Alerta operacional derivado do estado atual do ativo.")

            c1, c2, c3 = st.columns(3)
            c1.metric("Tipo", mode_label(alert.get("alert_type")))
            c2.metric("Status", alert.get("status", "-"))
            c3.metric("Confiança", str(alert.get("confidence", "-")))

            st.write(f"Primeira detecção: `{format_brazil_time(alert.get('first_detected_at'))}`")
            st.write(f"Última atualização: `{format_brazil_time(alert.get('updated_at'))}`")
            st.write(f"Modo simulado: `{mode_label(alert.get('failure_mode_simulated'))}`")

            st.markdown("**Evidências**")
            for evidence in alert.get("evidence", []):
                st.write(f"- {evidence}")

            st.markdown("**Ação recomendada**")
            st.info(alert.get("recommended_action", "-"))


def render_operational_diagnosis(latest_state: dict[str, Any]) -> None:
    diagnosis = latest_state.get("diagnosis")
    recommended_action = latest_state.get("recommended_action")
    client_question = latest_state.get("client_question_answered")
    expected_result = latest_state.get("expected_result")
    symptom = latest_state.get("symptom_simulated")
    demo_message = latest_state.get("demo_message")

    if not any([diagnosis, recommended_action, client_question, expected_result, symptom, demo_message]):
        return

    st.divider()
    st.subheader("Diagnóstico operacional")

    if demo_message:
        st.markdown(f"**Síntese do cenário:** {demo_message}")

    if symptom:
        st.write(f"**Sintoma simulado:** {symptom}")

    if diagnosis:
        st.markdown(f"**Diagnóstico esperado:** {diagnosis}")

    if recommended_action:
        st.markdown(f"**Ação recomendada:** {recommended_action}")

    if client_question:
        st.markdown(f"**Pergunta que este cenário responde ao cliente:** {client_question}")

    if expected_result:
        st.markdown(f"**Resultado esperado:** {expected_result}")


def render_aws_profile_error(error: ProfileNotFound) -> None:
    profile = os.getenv("AWS_PROFILE", "")
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    st.error(f"Profile AWS não encontrado: `{profile}`")
    st.write(
        "O dashboard está tentando usar um profile que não existe no AWS CLI desta máquina. "
        "Configure esse profile ou remova a variável `AWS_PROFILE` para usar credenciais padrão do ambiente."
    )

    st.markdown("**Opção 1: criar o profile informado**")
    st.code(
        f'aws configure --profile {profile or "automacaoapi"}\n'
        f'$env:AWS_PROFILE="{profile or "automacaoapi"}"\n'
        f'$env:AWS_REGION="{region}"',
        language="powershell",
    )

    st.markdown("**Opção 2: usar credenciais padrão, sem profile**")
    st.code(
        f'Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue\n'
        f'$env:AWS_REGION="{region}"',
        language="powershell",
    )

    st.caption(f"Detalhe técnico: {error}")


def render_aws_credentials_error(error: NoCredentialsError) -> None:
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    st.error("Credenciais AWS não encontradas")
    st.write(
        "O dashboard conseguiu iniciar, mas o boto3 não encontrou credenciais para consultar o DynamoDB. "
        "Configure credenciais no mesmo ambiente em que você executa o Streamlit."
    )

    st.markdown("**Opção 1: usar credenciais padrão**")
    st.code(
        f'aws configure\n'
        f'$env:AWS_REGION="{region}"\n'
        f'streamlit run src/dashboard/app.py',
        language="powershell",
    )

    st.markdown("**Opção 2: usar um profile nomeado**")
    st.code(
        f'aws configure --profile automacaoapi\n'
        f'$env:AWS_PROFILE="automacaoapi"\n'
        f'$env:AWS_REGION="{region}"\n'
        f'streamlit run src/dashboard/app.py',
        language="powershell",
    )

    st.caption(f"Detalhe técnico: {error}")


def render_history_unavailable(error: Exception) -> None:
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "ResourceNotFoundException":
            table_name = os.getenv("CONDITION_HISTORY_TABLE", "condition_history")
            region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
            st.sidebar.warning(
                "Histórico indisponível: crie a tabela "
                f"`{table_name}` na região `{region}` para habilitar o log operacional."
            )
            return

    st.sidebar.warning(f"Histórico indisponível: {error}")


def render_asset_detail(
    latest_state: dict[str, Any],
    active_alerts: list[dict[str, Any]],
    *,
    tenant_id: str,
    asset_id: str,
    history_repo: Any | None,
) -> None:
    metrics = latest_state.get("metrics", {})
    failure_mode = str(latest_state.get("failure_mode_simulated") or latest_state.get("mode") or "unknown")
    source = latest_state.get("source", "unknown")
    updated_at = format_brazil_time(latest_state.get("updated_at"))
    health_score = state_number(latest_state, "health_score")
    severity_score = resolve_severity_score(latest_state, metrics)
    operational_status = resolve_status_label(latest_state, failure_mode, health_score, severity_score)

    st.subheader("Estado atual do ativo")
    st.subheader(f"Status operacional: {operational_status}")

    col1, col2, col3, col4 = st.columns([1.2, 2.4, 1.2, 1.2])

    col1.metric("Ativo", asset_id)
    col2.metric("Modo atual", mode_label(failure_mode))
    col3.metric("Health Score", format_score(health_score))
    col4.metric("Severity Score", format_score(severity_score))

    st.caption(f"Fonte: `{source}` | Atualizado em: `{updated_at}`")

    st.divider()
    st.subheader("Métricas atuais")
    render_metric_grid(metrics)

    st.divider()
    render_asset_gauges_echarts(latest_state, cols_per_row=3)

    if history_repo is not None:
        render_history_button(
            history_repo=history_repo,
            tenant_id=tenant_id,
            asset_id=asset_id,
            timezone_str="America/Sao_Paulo",
        )

    render_operational_diagnosis(latest_state)

    st.divider()
    render_alerts(active_alerts)
    return


def main() -> None:
    config_store_path = os.getenv("DASHBOARD_CONFIG_STORE") or None
    config_repo = ConfigRepository(config_store_path)
    config = config_repo.load()
    client_config = config_repo.client(config)
    plant_config = config_repo.plant(config)

    tenant_id = os.getenv("TENANT_ID") or str(client_config.get("tenant_id") or "cliente_demo")
    plant_id = os.getenv("PLANT_ID") or str(plant_config.get("plant_id") or "lab_virtual")
    default_asset_id = os.getenv("ASSET_ID") or config_repo.default_asset_id(config)

    if SELECTED_ASSET_ID_KEY not in st.session_state:
        st.session_state[SELECTED_ASSET_ID_KEY] = default_asset_id

    page_target = st.session_state.pop(PAGE_TARGET_KEY, None)
    if page_target:
        st.session_state[DASHBOARD_PAGE_KEY] = page_target

    render_global_styles()

    st.title("MVP Monitoramento de Condição")
    st.caption("Bancada virtual OPC UA -> Bridge HTTPS -> AWS -> Diagnóstico")

    with st.sidebar:
        st.header("Ambiente")
        st.caption(f"Atual: {config_repo.environment_label(config)}")
        page = st.radio(
            "Navegação",
            [
                "Visão Geral da Planta",
                "Detalhe do Ativo",
                "Inteligência Operacional",
                "Sistema de Lubrificação",
                "Alertas e Eventos",
                "Matriz de Escalonamento",
                "Notification Outbox",
                "Relatórios",
                "Configurações",
                "Teste ponta a ponta",
            ],
            index=0,
            key=DASHBOARD_PAGE_KEY,
        )
        asset_id = str(st.session_state.get(SELECTED_ASSET_ID_KEY, default_asset_id))
        auto_refresh = False
        refresh_seconds = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5"))

        if page not in {"Configurações", "Teste ponta a ponta"}:
            if page != "Sistema de Lubrificação":
                st.write(f"Ativo selecionado: `{asset_id}`")
            auto_refresh = st.checkbox("Auto-refresh", value=True)
            refresh_seconds = st.number_input(
                "Intervalo de atualização em segundos",
                min_value=2,
                max_value=60,
                value=refresh_seconds,
            )

            if st.button("Atualizar agora", type="primary"):
                st.rerun()

            if page == "Detalhe do Ativo" and st.button("Trocar ativo", use_container_width=True):
                st.session_state[PAGE_TARGET_KEY] = "Visão Geral da Planta"
                st.rerun()

    asset_id = str(st.session_state.get(SELECTED_ASSET_ID_KEY, default_asset_id))

    if page == "Configurações":
        render_config_page(config_store_path)
        st.stop()
        return

    elif page == "Teste ponta a ponta":
        render_e2e_test_page(config_store_path)
        st.stop()
        return

    elif page == "Inteligência Operacional":
        try:
            render_operational_intelligence_page(
                tenant_id=tenant_id,
                plant_id=plant_id,
                asset_id=asset_id,
                history_hours=24,
            )
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar a inteligência operacional: {exc}")
            st.stop()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Sistema de Lubrificação":
        try:
            render_lubrication_page(os.getenv("LUBRICATION_CONFIG_PATH", "config/lubrication_pilot_config.json"))
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar o sistema de lubrificação: {exc}")
            st.stop()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Alertas e Eventos":
        try:
            render_alerts_center(
                tenant_id=tenant_id,
                plant_id=plant_id,
                assets=config_repo.assets(config),
                timezone_str=str(client_config.get("timezone") or "America/Sao_Paulo"),
            )
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar a central de alertas: {exc}")
            st.stop()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Matriz de Escalonamento":
        try:
            render_escalation_page(
                tenant_id=tenant_id,
                plant_id=plant_id,
                assets=config_repo.assets(config),
            )
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar a matriz de escalonamento: {exc}")
            st.stop()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Notification Outbox":
        try:
            multi_repo = create_multiasset_repository_from_env()
            current_states = multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
            render_notification_outbox_page(
                tenant_id=tenant_id,
                plant_id=plant_id,
                assets=config_repo.assets(config),
                escalation_path="escalation_rules_store.json",
                current_states=current_states,
            )
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar a Notification Outbox: {exc}")
            st.stop()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Visão Geral da Planta":
        try:
            multi_repo = create_multiasset_repository_from_env()
            states = multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar a visão geral da planta: {exc}")
            st.stop()

        selected_asset_id = render_plant_overview(states)

        if selected_asset_id:
            st.session_state[SELECTED_ASSET_ID_KEY] = selected_asset_id
            st.session_state[PAGE_TARGET_KEY] = "Detalhe do Ativo"
            st.rerun()

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    elif page == "Relatórios":
        try:
            repo = create_repository_from_env()
            multi_repo = create_multiasset_repository_from_env()
            states = multi_repo.list_current_states(tenant_id=tenant_id, plant_id=plant_id)
            alerts = repo.list_alerts(tenant_id=tenant_id, plant_id=plant_id)
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar os dados para relatórios: {exc}")
            st.stop()

        history_repo = None
        try:
            history_repo = create_history_repository_from_env()
        except Exception as exc:
            render_history_unavailable(exc)

        render_reports_page(
            states=states,
            alerts=alerts,
            history_repo=history_repo,
            tenant_id=tenant_id,
            selected_asset_id=asset_id,
        )
        st.stop()
        return

    elif page == "Detalhe do Ativo":
        try:
            repo = create_repository_from_env()
        except ProfileNotFound as exc:
            render_aws_profile_error(exc)
            st.stop()

        with st.sidebar:
            render_demo_selector(repo, tenant_id=tenant_id, plant_id=plant_id, asset_id=asset_id)

        try:
            latest_state = repo.get_latest_state(tenant_id=tenant_id, asset_id=asset_id)
            active_alerts = repo.get_active_alerts(tenant_id=tenant_id, asset_id=asset_id)
        except NoCredentialsError as exc:
            render_aws_credentials_error(exc)
            st.stop()
        except ClientError as exc:
            st.error(f"Não foi possível carregar o detalhe do ativo: {exc}")
            st.stop()

        if not latest_state:
            st.warning("Nenhum estado atual encontrado no DynamoDB.")
            st.stop()

        active_alerts = alerts_for_state(latest_state, active_alerts)

        history_repo = None
        try:
            history_repo = create_history_repository_from_env()
            history_repo.put_minute_snapshot(latest_state, retention_days=int(os.getenv("HISTORY_RETENTION_DAYS", "365")))
        except Exception as exc:
            render_history_unavailable(exc)

        render_asset_detail(
            latest_state,
            active_alerts,
            tenant_id=tenant_id,
            asset_id=asset_id,
            history_repo=history_repo,
        )

        if auto_refresh:
            time.sleep(float(refresh_seconds))
            st.rerun()

        st.stop()
        return

    st.error(f"Página não reconhecida: {page}")
    st.stop()
    return


if __name__ == "__main__":
    main()
