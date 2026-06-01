output "user_pool_id" {
  description = "ID do User Pool"
  value       = aws_cognito_user_pool.sentinela.id
}

output "oidc_issuer_url" {
  description = "Issuer OIDC para o oauth2-proxy (oidc_issuer_url)"
  value       = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.sentinela.id}"
}

output "app_client_id" {
  description = "client_id para o oauth2-proxy"
  value       = aws_cognito_user_pool_client.app.id
}

output "app_client_secret" {
  description = "client_secret para o oauth2-proxy (sensivel)"
  value       = aws_cognito_user_pool_client.app.client_secret
  sensitive   = true
}

output "hosted_ui_domain" {
  description = "Dominio do Hosted UI (tela de login)"
  value       = "${aws_cognito_user_pool_domain.hosted_ui.domain}.auth.${var.region}.amazoncognito.com"
}
