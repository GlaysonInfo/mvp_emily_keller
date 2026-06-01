"""Cognito Pre Token Generation (V1) — injeta o tenant como claim de topo.

Copia o atributo custom:tenant_id do usuário para um claim limpo `tenant_id`
no ID token, para que o oauth2-proxy possa repassá-lo como cabeçalho
(X-Auth-Request-Tenant) sem o prefixo "custom:".

Anexe esta função como gatilho "Pre token generation" do User Pool.
Veja docs/tenant_claim_setup.md (Abordagem B).
"""


def lambda_handler(event, context):
    attributes = event.get("request", {}).get("userAttributes", {}) or {}
    tenant = attributes.get("custom:tenant_id")

    if tenant:
        response = event.setdefault("response", {})
        response["claimsOverrideDetails"] = {
            "claimsToAddOrOverride": {"tenant_id": tenant},
        }

    return event
