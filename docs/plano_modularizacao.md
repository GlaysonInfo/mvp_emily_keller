# Plano de Modularização — Refatoração Interna + Visualização Local

Plano de execução **antes** de codar. Nenhum arquivo será movido até este
plano estar aprovado. Sem mexer no EC2; tudo roda em **localhost**, atrás de
um reverse proxy local numa única porta (`127.0.0.1:8080`).

## 1. Princípios

- **Strangler fig**: nada de big-bang. Mover por domínio, deixando *shims* de
  compatibilidade no caminho antigo enquanto o `app.py` ainda referenciar.
- **Sem quebrar a IHM em produção/staging**: o app continua subindo igual a
  cada passo. Cada fase tem um *critério de aceite* verificável.
- **Aproveitar o que já começou**: já existem `src/dashboard/app_local.py`,
  `src/dashboard/local_demo_repository.py` e `src/rules_engine/`. O plano
  constrói sobre isso, não substitui.
- **Fronteiras antes de serviços**: este passo é *refatoração interna* — não
  cria novos processos por domínio ainda. Cria os contratos para isso depois.
- **Local first**: todo o trabalho é validável no seu notebook, sem AWS.

## 2. Estado atual (síntese curta)

- `src/dashboard/app.py` tem **1060 linhas** e importa **~28 módulos**.
- **~40 arquivos** soltos no raiz de `src/dashboard/` se agrupam naturalmente
  em domínios (alerts, escalation, intelligence, notification, history, config,
  data, reports, e2e, demo).
- Sub-pacotes já existem e ficam: `auth/`, `hmi/`, `lubrication/`,
  `lubrication_field/`, `lubrication_efficiency/`,
  `lubrication_motor_efficiency/`, `lubrication_virtual_bench/`.
- Domínio de regras/diagnóstico já tem um pacote dedicado em
  `src/rules_engine/` (alert_models, diagnostics, rules) — manter e crescer.
- APIs em `src/api/` (grease/condition ingest) e Lambdas em `src/aws_lambdas/`
  ficam onde estão (escopo separado).
- **Duplicidade conhecida** (fora do escopo desta passada, mas registrada):
  `src/edge_bridge/` (legado MVP, OPC UA + MQTT) vs `src/edge/*_field` (campo,
  HTTP-JSON + IO-Link).

## 3. Estrutura-alvo do `src/dashboard/`

Sub-pacotes por domínio. Cada um com `engine.py` (lógica), `repository.py`
(persistência), `ui.py` (Streamlit) — quando aplicável — e um `__init__.py`
que **re-exporta** o que o `app.py` precisa.

```
src/dashboard/
├── app.py                  # router/dispatch (vai encolhendo)
├── app_local.py            # variante 100% local (já existe)
├── core/                   # transversal: formatters, gauges, demo_cases
│   ├── echarts_gauge_components.py
│   ├── connection_validators.py
│   └── demo/  (demo_cases.py, seed_history_for_intelligence.py)
├── data/                   # repositórios + factory
│   ├── dynamodb_repository.py
│   ├── multiasset_repository.py
│   ├── local_demo_repository.py
│   └── history_repository.py
├── alerts/                 # alert_*.py + alerts_*.py
│   ├── projection.py       # alert_projection.py
│   ├── repository.py       # alerts_repository.py
│   ├── parameter_presets.py
│   └── ui.py
├── escalation/             # escalation_*.py + reset_escalation_rules.py
│   ├── engine.py
│   ├── repository.py
│   └── ui.py
├── intelligence/           # intelligence_*.py + operational_intelligence_ui.py
│   ├── engine.py
│   ├── rules.py
│   ├── labels.py
│   ├── repository.py
│   ├── demo_history.py
│   └── ui.py               # operational_intelligence_ui
├── notification/           # notification_outbox_*.py
│   ├── engine.py
│   ├── repository.py
│   └── ui.py
├── config/                 # config_*.py + config_validation_ui.py
│   ├── repository.py
│   ├── consistency.py
│   ├── consistency_ui.py
│   ├── validation_ui.py
│   └── ui.py
├── history/                # history_export.py + history_ui.py
│   ├── export.py
│   └── ui.py
├── reports/                # reports.py + reports_ui.py
│   ├── engine.py
│   └── ui.py
├── e2e/                    # e2e_engine.py + e2e_ui.py
│   ├── engine.py
│   └── ui.py
├── plant/                  # plant_overview_ui.py (vista do operador)
│   └── overview_ui.py
├── auth/                   # já modularizado
├── hmi/                    # já modularizado
├── lubrication/            # já modularizado
├── lubrication_field/      # já modularizado
├── lubrication_efficiency/ # já modularizado
├── lubrication_motor_efficiency/   # já modularizado
└── lubrication_virtual_bench/      # já modularizado
```

