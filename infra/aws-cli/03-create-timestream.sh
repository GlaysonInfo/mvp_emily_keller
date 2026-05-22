#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${TIMESTREAM_DB:=condition_monitoring_lab}"
: "${TIMESTREAM_TABLE:=telemetry}"

aws timestream-write create-database \
  --region "$AWS_REGION" \
  --database-name "$TIMESTREAM_DB"

aws timestream-write create-table \
  --region "$AWS_REGION" \
  --database-name "$TIMESTREAM_DB" \
  --table-name "$TIMESTREAM_TABLE" \
  --retention-properties '{
    "MemoryStoreRetentionPeriodInHours": 24,
    "MagneticStoreRetentionPeriodInDays": 30
  }'

echo "Timestream table ready: $TIMESTREAM_DB.$TIMESTREAM_TABLE"

