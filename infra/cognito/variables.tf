variable "region" {
  description = "Regiao AWS"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_domain" {
  description = "Dominio da aplicacao (subdominio do app, atras do login)"
  type        = string
  default     = "app.sentinelaindustrial.com.br"
}

variable "hosted_ui_domain_prefix" {
  description = "Prefixo do dominio do Hosted UI do Cognito (precisa ser unico na regiao)"
  type        = string
  default     = "sentinela-industrial-login"
}
