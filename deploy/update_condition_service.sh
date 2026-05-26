#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/opt/automacaoapi}"
BRANCH="${BRANCH:-sprint-5/dashboard-mvp}"
SERVICE_NAME="condition-ingest"

echo "== Updating Condition Ingest Service =="
cd "${APP_DIR}"

echo "== Pulling ${BRANCH} =="
git fetch origin "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

echo "== Installing dependencies =="
.venv/bin/python -m pip install -e .
if [ -f "requirements_condition_api.txt" ]; then
  .venv/bin/python -m pip install -r requirements_condition_api.txt
fi

echo "== Restarting ${SERVICE_NAME} =="
sudo systemctl restart "${SERVICE_NAME}"
sleep 3

curl -fsS http://127.0.0.1:8001/condition/health
echo
sudo systemctl --no-pager status "${SERVICE_NAME}" || true
