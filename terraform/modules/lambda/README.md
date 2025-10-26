# Lambda Module

This module creates Lambda functions with automatic code packaging, CloudWatch logs, and optional features like VPC integration and function URLs.

## Features

- Automatic ZIP packaging from source directory
- CloudWatch Logs with configurable retention
- VPC integration support
- Lambda layers support
- Dead letter queue configuration
- X-Ray tracing
- Function URLs with CORS
- Configurable concurrency limits
- Environment variables
- Ephemeral storage configuration

## Usage

### Basic Lambda Function

```hcl
module "simple_lambda" {
  source = "./modules/lambda"

  function_name = "my-function"
  description   = "My Lambda function"
  handler       = "index.handler"
  runtime       = "python3.11"

  source_dir    = "${path.module}/../src/my-function"
  role_arn      = module.iam_role.role_arn

  memory_size   = 256
  timeout       = 30

  environment_variables = {
    ENVIRONMENT = "dev"
    LOG_LEVEL   = "INFO"
  }

  tags = {
    Environment = "dev"
  }
}
```

### Lambda with VPC and Layers

```hcl
module "vpc_lambda" {
  source = "./modules/lambda"

  function_name = "vpc-function"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  source_dir    = "${path.module}/../src/vpc-function"
  role_arn      = module.iam_role.role_arn

  memory_size   = 512
  timeout       = 300

  vpc_subnet_ids         = ["subnet-12345", "subnet-67890"]
  vpc_security_group_ids = ["sg-12345"]

  lambda_layers = [
    "arn:aws:lambda:us-east-1:123456789012:layer:my-layer:1"
  ]

  reserved_concurrent_executions = 10

  environment_variables = {
    DB_HOST = "mydb.example.com"
  }

  tags = {
    Environment = "prod"
  }
}
```

### Lambda with Function URL

```hcl
module "url_lambda" {
  source = "./modules/lambda"

  function_name = "api-function"
  handler       = "app.handler"
  runtime       = "python3.11"

  source_dir    = "${path.module}/../src/api"
  role_arn      = module.iam_role.role_arn

  enable_function_url   = true
  function_url_auth_type = "NONE"

  function_url_cors_config = {
    allow_origins = ["https://example.com"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["Content-Type"]
    max_age       = 86400
  }

  tags = {
    Environment = "dev"
  }
}
```

### Lambda with Dead Letter Queue

```hcl
module "dlq_lambda" {
  source = "./modules/lambda"

  function_name = "worker-function"
  handler       = "worker.process"
  runtime       = "python3.11"

  source_dir    = "${path.module}/../src/worker"
  role_arn      = module.iam_role.role_arn

  dlq_target_arn = aws_sqs_queue.dlq.arn

  tracing_mode = "Active"  # Enable X-Ray tracing

  log_retention_days = 14

  tags = {
    Environment = "prod"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| function_name | Name of the Lambda function | string | n/a | yes |
| handler | Lambda function handler | string | n/a | yes |
| runtime | Lambda runtime | string | n/a | yes |
| source_dir | Path to source directory | string | n/a | yes |
| role_arn | ARN of IAM role | string | n/a | yes |
| memory_size | Memory in MB | number | 128 | no |
| timeout | Timeout in seconds | number | 3 | no |
| environment_variables | Environment variables | map(string) | {} | no |
| vpc_subnet_ids | VPC subnet IDs | list(string) | null | no |
| lambda_layers | Lambda layer ARNs | list(string) | [] | no |
| reserved_concurrent_executions | Concurrency limit | number | -1 | no |

## Outputs

| Name | Description |
|------|-------------|
| function_name | Name of the function |
| function_arn | ARN of the function |
| function_invoke_arn | Invoke ARN for triggers |
| function_url | Function URL (if enabled) |
| log_group_name | CloudWatch Log Group name |

## Notes

- Source code is automatically zipped from `source_dir`
- Test files and Python cache files are excluded by default
- CloudWatch Log Group is created automatically
- VPC configuration requires NAT Gateway for internet access
- Function URL with `NONE` auth is publicly accessible
- Reserved concurrency limits affect account-level concurrency