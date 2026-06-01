from __future__ import annotations

import unittest
from decimal import Decimal

from botocore.exceptions import ClientError

from src.dashboard.dynamodb_repository import (
    DashboardRepository,
    alerts_table_name_from_env,
    decimal_to_native,
    normalize_active_alert_item,
    state_table_name_from_env,
)


class FakeTable:
    def __init__(
        self,
        *,
        item: dict | None = None,
        items: list[dict] | None = None,
        fail_tenant_plant_query: bool = False,
    ) -> None:
        self.item = item
        self.items = items or []
        self.fail_tenant_plant_query = fail_tenant_plant_query
        self.get_requests: list[dict] = []
        self.query_requests: list[dict] = []
        self.put_items: list[dict] = []
        self.delete_requests: list[dict] = []
        self.scan_requests: list[dict] = []

    def get_item(self, **kwargs) -> dict:
        self.get_requests.append(kwargs)
        if self.item is None:
            return {}
        return {"Item": self.item}

    def query(self, **kwargs) -> dict:
        self.query_requests.append(kwargs)
        if self.fail_tenant_plant_query and kwargs.get("IndexName") == "tenant_plant_index":
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Index not found"}},
                "Query",
            )
        return {"Items": self.items}

    def scan(self, **kwargs) -> dict:
        self.scan_requests.append(kwargs)
        return {"Items": self.items}

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {}

    def delete_item(self, **kwargs) -> dict:
        self.delete_requests.append(kwargs)
        return {}


class FallbackAlertsTable(FakeTable):
    def query(self, **kwargs) -> dict:
        self.query_requests.append(kwargs)

        if len(self.query_requests) == 1:
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid key condition"}},
                "Query",
            )

        return {"Items": self.items}


class FallbackDeleteAlertsTable(FallbackAlertsTable):
    def delete_item(self, **kwargs) -> dict:
        self.delete_requests.append(kwargs)

        if "pk" in kwargs.get("Key", {}):
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid key"}},
                "DeleteItem",
            )

        return {}


class FakeDynamoResource:
    def __init__(self, state_table: FakeTable, alerts_table: FakeTable) -> None:
        self.state_table = state_table
        self.alerts_table = alerts_table

    def Table(self, table_name: str) -> FakeTable:
        if table_name == "mvp_asset_state_dev":
            return self.state_table

        if table_name == "mvp_alerts_dev":
            return self.alerts_table

        if table_name == "condition_alerts":
            return self.alerts_table

        raise ValueError(f"Unexpected table: {table_name}")


