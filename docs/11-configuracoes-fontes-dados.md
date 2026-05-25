# Configurações - Fontes de Dados e Mapeamento de Sinais

## 1. Decisão de arquitetura

O módulo `Configurações` deve começar por `Fontes de Dados`.

O ativo monitorado não deve guardar protocolo, endpoint ou credencial de
comunicação. Motor, bomba, compressor e redutor são objetos monitorados. Quem
fala com o sistema é a camada de aquisição:

- Sensor.
- PLC / CLP.
- Gateway / edge device.
- SCADA.
- API.
- MQTT broker.
- OPC UA server.
- Entrada manual ou CSV.

A hierarquia correta é:

```text
Cliente
└── Planta
    ├── Fontes de Dados / Gateways / Conectores
    └── Ativos Monitorados
        └── Mapeamento de sinais/tags vindos das fontes de dados
```

Isso evita repetir a mesma conexão em vários ativos. Uma fonte OPC UA pode servir
20 ativos, e cada ativo mapeia apenas suas próprias tags.

## 2. Idioma oficial do sistema

Todos os conectores devem entregar telemetria no mesmo contrato interno,
independentemente da origem ser OPC UA, MQTT, Modbus, HTTP, CSV, gateway próprio
ou gateway do cliente.

Contrato interno inicial:

```json
{
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "source_id": "opcua_edge_bridge_01",
  "timestamp_utc": "2026-05-23T16:25:00Z",
  "metrics": {
    "rpm": 1779.57,
    "vibration_rms_mm_s": 2.96,
    "temperature_c": 67.91,
    "ultrasound_db": 41.54,
    "kurtosis_index": 3.59,
    "crest_factor_index": 3.42,
    "vibration_peak_g": 0.69,
    "hourmeter_h": 1284.03
  },
  "quality": {
    "status": "good",
    "latency_ms": 120,
    "sample_rate_sec": 5
  }
}
```

O dashboard, histórico, alertas e IA não devem depender do protocolo de origem.
Eles só devem consumir o contrato interno padronizado.

## 3. Primeira entrega do módulo Configurações

A primeira versão deve preparar a estrutura, ainda sem implementação funcional
em tela.

Menu futuro:

```text
Configurações
├── Cliente
├── Planta
├── Fontes de Dados
├── Ativos
├── Mapeamento de Sinais
├── Parâmetros e Alertas
├── Marco Zero
├── Lubrificação
└── Base de Conhecimento IA
```

Prioridade de implementação:

1. Fontes de Dados.
2. Ativos.
3. Mapeamento de Sinais.
4. Parâmetros técnicos e regras de alerta.
5. Marco zero.
6. Lubrificação.
7. Base de conhecimento IA.

## 4. Fontes de Dados

As fontes iniciais recomendadas para o MVP são:

| source_id | Tipo | Protocolo | Função |
|---|---|---|---|
| bancada_virtual | Simulação | Interno | Demonstração |
| opcua_edge_bridge_01 | Gateway | OPC UA / HTTPS | Integração industrial real |
| csv_manual_01 | Upload | CSV | Entrada manual ou offline |

Campos da entidade `config_data_sources`:

| Campo | Exemplo | Observação |
|---|---|---|
| tenant_id | cliente_demo | Dono da configuração |
| plant_id | lab_virtual | Unidade industrial |
| source_id | opcua_edge_bridge_01 | Identificador estável |
| name | Bridge OPC UA Linha 1 | Nome amigável |
| source_kind | gateway | simulação, gateway, API, upload |
| protocol | opcua_https | interno, opcua_https, mqtt, http, csv |
| environment | demo | demo, piloto, produção |
| endpoint_ref | opc.tcp://... ou URL | Pode ser mascarado |
| collection_interval_sec | 5 | Frequência de leitura |
| history_interval_sec | 60 | Frequência de gravação histórica |
| status | active | active, inactive, failed, pending |
| credential_ref | aws-secrets:... | Nunca texto puro |
| last_test_at | 2026-05-23T16:25:00Z | Último teste |
| last_test_status | ok | ok, failed, not_tested |
| last_payload_at | 2026-05-23T16:25:00Z | Último pacote recebido |

Credenciais devem ficar em variável de ambiente, AWS Secrets Manager ou solução
equivalente. A configuração deve armazenar apenas referência segura.

## 5. Mapeamento de Sinais

O cadastro do ativo deve apontar para uma fonte de dados e mapear tags para
métricas internas.

Exemplo visual:

```text
Ativo: motor_001
Fonte de dados: opcua_edge_bridge_01

rpm                  -> Motor001.RPM
vibration_rms_mm_s   -> Motor001.VIB_RMS
temperature_c        -> Motor001.TEMP
ultrasound_db        -> Motor001.ULTRA
hourmeter_h          -> Motor001.HOUR
```

Campos da entidade `config_asset_signal_map`:

| Campo | Exemplo | Observação |
|---|---|---|
| tenant_id | cliente_demo | Dono da configuração |
| plant_id | lab_virtual | Unidade industrial |
| asset_id | motor_001 | Ativo monitorado |
| source_id | opcua_edge_bridge_01 | Fonte associada |
| internal_metric | vibration_rms_mm_s | Métrica canônica |
| external_tag | Motor001.VIB_RMS | Tag externa |
| unit | mm/s | Unidade esperada |
| conversion | direct | direct, scale, expression |
| scale | 1.0 | Opcional |
| offset | 0.0 | Opcional |
| required | true | Falha se ausente |
| status | active | active, inactive |

## 6. Validação futura

A tela `Fontes de Dados` deve ter ações futuras:

- Testar conexão.
- Validar tags.
- Exibir último pacote recebido.
- Exibir latência média.
- Exibir tags encontradas e tags com erro.

Resposta esperada:

```text
Conexão OK
Último pacote recebido: 23/05/2026 16:25:00
Tags encontradas: 8/8
Tags com erro: 0
Latência média: 120 ms
Status: pronto para monitoramento
```

## 7. O que não implementar

Evitar o modelo:

```text
Ativo
├── protocolo
├── endpoint
├── usuário
├── senha
└── tags
```

Esse desenho acopla ativo físico a conexão técnica e duplica configuração quando
vários ativos usam o mesmo gateway.

Modelo correto:

```text
Fonte de Dados cadastrada uma vez
↓
Vários ativos usam essa fonte
↓
Cada ativo mapeia suas próprias tags
```

## 8. Próxima implementação recomendada

Sem codificação funcional neste momento. Próximo passo, quando autorizado:

1. Criar modelos locais em JSON para `config_data_sources` e
   `config_asset_signal_map`.
2. Criar tela `Configurações` com abas.
3. Implementar apenas `Fontes de Dados` em modo local/demonstração.
4. Implementar `Mapeamento de Sinais`.
5. Só depois persistir em DynamoDB ou outra camada definitiva.
