#!/usr/bin/env bash
# Diagnóstico do ambiente local. Não inicia nada — só verifica.
# Critério: sai 0 se tudo OK; 1 se faltar algo.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FAILED=0
ok()   { printf "  [OK]   %s\n" "$*"; }
warn() { printf "  [WARN] %s\n" "$*"; }
fail() { printf "  [FAIL] %s\n" "$*"; FAILED=1; }
hdr()  { printf "\n== %s ==\n" "$*"; }

# ---- 1. Sistema -------------------------------------------------------
hdr "Sistema / shell"
printf "  OSTYPE=%s   uname=%s   BASH=%s\n" \
	"${OSTYPE:-?}" "$(uname -s 2>/dev/null || echo ?)" "${BASH_VERSION:-?}"

# ---- 2. Python --------------------------------------------------------
hdr "Python"
PY=""
for cand in "$ROOT/.venv/bin/python" "$ROOT/.venv/Scripts/python.exe"; do
	if [ -x "$cand" ]; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
	PY="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
fi
if [ -n "$PY" ] && "$PY" --version >/dev/null 2>&1; then
	ok "encontrado: $PY"
	"$PY" --version 2>&1 | sed 's/^/         /'
else
	fail "Python não encontrado. Procurei: .venv/bin/python, .venv/Scripts/python.exe, python3, python"
	PY=""
fi

# ---- 3. Dependências --------------------------------------------------
hdr "Dependências Python (streamlit / uvicorn / fastapi)"
if [ -n "$PY" ]; then
	for mod in streamlit uvicorn fastapi; do
		ver="$("$PY" -c "import $mod; print(getattr($mod,'__version__','?'))" 2>/dev/null || true)"
		if [ -n "$ver" ]; then
			ok "$mod ($ver)"
		else
			fail "$mod NÃO instalado. Rode: $PY -m pip install -r requirements.txt"
		fi
	done
else
	warn "pulado (sem Python)"
fi

# ---- 4. Caddy ---------------------------------------------------------
hdr "Caddy"
CADDY=""
# 1) Override explícito via CADDY_BIN (ex.: para apontar o binário baixado direto)
if [ -n "${CADDY_BIN:-}" ] && [ -x "$CADDY_BIN" ]; then
	CADDY="$CADDY_BIN"
	ok "CADDY_BIN definido: $CADDY"
# 2) caddy normal no PATH
elif command -v caddy >/dev/null 2>&1; then
	CADDY="$(command -v caddy)"
	ok "no PATH: $CADDY"
else
	warn "caddy NÃO está no PATH. Procurando o binário em locais comuns..."
	CANDIDATES=(
		# Downloads (inclui o binário avulso do release oficial)
		"$HOME/Downloads/caddy.exe"
		"$HOME/Downloads/caddy_windows_amd64.exe"
		"$HOME/Downloads/caddy_windows_amd64"
		# Gestores de pacote no Windows
		"$HOME/scoop/shims/caddy.exe"
		"$HOME/scoop/apps/caddy/current/caddy.exe"
		"/c/ProgramData/chocolatey/bin/caddy.exe"
		"/c/Program Files/Caddy/caddy.exe"
		"$HOME/AppData/Local/Programs/Caddy/caddy.exe"
		"$HOME/AppData/Local/Microsoft/WinGet/Links/caddy.exe"
	)
	for c in "${CANDIDATES[@]}"; do
		if [ -x "$c" ]; then
			CADDY="$c"
			ok "encontrado em: $c"
			warn "Para esta sessão:  export CADDY_BIN=\"$c\""
			warn "Ou renomeie/copie como caddy.exe num diretório do PATH (ex.: ~/bin)."
			break
		fi
	done
	if [ -z "$CADDY" ]; then
		fail "Caddy não encontrado em locais comuns."
		fail "  Procurei em: ${CANDIDATES[*]}"
		fail "  Solução rápida: export CADDY_BIN=/caminho/completo/para/seu_caddy.exe"
		fail "  Solução permanente: rename para caddy.exe e mova para um diretório do PATH."
	fi
fi
# Verificação de versão (em separado, com o CADDY descoberto)
if [ -n "$CADDY" ]; then
	"$CADDY" version 2>/dev/null | head -1 | sed 's/^/         /'
fi

# ---- 5. Caddyfile válido? --------------------------------------------
if [ -n "$CADDY" ]; then
	hdr "Caddyfile (deploy/local/Caddyfile.local)"
	if "$CADDY" validate --config deploy/local/Caddyfile.local --adapter caddyfile >/dev/null 2>&1; then
		ok "Caddyfile válido"
	else
		fail "Caddyfile com erro. Rode para ver: $CADDY validate --config deploy/local/Caddyfile.local --adapter caddyfile"
	fi
fi

# ---- 6. Portas livres ------------------------------------------------
hdr "Portas (8080 / 8501 / 8000 / 8001)"
if [ -n "$PY" ]; then
	for p in 8080 8501 8000 8001; do
		if "$PY" -c "import socket,sys
try: s=socket.socket(); s.bind(('127.0.0.1',$p)); s.close()
except OSError: sys.exit(1)" 2>/dev/null; then
			ok "porta $p livre"
		else
			fail "porta $p OCUPADA. Rode 'make local-down' ou descubra quem está usando."
		fi
	done
else
	warn "pulado (sem Python para sondar)"
fi

# ---- Resumo -----------------------------------------------------------
echo ""
if [ "$FAILED" -eq 0 ]; then
	echo "RESULTADO: tudo verde. Suba com:  make local-up"
	exit 0
else
	echo "RESULTADO: faltam itens acima. Corrija e rode novamente: make local-check"
	exit 1
fi
