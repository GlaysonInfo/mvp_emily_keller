# Condition Monitoring Lab MVP

MVP demonstrativo de monitoramento de condição para ativos industriais, usando uma bancada virtual controlada.

O projeto simula um motor industrial monitorado por sensores virtuais, expõe tags via OPC UA, publica telemetria por MQTT/HTTPS, envia dados para AWS, armazena histórico, calcula tendências, detecta falhas iniciais por regras técnicas e apresenta alertas explicáveis em dashboard.

## Arquitetura

![Arquitetura da bancada virtual do MVP](docs/assets/arquitetura-bancada-mvp.png)

## Objetivo do MVP

Demonstrar para clientes o fluxo completo:

1. Motor virtual funcionando normalmente.
2. UaExpert conectado ao servidor OPC UA local.
3. Tags OPC UA mudando em tempo real.
4. Bridge Edge lendo dados do servidor OPC UA.
5. Bridge publicando dados via MQTT ou HTTPS.
6. AWS recebendo, normalizando e armazenando dados.
7. Dashboard mostrando tendências.
8. Motor de regra detectando falha inicial.
9. Alerta com causa provável, evidências e ação recomendada.

## Fora do escopo

Não faz parte deste MVP:

- Desenvolver máquinas.
- Desenvolver sensores físicos.
- Desenvolver firmware.
- Desenvolver PLC.
- Controlar atuadores industriais.
- Fazer automação de processo.
- Interferir em malhas de controle.

O MVP começa na camada de dados: recebimento, leitura, padronização, tratamento, logging, armazenamento histórico, análise contínua e entrega de diagnóstico.

## Cenários simulados

| Cenário | Comportamento esperado |
|---|---|
| `normal` | RPM estável, temperatura controlada, vibração baixa |
| `lubrication_degradation` | Ultrassom sobe primeiro, depois temperatura e vibração |
| `imbalance` | Vibração RMS cresce de forma contínua |
| `bearing_fault` | Kurtosis e crest factor sobem antes do RMS ficar crítico |

## Stack inicial

### Local / laboratório

- Python 3.11+
- Docker Desktop
- Mosquitto MQTT Broker
- Biblioteca `opcua` para servidor e cliente OPC UA em Python
- `paho-mqtt` para publicação MQTT local
- `PyYAML` para configuração do simulador
- UaExpert como cliente OPC UA de demonstração
- Streamlit ou dashboard web simples para visualização

Nota técnica: a Sprint 2 usa `opcua` como dependência OPC UA. A biblioteca `asyncua` não faz parte do runtime atual.

### AWS

- AWS IoT Core para entrada MQTT
- API Gateway para entrada HTTPS
- Lambda para normalização
- S3 para histórico bruto
- Amazon Timestream para séries temporais, se a conta AWS tiver acesso ao servico
- DynamoDB para estado atual e alertas
- EventBridge para eventos
- SNS ou SES para notificação futura
- CloudWatch para logs

## Decisão de ambiente

| Opção | Uso no MVP | Recomendação |
|---|---:|---|
| Notebook com Docker | Sim | Melhor para primeira demo presencial |
| EC2 na AWS | Sim | Bom para demo remota |
| WAGO Edge Controller | Não no início | Avaliar em fase 2, apenas como host edge industrial |
| PLC | Não | Fora do escopo |

## Como rodar a demonstração local

### Preparar ambiente Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

### Rodar o simulador OPC UA do Motor_001

```powershell
python -m simulator.opcua_server
```

O servidor expõe as tags em:

```text
opc.tcp://localhost:4840/lab/opcua/
```

No UaExpert, navegue até:

```text
Objects > Lab > Motor_001
```

Tags expostas na primeira versão:

- `rpm`
- `vibration_rms_mm_s`
- `vibration_peak_g`
- `temperature_c`
- `ultrasound_db`
- `horimeter_h`
- `kurtosis`
- `crest_factor`
- `health_score`
- `severity`
- `failure_mode`

### Rodar testes do simulador

```powershell
python -m unittest discover -s tests
```

### Subir Mosquitto local

```powershell
docker info
docker compose up -d mosquitto
docker compose ps
```

O broker usa a configuração de laboratório em `infra/docker/mosquitto.conf`:

```text
listener 1883 0.0.0.0
allow_anonymous true
persistence false
log_type all
```

### Rodar a bridge OPC UA para MQTT

Com o Mosquitto e o simulador OPC UA rodando:

```powershell
python -m edge_bridge.main
```

Por padrão, a bridge lê:

```text
opc.tcp://localhost:4840/lab/opcua/
```

E publica em:

```text
lab/cliente_demo/lab_virtual/motor_001/telemetry
```

Para inspecionar as mensagens:

