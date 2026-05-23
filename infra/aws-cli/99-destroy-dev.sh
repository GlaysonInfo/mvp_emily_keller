#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

mkdir -p build/aws

echo "== Destroy AWS MVP dev resources =="
echo
echo "AWS_PROFILE=${AWS_PROFILE}"
echo "AWS_REGION=${AWS_REGION}"
echo "RAW_BUCKET=${RAW_BUCKET}"
echo "DDB_TABLE=${DDB_TABLE}"
echo "ALERTS_TABLE=${ALERTS_TABLE}"
echo "TIMESTREAM_DB=${TIMESTREAM_DB}"
echo "TIMESTREAM_TABLE=${TIMESTREAM_TABLE}"
echo "LAMBDA_NAME=${LAMBDA_NAME}"
echo "LAMBDA_ROLE_NAME=${LAMBDA_ROLE_NAME}"
echo
echo "Ordem de remocao:"
echo "1. API Gateway HTTP API"
echo "2. Lambda"
echo "3. IAM inline/managed policies e role"
echo "4. Timestream table/database"
echo "5. DynamoDB alerts table"
echo "6. DynamoDB latest-state table"
echo "7. S3 objects"
echo "8. S3 bucket"
echo
read -r -p "Isto remove recursos AWS dev. Digite DESTROY para continuar: " CONFIRM

if [[ "$CONFIRM" != "DESTROY" ]]; then
  echo "Abortado pelo usuario."
  exit 1
fi

API_ID=""
if [ -f build/aws/http-api-id.txt ]; then
  API_ID="$(cat build/aws/http-api-id.txt)"
fi

if [ -z "$API_ID" ]; then
  API_NAME="${PROJECT}-ingest-${STAGE}"
  API_ID="$(aws apigatewayv2 get-apis \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query "Items[?Name=='${API_NAME}'].ApiId | [0]" \
    --output text 2>/dev/null || true)"

  if [ "$API_ID" = "None" ]; then
    API_ID=""
  fi
fi

if [ -n "$API_ID" ]; then
  aws apigatewayv2 delete-api \
    --api-id "$API_ID" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" || true
  echo "Deleted HTTP API: $API_ID"
else
  echo "HTTP API not found, skipping."
fi

if aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws lambda delete-function \
    --function-name "$LAMBDA_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"
  echo "Deleted Lambda: $LAMBDA_NAME"
else
  echo "Lambda not found, skipping."
fi

if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws iam detach-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    --profile "$AWS_PROFILE" || true

  aws iam delete-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-name "${LAMBDA_ROLE_NAME}-inline" \
    --profile "$AWS_PROFILE" || true

  aws iam delete-role \
    --role-name "$LAMBDA_ROLE_NAME" \
    --profile "$AWS_PROFILE"

  echo "Deleted IAM role: $LAMBDA_ROLE_NAME"
else
  echo "IAM role not found, skipping."
fi

if aws timestream-write describe-table \
  --database-name "$TIMESTREAM_DB" \
  --table-name "$TIMESTREAM_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws timestream-write delete-table \
    --database-name "$TIMESTREAM_DB" \
    --table-name "$TIMESTREAM_TABLE" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"
  echo "Deleted Timestream table: $TIMESTREAM_DB/$TIMESTREAM_TABLE"
else
  echo "Timestream table not found, skipping."
fi

if aws timestream-write describe-database \
  --database-name "$TIMESTREAM_DB" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws timestream-write delete-database \
    --database-name "$TIMESTREAM_DB" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"
  echo "Deleted Timestream database: $TIMESTREAM_DB"
else
  echo "Timestream database not found, skipping."
fi

if aws dynamodb describe-table \
  --table-name "$ALERTS_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws dynamodb delete-table \
    --table-name "$ALERTS_TABLE" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"
  echo "Deleted DynamoDB alerts table: $ALERTS_TABLE"
else
  echo "DynamoDB alerts table not found, skipping."
fi

if aws dynamodb describe-table \
  --table-name "$DDB_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws dynamodb delete-table \
    --table-name "$DDB_TABLE" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"
  echo "Deleted DynamoDB table: $DDB_TABLE"
else
  echo "DynamoDB table not found, skipping."
fi

if aws s3api head-bucket --bucket "$RAW_BUCKET" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws s3 rm "s3://${RAW_BUCKET}" --recursive --profile "$AWS_PROFILE"
  aws s3api delete-bucket --bucket "$RAW_BUCKET" --profile "$AWS_PROFILE"
  echo "Deleted S3 bucket: $RAW_BUCKET"
else
  echo "S3 bucket not found, skipping."
fi

echo "Destroy complete."
