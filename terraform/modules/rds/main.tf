# .ai-generated/terraform/modules/rds/main.tf
resource "aws_db_subnet_group" "main" {
  name       = "eppne-${var.environment}-rds-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags = { Environment = var.environment }
}

resource "aws_security_group" "rds" {
  name        = "eppne-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    # ✅ تم إصلاح الخلل: استخدام CIDR الخاص بالـ VPC بدلاً من متغير مفقود
    cidr_blocks = [var.vpc_cidr]
  }

  tags = { Environment = var.environment }
}

resource "aws_db_parameter_group" "postgres" {
  name   = "eppne-${var.environment}-postgres-params"
  family = "postgres16"

  parameter {
    name  = "max_connections"
    value = "1000"  # متوافق مع DATABASE_POOL_SIZE=100 + MAX_OVERFLOW=200
  }
  parameter {
    name  = "shared_buffers"
    value = "2048MB"  # ✅ تم رفعها من 1024 إلى 2048 لتحسين الأداء
  }
  tags = { Environment = var.environment }
}

resource "aws_db_instance" "main" {
  identifier = "eppne-${var.environment}-postgres"
  engine               = "postgres"
  engine_version       = "16.3"
  instance_class       = var.db_instance_class
  allocated_storage    = 100
  storage_encrypted    = true
  storage_type         = "gp3"
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  port                 = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  multi_az               = true
  publicly_accessible    = false
  deletion_protection    = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "eppne-${var.environment}-final-snapshot"
  parameter_group_name = aws_db_parameter_group.postgres.name

  tags = { Environment = var.environment }
}

# ✅ إخراج الـ Endpoint لاستخدامه في وحدة الأسرار
output "endpoint" {
  value = aws_db_instance.main.endpoint
}