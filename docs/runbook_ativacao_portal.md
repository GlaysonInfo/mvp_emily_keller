# Runbook — Ativação do Portal de Acesso (Cognito + oauth2-proxy + RBAC)

Checklist operacional para **fechar o acesso público** e ativar o login por
perfil em produção. Execute na ordem. Cada passo tem um comando e uma
verificação. Marque as caixas conforme avança.

- **Objetivo:** sair de "app público sem login" para "app atrás de Cognito por perfil".
- **Tempo estimado:** 1–2 h (janela de manutenção curta).
- **Onde:** servidor EC2 (`/opt/automacaoapi`) + console/CLI AWS.
- **Pré-leitura:** `docs/implementacao_portal_acesso.md`.
- **Reversível:** sim — ver a seção *Rollback*.

> Convenções: `app.sentinelaindustrial.com.br` = subdomínio do app;
> serviços systemd: `grease-ingest`, `condition-ingest`, `streamlit-dashboard`,
> `oauth2-proxy`. Ajuste nomes/portas se o seu ambiente diferir.

---

## 0. Antes de começar (pré-requisitos)

- [ ] Janela de manutenção combinada (haverá breve indisponibilidade do app).
- [ ] **Snapshot/backup** da instância EC2 e cópia da config atual do nginx:
      `sudo cp -r /etc/nginx /etc/nginx.bak.$(date +%F)`
- [ ] `git pull` na instância para trazer este pacote (`deploy/auth`, `infra/cognito`, `src/dashboard/auth`).
- [ ] Acesso AWS com permissão em **Cognito**, **IAM** e (se usar Lambda de tenant) **Lambda**.
- [ ] Confirme o usuário/dono do código (`ec2-user`) e o caminho `/opt/automacaoapi`.

---

## 1. DNS e TLS do subdomínio do app

- [ ] Criar registro DNS de `app.sentinelaindustrial.com.br` apontando para a EC2
      (A para o IP elástico, ou CNAME conforme seu provedor de DNS).
