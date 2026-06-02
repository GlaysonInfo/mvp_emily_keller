from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

try:
    from dashboard.dynamodb_repository import normalize_active_alert_item, tenant_plant_key
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.dynamodb_repository import normalize_active_alert_item, tenant_plant_key


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def from_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        number = float(value)
        if number.is_integer():
            return int(number)
        return number

    if isinstance(value, dict):
        return {key: from_decimal(item) for key, item in value.items()}

    if isinstance(value, list):
        return [from_decimal(item) for item in value]

    return value


def to_decimal(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {key: to_decimal(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_decimal(item) for item in value]

    return value


def alerts_table_name_from_env() -> str:
    return os.getenv("CONDITION_ALERTS_TABLE") or os.getenv("ALERTS_TABLE", "condition_alerts")


def region_from_env() -> str:
    return os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def severity_from_status_label(status_label: str) -> str:
    normalized = status_label.upper()

    if normalized in {"CRÍTICO", "CRITICO"}:
        return "critical"

    if normalized in {"ATENÇÃO", "ATENCAO", "ALERTA", "SEM COMUNICAÇÃO", "SEM COMUNICACAO"}:
        return "warning"

    return "normal"


class AlertsRepository:
    """
    Repositório operacional de alertas.

    O esquema preferencial da etapa atual é:
      CONDITION_ALERTS_TABLE=condition_alerts
      PK: tenant_asset  ex.: cliente_demo#motor_001
      SK: alert_key     ex.: open#vibration_rms_mm_s

    Para manter compatibilidade com a tabela antiga, a leitura também tenta o
    esquema pk/sk usado por mvp_alerts_dev quando o DynamoDB rejeita a chave nova.
    """

    def __init__(
        self,
        table_name: str | None = None,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if dynamodb_resource is None:
            session = boto3.Session(
                profile_name=profile_name or os.getenv("AWS_PROFILE") or None,
                region_name=region_name or region_from_env(),
            )
            dynamodb_resource = session.resource("dynamodb")

        self.table = dynamodb_resource.Table(table_name or alerts_table_name_from_env())

    @staticmethod
    def tenant_asset(tenant_id: str, asset_id: str) -> str:
        return f"{tenant_id}#{asset_id}"

    @staticmethod
    def legacy_pk(tenant_id: str, asset_id: str) -> str:
        return f"TENANT#{tenant_id}#ASSET#{asset_id}"

    def _collect_pages(self, operation: str, kwargs: dict[str, Any]) -> list[dict[str, Any]]:
        method = getattr(self.table, operation)
        result = method(**kwargs)
        items = list(result.get("Items", []))

        while "LastEvaluatedKey" in result:
            result = method(**{**kwargs, "ExclusiveStartKey": result["LastEvaluatedKey"]})
            items.extend(result.get("Items", []))

        return [from_decimal(item) for item in items]

    @staticmethod
    def _tenant_plant_index() -> str:
        return os.getenv("CONDITION_ALERTS_TENANT_PLANT_INDEX") or os.getenv(
            "ALERTS_TENANT_PLANT_INDEX",
            "tenant_plant_index",
        )

    def _query_by_asset(
        self,
        tenant_id: str,
        asset_id: str,
        status: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        filter_expression = None if not status or status == "Todos" else Attr("status").eq(status)
        tenant_asset = self.tenant_asset(tenant_id, asset_id)

        kwargs: dict[str, Any] = {"KeyConditionExpression": Key("tenant_asset").eq(tenant_asset)}
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression

        try:
            return self._filter_active_alerts(self._collect_pages("query", kwargs), active_only=active_only)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ValidationException":
                raise

        legacy_kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("pk").eq(self.legacy_pk(tenant_id, asset_id)) & Key("sk").begins_with("ALERT#")
        }
        if filter_expression is not None:
            legacy_kwargs["FilterExpression"] = filter_expression

        return self._filter_active_alerts(self._collect_pages("query", legacy_kwargs), active_only=active_only)

    @staticmethod
    def _filter_active_alerts(items: list[dict[str, Any]], *, active_only: bool) -> list[dict[str, Any]]:
        if not active_only:
            return items

        active_items: list[dict[str, Any]] = []
        for item in items:
            status = str(item.get("status") or "").strip().lower()
            if status in {"resolved", "closed"}:
                continue

            sk = str(item.get("sk") or "")
            alert_key = str(item.get("alert_key") or "")
            if sk.startswith("ALERT#ACTIVE#") or alert_key.startswith(("open#", "acknowledged#", "in_progress#")):
                active_items.append(item)
                continue

            if status in {"open", "acknowledged", "in_progress", "active"}:
                active_items.append(item)

        return active_items

    def list_alerts(
        self,
        tenant_id: str,
        plant_id: str | None = None,
        asset_id: str | None = None,
        status: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        if asset_id:
            return self._query_by_asset(tenant_id, asset_id, status=status, active_only=active_only)

        if plant_id:
            query_kwargs: dict[str, Any] = {
                "IndexName": self._tenant_plant_index(),
                "KeyConditionExpression": Key("tenant_plant").eq(tenant_plant_key(tenant_id, plant_id)),
            }
            if status and status != "Todos":
                query_kwargs["FilterExpression"] = Attr("status").eq(status)

            try:
                return self._filter_active_alerts(
                    self._collect_pages("query", query_kwargs),
                    active_only=active_only,
                )
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") != "ValidationException":
                    raise

        filter_expression = Attr("tenant_id").eq(tenant_id)

        if plant_id:
            filter_expression = filter_expression & Attr("plant_id").eq(plant_id)

        if status and status != "Todos":
            filter_expression = filter_expression & Attr("status").eq(status)

        return self._filter_active_alerts(
            self._collect_pages("scan", {"FilterExpression": filter_expression}),
            active_only=active_only,
        )

    def get_alert(
        self,
        tenant_asset: str,
        alert_key: str,
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = self.table.get_item(Key={"tenant_asset": tenant_asset, "alert_key": alert_key})
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ValidationException":
                raise
            result = {}

        item = result.get("Item")
        if item:
            return from_decimal(item)

        if pk and sk:
            result = self.table.get_item(Key={"pk": pk, "sk": sk})
            return from_decimal(result.get("Item", {}))

        return {}

    def _key_for_item(
        self,
        item: dict[str, Any],
        tenant_asset: str,
        alert_key: str,
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict[str, str]:
        if item.get("tenant_asset") and item.get("alert_key"):
            return {"tenant_asset": str(item["tenant_asset"]), "alert_key": str(item["alert_key"])}

        if item.get("pk") and item.get("sk"):
            return {"pk": str(item["pk"]), "sk": str(item["sk"])}

        if pk and sk:
            return {"pk": pk, "sk": sk}

        return {"tenant_asset": tenant_asset, "alert_key": alert_key}

    def update_status(
        self,
        tenant_asset: str,
        alert_key: str,
        new_status: str,
        user_name: str,
        note: str = "",
        action_taken: str = "",
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict[str, Any]:
        item = self.get_alert(tenant_asset, alert_key, pk=pk, sk=sk)
        if not item:
            raise RuntimeError("Alerta não encontrado.")

        ts = now_utc()
        timeline = item.get("timeline", [])
        if not isinstance(timeline, list):
            timeline = []

        timeline.append(
            {
                "at": ts,
                "by": user_name,
                "from_status": item.get("status"),
                "to_status": new_status,
                "note": note,
                "action_taken": action_taken,
            }
        )

        fields: dict[str, Any] = {
            "status": new_status,
            "last_status_update_at": ts,
            "last_status_update_by": user_name,
            "last_note": note,
            "last_action_taken": action_taken,
            "timeline": timeline,
        }

        if new_status == "acknowledged":
            fields["acknowledged_at"] = ts
            fields["acknowledged_by"] = user_name
        elif new_status == "in_progress":
            fields["in_progress_at"] = ts
            fields["in_progress_by"] = user_name
        elif new_status == "resolved":
            fields["resolved_at"] = ts
            fields["resolved_by"] = user_name
        elif new_status == "closed":
            fields["closed_at"] = ts
            fields["closed_by"] = user_name

        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        sets: list[str] = []

        for index, (key, value) in enumerate(fields.items()):
            names[f"#k{index}"] = key
            values[f":v{index}"] = to_decimal(value)
            sets.append(f"#k{index} = :v{index}")

        self.table.update_item(
            Key=self._key_for_item(item, tenant_asset, alert_key, pk=pk, sk=sk),
            UpdateExpression="SET " + ", ".join(sets),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

        return self.get_alert(tenant_asset, alert_key, pk=pk, sk=sk)

    def create_manual_alert(
        self,
        tenant_id: str,
        plant_id: str,
        asset_id: str,
        asset_name: str,
        metric: str,
        status_label: str,
        value: float | None,
        threshold: float | None,
        recommended_action: str,
        created_by: str = "operador_demo",
        note: str = "",
    ) -> dict[str, Any]:
        if not str(recommended_action or "").strip():
            raise ValueError("Informe uma ação recomendada antes de criar o evento.")

        ts = now_utc()
        tenant_asset = self.tenant_asset(tenant_id, asset_id)
        alert_key = f"open#manual#{metric}#{ts}"
        status_label = status_label or "ATENÇÃO"
        item = {
            "pk": self.legacy_pk(tenant_id, asset_id),
            "sk": f"ALERT#ACTIVE#MANUAL#{metric}#{ts}",
            "tenant_asset": tenant_asset,
            "tenant_plant": tenant_plant_key(tenant_id, plant_id),
            "alert_key": alert_key,
            "alert_id": f"{tenant_id}#{asset_id}#{metric}#manual#{ts}",
            "tenant_id": tenant_id,
            "plant_id": plant_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "alert_type": "manual_event",
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "severity": severity_from_status_label(status_label),
            "status_label": status_label,
            "status": "open",
            "probable_cause": metric,
            "confidence": 1.0,
            "evidence": [note] if note else ["Evento manual criado."],
            "first_detected_at": ts,
            "last_detected_at": ts,
            "updated_at": ts,
            "recommended_action": recommended_action,
            "created_by": created_by,
            "note": note,
            "timeline": [
                {
                    "at": ts,
                    "by": created_by,
                    "from_status": None,
                    "to_status": "open",
                    "note": note,
                    "action_taken": "Evento manual criado.",
                }
            ],
        }

        normalized_item = normalize_active_alert_item(item)
        self.table.put_item(Item=to_decimal(normalized_item))
        return normalized_item


def create_alerts_repository_from_env() -> AlertsRepository:
    try:
        from dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled
    except ImportError:  # pragma: no cover - supports streamlit run from repository root.
        from src.dashboard.local_demo_repository import create_local_demo_repository, local_demo_enabled

    if local_demo_enabled():
        return create_local_demo_repository()  # type: ignore[return-value]

    return AlertsRepository()
