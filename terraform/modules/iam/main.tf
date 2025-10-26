# IAM Role for Lambda execution
resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = var.tags
}

# Trust policy for Lambda service
data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = [var.service]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Attach AWS managed policies
resource "aws_iam_role_policy_attachment" "managed_policies" {
  for_each = toset(var.policy_arns)

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

# Create and attach inline policies
resource "aws_iam_role_policy" "inline_policies" {
  for_each = { for idx, policy in var.inline_policies : policy.name => policy }

  name   = each.value.name
  role   = aws_iam_role.this.id
  policy = each.value.policy
}