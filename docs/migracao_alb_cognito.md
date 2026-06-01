# Migração para ALB + Cognito nativo (remover o oauth2-proxy)

Substitui o oauth2-proxy pela autenticação nativa do **Application Load
Balancer** (ação `authenticate-cognito`). O nginx é mantido como reverse proxy
simples (sem `auth_request`). O modelo de perfis e tenants **não muda**.

## Antes x depois

```
ANTES:   Usuário -> nginx (auth_request) -> oauth2-proxy <-> Cognito
                                          -> Streamlit / APIs
DEPOIS:  Usuário -> ALB (authenticate-cognito) <-> Cognito
                 -> nginx (reverse proxy) -> Streamlit / APIs
```

O ALB injeta na requisição:
- `x-amzn-oidc-data` — JWT com claims do *userInfo* (email, `custom:tenant_id`);
- `x-amzn-oidc-accesstoken` — access token do Cognito, que **carrega
  `cognito:groups`** (de onde sai o perfil).

Por isso o **mesmo modelo de grupos** (`ADMIN_SERVER`, `CLIENTE_TECNICO`,
`CLIENTE_OPERADOR`, `TENANT_<id>`) continua valendo — sem precisar de
`custom:role`. A app lê isso em `AUTH_PROVIDER=alb`
(`src/dashboard/auth/identity.py`).

## Componentes

| Caminho | Função |
|---|---|
| `infra/alb/` | ALB, target group (nginx), listener `authenticate-cognito`, regras de ingestão sem auth, SGs, associação WAF opcional |
| `deploy/auth/nginx_app_alb.conf` | nginx do modo ALB (sem oauth2-proxy); repassa `x-amzn-oidc-*` ao Streamlit |
| `src/dashboard/auth/identity.py` | `AUTH_PROVIDER=alb`: lê grupos do access token e email/tenant do data |

## Pré-requisitos

- Certificado **ACM na região do ALB** para `app.sentinelaindustrial.com.br`
  (ALB usa cert regional; só o CloudFront exige us-east-1).
- App Client do Cognito com a callback do ALB:
  `https://app.sentinelaindustrial.com.br/oauth2/idpresponse`.
- VPC, 2+ subnets públicas e o `instance_id` da EC2.

## Cutover (passo a passo)

1. **Callback do ALB no Cognito.** Adicione a callback do ALB ao App Client:
   ```bash
   # acrescente https://app.sentinelaindustrial.com.br/oauth2/idpresponse
   # às Callback URLs do app client (console ou update-user-pool-client).
   ```
2. **Provisionar o ALB:**
   ```bash
   cd infra/alb && terraform init && terraform apply \
     -var="vpc_id=vpc-..." -var='public_subnet_ids=["subnet-a","subnet-b"]' \
     -var="instance_id=i-..." \
     -var="certificate_arn=arn:aws:acm:<regiao>:<acct>:certificate/<id>" \
     -var="user_pool_arn=<arn>" -var="user_pool_client_id=<id>" \
     -var="user_pool_domain=sentinela-industrial-login"
   terraform output    # alb_dns_name, alb_zone_id, instance_security_group_id
   ```
3. **Travar a instância:** anexe o `instance_security_group_id` à EC2 e
   **remova** qualquer ingress público (a EC2 passa a aceitar só o ALB).
4. **nginx:** troque a config do oauth2-proxy pela do modo ALB e pare o proxy:
   ```bash
   sudo cp deploy/auth/nginx_app_alb.conf /etc/nginx/conf.d/app_sentinela.conf
   sudo rm -f /etc/nginx/conf.d/app_sentinela_oauth2.conf   # config antiga
   sudo nginx -t && sudo systemctl reload nginx
   sudo systemctl disable --now oauth2-proxy
   ```
5. **App:** no `.env`, defina `AUTH_PROVIDER=alb` e reinicie:
   ```bash
   sudo systemctl restart streamlit-dashboard
   ```
6. **DNS:** aponte `app.sentinelaindustrial.com.br` para o ALB
   (registro ALIAS no Route 53 usando `alb_dns_name`/`alb_zone_id`).
7. (Opcional) Associe um **Web ACL regional** ao ALB via `-var="web_acl_arn=..."`.

## Verificação (aceite)

- [ ] Acesso anônimo é levado ao login do Cognito pelo ALB.
- [ ] Operador não vê "Configurações"/"Configuração de Campo"; Técnico vê campo,
      não global; Admin vê tudo (e tem o seletor de tenant).
- [ ] Cliente A não vê dados de B (isolamento).
- [ ] `POST /grease/ingest` sem token → 401/503 (rota de ingestão sem Cognito).
- [ ] Logout pelo botão "Sair".

## Segurança (limite de confiança)

A app **não verifica a assinatura** do `x-amzn-oidc-data`/`-accesstoken`; isso é
seguro porque a instância só aceita tráfego do ALB (security group em
`infra/alb`) e, na rota autenticada, o ALB **sobrescreve** esses cabeçalhos
(o cliente não consegue forjá-los). Hardening opcional: validar a assinatura
ES256 contra a chave pública regional do ALB
(`https://public-keys.auth.elb.<regiao>.amazonaws.com/<kid>`).

## Rollback

1. `.env`: `AUTH_PROVIDER=proxy`; `sudo systemctl restart streamlit-dashboard`.
2. Restaurar a config nginx com oauth2-proxy (`deploy/auth/nginx_app_auth.conf`)
   e `sudo systemctl enable --now oauth2-proxy`.
3. DNS de volta para a EC2 (ou manter o ALB sem a ação de auth, conforme o caso).
4. Reabrir o ingress da EC2 conforme a topologia anterior.

> O fallback de tenant por grupo `TENANT_<id>` e o atributo `custom:tenant_id`
> continuam funcionando igual ao modo proxy — ver `docs/tenant_claim_setup.md`.
