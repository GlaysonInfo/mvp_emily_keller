#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

LAMBDA_ZIP="build/lambda/ingest_lambda.zip"

if [ ! -f "$LAMBDA_ZIP" ]; then
  echo "Lambda package not found. Run infra/aws-cli/05-package-lambda.sh first."
  exit 1
fi

ROLE_ARN="$(aws iam get-role \
  --role-name "$ALERT_LAMBDA_ROLE_NAME" \
  --query Role.Arn \
  --output text \
  --profile "$AWS_PROFILE")"

if aws lambda get-function \
  --function-name "$ALERT_LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$ALERT_LAMBDA_NAME" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" >/dev/null

  aws lambda wait function-updated \
    --function-name "$ALERT_LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Alert Lambda code updated: $ALERT_LAMBDA_NAME"
else
  aws lambda create-function \
    --function-name "$ALERT_LAMBDA_NAME" \
    --runtime python3.12 \
    --handler aws_lambdas.alert_processor_lambda.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},ALERTS_TABLE=${ALERTS_TABLE}}" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" >/dev/null

  aws lambda wait function-active \
    --function-name "$ALERT_LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Alert Lambda created: $ALERT_LAMBDA_NAME"
fi

aws lambda update-function-configuration \
  --function-name "$ALERT_LAMBDA_NAME" \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},ALERTS_TABLE=${ALERTS_TABLE}}" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

echo "Alert Lambda configuration ready: $ALERT_LAMBDA_NAME"
