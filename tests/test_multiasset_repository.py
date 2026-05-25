from __future__ import annotations

import unittest
from decimal import Decimal

from src.dashboard.multiasset_repository import MultiAssetRepository, state_table_name_from_env


class FakeTable:
    def __init__(self) -> None:
        self.scan_requests: list[dict] = []
        self.responses = [
            {
                "Items": [{"asset_id": "motor_001", "health_score": Decimal("71.9")}],
                "LastEvaluatedKey": {"pk": "page-2"},
            },
            {"Items": [{"asset_id": "bomba_001", "health_score": Decimal("52.4")}]},
        ]

    def scan(self, **kwargs) -> dict:
        self.scan_requests.append(kwargs)
        return self.responses.pop(0)


class FakeDynamoResource:
    def __init__(self, table: FakeTable) -> None:
        self.table = table
        self.table_names: list[str] = []

    def Table(self, table_name: str) -> FakeTable:
        self.table_names.append(table_name)
        return self.table


class MultiAssetRepositoryTest(unittest.TestCase):
    def test_state_table_name_prefers_sprint_env_alias(self) -> None:
        import os

        old_state_table = os.environ.get("DYNAMODB_STATE_TABLE")
        old_table = os.environ.get("DYNAMODB_TABLE")
        os.environ["DYNAMODB_STATE_TABLE"] = "state_from_alias"
        os.environ["DYNAMODB_TABLE"] = "state_from_project"

        try:
            self.assertEqual(state_table_name_from_env(), "state_from_alias")
        finally:
            if old_state_table is None:
                os.environ.pop("DYNAMODB_STATE_TABLE", None)
            else:
                os.environ["DYNAMODB_STATE_TABLE"] = old_state_table

            if old_table is None:
                os.environ.pop("DYNAMODB_TABLE", None)
            else:
                os.environ["DYNAMODB_TABLE"] = old_table

    def test_list_current_states_paginates_and_converts_decimals(self) -> None:
        table = FakeTable()
        resource = FakeDynamoResource(table)
        repo = MultiAssetRepository(
            table_name="mvp_asset_state_dev",
            region_name="us-east-1",
            dynamodb_resource=resource,
        )

        states = repo.list_current_states(tenant_id="cliente_demo", plant_id="lab_virtual")

        self.assertEqual(resource.table_names, ["mvp_asset_state_dev"])
        self.assertEqual([state["asset_id"] for state in states], ["motor_001", "bomba_001"])
        self.assertEqual(states[0]["health_score"], 71.9)
        self.assertEqual(len(table.scan_requests), 2)
        self.assertIn("ExclusiveStartKey", table.scan_requests[1])


if __name__ == "__main__":
    unittest.main()
