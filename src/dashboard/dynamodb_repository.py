from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError


DEFAULT_RECOMMENDED_ACTION = (
    "Realizar inspeção técnica no ativo, registrar evidências e avaliar necessidade de intervenção corretiva "
    "ou preventiva."
)


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


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code") or "")


def _metric_from_alert(item: dict[str, Any]) -> str:
    if item.get("metric"):
        return str(item["metric"])

    if item.get("alert_type"):
        return str(item["alert_type"])

    sk = str(item.get("sk") or "")
    prefix = "ALERT#ACTIVE#"
    if sk.startswith(prefix):
        return sk[len(prefix) :]

    return "alert"


def _status_label_from_severity(severity: Any) -> str:
    normalized = str(severity or "").strip().lower()

    if normalized == "critical":
        return "CRÍTICO"

    if normalized == "normal":
        return "NORMAL"

    return "ATENÇÃO"


def _condition_alert_key(item: dict[str, Any], metric: str) -> str:
    status = str(item.get("status") or "open").lower()

    if item.get("is_demo_case"):
        source = "demo"
    elif item.get("is_e2e_test"):
        source = "e2e"
    else:
        source = "dashboard"

    return f"{status}#{source}#{metric}"


def tenant_plant_key(tenant_id: Any, plant_id: Any) -> str:
    return f"{tenant_id}#{plant_id}"


def normalize_active_alert_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    tenant_id = normalized.get("tenant_id")
    plant_id = normalized.get("plant_id")
    asset_id = normalized.get("asset_id")
    metric = _metric_from_alert(normalized)

    if tenant_id and asset_id:
        normalized.setdefault("pk", f"TENANT#{tenant_id}#ASSET#{asset_id}")
        normalized.setdefault("tenant_asset", f"{tenant_id}#{asset_id}")

    if tenant_id and plant_id:
        normalized.setdefault("tenant_plant", tenant_plant_key(tenant_id, plant_id))

    normalized.setdefault("sk", f"ALERT#ACTIVE#{metric}")
    normalized.setdefault("alert_key", _condition_alert_key(normalized, metric))
    normalized.setdefault("metric", metric)
    normalized.setdefault("status", "open")
    normalized.setdefault("status_label", _status_label_from_severity(normalized.get("severity")))

    if asset_id:
        normalized.setdefault("asset_name", str(asset_id))

    detected_at = normalized.get("last_detected_at") or normalized.get("updated_at") or normalized.get("first_detected_at")
    if detected_at:
        normalized["last_detected_at"] = detected_at

    if not str(normalized.get("recommended_action") or "").strip():
        normalized["recommended_action"] = DEFAULT_RECOMMENDED_ACTION

    return normalized


def _delete_keys_for_alert(alert: dict[str, Any]) -> list[dict[str, str]]:
    keys: list[dict[str, str]] = []

    if alert.get("pk") and alert.get("sk"):
        keys.append({"pk": str(alert["pk"]), "sk": str(alert["sk"])})

    if alert.get("tenant_asset") and alert.get("alert_key"):
        keys.append({"tenant_asset": str(alert["tenant_asset"]), "alert_key": str(alert["alert_key"])})

    return keys


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

    @staticmethod
    def _alerts_tenant_plant_index() -> str:
        return os.getenv("ALERTS_TENANT_PLANT_INDEX") or os.getenv(
            "CONDITION_ALERTS_TENANT_PLANT_INDEX",
            "tenant_plant_index",
        )

    @staticmethod
    def _normalize_latest_state_item(item: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(item)
        tenant_id = normalized.get("tenant_id")
        plant_id = normalized.get("plant_id")
        if tenant_id and plant_id:
            normalized.setdefault("tenant_plant", tenant_plant_key(tenant_id, plant_id))
        return normalized

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

        try:
            result = self.alerts_table.query(
                KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("ALERT#ACTIVE#"),
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ValidationException":
                raise

            result = self.alerts_table.query(
                KeyConditionExpression=Key("tenant_asset").eq(f"{tenant_id}#{asset_id}"),
            )

        items = result.get("Items", [])
        return [decimal_to_native(item) for item in items]

    def list_alerts(self, tenant_id: str, plant_id: str, *, active_only: bool = False) -> list[dict[str, Any]]:
        filter_expression = Attr("tenant_id").eq(tenant_id) & Attr("plant_id").eq(plant_id)

        if active_only:
            filter_expression = filter_expression & Attr("sk").begins_with("ALERT#ACTIVE#")

        try:
            query_kwargs: dict[str, Any] = {
                "IndexName": self._alerts_tenant_plant_index(),
                "KeyConditionExpression": Key("tenant_plant").eq(tenant_plant_key(tenant_id, plant_id)),
            }
            if active_only:
                query_kwargs["FilterExpression"] = Attr("sk").begins_with("ALERT#ACTIVE#")
            result = self.alerts_table.query(**query_kwargs)
            items = list(result.get("Items", []))

            while "LastEvaluatedKey" in result:
                result = self.alerts_table.query(
                    **query_kwargs,
                    ExclusiveStartKey=result["LastEvaluatedKey"],
                )
                items.extend(result.get("Items", []))

            return [decimal_to_native(item) for item in items]
        except ClientError as exc:
            if _client_error_code(exc) != "ValidationException":
                raise

        result = self.alerts_table.scan(FilterExpression=filter_expression)
        items = list(result.get("Items", []))

        while "LastEvaluatedKey" in result:
            result = self.alerts_table.scan(
                FilterExpression=filter_expression,
                ExclusiveStartKey=result["LastEvaluatedKey"],
            )
            items.extend(result.get("Items", []))

        return [decimal_to_native(item) for item in items]

    def put_latest_state(self, item: dict[str, Any]) -> None:
        self.state_table.put_item(Item=self._normalize_latest_state_item(item))

    def put_active_alert(self, item: dict[str, Any]) -> None:
        self.alerts_table.put_item(Item=normalize_active_alert_item(item))

    def clear_demo_alerts(self, tenant_id: str, asset_id: str) -> int:
        active_alerts = self.get_active_alerts(tenant_id=tenant_id, asset_id=asset_id)
        deleted = 0

        for alert in active_alerts:
            if not alert.get("is_demo_case"):
                continue

            delete_keys = _delete_keys_for_alert(alert)
            if not delete_keys:
                continue

            for index, key in enumerate(delete_keys):
                try:
                    self.alerts_table.delete_item(Key=key)
                    break
                except ClientError as exc:
                    if _client_error_code(exc) != "ValidationException" or index == len(delete_keys) - 1:
                        raise

            deleted += 1

        return deleted


def state_table_name_from_env() -> str:
    return os.getenv("DYNAMODB_STATE_TABLE") or os.getenv("DYNAMODB_TABLE", "mvp_asset_state_dev")


def alerts_table_name_from_env() -> str:
    return os.getenv("ALERTS_TABLE") or os.getenv("CONDITION_ALERTS_TABLE", "mvp_alerts_dev")


def create_repository_from_env() -> DashboardRepository:
    try:
        from dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled
    except ImportError:  # pragma: no cover - supports streamlit run from repository root.
        from src.dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled

    if local_demo_enabled():
        return create_local_demo_repository()  # type: ignore[return-value]

    return DashboardRepository(
        state_table_name=state_table_name_from_env(),
        alerts_table_name=alerts_table_name_from_env(),
        region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        profile_name=os.getenv("AWS_PROFILE") or None,
    )