> Cada movimentação deixa um **shim** no caminho antigo:
> ```python
> # src/dashboard/alerts_ui.py (shim temporário)
> from dashboard.alerts.ui import *  # noqa: F401, F403
> ```
> Assim o `app.py` continua importando do caminho antigo enquanto a transição
> acontece, sem nenhum breakage. Os shims somem na última fase.

## 4. Topologia local (uma porta, três processos)

```
                       ┌──────────────────────┐
 navegador  ─────────► │  reverse proxy local │
 localhost:8080        │  (Caddy ou nginx)    │
                       └──────┬───────────────┘
                              │  rotas por path
            ┌─────────────────┼─────────────────────┐
            ▼                 ▼                     ▼
   127.0.0.1:8501     127.0.0.1:8000        127.0.0.1:8001
   Streamlit IHM      FastAPI grease         FastAPI condition
   (src/dashboard)    (src/api/grease...)    (src/api/condition...)
```

Mapeamento de paths:

| Path local | Vai para | Quem |
|---|---|---|
| `http://localhost:8080/` | `127.0.0.1:8501` | Dashboard Streamlit (raiz e demais) |
| `http://localhost:8080/grease/*` | `127.0.0.1:8000` | API de ingestão de graxa |
| `http://localhost:8080/condition/*` | `127.0.0.1:8001` | API de ingestão de condição |

**Por que reverse proxy** (mesmo com um único app na fase atual): cria um
endpoint único de teste local, casa com a topologia futura (ALB), e quando
mais de um app/módulo aparecer, é só adicionar regras de path.

Proposta de orquestração (dois caminhos, escolher um depois):

- **A: Caddy + Makefile** (leve, sem Docker). `Caddyfile.local` minimalista,
  `Makefile` com `make local-up` / `make local-down` que sobem Streamlit + as
  duas APIs em background e o Caddy em foreground.
- **B: docker-compose.local.yml** (mais isolado). Três serviços + nginx num
  compose à parte (não toca no `docker-compose.yml` atual).

Recomendo **A** por ser mais simples e didático na fase de refatoração.

## 5. Fases de execução (passo a passo)

Cada fase é independente, pequena, e tem critério de aceite. Nada é tocado
até a fase anterior estar verde.

### Fase 0 — Preparar o ambiente local (sem mover código)
- Criar `Caddyfile.local` (proxy 8080 → 8501/8000/8001).
- Criar `Makefile` (ou `scripts/local/*.sh`) com targets `local-up`/`down`.
- Confirmar que `app_local.py` sobe sem AWS (usa `local_demo_repository`).
- **Aceite**: abrir `localhost:8080` → IHM responde; `localhost:8080/grease/health` e `/condition/health` retornam 200.

### Fase 1 — `data/` (camada de dados)
Mover: `dynamodb_repository.py`, `multiasset_repository.py`,
`local_demo_repository.py`, `history_repository.py` → `src/dashboard/data/`.
Deixar shims no raiz. Atualizar `data/__init__.py` re-exportando os símbolos.
- **Aceite**: o app local funciona sem alteração de imports nos demais arquivos; testes verdes.

### Fase 2 — `alerts/`
`alert_projection.py` → `alerts/projection.py`,
`alerts_repository.py` → `alerts/repository.py`,
`alerts_ui.py` → `alerts/ui.py`,
`alert_parameter_presets.py` → `alerts/parameter_presets.py`.
Shims no raiz.
- **Aceite**: página "Alertas e Eventos" funciona; testes `tests/test_alerts_*` verdes.

