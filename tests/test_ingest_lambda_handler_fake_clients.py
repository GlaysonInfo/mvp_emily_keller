from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from src.aws_lambdas import ingest_lambda


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
    def __init__(self) -> None:
        self.table = FakeDynamoTable()
        self.table_name = ""

    def Table(self, table_name) -> FakeDynamoTable:
        self.table_name = table_name
        return self.table


class FakeEventBridgeClient:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def put_events(self, **kwargs) -> dict:
        self.events.append(kwargs)
        return {"FailedEntryCount": 0, "Entries": [{"EventId": "fake-event-id"}]}


class TestIngestLambdaHandlerWithFakeClients(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["RAW_BUCKET"] = "test-raw-bucket"
        os.environ.pop("ENABLE_TIMESTREAM", None)
        os.environ["TIMESTREAM_DB"] = "condition_monitoring_lab"
        os.environ["TIMESTREAM_TABLE"] = "telemetry"
        os.environ["TIMESTREAM_ENABLED"] = "true"
        os.environ["DYNAMODB_TABLE"] = "mvp_asset_state"
        os.environ["EVENT_BUS"] = "default"

        self.fake_s3 = FakeS3Client()
        self.fake_timestream = FakeTimestreamClient()
        self.fake_dynamodb = FakeDynamoResource()
        self.fake_eventbridge = FakeEventBridgeClient()

    def fake_clients(self) -> dict:
        return {
            "s3": self.fake_s3,
            "timestream": self.fake_timestream,
            "dynamodb": self.fake_dynamodb,
            "eventbridge": self.fake_eventbridge,
        }

    def test_lambda_handler_accepts_api_gateway_event_and_writes_all_targets(self) -> None:
        event = {"body": json.dumps(sample_payload())}

        with patch.object(ingest_lambda, "get_boto3_clients", self.fake_clients):
            result = ingest_lambda.lambda_handler(event, context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 202)
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["metrics_received"], 3)

        self.assertEqual(len(self.fake_s3.objects), 1)
        self.assertEqual(self.fake_s3.objects[0]["Bucket"], "test-raw-bucket")
        self.assertIn("raw/tenant=cliente_demo", self.fake_s3.objects[0]["Key"])

        self.assertEqual(len(self.fake_timestream.writes), 1)
        self.assertEqual(self.fake_timestream.writes[0]["DatabaseName"], "condition_monitoring_lab")
        self.assertEqual(len(self.fake_timestream.writes[0]["Records"]), 3)

        self.assertEqual(len(self.fake_dynamodb.table.items), 1)
        latest_item = self.fake_dynamodb.table.items[0]
        self.assertEqual(latest_item["pk"], "TENANT#cliente_demo#ASSET#motor_001")
        self.assertEqual(latest_item["sk"], "LATEST")
        self.assertIn("rpm", latest_item["metrics"])

        self.assertEqual(len(self.fake_eventbridge.events), 1)
        event_entry = self.fake_eventbridge.events[0]["Entries"][0]
        self.assertEqual(event_entry["DetailType"], "TelemetryNormalized")

    def test_lambda_handler_skips_timestream_when_disabled(self) -> None:
        os.environ["TIMESTREAM_ENABLED"] = "false"
        event = {"body": json.dumps(sample_payload())}

        with patch.object(ingest_lambda, "get_boto3_clients", self.fake_clients):
            result = ingest_lambda.lambda_handler(event, context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 202)
        self.assertFalse(body["timestream_enabled"])
        self.assertEqual(len(self.fake_s3.objects), 1)
        self.assertEqual(len(self.fake_timestream.writes), 0)
        self.assertEqual(len(self.fake_dynamodb.table.items), 1)
        self.assertEqual(len(self.fake_eventbridge.events), 1)

    def test_lambda_handler_uses_enable_timestream_flag(self) -> None:
        os.environ["ENABLE_TIMESTREAM"] = "false"
        os.environ["TIMESTREAM_ENABLED"] = "true"
        event = {"body": json.dumps(sample_payload())}

        with patch.object(ingest_lambda, "get_boto3_clients", self.fake_clients):
            result = ingest_lambda.lambda_handler(event, context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 202)
        self.assertFalse(body["timestream_enabled"])
        self.assertEqual(len(self.fake_timestream.writes), 0)

    def test_lambda_handler_rejects_invalid_payload_without_writing(self) -> None:
        invalid_payload = sample_payload()
        invalid_payload["metrics"][0]["value"] = "not-a-number"

        event = {"body": json.dumps(invalid_payload)}

        with patch.object(ingest_lambda, "get_boto3_clients", self.fake_clients):
            result = ingest_lambda.lambda_handler(event, context=None)

        body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(body["status"], "invalid_payload")

        self.assertEqual(len(self.fake_s3.objects), 0)
        self.assertEqual(len(self.fake_timestream.writes), 0)
        self.assertEqual(len(self.fake_dynamodb.table.items), 0)
        self.assertEqual(len(self.fake_eventbridge.events), 0)


if __name__ == "__main__":
    unittest.main()
