from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aws_lambdas.ingest_lambda import (
    build_dynamodb_latest_item,
    build_raw_s3_key,
    build_timestream_records,
    lambda_handler,
    parse_event_payload,
    validate_payload,
)


def sample_payload() -> dict:
    return {
        "tenant_id": "cliente_demo",
        "plant_id": "lab_virtual",
        "asset_id": "motor_001",
        "source": "opcua_edge_bridge",
        "timestamp": "2026-05-22T13:00:00Z",
        "failure_mode_simulated": "normal",
        "metrics": [
            {"name": "rpm", "value": 1780.0, "unit": "rpm"},
            {"name": "vibration_rms_mm_s", "value": 2.2, "unit": "mm/s"},
            {"name": "temperature_c", "value": 61.5, "unit": "C"},
        ],
    }


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: list[dict] = []

    def put_object(self, **kwargs) -> dict:
        self.objects.append(kwargs)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class FakeTimestreamClient:
    def __init__(self) -> None:
        self.writes: list[dict] = []

    def write_records(self, **kwargs) -> dict:
        self.writes.append(kwargs)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class FakeDynamoTable:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def put_item(self, **kwargs) -> dict:
        self.items.append(kwargs["Item"])
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class FakeDynamoResource:
    def __init__(self, table: FakeDynamoTable) -> None:
        self.table = table
        self.requested_table_name = ""

    def Table(self, table_name: str) -> FakeDynamoTable:
        self.requested_table_name = table_name
        return self.table


class FakeEventBridgeClient:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def put_events(self, **kwargs) -> dict:
        self.events.extend(kwargs["Entries"])
        return {"FailedEntryCount": 0, "Entries": [{"EventId": "fake-event-id"}]}


class TestIngestLambda(unittest.TestCase):
    def test_parse_event_payload_from_api_gateway_body(self) -> None:
        payload = sample_payload()
        event = {"body": json.dumps(payload)}

        parsed = parse_event_payload(event)

        self.assertEqual(parsed["tenant_id"], "cliente_demo")
        self.assertEqual(parsed["asset_id"], "motor_001")

    def test_parse_event_payload_from_direct_event(self) -> None:
        payload = sample_payload()

        parsed = parse_event_payload(payload)

        self.assertEqual(parsed["plant_id"], "lab_virtual")

    def test_validate_payload_accepts_valid_payload(self) -> None:
        validate_payload(sample_payload())

    def test_validate_payload_rejects_missing_required_field(self) -> None:
        payload = sample_payload()
        del payload["tenant_id"]

        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_validate_payload_rejects_non_numeric_metric(self) -> None:
        payload = sample_payload()
        payload["metrics"].append({"name": "failure_mode", "value": "normal", "unit": "text"})

        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_build_raw_s3_key(self) -> None:
        key = build_raw_s3_key(sample_payload(), "evt_123")

        self.assertEqual(
            key,
            (
                "raw/tenant=cliente_demo/plant=lab_virtual/asset=motor_001/"
                "date=2026-05-22/evt_123.json"
            ),
        )

    def test_build_timestream_records(self) -> None:
        records = build_timestream_records(sample_payload())

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["MeasureName"], "rpm")
        self.assertEqual(records[0]["MeasureValueType"], "DOUBLE")
        self.assertEqual(records[0]["TimeUnit"], "MILLISECONDS")

    def test_build_dynamodb_latest_item(self) -> None:
        item = build_dynamodb_latest_item(
            payload=sample_payload(),
            event_id="evt_123",
            raw_s3_key="raw/test.json",
        )

        self.assertEqual(item["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(item["sk"], "LATEST")
        self.assertEqual(item["failure_mode_simulated"], "normal")
        self.assertIn("rpm", item["metrics"])

    def test_lambda_handler_writes_to_all_targets_with_fake_clients(self) -> None:
        fake_s3 = FakeS3Client()
        fake_timestream = FakeTimestreamClient()
        fake_table = FakeDynamoTable()
        fake_dynamodb = FakeDynamoResource(fake_table)
        fake_eventbridge = FakeEventBridgeClient()

        clients = {
            "s3": fake_s3,
            "timestream": fake_timestream,
            "dynamodb": fake_dynamodb,
            "eventbridge": fake_eventbridge,
        }

        env = {
            "RAW_BUCKET": "mvp-condition-monitoring-raw",
            "TIMESTREAM_DB": "condition_monitoring_lab",
            "TIMESTREAM_TABLE": "telemetry",
            "DYNAMODB_TABLE": "mvp_asset_state",
            "EVENT_BUS": "default",
        }

        event = {"body": json.dumps(sample_payload())}
        with patch.dict(os.environ, env, clear=False):
            with patch("aws_lambdas.ingest_lambda.get_boto3_clients", return_value=clients):
                result = lambda_handler(event, None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 202)
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["metrics_received"], 3)
        self.assertEqual(fake_s3.objects[0]["Bucket"], "mvp-condition-monitoring-raw")
        self.assertEqual(fake_timestream.writes[0]["DatabaseName"], "condition_monitoring_lab")
        self.assertEqual(fake_timestream.writes[0]["TableName"], "telemetry")
        self.assertEqual(fake_dynamodb.requested_table_name, "mvp_asset_state")
        self.assertEqual(fake_table.items[0]["asset_id"], "motor_001")
        self.assertEqual(fake_eventbridge.events[0]["DetailType"], "TelemetryNormalized")

    def test_lambda_handler_returns_500_when_eventbridge_reports_failure(self) -> None:
        class FailingEventBridgeClient(FakeEventBridgeClient):
            def put_events(self, **kwargs) -> dict:
                self.events.extend(kwargs["Entries"])
                return {
                    "FailedEntryCount": 1,
                    "Entries": [
                        {
                            "ErrorCode": "InternalFailure",
                            "ErrorMessage": "fake failure",
                        }
                    ],
                }

        fake_table = FakeDynamoTable()
        clients = {
            "s3": FakeS3Client(),
            "timestream": FakeTimestreamClient(),
            "dynamodb": FakeDynamoResource(fake_table),
            "eventbridge": FailingEventBridgeClient(),
        }

        env = {
            "RAW_BUCKET": "mvp-condition-monitoring-raw",
            "TIMESTREAM_DB": "condition_monitoring_lab",
            "TIMESTREAM_TABLE": "telemetry",
            "DYNAMODB_TABLE": "mvp_asset_state",
            "EVENT_BUS": "default",
        }

        event = {"body": json.dumps(sample_payload())}
        with patch.dict(os.environ, env, clear=False):
            with patch("aws_lambdas.ingest_lambda.get_boto3_clients", return_value=clients):
                result = lambda_handler(event, None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 500)
        self.assertEqual(body["status"], "internal_error")
        self.assertIn("EventBridge", body["error"])

    def test_lambda_handler_rejects_invalid_payload(self) -> None:
        invalid_payload = sample_payload()
        invalid_payload["metrics"] = []

        result = lambda_handler({"body": json.dumps(invalid_payload)}, None)
        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(body["status"], "invalid_payload")


if __name__ == "__main__":
    unittest.main()
