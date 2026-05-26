# Troubleshooting - Grease Ingest

## Servico nao sobe

```bash
sudo systemctl status grease-ingest --no-pager
sudo journalctl -u grease-ingest -n 100 --no-pager
```

Causas comuns:

- `/opt/automacaoapi` nao existe ou nao esta atualizado.
- `.venv` ausente ou criado com Python errado.
- dependencias de `requirements_grease_api.txt` nao instaladas.
- `src/api/grease_ingest_api.py` ausente.
- `/opt/automacaoapi/.env` ausente.
- porta `8000` ja ocupada por outro servico.

Se o servico antigo ainda estiver usando a porta:

```bash
sudo systemctl stop automacaoapi-grease-api
sudo systemctl disable automacaoapi-grease-api
sudo systemctl restart grease-ingest
```

## Health local funciona, mas HTTPS nao

Verificar:

```bash
curl http://127.0.0.1:8000/grease/health
curl -H "Host: sentinelaindustrial.com.br" http://127.0.0.1/grease/health
sudo nginx -t
sudo systemctl status nginx --no-pager
```

Causas comuns:

- snippet `/etc/nginx/snippets/grease_ingest_location.conf` nao incluido no server block;
- Nginx nao recarregado;
- DNS apontando para outra EC2;
- certificado HTTPS ainda nao emitido ou expirado;
- Security Group sem porta `443`.

## Nao abrir porta 8000

A porta `8000` deve ficar privada:

```bash
sudo ss -ltnp | grep ':8000'
```

Esperado:

```text
127.0.0.1:8000
```

Se aparecer `0.0.0.0:8000`, revise o service file e troque o host do Uvicorn para `127.0.0.1`.

## Erro de credenciais AWS

Na EC2, use IAM Role. Nao configure chave AWS fixa no servidor.

Teste:

```bash
aws sts get-caller-identity
aws dynamodb describe-table --table-name grease_lubrication_state --region us-east-1
```

A role precisa acessar:

- `grease_lubrication_state`
- `grease_lubrication_cycles`
- `condition_alerts`

## ResourceNotFoundException

Confirmar tabelas em `us-east-1`:

```bash
aws dynamodb describe-table --table-name grease_lubrication_state --region us-east-1
aws dynamodb describe-table --table-name grease_lubrication_cycles --region us-east-1
aws dynamodb describe-table --table-name condition_alerts --region us-east-1
```

## Erro 401

Enviar token:

```text
X-API-Key: <GREASE_INGEST_TOKEN>
```

ou:

```text
Authorization: Bearer <GREASE_INGEST_TOKEN>
```

## Erro 422

Payload invalido. Conferir campos minimos:

```json
{
  "tenant_id": "cliente_demo",
  "plant_id": "lab_virtual",
  "asset_id": "sistema_lubrificacao_01",
  "source_id": "grease_gateway_01",
  "timestamp_utc": "2026-05-26T12:00:00Z",
  "cycle_id": "cycle_001",
  "metrics": {
    "pressure_saida_graxa_01_bar": 84.2,
    "peak_saida_graxa_01_bar": 103.3
  }
}
```

## Teste externo

No Windows:

```powershell
$env:GREASE_INGEST_TOKEN="<token_do_piloto>"
.\scripts\health_remote_grease_ingest.ps1
.\scripts\test_remote_grease_ingest.ps1
```
