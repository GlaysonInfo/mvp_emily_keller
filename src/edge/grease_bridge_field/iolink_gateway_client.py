
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


def get_nested_value(data: dict, path: str):
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


class IOLinkGatewayClient:
    def __init__(self, config: dict):
        self.config = config
        self.gateway = config.get("gateway", {})
        self.timeout = int(self.gateway.get("read_timeout_sec", 5))

    def read_raw(self) -> dict[str, Any]:
        protocol = self.gateway.get("protocol", "http_json")

        if protocol == "http_json":
            return self._read_http_json()

        if protocol == "manual_csv":
            raise NotImplementedError("manual_csv deve ser tratado por importador separado.")

        raise NotImplementedError(f"Protocolo ainda não implementado: {protocol}")

    def _read_http_json(self) -> dict[str, Any]:
        endpoint = self.gateway.get("endpoint")
        if not endpoint:
            raise RuntimeError("Endpoint do gateway vazio.")

        headers = {"Accept": "application/json"}

        auth = self.gateway.get("authentication", {})
        token_env = auth.get("token_env")
        if token_env and os.getenv(token_env):
            headers["Authorization"] = f"Bearer {os.getenv(token_env)}"

        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)

    def read_pressures(self) -> dict[str, float]:
        raw = self.read_raw()
        pressures = {}

        for outlet in self.config.get("outlets", []):
            if not outlet.get("enabled", True):
                continue

            tag = outlet.get("gateway_tag_pressure")
            value = get_nested_value(raw, tag) if tag else None
            if value is None:
                continue

            pressures[outlet["outlet_id"]] = float(value)

        return pressures