```powershell
docker exec -it lab-mosquitto mosquitto_sub -h localhost -t "lab/+/+/+/telemetry" -v
```

Variáveis úteis:

| Variável | Padrão |
|---|---|
| `OPCUA_ENDPOINT` | `opc.tcp://localhost:4840/lab/opcua/` |
| `OPCUA_NAMESPACE_INDEX` | `2` |
| `MQTT_HOST` | `localhost` |
| `MQTT_PORT` | `1883` |
| `MQTT_TOPIC` | `lab/cliente_demo/lab_virtual/motor_001/telemetry` |
| `BRIDGE_INTERVAL_SECONDS` | `1.0` |
| `BRIDGE_PUBLISH_MODE` | `mqtt` |
| `HTTPS_INGEST_URL` | vazio |

### Checklist manual da Sprint 2

Com o Docker Desktop aberto, valide o ambiente:

```powershell
docker info
docker compose up -d mosquitto
docker compose ps
```

Depois execute em três terminais:

```powershell
python -m simulator.opcua_server
```

```powershell
python -m edge_bridge.main
```

```powershell
docker exec -it lab-mosquitto mosquitto_sub -h localhost -t "lab/+/+/+/telemetry" -v
```

Critérios de aceite:

- `docker ps` mostra o container `lab-mosquitto` em execução.
- O UaExpert conecta em `opc.tcp://localhost:4840/lab/opcua/`.
- O caminho `Objects > Lab > Motor_001` mostra 11 tags.
- A bridge lê as 11 tags sem encerrar se OPC UA ou MQTT ficarem temporariamente indisponíveis.
- O tópico MQTT recebe payload canônico a cada intervalo configurado.
- `failure_mode_simulated` fica no contexto do payload.
- `metrics` contém apenas métricas numéricas.
- Pelo menos 9 métricas numéricas aparecem no payload.

### Roteiro completo da demo

1. Subir broker MQTT local com Mosquitto.
2. Rodar o simulador do motor e servidor OPC UA.
3. Abrir o UaExpert.
4. Conectar ao endpoint OPC UA:

```text
opc.tcp://localhost:4840/lab/opcua/
```

5. Navegar até:

```text
Objects > Lab > Motor_001
```

6. Arrastar variáveis para a área de monitoramento.
7. Rodar a bridge OPC UA -> MQTT/HTTPS.
8. Validar chegada dos dados na AWS.
9. Abrir o dashboard.
10. Aguardar o ciclo de falha simulada e observar o alerta.

## Sprint 3 - Ingestão AWS via HTTPS

Divisão de trabalho:

- Sprint 3A: fechada; Lambda full-flow local com mocks/fakes.
- Sprint 3B: fechada; deploy AWS dev validado com S3, DynamoDB, Lambda e API Gateway HTTP API. Timestream fica opcional porque contas novas podem nao ter acesso ao Timestream for LiveAnalytics.

Fluxo-alvo:

```text
Bridge HTTPS
  -> API Gateway
  -> Lambda normalizadora
  -> S3 raw
  -> DynamoDB latest state
  -> Timestream telemetry opcional
  -> EventBridge TelemetryNormalized
```

Variáveis de ambiente da Lambda:

| Variável | Valor inicial |
|---|---|
| `RAW_BUCKET` | `${PROJECT}-raw-${STAGE}-${AWS_ACCOUNT_ID}` |
| `ENABLE_TIMESTREAM` | `false` |
| `TIMESTREAM_ENABLED` | `false` |
| `TIMESTREAM_DB` | `condition_monitoring_lab_dev` |
| `TIMESTREAM_TABLE` | `telemetry` |
| `DYNAMODB_TABLE` | `mvp_asset_state_dev` |
| `EVENT_BUS` | `default` |

Componentes iniciais:

- Lambda normalizadora: `src/aws_lambdas/ingest_lambda.py`
- Testes da Lambda: `tests/test_ingest_lambda.py`
- Scripts e notas AWS CLI: `infra/aws-cli/`

Definition of Done da Sprint 3:

- Lambda valida payload válido.
- Lambda rejeita payload inválido.
- Payload bruto é salvo no S3.
- Métricas são gravadas no Timestream quando `ENABLE_TIMESTREAM=true`.
- Último estado é atualizado no DynamoDB.
- API Gateway recebe `POST /telemetry`.
- Bridge envia HTTPS usando `HTTPS_INGEST_URL`.
- CloudWatch mostra logs sem erro.

Sprint 3A está pronta quando:

```powershell
python -m unittest discover -s tests -v
python -m compileall src tests
```

Resultado esperado: todos OK, com apenas o teste opcional do Mosquitto pulado quando Docker Desktop não estiver ativo.

