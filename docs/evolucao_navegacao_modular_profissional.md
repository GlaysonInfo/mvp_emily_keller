# Evolucao Natural - Navegacao Modular Profissional

Este documento registra a evolucao natural da plataforma antes de transformar o
cadastro de cliente, planta, ativos, sensores, usuarios e contrato em um fluxo
guiado de onboarding. O objetivo e garantir que as visoes por perfil e por
servico contratado estejam conceitualmente corretas antes de automatizar o
onboarding.

## 1. Problema identificado

O MVP ja possui autenticacao, RBAC, tenant e filtragem por servicos contratados,
mas a experiencia do tecnico ainda esta muito linear. A sidebar tecnica mistura
rotas de operacao, diagnostico, configuracao, demonstracao, notificacao e
relatorio no mesmo nivel.

Isso gera tres problemas:

- O tecnico nao entende rapidamente quais telas pertencem a Monitoramento de
  Equipamentos e quais pertencem a Sistema de Lubrificacao.
- Telas de demonstracao ou engenharia interna parecem recursos comuns do cliente.
- Inteligencia Operacional aparece mesmo quando deveria depender da contratacao
  dos dois modulos.

Conclusao: antes do onboarding guiado, a plataforma deve organizar a navegacao
por dominio industrial e por contrato ativo.

## 2. Regra de produto

Um cliente pode contratar:

1. Somente Monitoramento de Equipamentos.
2. Somente Sistema de Lubrificacao.
3. Monitoramento de Equipamentos + Sistema de Lubrificacao.

A navegacao de Operador e Tecnico deve refletir exatamente essa contratacao.
Menus de um modulo nao contratado nao devem aparecer.

O menu Inteligencia Operacional deve aparecer somente quando a planta tiver os
dois modulos ativos, porque seu valor nasce da correlacao entre condicao do
ativo, lubrificacao, eventos, historico e recomendacoes.

## 3. Papel do Admin Sentinela

O Admin Sentinela (`ADMIN_SERVER`) e o papel de plataforma. Ele:

- cria clientes/tenants;
- cria ou aprova o primeiro Admin do Cliente;
- cadastra plantas;
- habilita contratos por planta;
- define quais modulos estao ativos;
- governa protocolos, conectores, credenciais, templates, auditoria e suporte;
- pode visualizar a plataforma em modo multi-tenant.

O Admin Sentinela nao deve ser tratado como um operador invisivel do cliente. Se
ele precisar realizar suporte remoto ou configuracao em ambiente de cliente, a
plataforma deve exigir contexto explicito:

- cliente/tenant;
- planta;
- motivo/ticket;
- acao pretendida;
- registro de auditoria;
- idealmente ciencia ou politica contratual do cliente.

## 4. Papel do Admin do Cliente

O Admin do Cliente (`CLIENTE_ADMIN` + `TENANT_<id>`) administra o proprio tenant.
Ele deve ver apenas sua organizacao.

Responsabilidades naturais:

- manter usuarios do cliente;
- indicar quem e operador e quem e tecnico;
- consultar plantas e servicos contratados;
- ajustar destinatarios e politicas locais de notificacao;
- acompanhar o status do contrato e do piloto.

No MVP atual, a tela registra usuarios e administracao local, mas a criacao real
no Cognito ainda nao esta automatizada. Evolucao recomendada: o Admin do Cliente
convida usuarios e o sistema cria/atualiza Cognito automaticamente com:

- grupo de perfil: `CLIENTE_OPERADOR`, `CLIENTE_TECNICO` ou `CLIENTE_ADMIN`;
- grupo de tenant: `TENANT_<id>`;
- atributo `custom:tenant_id`;
- status e trilha de auditoria.

## 5. Menu profissional proposto

### 5.1. Tecnico - somente Monitoramento de Equipamentos

Grande grupo: `Monitoramento de Equipamentos`

Submenus:

