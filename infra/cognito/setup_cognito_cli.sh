#!/usr/bin/env bash
# =====================================================================
# Alternativa ao Terraform: cria o essencial do Cognito via AWS CLI.
# Requer: aws cli v2 configurado com credenciais e permissão em cognito-idp.
# Uso:
#   REGION=us-east-1 APP_DOMAIN=app.sentinelaindustrial.com.br \
#   HOSTED_PREFIX=sentinela-industrial-login bash setup_cognito_cli.sh
# =====================================================================
set -euo pipefail

REGION="${REGION:-us-east-1}"
APP_DOMAIN="${APP_DOMAIN:-app.sentinelaindustrial.com.br}"
HOSTED_PREFIX="${HOSTED_PREFIX:-sentinela-industrial-login}"
POOL_NAME="${POOL_NAME:-sentinela-industrial-prod}"

echo ">> Criando User Pool ${POOL_NAME} em ${REGION}..."
POOL_ID=$(aws cognito-idp create-user-pool \
  --region "$REGION" \
  --pool-name "$POOL_NAME" \
  --username-attributes email \
  --auto-verified-attributes email \
  --schema Name=tenant_id,AttributeDataType=String,Mutable=true,Required=false \
  --policies 'PasswordPolicy={MinimumLength=12,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=true}' \
  --query 'UserPool.Id' --output text)
echo "   User Pool: ${POOL_ID}"

echo ">> Criando grupos (perfis)..."
for g in ADMIN_SERVER:1 CLIENTE_TECNICO:10 CLIENTE_OPERADOR:20; do
  NAME="${g%%:*}"; PREC="${g##*:}"
  aws cognito-idp create-group --region "$REGION" \
    --user-pool-id "$POOL_ID" --group-name "$NAME" --precedence "$PREC" >/dev/null
  echo "   grupo ${NAME} (precedence ${PREC})"
done

echo ">> Criando domínio do Hosted UI..."
aws cognito-idp create-user-pool-domain --region "$REGION" \
  --user-pool-id "$POOL_ID" --domain "$HOSTED_PREFIX" >/dev/null
echo "   https://${HOSTED_PREFIX}.auth.${REGION}.amazoncognito.com"

echo ">> Criando App Client confidencial..."
CLIENT_JSON=$(aws cognito-idp create-user-pool-client --region "$REGION" \
  --user-pool-id "$POOL_ID" \
  --client-name sentinela-app-client \
  --generate-secret \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client \
  --supported-identity-providers COGNITO \
  --callback-urls "https://${APP_DOMAIN}/oauth2/callback" \
  --logout-urls "https://${APP_DOMAIN}/" \
  --output json)

CLIENT_ID=$(echo "$CLIENT_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin)["UserPoolClient"]["ClientId"])')
CLIENT_SECRET=$(echo "$CLIENT_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin)["UserPoolClient"]["ClientSecret"])')

echo ""
echo "================= COPIE PARA oauth2-proxy.cfg ================="
echo "oidc_issuer_url = \"https://cognito-idp.${REGION}.amazonaws.com/${POOL_ID}\""
echo "client_id       = \"${CLIENT_ID}\""
echo "client_secret   = \"${CLIENT_SECRET}\""
echo "=============================================================="
echo ""
echo "Crie um usuário de teste:"
echo "  aws cognito-idp admin-create-user --region ${REGION} --user-pool-id ${POOL_ID} \\"
echo "    --username tecnico@cliente.com --user-attributes Name=email,Value=tecnico@cliente.com Name=custom:tenant_id,Value=cliente_demo"
echo "  aws cognito-idp admin-add-user-to-group --region ${REGION} --user-pool-id ${POOL_ID} \\"
echo "    --username tecnico@cliente.com --group-name CLIENTE_TECNICO"
