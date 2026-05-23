from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from .https_publisher import HttpsPublisher
from .mqtt_publisher import MqttPublisher
from .opcua_reader import OpcUaReader
from .payload_builder import build_telemetry_payload


async def main() -> None:
    load_env_file(Path(".env"))
    logging.basicConfig(level=os.getenv("BRIDGE_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("opcua").setLevel(os.getenv("OPCUA_LOG_LEVEL", "WARNING"))

    tenant_id = os.getenv("TENANT_ID", "cliente_demo")
    plant_id = os.getenv("PLANT_ID", "lab_virtual")
    asset_id = os.getenv("ASSET_ID", "motor_001")

    opcua_endpoint = os.getenv("OPCUA_ENDPOINT", "opc.tcp://localhost:4840/lab/opcua/")
    opcua_namespace_index = int(os.getenv("OPCUA_NAMESPACE_INDEX", "2"))

    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", f"lab/{tenant_id}/{plant_id}/{asset_id}/telemetry")

    https_endpoint = os.getenv("HTTPS_INGEST_URL", "")
    publish_mode = os.getenv("BRIDGE_PUBLISH_MODE", "mqtt").lower()
    interval_seconds = float(os.getenv("BRIDGE_INTERVAL_SECONDS", "1.0"))

    reader = OpcUaReader(endpoint=opcua_endpoint, namespace_index=opcua_namespace_index)
    publishers = build_publishers(
        publish_mode=publish_mode,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic=mqtt_topic,
        https_endpoint=https_endpoint,
    )

    logging.info("Bridge Edge iniciada")
    logging.info("OPC UA endpoint: %s", opcua_endpoint)
    logging.info("Modo de publicacao: %s", publish_mode)
    logging.info("MQTT destino: %s:%s | topico=%s", mqtt_host, mqtt_port, mqtt_topic)
    if https_endpoint:
        logging.info("HTTPS endpoint: %s", https_endpoint)

    while True:
        try:
            values = await reader.read_motor_tags()
            payload = build_telemetry_payload(
                tenant_id=tenant_id,
                plant_id=plant_id,
                asset_id=asset_id,
                source="opcua_edge_bridge",
                values=values,
            )

            for publisher in publishers:
                publish_result = publisher.publish(payload)
                if publish_result is not None:
                    logging.info("%s status=%s", publisher.__class__.__name__, publish_result)

            logging.info(
                "publicado asset=%s failure_mode=%s metrics=%s",
                asset_id,
                payload.get("failure_mode_simulated"),
                len(payload["metrics"]),
            )
        except Exception:
            logging.exception("Erro na bridge")

        await asyncio.sleep(interval_seconds)


def build_publishers(
    *,
    publish_mode: str,
    mqtt_host: str,
    mqtt_port: int,
    mqtt_topic: str,
    https_endpoint: str,
) -> list[object]:
    publishers: list[object] = []

    if publish_mode in {"mqtt", "both"}:
        publishers.append(MqttPublisher(host=mqtt_host, port=mqtt_port, topic=mqtt_topic))

    if publish_mode in {"https", "both"}:
        publishers.append(HttpsPublisher(endpoint=https_endpoint))

    if not publishers:
        raise ValueError("BRIDGE_PUBLISH_MODE must be mqtt, https, or both")

    return publishers


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if __name__ == "__main__":
    asyncio.run(main())
