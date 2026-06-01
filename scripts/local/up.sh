#!/usr/bin/env bash
# Sobe APIs FastAPI + Streamlit + Caddy localmente, em background.
# PIDs em .pids/  Logs em logs/local/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PIDS_DIR="$ROOT/.pids"
LOGS_DIR="$ROOT/logs/local"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

# Python: usa o venv do projeto se existir (Linux ou Windows); senão, do PATH.
PY=""
for cand in "$ROOT/.venv/bin/python" "$ROOT/.venv/Scripts/python.exe"; do
	if [ -x "$cand" ]; then PY="$cand"; break; fi
done
[ -n "$PY" ] || PY="$(command -v python3 || command -v python)" || {
	echo "ERRO: Python não encontrado no PATH" >&2; exit 1; }

# Ambiente local: sem AWS, sem token (a API tem fail-closed por padrão).
export PYTHONPATH="$ROOT/src:$ROOT:${PYTHONPATH:-}"
export DASHBOARD_DATA_MODE="${DASHBOARD_DATA_MODE:-local}"
export AUTH_ENABLED="${AUTH_ENABLED:-false}"
export GREASE_REQUIRE_TOKEN="${GREASE_REQUIRE_TOKEN:-false}"
export CONDITION_REQUIRE_TOKEN="${CONDITION_REQUIRE_TOKEN:-false}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

start_bg() {
	local name="$1"; shift
	local pid_file="$PIDS_DIR/$name.pid"
	local log_file="$LOGS_DIR/$name.log"
	if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
		echo "[$name] já rodando (PID $(cat "$pid_file"))"
		return 0
	fi
	echo "[$name] iniciando -> $log_file"
	nohup "$@" >>"$log_file" 2>&1 &
	echo $! > "$pid_file"
}

# 1) API graxa
start_bg grease-api "$PY" -m uvicorn src.api.grease_ingest_api:app \
	--host 127.0.0.1 --port 8000

# 2) API condição
start_bg condition-api "$PY" -m uvicorn src.api.condition_ingest_api:app \
	--host 127.0.0.1 --port 8001

# 3) Dashboard Streamlit (entrypoint local)
start_bg dashboard "$PY" -m streamlit run src/dashboard/app_local.py \
	--server.address 127.0.0.1 --server.port 8501 \
	--server.headless true --browser.gatherUsageStats false

# 4) Caddy (reverse proxy unificando em 8080)
#    Procura nesta ordem: $CADDY_BIN (override) -> caddy no PATH -> locais comuns
CADDYFILE="$ROOT/deploy/local/Caddyfile.local"
CADDY=""
if [ -n "${CADDY_BIN:-}" ] && [ -x "$CADDY_BIN" ]; then
	CADDY="$CADDY_BIN"
elif command -v caddy >/dev/null 2>&1; then
	CADDY="$(command -v caddy)"
else
	for c in \
		"$HOME/Downloads/caddy.exe" \
		"$HOME/Downloads/caddy_windows_amd64.exe" \
		"$HOME/Downloads/caddy_windows_amd64" \
		"$HOME/scoop/shims/caddy.exe" \
		"$HOME/scoop/apps/caddy/current/caddy.exe" \
		"/c/ProgramData/chocolatey/bin/caddy.exe" \
		"/c/Program Files/Caddy/caddy.exe" \
		"$HOME/AppData/Local/Programs/Caddy/caddy.exe" \
		"$HOME/AppData/Local/Microsoft/WinGet/Links/caddy.exe"; do
		if [ -x "$c" ]; then CADDY="$c"; break; fi
	done
fi

if [ -n "$CADDY" ]; then
	echo "[caddy] usando: $CADDY"
	start_bg caddy "$CADDY" run --config "$CADDYFILE" --adapter caddyfile
else
	cat <<-EOF
		[caddy] AVISO: Caddy não encontrado.
		        Os serviços subiram, mas sem o reverse proxy.
		        Acesse direto:
		          dashboard      -> http://127.0.0.1:8501
		          grease  health -> http://127.0.0.1:8000/grease/health
		          cond.   health -> http://127.0.0.1:8001/condition/health
		        Solução rápida (sem mexer no PATH):
		          export CADDY_BIN=/caminho/para/seu/caddy_windows_amd64.exe
		          make local-restart
		        Ou instale via gestor de pacote:
		          macOS:   brew install caddy
		          Windows: scoop install caddy   (ou choco install caddy)
		          Linux:   https://caddyserver.com/docs/install
	EOF
fi

sleep 2

cat <<EOF

================================================================
  Sentinela Industrial — ambiente local
  Painel:                  http://localhost:8080/
  /grease/health:          http://localhost:8080/grease/health
  /condition/health:       http://localhost:8080/condition/health
  Logs:    $LOGS_DIR
  Parar:   make local-down   (ou bash scripts/local/down.sh)
  Status:  make local-status
================================================================
EOF