### Fase 3 — `escalation/`
`escalation_engine.py`, `escalation_repository.py`, `escalation_ui.py`,
`reset_escalation_rules.py` → `src/dashboard/escalation/`.
- **Aceite**: "Matriz de Escalonamento" funciona; testes verdes.

### Fase 4 — `intelligence/`
`intelligence_*.py` + `operational_intelligence_ui.py` → `src/dashboard/intelligence/`.
- **Aceite**: "Inteligência Operacional" funciona; testes verdes.

### Fase 5 — `notification/`
`notification_outbox_*.py` → `src/dashboard/notification/`.
- **Aceite**: "Notification Outbox" funciona; testes verdes.

### Fase 6 — `config/`
`config_*.py` + `config_validation_ui.py` + `connection_validators.py` →
`src/dashboard/config/`.
- **Aceite**: "Configurações" funciona (com a auditoria que já registramos).

### Fase 7 — `history/`, `reports/`, `e2e/`, `plant/`, `core/`
Mover os restantes (history_export/_ui, reports/_ui, e2e_*, plant_overview_ui,
demo_cases, echarts_gauge_components) para seus sub-pacotes.
- **Aceite**: todas as páginas continuam funcionando; testes verdes.

### Fase 8 — Apertar o `app.py`
Atualizar os imports do `app.py` para os caminhos **novos** (canônicos).
Reduzir o tamanho usando funções `render_<page>(...)` extraídas se ainda fizer
sentido. **Sem** quebrar a IHM.
- **Aceite**: `app.py` consideravelmente menor; comportamento idêntico ao
  ponto de partida; testes verdes.

### Fase 9 — Limpeza dos shims
Remover os arquivos antigos do raiz (shims) agora que ninguém os importa.
- **Aceite**: `find src/dashboard -maxdepth 1 -name '*.py'` mostra apenas
  `app.py`, `app_local.py` e `__init__.py`.

## 6. Compatibilidade durante a transição

- **Shims** no raiz de `src/dashboard/` re-exportam dos novos caminhos.
- O `app.py` segue importando dos caminhos antigos até a Fase 8 — zero risco
  de breakage entre fases.
- Cada fase atualiza um *único* domínio e roda o app local + a suíte de testes
  daquele domínio antes de seguir.

## 7. Verificação por fase (mesmo padrão)

1. `python -m pytest tests/test_<dominio>*.py` (suíte local do domínio).
2. `make local-up` e clicar nas páginas do domínio movido.
3. `python -m compileall src` para garantir sintaxe.
4. `git diff --stat` para conferir que **só o domínio em questão** foi tocado.

## 8. Fora do escopo desta passada (registrado para depois)

- Quebrar a IHM em **apps Streamlit por domínio** (multi-porta) — exige
  duplicar layout/auth; faremos depois com o reverse proxy já no lugar.
- **Unificar `src/edge_bridge` com `src/edge/*_field`** (duplicidade de
  bridges) — frente própria, fora do escopo do dashboard.
- **Docker Compose** consolidado e **ALB nativo** — já planejados em
  `docs/migracao_alb_cognito.md` e `docs/cicd_iac.md`.
- **Multi-tenant** no nível das *queries* dos repositórios (hoje o
  `tenant_id` é centralizado no `app.py`) — pode entrar numa próxima rodada
  do `data/`.

## 9. O que decido contigo antes de codar

- Caddy + Makefile (opção A) **ou** docker-compose.local.yml (opção B)?
- Em qual fase você quer parar para revisar antes de eu seguir? (Sugestão:
  parar após **Fase 0** e após **Fase 1** para alinhar o estilo do shim e da
  organização dos sub-pacotes; daí em diante eu sigo por domínio com
  *checkpoints* em cada PR/commit.)
- Algum domínio que você quer extrair **primeiro** por interesse prático
  (ex.: `intelligence/` ou `alerts/`) em vez da ordem proposta?
