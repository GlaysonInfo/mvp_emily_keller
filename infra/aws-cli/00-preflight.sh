#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

echo "== Preflight AWS MVP =="
echo
echo "AWS_PROFILE=${AWS_PROFILE}"
echo "AWS_REGION=${AWS_REGION}"
echo "PROJECT=${PROJECT}"
echo "STAGE=${STAGE}"

ACCOUNT_ID="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)"
ARN="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Arn --output text)"

echo "ACCOUNT_ID=${ACCOUNT_ID}"
echo "ARN=${ARN}"
echo
echo "Recursos que serao usados/criados:"
echo "RAW_BUCKET=${RAW_BUCKET}"
echo "DDB_TABLE=${DDB_TABLE}"
echo "TIMESTREAM_DB=${TIMESTREAM_DB}"
echo "TIMESTREAM_TABLE=${TIMESTREAM_TABLE}"
echo "LAMBDA_NAME=${LAMBDA_NAME}"
echo "LAMBDA_ROLE_NAME=${LAMBDA_ROLE_NAME}"
echo "EVENT_BUS=${EVENT_BUS}"
echo
read -r -p "Confirmar execucao nesta conta/regiao? Digite YES: " CONFIRM

if [[ "$CONFIRM" != "YES" ]]; then
  echo "Abortado pelo usuario."
  exit 1
fi

echo "Preflight OK."

