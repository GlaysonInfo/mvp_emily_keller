from __future__ import annotations

import importlib.util
import json
import socket
import time
import unittest


def has_paho_mqtt() -> bool:
    return importlib.util.find_spec("paho.mqtt.client") is not None


def is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@unittest.skipUnless(
    has_paho_mqtt() and is_port_open("localhost", 1883),
    "Mosquitto local nao esta disponivel em localhost:1883",
)
class MqttIntegrationOptionalTest(unittest.TestCase):
    def test_publish_and_receive_payload(self) -> None:
        import paho.mqtt.client as mqtt

        received_messages: list[str] = []

        def on_message(client, userdata, msg) -> None:
            received_messages.append(msg.payload.decode("utf-8"))

        subscriber = mqtt.Client()
        subscriber.on_message = on_message
        subscriber.connect("localhost", 1883, keepalive=60)
        subscriber.subscribe("lab/test/+/+/telemetry")
        subscriber.loop_start()

        publisher = mqtt.Client()
        publisher.connect("localhost", 1883, keepalive=60)

        payload = {
            "tenant_id": "test",
            "plant_id": "lab_virtual",
            "asset_id": "motor_001",
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "failure_mode_simulated": "normal",
            "metrics": [
                {"name": "rpm", "value": 1780.0, "unit": "rpm"},
            ],
        }

        publisher.publish(
            "lab/test/lab_virtual/motor_001/telemetry",
            json.dumps(payload),
            qos=1,
        )

        timeout_at = time.time() + 5
        while time.time() < timeout_at and not received_messages:
            time.sleep(0.1)

        subscriber.loop_stop()
        publisher.disconnect()
        subscriber.disconnect()

        self.assertTrue(received_messages)
        parsed = json.loads(received_messages[0])
        self.assertEqual(parsed["asset_id"], "motor_001")
        self.assertEqual(parsed["failure_mode_simulated"], "normal")
        self.assertEqual(parsed["metrics"][0]["name"], "rpm")


if __name__ == "__main__":
    unittest.main()
