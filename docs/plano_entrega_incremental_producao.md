# Plano de entrega incremental para maturidade de produção

Este plano cruza o MVP implementado no repositório com as recomendações da
`Avaliacao_Tecnica_Sentinela_Industrial_v2.docx`, do
`deep-research-report_final.md` e do plano de site institucional. O objetivo é
entregar melhorias reais no sistema, em lotes pequenos, sem exigir reescrita nem
commit no Git neste momento.

## 1. Leitura do estado atual

### Já implementado no MVP

- Simulador OPC UA, bridge local MQTT/HTTPS, Lambda de ingestão, regras de
  diagnóstico, dashboard Streamlit, APIs FastAPI de condição e lubrificação,
  módulos de lubrificação de campo, HMI Operador/Técnico, relatórios,
  escalonamento e outbox.
- Site institucional estático em `site/`, com `robots.txt`, `sitemap.xml`,
  páginas de produto, funcionamento, demonstração e acesso.
- Pacote inicial de autenticação/RBAC em `src/dashboard/auth/`.
- `AUTH_ENABLED=false` por padrão, mantendo o comportamento atual até ativação.
- Middlewares de ingestão com token obrigatório por padrão, escape explícito
  apenas para laboratório: `GREASE_REQUIRE_TOKEN=false` e
  `CONDITION_REQUIRE_TOKEN=false`.
- Comparação de token com `hmac.compare_digest`.
- Infra/documentação inicial para Cognito, oauth2-proxy, NGINX, ALB, site,
  GitHub OIDC e ambiente local via Makefile.
- Testes cobrindo RBAC, identidade dev, fail-closed e ingestão das APIs.

### Ainda parcial ou pendente

- CORS das APIs segue permissivo (`allow_origins=["*"]`,
  `allow_credentials=True`). **Atualização:** APIs passaram a usar
  `GREASE_ALLOWED_ORIGINS`, `CONDITION_ALLOWED_ORIGINS` ou `ALLOWED_ORIGINS`,
  com lista vazia por padrão.
- Allowlist de IP ainda usa `X-Forwarded-For`; precisa ser tratada como dado
  confiável somente depois do proxy sobrescrever cabeçalhos. **Atualização:**
  middlewares passaram a preferir `X-Trusted-Client-IP`, preenchido pelo NGINX,
  e `X-Forwarded-For` só é aceito com opt-in de laboratório.
- RBAC existe no app, mas precisa ser ativado e validado em staging/produção.
- Auditoria existe como helper, mas ainda deve ser chamada nos pontos sensíveis
  de alteração: configuração, campo, escalonamento, alertas e testes ponta a
  ponta.
- `list_alerts` e `list_current_states` ainda usam `scan`; aceitável no MVP,
  mas não é bom para produção.
- App Streamlit continua centralizado em `src/dashboard/app.py`; os módulos
  estão separados, mas a orquestração ainda é monolítica.
- WAF/rate limit/CloudWatch alarms ainda são implantação/infra, não comportamento
  validado end-to-end.
- CI/CD e IaC existem como base, mas precisam virar esteira operacional com
  ambientes, secrets e smoke tests.

## 2. Princípio de entrega

Cada incremento deve:

1. Alterar poucos arquivos.
2. Ter teste local ou checklist de validação.
3. Preservar o fluxo local/demo.
4. Ficar desligável por variável de ambiente quando houver risco operacional.
5. Não misturar site público, app autenticado e ingestão de campo.
6. Encerrar com `python -m unittest discover -s tests` antes de qualquer
   publicação.

Comandos padrão no PowerShell:

```powershell
$env:PYTHONPATH='src;.'
python -m unittest discover -s tests
```

Para fluxo local completo, usar Git Bash/WSL/MSYS2:

```bash
make local-check
make local-up
make local-status
make local-down
```

## 3. Incremento 0 - congelar baseline local sem commit

Objetivo: saber exatamente o que está sendo entregue, sem publicar nada.

Arquivos envolvidos:

- `AGENTS.md`
- `README.md`
- `Makefile`
- `docs/implementacao_portal_acesso.md`
- `docs/plano_entrega_incremental_producao.md`

Passos:

1. Rodar `git status --short` e guardar a lista de arquivos modificados.
2. Rodar testes unitários completos com `PYTHONPATH=src:.`.
3. Rodar `python -m compileall src tests`.
4. Rodar `python leak_scanner.py`, se o script continuar alinhado ao padrão
   atual.
5. Não commitar; apenas registrar resultado no fim deste documento ou em nota de
   execução.

Critério de aceite:

- Testes passam ou falhas ficam classificadas entre dependência ausente,
  ambiente local ou regressão real.
- Nenhum segredo aparece em arquivos versionáveis.

