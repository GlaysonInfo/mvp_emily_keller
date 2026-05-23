from __future__ import annotations

import argparse
import os
from typing import Any

from botocore.exceptions import ClientError, NoCredentialsError

from src.dashboard.demo_cases import (
    build_demo_alert_item,
    build_latest_state_item,
    get_demo_case,
    load_demo_cases,
)
from src.dashboard.dynamodb_repository import DashboardRepository


def env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)

        if value:
            return value

    return default


def create_repository(args: argparse.Namespace) -> DashboardRepository:
    state_table = args.state_table or env_first("DYNAMODB_TABLE", "DYNAMODB_STATE_TABLE")
    alerts_table = args.alerts_table or env_first("ALERTS_TABLE")
    region = args.region or env_first("AWS_REGION", "AWS_DEFAULT_REGION", default="us-east-1")
    profile = args.profile or os.getenv("AWS_PROFILE")

    if not state_table:
        raise RuntimeError("Defina DYNAMODB_TABLE ou use --state-table.")

    if not alerts_table:
        raise RuntimeError("Defina ALERTS_TABLE ou use --alerts-table.")

    return DashboardRepository(
        state_table_name=state_table,
        alerts_table_name=alerts_table,
        region_name=region or "us-east-1",
        profile_name=profile or None,
    )


def load_case(repo: DashboardRepository, case: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    state_item = build_latest_state_item(
        case,
        tenant_id=args.tenant_id,
        plant_id=args.plant_id,
        asset_id=args.asset_id,
    )
    alert_item = build_demo_alert_item(
        case,
        tenant_id=args.tenant_id,
        plant_id=args.plant_id,
        asset_id=args.asset_id,
        payload_updated_at=str(state_item["updated_at"]),
    )

    repo.put_latest_state(state_item)
    repo.clear_demo_alerts(tenant_id=args.tenant_id, asset_id=args.asset_id)

    if alert_item:
        repo.put_active_alert(alert_item)

    return state_item


def main() -> int:
    parser = argparse.ArgumentParser(description="Carrega cenarios de demonstracao no DynamoDB.")
    parser.add_argument("--list", action="store_true", help="Lista os cenarios disponiveis.")
    parser.add_argument("--case", help="Carrega um cenario especifico pelo case_id.")
    parser.add_argument("--all", action="store_true", help="Carrega todos os cenarios em sequencia.")
    parser.add_argument("--tenant-id", default=os.getenv("TENANT_ID", "cliente_demo"))
    parser.add_argument("--plant-id", default=os.getenv("PLANT_ID", "lab_virtual"))
    parser.add_argument("--asset-id", default=os.getenv("ASSET_ID", "motor_001"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--region", default=env_first("AWS_REGION", "AWS_DEFAULT_REGION", default="us-east-1"))
    parser.add_argument("--state-table", default=env_first("DYNAMODB_TABLE", "DYNAMODB_STATE_TABLE"))
    parser.add_argument("--alerts-table", default=os.getenv("ALERTS_TABLE"))
    args = parser.parse_args()

    cases = load_demo_cases()

    if args.list:
        for case in cases:
            print(f"{case['presentation_order']}. {case['case_id']} - {case['case_name']}")

        return 0

    if not args.case and not args.all:
        parser.error("Use --list, --case CASE_ID ou --all.")

    try:
        repo = create_repository(args)

        selected_cases = cases if args.all else [get_demo_case(args.case)]

        for case in selected_cases:
            item = load_case(repo, case, args)
            print(f"OK: {case['case_id']} - {case['case_name']}")
            print(f"Tenant: {item['tenant_id']} | Asset: {item['asset_id']} | Atualizado em: {item['updated_at']}")

        if args.all:
            print("Observacao: como a tabela usa sk=LATEST, o ultimo cenario fica visivel no dashboard.")

        return 0
    except NoCredentialsError:
        print("ERRO: Credenciais AWS nao encontradas. Rode aws configure ou defina AWS_PROFILE.")
    except ClientError as error:
        print(f"ERRO AWS/DynamoDB: {error}")
    except Exception as error:
        print(f"ERRO: {error}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
