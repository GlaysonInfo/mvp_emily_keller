from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

try:
    from dashboard.config_repository import ConfigRepository
    from dashboard.dynamodb_repository import decimal_to_native
    from dashboard.history_repository import build_history_item, to_dynamodb_safe
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.config_repository import ConfigRepository
    from src.dashboard.dynamodb_repository import decimal_to_native
    from src.dashboard.history_repository import build_history_item, to_dynamodb_safe


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def state_table_name_from_env() -> str:
    return os.getenv("DYNAMODB_STATE_TABLE") or os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev")


def history_table_name_from_env() -> str:
    return os.getenv("CONDITION_HISTORY_TABLE", "condition_history")


def alerts_table_name_from_env() -> str:
    return os.getenv("ALERTS_TABLE") or os.getenv("CONDITION_ALERTS_TABLE", "mvp_alerts_dev")


def region_from_env() -> str:
    return os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def load_config(config_path: str | None = None) -> dict[str, Any]:
    return ConfigRepository(config_path).load()


def session_resource() -> Any:
    profile_name = os.getenv("AWS_PROFILE") or None
    session = boto3.Session(profile_name=profile_name, region_name=region_from_env())
    return session.resource("dynamodb")


def _asset(config: dict[str, Any], asset_id: str) -> dict[str, Any]:
    return next((asset for asset in config.get("assets", []) if asset.get("asset_id") == asset_id), {})


def _source(config: dict[str, Any], source_id: str) -> dict[str, Any]:
    return next((source for source in config.get("data_sources", []) if source.get("source_id") == source_id), {})


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def is_virtual_source(source: dict[str, Any]) -> bool:
    protocol = _norm(source.get("protocol"))
    source_type = _norm(source.get("source_type"))
    endpoint = _norm(source.get("endpoint"))
    source_id = _norm(source.get("source_id"))

    return (
        "interno" in protocol
        or "simulação" in source_type
        or "simulacao" in source_type
        or endpoint.startswith("local/")
        or source_id.startswith("virtual")
        or source_id.startswith("bancada")
    )


def is_csv_source(source: dict[str, Any]) -> bool:
    protocol = _norm(source.get("protocol"))
    source_type = _norm(source.get("source_type"))
    endpoint = _norm(source.get("endpoint"))

    return "csv" in protocol or "manual" in protocol or "arquivo" in source_type or endpoint.startswith("upload/")


def is_http_source(source: dict[str, Any]) -> bool:
    protocol = _norm(source.get("protocol"))
    endpoint = _norm(source.get("endpoint"))

    return (
        "http" in protocol
        or "https" in protocol
        or endpoint.startswith("http://")
        or endpoint.startswith("https://")
    )


def infer_test_mode(source: dict[str, Any], requested_mode: str) -> tuple[str, str]:
    requested = _norm(requested_mode)

    if is_virtual_source(source):
        return "virtual", "Fonte virtual detectada; usando payload simulado local."

    if requested == "csv" or is_csv_source(source):
        return "csv", "Fonte CSV/manual detectada."

    if requested == "http" or is_http_source(source):
        return "http", "Fonte HTTP/HTTPS detectada."

    return "virtual", "Modo não reconhecido; usando payload simulado seguro."


def sample_payload(config: dict[str, Any], asset_id: str, source_id: str) -> dict[str, Any]:
    client = config.get("client", {})
    plant = config.get("plant", {})
    asset = _asset(config, asset_id)
    nominal_rpm = float(asset.get("nominal_rpm") or 1800)

    return {
        "tenant_id": client.get("tenant_id", "cliente_demo"),
        "plant_id": plant.get("plant_id", "lab_virtual"),
        "asset_id": asset_id,
        "source_id": source_id,
        "timestamp_utc": now_utc(),
        "metrics": {
            "rpm": round(nominal_rpm * 0.989, 2),
            "vibration_rms_mm_s": 2.96,
            "temperature_c": 67.91,
            "ultrasound_db": 41.54,
            "kurtosis_index": 3.59,
            "crest_factor_index": 3.42,
            "vibration_peak_g": 0.69,
            "hourmeter_h": 1284.03,
        },
        "quality": {
            "status": "good",
            "sample_rate_sec": 5,
            "source": "e2e_virtual_sample",
        },
    }