## 4. Incremento 1 - ativação segura do acesso ao app

Objetivo: transformar o RBAC já implementado em proteção real, primeiro em
staging.

Arquivos principais:

- `src/dashboard/app.py`
- `src/dashboard/auth/identity.py`
- `src/dashboard/auth/rbac.py`
- `src/dashboard/auth/guard.py`
- `src/dashboard/auth/audit.py`
- `deploy/auth/nginx_fase0_basic_auth.conf`
- `deploy/auth/nginx_app_auth.conf`
- `deploy/auth/oauth2-proxy.cfg.example`
- `deploy/auth/oauth2-proxy.service`
- `infra/cognito/*`
- `docs/implementacao_portal_acesso.md`
- `tests/test_dashboard_auth.py`

Entrega 1A - mitigação imediata:

1. No servidor, proteger `app.sentinelaindustrial.com.br` com Basic Auth ou
   allowlist usando `deploy/auth/nginx_fase0_basic_auth.conf`.
2. Confirmar que visitante anônimo não abre o Streamlit.
3. Manter `AUTH_ENABLED=false` até a etapa Cognito estar pronta.

Entrega 1B - Cognito + oauth2-proxy:

1. Criar User Pool Cognito e grupos `ADMIN_SERVER`, `CLIENTE_TECNICO`,
   `CLIENTE_OPERADOR`.
2. Configurar app client com Authorization Code + PKCE.
3. Instalar `oauth2-proxy` na EC2.
4. Aplicar `deploy/auth/nginx_app_auth.conf`, garantindo que o NGINX sobrescreve
   `X-Forwarded-Email`, `X-Forwarded-Groups` e `X-Forwarded-Tenant`.
5. Definir no serviço Streamlit:

```bash
AUTH_ENABLED=true
AUTH_SIGNOUT_URL=/oauth2/sign_out
```

6. Criar três usuários de teste, um por perfil.

Validação local sem proxy:

```powershell
$env:AUTH_ENABLED='true'
$env:AUTH_DEV_IDENTITY='{"email":"tec@cliente.com","groups":["CLIENTE_TECNICO","TENANT_cliente_demo"]}'
$env:PYTHONPATH='src;.'
python -m unittest tests.test_dashboard_auth
```

Critério de aceite:

- Usuário anônimo não acessa o app.
- Operador não acessa `Configurações`, `Teste ponta a ponta`,
  `Configuração de Campo — Lubrificação`, `Matriz de Escalonamento` nem
  `Notification Outbox`.
- Técnico acessa telas técnicas do próprio tenant, mas não configuração global.
- Admin acessa tudo e pode selecionar tenant.
- Cliente A não consulta dados do cliente B.

## 5. Incremento 2 - ingestão fail-closed e proxy confiável

Objetivo: fechar a API de campo para dados reais.

Arquivos principais:

- `src/api/grease_security_middleware.py`
- `src/api/condition_security_middleware.py`
- `src/api/grease_ingest_api.py`
- `src/api/condition_ingest_api.py`
- `deploy/nginx_grease_ingest.conf`
- `deploy/nginx_condition_ingest.conf`
- `tests/test_grease_ingest_api.py`
- `tests/test_condition_ingest_api.py`

Passos:

1. Confirmar que os tokens existem no `.env` de produção:

```bash
GREASE_INGEST_TOKEN=<token_rotacionavel>
CONDITION_INGEST_TOKEN=<token_rotacionavel>
```

2. Garantir que estes valores não estejam definidos como `false` em produção:

```bash
GREASE_REQUIRE_TOKEN=false
CONDITION_REQUIRE_TOKEN=false
```

3. Ajustar NGINX para sobrescrever a origem confiável, evitando aceitar
   `X-Forwarded-For` vindo do cliente final. **Implementado com
   `X-Trusted-Client-IP`.**
4. Evoluir os middlewares para preferir um cabeçalho interno do proxy, por
   exemplo `X-Trusted-Client-IP`, e só usar `X-Forwarded-For` em modo local.
   **Implementado.**
5. Validar 401 sem token, 503 sem token configurado e 403 para IP não permitido.

Critério de aceite:

- `/grease/ingest` e `/condition/ingest` nunca aceitam payload sem token em
  ambiente produtivo.
- Allowlist funciona apenas com IP definido pelo proxy.
- Testes de ingestão continuam passando.

## 6. Incremento 3 - CORS, rate limit e WAF

Objetivo: reduzir superfície de ataque sem afetar gateways de campo.

Arquivos principais:

- `src/api/grease_ingest_api.py`
- `src/api/condition_ingest_api.py`
- `deploy/nginx_grease_ingest.conf`
- `deploy/nginx_condition_ingest.conf`
- `infra/alb/*`
- `docs/migracao_alb_cognito.md`
- `docs/runbook_ativacao_portal.md`

