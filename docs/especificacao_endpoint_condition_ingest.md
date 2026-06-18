# Especificação do Endpoint `/condition/ingest`

Endpoint público para telemetria geral de equipamentos monitorados.

## URLs

Produção piloto:

```text
GET  https://sentinelaindustrial.com.br/condition/health
POST https://sentinelaindustrial.com.br/condition/ingest
```

Local na EC2:

```text
GET  http://127.0.0.1:8001/condition/health
POST http://127.0.0.1:8001/condition/ingest
```

## Headers

```text
Content-Type: application/json
X-API-Key: <CONDITION_INGEST_TOKEN>
```

Também é aceito:

```text
Authorization: Bearer <CONDITION_INGEST_TOKEN>
```

## Payload

```json
{
  "event_id": "7e15e2eb9fd74e4f9ae6bf3d1bb7db71",
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "asset_name": "Motor Principal",
  "source": "condition_gateway_01",
  "timestamp": "2026-05-26T18:00:00Z",
  "metrics": [
    {"name": "rpm", "value": 1778.0, "unit": "rpm"},
    {"name": "vibration_rms_mm_s", "value": 4.4, "unit": "mm/s"},
    {"name": "vibration_peak_g", "value": 0.82, "unit": "g"},
    {"name": "temperature_c", "value": 62.8, "unit": "C"},
    {"name": "ultrasound_db", "value": 33.1, "unit": "dB"},
    {"name": "kurtosis", "value": 3.2, "unit": "index"},
    {"name": "crest_factor", "value": 3.1, "unit": "index"},
    {"name": "health_score", "value": 67.6, "unit": "score"},
    {"name": "severity_score", "value": 32.4, "unit": "score"}
  ],
  "quality": {
    "source": "edge_gateway",
    "sample_rate_hz": 1
  }
}
```

## Idempotência e ordenação

`event_id` identifica uma amostra durante todo o ciclo de entrega. A bridge
deve conservar o mesmo valor ao repetir um envio. Quando o endpoint recebe
novamente o evento já processado, responde com `ok=true` e `duplicate=true`,
sem regravar estado, histórico ou alertas.

Telemetria com timestamp anterior ao último estado aceito do ativo também não
substitui o estado atual. Nesse caso, a resposta contém `stale=true`.

## Regras e recuperação

Quando o ativo possui regras em `parameters_alerts`, esses parâmetros governam
a classificação das métricas recebidas. A janela de persistência configurada
é aplicada tanto para ativar o alerta quanto para confirmar sua recuperação.
Enquanto a normalidade ainda está sendo validada, o alerta permanece ativo.
Ativos sem parâmetros cadastrados mantêm temporariamente as regras legadas da
bancada de demonstração.

## Métricas recomendadas

| Métrica | Unidade | Observação |
|---|---:|---|
| `pressure_bar` | bar | Pressão de processo, linha, bomba ou lubrificação |
| `flow_rate_l_min` | L/min | Vazão medida ou calculada |
| `level_percent` | % | Nível percentual em tanque, silo, reservatório ou processo |
| `level_m` | m | Nível absoluto quando disponível |
| `rpm` | rpm | Rotação do ativo |
| `vibration_rms_mm_s` | mm/s | Vibração RMS |
| `vibration_peak_g` | g | Pico de aceleração |
| `temperature_c` | C | Temperatura |
| `ultrasound_db` | dB | Ultrassom |
| `kurtosis` | index | Indicador impulsivo |
| `crest_factor` | index | Fator de crista |
| `health_score` | score | Saúde do ativo |
| `severity_score` | score | Gravidade operacional |

O endpoint aceita outras métricas desde que estejam cadastradas no mapa de
sinais e nos parâmetros técnicos do ativo. Para implantação em campo, prefira
nomes estáveis, unidades explícitas e tags rastreáveis até o sensor ou canal
físico de origem.

## Persistência

O endpoint grava:

```text
mvp_asset_state_dev       Estado atual do ativo
condition_history         Histórico por minuto
condition_alerts          Alertas ativos detectados
```

## Teste rápido

```bash
TOKEN="$(sudo grep '^CONDITION_INGEST_TOKEN=' /opt/automacaoapi/.env | tail -1 | cut -d= -f2-)"

CONDITION_INGEST_ENDPOINT="https://sentinelaindustrial.com.br/condition/ingest" \
CONDITION_INGEST_TOKEN="$TOKEN" \
/opt/automacaoapi/.venv/bin/python /opt/automacaoapi/scripts/test_condition_ingest.py
```
