from __future__ import annotations

import os


def cors_origins_from_env(env_name: str = "ALLOWED_ORIGINS") -> list[str]:
    """Return allowed CORS origins from a comma-separated env var.

    Empty means CORS is effectively disabled for browser origins. Use `*`
    explicitly only for local/demo environments that need permissive CORS.
    """
    raw = os.getenv(env_name, "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
