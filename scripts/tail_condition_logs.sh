#!/usr/bin/env bash
set -euo pipefail

sudo journalctl -u condition-ingest -f