Sprint 3B segue esta ordem:

1. Criar variáveis padrão em `infra/aws-cli/env.sh`.
2. Criar bucket S3 raw.
3. Criar tabela DynamoDB `mvp_asset_state_dev`.
4. Criar Timestream database/table somente se `ENABLE_TIMESTREAM=true`.
5. Criar IAM role e policy da Lambda.
6. Empacotar Lambda em `.zip`.
7. Criar ou atualizar Lambda real.
8. Testar Lambda por invoke direto.
9. Criar API Gateway HTTP API `POST /telemetry`.
10. Testar `curl -> API Gateway -> Lambda -> S3/DynamoDB` e Timestream, se habilitado.
11. Configurar `HTTPS_INGEST_URL` na bridge.

Status Sprint 3B:

- Validado: `curl -> API Gateway /dev/telemetry -> Lambda real -> S3 raw + DynamoDB latest state`.
- Validado: `OPC UA Server -> Bridge HTTPS -> API Gateway /dev/telemetry -> Lambda real -> S3 raw + DynamoDB latest state`.
- DynamoDB: tabela `mvp_asset_state_dev`.
- S3 raw: objetos em `raw/tenant=cliente_demo/plant=lab_virtual/asset=motor_001/`.
- Evidencia S3: novos arquivos raw da bridge em `date=2026-05-23`.
- Evidencia DynamoDB: `source=opcua_edge_bridge`, `failure_mode_simulated=imbalance`, `updated_at=2026-05-23T03:02:29.019870Z`, `raw_s3_key=raw/tenant=cliente_demo/plant=lab_virtual/asset=motor_001/date=2026-05-23/806c6859-76b4-4dd3-bb5a-a87ec6dc395c.json`.
- Evidencia DynamoDB: metricas numericas presentes no item `LATEST`.
- Timestream: opcional/pendente por limitacao de acesso da conta AWS ao Timestream for LiveAnalytics.
- CloudWatch: validado sem `ERROR` ou `Traceback`.
- Observacao operacional: ao finalizar testes AWS, parar a bridge com `Ctrl+C` para evitar chamadas continuas ao API Gateway/Lambda.

Scripts da Sprint 3B:

```powershell
bash infra/aws-cli/00-preflight.sh
bash infra/aws-cli/01-create-s3.sh
bash infra/aws-cli/02-create-dynamodb.sh
bash infra/aws-cli/03-create-timestream.sh  # pula quando ENABLE_TIMESTREAM=false
bash infra/aws-cli/04-create-lambda-role.sh
bash infra/aws-cli/05-package-lambda.sh
bash infra/aws-cli/06-deploy-lambda.sh
bash infra/aws-cli/07-invoke-lambda-direct.sh
bash infra/aws-cli/08-create-http-api.sh
bash infra/aws-cli/09-test-http-api.sh
```

Limpeza dev:

```powershell
bash infra/aws-cli/99-destroy-dev.sh
```

O script de limpeza exige confirmação explícita digitando `DESTROY`.

## Status do projeto

- Sprint 1: fechada.
- Sprint 2: code-ready; pendente apenas aceite operacional Mosquitto com Docker Desktop ativo.
- Sprint 3A: fechada; Lambda validada com fake clients.
- Sprint 3B: fechada; validada via HTTPS com S3 raw + DynamoDB latest state e CloudWatch sem erro.

PENDENTE OPERACIONAL:

Validar fluxo real OPC UA -> Bridge -> Mosquitto quando Docker Desktop estiver ativo.

## Sprint 4 - Motor de Regras e Alertas Explicaveis

Sprint 4A implementa primeiro o diagnostico local, sem tocar na AWS.

Fluxo-alvo:

```text
Payload canonico / DynamoDB latest state
  -> Motor de regras
  -> Diagnostico
  -> Alerta explicavel
  -> DynamoDB mvp_alerts_dev
  -> Dashboard futuro
```

Escopo Sprint 4A:

- Criar `rules_engine`.
- Criar contrato de alerta.
- Criar regras para `lubrication_degradation`, `imbalance` e `bearing_fault`.
- Criar testes unitarios fortes.
- Integrar com Lambda/DynamoDB somente depois.

Regras iniciais:

| Alerta | Condicao | Severidade |
|---|---|---|
| `lubrication_degradation` | `ultrasound_db > 38` e `temperature_c > 65` e `vibration_rms_mm_s < 4.0` | `warning` |
| `imbalance` | `vibration_rms_mm_s >= 4.0` e `ultrasound_db < 38` e `kurtosis < 4.5` | `critical` |
| `bearing_fault` | `kurtosis >= 5.0` e `crest_factor >= 4.5` | `critical` |