def payload_from_csv(uploaded_or_path: Any, asset_id: str, source_id: str, config: dict[str, Any]) -> dict[str, Any]:
    if uploaded_or_path is None:
        raise RuntimeError("Envie um arquivo CSV para executar o modo CSV/manual.")

    if hasattr(uploaded_or_path, "getvalue"):
        raw = uploaded_or_path.getvalue()
        text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else str(raw)
    else:
        from pathlib import Path

        text = Path(uploaded_or_path).read_text(encoding="utf-8-sig")

    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))

    if not rows:
        raise RuntimeError("CSV vazio ou sem linhas de dados.")

    row = next((item for item in rows if item.get("asset_id") == asset_id), rows[0])
    client = config.get("client", {})
    plant = config.get("plant", {})

    def number(name: str) -> float | None:
        raw_value = row.get(name)

        if raw_value in {None, ""}:
            return None

        try:
            return float(str(raw_value).replace(",", "."))
        except ValueError:
            return None

    return {
        "tenant_id": client.get("tenant_id", "cliente_demo"),
        "plant_id": plant.get("plant_id", "lab_virtual"),
        "asset_id": row.get("asset_id") or asset_id,
        "source_id": source_id,
        "timestamp_utc": row.get("timestamp_utc") or now_utc(),
        "metrics": {
            "rpm": number("rpm"),
            "vibration_rms_mm_s": number("vibration_rms_mm_s"),
            "temperature_c": number("temperature_c"),
            "ultrasound_db": number("ultrasound_db"),
            "kurtosis_index": number("kurtosis_index"),
            "crest_factor_index": number("crest_factor_index"),
            "vibration_peak_g": number("vibration_peak_g"),
            "hourmeter_h": number("hourmeter_h"),
        },
        "quality": {"status": "good", "source": "csv_manual"},
    }


def payload_from_http(endpoint: str, timeout_sec: int = 5) -> dict[str, Any]:
    if not endpoint:
        raise RuntimeError("Endpoint da fonte de dados não configurado.")

    endpoint = str(endpoint).strip()
    if not endpoint.lower().startswith(("http://", "https://")):
        raise RuntimeError(
            f"Endpoint inválido para HTTP/HTTPS: {endpoint!r}. "
            "Use uma URL iniciada por http:// ou https://, ou selecione Bancada Virtual."
        )

    start = time.perf_counter()
    request = urllib.request.Request(endpoint, headers={"Accept": "application/json"})

    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        raw = response.read()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        data = json.loads(raw.decode("utf-8"))

    data.setdefault("quality", {})
    data["quality"]["latency_ms"] = latency_ms
    data["quality"]["source"] = "http_bridge"
    return data


