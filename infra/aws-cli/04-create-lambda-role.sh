#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

cat > build/aws/lambda-trust-policy.json <<'JSON'
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

if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "IAM role already exists: $LAMBDA_ROLE_NAME"
else
  aws iam create-role \
    --role-name "$LAMBDA_ROLE_NAME" \
    --assume-role-policy-document file://build/aws/lambda-trust-policy.json \
    --profile "$AWS_PROFILE" >/dev/null

  echo "IAM role created: $LAMBDA_ROLE_NAME"
fi

aws iam attach-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --profile "$AWS_PROFILE"

cat > build/aws/lambda-inline-policy.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::${RAW_BUCKET}/raw/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${DDB_TABLE}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:WriteRecords"
      ],
      "Resource": "arn:aws:timestream:${AWS_REGION}:${AWS_ACCOUNT_ID}:database/${TIMESTREAM_DB}/table/${TIMESTREAM_TABLE}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:PutEvents"
      ],
      "Resource": "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:event-bus/${EVENT_BUS}"
    }
  ]
}
JSON

aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name "${LAMBDA_ROLE_NAME}-inline" \
  --policy-document file://build/aws/lambda-inline-policy.json \
  --profile "$AWS_PROFILE"

echo "IAM role policy ready: $LAMBDA_ROLE_NAME"

