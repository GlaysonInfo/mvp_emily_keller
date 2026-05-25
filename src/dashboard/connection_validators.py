from __future__ import annotations

import csv
import io
import socket
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    status: str
    message: str
    details: dict[str, Any]
    checked_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EXPECTED_CONTRACT_METRICS = [
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

CSV_REQUIRED_COLUMNS = [
    "asset_id",
    "timestamp_utc",
    "rpm",
    "vibration_rms_mm_s",
    "temperature_c",
]

MAIN_MAPPED_METRICS = ["rpm", "vibration_rms_mm_s", "temperature_c"]
SAFE_CREDENTIAL_PREFIXES = ("aws_secrets/", "aws-secrets:", "env/", "vault/", "ssm/")


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _result(
    ok: bool,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ValidationResult:
    return ValidationResult(
        ok=ok,
        status=status,
        message=message,
        details=details or {},
        checked_at_utc=_now_utc(),
    )


def normalize_protocol(value: Any) -> str:
    return str(value or "").strip().lower()


def _metric_name(signal: dict[str, Any]) -> str:
    return str(signal.get("metric") or signal.get("internal_metric") or "")


def _is_virtual_source(source: dict[str, Any]) -> bool:
    protocol = normalize_protocol(source.get("protocol"))
    source_type = normalize_protocol(source.get("source_type"))
    source_id = normalize_protocol(source.get("source_id"))

    return (
        "interno" in protocol
        or "internal" in protocol
        or "simulação" in source_type
        or "simulacao" in source_type
        or "simulation" in source_type
        or "bancada" in source_id
        or "virtual" in source_id
    )


def _is_csv_source(source: dict[str, Any]) -> bool:
    protocol = normalize_protocol(source.get("protocol"))
    source_type = normalize_protocol(source.get("source_type"))

    return "csv" in protocol or "manual" in protocol or "arquivo" in source_type or "upload" in source_type


def validate_virtual_bench(source: dict[str, Any]) -> ValidationResult:
    source_id = source.get("source_id")

    if not source_id:
        return _result(False, "falha", "Bancada virtual sem source_id.", {"required": ["source_id"]})

    return _result(
        True,
        "ok",
        "Bancada virtual disponível e pronta para demonstração.",
        {
            "source_id": source_id,
            "protocol": source.get("protocol"),
            "source_type": source.get("source_type"),
            "contract_metrics": EXPECTED_CONTRACT_METRICS,
            "latency_ms": 0,
        },
    )


def validate_secret_reference(source: dict[str, Any]) -> ValidationResult:
    credential_ref = str(source.get("credential_ref") or "").strip()

    if _is_virtual_source(source) or _is_csv_source(source):
        return _result(
            True,
            "ok",
            "Esta fonte não exige credencial para o MVP.",
            {"credential_required": False, "secret_value_exposed": False},
        )

    if not credential_ref:
        return _result(
            False,
            "atenção",
            "Fonte sem referência de credencial. Para ambiente real, configure um cofre seguro.",
            {
                "credential_required": True,
                "accepted_examples": [
                    "aws_secrets/opcua_edge_bridge_01",
                    "env/OPCUA_BRIDGE_TOKEN",
                    "vault/industrial/client_x/source_y",
                    "ssm/path/to/secret",
                ],
                "secret_value_exposed": False,
            },
        )

    if not credential_ref.startswith(SAFE_CREDENTIAL_PREFIXES):
        return _result(
            False,
            "atenção",
            "Referência de credencial informada, mas fora do padrão recomendado.",
            {
                "credential_ref": credential_ref,
                "accepted_prefixes": SAFE_CREDENTIAL_PREFIXES,
                "security_note": "Não salve senha, token ou usuário/senha em texto puro.",
                "secret_value_exposed": False,
            },
        )

    return _result(
        True,
        "ok",
        "Referência de credencial configurada em formato seguro.",
        {"credential_ref": credential_ref, "secret_value_exposed": False},
    )


def validate_http_endpoint(source: dict[str, Any], timeout_sec: int = 5) -> ValidationResult:
    endpoint = str(source.get("endpoint") or "").strip()

    if not endpoint:
        return _result(False, "falha", "Endpoint vazio. Informe URL da bridge/API.", {"endpoint": endpoint})

    if not endpoint.lower().startswith(("http://", "https://")):
        return _result(
            False,
            "falha",
            "Endpoint não é HTTP/HTTPS. Para este teste, informe a URL da bridge.",
            {"endpoint": endpoint},
        )

    headers = {
        "User-Agent": "ConditionMonitoringMVP/1.0",
        "Accept": "application/json,text/plain,*/*",
    }
    start = time.perf_counter()

    try:
        request = urllib.request.Request(endpoint, method="GET", headers=headers)

        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(5000)
            preview = raw.decode("utf-8", errors="replace")[:500]
            ok = 200 <= status_code < 400

            return _result(
                ok,
                "ok" if ok else "atenção",
                f"Endpoint respondeu com HTTP {status_code}.",
                {
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "latency_ms": elapsed_ms,
                    "content_type": content_type,
                    "response_preview": preview,
                },
            )

    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return _result(
            False,
            "falha",
            f"Endpoint respondeu erro HTTP {exc.code}.",
            {
                "endpoint": endpoint,
                "status_code": exc.code,
                "latency_ms": elapsed_ms,
                "reason": str(exc.reason),
            },
        )

    except urllib.error.URLError as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return _result(
            False,
            "falha",
            "Não foi possível conectar ao endpoint.",
            {"endpoint": endpoint, "latency_ms": elapsed_ms, "reason": str(exc.reason)},
        )

    except Exception as exc:  # pragma: no cover - defensive boundary around network stack.
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return _result(
            False,
            "falha",
            "Erro inesperado ao testar endpoint.",
            {"endpoint": endpoint, "latency_ms": elapsed_ms, "error": str(exc)},
        )


def validate_tcp_endpoint(host: str, port: int, timeout_sec: int = 5) -> ValidationResult:
    start = time.perf_counter()

    try:
        with socket.create_connection((host, int(port)), timeout=timeout_sec):
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return _result(
                True,
                "ok",
                f"Porta TCP acessível em {host}:{port}.",
                {"host": host, "port": port, "latency_ms": elapsed_ms},
            )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return _result(
            False,
            "falha",
            f"Falha ao acessar {host}:{port}.",
            {"host": host, "port": port, "latency_ms": elapsed_ms, "error": str(exc)},
        )


def read_csv_preview(file_obj: Any, delimiter: str = ",", max_rows: int = 20) -> tuple[list[str], list[dict[str, Any]]]:
    if file_obj is None:
        return [], []

    if isinstance(file_obj, (str, Path)):
        text = Path(file_obj).read_text(encoding="utf-8-sig")
    else:
        raw = file_obj.getvalue() if hasattr(file_obj, "getvalue") else file_obj.read()
        text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else str(raw)

    sample = text[:2048]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        pass

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = [dict(row) for _, row in zip(range(max_rows), reader)]

    return reader.fieldnames or [], rows


def validate_csv_file(file_obj: Any, required_columns: list[str] | None = None) -> ValidationResult:
    required_columns = required_columns or CSV_REQUIRED_COLUMNS

    try:
        columns, rows = read_csv_preview(file_obj)
    except Exception as exc:
        return _result(False, "falha", "Erro ao ler CSV.", {"error": str(exc)})

    if not columns:
        return _result(
            False,
            "falha",
            "CSV sem cabeçalho ou vazio.",
            {"required_columns": required_columns},
        )

    missing = [column for column in required_columns if column not in columns]

    if missing:
        return _result(
            False,
            "atenção",
            "CSV lido, mas há colunas obrigatórias ausentes.",
            {
                "columns_found": columns,
                "missing_columns": missing,
                "rows_preview_count": len(rows),
                "preview": rows[:3],
            },
        )

    return _result(
        True,
        "ok",
        "CSV lido com sucesso e colunas obrigatórias encontradas.",
        {
            "columns_found": columns,
            "required_columns": required_columns,
            "rows_preview_count": len(rows),
            "preview": rows[:3],
        },
    )


def validate_signal_map_for_csv(
    signal_map: list[dict[str, Any]],
    file_obj: Any,
    asset_id: str | None = None,
    source_id: str | None = None,
) -> ValidationResult:
    try:
        columns, rows = read_csv_preview(file_obj)
    except Exception as exc:
        return _result(False, "falha", "Erro ao validar mapeamento contra CSV.", {"error": str(exc)})

    maps = [signal for signal in signal_map if signal.get("enabled", True)]

    if source_id:
        maps = [signal for signal in maps if signal.get("source_id") == source_id]

    if asset_id:
        maps = [signal for signal in maps if signal.get("asset_id") == asset_id]

    if not maps:
        return _result(
            False,
            "atenção",
            "Nenhum mapeamento CSV habilitado para esta fonte/ativo.",
            {"source_id": source_id, "asset_id": asset_id, "columns_found": columns},
        )

    expected = [signal.get("external_tag") for signal in maps if signal.get("external_tag")]
    missing = [tag for tag in expected if tag not in columns]

    if missing:
        return _result(
            False,
            "atenção",
            "Algumas colunas mapeadas não foram encontradas no CSV.",
            {
                "asset_id": asset_id,
                "columns_found": columns,
                "expected_tags": expected,
                "missing_tags": missing,
            },
        )

    return _result(
        True,
        "ok",
        "Tags/colunas mapeadas encontradas no CSV.",
        {
            "asset_id": asset_id,
            "columns_found": columns,
            "expected_tags": expected,
            "rows_preview_count": len(rows),
        },
    )


def validate_signal_map_for_source(
    source: dict[str, Any],
    signal_map: list[dict[str, Any]],
    asset_id: str | None = None,
) -> ValidationResult:
    source_id = source.get("source_id")
    maps = [
        signal
        for signal in signal_map
        if signal.get("source_id") == source_id and signal.get("enabled", True)
    ]

    if asset_id:
        maps = [signal for signal in maps if signal.get("asset_id") == asset_id]

    if not maps:
        return _result(
            False,
            "atenção",
            "Nenhum sinal mapeado para esta fonte/ativo.",
            {"source_id": source_id, "asset_id": asset_id},
        )

    mapped_metrics = [_metric_name(signal) for signal in maps]
    missing_metrics = [metric for metric in MAIN_MAPPED_METRICS if metric not in mapped_metrics]
    missing_tags = [signal for signal in maps if not signal.get("external_tag")]

    if missing_tags:
        return _result(
            False,
            "atenção",
            "Há métricas sem tag externa configurada.",
            {"source_id": source_id, "asset_id": asset_id, "missing_external_tag": missing_tags},
        )

    if missing_metrics:
        return _result(
            False,
            "atenção",
            "Mapeamento existente, mas faltam métricas principais.",
            {
                "source_id": source_id,
                "asset_id": asset_id,
                "mapped_metrics": mapped_metrics,
                "missing_metrics": missing_metrics,
            },
        )

    return _result(
        True,
        "ok",
        "Mapeamento estrutural de sinais válido.",
        {
            "source_id": source_id,
            "asset_id": asset_id,
            "mapped_metrics": mapped_metrics,
            "mapped_count": len(maps),
        },
    )


def validate_source_connection(source: dict[str, Any]) -> ValidationResult:
    protocol = normalize_protocol(source.get("protocol"))

    if _is_virtual_source(source):
        return validate_virtual_bench(source)

    if _is_csv_source(source):
        return _result(
            True,
            "ok",
            "Fonte CSV/manual disponível. Use upload de arquivo para validar leitura e colunas.",
            {"source_id": source.get("source_id"), "protocol": source.get("protocol")},
        )

    if "http" in protocol or "https" in protocol:
        return validate_http_endpoint(source)

    if "mqtt" in protocol:
        return _result(
            False,
            "pendente",
            "Validação MQTT será implementada com teste de broker/tópico.",
            {"source_id": source.get("source_id"), "protocol": source.get("protocol")},
        )

    if "modbus" in protocol:
        return _result(
            False,
            "pendente",
            "Validação Modbus TCP será implementada com teste host/porta e leitura de registrador.",
            {"source_id": source.get("source_id"), "protocol": source.get("protocol")},
        )

    return _result(
        False,
        "atenção",
        "Protocolo não reconhecido para validação automática.",
        {"source_id": source.get("source_id"), "protocol": source.get("protocol")},
    )
