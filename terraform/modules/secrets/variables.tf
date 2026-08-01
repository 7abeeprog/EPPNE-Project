variable "environment" {}
variable "region" {}
variable "rds_endpoint" {}
variable "redis_endpoint" {}
variable "db_username" { sensitive = true }
variable "db_password" { sensitive = true }
variable "db_name" {}
variable "secret_key" { sensitive = true }
variable "s3_access_key" { sensitive = true }
variable "s3_secret_key" { sensitive = true }