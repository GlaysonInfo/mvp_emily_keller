output "deploy_role_arn" {
  description = "ARN do role a usar no GitHub Actions (variavel AWS_ROLE_ARN)"
  value       = aws_iam_role.deploy_site.arn
}

output "oidc_provider_arn" {
  description = "ARN do provedor OIDC do GitHub"
  value       = aws_iam_openid_connect_provider.github.arn
}
