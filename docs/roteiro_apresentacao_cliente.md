
# ROTEIRO DE APRESENTAÇÃO AO CLIENTE
## Sistema de Lubrificação por Pressão

## 1. Abertura

Apresentar o problema atual:

```text
Hoje a verificação depende da leitura visual dos manômetros.
Não há histórico automático.
Não há alerta remoto.
Não há rastreabilidade por ciclo.
```

## 2. Proposta

Demonstrar a solução:

```text
Cada saída de graxa recebe um sensor de pressão.
O manômetro físico é mantido.
O sistema registra a pressão por saída e por ciclo.
A IA identifica baixa pressão, sobrepressão e alívio lento.
```

## 3. Fluxo técnico

```text
Sensor → Gateway IO-Link → Bridge → API → Dashboard → Alertas → IA
```

## 4. Dashboard

Mostrar:

1. Status geral;
2. Pressão por saída;
3. Últimos ciclos;
4. Alertas ativos;
5. Recomendação da IA.

## 5. Exemplo de interpretação

```text
A saída 04 apresentou pico acima do limite e alívio lento.
O sistema sugere possível obstrução, graxa endurecida ou ponto pesado.
```

## 6. Valor para o cliente

- Menos inspeção manual;
- Histórico por ciclo;
- Evidência de lubrificação;
- Alerta antes da falha;
- Apoio à manutenção preditiva;
- Registro técnico para auditoria/manutenção.

## 7. Fechamento

Apresentar próximos passos:

1. Definir sensores;
2. Validar roscas/adaptadores;
3. Instalar piloto;
4. Coletar ciclos reais;
5. Ajustar baseline;
6. Expandir para mais saídas/equipamentos.