Passos:

1. Trocar CORS permissivo por allowlist via env. **Implementado no código; falta
   ativar valores nos ambientes publicados.**

```bash
ALLOWED_ORIGINS=https://app.sentinelaindustrial.com.br,https://sentinelaindustrial.com.br
```

2. Se o endpoint é usado apenas por gateways/server-to-server, considerar
   remover CORS da ingestão.
3. Aplicar `limit_req` no NGINX para `/grease/ingest` e `/condition/ingest`.
4. Colocar WAF no CloudFront/ALB com regra baseada em taxa.
5. Criar testes para parse de `ALLOWED_ORIGINS`.

Critério de aceite:

- Browser não consegue chamar API de origem não autorizada.
- Gateway autorizado continua funcionando.
- Requisições em rajada são limitadas antes de chegar no FastAPI.

## 7. Incremento 4 - auditoria de ações sensíveis

Objetivo: registrar quem alterou o quê, sem derrubar a aplicação.

Arquivos principais:

- `src/dashboard/auth/audit.py`
- `src/dashboard/config_ui.py`
- `src/dashboard/lubrication_field/field_config_ui.py`
- `src/dashboard/escalation_ui.py`
- `src/dashboard/alerts_ui.py`
- `src/dashboard/e2e_ui.py`
- `infra/aws-cli/18-create-audit-log-dynamodb.sh`
- `docs/auditoria.md`
- `tests/test_dashboard_auth.py` ou novo `tests/test_audit_events.py`

Passos:

1. Criar tabela `audit_log` com `pk=TENANT#<tenant_id>` e
   `sk=<timestamp>#<event_id>`.
2. Definir no app:

```bash
AUDIT_LOG_TABLE=audit_log
```

3. Chamar `audit.record(...)` nos pontos de gravação:
   configurações gerais, configuração de campo, mudança de status de alerta,
   alteração da matriz de escalonamento, geração/processamento de outbox e teste
   ponta a ponta. **Implementado via `dashboard.audit_events.record_sensitive_action`.**
4. Nos testes, usar fake repository ou arquivo JSONL temporário. **Implementado com
   `tests/test_audit_events.py`.**

Critério de aceite:

- Toda alteração operacional sensível deixa trilha com usuário, perfil, tenant,
  alvo, ação e timestamp.
- Falha na auditoria não quebra o fluxo principal.

## 8. Incremento 5 - substituir scans por consultas indexadas

Objetivo: preparar o DynamoDB para multiativos reais.

Arquivos principais:

- `src/dashboard/dynamodb_repository.py`
- `src/dashboard/multiasset_repository.py`
- `src/api/condition_ingest_service.py`
- `src/api/grease_ingest_service.py`
- `infra/aws-cli/*`
- `infra/*`
- `tests/test_multiasset_repository.py`
- `tests/test_dashboard_repository.py`

Mudanças de modelo sugeridas:

- Estado atual:
  - `tenant_plant = <tenant_id>#<plant_id>`
  - GSI `tenant_plant_index`: partition `tenant_plant`, sort `asset_id`
- Alertas:
  - `tenant_plant = <tenant_id>#<plant_id>`
  - `status_severity = <status>#<severity>#<updated_at>`
  - GSI para listagem por planta/status.

Passos:

1. Fazer writers preencherem novos atributos sem remover o modelo antigo.
   **Implementado para `tenant_plant` em estado atual e alertas.**
2. Criar GSI em staging.
   **Preparado por env vars `STATE_TENANT_PLANT_INDEX`,
   `ALERTS_TENANT_PLANT_INDEX` e `CONDITION_ALERTS_TENANT_PLANT_INDEX`.**
3. Alterar readers para usar `query` quando o GSI existir.
   **Implementado em `MultiAssetRepository`, `DashboardRepository` e
   `AlertsRepository`.**
4. Manter fallback controlado para `scan` no modo demo/local.
   **Implementado com fallback em `ValidationException`, para ambientes onde o
   GSI ainda não existe.**
5. Validar relatórios, planta e alertas com dados existentes.

Critério de aceite:

- Visão de planta e relatórios não dependem de `scan` em produção.
- Dados antigos continuam legíveis durante a migração.

## 9. Incremento 6 - site institucional e acesso ao sistema

Objetivo: publicar vitrine sem expor dashboard técnico bruto.

Arquivos principais:

- `site/index.html`
- `site/sistema-de-lubrificacao/index.html`
- `site/como-funciona/index.html`
- `site/demonstracao/index.html`
- `site/acesso/index.html`
- `site/assets/styles.css`
- `site/robots.txt`
- `site/sitemap.xml`
- `infra/site/*`
- `.github/workflows/deploy-site.yml`

