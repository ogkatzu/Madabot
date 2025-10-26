# Dead Letter Queue (created first so main queue can reference it)
resource "aws_sqs_queue" "dlq" {
  count = var.enable_dlq ? 1 : 0

  name                        = var.dlq_name
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : null
  message_retention_seconds   = var.dlq_retention_period
  delay_seconds               = 0

  tags = var.tags
}

# Main SQS Queue
resource "aws_sqs_queue" "this" {
  name                        = var.queue_name
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : null

  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  max_message_size           = var.max_message_size
  delay_seconds              = var.delay_seconds
  receive_wait_time_seconds  = var.receive_wait_time_seconds

  # Redrive policy (for DLQ)
  redrive_policy = var.enable_dlq ? jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
    maxReceiveCount     = var.max_receive_count
  }) : null

  # Server-side encryption
  sqs_managed_sse_enabled = var.enable_sse ? true : null
  kms_master_key_id       = var.kms_master_key_id

  tags = var.tags
}

# Queue Policy (optional)
resource "aws_sqs_queue_policy" "this" {
  count = var.queue_policy != null ? 1 : 0

  queue_url = aws_sqs_queue.this.id
  policy    = var.queue_policy
}