#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

rm -rf build/lambda
mkdir -p build/lambda

cp -r src/aws_lambdas build/lambda/
cp -r src/rules_engine build/lambda/

(
  cd build/lambda

  if command -v zip >/dev/null 2>&1; then
    zip -r ingest_lambda.zip aws_lambdas rules_engine >/dev/null
  elif command -v python >/dev/null 2>&1; then
    python - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

roots = [Path("aws_lambdas"), Path("rules_engine")]

with ZipFile("ingest_lambda.zip", "w", ZIP_DEFLATED) as archive:
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file():
                archive.write(path, path.as_posix())
PY
  else
    echo "Neither zip nor python was found. Cannot package Lambda." >&2
    exit 1
  fi
)

echo "Lambda package ready: build/lambda/ingest_lambda.zip"
