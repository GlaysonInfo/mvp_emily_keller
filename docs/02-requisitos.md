# Documento de Requisitos

## 1. Objetivo

Definir os requisitos funcionais, não funcionais, técnicos e de negócio do MVP de bancada virtual de monitoramento de condição.

## 2. Escopo do MVP

O MVP deve demonstrar o ciclo completo de monitoramento de condição:

1. Simulação do motor.
2. Exposição dos dados via OPC UA.
3. Visualização das tags no UaExpert.
4. Leitura dos dados por bridge edge.
5. Publicação para AWS via MQTT/HTTPS.
6. Normalização e armazenamento.
7. Cálculo de regras de diagnóstico.
8. Exibição em dashboard.
9. Geração de alerta explicável.

## 3. Restrições

### 3.1 Restrições de produto

- Não desenvolver PLC.
- Não desenvolver firmware.
- Não desenvolver sensores físicos.
- Não desenvolver máquinas.
- Não controlar equipamentos reais.
- Não acionar atuadores.
- Não depender de rede industrial real.

### 3.2 Restrições técnicas

- O MVP deve rodar em notebook com Docker.
- O MVP deve poder rodar em EC2 para demonstração remota.
- O servidor OPC UA deve ser local e simulado.
- O UaExpert deve ser usado apenas como cliente OPC UA.
- O broker Mosquitto local pode aceitar conexão anônima somente no laboratório.
- Em ambiente real, MQTT deve usar TLS, autenticação e certificados.

### 3.3 Restrições éticas e de segurança

- Não coletar dados pessoais desnecessários.
- Não usar o sistema para avaliar desempenho individual de técnicos.
- Não gerar recomendações sem evidências.
- Não apresentar diagnóstico como certeza absoluta.
- Todo alerta deve apresentar confiança, evidências e recomendação.

## 4. Requisitos funcionais

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---:|---|
| RF-001 | Simular um motor industrial virtual | Alta | O simulador gera dados contínuos a cada intervalo configurável |
| RF-002 | Simular cenário normal | Alta | RPM estável, temperatura controlada e vibração baixa aparecem no dashboard |
| RF-003 | Simular falha de lubrificação | Alta | Ultrassom sobe antes de temperatura e vibração |
| RF-004 | Simular desbalanceamento | Alta | Vibração RMS cresce continuamente durante o cenário |
| RF-005 | Simular falha em rolamento | Alta | Kurtosis e crest factor sobem antes do RMS crítico |
| RF-006 | Expor tags via OPC UA | Alta | UaExpert consegue navegar até Objects > Lab > Motor_001 |
| RF-007 | Ler tags OPC UA pela bridge | Alta | Bridge lê todas as tags esperadas sem erro |
| RF-008 | Publicar telemetria via MQTT local | Alta | Mensagens chegam ao tópico configurado no Mosquitto |
| RF-009 | Publicar telemetria via MQTT AWS | Alta | Mensagens chegam ao AWS IoT Core |
| RF-010 | Publicar telemetria via HTTPS | Média | API Gateway recebe payload válido |
| RF-011 | Validar payload canônico | Alta | Payload inválido é rejeitado e logado |
| RF-012 | Armazenar payload bruto no S3 | Alta | Cada evento aceito gera arquivo JSON no S3 |
| RF-013 | Gravar séries temporais no Timestream | Alta | Métricas podem ser consultadas por janela temporal |
| RF-014 | Atualizar estado atual no DynamoDB | Alta | Último estado do ativo é consultável por chave |
| RF-015 | Gerar evento normalizado | Alta | EventBridge recebe evento TelemetryNormalized |
| RF-016 | Detectar alerta por regra técnica | Alta | Cenários de falha geram alerta esperado |
| RF-017 | Exibir alerta explicável | Alta | Dashboard mostra causa provável, evidências e ação recomendada |
| RF-018 | Exibir tendência temporal | Alta | Dashboard mostra gráfico de vibração, temperatura, ultrassom e RPM |
| RF-019 | Exibir status de saúde do ativo | Alta | Dashboard mostra health_score e severidade |
| RF-020 | Registrar logs técnicos | Alta | CloudWatch e logs locais registram fluxo e erros |
| RF-021 | Simular fechamento de alerta | Baixa | Usuário pode marcar alerta como reconhecido ou resolvido |
| RF-022 | Exportar evidências do alerta | Baixa | Usuário pode copiar ou baixar resumo do alerta |