Contrato minimo de alerta:

```json
{
  "alert_type": "imbalance",
  "severity": "critical",
  "status": "open",
  "probable_cause": "Possivel desbalanceamento",
  "confidence": 0.82,
  "evidence": [
    "Vibracao RMS acima de 4.0 mm/s",
    "Ultrassom dentro da faixa esperada",
    "Kurtosis sem forte evidencia de impacto de rolamento"
  ],
  "recommended_action": "Verificar balanceamento, fixacao, acoplamento e base do motor"
}
```

Definition of Done Sprint 4A:

- Motor de regras recebe payload canonico.
- Cenario normal nao gera alerta.
- `lubrication_degradation` gera `warning`.
- `imbalance` gera `critical`.
- `bearing_fault` gera `critical`.
- Todo alerta tem causa provavel, severidade, evidencias e acao recomendada.
- Testes unitarios passam.

## Sprint 4B - Alert Processor Lambda

Decisao de arquitetura: o motor de alertas fica fora da Lambda de ingestao. A
`ingest_lambda` permanece responsavel por normalizar e persistir telemetria; a
`alert_processor_lambda` processa eventos `TelemetryNormalized` publicados no
EventBridge.

Fluxo-alvo:

```text
API Gateway
  -> ingest_lambda
  -> S3 raw
  -> DynamoDB mvp_asset_state_dev
  -> EventBridge TelemetryNormalized
  -> alert_processor_lambda
  -> DynamoDB mvp_alerts_dev
```

Modelo de alerta ativo:

- Tabela: `mvp_alerts_dev`.
- `pk`: `TENANT#{tenant_id}#ASSET#{asset_id}`.
- `sk`: `ALERT#ACTIVE#{alert_type}`.
- `alert_id`: `{tenant_id}#{asset_id}#{alert_type}#active`.

Esse modelo atualiza o alerta ativo por tipo, em vez de criar um alerta novo a
cada ciclo da bridge.

Sprint 4B local validada por fakes:

- Alert processor recebe evento EventBridge fake.
- Le latest state fake.
- Reconstrui payload canonico.
- Aplica `rules_engine`.
- Normal nao grava alerta.
- `imbalance` grava alerta `critical`.
- Alerta ativo preserva `first_detected_at`.

Sprint 4B AWS fechada:

- Tabela `mvp_alerts_dev` criada.
- Lambda `mvp-alert-processor-dev` criada e acionada pelo EventBridge.
- Regra `mvp-telemetry-normalized-alerts-dev` criada para eventos `TelemetryNormalized`.
- Fluxo validado: `OPC UA Server -> Bridge HTTPS -> API Gateway -> ingest_lambda -> DynamoDB latest state -> EventBridge -> alert_processor_lambda -> mvp_alerts_dev`.
- Alerta ativo gravado: `sk=ALERT#ACTIVE#lubrication_degradation`.
- `alert_id=cliente_demo#motor_001#lubrication_degradation#active`.
- `severity=warning`, `status=open`, `confidence=0.76`.
- `failure_mode_simulated=lubrication_degradation`.
- `first_detected_at=2026-05-23T03:55:17.808940Z`.
- CloudWatch da Lambda de alertas validado sem `ERROR` ou `Traceback`.

Integracao AWS executada:

1. Criar tabela `mvp_alerts_dev`.
2. Criar IAM role da `alert_processor_lambda`.
3. Empacotar Lambda incluindo `aws_lambdas` e `rules_engine`.
4. Criar Lambda alert processor.
5. Invocar alert processor diretamente com evento fake do EventBridge.
6. Criar regra EventBridge para `TelemetryNormalized`.
7. Permitir EventBridge invocar a Lambda.
8. Rodar bridge ate gerar `imbalance` ou `bearing_fault`.
9. Verificar item ativo em `mvp_alerts_dev`.

Scripts AWS Sprint 4B:

```powershell
bash infra/aws-cli/10-create-alerts-dynamodb.sh
bash infra/aws-cli/11-create-alert-lambda-role.sh
bash infra/aws-cli/05-package-lambda.sh
bash infra/aws-cli/12-deploy-alert-processor-lambda.sh
bash infra/aws-cli/14-invoke-alert-processor-direct.sh
bash infra/aws-cli/13-create-alert-eventbridge-rule.sh
bash infra/aws-cli/15-verify-alerts.sh
```

Handler da Lambda de alertas no pacote `.zip`:

```text
aws_lambdas.alert_processor_lambda.lambda_handler
```

Regra EventBridge:

```json
{
  "source": ["condition-monitoring.ingestion"],
  "detail-type": ["TelemetryNormalized"]
}
```

## Sprint 5 - Dashboard MVP

