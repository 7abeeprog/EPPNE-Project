# .ai-generated/terraform/modules/iam/main.tf

# 🔥 جلب Account ID تلقائياً
data "aws_caller_identity" "current" {}

# 🔥 جلب OIDC Provider من EKS Cluster (يعتمد على أن EKS تم إنشاؤه)
data "aws_eks_cluster" "cluster" {
  name = "eppne-${var.environment}-cluster"
}

data "aws_iam_openid_connect_provider" "cluster" {
  url = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}

# ---- دور Backend ----
resource "aws_iam_role" "backend_role" {
  name = "eppne-${var.environment}-backend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.cluster.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer}:sub" = "system:serviceaccount:default:backend-sa"
          }
        }
      }
    ]
  })
  tags = { Environment = var.environment }
}

resource "aws_iam_policy" "backend_policy" {
  name = "eppne-${var.environment}-backend-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:eppne/${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::eppne-${var.environment}-media/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backend_policy_attach" {
  role       = aws_iam_role.backend_role.name
  policy_arn = aws_iam_policy.backend_policy.arn
}