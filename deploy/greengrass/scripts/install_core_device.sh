#!/usr/bin/env bash
set -euo pipefail

: "${DEVICE_BUNDLE_DIR:=.}"
: "${GREENGRASS_ROOT:=/greengrass/v2}"
: "${CERT_TARGET_DIR:=${GREENGRASS_ROOT}/certs}"
: "${GREENGRASS_NUCLEUS_VERSION:=2.17.0}"
: "${GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS:=GreengrassV2TokenExchangeRoleAlias}"

if [[ ! -f "${DEVICE_BUNDLE_DIR}/device.env" ]]; then
  echo "device.env nao encontrado em ${DEVICE_BUNDLE_DIR}." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${DEVICE_BUNDLE_DIR}/device.env"

sudo mkdir -p "$CERT_TARGET_DIR" "$GREENGRASS_ROOT"
sudo cp "${DEVICE_BUNDLE_DIR}/certs/AmazonRootCA1.pem" "$CERT_TARGET_DIR/"
sudo cp "${DEVICE_BUNDLE_DIR}/certs/device.pem.crt" "$CERT_TARGET_DIR/"
sudo cp "${DEVICE_BUNDLE_DIR}/certs/private.pem.key" "$CERT_TARGET_DIR/"
sudo chmod 600 "$CERT_TARGET_DIR/private.pem.key"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y default-jre unzip curl python3 python3-pip
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y java-17-amazon-corretto unzip curl python3 python3-pip
fi

WORK_DIR="/tmp/sentinela-greengrass-install"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

curl -fsSL https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip -o greengrass-nucleus-latest.zip
unzip -q greengrass-nucleus-latest.zip -d GreengrassInstaller

cat > GreengrassInstaller/config.yaml <<EOF
---
system:
  certificateFilePath: "${CERT_TARGET_DIR}/device.pem.crt"
  privateKeyPath: "${CERT_TARGET_DIR}/private.pem.key"
  rootCaPath: "${CERT_TARGET_DIR}/AmazonRootCA1.pem"
  rootpath: "${GREENGRASS_ROOT}"
  thingName: "${THING_NAME}"
services:
  aws.greengrass.Nucleus:
    componentType: "NUCLEUS"
    version: "${GREENGRASS_NUCLEUS_VERSION}"
    configuration:
      awsRegion: "${AWS_REGION}"
      iotRoleAlias: "${GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS}"
      iotDataEndpoint: "${DATA_ENDPOINT}"
      iotCredEndpoint: "${CRED_ENDPOINT}"
      mqtt:
        port: 443
      greengrassDataPlanePort: 443
EOF

sudo -E java -Droot="$GREENGRASS_ROOT" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --init-config ./GreengrassInstaller/config.yaml \
  --component-default-user ggc_user:ggc_group \
  --setup-system-service true

sudo systemctl status greengrass --no-pager || true
sudo ls -la "$GREENGRASS_ROOT"
