#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

aws lambda invoke \
  --function-name "$LAMBDA_NAME" \
  --payload fileb://infra/aws-cli/sample-payload.json \
  --cli-binary-format raw-in-base64-out \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  build/aws/lambda-response.json >/dev/null

cat build/aws/lambda-response.json
echo

