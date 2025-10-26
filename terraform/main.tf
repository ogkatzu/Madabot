# Local variables for resource naming and common configurations
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.additional_tags
  )

  lambda_source_dir = "${path.module}/../lambdas"
}

# SSM Parameters for Secrets Management
resource "aws_ssm_parameter" "anthropic_api_key" {
  count = var.ai_provider == "anthropic" ? 1 : 0

  name        = "/${var.project_name}/${var.environment}/anthropic-api-key"
  description = "Anthropic API key for Claude"
  type        = "SecureString"
  value       = var.anthropic_api_key

  tags = local.common_tags
}

resource "aws_ssm_parameter" "google_api_key" {
  count = var.ai_provider == "google" ? 1 : 0

  name        = "/${var.project_name}/${var.environment}/google-api-key"
  description = "Google API key for Gemini"
  type        = "SecureString"
  value       = var.google_api_key

  tags = local.common_tags
}

resource "aws_ssm_parameter" "slack_webhook_url" {
  name        = "/${var.project_name}/${var.environment}/slack-webhook-url"
  description = "Slack webhook URL for notifications"
  type        = "SecureString"
  value       = var.slack_webhook_url

  tags = local.common_tags
}

resource "aws_ssm_parameter" "jira_api_token" {
  count = var.jira_enabled ? 1 : 0

  name        = "/${var.project_name}/${var.environment}/jira-api-token"
  description = "Jira API token"
  type        = "SecureString"
  value       = var.jira_api_token

  tags = local.common_tags
}

# DynamoDB Tables
module "dynamodb_alerts" {
  source = "./modules/dynamodb"

  table_name   = "${local.name_prefix}-alerts"
  billing_mode = var.dynamodb_billing_mode

  hash_key      = "alert_id"
  hash_key_type = "S"

  attributes = [
    {
      name = "alert_id"
      type = "S"
    },
    {
      name = "severity"
      type = "S"
    },
    {
      name = "timestamp"
      type = "N"
    }
  ]

  global_secondary_indexes = [
    {
      name            = "severity-timestamp-index"
      hash_key        = "severity"
      range_key       = "timestamp"
      projection_type = "ALL"
    }
  ]

  enable_streams   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  enable_ttl = false

  tags = local.common_tags
}

module "dynamodb_cache" {
  source = "./modules/dynamodb"

  table_name   = "${local.name_prefix}-analysis-cache"
  billing_mode = var.dynamodb_billing_mode

  hash_key      = "error_signature"
  hash_key_type = "S"

  attributes = [
    {
      name = "error_signature"
      type = "S"
    }
  ]

  global_secondary_indexes = []

  enable_streams = false

  enable_ttl         = true
  ttl_attribute_name = "ttl"

  tags = local.common_tags
}

# SQS Queues
module "sqs_processing" {
  source = "./modules/sqs"

  queue_name                  = "${local.name_prefix}-processing-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = var.processing_queue_visibility_timeout

  enable_dlq           = true
  dlq_name             = "${local.name_prefix}-processing-dlq.fifo"
  max_receive_count    = var.processing_queue_max_receive_count
  dlq_retention_period = var.dlq_retention_period

  tags = local.common_tags
}

module "sqs_distribution" {
  source = "./modules/sqs"

  queue_name                  = "${local.name_prefix}-distribution-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = var.distribution_queue_visibility_timeout

  enable_dlq           = true
  dlq_name             = "${local.name_prefix}-distribution-dlq.fifo"
  max_receive_count    = var.distribution_queue_max_receive_count
  dlq_retention_period = var.dlq_retention_period

  tags = local.common_tags
}

# IAM Roles for Lambda Functions
module "iam_ingestor" {
  source = "./modules/iam"

  role_name = "${local.name_prefix}-ingestor-role"
  service   = "lambda.amazonaws.com"

  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  inline_policies = [
    {
      name = "ingestor-permissions"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "sqs:SendMessage",
              "sqs:GetQueueAttributes"
            ]
            Resource = module.sqs_processing.queue_arn
          }
        ]
      })
    }
  ]

  tags = local.common_tags
}

