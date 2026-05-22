# Dicionário de Dados

## 1. Convenções

- Todos os timestamps devem usar UTC em formato ISO 8601.
- Identificadores devem usar snake_case.
- Métricas devem ter unidade explícita.
- Dados brutos devem ser preservados antes de qualquer transformação.
- Dados de laboratório podem conter o campo `failure_mode_simulated`, que não existirá em produção.

## 2. Payload canônico de telemetria

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|---|---|---:|---|---|
| event_id | string | Não | evt_123 | Identificador único do evento. Pode ser gerado na Lambda |
| tenant_id | string | Sim | cliente_demo | Identifica cliente ou tenant |
| plant_id | string | Sim | lab_virtual | Identifica planta, unidade ou ambiente |
| asset_id | string | Sim | motor_001 | Identifica ativo monitorado |
| source | string | Sim | opcua_lab_simulator | Fonte dos dados |
| timestamp | datetime | Sim | 2026-05-22T13:00:00Z | Momento da medição |
| failure_mode_simulated | string | Não | normal | Modo de falha usado somente em laboratório |
| metrics | array | Sim | [] | Lista de métricas medidas |

## 3. Métrica

| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|---|---|---:|---|---|
| name | string | Sim | vibration_rms_mm_s | Nome normalizado da métrica |
| value | number | Sim | 2.4 | Valor numérico |
| unit | string | Sim | mm/s | Unidade de medida |
| quality | string | Não | good | Qualidade do dado |
| original_name | string | Não | Vib RMS | Nome original recebido da fonte |

## 4. Métricas do motor virtual

| Nome normalizado | Unidade | Tipo | Faixa normal esperada | Descrição |
|---|---|---|---:|---|
| rpm | rpm | float | 1750 a 1810 | Rotação do motor |
| vibration_rms_mm_s | mm/s | float | 0.5 a 2.8 | Vibração RMS em velocidade |
| vibration_peak_g | g | float | 0.2 a 1.0 | Pico de vibração em aceleração |
| temperature_c | C | float | 45 a 65 | Temperatura do ativo ou componente |
| ultrasound_db | dB | float | 25 a 36 | Indicador de ultrassom |
| horimeter_h | h | float | crescente | Horímetro acumulado |
| kurtosis | index | float | 2.5 a 4.0 | Indicador estatístico de impulsos |
| crest_factor | index | float | 2.0 a 4.0 | Relação pico/RMS |
| health_score | score | float | 80 a 100 | Saúde calculada do ativo |
| severity | score | float | 0 a 100 | Severidade calculada |

## 5. Modos de falha simulados

| Código | Nome exibido | Descrição |
|---|---|---|
| normal | Normal | Comportamento saudável |
| lubrication_degradation | Falha de lubrificação | Ultrassom sobe primeiro, depois temperatura e vibração |
| imbalance | Desbalanceamento | Vibração RMS aumenta continuamente |
| bearing_fault | Falha em rolamento | Kurtosis e crest factor sobem antes do RMS crítico |

## 6. Entidade Tenant

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| tenant_id | string | Sim | Identificador do cliente |
| name | string | Sim | Nome do cliente |
| status | string | Sim | active, inactive |
| created_at | datetime | Sim | Data de criação |
| updated_at | datetime | Sim | Data de atualização |

## 7. Entidade Plant

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| plant_id | string | Sim | Identificador da planta |
| tenant_id | string | Sim | Cliente proprietário |
| name | string | Sim | Nome da planta |
| timezone | string | Sim | Timezone local para exibição |
| status | string | Sim | active, inactive |

## 8. Entidade Asset

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| asset_id | string | Sim | Identificador do ativo |
| plant_id | string | Sim | Planta associada |
| tenant_id | string | Sim | Cliente proprietário |
| name | string | Sim | Nome do ativo |
| asset_type | string | Sim | motor, pump, compressor etc. |
| criticality | integer | Sim | 1 a 5 |
| status | string | Sim | running, stopped, maintenance, unknown |
| created_at | datetime | Sim | Data de criação |

## 9. Entidade DataSource

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| source_id | string | Sim | Identificador da fonte |
| tenant_id | string | Sim | Cliente associado |
| plant_id | string | Sim | Planta associada |
| source_type | string | Sim | opcua, modbus_tcp, mqtt, https |
| endpoint | string | Não | Endpoint técnico |
| status | string | Sim | active, inactive, error |

## 10. Entidade TelemetryEvent

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| event_id | string | Sim | Identificador do evento |
| tenant_id | string | Sim | Cliente |
| plant_id | string | Sim | Planta |
| asset_id | string | Sim | Ativo |
| source | string | Sim | Fonte |
| timestamp | datetime | Sim | Timestamp da medição |
| received_at | datetime | Sim | Timestamp de recebimento |
| raw_s3_key | string | Sim | Caminho do payload bruto |
| validation_status | string | Sim | accepted, rejected |

## 11. Entidade Alert

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| alert_id | string | Sim | Identificador do alerta |
| tenant_id | string | Sim | Cliente |
| plant_id | string | Sim | Planta |
| asset_id | string | Sim | Ativo |
| alert_type | string | Sim | lubrication, imbalance, bearing_fault, generic |
| severity | string | Sim | info, warning, critical |
| status | string | Sim | open, acknowledged, resolved |
| probable_cause | string | Sim | Causa provável |
| confidence | number | Sim | Confiança de 0 a 1 |
| evidence | array | Sim | Lista de evidências |
| recommended_action | string | Sim | Ação recomendada |
| created_at | datetime | Sim | Criação |
| updated_at | datetime | Sim | Atualização |

## 12. Entidade DiagnosticEvidence

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| evidence_id | string | Sim | Identificador da evidência |
| alert_id | string | Sim | Alerta associado |
| metric_name | string | Sim | Métrica usada |
| observed_value | number | Sim | Valor observado |
| threshold | number | Não | Limite usado |
| message | string | Sim | Explicação textual |
| timestamp | datetime | Sim | Momento da evidência |

## 13. Entidade MaintenanceActionSimulated

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| action_id | string | Sim | Identificador da ação |
| alert_id | string | Sim | Alerta associado |
| action_type | string | Sim | inspect, lubricate, balance, replace_bearing |
| status | string | Sim | suggested, accepted, completed |
| description | string | Sim | Descrição da ação |
| created_at | datetime | Sim | Data de criação |

