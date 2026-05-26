
# CHECKLIST DE COMISSIONAMENTO EM CAMPO
## Sistema de Lubrificação por Pressão

## 1. Preparação

| Item | OK | Observação |
|---|---|---|
| Identificar equipamento onde o sistema será instalado | [ ] |  |
| Confirmar quantidade de saídas de graxa do piloto | [ ] |  |
| Confirmar pressão operacional aproximada | [ ] |  |
| Confirmar escala dos manômetros existentes | [ ] |  |
| Confirmar rosca/conexão dos manômetros | [ ] |  |
| Confirmar espaço físico para instalação dos sensores | [ ] |  |
| Confirmar ponto de alimentação 24 Vcc | [ ] |  |
| Confirmar ponto de rede/comunicação | [ ] |  |

---

## 2. Instalação mecânica

| Item | OK | Observação |
|---|---|---|
| Manômetro físico mantido na saída 01 | [ ] |  |
| Manômetro físico mantido na saída 02 | [ ] |  |
| Manômetro físico mantido na saída 03 | [ ] |  |
| Manômetro físico mantido na saída 04 | [ ] |  |
| Sensor instalado em paralelo na saída 01 | [ ] |  |
| Sensor instalado em paralelo na saída 02 | [ ] |  |
| Sensor instalado em paralelo na saída 03 | [ ] |  |
| Sensor instalado em paralelo na saída 04 | [ ] |  |
| Adaptadores/conexões em T instalados corretamente | [ ] |  |
| Sensores sem esforço mecânico excessivo | [ ] |  |
| Conexões verificadas quanto a vazamento | [ ] |  |

---

## 3. Instalação elétrica e comunicação

| Item | OK | Observação |
|---|---|---|
| Fonte 24 Vcc instalada | [ ] |  |
| Gateway IO-Link energizado | [ ] |  |
| Sensor 01 conectado ao gateway | [ ] |  |
| Sensor 02 conectado ao gateway | [ ] |  |
| Sensor 03 conectado ao gateway | [ ] |  |
| Sensor 04 conectado ao gateway | [ ] |  |
| Cabos identificados | [ ] |  |
| Caixa elétrica organizada | [ ] |  |
| Comunicação do gateway validada | [ ] |  |

---

## 4. Configuração do sistema

| Item | OK | Observação |
|---|---|---|
| Cliente cadastrado | [ ] |  |
| Planta cadastrada | [ ] |  |
| Sistema de lubrificação cadastrado | [ ] |  |
| Gateway cadastrado como fonte de dados | [ ] |  |
| Saída 01 mapeada | [ ] |  |
| Saída 02 mapeada | [ ] |  |
| Saída 03 mapeada | [ ] |  |
| Saída 04 mapeada | [ ] |  |
| Endpoint `/grease/ingest` configurado | [ ] |  |
| Token de ingestão configurado | [ ] |  |
| Região AWS confirmada como `us-east-1` | [ ] |  |

---

## 5. Testes funcionais

| Teste | OK | Evidência |
|---|---|---|
| `/grease/health` responde | [ ] |  |
| Gateway envia payload ao endpoint | [ ] |  |
| Payload é aceito com HTTP 200 | [ ] |  |
| Ciclo aparece em Últimos Ciclos | [ ] |  |
| Pressão por saída aparece no dashboard | [ ] |  |
| Alerta de baixa pressão é gerado | [ ] |  |
| Alerta de alta pressão é gerado | [ ] |  |
| Recomendação da IA é exibida | [ ] |  |
| Relatório do piloto é exportado | [ ] |  |

---

## 6. Aceite de comissionamento

**Resultado:**
[ ] Aprovado
[ ] Aprovado com pendências
[ ] Reprovado nesta etapa

**Observações finais:**
[preencher]
