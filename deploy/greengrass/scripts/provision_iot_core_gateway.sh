#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${THING_NAME:=sentinela-cliente-real-indoor-gateway-01}"
: "${THING_GROUP_NAME:=sentinela-greengrass-gateways}"
: "${POLICY_NAME:=SentinelaGreengrassGatewayPolicy}"
: "${CERT_DIR:=./build/greengrass/${THING_NAME}/certs}"
: "${GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS:=GreengrassV2TokenExchangeRoleAlias}"
: "${GREENGRASS_TOKEN_EXCHANGE_ROLE:=GreengrassV2TokenExchangeRole}"
: "${GREENGRASS_TOKEN_EXCHANGE_POLICY:=GreengrassV2TokenExchangeRoleAccess}"
: "${SENTINELA_GREENGRASS_ARTIFACT_BUCKET:=}"

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
mkdir -p "$CERT_DIR"

DATA_ENDPOINT="$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --region "$AWS_REGION" --query endpointAddress --output text)"
CRED_ENDPOINT="$(aws iot describe-endpoint --endpoint-type iot:CredentialProvider --region "$AWS_REGION" --query endpointAddress --output text)"
TRUST_DOC="$(mktemp)"
cat > "$TRUST_DOC" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "credentials.iot.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name "$GREENGRASS_TOKEN_EXCHANGE_ROLE" \
  --assume-role-policy-document "file://$TRUST_DOC" >/dev/null 2>&1 || true

ACCESS_DOC="$(mktemp)"
cat > "$ACCESS_DOC" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
        "s3:GetBucketLocation"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${SENTINELA_GREENGRASS_ARTIFACT_BUCKET:-sentinela-greengrass-artifacts-placeholder}/*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name "$GREENGRASS_TOKEN_EXCHANGE_POLICY" \
  --policy-document "file://$ACCESS_DOC" >/dev/null 2>&1 || true
TOKEN_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${GREENGRASS_TOKEN_EXCHANGE_POLICY}"
aws iam attach-role-policy \
  --role-name "$GREENGRASS_TOKEN_EXCHANGE_ROLE" \
  --policy-arn "$TOKEN_POLICY_ARN" >/dev/null 2>&1 || true

TOKEN_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${GREENGRASS_TOKEN_EXCHANGE_ROLE}"
aws iot create-role-alias \
  --region "$AWS_REGION" \
  --role-alias "$GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS" \
  --role-arn "$TOKEN_ROLE_ARN" >/dev/null 2>&1 || \
aws iot update-role-alias \
  --region "$AWS_REGION" \
  --role-alias "$GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS" \
  --role-arn "$TOKEN_ROLE_ARN" >/dev/null

echo ">> AWS IoT data endpoint: $DATA_ENDPOINT"
echo ">> AWS IoT credentials endpoint: $CRED_ENDPOINT"

aws iot create-thing --region "$AWS_REGION" --thing-name "$THING_NAME" >/dev/null 2>&1 || true
aws iot create-thing-group --region "$AWS_REGION" --thing-group-name "$THING_GROUP_NAME" >/dev/null 2>&1 || true
aws iot add-thing-to-thing-group --region "$AWS_REGION" --thing-name "$THING_NAME" --thing-group-name "$THING_GROUP_NAME" >/dev/null 2>&1 || true

CERT_JSON="$(aws iot create-keys-and-certificate \
  --region "$AWS_REGION" \
  --set-as-active \
  --certificate-pem-outfile "$CERT_DIR/device.pem.crt" \
  --public-key-outfile "$CERT_DIR/public.pem.key" \
  --private-key-outfile "$CERT_DIR/private.pem.key" \
  --output json)"
CERT_ARN="$(printf '%s' "$CERT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["certificateArn"])')"
CERT_ID="$(printf '%s' "$CERT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["certificateId"])')"

POLICY_DOC="$(mktemp)"
sed \
  -e "s/\${AWS_REGION}/$AWS_REGION/g" \
  -e "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" \
  -e "s/\${GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS}/$GREENGRASS_TOKEN_EXCHANGE_ROLE_ALIAS/g" \
  deploy/greengrass/templates/iot-policy-sentinela-greengrass.json > "$POLICY_DOC"

aws iot create-policy --region "$AWS_REGION" --policy-name "$POLICY_NAME" --policy-document "file://$POLICY_DOC" >/dev/null 2>&1 || true
aws iot attach-policy --region "$AWS_REGION" --policy-name "$POLICY_NAME" --target "$CERT_ARN"
aws iot attach-thing-principal --region "$AWS_REGION" --thing-name "$THING_NAME" --principal "$CERT_ARN"

curl -fsSL https://www.amazontrust.com/repository/AmazonRootCA1.pem -o "$CERT_DIR/AmazonRootCA1.pem"

cat > "./build/greengrass/${THING_NAME}/device.env" <<EOF
AWS_REGION=$AWS_REGION
THING_NAME=$THING_NAME
THING_GROUP_NAME=$THING_GROUP_NAME
DATA_ENDPOINT=$DATA_ENDPOINT
CRED_ENDPOINT=$CRED_ENDPOINT
CERT_ID=$CERT_ID
CERT_ARN=$CERT_ARN
EOF

cat <<EOF

Provisionamento concluido.
Leve ao gateway do cliente a pasta:
  build/greengrass/${THING_NAME}

Ela contem certificados X.509 e device.env. Trate como material sensivel.
EOF
