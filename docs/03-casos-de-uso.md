# Casos de Uso

## 1. Atores

| Ator | Descrição |
|---|---|
| Apresentador técnico | Pessoa que conduz a demonstração do MVP |
| Cliente | Pessoa que avalia a solução |
| Sistema simulador | Serviço que gera dados do motor virtual |
| UaExpert | Cliente OPC UA usado para demonstrar tags industriais |
| Bridge Edge | Serviço que lê dados simulados e envia para AWS |
| AWS Backend | Serviços serverless de ingestão, armazenamento e eventos |
| Motor de diagnóstico | Componente que aplica regras de falha |
| Dashboard | Interface para visualização de condição e alertas |

## 2. UC-001 — Iniciar simulação do motor

### Objetivo

Iniciar o motor virtual e gerar dados contínuos de telemetria.

### Atores

- Apresentador técnico.
- Sistema simulador.

### Pré-condições

- Python instalado.
- Dependências instaladas.
- Porta OPC UA disponível.

### Fluxo principal

1. Apresentador executa o script do simulador.
2. Sistema cria o servidor OPC UA.
3. Sistema cria o nó `Lab/Motor_001`.
4. Sistema inicia geração de dados a cada intervalo configurado.
5. Sistema alterna automaticamente entre cenários de normalidade e falha.

### Resultado esperado

O motor virtual passa a gerar tags OPC UA e payloads de telemetria.

### Exceções

- Porta OPC UA ocupada.
- Dependência Python ausente.
- Falha ao iniciar servidor.

## 3. UC-002 — Visualizar tags no UaExpert

### Objetivo

Demonstrar ao cliente que o motor virtual está expondo dados em formato industrial OPC UA.

### Atores

- Apresentador técnico.
- Cliente.
- UaExpert.

### Pré-condições

- Simulador OPC UA em execução.
- UaExpert instalado.

### Fluxo principal

1. Apresentador abre o UaExpert.
2. Apresentador adiciona endpoint:

```text
opc.tcp://localhost:4840/lab/opcua/
```

3. Apresentador navega até:

```text
Objects > Lab > Motor_001
```

4. Apresentador arrasta variáveis para a área de monitoramento.
5. Cliente observa tags mudando em tempo real.

### Resultado esperado

Cliente visualiza RPM, vibração, temperatura, ultrassom e demais variáveis sendo atualizadas.

### Exceções

- UaExpert não conecta.
- Endpoint incorreto.
- Firewall bloqueia porta.

## 4. UC-003 — Publicar telemetria via MQTT local

### Objetivo

Publicar dados simulados no broker MQTT local.

### Atores

- Simulador.
- Mosquitto.
- Bridge Edge.

### Pré-condições

- Mosquitto em execução.
- Tópico configurado.

### Fluxo principal

1. Simulador gera payload canônico.
2. Simulador publica mensagem MQTT local.
3. Bridge ou cliente de teste assina o tópico.
4. Mensagem é recebida e logada.

### Resultado esperado

A mensagem chega ao tópico:

```text
lab/cliente_demo/lab_virtual/motor_001/telemetry
```

## 5. UC-004 — Ler OPC UA e enviar para AWS

### Objetivo

Ler tags OPC UA pela bridge e enviar telemetria normalizada para AWS.

### Atores

- Bridge Edge.
- Servidor OPC UA.
- AWS IoT Core.
- API Gateway.

### Pré-condições

- Simulador OPC UA rodando.
- Credenciais AWS configuradas.
- Endpoint AWS configurado.

### Fluxo principal

1. Bridge conecta ao servidor OPC UA.
2. Bridge lê tags configuradas.
3. Bridge monta payload canônico.
4. Bridge publica via MQTT AWS ou HTTPS.
5. AWS recebe mensagem.
6. Lambda normaliza e armazena.

### Resultado esperado

O evento aparece em S3, Timestream e DynamoDB.

## 6. UC-005 — Normalizar e armazenar telemetria

### Objetivo

Validar, padronizar e armazenar dados recebidos na AWS.

### Atores

- Lambda Normalizadora.
- S3.
- Timestream.
- DynamoDB.
- CloudWatch.

### Pré-condições

- Payload recebido por MQTT ou HTTPS.
- Permissões IAM configuradas.

### Fluxo principal

1. Lambda recebe evento.
2. Lambda valida campos obrigatórios.
3. Lambda gera `event_id` quando ausente.
4. Lambda grava payload bruto no S3.
5. Lambda grava medidas no Timestream.
6. Lambda atualiza estado atual no DynamoDB.
7. Lambda publica evento no EventBridge.
8. Lambda registra logs no CloudWatch.

### Resultado esperado

Dados ficam disponíveis para consulta e diagnóstico.

## 7. UC-006 — Detectar falha de lubrificação

### Objetivo

Detectar falha inicial de lubrificação com base em ultrassom, temperatura e vibração.

### Atores

- Motor de diagnóstico.
- Dashboard.
- Cliente.

### Pré-condições

- Cenário `lubrication_degradation` ativo.
- Dados chegando à AWS.

### Fluxo principal

1. Motor de diagnóstico recebe evento normalizado.
2. Sistema consulta estado e janela recente de dados.
3. Regra detecta ultrassom acima do baseline.
4. Regra identifica temperatura em alta.
5. Sistema verifica que vibração ainda não está crítica.
6. Sistema gera alerta warning.
7. Dashboard exibe causa provável, evidências e ação recomendada.

### Resultado esperado

Alerta exibido:

```text
Causa provável: início de falha de lubrificação.
Ação recomendada: inspecionar lubrificação e condição do rolamento.
```

## 8. UC-007 — Detectar desbalanceamento

### Objetivo

Detectar comportamento compatível com desbalanceamento.

### Fluxo principal

1. Cenário `imbalance` inicia no simulador.
2. Vibração RMS aumenta continuamente.
3. Motor de diagnóstico identifica RMS elevado.
4. Sistema verifica ausência de forte indício de impacto de rolamento.
5. Sistema gera alerta critical.
6. Dashboard exibe evidências.

### Resultado esperado

Alerta exibido:

```text
Causa provável: possível desbalanceamento.
Ação recomendada: verificar balanceamento, fixação, acoplamento e base.
```

## 9. UC-008 — Detectar falha em rolamento

### Objetivo

Detectar comportamento compatível com falha em rolamento.

### Fluxo principal

1. Cenário `bearing_fault` inicia.
2. Kurtosis e crest factor aumentam.
3. Motor de diagnóstico detecta indícios de impacto mecânico.
4. Sistema gera alerta critical.
5. Dashboard mostra evidências.

### Resultado esperado

Alerta exibido:

```text
Causa provável: possível falha em rolamento.
Ação recomendada: inspecionar rolamento, lubrificação e espectro de vibração.
```

## 10. UC-009 — Acompanhar dashboard

### Objetivo

Permitir ao cliente visualizar condição atual, tendências e alertas.

### Fluxo principal

1. Usuário abre dashboard.
2. Dashboard consulta estado atual no DynamoDB.
3. Dashboard consulta histórico no Timestream.
4. Dashboard exibe gráficos de tendência.
5. Dashboard exibe alertas ativos.
6. Dashboard exibe recomendação técnica.

### Resultado esperado

Cliente entende claramente o valor da solução: detecção antecipada, explicabilidade e priorização.

