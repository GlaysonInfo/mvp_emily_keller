# =====================================================================
# OIDC GitHub Actions -> AWS (sem segredos de longa duração no repositório)
# Cria o provedor OIDC e um IAM Role assumível apenas pelos workflows
# do repositório informado, com permissão mínima para publicar o site.
#
#   cd infra/github-oidc
#   terraform init
#   terraform apply -var="github_owner=SEU_USUARIO_OU_ORG" \
#                   -var="github_repo=AutomacaoAPI" \
#                   -var="site_bucket=SEU-BUCKET-DO-SITE" \
#                   -var="cloudfront_distribution_arn=arn:aws:cloudfront::<acct>:distribution/<id>"
# =====================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# Provedor OIDC do GitHub (criar apenas uma vez por conta AWS).
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  # Thumbprint da CA do GitHub Actions OIDC.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Restringe a assunção do role ao repositório (qualquer branch/ambiente).
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_owner}/${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "deploy_site" {
  name               = "gha-deploy-site-${var.github_repo}"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "deploy_site" {
  statement {
    sid     = "SiteBucketWrite"
    effect  = "Allow"
    actions = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetObject"]
    resources = [
      "arn:aws:s3:::${var.site_bucket}",
      "arn:aws:s3:::${var.site_bucket}/*",
    ]
  }

  statement {
    sid       = "CloudFrontInvalidate"
    effect    = "Allow"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [var.cloudfront_distribution_arn]
  }
}

resource "aws_iam_role_policy" "deploy_site" {
  name   = "deploy-site-min"
  role   = aws_iam_role.deploy_site.id
  policy = data.aws_iam_policy_document.deploy_site.json
}
