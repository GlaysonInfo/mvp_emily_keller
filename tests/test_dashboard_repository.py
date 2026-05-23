from __future__ import annotations

import unittest
from decimal import Decimal

from src.dashboard.dynamodb_repository import DashboardRepository, decimal_to_native


class FakeTable:
    def __init__(self, *, item: dict | None = None, items: list[dict] | None = None) -> None:
        self.item = item
        self.items = items or []
        self.get_requests: list[dict] = []
        self.query_requests: list[dict] = []
        self.put_items: list[dict] = []
        self.delete_requests: list[dict] = []

    def get_item(self, **kwargs) -> dict:
        self.get_requests.append(kwargs)
        if self.item is None:
            return {}
        return {"Item": self.item}

    def query(self, **kwargs) -> dict:
        self.query_requests.append(kwargs)
        return {"Items": self.items}

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {}

    def delete_item(self, **kwargs) -> dict:
        self.delete_requests.append(kwargs)
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

    def test_put_latest_state_writes_item(self) -> None:
        state_table = FakeTable()
        repo = DashboardRepository(
            state_table_name="mvp_asset_state_dev",
            alerts_table_name="mvp_alerts_dev",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(state_table, FakeTable()),
        )
        item = {"pk": "TENANT#cliente_demo#ASSET#motor_001", "sk": "LATEST"}

        repo.put_latest_state(item)

        self.assertEqual(state_table.put_items, [item])

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


if __name__ == "__main__":
    unittest.main()
