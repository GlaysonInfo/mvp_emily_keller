
# CRITÉRIOS DE SUCESSO DO PILOTO

O piloto será considerado bem-sucedido quando atender aos critérios abaixo:

| Critério | Meta |
|---|---|
| Saídas monitoradas | mínimo 4 |
| Manômetros físicos mantidos | 100% das saídas do piloto |
| Leitura eletrônica por saída | funcionando |
| Gateway IO-Link | comunicação validada |
| API `/grease/ingest` | HTTP 200 nos testes |
| Ciclos gravados | exibidos no dashboard |
| Alertas | gerados para baixa/alta pressão |
| IA | recomendação coerente exibida |
| Relatório | exportado com dados do piloto |
| Cliente | entende valor operacional do sistema |

## Critério técnico mínimo

```text
Sensor → Gateway → Bridge → API → DynamoDB → Dashboard
```

deve funcionar de ponta a ponta.
