from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from .https_publisher import HttpsPublisher
from .mqtt_publisher import MqttPublisher
from .opcua_reader import OpcUaReader
from .payload_builder import build_telemetry_payload


logger = logging.getLogger("edge_bridge")


async def main() -> None:
    load_env_file(Path(".env"))
    configure_logging()

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

    logger.info("Bridge Edge iniciada")
    logger.info("OPC UA endpoint: %s", opcua_endpoint)
    logger.info("Modo de publicacao: %s", publish_mode)
    logger.info("MQTT destino: %s:%s | topico=%s", mqtt_host, mqtt_port, mqtt_topic)
    if https_endpoint:
        logger.info("HTTPS endpoint: %s", https_endpoint)

    while True:
        try:
            values = await reader.read_motor_tags()
            logger.info("OPC UA tags lidas com sucesso: %s tags", len(values))

            payload = build_telemetry_payload(
                tenant_id=tenant_id,
                plant_id=plant_id,
                asset_id=asset_id,
                source="opcua_edge_bridge",
                values=values,
            )
            logger.info(
                "Payload montado: asset=%s failure_mode=%s metrics=%s",
                asset_id,
                payload.get("failure_mode_simulated"),
                len(payload.get("metrics", [])),
            )

            for publisher in publishers:
                publish_result = publisher.publish(payload)
                if publish_result is not None:
                    logger.info("%s enviado com sucesso: status_code=%s", publisher_log_name(publisher), publish_result)

            logger.info(
                "publicado asset=%s failure_mode=%s metrics=%s",
                asset_id,
                payload.get("failure_mode_simulated"),
                len(payload["metrics"]),
            )
        except Exception:
            logger.exception("Erro na bridge")

        await asyncio.sleep(interval_seconds)


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("BRIDGE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    opcua_log_level = os.getenv("OPCUA_LOG_LEVEL", "WARNING")
    for logger_name in [
        "opcua",
        "opcua.client",
        "opcua.common",
        "opcua.uaprotocol",
    ]:
        logging.getLogger(logger_name).setLevel(opcua_log_level)


def publisher_log_name(publisher: object) -> str:
    if isinstance(publisher, HttpsPublisher):
        return "HTTPS"

    if isinstance(publisher, MqttPublisher):
        return "MQTT"

    return publisher.__class__.__name__


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
