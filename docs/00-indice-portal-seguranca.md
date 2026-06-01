# Índice — Portal de Acesso Seguro, Vitrine e Operação

Mapa de tudo que foi entregue para fechar o acesso público da aplicação e
publicar a vitrine institucional, com a ordem de execução. Os detalhes de cada
frente estão nos documentos referenciados.

## 1. Visão geral

Ponto de partida (avaliação técnica): a aplicação estava **pública sem
autenticação**. A solução separa três camadas — **vitrine** (pública,
indexável), **app autenticado** por perfil (Cognito) e **ingestão** protegida
por token — e adiciona RBAC, isolamento por cliente (tenant), CI/CD e auditoria.

Documentos de contexto (na raiz do repositório):
`Avaliacao_Tecnica_Sentinela_Industrial_v2.docx` e
`Plano_Proximo_Passo_Sentinela_Industrial.docx`.

## 2. Mapa de entregáveis

### Aplicação (RBAC, identidade, auditoria)
| Arquivo | Função |
|---|---|
| `src/dashboard/auth/identity.py` | Resolve a identidade (modo `proxy` e `alb`), perfil e tenant (cabeçalho ou grupo `TENANT_`) |
| `src/dashboard/auth/rbac.py` | Perfis, páginas e capacidades; `normalize_role` |
| `src/dashboard/auth/guard.py` | Login obrigatório, bloqueio de página, badge e seletor de tenant do Admin |
| `src/dashboard/auth/audit.py` | Trilha de auditoria (DynamoDB + fallback arquivo) |
| `src/dashboard/app.py` | Integra o guard e a auditoria (inerte enquanto `AUTH_ENABLED!=true`) |
| `src/api/*_security_middleware.py` | Ingestão fail-closed (token obrigatório + comparação constante) |
| `src/dashboard/config_ui.py`, `lubrication_field/field_config_store.py` | Emitem eventos de auditoria nas gravações |

### Deploy na instância
| Arquivo | Função |
|---|---|
| `deploy/auth/nginx_fase0_basic_auth.conf` | Mitigação imediata (basic auth / IP allowlist) |
| `deploy/auth/nginx_app_auth.conf` | nginx + oauth2-proxy (modo proxy) |
| `deploy/auth/nginx_app_alb.conf` | nginx para o modo ALB (sem oauth2-proxy) |
| `deploy/auth/oauth2-proxy.cfg.example` / `.alpha.cfg.example` / `.service` | Config/serviço do oauth2-proxy |
| `deploy/app/streamlit-dashboard.service` | Serviço systemd do dashboard |
| `deploy/app/deploy_app.sh` | Deploy na instância (via SSM) |

### Infraestrutura (Terraform / CLI)
| Caminho | Função |
|---|---|
| `infra/cognito/` | User Pool, grupos, `custom:tenant_id`, app client, domínio; Lambda Pre Token Generation |
| `infra/alb/` | ALB + `authenticate-cognito`, target group (nginx), rotas de ingestão sem auth, SGs |
| `infra/site/` | S3 + CloudFront (OAC, URLs amigáveis) + WAF |
| `infra/github-oidc/` | Provedor OIDC do GitHub + roles de deploy (site e app) |
| `infra/aws-cli/18-create-audit-log-dynamodb.sh` | Tabela DynamoDB de auditoria |

### Vitrine e CI/CD
| Caminho | Função |
|---|---|
| `site/` | Site institucional estático (Home, produto, como funciona, demo, acesso) + SEO |
| `.github/workflows/deploy-site.yml` | Publica a vitrine (S3 + CloudFront) via OIDC |
| `.github/workflows/deploy-app.yml` | Implanta o app na EC2 via SSM (staging/produção) |

### Documentação detalhada
| Documento | Assunto |
|---|---|
| `docs/implementacao_portal_acesso.md` | Visão completa do portal e estrutura de pastas |
| `docs/runbook_ativacao_portal.md` | Checklist operacional de ativação no servidor |
| `docs/tenant_claim_setup.md` | Isolamento por cliente (grupo `TENANT_` ou claim) |
| `docs/migracao_alb_cognito.md` | Migração do oauth2-proxy para ALB nativo |
| `docs/cicd_iac.md` | CI/CD e IaC (site e app) |
| `docs/auditoria.md` | Trilha de auditoria |

## 3. Ordem de execução recomendada

1. **Fase 0 — mitigação imediata** (não esperar o resto): tokens de ingestão
   obrigatórios no `.env` e `nginx_fase0_basic_auth.conf`. Fecha o acesso anônimo hoje.
2. **Cognito**: `infra/cognito` (User Pool, grupos, app client, domínio).
3. **Tenant**: criar grupos `TENANT_<id>` e associar usuários
   (`docs/tenant_claim_setup.md`, Abordagem A).
4. **Ativar o portal** — escolha um:
   - **oauth2-proxy** (rápido, sobre o que já existe): `docs/runbook_ativacao_portal.md`; ou
   - **ALB + Cognito nativo** (alvo recomendado): `docs/migracao_alb_cognito.md` + `infra/alb`.
   Em ambos: `.env` com `AUTH_ENABLED=true` (e `AUTH_PROVIDER=alb` no caso ALB).
5. **Deploy do app** (opcional, repetível): `infra/github-oidc` + `deploy-app.yml`.
6. **Vitrine**: ACM (us-east-1) → `infra/site` → variáveis no GitHub → `deploy-site.yml`.
7. **Auditoria**: `infra/aws-cli/18-create-audit-log-dynamodb.sh` + `AUDIT_LOG_TABLE` no `.env`.

## 4. Variáveis de ambiente (resumo)

| Variável | Uso |
|---|---|
| `AUTH_ENABLED` | Liga o RBAC na IHM (`true`/`false`) |
| `AUTH_PROVIDER` | `proxy` (oauth2-proxy) ou `alb` (ALB nativo) |
| `AUTH_SIGNOUT_URL` | URL de logout (modo proxy) |
| `AUTH_TENANT_GROUP_PREFIX` | Prefixo do grupo de tenant (padrão `TENANT_`) |
| `ADMIN_TENANTS` | Clientes que o Admin pode escolher no seletor |
| `GREASE_INGEST_TOKEN`, `CONDITION_INGEST_TOKEN` | Tokens de ingestão (obrigatórios) |
| `GREASE_REQUIRE_TOKEN`, `CONDITION_REQUIRE_TOKEN` | `false` só para lab/dev/testes |
| `AUDIT_LOG_TABLE`, `AUDIT_LOG_FILE` | Destino da trilha de auditoria |

## 5. Pré-requisitos e dependência

- **Streamlit ≥ 1.37** (já fixado em `requirements.txt`/`pyproject.toml`) para
  `st.context.headers`.
- Testes/CI de ingestão: definir os tokens ou `*_REQUIRE_TOKEN=false`.

## 6. Status de verificação

Verificado neste ambiente: lógica de RBAC, tenant, identidade ALB e auditoria
(testes isolados), sintaxe Python/YAML/shell. **A executar no seu ambiente**:
`terraform init/validate/apply` (não há Terraform/rede no sandbox) e os passos
operacionais na EC2/Cognito/AWS conforme os runbooks.
