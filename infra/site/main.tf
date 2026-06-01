# =====================================================================
# Vitrine institucional: S3 (privado) + CloudFront (OAC) + WAF + URLs amigáveis
# Pré-requisito: um certificado ACM VALIDADO em us-east-1 para o domínio
# (passe o ARN em acm_certificate_arn). CloudFront exige cert em us-east-1.
#
#   cd infra/site
#   terraform init
#   terraform apply \
#     -var="site_bucket=sentinela-site-prod" \
#     -var="domain=sentinelaindustrial.com.br" \
#     -var="acm_certificate_arn=arn:aws:acm:us-east-1:<acct>:certificate/<id>"
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

# WAFv2 com escopo CLOUDFRONT precisa estar em us-east-1.
provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}

# ---------------- S3 (privado) ----------------
resource "aws_s3_bucket" "site" {
  bucket = var.site_bucket
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------- WAF (rate limit + regras gerenciadas) ----------------
resource "aws_wafv2_web_acl" "site" {
  provider    = aws.use1
  name        = "sentinela-site"
  scope       = "CLOUDFRONT"
  default_action { allow {} }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "sentinela-site"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "rate-limit"
    priority = 1
    action { block {} }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "aws-common"
    priority = 2
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "aws-common"
      sampled_requests_enabled   = true
    }
  }
}

# ---------------- CloudFront ----------------
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "sentinela-site-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# URLs amigáveis: /pagina/ -> /pagina/index.html
resource "aws_cloudfront_function" "rewrite_index" {
  name    = "sentinela-rewrite-index"
  runtime = "cloudfront-js-2.0"
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;
      if (uri.endsWith('/')) { request.uri += 'index.html'; }
      else if (!uri.includes('.')) { request.uri += '/index.html'; }
      return request;
    }
  EOT
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  default_root_object = "index.html"
  aliases             = [var.domain]
  web_acl_id          = aws_wafv2_web_acl.site.arn

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # CachingOptimized (policy gerenciada da AWS)
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.rewrite_index.arn
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# ---------------- Bucket policy: só o CloudFront lê ----------------
data "aws_iam_policy_document" "site" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site.json
}