Objetivo: criar uma interface demonstrativa local lendo diretamente:

```text
DynamoDB mvp_asset_state_dev
        +
DynamoDB mvp_alerts_dev
        ->
Dashboard Streamlit local
```

Uso no MVP:

- Estado atual do `Motor_001`.
- Metricas atuais.
- Health score.
- Modo de falha simulado.
- Alertas ativos.
- Causa provavel, evidencias e acao recomendada.

Para demonstracao local, o dashboard le DynamoDB diretamente com `boto3`. Em
producao futura, o caminho recomendado sera `Dashboard Web -> API Backend ->
DynamoDB/S3/historico`.

Variaveis de ambiente:

```powershell
$env:AWS_PROFILE="Glayson"
$env:AWS_REGION="us-east-1"
$env:TENANT_ID="cliente_demo"
$env:PLANT_ID="lab_virtual"
$env:ASSET_ID="motor_001"
$env:DYNAMODB_TABLE="mvp_asset_state_dev"
$env:ALERTS_TABLE="mvp_alerts_dev"
$env:DASHBOARD_REFRESH_SECONDS="5"
```

Como rodar:

```powershell
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

### Cenários de demonstração

O dashboard inclui um `Modo Apresentação`, na barra lateral. Ele percorre os
pacotes simulados na ordem comercial da demo e carrega cada cenário diretamente
nas tabelas DynamoDB do MVP, sem esperar a falha evoluir em tempo real.

Pacotes disponíveis:

1. Operação Normal do Motor.
2. Degradação de Lubrificação.
3. Desbalanceamento ou Desalinhamento Mecânico.
4. Aquecimento Anormal.
5. Falha Inicial em Rolamento.
6. Risco Crítico de Parada.
7. Pós-Manutenção e Recuperação do Ativo.
8. Perda de Comunicação ou Sensor Offline.

O seletor grava o estado atual com `pk=TENANT#{tenant_id}#ASSET#{asset_id}` e
`sk=LATEST`, no mesmo formato usado pela Lambda de ingestão. Nos casos com
diagnóstico ativo, também grava um alerta em `ALERT#ACTIVE#{case_id}`. Ao trocar
de cenário, o app limpa apenas alertas marcados como demonstração
(`is_demo_case=true`), preservando alertas reais que estejam na tabela.

Controles do modo apresentação:

- `⬅ Cenário anterior`.
- `Aplicar cenário`.
- `Próximo cenário ➡`.

Também é possível carregar os cenários por linha de comando:

```powershell
$env:AWS_PROFILE="Glayson"
$env:AWS_REGION="us-east-1"
$env:TENANT_ID="cliente_demo"
$env:PLANT_ID="lab_virtual"
$env:ASSET_ID="motor_001"
$env:DYNAMODB_TABLE="mvp_asset_state_dev"
$env:ALERTS_TABLE="mvp_alerts_dev"

python seed_demo_cases.py --list
python seed_demo_cases.py --case lubrication_degradation
```

### Painel visual de variação

O dashboard também renderiza um painel de relógios industriais com Apache
ECharts, logo abaixo das métricas atuais. Os gauges mostram ponteiro, valor
central, animação e faixa visual de condição para:

- RPM.
- Vibração RMS.
- Temperatura.
- Ultrassom.
- Kurtosis.
- Crest Factor.
- Pico de vibração.
- Health Score.
- Severity Score.

Os limites atuais são limiares simulados para demonstração comercial. Em uma
evolução de produto, esses limites devem virar configuração por tipo de ativo,
criticidade, rotação nominal, histórico, norma adotada e baseline real do
cliente.

### Histórico operacional exportável

O dashboard grava um snapshot técnico por minuto em uma tabela DynamoDB separada
do estado atual. Isso preserva o `LATEST` leve para a tela principal e cria uma
trilha auditável para exportação.

Tabela sugerida:

```text
condition_history
```

Chaves:

| Campo | Tipo | Uso |
|---|---|---|
| `tenant_asset` | String | Partition key, no formato `tenant_id#asset_id` |
| `ts_utc_minute` | String | Sort key, minuto UTC no formato ISO |
| `ttl_epoch` | Number | TTL opcional para retenção automática |

Variáveis de ambiente:

```powershell
$env:CONDITION_HISTORY_TABLE="condition_history"
$env:HISTORY_RETENTION_DAYS="365"
```

Para criar a tabela de histórico no DynamoDB pelo PowerShell:

```powershell
$env:AWS_PROFILE="automacaoapi"
$env:AWS_REGION="us-east-1"
$env:CONDITION_HISTORY_TABLE="condition_history"
.\infra\aws-cli\16-create-condition-history-dynamodb.ps1
```

