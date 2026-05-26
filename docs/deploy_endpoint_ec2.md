# Deploy do endpoint `/grease/ingest` na EC2

Este guia instala o endpoint de ingestao de ciclos de lubrificacao como servico fixo na EC2 do piloto.

Padrao do ambiente:

- EC2: `44.204.114.107`
- Usuario Linux: `ec2-user`
- Dominio publico: `https://sentinelaindustrial.com.br`
- API local: `http://127.0.0.1:8000`
- Endpoint publico: `https://sentinelaindustrial.com.br/grease/ingest`
- Health publico: `https://sentinelaindustrial.com.br/grease/health`
- Regiao AWS: `us-east-1`

Importante: nao liberar a porta `8000` publicamente. O Uvicorn deve ficar em `127.0.0.1:8000`, e o Nginx deve publicar apenas `/grease/` via HTTP/HTTPS.

## 1. Entrar na EC2

```bash
ssh ec2-user@44.204.114.107
```

Ou use o EC2 Instance Connect no console AWS.

## 2. Atualizar o repositorio

```bash
cd /opt/automacaoapi
git fetch origin sprint-5/dashboard-mvp
git pull --ff-only origin sprint-5/dashboard-mvp
```

## 3. Instalar o servico

```bash
cd /opt/automacaoapi
sudo bash deploy/install_grease_service.sh /opt/automacaoapi
```

O script:

- instala dependencias Python;
- atualiza `/opt/automacaoapi/.env`;
- cria token se `GREASE_INGEST_TOKEN` estiver vazio;
- instala o systemd service `grease-ingest`;
- para o servico antigo `automacaoapi-grease-api`, se existir;
- publica `/grease/` no Nginx;
- testa health local e via Nginx.

## 4. Verificar localmente na EC2

```bash
curl http://127.0.0.1:8000/grease/health
curl -H "Host: sentinelaindustrial.com.br" http://127.0.0.1/grease/health
sudo systemctl status grease-ingest --no-pager
```

## 5. Testar de fora da EC2

No Windows:

```powershell
.\scripts\health_remote_grease_ingest.ps1

$env:GREASE_INGEST_TOKEN="<token_do_piloto>"
.\scripts\test_remote_grease_ingest.ps1
```

Ou em Python:

```powershell
$env:GREASE_INGEST_TOKEN="<token_do_piloto>"
python scripts\test_remote_grease_ingest.py
```

Para ler o token na EC2:

```bash
sudo grep GREASE_INGEST_TOKEN /opt/automacaoapi/.env
```

## 6. Atualizar o servico depois de novos commits

```bash
cd /opt/automacaoapi
sudo bash deploy/update_grease_service.sh /opt/automacaoapi
```

## 7. Logs

```bash
sudo journalctl -u grease-ingest -f
```

## 8. Security Group

Manter liberado:

- `80/tcp` para HTTP ou redirecionamento;
- `443/tcp` para HTTPS;
- `22/tcp` somente para seu IP, se usar SSH.

Nao liberar:

- `8000/tcp`.

O gateway IO-Link deve enviar para `https://sentinelaindustrial.com.br/grease/ingest`, com o token no header `X-API-Key`.
