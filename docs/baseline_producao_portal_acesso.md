# Baseline de Producao - Portal de Acesso

Este documento registra o estado minimo esperado para considerar o portal de
acesso pronto como baseline de producao do MVP. Use como checklist apos deploy,
troca de configuracao do Cognito, atualizacao do nginx ou criacao de novos
usuarios.

## 1. Escopo validado

- Vitrine institucional publica: `https://sentinelaindustrial.com.br/`.
- Hub de acesso publico e sem indexacao: `https://sentinelaindustrial.com.br/acesso/`.
- App operacional protegido: `https://app.sentinelaindustrial.com.br/`.
- Login via AWS Cognito Hosted UI.
- Protecao do app via nginx + oauth2-proxy.
- Separacao de menus e rotas por perfil.
- Isolamento de cliente por grupo Cognito `TENANT_<tenant_id>`.
- Logout completo: app -> oauth2-proxy -> Cognito -> vitrine institucional.

## 2. Grupos Cognito obrigatorios

| Grupo | Finalidade |
|---|---|
| `ADMIN_SERVER` | Admin Sentinela / plataforma, cross-tenant |
| `CLIENTE_ADMIN` | Admin do cliente, limitado ao proprio tenant |
| `CLIENTE_TECNICO` | Tecnico do cliente, limitado ao proprio tenant |
| `CLIENTE_OPERADOR` | Operador do cliente, limitado ao proprio tenant |
| `TENANT_cliente_demo` | Associacao dos usuarios do cliente `cliente_demo` |

Usuarios de cliente precisam ter sempre um grupo de perfil e um grupo de tenant.
Exemplo: `admin.cliente@cliente.com` precisa de `CLIENTE_ADMIN` e
`TENANT_cliente_demo`. O atributo `custom:tenant_id` deve ser mantido, mas no
fluxo atual o tenant efetivo vem do grupo `TENANT_`.

## 3. Usuarios de referencia

| Usuario | Grupos esperados | Resultado esperado |
|---|---|---|
| `operador@cliente.com` | `CLIENTE_OPERADOR`, `TENANT_cliente_demo` | Ve apenas menu operacional |
| `tecnico@cliente.com` | `CLIENTE_TECNICO`, `TENANT_cliente_demo` | Ve menu tecnico, sem admin global |
| `admin.cliente@cliente.com` | `CLIENTE_ADMIN`, `TENANT_cliente_demo` | Ve administracao do cliente, sem admin Sentinela |
| `admin@sentinela.com.br` | `ADMIN_SERVER` | Ve administracao da plataforma |

Nao registre senhas neste arquivo nem em arquivos versionados.

## 4. Validacao por linha de comando

Execute na EC2:

```bash
cd /opt/automacaoapi
git log -1 --oneline

curl -I https://sentinelaindustrial.com.br/
curl -I https://sentinelaindustrial.com.br/acesso/
curl -I https://app.sentinelaindustrial.com.br/
curl -I https://app.sentinelaindustrial.com.br/oauth2/sign_out

curl http://127.0.0.1:8000/grease/health
curl http://127.0.0.1:8001/condition/health
curl http://127.0.0.1:8501/_stcore/health

sudo systemctl status grease-ingest --no-pager
sudo systemctl status condition-ingest --no-pager
sudo systemctl status streamlit-dashboard --no-pager
sudo systemctl status oauth2-proxy --no-pager
```

Resultados esperados:

- `sentinelaindustrial.com.br/`: `200 OK`.
- `sentinelaindustrial.com.br/acesso/`: `200 OK`.
- `app.sentinelaindustrial.com.br/` sem cookie: `302` para Cognito.
- `app.sentinelaindustrial.com.br/oauth2/sign_out`: `302` iniciando logout.
- APIs locais de health: `ok: true`.
- Streamlit local: `ok`.
- Servicos systemd: `active (running)`.

Observacao: `https://app.sentinelaindustrial.com.br/oauth2/auth` pode retornar
`404` quando chamado externamente. Isso e esperado porque a rota e `internal` no
nginx e deve ser usada apenas por `auth_request`.

## 5. Validacao por navegador

Use aba anonima para cada usuario, ou faca logout completo entre os testes:

`https://app.sentinelaindustrial.com.br/oauth2/sign_out`

Checklist:

- [ ] Vitrine abre sem login.
- [ ] Botao de acesso leva ao Hosted UI do Cognito.
- [ ] Usuario anonimo nao abre o dashboard diretamente.
- [ ] Operador nao ve navegacao tecnica nem administracao.
- [ ] Tecnico ve telas tecnicas contratadas e nao ve Admin da Plataforma.
- [ ] Admin do Cliente ve administracao do cliente e nao ve Admin da Plataforma.
- [ ] Admin Sentinela ve Admin da Plataforma.
- [ ] Usuario de cliente sem `TENANT_` e bloqueado com mensagem de tenant.
- [ ] Logout pelo link "Sair" encerra sessao e retorna para a vitrine.
- [ ] Apos logout completo, outro usuario pode entrar sem herdar a sessao anterior.

## 6. Variaveis de ambiente esperadas

No `/opt/automacaoapi/.env`:

```ini
AUTH_ENABLED=true
AUTH_LOGIN_URL=https://app.sentinelaindustrial.com.br/oauth2/start?rd=%2F
AUTH_SIGNOUT_URL=https://app.sentinelaindustrial.com.br/oauth2/sign_out
INSTITUTIONAL_SITE_URL=https://sentinelaindustrial.com.br/
```

No oauth2-proxy, a whitelist precisa permitir o dominio institucional e o Hosted
UI do Cognito:

```ini
OAUTH2_PROXY_WHITELIST_DOMAINS=.sentinelaindustrial.com.br,sentinela-industrial-login.auth.us-east-1.amazoncognito.com
```

## 7. Evidencias a registrar no aceite

- SHA do commit em producao (`git log -1 --oneline`).
- Data/hora do teste.
- Prints ou anotacoes de menu para cada perfil.
- Saida dos comandos `curl` de health.
- Saida resumida dos `systemctl status`.
- Lista de grupos Cognito por usuario, sem senhas.

## 8. Estado de baseline aprovado

Quando todos os itens acima passarem, considerar fechado o baseline:

`vitrine publica -> login Cognito -> app protegido -> RBAC por perfil -> tenant -> logout para vitrine`

Proximo bloco recomendado apos este baseline: hardening operacional em AWS
CloudWatch, backup, auditoria persistente e ingestao em campo com tokens e
restricao de origem.
