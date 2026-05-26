# Checklist de Teste do Gateway de Equipamentos

## Pré-requisitos

- [ ] Serviço `condition-ingest` ativo na EC2.
- [ ] Health público responde em `/condition/health`.
- [ ] Token `CONDITION_INGEST_TOKEN` configurado.
- [ ] Tabelas DynamoDB existentes: `mvp_asset_state_dev`, `condition_history`, `condition_alerts`.
- [ ] Gateway/edge com acesso HTTPS de saída para `sentinelaindustrial.com.br`.

## Teste local na EC2

```bash
curl http://127.0.0.1:8001/condition/health

TOKEN="$(sudo grep '^CONDITION_INGEST_TOKEN=' /opt/automacaoapi/.env | tail -1 | cut -d= -f2-)"

CONDITION_INGEST_ENDPOINT="http://127.0.0.1:8001/condition/ingest" \
CONDITION_INGEST_TOKEN="$TOKEN" \
/opt/automacaoapi/.venv/bin/python /opt/automacaoapi/scripts/test_condition_ingest.py
```

## Teste público

```bash
curl https://sentinelaindustrial.com.br/condition/health
```

```powershell
$env:CONDITION_INGEST_TOKEN="token_do_piloto"
python scripts\test_remote_condition_ingest.py
```

## Critérios de sucesso

- [ ] POST retorna HTTP 200.
- [ ] Resposta mostra `saved_state=true`.
- [ ] Resposta mostra `saved_history=true`.
- [ ] Resposta mostra `saved_alerts=true`.
- [ ] Ativo aparece no Painel da Planta.
- [ ] Detalhe do Ativo mostra métricas atualizadas.
- [ ] Histórico aparece em Relatórios/Inteligência.
- [ ] Alertas aparecem em Alertas e Eventos quando as regras disparam.

## Mapeamento de campo

| Sinal físico | Métrica enviada |
|---|---|
| Rotação | `rpm` |
| Vibração RMS | `vibration_rms_mm_s` |
| Pico de vibração | `vibration_peak_g` |
| Temperatura | `temperature_c` |
| Ultrassom | `ultrasound_db` |
| Kurtosis | `kurtosis` |
| Crest factor | `crest_factor` |
| Saúde calculada no edge | `health_score` |
| Gravidade calculada no edge | `severity_score` |
