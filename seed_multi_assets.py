from __future__ import annotations

import json
import os
from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound


DATA_FILE = Path(__file__).parent / "src" / "dashboard" / "demo_multiasset_states.json"

UNIT_BY_METRIC = {
    "rpm": "rpm",
    "vibration_rms_mm_s": "mm/s",
    "temperature_c": "C",
    "ultrasound_db": "dB",
    "kurtosis_index": "index",
    "crest_factor_index": "index",
    "vibration_peak_g": "g",
    "hourmeter_h": "h",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def table_name_from_env() -> str:
    return os.getenv("DYNAMODB_STATE_TABLE") or os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev")


def region_from_env() -> str:
    return os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def to_dynamodb_safe(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value

    if isinstance(value, int | float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {key: to_dynamodb_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_dynamodb_safe(item) for item in value]

    return value


def build_metric_map(raw_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}

    for name, value in raw_metrics.items():
        metrics[name] = {
            "value": value,
            "unit": UNIT_BY_METRIC.get(name, ""),
        }

    return metrics


def build_state_item(state: dict[str, Any], updated_at: str | None = None) -> dict[str, Any]:
    tenant_id = str(state.get("tenant_id", "cliente_demo"))
    plant_id = str(state.get("plant_id", "lab_virtual"))
    asset_id = str(state["asset_id"])
    state_updated_at = updated_at or utc_now_iso()
    metrics = state.get("metrics")
    metric_map = build_metric_map(metrics if isinstance(metrics, dict) else {})

    item = dict(state)
    item.update(
        {
            "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
            "sk": "LATEST",
            "tenant_id": tenant_id,
            "plant_id": plant_id,
            "asset_id": asset_id,
            "tenant_plant": f"{tenant_id}#{plant_id}",
            "updated_at": state_updated_at,
            "received_at": state_updated_at,
            "failure_mode_simulated": state.get("mode"),
            "source": state.get("source", "demo_multiasset_loader"),
            "loaded_by": "demo_multiasset_loader",
            "event_id": f"multiasset-demo-{asset_id}",
            "is_demo_multiasset": True,
            "metrics": metric_map,
        }
    )

    return to_dynamodb_safe(item)


def get_table() -> Any:
    session = boto3.Session(
        profile_name=os.getenv("AWS_PROFILE") or None,
        region_name=region_from_env(),
    )
    return session.resource("dynamodb").Table(table_name_from_env())


def load_states(path: Path = DATA_FILE) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Carrega estados multiativos de demonstração no DynamoDB.")
    parser.add_argument("--list", action="store_true", help="Lista os ativos do pacote sem gravar no DynamoDB.")
    parser.add_argument("--data-file", type=Path, default=DATA_FILE, help="Caminho do JSON de estados multiativos.")
    return parser.parse_args()


def print_state_list(states: list[dict[str, Any]]) -> None:
    for state in states:
        print(
            f"{state.get('asset_id')} | {state.get('asset_name')} | "
            f"{state.get('asset_type')} | {state.get('status_label')} | "
            f"Health={state.get('health_score')}"
        )

    print(f"\nTotal: {len(states)} ativo(s).")


def main() -> None:
    args = parse_args()

    try:
        states = load_states(args.data_file)

        if args.list:
            print_state_list(states)
            return

        table = get_table()

        for state in states:
            item = build_state_item(state)
            table.put_item(Item=item)
            print(
                "OK: "
                f"{item['asset_id']} | {item.get('asset_name')} | {item.get('status_label')} | "
                f"Health={item.get('health_score')}"
            )

        print(f"\nTotal carregado: {len(states)} ativo(s).")
        print(f"Tabela: {table_name_from_env()} | Região: {region_from_env()}")
    except ProfileNotFound as exc:
        print(f"ERRO: profile AWS não encontrado: {exc}")
    except NoCredentialsError:
        print("ERRO: credenciais AWS não encontradas.")
    except ClientError as exc:
        print(f"ERRO AWS/DynamoDB: {exc}")
    except Exception as exc:
        print(f"ERRO: {exc}")


if __name__ == "__main__":
    main()