- [ ] Emitir certificado TLS para o subdomínio (Let's Encrypt/certbot no nginx):
      ```bash
      sudo certbot --nginx -d app.sentinelaindustrial.com.br
      ```
- [ ] **Verificar:** `curl -I https://app.sentinelaindustrial.com.br` responde com TLS válido.

---

## 2. Criar o Cognito (User Pool, grupos, app client)

- [ ] Aplicar a IaC:
      ```bash
      cd /opt/automacaoapi/infra/cognito
      terraform init
      terraform apply \
        -var="region=us-east-1" \
        -var="app_domain=app.sentinelaindustrial.com.br" \
        -var="hosted_ui_domain_prefix=sentinela-industrial-login"
      ```
      (alternativa sem Terraform: `bash setup_cognito_cli.sh`)
- [ ] **Anotar os outputs** (vai usar no oauth2-proxy):
      ```bash
      terraform output oidc_issuer_url
      terraform output app_client_id
      terraform output -raw app_client_secret
      terraform output hosted_ui_domain
      ```
- [ ] No console do Cognito (App client), confira a **callback URL**:
      `https://app.sentinelaindustrial.com.br/oauth2/callback`.

### 2.1. Criar usuários de teste (um por perfil)

- [ ] Admin, Técnico e Operador, com o atributo de cliente (`custom:tenant_id`):
      ```bash
      POOL=<USER_POOL_ID>
      # Técnico do cliente_demo
      aws cognito-idp admin-create-user --user-pool-id $POOL \
        --username tecnico@cliente.com \
        --user-attributes Name=email,Value=tecnico@cliente.com Name=custom:tenant_id,Value=cliente_demo
      aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
        --username tecnico@cliente.com --group-name CLIENTE_TECNICO
      # Repita para operador@cliente.com (CLIENTE_OPERADOR),
      # admin.cliente@cliente.com (CLIENTE_ADMIN) e admin@suaempresa.com (ADMIN_SERVER)
      ```

### 2.2. Garantir o tenant do cliente (passo que exige atenção)

O isolamento por cliente depende de a aplicação saber o `tenant_id` do usuário.
Detalhes e comandos em **`docs/tenant_claim_setup.md`**. Escolha **uma**:

- [ ] **(Recomendada) Abordagem A — grupo `TENANT_<id>`.** Sem infra extra: crie
      o grupo do cliente e adicione o usuário a ele, além do grupo de perfil:
      ```bash
      POOL=<USER_POOL_ID>
      aws cognito-idp create-group --user-pool-id $POOL --group-name TENANT_cliente_demo
      aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
        --username tecnico@cliente.com --group-name TENANT_cliente_demo
      ```
- [ ] **Abordagem B — claim `tenant_id`.** Lambda Pre Token Generation
      (`infra/cognito/pre_token_generation_lambda.py`) + oauth2-proxy
      `--alpha-config` (`deploy/auth/oauth2-proxy.alpha.cfg.example`).

> Perfil **cliente** sem tenant é bloqueado pelo `resolve_tenant`. O **Admin**
> não precisa de tenant (opera cross-tenant).

---

## 3. Instalar e configurar o oauth2-proxy

- [ ] Baixar o binário para `/usr/local/bin/oauth2-proxy` (releases oficiais) e criar o usuário:
      ```bash
      sudo useradd -r -s /usr/sbin/nologin oauth2proxy
      sudo mkdir -p /etc/oauth2-proxy
      ```
- [ ] Gerar o cookie secret:
      ```bash
      openssl rand -base64 32 | tr -- '+/' '-_'
      ```
- [ ] Copiar e preencher a config:
      ```bash
      sudo cp /opt/automacaoapi/deploy/auth/oauth2-proxy.cfg.example /etc/oauth2-proxy/oauth2-proxy.cfg
      sudo nano /etc/oauth2-proxy/oauth2-proxy.cfg
      # preencher: oidc_issuer_url, client_id, client_secret, cookie_secret
      ```
- [ ] Instalar e iniciar o serviço:
      ```bash
      sudo cp /opt/automacaoapi/deploy/auth/oauth2-proxy.service /etc/systemd/system/
      sudo systemctl daemon-reload
      sudo systemctl enable --now oauth2-proxy
      ```
- [ ] **Verificar:** `sudo systemctl status oauth2-proxy` ativo e ouvindo em `127.0.0.1:4180`:
      `sudo ss -lntp | grep 4180`

---

## 4. nginx com auth_request (substitui a exposição pública)

- [ ] Editar o arquivo com seu `server_name` e caminhos de certificado:
      `/opt/automacaoapi/deploy/auth/nginx_app_auth.conf`
- [ ] Instalar a config (ajuste o destino conforme sua organização do nginx):
      ```bash
      sudo cp /opt/automacaoapi/deploy/auth/nginx_app_auth.conf /etc/nginx/conf.d/app_sentinela.conf
      sudo nginx -t && sudo systemctl reload nginx
      ```
- [ ] **Verificar:** acesso anônimo é redirecionado ao login do Cognito:
      `curl -sI https://app.sentinelaindustrial.com.br/ | grep -i location` (deve apontar para `/oauth2/start` ou o Cognito).

---

## 5. Ativar o RBAC no app + serviço do dashboard

- [ ] Atualizar `/opt/automacaoapi/.env`:
      ```ini
      AUTH_ENABLED=true
      AUTH_SIGNOUT_URL=https://app.sentinelaindustrial.com.br/oauth2/sign_out
      AUTH_LOGIN_URL=https://app.sentinelaindustrial.com.br/oauth2/start?rd=%2F
      INSTITUTIONAL_SITE_URL=https://sentinelaindustrial.com.br/
      GREASE_INGEST_TOKEN=<token forte>
      CONDITION_INGEST_TOKEN=<token forte>
      # opcional: GREASE_ALLOWED_SOURCE_IPS / CONDITION_ALLOWED_SOURCE_IPS
      ```
- [ ] Atualizar dependências (Streamlit ≥ 1.37 é necessário):
      ```bash
      sudo -u ec2-user /opt/automacaoapi/.venv/bin/pip install -r /opt/automacaoapi/requirements.txt
      ```
- [ ] Instalar/atualizar o serviço do dashboard (se ainda não existir):
      ```bash
      sudo cp /opt/automacaoapi/deploy/app/streamlit-dashboard.service /etc/systemd/system/
      sudo systemctl daemon-reload
      sudo systemctl enable --now streamlit-dashboard
      sudo systemctl restart grease-ingest condition-ingest
      ```
- [ ] Configurar o **mesmo token** no bridge/gateway (cabeçalho `X-API-Key`),
      senão a ingestão (agora fail-closed) responderá 401/503.

---

## 6. Validação (critério de aceite)

- [ ] **Anônimo bloqueado:** abrir `https://app.sentinelaindustrial.com.br/` em aba anônima → redireciona ao login (não abre o painel).
- [ ] **Operador:** loga e **não** vê "Configurações" nem "Configuração de Campo".
- [ ] **Técnico:** vê "Configuração de Campo", mas **não** "Configurações" global.
- [ ] **Admin:** vê todas as páginas.
- [ ] **Isolamento:** usuário do `cliente_demo` não vê dados de outro tenant.
- [ ] **Ingestão protegida:**
      ```bash
      curl -s -o /dev/null -w "%{http_code}\n" -X POST https://app.sentinelaindustrial.com.br/grease/ingest -d '{}'   # espera 401 ou 503
      ```
- [ ] **Logout:** o link "Sair" encerra a sessão.
- [ ] **Não indexável:** `curl -sI https://app.sentinelaindustrial.com.br/ | grep -i x-robots-tag` mostra `noindex`.

---

## 7. Encerramento

- [ ] Remover a mitigação temporária da Fase 0 (basic auth), se ainda estiver ativa.
- [ ] Acompanhar logs por alguns minutos:
      ```bash
      sudo journalctl -u oauth2-proxy -u streamlit-dashboard -f
      ```
- [ ] Registrar no controle de mudanças: data, responsável, versão do código (SHA).

---

## 8. Rollback (se algo falhar)

Reverter é rápido e seguro:

- [ ] Desligar o RBAC: no `.env`, `AUTH_ENABLED=false` e `sudo systemctl restart streamlit-dashboard`.
- [ ] Restaurar o acesso temporário protegido (Fase 0, basic auth) em vez do auth_request:
      ```bash
      sudo cp /opt/automacaoapi/deploy/auth/nginx_fase0_basic_auth.conf /etc/nginx/conf.d/app_sentinela.conf
      sudo nginx -t && sudo systemctl reload nginx
      sudo systemctl stop oauth2-proxy
      ```
- [ ] **Nunca** volte a expor o app sem nenhuma proteção — mantenha pelo menos a Fase 0.

---

## 9. Resumo de variáveis e portas

| Item | Valor |
|---|---|
| Dashboard (Streamlit) | `127.0.0.1:8501` (atrás do nginx) |
| API graxa | `127.0.0.1:8000` |
| API condição | `127.0.0.1:8001` |
| oauth2-proxy | `127.0.0.1:4180` |
| `.env` chaves | `AUTH_ENABLED`, `AUTH_LOGIN_URL`, `AUTH_SIGNOUT_URL`, `INSTITUTIONAL_SITE_URL`, `GREASE_INGEST_TOKEN`, `CONDITION_INGEST_TOKEN`, `ADMIN_TENANTS` (opcional) |
| `ADMIN_TENANTS` | Lista (vírgula) de clientes que o Admin pode visualizar no seletor da IHM |
| Grupos Cognito | `ADMIN_SERVER`, `CLIENTE_ADMIN`, `CLIENTE_TECNICO`, `CLIENTE_OPERADOR` |
| Atributo tenant | `custom:tenant_id` → cabeçalho `X-Forwarded-Tenant` |
