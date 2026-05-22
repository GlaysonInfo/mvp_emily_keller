# AWS CLI - Sprint 3

Scripts e notas para criar os recursos mínimos da ingestão HTTPS do MVP.

Fluxo-alvo:

```text
Bridge HTTPS -> API Gateway -> Lambda -> S3 + DynamoDB + Timestream + EventBridge
```

Variáveis sugeridas:

```bash
export AWS_REGION=us-east-1
export RAW_BUCKET=mvp-condition-monitoring-raw
export TIMESTREAM_DB=condition_monitoring_lab
export TIMESTREAM_TABLE=telemetry
export DYNAMODB_TABLE=mvp_asset_state
export EVENT_BUS=default
```

Ordem de execução planejada:

1. `01-create-s3.sh`
2. `02-create-dynamodb.sh`
3. `03-create-timestream.sh`
4. `04-package-lambda.sh`
5. Ler `05-api-gateway-notes.md`

