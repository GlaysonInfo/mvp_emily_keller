"""Camada de autenticação e RBAC da IHM.

Este pacote NÃO implementa o login em si — o login é feito por um proxy de
identidade (oauth2-proxy + AWS Cognito) colocado na frente do Streamlit.
A aplicação apenas LÊ a identidade já validada pelo proxy (via cabeçalhos
HTTP) e impõe o controle de acesso por perfil (RBAC) e por cliente (tenant).

Fluxo:
    Navegador -> oauth2-proxy (valida token Cognito) -> nginx -> Streamlit
    O proxy injeta cabeçalhos: X-Forwarded-Email, X-Forwarded-User,
    X-Forwarded-Groups, X-Forwarded-Tenant.

Ative o controle definindo a variável de ambiente AUTH_ENABLED=true.
Enquanto AUTH_ENABLED não for "true", o código permanece inerte e o
comportamento atual da aplicação não muda.
"""

from .identity import Identity, resolve_identity
from .rbac import (
    ROLE_ADMIN,
    ROLE_CLIENTE_ADMIN,
    ROLE_OPERADOR,
    ROLE_TECNICO,
    allowed_pages,
    can,
    can_access,
)

__all__ = [
    "Identity",
    "resolve_identity",
    "ROLE_ADMIN",
    "ROLE_CLIENTE_ADMIN",
    "ROLE_TECNICO",
    "ROLE_OPERADOR",
    "allowed_pages",
    "can",
    "can_access",
]
