variable "role_name" {
  description = "Name of the IAM role"
  type        = string
}

variable "service" {
  description = "AWS service that will assume this role (e.g., lambda.amazonaws.com)"
  type        = string
  default     = "lambda.amazonaws.com"
}

variable "policy_arns" {
  description = "List of AWS managed policy ARNs to attach to the role"
  type        = list(string)
  default     = []
}

variable "inline_policies" {
  description = "List of inline policies to attach to the role"
  type = list(object({
    name   = string
    policy = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to the IAM role"
  type        = map(string)
  default     = {}
}