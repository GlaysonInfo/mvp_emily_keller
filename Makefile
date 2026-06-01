# =====================================================================
# Sentinela Industrial — Makefile (modo local)
# Roda APIs FastAPI + Streamlit + Caddy localmente. Não toca em EC2/AWS.
# Use `make help` para ver os atalhos.
# Pré-req: Python no PATH (ou .venv em .venv/), e Caddy instalado
# (https://caddyserver.com/docs/install).
# Em Windows, rode via Git Bash, WSL ou MSYS2.
# =====================================================================

SHELL := /usr/bin/env bash

.PHONY: help \
        local-check \
        local-up local-down local-status local-logs local-restart \
        local-dashboard local-grease local-condition local-caddy

help: ## mostra esta ajuda
	@awk 'BEGIN{FS=":.*##"; printf "Targets:\n"} \
	     /^[a-zA-Z_-]+:.*##/ {printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)

# ---- diagnostico ---------------------------------------------------------

local-check: ## diagnostica Python, deps, Caddy e portas (rode antes do local-up)
	@bash scripts/local/check.sh

# ---- ciclo de vida do ambiente local ------------------------------------

local-up: ## sobe APIs + dashboard + Caddy em background
	@bash scripts/local/up.sh

local-down: ## para tudo (kills graceful, fallback -9)
	@bash scripts/local/down.sh

local-status: ## lista quem está rodando
	@bash scripts/local/status.sh

local-logs: ## tail -F dos logs em logs/local/
	@bash scripts/local/tail.sh

local-restart: local-down local-up ## reinicia (down + up)

# ---- atalhos de debug (foreground, sem PID/log) -------------------------

local-dashboard: ## Streamlit em foreground
	DASHBOARD_DATA_MODE=local AUTH_ENABLED=false \
	PYTHONPATH=src:. python -m streamlit run src/dashboard/app_local.py \
	  --server.address 127.0.0.1 --server.port 8501

local-grease: ## API grease em foreground (--reload)
	GREASE_REQUIRE_TOKEN=false \
	PYTHONPATH=src:. python -m uvicorn src.api.grease_ingest_api:app \
	  --host 127.0.0.1 --port 8000 --reload

local-condition: ## API condition em foreground (--reload)
	CONDITION_REQUIRE_TOKEN=false \
	PYTHONPATH=src:. python -m uvicorn src.api.condition_ingest_api:app \
	  --host 127.0.0.1 --port 8001 --reload

local-caddy: ## Caddy em foreground
	caddy run --config deploy/local/Caddyfile.local --adapter caddyfile
