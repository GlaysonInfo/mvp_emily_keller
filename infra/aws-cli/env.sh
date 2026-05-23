#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${AWS_PROFILE:=default}"
: "${PROJECT:=condition-monitoring-lab}"
: "${STAGE:=dev}"

if ! command -v aws >/dev/null 2>&1; then
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      for aws_cli_dir in \
        "/c/Program Files/Amazon/AWSCLIV2" \
        "/c/Program Files (x86)/Amazon/AWSCLIV2"
      do
        if [[ -x "${aws_cli_dir}/aws.exe" ]]; then
          export PATH="${aws_cli_dir}:${PATH}"
          break
        fi
      done
      ;;
  esac
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI nao encontrado no PATH do Bash." >&2
  echo "No Windows/Git Bash, confirme se existe: C:\\Program Files\\Amazon\\AWSCLIV2\\aws.exe" >&2
  exit 127
fi

export AWS_REGION
export AWS_PROFILE
export PROJECT
export STAGE

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" --query Account --output text)}"
export AWS_ACCOUNT_ID

: "${RAW_BUCKET:=${PROJECT}-raw-${STAGE}-${AWS_ACCOUNT_ID}}"
: "${DDB_TABLE:=mvp_asset_state_${STAGE}}"
: "${DYNAMODB_TABLE:=${DDB_TABLE}}"
: "${ENABLE_TIMESTREAM:=${TIMESTREAM_ENABLED:-false}}"
: "${TIMESTREAM_ENABLED:=${ENABLE_TIMESTREAM}}"
: "${TIMESTREAM_DB:=condition_monitoring_lab_${STAGE}}"
: "${TIMESTREAM_TABLE:=telemetry}"
: "${LAMBDA_NAME:=mvp-ingest-telemetry-${STAGE}}"
: "${LAMBDA_ROLE_NAME:=mvp-ingest-telemetry-role-${STAGE}}"
: "${EVENT_BUS:=default}"

export RAW_BUCKET
export DDB_TABLE
export DYNAMODB_TABLE
export ENABLE_TIMESTREAM
export TIMESTREAM_ENABLED
export TIMESTREAM_DB
export TIMESTREAM_TABLE
export LAMBDA_NAME
export LAMBDA_ROLE_NAME
export EVENT_BUS
