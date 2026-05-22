# Backlog Técnico

## 1. Épico — Simulação de ativo

| ID | História | Prioridade |
|---|---|---:|
| SIM-001 | Como apresentador, quero iniciar um motor virtual para gerar dados sintéticos | Alta |
| SIM-002 | Como apresentador, quero alternar cenários de falha automaticamente | Alta |
| SIM-003 | Como desenvolvedor, quero configurar intervalo de amostragem por variável de ambiente | Média |
| SIM-004 | Como cliente, quero ver o modo de falha atual no dashboard | Média |

## 2. Épico — OPC UA

| ID | História | Prioridade |
|---|---|---:|
| OPC-001 | Como cliente, quero visualizar as tags no UaExpert | Alta |
| OPC-002 | Como bridge, quero ler todas as tags do Motor_001 | Alta |
| OPC-003 | Como desenvolvedor, quero configurar endpoint OPC UA por variável de ambiente | Média |

## 3. Épico — MQTT/HTTPS

| ID | História | Prioridade |
|---|---|---:|
| INT-001 | Como sistema, quero publicar telemetria no Mosquitto local | Alta |
| INT-002 | Como sistema, quero publicar telemetria no AWS IoT Core | Alta |
| INT-003 | Como sistema, quero publicar telemetria via API Gateway HTTPS | Média |
| INT-004 | Como sistema, quero aplicar retry em caso de falha temporária | Média |

## 4. Épico — AWS ingestão

| ID | História | Prioridade |
|---|---|---:|
| AWS-001 | Como backend, quero receber eventos por Lambda | Alta |
| AWS-002 | Como backend, quero gravar payload bruto no S3 | Alta |
| AWS-003 | Como backend, quero gravar séries no Timestream | Alta |
| AWS-004 | Como backend, quero atualizar latest state no DynamoDB | Alta |
| AWS-005 | Como backend, quero publicar evento no EventBridge | Alta |

## 5. Épico — Diagnóstico

| ID | História | Prioridade |
|---|---|---:|
| DIA-001 | Como sistema, quero detectar falha de lubrificação | Alta |
| DIA-002 | Como sistema, quero detectar desbalanceamento | Alta |
| DIA-003 | Como sistema, quero detectar falha em rolamento | Alta |
| DIA-004 | Como cliente, quero ver evidências do diagnóstico | Alta |
| DIA-005 | Como cliente, quero ver ação recomendada | Alta |

## 6. Épico — Dashboard

| ID | História | Prioridade |
|---|---|---:|
| DASH-001 | Como cliente, quero ver estado atual do ativo | Alta |
| DASH-002 | Como cliente, quero ver gráfico de tendência | Alta |
| DASH-003 | Como cliente, quero ver alertas ativos | Alta |
| DASH-004 | Como cliente, quero filtrar por janela de tempo | Média |
| DASH-005 | Como cliente, quero exportar resumo de alerta | Baixa |

## 7. Épico — Operação e demo

| ID | História | Prioridade |
|---|---|---:|
| OPS-001 | Como apresentador, quero rodar tudo com Docker Compose | Alta |
| OPS-002 | Como apresentador, quero um roteiro de demo reproduzível | Alta |
| OPS-003 | Como desenvolvedor, quero logs claros para troubleshooting | Alta |
| OPS-004 | Como equipe, quero controlar custo AWS do MVP | Média |

## 8. Fase 2

| ID | História | Prioridade |
|---|---|---:|
| F2-001 | Avaliar WAGO Edge Controller como host edge industrial | Média |
| F2-002 | Adicionar Modbus TCP completo | Média |
| F2-003 | Avaliar AWS IoT SiteWise Edge | Média |
| F2-004 | Criar modelo de anomalia com SageMaker | Média |
| F2-005 | Criar RAG com manuais e POPs | Baixa |
| F2-006 | Integrar ordem de serviço real | Baixa |

