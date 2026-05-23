#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

mkdir -p build/aws

cat > build/aws/alert-event-pattern.json <<'JSON'
{
  "source": ["condition-monitoring.ingestion"],
  "detail-type": ["TelemetryNormalized"]
}
JSON

ALERT_LAMBDA_ARN="$(aws lambda get-function \
  --function-name "$ALERT_LAMBDA_NAME" \
  --query Configuration.FunctionArn \
  --output text \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE")"

RULE_ARN="$(aws events put-rule \
  --name "$ALERT_EVENT_RULE_NAME" \
  --event-pattern file://build/aws/alert-event-pattern.json \
  --event-bus-name "$EVENT_BUS" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query RuleArn \
  --output text)"

aws events put-targets \
  --rule "$ALERT_EVENT_RULE_NAME" \
  --event-bus-name "$EVENT_BUS" \
  --targets "Id=${ALERT_LAMBDA_NAME},Arn=${ALERT_LAMBDA_ARN}" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" >/dev/null

STATEMENT_ID="AllowEventBridgeAlertInvoke-${STAGE}"

if aws lambda get-policy \
  --function-name "$ALERT_LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query Policy \
  --output text 2>/dev/null | grep -q "$STATEMENT_ID"; then
  echo "Lambda permission already exists: $STATEMENT_ID"
else
  aws lambda add-permission \
    --function-name "$ALERT_LAMBDA_NAME" \
    --statement-id "$STATEMENT_ID" \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "$RULE_ARN" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" >/dev/null

  echo "Lambda permission added: $STATEMENT_ID"
fi

echo "EventBridge alert rule ready: $ALERT_EVENT_RULE_NAME -> $ALERT_LAMBDA_NAME"
