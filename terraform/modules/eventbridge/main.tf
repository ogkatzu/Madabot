# EventBridge Rule
resource "aws_cloudwatch_event_rule" "this" {
  name                = var.rule_name
  description         = var.rule_description
  event_pattern       = var.event_pattern
  schedule_expression = var.schedule_expression
  state               = var.rule_state
  role_arn            = var.role_arn

  tags = var.tags
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "this" {
  rule      = aws_cloudwatch_event_rule.this.name
  target_id = var.target_id
  arn       = var.target_arn

  # Input transformation
  dynamic "input_transformer" {
    for_each = var.input_transformer != null ? [1] : []
    content {
      input_paths    = var.input_transformer.input_paths
      input_template = var.input_transformer.input_template
    }
  }

  # Dead letter queue
  dynamic "dead_letter_config" {
    for_each = var.dlq_arn != null ? [1] : []
    content {
      arn = var.dlq_arn
    }
  }

  # Retry policy
  dynamic "retry_policy" {
    for_each = var.retry_policy != null ? [1] : []
    content {
      maximum_event_age_in_seconds = var.retry_policy.maximum_event_age_in_seconds
      maximum_retry_attempts       = var.retry_policy.maximum_retry_attempts
    }
  }

  # SQS target configuration
  dynamic "sqs_target" {
    for_each = var.sqs_message_group_id != null ? [1] : []
    content {
      message_group_id = var.sqs_message_group_id
    }
  }

  # Batch configuration (for SQS and Kinesis)
  dynamic "batch_target" {
    for_each = var.batch_size != null ? [1] : []
    content {
      job_definition = var.batch_job_definition
      job_name       = var.batch_job_name
    }
  }
}