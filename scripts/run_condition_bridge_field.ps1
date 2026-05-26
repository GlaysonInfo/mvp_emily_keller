$env:AWS_DEFAULT_REGION = "us-east-1"

if (-not $env:CONDITION_FIELD_CONFIG) {
  $env:CONDITION_FIELD_CONFIG = "config/field_condition_config.json"
}

if (-not $env:CONDITION_INGEST_ENDPOINT) {
  $env:CONDITION_INGEST_ENDPOINT = "https://sentinelaindustrial.com.br/condition/ingest"
}

python -m src.edge.condition_bridge_field.bridge_runner
