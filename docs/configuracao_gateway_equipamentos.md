# Configuracao de gateway de equipamentos

Este modulo prepara a entrada de sinais reais de equipamentos monitorados para o endpoint publico:

```text
POST https://sentinelaindustrial.com.br/condition/ingest
```

## Fluxo

```text
Sensor / CLP / Gateway
  -> Bridge de campo
  -> /condition/ingest
  -> mvp_asset_state_dev
  -> condition_history
  -> condition_alerts
  -> Dashboard / IA / Alertas
```

## Configuracao

Copie o exemplo antes de editar em campo:

```powershell
copy config\field_condition_config.example.json config\field_condition_config.json
```

No arquivo `config/field_condition_config.json`, ajuste:

| Area | Campo |
|---|---|
| Cliente | `client.tenant_id` |
| Planta | `plant.plant_id` |
| Gateway | `gateway.source_id`, `gateway.protocol`, `gateway.endpoint` |
| API | `ingest_api.endpoint`, `ingest_api.token_env`, retry e fila persistente |
| Ativos | `assets[].asset_id`, `asset_name`, `area`, `criticality` |
| Sinais | `assets[].signals[].metric`, `tag`, `unit` |

## Protocolos suportados inicialmente

| Protocolo | Uso |
|---|---|
| `simulated_json` | Demonstracao local com arquivo JSON |
| `http_json` | Gateway/edge que exponha leitura por HTTP GET |

Para gateways Modbus, OPC UA ou MQTT, a recomendacao e usar uma bridge local que leia o protocolo industrial e exponha um JSON normalizado para este modulo.

## Teste local de mapeamento

```powershell
python scripts\simulate_condition_gateway_payload.py
```

## Execucao da bridge

```powershell
$env:CONDITION_INGEST_TOKEN="token_do_piloto"
.\scripts\run_condition_bridge_field.ps1
```

Na EC2/Linux, o equivalente e:

```bash
cd /opt/automacaoapi
source .venv/bin/activate
export CONDITION_FIELD_CONFIG=config/field_condition_config.json
export CONDITION_INGEST_TOKEN="token_do_piloto"
python -m src.edge.condition_bridge_field.bridge_runner
```

## Payload gerado

Cada ativo habilitado gera um payload no formato aceito pelo endpoint:

```json
{
  "event_id": "identificador-unico-da-amostra",
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "source": "condition_gateway_01",
  "metrics": [
    {"name": "rpm", "value": 1778.0, "unit": "rpm"},
    {"name": "vibration_rms_mm_s", "value": 4.4, "unit": "mm/s"},
    {"name": "temperature_c", "value": 62.8, "unit": "C"}
  ]
}
```

Antes do envio, cada payload é salvo em `ingest_api.spool_dir`. Em caso de
indisponibilidade da rede ou da API, a bridge conserva a amostra e repete o
envio com backoff exponencial. O arquivo só é removido depois da confirmação
da API. O `event_id` permite que uma retransmissão seja reconhecida sem gerar
novo estado, histórico ou alerta.
