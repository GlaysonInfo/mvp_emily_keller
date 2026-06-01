from __future__ import annotations

from src.api.http_config import cors_origins_from_env


def test_cors_origins_from_env_defaults_to_empty(monkeypatch) -> None:
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert cors_origins_from_env() == []


def test_cors_origins_from_env_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://app.sentinelaindustrial.com.br, https://sentinelaindustrial.com.br, ",
    )

    assert cors_origins_from_env() == [
        "https://app.sentinelaindustrial.com.br",
        "https://sentinelaindustrial.com.br",
    ]
