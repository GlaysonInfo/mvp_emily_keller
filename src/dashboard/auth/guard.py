"""Helpers de autenticação/RBAC para uso dentro do app Streamlit.

Uso típico em src/dashboard/app.py (dentro de main()):

    from dashboard.auth.guard import (
        auth_enabled, enforce_authentication, enforce_page_access,
        resolve_tenant, render_identity_badge,
    )

    identity = None
    if auth_enabled():
        identity = enforce_authentication()        # para a execução se não houver login
        tenant_id = resolve_tenant(identity, tenant_id)
    ...
    hmi = render_hmi_sidebar(config=config)
    page = hmi["page"]
    if identity is not None:
        render_identity_badge(identity)
        enforce_page_access(identity, page)        # bloqueia páginas fora do perfil

Tudo fica inerte enquanto AUTH_ENABLED != "true".
"""

from __future__ import annotations

import os

try:  # import tardio/defensivo para não quebrar contextos sem streamlit
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

try:
    from dashboard.auth.identity import Identity, resolve_identity
    from dashboard.auth.rbac import allowed_pages, can, can_access
    from dashboard.module_registry import routes_for_context
    from dashboard.platform_admin_repository import PlatformAdminRepository
except ImportError:  # pragma: no cover - execução a partir da raiz do repo
    from src.dashboard.auth.identity import Identity, resolve_identity
    from src.dashboard.auth.rbac import allowed_pages, can, can_access
    from src.dashboard.module_registry import routes_for_context
    from src.dashboard.platform_admin_repository import PlatformAdminRepository


_TRUE = {"1", "true", "yes", "on"}


def auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "false").strip().lower() in _TRUE


def _signout_url() -> str:
    # URL de logout do oauth2-proxy (ajuste o caminho se necessário).
    explicit_url = os.getenv("AUTH_SIGNOUT_URL")
    if explicit_url:
        return explicit_url

    institutional_url = os.getenv("INSTITUTIONAL_SITE_URL")
    if institutional_url:
        return institutional_url

    if os.getenv("AUTH_DEV_IDENTITY") or os.getenv("DASHBOARD_DATA_MODE", "").strip().lower() in {"local", "demo", "offline"}:
        return "http://127.0.0.1:8081/"

    return "https://sentinelaindustrial.com.br/"


def enforce_authentication() -> Identity:
    """Garante login válido; se não houver, renderiza aviso e interrompe a página."""
    identity = resolve_identity()
    if identity is None or not identity.is_authenticated:
        if st is not None:
            st.title("Acesso restrito")
            st.warning(
                "Esta área exige autenticação. Sua sessão não foi reconhecida "
                "ou seu usuário não possui um perfil válido (Operador, Técnico "
                "ou Admin do Sistema). Entre pelo botão “Acesso ao Sistema” ou "
                "contate o administrador da plataforma."
            )
            st.stop()
        raise PermissionError("Usuário não autenticado.")
    return identity


def enforce_page_access(identity: Identity, page: str) -> None:
    """Bloqueia o acesso a uma página fora do perfil do usuário."""
    if can_access(identity.role, page):
        return
    if st is not None:
        st.error(
            f"Seu perfil ({identity.role or 'sem perfil'}) não tem acesso à "
            f"página “{page}”. Páginas disponíveis: "
            f"{', '.join(sorted(allowed_pages(identity.role))) or '—'}."
        )
        st.stop()
    raise PermissionError(f"Sem permissão para a página: {page}")


def contracted_services_for_identity(identity: Identity) -> list[str] | str | None:
    if identity.service_keys:
        return list(identity.service_keys)
    return os.getenv("AUTH_DEFAULT_SERVICES") or None


def contracted_services_for_context(
    identity: Identity,
    tenant_id: str | None = None,
    plant_id: str | None = None,
) -> list[str] | str | None:
    if identity.service_keys:
        return list(identity.service_keys)

    if tenant_id and plant_id:
        repo = PlatformAdminRepository(os.getenv("PLATFORM_ADMIN_STORE") or None)
        services = repo.services_for_contract(str(tenant_id), str(plant_id))
        if services is not None:
            return services

    return os.getenv("AUTH_DEFAULT_SERVICES") or None


