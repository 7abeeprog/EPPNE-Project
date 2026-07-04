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
    bucket         = "eppne-terraform-state-ACCOUNT_ID"  # TODO: استبدل ACCOUNT_ID
    key            = "eppne/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "eppne-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "./modules/networking"
  region = var.aws_region
  vpc_cidr = var.vpc_cidr
  environment = var.environment
}

module "iam" {
  source = "./modules/iam"
  environment = var.environment
}

module "secrets" {
  source = "./modules/secrets"
  environment = var.environment
  depends_on = [module.iam]
}

module "eks" {
  source = "./modules/eks"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  node_instance_types = var.node_instance_types
  desired_capacity = var.desired_capacity
  depends_on = [module.iam, module.networking]
}

module "rds" {
  source = "./modules/rds"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_instance_class = var.db_instance_class
  db_username = var.db_username
  db_password = var.db_password
  db_name = var.db_name
  depends_on = [module.networking]
}

module "elasticache" {
  source = "./modules/elasticache"
  environment = var.environment
  vpc_id = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  redis_node_type = var.redis_node_type
  depends_on = [module.networking]
}

module "s3" {
  source = "./modules/s3"
  environment = var.environment
}