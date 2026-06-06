from __future__ import annotations

from typing import Any, Mapping


ASSISTED_PRODUCTION_CHECKS = [
    {
        "id": "real_machine_identified",
        "item": "Máquina real identificada",
        "criterion": "Ativo físico, tag/local e criticidade confirmados.",
        "owner": "Sentinela + Cliente",
    },
    {
        "id": "real_sensors_installed",
        "item": "Sensores reais instalados",
        "criterion": "Sensores, grandezas e pontos de medição conferidos em campo.",
        "owner": "Técnico",
    },
    {
        "id": "gateway_registered",
        "item": "Gateway cadastrado",
        "criterion": "Fonte/gateway vinculada à planta e ao ativo correto.",
        "owner": "Sentinela",
    },
    {
        "id": "https_endpoint_validated",
        "item": "Endpoint HTTPS validado",
        "criterion": "Gateway alcança o endpoint de ingestão por HTTPS.",
        "owner": "Técnico",
    },
    {
        "id": "token_configured",
        "item": "Token configurado",
        "criterion": "Token de ingestão configurado no gateway sem exposição em tela ou arquivo versionado.",
        "owner": "Sentinela",
    },
    {
        "id": "first_payload_received",
        "item": "Primeiro payload recebido",
        "criterion": "Payload real gravado com tenant, planta, ativo e timestamp corretos.",
        "owner": "Sentinela",
    },
    {
        "id": "last_communication_visible",
        "item": "Última comunicação visível",
        "criterion": "Dashboard mostra comunicação recente do ativo real.",
        "owner": "Sentinela",
    },
    {
        "id": "test_alert_generated",
        "item": "Alerta de teste gerado",
        "criterion": "Cenário controlado gera alerta esperado sem afetar operação real.",
        "owner": "Sentinela + Técnico",
    },
    {
        "id": "test_alert_acknowledged",
        "item": "Alerta reconhecido/tratado",
        "criterion": "Fluxo de ciência e tratamento foi executado por usuário autorizado.",
        "owner": "Operação",
    },
    {
        "id": "stop_criteria_defined",
        "item": "Critério de parada definido",
        "criterion": "Condições de pausa do teste, contato responsável e fallback documentados.",
        "owner": "Sentinela + Cliente",
    },
]

REQUIRED_ASSISTED_CHECK_IDS = tuple(str(item["id"]) for item in ASSISTED_PRODUCTION_CHECKS)
REQUIRED_ASSISTED_CONTEXT_FIELDS = (
    "machine_id",
    "gateway_id",
    "responsible",
    "endpoint_url",
    "stop_criteria",
)


def release_blockers(run: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    manual_steps = dict(run.get("manual_steps") or {})
    checks = dict(run.get("assisted_checks") or {})
    context = dict(run.get("assisted_context") or {})

    if not manual_steps.get("commissioning"):
        blockers.append("Registrar a validação de ingestão, baseline e alertas.")

    missing_checks = [check_id for check_id in REQUIRED_ASSISTED_CHECK_IDS if not checks.get(check_id)]
    if missing_checks:
        blockers.append(f"Concluir os {len(missing_checks)} itens pendentes do checklist indoor.")

    missing_context = [field for field in REQUIRED_ASSISTED_CONTEXT_FIELDS if not str(context.get(field) or "").strip()]
    if missing_context:
        blockers.append("Preencher máquina, gateway, responsável, endpoint e critério de parada.")

    return blockers


def onboarding_release_ready(run: Mapping[str, Any]) -> bool:
    return not release_blockers(run)


def validate_onboarding_release(run: Mapping[str, Any]) -> None:
    manual_steps = dict(run.get("manual_steps") or {})
    release_requested = bool(manual_steps.get("release")) or str(run.get("status") or "") == "Liberado"
    if not release_requested:
        return
    blockers = release_blockers(run)
    if blockers:
        raise ValueError("Onboarding não pode ser liberado: " + " ".join(blockers))
