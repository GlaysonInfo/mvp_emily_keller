#!/usr/bin/env bash
# Tail dos logs locais (Ctrl+C para sair).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOGS_DIR="$ROOT/logs/local"

if [ ! -d "$LOGS_DIR" ] || [ -z "$(ls -A "$LOGS_DIR" 2>/dev/null)" ]; then
	echo "Nenhum log em $LOGS_DIR. Suba o ambiente com: make local-up"
	exit 0
fi

exec tail -F "$LOGS_DIR"/*.log