module "iam_analyzer" {
  source = "./modules/iam"

  role_name = "${local.name_prefix}-analyzer-role"
  service   = "lambda.amazonaws.com"

  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  inline_policies = [
    {
      name = "analyzer-permissions"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "sqs:ReceiveMessage",
              "sqs:DeleteMessage",
              "sqs:GetQueueAttributes"
            ]
            Resource = module.sqs_processing.queue_arn
          },
          {
            Effect = "Allow"
            Action = [
              "sqs:SendMessage",
              "sqs:GetQueueAttributes"
            ]
            Resource = module.sqs_distribution.queue_arn
          },
          {
            Effect = "Allow"
            Action = [
              "dynamodb:GetItem",
              "dynamodb:PutItem",
              "dynamodb:UpdateItem",
              "dynamodb:Query",
              "dynamodb:Scan"
            ]
            Resource = [
              module.dynamodb_alerts.table_arn,
              "${module.dynamodb_alerts.table_arn}/index/*",
              module.dynamodb_cache.table_arn
            ]
          },
          {
            Effect = "Allow"
            Action = [
              "logs:FilterLogEvents",
              "logs:GetLogEvents",
              "logs:DescribeLogGroups",
              "logs:DescribeLogStreams"
            ]
            Resource = "*"
          },
          {
            Effect = "Allow"
            Action = [
              "ssm:GetParameter",
              "ssm:GetParameters"
            ]
            Resource = concat(
              var.ai_provider == "anthropic" ? [aws_ssm_parameter.anthropic_api_key[0].arn] : [],
              var.ai_provider == "google" ? [aws_ssm_parameter.google_api_key[0].arn] : []
            )
          }
        ]
      })
    }
  ]

  tags = local.common_tags
}

module "iam_notifier" {
  source = "./modules/iam"

  role_name = "${local.name_prefix}-notifier-role"
  service   = "lambda.amazonaws.com"

  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  inline_policies = [
    {
      name = "notifier-permissions"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "sqs:ReceiveMessage",
              "sqs:DeleteMessage",
              "sqs:GetQueueAttributes"
            ]
            Resource = module.sqs_distribution.queue_arn
          },
          {
            Effect = "Allow"
            Action = [
              "dynamodb:GetItem",
              "dynamodb:Query"
            ]
            Resource = module.dynamodb_alerts.table_arn
          },
          {
            Effect = "Allow"
            Action = [
              "ssm:GetParameter",
              "ssm:GetParameters"
            ]
            Resource = [
              aws_ssm_parameter.slack_webhook_url.arn
            ]
          },
          {
            Effect = "Allow"
            Action = [
              "ses:SendEmail",
              "ses:SendRawEmail"
            ]
            Resource = "*"
            Condition = {
              StringEquals = {
                "ses:FromAddress" = var.email_enabled ? var.email_from_address : ""
              }
            }
          }
        ]
      })
    }
  ]

  tags = local.common_tags
}

# Lambda Functions
module "lambda_ingestor" {
  source = "./modules/lambda"

  function_name = "${local.name_prefix}-ingestor"
  description   = "Ingests and normalizes alerts from CloudWatch"
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime

  source_dir = "${local.lambda_source_dir}/ingestor"

  role_arn = module.iam_ingestor.role_arn

  memory_size = var.ingestor_memory_size
  timeout     = var.ingestor_timeout

  environment_variables = {
    ENVIRONMENT          = var.environment
    PROCESSING_QUEUE_URL = module.sqs_processing.queue_url
    ALERTS_TABLE         = module.dynamodb_alerts.table_name
  }

  tags = local.common_tags
}

module "lambda_analyzer" {
  source = "./modules/lambda"

  function_name = "${local.name_prefix}-analyzer"
  description   = "Analyzes alerts using AI (${var.ai_provider == "anthropic" ? "Claude" : "Gemini"})"
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime

