from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


def decimal_to_native(value: Any) -> Any:
    if isinstance(value, Decimal):
        number = float(value)
        if number.is_integer():
            return int(number)
        return number

    if isinstance(value, dict):
        return {key: decimal_to_native(item) for key, item in value.items()}

    if isinstance(value, list):
        return [decimal_to_native(item) for item in value]

    return value


class DashboardRepository:
    def __init__(
        self,
        state_table_name: str,
        alerts_table_name: str,
        region_name: str,
        profile_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if dynamodb_resource is None:
            if profile_name:
                session = boto3.Session(profile_name=profile_name, region_name=region_name)
            else:
                session = boto3.Session(region_name=region_name)

            dynamodb_resource = session.resource("dynamodb")

        self.state_table = dynamodb_resource.Table(state_table_name)
        self.alerts_table = dynamodb_resource.Table(alerts_table_name)

    def get_latest_state(self, tenant_id: str, asset_id: str) -> dict[str, Any] | None:
        key = {
            "pk": f"TENANT#{tenant_id}#ASSET#{asset_id}",
            "sk": "LATEST",
        }

        result = self.state_table.get_item(Key=key)
        item = result.get("Item")

        if not item:
            return None

        return decimal_to_native(item)

    def get_active_alerts(self, tenant_id: str, asset_id: str) -> list[dict[str, Any]]:
        pk = f"TENANT#{tenant_id}#ASSET#{asset_id}"

        result = self.alerts_table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("ALERT#ACTIVE#"),
        )

        items = result.get("Items", [])
        return [decimal_to_native(item) for item in items]


def create_repository_from_env() -> DashboardRepository:
    return DashboardRepository(
        state_table_name=os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev"),
        alerts_table_name=os.getenv("ALERTS_TABLE", "mvp_alerts_dev"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        profile_name=os.getenv("AWS_PROFILE") or None,
    )
