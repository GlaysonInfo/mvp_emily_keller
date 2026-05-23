#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

cat > build/aws/alert-lambda-trust-policy.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

if aws iam get-role --role-name "$ALERT_LAMBDA_ROLE_NAME" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "Alert IAM role already exists: $ALERT_LAMBDA_ROLE_NAME"
else
  aws iam create-role \
    --role-name "$ALERT_LAMBDA_ROLE_NAME" \
    --assume-role-policy-document file://build/aws/alert-lambda-trust-policy.json \
    --profile "$AWS_PROFILE" >/dev/null

  echo "Alert IAM role created: $ALERT_LAMBDA_ROLE_NAME"
fi

aws iam attach-role-policy \
  --role-name "$ALERT_LAMBDA_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --profile "$AWS_PROFILE"

cat > build/aws/alert-lambda-inline-policy.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${DDB_TABLE}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${ALERTS_TABLE}"
    }
  ]
}
JSON

aws iam put-role-policy \
  --role-name "$ALERT_LAMBDA_ROLE_NAME" \
  --policy-name "${ALERT_LAMBDA_ROLE_NAME}-inline" \
  --policy-document file://build/aws/alert-lambda-inline-policy.json \
  --profile "$AWS_PROFILE"

echo "Alert IAM role policy ready: $ALERT_LAMBDA_ROLE_NAME"
