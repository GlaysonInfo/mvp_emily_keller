
# Especificação de Payload — Lubrificação

## Payload de ciclo

```json
{
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "sistema_lubrificacao_01",
  "source_id": "grease_gateway_01",
  "timestamp_utc": "2026-05-25T23:30:00Z",
  "cycle_id": "cycle_20260525_233000",
  "metrics": {
    "pressure_saida_graxa_01_bar": 84.2,
    "peak_saida_graxa_01_bar": 102.3,
    "rise_time_saida_graxa_01_sec": 3.2,
    "decay_time_saida_graxa_01_sec": 4.8
  }
}
```

## Convenção de nomes

```text
pressure_saida_graxa_01_bar
peak_saida_graxa_01_bar
min_saida_graxa_01_bar
avg_saida_graxa_01_bar
rise_time_saida_graxa_01_sec
decay_time_saida_graxa_01_sec
```
