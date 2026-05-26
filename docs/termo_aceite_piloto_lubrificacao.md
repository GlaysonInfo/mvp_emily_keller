
# TERMO DE ACEITE TÉCNICO DO PILOTO
## Monitoramento Inteligente de Lubrificação por Pressão

## 1. Identificação

**Cliente:** [preencher]
**Planta/Unidade:** [preencher]
**Área/Equipamento:** [preencher]
**Sistema monitorado:** Sistema de Lubrificação Centralizada
**Data do comissionamento:** [preencher]
**Responsável do cliente:** [preencher]
**Responsável técnico do piloto:** [preencher]

---

## 2. Objetivo do piloto

Validar tecnicamente a solução de monitoramento inteligente de lubrificação por pressão, com instrumentação de saídas de graxa por sensores eletrônicos, mantendo os manômetros físicos existentes, com envio dos dados ao sistema em nuvem para registro histórico, alertas e recomendação operacional por IA.

---

## 3. Arquitetura implantada

A arquitetura do piloto segue o fluxo:

```text
Sensor de pressão por saída
→ Gateway IO-Link
→ Bridge Edge
→ Endpoint HTTP /grease/ingest
→ DynamoDB
→ Dashboard Sistema de Lubrificação
→ Alertas
→ Recomendação da IA
```

---

## 4. Escopo validado

| Item | Situação | Observação |
|---|---|---|
| Saídas de graxa monitoradas | [ ] Validado | 4 saídas no piloto |
| Manômetros físicos mantidos | [ ] Validado | Leitura visual preservada |
| Sensores de pressão instalados | [ ] Validado | Faixa recomendada 0–250 bar |
| Gateway IO-Link configurado | [ ] Validado | Portas/tags mapeadas |
| Bridge Edge operando | [ ] Validado | Envio para endpoint |
| Endpoint `/grease/ingest` ativo | [ ] Validado | EC2 / API |
| Dados gravados no DynamoDB | [ ] Validado | Estado e ciclos |
| Dashboard atualizado | [ ] Validado | Sistema de Lubrificação |
| Histórico de ciclos exibido | [ ] Validado | Últimos ciclos |
| Alertas gerados | [ ] Validado | Baixa/alta pressão |
| Recomendação da IA exibida | [ ] Validado | Diagnóstico operacional |

---

## 5. Critérios de aceite

O piloto será considerado tecnicamente aceito quando demonstrar:

1. leitura individual das saídas monitoradas;
2. compatibilidade entre leitura física do manômetro e leitura eletrônica;
3. recepção dos dados pelo endpoint `/grease/ingest`;
4. gravação dos ciclos no banco de dados;
5. exibição dos ciclos no dashboard;
6. geração de alerta por condição anormal;
7. emissão de recomendação técnica automática;
8. rastreabilidade mínima do ciclo de lubrificação.

---

## 6. Evidências

Anexar ou registrar:

| Evidência | Referência |
|---|---|
| Foto dos manômetros e sensores instalados | [preencher] |
| Print do gateway/portas IO-Link | [preencher] |
| Print do endpoint/health check | [preencher] |
| Print do dashboard Sistema de Lubrificação | [preencher] |
| Print dos últimos ciclos | [preencher] |
| Print dos alertas ativos | [preencher] |
| Print da recomendação da IA | [preencher] |

---

## 7. Pendências identificadas

| Pendência | Responsável | Prazo | Status |
|---|---|---|---|
| [preencher] | [preencher] | [preencher] | [preencher] |

---

## 8. Conclusão técnica

Após a execução dos testes de campo, verificou-se que a solução demonstrou capacidade de monitorar as saídas de graxa por pressão, registrar ciclos de lubrificação, gerar histórico, identificar condições anormais e apresentar recomendações operacionais por IA.

**Resultado do aceite:**
[ ] Aceito sem ressalvas
[ ] Aceito com pendências
[ ] Não aceito nesta etapa

---

## 9. Assinaturas

**Responsável técnico do piloto:**
Nome: ___________________________
Assinatura: ______________________
Data: ____/____/______

**Responsável do cliente:**
Nome: ___________________________
Assinatura: ______________________
Data: ____/____/______
