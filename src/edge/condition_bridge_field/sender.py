from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


class ConditionIngestSender:
    def __init__(self, config: dict[str, Any]):
        ingest = config.get("ingest_api", {})
        self.endpoint = os.getenv("CONDITION_INGEST_ENDPOINT") or ingest.get("endpoint")
        self.token_env = ingest.get("token_env") or "CONDITION_INGEST_TOKEN"
        self.max_attempts = max(1, int(os.getenv("CONDITION_INGEST_MAX_ATTEMPTS") or ingest.get("max_attempts") or 3))
        self.backoff_sec = max(
            0.0,
            float(os.getenv("CONDITION_INGEST_BACKOFF_SEC") or ingest.get("backoff_sec") or 1.0),
        )

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

    def send_with_retry(self, payload: dict[str, Any], timeout_sec: int = 15) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.send(payload, timeout_sec=timeout_sec)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_sec * (2 ** (attempt - 1)))
        assert last_error is not None
        raise last_error
