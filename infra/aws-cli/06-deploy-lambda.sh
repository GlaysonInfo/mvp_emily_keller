#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

LAMBDA_ZIP="build/lambda/ingest_lambda.zip"

if [ ! -f "$LAMBDA_ZIP" ]; then
  echo "Lambda package not found. Run infra/aws-cli/05-package-lambda.sh first."
  exit 1
fi

ROLE_ARN="$(aws iam get-role \
  --role-name "$LAMBDA_ROLE_NAME" \
  --query Role.Arn \
  --output text \
  --profile "$AWS_PROFILE")"

if aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" >/dev/null

  aws lambda wait function-updated \
    --function-name "$LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Lambda code updated: $LAMBDA_NAME"
else
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.12 \
    --handler aws_lambdas.ingest_lambda.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={RAW_BUCKET=${RAW_BUCKET},TIMESTREAM_DB=${TIMESTREAM_DB},TIMESTREAM_TABLE=${TIMESTREAM_TABLE},DYNAMODB_TABLE=${DYNAMODB_TABLE},EVENT_BUS=${EVENT_BUS}}" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" >/dev/null

  aws lambda wait function-active \
    --function-name "$LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Lambda created: $LAMBDA_NAME"
fi

aws lambda update-function-configuration \
  --function-name "$LAMBDA_NAME" \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={RAW_BUCKET=${RAW_BUCKET},TIMESTREAM_DB=${TIMESTREAM_DB},TIMESTREAM_TABLE=${TIMESTREAM_TABLE},DYNAMODB_TABLE=${DYNAMODB_TABLE},EVENT_BUS=${EVENT_BUS}}" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

echo "Lambda configuration ready: $LAMBDA_NAME"
