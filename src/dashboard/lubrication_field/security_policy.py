
from __future__ import annotations

import os


def get_ingest_token(config: dict) -> str | None:
    ingest = config.get("ingest_api", {})
    token_env = ingest.get("token_env") or "GREASE_INGEST_TOKEN"
    return os.getenv(token_env)


def is_ip_allowed(config: dict, source_ip: str) -> bool:
    allowed = config.get("ingest_api", {}).get("allowed_source_ips", [])
    if not allowed:
        return True
    return source_ip in allowed


def build_auth_headers(config: dict) -> dict[str, str]:
    token = get_ingest_token(config)
    if not token:
        return {}
    return {"X-API-Key": token}