- `Visao da Planta`
- `Ativos Monitorados`
- `Diagnostico do Ativo`
- `Historico e Tendencias`
- `Regras e Limites`
- `Alertas e Escalonamento`
- `Relatorios`

Observacao: `Inteligencia Operacional` nao aparece quando o cliente contratou
apenas este modulo. O tecnico pode ter diagnostico e tendencia, mas nao a
correlacao completa com lubrificacao.

### 5.2. Tecnico - somente Sistema de Lubrificacao

Grande grupo: `Sistema de Lubrificacao`

Submenus:

- `Painel do Sistema`
- `Pontos de Lubrificacao`
- `Ciclos e Eficiencia`
- `Anomalias de Campo`
- `Parametros de Campo`
- `Alertas e Escalonamento`
- `Relatorios`

Observacao: `Eficiencia da Lubrificacao do Motor` nao deveria aparecer neste
caso como tela isolada. Se o cliente nao contratou monitoramento de condicao,
nao ha base suficiente para falar de eficiencia no motor em sentido integrado.

### 5.3. Tecnico - ambos os modulos contratados

Grandes grupos:

- `Monitoramento de Equipamentos`
- `Sistema de Lubrificacao`
- `Inteligencia Operacional`

Submenus de `Inteligencia Operacional`:

- `Correlacao Condicao x Lubrificacao`
- `Risco Operacional`
- `Recomendacoes`
- `Evidencias para Relatorio`

Neste caso, uma tela derivada da atual `Eficiencia da Lubrificacao do Motor`
pode fazer sentido, mas deveria ser reposicionada e renomeada como parte da
Inteligencia Operacional, por exemplo:

- `Correlacao Motor x Lubrificacao`; ou
- `Eficiencia Integrada do Ativo`.

## 6. Telas que devem mudar de lugar

| Tela atual | Diagnostico | Destino recomendado |
|---|---|---|
| `Eficiencia da Lubrificacao do Motor` | Parece tela tecnica solta e ambigua | Mover para Inteligencia Operacional quando os dois modulos estiverem ativos |
| `Bancada Virtual - Lubrificacao` | Tela de demo/lab, nao de cliente em producao | Ocultar de clientes; deixar para Admin Sentinela/demonstracao/staging |
| `Configuracao de Campo - Lubrificacao` | Pode ser recurso tecnico real, mas nao deve ficar solto | Renomear para `Parametros de Campo` dentro de Sistema de Lubrificacao |
| `Matriz de Escalonamento` | Configuracao de quem e acionado, por severidade/SLA | Mover para `Alertas e Notificacoes`, visivel para Tecnico autorizado e Admin do Cliente |
| `Notification Outbox` | Fila/auditoria tecnica de notificacoes enviadas | Renomear para `Fila de Notificacoes`; visivel para Admin Sentinela e, talvez, Cliente Admin read-only |
| `Relatorios` | Recurso comum, mas deve respeitar modulo/contrato | Pode ficar como submenu dentro de cada modulo ou como grupo comum filtrado |

## 7. Matriz de Escalonamento

A Matriz de Escalonamento nao e uma tela operacional diaria. Ela define quem
deve ser avisado quando um evento acontece.

Exemplo:

- Alerta critico de motor: avisar operador imediatamente.
- Se nao houver reconhecimento em 15 minutos: avisar tecnico.
- Se persistir por 1 hora: avisar responsavel de manutencao.
- Se risco de parada: avisar gestor da planta.

Uso recomendado:

- Admin Sentinela cria templates globais.
- Admin do Cliente define contatos e politicas locais.
- Tecnico pode ajustar regras tecnicas se o contrato permitir.
- Operador apenas recebe/atende alertas; nao configura matriz.

## 8. Notification Outbox

Notification Outbox e a fila historica/tecnica das notificacoes que o sistema
tentou enviar. Ela responde perguntas como:

- a notificacao foi gerada?
- para quem foi enviada?
- qual canal foi usado?
- houve erro?
- precisa reprocessar?

Uso recomendado:

