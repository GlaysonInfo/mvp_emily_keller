from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.dashboard.intelligence_demo_history import create_demo_history_items, seed_demo_history_to_dynamodb


class FakeBatchWriter:
    def __init__(self, sink: list[dict]) -> None:
        self.sink = sink

    def __enter__(self) -> "FakeBatchWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def put_item(self, *, Item: dict) -> None:
        self.sink.append(Item)


class FakeTable:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def batch_writer(self) -> FakeBatchWriter:
        return FakeBatchWriter(self.items)


class FakeHistoryRepository:
    def __init__(self) -> None:
        self.table = FakeTable()


class IntelligenceDemoHistoryTest(unittest.TestCase):
    def test_create_demo_history_items_matches_history_table_keys(self) -> None:
        items = create_demo_history_items(
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
            current_state={
                "status_label": "ATENÇÃO",
                "temperature_c": 76,
                "vibration_rms_mm_s": 2.4,
                "ultrasound_db": 47,
                "health_score": 71.9,
                "severity_score": 28.1,
            },
            minutes_healthy=3,
            minutes_degraded=2,
            now=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
        )

        self.assertEqual(len(items), 5)
        self.assertEqual(items[0]["tenant_asset"], "cliente_demo#motor_001")
        self.assertEqual(items[0]["status_label"], "NORMAL")
        self.assertEqual(items[-1]["status_label"], "ATENÇÃO")
        self.assertIn("ts_utc_minute", items[-1])
        self.assertIn("temperature_c", items[-1])

    def test_seed_demo_history_writes_batch_items(self) -> None:
        repository = FakeHistoryRepository()

        count = seed_demo_history_to_dynamodb(
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
            current_state={"status_label": "ATENÇÃO", "severity_score": 28.1},
            history_repository=repository,
        )

        self.assertEqual(count, 140)
        self.assertEqual(len(repository.table.items), 140)
        self.assertEqual(repository.table.items[0]["tenant_asset"], "cliente_demo#motor_001")


if __name__ == "__main__":
    unittest.main()
