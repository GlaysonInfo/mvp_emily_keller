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
| `Bluetooth LE (configuração local)` | Notebook Admin Sentinela pareia localmente para ler configuração/parâmetros do equipamento |
| `Bluetooth fabricante (configuração local)` | Canal local proprietário, dependente de biblioteca, aplicativo ou SDK do fabricante |

Para gateways Modbus, OPC UA ou MQTT, a recomendacao e usar uma bridge local que leia o protocolo industrial e exponha um JSON normalizado para este modulo.

## Configuração local via Bluetooth

Quando o equipamento de monitoramento do fabricante disponibilizar parâmetros
por Bluetooth, o notebook do Admin Sentinela deve ser tratado como ferramenta de
comissionamento local, não como canal permanente de telemetria.

Fluxo recomendado:

1. Admin Sentinela acessa a planta com notebook autorizado.
2. Notebook pareia por Bluetooth com o equipamento do fabricante.
3. Software, SDK ou adapter do fabricante lê configuração, canais, unidades,
   limites e identificação do dispositivo.
4. Admin valida os dados e registra no onboarding: ativo, sensor, gateway,
   métricas internas, tags externas, faixa do instrumento e limites iniciais.
5. A telemetria contínua segue pelo gateway/edge local e envio HTTPS para o
   Sentinela.

Itens mínimos a capturar:

| Item | Exemplo |
|---|---|
| Identificação do equipamento | fabricante, modelo, série, firmware |
| Canal físico | porta, endereço, UUID BLE, tag externa ou registrador |
| Métrica interna | `pressure_bar`, `flow_rate_l_min`, `temperature_c`, `level_percent`, `vibration_rms_mm_s` |
| Unidade | bar, L/min, C, %, mm/s |
| Faixa do instrumento | 0 a 10 bar, 0 a 100 %, 0 a 25 mm/s |
| Faixa nominal do processo | faixa esperada da operação real |
| Credencial ou pareamento | referência segura, nunca senha em texto aberto |

Essa etapa deve gerar auditoria de configuração. O uso de Bluetooth em produção
deve respeitar política do cliente, distância física, autorização de pareamento
e documentação do fabricante.

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
