
from __future__ import annotations

import json
import os
import urllib.request


class GreaseIngestSender:
    def __init__(self, config: dict):
        self.config = config
        self.ingest = config.get("ingest_api", {})
        self.endpoint = self.ingest.get("endpoint")
        self.token_env = self.ingest.get("token_env") or "GREASE_INGEST_TOKEN"

    def send(self, payload: dict, timeout_sec: int = 10) -> dict:
        if not self.endpoint:
            raise RuntimeError("Endpoint /grease/ingest não configurado.")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        token = os.getenv(self.token_env)
        if token:
            headers["X-API-Key"] = token

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