class DashboardRepositoryTest(unittest.TestCase):
    def test_decimal_to_native_converts_nested_values(self) -> None:
        data = {
            "rpm": Decimal("1778.50"),
            "count": Decimal("2"),
            "values": [Decimal("1.25")],
        }

        converted = decimal_to_native(data)

        self.assertEqual(converted["rpm"], 1778.5)
        self.assertEqual(converted["count"], 2)
        self.assertEqual(converted["values"], [1.25])

    def test_get_latest_state_returns_native_item(self) -> None:
        state_table = FakeTable(
            item={
                "pk": "TENANT#cliente_demo#ASSET#motor_001",
                "sk": "LATEST",
                "metrics": {
                    "rpm": {"value": Decimal("1780.0"), "unit": "rpm"},
                },
            }
        )
        alerts_table = FakeTable()
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(state_table, alerts_table),
        )

        item = repo.get_latest_state("cliente_demo", "motor_001")

        self.assertIsNotNone(item)
        self.assertEqual(item["metrics"]["rpm"]["value"], 1780)
        self.assertEqual(
            state_table.get_requests[0]["Key"],
            {
                "pk": "TENANT#cliente_demo#ASSET#motor_001",
                "sk": "LATEST",
            },
        )

    def test_get_latest_state_returns_none_when_missing(self) -> None:
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), FakeTable()),
        )

        self.assertIsNone(repo.get_latest_state("cliente_demo", "motor_001"))

    def test_get_active_alerts_returns_native_items(self) -> None:
        alerts_table = FakeTable(
            items=[
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#lubrication_degradation",
                    "confidence": Decimal("0.76"),
                }
            ]
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        alerts = repo.get_active_alerts("cliente_demo", "motor_001")

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["confidence"], 0.76)
        self.assertEqual(len(alerts_table.query_requests), 1)

    def test_get_active_alerts_falls_back_to_condition_alerts_schema(self) -> None:
        alerts_table = FallbackAlertsTable(
            items=[
                {
                    "tenant_asset": "cliente_demo#motor_001",
                    "alert_key": "open#e2e#vibration_rms_mm_s",
                    "confidence": Decimal("1.0"),
                }
            ]
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="condition_alerts",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        alerts = repo.get_active_alerts("cliente_demo", "motor_001")

        self.assertEqual(alerts[0]["confidence"], 1)
        self.assertEqual(len(alerts_table.query_requests), 2)

    def test_list_alerts_queries_tenant_plant_index(self) -> None:
        alerts_table = FakeTable(
            items=[
                {
                    "tenant_id": "cliente_demo",
                    "plant_id": "lab_virtual",
                    "asset_id": "motor_001",
                    "confidence": Decimal("0.76"),
                }
            ]
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        alerts = repo.list_alerts("cliente_demo", "lab_virtual", active_only=True)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["confidence"], 0.76)
        self.assertEqual(len(alerts_table.query_requests), 1)
        self.assertEqual(alerts_table.query_requests[0]["IndexName"], "tenant_plant_index")
        self.assertEqual(alerts_table.scan_requests, [])

    def test_list_alerts_falls_back_to_scan_when_tenant_plant_index_is_missing(self) -> None:
        alerts_table = FakeTable(
            items=[
                {
                    "tenant_id": "cliente_demo",
                    "plant_id": "lab_virtual",
                    "asset_id": "motor_001",
                    "confidence": Decimal("0.76"),
                }
            ],
            fail_tenant_plant_query=True,
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        alerts = repo.list_alerts("cliente_demo", "lab_virtual", active_only=True)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(alerts_table.query_requests), 1)
        self.assertEqual(len(alerts_table.scan_requests), 1)

    def test_put_latest_state_writes_item(self) -> None:
        state_table = FakeTable()
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(state_table, FakeTable()),
        )
        item = {
            "pk": "TENANT#cliente_demo#ASSET#motor_001",
            "sk": "LATEST",
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
        }

        repo.put_latest_state(item)

        self.assertEqual(state_table.put_items[0]["tenant_plant"], "cliente_demo#lab_virtual")

    def test_normalize_active_alert_item_adds_condition_alert_keys(self) -> None:
        item = {
            "pk": "TENANT#cliente_demo#ASSET#motor_001",
            "sk": "ALERT#ACTIVE#thermal_stress",
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "asset_id": "motor_001",
            "severity": "warning",
            "is_demo_case": True,
        }

        normalized = normalize_active_alert_item(item)

        self.assertEqual(normalized["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(normalized["tenant_plant"], "cliente_demo#lab_virtual")
        self.assertEqual(normalized["alert_key"], "open#demo#thermal_stress")
        self.assertEqual(normalized["metric"], "thermal_stress")
        self.assertEqual(normalized["status_label"], "ATENÇÃO")
        self.assertEqual(normalized["asset_name"], "motor_001")
        self.assertTrue(normalized["recommended_action"])
        self.assertNotIn("tenant_asset", item)

    def test_put_active_alert_writes_dual_schema_item(self) -> None:
        alerts_table = FakeTable()
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="condition_alerts",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        repo.put_active_alert(
            {
                "pk": "TENANT#cliente_demo#ASSET#motor_001",
                "sk": "ALERT#ACTIVE#thermal_stress",
                "tenant_id": "cliente_demo",
                "plant_id": "lab_virtual",
                "asset_id": "motor_001",
                "severity": "warning",
                "is_demo_case": True,
            }
        )

        written = alerts_table.put_items[0]
        self.assertEqual(written["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(written["alert_key"], "open#demo#thermal_stress")
        self.assertEqual(written["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(written["sk"], "ALERT#ACTIVE#thermal_stress")

    def test_create_repository_from_env_prefers_e2e_table_aliases(self) -> None:
        import os

        old_state = os.environ.get("DYNAMODB_STATE_TABLE")
        old_table = os.environ.get("DYNAMODB_TABLE")
        old_alerts = os.environ.get("ALERTS_TABLE")
        old_condition_alerts = os.environ.get("CONDITION_ALERTS_TABLE")
        os.environ["DYNAMODB_STATE_TABLE"] = "state_alias"
        os.environ["DYNAMODB_TABLE"] = "state_legacy"
        os.environ.pop("ALERTS_TABLE", None)
        os.environ["CONDITION_ALERTS_TABLE"] = "condition_alerts"

        try:
            self.assertEqual(state_table_name_from_env(), "state_alias")
            self.assertEqual(alerts_table_name_from_env(), "condition_alerts")
        finally:
            if old_state is None:
                os.environ.pop("DYNAMODB_STATE_TABLE", None)
            else:
                os.environ["DYNAMODB_STATE_TABLE"] = old_state

            if old_table is None:
                os.environ.pop("DYNAMODB_TABLE", None)
            else:
                os.environ["DYNAMODB_TABLE"] = old_table

            if old_alerts is None:
                os.environ.pop("ALERTS_TABLE", None)
            else:
                os.environ["ALERTS_TABLE"] = old_alerts

            if old_condition_alerts is None:
                os.environ.pop("CONDITION_ALERTS_TABLE", None)
            else:
                os.environ["CONDITION_ALERTS_TABLE"] = old_condition_alerts

    def test_clear_demo_alerts_deletes_only_demo_alerts(self) -> None:
        alerts_table = FakeTable(
            items=[
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#demo",
                    "is_demo_case": True,
                },
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#real",
                    "is_demo_case": False,
                },
            ]
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        deleted = repo.clear_demo_alerts("cliente_demo", "motor_001")

        self.assertEqual(deleted, 1)
        self.assertEqual(
            alerts_table.delete_requests,
            [{"Key": {"pk": "TENANT#cliente_demo#ASSET#motor_001", "sk": "ALERT#ACTIVE#demo"}}],
        )

    def test_clear_demo_alerts_falls_back_to_condition_alerts_key(self) -> None:
        alerts_table = FallbackDeleteAlertsTable(
            items=[
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#thermal_stress",
                    "tenant_asset": "cliente_demo#motor_001",
                    "alert_key": "open#demo#thermal_stress",
                    "is_demo_case": True,
                }
            ]
        )
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="condition_alerts",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(FakeTable(), alerts_table),
        )

        deleted = repo.clear_demo_alerts("cliente_demo", "motor_001")

        self.assertEqual(deleted, 1)
        self.assertEqual(
            alerts_table.delete_requests,
            [
                {"Key": {"pk": "TENANT#cliente_demo#ASSET#motor_001", "sk": "ALERT#ACTIVE#thermal_stress"}},
                {"Key": {"tenant_asset": "cliente_demo#motor_001", "alert_key": "open#demo#thermal_stress"}},
            ],
        )


if __name__ == "__main__":
    unittest.main()
