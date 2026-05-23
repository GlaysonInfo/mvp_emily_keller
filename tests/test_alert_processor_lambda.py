from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from src.aws_lambdas import alert_processor_lambda


class FakeTable:
    def __init__(self, item: dict | None = None) -> None:
        self.item = item
        self.get_requests: list[dict] = []
        self.put_items: list[dict] = []

    def get_item(self, **kwargs) -> dict:
        self.get_requests.append(kwargs)
        if self.item:
            return {"Item": self.item}
        return {}

    def put_item(self, **kwargs) -> dict:
        self.put_items.append(kwargs["Item"])
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class FakeDynamoResource:
    def __init__(self, state_table: FakeTable, alerts_table: FakeTable) -> None:
        self.state_table = state_table
        self.alerts_table = alerts_table

    def Table(self, table_name: str) -> FakeTable:
        if table_name == "mvp_asset_state_dev":
            return self.state_table

        if table_name == "mvp_alerts_dev":
            return self.alerts_table

        raise ValueError(f"Tabela inesperada: {table_name}")


def eventbridge_event() -> dict:
    return {
        "source": "condition-monitoring.ingestion",
        "detail-type": "TelemetryNormalized",
        "detail": {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "asset_id": "motor_001",
            "timestamp": "2026-05-23T03:02:29Z",
            "raw_s3_key": "raw/test.json",
        },
    }


def latest_item(metrics: dict, failure_mode: str = "normal") -> dict:
    return {
        "pk": "TENANT#cliente_demo#ASSET#motor_001",
        "sk": "LATEST",
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "motor_001",
        "source": "opcua_edge_bridge",
        "updated_at": "2026-05-23T03:02:29Z",
        "failure_mode_simulated": failure_mode,
        "metrics": metrics,
    }


def latest_imbalance_item() -> dict:
    return latest_item(
        {
            "rpm": {"value": Decimal("1770.0"), "unit": "rpm"},
            "vibration_rms_mm_s": {"value": Decimal("4.4"), "unit": "mm/s"},
            "temperature_c": {"value": Decimal("62.8"), "unit": "C"},
            "ultrasound_db": {"value": Decimal("33.1"), "unit": "dB"},
            "kurtosis": {"value": Decimal("3.2"), "unit": "index"},
            "crest_factor": {"value": Decimal("3.1"), "unit": "index"},
            "health_score": {"value": Decimal("67.6"), "unit": "score"},
            "severity": {"value": Decimal("70.5"), "unit": "score"},
        },
        failure_mode="imbalance",
    )


def latest_normal_item() -> dict:
    return latest_item(
        {
            "rpm": {"value": Decimal("1780.0"), "unit": "rpm"},
            "vibration_rms_mm_s": {"value": Decimal("2.0"), "unit": "mm/s"},
            "temperature_c": {"value": Decimal("60.0"), "unit": "C"},
            "ultrasound_db": {"value": Decimal("32.0"), "unit": "dB"},
            "kurtosis": {"value": Decimal("3.1"), "unit": "index"},
            "crest_factor": {"value": Decimal("3.0"), "unit": "index"},
            "health_score": {"value": Decimal("97.0"), "unit": "score"},
        }
    )


class TestAlertProcessorLambda(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DYNAMODB_TABLE"] = "mvp_asset_state_dev"
        os.environ["ALERTS_TABLE"] = "mvp_alerts_dev"

    def test_processes_event_and_writes_imbalance_alert(self) -> None:
        state_table = FakeTable(item=latest_imbalance_item())
        alerts_table = FakeTable()
        fake_resource = FakeDynamoResource(state_table=state_table, alerts_table=alerts_table)

        with patch.object(alert_processor_lambda, "get_dynamodb_resource", return_value=fake_resource):
            result = alert_processor_lambda.lambda_handler(eventbridge_event(), context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["status"], "processed")
        self.assertEqual(body["alerts_detected"], 1)
        self.assertEqual(body["alerts_written"], 1)

        written_alert = alerts_table.put_items[0]

        self.assertEqual(written_alert["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(written_alert["sk"], "ALERT#ACTIVE#imbalance")
        self.assertEqual(written_alert["alert_id"], "cliente_demo#motor_001#imbalance#active")
        self.assertEqual(written_alert["alert_type"], "imbalance")
        self.assertEqual(written_alert["severity"], "critical")
        self.assertEqual(written_alert["status"], "open")
        self.assertEqual(written_alert["source"], "opcua_edge_bridge")
        self.assertEqual(written_alert["failure_mode_simulated"], "imbalance")
        self.assertIn("probable_cause", written_alert)
        self.assertIn("recommended_action", written_alert)
        self.assertTrue(written_alert["evidence"])

    def test_normal_state_does_not_write_alert(self) -> None:
        state_table = FakeTable(item=latest_normal_item())
        alerts_table = FakeTable()
        fake_resource = FakeDynamoResource(state_table=state_table, alerts_table=alerts_table)

        with patch.object(alert_processor_lambda, "get_dynamodb_resource", return_value=fake_resource):
            result = alert_processor_lambda.lambda_handler(eventbridge_event(), context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["alerts_detected"], 0)
        self.assertEqual(body["alerts_written"], 0)
        self.assertEqual(len(alerts_table.put_items), 0)

    def test_existing_active_alert_preserves_first_detected_at(self) -> None:
        state_table = FakeTable(item=latest_imbalance_item())
        alerts_table = FakeTable(item={"first_detected_at": "2026-05-23T03:00:00Z"})
        fake_resource = FakeDynamoResource(state_table=state_table, alerts_table=alerts_table)

        with patch.object(alert_processor_lambda, "get_dynamodb_resource", return_value=fake_resource):
            result = alert_processor_lambda.lambda_handler(eventbridge_event(), context=None)

        self.assertEqual(result["statusCode"], 200)
        written_alert = alerts_table.put_items[0]
        self.assertEqual(written_alert["first_detected_at"], "2026-05-23T03:00:00Z")

    def test_returns_404_when_latest_state_not_found(self) -> None:
        state_table = FakeTable(item=None)
        alerts_table = FakeTable()
        fake_resource = FakeDynamoResource(state_table=state_table, alerts_table=alerts_table)

        with patch.object(alert_processor_lambda, "get_dynamodb_resource", return_value=fake_resource):
            result = alert_processor_lambda.lambda_handler(eventbridge_event(), context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 404)
        self.assertEqual(body["status"], "latest_state_not_found")
        self.assertEqual(len(alerts_table.put_items), 0)

    def test_returns_400_when_event_detail_is_invalid(self) -> None:
        result = alert_processor_lambda.lambda_handler({"detail": {}}, context=None)
        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(body["status"], "invalid_event")


if __name__ == "__main__":
    unittest.main()
