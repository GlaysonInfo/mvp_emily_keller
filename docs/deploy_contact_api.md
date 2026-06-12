# API de contato do site institucional

## Objetivo

O formulário das páginas `/demonstracao/` e `/contato/` envia a solicitação para
`POST /contact/submit`. O serviço FastAPI valida o conteúdo, aplica proteção
antispam e limite de requisições e encaminha a mensagem pelo Amazon SES.

O navegador não recebe credenciais AWS e não precisa abrir um aplicativo de
e-mail. A confirmação do envio aparece na própria página.

## Pré-requisitos no Amazon SES

1. Use a região configurada na aplicação, atualmente `us-east-1`.
2. Verifique no SES o domínio ou endereço definido em `CONTACT_FROM_EMAIL`.
3. Publique no DNS os registros DKIM apresentados pelo SES.
4. Enquanto a conta estiver no sandbox do SES, verifique também
   `suporte@meuprompt.net`.
5. Antes da abertura comercial, solicite ao SES a saída do sandbox.

O endereço recomendado para o primeiro deploy é:

```text
CONTACT_FROM_EMAIL=suporte@meuprompt.net
CONTACT_TO_EMAIL=suporte@meuprompt.net
```

## Permissão da role EC2

A role `AutomacaoApiEC2Role` precisa enviar mensagens pelo SES. Em uma sessão
com permissão IAM:

```bash
cd /opt/automacaoapi

aws iam put-role-policy \
  --role-name AutomacaoApiEC2Role \
  --policy-name SentinelaInstitutionalContactSes \
  --policy-document file://deploy/contact-api-iam-policy.json
```

Não grave `AWS_ACCESS_KEY_ID` ou `AWS_SECRET_ACCESS_KEY` no `.env`.

## Configuração na EC2

Adicione ao `/opt/automacaoapi/.env`:

```dotenv
CONTACT_FROM_EMAIL=suporte@meuprompt.net
CONTACT_TO_EMAIL=suporte@meuprompt.net
CONTACT_ALLOWED_ORIGINS=https://sentinelaindustrial.com.br,https://www.sentinelaindustrial.com.br
CONTACT_RATE_LIMIT=5
CONTACT_RATE_WINDOW_SECONDS=900
```

Instale e inicie o serviço:

```bash
cd /opt/automacaoapi
source .venv/bin/activate
python -m pip install -r requirements_contact_api.txt

sudo cp deploy/contact-api.service /etc/systemd/system/contact-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now contact-api

curl http://127.0.0.1:8002/contact/health
sudo systemctl status contact-api --no-pager
```

## Nginx

O template `deploy/nginx_institutional_site.conf` já contém a rota. Se a
configuração ativa for mantida manualmente, copie o conteúdo de
`deploy/nginx_contact_api.conf` para dentro do bloco HTTPS de
`sentinelaindustrial.com.br`, antes de `location /`.

Depois:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl https://sentinelaindustrial.com.br/contact/health
```

## Teste funcional

Envie uma solicitação pela página:

```text
https://sentinelaindustrial.com.br/demonstracao/
```

Confirme:

1. O botão muda para `Enviando...`.
2. A página apresenta a confirmação de envio.
3. A mensagem chega em `suporte@meuprompt.net`.
4. Responder à mensagem usa o e-mail corporativo informado pelo visitante.

Logs:

```bash
sudo journalctl -u contact-api -n 100 --no-pager
```
