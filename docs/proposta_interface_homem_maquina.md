# Proposta de Interface Homem-Máquina para Operação de Campo

## Diagnóstico
O operador de campo precisa responder rapidamente:

```text
Tem problema?
Onde está?
Qual é a prioridade?
O que devo fazer?
Preciso chamar manutenção?
```

Ele não precisa ver matriz de escalonamento, outbox, teste ponta a ponta, configuração de campo e modo apresentação na rotina normal.

## Solução
Criar dois modos:

### Modo Operador
```text
Painel da Planta
Equipamento
Lubrificação
Alertas
Relatórios
Ajuda
```

### Modo Técnico
Menu completo para configuração, testes, matriz, IA e manutenção do sistema.

## Troca de termos
| Técnico | Campo |
|---|---|
| Asset | Equipamento |
| Health Score | Saúde |
| Severity Score | Gravidade |
| Baseline | Padrão normal |
| Anomalia | Desvio |
| Endpoint | Endereço de recebimento |
