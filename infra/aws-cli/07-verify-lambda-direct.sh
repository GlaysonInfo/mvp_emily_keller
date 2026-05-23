#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

RAW_PREFIX="raw/tenant=cliente_demo/plant=lab_virtual/asset=motor_001/"

echo "Checking S3 raw payloads:"
aws s3 ls "s3://${RAW_BUCKET}/${RAW_PREFIX}" \
  --recursive \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  | tail -n 10

echo
echo "Checking DynamoDB latest item:"
aws dynamodb get-item \
  --table-name "$DDB_TABLE" \
  --key '{"pk":{"S":"TENANT#cliente_demo#ASSET#motor_001"},"sk":{"S":"LATEST"}}' \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
