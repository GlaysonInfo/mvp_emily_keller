# Fluxos de Integração

## 1. Fluxo local OPC UA para UaExpert

```mermaid
sequenceDiagram
    participant Sim as Simulador Motor
    participant OPC as Servidor OPC UA
    participant UA as UaExpert
    participant Cliente as Cliente

    Sim->>OPC: Atualiza tags do Motor_001
    UA->>OPC: Conecta no endpoint opc.tcp://localhost:4840/lab/opcua/
    UA->>OPC: Navega em Objects > Lab > Motor_001
    OPC-->>UA: Retorna nós e valores
    UA-->>Cliente: Exibe tags em tempo real
```

## 2. Fluxo local MQTT

```mermaid
sequenceDiagram
    participant Sim as Simulador Motor
    participant MQTT as Mosquitto Local
    participant Bridge as Bridge Edge

    Sim->>MQTT: Publica payload canônico
    Bridge->>MQTT: Assina tópico lab/+/+/+/telemetry
    MQTT-->>Bridge: Entrega telemetria
    Bridge->>Bridge: Valida e loga payload
```

## 3. Fluxo OPC UA para AWS via Bridge

```mermaid
sequenceDiagram
    participant OPC as Servidor OPC UA
    participant Bridge as Bridge Edge
    participant IoT as AWS IoT Core
    participant Lambda as Lambda Normalizadora
    participant S3 as Amazon S3
    participant TS as Timestream
    participant DDB as DynamoDB
    participant EB as EventBridge

    Bridge->>OPC: Lê tags do Motor_001
    OPC-->>Bridge: Retorna valores atuais
    Bridge->>Bridge: Monta payload canônico
    Bridge->>IoT: Publica MQTT
    IoT->>Lambda: Regra aciona Lambda
    Lambda->>Lambda: Valida e normaliza
    Lambda->>S3: Grava raw JSON
    Lambda->>TS: Grava medidas temporais
    Lambda->>DDB: Atualiza estado atual
    Lambda->>EB: Publica TelemetryNormalized
```

## 4. Fluxo HTTPS para AWS

```mermaid
sequenceDiagram
    participant Bridge as Bridge Edge
    participant API as API Gateway
    participant Lambda as Lambda Normalizadora
    participant S3 as Amazon S3
    participant TS as Timestream
    participant DDB as DynamoDB
    participant EB as EventBridge

    Bridge->>API: POST /telemetry
    API->>Lambda: Encaminha request
    Lambda->>Lambda: Valida schema
    Lambda->>S3: Grava bruto
    Lambda->>TS: Grava séries temporais
    Lambda->>DDB: Atualiza latest state
    Lambda->>EB: Publica evento
```

### 4.1 Fluxo cliente para envio HTTPS

Para implantação em campo, o caminho recomendado é:

```text
Sensor / transmissor / instrumento
  -> switch, gateway ou rede industrial local
  -> Raspberry Pi ou computador edge do cliente
  -> Bridge Sentinela
  -> HTTPS /condition/ingest
  -> Sistema Sentinela na AWS
```

Use o passo a passo em
`docs/manual_cliente_envio_https_sentinela.md` para configurar o lado cliente,
incluindo rede, token, arquivo de campo, simulação de payload, envio real por
HTTPS e serviço Linux.

## 5. Fluxo de diagnóstico

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant Rules as Motor de Regras
    participant TS as Timestream
    participant DDB as DynamoDB
    participant Dash as Dashboard

    EB->>Rules: Evento TelemetryNormalized
    Rules->>DDB: Busca estado atual do ativo
    Rules->>TS: Busca janela recente de métricas
    Rules->>Rules: Calcula tendência e aplica regras
    alt Falha detectada
        Rules->>DDB: Cria ou atualiza alerta
        Rules->>EB: Publica AlertCreated
    else Sem falha relevante
        Rules->>DDB: Mantém estado normal
    end
    Dash->>DDB: Consulta alertas ativos
    Dash->>TS: Consulta séries temporais
    Dash-->>Dash: Exibe tendências e diagnóstico
```

## 6. Payload de entrada MQTT/HTTPS

```json
{
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "source": "opcua_lab_simulator",
  "timestamp": "2026-05-22T13:00:00Z",
  "failure_mode_simulated": "lubrication_degradation",
  "metrics": [
    {"name": "rpm", "value": 1781.5, "unit": "rpm"},
    {"name": "vibration_rms_mm_s", "value": 2.8, "unit": "mm/s"},
    {"name": "temperature_c", "value": 66.5, "unit": "C"},
    {"name": "ultrasound_db", "value": 41.2, "unit": "dB"},
    {"name": "kurtosis", "value": 3.4, "unit": "index"},
    {"name": "crest_factor", "value": 3.2, "unit": "index"}
  ]
}
```

## 7. Payload de alerta

```json
{
  "alert_id": "alert_123",
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "alert_type": "lubrication",
  "severity": "warning",
  "status": "open",
  "probable_cause": "Início de falha de lubrificação",
  "confidence": 0.78,
  "evidence": [
    "Ultrassom acima do baseline",
    "Temperatura em tendência de alta",
    "Vibração ainda abaixo de nível crítico"
  ],
  "recommended_action": "Inspecionar lubrificação e condição do rolamento",
  "created_at": "2026-05-22T13:00:00Z"
}
```

## 8. Estratégia de tópicos MQTT

### 8.1 Laboratório local

```text
lab/{tenant_id}/{plant_id}/{asset_id}/telemetry
lab/{tenant_id}/{plant_id}/{asset_id}/status
lab/{tenant_id}/{plant_id}/{asset_id}/alerts
```

### 8.2 AWS IoT Core

```text
condition-monitoring/{tenant_id}/{plant_id}/{asset_id}/telemetry
condition-monitoring/{tenant_id}/{plant_id}/{asset_id}/status
```

## 9. Regras de retry

A bridge deve:

1. Tentar enviar evento.
2. Registrar erro em log local quando falhar.
3. Repetir com backoff exponencial.
4. Manter buffer local simples em arquivo ou SQLite na fase futura.
5. Nunca descartar dado sem log.

## 10. Tratamento de erro

| Erro | Ação |
|---|---|
| OPC UA indisponível | Logar, tentar reconectar e manter serviço ativo |
| MQTT indisponível | Repetir envio com backoff |
| API HTTPS retorna 4xx | Registrar payload rejeitado |
| API HTTPS retorna 5xx | Repetir envio |
| Payload inválido | Enviar para área rejected no S3 |
| Falha Timestream | Logar erro e acionar DLQ em fase posterior |