Na tela, o botão `Histórico` abre:

- Período: última 1h, 6h, 12h, 24h ou 7 dias.
- Formato: minuto a minuto, resumo 1h, resumo 6h, resumo 12h ou resumo 24h.
- Exportação em CSV.
- Exportação em TXT.

O resumo técnico trata cada variável conforme sua natureza:

- RPM: valor final e média.
- Vibração RMS, temperatura, ultrassom, kurtosis e crest factor: média e máximo.
- Pico de vibração: máximo.
- Health Score: final, média e mínimo.
- Severity Score: final, média e máximo.
- Horímetro: inicial, final e diferença.
- Alertas: minutos em alerta e minutos críticos.

### Sprint 1 - Parque Industrial Multiativos

O dashboard agora possui navegação entre:

- `Visão Geral da Planta`.
- `Detalhe do Ativo`.

A visão geral consulta a tabela de estado atual e monta um painel executivo com
KPIs da planta, filtros e lista clicável de ativos por prioridade. Ao clicar em
um ativo, o app muda para o detalhe e reaproveita os relógios, histórico e
diagnóstico já existentes.

Arquivos principais:

- `src/dashboard/demo_assets_catalog.json`
- `src/dashboard/demo_multiasset_states.json`
- `src/dashboard/multiasset_repository.py`
- `src/dashboard/plant_overview_ui.py`
- `seed_multi_assets.py`

Para listar os ativos simulados sem acessar a AWS:

```powershell
python seed_multi_assets.py --list
```

Para carregar os 12 ativos simulados na tabela de estado atual:

```powershell
$env:AWS_PROFILE="automacaoapi"
$env:AWS_REGION="us-east-1"
$env:AWS_DEFAULT_REGION="us-east-1"
$env:DYNAMODB_TABLE="mvp_asset_state_dev"

python seed_multi_assets.py
```

Também é aceito o alias do pacote:

```powershell
$env:DYNAMODB_STATE_TABLE="mvp_asset_state_dev"
```

Nesta Sprint, a consulta multiativos usa `scan` com filtro por `tenant_id`,
`plant_id` e `sk=LATEST`. Para produção, evoluir para um GSI:

```text
GSI: tenant_plant_index
Partition key: tenant_plant
Sort key: asset_id
```

### Relatórios MVP

A navegação lateral inclui a tela `Relatórios`, com exportação em CSV e TXT.
Esta primeira versão cobre os relatórios mais úteis para demonstração e gestão:

- Gerais:
  - Visão geral da planta.
  - Ranking de risco.
- Operacionais:
  - Relatório individual do ativo.
  - Tendência operacional.
- Eventos:
  - Alertas ativos.
  - Histórico de alertas.

Os relatórios gerais usam os estados atuais dos ativos. A tendência operacional
usa a tabela `condition_history`. Os relatórios de eventos usam a tabela
`mvp_alerts_dev`; nesta fase, o histórico de alertas reflete o que existir nessa
tabela.

Quando um ativo está em condição de risco, mas ainda não existe alerta formal
persistido para ele, o dashboard projeta um alerta operacional a partir do estado
atual. Isso mantém o detalhe do ativo e o relatório de alertas ativos coerentes
com o Health Score, Severity Score e status operacional exibidos.

### Configurações MVP

A navegação lateral inclui a tela `Configurações`. A primeira entrega usa
persistência local em `src/dashboard/config_store.json` e prepara:

- Cliente.
- Planta.
- Fontes de Dados.
- Ativos.
- Mapeamento de Sinais.
- Parâmetros e Alertas.

A arquitetura está documentada em `docs/11-configuracoes-fontes-dados.md`. A
decisão principal é separar o ativo monitorado da camada de aquisição: fontes de
dados/gateways/conectores entram em `data_sources`, e o vínculo
ativo-fonte-tag fica em `signal_map`. Credenciais não são armazenadas em texto
puro; o cadastro guarda apenas uma referência segura, como Secrets Manager ou
variável de ambiente.

#### Validações reais de Configurações

A aba `Fontes de Dados` possui validações funcionais:

- Bancada virtual: valida cadastro interno e contrato de métricas esperado.
- Bridge OPC UA / HTTPS: testa a URL da bridge, status HTTP, latência e prévia
  da resposta.
- CSV/manual: lê arquivo enviado, valida cabeçalho, colunas obrigatórias e
  mapeamento de tags contra colunas do CSV.
- Credencial: valida apenas a referência segura, sem ler nem exibir segredo.

Arquivo CSV de exemplo: `docs/configuration/examples/sample_monitoring_data.csv`.

### Teste Ponta a Ponta

A navegação lateral inclui a tela `Teste ponta a ponta`. Ela executa um teste
controlado da cadeia:

