output "bucket_name" {
  value       = aws_s3_bucket.site.bucket
  description = "Bucket do site (use no workflow / OIDC)"
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.site.id
  description = "ID da distribuicao (para invalidacao no deploy)"
}

output "cloudfront_distribution_arn" {
  value       = aws_cloudfront_distribution.site.arn
  description = "ARN da distribuicao (use no infra/github-oidc)"
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.site.domain_name
  description = "Aponte o DNS do dominio (CNAME/ALIAS) para este host"
}
