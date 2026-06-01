variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_owner" {
  description = "Usuario ou organizacao dono do repositorio no GitHub"
  type        = string
}

variable "github_repo" {
  description = "Nome do repositorio (ex.: AutomacaoAPI)"
  type        = string
  default     = "AutomacaoAPI"
}

variable "site_bucket" {
  description = "Nome do bucket S3 do site institucional"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = "ARN da distribuicao CloudFront do site (para invalidacao)"
  type        = string
}

variable "app_instance_tags" {
  description = "Valores permitidos da tag App nas instancias do app (staging/prod)"
  type        = list(string)
  default     = ["sentinela-staging", "sentinela-production"]
}