def allowed_routes_for_identity(identity: Identity) -> list[str]:
    return routes_for_context(identity.role, contracted_services_for_identity(identity))


def allowed_routes_for_context(
    identity: Identity,
    tenant_id: str | None = None,
    plant_id: str | None = None,
) -> list[str]:
    return routes_for_context(identity.role, contracted_services_for_context(identity, tenant_id, plant_id))


def enforce_modular_page_access(
    identity: Identity,
    page: str,
    contracted_services: list[str] | str | None = None,
) -> None:
    contracted_services = contracted_services_for_identity(identity) if contracted_services is None else contracted_services

    available_pages = set(routes_for_context(identity.role, contracted_services))
    if page in available_pages:
        return
    if st is not None:
        st.error(
            f"Seu perfil ({identity.role or 'sem perfil'}) não tem acesso à "
            f"página “{page}”. Páginas disponíveis: "
            f"{', '.join(sorted(available_pages)) or '—'}."
        )
        st.stop()
    raise PermissionError(f"Sem permissão para a página: {page}")


def resolve_tenant(identity: Identity, env_default: str) -> str:
    """Define o tenant das consultas.

    - Operador/Técnico: sempre o próprio tenant da identidade (isolamento).
    - Admin do Sistema: pode operar em qualquer tenant (usa o padrão/seleção).
    """
    if can(identity.role, "cross_tenant"):
        return str(env_default)
    if identity.tenant_id:
        return str(identity.tenant_id)
    # Cliente sem tenant atribuído: não deve ver dados de ninguém.
    if st is not None:
        st.error(
            "Seu usuário não está associado a nenhum cliente (tenant). "
            "Contate o administrador da plataforma."
        )
        st.stop()
    raise PermissionError("Identidade de cliente sem tenant_id.")


def render_identity_badge(identity: Identity) -> None:
    """Exibe quem está logado e um link de logout na barra lateral."""
    if st is None:
        return
    role_label = {
        "admin": "Admin do Sistema",
        "cliente_admin": "Cliente Admin",
        "tecnico": "Técnico",
        "operador": "Operador",
    }.get(identity.role or "", "sem perfil")
    with st.sidebar:
        st.divider()
        st.caption(f"👤 {identity.display_name}")
        st.caption(f"Perfil: {role_label}")
        if identity.tenant_id and not can(identity.role, "cross_tenant"):
            st.caption(f"Cliente: {identity.tenant_id}")
        st.markdown(f"[Sair]({_signout_url()})")


def _admin_tenant_options(current_tenant: str) -> list[str]:
    """Lista de tenants que o Admin pode visualizar.

    Origem: variável de ambiente ADMIN_TENANTS (separada por vírgula). O tenant
    atual é sempre incluído. Duplicatas removidas preservando a ordem.
    """
    raw = os.getenv("ADMIN_TENANTS", "")
    tenants = [t.strip() for t in raw.split(",") if t.strip()]
    ordered: list[str] = []
    for tenant in [current_tenant, *tenants]:
        if tenant and tenant not in ordered:
            ordered.append(tenant)
    return ordered or [current_tenant]


def admin_tenant_selector(identity: Identity, current_tenant: str) -> str:
    """Seletor de cliente (tenant) para o Admin do Sistema.

    - Admin (cross_tenant): mostra um seletor na barra lateral e devolve o tenant
      escolhido (persistido na sessão).
    - Operador/Técnico: devolve o tenant atual sem alteração (isolamento).
    """
    if st is None or not can(identity.role, "cross_tenant"):
        return current_tenant

    options = _admin_tenant_options(current_tenant)
    # Inicializa/sanitiza a seleção sem conflitar 'index' com 'key'.
    if st.session_state.get("admin_tenant") not in options:
        st.session_state["admin_tenant"] = (
            current_tenant if current_tenant in options else options[0]
        )
    with st.sidebar:
        return st.selectbox("Cliente (tenant)", options, key="admin_tenant")
