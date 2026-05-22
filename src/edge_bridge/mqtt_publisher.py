from __future__ import annotations

import json
import logging
from typing import Any

MQTT_ERR_SUCCESS = 0


class MqttPublisher:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        topic: str,
        client: Any | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self.client = client
        self._client_factory = self._create_client if client is None else None
        self._connected = False

    def connect(self) -> None:
        if self._connected:
            return

        if self.client is None:
            if self._client_factory is None:
                raise RuntimeError("Cliente MQTT nao inicializado")
            self.client = self._client_factory()

        result = self.client.connect(self.host, self.port, keepalive=60)
        if result not in (None, MQTT_ERR_SUCCESS):
            raise RuntimeError(f"Falha ao conectar MQTT. rc={result}")

        self.client.loop_start()
        self._connected = True
        logging.info("MQTT conectado em %s:%s", self.host, self.port)

    def publish(self, payload: dict[str, Any]) -> None:
        self.connect()
        message = json.dumps(payload, ensure_ascii=False)
        result = self.client.publish(self.topic, message, qos=1)

        if result.rc != MQTT_ERR_SUCCESS:
            self._connected = False
            raise RuntimeError(f"Falha ao publicar MQTT. rc={result.rc}")

    @staticmethod
    def _create_client() -> Any:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:  # pragma: no cover - exercised only without dependency.
            raise SystemExit("paho-mqtt is required. Install dependencies with: python -m pip install -e .") from exc

        return mqtt.Client()