- Admin Sentinela: acesso completo para suporte e auditoria.
- Admin do Cliente: acesso resumido/read-only para transparencia.
- Tecnico: acesso somente quando estiver tratando falha de notificacao.
- Operador: nao precisa ver esta tela.

Nome recomendado para produto: `Fila de Notificacoes`.

## 9. Bancada virtual e demonstracoes

`Bancada Virtual - Lubrificacao` e uma excelente ferramenta de demonstracao,
teste e suporte, mas nao deve aparecer como tela comum do tecnico do cliente em
producao.

Recomendacao:

- visivel para `ADMIN_SERVER`;
- visivel em ambiente `Demonstracao` ou `Piloto` quando explicitamente ligado;
- oculto por padrao para cliente em producao;
- controlado por flag, por exemplo `DASHBOARD_SHOW_DEMO_TOOLS=true`.

## 10. Modelo de navegacao alvo

Em vez de uma lista unica de radio buttons, a sidebar deveria usar grupos por
servico:

```text
Ambiente
Cliente / Planta / Perfil

Monitoramento de Equipamentos
  - Visao da Planta
  - Ativos Monitorados
  - Diagnostico do Ativo
  - Historico e Tendencias
  - Regras e Limites

Sistema de Lubrificacao
  - Painel do Sistema
  - Pontos de Lubrificacao
  - Ciclos e Eficiencia
  - Parametros de Campo

Inteligencia Operacional
  - Correlacao Condicao x Lubrificacao
  - Recomendacoes
  - Evidencias para Relatorio

Alertas e Notificacoes
  - Alertas e Eventos
  - Escalonamento
  - Fila de Notificacoes

Relatorios
```

O grupo `Inteligencia Operacional` deve existir somente quando
`condition + lubrication` estiverem ativos para a planta.

## 11. Criterios de aceite para refatorar a navegacao

- Cliente com apenas `condition` nao ve telas de lubrificacao.
- Cliente com apenas `lubrication` nao ve telas de monitoramento de condicao.
- Cliente com ambos ve `Inteligencia Operacional`.
- Cliente com apenas um modulo nao ve `Inteligencia Operacional`.
- Operador nunca ve configuracoes, matriz, outbox ou bancada virtual.
- Tecnico ve configuracoes tecnicas somente dos modulos contratados.
- Admin do Cliente ve usuarios, plantas, contratos e politicas locais do tenant.
- Admin Sentinela ve governanca global, tenants, contratos, conectores, auditoria
  e ferramentas de demonstracao/suporte.
- Demo/lab nao aparece em producao para cliente, salvo flag explicita.
- Todo ajuste de configuracao sensivel deve gerar auditoria.

## 12. Ordem incremental recomendada

1. Registrar esta decisao como arquitetura de produto.
2. Ajustar `module_registry.py` para separar rotas por grupos logicos, nao apenas
   por lista linear.
3. Alterar `hmi_sidebar.py` para renderizar navegacao agrupada por modulo.
4. Remover `Bancada Virtual` do tecnico do cliente por padrao.
5. Mover `Eficiencia da Lubrificacao do Motor` para Inteligencia Operacional ou
   Admin/Demo, conforme contrato.
6. Renomear `Notification Outbox` para `Fila de Notificacoes`.
7. Renomear `Matriz de Escalonamento` para `Escalonamento de Alertas` e mover
   para grupo de Alertas e Notificacoes.
8. Criar testes para os tres cenarios de contrato: somente condition, somente
   lubrication e ambos.
9. So depois transformar o cadastro de cliente/planta/ativos/sensores/usuarios
   e contrato em fluxo guiado de onboarding.

## 13. Decisao registrada

A plataforma deve evoluir como sistema multi-tenant modular por servico
contratado, com navegacao profissional por dominio industrial. O onboarding
guiado so deve ser implementado depois que as visoes de Operador, Tecnico,
Admin do Cliente e Admin Sentinela estiverem coerentes com essa arquitetura.