def metric_value(payload: dict[str, Any], metric: str) -> float | None:
    raw_value = payload.get(metric, (payload.get("metrics") or {}).get(metric))

    if raw_value is None or isinstance(raw_value, bool):
        return None

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def evaluate_rules(config: dict[str, Any], payload: dict[str, Any]) -> tuple[str, float, float, list[dict[str, Any]]]:
    asset_id = payload.get("asset_id")
    rules = [
        rule
        for rule in config.get("parameters_alerts", [])
        if rule.get("asset_id") == asset_id and rule.get("enabled", True)
    ]
    severity_rank = {"NORMAL": 0, "ATENÇÃO": 30, "ALERTA": 55, "CRÍTICO": 80}
    events: list[dict[str, Any]] = []
    max_severity = 0

    for rule in rules:
        metric = str(rule.get("metric") or "")
        value = metric_value(payload, metric)

        if value is None:
            continue

        label = "NORMAL"
        threshold = None
        critical_min = float(rule.get("critical_min") or 0)
        alert_min = float(rule.get("alert_min") or 0)
        attention_min = float(rule.get("attention_min") or 0)
        critical_max = float(rule.get("critical_max") or 0)
        alert_max = float(rule.get("alert_max") or 0)
        attention_max = float(rule.get("attention_max") or 0)

        if metric == "health_score" or (critical_max > 0 and alert_max > 0):
            if critical_max and value <= critical_max:
                label, threshold = "CRÍTICO", critical_max
            elif alert_max and value <= alert_max:
                label, threshold = "ALERTA", alert_max
            elif attention_max and value <= attention_max:
                label, threshold = "ATENÇÃO", attention_max
        else:
            if critical_min and value >= critical_min:
                label, threshold = "CRÍTICO", critical_min
            elif alert_min and value >= alert_min:
                label, threshold = "ALERTA", alert_min
            elif attention_min and value >= attention_min:
                label, threshold = "ATENÇÃO", attention_min

        severity = severity_rank[label]
        max_severity = max(max_severity, severity)

        if label != "NORMAL":
            events.append(
                {
                    "metric": metric,
                    "value": value,
                    "status_label": label,
                    "threshold": threshold,
                    "recommended_action": rule.get("recommended_action", ""),
                }
            )

    severity_score = payload.get("severity_score")
    health_score = payload.get("health_score")

    if severity_score is None:
        severity_score = max_severity

    if health_score is None:
        health_score = round(max(0, 100 - float(severity_score)), 1)

    if max_severity >= 80:
        overall = "CRÍTICO"
    elif max_severity >= 55:
        overall = "ALERTA"
    elif max_severity >= 30:
        overall = "ATENÇÃO"
    else:
        overall = "NORMAL"

    return overall, float(health_score), float(severity_score), events


def build_current_state_item(
    config: dict[str, Any],
    payload: dict[str, Any],
    status_label: str,
    health_score: float,
    severity_score: float,
) -> dict[str, Any]:
    asset = _asset(config, str(payload.get("asset_id")))
    tenant_id = str(payload.get("tenant_id"))
    asset_id = str(payload.get("asset_id"))
    metrics = payload.get("metrics") or {}
    updated_at = payload.get("timestamp_utc") or now_utc()

    return {
        **asset,
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": "LATEST",
        "tenant_id": tenant_id,
        "plant_id": payload.get("plant_id"),
        "asset_id": asset_id,
        "source": payload.get("source_id"),
        "source_id": payload.get("source_id"),
        "updated_at": updated_at,
        "status_label": status_label,
        "health_score": health_score,
        "severity_score": severity_score,
        "mode": "e2e_ingestion_test",
        "mode_label": "Teste ponta a ponta",
        "metrics": metrics,
        "rpm": metrics.get("rpm"),
        "vibration_rms": metrics.get("vibration_rms_mm_s"),
        "temperature": metrics.get("temperature_c"),
        "ultrasound": metrics.get("ultrasound_db"),
        "kurtosis": metrics.get("kurtosis_index"),
        "crest_factor": metrics.get("crest_factor_index"),
        "vibration_peak": metrics.get("vibration_peak_g"),
        "hourmeter": metrics.get("hourmeter_h"),
        "diagnosis": "Registro gerado pelo teste ponta a ponta.",
        "recommended_action": "Validar cadeia fonte -> ingestão -> estado atual -> histórico -> alerta.",
        "tenant_plant": f"{tenant_id}#{payload.get('plant_id')}",
        "is_e2e_test": True,
    }


def _alert_severity(status_label: str) -> str:
    if status_label in {"CRÍTICO", "CRITICO"}:
        return "critical"

    return "warning"


