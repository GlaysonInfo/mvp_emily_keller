from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.edge.condition_bridge_field.config_store import load_condition_field_config
from src.edge.condition_bridge_field.delivery_queue import ConditionDeliveryQueue
from src.edge.condition_bridge_field.gateway_client import ConditionGatewayClient
from src.edge.condition_bridge_field.iot_topic import build_iot_topic
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads


class GreengrassIotCorePublisher:
    def __init__(self, config: dict[str, Any]):
        try:
            from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
            from awsiot.greengrasscoreipc.model import QOS
        except Exception as exc:  # pragma: no cover - depende do runtime Greengrass.
            raise RuntimeError(
                "AWS IoT Device SDK nao encontrado. Instale awsiotsdk no componente Greengrass."
            ) from exc

        qos_name = str(config.get("iot_core", {}).get("qos") or "AT_LEAST_ONCE")
        self._client = GreengrassCoreIPCClientV2()
        self._qos = getattr(QOS, qos_name, QOS.AT_LEAST_ONCE)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self._client.publish_to_iot_core(
            topic_name=topic,
            qos=self._qos,
            payload=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )


def _max_iterations() -> int | None:
    if os.getenv("CONDITION_BRIDGE_ONCE"):
        return 1

    value = os.getenv("CONDITION_BRIDGE_MAX_ITERATIONS")
    if value:
        return int(value)

    return None


def _spool_dir(config: dict[str, Any]) -> str | None:
    return (
        config.get("iot_core", {}).get("spool_dir")
        or config.get("ingest_api", {}).get("spool_dir")
        or "data/condition_bridge_spool/greengrass_iot"
    )


def main() -> None:
    config_path = os.getenv("CONDITION_FIELD_CONFIG", "config/ethernet_apl_greengrass_condition_config.example.json")
    config = load_condition_field_config(config_path)

    client = ConditionGatewayClient(config)
    publisher = GreengrassIotCorePublisher(config)
    queue = ConditionDeliveryQueue(_spool_dir(config))
    poll_interval_ms = int(config.get("gateway", {}).get("poll_interval_ms", 1000))
    sleep_sec = poll_interval_ms / 1000
    max_iterations = _max_iterations()
    iterations = 0

    print("Sentinela Greengrass condition bridge started.")
    print(f"Config: {config_path}")
    print(f"Topic template: {config.get('iot_core', {}).get('topic_template')}")

    while True:
        try:
            raw = client.read_raw()
            payloads = build_condition_payloads(config, raw)
            for payload in payloads:
                queue.enqueue(payload)

            for queued_item in queue.pending():
                queued_payload = queue.load(queued_item)
                topic = build_iot_topic(config, queued_payload)
                publisher.publish(topic, queued_payload)
                print(f"Published {queued_payload.get('asset_id')} -> {topic}")
                queue.acknowledge(queued_item)
        except Exception as exc:
            print(f"Greengrass bridge error: {type(exc).__name__}: {exc}")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break

        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
