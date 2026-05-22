from __future__ import annotations

import asyncio
from typing import Any, Iterable

try:
    from simulator.contracts import OPCUA_TAGS
except ImportError:  # pragma: no cover - supports python -m src.edge_bridge.main.
    from src.simulator.contracts import OPCUA_TAGS


class OpcUaReader:
    def __init__(
        self,
        *,
        endpoint: str,
        namespace_index: int = 2,
        lab_node: str = "Lab",
        motor_node: str = "Motor_001",
        tag_names: Iterable[str] = OPCUA_TAGS,
    ) -> None:
        self.endpoint = endpoint
        self.namespace_index = namespace_index
        self.lab_node = lab_node
        self.motor_node = motor_node
        self.tag_names = tuple(tag_names)

    async def read_motor_tags(self) -> dict[str, Any]:
        return await asyncio.to_thread(self.read_motor_tags_sync)

    def read_motor_tags_sync(self) -> dict[str, Any]:
        try:
            from opcua import Client
        except ImportError as exc:  # pragma: no cover - exercised only without dependency.
            raise SystemExit("opcua is required. Install dependencies with: python -m pip install -e .") from exc

        client = Client(self.endpoint)
        client.connect()
        try:
            root = client.nodes.objects
            lab = root.get_child([self._qualified(self.lab_node)])
            motor = lab.get_child([self._qualified(self.motor_node)])

            values: dict[str, Any] = {}
            for tag_name in self.tag_names:
                node = motor.get_child([self._qualified(tag_name)])
                values[tag_name] = node.get_value()

            return values
        finally:
            client.disconnect()

    def _qualified(self, browse_name: str) -> str:
        return f"{self.namespace_index}:{browse_name}"
