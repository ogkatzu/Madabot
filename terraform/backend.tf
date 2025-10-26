# Backend configuration for Terraform state
# Initialize with: terraform init -backend-config=environments/<env>-backend.tfvars

terraform {
  backend "s3" {
    # bucket         = "your-terraform-state-bucket"  # Set via backend config file
    # key            = "mcp-first-responder/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "terraform-state-lock"
    # encrypt        = true
  }
}