#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

ALERT_PK="${ALERT_PK:-TENANT#cliente_demo#ASSET#motor_001}"

echo "Checking active alerts in ${ALERTS_TABLE}:"
aws dynamodb query \
  --table-name "$ALERTS_TABLE" \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values "{\":pk\":{\"S\":\"${ALERT_PK}\"}}" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
