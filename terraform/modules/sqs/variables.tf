variable "queue_name" {
  description = "Name of the SQS queue"
  type        = string
}

variable "fifo_queue" {
  description = "Whether this is a FIFO queue"
  type        = bool
  default     = false
}

variable "content_based_deduplication" {
  description = "Enable content-based deduplication for FIFO queues"
  type        = bool
  default     = false
}

variable "visibility_timeout_seconds" {
  description = "Visibility timeout for the queue (in seconds)"
  type        = number
  default     = 30
}

variable "message_retention_seconds" {
  description = "Number of seconds Amazon SQS retains a message"
  type        = number
  default     = 345600 # 4 days
}

variable "max_message_size" {
  description = "Maximum message size in bytes"
  type        = number
  default     = 262144 # 256 KB
}

variable "delay_seconds" {
  description = "Delay before a message becomes available (in seconds)"
  type        = number
  default     = 0
}

variable "receive_wait_time_seconds" {
  description = "Wait time for ReceiveMessage calls (long polling)"
  type        = number
  default     = 0
}

variable "enable_dlq" {
  description = "Enable dead letter queue"
  type        = bool
  default     = false
}

variable "dlq_name" {
  description = "Name of the dead letter queue"
  type        = string
  default     = ""
}

variable "max_receive_count" {
  description = "Maximum number of receives before sending to DLQ"
  type        = number
  default     = 3
}

variable "dlq_retention_period" {
  description = "Message retention period for DLQ (in seconds)"
  type        = number
  default     = 1209600 # 14 days
}

variable "enable_sse" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "kms_master_key_id" {
  description = "KMS key ID for encryption (leave empty for AWS managed key)"
  type        = string
  default     = null
}

variable "queue_policy" {
  description = "JSON policy for the queue"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to the queue"
  type        = map(string)
  default     = {}
}