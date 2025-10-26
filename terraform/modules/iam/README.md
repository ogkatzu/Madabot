# IAM Module

This module creates IAM roles with attached policies for AWS services, primarily Lambda functions.

## Features

- Creates IAM roles with service-specific assume role policies
- Attaches AWS managed policies
- Supports inline policies for custom permissions
- Follows least-privilege security principles

## Usage

```hcl
module "lambda_role" {
  source = "./modules/iam"

  role_name = "my-lambda-role"
  service   = "lambda.amazonaws.com"

  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  inline_policies = [
    {
      name = "custom-permissions"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "s3:GetObject"
            ]
            Resource = "arn:aws:s3:::my-bucket/*"
          }
        ]
      })
    }
  ]

  tags = {
    Environment = "dev"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| role_name | Name of the IAM role | string | n/a | yes |
| service | AWS service that will assume this role | string | "lambda.amazonaws.com" | no |
| policy_arns | List of AWS managed policy ARNs | list(string) | [] | no |
| inline_policies | List of inline policies | list(object) | [] | no |
| tags | Tags to apply to the role | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| role_arn | ARN of the IAM role |
| role_name | Name of the IAM role |
| role_id | ID of the IAM role |