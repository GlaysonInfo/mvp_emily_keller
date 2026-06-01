from __future__ import annotations

import os
from typing import Any, Iterable


SERVICE_CONDITION = "condition"
SERVICE_LUBRICATION = "lubrication"

ROLE_OPERADOR = "operador"
ROLE_TECNICO = "tecnico"
ROLE_CLIENTE_ADMIN = "cliente_admin"
ROLE_ADMIN = "admin"

SERVICE_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "service": "Monitoramento de Equipamentos e Maquinas",
        "module_key": SERVICE_CONDITION,
        "contract_scope": "Ativos rotativos, maquinas, sensores, gateways e diagnostico de condicao.",
        "operator_pages": [
            "Monitoramento de Equipamentos",
            "Visão Geral da Planta",
            "Detalhe do Ativo",
            "Alertas e Eventos",
            "Relatórios",
        ],
        "technician_pages": [
            "Monitoramento de Equipamentos",
            "Visão Geral da Planta",
            "Detalhe do Ativo",
            "Inteligência Operacional",
            "Alertas e Eventos",
            "Matriz de Escalonamento",
            "Notification Outbox",
            "Relatórios",
        ],
        "operator_view": [
            "Painel da planta com status por ativo, severidade, comunicacao e ultima leitura.",
            "Detalhe do ativo com vibracao, temperatura, ultrassom, horimetro e diagnostico atual.",
            "Alertas e eventos operacionais com acao recomendada e registro de atendimento.",
            "Relatorios de operacao e historico do ativo selecionado.",
        ],
        "technician_view": [
            "Cadastro tecnico de ativos, sensores, limites e contexto operacional por planta.",
            "Configurar protocolos e conectores do servico de condicao: OPC UA, MQTT, HTTPS e gateways.",
            "Ajustar regras de diagnostico, thresholds, janelas de historico e severidade.",
            "Analisar inteligencia operacional, tendencias, causas provaveis e recomendacoes.",
        ],
        "admin_view": [
            "Habilitar o servico de monitoramento de equipamentos por cliente e planta.",
            "Gerenciar conectores, credenciais, parametros globais, templates de alerta e notificacoes.",
            "Auditar eventos, processamentos, tenants, plantas e integracoes de campo.",
        ],
    },
    {
        "service": "Sistema de Lubrificacao",
        "module_key": SERVICE_LUBRICATION,
        "contract_scope": "Sistemas centralizados, saidas de graxa, ciclos, pressao e eficiencia de lubrificacao.",
        "operator_pages": [
            "Operação de Lubrificação",
            "Sistema de Lubrificação",
            "Eficiência da Lubrificação",
            "Alertas e Eventos",
            "Relatórios",
        ],
        "technician_pages": [
            "Operação de Lubrificação",
            "Sistema de Lubrificação",
            "Eficiência da Lubrificação",
            "Eficiência da Lubrificação do Motor",
            "Bancada Virtual — Lubrificação",
            "Configuração de Campo — Lubrificação",
            "Alertas e Eventos",
            "Matriz de Escalonamento",
            "Notification Outbox",
            "Relatórios",
        ],
        "operator_view": [
            "Painel do sistema com status das saidas, ciclo atual, anomalias e alertas ativos.",
            "Visualizacao de eficiencia de lubrificacao e impacto operacional por equipamento.",
            "Alertas de baixa pressao, alta pressao, alivio lento e falha de comunicacao.",
            "Relatorios de ciclos, ocorrencias e acoes tomadas pela operacao.",
        ],
        "technician_view": [
            "Configurar gateway IO-Link, pontos de lubrificacao, baselines e limites por saida.",
            "Executar bancada virtual, validacao de campo e ajuste de curvas por ciclo.",
            "Configurar regras de alerta/evento, matriz de escalonamento e notificacoes.",
            "Analisar eficiencia da lubrificacao do motor e recomendacoes tecnicas.",
        ],
        "admin_view": [
            "Habilitar o servico de lubrificacao por cliente, planta e sistema instalado.",
            "Gerenciar protocolos, conectores, modelos de configuracao de campo e templates de diagnostico.",
            "Auditar configuracoes, alteracoes de thresholds, integracoes e notificacoes emitidas.",
        ],
    },
]

ROLE_REQUIREMENTS = [
    {
        "Perfil": "Operador",
        "Escopo": "Operacao diaria do servico contratado.",
        "Pode": "Ver status, atender alertas, consultar detalhes, relatorios e recomendacoes.",
        "Nao pode": "Editar conectores, baselines, protocolos, tenants ou parametros globais.",
    },
    {
        "Perfil": "Tecnico",
        "Escopo": "Configuracao tecnica do proprio cliente/tenant.",
        "Pode": "Configurar campo, regras tecnicas, thresholds, escalonamento e validacoes.",
        "Nao pode": "Acessar outros clientes ou alterar parametros globais da plataforma.",
    },
    {
        "Perfil": "Cliente Admin",
        "Escopo": "Administracao do cliente dentro do proprio tenant.",
        "Pode": "Gerenciar plantas, usuarios do cliente, modulos contratados, notificacoes e politicas locais.",
        "Nao pode": "Criar tenants externos, alterar protocolos globais ou credenciais da plataforma.",
    },
    {
        "Perfil": "Admin do Sistema",
        "Escopo": "Administracao da plataforma e operacao multi-tenant.",
        "Pode": "Criar clientes, plantas, contratos de servico, conectores globais, protocolos e auditoria.",
        "Nao pode": "Executar operacao de campo sem trilha de auditoria e contexto de tenant/planta.",
    },
]

