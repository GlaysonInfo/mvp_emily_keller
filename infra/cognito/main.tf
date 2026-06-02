# =====================================================================
# AWS Cognito — Portal de acesso da Sentinela Industrial
# Cria: User Pool, 4 grupos (perfis), atributo custom:tenant_id,
# domínio do Hosted UI e um App Client (confidencial) para o oauth2-proxy.
#
#   cd infra/cognito
#   terraform init
#   terraform apply -var="region=us-east-1"
# =====================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_cognito_user_pool" "sentinela" {
  name = "sentinela-industrial-${var.environment}"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # MFA opcional (recomendado para ADMIN_SERVER). Use "ON" para obrigatório.
  mfa_configuration = "OPTIONAL"
  software_token_mfa_configuration {
    enabled = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Atributo que isola o cliente (tenant) de cada usuário.
  schema {
    name                     = "tenant_id"
    attribute_data_type      = "String"
    mutable                  = true
    required                 = false
    string_attribute_constraints {
      min_length = 1
      max_length = 128
    }
  }

  tags = {
    project = "sentinela-industrial"
    env     = var.environment
  }
}

# ---- Perfis (grupos) ----
resource "aws_cognito_user_group" "admin_server" {
  name         = "ADMIN_SERVER"
  user_pool_id = aws_cognito_user_pool.sentinela.id
  description  = "Admin do sistema (toda a plataforma, todos os tenants)"
  precedence   = 1
}

resource "aws_cognito_user_group" "cliente_admin" {
  name         = "CLIENTE_ADMIN"
  user_pool_id = aws_cognito_user_pool.sentinela.id
  description  = "Admin do cliente (usuarios, plantas e contratos do proprio tenant)"
  precedence   = 5
}

resource "aws_cognito_user_group" "cliente_tecnico" {
  name         = "CLIENTE_TECNICO"
  user_pool_id = aws_cognito_user_pool.sentinela.id
  description  = "Tecnico do cliente (configura o proprio tenant)"
  precedence   = 10
}

resource "aws_cognito_user_group" "cliente_operador" {
  name         = "CLIENTE_OPERADOR"
  user_pool_id = aws_cognito_user_pool.sentinela.id
  description  = "Operador do cliente (operacao, sem editar configuracao)"
  precedence   = 20
}

# ---- Domínio do Hosted UI (tela de login) ----
resource "aws_cognito_user_pool_domain" "hosted_ui" {
  domain       = var.hosted_ui_domain_prefix
  user_pool_id = aws_cognito_user_pool.sentinela.id
}

# ---- App Client (confidencial) usado pelo oauth2-proxy ----
resource "aws_cognito_user_pool_client" "app" {
  name         = "sentinela-app-client"
  user_pool_id = aws_cognito_user_pool.sentinela.id

  generate_secret                      = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = ["https://${var.app_domain}/oauth2/callback"]
  logout_urls   = [
    "https://${var.app_domain}/",
    "https://${var.institutional_domain}/",
  ]

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  access_token_validity  = 60
  id_token_validity       = 60
  refresh_token_validity = 8
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "hours"
  }

  # Permite ao app client ler/usar o atributo de tenant.
  read_attributes  = ["email", "custom:tenant_id"]
  write_attributes = ["email", "custom:tenant_id"]
}
