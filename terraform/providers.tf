provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "mcp-first-responder"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner_email
    }
  }
}