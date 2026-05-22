# Plano de Implementação do MVP

## 1. Estratégia

Implementar o MVP em ciclos curtos, começando localmente e evoluindo para integração AWS.

Ordem recomendada:

1. Simulador local.
2. Servidor OPC UA.
3. UaExpert.
4. MQTT local.
5. Bridge Edge.
6. AWS ingestão.
7. Armazenamento.
8. Motor de regras.
9. Dashboard.
10. Empacotamento Docker.

## 2. Sprint 1 — Simulador e OPC UA

### Objetivos

- Criar motor virtual.
- Criar cenários de falha.
- Expor tags via OPC UA.
- Validar no UaExpert.

### Entregáveis

- `src/simulator/motor_model.py`
- `src/simulator/opcua_server.py`
- `src/simulator/config.yaml`
- Documentação de execução local.

### Critério de pronto

- UaExpert visualiza todas as tags.
- Cenários alternam automaticamente.

## 3. Sprint 2 — MQTT local e Bridge Edge

### Objetivos

- Subir Mosquitto local via Docker.
- Publicar payload canônico.
- Criar bridge OPC UA -> MQTT/HTTPS.

### Entregáveis

- `infra/docker/mosquitto.conf`
- `src/edge_bridge/opcua_reader.py`
- `src/edge_bridge/publisher_mqtt.py`
- `src/edge_bridge/publisher_https.py`
- `src/edge_bridge/main.py`

### Critério de pronto

- Bridge lê tags OPC UA.
- Bridge publica payload em MQTT local.
- Payload segue schema canônico.

## 4. Sprint 3 — AWS ingestão e armazenamento

### Objetivos

- Criar recursos AWS mínimos.
- Receber MQTT no AWS IoT Core.
- Receber HTTPS no API Gateway.
- Normalizar com Lambda.
- Armazenar em S3, Timestream e DynamoDB.

### Entregáveis

- `src/aws_lambdas/ingest_lambda.py`
- Scripts AWS CLI para criar recursos.
- Documentação de variáveis de ambiente.

### Critério de pronto

- Evento aparece no S3.
- Medidas aparecem no Timestream.
- Latest state aparece no DynamoDB.

## 5. Sprint 4 — Motor de regras

### Objetivos

- Implementar regras de falha.
- Criar alertas explicáveis.
- Persistir alertas no DynamoDB.

### Entregáveis

- `src/rules_engine/diagnostics.py`
- `src/rules_engine/rules.py`
- `src/rules_engine/alert_repository.py`
- Testes unitários.

### Critério de pronto

- Falha de lubrificação gera warning.
- Desbalanceamento gera critical.
- Falha em rolamento gera critical.

## 6. Sprint 5 — Dashboard

### Objetivos

- Exibir estado atual.
- Exibir tendências.
- Exibir alertas e evidências.

### Entregáveis

- `src/dashboard/app.py`
- Gráficos de telemetria.
- Cards de health score e severidade.
- Lista de alertas.

### Critério de pronto

- Dashboard suporta roteiro completo da demo.

## 7. Sprint 6 — Empacotamento e roteiro final

### Objetivos

- Criar Docker Compose local.
- Criar roteiro de demo.
- Criar troubleshooting.

### Entregáveis

- `docker-compose.yml`
- `docs/07-criterios-aceite-demo.md` atualizado.
- `docs/troubleshooting.md` futuro.

## 8. Ordem sugerida de criação no VS Code

```text
1. Criar repositório.
2. Criar ambiente virtual Python.
3. Criar pastas docs, src, infra, tests.
4. Criar simulador puro sem OPC UA.
5. Adicionar servidor OPC UA.
6. Validar UaExpert.
7. Adicionar MQTT local.
8. Criar bridge separada.
9. Criar Lambda localmente com testes.
10. Criar recursos AWS mínimos.
11. Integrar bridge com AWS.
12. Criar motor de regras.
13. Criar dashboard.
14. Ensaiar demo.
```

## 9. Métricas de progresso

| Métrica | Meta MVP |
|---|---:|
| Tags OPC UA atualizadas | 11 tags |
| Frequência de atualização | 1 segundo configurável |
| Cenários simulados | 4 |
| Protocolos demonstrados | OPC UA + MQTT + HTTPS |
| Bancos AWS usados | S3 + Timestream + DynamoDB |
| Regras de falha | 3 regras principais |
| Telas dashboard | 3 a 5 telas/seções |

## 10. Riscos de implementação

| Risco | Impacto | Mitigação |
|---|---|---|
| UaExpert não conecta | Alto | Testar endpoint local antes da demo |
| Porta 4840 ocupada | Médio | Permitir configuração por variável de ambiente |
| AWS IoT certificados complexos | Médio | Ter fallback HTTPS via API Gateway |
| Timestream com erro de schema | Médio | Criar função única de conversão de métricas |
| Custo AWS inesperado | Médio | Usar baixo volume e tags de custo |
| Dashboard lento | Baixo | Consultar janela curta no MVP |

