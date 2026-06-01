#!/usr/bin/env bash
# =====================================================================
# Deploy do app na instância (executado via SSM pelo GitHub Actions).
# Idempotente: atualiza o código para um ref, reinstala dependências e
# reinicia os serviços (APIs de ingestão + dashboard Streamlit).
#
# Pré-requisitos na instância:
#   - repositório clonado em /opt/automacaoapi (remote 'origin')
#   - virtualenv em /opt/automacaoapi/.venv
#   - units instaladas: grease-ingest, condition-ingest, streamlit-dashboard
#   - /opt/automacaoapi/.env com tokens e AUTH_ENABLED
#
# Variáveis:
#   DEPLOY_REF  commit/branch a implantar (default: main)
#   APP_DIR     diretório do app (default: /opt/automacaoapi)
#   APP_USER    usuário dono do código (default: ec2-user)
# =====================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/automacaoapi}"
APP_USER="${APP_USER:-ec2-user}"
DEPLOY_REF="${DEPLOY_REF:-main}"

echo ">> Deploy ref=${DEPLOY_REF} em ${APP_DIR}"
cd "$APP_DIR"

# Atualiza o código de forma determinística.
sudo -u "$APP_USER" git fetch --all --prune
sudo -u "$APP_USER" git reset --hard "${DEPLOY_REF}"

# Dependências (sem tocar pacotes do sistema).
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/pip" install -r requirements.txt

# Recarrega units (caso tenham mudado) e reinicia serviços.
sudo systemctl daemon-reload
for svc in grease-ingest condition-ingest streamlit-dashboard; do
  if systemctl list-unit-files | grep -q "^${svc}.service"; then
    echo ">> reiniciando ${svc}"
    sudo systemctl restart "${svc}"
  else
    echo ">> aviso: serviço ${svc} não instalado (pulando)"
  fi
done

# Smoke test local das APIs (sem expor portas externas).
echo ">> smoke test /health"
curl -fsS http://127.0.0.1:8000/grease/health  >/dev/null && echo "grease OK"     || echo "grease FALHOU"
curl -fsS http://127.0.0.1:8001/condition/health >/dev/null && echo "condition OK" || echo "condition FALHOU"

echo ">> Deploy concluído."
