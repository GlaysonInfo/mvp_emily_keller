# Trilha de Auditoria (quem alterou o quê e quando)

Registra eventos sensíveis — alterações de configuração e de campo — com o
usuário, o perfil, o cliente (tenant), a ação, o alvo e o horário. Depende do
portal de acesso ativo (`AUTH_ENABLED=true`) para identificar o usuário.

## Como funciona

- `src/dashboard/auth/audit.py` grava cada evento. O **ator** (usuário logado)
  é definido por sessão no `app.py` (`audit.set_actor(identity)`) e lido nos
  pontos de gravação.
- Destino: **DynamoDB** se `AUDIT_LOG_TABLE` estiver definido; caso contrário (ou
  em falha), arquivo **JSONL** em `AUDIT_LOG_FILE` (padrão `logs/audit.log`).
- O registro **nunca levanta exceção** — auditoria não derruba a aplicação.

## Pontos já instrumentados

| Ação | Onde | Cobertura |
|---|---|---|
| `config.save` | `config_ui._save` | Todas as gravações da página Configurações: cliente, planta, fontes de dados, ativos, mapeamento de sinais e parâmetros/alertas |
| `field_config.save` | `lubrication_field/field_config_store.save_field_config` | Configuração de campo da lubrificação |

> Para auditar mais ações (ex.: tratar alerta, alterar matriz de escalonamento),
> chame `audit.record("acao", target=..., details=...)` no ponto de gravação —
> o ator e o tenant são preenchidos automaticamente a partir da sessão.

## Versionamento do cadastro técnico

Alterações em gateways, ativos, sensores, mapeamentos de sinais e parâmetros de
alerta também geram uma revisão estruturada no `DASHBOARD_CONFIG_STORE`.

Cada revisão contém:

- número sequencial e identificador da alteração;
- data UTC, usuário e perfil autenticado;
- tenant, planta, tipo da mudança e alvo técnico;
- motivo informado pelo responsável;
- operação e estado anterior/posterior de cada entidade alterada.

O histórico pode ser consultado em **Admin Sentinela > Onboarding > Ativo,
sensor e gateway > Histórico técnico e auditoria**. O store mantém as 250
revisões mais recentes. A mesma ação também é enviada para a auditoria global
como `technical_registry.update` ou `config.save`.

Gravações sem diferença técnica não criam uma nova versão. O arquivo de
configuração é substituído atomicamente para reduzir o risco de corrupção em
caso de interrupção durante a escrita.

Duplicações e remoções de sensores também são versionadas. A remoção elimina o
mapeamento de sinal associado e só remove a regra do ativo/métrica quando
nenhum outro sensor ainda utiliza essa métrica.

## Esquema do evento

```json
{
  "ts": "2026-05-27T18:30:00Z",
  "event_id": "a1b2c3d4e5f6",
  "action": "config.save",
  "user_email": "tecnico@cliente.com",
  "role": "tecnico",
  "tenant_id": "cliente_demo",
  "target": "Parâmetro/alerta salvo com sucesso.",
  "details": null,
  "status": "ok",
  "source": "dashboard"
}
```

No DynamoDB: `pk = TENANT#<tenant_id>`, `sk = <ts>#<event_id>` — permite
consultar por cliente e por janela de tempo (query por `pk` + range de `sk`).

## Configuração

```ini
# .env do app
AUDIT_LOG_TABLE=condition_audit_log     # opcional; sem ela usa arquivo
AUDIT_LOG_FILE=logs/audit.log           # fallback (padrão)
```

Criar a tabela (mesmo padrão dos demais scripts de infra):

```bash
AUDIT_LOG_TABLE=condition_audit_log bash infra/aws-cli/18-create-audit-log-dynamodb.sh
```

A IAM role da aplicação precisa de `dynamodb:PutItem` nessa tabela (consultas de
leitura/relatório usam `dynamodb:Query`).

## Verificação

1. Logar e salvar algo em Configurações.
2. Conferir um novo item:
   ```bash
   # arquivo:
   tail -n 5 logs/audit.log
   # ou DynamoDB:
   aws dynamodb query --table-name condition_audit_log \
     --key-condition-expression "pk = :p" \
     --expression-attribute-values '{":p":{"S":"TENANT#cliente_demo"}}'
   ```
