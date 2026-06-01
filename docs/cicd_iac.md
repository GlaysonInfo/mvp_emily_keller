# CI/CD e IaC da Vitrine (S3 + CloudFront + WAF, deploy via OIDC)

Complementa `docs/implementacao_portal_acesso.md`. Entrega a publicação da
vitrine institucional com infraestrutura como código e deploy sem segredos de
longa duração (OIDC GitHub → AWS).

## Componentes

| Caminho | O que cria |
|---|---|
| `infra/site/` | S3 privado + CloudFront (OAC + URLs amigáveis) + WAF (rate limit + regras gerenciadas) |
| `infra/github-oidc/` | Provedor OIDC do GitHub + IAM Role mínimo para o deploy do site |
| `.github/workflows/deploy-site.yml` | Sincroniza `site/` no S3 e invalida o CloudFront |

## Ordem de execução (uma vez)

1. **Certificado ACM** (us-east-1, validado por DNS) para
   `sentinelaindustrial.com.br`. Guarde o ARN.

2. **Infra do site**:
   ```bash
   cd infra/site
   terraform init
   terraform apply \
     -var="site_bucket=sentinela-site-prod" \
     -var="domain=sentinelaindustrial.com.br" \
     -var="acm_certificate_arn=arn:aws:acm:us-east-1:<acct>:certificate/<id>"
   terraform output   # anote bucket_name, cloudfront_distribution_id, _arn, _domain
   ```
   Aponte o DNS do domínio (ALIAS/CNAME) para o `cloudfront_domain_name`.

3. **OIDC + role de deploy**:
   ```bash
   cd infra/github-oidc
   terraform init
   terraform apply \
     -var="github_owner=SEU_USUARIO_OU_ORG" \
     -var="github_repo=AutomacaoAPI" \
     -var="site_bucket=sentinela-site-prod" \
     -var="cloudfront_distribution_arn=<cloudfront_distribution_arn do passo 2>"
   terraform output deploy_role_arn
   ```

4. **Variáveis no GitHub** (Settings → Secrets and variables → Actions → Variables,
   no ambiente `production`):
   - `AWS_ROLE_ARN` = `deploy_role_arn`
   - `AWS_REGION` = `us-east-1`
   - `SITE_BUCKET` = `sentinela-site-prod`
   - `CF_DISTRIBUTION_ID` = `cloudfront_distribution_id`

5. **Proteção do ambiente** (recomendado): em Settings → Environments →
   `production`, exija *required reviewers* para aprovar cada deploy.

## Deploy

A cada push em `main` que toque `site/**`, o workflow assume o role via OIDC,
sincroniza o bucket e invalida o cache. Também roda manualmente
(*workflow_dispatch*).

## Notas de segurança

- Sem chaves AWS no repositório: a credencial é temporária (OIDC), restrita ao
  repositório (`repo:owner/repo:*`) e ao role de permissão mínima.
- O bucket é privado; só o CloudFront lê (OAC + bucket policy por `SourceArn`).
- O WAF aplica limite de taxa por IP e o conjunto comum de regras gerenciadas.
- A área `/acesso/` permanece `noindex`; a aplicação fica no subdomínio `app.`
  atrás do Cognito (ver guia do portal de acesso).

## Deploy do app (EC2 via SSM) — `deploy-app.yml`

Implanta as APIs de ingestão e o dashboard Streamlit na(s) instância(s) EC2 sem
SSH e sem segredos de longa duração: o GitHub Actions assume um role via OIDC e
dispara um comando SSM que roda `deploy/app/deploy_app.sh` na instância.

Componentes:

| Caminho | Função |
|---|---|
| `deploy/app/streamlit-dashboard.service` | unit systemd do dashboard (porta 8501, atrás do nginx) |
| `deploy/app/deploy_app.sh` | atualiza código (git reset ao SHA), reinstala deps e reinicia serviços + smoke test |
| `.github/workflows/deploy-app.yml` | OIDC → `ssm send-command` por tag, com poll de conclusão |
| `infra/github-oidc/app-deploy.tf` | role IAM mínimo (`ssm:SendCommand` no doc shell + instâncias com a tag `App`) |

Pré-requisitos na instância: repositório clonado em `/opt/automacaoapi`,
virtualenv em `.venv`, units instaladas (`grease-ingest`, `condition-ingest`,
`streamlit-dashboard`), SSM agent ativo e a tag `App=sentinela-production`
(ou `-staging`).

Mapeamento de ambientes:

| Branch | Ambiente | Tag de instância |
|---|---|---|
| `develop` | staging | `sentinela-staging` |
| `main` | production | `sentinela-production` |

Variáveis por ambiente (Settings → Environments → Variables): `AWS_ROLE_ARN`
(= `deploy_app_role_arn` do `infra/github-oidc`), `AWS_REGION`, `INSTANCE_TAG`.

> O **staging** deve ser isolado: instância própria, tabelas DynamoDB próprias
> (sufixo de ambiente) e `.env` próprio. Nunca aponte staging para os dados de
> produção.

## Evolução (prioridade menor)

- Migrar o proxy do app para **ALB + Cognito nativo** e ligar o mesmo WAF
  (o oauth2-proxy já cobre a necessidade atual).
- Seletor de tenant para o perfil Admin do Sistema na IHM.
