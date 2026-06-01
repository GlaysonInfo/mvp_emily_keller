#!/usr/bin/env bash
# Para todos os processos locais iniciados por up.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIDS_DIR="$ROOT/.pids"

if [ ! -d "$PIDS_DIR" ] || [ -z "$(ls -A "$PIDS_DIR" 2>/dev/null)" ]; then
	echo "Nada para parar."
	exit 0
fi

for pid_file in "$PIDS_DIR"/*.pid; do
	[ -f "$pid_file" ] || continue
	name="$(basename "$pid_file" .pid)"
	pid="$(cat "$pid_file" 2>/dev/null || echo)"
	if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
		echo "[$name] parando PID $pid"
		kill "$pid" 2>/dev/null || true
		for _ in 1 2 3 4 5; do
			kill -0 "$pid" 2>/dev/null || break
			sleep 1
		done
		if kill -0 "$pid" 2>/dev/null; then
			echo "[$name] forçando kill -9 PID $pid"
			kill -9 "$pid" 2>/dev/null || true
		fi
	else
		echo "[$name] (já parado)"
	fi
	rm -f "$pid_file"
done

echo "Tudo parado."
