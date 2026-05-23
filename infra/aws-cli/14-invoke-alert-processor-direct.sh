#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

aws lambda invoke \
  --function-name "$ALERT_LAMBDA_NAME" \
  --payload fileb://infra/aws-cli/sample-alert-event.json \
  --cli-binary-format raw-in-base64-out \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  build/aws/alert-lambda-response.json >/dev/null

cat build/aws/alert-lambda-response.json
echo
