# AGENTS.md

Repository-wide instructions for coding agents working in this workspace.

## Working Baseline

- Run commands from the repository root.
- Set `PYTHONPATH` before running Python entry points. Use `PYTHONPATH=src:.` in bash and `$env:PYTHONPATH='src;.'` in PowerShell.
- For local development, install the main project package or the full dependency set. Do not use the Lambda-specific requirements files for general local work.
- Prefer the existing VS Code tasks for `Run unit tests`, `Run OPC UA simulator`, `Run Edge Bridge`, and `Run Mosquitto` when they match the task.
- Keep local lab flows and field/AWS flows separate. This repo contains both.

## Commands Agents Should Prefer

- Full test suite: `python -m unittest discover -s tests`
- OPC UA simulator: `python -m simulator.opcua_server`
- Lab edge bridge: `python -m edge_bridge.main`
- Local dashboard: `PYTHONPATH=src:. python -m streamlit run src/dashboard/app_local.py --server.address 127.0.0.1 --server.port 8501`
- Local grease API: `PYTHONPATH=src:. python -m uvicorn src.api.grease_ingest_api:app --host 127.0.0.1 --port 8000 --reload`
- Local condition API: `PYTHONPATH=src:. python -m uvicorn src.api.condition_ingest_api:app --host 127.0.0.1 --port 8001 --reload`
- Local stack lifecycle: `make local-check`, `make local-up`, `make local-down`, `make local-status`, `make local-logs`

## Platform Notes

- The Makefile and scripts under `scripts/local/` assume bash. On Windows, use Git Bash, WSL, or MSYS2 for those targets.
- PowerShell is fine for direct Python commands and the existing VS Code tasks.
- `docker compose up mosquitto` is the local MQTT broker path used by the lab demo.

## Project Map

- `src/simulator/`: virtual motor model and OPC UA server for the lab demo.
- `src/edge_bridge/`: lab bridge from OPC UA to MQTT or HTTPS.
- `src/edge/grease_bridge_field/` and `src/edge/condition_bridge_field/`: field bridges for real gateway integrations.
- `src/api/`: FastAPI ingest endpoints and their security middleware.
- `src/dashboard/`: Streamlit UI, repositories, and auth helpers.
- `src/rules_engine/`: alerting, diagnostics, and domain rules.
- `tests/`: `unittest` suite. Follow existing fake AWS patterns instead of introducing real AWS dependencies.
- `config/`: JSON configuration files. Prefer env-driven path selection over hardcoded paths.
- `deploy/` and `infra/`: deployment and infrastructure automation; these are not the default local development loop.

## Repo-Specific Conventions

- Relative config paths are expected to resolve from the repository root.
- Preserve the `python -m ...` execution pattern and existing import fallbacks when touching runnable modules.
- Use `requirements.txt` or `python -m pip install -e .` for local development. `requirements_condition_api.txt`, `requirements_grease_api.txt`, and `requirements_intelligence.txt` are narrower deployment subsets.
- `BRIDGE_PUBLISH_MODE` selects `mqtt` or `https`. If you switch to `https`, also set `HTTPS_INGEST_URL`.
- Local API auth can be disabled with `GREASE_REQUIRE_TOKEN=false` and `CONDITION_REQUIRE_TOKEN=false`.
- Avoid editing `src/condition_monitoring_lab_mvp.egg-info/` unless the task is explicitly about packaging metadata.
- Repository documentation is mostly in Portuguese. Reuse the existing domain terms and payload names instead of renaming them into generic English.

## Testing Guidance

- Use `unittest`, not `pytest`.
- Prefer a narrow file run while iterating, then rerun `python -m unittest discover -s tests` for the touched area.
- Many tests stub DynamoDB and related AWS services with fake objects. Extend those patterns instead of adding live AWS calls.

## Docs To Link Before You Reconstruct Context

- Architecture overview: [docs/01-visao-geral-arquitetura.md](docs/01-visao-geral-arquitetura.md)
- Integration flows: [docs/06-fluxos-integracao.md](docs/06-fluxos-integracao.md)
- Data dictionary: [docs/04-dicionario-de-dados.md](docs/04-dicionario-de-dados.md)
- Condition ingest contract: [docs/especificacao_endpoint_condition_ingest.md](docs/especificacao_endpoint_condition_ingest.md)
- Grease ingest contract: [docs/especificacao_endpoint_grease_ingest.md](docs/especificacao_endpoint_grease_ingest.md)
- Field lubrication setup: [docs/configuracao_campo_lubrificacao.md](docs/configuracao_campo_lubrificacao.md)
- IO-Link gateway checks: [docs/checklist_teste_gateway_iolink.md](docs/checklist_teste_gateway_iolink.md)
- Grease ingest troubleshooting: [docs/troubleshooting_grease_ingest.md](docs/troubleshooting_grease_ingest.md)
- EC2 deployment flow: [docs/deploy_endpoint_ec2.md](docs/deploy_endpoint_ec2.md)
- Local demo walkthrough: [README.md](README.md)