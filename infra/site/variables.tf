variable "region" {
  description = "Regiao do bucket S3 do site"
  type        = string
  default     = "us-east-1"
}

variable "site_bucket" {
  description = "Nome do bucket S3 (globalmente unico)"
  type        = string
}

variable "domain" {
  description = "Dominio da vitrine"
  type        = string
  default     = "sentinelaindustrial.com.br"
}

variable "acm_certificate_arn" {
  description = "ARN do certificado ACM (us-east-1) ja validado para o dominio"
  type        = string
}
