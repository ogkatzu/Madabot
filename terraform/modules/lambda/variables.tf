variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "description" {
  description = "Description of the Lambda function"
  type        = string
  default     = ""
}

variable "handler" {
  description = "Lambda function handler"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
}

variable "source_dir" {
  description = "Path to the source directory containing Lambda code"
  type        = string
}

variable "exclude_files" {
  description = "List of file patterns to exclude from the zip"
  type        = list(string)
  default     = ["tests/*", "*.pyc", "__pycache__/*", ".pytest_cache/*", "*.egg-info/*"]
}

variable "role_arn" {
  description = "ARN of the IAM role for Lambda execution"
  type        = string
}

variable "memory_size" {
  description = "Amount of memory in MB allocated to the Lambda function"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Timeout in seconds for the Lambda function"
  type        = number
  default     = 3
}

variable "reserved_concurrent_executions" {
  description = "Reserved concurrent executions for the function (-1 for unreserved)"
  type        = number
  default     = -1
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "vpc_subnet_ids" {
  description = "List of subnet IDs for VPC configuration"
  type        = list(string)
  default     = null
}

variable "vpc_security_group_ids" {
  description = "List of security group IDs for VPC configuration"
  type        = list(string)
  default     = null
}

variable "lambda_layers" {
  description = "List of Lambda layer ARNs"
  type        = list(string)
  default     = []
}

variable "dlq_target_arn" {
  description = "ARN of SQS queue or SNS topic for dead letter queue"
  type        = string
  default     = null
}

variable "tracing_mode" {
  description = "X-Ray tracing mode (PassThrough or Active)"
  type        = string
  default     = "PassThrough"
}

variable "ephemeral_storage_size" {
  description = "Size of ephemeral storage (/tmp) in MB"
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 7
}

variable "enable_function_url" {
  description = "Enable Lambda function URL"
  type        = bool
  default     = false
}

variable "function_url_auth_type" {
  description = "Authorization type for function URL (NONE or AWS_IAM)"
  type        = string
  default     = "AWS_IAM"
}

variable "function_url_cors_config" {
  description = "CORS configuration for function URL"
  type        = map(any)
  default     = null
}

variable "tags" {
  description = "Tags to apply to the Lambda function"
  type        = map(string)
  default     = {}
}