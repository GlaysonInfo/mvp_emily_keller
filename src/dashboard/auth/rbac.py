"""Controle de acesso por perfil (RBAC) e mapeamento de grupos do Cognito.

Perfis:
    - ADMIN_SERVER     -> admin do sistema (toda a plataforma, todos os tenants)
    - CLIENTE_ADMIN    -> admin do cliente (usuarios, plantas e contratos do tenant)
    - CLIENTE_TECNICO  -> técnico do cliente (configura o que é do seu tenant)
    - CLIENTE_OPERADOR -> operador do cliente (opera, sem editar configuração)

A separação Operador/Técnico, hoje apenas visual no app, passa a ser efetiva:
cada página e cada capacidade ("capability") fica restrita ao perfil.
"""

from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_CLIENTE_ADMIN = "cliente_admin"
ROLE_TECNICO = "tecnico"
ROLE_OPERADOR = "operador"

# Grupo do Cognito -> perfil interno
GROUP_TO_ROLE = {
    "ADMIN_SERVER": ROLE_ADMIN,
    "CLIENTE_ADMIN": ROLE_CLIENTE_ADMIN,
    "CLIENTE_TECNICO": ROLE_TECNICO,
    "CLIENTE_OPERADOR": ROLE_OPERADOR,
}

# Páginas visíveis ao Operador (operação de campo).
OPERATOR_PAGES = {
    "Monitoramento de Equipamentos",
    "Visão Geral da Planta",
    "Detalhe do Ativo",
    "Operação de Lubrificação",
    "Sistema de Lubrificação",
    "Eficiência da Lubrificação",
    "Alertas e Eventos",
    "Relatórios",
    "Ajuda do Operador",
}

# Páginas adicionais do Técnico (configuração do próprio cliente/tenant).
TECNICO_EXTRA_PAGES = {
    "Monitoramento de Equipamentos",
    "Inteligência Operacional",
    "Eficiência da Lubrificação do Motor",
    "Bancada Virtual — Lubrificação",
    "Configuração de Campo — Lubrificação",
    "Matriz de Escalonamento",
    "Notification Outbox",
}

# Páginas exclusivas do Admin do Sistema (configuração global do servidor).
ADMIN_EXTRA_PAGES = {
    "Configurações",
    "Admin da Plataforma",
    "Arquitetura Modular",
    "Teste ponta a ponta",
}

TECNICO_PAGES = OPERATOR_PAGES | TECNICO_EXTRA_PAGES
CLIENTE_ADMIN_PAGES = {"Configurações", "Admin do Cliente"}
ADMIN_PAGES = ADMIN_EXTRA_PAGES

_PAGES_BY_ROLE = {
    ROLE_ADMIN: ADMIN_PAGES,
    ROLE_CLIENTE_ADMIN: CLIENTE_ADMIN_PAGES,
    ROLE_TECNICO: TECNICO_PAGES,
    ROLE_OPERADOR: OPERATOR_PAGES,
}

# Capacidades (ações sensíveis) por perfil.
_CAPABILITIES = {
    "view_dashboard": {ROLE_ADMIN, ROLE_CLIENTE_ADMIN, ROLE_TECNICO, ROLE_OPERADOR},
    "handle_alerts": {ROLE_ADMIN, ROLE_CLIENTE_ADMIN, ROLE_TECNICO, ROLE_OPERADOR},
    "edit_field_config": {ROLE_ADMIN, ROLE_TECNICO},
    "edit_alert_params": {ROLE_ADMIN, ROLE_TECNICO},
    "edit_client_config": {ROLE_ADMIN, ROLE_CLIENTE_ADMIN},
    "manage_client_users": {ROLE_ADMIN, ROLE_CLIENTE_ADMIN},
    "edit_server_config": {ROLE_ADMIN},
    "manage_tenants": {ROLE_ADMIN},
    "cross_tenant": {ROLE_ADMIN},  # ver dados de mais de um cliente
}


def role_from_groups(groups: list[str] | None) -> str | None:
    """Resolve o perfil a partir dos grupos do Cognito (precedência admin > técnico > operador)."""
    if not groups:
        return None
    for group in ("ADMIN_SERVER", "CLIENTE_ADMIN", "CLIENTE_TECNICO", "CLIENTE_OPERADOR"):
        if group in groups:
            return GROUP_TO_ROLE[group]
    return None


# Normaliza um valor de papel vindo de um claim (ex.: custom:role no modo ALB)
# para uma das constantes internas. Aceita nomes de grupo, pt-BR e inglês.
_ROLE_ALIASES = {
    "admin": ROLE_ADMIN,
    "admin_server": ROLE_ADMIN,
    "administrator": ROLE_ADMIN,
    "cliente_admin": ROLE_CLIENTE_ADMIN,
    "client_admin": ROLE_CLIENTE_ADMIN,
    "tenant_admin": ROLE_CLIENTE_ADMIN,
    "tecnico": ROLE_TECNICO,
    "técnico": ROLE_TECNICO,
    "technician": ROLE_TECNICO,
    "cliente_tecnico": ROLE_TECNICO,
    "operador": ROLE_OPERADOR,
    "operator": ROLE_OPERADOR,
    "cliente_operador": ROLE_OPERADOR,
}


def normalize_role(value: str | None) -> str | None:
    if not value:
        return None
    return _ROLE_ALIASES.get(str(value).strip().lower())


def allowed_pages(role: str | None) -> set[str]:
    return set(_PAGES_BY_ROLE.get(role or "", set()))


def can_access(role: str | None, page: str) -> bool:
    return page in allowed_pages(role)


def can(role: str | None, capability: str) -> bool:
    return (role or "") in _CAPABILITIES.get(capability, set())