## 5. Requisitos não funcionais

| ID | Requisito | Meta MVP |
|---|---|---|
| RNF-001 | Latência de ingestão | Até 10 segundos entre geração local e visualização no dashboard |
| RNF-002 | Disponibilidade da demo | 95% durante janela de apresentação |
| RNF-003 | Custo | Baixo custo, usando serverless sempre que possível |
| RNF-004 | Observabilidade | Logs de simulador, bridge, Lambda e dashboard |
| RNF-005 | Reprodutibilidade | Projeto deve rodar com comandos documentados |
| RNF-006 | Portabilidade | Rodar em notebook ou EC2 |
| RNF-007 | Segurança de laboratório | MQTT anônimo apenas local e documentado |
| RNF-008 | Segurança futura | Prever TLS, certificados e IAM mínimo necessário |
| RNF-009 | Escalabilidade futura | Separar ingestão, armazenamento, diagnóstico e dashboard |
| RNF-010 | Explicabilidade | Todo alerta deve apresentar evidências legíveis |

## 6. Requisitos de dados

### 6.1 Payload canônico

```json
{
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "motor_001",
  "source": "opcua_lab_simulator",
  "timestamp": "2026-05-22T13:00:00Z",
  "failure_mode_simulated": "normal",
  "metrics": [
    {"name": "rpm", "value": 1780.0, "unit": "rpm"},
    {"name": "vibration_rms_mm_s", "value": 2.1, "unit": "mm/s"},
    {"name": "temperature_c", "value": 60.0, "unit": "C"},
    {"name": "ultrasound_db", "value": 32.0, "unit": "dB"}
  ]
}
```

### 6.2 Campos obrigatórios

- tenant_id.
- plant_id.
- asset_id.
- source.
- timestamp.
- metrics.
- metrics[].name.
- metrics[].value.
- metrics[].unit.

## 7. Regras de diagnóstico MVP

### 7.1 Falha de lubrificação

Condição inicial sugerida:

```text
ultrasound_db > 38
AND temperature_c em tendência de alta
AND vibration_rms_mm_s ainda abaixo de nível crítico
```

Saída esperada:

- Severidade: warning.
- Causa provável: início de falha de lubrificação.
- Evidências: ultrassom acima do baseline, temperatura em alta, vibração ainda não crítica.
- Ação: verificar lubrificação e condição do rolamento.

### 7.2 Desbalanceamento

Condição inicial sugerida:

```text
vibration_rms_mm_s > 4.0
AND kurtosis < 4.5
```

Saída esperada:

- Severidade: critical.
- Causa provável: possível desbalanceamento.
- Evidências: vibração RMS elevada, sem indício forte de impacto de rolamento.
- Ação: verificar balanceamento, fixação, acoplamento e base.

### 7.3 Falha em rolamento

Condição inicial sugerida:

```text
kurtosis > 5.0
AND crest_factor > 4.5
```

Saída esperada:

- Severidade: critical.
- Causa provável: possível falha em rolamento.
- Evidências: kurtosis elevada, crest factor elevado, picos compatíveis com impacto mecânico.
- Ação: inspecionar rolamento, lubrificação e espectro de vibração.

## 8. Critérios gerais de sucesso

O MVP será considerado aprovado quando:

1. O cliente visualizar as tags OPC UA no UaExpert.
2. Os dados chegarem à AWS via MQTT ou HTTPS.
3. O histórico aparecer no dashboard.
4. Pelo menos três cenários de falha gerarem alertas explicáveis.
5. O dashboard apresentar causa provável, evidências e ação recomendada.
6. A arquitetura ficar clara como extensível para edge industrial real.

