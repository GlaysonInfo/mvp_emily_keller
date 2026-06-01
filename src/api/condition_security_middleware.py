from __future__ import annotations

import hmac
import os
from ipaddress import ip_address, ip_network

from fastapi import Header, HTTPException, Request

_DISABLE_VALUES = {"0", "false", "no", "off"}


def _require_token() -> bool:
    """Por padrão a ingestão exige token (fail-closed).

    Para laboratório/dev/testes, defina CONDITION_REQUIRE_TOKEN=false para desativar.
    """
    return os.getenv("CONDITION_REQUIRE_TOKEN", "true").strip().lower() not in _DISABLE_VALUES


def _token_matches(expected: str, candidates: list[str]) -> bool:
    return any(c and hmac.compare_digest(c, expected) for c in candidates)


def _client_ip(
    request: Request,
    trusted_client_ip: str | None,
    forwarded_for: str | None,
) -> str:
    if trusted_client_ip:
        return trusted_client_ip.strip()
    if os.getenv("CONDITION_TRUST_X_FORWARDED_FOR", "").strip().lower() in {"1", "true", "yes", "on"} and forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


def _ip_allowed(client_ip: str, allowed_entries: list[str]) -> bool:
    if not allowed_entries:
        return True

    try:
        parsed_ip = ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowed_entries:
        try:
            if "/" in entry and parsed_ip in ip_network(entry, strict=False):
                return True
            if parsed_ip == ip_address(entry):
                return True
        except ValueError:
            if client_ip == entry:
                return True

    return False


def validate_condition_ingest_security(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_trusted_client_ip: str | None = Header(default=None, alias="X-Trusted-Client-IP"),
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
) -> bool:
    expected = os.getenv("CONDITION_INGEST_TOKEN")
    allowed_ips_raw = os.getenv("CONDITION_ALLOWED_SOURCE_IPS", "")
    allowed_ips = [entry.strip() for entry in allowed_ips_raw.split(",") if entry.strip()]

    client_ip = _client_ip(request, x_trusted_client_ip, x_forwarded_for)

    if not _ip_allowed(client_ip, allowed_ips):
        raise HTTPException(status_code=403, detail=f"IP não autorizado para ingestão: {client_ip}")

    if not expected:
        # Fail-closed: sem token configurado, a ingestão fica indisponível
        # (a menos que CONDITION_REQUIRE_TOKEN=false, apenas para laboratório/dev).
        if _require_token():
            raise HTTPException(
                status_code=503,
                detail="Ingestão indisponível: token de autenticação não configurado no servidor.",
            )
        return True

    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()

    if _token_matches(expected, [x_api_key or "", bearer]):
        return True

    raise HTTPException(status_code=401, detail="Token de ingestão inválido ou ausente.")
