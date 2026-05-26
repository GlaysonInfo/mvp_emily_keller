
$env:AWS_DEFAULT_REGION="us-east-1"

if (-not $env:GREASE_FIELD_CONFIG) {
  $env:GREASE_FIELD_CONFIG="config/field_lubrication_config.json"
}

if (-not $env:GREASE_INGEST_ENDPOINT) {
  $env:GREASE_INGEST_ENDPOINT="https://sentinelaindustrial.com.br/grease/ingest"
}

python -m src.edge.grease_bridge_field.bridge_runner
