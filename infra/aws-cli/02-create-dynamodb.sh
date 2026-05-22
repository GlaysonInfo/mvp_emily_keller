#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

if aws dynamodb describe-table \
  --table-name "$DDB_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "DynamoDB table already exists: $DDB_TABLE"
else
  aws dynamodb create-table \
    --table-name "$DDB_TABLE" \
    --attribute-definitions \
      AttributeName=pk,AttributeType=S \
      AttributeName=sk,AttributeType=S \
    --key-schema \
      AttributeName=pk,KeyType=HASH \
      AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  aws dynamodb wait table-exists \
    --table-name "$DDB_TABLE" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "DynamoDB table created: $DDB_TABLE"
fi

