from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


def get_nested_value(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


class ConditionGatewayClient:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.gateway = config.get("gateway", {})
        self.timeout = int(self.gateway.get("read_timeout_sec", 5))

    def read_raw(self) -> dict[str, Any]:
        protocol = self.gateway.get("protocol", "http_json")

        if protocol == "simulated_json":
            return self._read_simulated_json()

        if protocol == "http_json":
            return self._read_http_json()

        raise NotImplementedError(f"Unsupported gateway protocol: {protocol}")

    def _read_simulated_json(self) -> dict[str, Any]:
        sample_path = self.gateway.get("sample_path") or "src/edge/condition_bridge_field/sample_raw_gateway_response.json"
        return json.loads(Path(sample_path).read_text(encoding="utf-8"))

    def _read_http_json(self) -> dict[str, Any]:
        endpoint = self.gateway.get("endpoint")
        if not endpoint:
            raise RuntimeError("Gateway endpoint is empty.")

        headers = {"Accept": "application/json"}
        auth = self.gateway.get("authentication", {})
        token_env = auth.get("token_env")
        if token_env and os.getenv(token_env):
            headers["Authorization"] = f"Bearer {os.getenv(token_env)}"

        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
