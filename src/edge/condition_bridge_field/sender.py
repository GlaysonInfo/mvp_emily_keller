from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class ConditionIngestSender:
    def __init__(self, config: dict[str, Any]):
        ingest = config.get("ingest_api", {})
        self.endpoint = os.getenv("CONDITION_INGEST_ENDPOINT") or ingest.get("endpoint")
        self.token_env = ingest.get("token_env") or "CONDITION_INGEST_TOKEN"

    def send(self, payload: dict[str, Any], timeout_sec: int = 15) -> dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("Endpoint /condition/ingest is not configured.")

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
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
