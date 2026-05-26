
# PLANO DE TESTE DE CAMPO
## Gateway IO-Link → /grease/ingest

## 1. Teste de comunicação

| Teste | Resultado esperado |
|---|---|
| Gateway energizado | LEDs/diagnóstico OK |
| Sensores reconhecidos | 4 portas ativas |
| Leitura instantânea | Pressão em bar por porta |
| Bridge acessa gateway | resposta HTTP/MQTT/OPC/Modbus |
| Bridge monta payload | JSON válido |
| API recebe payload | HTTP 200 |
| Dashboard atualiza | ciclo exibido |

## 2. Teste de ciclo normal

Simular ou aguardar ciclo real com pressão normal nas saídas.

Resultado esperado:

```text
Status geral NORMAL ou ATENÇÃO leve
Pulso detectado nas saídas
Pico registrado
Histórico salvo
```

## 3. Teste de baixa pressão

Simular baixa pressão ou usar payload controlado.

Resultado esperado:

```text
Alerta: baixa pressão
Possível falta de graxa, vazamento, linha aberta ou pistão sem atuação
```

## 4. Teste de alta pressão

Simular alta pressão.

Resultado esperado:

```text
Alerta: alta pressão
Possível obstrução, graxa endurecida ou ponto pesado
```

## 5. Teste de alívio lento

Simular pressão que demora a cair.

Resultado esperado:

```text
Atenção/Alerta: alívio lento
Recomendação de inspeção da linha/ponto lubrificado
```

## 6. Teste de ausência de pulso

Simular saída sem variação de pressão.

Resultado esperado:

```text
Crítico: sem pulso de lubrificação
Verificar pistão, linha ou distribuidor
```
