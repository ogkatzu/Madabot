# SQS Module

This module creates SQS queues with optional dead letter queues, FIFO support, and encryption.

## Features

- Standard and FIFO queue support
- Dead letter queue (DLQ) with configurable retry logic
- Content-based deduplication for FIFO queues
- Server-side encryption with KMS or AWS managed keys
- Long polling support
- Configurable message retention and visibility timeout
- Custom queue policies

## Usage

### Standard Queue with DLQ

```hcl
module "processing_queue" {
  source = "./modules/sqs"

  queue_name                 = "my-processing-queue"
  visibility_timeout_seconds = 300

  enable_dlq           = true
  dlq_name             = "my-processing-dlq"
  max_receive_count    = 3
  dlq_retention_period = 1209600  # 14 days

  tags = {
    Environment = "dev"
  }
}
```

### FIFO Queue with Content-Based Deduplication

```hcl
module "fifo_queue" {
  source = "./modules/sqs"

  queue_name                  = "my-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 900

  enable_dlq           = true
  dlq_name             = "my-queue-dlq.fifo"
  max_receive_count    = 3

  tags = {
    Environment = "prod"
  }
}
```

### Queue with Custom Policy

```hcl
module "queue_with_policy" {
  source = "./modules/sqs"

  queue_name = "my-queue"

  queue_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "sqs:SendMessage"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = "dev"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| queue_name | Name of the SQS queue | string | n/a | yes |
| fifo_queue | Whether this is a FIFO queue | bool | false | no |
| content_based_deduplication | Enable content-based deduplication | bool | false | no |
| visibility_timeout_seconds | Visibility timeout (seconds) | number | 30 | no |
| message_retention_seconds | Message retention period (seconds) | number | 345600 | no |
| enable_dlq | Enable dead letter queue | bool | false | no |
| dlq_name | Name of the DLQ | string | "" | no |
| max_receive_count | Max receives before DLQ | number | 3 | no |
| enable_sse | Enable server-side encryption | bool | true | no |

## Outputs

| Name | Description |
|------|-------------|
| queue_url | URL of the queue |
| queue_arn | ARN of the queue |
| queue_name | Name of the queue |
| dlq_url | URL of the DLQ (if enabled) |
| dlq_arn | ARN of the DLQ (if enabled) |

## Notes

- FIFO queue names must end with `.fifo`
- Content-based deduplication requires FIFO queues
- DLQ retention period should be longer than main queue
- Visibility timeout should match Lambda function timeout