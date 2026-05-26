from __future__ import annotations

import os
from ipaddress import ip_address, ip_network

from fastapi import Header, HTTPException, Request


def _client_ip(request: Request, forwarded_for: str | None) -> str:
    if forwarded_for:
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
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
) -> bool:
    expected = os.getenv("CONDITION_INGEST_TOKEN")
    allowed_ips_raw = os.getenv("CONDITION_ALLOWED_SOURCE_IPS", "")
    allowed_ips = [entry.strip() for entry in allowed_ips_raw.split(",") if entry.strip()]

    client_ip = _client_ip(request, x_forwarded_for)

    if not _ip_allowed(client_ip, allowed_ips):
        raise HTTPException(status_code=403, detail=f"IP não autorizado para ingestão: {client_ip}")

    if not expected:
        return True

    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()

    if x_api_key == expected or bearer == expected:
        return True

    raise HTTPException(status_code=401, detail="Token de ingestão inválido ou ausente.")
