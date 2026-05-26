# Especificação do Endpoint `/grease/ingest`

## Método

```text
POST /grease/ingest
```

## URL local

```text
http://127.0.0.1:8000/grease/ingest
```

## URL no piloto EC2

```text
https://sentinelaindustrial.com.br/grease/ingest
```

Na EC2, o serviço da API deve ficar local em `127.0.0.1:8000` e ser exposto pelo
Nginx/HTTPS. Evite liberar a porta `8000` diretamente no Security Group.

Para teste interno na EC2:

```text
http://127.0.0.1:8000/grease/ingest
```

## Região AWS

```text
us-east-1
```

## Headers

```text
Content-Type: application/json
X-API-Key: <GREASE_INGEST_TOKEN>   # opcional se token estiver configurado
```

## Métricas por saída

```text
pressure_saida_graxa_01_bar
peak_saida_graxa_01_bar
min_saida_graxa_01_bar
avg_saida_graxa_01_bar
rise_time_saida_graxa_01_sec
decay_time_saida_graxa_01_sec
```

Repetir para `saida_graxa_01` até `saida_graxa_04` no piloto.

## Gravações realizadas

```text
grease_lubrication_state
grease_lubrication_cycles
condition_alerts
```
