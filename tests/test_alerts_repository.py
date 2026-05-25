from __future__ import annotations

import unittest
from decimal import Decimal

from botocore.exceptions import ClientError

from src.dashboard.alerts_repository import AlertsRepository, severity_from_status_label


class FakeTable:
    def __init__(
        self,
        *,
        item: dict | None = None,
        items: list[dict] | None = None,
        fail_first_query: bool = False,
        fail_condition_get: bool = False,
    ) -> None:
        self.item = item
        self.items = items or []
        self.fail_first_query = fail_first_query
        self.fail_condition_get = fail_condition_get
        self.query_requests: list[dict] = []
        self.scan_requests: list[dict] = []
        self.get_requests: list[dict] = []
        self.update_requests: list[dict] = []
        self.put_items: list[dict] = []

    def query(self, **kwargs) -> dict:
        self.query_requests.append(kwargs)
        if self.fail_first_query and len(self.query_requests) == 1:
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid key condition"}},
                "Query",
            )
        return {"Items": self.items}

    def scan(self, **kwargs) -> dict:
        self.scan_requests.append(kwargs)
        return {"Items": self.items}

    def get_item(self, **kwargs) -> dict:
        self.get_requests.append(kwargs)
        if self.fail_condition_get and "tenant_asset" in kwargs.get("Key", {}):
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid key"}},
                "GetItem",
            )

        if self.item is None:
            return {}

        return {"Item": self.item}

    def update_item(self, **kwargs) -> dict:
        self.update_requests.append(kwargs)
        return {}

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {}


class FakeDynamoResource:
    def __init__(self, table: FakeTable) -> None:
        self.table = table

    def Table(self, table_name: str) -> FakeTable:
        if table_name != "condition_alerts":
            raise ValueError(f"Unexpected table: {table_name}")
        return self.table


class AlertsRepositoryTest(unittest.TestCase):
    def repo(self, table: FakeTable) -> AlertsRepository:
        return AlertsRepository(table_name="condition_alerts", dynamodb_resource=FakeDynamoResource(table))

    def test_list_alerts_queries_condition_schema_by_asset(self) -> None:
        table = FakeTable(
            items=[
                {
                    "tenant_asset": "cliente_demo#motor_001",
                    "alert_key": "open#e2e#vibration_rms_mm_s",
                    "confidence": Decimal("1.0"),
                }
            ]
        )

        alerts = self.repo(table).list_alerts("cliente_demo", asset_id="motor_001")

        self.assertEqual(alerts[0]["confidence"], 1)
        self.assertEqual(len(table.query_requests), 1)

    def test_list_alerts_falls_back_to_legacy_pk_schema(self) -> None:
        table = FakeTable(
            fail_first_query=True,
            items=[
                {
                    "pk": "TENANT#cliente_demo#ASSET#motor_001",
                    "sk": "ALERT#ACTIVE#imbalance",
                    "confidence": Decimal("0.82"),
                }
            ],
        )

        alerts = self.repo(table).list_alerts("cliente_demo", asset_id="motor_001")

        self.assertEqual(alerts[0]["confidence"], 0.82)
        self.assertEqual(len(table.query_requests), 2)

    def test_update_status_appends_timeline_and_uses_condition_key(self) -> None:
        table = FakeTable(
            item={
                "tenant_asset": "cliente_demo#motor_001",
                "alert_key": "open#e2e#vibration_rms_mm_s",
                "status": "open",
                "timeline": [],
            }
        )

        self.repo(table).update_status(
            "cliente_demo#motor_001",
            "open#e2e#vibration_rms_mm_s",
            "acknowledged",
            "Ana",
            "Ciente da ocorrência.",
            "Inspeção visual programada.",
        )

        update = table.update_requests[0]
        self.assertEqual(
            update["Key"],
            {"tenant_asset": "cliente_demo#motor_001", "alert_key": "open#e2e#vibration_rms_mm_s"},
        )
        self.assertIn("acknowledged", update["ExpressionAttributeValues"].values())

        timeline = next(value for value in update["ExpressionAttributeValues"].values() if isinstance(value, list))
        self.assertEqual(timeline[-1]["by"], "Ana")
        self.assertEqual(timeline[-1]["to_status"], "acknowledged")

    def test_create_manual_alert_writes_new_and_legacy_keys(self) -> None:
        table = FakeTable()

        item = self.repo(table).create_manual_alert(
            "cliente_demo",
            "lab_virtual",
            "motor_001",
            "Motor Linha 1",
            "inspecao_visual",
            "CRÍTICO",
            8.5,
            7.0,
            "Parar equipamento e inspecionar.",
            "Ana",
            "Ruído anormal observado.",
        )

        written = table.put_items[0]
        self.assertEqual(written["tenant_asset"], "cliente_demo#motor_001")
        self.assertTrue(written["alert_key"].startswith("open#manual#inspecao_visual#"))
        self.assertEqual(written["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertTrue(written["sk"].startswith("ALERT#ACTIVE#MANUAL#inspecao_visual#"))
        self.assertEqual(written["severity"], "critical")
        self.assertIsInstance(written["value"], Decimal)
        self.assertEqual(item["status"], "open")

    def test_severity_from_status_label_treats_communication_loss_as_warning(self) -> None:
        self.assertEqual(severity_from_status_label("SEM COMUNICAÇÃO"), "warning")
        self.assertEqual(severity_from_status_label("SEM COMUNICACAO"), "warning")


if __name__ == "__main__":
    unittest.main()
