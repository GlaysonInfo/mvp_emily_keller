# Implementação do Portal de Acesso Seguro + Vitrine

Guia de implementação do **próximo passo** do MVP: fechar o acesso à aplicação
(risco crítico nº 1) e publicar a vitrine institucional indexável, sobre a
mesma base de identidade (AWS Cognito).

Este pacote já foi **escrito no repositório** e está pronto para configurar e
ativar. O controle de acesso na IHM fica **inerte** até você definir
`AUTH_ENABLED=true`, então nada do comportamento atual muda antes da hora.

---

## 0. Estratégia adotada (reconciliação das análises)

Foram avaliados: a Avaliação Técnica (v2), o Plano do Próximo Passo e o
relatório de pesquisa (`deep-research-report_final.md` / "Plano de site
institucional primeiro passo.docx"). Todos convergem para a **separação em três
camadas**: vitrine pública indexável, aplicação autenticada por perfil e
ingestão protegida. Decisões escolhidas (a melhor combinação descrita):

| Tema | Decisão adotada | Origem |
|---|---|---|
| Separação de camadas | Vitrine (raiz) + app (`app.`) + API protegida | consenso |
| Identidade | **AWS Cognito**, Authorization Code + **PKCE** | pesquisa + plano |
| Proxy de auth (agora) | **oauth2-proxy + nginx** no EC2 atual (baixa fricção) | "implementar no que já existe" |
| Proxy de auth (evolução) | ALB + Cognito nativo + WAF | pesquisa |
| Vitrine | Site **estático** (S3 + CloudFront) | pesquisa |
| Perfis | `ADMIN_SERVER`, `CLIENTE_TECNICO`, `CLIENTE_OPERADOR` | consenso |
| Ingestão | Token **obrigatório** (fail-closed) + allowlist | consenso |

> **Nota importante de reconciliação.** O relatório de pesquisa lista caminhos
> de código como `api/server.py`, `middleware/collector.py`,
> `pages/9_HMI_Operador.py`, `middleware/emily_keller.service`. **Esses caminhos
> não correspondem ao repositório real**, que usa `src/dashboard/app.py`,
> `src/api/grease_ingest_api.py`, `src/api/condition_ingest_api.py`,
> `src/edge/...` e serviços `deploy/grease-ingest.service` /
> `deploy/condition-ingest.service`. **Todo este pacote foi construído contra a
> estrutura real**, validada por leitura do código.

---

## 1. Estrutura de pastas (o que foi criado)

```
AutomacaoAPI/
├─ src/
│  ├─ api/
│  │  ├─ grease_security_middleware.py      # [ALTERADO] token obrigatório + compare_digest
│  │  └─ condition_security_middleware.py   # [ALTERADO] token obrigatório + compare_digest
│  └─ dashboard/
│     ├─ app.py                             # [ALTERADO] chama o guard de RBAC (inerte por padrão)
│     └─ auth/                              # [NOVO] camada de autenticação/RBAC da IHM
│        ├─ __init__.py
│        ├─ identity.py                     # lê identidade dos cabeçalhos do proxy
│        ├─ rbac.py                         # perfis, páginas e capacidades
│        └─ guard.py                        # helpers Streamlit (login, tenant, bloqueio de página)
├─ deploy/
│  └─ auth/                                 # [NOVO] proxy de autenticação
│     ├─ nginx_fase0_basic_auth.conf        # mitigação imediata (basic auth / IP allowlist)
│     ├─ nginx_app_auth.conf                # nginx + auth_request (Fase 1)
│     ├─ oauth2-proxy.cfg.example           # config do oauth2-proxy (Cognito OIDC + PKCE)
│     └─ oauth2-proxy.service               # unit systemd do oauth2-proxy
├─ infra/
│  └─ cognito/                              # [NOVO] IaC do Cognito
│     ├─ main.tf                            # user pool, grupos, atributo tenant, app client, domínio
│     ├─ variables.tf
│     ├─ outputs.tf
│     └─ setup_cognito_cli.sh               # alternativa via AWS CLI
├─ site/                                    # [NOVO] vitrine institucional estática
│  ├─ index.html                            # Home
│  ├─ sistema-de-lubrificacao/index.html    # Produto
│  ├─ como-funciona/index.html
│  ├─ demonstracao/index.html               # captura de lead (CRM/webhook a ligar)
│  ├─ acesso/index.html                     # hub de login por perfil (noindex)
│  ├─ assets/styles.css
│  ├─ robots.txt
│  ├─ sitemap.xml
│  └─ README.md                             # mapa de páginas restantes + deploy + SEO
└─ docs/
   └─ implementacao_portal_acesso.md        # este guia
```

---

## 2. FASE 0 — Mitigação imediata (hoje)

Objetivo: tirar a aplicação da exposição pública e tornar a ingestão obrigatória,
**antes** de ter o Cognito pronto.

### 2.1. Token de ingestão obrigatório (já no código)

Os middlewares agora **falham fechado**: sem `*_INGEST_TOKEN` configurado, a
ingestão responde `503`. Defina os tokens no `.env` do servidor:

```bash
# /opt/automacaoapi/.env
GREASE_INGEST_TOKEN=$(openssl rand -hex 32)
CONDITION_INGEST_TOKEN=$(openssl rand -hex 32)
# opcional: restrinja a origem do gateway
GREASE_ALLOWED_SOURCE_IPS=203.0.113.10
CONDITION_ALLOWED_SOURCE_IPS=203.0.113.10
# opcional: libere CORS apenas para frontends conhecidos; vazio desabilita CORS
GREASE_ALLOWED_ORIGINS=https://app.sentinelaindustrial.com.br
CONDITION_ALLOWED_ORIGINS=https://app.sentinelaindustrial.com.br
```

E configure o **mesmo token** no bridge/gateway (cabeçalho `X-API-Key` ou
`Authorization: Bearer`).

> Para laboratório/dev sem token, é possível desligar com
> `GREASE_REQUIRE_TOKEN=false` / `CONDITION_REQUIRE_TOKEN=false`.
> **Não use isso em produção.**

### 2.2. Aplicação atrás de autenticação no proxy

Enquanto o Cognito não está no ar, proteja o Streamlit com autenticação básica
(ou allowlist de IP) — ver `deploy/auth/nginx_fase0_basic_auth.conf`:

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd_sentinela admin
# inclua o server block do arquivo, ajuste o server_name e:
sudo nginx -t && sudo systemctl reload nginx
```

Isso já fecha o acesso anônimo à página **Configurações** e a todo o app.

Os snippets NGINX de ingestão também devem sobrescrever
`X-Trusted-Client-IP` com `$remote_addr`. A API usa esse cabeçalho interno para
allowlist e não confia em `X-Forwarded-For` por padrão.

---

## 3. FASE 1 — Cognito + oauth2-proxy + RBAC

### 3.1. Domínios

- `sentinelaindustrial.com.br` → vitrine (S3 + CloudFront)
- `app.sentinelaindustrial.com.br` → aplicação (EC2/nginx, atrás do proxy)

### 3.2. Criar o Cognito (Terraform)

```bash
cd infra/cognito
terraform init
terraform apply -var="region=us-east-1" \
  -var="app_domain=app.sentinelaindustrial.com.br" \
  -var="hosted_ui_domain_prefix=sentinela-industrial-login"
# anote os outputs: oidc_issuer_url, app_client_id, app_client_secret, hosted_ui_domain
terraform output -raw app_client_secret
```

(ou use `bash infra/cognito/setup_cognito_cli.sh` se preferir AWS CLI.)

### 3.3. Instalar e configurar o oauth2-proxy

```bash
# baixe o binário em /usr/local/bin/oauth2-proxy (releases oficiais)
sudo useradd -r -s /usr/sbin/nologin oauth2proxy
sudo mkdir -p /etc/oauth2-proxy
sudo cp deploy/auth/oauth2-proxy.cfg.example /etc/oauth2-proxy/oauth2-proxy.cfg
# preencha oidc_issuer_url, client_id, client_secret e gere o cookie_secret:
openssl rand -base64 32 | tr -- '+/' '-_'
sudo cp deploy/auth/oauth2-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now oauth2-proxy
```

### 3.4. nginx com auth_request

Substitua a config da Fase 0 por `deploy/auth/nginx_app_auth.conf` (ajuste
`server_name` e os caminhos de certificado). Esse arquivo valida cada requisição
no oauth2-proxy e **injeta** os cabeçalhos de identidade
(`X-Forwarded-Email/User/Groups/Tenant`), sobrescrevendo qualquer valor enviado
pelo cliente. Depois: `sudo nginx -t && sudo systemctl reload nginx`.

### 3.5. Ativar o RBAC na aplicação

No `.env` do app (serviço do Streamlit):

```bash
AUTH_ENABLED=true
AUTH_SIGNOUT_URL=/oauth2/sign_out
# (opcional) nomes de cabeçalho, se mudar no nginx:
# AUTH_HEADER_EMAIL=x-forwarded-email
# AUTH_HEADER_GROUPS=x-forwarded-groups
# AUTH_HEADER_TENANT=x-forwarded-tenant
```

Requer **Streamlit >= 1.37** (para `st.context.headers`). Ajuste o
`requirements.txt` / `pyproject.toml` de `streamlit>=1.36` para `>=1.37`.

Com `AUTH_ENABLED=true`, o `app.py` passa a:
1. exigir login válido (`enforce_authentication`);
2. resolver o tenant pela identidade (`resolve_tenant`) — isolando o cliente;
3. exibir o usuário/perfil na barra lateral e **bloquear páginas fora do perfil**
   (`enforce_page_access`).

4. registrar ações sensíveis em trilha de auditoria quando `AUDIT_LOG_TABLE`
   ou `AUDIT_LOG_FILE` estiver configurado.

Auditoria local/produção:

```bash
# Produção: DynamoDB
AUDIT_LOG_TABLE=audit_log

# Fallback local ou contingência
AUDIT_LOG_FILE=logs/audit.log
```

### 3.6. Tenant (atributo `custom:tenant_id`)

O isolamento por cliente depende de o tenant chegar como cabeçalho
`X-Forwarded-Tenant`. Duas formas:

- **(a)** oauth2-proxy (v7+) com config alpha `injectRequestHeaders` mapeando o
  claim `custom:tenant_id` → `X-Auth-Request-Tenant`; ou
- **(b)** uma **Lambda de Pre Token Generation** no Cognito que copie
  `custom:tenant_id` para um claim repassável.

Ao criar cada usuário, defina o atributo:

```bash
aws cognito-idp admin-update-user-attributes --user-pool-id <POOL_ID> \
  --username tecnico@cliente.com \
  --user-attributes Name=custom:tenant_id,Value=cliente_demo
```

### 3.7. Criar usuários de teste

```bash
POOL=<POOL_ID>
aws cognito-idp admin-create-user --user-pool-id $POOL \
  --username tecnico@cliente.com \
  --user-attributes Name=email,Value=tecnico@cliente.com Name=custom:tenant_id,Value=cliente_demo
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
  --username tecnico@cliente.com --group-name CLIENTE_TECNICO
```

> **Teste local sem proxy:** defina
> `AUTH_DEV_IDENTITY='{"email":"tec@x.com","groups":["CLIENTE_TECNICO"],"tenant_id":"cliente_demo"}'`
> e `AUTH_ENABLED=true` para simular um usuário logado.

---

## 4. Vitrine estática (S3 + CloudFront)

Os arquivos estão em `site/`. Deploy resumido (ver `site/README.md`):

```bash
aws s3 sync site/ s3://SEU-BUCKET-DO-SITE/ --delete
# CloudFront na frente, certificado ACM em us-east-1, invalidar cache no deploy
```

SEO já incluso: `robots.txt`, `sitemap.xml`, `canonical`, Open Graph e
JSON-LD (`Organization`, `WebSite`, `SoftwareApplication`, `BreadcrumbList`).
Cadastre o domínio no **Google Search Console** e ligue o **GA4** (placeholder
comentado no `index.html`). A área `/acesso/` é `noindex`.

---

## 5. Impacto em testes / CI (atenção)

Como a ingestão agora é fail-closed, os testes que chamam os endpoints sem token
podem falhar. No ambiente de teste/CI, defina o token **ou** desligue a
exigência:

```bash
export GREASE_REQUIRE_TOKEN=false
export CONDITION_REQUIRE_TOKEN=false
```

(ou exporte `GREASE_INGEST_TOKEN`/`CONDITION_INGEST_TOKEN` com um valor de teste).

---

## 6. Checklist de aceite

- [ ] App não abre sem login (sessão anônima é redirecionada ao Cognito).
- [ ] Operador não vê "Configurações" nem "Configuração de Campo".
- [ ] Técnico vê configuração de campo, mas não "Configurações" global.
- [ ] Admin vê tudo; consegue operar em qualquer tenant.
- [ ] Cliente A não enxerga dados do cliente B (isolamento por tenant).
- [ ] `/grease/ingest` e `/condition/ingest` exigem token (401/503 sem ele).
- [ ] Vitrine pública indexável; `/acesso/` com `noindex`.
- [ ] Sitemap submetido no Search Console; GA4 ativo.

---

## 7. Evolução (depois do MVP seguro)

1. Migrar oauth2-proxy → **ALB + Cognito nativo** + **AWS WAF** (rate limiting).
2. **CI/CD** GitHub Actions com **OIDC para AWS** (sem segredos longos),
   ambientes `staging` e `production`.
3. **IaC** completa (S3/CloudFront/ACM/ALB/EC2/SG/DynamoDB/CloudWatch).
4. Aplicar o filtro de **tenant nas consultas** dos repositórios DynamoDB
   (usar o `tenant_id` resolvido pela identidade, não o do `.env`).
5. **Trilha de auditoria** por usuário/tenant; políticas **LGPD** (privacidade,
   cookies, termos, encarregado/DPO, plano de incidente).
6. Modularização dos serviços conforme a Avaliação Técnica.
