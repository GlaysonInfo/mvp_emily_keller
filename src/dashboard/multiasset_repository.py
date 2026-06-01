from __future__ import annotations

import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

try:
    from dashboard.dynamodb_repository import decimal_to_native, tenant_plant_key
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.dynamodb_repository import decimal_to_native, tenant_plant_key


def state_table_name_from_env() -> str:
    return os.getenv("DYNAMODB_STATE_TABLE") or os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev")


def region_from_env() -> str:
    return os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


class MultiAssetRepository:
    """Consulta a tabela de estado atual para montar a visão de planta.

    Para a Sprint 1, usamos scan filtrando por tenant/planta. Isso é suficiente
    para demonstração e pode evoluir para um GSI por `tenant_plant`.
    """

    def __init__(
        self,
        table_name: str,
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

        self.table = dynamodb_resource.Table(table_name)

    @staticmethod
    def _tenant_plant_index() -> str:
        return os.getenv("STATE_TENANT_PLANT_INDEX", "tenant_plant_index")

    def list_current_states(self, tenant_id: str, plant_id: str) -> list[dict[str, Any]]:
        filter_expression = (
            Attr("tenant_id").eq(tenant_id)
            & Attr("plant_id").eq(plant_id)
            & Attr("sk").eq("LATEST")
        )

        try:
            query_kwargs: dict[str, Any] = {
                "IndexName": self._tenant_plant_index(),
                "KeyConditionExpression": Key("tenant_plant").eq(tenant_plant_key(tenant_id, plant_id)),
                "FilterExpression": Attr("sk").eq("LATEST"),
            }
            response = self.table.query(**query_kwargs)
            items = list(response.get("Items", []))

            while "LastEvaluatedKey" in response:
                response = self.table.query(
                    **query_kwargs,
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            return [decimal_to_native(item) for item in items]
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code") or "") != "ValidationException":
                raise

        response = self.table.scan(FilterExpression=filter_expression)
        items = list(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                FilterExpression=filter_expression,
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        return [decimal_to_native(item) for item in items]


def create_multiasset_repository_from_env() -> MultiAssetRepository:
    try:
        from dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled
    except ImportError:  # pragma: no cover - supports streamlit run from repository root.
        from src.dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled

    if local_demo_enabled():
        return create_local_demo_repository()  # type: ignore[return-value]

    return MultiAssetRepository(
        table_name=state_table_name_from_env(),
        region_name=region_from_env(),
        profile_name=os.getenv("AWS_PROFILE") or None,
    )
