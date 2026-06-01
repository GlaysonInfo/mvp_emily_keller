# =====================================================================
# ALB + Cognito nativo (substitui o oauth2-proxy; mantém o nginx)
# Fluxo:  Usuário -> ALB (authenticate-cognito) -> nginx (instância) -> app
# O ALB injeta x-amzn-oidc-data (lido por src/dashboard/auth/identity.py em
# AUTH_PROVIDER=alb). As rotas de ingestão (/grease, /condition) passam SEM
# autenticação Cognito (protegidas por token na própria API).
# O nginx (deploy/alb/nginx_app_alb.conf) roteia por caminho para os
# serviços locais (8501/8000/8001), que permanecem em 127.0.0.1.
#
#   cd infra/alb && terraform init && terraform apply \
#     -var="vpc_id=vpc-..." -var='public_subnet_ids=["subnet-a","subnet-b"]' \
#     -var="instance_id=i-..." -var="certificate_arn=arn:aws:acm:<regiao>:...:certificate/..." \
#     -var="user_pool_arn=arn:aws:cognito-idp:...:userpool/..." \
#     -var="user_pool_client_id=..." -var="user_pool_domain=sentinela-industrial-login"
#
# IMPORTANTE: o App Client do Cognito precisa ter a callback
#   https://app.sentinelaindustrial.com.br/oauth2/idpresponse
# (URL usada pelo ALB; diferente da do oauth2-proxy).
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

# ---------------- Security Groups ----------------
resource "aws_security_group" "alb" {
  name        = "sentinela-alb"
  description = "ALB publico (443/80)"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTP (redireciona p/ HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# A instancia (nginx) aceita trafego SOMENTE do ALB. Anexe este SG na EC2 e
# remova qualquer ingress publico nas portas do app.
resource "aws_security_group" "instance" {
  name        = "sentinela-app-instance"
  description = "App/nginx: aceita apenas o ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "nginx (HTTP) a partir do ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------- ALB + target group (nginx) ----------------
resource "aws_lb" "app" {
  name               = "sentinela-app"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "app" {
  name        = "sentinela-app"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    path                = "/healthz"
    matcher             = "200-399"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  # Streamlit usa WebSocket/sessão: ative stickiness.
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = var.instance_id
  port             = 80
}

# ---------------- Listeners ----------------
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  # Padrao: autentica no Cognito e encaminha ao nginx (dashboard).
  default_action {
    type  = "authenticate-cognito"
    order = 1
    authenticate_cognito {
      user_pool_arn              = var.user_pool_arn
      user_pool_client_id        = var.user_pool_client_id
      user_pool_domain           = var.user_pool_domain
      scope                      = "openid email profile"
      session_cookie_name        = "AWSELBAuthSessionCookie"
      on_unauthenticated_request = "authenticate"
    }
  }
  default_action {
    type             = "forward"
    order            = 2
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Ingestao das APIs: SEM autenticacao Cognito (token na propria API).
resource "aws_lb_listener_rule" "grease" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
  condition {
    path_pattern { values = ["/grease", "/grease/*"] }
  }
}

resource "aws_lb_listener_rule" "condition" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 20
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
  condition {
    path_pattern { values = ["/condition", "/condition/*"] }
  }
}

# ---------------- WAF regional (opcional) ----------------
resource "aws_wafv2_web_acl_association" "alb" {
  count        = var.web_acl_arn == "" ? 0 : 1
  resource_arn = aws_lb.app.arn
  web_acl_arn  = var.web_acl_arn
}