Passos:

1. Ajustar domínio, canonical e URLs finais no site.
2. Publicar site em S3 + CloudFront.
3. Confirmar `noindex` em `/acesso/`.
4. Ligar botão `Acesso ao Sistema` para o login real do app.
5. Validar Search Console, sitemap e metadados Open Graph.

Critério de aceite:

- Site público indexável.
- Área de acesso não indexável.
- CTA de demonstração funciona ou aponta para canal de contato validado.

## 10. Incremento 7 - observabilidade operacional

Objetivo: saber se o sistema está vivo, lento, recebendo dados ou falhando.

Arquivos principais:

- `deploy/app/streamlit-dashboard.service`
- `deploy/grease-ingest.service`
- `deploy/condition-ingest.service`
- `deploy/auth/oauth2-proxy.service`
- `deploy/nginx_*`
- `docs/runbook_ativacao_portal.md`
- `docs/troubleshooting_grease_ingest.md`

Passos:

1. Enviar logs de NGINX, Streamlit, FastAPI e oauth2-proxy para CloudWatch.
2. Criar alarmes para 5xx, latência, falta de ingestão e erro de login.
3. Adicionar health checks pós-deploy:
   - `GET /condition/health`
   - `GET /grease/health`
   - app autenticado redireciona anônimo para login
   - site responde 200
4. Documentar runbook de incidente e rollback.

Critério de aceite:

- Falhas críticas geram alarme.
- Operador técnico sabe qual serviço reiniciar e onde olhar logs.

## 11. Incremento 8 - CI/CD e IaC com gates

Objetivo: tirar deploy manual do caminho crítico.

Arquivos principais:

- `.github/workflows/deploy-app.yml`
- `.github/workflows/deploy-site.yml`
- `infra/github-oidc/*`
- `infra/site/*`
- `infra/alb/*`
- `infra/cognito/*`
- `docs/cicd_iac.md`

Passos:

1. Criar ambientes GitHub `staging` e `production`.
2. Usar OIDC para AWS, sem access key fixa.
3. Rodar testes, compileall e smoke tests antes de deploy.
4. Exigir aprovação manual para production.
5. Publicar primeiro site, depois app, depois infra sensível.

Critério de aceite:

- Deploy de staging é repetível.
- Production exige aprovação.
- Rollback está documentado e testado.

## 12. Incremento 9 - modularização sem big-bang

Objetivo: reduzir acoplamento do `app.py` preservando telas atuais.

Arquivos principais:

- `src/dashboard/app.py`
- `src/dashboard/*_ui.py`
- `src/dashboard/lubrication/*`
- `src/dashboard/lubrication_field/*`
- `src/api/*`
- `src/rules_engine/*`
- `src/edge/*`
- `docs/plano_modularizacao.md`

Sequência recomendada:

1. Extrair contratos canônicos para um pacote interno comum.
2. Isolar repositórios DynamoDB/S3 atrás de interfaces.
3. Transformar módulos de lubrificação em um serviço/coordenador próprio.
4. Mover alertas, escalonamento e outbox para serviço orientado a eventos.
5. Fazer a IHM consumir APIs internas, reduzindo lógica de negócio no Streamlit.
6. Unificar `src/edge_bridge` e `src/edge/*_bridge_field` sob adaptadores.

Critério de aceite:

- Cada etapa mantém telas atuais funcionando.
- Cada fronteira nova tem contrato e teste.
- Nenhum módulo especialista depende de `streamlit`.

## 13. Ordem recomendada de execução

1. Incremento 0 - baseline e testes.
2. Incremento 1A - proteção imediata do app.
3. Incremento 2 - garantir ingestão fail-closed em ambiente real.
4. Incremento 1B - Cognito/oauth2-proxy/RBAC ativo.
5. Incremento 3 - CORS/rate limit/WAF.
6. Incremento 4 - auditoria.
7. Incremento 6 - site institucional publicado.
8. Incremento 7 - observabilidade.
9. Incremento 8 - CI/CD e IaC.
10. Incremento 5 - GSI e queries.
11. Incremento 9 - modularização progressiva.

## 14. Regra de ouro para comunicação comercial

Comunicar como pronto:

- monitoramento de condição;
- sistema de lubrificação por pressão;
- ingestão via gateway/API;
- diagnóstico explicável;
- HMI de operador/técnico;
- piloto demonstrável e operável.

Comunicar como roadmap:

- ML/SageMaker;
- SiteWise Edge;
- Modbus completo;
- CRM integrado;
- multi-tenant produtivo em escala;
- módulos especialistas independentes.

Isso evita vender como produto acabado aquilo que hoje ainda está em maturação
operacional.