```text
Fonte de dados -> payload padronizado -> estado atual -> histórico -> alertas -> leitura de volta
```

Modos disponíveis:

- Bancada virtual / payload simulado.
- CSV/manual.
- HTTP/HTTPS da bridge.

Variáveis usadas:

```powershell
$env:DYNAMODB_STATE_TABLE="mvp_asset_state_dev"
$env:CONDITION_HISTORY_TABLE="condition_history"
$env:CONDITION_ALERTS_TABLE="condition_alerts"
```

O script `infra/aws-cli/17-create-e2e-dynamodb-tables.ps1` cria as tabelas
`condition_history` e `condition_alerts` quando elas ainda não existem. A tabela
de estado atual deve ser a mesma usada pelo dashboard.

Payload HTTP de exemplo:
`docs/configuration/examples/sample_e2e_payload.json`.

### Central de Alertas e Eventos

A navegação lateral também inclui a tela `Alertas e Eventos`. Ela fecha o ciclo
operacional depois da detecção:

```text
detectar -> registrar -> reconhecer ciência -> tratar -> resolver -> fechar -> auditar
```

Funcionalidades entregues:

- Listagem de eventos da tabela `condition_alerts`.
- Filtros por status de tratamento, ativo e severidade.
- KPIs de eventos, abertos, cientes, em tratamento e críticos.
- Cards priorizados por status e severidade.
- Alteração de status para `acknowledged`, `in_progress`, `resolved` ou `closed`.
- Registro de responsável, observação e ação tomada.
- Timeline do evento.
- Criação de evento manual para inspeção visual ou ocorrência de campo.
- Exportação CSV/TXT.

### Matriz de Escalonamento

A navegação lateral inclui a tela `Matriz de Escalonamento`. Ela governa:

- qual severidade usa qual canal;
- qual grupo recebe;
- quando repetir;
- quando escalar;
- qual mensagem seria enviada.

Arquivos principais:

- `src/dashboard/escalation_rules_store.json`
- `src/dashboard/escalation_repository.py`
- `src/dashboard/escalation_engine.py`
- `src/dashboard/escalation_ui.py`

Regras iniciais:

| Severidade | Canal | Destino | Repetição | Escalonamento |
| --- | --- | --- | --- | --- |
| ATENÇÃO | Dashboard | Operador local | Não repete | Não escala |
| ALERTA | Dashboard + Telegram | Manutenção | 30 min | 60 min |
| CRÍTICO | Dashboard + Telegram + WhatsApp | Manutenção + gestor | 10 min | 20 min |
| SEM COMUNICAÇÃO | Dashboard + Telegram | Automação/TI | 30 min | 60 min |

A tela possui abas para `Regras`, `Grupos de Contato`, `Canais` e `Simulação`.
Na simulação, os alertas atuais da Central são avaliados contra a matriz e o
dashboard mostra regra aplicada, ativo, severidade, métrica, canais, grupos de
destino, necessidade de repetição/escalonamento e a mensagem que seria enviada.

Essa matriz prepara Telegram/WhatsApp para funcionarem como canais governados
por severidade, status de tratamento e responsabilidade operacional, evitando
disparos soltos.

### Notification Outbox

A navegação lateral inclui a tela `Notification Outbox`. Ela ainda não envia
mensagens reais; nesta etapa cria uma fila local e processa em modo dry-run.
Os candidatos vêm de duas origens: alertas abertos da Central e estados atuais
da planta em `ATENÇÃO`, `ALERTA`, `CRÍTICO` ou `SEM COMUNICAÇÃO`.

Fluxo demonstrável:

```text
Alerta -> Matriz -> Outbox -> Envio simulado
```

Arquivos principais:

- `src/dashboard/notification_outbox_store.json`
- `src/dashboard/notification_outbox_repository.py`
- `src/dashboard/notification_outbox_engine.py`
- `src/dashboard/notification_outbox_ui.py`

Na tela:

- `Gerar/atualizar fila de notificações` calcula alertas e estados atuais
  contra a matriz e adiciona itens não duplicados à fila.
- `Processar em dry-run` marca os itens pendentes como processados sem chamar
  Telegram, WhatsApp ou e-mail.
- A fila exibe regra, ativo, severidade, canais, grupos e mensagem calculada.

Tabela esperada:

```text
condition_alerts
Partition key: tenant_asset
Sort key: alert_key
```

Variável usada:

```powershell
$env:CONDITION_ALERTS_TABLE="condition_alerts"
```

### Sistema de Lubrificação

A navegação lateral inclui a tela `Sistema de Lubrificação`, voltada ao piloto
`Monitoramento Inteligente de Lubrificação por Pressão`.

