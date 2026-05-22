from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpsPublisher:
    def __init__(self, *, endpoint: str, timeout_seconds: float = 10.0) -> None:
        if not endpoint:
            raise ValueError("endpoint is required for HTTPS publishing")

        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def publish(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = response.getcode()
        except HTTPError as exc:
            raise RuntimeError(f"Falha ao publicar HTTPS. status={exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Falha ao publicar HTTPS. erro={exc.reason}") from exc

        if status >= 400:
            raise RuntimeError(f"Falha ao publicar HTTPS. status={status}")