def build_alert_item(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    tenant_id = str(state.get("tenant_id"))
    asset_id = str(state.get("asset_id"))
    metric = str(event.get("metric"))
    updated_at = state.get("updated_at") or now_utc()
    status_label = str(event.get("status_label") or "ATENÇÃO")

    return {
        "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
        "sk": f"ALERT#ACTIVE#E2E#{metric}",
        "tenant_asset": f"{tenant_id}#{asset_id}",
        "alert_key": f"open#e2e#{metric}",
        "alert_id": f"{tenant_id}#{asset_id}#{metric}#e2e",
        "tenant_id": tenant_id,
        "plant_id": state.get("plant_id"),
        "asset_id": asset_id,
        "asset_name": state.get("asset_name"),
        "source_id": state.get("source_id"),
        "alert_type": "e2e_ingestion_test",
        "metric": metric,
        "value": event.get("value"),
        "threshold": event.get("threshold"),
        "severity": _alert_severity(status_label),
        "status_label": status_label,
        "status": "open",
        "probable_cause": f"{metric} fora da faixa configurada",
        "confidence": 1.0,
        "evidence": [f"{metric}: {event.get('value')} | limite: {event.get('threshold')}"],
        "recommended_action": event.get("recommended_action") or "Verificar condição operacional do ativo.",
        "failure_mode_simulated": "e2e_ingestion_test",
        "source": "e2e_test",
        "first_detected_at": updated_at,
        "updated_at": updated_at,
        "last_payload_timestamp": updated_at,
        "created_by": "e2e_test",
        "is_e2e_test": True,
    }


def _fallback_query_alerts(table: Any, tenant_id: str, asset_id: str) -> list[dict[str, Any]]:
    tenant_asset = f"{tenant_id}#{asset_id}"
    result = table.query(KeyConditionExpression=Key("tenant_asset").eq(tenant_asset))
    return [decimal_to_native(item) for item in result.get("Items", [])]


class E2EDynamoClient:
    def __init__(
        self,
        *,
        state_table_name: str | None = None,
        history_table_name: str | None = None,
        alerts_table_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        dynamodb_resource = dynamodb_resource or session_resource()
        self.state_table = dynamodb_resource.Table(state_table_name or state_table_name_from_env())
        self.history_table = dynamodb_resource.Table(history_table_name or history_table_name_from_env())
        self.alerts_table = dynamodb_resource.Table(alerts_table_name or alerts_table_name_from_env())

    def put_current_state(self, state: dict[str, Any]) -> None:
        self.state_table.put_item(Item=to_dynamodb_safe(state))

    def read_current_state(self, tenant_id: str, asset_id: str) -> dict[str, Any]:
        result = self.state_table.get_item(
            Key={
                "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
                "sk": "LATEST",
            }
        )
        return decimal_to_native(result.get("Item", {}))

    def put_history(self, state: dict[str, Any]) -> dict[str, Any]:
        history_item = build_history_item(state)
        self.history_table.put_item(Item=history_item)
        return decimal_to_native(history_item)

    def query_history(self, tenant_id: str, asset_id: str, *, minutes_back: int = 10) -> list[dict[str, Any]]:
        end = datetime.now(UTC)
        start = end - timedelta(minutes=minutes_back)
        tenant_asset = f"{tenant_id}#{asset_id}"
        result = self.history_table.query(
            KeyConditionExpression=Key("tenant_asset").eq(tenant_asset)
            & Key("ts_utc_minute").between(
                start.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
                end.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            )
        )
        return [decimal_to_native(item) for item in result.get("Items", [])]

    def put_alerts(self, state: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        saved_alerts = [build_alert_item(state, event) for event in events]

        for alert in saved_alerts:
            self.alerts_table.put_item(Item=to_dynamodb_safe(alert))

        return saved_alerts

    def query_alerts(self, tenant_id: str, asset_id: str) -> list[dict[str, Any]]:
        pk = f"TENANT#{tenant_id}#ASSET#{asset_id}"

        try:
            result = self.alerts_table.query(
                KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("ALERT#ACTIVE#")
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ValidationException":
                raise
            return _fallback_query_alerts(self.alerts_table, tenant_id, asset_id)

        return [decimal_to_native(item) for item in result.get("Items", [])]


def _blank_result(source_id: str, asset_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "checked_at_utc": now_utc(),
        "source_id": source_id,
        "asset_id": asset_id,
        "requested_mode": None,
        "effective_mode": None,
        "status_label": "-",
        "health_score": None,
        "severity_score": None,
        "steps": [],
        "payload": None,
        "current_state": None,
        "history_records": 0,
        "alerts_records": 0,
        "alerts_created": [],
    }


def run_e2e_test(
    *,
    config_path: str | None,
    source_id: str,
    asset_id: str,
    mode: str = "virtual",
    csv_file: Any = None,
    dynamodb_client: E2EDynamoClient | None = None,
) -> dict[str, Any]:
    result = _blank_result(source_id, asset_id)

    def step(name: str, ok: bool, details: dict[str, Any] | None = None) -> None:
        result["steps"].append({"step": name, "ok": bool(ok), "details": details or {}})

    try:
        config = load_config(config_path)
        source = _source(config, source_id)

        if not source:
            step("Fonte de dados localizada", False, {"source_id": source_id})
            return result

        step(
            "Fonte de dados localizada",
            True,
            {
                "source_id": source_id,
                "protocol": source.get("protocol"),
                "source_type": source.get("source_type"),
                "endpoint": source.get("endpoint"),
            },
        )

        effective_mode, mode_reason = infer_test_mode(source, mode)
        result["requested_mode"] = mode
        result["effective_mode"] = effective_mode
        step(
            "Modo de teste definido",
            True,
            {
                "requested_mode": mode,
                "effective_mode": effective_mode,
                "reason": mode_reason,
                "endpoint": source.get("endpoint"),
            },
        )

        if effective_mode == "csv":
            payload = payload_from_csv(csv_file, asset_id, source_id, config)
        elif effective_mode == "http":
            payload = payload_from_http(str(source.get("endpoint") or ""))
        else:
            payload = sample_payload(config, asset_id, source_id)

        result["payload"] = payload
        result["asset_id"] = payload.get("asset_id")
        step("Payload obtido", True, {"asset_id": payload.get("asset_id"), "timestamp_utc": payload.get("timestamp_utc")})

        status_label, health_score, severity_score, events = evaluate_rules(config, payload)
        result["status_label"] = status_label
        result["health_score"] = health_score
        result["severity_score"] = severity_score
        step(
            "Regras de alerta avaliadas",
            True,
            {
                "status_label": status_label,
                "health_score": health_score,
                "severity_score": severity_score,
                "events": events,
            },
        )

        state = build_current_state_item(config, payload, status_label, health_score, severity_score)
        dynamodb_client = dynamodb_client or E2EDynamoClient()
        dynamodb_client.put_current_state(state)
        step("Estado atual gravado no DynamoDB", True, {"table": state_table_name_from_env()})

        history_item = dynamodb_client.put_history(state)
        step(
            "Histórico gravado no DynamoDB",
            True,
            {"table": history_table_name_from_env(), "ts_utc_minute": history_item.get("ts_utc_minute")},
        )

        alerts_created = dynamodb_client.put_alerts(state, events)
        result["alerts_created"] = alerts_created
        step(
            "Alertas avaliados e gravados",
            True,
            {"table": alerts_table_name_from_env(), "alerts_count": len(alerts_created)},
        )

        readback = dynamodb_client.read_current_state(str(payload.get("tenant_id")), str(payload.get("asset_id")))
        result["current_state"] = readback
        step(
            "Dashboard consegue ler estado atual",
            bool(readback),
            {"asset_id": readback.get("asset_id"), "status_label": readback.get("status_label")},
        )

        history = dynamodb_client.query_history(str(payload.get("tenant_id")), str(payload.get("asset_id")))
        result["history_records"] = len(history)
        step("Histórico consultável", len(history) > 0, {"records": len(history)})

        alerts = dynamodb_client.query_alerts(str(payload.get("tenant_id")), str(payload.get("asset_id")))
        result["alerts_records"] = len(alerts)
        step("Alertas consultáveis", True, {"records": len(alerts)})

    except Exception as exc:
        step("Falha durante execução", False, {"error": str(exc), "error_type": type(exc).__name__})

    result["ok"] = all(item["ok"] for item in result["steps"])
    result["checked_at_utc"] = now_utc()
    return result