O submódulo monitora quatro saídas de graxa do conjunto de lubrificação, mantendo
os manômetros físicos e usando sensores eletrônicos de pressão para registrar
pressão instantânea, pico por ciclo, tempo de subida, tempo de alívio, pulso
detectado, anomalias, alertas e recomendação explicável.

Arquivos principais:

- `src/dashboard/lubrication/lubrication_config.py`
- `src/dashboard/lubrication/lubrication_engine.py`
- `src/dashboard/lubrication/lubrication_repository.py`
- `src/dashboard/lubrication/lubrication_ui.py`
- `src/edge/grease_bridge/grease_cycle_simulator.py`
- `src/edge/grease_bridge/grease_payload_sender.py`
- `config/lubrication_pilot_config.json`

Tabelas sugeridas:

```text
grease_lubrication_state
Partition key: tenant_id
Sort key: asset_id

grease_lubrication_cycles
Partition key: tenant_asset
Sort key: cycle_timestamp
```

Variáveis usadas:

```powershell
$env:GREASE_STATE_TABLE="grease_lubrication_state"
$env:GREASE_CYCLES_TABLE="grease_lubrication_cycles"
$env:LUBRICATION_CONFIG_PATH="config/lubrication_pilot_config.json"
```

Teste rápido sem hardware:

```powershell
.\scripts\create_lubrication_tables.ps1
python scripts\seed_lubrication_demo.py
```

### Endpoint de Ingestão de Lubrificação

O projeto também inclui uma API HTTP específica para receber ciclos reais da
bridge/gateway do sistema de lubrificação:

```text
GET  /grease/health
POST /grease/ingest
```

Arquivos principais:

- `src/api/grease_ingest_api.py`
- `src/api/grease_ingest_models.py`
- `src/api/grease_ingest_service.py`
- `src/edge/grease_bridge/grease_payload_sender_http.py`
- `deploy/grease-ingest.service`
- `deploy/install_grease_service.sh`
- `deploy/update_grease_service.sh`
- `deploy/nginx_grease_ingest.conf`

Execução local:

```powershell
.\scripts\run_grease_api.ps1 -Reload
.\scripts\test_grease_ingest.ps1
```

Na EC2, o serviço deve escutar em `127.0.0.1:8000` e o Nginx deve expor o
endpoint pelo domínio HTTPS:

```text
https://sentinelaindustrial.com.br/grease/ingest
```

Instalação na EC2:

```bash
cd /opt/automacaoapi
sudo bash deploy/install_grease_service.sh /opt/automacaoapi
```

Atualização depois de novos commits:

```bash
cd /opt/automacaoapi
sudo bash deploy/update_grease_service.sh /opt/automacaoapi
```

Não libere a porta `8000` no Security Group; o endpoint público deve passar pelo
Nginx em `80/443`.

Para piloto, o endpoint pode exigir token simples:

```text
GREASE_INGEST_TOKEN=token_do_piloto
```

O cliente/bridge deve enviar esse valor em `X-API-Key` ou `Authorization: Bearer`.

### Configuração de Campo — Lubrificação

A navegação lateral também inclui `Configuração de Campo — Lubrificação`, focada
na preparação do piloto real com gateway IO-Link, sensores físicos, manômetros
mantidos, baseline por saída, curva pressão x tempo, segurança do endpoint e
relatórios específicos.

Arquivos principais:

- `config/field_lubrication_config.json`
- `config/field_lubrication_config.example.json`
- `config/grease_iolink_gateway_config.example.json`
- `src/dashboard/lubrication_field/field_config_ui.py`
- `src/dashboard/lubrication_field/baseline_engine.py`
- `src/dashboard/lubrication_field/cycle_curve_engine.py`
- `src/edge/grease_bridge_field/bridge_runner.py`
- `src/edge/grease_bridge_field/payload_builder.py`
- `src/api/grease_security_middleware.py`

Scripts úteis:

```powershell
python scripts\test_field_config.py
python scripts\simulate_raw_iolink_cycle.py
.\scripts\run_grease_bridge_field.ps1
python scripts\generate_lubrication_report.py
```

Variáveis adicionais:

```text
GREASE_FIELD_CONFIG=config/field_lubrication_config.json
GREASE_ALLOWED_SOURCE_IPS=
```

Definition of Done Sprint 5A:

- Dashboard abre localmente.
- Lê `mvp_asset_state_dev`.
- Mostra `Motor_001` e métricas atuais.
- Lê `mvp_alerts_dev`.
- Mostra alerta ativo de `lubrication_degradation`.
- Mostra causa provável, evidências e ação recomendada.
- Atualiza sem reiniciar a aplicação.
- Testes locais continuam OK.

