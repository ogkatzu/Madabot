# CloudWatch Logs Subscription Filters
# These send log events directly to the Ingestor Lambda

# Grant CloudWatch Logs permission to invoke Lambda
resource "aws_lambda_permission" "cloudwatch_logs_invoke_ingestor" {
  statement_id  = "AllowExecutionFromCloudWatchLogs"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_ingestor.function_name
  principal     = "logs.amazonaws.com"
}

# Subscription filter for test application
resource "aws_cloudwatch_log_subscription_filter" "test_app" {
  count = var.enable_test_app_monitoring ? 1 : 0

  name            = "${local.name_prefix}-test-app-errors"
  log_group_name  = "/aws/test-app"
  filter_pattern  = "?ERROR ?CRITICAL ?WARN"
  destination_arn = module.lambda_ingestor.function_arn

  depends_on = [
    aws_lambda_permission.cloudwatch_logs_invoke_ingestor
  ]
}

# Subscription filters for Lambda functions
resource "aws_cloudwatch_log_subscription_filter" "lambda_errors" {
  for_each = var.enable_lambda_monitoring ? toset(var.monitored_lambda_patterns) : []

  name            = "${local.name_prefix}-lambda-${replace(each.value, "/aws/lambda/", "")}-errors"
  log_group_name  = each.value
  filter_pattern  = "?ERROR ?Exception ?Traceback"
  destination_arn = module.lambda_ingestor.function_arn

  depends_on = [
    aws_lambda_permission.cloudwatch_logs_invoke_ingestor
  ]
}
