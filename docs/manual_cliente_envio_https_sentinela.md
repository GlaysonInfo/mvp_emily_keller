# Manual do cliente - envio HTTPS para o Sentinela

## Objetivo

Configurar o lado cliente para coletar sinais industriais e enviar telemetria ao
Sistema Sentinela na AWS por HTTPS.

Sinais suportados nesta etapa:

- pressão;
- vazão;
- temperatura;
- nível;
- vibração;
- rotação, ultrassom, saúde do ativo e severidade, quando disponíveis.

O histórico gerado por esses sinais alimenta monitoramento, prevenção de falhas,
alertas, diagnóstico e redução de paradas não programadas.

## Arquitetura de campo

```text
Sensor / transmissor / instrumento
  -> switch, gateway ou rede industrial local
  -> Raspberry Pi ou computador edge do cliente
  -> Bridge Sentinela
  -> HTTPS
  -> https://sentinelaindustrial.com.br/condition/ingest
  -> AWS / histórico / alertas / dashboard
```

O Raspberry Pi pode ser usado como edge/transmissor local quando o projeto exigir
um equipamento dedicado próximo aos sensores. A configuração de rede, acesso
remoto, usuário, SSH e sistema operacional deve seguir a documentação oficial da
Raspberry Pi.

Referências oficiais:

- Getting started: https://www.raspberrypi.com/documentation/computers/getting-started.html
- Configuration: https://www.raspberrypi.com/documentation/computers/configuration.html

## Responsabilidades

| Parte | Responsabilidade |
|---|---|
| Cliente | Energia, rede local, acesso à internet, IP/DNS, política de firewall e instalação física |
| Fabricante/integrador | Sensor, transmissor, switch, gateway, protocolo e documentação técnica |
| Sentinela | Cadastro do cliente/planta/ativos/sensores, token, bridge, endpoint e validação de payload |

## Pré-requisitos

1. Cliente e planta cadastrados no Admin Sentinela.
2. Ativo real cadastrado.
3. Sensor ou instrumento associado ao ativo.
4. Gateway/fonte de dados cadastrado.
5. Token `CONDITION_INGEST_TOKEN` emitido pela Sentinela.
6. Saída HTTPS liberada para:

```text
https://sentinelaindustrial.com.br/condition/health
https://sentinelaindustrial.com.br/condition/ingest
```

7. Relógio do edge sincronizado por NTP.
8. DNS funcional no equipamento cliente.

## Portas e segurança de rede

| Item | Valor |
|---|---|
| Protocolo externo | HTTPS |
| Porta externa | 443/tcp |
| Autenticação | Header `X-API-Key` |
| Direção | Cliente -> Sentinela |
| Entrada pública no cliente | Não necessária |

Não libere portas públicas no Raspberry Pi ou computador edge para o Sentinela.
O envio é sempre de saída.

## Preparar o computador edge

### Linux/Raspberry Pi OS

```bash
sudo apt update
sudo apt install -y python3 python3-venv git curl

curl https://sentinelaindustrial.com.br/condition/health
```

Resultado esperado:

```json
{"ok":true,"service":"condition-ingest-api"}
```

Clone ou copie o pacote Sentinela autorizado para o equipamento:

```bash
cd /opt
sudo git clone https://github.com/GlaysonInfo/mvp_emily_keller automacaoapi
sudo chown -R "$USER":"$USER" /opt/automacaoapi

cd /opt/automacaoapi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements_condition_api.txt
```

## Configurar o arquivo de campo

Crie a configuração a partir do exemplo:

```bash
cd /opt/automacaoapi
cp config/field_condition_config.example.json config/field_condition_config.json
```

Edite:

```bash
nano config/field_condition_config.json
```

Campos principais:

| Campo | Exemplo |
|---|---|
| `client.tenant_id` | `cliente_real` |
| `plant.plant_id` | `indoor` |
| `gateway.source_id` | `raspberrypi_edge_01` |
| `gateway.protocol` | `http_json`, `modbus_tcp`, `opcua`, `mqtt` ou adapter local |
| `gateway.endpoint` | URL local do gateway, arquivo ou adapter |
| `ingest_api.endpoint` | `https://sentinelaindustrial.com.br/condition/ingest` |
| `ingest_api.token_env` | `CONDITION_INGEST_TOKEN` |
| `assets[].asset_id` | `motor_001`, `tanque_001`, `bomba_001` |
| `assets[].signals[].metric` | `pressure_bar`, `flow_rate_l_min`, `temperature_c`, `level_percent`, `vibration_rms_mm_s` |
| `assets[].signals[].tag` | tag externa lida no gateway |

