# .ai-generated/terraform/modules/secrets/main.tf
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "eppne/${var.environment}/secrets"
  tags = { Environment = var.environment }
}

resource "aws_secretsmanager_secret_version" "app_secrets_version" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    "SECRET_KEY" = var.secret_key
    # 🔥 استخدام الـ Endpoints الفعلية التي تم تمريرها من Root Module
    "DATABASE_URL" = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${var.rds_endpoint}:5432/${var.db_name}"
    "REDIS_URL" = "redis://${var.redis_endpoint}:6379/0"
    "S3_ENDPOINT" = "https://s3.${var.region}.amazonaws.com"
    "S3_ACCESS_KEY" = var.s3_access_key
    "S3_SECRET_KEY" = var.s3_secret_key
    "ALGORITHM" = "HS256"
    "ACCESS_TOKEN_EXPIRE_MINUTES" = "10080"
  })
}