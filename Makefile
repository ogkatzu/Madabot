.PHONY: help init plan apply destroy clean validate fmt test

# Environment (override with: make plan ENV=staging)
ENV ?= dev

FUNCTIO_NAME = $$(cd terraform && terraform output -raw ingestor_function_name)
# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)MCP First-Responder - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

init: ## Initialize Terraform with backend for specified ENV
	@echo "$(BLUE)Initializing Terraform for $(ENV) environment...$(NC)"
	cd terraform && terraform init -backend-config=environments/$(ENV)-backend.tfvars

init-upgrade: ## Initialize and upgrade Terraform providers
	@echo "$(BLUE)Upgrading Terraform providers...$(NC)"
	cd terraform && terraform init -backend-config=environments/$(ENV)-backend.tfvars -upgrade

validate: ## Validate Terraform configuration
	@echo "$(BLUE)Validating Terraform configuration...$(NC)"
	cd terraform && terraform validate

fmt: ## Format Terraform files
	@echo "$(BLUE)Formatting Terraform files...$(NC)"
	cd terraform && terraform fmt -recursive

plan: ## Plan Terraform changes for ENV
	@echo "$(BLUE)Planning Terraform changes for $(ENV)...$(NC)"
	cd terraform && terraform plan -var-file=environments/$(ENV).tfvars

apply: ## Apply Terraform changes for ENV
	@echo "$(YELLOW)Applying Terraform changes for $(ENV)...$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd terraform && terraform apply -var-file=environments/$(ENV).tfvars; \
	fi

auto-apply: ## Apply Terraform changes without confirmation (CI/CD use)
	@echo "$(RED)Auto-applying Terraform changes for $(ENV)...$(NC)"
	cd terraform && terraform apply -var-file=environments/$(ENV).tfvars -auto-approve

destroy: ## Destroy Terraform infrastructure for ENV
	@echo "$(RED)Destroying infrastructure for $(ENV)...$(NC)"
	@read -p "Are you REALLY sure? Type '$(ENV)' to confirm: " -r; \
	echo; \
	if [[ $$REPLY == "$(ENV)" ]]; then \
		cd terraform && terraform destroy -var-file=environments/$(ENV).tfvars; \
	else \
		echo "$(RED)Confirmation failed. Aborting.$(NC)"; \
	fi

output: ## Show Terraform outputs
	@echo "$(BLUE)Terraform outputs:$(NC)"
	cd terraform && terraform output

clean: ## Clean Terraform artifacts
	@echo "$(BLUE)Cleaning Terraform artifacts...$(NC)"
	rm -rf terraform/.terraform/
	rm -f terraform/.terraform.lock.hcl
	find terraform/modules -type d -name '.terraform' -exec rm -rf {} + 2>/dev/null || true

# Lambda Development
lambda-deps: ## Install Lambda dependencies
	@echo "$(BLUE)Installing Lambda dependencies...$(NC)"
	cd lambdas/ingestor && pip install -r requirements.txt -t .
	cd lambdas/analyzer && pip install -r requirements.txt -t .
	cd lambdas/slack_notifier && pip install -r requirements.txt -t .

lambda-test: ## Run Lambda unit tests
	@echo "$(BLUE)Running Lambda tests...$(NC)"
	cd lambdas && python -m pytest

# Infrastructure Testing
test-ingestor: ## Test ingestor Lambda function
	@echo "$(BLUE)Testing ingestor Lambda...$(NC)"
	aws lambda invoke \
		--function-name $$(cd terraform && terraform output -raw ingestor_function_name) \
		--payload '{"test": "event"}' \
		response.json
	@cat response.json
	@rm response.json

logs-ingestor: ## Tail ingestor Lambda logs
	@echo "$(BLUE)Tailing ingestor logs...$(NC)"
	aws logs tail $$(cd terraform && terraform output -raw ingestor_log_group) --follow

logs-analyzer: ## Tail analyzer Lambda logs
	@echo "$(BLUE)Tailing analyzer logs...$(NC)"
	aws logs tail $$(cd terraform && terraform output -raw analyzer_log_group) --follow

logs-notifier: ## Tail notifier Lambda logs
	@echo "$(BLUE)Tailing notifier logs...$(NC)"
	aws logs tail $$(cd terraform && terraform output -raw notifier_log_group) --follow

check-dlq: ## Check processing dead letter queue
	@echo "$(BLUE)Checking processing DLQ...$(NC)"
	aws sqs receive-message \
		--queue-url $$(cd terraform && terraform output -raw processing_dlq_url) \
		--max-number-of-messages 10

check-queue: ## Check processing queue depth
	@echo "$(BLUE)Checking processing queue depth...$(NC)"
	aws sqs get-queue-attributes \
		--queue-url $$(cd terraform && terraform output -raw processing_queue_url) \
		--attribute-names ApproximateNumberOfMessagesVisible

# Setup Helpers
setup-backend: ## Create S3 bucket and DynamoDB table for Terraform state
	@echo "$(BLUE)Setting up Terraform backend...$(NC)"
	aws s3 mb s3://mcp-first-responder-terraform-state-$(ENV) --region us-east-1 || true
	aws s3api put-bucket-versioning \
		--bucket mcp-first-responder-terraform-state-$(ENV) \
		--versioning-configuration Status=Enabled
	aws dynamodb create-table \
		--table-name mcp-first-responder-terraform-locks \
		--attribute-definitions AttributeName=LockID,AttributeType=S \
		--key-schema AttributeName=LockID,KeyType=HASH \
		--billing-mode PAY_PER_REQUEST \
		--region us-east-1 || true
	@echo "$(GREEN)Backend setup complete!$(NC)"

# Full Deployment
deploy: init validate fmt plan apply ## Full deployment: init, validate, format, plan, apply

# Development Workflow
dev: ## Quick dev deployment
	@$(MAKE) ENV=dev deploy

staging: ## Quick staging deployment
	@$(MAKE) ENV=staging deploy

prod: ## Quick production deployment
	@$(MAKE) ENV=prod deploy

# Documentation
docs: ## Generate architecture documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd terraform && terraform-docs markdown table --output-file MODULE_DOCS.md modules/

# Version Info
version: ## Show Terraform and provider versions
	@echo "$(BLUE)Terraform version:$(NC)"
	cd terraform && terraform version

# Test Event File
test-event: ## Show sample test event
	@echo "$(BLUE)Sample test event:$(NC)"
	@cat test-event.json
	openssl base64 -out encoded_payload -in test-event.json
	aws lambda invoke \
    --function-name $(FUNCTIO_NAME) \
    --payload file://encoded_payload \
    response.json