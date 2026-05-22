#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

API_URL="${HTTPS_INGEST_URL:-}"

if [ -z "$API_URL" ] && [ -f build/aws/http-api-url.txt ]; then
  API_URL="$(cat build/aws/http-api-url.txt)"
fi

if [ -z "$API_URL" ]; then
  echo "Set HTTPS_INGEST_URL or run infra/aws-cli/08-create-http-api.sh first."
  exit 1
fi

curl \
  --fail-with-body \
  --request POST \
  --header "content-type: application/json" \
  --data @infra/aws-cli/sample-payload.json \
  "$API_URL"

echo