  source_dir = "${local.lambda_source_dir}/analyzer"

  role_arn = module.iam_analyzer.role_arn

  memory_size = var.analyzer_memory_size
  timeout     = var.analyzer_timeout

  environment_variables = merge(
    {
      ENVIRONMENT            = var.environment
      AI_PROVIDER            = var.ai_provider
      ALERTS_TABLE           = module.dynamodb_alerts.table_name
      ANALYSIS_CACHE_TABLE   = module.dynamodb_cache.table_name
      DISTRIBUTION_QUEUE_URL = module.sqs_distribution.queue_url
    },
    var.ai_provider == "anthropic" ? {
      ANTHROPIC_API_KEY_PARAM = aws_ssm_parameter.anthropic_api_key[0].name
    } : {},
    var.ai_provider == "google" ? {
      GOOGLE_API_KEY_PARAM = aws_ssm_parameter.google_api_key[0].name
    } : {}
  )

  reserved_concurrent_executions = 10 # Limit concurrency to control Claude API costs

  tags = local.common_tags
}

module "lambda_slack_notifier" {
  source = "./modules/lambda"

  function_name = "${local.name_prefix}-slack-notifier"
  description   = "Sends formatted alerts to Slack"
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime

  source_dir = "${local.lambda_source_dir}/slack_notifier"

  role_arn = module.iam_notifier.role_arn

  memory_size = var.notifier_memory_size
  timeout     = var.notifier_timeout

  environment_variables = {
    ENVIRONMENT             = var.environment
    ALERTS_TABLE            = module.dynamodb_alerts.table_name
    SLACK_WEBHOOK_URL_PARAM = aws_ssm_parameter.slack_webhook_url.name
  }

  tags = local.common_tags
}

# Lambda Event Source Mappings
resource "aws_lambda_event_source_mapping" "analyzer_sqs" {
  event_source_arn = module.sqs_processing.queue_arn
  function_name    = module.lambda_analyzer.function_arn
  batch_size       = 1
  enabled          = true

  scaling_config {
    maximum_concurrency = 10
  }
}

resource "aws_lambda_event_source_mapping" "notifier_sqs" {
  event_source_arn = module.sqs_distribution.queue_arn
  function_name    = module.lambda_slack_notifier.function_arn
  batch_size       = 1
  enabled          = true
}

# EventBridge Rule for CloudWatch Events
module "eventbridge" {
  source = "./modules/eventbridge"

  rule_name        = "${local.name_prefix}-cloudwatch-alerts"
  rule_description = "Routes CloudWatch error and warning events to ingestor"
  rule_state       = var.eventbridge_rule_state

  event_pattern = jsonencode({
    source      = ["aws.logs"]
    detail-type = ["CloudWatch Logs"]
    detail = {
      logGroup = var.cloudwatch_log_group_patterns
      logLevel = ["ERROR", "WARN", "CRITICAL"]
    }
  })

  target_arn = module.lambda_ingestor.function_arn

  tags = local.common_tags
}

# Grant EventBridge permission to invoke Lambda
resource "aws_lambda_permission" "eventbridge_invoke_ingestor" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_ingestor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = module.eventbridge.rule_arn
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "processing_dlq_alarm" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-processing-dlq-alarm"
  alarm_description   = "Alert when messages arrive in processing DLQ"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = var.dlq_alarm_threshold

  dimensions = {
    QueueName = module.sqs_processing.dlq_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "distribution_dlq_alarm" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-distribution-dlq-alarm"
  alarm_description   = "Alert when messages arrive in distribution DLQ"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = var.dlq_alarm_threshold

  dimensions = {
    QueueName = module.sqs_distribution.dlq_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "analyzer_errors" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-analyzer-errors"
  alarm_description   = "Alert when analyzer Lambda error rate is high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_rate_threshold

  dimensions = {
    FunctionName = module.lambda_analyzer.function_name
  }

  tags = local.common_tags
}