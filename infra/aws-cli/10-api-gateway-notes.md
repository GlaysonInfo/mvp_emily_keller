# API Gateway HTTPS Ingest

Sprint 3B deve expor uma rota HTTPS simples:

```text
POST /telemetry
```

Integracao:

- API type: HTTP API
- Lambda: `src/aws_lambdas/ingest_lambda.py`
- Handler: `aws_lambdas.ingest_lambda.lambda_handler`
- Entrada: payload canonico produzido pela bridge
- Saida esperada: HTTP `202` com `event_id`, `raw_s3_key` e `metrics_received`

Variaveis de ambiente da Lambda:

```text
RAW_BUCKET=mvp-condition-monitoring-raw
TIMESTREAM_DB=condition_monitoring_lab
TIMESTREAM_TABLE=telemetry
DYNAMODB_TABLE=mvp_asset_state
EVENT_BUS=default
```

Quando a rota estiver publicada, configurar na bridge:

```text
BRIDGE_PUBLISH_MODE=https
HTTPS_INGEST_URL=https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/telemetry
```

Validacao:

```bash
infra/aws-cli/09-test-http-api.sh
```

