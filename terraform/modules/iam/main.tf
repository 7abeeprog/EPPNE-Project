# .ai-generated/terraform/modules/iam/main.tf
# دور IAM لـ Backend Service Account
resource "aws_iam_role" "backend_role" {
  name = "eppne-${var.environment}-backend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/XXXXX"  # TODO: استبدل بعد إنشاء EKS
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/XXXXX:sub" = "system:serviceaccount:default:backend-sa"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
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
        Resource = "arn:aws:secretsmanager:${var.region}:ACCOUNT_ID:secret:eppne/${var.environment}/*"  # TODO: استبدل ACCOUNT_ID
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

# دور IAM لـ AI Service Account
resource "aws_iam_role" "ai_role" {
  name = "eppne-${var.environment}-ai-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/XXXXX"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/XXXXX:sub" = "system:serviceaccount:default:ai-sa"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# دور IAM لـ Frontend Service Account (للملفات الثابتة)
resource "aws_iam_role" "frontend_role" {
  name = "eppne-${var.environment}-frontend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/XXXXX"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/XXXXX:sub" = "system:serviceaccount:default:frontend-sa"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}