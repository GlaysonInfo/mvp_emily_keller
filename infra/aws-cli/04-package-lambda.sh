#!/usr/bin/env bash
set -euo pipefail

rm -rf build/lambda
mkdir -p build/lambda

cp -r src/aws_lambdas build/lambda/

(
  cd build/lambda
  zip -r ingest_lambda.zip aws_lambdas
)

echo "Lambda package ready: build/lambda/ingest_lambda.zip"

