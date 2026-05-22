from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from edge_bridge.mqtt_publisher import MqttPublisher


class FakePublishResult:
    def __init__(self, rc: int) -> None:
        self.rc = rc


class FakeMqttClient:
    def __init__(self, rc: int = 0, connect_rc: int | None = None) -> None:
        self.rc = rc
        self.connect_rc = connect_rc
        self.connected = False
        self.loop_started = False
        self.published: list[tuple[str, str, int]] = []
        self.connect_calls = 0

    def connect(self, host: str, port: int, keepalive: int) -> int | None:
        self.connect_calls += 1
        self.connected = (host, port, keepalive) == ("localhost", 1883, 60)
        return self.connect_rc

    def loop_start(self) -> None:
        self.loop_started = True

    def publish(self, topic: str, message: str, qos: int) -> FakePublishResult:
        self.published.append((topic, message, qos))
        return FakePublishResult(self.rc)


class MqttPublisherTest(unittest.TestCase):
    def test_connect_starts_mqtt_loop(self) -> None:
        client = FakeMqttClient()
        publisher = MqttPublisher(host="localhost", port=1883, topic="lab/demo", client=client)

        publisher.connect()

        self.assertTrue(client.connected)
        self.assertTrue(client.loop_started)

    def test_publish_sends_json_to_configured_topic(self) -> None:
        client = FakeMqttClient()
        publisher = MqttPublisher(host="localhost", port=1883, topic="lab/demo", client=client)

        publisher.publish({"asset_id": "motor_001", "failure_mode_simulated": "normal"})

        self.assertEqual(len(client.published), 1)
        topic, message, qos = client.published[0]
        self.assertEqual(topic, "lab/demo")
        self.assertEqual(qos, 1)
        self.assertEqual(json.loads(message)["asset_id"], "motor_001")
        self.assertEqual(client.connect_calls, 1)

    def test_publish_raises_when_client_reports_failure(self) -> None:
        client = FakeMqttClient(rc=4)
        publisher = MqttPublisher(host="localhost", port=1883, topic="lab/demo", client=client)

        with self.assertRaises(RuntimeError):
            publisher.publish({"asset_id": "motor_001"})

    def test_publish_retries_connection_after_publish_failure(self) -> None:
        client = FakeMqttClient(rc=4)
        publisher = MqttPublisher(host="localhost", port=1883, topic="lab/demo", client=client)

        with self.assertRaises(RuntimeError):
            publisher.publish({"asset_id": "motor_001"})

        client.rc = 0
        publisher.publish({"asset_id": "motor_001"})

        self.assertEqual(client.connect_calls, 2)
        self.assertEqual(len(client.published), 2)

    def test_connect_raises_when_client_reports_connection_failure(self) -> None:
        client = FakeMqttClient(connect_rc=4)
        publisher = MqttPublisher(host="localhost", port=1883, topic="lab/demo", client=client)

        with self.assertRaises(RuntimeError):
            publisher.connect()


if __name__ == "__main__":
    unittest.main()
