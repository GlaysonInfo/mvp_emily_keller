from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
import streamlit as st

try:
    from dashboard.dynamodb_repository import create_repository_from_env
    from dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases
    from dashboard.echarts_gauge_components import render_asset_gauges_echarts
    from dashboard.history_repository import create_history_repository_from_env
    from dashboard.history_ui import render_history_button
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.demo_cases import build_demo_alert_item, build_latest_state_item, load_demo_cases
    from src.dashboard.dynamodb_repository import create_repository_from_env
    from src.dashboard.echarts_gauge_components import render_asset_gauges_echarts
    from src.dashboard.history_repository import create_history_repository_from_env
    from src.dashboard.history_ui import render_history_button


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


def metric_value(metrics: dict[str, Any], name: str, default: str = "-") -> str:
    metric = metrics.get(name)

    if not metric:
        return default

    value = metric.get("value")
    unit = display_unit(str(metric.get("unit", "")))

    if isinstance(value, float):
        return f"{value:.2f} {unit}".strip()

    if value is None:
        return default

    return f"{value} {unit}".strip()


def display_unit(unit: str) -> str:
    if unit == "C":
        return "\N{DEGREE SIGN}C"

    return unit


def metric_number(metrics: dict[str, Any], name: str) -> float | None:
    metric = metrics.get(name)

    if not isinstance(metric, dict):
        return None

    value = metric.get("value")

    if isinstance(value, int | float):
        return float(value)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_score(value: float | int | str | None) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def resolve_severity_score(latest_state: dict[str, Any], metrics: dict[str, Any]) -> float | None:
    explicit_score = latest_state.get("severity_score")

    if isinstance(explicit_score, int | float):
        return float(explicit_score)

    metric_score = metric_number(metrics, "severity")

    if metric_score is not None:
        return metric_score

    health_score = metric_number(metrics, "health_score")

    if health_score is None:
        health_score = latest_state.get("health_score")

    if isinstance(health_score, int | float):
        return round(100.0 - float(health_score), 1)

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
    m8.metric("Horímetro", metric_value(metrics, "horimeter_h"))


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


def main() -> None:
    tenant_id = os.getenv("TENANT_ID", "cliente_demo")
    plant_id = os.getenv("PLANT_ID", "lab_virtual")
    asset_id = os.getenv("ASSET_ID", "motor_001")

    st.title("MVP Monitoramento de Condição")
    st.caption("Bancada virtual OPC UA -> Bridge HTTPS -> AWS -> Diagnóstico")

    try:
        repo = create_repository_from_env()
    except ProfileNotFound as exc:
        render_aws_profile_error(exc)
        st.stop()

    with st.sidebar:
        st.header("Configuração")
        st.write(f"Tenant: `{tenant_id}`")
        st.write(f"Planta: `{plant_id}`")
        st.write(f"Ativo: `{asset_id}`")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_seconds = st.number_input(
            "Intervalo de atualização em segundos",
            min_value=2,
            max_value=60,
            value=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5")),
        )

        if st.button("Atualizar agora", type="primary"):
            st.rerun()

        render_demo_selector(repo, tenant_id=tenant_id, plant_id=plant_id, asset_id=asset_id)

    try:
        latest_state = repo.get_latest_state(tenant_id=tenant_id, asset_id=asset_id)
        active_alerts = repo.get_active_alerts(tenant_id=tenant_id, asset_id=asset_id)
    except NoCredentialsError as exc:
        render_aws_credentials_error(exc)
        st.stop()

    if not latest_state:
        st.warning("Nenhum estado atual encontrado no DynamoDB.")
        st.stop()

    history_repo = None
    try:
        history_repo = create_history_repository_from_env()
        history_repo.put_minute_snapshot(latest_state, retention_days=int(os.getenv("HISTORY_RETENTION_DAYS", "365")))
    except Exception as exc:
        render_history_unavailable(exc)

    metrics = latest_state.get("metrics", {})
    failure_mode = str(latest_state.get("failure_mode_simulated") or latest_state.get("mode") or "unknown")
    source = latest_state.get("source", "unknown")
    updated_at = format_brazil_time(latest_state.get("updated_at"))
    health_score = metric_number(metrics, "health_score")
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

    if auto_refresh:
        time.sleep(float(refresh_seconds))
        st.rerun()


if __name__ == "__main__":
    main()
