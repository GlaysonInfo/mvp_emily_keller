#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

LAMBDA_ARN="$(aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --query Configuration.FunctionArn \
  --output text \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE")"

API_NAME="${PROJECT}-ingest-${STAGE}"

API_ID="$(aws apigatewayv2 create-api \
  --name "$API_NAME" \
  --protocol-type HTTP \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query ApiId \
  --output text)"

echo "$API_ID" > build/aws/http-api-id.txt

INTEGRATION_ID="$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri "$LAMBDA_ARN" \
  --payload-format-version 2.0 \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query IntegrationId \
  --output text)"

aws apigatewayv2 create-route \
  --api-id "$API_ID" \
  --route-key "POST /telemetry" \
  --target "integrations/${INTEGRATION_ID}" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

aws apigatewayv2 create-stage \
  --api-id "$API_ID" \
  --stage-name "$STAGE" \
  --auto-deploy \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

aws lambda add-permission \
  --function-name "$LAMBDA_NAME" \
  --statement-id "AllowHttpApiInvoke-${STAGE}-${API_ID}" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/POST/telemetry" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE}/telemetry"
echo "$API_URL" > build/aws/http-api-url.txt

echo "HTTP API ready: $API_URL"

