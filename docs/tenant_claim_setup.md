# Levar o tenant até a aplicação (isolamento por cliente)

Para o perfil **cliente** (Operador/Técnico), a aplicação precisa saber a qual
cliente o usuário pertence — o `tenant_id`. O `src/dashboard/auth` resolve o
tenant assim, em ordem de precedência:

1. cabeçalho `X-Forwarded-Tenant` (se o proxy o enviar); senão
2. um grupo no formato `TENANT_<id>` (convenção de grupo); senão
3. usuário cliente **sem** tenant é bloqueado (Admin não precisa — opera cross-tenant).

Há duas formas de fornecer o tenant. **A Abordagem A é a recomendada** por não
exigir infraestrutura extra.

---

## Abordagem A (recomendada) — tenant via grupo `TENANT_<id>`

O oauth2-proxy já repassa os grupos do Cognito nativamente (via
`set_xauthrequest`/`X-Auth-Request-Groups`). Basta adicionar a cada usuário
cliente um grupo que carrega o tenant. **Nenhuma config alpha, nenhuma Lambda.**

### Passos

1. Criar o grupo do cliente (uma vez por cliente):
   ```bash
   POOL=<USER_POOL_ID>
   aws cognito-idp create-group --user-pool-id $POOL --group-name TENANT_cliente_demo
   ```
2. Adicionar o usuário ao grupo de perfil **e** ao grupo de tenant:
   ```bash
   aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
     --username tecnico@cliente.com --group-name CLIENTE_TECNICO
   aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
     --username tecnico@cliente.com --group-name TENANT_cliente_demo
   ```

A aplicação extrai `cliente_demo` do grupo `TENANT_cliente_demo`. O prefixo é
configurável por `AUTH_TENANT_GROUP_PREFIX` (padrão `TENANT_`). Os grupos
`TENANT_*` são ignorados na resolução de perfil (só contam `ADMIN_SERVER`,
`CLIENTE_TECNICO`, `CLIENTE_OPERADOR`).

> Observação: manter também o atributo `custom:tenant_id` no usuário é útil para
> relatórios/admin, mesmo usando a convenção de grupo.

---

## Abordagem B (avançada) — tenant como claim (`tenant_id`)

Use se preferir um claim limpo em vez de grupo. Tem duas partes.

### B.1. Lambda Pre Token Generation (injeta o claim)

Código pronto em `infra/cognito/pre_token_generation_lambda.py` — copia
`custom:tenant_id` → claim `tenant_id` no ID token.

Anexar como gatilho do User Pool (Terraform), adicionando ao
`aws_cognito_user_pool` em `infra/cognito/main.tf`:

```hcl
# variável (variables.tf)
variable "pre_token_generation_lambda_arn" {
  type    = string
  default = ""
}

# dentro do resource aws_cognito_user_pool "sentinela"
dynamic "lambda_config" {
  for_each = var.pre_token_generation_lambda_arn == "" ? [] : [1]
  content {
    pre_token_generation = var.pre_token_generation_lambda_arn
  }
}
```

Crie a função (zip do arquivo acima) e passe o ARN em
`-var="pre_token_generation_lambda_arn=arn:aws:lambda:...:function:..."`.

### B.2. oauth2-proxy alpha (repassa o claim como cabeçalho)

Use `deploy/auth/oauth2-proxy.alpha.cfg.example` e rode o proxy com
`--alpha-config`. O nginx já lê `X-Auth-Request-Tenant` (ver
`deploy/auth/nginx_app_auth.conf`) e o repassa como `X-Forwarded-Tenant`.

> A config alpha é sensível à versão do oauth2-proxy: valide com
> `oauth2-proxy --version` e teste em staging.

---

## Como verificar (qualquer abordagem)

1. Logar como Técnico/Operador do `cliente_demo` e abrir o app.
2. Na barra lateral deve aparecer "Cliente: cliente_demo".
3. Confirmar que esse usuário **não** vê dados de outro tenant.
4. Logar como Admin: opera cross-tenant (não restrito a um cliente).

Se um usuário cliente cair na mensagem "não está associado a nenhum cliente",
faltou o grupo `TENANT_<id>` (Abordagem A) ou o claim `tenant_id` (Abordagem B).
