#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${DYNAMODB_TABLE:=mvp_asset_state}"

aws dynamodb create-table \
  --region "$AWS_REGION" \
  --table-name "$DYNAMODB_TABLE" \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE

echo "DynamoDB table ready: $DYNAMODB_TABLE"