## Configurar o token

O token não deve ficar gravado no arquivo JSON. Use variável de ambiente ou
serviço `systemd`.

Teste manual:

```bash
export CONDITION_INGEST_TOKEN="cole_o_token_fornecido_pela_sentinela"
```

## Simular payload antes do envio real

```bash
cd /opt/automacaoapi
source .venv/bin/activate

PYTHONPATH=src:. \
CONDITION_FIELD_CONFIG=config/field_condition_config.json \
python scripts/simulate_condition_gateway_payload.py
```

Valide se o JSON contém:

- `tenant_id` correto;
- `plant_id` correto;
- `asset_id` cadastrado;
- `source` igual ao gateway/fonte;
- métricas com nome e unidade corretos.

## Enviar um teste real por HTTPS

```bash
cd /opt/automacaoapi
source .venv/bin/activate

export CONDITION_INGEST_TOKEN="cole_o_token_fornecido_pela_sentinela"

PYTHONPATH=src:. \
CONDITION_FIELD_CONFIG=config/field_condition_config.json \
CONDITION_BRIDGE_ONCE=1 \
python -m src.edge.condition_bridge_field.bridge_runner
```

Resultado esperado:

```text
Condition field bridge started.
Sent <asset_id> | status=<STATUS> | metrics=<quantidade>
```

No dashboard Admin Sentinela, confirme:

1. último payload recebido;
2. idade da última comunicação;
3. ativo comunicando;
4. status operacional;
5. histórico;
6. alerta de teste, se configurado.

## Rodar como serviço Linux

Crie o arquivo:

```bash
sudo nano /etc/systemd/system/sentinela-condition-bridge.service
```

Conteúdo:

```ini
[Unit]
Description=Sentinela Condition Bridge - Cliente
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/automacaoapi
Environment=PYTHONPATH=src:.
Environment=CONDITION_FIELD_CONFIG=config/field_condition_config.json
Environment=CONDITION_INGEST_TOKEN=cole_o_token_fornecido_pela_sentinela
ExecStart=/opt/automacaoapi/.venv/bin/python -m src.edge.condition_bridge_field.bridge_runner
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sentinela-condition-bridge
sudo systemctl status sentinela-condition-bridge --no-pager
```

Logs:

```bash
sudo journalctl -u sentinela-condition-bridge -f
```

## Checklist de aceite

| Item | Status |
|---|---|
| Edge energizado e em rede | [ ] |
| DNS resolve `sentinelaindustrial.com.br` | [ ] |
| `condition/health` responde | [ ] |
| Token configurado | [ ] |
| Arquivo de campo revisado | [ ] |
| Métricas mapeadas para ativo correto | [ ] |
| Payload simulado validado | [ ] |
| Primeiro envio HTTPS realizado | [ ] |
| Última comunicação visível no Admin Sentinela | [ ] |
| Histórico visível | [ ] |
| Alerta de teste gerado, reconhecido e tratado | [ ] |

## Problemas comuns

| Sintoma | Causa provável | Ação |
|---|---|---|
| HTTP 401 | Token ausente ou incorreto | Revisar `CONDITION_INGEST_TOKEN` |
| HTTP 403 | Origem/IP bloqueado | Revisar política do endpoint com a Sentinela |
| HTTP 422 | Payload inválido | Validar métricas duplicadas, nomes e unidades |
| HTTP 5xx | Serviço indisponível | Manter spool local e repetir automaticamente |
| Sem histórico | `tenant_id`, `plant_id`, `asset_id` ou `source` divergente | Conferir cadastro no Admin Sentinela |
| Sensor sem leitura | Tag externa incorreta ou gateway inacessível | Validar leitura local antes do envio |

## Observação sobre Bluetooth

Bluetooth deve ser usado para comissionamento local quando o equipamento do
fabricante disponibilizar configuração por BLE ou aplicativo proprietário. A
telemetria contínua deve seguir por gateway/edge e HTTPS, com autenticação,
histórico e auditoria no Sentinela.
