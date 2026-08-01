# .ai-generated/terraform/variables.tf

variable "aws_region" {
  description = "منطقة AWS"
  default     = "us-east-1"
}

variable "environment" {
  description = "اسم البيئة (prod, staging, dev)"
  default     = "prod"
}

# ---------- الشبكات ----------
variable "vpc_cidr" {
  description = "نطاق IP الخاص بـ VPC"
  default     = "10.0.0.0/16"
}

# ---------- EKS ----------
variable "node_instance_types" {
  description = "أنواع مثيلات EC2 لعقد EKS"
  type        = list(string)
  default     = ["c6g.xlarge", "c6i.xlarge"] # ✅ يوصى باستخدام Graviton أو Intel الحديثة
}

variable "desired_capacity" {
  description = "العدد الابتدائي لعقد EKS (يجب أن يكون >= 3 لتوزيع Pods)"
  default     = 3
}

# ---------- RDS ----------
variable "db_instance_class" {
  description = "نوع مثيل RDS (يوصى بـ db.r6g.xlarge على الأقل)"
  default     = "db.r6g.xlarge"
}

variable "db_username" {
  description = "اسم مستخدم قاعدة البيانات"
  sensitive   = true
  default     = "eppne_admin"
}

variable "db_password" {
  description = "كلمة مرور قاعدة البيانات"
  sensitive   = true
}

variable "db_name" {
  description = "اسم قاعدة البيانات"
  default     = "eppne"
}

# ---------- ElastiCache ----------
variable "redis_node_type" {
  description = "نوع مثيل Redis (يوصى بـ cache.r6g.large)"
  default     = "cache.r6g.large"
}

# ---------- الأسرار (للتهيئة الأولية) ----------
variable "secret_key" {
  description = "مفتاح JWT السري (يجب تغييره)"
  sensitive   = true
  default     = "CHANGE_ME_PROD_SECRET_KEY_32_CHARS_MINIMUM"
}

variable "s3_access_key" {
  description = "مفتاح وصول AWS S3"
  sensitive   = true
  default     = "CHANGE_ME"
}

variable "s3_secret_key" {
  description = "مفتاح سري AWS S3"
  sensitive   = true
  default     = "CHANGE_ME"
}