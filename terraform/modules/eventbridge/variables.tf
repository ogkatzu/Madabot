variable "rule_name" {
  description = "Name of the EventBridge rule"
  type        = string
}

variable "rule_description" {
  description = "Description of the EventBridge rule"
  type        = string
  default     = ""
}

variable "event_pattern" {
  description = "Event pattern as JSON string"
  type        = string
  default     = null
}

variable "schedule_expression" {
  description = "Schedule expression (rate or cron)"
  type        = string
  default     = null
}

variable "rule_state" {
  description = "State of the rule (ENABLED or DISABLED)"
  type        = string
  default     = "ENABLED"
  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.rule_state)
    error_message = "Rule state must be ENABLED or DISABLED."
  }
}

variable "role_arn" {
  description = "IAM role ARN for EventBridge to assume"
  type        = string
  default     = null
}

variable "target_id" {
  description = "Unique target ID"
  type        = string
  default     = "1"
}

variable "target_arn" {
  description = "ARN of the target (Lambda, SQS, SNS, etc.)"
  type        = string
}

variable "input_transformer" {
  description = "Input transformer configuration"
  type = object({
    input_paths    = map(string)
    input_template = string
  })
  default = null
}

variable "dlq_arn" {
  description = "ARN of the dead letter queue for failed events"
  type        = string
  default     = null
}

variable "retry_policy" {
  description = "Retry policy configuration"
  type = object({
    maximum_event_age_in_seconds = number
    maximum_retry_attempts       = number
  })
  default = null
}

variable "sqs_message_group_id" {
  description = "Message group ID for FIFO SQS target"
  type        = string
  default     = null
}

variable "batch_size" {
  description = "Batch size for SQS/Kinesis targets"
  type        = number
  default     = null
}

variable "batch_job_definition" {
  description = "AWS Batch job definition"
  type        = string
  default     = null
}

variable "batch_job_name" {
  description = "AWS Batch job name"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to the EventBridge rule"
  type        = map(string)
  default     = {}
}