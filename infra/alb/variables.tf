variable "region" {
  description = "Regiao do ALB (mesma da instancia e do certificado ACM regional)"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC onde ficam o ALB e a instancia"
  type        = string
}

variable "public_subnet_ids" {
  description = "Subnets publicas para o ALB (>= 2 em AZs diferentes)"
  type        = list(string)
}

variable "instance_id" {
  description = "ID da instancia EC2 do app (alvo dos target groups)"
  type        = string
}

variable "certificate_arn" {
  description = "ARN do certificado ACM (na regiao do ALB) para app.sentinelaindustrial.com.br"
  type        = string
}

variable "user_pool_arn" {
  description = "ARN do User Pool do Cognito"
  type        = string
}

variable "user_pool_client_id" {
  description = "App Client do Cognito (callback https://app.../oauth2/idpresponse)"
  type        = string
}

variable "user_pool_domain" {
  description = "Prefixo do dominio do Hosted UI do Cognito"
  type        = string
}

variable "web_acl_arn" {
  description = "ARN de um Web ACL regional (WAFv2) para associar ao ALB; vazio = nao associa"
  type        = string
  default     = ""
}
