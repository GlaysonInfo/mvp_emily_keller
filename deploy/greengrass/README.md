# Pacote Greengrass Ethernet-APL - Sentinela Industrial

Este pacote prepara o caminho:

```text
Sensor Ethernet-APL
  -> switch de campo APL / rede de automacao
  -> gateway industrial ou Raspberry Pi com AWS IoT Greengrass
  -> componente com.sentinela.ConditionAplBridge
  -> AWS IoT Core MQTT/TLS
  -> regra IoT para Lambda normalizadora ou DynamoDB raw
  -> telas Sentinela
```

## Conteudo

| Arquivo | Uso |
|---|---|
| `sentinela-condition-apl/recipe.yaml` | Receita do componente Greengrass. |
| `scripts/provision_iot_core_gateway.sh` | Cria thing, certificado X.509, politica IoT, token exchange role e device bundle. |
| `scripts/install_core_device.sh` | Instala o AWS IoT Greengrass Core no gateway Linux do cliente. |
| `scripts/build_component_package.ps1` | Gera o ZIP do componente a partir do codigo do repositório. |
| `templates/iot-policy-sentinela-greengrass.json` | Politica IoT do certificado do gateway. |
| `templates/iot-rule-condition-to-lambda.json` | Regra IoT recomendada para acionar Lambda normalizadora. |
| `templates/iot-rule-condition-raw-dynamodb.json` | Regra alternativa para arquivar payload bruto no DynamoDB. |

## 1. Gerar certificados e recursos AWS IoT Core

No computador tecnico Sentinela com AWS CLI autenticado:

```bash
cd /opt/automacaoapi

AWS_REGION=us-east-1 \
THING_NAME=sentinela-cliente-real-indoor-gateway-01 \
THING_GROUP_NAME=sentinela-greengrass-gateways \
SENTINELA_GREENGRASS_ARTIFACT_BUCKET=<bucket-de-componentes> \
bash deploy/greengrass/scripts/provision_iot_core_gateway.sh
```

Resultado esperado:

```text
build/greengrass/sentinela-cliente-real-indoor-gateway-01/
  certs/AmazonRootCA1.pem
  certs/device.pem.crt
  certs/private.pem.key
  device.env
```

Trate esta pasta como material sensivel. A chave privada nao deve ser enviada por e-mail.

## 2. Instalar Greengrass no gateway do cliente

Copie a pasta gerada para o gateway Linux do cliente e execute:

```bash
cd ~/sentinela-cliente-real-indoor-gateway-01
sudo bash /caminho/para/install_core_device.sh
```

Se o script estiver na propria pasta:

```bash
DEVICE_BUNDLE_DIR=. sudo -E bash deploy/greengrass/scripts/install_core_device.sh
```

Validacoes:

```bash
sudo systemctl status greengrass --no-pager
sudo ls -la /greengrass/v2
sudo tail -n 100 /greengrass/v2/logs/greengrass.log
```

## 3. Gerar pacote do componente

No repositório Sentinela:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\greengrass\scripts\build_component_package.ps1
```

Suba o ZIP gerado para o bucket configurado na receita:

```bash
aws s3 cp build/greengrass/component/sentinela-condition-apl.zip \
  s3://<bucket-de-componentes>/components/com.sentinela.ConditionAplBridge/1.0.0/sentinela-condition-apl.zip
```

Depois crie o componente Greengrass no console ou pela AWS CLI usando a receita
`deploy/greengrass/sentinela-condition-apl/recipe.yaml`.

## 4. Criar regra IoT Core

Opcao recomendada: IoT Rule -> Lambda normalizadora Sentinela.

```bash
aws iot create-topic-rule \
  --region us-east-1 \
  --rule-name sentinela_condition_to_lambda \
  --topic-rule-payload file://deploy/greengrass/templates/iot-rule-condition-to-lambda.rendered.json
```

Antes, substitua os placeholders:

- `${CONDITION_NORMALIZER_LAMBDA_ARN}`
- `${IOT_RULE_LOG_ROLE_ARN}`

Opcao temporaria: IoT Rule -> DynamoDB raw para evidenciar chegada dos dados
antes da normalizacao completa.

## 5. Configurar adapter local Ethernet-APL

O componente Greengrass espera que um adapter local exponha JSON HTTP em:

```text
http://127.0.0.1:8080/apl/read
```

Ajuste em `config/ethernet_apl_greengrass_condition_config.example.json`:

- `gateway.endpoint`
- `gateway.default_device_ip`
- `assets[].asset_id`
- `assets[].signals[].tag`
- `iot_core.topic_template`

O adapter pode ler o instrumento via Modbus TCP, OPC UA, PROFINET, web server
HTTPS do fabricante ou SDK proprietario, desde que entregue JSON normalizado.

## 6. Teste local antes do deploy Greengrass

```bash
PYTHONPATH=src:. \
CONDITION_FIELD_CONFIG=config/ethernet_apl_greengrass_condition_config.example.json \
python scripts/simulate_condition_gateway_payload.py
```

O payload deve conter `tenant_id`, `plant_id`, `asset_id`, `source`, `timestamp`
e `metrics`.
