#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

if aws s3api head-bucket --bucket "$RAW_BUCKET" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "S3 bucket already exists: $RAW_BUCKET"
else
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "$RAW_BUCKET" \
      --region "$AWS_REGION" \
      --profile "$AWS_PROFILE"
  else
    aws s3api create-bucket \
      --bucket "$RAW_BUCKET" \
      --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION" \
      --profile "$AWS_PROFILE"
  fi

  echo "S3 bucket created: $RAW_BUCKET"
fi

aws s3api put-bucket-encryption \
  --bucket "$RAW_BUCKET" \
  --profile "$AWS_PROFILE" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'

echo "S3 encryption enabled: $RAW_BUCKET"
