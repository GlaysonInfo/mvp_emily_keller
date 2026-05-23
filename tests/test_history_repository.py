from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from src.dashboard.history_repository import ConditionHistoryRepository, build_history_item, floor_to_minute


class FakeHistoryTable:
    def __init__(self, items: list[dict] | None = None) -> None:
        self.items = items or []
        self.put_items: list[dict] = []
        self.query_requests: list[dict] = []

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {}

    def query(self, **kwargs) -> dict:
        self.query_requests.append(kwargs)
        return {"Items": self.items}


class FakeDynamoResource:
    def __init__(self, table: FakeHistoryTable) -> None:
        self.table = table

    def Table(self, table_name: str) -> FakeHistoryTable:
        if table_name != "condition_history":
            raise ValueError(f"Unexpected table: {table_name}")

        return self.table


class HistoryRepositoryTest(unittest.TestCase):
    def test_build_history_item_flattens_latest_state_by_minute(self) -> None:
        latest_state = {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "asset_id": "motor_001",
            "source": "opcua_edge_bridge",
            "updated_at": "2026-05-23T12:11:33Z",
            "failure_mode_simulated": "lubrication_degradation",
            "metrics": {
                "rpm": {"value": Decimal("1779.57"), "unit": "rpm"},
                "vibration_rms_mm_s": {"value": Decimal("2.96"), "unit": "mm/s"},
                "temperature_c": {"value": Decimal("67.91"), "unit": "C"},
                "ultrasound_db": {"value": Decimal("41.54"), "unit": "dB"},
                "kurtosis": {"value": Decimal("3.59"), "unit": "index"},
                "crest_factor": {"value": Decimal("3.42"), "unit": "index"},
                "vibration_peak_g": {"value": Decimal("0.69"), "unit": "g"},
                "horimeter_h": {"value": Decimal("1284.03"), "unit": "h"},
                "health_score": {"value": Decimal("71.9"), "unit": "score"},
            },
        }

        item = build_history_item(
            latest_state,
            recorded_at=datetime(2026, 5, 23, 12, 11, 44, tzinfo=UTC),
        )

        self.assertEqual(item["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(item["ts_utc_minute"], "2026-05-23T12:11:00Z")
        self.assertEqual(item["mode"], "lubrication_degradation")
        self.assertEqual(item["status_label"], "ATENÇÃO")
        self.assertEqual(item["temperature_c"], Decimal("67.91"))
        self.assertEqual(item["hourmeter_h"], Decimal("1284.03"))
        self.assertEqual(item["severity_score"], Decimal("28.1"))
        self.assertIn("ttl_epoch", item)

    def test_put_minute_snapshot_writes_item(self) -> None:
        table = FakeHistoryTable()
        repo = ConditionHistoryRepository(
            table_name="condition_history",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(table),
        )

        item = repo.put_minute_snapshot({"tenant_id": "cliente_demo", "asset_id": "motor_001", "metrics": {}})

        self.assertEqual(table.put_items, [item])

    def test_query_history_returns_native_items(self) -> None:
        table = FakeHistoryTable(items=[{"temperature_c": Decimal("67.91")}])
        repo = ConditionHistoryRepository(
            table_name="condition_history",
            region_name="us-east-1",
            dynamodb_resource=FakeDynamoResource(table),
        )

        items = repo.query_history(
            tenant_id="cliente_demo",
            asset_id="motor_001",
            start_utc=datetime(2026, 5, 23, 12, 0, tzinfo=UTC),
            end_utc=datetime(2026, 5, 23, 13, 0, tzinfo=UTC),
        )

        self.assertEqual(items, [{"temperature_c": 67.91}])
        self.assertEqual(len(table.query_requests), 1)

    def test_floor_to_minute_removes_seconds(self) -> None:
        timestamp = datetime(2026, 5, 23, 12, 11, 44, 123, tzinfo=UTC)

        self.assertEqual(floor_to_minute(timestamp), datetime(2026, 5, 23, 12, 11, tzinfo=UTC))


if __name__ == "__main__":
    unittest.main()
