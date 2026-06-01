# =====================================================================
# Role IAM para o workflow deploy-app.yml (deploy via SSM).
# Reaproveita o provedor OIDC e o trust definido em main.tf.
# =====================================================================

resource "aws_iam_role" "deploy_app" {
  name               = "gha-deploy-app-${var.github_repo}"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "deploy_app" {
  # Enviar comando apenas com o documento padrão de shell...
  statement {
    sid       = "SsmSendRunShellDoc"
    effect    = "Allow"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.region}::document/AWS-RunShellScript"]
  }

  # ...e somente para instâncias marcadas com a tag App permitida.
  statement {
    sid       = "SsmSendToTaggedInstances"
    effect    = "Allow"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:instance/*"]

    condition {
      test     = "StringLike"
      variable = "aws:ResourceTag/App"
      values   = var.app_instance_tags
    }
  }

  # Consultar o resultado da execução.
  statement {
    sid    = "SsmReadInvocations"
    effect = "Allow"
    actions = [
      "ssm:ListCommandInvocations",
      "ssm:ListCommands",
      "ssm:GetCommandInvocation",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy_app" {
  name   = "deploy-app-ssm-min"
  role   = aws_iam_role.deploy_app.id
  policy = data.aws_iam_policy_document.deploy_app.json
}

output "deploy_app_role_arn" {
  description = "ARN do role de deploy do app (variavel AWS_ROLE_ARN do deploy-app)"
  value       = aws_iam_role.deploy_app.arn
}