ADMIN_DOMAINS = [
    "Cadastro de clientes, plantas, usuarios e servicos contratados.",
    "Protocolos e conectores: OPC UA, MQTT, HTTPS, IO-Link gateway, API ingest e credenciais.",
    "Configuracoes de campo por servico: ativos/sensores para equipamentos, gateways/saidas para lubrificacao.",
    "Configuracoes de alertas, eventos, thresholds, severidade, SLA e matriz de escalonamento.",
    "Notificacoes: canais, destinatarios, templates, outbox, reprocessamento e auditoria.",
    "Governanca: isolamento por tenant/planta, logs de auditoria, retencao, exportacao e permissao.",
]

DUAL_SERVICE_REQUIREMENTS = [
    "O cliente pode contratar apenas Monitoramento de Equipamentos, apenas Sistema de Lubrificacao ou ambos.",
    "Quando os dois servicos estiverem ativos para a mesma planta, a Inteligencia Operacional deve correlacionar condicao do ativo, eficiencia de lubrificacao, alertas e historico.",
    "Menus e rotas devem ser filtrados por contrato de servico, perfil do usuario, tenant e planta.",
    "Dados devem carregar sempre com tenant_id, plant_id, module_key, asset_id e, quando aplicavel, lubrication_system_id/outlet_id.",
]

INCREMENTAL_DELIVERY_STEPS = [
    {
        "Passo": "1",
        "Entrega": "Mapa de modulos e permissoes",
        "Resultado": "Tela atual aprovada como contrato funcional para perfis, servicos e admin.",
    },
    {
        "Passo": "2",
        "Entrega": "Modelo de navegacao modular",
        "Resultado": "Menu central filtra por servico contratado e perfil sem regras espalhadas nas telas.",
    },
    {
        "Passo": "3",
        "Entrega": "Cliente Admin",
        "Resultado": "Novo perfil para plantas, usuarios do tenant, modulos contratados e configuracoes locais.",
    },
    {
        "Passo": "4",
        "Entrega": "Admin do Sistema",
        "Resultado": "Area global para tenants, protocolos, conectores, templates, auditoria e notificacoes.",
    },
    {
        "Passo": "5",
        "Entrega": "Claims reais de autenticacao",
        "Resultado": "Cognito/oauth2-proxy injeta tenant, planta, perfil e servicos habilitados no app.",
    },
]

GLOBAL_ADMIN_PAGES = ["Admin da Plataforma", "Configurações"]
ADMIN_DEV_PAGES = ["Arquitetura Modular", "Teste ponta a ponta"]
CLIENT_ADMIN_PAGES = ["Configurações", "Admin do Cliente"]
ALWAYS_OPERATOR_PAGES = ["Ajuda do Operador"]
_TRUE = {"1", "true", "yes", "on"}


def service_keys() -> set[str]:
    return {str(service["module_key"]) for service in SERVICE_BLUEPRINTS}


def normalize_service_keys(value: Iterable[str] | str | None) -> set[str]:
    if value is None:
        return service_keys()
    if isinstance(value, str):
        raw_items = value.replace(";", ",").split(",")
    else:
        raw_items = list(value)
    normalized = {str(item).strip().lower() for item in raw_items if str(item).strip()}
    return normalized & service_keys()


def services_for_contract(value: Iterable[str] | str | None) -> list[dict[str, Any]]:
    keys = normalize_service_keys(value)
    return [service for service in SERVICE_BLUEPRINTS if service["module_key"] in keys]


def has_operational_intelligence(value: Iterable[str] | str | None) -> bool:
    keys = normalize_service_keys(value)
    return {SERVICE_CONDITION, SERVICE_LUBRICATION}.issubset(keys)


def _append_unique(target: list[str], pages: Iterable[str]) -> None:
    for page in pages:
        if page not in target:
            target.append(page)


def admin_dev_pages_enabled() -> bool:
    return os.getenv("DASHBOARD_SHOW_ADMIN_DEV_TOOLS", "").strip().lower() in _TRUE


def routes_for_context(role: str | None, contracted_services: Iterable[str] | str | None = None) -> list[str]:
    role = role or ""
    routes: list[str] = []
    services = services_for_contract(contracted_services)

    if role == ROLE_OPERADOR:
        for service in services:
            _append_unique(routes, service["operator_pages"])
        _append_unique(routes, ALWAYS_OPERATOR_PAGES)
        return routes

    if role == ROLE_TECNICO:
        for service in services:
            _append_unique(routes, service["technician_pages"])
        return routes

    if role == ROLE_CLIENTE_ADMIN:
        _append_unique(routes, CLIENT_ADMIN_PAGES)
        return routes

    if role == ROLE_ADMIN:
        _append_unique(routes, GLOBAL_ADMIN_PAGES)
        if admin_dev_pages_enabled():
            _append_unique(routes, ADMIN_DEV_PAGES)
        return routes

    return []


def default_route_for_role(role: str | None, routes: Iterable[str]) -> str | None:
    available = list(routes)
    preferred_by_role = {
        ROLE_ADMIN: ["Admin da Plataforma", "Configurações"],
        ROLE_CLIENTE_ADMIN: ["Admin do Cliente", "Visão Geral da Planta"],
        ROLE_TECNICO: [
            "Monitoramento de Equipamentos",
            "Operação de Lubrificação",
            "Inteligência Operacional",
            "Visão Geral da Planta",
        ],
        ROLE_OPERADOR: [
            "Monitoramento de Equipamentos",
            "Operação de Lubrificação",
            "Visão Geral da Planta",
            "Sistema de Lubrificação",
        ],
    }
    for route in preferred_by_role.get(role or "", []):
        if route in available:
            return route
    return available[0] if available else None
