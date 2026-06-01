"""Resolução da identidade do usuário a partir do proxy de autenticação.

A identidade é produzida pelo oauth2-proxy/ALB após validar o token do
AWS Cognito e repassada ao Streamlit por cabeçalhos HTTP. Aqui nós apenas
lemos esses cabeçalhos (nunca confiamos em entrada do navegador diretamente —
em produção o nginx deve sobrescrever esses cabeçalhos com os valores do
auth_request, impedindo falsificação pelo cliente).

Para desenvolvimento local sem o proxy, defina AUTH_DEV_IDENTITY, ex.:
    AUTH_DEV_IDENTITY='{"email":"tec@cliente.com","groups":["CLIENTE_TECNICO","TENANT_cliente_demo"]}'
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field

try:
    from dashboard.module_registry import normalize_service_keys
except ImportError:  # pragma: no cover - supports tests/imports from repository root.
    from src.dashboard.module_registry import normalize_service_keys

from .rbac import normalize_role, role_from_groups


@dataclass
class Identity:
    email: str
    name: str
    groups: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    role: str | None = None
    service_keys: list[str] = field(default_factory=list)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.email) and self.role is not None

    @property
    def display_name(self) -> str:
        return self.name or self.email or "usuário"


def _header_name(env_name: str, default: str) -> str:
    return os.getenv(env_name, default).strip().lower()


# Nomes de cabeçalho (configuráveis) que o proxy injeta.
_HDR_EMAIL = _header_name("AUTH_HEADER_EMAIL", "x-forwarded-email")
_HDR_USER = _header_name("AUTH_HEADER_USER", "x-forwarded-user")
_HDR_GROUPS = _header_name("AUTH_HEADER_GROUPS", "x-forwarded-groups")
_HDR_TENANT = _header_name("AUTH_HEADER_TENANT", "x-forwarded-tenant")
_HDR_SERVICES = _header_name("AUTH_HEADER_SERVICES", "x-forwarded-services")

# Convenção opcional de tenant via grupo do Cognito: um grupo no formato
# "TENANT_<id>" (ex.: TENANT_cliente_demo) define o cliente do usuário.
# Usado como fallback quando o cabeçalho de tenant não está presente —
# permite multi-tenant sem config alpha do oauth2-proxy nem Lambda.
_TENANT_GROUP_PREFIX = os.getenv("AUTH_TENANT_GROUP_PREFIX", "TENANT_")
_SERVICE_GROUP_PREFIX = os.getenv("AUTH_SERVICE_GROUP_PREFIX", "SERVICE_")


def _tenant_from_groups(groups: list[str] | None) -> str | None:
    prefix = _TENANT_GROUP_PREFIX
    for group in groups or []:
        if group.startswith(prefix) and len(group) > len(prefix):
            return group[len(prefix):]
    return None


def _resolve_tenant(header_tenant: str | None, groups: list[str]) -> str | None:
    # Precedência: cabeçalho explícito do proxy > convenção de grupo TENANT_.
    return (header_tenant or None) or _tenant_from_groups(groups)


def _services_from_groups(groups: list[str] | None) -> list[str]:
    prefix = _SERVICE_GROUP_PREFIX
    services = [
        group[len(prefix):]
        for group in groups or []
        if group.startswith(prefix) and len(group) > len(prefix)
    ]
    return sorted(normalize_service_keys(services))


def _resolve_services(raw_services: list[str] | str | None, groups: list[str]) -> list[str]:
    if raw_services:
        return sorted(normalize_service_keys(raw_services))
    return _services_from_groups(groups)


# ---------------------------------------------------------------------------
# Modo ALB + Cognito nativo (sem oauth2-proxy). Defina AUTH_PROVIDER=alb.
# O ALB autentica e injeta o cabeçalho assinado x-amzn-oidc-data (um JWT cujo
# payload traz os claims do usuário). Aqui decodificamos apenas o payload.
# NÃO verificamos a assinatura: isso só é seguro porque a instância aceita
# tráfego apenas do ALB (security group em infra/alb). Para verificação de
# assinatura, ver docs/migracao_alb_cognito.md.
# Observação: cognito:groups pode não vir no x-amzn-oidc-data (deriva do
# userInfo); por isso o papel também é lido de custom:role, e o tenant de
# custom:tenant_id. Veja o doc da migração.
# ---------------------------------------------------------------------------
_AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "proxy").strip().lower()
# x-amzn-oidc-data: claims do userInfo (email, custom:*) — sem cognito:groups.
_HDR_ALB_DATA = _header_name("AUTH_HEADER_ALB_DATA", "x-amzn-oidc-data")
# x-amzn-oidc-accesstoken: access token do Cognito — COM cognito:groups.
_HDR_ALB_ACCESS = _header_name("AUTH_HEADER_ALB_ACCESS", "x-amzn-oidc-accesstoken")


def _b64url_json(segment: str) -> dict:
    padding = "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(segment + padding).decode("utf-8"))


def _decode_jwt_payload(raw: str | None) -> dict | None:
    if not raw or raw.count(".") < 2:
        return None
    try:
        return _b64url_json(raw.split(".")[1])
    except Exception:
        return None


def _alb_claims(headers: dict[str, str]) -> dict | None:
    return _decode_jwt_payload(headers.get(_HDR_ALB_DATA))


def _alb_access_claims(headers: dict[str, str]) -> dict | None:
    return _decode_jwt_payload(headers.get(_HDR_ALB_ACCESS))


def _groups_from_claims(claims: dict) -> list[str]:
    groups = claims.get("cognito:groups") or claims.get("groups") or []
    if isinstance(groups, str):
        return _split_groups(groups)
    return [str(g) for g in groups]


def _identity_from_alb(headers: dict[str, str]) -> Identity | None:
    claims = _alb_claims(headers) or {}
    access = _alb_access_claims(headers) or {}
    if not claims and not access:
        return None

    email = str(
        claims.get("email")
        or access.get("username")
        or access.get("cognito:username")
        or claims.get("cognito:username")
        or ""
    )
    if not email:
        return None

    # Grupos vêm do access token (que carrega cognito:groups); fallback no data.
    groups = _groups_from_claims(access) or _groups_from_claims(claims)
    # Papel: grupos (modelo padrão) e, como fallback opcional, custom:role.
    role = role_from_groups(groups) or normalize_role(claims.get("custom:role") or claims.get("role"))
    tenant = (
        claims.get("custom:tenant_id")
        or claims.get("tenant_id")
        or _tenant_from_groups(groups)
    )
    return Identity(
        email=email,
        name=str(claims.get("name") or email),
        groups=groups,
        tenant_id=tenant,
        role=role,
        service_keys=_resolve_services(claims.get("custom:services") or claims.get("services"), groups),
    )


def _request_headers() -> dict[str, str]:
    """Lê os cabeçalhos da requisição atual (Streamlit >= 1.37)."""
    try:
        import streamlit as st

        ctx = getattr(st, "context", None)
        headers = getattr(ctx, "headers", None) if ctx is not None else None
        if headers:
            return {str(k).lower(): str(v) for k, v in dict(headers).items()}
    except Exception:
        pass
    return {}


def _split_groups(raw: str | None) -> list[str]:
    if not raw:
        return []
    # oauth2-proxy separa por vírgula; toleramos espaços/; também.
    parts = [p.strip() for chunk in raw.split(",") for p in chunk.split(";")]
    return [p for p in parts if p]


def _dev_identity() -> Identity | None:
    raw = os.getenv("AUTH_DEV_IDENTITY")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    groups = data.get("groups") or []
    if isinstance(groups, str):
        groups = _split_groups(groups)
    groups = list(groups)
    return Identity(
        email=str(data.get("email") or ""),
        name=str(data.get("name") or data.get("email") or ""),
        groups=groups,
        tenant_id=_resolve_tenant(data.get("tenant_id"), groups),
        role=role_from_groups(groups),
        service_keys=_resolve_services(data.get("services"), groups),
    )


def resolve_identity() -> Identity | None:
    """Retorna a Identity do usuário autenticado, ou None se não houver login válido."""
    dev = _dev_identity()
    if dev is not None:
        return dev

    headers = _request_headers()

    if _AUTH_PROVIDER == "alb":
        return _identity_from_alb(headers)

    email = headers.get(_HDR_EMAIL, "")
    if not email:
        return None

    groups = _split_groups(headers.get(_HDR_GROUPS))
    return Identity(
        email=email,
        name=headers.get(_HDR_USER, "") or email,
        groups=groups,
        tenant_id=_resolve_tenant(headers.get(_HDR_TENANT), groups),
        role=role_from_groups(groups),
        service_keys=_resolve_services(headers.get(_HDR_SERVICES), groups),
    )
