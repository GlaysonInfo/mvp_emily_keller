#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

if aws dynamodb describe-table \
  --table-name "$ALERTS_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "DynamoDB alerts table already exists: $ALERTS_TABLE"
else
  aws dynamodb create-table \
    --table-name "$ALERTS_TABLE" \
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
    --table-name "$ALERTS_TABLE" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

  echo "DynamoDB alerts table created: $ALERTS_TABLE"
fi
