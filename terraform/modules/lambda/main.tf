# Data source to create zip file from source directory
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.terraform/tmp/${var.function_name}.zip"
  excludes    = var.exclude_files
}

# Lambda Function
resource "aws_lambda_function" "this" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.function_name
  role             = var.role_arn
  handler          = var.handler
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = var.runtime

  memory_size = var.memory_size
  timeout     = var.timeout

  reserved_concurrent_executions = var.reserved_concurrent_executions

  # Environment variables
  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  # VPC configuration
  dynamic "vpc_config" {
    for_each = var.vpc_subnet_ids != null ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  # Layers
  layers = var.lambda_layers

  # Dead letter config
  dynamic "dead_letter_config" {
    for_each = var.dlq_target_arn != null ? [1] : []
    content {
      target_arn = var.dlq_target_arn
    }
  }

  # Tracing
  tracing_config {
    mode = var.tracing_mode
  }

  # Ephemeral storage
  ephemeral_storage {
    size = var.ephemeral_storage_size
  }

  tags = var.tags

  depends_on = [
    data.archive_file.lambda_zip
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Lambda Function URL (optional)
resource "aws_lambda_function_url" "this" {
  count = var.enable_function_url ? 1 : 0

  function_name      = aws_lambda_function.this.function_name
  authorization_type = var.function_url_auth_type

  dynamic "cors" {
    for_each = var.function_url_cors_config != null ? [1] : []
    content {
      allow_credentials = lookup(var.function_url_cors_config, "allow_credentials", false)
      allow_origins     = lookup(var.function_url_cors_config, "allow_origins", ["*"])
      allow_methods     = lookup(var.function_url_cors_config, "allow_methods", ["*"])
      allow_headers     = lookup(var.function_url_cors_config, "allow_headers", [])
      expose_headers    = lookup(var.function_url_cors_config, "expose_headers", [])
      max_age           = lookup(var.function_url_cors_config, "max_age", 0)
    }
  }
}