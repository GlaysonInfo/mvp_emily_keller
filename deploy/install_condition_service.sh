#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/opt/automacaoapi}"
DOMAIN="${DOMAIN:-sentinelaindustrial.com.br}"
APP_USER="${APP_USER:-ec2-user}"
SERVICE_NAME="condition-ingest"
ENV_FILE="${APP_DIR}/.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_SNIPPET="/etc/nginx/snippets/condition_ingest_location.conf"
NGINX_CONF="/etc/nginx/conf.d/automacaoapi.conf"

echo "== Condition Ingest Service install =="
echo "APP_DIR: ${APP_DIR}"
echo "DOMAIN: ${DOMAIN}"

if [ ! -d "${APP_DIR}" ]; then
  echo "ERROR: app directory not found: ${APP_DIR}"
  exit 1
fi

cd "${APP_DIR}"

if [ ! -d ".venv" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    python3.11 -m venv .venv
  else
    python3 -m venv .venv
  fi
fi

echo "== Installing Python dependencies =="
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
if [ -f "requirements_condition_api.txt" ]; then
  .venv/bin/python -m pip install -r requirements_condition_api.txt
fi

echo "== Updating ${ENV_FILE} =="
sudo touch "${ENV_FILE}"
sudo chmod 600 "${ENV_FILE}"

set_env() {
  local key="$1"
  local value="$2"
  if sudo grep -q "^${key}=" "${ENV_FILE}"; then
    sudo sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" | sudo tee -a "${ENV_FILE}" >/dev/null
  fi
}

set_env "AWS_REGION" "us-east-1"
set_env "AWS_DEFAULT_REGION" "us-east-1"
set_env "DYNAMODB_STATE_TABLE" "mvp_asset_state_dev"
set_env "CONDITION_HISTORY_TABLE" "condition_history"
set_env "CONDITION_ALERTS_TABLE" "condition_alerts"
set_env "CONDITION_API_HOST" "127.0.0.1"
set_env "CONDITION_API_PORT" "8001"
set_env "PYTHONUNBUFFERED" "1"

if ! sudo grep -q "^CONDITION_ALLOWED_SOURCE_IPS=" "${ENV_FILE}"; then
  echo "CONDITION_ALLOWED_SOURCE_IPS=" | sudo tee -a "${ENV_FILE}" >/dev/null
fi
if ! sudo grep -q "^CONDITION_ALLOWED_ORIGINS=" "${ENV_FILE}"; then
  echo "CONDITION_ALLOWED_ORIGINS=" | sudo tee -a "${ENV_FILE}" >/dev/null
fi

CURRENT_TOKEN="$(sudo grep '^CONDITION_INGEST_TOKEN=' "${ENV_FILE}" | tail -1 | cut -d= -f2- || true)"
if [ -z "${CURRENT_TOKEN}" ]; then
  NEW_TOKEN="$(openssl rand -hex 24)"
  set_env "CONDITION_INGEST_TOKEN" "${NEW_TOKEN}"
  echo "A new CONDITION_INGEST_TOKEN was created in ${ENV_FILE}."
else
  echo "CONDITION_INGEST_TOKEN already exists."
fi

echo "== Installing systemd service =="
sudo cp deploy/condition-ingest.service "${SERVICE_FILE}"
sudo sed -i "s|WorkingDirectory=/opt/automacaoapi|WorkingDirectory=${APP_DIR}|g" "${SERVICE_FILE}"
sudo sed -i "s|EnvironmentFile=/opt/automacaoapi/.env|EnvironmentFile=${ENV_FILE}|g" "${SERVICE_FILE}"
sudo sed -i "s|ExecStart=/opt/automacaoapi/.venv/bin/python|ExecStart=${APP_DIR}/.venv/bin/python|g" "${SERVICE_FILE}"
sudo sed -i "s|User=ec2-user|User=${APP_USER}|g" "${SERVICE_FILE}"
sudo sed -i "s|Group=ec2-user|Group=${APP_USER}|g" "${SERVICE_FILE}"

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "== Waiting for local API =="
sleep 3
curl -fsS http://127.0.0.1:8001/condition/health
echo

echo "== Ensuring Nginx =="
if ! command -v nginx >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y nginx
  else
    sudo yum install -y nginx
  fi
fi
sudo systemctl enable nginx

echo "== Installing Nginx /condition/ snippet =="
sudo mkdir -p /etc/nginx/snippets
sudo cp deploy/nginx_condition_ingest.conf "${NGINX_SNIPPET}"
sudo rm -f /etc/nginx/conf.d/condition_ingest_location.conf

if [ ! -f "${NGINX_CONF}" ]; then
  echo "Creating ${NGINX_CONF}."
  sudo tee "${NGINX_CONF}" >/dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    include ${NGINX_SNIPPET};

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF
else
  echo "Updating ${NGINX_CONF}."
  sudo cp "${NGINX_CONF}" "${NGINX_CONF}.bak.$(date +%Y%m%d%H%M%S)"
  sudo "${APP_DIR}/.venv/bin/python" - <<'PY'
from pathlib import Path
import re

path = Path("/etc/nginx/conf.d/automacaoapi.conf")
text = path.read_text(encoding="utf-8")
include_line = "include /etc/nginx/snippets/condition_ingest_location.conf;"

if include_line not in text:
    pattern = re.compile(r"(?m)^(\s*)location\s+/\s*\{")

    def repl(match):
        indent = match.group(1)
        return f"{indent}{include_line}\n\n{match.group(0)}"

    text, count = pattern.subn(repl, text, count=1)
    if count == 0:
        raise SystemExit("Could not find 'location / {' in /etc/nginx/conf.d/automacaoapi.conf")
    path.write_text(text, encoding="utf-8")
else:
    print("Nginx /condition/ include already exists.")
PY
fi

sudo nginx -t
sudo systemctl reload nginx || sudo systemctl restart nginx

echo "== Final checks =="
curl -fsS -H "Host: ${DOMAIN}" http://127.0.0.1/condition/health
echo
sudo systemctl --no-pager status "${SERVICE_NAME}" || true

echo
echo "Ready."
echo "Public health: https://${DOMAIN}/condition/health"
echo "Public ingest: https://${DOMAIN}/condition/ingest"
echo "Logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo "Token: sudo grep CONDITION_INGEST_TOKEN ${ENV_FILE}"
