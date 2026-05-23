# AWS CLI - Sprint 3B

Scripts para provisionar o ambiente AWS dev da ingestao HTTPS do MVP.

Fluxo-alvo:

```text
Bridge HTTPS -> API Gateway HTTP API -> Lambda -> S3 + DynamoDB + EventBridge
EventBridge TelemetryNormalized -> Alert Processor Lambda -> DynamoDB alerts
```

Timestream for LiveAnalytics e opcional neste MVP. Em contas AWS sem acesso ao servico,
use `ENABLE_TIMESTREAM=false` e siga a validacao com S3 + DynamoDB.

## Pre-requisitos

- AWS CLI autenticado.
- Perfil local configurado em `AWS_PROFILE`.
- Permissoes para criar S3, DynamoDB, IAM, Lambda, EventBridge e API Gateway.
- Permissoes de Timestream apenas se `ENABLE_TIMESTREAM=true`.
- Bash com `zip` e `curl` disponiveis.

## Variaveis

Edite ou sobrescreva variaveis em `env.sh`:

```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="default"
export PROJECT="condition-monitoring-lab"
export STAGE="dev"
```

`RAW_BUCKET` inclui o Account ID para manter o nome globalmente unico.

`ENABLE_TIMESTREAM=false` e o padrao para contas novas, pois o acesso novo ao
Timestream for LiveAnalytics pode estar indisponivel.

## Ordem de execucao

0. `./infra/aws-cli/00-preflight.sh`
1. `./infra/aws-cli/01-create-s3.sh`
2. `./infra/aws-cli/02-create-dynamodb.sh`
3. `./infra/aws-cli/03-create-timestream.sh` (pula quando `ENABLE_TIMESTREAM=false`)
4. `./infra/aws-cli/04-create-lambda-role.sh`
5. `./infra/aws-cli/05-package-lambda.sh`
6. `./infra/aws-cli/06-deploy-lambda.sh`
7. `./infra/aws-cli/07-invoke-lambda-direct.sh`
8. `./infra/aws-cli/08-create-http-api.sh`
9. `./infra/aws-cli/09-test-http-api.sh`
10. `./infra/aws-cli/10-create-alerts-dynamodb.sh`
11. `./infra/aws-cli/11-create-alert-lambda-role.sh`
12. `./infra/aws-cli/05-package-lambda.sh`
13. `./infra/aws-cli/12-deploy-alert-processor-lambda.sh`
14. `./infra/aws-cli/14-invoke-alert-processor-direct.sh`
15. `./infra/aws-cli/13-create-alert-eventbridge-rule.sh`
16. `./infra/aws-cli/15-verify-alerts.sh`
17. Ler `10-api-gateway-notes.md`

## Teste direto da Lambda

Antes da API Gateway, valide:

```bash
./infra/aws-cli/07-invoke-lambda-direct.sh
```

Resultado esperado: `statusCode` 202 no arquivo `build/aws/lambda-response.json`.

Depois confira:

- Objeto raw no S3.
- Item `LATEST` no DynamoDB.
- Registros no Timestream, se `ENABLE_TIMESTREAM=true`.
- Evento `TelemetryNormalized` no EventBridge/CloudWatch conforme configuracao.

## Limpeza dev

Para remover os recursos dev criados por estes scripts:

```bash
./infra/aws-cli/99-destroy-dev.sh
```

O script exige confirmacao digitando `DESTROY`.

Ordem de remocao:

1. API Gateway HTTP API.
2. Lambda.
3. IAM inline/managed policies e role.
4. Timestream table/database.
5. DynamoDB table.
6. S3 objects.
7. S3 bucket.
