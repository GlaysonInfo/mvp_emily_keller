#!/usr/bin/env bash
set -euo pipefail
sudo journalctl -u grease-ingest -f -n 100
