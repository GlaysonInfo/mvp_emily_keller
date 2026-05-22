# Critérios de Aceite da Demonstração

## 1. Objetivo

Definir uma lista objetiva para validar se o MVP está pronto para ser demonstrado ao cliente.

## 2. Checklist técnico antes da demo

| Item | Status esperado |
|---|---|
| Docker instalado | OK |
| Python instalado | OK |
| Dependências Python instaladas | OK |
| Mosquitto local rodando | OK |
| Simulador OPC UA rodando | OK |
| UaExpert conecta no endpoint | OK |
| Tags aparecem em Objects > Lab > Motor_001 | OK |
| Bridge lê tags OPC UA | OK |
| Bridge publica MQTT local | OK |
| Bridge publica para AWS | OK |
| Lambda recebe evento | OK |
| S3 grava payload bruto | OK |
| Timestream recebe métricas | OK |
| DynamoDB atualiza latest state | OK |
| Motor de regras cria alerta | OK |
| Dashboard exibe séries temporais | OK |
| Dashboard exibe alerta explicável | OK |

## 3. Roteiro da demo

### Etapa 1 — Contexto

Explicar que a bancada é virtual e controlada.

Mensagem-chave:

```text
Este MVP não controla equipamentos e não depende de PLC. Ele demonstra a camada de software que recebe, padroniza, monitora, diagnostica e recomenda ações a partir de dados industriais.
```

### Etapa 2 — Motor virtual

Mostrar o terminal com o simulador rodando.

Critério de sucesso:

- Logs atualizam a cada segundo ou intervalo configurado.
- O modo normal aparece inicialmente.

### Etapa 3 — UaExpert

Mostrar conexão OPC UA.

Critério de sucesso:

- Endpoint conectado.
- Variáveis aparecem no UaExpert.
- Valores mudam em tempo real.

### Etapa 4 — Bridge Edge

Mostrar a bridge lendo OPC UA e enviando dados.

Critério de sucesso:

- Logs indicam leitura das tags.
- Logs indicam publicação MQTT/HTTPS.

### Etapa 5 — AWS

Mostrar evidência de chegada dos dados.

Critério de sucesso:

- Payload no S3.
- Último estado no DynamoDB.
- Série temporal no Timestream.

### Etapa 6 — Dashboard

Mostrar tendências.

Critério de sucesso:

- Gráfico de RPM.
- Gráfico de vibração RMS.
- Gráfico de temperatura.
- Gráfico de ultrassom.
- Health score.

### Etapa 7 — Falha inicial

Aguardar mudança de cenário.

Critério de sucesso:

- Falha de lubrificação gera warning.
- Desbalanceamento gera critical.
- Falha de rolamento gera critical.

### Etapa 8 — Diagnóstico explicável

Mostrar alerta.

Critério de sucesso:

O dashboard exibe:

- Causa provável.
- Severidade.
- Confiança.
- Evidências.
- Ação recomendada.

## 4. Critérios de aceite por cenário

### 4.1 Normal

| Métrica | Esperado |
|---|---|
| RPM | Estável |
| Temperatura | Controlada |
| Vibração RMS | Baixa |
| Ultrassom | Baixo |
| Alerta | Nenhum ou info |

### 4.2 Falha de lubrificação

| Métrica | Esperado |
|---|---|
| Ultrassom | Sobe primeiro |
| Temperatura | Sobe depois |
| Vibração RMS | Pode subir levemente |
| Alerta | Warning |
| Diagnóstico | Início de falha de lubrificação |

### 4.3 Desbalanceamento

| Métrica | Esperado |
|---|---|
| Vibração RMS | Cresce continuamente |
| Kurtosis | Não necessariamente alta |
| Crest factor | Não necessariamente alto |
| Alerta | Critical |
| Diagnóstico | Possível desbalanceamento |

### 4.4 Falha em rolamento

| Métrica | Esperado |
|---|---|
| Kurtosis | Sobe |
| Crest factor | Sobe |
| Vibração RMS | Pode subir depois |
| Alerta | Critical |
| Diagnóstico | Possível falha em rolamento |

## 5. Critérios de reprovação

A demo deve ser considerada não pronta se:

- UaExpert não conectar ao servidor OPC UA.
- As tags não mudarem em tempo real.
- A bridge não enviar dados.
- AWS não armazenar eventos.
- Dashboard não exibir tendência.
- Nenhuma regra gerar alerta.
- Alertas não tiverem evidência e ação recomendada.

## 6. Checklist Sprint 2 - OPC UA para MQTT local

### 6.1 Comandos

Com o Docker Desktop aberto:

```powershell
docker info
docker compose up -d mosquitto
docker compose ps
```

Terminal 1:

```powershell
python -m simulator.opcua_server
```

Terminal 2:

```powershell
python -m edge_bridge.main
```

Terminal 3:

```powershell
docker exec -it lab-mosquitto mosquitto_sub -h localhost -t "lab/+/+/+/telemetry" -v
```

### 6.2 UaExpert

Endpoint:

```text
opc.tcp://localhost:4840/lab/opcua/
```

Caminho:

```text
Objects > Lab > Motor_001
```

Tags esperadas:

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

### 6.3 Critério de aceite

- Mosquitto responde e aparece em `docker ps`.
- UaExpert exibe as 11 tags do `Motor_001`.
- A bridge publica no tópico `lab/cliente_demo/lab_virtual/motor_001/telemetry`.
- O payload contém `failure_mode_simulated` fora de `metrics`.
- `metrics` contém apenas valores numéricos.
- Pelo menos 9 métricas numéricas aparecem no payload.
- Se OPC UA ou MQTT ficarem indisponíveis, a bridge registra erro e tenta novamente no próximo ciclo.

