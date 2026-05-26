# Checklist - teste com Gateway IO-Link

Use este checklist antes de apontar o gateway real para o endpoint do piloto.

## Infraestrutura

- [ ] EC2 acessivel.
- [ ] Servico `grease-ingest` ativo.
- [ ] `curl http://127.0.0.1:8000/grease/health` responde na EC2.
- [ ] `https://sentinelaindustrial.com.br/grease/health` responde fora da EC2.
- [ ] Porta `8000` nao esta liberada publicamente.
- [ ] Nginx publica `/grease/` via HTTPS.
- [ ] Regiao AWS configurada como `us-east-1`.
- [ ] Tabelas DynamoDB existem: `grease_lubrication_state`, `grease_lubrication_cycles`, `condition_alerts`.
- [ ] IAM Role da EC2 tem permissao para `GetItem`, `PutItem`, `UpdateItem`, `Query`, `Scan` e `DescribeTable` nessas tabelas.
- [ ] `GREASE_INGEST_TOKEN` definido em `/opt/automacaoapi/.env`.

## Gateway

- [ ] Gateway envia `POST https://sentinelaindustrial.com.br/grease/ingest`.
- [ ] Header `Content-Type: application/json`.
- [ ] Header `X-API-Key: <token_do_piloto>` ou `Authorization: Bearer <token_do_piloto>`.
- [ ] Timestamp em UTC.
- [ ] `tenant_id=cliente_demo`.
- [ ] `plant_id=lab_virtual`.
- [ ] `asset_id=sistema_lubrificacao_01`.
- [ ] `source_id=grease_gateway_01`.

## Sensores e mecanica

- [ ] Sensores configurados para faixa 0-250 bar.
- [ ] Manometros fisicos mantidos para comparacao.
- [ ] Conexoes em T/adaptadores conferidos para pressao real da linha.
- [ ] Cabos protegidos e identificados por saida.
- [ ] Cada sensor corresponde a uma saida de graxa clara: 01, 02, 03 e 04.

## Testes funcionais

- [ ] Enviar ciclo normal.
- [ ] Enviar ciclo com baixa pressao.
- [ ] Enviar ciclo com alta pressao.
- [ ] Enviar ciclo com alivio lento.
- [ ] Enviar ciclo sem pulso, se o gateway conseguir simular.
- [ ] Confirmar registro em `grease_lubrication_cycles`.
- [ ] Confirmar estado atual em `grease_lubrication_state`.
- [ ] Confirmar alertas em `condition_alerts`.
- [ ] Confirmar tela Sistema de Lubrificacao no dashboard.
- [ ] Confirmar recomendacao da IA.
