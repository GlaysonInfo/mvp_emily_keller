#!/usr/bin/env bash
# Cria a tabela DynamoDB da trilha de auditoria (quem alterou o quê e quando).
# pk = TENANT#<tenant_id>, sk = <iso_ts>#<event_id>  -> consultas por cliente/tempo.
set -euo pipefail
source "$(dirname "$0")/env.sh"

AUDIT_LOG_TABLE="${AUDIT_LOG_TABLE:-condition_audit_log}"

if aws dynamodb describe-table \
  --table-name "$AUDIT_LOG_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "DynamoDB audit table already exists: $AUDIT_LOG_TABLE"
else
  aws dynamodb create-table \
    --table-name "$AUDIT_LOG_TABLE" \
    --attribute-definitions \
      AttributeName=pk,AttributeType=S \
      AttributeName=sk,AttributeType=S \
    --key-schema \
      AttributeName=pk,KeyType=HASH \
      AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

  aws dynamodb wait table-exists \
    --table-name "$AUDIT_LOG_TABLE" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

  echo "DynamoDB audit table created: $AUDIT_LOG_TABLE"
fi
