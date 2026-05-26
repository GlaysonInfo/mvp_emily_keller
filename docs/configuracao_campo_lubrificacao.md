# Configuração de Campo — Lubrificação

A configuração de campo reúne:
- cliente;
- planta;
- sistema de lubrificação;
- gateway IO-Link;
- sensores por saída;
- regras iniciais;
- baseline;
- endpoint de ingestão;
- segurança.

Arquivo principal:

```text
config/field_lubrication_config.json
```

Campos críticos:
- `aws.region = us-east-1`;
- `ingest_api.endpoint`;
- `outlets[*].gateway_tag_pressure`;
- `outlets[*].sensor_range_bar`;
- `outlets[*].physical_gauge_present`.
