# EventBridge Module

This module creates EventBridge (CloudWatch Events) rules and targets for event-driven architectures.

## Features

- Event pattern-based rules
- Schedule-based rules (rate or cron)
- Multiple target types (Lambda, SQS, SNS, etc.)
- Input transformation
- Dead letter queue for failed events
- Retry policies
- Support for FIFO SQS targets
- Batch targets for SQS and Kinesis

## Usage

### Event Pattern Rule (CloudWatch Logs)

```hcl
module "cloudwatch_alerts" {
  source = "./modules/eventbridge"

  rule_name        = "cloudwatch-error-alerts"
  rule_description = "Route CloudWatch error logs to Lambda"
  rule_state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["aws.logs"]
    detail-type = ["CloudWatch Logs"]
    detail = {
      logGroup = ["/aws/lambda/*"]
      logLevel = ["ERROR", "CRITICAL"]
    }
  })

  target_arn = module.lambda.function_arn

  retry_policy = {
    maximum_event_age      = 3600
    maximum_retry_attempts = 2
  }

  tags = {
    Environment = "dev"
  }
}
```

### Schedule-Based Rule (Cron)

```hcl
module "scheduled_task" {
  source = "./modules/eventbridge"

  rule_name        = "daily-cleanup"
  rule_description = "Run cleanup task daily at 2 AM UTC"

  schedule_expression = "cron(0 2 * * ? *)"

  target_arn = module.lambda.function_arn

  tags = {
    Environment = "prod"
  }
}
```

### Rule with Input Transformation

```hcl
module "transformed_events" {
  source = "./modules/eventbridge"

  rule_name = "ec2-state-changes"

  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
  })

  target_arn = module.lambda.function_arn

  input_transformer = {
    input_paths = {
      instance = "$.detail.instance-id"
      state    = "$.detail.state"
      time     = "$.time"
    }
    input_template = <<EOF
{
  "instance_id": <instance>,
  "state": <state>,
  "timestamp": <time>
}
EOF
  }

  tags = {
    Environment = "dev"
  }
}
```

### Rule with FIFO SQS Target

```hcl
module "fifo_queue_events" {
  source = "./modules/eventbridge"

  rule_name = "order-events"

  event_pattern = jsonencode({
    source      = ["custom.orders"]
    detail-type = ["Order Placed"]
  })

  target_arn = aws_sqs_queue.orders_fifo.arn

  sqs_message_group_id = "orders"

  dlq_arn = aws_sqs_queue.events_dlq.arn

  tags = {
    Environment = "prod"
  }
}
```

### Rate-Based Schedule

```hcl
module "health_check" {
  source = "./modules/eventbridge"

  rule_name        = "health-check"
  rule_description = "Run health check every 5 minutes"

  schedule_expression = "rate(5 minutes)"

  target_arn = module.lambda.function_arn

  tags = {
    Environment = "prod"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| rule_name | Name of the EventBridge rule | string | n/a | yes |
| rule_description | Description of the rule | string | "" | no |
| event_pattern | Event pattern as JSON | string | null | no |
| schedule_expression | Schedule (rate or cron) | string | null | no |
| rule_state | Rule state (ENABLED/DISABLED) | string | "ENABLED" | no |
| target_arn | ARN of the target | string | n/a | yes |
| input_transformer | Input transformation config | object | null | no |
| dlq_arn | DLQ ARN for failed events | string | null | no |
| retry_policy | Retry policy configuration | object | null | no |

## Outputs

| Name | Description |
|------|-------------|
| rule_name | Name of the rule |
| rule_arn | ARN of the rule |
| target_id | ID of the target |

## Notes

- Either `event_pattern` or `schedule_expression` must be set
- FIFO SQS targets require `sqs_message_group_id`
- Lambda targets need `aws_lambda_permission` resource
- Input transformer paths use JSONPath syntax
- Cron expressions use AWS cron format (6 fields)
- Rate expressions support minutes, hours, or days

## Event Pattern Examples

### CloudWatch Logs
```json
{
  "source": ["aws.logs"],
  "detail-type": ["CloudWatch Logs"]
}
```

### EC2 State Changes
```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"]
}
```

### Custom Application Events
```json
{
  "source": ["custom.app"],
  "detail-type": ["User Action"]
}
```