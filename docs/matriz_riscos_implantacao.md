
# MATRIZ DE RISCOS DA IMPLANTAÇÃO
## Sistema de Lubrificação por Pressão

| Risco | Probabilidade | Impacto | Consequência | Mitigação |
|---|---|---|---|---|
| Sensor com faixa inadequada | Média | Alto | Saturação ou leitura inútil | Usar 0–250 bar no piloto |
| Rosca incompatível | Média | Médio | Atraso na instalação | Medir manômetro antes da compra |
| Vazamento em adaptador | Baixa/Média | Alto | Perda de graxa e risco operacional | Usar conexões adequadas e teste estanqueidade |
| Sensor instalado sem suporte | Média | Médio | Vibração/dano mecânico | Usar suporte ou mangueira curta |
| Gateway incompatível | Média | Alto | Dados não chegam ao sistema | Confirmar protocolo antes da compra |
| Security Group bloqueado | Média | Médio | Endpoint inacessível | Liberar porta/IP antes do teste |
| Token ausente/incorreto | Média | Baixo/Médio | HTTP 401 | Validar token no checklist |
| Falta de baseline inicial | Alta | Médio | IA limitada no início | Coletar 20–50 ciclos reais |
| Regras fixas mal calibradas | Média | Médio | Alertas excessivos ou ausentes | Ajustar após ciclos reais |
| Falha de conectividade | Média | Médio | Perda temporária de dados | Buffer local na bridge |
| Interpretação errada pelo usuário | Média | Médio | Ação inadequada | Relatório e treinamento |
