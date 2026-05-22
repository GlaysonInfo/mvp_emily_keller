#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${RAW_BUCKET:=mvp-condition-monitoring-raw}"

aws s3api create-bucket \
  --bucket "$RAW_BUCKET" \
  --region "$AWS_REGION"

aws s3api put-bucket-encryption \
  --bucket "$RAW_BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'

echo "S3 bucket ready: $RAW_BUCKET"

