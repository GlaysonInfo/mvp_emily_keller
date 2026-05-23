from __future__ import annotations

import unittest
from unittest.mock import patch

from src.edge_bridge.https_publisher import HttpsPublisher


class FakeHttpResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def getcode(self) -> int:
        return self.status_code


class HttpsPublisherTest(unittest.TestCase):
    def test_publish_returns_http_status_code(self) -> None:
        publisher = HttpsPublisher(endpoint="https://example.test/telemetry")

        with patch("src.edge_bridge.https_publisher.urlopen", return_value=FakeHttpResponse(202)):
            status_code = publisher.publish({"asset_id": "motor_001"})

        self.assertEqual(status_code, 202)


if __name__ == "__main__":
    unittest.main()
