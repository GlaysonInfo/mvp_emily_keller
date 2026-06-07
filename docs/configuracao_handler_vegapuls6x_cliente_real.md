# Configuracao do Handler / VEGAPULS 6X para cliente_real indoor

Este guia prepara o primeiro teste indoor com o sensor radar de nivel
VEGAPULS 6X, identificado no PDF `docs/configuration/Handler.pdf`.

## Identificacao tecnica

| Item | Valor inicial |
|---|---|
| Fabricante | VEGA |
| Modelo | VEGAPULS 6X |
| Funcao | Medicao continua de nivel de enchimento de liquidos ou solidos |
| Protocolos do equipamento | PROFINET, Modbus TCP, OPC UA, Ethernet-APL |
| IP de fabrica citado no guia | `192.168.0.110` |
| Alimentacao do sensor | 9,6 a 15 V DC |
| Cliente | `cliente_real` |
| Planta | `indoor` |
| Ativo Sentinela | `handler_vegapuls6x_01` |
| Fonte/gateway Sentinela | `handler_vegapuls6x_gateway_01` |

## Arquitetura recomendada para o indoor

```text
VEGAPULS 6X
  -> Modbus TCP ou OPC UA em rede local
  -> Adapter local do Handler
  -> JSON normalizado
  -> condition bridge field
  -> POST /condition/ingest
  -> Dashboard Sentinela
```

O runtime atual da bridge de campo le `simulated_json` e `http_json`.
Portanto, para o primeiro indoor, o caminho recomendado e usar um adapter local
que leia Modbus TCP ou OPC UA do VEGAPULS 6X e exponha HTTP JSON para a bridge.

## Arquivos preparados

| Arquivo | Uso |
|---|---|
| `config/cliente_real_indoor_platform_admin_store.json` | Tenant, planta, contrato e onboarding minimo |
| `config/cliente_real_indoor_config_store.json` | Cadastro operacional: fonte, ativo, sensores, sinais e limites |
| `config/cliente_real_indoor_condition_config.json` | Configuracao da bridge de campo |
| `src/edge/condition_bridge_field/sample_handler_vegapuls6x_response.json` | Sample de leitura normalizada do adapter |

## Metricas normalizadas

| Metrica Sentinela | Origem tecnica no guia | Unidade |
|---|---|---|
| `level_percent` | Percent / nivel percentual | `%` |
| `level_m` | Level / filling height | `m` |
| `distance_m` | Distance | `m` |
| `measurement_reliability_percent` | Measurement reliability / seguranca de medicao | `%` |
| `electronic_temperature_c` | Electronic temperature | `C` |
| `measurement_rate_hz` | Measurement Rate | `Hz` |
| `operating_voltage_v` | Operating Voltage | `V` |
| `apl_snr_db` | APL-SNR | `dB` |
| `device_state` | Device State / NAMUR State | `state` |

## Modbus TCP citado no guia

O guia informa leitura por FC04 `Read Input-Register`. Os registradores
relevantes para o adapter sao:

| Variavel | Registradores |
|---|---|
| Device State | 100 |
| Level value | 110, 111 |
| Distance value | 114, 115 |
| Percent value | 122, 123 |
| Linearized percent value | 126, 127 |
| Measurement reliability value | 130, 131 |
| Electronic temperature value | 134, 135 |
| Measurement rate value | 138, 139 |
| Operating voltage value | 142, 143 |
| APL-SNR value | 146, 147 |

Os valores principais usam IEEE 754 em dois registradores. O adapter deve
converter para `float` antes de entregar JSON.

## Comissionamento minimo

1. Confirmar alimentacao, aterramento, rede e acesso ao web server do sensor.
2. Ajustar IP do sensor para a rede indoor ou registrar o IP de fabrica
   `192.168.0.110` no plano de teste.
3. Ativar o protocolo escolhido no menu de servicos de rede do equipamento.
4. Calibrar 0% e 100% conforme geometria real do reservatorio/silo.
5. Confirmar supressao de ecos falsos quando houver parede, cone, aderencia ou
   agitacao relevante.
6. Validar leitura no adapter local.
7. Rodar a bridge com `CONDITION_FIELD_CONFIG=config/cliente_real_indoor_condition_config.json`.
8. Confirmar primeiro payload no Admin Sentinela > Saude do teste indoor.
9. Gerar alerta controlado e registrar ciencia/tratamento.

## Comandos locais de validacao

```powershell
$env:PYTHONPATH='src;.'
$env:CONDITION_FIELD_CONFIG='config/cliente_real_indoor_condition_config.json'
python scripts\simulate_condition_gateway_payload.py
```

Para campo real, altere `gateway.protocol` para `http_json`, ajuste
`gateway.endpoint` para o adapter real e configure:

```powershell
$env:HANDLER_ADAPTER_TOKEN='token_do_adapter'
$env:CONDITION_INGEST_TOKEN='token_do_endpoint'
python -m src.edge.condition_bridge_field.bridge_runner
```

## Pendencias antes de levar ao cliente

- Confirmar se o teste indoor medira liquido, solido, reservatorio ou silo.
- Definir altura fisica, distancia minima, ponto 0%, ponto 100% e faixa normal.
- Coletar numero de serie real do sensor.
- Definir protocolo final: Modbus TCP, OPC UA ou PROFINET via CLP.
- Validar se o adapter local sera nosso, do cliente ou de terceiro.
- Ajustar limites depois do primeiro baseline real.
