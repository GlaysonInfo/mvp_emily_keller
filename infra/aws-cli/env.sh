#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${AWS_PROFILE:=default}"
: "${PROJECT:=condition-monitoring-lab}"
: "${STAGE:=dev}"

export AWS_REGION
export AWS_PROFILE
export PROJECT
export STAGE

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)}"
export AWS_ACCOUNT_ID

: "${RAW_BUCKET:=${PROJECT}-raw-${STAGE}-${AWS_ACCOUNT_ID}}"
: "${DDB_TABLE:=mvp_asset_state_${STAGE}}"
: "${DYNAMODB_TABLE:=${DDB_TABLE}}"
: "${TIMESTREAM_DB:=condition_monitoring_lab_${STAGE}}"
: "${TIMESTREAM_TABLE:=telemetry}"
: "${LAMBDA_NAME:=mvp-ingest-telemetry-${STAGE}}"
: "${LAMBDA_ROLE_NAME:=mvp-ingest-telemetry-role-${STAGE}}"
: "${EVENT_BUS:=default}"

export RAW_BUCKET
export DDB_TABLE
export DYNAMODB_TABLE
export TIMESTREAM_DB
export TIMESTREAM_TABLE
export LAMBDA_NAME
export LAMBDA_ROLE_NAME
export EVENT_BUS
