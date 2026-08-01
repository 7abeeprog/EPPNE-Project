# .ai-generated/terraform/main.tf
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    # ⚠️ استبدل ACCOUNT_ID برقم حسابك الفعلي في AWS
    bucket         = "eppne-terraform-state-ACCOUNT_ID"
    key            = "eppne/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "eppne-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# 1. الشبكات (VPC, Subnets, NAT)
# ============================================
module "networking" {
  source = "./modules/networking"
  region  = var.aws_region
  vpc_cidr = var.vpc_cidr
  environment = var.environment
}

# ============================================
# 2. الأدوار الأمنية (IAM)
# ============================================
module "iam" {
  source = "./modules/iam"
  environment = var.environment
  oidc_provider_arn = module.eks.oidc_provider_arn # يتم تمريره تلقائياً من وحدة EKS
}

# ============================================
# 3. مجموعة Kubernetes (EKS)
# ============================================
module "eks" {
  source = "./modules/eks"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  node_instance_types = var.node_instance_types
  desired_capacity = var.desired_capacity
  depends_on = [module.iam, module.networking]
}

# ============================================
# 4. قاعدة البيانات (RDS PostgreSQL) - Multi-AZ
# ============================================
module "rds" {
  source = "./modules/rds"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  vpc_cidr = var.vpc_cidr  # ✅ تم تمرير CIDR لاستخدامه في الأمان بدلاً من SG المتغير
  private_subnet_ids = module.networking.private_subnet_ids
  db_instance_class = var.db_instance_class
  db_username = var.db_username
  db_password = var.db_password
  db_name = var.db_name
  depends_on = [module.networking]
}

# ============================================
# 5. الذاكرة المؤقتة (Redis ElastiCache)
# ============================================
module "elasticache" {
  source = "./modules/elasticache"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  redis_node_type = var.redis_node_type
  depends_on = [module.networking]
}

# ============================================
# 6. الأسرار (Secrets Manager) - ✅ ربط تلقائي بـ RDS و Redis
# ============================================
module "secrets" {
  source = "./modules/secrets"
  environment = var.environment
  region = var.aws_region
  # 🔥 تمرير الـ Endpoints الفعلية التي تم إنشاؤها من الوحدات الأخرى
  rds_endpoint = module.rds.endpoint
  redis_endpoint = module.elasticache.endpoint
  db_username = var.db_username
  db_password = var.db_password
  db_name = var.db_name
  secret_key = var.secret_key
  s3_access_key = var.s3_access_key
  s3_secret_key = var.s3_secret_key
  depends_on = [module.rds, module.elasticache]
}

# ============================================
# 7. التخزين (S3)
# ============================================
module "s3" {
  source = "./modules/s3"
  environment = var.environment
}