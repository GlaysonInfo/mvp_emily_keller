#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

if aws timestream-write describe-database \
  --database-name "$TIMESTREAM_DB" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "Timestream database already exists: $TIMESTREAM_DB"
else
  aws timestream-write create-database \
    --database-name "$TIMESTREAM_DB" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Timestream database created: $TIMESTREAM_DB"
fi

if aws timestream-write describe-table \
  --database-name "$TIMESTREAM_DB" \
  --table-name "$TIMESTREAM_TABLE" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "Timestream table already exists: $TIMESTREAM_DB/$TIMESTREAM_TABLE"
else
  aws timestream-write create-table \
    --database-name "$TIMESTREAM_DB" \
    --table-name "$TIMESTREAM_TABLE" \
    --retention-properties MemoryStoreRetentionPeriodInHours=24,MagneticStoreRetentionPeriodInDays=7 \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

  echo "Timestream table created: $TIMESTREAM_DB/$TIMESTREAM_TABLE"
fi

