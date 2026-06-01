#!/usr/bin/env bash
# Lista o estado de cada processo registrado em .pids/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIDS_DIR="$ROOT/.pids"

if [ ! -d "$PIDS_DIR" ] || [ -z "$(ls -A "$PIDS_DIR" 2>/dev/null)" ]; then
	echo "Nada rodando."
	exit 0
fi

printf "%-16s %-8s %s\n" "SERVIÇO" "PID" "ESTADO"
printf -- "----------------------------------------\n"

for pid_file in "$PIDS_DIR"/*.pid; do
	[ -f "$pid_file" ] || continue
	name="$(basename "$pid_file" .pid)"
	pid="$(cat "$pid_file" 2>/dev/null || echo)"
	if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
		printf "%-16s %-8s %s\n" "$name" "$pid" "rodando"
	else
		printf "%-16s %-8s %s\n" "$name" "${pid:-?}" "parado"
	fi
done
